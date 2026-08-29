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
from sloads.frames import AIRPLANE_DATUM, GROUND_LINE, caption
from sloads.models import ConditionResult, LoadValue, Project
from sloads.modules.body_loads import body_load_rows, build_body_loads
from sloads.modules.net_loads import build_net_loads, wing_load_rows
from sloads.modules.taildist import build_tail_chordwise
from sloads.modules.weight_estimate import ADVISORY as _ESTIMATE_ADVISORY
from sloads.modules.weight_estimate import compare_with_itemized
from sloads.report import (
    SUMMARY_GROUP_BY,
    csv_comment_block,
    format_value,
    module_text_report,
    summary_rows,
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
    #: Column to group the rows by on screen (#95, C210-27): a one-line-per-
    #: case shape renders one sub-table per value of this column (per
    #: component, the M2-4 Results Review layout), each dropping the quantity
    #: columns that whole group leaves at "—". The artifacts keep the rows
    #: flat -- same rows, same columns, one CSV.
    group_by: str = ""


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

    # The one summary-shape dispatch (#95, C210-8/27): the same rows the CSV
    # below is written from, so the screen and the export cannot print one
    # data set two ways. SELECT renders one line per case with its per-case
    # SF (the owner directive); WTENV one row per weight/station point;
    # everything else the data-shaped generic table.
    rows = summary_rows(name, display)
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
                       advisory=advisory(project, system) if advisory else "",
                       group_by=SUMMARY_GROUP_BY.get(name, ""))


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


def select_inertia_advisory(project: Project, _system: UnitSystem) -> str:
    """SELECT's block caption: the search scope, and which inertias are estimates.

    The scope sentence is C210-26's GUI half (#94): the candidate pool per
    category is the entire V-n matrix, filtered only by condition label, and no
    single sentence on the page said so -- "PHAA (case 118)" gave the user no
    way to know the other loadings were considered rather than skipped. The
    theory half landed in ``00_theory_sources.md``'s select row in-session.

    Inertia half (#95, C210-25):

    The checked-maneuver Iyy and the side-gust default IZZ are SELECT.BAS's
    statistical rod estimates -- faithful to the original, and measured +34 %
    / +49 % over WTONECG's database values on the C210 (about 10 % on the
    checked-man tail load, conservative direction) with nothing on the page
    saying an estimate was in play. Said as a caption, not a warning: the
    numbers are behaving exactly as designed (the C210-9 argument). The IZZ
    override's own field carries the rod default beside it on the Geometry
    page (``field_registry``); the rod numbers here are quoted from the same
    resolvers the calc uses, and the database comparison from ``Project.mass``
    when WTONECG has run. Inertias are quoted in slug-ft^2 in either unit
    system -- neither channel converts them.
    """
    from sloads.constants import LBIN2_PER_SLUGFT2
    from sloads.modules.select import default_side_gust_izz

    text = ("Each critical condition is the governing case searched over the "
            "full V-n matrix — all loadings, CGs and altitudes. "
            "Inertias: the checked-maneuver pitch inertia Iyy "
            "(0.44\u00b7W\u00b7L\u00b2/12g) and the side-gust yaw inertia IZZ "
            "(wing + fuselage slender rods; overridable on the Geometry page's "
            "v-tail IZZ field) are SELECT.BAS **statistical rod estimates**, "
            "not the item data base.")
    vt = project.vtail_loads
    if vt is not None and vt.izz_slugft2:
        text += (f" IZZ here is the typed override, {vt.izz_slugft2:,.0f} "
                 "slug-ft\u00b2.")
    else:
        izz_rod = default_side_gust_izz(project)
        if izz_rod is not None:
            text += f" The rod IZZ in use is {izz_rod:,.0f} slug-ft\u00b2."
    mass = project.mass
    if mass is not None and mass.cases:
        heaviest = max(mass.cases, key=lambda c: c.weight_lb)
        text += (" For comparison, WTONECG's item-database inertias at the "
                 f"heaviest loading ({heaviest.name}): Iyy "
                 f"{heaviest.iyy / LBIN2_PER_SLUGFT2:,.0f}, IZZ "
                 f"{heaviest.izz / LBIN2_PER_SLUGFT2:,.0f} slug-ft\u00b2.")
    return text


#: Per-module block captions, keyed the same way :data:`STATION_WARNINGS` is:
#: what a program *is* belongs to the program, so the page looks it up rather
#: than naming WTESTIMA in a renderer (gate G2).
def taildist_spanwise_advisory(_project: Project, _system: UnitSystem) -> str:
    """TAILDIST's block caption: where the spanwise deliverable lives (#94).

    C210-33: the spanwise empennage table (per-station shear/bending/torsion on
    the load reference axis) is deliberately not an oracle page -- OG-2 derives
    the oracle set as the .BAS-backed steps plus their input producers, and
    ``tail_span_loads`` has ``bas=None`` (a modern deliverable, not a McMaster
    program). The scope rule is right, but nothing here said the deliverable
    exists elsewhere, so the owner searched this GUI for it.
    """
    return ("Chordwise distributions only. The spanwise station table -- "
            "per-station shear, bending and torsion on the load reference "
            "axis -- is the main GUI's **Tail Span Loads** page and the export "
            "decks; it is not a McMaster program, so it has no oracle page.")


def landing_frame_advisory(_project: Project, _system: UnitSystem) -> str:
    """LANDLOAD's block caption: which frame each row is stated in (note 38 GF-7).

    LANDLOAD prints its whole matrix twice and says which frame each table is in;
    this GUI rendered the numbers with no frame at all, while the export deck
    consumed the other one -- a reader moving between them had no stated bridge,
    and the two differ by a rotation of the ground angle. The words are the
    manual's own, from the one owner that has them
    (:func:`sloads.frames.caption`), so the two GUIs cannot come to say it
    differently.
    """
    return (f"Every row names its frame. The **delivered** per-wheel forces and "
            f"their points of application, the NR/NV/ND load factors and the "
            f"datum unbalanced moments are {caption(AIRPLANE_DATUM)} -- the "
            f"frame the export deck applies. The primed set (VMP/DMP/SMP, "
            f"VNP/DNP/SNP, NVP/NDP/NS and the unbalanced moments without "
            f"'(datum)') is {caption(GROUND_LINE)}, which is how the manual "
            f"prints it; it is in the text download and, by design, not in the "
            f"CSV.")


MODULE_ADVISORIES: Dict[str, Callable[[Project, UnitSystem], str]] = {
    "weight_estimate": weight_estimate_advisory,
    "select": select_inertia_advisory,
    "taildist": taildist_spanwise_advisory,
    "landing": landing_frame_advisory,
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
def _block_frames(block: ResultBlock) -> List[Tuple[str, pd.DataFrame]]:
    """The dataframes one block renders: the whole table, or one per
    ``group_by`` value (#95, C210-27).

    A grouped block (SELECT) renders one sub-table per component, each with
    the quantity columns that component actually fills -- the union columns a
    group leaves entirely at "\u2014" are dropped, and the grouping column
    itself becomes the sub-table's title. Same rows as the CSV artifact either
    way; this is presentation, not a second shape.
    """
    frame = pd.DataFrame(list(block.rows))
    if not block.group_by or block.group_by not in frame.columns:
        return [("", frame)]
    out: List[Tuple[str, pd.DataFrame]] = []
    for value in dict.fromkeys(frame[block.group_by]):
        sub = frame[frame[block.group_by] == value].drop(columns=[block.group_by])
        keep = [c for c in sub.columns if not (sub[c] == "\u2014").all()]
        out.append((str(value), sub[keep]))
    return out


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
        for subtitle, frame in _block_frames(block):
            if subtitle:
                st.markdown(f"**{subtitle}**")
            st.dataframe(frame, hide_index=True, width="stretch")
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
    "select_inertia_advisory", "step_results", "taildist_spanwise_advisory",
    "weight_estimate_advisory",
]
