"""The oracle GUI's one results renderer, built from the workflow SSOT.

Design note 32, step **OG-E**. The same argument as the input form one level on:
there are fourteen oracle pages and no fourteen output blocks. A page's programs
are :func:`sloads.workflow.step_modules` -- its own ``module`` plus the
contributors folded into it, which together are what its ``bas`` string claims
-- so Weight & Mass Properties runs WTESTIMA, WTONECG and WTENV because
``workflow.py`` says it does, not because this file names them.

**Every artifact comes from an owner** (OG-6). Load cases are
:func:`sloads.io.load_cases_csv` with :func:`~sloads.report.csv_comment_block`,
and the text report is :func:`sloads.report.module_text_report` -- the same two
calls ``cli.py`` makes, so the ULT marker and the per-case SF statement are
identical by construction rather than by resemblance. There is no CSV writer
here and no unit factor here; the deliverable system is resolved once, in the
shell, and handed to the owners.

**The station tables.** OG-6 named two owners, which gives a page its load cases
and nothing else -- and the load cases are not what AIRLOADS, NETLOADS or
TAILDIST *print*. Their printed output, the output Appendix A is, is the
spanwise/chordwise station table, which lives in ``ModuleResult`` nowhere: it is
built from ``wing_load_rows``/``body_load_rows``/``build_tail_chordwise`` and
rendered by :mod:`app_shell.limit_csv`, the shared shell owner OG-B extracted
for exactly this channel. OG-6 is amended (2026-08-20, owner) to name it as a
third owner, because an oracle GUI that cannot show the oracle's own printout is
not one. Those tables are **LIMIT** -- the oracle-traceable calc values, the
``CONVENTIONS.md`` analysis-page carve-out -- and say so in-band, in the
``Basis`` column and in the ``*_LIMIT.csv`` filename.

:data:`STATION_TABLES` is keyed by *module* name, not by page key: which row
builder a program has is a fact about the program, and keying on the page would
put a step key back in the GUI (gate G2).

**One download call site.** :func:`step_results` returns the blocks and their
:class:`Artifact` payloads as data, and :func:`render_results` is the only place
that turns one into an ``st.download_button``. Gate **G7** reads the payloads
directly, so what it checks is the bytes the user gets, not a source pattern
that resembles them -- and a second call site would be an artifact the gate had
never seen, which ``tests/test_oracle_gui.py`` fails on.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, NamedTuple, Tuple

import pandas as pd
import streamlit as st

from app_shell.limit_csv import (
    body_limit_csv,
    body_limit_rows,
    tail_limit_csv,
    tail_limit_rows,
    wing_limit_csv,
    wing_limit_rows,
)
from oracle_app.labels import pretty
from sloads import UnitSystem, convert_results, registry
from sloads import io as sloads_io
from sloads import workflow as wf
from sloads.models import Project
from sloads.modules.body_loads import body_load_rows, build_body_loads
from sloads.modules.net_loads import build_net_loads, wing_load_rows
from sloads.modules.taildist import build_tail_chordwise
from sloads.report import (
    csv_comment_block,
    has_load_case_data,
    load_cases_to_rows,
    module_text_report,
    results_to_rows,
)

#: What a page states about the loads in one block. The oracle GUI never applies
#: a factor of its own -- these describe what the owner already produced.
ULTIMATE = "ULTIMATE"
LIMIT = "LIMIT"

#: The error contract's two halves (``00_program_overview.md``): a module raises
#: ``MissingInputError`` for an absent slice and ``ValueError`` for input that is
#: present but unusable, and both mean *this page is not ready yet* rather than
#: *this GUI is broken*. Caught here and shown as the block's note, exactly as
#: ``app/views/one_engine_out.py`` does. Anything else still raises: a renderer
#: bug must not be indistinguishable from a blank project.
_NOT_READY = (ValueError, ZeroDivisionError)

_ULT_NOTE = ("ULTIMATE loads (= limit x the case safety factor); the factor is "
             "in the SF column and the `-ULT` marker is part of the units.")
# The basis is stated in the table itself, but *where* depends on the table: the
# wing and fuselage station tables carry a `Basis` column, while the tail
# chordwise table has none and marks every load header instead
# (`app_shell/limit_csv.tail_limit_rows`). Saying only "the Basis column" was
# wrong for a third of the tables this caption sits under (review CR-A-7).
_LIMIT_NOTE = ("LIMIT station loads -- the oracle-traceable calc values "
               "(CONVENTIONS.md §3). The basis travels with the table: in its "
               "`Basis` column, or in each load's column header where the table "
               "has no such column, and in the `_LIMIT.csv` filename.")


class Artifact(NamedTuple):
    """One downloadable file a page offers, payload included.

    The payload is the string the user receives, so gate G7 can read it rather
    than infer it from the call that would have produced it.
    """

    label: str
    file_name: str
    mime: str
    payload: str


class ResultBlock(NamedTuple):
    """One heading, one table, its downloads -- or a note saying why there is
    no table yet."""

    module: str
    title: str
    basis: str = ULTIMATE
    rows: Tuple[Dict[str, Any], ...] = ()
    artifacts: Tuple[Artifact, ...] = ()
    note: str = ""


class StationTable(NamedTuple):
    """A program's printed station table: how to build it, and how the shell
    renders and writes it."""

    title: str
    stem: str
    build: Callable[[Project], Any]
    rows: Callable[[Any, UnitSystem], List[Dict[str, object]]]
    csv: Callable[[Any, UnitSystem], str]


#: The three programs that print a station table, keyed by module name. Their
#: builders return different shapes (wing and fuselage go through a row builder
#: first; TAILDIST's results are rendered directly), which is why each entry
#: carries its own ``build``.
STATION_TABLES: Dict[str, StationTable] = {
    "net_loads": StationTable(
        "Spanwise wing stations", "wing_stations",
        lambda p: wing_load_rows(build_net_loads(p).wing_net),
        wing_limit_rows, wing_limit_csv),
    "body_loads": StationTable(
        "Fuselage stations", "fuselage_stations",
        lambda p: body_load_rows(build_body_loads(p)),
        body_limit_rows, body_limit_csv),
    "taildist": StationTable(
        "Chordwise tail distribution", "tail_chordwise",
        build_tail_chordwise,
        tail_limit_rows, tail_limit_csv),
}


# --------------------------------------------------------------------------- #
# Building the blocks -- pure, no Streamlit
# --------------------------------------------------------------------------- #
def _module_block(project: Project, name: str, system: UnitSystem) -> ResultBlock:
    """One program's load cases, as a table plus its CSV and text downloads."""
    title = pretty(name)
    try:
        result = registry.get(name)(project)
    except _NOT_READY as exc:
        return ResultBlock(name, title, note=f"{title} cannot run yet — {exc}")

    display = convert_results(result.conditions, system)
    if not display:
        return ResultBlock(name, title, note=f"{title} produced no conditions.")

    rows = (load_cases_to_rows(display) if has_load_case_data(display)
            else results_to_rows(display))
    artifacts = (
        Artifact(f"{title} (CSV)", f"{name}.csv", "text/csv",
                 sloads_io.load_cases_csv(result,
                                          header_comment=csv_comment_block(project),
                                          system=system)),
        Artifact(f"{title} (text)", f"{name}.txt", "text/plain",
                 module_text_report(title, display)),
    )
    return ResultBlock(name, title, ULTIMATE, tuple(rows), artifacts)


def _station_block(project: Project, name: str, system: UnitSystem) -> ResultBlock:
    """The program's printed station table, LIMIT and marked as such."""
    spec = STATION_TABLES[name]
    try:
        built = spec.build(project)
    except _NOT_READY as exc:
        return ResultBlock(name, spec.title, LIMIT,
                           note=f"{spec.title} cannot be built yet — {exc}")
    rows = spec.rows(built, system)
    if not rows:
        return ResultBlock(name, spec.title, LIMIT,
                           note=f"{spec.title} has no stations.")
    artifact = Artifact(f"{spec.title} (CSV, LIMIT)",
                        f"{spec.stem}_LIMIT.csv", "text/csv",
                        spec.csv(built, system))
    return ResultBlock(name, spec.title, LIMIT, tuple(rows), (artifact,))


def step_results(project: Project, key: str, system: UnitSystem) -> List[ResultBlock]:
    """Every result block one oracle page shows, in the order it shows them.

    Empty when the step runs no program at all -- a pure input page has no
    results heading rather than an empty one.
    """
    modules = wf.step_modules(key)
    if not modules:
        return []

    step = wf.BY_KEY[key]
    upstream = wf.missing_upstream(project, step)
    own = wf.missing_self_entered(project, step)
    if upstream or own:
        # Two remedies, named separately (#45, CR-D-3): an upstream slice is
        # another page's to make; a self-entered one is this page's own form.
        parts = []
        if upstream:
            parts.append(f"needs {', '.join(f'`{m}`' for m in upstream)} — "
                         "run the pages before this one first")
        if own:
            parts.append(f"needs {', '.join(f'`{m}`' for m in own)} — "
                         "entered on this very page: fill in the form above")
        return [ResultBlock(
            "", step.title,
            note=f"{step.bas or step.title} {'; '.join(parts)}.")]

    blocks: List[ResultBlock] = []
    for name in modules:
        blocks.append(_module_block(project, name, system))
        if name in STATION_TABLES:
            blocks.append(_station_block(project, name, system))
    return blocks


def page_artifacts(project: Project, key: str,
                   system: UnitSystem) -> List[Artifact]:
    """Every file one oracle page offers for download. Gate G7's subject."""
    return [a for b in step_results(project, key, system) for a in b.artifacts]


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_results(project: Project, key: str, system: UnitSystem) -> None:
    """Render one oracle page's results, downloads included."""
    blocks = step_results(project, key, system)
    if not blocks:
        return

    st.header("Results")
    for block in blocks:
        st.subheader(block.title)
        if block.module:
            st.caption(f"`{block.module}`")
        if block.note:
            st.info(block.note)
            st.divider()
            continue

        st.caption(_ULT_NOTE if block.basis == ULTIMATE else _LIMIT_NOTE)
        st.dataframe(pd.DataFrame(list(block.rows)), hide_index=True,
                     width="stretch")
        columns = st.columns(len(block.artifacts))
        for column, artifact in zip(columns, block.artifacts):
            column.download_button(
                f"Download {artifact.label}", artifact.payload,
                file_name=artifact.file_name, mime=artifact.mime,
                key=f"{key}.{artifact.file_name}", width="stretch")
        st.divider()


__all__ = [
    "LIMIT", "STATION_TABLES", "ULTIMATE", "Artifact", "ResultBlock",
    "StationTable", "page_artifacts", "render_results", "step_results",
]
