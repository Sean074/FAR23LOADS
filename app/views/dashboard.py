"""Project Dashboard — the Start-section landing page.

Load or save the single ``project.json``, name the project, and see workflow
progress at a glance: every step in :mod:`sloads.workflow`, grouped by the six
Phase-D sections, with a status that reads the live project (blocked / ready /
done). This replaces the old Phase-0 Home page, which only inspected four of the
~20 project slices.

One page of the multipage app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

import streamlit as st

from components import render_applicability_banner, workflow_page_link

from sloads import Project
from sloads import workflow as wf

st.title("🛩️ sloads — Project Dashboard")
st.caption(
    "Modern Python/Streamlit port of the McMaster FAR 23 LOADS suite. One reloadable "
    "project carries every module's inputs; work the sections left-to-right in the "
    "sidebar — **Start → Develop V-n diagram → Flight loads → Other loads → "
    "Landing loads → Load-case plotting → Export**. Open/Save a project against local disk from the "
    "**Project file** widget in the sidebar (every page)."
)

project: Project = st.session_state.get("project", Project(name=""))
render_applicability_banner(project)

# --------------------------------------------------------------------------- #
# Project metadata
# --------------------------------------------------------------------------- #
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    project.name = st.text_input("Project name", value=project.name)
with col2:
    project.engineer = st.text_input("Engineer", value=project.engineer)
with col3:
    project.date = st.text_input("Date", value=project.date, placeholder="YYYY-MM-DD")
st.session_state["project"] = project

# --------------------------------------------------------------------------- #
# Workflow progress
# --------------------------------------------------------------------------- #
st.header("Workflow progress")


def _status(step: wf.WorkflowStep):
    """(icon, label, help) for a step against the current project."""
    if not wf.requirements_met(project, step):
        missing = ", ".join(wf.missing_requirements(project, step))
        return "⛔", "blocked", f"Needs: {missing}"
    if step.produces is None:
        return "▫️", "view", "Ready — derived view (persists no slice)"
    if wf.is_produced(project, step):
        return "✅", "done", f"Produced `{step.produces}`"
    return "🟡", "ready", "Inputs ready — open to compute"


# Headline metric: how much of the producible work is done.
producible = [s for s in wf.STEPS if s.produces is not None]
done = [s for s in producible if wf.is_produced(project, s)]
blocked = [s for s in wf.STEPS if s.module and not wf.requirements_met(project, s)]

m1, m2, m3 = st.columns(3)
m1.metric("Slices produced", f"{len(done)} / {len(producible)}")
m2.metric("Steps blocked", len(blocked))
m3.metric("Schema version", project.schema_version)

st.progress(len(done) / len(producible) if producible else 0.0)

# Per-section checklists, one column each (this dashboard's own Start step and
# any section with no steps yet — Loads Plots, pending Step D7 — are omitted).
_sections = {
    phase: [s for s in steps if s.key != "dashboard"]
    for phase, steps in wf.by_phase().items()
}
_sections = {phase: steps for phase, steps in _sections.items() if steps}
phase_cols = st.columns(len(_sections))
for col, (phase, steps) in zip(phase_cols, _sections.items()):
    with col:
        st.subheader(phase)
        for s in steps:
            icon, _label, help_ = _status(s)
            bas = f" · {s.bas}" if s.bas else ""
            # Clickable row: emoji status as icon, summary + status + BAS in the
            # tooltip. Blocked steps stay navigable (M2-2) so the user lands on the
            # page and reads its own (now-linked) gating message.
            workflow_page_link(
                s.key, icon=icon, help=f"{s.summary}{bas}\n\n{help_}",
            )

st.caption(
    "✅ output present  ·  🟡 inputs ready, open the page to compute  ·  "
    "▫️ derived view (no stored slice)  ·  ⛔ blocked (open an upstream page first). "
    "Every row links to its page."
)
