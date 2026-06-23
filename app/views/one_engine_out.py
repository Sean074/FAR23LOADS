"""Streamlit page for one-engine-out vertical-tail loads (ONENGOUT, Ch 11).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Time-marches the FAR 23.367 yaw transient after a critical-engine failure and reports
the maximum vertical-tail load at each speed (VC ultimate / VD limit / VS). The failed
engine, vertical-tail geometry, yaw inertia and speeds come from the project; the
failure-transient timing is edited below. Pick a case to re-run its full time history.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import OneEngineOutInput, Project
from farloads.modules.one_engine_out import run, time_history


st.title("One Engine Out — Vertical Tail Loads (ONENGOUT)")
st.caption(
    "Python/Streamlit port of ONENGOUT.BAS (Reference 1 Ch 11): the FAR 23.367 "
    "one-engine-out yaw transient, integrated until the pilot's rudder recovery, "
    "reporting the maximum vertical-tail load at each speed."
)

project: Project = st.session_state.get("project", Project(name=""))

if not project.engines or len(project.engines) < 2:
    st.warning("One-engine-out needs a **multi-engine** layout (define ≥2 engines).")
    st.stop()
if project.vtail_loads is None:
    st.warning("Define the **vertical-tail geometry** (Critical Loads page) first.")
    st.stop()
if project.mass is None or not project.mass.cases:
    st.warning("Run **Weight, CG & Inertia** (WTONECG) first — ONENGOUT needs IZZ.")
    st.stop()

inp = project.one_engine_out or OneEngineOutInput()

st.subheader("Failure transient")
c1, c2, c3, c4 = st.columns(4)
inp.thrust_decay_time_s = c1.number_input("Thrust decay time (s)",
                                          value=float(inp.thrust_decay_time_s), min_value=0.0)
inp.windmill_drag_time_s = c2.number_input("Windmill drag buildup (s)",
                                           value=float(inp.windmill_drag_time_s), min_value=0.0)
inp.rudder_travel_time_s = c3.number_input("Full-rudder travel time (s)",
                                           value=float(inp.rudder_travel_time_s), min_value=0.0)
inp.time_step_s = c4.number_input("Time step (s)", value=float(inp.time_step_s or 0.05),
                                  min_value=0.005, step=0.005, format="%.3f")

c5, c6 = st.columns(2)
inp.failed_engine_index = int(c5.selectbox(
    "Failed engine", options=list(range(len(project.engines))),
    index=min(inp.failed_engine_index, len(project.engines) - 1),
    format_func=lambda i: f"#{i} {project.engines[i].engine_designation or ''}".strip()))
inp.use_takeoff_power = c6.checkbox("Use take-off power (else max-continuous)",
                                    value=inp.use_takeoff_power)

project.one_engine_out = inp
st.session_state["project"] = project

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    mod = run(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute one-engine-out loads: {exc}")
    st.stop()

st.subheader("Maximum tail loads by speed")
st.caption(
    "On-screen loads are **LIMIT** (oracle values, traceable to the manual). The "
    "**Review/Export** pages report **ULTIMATE** = limit × 1.5 (14 CFR 23.303)."
)
rows = []
for cond in mod.conditions:
    v = {x.label: x.value for x in cond.values}
    rows.append({
        "Speed": cond.title.replace("One engine out — ", ""),
        "FAR": cond.far_reference,
        "V (kt EAS)": round(v["V (EAS)"], 1),
        "Thrust (lb, LIMIT)": round(v["Engine thrust"], 1),
        "Windmill drag (lb, LIMIT)": round(v["Windmill drag"], 1),
        "Max yaw rate (deg/s)": round(v["Max yawing velocity"], 2),
        "Max tail load (lb, LIMIT)": round(v["Max tail load"], 1),
        "Time to recovery (s)": round(v["Time to recovery"], 2),
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
for cond in mod.conditions:
    if "NOT recovered" in cond.note:
        st.warning(f"**{cond.title}** — {cond.note}")

st.subheader("Time history")
labels = [cond.title.replace("One engine out — ", "") for cond in mod.conditions]
pick = st.selectbox("Speed case", options=labels)
if st.button("Run time history"):
    hist = time_history(project, pick)
    df = pd.DataFrame([{
        "time": r.time, "THETA (deg)": r.theta, "THETADOT (deg/s)": r.theta_dot,
        "LT25 (lb, LIMIT)": r.lt25, "LT50 (lb, LIMIT)": r.lt50, "LT (lb, LIMIT)": r.lt,
        "rudder (deg)": r.rudder_deg,
    } for r in hist]).set_index("time")
    st.line_chart(df[["THETA (deg)", "THETADOT (deg/s)"]])
    st.line_chart(df[["LT25 (lb, LIMIT)", "LT50 (lb, LIMIT)", "LT (lb, LIMIT)"]])
    st.download_button("Download time history (CSV)", df.to_csv(),
                       file_name=f"one_engine_out_{pick.split()[0]}.csv", mime="text/csv")
