"""FAR 23 LOADS — multi-page app home.

Load or save the single ``project.json`` that carries every module's inputs,
see a project summary, and run all registered modules at once. Each program in
the suite is a page under ``app/pages/``; Phase 0 ships the engine-mount page.

Run with:  streamlit run app/Home.py
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from farloads import Project, io as farloads_io, registry
from farloads.report import results_to_rows

st.set_page_config(page_title="FAR 23 LOADS", layout="wide")

st.title("FAR 23 LOADS")
st.caption(
    "Modern Python/Streamlit port of the McMaster FAR 23 LOADS suite. "
    "One reloadable project carries every module's inputs; each program is a "
    "page in the sidebar."
)

# --------------------------------------------------------------------------- #
# Project load / save
# --------------------------------------------------------------------------- #
st.header("Project")

uploaded = st.file_uploader("Load a project.json", type="json")
if uploaded is not None:
    project = farloads_io.project_from_dict(json.load(uploaded))
    st.session_state["project"] = project
    st.success(f"Loaded project: {project.name or '(unnamed)'}")

project: Project = st.session_state.get("project", Project(name=""))

col1, col2 = st.columns(2)
with col1:
    project.name = st.text_input("Project name", value=project.name)
with col2:
    st.download_button(
        "Save project (JSON)",
        farloads_io.project_to_json(project),
        file_name="project.json",
        mime="application/json",
    )
st.session_state["project"] = project

# --------------------------------------------------------------------------- #
# Summary of what the project carries
# --------------------------------------------------------------------------- #
st.header("Summary")
slices = {"engine": project.engine, "weight": project.weight}
present = [name for name, slice_ in slices.items() if slice_ is not None]
st.write(
    f"Schema version **{project.schema_version}**. "
    f"Input slices present: **{', '.join(present) or 'none yet'}**."
)

# --------------------------------------------------------------------------- #
# Run all registered modules
# --------------------------------------------------------------------------- #
st.header("Run all modules")
st.caption(f"Registered modules: {', '.join(registry.available()) or '(none)'}")

if st.button("Run all"):
    module_results = registry.run_all_modules(project)
    if not module_results:
        st.warning("No module had the inputs it needs. Fill a module page first.")
    for mr in module_results:
        st.subheader(mr.module)
        rows = results_to_rows(mr.conditions)
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        csv = farloads_io.load_cases_csv(mr)
        st.download_button(
            f"Download {mr.module} load cases (CSV)",
            csv,
            file_name=f"{mr.module}_load_cases.csv",
            mime="text/csv",
            key=f"csv_{mr.module}",
        )
