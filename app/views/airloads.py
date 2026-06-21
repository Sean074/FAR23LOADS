"""Streamlit page for the spanwise wing airloads (port of AIRLOADS.BAS + TAU.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes the wing spanwise lift distribution by Schrenk's method (Reference 1
Ch 7): the additive distribution (untwisted wing at CL=1), the basic distribution
(from the spanwise twist), and their combination at a target CL. The wing planform
is read from the Wing Geometry page's ``wing`` surface; this page adds the aero
inputs (section lift-curve slope, taper/tip ratio for TAU, twist, target CL).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import AeroInput, AeroSurfaceInput, Project
from farloads import io as farloads_io
from farloads.modules.airloads import schrenk_distribution
from farloads.report import module_text_report
from farloads.modules.airloads import run as airloads_run


st.title("Spanwise Wing Airloads — Schrenk")
st.caption(
    "Python/Streamlit port of AIRLOADS.BAS + TAU.BAS (Hal C. McMaster). Spanwise "
    "c·cl lift distribution by Schrenk's method (additive + basic), the input to "
    "the balancing, inertia and net-load modules."
)

project: Project = st.session_state.get("project", Project(name=""))

wing_geom = project.geometry.by_name("wing") if project.geometry else None
if wing_geom is None:
    st.warning(
        "No wing planform found. Define a `wing` surface on the **Wing Geometry** "
        "page first — AIRLOADS reads the planform (chord polylines) from it."
    )
    st.stop()

existing = project.aero.by_name("wing") if project.aero else None

with st.sidebar:
    st.header("Wing aero inputs")
    section_slope = st.number_input(
        "Section lift-curve slope m₀ (per deg)", min_value=0.01,
        value=float(existing.section_slope) if existing else 0.1075, format="%.4f")
    taper_ratio = st.number_input(
        "Taper ratio (tip chord / root chord)", min_value=0.0, max_value=1.0,
        value=float(existing.taper_ratio) if existing else 0.4356, format="%.4f")
    tip_ratio = st.number_input(
        "Tip ratio (rounded-tip width / semi-span)", min_value=0.0, max_value=1.0,
        value=float(existing.tip_ratio) if existing else 0.0, format="%.3f")
    use_tau_override = st.checkbox("Override TAU", value=existing.tau is not None if existing else False)
    tau_override = None
    if use_tau_override:
        tau_override = st.number_input(
            "TAU", value=float(existing.tau) if existing and existing.tau is not None else 0.04)
    target_cl = st.number_input(
        "Target wing CL", value=float(existing.target_cl) if existing else 1.0, format="%.3f")

    st.subheader("Spanwise twist")
    st.caption("Zero-lift angle (deg) at each butt line Y (inboard → outboard). Empty = untwisted.")
    default_twist = existing.twist if existing and existing.twist else []
    twist_df = st.data_editor(
        pd.DataFrame(default_twist or [[0.0, 0.0]], columns=["Y (in)", "Angle (deg)"]),
        num_rows="dynamic", hide_index=True, use_container_width=True)

twist = [(float(r["Y (in)"]), float(r["Angle (deg)"])) for _, r in twist_df.iterrows()
         if pd.notna(r["Y (in)"]) and pd.notna(r["Angle (deg)"])]
# Drop a lone all-zero placeholder row so an untwisted wing has an empty table.
if twist == [(0.0, 0.0)]:
    twist = []

aero_surf = AeroSurfaceInput(
    name="wing", section_slope=section_slope, taper_ratio=taper_ratio,
    tip_ratio=tip_ratio, tau=tau_override, twist=twist, target_cl=target_cl)
project.aero = AeroInput(surfaces=[aero_surf])
st.session_state["project"] = project

try:
    table = schrenk_distribution(wing_geom, aero_surf)
    results = airloads_run(project).conditions
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute airloads: {exc}")
    st.stop()

if project.is_concept:
    st.warning(
        "Concept category (C): the span-load distribution is a Schrenk **extrapolation** "
        "and is unverified above the FAR 23 calibration band."
    )

col1, col2, col3, col4 = st.columns(4)
col1.metric("Wing CLα slope M", f"{table.m_wing:.4f}", help="incl. AR & TAU (per deg)")
col2.metric("TAU", f"{table.tau:.4f}")
col3.metric("Target CL", f"{table.target_cl:.3f}")
col4.metric("Recovered CL", f"{table.recovered_cl:.4f}", help="∫c·cl dy / (S/2) — closure check")

fig = go.Figure()
fig.add_trace(go.Scatter(x=table.ye, y=table.ccl_additive, name="additive (×CL)", mode="lines+markers"))
fig.add_trace(go.Scatter(x=table.ye, y=table.ccl_basic, name="basic (twist)", mode="lines+markers"))
fig.add_trace(go.Scatter(x=table.ye, y=table.ccl_total, name=f"total @ CL={table.target_cl:g}",
                         mode="lines+markers", line=dict(width=3)))
fig.update_layout(
    title="Spanwise span load c·cl", xaxis_title="Butt line Y (in)",
    yaxis_title="c·cl (in)", legend=dict(orientation="h"), height=420)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Per-strip distribution")
st.dataframe(pd.DataFrame({
    "Y (in)": table.ye,
    "chord (in)": table.chord,
    "c·cl additive": table.ccl_additive,
    "c·cl basic": table.ccl_basic,
    "c·cl total": table.ccl_total,
    "cl total": table.cl_total,
}), hide_index=True, use_container_width=True)

st.download_button(
    "Download airloads (CSV)", farloads_io.load_cases_csv(results),
    file_name="airloads.csv", mime="text/csv")
st.download_button(
    "Download airloads (text)", module_text_report("Spanwise wing airloads", results),
    file_name="airloads.txt", mime="text/plain")
