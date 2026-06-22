"""Streamlit page for FAR 23 engine-mount loads (port of ENGLOADS.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Multi-engine layouts are first-class: the sidebar picks the layout (1 nose / 2 or
4 wing-mounted engines) and which engine is being assessed. Each engine's inputs
are held canonically (Imperial) in ``st.session_state["engine_inputs"]`` so they
survive switching engines and unit systems; the widgets only edit the selected
engine and write their values back. A single engine reduces exactly to the legacy
behaviour (no ``[TAG]`` prefixes, results identical to ``run_all``).
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
from farloads.modules import engine as calc
from farloads.report import load_cases_to_rows, text_report


st.title("Engine Mount Loads — FAR 23")
st.caption(
    "Python/Streamlit port of ENGLOADS.BAS (Hal C. McMaster, v3.0). "
    "Computes engine-mount design loads per FAR Part 23 Subpart C."
)


def default_engine() -> EngineInput:
    """A fresh engine in canonical Imperial units (the IO-520-BB worked example).

    Used to seed the first engine and to pad the list when the layout grows.
    """
    return EngineInput(
        engine_designation="CONTINENTAL IO-520-BB",
        prop_designation="HARTZELL",
        engine_type=EngineType.RECIPROCATING,
        limit_load_factor=3.8,
        engine_weight_lb=505.0,
        engine_cg=(22.0, 0.0, -10.0),
        prop_weight_lb=74.0,
        prop_diameter_in=84.0,
        prop_blades=3,
        takeoff_rpm=2700.0,
        max_cont_rpm=2500.0,
        prop_cg=(-10.0, 0.0, 93.022),
        takeoff_hp=285.0,
        max_cont_hp=265.0,
        cylinders=6,
    )


# --------------------------------------------------------------------------- #
# Sidebar: units, layout, engine selection, per-engine identification
# --------------------------------------------------------------------------- #
_LAYOUTS = {
    "1 — Single (nose)": EngineLayout.SINGLE_NOSE,
    "2 — Twin (wing)": EngineLayout.TWIN_WING,
    "4 — Quad (wing)": EngineLayout.QUAD_WING,
}

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

    st.header("Engine layout")
    layout = _LAYOUTS[st.radio("Engines & arrangement", list(_LAYOUTS), index=0)]
    n_engines = layout.expected_count

    # Canonical Imperial store we own (survives reruns / engine + unit switches).
    if "engine_inputs" not in st.session_state:
        st.session_state["engine_inputs"] = [default_engine()]
    engines: list[EngineInput] = st.session_state["engine_inputs"]
    if len(engines) < n_engines:
        engines.extend(default_engine() for _ in range(n_engines - len(engines)))
    elif len(engines) > n_engines:
        del engines[n_engines:]

    if n_engines > 1:
        prev = min(st.session_state.get("engine_sel", 0), n_engines - 1)
        idx = st.radio(
            "Engine being assessed",
            options=range(n_engines),
            index=prev,
            format_func=lambda i: f"{i + 1} — {engines[i].engine_designation or 'engine'}",
        )
        st.session_state["engine_sel"] = idx
    else:
        idx = 0

cur = engines[idx]  # the engine currently being edited (canonical Imperial)


def dflt(imperial_value: float, kind: str) -> float:
    """Seed a widget's default value, converted into the selected unit system.

    Always returns ``float`` (even for whole-number stored values) so it never
    clashes with a float ``step`` in ``st.number_input``.
    """
    return float(round(to_display(imperial_value, kind, system), 4))


def k(name: str, unitful: bool = True) -> str:
    """Per-(engine, unit-system) widget key.

    Including the engine index re-seeds the widget when the selected engine
    changes; including the unit system re-seeds it (with converted defaults) when
    units switch. Unitful=False omits the system suffix for system-independent
    quantities (load factor, RPM, counts, time) so their value is not reset on a
    unit switch.
    """
    return f"e{idx}_{name}_{system.value}" if unitful else f"e{idx}_{name}"


with st.sidebar:
    st.header("Engine identification")
    engine_designation = st.text_input(
        "Engine manufacturer & designation", cur.engine_designation, key=k("designation", False)
    )
    prop_designation = st.text_input(
        "Propeller manufacturer & designation", cur.prop_designation, key=k("prop_desig", False)
    )
    type_label = st.radio(
        "Engine type", ["Reciprocating", "Turboprop"],
        index=1 if cur.is_turboprop else 0, key=k("type", False),
    )
    engine_type = (
        EngineType.TURBOPROP if type_label == "Turboprop" else EngineType.RECIPROCATING
    )
    is_turbo = engine_type == EngineType.TURBOPROP

# --------------------------------------------------------------------------- #
# Inputs (for the selected engine)
# --------------------------------------------------------------------------- #
if n_engines > 1:
    st.info(f"Editing engine {idx + 1} of {n_engines}: **{engine_designation or 'engine'}**")

st.subheader("Common inputs")
c1, c2, c3 = st.columns(3)
with c1:
    limit_load_factor = st.number_input("Limit load factor, Nz", value=cur.limit_load_factor, step=0.1, key=k("nz", False))
    engine_weight_lb = st.number_input(f"Engine weight, {U['weight']}", value=dflt(cur.engine_weight_lb, "weight"), step=1.0, key=k("engwt"))
    prop_weight_lb = st.number_input(f"Propeller weight, {U['weight']}", value=dflt(cur.prop_weight_lb, "weight"), step=1.0, key=k("propwt"))
    prop_diameter_in = st.number_input(f"Propeller diameter, {U['length']}", value=dflt(cur.prop_diameter_in, "length"), step=1.0, key=k("propdia"))
    prop_blades = st.number_input("Number of prop blades", value=cur.prop_blades, step=1, min_value=1, key=k("blades", False))
with c2:
    st.markdown(f"**Engine CG ({U['length']})**")
    xeng = st.number_input("X engine", value=dflt(cur.engine_cg[0], "length"), key=k("xeng"))
    yeng = st.number_input("Y engine", value=dflt(cur.engine_cg[1], "length"), key=k("yeng"))
    zeng = st.number_input("Z engine", value=dflt(cur.engine_cg[2], "length"), key=k("zeng"))
with c3:
    st.markdown(f"**Propeller CG ({U['length']})**")
    xprop = st.number_input("X prop", value=dflt(cur.prop_cg[0], "length"), key=k("xprop"))
    yprop = st.number_input("Y prop", value=dflt(cur.prop_cg[1], "length"), key=k("yprop"))
    zprop = st.number_input("Z prop", value=dflt(cur.prop_cg[2], "length"), key=k("zprop"))
    takeoff_rpm = st.number_input("Takeoff RPM", value=cur.takeoff_rpm, step=10.0, key=k("torpm", False))
    max_cont_rpm = st.number_input("Max continuous RPM", value=cur.max_cont_rpm, step=10.0, key=k("contrpm", False))

# Type-specific inputs
takeoff_hp = max_cont_hp = cylinders = None
max_engine_torque = cruise_torque = hub_weight_lb = stop_time_s = None
prop_inertia = None
rotors: list[Rotor] = []

if not is_turbo:
    st.subheader("Reciprocating engine inputs")
    r1, r2, r3 = st.columns(3)
    with r1:
        takeoff_hp = st.number_input(f"Takeoff power, {U['power']}", value=dflt(cur.takeoff_hp or 285.0, "power"), step=1.0, key=k("tohp"))
    with r2:
        max_cont_hp = st.number_input(f"Max continuous power, {U['power']}", value=dflt(cur.max_cont_hp or 265.0, "power"), step=1.0, key=k("conthp"))
    with r3:
        cylinders = st.number_input("Number of cylinders", value=cur.cylinders or 6, step=1, min_value=2, key=k("cyl", False))
else:
    st.subheader("Turboprop engine inputs")
    t1, t2, t3 = st.columns(3)
    with t1:
        max_engine_torque = st.number_input(f"Max engine torque, {U['torque']}", value=dflt(cur.max_engine_torque or 1970.0, "torque"), step=10.0, key=k("engtorq"))
    with t2:
        cruise_torque = st.number_input(f"Max cont (cruise) torque, {U['torque']}", value=dflt(cur.cruise_torque or 1800.0, "torque"), step=10.0, key=k("cruztorq"))
    with t3:
        stop_time_s = st.number_input("Sudden-stoppage time, s", value=cur.stop_time_s or 0.3, step=0.05,
                                      help="FAA usually accepts 0.3 s", key=k("dt", False))

    st.markdown("**Propeller polar inertia**")
    p1, p2 = st.columns([1, 1])
    with p1:
        prop_inertia_mode = st.radio(
            "Source",
            ["Approximate from weight & diameter", "Enter measured value"],
            index=1 if cur.prop_inertia is not None else 0,
            key=k("propinertia_mode", False),
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
                value=dflt(cur.prop_inertia or 9.174, "inertia"), step=0.1, format="%.4f",
                key=k("prop_inertia"),
            )
        else:
            hub_weight_lb = st.number_input(
                f"Propeller hub weight, {U['weight']}", value=dflt(cur.hub_weight_lb or 0.0, "weight"), step=1.0,
                help="Subtracted from propeller weight before approximating inertia.",
                key=k("hubwt"),
            )

    st.markdown("**Turbine rotor inertia by spool** (clockwise from pilot's view is positive RPM)")
    st.caption("One row per spool. Leave the inertia column blank to approximate that spool as a solid disk (I = ½·m·r²).")
    if cur.rotors:
        default_rotors = pd.DataFrame(
            [
                {
                    "diameter_in": dflt(r.diameter_in, "length"),
                    "weight_lb": dflt(r.weight_lb, "weight"),
                    "max_rpm": r.max_rpm,
                    "inertia": float("nan") if r.inertia is None else dflt(r.inertia, "inertia"),
                    "rotor_type": r.rotor_type.value,
                    "direction": r.direction.value,
                }
                for r in cur.rotors
            ]
        )
    else:
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
        key=f"rotors_e{idx}_{system.value}",
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
# convert to the Imperial canonical form the calculation core expects, and write
# it back to the per-engine store so it survives switching engines / units.
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
engines[idx] = inp  # keep the canonical store current

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Results")

# All engines are validated together as a Project (count must match the layout).
project = Project(name=engine_designation or "engine", engines=engines, engine_layout=layout)

show_all = st.checkbox(
    "Show all engines", value=False, disabled=(n_engines == 1),
    help="Off: results for the selected engine only. On: every engine, each "
         "condition prefixed with the engine designation.",
)

try:
    if show_all and n_engines > 1:
        conditions = calc.run(project).conditions
    else:
        conditions = run_all(inp)
except Exception as exc:  # surface, don't crash
    st.error(f"Could not compute loads: {exc}")
    st.stop()

# Results are computed in Imperial; convert to the selected system for display.
conditions = convert_results(conditions, system)

# Derived echo for the selected engine (the BASIC printed these intermediate
# values); scoped to the selected engine even when "Show all engines" is on.
ppwt = to_display(calc.combined_weight(inp), "weight", system)
xpp, ypp, zpp = (to_display(c, "length", system) for c in calc.combined_cg(inp))
m1, m2, m3 = st.columns(3)
m1.metric("Combined weight (prop+engine)", f"{ppwt:g} {U['weight']}")
m2.metric("Combined CG X / Y / Z", f"{xpp:g}, {ypp:g}, {zpp:g} {U['length']}")
m3.metric("Torque factor", f"{calc.torque_factor(inp):g}")

for r in conditions:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        df = pd.DataFrame(
            [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)
        if r.note:
            st.info(r.note)

# --------------------------------------------------------------------------- #
# Downloads (always cover every engine in the project)
# --------------------------------------------------------------------------- #
st.divider()
export_conditions = convert_results(calc.run(project).conditions, system)
d1, d2, d3 = st.columns(3)

with d1:
    st.download_button(
        "Download text report",
        text_report(inp, export_conditions, unit_system=unit_label),
        file_name="engine_mount_loads.txt",
        mime="text/plain",
    )

with d2:
    csv = pd.DataFrame(load_cases_to_rows(export_conditions)).to_csv(index=False)
    st.download_button(
        "Download load cases (CSV)",
        csv,
        file_name="engine_mount_load_cases.csv",
        mime="text/csv",
        help="One row per load case: ID, description, application point, and applied loads.",
    )

with d3:
    # Saved inputs are always canonical Imperial (regardless of the UI unit
    # selection) so the files stay consistent with the examples/ set. Every engine
    # and the chosen layout are wrapped in a Project so the file is a valid
    # project.json that the Home page, CLI and other modules can reload.
    input_json = farloads_io.project_to_json(project)
    st.download_button(
        "Save project (JSON)", input_json, file_name="engine.project.json",
        mime="application/json",
    )
