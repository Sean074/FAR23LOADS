"""Widget identity across a project replacement — the *project generation*.

Streamlit widget state, once registered under a key, wins over the ``value=``
argument on every later rerun. Widget keys in both GUIs are stable across
projects — a registry path in :mod:`oracle_app.form`, a hand-written name in
``app/views/`` — so a page **visited before** a load kept re-rendering its own
retained state, and, because those widgets persist what they return, wrote that
stale state straight back over the project that had just been loaded. In the
oracle GUI (which has no Apply step) that happened on the load's own rerun: the
row-count widget of a table held ``0``, so all 21 ``weight.items`` and all 8
``cg_cases`` of a loaded ATR-42 were popped, and saving from there put the
emptied project on disk. It is not a display defect and re-seeding does not fix
it: the widget has to be a **different widget**.

This module is that difference. Every widget seeded from the project keys itself
through :func:`widget_key`, which stamps the key with a counter bumped exactly
once per *replacement* of the session's project — by
:func:`app_shell.project_state.adopt` (a load), and by the JSON editor's Apply
(``app/views/project_editor.py``), which replaces the project without saving it
and so bumps here without touching the dirty baseline. A mutation, a per-page
Apply, a unit switch: not a replacement, and the widgets keep their state.

The alternative — clearing widget state on adopt — needs a list of keys the
shell would have to keep in step with the field registry and twenty-one view
modules; it is wrong the first time a widget is added, and silent about it.
The generation stamp is carried by the key itself, so a new widget is fresh by
construction, and ``tests/test_widget_freshness.py`` fails on one that skips it.

It lives in its own module, not in ``project_state``, so the shell's unit
boundary (:func:`app_shell.components.unit_number_input`) can stamp keys without
importing the module that imports *it*.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

#: Session-state key holding the generation counter.
PROJECT_GENERATION_KEY = "_project_generation"

#: Separator between the generation stamp and a widget's own key. Chosen so it
#: cannot collide with a registry path (dots), a unit-system suffix
#: (underscores) or a row index.
SEPARATOR = "::"


def project_generation() -> int:
    """How many times the session's project has been replaced."""
    return int(st.session_state.get(PROJECT_GENERATION_KEY, 0))


def bump_generation() -> None:
    """Record that the session's project was replaced — retiring, by renaming,
    every widget seeded from the project it replaces."""
    st.session_state[PROJECT_GENERATION_KEY] = project_generation() + 1


def widget_key(base: Optional[str]) -> Optional[str]:
    """``base`` stamped with the current project generation.

    Idempotent: stamping an already-stamped key returns it unchanged, so a view
    may stamp its own key and still hand it to a shell helper that stamps too.
    ``None`` (a widget that asked Streamlit for positional identity) passes
    through — there is no state to go stale.
    """
    if not base:
        return base
    prefix = f"g{project_generation()}{SEPARATOR}"
    return base if base.startswith(prefix) else f"{prefix}{base}"


def unstamped(key: Optional[str]) -> str:
    """``key`` without its generation stamp — the inverse of :func:`widget_key`.

    For tests and anything else that identifies a widget by what it edits rather
    than by which load of the project it belongs to.
    """
    if not key:
        return ""
    head, sep, rest = key.partition(SEPARATOR)
    return rest if sep and head.startswith("g") and head[1:].isdigit() else key
