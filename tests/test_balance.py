"""Balanced free-free airplane cases and the assembled deck (plan 11 B2-B5).

The mission's aim 2: *a full airplane balanced case -- wing tip to wing tip, nose
to tail -- with no need for a constraint, because the loads balance.*

The airplane has always balanced at **trim** (``LZW + LT == Nz*W``, asserted for
a long time in ``test_concept_closure``). What never inherited that balance was
the **distributed** load set: the wing distribution, the tail load, the fuselage
inertia and the trim solve were four calculations nothing assembled. These tests
gate the assembly.

Two kinds of check, and the distinction matters:

* **the residual before closure** -- what the physics actually achieves, gated at
  1 % of ``n*W`` / ``n*W*MAC`` (plan 11 §6 acceptance 1). This is the real
  measurement, and it is deliberately taken *before* any relief is applied;
* **closure to machine precision after** -- that the three-DOF relief does what
  it claims, checked both in memory and, separately, by re-deriving the resultant
  from the exported deck's own card text.

Three things this suite exists to keep from regressing, each of which was a real
error found while building:

1. ``WingStationLoad.myy`` is a *cumulative* torsion carrying the sweep/dihedral
   transfer, not a free moment. Treating it as free puts the pitching residual at
   20.5 % of ``n*W*MAC`` instead of 0.12 %.
2. The wing load must be at the balanced case's own flight condition, not the
   hand-entered one -- otherwise the two halves describe different conditions and
   the force residual runs 10-37 %.
3. The deck's nodes must sit at each load's true position. Flattening them onto
   the fuselage beam line, or letting a ballast item fall through to a shared
   node, unbalanced the *deck* by 3.9-21.9 % while the in-memory case still
   closed to 1e-13 -- visible only by re-deriving from the card text.
"""

import math
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io  # noqa: E402
from sloads.constants import LBIN2_PER_SLUGFT2  # noqa: E402
from sloads import mass_distribution as md  # noqa: E402
from sloads.models import BalancedLoad, MassComponent, MissingInputError  # noqa: E402
from sloads.modules import one_engine_out  # noqa: E402
from sloads.rigid_body import InertiaTensor, radians_per_s2  # noqa: E402
from sloads.export.balanced_deck import (  # noqa: E402
    BALANCED_WING_L_BASE,
    BALANCED_WING_R_BASE,
    balanced_deck,
    case_sids,
    deck_nodes,
)
from sloads.export.coordinates import (  # noqa: E402
    reflect_force,
    reflect_moment,
    reflect_point,
    reflect_side,
)
from sloads.export.equilibrium import parse_cards, resultant  # noqa: E402
from sloads.modules import balance as balance_module  # noqa: E402
from sloads.modules.balance import (  # noqa: E402
    BALANCED_VTAIL_CONDITIONS,
    HANDEDNESS_TOL,
    RESIDUAL_GATE,
    ROLLING_WING_CONDITIONS,
    SKIP_REASONS,
    SKIPPED_RECORD_TITLE,
    SYMMETRIC_WING_CONDITIONS,
    build_balanced_cases,
    skipped_condition_lines,
    carry_sources_absent,
    fin_load,
    handed_twin,
    htail_load,
    htail_side_loads,
    is_unsymmetrical_htail,
    is_handed,
    is_lateral,
    resultant6,
)
from sloads.modules.balance import resultant as case_resultant  # noqa: E402
from sloads.modules.select import default_critical, default_envelope  # noqa: E402
from sloads.modules.tail_span import build_tail_span, strip_spans  # noqa: E402
from sloads.modules.wing_inertia import inertia_units  # noqa: E402
from sloads.tail_geometry import HTAIL, VTAIL, resolve_tail_planform  # noqa: E402
from sloads.units import Channel, UnitSystem, deliverable_units  # noqa: E402
from sloads.cg_cases import flight_cases  # noqa: E402

from imperial_baseline import EXAMPLES  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SYSTEMS = (UnitSystem.IMPERIAL, UnitSystem.SI)

#: Which fixtures assemble a balanced case at all, and how many.
#:
#: A condition is assembled only when the whole chain exists: SELECT named it, it
#: has a V-n point, and its CG case resolves to a **derivable** payload loading
#: (step C1). ``cessna_210``, ``atr42_100``, ``dhc8_dash8`` and ``concept_heavy``
#: produce none, because none of their payload cases is a loading their weight
#: database can actually produce -- a case needing 12-31 % of the airplane as
#: ballast has no honest inertia set, and inventing one would put fictitious mass
#: into the very balance the case exists to demonstrate. Filed on the backlog as
#: a fixture-data item; pinned here so it is a recorded fact, not a silent gap.
#:
#: ``(label, hand)`` pairs from B7: a rolling condition appears **twice**, once
#: per hand, and every other condition once with no hand.
#:
#: B8a-3 adds the four **lateral** conditions -- the vertical tail's own FAR
#: 23.441/23.443 set -- and every one of them is handed, because a fin load is
#: handed by construction (decision L-6, :func:`test_the_handedness_predicate`).
#: They assemble on both fixtures and on neither of the others, for the same
#: derivable-loading reason the symmetric families do.
_LATERAL_CASES = [
    ("SUDDEN RUDDER", "R"), ("SUDDEN RUDDER", "L"),
    ("YAW TO SIDESLIP", "R"), ("YAW TO SIDESLIP", "L"),
    ("YAW 15 NEUTRAL", "R"), ("YAW 15 NEUTRAL", "L"),
    ("SIDE GUST", "R"), ("SIDE GUST", "L"),
]

#: The 23.427(a) family (D-R8), handed by construction: SELECT puts 100 % of half
#: the governing tail load on one side and ``min(100 - 10(n-1), 80)`` percent on
#: the other, so both hands must be sized for and both are emitted. It sits
#: between the wing and lateral families because that is SELECT's own emission
#: order -- wing, h-tail, v-tail.
_UNSYMMETRICAL_CASES = [("UNSYMMETRICAL", "R"), ("UNSYMMETRICAL", "L")]

_EXPECTED_CASES = {
    "ga6_normal.project.json": [
        ("PHAA", ""), ("PLAA", ""), ("PMAA", ""), ("NMAA", ""),
        ("ACRL", "R"), ("ACRL", "L"), ("TORS", ""),
    ] + _UNSYMMETRICAL_CASES + _LATERAL_CASES,
    "cessna_210.project.json": [],
    "atr42_100.project.json": [],
    "dhc8_dash8.project.json": [],
    "concept_heavy.project.json": [],
    "concept_regional_jet.project.json": [
        ("PHAA", ""), ("PLAA", ""), ("PMAA", ""),
        ("ACRL", "R"), ("ACRL", "L"), ("TORS", ""),
    ] + _UNSYMMETRICAL_CASES + _LATERAL_CASES,
}

#: The pre-closure **pitch** residual, per fixture, as a fraction of ``n*W*MAC``.
#:
#: Plan 11's gate is 1 % and ``ga6_normal`` -- the Appendix A fixture -- meets it
#: on every case with room to spare. ``concept_regional_jet`` does not, on its
#: three high-speed low-CL cases (PLAA 1.041 %, PMAA 0.967 %, TORS 1.174 %), and
#: that is **stated here rather than absorbed into a wider gate for everyone**:
#: plan 11 R3 anticipated exactly this and offered "state the floor per fixture"
#: as the remedy. The pattern is diagnostic -- the exceedance tracks cases whose
#: lumped fuselage ``Cm`` is small or reversed, i.e. where the trim's
#: airplane-less-tail moment and the distributed wing's own section ``Cm`` nearly
#: cancel and the residual is a difference of large numbers. Filed on the backlog.
#:
#: B8a-3 splits the ceiling **per family** rather than widening it, for the same
#: reason it is stated per fixture: the lateral cases sit at V-n points the
#: symmetric families never visit (ga6 14 and 35, RJ 14 and 95), and their pitch
#: residual is larger there -- ga6 ``SUDDEN RUDDER`` 0.341 %, RJ ``SIDE GUST``
#: 1.586 %. That is *not* lateral contamination: the fin set carries ``fy`` and
#: ``mz`` only, so it contributes nothing to ``Fz``/``My``, and the symmetric half
#: of a lateral case has the identical residual to the last digit
#: (:func:`test_the_symmetric_half_of_a_lateral_case_still_closes`). Keeping the
#: symmetric bounds where they were preserves their bite; a single widened number
#: would have let a real symmetric regression through.
#:
#: These are upper bounds, not targets: they bite on any regression.
#: D-R8 adds an ``unsymmetrical`` bound, and it is a bound on a *different*
#: quantity: the 23.427(a) case's own pre-closure pitch residual is the maneuver
#: (144 % of ``n*W*MAC``), so what is bounded is its **trim half** -- the same
#: case with the lumped trim tail load restored, in
#: :func:`test_the_trim_half_of_an_unsymmetrical_case_still_closes`. It sits at
#: its own V-n point (ga6 74/``CG4``, RJ 34), which the symmetric families never
#: visit, and measures 0.301 % / 0.694 % there.
_PITCH_RESIDUAL_CEILING = {
    "ga6_normal.project.json": {"symmetric": 0.0030, "lateral": 0.0070,
                                "unsymmetrical": 0.0035},
    "concept_regional_jet.project.json": {"symmetric": 0.0120, "lateral": 0.0160,
                                          "unsymmetrical": 0.0080},
}


def _family(case) -> str:
    """``"lateral"``, ``"unsymmetrical"`` or ``"symmetric"`` -- which of the three
    balanced families a case belongs to.

    Named off the *applied* load set through balance's own readers, so the test
    suite cannot drift from what the deck header calls each family.
    """
    if is_lateral(case):
        return "lateral"
    return "unsymmetrical" if is_unsymmetrical_htail(case) else "symmetric"


def _project(example: str):
    return io.load_project(os.path.join(_ROOT, "examples", example))


def _with_cases():
    return [e for e, v in _EXPECTED_CASES.items() if v]


# --------------------------------------------------------------------------- #
# Scope
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_which_conditions_assemble_is_pinned(example):
    got = [(c.label, c.hand) for c in build_balanced_cases(_project(example))]
    assert got == _EXPECTED_CASES[example], example


# --------------------------------------------------------------------------- #
# The skipped-conditions record (review F-C7)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_every_condition_is_either_assembled_or_recorded(example):
    """**The F-C7 gate.** No condition SELECT named may leave the assembly
    unaccounted for.

    Before this, a missing V-n point, an unknown CG case or a non-derivable
    loading each dropped a condition with no record anywhere -- and the only
    thing standing between that and a user's project was ``_EXPECTED_CASES``
    above, which pins the *shipped fixtures'* drop set and nothing else. This
    asserts the property instead of the fixture: assembled ∪ recorded is exactly
    SELECT's set, and the two are disjoint.
    """
    project = _project(example)
    skipped = []
    cases = build_balanced_cases(project, skipped)

    named = {(c.component, c.label, c.case)
             for c in default_critical(project).conditions}
    assembled = {(c.case_ref.component, c.label, c.vn_case) for c in cases}
    recorded = {(s.component, s.label, s.case) for s in skipped}
    assert assembled | recorded == named, sorted(named ^ (assembled | recorded))
    assert not (assembled & recorded), sorted(assembled & recorded)
    # Every recorded reason is one of the declared ones -- a hand-written
    # sentence at a fifth ``continue`` would slip past the two set checks above.
    assert {s.code for s in skipped} <= set(SKIP_REASONS), skipped
    assert all(s.reason == SKIP_REASONS[s.code] for s in skipped)


def test_the_record_names_the_condition_the_review_found_missing():
    """``concept_regional_jet`` loses NMAA to a non-derivable loading -- the
    concrete case F-C7 was raised on. It is now *stated*, with its reason, rather
    than silently absent from the primary deliverable."""
    project = _project("concept_regional_jet.project.json")
    skipped = []
    build_balanced_cases(project, skipped)
    nmaa = [s for s in skipped if s.label == "NMAA"]
    assert len(nmaa) == 1, skipped
    assert nmaa[0].component == "wing"
    assert nmaa[0].code == "loading-not-derivable"
    # The fuselage family is a deliberate exclusion, and is recorded as one
    # rather than left to be inferred from its absence. The h-tail's *symmetric*
    # conditions are a different statement since D-R8 -- they are already in
    # every case, as the trim tail load -- and only 23.427(a) assembles.
    assert {s.code for s in skipped if s.component == "fuselage"} == {
        "out-of-family"}
    assert {s.code for s in skipped if s.component == "htail"} == {
        "htail-symmetric"}
    assert "UNSYMMETRICAL" not in {s.label for s in skipped}


@pytest.mark.parametrize("example", _with_cases())
def test_the_deck_states_what_it_does_not_cover(example):
    """The record travels in the deck's own ``$`` block.

    A deck lists what it holds; a condition that dropped out is invisible in it
    by construction. The block is emitted whether or not anything was skipped --
    "none" is the completeness statement, and a block that appears only on a
    lossy run cannot be told from a deck written before the record existed.
    """
    project = _project(example)
    skipped = []
    build_balanced_cases(project, skipped)
    text = balanced_deck(project)
    assert "CONDITIONS NOT ASSEMBLED" in text
    # The block is line-wrapped, so it is compared as unwrapped text: every
    # recorded line, verbatim, has to be in there.
    block = " ".join(
        ln.lstrip("$ ").lstrip("- ") for ln in _skipped_lines_of(text))
    block = " ".join(block.split())
    for line in skipped_condition_lines(skipped):
        assert " ".join(line.split()) in block, (example, line)
    # The deck the caller supplies cases to states the same record as the one
    # that assembles them itself -- the GUI path must not lose the block.
    assert _skipped_lines_of(text) == _skipped_lines_of(
        balanced_deck(project, cases=build_balanced_cases(project),
                      skipped=skipped))


def test_the_deck_block_says_none_when_nothing_was_skipped():
    assert ("None -- every condition SELECT named assembled into a case."
            in _skipped_block([]))


def test_the_module_result_carries_the_record():
    """The record is on the ``ModuleResult`` too, so every consumer of the module
    (report, CSV, GUI) states it without re-running the assembly."""
    project = _project("concept_regional_jet.project.json")
    result = balance_module.run(project)
    record = [c for c in result.conditions if c.title == SKIPPED_RECORD_TITLE]
    assert len(record) == 1, [c.title for c in result.conditions]
    row = record[0]
    skipped = []
    build_balanced_cases(project, skipped)
    assert row.values[0].value == float(len(skipped))
    assert row.values[0].key == "balanced_skipped_count"
    assert "NMAA" in row.note
    # It is a statement about the run, not a load case: no case_ref, so it mints
    # no case-index row, and its one value is dimensionless so the ULTIMATE
    # boundary passes it through unscaled.
    assert row.case_ref is None
    assert row.values[0].units == ""


def _skipped_block(skipped):
    from sloads.export.balanced_deck import _skipped_block as block
    return "\n".join(block(skipped))


def _skipped_lines_of(deck_text: str):
    lines = deck_text.splitlines()
    start = lines.index(
        "$ ------------------------------ CONDITIONS NOT ASSEMBLED (SELECT set)")
    end = lines.index("$", start)
    return lines[start:end]


# --------------------------------------------------------------------------- #
# The gate: the residual BEFORE closure (plan 11 acceptance 1)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _with_cases())
def test_the_pre_closure_residual_is_within_the_gate(example):
    """``|dFz|/(n*W) < 1 %``, and the pitch residual within its stated ceiling.

    The gate is on the physics, not on the correction -- which is the whole point
    of measuring it before closure. **Force** meets plan 11's 1 % on every case of
    every fixture (ga6 0.05-0.62 %, RJ 0.03-0.70 %). **Pitch** meets it on
    ``ga6_normal``, the Appendix A fixture, at 0.12-0.29 %; on
    ``concept_regional_jet`` three high-speed low-CL cases exceed it and are
    bounded per fixture instead -- see :data:`_PITCH_RESIDUAL_CEILING` for the
    numbers, the diagnosis and why the gate is not simply widened.

    The **roll** and **yaw** DOF are deliberately not gated here. On a rolling
    case ``residual_mx`` is the applied aileron couple; on a lateral case
    ``residual_fy``/``residual_mz`` are the applied fin load in full. In both
    the airplane is *supposed* not to balance them -- it rolls and yaws instead
    -- so a residual gate on those components would be a gate on nothing. See
    :func:`test_the_roll_moment_is_the_applied_couple` and
    :func:`test_the_symmetric_half_of_a_lateral_case_still_closes`.

    The **23.427(a)** family is excluded from ``Fz``/``My`` for the same kind of
    reason and it is the strongest instance of it (D-R8): its applied tail load
    is a *maneuver* load and replaces the trim tail load its V-n point balances
    at, so the airplane is genuinely out of trim and the residual is that
    mismatch in full -- 49.8 % of ``n*W`` on ``ga6_normal``. Gating it here would
    gate the maneuver. What is gated instead is the case's **trim half**, at the
    same 1 %, in
    :func:`test_the_trim_half_of_an_unsymmetrical_case_still_closes`.
    """
    for case in build_balanced_cases(_project(example)):
        if _family(case) == "unsymmetrical":
            continue
        where = f"{example} {case.label}{case.hand}"
        ceiling = _PITCH_RESIDUAL_CEILING[example][_family(case)]
        assert case.force_residual_fraction < RESIDUAL_GATE, (
            f"{where}: force residual {case.force_residual_fraction * 100:.3f} %")
        assert case.moment_residual_fraction < ceiling, (
            f"{where}: pitch residual {case.moment_residual_fraction * 100:.3f} % "
            f"against the {_family(case)} ceiling {ceiling * 100:.2f} %")


@pytest.mark.parametrize("example", _with_cases())
def test_the_closure_relief_is_small(example):
    """``|dn|/n < 1 %`` (plan 11 acceptance 2) -- how much of the balance was
    assumed rather than computed.

    Read the other way round on the 23.427(a) family, and deliberately: there the
    relief is not a correction to a balance that nearly held, it is the airplane's
    response to a maneuver tail load (-0.496 g on ``ga6_normal``), so it is the
    *answer* rather than a measure of how much was assumed. It is bounded by its
    own gate -- the trim half -- and reported per case in the table and the deck
    header.
    """
    for case in build_balanced_cases(_project(example)):
        if _family(case) == "unsymmetrical":
            continue
        assert abs(case.delta_n / case.nz) < RESIDUAL_GATE, f"{example} {case.label}"


@pytest.mark.parametrize("example", _with_cases())
def test_the_case_closes_in_all_three_symmetric_dof(example):
    """After closure: ``Fx``, ``Fz`` and ``My`` about the CG are zero to machine
    precision.

    Three degrees of freedom, not the two plan 11 B-3 anticipated. Nothing else
    in the assembled model reacts **drag** -- the suite has no distributed thrust
    -- so leaving x open puts 17-26 % of ``n*W`` into the support reaction and
    makes "reactions ~ 0" untrue in a deck that still solves. FAR 23's ``nx`` is
    exactly this quantity.
    """
    p = _project(example)
    cgs = {c.name: c for c in flight_cases(p)}
    for case in build_balanced_cases(p):
        cg = cgs[case.cg]
        fx, fz, my = case_resultant(case.loads, (cg.xcg, 0.0, cg.zcg))
        scale = case.n_w
        assert abs(fx) < 1e-6 * scale, f"{example} {case.label} Fx"
        assert abs(fz) < 1e-6 * scale, f"{example} {case.label} Fz"
        assert abs(my) < 1e-6 * scale * case.mac, f"{example} {case.label} My"


@pytest.mark.parametrize("example", _with_cases())
def test_the_inertia_set_weighs_the_case(example):
    """Σ modelled mass == the payload case's weight, exactly.

    The mass SSOT's guarantee carried into the balance: wing mass comes from the
    loading's WING items (spread by WINGINER's shape) and everything else from
    the beam items, so the two partition the airplane rather than overlapping.
    Where they overlapped -- the wing-tank fuel on two fixtures -- taking WINGINER's
    own panel+concentrated model instead cost 12-13 % of ``n*W``.
    """
    for case in build_balanced_cases(_project(example)):
        modelled = sum(ld.weight_lb for ld in case.loads
                       if ld.source in ("wing-inertia", "body-inertia"))
        assert modelled == pytest.approx(case.weight_lb, rel=1e-9), \
            f"{example} {case.label}"


def test_wing_items_with_no_panel_model_raise_rather_than_vanish():
    """The B-2 partition's edge-case gate (review **F-C5**).

    ``panel_weight_lb = 0`` makes WINGINER integrate no panel, so the wing
    inertia scale has nothing to scale onto -- while ``assembly_distributes_mass``
    goes on excluding the same WING items from ``body_inertia`` because the wing
    set is meant to carry them. The whole WING item weight used to leave the
    model there, absorbed silently by the closure. No shipped fixture reaches it,
    which is why it needs its own case: ``ga6_normal``'s 330 lb of wing items
    against an emptied panel model.
    """
    p = _project("ga6_normal.project.json")
    wing = sum(it.weight_lb for it in p.weight.items
               if md.component_of(it, p) is MassComponent.WING)
    assert wing, "fixture must carry WING-tagged item mass for this to gate"

    p.wing_mass = replace(p.wing_mass, panel_weight_lb=0.0)
    with pytest.raises(MissingInputError) as exc:
        build_balanced_cases(p)
    assert f"{wing:.0f} lb" in str(exc.value)


def test_no_wing_items_and_no_panel_still_weighs_the_case():
    """The other half of the gate: nothing to spread is not an error.

    With the WING tag off the items, the fuselage beam carries them, the wing
    inertia scale is legitimately 0.0 and no mass is lost -- so this must build,
    and the partition must still weigh the whole case.
    """
    p = _project("ga6_normal.project.json")
    p.weight.items = [replace(it, component=MassComponent.FUSELAGE)
                      if md.component_of(it, p) is MassComponent.WING else it
                      for it in p.weight.items]
    p.wing_mass = replace(p.wing_mass, panel_weight_lb=0.0)

    cases = build_balanced_cases(p)
    assert cases
    for case in cases:
        modelled = sum(ld.weight_lb for ld in case.loads
                       if ld.source in ("wing-inertia", "body-inertia"))
        assert modelled == pytest.approx(case.weight_lb, rel=1e-9), case.label
        assert not [ld for ld in case.loads if ld.source == "wing-inertia"]


# --------------------------------------------------------------------------- #
# B3 -- the seam rule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _with_cases())
def test_no_free_body_cut_reaction_is_applied(example):
    """Plan 11 §4: *a load that a free-body cut introduces is never applied in
    the assembled model.*

    The wing carry-through is the seam between two free bodies. The per-component
    fuselage deck applies it because it has cut the wing off; the assembled model
    has not, so its solver recovers it, and applying it as well would react the
    wing twice. Structural (``balance.assemble`` never reads ``body_loads``);
    this is the drift guard.
    """
    for case in build_balanced_cases(_project(example)):
        assert carry_sources_absent(case), f"{example} {case.label}"
        assert not any(ld.source in ("carry", "correction") for ld in case.loads)


# --------------------------------------------------------------------------- #
# B5 -- the assembled deck
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _with_cases())
@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_deck_balances_from_its_own_cards(example, system):
    """**The acceptance test of the whole step.**

    Re-derive each subcase's resultant from the emitted ``GRID``/``FORCE``/
    ``MOMENT`` text and check it is zero about the CG. Reading the deck rather
    than the objects is what makes this meaningful: the in-memory case closed to
    1e-13 while the deck was out by 3.9-21.9 %, because distinct loads were
    collapsing onto shared nodes. Nothing but the card text would have shown it.

    **All six DOF** (review finding F-G1, closed 2026-08-10). Until then this
    read ``fx``/``fz``/``my`` only, while ``equilibrium.Resultant`` carried the
    lateral three all along -- so the node-collapse failure mode this gate exists
    for could hit a fin ``FORCE`` card or a reflected port-twin node and unbalance
    ``fy``/``mx``/``mz`` with nothing looking. The lateral three are not
    decoration on this deck: from B8a-3 every assembled deck carries eight
    lateral cases, and the handed twins differ *only* in those components.

    Levers, per axis: pitch against the MAC as before, roll and yaw against the
    **semi-span** -- the same lever ``BalancedCaseResult.roll_residual_fraction``
    judges the physics residual by, so the deck gate and the closure report agree
    on what "small" means for a moment.
    """
    p = _project(example)
    cgs = {c.name: c for c in flight_cases(p)}
    cases = build_balanced_cases(p)
    u = deliverable_units(system, Channel.SOLVER)
    grids, _, _, forces, moments = parse_cards(
        balanced_deck(p, system=system, cases=cases))
    for sid, case in zip(case_sids(cases), cases):
        cg = cgs[case.cg]
        ref = (cg.xcg * u.length.factor, 0.0, cg.zcg * u.length.factor)
        got = resultant(forces, moments, grids, sid, ref)
        n_w = case.n_w * case.safety_factor * u.force.factor
        n_w_mac = n_w * case.mac * u.length.factor
        n_w_span = n_w * case.semi_span * u.length.factor
        assert n_w_span > 0.0, f"{example}: no semi-span to judge roll/yaw by"
        where = f"{example} {system.value} {case.label}"
        # 1e-5 is the %.6E card format accumulated over ~150 cards, not physics.
        assert abs(got.fx) < 1e-5 * n_w, f"{where} Fx"
        assert abs(got.fy) < 1e-5 * n_w, f"{where} Fy"
        assert abs(got.fz) < 1e-5 * n_w, f"{where} Fz"
        assert abs(got.mx) < 1e-5 * n_w_span, f"{where} Mx"
        assert abs(got.my) < 1e-5 * n_w_mac, f"{where} My"
        assert abs(got.mz) < 1e-5 * n_w_span, f"{where} Mz"


def test_the_lateral_half_of_the_deck_gate_has_teeth():
    """**F-G1's teeth**: reverse one lateral ``FORCE`` card and only ``fy``/``mx``/
    ``mz`` notice.

    A widened gate that passes on the first run proves nothing, so this measures
    what the three DOF it gained can see that the three it had could not. The
    mutation is the review's own failure mode -- a lateral card of the fin family
    with its ``y`` component reversed, which is what a sign error in the
    span-to-waterline map or in the port-twin reflection produces.

    Measured on ``ga6_normal``, as fractions of the gate's own scales: ``fy``
    **3.4 %**, ``mz`` **3.1 %**, ``mx`` **0.20 %** -- against ``fx`` 9e-10,
    ``fz`` 6e-9 and ``my`` 5e-8, all of them comfortably inside the 1e-5
    tolerance. The old gate would have called this deck balanced.
    """
    p = _project("ga6_normal.project.json")
    cases = build_balanced_cases(p)
    index = next(i for i, c in enumerate(cases) if is_lateral(c))
    sid = case_sids(cases)[index]
    case = cases[index]

    lines, hit = [], False
    for line in balanced_deck(p, cases=cases).splitlines():
        f = line.split(",")
        if not hit and line.startswith(f"FORCE, {sid},") and abs(float(f[6])) > 1e-9:
            f[6], hit = f" {-float(f[6]):.6E}", True
            line = ",".join(f)
        lines.append(line)
    assert hit, "no lateral FORCE card to reverse -- the deck format changed"

    cg = {c.name: c for c in flight_cases(p)}[case.cg]
    grids, _, _, forces, moments = parse_cards("\n".join(lines) + "\n")
    got = resultant(forces, moments, grids, sid, (cg.xcg, 0.0, cg.zcg))
    n_w = case.n_w * case.safety_factor

    # The three the gate always had: blind to it.
    assert abs(got.fx) < 1e-5 * n_w
    assert abs(got.fz) < 1e-5 * n_w
    assert abs(got.my) < 1e-5 * n_w * case.mac
    # The three it gained: each on its own, by a wide margin.
    assert abs(got.fy) > 1e-2 * n_w, got.fy
    assert abs(got.mx) > 1e-3 * n_w * case.semi_span, got.mx
    assert abs(got.mz) > 1e-2 * n_w * case.semi_span, got.mz


@pytest.mark.parametrize("example", _with_cases())
def test_every_load_has_its_own_node(example):
    """Two loads at different positions never share a GID.

    The bug this pins cost 21.9 % of the deck's balance and was invisible in
    memory: wing air (25 % chord) and wing inertia (item-anchored 50 % chord) at
    one span station were keyed on span alone, and every ballast item -- which has
    no fuselage beam station, the beam being derived from the untouched database
    -- fell through to a shared node.
    """
    p = _project(example)
    cases = build_balanced_cases(p)
    nodes = deck_nodes(cases, p)
    assert len(set(nodes.values())) == len(nodes), "two positions share a GID"


@pytest.mark.parametrize("example", _with_cases())
def test_the_wing_has_two_node_bands(example):
    """Left and right are separate runs -- the first deck in the suite with both.

    Every previous deck carried a single half-span. The split is what lets an
    antisymmetric case (plan 11 B7) load the two sides differently without
    renumbering anything.
    """
    p = _project(example)
    nodes = deck_nodes(build_balanced_cases(p), p)
    right = {g for k, g in nodes.items() if k[0] == "R"}
    left = {g for k, g in nodes.items() if k[0] == "L"}
    assert right and left and len(right) == len(left)
    assert all(BALANCED_WING_R_BASE <= g < BALANCED_WING_R_BASE + 200 for g in right)
    assert all(BALANCED_WING_L_BASE <= g < BALANCED_WING_L_BASE + 200 for g in left)
    assert not (right & left)


@pytest.mark.parametrize("example", _with_cases())
def test_the_deck_is_determinately_supported(example):
    """One node, six DOF: the reaction *is* the residual, which is the free-free
    proof rather than a modelling convenience."""
    text = balanced_deck(_project(example))
    _, _, spc1, _, _ = parse_cards(text)
    assert len(spc1) == 1
    _, comp, gids = spc1[0]
    assert comp == "123456" and len(gids) == 1
    assert "the reaction IS the residual" in text.replace("its reaction IS the residual",
                                                          "the reaction IS the residual")


@pytest.mark.parametrize("example", _with_cases())
def test_the_deck_states_its_residual_and_its_lumped_moment(example):
    """A deck forwarded on its own must say how much of the balance was computed
    and how much relieved, and that the body ``Cm`` is lumped."""
    text = balanced_deck(_project(example))
    assert "Residual BEFORE closure" in text
    assert "Lumped fuselage Cm moment" in text
    assert "FULL SPAN, free-free" in text


@pytest.mark.parametrize("example", _with_cases())
def test_deck_subcase_ids_are_minted_and_survive_a_dropped_case(example):
    """**D-R7** at deck level: the ``SUBCASE`` a case is written under is its own
    id, and dropping a condition renumbers nothing.

    The positional scheme made the flagship deliverable's case identity a
    property of the export -- one missing V-n point moved every subsequent
    ``SUBCASE`` number, so a solver result could not be read without the run
    that produced it. This drops a case from the middle and asserts the
    survivors keep the numbers they had, which is the property the shipped deck
    now offers a consumer.
    """
    p = _project(example)
    cases = build_balanced_cases(p)
    assert len(cases) > 2, f"{example}: too few cases to drop one from the middle"
    minted = {c.case_ref.case_id: sid
              for sid, c in zip(case_sids(cases), cases) if c.case_ref}
    assert len(minted) == len(cases), f"{example}: a case reached the deck unidentified"

    text = balanced_deck(p, cases=cases)
    for sid, case in zip(case_sids(cases), cases):
        assert f"SUBCASE {sid}\n" in text, \
            f"{example}: {case.label} is not written under its minted id"

    kept = [c for i, c in enumerate(cases) if i != 1]
    after = {c.case_ref.case_id: sid for sid, c in zip(case_sids(kept), kept)}
    assert all(after[cid] == minted[cid] for cid in after), \
        f"{example}: dropping one case renumbered the survivors"


def test_two_cases_with_one_identity_cannot_share_a_subcase():
    """The one failure minting can have, refused rather than merged.

    Positional ids could not collide; minted ones can, if a build hands the same
    ``CaseRef`` and hand to two cases. Sharing a ``SUBCASE`` would silently sum
    two load sets in the solver -- the D-19 class -- so the deck refuses.
    """
    p = _project("ga6_normal.project.json")
    cases = build_balanced_cases(p)
    with pytest.raises(ValueError, match="mint SUBCASE"):
        balanced_deck(p, cases=list(cases) + [cases[0]])


def test_a_project_with_no_balanced_case_refuses_a_deck():
    """A deck with no subcases would read as a clean result rather than an absent
    one."""
    with pytest.raises(ValueError, match="no balanced case"):
        balanced_deck(_project("cessna_210.project.json"))


# --------------------------------------------------------------------------- #
# B7 -- the antisymmetric cases and the handedness machinery
# --------------------------------------------------------------------------- #
def test_only_acrl_carries_roll():
    """``unbal_moment`` is non-zero on ``ACRL`` alone -- a **measured** finding.

    Plan 11 phase 2 is worded "the antisymmetric wing cases (``ACRL``, ``TORS``)",
    but the handedness of a wing case lives entirely in ``WingLoadCase.unbal_moment``
    (FAR 23.349), and every shipped fixture enters zero for ``TORS``. That is not
    a fixture oversight: a *steady* roll has no unbalanced rolling moment by
    definition -- the aileron moment is balanced by roll damping -- and the
    up-going/down-going aero asymmetry that remains has no spanwise
    representation anywhere in this suite. ``TORS`` is therefore assembled as the
    symmetric case it is.

    Pinned so that a fixture which ever enters a rolling ``TORS`` goes red here
    rather than being assembled symmetrically and quietly meaning nothing.
    """
    assert "TORS" in SYMMETRIC_WING_CONDITIONS
    assert ROLLING_WING_CONDITIONS == ("ACRL",)
    for example in EXAMPLES:
        project = _project(example)
        for case in (project.wing_mass.cases if project.wing_mass else []):
            if case.name == "ACRL":
                continue
            assert case.unbal_moment == 0.0, (
                f"{example} {case.name} carries UNB={case.unbal_moment}: it is "
                "antisymmetric and must not be assembled as a symmetric case")


@pytest.mark.parametrize("example", _with_cases())
def test_the_roll_moment_is_the_applied_couple(example):
    """``residual_mx`` is **exactly** the applied aileron couple, and nothing else.

    Two statements in one: the rolling cases carry ``-UNB`` to machine precision,
    and every other case carries no rolling moment at all. If any other load in
    the assembly had a roll component -- a mirroring slip, an inertia strip on the
    wrong side -- it would land here.

    B8a-3 exempts the **lateral** family, and the exemption is the physics: a fin
    load sits above the roll axis, so ``-Fy*(z - z_cg)`` is a genuine rolling
    moment the case is *supposed* to carry, and it is asserted positively here
    rather than merely excused -- the roll must equal the fin set's own moment
    about the CG, with no contribution from anything else in the assembly.
    """
    project = _project(example)
    cgs = {c.name: c for c in flight_cases(project)}
    for case in build_balanced_cases(project):
        where = f"{example} {case.label}{case.hand}"
        if is_lateral(case):
            cg = cgs[case.cg]
            fin = [ld for ld in case.loads if ld.source == "vtail-air"]
            _, _, _, mx, _, _ = resultant6(fin, (cg.xcg, 0.0, cg.zcg))
            assert case.residual_mx == pytest.approx(mx, rel=1e-12), (
                f"{where}: the pre-closure roll is not the fin load's own moment")
            assert case.unbal_moment == 0.0, where
            continue
        if is_unsymmetrical_htail(case):
            # Same statement for the 23.427(a) family (D-R8): the whole roll of
            # the case must be the h-tail set's own moment about the CG -- the
            # left/right split and nothing else. A mirroring slip in the wing or
            # a strip on the wrong side would land here, exactly as before.
            cg = cgs[case.cg]
            ht = [ld for ld in case.loads if ld.source == "htail-air"]
            _, _, _, mx, _, _ = resultant6(ht, (cg.xcg, 0.0, cg.zcg))
            assert case.residual_mx == pytest.approx(mx, rel=1e-12), (
                f"{where}: the pre-closure roll is not the tail split's own moment")
            assert case.unbal_moment == 0.0, where
            continue
        assert case.residual_mx == pytest.approx(-case.unbal_moment, abs=1e-6), where
        if not case.hand:
            assert case.unbal_moment == 0.0, where


#: The share of the aileron's rolling moment the **wing span** reacts, per
#: fixture: ``p_dot(closure) / (Mx / Sum w*y^2)``. Pinned because it is the one
#: number the two roll producers do *not* share, and because it is a physical
#: statement about the airplane rather than a tolerance -- see
#: :func:`test_roll_closure_reproduces_winginer`.
_WING_SPAN_ROLL_SHARE = {
    "ga6_normal.project.json": 0.795230,
    "concept_regional_jet.project.json": 0.769455,
}


@pytest.mark.parametrize("example", _with_cases())
def test_roll_closure_reproduces_winginer(example):
    """**The B7 closure gate**, as B8a-2 restated it: shape exactly, magnitude pinned.

    Concept mode has no printed oracle, so a stated closure gate against an
    *independent producer* stands in for one (``CLAUDE.md`` practice 2). Here the
    two producers are as independent as the codebase allows: WINGINER's
    ``fz_r``/``iwxx`` recurrence, which is oracle-locked FAR 23 code untouched by
    this step, and the balance layer's roll-acceleration solve, which knows
    nothing about it and closes a residual it computed itself.

    **What B8a-2 changed, and why it is not a weakening.** Through B7 this was an
    equality: the closure's roll strips *were* ``ur*fz_r``, ratio 1.000000. That
    held because the roll DOF solved on ``Sum w*y^2``, and every mass in every
    fixture's database sits at ``y = 0``, so the wing span was the airplane's
    entire roll inertia by construction. The full d'Alembert field (decision L-2)
    ends that: a mass **above** the roll axis is thrown sideways by a roll
    acceleration, so ``Sum w*dz^2`` joins the roll inertia -- on
    ``concept_regional_jet`` it is +30 % of ``Sum w*y^2`` on its own -- and each
    item's entered self-``Ixx`` joins it too (decision L-3). The airplane
    therefore reacts about a fifth of the aileron moment somewhere other than the
    wing span, and WINGINER's wing-only model has no counterpart to that.

    So the gate asserts the two halves separately, which is strictly more than
    the equality did:

    * **shape** -- ``fz / (ur*fz_r)`` is the *same constant* on every strip, to
      1e-9. This is the whole of what WINGINER's distribution says, and it is
      untouched: the relief is still exactly ``-w*p_dot*y``;
    * **magnitude** -- that constant is the wing span's share of the roll
      moment, pinned per fixture (:data:`_WING_SPAN_ROLL_SHARE`), and it equals
      ``p_dot / (Mx / Sum w*y^2)`` by construction. It goes red if the roll
      inertia model drifts, which the old equality could not see at all.
    """
    project = _project(example)
    wm = project.wing_mass
    geom = project.geometry.by_name(wm.surface)
    u = inertia_units(geom, wm)
    winginer = {round(y, 6): f for y, f in zip(u.ye, u.fz_r) if f}

    # ``hand == "R"`` no longer means "rolling": from B8a-3 the lateral family is
    # handed too. Selected on the condition, which is what the check is about.
    rolling = [c for c in build_balanced_cases(project)
               if c.hand == "R" and c.label in ROLLING_WING_CONDITIONS]
    assert rolling, f"{example}: no rolling case to check"
    for case in rolling:
        ur = case.unbal_moment / 100000.0
        strips = [ld for ld in case.loads
                  if ld.source == "closure-roll" and ld.y > 0
                  and round(ld.y, 6) in winginer]
        assert len(strips) >= 5, f"{example}: only {len(strips)} strips matched"

        ratios = [ld.fz / (ur * winginer[round(ld.y, 6)]) for ld in strips]
        for ld, got in zip(strips, ratios):
            assert got == pytest.approx(ratios[0], rel=1e-9), (
                f"{example} {case.label} strip y={ld.y}: the roll relief is no "
                f"longer WINGINER's shape -- ratio {got} against {ratios[0]}")

        share = _WING_SPAN_ROLL_SHARE[example]
        assert ratios[0] == pytest.approx(share, rel=1e-5), (
            f"{example} {case.label}: the wing span now reacts {ratios[0]:.6f} "
            f"of the aileron rolling moment, not the pinned {share}")

        # ...and that constant IS the roll-inertia ratio, not a fitted number.
        masses = [ld for ld in case.loads if ld.weight_lb]
        span_only = sum(ld.weight_lb * ld.y ** 2 for ld in masses)
        assert ratios[0] == pytest.approx(
            case.p_dot / (case.residual_mx / span_only), rel=1e-9), (
            f"{example} {case.label}: the magnitude ratio does not equal the "
            "wing-span share of the assembled roll inertia")


# --------------------------------------------------------------------------- #
# The B8a-2 gates (plan 13 §7): G1, G4, G5, G6
# --------------------------------------------------------------------------- #
def _oeo_history(project):
    """``(CaseInputs, [HistoryRow])`` of the first one-engine-out speed case.

    ``None`` when the project enters no such case at all. **Every number here is
    now the fixture's own.** Until 2026-08-13 this supplied a synthetic 2000 hp,
    because no shipped fixture entered engine horsepower and ONENGOUT could not
    execute on any of them; ``atr42_100`` and ``dhc8_dash8`` carry their
    certificated ratings since, so the injection is gone and G1 reads a history
    built entirely from fixture data. (The identity under test never depended on
    it -- ``psi_2dot = Mz / Izz`` is about the operator and holds at every step of
    any history -- but a gate that feeds itself an input is one an unrelated data
    change can quietly hollow out.)
    """
    oeo = project.one_engine_out
    if oeo is None or not project.engines:
        return None
    try:
        cases = one_engine_out._load_cases(project, oeo)
        if not cases:
            return None
        inputs = one_engine_out._case_inputs(project, cases[0].v_hi_kt)
        rows, _ = one_engine_out.simulate(inputs)
    except (MissingInputError, ValueError):
        return None
    return inputs, rows



#: Which fixtures carry a one-engine-out case, and so can serve as G1's
#: independent producer. Pinned, and deliberately **disjoint** from
#: :func:`_with_cases`: the two fixtures that assemble balanced cases enter no
#: ``one_engine_out`` slice, and the two that enter one assemble no balanced
#: case. That is why G1 is stated as an identity on the *solve* rather than on a
#: case -- the two producers do not meet on any single fixture, and a gate
#: parametrised over the balanced-case fixtures would have skipped itself into
#: vacuity on every run.
_WITH_ONE_ENGINE_OUT = ("atr42_100.project.json", "dhc8_dash8.project.json")


def test_g1_has_a_producer_to_check_against():
    """The vacuity guard for :func:`test_the_yaw_dof_reproduces_onengout`."""
    got = tuple(e for e in EXAMPLES if _oeo_history(_project(e)) is not None)
    assert got == _WITH_ONE_ENGINE_OUT, got


@pytest.mark.parametrize("example", _WITH_ONE_ENGINE_OUT)
def test_the_yaw_dof_reproduces_onengout(example):
    """**G1.** The closure's yaw solve is ``psi_2dot = Mz / Izz`` -- ONENGOUT's.

    B8a-2's counterpart to the B7 roll gate, and the stronger of the two,
    because the other producer here is **oracle-locked FAR 23 code**:
    ``ONENGOUT.BAS`` 282-286 (Ref 1 Ch 11 p87-88, FAR 23.367) integrates
    ``THETA2DOT = MOM/12/IZZ*57.3`` and knows nothing whatever about balanced
    cases. The yaw degree of freedom is new at B8a-2 and has no other check.

    Run against the module's **own time history** rather than a re-derived
    formula, so the comparison is with what ONENGOUT actually computes at each
    step, at that step's own moment. ``_DEG`` is ONENGOUT's 57.3 rather than
    ``math.degrees``' 57.29578 -- the identity under test is the physics
    ``M/(12*Izz)``, not the manual's rounding of a radian.
    """
    inputs, history = _oeo_history(_project(example))
    # ONENGOUT is a single-DOF yaw model with no products of inertia, so the
    # tensor to compare against is diagonal. ``ixx``/``iyy`` are filled only to
    # keep it invertible -- with every product of inertia zero the yaw row
    # decouples exactly, and their values cannot reach the answer.
    izz = inputs.izz * LBIN2_PER_SLUGFT2
    tensor = InertiaTensor(ixx=izz, iyy=izz, izz=izz)
    checked = 0
    for row in history:
        if not row.moment:
            continue
        omega_dot = tensor.solve((0.0, 0.0, row.moment))
        got = radians_per_s2(omega_dot)[2] * one_engine_out._DEG
        assert got == pytest.approx(row.theta_2dot, rel=1e-12), (
            f"{example} t={row.time}: closure {got} vs ONENGOUT {row.theta_2dot}")
        checked += 1
    assert checked > 10, f"{example}: only {checked} steps compared"


#: ``Izz`` of the assembled closure tensor, slug-ft^2, per fixture and loading.
#: **G4**, and it is an equality rather than a comparison: with decision L-3
#: answered, ``Izz(closure)`` must equal ``Izz(WTONECG) - wing self-Izz +
#: Sum w*y^2(WINGINER spread)`` -- the same airplane from two producers that
#: share no code. Pinned as well as reconciled, because a reconciliation that
#: drifted on both sides at once would still balance.
_CLOSURE_IZZ = {
    "ga6_normal.project.json": {"CG1": 2992.1, "CG2": 2933.5, "CG3": 2534.2,
                                # CG4 arrives with the 23.427(a) case (D-R8):
                                # the lightest loading, hence the smallest Izz.
                                "CG4": 2424.1},
    "concept_regional_jet.project.json": {"CG1 aft heavy": 256507.6,
                                          "CG2 fwd heavy": 331827.6},
}


@pytest.mark.parametrize("example", _with_cases())
def test_the_closure_izz_is_pinned_and_reconciles(example):
    """**G4.** Three producers give three ``Izz`` for one airplane; pin the one
    that reacts the load, and show it is the others' identity.

    Plan 13 §3.4 measured the spread and it is not noise: ``select._default_izz``
    (Ch 9) gives ``ga6_normal`` 4169, ``WTONECG`` gives 3023, and the assembled
    mass set gives 2934. Two of those are printed in Appendix A, side by side,
    38 % apart. The mitigation (risk R5) is that the case reports which one
    reacted its load -- so this asserts that number, and that it is reachable
    from the deliverable rather than only from a scratch script.
    """
    for case in build_balanced_cases(_project(example)):
        want = _CLOSURE_IZZ[example][case.cg]
        got = case.closure_inertia.izz / LBIN2_PER_SLUGFT2
        assert got == pytest.approx(want, rel=1e-4), (
            f"{example} {case.label} {case.cg}: Izz(closure) {got:.1f} "
            f"against the pinned {want}")
        # The tensor is the assembled model's, not a re-derivation: it must be
        # positive-definite in the obvious sense and carry the Ixz coupling.
        assert case.closure_inertia.ixx > 0 and case.closure_inertia.iyy > 0
        assert case.closure_inertia.ixz != 0.0
        assert case.closure_inertia.ixy == pytest.approx(0.0, abs=1e-6), (
            f"{example} {case.label}: the mass model is not mirror-symmetric")


@pytest.mark.parametrize("example", _with_cases())
def test_a_symmetric_case_reduces_to_three_dof(example):
    """**G5.** The 6-DOF closure on a symmetric case is the 3-DOF one it replaced.

    The reduction that makes B8a-2 a superset rather than a change: with no
    lateral applied load, the lateral three solve to zero and the deck carries
    the same physics it did before -- ``n_x``/``n_z`` identical by construction
    (they are still ``F/W``), and the pitch DOF still reacting the whole
    ``My`` residual.

    What did **not** stay identical, and is asserted rather than glossed:
    ``q_dot`` is no longer ``My / Sum w*dx^2``. The pitch inertia became a real
    ``Iyy`` -- it gained ``Sum w*dz^2`` and the non-wing self-inertia -- so
    ``q_dot`` fell 18-22 % on ``ga6_normal`` and 3-4 % on the regional jet. The
    *deck* barely moved, because the pitch relief is only 0.06-0.56 % of a peak
    node load, but the reported acceleration did, and it moved towards the
    truth.
    """
    project = _project(example)
    cgs = {c.name: c for c in flight_cases(project)}
    for case in build_balanced_cases(project):
        if case.hand:
            continue
        where = f"{example} {case.label}"
        cg = cgs[case.cg]
        masses = [ld for ld in case.loads if ld.weight_lb]
        w_total = sum(ld.weight_lb for ld in masses)

        # The translational three are unchanged: still F/W, exactly.
        assert case.delta_n == pytest.approx(case.residual_fz / w_total, rel=1e-12)
        assert case.delta_nx == pytest.approx(case.residual_fx / w_total, rel=1e-12)
        assert case.delta_ny == 0.0, where

        # Pitch reacts the whole My residual, through the real Iyy...
        assert case.q_dot == pytest.approx(
            case.residual_my / case.closure_inertia.iyy, rel=1e-9), where
        # ...which is strictly larger than the Sum w*dx^2 the 3-DOF closure used.
        old_j = sum(ld.weight_lb * (ld.x - cg.xcg) ** 2 for ld in masses)
        assert case.closure_inertia.iyy > old_j, where
        assert abs(case.q_dot) < abs(case.residual_my / old_j), where


#: What ``ACRL`` gained at B8a-2, per fixture: the peak nodal companion side
#: force the roll field applies, and the yaw acceleration ``Ixz`` induces from
#: it, in deg/s^2. **G6** -- the one shipped case whose *physics* L-2 changes,
#: so the change is asserted rather than re-baselined (risk R1).
_ACRL_LATERAL = {
    "ga6_normal.project.json": {"companion_fy_lb": 89.83, "r_dot_deg_s2": 18.93},
    "concept_regional_jet.project.json": {"companion_fy_lb": 551.85,
                                          "r_dot_deg_s2": -0.993},
}


@pytest.mark.parametrize("example", _with_cases())
def test_acrl_gained_the_companion_field_and_an_induced_yaw(example):
    """**G6.** A rolling airplane with non-zero ``Ixz`` yaws, and throws mass sideways.

    Both are new at B8a-2 and both are real physics the shipped model could not
    express. The companion ``fy = +w*p_dot*dz`` is *larger* than the roll term
    already in the deck, because ``fz = -w*p_dot*dy`` reaches only the wing
    strips -- every item in every fixture's database sits at ``y = 0`` -- while
    the companion reaches every mass off the roll axis.

    The net side force it adds must be **zero**: it is a d'Alembert reaction to
    an angular acceleration, not a side load, and if it netted anything the case
    would be applying a lateral force nothing asked for.
    """
    want = _ACRL_LATERAL[example]
    rolling = [c for c in build_balanced_cases(_project(example))
               if c.hand == "R" and c.label in ROLLING_WING_CONDITIONS]
    assert rolling, f"{example}: no rolling case"
    for case in rolling:
        roll = [ld for ld in case.loads if ld.source == "closure-roll"]
        assert roll, f"{example}: no roll relief"
        peak = max(abs(ld.fy) for ld in roll)
        assert peak == pytest.approx(want["companion_fy_lb"], rel=1e-3), (
            f"{example} {case.label}: companion peak fy {peak:.1f} lb")
        assert sum(ld.fy for ld in roll) == pytest.approx(
            0.0, abs=1e-9 * case.weight_lb), (
            f"{example} {case.label}: the companion field nets a side force")

        r_dot = math.degrees(radians_per_s2((0.0, 0.0, case.r_dot))[2])
        assert r_dot == pytest.approx(want["r_dot_deg_s2"], rel=1e-3), (
            f"{example} {case.label}: induced yaw {r_dot:.3f} deg/s^2")
        # It is Ixz that induces it -- zero the coupling and the yaw goes away.
        assert case.closure_inertia.ixz != 0.0
        uncoupled = replace(case.closure_inertia, ixz=0.0, ixy=0.0, iyz=0.0)
        assert uncoupled.solve(
            (case.residual_mx, case.residual_my, case.residual_mz))[2] == \
            pytest.approx(0.0, abs=abs(case.r_dot) * 1e-3)


@pytest.mark.parametrize("example", _with_cases())
def test_the_case_closes_in_all_six_dof(example):
    """After relief, all six rigid-body components are zero to machine precision.

    The three symmetric DOF were already gated at B2; roll is the one B7 adds, and
    it is the one an antisymmetric case fails silently without -- ``ACRL``
    assembled with no roll term closes ``Fx``/``Fz``/``My`` to 1e-11 while
    carrying a whole unreacted aileron couple.
    """
    project = _project(example)
    cgs = {c.name: c for c in flight_cases(project)}
    for case in build_balanced_cases(project):
        cg = cgs[case.cg]
        fx, fy, fz, mx, my, mz = resultant6(case.loads, (cg.xcg, 0.0, cg.zcg))
        where = f"{example} {case.label}{case.hand}"
        scale = case.n_w
        assert abs(fx) < 1e-6 * scale, f"{where} Fx"
        assert abs(fy) < 1e-6 * scale, f"{where} Fy"
        assert abs(fz) < 1e-6 * scale, f"{where} Fz"
        assert abs(mx) < 1e-6 * scale * case.semi_span, f"{where} Mx"
        assert abs(my) < 1e-6 * scale * case.mac, f"{where} My"
        assert abs(mz) < 1e-6 * scale * case.semi_span, f"{where} Mz"


@pytest.mark.parametrize("example", _with_cases())
def test_the_lateral_dof_are_untouched(example):
    """No **applied** load in the symmetric families has a side component (**G5**).

    ``Fy``/``Mz`` are computed rather than assumed so B8a's lateral cases inherit
    a complete resultant; this pins that today no applied load creates one, which
    is what makes the roll check above unambiguous.

    B8a-2 split the statement in two, because a rolling case now *does* carry a
    lateral relief field (``fy = +w*p_dot*dz``, decision L-2) -- real physics, and
    the point of the step. What stays absolutely true is the **applied** set, and
    what stays true of a **symmetric** case is that its lateral relief is
    float-cancellation noise rather than load: ``residual_mx``/``residual_mz`` on
    a mirror-symmetric mass model are zero up to summation order, so the solve
    returns ~1e-18 rad-equivalents and the relief it produces is fifteen orders
    below a card the deck would even print. Bounded rather than asserted exactly
    zero, because rounding the residual to zero to make the claim exact would be
    a rounding dressed as physics.

    B8a-3 scopes it to the **symmetric and rolling** families, which is what it
    always meant: the lateral family exists precisely to apply a side load, and
    its own statement of the same kind is
    :func:`test_the_symmetric_half_of_a_lateral_case_still_closes` -- strip the
    fin set out and this claim holds again, to the last digit.
    """
    for case in build_balanced_cases(_project(example)):
        if is_lateral(case):
            continue
        applied = [ld for ld in case.loads if not ld.source.startswith("closure-")]
        assert all(ld.fy == 0.0 and ld.mz == 0.0 for ld in applied), case.label
        assert case.residual_fy == 0.0, case.label
        assert abs(case.residual_mz) < 1e-6 * case.n_w * case.semi_span, case.label
        if case.hand:
            continue
        # A symmetric case: the lateral DOF close on noise, not on load.
        assert case.delta_ny == 0.0, case.label
        lateral = max(max(abs(ld.fy), abs(ld.mz)) for ld in case.loads)
        assert lateral < 1e-9 * case.n_w, f"{case.label}: {lateral} lb of side load"


# --------------------------------------------------------------------------- #
# The B8a-3 gates (plan 13 §7): G9, G10, and the L-6 predicate
# --------------------------------------------------------------------------- #
#: **G10.** What each lateral case *is*, per fixture: the net applied fin side
#: load (lb), the lateral load factor it produces (g), and the yaw and roll
#: accelerations (deg/s^2). Four numbers per condition, pinned in both
#: directions -- these are the whole answer of a rudder or gust case, and there
#: is no printed oracle for any of them, so a stated measurement is the gate
#: (``CLAUDE.md`` practice 2).
#:
#: Three of them are *not* free parameters and are asserted structurally as well
#: as pinned: ``n_y`` is ``L_v / W`` exactly (the ``Sum Fy = 0`` of plan 13 §2),
#: the yaw follows from the same ``Izz``/``Ixz`` tensor B8a-2 pinned, and the
#: roll is the fin's own moment about the CG (asserted in
#: :func:`test_the_roll_moment_is_the_applied_couple`). The fin loads themselves
#: are SELECT's, unchanged -- see :func:`sloads.modules.balance.fin_sets`.
#:
#: The yaw figures are **not** those of plan 13 §3.1: those were measured against
#: the placement-only ``Izz`` that preceded L-3. Against the shipped tensor
#: ga6 ``SUDDEN RUDDER`` is 178.05 deg/s^2 rather than 205.7 -- a ratio of 0.866
#: where the ``Izz`` ratio alone would give 0.886, the difference being the
#: ``Ixz`` coupling. Plan 13 §7 is amended to these.
_LATERAL_CASE_NUMBERS = {
    "ga6_normal.project.json": {
        "SUDDEN RUDDER": (585.7113, +0.172268, +178.0465, -12.0373),
        "YAW TO SIDESLIP": (-97.7614, -0.028753, -19.4378, +3.2401),
        "YAW 15 NEUTRAL": (-525.7482, -0.154632, -151.9110, +11.7518),
        "SIDE GUST": (603.9904, +0.177644, +185.5132, -20.1640),
    },
    "concept_regional_jet.project.json": {
        "SUDDEN RUDDER": (6907.3247, +0.209313, +51.5652, -57.7489),
        "YAW TO SIDESLIP": (-3548.1801, -0.107521, -20.8441, +31.1333),
        "YAW 15 NEUTRAL": (-8042.6960, -0.243718, -55.6995, +68.3709),
        "SIDE GUST": (7080.4238, +0.214558, +42.9290, -77.8823),
    },
}


@pytest.mark.parametrize("example", _with_cases())
def test_the_lateral_cases_are_pinned(example):
    """**G10.** Every lateral case's applied load and the motion it causes.

    The starboard case is the computed one; the port twin is its mirror and is
    checked as such by :func:`test_the_handed_twins_are_mirror_images`, so the
    pins are stated once.
    """
    want = _LATERAL_CASE_NUMBERS[example]
    got = {c.label: c for c in build_balanced_cases(_project(example))
           if is_lateral(c) and c.hand == "R"}
    assert sorted(got) == sorted(want), f"{example}: {sorted(got)}"
    assert sorted(got) == sorted(BALANCED_VTAIL_CONDITIONS), example

    for label, (fin, ny, r_dot, p_dot) in want.items():
        case = got[label]
        where = f"{example} {label}"
        assert fin_load(case) == pytest.approx(fin, rel=1e-4), (
            f"{where}: fin side load {fin_load(case):.4f} lb")
        assert case.delta_ny == pytest.approx(ny, rel=1e-4), (
            f"{where}: Ny {case.delta_ny:+.6f} g")
        # ...and Ny is not a fitted number: it is Sum Fy = 0, i.e. L_v / W.
        assert case.delta_ny == pytest.approx(
            fin_load(case) / case.weight_lb, rel=1e-12), where

        got_p, _, got_r = (math.degrees(v) for v in
                           radians_per_s2((case.p_dot, case.q_dot, case.r_dot)))
        assert got_r == pytest.approx(r_dot, rel=1e-4), (
            f"{where}: yaw acceleration {got_r:+.4f} deg/s^2")
        assert got_p == pytest.approx(p_dot, rel=1e-4), (
            f"{where}: roll acceleration {got_p:+.4f} deg/s^2")


@pytest.mark.parametrize("example", _with_cases())
def test_the_applied_fin_set_is_air_only_so_the_mass_is_applied_once(example):
    """The fin's mass enters an assembled case **once**, in the closure field.

    Since the tail-mass SSOT step the per-condition fin deck carries its own
    lateral inertia (``-n_y*W_vt``), so ``WingStationLoad.fz`` is a *net* load
    there. An assembled case must still apply the applied-aerodynamic set air
    only, because it accounts for the fin's mass separately through the
    ``VTAIL``-tagged items — reading the net would relieve the side load with a
    mass it is also carrying in the closure field.

    Asserted against SELECT's own totals, which no part of the assembly touches:
    Σ applied fin ``fy`` must be the condition's ``LT25+LT50`` exactly, not the
    ``(1 − W_vt/W)`` fraction of it the fin deck reports. Caught here in the
    first place only by a pinned number, which is why it now has a gate that says
    what it means.
    """
    project = _project(example)
    spans = {r.case: r for r in build_tail_span(project)[VTAIL]}
    for case in build_balanced_cases(project):
        if not is_lateral(case) or case.hand != "R":
            continue
        span = spans[case.label]
        assert fin_load(case) == pytest.approx(span.air_total, rel=1e-12), (
            f"{example} {case.label}: the applied fin set is not air only -- "
            f"{fin_load(case):.4f} lb against SELECT's {span.air_total:.4f} lb")
        # And the deck the fin is sized from *does* carry the inertia, so the two
        # differ by exactly the mass ratio. Both statements have to hold at once.
        if span.inertia_modelled and span.case_weight_lb:
            net = sum(st.fz for st in span.stations)
            assert net == pytest.approx(
                span.air_total * (1.0 - span.surface_weight_lb / span.case_weight_lb),
                rel=1e-12), f"{example} {case.label}"


@pytest.mark.parametrize("example", _with_cases())
def test_the_symmetric_half_of_a_lateral_case_still_closes(example):
    """**G9.** The residual gate that *does* apply to a lateral case.

    Plan 11's 1 % residual gate is meaningless laterally by construction:
    ``residual_fy``/``residual_mz`` before closure **are** the fin load in full,
    because nothing in an airplane balances a rudder kick -- it yaws, and the
    closure is that yaw. (The same standing ``ACRL``'s roll residual has had
    since B7.) Gating them would either be vacuous or force a fictitious
    balancing load into the case.

    What must still hold is that adding the fin set broke nothing in the half
    that *does* balance: strip the ``vtail-air`` loads out and the symmetric
    residual is unchanged to the last digit -- which it is *exactly*, and for a
    reason worth stating: the fin set carries ``fy`` and ``mz`` only, so it
    cannot contribute to ``Fx``/``Fz``/``My`` at all. Asserted rather than
    argued, because a frame-map slip -- the fin's normal force landing back on
    ``fz`` -- is precisely the error that would break it, and it would break it
    silently.
    """
    project = _project(example)
    cgs = {c.name: c for c in flight_cases(project)}
    lateral = [c for c in build_balanced_cases(project) if is_lateral(c)]
    assert lateral, f"{example}: no lateral case"
    for case in lateral:
        cg = cgs[case.cg]
        where = f"{example} {case.label}{case.hand}"
        applied = [ld for ld in case.loads
                   if not ld.source.startswith("closure-")]
        half = [ld for ld in applied if ld.source != "vtail-air"]
        fx, fy, fz, mx, my, mz = resultant6(half, (cg.xcg, 0.0, cg.zcg))

        assert fx == pytest.approx(case.residual_fx, rel=1e-12), f"{where} Fx"
        assert fz == pytest.approx(case.residual_fz, rel=1e-12), f"{where} Fz"
        assert my == pytest.approx(case.residual_my, rel=1e-12), f"{where} My"
        # The symmetric half is symmetric: no side force, and its roll and yaw
        # are summation noise rather than load.
        assert fy == 0.0, f"{where}: the symmetric half carries {fy} lb of Fy"
        assert abs(mx) < 1e-9 * case.n_w * case.semi_span, f"{where} Mx"
        assert abs(mz) < 1e-9 * case.n_w * case.semi_span, f"{where} Mz"

        # ...and the lateral residual IS the fin load, not a balance error.
        assert case.residual_fy == pytest.approx(fin_load(case), rel=1e-12), where


# --------------------------------------------------------------------------- #
# The D-R8 gates: the 23.427(a) unsymmetrical h-tail family
# --------------------------------------------------------------------------- #
#: What SELECT gives the 23.427(a) case, per fixture: ``(RH, LH, total)`` in lb
#: and the ``pc`` split percent. **Read from SELECT, never recomputed here** --
#: pinned so a change in the oracle-locked search shows up as a change in the
#: assembled deliverable rather than passing through it unremarked.
_UNSYMMETRICAL_SPLIT = {
    "ga6_normal.project.json": (-700.380105, -504.273676, 72.0),
    "concept_regional_jet.project.json": (5877.725954, 4702.180763, 80.0),
}


def _unsymmetrical(project):
    return [c for c in build_balanced_cases(project) if is_unsymmetrical_htail(c)]


@pytest.mark.parametrize("example", _with_cases())
def test_the_unsymmetrical_case_carries_selects_own_split(example):
    """**The D-R8 composition gate.** The applied tail load *is* SELECT's.

    Two producers, one answer, and that is the whole point of the branch: SELECT
    picks the governing symmetric tail load and splits it 100 % / ``pc`` %
    (oracle-locked, an approved deviation of record), and the assembly's job is
    to distribute that -- not to re-derive it. So each half of the applied set
    must sum to SELECT's own ``RH``/``LH`` to the last digit, and the port twin
    must be the same two numbers **swapped**, which is what makes the pair the
    "either side" of 23.427(a) rather than one case printed twice.
    """
    project = _project(example)
    rh_want, lh_want, pc = _UNSYMMETRICAL_SPLIT[example]
    cases = _unsymmetrical(project)
    assert [c.hand for c in cases] == ["R", "L"], f"{example}: {cases}"
    # Pinned above *and* read from SELECT here: a pin alone would drift with the
    # search it is meant to be pinning.
    cond = next(c for c in default_critical(project).conditions
                if c.component == "htail" and c.label == "UNSYMMETRICAL")
    select = {lv.key: lv.value for lv in cond.loads}
    assert select["rh_side_load"] == pytest.approx(rh_want, rel=1e-9), example
    assert select["lh_side_load"] == pytest.approx(lh_want, rel=1e-9), example
    assert select["other_side_percent"] == pc, example
    # The split percent is SELECT's rule, restated here only to show the pair
    # really is asymmetric -- a 100/100 "split" would pass every other assertion.
    assert lh_want == pytest.approx(pc / 100.0 * rh_want, rel=1e-6)

    for case in cases:
        where = f"{example} {case.label}{case.hand}"
        rh, lh = htail_side_loads(case)
        want = (rh_want, lh_want) if case.hand == "R" else (lh_want, rh_want)
        assert rh == pytest.approx(want[0], rel=1e-9), f"{where} starboard half"
        assert lh == pytest.approx(want[1], rel=1e-9), f"{where} port half"
        assert htail_load(case) == pytest.approx(rh_want + lh_want, rel=1e-9), where
        # ...and it replaces the trim tail load rather than joining it: a case
        # carrying both would balance far better and be wrong.
        assert not any(ld.source == "tail-air" for ld in case.loads), where


@pytest.mark.parametrize("example", _with_cases())
def test_the_unsymmetrical_roll_is_the_closed_form(example):
    """**The D-R8 distribution gate**: an analytic target, not a re-run.

    Concept mode has no printed oracle, so the gate is a closed form the
    distribution must hit (``CLAUDE.md`` practice 2). The applied rolling moment
    about the centreline is ``(RH - LH) * y_bar`` exactly, with ``y_bar`` the
    chord-weighted centroid of the half planform -- because the chord-proportional
    distribution puts the same shape on both halves and only the scale differs.
    Computed here from the planform rather than from the load set, so the two
    sides of the identity share no code: -7167.69 lb-in on ``ga6_normal``,
    +81700.39 on the regional jet, ratio 1.000000000 on both.
    """
    project = _project(example)
    planform = resolve_tail_planform(project, HTAIL)
    strips = strip_spans(planform)
    y_bar = (sum(planform.chord(s) * ds * s for s, ds in strips)
             / sum(planform.chord(s) * ds for s, ds in strips))
    rh_want, lh_want, _ = _UNSYMMETRICAL_SPLIT[example]

    for case in _unsymmetrical(project):
        where = f"{example} {case.label}{case.hand}"
        rh, lh = htail_side_loads(case)
        roll = sum(ld.y * ld.fz for ld in case.loads if ld.source == "htail-air")
        assert roll == pytest.approx((rh - lh) * y_bar, rel=1e-9), where
        # The hand is a real reversal of that moment, not a relabelling.
        assert (roll > 0) == (rh - lh > 0), where
        # Against the pinned split, whose constants carry six decimals -- hence
        # the looser tolerance than the identity above, which is exact.
        assert abs(roll) == pytest.approx(abs(rh_want - lh_want) * y_bar, rel=1e-7)


@pytest.mark.parametrize("example", _with_cases())
def test_the_trim_half_of_an_unsymmetrical_case_still_closes(example):
    """**The D-R8 residual gate** -- the one that does apply to this family.

    Plan 11's 1 % gate is meaningless on a 23.427(a) case for a stronger version
    of the lateral reason: its applied tail load is a *maneuver* load and it
    replaces the trim tail load the V-n point balances at, so the pre-closure
    ``Fz``/``My`` are that mismatch in full (49.8 % of ``n*W`` on ``ga6_normal``)
    and the vertical and pitch closure is the motion it causes -- an abrupt
    elevator input, which is what 23.423 and 23.427 are about.

    What must still hold is that everything *else* in the case is the shipped
    balanced assembly: put the trim tail load back, as a lumped force at the
    tail's own reference point, and the case closes inside the 1 % gate again.
    That also pins the replacement itself -- if the h-tail set were being applied
    *beside* ``vn.lt`` rather than instead of it, this restoration would double
    the tail load and the residual would blow out.
    """
    project = _project(example)
    cgs = {c.name: c for c in flight_cases(project)}
    vn = {p.case: p for p in default_envelope(project).vn}
    fl = project.flight_loads
    cases = _unsymmetrical(project)
    assert cases, f"{example}: no 23.427(a) case"

    for case in cases:
        where = f"{example} {case.label}{case.hand}"
        cg = cgs[case.cg]
        point = vn[case.vn_case]
        trim = [ld for ld in case.loads
                if not ld.source.startswith("closure-")
                and ld.source != "htail-air"]
        trim.append(BalancedLoad(x=fl.xtc, y=0.0, z=fl.zw, fz=point.lt,
                                 source="tail-air", side="C"))
        fx, fy, fz, mx, my, mz = resultant6(trim, (cg.xcg, 0.0, cg.zcg))

        n_w = case.n_w
        assert abs(fz) < RESIDUAL_GATE * n_w, (
            f"{where}: trim-half force residual {100 * fz / n_w:.3f} % of n*W")
        ceiling = _PITCH_RESIDUAL_CEILING[example]["unsymmetrical"]
        assert abs(my) < ceiling * n_w * case.mac, (
            f"{where}: trim-half pitch residual "
            f"{100 * my / (n_w * case.mac):.3f} % against {ceiling * 100:.2f} %")
        # The trim half is symmetric: the whole hand of the case is the tail
        # split, and putting the lumped load back removes it entirely.
        assert fy == 0.0, f"{where}: trim half carries {fy} lb of Fy"
        assert abs(mx) < 1e-9 * n_w * case.semi_span, f"{where} trim-half roll"
        assert abs(mz) < 1e-9 * n_w * case.semi_span, f"{where} trim-half yaw"


@pytest.mark.parametrize("example", _with_cases())
def test_the_closure_is_solved_at_the_mass_centroid(example):
    """The relief field is referred to the mass set's own centroid, not the
    entered CG -- and on one shipped loading those differ (D-R8).

    The two coincide on every loading the fixtures had before the 23.427(a) case
    arrived, which is why the difference could sit unnoticed in a decoupled
    ``n = F/W`` solve: an angular acceleration applied about the wrong point
    leaves ``-omega_dot x Sum w_i r_i`` of unclosed force, and with the tiny
    ``omega_dot`` of a trimmed case that is nothing. ``ga6_normal``'s ``CG4``
    loading sits 0.0024 in forward and 0.0052 in below its own entered CG, and
    the 23.427(a) case accelerates it at 637 deg/s^2: 0.31 lb of ``Fx``, four
    orders above the closure gate. Asserted as a property so it cannot come back
    on a loading nobody thought to check.
    """
    project = _project(example)
    cgs = {c.name: c for c in flight_cases(project)}
    offsets = []
    for case in build_balanced_cases(project):
        cg = cgs[case.cg]
        masses = [ld for ld in case.loads
                  if ld.weight_lb and not ld.source.startswith("closure-")]
        w = sum(ld.weight_lb for ld in masses)
        offsets.append(max(
            abs(sum(ld.weight_lb * (ld.x - cg.xcg) for ld in masses) / w),
            abs(sum(ld.weight_lb * (ld.z - cg.zcg) for ld in masses) / w)))
        # Closure is exact regardless (the six-DOF gate asserts the same thing
        # case by case); what this test adds is that the property is *tested*
        # against a loading where the two reference points really differ.
    if example == "ga6_normal.project.json":
        assert max(offsets) > 1e-3, (
            "no shipped loading's mass centroid differs from its entered CG any "
            "more -- this gate has stopped gating anything, and the closure's "
            "reference point needs a constructed case instead")


def test_the_handedness_predicate():
    """The **L-6 drift guard**: what makes a case handed, stated in isolation.

    ``is_handed`` reads the *distribution* and not the resultant, which is the
    whole of decision L-6: ``ga6_normal``'s ``YAW TO SIDESLIP`` nets -97.8 lb of
    side force out of parts worth -683 and +586, and a net-based predicate would
    mint it unhanded on that near-cancellation and assemble a rudder-kick case
    as a symmetric one. The two-strip set below is that failure in miniature.
    """
    def load(**kw):
        return BalancedLoad(x=0.0, y=0.0, z=0.0, **kw)

    n_w = 1000.0
    assert not is_handed([], n_w)
    assert not is_handed([load(fz=500.0), load(fz=-500.0, my=3.0)], n_w)

    # Nets to zero, but each half is a real side load: handed.
    assert is_handed([load(fy=400.0), load(fy=-400.0)], n_w)
    # A roll or yaw component is enough on its own.
    assert is_handed([load(mx=1.0)], n_w)
    assert is_handed([load(mz=1.0)], n_w)

    # The threshold is a fraction of n*W, so it means the same on any airplane.
    just_under = 0.4 * HANDEDNESS_TOL * n_w
    assert not is_handed([load(fy=just_under), load(fy=just_under)], n_w)
    assert is_handed([load(fy=just_under), load(fy=just_under)], n_w / 10.0)

    # D-R8: a net rolling moment made by the DISTRIBUTION itself -- 23.427(a)'s
    # only signature, since it carries no side force and no free moment. It
    # needs a length to be judged against, and with none supplied the roll test
    # is skipped rather than run against a number whose units decide it.
    span = 100.0
    split = [BalancedLoad(x=0.0, y=+50.0, z=0.0, fz=-100.0),
             BalancedLoad(x=0.0, y=-50.0, z=0.0, fz=-72.0)]
    assert is_handed(split, n_w, span)
    assert not is_handed(split, n_w)
    # A mirror-symmetric distribution is not handed by it, at any length.
    even = [BalancedLoad(x=0.0, y=+50.0, z=0.0, fz=-100.0),
            BalancedLoad(x=0.0, y=-50.0, z=0.0, fz=-100.0)]
    assert not is_handed(even, n_w, span)


@pytest.mark.parametrize("example", _with_cases())
def test_the_handed_twins_are_mirror_images(example):
    """The port twin is the starboard case reflected -- pairwise, load by load.

    Everything even under the mirror is *identical* (the twin's vertical,
    longitudinal and pitching balance is the same case), and everything odd
    reverses. Checked on the loads themselves rather than on totals, because a
    totals-only check passes for a case that reflected nothing at all.

    **G7**, extended by B8a-3 to the lateral family, where the mirror has a
    physical name: the port twin of a rudder kick is the *opposite* kick, the
    ``-beta`` of a ``+beta`` case. That makes the applied set odd as well as the
    closure -- the fin's ``fy`` and its ``mz`` torsion both reverse -- which the
    rolling family, whose applied loads are all symmetric, never exercised.
    """
    cases = build_balanced_cases(_project(example))
    pairs = [(a, b) for a, b in zip(cases, cases[1:])
             if a.hand == "R" and b.hand == "L" and a.label == b.label]
    assert pairs, f"{example}: no handed pair"
    for right, left in pairs:
        assert right.case_ref.case_id.endswith("R")
        assert left.case_ref.case_id == right.case_ref.case_id[:-1] + "L"
        assert left.unbal_moment == -right.unbal_moment
        # Odd under the mirror -- the lateral three, all of which B8a-2 made
        # non-trivial: roll reverses, and so do the yaw and side-force relief it
        # induces through Ixz.
        assert left.p_dot == -right.p_dot
        assert left.r_dot == -right.r_dot
        assert left.delta_ny == -right.delta_ny
        assert left.residual_fy == -right.residual_fy
        assert left.residual_mx == -right.residual_mx
        assert left.residual_mz == -right.residual_mz
        assert fin_load(left) == -fin_load(right)
        # Even under the mirror: the twin is the same case in these DOF.
        assert left.residual_fz == right.residual_fz
        assert left.residual_fx == right.residual_fx
        assert left.residual_my == right.residual_my
        assert left.delta_n == right.delta_n
        assert left.q_dot == right.q_dot
        assert len(left.loads) == len(right.loads)
        for a, b in zip(right.loads, left.loads):
            assert (b.x, b.y, b.z) == (a.x, -a.y, a.z)
            assert (b.fx, b.fy, b.fz) == (a.fx, -a.fy, a.fz)
            assert (b.mx, b.my, b.mz) == (-a.mx, a.my, -a.mz)
            assert b.source == a.source


def test_a_symmetric_case_has_no_twin():
    """A symmetric case is its own mirror image; minting a twin would put the same
    load set in the deck twice."""
    cases = build_balanced_cases(_project("ga6_normal.project.json"))
    symmetric = next(c for c in cases if not c.hand)
    with pytest.raises(ValueError, match="no hand"):
        handed_twin(symmetric)


def test_the_reflection_operator_is_an_involution():
    """The B-6 drift guard: reflect twice and you are back where you started.

    The operator has **one owner** (``export/coordinates.py``) precisely because a
    sign convention copied to a second call site is the class of error that
    produces a deck which parses, solves, and sizes structure to a load the
    airplane never sees. This is the guard ``CLAUDE.md`` practice 3 asks for
    alongside that owner.
    """
    assert reflect_point(1.0, 2.0, 3.0) == (1.0, -2.0, 3.0)
    assert reflect_force(1.0, 2.0, 3.0) == (1.0, -2.0, 3.0)
    # A moment is an axial vector and transforms the other way round: roll and
    # yaw reverse, pitch does not. Applying the force rule here would mirror a
    # rolling case into itself and negate its pitch.
    assert reflect_moment(1.0, 2.0, 3.0) == (-1.0, 2.0, -3.0)
    assert reflect_side("R") == "L" and reflect_side("L") == "R"
    assert reflect_side("C") == "C"
    for v in ((1.0, 2.0, 3.0), (-4.5, 0.0, 6.25)):
        assert reflect_point(*reflect_point(*v)) == v
        assert reflect_force(*reflect_force(*v)) == v
        assert reflect_moment(*reflect_moment(*v)) == v


@pytest.mark.parametrize("example", _with_cases())
def test_the_rolling_deck_states_that_it_rolls(example):
    """A rolling deck must say so, and say the couple is applied rather than
    unbalanced -- otherwise a reader sees a 2-7 % 'residual' and distrusts the
    case for the wrong reason."""
    text = balanced_deck(_project(example))
    assert "ROLLING case: applied aileron couple" in text
    assert "STARBOARD roll" in text and "PORT roll" in text
    over = [ln for ln in text.splitlines() if ln.startswith("$") and len(ln) > 72]
    assert not over, over


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
