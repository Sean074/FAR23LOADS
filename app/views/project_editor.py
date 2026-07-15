"""Streamlit page for reviewing/hand-editing the whole project as JSON.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

The canonical ``project.json`` on disk (and every calc module) is always
Imperial -- see ``farloads/units.py`` and CLAUDE.md's units discussion. This
page is a presentation-layer convenience only: it shows the *same* project as
JSON, converted into the sidebar's selected Imperial/SI display units
(``farloads.units.project_dict_to_display``), so a user reviewing or
hand-editing weight/geometry data can work in whichever system they think in.
Apply converts the edited JSON back to Imperial
(``farloads.units.project_dict_to_imperial``) and replaces the in-session
project; the existing sidebar Open/Save/Download widget (``app/Home.py``)
then persists it exactly as it always has -- one Imperial project.json, with
all project data in it. No new file, no stored unit tag.

Fields with no known unit conversion (airspeed/altitude -- deliberately kept
aviation-standard in both systems -- plus any field not yet in the project
schema's unit table) are shown/edited in their native Imperial value
regardless of the toggle; see the caption below for the exact list.
"""

from __future__ import annotations

import json

import streamlit as st

from farloads import Project, UnitSystem
from farloads import io as farloads_io
from farloads.units import project_dict_to_display, project_dict_to_imperial

st.title("Project JSON Editor")
st.caption(
    "The whole project, shown as JSON in the sidebar's selected units. Calc and "
    "the saved project.json are always Imperial -- this is a display/edit "
    "convenience; **Apply** converts back to Imperial before updating the "
    "session, and the existing sidebar **Save to disk** / **Download** writes "
    "the same single Imperial project.json as every other page."
)

system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
project: Project = st.session_state.get("project", Project(name=""))

if system == UnitSystem.SI:
    st.info(
        "Showing **SI**. Airspeed (KEAS) and altitude (ft) fields stay "
        "aviation-standard regardless of this toggle -- they are not converted. "
        "Any field this page doesn't yet recognize also stays in its native "
        "Imperial value; check the field name's unit suffix if unsure."
    )

_TEXT_KEY = "_project_editor_text"
_LOADED_SNAPSHOT_KEY = "_project_editor_loaded_for"


def _current_display_text() -> str:
    raw = farloads_io.project_to_dict(project)
    display = project_dict_to_display(raw, system)
    return json.dumps(display, indent=2, sort_keys=False)


# Re-seed the text area whenever the project or the unit system changes
# underneath it (e.g. applied on another page, or the sidebar toggle flipped) --
# but never clobber an in-progress hand-edit that hasn't been applied yet.
_snapshot_id = (id(project), system.value, farloads_io.project_to_json(project))
if st.session_state.get(_LOADED_SNAPSHOT_KEY) != _snapshot_id:
    st.session_state[_TEXT_KEY] = _current_display_text()
    st.session_state[_LOADED_SNAPSHOT_KEY] = _snapshot_id

c1, c2 = st.columns([1, 5])
if c1.button("Reload", help="Discard edits below and reload from the current project."):
    st.session_state[_TEXT_KEY] = _current_display_text()
    st.session_state[_LOADED_SNAPSHOT_KEY] = _snapshot_id
    st.rerun()

edited_text = st.text_area(
    "project.json (selected units)", key=_TEXT_KEY, height=560,
    label_visibility="collapsed",
)

apply_col, _ = st.columns([1, 5])
if apply_col.button("Apply", type="primary"):
    try:
        edited_display = json.loads(edited_text)
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON: {exc}")
        st.stop()
    try:
        imperial_dict = project_dict_to_imperial(edited_display, system)
        new_project = farloads_io.project_from_dict(imperial_dict)
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        st.error(f"Could not build a project from this JSON: {exc}")
        st.stop()
    st.session_state["project"] = new_project
    st.session_state[_LOADED_SNAPSHOT_KEY] = None  # force a re-seed next render
    st.success(
        "Applied. The session project now reflects your edits (converted back "
        "to Imperial). Use the sidebar's Save/Download to write it to disk."
    )
    st.rerun()
