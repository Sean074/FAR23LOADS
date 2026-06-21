"""FAR 23 LOADS — multipage entrypoint.

Run with:  streamlit run app/Home.py

The whole app is one reloadable ``project.json`` carried in ``st.session_state``.
Navigation is built explicitly from :mod:`farloads.workflow` (the single source of
truth for the step graph) and grouped into the four workflow phases the user moves
through left-to-right:

    Overview ──▶ 1 · Define ──▶ 2 · Analyze ──▶ 3 · Review ──▶ 4 · Export

Using ``st.navigation`` (rather than the implicit ``pages/`` directory) means page
order and titles come from the workflow metadata, not filename numbers -- so there
is no numeric-prefix coupling and no duplicate-index collisions.
"""

from __future__ import annotations

import streamlit as st

from farloads import workflow as wf

# Must be the first Streamlit call, and the ONLY set_page_config in the app
# (individual views must not call it again under st.navigation).
st.set_page_config(page_title="FAR 23 LOADS", layout="wide", page_icon="🛩️")

# Numbered, ordered section labels for the sidebar groups.
_PHASE_LABEL = {
    wf.DEFINE: "1 · Define",
    wf.ANALYZE: "2 · Analyze",
    wf.REVIEW: "3 · Review",
    wf.EXPORT: "4 · Export",
}


def _page(step: wf.WorkflowStep) -> st.Page:
    """A navigable page for a workflow step (view file is ``views/<key>.py``)."""
    return st.Page(f"views/{step.key}.py", title=step.title, url_path=step.key)


# Overview / landing page.
dashboard = st.Page(
    "views/dashboard.py", title="Project Dashboard", icon="🛩️",
    url_path="dashboard", default=True,
)

sections = {"Overview": [dashboard]}
for phase, steps in wf.by_phase().items():
    sections[_PHASE_LABEL[phase]] = [_page(s) for s in steps]

pg = st.navigation(sections)
pg.run()
