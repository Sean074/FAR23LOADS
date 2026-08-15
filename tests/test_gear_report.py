"""The gear free body and the assembled ground cases -- step 10 piece 3.

Decisions **G-2**, **G-6**, **G-7/G-7a**, **G-8**, **G-12/G-12a** and **G-13** of
``docs/30_future/18_step10_ground_cases_plan.md``.

**This file holds the step's benchmark-first gate**, and it is worth saying what
makes it one. There is no printed oracle for an assembled ground case -- Appendix
A prints LANDLOAD's reactions, not an airplane in equilibrium -- so ``CLAUDE.md``
asks instead for "a stated physics-closure / invariant gate in CI, written with
the feature". The gate here is stronger than that phrasing usually buys, because
the two sides are computed by genuinely different routes:

* **sloads** assembles gear reactions, wing lift and the itemized mass model and
  solves a six-DOF rigid-body field on the assembled inertia tensor;
* **LANDLOAD** reaches ``NVP``/``NDP``/``NS`` by lever arms and FAR percentages,
  with no mass matrix anywhere in it.

They agree to floating-point noise on every case of every fixture. That agreement
is content-carrying rather than self-referential, which is exactly what the
oracle rule exists to buy where an oracle exists.

Run standalone:  ``python tests/test_gear_report.py``
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io  # noqa: E402
from sloads.export.balanced_deck import (  # noqa: E402
    BALANCED_GEAR_BASE,
    balanced_deck,
    deck_nodes,
)
from sloads.export.sbeam_bridge import gear_report_rows  # noqa: E402
from sloads.gear_loads import (  # noqa: E402
    MAIN,
    NOSE,
    applied_wheels,
    attitude_of,
    gear_case_loads,
    ground_rotation_deg,
    to_ground_line,
    transfer_couple,
)
from sloads.models import MissingInputError  # noqa: E402
from sloads.modules.balance import (  # noqa: E402
    GROUND_ONE_WHEEL_CASES,
    GROUND_SIDE_CASES,
    build_balanced_cases,
    is_ground,
    resultant6,
)
from sloads.modules.landing import build_landing  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Every shipped fixture, and whether it can produce a gear report at all.
#: **G-13's coverage pin for the report**, and deliberately a *different* set
#: from the assembled ground cases': the report needs LANDLOAD output and gear
#: geometry and **no mass model**, so it reaches five airplanes where the
#: assembled cases reach two. Stating the asymmetry rather than smoothing it over
#: is the point -- a reader who finds ground cases on two fixtures and gear rows
#: on five should be able to see immediately that this is by construction.
_GEAR_FIXTURES = {
    "ga6_normal.project.json": True,
    "cessna_210.project.json": True,
    "atr42_100.project.json": True,
    "dhc8_dash8.project.json": True,
    "concept_regional_jet.project.json": True,
    # No gear geometry and no landing slice -- backlog: giving it both is cheap
    # fixture data and buys a sixth fixture plus the only concept-mode exercise
    # of the 23.473(g) floor warning. The step is not held for it.
    "concept_heavy.project.json": False,
}

_WITH_GEAR = [e for e, v in _GEAR_FIXTURES.items() if v]

#: The fixtures whose ground cases actually assemble (they need a **derivable**
#: mass loading as well). Two, per G-13 -- and the four that do not are the
#: already-pinned Pri 9 fixture-data finding, not anything about this step.
_WITH_GROUND_CASES = ["ga6_normal.project.json", "concept_regional_jet.project.json"]


def _project(example: str):
    return io.load_project(os.path.join(_ROOT, "examples", example))


# --------------------------------------------------------------------------- #
# Coverage (G-13)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", sorted(_GEAR_FIXTURES))
def test_which_fixtures_produce_a_gear_report_is_pinned(example):
    """Pinned, not chased: the report's coverage is a recorded fact.

    It goes red the day ``concept_heavy`` gains gear geometry, which is the
    mechanism ``test_which_conditions_assemble_is_pinned`` already uses.
    """
    try:
        cases = gear_case_loads(_project(example))
    except MissingInputError:
        cases = []
    assert bool(cases) is _GEAR_FIXTURES[example], example


@pytest.mark.parametrize("example", _WITH_GEAR)
def test_the_report_carries_all_thirty_three_cases(example):
    """**All 33**, against the assembled deck's 24 -- the G-6 amendment.

    The 23.499 supplementary nose-wheel family is not merely excluded from the
    assembled cases, it has a home: 25-33 are gear-design cases and this report
    is where they were always aimed. The two artifacts carry different case sets
    **by design**, and that is asserted here rather than left to be noticed.
    """
    cases = gear_case_loads(_project(example))
    assert [c.case for c in cases] == list(range(1, 34))
    supplementary = [c for c in cases if c.case >= 25]
    assert len(supplementary) == 9
    # The family's defining property, and the reason it cannot be assembled: no
    # main-gear reaction exists anywhere in it, so there is no airplane in
    # equilibrium to balance.
    for case in supplementary:
        main = next(leg for leg in case.legs if leg.leg == MAIN)
        assert not any(main.ground_line), (case.case, main.ground_line)
        nose = next(leg for leg in case.legs if leg.leg == NOSE)
        assert any(nose.ground_line), case.case


# --------------------------------------------------------------------------- #
# G-2's third guard: the transfer preserves resultants
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _WITH_GEAR)
def test_the_transfer_to_the_reference_point_preserves_the_resultant(example):
    """**G-2's third guard.** The reaction is identical before and after the move.

    LANDLOAD computes the reaction at the tyre contact patch -- 23.485(d) puts it
    there -- and the transfer to the attachment node is *ours*, which is exactly
    why it is policed. Force plus the lever-arm couple at the node has the same
    resultant about **every** reference as the force alone at the patch, so this
    is a property of the construction rather than an approximation, and it is
    gated exactly (``rel_tol 1e-12``) rather than to a tolerance.

    Taken about a deliberately arbitrary point, not about the CG: about the CG a
    dropped couple could still cancel against something. Measured worst case over
    all 33 cases and both legs on ``ga6_normal``: 3.4e-16.
    """
    ref = (80.0, 3.0, 90.0)          # arbitrary, and nothing in the model is here
    worst = 0.0
    for case in gear_case_loads(_project(example)):
        for leg in case.legs:
            if not any(leg.airplane):
                continue
            fx, fy, fz = leg.airplane
            px, py, pz = leg.patch
            nx, ny, nz = leg.node
            mx, my, mz = leg.couple
            before = ((py - ref[1]) * fz - (pz - ref[2]) * fy,
                      (pz - ref[2]) * fx - (px - ref[0]) * fz,
                      (px - ref[0]) * fy - (py - ref[1]) * fx)
            after = (mx + (ny - ref[1]) * fz - (nz - ref[2]) * fy,
                     my + (nz - ref[2]) * fx - (nx - ref[0]) * fz,
                     mz + (nx - ref[0]) * fy - (ny - ref[1]) * fx)
            scale = max(abs(v) for v in before) or 1.0
            worst = max(worst, max(abs(a - b) for a, b in zip(before, after)) / scale)
    assert worst < 1e-12, f"{example}: worst relative moment error {worst:.3e}"


def test_dropping_the_offset_couple_breaks_the_transfer():
    """**G-13's first negative control.** A gate is trusted once it has failed.

    Targets G-2's transfer directly: drop the lever-arm couple and the reaction
    about any other point is no longer the reaction that was computed. This is
    the failure the assembled residual alone would **never** catch -- a transfer
    that dropped its couple consistently still sums to zero at a determinate
    support, which is precisely why the guard above is written about an arbitrary
    reference rather than about the CG.
    """
    case = next(c for c in gear_case_loads(_project("ga6_normal.project.json"))
                if c.case == 16)                     # braked roll: big drag load
    leg = next(leg for leg in case.legs if leg.leg == MAIN)
    ref = (80.0, 3.0, 90.0)
    fx, fy, fz = leg.airplane
    px, _, pz = leg.patch
    nx, _, nz = leg.node
    before_my = (pz - ref[2]) * fx - (px - ref[0]) * fz
    without_couple_my = (nz - ref[2]) * fx - (nx - ref[0]) * fz
    assert not math.isclose(before_my, without_couple_my, rel_tol=1e-6), (
        "the negative control cannot fire: this case's patch and node are too "
        "close for a dropped couple to matter, so it is the wrong case to "
        "target the guard with")
    # And the couple is exactly the difference it makes.
    assert math.isclose(before_my, without_couple_my + leg.couple[1], rel_tol=1e-12)


def test_the_couple_is_the_cross_product_and_nothing_else():
    """``M = (patch - node) x F``, asserted against a hand-written cross product.

    The single owner (:func:`sloads.gear_loads.transfer_couple`) checked against
    the formula rather than against itself -- ``CLAUDE.md`` practice 3 asks for a
    drift guard beside an owner, and an owner compared with a second call to
    itself is not one.
    """
    point, node, force = (10.0, 4.0, -2.0), (1.0, -1.0, 3.0), (7.0, -5.0, 11.0)
    rx, ry, rz = 9.0, 5.0, -5.0
    fx, fy, fz = force
    assert transfer_couple(point, node, force) == (
        ry * fz - rz * fy, rz * fx - rx * fz, rx * fy - ry * fx)


# --------------------------------------------------------------------------- #
# G-12: the geometry the report surfaces
# --------------------------------------------------------------------------- #
def test_the_strut_state_follows_landload_per_attitude():
    """Cases 1-12 are computed at the **compressed** axle, 13-33 at the static one.

    The manual's own split, followed rather than re-decided, and it is not a
    formality: on ``ga6_normal`` the level and ground-roll contact points differ
    by 0.49 in in ``x`` and **3.71 in in ``z``**, which is 6,706 lb-in of pitch on
    the braked-roll drag load.
    """
    for case in range(1, 13):
        assert attitude_of(case)[0] == "compressed", case
    for case in range(13, 34):
        assert attitude_of(case)[0] == "static", case
    with pytest.raises(ValueError, match="no ground attitude"):
        attitude_of(34)

    cases = {c.case: c for c in gear_case_loads(_project("ga6_normal.project.json"))}
    level = next(leg for leg in cases[1].legs if leg.leg == MAIN)
    roll = next(leg for leg in cases[16].legs if leg.leg == MAIN)
    assert math.isclose(roll.patch[0] - level.patch[0], 0.49, abs_tol=0.01)
    assert math.isclose(roll.patch[2] - level.patch[2], 3.71, abs_tol=0.01)
    # The application node does NOT move: a trunnion is fixed to the airframe, so
    # the attitude difference lands in the lever arm, where the physics puts it.
    assert level.node == roll.node


def test_the_stroke_is_recovered_from_the_three_axle_states():
    """ga6's main leg: 24 % of stroke in the landing attitudes, 77 % in the
    handling ones -- impact versus sitting, which no other deliverable states.

    No new input: the travel is the distance from the fully extended axle to the
    one the attitude is computed at, measured along the leg's own line so a leg
    that rakes as it compresses is not measured in ``z`` alone.
    """
    cases = {c.case: c for c in gear_case_loads(_project("ga6_normal.project.json"))}
    level = next(leg for leg in cases[1].legs if leg.leg == MAIN)
    roll = next(leg for leg in cases[16].legs if leg.leg == MAIN)
    assert math.isclose(level.stroke_in, 1.70, abs_tol=0.01)
    assert math.isclose(level.stroke_fraction, 0.243, abs_tol=0.005)
    assert math.isclose(roll.stroke_in, 5.42, abs_tol=0.01)
    assert math.isclose(roll.stroke_fraction, 0.775, abs_tol=0.005)


@pytest.mark.parametrize("example", _WITH_GEAR)
def test_the_two_frames_round_trip_through_the_rotation(example):
    """``rho`` recovers the ground-line pair from the airplane-datum one, exactly.

    The rotation is measured from the case's **own two resolutions** of one
    reaction rather than from ``GRA``, which is what lets this step avoid
    adjudicating a sign inconsistency that is in LANDLOAD.BAS itself (``beta`` is
    ``gamma - GRA(1)`` for the level attitude and ``+GRA(2)`` for the ground-roll
    one). Asserting the round trip is what makes ``rho`` trustworthy enough to
    carry G-7a's lift axis and G-6's gate.

    It also asserts what G-12 calls out as *correct but non-obvious*: ``SMP``
    passes through **unrotated**, being normal to the pitch rotation.
    """
    for case in gear_case_loads(_project(example)):
        for leg in case.legs:
            if not any(leg.airplane):
                continue
            rho = leg.rotation_deg
            v, d = to_ground_line(leg.airplane[2], leg.airplane[0], rho)
            assert math.isclose(v, leg.ground_line[0], abs_tol=1e-6 * max(1.0, abs(v)))
            assert math.isclose(d, leg.ground_line[1], abs_tol=1e-6 * max(1.0, abs(d)))
            # Side load: same number in both frames.
            assert leg.airplane[1] == leg.ground_line[2]


def test_the_frames_differ_by_the_amounts_the_design_note_measured():
    """The two G-12 figures, asserted so the frame choice cannot silently invert.

    ga6 case 1 drag: **1,020 lb ground-line against 795 lb airplane-datum**
    (-22 %). The side family: **0 lb ground-line drag against 186 lb** in the
    airplane datum. If these ever swap, a deck is applying the gear reaction in
    the wrong frame -- which parses, solves, and is wrong by a fifth.
    """
    cases = {c.case: c for c in gear_case_loads(_project("ga6_normal.project.json"))}
    level = next(leg for leg in cases[1].legs if leg.leg == MAIN)
    assert math.isclose(level.ground_line[1], 1020.2, abs_tol=0.5)
    assert math.isclose(level.airplane[0], 795.2, abs_tol=0.5)
    side = next(leg for leg in cases[19].legs if leg.leg == MAIN)
    assert side.ground_line[1] == 0.0
    assert math.isclose(side.airplane[0], 186.2, abs_tol=0.5)


def test_the_leg_inertia_is_stated_or_blank_and_never_guessed():
    """G-12a: ``0.0`` leg weight means *not stated*, and shows the free body open.

    ga6's main leg is 77.5 lb -- half the 155 lb its database carries for the
    main gear, because ``weight_lb`` is **per leg** and ``VMP`` is per wheel. At
    ``NVP`` 3.167 that is 245 lb against a 4,038 lb reaction, **6.1 %**: too
    large to leave out of a free body and small enough that pairing it with the
    wrong number of legs (as the design note first did) reads as plausible.
    """
    cases = {c.case: c for c in gear_case_loads(_project("ga6_normal.project.json"))}
    leg = next(x for x in cases[4].legs if x.leg == MAIN)
    assert leg.leg_weight_lb == 77.5
    assert math.isclose(leg.inertia_fz, 77.5 * 3.167, rel_tol=1e-3)
    assert math.isclose(leg.inertia_fz / leg.airplane[2], 0.0596, abs_tol=0.005)
    # Closed: the reaction less the leg's own inertia is what the structure above
    # the trunnion sees. The deck applies the *reaction* at the node and carries
    # the leg's mass separately, which is why both are reported.
    assert math.isclose(leg.net_of_inertia[2], leg.airplane[2] - leg.inertia_fz)

    # Not stated -> blank, not zero. A leg nobody weighed is not weightless.
    project = _project("ga6_normal.project.json")
    project.geometry.landing_gear.main_gear.weight_lb = 0.0
    unstated = next(x for x in next(
        c for c in gear_case_loads(project) if c.case == 4).legs if x.leg == MAIN)
    assert unstated.leg_weight_lb is None
    assert unstated.inertia_fz is None
    assert unstated.net_of_inertia is None
    rows = [r for r in gear_report_rows(project) if r["Leg"] == MAIN]
    assert rows and all(r["Leg inertia Fz"] == "" for r in rows)
    assert all(r["Net Fz above trunnion"] == "" for r in rows)


def test_the_entered_leg_weights_agree_with_the_item_database():
    """``2 x main + nose`` against the database's gear rows -- **pinned per fixture**.

    Two statements of one quantity is a drift risk, and it is held the way this
    project already holds that class (the ``unmodelled_wing_mass`` mechanism)
    rather than by a name-matching reconciliation in the calc -- which would put
    the very failure mode G-12a exists to avoid back into the code, where the pin
    puts it in a test.
    """
    expected = {
        "ga6_normal.project.json": (77.5, 49.0, 155.0 + 49.0),
        "cessna_210.project.json": (85.0, 57.0, 170.0 + 57.0),
        "atr42_100.project.json": (525.0, 260.0, 1050.0 + 260.0),
        "dhc8_dash8.project.json": (600.0, 300.0, 1200.0 + 300.0),
        "concept_regional_jet.project.json": (575.0, 300.0, 1150.0 + 300.0),
    }
    for example, (main, nose, database) in expected.items():
        lg = _project(example).geometry.landing_gear
        assert lg.main_gear.weight_lb == main, example
        assert lg.nose_gear.weight_lb == nose, example
        assert 2 * main + nose == database, example


# --------------------------------------------------------------------------- #
# G-6: the closed-form gate -- this step's benchmark
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _WITH_GROUND_CASES)
def test_the_ground_closure_reproduces_landload(example):
    """**The step's benchmark-first gate (G-6).**

    The six-DOF solve closes the case; LANDLOAD's inertia factors are the
    independent closed-form check on it. Rotate the solved rigid-body field back
    to the ground line and it must reproduce ``NVP``/``NDP``/``NS`` -- which it
    does to floating-point noise, on every case of both fixtures.

    **This is what FAR 23.471 asks for, not merely a convenient reuse:** *"the
    external reactions must be placed in equilibrium with the linear and angular
    inertia forces in a rational or conservative manner."* A six-DOF rigid-body
    closure over the itemized mass model is that sentence.

    Why the agreement carries content: LANDLOAD reaches these factors by lever
    arms and FAR percentages -- there is no mass matrix anywhere in it -- while
    this reaches them by solving one on the assembled item database. Two
    completely different routes, one answer.

    ``NVP``/``NDP`` are compared **after** rotation because they are stated about
    the ground line while the solve is in body axes. That rotation appears here,
    in the check, and **nowhere in the load path** -- which is the whole reason
    G-6 declined to consume ``NVP`` directly.
    """
    project = _project(example)
    _, reactions = build_landing(project)
    by_case = {c.case: c for c in reactions}
    cases = [c for c in build_balanced_cases(project) if is_ground(c)]
    assert cases, example

    for case in cases:
        gear = by_case[case.vn_case]
        rho = ground_rotation_deg(gear)
        nvp, ndp = to_ground_line(case.delta_n, case.delta_nx, rho)
        where = f"{example} {case.case_ref.case_id} (LANDLOAD case {case.vn_case})"
        assert math.isclose(nvp, gear.nvp, rel_tol=1e-9), f"{where}: NVP"
        assert math.isclose(ndp, gear.ndp, rel_tol=1e-9, abs_tol=1e-9), f"{where}: NDP"
        # NS is lateral and normal to the rotation, so it is compared as is.
        # The port twin of a side case carries the opposite sign, which is what
        # its own hand says -- so compare magnitudes and let the hand test below
        # police the sign.
        assert math.isclose(abs(case.delta_ny), abs(gear.ns),
                            rel_tol=1e-9, abs_tol=1e-9), f"{where}: NS"


@pytest.mark.parametrize("example", _WITH_GROUND_CASES)
def test_the_ground_case_closes_in_all_six_dof(example):
    """After closure, all six rigid-body components about the CG are zero.

    The universal property every balanced family shares. Stated for the ground
    family too rather than assumed from the flight families' passing it: these
    cases are the first in the suite whose applied set carries free moments on
    *both* sides of the centreline (the two transfer couples), and the first
    whose base load factor is zero.
    """
    for case in build_balanced_cases(_project(example)):
        if not is_ground(case):
            continue
        ref = (case.cg_x, 0.0, case.cg_z)
        components = resultant6(case.loads, ref)
        scale = max(case.n_w, 1.0)
        for name, value in zip("Fx Fy Fz Mx My Mz".split(), components):
            bound = scale * (1e-6 if name.startswith("F") else case.mac * 1e-6)
            assert abs(value) < max(bound, 1e-6), (
                f"{example} {case.case_ref.case_id}: {name} = {value:.6g}")


def test_the_static_contact_patch_breaks_the_level_landing_gate():
    """**G-13's second negative control.**

    Targets G-12's per-attitude geometry, which G-13 identifies as otherwise the
    least-guarded new decision in the note. Compute a level-landing case at the
    **static** axle instead of the compressed one and the closed-form factor gate
    must go red -- and it does, because the contact patch moves 3.71 in in ``z``
    and 0.49 in in ``x``, which changes the lever arms the moment balance is
    solved on.

    Asserted on the moment, not on ``NVP``: the vertical force factor is
    unchanged by moving the patch (the same force still acts), so a control that
    watched ``NVP`` alone would pass and prove nothing. That distinction is the
    reason this test exists rather than a blanket "perturb something" check.
    """
    project = _project("ga6_normal.project.json")
    case = next(c for c in gear_case_loads(project) if c.case == 4)
    leg = next(x for x in case.legs if x.leg == MAIN)

    honest = applied_wheels(case.legs)
    ref = (85.10, 0.0, 90.0)

    def pitching(wheels):
        my = 0.0
        for w in wheels:
            my += (w.couple[1] + (w.node[2] - ref[2]) * w.force[0]
                   - (w.node[0] - ref[0]) * w.force[2])
        return my

    honest_my = pitching(honest)

    # The same reaction, transferred from the WRONG attitude's contact patch.
    from dataclasses import replace as _replace
    wrong_patch = (leg.patch[0] + 0.49, leg.patch[1], leg.patch[2] + 3.71)
    broken = applied_wheels([_replace(x, patch=wrong_patch,
                                      couple=transfer_couple(wrong_patch, x.node,
                                                             x.airplane))
                             if x.leg == MAIN else x for x in case.legs])
    broken_my = pitching(broken)
    assert not math.isclose(honest_my, broken_my, rel_tol=1e-6), (
        "the negative control cannot fire -- the attitude's contact patch makes "
        "no difference to the pitching moment, which would mean the per-attitude "
        "geometry of G-12 is unguarded")


# --------------------------------------------------------------------------- #
# G-8: handedness, and LANDLOAD's own twins as the operator's check
# --------------------------------------------------------------------------- #
def test_the_reflected_side_case_reproduces_landloads_own_twin():
    """**G-8's external check on the reflection operator.**

    The 23.485 family is three loadings x two drift directions, so LANDLOAD
    supplies *both* hands. The suite assembles the **odd** member and derives the
    even one by reflection -- so the manual's own even-member figures are an
    independent check on the reflection operator, and the only external one it
    will ever get: every other reflection in the suite is guarded against itself.

    ``NS``, ``ROLLP`` and ``YAWP`` must come back sign-flipped and equal in
    magnitude.
    """
    _, reactions = build_landing(_project("ga6_normal.project.json"))
    by_case = {c.case: c for c in reactions}
    for odd, even in ((19, 20), (21, 22), (23, 24)):
        a, b = by_case[odd], by_case[even]
        assert math.isclose(a.ns, -b.ns, rel_tol=1e-12), (odd, even)
        assert math.isclose(a.rollp, -b.rollp, rel_tol=1e-12), (odd, even)
        assert math.isclose(a.yawp, -b.yawp, rel_tol=1e-12), (odd, even)
        # And the two wheels' side loads are the manual's 0.5 W / 0.33 W pair,
        # acting the same way globally and summing to the 0.83 W that NS states.
        assert math.isclose(a.smp, -0.5 * a.weight_lb, rel_tol=1e-9)
        assert math.isclose(b.smp, 0.33 * b.weight_lb, rel_tol=1e-9)
        assert math.isclose((a.smp - b.smp) / a.weight_lb, a.ns, rel_tol=1e-9)


def test_the_assembled_side_case_carries_both_wheels_side_loads():
    """The assembler reads the **partner** case for the second wheel (G-8).

    ``GearReactionCase`` carries a single ``SMP`` while an assembled side case
    needs both wheels -- 0.5 W on one and 0.33 W on the other. Reading the
    partner rather than re-deriving the percentages is what keeps 23.485(c) in
    one place; the resulting total is ``NS x W``, which is asserted here and
    again, from the other end, by the closure gate above.
    """
    project = _project("ga6_normal.project.json")
    _, reactions = build_landing(project)
    by_case = {c.case: c for c in reactions}
    case = next(c for c in gear_case_loads(project) if c.case == 19)
    wheels = applied_wheels(case.legs,
                            partner_side_lb=by_case[20].smp)
    mains = [w for w in wheels if w.leg == MAIN]
    assert len(mains) == 2
    starboard = next(w for w in mains if w.side == "R")
    port = next(w for w in mains if w.side == "L")
    assert math.isclose(starboard.force[1], by_case[19].smp)
    assert math.isclose(port.force[1], -by_case[20].smp)
    total = starboard.force[1] + port.force[1]
    assert math.isclose(total / by_case[19].weight_lb, by_case[19].ns, rel_tol=1e-9)


@pytest.mark.parametrize("example", _WITH_GROUND_CASES)
def test_the_handed_ground_families_are_the_measured_ones(example):
    """Only the one-wheel and side families have a hand, and it is measured.

    G-8's table, asserted: the level, tail-down and braked-roll families load
    both main wheels equally and have ``ROLLP = YAWP = 0``, so they are their own
    mirror image and are minted unhanded. Emitting twins for them would put the
    same load set in the deck twice.
    """
    for case in build_balanced_cases(_project(example)):
        if not is_ground(case):
            continue
        number = case.vn_case
        handed = number in GROUND_ONE_WHEEL_CASES or number in GROUND_SIDE_CASES
        assert bool(case.hand) is handed, (
            f"{example} {case.case_ref.case_id}: hand {case.hand!r}")


# --------------------------------------------------------------------------- #
# G-13: the loop between the two artifacts, closed through the deck
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _WITH_GROUND_CASES)
def test_the_deck_applies_the_reports_reference_point_reaction(example):
    """**The G-12/G-13 loop: one load, two artifacts, checked against each other.**

    The gear report states what arrives at the reference point; the assembled
    deck applies it at that node. They must be the same numbers, case by case and
    leg by leg -- which is what makes the two artifacts *provably* one load seen
    from two sides rather than two calculations that happen to agree.

    Read from the deck's own **card text**, not from a second call to the
    builder, and found by **GID band** rather than by coordinate -- which is what
    the gear band (decision G-2) exists for.
    """
    from sloads.case_ids import balanced_subcase_id

    project = _project(example)
    cases = [c for c in build_balanced_cases(project) if is_ground(c)]
    nodes = deck_nodes(build_balanced_cases(project), project)
    gear_gids = {gid for gid in nodes.values()
                 if BALANCED_GEAR_BASE <= gid < BALANCED_GEAR_BASE + 100}
    assert gear_gids, example

    text = balanced_deck(project)
    applied: dict = {}
    for line in text.splitlines():
        if not line.startswith("FORCE,"):
            continue
        f = [p.strip() for p in line.split(",")]
        sid, gid = int(f[1]), int(f[2])
        if gid not in gear_gids:
            continue
        applied.setdefault((sid, gid), [0.0, 0.0, 0.0])
        for i in range(3):
            applied[(sid, gid)][i] += float(f[5 + i])

    checked = 0
    for case in cases:
        sid = balanced_subcase_id(case.case_ref.case_id, case.hand)
        sf = case.safety_factor
        for load in case.loads:
            if not load.source.startswith("gear-"):
                continue
            gid = nodes[(load.side, round(load.x, 6), round(load.y, 6),
                         round(load.z, 6))]
            got = applied[(sid, gid)]
            want = (load.fx * sf, load.fy * sf, load.fz * sf)
            for g, w in zip(got, want):
                assert math.isclose(g, w, rel_tol=1e-5, abs_tol=1e-6), (
                    example, case.case_ref.case_id, gid)
            checked += 1
    assert checked, example


@pytest.mark.parametrize("example", _WITH_GEAR)
def test_the_report_rows_are_ultimate_at_the_governing_factor(example):
    """Every load in the report is ULTIMATE at the factor the governing table gives.

    Ground loads are **limit** loads by the regulation's own words (23.471), so
    the factor is 1.5 (23.303) -- G-10. The report states loads, so the standing
    load-output contract applies to it exactly as to every other channel, and the
    factor comes from the governing table rather than from a literal here.
    """
    from sloads.safety_factors import table_for

    project = _project(example)
    rows = gear_report_rows(project)
    assert rows, example
    factor = table_for(project).factor_for(
        gear_case_loads(project)[0]).factor
    assert factor == 1.5, example

    limit = {c.case: c for c in build_landing(project)[1]}
    for row in rows:
        if row["Leg"] != MAIN or not row["Ground-line V"]:
            continue
        want = limit[int(row["Case"])].vmp * factor
        assert math.isclose(float(row["Ground-line V"]), want, rel_tol=1e-6), row["ID"]


if __name__ == "__main__":                                   # zero-dependency runner
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        marks = getattr(fn, "pytestmark", [])
        params = [m.args[1] for m in marks if m.name == "parametrize"]
        for args in (params[0] if params else [None]):
            try:
                fn(args) if args is not None else fn()
            except Exception as exc:                          # noqa: BLE001
                failures += 1
                print(f"FAIL {name}{f'[{args}]' if args else ''}: {exc}")
    print("FAILURES:" if failures else "OK", failures or "")
    sys.exit(1 if failures else 0)
