"""General configuration & layout (modern addition -- no original ``.BAS``).

This module is the geometric **source of truth** for an initial concept: from the
parametric ``LayoutInput`` slice it derives the wing planform, the mean
aerodynamic chord and its leading-edge station, a tail-volume neutral-point /
static-margin estimate, and the landing-gear tip-back / overturn angles and prop
ground clearance. It then *seeds* the downstream pages (WINGGEOM polylines,
WTENV/STRSPEED ``XLEMAC``/``MAC``).

There is **no manual regression oracle** for this page; the Appendix A/B geometry
is used only as a *sanity* fixture (the derived MAC/XLEMAC must match what
WINGGEOM reproduces -- see ``tests/test_configuration.py``). To honour the rule
that a module must not recompute a quantity another module owns, the MAC /
XLEMAC / aspect ratio / span are obtained by generating the WINGGEOM edge
polylines and running them through the WINGGEOM strip integrator
(:func:`sloads.modules.wing_geometry.surface_properties`), not by an
independent integration.

Method references (Reference 1, McMaster):
- trapezoidal MAC / Y_MAC closed form, Ch 5 (cross-checked against WINGGEOM);
- tail-volume neutral point / static margin, Ch 8 (tail-volume coefficient
  ``V_H = S_t·l_t / (S_w·MAC)``; ``h_n = h_acw + V_H·(a_t/a_w)·(1 - dε/dα)``);
- tip-back / overturn (turnover) angles, standard landing-gear geometry
  (Roskam/Raymer first-cut; no FAR23 oracle).

All estimates use first-order method assumptions (documented constants below) and
are surfaced as *estimates* in the UI -- in concept mode they are flagged as
unverified extrapolation, consistent with the Phase-C validation contract.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from ..constants import IN2_PER_FT2
from ..models import (
    MissingInputError,
    ConditionResult,
    EmpennageInput,
    LandingGearGeometry,
    LayoutInput,
    LoadValue,
    ModuleResult,
    Project,
    SurfaceInput,
    TailType,
    Vec3,
)
from ..registry import register
from ..tail_geometry import fin_root_waterline
from .wing_geometry import surface_properties

_FAR = "configuration"  # modern addition; no FAR condition / no .BAS oracle
_IN = "in"
_DEG = "deg"

# Method assumptions for the tail-volume neutral-point estimate (Ref 1 Ch 8).
# First-order defaults: wing aerodynamic centre at 25% MAC, tail/wing lift-curve
# slope ratio ~1, and a typical downwash factor (1 - dε/dα) ~ 0.6. Documented and
# centralized here so a refinement is a one-line change.
_H_AC_WING = 0.25          # wing aerodynamic centre, fraction of MAC
_LIFT_SLOPE_RATIO = 1.0    # a_t / a_w
_DOWNWASH_FACTOR = 0.6     # (1 - dε/dα)

# Integration strip count for the generated-polyline WINGGEOM cross-check. A pure
# trapezoid is exact in the limit; 40 strips is well inside the ±0.1% sanity band.
_STRIPS = 40


def wing_planform(layout: LayoutInput) -> Tuple[float, float, float, float]:
    """Span, root chord, tip chord and semi-span (all inches) of the trapezoid.

    From the parametric wing (area ``S`` ft², aspect ratio ``AR``, taper ``λ``):
    ``b = √(AR·S)``; ``c_root = 2·S / (b·(1+λ))``; ``c_tip = λ·c_root`` -- the
    standard trapezoidal-wing relations, returned in inches.
    """
    if layout.wing_area_sqft <= 0 or layout.aspect_ratio <= 0:
        raise ValueError("configuration wing needs positive area and aspect ratio")
    area_in2 = layout.wing_area_sqft * IN2_PER_FT2
    taper = layout.taper_ratio
    span_in = math.sqrt(layout.aspect_ratio * layout.wing_area_sqft) * 12.0
    c_root = 2.0 * area_in2 / (span_in * (1.0 + taper))
    c_tip = taper * c_root
    return span_in, c_root, c_tip, span_in / 2.0


def wing_polylines(layout: LayoutInput) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """WINGGEOM leading-/trailing-edge polylines for the parametric wing.

    ``(X, Y)`` points inboard -> outboard (fuselage station, butt line, inches),
    in the exact shape :class:`SurfaceInput` expects, so the page can seed
    ``Project.geometry`` from the layout. The LE runs from the root station at the
    given sweep; the TE is the LE plus the local chord.
    """
    _span, c_root, c_tip, semi = wing_planform(layout)
    tan_sweep = math.tan(math.radians(layout.le_sweep_deg))
    x_le_tip = layout.le_root_x + semi * tan_sweep
    leading_edge = [(layout.le_root_x, 0.0), (x_le_tip, semi)]
    trailing_edge = [(layout.le_root_x + c_root, 0.0), (x_le_tip + c_tip, semi)]
    return leading_edge, trailing_edge


def wing_surface(layout: LayoutInput) -> SurfaceInput:
    """The generated WINGGEOM ``SurfaceInput`` for the parametric wing."""
    le, te = wing_polylines(layout)
    return SurfaceInput(name="wing", leading_edge=le, trailing_edge=te,
                        symmetric=True, elements=_STRIPS)


def wing_layout_from_surface(surf: SurfaceInput) -> Dict[str, float]:
    """Best-effort parametric wing scalars, backed out of a WINGGEOM surface.

    The inverse of :func:`wing_polylines`: area and aspect ratio come straight
    from the WINGGEOM strip integrator (:func:`wing_geometry.surface_properties`);
    root/tip chord and LE sweep are read from the leading-/trailing-edge
    polyline's root (first) and tip (last) points. Exact when the surface is the
    two-point trapezoid ``wing_polylines`` generates; a root/tip-only first-cut
    for a multi-point (e.g. cranked) polyline.

    Lets a project that already has a "wing" surface (imported ``project.json``,
    or a project built surface-first on the Wing Geometry page) seed the
    Configuration & Layout page's parametric wing fields instead of starting
    from blank defaults. ``root_waterline_z``/``dihedral_deg`` are not returned --
    a WINGGEOM surface carries no Z data to derive them from.
    """
    props = surface_properties(surf)
    values = {v.label: v.value for v in props.values}
    xf_root, yroot = surf.leading_edge[0]
    xf_tip, ytip = surf.leading_edge[-1]
    xa_root, _ = surf.trailing_edge[0]
    xa_tip, _ = surf.trailing_edge[-1]
    root_chord = xa_root - xf_root
    tip_chord = xa_tip - xf_tip
    taper_ratio = tip_chord / root_chord if root_chord else 1.0
    sweep_deg = math.degrees(math.atan2(xf_tip - xf_root, ytip - yroot)) if ytip != yroot else 0.0
    return {
        "wing_area_sqft": values["Total area"] / IN2_PER_FT2,
        "aspect_ratio": values["Aspect ratio"],
        "taper_ratio": taper_ratio,
        "le_sweep_deg": sweep_deg,
        "le_root_x": xf_root,
    }


# V-tail panels have no dedicated dihedral field (Step: tail-type usability pass);
# a fixed typical value keeps the sketch simple. Documented so a refinement is a
# one-line change, same convention as the neutral-point assumptions above.
_V_TAIL_DIHEDRAL_DEG = 40.0


def _hinge_fraction(aft_hinge_sqft: float, area_sqft: float) -> float:
    """Elevator/rudder chord fraction (hinge line to TE) from the native areas.

    ``Saft/S`` is the control-surface area aft of the hinge as a fraction of the
    surface area -- for a full-span control the chordwise fraction the movable
    surface occupies (Step G6: the three-view draws the surface from the same
    analysis-native areas, not a separate hingeline input). Clamped to a sensible
    sketch band."""
    if area_sqft <= 0 or aft_hinge_sqft <= 0:
        return 0.0
    return max(0.05, min(0.9, aft_hinge_sqft / area_sqft))


def tail_planform(layout: LayoutInput,
                  empennage: Optional["EmpennageInput"] = None) -> Dict[str, Dict[str, List[Tuple[float, float]]]]:
    """Tail-surface sketch polylines for the three-view, keyed by panel name.

    Each panel maps to ``{"top": [(x, y), ...], "side": [(x, z), ...], "front":
    [(y, z), ...]}`` -- ready-to-plot polylines/outlines in the three-view's Top
    (X, Y) / Side (X, Z) / Front (Y, Z) axes. A first-order rectangular-planform
    sketch (constant chord = area / span; the empennage carries no tail taper or
    sweep), not a structural surface definition.

    Step G6: the tail geometry is read from the single-source ``empennage``
    (``htail``/``vtail`` = the analysis-native :class:`TailLoadsInput`/
    :class:`VTailLoadsInput`) -- area ``ST``/``SV``, span (``2*htail_semispan_in`` /
    ``vtail_span_in``) and the 25%-tail-MAC station (``xt25``/``xv25``) place each
    surface, and the elevator/rudder are drawn as the aft ``Saft/S`` chord band
    (``elevator``/``rudder`` panels) so the movable surfaces come from the same data
    the loads use. Returns ``{}`` when no empennage/tail geometry is present.

    The vertical-tail root and (for ``T_TAIL``/``CRUCIFORM``) the implied
    horizontal-tail height are referenced from the top of the fuselage
    (``root_waterline_z + fuselage_height / 2``). ``layout.h_tail_z`` is a further
    user offset; if left at ``0`` for ``T_TAIL``/``CRUCIFORM`` a sensible default
    (top of fin / mid-fin) is used instead of the fuselage centreline.
    """
    ht = empennage.htail if empennage is not None else None
    vt = empennage.vtail if empennage is not None else None
    h_area = ht.htail_area_sqft if ht is not None else 0.0
    h_span_in = 2.0 * ht.htail_semispan_in if ht is not None else 0.0
    v_area = vt.vtail_area_sqft if vt is not None else 0.0
    v_span_in = vt.vtail_span_in if vt is not None else 0.0
    if h_span_in <= 0 and v_span_in <= 0:
        return {}

    # One owner for where the fin's root sits (plan 13 L-1): the sketch and the
    # load deck read the same function, so they cannot place one fin twice.
    fin_root_z = fin_root_waterline(
        layout, v_span_in, vt.vtail_root_waterline_z if vt is not None else 0.0).z
    panels: Dict[str, Dict[str, List[Tuple[float, float]]]] = {}

    if layout.tail_type == TailType.V_TAIL:
        if v_area > 0 and v_span_in > 0:
            area_in2 = (v_area * IN2_PER_FT2) / 2.0  # per panel
            chord = area_in2 / v_span_in
            x_mac = vt.xv25
            x_le, x_te = x_mac - 0.25 * chord, x_mac + 0.75 * chord
            dihedral = math.radians(_V_TAIL_DIHEDRAL_DEG)
            proj_y = v_span_in * math.cos(dihedral)
            proj_z = v_span_in * math.sin(dihedral)
            for sgn, side in ((1, "right"), (-1, "left")):
                panels[f"v_tail_{side}"] = {
                    "top": [(x_le, 0.0), (x_te, 0.0), (x_te, sgn * proj_y),
                            (x_le, sgn * proj_y), (x_le, 0.0)],
                    "side": [(x_le, fin_root_z), (x_te, fin_root_z),
                             (x_te, fin_root_z + proj_z), (x_le, fin_root_z + proj_z),
                             (x_le, fin_root_z)],
                    "front": [(0.0, fin_root_z), (sgn * proj_y, fin_root_z + proj_z)],
                }
        return panels

    if v_area > 0 and v_span_in > 0:
        area_in2 = v_area * IN2_PER_FT2
        chord = area_in2 / v_span_in
        x_mac = vt.xv25
        x_le, x_te = x_mac - 0.25 * chord, x_mac + 0.75 * chord
        z1 = fin_root_z + v_span_in
        panels["v_tail"] = {
            "top": [(x_le, 0.0), (x_te, 0.0)],
            "side": [(x_le, fin_root_z), (x_te, fin_root_z), (x_te, z1),
                     (x_le, z1), (x_le, fin_root_z)],
            "front": [(0.0, fin_root_z), (0.0, z1)],
        }
        # Rudder: aft Saft/S chord band over the fin height (Side view).
        r_frac = _hinge_fraction(vt.rudder_aft_hinge_sqft, v_area)
        if r_frac > 0:
            x_hinge = x_te - r_frac * chord
            panels["rudder"] = {
                "top": [(x_hinge, 0.0), (x_te, 0.0)],
                "side": [(x_hinge, fin_root_z), (x_te, fin_root_z), (x_te, z1),
                         (x_hinge, z1), (x_hinge, fin_root_z)],
                "front": [(0.0, fin_root_z), (0.0, z1)],
            }

    if h_area > 0 and h_span_in > 0:
        area_in2 = h_area * IN2_PER_FT2
        chord = area_in2 / h_span_in
        x_mac = ht.xt25
        x_le, x_te = x_mac - 0.25 * chord, x_mac + 0.75 * chord
        h_half = h_span_in / 2.0

        h_tail_z = layout.h_tail_z
        if h_tail_z == 0.0 and layout.tail_type == TailType.T_TAIL:
            h_tail_z = layout.fuselage_height / 2.0 + v_span_in
        elif h_tail_z == 0.0 and layout.tail_type == TailType.CRUCIFORM:
            h_tail_z = layout.fuselage_height / 2.0 + v_span_in * 0.5
        h_z = layout.root_waterline_z + h_tail_z

        panels["h_tail"] = {
            "top": [(x_le, h_half), (x_te, h_half), (x_te, -h_half),
                    (x_le, -h_half), (x_le, h_half)],
            "side": [(x_le, h_z), (x_te, h_z)],
            "front": [(-h_half, h_z), (h_half, h_z)],
        }
        # Elevator: aft Saft/S chord band over the full h-tail span (Top view).
        e_frac = _hinge_fraction(ht.elevator_aft_hinge_sqft, h_area)
        if e_frac > 0:
            x_hinge = x_te - e_frac * chord
            panels["elevator"] = {
                "top": [(x_hinge, h_half), (x_te, h_half), (x_te, -h_half),
                        (x_hinge, -h_half), (x_hinge, h_half)],
                "side": [(x_hinge, h_z), (x_te, h_z)],
                "front": [(-h_half, h_z), (h_half, h_z)],
            }

    return panels


def _wing_geometry(layout: LayoutInput) -> dict:
    """Wing MAC/XLEMAC/Y_MAC/AR/span via the WINGGEOM strip integrator.

    Reads them straight out of :func:`wing_geometry.surface_properties` so
    WINGGEOM stays the single owner of the integration.
    """
    result = surface_properties(wing_surface(layout))
    return {v.label: v.value for v in result.values}


# --------------------------------------------------------------------------- #
# Component stations -- Weight DB seeding (Step D4.3)
# --------------------------------------------------------------------------- #
# Alias substrings (lowercased) that identify a Weight-DB item as belonging to a
# derived component, most-specific first so "Horizontal tail" matches "h_tail"
# rather than the lumped "tail" catch-all (WTESTIMA's single "Tail" structure-group
# item, which has no h/v breakdown -- see estimate_to_mass_items).
_COMPONENT_ALIASES: Dict[str, Tuple[str, ...]] = {
    "h_tail": ("horizontal tail", "h-tail", "h_tail", "htail"),
    "v_tail": ("vertical tail", "v-tail", "v_tail", "vtail"),
    "main_gear": ("main gear", "main_gear"),
    "nose_gear": ("nose gear", "nose_gear"),
    "landing_gear": ("landing gear", "gear"),
    "wing": ("wing",),
    "fuselage": ("fuselage",),
    "tail": ("tail",),
}
_COMPONENT_MATCH_ORDER: Tuple[str, ...] = (
    "h_tail", "v_tail", "main_gear", "nose_gear", "landing_gear", "wing", "fuselage", "tail",
)


def gear_stations(layout: LayoutInput, landing_gear: Optional[LandingGearGeometry]) -> Optional[dict]:
    """Coarse gear geometry derived from the single-source LANDLOAD axle geometry
    (Step G6b), or ``None`` when no gear geometry is present.

    Returns ``{main_x, nose_x, track, gear_height, ground_z}`` (inches). The main/nose
    stations are the **static-axle X**; ``track`` is the tread; the ground line is the
    lowest static wheel contact (static axle ``Z`` minus rolling radius), and
    ``gear_height`` = root waterline − ground (replacing the retired coarse
    ``LayoutInput.gear_height`` — the native axle geometry is authoritative).
    """
    if landing_gear is None:
        return None
    mg, ng = landing_gear.main_gear, landing_gear.nose_gear
    main_x, nose_x = mg.axle_static[0], ng.axle_static[0]
    if main_x <= 0 and nose_x <= 0:
        return None
    wheels = []
    if main_x > 0:
        wheels.append(mg.axle_static[1] - mg.rolling_radius_in)
    if nose_x > 0:
        wheels.append(ng.axle_static[1] - ng.rolling_radius_in)
    ground_z = min(wheels) if wheels else layout.root_waterline_z
    return {"main_x": main_x, "nose_x": nose_x, "track": landing_gear.tread_in,
            "gear_height": layout.root_waterline_z - ground_z, "ground_z": ground_z}


def component_stations(layout: LayoutInput,
                       empennage: Optional[EmpennageInput] = None,
                       landing_gear: Optional[LandingGearGeometry] = None) -> Dict[str, Vec3]:
    """Approximate ``(x, y, z)`` station (fuselage station / butt line / waterline,
    inches) for each named airframe component, derived from ``LayoutInput``'s
    coarse scalars -- a rough first-cut for seeding the Weight DB (WTONECG), not a
    new schema field (Step D4.3; no per-component station sub-model was added --
    see the D-5 decision in ``docs/40_history/05_phase_d_gui_workflow_plan.md``). A seeded
    ``MassItem.x/y/z`` is always overridable by hand afterward.

    Keys present depend on which scalars are set: ``"wing"`` (25% MAC, matching the
    CG first-cut used elsewhere in this module), ``"fuselage"`` (length midpoint),
    ``"h_tail"``/``"v_tail"`` (the 25%-tail-MAC station ``xt25``/``xv25`` from the
    Step-G6 single-source ``empennage``), ``"tail"`` (area-weighted h/v average, for
    a single lumped "Tail" item), ``"main_gear"``/``"nose_gear"`` (gear station,
    strut mid-height) and ``"landing_gear"`` (weight-weighted ~3:1 main:nose
    average). All at butt line ``y=0`` (centreline).
    """
    ht = empennage.htail if empennage is not None else None
    vt = empennage.vtail if empennage is not None else None
    stations: Dict[str, Vec3] = {}
    wing_x = layout.le_root_x
    if layout.wing_area_sqft > 0 and layout.aspect_ratio > 0:
        geom = _wing_geometry(layout)
        wing_x = geom["XLE(MAC) station of MAC LE"] + 0.25 * geom["MAC"]
        stations["wing"] = (wing_x, 0.0, layout.root_waterline_z)
    if layout.fuselage_length > 0:
        stations["fuselage"] = (
            layout.datum_x + layout.fuselage_length / 2.0, 0.0, layout.root_waterline_z,
        )
    if ht is not None and ht.xt25 > 0:
        stations["h_tail"] = (ht.xt25, 0.0, layout.root_waterline_z)
    if vt is not None and vt.xv25 > 0:
        stations["v_tail"] = (vt.xv25, 0.0, layout.root_waterline_z)
    tail_pts = [
        (ht.htail_area_sqft if ht is not None else 0.0, stations["h_tail"]) if "h_tail" in stations else None,
        (vt.vtail_area_sqft if vt is not None else 0.0, stations["v_tail"]) if "v_tail" in stations else None,
    ]
    tail_pts = [p for p in tail_pts if p is not None]
    if tail_pts:
        total_area = sum(a for a, _ in tail_pts) or float(len(tail_pts))
        tail_x = sum((a or 1.0) * pt[0] for a, pt in tail_pts) / total_area
        stations["tail"] = (tail_x, 0.0, layout.root_waterline_z)
    gc = gear_stations(layout, landing_gear)
    if gc is not None and gc["gear_height"] > 0:
        gear_z = layout.root_waterline_z - gc["gear_height"] / 2.0
        if gc["main_x"] > 0:
            stations["main_gear"] = (gc["main_x"], 0.0, gear_z)
        if gc["nose_x"] > 0:
            stations["nose_gear"] = (gc["nose_x"], 0.0, gear_z)
    gear_pts = [
        (3.0, stations["main_gear"]) if "main_gear" in stations else None,
        (1.0, stations["nose_gear"]) if "nose_gear" in stations else None,
    ]
    gear_pts = [p for p in gear_pts if p is not None]
    if gear_pts:
        total_w = sum(w for w, _ in gear_pts)
        gx = sum(w * pt[0] for w, pt in gear_pts) / total_w
        gz = sum(w * pt[2] for w, pt in gear_pts) / total_w
        stations["landing_gear"] = (gx, 0.0, gz)
    return stations


def match_component_station(name: str, stations: Dict[str, Vec3]) -> Optional[Vec3]:
    """Match a ``MassItem.name`` to a :func:`component_stations` entry by
    substring alias (case-insensitive), most-specific key first. Returns
    ``None`` when no alias matches (the item is left untouched by the seed
    button)."""
    lname = name.lower()
    for key in _COMPONENT_MATCH_ORDER:
        if key not in stations:
            continue
        if any(alias in lname for alias in _COMPONENT_ALIASES[key]):
            return stations[key]
    return None


def _planform_condition(layout: LayoutInput, geom: dict) -> ConditionResult:
    span, c_root, c_tip, _semi = wing_planform(layout)
    return ConditionResult(
        title="Wing planform (parametric -> WINGGEOM)",
        far_reference=_FAR,
        values=[
            LoadValue("Span", span, _IN, key="span"),
            LoadValue("Root chord", c_root, _IN, key="root_chord"),
            LoadValue("Tip chord", c_tip, _IN, key="tip_chord"),
            LoadValue("MAC", geom["MAC"], _IN, key="mac"),
            LoadValue("XLE(MAC) station of MAC LE", geom["XLE(MAC) station of MAC LE"], _IN,
                key="xle_mac_station_of_mac_le"),
            LoadValue("YLE(MAC) butt line of MAC", geom["YLE(MAC) butt line of MAC"], _IN,
                key="yle_mac_butt_line_of_mac"),
            LoadValue("Aspect ratio", geom["Aspect ratio"], key="aspect_ratio"),
        ],
        note="MAC/XLEMAC/AR via the WINGGEOM strip integrator on the generated polylines.",
    )


def _stability_condition(project: Project, layout: LayoutInput, geom: dict) -> Optional[ConditionResult]:
    """Tail-volume neutral point + static margin (Ref 1 Ch 8 first-cut).

    Reads the h-tail area and 25%-MAC station from the Step-G6 single-source
    ``geometry.empennage.htail``; the tail arm is derived as ``xt25`` minus the 25%
    wing-MAC station (``XLEMAC + 0.25*MAC``), so it is not stored twice.
    """
    emp = project.geometry.empennage if project.geometry is not None else None
    ht = emp.htail if emp is not None else None
    mac = geom["MAC"]
    xlemac = geom["XLE(MAC) station of MAC LE"]
    if ht is None or ht.htail_area_sqft <= 0 or layout.wing_area_sqft <= 0 or mac <= 0:
        return None
    h_arm = ht.xt25 - (xlemac + 0.25 * mac)
    if h_arm <= 0:
        return None
    v_h = (ht.htail_area_sqft * h_arm) / (layout.wing_area_sqft * mac)
    h_n = _H_AC_WING + v_h * _LIFT_SLOPE_RATIO * _DOWNWASH_FACTOR
    np_station = xlemac + h_n * mac

    values = [
        LoadValue("Horizontal tail volume V_H", v_h, key="horizontal_tail_volume_v_h"),
        LoadValue("Neutral point (%MAC)", h_n * 100.0, "%MAC", key="neutral_point_pct_mac"),
        LoadValue("Neutral point station", np_station, _IN, key="neutral_point_station"),
    ]
    note = (
        "Tail-volume estimate (h_acw=0.25, a_t/a_w=1.0, 1-dε/dα=0.6); "
        "first-order, no oracle."
    )

    # Static margin needs a CG; use the aft-gross %MAC limit from WTENV when present
    # (the critical aft CG). Reported as an estimate; left out if no CG is known.
    env = project.weight.envelope if project.weight is not None else None
    if env is not None and env.aft_gross_pct_mac:
        h_cg = env.aft_gross_pct_mac / 100.0
        values.append(LoadValue("CG (%MAC, aft-gross limit)", env.aft_gross_pct_mac, "%MAC",
            key="cg_pct_mac_aft_gross_limit"))
        values.append(LoadValue("Static margin (%MAC)", (h_n - h_cg) * 100.0, "%MAC", key="static_margin_pct_mac"))
    else:
        note += " Static margin needs a CG (WTENV aft-gross %MAC) -- not in project."

    return ConditionResult(title="Longitudinal stability (estimate)", far_reference=_FAR,
                           values=values, note=note)


def cg_estimate(project: Project, layout: LayoutInput,
                mac: float, xlemac: float) -> Tuple[float, float, str]:
    """The best available CG station/waterline, and a short label for its source.

    True CG (Step D4.5): when ``Project.mass`` is populated (WTONECG has run on
    the itemized Weight DB), use its weight-averaged station -- the same
    ``(cg_x, cg_z)`` SELECT/FLTLOADS/LANDLOAD read. ``Project.mass.cases`` is
    currently always a single "itemized loading" case (`weight_onecg.build_mass`
    -- the four structural-limit loadings x gear up/down is a later
    refinement); once that lands this should pick the representative case
    rather than always the first.

    Falls back to the 25%-MAC / wing-reference-waterline first cut (the only
    option before a mass slice exists) -- geometric estimates, not certified
    figures. Callers surface the returned source label so the UI/report make
    clear which one is in play.

    Takes ``mac``/``xlemac`` as plain numbers rather than the geometry dict it
    used to index by label. The caller inside this module passes
    ``_wing_geometry``'s dict entries; the Configuration page passed its
    *LoadValue* table, which worked only because the two dicts happened to spell
    "MAC" the same way -- a coincidence M4-9 broke and this signature removes.
    """
    if project.mass is not None and project.mass.cases:
        case = project.mass.cases[0]
        return case.cg_x, case.cg_z, "Weight DB"
    return xlemac + 0.25 * mac, layout.root_waterline_z, "25% MAC estimate"


def _gear_condition(project: Project, layout: LayoutInput, geom: dict) -> Optional[ConditionResult]:
    """Tip-back / overturn angles + prop clearance from the gear geometry.

    The CG (:func:`cg_estimate`) is the true weight-averaged station from
    ``Project.mass`` when available (Step D4.5), else the 25%-MAC / wing-
    reference-waterline first cut -- so the tip-back/overturn angles (the
    tail-ground-clearance-relevant figures here) sharpen automatically once a
    mass slice exists, with no separate refinement needed. Prop clearance does
    not depend on the CG (it only needs the engine/gear geometry), so it is
    unaffected either way.
    """
    gc = gear_stations(layout, project.geometry.landing_gear if project.geometry is not None else None)
    if gc is None or gc["main_x"] <= 0 or gc["gear_height"] <= 0:
        return None
    x_cg, z_cg, cg_source = cg_estimate(
        project, layout, geom["MAC"], geom["XLE(MAC) station of MAC LE"])
    ground_z = gc["ground_z"]
    h_cg = z_cg - ground_z              # CG height above ground

    values: List[LoadValue] = []

    # Tip-back: angle of the main-wheel -> CG line from the vertical. CG forward of
    # the main gear (positive) is required; ~15 deg is the usual minimum.
    tipback = math.degrees(math.atan2(gc["main_x"] - x_cg, h_cg))
    values.append(LoadValue(f"CG station ({cg_source})", x_cg, _IN, key="cg_station"))
    values.append(LoadValue("Tip-back angle", tipback, _DEG, key="tip_back_angle"))

    # Overturn (turnover) angle: from the CG to the nose-wheel / main-wheel ground
    # line. Lower is more stable; ~63 deg is the usual maximum.
    if gc["nose_x"] and gc["track"]:
        xn, xm, half = gc["nose_x"], gc["main_x"], gc["track"] / 2.0
        # Perpendicular distance (plan view) from the CG (on the centreline) to the
        # nose-wheel -> main-wheel line.
        dx, dy = xm - xn, half - 0.0
        seg = math.hypot(dx, dy)
        d = abs(dx * (0.0 - 0.0) - dy * (x_cg - xn)) / seg  # |cross| / |seg|
        overturn = math.degrees(math.atan2(h_cg, d))
        values.append(LoadValue("Overturn (turnover) angle", overturn, _DEG, key="overturn_turnover_angle"))

    # Prop ground clearance: nose engine prop tip vs ground (needs engine + prop).
    eng = project.engine
    if eng is not None and eng.prop_diameter_in:
        prop_tip_z = eng.prop_cg[2] - eng.prop_diameter_in / 2.0
        values.append(LoadValue("Prop ground clearance", prop_tip_z - ground_z, _IN, key="prop_ground_clearance"))

    note = (
        f"CG from the {cg_source}"
        + ("." if cg_source == "Weight DB" else " (no mass slice present).")
        + " Tip-back >= ~15 deg, overturn <= ~63 deg."
    )
    return ConditionResult(
        title="Landing-gear geometry (estimate)", far_reference=_FAR, values=values, note=note,
    )


def configuration_properties(project: Project) -> List[ConditionResult]:
    """All configuration/layout derived quantities for a :class:`Project`."""
    layout = project.geometry.parametric if project.geometry is not None else None
    if layout is None:
        raise MissingInputError("Project has no 'geometry.parametric' slice for the configuration module")
    geom = _wing_geometry(layout)
    results = [_planform_condition(layout, geom)]
    for cond in (_stability_condition(project, layout, geom),
                 _gear_condition(project, layout, geom)):
        if cond is not None:
            results.append(cond)
    if project.is_concept:
        results[0].note += " Concept mode: results are unverified extrapolation."
    return results


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "configuration"


def run(project: Project) -> ModuleResult:
    """Run the configuration/layout derivation against a :class:`Project`."""
    return ModuleResult(module=MODULE_NAME, conditions=configuration_properties(project))


register(MODULE_NAME, run)
