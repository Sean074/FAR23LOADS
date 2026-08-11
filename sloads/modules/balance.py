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
the ``WING``-tagged items of the case's derived loading (step B1/C1), spread over
WINGINER's spanwise shape -- decision B-2 and plan 11 §4. Taking it from
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
the fuselage's Munk moment: measured at **+4.3 to +6.3 %** of ``n*W*MAC`` across
the fixtures, positive (destabilising), and with no distributed carrier until
backlog item M4-19 lands the Multhopp/Nelson body moment. It is applied here as a
single free moment on the fuselage (``source="fuselage-cm"``), which preserves the
total exactly and is labelled as lumped wherever it is rendered. Omitting it
would leave a systematic ~5 % moment residual that the closure would then absorb
silently -- a real aero load disguised as a correction.

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
programs, so ``n_y`` and the yaw acceleration are **over-stated** -- conservative
for the inertia they drive on every component, and not the airplane's real
accelerations. That is said in-band, on every lateral case, through
:data:`LATERAL_AERO_NOTE`. Its magnitude is stated as *unknown*, because
quantifying it is building the missing model; this is the weaker of the suite's
two honesty statements and is not dressed up as the stronger one (the lumped
fuselage ``Cm``, whose size can be quoted).

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

from dataclasses import dataclass, replace
from math import degrees
from typing import List, Optional, Sequence, Tuple

from ..case_ids import handed_case_id
from ..derived_geometry import sync_geometry_derived
from ..export.coordinates import (
    reflect_force,
    reflect_moment,
    reflect_point,
    reflect_side,
    tail_force_to_airplane,
    tail_station_to_airplane,
    tail_torsion_to_airplane,
)
from ..mass_distribution import (
    CaseLoading,
    MassComponent,
    assembly_distributes_mass,
    component_of,
    derive_case_loadings,
)
from ..models import (
    BalancedCaseResult,
    BalancedLoad,
    CgCase,
    MissingInputError,
    ModuleResult,
    Project,
    TailSpanResult,
    VnPoint,
    WingLoadResult,
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

#: The L-7 statement of record, carried in-band on every lateral case: on the
#: result's ``notes``, hence in the deck header and the UI. The *direction* of
#: the error is stated, not merely its existence -- and its magnitude is stated
#: as unknown, because quantifying it is building the missing model.
LATERAL_AERO_NOTE = (
    "the fin is the only lateral aerodynamic load this suite computes -- "
    "fuselage and wing side force in sideslip are not modelled, so n_y and the "
    "yaw acceleration are OVER-STATED (by an unknown amount) and the inertia "
    "they drive is conservative on every component; the fin's own design load "
    "is SELECT's, unchanged")


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
        "not one of the balanced families this analysis assembles -- fuselage, "
        "ground and one-engine-out conditions are covered by the per-component "
        "analyses only"),
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
        "its V-n point names a loading this project does not define, so the "
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

    @property
    def name(self) -> str:
        """The condition, named as SELECT names it."""
        where = f" (V-n {self.case})" if self.case is not None else ""
        return f"{self.component} {self.label}{where}"


def _skip(cond, code: str) -> SkippedCondition:
    return SkippedCondition(component=cond.component, label=cond.label,
                            case=cond.case, code=code, reason=SKIP_REASONS[code])


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


def wing_sets(project: Project, vn: VnPoint,
              condition: str) -> Tuple[List[BalancedLoad], float, float]:
    """Starboard wing air + inertia loads, at ``vn``'s own flight condition.

    Returns ``(loads, wing_item_weight, cm_free_total)`` where ``cm_free_total``
    is the section-``Cm`` free moment of **both** wings -- the caller needs it to
    work out the fuselage's share of the trim moment.
    """
    wm = project.wing_mass
    geom = project.geometry.by_name(wm.surface)
    aero = project.aero.by_name(wm.surface)
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
    cm_free = 2.0 * sum(ml)

    # Inertia: the loading's own WING items, spread over WINGINER's shape.
    # Inertia strips take WINGINER's **spanwise shape** at the 50 % chord (where
    # it models the panel mass CG -- its torsion carries ``-w*(c50x - c25x)`` for
    # exactly that reason), then are shifted bodily in x and z so the set's
    # centroid is the WING items' own.
    #
    # The split of authority is decision B-2: the item database owns *where* the
    # mass is, WINGINER owns *how it is spread along the span*. Without the shift
    # the two disagree -- ga6's wing item sits at x 97.87 while the 50 % chord
    # line runs 78-95 -- and the difference lands in the pitching residual as a
    # moment the trim does not have, because the trim lumps all mass at the CG.
    # It is worth 2.8-4.3 % of ``n*W*MAC`` on ``concept_regional_jet``.
    u = inertia_units(geom, wm)
    panel = sum(u.w)
    strips = [(i, w) for i, w in enumerate(u.w) if w]
    if strips and panel:
        x_shape = sum(w * u.c50x[i] for i, w in strips) / panel
        z_shape = sum(w * u.z[i] for i, w in strips) / panel
    else:
        x_shape = z_shape = 0.0
    for i, w in strips:
        loads.append(BalancedLoad(
            x=u.c50x[i] - x_shape, y=u.ye[i], z=u.z[i] - z_shape,
            fz=-w * vn.nz, weight_lb=w, source="wing-inertia", side="R"))
    return loads, 2.0 * panel, cm_free


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
    wing_items = sum(it.weight_lb for it in loading.items
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
        for it in loading.items
        if not assembly_distributes_mass(component_of(it, project))
    ]


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
    return sum(ld.fz for ld in case.loads if ld.source == "htail-air")


def htail_side_loads(case: BalancedCaseResult) -> Tuple[float, float]:
    """``(starboard, port)`` halves of the applied h-tail load -- SELECT's own
    ``RH``/``LH`` on the computed case, and swapped on its port twin.

    Split by the strip's side of the centreline rather than by its ``side`` tag,
    so the two agree only because the tag is right -- a reflection that failed to
    swap the tags would show up here rather than being echoed back.
    """
    rh = sum(ld.fz for ld in case.loads if ld.source == "htail-air" and ld.y > 0)
    lh = sum(ld.fz for ld in case.loads if ld.source == "htail-air" and ld.y < 0)
    return rh, lh


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
    return sum(ld.fy for ld in case.loads if ld.source == "vtail-air")


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
    if any(ld.mx or ld.mz for ld in applied):
        return True
    if sum(abs(ld.fy) for ld in applied) > HANDEDNESS_TOL * n_w:
        return True
    # The rolling test reads the **net**, unlike the lateral one above, and for
    # the opposite reason: a mirror-symmetric set cancels to exactly zero here
    # (each pair contributes ``y*f + (-y)*f``), so the net is a clean signal
    # rather than a near-cancellation of large parts. Measured, the two
    # populations do not overlap: symmetric wing cases net 1e-17 of ``n*W*b/2``
    # in roll and the 23.427(a) case nets 6e-3 to 1.7e-2.
    if ref_length <= 0.0:
        return False
    roll = sum(ld.mx + ld.y * ld.fz - ld.z * ld.fy for ld in applied)
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
    for it in loading.items:
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
    fx = sum(ld.fx for ld in loads)
    fy = sum(ld.fy for ld in loads)
    fz = sum(ld.fz for ld in loads)
    mx = sum(ld.mx + (ld.y - ref[1]) * ld.fz - (ld.z - ref[2]) * ld.fy
             for ld in loads)
    my = sum(ld.my + (ld.z - ref[2]) * ld.fx - (ld.x - ref[0]) * ld.fz
             for ld in loads)
    mz = sum(ld.mz + (ld.x - ref[0]) * ld.fy - (ld.y - ref[1]) * ld.fx
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
    PHAA the closure gives 0.661 g against the fixture's entered ``nx`` of
    0.6065, the difference being the same strip-quadrature-versus-closed-form gap
    that sets the vertical residual floor. Leaving it open would put 17-26 % of
    ``n*W`` into the support reaction and make "reactions ~ 0" untrue in a file
    that still solved.

    The relief is spread over **the inertia loads already in the model**, not
    over the raw item list. Those are the same masses, but at the places the
    assembled model actually carries them -- wing mass out along the span rather
    than on the centreline where the database enters it -- so the deck's internal
    load path stays physical and no relief lands on a node the airplane has no
    mass at.
    """
    zero = (0.0, 0.0, 0.0)
    masses = [(ld, ld.weight_lb) for ld in loads if ld.weight_lb]
    w_total = sum(w for _, w in masses)
    if not w_total:
        return zero, zero, InertiaTensor()

    # The centroid of the masses the model actually carries -- the one point the
    # relief field is exact about (see the docstring).
    cx = sum(ld.x * w for ld, w in masses) / w_total
    cy = sum(ld.y * w for ld, w in masses) / w_total
    cz = sum(ld.z * w for ld, w in masses) / w_total
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
            only = tuple(omega_dot[i] if i == axis else 0.0 for i in range(3))
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
    fl = project.flight_loads
    notes: List[str] = []

    wing_r, panel_both, cm_free = wing_sets(project, vn, condition)
    scale = _wing_inertia_scale(loading, project, panel_both)
    if scale == 0.0:
        notes.append("the loading carries no WING-tagged item mass -- "
                     "wing inertia not modelled")
    elif abs(scale - 1.0) > 1e-6:
        notes.append(
            f"wing inertia scaled x{scale:.4f} onto the loading's WING items "
            f"({scale * panel_both:.0f} lb); WINGINER's integrated panel mass is "
            f"{panel_both:.0f} lb")
    wing_items = [it for it in loading.items
                  if component_of(it, project) == MassComponent.WING]
    w_wing = sum(it.weight_lb for it in wing_items)
    x_wing = (sum(it.weight_lb * it.x for it in wing_items) / w_wing) if w_wing else 0.0
    z_wing = (sum(it.weight_lb * it.z for it in wing_items) / w_wing) if w_wing else 0.0
    wing_r = [
        replace(ld, fz=ld.fz * scale, weight_lb=ld.weight_lb * scale,
                x=ld.x + x_wing, z=ld.z + z_wing)
        if ld.source == "wing-inertia" else ld
        for ld in wing_r
    ]

    loads: List[BalancedLoad] = list(wing_r) + _mirror(wing_r)
    if htail:
        loads += list(htail)
        applied_ht = sum(ld.fz for ld in htail)
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
    wing_about_ac = sum(
        ld.my + (ld.z - fl.zw) * ld.fx - (ld.x - fl.xw) * ld.fz
        for ld in loads if ld.source == "wing-air")
    fuselage_cm = vn.m_wf - wing_about_ac
    loads.append(BalancedLoad(x=fl.xw, y=0.0, z=fl.zw, my=fuselage_cm,
                              source="fuselage-cm", side="C"))

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
        notes.append(
            f"aileron rolling moment {-unb:+.0f} lb-in applied as a lumped free "
            "couple: the suite has no aileron spanwise geometry, so its own lift "
            "increment is not distributed (WINGINER carries only the inertia "
            "reaction, which IS distributed here)")

    if lateral:
        loads += list(lateral)
        notes.append(LATERAL_AERO_NOTE)

    geom = project.geometry.by_name(project.wing_mass.surface)
    semi_span = geom.leading_edge[-1][1] if geom else 0.0
    ref = (cg.xcg, 0.0, cg.zcg)
    handed = is_handed(loads, abs(vn.nz * cg.weight_lb), semi_span)
    residual = resultant6(loads, ref)
    fx, fy, fz, mx, my, mz = residual
    n, omega_dot, tensor = _closure(
        loads, cg, residual, point_mass_self_inertia(loading, project))

    return BalancedCaseResult(
        label=condition, vn_case=vn.case, cg=cg.name, nz=vn.nz,
        weight_lb=cg.weight_lb, mac=fl.mac,
        semi_span=semi_span, loads=loads,
        residual_fz=fz, residual_fx=fx, residual_my=my,
        residual_fy=fy, residual_mx=mx, residual_mz=mz,
        delta_n=n[2], delta_nx=n[0], delta_ny=n[1],
        p_dot=omega_dot[0], q_dot=omega_dot[1], r_dot=omega_dot[2],
        closure_inertia=tensor,
        unbal_moment=unb, fuselage_cm=fuselage_cm,
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


def handed_twin(case: BalancedCaseResult) -> BalancedCaseResult:
    """The opposite-hand twin of an antisymmetric case, by reflection (B-6).

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
        case_ref=_handed_ref(ref, reflect_side(case.hand)),
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
    cgs = {c.name: c for c in project.flight_loads.cg_cases}
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
        point = vn.get(cond.case)
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
    return out


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
        # ... 23.443(b)); the symmetric families keep the two references they
        # have always reported, so no shipped row moves.
        far = ((c.case_ref.far_reference if c.case_ref else "") or "23.321"
               ) if (lateral or unsymmetrical) else (
            "23.349" if c.unbal_moment else "23.321")
        conditions.append(ConditionResult(
            title=f"Balanced case {c.label}{hand} (V-n {c.vn_case}, {c.cg})",
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
            ],
            note="; ".join(c.notes) or None,
        ))
    conditions.append(_skipped_record(skipped))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)


__all__ = [
    "SYMMETRIC_WING_CONDITIONS",
    "ROLLING_WING_CONDITIONS",
    "BALANCED_WING_CONDITIONS",
    "BALANCED_VTAIL_CONDITIONS",
    "BALANCED_HTAIL_CONDITIONS",
    "HANDEDNESS_TOL",
    "LATERAL_AERO_NOTE",
    "RESIDUAL_GATE",
    "SKIP_REASONS",
    "SKIPPED_RECORD_TITLE",
    "SkippedCondition",
    "wing_sets",
    "fin_load",
    "fin_sets",
    "htail_sets",
    "htail_load",
    "htail_side_loads",
    "is_unsymmetrical_htail",
    "is_lateral",
    "is_handed",
    "body_inertia",
    "resultant",
    "resultant6",
    "reflect_load",
    "handed_twin",
    "unbalanced_rolling_moment",
    "assemble",
    "build_balanced_cases",
    "skipped_conditions",
    "skipped_condition_lines",
    "carry_sources_absent",
]
