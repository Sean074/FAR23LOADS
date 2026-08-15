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
right-hand side       ``6001+`` (wing strips; h-tail strips on 23.427(a))
left-hand side        ``6201+``
centreline            ``6401+`` (fuselage masses, tail load, lumped body Cm)
gear reference points ``10001+`` (a ground case's trunnions, decision G-2)
===================  ==============

The two side runs are named for the wing in :mod:`sloads.export.bands` because
the wing is what first needed them; what they carry is every load on that side of
the centreline, which from D-R8 includes the distributed 23.427(a) horizontal
tail. A case assembled at its trim tail load still carries that load lumped on
the centreline run.

The three bands are declared in :mod:`sloads.export.bands`, which owns every
GID/EID/SID run in the suite and proves them disjoint. They were ``4001+`` and
collided with the spanwise tail decks until 2026-08-10 (review F-C1).

The ``SUBCASE``/``SID`` ids are **minted from the case id**, per hand -- see
:func:`case_sids` and :func:`sloads.case_ids.balanced_subcase_id` (decision
D-R7). They were positional until 2026-08-10 (review m1).

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
from typing import Dict, List, Optional, Sequence, Tuple

from ..case_ids import (ASSEMBLED_DECK, NO_LOAD_ID, balanced_subcase_id,
                        deck_load_id)
from ..models import BalancedCaseResult, BalancedLoad, Project
from ..modules.balance import (SkippedCondition, build_balanced_cases,
                               carry_sources_absent, case_source_name,
                               fin_load, htail_load,
                               htail_side_loads, is_ground, is_lateral,
                               is_unsymmetrical_htail, skipped_condition_lines,
                               skipped_conditions)
from ..rigid_body import radians_per_s2
from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .bands import band
from .coordinates import SBEAM_CID, to_force, to_grid, to_moment
from .sbeam_bridge import _fmt, _sf_str, _stamped

#: Node runs, from the band registry (:mod:`sloads.export.bands`) -- the single
#: owner of every GID/EID/SID band in the suite. These three were 4001/4201/4401
#: until 2026-08-10, which collided completely with the spanwise tail decks'
#: 4001-5000; the registry is what makes that class of collision a test failure.
_NODE_BANDS = {"R": band("balanced-wing-right"),
               "L": band("balanced-wing-left"),
               "C": band("balanced-centreline")}
#: The gear reference points (decision G-2). A separate band from the three
#: position runs so a gear node is identifiable **by id**, which is what lets
#: G-13's solver assertion find the reaction sbeam recovers there without
#: matching coordinates.
_GEAR_BAND = band("balanced-gear")
#: Gear reference-point node run.
BALANCED_GEAR_BASE = _GEAR_BAND.start
#: Right-hand wing node run.
BALANCED_WING_R_BASE = _NODE_BANDS["R"].start
#: Left-hand wing node run -- separate so an antisymmetric case can load the two
#: sides differently without renumbering (plan 11 B7).
BALANCED_WING_L_BASE = _NODE_BANDS["L"].start
#: Centreline node run -- fuselage masses, the tail air load, the lumped
#: fuselage Cm moment, and every closure point that sits on the centreline.
BALANCED_BODY_BASE = _NODE_BANDS["C"].start

_FALLBACK_SID_BAND = band("balanced-subcase-unmapped")
#: The positional-fallback SUBCASE / load-set run, for a case that carries no
#: ``CaseRef`` at all. Every case the suite assembles is **minted** instead --
#: :func:`~sloads.case_ids.balanced_subcase_id`, see :func:`case_sids`.
BALANCED_FALLBACK_SID_BASE = _FALLBACK_SID_BAND.start


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
    gear_count = 0
    out: Dict[Tuple[str, float, float, float], int] = {}
    for case in cases:
        for load in case.loads:
            key = _node_key(load)
            if key in out:
                continue
            # A gear reference point takes its own band, whatever side it is on
            # (decision G-2): it is the one node in this deck a consumer needs to
            # find by id rather than by position, because the gear report states
            # the load delivered there and G-13 compares the two through the
            # solver.
            if load.source.startswith("gear-"):
                try:
                    out[key] = _GEAR_BAND.allocate(gear_count)
                except ValueError as exc:
                    raise ValueError(f"balanced deck: {exc}") from None
                gear_count += 1
                continue
            side = load.side if load.side in counts else "C"
            try:
                out[key] = _NODE_BANDS[side].allocate(counts[side])
            except ValueError as exc:
                raise ValueError(f"balanced deck: {exc}") from None
            counts[side] += 1
    return out


def case_sids(cases: Sequence[BalancedCaseResult]) -> List[int]:
    """One ``SUBCASE`` / load-set id per case, minted from its ``CaseRef``.

    Decision **D-R7** (review finding m1). The ids were positional --
    ``BALANCED_SID_BASE + i`` -- which made them a property of the export rather
    than of the case: one condition dropping out of the set (a missing V-n
    point, a payload loading that will not derive) renumbered every case after
    it, and the flagship deliverable was the last deck family still doing what
    M4-2 decision 8 removed everywhere else. Minted, ``W-05R`` is ``7105`` in
    every run of every project that assembles it.

    Handedness is carried by the case, not read off the id: a ``CaseRef`` that
    reached here without its suffix would otherwise mint the two twins of one
    condition onto the same number, which is the one failure this function must
    not have. The duplicate check below is the guard on that -- it catches a
    repeated ``CaseRef`` too, which is a genuine build error rather than a
    numbering one.

    A case with no ``CaseRef`` (a bare case list built in a test; nothing the
    suite assembles) falls back to its position, in the separate
    ``balanced-subcase-unmapped`` band so it can never land on a minted id.
    """
    out: List[int] = []
    for i, case in enumerate(cases):
        if case.case_ref is None:
            try:
                out.append(_FALLBACK_SID_BAND.allocate(i))
            except ValueError as exc:
                raise ValueError(f"balanced deck: {exc}") from None
            continue
        # The hand is passed, not encoded into the id and re-parsed (G-8). It was
        # ``handed_case_id(case_id, hand)`` until the ground families arrived,
        # which worked only because every id then *could* take a suffix; the
        # 23.485 side pair cannot, since LANDLOAD ships both hands under ids of
        # their own (``LG-19`` port, ``LG-20`` starboard) and suffixing either
        # would invent a second id for one physical condition.
        out.append(balanced_subcase_id(case.case_ref.case_id, case.hand))
    seen: Dict[int, BalancedCaseResult] = {}
    for sid, case in zip(out, cases):
        if sid in seen:
            raise ValueError(
                f"balanced deck: cases {seen[sid].label} and {case.label} both "
                f"mint SUBCASE {sid} -- two assembled cases share one case id "
                "and hand")
        seen[sid] = case
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


def _header(case: BalancedCaseResult, u: DeliverableUnits) -> List[str]:
    _, _, res_fz = to_force(0.0, 0.0, case.residual_fz, u)
    _, res_my, _ = to_moment(0.0, case.residual_my, 0.0, u)
    _, cm_my, _ = to_moment(0.0, case.fuselage_cm, 0.0, u)
    if is_ground(case):
        # A ground case's label already names the condition ("side load",
        # "one-wheel landing"), so the hand adds the side and nothing else. And
        # it makes no claim about which twin was computed: for the 23.485 family
        # LANDLOAD ships **both** drift directions under ids of their own, and
        # the one the suite assembles is the PORT case -- so "mirror of the
        # starboard case" would be backwards here (decision G-8).
        hand = {"R": " -- STARBOARD", "L": " -- PORT"}.get(case.hand, "")
    else:
        # What the hand *is* differs between the flight families, and naming it
        # "roll" on a rudder kick would be wrong: a lateral case's twin is the
        # opposite-sign side load, which happens to roll the airplane as well.
        kind = ("side load" if is_lateral(case)
                else "tail load split" if is_unsymmetrical_htail(case) else "roll")
        hand = {"R": f" -- STARBOARD {kind} (the computed case)",
                "L": f" -- PORT {kind} (mirror of the starboard case)"}.get(
                    case.hand, "")
    # Angular accelerations are reported in deg/s^2 -- a quantity a reader can
    # judge -- while the calc carries them in the weight-space 1/in the closure
    # solves in. The conversion has one owner; see sloads.rigid_body.
    p_dot, q_dot, r_dot = (_deg(v) for v in
                           radians_per_s2((case.p_dot, case.q_dot, case.r_dot)))
    sentences = [
        f"Balanced case {case.label}{hand} -- {case_source_name(case)}, "
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
        "The support below is determinate: its reaction IS the residual above.",
    ]
    if not is_ground(case):
        # A ground case has no trim, so it has no airplane-less-tail Cm to
        # apportion: printing "0 lb-in" beside a sentence about the trim solve
        # would describe machinery this case does not use.
        sentences.insert(-1, (
            f"Lumped fuselage Cm moment applied: {cm_my:.0f} {u.moment.label} "
            "(the trim's airplane-less-tail Cm that the distributed wing does "
            "not carry; it has no distributed form until the body aero moment "
            "lands)."))
    else:
        # The residual line above reads 100 % of n*W on a ground case, which is
        # correct and would otherwise read as alarming. Say why, here, where the
        # number is -- the same treatment the lateral and 23.427(a) families get.
        sentences.insert(-1, (
            "GROUND case (FAR 23.471-23.499): the pre-closure residual above is "
            "the applied gear load IN FULL and is NOT a balance error. A ground "
            "case has nothing to trim against -- no aero balances a wheel "
            "reaction -- so the airplane accelerates, and the six-DOF closure "
            "below IS that motion. The 1 % residual gate does not apply to this "
            "family; the gate that does is that the solved field, rotated back "
            "to the ground line, reproduces LANDLOAD's NVP/NDP/NS exactly."))
    if is_lateral(case):
        _, fin_fy, _ = to_force(0.0, fin_load(case), 0.0, u)
        _, _, res_mz = to_moment(0.0, 0.0, case.residual_mz, u)
        sentences.append(
            f"LATERAL case: applied fin side load {fin_fy:.1f} {u.force.label} "
            f"LIMIT (like the residuals above; the cards below are ULTIMATE), "
            f"distributed over the fin span from its root waterline. The "
            f"pre-closure Fy and Mz ({res_mz:.0f} {u.moment.label}) are that "
            "load in full, and are NOT a balance error: nothing in an airplane "
            "cancels a rudder kick -- it yaws and rolls, and the closure above "
            "is that motion. The 1 % residual gate is on the case's symmetric "
            "half, which is unchanged.")
    if is_unsymmetrical_htail(case):
        rh, lh = htail_side_loads(case)
        _, _, ht_total = to_force(0.0, 0.0, htail_load(case), u)
        _, _, ht_rh = to_force(0.0, 0.0, rh, u)
        _, _, ht_lh = to_force(0.0, 0.0, lh, u)
        # The *statement* of what this family is travels on the case's own notes
        # (balance.assemble), which reach the UI and the report as well; what
        # the deck adds here is the split in the deck's own units, and the
        # LIMIT/ULTIMATE reading of it.
        sentences.append(
            f"UNSYMMETRICAL h-tail case (FAR 23.427(a)): applied tail load "
            f"{ht_total:.1f} {u.force.label} LIMIT (like the residuals above; "
            f"the cards below are ULTIMATE), split {ht_rh:.1f} starboard / "
            f"{ht_lh:.1f} port and distributed over the full-span tail rather "
            "than lumped on the centreline. See the NOTE below for what that "
            "does to the residuals.")
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


def _skipped_block(skipped: Sequence[SkippedCondition]) -> List[str]:
    """The F-C7 record as deck comment lines, wrapped inside 72 columns.

    Printed whether or not anything was skipped: "every condition assembled" is
    the completeness statement, and a block that appears only on a lossy run
    cannot be told from a deck written before the record existed.
    """
    out = ["$",
           "$ ------------------------------ CONDITIONS NOT ASSEMBLED (SELECT set)"]
    lines = skipped_condition_lines(skipped)
    if not lines:
        out.append("$ None -- every condition SELECT named assembled into a case.")
        return out
    for line in lines:
        out += [f"$ {ln}" for ln in textwrap.wrap(line, width=70,
                                                 initial_indent="- ",
                                                 subsequent_indent="    ")]
    return out


def balanced_deck(project: Project, *,
                  header_comment: str = "",
                  system: UnitSystem = UnitSystem.IMPERIAL,
                  cases: Sequence[BalancedCaseResult] = (),
                  skipped: Optional[Sequence[SkippedCondition]] = None) -> str:
    """The assembled full-span deck: one ``SUBCASE`` per balanced case.

    Raises when no symmetric wing condition assembles -- a deck with no subcases
    would read as a clean result rather than as an absent one.

    ``skipped`` is the F-C7 record, stated in the deck's own ``$`` block beside
    the case map: what the deck covers is only half the statement, and a
    condition that dropped out is invisible in a deck that lists only what it
    holds. It is derived here when the caller does not supply it, so the block
    can never be silently absent; a caller that already assembled (the Balanced
    Cases page) passes its own record and saves the second pass.

    ``header_comment`` is the ``$``-prefixed methods & units block
    (:func:`~sloads.report.bdf_comment_block`), applied through the same
    :func:`~sloads.export.sbeam_bridge._stamped` owner every other deck uses:
    the mission's primary deliverable states its own basis when it travels
    alone. Blank leaves the deck byte-identical (the frozen Imperial baseline
    renders it unstamped).
    """
    u = _units(system)
    if cases:
        cases = list(cases)
        if skipped is None:
            skipped = skipped_conditions(project)
    else:
        record: List[SkippedCondition] = []
        cases = build_balanced_cases(project, record)
        if skipped is None:
            skipped = record
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

    sids = case_sids(cases)

    head: List[str] = ["SOL 101", "$",
                       "$ ------------------------------------------- BALANCED CASE MAP"]
    for line in textwrap.wrap(
            "SUBCASE ids are minted from the case id, not from its position: "
            "5000 + subcase_id symmetric, 7000 + starboard, 8000 + port "
            "(W-05R = 7105). They do not move when the case set changes.",
            width=70, subsequent_indent="  "):
        head.append(f"$ {line}")
    for sid, case in zip(sids, cases):
        # Wrapped, not hand-broken: B8a-3's condition names ("YAW TO SIDESLIP")
        # are half again as long as the four-letter wing ones and pushed this
        # line past 72 columns on the fixtures that carry a long CG name.
        # The case id leads, as it does in every other deck's map block and as
        # the case control's own LABEL does below: the map is what a consumer
        # joins a solver result to the case index by, and the id is the join key
        # (design note 17). Before it was added this block named the condition
        # only, so the assembled deck was the one family whose comment block
        # could not be joined without reading its case control.
        entry = (f"SUBCASE {sid} = {case.case_ref.case_id if case.case_ref else '(no case id)'}"
                 f" -- {case.label}"
                 f"{'-' + case.hand if case.hand else ''} -- "
                 f"{case_source_name(case, short=True)}"
                 f" -- {case.cg} -- Nz {case.nz:g}")
        head += [f"$ {ln}" for ln in textwrap.wrap(entry, width=70,
                                                   subsequent_indent="    ")]
    head += _skipped_block(skipped)
    head.append("$")
    for sid, case in zip(sids, cases):
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
        f"$ Gear reference points {BALANCED_GEAR_BASE}+: a ground case's wheel",
        "$ reactions are transferred here from the tyre contact patch, each with",
        "$ its lever-arm couple, so the load at the node has the identical",
        "$ resultant it had at the patch. The trunnion does not move between",
        "$ attitudes -- the strut state lands in the lever arm, not in the node.",
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
    for sid, case in zip(sids, cases):
        bulk += ["$"] + _header(case, u) + _load_lines(case, sid, nodes, u)

    return _stamped(header_comment, "\n".join(head + bulk + ["ENDDATA"]) + "\n")


def write_balanced_deck(project: Project, path: str, *,
                        header_comment: str = "",
                        system: UnitSystem = UnitSystem.IMPERIAL,
                        cases: Sequence[BalancedCaseResult] = (),
                        skipped: Optional[Sequence[SkippedCondition]] = None) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(balanced_deck(project, header_comment=header_comment,
                               system=system, cases=cases, skipped=skipped))


def balanced_case_rows(cases: Sequence[BalancedCaseResult]) -> List[Dict[str, str]]:
    """One row per balanced case: the numbers an engineer needs to trust it.

    The residual and the closure are the case's honesty statement, so they are
    columns of the deliverable rather than a log line.

    The lateral columns (``Ny``, yaw and roll acceleration) are the whole answer
    of a rudder or gust case, and are printed for every row so the table stays
    rectangular: on a symmetric case they read ``+0.00000`` / ``0``, which is the
    statement that the case has no lateral motion, not a missing number. Pitch
    acceleration joined them at D-R8 for the same reason from the other side: it
    is the whole answer of the 23.427(a) case, whose applied tail load is a
    maneuver load rather than the trim one, and it is near zero on every case
    that *is* assembled at its trim tail load -- which is worth being able to see.
    """
    rows: List[Dict[str, str]] = []
    for c in cases:
        p_dot, q_dot, r_dot = (_deg(v) for v in
                               radians_per_s2((c.p_dot, c.q_dot, c.r_dot)))
        rows.append({
            # The assembled deck's own identity for this case (design note 17):
            # the id is the deck's LABEL, LOAD its SUBCASE/SID integer -- minted
            # in the per-hand block, so the twins differ by their thousands digit.
            "ID": c.case_ref.case_id if c.case_ref else "—",
            "LOAD": ((deck_load_id(c.case_ref.case_id, ASSEMBLED_DECK, c.hand)
                      or NO_LOAD_ID) if c.case_ref else NO_LOAD_ID),
            "Case": c.label,
            "Hand": c.hand or "-",
            # Family-aware, and headed "Source case" rather than "V-n point"
            # (R6-C3): the column carries LANDLOAD's case number on a ground
            # row and FLTLOADS' V-n point on a flight one, so the value names
            # its own table and the header can no longer claim otherwise.
            "Source case": case_source_name(c),
            "Loading": c.cg,
            "Nz": f"{c.nz:.3f}",
            "Residual Fz (% n*W)": f"{c.force_residual_fraction * 100:.3f}",
            "Residual My (% n*W*MAC)": f"{c.moment_residual_fraction * 100:.3f}",
            # Applied, not unbalanced -- see
            # BalancedCaseResult.roll_moment_fraction.
            "Roll couple (% n*W*b/2)": f"{c.roll_moment_fraction * 100:.3f}",
            "Closure dn (g)": f"{c.delta_n:+.5f}",
            "Closure dNy (g)": f"{c.delta_ny:+.5f}",
            "Yaw acc (deg/s^2)": f"{r_dot:+.4g}",
            "Roll acc (deg/s^2)": f"{p_dot:+.4g}",
            "Pitch acc (deg/s^2)": f"{q_dot:+.4g}",
            "Basis": "LIMIT",
        })
    return rows


__all__ = [
    "BALANCED_WING_R_BASE",
    "BALANCED_WING_L_BASE",
    "BALANCED_BODY_BASE",
    "BALANCED_GEAR_BASE",
    "BALANCED_FALLBACK_SID_BASE",
    "case_sids",
    "deck_nodes",
    "balanced_deck",
    "write_balanced_deck",
    "balanced_case_rows",
]
