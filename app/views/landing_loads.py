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

from farloads import LandingGearInput, LandingInput, Project, io
from farloads.modules.landing import build_landing, run


st.title("Landing Loads — LGFACTOR + LANDLOAD")
st.caption(
    "Python/Streamlit port of LGFACTOR.BAS + LANDLOAD.BAS (Reference 1 Ch 20): the "
    "landing load factor (FAR 23.473) and the tricycle-gear ground reactions "
    "(FAR 23.473–23.499)."
)

project: Project = st.session_state.get("project", Project(name=""))
inp = project.landing or LandingInput()


def _gear_inputs(label: str, gear: LandingGearInput) -> LandingGearInput:
    st.markdown(f"**{label}**")
    c = st.columns(4)
    strut = c[0].selectbox(f"{label} strut", ["O", "S"],
                           index=0 if gear.strut == "O" else 1,
                           help="Oleo (O) or spring (S)", key=f"{label}_strut")
    rr = c[1].number_input(f"{label} rolling radius (in)", min_value=0.0,
                           value=float(gear.rolling_radius_in), key=f"{label}_rr")
    cc = st.columns(6)
    xc = cc[0].number_input(f"{label} X compressed", value=float(gear.axle_compressed[0]),
                            key=f"{label}_xc")
    zc = cc[1].number_input(f"{label} Z compressed", value=float(gear.axle_compressed[1]),
                            key=f"{label}_zc")
    xs = cc[2].number_input(f"{label} X static", value=float(gear.axle_static[0]),
                            key=f"{label}_xs")
    zs = cc[3].number_input(f"{label} Z static", value=float(gear.axle_static[1]),
                            key=f"{label}_zs")
    xe = cc[4].number_input(f"{label} X extended", value=float(gear.axle_extended[0]),
                            key=f"{label}_xe")
    ze = cc[5].number_input(f"{label} Z extended", value=float(gear.axle_extended[1]),
                            key=f"{label}_ze")
    return LandingGearInput((xc, zc), (xs, zs), (xe, ze), rr, strut)


st.subheader("Landing load factor (LGFACTOR)")
c1, c2, c3 = st.columns(3)
inp.max_landing_weight_lb = c1.number_input(
    "Max landing weight, W (lb)", min_value=0.0, value=float(inp.max_landing_weight_lb),
    help="Typically 0.95·MTOW (FAR 23.473(b)/(c)).")
inp.gross_weight_lb = c2.number_input(
    "Gross (max take-off) weight, GW (lb)", min_value=0.0, value=float(inp.gross_weight_lb))
inp.wing_area_sqft = c3.number_input(
    "Wing area, S (sq ft)", min_value=0.0, value=float(inp.wing_area_sqft),
    help="0 → read from the wing geometry surface.")
inp.strut_stroke_in = c1.number_input(
    "Strut stroke (in)", min_value=0.0, value=float(inp.strut_stroke_in))
inp.tire_od_in = c2.number_input("Tyre OD (in)", min_value=0.0, value=float(inp.tire_od_in))
inp.hub_diameter_in = c3.number_input("Hub diameter (in)", min_value=0.0,
                                      value=float(inp.hub_diameter_in))
inp.lift_factor = c1.number_input(
    "Wing lift factor, L (≤ 0.667)", min_value=0.0, max_value=0.667,
    value=float(inp.lift_factor))
inp.gear_load_factor = c2.number_input(
    "Gear load factor override, NLG", min_value=0.0, value=float(inp.gear_load_factor),
    help="0 → use LGFACTOR's computed N − L. LANDLOAD usually rounds it up.")

st.subheader("Landing gear geometry (LANDLOAD)")
inp.main_gear = _gear_inputs("Main gear", inp.main_gear)
inp.nose_gear = _gear_inputs("Nose gear", inp.nose_gear)
c = st.columns(2)
inp.tread_in = c[0].number_input("Tread between mains (in)", min_value=0.0,
                                 value=float(inp.tread_in))
inp.tail_down_angle_deg = c[1].number_input("Tail-down ground angle (deg)", min_value=0.0,
                                            value=float(inp.tail_down_angle_deg))

project.landing = inp
st.session_state["project"] = project

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
rows = [{
    "Case": c.case, "Condition": c.description, "FAR": c.far_reference, "CG": c.cg_name,
    "VMP": round(c.vmp, 1), "DMP": round(c.dmp, 1), "SMP": round(c.smp, 1),
    "RMP": round(c.rmp, 1), "VNP": round(c.vnp, 1), "DNP": round(c.dnp, 1),
    "SNP": round(c.snp, 1), "RESULT": round(c.result, 1),
} for c in reactions]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.caption("VMP/DMP/SMP — vertical/drag/side main per wheel; VNP/DNP/SNP — nose. "
           "Loads in lb, with respect to the ground line.")

st.download_button("Download landing loads (CSV)", io.load_cases_csv(mod),
                   file_name="landing_loads.csv", mime="text/csv")
