"""Streamlit page for aileron loads (AILERON, Ch 16).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes the critical deflected up/down aileron loads (FAR 23.455 / CAM 3.222)
from the STRSPEED design speeds (VA/VC/VD) and the aileron hinge geometry, with the
constant-forward / taper-to-TE simplified chordwise pressure.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_shell import optional_slice
from app_shell.components import active_system, gate, stop_page, unit_number_input
from app_shell.widget_keys import widget_key
from sloads import (
    AileronLoadsInput,
    Project,
    UnitSystem,
    convert_results,
    labels_for,
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
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
U = labels_for(system)  # {"area_sqft",...} -> unit string

if project.speeds is None:
    gate("Define the **Structural Speeds** (VA/VC/VD) first.", "structural_speeds")
    stop_page()

# Captured before the form mutates ``inp`` in place: ``store`` needs to
# know whether the project *had* this Optional slice (#145).
_existing_slice = project.aileron_loads
inp = project.aileron_loads or AileronLoadsInput()
with st.form("aileron_loads_form"):
    st.subheader(f"Aileron geometry & deflection ({U['area_sqft']})")
    c1, c2 = st.columns(2)
    down_deflection_deg = c1.number_input(
        "Max down deflection (deg)", min_value=0.0, value=float(inp.down_deflection_deg), step=1.0,
        key=widget_key("ail_down_defl"))
    up_deflection_deg = c2.number_input(
        "Max up deflection (deg)", min_value=0.0, value=float(inp.up_deflection_deg), step=1.0,
        key=widget_key("ail_up_defl"),
        help="Magnitude; applied as a negative (trailing-edge-up) throw.")
    area_fwd_hinge_sqft = unit_number_input(
        "Area fwd of hinge line, SAFWD", float(inp.area_fwd_hinge_sqft),
        kind="area_sqft", key="ail_safwd", min_value=0.0, step=0.1, container=c1)
    area_aft_hinge_sqft = unit_number_input(
        "Area aft of hinge line, SAAFT", float(inp.area_aft_hinge_sqft),
        kind="area_sqft", key="ail_saaft", min_value=0.0, step=0.1, container=c2)
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.down_deflection_deg = down_deflection_deg
    inp.up_deflection_deg = up_deflection_deg
    inp.area_fwd_hinge_sqft = area_fwd_hinge_sqft
    inp.area_aft_hinge_sqft = area_aft_hinge_sqft
    project.aileron_loads = optional_slice.store(inp, _existing_slice)
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
    stop_page()

display_conditions = convert_results(mod.conditions, system)
vals = {v.key: v.value for v in display_conditions[0].values}
force_u = "N" if system == UnitSystem.SI else "lb"
pressure_u = "kPa" if system == UnitSystem.SI else "lb/in²"
st.caption(
    "On-screen loads are **LIMIT** (oracle values, traceable to the manual). "
    "Every load below is **LIMIT** too: the downloads and the "
    "**Review/Export** pages state the 14 CFR 23.303 factor per case and "
    "apply it nowhere — apply it in the sizing analysis."
)
m1, m2, m3 = st.columns(3)
m1.metric(f"Critical down load ({force_u}, LIMIT)", f"{vals['critical_down_aileron_load']:,.2f}")
m2.metric(f"Critical up load ({force_u}, LIMIT)", f"{vals['critical_up_aileron_load']:,.2f}")
m3.metric("At speed (kt)", f"{vals['down_aileron_speed']:.0f} / {vals['up_aileron_speed']:.0f}")

st.subheader("Forward-of-hinge pressures")
st.write(pd.DataFrame([
    {"Case": "down", f"Load ({force_u}, LIMIT)": round(to_si_scalar(results[0].load_lb, "lbf", system), 2),
     f"Pressure fwd of hinge ({pressure_u}, LIMIT)":
         round(to_si_scalar(vals["pressure_fwd_of_hinge_down"], "psi", system), 4)},
    {"Case": "up", f"Load ({force_u}, LIMIT)": round(to_si_scalar(results[1].load_lb, "lbf", system), 2),
     f"Pressure fwd of hinge ({pressure_u}, LIMIT)":
         round(to_si_scalar(vals["pressure_fwd_of_hinge_up"], "psi", system), 4)},
]))

st.download_button("Download aileron loads (CSV)", sb.control_surface_csv(results, system=system),
                   file_name="aileron_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results, system=system),
                   file_name="aileron_loads.bdf", mime="text/plain")
