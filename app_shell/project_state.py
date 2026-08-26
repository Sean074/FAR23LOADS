"""The project in session state, and the unsaved-changes guard around replacing it.

The whole app is one reloadable ``project.json`` carried in
``st.session_state["project"]``. This module owns that slot: seeding it, keeping
the *saved snapshot* baseline the dirty flag diffs against, and the
load-guard chain every load action goes through —

    safe_load(read_dict, source)  ->  apply_schema_check  ->  load_with_guard
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
import os
import warnings
from typing import Any, Callable, Mapping, Optional

import streamlit as st

from app_shell.components import active_project
from app_shell.widget_keys import bump_generation
from sloads import Project
from sloads import io as sloads_io

#: Session-state key holding the dict form of the last loaded/saved project.
#: The dirty flag is a diff against this, not a mutation counter, so an edit
#: that returns a field to its saved value correctly reads as *not* dirty.
SAVED_SNAPSHOT_KEY = "_saved_project_snapshot"

#: Session-state key holding the ``projects/`` path this project was opened
#: from or last saved to (``None`` for a fresh, example or uploaded project).
#: Save writes there without asking; any *other* existing file is confirmed
#: first (#65, PB-6).
SAVED_PATH_KEY = "_saved_project_path"


def mark_saved(project: Project, path: Optional[str] = None) -> None:
    """Snapshot ``project`` as the last loaded/saved state (the dirty baseline),
    and record the on-disk file it now corresponds to (``None``: no file)."""
    st.session_state[SAVED_SNAPSHOT_KEY] = sloads_io.project_to_dict(project)
    st.session_state[SAVED_PATH_KEY] = path


def saved_path() -> Optional[str]:
    """The file Save writes back to unprompted, if the project has one."""
    return st.session_state.get(SAVED_PATH_KEY)


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


def adopt(new_project: Project, path: Optional[str] = None) -> None:
    """Replace the session's project, reset the dirty baseline to it, and retire
    the widgets that were seeded from the project it replaces. ``path`` is the
    ``projects/`` file it was opened from, if any (see :data:`SAVED_PATH_KEY`).

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
    mark_saved(new_project, path)


@st.dialog("Discard unsaved changes?")
def confirm_discard(new_project: Project, source: str, path: Optional[str] = None) -> None:
    current = active_project()
    st.write(
        f"**{current.name or '(unnamed)'}** has unsaved changes. Loading "
        f"**{source}** will replace them in this session (nothing on disk is "
        "deleted)."
    )
    c1, c2 = st.columns(2)
    if c1.button("Discard and load", type="primary", use_container_width=True):
        adopt(new_project, path)
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


def apply_schema_check(new_project: Project, source_version: int) -> Project:
    """Surface a soft ``SCHEMA_VERSION`` mismatch, then return the project ready to
    adopt. A newer file warns (and still loads); an older file has already been
    migrated by ``io.py`` and is reported as such. Uses ``st.toast`` because the
    adopt path ends in ``st.rerun()``, which would discard an ordinary
    ``st.warning``.

    ``source_version`` is the version the file carried **before** migration
    (``io.source_schema_version``), and it has to be passed in: this used to ask
    ``new_project.schema_version``, which ``migrate`` has already stamped at
    :data:`SCHEMA_VERSION`, so the answer was always "ok" and the migration
    notice could never fire -- a v41 file opened, was upgraded, and would be
    rewritten at v55 on save with nothing said (review PB-14).

    The stamp itself is not touched here any more, for the same reason: it was
    already current before this function saw the project.
    """
    status, message = sloads_io.schema_status(source_version)
    if status == "newer":
        st.toast(message, icon="⚠️")
    elif status == "older":
        st.toast(message, icon="🔁")
    return new_project


def safe_load(read_dict: Callable[[], Mapping[str, Any]], source: str) -> Optional[Project]:
    """Build a project from a load action, showing ``st.error`` instead of a
    traceback on a malformed / wrong-shape file (parity with the JSON Editor).
    Returns ``None`` on failure so the caller skips the load.

    The argument is the **dict reader**, not a project builder: what version the
    file was written at is a fact about the dict, and ``project_from_dict``
    stamps it away (review PB-14). Building here rather than at the call site is
    what keeps the two -- the project and the version it came from -- in one
    place for every load action in either GUI.
    """
    try:
        # A migration hop that had to choose between two disagreeing copies of
        # one quantity (v55, #52) says so with ``warnings.warn``; headless that
        # reaches stderr, but a Streamlit page would swallow it. Captured here
        # and shown as toasts, the same channel ``apply_schema_check`` uses,
        # because the adopt path ends in ``st.rerun()`` and an ordinary
        # ``st.warning`` would not survive it.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            raw = read_dict()
            project = apply_schema_check(sloads_io.project_from_dict(raw),
                                         sloads_io.source_schema_version(raw))
        for w in caught:
            st.toast(f"{source}: {w.message}", icon="⚠️")
        return project
    except (json.JSONDecodeError, OSError, TypeError, ValueError, KeyError,
            AttributeError) as exc:
        st.error(f"Couldn't load {source}: {exc}")
        return None


def load_with_guard(new_project: Project, source: str, path: Optional[str] = None) -> None:
    """Adopt ``new_project``, first confirming if the current one is dirty.
    ``path`` is the ``projects/`` file it came from (Open), else ``None``."""
    if has_unsaved_changes(active_project()):
        confirm_discard(new_project, source, path)
    else:
        adopt(new_project, path)
        st.rerun()


@st.dialog("Overwrite the saved project?")
def confirm_overwrite(project: Project, path: str) -> None:
    """Save wants to write ``path``, which exists and is not this project's own
    file. Until #65 a second project named like the first silently replaced
    it on disk."""
    st.write(f"**{os.path.basename(path)}** already exists in the projects "
             "directory and is not the file this project was opened from. "
             "Overwrite it?")
    c1, c2 = st.columns(2)
    if c1.button("Overwrite", type="primary", use_container_width=True):
        save_to(project, path)
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


def save_to(project: Project, path: str) -> None:
    """Write ``project`` to ``path`` and make that file its saved state."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sloads_io.save_project(project, path)
    mark_saved(project, path)


def save_with_guard(project: Project, path: str) -> bool:
    """Save to ``path``; returns ``True`` when written now, ``False`` when an
    overwrite of some *other* existing file was put to the user first."""
    own = saved_path()
    if os.path.exists(path) and (own is None or os.path.abspath(own) != os.path.abspath(path)):
        confirm_overwrite(project, path)
        return False
    save_to(project, path)
    return True
