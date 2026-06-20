"""Configuration & Layout page (modern addition; port-free).

The geometric source of truth for an initial concept: edit the parametric
fuselage / wing / tail / gear geometry, see a three-view with the CG and neutral
point marked, read the derived MAC / XLEMAC / static-margin / tip-back / overturn
assessment, and place the design against a reference fleet (W/S-vs-W/P and
MTOW-vs-OEW). Seed buttons push the geometry downstream (WINGGEOM polylines, which
in turn feed WTENV / STRSPEED).

There is no manual oracle for this page; concept results are first-order estimates
(see ``farloads/modules/configuration.py``). Run the suite with:
    streamlit run app/Home.py
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from farloads import LayoutInput, Project
from farloads.modules.configuration import (
    configuration_properties,
    wing_polylines,
    wing_surface,
)

st.set_page_config(page_title="FAR 23 Configuration & Layout", layout="wide")

st.title("Configuration & Layout")
st.caption(
    "Parametric fuselage / wing / tail / gear geometry — the geometric source of "
    "truth that seeds the geometry, weight and speeds pages. A modern addition with "
    "no original program and no regression oracle; figures are first-order estimates."
)

project: Project = st.session_state.get("project", Project(name=""))
layout = project.configuration or LayoutInput(
    fuselage_length=300.0, fuselage_width=48.0, fuselage_height=60.0,
    wing_area_sqft=174.0, aspect_ratio=6.0, taper_ratio=0.6,
    dihedral_deg=3.0, le_sweep_deg=2.0, le_root_x=90.0, root_waterline_z=40.0,
    h_tail_area=30.0, h_tail_arm=180.0, v_tail_area=18.0, v_tail_arm=175.0,
    nose_gear_x=30.0, main_gear_x=150.0, track=90.0, gear_height=35.0,
)


# --------------------------------------------------------------------------- #
# Input groups
# --------------------------------------------------------------------------- #
def _num(label: str, value: float, key: str, step: float = 1.0) -> float:
    return float(st.number_input(label, value=float(value), step=step, key=key))


with st.sidebar:
    st.header("Geometry (inches / ft²)")
    with st.expander("Fuselage", expanded=True):
        layout.fuselage_length = _num("Length (in)", layout.fuselage_length, "f_len")
        layout.fuselage_width = _num("Width (in)", layout.fuselage_width, "f_wid")
        layout.fuselage_height = _num("Height (in)", layout.fuselage_height, "f_hgt")
        layout.datum_x = _num("Nose datum station (in)", layout.datum_x, "f_dat")
    with st.expander("Wing", expanded=True):
        layout.wing_area_sqft = _num("Area S (ft²)", layout.wing_area_sqft, "w_area")
        layout.aspect_ratio = _num("Aspect ratio", layout.aspect_ratio, "w_ar", 0.1)
        layout.taper_ratio = _num("Taper ratio", layout.taper_ratio, "w_taper", 0.05)
        layout.le_sweep_deg = _num("LE sweep (deg)", layout.le_sweep_deg, "w_sweep", 0.5)
        layout.dihedral_deg = _num("Dihedral (deg)", layout.dihedral_deg, "w_dih", 0.5)
        layout.le_root_x = _num("LE root station (in)", layout.le_root_x, "w_lex")
        layout.root_waterline_z = _num("Root waterline (in)", layout.root_waterline_z, "w_wl")
    with st.expander("Tail"):
        layout.h_tail_area = _num("H-tail area (ft²)", layout.h_tail_area, "h_area")
        layout.h_tail_arm = _num("H-tail arm (in)", layout.h_tail_arm, "h_arm")
        layout.v_tail_area = _num("V-tail area (ft²)", layout.v_tail_area, "v_area")
        layout.v_tail_arm = _num("V-tail arm (in)", layout.v_tail_arm, "v_arm")
    with st.expander("Landing gear"):
        layout.nose_gear_x = _num("Nose gear station (in)", layout.nose_gear_x, "g_nose")
        layout.main_gear_x = _num("Main gear station (in)", layout.main_gear_x, "g_main")
        layout.track = _num("Track (in)", layout.track, "g_track")
        layout.gear_height = _num("Gear height (in)", layout.gear_height, "g_hgt")

project.configuration = layout
st.session_state["project"] = project

# --------------------------------------------------------------------------- #
# Derived assessment
# --------------------------------------------------------------------------- #
try:
    results = configuration_properties(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not derive configuration: {exc}")
    st.stop()

derived = {v.label: v.value for r in results for v in r.values}
mac = derived["MAC"]
xlemac = derived["XLE(MAC) station of MAC LE"]
x_cg = xlemac + 0.25 * mac
np_station = derived.get("Neutral point station")


# --------------------------------------------------------------------------- #
# Three-view
# --------------------------------------------------------------------------- #
def _three_view() -> go.Figure:
    le, te = wing_polylines(layout)
    semi = le[-1][1]
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Top", "Side", "Front"))

    # --- Top view: X (horizontal) vs Y (lateral). Wing planform both sides. ---
    le_x = [p[0] for p in le]
    le_y = [p[1] for p in le]
    te_x = [p[0] for p in te]
    te_y = [p[1] for p in te]
    wing_x = le_x + te_x[::-1] + [le_x[0]]
    wing_y = le_y + te_y[::-1] + [le_y[0]]
    for sgn in (1, -1):
        fig.add_scatter(x=wing_x, y=[sgn * v for v in wing_y], mode="lines",
                        line=dict(color="#1f77b4"), showlegend=False, row=1, col=1)
    # Fuselage outline (length x width).
    nose, tail = layout.datum_x, layout.datum_x + layout.fuselage_length
    hw = layout.fuselage_width / 2.0
    fig.add_scatter(x=[nose, tail, tail, nose, nose], y=[hw, hw, -hw, -hw, hw],
                    mode="lines", line=dict(color="#888"), showlegend=False, row=1, col=1)
    # CG / NP markers.
    fig.add_scatter(x=[x_cg], y=[0], mode="markers", marker=dict(color="#d62728", size=11, symbol="x"),
                    name="CG (25% MAC)", row=1, col=1)
    if np_station is not None:
        fig.add_scatter(x=[np_station], y=[0], mode="markers",
                        marker=dict(color="#2ca02c", size=11, symbol="circle-open"),
                        name="Neutral point", row=1, col=1)
    fig.update_yaxes(scaleanchor="x", scaleratio=1, row=1, col=1)

    # --- Side view: X (horizontal) vs Z (waterline). Fuselage + gear. ---
    fh = layout.fuselage_height
    z0 = layout.root_waterline_z - fh / 2.0
    fig.add_scatter(x=[nose, tail, tail, nose, nose],
                    y=[z0, z0, z0 + fh, z0 + fh, z0], mode="lines",
                    line=dict(color="#888"), showlegend=False, row=1, col=2)
    ground = layout.root_waterline_z - layout.gear_height
    fig.add_scatter(x=[nose, tail], y=[ground, ground], mode="lines",
                    line=dict(color="#aaa", dash="dot"), showlegend=False, row=1, col=2)
    for gx in (layout.nose_gear_x, layout.main_gear_x):
        if gx:
            fig.add_scatter(x=[gx, gx], y=[ground, layout.root_waterline_z], mode="lines",
                            line=dict(color="#555"), showlegend=False, row=1, col=2)
    fig.add_scatter(x=[x_cg], y=[layout.root_waterline_z], mode="markers",
                    marker=dict(color="#d62728", size=11, symbol="x"), showlegend=False, row=1, col=2)
    fig.update_yaxes(scaleanchor="x", scaleratio=1, row=1, col=2)

    # --- Front view: Y (lateral) vs Z (waterline). Fuselage + dihedral + track. ---
    fig.add_scatter(x=[-hw, hw, hw, -hw, -hw],
                    y=[z0, z0, z0 + fh, z0 + fh, z0], mode="lines",
                    line=dict(color="#888"), showlegend=False, row=1, col=3)
    dz = semi * math.tan(math.radians(layout.dihedral_deg))
    fig.add_scatter(x=[-semi, 0, semi],
                    y=[layout.root_waterline_z + dz, layout.root_waterline_z,
                       layout.root_waterline_z + dz], mode="lines",
                    line=dict(color="#1f77b4"), showlegend=False, row=1, col=3)
    if layout.track:
        fig.add_scatter(x=[-layout.track / 2, layout.track / 2], y=[ground, ground],
                        mode="markers", marker=dict(color="#555", size=8), showlegend=False, row=1, col=3)
    fig.update_yaxes(scaleanchor="x", scaleratio=1, row=1, col=3)

    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.2, x=0))
    return fig


st.plotly_chart(_three_view(), use_container_width=True)

# --------------------------------------------------------------------------- #
# Assessment + seeding
# --------------------------------------------------------------------------- #
left, right = st.columns([3, 2])
with left:
    st.subheader("Assessment")
    for r in results:
        with st.expander(r.title, expanded=True):
            rows = [{"Quantity": v.label, "Value": round(v.value, 4), "Units": v.units} for v in r.values]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            if r.note:
                st.caption(r.note)

with right:
    st.subheader("Seed downstream pages")
    st.caption(
        "Generate the WINGGEOM wing surface from the parametric planform. The "
        "Weight-Envelope and Structural-Speeds pages read XLEMAC/MAC and the wing "
        "area from that geometry."
    )
    if st.button("Seed wing geometry (WINGGEOM)"):
        from farloads import GeometryInput

        geom = project.geometry or GeometryInput()
        surfaces = [s for s in geom.surfaces if s.name != "wing"]
        surfaces.insert(0, wing_surface(layout))
        project.geometry = GeometryInput(surfaces=surfaces)
        st.session_state["project"] = project
        st.success(
            f"Seeded the wing surface (MAC {mac:.2f} in, XLEMAC {xlemac:.2f} in). "
            "Open the Wing Geometry page to refine it."
        )

# --------------------------------------------------------------------------- #
# Fleet comparison
# --------------------------------------------------------------------------- #
_REFERENCE_CSV = Path(__file__).resolve().parent.parent / "data" / "reference_aircraft.csv"

st.subheader("Comparison with similar aircraft")
st.caption(
    "Wing loading (W/S) and power loading (W/P) and MTOW-vs-OEW against a reference "
    "fleet. Reference figures are nominal published specs for visual comparison only."
)

# This airplane's totals, if known from other slices (configuration carries no weight).
mtow = None
if project.speeds is not None and project.speeds.weight_lb:
    mtow = project.speeds.weight_lb
elif project.weight is not None and project.weight.items:
    mtow = project.weight.direct_totals()[0]
power = sum((e.max_cont_hp or 0.0) for e in project.engines) if project.engines else 0.0

try:
    fleet = pd.read_csv(_REFERENCE_CSV, comment="#")
except FileNotFoundError:
    st.info(f"Reference aircraft data file not found at {_REFERENCE_CSV}.")
else:
    fleet["series"] = "Reference fleet"
    fleet["w_s"] = fleet["mtow_lb"] / fleet["wing_area_ft2"]
    fleet["w_p"] = fleet["mtow_lb"] / fleet["max_hp"].where(fleet["max_hp"] > 0)
    rows = []
    if mtow:
        this = {"aircraft": project.name or "This airplane", "mtow_lb": mtow,
                "oew_lb": None, "wing_area_ft2": layout.wing_area_sqft,
                "max_hp": power, "series": "This airplane"}
        this["w_s"] = mtow / layout.wing_area_sqft if layout.wing_area_sqft else None
        this["w_p"] = mtow / power if power else None
        rows.append(this)
    plot_df = pd.concat([fleet, pd.DataFrame(rows)], ignore_index=True) if rows else fleet

    tab1, tab2 = st.tabs(["Wing loading vs power loading", "MTOW vs OEW"])
    with tab1:
        wp_df = plot_df.dropna(subset=["w_s", "w_p"])
        fig = px.scatter(
            wp_df, x="w_s", y="w_p", color="series", symbol="series",
            hover_name="aircraft", hover_data=["mtow_lb", "max_hp", "wing_area_ft2"],
            color_discrete_map={"Reference fleet": "#1f77b4", "This airplane": "#d62728"},
            labels={"w_s": "Wing loading W/S (lb/ft²)", "w_p": "Power loading W/P (lb/hp)", "series": ""},
        )
        fig.update_layout(legend=dict(orientation="h", y=1.1, x=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Jets (max_hp = 0) are excluded from this plot.")
    with tab2:
        oew_df = plot_df.dropna(subset=["oew_lb"])
        fig2 = px.scatter(
            oew_df, x="oew_lb", y="mtow_lb", color="series", symbol="series",
            log_x=True, log_y=True, hover_name="aircraft",
            color_discrete_map={"Reference fleet": "#1f77b4", "This airplane": "#d62728"},
            labels={"oew_lb": "Empty weight OEW (lb)", "mtow_lb": "MTOW (lb)", "series": ""},
        )
        fig2.update_layout(legend=dict(orientation="h", y=1.1, x=0))
        st.plotly_chart(fig2, use_container_width=True)

    if mtow is None:
        st.info("Set the design weight (Structural Speeds) or itemized weights to plot this airplane.")

    with st.expander("Reference fleet data"):
        st.dataframe(fleet.drop(columns=["series"]), hide_index=True, use_container_width=True)
