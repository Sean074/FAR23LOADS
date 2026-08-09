"""Solve an exported deck in the real sbeam -- the round-trip gate's machinery.

Design note: ``docs/30_future/10_sbeam_roundtrip_ci_harness_plan.md`` (decisions
S-1...S-9). Sibling authority, which this module consumes rather than
reimplements: :mod:`sloads.export.equilibrium`.

The two export-boundary gates answer different questions. ``equilibrium``
re-derives a deck's resultant **from its own card text** -- "do the cards sum to
what the header claims?". This one hands the deck to **another program** and asks
"does a real solver read this file and recover the same loads?". Only the second
one catches card syntax sbeam rejects, a GID reference to nothing, a frame or
sign mismatch, or a case-control error -- and only the second one is evidence
about the mission's actual claim, which is that the deck *solves*.

Production module, test-only *use* -- exactly as ``equilibrium`` is. Nothing in
the shipping path imports it today, and it must stay that way: acceptance point 6
of the design note is that this step changes no exported byte. It lives in
``sloads/`` rather than ``tests/`` because a later runtime "validate this deck"
surface has to consume this authority instead of hand-rolling a second one.

What has to be wrapped, and why
-------------------------------
Only the wing deck is solvable as exported: ``stick_model_bdf`` writes ``SOL
101`` with ``GRID``/``CBAR``/``PBAR``/``MAT1``/``SPC1``. The body and tail decks
are load-cards-only, and the assembled balanced deck carries case control,
``GRID``s and a determinate ``SPC1`` but **no elements** -- it is a load set on a
node cloud, which is all a load deliverable needs to be and is singular to a
linear static solve.

:func:`wrap_as_stick_model` supplies the missing structure from the deck's own
``GRID`` cards (plan 07 decision E-5 put them there; without them this is
unbuildable). It invents no geometry and it is **test-only**: it is never written
by the CLI or the GUI, and L-1 supersedes it with a real assembled stick model.

The support is the point, not a workaround
------------------------------------------
sbeam's SOL 101 has no inertia relief -- ``SUPORT`` is honoured by the SOL 144
trim partition only -- so a free-free deck cannot simply be solved. It is
constrained instead at a **statically determinate** set of DOFs, which carries
exactly the residual the applied set fails to balance, and the assertion is that
the recovered reaction is **zero**. That is a stronger statement than the card
sum: it proves free-free equilibrium through the solver's own assembly, using the
lever arms *it* computes from the deck's ``GRID`` cards rather than sloads' idea
of them. A deck that closes on paper but reacts non-zero here has a geometry
error no card sum can see.

.. rubric:: The 3-2-1 scheme is degenerate on a beam line

The design note proposed the body support as "``z`` at two stations plus ``x`` at
one" -- the classical 3-2-1. That is three constraints, not six, and on a
**collinear** node set it cannot be completed into a determinate one: the
fuselage deck's nodes all lie on ``y = z = 0``, so no combination of translation
constraints restrains rotation about the beam axis, and the solve is singular.
Beam elements carry rotational stiffness at their nodes, so the collinear analog
of 3-2-1 constrains that rotation directly: ``1234`` at the first station and
``23`` at the last -- six constraints, no redundancy, reactions still fixed by
statics alone. See :data:`Support`.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Sequence, Tuple

from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .coordinates import to_pressure
from .equilibrium import parse_cards
from .sbeam_bridge import _MAT1_E, _MAT1_NU, _PBAR_A, _PBAR_I, _PBAR_J, _fmt

Vec3 = Tuple[float, float, float]

#: SID of the constraint set the wrapper emits, and that its synthesised case
#: control selects. Matches ``stick_model_bdf``'s and ``balanced_deck``'s, so a
#: wrapped deck and a shipped one name their constraints the same way.
SPC_SID = 1


class SbeamUnavailable(RuntimeError):
    """Raised when a solve is requested and sbeam is not installed.

    Its own type so the caller can distinguish "the solver is absent" (a skip,
    or a hard failure under ``SLOADS_REQUIRE_SBEAM=1`` -- decision S-7) from
    "the solver rejected the deck", which is the finding this gate exists for.
    """


class Support(Enum):
    """Which DOFs the wrapper constrains, and where.

    ``CLAMPED_FIRST``
        All six DOF at the first node. The tail deck's convention: its reaction
        is then the deck's own resultant about the leading-edge chord station,
        which is plan 07's E-2 tail reference recovered independently.
    ``DETERMINATE``
        ``1234`` at the first node and ``23`` at the last -- six constraints on a
        collinear beam line, no redundancy (see the module docstring). The body
        deck's convention, where the claim under test is that the reaction is
        **zero**.
    ``DECK``
        The deck already carries its own ``SPC1``; emit none. The assembled
        balanced deck's convention -- its determinate six-DOF support *is* the
        deliverable's own statement, so the harness must test that one, not a
        support the harness chose.
    """

    CLAMPED_FIRST = "clamped_first"
    DETERMINATE = "determinate"
    DECK = "deck"


class Topology(Enum):
    """How the wrapper connects the deck's nodes into a solvable structure.

    ``CHAIN``
        One ``CBAR`` between consecutive nodes in ``x`` order -- the body and
        tail decks, which *are* beam lines (``y = z = 0``). Keeps the recovered
        element forces meaningful as internal loads, which ``STAR`` would not:
        the aft-most element's shear closing to zero is the fuselage deck's
        terminal-``Myy`` claim, verified downstream.
    ``STAR``
        One ``CBAR`` from the support node to every other node -- the assembled
        full-span deck, whose nodes are a three-dimensional cloud (both wings,
        the centreline, real waterlines) with no chain order to speak of. Still
        a tree, so still determinate: the support reaction remains the applied
        resultant and "reactions ~ 0" keeps its meaning. The element forces are
        not internal loads of anything real, and nothing asserts them.
    """

    CHAIN = "chain"
    STAR = "star"


# --------------------------------------------------------------------------- #
# Wrapping a cards-only (or element-less) deck into a solvable model
# --------------------------------------------------------------------------- #
def _units(system: UnitSystem) -> DeliverableUnits:
    return deliverable_units(system, Channel.SOLVER)


def _orientation(a: Vec3, b: Vec3) -> Vec3:
    """A ``CBAR`` orientation vector not parallel to the element axis.

    Tried in ``z, y, x`` order so a beam line along ``x`` (body, tail) and a
    wing-ward element both keep the ``(0, 0, 1)`` convention the shipped stick
    model uses, and only a genuinely vertical element takes another.
    """
    ax, ay, az = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    norm = (ax * ax + ay * ay + az * az) ** 0.5
    if norm == 0.0:
        raise ValueError("zero-length element: two GRIDs share a location")
    ux, uy, uz = ax / norm, ay / norm, az / norm
    for v in ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)):
        cross = (uy * v[2] - uz * v[1], uz * v[0] - ux * v[2], ux * v[1] - uy * v[0])
        if max(abs(c) for c in cross) > 1e-6:
            return v
    raise AssertionError("no orientation vector is independent of the axis")


def _property_lines(u: DeliverableUnits) -> List[str]:
    """``MAT1``/``PBAR`` placeholder section, converted to the deck's units.

    Imported from :mod:`sloads.export.sbeam_bridge` rather than redeclared, so
    the "a determinate structure's reactions are stiffness-independent" claim
    stays true in exactly one place.
    """
    return [
        "$ ---------------------------------------------- WRAPPER PROPERTIES",
        "$ Placeholder section (test-only wrapper); the support is determinate,",
        "$ so the recovered reactions do not depend on these values.",
        f"MAT1, 1, {_fmt(to_pressure(_MAT1_E, u))}, , {_MAT1_NU}, 0.0",
        f"PBAR, 1, 1, {_fmt(_PBAR_A * u.length.factor ** 2)}, "
        f"{_fmt(_PBAR_I * u.length.factor ** 4)}, "
        f"{_fmt(_PBAR_I * u.length.factor ** 4)}, "
        f"{_fmt(_PBAR_J * u.length.factor ** 4)}",
    ]


#: First ``RBE2`` id. Rigid elements share NASTRAN's element-id space, so the
#: ties are numbered well clear of the ``CBAR`` chain rather than interleaved.
_RBE2_EID_BASE = 900001


def _collapse(grids: Dict[int, Vec3],
              order: Sequence[int]) -> List[Tuple[int, List[int]]]:
    """``[(representative GID, [coincident GIDs])]``, in the given order.

    Two nodes at the same point are not a defect and not a duplicate: the
    fuselage deck of ``concept_regional_jet`` carries the tail air load at
    exactly the station of a mass lump, and both are real, separately-numbered
    loads. They cannot be joined by an element (it would have zero length and no
    axis), so the representative takes the chain and the rest are tied to it
    rigidly -- which is what coincident nodes mean.
    """
    out: List[Tuple[int, List[int]]] = []
    seen: Dict[Tuple[float, float, float], int] = {}
    for gid in order:
        key = (round(grids[gid][0], 6), round(grids[gid][1], 6),
               round(grids[gid][2], 6))
        if key in seen:
            out[seen[key]][1].append(gid)
        else:
            seen[key] = len(out)
            out.append((gid, []))
    return out


def _element_lines(grids: Dict[int, Vec3],
                   runs: Sequence[Sequence[Tuple[int, List[int]]]],
                   topology: Topology) -> List[str]:
    lines = ["$ ------------------------------------------------ WRAPPER ELEMENTS"]
    eid = 1
    ties: List[str] = []
    for collapsed in runs:
        nodes = [rep for rep, _ in collapsed]
        if topology is Topology.CHAIN:
            pairs = list(zip(nodes, nodes[1:]))
        else:
            pairs = [(nodes[0], gid) for gid in nodes[1:]]
        for ga, gb in pairs:
            vx, vy, vz = _orientation(grids[ga], grids[gb])
            lines.append(f"CBAR, {eid}, 1, {ga}, {gb}, {vx}, {vy}, {vz}")
            eid += 1
        for rep, tied in collapsed:
            if tied:
                ties.append(f"RBE2, {_RBE2_EID_BASE + len(ties)}, {rep}, 123456, "
                            + ", ".join(str(g) for g in tied))
    if ties:
        lines += ["$ Coincident nodes, rigidly tied (see roundtrip._collapse)."] + ties
    return lines


def _supportable(run: Sequence[Tuple[int, List[int]]]) -> List[int]:
    """The nodes of a collapsed run that may carry a constraint.

    Representatives only -- a node tied by ``RBE2`` is a dependent DOF, and
    constraining one is an error rather than a support -- and among those, only
    the ones that tie nothing. **That second exclusion is a solver workaround,
    and it is load-bearing:** sbeam's ``recover_reactions`` subtracts the raw
    applied vector at the constrained DOFs, so a load that a rigid element
    transfers *onto* a constrained node is never subtracted and comes back out
    as reaction. Measured on ``concept_regional_jet``'s fuselage deck, whose tail
    air load sits at exactly the station of a mass lump: the aft support reported
    1738.13 lb against an applied set that closes to 0.007 lb -- to the pound,
    the tied node's own load.

    Supporting elsewhere sidesteps it entirely and costs nothing: determinacy
    needs two distinct positions, not two particular ones.
    """
    return [rep for rep, tied in run if not tied]


def _constraint_lines(support: Support,
                      runs: Sequence[Sequence[Tuple[int, List[int]]]]) -> List[str]:
    if support is Support.DECK:
        return []
    lines = ["$ --------------------------------------------- WRAPPER CONSTRAINTS"]
    for run in runs:
        free = _supportable(run)
        if not free:
            raise ValueError(
                "every node in this run is tied to another -- there is nowhere "
                "to put a support whose reaction can be trusted")
        if support is Support.CLAMPED_FIRST or len(free) == 1:
            # A one-node run has no beam to be determinate along; clamp it.
            lines.append(f"SPC1, {SPC_SID}, 123456, {free[0]}")
        else:
            # Six constraints, no redundancy, on a collinear node set -- 1234 at
            # one end and 23 at the other. See the module docstring on why the
            # 3-2-1 translation scheme is degenerate here.
            lines.append(f"SPC1, {SPC_SID}, 1234, {free[0]}")
            lines.append(f"SPC1, {SPC_SID}, 23, {free[-1]}")
    return lines


def _case_control(sids: Sequence[int], title: str) -> List[str]:
    lines = ["SOL 101", "$",
             f"$ Test-only stick wrapper -- {title}",
             "$ NOT a sloads deliverable; see sloads/export/roundtrip.py.", "$"]
    for sid in sids:
        lines += [
            f"SUBCASE {sid}",
            f"  LABEL = wrapped SID {sid}",
            f"  SPC = {SPC_SID}",
            f"  LOAD = {sid}",
            "  DISPLACEMENT = ALL",
            "  SPCFORCE = ALL",
            "  FORCE = ALL",
            "$",
        ]
    lines.append("BEGIN BULK")
    return lines


def wrap_as_stick_model(deck_text: str, *, support: Support,
                        system: UnitSystem = UnitSystem.IMPERIAL,
                        topology: Topology = Topology.CHAIN,
                        groups: Sequence[Sequence[int]] = (),
                        title: str = "sloads deck") -> str:
    """Make a load deck solvable, using only the geometry it already carries.

    Consumes the deck's own ``GRID`` cards -- it invents no nodes and moves none.
    A deck that already carries case control (the assembled balanced deck) keeps
    it, and only the missing bulk is appended; a cards-only deck (body, tail)
    additionally gets ``SOL 101`` and one ``SUBCASE`` per load set.

    ``groups`` names the deck's **separate structures**, each getting its own
    element run and its own support. It is not a refinement: the tail deck holds
    two disjoint beams -- the h-tail and the v-tail, each a chord line stated
    from its own leading edge -- so their stations are *coincident in space*
    (both run from ``x = 0`` at ``y = z = 0``, the decks' "component in
    isolation" convention). Chaining the deck's nodes as one run therefore
    produces zero-length elements, which is what running this against
    ``ga6_normal`` found. Default: every node in one group.

    **Test-only.** This is not a sloads deliverable, it is never written by the
    CLI or the GUI, and it does not pre-empt L-1.
    """
    grids, cbars, _, forces, moments = parse_cards(deck_text)
    if not grids:
        raise ValueError(
            "deck carries no GRID cards -- there is no geometry to build a "
            "stick model from (control-surface decks are out of scope, S-3)")
    if cbars:
        raise ValueError(
            "deck already carries CBAR elements -- it is solvable as exported "
            "and must be handed to solve_deck() unwrapped, so the harness tests "
            "the shipped deck rather than a wrapped copy of it")

    u = _units(system)

    def _ordered(gids):
        # Beam-line order for CHAIN; for STAR only the first node matters, and
        # sorting keeps the support choice deterministic across runs and unit
        # systems.
        return sorted(gids, key=lambda gid: (grids[gid][0], grids[gid][1],
                                             grids[gid][2], gid))

    if groups:
        named = {gid for group in groups for gid in group}
        missing = set(grids) - named
        if missing:
            raise ValueError(
                f"GRIDs {sorted(missing)} are in no group -- an unattached node "
                "makes the stiffness matrix singular, so the omission must be "
                "deliberate rather than silent")
        runs = [_collapse(grids, _ordered(group)) for group in groups]
    else:
        runs = [_collapse(grids, _ordered(grids))]

    if support is Support.DECK:
        # The deck picked its own support before the wrapper existed, so the
        # tie-vs-reaction trap in _supportable() has to be checked rather than
        # avoided -- silently reporting a tied node's load as the residual of the
        # airplane's balance is precisely the wrong failure here.
        tied_owners = {rep for run in runs for rep, tied in run if tied}
        _, _, deck_spc, _, _ = parse_cards(deck_text)
        held = {gid for _, _, gids in deck_spc for gid in gids}
        clash = sorted(held & tied_owners)
        if clash:
            raise ValueError(
                f"the deck constrains GID(s) {clash}, which the wrapper must tie "
                "coincident nodes to -- sbeam would report the tied node's load "
                "as a reaction (see roundtrip._supportable)")

    sids = sorted(set(forces) | set(moments))

    bulk = (_property_lines(u)
            + _element_lines(grids, runs, topology)
            + _constraint_lines(support, runs))

    if "BEGIN BULK" in deck_text:
        # The deck brought its own case control and constraints (the assembled
        # full-span deck). Splice the wrapper's bulk in ahead of ENDDATA and
        # change nothing else -- what is under test is that deck, as shipped.
        head, sep, tail = deck_text.rpartition("ENDDATA")
        if not sep:
            raise ValueError("deck has BEGIN BULK but no ENDDATA")
        return head + "\n".join(bulk) + "\nENDDATA" + tail

    return "\n".join(_case_control(sids, title) + [deck_text.rstrip("\n")]
                     + bulk + ["ENDDATA"]) + "\n"


# --------------------------------------------------------------------------- #
# Solving
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Reaction:
    """The total constraint reaction of one subcase, summed over every node.

    ``force`` is Σ of the reaction force components; ``moment`` is Σ of the
    reaction moments **plus** the reaction forces' lever arms about ``ref``, so a
    multi-node determinate support reports one rigid-body resultant rather than
    six numbers the caller has to recombine. For a determinate support the whole
    thing is the negative of the applied resultant about ``ref``, and for a deck
    claiming free-free equilibrium it is zero.

    ``scale`` is Σ\\|term\\| over the same sum, for
    :func:`sloads.export.equilibrium.closes` to size a zero-target tolerance
    with -- the same definition of "small" as the card-sum gate uses, so the two
    can never disagree about it.
    """

    force: Vec3
    moment: Vec3
    ref: Vec3
    force_scale: float
    moment_scale: float


def total_reaction(reactions: Dict[int, "object"], grids: Dict[int, Vec3],
                   ref: Vec3 = (0.0, 0.0, 0.0)) -> Reaction:
    """Sum sbeam's ``{gid: (6,)}`` reaction map into one :class:`Reaction`."""
    f = [0.0, 0.0, 0.0]
    m = [0.0, 0.0, 0.0]
    f_abs = [0.0, 0.0, 0.0]
    m_abs = [0.0, 0.0, 0.0]
    for gid, vec in reactions.items():
        fx, fy, fz = float(vec[0]), float(vec[1]), float(vec[2])
        mx, my, mz = float(vec[3]), float(vec[4]), float(vec[5])
        gx, gy, gz = grids[gid]
        dx, dy, dz = gx - ref[0], gy - ref[1], gz - ref[2]
        # r x F, right-handed, in the SLOADS/CID-0 identity frame -- the same
        # transfer equilibrium.resultant() applies to the applied cards.
        tx, ty, tz = dy * fz - dz * fy, dz * fx - dx * fz, dx * fy - dy * fx
        for axis, (fv, mv) in enumerate(((fx, mx + tx), (fy, my + ty),
                                         (fz, mz + tz))):
            f[axis] += fv
            m[axis] += mv
            f_abs[axis] += abs(fv)
            m_abs[axis] += abs(mv)
    return Reaction(force=(f[0], f[1], f[2]), moment=(m[0], m[1], m[2]), ref=ref,
                    force_scale=max(f_abs) if f_abs else 0.0,
                    moment_scale=max(m_abs) if m_abs else 0.0)


def solve_deck(deck_text: str) -> Dict[int, "object"]:
    """``{subcase id: Sol101Result}`` -- parse and solve every subcase in the deck.

    Goes through sbeam's own reader (``parse_bdf``) rather than any sloads
    parser, deliberately: a deck this gate accepts is a deck sbeam accepts.
    Raises :class:`SbeamUnavailable` if sbeam is not installed; anything the
    solver itself raises (a parse error, a singular stiffness matrix) is left to
    propagate, because that *is* the finding.
    """
    try:
        from sbeam.parser.bdf_reader import parse_bdf
        from sbeam.solver.sol101 import run_sol101
    except ImportError as exc:  # pragma: no cover - exercised by the skip path
        raise SbeamUnavailable(
            "sbeam is not installed -- `pip install -e '.[solver]'` to run the "
            "round-trip gate") from exc

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "deck.bdf")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(deck_text)
        cc, bulk = parse_bdf(path)
    if cc.sol != 101:
        raise ValueError(f"deck is SOL {cc.sol}; this harness solves SOL 101 only")
    return {sc.subcase_id: run_sol101(bulk, sc) for sc in cc.subcases}


__all__ = [
    "SPC_SID",
    "Reaction",
    "SbeamUnavailable",
    "Support",
    "Topology",
    "solve_deck",
    "total_reaction",
    "wrap_as_stick_model",
]
