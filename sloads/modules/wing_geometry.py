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

from typing import List, Optional, Sequence, Tuple

from ..derived_geometry import (
    planform_aspect_ratio,
    require_integrable_planform,
    require_positive_planform_area,
)
from ..models import (
    ConditionResult,
    GeometryInput,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    SurfaceInput,
)
from ..registry import register

_FAR = "geometry"  # geometry basis for the 23.301+ airload conditions
_IN = "in"
_IN2 = "in^2"

Point = Tuple[float, float]


def surface_top_outline(
    leading_edge: Sequence[Point], trailing_edge: Sequence[Point], symmetric: bool = True,
) -> List[Tuple[List[float], List[float]]]:
    """Closed-polygon (x, y) outline(s) for a top-view surface plot.

    A presentation helper (not a load/geometry calc), shared by the Configuration
    & Layout three-view and the Wing/Surface Geometry planform plot so the two
    GUI pages don't duplicate the same "polyline -> plotly-ready outline" math.

    Builds one closed outline from ``leading_edge`` + reversed ``trailing_edge``
    (inboard -> outboard -> back to start); when ``symmetric``, returns that
    outline plus its mirror image about the centreline (``y -> -y``), matching
    how a symmetric lifting surface (wing/tail) is entered as one half.

    Returns a list of ``(xs, ys)`` point-list pairs -- one entry, or two when
    ``symmetric`` -- ready for ``fig.add_scatter(x=xs, y=ys, mode="lines")``.
    """
    if not leading_edge or not trailing_edge:
        return []
    le_x = [p[0] for p in leading_edge]
    le_y = [p[1] for p in leading_edge]
    te_x = [p[0] for p in trailing_edge]
    te_y = [p[1] for p in trailing_edge]
    xs = le_x + te_x[::-1] + [le_x[0]]
    ys = le_y + te_y[::-1] + [le_y[0]]
    if not symmetric:
        return [(xs, ys)]
    return [(xs, list(ys)), (xs, [-v for v in ys])]


def interp_x(polyline: List, y: float) -> float:
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


def planform_boundary(leading_edge: Sequence, trailing_edge: Sequence):
    """The closed planform's ``(left, right, zmin, zmax, breaks)``.

    The surface is the **closed polygon** its two edges bound: leading edge, tip
    chord across to the trailing edge's outboard point, trailing edge, then a
    root chord back to the leading edge's inboard point (owner, 2026-08-30).
    Where the two polylines cover the same span -- every surface shipped before
    the GA6 empennage went in -- the closing chords are degenerate and this
    reduces exactly to ``chord = X_TE - X_LE``.

    Where they do not, the closing chords are the boundary. The GA6 vertical
    tail is the case: its leading edge starts at waterline 117.0 and its
    trailing edge at 111.5, so between those the forward boundary is the root
    chord rather than the leading edge extrapolated. Extrapolating instead
    over-reads the area by 8 %; closing the polygon reproduces the manual's own
    figures to 0.08 %.
    """
    le, te = list(leading_edge), list(trailing_edge)
    le_lo, le_hi = le[0][1], le[-1][1]
    te_lo, te_hi = te[0][1], te[-1][1]
    zmin, zmax = min(le_lo, te_lo), max(le_hi, te_hi)

    def seg_x(a, b, z):
        (x0, z0), (x1, z1) = a, b
        return x0 if z1 == z0 else x0 + (x1 - x0) * (z - z0) / (z1 - z0)

    def left(z):
        if z < le_lo:
            return seg_x(le[0], te[0], z)      # root chord
        if z > le_hi:
            return seg_x(le[-1], te[-1], z)    # tip chord
        return interp_x(le, z)

    def right(z):
        if z < te_lo:
            return seg_x(le[0], te[0], z)
        if z > te_hi:
            return seg_x(le[-1], te[-1], z)
        return interp_x(te, z)

    breaks = sorted({z for _x, z in le} | {z for _x, z in te} | {zmin, zmax})
    return left, right, zmin, zmax, [z for z in breaks if zmin <= z <= zmax]


def surface_properties(surf: SurfaceInput) -> ConditionResult:
    """Geometric properties of one aerodynamic surface (WINGGEOM core).

    **The integrals are closed-form, not a strip sum** (owner, 2026-08-30). Both
    edges are piecewise linear, so on each interval between their breakpoints the
    chord is linear and every integral WINGGEOM forms has an exact value; summing
    those is the strip sum's limit with none of its discretisation error. The
    manual's own ``H`` was a convergence parameter it never printed, and matching
    it was guesswork: the GA6 empennage read 0.2-1.0 % off at ``elements=20`` and
    the aileron test had been loosened to +/-2 % for exactly this reason. Exact
    integration puts every Appendix A surface within 0.084 %.

    ``elements`` therefore no longer drives this calculation. It stays what plan
    09 T-1 calls it -- the user's spanwise **load-station** count -- and is
    reported here so a reader can still see it.
    """
    require_integrable_planform(surf)   # the shared precondition (#71)

    left, right, zroot, ztip, breaks = planform_boundary(
        surf.leading_edge, surf.trailing_edge)
    area = sc2 = saye = sbarxc = 0.0
    for a, b in zip(breaks, breaks[1:]):
        length = b - a
        if length <= 0.0:
            continue
        c0, c1 = right(a) - left(a), right(b) - left(b)
        m0, m1 = (left(a) + right(a)) / 2.0, (left(b) + right(b)) / 2.0
        area += length * (c0 + c1) / 2.0
        sc2 += length * (c0 * c0 + c0 * c1 + c1 * c1) / 3.0
        saye += length * (a * (c0 + c1) / 2.0 + length * (c0 / 6.0 + c1 / 3.0))
        sbarxc += length * (2 * c0 * m0 + c0 * m1 + c1 * m0 + 2 * c1 * m1) / 6.0

    # The post-sweep half of the same precondition (#71): every line below
    # divides by `area`, and `_NOT_READY` deliberately does not catch
    # `ZeroDivisionError` (0.7.2), so a coincident-edge planform reached the
    # page as a traceback.
    require_positive_planform_area(surf.name, area)
    xbar = sbarxc / area
    ybar = saye / area
    mac = sc2 / area
    xlemac = xbar - mac / 2

    # AR from the one spelling (note 36, OV-5); span/area stay local.
    aspect_ratio = planform_aspect_ratio(zroot, ztip, area, surf.symmetric)
    if surf.symmetric:
        span = 2 * ztip
        total_area = 2 * area
    else:
        span = ztip - zroot
        total_area = area

    return ConditionResult(
        title=f"Aerodynamic surface geometry: {surf.name}",
        far_reference=_FAR,
        values=[
            LoadValue("Area per side", area, _IN2, key="area_per_side"),
            LoadValue("Total area", total_area, _IN2, key="total_area"),
            LoadValue("MAC", mac, _IN, key="mac"),
            LoadValue("YLE(MAC) butt line of MAC", ybar, _IN, key="yle_mac_butt_line_of_mac"),
            LoadValue("XLE(MAC) station of MAC LE", xlemac, _IN, key="xle_mac_station_of_mac_le"),
            LoadValue("Aspect ratio", aspect_ratio, key="aspect_ratio"),
            LoadValue("Span", span, _IN, key="span"),
            LoadValue("Integration elements", surf.elements, key="integration_elements"),
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
    problem = project.engine_layout_problem()
    if problem:
        raise ValueError(problem)

    values: List[LoadValue] = []
    from .engine import resolved_engines
    for i, eng in enumerate(resolved_engines(project), start=1):
        y = eng.engine_cg[1]
        xf = interp_x(wing.leading_edge, abs(y))
        xa = interp_x(wing.trailing_edge, abs(y))
        # The label names the engine; the key is its index in project.engines.
        values.append(LoadValue(f"Engine {i} ({eng.engine_designation or '?'}) butt line Y",
                                y, _IN, key=f"engine_{i}_butt_line_y"))
        values.append(LoadValue(f"Engine {i} local wing chord", xa - xf, _IN,
                                key=f"engine_{i}_local_wing_chord"))
    return ConditionResult(
        title="Wing-mounted engine spanwise stations",
        far_reference=_FAR,
        values=values,
        note=f"Engine layout {layout.value}; chord interpolated at each engine butt line.",
    )


def geometry_properties(geometry: GeometryInput, project: Optional[Project] = None) -> List[ConditionResult]:
    """Geometric properties for every surface, plus engine stations if applicable."""
    if not geometry.surfaces:
        raise MissingInputError("WINGGEOM needs at least one surface")
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
        raise MissingInputError("Project has no 'geometry' surfaces for the wing_geometry module")
    return ModuleResult(module=MODULE_NAME, conditions=geometry_properties(project.geometry, project))


register(MODULE_NAME, run)

# --------------------------------------------------------------------------- #
# Public surface (M4-12b). Names not listed here are module-private: an
# underscore-free name outside this list is still not an import contract, and
# ``app/`` must import nothing underscored from ``sloads``.
# --------------------------------------------------------------------------- #
__all__ = [
    "MODULE_NAME",
    "geometry_properties",
    "interp_x",
    "run",
    "surface_properties",
    "surface_top_outline",
]
