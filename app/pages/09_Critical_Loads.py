"""Streamlit page for the critical flight loads (SELECT).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the governing (critical) load on each major component -- wing, horizontal
tail, vertical tail and fuselage -- selected from the FLTLOADS V-n matrix by the
SELECT module (Reference 1 Ch 9). The horizontal- and vertical-tail rational loads
appear when the Tail Loads inputs are present on the project.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import Project
from farloads.modules.select import build_critical

st.set_page_config(page_title="FAR 23 Critical Loads", layout="wide")

st.title("Critical Flight Loads — SELECT")
st.caption(
    "Python/Streamlit port of SELECT.BAS (Hal C. McMaster). Searches the balanced "
    "V-n matrix (FLTLOADS) for the governing wing, horizontal-tail, vertical-tail "
    "and fuselage loads (FAR 23.301/23.331/23.333/23.421/23.423/23.425/23.427/"
    "23.441/23.443)."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.flight_loads is None and project.envelope is None:
    st.warning("Define the flight-loads inputs on the **Flight Envelope** page first "
               "(SELECT searches the V-n matrix it produces).")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): critical loads are an **unverified "
               "extrapolation** above the FAR 23 calibration band.")

if project.tail_loads is None:
    st.info("Add the **Tail Loads** inputs to the project to include the rational "
            "horizontal-tail loads; the wing and fuselage conditions are shown regardless.")

try:
    critical = build_critical(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not select critical loads: {exc}")
    st.stop()

# Persist so downstream pages (Fuselage Loads, exports) can reuse the selection.
if project.envelope is not None:
    project.envelope.critical = critical
    st.session_state["project"] = project

_COMPONENTS = [
    ("wing", "Wing", "PHAA / PMAA / PLAA / NMAA, accelerated & steady roll"),
    ("htail", "Horizontal tail", "balancing, maneuver, gust, unsymmetrical"),
    ("vtail", "Vertical tail", "rudder, sideslip, yaw, side gust"),
    ("fuselage", "Fuselage", "load on wing, aft bending, greatest Nz"),
]

for key, title, sub in _COMPONENTS:
    conds = [c for c in critical.conditions if c.component == key]
    if not conds:
        continue
    st.subheader(f"{title} — {len(conds)} condition(s)")
    st.caption(sub)
    rows = []
    for c in conds:
        row = {"Condition": c.label, "FAR": c.far_reference, "V-n case": c.case}
        for lv in c.loads:
            row[lv.label] = round(lv.value, 2)
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
