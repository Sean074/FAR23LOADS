"""Streamlit page for control-surface tab loads (TABLOADS, Ch 18).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes tab loads at full deflection at VC (FAR 23.409 / CAM 3.224) for each tab,
with the trapezoidal chordwise distribution (LE = 2× TE). VC comes from STRSPEED;
each tab's geometry is edited in the table below.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import Project, TabLoadsInput, TabSpec, UnitSystem, convert_results, to_si_scalar
from farloads.export import sbeam_bridge as sb
from farloads.modules.tab import build_tabs, run


st.title("Control-Surface Tab Loads — TABLOADS")
st.caption(
    "Python/Streamlit port of TABLOADS.BAS (Reference 1 Ch 18): full tab deflection "
    "at VC with a trapezoidal chordwise distribution (leading-edge loading twice the "
    "trailing edge) per CAM 3.224-1(b)."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)

if project.speeds is None:
    st.warning("Define the **Structural Speeds** (VC) first.")
    st.stop()

inp = project.tab_loads or TabLoadsInput()
existing = [
    {"surface": t.surface, "mac_in": t.mac_in, "area_sqin": t.area_sqin,
     "station_in": t.station_in, "airfoil_chord_in": t.airfoil_chord_in,
     "deflection_deg": t.deflection_deg}
    for t in inp.tabs
] or [{"surface": "htail", "mac_in": 0.0, "area_sqin": 0.0, "station_in": 0.0,
       "airfoil_chord_in": 0.0, "deflection_deg": 0.0}]

with st.form("tab_loads_form"):
    st.subheader("Tabs")
    edited = st.data_editor(
        pd.DataFrame(existing), num_rows="dynamic", use_container_width=True,
        column_config={
            "surface": st.column_config.SelectboxColumn(options=["wing", "htail", "vtail"]),
            "mac_in": st.column_config.NumberColumn("MAC (in)"),
            "area_sqin": st.column_config.NumberColumn("Area (sq in)"),
            "station_in": st.column_config.NumberColumn("BL/WL of tab MAC (in)"),
            "airfoil_chord_in": st.column_config.NumberColumn("Airfoil chord at MAC (in)"),
            "deflection_deg": st.column_config.NumberColumn("Deflection (deg)"),
        })
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.tabs = [
        TabSpec(surface=str(row.surface), mac_in=float(row.mac_in),
                area_sqin=float(row.area_sqin), station_in=float(row.station_in),
                airfoil_chord_in=float(row.airfoil_chord_in),
                deflection_deg=float(row.deflection_deg))
        for row in edited.itertuples() if float(row.area_sqin) > 0
    ]
    project.tab_loads = inp
    st.session_state["project"] = project
    st.success("Tabs applied.")

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

if not inp.tabs:
    st.info("Add at least one tab (positive area) above.")
    st.stop()

try:
    mod = run(project)
    results = build_tabs(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute tab loads: {exc}")
    st.stop()

st.subheader("Tab loads")
st.caption(
    "On-screen loads are **LIMIT** (oracle values, traceable to the manual). The "
    "CSV / FORCE-card downloads below and the **Review/Export** pages report "
    "**ULTIMATE** = limit × 1.5 (14 CFR 23.303)."
)
force_u = "N" if system == UnitSystem.SI else "lb"
pressure_u = "kPa" if system == UnitSystem.SI else "psi"
display_conditions = convert_results(mod.conditions, system)
rows = []
for cond in display_conditions:
    v = {x.label: x.value for x in cond.values}
    rows.append({"Tab": cond.title, "E": round(v["Tab chord ratio E"], 4),
                 f"Load ({force_u}, LIMIT)": round(v["Tab load"], 2),
                 f"LE {pressure_u} (LIMIT)": round(to_si_scalar(v["Tab LE pressure"], "psi", system), 4),
                 f"TE {pressure_u} (LIMIT)": round(to_si_scalar(v["Tab TE pressure"], "psi", system), 4)})
st.write(pd.DataFrame(rows))

if project.loads is not None:
    project.loads.control_surface = [
        r for r in project.loads.control_surface if not r.surface.startswith("tab:")
    ] + results
    st.session_state["project"] = project

st.download_button("Download tab loads (CSV)", sb.control_surface_csv(results),
                   file_name="tab_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results),
                   file_name="tab_loads.bdf", mime="text/plain")
