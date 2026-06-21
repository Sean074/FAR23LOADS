"""Streamlit page for FAR 23 aerodynamic surface geometry (port of WINGGEOM.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Each surface is defined by its leading- and trailing-edge points (fuselage
station X, butt line Y, inches), ordered inboard -> outboard, and the strip count
the chord is integrated over. The wing's MAC/XLEMAC seed the later weight-envelope
and structural-speed pages. Inputs are entered in Imperial; an SI output toggle is
offered (length -> mm, area -> m²).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import GeometryInput, Project, SurfaceInput, UnitSystem, convert_results
from farloads import io as farloads_io
from farloads.modules.wing_geometry import geometry_properties
from farloads.report import module_text_report


st.title("Aerodynamic Surface Geometry — FAR 23")
st.caption(
    "Python/Streamlit port of WINGGEOM.BAS (Hal C. McMaster). Area, MAC, XLEMAC, "
    "aspect ratio and span for each surface, by spanwise strip integration."
)

project: Project = st.session_state.get("project", Project(name=""))
geometry = project.geometry or GeometryInput()
if not geometry.surfaces:
    geometry = GeometryInput(surfaces=[
        SurfaceInput(
            name="wing", symmetric=True, elements=20,
            leading_edge=[(45.0, 0.0), (64.31301, 46.5), (72.0, 201.0)],
            trailing_edge=[(146.0, 0.0), (116.0, 201.0)],
        ),
    ])

with st.sidebar:
    st.header("Output units")
    out_label = st.radio("Reported lengths/areas in", ["Imperial (in)", "SI (mm, m²)"], index=0,
                         help="Surface point inputs below are entered in Imperial inches.")
    system = UnitSystem.SI if out_label.startswith("SI") else UnitSystem.IMPERIAL

# Per-surface editable point tables.
edited_surfaces = []
for surf in geometry.surfaces:
    with st.expander(f"Surface: {surf.name}", expanded=(surf.name == "wing")):
        cols = st.columns(2)
        with cols[0]:
            sym = st.checkbox("Symmetric about CL", value=surf.symmetric, key=f"sym_{surf.name}")
        with cols[1]:
            elems = st.number_input("Integration elements", min_value=2, max_value=100,
                                    value=int(surf.elements), key=f"el_{surf.name}")
        le_df = st.data_editor(pd.DataFrame(surf.leading_edge, columns=["XLE", "YLE"]),
                               num_rows="dynamic", key=f"le_{surf.name}")
        te_df = st.data_editor(pd.DataFrame(surf.trailing_edge, columns=["XTE", "YTE"]),
                               num_rows="dynamic", key=f"te_{surf.name}")
        edited_surfaces.append(SurfaceInput(
            name=surf.name, symmetric=sym, elements=int(elems),
            leading_edge=[tuple(r) for r in le_df.dropna().to_numpy().tolist()],
            trailing_edge=[tuple(r) for r in te_df.dropna().to_numpy().tolist()],
        ))

geometry = GeometryInput(surfaces=edited_surfaces)
project.geometry = geometry
st.session_state["project"] = project

try:
    results = geometry_properties(geometry, project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute geometry: {exc}")
    st.stop()

results = convert_results(results, system)

for r in results:
    with st.expander(f"{r.title}", expanded=True):
        rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        if r.note:
            st.caption(r.note)

st.download_button(
    "Download geometry (CSV)",
    farloads_io.load_cases_csv(results),
    file_name="wing_geometry.csv",
    mime="text/csv",
)
st.download_button(
    "Download geometry (text)",
    module_text_report("Aerodynamic surface geometry", results),
    file_name="wing_geometry.txt",
    mime="text/plain",
)
