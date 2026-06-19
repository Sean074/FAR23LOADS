"""Aerodynamic surface geometry, ported from WINGGEOM.BAS (Hal C. McMaster).

WINGGEOM computes the geometric properties -- area, mean aerodynamic (geometric)
chord MAC, the butt line and fuselage station of the leading edge of the MAC,
aspect ratio and span -- for every aerodynamic surface (wing, tails, ailerons,
flaps, elevators, rudders and their tabs). The wing's ``XLEMAC``/``MAC`` seed the
weight-envelope (WTENV) and structural-speed (STRSPEED) modules; the per-surface
tables feed the air-load and flight-load modules downstream (Reference 1 Ch 5).

Method (WINGGEOM.BAS lines 510-940, verified against the Appendix A wing element
table p141): the span is divided into ``H`` strips of width ``DY``; the chord
``C = X_TE - X_LE`` is interpolated from the edge polylines at each strip's
mid-station ``YE`` and summed:

    A     = SUM(C*DY)                  area on one side of the plane of symmetry
    MAC   = SUM(C^2*DY) / A            mean aerodynamic (geometric) chord
    YBAR  = SUM(YE*C*DY) / A           butt line of the MAC
    XBAR  = SUM(((X_LE+X_TE)/2)*C*DY)/A fuselage station of the mid-MAC
    XLEMAC = XBAR - MAC/2              fuselage station of the MAC leading edge
    AR    = (2*Ytip)^2 / (2*A)         symmetric surfaces (span = 2*Ytip)
          = (Ytip - Yroot)^2 / A       single-side surfaces (span = Ytip - Yroot)

Because the manual's printed figures are themselves this strip sum, ``elements``
must match the value the manual used (20 for the Appendix A wing) to reproduce
them; see the per-surface ``elements`` field.

Reference: WINGGEOM.BAS, Appendix C (embedded geometry subroutine p409-410);
worked example Appendix A p141 (wing: MAC 69.246, XLEMAC 63.641, AR 6.095).
"""

from __future__ import annotations

from typing import List, Optional

from ..models import (
    ConditionResult,
    GeometryInput,
    LoadValue,
    ModuleResult,
    Project,
    SurfaceInput,
)
from ..registry import register

_FAR = "geometry"  # geometry basis for the 23.301+ airload conditions
_IN = "in"
_IN2 = "in^2"


def _interp_x(polyline: List, y: float) -> float:
    """Fuselage station X on an edge polyline at butt line ``y``.

    Piecewise-linear between the defining points, ordered inboard -> outboard
    (WINGGEOM.BAS lines 600-730). A two-point edge is a single straight segment;
    outside the defined range the nearest segment is extrapolated.
    """
    pts = polyline
    if len(pts) == 2:
        (x0, y0), (x1, y1) = pts
        return (x1 - x0) * (y - y0) / (y1 - y0) + x0
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        if y0 <= y <= y1:
            return (x1 - x0) * (y - y0) / (y1 - y0) + x0
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    return (x1 - x0) * (y - y0) / (y1 - y0) + x0


def surface_properties(surf: SurfaceInput) -> ConditionResult:
    """Geometric properties of one aerodynamic surface (WINGGEOM core)."""
    if surf.elements < 2:
        raise ValueError(f"surface '{surf.name}' needs >= 2 integration elements")
    if len(surf.leading_edge) < 2 or len(surf.trailing_edge) < 2:
        raise ValueError(f"surface '{surf.name}' needs >= 2 LE and TE points")

    yroot = surf.leading_edge[0][1]
    ytip = surf.leading_edge[-1][1]
    h = surf.elements
    dy = (ytip - yroot) / h

    area = sc2 = saye = sbarxc = 0.0
    for el in range(h):
        ye = yroot + dy / 2 + el * dy
        xf = _interp_x(surf.leading_edge, ye)   # leading edge (front)
        xa = _interp_x(surf.trailing_edge, ye)  # trailing edge (aft)
        chord = xa - xf
        da = chord * dy
        area += da
        sc2 += chord * chord * dy
        saye += da * ye
        sbarxc += da * (xf + xa) / 2

    xbar = sbarxc / area
    ybar = saye / area
    mac = sc2 / area
    xlemac = xbar - mac / 2

    if surf.symmetric:
        aspect_ratio = (2 * ytip) ** 2 / (2 * area)
        span = 2 * ytip
        total_area = 2 * area
    else:
        aspect_ratio = (ytip - yroot) ** 2 / area
        span = ytip - yroot
        total_area = area

    return ConditionResult(
        title=f"Aerodynamic surface geometry: {surf.name}",
        far_reference=_FAR,
        values=[
            LoadValue("Area per side", area, _IN2),
            LoadValue("Total area", total_area, _IN2),
            LoadValue("MAC", mac, _IN),
            LoadValue("YLE(MAC) butt line of MAC", ybar, _IN),
            LoadValue("XLE(MAC) station of MAC LE", xlemac, _IN),
            LoadValue("Aspect ratio", aspect_ratio),
            LoadValue("Span", span, _IN),
            LoadValue("Integration elements", h),
        ],
        note="Symmetric about airplane CL" if surf.symmetric else "Single side (not symmetric about CL)",
    )


def _engine_stations(project: Project, geometry: GeometryInput) -> Optional[ConditionResult]:
    """Engine butt-line stations on the wing for wing-mounted layouts.

    Reports each engine's butt line ``Y`` and the local wing chord there, so the
    one-engine-out and wing-inertia modules (later phases) can read the engine
    positions from the geometry slice. Returns ``None`` unless the layout is
    wing-mounted and a ``wing`` surface is present.
    """
    layout = project.engine_layout
    if layout is None or not layout.is_wing_mounted:
        return None
    wing = geometry.by_name("wing")
    if wing is None or not project.engines:
        return None

    values: List[LoadValue] = []
    for i, eng in enumerate(project.engines, start=1):
        y = eng.engine_cg[1]
        xf = _interp_x(wing.leading_edge, abs(y))
        xa = _interp_x(wing.trailing_edge, abs(y))
        values.append(LoadValue(f"Engine {i} ({eng.engine_designation or '?'}) butt line Y", y, _IN))
        values.append(LoadValue(f"Engine {i} local wing chord", xa - xf, _IN))
    return ConditionResult(
        title="Wing-mounted engine spanwise stations",
        far_reference=_FAR,
        values=values,
        note=f"Engine layout {layout.value}; chord interpolated at each engine butt line.",
    )


def geometry_properties(geometry: GeometryInput, project: Optional[Project] = None) -> List[ConditionResult]:
    """Geometric properties for every surface, plus engine stations if applicable."""
    if not geometry.surfaces:
        raise ValueError("WINGGEOM needs at least one surface")
    results = [surface_properties(s) for s in geometry.surfaces]
    if project is not None:
        engines = _engine_stations(project, geometry)
        if engines is not None:
            results.append(engines)
    return results


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "wing_geometry"


def run(project: Project) -> ModuleResult:
    """Run WINGGEOM against a :class:`Project`'s ``geometry`` surfaces."""
    if project.geometry is None or not project.geometry.surfaces:
        raise ValueError("Project has no 'geometry' surfaces for the wing_geometry module")
    return ModuleResult(module=MODULE_NAME, conditions=geometry_properties(project.geometry, project))


register(MODULE_NAME, run)
