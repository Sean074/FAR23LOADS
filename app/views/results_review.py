"""Results Review — consolidated governing loads across every component.

The Export-section pre-export summary: the governing (critical) load on each major
component from SELECT, then every module's results rolled up by workflow section.
Everything is recomputed live from the project inputs (the single source of
truth), so this page is never stale -- it does not rely on persisted result
slices.

One page of the multipage app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_shell.components import active_system, gate
from sloads import Project, UnitSystem, convert_results, registry
from sloads import workflow as wf
from sloads.modules.select import build_critical
from sloads.report import governing_loads_table, summary_rows

st.title("Results Review")
st.caption(
    "Consolidated governing loads across every component. Recomputed live from the "
    "project inputs — open the individual section pages for full distributions, plots "
    "and per-component exports."
)

project: Project = st.session_state.get("project", Project(name=""))
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()


# --------------------------------------------------------------------------- #
# Headline: governing (critical) loads from SELECT
# --------------------------------------------------------------------------- #
st.header("Governing loads (SELECT)")
st.caption(
    "Load columns are **ULTIMATE** (limit × SF), marked `-ULT` in the header; the "
    "`SF` column states the factor. Dimensionless/speed columns (n, CL, V) are "
    "unscaled and unmarked."
)

_COMPONENTS = [
    ("wing", "Wing"),
    ("htail", "Horizontal tail"),
    ("vtail", "Vertical tail"),
    ("fuselage", "Fuselage"),
]

try:
    critical = build_critical(project)
    # Carry forward the Critical Loads tab's persisted opt-out selection (Step
    # D5) -- case IDs are deterministic/stable, so this stays valid across the
    # fresh recompute above.
    if project.envelope is not None and project.envelope.critical is not None:
        critical.selected_case_ids = project.envelope.critical.selected_case_ids
except (ValueError, ZeroDivisionError, KeyError) as exc:
    critical = None
    gate(
        "Critical loads need the V-n environment — set up the **Flight Envelope "
        f"(V-n)** page (V-n diagram + Critical Loads tabs) first. ({exc})",
        "flight_envelope", kind="info",
    )

if critical is not None:
    if project.is_concept:
        st.warning("Concept category (C): governing loads are an **unverified "
                   "extrapolation** above the FAR 23 calibration band.")
    if critical.selected_case_ids:
        st.caption(
            "Showing the curated selection from the **Critical Loads** tab "
            "(some conditions were deselected there)."
        )
    selected_conditions = critical.selected()
    any_shown = False
    cols = st.columns(len(_COMPONENTS))
    for col, (key, title) in zip(cols, _COMPONENTS):
        conds = [c for c in selected_conditions if c.component == key]
        col.metric(title, f"{len(conds)} cond.")
    for key, title in _COMPONENTS:
        conds = [c for c in selected_conditions if c.component == key]
        if not conds:
            continue
        any_shown = True
        st.subheader(title)
        rows = governing_loads_table(conds, system)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if not any_shown:
        st.info("No governing conditions selected yet.")

# --------------------------------------------------------------------------- #
# All module results, rolled up by workflow phase
# --------------------------------------------------------------------------- #
st.header("All results by section")
st.caption("Every module whose inputs are present, grouped by workflow section.")

step_by_module = {s.module: s for s in wf.STEPS if s.module}
# A module with an *invalid* input raises, and that must stay visible (M2R-8) --
# but not by killing a page that renders every other module's results. Reported
# by name below instead (#145).
module_results, _module_failures = registry.run_all_modules_reporting(project)

if _module_failures:
    st.error(
        "These modules could not run — their inputs are present but not valid. "
        "Fix them on their own pages; every other result below is unaffected:\n\n"
        + "\n".join(f"- **{step_by_module[n].title if n in step_by_module else n}** — {e}"
                     for n, e in _module_failures))
by_phase: dict = {p: [] for p in wf.PHASES}
for mr in module_results:
    step = step_by_module.get(mr.module)
    if step is not None:
        by_phase[step.phase].append((step, mr))

if not module_results:
    gate("No module has the inputs it needs yet — start from the **Project Dashboard** "
         "and work the workflow left-to-right.", "dashboard")

for phase in wf.PHASES:
    entries = by_phase.get(phase, [])
    if not entries:
        continue
    st.subheader(phase)
    for step, mr in entries:
        with st.expander(f"{step.title}  ·  {len(mr.conditions)} condition(s)"):
            conds = convert_results(mr.conditions, system)
            # The one summary-shape dispatch (#95, C210-8/27), shared with the
            # module CSV channel and the oracle results page.
            rows = summary_rows(mr.module, conds)
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            else:
                st.caption("No tabular results.")
