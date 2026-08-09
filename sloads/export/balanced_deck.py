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

from typing import Dict, List, Sequence, Tuple

from ..models import BalancedCaseResult, BalancedLoad, Project
from ..modules.balance import build_balanced_cases, carry_sources_absent
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


def _header(case: BalancedCaseResult, u: DeliverableUnits) -> List[str]:
    _, _, res_fz = to_force(0.0, 0.0, case.residual_fz, u)
    _, res_my, _ = to_moment(0.0, case.residual_my, 0.0, u)
    _, cm_my, _ = to_moment(0.0, case.fuselage_cm, 0.0, u)
    lines = [
        f"$ Balanced case {case.label} -- V-n point {case.vn_case}, "
        f"loading {case.cg}, Nz = {case.nz:g}",
        f"$ Case ID: {case.case_ref.case_id if case.case_ref else '(none)'}",
        f"$ Loads are ULTIMATE (limit x SF={_sf_str(case.safety_factor)}).",
        "$ FULL SPAN, free-free: aero and inertia together, both wings.",
        f"$ Residual BEFORE closure: Fz {res_fz:.2f} {u.force.label} "
        f"({case.force_residual_fraction * 100:.3f} % of n*W); "
        f"My {res_my:.0f} {u.moment.label} "
        f"({case.moment_residual_fraction * 100:.3f} % of n*W*MAC).",
        f"$ Closed by dn = {case.delta_n:+.5f} g plus a self-equilibrating pitch "
        "relief; both are mass-proportional.",
        f"$ Lumped fuselage Cm moment applied: {cm_my:.0f} {u.moment.label} "
        "(the trim's airplane-less-tail Cm that the distributed wing does not",
        "$   carry; it has no distributed form until the body aero moment lands).",
        "$ The support below is determinate: its reaction IS the residual above.",
    ]
    for note in case.notes:
        lines.append(f"$ NOTE: {note}")
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
        "V-n point": str(c.vn_case),
        "Loading": c.cg,
        "Nz": f"{c.nz:.3f}",
        "Residual Fz (% n*W)": f"{c.force_residual_fraction * 100:.3f}",
        "Residual My (% n*W*MAC)": f"{c.moment_residual_fraction * 100:.3f}",
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
