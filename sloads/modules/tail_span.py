"""Spanwise empennage load distribution -- the tail's structural deliverable.

Design note: ``docs/30_future/09_distributed_empennage_loads_plan.md``, step
**T2**, decisions T-2/T-3/T-6/T-8/T-9/T-10. Planform resolution and the
half/full bookkeeping: :mod:`sloads.tail_geometry`. Conventions:
``docs/10_standard/CONVENTIONS.md``.

The empennage has had *chordwise* loads since C7 (``taildist.py``, Ch 10,
Appendix-A oracle-locked) and *totals* since C6 (``select.py``). What it has
never had is the thing the wing has: a load at every span station, on a stated
load reference axis, that a beam model can be sized from. This module is that,
and it is a pure consumer -- SELECT's ``LT25``/``LT50`` and the v-tail side
loads are **read, never recomputed** (T-7), so no Appendix A figure moves.

The distribution
----------------
Chord-proportional, for both the angle-of-attack (``LT25``) and camber/control
(``LT50``) parts (decision T-2). Per strip ``j`` of the **whole** planform area
``S``::

    w25_j = k_side * LT25 * (c_j*dy)/S
    w50_j = k_side * LT50 * (c_j*dy)/S
    fz_j  = w25_j + w50_j                                     air
    tor_j = w25_j*(x_lra_j - x25_j) + w50_j*(x_lra_j - x50_j)  torsion about the LRA
    fi_j  = -n * W_surf * (c_j*dy)/S                          inertia (T-9)

Chordwise placement stays exactly TAILDIST's -- ``LT25`` at 25 % chord, ``LT50``
at 50 % -- so the strip torsion about any reference axis is closed-form and the
whole distribution has **analytic** closure targets. That matters more here than
usual: no printed oracle exists for a spanwise tail distribution, so those
closed forms *are* the gate (``CLAUDE.md`` practice 2, plan §4).

Three things that are easy to get backwards, and are not
--------------------------------------------------------
**1. The inertia sign is d'Alembert, full stop** (decision T-9). It is
``-n * W_surf``, set by the case's load factor alone -- never "opposing the air
load". The governing GA6 h-tail conditions are *down*-load cases
(``UNCHECKED MAN DN`` at -1400 lb), so a magnitude-opposing rule would relieve
exactly the cases that size the surface. ``test_the_inertia_sign_is_dalembert``
pins it by asserting a down-load case comes out **larger** in magnitude than
air alone.

**2. The h-tail beam is full span, tip to tip** (decision T-8). Not a semispan
table doubled: the stations run from the port tip through the centreline to the
starboard tip as one member, reacted at the **fuselage attachment stations**
this module defines (``attachment_y``) rather than clamped at a root. That is
the only topology that can carry the 23.427(a) left/right asymmetry in one deck,
and it keeps SELECT's both-sides totals end-to-end with no factor-of-two seam.
The attachment stations are defined *here*, in the physics, and not improvised
by the deck writer -- otherwise the export invariant would have nothing to close
against (plan §7's named risk).

**3. Cumulative quantities run tip->root on each half.** ``sz``/``mxx``/``myy``
at a station are the internal loads there, integrating the loads **outboard of
it on its own half**, exactly as ``airloads.py`` does. The two halves meet at
the centreline. A station's own ``fz``/``fx`` are the applied strip loads, which
is what the deck emits directly -- the wing bridge has to *difference* the
cumulative column because WINGINER publishes nothing else, and that differencing
is what smears a concentrated mass inboard (the filed wing-export defect). The
tail publishes the strip loads, so the export needs no differencing and inherits
none of that.

Phase-1 scope, stated in-band
-----------------------------
* **V-tail inertia is omitted.** The suite has no lateral load factor -- the
  v-tail cases carry the airplane's *normal* ``n``, which is not the
  acceleration a fin's own mass sees sideways. Applying ``n_z`` to it would be a
  fabricated load in the wrong direction. Every v-tail result carries
  ``inertia_modelled=False`` and says so. Revisit with plan 11 B8a, which is
  where a lateral load factor first has to exist.
* **Control-surface load is smeared** into the parent surface (decision T-4
  option 2): ``LT50`` *is* the control part and it is already in the
  distribution above. T5 makes the mode explicit; T6 adds the discrete
  hinge/actuator alternative.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..models import (
    ConditionResult,
    CriticalCondition,
    CriticalLoadSet,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    TailSpanResult,
    WingStationLoad,
)
from ..registry import register
from ..tail_geometry import HTAIL, VTAIL, TailPlanform, resolve_tail_planform
from .select import build_critical

MODULE_NAME = "tail_span"

#: The control-surface load modes (decision T-4). ``"smeared"`` is phase 1 and the
#: only one implemented; ``"discrete"`` is T6 and raises until it exists, because
#: a silent fallback would report a localized hinge/actuator load path that the
#: deck does not contain.
CONTROL_MODES = ("smeared", "discrete")
DEFAULT_CONTROL_MODE = "smeared"

#: Load factor used when a condition names no V-n point (plan §7's documented
#: fallback). Printed in-band on the result rather than assumed silently.
DEFAULT_LOAD_FACTOR = 1.0

#: The chordwise stations ``LT25`` and ``LT50`` act at -- TAILDIST's own, and the
#: reason the strip torsion is closed-form (decision T-2).
X25_PCT = 0.25
X50_PCT = 0.50


# --------------------------------------------------------------------------- #
# Strip geometry
# --------------------------------------------------------------------------- #
def strip_spans(planform: TailPlanform) -> List[Tuple[float, float]]:
    """``[(span station, strip width)]`` for one half planform, root -> tip.

    Uniform strips with mid-strip stations, ``elements`` of them -- exactly the
    wing's pattern (decision T-6), so ``interp_x``/tributary reasoning carries
    over unchanged and a user who has set ``elements`` on the wing gets the same
    semantics on the tail.
    """
    h = max(2, planform.elements)
    ds = planform.span / h
    return [(ds / 2.0 + j * ds, ds) for j in range(h)]


def attachment_stations(project: Project, planform: TailPlanform) -> List[float]:
    """The span stations the full-span h-tail beam is reacted at (decision T-8).

    The horizontal tail attaches to the fuselage at its sides, so the beam is
    supported at ``+-fuselage_width/2`` -- a genuinely determinate pair for a
    symmetric case, and the pair whose reactions differ under 23.427(a), which is
    the whole point of the full-span topology.

    Where the parametric fuselage width is unknown (it is ``None`` on every
    shipped fixture) the attachments fall back to the **centreline pair** at
    ``+-ds/2``, the innermost strip stations: still two distinct supports, still
    determinate, and stated on the result rather than silently chosen. The
    consequence is that the carry-through between them is a single strip wide, so
    the recovered attachment bending is very slightly high -- the same direction
    as the wing's centreline-clamp limitation, and filed alongside it.
    """
    if planform.component != HTAIL:
        return []
    geometry = project.geometry
    layout = geometry.parametric if geometry is not None else None
    width = getattr(layout, "fuselage_width", None) if layout is not None else None
    if width:
        half = min(0.5 * width, 0.9 * planform.span)
        return [-half, half]
    ds = planform.span / max(2, planform.elements)
    return [-ds / 2.0, ds / 2.0]


# --------------------------------------------------------------------------- #
# The distribution
# --------------------------------------------------------------------------- #
def distribute(planform: TailPlanform, lt25: float, lt50: float, *,
               n_case: float = 0.0, surface_weight_lb: float = 0.0,
               rh_scale: float = 1.0, lh_scale: float = 1.0,
               z_offset: float = 0.0) -> List[WingStationLoad]:
    """The spanwise station table for one condition, in the surface's local frame.

    Returns stations ordered by span coordinate: port tip -> starboard tip for
    the symmetric h-tail (``y`` negative to positive), root -> tip for the
    single-sided v-tail. ``fz`` is the **net** strip load, air plus inertia;
    ``sz``/``mxx``/``myy`` are cumulative tip->root on each half.

    ``surface_weight_lb`` of zero switches the inertia off entirely, which is how
    the air-only closure is checked against an independent producer rather than
    against a re-run of this same quadrature.
    """
    area = planform.area
    if area <= 0:
        return []
    halves: List[Tuple[float, float]] = (
        [(-1.0, lh_scale), (1.0, rh_scale)] if planform.symmetric
        else [(1.0, rh_scale)])

    stations: List[WingStationLoad] = []
    for sign, k_side in halves:
        half: List[WingStationLoad] = []
        for s, ds in strip_spans(planform):
            chord = planform.chord(s)
            frac = chord * ds / area
            w25 = k_side * lt25 * frac
            w50 = k_side * lt50 * frac
            x_lra = planform.x_at(s, planform.ref_axis_pct)
            torsion = (w25 * (x_lra - planform.x_at(s, X25_PCT))
                       + w50 * (x_lra - planform.x_at(s, X50_PCT)))
            inertia = -n_case * surface_weight_lb * frac
            half.append(WingStationLoad(
                x=x_lra, y=sign * s, z=z_offset,
                fx=0.0, fz=w25 + w50 + inertia,
                sx=0.0, sz=0.0, mxx=0.0, myy=0.0, mzz=0.0,
                myy_free=torsion))
        # Cumulative tip -> root on this half. ``myy`` accumulates the strip
        # torsions plus the sweep transfer of outboard shear, exactly as
        # ``airloads`` does; on an unswept planform the transfer term is
        # identically zero and the root torsion is the closed form of plan §4.
        half.sort(key=lambda st: abs(st.y), reverse=True)
        sz = mxx = myy = 0.0
        prev: Optional[WingStationLoad] = None
        for st in half:
            if prev is not None:
                mxx += sz * (abs(prev.y) - abs(st.y))
                myy += sz * (st.x - prev.x)
            sz += st.fz
            myy += st.myy_free
            st.sz = sz
            st.mxx = mxx + 0.0
            st.myy = myy
            prev = st
        stations.extend(half)

    stations.sort(key=lambda st: st.y)
    return stations


def free_torsion_total(planform: TailPlanform, lt25: float, lt50: float, *,
                       rh_scale: float = 1.0, lh_scale: float = 1.0) -> float:
    """Σ of the strip torsions about the LRA -- plan §4's closed-form target.

    Separate from :func:`distribute` on purpose: this is the quantity the
    analytic closure is stated for, and computing it independently of the
    cumulative recurrence is what makes the gate a check rather than a tautology.
    """
    total = 0.0
    halves = [lh_scale, rh_scale] if planform.symmetric else [rh_scale]
    for k_side in halves:
        for s, ds in strip_spans(planform):
            frac = planform.chord(s) * ds / planform.area
            x_lra = planform.x_at(s, planform.ref_axis_pct)
            total += (k_side * lt25 * frac * (x_lra - planform.x_at(s, X25_PCT))
                      + k_side * lt50 * frac * (x_lra - planform.x_at(s, X50_PCT)))
    return total


# --------------------------------------------------------------------------- #
# Case assembly
# --------------------------------------------------------------------------- #
def _critical_set(project: Project) -> CriticalLoadSet:
    if project.envelope is not None and project.envelope.critical is not None:
        return project.envelope.critical
    return build_critical(project)


def _load_factor(project: Project, cond: CriticalCondition) -> Tuple[float, bool]:
    """``(n, from_vn)`` for a condition -- its V-n point's, or the fallback."""
    if cond.case is not None and project.envelope is not None:
        point = next((p for p in project.envelope.vn if p.case == cond.case), None)
        if point is not None:
            return point.nz, True
    return DEFAULT_LOAD_FACTOR, False


def _value(cond: CriticalCondition, key: str) -> Optional[float]:
    for lv in cond.loads:
        if lv.key == key:
            return lv.value
    return None


def side_scales(cond: CriticalCondition) -> Tuple[float, float]:
    """``(rh_scale, lh_scale)`` for a condition (decision T-10).

    ``1.0``/``1.0`` for every symmetric condition. For 23.427(a) the scales come
    from ``select_htail_unsymmetrical``'s own RH/LH split, **read** off the
    condition's reported loads and never recomputed -- the ``pc = min(100 -
    10(n-1), 80)`` rule stays owned by SELECT, which is oracle-locked. Each scale
    is that side's share of *half* the total, because a half planform integrates
    to half the load.
    """
    rh, lh = _value(cond, "rh_side_load"), _value(cond, "lh_side_load")
    if rh is None or lh is None:
        return 1.0, 1.0
    half = 0.5 * ((cond.lt25 or 0.0) + (cond.lt50 or 0.0))
    if not half:
        return 1.0, 1.0
    return rh / half, lh / half


def _surface_weight(project: Project, component: str) -> float:
    for tm in project.tail_mass or []:
        if tm.surface == component:
            return tm.panel_weight_lb
    return 0.0


def control_load_mode(project: Project, component: str) -> str:
    """The control-load mode for one surface (T-4/T5), validated.

    Phase 1 ships ``"smeared"`` only. ``"discrete"`` is refused rather than
    quietly downgraded: the two modes describe *different load paths* -- one
    spreads the control load into the surface, the other concentrates it at hinge
    and actuator stations -- and a deck that claims the second while carrying the
    first would be wrong in exactly the place a designer looks.
    """
    mode = DEFAULT_CONTROL_MODE
    for tm in project.tail_mass or []:
        if tm.surface == component:
            mode = tm.control_load_mode or DEFAULT_CONTROL_MODE
    if mode not in CONTROL_MODES:
        raise ValueError(
            f"unknown control_load_mode {mode!r} for {component}; expected one of "
            f"{CONTROL_MODES}")
    if mode == "discrete":
        raise MissingInputError(
            f"control_load_mode='discrete' for the {component} needs hinge and "
            "actuator span stations, which the schema does not carry yet (plan 09 "
            "T6). Use 'smeared' -- the control load is already distributed into "
            "the surface as the LT50 part.")
    return mode


def _h_tail_waterline(project: Project) -> float:
    geometry = project.geometry
    layout = geometry.parametric if geometry is not None else None
    return layout.root_waterline_z if layout is not None else 0.0


def build_tail_span(project: Project) -> Dict[str, List[TailSpanResult]]:
    """``{"htail": [...], "vtail": [...]}`` -- one result per critical condition.

    A surface with no planform (no area/span entered) yields an empty list; a
    condition with no ``LT25``/``LT50`` split is skipped, exactly as
    ``taildist`` skips it, so the two tail views cover the same conditions.
    """
    out: Dict[str, List[TailSpanResult]] = {HTAIL: [], VTAIL: []}
    planforms = {c: resolve_tail_planform(project, c) for c in (HTAIL, VTAIL)}
    if not any(planforms.values()):
        return out

    for cond in _critical_set(project).conditions:
        component = cond.component
        if component not in (HTAIL, VTAIL):
            continue
        planform = planforms.get(component)
        if planform is None or cond.lt25 is None or cond.lt50 is None:
            continue

        mode = control_load_mode(project, component)
        n_case, from_vn = _load_factor(project, cond)
        rh_scale, lh_scale = side_scales(cond)
        # Phase 1: the v-tail carries no inertia -- see the module docstring.
        inertia_modelled = component == HTAIL
        weight = _surface_weight(project, component) if inertia_modelled else 0.0
        z_offset = _h_tail_waterline(project) if component == HTAIL else 0.0

        notes = list(planform.notes)
        notes.append(
            f"control load {mode}: the LT50 camber/elevator part is distributed "
            "into the surface with the rest, not applied at hinge stations")
        if not from_vn:
            notes.append(
                f"condition names no V-n point -- load factor defaulted to "
                f"{DEFAULT_LOAD_FACTOR:g} for the inertia term")
        if not inertia_modelled:
            notes.append(
                "v-tail inertia omitted: the suite has no lateral load factor, and "
                "applying the airplane's normal n to a fin's mass would be a "
                "fabricated load in the wrong direction (plan 09 phase-1 scope)")
        elif weight <= 0.0:
            notes.append(
                "no tail_mass entry for this surface -- air load only, no inertia")
        if rh_scale != lh_scale:
            notes.append(
                f"UNSYMMETRICAL (23.427(a)): RH x{rh_scale:.3f}, LH x{lh_scale:.3f} "
                "of the half-surface load, read from SELECT's own split")

        stations = distribute(
            planform, cond.lt25, cond.lt50, n_case=n_case,
            surface_weight_lb=weight, rh_scale=rh_scale, lh_scale=lh_scale,
            z_offset=z_offset)
        out[component].append(TailSpanResult(
            case=cond.label, component=component, stations=stations,
            lt25=cond.lt25, lt50=cond.lt50, n_case=n_case,
            surface_weight_lb=weight,
            attachment_y=attachment_stations(project, planform),
            rh_scale=rh_scale, lh_scale=lh_scale,
            planform_assumed=planform.assumed, control_load_mode=mode,
            inertia_modelled=inertia_modelled and weight > 0.0,
            case_ref=cond.case_ref, safety_factor=cond.safety_factor,
            torsion_axis=f"LRA {planform.ref_axis_pct * 100:.0f}% chord",
            notes=notes,
        ))
    return out


def air_total(result: TailSpanResult) -> float:
    """The air load the table integrates to -- SELECT's total, per-side scaled."""
    return result.air_total


def inertia_total(result: TailSpanResult) -> float:
    """``-n * W_surf`` -- the d'Alembert total (T-9), zero when not modelled."""
    return -result.n_case * result.surface_weight_lb if result.inertia_modelled else 0.0


def root_index(result: TailSpanResult) -> int:
    """Index of the station nearest the surface root (the centreline for the
    h-tail), where the cumulative columns carry the whole half's load."""
    return min(range(len(result.stations)),
               key=lambda i: abs(result.stations[i].y))


def run(project: Project) -> ModuleResult:
    """Registry entry point: the spanwise empennage loads as a reportable result."""
    spans = build_tail_span(project)
    results = spans[HTAIL] + spans[VTAIL]
    if not results:
        raise MissingInputError(
            "no empennage surface has both a planform (area + span) and a critical "
            "condition carrying an LT25/LT50 split -- nothing to distribute")

    conditions: List[ConditionResult] = []
    for r in results:
        stations = r.stations
        root = stations[root_index(r)] if stations else None
        conditions.append(ConditionResult(
            title=f"{r.component} spanwise load -- {r.case}",
            far_reference="23.427(a)" if r.rh_scale != r.lh_scale else "23.421",
            values=[
                LoadValue("Air load total", air_total(r), "lb",
                          key="tail_span_air_total"),
                LoadValue("Inertia total", inertia_total(r), "lb",
                          key="tail_span_inertia_total"),
                LoadValue("Stations", float(len(stations)), "",
                          key="tail_span_stations"),
                LoadValue("Root shear Sz", root.sz if root else 0.0, "lb",
                          key="tail_span_root_sz"),
                LoadValue("Root bending Mxx", root.mxx if root else 0.0, "lb-in",
                          key="tail_span_root_mxx"),
                LoadValue(f"Root torsion Myy ({r.torsion_axis})",
                          root.myy if root else 0.0, "lb-in",
                          key="tail_span_root_myy"),
            ],
            note="; ".join(r.notes) or None,
            safety_factor=r.safety_factor,
            case_ref=r.case_ref,
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)


__all__ = [
    "MODULE_NAME",
    "CONTROL_MODES",
    "DEFAULT_CONTROL_MODE",
    "DEFAULT_LOAD_FACTOR",
    "control_load_mode",
    "X25_PCT",
    "X50_PCT",
    "air_total",
    "attachment_stations",
    "build_tail_span",
    "distribute",
    "free_torsion_total",
    "inertia_total",
    "root_index",
    "side_scales",
    "strip_spans",
]
