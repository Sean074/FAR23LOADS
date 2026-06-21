"""Project Dashboard — the Overview landing page.

Load or save the single ``project.json``, name the project, and see workflow
progress at a glance: every step in :mod:`farloads.workflow`, grouped by phase,
with a status that reads the live project (blocked / ready / done). This replaces
the old Phase-0 Home page, which only inspected four of the ~20 project slices.

One page of the multipage app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

import json

import streamlit as st

from farloads import Project
from farloads import io as farloads_io
from farloads import workflow as wf

st.title("🛩️ FAR 23 LOADS — Project Dashboard")
st.caption(
    "Modern Python/Streamlit port of the McMaster FAR 23 LOADS suite. One reloadable "
    "project carries every module's inputs; work the phases left-to-right in the "
    "sidebar — **Define → Analyze → Review → Export**."
)

project: Project = st.session_state.get("project", Project(name=""))

# --------------------------------------------------------------------------- #
# Load / save the project file
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Project file")
    uploaded = st.file_uploader("Load project.json", type="json")
    if uploaded is not None:
        project = farloads_io.project_from_dict(json.load(uploaded))
        st.session_state["project"] = project
        st.success(f"Loaded: {project.name or '(unnamed)'}")

col1, col2 = st.columns([2, 1])
with col1:
    project.name = st.text_input("Project name", value=project.name)
with col2:
    st.write("")  # vertical nudge to align with the text input
    fname = (project.name or "project").strip().replace(" ", "_") or "project"
    st.download_button(
        "💾 Save project (JSON)",
        farloads_io.project_to_json(project),
        file_name=f"{fname}.json",
        mime="application/json",
        use_container_width=True,
    )
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

# Per-phase checklists, one column each.
phase_cols = st.columns(len(wf.PHASES))
for col, (phase, steps) in zip(phase_cols, wf.by_phase().items()):
    with col:
        st.subheader(phase)
        for s in steps:
            icon, _label, help_ = _status(s)
            bas = f" · _{s.bas}_" if s.bas else ""
            st.markdown(f"{icon} **{s.title}**{bas}", help=f"{s.summary}\n\n{help_}")

st.caption(
    "✅ output present  ·  🟡 inputs ready, open the page to compute  ·  "
    "▫️ derived view (no stored slice)  ·  ⛔ blocked (open an upstream page first)"
)
