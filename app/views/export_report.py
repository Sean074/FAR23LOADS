"""Export & Report — every output of the suite in one place.

Four kinds of hand-off, all recomputed live from the project inputs:

* **Project file** — the canonical ``project.json`` (the save file / single source
  of truth).
* **Load-case CSVs & text report** — per-module results for spreadsheets / records.
* **sbeam BDF cards** — wing / fuselage / tail / control-surface ``FORCE``/``MOMENT``
  cards (and the wing stick model) for the sbeam finite-element bridge.
* **Combined bundle** — one ``.zip`` of all of the above for archive / hand-off.

Nothing here depends on persisted result slices, so the exports always reflect the
current inputs. Channels whose inputs are absent are shown as disabled with a note.

One page of the multipage app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

import io as _io
import zipfile

import streamlit as st

from farloads import Project, registry
from farloads import io as farloads_io
from farloads import workflow as wf
from farloads.export import sbeam_bridge as sb
from farloads.modules.aileron import build_aileron
from farloads.modules.body_loads import build_body_loads
from farloads.modules.flap import build_flap
from farloads.modules.net_loads import build_net_loads
from farloads.modules.tab import build_tabs
from farloads.modules.taildist import build_tail_chordwise
from farloads.report import module_text_report

st.title("Export & Report")
st.caption(
    "Project JSON, per-module load CSVs, and sbeam BDF cards — all recomputed from "
    "the current inputs, so exports are never stale."
)

project: Project = st.session_state.get("project", Project(name=""))
_stem = (project.name or "project").strip().replace(" ", "_") or "project"

_CALC_ERRORS = (ValueError, ZeroDivisionError, KeyError, IndexError)


def _try(fn, *args):
    """Run a build/export call defensively; return its value or ``None``."""
    try:
        return fn(*args)
    except _CALC_ERRORS:
        return None


# --------------------------------------------------------------------------- #
# Compute every artifact once (used by both the per-channel buttons and the zip)
# --------------------------------------------------------------------------- #
project_json = farloads_io.project_to_json(project)
module_results = registry.run_all_modules(project)
step_by_module = {s.module: s for s in wf.STEPS if s.module}


def _module_label(mr) -> str:
    step = step_by_module.get(mr.module)
    return step.title if step else mr.module


text_report = "\n\n".join(
    module_text_report(_module_label(mr), mr.conditions) for mr in module_results
)
module_csvs = {mr.module: farloads_io.load_cases_csv(mr) for mr in module_results}

# sbeam component loads, defensively.
_net = _try(build_net_loads, project)
_wing = _net.wing_net if _net is not None else None
_body = _try(build_body_loads, project)
_tail = _try(build_tail_chordwise, project)
_control = []
for _fn in (build_aileron, build_flap, build_tabs):
    _control += (_try(_fn, project) or [])

# (filename, content) for each available BDF/CSV sbeam artifact.
_bdf_artifacts: dict = {}
if _wing:
    _bdf_artifacts["wing_loads.bdf"] = _try(sb.force_moment_cards, _wing) or ""
    _bdf_artifacts["wing_span_loads.csv"] = _try(sb.span_load_csv, _wing) or ""
    _bdf_artifacts["wing_stick.bdf"] = _try(sb.stick_model_bdf, _wing) or ""
if _body:
    _bdf_artifacts["fuselage_loads.bdf"] = _try(sb.body_force_moment_cards, _body) or ""
    _bdf_artifacts["fuselage_span_loads.csv"] = _try(sb.body_span_load_csv, _body) or ""
if _tail:
    _bdf_artifacts["tail_loads.bdf"] = _try(sb.tail_force_moment_cards, _tail) or ""
    _bdf_artifacts["tail_chordwise.csv"] = _try(sb.tail_chordwise_csv, _tail) or ""
if _control:
    _bdf_artifacts["control_surface_loads.bdf"] = _try(sb.control_surface_force_moment_cards, _control) or ""
    _bdf_artifacts["control_surface_loads.csv"] = _try(sb.control_surface_csv, _control) or ""


# --------------------------------------------------------------------------- #
# 1. Project file + combined bundle
# --------------------------------------------------------------------------- #
st.header("Project file & bundle")
c1, c2 = st.columns(2)
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
        for name, content in _bdf_artifacts.items():
            if content:
                z.writestr(f"sbeam/{_stem}_{name}", content)
    return buf.getvalue()


c2.download_button("📦 Download all (.zip)", _zip_bundle(),
                   file_name=f"{_stem}_loads_bundle.zip", mime="application/zip")

# --------------------------------------------------------------------------- #
# 2. Load-case CSVs + combined text report
# --------------------------------------------------------------------------- #
st.header("Load cases & report")
if not module_results:
    st.info("No module has the inputs it needs yet — fill in the Define pages first.")
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
st.caption("FORCE/MOMENT cards (and the wing stick model) for the sbeam FE bridge.")


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
_bdf_row("Fuselage", "fuselage_loads.bdf", "fuselage_span_loads.csv")
_bdf_row("Tail", "tail_loads.bdf", "tail_chordwise.csv")
_bdf_row("Control surfaces", "control_surface_loads.bdf", "control_surface_loads.csv")
