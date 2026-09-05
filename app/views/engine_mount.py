"""Streamlit page for FAR 23 engine-mount loads (port of ENGLOADS.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Multi-engine layouts are first-class: the sidebar picks the layout (1 nose / 2 or
4 wing-mounted engines) and which engine is being assessed; these are read/write
directly against ``Project.engines``/``Project.engine_layout`` (Step D6 -- no
separate ad hoc state store). The engine-parameter form edits the selected engine
only; switching engines/units without clicking Apply discards the in-progress
edit (Phase-D convention: unapplied widget state is never silently kept). A
single engine reduces exactly to the legacy behaviour (no ``[TAG]`` prefixes,
results identical to ``run_all``).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_shell import optional_slice
from app_shell.components import active_system, stop_page
from app_shell.widget_keys import widget_key
from sloads import (
    EngineInput,
    EngineLayout,
    EngineType,
    Project,
    Rotor,
    RotorDirection,
    RotorType,
    UnitSystem,
    convert_results,
    labels_for,
    run_all,
    to_display,
    to_imperial,
)
from sloads import io as sloads_io
from sloads.modules import engine as calc
from sloads.report import LoadChannel, load_cases_to_rows, text_report

st.title("Engine Mount Loads — FAR 23")
st.caption(
    "Python/Streamlit port of ENGLOADS.BAS (Hal C. McMaster, v3.0). "
    "Computes engine-mount design loads per FAR Part 23 Subpart C."
)


def _stated(entered, previous):
    """``entered``, or ``None`` when the widget is at zero and nothing was stated.

    Every Optional scalar on this form is seeded ``cur.x or 0``, so a field the
    project leaves unset renders as 0 and comes back as a *stated* zero. Keeping
    it unset unless a value is actually entered is what makes an Apply over an
    untouched form a no-op (#145).
    """
    if previous is None and not entered:
        return None
    return entered


def blank_engine() -> EngineInput:
    """An empty engine (all zero/blank), used to pad the working list beyond
    ``Project.engines`` when the selected layout needs more engines than are
    stored yet. Never committed until the form's Apply is clicked."""
    return EngineInput()


project: Project = st.session_state.get("project", Project(name=""))

# --------------------------------------------------------------------------- #
# Sidebar: units, layout, engine selection -- live navigation controls, not
# gated behind Apply (they pick *what* to edit/display, not engine parameters).
# --------------------------------------------------------------------------- #
_LAYOUTS = {
    "1 — Single (nose)": EngineLayout.SINGLE_NOSE,
    "2 — Twin (wing)": EngineLayout.TWIN_WING,
    "4 — Quad (wing)": EngineLayout.QUAD_WING,
}
_LAYOUT_LABELS = list(_LAYOUTS)

# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
U = labels_for(system)  # {"weight","length","torque","power"} -> unit string

with st.sidebar:
    st.caption(
        f"Input/output units: **{'Imperial' if system == UnitSystem.IMPERIAL else 'SI'}** "
        "(set in the sidebar's global **Units** control, above). Switching it "
        "re-seeds these fields with converted defaults."
    )

    st.header("Engine layout")
    default_layout_idx = (
        list(_LAYOUTS.values()).index(project.engine_layout)
        if project.engine_layout in _LAYOUTS.values() else 0
    )
    layout = _LAYOUTS[st.radio("Engines & arrangement", _LAYOUT_LABELS, index=default_layout_idx,
                               key=widget_key("em_layout"))]
    n_engines = layout.expected_count

    # Working copy for widget-seeding only; not written to project.engines until
    # Apply (padding a layout change never fabricates committed project data).
    engines_working = list(project.engines)
    if len(engines_working) < n_engines:
        engines_working.extend(blank_engine() for _ in range(n_engines - len(engines_working)))
    elif len(engines_working) > n_engines:
        engines_working = engines_working[:n_engines]

    if n_engines > 1:
        prev = min(st.session_state.get("engine_sel", 0), n_engines - 1)
        idx = st.radio(
            "Engine being assessed",
            options=range(n_engines),
            index=prev,
            key=widget_key("em_engine_sel"),
            format_func=lambda i: f"{i + 1} — {engines_working[i].engine_designation or 'engine'}",
        )
        st.session_state["engine_sel"] = idx
    else:
        idx = 0

cur = engines_working[idx]  # the engine currently being edited (canonical Imperial)


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


# --------------------------------------------------------------------------- #
# Inputs (for the selected engine) -- main body, inside one form + Apply.
# --------------------------------------------------------------------------- #
with st.form("engine_mount_form"):
    if n_engines > 1:
        st.info(f"Editing engine {idx + 1} of {n_engines}: **{cur.engine_designation or 'engine'}**")

    st.subheader("Engine identification")
    c0a, c0b, c0c = st.columns(3)
    engine_designation = c0a.text_input(
        "Engine manufacturer & designation", cur.engine_designation, key=widget_key(k("designation", False))
    )
    prop_designation = c0b.text_input(
        "Propeller manufacturer & designation", cur.prop_designation, key=widget_key(k("prop_desig", False))
    )
    type_label = c0c.radio(
        "Engine type", ["Reciprocating", "Turboprop"],
        index=1 if cur.is_turboprop else 0, key=widget_key(k("type", False)),
    )
    engine_type = (
        EngineType.TURBOPROP if type_label == "Turboprop" else EngineType.RECIPROCATING
    )
    is_turbo = engine_type == EngineType.TURBOPROP

    st.subheader("Certification basis")
    include_far25 = st.checkbox(
        "Add supplemental FAR 25 cases (optional)",
        value=project.include_far25,
        key=widget_key("em_include_far25"),
        help=(
            "Keeps every FAR 23 case and appends the three 14 CFR 25.361 / 25.371 "
            "cases that are *not* already covered by the corrected FAR 23 set "
            "(turbopropeller engines only): sudden stoppage with a 1g vertical, "
            "maximum engine acceleration torque, and gyroscopic loads at the A2 "
            "limit load factor. The duplicate FAR 25 torque cases were removed "
            "because they equal the corrected 23.361(a)(1)/(a)(2)/(a)(3). The FAR "
            "23 results are unchanged. Gyroscopic loads use the conservative fixed "
            "FAR 23.371(b) rates as an initial-concept stand-in for the 25.371 "
            "maneuver-derived rates. Applies to all engines in the project."
        ),
    )
    if include_far25:
        st.caption(
            "Supplemental FAR 25 cases apply to turbopropeller engines only; "
            "recip/jet installations show the FAR 23 set unchanged."
        )

    st.subheader("Common inputs")
    c1, c2, c3 = st.columns(3)
    with c1:
        limit_load_factor = st.number_input(
            "Limit load factor, Nz", value=float(cur.limit_load_factor), step=0.1, key=widget_key(k("nz", False)))
        engine_weight_lb = st.number_input(
            f"Engine weight, {U['weight']}", value=dflt(cur.engine_weight_lb, "weight"),
            step=1.0, key=widget_key(k("engwt")))
        prop_weight_lb = st.number_input(
            f"Propeller weight, {U['weight']}", value=dflt(cur.prop_weight_lb, "weight"),
            step=1.0, key=widget_key(k("propwt")))
        prop_diameter_in = st.number_input(
            f"Propeller diameter, {U['length']}", value=dflt(cur.prop_diameter_in, "length"),
            step=1.0, key=widget_key(k("propdia")))
        prop_blades = st.number_input(
            "Number of prop blades", value=cur.prop_blades, step=1, min_value=0, key=widget_key(k("blades", False)))
    with c2:
        st.markdown(f"**Engine CG ({U['length']})**")
        xeng = st.number_input("X engine", value=dflt(cur.engine_cg[0], "length"), key=widget_key(k("xeng")))
        yeng = st.number_input("Y engine", value=dflt(cur.engine_cg[1], "length"), key=widget_key(k("yeng")))
        zeng = st.number_input("Z engine", value=dflt(cur.engine_cg[2], "length"), key=widget_key(k("zeng")))
    with c3:
        st.markdown(f"**Propeller CG ({U['length']})**")
        xprop = st.number_input("X prop", value=dflt(cur.prop_cg[0], "length"), key=widget_key(k("xprop")))
        yprop = st.number_input("Y prop", value=dflt(cur.prop_cg[1], "length"), key=widget_key(k("yprop")))
        zprop = st.number_input("Z prop", value=dflt(cur.prop_cg[2], "length"), key=widget_key(k("zprop")))
        takeoff_rpm = st.number_input(
            "Takeoff RPM", value=float(cur.takeoff_rpm), step=10.0, key=widget_key(k("torpm", False)))
        max_cont_rpm = st.number_input(
            "Max continuous RPM", value=float(cur.max_cont_rpm), step=10.0, key=widget_key(k("contrpm", False)))

    # Type-specific inputs
    takeoff_hp = max_cont_hp = cylinders = None
    max_engine_torque = cruise_torque = hub_weight_lb = stop_time_s = None
    max_accel_torque = None
    design_yaw_rate = cur.design_yaw_rate_rad_s
    design_pitch_rate = cur.design_pitch_rate_rad_s
    prop_inertia = None
    rotors: list[Rotor] = []

    if not is_turbo:
        st.subheader("Reciprocating engine inputs")
        r1, r2, r3 = st.columns(3)
        with r1:
            takeoff_hp = st.number_input(
                f"Takeoff power, {U['power']}", value=dflt(cur.takeoff_hp or 0.0, "power"),
                step=1.0, key=widget_key(k("tohp")))
        with r2:
            max_cont_hp = st.number_input(
                f"Max continuous power, {U['power']}", value=dflt(cur.max_cont_hp or 0.0, "power"),
                step=1.0, key=widget_key(k("conthp")))
        with r3:
            cylinders = st.number_input(
                "Number of cylinders", value=cur.cylinders or 0, step=1, min_value=0, key=widget_key(k("cyl", False)))
    else:
        st.subheader("Turboprop engine inputs")
        t1, t2, t3 = st.columns(3)
        with t1:
            max_engine_torque = st.number_input(
                f"Max engine torque, {U['torque']}", value=dflt(cur.max_engine_torque or 0.0, "torque"),
                step=10.0, key=widget_key(k("engtorq")))
        with t2:
            cruise_torque = st.number_input(
                f"Max cont (cruise) torque, {U['torque']}", value=dflt(cur.cruise_torque or 0.0, "torque"),
                step=10.0, key=widget_key(k("cruztorq")))
        with t3:
            stop_time_s = st.number_input("Sudden-stoppage time, s", value=float(cur.stop_time_s or 0.3), step=0.05,
                                          help="FAA usually accepts 0.3 s", key=widget_key(k("dt", False)))

        if include_far25:
            st.markdown("**FAR 25 only**")
            f1, _ = st.columns([1, 2])
            with f1:
                max_accel_torque = st.number_input(
                    f"Max accelerating torque, {U['torque']}",
                    value=dflt(cur.max_accel_torque if cur.max_accel_torque is not None
                               else (cur.max_engine_torque or 0.0), "torque"),
                    step=10.0, key=widget_key(k("accel_torq")),
                    help=("FAR 25.361(a)(3)(ii). Leave at the max engine torque if no "
                          "separate accelerating-torque value is available."),
                )

            st.caption(
                "**25.371 gyroscopic rates (advisory).** The 25.371 gyro case uses a "
                "fixed FAR 23.371(b) stand-in (2.5 rad/s yaw, 1 rad/s pitch). If you "
                "know the concept's real design rates, enter them here: they do **not** "
                "change the computed moment, but if either exceeds the stand-in the "
                "result is flagged as under-predicting (0 = leave unset)."
            )
            g1, g2 = st.columns(2)
            with g1:
                _yaw_in = st.number_input(
                    "Design yaw rate, rad/s", value=float(cur.design_yaw_rate_rad_s or 0.0),
                    min_value=0.0, step=0.1, key=widget_key(k("design_yaw", False)),
                    help="Concept real 25.371 yaw rate. 0 = use the fixed 2.5 rad/s stand-in.",
                )
                design_yaw_rate = _yaw_in if _yaw_in > 0 else None
            with g2:
                _pitch_in = st.number_input(
                    "Design pitch rate, rad/s", value=float(cur.design_pitch_rate_rad_s or 0.0),
                    min_value=0.0, step=0.1, key=widget_key(k("design_pitch", False)),
                    help="Concept real 25.371 pitch rate. 0 = use the fixed 1 rad/s stand-in.",
                )
                design_pitch_rate = _pitch_in if _pitch_in > 0 else None

        st.markdown("**Propeller polar inertia**")
        p1, p2 = st.columns([1, 1])
        with p1:
            prop_inertia_mode = st.radio(
                "Source",
                ["Approximate from weight & diameter", "Enter measured value"],
                index=1 if cur.prop_inertia is not None else 0,
                key=widget_key(k("propinertia_mode", False)),
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
                    value=dflt(cur.prop_inertia or 0.0, "inertia"), step=0.1, format="%.4f",
                    key=widget_key(k("prop_inertia")),
                )
            else:
                hub_weight_lb = st.number_input(
                    f"Propeller hub weight, {U['weight']}", value=dflt(cur.hub_weight_lb or 0.0, "weight"), step=1.0,
                    help="Subtracted from propeller weight before approximating inertia.",
                    key=widget_key(k("hubwt")),
                )

        st.markdown("**Turbine rotor inertia by spool** (clockwise from pilot's view is positive RPM)")
        st.caption(
            "One row per spool. Leave the inertia column blank to approximate that "
            "spool as a solid disk (I = ½·m·r²)."
        )
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
            ] or [
                {"diameter_in": 0.0, "weight_lb": 0.0, "max_rpm": 0.0,
                 "inertia": float("nan"), "rotor_type": "T", "direction": "CC"},
            ]
        )
        rotor_df = st.data_editor(
            default_rotors,
            num_rows="dynamic",
            column_config={
                "diameter_in": st.column_config.NumberColumn(f"Diameter ({U['length']})"),
                "weight_lb": st.column_config.NumberColumn(f"Weight ({U['weight']})"),
                "max_rpm": st.column_config.NumberColumn("Max RPM (signed)"),
                "inertia": st.column_config.NumberColumn(
                    f"Measured inertia ({U['inertia']})",
                    help="Optional; blank = approximate from geometry."),
                "rotor_type": st.column_config.SelectboxColumn("Type", options=["C", "T"]),
                "direction": st.column_config.SelectboxColumn("Direction", options=["CW", "CC"]),
            },
            key=widget_key(f"rotors_e{idx}_{system.value}"),
        )
        for _, row in rotor_df.iterrows():
            if pd.isna(row["diameter_in"]) or float(row["diameter_in"]) <= 0:
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

    # ------------------------------------------------------------------ #
    # Balanced-cases input, not a mount input (backlog #10): the thrust this
    # engine puts into the airframe, applied at its hub in the assembled
    # flight cases. Outside the type-specific blocks because it is entered the
    # same way for both engine types.
    # ------------------------------------------------------------------ #
    st.markdown("**Design thrust (balanced flight cases)**")
    st.caption(
        "The thrust this engine delivers, applied as a `FORCE` at its hub "
        "(propeller CG, falling back to the engine CG) in every assembled "
        "**flight** balanced case and in the LRA beam model. Taken along the "
        "airplane x axis; the thrust-line incidence and toe angles, the "
        "propeller normal force and every slipstream term are not modelled. "
        "Nothing balances it -- the case's longitudinal load factor and pitch "
        "acceleration carry it -- and ground cases do not take it. "
        "0 = no thrust, which is what every case did before this input existed."
    )
    tcol, _ = st.columns([1, 2])
    with tcol:
        _thrust_in = st.number_input(
            f"Thrust per engine, {U['force']}",
            value=dflt(cur.thrust_lb or 0.0, "force"), min_value=0.0, step=10.0,
            key=widget_key(k("thrust")),
            help=("Applied forward at the hub. Requires a propeller CG or an "
                  "engine CG to act at."),
        )
    thrust_lb = _thrust_in if _thrust_in > 0 else None

    applied = st.form_submit_button("Apply", type="primary")

if applied:
    # Build the input from the widgets (values are in the selected unit system),
    # convert to the Imperial canonical form the calculation core expects, and
    # commit it into Project.engines/Project.engine_layout/Project.include_far25.
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
        # ``_stated`` on every Optional scalar whose widget seeds ``cur.x or 0``:
        # the widget cannot tell "not stated" from "zero", so taking its value
        # straight turned an unset field into a stated 0 on any Apply. That is
        # #121's class from the writing side -- and a stated ``cylinders = 0``
        # is what made a blank engine fail "Reciprocating engines must have at
        # least 2 cylinders" on the Results Review and Export pages (#145).
        takeoff_hp=_stated(takeoff_hp, cur.takeoff_hp),
        max_cont_hp=_stated(max_cont_hp, cur.max_cont_hp),
        cylinders=_stated(int(cylinders) if cylinders is not None else None,
                          cur.cylinders),
        max_engine_torque=_stated(max_engine_torque, cur.max_engine_torque),
        cruise_torque=_stated(cruise_torque, cur.cruise_torque),
        hub_weight_lb=_stated(hub_weight_lb, cur.hub_weight_lb),
        stop_time_s=_stated(stop_time_s, cur.stop_time_s),
        rotors=rotors,
        max_accel_torque=max_accel_torque,
        design_yaw_rate_rad_s=design_yaw_rate,
        design_pitch_rate_rad_s=design_pitch_rate,
        thrust_lb=thrust_lb,
        # No widget renders ``mounted_on`` (BM-4's engine parent), so it has to be
        # carried across explicitly: rebuilding the input from the form alone reset
        # a stated "fuselage" to None, and the deck then inferred the parent from
        # the CG butt line and marked it assumed -- silently replacing the user's
        # statement with a guess (#36). Carried by name rather than by
        # ``dataclasses.replace`` because ``to_imperial`` runs over the result, and
        # a carried *numeric* field would be converted a second time.
        mounted_on=engines_working[idx].mounted_on,
    )
    engines_working[idx] = to_imperial(inp_display, system)
    # An Apply may fill an engine in and may change one; it may not create the
    # *first* one out of a form nobody filled in. On a project with no engines
    # that attached a blank engine plus an ``engine_layout`` to match, and the
    # blank engine's zero cylinder count then took Results Review and Export
    # down on ``concept_heavy`` (#145 — the same rule as
    # ``app_shell.optional_slice``, which owns it for the record-shaped slices).
    if project.engines or optional_slice.store(
            engines_working[idx], None, seed=cur) is not None:
        project.engines = engines_working
        project.engine_layout = layout
        project.include_far25 = include_far25
        st.session_state["project"] = project
        st.success(f"Engine {idx + 1} applied.")
    else:
        st.warning("Nothing entered — fill the engine in above, then Apply.")

# --------------------------------------------------------------------------- #
# Results (against the committed Project.engines, not the unapplied working copy)
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Results")

if not project.engines:
    st.info("No engine defined yet — fill in the form above and Apply.")
    stop_page()

result_idx = min(idx, len(project.engines) - 1)
inp = project.engines[result_idx]

show_all = st.checkbox(
    "Show all engines", value=False, disabled=(len(project.engines) == 1),
    key=widget_key("em_show_all"),
    help="Off: results for the selected engine only. On: every engine, each "
         "condition prefixed with the engine designation.",
)

try:
    if show_all and len(project.engines) > 1:
        conditions = calc.run(project).conditions
    else:
        conditions = run_all(inp, include_far25=project.include_far25)
except Exception as exc:  # surface, don't crash
    st.error(f"Could not compute loads: {exc}")
    stop_page()

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

st.caption(
    "Load-case values below are **LIMIT** (oracle values, traceable to the "
    "manual). So is every load on the **Review/Export** pages: they state the "
    "14 CFR 23.303 factor per case and apply it nowhere — apply it in the "
    "sizing analysis. The 23.367(a)(2) sudden-stoppage torque is the one "
    "family the regulation prescribes ALREADY ULTIMATE (`SF=1.0`)."
)
for r in conditions:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        df = pd.DataFrame(
            [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        )
        st.dataframe(df, hide_index=True, width="stretch")
        if r.note:
            if r.note.lstrip().upper().startswith("WARNING"):
                st.warning(r.note)
            else:
                st.info(r.note)

# --------------------------------------------------------------------------- #
# Downloads (always cover every engine in the project)
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Downloads")
try:
    export_conditions = convert_results(calc.run(project).conditions, system)
except Exception as exc:
    st.warning(
        f"Could not build the all-engine export bundle yet: {exc}. Fill in and "
        "Apply every engine in the current layout first."
    )
    stop_page()
d1, d2, d3 = st.columns(3)

with d1:
    st.download_button(
        "Download text report",
        text_report(inp, export_conditions,
                   unit_system="Imperial" if system == UnitSystem.IMPERIAL else "SI",
                   channel=LoadChannel.LIMIT),
        file_name="engine_mount_loads.txt",
        mime="text/plain",
    )

with d2:
    csv = pd.DataFrame(load_cases_to_rows(
        export_conditions, channel=LoadChannel.LIMIT)).to_csv(index=False)
    st.download_button(
        "Download load cases (CSV)",
        csv,
        file_name="engine_mount_load_cases.csv",
        mime="text/csv",
        help="One row per load case: ID, description, application point, and applied loads.",
    )

with d3:
    # Saved inputs are always canonical Imperial (regardless of the UI unit
    # selection) since io.project_to_json serializes the real project as-is.
    input_json = sloads_io.project_to_json(project)
    st.download_button(
        "Save project (JSON)", input_json, file_name="engine.project.json",
        mime="application/json",
    )
