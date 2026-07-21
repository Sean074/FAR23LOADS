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

from components import gate

from farloads import OneEngineOutInput, Project, UnitSystem, convert_results, to_si_scalar
from farloads.modules.one_engine_out import run, time_history


st.title("One Engine Out — Vertical Tail Loads (ONENGOUT)")
st.caption(
    "Python/Streamlit port of ONENGOUT.BAS (Reference 1 Ch 11): the FAR 23.367 "
    "one-engine-out yaw transient, integrated until the pilot's rudder recovery, "
    "reporting the maximum vertical-tail load at each speed."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)

if not project.engines or len(project.engines) < 2:
    st.warning("One-engine-out needs a **multi-engine** layout (define ≥2 engines).")
    st.stop()
if project.vtail_loads is None:
    gate("Define the **vertical-tail geometry** (Flight Envelope (V-n) page, "
         "Critical Loads tab) first.", "flight_envelope")
    st.stop()
if project.mass is None or not project.mass.cases:
    gate("Run **Weight, CG & Inertia** (WTONECG, on the Weight & Mass Properties page) "
         "first — ONENGOUT needs IZZ.", "weight_mass")
    st.stop()

inp = project.one_engine_out or OneEngineOutInput()

with st.form("one_engine_out_form"):
    st.subheader("Failure transient")
    c1, c2, c3, c4 = st.columns(4)
    thrust_decay_time_s = c1.number_input("Thrust decay time (s)",
                                          value=float(inp.thrust_decay_time_s), min_value=0.0)
    windmill_drag_time_s = c2.number_input("Windmill drag buildup (s)",
                                           value=float(inp.windmill_drag_time_s), min_value=0.0)
    rudder_travel_time_s = c3.number_input("Full-rudder travel time (s)",
                                           value=float(inp.rudder_travel_time_s), min_value=0.0)
    time_step_s = c4.number_input("Time step (s)", value=float(inp.time_step_s or 0.05),
                                  min_value=0.005, step=0.005, format="%.3f")

    c5, c6 = st.columns(2)
    failed_engine_index = int(c5.selectbox(
        "Failed engine", options=list(range(len(project.engines))),
        index=min(inp.failed_engine_index, len(project.engines) - 1),
        format_func=lambda i: f"#{i} {project.engines[i].engine_designation or ''}".strip()))
    use_takeoff_power = c6.checkbox("Use take-off power (else max-continuous)",
                                    value=inp.use_takeoff_power)
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.thrust_decay_time_s = thrust_decay_time_s
    inp.windmill_drag_time_s = windmill_drag_time_s
    inp.rudder_travel_time_s = rudder_travel_time_s
    inp.time_step_s = time_step_s
    inp.failed_engine_index = failed_engine_index
    inp.use_takeoff_power = use_takeoff_power
    project.one_engine_out = inp
    st.session_state["project"] = project
    st.success("Failure-transient inputs applied.")

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
force_u = "N" if system == UnitSystem.SI else "lb"
display_conditions = convert_results(mod.conditions, system)
rows = []
for cond in display_conditions:
    v = {x.label: x.value for x in cond.values}
    rows.append({
        "Speed": cond.title.replace("One engine out — ", ""),
        "FAR": cond.far_reference,
        "V (kt EAS)": round(v["V (EAS)"], 1),
        f"Thrust ({force_u}, LIMIT)": round(v["Engine thrust"], 1),
        f"Windmill drag ({force_u}, LIMIT)": round(v["Windmill drag"], 1),
        "Max yaw rate (deg/s)": round(v["Max yawing velocity"], 2),
        f"Max tail load ({force_u}, LIMIT)": round(v["Max tail load"], 1),
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
        f"LT25 ({force_u}, LIMIT)": to_si_scalar(r.lt25, "lbf", system),
        f"LT50 ({force_u}, LIMIT)": to_si_scalar(r.lt50, "lbf", system),
        f"LT ({force_u}, LIMIT)": to_si_scalar(r.lt, "lbf", system),
        "rudder (deg)": r.rudder_deg,
    } for r in hist]).set_index("time")
    st.line_chart(df[["THETA (deg)", "THETADOT (deg/s)"]])
    st.line_chart(df[[f"LT25 ({force_u}, LIMIT)", f"LT50 ({force_u}, LIMIT)", f"LT ({force_u}, LIMIT)"]])
    st.download_button("Download time history (CSV)", df.to_csv(),
                       file_name=f"one_engine_out_{pick.split()[0]}.csv", mime="text/csv")
