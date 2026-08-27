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

import traceback as tb
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
from sloads import UnitSystem, convert_results, mass_distribution, registry
from sloads import io as sloads_io
from sloads import workflow as wf
from sloads.models import ConditionResult, LoadValue, Project
from sloads.modules.body_loads import body_load_rows, build_body_loads
from sloads.modules.net_loads import build_net_loads, wing_load_rows
from sloads.modules.taildist import build_tail_chordwise
from sloads.modules.weight_estimate import ADVISORY as _ESTIMATE_ADVISORY
from sloads.modules.weight_estimate import compare_with_itemized
from sloads.report import (
    csv_comment_block,
    format_value,
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
#:
#: ``ZeroDivisionError`` was in this tuple until 2026-08-24 (#71/PB-18, narrow
#: half) and is **not** part of that contract: it is not a ``ValueError``, no
#: module raises it deliberately, and it never means "keep typing" — it is
#: arithmetic that went wrong. A blank weight/CG case produced exactly that, so a
#: page that had been working stopped dead and said only that it was not ready.
#: That case now refuses by name upstream (``build_envelope``); any other
#: division by zero is a defect and surfaces as one. The remaining half of #71 —
#: showing the exception type and an expandable traceback rather than ``str(e)``
#: alone (C210-24) — shipped at #99: ``_not_ready_traceback`` below.
_NOT_READY = (ValueError,)


def _not_ready_traceback(exc: BaseException) -> str:
    """The traceback behind a not-ready note, module:line first (C210-24).

    The first line names the frame that raised -- the one thing a bug report
    needs -- so the reader is not made to walk the whole stack to find it; the
    full traceback follows for the report itself.
    """
    frames = tb.extract_tb(exc.__traceback__)
    where = ""
    if frames:
        last = frames[-1]
        where = f"{last.filename}:{last.lineno} in {last.name}\n\n"
    return where + "".join(
        tb.format_exception(type(exc), exc, exc.__traceback__))

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
    #: The traceback behind a not-ready ``note``, module:line first (C210-24 /
    #: the display half of #71): the friendly one-liner stays, but a from-blank
    #: user must be able to report *where* it died without leaving the GUI.
    #: Rendered as an expander beside the note; empty when the note is not an
    #: exception ("no conditions", "no stations").
    traceback: str = ""
    #: What the block *is*, said before the numbers rather than about them: a
    #: statistical estimate that feeds nothing downstream reads as an input to
    #: everything below it unless the page says otherwise (C210-9, #78). Shown
    #: as a caption, not a warning — nothing here is wrong, and a warning on a
    #: block that is behaving exactly as designed is the boy who cried wolf.
    advisory: str = ""
    #: What the numbers rest on that the user should know before trusting them
    #: -- an item data base that never said which beam carries the wing, a
    #: wing-mass tie that does not close. Shown as warnings above the table.
    warnings: Tuple[str, ...] = ()


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
        return ResultBlock(
            name, title,
            note=f"{title} cannot run yet — {type(exc).__name__}: {exc}",
            traceback=_not_ready_traceback(exc))

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
    advisory = MODULE_ADVISORIES.get(name)
    return ResultBlock(name, title, ULTIMATE, tuple(rows), artifacts,
                       advisory=advisory(project, system) if advisory else "")


def _station_block(project: Project, name: str, system: UnitSystem) -> ResultBlock:
    """The program's printed station table, LIMIT and marked as such."""
    spec = STATION_TABLES[name]
    try:
        built = spec.build(project)
    except _NOT_READY as exc:
        return ResultBlock(
            name, spec.title, LIMIT,
            note=f"{spec.title} cannot be built yet — {type(exc).__name__}: {exc}",
            traceback=_not_ready_traceback(exc))
    rows = spec.rows(built, system)
    if not rows:
        return ResultBlock(name, spec.title, LIMIT,
                           note=f"{spec.title} has no stations.")
    artifact = Artifact(f"{spec.title} (CSV, LIMIT)",
                        f"{spec.stem}_LIMIT.csv", "text/csv",
                        spec.csv(built, system))
    return ResultBlock(name, spec.title, LIMIT, tuple(rows), (artifact,),
                       warnings=STATION_WARNINGS.get(name, lambda _p: ())(project))


def fuselage_mass_warnings(project: Project) -> Tuple[str, ...]:
    """What the fuselage beam carries that the item data base did not say.

    BODYLOAD's own input was the fuselage item list, so which items it lumps was
    never in doubt. Here that is the ``component`` tag, and an untagged item is
    carried by the fuselage *by inference* (``mass_distribution.infer_component``
    refuses to guess anything else) -- on the GA-6 that put the 330 lb wing panel
    on the fuselage beam at 9 % of its peak shear with nothing on the page
    saying so (review 2026-08-22 PB-2). The wing-mass tie, the entered-station
    reconciliation and a tail surface with no item at all are the same
    question from the other side, so they are stated here together.
    """
    out: List[str] = []
    inferred = mass_distribution.distribution(project).inferred
    if inferred:
        shown = ", ".join(inferred[:6]) + (" …" if len(inferred) > 6 else "")
        out.append(f"{len(inferred)} weight item(s) carry no component tag and are lumped "
                   f"on the fuselage beam by inference: {shown}. Tag the wing and "
                   "empennage items on the Weight & Mass page (`component`).")
    for check in (mass_distribution.wing_mass_tie(project),
                  mass_distribution.fuselage_reconciliation(project)):
        if check is not None and not check.ok:
            out.append(f"{check.code}: {check.detail}.")
    untagged = mass_distribution.untagged_tail_surfaces(project)
    if untagged and project.weight is not None and project.weight.items:
        out.append(f"No weight item is tagged {' or '.join(f'`{c}`' for c in untagged)}: "
                   "that surface's mass rides the fuselage beam.")
    return tuple(out)


#: Per station table, the pure check that says what its numbers rest on.
STATION_WARNINGS: Dict[str, Callable[[Project], Tuple[str, ...]]] = {
    "body_loads": fuselage_mass_warnings,
}


def weight_estimate_advisory(project: Project, system: UnitSystem) -> str:
    """WTESTIMA's block caption: what it feeds, and how it compares.

    The sentence is the module's own (:data:`sloads.modules.weight_estimate.ADVISORY`)
    -- it is a fact about the program, not about this page, and the main GUI's
    Weight & Mass tab states the same thing beside its seed button. The numbers
    come from :func:`~sloads.modules.weight_estimate.compare_with_itemized` and
    are converted through :func:`~sloads.convert_results`, the same boundary
    every other figure on the page crosses, so an SI page cannot show a pound.

    A gap here is expected: the estimate is a GA correlation and the data base is
    a weighed airplane. It is shown plainly and never thresholded — there is no
    sourced figure for "too far", and inventing one would put a verdict on the
    page where C210-9 asked only for the comparison.
    """
    rows = compare_with_itemized(project)
    if not rows:
        return _ESTIMATE_ADVISORY
    values = [LoadValue(f"{r.quantity}|{part}", v, "lb", quantity="mass")
              for r in rows
              for part, v in (("est", r.estimated_lb), ("entered", r.entered_lb),
                              ("delta", r.delta_lb))]
    display = convert_results(
        [ConditionResult(title="", far_reference="", values=values)], system)[0].values
    parts = []
    for i, r in enumerate(rows):
        est, entered, delta = display[3 * i:3 * i + 3]
        parts.append(
            f"**{r.quantity}** — estimate {format_value(est.value)} {est.units} "
            f"against {format_value(entered.value)} {entered.units} entered "
            f"({delta.value:+.0f} {delta.units}, {r.delta_pct:+.1f} %)")
    return f"{_ESTIMATE_ADVISORY} " + "; ".join(parts) + "."


#: Per-module block captions, keyed the same way :data:`STATION_WARNINGS` is:
#: what a program *is* belongs to the program, so the page looks it up rather
#: than naming WTESTIMA in a renderer (gate G2).
MODULE_ADVISORIES: Dict[str, Callable[[Project, UnitSystem], str]] = {
    "weight_estimate": weight_estimate_advisory,
}


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
            if block.traceback:
                with st.expander("Traceback (for a bug report)"):
                    st.code(block.traceback)
            st.divider()
            continue

        st.caption(_ULT_NOTE if block.basis == ULTIMATE else _LIMIT_NOTE)
        if block.advisory:
            st.caption(block.advisory)
        for warning in block.warnings:
            st.warning(warning)
        st.dataframe(pd.DataFrame(list(block.rows)), hide_index=True,
                     width="stretch")
        # ``st.columns(0)`` raises, so a block with rows and no download would
        # take the whole page down with it -- a real mechanism with no live
        # trigger today, every result block that reaches here happening to carry
        # at least one artifact (code review 2026-08-24 §4.3, #89). Guarded
        # rather than left to that coincidence.
        if block.artifacts:
            columns = st.columns(len(block.artifacts))
            for column, artifact in zip(columns, block.artifacts):
                column.download_button(
                    f"Download {artifact.label}", artifact.payload,
                    file_name=artifact.file_name, mime=artifact.mime,
                    key=f"{key}.{artifact.file_name}", width="stretch")
        st.divider()


__all__ = [
    "LIMIT", "MODULE_ADVISORIES", "STATION_TABLES", "STATION_WARNINGS", "ULTIMATE",
    "Artifact", "ResultBlock", "StationTable", "page_artifacts", "render_results",
    "step_results", "weight_estimate_advisory",
]
