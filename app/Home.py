"""FAR 23 LOADS — multipage entrypoint.

Run with:  streamlit run app/Home.py

The whole app is one reloadable ``project.json`` carried in ``st.session_state``.
Navigation is built explicitly from :mod:`farloads.workflow` (the single source of
truth for the step graph) and grouped into the six Phase-D workflow sections the
user moves through left-to-right:

    1 · Start ──▶ 2 · Airplane ──▶ 3 · Envelopes & Critical Conditions ──▶
    4 · Analysis ──▶ 5 · Loads Plots ──▶ 6 · Export

Using ``st.navigation`` (rather than the implicit ``pages/`` directory) means page
order and titles come from the workflow metadata, not filename numbers -- so there
is no numeric-prefix coupling and no duplicate-index collisions. A section with no
steps yet (``Loads Plots``, pending Step D7) is omitted from the sidebar rather
than shown empty.

This module also owns the **global unit-system toggle** and the **global project
file widget** (Step D3, decision D-3): Imperial/SI selection (``st.session_state
["unit_system"]``, read by every view via :func:`farloads.units.convert_results`)
plus Open/Save against a local ``projects/`` directory, New-from-example, and the
browser upload/download fallback. Both are built once, here, above ``pg.run()``,
so they appear in the sidebar on every page regardless of which view is active.
Calc and ``project.json`` stay Imperial-only (canonical internal units); SI is a
presentation choice applied at each view's render boundary. Airspeed (KEAS) and
altitude (ft) are aviation-standard units and are not affected by this toggle.
"""

from __future__ import annotations

import json
import os

import streamlit as st

from farloads import Project, UnitSystem
from farloads import io as farloads_io
from farloads import workflow as wf

# Must be the first Streamlit call, and the ONLY set_page_config in the app
# (individual views must not call it again under st.navigation).
st.set_page_config(page_title="FAR 23 LOADS", layout="wide", page_icon="🛩️")

# Numbered, ordered section labels for the sidebar groups.
_PHASE_LABEL = {
    wf.START: "1 · Start",
    wf.AIRPLANE: "2 · Airplane",
    wf.ENVELOPES: "3 · Envelopes & Critical Conditions",
    wf.ANALYSIS: "4 · Analysis",
    wf.LOADS_PLOTS: "5 · Loads Plots",
    wf.EXPORT: "6 · Export",
}

_ICONS = {"dashboard": "🛩️"}

_EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)


def _page(step: wf.WorkflowStep) -> st.Page:
    """A navigable page for a workflow step (view file is ``views/<key>.py``)."""
    return st.Page(
        f"views/{step.key}.py", title=step.title, url_path=step.key,
        icon=_ICONS.get(step.key), default=(step.key == "dashboard"),
    )


# --------------------------------------------------------------------------- #
# Global project state + the sidebar file widget (every page)
# --------------------------------------------------------------------------- #
if "project" not in st.session_state:
    st.session_state["project"] = Project(name="")
project: Project = st.session_state["project"]


def _mark_saved(p: Project) -> None:
    """Snapshot ``p`` as the last loaded/saved state (the unsaved-changes baseline)."""
    st.session_state["_saved_project_snapshot"] = farloads_io.project_to_dict(p)


if "_saved_project_snapshot" not in st.session_state:
    _mark_saved(project)


def _has_unsaved_changes(p: Project) -> bool:
    return farloads_io.project_to_dict(p) != st.session_state.get("_saved_project_snapshot")


def _adopt(new_project: Project) -> None:
    st.session_state["project"] = new_project
    _mark_saved(new_project)


@st.dialog("Discard unsaved changes?")
def _confirm_discard(new_project: Project, source: str) -> None:
    st.write(
        f"**{project.name or '(unnamed)'}** has unsaved changes. Loading "
        f"**{source}** will replace them in this session (nothing on disk is "
        "deleted)."
    )
    c1, c2 = st.columns(2)
    if c1.button("Discard and load", type="primary", use_container_width=True):
        _adopt(new_project)
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


def _load_with_guard(new_project: Project, source: str) -> None:
    if _has_unsaved_changes(project):
        _confirm_discard(new_project, source)
    else:
        _adopt(new_project)
        st.rerun()


with st.sidebar:
    st.header("Units")
    _unit_label = st.radio(
        "Reported results in", ["Imperial", "SI"],
        index=0 if st.session_state.get("unit_system", UnitSystem.IMPERIAL) == UnitSystem.IMPERIAL else 1,
        horizontal=True, key="_unit_system_radio",
        help=(
            "Applies everywhere in the app: weights, lengths, forces, moments, "
            "torque, power and inertia. Calculations always run in Imperial "
            "internally (the FAR 23 LOADS manual's units), so this only changes "
            "how inputs/results are displayed. Airspeed (KEAS) and altitude (ft) "
            "stay in aviation-standard units in both modes."
        ),
    )
    st.session_state["unit_system"] = (
        UnitSystem.IMPERIAL if _unit_label == "Imperial" else UnitSystem.SI
    )

    st.header("Project file")
    dirty = _has_unsaved_changes(project)
    st.caption("🟠 Unsaved changes" if dirty else "⚪ No unsaved changes")

    projects_dir = farloads_io.default_projects_dir()
    saved = farloads_io.list_saved_projects(projects_dir)
    example_files = sorted(
        f for f in os.listdir(_EXAMPLES_DIR) if f.endswith(".project.json")
    ) if os.path.isdir(_EXAMPLES_DIR) else []

    with st.expander("📂 Open", expanded=False):
        if saved:
            choice = st.selectbox(
                "Saved projects", [f for f, _mtime in saved], key="_open_saved_choice"
            )
            if st.button("Open", key="_open_saved_btn", use_container_width=True):
                path = os.path.join(projects_dir, choice)
                _load_with_guard(farloads_io.load_project(path), choice)
        else:
            st.caption(f"No saved projects yet in `{projects_dir}`.")

        if example_files:
            example_choice = st.selectbox(
                "New from example", example_files, key="_open_example_choice"
            )
            if st.button("Load example", key="_open_example_btn", use_container_width=True):
                path = os.path.join(_EXAMPLES_DIR, example_choice)
                _load_with_guard(farloads_io.load_project(path), example_choice)

        uploaded = st.file_uploader("Upload project.json", type="json", key="_uploader")
        if uploaded is not None:
            _load_with_guard(
                farloads_io.project_from_dict(json.load(uploaded)), uploaded.name
            )

    fname = (project.name or "project").strip().replace(" ", "_") or "project"
    if st.button("💾 Save to disk", use_container_width=True, key="_save_btn"):
        os.makedirs(projects_dir, exist_ok=True)
        save_path = os.path.join(projects_dir, f"{fname}.project.json")
        farloads_io.save_project(project, save_path)
        _mark_saved(project)
        st.success(f"Saved: {save_path}")
        st.rerun()

    st.download_button(
        "Download project.json", farloads_io.project_to_json(project),
        file_name=f"{fname}.json", mime="application/json",
        use_container_width=True, key="_download_btn",
    )

sections = {
    _PHASE_LABEL[phase]: [_page(s) for s in steps]
    for phase, steps in wf.by_phase().items()
    if steps
}

pg = st.navigation(sections)
pg.run()
