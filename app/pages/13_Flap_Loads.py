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

from farloads import FlapLoadsInput, Project
from farloads.export import sbeam_bridge as sb
from farloads.modules.flap import build_flap, run

st.set_page_config(page_title="FAR 23 Flap Loads", layout="wide")

st.title("Flap Loads — FLAPLOAD")
st.caption(
    "Python/Streamlit port of FLAPLOAD.BAS (Reference 1 Ch 17): the critical "
    "flaps-extended load (Abbott & von Doenhoff Fig 98 flap-lift build-up), with "
    "the propeller-slipstream and head-on-gust amplifications."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.speeds is None:
    st.warning("Define the **Structural Speeds** (VS/VSF/VF, weight) first.")
    st.stop()

inp = project.flap_loads or FlapLoadsInput()
st.subheader("Flap geometry & deflection")
c1, c2 = st.columns(2)
inp.flap_deflection_deg = c1.number_input(
    "Max flap deflection (deg)", min_value=0.0, value=float(inp.flap_deflection_deg), step=1.0)
inp.flap_chord_ratio = c2.number_input(
    "Flap chord / wing chord, E", min_value=0.0, value=float(inp.flap_chord_ratio), step=0.01)
inp.flap_area_one_side_sqft = c1.number_input(
    "Flap area on one side, SF (sq ft)", min_value=0.0,
    value=float(inp.flap_area_one_side_sqft), step=0.1)
inp.gust_load_factor = c2.number_input(
    "Flaps-extended gust load factor, NG", min_value=0.0,
    value=float(inp.gust_load_factor), step=0.1)
inp.nacelle_frontal_area_sqft = c1.number_input(
    "Nacelle/fuselage frontal area, AF (sq ft)", min_value=0.0,
    value=float(inp.nacelle_frontal_area_sqft), step=0.1)
inp.engine_butt_line_in = c2.number_input(
    "Engine butt line, BLPROP (in; 0 = fuselage)", value=float(inp.engine_butt_line_in), step=1.0)
project.flap_loads = inp
st.session_state["project"] = project

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    mod = run(project)
    results = build_flap(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute flap loads: {exc}")
    st.stop()

vals = {v.label: v.value for v in mod.conditions[0].values}
m1, m2, m3 = st.columns(3)
m1.metric("Critical flap load (lb)", f"{vals['Critical flap load (23.345(a))']:,.0f}")
m2.metric("LE pressure (lb/in²)", f"{vals['LE pressure (TE = half)']:.3f}")
m3.metric("Combined w/ gust (lb)", f"{vals['Flap load combined w/ gust']:,.0f}")

st.subheader("Flaps-extended envelope")
labels = ["1G stall", "2G stall", "2G at VF", "gust at VF"]
st.write(pd.DataFrame([
    {"Condition": lab,
     "Flap CL": round(vals[f"Flap CL {lab}"], 4),
     "Flap load (lb)": round(vals[f"Flap load {lab}"], 1)}
    for lab in labels
]))

if "Slipstream factor" in vals:
    st.subheader("Slipstream (FAR 23.457(b))")
    s1, s2, s3 = st.columns(3)
    s1.metric("Slipstream factor", f"{vals['Slipstream factor']:.3f}")
    s2.metric("Slipstream V at flap (kt)", f"{vals['Slipstream velocity at flap']:.1f}")
    s3.metric("Slipstream BL band (in)",
              f"{vals['Slipstream inboard BL']:.1f} … {vals['Slipstream outboard BL']:.1f}")

if project.loads is not None:
    project.loads.control_surface = [
        r for r in project.loads.control_surface if not r.surface.startswith("flap")
    ] + results
    st.session_state["project"] = project

st.download_button("Download flap loads (CSV)", sb.control_surface_csv(results),
                   file_name="flap_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results),
                   file_name="flap_loads.bdf", mime="text/plain")
