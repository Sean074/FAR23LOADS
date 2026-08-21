"""sloads — multipage entrypoint.

Run with:  streamlit run app/Home.py

This file is now **only what is specific to this front-end**: its page set, its
sidebar grouping, and its one ``st.set_page_config``. Everything shared with the
second GUI (design note 32) lives in :mod:`app_shell` — the project in session
state and its unsaved-changes guard (:mod:`app_shell.project_state`), the units
toggle and project-file widget (:mod:`app_shell.sidebar`), the page scaffold and
unit boundary (:mod:`app_shell.components`).

The whole app is one reloadable ``project.json`` carried in ``st.session_state``.
Navigation is built explicitly from :mod:`sloads.workflow` (the single source of
truth for the step graph) and grouped into a **Start** app-shell section plus the
six analysis-flow phases the user moves through left-to-right (Step G2):

    Start ──▶ 1 · Develop V-n diagram ──▶ 2 · Flight loads ──▶ 3 · Other loads ──▶
    4 · Landing loads ──▶ 5 · Load-case plotting ──▶ 6 · Export

Using ``st.navigation`` (rather than the implicit ``pages/`` directory) means page
order and titles come from the workflow metadata, not filename numbers -- so there
is no numeric-prefix coupling and no duplicate-index collisions. A section with no
steps is omitted from the sidebar rather than shown empty.

Navigation is deliberately *not* shared shell: this GUI shows every workflow step,
while the oracle GUI shows only the steps backed by an original ``.BAS`` program
(note 32, OG-2), so the two derive their page sets from the same ``workflow.py``
by different rules.
"""

from __future__ import annotations

import streamlit as st

from app_shell.nav import register_pages
from app_shell.project_state import ensure_project
from app_shell.sidebar import render_shell_sidebar
from sloads import workflow as wf

# Must be the first Streamlit call, and the ONLY set_page_config in this
# entry point (individual views must not call it again under st.navigation;
# the second GUI has exactly one of its own -- note 32, OG-10). The shell
# imports above define widgets but emit nothing, so they do not consume it.
st.set_page_config(page_title="sloads", layout="wide", page_icon="🛩️")

# Ordered section labels for the sidebar groups: an un-numbered Start app-shell
# group above the six numbered analysis-flow phases (Step G2).
_PHASE_LABEL = {
    wf.START: "Start",
    wf.DEVELOP_VN: "1 · Develop V-n diagram",
    wf.FLIGHT_LOADS: "2 · Flight loads",
    wf.OTHER_LOADS: "3 · Other loads",
    wf.LANDING: "4 · Landing loads",
    wf.LOADS_PLOTTING: "5 · Load-case plotting",
    wf.EXPORT: "6 · Export",
}

_ICONS = {"dashboard": "🛩️"}


def _page(step: wf.WorkflowStep) -> st.Page:
    """A navigable page for a workflow step (view file is ``views/<key>.py``)."""
    return st.Page(
        f"views/{step.key}.py", title=step.title, url_path=step.key,
        icon=_ICONS.get(step.key), default=(step.key == "dashboard"),
    )


project = ensure_project()
render_shell_sidebar(project)

_pages = {s.key: _page(s) for s in wf.STEPS}
# The link helper resolves a step key to *this* GUI's page object rather than to
# a path (note 32, OG-F), so the page set it links into is the one built here.
register_pages(_pages)

sections = {
    _PHASE_LABEL[phase]: [_pages[s.key] for s in steps]
    for phase, steps in wf.by_phase().items()
    if steps
}

# ``expanded=True`` keeps every phase group (incl. Other loads / Landing /
# Load-case plotting / Export) open in the sidebar rather than collapsing the tail
# behind a "View N more" expander on first run (review G3, M2-2).
pg = st.navigation(sections, expanded=True)
pg.run()
