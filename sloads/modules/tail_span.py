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
    fi_j  = -n_n * W_surf * (c_j*dy)/S                        inertia (T-9)
    fa_j  = -n_a * W_surf * (c_j*dy)/S                        axial (v-tail only)

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

**4. The surface weight is derived, never entered twice.** It comes from the
``htail``/``vtail``-tagged rows of ``weight.items`` -- the mass SSOT (plan 11
decision B-2) -- through ``mass_distribution.tail_surface_weight``. Until
2026-08-10 this module read ``TailMassInput.panel_weight_lb`` and nothing else,
and **no shipped fixture had ever set one**, so every h-tail deck the suite
produced was air-only while the data base carried the tail mass all along. The
entered value survives as an explicit override; the difference is reported by
``mass_distribution.tail_reconciliation`` either way.

Each surface's inertia, and why they differ
-------------------------------------------
The h-tail's normal axis is the airplane's vertical, so one term does it:
``-n_z*W_ht`` in ``fz``, bending the surface. The **fin's normal axis is
lateral**, so the same vertical acceleration does something else entirely to it,
and the fin needs two terms:

* ``-n_y*W_vt`` in ``fz`` (the local normal, mapped to airplane ``fy``) --
  the bending term, with ``n_y = (LT25+LT50)/W_case`` from
  :func:`lateral_load_factor`. It relieves the surface total by exactly
  ``W_vt/W_case``, which is what makes it self-checking, and it inherits plan 13
  decision **L-7**'s fin-only over-statement caveat.
* ``-n_z*W_vt`` in ``f_span`` -- **axial** along the fin, no bending at all.

This supersedes plan 13 decision **L-8** for this per-condition view (user
decision, 2026-08-10). The balanced case remains the authority for a *balanced*
lateral field; what changed is that the fin's own mass now appears in the fin's
own deck, where before the deck was silently air-only.

Phase-1 scope, stated in-band
-----------------------------
* **Control-surface load is smeared** into the parent surface (decision T-4
  option 2): ``LT50`` *is* the control part and it is already in the
  distribution above. T5 makes the mode explicit; T6 adds the discrete
  hinge/actuator alternative.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from ..models import (
    ConditionResult,
    CriticalCondition,
    CriticalLoadSet,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    TailSpanResult,
    VnPoint,
    WingStationLoad,
)
from ..registry import register
from ..tail_geometry import HTAIL, VTAIL, TailPlanform, resolve_tail_planform
from .select import default_critical, vn_points

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
               z_offset: float = 0.0, n_normal: Optional[float] = None,
               n_axial: float = 0.0) -> List[WingStationLoad]:
    """The spanwise station table for one condition, in the surface's local frame.

    Returns stations ordered by span coordinate: port tip -> starboard tip for
    the symmetric h-tail (``y`` negative to positive), root -> tip for the
    single-sided v-tail. ``fz`` is the **net** strip load, air plus inertia;
    ``sz``/``mxx``/``myy`` are cumulative tip->root on each half.

    ``surface_weight_lb`` of zero switches the inertia off entirely, which is how
    the air-only closure is checked against an independent producer rather than
    against a re-run of this same quadrature.

    **Two load factors, because a surface has two directions.** ``n_normal`` is
    the acceleration along the surface's *normal* (load) axis and drives the
    bending inertia in ``fz``; it defaults to ``n_case``, which is right for the
    horizontal tail, whose normal axis *is* the airplane's vertical. The fin's
    normal axis is lateral, so its caller passes the lateral factor here and the
    vertical one as ``n_axial`` -- the term that runs along the fin's span and
    lands in ``f_span``. Passing ``n_case`` for a fin's normal direction would
    claim a pull-up bends the fin sideways, which is the error this signature
    exists to make unavailable.
    """
    area = planform.area
    if area <= 0:
        return []
    n_bend = n_case if n_normal is None else n_normal
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
            inertia = -n_bend * surface_weight_lb * frac
            axial = -n_axial * surface_weight_lb * frac
            half.append(WingStationLoad(
                x=x_lra, y=sign * s, z=z_offset,
                fx=0.0, fz=w25 + w50 + inertia,
                sx=0.0, sz=0.0, mxx=0.0, myy=0.0, mzz=0.0,
                myy_free=torsion, f_inertia=inertia, f_span=axial))
        # Cumulative tip -> root on this half. ``myy`` accumulates the strip
        # torsions plus the sweep transfer of outboard shear, exactly as
        # ``airloads`` does; on an unswept planform the transfer term is
        # identically zero and the root torsion is the closed form of plan §4.
        half.sort(key=lambda st: abs(st.y), reverse=True)
        sz = mxx = myy = s_span = 0.0
        prev: Optional[WingStationLoad] = None
        for st in half:
            if prev is not None:
                mxx += sz * (abs(prev.y) - abs(st.y))
                myy += sz * (st.x - prev.x)
            sz += st.fz
            # The axial column accumulates on the same tip->root sweep, and it is
            # a pure sum: an axial load makes no moment about its own line of
            # action, so it enters neither ``mxx`` nor ``myy``.
            s_span += st.f_span
            myy += st.myy_free
            st.sz = sz
            st.mxx = mxx + 0.0
            st.myy = myy
            st.s_span = s_span
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
    return default_critical(project)


def _vn_points(project: Project) -> List["VnPoint"]:
    """The V-n matrix to read load factors from -- through the **single owner**.

    ``select.vn_points`` is that owner's tolerant read (M2R-8): the persisted
    ``Project.envelope`` when it has one, freshly built from the flight-loads
    inputs when it does not, ``[]`` when neither exists. Reading
    ``project.envelope`` directly -- which this module did until 2026-08-10 --
    silently returns nothing on the path that matters most, because
    ``registry.run_all_modules`` never assigns ``project.envelope``: **every
    exported tail deck took the ``n = 1.0`` fallback**, understating the h-tail
    inertia by up to 3.8x on exactly the balancing cases that size the surface.
    That was invisible while the surface weight was always zero, and became a
    wrong number the moment it was not.

    With no V-n matrix at all each condition takes the documented fallback and
    says so, which is the honest end state for a project with no flight-loads
    inputs.
    """
    return vn_points(project)


def _load_factor(cond: CriticalCondition,
                 vn_points: Sequence["VnPoint"]) -> Tuple[float, bool]:
    """``(n, from_vn)`` for a condition -- its V-n point's, or the fallback."""
    if cond.case is not None:
        point = next((p for p in vn_points if p.case == cond.case), None)
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
    """The surface weight to smear -- **derived from the item data base**.

    Delegated to :func:`sloads.mass_distribution.tail_surface_weight`, the single
    owner: the ``htail``/``vtail``-tagged ``weight.items`` by default, the
    entered ``TailMassInput.panel_weight_lb`` only when it is marked an explicit
    override. Until this step the entered value was the *only* source and no
    fixture ever set one, so every h-tail deck the suite shipped was air-only.
    """
    from ..mass_distribution import tail_surface_weight

    return tail_surface_weight(project, component)


def _weight_basis(project: Project, component: str) -> str:
    """Where this surface's weight came from -- said on the result, not implied."""
    for tm in project.tail_mass or []:
        if tm.surface == component and tm.weight_is_override:
            return "entered as an EXPLICIT OVERRIDE of the weight data base"
    return f"derived from the {component}-tagged items in the weight data base"


def _case_weight(project: Project, cond: CriticalCondition,
                 vn_points: Sequence["VnPoint"]) -> float:
    """The airplane weight the condition flies at -- its V-n point's CG case.

    The same lookup SELECT makes (``cg_map[point.cg].weight_lb``), so the lateral
    load factor below is built on the case's own weight and not on a gross-weight
    stand-in. 0.0 when the condition names no V-n point, which switches the
    lateral inertia off rather than dividing by a guess.
    """
    fl = project.flight_loads
    if fl is None or cond.case is None:
        return 0.0
    point = next((p for p in vn_points if p.case == cond.case), None)
    if point is None:
        return 0.0
    case = next((c for c in fl.cg_cases if c.name == point.cg), None)
    return case.weight_lb if case is not None else 0.0


def lateral_load_factor(project: Project, cond: CriticalCondition,
                        vn_points: Optional[Sequence["VnPoint"]] = None
                        ) -> Tuple[float, float]:
    """``(n_y, W_case)`` for a fin condition -- the fin's own side load over it.

    **Why this is the producer.** A fin's mass is accelerated *sideways*, and the
    lateral load factor that does it is a property of a balanced case. This is a
    single-condition view with no balance in it, so the lateral factor is derived
    the only self-consistent way available: the free-free lateral acceleration of
    the airplane under the one lateral aerodynamic load the suite models, which
    is the fin's own::

        n_y = (LT25 + LT50) / W_case

    Two consequences, both stated in-band on every v-tail result rather than left
    for a reader to work out:

    1. It **relieves**. The strip inertia is ``-n_y*W_vt*frac``, so the surface
       total comes out at ``(1 - W_vt/W_case)`` of the air load exactly -- 0.7 %
       on ga6, 1.8 % on the regional jet. Small, and in the unconservative
       direction, which is precisely why it is reported and not buried.
    2. It inherits **plan 13 decision L-7**: no fuselage or wing side force in
       sideslip exists anywhere in this suite, so reacting the fin's load with
       inertia alone over-states the real airplane's ``n_y``. Conservative for
       the accelerations, and it makes the relief above an upper bound on itself.

    Superseding L-8 for this view is deliberate (user decision, 2026-08-10): the
    balanced case remains the authority for a *balanced* lateral field; this term
    is the fin's own mass in the fin's own deck, and its exactness (item 1) is
    what makes it checkable.
    """
    points = _vn_points(project) if vn_points is None else vn_points
    weight = _case_weight(project, cond, points)
    if not weight:
        return 0.0, 0.0
    return ((cond.lt25 or 0.0) + (cond.lt50 or 0.0)) / weight, weight


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
    # Resolved once for the whole build, as ``build_critical`` does with the same
    # envelope -- not per condition, which would rebuild the V-n matrix up to
    # thirteen times on a fixture that persists none.
    vn_points = _vn_points(project)

    for cond in _critical_set(project).conditions:
        component = cond.component
        if component not in (HTAIL, VTAIL):
            continue
        planform = planforms.get(component)
        if planform is None or cond.lt25 is None or cond.lt50 is None:
            continue

        mode = control_load_mode(project, component)
        n_case, from_vn = _load_factor(cond, vn_points)
        rh_scale, lh_scale = side_scales(cond)
        weight = _surface_weight(project, component)
        # Each surface's inertia is built on the acceleration along *its own*
        # normal axis. The h-tail's normal axis is the airplane's vertical, so
        # ``n_case`` is it and there is no axial term. The fin's normal axis is
        # lateral: its bending inertia comes from ``n_y`` and ``n_case`` becomes
        # the term that runs *along* the fin's span (axial). Getting these two
        # crossed would put a pull-up into fin side bending.
        if component == VTAIL:
            n_normal, case_weight = lateral_load_factor(project, cond, vn_points)
            n_axial = n_case
        else:
            n_normal, case_weight, n_axial = n_case, 0.0, 0.0
        inertia_modelled = weight > 0.0 and bool(n_normal or n_axial)
        # The fin's own root waterline (plan 13 L-1), not zero: the roll moment a
        # side load makes about the CG is ``-Fy*(z - z_cg)``, so a fin modelled on
        # the centreline gets that moment wrong and can get it wrong in *sign*.
        # Owned by ``tail_geometry.fin_root_waterline`` and carried on the
        # planform, so the three-view and this deck place one fin once.
        z_offset = _h_tail_waterline(project) if component == HTAIL else planform.root_z

        notes = list(planform.notes)
        notes.append(
            f"control load {mode}: the LT50 camber/elevator part is distributed "
            "into the surface with the rest, not applied at hinge stations")
        if not from_vn:
            notes.append(
                f"condition names no V-n point -- load factor defaulted to "
                f"{DEFAULT_LOAD_FACTOR:g} for the inertia term")
        if component == VTAIL:
            notes.append(
                f"fin root waterline {planform.root_z:.1f} in "
                f"({'ASSUMED, ' if planform.root_z_assumed else ''}"
                f"basis '{planform.root_z_basis}') -- the stations run from there "
                "to the tip, so the deck's roll arm about the airplane CG is this "
                "value plus the span")
        if weight <= 0.0:
            notes.append(
                f"no {component}-tagged item in the weight data base and no "
                "entered override -- air load only, no inertia. This is an "
                "omission in the data, not a weightless surface: tag the "
                "surface's mass items on the Weights page")
        else:
            notes.append(
                f"surface mass {weight:.1f} lb, {_weight_basis(project, component)}, "
                "smeared as a uniform area density over the planform (T-3)")
        if component == VTAIL and weight > 0.0:
            if case_weight:
                notes.append(
                    f"fin side inertia at n_y = {n_normal:+.4f} g "
                    f"(= side load / {case_weight:.0f} lb case weight): the "
                    "free-free lateral response to the fin's own load, the only "
                    "lateral aero this suite models. It RELIEVES the surface "
                    f"total by exactly W_vt/W = {100.0 * weight / case_weight:.2f} %"
                    " -- and because no fuselage or wing sideslip force exists "
                    "(plan 13 L-7), the real airplane's n_y is smaller and that "
                    "relief is an upper bound on itself")
            else:
                notes.append(
                    "fin side inertia omitted: the condition names no V-n point, "
                    "so there is no case weight to form n_y from")
            notes.append(
                f"fin axial inertia {-n_axial * weight:+.1f} lb total at "
                f"n_z = {n_axial:.3f} g -- the fin spans in Z, so the vertical "
                "acceleration that bends an h-tail compresses this surface; it "
                "is an axial column, and it makes no bending")
        if rh_scale != lh_scale:
            notes.append(
                f"UNSYMMETRICAL (23.427(a)): RH x{rh_scale:.3f}, LH x{lh_scale:.3f} "
                "of the half-surface load, read from SELECT's own split")

        stations = distribute(
            planform, cond.lt25, cond.lt50, n_case=n_case,
            surface_weight_lb=weight, rh_scale=rh_scale, lh_scale=lh_scale,
            z_offset=z_offset, n_normal=n_normal, n_axial=n_axial)
        out[component].append(TailSpanResult(
            case=cond.label, component=component, stations=stations,
            lt25=cond.lt25, lt50=cond.lt50, n_case=n_case,
            surface_weight_lb=weight, n_y=n_normal if component == VTAIL else 0.0,
            case_weight_lb=case_weight,
            attachment_y=attachment_stations(project, planform),
            rh_scale=rh_scale, lh_scale=lh_scale,
            planform_assumed=planform.assumed, control_load_mode=mode,
            inertia_modelled=inertia_modelled,
            case_ref=cond.case_ref, safety_factor=cond.safety_factor,
            torsion_axis=f"LRA {planform.ref_axis_pct * 100:.0f}% chord",
            notes=notes,
        ))
    return out


def air_total(result: TailSpanResult) -> float:
    """The air load the table integrates to -- SELECT's total, per-side scaled."""
    return result.air_total


def inertia_total(result: TailSpanResult) -> float:
    """``-n_normal * W_surf`` -- the d'Alembert **bending** total (T-9).

    The normal-direction factor, which is the vertical ``n_case`` for the h-tail
    and the lateral ``n_y`` for the fin -- the one distinction this whole step
    turns on. Zero when the surface carries no modelled inertia.
    """
    if not result.inertia_modelled:
        return 0.0
    n = result.n_y if result.component == VTAIL else result.n_case
    return -n * result.surface_weight_lb


def axial_total(result: TailSpanResult) -> float:
    """``-n_z * W_surf`` along the span -- the fin's axial column, 0 elsewhere.

    Non-zero only for the vertical tail: it is the term that exists *because* the
    fin spans in Z, so there is nothing for it to be on a horizontal surface.
    """
    if not result.inertia_modelled or result.component != VTAIL:
        return 0.0
    return -result.n_case * result.surface_weight_lb


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
    "axial_total",
    "build_tail_span",
    "distribute",
    "free_torsion_total",
    "inertia_total",
    "lateral_load_factor",
    "root_index",
    "side_scales",
    "strip_spans",
]
