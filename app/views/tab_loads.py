"""Streamlit page for control-surface tab loads (TABLOADS, Ch 18).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes tab loads at full deflection at VC (FAR 23.409 / CAM 3.224) for each tab,
with the trapezoidal chordwise distribution (LE = 2× TE). VC comes from STRSPEED;
each tab's geometry is edited in the table below.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_shell import optional_slice
from app_shell.components import active_system, gate, stop_page
from app_shell.widget_keys import widget_key
from sloads import (
    Project,
    TabLoadsInput,
    TabSpec,
    UnitSystem,
    convert_results,
    labels_for,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from sloads.export import sbeam_bridge as sb
from sloads.modules.tab import build_tabs, run

st.title("Control-Surface Tab Loads — TABLOADS")
st.caption(
    "Python/Streamlit port of TABLOADS.BAS (Reference 1 Ch 18): full tab deflection "
    "at VC with a trapezoidal chordwise distribution (leading-edge loading twice the "
    "trailing edge) per CAM 3.224-1(b)."
)

project: Project = st.session_state.get("project", Project(name=""))
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
U = labels_for(system)  # {"length": ..., "area_sqft": ...} -> unit string

if project.speeds is None:
    gate("Define the **Structural Speeds** (VC) first.", "structural_speeds")
    stop_page()

# Captured before the form mutates ``inp`` in place: ``store`` needs to
# know whether the project *had* this Optional slice (#145).
_existing_slice = project.tab_loads
inp = project.tab_loads or TabLoadsInput()
existing = [
    {"surface": t.surface, "mac_in": to_display(t.mac_in, "length", system),
     "area_sqft": to_display(t.area_sqft, "area_sqft", system),
     "station_in": to_display(t.station_in, "length", system),
     "airfoil_chord_in": to_display(t.airfoil_chord_in, "length", system),
     "deflection_deg": t.deflection_deg}
    for t in inp.tabs
] or [{"surface": "htail", "mac_in": 0.0, "area_sqft": 0.0, "station_in": 0.0,
       "airfoil_chord_in": 0.0, "deflection_deg": 0.0}]

with st.form("tab_loads_form"):
    st.subheader("Tabs")
    edited = st.data_editor(
        pd.DataFrame(existing), num_rows="dynamic", width="stretch",
        key=widget_key(f"tab_loads_editor_{system.value}"),
        column_config={
            "surface": st.column_config.SelectboxColumn(options=["wing", "htail", "vtail"]),
            "mac_in": st.column_config.NumberColumn(f"MAC ({U['length']})"),
            "area_sqft": st.column_config.NumberColumn(f"Area ({U['area_sqft']})"),
            "station_in": st.column_config.NumberColumn(f"BL/WL of tab MAC ({U['length']})"),
            "airfoil_chord_in": st.column_config.NumberColumn(
                f"Airfoil chord at MAC ({U['length']})"),
            "deflection_deg": st.column_config.NumberColumn("Deflection (deg)"),
        })
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.tabs = [
        TabSpec(surface=str(row.surface),
                mac_in=to_imperial_scalar(float(row.mac_in), "length", system),
                area_sqft=to_imperial_scalar(float(row.area_sqft), "area_sqft", system),
                station_in=to_imperial_scalar(float(row.station_in), "length", system),
                airfoil_chord_in=to_imperial_scalar(
                    float(row.airfoil_chord_in), "length", system),
                deflection_deg=float(row.deflection_deg))
        for row in edited.itertuples()
        if to_imperial_scalar(float(row.area_sqft), "area_sqft", system) > 0
    ]
    project.tab_loads = optional_slice.store(inp, _existing_slice)
    st.session_state["project"] = project
    st.success("Tabs applied.")

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

if not inp.tabs:
    st.info("Add at least one tab (positive area) above.")
    stop_page()

try:
    mod = run(project)
    results = build_tabs(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute tab loads: {exc}")
    stop_page()

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
    v = {x.key: x.value for x in cond.values}
    rows.append({"Tab": cond.title, "E": round(v["tab_chord_ratio_e"], 4),
                 f"Load ({force_u}, LIMIT)": round(v["tab_load"], 2),
                 f"LE {pressure_u} (LIMIT)": round(to_si_scalar(v["tab_le_pressure"], "psi", system), 4),
                 f"TE {pressure_u} (LIMIT)": round(to_si_scalar(v["tab_te_pressure"], "psi", system), 4)})
st.write(pd.DataFrame(rows))

st.download_button("Download tab loads (CSV)", sb.control_surface_csv(results, system=system),
                   file_name="tab_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results, system=system),
                   file_name="tab_loads.bdf", mime="text/plain")
