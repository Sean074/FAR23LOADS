"""Export & Report — project JSON, load CSVs, sbeam BDF cards (placeholder)."""

from __future__ import annotations

import streamlit as st

from farloads import Project

st.title("Export & Report")
st.caption("Project JSON, per-module load CSVs, and sbeam BDF cards in one place.")

project: Project = st.session_state.get("project", Project(name=""))
st.info("Consolidated export view — under construction.")
