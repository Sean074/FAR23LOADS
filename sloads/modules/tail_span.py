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

The two control-surface load paths (T-4)
----------------------------------------
``"smeared"`` (the default, phase 1): the control load is already in the
distribution above -- ``LT50`` is the camber/elevator part and it is spread with
the rest. Nothing is added or removed; the mode is a statement about what the
numbers mean.

``"discrete"`` (T6): the control surface's own load leaves the strips and enters
the parent surface where the airplane puts it -- hinge reactions by tributary
span, plus the hinge-moment couple at the actuator. The control load is
**SELECT's own** (``elevator_load`` / ``load_on_rudder``, oracle-locked), and the
hinge moment is that load on the centroid of TAILDIST's aft-of-hinge pressure
block: the first hinge-moment output in the suite. See the section header below
for what each of those choices is protecting against.

T-tail transfer (T7)
--------------------
Where the layout says the horizontal tail sits on the fin, every v-tail case also
carries the h-tail's concurrent load at the fin tip -- the balancing load at that
case's own V-n point plus the h-tail's inertia (decision T-5). Conventional
layouts are untouched, to the byte.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from ..models import (
    ConditionResult,
    ControlPointLoad,
    CriticalCondition,
    CriticalLoadSet,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    TailSpanResult,
    TipTransfer,
    VnPoint,
    WingStationLoad,
)
from ..cg_cases import flight_cases
from ..derived_geometry import fuselage_width_at
from ..registry import register
from ..tail_geometry import HTAIL, VTAIL, TailPlanform, is_t_tail, resolve_tail_planform
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


class HTailAttachment(NamedTuple):
    """Where the full-span h-tail beam is reacted, and on whose authority (T-8a).

    ``y`` are the span stations; ``assumed`` is False only when the stations are a
    consequence of *entered* data alone; ``basis`` names the branch that produced
    them and is the discriminator a downstream model gates on (note 24 BM-3);
    ``note`` is the in-band sentence a derived value owes its consumer. Same
    provenance shape as ``tail_geometry.FinRoot`` and
    ``derived_geometry.BodyDragWaterline``.
    """

    y: List[float]
    assumed: bool
    basis: str
    note: str = ""


#: ``basis`` values :func:`htail_attachment` can return. ``STRIP_PAIR`` is the
#: no-geometry fallback -- the one a beam model must refuse to build a
#: conventional attachment on (note 24 BM-3), because it is not a fuselage
#: dimension at all, merely two adjacent stations that happen to straddle the
#: centreline.
ATTACH_FIN_TIP = "t-tail fin-tip joint"
ATTACH_ENTERED = "entered attachment butt line (sob_y_in)"
ATTACH_OUTLINE = "fuselage outline at the h-tail LRA station"
ATTACH_STRIP_PAIR = "innermost strip pair -- no fuselage geometry"


def htail_attachment(project: Project, planform: TailPlanform) -> HTailAttachment:
    """The stations the full-span h-tail beam is reacted at (decisions T-8/T-8a).

    Resolution order::

        T-tail layout        -> [0.0], the fin-tip joint          (assumed False)
        entered sob_y_in     -> +-sob_y_in                        (assumed False)
        fuselage outline     -> +-w(x_lra)/2                      (assumed True)
        neither              -> +-ds/2, the innermost strip pair   (assumed True)

    **T-tail first, because it is a different topology, not a different number**
    (note 24 F5.1). A T-tail horizontal surface is not attached to the fuselage at
    all -- it sits on the fin, and every load it carries reaches the airplane
    through the fin tip. Its beam therefore has *one* support on the centreline,
    a rigid joint that reacts moment as well as shear; reporting a pair of
    fuselage-side supports for it would describe a load path the airplane does not
    have. Entered ``tail_type`` is the whole authority, so nothing is assumed.

    **The outline branch interpolates, and does not take the maximum.** The
    horizontal tail attaches to the body at its own station -- in the tail cone --
    so the width that matters is :func:`~sloads.derived_geometry.fuselage_width_at`
    evaluated at the h-tail *root LRA* station, the same axis the beam model puts
    the node on (F6). ``parametric.fuselage_width`` is the **maximum** section and
    is deliberately not used: on ``atr42_100`` it is 106 in against 22 in at the
    tail, which would put the attachments five times too far outboard.

    That branch is marked **assumed even for an entered outline**, and the reason
    is worth stating: a fuselage outline is a station-area table sized to describe
    *volume*, and no shipped one resolves the tail cone at the empennage -- the
    three-section default (:func:`~sloads.models.inputs.default_fuselage_outline`)
    carries a tail-end width of a *tenth* of the maximum, a shape factor nobody
    measured. The attachment half-span swings by half again on that factor alone.
    Consumers that need a station they can build structure on should gate on
    ``basis``, and the real fix is an entered attachment butt line -- the h-tail
    surface's ``sob_y_in`` (BM-1: one quantity, read here and by the wing SOB
    resolver), not a better guess at the body.

    **The fallback is the centreline pair**: still two distinct determinate
    supports, still carrying the 23.427(a) asymmetry, but a single strip wide, so
    the recovered attachment bending is high -- the same direction as the wing's
    centreline-clamp limitation, and filed alongside it.
    """
    if planform.component != HTAIL:
        return HTailAttachment([], False, "", "")
    if is_t_tail(project):
        return HTailAttachment(
            [0.0], False, ATTACH_FIN_TIP,
            "T-TAIL layout: the horizontal tail is not fuselage-attached, so its "
            "beam has ONE support -- the fin-tip joint on the centreline, which "
            "reacts moment as well as shear. A fuselage-side pair would describe "
            "a load path this airplane does not have")
    geometry = project.geometry
    surf = geometry.by_name(planform.component) if geometry is not None else None
    if surf is not None and surf.sob_y_in is not None:
        y = abs(float(surf.sob_y_in))
        return HTailAttachment(
            [-y, y], False, ATTACH_ENTERED,
            f"h-tail attachment at +-{y:.1f} in -- the entered sob_y_in butt "
            "line (BM-1)")
    width = fuselage_width_at(
        geometry.fuselage if geometry is not None else None,
        planform.x_at(0.0, planform.ref_axis_pct))
    if width:
        half = min(0.5 * width, 0.9 * planform.span)
        return HTailAttachment(
            [-half, half], True, ATTACH_OUTLINE,
            f"h-tail attachment ASSUMED at +-{half:.1f} in -- half the fuselage "
            f"outline's width ({width:.1f} in) interpolated at the h-tail LRA "
            f"station {planform.x_at(0.0, planform.ref_axis_pct):.1f} in. The "
            "outline describes body volume, not the tail-cone frames: enter the "
            "attachment butt line to state it")
    ds = planform.span / max(2, planform.elements)
    return HTailAttachment(
        [-ds / 2.0, ds / 2.0], True, ATTACH_STRIP_PAIR,
        f"h-tail attachment ASSUMED at the innermost strip pair (+-{ds / 2.0:.1f} "
        "in) -- this project has no fuselage outline, so there is no body width "
        "to sit on. The carry-through is one strip wide and the attachment "
        "bending is correspondingly high")


def attachment_stations(project: Project, planform: TailPlanform) -> List[float]:
    """The attachment span stations alone -- see :func:`htail_attachment`."""
    return htail_attachment(project, planform).y


# --------------------------------------------------------------------------- #
# The distribution
# --------------------------------------------------------------------------- #
def distribute(planform: TailPlanform, lt25: float, lt50: float, *,
               n_case: float = 0.0, surface_weight_lb: float = 0.0,
               rh_scale: float = 1.0, lh_scale: float = 1.0,
               z_offset: float = 0.0, n_normal: Optional[float] = None,
               n_axial: float = 0.0,
               control_removal: Optional["ControlRemoval"] = None
               ) -> List[WingStationLoad]:
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

    ``control_removal`` is the ``"discrete"`` mode's other half (T6): the control
    surface's own load, taken back **out** of these strips over the span it
    actually occupies, so :func:`control_point_loads` can put it in at the hinges
    instead. Its two parts leave from the chord stations they arrived at -- the
    camber share off the 50 % line, the AoA share off the 25 % -- which is what
    keeps the parent surface's remaining load where TAILDIST puts it.
    """
    area = planform.area
    if area <= 0:
        return []
    n_bend = n_case if n_normal is None else n_normal
    halves: List[Tuple[float, float]] = (
        [(-1.0, lh_scale), (1.0, rh_scale)] if planform.symmetric
        else [(1.0, rh_scale)])
    shares = _removal_shares(planform, control_removal)

    stations: List[WingStationLoad] = []
    for sign, k_side in halves:
        half: List[WingStationLoad] = []
        for j, (s, ds) in enumerate(strip_spans(planform)):
            chord = planform.chord(s)
            frac = chord * ds / area
            if control_removal is None:
                # Left exactly as it was written at T2, arithmetic and order: the
                # smeared deck is bit-identical output and a re-associated
                # multiply would move its last bit on the one case whose
                # ``k_side`` is not 1 (23.427(a)).
                w25 = k_side * lt25 * frac
                w50 = k_side * lt50 * frac
            else:
                w25 = k_side * (lt25 * frac - shares[j] * control_removal.aoa)
                w50 = k_side * (lt50 * frac - shares[j] * control_removal.camber)
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
# The discrete control-surface load path (T6)
# --------------------------------------------------------------------------- #
# What changes in ``"discrete"`` mode is *where the control load enters the
# structure*, not how much of it there is. The surface's total is untouched; the
# control surface's own share stops being spread over the parent planform and is
# handed to it the way the airplane hands it over -- normal reactions at the
# hinges, and the hinge-moment couple at the actuator.
#
# Three things this path is careful about:
#
# 1. **The control load is SELECT's** (decision T-12), read and never recomputed:
#    ``elevator_load`` (SELECT.BAS 5216-5218) and its rudder counterpart, split
#    into their camber and angle-of-attack parts so each leaves the distribution
#    from the chord station TAILDIST put it at. Plan 09 T6's own sentence said
#    "the control part (LT50)", and that is not the same thing: ``LT50`` is the
#    *camber* load and its chordwise trapezoid runs leading edge to trailing edge,
#    so hanging all of it on the hinges would move stabilizer load onto the
#    elevator while ignoring the angle-of-attack share the elevator really
#    carries. Where a condition publishes no such value (the balancing, checked,
#    gust and unsymmetrical h-tail conditions; the rudder-neutral fin ones) the
#    load is **derived** from the TAILDIST aft-of-hinge block and marked, the
#    same derive-and-mark contract the planform itself is under.
#
# 2. **The identity is structural, not lucky** (decision T-14). Exactly the
#    control load leaves the strips and exactly the control load arrives at the
#    hinges, because the removal shares are normalised to sum to one over the
#    control surface's span. Removing it with the raw strip fractions would leave
#    the cross-mode force identity resting on ``sum(frac) == 1``, which is exact
#    for a derived rectangle and only 1 %-true for an entered polyline -- the T1
#    validator's own tolerance, quietly become a load error.
#
# 3. **The actuator carries a couple, not a force** (decision T-15). The schema
#    has no horn radius, so a rotary actuator is the honest model -- and it makes
#    the chordwise bookkeeping exact: hinge torsion plus actuator couple is
#    ``L_cs * (x_lra - x_cp)``, the control load acting at its own centre of
#    pressure, which is the number the smeared mode would have produced had it
#    ever placed the load there.

#: Chordwise centroid of the aft-of-hinge pressure block, as a fraction of the
#: aft-of-hinge chord (decision T-13). It is exactly a third because that block is
#: **always** a triangle: TAILDIST's net trailing-edge pressure is identically
#: zero (``WATT3 = WCAM3 = 0``), so the profile aft of the hinge line runs
#: linearly from its hinge-line value to nothing at the trailing edge, whatever
#: the case. That is what makes the suite's first hinge moment a closed form
#: rather than a quadrature.
HINGE_BLOCK_CENTROID = 1.0 / 3.0


@dataclass(frozen=True)
class ControlAttachment:
    """Where a control surface is held: hinge stations and the actuator (T-17).

    Span stations (in) measured **from the surface root along its span axis** --
    butt lines for the elevator, heights above the fin root for the rudder --
    the same coordinate the strips use. Entered once, for one side, on the
    symmetric horizontal tail and mirrored, exactly as the planform is.
    """

    surface: str
    hinges: Tuple[float, ...]
    actuator: float

    @property
    def span_extent(self) -> Tuple[float, float]:
        """The control surface's own span, taken as first hinge to last.

        The schema carries no separate control-surface span, and this is the
        honest reading of the geometry it does carry: the load is removed from
        the parent surface over the span the hinges hold, not over the whole
        surface. A control surface that overhangs its outermost hinge is
        therefore modelled as ending there -- stated, and revisited if a
        control-surface planform is ever entered.
        """
        return self.hinges[0], self.hinges[-1]


@dataclass(frozen=True)
class ControlRemoval:
    """The control load taken out of the smeared strips, by part and by span.

    ``camber``/``aoa`` are **per half planform**, like everything else the strip
    loop multiplies by ``k_side``: a symmetric surface's half integrates half the
    load, so it gives up half the control load. Built together with the hinge
    loads in :func:`build_tail_span` from one ``per_side`` value, because the two
    have to be the same number for the cross-mode force identity to hold.
    """

    camber: float          # the LT50-side share, off the 50 % chord line
    aoa: float             # the LT25-side share, off the 25 % chord line
    y_lo: float
    y_hi: float

    @property
    def total(self) -> float:
        return self.camber + self.aoa


def control_attachment(project: Project, component: str,
                       planform: TailPlanform) -> ControlAttachment:
    """The validated hinge/actuator geometry for one surface, or raise.

    Refused loudly and specifically, because every one of these is a modelling
    statement a designer would want to hear about rather than have guessed: no
    geometry at all, one hinge (a hinge line needs two points to be a line),
    a station off the surface, or an actuator outside the span its own hinges
    hold.
    """
    entry = next((tm for tm in project.tail_mass or []
                  if tm.surface == component), None)
    hinges = sorted(entry.hinges_span_in) if entry is not None else []
    actuator = entry.actuator_span_in if entry is not None else 0.0
    if len(hinges) < 2 or not actuator:
        raise MissingInputError(
            f"control_load_mode='discrete' for the {component} needs hinge and "
            "actuator span stations: set tail_mass.hinges_span_in (at least two, "
            "measured from the surface root along its span) and "
            "tail_mass.actuator_span_in. Use 'smeared' to keep the control load "
            "distributed into the surface as it has been.")
    span = planform.span
    off = [h for h in hinges if h < 0.0 or h > span]
    if off:
        raise ValueError(
            f"{component} hinge stations {off} are off the surface, whose span is "
            f"{span:.1f} in from the root -- hinge stations are measured along the "
            "span from the root, not as fuselage stations")
    if not hinges[0] <= actuator <= hinges[-1]:
        raise ValueError(
            f"{component} actuator station {actuator:.1f} in is outside the span "
            f"its hinges hold ({hinges[0]:.1f} to {hinges[-1]:.1f} in). The "
            "actuator reacts the hinge moment of the surface between the hinges; "
            "outside them there is no control surface for it to drive")
    return ControlAttachment(component, tuple(hinges), actuator)


def hinge_chord_fraction(project: Project, cond: CriticalCondition) -> float:
    """``Saft/S`` -- the aft-of-hinge chord as a fraction of the local chord.

    TAILDIST's ``CEAFTHL = (Saft/S)*CAVE`` is that fraction times the *average*
    chord; taken as a fraction it applies at every station of a tapered surface,
    which is what a constant-percent-chord hinge line means. Read from
    :func:`sloads.modules.taildist.surface_geom`, so the spanwise deck and the
    chordwise pressures cannot end up with two different hinge lines.
    """
    from .taildist import surface_geom

    geom = surface_geom(project, cond)
    if geom is None:
        return 0.0
    area_sqin, aft_sqin, _span = geom
    return aft_sqin / area_sqin if area_sqin else 0.0


def derived_control_load(project: Project, cond: CriticalCondition) -> float:
    """The control-surface load integrated from TAILDIST's aft-of-hinge block.

    The fallback for a condition that publishes no control-surface load of its
    own (T-12). It is the oracle-locked chordwise profile, integrated from the
    hinge line aft over the full span::

        L_cs = 0.5 * c_e * psi(hinge line) * span

    -- a triangle, for the reason :data:`HINGE_BLOCK_CENTROID` gives. Derived, and
    marked as derived on the result: it is a first-order stand-in for a number
    SELECT publishes directly on the four conditions that have one.
    """
    from .taildist import chordwise_pressures, surface_geom

    geom = surface_geom(project, cond)
    if geom is None or cond.lt25 is None or cond.lt50 is None:
        return 0.0
    area_sqin, aft_sqin, span_in = geom
    stations = chordwise_pressures(cond.lt25, cond.lt50, area_sqin, aft_sqin, span_in)
    c_e, psi_hinge = stations[3].x, stations[4].psi
    return 0.5 * c_e * psi_hinge * span_in


def control_load_parts(project: Project, cond: CriticalCondition,
                       component: str) -> Tuple[float, float, str]:
    """``(camber share, AoA share, basis)`` of the control-surface load (T-12).

    SELECT's own number where the condition carries one -- ``elevator_load`` for
    the horizontal tail, the rudder load for the fin -- split into the two parts
    it is the sum of, so each can leave the distribution from its own chord
    station. Otherwise the TAILDIST-derived load of
    :func:`derived_control_load`, reported entirely as the camber part, since
    that is the part the control surface's deflection produces and there is
    nothing in a derived scalar to split.
    """
    from .select import elevator_load_parts, rudder_load_parts

    published = _value(cond, "elevator_load" if component == HTAIL
                       else "load_on_rudder")
    if published is not None:
        if component == HTAIL and project.tail_loads is not None:
            cam, att = elevator_load_parts(cond.lt50 or 0.0, cond.lt25 or 0.0,
                                           project.tail_loads)
        elif component == VTAIL and project.vtail_loads is not None:
            cam, att = rudder_load_parts(cond.lt50 or 0.0, cond.lt25 or 0.0,
                                         project.vtail_loads)
        else:                                     # pragma: no cover - guarded above
            cam, att = published, 0.0
        return cam, att, (
            "read from SELECT's own "
            f"{'elevator' if component == HTAIL else 'rudder'} load "
            "(oracle-locked, Ch 9)")
    return derived_control_load(project, cond), 0.0, (
        "DERIVED by integrating TAILDIST's aft-of-hinge pressure block -- this "
        "condition publishes no control-surface load of its own")


def _removal_shares(planform: TailPlanform,
                    removal: Optional[ControlRemoval]) -> List[float]:
    """Per-strip shares of the control load to remove, summing to **exactly 1**.

    Chord-weighted by each strip's *overlap* with the control surface's span, not
    by whether its midpoint happens to fall inside it: a strip that straddles the
    inboard end of an elevator gives up the part of itself the elevator covers,
    which is both right and immune to the station count.
    """
    strips = strip_spans(planform)
    if removal is None:
        return [0.0] * len(strips)
    weights = []
    for s, ds in strips:
        overlap = max(0.0, min(s + ds / 2.0, removal.y_hi)
                      - max(s - ds / 2.0, removal.y_lo))
        weights.append(planform.chord(s) * overlap)
    total = sum(weights)
    if total <= 0:                                # pragma: no cover - validated away
        return [0.0] * len(strips)
    return [w / total for w in weights]


def _hinge_tributaries(attachment: ControlAttachment,
                       planform: TailPlanform) -> List[float]:
    """Chord-weighted tributary shares of one hinge set, summing to exactly 1.

    Midpoints between adjacent hinges, ends at the control surface's own ends --
    the ordinary tributary rule for a line of supports, weighted by local chord
    because the load being shared out is chord-proportional (T-2).
    """
    hinges = attachment.hinges
    lo, hi = attachment.span_extent
    weights = []
    for i, h in enumerate(hinges):
        left = lo if i == 0 else 0.5 * (hinges[i - 1] + h)
        right = hi if i == len(hinges) - 1 else 0.5 * (h + hinges[i + 1])
        weights.append(planform.chord(h) * (right - left))
    total = sum(weights)
    return [w / total for w in weights]


def control_point_loads(planform: TailPlanform, attachment: ControlAttachment,
                        control_load: float, hinge_fraction: float, *,
                        rh_scale: float = 1.0, lh_scale: float = 1.0,
                        z_offset: float = 0.0
                        ) -> Tuple[List[ControlPointLoad], float]:
    """``(attachment loads, hinge moment)`` for one condition (T6).

    ``control_load`` is the whole surface's control load -- both sides for the
    elevator, as every other tail total in this suite is -- and each half takes
    its own ``k_side`` share of half of it, exactly as the strips do.

    Each hinge lands on the LRA line at its span station, carrying its tributary
    share of the load and the torsion that share makes about the LRA from the
    hinge line: ``F * (x_lra - x_hinge_line)``. The actuator lands on the LRA at
    its own station carrying ``-HM``, and the sign is what makes the pair add up:
    hinge torsion plus actuator couple is the control load acting at its own
    centre of pressure, a third of the aft-of-hinge chord behind the hinge line.
    """
    halves: List[Tuple[float, float]] = (
        [(-1.0, lh_scale), (1.0, rh_scale)] if planform.symmetric
        else [(1.0, rh_scale)])
    shares = _hinge_tributaries(attachment, planform)
    per_side = 0.5 * control_load if planform.symmetric else control_load

    out: List[ControlPointLoad] = []
    hinge_moment = 0.0
    for sign, k_side in halves:
        side_load = k_side * per_side
        side_moment = 0.0
        for h, share in zip(attachment.hinges, shares):
            chord = planform.chord(h)
            x_lra = planform.x_at(h, planform.ref_axis_pct)
            x_hinge = planform.x_at(h, 1.0 - hinge_fraction)
            force = side_load * share
            side_moment += force * hinge_fraction * chord * HINGE_BLOCK_CENTROID
            out.append(ControlPointLoad(
                kind="hinge", x=x_lra, y=sign * h, z=z_offset,
                f_normal=force, m_torsion=force * (x_lra - x_hinge)))
        a = attachment.actuator
        out.append(ControlPointLoad(
            kind="actuator", x=planform.x_at(a, planform.ref_axis_pct),
            y=sign * a, z=z_offset, f_normal=0.0, m_torsion=-side_moment))
        hinge_moment += side_moment

    out.sort(key=lambda p: (p.y, p.kind))
    return out, hinge_moment


def control_centre_of_pressure(planform: TailPlanform, s: float,
                               hinge_fraction: float) -> float:
    """Chord station of the control load at span ``s`` -- the hinge line plus a
    third of the aft-of-hinge chord. The identity the cross-mode torsion
    difference is stated against."""
    return (planform.x_at(s, 1.0 - hinge_fraction)
            + hinge_fraction * planform.chord(s) * HINGE_BLOCK_CENTROID)


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
    case = next((c for c in flight_cases(project) if c.name == point.cg), None)
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
    """The control-load mode for one surface (T-4/T5/T6), validated.

    ``"discrete"`` is never quietly downgraded to ``"smeared"``: the two describe
    *different load paths* -- one spreads the control load into the surface, the
    other concentrates it at hinge and actuator stations -- and a deck that
    claimed the second while carrying the first would be wrong in exactly the
    place a designer looks. Selecting it without the attachment geometry it needs
    therefore raises, from :func:`control_attachment`.
    """
    mode = DEFAULT_CONTROL_MODE
    for tm in project.tail_mass or []:
        if tm.surface == component:
            mode = tm.control_load_mode or DEFAULT_CONTROL_MODE
    if mode not in CONTROL_MODES:
        raise ValueError(
            f"unknown control_load_mode {mode!r} for {component}; expected one of "
            f"{CONTROL_MODES}")
    return mode


# --------------------------------------------------------------------------- #
# The T-tail transfer (T7)
# --------------------------------------------------------------------------- #
# On a T-tail the horizontal surface is not attached to the fuselage at all: it
# sits on top of the fin, and every load it carries reaches the airplane *through*
# the fin. Until this step ``TailType.T_TAIL`` drove only the three-view sketch --
# a v-tail deck for a T-tail airplane was the same deck it would have been for a
# conventional one, missing the load its own tip is holding up.
#
# What "concurrent" means is decision T-5: the **balancing** h-tail load at the
# v-tail case's own V-n point, plus the h-tail's inertia at that point's load
# factor. Rational pairing, one deck per fin case. The conservative alternative --
# pairing every fin case with the critical h-tail load whatever condition produced
# it -- is pre-scoped in plan §8 as a selectable policy and deliberately not the
# default, because it pairs loads the airplane never sees together.

def mid_chord_centroid(planform: TailPlanform) -> float:
    """Area-weighted mean chord station of the surface's mid-chord line (in).

    Where a uniformly-smeared surface mass acts chordwise (T-3 spreads it by
    area, so its centroid is the planform's). Integrated over the same strips the
    loads use, so a tapered or swept h-tail moves this station the way it moves
    every other one.
    """
    area = moment = 0.0
    for s, ds in strip_spans(planform):
        da = planform.chord(s) * ds
        area += da
        moment += da * planform.x_at(s, 0.5)
    return moment / area if area else 0.0


def _tail_cp_station(project: Project, case: Optional[int]) -> Tuple[float, bool]:
    """``(chordwise station of the balancing tail load, assumed?)``.

    FLTLOADS publishes the CP it balanced about, per V-n point
    (``TailBalanceLoad.tail_cp_station``), so the transferred moment's lever arm
    is read rather than assumed. The fallback is the 25 % tail MAC -- the station
    the load would act at with no camber -- and it is marked, because a lever arm
    is the whole content of a transfer.
    """
    from .select import default_envelope

    if case is not None:
        for tb in default_envelope(project).tail_balance:
            if tb.case == case:
                return tb.tail_cp_station, False
    ti = project.tail_loads
    return (ti.xt25 if ti is not None else 0.0), True


def ttail_transfer(project: Project, cond: CriticalCondition,
                   htail: Optional[TailPlanform], x_tip: float,
                   points: Sequence["VnPoint"]) -> Optional[TipTransfer]:
    """The h-tail set this fin case carries at its tip, or ``None`` (T7).

    ``None`` -- not a zero set -- when the pairing cannot be resolved: no
    horizontal tail modelled, or a fin condition that names no V-n point and so
    has no concurrent flight condition to read a balancing load from. The
    difference matters: a zero transfer is a claim about the airplane, and this
    is a statement about the data.

    The moment is taken about the fin-tip node in the ``(x_ref - x_load)*F``
    sense :func:`sloads.export.coordinates.tail_torsion_to_airplane` derives, so
    the transferred set and the fin's own strip torsions are in one convention.
    Roll and yaw are zero by T-16: a balancing condition is symmetric, so the
    h-tail's halves cancel about the centreline.
    """
    if htail is None or cond.case is None:
        return None
    point = next((p for p in points if p.case == cond.case), None)
    if point is None:
        return None
    weight = _surface_weight(project, HTAIL)
    x_air, cp_assumed = _tail_cp_station(project, cond.case)
    x_mass = mid_chord_centroid(htail)
    air, inertia = point.lt, -point.nz * weight
    note = (f"T-tail: the horizontal tail's concurrent load rides this fin's tip "
            f"(T-5 pairing -- the balancing load {air:+.0f} lb at V-n case "
            f"{cond.case}, n = {point.nz:.2f}, plus its own inertia "
            f"{inertia:+.0f} lb at {weight:.0f} lb of surface mass)")
    if cp_assumed:
        note += (". Its chordwise station is ASSUMED as the 25 % tail MAC -- the "
                 "V-n point publishes no balanced tail CP")
    if weight <= 0.0:
        note += (". No htail-tagged mass item, so the transferred set is air only")
    return TipTransfer(
        fz=air + inertia,
        myy=(x_tip - x_air) * air + (x_tip - x_mass) * inertia,
        air_lb=air, inertia_lb=inertia, x_air=x_air, x_mass=x_mass, x_tip=x_tip,
        n_case=point.nz, surface_weight_lb=weight, cp_assumed=cp_assumed,
        note=note)


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

        # The discrete control path (T6). Resolved before the notes, because what
        # it finds -- how much control load there is and where its number came
        # from -- is one of the things the result has to say out loud.
        removal: Optional[ControlRemoval] = None
        control_loads: List[ControlPointLoad] = []
        control_load = hinge_moment = hinge_arm = 0.0
        control_basis = ""
        notes = list(planform.notes)
        attach = htail_attachment(project, planform)
        if attach.note:
            notes.append(attach.note)
        if mode == "discrete":
            attachment = control_attachment(project, component, planform)
            fraction = hinge_chord_fraction(project, cond)
            cam, att, control_basis = control_load_parts(project, cond, component)
            control_load = cam + att
            per_side = 0.5 if planform.symmetric else 1.0
            lo, hi = attachment.span_extent
            removal = ControlRemoval(camber=per_side * cam, aoa=per_side * att,
                                     y_lo=lo, y_hi=hi)
            control_loads, hinge_moment = control_point_loads(
                planform, attachment, control_load, fraction,
                rh_scale=rh_scale, lh_scale=lh_scale, z_offset=z_offset)
            # The *applied* total, per-side scaled -- the same treatment
            # ``air_total`` gives the surface load, so the two are comparable on
            # the one condition (23.427(a)) whose sides differ.
            control_load = sum(p.f_normal for p in control_loads)
            hinge_arm = hinge_moment / control_load if control_load else 0.0
            notes.append(
                f"control load DISCRETE: {control_load:+.1f} lb "
                f"({control_basis}) is OUT of the strips over the "
                f"{lo:.1f}-{hi:.1f} in control span and applied at "
                f"{len(attachment.hinges)} hinge stations per side, with the "
                f"hinge moment {hinge_moment:+.0f} lb-in reacted as a couple at "
                f"the actuator ({attachment.actuator:.1f} in)")
            notes.append(
                f"hinge moment arm {hinge_arm:.2f} in = a third of the "
                f"aft-of-hinge chord ({fraction * 100:.1f} % of chord), the "
                "centroid of TAILDIST's aft-of-hinge pressure block")
        else:
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
            z_offset=z_offset, n_normal=n_normal, n_axial=n_axial,
            control_removal=removal)
        # The T-tail transfer rides the *last* fin node, so it is resolved after
        # the stations exist rather than from the planform: the node the deck will
        # actually apply it at is the one whose lever arm has to be right.
        transfer = None
        if component == VTAIL and stations and is_t_tail(project):
            transfer = ttail_transfer(project, cond, planforms.get(HTAIL),
                                      stations[-1].x, vn_points)
            notes.append(transfer.note if transfer is not None else (
                "T-TAIL layout, but the concurrent horizontal-tail load could not "
                "be resolved (no h-tail planform, or this condition names no V-n "
                "point) -- this fin deck carries NO tip transfer, and on a T-tail "
                "that is an omission in the data rather than a load path that "
                "does not exist"))
        out[component].append(TailSpanResult(
            case=cond.label, component=component, stations=stations,
            lt25=cond.lt25, lt50=cond.lt50, n_case=n_case,
            surface_weight_lb=weight, n_y=n_normal if component == VTAIL else 0.0,
            case_weight_lb=case_weight,
            attachment_y=attach.y,
            attachment_assumed=attach.assumed,
            attachment_basis=attach.basis,
            rh_scale=rh_scale, lh_scale=lh_scale,
            planform_assumed=planform.assumed, control_load_mode=mode,
            control_loads=control_loads,
            control_surface_load_lb=control_load,
            control_load_basis=control_basis,
            hinge_moment_lbin=hinge_moment, hinge_moment_arm_in=hinge_arm,
            tip_transfer=transfer,
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
        extra: List[LoadValue] = []
        if r.control_load_mode == "discrete":
            # The suite's first hinge-moment output (T6). Reported as a value in
            # its own right, not only as a card in a deck: it is what a
            # control-system designer sizes an actuator from.
            extra += [
                LoadValue("Control-surface load", r.control_surface_load_lb, "lb",
                          key="control_surface_load"),
                LoadValue("Hinge moment", r.hinge_moment_lbin, "lb-in",
                          key="hinge_moment"),
                LoadValue("Hinge moment arm", r.hinge_moment_arm_in, "in",
                          key="hinge_moment_arm"),
            ]
        if r.tip_transfer is not None:
            t = r.tip_transfer
            extra += [
                LoadValue("T-tail transfer Fz", t.fz, "lb",
                          key="ttail_transfer_fz"),
                LoadValue("T-tail transfer Myy (fin tip)", t.myy, "lb-in",
                          key="ttail_transfer_myy"),
            ]
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
            ] + extra,
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
    "HINGE_BLOCK_CENTROID",
    "ATTACH_FIN_TIP",
    "ATTACH_OUTLINE",
    "ATTACH_STRIP_PAIR",
    "ControlAttachment",
    "ControlRemoval",
    "HTailAttachment",
    "htail_attachment",
    "control_attachment",
    "control_centre_of_pressure",
    "control_load_mode",
    "control_load_parts",
    "control_point_loads",
    "derived_control_load",
    "hinge_chord_fraction",
    "mid_chord_centroid",
    "ttail_transfer",
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
