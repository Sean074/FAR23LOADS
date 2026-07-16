"""Streamlit page for FAR 23 aerodynamic surface geometry (port of WINGGEOM.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Each surface is defined by its leading- and trailing-edge points (fuselage
station X, butt line Y, inches), ordered inboard -> outboard, and the strip count
the chord is integrated over. The wing's MAC/XLEMAC seed the later weight-envelope
and structural-speed pages. Inputs are entered in Imperial; results follow the
sidebar's Imperial/SI toggle (``Home.py``).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import (
    GeometryInput,
    Project,
    SurfaceInput,
    UnitSystem,
    consistency_warnings,
    convert_results,
    labels_for,
    to_display,
    to_imperial_scalar,
)
from farloads import io as farloads_io
from farloads.modules.wing_geometry import geometry_properties, surface_top_outline
from farloads.report import module_text_report


st.title("Aerodynamic Surface Geometry — FAR 23")
st.caption(
    "Python/Streamlit port of WINGGEOM.BAS (Hal C. McMaster). Area, MAC, XLEMAC, "
    "aspect ratio and span for each surface, by spanwise strip integration."
)

project: Project = st.session_state.get("project", Project(name=""))
for _w in consistency_warnings(project):
    if _w.page == "wing_geometry":
        st.warning(_w.message)
geometry = project.geometry or GeometryInput()

system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"length",...} -> unit string

with st.expander("ℹ️ Parameter guide", expanded=False):
    st.markdown(
        "Each surface is defined by its leading- and trailing-edge points, ordered inboard → outboard "
        "(WINGGEOM, Ch 4):\n\n"
        "- **XLE / XTE** — fuselage station (X, aft of the nose datum) of the leading / trailing edge point.\n"
        "- **YLE / YTE** — butt line (Y, lateral distance from the centreline) of that point.\n"
        "- **Symmetric about CL** — enter only the right-hand semi-span; it is mirrored for the integration.\n"
        "- **Integration elements** — number of spanwise strips the chord is integrated over.\n\n"
        "**Derived (below):** *Area* = ∫ chord dy; *MAC* = mean aerodynamic chord; *XLEMAC* = station of the "
        "MAC leading edge; *AR* = b²/S (aspect ratio); *span* b."
    )

# Add a new (blank) surface -- immediate, not gated behind the edit form below.
with st.form("add_surface_form", clear_on_submit=True):
    new_name = st.text_input("New surface name", value="", placeholder="e.g. wing")
    add_surface = st.form_submit_button("Add surface")
if add_surface and new_name:
    surfaces = list(geometry.surfaces) + [SurfaceInput(name=new_name, leading_edge=[], trailing_edge=[])]
    project.geometry = GeometryInput(surfaces=surfaces)
    st.session_state["project"] = project
    st.rerun()

if not geometry.surfaces:
    st.info("No surfaces defined yet -- add one above (e.g. \"wing\") to enter its leading/trailing edge points.")
    st.stop()

# Per-surface editable point tables, applied together.
with st.form("geometry_form"):
    field_inputs = []
    for surf in geometry.surfaces:
        with st.expander(f"Surface: {surf.name}", expanded=(surf.name == "wing")):
            cols = st.columns(2)
            with cols[0]:
                sym = st.checkbox("Symmetric about CL", value=surf.symmetric, key=f"sym_{surf.name}",
                                  help="Mirror the entered semi-span about the centreline; enter only the "
                                       "right-hand points when ticked.")
            with cols[1]:
                elems = st.number_input("Integration elements", min_value=2, max_value=100,
                                        value=int(surf.elements), key=f"el_{surf.name}",
                                        help="Number of spanwise strips the chord is integrated over for "
                                             "Area/MAC/XLEMAC (WINGGEOM, Ch 4). More strips = finer integration.")
            st.caption(f"Points entered in {U['length']}.")
            le_display = [(to_display(x, "length", system), to_display(y, "length", system))
                          for x, y in surf.leading_edge]
            te_display = [(to_display(x, "length", system), to_display(y, "length", system))
                          for x, y in surf.trailing_edge]
            le_cols = {"XLE": st.column_config.NumberColumn(f"XLE ({U['length']})"),
                      "YLE": st.column_config.NumberColumn(f"YLE ({U['length']})")}
            te_cols = {"XTE": st.column_config.NumberColumn(f"XTE ({U['length']})"),
                      "YTE": st.column_config.NumberColumn(f"YTE ({U['length']})")}
            le_df = st.data_editor(pd.DataFrame(le_display, columns=["XLE", "YLE"]),
                                   num_rows="dynamic", column_config=le_cols, key=f"le_{surf.name}_{system.value}")
            te_df = st.data_editor(pd.DataFrame(te_display, columns=["XTE", "YTE"]),
                                   num_rows="dynamic", column_config=te_cols, key=f"te_{surf.name}_{system.value}")
            field_inputs.append((surf.name, sym, elems, le_df, te_df))
    applied = st.form_submit_button("Apply geometry", type="primary")

if applied:
    def _imp_pt(row):
        return tuple(to_imperial_scalar(v, "length", system) for v in row)

    edited_surfaces = [
        SurfaceInput(
            name=name, symmetric=sym, elements=int(elems),
            leading_edge=[_imp_pt(r) for r in le_df.dropna().to_numpy().tolist()],
            trailing_edge=[_imp_pt(r) for r in te_df.dropna().to_numpy().tolist()],
        )
        for name, sym, elems, le_df, te_df in field_inputs
    ]
    geometry = GeometryInput(surfaces=edited_surfaces)
    project.geometry = geometry
    st.session_state["project"] = project

def _planform_plot() -> go.Figure:
    fig = go.Figure()
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    for i, surf in enumerate(geometry.surfaces):
        color = palette[i % len(palette)]
        outlines = surface_top_outline(surf.leading_edge, surf.trailing_edge, symmetric=surf.symmetric)
        for j, (xs, ys) in enumerate(outlines):
            xs_disp = [to_display(x, "length", system) for x in xs]
            ys_disp = [to_display(y, "length", system) for y in ys]
            fig.add_scatter(x=xs_disp, y=ys_disp, mode="lines", line=dict(color=color),
                            name=surf.name, showlegend=(j == 0))
    fig.update_yaxes(scaleanchor="x", scaleratio=1, title=f"Y (butt line, {U['length']})")
    fig.update_xaxes(title=f"X (fuselage station, {U['length']})")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10))
    return fig


if any(surf.leading_edge and surf.trailing_edge for surf in geometry.surfaces):
    st.plotly_chart(_planform_plot(), use_container_width=True)
else:
    st.caption("Enter leading/trailing-edge points below to see the planform plot.")

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
