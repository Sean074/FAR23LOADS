"""The global sidebar every page inherits: units, project file, About.

Built once by each GUI entry point above its ``pg.run()``, so it appears on every
page regardless of which view is active (Step D3, decision D-3). Two blocks:

* **Units** — the Imperial/SI selection. Calc and ``project.json`` stay
  Imperial-only (canonical internal units); SI is a presentation choice applied
  at each view's render boundary via :func:`app_shell.components.active_system`.
  Airspeed (KEAS) and altitude (ft) are aviation-standard and unaffected.
* **Project file** — the dirty flag, Open from the local ``projects/`` directory,
  New-from-example, browser upload/download, Save to disk. Every load path goes
  through :mod:`app_shell.project_state`'s guard chain.

Extracted from ``app/Home.py`` by design note 32 step OG-B: a second front-end
must not grow a second units toggle or a second Save button that can disagree
with this one about where a project lives or whether it is dirty.
"""

from __future__ import annotations

import json
import os

import streamlit as st

from app_shell.project_state import (
    has_unsaved_changes,
    load_with_guard,
    mark_saved,
    safe_load,
)
from sloads import Project, UnitSystem
from sloads import io as sloads_io
from sloads.units import unit_system_from

#: Bundled example projects (``<repo>/examples``), offered as New-from-example.
EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)


def render_shell_sidebar(project: Project, *, examples_dir: str = EXAMPLES_DIR) -> None:
    """Render the units + project-file + About sidebar for ``project``."""
    with st.sidebar:
        st.header("Units")
        unit_label = st.radio(
            "Reported results in", ["Imperial", "SI"],
            index=0 if unit_system_from(project.unit_system) == UnitSystem.IMPERIAL else 1,
            horizontal=True, key="_unit_system_radio",
            help=(
                "Applies everywhere in the app: weights, lengths, forces, moments, "
                "torque, power and inertia — **and to everything you export** (the "
                "report, the load-case CSVs and the sbeam decks are all written in "
                "this system). Calculations always run in Imperial internally (the "
                "FAR 23 LOADS manual's units), and the saved project.json always "
                "stores Imperial values — this is a rendering preference, not a "
                "conversion of your data. Airspeed (KEAS) and altitude (ft) stay in "
                "aviation-standard units in both modes."
            ),
        )
        selected = UnitSystem.IMPERIAL if unit_label == "Imperial" else UnitSystem.SI
        # M4-20 D-22: the selection lives on the project, so changing it is a project
        # edit and shows as an unsaved change (the dirty flag below is a diff against
        # the last loaded/saved snapshot). The session key is kept in step so a render
        # that has no project yet still resolves.
        if project.unit_system != selected.value:
            project.unit_system = selected.value
        st.session_state["unit_system"] = selected

        st.header("Project file")
        dirty = has_unsaved_changes(project)
        st.caption("🟠 Unsaved changes" if dirty else "⚪ No unsaved changes")

        projects_dir = sloads_io.default_projects_dir()
        saved = sloads_io.list_saved_projects(projects_dir)
        example_files = sorted(
            f for f in os.listdir(examples_dir) if f.endswith(".project.json")
        ) if os.path.isdir(examples_dir) else []

        with st.expander("📂 Open", expanded=False):
            if saved:
                choice = st.selectbox(
                    "Saved projects", [f for f, _mtime in saved], key="_open_saved_choice"
                )
                if st.button("Open", key="_open_saved_btn", use_container_width=True):
                    path = os.path.join(projects_dir, choice)
                    loaded = safe_load(lambda: sloads_io.load_project(path), choice)
                    if loaded is not None:
                        load_with_guard(loaded, choice)
            else:
                st.caption(f"No saved projects yet in `{projects_dir}`.")

            if example_files:
                example_choice = st.selectbox(
                    "New from example", example_files, key="_open_example_choice"
                )
                if st.button("Load example", key="_open_example_btn", use_container_width=True):
                    path = os.path.join(examples_dir, example_choice)
                    loaded = safe_load(lambda: sloads_io.load_project(path), example_choice)
                    if loaded is not None:
                        load_with_guard(loaded, example_choice)

            uploaded = st.file_uploader("Upload project.json", type="json", key="_uploader")
            if uploaded is not None:
                loaded = safe_load(
                    lambda: sloads_io.project_from_dict(json.load(uploaded)), uploaded.name
                )
                if loaded is not None:
                    load_with_guard(loaded, uploaded.name)

        fname = (project.name or "project").strip().replace(" ", "_") or "project"
        if st.button("💾 Save to disk", use_container_width=True, key="_save_btn"):
            os.makedirs(projects_dir, exist_ok=True)
            save_path = os.path.join(projects_dir, f"{fname}.project.json")
            sloads_io.save_project(project, save_path)
            mark_saved(project)
            st.success(f"Saved: {save_path}")
            st.rerun()

        st.download_button(
            "Download project.json", sloads_io.project_to_json(project),
            file_name=f"{fname}.json", mime="application/json",
            use_container_width=True, key="_download_btn",
        )

        # App-wide About / non-affiliation notice (built once, shown on every page).
        st.divider()
        with st.expander("ℹ️ About", expanded=False):
            st.caption(
                "A modern **open replication** of the FAR23 loads suite "
                "(DOT/FAA/AR-96/46; Hal C. McMaster's CAE theory manual). "
                "An educational and exploratory engineering tool — results are "
                "**not certified** for structural design or airworthiness decisions."
            )
            st.caption(
                "**Not affiliated with, endorsed by, or associated with McGettrick "
                "Structural Engineering, Inc. or DARcorporation**, whose "
                "\"FAR 23 LOADS\" is a separate commercial product."
            )
        st.caption("Open replication — not affiliated with McGettrick / DARcorporation.")
