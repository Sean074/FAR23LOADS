"""Streamlit page for FAR 23 engine-mount loads (port of ENGLOADS.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import (
    EngineInput,
    EngineLayout,
    EngineType,
    Project,
    Rotor,
    RotorType,
    RotorDirection,
    UnitSystem,
    convert_results,
    labels_for,
    run_all,
    to_display,
    to_imperial,
)
from farloads import io as farloads_io
from farloads.report import load_cases_to_rows, text_report


st.title("Engine Mount Loads — FAR 23")
st.caption(
    "Python/Streamlit port of ENGLOADS.BAS (Hal C. McMaster, v3.0). "
    "Computes engine-mount design loads per FAR Part 23 Subpart C."
)

# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Units")
    unit_label = st.radio(
        "Input / output units",
        ["Imperial", "SI"],
        index=0,
        help=(
            "Imperial: lb, in, ft-lb, hp. SI: kg, mm, N·m, kW. "
            "Calculations always run in Imperial internally so results match "
            "the FAR 23 LOADS manual; SI values are converted at the boundary. "
            "Switching units re-seeds the fields with converted defaults."
        ),
    )
    system = UnitSystem.SI if unit_label == "SI" else UnitSystem.IMPERIAL
    U = labels_for(system)  # {"weight","length","torque","power"} -> unit string

    st.header("Engine identification")
    engine_designation = st.text_input(
        "Engine manufacturer & designation", "CONTINENTAL IO-520-BB"
    )
    prop_designation = st.text_input("Propeller manufacturer & designation", "HARTZELL")
    type_label = st.radio("Engine type", ["Reciprocating", "Turboprop"], index=0)
    engine_type = (
        EngineType.TURBOPROP if type_label == "Turboprop" else EngineType.RECIPROCATING
    )
    is_turbo = engine_type == EngineType.TURBOPROP


def dflt(imperial_value: float, kind: str) -> float:
    """Seed a widget's default value, converted into the selected unit system."""
    return round(to_display(imperial_value, kind, system), 4)

st.subheader("Common inputs")
c1, c2, c3 = st.columns(3)
with c1:
    limit_load_factor = st.number_input("Limit load factor, Nz", value=3.8, step=0.1)
    engine_weight_lb = st.number_input(f"Engine weight, {U['weight']}", value=dflt(505.0, "weight"), step=1.0)
    prop_weight_lb = st.number_input(f"Propeller weight, {U['weight']}", value=dflt(74.0, "weight"), step=1.0)
    prop_diameter_in = st.number_input(f"Propeller diameter, {U['length']}", value=dflt(84.0, "length"), step=1.0)
    prop_blades = st.number_input("Number of prop blades", value=3, step=1, min_value=1)
with c2:
    st.markdown(f"**Engine CG ({U['length']})**")
    xeng = st.number_input("X engine", value=dflt(22.0, "length"))
    yeng = st.number_input("Y engine", value=dflt(0.0, "length"))
    zeng = st.number_input("Z engine", value=dflt(-10.0, "length"))
with c3:
    st.markdown(f"**Propeller CG ({U['length']})**")
    xprop = st.number_input("X prop", value=dflt(-10.0, "length"))
    yprop = st.number_input("Y prop", value=dflt(0.0, "length"))
    zprop = st.number_input("Z prop", value=dflt(93.022, "length"))
    takeoff_rpm = st.number_input("Takeoff RPM", value=2700.0, step=10.0)
    max_cont_rpm = st.number_input("Max continuous RPM", value=2500.0, step=10.0)

# Type-specific inputs
takeoff_hp = max_cont_hp = cylinders = None
max_engine_torque = cruise_torque = hub_weight_lb = stop_time_s = None
prop_inertia = None
rotors: list[Rotor] = []

if not is_turbo:
    st.subheader("Reciprocating engine inputs")
    r1, r2, r3 = st.columns(3)
    with r1:
        takeoff_hp = st.number_input(f"Takeoff power, {U['power']}", value=dflt(285.0, "power"), step=1.0)
    with r2:
        max_cont_hp = st.number_input(f"Max continuous power, {U['power']}", value=dflt(265.0, "power"), step=1.0)
    with r3:
        cylinders = st.number_input("Number of cylinders", value=6, step=1, min_value=2)
else:
    st.subheader("Turboprop engine inputs")
    t1, t2, t3 = st.columns(3)
    with t1:
        max_engine_torque = st.number_input(f"Max engine torque, {U['torque']}", value=dflt(1970.0, "torque"), step=10.0)
    with t2:
        cruise_torque = st.number_input(f"Max cont (cruise) torque, {U['torque']}", value=dflt(1800.0, "torque"), step=10.0)
    with t3:
        stop_time_s = st.number_input("Sudden-stoppage time, s", value=0.3, step=0.05,
                                      help="FAA usually accepts 0.3 s")

    st.markdown("**Propeller polar inertia**")
    p1, p2 = st.columns([1, 1])
    with p1:
        prop_inertia_mode = st.radio(
            "Source",
            ["Approximate from weight & diameter", "Enter measured value"],
            help=(
                "Approximate models the blades as thin rods, I = m·L²/3, with the "
                "hub weight removed (it sits near the axis). Enter a measured "
                "value if the propeller manufacturer provides the polar moment "
                "of inertia."
            ),
        )
    with p2:
        if prop_inertia_mode == "Enter measured value":
            prop_inertia = st.number_input(
                f"Measured propeller polar inertia, {U['inertia']}",
                value=dflt(9.174, "inertia"), step=0.1, format="%.4f",
            )
        else:
            hub_weight_lb = st.number_input(
                f"Propeller hub weight, {U['weight']}", value=dflt(0.0, "weight"), step=1.0,
                help="Subtracted from propeller weight before approximating inertia.",
            )

    st.markdown("**Rotors** (clockwise from pilot's view is positive RPM)")
    st.caption("Leave the inertia column blank to approximate each rotor as a solid disk (I = ½·m·r²).")
    default_rotors = pd.DataFrame(
        [
            {"diameter_in": dflt(10.0, "length"), "weight_lb": dflt(19.34, "weight"), "max_rpm": -33750.0, "inertia": float("nan"), "rotor_type": "T", "direction": "CC"},
            {"diameter_in": dflt(9.0, "length"), "weight_lb": dflt(15.66, "weight"), "max_rpm": 33000.0, "inertia": float("nan"), "rotor_type": "T", "direction": "CW"},
        ]
    )
    rotor_df = st.data_editor(
        default_rotors,
        num_rows="dynamic",
        column_config={
            "diameter_in": st.column_config.NumberColumn(f"Diameter ({U['length']})"),
            "weight_lb": st.column_config.NumberColumn(f"Weight ({U['weight']})"),
            "max_rpm": st.column_config.NumberColumn("Max RPM (signed)"),
            "inertia": st.column_config.NumberColumn(f"Measured inertia ({U['inertia']})", help="Optional; blank = approximate from geometry."),
            "rotor_type": st.column_config.SelectboxColumn("Type", options=["C", "T"]),
            "direction": st.column_config.SelectboxColumn("Direction", options=["CW", "CC"]),
        },
        key=f"rotors_{system.value}",
    )
    for _, row in rotor_df.iterrows():
        if pd.isna(row["diameter_in"]):
            continue
        measured = row.get("inertia")
        rotors.append(
            Rotor(
                diameter_in=float(row["diameter_in"]),
                weight_lb=float(row["weight_lb"]),
                max_rpm=float(row["max_rpm"]),
                rotor_type=RotorType(row["rotor_type"]),
                direction=RotorDirection(row["direction"]),
                inertia=None if pd.isna(measured) else float(measured),
            )
        )

# Build the input from the widgets (values are in the selected unit system),
# then convert to the Imperial canonical form the calculation core expects.
inp_display = EngineInput(
    engine_designation=engine_designation,
    prop_designation=prop_designation,
    engine_type=engine_type,
    limit_load_factor=limit_load_factor,
    engine_weight_lb=engine_weight_lb,
    engine_cg=(xeng, yeng, zeng),
    prop_weight_lb=prop_weight_lb,
    prop_diameter_in=prop_diameter_in,
    prop_inertia=prop_inertia,
    prop_blades=int(prop_blades),
    takeoff_rpm=takeoff_rpm,
    max_cont_rpm=max_cont_rpm,
    prop_cg=(xprop, yprop, zprop),
    takeoff_hp=takeoff_hp,
    max_cont_hp=max_cont_hp,
    cylinders=int(cylinders) if cylinders is not None else None,
    max_engine_torque=max_engine_torque,
    cruise_torque=cruise_torque,
    hub_weight_lb=hub_weight_lb,
    stop_time_s=stop_time_s,
    rotors=rotors,
)
inp = to_imperial(inp_display, system)

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Results")

try:
    results = run_all(inp)
except Exception as exc:  # surface, don't crash
    st.error(f"Could not compute loads: {exc}")
    st.stop()

# Results are computed in Imperial; convert to the selected system for display.
results = convert_results(results, system)

# Derived echo (the BASIC printed these intermediate values)
from farloads.modules import engine as calc

ppwt = to_display(calc.combined_weight(inp), "weight", system)
xpp, ypp, zpp = (to_display(c, "length", system) for c in calc.combined_cg(inp))
m1, m2, m3 = st.columns(3)
m1.metric("Combined weight (prop+engine)", f"{ppwt:g} {U['weight']}")
m2.metric("Combined CG X / Y / Z", f"{xpp:g}, {ypp:g}, {zpp:g} {U['length']}")
m3.metric("Torque factor", f"{calc.torque_factor(inp):g}")

for r in results:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        df = pd.DataFrame(
            [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)
        if r.note:
            st.info(r.note)

# --------------------------------------------------------------------------- #
# Downloads
# --------------------------------------------------------------------------- #
st.divider()
d1, d2, d3 = st.columns(3)

with d1:
    st.download_button(
        "Download text report",
        text_report(inp, results, unit_system=unit_label),
        file_name="engine_mount_loads.txt",
        mime="text/plain",
    )

with d2:
    csv = pd.DataFrame(load_cases_to_rows(results)).to_csv(index=False)
    st.download_button(
        "Download load cases (CSV)",
        csv,
        file_name="engine_mount_load_cases.csv",
        mime="text/csv",
        help="One row per load case: ID, description, application point, and applied loads.",
    )

with d3:
    # Saved inputs are always canonical Imperial (regardless of the UI unit
    # selection) so the files stay consistent with the examples/ set. The engine
    # slice is wrapped in a Project so the file is a valid project.json that the
    # Home page, CLI and other modules can reload.
    project = Project(name=engine_designation or "engine", engines=[inp],
                      engine_layout=EngineLayout.SINGLE_NOSE)
    input_json = farloads_io.project_to_json(project)
    st.download_button(
        "Save project (JSON)", input_json, file_name="engine.project.json",
        mime="application/json",
    )
