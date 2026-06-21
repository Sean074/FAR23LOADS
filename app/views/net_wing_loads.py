"""Streamlit page for the net wing loads (WINGINER + NETLOADS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the spanwise wing shear, bending moment and torsion for a critical
condition as the algebraic sum of the AIRLOADS air loads and the WINGINER inertia
loads (Reference 1 Ch 12-14) -- the headline structural deliverable. The wing
planform/aero come from the Wing Geometry / Airloads pages; this page adds the
wing-mass distribution (panel weight, density ratio, rib, dihedral, concentrated
weights) and the critical load cases.
"""

from __future__ import annotations

import csv
import io as _io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import ConcentratedWeight, Project, WingLoadCase, WingMassInput
from farloads.modules.net_loads import build_net_loads, wing_load_rows


st.title("Net Wing Loads — shear / bending / torsion")
st.caption(
    "Python/Streamlit port of WINGINER.BAS + NETLOADS.BAS (Hal C. McMaster). Net "
    "spanwise wing load = air load (AIRLOADS) − inertia (WINGINER), giving the "
    "shear, bending moment and torsion along the 25% chord."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.geometry is None or project.geometry.by_name("wing") is None:
    st.warning("Define a `wing` surface on the **Wing Geometry** page first.")
    st.stop()
if project.aero is None or project.aero.by_name("wing") is None:
    st.warning("Set the wing aero inputs on the **Airloads** page first (NETLOADS needs them).")
    st.stop()

wm = project.wing_mass or WingMassInput()

with st.sidebar:
    st.header("Wing mass distribution")
    panel = st.number_input("Outboard panel weight, one side (lb)", min_value=0.0,
                            value=float(wm.panel_weight_lb) or 165.0)
    dr = st.number_input("Tip/root area-density ratio", min_value=0.0, max_value=1.0,
                         value=float(wm.tip_root_density_ratio) or 0.95, format="%.3f")
    rib = st.number_input("Inboard rib butt line (in)", value=float(wm.inboard_rib_y) or 23.0)
    wrp = st.number_input("WL of wing ref plane at centreline (in)",
                          value=float(wm.wrp_waterline) or 78.5)
    dihedral = st.number_input("Dihedral (deg)", value=float(wm.dihedral_deg) or 6.0)

st.subheader("Concentrated wing weights")
cw_default = pd.DataFrame(
    [[c.name, c.weight_lb, c.x, c.y, c.z] for c in wm.concentrated]
    or [["", 0.0, 0.0, 0.0, 0.0]],
    columns=["name", "weight_lb", "x", "y", "z"],
)
cw_df = st.data_editor(cw_default, num_rows="dynamic", hide_index=True, use_container_width=True)
concentrated = [
    ConcentratedWeight(name=str(r["name"]), weight_lb=float(r["weight_lb"]),
                       x=float(r["x"]), y=float(r["y"]), z=float(r["z"]))
    for _, r in cw_df.iterrows()
    if pd.notna(r["weight_lb"]) and float(r["weight_lb"]) != 0.0
]

st.subheader("Critical load cases")
st.caption("Nz / Nx are the inertia load factors (negative of the air-load factor); "
           "CL / V are the air-load condition. Reference a V-n case to auto-fill from FLTLOADS.")
case_default = pd.DataFrame(
    [[c.name, c.case, c.nz, c.nx, c.unbal_moment, c.cl, c.v_eas_kt] for c in wm.cases]
    or [["PHAA", None, -3.8, 0.6065, 0.0, 1.52, 117.4]],
    columns=["name", "vn_case", "nz", "nx", "unbal_moment", "cl", "v_eas_kt"],
)
case_df = st.data_editor(case_default, num_rows="dynamic", hide_index=True, use_container_width=True)


def _opt(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


cases = [
    WingLoadCase(name=str(r["name"]), case=_opt(r["vn_case"]) and int(r["vn_case"]),
                 nz=_opt(r["nz"]), nx=_opt(r["nx"]),
                 unbal_moment=float(r["unbal_moment"]) if pd.notna(r["unbal_moment"]) else 0.0,
                 cl=_opt(r["cl"]), v_eas_kt=_opt(r["v_eas_kt"]))
    for _, r in case_df.iterrows()
    if pd.notna(r["name"]) and str(r["name"]).strip()
]

project.wing_mass = WingMassInput(
    panel_weight_lb=panel, tip_root_density_ratio=dr, inboard_rib_y=rib, wrp_waterline=wrp,
    dihedral_deg=dihedral, surface="wing", concentrated=concentrated, cases=cases)
st.session_state["project"] = project

if project.is_concept:
    st.warning("Concept category (C): net loads are an **unverified extrapolation** "
               "above the FAR 23 calibration band.")

try:
    loads = build_net_loads(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute net wing loads: {exc}")
    st.stop()

case_names = [r.case for r in loads.wing_net]
sel = st.selectbox("Show case", case_names)
air = next(r for r in loads.wing_air if r.case == sel)
inertia = next(r for r in loads.wing_inertia if r.case == sel)
net = next(r for r in loads.wing_net if r.case == sel)

c1, c2, c3 = st.columns(3)
c1.metric("Root shear Sz (lb)", f"{net.stations[0].sz:,.0f}")
c2.metric("Root bending Mxx (lb-in)", f"{net.stations[0].mxx:,.0f}")
c3.metric("Root torsion Myy (lb-in)", f"{net.stations[0].myy:,.0f}")

for title, attr, unit in [("Shear Sz", "sz", "lb"), ("Bending Mxx", "mxx", "lb-in"),
                          ("Torsion Myy", "myy", "lb-in")]:
    fig = go.Figure()
    for label, r in [("air", air), ("inertia", inertia), ("net", net)]:
        fig.add_trace(go.Scatter(
            x=[s.y for s in r.stations], y=[getattr(s, attr) for s in r.stations],
            name=label, mode="lines+markers", line=dict(width=3 if label == "net" else 1)))
    fig.update_layout(title=f"{title} — {sel}", xaxis_title="Butt line Y (in)",
                      yaxis_title=f"{title} ({unit})", legend=dict(orientation="h"), height=320)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Net load station table")
st.dataframe(pd.DataFrame(wing_load_rows([net])), hide_index=True, use_container_width=True)

buf = _io.StringIO()
rows = wing_load_rows(loads.wing_net)
writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
writer.writeheader()
writer.writerows(rows)
st.download_button("Download net wing loads (CSV)", buf.getvalue(),
                   file_name="net_wing_loads.csv", mime="text/csv")
