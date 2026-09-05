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

from app_shell.components import (
    IN_SHELL_KEY,
    RELEASE_STATE,
    StopPage,
    unit_number_input,
)
from app_shell.project_state import (
    has_unsaved_changes,
    load_with_guard,
    safe_load,
    save_with_guard,
)
from app_shell.widget_keys import widget_key
from sloads import Project, UnitSystem
from sloads import io as sloads_io
from sloads.constants import convert_airspeed, eas_from_airspeed
from sloads.derived_geometry import (
    mac_reference,
    pct_mac_to_station,
    station_to_pct_mac,
)
from sloads.report import LoadChannel
from sloads.report.results_zip import results_zip_bytes
from sloads.report.results_zip import results_zip_name as _results_zip_name
from sloads.units import (
    labels_for,
    to_display,
    unit_system_from,
)

#: Bundled example projects (``<repo>/examples``), offered as New-from-example.
EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)

#: Session-state key holding the identity of the last Upload already handled,
#: so the handler fires once per upload, not once per rerun (#34).
_UPLOAD_PROCESSED_KEY = "_uploader_processed"


@contextmanager
def render_shell_sidebar(project: Project, *,
                         examples_dir: str = EXAMPLES_DIR,
                         channel: LoadChannel = LoadChannel.LIMIT,
                         ) -> Iterator[None]:
    """The units + project-file + About sidebar for ``project``, around the page.

    ``with render_shell_sidebar(project): pg.run()``. Units and About render on
    entry; the project-file block renders on exit, *after* the page has
    persisted its edits, into the slot reserved for it between the two -- so
    the dirty caption and the download payload describe the project the user is
    looking at, not the one before the last keystroke (#64). A page leaves early
    ``channel`` is the load basis of the results zip this sidebar builds. It
    defaults to LIMIT, the project's one basis since note 49 OR-116; the
    **frozen** ``oracle_app/Oracle.py`` — which
    cannot be edited to pass an argument — keeps today's zip byte-for-byte;
    ``app/Home.py`` passes ``LoadChannel.LIMIT`` so the zip matches the pages it
    mirrors (design note 48, OR-77/OR-79). One sidebar serves both GUIs, which
    is why the choice is a parameter rather than a constant.

    A page leaves early
    through :func:`app_shell.components.stop_page`, never ``st.stop()``: the
    exit is caught here and the block is still filled -- Streamlit discards
    everything emitted after ``st.stop()``, which would have lost Save /
    Download on exactly the pages that gate.
    """
    with st.sidebar:
        _render_units(project)
        slot = st.container()
        _render_tools(project)
        _render_about()
    st.session_state[IN_SHELL_KEY] = True
    try:
        yield
    except StopPage:
        pass
    finally:
        st.session_state[IN_SHELL_KEY] = False
        with slot:
            _render_project_file(project, examples_dir, channel)


def _render_units(project: Project) -> None:
    st.header("Units")
    unit_label = st.radio(
        "Reported results in", ["Imperial", "SI"],
        index=0 if unit_system_from(project.unit_system) == UnitSystem.IMPERIAL else 1,
        horizontal=True, key=widget_key("_unit_system_radio"),
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
    #
    # Because it lives on the project, the radio is a **project-seeded** widget and
    # carries the generation stamp like any other (#70, review 2026-08-22 PB-16).
    # Unstamped, its retained state beat ``index=``: opening an SI-saved file in an
    # Imperial session put "imperial" back on the loaded project and showed
    # "Unsaved changes" before the user had touched anything -- the load editing
    # the file it had just read. Within a session the stamp does not move, so a
    # unit choice still survives every rerun; only a project *replacement*
    # re-seeds it, which is the whole point.
    if project.unit_system != selected.value:
        project.unit_system = selected.value
    st.session_state["unit_system"] = selected


def _render_project_file(project: Project, examples_dir: str,
                         channel: LoadChannel = LoadChannel.LIMIT) -> None:
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
            if st.button("Open", key="_open_saved_btn", width="stretch"):
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
            if st.button("Load example", key="_open_example_btn", width="stretch"):
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
    if st.button("💾 Save to disk", width="stretch", key="_save_btn"):
        save_path = os.path.join(projects_dir, sloads_io.project_filename(project.name))
        if save_with_guard(project, save_path):
            # A toast, not ``st.success``: the ``st.rerun()`` on the next line
            # discards the frame that carried it, so the confirmation of the one
            # action with a side effect outside the session was never once seen
            # (#72, PB-23). Toasts survive the rerun -- the same channel the
            # loader's repair warnings use (``project_state`` OG-D).
            st.toast(f"Saved: {save_path}", icon="💾")
            st.rerun()

    # The same ``.project.json`` name Save-to-disk writes, so a downloaded file
    # dropped into ``projects/`` is listed by Open (CR-D-9).
    st.download_button(
        "Download project.json", sloads_io.project_to_json(project),
        file_name=sloads_io.project_filename(project.name), mime="application/json",
        width="stretch", key="_download_btn",
    )
    # Two complementary routes, said *before* the click (#94, C210-48): a
    # browser page cannot open an OS save dialog for a server-side write, so
    # Save offers no location choice -- and until this caption, its fixed
    # target appeared only in the success toast after the fact, so the pair
    # read as one mislabeled button.
    st.caption(
        f"**Save to disk** writes `{os.path.join(projects_dir, sloads_io.project_filename(project.name))}` "
        "beside the app — no location dialog; files there are listed by **Open**. "
        "**Download** hands the same file to your browser, which chooses the "
        "location; dropped into that folder, it is listed by Open too."
    )

    # The whole-project results zip (C210-45, backlog 19c): every registered
    # module run against the current project, rendered by the same owners the
    # CLI uses, with a skip-and-manifest for pages that refuse. Two-step
    # (build, then download) because the build runs all 22 modules -- doing
    # that on every sidebar rerun would tax every page for a button nobody
    # pressed. The built bytes are keyed to the project's serialized identity,
    # so an edit after Build invalidates the stale zip instead of serving it.
    if st.button("📦 Build results zip", width="stretch",
                 key="_results_zip_build"):
        ident = sloads_io.project_to_json(project)  # identity of what was built
        try:
            data, manifest = results_zip_bytes(
                project, system=unit_system_from(project.unit_system),
                channel=channel)
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
                mime="application/zip", width="stretch",
                key="_results_zip_dl",
            )
            st.caption(
                f"{_ran} of {len(_manifest)} modules ran — see MANIFEST.txt "
                "inside; your browser chooses the location."
            )


# --------------------------------------------------------------------------- #
# Tools (#80) -- display-only arithmetic, in the sidebar of both front-ends
# --------------------------------------------------------------------------- #
#: The airspeed measures the converter offers, in the order a POH quotes them.
_SPEED_UNITS = ("KCAS", "KEAS", "KTAS")

#: The two directions of the %MAC <-> fuselage-station conversion.
_PCT_TO_STATION = "% MAC → station"
_STATION_TO_PCT = "station → % MAC"


def _render_tools(project: Project) -> None:
    """The collapsed Tools expander: the two conversions done by hand in the
    C210 build (#80, owner feature request, build review 2026-08-23).

    Rendered from the shared shell so both front-ends get one implementation.
    It is **display-only** -- it reads the project and writes nothing back, so
    no entry here can dirty a project or move a load -- which is the ground of
    the owner's refinement to the oracle GUI's capability cap (OG-1): the cap
    governs analysis and data capability, not inert display utilities.

    Both conversions delegate their arithmetic to the ``sloads`` owners
    (:func:`sloads.constants.eas_from_airspeed` / ``convert_airspeed`` over the
    suite's own atmosphere; :func:`sloads.derived_geometry.mac_reference` and the
    two %MAC functions), so a tool cannot answer a question differently from the
    modules -- the no-dual-path rule (G1) applies to a sidebar as much as a page.
    """
    system = unit_system_from(project.unit_system)
    st.divider()
    with st.expander("🛠️ Tools", expanded=False):
        _render_speed_converter()
        st.divider()
        _render_mac_converter(project, system)


def _render_speed_converter() -> None:
    st.markdown("**Airspeed converter**")
    speed = st.number_input(
        "Speed (kt)", min_value=0.0, value=100.0, step=1.0,
        key=widget_key("_tool_speed"),
        help="A speed off a POH, a placard or a page of this app. Airspeeds are "
             "knots in both unit systems (aviation standard).",
    )
    measure = st.selectbox(
        "is", _SPEED_UNITS, index=0, key=widget_key("_tool_speed_unit"),
        help="Which airspeed the number above is. **KCAS** is what a POH and a "
             "placard quote; **KEAS** is what every speed in this app and in the "
             "FAR 23 LOADS manual is; **KTAS** is true airspeed.",
    )
    altitude = st.number_input(
        "at altitude (ft)", min_value=0.0, value=0.0, step=500.0,
        key=widget_key("_tool_altitude"),
        help="Pressure altitude on a standard day. The conversion is ISA-only — "
             "it takes no account of a non-standard temperature.",
    )
    if speed <= 0.0:
        st.caption("Enter a speed above zero.")
        return
    eas = eas_from_airspeed(float(speed), float(altitude), str(measure))
    st.dataframe(
        {"Measure": list(_SPEED_UNITS),
         "kt": [round(convert_airspeed(eas, float(altitude), u), 2) for u in _SPEED_UNITS]},
        hide_index=True, width="stretch",
    )
    st.caption(
        "ISA standard day, subsonic. The three are equal at sea level and part "
        "with altitude and Mach."
    )


def _render_mac_converter(project: Project, system: UnitSystem) -> None:
    st.markdown("**% MAC ↔ fuselage station**")
    ref = mac_reference(project)
    if ref is None:
        st.caption(
            "No wing to measure against yet. A %MAC is read from the wing "
            "planform (its MAC and MAC leading-edge station) — add the wing "
            "surface on the Configuration & Layout page, or set the weight "
            "envelope's XLEMAC and MAC directly."
        )
        return
    length_label = labels_for(system)["length"]
    direction = st.radio(
        "Convert", [_PCT_TO_STATION, _STATION_TO_PCT], key=widget_key("_tool_mac_dir"),
        label_visibility="collapsed",
    )
    if direction == _PCT_TO_STATION:
        pct = st.number_input("% MAC", value=25.0, step=1.0, key=widget_key("_tool_pct_mac"))
        station = pct_mac_to_station(float(pct), ref)
        st.metric(f"Fuselage station ({length_label})",
                  f"{to_display(station, 'length', system):.2f}")
    else:
        # A converted length goes through the one unit boundary like every other
        # converted number in either GUI (#126). Seeded and keyed by hand, this
        # field kept its retained state across a unit switch -- Streamlit's state
        # outvotes ``value=`` -- and the same digits were read as inches and then
        # as millimetres: 63.641 answered 0.00 %MAC in Imperial and -88.29 %MAC
        # after toggling to SI, the same field, the same number, two answers.
        # ``unit_number_input`` takes Imperial in and returns Imperial, and its
        # key carries the system, so the switch re-seeds instead of reinterpreting.
        entered = unit_number_input("Fuselage station", ref.xlemac, kind="length",
                                    step=1.0, key=widget_key("_tool_station"))
        station = ref.xlemac if entered is None else float(entered)
        st.metric("% MAC", f"{station_to_pct_mac(station, ref):.2f}")
    # The C210-13 half of the row: WTENV falls back to the planform when the
    # envelope's XLEMAC/MAC are blank, and nothing on that page says so. A tool
    # that answers with the fallback and does not name it repeats the defect.
    source = ("the weight envelope's typed XLEMAC/MAC" if ref.source == "override"
              else f"the {ref.surface_name!r} wing planform")
    st.caption(
        f"Measured from {source}: XLEMAC "
        f"{to_display(ref.xlemac, 'length', system):.2f}, MAC "
        f"{to_display(ref.mac, 'length', system):.2f} {length_label}."
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
        # What this release is, from its one owner (components.RELEASE_STATE) --
        # the same sentence README.md and CAPABILITIES.md carry. It belongs in
        # front of the user, not only in the packaging metadata: a person typing
        # an airplane into the beta front-end has no other way to learn that is
        # what it is, and `Development Status :: 4 - Beta` is read by pip, not by
        # them (owner ruling 2026-08-28, production-release review §5.3).
        st.caption(f"**Release state.** {RELEASE_STATE}")
        st.caption(
            "**Not affiliated with, endorsed by, or associated with McGettrick "
            "Structural Engineering, Inc. or DARcorporation**, whose "
            "\"FAR 23 LOADS\" is a separate commercial product."
        )
    st.caption("Open replication — not affiliated with McGettrick / DARcorporation.")
