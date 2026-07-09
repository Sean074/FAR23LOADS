"""FAR 23 LOADS — multipage entrypoint.

Run with:  streamlit run app/Home.py

The whole app is one reloadable ``project.json`` carried in ``st.session_state``.
Navigation is built explicitly from :mod:`farloads.workflow` (the single source of
truth for the step graph) and grouped into the six Phase-D workflow sections the
user moves through left-to-right:

    1 · Start ──▶ 2 · Airplane ──▶ 3 · Envelopes & Critical Conditions ──▶
    4 · Analysis ──▶ 5 · Loads Plots ──▶ 6 · Export

Using ``st.navigation`` (rather than the implicit ``pages/`` directory) means page
order and titles come from the workflow metadata, not filename numbers -- so there
is no numeric-prefix coupling and no duplicate-index collisions. A section with no
steps yet (``Loads Plots``, pending Step D7) is omitted from the sidebar rather
than shown empty.
"""

from __future__ import annotations

import streamlit as st

from farloads import workflow as wf

# Must be the first Streamlit call, and the ONLY set_page_config in the app
# (individual views must not call it again under st.navigation).
st.set_page_config(page_title="FAR 23 LOADS", layout="wide", page_icon="🛩️")

# Numbered, ordered section labels for the sidebar groups.
_PHASE_LABEL = {
    wf.START: "1 · Start",
    wf.AIRPLANE: "2 · Airplane",
    wf.ENVELOPES: "3 · Envelopes & Critical Conditions",
    wf.ANALYSIS: "4 · Analysis",
    wf.LOADS_PLOTS: "5 · Loads Plots",
    wf.EXPORT: "6 · Export",
}

_ICONS = {"dashboard": "🛩️"}


def _page(step: wf.WorkflowStep) -> st.Page:
    """A navigable page for a workflow step (view file is ``views/<key>.py``)."""
    return st.Page(
        f"views/{step.key}.py", title=step.title, url_path=step.key,
        icon=_ICONS.get(step.key), default=(step.key == "dashboard"),
    )


sections = {
    _PHASE_LABEL[phase]: [_page(s) for s in steps]
    for phase, steps in wf.by_phase().items()
    if steps
}

pg = st.navigation(sections)
pg.run()
