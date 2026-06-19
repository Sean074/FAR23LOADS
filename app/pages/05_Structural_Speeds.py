"""Streamlit page for FAR 23 structural design speeds (port of STRSPEED.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Choose the certification category and enter the design weight, stall speeds and
chosen design speeds (KEAS). The wing area is read from the Wing Geometry page's
wing surface when present, else entered here. Reports the limit maneuver load
factors (FAR 23.337), the design speeds (FAR 23.335) and the cruise/dive Mach at
the shoulder altitude. All speeds are knots equivalent airspeed.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import Project, StructuralSpeedsInput
from farloads import io as farloads_io
from farloads.modules.structural_speeds import design_speeds
from farloads.report import module_text_report

st.set_page_config(page_title="FAR 23 Structural Speeds", layout="wide")

st.title("Structural Design Speeds — FAR 23")
st.caption(
    "Python/Streamlit port of STRSPEED.BAS (Hal C. McMaster). Limit maneuver load "
    "factors and design airspeeds (VA, VC, VD, VF) with their FAR minimums."
)

project: Project = st.session_state.get("project", Project(name=""))
existing = project.speeds

_CATS = {"Normal / commuter": "N", "Utility": "U", "Acrobatic": "A"}
_CAT_LABELS = list(_CATS)

has_wing = project.geometry is not None and project.geometry.by_name(
    existing.wing_surface if existing else "wing") is not None

with st.sidebar:
    st.header("Inputs (Imperial / KEAS)")
    cat_default = next((k for k, v in _CATS.items() if existing and v == existing.category), "Normal / commuter")
    cat_label = st.selectbox("Category", _CAT_LABELS, index=_CAT_LABELS.index(cat_default))
    weight = st.number_input("Design (gross) weight (lb)", min_value=1.0,
                             value=float(existing.weight_lb) if existing else 3400.0)
    if has_wing:
        st.caption("Wing area read from the Wing Geometry page.")
        wing_area = None
    else:
        wing_area = st.number_input("Wing area S (ft²)", min_value=1.0,
                                    value=float(existing.wing_area_sqft) if existing and existing.wing_area_sqft else 184.125)
    vh = st.number_input("Max sea-level speed VH (kt)", min_value=1.0,
                         value=float(existing.vh_kt) if existing else 190.0)
    vs = st.number_input("Stall speed, flaps up VS (kt)", min_value=1.0,
                         value=float(existing.stall_clean_kt) if existing else 62.226)
    vsf = st.number_input("Stall speed, flaps down VSF (kt)", min_value=1.0,
                          value=float(existing.stall_flap_kt) if existing else 58.611)
    alt = st.number_input("Shoulder altitude (ft)", min_value=0.0,
                          value=float(existing.shoulder_altitude_ft) if existing else 12000.0)
    st.subheader("Chosen speeds (blank = use minimum)")
    vc = st.number_input("Chosen cruise VC (kt)", min_value=0.0,
                         value=float(existing.chosen_vc) if existing and existing.chosen_vc else 170.0)
    vd = st.number_input("Chosen dive VD (kt)", min_value=0.0,
                         value=float(existing.chosen_vd) if existing and existing.chosen_vd else 212.5)

inp = StructuralSpeedsInput(
    category=_CATS[cat_label],
    weight_lb=weight,
    wing_area_sqft=wing_area,
    vh_kt=vh,
    stall_clean_kt=vs,
    stall_flap_kt=vsf,
    shoulder_altitude_ft=alt,
    chosen_vc=vc or None,
    chosen_vd=vd or None,
)
project.speeds = inp
st.session_state["project"] = project

try:
    results = design_speeds(project, inp)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute structural speeds: {exc}")
    st.stop()

for r in results:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        if r.note:
            st.caption(r.note)

st.download_button(
    "Download structural speeds (CSV)",
    farloads_io.load_cases_csv(results),
    file_name="structural_speeds.csv",
    mime="text/csv",
)
st.download_button(
    "Download structural speeds (text)",
    module_text_report("Structural design speeds", results),
    file_name="structural_speeds.txt",
    mime="text/plain",
)
