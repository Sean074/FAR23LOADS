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

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components import render_applicability_banner

from farloads.applicability import effective_occupants
from farloads import (
    FuselageOutline,
    FuselageSection,
    GeometryInput,
    LayoutInput,
    MassItemKind,
    Project,
    SurfaceInput,
    TailLoadsInput,
    TailType,
    UnitSystem,
    VTailLoadsInput,
    WeightInput,
    consistency_warnings,
    convert_results,
    default_fuselage_outline,
    labels_for,
    to_display,
    to_imperial_scalar,
)
from farloads import io as farloads_io
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
from farloads.modules.wing_geometry import geometry_properties, surface_top_outline
from farloads.report import module_text_report

_TAIL_TYPE_LABELS = {
    TailType.CONVENTIONAL: "Conventional",
    TailType.T_TAIL: "T-tail",
    TailType.V_TAIL: "V-tail",
    TailType.CRUCIFORM: "Cruciform",
}
_TAIL_TYPE_BY_LABEL = {v: k for k, v in _TAIL_TYPE_LABELS.items()}


st.title("Geometry")
st.caption(
    "The single geometry source of truth (Step G1): parametric fuselage / wing / "
    "tail / gear, the fuselage outline, and the WINGGEOM lifting-surface planforms "
    "on one page. Every downstream page reads this read-only. A modern addition with "
    "no original program and no regression oracle; figures are first-order estimates."
)

project: Project = st.session_state.get("project", Project(name=""))
render_applicability_banner(project)
for _w in consistency_warnings(project):
    # The Geometry page is the merged home of the old Configuration & Layout and
    # Wing Geometry pages (Step G1), so it surfaces both warning categories.
    if _w.page in ("configuration_layout", "wing_geometry"):
        st.warning(_w.message)
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"weight","length","area_sqft",...} -> unit string

# Read-only echo of the occupant count (owned by the Structural Speeds page,
# StructuralSpeedsInput.occupants; falls back to the Weight Estimate seat count).
_occupants = effective_occupants(project)
if _occupants is not None:
    st.caption(f"Occupants (from Structural Speeds / Weight Estimate): **{_occupants}**")

# No parametric slice yet (e.g. a loaded project that has WINGGEOM surfaces but
# was never edited on this page): seed the parametric wing fields from the existing
# "wing" surface rather than showing blank defaults for data the project already
# has. Not committed to project.geometry.parametric until Apply.
_parametric = project.geometry.parametric if project.geometry is not None else None
_from_geometry = False
if _parametric is not None:
    layout = _parametric
else:
    layout = LayoutInput()
    wing_surf = project.geometry.by_name("wing") if project.geometry else None
    if wing_surf is not None and len(wing_surf.leading_edge) >= 2 and len(wing_surf.trailing_edge) >= 2:
        try:
            layout = replace(layout, **wing_layout_from_surface(wing_surf))
            _from_geometry = True
        except (ValueError, ZeroDivisionError):
            pass


def _set_geometry(proj: Project, **changes) -> None:
    """Write ``changes`` onto the unified geometry slice, creating it if absent
    and preserving the other geometry fields (parametric / surfaces / fuselage).

    This page is the sole owner/editor of ``Project.geometry``; downstream pages
    read it read-only (Step G1)."""
    geom = proj.geometry or GeometryInput()
    proj.geometry = replace(geom, **changes)
    st.session_state["project"] = proj


# --------------------------------------------------------------------------- #
# Input groups
# --------------------------------------------------------------------------- #
def _num(label: str, value: float, key: str, kind: str | None = None, step: float = 1.0,
         help: str | None = None) -> float:
    """A ``number_input`` seeded from a canonical Imperial ``value``.

    When ``kind`` is given, the widget displays/accepts the value converted
    into the selected unit system (label gets the unit suffix, key gets a
    per-system suffix so switching units re-seeds the widget with converted
    defaults). ``kind=None`` is for system-independent quantities (ratios,
    angles) and passes the value through unchanged. ``help`` is the hover
    tooltip (Step E2).
    """
    if kind is None:
        return float(st.number_input(label, value=float(value), step=step, key=key, help=help))
    display_value = float(round(to_display(value, kind, system), 4))
    return float(st.number_input(f"{label} ({U[kind]})", value=display_value, step=step,
                                  key=f"{key}_{system.value}", help=help))


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
            fuselage_length = _num("Length", layout.fuselage_length, "f_len", "length",
                                   help="Overall fuselage length, nose to tail (concept estimate — configuration.py).")
            fuselage_width = _num("Width", layout.fuselage_width, "f_wid", "length",
                                  help="Maximum fuselage width; sets the top-view body outline.")
            fuselage_height = _num("Height", layout.fuselage_height, "f_hgt", "length",
                                   help="Maximum fuselage height; sets the side/front-view body outline.")
            datum_x = _num("Nose datum station", layout.datum_x, "f_dat", "length",
                           help="Fuselage station of the nose reference datum; all X stations are measured aft "
                                "from here (WTONECG station convention).")
        with st.expander("Wing", expanded=True):
            wing_area_sqft = _num("Area S", layout.wing_area_sqft, "w_area", "area_sqft",
                                  help="Reference (trapezoidal) wing planform area S; drives W/S and the "
                                       "WINGGEOM surface seed (Ch 4).")
            aspect_ratio = _num("Aspect ratio", layout.aspect_ratio, "w_ar", None, 0.1,
                                help="Wing aspect ratio AR = b²/S; sets the derived span for a given area.")
            taper_ratio = _num("Taper ratio", layout.taper_ratio, "w_taper", None, 0.05,
                               help="Tip/root chord ratio λ (0 < λ ≤ 1); values > 1 are flagged inconsistent.")
            le_sweep_deg = _num("LE sweep (deg)", layout.le_sweep_deg, "w_sweep", None, 0.5,
                                help="Leading-edge sweep angle Λ_LE, degrees.")
            dihedral_deg = _num("Dihedral (deg)", layout.dihedral_deg, "w_dih", None, 0.5,
                                help="Wing dihedral angle, degrees; seeds the Wing/Tail Loads pages and the "
                                     "front-view sketch.")
            le_root_x = _num("LE root station", layout.le_root_x, "w_lex", "length",
                             help="Fuselage station of the wing root leading edge; positions the planform "
                                  "and sets XLEMAC.")
            root_waterline_z = _num("Root waterline", layout.root_waterline_z, "w_wl", "length",
                                    help="Vertical (Z) waterline of the wing root; sets wing height for the "
                                         "side/front views.")
        with st.expander("Tail arrangement"):
            tail_type_label = st.selectbox(
                "Tail type", list(_TAIL_TYPE_LABELS.values()),
                index=list(_TAIL_TYPE_LABELS.keys()).index(layout.tail_type), key="tail_type",
                help="Empennage arrangement; T-tail/cruciform auto-place the h-tail Z when its offset is 0.",
            )
            h_tail_z = _num("H-tail Z offset from waterline (0 = auto for T-tail/cruciform)",
                            layout.h_tail_z, "h_z", "length", 1.0,
                            help="Vertical offset of the h-tail above the root waterline; leave 0 to auto-place "
                                 "on the fin for a T-tail/cruciform.")
            st.caption(
                "H-/V-tail **area, span and the elevator/rudder** are the analysis-native "
                "inputs — set them once in the **Empennage & control surfaces** section "
                "below (Step G6, single source; the three-view draws them from there)."
            )
        with st.expander("Landing gear"):
            nose_gear_x = _num("Nose gear station", layout.nose_gear_x, "g_nose", "length",
                               help="Fuselage station of the nose-gear contact point (LANDLOAD geometry, Ch 10).")
            main_gear_x = _num("Main gear station", layout.main_gear_x, "g_main", "length",
                               help="Fuselage station of the main-gear contact point; with the CG sets the "
                                    "tip-back margin.")
            track = _num("Track", layout.track, "g_track", "length",
                         help="Main-gear track (lateral wheel spacing); with CG height sets the overturn angle.")
            gear_height = _num("Gear height", layout.gear_height, "g_hgt", "length",
                               help="Ground-to-waterline gear height; sets the ground line in the side/front views.")
        applied = st.form_submit_button("Apply geometry", type="primary")

    with st.expander("ℹ️ Parameter guide", expanded=False):
        st.markdown(
            "- **Datum / station** — X stations are fuselage stations measured aft from the nose datum "
            "(inches). Y is butt line (lateral, +right), Z is waterline (vertical, +up).\n"
            "- **MAC** — mean aerodynamic chord, the reference chord of the equivalent rectangular wing; "
            "loads and the CG are referenced to it.\n"
            "- **XLEMAC** — fuselage station of the leading edge of the MAC; the origin for %-MAC positions.\n"
            "- **Neutral point** — the CG station at which the airplane is neutrally stable (∂Cm/∂α = 0).\n"
            "- **Static margin** — (neutral point − CG) / MAC, as a fraction of MAC; positive = statically stable.\n"
            "- **Tip-back / overturn angle** — gear-geometry margins: tip-back from the CG-to-main-gear "
            "geometry, overturn from the CG height and track.\n\n"
            "Configuration & Layout is a modern, port-free page (no manual oracle); figures are first-order "
            "concept estimates — see `farloads/modules/configuration.py`."
        )

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
        tail_type=_TAIL_TYPE_BY_LABEL[tail_type_label], h_tail_z=_imp(h_tail_z, "length"),
        nose_gear_x=_imp(nose_gear_x, "length"), main_gear_x=_imp(main_gear_x, "length"),
        track=_imp(track, "length"), gear_height=_imp(gear_height, "length"),
    )
    # Preserve a hand-edited fuselage outline; default it from the scalars when none.
    _existing_fuse = project.geometry.fuselage if project.geometry is not None else None
    _set_geometry(project, parametric=layout,
                  fuselage=_existing_fuse or default_fuselage_outline(layout))

_parametric = project.geometry.parametric if project.geometry is not None else None
if _parametric is None:
    st.info(
        "No geometry defined yet -- fill in at least the wing area and aspect "
        "ratio in the sidebar and Apply geometry."
    )
    st.stop()
layout = _parametric

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
    # Fuselage top-view outline: the body sections (plan-view half-widths) when a
    # fuselage outline is present, else the coarse length x width rectangle.
    fuse = project.geometry.fuselage if project.geometry is not None else None
    nose, tail = layout.datum_x, layout.datum_x + layout.fuselage_length
    hw = layout.fuselage_width / 2.0
    if fuse is not None and fuse.sections:
        secs = fuse.sections
        top_x = [s.x for s in secs] + [s.x for s in reversed(secs)] + [secs[0].x]
        top_y = ([s.width / 2.0 for s in secs]
                 + [-s.width / 2.0 for s in reversed(secs)] + [secs[0].width / 2.0])
    else:
        top_x = [nose, tail, tail, nose, nose]
        top_y = [hw, hw, -hw, -hw, hw]
    fig.add_scatter(x=top_x, y=top_y, mode="lines", line=dict(color="#888"),
                    showlegend=False, row=1, col=1)
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
    if fuse is not None and fuse.sections:
        cz = layout.root_waterline_z
        side_x = [s.x for s in secs] + [s.x for s in reversed(secs)] + [secs[0].x]
        side_y = ([cz + s.height / 2.0 for s in secs]
                  + [cz - s.height / 2.0 for s in reversed(secs)] + [cz + secs[0].height / 2.0])
    else:
        side_x = [nose, tail, tail, nose, nose]
        side_y = [z0, z0, z0 + fh, z0 + fh, z0]
    fig.add_scatter(x=side_x, y=side_y, mode="lines",
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

    # --- Tail panels + elevator/rudder (Step G6: from the single-source ---
    # --- empennage; control surfaces shaded distinctly).                 ---
    _emp = project.geometry.empennage if project.geometry is not None else None
    for name, panel in tail_planform(layout, _emp).items():
        ctrl = name.startswith(("elevator", "rudder"))
        color = "#d62728" if ctrl else "#ff7f0e"
        fill = "toself" if ctrl else None
        for col, key in ((1, "top"), (2, "side"), (3, "front")):
            fig.add_scatter(x=[p[0] for p in panel[key]], y=[p[1] for p in panel[key]],
                            mode="lines", line=dict(color=color), fill=fill,
                            fillcolor="rgba(214,39,40,0.25)" if ctrl else None,
                            name=name if ctrl and col == 1 else None,
                            showlegend=ctrl and col == 1, row=1, col=col)

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


# --------------------------------------------------------------------------- #
# Empennage & control surfaces (Step G6): single-source tail + elevator/rudder
# geometry, edited once here (drives the three-view above AND the tail-load
# analysis via the Project.tail_loads/.vtail_loads properties).
# --------------------------------------------------------------------------- #
st.subheader("Empennage & control surfaces")
st.caption(
    "Single source (Step G6) for the horizontal-/vertical-tail and elevator/rudder "
    "geometry: entered once here, it drives **both** the three-view below and the "
    "rational tail-load analysis (SELECT / TAILDIST / BALLOADS / one-engine-out). "
    "Values are Imperial engineering-native (in, ft², deg) — the manual's tail-load "
    "input set. The three-view draws the elevator/rudder as the aft Saft/S chord band."
)
_emp = project.geometry.empennage if project.geometry is not None else None
_ht0 = (_emp.htail if _emp is not None else None) or TailLoadsInput()
_vt0 = (_emp.vtail if _emp is not None else None) or VTailLoadsInput()

with st.form("empennage_form"):
    en_h = st.checkbox("Model horizontal tail + elevator",
                       value=_emp is not None and _emp.htail is not None)
    with st.expander("Horizontal tail & elevator", expanded=True):
        c = st.columns(3)
        ht_area = c[0].number_input("H-tail area ST (ft²)", min_value=0.0,
                                    value=float(_ht0.htail_area_sqft), key="en_ht_area")
        ht_semi = c[1].number_input("H-tail semi-span (in)", min_value=0.0,
                                    value=float(_ht0.htail_semispan_in), key="en_ht_semi")
        ht_arht = c[2].number_input("H-tail aspect ratio ARHT", min_value=0.0,
                                    value=float(_ht0.aspect_ratio_htail), key="en_arht")
        ht_arw = c[0].number_input("Wing aspect ratio ARW", min_value=0.0,
                                   value=float(_ht0.aspect_ratio_wing), key="en_arw")
        ht_xt25 = c[1].number_input("25% tail-MAC station xt25 (in)",
                                    value=float(_ht0.xt25), key="en_xt25")
        ht_xt50 = c[2].number_input("50% tail-MAC station xt50 (in)",
                                    value=float(_ht0.xt50), key="en_xt50")
        ht_it = c[0].number_input("Tail incidence IT (deg)",
                                  value=float(_ht0.tail_incidence_deg), key="en_it")
        ht_lf = c[1].number_input("Airplane length LF (in)", min_value=0.0,
                                  value=float(_ht0.airplane_length_in), key="en_lf")
        ht_aw = c[2].number_input("Wing lift slope AW (per rad)",
                                  value=float(_ht0.wing_lift_slope_per_rad), key="en_aw")
        ht_iwc = c[0].number_input("Wing zero-lift, cruise (deg)",
                                   value=float(_ht0.wing_zero_lift_cruise_deg), key="en_iwc")
        ht_iwe = c[1].number_input("Wing zero-lift, enroute (deg)",
                                   value=float(_ht0.wing_zero_lift_enroute_deg), key="en_iwe")
        ht_iwl = c[2].number_input("Wing zero-lift, landing (deg)",
                                   value=float(_ht0.wing_zero_lift_landing_deg), key="en_iwl")
        st.markdown("**Elevator**")
        e = st.columns(3)
        el_se = e[0].number_input("Elevator area SE (ft²)", min_value=0.0,
                                  value=float(_ht0.elevator_area_sqft), key="en_se")
        el_fwd = e[1].number_input("Area fwd of hinge SEFWDHL (ft²)", min_value=0.0,
                                   value=float(_ht0.elevator_fwd_hinge_sqft), key="en_sefwd")
        el_aft = e[2].number_input("Area aft of hinge SEAFTHL (ft²)", min_value=0.0,
                                   value=float(_ht0.elevator_aft_hinge_sqft), key="en_seaft")
        el_up = e[0].number_input("TE-up deflection EUP (deg)", min_value=0.0,
                                  value=float(_ht0.elevator_te_up_deg), key="en_eup")
        el_dn = e[1].number_input("TE-down deflection EDN (deg)", min_value=0.0,
                                  value=float(_ht0.elevator_te_down_deg), key="en_edn")
        el_eff = e[2].number_input("Elevator effectiveness", min_value=0.0,
                                   value=float(_ht0.elevator_effectiveness), key="en_eeff")

    en_v = st.checkbox("Model vertical tail + rudder",
                       value=_emp is not None and _emp.vtail is not None)
    with st.expander("Vertical tail & rudder", expanded=True):
        c = st.columns(3)
        vt_area = c[0].number_input("V-tail area SV (ft²)", min_value=0.0,
                                    value=float(_vt0.vtail_area_sqft), key="en_vt_area")
        vt_span = c[1].number_input("V-tail span (in)", min_value=0.0,
                                    value=float(_vt0.vtail_span_in), key="en_vt_span")
        vt_arvt = c[2].number_input("V-tail aspect ratio ARVT", min_value=0.0,
                                    value=float(_vt0.aspect_ratio_vtail), key="en_arvt")
        vt_mac = c[0].number_input("V-tail MAC (in)", min_value=0.0,
                                   value=float(_vt0.vtail_mac_in), key="en_vmac")
        vt_xv25 = c[1].number_input("25% V-tail-MAC station xv25 (in)",
                                    value=float(_vt0.xv25), key="en_xv25")
        vt_xv50 = c[2].number_input("50% V-tail-MAC station xv50 (in)",
                                    value=float(_vt0.xv50), key="en_xv50")
        vt_b = c[0].number_input("Wing span B (in)", min_value=0.0,
                                 value=float(_vt0.wing_span_in), key="en_wspan")
        vt_lf = c[1].number_input("Airplane length LF (in)", min_value=0.0,
                                  value=float(_vt0.airplane_length_in), key="en_vlf")
        vt_gw = c[2].number_input("Gross weight GW (lb, 0=auto)", min_value=0.0,
                                  value=float(_vt0.gross_weight_lb), key="en_gw")
        vt_izz = c[0].number_input("Yaw inertia IZZ (slug·ft², 0=auto)", min_value=0.0,
                                   value=float(_vt0.izz_slugft2), key="en_izz")
        st.markdown("**Rudder**")
        r = st.columns(3)
        rd_sr = r[0].number_input("Rudder area SR (ft²)", min_value=0.0,
                                  value=float(_vt0.rudder_area_sqft), key="en_sr")
        rd_fwd = r[1].number_input("Area fwd of hinge SRFWDHL (ft²)", min_value=0.0,
                                   value=float(_vt0.rudder_fwd_hinge_sqft), key="en_srfwd")
        rd_aft = r[2].number_input("Area aft of hinge SRAFTHL (ft²)", min_value=0.0,
                                   value=float(_vt0.rudder_aft_hinge_sqft), key="en_sraft")
        rd_rd = r[0].number_input("Rudder deflection RD (deg)", min_value=0.0,
                                  value=float(_vt0.rudder_deflection_deg), key="en_rd")
        rd_efv = r[1].number_input("Large-deflection factor EFV", min_value=0.0,
                                   value=float(_vt0.rudder_large_deflection_factor), key="en_efv")
    en_applied = st.form_submit_button("Apply empennage", type="primary")

if en_applied:
    project.tail_loads = TailLoadsInput(
        tail_incidence_deg=ht_it, wing_zero_lift_cruise_deg=ht_iwc,
        wing_zero_lift_enroute_deg=ht_iwe, wing_zero_lift_landing_deg=ht_iwl,
        aspect_ratio_wing=ht_arw, aspect_ratio_htail=ht_arht, htail_area_sqft=ht_area,
        elevator_effectiveness=el_eff, xt25=ht_xt25, xt50=ht_xt50,
        elevator_te_up_deg=el_up, elevator_te_down_deg=el_dn, elevator_area_sqft=el_se,
        elevator_fwd_hinge_sqft=el_fwd, elevator_aft_hinge_sqft=el_aft,
        airplane_length_in=ht_lf, wing_lift_slope_per_rad=ht_aw, htail_semispan_in=ht_semi,
    ) if en_h else None
    project.vtail_loads = VTailLoadsInput(
        rudder_deflection_deg=rd_rd, vtail_area_sqft=vt_area, rudder_area_sqft=rd_sr,
        rudder_fwd_hinge_sqft=rd_fwd, rudder_aft_hinge_sqft=rd_aft, aspect_ratio_vtail=vt_arvt,
        vtail_mac_in=vt_mac, xv25=vt_xv25, xv50=vt_xv50, airplane_length_in=vt_lf,
        wing_span_in=vt_b, gross_weight_lb=vt_gw, rudder_large_deflection_factor=rd_efv,
        izz_slugft2=vt_izz, vtail_span_in=vt_span,
    ) if en_v else None
    st.session_state["project"] = project
    st.success("Empennage geometry updated.")
    st.rerun()

st.plotly_chart(_three_view(), use_container_width=True)

# --------------------------------------------------------------------------- #
# Fuselage outline (Step G1): the station-area table that drives the body
# profile above and (Step G4) the fuselage pitching-moment estimator.
# --------------------------------------------------------------------------- #
with st.expander("Fuselage outline (body sections)"):
    st.caption(
        f"Cross-sections nose → tail: fuselage station X and the max body width / "
        f"height at that station ({U['length']}). Drives the three-view body profile "
        "and the Step G4 pitching-moment estimator (cross-section area ≈ π/4·w·h). "
        "Defaults from the Length / Width / Height scalars; edit to refine."
    )
    _fuse = project.geometry.fuselage if project.geometry is not None else None
    _sections = (_fuse.sections if _fuse is not None else None) or (
        (default_fuselage_outline(layout) or FuselageOutline()).sections
    )
    _fuse_rows = [
        {"X": to_display(s.x, "length", system),
         "Width": to_display(s.width, "length", system),
         "Height": to_display(s.height, "length", system)}
        for s in _sections
    ]
    _fuse_cols = {
        "X": st.column_config.NumberColumn(f"Station X ({U['length']})"),
        "Width": st.column_config.NumberColumn(f"Width ({U['length']})"),
        "Height": st.column_config.NumberColumn(f"Height ({U['length']})"),
    }
    with st.form("fuselage_outline_form"):
        _fuse_df = st.data_editor(
            pd.DataFrame(_fuse_rows, columns=["X", "Width", "Height"]),
            num_rows="dynamic", column_config=_fuse_cols, key=f"fuse_sections_{system.value}",
        )
        if st.form_submit_button("Apply fuselage outline", type="primary"):
            rows = _fuse_df.dropna().to_numpy().tolist()
            sections = [
                FuselageSection(
                    x=to_imperial_scalar(x, "length", system),
                    width=to_imperial_scalar(w, "length", system),
                    height=to_imperial_scalar(h, "length", system),
                )
                for x, w, h in sorted(rows, key=lambda r: r[0])
            ]
            _set_geometry(project, fuselage=FuselageOutline(sections=sections))
            st.success(f"Saved {len(sections)} fuselage section(s).")
            st.rerun()

# --------------------------------------------------------------------------- #
# Lifting-surface planforms (WINGGEOM) -- merged onto this page (Step G1).
# The Seed button above generates the wing surface from the parametric planform;
# here each surface's leading/trailing-edge polylines are refined and integrated.
# --------------------------------------------------------------------------- #
st.subheader("Lifting-surface planforms (WINGGEOM)")
st.caption(
    "Each lifting surface is defined by its leading-/trailing-edge points (fuselage "
    f"station X, butt line Y, {U['length']}), inboard → outboard, and the strip count "
    "the chord is integrated over. The wing's MAC / XLEMAC seed the weight-envelope "
    "and structural-speed pages."
)
_geometry = project.geometry or GeometryInput()

with st.form("add_surface_form", clear_on_submit=True):
    _new_name = st.text_input("New surface name", value="", placeholder="e.g. wing")
    if st.form_submit_button("Add surface") and _new_name:
        _surfaces = list(_geometry.surfaces) + [
            SurfaceInput(name=_new_name, leading_edge=[], trailing_edge=[])
        ]
        _set_geometry(project, surfaces=_surfaces)
        st.rerun()

if not _geometry.surfaces:
    st.info(
        "No lifting surfaces defined yet -- Seed the wing geometry (button below) or "
        "add one above (e.g. \"wing\") to enter its leading/trailing-edge points."
    )
else:
    with st.form("surface_geometry_form"):
        _surface_inputs = []
        for _surf in _geometry.surfaces:
            with st.expander(f"Surface: {_surf.name}", expanded=(_surf.name == "wing")):
                _c = st.columns(2)
                _sym = _c[0].checkbox("Symmetric about CL", value=_surf.symmetric,
                                      key=f"sym_{_surf.name}")
                _elems = _c[1].number_input("Integration elements", min_value=2, max_value=100,
                                            value=int(_surf.elements), key=f"el_{_surf.name}")
                st.caption(f"Points entered in {U['length']}.")
                _le = [(to_display(x, "length", system), to_display(y, "length", system))
                       for x, y in _surf.leading_edge]
                _te = [(to_display(x, "length", system), to_display(y, "length", system))
                       for x, y in _surf.trailing_edge]
                _le_cols = {"XLE": st.column_config.NumberColumn(f"XLE ({U['length']})"),
                            "YLE": st.column_config.NumberColumn(f"YLE ({U['length']})")}
                _te_cols = {"XTE": st.column_config.NumberColumn(f"XTE ({U['length']})"),
                            "YTE": st.column_config.NumberColumn(f"YTE ({U['length']})")}
                _le_df = st.data_editor(pd.DataFrame(_le, columns=["XLE", "YLE"]),
                                        num_rows="dynamic", column_config=_le_cols,
                                        key=f"le_{_surf.name}_{system.value}")
                _te_df = st.data_editor(pd.DataFrame(_te, columns=["XTE", "YTE"]),
                                        num_rows="dynamic", column_config=_te_cols,
                                        key=f"te_{_surf.name}_{system.value}")
                _surface_inputs.append((_surf.name, _sym, _elems, _le_df, _te_df))
        if st.form_submit_button("Apply surface geometry", type="primary"):
            def _imp_pt(row):
                return tuple(to_imperial_scalar(v, "length", system) for v in row)

            _edited = [
                SurfaceInput(
                    name=name, symmetric=sym, elements=int(elems),
                    leading_edge=[_imp_pt(r) for r in le_df.dropna().to_numpy().tolist()],
                    trailing_edge=[_imp_pt(r) for r in te_df.dropna().to_numpy().tolist()],
                )
                for name, sym, elems, le_df, te_df in _surface_inputs
            ]
            _set_geometry(project, surfaces=_edited)
            st.success(f"Applied {len(_edited)} surface(s).")
            st.rerun()

    try:
        _surf_results = geometry_properties(project.geometry, project)
    except (ValueError, ZeroDivisionError) as _exc:
        _surf_results = None
        st.caption(f"Surface integration pending: {_exc}")
    if _surf_results:
        _surf_display = convert_results(_surf_results, system)
        for _r in _surf_display:
            with st.expander(f"{_r.title}", expanded=(_r == _surf_display[0])):
                st.dataframe(
                    pd.DataFrame([{"Quantity": v.label, "Value": round(v.value, 4),
                                   "Units": v.units} for v in _r.values]),
                    hide_index=True, use_container_width=True)
                if _r.note:
                    st.caption(_r.note)
        _dl = st.columns(2)
        _dl[0].download_button(
            "Download surface geometry (CSV)",
            farloads_io.load_cases_csv(_surf_results),
            file_name="wing_geometry.csv", mime="text/csv",
        )
        _dl[1].download_button(
            "Download surface geometry (text)",
            module_text_report("Aerodynamic surface geometry", _surf_results),
            file_name="wing_geometry.txt", mime="text/plain",
        )

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
            x = c1.number_input("X (in)", value=float(eng.engine_cg[0]), key=f"eng_cg_x_{i}",
                                help="Engine CG fuselage station (inches aft of the nose datum).")
            y = c2.number_input("Y (in)", value=float(eng.engine_cg[1]), key=f"eng_cg_y_{i}",
                                help="Engine CG butt line (inches, +right of centreline).")
            z = c3.number_input("Z (in)", value=float(eng.engine_cg[2]), key=f"eng_cg_z_{i}",
                                help="Engine CG waterline (inches, +up).")
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
        geom = project.geometry or GeometryInput()
        surfaces = [s for s in geom.surfaces if s.name != "wing"]
        surfaces.insert(0, wing_surface(layout))
        _set_geometry(project, surfaces=surfaces)
        st.success(
            f"Seeded the wing surface (MAC {mac:.2f} in, XLEMAC {xlemac:.2f} in). "
            "Refine it in the Lifting-surface planforms section below."
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
                "No weight items to seed. Add items on the Weight & Mass Properties "
                "page (the Weight, CG & Inertia tab, or the Estimate tab's seed button) first."
            )
        else:
            stations = component_stations(
                layout, project.geometry.empennage if project.geometry is not None else None)
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
