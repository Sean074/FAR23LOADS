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

from app_shell.components import render_applicability_banner, workflow_page_link
from app_shell.widget_keys import widget_key
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
# The project's *name* is the sidebar's (``app_shell.sidebar``, both GUIs --
# #65): it names the saved file, and a second widget for one field would
# write its own retained state back over the other's on every rerun.
col1, col2 = st.columns(2)
with col1:
    project.engineer = st.text_input("Engineer", value=project.engineer,
                                     key=widget_key("dash_engineer"))
with col2:
    project.date = st.text_input("Date", value=project.date, placeholder="YYYY-MM-DD",
                                 key=widget_key("dash_date"))

project.description = st.text_input(
    "Description", value=project.description,
    key=widget_key("dash_description"),
    placeholder="e.g. six-place single, normal category",
    help="One line describing the airplane; appears under the title on the summary report.")

# Document control (Step G8.2) -- the summary report's title page and signature
# block. Free text, all optional; a blank field is simply omitted from the report.
with st.expander("Document control (summary report title page)"):
    st.caption(
        "Carried onto the **Summary report**'s title page and signature block "
        "(Export page). All optional — a blank field is omitted rather than "
        "printed empty. **Revision** is free text you maintain (decision G8-5): "
        "the tool does not auto-increment it, so it can never disagree with your "
        "own drawing/report system of record."
    )
    d1, d2, d3 = st.columns(3)
    with d1:
        project.revision = st.text_input("Revision", value=project.revision,
                                         placeholder="e.g. A, B, IR",
                                         key=widget_key("dash_revision"))
    with d2:
        project.checked_by = st.text_input("Checked by", value=project.checked_by,
                                           key=widget_key("dash_checked_by"))
    with d3:
        project.approved_by = st.text_input("Approved by", value=project.approved_by,
                                            key=widget_key("dash_approved_by"))

st.session_state["project"] = project

# --------------------------------------------------------------------------- #
# Workflow progress
# --------------------------------------------------------------------------- #
st.header("Workflow progress")


def _status(step: wf.WorkflowStep):
    """(icon, label, help) for a step against the current project."""
    upstream = wf.missing_upstream(project, step)
    if upstream:
        return "⛔", "blocked", f"Needs: {', '.join(upstream)}"
    self_entered = wf.missing_self_entered(project, step)
    if self_entered:
        # Missing, but the page's own form enters it (#45) -- open, don't wait.
        return "🟡", "ready", f"Open to enter {', '.join(self_entered)} and compute"
    if step.produces is None:
        return "▫️", "view", "Ready — derived view (persists no slice)"
    if wf.is_produced(project, step):
        return "✅", "done", f"Produced `{step.produces}`"
    return "🟡", "ready", "Inputs ready — open to compute"


# Headline metric: how much of the producible work is done.
producible = [s for s in wf.STEPS if s.produces is not None]
done = [s for s in producible if wf.is_produced(project, s)]
blocked = [s for s in wf.STEPS if s.module and wf.missing_upstream(project, s)]

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
