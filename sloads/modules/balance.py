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

**The twins come from reflection, not recomputation** (decisions B-6/B-7). Every
case with antisymmetric content is emitted as a handed pair, the port case being
the mirror image of the starboard one through
:func:`sloads.export.coordinates.reflect_load`. The FAR 23 core never sees
handedness; the id gains an ``L``/``R`` suffix and the unhanded id remains the
physical condition.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Sequence, Tuple

from ..case_ids import handed_case_id
from ..derived_geometry import sync_geometry_derived
from ..export.coordinates import (
    reflect_force,
    reflect_moment,
    reflect_point,
    reflect_side,
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
    VnPoint,
    WingLoadResult,
)
from ..registry import register
from ..rigid_body import (
    InertiaTensor,
    PointMass,
    SelfInertia,
    inertia_tensor,
    relief_force,
    relief_moment,
)
from .airloads import air_load_distribution
from .flight_envelope import build_envelope
from .select import build_critical
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

#: Acceptance gate (plan 11 §6): the residual **before** closure, as a fraction
#: of ``n*W`` for force and ``n*W*MAC`` for moment.
RESIDUAL_GATE = 0.01


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
    a load. Returns 0.0 for a wing with no modelled panel, which is a caller
    error rather than a silent zero -- :func:`assemble` notes it.
    """
    wing_items = sum(it.weight_lb for it in loading.items
                     if component_of(it, project) == MassComponent.WING)
    return wing_items / panel_both_sides if panel_both_sides else 0.0


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

    The three translational DOF stay decoupled ratios ``n = F/W``, because the
    mass set's own centroid *is* the reference point (step C1 solves the ballast
    from it), so a uniform load factor produces no moment. The three rotational
    DOF are **one coupled 3x3 solve** on the assembled inertia tensor: the field
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

    points = [PointMass(w, ld.x - cg.xcg, ld.y, ld.z - cg.zcg)
              for ld, w in masses]
    tensor = inertia_tensor(points, [si for _, si in self_inertia])
    fx, fy, fz, mx, my, mz = residual
    n = (fx / w_total, fy / w_total, fz / w_total)
    omega_dot = tensor.solve((mx, my, mz))

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
             case_ref=None, unb: float = 0.0) -> BalancedCaseResult:
    """Assemble one balanced case and close its residual.

    ``unb`` is the unbalanced rolling moment (FAR 23.349) for an accelerated-roll
    condition; zero makes the case symmetric and is the default, so every
    symmetric caller is unchanged.
    """
    fl = project.flight_loads
    notes: List[str] = []

    wing_r, panel_both, cm_free = wing_sets(project, vn, condition)
    scale = _wing_inertia_scale(loading, project, panel_both)
    if scale == 0.0:
        notes.append("wing panel mass is zero -- wing inertia not modelled")
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

    ref = (cg.xcg, 0.0, cg.zcg)
    residual = resultant6(loads, ref)
    fx, fy, fz, mx, my, mz = residual
    n, omega_dot, tensor = _closure(
        loads, cg, residual, point_mass_self_inertia(loading, project))

    geom = project.geometry.by_name(project.wing_mass.surface)
    return BalancedCaseResult(
        label=condition, vn_case=vn.case, cg=cg.name, nz=vn.nz,
        weight_lb=cg.weight_lb, mac=fl.mac,
        semi_span=geom.leading_edge[-1][1] if geom else 0.0, loads=loads,
        residual_fz=fz, residual_fx=fx, residual_my=my,
        residual_fy=fy, residual_mx=mx, residual_mz=mz,
        delta_n=n[2], delta_nx=n[0], delta_ny=n[1],
        p_dot=omega_dot[0], q_dot=omega_dot[1], r_dot=omega_dot[2],
        closure_inertia=tensor,
        unbal_moment=unb, fuselage_cm=fuselage_cm,
        case_ref=_handed_ref(case_ref, "R") if unb else case_ref,
        hand="R" if unb else "", notes=notes,
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
    the roll relief -- and everything even is untouched, so the twin's vertical,
    longitudinal and pitching balance is *identical* and only its roll reverses.
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


def build_balanced_cases(project: Project) -> List[BalancedCaseResult]:
    """One :class:`BalancedCaseResult` per wing condition SELECT picked -- **two**
    for a condition carrying an unbalanced rolling moment.

    A condition is assembled only when the whole chain exists for it: SELECT
    named it, it has a V-n point, and its CG case resolves to a **derivable**
    loading (step C1). A case whose CG the weight database cannot produce has no
    honest inertia set, and inventing one would put fictitious mass into the very
    balance the case exists to demonstrate.

    A rolling condition (``UNB != 0``) is emitted as a **handed pair** -- the
    computed starboard case and its port mirror (B-6/B-7). A rolling condition
    whose ``UNB`` happens to be zero is emitted once, unhanded: the twins exist
    for cases that have a hand, not for cases that are merely allowed one.
    """
    sync_geometry_derived(project)
    if project.flight_loads is None or project.wing_mass is None:
        raise MissingInputError("balance needs 'flight_loads' and 'wing_mass'")
    envelope = project.envelope or build_envelope(project)
    critical = envelope.critical or build_critical(project)
    vn = {p.case: p for p in envelope.vn}
    cgs = {c.name: c for c in project.flight_loads.cg_cases}
    loadings = {ld.name: ld for ld in derive_case_loadings(project)}

    out: List[BalancedCaseResult] = []
    for cond in critical.conditions:
        if cond.component != "wing" or cond.label not in BALANCED_WING_CONDITIONS:
            continue
        point = vn.get(cond.case)
        if point is None:
            continue
        cg = cgs.get(point.cg)
        loading = loadings.get(point.cg)
        if cg is None or loading is None or not loading.derivable:
            continue
        unb = (unbalanced_rolling_moment(project, cond.label)
               if cond.label in ROLLING_WING_CONDITIONS else 0.0)
        case = assemble(project, cond.label, point, loading, cg,
                        case_ref=cond.case_ref, unb=unb)
        out.append(case)
        if case.hand:
            out.append(handed_twin(case))
    return out


def carry_sources_absent(result: BalancedCaseResult) -> bool:
    """No cut reaction is applied in an assembled case (plan 11 §4's seam rule).

    The wing carry-through is *internal* to a full-span model -- the solver
    recovers it — so applying it as well would react the wing twice. Structural
    here (``assemble`` never reads ``body_loads``); this is the drift guard.
    """
    return not any(ld.source in ("carry", "correction") for ld in result.loads)


def run(project: Project) -> ModuleResult:
    """Registry entry point: the balanced cases as a reportable result."""
    from ..models import ConditionResult, LoadValue

    cases = build_balanced_cases(project)
    if not cases:
        raise MissingInputError(
            "no symmetric wing condition has both a V-n point and a derivable "
            "payload loading -- nothing to balance")
    conditions = []
    for c in cases:
        hand = {"R": " starboard roll", "L": " port roll"}.get(c.hand, "")
        roll_values = [
            # Applied, not unbalanced: the airplane is *meant* not to balance a
            # rolling case. See BalancedCaseResult.roll_moment_fraction.
            LoadValue("Applied aileron rolling moment", -c.unbal_moment, "lb-in",
                      key="balanced_roll_moment"),
            LoadValue("Roll couple (% of n*W*b/2)",
                      100.0 * c.roll_moment_fraction, "%",
                      key="balanced_roll_moment_pct"),
        ] if c.unbal_moment else []
        conditions.append(ConditionResult(
            title=f"Balanced case {c.label}{hand} (V-n {c.vn_case}, {c.cg})",
            far_reference="23.349" if c.unbal_moment else "23.321",
            values=roll_values + [
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
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)


__all__ = [
    "SYMMETRIC_WING_CONDITIONS",
    "ROLLING_WING_CONDITIONS",
    "BALANCED_WING_CONDITIONS",
    "RESIDUAL_GATE",
    "wing_sets",
    "body_inertia",
    "resultant",
    "resultant6",
    "reflect_load",
    "handed_twin",
    "unbalanced_rolling_moment",
    "assemble",
    "build_balanced_cases",
    "carry_sources_absent",
]
