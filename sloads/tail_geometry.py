"""The empennage planform the spanwise strip integrator runs on (plan 09 T1).

Design note: ``docs/30_future/09_distributed_empennage_loads_plan.md`` decisions
**T-1** (reuse ``SurfaceInput``) and **T-8** (full-span h-tail bookkeeping).
Conventions: ``docs/10_standard/CONVENTIONS.md`` §1 (axes), §7 (single-source
owners).

Two representations of the same surface
---------------------------------------
The empennage has carried its geometry as **scalars** since the suite was ported
-- ``htail_area_sqft``/``htail_semispan_in`` on :class:`TailLoadsInput`,
``vtail_area_sqft``/``vtail_span_in`` on :class:`VTailLoadsInput` -- because that
is all SELECT, TAILDIST and BALLOADS ever needed. Those scalars are
**oracle-authoritative** and this module never overrides them.

A spanwise distribution needs more: a chord at every station. Decision T-1 gets
it by reusing the wing's ``SurfaceInput`` -- an ``"htail"`` / ``"vtail"`` entry in
``geometry.surfaces``, with the same LE/TE polylines, the same user-set
``elements`` station count and the same ``ref_axis_pct`` loads reference axis.
Where such an entry exists it is authoritative **for strips**, and the 1 %
validator below is the drift guard that keeps the two representations describing
one airplane.

The derived planform, and why it is marked rather than hidden
--------------------------------------------------------------
No shipped fixture carries tail polylines, and requiring them would mean
hand-entering planform data for six airplanes with no oracle to check it
against. So where the entry is absent this module **derives** a rectangular
planform from the authoritative scalars -- constant chord ``S/b``, leading edge
a quarter-chord ahead of the 25 %-MAC station -- which is precisely the
first-order derivation ``configuration.tail_planform`` has always used for the
three-view, and which that function's own docstring is careful to call "not a
structural surface definition".

It is not one here either, and the result says so: every derived planform sets
``assumed=True``, which travels into :class:`TailSpanResult`, the page, the CSV
and the deck ``$`` header. This is the established pattern for a value the tool
had to supply rather than read (``body_loads``' ``spars_assumed``,
``wing_geometry``'s assumed spar fractions) -- a first-order answer, delivered,
and never reported as input.

**What "assumed" costs, quantitatively.** The bending closure integrates the
half-planform area centroid, ``ybar = (b/3)(c_r + 2c_t)/(c_r + c_t)``: ``b/2``
for the rectangle assumed here, falling to ``b/3`` for a fully-tapered surface.
A real tapered tail therefore carries its load further inboard than this
assumption, so a derived planform is **conservative in root bending** -- but the
station-by-station distribution it delivers is not the surface's own. Enter the
polylines when the tail geometry is known.

Half and full, stated once (plan 09 §3.1)
------------------------------------------
``SurfaceInput`` polylines are defined on **one side** of a ``symmetric=True``
surface. The horizontal tail is symmetric, so ``2 x polyline_area`` compares
against ``htail_area_sqft`` and ``polyline_semispan`` against
``htail_semispan_in``. The vertical tail is a single surface: ``polyline_area``
compares against ``vtail_area_sqft`` and ``polyline_span`` against
``vtail_span_in``, with no factor anywhere. Getting this backwards is a factor of
two in every strip, which is why it is written down once, here, and used from
here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .models import GeometryInput, Project, SurfaceInput, TailType

#: Component names, which are also the ``geometry.surfaces`` entry names (T-1).
HTAIL = "htail"
VTAIL = "vtail"
TAIL_COMPONENTS = (HTAIL, VTAIL)

#: Fractional agreement required between an entered planform and the
#: oracle-authoritative scalars (plan 09 §3.1). Loud, not a silent preference:
#: two representations of one surface that disagree by more than this are a data
#: defect, and every downstream number would be quietly wrong by that much.
PLANFORM_TOLERANCE = 0.01

_SQIN_PER_SQFT = 144.0


@dataclass
class TailPlanform:
    """The resolved planform of one empennage surface, in its **local** frame.

    ``span`` runs from the surface root (``0``) outboard; for the horizontal tail
    that is the semispan (the full-span station set is built by mirroring, T-8)
    and for the vertical tail the whole fin. ``le``/``te`` are ``(x, s)`` polyline
    points -- chordwise station against span coordinate -- so a single strip
    integrator serves both surfaces and the local->airplane mapping stays in
    ``export/coordinates.py`` where it has one owner.

    ``area`` is the **whole surface** (both sides for the h-tail), matching every
    other tail quantity in the suite. ``assumed`` records that the planform was
    derived from the scalars rather than entered.
    """

    component: str
    le: List[Tuple[float, float]]
    te: List[Tuple[float, float]]
    span: float                     # semispan (htail) / full fin span (vtail), in
    area: float                     # whole surface, in^2
    elements: int = 10
    ref_axis_pct: float = 0.25
    assumed: bool = False
    root_z: float = 0.0             # v-tail only: waterline of the fin root
    notes: List[str] = field(default_factory=list)

    @property
    def symmetric(self) -> bool:
        """True for the h-tail: the local semispan planform mirrors to full span."""
        return self.component == HTAIL

    def chord(self, s: float) -> float:
        """Local chord at span station ``s`` (in), by linear interpolation."""
        return _interp(self.te, s) - _interp(self.le, s)

    def x_le(self, s: float) -> float:
        return _interp(self.le, s)

    def x_at(self, s: float, pct: float) -> float:
        """Chordwise station of ``pct`` of the local chord at span ``s``."""
        return self.x_le(s) + pct * self.chord(s)


def _interp(points: List[Tuple[float, float]], s: float) -> float:
    """Chordwise ``x`` at span ``s`` on a polyline of ``(x, span)`` points.

    Clamped outside the defined range rather than extrapolated: a strip centroid
    can land a rounding step outside the last point, and extrapolating a chord
    there would produce a silently wrong (possibly negative) strip.
    """
    if len(points) == 1:
        return points[0][0]
    if s <= points[0][1]:
        return points[0][0]
    for (x0, s0), (x1, s1) in zip(points, points[1:]):
        if s <= s1:
            if s1 == s0:
                return x1
            return x0 + (x1 - x0) * (s - s0) / (s1 - s0)
    return points[-1][0]


# --------------------------------------------------------------------------- #
# Validation -- the drift guard between the two representations
# --------------------------------------------------------------------------- #
def _polyline_area_and_span(surf: SurfaceInput) -> Tuple[float, float]:
    """``(area_one_side_in2, span_in)`` of an entered planform.

    Integrated the same way ``wing_geometry.surface_properties`` does -- strip
    midpoints over ``elements`` -- so an entered tail and an entered wing are
    measured by one rule.
    """
    s_root = surf.leading_edge[0][1]
    s_tip = surf.leading_edge[-1][1]
    h = max(1, surf.elements)
    ds = (s_tip - s_root) / h
    area = 0.0
    for el in range(h):
        s = s_root + ds / 2 + el * ds
        area += (_interp(surf.trailing_edge, s) - _interp(surf.leading_edge, s)) * ds
    return area, s_tip - s_root


def validate_tail_planform(surf: SurfaceInput, component: str,
                           area_sqft: float, span_in: float) -> None:
    """Raise if an entered planform disagrees with the authoritative scalars.

    ``area_sqft``/``span_in`` are the surface's scalar values: ``htail_area_sqft``
    with ``htail_semispan_in``, or ``vtail_area_sqft`` with ``vtail_span_in``.
    The half/full bookkeeping is applied here and nowhere else (§3.1): the h-tail
    doubles its one-sided polyline area and compares span as a **semispan**; the
    v-tail compares both directly.

    Loud, per T-1: silently preferring one representation would leave the whole
    tail path -- chordwise pressures from the scalars, spanwise strips from the
    polylines -- describing two different airplanes.
    """
    if area_sqft <= 0 or span_in <= 0:
        return
    poly_area, poly_span = _polyline_area_and_span(surf)
    want_area = area_sqft * _SQIN_PER_SQFT
    got_area = 2.0 * poly_area if component == HTAIL else poly_area
    for what, got, want in (("area", got_area, want_area),
                            ("span", poly_span, span_in)):
        if want and abs(got - want) / abs(want) > PLANFORM_TOLERANCE:
            raise ValueError(
                f"{component} planform disagrees with its scalar geometry: "
                f"{what} {got:.1f} from the geometry.surfaces polyline against "
                f"{want:.1f} from "
                f"{'htail_area_sqft/htail_semispan_in' if component == HTAIL else 'vtail_area_sqft/vtail_span_in'}"
                f" ({abs(got - want) / abs(want) * 100:.1f} % apart, limit "
                f"{PLANFORM_TOLERANCE * 100:.0f} %). The scalars are "
                "oracle-authoritative; correct the polyline or the scalar, do not "
                "leave the surface described twice, differently."
            )


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #
def _scalars(project: Project, component: str) -> Optional[Tuple[float, float, float]]:
    """``(area_sqft, span_in, x25)`` from the oracle-authoritative scalar slice.

    ``span_in`` is the **semispan** for the h-tail and the full span for the
    v-tail, i.e. exactly the local span each planform is defined over.
    """
    if component == HTAIL:
        ti = project.tail_loads
        if ti is None or ti.htail_area_sqft <= 0 or ti.htail_semispan_in <= 0:
            return None
        return ti.htail_area_sqft, ti.htail_semispan_in, ti.xt25
    vt = project.vtail_loads
    if vt is None or vt.vtail_area_sqft <= 0 or vt.vtail_span_in <= 0:
        return None
    return vt.vtail_area_sqft, vt.vtail_span_in, vt.xv25


def _fin_root_z(geometry: Optional[GeometryInput]) -> float:
    """Waterline of the vertical-tail root: the top of the fuselage.

    The same reference ``configuration.tail_planform`` draws the fin from, so the
    three-view and the load deck put the fin in one place. Zero when there is no
    parametric layout -- the fin then sits on the centreline, which is wrong but
    is *stated* (the planform carries a note) rather than guessed at silently.
    """
    layout = geometry.parametric if geometry is not None else None
    if layout is None:
        return 0.0
    return layout.root_waterline_z + layout.fuselage_height / 2.0


def resolve_tail_planform(project: Project,
                          component: str) -> Optional[TailPlanform]:
    """The planform to run strips on, or ``None`` when the surface is not modelled.

    Entered polylines win and are validated; otherwise a rectangular planform is
    derived from the scalars and marked ``assumed``. See the module docstring for
    why the derivation exists and what it costs.
    """
    if component not in TAIL_COMPONENTS:
        raise ValueError(f"unknown tail component {component!r}; expected one of "
                         f"{TAIL_COMPONENTS}")
    scalars = _scalars(project, component)
    if scalars is None:
        return None
    area_sqft, span_in, x25 = scalars
    area_in2 = area_sqft * _SQIN_PER_SQFT
    geometry = project.geometry
    surf = geometry.by_name(component) if geometry is not None else None
    root_z = _fin_root_z(geometry) if component == VTAIL else 0.0

    if surf is not None:
        validate_tail_planform(surf, component, area_sqft, span_in)
        s_root = surf.leading_edge[0][1]
        return TailPlanform(
            component=component,
            le=[(x, s - s_root) for x, s in surf.leading_edge],
            te=[(x, s - s_root) for x, s in surf.trailing_edge],
            span=surf.leading_edge[-1][1] - s_root,
            area=area_in2,
            elements=surf.elements,
            ref_axis_pct=surf.ref_axis_pct,
            assumed=False,
            root_z=root_z,
        )

    # Derived: constant chord = S/b, LE a quarter chord ahead of the 25 % MAC
    # station. For the h-tail the local span is the semispan and the area is
    # both-sides, so the chord is S/(2*semispan) -- the full-span average chord,
    # which is exactly TAILDIST's CAVE.
    full_span = 2.0 * span_in if component == HTAIL else span_in
    chord = area_in2 / full_span
    x_le = x25 - 0.25 * chord
    notes = [
        f"{component} planform DERIVED as a rectangle (chord {chord:.2f} in) from "
        f"the area/span scalars -- no '{component}' entry in geometry.surfaces. "
        "First-order: a tapered surface carries its load further inboard, so root "
        "bending here is conservative but the station distribution is not the "
        "surface's own."
    ]
    if component == VTAIL and root_z == 0.0:
        notes.append(
            "vtail root waterline is 0 (no parametric fuselage) -- the fin is "
            "placed on the airplane centreline")
    return TailPlanform(
        component=component,
        le=[(x_le, 0.0), (x_le, span_in)],
        te=[(x_le + chord, 0.0), (x_le + chord, span_in)],
        span=span_in,
        area=area_in2,
        elements=_derived_elements(project, component),
        ref_axis_pct=_derived_ref_axis(project),
        assumed=True,
        root_z=root_z,
        notes=notes,
    )


def _derived_elements(project: Project, component: str) -> int:
    """Station count for a derived planform: the wing's, so one project reports
    every surface at a comparable resolution, floored at the T-6 minimum of 2."""
    geometry = project.geometry
    wing = geometry.by_name("wing") if geometry is not None else None
    return max(2, wing.elements // 2 if wing is not None else 10)


def _derived_ref_axis(project: Project) -> float:
    """LRA fraction for a derived planform: the wing's, so a project that has
    stated its beam axis once does not have to state it again per surface."""
    geometry = project.geometry
    wing = geometry.by_name("wing") if geometry is not None else None
    return wing.ref_axis_pct if wing is not None else 0.25


def half_area_centroid(planform: TailPlanform) -> float:
    """Span centroid ``ybar`` of one half-planform (in) -- the bending target.

    Closed-form for a straight-tapered surface,
    ``ybar = (b/3)(c_r + 2c_t)/(c_r + c_t)``, and this integration reproduces it;
    the test states the analytic value and this function is what the module
    integrates, so the two are independent producers of the same number.
    """
    h = max(1, planform.elements)
    ds = planform.span / h
    area = moment = 0.0
    for el in range(h):
        s = ds / 2 + el * ds
        da = planform.chord(s) * ds
        area += da
        moment += da * s
    return moment / area if area else 0.0


def is_t_tail(project: Project) -> bool:
    """True when the layout says the h-tail sits on the fin (plan 09 T7's gate)."""
    geometry = project.geometry
    layout = geometry.parametric if geometry is not None else None
    return layout is not None and layout.tail_type == TailType.T_TAIL


__all__ = [
    "HTAIL",
    "VTAIL",
    "TAIL_COMPONENTS",
    "PLANFORM_TOLERANCE",
    "TailPlanform",
    "half_area_centroid",
    "is_t_tail",
    "resolve_tail_planform",
    "validate_tail_planform",
]
