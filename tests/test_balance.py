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

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io  # noqa: E402
from sloads.export.balanced_deck import (  # noqa: E402
    BALANCED_SID_BASE,
    BALANCED_WING_L_BASE,
    BALANCED_WING_R_BASE,
    balanced_deck,
    deck_nodes,
)
from sloads.export.coordinates import (  # noqa: E402
    reflect_force,
    reflect_moment,
    reflect_point,
    reflect_side,
)
from sloads.export.equilibrium import parse_cards, resultant  # noqa: E402
from sloads.modules.balance import (  # noqa: E402
    RESIDUAL_GATE,
    ROLLING_WING_CONDITIONS,
    SYMMETRIC_WING_CONDITIONS,
    build_balanced_cases,
    carry_sources_absent,
    handed_twin,
    resultant6,
)
from sloads.modules.balance import resultant as case_resultant  # noqa: E402
from sloads.modules.wing_inertia import inertia_units  # noqa: E402
from sloads.units import Channel, UnitSystem, deliverable_units  # noqa: E402

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
_EXPECTED_CASES = {
    "ga6_normal.project.json": [
        ("PHAA", ""), ("PLAA", ""), ("PMAA", ""), ("NMAA", ""),
        ("ACRL", "R"), ("ACRL", "L"), ("TORS", ""),
    ],
    "cessna_210.project.json": [],
    "atr42_100.project.json": [],
    "dhc8_dash8.project.json": [],
    "concept_heavy.project.json": [],
    "concept_regional_jet.project.json": [
        ("PHAA", ""), ("PLAA", ""), ("PMAA", ""),
        ("ACRL", "R"), ("ACRL", "L"), ("TORS", ""),
    ],
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
#: These are upper bounds, not targets: they bite on any regression.
_PITCH_RESIDUAL_CEILING = {
    "ga6_normal.project.json": 0.0030,
    "concept_regional_jet.project.json": 0.0120,
}


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

    The **roll** DOF is deliberately not gated here: on a rolling case
    ``residual_mx`` is the applied aileron couple, which the airplane is supposed
    not to balance. See :func:`test_the_roll_moment_is_the_applied_couple`.
    """
    for case in build_balanced_cases(_project(example)):
        where = f"{example} {case.label}{case.hand}"
        assert case.force_residual_fraction < RESIDUAL_GATE, (
            f"{where}: force residual {case.force_residual_fraction * 100:.3f} %")
        assert case.moment_residual_fraction < _PITCH_RESIDUAL_CEILING[example], (
            f"{where}: pitch residual {case.moment_residual_fraction * 100:.3f} %")


@pytest.mark.parametrize("example", _with_cases())
def test_the_closure_relief_is_small(example):
    """``|dn|/n < 1 %`` (plan 11 acceptance 2) -- how much of the balance was
    assumed rather than computed."""
    for case in build_balanced_cases(_project(example)):
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
    cgs = {c.name: c for c in p.flight_loads.cg_cases}
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
    """
    p = _project(example)
    cgs = {c.name: c for c in p.flight_loads.cg_cases}
    cases = build_balanced_cases(p)
    u = deliverable_units(system, Channel.SOLVER)
    grids, _, _, forces, moments = parse_cards(
        balanced_deck(p, system=system, cases=cases))
    for i, case in enumerate(cases):
        cg = cgs[case.cg]
        ref = (cg.xcg * u.length.factor, 0.0, cg.zcg * u.length.factor)
        got = resultant(forces, moments, grids, BALANCED_SID_BASE + i, ref)
        n_w = case.n_w * case.safety_factor * u.force.factor
        n_w_mac = n_w * case.mac * u.length.factor
        where = f"{example} {system.value} {case.label}"
        # 1e-5 is the %.6E card format accumulated over ~150 cards, not physics.
        assert abs(got.fx) < 1e-5 * n_w, f"{where} Fx"
        assert abs(got.fz) < 1e-5 * n_w, f"{where} Fz"
        assert abs(got.my) < 1e-5 * n_w_mac, f"{where} My"


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
    """
    for case in build_balanced_cases(_project(example)):
        where = f"{example} {case.label}{case.hand}"
        assert case.residual_mx == pytest.approx(-case.unbal_moment, abs=1e-6), where
        if not case.hand:
            assert case.unbal_moment == 0.0, where


@pytest.mark.parametrize("example", _with_cases())
def test_roll_closure_reproduces_winginer(example):
    """**The B7 closure gate.** The roll relief == WINGINER's unit-roll set.

    Concept mode has no printed oracle, so a stated closure gate against an
    *independent producer* stands in for one (``CLAUDE.md`` practice 2). Here the
    two producers are as independent as the codebase allows: WINGINER's
    ``fz_r``/``iwxx`` recurrence, which is oracle-locked FAR 23 code untouched by
    this step, and the balance layer's roll-acceleration solve, which knows
    nothing about it and closes a residual it computed itself.

    They agree strip for strip, ratio 1.000000 -- and the wing-item/WINGINER-panel
    scale (0.9903 on ga6, 1.0100 on the RJ) cancels identically, because the
    closure normalises on the same masses the assembled model carries.
    """
    project = _project(example)
    wm = project.wing_mass
    geom = project.geometry.by_name(wm.surface)
    u = inertia_units(geom, wm)
    winginer = {round(y, 6): f for y, f in zip(u.ye, u.fz_r) if f}

    rolling = [c for c in build_balanced_cases(project) if c.hand == "R"]
    assert rolling, f"{example}: no rolling case to check"
    for case in rolling:
        ur = case.unbal_moment / 100000.0
        strips = [ld for ld in case.loads
                  if ld.source == "closure-roll" and ld.y > 0
                  and round(ld.y, 6) in winginer]
        assert len(strips) >= 5, f"{example}: only {len(strips)} strips matched"
        for ld in strips:
            want = ur * winginer[round(ld.y, 6)]
            assert ld.fz == pytest.approx(want, rel=1e-9), (
                f"{example} {case.label} strip y={ld.y}: {ld.fz} vs {want}")


@pytest.mark.parametrize("example", _with_cases())
def test_the_case_closes_in_all_six_dof(example):
    """After relief, all six rigid-body components are zero to machine precision.

    The three symmetric DOF were already gated at B2; roll is the one B7 adds, and
    it is the one an antisymmetric case fails silently without -- ``ACRL``
    assembled with no roll term closes ``Fx``/``Fz``/``My`` to 1e-11 while
    carrying a whole unreacted aileron couple.
    """
    project = _project(example)
    cgs = {c.name: c for c in project.flight_loads.cg_cases}
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
    """No load in any shipped family has a side component, and nothing invents one.

    ``Fy``/``Mz`` are computed rather than assumed so B8a's lateral cases inherit
    a complete resultant; this pins that today they are identically zero, which is
    what makes the roll check above unambiguous.
    """
    for case in build_balanced_cases(_project(example)):
        # Exactly zero on the loads -- nothing constructs a side component...
        assert all(ld.fy == 0.0 and ld.mz == 0.0 for ld in case.loads), case.label
        # ...so the resultant is zero to summation rounding, no more.
        assert case.residual_fy == 0.0, case.label
        assert abs(case.residual_mz) < 1e-6 * case.n_w * case.semi_span, case.label


@pytest.mark.parametrize("example", _with_cases())
def test_the_handed_twins_are_mirror_images(example):
    """The port twin is the starboard case reflected -- pairwise, load by load.

    Everything even under the mirror is *identical* (the twin's vertical,
    longitudinal and pitching balance is the same case), and everything odd
    reverses. Checked on the loads themselves rather than on totals, because a
    totals-only check passes for a case that reflected nothing at all.
    """
    cases = build_balanced_cases(_project(example))
    pairs = [(a, b) for a, b in zip(cases, cases[1:])
             if a.hand == "R" and b.hand == "L" and a.label == b.label]
    assert pairs, f"{example}: no handed pair"
    for right, left in pairs:
        assert right.case_ref.case_id.endswith("R")
        assert left.case_ref.case_id == right.case_ref.case_id[:-1] + "L"
        assert left.unbal_moment == -right.unbal_moment
        assert left.delta_roll == -right.delta_roll
        # Even under the mirror: the twin is the same case in these DOF.
        assert left.residual_fz == right.residual_fz
        assert left.residual_fx == right.residual_fx
        assert left.residual_my == right.residual_my
        assert left.delta_n == right.delta_n
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
