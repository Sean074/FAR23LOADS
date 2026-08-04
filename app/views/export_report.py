"""Export & Report — every output of the suite in one place.

Five kinds of hand-off, all recomputed live from the project inputs:

* **Project file** — the canonical ``project.json`` (the save file / single source
  of truth).
* **Load-case CSVs & text report** — per-module results for spreadsheets / records.
* **sbeam BDF cards** — wing / fuselage / tail / control-surface ``FORCE``/``MOMENT``
  cards (and the wing stick model) for the sbeam finite-element bridge.
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

import io as _io
import zipfile
from importlib.metadata import PackageNotFoundError, version as _pkg_version

import streamlit as st

from components import gate

from sloads import Project, consistency_warnings, registry
from sloads import io as sloads_io
from sloads import workflow as wf
from sloads.export import sbeam_bridge as sb
from sloads.export.workbook import build_workbook
from sloads.modules.aileron import build_aileron
from sloads.modules.body_loads import build_body_loads
from sloads.modules.flap import build_flap
from sloads.modules.net_loads import (
    build_net_loads,
    loads_ref_axis_results,
    torsion_axis_label,
    wing_lra,
)
from sloads.modules.tab import build_tabs
from sloads.modules.taildist import build_tail_chordwise
from sloads.report import module_text_report
from sloads.report.methods import (
    bdf_comment_block,
    csv_comment_block,
    methods_statement,
    strip_comment_lines,
)


def _version(name: str) -> str:
    """Installed tool version for the methods statement's provenance block."""
    try:
        return _pkg_version(name)
    except PackageNotFoundError:  # pragma: no cover - source checkout without install
        return ""

st.title("Export & Report")
st.caption(
    "Project JSON, per-module load CSVs, and sbeam BDF cards — all recomputed from "
    "the current inputs, so exports are never stale."
)

project: Project = st.session_state.get("project", Project(name=""))
_stem = (project.name or "project").strip().replace(" ", "_") or "project"

# Consistency warnings tagged for this page (M4-14: an out-of-range per-case
# safety_factor would make the exported ULTIMATE loads unconservative).
for _w in consistency_warnings(project):
    if _w.page == "export_report":
        st.warning(_w.message)

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

text_report = "\n\n".join(
    [report_header] + [module_text_report(_module_label(mr), mr.conditions) for mr in module_results]
)


# sbeam component loads, defensively. Wing results are transferred to the wing
# surface's loads reference axis (LRA) at this boundary -- every exported wing
# torsion is stated about that axis (in-band: span-CSV `MyyAxis`, BDF comments).
_net = _try(build_net_loads, project)
_wing = loads_ref_axis_results(project, _net.wing_net) if _net is not None else None
_body = _try(build_body_loads, project)
_tail = _try(build_tail_chordwise, project)
_control = []
for _fn in (build_aileron, build_flap, build_tabs):
    _control += (_try(_fn, project) or [])

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
        *(mr.conditions for mr in module_results), _wing or [], _body or [],
        _tail or [], _control,
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
_stamp_kw = dict(tool_version=_tool_version, scope=_scope_text,
                 deselected_case_ids=_deselected_ids or None)
_methods = methods_statement(project, **_stamp_kw)
_csv_stamp = csv_comment_block(project, **_stamp_kw)
_bdf_stamp = bdf_comment_block(project, **_stamp_kw)

module_csvs = {mr.module: sloads_io.load_cases_csv(mr, header_comment=_csv_stamp)
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
    _bdf_artifacts["wing_loads.bdf"] = _try(sb.force_moment_cards, _wing) or ""
    _bdf_artifacts["wing_span_loads.csv"] = _try(sb.span_load_csv, _wing, header_comment=_csv_stamp) or ""
    _bdf_artifacts["wing_stick.bdf"] = _try(sb.stick_model_bdf, _wing) or ""
if _body:
    _bdf_artifacts["fuselage_loads.bdf"] = _try(sb.body_force_moment_cards, _body) or ""
    _bdf_artifacts["fuselage_span_loads.csv"] = _try(sb.body_span_load_csv, _body, header_comment=_csv_stamp) or ""
    # Reported beside the FORCE set, never in it -- the span loads already carry
    # the carry-through reaction (M4-1).
    _bdf_artifacts["fuselage_fitting_loads.csv"] = _try(
        sb.body_fitting_load_csv, _body, header_comment=_csv_stamp) or ""
if _tail:
    _bdf_artifacts["tail_loads.bdf"] = _try(sb.tail_force_moment_cards, _tail) or ""
    _bdf_artifacts["tail_chordwise.csv"] = _try(sb.tail_chordwise_csv, _tail, header_comment=_csv_stamp) or ""
if _control:
    _bdf_artifacts["control_surface_loads.bdf"] = _try(sb.control_surface_force_moment_cards, _control) or ""
    _bdf_artifacts["control_surface_loads.csv"] = _try(
        sb.control_surface_csv, _control, header_comment=_csv_stamp) or ""

# Case-index table (Step D1): ID -> full definition, from every module's own
# ConditionResults (covers engine/landing/SELECT) plus the sbeam component
# deliverables recomputed above (covers the full wing/body/tail/control sets).
case_index_csv = sb.case_index_csv_from(
    *(mr.conditions for mr in module_results), _wing or [], _body or [], _tail or [], _control,
    header_comment=_csv_stamp,
)


# --------------------------------------------------------------------------- #
# 1. Project file + combined bundle
# --------------------------------------------------------------------------- #
st.header("Project file & bundle")
c1, c2, c3 = st.columns(3)
c1.download_button("💾 Save project.json", project_json,
                   file_name=f"{_stem}.json", mime="application/json")


def _zip_bundle() -> bytes:
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{_stem}.json", project_json)
        if text_report.strip():
            z.writestr(f"{_stem}_report.txt", text_report)
        for module, csv in module_csvs.items():
            if csv:
                z.writestr(f"load_cases/{_stem}_{module}.csv", csv)
        if case_index_csv.strip():
            z.writestr(f"{_stem}_case_index.csv", case_index_csv)
        # The bundle's own controlling statement -- readable without opening a CSV.
        z.writestr("METHODS.txt", _methods)
        for name, content in _bdf_artifacts.items():
            if content:
                z.writestr(f"sbeam/{_stem}_{name}", content)
    return buf.getvalue()


c2.download_button("📦 Download all (.zip)", _zip_bundle(),
                   file_name=f"{_stem}_loads_bundle.zip", mime="application/zip")


def _workbook_bytes() -> bytes:
    project_info = {
        "Name": project.name or "(unnamed)",
        "Engineer": project.engineer or "",
        "Date": project.date or "",
        "Category": "Concept" if project.is_concept else "GA (FAR 23)",
    }
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
                          span_csvs, methods=_methods)


c3.download_button(
    "📊 Download workbook (.xlsx)", _workbook_bytes(),
    file_name=f"{_stem}_loads_bundle.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# --------------------------------------------------------------------------- #
# 2. Load-case CSVs + combined text report
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
# 3. sbeam BDF cards
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

# --------------------------------------------------------------------------- #
# 4. Case-index table (Step D1)
# --------------------------------------------------------------------------- #
st.header("Case index")
st.caption("Every structured case ID this run produced, mapped to its full definition.")
if case_index_csv.strip():
    import csv as _csv_mod

    rows = list(_csv_mod.DictReader(_io.StringIO(strip_comment_lines(case_index_csv))))
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.download_button("Case index (CSV)", case_index_csv,
                       file_name=f"{_stem}_case_index.csv", mime="text/csv")
else:
    gate("No structured case IDs yet — run a component module first.",
         "dashboard", kind="info")
