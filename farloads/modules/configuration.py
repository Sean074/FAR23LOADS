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
(:func:`farloads.modules.wing_geometry.surface_properties`), not by an
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
from typing import List, Optional, Tuple

from ..constants import IN2_PER_FT2
from ..models import (
    ConditionResult,
    LayoutInput,
    LoadValue,
    ModuleResult,
    Project,
    SurfaceInput,
)
from ..registry import register
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


def _wing_geometry(layout: LayoutInput) -> dict:
    """Wing MAC/XLEMAC/Y_MAC/AR/span via the WINGGEOM strip integrator.

    Reads them straight out of :func:`wing_geometry.surface_properties` so
    WINGGEOM stays the single owner of the integration.
    """
    result = surface_properties(wing_surface(layout))
    return {v.label: v.value for v in result.values}


def _planform_condition(layout: LayoutInput, geom: dict) -> ConditionResult:
    span, c_root, c_tip, _semi = wing_planform(layout)
    return ConditionResult(
        title="Wing planform (parametric -> WINGGEOM)",
        far_reference=_FAR,
        values=[
            LoadValue("Span", span, _IN),
            LoadValue("Root chord", c_root, _IN),
            LoadValue("Tip chord", c_tip, _IN),
            LoadValue("MAC", geom["MAC"], _IN),
            LoadValue("XLE(MAC) station of MAC LE", geom["XLE(MAC) station of MAC LE"], _IN),
            LoadValue("YLE(MAC) butt line of MAC", geom["YLE(MAC) butt line of MAC"], _IN),
            LoadValue("Aspect ratio", geom["Aspect ratio"]),
        ],
        note="MAC/XLEMAC/AR via the WINGGEOM strip integrator on the generated polylines.",
    )


def _stability_condition(project: Project, layout: LayoutInput, geom: dict) -> Optional[ConditionResult]:
    """Tail-volume neutral point + static margin (Ref 1 Ch 8 first-cut)."""
    if layout.h_tail_area <= 0 or layout.h_tail_arm <= 0:
        return None
    mac = geom["MAC"]
    xlemac = geom["XLE(MAC) station of MAC LE"]
    v_h = (layout.h_tail_area * layout.h_tail_arm) / (layout.wing_area_sqft * mac)
    h_n = _H_AC_WING + v_h * _LIFT_SLOPE_RATIO * _DOWNWASH_FACTOR
    np_station = xlemac + h_n * mac

    values = [
        LoadValue("Horizontal tail volume V_H", v_h),
        LoadValue("Neutral point (%MAC)", h_n * 100.0, "%MAC"),
        LoadValue("Neutral point station", np_station, _IN),
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
        values.append(LoadValue("CG (%MAC, aft-gross limit)", env.aft_gross_pct_mac, "%MAC"))
        values.append(LoadValue("Static margin (%MAC)", (h_n - h_cg) * 100.0, "%MAC"))
    else:
        note += " Static margin needs a CG (WTENV aft-gross %MAC) -- not in project."

    return ConditionResult(title="Longitudinal stability (estimate)", far_reference=_FAR,
                           values=values, note=note)


def _gear_condition(project: Project, layout: LayoutInput, geom: dict) -> Optional[ConditionResult]:
    """Tip-back / overturn angles + prop clearance from the gear geometry.

    The CG is taken at 25% MAC (station from WINGGEOM) and at the wing-reference
    waterline -- a documented first-cut when no mass slice is available -- so the
    angles are geometric estimates, not certified figures.
    """
    if layout.main_gear_x <= 0 or layout.gear_height <= 0:
        return None
    mac = geom["MAC"]
    xlemac = geom["XLE(MAC) station of MAC LE"]
    x_cg = xlemac + 0.25 * mac          # CG x ~ 25% MAC (first cut)
    h_cg = layout.gear_height           # CG height above ground ~ WRP height
    ground_z = layout.root_waterline_z - layout.gear_height

    values: List[LoadValue] = []

    # Tip-back: angle of the main-wheel -> CG line from the vertical. CG forward of
    # the main gear (positive) is required; ~15 deg is the usual minimum.
    tipback = math.degrees(math.atan2(layout.main_gear_x - x_cg, h_cg))
    values.append(LoadValue("CG station (25% MAC est.)", x_cg, _IN))
    values.append(LoadValue("Tip-back angle", tipback, _DEG))

    # Overturn (turnover) angle: from the CG to the nose-wheel / main-wheel ground
    # line. Lower is more stable; ~63 deg is the usual maximum.
    if layout.nose_gear_x and layout.track:
        xn, xm, half = layout.nose_gear_x, layout.main_gear_x, layout.track / 2.0
        # Perpendicular distance (plan view) from the CG (on the centreline) to the
        # nose-wheel -> main-wheel line.
        dx, dy = xm - xn, half - 0.0
        seg = math.hypot(dx, dy)
        d = abs(dx * (0.0 - 0.0) - dy * (x_cg - xn)) / seg  # |cross| / |seg|
        overturn = math.degrees(math.atan2(h_cg, d))
        values.append(LoadValue("Overturn (turnover) angle", overturn, _DEG))

    # Prop ground clearance: nose engine prop tip vs ground (needs engine + prop).
    eng = project.engine
    if eng is not None and eng.prop_diameter_in:
        prop_tip_z = eng.prop_cg[2] - eng.prop_diameter_in / 2.0
        values.append(LoadValue("Prop ground clearance", prop_tip_z - ground_z, _IN))

    return ConditionResult(
        title="Landing-gear geometry (estimate)", far_reference=_FAR, values=values,
        note="CG at 25% MAC / WRP waterline (first cut). Tip-back >= ~15 deg, overturn <= ~63 deg.",
    )


def configuration_properties(project: Project) -> List[ConditionResult]:
    """All configuration/layout derived quantities for a :class:`Project`."""
    layout = project.configuration
    if layout is None:
        raise ValueError("Project has no 'configuration' slice for the configuration module")
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
