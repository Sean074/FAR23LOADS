"""Balanced free-free airplane cases -- wing tip to wing tip, nose to tail.

Plan 11 (``docs/30_future/11_balanced_airframe_cases_plan.md``) step **B2**,
decisions B-1…B-5. Conventions: ``docs/10_standard/CONVENTIONS.md``.

The goal, in the user's words: *a full airplane balanced case with no need for a
constraint, because the loads balance.* The airplane already balances at trim --
``flight_envelope._balance`` closes ``LZW + LT = Nz*W`` exactly, and
``test_concept_closure`` has asserted it for a long time. What was missing is
that the **distributed** loads never inherited that balance: the wing
distribution, the tail load, the fuselage inertia and the trim solve were four
separate calculations that nothing assembled.

This module assembles them and reports what is left over.

Three things had to be got right, and each was measured rather than assumed
-------------------------------------------------------------------------
**1. A cumulative torsion is not a free moment.** ``WingStationLoad.myy`` is the
torsion about the *root* 25 % chord, and it already contains the sweep and
dihedral transfer of outboard shear inboard (``tyy``/``tvyy`` in
``airloads.py``). Assembling from it *and* applying the strip's position offset
counts the transfer twice: on ``ga6_normal`` PHAA that puts the pitching-moment
residual at **20.5 %** of ``n*W*MAC`` instead of 0.15 %. Only the section
pitching moment ``ml`` is a free moment, and :func:`_free_moments` recovers it by
subtracting the two transfer accumulations back out.

**2. The wing load must be at the balanced case's own flight condition.** The
entered ``wing_mass.cases`` carry a hand-written ``cl``/``v_eas_kt`` that is a
*different condition* from the V-n point SELECT pairs them with -- ``atr42_100``
enters CL 1.55 at 170 kt against its V-n point's 1.7283 at 185.85 kt. Assembling
the two halves then compares different flight conditions, and the force residual
runs 10-37 % of ``n*W``. So the wing distribution is **recomputed at the V-n
point's own** ``cl``/``v``/``nz`` (:func:`wing_sets`). The entered distributions
are untouched and remain the FAR 23 deliverables -- this adds a case, it does not
change one, and no Appendix A oracle moves.

**3. The mass model is the items, not WINGINER's own.** Wing inertia comes from
the ``WING``-tagged items of the case's derived loading (step B1/C1) -- read as
**reacted parts** (:func:`~sloads.mass_distribution.reacted_parts`, design note
29), so a fuel row partly carried by the wing contributes its wing share here and
its body share to :func:`body_inertia` -- spread over WINGINER's spanwise shape --
decision B-2 and plan 11 §4. Taking it from
``wing_mass.panel_weight_lb + concentrated`` instead double-counts anything that
is in both models: on ``atr42_100`` and ``dhc8_dash8`` the wing-tank fuel is, and
the residual runs 12-13 % rather than 1.9 %.

What the assembled case carries, and what it must not
-----------------------------------------------------
The seam rule (plan 11 §4), stated once: **a load that a free-body cut
introduces is never applied in the assembled model.** Each per-component deck
takes a cut and carries the cut reaction as an applied load; in the assembled
model the solver recovers it. Concretely the wing carry-through reaction
(``BodyStationLoad.source == "carry"``) is *excluded* -- :func:`assemble` never
reads ``body_loads``, and :func:`carry_sources_absent` is the guard.

The fuselage pitching moment
----------------------------
The trim carries ``Cm`` for the airplane **less tail** -- wing *and* fuselage --
while the distributed wing carries only its own section ``Cm``. The difference is
the fuselage's Munk moment, and it has no distributed carrier until backlog item
M4-19 lands the Multhopp/Nelson body moment. It is applied here as a single free
moment on the fuselage (``source="fuselage-cm"``), which preserves the total
exactly and is labelled as lumped wherever it is rendered. Omitting it would
leave a moment residual of the same size for the closure to absorb silently -- a
real aero load disguised as a correction.

Its size is **not** a small positive constant. Measured across the fixtures that
have flight cases it runs **-6.6 to +4.9 %** of ``n*W*MAC`` on ``ga6_normal`` and
**-8.5 to +5.8 %** on ``concept_regional_jet``, and it changes sign -- with
``alpha``, as a slope term must (``NMAA`` is the negative-``alpha`` case on the
ga6). An earlier "+4.3 to +6.3 %, positive" reading here was taken over the
symmetric wing conditions only and did not survive the negative-``alpha`` and
lateral points (corrected 2026-08-15).

Residual closure (B-3)
----------------------
Whatever is left is closed as mass-proportional inertia relief in two decoupled
degrees of freedom -- ``delta_n`` on every mass, and a pitch term
``+k*(x_i - x_cg)*w_i``. They do not fight each other: the pitch term sums to
zero force because ``sum(w_i*(x_i - x_cg)) == 0`` by the definition of the CG,
and the ``delta_n`` term sums to zero moment for the same reason. Both magnitudes
are recorded on the result, and the gate is on the residual **before** closure --
the physics, not the correction.

The antisymmetric cases (B7)
----------------------------
**Only ``ACRL`` is antisymmetric, and it is measured, not assumed.** The
handedness of a wing case lives entirely in ``WingLoadCase.unbal_moment`` (UNB,
FAR 23.349), and UNB is non-zero on ``ACRL`` alone -- ``ga6_normal`` -149,043
in-lb, ``concept_regional_jet`` -600,000, zero everywhere else including
``TORS`` on every fixture. That is not a fixture accident: a *steady* roll has no
unbalanced rolling moment by definition (the aileron moment is balanced by roll
damping), and the up-going/down-going aero asymmetry that remains has no
spanwise representation anywhere in this suite. ``TORS`` is therefore assembled
as the symmetric case it is, and :func:`test_only_acrl_carries_roll` pins that
finding so a fixture that ever enters a non-zero UNB for it goes red.

**The applied couple is lumped; the reaction is distributed.** WINGINER's model
-- the one Appendix A is locked to -- never distributes the aileron's own lift
increment: it takes only the *inertia reaction* to the roll acceleration UNB
causes (``fz_r``, the unit-roll distribution). The assembled case matches that
exactly: the aero rolling moment enters as a single labelled free couple at the
wing aerodynamic centre (``source="aileron-roll"``, the same treatment and the
same honesty as ``fuselage-cm``), and the distributed antisymmetric load the
wing actually carries comes out of the **roll degree of freedom of the closure**.
The consequence is stated wherever the case is rendered: the aileron's spanwise
lift increment is not modelled, because ``AileronLoadsInput`` carries areas and
no butt lines (filed in the backlog).

**And that closure is checkable against an independent producer.** Closing the
roll residual with ``k_roll*w_i*y_i`` -- physically ``-m_i*p_dot*y_i``, the roll
analog of the pitch term, decoupled from all three symmetric DOF because
``sum(w_i*y_i) == 0`` for a mirror-symmetric mass model -- reproduces WINGINER's
``ur*fz_r`` distribution **strip for strip**: ratio 1.000000 on both fixtures,
with the wing-item/panel scale cancelling identically. Two producers, one answer:
WINGINER's oracle-locked recurrence and this module's ``p_dot`` solve. That
identity is the B7 closure gate (``test_roll_closure_reproduces_winginer``),
standing in for the printed oracle concept mode does not have.

The lateral cases (B8a)
-----------------------
Plan 13 (``docs/30_future/13_b8a_lateral_closure_plan.md``), decisions L-1…L-8.
SELECT's four rational v-tail conditions -- sudden rudder, yaw to sideslip, yaw
15 neutral, side gust -- assemble as balanced cases too, and they are the first
lateral load factors this suite has ever produced. All four sit on V-n points at
``n_z ~ 1``, so the vertical/longitudinal/pitch half is the symmetric machinery
unchanged; what is added is the fin's distributed side load (:func:`fin_sets`)
and the three lateral degrees of freedom of the closure B8a-2 built.

**Nothing balances a rudder kick, and nothing is supposed to.** In the symmetric
case aero and inertia nearly cancel and a residual over 1 % means something is
missing. Laterally there is nothing to cancel against: the pre-closure ``Fy`` and
``Mz`` residuals **are** the fin load, in full, by construction. So
:data:`RESIDUAL_GATE` does not apply to them -- the same standing as ``ACRL``'s
roll residual -- and the gate that does is that the case's *symmetric half*, with
the fin load removed, still closes inside 1 %.

**The fin is the only lateral aero the suite computes** (decision L-7). Fuselage
and wing side force in sideslip exist on the airplane and nowhere in these 22
programs, and the two degrees of freedom they are missing from err in **opposite
directions**. The body's yawing couple is destabilizing and opposes the fin's, so
the yaw acceleration is **over-stated** and the inertia it drives is
conservative. The body-and-wing side force, however, acts the *same* way as the
fin's restoring load at ``+beta`` -- it **adds** -- so ``n_y`` is
**under-stated** and the lateral translational inertia it drives is **not**
conservative. Neither is the airplane's real acceleration. That is said in-band,
on every lateral case, through :data:`LATERAL_AERO_NOTE`. Both magnitudes are
stated as *unknown*, because quantifying them is building the missing model
(backlog L-7); this is the weaker of the suite's two honesty statements and is
not dressed up as the stronger one (the lumped fuselage ``Cm``, whose size can be
quoted).

The unsymmetrical horizontal tail (D-R8)
---------------------------------------
Decision **D-R8** (2026-08-10), review finding **F-R5**. FAR **23.427(a)** is the
one horizontal-tail condition with a genuine hand: SELECT takes the
largest-magnitude symmetric tail load and puts 100 % of half of it on one side
and ``pc = min(100 - 10(n-1), 80)`` percent on the other. Every other h-tail
condition is symmetric and already rides the wing cases as the trim tail load
``vn.lt``; this one has left/right content that a lumped centreline force cannot
carry, and the full-span tail topology (plan 09 decision T-8) was built for it.

**The applied tail load is SELECT's own, and it replaces the trim load** rather
than adding to it: ``RH + LH`` *is* the condition's total tail load, and applying
``vn.lt`` beside it would count the balancing part twice. The h-tail strips come
from :func:`htail_sets`, the exact analogue of :func:`fin_sets` -- air only, with
the surface's mass left in :func:`body_inertia` to ride the closure field, so
each mass still enters exactly one set.

**The pre-closure residual is the maneuver, not an error.** The 23.427(a) load is
a *maneuver* load (the unchecked maneuver governs on both fixtures that assemble)
and its V-n point is a balanced one at ``n_z ~ 1``, so the airplane is genuinely
not in trim: on ``ga6_normal`` the applied tail load is -1204.7 lb against a trim
-177.7, and the difference -- 49.8 % of ``n*W``, 144 % of ``n*W*MAC`` -- comes out
as ``delta_n = -0.496 g`` and ``q_dot = +637 deg/s^2``. That is what an abrupt
elevator input does, and closing it in the pitch degree of freedom is the
standard treatment of an unbalanced pitching maneuver, not a correction applied
to a broken balance. :data:`RESIDUAL_GATE` therefore does not apply to this
family's ``Fz``/``My`` either -- the same standing as the lateral cases -- and the
gate that does is that the case's **trim half**, with the 23.427(a) set replaced
by the lumped ``vn.lt``, still closes inside it
(``test_the_trim_half_of_an_unsymmetrical_case_still_closes``).

Two independent producers check what is applied: the set's per-side sums are
SELECT's own ``RH``/``LH`` to the last digit, and its rolling moment about the
centreline is the closed form ``(RH - LH) * y_bar`` with ``y_bar`` the
chord-weighted centroid of the half planform -- ratio 1.000000000 on both
fixtures.

**The twins come from reflection, not recomputation** (decisions B-6/B-7). Every
case with antisymmetric content is emitted as a handed pair, the port case being
the mirror image of the starboard one through
:func:`sloads.export.coordinates.reflect_load`. The FAR 23 core never sees
handedness; the id gains an ``L``/``R`` suffix and the unhanded id remains the
physical condition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from math import cos, degrees, pi, radians, sin
from typing import Dict, List, Optional, Sequence, Tuple

from ..case_ids import handed_case_id
from ..cg_cases import flight_cases, ground_cases, landing_role_cases
from ..constants import POLAR_TRUSTED_ALPHA_DEG
from ..derived_geometry import body_drag_waterline, sync_geometry_derived
from ..export.coordinates import (
    reflect_force,
    reflect_moment,
    reflect_point,
    reflect_side,
    tail_force_to_airplane,
    tail_station_to_airplane,
    tail_torsion_to_airplane,
)
from ..gear_loads import GearCaseLoads, applied_wheels, gear_case_loads
from ..mass_distribution import (
    CaseLoading,
    MassComponent,
    assembly_distributes_mass,
    component_of,
    derive_case_loadings,
    reacted_parts,
)
from ..models import (
    AeroInput,
    BalancedCaseResult,
    BalancedLoad,
    CgCase,
    FlightLoadsInput,
    GeometryInput,
    LandingInput,
    MissingInputError,
    ModuleResult,
    Project,
    TailSpanResult,
    VnPoint,
    WingLoadResult,
    WingMassInput,
)
from ..registry import register
from ..rigid_body import (
    InertiaTensor,
    PointMass,
    SelfInertia,
    inertia_tensor,
    radians_per_s2,
    relief_force,
    relief_moment,
)
from ..tail_geometry import HTAIL, VTAIL
from .airloads import air_load_distribution
from .select import default_critical, default_envelope
from .tail_span import build_tail_span
from .wing_inertia import inertia_units, resolve_wing_cases

MODULE_NAME = "balance"

#: Wing conditions whose load set is symmetric about the centreline. ``TORS``
#: joined this list at B7 **by measurement**: its ``unbal_moment`` is zero on
#: every fixture, because a steady roll has no unbalanced rolling moment (see the
#: module docstring). Assembling it as symmetric is therefore not an
#: approximation -- it is what the case contains.
SYMMETRIC_WING_CONDITIONS = ("PHAA", "PLAA", "PMAA", "NMAA", "TORS")

#: Wing conditions that may carry an unbalanced rolling moment, hence a handed
#: pair. Membership here does **not** by itself make a case antisymmetric: a
#: condition whose ``unbal_moment`` is zero assembles symmetrically and is minted
#: unhanded, so the twins never appear for a case that has no hand.
ROLLING_WING_CONDITIONS = ("ACRL",)

#: Every wing condition the assembled deck covers.
BALANCED_WING_CONDITIONS = SYMMETRIC_WING_CONDITIONS + ROLLING_WING_CONDITIONS

#: SELECT's four rational vertical-tail conditions (FAR 23.441 maneuver, 23.443
#: gust), each assembled as a **lateral** balanced case at B8a-3. All four sit on
#: V-n points at ``n_z ~ 1``, so the vertical/longitudinal/pitch half of the case
#: is the shipped symmetric machinery unchanged and only the applied set grows.
#: ONENGOUT's 23.367 conditions are deliberately absent: that is a transient, not
#: a balanced steady case (plan 13 §4).
BALANCED_VTAIL_CONDITIONS = ("SUDDEN RUDDER", "YAW TO SIDESLIP",
                             "YAW 15 NEUTRAL", "SIDE GUST")

#: The horizontal-tail conditions assembled as balanced cases (D-R8) -- the
#: 23.427(a) unsymmetrical load and nothing else, because it is the only h-tail
#: condition with a hand. The symmetric ones are *already* in the deliverable, as
#: the trim tail load ``vn.lt`` of every wing case's balanced assembly; giving
#: them a second assembled case would put the same physics in the deck twice
#: under a different name (:data:`SKIP_REASONS` ``htail-symmetric`` says so on
#: the record rather than dropping them silently).
BALANCED_HTAIL_CONDITIONS = ("UNSYMMETRICAL",)

#: Acceptance gate (plan 11 §6): the residual **before** closure, as a fraction
#: of ``n*W`` for force and ``n*W*MAC`` for moment.
#:
#: **It does not apply laterally, and that is physics rather than an exemption**
#: (plan 13 §2). A symmetric case's aero and inertia nearly cancel, so a residual
#: above 1 % means something is missing. A rudder kick has *nothing to cancel
#: against*: the fin load is reacted by inertia alone, so the pre-closure lateral
#: residual **is** the whole fin load by construction -- the same standing as
#: ``ACRL``'s roll residual, which plan 11 §10 already records. The lateral gate
#: is instead that the case's **symmetric half** still closes inside this bound
#: with the fin load removed (``test_the_symmetric_half_still_closes``).
RESIDUAL_GATE = 0.01

#: Applied lateral content below this fraction of ``n*W`` is summation noise, not
#: a hand (decision L-6). It serves the rolling test of :func:`is_handed` too,
#: against ``n*W*(b/2)``: the margin there is fifteen orders of magnitude -- a
#: mirror-symmetric applied set nets 1e-17 of ``n*W*b/2`` in roll, and the
#: 23.427(a) h-tail case 6e-3 to 1.7e-2 -- so one threshold serves both.
HANDEDNESS_TOL = 1e-9

#: The B7 statement of record for the lumped aileron couple, carried in-band on
#: every ``ACRL`` case (the case's ``notes``, hence the deck header and the UI)
#: and in the report's standing limitations (review F-R4) — one wording for both,
#: because the deck and the controlling document must not caveat the same
#: modelling choice differently. The couple's *magnitude* is per case and is
#: stated beside this sentence; what is standing is the modelling choice.
AILERON_COUPLE_NOTE = (
    "the suite has no aileron spanwise geometry, so its own lift increment is "
    "not distributed (WINGINER carries only the inertia reaction, which IS "
    "distributed here)")

#: The L-7 statement of record, carried in-band on every lateral case: on the
#: result's ``notes``, hence in the deck header and the UI. The *direction* of
#: the error is stated per degree of freedom, not merely its existence, because
#: the two directions differ (2026-08-15 defect fix): the missing body yawing
#: couple opposes the fin's, so ``psi_dd`` is over-stated and its inertia is
#: conservative; the missing body-and-wing side force ADDS to the fin's, so
#: ``n_y`` is UNDER-stated and its inertia is not. Both magnitudes stay
#: *unknown* here -- they are measurable (design note
#: ``docs/30_future/19_l7_lateral_body_aero_note.md`` §7 puts ``|n_y|`` 4-12 %
#: low on the one fixture with body geometry) but no shipped code computes them,
#: and a number in a deck header must be one this tool can reproduce. Quoting
#: them is part of backlog L-7, which replaces this sentence outright.
LATERAL_AERO_NOTE = (
    "the fin is the only lateral aerodynamic load this suite computes -- "
    "fuselage and wing side force in sideslip are not modelled, and the two "
    "lateral degrees of freedom err in OPPOSITE directions: the yaw "
    "acceleration is OVER-STATED and the inertia it drives is conservative, "
    "while n_y is UNDER-STATED -- the missing side force adds to the fin's -- "
    "so the lateral translational inertia it drives is NOT conservative on any "
    "component; both by an unknown amount. The fin's own design load is "
    "SELECT's, unchanged")


# --------------------------------------------------------------------------- #
# The skipped-conditions record (review F-C7)
# --------------------------------------------------------------------------- #
#: Reason codes :func:`build_balanced_cases` records against a condition it did
#: not assemble. The code is the stable identity (tests and consumers key on it);
#: the sentence beside it is what the reader gets.
#:
#: ``out-of-family`` is a *deliberate* exclusion and the rest are gaps in the
#: project's inputs, but both are recorded: the deliverable's honesty statement
#: is "here is every condition SELECT named and what became of it", and a silent
#: exclusion reads exactly like a condition that was never named.
#:
#: The wording is **reader-facing prose, not diagnostics**: these sentences reach
#: the controlling document (report §4) as well as the deck, and the report's rule
#: is that its reader is an analyst rather than a maintainer -- so no input-slice
#: or constant names appear here.
SKIP_REASONS = {
    "out-of-family": (
        "not one of the balanced families this analysis assembles -- fuselage "
        "and one-engine-out conditions are covered by the per-component "
        "analyses only"),
    "gear-design-only": (
        "a supplementary nose-wheel condition (FAR 23.499): it carries nose "
        "reactions only, with no main-gear reaction anywhere in the family, so "
        "it is a local gear-design case rather than an airplane in equilibrium "
        "and there is nothing for a balanced case to balance. It is not "
        "missing from the deliverable -- the gear load report carries it, with "
        "all thirty-three cases"),
    "side-twin-by-reflection": (
        "the opposite drift direction of the side-load case before it (FAR "
        "23.485), which this analysis produces by REFLECTING that case rather "
        "than assembling it a second time -- so it is in the deck, under its "
        "own case id, as the twin. Assembling both would put two handedness "
        "mechanisms in one step; deriving it instead gives the reflection "
        "operator the one independent check it has, against the manual's own "
        "figures for this case"),
    "htail-symmetric": (
        "a symmetric horizontal-tail condition: it is already in every balanced "
        "case, as the trim tail load the assembled airplane is balanced against, "
        "so only the 23.427(a) unsymmetrical condition -- the one with a "
        "left/right hand -- is assembled as a case of its own"),
    "no-htail-loads": (
        "no horizontal-tail spanwise load distribution is available for it, so "
        "there is no unsymmetrical tail load to assemble the case around"),
    "no-fin-loads": (
        "no vertical-tail spanwise load distribution is available for it, so "
        "there is no fin side load to assemble the case around"),
    "no-vn-point": (
        "its V-n point is not in the flight envelope, so the case has no "
        "flight condition to be assembled at"),
    "no-cg-case": (
        # "source case", not "V-n point": this reason is reached by the ground
        # family too, whose case number is LANDLOAD's (R6-C3). The condition's
        # own name, beside it in the record, says which table it numbers into.
        "its source case names a loading this project does not define, so the "
        "case has no weight or CG"),
    "loading-not-derivable": (
        "its payload loading is not derivable from the itemized weight "
        "database -- a CG the items cannot actually produce has no honest "
        "inertia set, and inventing one would put fictitious mass into the "
        "very balance the case exists to demonstrate"),
}


@dataclass(frozen=True)
class SkippedCondition:
    """One condition SELECT named that :func:`build_balanced_cases` did not
    assemble, and why (review F-C7).

    Not persisted and not a schema type: it is a statement *about* a run, minted
    with the cases and travelling beside them onto the ``ModuleResult``, the deck
    ``$`` block and the report. ``code`` is the stable machine identity (a key of
    :data:`SKIP_REASONS`); ``reason`` is the sentence rendered.
    """
    component: str
    label: str
    case: Optional[int]
    code: str
    reason: str
    #: Which table :attr:`case` numbers into -- LANDLOAD's for a ground
    #: condition, FLTLOADS' V-n for a flight one (R6-C3). Carried rather than
    #: inferred from ``component`` so the record states its own family, and
    #: defaulted to the flight family because that is what a skip minted from a
    #: SELECT condition is.
    ground: bool = False

    @property
    def name(self) -> str:
        """The condition, named as the family that produced it names it."""
        where = (f" ({source_case_name(self.case, self.ground, short=True)})"
                 if self.case is not None else "")
        return f"{self.component} {self.label}{where}"


def _skip(cond, code: str) -> SkippedCondition:
    return SkippedCondition(component=cond.component, label=cond.label,
                            case=cond.case, code=code, reason=SKIP_REASONS[code],
                            ground=isinstance(cond, _GroundCondition))


# --------------------------------------------------------------------------- #
# Free moments -- undoing AIRLOADS' cumulative transfer
# --------------------------------------------------------------------------- #
def _free_moments(result: WingLoadResult) -> List[float]:
    """Per-strip **free** pitching moment (the section ``Cm`` term alone).

    ``AIRLOADS`` accumulates ``myy = tyy + tvyy + trq``: the sweep transfer of
    outboard shear (``tyy``), the dihedral transfer of outboard drag (``tvyy``)
    and the section pitching moment (``trq``). Only the last is a free moment;
    the other two are position transfers that an assembly applies for itself.
    Both are reconstructed here from the station table by the same recurrence
    ``airloads`` builds them with, and subtracted back out.

    On ``ga6_normal`` PHAA the root torsion is -79,003 lb-in, of which -60,474 is
    sweep transfer and -9,594 dihedral -- so the free moment is -8,935, and using
    the -79,003 figure as if it were free is the 20 % error.
    """
    s = result.stations
    h = len(s)
    tyy = [0.0] * h
    tvyy = [0.0] * h
    for i in range(h - 2, -1, -1):
        tyy[i] = tyy[i + 1] - s[i + 1].sz * (s[i + 1].x - s[i].x)
        tvyy[i] = tvyy[i + 1] + s[i + 1].sx * (s[i + 1].z - s[i].z)
    trq = [s[i].myy - tyy[i] - tvyy[i] for i in range(h)]
    return [trq[i] - (trq[i + 1] if i + 1 < h else 0.0) for i in range(h)]


# --------------------------------------------------------------------------- #
# The applied sets
# --------------------------------------------------------------------------- #
def reflect_load(load: BalancedLoad) -> BalancedLoad:
    """One load's mirror image through the centreline plane (decision B-6).

    Every component goes through the single owner in
    :mod:`sloads.export.coordinates`, including the ones that are zero today, so
    the sign convention lives in exactly one place and the lateral families of
    B8a inherit it already checked.
    """
    x, y, z = reflect_point(load.x, load.y, load.z)
    fx, fy, fz = reflect_force(load.fx, load.fy, load.fz)
    mx, my, mz = reflect_moment(load.mx, load.my, load.mz)
    return replace(load, x=x, y=y, z=z, fx=fx, fy=fy, fz=fz,
                   mx=mx, my=my, mz=mz, side=reflect_side(load.side))


def _mirror(loads: Sequence[BalancedLoad]) -> List[BalancedLoad]:
    """The port-side image of a starboard set.

    The *geometric* half of building a full-span airplane out of a half-span
    calculation -- distinct from :func:`reflect_load`'s use in
    :func:`handed_twin`, which mirrors a whole assembled case to get its
    opposite-hand twin. Same operator either way, which is the point of giving it
    one owner.
    """
    return [reflect_load(ld) for ld in loads]


def _wing_slices(project: Project) -> Tuple[WingMassInput, GeometryInput, AeroInput]:
    """The three slices every wing set reads, present -- or the module's refusal.

    :func:`run` checks ``wing_mass`` at entry; the helpers below are also called
    directly (ground cases, tests), so the same refusal lives here once instead
    of an ``AttributeError`` at the first dereference.
    """
    wm, geometry, aero = project.wing_mass, project.geometry, project.aero
    if wm is None or geometry is None or aero is None:
        raise MissingInputError("balance needs 'wing_mass', 'geometry' and 'aero'")
    return wm, geometry, aero


def _flight_loads(project: Project) -> FlightLoadsInput:
    fl = project.flight_loads
    if fl is None:
        raise MissingInputError("balance needs 'flight_loads'")
    return fl


def wing_sets(project: Project, vn: VnPoint) -> Tuple[List[BalancedLoad], float, float]:
    """Starboard wing air + inertia loads, at ``vn``'s own flight condition.

    Returns ``(loads, wing_item_weight, cm_free_total)`` where ``cm_free_total``
    is the section-``Cm`` free moment of **both** wings -- the caller needs it to
    work out the fuselage's share of the trim moment.
    """
    wm, geometry, aero_in = _wing_slices(project)
    geom = geometry.by_name(wm.surface)
    aero = aero_in.by_name(wm.surface)
    base = next((c for c in resolve_wing_cases(project, wm)), None)
    if geom is None or aero is None or base is None:
        raise MissingInputError("balance needs a wing surface, aero set and load case")

    air = air_load_distribution(geom, aero, vn.cl, vn.v_eas_kt,
                                wm.wrp_waterline, wm.dihedral_deg)
    ml = _free_moments(air)
    loads = [
        BalancedLoad(x=s.x, y=s.y, z=s.z, fx=s.fx, fz=s.fz, my=ml[i],
                     source="wing-air", side="R")
        for i, s in enumerate(air.stations)
    ]
    cm_free = 2.0 * math.fsum(ml)

    inertia, panel_both = wing_inertia_strips(project, vn.nz)
    return loads + inertia, panel_both, cm_free


def wing_inertia_strips(project: Project,
                        nz: float) -> Tuple[List[BalancedLoad], float]:
    """Starboard wing inertia strips at load factor ``nz``, plus the panel mass.

    Returns ``(strips, panel_weight_both_sides)``, **centred on their own
    centroid** -- :func:`place_wing_inertia` is what moves them onto the loading's
    WING items and scales them to it. The two halves are separate because the
    ground families need the same shape at ``nz = 0`` (their load factor is
    solved, not given: decision G-6), and a second copy of this construction
    beside them is the drift ``CLAUDE.md`` practice 3 forbids.

    Inertia strips take WINGINER's **spanwise shape** at the 50 % chord (where it
    models the panel mass CG -- its torsion carries ``-w*(c50x - c25x)`` for
    exactly that reason).

    The split of authority is decision B-2: the item database owns *where* the
    mass is, WINGINER owns *how it is spread along the span*. Without the shift
    the two disagree -- ga6's wing item sits at x 97.87 while the 50 % chord line
    runs 78-95 -- and the difference lands in the pitching residual as a moment
    the trim does not have, because the trim lumps all mass at the CG. It is
    worth 2.8-4.3 % of ``n*W*MAC`` on ``concept_regional_jet``.

    A strip carries ``weight_lb`` whatever ``nz`` is, which is what lets a ground
    case work: at ``nz = 0`` the strips apply no force and the closure field
    accelerates them, so the wing's mass is in the model exactly once either way.
    """
    wm, geometry, _ = _wing_slices(project)
    geom = geometry.by_name(wm.surface)
    if geom is None:
        raise MissingInputError(f"balance: wing surface {wm.surface!r} is not in 'geometry'")
    u = inertia_units(geom, wm)
    panel = math.fsum(u.w)
    strips = [(i, w) for i, w in enumerate(u.w) if w]
    if strips and panel:
        x_shape = math.fsum(w * u.c50x[i] for i, w in strips) / panel
        z_shape = math.fsum(w * u.z[i] for i, w in strips) / panel
    else:
        x_shape = z_shape = 0.0
    return ([BalancedLoad(x=u.c50x[i] - x_shape, y=u.ye[i], z=u.z[i] - z_shape,
                          fz=-w * nz, weight_lb=w, source="wing-inertia", side="R")
             for i, w in strips], 2.0 * panel)


def place_wing_inertia(loads: Sequence[BalancedLoad], loading: CaseLoading,
                       project: Project,
                       panel_both: float) -> Tuple[List[BalancedLoad], List[str]]:
    """Scale ``loads``' wing inertia onto the loading's WING items and place it.

    The other half of :func:`wing_inertia_strips`: WINGINER supplies the spanwise
    shape, the item database supplies the mass and where its centroid sits
    (decision B-2), and this is where the two are married. Returns the loads with
    every ``wing-inertia`` strip scaled and shifted, plus the notes the scale owes
    the reader -- a scale that is not 1.0 means the two mass models disagree, and
    the case says by how much rather than absorbing it.
    """
    notes: List[str] = []
    scale = _wing_inertia_scale(loading, project, panel_both)
    if scale == 0.0:
        notes.append("the loading carries no WING-tagged item mass -- "
                     "wing inertia not modelled")
    elif abs(scale - 1.0) > 1e-6:
        notes.append(
            f"wing inertia scaled x{scale:.4f} onto the loading's WING items "
            f"({scale * panel_both:.0f} lb); WINGINER's integrated panel mass is "
            f"{panel_both:.0f} lb")
    wing_items = [it for it in reacted_parts(loading.items, project)
                  if component_of(it, project) == MassComponent.WING]
    w_wing = math.fsum(it.weight_lb for it in wing_items)
    x_wing = (math.fsum(it.weight_lb * it.x for it in wing_items) / w_wing) if w_wing else 0.0
    z_wing = (math.fsum(it.weight_lb * it.z for it in wing_items) / w_wing) if w_wing else 0.0
    return ([replace(ld, fz=ld.fz * scale, weight_lb=ld.weight_lb * scale,
                     x=ld.x + x_wing, z=ld.z + z_wing)
             if ld.source == "wing-inertia" else ld
             for ld in loads], notes)


def _wing_inertia_scale(loading: CaseLoading, project: Project,
                        panel_both_sides: float) -> float:
    """Factor bringing WINGINER's panel mass onto the loading's WING item weight.

    Decision B-2: the items are the mass SSOT, and WINGINER supplies the *shape*.
    Where the two models already agree the factor is exactly 1.0 (``ga6_normal``
    330 = 2 x 165); where they do not it is what stops the disagreement becoming
    a load.

    **The partition gate (review F-C5).** WING-tagged items are excluded from
    :func:`body_inertia` precisely because the wing set carries them, so a wing
    set scaled to zero would delete their whole weight from the model and let
    the closure absorb it silently. When the loading has WING items and WINGINER
    integrates no panel at all there is no spanwise shape to put them on, and
    that is an inconsistent input rather than a load case: it raises. Only a
    loading with **no** WING item mass scales to 0.0, and then nothing is lost
    -- :func:`assemble` notes that case.
    """
    wing_items = math.fsum(it.weight_lb for it in reacted_parts(loading.items, project)
                     if component_of(it, project) == MassComponent.WING)
    if panel_both_sides <= 0.0:
        if wing_items:
            raise MissingInputError(
                f"the loading carries {wing_items:.0f} lb of WING-tagged items but "
                "the wing mass model integrates no panel mass "
                "(wing_mass.panel_weight_lb = 0): there is no spanwise shape to "
                "distribute them over. Enter a panel weight, or retag the items "
                "onto a component the fuselage beam carries")
        return 0.0
    return wing_items / panel_both_sides


def body_inertia(loading: CaseLoading, project: Project,
                 nz: float) -> List[BalancedLoad]:
    """Inertia of everything the wing does not carry, at each item's own station.

    The wing enters the fuselage as the carry-through *reaction*, which the
    assembled model's solver recovers -- so no ``carry`` load appears here, and
    none may (plan 11 §4).

    "What the wing does not carry" is asked through
    :func:`~sloads.mass_distribution.assembly_distributes_mass`, the same
    predicate :func:`point_mass_self_inertia` uses, so the set of items carried
    as points and the set contributing a self-inertia free moment cannot drift
    apart (decision L-3).
    """
    return [
        BalancedLoad(x=it.x, y=it.y, z=it.z, fz=-it.weight_lb * nz,
                     weight_lb=it.weight_lb, source="body-inertia", side="C")
        for it in reacted_parts(loading.items, project)
        if not assembly_distributes_mass(component_of(it, project))
    ]


def body_axial_set(loads: Sequence[BalancedLoad], project: Project,
                   vn: VnPoint, loading: CaseLoading,
                   ) -> Tuple[float, float, bool, List[BalancedLoad], List[str]]:
    """The airplane's **non-wing** drag: ``(applied, dCD, clamped, loads, notes)``.

    Design note: ``docs/30_future/20_body_drag_carrier_note.md``.

    The FLTLOADS trim balances the airplane-less-tail drag from the **polar**
    (``aero_curves.drag_cd``, the ``CD(CL)`` polynomial the project enters);
    the assembled model's only ``fx`` is the wing strips' own chordwise force
    (``airloads``: section profile drag plus the lifting-line induced drag,
    resolved with lift through the case ``alpha``). The difference is the
    fuselage, the nacelles and every other non-wing parasite contribution, and
    before this it was simply absent -- ``residual_fx`` *equalled* the wing
    strips' sum, and the couple the missing force left about the CG was the
    whole of the pre-closure pitch residual.

    That it is genuinely parasite drag, and not a bookkeeping artefact, is
    measurable: both the trim and the strips resolve through the same ``alpha``,
    so the body-axis gap splits exactly into wind-axis parts,

        dD = dFx*cos(a) + dFz*sin(a)        dL = dFz*cos(a) - dFx*sin(a)

    and ``dL/L`` comes out <= 0.6 % everywhere while ``dD/(q*S)`` is a near
    constant **-0.018 across all seven** ``ga6_normal`` cases -- a ``CD`` offset
    independent of ``CL``, which is what a missing parasite term looks like and
    what a lift-model disagreement does not.

    ``dCD`` is returned as that **wind-axis** increment rather than the axial one
    (the two differ by the negligible ``dL*sin(a)`` tilt), because the physical
    content of the diagnostic is the drag-coefficient offset.

    **Sign.** ``CONVENTIONS.md`` §1: ``x`` is +aft, so both ``vn.dx`` and the
    strips' ``fx`` are already body-axis ``x`` forces and the correction is a
    subtraction in one frame, needing no rotation. Positive is aft, i.e. drag.

    **A forward value is a defect in one of the two drag models, not a load**
    (D-4 as revised 2026-08-17, backlog Pri 2). Where it appears is what
    decides the treatment, and the deciding quantity is the trim's ``alpha``
    against the polar's trusted window :data:`~sloads.constants.POLAR_TRUSTED_ALPHA_DEG`
    (:func:`polar_alpha_trusted`):

    * **outside the window** the polar is being read where it was never fitted
      -- above it the strip model's induced drag overshoots
      (``concept_regional_jet``, +20/+22 deg), below it the fit is 13 deg under
      zero lift (``NMAA`` on the three crudest-polar fixtures) -- so a forward
      difference is **not applied**: no ``body-axial`` card, ``body_axial`` = 0,
      ``body_axial_clamped`` set, and the raw value in the note. ``dCD`` is
      still computed and reported from the unclamped difference, so the G10
      diagnostic keeps its signal; ``residual_fx`` re-opens by exactly the
      clamped amount on those cases and only those, and the G1/G5 gates read
      the same flag. Revision 1 of D-4 refused to clamp because that would
      "reopen ``residual_fx`` and hide the overshoot"; it hid neither once the
      window is stated and ``dCD`` stays reported, and it put a forward
      "drag" of 1.0-1.4 klb on three ``NMAA`` decks (backlog Pri 2).
    * **inside the window** both models are trusted, so a forward value cannot
      be excused: it is applied as computed **and** noted, and
      ``tests/test_balance.py``'s G10 gate fails on it -- the fixture's aero
      data is wrong, not the assembly.

    **Placement.** The waterline is the single owner
    :func:`~sloads.derived_geometry.body_drag_waterline` and is the only free
    parameter here (decision D-1). The fuselage station reaches no gate -- a pure
    axial force contributes ``my = (z-zcg)*fx`` with no ``x`` term -- so it is
    spread over the body outline by cross-section-area share where one exists,
    and lumped at the body masses' own centroid where it does not. Both are
    stated; neither can move a number.
    """
    fl = _flight_loads(project)
    wing_fx = math.fsum(ld.fx for ld in loads if ld.source == "wing-air")
    wing_fz = math.fsum(ld.fz for ld in loads if ld.source == "wing-air")
    total = vn.dx - wing_fx
    if not total:
        return 0.0, 0.0, False, [], []

    # The wind-axis drag increment, for the G10 consistency diagnostic.
    a = radians(vn.alpha_deg)
    q_psf = vn.v_eas_kt ** 2 / 295.0
    qs = q_psf * fl.wing_area_sqft
    delta_cd = ((-total) * cos(a)
                + (wing_fz - vn.lzw) * sin(a)) / qs if qs else 0.0

    wl = body_drag_waterline(project)
    notes: List[str] = []
    if wl.note:
        notes.append(wl.note)
    if total < 0.0:
        lo, hi = POLAR_TRUSTED_ALPHA_DEG
        if not polar_alpha_trusted(vn.alpha_deg):
            side = "above" if vn.alpha_deg > hi else "below"
            notes.append(
                f"the non-wing axial force comes out FORWARD ({total:+,.0f} lb; "
                f"dCD = {delta_cd:+.5f}) at alpha {vn.alpha_deg:+.1f} deg, "
                f"{side} the polar's trusted window ({lo:+.0f}, {hi:+.0f}) deg, "
                f"where the airplane-less-tail polar and the strip model are "
                f"not both trusted: NOT applied (dCD reported unclamped; "
                f"residual_fx re-opens by this amount) -- design note 20 D-4 "
                f"as revised 2026-08-17")
            return 0.0, delta_cd, True, [], notes
        notes.append(
            f"the non-wing axial force is FORWARD ({total:+,.0f} lb; dCD = "
            f"{delta_cd:+.5f}) INSIDE the polar's trusted window "
            f"({lo:+.0f}, {hi:+.0f}) deg -- the fixture's aero data is "
            f"inconsistent where both drag models are trusted; applied as "
            f"computed and flagged (D-4)")

    stations = _body_drag_stations(project, loading)
    if not stations:
        return total, delta_cd, False, [], [
            *notes, "the non-wing drag has no body station to act at and is NOT applied"]
    notes.append(
        f"non-wing drag {total:+,.0f} lb applied at waterline {wl.z:.1f} "
        f"({wl.basis}) over {len(stations)} body station(s); dCD = {delta_cd:+.5f}")
    return total, delta_cd, False, [
        BalancedLoad(x=x, y=0.0, z=wl.z, fx=total * frac,
                     source="body-axial", side="C")
        for x, frac in stations
    ], notes


def polar_alpha_trusted(alpha_deg: float) -> bool:
    """Is the trim ``alpha`` inside the polar's trusted window?

    The one predicate on :data:`~sloads.constants.POLAR_TRUSTED_ALPHA_DEG`,
    read by :func:`body_axial_set` and by the G10 gate in ``tests/test_balance.py``
    so the code and the test cannot disagree about where a forward non-wing
    force is a defect (inside) and where it is an untrusted difference that
    is not applied (outside).
    """
    lo, hi = POLAR_TRUSTED_ALPHA_DEG
    return lo <= alpha_deg <= hi


def _body_drag_stations(project: Project,
                        loading: CaseLoading) -> List[Tuple[float, float]]:
    """``[(x, fraction)]`` the body-axial load is spread over; sums to 1.0.

    Cross-section-area share over the fuselage outline where there is one -- each
    interior station taking half of each adjoining trapezoidal segment, so the
    ends are not over-weighted -- else a single station at the body masses' own
    centroid. Neither choice can move a gate (see :func:`body_axial_set`); the
    outline branch exists so the deck's axial load path is physical where the
    geometry supports one.
    """
    outline = project.geometry.fuselage if project.geometry is not None else None
    sections = list(outline.sections) if outline is not None else []
    if len(sections) >= 2:
        area = [pi / 4.0 * s.width * s.height for s in sections]
        w = [0.0] * len(sections)
        for i in range(len(sections) - 1):
            seg = 0.5 * (area[i] + area[i + 1]) * (sections[i + 1].x - sections[i].x)
            w[i] += 0.5 * seg
            w[i + 1] += 0.5 * seg
        total = math.fsum(w)
        if total > 0.0:
            return [(s.x, wi / total) for s, wi in zip(sections, w) if wi]
    body = [it for it in reacted_parts(loading.items, project)
            if not assembly_distributes_mass(component_of(it, project))]
    weight = math.fsum(it.weight_lb for it in body)
    if weight:
        return [(math.fsum(it.x * it.weight_lb for it in body) / weight, 1.0)]
    return []


def fin_sets(result: TailSpanResult) -> List[BalancedLoad]:
    """The fin's distributed side load, in airplane axes (decision L-6, plan 13 §2).

    A pure consumer of :mod:`sloads.modules.tail_span`, which is itself a pure
    consumer of SELECT -- so the load a lateral balanced case carries is the
    Appendix-A-locked side load, strip for strip, and no oracle is at risk from
    assembling it. What this function adds is the **frame change**, and it makes
    it through the single owner in :mod:`sloads.export.coordinates` rather than
    by hand:

    * the fin's span is ``z``, so a station at span ``s`` sits at
      ``z = root_waterline + s`` -- the waterline B8a-1 gave it, without which
      the roll moment ``-Fy*(z - z_cg)`` comes out with the wrong **sign** on
      ``ga6_normal`` (plan 13 §3.3);
    * the fin's normal force is a **side** force, ``fy``, not ``fz``;
    * the fin's torsion is about its span axis, so it is ``mz``, and it is the
      **negated** stored value -- the derivation is in
      :func:`~sloads.export.coordinates.tail_torsion_to_airplane`.

    The set is air only, and deliberately: fin **inertia** rides in the closure
    field at the case's own ``n_y``/``omega_dot``, through the ``VTAIL``-tagged
    mass items :func:`body_inertia` already carries (decision L-8).

    Which is why the strip's air load is taken as ``fz - f_inertia`` rather than
    as ``fz``. Since the tail-mass SSOT step the per-condition fin deck carries
    its own lateral inertia, and reading the net here would apply the fin's mass
    **twice** in an assembled case -- once relieving the applied side load, once
    in the closure field. The seam is the same one the wing's carry-through has,
    and it is held the same way: each mass enters exactly one set.
    """
    loads: List[BalancedLoad] = []
    for st in result.stations:
        x, y, z = tail_station_to_airplane(st.x, st.y, VTAIL, root_z=st.z)
        fx, fy, fz = tail_force_to_airplane(st.fz - st.f_inertia, VTAIL)
        mx, my, mz = tail_torsion_to_airplane(st.myy_free, VTAIL)
        loads.append(BalancedLoad(x=x, y=y, z=z, fx=fx, fy=fy, fz=fz,
                                  mx=mx, my=my, mz=mz,
                                  source="vtail-air", side="C"))
    return loads


def htail_sets(result: TailSpanResult) -> List[BalancedLoad]:
    """The horizontal tail's distributed load, in airplane axes (D-R8, F-R5).

    :func:`fin_sets`' sibling, and deliberately built the same way: a pure
    consumer of :mod:`sloads.modules.tail_span`, which is a pure consumer of
    SELECT, so the 23.427(a) load an assembled case carries is SELECT's own
    RH/LH split strip for strip and no oracle is at risk from assembling it.

    The frame change goes through the single owner in
    :mod:`sloads.export.coordinates`, with ``component=HTAIL``: the h-tail's span
    is ``y``, so a station sits at its own span coordinate on both halves of the
    full-span table (plan 09 decision T-8); its normal force is vertical, so it
    is ``fz``; and its torsion is about the ``y`` axis, so it is a free ``my``,
    the stored value unchanged. The strips carry the tail's waterline in ``z``,
    which is where they are, not the trim load's reference plane.

    **Air only**, exactly as the fin set is: the surface's mass items stay in
    :func:`body_inertia` and are accelerated by the closure field, so the tail's
    weight enters the case once. Reading the strips' net ``fz`` instead would
    apply it twice, once as the per-condition deck's own d'Alembert term and once
    in the relief.

    The ``side`` tag is the half of the airplane the strip is on -- which is what
    ``side`` has always meant, the wing being the only carrier of it until now --
    so :func:`reflect_load` swaps the two halves when the port twin is minted.
    """
    loads: List[BalancedLoad] = []
    for st in result.stations:
        x, y, z = tail_station_to_airplane(st.x, st.y, HTAIL, root_z=st.z)
        fx, fy, fz = tail_force_to_airplane(st.fz - st.f_inertia, HTAIL)
        mx, my, mz = tail_torsion_to_airplane(st.myy_free, HTAIL)
        loads.append(BalancedLoad(x=x, y=y, z=z, fx=fx, fy=fy, fz=fz,
                                  mx=mx, my=my, mz=mz,
                                  source="htail-air", side="R" if y > 0 else "L"))
    return loads


def is_unsymmetrical_htail(case: BalancedCaseResult) -> bool:
    """Does this case carry the distributed 23.427(a) tail load? (D-R8)

    The ``htail-air`` tag has one reader -- here -- so the deck header, the case
    table, the report and the gates all agree on what the family *is*, the same
    single-owner rule :func:`is_lateral` follows for the fin.
    """
    return any(ld.source == "htail-air" for ld in case.loads)


def htail_load(case: BalancedCaseResult) -> float:
    """The **net** applied horizontal-tail load; ``0.0`` when there is no set.

    Equal to SELECT's ``RH + LH`` for a 23.427(a) case, which is the identity the
    composition gate asserts. Use :func:`is_unsymmetrical_htail` to ask whether
    the case *has* the set: a tail load that happened to sum to zero would still
    be one, because it is the distribution that is handed.
    """
    return math.fsum(ld.fz for ld in case.loads if ld.source == "htail-air")


def htail_side_loads(case: BalancedCaseResult) -> Tuple[float, float]:
    """``(starboard, port)`` halves of the applied h-tail load -- SELECT's own
    ``RH``/``LH`` on the computed case, and swapped on its port twin.

    Split by the strip's side of the centreline rather than by its ``side`` tag,
    so the two agree only because the tag is right -- a reflection that failed to
    swap the tags would show up here rather than being echoed back.
    """
    rh = math.fsum(ld.fz for ld in case.loads if ld.source == "htail-air" and ld.y > 0)
    lh = math.fsum(ld.fz for ld in case.loads if ld.source == "htail-air" and ld.y < 0)
    return rh, lh


def is_ground(case: BalancedCaseResult) -> bool:
    """Does this case carry applied gear reactions? (i.e. is it a ground case.)

    The ``gear-*`` tag has one reader -- here -- so the deck header, the case
    table, the report and the gates all agree on what the ground family *is*, the
    same single-owner rule :func:`is_lateral` follows for the fin and
    :func:`is_unsymmetrical_htail` for the 23.427(a) tail.

    It matters most to the gates. A ground case has **nothing to trim against**,
    so :data:`RESIDUAL_GATE` -- which asks "did the aero and inertia that should
    have cancelled actually cancel?" -- has no meaning for it: the pre-closure
    residual is the whole applied gear load by construction, exactly as a rudder
    kick's is the whole fin load. The gate that does apply is G-6's, and it is
    stronger: the solved rigid-body field, rotated back to the ground line, must
    reproduce LANDLOAD's ``NVP``/``NDP``/``NS`` -- which it does exactly.
    """
    return any(ld.source.startswith("gear-") for ld in case.loads)


#: What the integer in :attr:`BalancedCaseResult.vn_case` actually names, by
#: family (R6-C3). The field holds the **source case number**: FLTLOADS' V-n
#: point for a flight case, LANDLOAD's case number for a ground one -- two
#: different tables that both number from 1, so a label naming the wrong one
#: sends a reader to a real and unrelated row.
FLIGHT_SOURCE_STEM = "V-n point"
GROUND_SOURCE_STEM = "LANDLOAD case"


def source_case_name(case_number: int, ground: bool, *,
                     short: bool = False) -> str:
    """The source case, named as the family that produced it names it (R6-C3).

    **The one owner of this wording.** Every surface that prints the number --
    the assembled deck's ``$`` header and case map, :func:`run`'s condition
    titles, the balanced-case rows table and :attr:`SkippedCondition.name` --
    goes through here, so none of them can drift into calling a LANDLOAD case a
    V-n point again. Display wording only: the number and the case identity are
    untouched (the join key is the ``CaseRef`` id, not this string).

    ``short`` is the compact form the case map and the parenthesised titles use.
    The ground stem has no short form on purpose -- abbreviating it would invent
    a fourth name for the same number, and it is the family that was being
    mislabelled.
    """
    if ground:
        return f"{GROUND_SOURCE_STEM} {case_number}"
    stem = "V-n" if short else FLIGHT_SOURCE_STEM
    return f"{stem} {case_number}"


def case_source_name(case: BalancedCaseResult, *, short: bool = False) -> str:
    """:func:`source_case_name` for an assembled case, family read off the case."""
    return source_case_name(case.vn_case, is_ground(case), short=short)


def is_lateral(case: BalancedCaseResult) -> bool:
    """Does this case carry an applied fin load? (i.e. is it one of B8a-3's.)

    The ``vtail-air`` tag has exactly one reader -- here and in
    :func:`fin_load` -- so the deck header, the row table and the gates all agree
    on what a lateral case *is* (``CLAUDE.md`` practice 3). Asked of the tag and
    not of :func:`fin_load`'s net, because a fin set whose strips happened to sum
    to zero would still be a lateral case: it is the distribution that is
    handed, not the resultant (the same distinction :func:`is_handed` draws).
    """
    return any(ld.source == "vtail-air" for ld in case.loads)


def fin_load(case: BalancedCaseResult) -> float:
    """The **net** applied fin side load; ``0.0`` when there is no fin set.

    The number the deck reports and the gates pin. Use :func:`is_lateral` to ask
    whether the case *has* a fin set.
    """
    return math.fsum(ld.fy for ld in case.loads if ld.source == "vtail-air")


def is_handed(applied: Sequence[BalancedLoad], n_w: float,
              ref_length: float = 0.0) -> bool:
    """Does this **applied** load set have a hand? (decision L-6, D-R8)

    Three sources of handedness, and the third is what D-R8 added: a free
    ``mx``/``mz`` (the aileron couple), lateral force content (a fin load), and a
    **net rolling moment made by the distribution itself** -- which is the only
    thing the 23.427(a) h-tail case has. Its asymmetry is 100 % of half the tail
    load on one side against 72-80 % on the other, all of it in ``fz`` at
    opposite ``y``: no side force, no free moment, and a predicate reading only
    the first two would mint it unhanded and emit one twin where 23.427(a)
    requires both sides considered.

    ``ref_length`` is the semi-span the rolling moment is judged against; with
    none supplied there is no length scale to form a fraction from, so the roll
    test is skipped rather than run against a number whose units decide the
    answer. :func:`assemble` always supplies it.

    Two properties, both deliberate and both lost by the obvious alternatives:

    **It reads the distribution, not the resultant.** ``ga6_normal``'s
    ``YAW TO SIDESLIP`` nets only -97.8 lb of side force out of parts worth
    -683 (yaw) and +586 (rudder), so ``sum|fy| ~ 1270`` while ``|sum fy| ~ 98``.
    A net-based predicate would mint a rudder-kick case *unhanded* on the
    strength of a near-cancellation and assemble it as a symmetric one -- the
    same silent-symmetry failure plan 11 §10 records for ``TORS``, arrived at
    from the opposite direction.

    **It is evaluated pre-closure, so it cannot feed on its own output.** From
    B8a-2 the closure gives any rolling case a lateral relief field, so a
    predicate reading the *final* load set would find lateral content in every
    case that rolls and hand every one of them.

    The threshold is a fraction of ``n*W`` rather than an absolute pound, so it
    means the same thing on a 3,400 lb trainer and a 33,000 lb jet.
    """
    # The free-moment test reads the **net**, not "any load carries one". It was
    # ``any(ld.mx or ld.mz ...)`` until the ground families arrived, which was
    # indistinguishable while the aileron couple was the suite's only free
    # ``mx``: one lumped couple at the centreline is its own net. A ground case
    # transfers every wheel reaction from its contact patch to its trunnion with
    # a lever-arm couple, so *both* main wheels carry an ``mx`` -- equal and
    # opposite, cancelling exactly -- and an "any" test minted every symmetric
    # level-landing case handed, emitting a twin that is the same load set
    # mirrored onto itself. The net is the question that was always meant.
    free = (math.fsum(ld.mx for ld in applied), math.fsum(ld.mz for ld in applied))
    if ref_length <= 0.0:
        if any(free):
            return True
    elif max(abs(v) for v in free) > HANDEDNESS_TOL * n_w * ref_length:
        return True
    if math.fsum(abs(ld.fy) for ld in applied) > HANDEDNESS_TOL * n_w:
        return True
    # The rolling test reads the **net**, unlike the lateral one above, and for
    # the opposite reason: a mirror-symmetric set cancels to exactly zero here
    # (each pair contributes ``y*f + (-y)*f``), so the net is a clean signal
    # rather than a near-cancellation of large parts. Measured, the two
    # populations do not overlap: symmetric wing cases net 1e-17 of ``n*W*b/2``
    # in roll and the 23.427(a) case nets 6e-3 to 1.7e-2.
    if ref_length <= 0.0:
        return False
    roll = math.fsum(ld.mx + ld.y * ld.fz - ld.z * ld.fy for ld in applied)
    return abs(roll) > HANDEDNESS_TOL * n_w * ref_length


def point_mass_self_inertia(loading: CaseLoading, project: Project):
    """``[((x, y, z), SelfInertia)]`` for every item carried as a point mass.

    Decision **L-3**: an item the assembly does not spread still resists angular
    acceleration about its own centre, and that resistance has no other carrier
    in the model. Items with no entered inertia are dropped rather than emitted
    as zeros, so the deck gains a ``MOMENT`` card only where the database
    actually says something -- on ``ga6_normal`` that is a handful of lumps
    worth 13.3 % of ``Izz``, and on ``concept_regional_jet`` it is nothing at
    all, because that database enters no self-inertias.
    """
    out = []
    for it in reacted_parts(loading.items, project):
        if assembly_distributes_mass(component_of(it, project)):
            continue
        if it.ixx or it.iyy or it.izz:
            out.append(((it.x, it.y, it.z),
                        SelfInertia(it.ixx, it.iyy, it.izz)))
    return out


# --------------------------------------------------------------------------- #
# Resultants and closure
# --------------------------------------------------------------------------- #
def resultant(loads: Sequence[BalancedLoad],
              ref: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """``(Fx, Fz, My)`` of ``loads`` about ``ref`` -- free moments plus lever arms.

    The symmetric three. :func:`resultant6` is the full rigid-body resultant;
    this stays as the in-plane view every symmetric caller wants.
    """
    fx, _, fz, _, my, _ = resultant6(loads, ref)
    return fx, fz, my


def resultant6(loads: Sequence[BalancedLoad],
               ref: Tuple[float, float, float]) -> Tuple[float, float, float,
                                                         float, float, float]:
    """``(Fx, Fy, Fz, Mx, My, Mz)`` of ``loads`` about ``ref``.

    All six, from B7 on, because an antisymmetric case is out of balance in a
    degree of freedom the symmetric three cannot see: ``ACRL`` assembled without
    a roll term closes ``Fx``/``Fz``/``My`` to 1e-11 and carries a whole
    unbalanced rolling moment, which is precisely the case reading as balanced
    while meaning nothing.

    ``Fy`` and ``Mz`` are identically zero for every family shipped today -- no
    load in the suite has a side component yet -- and are computed rather than
    assumed so B8a's lateral cases inherit a resultant that already covers them,
    and so :func:`test_lateral_dof_are_untouched` can pin the fact.
    """
    fx = math.fsum(ld.fx for ld in loads)
    fy = math.fsum(ld.fy for ld in loads)
    fz = math.fsum(ld.fz for ld in loads)
    mx = math.fsum(ld.mx + (ld.y - ref[1]) * ld.fz - (ld.z - ref[2]) * ld.fy
             for ld in loads)
    my = math.fsum(ld.my + (ld.z - ref[2]) * ld.fx - (ld.x - ref[0]) * ld.fz
             for ld in loads)
    mz = math.fsum(ld.mz + (ld.x - ref[0]) * ld.fy - (ld.y - ref[1]) * ld.fx
             for ld in loads)
    return fx, fy, fz, mx, my, mz


#: One ``closure-*`` source per degree of freedom, and the axis of
#: ``omega_dot`` each rotational one carries. Split rather than emitted as a
#: single ``closure-rot`` load because the split is what makes the field
#: *attributable*: the B7 gate isolates the roll strips and compares them with
#: WINGINER's unit-roll set, and a deck reader can see which acceleration put a
#: given card there. The sum of the three is the full field either way.
_ROTATIONAL_SOURCES = (("closure-roll", 0), ("closure-pitch", 1),
                       ("closure-yaw", 2))


def _closure(loads: List[BalancedLoad], cg: CgCase,
             residual: Tuple[float, float, float, float, float, float],
             self_inertia: Sequence[Tuple[Tuple[float, float, float],
                                          SelfInertia]] = (),
             ) -> Tuple[Tuple[float, float, float],
                        Tuple[float, float, float], InertiaTensor]:
    """Close the residual as rigid-body relief; return ``(n, omega_dot, tensor)``.

    **Six** degrees of freedom from B8a-2 (plan 13 decisions L-2/L-3), not the
    four B7 carried and not the two plan 11 B-3 anticipated, and -- more to the
    point -- **one field** rather than four hand-rolled slices of one. The
    relief is ``f_i = -w_i (n + omega_dot x r_i)``, written once in
    :mod:`sloads.rigid_body`; this function decides *what* it is applied to and
    with which accelerations.

    The three translational DOF stay decoupled ratios ``n = F/W`` **because the
    field is referred to the mass set's own centroid**, where ``Sum w_i r_i`` is
    zero by definition: a uniform load factor then produces no moment, and an
    angular acceleration produces no net force. That reference is the loading's
    CG to the last digit on nearly every case (step C1 solves the ballast from
    it), and it is computed here rather than assumed to be, because "nearly"
    is not a closure. ``ga6_normal``'s ``CG4`` loading sits 0.0024 in forward and
    0.0052 in below its own entered CG -- nothing at all until an acceleration
    multiplies it, and the 23.427(a) case's ``q_dot`` of 637 deg/s^2 is what
    multiplies it: referred to the entered CG the same field leaves **0.31 lb**
    of ``Fx`` unclosed (D-R8). The residual reported on the case is still stated
    about the CG, which is what a reader expects; only the relief is solved
    where it is exact.

    The three rotational DOF are **one coupled 3x3 solve** on the assembled
    inertia tensor about that same centroid: the field
    an angular acceleration applies produces the moment ``-[I]{omega_dot}``
    exactly, and ``[I]``'s off-diagonal ``Ixz`` is 8.4 % of the ga6's pitch
    inertia and larger on the regional jet (plan 13 §3.5), so roll and yaw are
    genuinely coupled and three independent ratios would be wrong rather than
    approximate.

    What changed at B8a-2, and what it moved
    ----------------------------------------
    Each acceleration now applies **both** its force components rather than the
    one the vertical-only ancestors carried. That is the difference between
    ``Sum w*d^2`` and a moment of inertia, and it is not uniformly small:

    * pitch gained ``fx = -w*q_dot*dz``. The companion itself is negligible
      (<= 0.08 % of a node load) but the *acceleration* moved, because the pitch
      inertia stopped being ``Sum w*dx^2``: ``q_dot`` fell 18-22 % on
      ``ga6_normal``, 3-4 % on the regional jet;
    * roll gained ``fy = +w*p_dot*dz``, worth 94-518 lb at a peak node -- larger
      than the roll term already in the deck, because ``fz = -w*p_dot*dy``
      touches only the wing strips (every database item sits at ``y = 0``) while
      the companion touches every mass off the roll axis. ``p_dot`` fell 20.7 %
      / 23.2 % accordingly, and the B7 gate reads the *shape* it preserves
      exactly plus that ratio, pinned;
    * yaw is new, and would have been 55 % wrong had it copied the pitch DOF's
      one-component pattern.

    Self-inertia (L-3) rides along as a **free moment** ``-[I_self]{omega_dot}``
    at each node whose mass the assembly carries as a point. It is 13.3 % of
    ``ga6_normal``'s ``Izz``; the regional jet's database enters none.

    The x degree of freedom is not optional: **nothing else in the assembled
    model reacts drag.** The suite has no distributed thrust, and FAR 23's
    longitudinal load factor ``nx`` is exactly this quantity. On ``ga6_normal``
    PHAA the closure gives 0.661 g against the trim's own drag of 0.610. Leaving
    it open would put 17-26 % of ``n*W`` into the support reaction and make
    "reactions ~ 0" untrue in a file that still solved.

    That 0.05 g difference is **not** quadrature (an earlier reading here called
    it "the same strip-quadrature-versus-closed-form gap"; corrected 2026-08-15).
    ``residual_fx`` equals the wing strips' ``Sum fx`` exactly -- nothing in the
    assembled model carries the airplane's **non-wing** drag -- and the gap is
    element-independent: -191.5 lb at 5 elements, -173.4 lb converged at 640. It
    is a missing load, not an integration error, and the same missing load is the
    whole of the pitch residual through its ``(zw - zcg)`` arm. Filed on the
    backlog as "non-wing drag has no carrier in the assembled model".

    The relief is spread over **the inertia loads already in the model**, not
    over the raw item list. Those are the same masses, but at the places the
    assembled model actually carries them -- wing mass out along the span rather
    than on the centreline where the database enters it -- so the deck's internal
    load path stays physical and no relief lands on a node the airplane has no
    mass at.
    """
    zero = (0.0, 0.0, 0.0)
    masses = [(ld, ld.weight_lb) for ld in loads if ld.weight_lb]
    w_total = math.fsum(w for _, w in masses)
    if not w_total:
        return zero, zero, InertiaTensor()

    # The centroid of the masses the model actually carries -- the one point the
    # relief field is exact about (see the docstring).
    cx = math.fsum(ld.x * w for ld, w in masses) / w_total
    cy = math.fsum(ld.y * w for ld, w in masses) / w_total
    cz = math.fsum(ld.z * w for ld, w in masses) / w_total
    points = [PointMass(w, ld.x - cx, ld.y - cy, ld.z - cz) for ld, w in masses]
    tensor = inertia_tensor(points, [si for _, si in self_inertia])
    fx, fy, fz, mx, my, mz = residual
    n = (fx / w_total, fy / w_total, fz / w_total)
    # The residual arrives about the CG; transfer it to the centroid,
    # ``M_c = M_ref + (ref - c) x F``, before solving for the accelerations.
    dx, dy, dz = cg.xcg - cx, 0.0 - cy, cg.zcg - cz
    omega_dot = tensor.solve((mx + dy * fz - dz * fy,
                              my + dz * fx - dx * fz,
                              mz + dx * fy - dy * fx))

    for (ld, w), pm in zip(masses, points):
        r = (pm.dx, pm.dy, pm.dz)
        f = relief_force(w, r, n, zero)
        loads.append(BalancedLoad(x=ld.x, y=ld.y, z=ld.z,
                                  fx=f[0], fy=f[1], fz=f[2],
                                  source="closure-n", side=ld.side))
        for source, axis in _ROTATIONAL_SOURCES:
            if not omega_dot[axis]:
                continue
            only = (omega_dot[0] if axis == 0 else 0.0,
                    omega_dot[1] if axis == 1 else 0.0,
                    omega_dot[2] if axis == 2 else 0.0)
            f = relief_force(w, r, zero, only)
            loads.append(BalancedLoad(x=ld.x, y=ld.y, z=ld.z,
                                      fx=f[0], fy=f[1], fz=f[2],
                                      source=source, side=ld.side))

    for (x, y, z), si in self_inertia:
        m = relief_moment(si, omega_dot)
        if any(m):
            loads.append(BalancedLoad(x=x, y=y, z=z, mx=m[0], my=m[1], mz=m[2],
                                      source="closure-self", side="C"))
    return n, omega_dot, tensor


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def unbalanced_rolling_moment(project: Project, condition: str) -> float:
    """The entered ``UNB`` of wing condition ``condition`` (FAR 23.349), or 0.

    Read from the **entered** ``wing_mass.cases``, which is where the aileron's
    unbalanced rolling moment lives; a *derived* wing case carries ``UNB = 0``
    (the documented gap in ``wing_inertia.resolve_wing_cases``), so a project
    relying on the derived route simply has no rolling case to assemble rather
    than a silently symmetric one.
    """
    wm = project.wing_mass
    if wm is None:
        return 0.0
    case = next((c for c in wm.cases if c.name == condition), None)
    return case.unbal_moment if case is not None else 0.0


def assemble(project: Project, condition: str, vn: VnPoint,
             loading: CaseLoading, cg: CgCase,
             case_ref=None, unb: float = 0.0,
             lateral: Sequence[BalancedLoad] = (),
             htail: Sequence[BalancedLoad] = ()) -> BalancedCaseResult:
    """Assemble one balanced case and close its residual.

    ``unb`` is the unbalanced rolling moment (FAR 23.349) for an accelerated-roll
    condition; zero makes the case symmetric and is the default, so every
    symmetric caller is unchanged.

    ``lateral`` is the applied side-load set -- the fin distribution of a
    23.441/23.443 condition (B8a-3, :func:`fin_sets`). The symmetric half of the
    case is assembled from the V-n point exactly as it always was: all four
    v-tail conditions sit at ``n_z ~ 1``, so nothing about the vertical,
    longitudinal or pitching physics changes when a side load is added beside it,
    and ``test_the_symmetric_half_still_closes`` is the guard that it did not.

    ``htail`` is the distributed horizontal-tail load of the 23.427(a)
    unsymmetrical condition (D-R8, :func:`htail_sets`). It **replaces** the
    lumped trim tail load: SELECT's ``RH + LH`` is the condition's whole tail
    load, and applying ``vn.lt`` beside it would carry the balancing part twice.
    The mismatch between the two is the maneuver -- see the module docstring --
    and the pitch degree of freedom of the closure is what reacts it.

    **Handedness is measured, not declared** (decision L-6): the case gets a hand
    when its *applied* set has lateral content or a net rolling moment, whatever
    put it there -- the aileron couple of ``ACRL``, the fin load of a rudder kick
    or the left/right split of 23.427(a). Before B8a-3 the first two would have
    been separate flags; :func:`is_handed` is the one predicate.
    """
    fl = _flight_loads(project)
    notes: List[str] = []

    wing_r, panel_both, _cm_free = wing_sets(project, vn)
    wing_r, scale_notes = place_wing_inertia(wing_r, loading, project, panel_both)
    notes += scale_notes

    loads: List[BalancedLoad] = list(wing_r) + _mirror(wing_r)
    if htail:
        loads += list(htail)
        applied_ht = math.fsum(ld.fz for ld in htail)
        notes.append(
            f"UNSYMMETRICAL (FAR 23.427(a)): the applied tail load is SELECT's "
            f"own left/right split, {applied_ht:+.0f} lb, and it REPLACES the "
            f"trim tail load {vn.lt:+.0f} lb this V-n point balances at. The "
            f"difference is the maneuver -- 23.427(a) distributes a maneuver "
            f"tail load, and the airplane is not in trim under it -- so the "
            f"pre-closure Fz and My are that difference in full and are NOT a "
            f"balance error: the vertical and pitch degrees of freedom of the "
            f"closure are the motion it causes. The 1 % residual gate is on the "
            f"case's trim half, which is unchanged")
    else:
        loads.append(BalancedLoad(x=fl.xtc, y=0.0, z=fl.zw, fz=vn.lt,
                                  source="tail-air", side="C"))
    loads += body_inertia(loading, project, vn.nz)

    # The fuselage's share of the trim pitching moment: what the airplane-less-tail
    # Cm carries that the distributed wing does not (see the module docstring).
    wing_about_ac = math.fsum(
        ld.my + (ld.z - fl.zw) * ld.fx - (ld.x - fl.xw) * ld.fz
        for ld in loads if ld.source == "wing-air")
    fuselage_cm = vn.m_wf - wing_about_ac
    loads.append(BalancedLoad(x=fl.xw, y=0.0, z=fl.zw, my=fuselage_cm,
                              source="fuselage-cm", side="C"))

    # The airplane's NON-WING drag (see "The body-axial load" in the docstring).
    body_axial, delta_cd, body_axial_clamped, drag_loads, drag_notes = body_axial_set(
        loads, project, vn, loading)
    loads += drag_loads
    notes += drag_notes

    # The aileron's rolling moment (FAR 23.349), applied as a labelled free
    # couple at the wing aerodynamic centre. Sign: WINGINER's unit-roll inertia
    # set produces a rolling moment of exactly ``+UNB`` (verified: its
    # normalisation makes ``sum(y*fz_r)`` equal 100,000 for a unit case), and
    # NETLOADS enters inertia opposing the air load -- so the *aero* moment this
    # is the couple for is ``-UNB``. The closure's roll DOF then reproduces
    # WINGINER's distribution strip for strip, which is the check that this sign
    # is right rather than merely consistent.
    if unb:
        loads.append(BalancedLoad(x=fl.xw, y=0.0, z=fl.zw, mx=-unb,
                                  source="aileron-roll", side="C"))
        notes.append(f"aileron rolling moment {-unb:+.0f} lb-in applied as a "
                     f"lumped free couple: {AILERON_COUPLE_NOTE}")

    if lateral:
        loads += list(lateral)
        notes.append(LATERAL_AERO_NOTE)

    wm, geometry, _ = _wing_slices(project)
    geom = geometry.by_name(wm.surface)
    semi_span = geom.leading_edge[-1][1] if geom else 0.0
    ref = (cg.xcg, 0.0, cg.zcg)
    handed = is_handed(loads, abs(vn.nz * cg.weight_lb), semi_span)
    residual = resultant6(loads, ref)
    fx, fy, fz, mx, my, mz = residual
    n, omega_dot, tensor = _closure(
        loads, cg, residual, point_mass_self_inertia(loading, project))

    return BalancedCaseResult(
        label=condition, vn_case=vn.case, cg=cg.name, nz=vn.nz,
        weight_lb=cg.weight_lb, mac=fl.mac, cg_x=cg.xcg, cg_z=cg.zcg,
        semi_span=semi_span, loads=loads,
        residual_fz=fz, residual_fx=fx, residual_my=my,
        residual_fy=fy, residual_mx=mx, residual_mz=mz,
        delta_n=n[2], delta_nx=n[0], delta_ny=n[1],
        p_dot=omega_dot[0], q_dot=omega_dot[1], r_dot=omega_dot[2],
        closure_inertia=tensor,
        unbal_moment=unb, fuselage_cm=fuselage_cm,
        body_axial=body_axial, delta_cd=delta_cd,
        body_axial_clamped=body_axial_clamped,
        case_ref=_handed_ref(case_ref, "R") if handed else case_ref,
        hand="R" if handed else "", notes=notes,
    )


def _handed_ref(ref, hand: str):
    """``CaseRef`` with the handedness suffix on its id (B-7), or ``None``."""
    if ref is None:
        return None
    return replace(ref, case_id=handed_case_id(ref.case_id, hand))


def _flip(value: float) -> float:
    """``-value``, with IEEE negative zero normalised away.

    A symmetric quantity on a handed pair is exactly ``0.0``, and negating it
    gives ``-0.0`` -- which renders as ``-0.00000`` in the port twin's deck
    header beside the starboard twin's ``+0.00000``, reading as a difference
    where there is none. ``-0.0 + 0.0`` is ``+0.0``; adding zero is the identity
    on every other value.
    """
    return -value + 0.0


def handed_twin(case: BalancedCaseResult, case_ref=None) -> BalancedCaseResult:
    """The opposite-hand twin of an antisymmetric case, by reflection (B-6).

    ``case_ref`` overrides the twin's identity instead of deriving it by suffixing
    the computed case's id, and exists for exactly one family: the 23.485 side
    condition, whose twin **already has an id of its own** (``LG-20`` beside
    ``LG-19``) because LANDLOAD supplies both drift directions. Minting
    ``LG-19L``/``LG-19R`` beside a shipped ``LG-20`` would put two ids on one
    physical condition, which M4-2 decision 1 forbids. Everywhere else the twin is
    derived and this stays ``None`` (decision G-8).

    Derived from the computed case rather than recomputed, which is the whole
    point: the oracle-locked FAR 23 path never sees handedness. Every quantity
    that is odd under the mirror flips through the single owner in
    :mod:`sloads.export.coordinates` -- positions, side tags, the applied couple,
    the fin's side load and torsion, the lateral relief -- and everything even is
    untouched, so the twin's vertical, longitudinal and pitching balance is
    *identical* and only its lateral half reverses. On a v-tail case that is the
    ``-beta`` condition of a ``+beta`` one, got for the cost of a sign flip and
    without SELECT ever seeing the question.
    """
    if not case.hand:
        raise ValueError(
            f"balanced case {case.label} has no hand -- a symmetric case is its "
            "own mirror image, and minting a twin for it would put the same "
            "load set in the deck twice")
    ref = case.case_ref
    twin_ref = (case_ref if case_ref is not None
                else _handed_ref(ref, reflect_side(case.hand)))
    return replace(
        case,
        loads=[reflect_load(ld) for ld in case.loads],
        residual_mx=-case.residual_mx,
        residual_mz=-case.residual_mz,
        residual_fy=_flip(case.residual_fy),
        delta_ny=_flip(case.delta_ny),
        p_dot=_flip(case.p_dot),
        r_dot=_flip(case.r_dot),
        unbal_moment=-case.unbal_moment,
        hand=reflect_side(case.hand),
        case_ref=twin_ref,
    )


def _tail_distributions(project: Project, component: str, builder) -> dict:
    """``{condition label: load set}`` for one empennage surface, or ``{}``.

    Built once per project rather than per case: ``build_tail_span`` re-resolves
    both planforms and re-runs SELECT, and the conditions of a surface share V-n
    points. A project whose chain does not exist yields nothing here and simply
    assembles no case of that family -- the same "the whole chain must exist"
    rule the symmetric families follow.
    """
    try:
        spans = build_tail_span(project)
    except MissingInputError:
        return {}
    return {r.case: builder(r) for r in spans.get(component, ())}


def _fin_distributions(project: Project) -> dict:
    """``{condition label: fin load set}`` for every v-tail condition, or ``{}``.

    Built once per project rather than per case: ``build_tail_span`` re-resolves
    the planform and re-runs SELECT, and three of the four conditions share a
    V-n point. A project with no ``vtail_loads`` yields nothing here and simply
    assembles no lateral case -- the same "the whole chain must exist" rule the
    symmetric families follow.
    """
    return _tail_distributions(project, VTAIL, fin_sets)


def _htail_distributions(project: Project) -> dict:
    """``{condition label: h-tail load set}`` for every h-tail condition (D-R8).

    Only ``UNSYMMETRICAL`` is ever asked for (:data:`BALANCED_HTAIL_CONDITIONS`);
    the whole table is built because the underlying span build produces it in one
    pass either way.
    """
    return _tail_distributions(project, HTAIL, htail_sets)


def build_balanced_cases(
        project: Project,
        skipped: Optional[List[SkippedCondition]] = None,
) -> List[BalancedCaseResult]:
    """One :class:`BalancedCaseResult` per condition SELECT picked -- **two** for
    a condition that has a hand.

    Three families, assembled by the same machinery (B8a-3, D-R8):

    * the **wing** conditions of :data:`BALANCED_WING_CONDITIONS` -- symmetric,
      plus ``ACRL``'s applied aileron couple;
    * the **vertical-tail** conditions of :data:`BALANCED_VTAIL_CONDITIONS` --
      the fin's distributed side load riding on the same symmetric case its V-n
      point already describes;
    * the **horizontal-tail** condition of :data:`BALANCED_HTAIL_CONDITIONS` --
      FAR 23.427(a)'s left/right split, distributed over the full-span tail in
      place of the lumped trim tail load every other case carries.

    A condition is assembled only when the whole chain exists for it: SELECT
    named it, it has a V-n point, and its CG case resolves to a **derivable**
    loading (step C1). A case whose CG the weight database cannot produce has no
    honest inertia set, and inventing one would put fictitious mass into the very
    balance the case exists to demonstrate.

    A case with lateral content in its applied set is emitted as a **handed
    pair** -- the computed starboard case and its port mirror (B-6/B-7). A
    condition that is merely *allowed* a hand and turns out not to have one (a
    rolling condition whose ``UNB`` is zero) is emitted once, unhanded: the twins
    exist for cases that have a hand.

    **Every condition that does not assemble is recorded** (review F-C7): pass a
    list as ``skipped`` and it is extended with one :class:`SkippedCondition` per
    dropped condition, in SELECT's order. Before this, a missing V-n point or a
    non-derivable loading dropped a condition out of the primary deliverable in
    silence, and only the shipped fixtures' drop set was pinned. Callers that
    want the record alone use :func:`skipped_conditions`.
    """
    sync_geometry_derived(project)
    if project.flight_loads is None or project.wing_mass is None:
        raise MissingInputError("balance needs 'flight_loads' and 'wing_mass'")
    # Both through their single owners (review F-C6). ``project.envelope or
    # build_envelope(project)`` duplicated the owner's rule and got it wrong at the
    # edge: a persisted envelope carrying an *empty* ``vn`` was accepted, and every
    # condition then dropped out of the assembly under a misleading "nothing to
    # balance". ``default_envelope`` rebuilds in that case; ``default_critical``
    # applies the same rule to the critical set.
    envelope = default_envelope(project)
    critical = default_critical(project)
    vn = {p.case: p for p in envelope.vn}
    cgs = {c.name: c for c in flight_cases(project)}
    loadings = {ld.name: ld for ld in derive_case_loadings(project)}
    fins = _fin_distributions(project)
    htails = _htail_distributions(project)

    record: List[SkippedCondition] = skipped if skipped is not None else []

    out: List[BalancedCaseResult] = []
    for cond in critical.conditions:
        unb = 0.0
        lateral: Sequence[BalancedLoad] = ()
        htail: Sequence[BalancedLoad] = ()
        if cond.component == "wing" and cond.label in BALANCED_WING_CONDITIONS:
            unb = (unbalanced_rolling_moment(project, cond.label)
                   if cond.label in ROLLING_WING_CONDITIONS else 0.0)
        elif cond.component == VTAIL and cond.label in BALANCED_VTAIL_CONDITIONS:
            lateral = fins.get(cond.label, ())
            if not lateral:
                record.append(_skip(cond, "no-fin-loads"))
                continue
        elif cond.component == HTAIL and cond.label in BALANCED_HTAIL_CONDITIONS:
            htail = htails.get(cond.label, ())
            if not htail:
                record.append(_skip(cond, "no-htail-loads"))
                continue
        elif cond.component == HTAIL:
            record.append(_skip(cond, "htail-symmetric"))
            continue
        else:
            record.append(_skip(cond, "out-of-family"))
            continue
        point = vn.get(cond.case) if cond.case is not None else None
        if point is None:
            record.append(_skip(cond, "no-vn-point"))
            continue
        cg = cgs.get(point.cg)
        loading = loadings.get(point.cg)
        if cg is None or loading is None:
            record.append(_skip(cond, "no-cg-case"))
            continue
        if not loading.derivable:
            record.append(_skip(cond, "loading-not-derivable"))
            continue
        case = assemble(project, cond.label, point, loading, cg,
                        case_ref=cond.case_ref, unb=unb, lateral=lateral,
                        htail=htail)
        out.append(case)
        if case.hand:
            out.append(handed_twin(case))
    # The ground families join the same deck (decision G-1) -- they are balanced
    # free-free cases like every other, and building them in a per-component view
    # first would put the primary deliverable second. They are appended rather
    # than interleaved so the flight families' order, and therefore every shipped
    # deck's existing subcase sequence, is untouched.
    out += build_ground_cases(project, record)
    return out


# --------------------------------------------------------------------------- #
# The ground families (step 10 piece 3 -- decisions G-1, G-6, G-7/G-7a, G-8)
# --------------------------------------------------------------------------- #
#: LANDLOAD cases that carry wing lift: the **landing** families (23.479 level
#: 3-/2-wheel, 23.481 tail-down, 23.483 one-wheel). Decision G-7, and it is the
#: manual's own split rather than a new one -- ``landing.landing_reactions``
#: includes the ``lf*WL`` term in ``nvp`` for exactly these cases and omits it for
#: 13-24. **The regulation draws the same line**: 23.473(a) lets 23.479/481/483
#: be met at the design landing weight, which is why those are the families
#: LANDLOAD scales differently, and 23.485/23.493 are the gross-weight ones. The
#: family split, the lift split and the weight split are one split.
GROUND_LIFT_CASES = range(1, 13)

#: The 23.483 one-wheel family: a single main gear carries the whole reaction, so
#: the case has a hand and LANDLOAD supplies **neither** twin (there is no sign
#: flip anywhere in cases 10-12 -- they are the three loadings, one hand each).
GROUND_ONE_WHEEL_CASES = range(10, 13)

#: The 23.485 side family: three loadings x **two drift directions**, so LANDLOAD
#: supplies **both** hands. Only the odd member of each pair is assembled and the
#: even one becomes an independent check on the reflection operator (G-8).
GROUND_SIDE_CASES = range(19, 25)

#: The ground families the assembled deck carries: 1-24. The 23.499 supplementary
#: nose-wheel family (25-33) is deliberately absent -- see
#: :data:`SKIP_REASONS`'s ``gear-design-only``.
BALANCED_GROUND_CASES = range(1, 25)

#: The G-7a statement of record, carried in-band on every ground case that
#: carries lift. The tilt is small and the reason it exists is not obvious from
#: the cards, so it travels with them rather than sitting in a document beside.
GROUND_LIFT_NOTE = (
    "the wing lift is L x W on the AIRLOADS spanwise shape, and it acts along "
    "the GROUND LINE rather than the airplane z axis: lift is perpendicular to "
    "the flight path, and at touchdown that is the runway, so the airplane's "
    "attitude tilts the lift vector by the ground angle. Only the SHAPE is "
    "borrowed from AIRLOADS -- the magnitude is L x W, so no speed, CL or V-n "
    "point is involved and no new aerodynamics is invented")

#: The G-7 statement of record for the ground-handling families, which carry no
#: lift at all. Said explicitly because "no lift" and "no load" are easy to
#: confuse, and the wing is emphatically not load-free in a braked roll.
GROUND_NO_LIFT_NOTE = (
    "no wing lift in this family (FAR 23.485 / 23.493 are ground-handling "
    "conditions): the gear loads are balanced by inertia alone. The wing still "
    "carries its OWN inertia at the case's solved load factor, so it is "
    "lift-free, not load-free")

#: The G-6 statement of record: what closes a ground case, and what does not.
GROUND_CLOSURE_NOTE = (
    "closed by the six-DOF rigid-body field, not by LANDLOAD's NVP/NDP/NS. "
    "Those are translation only -- the rotational half sits unreacted in "
    "PITCHP/ROLLP/YAWP -- and they are stated about the ground line, so "
    "consuming them would put a frame rotation in the load path. They are the "
    "independent closed-form check on the solve instead (FAR 23.471: the "
    "external reactions must be placed in equilibrium with the linear and "
    "angular inertia forces)")


def gear_sets(wheels: Sequence) -> List[BalancedLoad]:
    """The applied gear reactions of one ground case, at their reference points.

    A pure consumer of :mod:`sloads.gear_loads`, which is itself a pure consumer
    of :mod:`sloads.modules.landing` -- so the reaction an assembled ground case
    carries is the Appendix-A-locked one, per wheel, and no oracle is at risk from
    assembling it. What this adds is the ``BalancedLoad`` wrapper and the
    ``source``/``side`` tags the deck bands by.

    Each wheel arrives as a force **and** the lever-arm couple that carried it
    from the tyre contact patch to the trunnion, so the pair together has the
    identical resultant the reaction had at the patch (G-2's third guard asserts
    exactly that, at ``rel_tol 1e-12``). Applying the force without the couple is
    the failure mode the guard exists for: it still sums to zero at a determinate
    support, so the assembled residual alone would never catch it.

    No load-factor argument on purpose: the leg's own mass rides the closure
    field through its ``weight.items`` rows, exactly as the empennage surfaces'
    does, so that each mass enters exactly one set.
    """
    loads: List[BalancedLoad] = []
    for wheel in wheels:
        fx, fy, fz = wheel.force
        mx, my, mz = wheel.couple
        loads.append(BalancedLoad(
            x=wheel.node[0], y=wheel.node[1], z=wheel.node[2],
            fx=fx, fy=fy, fz=fz, mx=mx, my=my, mz=mz,
            source=f"gear-{wheel.leg}", side=wheel.side))
    return loads


def ground_lift_sets(project: Project, lift_lb: float,
                     rotation_deg: float) -> List[BalancedLoad]:
    """The starboard wing's share of the ground-case lift (G-7, G-7a).

    ``lift_lb`` is the **whole airplane's** lift, ``L x W_case``; this returns one
    half of it, and the caller mirrors. The shape is the AIRLOADS Schrenk
    distribution, rescaled -- only the shape, so no speed, ``CL`` or V-n point is
    needed and the oracle-locked spanwise integrator is reused rather than a
    lumped force invented. That matters structurally: a lumped force gives the
    inboard wing none of the ground-case bending relief it actually gets.

    **The vector lies along the ground line** (decision G-7a), so it enters
    airplane axes as ``(L sin rho, 0, L cos rho)``. Lift is perpendicular to the
    flight path; at touchdown the flight path is the runway to within the descent
    angle; and the airplane sits at ``rho`` to it. On ``ga6_normal``'s level
    families that puts ~152 lb of the 2,154 lb lift forward, and it is what keeps
    G-6's ``NVP``/``NDP`` gate an identity rather than a tolerance -- LANDLOAD
    sums ``lf*WL`` into the ground-line vertical, so a lift applied along ``z``
    would enter that sum short by ``cos rho``.

    The section ``Cm`` and the induced ``fx`` of the aerodynamic distribution are
    deliberately **not** carried: they scale with ``q*CL`` and this case has
    neither. Borrowing them would be inventing aerodynamics the condition does
    not define.
    """
    wm, geometry, aero_in = _wing_slices(project)
    geom = geometry.by_name(wm.surface)
    aero = aero_in.by_name(wm.surface)
    if geom is None or aero is None:
        raise MissingInputError("a ground case needs a wing surface and aero set")
    # Any (cl, v) gives the same *shape*: the Schrenk distribution scales with
    # ``q*CL`` as a whole. Unit values make that explicit at the call site rather
    # than borrowing a flight condition this case does not have.
    shape = air_load_distribution(geom, aero, 1.0, 100.0,
                                  wm.wrp_waterline, wm.dihedral_deg)
    total = math.fsum(s.fz for s in shape.stations)
    if not total:
        raise MissingInputError(
            "the wing spanwise distribution integrates to zero lift, so a ground "
            "case's lift has no shape to be distributed on")
    k = (lift_lb / 2.0) / total
    a = radians(rotation_deg)
    return [BalancedLoad(x=s.x, y=s.y, z=s.z,
                         fx=s.fz * k * sin(a), fz=s.fz * k * cos(a),
                         source="ground-lift", side="R")
            for s in shape.stations]


def assemble_ground(project: Project, gear: "GearCaseLoads", wheels: Sequence,
                    loading: CaseLoading, cg: CgCase, lift_factor: float,
                    rotation_deg: float, *, case_ref=None,
                    hand: str = "") -> BalancedCaseResult:
    """Assemble one **ground** case and close it in six DOF (G-1, G-6, G-7).

    The sibling of :func:`assemble`, and deliberately not a branch inside it: a
    ground case has no V-n point, so it has no ``cl``, no ``lt`` trim tail load
    and no ``m_wf`` -- three of the four things the flight assembly is built
    around. What the two share is everything that matters, and they share it as
    code: :func:`wing_inertia_strips`, :func:`place_wing_inertia`,
    :func:`body_inertia`, :func:`resultant6`, :func:`point_mass_self_inertia` and
    :func:`_closure`.

    **Nothing is applied at a flight load factor, because there is not one.** The
    inertia set enters at ``nz = 0`` and the closure solves the whole rigid-body
    field, which is what G-6 asks for and what FAR **23.471** asks for: *"the
    external reactions must be placed in equilibrium with the linear and angular
    inertia forces in a rational or conservative manner."* The solved ``n_z``
    rotated back to the ground line **is** ``NVP``, exactly -- that identity is
    this step's benchmark-first gate, and it is content-carrying because LANDLOAD
    reaches those factors by lever arms and FAR percentages rather than by a mass
    matrix.

    **The pre-closure residual is the whole applied load and is not an error.**
    A ground case has nothing to cancel against -- there is no trim -- so
    :data:`RESIDUAL_GATE` does not apply to it, the same standing as the lateral
    families and the 23.427(a) h-tail case. Nothing trims the case in pitch
    either: distributing the lift at the wing rather than netting it at the CG
    (as LANDLOAD does, via ``NLG = N - L``) leaves a pitching moment, measured at
    1.26-1.47 % of ``n*W*MAC`` on ``ga6_normal``, reacted by pitch acceleration
    alone. An airplane at touchdown is an accelerating body, not a trimmed one,
    and Ch 20 has no balancing tail load to invent.

    ``hand`` is passed in rather than measured for the 23.485 family, where the
    *manual* decides which hand a case is: ``LG-19`` is the port drift and
    ``LG-20`` the starboard, and both ids already exist. Left blank, the hand is
    measured by :func:`is_handed` as it is for every other family.
    """
    fl = project.flight_loads
    notes: List[str] = [GROUND_CLOSURE_NOTE]

    inertia, panel_both = wing_inertia_strips(project, 0.0)
    wing_r, scale_notes = place_wing_inertia(inertia, loading, project, panel_both)
    notes += scale_notes

    lift_lb = lift_factor * gear.weight_lb if gear.case in GROUND_LIFT_CASES else 0.0
    if lift_lb:
        wing_r = list(wing_r) + ground_lift_sets(project, lift_lb, rotation_deg)
        notes.append(f"applied wing lift {lift_lb:+.0f} lb (L = {lift_factor:g} x "
                     f"{gear.weight_lb:,.0f} lb, FAR 23.473(a)): {GROUND_LIFT_NOTE}")
    else:
        notes.append(GROUND_NO_LIFT_NOTE)

    loads: List[BalancedLoad] = list(wing_r) + _mirror(wing_r)
    loads += gear_sets(wheels)
    loads += body_inertia(loading, project, 0.0)

    wm, geometry, _ = _wing_slices(project)
    geom = geometry.by_name(wm.surface)
    semi_span = geom.leading_edge[-1][1] if geom else 0.0
    ref = (cg.xcg, 0.0, cg.zcg)
    # The 23.485 family's hand is the manual's (both ids exist, so it is passed
    # in); every other family's is measured from the applied set, exactly as the
    # flight families' is. The one-wheel case is caught by ``is_handed``'s third
    # source -- a net rolling moment made by the distribution itself -- which was
    # added for the 23.427(a) h-tail and covers this without a change: all the
    # vertical reaction sits at one ``y`` and there is no side force at all, so a
    # lateral-content-only predicate would have minted it unhanded.
    if not hand and is_handed(loads, abs(gear.weight_lb), semi_span):
        # A *measured* hand suffixes the id, exactly as the flight families do:
        # the 23.483 one-wheel condition has only ``LG-10``, so its two hands are
        # ``LG-10L``/``LG-10R``. A hand that was **passed in** does not, because
        # it came from the 23.485 family where LANDLOAD already supplies both
        # drift directions under ids of their own (G-8).
        hand = "R"
        case_ref = _handed_ref(case_ref, hand)
    residual = resultant6(loads, ref)
    fx, fy, fz, mx, my, mz = residual
    n, omega_dot, tensor = _closure(
        loads, cg, residual, point_mass_self_inertia(loading, project))

    carriers = sorted({w.carrier.value for w in wheels if w.carrier is not None})
    if carriers:
        notes.append(
            "gear reactions are transferred from the tyre contact patch to each "
            f"leg's own reference point ({', '.join(carriers)}-carried) with the "
            "lever-arm couple, so the load at the node has the identical "
            "resultant it had at the patch")

    return BalancedCaseResult(
        label=gear.description, vn_case=gear.case, cg=cg.name,
        # A ground case's ``nz`` is an OUTPUT, not an input: it is solved, and
        # ``delta_n`` carries it. Reported here as the solved value so every
        # consumer of ``BalancedCaseResult.nz`` -- the deck header, the row
        # table, the report -- states the load factor the case actually runs at
        # rather than a placeholder 1.0 nobody computed.
        nz=n[2], weight_lb=gear.weight_lb, mac=fl.mac if fl else 0.0,
        cg_x=cg.xcg, cg_z=cg.zcg,
        semi_span=semi_span, loads=loads,
        residual_fz=fz, residual_fx=fx, residual_my=my,
        residual_fy=fy, residual_mx=mx, residual_mz=mz,
        delta_n=n[2], delta_nx=n[0], delta_ny=n[1],
        p_dot=omega_dot[0], q_dot=omega_dot[1], r_dot=omega_dot[2],
        closure_inertia=tensor, fuselage_cm=0.0,
        case_ref=case_ref, hand=hand, notes=notes,
    )


def _ground_target(base: CgCase, weight_lb: float) -> CgCase:
    """The weight/CG an assembled ground case sits at.

    The roled loading's **CG station** at the case's **own design weight**, which
    are not always the same weight: 23.473(a) lets 23.479/481/483 be met at the
    design landing weight while 23.485/23.493 are met at the maximum take-off
    weight, and LANDLOAD applies that as ``WR`` on cases 13-22. Renaming the case
    when the weight moves keeps the two apart in the derivation record and in the
    deck, so a reader is never shown "aft max landing" against a take-off weight.

    **The entered loading is dropped with the weight (D-25 / D-26).** A
    ``LoadingDefinition`` states which items are aboard, not what the airplane
    weighs, so carrying it onto a re-weighted target would assemble the landing
    loading's inertia set against take-off-weight gear reactions and call the
    result balanced -- measured on ``concept_regional_jet`` 2026-08-15 as 31,000 lb
    of modelled mass under a case declaring 33,000. Setting it to ``None`` sends
    the re-weighted target through the subset search, which is what produced these
    cases before any loading was entered and is the one route that solves for the
    *weight* as well as the station. A target the search cannot reach is skipped
    and recorded, never invented, exactly as before.
    """
    if abs(weight_lb - base.weight_lb) <= 1e-6:
        return base
    return replace(base, name=f"{base.name} at {weight_lb:,.0f} lb",
                   weight_lb=weight_lb, loading=None)


def _ground_loadings(project: Project,
                     gear: Sequence[GearCaseLoads]) -> Dict[int, Tuple[CgCase, Optional[CaseLoading]]]:
    """``{LANDLOAD case number: (CgCase, CaseLoading)}`` for every ground case.

    Keyed by **case number** rather than by loading name, because the name alone
    does not identify the target: cases 1-12 and 19-22 both name ``aft max
    landing`` and sit at different design weights (23.473(a) again), so a
    name lookup silently returns whichever was derived first -- which on
    ``ga6_normal`` put the side family's inertia set 170 lb light and its ``n_y``
    5 % high.

    Derived through the **same** :func:`~sloads.mass_distribution.derive_case_loadings`
    every flight case uses, with the same ``derivable`` gate: a ground case whose
    loading the weight database cannot produce is skipped and recorded, never
    invented (decision G-3). Ground cases *inherit* the already-pinned
    "payload cases are not loadings the weight database can produce" limitation;
    they do not create one and they do not wait on it.
    """
    base = {c.name: c for c in landing_role_cases(project)}
    per_case: Dict[int, CgCase] = {}
    distinct: Dict[str, CgCase] = {}
    for g in gear:
        anchor = base.get(g.cg_name)
        if anchor is None:
            continue
        target = _ground_target(anchor, g.weight_lb)
        per_case[g.case] = target
        distinct[target.name] = target
    loadings = {ld.name: ld for ld in
                derive_case_loadings(project, list(distinct.values()))}
    return {case: (target, loadings.get(target.name))
            for case, target in per_case.items()}


def build_ground_cases(
        project: Project,
        skipped: Optional[List[SkippedCondition]] = None,
) -> List[BalancedCaseResult]:
    """The ground/landing conditions as assembled balanced cases (G-1).

    **Ground cases are born in the assembled free-free deck**, not in a
    per-component body view. A ground case is irreducibly three-dimensional --
    on ``ga6_normal`` braked roll is 2,261 lb vertical against 1,809 lb of drag
    per wheel, and the side family 2,261 against -1,700 lb of side load, applied
    at the contact patch ~41 in below the fuselage beam line and +-57 in off the
    centreline. Those lever arms *are* the load case, and the per-component
    fuselage deck is planar by construction, so building it there first and in
    the primary deliverable second would be backwards.

    Which of LANDLOAD's 33 cases assemble, and why the rest do not:

    * **1-24** assemble, one balanced case each, plus a twin where the family has
      a hand;
    * **20, 22, 24** are the even members of the 23.485 pairs: they are LANDLOAD's
      *own* opposite drift direction, and decision G-8 mints them by **reflecting**
      the odd member instead, so the reflection operator keeps its single owner
      and gains the only external check it will ever get. They are recorded as
      derived rather than dropped;
    * **25-33** are the 23.499 supplementary nose-wheel family, which carries nose
      reactions only -- no main-gear reaction exists in it -- so it is a local
      gear-design case, not an airplane in equilibrium. It is recorded, and it
      has a home: the gear load report carries all 33.

    Every skip is recorded through the same :class:`SkippedCondition` path the
    flight families use, so "here is every condition and what became of it"
    covers the ground family too.
    """
    record: List[SkippedCondition] = skipped if skipped is not None else []
    try:
        gear = gear_case_loads(project)
    except MissingInputError:
        return []
    if not ground_cases(project):
        return []

    loadings = _ground_loadings(project, gear)
    by_case = {g.case: g for g in gear}
    landing: Optional[LandingInput] = project.landing
    if landing is None:
        raise MissingInputError("ground cases need 'landing'")
    lift_factor = landing.lift_factor

    out: List[BalancedCaseResult] = []
    for g in gear:
        cond = _GroundCondition(g)
        if g.case not in BALANCED_GROUND_CASES:
            record.append(_skip(cond, "gear-design-only"))
            continue
        if g.case in GROUND_SIDE_CASES and g.case % 2 == 0:
            record.append(_skip(cond, "side-twin-by-reflection"))
            continue
        entry = loadings.get(g.case)
        if entry is None:
            record.append(_skip(cond, "no-cg-case"))
            continue
        cg, loading = entry
        if loading is None or not loading.derivable:
            record.append(_skip(cond, "loading-not-derivable"))
            continue

        one_wheel = g.case in GROUND_ONE_WHEEL_CASES
        partner = by_case.get(g.case + 1) if g.case in GROUND_SIDE_CASES else None
        wheels = applied_wheels(
            g.legs, one_wheel=one_wheel,
            partner_side_lb=(partner.legs[0].ground_line[2] if partner else None))
        rotation = g.legs[0].rotation_deg
        # The 23.485 family's hand is LANDLOAD's own: ``SMP`` is negative on the
        # odd member (0.5 W inboard to port) and positive on the even one, so the
        # computed case is the PORT drift and its twin the starboard. Every other
        # family lets ``is_handed`` measure it.
        hand = ""
        if partner is not None:
            hand = "L" if g.legs[0].ground_line[2] < 0 else "R"
        case = assemble_ground(project, g, wheels, loading, cg, lift_factor,
                               rotation, case_ref=g.case_ref, hand=hand)
        out.append(case)
        if case.hand:
            twin_ref = partner.case_ref if partner is not None else None
            out.append(handed_twin(case, case_ref=twin_ref))
    return out


@dataclass(frozen=True)
class _GroundCondition:
    """A LANDLOAD case wearing the shape :func:`_skip` expects.

    ``SkippedCondition`` was written around SELECT's conditions, which carry
    ``component``/``label``/``case``. A ground case has all three under different
    names, so this adapts rather than duplicating the record type -- the
    deliverable's completeness statement must read as one list, not two.
    """

    gear: GearCaseLoads

    @property
    def component(self) -> str:
        return "landing_gear"

    @property
    def label(self) -> str:
        return self.gear.description

    @property
    def case(self) -> int:
        return self.gear.case


def skipped_conditions(project: Project) -> List[SkippedCondition]:
    """The F-C7 record alone, for a caller that already has the cases.

    Assembly is re-run, so a caller that wants both takes the sink form of
    :func:`build_balanced_cases` instead -- one pass, one record.
    """
    record: List[SkippedCondition] = []
    build_balanced_cases(project, record)
    return record


def skipped_condition_lines(skipped: Sequence[SkippedCondition]) -> List[str]:
    """The record as text, **one line per reason** -- the single owner of the
    wording every surface states it in (deck ``$`` block, report, UI).

    Grouped rather than one line per condition because the reasons repeat and the
    conditions do not: on ``ga6_normal`` a dozen h-tail, fuselage and ground
    conditions share the one "not a balanced family" sentence, and repeating it
    per condition buried the record it exists to make readable. Reasons appear in
    the order SELECT first hit them; conditions in SELECT's order within each.
    """
    grouped: List[Tuple[str, List[str]]] = []
    index = {}
    for s in skipped:
        if s.code not in index:
            index[s.code] = len(grouped)
            grouped.append((s.reason, []))
        grouped[index[s.code]][1].append(s.name)
    return [f"{reason}: {', '.join(names)}" for reason, names in grouped]


def carry_sources_absent(result: BalancedCaseResult) -> bool:
    """No cut reaction is applied in an assembled case (plan 11 §4's seam rule).

    The wing carry-through is *internal* to a full-span model -- the solver
    recovers it — so applying it as well would react the wing twice. Structural
    here (``assemble`` never reads ``body_loads``); this is the drift guard.
    """
    return not any(ld.source in ("carry", "correction") for ld in result.loads)


#: Title of the F-C7 record row on the ``ModuleResult``. A constant because it is
#: the string the report and the guard test both look the record up by.
SKIPPED_RECORD_TITLE = "Assembly record -- conditions not assembled"


def _skipped_record(skipped: Sequence[SkippedCondition]):
    """The F-C7 record as a :class:`ConditionResult` (review F-C7).

    Emitted **whether or not anything was skipped**: "every condition SELECT
    named assembled" is the statement the deliverable was missing, and a record
    that appears only when something is wrong cannot be told from one that was
    never produced. It carries no ``case_ref`` -- it is a statement about the run,
    not a load case, so it mints no case index row -- and its one value is a
    dimensionless count, which the ULTIMATE boundary passes through unscaled.
    """
    from ..models import ConditionResult, LoadValue

    lines = skipped_condition_lines(skipped)
    note = (" | ".join(lines) if lines else
            "every condition SELECT named was assembled into a balanced case")
    return ConditionResult(
        title=SKIPPED_RECORD_TITLE,
        far_reference="",
        values=[LoadValue("Conditions not assembled", float(len(skipped)), "",
                          key="balanced_skipped_count")],
        note=note,
    )


def run(project: Project) -> ModuleResult:
    """Registry entry point: the balanced cases as a reportable result.

    The last condition is always the F-C7 skipped-conditions record
    (:func:`_skipped_record`), so a consumer of this result can always state what
    the assembled deliverable does *not* cover.
    """
    from ..models import ConditionResult, LoadValue

    skipped: List[SkippedCondition] = []
    cases = build_balanced_cases(project, skipped)
    if not cases:
        raise MissingInputError(
            "no wing or vertical-tail condition has both a V-n point and a "
            "derivable payload loading -- nothing to balance")
    conditions = []
    for c in cases:
        hand = {"R": " starboard", "L": " port"}.get(c.hand, "")
        roll_values = [
            # Applied, not unbalanced: the airplane is *meant* not to balance a
            # rolling case. See BalancedCaseResult.roll_moment_fraction.
            LoadValue("Applied aileron rolling moment", -c.unbal_moment, "lb-in",
                      key="balanced_roll_moment"),
            LoadValue("Roll couple (% of n*W*b/2)",
                      100.0 * c.roll_moment_fraction, "%",
                      key="balanced_roll_moment_pct"),
        ] if c.unbal_moment else []
        unsymmetrical = is_unsymmetrical_htail(c)
        rh, lh = htail_side_loads(c)
        htail_values = [
            # The case's defining applied load and the split that gives it its
            # hand, reported before the motion the mismatch with trim causes.
            LoadValue("Applied horizontal-tail load", htail_load(c), "lb",
                      key="balanced_htail_load"),
            LoadValue("Starboard half", rh, "lb", key="balanced_htail_rh"),
            LoadValue("Port half", lh, "lb", key="balanced_htail_lh"),
            LoadValue("Pitch acceleration", degrees(radians_per_s2(
                (0.0, c.q_dot, 0.0))[1]), "deg/s^2", key="balanced_q_dot"),
        ] if unsymmetrical else []
        lateral = is_lateral(c)
        lateral_values = [
            # The case's defining applied load, reported before the motion it
            # causes: nothing balances it, so the three below ARE its reaction.
            LoadValue("Applied fin side load", fin_load(c), "lb",
                      key="balanced_fin_load"),
            LoadValue("Lateral load factor Ny", c.delta_ny, "g",
                      key="balanced_ny"),
            LoadValue("Yaw acceleration", degrees(radians_per_s2(
                (0.0, 0.0, c.r_dot))[2]), "deg/s^2", key="balanced_r_dot"),
            LoadValue("Roll acceleration", degrees(radians_per_s2(
                (c.p_dot, 0.0, 0.0))[0]), "deg/s^2", key="balanced_p_dot"),
        ] if lateral else []
        # A lateral case names the rule SELECT picked it under (23.441(a)(1)
        # ... 23.443(b)) and a ground case the condition LANDLOAD computed it
        # under (23.479 ... 23.493, R6-C1 -- 23.471 is the family's general
        # sentence, the fallback a ref-less ground case would deserve). The
        # symmetric flight families keep their literals: their CaseRefs name
        # the V-n envelope source (23.333), but the *balancing* of that point
        # is 23.321's requirement, so the row keeps citing it.
        ground = is_ground(c)
        if lateral or unsymmetrical or ground:
            far = (c.case_ref.far_reference if c.case_ref else "") or (
                "23.471" if ground else "23.321")
        else:
            far = "23.349" if c.unbal_moment else "23.321"
        conditions.append(ConditionResult(
            title=(f"Balanced case {c.label}{hand} "
                   f"({case_source_name(c, short=True)}, {c.cg})"),
            far_reference=far,
            values=roll_values + htail_values + lateral_values + [
                LoadValue("Load factor Nz", c.nz, "g", key="balanced_nz"),
                LoadValue("Weight", c.weight_lb, "lb", quantity="mass",
                          key="balanced_weight"),
                LoadValue("Residual Fz (pre-closure)", c.residual_fz, "lb",
                          key="balanced_residual_fz"),
                LoadValue("Residual Fz (% of n*W)",
                          100.0 * c.force_residual_fraction, "%",
                          key="balanced_residual_fz_pct"),
                LoadValue("Residual My (pre-closure)", c.residual_my, "lb-in",
                          key="balanced_residual_my"),
                LoadValue("Residual My (% of n*W*MAC)",
                          100.0 * c.moment_residual_fraction, "%",
                          key="balanced_residual_my_pct"),
                LoadValue("Closure dn", c.delta_n, "g", key="balanced_delta_n"),
                LoadValue("Lumped fuselage Cm moment", c.fuselage_cm, "lb-in",
                          key="balanced_fuselage_cm"),
                LoadValue("Non-wing drag (body-axial)", c.body_axial, "lb",
                          key="balanced_body_axial"),
                LoadValue("Non-wing drag dCD", c.delta_cd, "",
                          key="balanced_delta_cd"),
            ],
            note="; ".join(c.notes),
        ))
    conditions.append(_skipped_record(skipped))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)


__all__ = [
    "AILERON_COUPLE_NOTE",
    "BALANCED_HTAIL_CONDITIONS",
    "BALANCED_VTAIL_CONDITIONS",
    "BALANCED_WING_CONDITIONS",
    "FLIGHT_SOURCE_STEM",
    "GROUND_SOURCE_STEM",
    "HANDEDNESS_TOL",
    "LATERAL_AERO_NOTE",
    "RESIDUAL_GATE",
    "ROLLING_WING_CONDITIONS",
    "SKIPPED_RECORD_TITLE",
    "SKIP_REASONS",
    "SYMMETRIC_WING_CONDITIONS",
    "SkippedCondition",
    "assemble",
    "body_inertia",
    "build_balanced_cases",
    "carry_sources_absent",
    "case_source_name",
    "fin_load",
    "fin_sets",
    "handed_twin",
    "htail_load",
    "htail_sets",
    "htail_side_loads",
    "is_ground",
    "is_handed",
    "is_lateral",
    "is_unsymmetrical_htail",
    "reflect_load",
    "resultant",
    "resultant6",
    "skipped_condition_lines",
    "skipped_conditions",
    "source_case_name",
    "unbalanced_rolling_moment",
    "wing_sets",
]
