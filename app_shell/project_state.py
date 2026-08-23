"""The project in session state, and the unsaved-changes guard around replacing it.

The whole app is one reloadable ``project.json`` carried in
``st.session_state["project"]``. This module owns that slot: seeding it, keeping
the *saved snapshot* baseline the dirty flag diffs against, and the
load-guard chain every load action goes through —

    safe_load(build, source)  ->  apply_schema_check  ->  load_with_guard
                                                              |
                                        clean project ---> adopt + rerun
                                        dirty project ---> confirm_discard dialog

Extracted from ``app/Home.py`` by design note 32 step OG-B. They were private
module functions of a Streamlit *script*: importing them meant executing the
existing app (``st.set_page_config``, the sidebar, ``pg.run()``), so the second
GUI could not reuse them and would have had to carry its own copy of the dirty
guard — two implementations of "are there unsaved changes?", which is the class
of duplication ``CLAUDE.md`` rule 3 exists to prevent. Behaviour is unchanged
from the script version; only the leading underscores are gone, since these are
now the shell's public surface.

The schema check is deliberately **soft** in both directions (a newer file warns
and still loads, an older one is migrated in place) — the hard contract lives in
``sloads.io``, and this is only how the GUI reports it.
"""

from __future__ import annotations

import json
import warnings
from typing import Callable, Optional

import streamlit as st

from app_shell.components import active_project
from app_shell.widget_keys import bump_generation
from sloads import Project
from sloads import io as sloads_io
from sloads.models import SCHEMA_VERSION

#: Session-state key holding the dict form of the last loaded/saved project.
#: The dirty flag is a diff against this, not a mutation counter, so an edit
#: that returns a field to its saved value correctly reads as *not* dirty.
SAVED_SNAPSHOT_KEY = "_saved_project_snapshot"


def mark_saved(project: Project) -> None:
    """Snapshot ``project`` as the last loaded/saved state (the dirty baseline)."""
    st.session_state[SAVED_SNAPSHOT_KEY] = sloads_io.project_to_dict(project)


def ensure_project() -> Project:
    """The session's project, seeding an empty one (and its baseline) on first run.

    Called once by each GUI entry point above its navigation, so every page can
    rely on ``st.session_state["project"]`` existing.
    """
    if "project" not in st.session_state:
        st.session_state["project"] = Project(name="")
    project: Project = st.session_state["project"]
    if SAVED_SNAPSHOT_KEY not in st.session_state:
        mark_saved(project)
    return project


def has_unsaved_changes(project: Project) -> bool:
    return sloads_io.project_to_dict(project) != st.session_state.get(SAVED_SNAPSHOT_KEY)


def adopt(new_project: Project) -> None:
    """Replace the session's project, reset the dirty baseline to it, and retire
    the widgets that were seeded from the project it replaces.

    This and the JSON editor's Apply (``app/views/project_editor.py``, which
    replaces the project *without* saving it, so it bumps the generation itself
    and leaves the dirty baseline alone) are the only two places in either GUI
    that mean "the project was replaced". The generation bump belongs at both:
    without it, a page visited before the load re-renders from its own retained
    widget state and writes that state back over what was just loaded
    (:mod:`app_shell.widget_keys`).
    """
    st.session_state["project"] = new_project
    bump_generation()
    mark_saved(new_project)


@st.dialog("Discard unsaved changes?")
def confirm_discard(new_project: Project, source: str) -> None:
    current = active_project()
    st.write(
        f"**{current.name or '(unnamed)'}** has unsaved changes. Loading "
        f"**{source}** will replace them in this session (nothing on disk is "
        "deleted)."
    )
    c1, c2 = st.columns(2)
    if c1.button("Discard and load", type="primary", use_container_width=True):
        adopt(new_project)
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


def apply_schema_check(new_project: Project) -> Project:
    """Surface a soft ``SCHEMA_VERSION`` mismatch, then return the project ready to
    adopt. A newer file warns (and still loads); an older file is migrated in place
    (its field-presence migration already ran in ``io.py``; here we bump the stamp).
    Uses ``st.toast`` because the adopt path ends in ``st.rerun()``, which would
    discard an ordinary ``st.warning``."""
    status, message = sloads_io.schema_status(new_project.schema_version)
    if status == "newer":
        st.toast(message, icon="⚠️")
    elif status == "older":
        new_project.schema_version = SCHEMA_VERSION
        st.toast(message, icon="🔁")
    return new_project


def safe_load(build: Callable[[], Project], source: str) -> Optional[Project]:
    """Build a project from a load action, showing ``st.error`` instead of a
    traceback on a malformed / wrong-shape file (parity with the JSON Editor).
    Returns ``None`` on failure so the caller skips the load."""
    try:
        # A migration hop that had to choose between two disagreeing copies of
        # one quantity (v55, #52) says so with ``warnings.warn``; headless that
        # reaches stderr, but a Streamlit page would swallow it. Captured here
        # and shown as toasts, the same channel ``apply_schema_check`` uses,
        # because the adopt path ends in ``st.rerun()`` and an ordinary
        # ``st.warning`` would not survive it.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            project = apply_schema_check(build())
        for w in caught:
            st.toast(f"{source}: {w.message}", icon="⚠️")
        return project
    except (json.JSONDecodeError, OSError, TypeError, ValueError, KeyError,
            AttributeError) as exc:
        st.error(f"Couldn't load {source}: {exc}")
        return None


def load_with_guard(new_project: Project, source: str) -> None:
    """Adopt ``new_project``, first confirming if the current one is dirty."""
    if has_unsaved_changes(active_project()):
        confirm_discard(new_project, source)
    else:
        adopt(new_project)
        st.rerun()
