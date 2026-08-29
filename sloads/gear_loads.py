"""The landing gear as a **free body**: contact patch in, reference point out.

Decision **G-12** (``docs/40_history/23_step10_ground_cases_plan.md``), step 10
piece 3. Conventions: ``docs/10_standard/CONVENTIONS.md``. The reactions
themselves are :mod:`sloads.modules.landing`'s, unchanged and oracle-locked to
Appendix A p230/p236 -- nothing here recomputes one.

One load, delivered twice, for two different readers
----------------------------------------------------
A ground reaction has two consumers who need it in different frames, at different
points, and neither is served well by the other's form:

* the **airframe** wants it at the gear attachment node, in airplane axes, so it
  can be applied to a beam model -- :mod:`sloads.modules.balance` assembles the
  ground cases from exactly that;
* the **gear** wants it at the tyre contact patch, in the ground-line frame, with
  the strut state and ground angle it was computed at -- that is the boundary
  condition a gear analysis starts from, and no previous sloads deliverable
  stated it.

This module owns both, and owns the relationship between them, so the two
artifacts are provably one load seen from two sides rather than two calculations
that happen to agree. The relationship is the deliverable's own drift guard:

    the gear report's reference-point reaction
        == the assembled deck's applied load at the gear node, sign-flipped

which promotes the plan-07 resultant invariant from a hidden test into something
a reader can check by eye.

What it is, and what it is not
------------------------------
This is the **gear interface load definition**. sloads has no gear kinematic
model, so it does not and must not claim drag-brace, side-brace, trunnion or
axle-bending loads. With the contact patch, the components, the ground angle, the
stroke and the reference-point reaction, a gear engineer builds those; without
this artifact they cannot. Overstating it would be the "a wrong card outranks a
missing card" failure in its purest form.

**The leg inertia has a stated limit.** :attr:`GearLegLoad.inertia_fz` is the
leg's own weight at the case's *airplane* vertical load factor, which is what
closes the free body. It is **not** a gear design load: only the unsprung mass --
wheel, tyre, axle, lower oleo -- sees the impact amplification that actually sizes
an axle, and sloads does not model that. :data:`UNSPRUNG_NOTE` is the statement of
record and travels on every rendering.

Three geometry facts the manual already knows, surfaced here
------------------------------------------------------------
**The strut state follows LANDLOAD per attitude** (G-12): the contact patch is
taken from the **compressed** axle for cases 1-12 (level, tail-down, one-wheel)
and the **static** axle for 13-33 (ground roll, side, supplementary nose), each
with its own ground angle. On ``ga6_normal`` the level and ground-roll contact
points differ by 0.49 in in ``x`` and **3.71 in in ``z``** -- 6,706 lb-in of pitch
on the braked-roll drag load -- so following the manual is not a formality.

**The application node does not move.** A trunnion is fixed to the airframe, so
the GIDs are stable across attitudes and the difference lands in the lever arm,
which is where the physics puts it.

**The stroke is more informative than the state names suggest.** Recovered from
the three entered axle positions, ``ga6_normal``'s main leg sits at 24 % of its
7-in stroke in the landing attitudes and 77 % in the handling ones -- impact
versus sitting, which is exactly what a gear analyst needs told.

Frames
------
``GearReactionCase`` carries both resolutions already: the ground-line ("prime")
set ``VMP``/``DMP``/``SMP`` the manual prints, and the airplane-datum set
``vm``/``dm`` it resolves through ``PHIM``/``PHIN``. This module takes each
artifact's own -- it never re-derives the rotation, which would put a second
implementation of ``PHIM`` beside the first. The difference is not cosmetic: on
``ga6_normal`` case 1 the drag is **1,020 lb ground-line against 795 lb
airplane-datum (-22 %)**, and the side family carries 0 lb of ground-line drag
against 186 lb in the airplane datum.

``SMP`` passes through **unrotated** -- it is normal to the pitch rotation --
which is correct but non-obvious, so :func:`ground_rotation_deg` exists to let a
gate assert it rather than let a reader assume it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .frames import rotation_deg
from .models import (
    CaseRef,
    GearCarrier,
    GearReactionCase,
    LandingGearGeometry,
    LandingGearInput,
    LandingInput,
    MissingInputError,
    Project,
)
from .modules.landing import (
    GROUND_ONE_WHEEL_CASES,
    attitude_of,
    build_landing,
    ground_angles,
    side_partner,
)

__all__ = [
    "AXLE",
    "DELIVERED_KEYS",
    "DELIVERED_ORDER",
    "GROUND_CONTACT",
    "LEG_WEIGHT_UNSET_NOTE",
    "MAIN",
    "MAIN_LEFT",
    "MAIN_RIGHT",
    "NOSE",
    "POINTS",
    "UNSPRUNG_NOTE",
    "AppliedWheel",
    "DeliveredLeg",
    "GearCaseLoads",
    "GearLegLoad",
    "application_point",
    "application_point_of",
    "applied_wheels",
    "attitude_of",
    "contact_patch",
    "delivered_gear_legs",
    "delivered_legs",
    "gear_case_loads",
    "ground_rotation_deg",
    "leg_weight",
    "strut_stroke",
    "transfer_couple",
]

#: The two legs of a tricycle gear, as this module names them. Strings rather
#: than an enum because they are also the report's own column values and a
#: ``GearReactionCase`` field prefix; one spelling, here.
MAIN = "main"
NOSE = "nose"

#: The limit on what the leg inertia term means, stated in-band on every surface
#: that renders it (G-12). The *direction* of the shortfall is named, not merely
#: its existence: an axle sees more than this, never less.
UNSPRUNG_NOTE = (
    "the leg inertia below is the leg's own weight at the AIRPLANE vertical load "
    "factor, which is what closes this free body -- it is NOT a gear design "
    "load. Unsprung-mass amplification (wheel, tyre, axle, lower oleo "
    "decelerating against the ground during spin-up and the first of the stroke) "
    "is what actually sizes an axle, and sloads does not model it, so the real "
    "axle inertia is HIGHER than the number here by an amount this suite cannot "
    "quantify")

#: What a leg with no entered weight reports instead of a guess (G-12a).
LEG_WEIGHT_UNSET_NOTE = (
    "no leg weight is entered for this leg, so its inertia term is blank and the "
    "free body below is shown OPEN: the contact-patch load and the "
    "reference-point reaction differ by the leg's own inertia, which on a light "
    "single is around 6 % of the reaction. Enter the leg weight (whole leg, "
    "trunnion down) to close it")

def _axle(leg: LandingGearInput, state: str) -> Tuple[float, float]:
    return {"compressed": leg.axle_compressed,
            "static": leg.axle_static,
            "extended": leg.axle_extended}[state]


def contact_patch(leg: LandingGearInput, state: str,
                  ground_angle_deg: float) -> Tuple[float, float]:
    """The tyre contact patch ``(x, z)`` for one leg in one attitude.

    ``x + r*sin(GRA)``, ``z - r*cos(GRA)`` from the axle at ``state`` -- LANDLOAD's
    own construction (LANDLOAD.BAS lines 50-720, where ``_geometry`` forms the
    ground line from exactly these two expressions), reused here under a single
    owner rather than written out a second time beside the report.
    """
    x, z = _axle(leg, state)
    a = math.radians(ground_angle_deg)
    return (x + leg.rolling_radius_in * math.sin(a),
            z - leg.rolling_radius_in * math.cos(a))


#: The two points LANDLOAD applies a reaction at, spelled as the report prints
#: them (design note 39 AP-1). Strings rather than an enum for the same reason
#: :data:`MAIN`/:data:`NOSE` are: they are also column values.
AXLE = "axle"
GROUND_CONTACT = "ground contact point"

#: Every application point a delivered load may name, as
#: :data:`~sloads.models.LoadValue.point` carries it. A vocabulary rather than
#: free text for :data:`~sloads.frames.FRAMES`' reason (#141): the word rides
#: out to the delivered CSV beside the coordinates, and a typo there is a load
#: delivered to a point that does not exist -- indistinguishable, downstream,
#: from one delivered to the other point. A blank names none and is delivered
#: unannotated, which is the right answer for a load factor or a sink rate.
POINTS = (AXLE, GROUND_CONTACT)

#: **Where each case's reaction acts** -- Appendix A's own printed column, not a
#: choice this replication makes (design note 39, AP-1; the column is transcribed
#: in design note 38 s1.14). p231/p233 head cases 1-12 "CENTER OF EACH WHEEL" and
#: 13-24 "GROUND CONTACT POINT"; p232 heads 25/26, 28/29, 31/32 "CL AXLE" and
#: 27, 30, 33 "GROUND".
#:
#: The split is physical. The level-landing drag is a **spin-up** load -- the
#: patch friction accelerates the wheel's rotation and what the leg carries
#: arrives through the bearing, at the axle -- while braking torque is internal
#: to the wheel/leg free body and leaves the patch force where it acts. That is
#: why applying every case at the patch does not merely relocate ``r x F`` on
#: cases 1-12: it invents it. Measured on the six bundled fixtures, the manual's
#: own unbalanced pitching moment is reproduced to <=62 lb-in at this column's
#: point and missed by 20,964-665,862 lb-in at the other one (note 39 s2).
_GROUND_CONTACT_CASES = frozenset(range(13, 25)) | {27, 30, 33}


def application_point_of(case: int) -> str:
    """:data:`AXLE` or :data:`GROUND_CONTACT` for LANDLOAD case ``case`` (AP-1).

    Raises for a case outside 1-33 for :func:`attitude_of`'s reason: a lookup
    with a fallback answers confidently for a case it has never heard of.
    """
    if not 1 <= case <= 33:
        raise ValueError(f"no application point for LANDLOAD case {case!r} (expected 1-33)")
    return GROUND_CONTACT if case in _GROUND_CONTACT_CASES else AXLE


def application_point(leg: LandingGearInput, case: int, state: str,
                      ground_angle_deg: float) -> Tuple[float, float]:
    """The ``(x, z)`` this case's reaction is applied at, per :data:`AXLE` /
    :data:`GROUND_CONTACT` (AP-2 -- the **one** owner).

    Everything that names a point reads this: the transfer to the reference
    node, the gear free-body report and the landing module's emitted location.
    A load and its point are one statement, and two constructions is how they
    come apart.
    """
    return (contact_patch(leg, state, ground_angle_deg)
            if application_point_of(case) == GROUND_CONTACT
            else _axle(leg, state))


def strut_stroke(leg: LandingGearInput, state: str,
                 stroke_in: float) -> Tuple[float, float]:
    """``(travel from extended, fraction of the entered stroke)`` at ``state``.

    Travel is the straight-line distance from the fully extended axle position to
    the one this attitude is computed at, so a leg that rakes as it compresses is
    measured along its own line rather than in ``z`` alone. The fraction is
    against ``LandingInput.strut_stroke_in``, the same stroke LGFACTOR absorbs the
    landing energy over -- so "24 % of stroke" and the load factor beside it are
    stated against one number.

    Returns a fraction of ``0.0`` when no stroke is entered, rather than dividing
    by it: an unentered stroke is a missing input, and the report says so instead
    of printing an infinity.
    """
    xe, ze = _axle(leg, "extended")
    x, z = _axle(leg, state)
    travel = math.hypot(x - xe, z - ze)
    return travel, (travel / stroke_in if stroke_in else 0.0)


def ground_rotation_deg(case: GearReactionCase) -> float:
    """``rho`` for one LANDLOAD case, from the case's **own two resolutions**.

    The formula and what reads it are :func:`sloads.frames.rotation_deg`; this is
    the case-level wrapper, and what it adds is the answer for a case that does
    not resolve. It falls back to the nose resolution when the main reaction is
    zero, and to ``0.0`` when neither leg carries a reaction -- a case with no
    load has no frame to rotate, and returning an angle from ``atan2(0, 0)``
    would be a number with no meaning behind it.

    Measured on ``ga6_normal``: -4.0570, -15.0003 (tail down) and +4.7253 /
    +4.7239 degrees before the GF-1 sign fix; ``-GRA`` on every attitude after it.
    """
    for datum, prime in (((case.vm, case.dm), (case.vmp, case.dmp)),
                         ((case.vn, case.dn), (case.vnp, case.dnp))):
        if any(datum) or any(prime):
            return rotation_deg(*datum, *prime)
    return 0.0


def transfer_couple(point: Tuple[float, float, float],
                    node: Tuple[float, float, float],
                    force: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """The free moment that moves ``force`` from ``point`` to ``node`` unchanged.

    ``M = (point - node) x F`` -- the plan-14 concentrated-mass offset-couple
    pattern, which is already verified against NETLOADS shear *and* bending in the
    real solver. Force plus this couple at ``node`` has the **identical**
    resultant about every reference as the original force at ``point``, which is
    what makes the transfer a change of description rather than a change of load.

    That is a property of the construction, not an approximation, so its guard is
    exact (``rel_tol 1e-12``) rather than tolerant -- see G-2's third guard.
    """
    rx, ry, rz = (point[0] - node[0], point[1] - node[1], point[2] - node[2])
    fx, fy, fz = force
    return (ry * fz - rz * fy,
            rz * fx - rx * fz,
            rx * fy - ry * fx)


def leg_weight(leg: LandingGearInput) -> Optional[float]:
    """The entered leg weight (lb), or ``None`` when it is not stated (G-12a).

    ``None`` and ``0.0`` are different answers and the distinction is the point:
    a leg whose weight nobody entered has an *unknown* inertia term, and the
    report shows the free body open and says so, rather than closing it against a
    leg that weighs nothing.
    """
    return leg.weight_lb if leg.weight_lb > 0.0 else None


@dataclass(frozen=True)
class GearLegLoad:
    """One leg's free body in one ground case: contact patch in, trunnion out.

    Positions and the reference point are in airplane axes (in); forces in lb and
    moments in lb-in, all **LIMIT** -- the ULTIMATE factor is applied at the
    render/export boundary like every other load quantity in the suite.
    """

    case: int
    description: str
    far_reference: str
    cg_name: str
    leg: str                              # MAIN | NOSE
    #: The tyre contact patch, per this case's attitude -- **geometry**, and the
    #: boundary condition a gear analysis starts from, so it is reported on every
    #: case whether or not the reaction is applied there (design note 39, AP-3).
    patch: Tuple[float, float, float]
    #: **Where the reaction is applied** -- :data:`AXLE` or :data:`GROUND_CONTACT`
    #: per Appendix A's printed column (AP-1), and the point :attr:`couple`
    #: transfers from. Equal to :attr:`patch` on the ground-contact families and
    #: to the axle at this case's strut state on the rest.
    point: Tuple[float, float, float]
    point_name: str                       # AXLE | GROUND_CONTACT
    #: Ground-line ("prime") components at the patch -- the frame the manual
    #: prints and a gear engineer reads: vertical, drag, side.
    ground_line: Tuple[float, float, float]
    #: Airplane-datum components of the same reaction -- the frame the airframe
    #: deck applies. ``SMP`` is common to both (it is normal to the rotation).
    airplane: Tuple[float, float, float]  # (fx, fy, fz)
    #: The attitude this case was computed in.
    strut_state: str                      # "compressed" | "static"
    ground_angle_deg: float
    rotation_deg: float                   # rho, ground line -> airplane datum
    #: Strut travel from fully extended (in) and its fraction of the entered
    #: stroke -- impact versus sitting, which no other deliverable states.
    stroke_in: float
    stroke_fraction: float
    #: The gear reference point (G-2's ``attach``) and how the load gets there.
    node: Tuple[float, float, float]
    carrier: Optional[GearCarrier]
    couple: Tuple[float, float, float]    # the transfer's lever-arm moment
    #: The leg's own inertia at this case's vertical ground-line load factor,
    #: ``None`` when no leg weight is entered (G-12a). See :data:`UNSPRUNG_NOTE`
    #: for what it does and does not mean.
    leg_weight_lb: Optional[float]
    inertia_fz: Optional[float]

    @property
    def reaction(self) -> Tuple[float, float, float]:
        """What arrives at the reference point: the transferred reaction.

        This is the quantity G-13's solver assertion compares against the
        reaction sbeam recovers at the gear GID, sign-flipped -- so it is the
        applied force, **not** net of the leg's own inertia.
        """
        return self.airplane

    @property
    def net_of_inertia(self) -> Optional[Tuple[float, float, float]]:
        """The reaction less the leg's own inertia -- the free body closed.

        ``None`` when the leg weight is not stated. This is what the *structure
        above the trunnion* sees; :attr:`reaction` is what the deck applies at the
        node, with the leg's mass carried separately by the mass model. Both are
        reported, because they answer different questions and reporting one as
        the other is how a 6 % error gets into a fitting.
        """
        if self.inertia_fz is None:
            return None
        fx, fy, fz = self.airplane
        return (fx, fy, fz - self.inertia_fz)


@dataclass(frozen=True)
class GearCaseLoads:
    """One LANDLOAD case's legs, in report order (main then nose)."""

    case: int
    description: str
    far_reference: str
    cg_name: str
    #: The design weight this case is computed at -- ``WL``, not the named
    #: loading's own weight on cases 13-22 (see ``GearReactionCase.weight_lb``).
    weight_lb: float
    #: LANDLOAD's own minted identity for the case (``LG-01`` ... ``LG-33``), so
    #: the report, the assembled deck and the case index all join on one id.
    case_ref: Optional[CaseRef]
    legs: Tuple[GearLegLoad, ...]


def _leg_load(case: GearReactionCase, leg_name: str, leg: LandingGearInput,
              inp: LandingInput, gear: LandingGearGeometry,
              gra: Sequence[float]) -> GearLegLoad:
    state, gra_index = attitude_of(case.case)
    angle = gra[gra_index]
    px, pz = contact_patch(leg, state, angle)
    ax, az = application_point(leg, case.case, state, angle)
    stroke, fraction = strut_stroke(leg, state, inp.strut_stroke_in)
    rho = ground_rotation_deg(case)

    if leg_name == MAIN:
        v, d, s = case.vmp, case.dmp, case.smp
        fz, fx = case.vm, case.dm
        # The main gear is a pair; the patch is reported at the starboard wheel
        # and its twin is the mirror. ``tread`` is a wheel dimension and is the
        # right one *here* -- it is the trunnion butt line it must never be
        # confused with (decision G-2).
        py = gear.tread_in / 2.0
    else:
        v, d, s = case.vnp, case.dnp, case.snp
        fz, fx = case.vn, case.dn
        py = 0.0

    patch = (px, py, pz)
    point = (ax, py, az)
    node = (leg.attach[0], leg.attach[1], leg.attach[2])
    force = (fx, s, fz)
    weight = leg_weight(leg)
    return GearLegLoad(
        case=case.case, description=case.description,
        far_reference=case.far_reference, cg_name=case.cg_name,
        leg=leg_name, patch=patch, point=point,
        point_name=application_point_of(case.case),
        ground_line=(v, d, s), airplane=force,
        strut_state=state, ground_angle_deg=angle, rotation_deg=rho,
        stroke_in=stroke, stroke_fraction=fraction,
        node=node, carrier=leg.carrier,
        # From the **applied** point, not the patch: on cases 1-12 the two are a
        # rolling radius apart and the difference is a pitching moment the
        # airplane never sees (AP-1/AP-4 -- the force is untouched, the arm is
        # what was wrong).
        couple=transfer_couple(point, node, force),
        leg_weight_lb=weight,
        # The leg rides the airplane's own vertical ground-line factor. ``NVP`` is
        # zero on the 23.499 family (25-33), which carries no airplane
        # equilibrium at all, so those rows report no inertia rather than zero.
        inertia_fz=(weight * case.nvp if weight is not None and case.nvp else None),
    )


def gear_case_loads(project: Project) -> List[GearCaseLoads]:
    """Every LANDLOAD case as a gear free body -- **all 33** (G-6's amendment).

    The assembled deck carries 24: the 23.499 supplementary-nose family is a local
    gear-design case with no main-gear reaction and therefore no airplane in
    equilibrium, so it is skipped there with a recorded reason. It belongs *here*,
    though -- cases 25-33 are gear-design cases and this report is where they were
    always aimed. **The two artifacts carry different case sets by design.**

    Raises when the project has no gear geometry, which is the honest answer:
    ``concept_heavy`` has neither a ``landing`` slice nor gear geometry, so it
    produces no gear report at all rather than an empty one (backlog: giving it
    both is cheap fixture data and buys a sixth fixture).
    """
    geom = project.geometry
    lg = geom.landing_gear if geom is not None else None
    if lg is None:
        raise MissingInputError(
            "the gear load report needs landing-gear geometry: set "
            "geometry.landing_gear (the axle positions at the three strut "
            "states, rolling radius and tread).")
    inp = project.landing
    if inp is None:
        raise MissingInputError("the gear load report needs the 'landing' input slice")
    _, reactions = build_landing(project)
    gra = ground_angles(inp, lg)

    out: List[GearCaseLoads] = []
    for case in reactions:
        legs = tuple(_leg_load(case, name, leg, inp, lg, gra)
                     for name, leg in ((MAIN, lg.main_gear), (NOSE, lg.nose_gear)))
        out.append(GearCaseLoads(
            case=case.case, description=case.description,
            far_reference=case.far_reference, cg_name=case.cg_name,
            weight_lb=case.weight_lb, case_ref=case.case_ref, legs=legs))
    return out


@dataclass(frozen=True)
class AppliedWheel:
    """One wheel's reaction, transferred and ready to apply at its own node.

    The assembled deck's view of :class:`GearLegLoad`: which side of the airplane
    the wheel is on, the gear reference point its load is delivered to, the
    airplane-datum force, and the lever-arm couple that made the transfer exact.
    """

    leg: str
    side: str                              # "R" | "L" | "C"
    node: Tuple[float, float, float]
    force: Tuple[float, float, float]
    couple: Tuple[float, float, float]
    carrier: Optional[GearCarrier]
    #: This wheel's contact patch (geometry, AP-3) and the point its reaction is
    #: applied at (AP-1) -- equal on the ground-contact families, a rolling
    #: radius apart on the rest. The couple transfers from :attr:`point`.
    patch: Tuple[float, float, float]
    point: Tuple[float, float, float]


def applied_wheels(legs: Sequence[GearLegLoad], *, one_wheel: bool = False,
                   partner_side_lb: Optional[float] = None) -> List[AppliedWheel]:
    """The wheels a **balanced** ground case applies, from its legs' free bodies.

    Where :class:`GearLegLoad` is per *leg* -- LANDLOAD's own presentation, one
    main row carrying the per-wheel reaction -- an assembled case needs the
    airplane: two main wheels at ``+-tread/2``, or one, and each on its own node.

    ``one_wheel`` drops the port main wheel for the 23.483 family, where a single
    main gear carries the whole reaction. The case then has a hand, which
    :func:`sloads.modules.balance.is_handed` finds for itself from the rolling
    moment the placement makes -- it is not declared here.

    ``partner_side_lb`` is the 23.485 family's second wheel. ``GearReactionCase``
    carries a **single** ``SMP``, while the side condition puts *different* side
    loads on the two wheels -- 0.5 W inboard on one and 0.33 W outboard on the
    other (23.485(c)) -- which act in the **same** global direction and sum to the
    0.83 W that ``NS`` states. So the assembler reads the partner case's ``SMP``
    for the second wheel rather than re-deriving the percentages, and the port
    wheel takes ``-partner_side_lb``: the sign flip is what turns the manual's
    two *inboard/outboard* statements into one global side load. Absent, both
    wheels take the leg's own side load, which is zero on every other family.
    """
    out: List[AppliedWheel] = []
    for leg in legs:
        if not any(leg.airplane) and not any(leg.couple):
            continue                       # this leg carries nothing in this case
        fx, fy, fz = leg.airplane
        if leg.leg == NOSE:
            out.append(AppliedWheel(leg.leg, "C", leg.node, leg.airplane,
                                    leg.couple, leg.carrier, leg.patch, leg.point))
            continue
        ax, ay, az = leg.node
        px, py, pz = leg.patch
        qx, qy, qz = leg.point
        wheels = [("R", (ax, ay, az), (px, py, pz), (qx, qy, qz), fy)]
        if not one_wheel:
            port_fy = -partner_side_lb if partner_side_lb is not None else fy
            wheels.append(("L", (ax, -ay, az), (px, -py, pz), (qx, -qy, qz), port_fy))
        for side, node, patch, point, side_lb in wheels:
            force = (fx, side_lb, fz)
            # The transfer is from the **applied** point (AP-1/AP-2), which is
            # the axle on the landing attitudes; ``patch`` rides along as the
            # gear-side geometry it always was (AP-3).
            out.append(AppliedWheel(
                leg.leg, side, node, force,
                transfer_couple(point, node, force), leg.carrier, patch, point))
    return out


#: The three gear legs a delivered ground case names, in report order (design
#: note 38 GF-6). ``MAIN``/``NOSE`` are LANDLOAD's own two *legs* -- one main row
#: carrying the per-wheel reaction; these are the three *wheels* an airplane
#: stands on, which is what a stress model needs and what makes a case's free
#: body readable without reconstructing which gear the family implies.
MAIN_LEFT = "main left"
MAIN_RIGHT = "main right"
DELIVERED_ORDER = (NOSE, MAIN_LEFT, MAIN_RIGHT)

#: ``LoadValue`` key stems, in the same order. The emitted keys are
#: ``<stem>_fx`` / ``_fy`` / ``_fz`` for the force and ``_x`` / ``_y`` / ``_z``
#: for the point it acts at.
DELIVERED_KEYS = {NOSE: "nose", MAIN_LEFT: "main_left", MAIN_RIGHT: "main_right"}


@dataclass(frozen=True)
class DeliveredLeg:
    """One wheel of a ground case as the deliverable states it: force and point.

    A load and its point of application are **one statement** (design note 39):
    a magnitude with no point is not a load, and moving the point silently
    changes every moment downstream. So this carries both, in the airplane datum
    -- the frame a beam model applies -- together with the attitude the point was
    taken at and the gear reference point the leg delivers to.

    ``force`` is **LIMIT**, like every other calc-layer load quantity; the
    ultimate factor is applied once at the render/export boundary.

    A wheel this case does not load is present with a zero force rather than
    absent (GF-6): three legs on every case, always.
    """

    name: str                              # NOSE | MAIN_LEFT | MAIN_RIGHT
    #: This leg's ``LoadValue`` key stem, from :data:`DELIVERED_KEYS` -- carried
    #: on the record so the producing module names the keys without importing
    #: back into this one (``modules.landing`` is what ``gear_loads`` reads).
    key_stem: str
    force: Tuple[float, float, float]      # airplane-datum Fx, Fy, Fz (lb, LIMIT)
    point: Tuple[float, float, float]      # where it acts (in)
    point_name: str                        # AXLE | GROUND_CONTACT
    node: Tuple[float, float, float]       # the gear reference point (G-2)
    strut_state: str                       # "compressed" | "static"

    @property
    def carries_load(self) -> bool:
        """Whether this wheel is loaded at all in this case."""
        return any(self.force)


def _mirrored(point: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x, y, z = point
    return (x, -y, z)


def delivered_legs(case: GearCaseLoads, *, partner_side_lb: Optional[float] = None
                   ) -> Tuple[DeliveredLeg, ...]:
    """The three wheels of one ground case, in :data:`DELIVERED_ORDER`.

    Built **from** :func:`applied_wheels` rather than beside it, so the delivered
    statement and the assembled deck cannot come to differ: every loaded wheel
    here is the same wheel, with the same force and the same point, that the deck
    applies. What this adds is the wheels ``applied_wheels`` drops -- the port
    main of a 23.483 one-wheel case, both mains of the 23.499 supplementary-nose
    family, the nose wheel of every case that lifts it clear -- which it emits at
    zero, with its point and node still stated. An unloaded gear is a fact about
    the case, and omitting it makes the reader reconstruct the family's rule.

    ``partner_side_lb`` is the 23.485 family's second wheel, as
    :func:`applied_wheels` documents; :func:`delivered_gear_legs` supplies it
    from the pairing :func:`sloads.modules.landing.side_partner` owns.
    """
    one_wheel = case.case in GROUND_ONE_WHEEL_CASES
    wheels = {(w.leg, w.side): w
              for w in applied_wheels(case.legs, one_wheel=one_wheel,
                                      partner_side_lb=partner_side_lb)}
    by_leg = {leg.leg: leg for leg in case.legs}
    out: List[DeliveredLeg] = []
    for name, kind, side, mirror in ((NOSE, NOSE, "C", False),
                                     (MAIN_LEFT, MAIN, "L", True),
                                     (MAIN_RIGHT, MAIN, "R", False)):
        leg = by_leg[kind]
        wheel = wheels.get((kind, side))
        if wheel is not None:
            force, point, node = wheel.force, wheel.point, wheel.node
        else:
            force = (0.0, 0.0, 0.0)
            point = _mirrored(leg.point) if mirror else leg.point
            node = _mirrored(leg.node) if mirror else leg.node
        out.append(DeliveredLeg(name=name, key_stem=DELIVERED_KEYS[name],
                                force=force, point=point,
                                point_name=leg.point_name, node=node,
                                strut_state=leg.strut_state))
    return tuple(out)


def delivered_gear_legs(cases: Sequence[GearCaseLoads]
                        ) -> "Dict[int, Tuple[DeliveredLeg, ...]]":
    """:func:`delivered_legs` for a whole 33-case matrix, keyed by case number.

    The list is needed rather than the case alone because the 23.485 side family
    puts a *different* side load on each of the two wheels -- 0.5 W inboard and
    0.33 W outboard, acting the same way globally -- and LANDLOAD carries the
    second one on the paired case rather than on this one.
    """
    by_case = {c.case: c for c in cases}
    out: "Dict[int, Tuple[DeliveredLeg, ...]]" = {}
    for c in cases:
        partner = side_partner(c.case)
        twin = by_case.get(partner) if partner is not None else None
        out[c.case] = delivered_legs(
            c, partner_side_lb=twin.legs[0].ground_line[2] if twin else None)
    return out
