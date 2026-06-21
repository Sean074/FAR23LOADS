"""Streamlit page for aileron loads (AILERON, Ch 16).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes the critical deflected up/down aileron loads (FAR 23.455 / CAM 3.222)
from the STRSPEED design speeds (VA/VC/VD) and the aileron hinge geometry, with the
constant-forward / taper-to-TE simplified chordwise pressure.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import AileronLoadsInput, Project
from farloads.export import sbeam_bridge as sb
from farloads.modules.aileron import build_aileron, run


st.title("Aileron Loads — AILERON")
st.caption(
    "Python/Streamlit port of AILERON.BAS (Reference 1 Ch 16): the deflected "
    "(unsymmetrical) rolling-condition loads per FAR 23.455 / CAM 3.222(c), "
    "CL_ail = 0.04·DEFL, with the largest up and down loads selected."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.speeds is None:
    st.warning("Define the **Structural Speeds** (VA/VC/VD) first.")
    st.stop()

inp = project.aileron_loads or AileronLoadsInput()
st.subheader("Aileron geometry & deflection")
c1, c2 = st.columns(2)
inp.down_deflection_deg = c1.number_input(
    "Max down deflection (deg)", min_value=0.0, value=float(inp.down_deflection_deg), step=1.0)
inp.up_deflection_deg = c2.number_input(
    "Max up deflection (deg)", min_value=0.0, value=float(inp.up_deflection_deg), step=1.0,
    help="Magnitude; applied as a negative (trailing-edge-up) throw.")
inp.area_fwd_hinge_sqft = c1.number_input(
    "Area fwd of hinge line, SAFWD (sq ft)", min_value=0.0,
    value=float(inp.area_fwd_hinge_sqft), step=0.1)
inp.area_aft_hinge_sqft = c2.number_input(
    "Area aft of hinge line, SAAFT (sq ft)", min_value=0.0,
    value=float(inp.area_aft_hinge_sqft), step=0.1)
project.aileron_loads = inp
st.session_state["project"] = project

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    mod = run(project)
    results = build_aileron(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute aileron loads: {exc}")
    st.stop()

vals = {v.label: v.value for v in mod.conditions[0].values}
m1, m2, m3 = st.columns(3)
m1.metric("Critical down load (lb)", f"{vals['Critical down aileron load']:,.2f}")
m2.metric("Critical up load (lb)", f"{vals['Critical up aileron load']:,.2f}")
m3.metric("At speed (kt)", f"{vals['Down aileron speed']:.0f} / {vals['Up aileron speed']:.0f}")

st.subheader("Forward-of-hinge pressures")
st.write(pd.DataFrame([
    {"Case": "down", "Load (lb)": round(results[0].load_lb, 2),
     "Pressure fwd of hinge (lb/in²)": round(vals["Pressure fwd of hinge (down)"], 4)},
    {"Case": "up", "Load (lb)": round(results[1].load_lb, 2),
     "Pressure fwd of hinge (lb/in²)": round(vals["Pressure fwd of hinge (up)"], 4)},
]))

# Persist for the sbeam control-surface export.
if project.loads is not None:
    project.loads.control_surface = [
        r for r in project.loads.control_surface if not r.surface.startswith("aileron")
    ] + results
    st.session_state["project"] = project

st.download_button("Download aileron loads (CSV)", sb.control_surface_csv(results),
                   file_name="aileron_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results),
                   file_name="aileron_loads.bdf", mime="text/plain")
