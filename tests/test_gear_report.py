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
* **LANDLOAD** reaches ``NVP``/``NDP``/``NS`` and
  ``PITCHP``/``ROLLP``/``YAWP`` by lever arms and FAR percentages, with no mass
  matrix anywhere in it.

They agree to floating-point noise on every case of every fixture. That agreement
is content-carrying rather than self-referential, which is exactly what the
oracle rule exists to buy where an oracle exists.

The gate is in **two halves**, as G-6 wrote it. The translational half
(``test_the_ground_closure_reproduces_landload``) compares the solved load-factor
field with ``NVP``/``NDP``/``NS``; the rotational half
(``test_the_ground_closure_reproduces_landloads_unbalanced_moments``, R6-T1)
compares ``[I]{omega_dot}`` with the unbalanced moments, carrying the two
deliberate departures -- G-7a's distributed lift and G-12's contact patch -- in
the line rather than in the tolerance. The rotational half is also where the
frames stop agreeing with each other: see
``test_the_ground_roll_attitude_is_resolved_against_the_other_sign``.

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
    GROUND_LIFT_CASES,
    GROUND_ONE_WHEEL_CASES,
    GROUND_SIDE_CASES,
    build_balanced_cases,
    is_ground,
    resultant6,
)
# ``_effective_gear_input`` is the module's own resolver for the gear geometry
# (M2R-4: nothing is written back to the project), and the rotational gate needs
# the same axle stations the reactions were computed at. Reaching for it is the
# alternative to keeping a second copy of that resolution beside the test.
from sloads.modules.landing import (  # noqa: E402
    _effective_gear_input,
    build_landing,
    ground_angles,
)

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
def _is_reflected(case, gear) -> bool:
    """Is this assembled case the **reflected twin** rather than the computed one?

    The two handed ground families answer it differently, and the asymmetry is
    G-8's, not this test's: LANDLOAD supplies **both** drift directions of the
    23.485 side condition under ids of their own, so there the computed member is
    the one carrying LANDLOAD's own id and the twin carries the partner's. The
    23.483 one-wheel family has a single id and no twin in the manual at all, so
    the assembler mints the starboard case and reflects it.
    """
    if case.vn_case in GROUND_ONE_WHEEL_CASES:
        return case.hand == "L"
    return bool(gear.case_ref) and case.case_ref.case_id != gear.case_ref.case_id


def _mass_centroid(case):
    """The centroid of the masses the assembled case actually carries.

    The point the closure field is referred to (``balance._closure``), and
    therefore the point ``[I]{omega_dot}`` is a moment about. Recomputed here
    rather than exposed on the result: it is one weighted mean over the case's
    own loads, and the gate wants to state the frame transfer it is making out
    loud rather than accept one.
    """
    masses = [(ld, ld.weight_lb) for ld in case.loads if ld.weight_lb]
    total = sum(w for _, w in masses)
    return tuple(sum(getattr(ld, axis) * w for ld, w in masses) / total
                 for axis in "xyz")


def _cross(r, f):
    return (r[1] * f[2] - r[2] * f[1],
            r[2] * f[0] - r[0] * f[2],
            r[0] * f[1] - r[1] * f[0])


def _solved_moment_about_cg(case):
    """``[I]{omega_dot}``, transferred from the mass centroid to the case's CG.

    Two steps, both of which the gate exists to check. ``[I]{omega_dot}`` is the
    moment the solved angular field takes; it is a moment **about the centroid**,
    because that is where the closure is referred and where the rotational relief
    carries no net force. LANDLOAD states its unbalanced moments about the
    **CG**, so the applied resultant's own transfer ``M_cg = M_c + (c - cg) x F``
    is undone here. On ``ga6_normal`` the two points differ by thousandths of an
    inch and the transfer is worth ~900 lb-in on a 180,000 lb-in pitching moment
    -- a 0.5 % term that a gate written at ``rel_tol 1e-9`` cannot skip.
    """
    solved = case.closure_inertia.moment((case.p_dot, case.q_dot, case.r_dot))
    cg = (case.cg_x, 0.0, case.cg_z)
    offset = tuple(c - g for c, g in zip(_mass_centroid(case), cg))
    force = (case.residual_fx, case.residual_fy, case.residual_fz)
    return tuple(s + t for s, t in zip(solved, _cross(offset, force)))


def _lift_moment_about_cg(case, gear, lift_factor):
    """The **G-7a** departure, rebuilt in closed form: ``L x W`` along the ground line.

    The one place the assembled ground case deliberately differs from LANDLOAD,
    and G-6 asked for it in the pitch line explicitly rather than absorbed in
    slack: LANDLOAD nets the lift at the CG (``NLG = N - L``) while this
    distributes it on the wing, which leaves a pitching moment the manual never
    forms.

    The **magnitude and the axis are rebuilt** from the two statements that own
    them -- ``L x W_case`` for the size (G-7) and the ground line for the
    direction (G-7a) -- so changing either goes red here. Only the lift
    *centroid* is read from the applied set, because the AIRLOADS spanwise shape
    is what puts it there and re-deriving Schrenk in a test would be the second
    copy ``CLAUDE.md`` practice 3 forbids. That the two agree exactly is asserted
    before the term is used.
    """
    lift_lb = lift_factor * gear.weight_lb if gear.case in GROUND_LIFT_CASES else 0.0
    if not lift_lb:
        assert not [ld for ld in case.loads if ld.source == "ground-lift"], (
            f"{case.case_ref.case_id}: lift applied to a family that carries none")
        return (0.0, 0.0, 0.0)
    lift = [ld for ld in case.loads if ld.source == "ground-lift"]
    total = sum(math.hypot(ld.fx, ld.fz) for ld in lift)
    centroid = tuple(sum(getattr(ld, axis) * math.hypot(ld.fx, ld.fz)
                         for ld in lift) / total for axis in "xyz")
    rho = math.radians(ground_rotation_deg(gear))
    vector = (lift_lb * math.sin(rho), 0.0, lift_lb * math.cos(rho))
    cg = (case.cg_x, 0.0, case.cg_z)
    moment = _cross(tuple(c - g for c, g in zip(centroid, cg)), vector)
    # The closed form and the applied set are the same load, stated twice.
    applied = _resultant_of(case, {"ground-lift"}, cg)
    for want, got, axis in zip(moment, applied, "xyz"):
        assert math.isclose(want, got, rel_tol=1e-9, abs_tol=1e-6 * lift_lb), (
            f"{case.case_ref.case_id}: lift moment {axis} {want} != {got}")
    return moment


def _resultant_of(case, sources, ref):
    """The moment about ``ref`` of just the named load sources."""
    picked = [ld for ld in case.loads if ld.source in sources]
    return resultant6(picked, ref)[3:]


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
        # NS is lateral and normal to the rotation, so it is compared as is --
        # and **signed** (R6-T2). The computed member of a 23.485 pair carries
        # LANDLOAD's own printed sign; only the reflected twin negates it, and
        # which one is which is a fact about the case, not a free choice, so the
        # gate states it rather than comparing magnitudes and leaving the sign to
        # the hand pin.
        want = -gear.ns if _is_reflected(case, gear) else gear.ns
        assert math.isclose(case.delta_ny, want,
                            rel_tol=1e-9, abs_tol=1e-9), f"{where}: NS"


#: The families whose ``PITCHP`` is ``mult x RMP x BP`` -- one resultant on one
#: arm, and ``BP`` is measured to the **axle** (``landing._geometry`` builds it
#: from ``axle_compressed``/``axle_static``). The braked-roll families 13-18 are
#: the exception: their ``-2(VMP x BP + DMP x CP)`` puts the drag arm ``CP`` on
#: the **ground line**, where the tyre is. The assembled case applies every
#: reaction at the contact patch (G-2/G-12; FAR 23.485(d) says so in as many
#: words), so the gate moves the applied set to whichever point the family's own
#: formula used. Getting this wrong is not subtle: the level family misses by
#: 12 % (21,000 lb-in on ``ga6_normal`` case 4).
_PITCH_ARM_AT_THE_AXLE = frozenset(list(range(1, 13)) + list(range(19, 25)))


@pytest.mark.parametrize("example", _WITH_GROUND_CASES)
def test_the_ground_closure_reproduces_landloads_unbalanced_moments(example):
    """**G-6's rotational half** -- the three lines the design note promised (R6-T1).

    The translational gate above is one half of what G-6 wrote down. This is the
    other::

        Iyy.theta_ddot == PITCHP + the G-7a lift term
        Ixx.phi_ddot   == ROLLP        Izz.psi_ddot == YAWP

    and it is the half worth having, because the rotational field is where the
    frame work happens: ``[I]{omega_dot}`` is a moment about the **mass
    centroid** in **body axes** on the **assembled tensor**, while
    ``PITCHP``/``ROLLP``/``YAWP`` are about the **CG** on the **ground line**
    from lever arms and FAR percentages. Every step of that transfer is written
    out here -- centroid to CG, patch to arm point, body axes to ground line --
    so a frame error lands on a named line instead of hiding in a tolerance.

    **The two deliberate departures are carried explicitly, not absorbed.**
    ``_lift_moment_about_cg`` rebuilds G-7a's ``L x W`` along the ground line and
    subtracts it, so if G-7 is ever changed without revisiting this gate the gate
    goes red -- which is exactly what the design note asked for. The patch-to-arm
    move is :data:`_PITCH_ARM_AT_THE_AXLE`.

    **Which frame each line is compared in is LANDLOAD's choice, and they are not
    the same choice** -- this is the gate's real finding, and it is about the
    oracle rather than about the port:

    * ``ROLLP = +-0.83 W x CP`` is built on ``CP``, the CG's height above the
      **contact line**, so the roll line is compared in the contact-line frame
      (``-GRA``) with the side loads left at the tyre;
    * ``YAWP = +-0.83 W x BP`` is built on ``BP``, an **axle** arm resolved
      through ``BETA``, so the yaw line is compared in the case's own ``rho``.

    For every attitude but one those are the same frame, because ``rho == -GRA``.
    In the ground-roll attitude they differ by ``2 x GRA(2)`` -- 9.45 deg on
    ``ga6_normal`` -- because ``LANDLOAD.BAS`` resolves that attitude at
    ``PHIM = +BETA(2)`` where the level and tail-down attitudes use
    ``GAMMA - GRA(1)`` and ``-BETA(3)``. That inconsistency is McMaster's own,
    it is faithfully ported (see
    ``test_the_two_frames_round_trip_through_the_rotation``, which named it and
    declined to adjudicate it), and it is pinned as its own statement in
    :func:`test_the_ground_roll_attitude_is_resolved_against_the_other_sign`.

    **Tolerances, and their causes.** The one-wheel family's ``ROLLP``/``YAWP``
    are ``VMP x TREAD/2`` and ``-DMP x TREAD/2`` -- the tread arm is shared
    geometry, so those lines are identities and are asserted at ``rel_tol
    1e-9`` (measured: 4e-16). Every other line is compared against a lever arm
    the BASIC **truncates to 3 decimals when it prints it** (``LANDLOAD.BAS``
    780-790, ``landing._trunc3``), which is worth up to 2e-4 of the moment, so
    those are bounded at ``1e-4 x W x MAC``. The braked-roll family's pitch
    carries the frame difference above as well and is bounded at ``5e-2 x W x
    MAC`` -- measured 0.6-3.2 % on ``ga6_normal`` and 1e-5 on the regional jet,
    whose ``GRA(2)`` is zero and which therefore cannot see the inconsistency at
    all. Every bound is one-sided and every measured value is quoted, so a drift
    into the slack is visible rather than silent.
    """
    project = _project(example)
    _, reactions = build_landing(project)
    # The effective input, not the entered slice: the gear geometry these arms
    # are built from is resolved onto it (M2R-4), and ``project.landing`` alone
    # has no axle stations at all on either fixture.
    inp = _effective_gear_input(project, project.landing)
    gra = ground_angles(inp)
    radius = {MAIN: inp.main_gear.rolling_radius_in,
              NOSE: inp.nose_gear.rolling_radius_in}
    by_case = {c.case: c for c in reactions}
    cases = [c for c in build_balanced_cases(project) if is_ground(c)]
    assert cases, example

    for case in cases:
        gear = by_case[case.vn_case]
        where = f"{example} {case.case_ref.case_id} (LANDLOAD case {case.vn_case})"
        # The case's own moment scale. Bounds are stated against it rather than
        # against the compared value, because three of the families state a
        # LANDLOAD moment of exactly zero and "0.1 % of nothing" is not a bound.
        scale = case.weight_lb * case.mac
        rho = math.radians(ground_rotation_deg(gear))
        angle = math.radians(gra[attitude_of(case.vn_case)[1]])
        contact_line = -angle
        flip = -1.0 if _is_reflected(case, gear) else 1.0

        # The solved field about the CG, less the G-7a departure: what is left is
        # the moment of the gear reactions alone, which is what LANDLOAD states.
        at_patch = tuple(
            s - lift for s, lift in
            zip(_solved_moment_about_cg(case),
                _lift_moment_about_cg(case, gear, inp.lift_factor)))
        # ... and the same load moved from the tyre to the axle. Both wheels of a
        # leg share the offset (the patch is the rolling radius from the axle
        # along the ground normal), so one cross product per leg is the whole
        # move, and it lands only in pitch until a family carries a side load.
        at_axle = at_patch
        for leg, r in radius.items():
            applied = [ld for ld in case.loads if ld.source == f"gear-{leg}"]
            if not applied:
                continue
            force = tuple(sum(getattr(ld, c) for ld in applied)
                          for c in ("fx", "fy", "fz"))
            offset = (-r * math.sin(angle), 0.0, r * math.cos(angle))
            at_axle = tuple(a + m for a, m in zip(at_axle, _cross(offset, force)))

        pitch_at = (at_axle if case.vn_case in _PITCH_ARM_AT_THE_AXLE else at_patch)
        # 13-18 also carry the ground-roll attitude's frame difference, which no
        # rotation in the check can remove: it is in the direction the reaction
        # is applied, not in the reference the moment is taken about.
        pitch_tol = 1e-4 if case.vn_case in _PITCH_ARM_AT_THE_AXLE else 5e-2
        assert abs(pitch_at[1] - gear.pitchp) <= pitch_tol * scale, (
            f"{where}: PITCHP {pitch_at[1]:,.1f} != {gear.pitchp:,.1f}")

        roll = (at_patch[0] * math.cos(contact_line)
                - at_patch[2] * math.sin(contact_line))
        yaw = at_axle[2] * math.cos(rho) + at_axle[0] * math.sin(rho)
        if case.vn_case in GROUND_ONE_WHEEL_CASES:
            # The tread arm is the assembled model's own geometry, so these two
            # are identities rather than agreements.
            assert math.isclose(roll, flip * gear.rollp, rel_tol=1e-9), (
                f"{where}: ROLLP {roll:,.3f} != {flip * gear.rollp:,.3f}")
            assert math.isclose(yaw, flip * gear.yawp, rel_tol=1e-9), (
                f"{where}: YAWP {yaw:,.3f} != {flip * gear.yawp:,.3f}")
        else:
            assert abs(roll - flip * gear.rollp) <= 1e-4 * scale, (
                f"{where}: ROLLP {roll:,.1f} != {flip * gear.rollp:,.1f}")
            assert abs(yaw - flip * gear.yawp) <= 1e-4 * scale, (
                f"{where}: YAWP {yaw:,.1f} != {flip * gear.yawp:,.1f}")


def test_the_rotational_gates_two_departures_are_not_no_ops():
    """**The rotational gate's negative control.** Both corrections carry content.

    A gate whose corrections are negligible is a gate that would pass with them
    deleted, so the two the rotational line makes are measured here on
    ``ga6_normal`` case 4 -- the level 2-wheel condition, which carries both.

    * the **arm point** (G-12): comparing at the tyre instead of the axle misses
      ``PITCHP`` by 20,961 lb-in, **12.5 %**;
    * the **lift term** (G-7a): 9,787 lb-in, 5.8 % -- small, and exactly the size
      that hides inside a percentage tolerance, which is why G-6 asked for it in
      the line rather than in the slack.
    """
    project = _project("ga6_normal.project.json")
    _, reactions = build_landing(project)
    gear = next(c for c in reactions if c.case == 4)
    inp = _effective_gear_input(project, project.landing)
    case = next(c for c in build_balanced_cases(project)
                if is_ground(c) and c.vn_case == 4)

    lift = _lift_moment_about_cg(case, gear, inp.lift_factor)
    assert math.isclose(lift[1], 9786.7, rel_tol=1e-3)
    assert abs(lift[1]) > 0.05 * abs(gear.pitchp)

    angle = math.radians(ground_angles(inp)[attitude_of(4)[1]])
    r = inp.main_gear.rolling_radius_in
    force = tuple(sum(getattr(ld, c) for ld in case.loads
                      if ld.source == f"gear-{MAIN}") for c in ("fx", "fy", "fz"))
    move = _cross((-r * math.sin(angle), 0.0, r * math.cos(angle)), force)
    assert math.isclose(move[1], 20961.0, rel_tol=1e-3)
    assert abs(move[1]) > 0.1 * abs(gear.pitchp)


@pytest.mark.parametrize("example", sorted(_WITH_GEAR))
def test_the_ground_roll_attitude_is_resolved_against_the_other_sign(example):
    """``rho == -GRA`` in every attitude but the ground-roll one, where it is ``+GRA``.

    The statement of record for what G-6's rotational gate found (R6-T1), pinned
    on every gear fixture rather than left in a docstring. ``rho`` is the angle
    the reaction is rotated through to reach airplane axes, recovered from the
    case's own two resolutions; ``GRA`` is the angle of the line the tyres stand
    on. They are the same rotation seen from the two ends, so ``rho = -GRA`` --
    and it is, in the level attitude (``PHIM = GAMMA - BETA(1)``) and the
    tail-down one (``PHIM = -BETA(3)``), on all five fixtures. The ground-roll
    attitude uses ``PHIM = +BETA(2)`` (``LANDLOAD.BAS``: ``L=13 TO 18:
    PHIM(L)=ATN(.8)*57.3+BETA(2)``, ``L=19 TO 24: PHIM(L)=BETA(2)``), which is
    the other sign.

    The port is faithful to the BASIC on both, so this is not a defect in the
    replication and nothing here is "fixed" -- it is recorded, with its
    consequence measured: on ``ga6_normal`` the 23.485 family's own ``ROLLP`` and
    ``YAWP`` cannot both be reproduced by any single rigid rotation, because they
    are stated 2 x GRA(2) = 9.45 deg apart. On an airplane that sits level
    (``GRA(2) = 0``: the regional jet and both twins) the two signs coincide and
    the question does not arise, which is why only ``ga6_normal`` and the Cessna
    can see it at all.

    **Decision of record (user, 2026-08-15): keep the manual's convention -- this
    is a faithful replication.** No deviation is taken, so this test asserts the
    manual's own signs, ``+GRA`` on the ground-roll attitude included, and is the
    thing that goes red if either ever moves. The reasoning, the exposure and the
    conditions under which the question would resume are recorded under
    "Considered and declined" in ``docs/20_theory/02_approved_corrections.md``,
    which is the register the oracle-deviation policy points at.
    """
    project = _project(example)
    inp = _effective_gear_input(project, project.landing)
    gra = ground_angles(inp)
    _, reactions = build_landing(project)
    seen = set()
    for gear in reactions:
        if gear.case > 24 or not gear.rmp:
            continue
        attitude = attitude_of(gear.case)[1]
        rho = ground_rotation_deg(gear)
        want = gra[attitude] if attitude == 1 else -gra[attitude]
        assert math.isclose(rho, want, rel_tol=1e-9, abs_tol=1e-9), (
            f"{example} case {gear.case}: rho {rho} against GRA {gra[attitude]}")
        seen.add(attitude)
    assert seen == {0, 1, 2}, (example, seen)


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


# --------------------------------------------------------------------------- #
# R6-C2 / R6-C4: the CSV channel meets the load-output contract, in both systems
# --------------------------------------------------------------------------- #
def _parsed_csv(text):
    import csv as _csv
    import io as _io

    reader = _csv.reader(_io.StringIO(text))
    header = next(reader)
    return header, [dict(zip(header, row)) for row in reader]


def test_the_csv_states_its_units_its_factor_and_its_wheel():
    """**R6-C2 + R6-C4's pin, Imperial.** The file states its own column units.

    Every load column carries the ``-ULT`` marker in its header, ``SF`` is the
    last column and states the factor per case, the weights (inputs, not
    factored loads) carry the plain force unit -- and the ``Wheel`` column says
    which wheel a ``main`` row describes (the starboard one of the pair; the
    port twin is the mirror), which before R6-C4 was said only in a code
    comment. Before R6-C2 none of this was in the file: the ULTIMATE basis
    lived solely in the methods stamp above the table.
    """
    from sloads.export.sbeam_bridge import gear_report_csv

    header, rows = _parsed_csv(
        gear_report_csv(_project("ga6_normal.project.json")))
    for label in ("Ground-line V (lbs-ULT)", "Datum Fz (lbs-ULT)",
                  "Transfer Mx (lb-in-ULT)", "Leg inertia Fz (lbs-ULT)",
                  "Net Fz above trunnion (lbs-ULT)", "Stroke (in)",
                  "Patch X (in)", "Design weight (lb)", "Leg weight (lb)"):
        assert label in header, label
    assert header[-1] == "SF"
    assert rows
    # Ground loads are LIMIT by 23.471, so the governing table's factor is 1.5
    # (23.303) -- stated in-band on every row, the F-R1 rule.
    assert all(r["SF"] == "1.5" for r in rows)
    assert {r["Wheel"] for r in rows if r["Leg"] == MAIN} == {"starboard"}
    assert {r["Wheel"] for r in rows if r["Leg"] == NOSE} == {"centreline"}


def test_the_si_channel_states_si_units_and_converted_values():
    """**R6-C2's SI pin -- the assertion whose absence let the defect ship.**

    Before it, the SI file showed ``4.325464E+01`` (a millimetre value) under a
    hard-coded ``Stroke (in)`` header, because no test read the SI gear CSV at
    all. Header labels plus one converted value per dimension, so the family
    cannot regress: mm is exactly 25.4 x in, N is 4.448222 x lb, and the
    moment column carries the solver channel's ``Nmm-ULT``.
    """
    from sloads.export.sbeam_bridge import gear_report_csv
    from sloads.units import UnitSystem

    project = _project("ga6_normal.project.json")
    _, imperial = _parsed_csv(gear_report_csv(project))
    si_header, si = _parsed_csv(
        gear_report_csv(project, system=UnitSystem.SI))
    for label in ("Stroke (mm)", "Ground-line V (N-ULT)",
                  "Transfer Mx (Nmm-ULT)", "Design weight (N)"):
        assert label in si_header, label
    assert len(si) == len(imperial)
    a, b = imperial[0], si[0]
    assert math.isclose(float(b["Stroke (mm)"]),
                        float(a["Stroke (in)"]) * 25.4, rel_tol=1e-5)
    assert math.isclose(float(b["Ground-line V (N-ULT)"]),
                        float(a["Ground-line V (lbs-ULT)"]) * 4.448222,
                        rel_tol=1e-5)
    assert math.isclose(float(b["Transfer Mx (Nmm-ULT)"]),
                        float(a["Transfer Mx (lb-in-ULT)"]) * 4.448222 * 25.4,
                        rel_tol=1e-5)


#: The worked example of ``docs/20_theory/balanced_cases.md`` §9.5, figure for
#: figure. Three families on ``ga6_normal``: a level landing that carries lift
#: (23.479), a ground-handling case that carries none (23.493), and the handed
#: side condition (23.485). Keyed by LANDLOAD case number.
#:
#: The document's own contract is that **every number quoted in it is pinned in
#: CI** -- §10 maps figure to gate -- and the gates above prove *relationships*
#: (an identity against LANDLOAD, a closure to machine precision) which hold just
#: as well if every figure in the table moves together. This is the other kind of
#: gate: the values a reader is shown. A physics change that moves them is not
#: forbidden, it is required to update the document in the same session.
_WORKED_EXAMPLE = {
    4: dict(label="2-wheel level landing (nose clear)", weight_lb=3230.0,
            rho=-4.057, gear_fx=2042.3, gear_fz=8240.1, lift_lb=2154.4,
            lift_fx=-152.4, fx=1889.9, fz=10389.1, my=-179232.0,
            nz=3.2165, nx=0.5851, ny=0.0, q_dot=-1.925e-2,
            nvp=3.1670, ndp=0.8112, lift_my=9787.0, lift_pct=1.360),
    13: dict(label="braked roll (nose down)", weight_lb=3400.0,
             rho=4.724, gear_fx=2611.5, gear_fz=4321.6, lift_lb=0.0,
             lift_fx=0.0, fx=2611.5, fz=4321.6, my=-757.1,
             nz=1.2711, nx=0.7681, ny=0.0, q_dot=-8.016e-5,
             nvp=1.3300, ndp=0.6608, lift_my=0.0, lift_pct=0.0),
    19: dict(label="side load", weight_lb=3400.0,
             rho=4.724, gear_fx=372.4, gear_fz=4506.6, lift_lb=0.0,
             lift_fx=0.0, fx=372.4, fz=4506.6, my=-70654.5,
             nz=1.3255, nx=0.1095, ny=-0.8300, q_dot=-7.481e-3,
             nvp=1.3300, ndp=0.0, lift_my=0.0, lift_pct=0.0),
}


def test_the_ground_worked_example_is_pinned():
    """§9.5 of the theory doc, figure for figure (R6-D7).

    Also the three statements the prose makes *about* the table, asserted rather
    than left as claims: the applied set at ``n_z = 0`` is gear + lift and
    nothing else (so the pre-closure resultant is the whole applied load, which
    is why ``RESIDUAL_GATE`` does not apply); the solved field rotated to the
    ground line is LANDLOAD's own print; and the side case's twin carries the
    mirrored ``n_y``.
    """
    project = _project("ga6_normal.project.json")
    _, reactions = build_landing(project)
    by_case = {c.case: c for c in reactions}
    cases = {}
    for case in build_balanced_cases(project):
        if is_ground(case):
            cases.setdefault(case.vn_case, []).append(case)

    for number, want in _WORKED_EXAMPLE.items():
        case = cases[number][0]
        gear = by_case[number]
        where = f"LANDLOAD case {number} ({case.case_ref.case_id})"
        assert case.label == want["label"], where
        assert math.isclose(case.weight_lb, want["weight_lb"], rel_tol=1e-9), where
        assert math.isclose(ground_rotation_deg(gear), want["rho"],
                            abs_tol=5e-4), f"{where}: rho"

        # The applied set: gear reactions plus (on the landing families) lift,
        # and no third contributor -- the inertia sets are at zero load factor.
        applied = {"gear": (0.0, 0.0), "lift": (0.0, 0.0)}
        other = 0.0
        for load in case.loads:
            if load.source.startswith("gear-"):
                key = "gear"
            elif load.source == "ground-lift":
                key = "lift"
            elif load.source.startswith("closure-"):
                continue
            else:
                other += abs(load.fx) + abs(load.fy) + abs(load.fz)
                continue
            fx, fz = applied[key]
            applied[key] = (fx + load.fx, fz + load.fz)
        assert other == 0.0, f"{where}: inertia set carries force at n_z = 0"
        assert math.isclose(applied["gear"][0], want["gear_fx"], abs_tol=0.05), where
        assert math.isclose(applied["gear"][1], want["gear_fz"], abs_tol=0.05), where
        assert math.isclose(math.hypot(*applied["lift"]), want["lift_lb"],
                            abs_tol=0.05), f"{where}: lift"
        assert math.isclose(applied["lift"][0], want["lift_fx"], abs_tol=0.05), where

        for name, value in (("fx", case.residual_fx), ("fz", case.residual_fz),
                            ("my", case.residual_my)):
            assert math.isclose(value, want[name], rel_tol=5e-6, abs_tol=0.05), (
                f"{where}: pre-closure {name} {value}")
        for name, value in (("nz", case.delta_n), ("nx", case.delta_nx),
                            ("ny", case.delta_ny)):
            assert math.isclose(value, want[name], abs_tol=5e-5), (
                f"{where}: solved {name} {value}")
        assert math.isclose(case.q_dot, want["q_dot"], rel_tol=1e-3), where

        nvp, ndp = to_ground_line(case.delta_n, case.delta_nx,
                                  ground_rotation_deg(gear))
        assert math.isclose(nvp, want["nvp"], abs_tol=5e-5), f"{where}: NVP"
        assert math.isclose(ndp, want["ndp"], abs_tol=5e-5), f"{where}: NDP"
        # ...and the quoted "LANDLOAD prints" row is LANDLOAD's, not a copy of
        # the rotated value: read from the reaction table itself.
        assert math.isclose(gear.nvp, want["nvp"], abs_tol=5e-5), where
        assert math.isclose(gear.ndp, want["ndp"], abs_tol=5e-5), where

        lift_my = _lift_moment_about_cg(case, gear, project.landing.lift_factor)[1]
        assert math.isclose(lift_my, want["lift_my"], rel_tol=1e-3,
                            abs_tol=0.5), f"{where}: G-7a lift moment"
        if want["lift_pct"]:
            pct = 100.0 * lift_my / (abs(case.delta_n * case.weight_lb) * case.mac)
            assert math.isclose(pct, want["lift_pct"], abs_tol=5e-4), where

    # §9.4's two lift-moment figures: the level family's and the tail-down one's,
    # the pitching moment G-7a's distributed lift leaves where LANDLOAD nets it
    # at the CG. The level figure rides the table above; this is its sibling.
    tail_down = cases[3][0]
    pct = 100.0 * _lift_moment_about_cg(
        tail_down, by_case[3], project.landing.lift_factor)[1] / (
            abs(tail_down.delta_n * tail_down.weight_lb) * tail_down.mac)
    assert math.isclose(pct, -2.383, abs_tol=5e-4), pct

    # The side family's twin, quoted in the prose after the table.
    twin = cases[19][1]
    assert math.isclose(twin.delta_ny, -_WORKED_EXAMPLE[19]["ny"], abs_tol=5e-5)
    assert math.isclose(twin.p_dot, -cases[19][0].p_dot, rel_tol=1e-9)
    assert math.isclose(twin.r_dot, -cases[19][0].r_dot, rel_tol=1e-9)


def test_the_worked_examples_contact_patch_is_where_the_prose_says():
    """§9's opening lever arms: 41 in below the CG waterline, ±57.25 in out.

    The sentence exists to argue that a ground case is irreducibly
    three-dimensional, so the two numbers carrying that argument are pinned like
    any other quoted figure.
    """
    project = _project("ga6_normal.project.json")
    gear = {c.case: c for c in gear_case_loads(project)}[13]
    case = next(c for c in build_balanced_cases(project)
                if is_ground(c) and c.vn_case == 13)
    leg = next(lg for lg in gear.legs if lg.leg == MAIN)
    assert math.isclose(leg.patch[1], 57.25, abs_tol=5e-3)
    assert math.isclose(case.cg_z - leg.patch[2], 41.0, abs_tol=0.5)
    # ...and the per-wheel figures the same sentence quotes, read from the
    # **assembled** case rather than from ``applied_wheels`` directly: what the
    # sentence is about is the load the deck carries at each patch, and the
    # 23.485 family's side load is split across the pair by G-8's own rule.
    main = [ld for ld in case.loads if ld.source == "gear-main"]
    assert len(main) == 2
    assert math.isclose(main[0].fz, 1307.0, abs_tol=0.5)
    assert math.isclose(main[0].fx, 1235.0, abs_tol=0.5)
    side = next(c for c in build_balanced_cases(project)
                if is_ground(c) and c.vn_case == 19)
    side_main = [ld for ld in side.loads if ld.source == "gear-main"]
    assert [round(ld.fy) for ld in side_main] == [-1700, -1122]
    assert all(math.isclose(ld.fz, 2253.0, abs_tol=0.5) for ld in side_main)


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
