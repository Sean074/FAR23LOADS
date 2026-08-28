"""Export & Report — every output of the suite in one place.

Five kinds of hand-off, all recomputed live from the project inputs:

* **Project file** — the canonical ``project.json`` (the save file / single source
  of truth).
* **Load-case CSVs & text report** — per-module results for spreadsheets / records.
* **sbeam BDF cards** — wing / fuselage / tail / control-surface ``FORCE``/``MOMENT``
  cards (and the wing stick model) for the sbeam finite-element bridge, plus the
  **assembled full-span free-free deck** — the mission's primary loads
  deliverable, of which the per-component decks are analysis views — and the
  **CONM2/MASSSET mass model** that checks its inertia half independently.
* **Summary report (Step G8)** — the controlling document of the deliverable: a
  LaTeX ``.tex`` always, compiled to PDF when a TeX engine is available.
* **Combined bundle** — one ``.zip`` (or one multi-sheet ``.xlsx`` workbook, Step
  D8.2) of all of the above for archive / hand-off.
* **Export scope (Step D8.3)** — the fuselage/tail sbeam artifacts and the case
  index can be filtered to the Critical Loads tab's governing-case selection;
  wing and control-surface exports always include the full set (see the "Export
  scope" section's caption for why).

Nothing here depends on persisted result slices, so the exports always reflect the
current inputs. Channels whose inputs are absent are shown as disabled with a note.

One page of the multipage app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

import datetime as _dt
import io as _io
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

import streamlit as st

from app_shell.components import active_system, gate, page_header
from app_shell.widget_keys import widget_key
from sloads import Project, registry
from sloads import io as sloads_io
from sloads import workflow as wf
from sloads.export import mass_cards as mc
from sloads.export import sbeam_bridge as sb
from sloads.export.balanced_deck import balanced_deck
from sloads.export.pdf import ENGINE_ENV_VAR, compile_pdf, find_engine
from sloads.export.workbook import build_workbook
from sloads.modules.balance import build_balanced_cases
from sloads.modules.net_loads import torsion_axis_label, wing_lra
from sloads.report import module_text_report
from sloads.report.bundle import bundle_members, bundle_zip_bytes
from sloads.report.content import ComponentLoads, component_loads
from sloads.report.latex import render_report
from sloads.report.methods import (
    bdf_comment_block,
    csv_comment_block,
    methods_statement,
    strip_comment_lines,
)
from sloads.units import (
    Channel,
    convert_results,
    deliverable_units,
    system_name,
)


def _version(name: str) -> str:
    """Installed tool version for the methods statement's provenance block."""
    try:
        return _pkg_version(name)
    except PackageNotFoundError:  # pragma: no cover - source checkout without install
        return ""

# The header renders this page's consistency warnings (M4-14: an out-of-range
# per-case safety_factor would make the exported ULTIMATE loads unconservative).
# ``banner=False``: this page has never carried the applicability banner, and
# #82 changes what is *rendered here*, not what this page is.
project: Project = page_header(
    "export_report",
    caption=(
        "Project JSON, per-module load CSVs, and sbeam BDF cards — all recomputed "
        "from the current inputs, so exports are never stale."
    ),
    banner=False,
).project
_stem = (project.name or "project").strip().replace(" ", "_") or "project"

_CALC_ERRORS = (ValueError, ZeroDivisionError, KeyError, IndexError)


def _try(fn, *args, **kwargs):
    """Run a build/export call defensively; return its value or ``None``."""
    try:
        return fn(*args, **kwargs)
    except _CALC_ERRORS:
        return None


# --------------------------------------------------------------------------- #
# Compute every artifact once (used by both the per-channel buttons and the zip)
# --------------------------------------------------------------------------- #
# The bundle's unit system, resolved ONCE from the sidebar toggle and shared by
# every artifact below -- that single value is what makes "one bundle, one system"
# true by construction rather than by discipline, and it is what the in-band unit
# statement (M4-20 step 5) promises the reader. ``active_system()`` is the one read
# of the selection in the whole app layer (D-16).
_system = active_system()

project_json = sloads_io.project_to_json(project)
module_results = registry.run_all_modules(project)
step_by_module = {s.module: s for s in wf.STEPS if s.module}


def _module_label(mr) -> str:
    step = step_by_module.get(mr.module)
    return step.title if step else mr.module


_header_lines = [f"Project: {project.name or '(unnamed)'}"]
if project.engineer:
    _header_lines.append(f"Engineer: {project.engineer}")
if project.date:
    _header_lines.append(f"Date: {project.date}")
report_header = "\n".join(_header_lines)

# ``report/render.py`` is unit-agnostic by construction -- it reads each
# LoadValue's own units string -- so the *caller* converts, unlike the CSV writer
# which converts internally (M4-20 step 3). Handing it already-converted results
# AND a system would be a double conversion; these two paths are deliberately
# asymmetric, exactly as in ``cli.py``.
text_report = "\n\n".join(
    [report_header] + [
        module_text_report(_module_label(mr), convert_results(mr.conditions, _system))
        for mr in module_results
    ]
)


# sbeam component loads, defensively, through the one builder the summary report
# also uses (Step G8.4): the report and the files beside it in the bundle are
# then the same numbers by construction, not by two call sites agreeing. Wing
# results come back already transferred to the wing surface's loads reference
# axis (LRA), so every exported wing torsion is stated about that axis (in-band:
# span-CSV `MyyAxis`, BDF comments).
_components = component_loads(project)
_wing, _body, _tail, _control = (_components.wing, _components.body,
                                 _components.tail, _components.control)

# --------------------------------------------------------------------------- #
# Export scope (Step D8.3): honor the D5 Critical Loads tab's opt-out case
# selection. Case ids are copied verbatim from `envelope.critical.conditions`
# for fuselage/htail/vtail (body_loads.py, taildist.py), so the filter is exact
# there. Wing (`WingMassInput.cases`) and control-surface (aileron/flap/tab)
# results mint their own case ids on disjoint bands that never overlap with
# `envelope.critical` (see docs/30_future/00_backlog.md, "Unify select_wing/
# one_engine_out case identity") -- they always export the full set until that
# gap closes.
# Every case ID this run produced, so the deselected set can be named explicitly
# rather than described only as "filtered".
_all_case_ids = {
    r["ID"] for r in sb.case_index_rows_from(
        _wing or [], _body or [], _tail or [], _control,
        *(mr.conditions for mr in module_results),
    ) if r.get("ID")
}

_has_selection = bool(
    project.envelope is not None
    and project.envelope.critical is not None
    and project.envelope.critical.selected_case_ids
)
st.header("Export scope")
_scope = st.radio(
    "Scope for the fuselage/tail sbeam artifacts and the case index",
    ["Full set", "Governing set (Critical Loads selection)"],
    horizontal=True,
    key=widget_key("export_scope"),
    disabled=not _has_selection,
    help="Filters to the conditions kept checked on the Flight Envelope (V-n) "
         "page's Critical Loads tab. Wing and control-surface exports are "
         "unaffected (see caption below).",
)
if not _has_selection:
    st.caption(
        "No conditions are deselected on the **Critical Loads** tab (Flight Envelope "
        "(V-n) page), so there is "
        "nothing to filter yet — every export below is the full set."
    )
_selected_ids = (
    set(project.envelope.critical.selected_case_ids)
    if _has_selection and _scope.startswith("Governing")
    else None
)
# Methods & limitations (Step G8.3): built once, from the *resolved* export scope,
# and stamped into every channel -- so a CSV or BDF forwarded on its own still
# states that its loads are ULTIMATE, under what category, and what this tool does
# not do. It must come after the scope radio above: an analyst who receives a
# filtered set has to be told which cases were removed, by ID.
_tool_version = _version("sloads")
_deselected_ids = sorted(_all_case_ids - _selected_ids) if _selected_ids is not None else []
_scope_text = "governing case set" if _deselected_ids else "full case set"
# One timestamp per page render, shared by every channel. The pure code never
# reads the clock (a renderer that did would make two revisions of one report
# undiffable); the caller owns it, and this is the caller.
_generated = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
_stamp_kw = {"tool_version": _tool_version, "scope": _scope_text,
                 "deselected_case_ids": _deselected_ids or None, "system": _system,
                 "generated": _generated}
_methods = methods_statement(project, **_stamp_kw)
_csv_stamp = csv_comment_block(project, **_stamp_kw)
_bdf_stamp = bdf_comment_block(project, **_stamp_kw)

module_csvs = {mr.module: sloads_io.load_cases_csv(mr, header_comment=_csv_stamp,
                                                   system=_system)
               for mr in module_results}

if _selected_ids is not None:
    if _body:
        _body = sb.filter_by_selected_case_ids(_body, _selected_ids)
    if _tail:
        _tail = sb.filter_by_selected_case_ids(_tail, _selected_ids)
    if _wing or _control:
        st.caption(
            "Wing and control-surface case selection isn't wired to the Critical "
            "Loads page yet (see backlog — case-identity unification gap); those "
            "exports always include the full set regardless of this toggle."
        )

# (filename, content) for each available BDF/CSV sbeam artifact.
_bdf_artifacts: dict = {}
if _wing:
    _bdf_artifacts["wing_loads.bdf"] = _try(
        sb.force_moment_cards, _wing, header_comment=_bdf_stamp, system=_system) or ""
    _bdf_artifacts["wing_span_loads.csv"] = _try(
        sb.span_load_csv, _wing, header_comment=_csv_stamp, system=_system) or ""
    from sloads.derived_geometry import sob_station

    _bdf_artifacts["wing_stick.bdf"] = _try(
        sb.stick_model_bdf, _wing, header_comment=_bdf_stamp, system=_system,
        sob=sob_station(project)) or ""
if _body:
    _bdf_artifacts["fuselage_loads.bdf"] = _try(
        sb.body_force_moment_cards, _body, header_comment=_bdf_stamp,
        system=_system) or ""
    _bdf_artifacts["fuselage_span_loads.csv"] = _try(
        sb.body_span_load_csv, _body, header_comment=_csv_stamp, system=_system) or ""
    # Reported beside the FORCE set, never in it -- the span loads already carry
    # the carry-through reaction (M4-1).
    _bdf_artifacts["fuselage_fitting_loads.csv"] = _try(
        sb.body_fitting_load_csv, _body, header_comment=_csv_stamp,
        system=_system) or ""
if _tail:
    _bdf_artifacts["tail_loads.bdf"] = _try(
        sb.tail_force_moment_cards, _tail, header_comment=_bdf_stamp,
        system=_system) or ""
    _bdf_artifacts["tail_chordwise.csv"] = _try(
        sb.tail_chordwise_csv, _tail, header_comment=_csv_stamp, system=_system) or ""
if _control:
    _bdf_artifacts["control_surface_loads.bdf"] = _try(
        sb.control_surface_force_moment_cards, _control,
        header_comment=_bdf_stamp, system=_system) or ""
    _bdf_artifacts["control_surface_loads.csv"] = _try(
        sb.control_surface_csv, _control, header_comment=_csv_stamp,
        system=_system) or ""

# The assembled full-span deliverable and the mass model that checks its inertia
# half (decision D-R2). Both were page-only downloads until 2026-08-10: the
# mission's primary output travelled outside the bundle and outside the
# controlling document that states its basis (review F-D2). They ride the same
# `_bdf_stamp` and the same `_system` as every deck above, so a bundle still
# states one basis and one unit system.
_balanced_skipped: list = []
_balanced_cases = _try(build_balanced_cases, project, _balanced_skipped) or []
if _balanced_cases:
    _bdf_artifacts["balanced_airframe.bdf"] = _try(
        balanced_deck, project, header_comment=_bdf_stamp, system=_system,
        cases=_balanced_cases, skipped=_balanced_skipped) or ""
# The LRA beam model (step 12, note 24 R-1) -- the third deliverable. Its
# refusals (LraRefusal: no entered ref_axis_pct, no SOB, no outline, no
# spars, a strip-pair h-tail attachment) are stated absences, so _try's
# swallow-to-empty is right here: the row below simply shows no file, and the
# CLI route is where the refusal's own sentence is surfaced.
if _balanced_cases:
    from sloads.export.lra_model import lra_model_bdf as _lra_model_bdf

    _bdf_artifacts["lra_model.bdf"] = _try(
        _lra_model_bdf, project, header_comment=_bdf_stamp, system=_system,
        cases=_balanced_cases) or ""
if project.weight is not None and project.weight.items:
    _bdf_artifacts["mass_model.bdf"] = _try(
        mc.conm2_fragment, project, header_comment=_bdf_stamp,
        system=_system) or ""
    _bdf_artifacts["mass_check.bdf"] = _try(
        mc.mass_check_deck, project, header_comment=_bdf_stamp,
        system=_system) or ""
    _bdf_artifacts["inertia_only.bdf"] = _try(
        mc.inertia_only_cards, project, header_comment=_bdf_stamp,
        system=_system) or ""

# Case-index table (Step D1): ID -> full definition, from every module's own
# ConditionResults (covers engine/landing/SELECT) plus the sbeam component
# deliverables recomputed above (covers the full wing/body/tail/control sets).
case_index_csv = sb.case_index_csv_from(
    # Deck-exported results first: first-seen defines a row's flight condition,
    # and the row states the condition its cards were computed at (see
    # ``case_index_rows_from``).
    _wing or [], _body or [], _tail or [], _control,
    *(mr.conditions for mr in module_results),
    header_comment=_csv_stamp,
    # The assembled deck's own cases fill the second deck-number column; a case
    # is quoted in a column only when it is actually in that deck (note 17).
    assembled=_balanced_cases,
)

# The governing safety-factor table (M4-8 / G-11): the authority every SF in this
# bundle is derived from, travelling as its own stamped channel so a deck's SF=
# marker can be traced without the report.
safety_factors_csv = sb.safety_factors_csv(project, header_comment=_csv_stamp)

# The gear interface load definition (G-12): the boundary condition a gear
# analysis starts from, which no other channel in this bundle states. Absent --
# not empty -- on a project with no gear geometry, so the bundle never carries a
# header-only file that reads as "no gear loads".
gear_report_csv = _try(sb.gear_report_csv, project, _csv_stamp, _system) or ""

# Summary report (Step G8): rendered from the *scoped* component loads and the
# module results already computed above, so the document describes exactly the
# files it ships beside -- same numbers, same unit system, same case set.
_report_tex = _try(
    render_report, project, system=_system, generated=_generated,
    tool_version=_tool_version, scope=_scope_text,
    deselected_case_ids=_deselected_ids or None,
    module_results=module_results,
    components=ComponentLoads(wing=_wing or [], body=_body or [], tail=_tail or [],
                              control=_control, critical=_components.critical),
) or ""


# --------------------------------------------------------------------------- #
# 1. Project file + combined bundle
# --------------------------------------------------------------------------- #
st.header("Project file & bundle")


def _units_caption() -> str:
    """The system this bundle will be written in, stated beside the downloads.

    Derived from the same ``_system`` the writers were given and from
    ``deliverable_units`` itself, so the caption cannot drift from the files: it
    is the on-page half of the in-band statement each file carries (M4-20 step 5;
    ``GUI_design.md`` §7).
    """
    human = deliverable_units(_system, Channel.HUMAN)
    solver = deliverable_units(_system, Channel.SOLVER)

    def listed(u):
        return f"{u.force.label}, {u.length.label}, {u.moment.label}, {u.pressure.label}"

    name = system_name(_system)
    sets = (
        f"in **{listed(human)}**" if listed(human) == listed(solver) else
        f"human-readable files in **{listed(human)}**, the sbeam decks in "
        f"**{listed(solver)}** (a deck in N and mm needs N·mm moments)"
    )
    return (
        f"Every file below is written in **{name}** — {sets}. Airspeed stays KEAS "
        "and altitude stays ft in both systems. Change it with the Imperial/SI "
        "toggle in the sidebar; loads are ULTIMATE in every export."
    )


st.caption(_units_caption())
c1, c2, c3 = st.columns(3)
c1.download_button("💾 Save project.json", project_json,
                   file_name=f"{_stem}.json", mime="application/json")


def _zip_bundle() -> bytes:
    """The bundle, assembled by its one owner.

    The member list is :func:`sloads.report.bundle.bundle_members` and not this
    function: a member named here and nowhere else is a file that travels
    without a basis, which is what CR-C-1 found three times over. That module is
    pure, so ``tests/test_bundle_manifest.py`` reads the same namelist the user
    downloads and holds it against Appendix A. Add a file there, with its
    manifest row -- never here.
    """
    _pdf = st.session_state.get("report_pdf_bytes")
    return bundle_zip_bytes(bundle_members(
        _stem,
        project_json=project_json,
        text_report=text_report,
        module_csvs=module_csvs,
        case_index_csv=case_index_csv,
        safety_factors_csv=safety_factors_csv,
        gear_report_csv=gear_report_csv,
        methods=_methods,
        report_tex=_report_tex or "",
        report_pdf=(_pdf if st.session_state.get("report_pdf_key") == _report_tex
                    else None),
        sbeam_artifacts=_bdf_artifacts,
    ))


c2.download_button("📦 Download all (.zip)", _zip_bundle(),
                   file_name=f"{_stem}_loads_bundle.zip", mime="application/zip")


def _workbook_bytes() -> bytes:
    project_info = {
        "Name": project.name or "(unnamed)",
        "Engineer": project.engineer or "",
        "Date": project.date or "",
        "Category": "Concept" if project.is_concept else "GA (FAR 23)",
    }
    # The workbook's in-band unit statement (M4-20 step 5) is `build_workbook`'s
    # own, stated PER SHEET from this one `_system` (review m14): the .xlsx has
    # no comment rows to carry the CSV/BDF stamp, and one workbook-level
    # statement would be wrong for the solver-channel span sheets below.
    module_labels = {mr.module: _module_label(mr) for mr in module_results}
    span_csvs = {
        title: _bdf_artifacts[key]
        for title, key in [
            ("Wing Span Loads", "wing_span_loads.csv"),
            ("Fuselage Span Loads", "fuselage_span_loads.csv"),
            ("Fuselage Fitting Loads", "fuselage_fitting_loads.csv"),
            ("Tail Chordwise", "tail_chordwise.csv"),
            ("Control Surface Loads", "control_surface_loads.csv"),
        ]
        if _bdf_artifacts.get(key)
    }
    return build_workbook(project_info, module_csvs, module_labels, case_index_csv,
                          span_csvs, methods=_methods, system=_system)


c3.download_button(
    "📊 Download workbook (.xlsx)", _workbook_bytes(),
    file_name=f"{_stem}_loads_bundle.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# --------------------------------------------------------------------------- #
# 2. Summary report (Step G8)
# --------------------------------------------------------------------------- #
st.header("Summary report")
st.caption(
    "The controlling document of this deliverable: the airplane, its envelope, "
    "the FAR conditions analysed and every governing **ULTIMATE** load with its "
    "safety factor, plus the methods & limitations statement and a manifest of "
    "the files above. The LaTeX source is the primary artifact and always "
    "downloads; the PDF is compiled here when a TeX engine is available."
)
if not _report_tex:
    gate("The report could not be built from the current inputs — start from the "
         "**Project Dashboard** and work the workflow left-to-right.",
         "dashboard", kind="info")
else:
    _r1, _r2 = st.columns(2)
    _r1.download_button("📘 Summary report (.tex)", _report_tex,
                        file_name=f"{_stem}_summary_report.tex",
                        mime="application/x-tex")
    _engine = find_engine()
    if _engine is None:
        st.caption(
            "No TeX engine found on this machine, so no PDF can be compiled here. "
            "The `.tex` above is complete and compiles anywhere (`tectonic`, "
            "`latexmk` or `pdflatex`); set the `"
            + ENGINE_ENV_VAR + "` environment variable to point at a specific one."
        )
    else:
        if _r2.button("🖨️ Compile PDF", help=f"Using {_engine}"):
            with st.spinner("Compiling the report…"):
                _result = compile_pdf(_report_tex)
            st.session_state["report_pdf_bytes"] = _result.pdf
            st.session_state["report_pdf_key"] = _report_tex
            st.session_state["report_pdf_log"] = _result.log
        _pdf = st.session_state.get("report_pdf_bytes")
        _fresh = st.session_state.get("report_pdf_key") == _report_tex
        if _pdf and _fresh:
            st.download_button("📕 Summary report (.pdf)", _pdf,
                               file_name=f"{_stem}_summary_report.pdf",
                               mime="application/pdf")
            st.caption(f"Compiled with `{_engine}`; the PDF is also included in the "
                       "bundle .zip above.")
        elif _pdf and not _fresh:
            st.caption("The inputs changed since the last compile — press "
                       "**Compile PDF** again for an up-to-date document.")
        elif st.session_state.get("report_pdf_log"):
            # A compile failure is a caption, never an exception: the .tex is the
            # deliverable and is already downloadable above (decision G8-1).
            st.warning("The report did not compile. The `.tex` above is still "
                       "complete — compile it elsewhere, or read the engine log:")
            st.code(st.session_state["report_pdf_log"][-2000:], language="text")

# --------------------------------------------------------------------------- #
# 3. Load-case CSVs + combined text report
# --------------------------------------------------------------------------- #
st.header("Load cases & report")
if not module_results:
    gate("No module has the inputs it needs yet — start from the **Project Dashboard** "
         "and work the workflow left-to-right.", "dashboard", kind="info")
else:
    st.download_button("📄 Combined text report (all modules)", text_report,
                       file_name=f"{_stem}_report.txt", mime="text/plain")
    with st.expander(f"Per-module load-case CSVs ({len(module_results)} modules)"):
        for mr in module_results:
            csv = module_csvs[mr.module]
            st.download_button(f"{_module_label(mr)} (CSV)", csv,
                               file_name=f"{_stem}_{mr.module}.csv", mime="text/csv",
                               key=f"csv_{mr.module}", disabled=not csv)

# --------------------------------------------------------------------------- #
# 4. sbeam BDF cards
# --------------------------------------------------------------------------- #
st.header("sbeam BDF export")
st.caption(
    "FORCE/MOMENT cards (and the wing stick model) for the sbeam FE bridge. "
    f"Wing torsion My/Myy is stated about the **{torsion_axis_label(wing_lra(project))}** "
    "(the wing's loads reference axis, set on the Geometry page); the axis "
    "travels in-band in the span-CSV `MyyAxis` column and the BDF `$` comments."
)


def _bdf_row(label: str, *names):
    """Render one component's export buttons, disabled if its inputs are absent."""
    st.subheader(label)
    present = [n for n in names if _bdf_artifacts.get(n)]
    if not present:
        st.caption("Not available — set the upstream inputs for this component first.")
        return
    cols = st.columns(len(names))
    for col, name in zip(cols, names):
        content = _bdf_artifacts.get(name, "")
        mime = "text/csv" if name.endswith(".csv") else "text/plain"
        col.download_button(name, content, file_name=f"{_stem}_{name}", mime=mime,
                            key=f"bdf_{name}", disabled=not content)


_bdf_row("Wing", "wing_loads.bdf", "wing_span_loads.csv", "wing_stick.bdf")
_bdf_row("Fuselage", "fuselage_loads.bdf", "fuselage_span_loads.csv",
         "fuselage_fitting_loads.csv")
if _body:
    if any(getattr(r, "closure_artifact", False) for r in _body):
        st.caption(
            "⚠️ **Fuselage closure artifact.** The wing spar stations could not be "
            "derived, so the unbalanced moment was reacted by a correction spread "
            "over the whole body rather than the wing carry-through: the beam "
            "closes, but the correction has no physical source and no fitting "
            "loads are reported. The caveat is stamped as `$ CAVEAT:` comments in "
            "`fuselage_loads.bdf`. Define the wing spar chord fractions on the "
            "**Configuration & Layout** page to get the Ch 15 reaction."
        )
    else:
        st.caption(
            "The body distribution closes both ΣFz and ΣM at the front/rear spar "
            "attachments (Ref 1 Ch 15 p103); each `fuselage_loads.bdf` block "
            "states both residuals. `fuselage_fitting_loads.csv` reports the "
            "wing-attach fitting loads — the span loads already carry them, so do "
            "not apply them on top."
            + (" Spar stations are **assumed** (default chord fractions)."
               if any(getattr(r, "spars_assumed", False) for r in _body) else "")
        )
_bdf_row("Tail", "tail_loads.bdf", "tail_chordwise.csv")
_bdf_row("Control surfaces", "control_surface_loads.bdf", "control_surface_loads.csv")
_bdf_row("Assembled airframe (free-free)", "balanced_airframe.bdf")
_bdf_row("LRA beam model", "lra_model.bdf")
if _balanced_cases:
    st.caption(
        f"The mission's primary loads deliverable: {len(_balanced_cases)} "
        "`SUBCASE`s, both wings, aero and inertia together on a statically "
        "determinate support — the recovered reaction *is* the residual, so "
        "'reactions ≈ 0' is the free-free equilibrium proof. Per-case load "
        "factors, residuals and handed twin pairs are tabulated in the summary "
        "report; the **Balanced Cases** page shows the same numbers live."
        + (f" {len(_balanced_skipped)} SELECT condition(s) did not assemble — the "
           "deck and the report both name them." if _balanced_skipped else "")
    )
else:
    st.caption(
        "No condition assembles into a balanced case yet — one needs a V-n point "
        "**and** a payload loading the itemized weight database can produce. The "
        "summary report states the same absence rather than omitting it."
    )
_bdf_row("Mass model (CONM2)", "mass_model.bdf", "mass_check.bdf",
         "inertia_only.bdf")
if _bdf_artifacts.get("mass_model.bdf"):
    st.caption(
        "**Do not apply the mass model together with the FORCE/MOMENT decks** — "
        "those cards are the *total* applied load and already contain inertia. "
        "`mass_model.bdf` is the fragment (CONM2 + one MASSSET per payload case), "
        "`mass_check.bdf` the self-contained runnable deck (MASSSET + GRAV, no "
        "load cards), `inertia_only.bdf` sloads' own inertia set for comparison "
        "only. Which payload case is which MASSSET is tabulated in the report."
    )

# --------------------------------------------------------------------------- #
# 5. Case-index table (Step D1)
# --------------------------------------------------------------------------- #
st.header("Case index")
st.caption("Every structured case ID this run produced, mapped to its full definition.")
if case_index_csv.strip():
    import csv as _csv_mod

    rows = list(_csv_mod.DictReader(_io.StringIO(strip_comment_lines(case_index_csv))))
    st.dataframe(rows, width="stretch", hide_index=True)
    st.download_button("Case index (CSV)", case_index_csv,
                       file_name=f"{_stem}_case_index.csv", mime="text/csv")
else:
    gate("No structured case IDs yet — run a component module first.",
         "dashboard", kind="info")
