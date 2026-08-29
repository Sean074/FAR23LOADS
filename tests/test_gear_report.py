"""The gear free body and the assembled ground cases -- step 10 piece 3.

Decisions **G-2**, **G-6**, **G-7/G-7a**, **G-8**, **G-12/G-12a** and **G-13** of
``docs/40_history/23_step10_ground_cases_plan.md``.

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

import pytest

from sloads import io
from sloads.export.balanced_deck import (
    BALANCED_GEAR_BASE,
    balanced_deck,
    deck_nodes,
)
from sloads.export.sbeam_bridge import gear_report_rows
from sloads.gear_loads import (
    AXLE,
    GROUND_CONTACT,
    MAIN,
    NOSE,
    application_point_of,
    applied_wheels,
    attitude_of,
    gear_case_loads,
    ground_rotation_deg,
    to_ground_line,
    transfer_couple,
)
from sloads.models import MissingInputError
from sloads.modules.balance import (
    GROUND_LIFT_CASES,
    GROUND_ONE_WHEEL_CASES,
    GROUND_SIDE_CASES,
    build_balanced_cases,
    is_ground,
    resultant6,
)

# ``gear_geometry`` is the module's own resolver for the gear geometry (note 33,
# DS-2), and the rotational gate needs the same axle stations the reactions were
# computed at. Reaching for it is the alternative to keeping a second copy of that
# resolution beside the test.
from sloads.modules.landing import (
    build_landing,
    gear_geometry,
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

    LANDLOAD applies each reaction at the point its own printed column names --
    the axle on the landing attitudes, the tyre contact patch on the handling
    ones (design note 39 AP-1) -- and the transfer to the attachment node is
    *ours*, which is exactly why it is policed. Force plus the lever-arm couple
    at the node has the same resultant about **every** reference as the force
    alone at that point, so this is a property of the construction rather than an
    approximation, and it is gated exactly (``rel_tol 1e-12``) rather than to a
    tolerance.

    It is asserted from ``leg.point``, the applied point, and **not** from
    ``leg.patch``: reading the patch is what this test did until 2026-08-29, and
    it passed all the way through -- an exact transfer from the wrong point is
    still exact, which is the whole reason #139 needed an external witness
    (``PITCHP``) rather than an internal one.

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
            px, py, pz = leg.point
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
    (-22 %). The side family: **0 lb ground-line drag against -186 lb** in the
    airplane datum. If these ever swap, a deck is applying the gear reaction in
    the wrong frame -- which parses, solves, and is wrong by a fifth.

    The side value is **negative** -- the body-frame drag acts *forward* -- and
    that sign is the whole physical claim of design note 38's GF-1: the
    ground-line load there is purely normal, so the entire body-frame drag
    component *is* the rotation. It read +186 until 2026-08-29 (approved
    deviation, register ``02_approved_corrections.md``); nose-up geometry demands
    forward, and aft was the wrong-signed ``BETA(2)`` showing through.
    """
    cases = {c.case: c for c in gear_case_loads(_project("ga6_normal.project.json"))}
    level = next(leg for leg in cases[1].legs if leg.leg == MAIN)
    assert math.isclose(level.ground_line[1], 1020.2, abs_tol=0.5)
    assert math.isclose(level.airplane[0], 795.2, abs_tol=0.5)
    side = next(leg for leg in cases[19].legs if leg.leg == MAIN)
    assert side.ground_line[1] == 0.0
    assert math.isclose(side.airplane[0], -186.2, abs_tol=0.5)


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


#: **Withdrawn 2026-08-29 (design note 39, #139).** This set used to move the
#: applied load from the tyre to the axle *inside the gate* on cases 1-12 and
#: 19-24, because "the family's own formula" measured its arm there. It was
#: right about the arithmetic and wrong about what it meant: the assembled case
#: applied every reaction at the contact patch, LANDLOAD applies the landing
#: attitudes at the **axle** -- its own printed column -- and the 12 % the
#: comment below recorded as a bookkeeping move between two conventions was a
#: defect in the deck's lever arm. The move now lives in
#: ``gear_loads.application_point``, and the pitch line compares **where the
#: load is applied**, with no correction of its own (G-AP-1).
#:
#: *Kept verbatim as the thing that was believed:* "The families whose PITCHP is
#: mult x RMP x BP -- one resultant on one arm, and BP is measured to the axle.
#: The braked-roll families 13-18 are the exception: their -2(VMP x BP + DMP x
#: CP) puts the drag arm CP on the ground line, where the tyre is. The assembled
#: case applies every reaction at the contact patch (G-2/G-12), so the gate moves
#: the applied set to whichever point the family's own formula used. Getting this
#: wrong is not subtle: the level family misses by 12 % (21,000 lb-in on
#: ga6_normal case 4)."


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

    Those are the same frame in every attitude, because ``rho == -GRA``.
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
    # Resolved from ``geometry.landing_gear``, its one stored home (note 33): the
    # landing slice carries no axle stations at all, on any fixture.
    gear_geom = gear_geometry(project)
    gra = ground_angles(project.landing, gear_geom)
    radius = {MAIN: gear_geom.main_gear.rolling_radius_in,
              NOSE: gear_geom.nose_gear.rolling_radius_in}
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
        # the moment of the gear reactions alone, which is what LANDLOAD states,
        # taken about **the point the case applies them at** (design note 39
        # AP-1: the axle on 1-12 and 25/26/28/29/31/32, the tyre on the rest).
        # The gate makes no arm correction of its own any more -- the one it used
        # to make was the defect, and it now lives in the code.
        at_applied = tuple(
            s - lift for s, lift in
            zip(_solved_moment_about_cg(case),
                _lift_moment_about_cg(case, gear, project.landing.lift_factor)))
        # The same load at the *other* point, for the two lines whose LANDLOAD
        # formula is built on the other one. Both wheels of a leg share the
        # offset (the patch is the rolling radius from the axle along the ground
        # normal), so one cross product per leg is the whole move, and it lands
        # only in pitch until a family carries a side load.
        applied_at_tyre = application_point_of(case.vn_case) == GROUND_CONTACT
        at_axle, at_tyre = at_applied, at_applied
        for leg, r in radius.items():
            applied = [ld for ld in case.loads if ld.source == f"gear-{leg}"]
            if not applied:
                continue
            force = tuple(sum(getattr(ld, c) for ld in applied)
                          for c in ("fx", "fy", "fz"))
            offset = (-r * math.sin(angle), 0.0, r * math.cos(angle))
            move = _cross(offset, force)
            if applied_at_tyre:
                at_axle = tuple(a + m for a, m in zip(at_axle, move))
            else:
                at_tyre = tuple(a - m for a, m in zip(at_tyre, move))

        # **G-AP-1.** One bound, every family, no per-family arm move and no
        # per-family slack: 13-18's old 5e-2 carried the ground-roll attitude's
        # wrong-way rotation (#133, landed 2026-08-29) and 1-12's arm move
        # carried #139, and with both fixed at their origins every case closes on
        # the same 1e-4 the truncated-arm families always needed.
        assert abs(at_applied[1] - gear.pitchp) <= 1e-4 * scale, (
            f"{where}: PITCHP {at_applied[1]:,.1f} != {gear.pitchp:,.1f}")

        roll = (at_tyre[0] * math.cos(contact_line)
                - at_tyre[2] * math.sin(contact_line))
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

    * the **arm point** (design note 39 AP-1): applying the level attitude at the
      tyre instead of the axle misses ``PITCHP`` by 20,961 lb-in, **12.5 %**.
      Until 2026-08-29 that was a correction the *gate* made and the code did
      not, and this line measured the correction; it now measures the **defect**
      #139 fixed, from the same arithmetic and the same number. A control that
      keeps firing after the thing it controls moves into the code is the one
      worth keeping;
    * the **lift term** (G-7a): 9,787 lb-in, 5.8 % -- small, and exactly the size
      that hides inside a percentage tolerance, which is why G-6 asked for it in
      the line rather than in the slack.
    """
    project = _project("ga6_normal.project.json")
    _, reactions = build_landing(project)
    gear = next(c for c in reactions if c.case == 4)
    gear_geom = gear_geometry(project)
    case = next(c for c in build_balanced_cases(project)
                if is_ground(c) and c.vn_case == 4)

    lift = _lift_moment_about_cg(case, gear, project.landing.lift_factor)
    assert math.isclose(lift[1], 9786.7, rel_tol=1e-3)
    assert abs(lift[1]) > 0.05 * abs(gear.pitchp)

    angle = math.radians(
        ground_angles(project.landing, gear_geom)[attitude_of(4)[1]])
    r = gear_geom.main_gear.rolling_radius_in
    force = tuple(sum(getattr(ld, c) for ld in case.loads
                      if ld.source == f"gear-{MAIN}") for c in ("fx", "fy", "fz"))
    move = _cross((-r * math.sin(angle), 0.0, r * math.cos(angle)), force)
    assert math.isclose(move[1], 20961.0, rel_tol=1e-3)
    assert abs(move[1]) > 0.1 * abs(gear.pitchp)


@pytest.mark.parametrize("example", sorted(_WITH_GEAR))
def test_rho_is_minus_the_ground_angle_in_every_attitude(example):
    """``rho == -GRA(attitude)``, exactly, on every case of every gear fixture.

    ``rho`` is the angle the reaction is rotated through to reach airplane axes,
    recovered from the case's own two resolutions; ``GRA`` is the angle of the
    line the tyres stand on. They are the same rotation seen from the two ends,
    so ``rho = -GRA`` -- in every attitude, with no exception.

    **This test was flipped, not written, on 2026-08-29** (design note 38 GF-4).
    It previously asserted the opposite for the ground-roll attitude, under the
    name ``test_the_ground_roll_attitude_is_resolved_against_the_other_sign``,
    and recorded a decision of 2026-08-15 to keep the manual's convention as a
    faithful replication. That decision's own text named legible printed output
    as the condition under which it would resume; Appendix A's braked-roll
    construction figure (p235) is that output, and it prints lever arms of
    77.052 / 17.760 / 94.811 where the p230 *table* -- program output -- prints
    69.886 / 23.260 / 93.147. ``LANDLOAD.BAS`` carries the wrong sign in
    ``BETA(2)``/``BETA(3)``; attitude 3 negates it back at both its use sites and
    so came out right, attitude 2 at neither. The register entry that supersedes
    the declined one is in ``docs/20_theory/02_approved_corrections.md``.

    Why this gate exists at all rather than G-6: G-6 recovers its reference from
    the very resolutions it checks, so it is self-consistent by construction and
    structurally cannot see a sign error. This one goes to ``ground_angles``
    directly. Its assumption, stated so it is not inherited silently: the
    nose-up sense of ``GRA`` is derived on **tricycle** geometry, the only
    arrangement the suite models -- a tail-wheel configuration would re-open the
    derivation, not inherit it.
    """
    project = _project(example)
    gra = ground_angles(project.landing, gear_geometry(project))
    _, reactions = build_landing(project)
    seen = set()
    for gear in reactions:
        if gear.case > 24 or not gear.rmp:
            continue
        attitude = attitude_of(gear.case)[1]
        rho = ground_rotation_deg(gear)
        want = -gra[attitude]
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
        for name, value in zip(["Fx", "Fy", "Fz", "Mx", "My", "Mz"], components):
            bound = scale * (1e-6 if name.startswith("F") else case.mac * 1e-6)
            assert abs(value) < max(bound, 1e-6), (
                f"{example} {case.case_ref.case_id}: {name} = {value:.6g}")


def test_the_static_contact_patch_breaks_the_level_landing_gate():
    """**G-13's second negative control.**

    Targets G-12's per-attitude geometry, which G-13 identifies as otherwise the
    least-guarded new decision in the note. Compute a level-landing case at the
    **static** axle instead of the compressed one and the closed-form factor gate
    must go red -- and it does, because the applied point moves 3.70 in in ``z``
    and 0.40 in in ``x``, which changes the lever arms the moment balance is
    solved on.

    It perturbs ``point``, the point the reaction is applied at (design note 39
    AP-1), which on this level-landing case is the **axle**. It perturbed
    ``patch`` until 2026-08-29, when the patch stopped being the transfer point
    on cases 1-12 -- at which moment this control silently stopped being able to
    fire. That is the failure mode a negative control exists to catch in
    *itself*, so it is now anchored to the same attribute the transfer reads.

    Asserted on the moment, not on ``NVP``: the vertical force factor is
    unchanged by moving the point (the same force still acts), so a control that
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

    # The same reaction, transferred from the WRONG attitude's applied point --
    # the static axle where this case is computed at the compressed one.
    from dataclasses import replace as _replace
    static = gear_geometry(project).main_gear.axle_static
    wrong_point = (static[0], leg.point[1], static[1])
    assert not math.isclose(wrong_point[0], leg.point[0]), "the two axles coincide"
    broken = applied_wheels([_replace(x, point=wrong_point,
                                      couple=transfer_couple(wrong_point, x.node,
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
    # Case 4 moved on 2026-08-29 with the application-point correction (design
    # note 39 AP-1, #139): the level attitude is applied at the **axle**, where
    # it was transferred from the tyre. Only ``my`` and ``q_dot`` move -- the
    # forces are LANDLOAD's own and are untouched, which is why ``nz``/``nx``
    # and the rotated ``NVP``/``NDP`` are the same figures as before. The
    # residual falls to within 1.1 lb-in of LANDLOAD's own PITCHP once G-7a's
    # lift moment is allowed for (-158,271.3 - 9,786.6 vs -168,056.9), against
    # -20,961.8 at the old point.
    4: dict(label="2-wheel level landing (nose clear)", weight_lb=3230.0,
            rho=-4.057, gear_fx=2042.3, gear_fz=8240.1, lift_lb=2154.4,
            lift_fx=-152.4, fx=1889.9, fz=10389.1, my=-158271.3,
            nz=3.2165, nx=0.5851, ny=0.0, q_dot=-1.701e-2,
            nvp=3.1670, ndp=0.8112, lift_my=9787.0, lift_pct=1.360),
    # Cases 13 and 19 moved on 2026-08-29 with the BETA(2) correction (design
    # note 38 GF-1/GF-2', register 02_approved_corrections.md). The headline is
    # ``my``: case 13's pre-closure residual pitching moment falls from -757.1
    # to **-0.7 lb-in**, and its q_dot from -8.0e-5 to -7.4e-8. That is the
    # independent confirmation of the correction -- the residual is measured
    # against LANDLOAD's own unbalanced moments, not against anything the fix
    # touches, and the wrong-signed lever arms were what it had been reading.
    13: dict(label="braked roll (nose down)", weight_lb=3400.0,
             rho=-4.724, gear_fx=2038.5, gear_fz=4705.9, lift_lb=0.0,
             lift_fx=0.0, fx=2038.5, fz=4705.9, my=-0.7,
             nz=1.3841, nx=0.5996, ny=0.0, q_dot=-7.445e-8,
             nvp=1.3300, ndp=0.7115, lift_my=0.0, lift_pct=0.0),
    19: dict(label="side load", weight_lb=3400.0,
             rho=-4.724, gear_fx=-372.4, gear_fz=4506.6, lift_lb=0.0,
             lift_fx=0.0, fx=-372.4, fz=4506.6, my=-39838.1,
             nz=1.3255, nx=-0.1095, ny=-0.8300, q_dot=-4.218e-3,
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
    # Case 13's airplane-datum pair. p232 prints 1307 / 1235; these are the
    # approved-deviation values (design note 38 GF-1/GF-2', 2026-08-29 --
    # register 02_approved_corrections.md), the same resultant resolved through
    # the corrected PHIM = atan(0.8) - GRA(2) = 33.936 deg rather than 43.387.
    assert math.isclose(main[0].fz, 1606.5, abs_tol=0.5)
    assert math.isclose(main[0].fx, 1081.0, abs_tol=0.5)
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
            except Exception as exc:
                failures += 1
                print(f"FAIL {name}{f'[{args}]' if args else ''}: {exc}")
    print("FAILURES:" if failures else "OK", failures or "")
    sys.exit(1 if failures else 0)


#: **The printed column, transcribed** (Appendix A p231/p233 head the ground-line
#: and unbalanced-moment tables; p232 heads the airplane-datum one). Rendered at
#: 200 dpi and read cell by cell on 2026-08-29 -- the column the OCR lost, and the
#: statement design note 39 AP-1 rests on. Written out case by case rather than as
#: ranges so that it is a **transcription** and not a restatement of the code's own
#: rule: a range expression here would be the same construction ``gear_loads``
#: makes, and two copies of one rule cannot disagree.
_PRINTED_APPLICATION_POINT = {
    1: "CENTER OF EACH WHEEL", 2: "CENTER OF EACH WHEEL", 3: "CENTER OF EACH WHEEL",
    4: "CENTER OF EACH WHEEL", 5: "CENTER OF EACH WHEEL", 6: "CENTER OF EACH WHEEL",
    7: "CENTER OF EACH WHEEL", 8: "CENTER OF EACH WHEEL", 9: "CENTER OF EACH WHEEL",
    10: "CENTER OF EACH WHEEL", 11: "CENTER OF EACH WHEEL", 12: "CENTER OF EACH WHEEL",
    13: "GROUND CONTACT POINT", 14: "GROUND CONTACT POINT", 15: "GROUND CONTACT POINT",
    16: "GROUND CONTACT POINT", 17: "GROUND CONTACT POINT", 18: "GROUND CONTACT POINT",
    19: "GROUND CONTACT POINT", 20: "GROUND CONTACT POINT", 21: "GROUND CONTACT POINT",
    22: "GROUND CONTACT POINT", 23: "GROUND CONTACT POINT", 24: "GROUND CONTACT POINT",
    25: "CL AXLE", 26: "CL AXLE", 27: "GROUND",
    28: "CL AXLE", 29: "CL AXLE", 30: "GROUND",
    31: "CL AXLE", 32: "CL AXLE", 33: "GROUND",
}

#: How the manual's two spellings of each point map onto this package's two
#: (``AXLE`` / ``GROUND_CONTACT``). "CL AXLE" is the axle on the centreline --
#: the 23.499 family is nose-only, so its axle *is* on the centreline and the
#: extra word is a statement about the wheel, not about a third point.
_PRINTED_TO_OWNER = {
    "CENTER OF EACH WHEEL": AXLE, "CL AXLE": AXLE,
    "GROUND CONTACT POINT": GROUND_CONTACT, "GROUND": GROUND_CONTACT,
}


def test_the_application_point_is_the_manuals_printed_column():
    """**G-AP-2** -- every case's point matches Appendix A's own column.

    Asserted against :data:`_PRINTED_APPLICATION_POINT`, a transcription, and
    never against the code that builds the answer. This is the gate that makes
    AP-1 a reading of the manual rather than a preference: the point is a
    physical fact about where the load enters the structure (spin-up drag is
    reacted at the bearing, braking torque is internal to the wheel), and the
    manual states it per family.
    """
    assert len(_PRINTED_APPLICATION_POINT) == 33
    for case, printed in _PRINTED_APPLICATION_POINT.items():
        assert application_point_of(case) == _PRINTED_TO_OWNER[printed], (
            f"case {case}: printed {printed!r}")
    for outside in (0, 34, -1):
        with pytest.raises(ValueError):
            application_point_of(outside)


def test_the_application_point_is_built_in_exactly_one_place():
    """**G-AP-3** -- one owner for the point, structurally, not by convention.

    A load and its point are one statement (design note 38 §1.14), and the way
    they come apart is a second construction of the point somewhere downstream:
    that is exactly how the deck ended up transferring from the patch while the
    manual applied at the axle, with an exact transfer and a green suite on both
    sides of the disagreement.

    So two things are asserted about the package's own source. Every **gear**
    ``transfer_couple`` call transfers from the owner's ``point`` and never from
    a patch; and ``contact_patch``/``_axle`` -- the two constructions
    :func:`application_point` chooses between -- are called nowhere outside
    ``gear_loads`` itself. Anything that needs a point reads
    ``application_point`` or a ``GearLegLoad``/``AppliedWheel`` field.

    The export channel's movers call the same rule on points that are not gear
    points at all (concentrated-mass offsets, LRA node routing), so the call-site
    half is scoped to ``gear_loads``. The *rule* itself is now singular: it was
    implemented twice, identically, each copy's docstring claiming to be note 24
    R-11's single owner, and ``export/coordinates.py`` re-exports this one since
    2026-08-29.
    """
    import pathlib
    import re

    package = pathlib.Path(__file__).resolve().parent.parent / "sloads"
    calls = re.compile(r"transfer_couple\(\s*([A-Za-z_][A-Za-z_0-9.]*)")
    builders = re.compile(r"(?<![A-Za-z_.])(contact_patch|_axle)\(")
    offenders = []
    for path in sorted(package.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(package.parent)
        if path.name == "gear_loads.py":
            for arg in calls.findall(text):
                if arg.split(".")[-1] not in ("point", "node"):
                    offenders.append(
                        f"{rel}: transfer_couple({arg}, ...) -- not the owner's point")
        else:
            for builder in builders.findall(text):
                offenders.append(f"{rel}: builds a point with {builder}()")
    # One implementation of the rule, not one per layer (#139).
    from sloads.export.coordinates import transfer_couple as exported
    from sloads.gear_loads import transfer_couple as owned
    assert exported is owned, "the transfer rule is implemented twice again"
    assert not offenders, "a second application point exists:\n  " + "\n  ".join(offenders)
