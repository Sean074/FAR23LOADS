"""The global sidebar every page inherits: units, project file, About.

Built once by each GUI entry point *around* its ``pg.run()`` --
``with render_shell_sidebar(project): pg.run()`` -- so it appears on every page
regardless of which view is active (Step D3, decision D-3). Two blocks:

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

**Order of rendering (#64, review 2026-08-22 PB-4).** Streamlit runs the
script top to bottom on every rerun, and the rerun that carries a widget edit
runs the sidebar before the page that persists the edit. A project-file block
rendered *above* ``pg.run()`` therefore serialised the download payload and
read the dirty flag from the project as of the *previous* interaction: the
oracle GUI has no Apply, so every last edit was missing from the download while
the caption said clean. The units block must still come first
(:func:`app_shell.components.active_system` reads it), so the sidebar reserves
the project-file slot before the page and fills it after. A page's early exit
is :func:`app_shell.components.stop_page`, not ``st.stop()`` -- Streamlit
discards everything emitted after ``st.stop()``, the reserved slot included.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Iterator

import streamlit as st

from app_shell.components import IN_SHELL_KEY, StopPage
from app_shell.project_state import (
    has_unsaved_changes,
    load_with_guard,
    safe_load,
    save_with_guard,
)
from app_shell.widget_keys import widget_key
from sloads import Project, UnitSystem
from sloads import io as sloads_io
from sloads.report.results_zip import results_zip_bytes
from sloads.report.results_zip import results_zip_name as _results_zip_name
from sloads.units import unit_system_from

#: Bundled example projects (``<repo>/examples``), offered as New-from-example.
EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)

#: Session-state key holding the identity of the last Upload already handled,
#: so the handler fires once per upload, not once per rerun (#34).
_UPLOAD_PROCESSED_KEY = "_uploader_processed"


@contextmanager
def render_shell_sidebar(project: Project, *,
                         examples_dir: str = EXAMPLES_DIR) -> Iterator[None]:
    """The units + project-file + About sidebar for ``project``, around the page.

    ``with render_shell_sidebar(project): pg.run()``. Units and About render on
    entry; the project-file block renders on exit, *after* the page has
    persisted its edits, into the slot reserved for it between the two -- so
    the dirty caption and the download payload describe the project the user is
    looking at, not the one before the last keystroke (#64). A page leaves early
    through :func:`app_shell.components.stop_page`, never ``st.stop()``: the
    exit is caught here and the block is still filled -- Streamlit discards
    everything emitted after ``st.stop()``, which would have lost Save /
    Download on exactly the pages that gate.
    """
    with st.sidebar:
        _render_units(project)
        slot = st.container()
        _render_about()
    st.session_state[IN_SHELL_KEY] = True
    try:
        yield
    except StopPage:
        pass
    finally:
        st.session_state[IN_SHELL_KEY] = False
        with slot:
            _render_project_file(project, examples_dir)


def _render_units(project: Project) -> None:
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


def _render_project_file(project: Project, examples_dir: str) -> None:
    st.header("Project file")
    # The name is document metadata, not an oracle input, so no oracle page
    # renders it -- and a project built there was called "" for its whole life:
    # every Save was ``project.project.json`` over the last (#65, PB-6). One
    # widget for both GUIs, here, beside the file it names.
    name = st.text_input("Project name", project.name, key=widget_key("_project_name"),
                         help="Names the saved / downloaded file: "
                              f"`{sloads_io.project_filename(project.name)}`.")
    if name != project.name:
        project.name = name
    dirty = has_unsaved_changes(project)
    st.caption("🟠 Unsaved changes" if dirty else "⚪ No unsaved changes")

    projects_dir = sloads_io.default_projects_dir()
    saved = sloads_io.list_saved_projects(projects_dir)
    example_files = sorted(
        f for f in os.listdir(examples_dir) if f.endswith(sloads_io.PROJECT_SUFFIX)
    ) if os.path.isdir(examples_dir) else []

    with st.expander("📂 Open", expanded=False):
        if saved:
            choice = st.selectbox(
                "Saved projects", [f for f, _mtime in saved], key="_open_saved_choice"
            )
            if st.button("Open", key="_open_saved_btn", use_container_width=True):
                path = os.path.join(projects_dir, choice)
                loaded = safe_load(lambda: sloads_io.read_project_dict(path), choice)
                if loaded is not None:
                    load_with_guard(loaded, choice, path)
        else:
            st.caption(f"No saved projects yet in `{projects_dir}`.")

        if example_files:
            example_choice = st.selectbox(
                "New from example", example_files, key="_open_example_choice"
            )
            if st.button("Load example", key="_open_example_btn", use_container_width=True):
                path = os.path.join(examples_dir, example_choice)
                loaded = safe_load(lambda: sloads_io.read_project_dict(path), example_choice)
                if loaded is not None:
                    load_with_guard(loaded, example_choice)

        # Edge-triggered on the upload identity (#34): ``st.file_uploader``
        # returns the same file object on *every* rerun while it sits in the
        # widget, so acting on ``is not None`` alone re-adopts forever
        # (adopt -> rerun -> re-adopt) and, on a dirty project, reopens the
        # discard dialog faster than Cancel can close it. Each new upload
        # mints a fresh ``file_id``, so a deliberate re-upload still loads.
        # The identity is recorded *before* the guard runs: Cancel then
        # genuinely cancels (the file stays in the widget, ignored), and a
        # file that fails to parse is not retried on every rerun.
        uploaded = st.file_uploader("Upload project.json", type="json", key="_uploader")
        if uploaded is not None:
            ident = getattr(uploaded, "file_id", None) or (uploaded.name, uploaded.size)
            if st.session_state.get(_UPLOAD_PROCESSED_KEY) != ident:
                st.session_state[_UPLOAD_PROCESSED_KEY] = ident
                loaded = safe_load(lambda: json.load(uploaded), uploaded.name)
                if loaded is not None:
                    load_with_guard(loaded, uploaded.name)

    # One sanitiser for Save and Download (``io.project_filename``): the raw
    # name reached the filesystem before #65. The file this project came from
    # is written back unasked; any other existing file is confirmed first.
    if st.button("💾 Save to disk", use_container_width=True, key="_save_btn"):
        save_path = os.path.join(projects_dir, sloads_io.project_filename(project.name))
        if save_with_guard(project, save_path):
            st.success(f"Saved: {save_path}")
            st.rerun()

    # The same ``.project.json`` name Save-to-disk writes, so a downloaded file
    # dropped into ``projects/`` is listed by Open (CR-D-9).
    st.download_button(
        "Download project.json", sloads_io.project_to_json(project),
        file_name=sloads_io.project_filename(project.name), mime="application/json",
        use_container_width=True, key="_download_btn",
    )

    # The whole-project results zip (C210-45, backlog 19c): every registered
    # module run against the current project, rendered by the same owners the
    # CLI uses, with a skip-and-manifest for pages that refuse. Two-step
    # (build, then download) because the build runs all 22 modules -- doing
    # that on every sidebar rerun would tax every page for a button nobody
    # pressed. The built bytes are keyed to the project's serialized identity,
    # so an edit after Build invalidates the stale zip instead of serving it.
    if st.button("📦 Build results zip", use_container_width=True,
                 key="_results_zip_build"):
        ident = sloads_io.project_to_json(project)  # identity of what was built
        try:
            data, manifest = results_zip_bytes(
                project, system=unit_system_from(project.unit_system))
        except Exception as exc:  # a genuine defect: show it, don't swallow it
            st.error(f"{type(exc).__name__}: {exc}")
        else:
            st.session_state["_results_zip"] = (ident, data, manifest)
    _built = st.session_state.get("_results_zip")
    if _built is not None:
        _ident, _data, _manifest = _built
        if _ident != sloads_io.project_to_json(project):
            st.session_state.pop("_results_zip", None)
            st.caption("Project changed since the zip was built — build again.")
        else:
            _ran = sum(1 for line in _manifest if line.endswith(": OK"))
            st.download_button(
                "⬇️ Download results (zip)", _data,
                file_name=_results_zip_name(project),
                mime="application/zip", use_container_width=True,
                key="_results_zip_dl",
            )
            st.caption(
                f"{_ran} of {len(_manifest)} modules ran — see MANIFEST.txt "
                "inside; your browser chooses the location."
            )


def _render_about() -> None:
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
