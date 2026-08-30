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

from app_shell import optional_slice
from app_shell.components import active_system, gate, stop_page
from app_shell.widget_keys import widget_key
from sloads import OneEngineOutInput, Project, UnitSystem, convert_results, to_si_scalar
from sloads.applicability import engine_failure_not_applicable
from sloads.modules.one_engine_out import PROPELLER_ONLY_NOTE, run, time_history

st.title("One Engine Out — Vertical Tail Loads (ONENGOUT)")
st.caption(
    "Python/Streamlit port of ONENGOUT.BAS (Reference 1 Ch 11): the FAR 23.367 "
    "one-engine-out yaw transient, integrated until the pilot's rudder recovery, "
    "reporting the maximum vertical-tail load at each speed."
)
# The coverage limitation, in the module's own wording (it also ships as the
# `engine-failure-propeller-only` standing limitation in every methods stamp) --
# a page that draws a fin load for a turbofan twin must say what it modelled.
st.caption("**Limitation:** " + PROPELLER_ONLY_NOTE + ".")

project: Project = st.session_state.get("project", Project(name=""))
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()

if not project.engines:
    # Not an applicability statement: an empty engine list is an unfinished
    # project, and the form below indexes into it (the failed-engine selector).
    gate("Define the **engines** first — the failed engine's power, propeller and "
         "butt line are what this page marches.", "engine_mount")
    stop_page()
# Was a hand-written ``len(project.engines) < 2`` here, which caught the single but
# not the twin whose *failed* engine sits at BL 0 -- also a zero yaw moment, also a
# simulation of nothing. The shared predicate is what the module refuses on and what
# the oracle GUI withholds its form on, so the three cannot disagree (#84, C210-43).
_not_applicable = engine_failure_not_applicable(project)
if _not_applicable:
    st.info(_not_applicable)
    stop_page()
if project.vtail_loads is None:
    gate("Define the **vertical-tail geometry** (Flight Envelope (V-n) page, "
         "Critical Loads tab) first.", "flight_envelope")
    stop_page()
if project.mass is None or not project.mass.cases:
    gate("Fill the itemised mass data base on the **Weight & Mass Properties** page "
         "(Weight, CG & Inertia tab) and press **Apply weight items** — that persists "
         "the mass slice ONENGOUT reads IZZ from.", "weight_mass")
    stop_page()

# Captured before the form mutates ``inp`` in place: ``store`` needs to
# know whether the project *had* this Optional slice (#145).
_existing_slice = project.one_engine_out
inp = project.one_engine_out or OneEngineOutInput()

with st.form("one_engine_out_form"):
    st.subheader("Failure transient")
    c1, c2, c3, c4 = st.columns(4)
    thrust_decay_time_s = c1.number_input("Thrust decay time (s)",
                                          value=float(inp.thrust_decay_time_s), min_value=0.0,
                                          key=widget_key("oeo_thrust_decay"))
    windmill_drag_time_s = c2.number_input("Windmill drag buildup (s)",
                                           value=float(inp.windmill_drag_time_s), min_value=0.0,
                                           key=widget_key("oeo_windmill_time"))
    rudder_travel_time_s = c3.number_input("Full-rudder travel time (s)",
                                           value=float(inp.rudder_travel_time_s), min_value=0.0,
                                           key=widget_key("oeo_rudder_time"))
    time_step_s = c4.number_input("Time step (s)", value=float(inp.time_step_s or 0.05),
                                  min_value=0.005, step=0.005, format="%.3f",
                                  key=widget_key("oeo_time_step"))

    c5, c6 = st.columns(2)
    failed_engine_index = int(c5.selectbox(
        "Failed engine", options=list(range(len(project.engines))),
        index=min(inp.failed_engine_index, len(project.engines) - 1),
        key=widget_key("oeo_failed_engine"),
        format_func=lambda i: f"#{i} {project.engines[i].engine_designation or ''}".strip()))
    use_takeoff_power = c6.checkbox("Use take-off power (else max-continuous)",
                                    value=inp.use_takeoff_power,
                                    key=widget_key("oeo_takeoff_power"))
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.thrust_decay_time_s = thrust_decay_time_s
    inp.windmill_drag_time_s = windmill_drag_time_s
    inp.rudder_travel_time_s = rudder_travel_time_s
    inp.time_step_s = time_step_s
    inp.failed_engine_index = failed_engine_index
    inp.use_takeoff_power = use_takeoff_power
    project.one_engine_out = optional_slice.store(inp, _existing_slice)
    st.session_state["project"] = project
    st.success("Failure-transient inputs applied.")

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    mod = run(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute one-engine-out loads: {exc}")
    stop_page()

st.subheader("Maximum tail loads by speed")
st.caption(
    "On-screen loads are **LIMIT** (oracle values, traceable to the manual). The "
    "**Review/Export** pages report **ULTIMATE** = limit × 1.5 (14 CFR 23.303)."
)
force_u = "N" if system == UnitSystem.SI else "lb"
display_conditions = convert_results(mod.conditions, system)
rows = []
for cond in display_conditions:
    v = {x.key: x.value for x in cond.values}
    rows.append({
        "Speed": cond.title.replace("One engine out — ", ""),
        "FAR": cond.far_reference,
        "V (kt EAS)": round(v["v_eas"], 1),
        f"Thrust ({force_u}, LIMIT)": round(v["engine_thrust"], 1),
        f"Windmill drag ({force_u}, LIMIT)": round(v["windmill_drag"], 1),
        "Max yaw rate (deg/s)": round(v["max_yawing_velocity"], 2),
        f"Max tail load ({force_u}, LIMIT)": round(v["max_tail_load"], 1),
        "Time to recovery (s)": round(v["time_to_recovery"], 2),
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
for cond in mod.conditions:
    if "NOT recovered" in cond.note:
        st.warning(f"**{cond.title}** — {cond.note}")

st.subheader("Time history")
labels = [cond.title.replace("One engine out — ", "") for cond in mod.conditions]
pick = st.selectbox("Speed case", options=labels, key=widget_key("oeo_speed_case"))
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
                       file_name=f"one_engine_out_{pick.split()[0]}_LIMIT.csv",
                       mime="text/csv")
