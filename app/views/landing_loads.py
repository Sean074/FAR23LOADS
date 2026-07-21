"""Streamlit page for landing / ground loads (LGFACTOR + LANDLOAD, Ch 20).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Estimates the landing load factor (LGFACTOR, FAR 23.473(d)-(g)) from the drop-test
work-energy balance, then computes the tricycle-gear reaction loads for the level,
tail-down, one-wheel, braked-roll, side and supplementary-nose-wheel ground
conditions (LANDLOAD, FAR 23.473-23.499). Reads the per-CG weight & CG from
Project.mass (WTONECG) unless overridden here. Tricycle gear only (UG Table 2.1).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import (
    LandingInput,
    Project,
    UnitSystem,
    io,
    labels_for,
    si_scalar_label,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from farloads.derived_geometry import wing_reference
from farloads.modules.landing import build_landing, run


st.title("Landing Loads — LGFACTOR + LANDLOAD")
st.caption(
    "Python/Streamlit port of LGFACTOR.BAS + LANDLOAD.BAS (Reference 1 Ch 20): the "
    "landing load factor (FAR 23.473) and the tricycle-gear ground reactions "
    "(FAR 23.473–23.499)."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"weight","length","area_sqft",...} -> unit string
inp = project.landing or LandingInput()

with st.form("landing_loads_form"):
    st.subheader("Landing load factor (LGFACTOR)")
    c1, c2, c3 = st.columns(3)
    max_landing_weight_lb = c1.number_input(
        f"Max landing weight, W ({U['weight']})", min_value=0.0,
        value=float(round(to_display(inp.max_landing_weight_lb, "weight", system), 4)),
        help="Typically 0.95·MTOW (FAR 23.473(b)/(c)); not auto-derived (an engineering "
             "judgment call, not a duplicate of another slice).",
        key=f"max_landing_weight_{system.value}")
    gross_weight_lb = c2.number_input(
        f"Gross (max take-off) weight override, GW ({U['weight']})", min_value=0.0,
        value=float(round(to_display(inp.gross_weight_lb, "weight", system), 4)),
        help="0 → derived from the heaviest CG case (Project.mass).",
        key=f"gross_weight_{system.value}")
    # Step M2-6: wing area is single-sourced from the geometry wing (read-only here).
    _wr = wing_reference(project, "wing")
    _wing_area_display = _wr.s_sqft if _wr is not None else inp.wing_area_sqft
    c3.metric(f"Wing area S ({U['area_sqft']})",
              f"{to_display(_wing_area_display, 'area_sqft', system):.3f}",
              help="Single-sourced from the wing planform on the Geometry page (Step M2-6).")
    strut_stroke_in = c1.number_input(
        f"Strut stroke ({U['length']})", min_value=0.0,
        value=float(round(to_display(inp.strut_stroke_in, "length", system), 4)),
        key=f"strut_stroke_{system.value}")
    tire_od_in = c2.number_input(
        f"Tyre OD ({U['length']})", min_value=0.0,
        value=float(round(to_display(inp.tire_od_in, "length", system), 4)),
        key=f"tire_od_{system.value}")
    hub_diameter_in = c3.number_input(
        f"Hub diameter ({U['length']})", min_value=0.0,
        value=float(round(to_display(inp.hub_diameter_in, "length", system), 4)),
        key=f"hub_diameter_{system.value}")
    lift_factor = c1.number_input(
        "Wing lift factor, L (≤ 0.667)", min_value=0.0, max_value=0.667,
        value=float(inp.lift_factor))
    gear_load_factor = c2.number_input(
        "Gear load factor override, NLG", min_value=0.0, value=float(inp.gear_load_factor),
        help="0 → use LGFACTOR's computed N − L. LANDLOAD usually rounds it up.")

    tail_down_angle_deg = st.number_input("Tail-down ground angle (deg)", min_value=0.0,
                                          value=float(inp.tail_down_angle_deg))
    st.caption(
        "The **landing-gear geometry** (axle stations, tread, rolling radius, strut) is "
        "the single-source **Landing gear** section on the **Geometry** page (Step G6b) — "
        "edit it there; LANDLOAD reads it read-only.")
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.max_landing_weight_lb = to_imperial_scalar(max_landing_weight_lb, "weight", system)
    inp.gross_weight_lb = to_imperial_scalar(gross_weight_lb, "weight", system)
    # wing_area_sqft is derived from geometry (Step M2-6) -- not written here.
    inp.strut_stroke_in = to_imperial_scalar(strut_stroke_in, "length", system)
    inp.tire_od_in = to_imperial_scalar(tire_od_in, "length", system)
    inp.hub_diameter_in = to_imperial_scalar(hub_diameter_in, "length", system)
    inp.lift_factor = lift_factor
    inp.gear_load_factor = gear_load_factor
    inp.tail_down_angle_deg = tail_down_angle_deg
    project.landing = inp
    st.session_state["project"] = project
    st.success("Landing/ground inputs applied.")

if not inp.cg_cases and (project.mass is None or not project.mass.cases):
    st.warning("Provide the **Weight, CG & Inertia** (WTONECG) results, or enter the "
               "three landing CG cases in the project JSON, before computing reactions.")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    lf, reactions = build_landing(project)
    mod = run(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute landing loads: {exc}")
    st.stop()

st.subheader("Landing load factor")
m1, m2, m3 = st.columns(3)
m1.metric("Sink rate (ft/s)", f"{lf.sink_rate_fps:.3f}")
m2.metric("Airplane load factor N", f"{lf.airplane_load_factor:.3f}")
m3.metric("Gear load factor NLG", f"{lf.gear_load_factor:.3f}")

st.subheader("Gear reaction loads (ground line)")
st.caption(
    "On-screen reactions are **LIMIT** (oracle values, traceable to the manual). "
    "The CSV download below and the **Review/Export** pages report **ULTIMATE** "
    "= limit × 1.5 (14 CFR 23.303)."
)
_lbf_lbl = si_scalar_label("lbf", system)
# Display-only conversion of the ground-reaction forces; ``reactions``/``mod``
# (the CSV export below) are never touched -- they stay Imperial.
rows = [{
    "Case": c.case, "Condition": c.description, "FAR": c.far_reference, "CG": c.cg_name,
    f"VMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.vmp, "lbf", system), 1),
    f"DMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.dmp, "lbf", system), 1),
    f"SMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.smp, "lbf", system), 1),
    f"RMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.rmp, "lbf", system), 1),
    f"VNP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.vnp, "lbf", system), 1),
    f"DNP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.dnp, "lbf", system), 1),
    f"SNP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.snp, "lbf", system), 1),
    f"RESULT ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.result, "lbf", system), 1),
} for c in reactions]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.caption(f"VMP/DMP/SMP — vertical/drag/side main per wheel; VNP/DNP/SNP — nose. "
           f"Loads in {_lbf_lbl}, with respect to the ground line.")

st.download_button("Download landing loads (CSV)", io.load_cases_csv(mod),
                   file_name="landing_loads.csv", mime="text/csv")
