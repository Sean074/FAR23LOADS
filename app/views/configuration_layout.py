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
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components import render_applicability_banner

from farloads.applicability import effective_occupants
from farloads import (
    LayoutInput,
    MassItemKind,
    Project,
    TailType,
    UnitSystem,
    WeightInput,
    convert_results,
    labels_for,
    to_display,
    to_imperial_scalar,
)
from farloads.modules.configuration import (
    cg_estimate,
    component_stations,
    configuration_properties,
    match_component_station,
    tail_planform,
    wing_layout_from_surface,
    wing_polylines,
    wing_surface,
)
from farloads.modules.wing_geometry import surface_top_outline

_TAIL_TYPE_LABELS = {
    TailType.CONVENTIONAL: "Conventional",
    TailType.T_TAIL: "T-tail",
    TailType.V_TAIL: "V-tail",
    TailType.CRUCIFORM: "Cruciform",
}
_TAIL_TYPE_BY_LABEL = {v: k for k, v in _TAIL_TYPE_LABELS.items()}


st.title("Configuration & Layout")
st.caption(
    "Parametric fuselage / wing / tail / gear geometry — the geometric source of "
    "truth that seeds the geometry, weight and speeds pages. A modern addition with "
    "no original program and no regression oracle; figures are first-order estimates."
)

project: Project = st.session_state.get("project", Project(name=""))
render_applicability_banner(project)
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"weight","length","area_sqft","length_ft",...} -> unit string

# Read-only echo of the occupant count (owned by the Structural Speeds page,
# StructuralSpeedsInput.occupants; falls back to the Weight Estimate seat count).
_occupants = effective_occupants(project)
if _occupants is not None:
    st.caption(f"Occupants (from Structural Speeds / Weight Estimate): **{_occupants}**")

# No configuration slice yet (e.g. a loaded project that has WINGGEOM surfaces
# but was never edited on this page): seed the parametric wing fields from the
# existing "wing" surface rather than showing blank defaults for data the
# project already has. Not committed to project.configuration until Apply.
_from_geometry = False
if project.configuration is not None:
    layout = project.configuration
else:
    layout = LayoutInput()
    wing_surf = project.geometry.by_name("wing") if project.geometry else None
    if wing_surf is not None and len(wing_surf.leading_edge) >= 2 and len(wing_surf.trailing_edge) >= 2:
        try:
            layout = replace(layout, **wing_layout_from_surface(wing_surf))
            _from_geometry = True
        except (ValueError, ZeroDivisionError):
            pass


# --------------------------------------------------------------------------- #
# Input groups
# --------------------------------------------------------------------------- #
def _num(label: str, value: float, key: str, kind: str | None = None, step: float = 1.0) -> float:
    """A ``number_input`` seeded from a canonical Imperial ``value``.

    When ``kind`` is given, the widget displays/accepts the value converted
    into the selected unit system (label gets the unit suffix, key gets a
    per-system suffix so switching units re-seeds the widget with converted
    defaults). ``kind=None`` is for system-independent quantities (ratios,
    angles) and passes the value through unchanged.
    """
    if kind is None:
        return float(st.number_input(label, value=float(value), step=step, key=key))
    display_value = float(round(to_display(value, kind, system), 4))
    return float(st.number_input(f"{label} ({U[kind]})", value=display_value, step=step,
                                  key=f"{key}_{system.value}"))


with st.sidebar:
    st.header(f"Geometry ({U['length']} / {U['area_sqft']})")
    st.caption(
        f"Input units: **{'Imperial' if system == UnitSystem.IMPERIAL else 'SI'}** "
        "(set in the sidebar's global **Units** control, above). Switching it "
        "re-seeds these fields with converted defaults."
    )
    if _from_geometry:
        st.caption(
            "Wing area/aspect ratio/taper/sweep/LE station below were derived from "
            "the project's existing **wing** surface (Wing Geometry page) -- review "
            "and **Apply geometry** to save them into Configuration & Layout."
        )
    with st.form("layout_form"):
        with st.expander("Fuselage", expanded=True):
            fuselage_length = _num("Length", layout.fuselage_length, "f_len", "length")
            fuselage_width = _num("Width", layout.fuselage_width, "f_wid", "length")
            fuselage_height = _num("Height", layout.fuselage_height, "f_hgt", "length")
            datum_x = _num("Nose datum station", layout.datum_x, "f_dat", "length")
        with st.expander("Wing", expanded=True):
            wing_area_sqft = _num("Area S", layout.wing_area_sqft, "w_area", "area_sqft")
            aspect_ratio = _num("Aspect ratio", layout.aspect_ratio, "w_ar", None, 0.1)
            taper_ratio = _num("Taper ratio", layout.taper_ratio, "w_taper", None, 0.05)
            le_sweep_deg = _num("LE sweep (deg)", layout.le_sweep_deg, "w_sweep", None, 0.5)
            dihedral_deg = _num("Dihedral (deg)", layout.dihedral_deg, "w_dih", None, 0.5)
            le_root_x = _num("LE root station", layout.le_root_x, "w_lex", "length")
            root_waterline_z = _num("Root waterline", layout.root_waterline_z, "w_wl", "length")
        with st.expander("Tail"):
            tail_type_label = st.selectbox(
                "Tail type", list(_TAIL_TYPE_LABELS.values()),
                index=list(_TAIL_TYPE_LABELS.keys()).index(layout.tail_type), key="tail_type",
            )
            h_tail_area = _num("H-tail area", layout.h_tail_area, "h_area", "area_sqft")
            h_tail_arm = _num("H-tail arm", layout.h_tail_arm, "h_arm", "length")
            h_tail_span_ft = _num("H-tail span", layout.h_tail_span_ft, "h_span", "length_ft", 0.5)
            h_tail_z = _num("H-tail Z offset from waterline (0 = auto for T-tail/cruciform)",
                            layout.h_tail_z, "h_z", "length", 1.0)
            v_tail_area = _num("V-tail area", layout.v_tail_area, "v_area", "area_sqft")
            v_tail_arm = _num("V-tail arm", layout.v_tail_arm, "v_arm", "length")
            v_tail_span_ft = _num("V-tail span", layout.v_tail_span_ft, "v_span", "length_ft", 0.5)
        with st.expander("Landing gear"):
            nose_gear_x = _num("Nose gear station", layout.nose_gear_x, "g_nose", "length")
            main_gear_x = _num("Main gear station", layout.main_gear_x, "g_main", "length")
            track = _num("Track", layout.track, "g_track", "length")
            gear_height = _num("Gear height", layout.gear_height, "g_hgt", "length")
        applied = st.form_submit_button("Apply geometry", type="primary")

if applied:
    def _imp(v: float, kind: str) -> float:
        return to_imperial_scalar(v, kind, system)

    # This page owns the whole configuration slice, so a wholesale replace on
    # Apply is correct here (unlike a slice shared with other pages/edits).
    layout = LayoutInput(
        fuselage_length=_imp(fuselage_length, "length"), fuselage_width=_imp(fuselage_width, "length"),
        fuselage_height=_imp(fuselage_height, "length"), datum_x=_imp(datum_x, "length"),
        wing_area_sqft=_imp(wing_area_sqft, "area_sqft"), aspect_ratio=aspect_ratio, taper_ratio=taper_ratio,
        dihedral_deg=dihedral_deg, le_sweep_deg=le_sweep_deg, le_root_x=_imp(le_root_x, "length"),
        root_waterline_z=_imp(root_waterline_z, "length"),
        h_tail_area=_imp(h_tail_area, "area_sqft"), h_tail_arm=_imp(h_tail_arm, "length"),
        v_tail_area=_imp(v_tail_area, "area_sqft"), v_tail_arm=_imp(v_tail_arm, "length"),
        tail_type=_TAIL_TYPE_BY_LABEL[tail_type_label],
        h_tail_span_ft=_imp(h_tail_span_ft, "length_ft"), h_tail_z=_imp(h_tail_z, "length"),
        v_tail_span_ft=_imp(v_tail_span_ft, "length_ft"),
        nose_gear_x=_imp(nose_gear_x, "length"), main_gear_x=_imp(main_gear_x, "length"),
        track=_imp(track, "length"), gear_height=_imp(gear_height, "length"),
    )
    project.configuration = layout
    st.session_state["project"] = project

if project.configuration is None:
    st.info(
        "No geometry defined yet -- fill in at least the wing area and aspect "
        "ratio in the sidebar and Apply geometry."
    )
    st.stop()

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
x_cg, z_cg, cg_source = cg_estimate(project, layout, derived)
np_station = derived.get("Neutral point station")


# --------------------------------------------------------------------------- #
# Three-view
# --------------------------------------------------------------------------- #
def _three_view() -> go.Figure:
    le, te = wing_polylines(layout)
    semi = le[-1][1]
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Top", "Side", "Front"))

    # --- Top view: X (horizontal) vs Y (lateral). Wing planform both sides. ---
    for xs, ys in surface_top_outline(le, te, symmetric=True):
        fig.add_scatter(x=xs, y=ys, mode="lines",
                        line=dict(color="#1f77b4"), showlegend=False, row=1, col=1)
    # Fuselage outline (length x width).
    nose, tail = layout.datum_x, layout.datum_x + layout.fuselage_length
    hw = layout.fuselage_width / 2.0
    fig.add_scatter(x=[nose, tail, tail, nose, nose], y=[hw, hw, -hw, -hw, hw],
                    mode="lines", line=dict(color="#888"), showlegend=False, row=1, col=1)
    # CG / NP markers.
    fig.add_scatter(x=[x_cg], y=[0], mode="markers", marker=dict(color="#d62728", size=11, symbol="x"),
                    name=f"CG ({cg_source})", row=1, col=1)
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
    fig.add_scatter(x=[x_cg], y=[z_cg], mode="markers",
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

    # --- Tail (h-tail / v-tail / V-tail panels), sketched from tail_type. ---
    for panel in tail_planform(layout).values():
        top_xs = [p[0] for p in panel["top"]]
        top_ys = [p[1] for p in panel["top"]]
        fig.add_scatter(x=top_xs, y=top_ys, mode="lines", line=dict(color="#ff7f0e"),
                        showlegend=False, row=1, col=1)
        side_xs = [p[0] for p in panel["side"]]
        side_ys = [p[1] for p in panel["side"]]
        fig.add_scatter(x=side_xs, y=side_ys, mode="lines", line=dict(color="#ff7f0e"),
                        showlegend=False, row=1, col=2)
        front_xs = [p[0] for p in panel["front"]]
        front_ys = [p[1] for p in panel["front"]]
        fig.add_scatter(x=front_xs, y=front_ys, mode="lines", line=dict(color="#ff7f0e"),
                        showlegend=False, row=1, col=3)

    # --- Mass-item overlay (Step D4.6): one marker group per MassItemKind, ---
    # --- sized by weight, in all three views.                             ---
    _KIND_COLORS = {
        MassItemKind.EMPTY: "#7f7f7f",
        MassItemKind.MINIMUM: "#ff7f0e",
        MassItemKind.DISCRETIONARY: "#17becf",
    }

    def _marker_size(weight_lb: float) -> float:
        return max(6.0, min(24.0, 6.0 + weight_lb ** 0.5))

    mass_items = project.weight.items if project.weight else []
    groups = defaultdict(list)
    for it in mass_items:
        groups[it.kind].append(it)
    for kind, items in groups.items():
        color = _KIND_COLORS.get(kind, "#000000")
        sizes = [_marker_size(it.weight_lb) for it in items]
        names = [f"{it.name} ({it.weight_lb:.0f} lb)" for it in items]
        marker = dict(color=color, size=sizes, opacity=0.6, symbol="circle")
        fig.add_scatter(x=[it.x for it in items], y=[it.y for it in items], mode="markers",
                        marker=marker, name=f"{kind.value} items", text=names, hoverinfo="text",
                        row=1, col=1)
        fig.add_scatter(x=[it.x for it in items], y=[it.z for it in items], mode="markers",
                        marker=marker, text=names, hoverinfo="text", showlegend=False, row=1, col=2)
        fig.add_scatter(x=[it.y for it in items], y=[it.z for it in items], mode="markers",
                        marker=marker, text=names, hoverinfo="text", showlegend=False, row=1, col=3)

    # --- Engine overlay: one marker per Project.engines[] entry, at engine_cg. ---
    engines = project.engines or []
    if engines:
        ex = [e.engine_cg[0] for e in engines]
        ey = [e.engine_cg[1] for e in engines]
        ez = [e.engine_cg[2] for e in engines]
        labels = [e.engine_designation or f"Engine {i + 1}" for i, e in enumerate(engines)]
        eng_marker = dict(color="#9467bd", size=13, symbol="diamond")
        fig.add_scatter(x=ex, y=ey, mode="markers", marker=eng_marker, name="Engines",
                        text=labels, hoverinfo="text", row=1, col=1)
        fig.add_scatter(x=ex, y=ez, mode="markers", marker=eng_marker,
                        text=labels, hoverinfo="text", showlegend=False, row=1, col=2)
        fig.add_scatter(x=ey, y=ez, mode="markers", marker=eng_marker,
                        text=labels, hoverinfo="text", showlegend=False, row=1, col=3)

    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.2, x=0))
    return fig


st.plotly_chart(_three_view(), use_container_width=True)

# --------------------------------------------------------------------------- #
# Engine position write-back (Step D4.6)
# --------------------------------------------------------------------------- #
if project.engines:
    with st.expander("Engine positions (engine_cg)"):
        st.caption(
            "Numeric override of each engine's mount station (X/Y/Z, inches) -- "
            "not drag-and-drop. Defaults to the current EngineInput.engine_cg; "
            "Apply writes back and re-renders the diamond marker above."
        )
        overrides = []
        for i, eng in enumerate(project.engines):
            st.markdown(f"**{eng.engine_designation or f'Engine {i + 1}'}**")
            c1, c2, c3 = st.columns(3)
            x = c1.number_input("X (in)", value=float(eng.engine_cg[0]), key=f"eng_cg_x_{i}")
            y = c2.number_input("Y (in)", value=float(eng.engine_cg[1]), key=f"eng_cg_y_{i}")
            z = c3.number_input("Z (in)", value=float(eng.engine_cg[2]), key=f"eng_cg_z_{i}")
            overrides.append((x, y, z))
        if st.button("Apply engine positions"):
            project.engines = [
                replace(eng, engine_cg=xyz) for eng, xyz in zip(project.engines, overrides)
            ]
            st.session_state["project"] = project
            st.success(f"Updated engine_cg for {len(overrides)} engine(s).")
            st.rerun()
else:
    st.caption(
        "No engines defined yet -- add one on the Engine Mount Loads page to see "
        "it plotted on the three-view."
    )

# --------------------------------------------------------------------------- #
# Assessment + seeding
# --------------------------------------------------------------------------- #
left, right = st.columns([3, 2])
with left:
    st.subheader("Assessment")
    # Display-only conversion: `results`/`derived` above stay Imperial (inches)
    # because they feed the three-view plotting and cg_estimate() geometry math.
    display_results = convert_results(results, system)
    for r in display_results:
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

    st.caption(
        "Approximate each named component's station from the geometry above into "
        "the Weight DB (WTONECG) -- only for items whose station is still unset "
        "(0, 0, 0); a hand-entered station is never overwritten."
    )
    if st.button("Seed component stations into Weight DB"):
        items = project.weight.items if project.weight else []
        if not items:
            st.warning(
                "No weight items to seed. Add items on the Weight, CG & Inertia "
                "page (or the Weight Estimate page's seed button) first."
            )
        else:
            stations = component_stations(layout)
            seeded, new_items = 0, []
            for item in items:
                if (item.x, item.y, item.z) == (0.0, 0.0, 0.0):
                    match = match_component_station(item.name, stations)
                    if match is not None:
                        item = replace(item, x=match[0], y=match[1], z=match[2])
                        seeded += 1
                new_items.append(item)
            project.weight = WeightInput(
                estimation=project.weight.estimation, items=new_items, envelope=project.weight.envelope,
            )
            st.session_state["project"] = project
            if seeded:
                st.success(
                    f"Seeded a station for {seeded} weight item(s). Open Weight, "
                    "CG & Inertia to review or override."
                )
            else:
                st.info("No zero-station items matched a derivable component name.")

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
