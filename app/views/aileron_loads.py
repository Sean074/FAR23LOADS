"""Streamlit page for aileron loads (AILERON, Ch 16).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes the critical deflected up/down aileron loads (FAR 23.455 / CAM 3.222)
from the STRSPEED design speeds (VA/VC/VD) and the aileron hinge geometry, with the
constant-forward / taper-to-TE simplified chordwise pressure.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import gate

from sloads import (
    AileronLoadsInput,
    Project,
    UnitSystem,
    convert_results,
    labels_for,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from sloads.export import sbeam_bridge as sb
from sloads.modules.aileron import build_aileron, run


st.title("Aileron Loads — AILERON")
st.caption(
    "Python/Streamlit port of AILERON.BAS (Reference 1 Ch 16): the deflected "
    "(unsymmetrical) rolling-condition loads per FAR 23.455 / CAM 3.222(c), "
    "CL_ail = 0.04·DEFL, with the largest up and down loads selected."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"area_sqft",...} -> unit string

if project.speeds is None:
    gate("Define the **Structural Speeds** (VA/VC/VD) first.", "structural_speeds")
    st.stop()

inp = project.aileron_loads or AileronLoadsInput()
with st.form("aileron_loads_form"):
    st.subheader(f"Aileron geometry & deflection ({U['area_sqft']})")
    c1, c2 = st.columns(2)
    down_deflection_deg = c1.number_input(
        "Max down deflection (deg)", min_value=0.0, value=float(inp.down_deflection_deg), step=1.0)
    up_deflection_deg = c2.number_input(
        "Max up deflection (deg)", min_value=0.0, value=float(inp.up_deflection_deg), step=1.0,
        help="Magnitude; applied as a negative (trailing-edge-up) throw.")
    area_fwd_hinge_sqft = c1.number_input(
        f"Area fwd of hinge line, SAFWD ({U['area_sqft']})", min_value=0.0,
        value=float(round(to_display(inp.area_fwd_hinge_sqft, "area_sqft", system), 4)), step=0.1,
        key=f"safwd_{system.value}")
    area_aft_hinge_sqft = c2.number_input(
        f"Area aft of hinge line, SAAFT ({U['area_sqft']})", min_value=0.0,
        value=float(round(to_display(inp.area_aft_hinge_sqft, "area_sqft", system), 4)), step=0.1,
        key=f"saaft_{system.value}")
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.down_deflection_deg = down_deflection_deg
    inp.up_deflection_deg = up_deflection_deg
    inp.area_fwd_hinge_sqft = to_imperial_scalar(area_fwd_hinge_sqft, "area_sqft", system)
    inp.area_aft_hinge_sqft = to_imperial_scalar(area_aft_hinge_sqft, "area_sqft", system)
    project.aileron_loads = inp
    st.session_state["project"] = project
    st.success("Aileron geometry applied.")

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    mod = run(project)
    results = build_aileron(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute aileron loads: {exc}")
    st.stop()

display_conditions = convert_results(mod.conditions, system)
vals = {v.label: v.value for v in display_conditions[0].values}
force_u = "N" if system == UnitSystem.SI else "lb"
pressure_u = "kPa" if system == UnitSystem.SI else "lb/in²"
st.caption(
    "On-screen loads are **LIMIT** (oracle values, traceable to the manual). The "
    "CSV / FORCE-card downloads below and the **Review/Export** pages report "
    "**ULTIMATE** = limit × 1.5 (14 CFR 23.303)."
)
m1, m2, m3 = st.columns(3)
m1.metric(f"Critical down load ({force_u}, LIMIT)", f"{vals['Critical down aileron load']:,.2f}")
m2.metric(f"Critical up load ({force_u}, LIMIT)", f"{vals['Critical up aileron load']:,.2f}")
m3.metric("At speed (kt)", f"{vals['Down aileron speed']:.0f} / {vals['Up aileron speed']:.0f}")

st.subheader("Forward-of-hinge pressures")
st.write(pd.DataFrame([
    {"Case": "down", f"Load ({force_u}, LIMIT)": round(to_si_scalar(results[0].load_lb, "lbf", system), 2),
     f"Pressure fwd of hinge ({pressure_u}, LIMIT)":
         round(to_si_scalar(vals["Pressure fwd of hinge (down)"], "psi", system), 4)},
    {"Case": "up", f"Load ({force_u}, LIMIT)": round(to_si_scalar(results[1].load_lb, "lbf", system), 2),
     f"Pressure fwd of hinge ({pressure_u}, LIMIT)":
         round(to_si_scalar(vals["Pressure fwd of hinge (up)"], "psi", system), 4)},
]))

st.download_button("Download aileron loads (CSV)", sb.control_surface_csv(results),
                   file_name="aileron_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results),
                   file_name="aileron_loads.bdf", mime="text/plain")
