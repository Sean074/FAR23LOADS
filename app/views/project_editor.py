"""Streamlit page for reviewing/hand-editing the whole project as JSON.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

The canonical ``project.json`` on disk (and every calc module) is always
Imperial -- see ``sloads/units.py`` and CLAUDE.md's units discussion. This
page is a presentation-layer convenience only: it shows the *same* project as
JSON, converted into the sidebar's selected Imperial/SI display units
(``sloads.units.project_dict_to_display``), so a user reviewing or
hand-editing weight/geometry data can work in whichever system they think in.
Apply converts the edited JSON back to Imperial
(``sloads.units.project_dict_to_imperial``) and replaces the in-session
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

from app_shell.components import active_system, stop_page
from app_shell.widget_keys import bump_generation, widget_key
from sloads import Project, UnitSystem
from sloads import io as sloads_io
from sloads.units import project_dict_to_display, project_dict_to_imperial
from sloads.validation import safety_factor_valid

st.title("Project JSON Editor")
st.caption(
    "The whole project, shown as JSON in the sidebar's selected units. Calc and "
    "the saved project.json are always Imperial -- this is a display/edit "
    "convenience; **Apply** converts back to Imperial before updating the "
    "session, and the existing sidebar **Save to disk** / **Download** writes "
    "the same single Imperial project.json as every other page."
)

# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
project: Project = st.session_state.get("project", Project(name=""))

if system == UnitSystem.SI:
    st.info(
        "Showing **SI**. Airspeed (KEAS) and altitude (ft) fields stay "
        "aviation-standard regardless of this toggle -- they are not converted. "
        "Any field this page doesn't yet recognize also stays in its native "
        "Imperial value; check the field name's unit suffix if unsure."
    )

#: Stamped, like every widget seeded from the project: the text this page
#: holds *is* the project, so it must not outlive the project it was read
#: from (``app_shell.widget_keys``). The session-state writes below use the
#: same stamped key, so the re-seed logic is unchanged.
_TEXT_KEY = widget_key("_project_editor_text")
_LOADED_SNAPSHOT_KEY = "_project_editor_loaded_for"


def _bad_safety_factors(node, path=""):
    """``(json_path, value)`` for every ``safety_factor`` in the dict tree that
    fails ``sloads.validation.safety_factor_valid`` (M4-14)."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            sub = f"{path}.{key}" if path else key
            if key == "safety_factor" and not safety_factor_valid(value):
                found.append((sub, value))
            else:
                found.extend(_bad_safety_factors(value, sub))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found.extend(_bad_safety_factors(item, f"{path}[{i}]"))
    return found


def _current_display_text() -> str:
    raw = sloads_io.project_to_dict(project)
    display = project_dict_to_display(raw, system)
    return json.dumps(display, indent=2, sort_keys=False)


# Re-seed the text area whenever the project or the unit system changes
# underneath it (e.g. applied on another page, or the sidebar toggle flipped) --
# but never clobber an in-progress hand-edit that hasn't been applied yet.
_snapshot_id = (id(project), system.value, sloads_io.project_to_json(project))
if st.session_state.get(_LOADED_SNAPSHOT_KEY) != _snapshot_id:
    st.session_state[_TEXT_KEY] = _current_display_text()
    st.session_state[_LOADED_SNAPSHOT_KEY] = _snapshot_id

c1, c2 = st.columns([1, 5])
if c1.button("Reload", help="Discard edits below and reload from the current project."):
    st.session_state[_TEXT_KEY] = _current_display_text()
    st.session_state[_LOADED_SNAPSHOT_KEY] = _snapshot_id
    st.rerun()

edited_text = st.text_area(
    "project.json (selected units)", key=widget_key(_TEXT_KEY), height=560,
    label_visibility="collapsed",
)

apply_col, _ = st.columns([1, 5])
if apply_col.button("Apply", type="primary"):
    try:
        edited_display = json.loads(edited_text)
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON: {exc}")
        stop_page()
    try:
        imperial_dict = project_dict_to_imperial(edited_display, system)
        new_project = sloads_io.project_from_dict(imperial_dict)
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        st.error(f"Could not build a project from this JSON: {exc}")
        stop_page()
    # The version *as typed*, read off the raw dict: project_from_dict has
    # already migrated and stamped, so asking the built project is always "ok"
    # and an edit that pastes an older file would be upgraded silently -- the
    # same defect as the sidebar's (review PB-14, swept here in the same
    # change). The stamp needs no bumping for the same reason.
    status, message = sloads_io.schema_status(
        sloads_io.source_schema_version(imperial_dict))
    if status == "newer":
        st.warning(message)
    elif status == "older":
        st.info(message)
    # Surface an invalid per-case safety_factor at the hand-edit entry point
    # (M4-14). Checked on the *raw* dict: project_from_dict has already reset
    # any invalid value to the conservative 1.5 default, so the built project
    # can't show what was typed.
    for _path, _v in _bad_safety_factors(imperial_dict):
        st.warning(
            f"`{_path}`: safety_factor = {_v!r} is outside the legal [1.0, 1.5] "
            "band (14 CFR 23.303; the factor is set by the load-case "
            "definition) and was reset to the conservative default 1.5."
        )
    st.session_state["project"] = new_project
    # A hand-edit is a *replacement*, like a load: every widget on every other
    # page was seeded from the project this one just discarded, and would write
    # those values back on its next Apply. Not ``adopt()`` -- these edits are
    # not saved to disk, so the dirty baseline must stay where it is.
    bump_generation()
    st.session_state[_LOADED_SNAPSHOT_KEY] = None  # force a re-seed next render
    st.success(
        "Applied. The session project now reflects your edits (converted back "
        "to Imperial). Use the sidebar's Save/Download to write it to disk."
    )
    st.rerun()
