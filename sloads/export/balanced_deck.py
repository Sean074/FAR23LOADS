"""The assembled full-span balanced deck -- the mission's primary loads deliverable.

Plan 11 decisions **B-4/B-5**, step **B5**. Conventions:
``docs/10_standard/CONVENTIONS.md``. Physics and residual closure:
:mod:`sloads.modules.balance`.

Every other deck this package writes is a **view**: a per-component free body, cut
out of the airplane, carrying the cut reaction as an applied load and needing a
clamp to stand up. This one is the airplane -- wing tip to wing tip, nose to tail,
aero and inertia together -- and it needs no constraint to hold, because the loads
balance.

How the deck proves that
------------------------
A free-free model cannot simply be handed to a linear static solve; the stiffness
matrix is singular. sbeam's SOL 101 has no inertia relief either (``SUPORT`` is
honoured by the SOL 144 trim partition only, verified 2026-08-08). So the deck
carries a **statically determinate** support -- one node clamped in all six DOF --
and the claim is not that the model is unconstrained but that the constraint does
nothing:

    the recovered reaction at that node IS the case's residual

which the solver computes from its own assembly of the cards, independently of
anything sloads calculated. "Reactions ~ 0" is therefore the free-free
equilibrium proof, not a modelling convenience. The residual before closure is
stated in the ``$`` header so a reader can see how much of the balance was
computed and how much was relieved.

GID bands
---------
The wing needs **two** bands here, which is new: every previous deck carried a
single half-span. Left and right are separate node runs so an antisymmetric case
(plan 11 B7) can load them differently without renumbering anything.

===================  ==============
band                 GIDs
===================  ==============
right wing            ``4001+``
left wing             ``4201+``
centreline            ``4401+`` (fuselage masses, tail load, lumped body Cm)
===================  ==============

The deck allocates its own nodes at each load's true ``(x, y, z)`` rather than
reusing the body deck's ``1001+`` beam line -- see :func:`deck_nodes` for why
flattening the waterlines silently unbalanced it.

What is **not** here
--------------------
No wing carry-through reaction. It is the seam between two free bodies, and in an
assembled model the solver recovers it -- applying it as well would react the wing
twice (plan 11 §4's rule: *a load that a free-body cut introduces is never applied
in the assembled model*). Guarded by
:func:`sloads.modules.balance.carry_sources_absent`.
"""

from __future__ import annotations

import math
import textwrap
from typing import Dict, List, Sequence, Tuple

from ..models import BalancedCaseResult, BalancedLoad, Project
from ..modules.balance import build_balanced_cases, carry_sources_absent
from ..rigid_body import radians_per_s2
from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .coordinates import SBEAM_CID, to_force, to_grid, to_moment
from .sbeam_bridge import _fmt, _sf_str

#: Right-hand wing node run.
BALANCED_WING_R_BASE = 4001
#: Left-hand wing node run -- separate so an antisymmetric case can load the two
#: sides differently without renumbering (plan 11 B7).
BALANCED_WING_L_BASE = 4201
#: Centreline node run -- fuselage masses, the tail air load, the lumped
#: fuselage Cm moment, and every closure point that sits on the centreline.
BALANCED_BODY_BASE = 4401
#: Node run capacity per wing side, and for the centreline run.
_WING_BLOCK = 200
_BODY_BLOCK = 600

#: SUBCASE / load-set ids for the assembled deck.
BALANCED_SID_BASE = 5001


def _units(system: UnitSystem) -> DeliverableUnits:
    return deliverable_units(system, Channel.SOLVER)


def _node_key(load: BalancedLoad) -> Tuple[str, float, float, float]:
    """Identity of the node a load hangs on: its side and its position.

    Loads are grouped by position rather than by index because several sources
    land on the same point -- a body station carries its inertia, its ``delta_n``
    relief and its pitch relief -- and they must share one node or the deck grows
    three coincident grids per item.
    """
    return (load.side, round(load.x, 6), round(load.y, 6), round(load.z, 6))


def deck_nodes(cases: Sequence[BalancedCaseResult],
               project: Project) -> Dict[Tuple[str, float, float, float], int]:
    """``{node key: GID}`` -- one node per distinct **position**, per side.

    Geometry is shared across the subcases (same airplane), so the table is built
    once from all of them; a case that loads a station another does not still
    gets its node.

    Every node is allocated at the load's true ``(x, y, z)``, and the fuselage
    beam's ``1001+`` nodes are deliberately **not** reused. Two reasons, both
    found by checking the deck against its own cards rather than by inspection:

    * the body deck's nodes live on the beam line at ``z = 0``, while the mass
      items they stand for are at real waterlines. The closure's longitudinal
      relief acts through those waterlines, so flattening them loses a real
      pitching moment;
    * an item at the same ``x`` but a different ``z`` (``ga6_normal``'s gear
      wheel at 69 and gear structure at 78) would share a node, and a **ballast**
      item has no beam station at all -- the beam is derived from the untouched
      database, the loading adds a solved ballast row somewhere else entirely.
      Those all collapsed onto one node and cost 3.9-21.9 % of the deck's balance
      while the in-memory case still closed to 1e-13.

    The CONM2 mass model composes with this deck regardless: its cards attach by
    offset, so they do not need identical node numbering.
    """
    counts = {"R": 0, "L": 0, "C": 0}
    bases = {"R": BALANCED_WING_R_BASE, "L": BALANCED_WING_L_BASE,
             "C": BALANCED_BODY_BASE}
    blocks = {"R": _WING_BLOCK, "L": _WING_BLOCK, "C": _BODY_BLOCK}
    out: Dict[Tuple[str, float, float, float], int] = {}
    for case in cases:
        for load in case.loads:
            key = _node_key(load)
            if key in out:
                continue
            side = load.side if load.side in counts else "C"
            if counts[side] >= blocks[side]:
                raise ValueError(
                    f"balanced deck: {side}-side nodes exceed the "
                    f"{blocks[side]}-GID block at {bases[side]}")
            out[key] = bases[side] + counts[side]
            counts[side] += 1
    return out


#: Below this, in deg/s^2, a reported angular acceleration is float-cancellation
#: noise rather than motion. A symmetric case's roll and yaw residuals are zero
#: up to summation order, so the closure returns ~1e-14 deg/s^2 for them --
#: printing that at four significant figures would put a different meaningless
#: number in the deck on every platform, and read as a result. The real
#: accelerations this deck carries run 0.18 to 611 deg/s^2, ten orders above.
_OMEGA_DOT_NOISE = 1e-6


def _deg(rad_per_s2: float) -> float:
    """An angular acceleration in deg/s^2, with numerical noise snapped to zero."""
    value = math.degrees(rad_per_s2)
    return 0.0 if abs(value) < _OMEGA_DOT_NOISE else value


def _fin_load(case: BalancedCaseResult) -> float:
    """The applied fin side load of a lateral case, or 0.0 for every other."""
    return sum(ld.fy for ld in case.loads if ld.source == "vtail-air")


def _header(case: BalancedCaseResult, u: DeliverableUnits) -> List[str]:
    _, _, res_fz = to_force(0.0, 0.0, case.residual_fz, u)
    _, res_my, _ = to_moment(0.0, case.residual_my, 0.0, u)
    _, cm_my, _ = to_moment(0.0, case.fuselage_cm, 0.0, u)
    # What the hand *is* differs between the two handed families, and naming it
    # "roll" on a rudder kick would be wrong: a lateral case's twin is the
    # opposite-sign side load, which happens to roll the airplane as well.
    kind = "roll" if case.unbal_moment else "side load"
    hand = {"R": f" -- STARBOARD {kind} (the computed case)",
            "L": f" -- PORT {kind} (mirror of the starboard case)"}.get(case.hand, "")
    # Angular accelerations are reported in deg/s^2 -- a quantity a reader can
    # judge -- while the calc carries them in the weight-space 1/in the closure
    # solves in. The conversion has one owner; see sloads.rigid_body.
    p_dot, q_dot, r_dot = (_deg(v) for v in
                           radians_per_s2((case.p_dot, case.q_dot, case.r_dot)))
    sentences = [
        f"Balanced case {case.label}{hand} -- V-n point {case.vn_case}, "
        f"loading {case.cg}, Nz = {case.nz:g}",
        f"Case ID: {case.case_ref.case_id if case.case_ref else '(none)'}",
        f"Loads are ULTIMATE (limit x SF={_sf_str(case.safety_factor)}).",
        "FULL SPAN, free-free: aero and inertia together, both wings.",
        f"Residual BEFORE closure: Fz {res_fz:.2f} {u.force.label} "
        f"({case.force_residual_fraction * 100:.3f} % of n*W); "
        f"My {res_my:.0f} {u.moment.label} "
        f"({case.moment_residual_fraction * 100:.3f} % of n*W*MAC).",
        f"Closed in SIX DOF by the rigid-body relief field "
        f"f = -w (n + wdot x r): n = ({case.delta_nx:+.5f}, "
        f"{case.delta_ny:+.5f}, {case.delta_n:+.5f}) g, wdot = "
        f"({p_dot:+.4g}, {q_dot:+.4g}, {r_dot:+.4g}) deg/s^2, plus each "
        "point mass's own inertia as a free moment.",
        f"Lumped fuselage Cm moment applied: {cm_my:.0f} {u.moment.label} "
        "(the trim's airplane-less-tail Cm that the distributed wing does not "
        "carry; it has no distributed form until the body aero moment lands).",
        "The support below is determinate: its reaction IS the residual above.",
    ]
    fin = _fin_load(case)
    if fin:
        _, fin_fy, _ = to_force(0.0, fin, 0.0, u)
        _, _, res_mz = to_moment(0.0, 0.0, case.residual_mz, u)
        sentences.append(
            f"LATERAL case: applied fin side load {fin_fy:.1f} {u.force.label}, "
            f"distributed over the fin span from its root waterline. The "
            f"pre-closure Fy and Mz ({res_mz:.0f} {u.moment.label}) are that "
            "load in full, and are NOT a balance error: nothing in an airplane "
            "cancels a rudder kick -- it yaws and rolls, and the closure above "
            "is that motion. The 1 % residual gate is on the case's symmetric "
            "half, which is unchanged.")
    if case.unbal_moment:
        _, roll_my, _ = to_moment(0.0, case.residual_mx, 0.0, u)
        sentences.append(
            f"ROLLING case: applied aileron couple {roll_my:.0f} "
            f"{u.moment.label} (FAR 23.349), reacted entirely by roll "
            f"acceleration ({case.roll_moment_fraction * 100:.2f} % of "
            "n*W*b/2). That is the physics of an accelerated roll, not an "
            "out-of-balance: the relief is distributed over every mass, and "
            "over the wing span it is WINGINER's own unit-roll shape. The "
            "span carries the larger part of it; the rest is reacted by mass "
            "off the roll axis, which a wing-only model has no term for.")
    sentences += [f"NOTE: {note}" for note in case.notes]

    # Free-field bulk data is 72 columns and every one of these is a comment a
    # human reads; wrapped here rather than hand-broken so a longer number (SI is
    # wider) cannot silently push a line over.
    lines: List[str] = []
    for sentence in sentences:
        lines += [f"$ {ln}" for ln in textwrap.wrap(sentence, width=70,
                                                    subsequent_indent="  ")]
    return lines


def _load_lines(case: BalancedCaseResult, sid: int, nodes, u: DeliverableUnits,
                tol: float = 1e-9) -> List[str]:
    lines: List[str] = []
    for load in case.loads:
        gid = nodes[_node_key(load)]
        sf = case.safety_factor
        fx, fy, fz = to_force(load.fx * sf, load.fy * sf, load.fz * sf, u)
        if max(abs(load.fx), abs(load.fy), abs(load.fz)) * sf > tol:
            lines.append(f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(fx)}, {_fmt(fy)}, {_fmt(fz)}")
        mx, my, mz = to_moment(load.mx * sf, load.my * sf, load.mz * sf, u)
        if max(abs(load.mx), abs(load.my), abs(load.mz)) * sf > tol:
            lines.append(f"MOMENT, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(mx)}, {_fmt(my)}, {_fmt(mz)}")
    return lines


def balanced_deck(project: Project, *,
                  system: UnitSystem = UnitSystem.IMPERIAL,
                  cases: Sequence[BalancedCaseResult] = ()) -> str:
    """The assembled full-span deck: one ``SUBCASE`` per balanced case.

    Raises when no symmetric wing condition assembles -- a deck with no subcases
    would read as a clean result rather than as an absent one.
    """
    u = _units(system)
    cases = list(cases) if cases else build_balanced_cases(project)
    if not cases:
        raise ValueError(
            "no balanced case could be assembled -- every symmetric wing "
            "condition is missing a V-n point or a derivable payload loading "
            "(see modules.balance.build_balanced_cases)")
    for case in cases:
        if not carry_sources_absent(case):
            raise ValueError(
                f"balanced case {case.label} carries a free-body cut reaction; "
                "an assembled model must not apply one (plan 11 §4)")

    nodes = deck_nodes(cases, project)
    support = min(nodes.values())

    head: List[str] = ["SOL 101", "$",
                       "$ ------------------------------------------- BALANCED CASE MAP"]
    for i, case in enumerate(cases):
        head.append(f"$ SUBCASE {BALANCED_SID_BASE + i} = {case.label} -- V-n "
                    f"{case.vn_case} -- {case.cg} -- Nz {case.nz:g}")
    head.append("$")
    for i, case in enumerate(cases):
        sid = BALANCED_SID_BASE + i
        head += [
            f"SUBCASE {sid}",
            f"  LABEL = {case.case_ref.case_id if case.case_ref else case.label}",
            f"  TITLE = {case.label} balanced free-free (Nz={case.nz:g}, {case.cg})",
            "  SPC = 1",
            f"  LOAD = {sid}",
            "  DISPLACEMENT = ALL",
            "  SPCFORCE = ALL",
            "$",
        ]
    head.append("BEGIN BULK")

    bulk: List[str] = [
        "$ ------------------------------------------------------------ NODES",
        f"$ Right wing {BALANCED_WING_R_BASE}+, left wing "
        f"{BALANCED_WING_L_BASE}+, centreline {BALANCED_BODY_BASE}+ (fuselage",
        "$ masses, tail air load, lumped body Cm). Nodes are at each load's true",
        "$ position, not flattened onto a beam line.",
        f"$ Lengths in {u.length.label}.",
        "$ GRID, GID, CP, X1, X2, X3",
    ]
    for key, gid in sorted(nodes.items(), key=lambda kv: kv[1]):
        gx, gy, gz = to_grid(key[1], key[2], key[3], u)
        bulk.append(f"GRID, {gid}, , {_fmt(gx)}, {_fmt(gy)}, {_fmt(gz)}")
    bulk += [
        "$ ------------------------------------------------------- CONSTRAINTS",
        "$ Determinate: one node, six DOF. The recovered reaction IS the residual",
        "$ stated in each case header -- 'reactions ~ 0' is the free-free proof.",
        f"SPC1, 1, 123456, {support}",
        "$ ------------------------------------------------------------ LOADS",
    ]
    for i, case in enumerate(cases):
        sid = BALANCED_SID_BASE + i
        bulk += ["$"] + _header(case, u) + _load_lines(case, sid, nodes, u)

    return "\n".join(head + bulk + ["ENDDATA"]) + "\n"


def write_balanced_deck(project: Project, path: str, *,
                        system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(balanced_deck(project, system=system))


def balanced_case_rows(cases: Sequence[BalancedCaseResult]) -> List[Dict[str, str]]:
    """One row per balanced case: the numbers an engineer needs to trust it.

    The residual and the closure are the case's honesty statement, so they are
    columns of the deliverable rather than a log line.
    """
    return [{
        "Case": c.label,
        "Hand": c.hand or "-",
        "V-n point": str(c.vn_case),
        "Loading": c.cg,
        "Nz": f"{c.nz:.3f}",
        "Residual Fz (% n*W)": f"{c.force_residual_fraction * 100:.3f}",
        "Residual My (% n*W*MAC)": f"{c.moment_residual_fraction * 100:.3f}",
        # Applied, not unbalanced -- see BalancedCaseResult.roll_moment_fraction.
        "Roll couple (% n*W*b/2)": f"{c.roll_moment_fraction * 100:.3f}",
        "Closure dn (g)": f"{c.delta_n:+.5f}",
        "Basis": "LIMIT",
    } for c in cases]


__all__ = [
    "BALANCED_WING_R_BASE",
    "BALANCED_WING_L_BASE",
    "BALANCED_BODY_BASE",
    "BALANCED_SID_BASE",
    "deck_nodes",
    "balanced_deck",
    "write_balanced_deck",
    "balanced_case_rows",
]
