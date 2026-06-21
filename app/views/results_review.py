"""Results Review — consolidated governing loads across every component.

The Review-phase summary: the governing (critical) load on each major component
from SELECT, then every module's results rolled up by workflow phase. Everything
is recomputed live from the project inputs (the single source of truth), so this
page is never stale -- it does not rely on persisted result slices.

One page of the multipage app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import Project, registry
from farloads import workflow as wf
from farloads.modules.select import build_critical
from farloads.report import (
    has_load_case_data,
    load_cases_to_rows,
    results_to_rows,
)

st.title("Results Review")
st.caption(
    "Consolidated governing loads across every component. Recomputed live from the "
    "project inputs — open the individual phase pages for full distributions, plots "
    "and per-component exports."
)

project: Project = st.session_state.get("project", Project(name=""))

# --------------------------------------------------------------------------- #
# Headline: governing (critical) loads from SELECT
# --------------------------------------------------------------------------- #
st.header("Governing loads (SELECT)")

_COMPONENTS = [
    ("wing", "Wing"),
    ("htail", "Horizontal tail"),
    ("vtail", "Vertical tail"),
    ("fuselage", "Fuselage"),
]

try:
    critical = build_critical(project)
except (ValueError, ZeroDivisionError, KeyError) as exc:
    critical = None
    st.info(
        "Critical loads need the V-n environment — set up the **Flight Envelope** "
        f"and **Critical Loads** pages first. ({exc})"
    )

if critical is not None:
    if project.is_concept:
        st.warning("Concept category (C): governing loads are an **unverified "
                   "extrapolation** above the FAR 23 calibration band.")
    any_shown = False
    cols = st.columns(len(_COMPONENTS))
    for col, (key, title) in zip(cols, _COMPONENTS):
        conds = [c for c in critical.conditions if c.component == key]
        col.metric(title, f"{len(conds)} cond.")
    for key, title in _COMPONENTS:
        conds = [c for c in critical.conditions if c.component == key]
        if not conds:
            continue
        any_shown = True
        st.subheader(title)
        rows = []
        for c in conds:
            row = {"Condition": c.label, "FAR": c.far_reference, "V-n case": c.case}
            for lv in c.loads:
                row[lv.label] = round(lv.value, 2)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if not any_shown:
        st.info("No governing conditions selected yet.")

# --------------------------------------------------------------------------- #
# All module results, rolled up by workflow phase
# --------------------------------------------------------------------------- #
st.header("All results by phase")
st.caption("Every module whose inputs are present, grouped Define → Analyze → Review.")

step_by_module = {s.module: s for s in wf.STEPS if s.module}
module_results = registry.run_all_modules(project)
by_phase: dict = {p: [] for p in wf.PHASES}
for mr in module_results:
    step = step_by_module.get(mr.module)
    if step is not None:
        by_phase[step.phase].append((step, mr))

if not module_results:
    st.warning("No module has the inputs it needs yet. Fill in the Define pages first.")

for phase in wf.PHASES:
    entries = by_phase.get(phase, [])
    if not entries:
        continue
    st.subheader(phase)
    for step, mr in entries:
        with st.expander(f"{step.title}  ·  {len(mr.conditions)} condition(s)"):
            conds = mr.conditions
            rows = load_cases_to_rows(conds) if has_load_case_data(conds) else results_to_rows(conds)
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            else:
                st.caption("No tabular results.")
