"""Streamlit page for flap loads (FLAPLOAD, Ch 17).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes the critical flaps-extended flap load (FAR 23.345 / 23.457) over the
four-condition envelope, plus the FAR 23.457(b) slipstream and FAR 23.345(c)(1)
head-on-gust amplifications. Stall speeds / VF / weight come from STRSPEED; wing
area from the geometry; propeller power/diameter from the engine.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_shell.components import active_system, gate
from app_shell.widget_keys import widget_key
from sloads import (
    FlapLoadsInput,
    Project,
    UnitSystem,
    convert_results,
    labels_for,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from sloads.export import sbeam_bridge as sb
from sloads.modules.flap import build_flap, run

st.title("Flap Loads — FLAPLOAD")
st.caption(
    "Python/Streamlit port of FLAPLOAD.BAS (Reference 1 Ch 17): the critical "
    "flaps-extended load (Abbott & von Doenhoff Fig 98 flap-lift build-up), with "
    "the propeller-slipstream and head-on-gust amplifications."
)

project: Project = st.session_state.get("project", Project(name=""))
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
U = labels_for(system)  # {"area_sqft","length",...} -> unit string

if project.speeds is None:
    gate("Define the **Structural Speeds** (VS/VSF/VF, weight) first.", "structural_speeds")
    st.stop()

inp = project.flap_loads or FlapLoadsInput()
with st.form("flap_loads_form"):
    st.subheader("Flap geometry & deflection")
    c1, c2 = st.columns(2)
    flap_deflection_deg = c1.number_input(
        "Max flap deflection (deg)", min_value=0.0, value=float(inp.flap_deflection_deg), step=1.0)
    flap_chord_ratio = c2.number_input(
        "Flap chord / wing chord, E", min_value=0.0, value=float(inp.flap_chord_ratio), step=0.01)
    flap_area_one_side_sqft = c1.number_input(
        f"Flap area on one side, SF ({U['area_sqft']})", min_value=0.0,
        value=float(round(to_display(inp.flap_area_one_side_sqft, "area_sqft", system), 4)),
        step=0.1, key=widget_key(f"flap_area_{system.value}"))
    gust_load_factor = c2.number_input(
        "Flaps-extended gust load factor, NG", min_value=0.0,
        value=float(inp.gust_load_factor), step=0.1)
    nacelle_frontal_area_sqft = c1.number_input(
        f"Nacelle/fuselage frontal area, AF ({U['area_sqft']})", min_value=0.0,
        value=float(round(to_display(inp.nacelle_frontal_area_sqft, "area_sqft", system), 4)),
        step=0.1, key=widget_key(f"nacelle_area_{system.value}"))
    engine_butt_line_in = c2.number_input(
        f"Engine butt line, BLPROP ({U['length']}; 0 = fuselage)",
        value=float(round(to_display(inp.engine_butt_line_in, "length", system), 4)),
        step=1.0, key=widget_key(f"engine_bl_{system.value}"))
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.flap_deflection_deg = flap_deflection_deg
    inp.flap_chord_ratio = flap_chord_ratio
    inp.flap_area_one_side_sqft = to_imperial_scalar(flap_area_one_side_sqft, "area_sqft", system)
    inp.gust_load_factor = gust_load_factor
    inp.nacelle_frontal_area_sqft = to_imperial_scalar(nacelle_frontal_area_sqft, "area_sqft", system)
    inp.engine_butt_line_in = to_imperial_scalar(engine_butt_line_in, "length", system)
    project.flap_loads = inp
    st.session_state["project"] = project
    st.success("Flap geometry applied.")

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    mod = run(project)
    results = build_flap(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute flap loads: {exc}")
    st.stop()

display_conditions = convert_results(mod.conditions, system)
vals = {v.key: v.value for v in display_conditions[0].values}
force_u = "N" if system == UnitSystem.SI else "lb"
pressure_u = "kPa" if system == UnitSystem.SI else "lb/in²"
st.caption(
    "On-screen loads are **LIMIT** (oracle values, traceable to the manual). The "
    "CSV / FORCE-card downloads below and the **Review/Export** pages report "
    "**ULTIMATE** = limit × 1.5 (14 CFR 23.303)."
)
m1, m2, m3 = st.columns(3)
m1.metric(f"Critical flap load ({force_u}, LIMIT)", f"{vals['critical_flap_load_23_345_a']:,.0f}")
m2.metric(f"LE pressure ({pressure_u}, LIMIT)",
          f"{to_si_scalar(vals['le_pressure_te_half'], 'psi', system):.3f}")
m3.metric(f"Combined w/ gust ({force_u}, LIMIT)", f"{vals['flap_load_combined_w_gust']:,.0f}")

st.subheader("Flaps-extended envelope")
# (row heading, LoadValue key suffix) -- the heading is this page's wording,
# the suffix is the calc's key for the same envelope point (M4-9).
conditions = [("1G stall", "1g_stall"), ("2G stall", "2g_stall"),
              ("2G at VF", "2g_at_vf"), ("gust at VF", "gust_at_vf")]
st.write(pd.DataFrame([
    {"Condition": heading,
     "Flap CL": round(vals[f"flap_cl_{suffix}"], 4),
     f"Flap load ({force_u}, LIMIT)": round(vals[f"flap_load_{suffix}"], 1)}
    for heading, suffix in conditions
]))

if "Slipstream factor" in vals:
    st.subheader("Slipstream (FAR 23.457(b))")
    s1, s2, s3 = st.columns(3)
    s1.metric("Slipstream factor", f"{vals['slipstream_factor']:.3f}")
    s2.metric("Slipstream V at flap (kt)", f"{vals['slipstream_velocity_at_flap']:.1f}")
    length_u = "mm" if system == UnitSystem.SI else "in"
    s3.metric(f"Slipstream BL band ({length_u})",
              f"{vals['slipstream_inboard_bl']:.1f} … {vals['slipstream_outboard_bl']:.1f}")

st.download_button("Download flap loads (CSV)", sb.control_surface_csv(results, system=system),
                   file_name="flap_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results, system=system),
                   file_name="flap_loads.bdf", mime="text/plain")
