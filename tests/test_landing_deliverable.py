"""The delivered ground load: three wheels, a point each, and a named frame.

Design note 38 GF-6/GF-7 (#134), gates G-GF-6 and G-GF-7. What the replication
shipped before this was a magnitude in an unnamed frame: LANDLOAD prints its
whole matrix twice -- once with respect to the ground line, once with respect to
the airplane datum -- and ``run()`` emitted the first set only, with no
application point, no attitude and no frame label, while the export deck consumed
the second. A stress model consumes a force **and a point**; a magnitude with an
unnamed frame is not a load.

The gates here are, in order:

1. **Three legs on every case of every bundled example** -- nose, left main,
   right main, an unloaded gear at zero rather than omitted.
2. **The point is Appendix A's printed column**, per family (design note 39).
3. **The delivered forces sum to the page.** The three wheels' airplane-datum
   components reproduce p232's own printed force cells, and the NR/NV/ND load
   factors are that sum over the weight plus the rotated lift -- derived from the
   page and the manual's own formula, never from the module under test.
4. **The CSV/text split**, both ways: the delivered CSV carries the body frame
   only, and the text report keeps both sets.
5. **One caption owner** for the frame words, in both GUIs.

Reference: LANDLOAD.BAS (Appendix C p468) lines 5140/5230 (the two frame
banners) and the NV/ND/NNS loops; Appendix A p231 (FUSELAGE AXIS ANGLE, the
point-of-load column), p232 (the airplane-datum table and its NR/NV/ND columns,
transcribed 2026-08-29 -- design note 38 §1.13), p233.
"""

import csv as _csv
import io as _io
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io, registry
from sloads.frames import AIRPLANE_DATUM, FRAMES, GROUND_LINE, caption, is_report_only
from sloads.gear_loads import (
    AXLE,
    GROUND_CONTACT,
    MAIN_LEFT,
    MAIN_RIGHT,
    NOSE,
    POINTS,
    application_point_of,
    delivered_gear_legs,
    gear_case_loads,
)
from sloads.models import MissingInputError
from sloads.modules.landing import (
    GROUND_LIFT_CASES,
    GROUND_ONE_WHEEL_CASES,
    attitude_of,
    build_landing,
    ground_angles,
    side_partner,
)
from sloads.report import module_text_report

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXAMPLES = os.path.join(os.path.dirname(_HERE), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")

#: Every bundled example that has gear geometry. ``concept_heavy`` has neither a
#: ``landing`` slice nor gear geometry and produces no gear report at all.
_FIXTURES = ("ga6_normal", "baron_58", "cessna_210", "atr42_100", "dhc8_dash8",
             "concept_regional_jet")

REL = 1e-3          # the project's oracle band


def _project(name):
    return io.load_project(os.path.join(_EXAMPLES, f"{name}.project.json"))


def _legs(project):
    return delivered_gear_legs(gear_case_loads(project))


# --------------------------------------------------------------------------- #
# 1. Three legs, always
# --------------------------------------------------------------------------- #
def test_every_case_of_every_example_carries_all_three_legs():
    """G-GF-6: nose, left main, right main -- on all 33 cases, everywhere.

    Including the ones a family lifts clear: the 23.481 tail-down and 23.493
    braked families put no load on the nose wheel, the 23.483 one-wheel family
    none on the port main, and the 23.499 supplementary-nose family none on
    either main. Those wheels are emitted at **zero**, with their point and their
    reference node still stated. Which gears a case leaves unloaded is a fact
    about the case; omitting them makes the reader reconstruct the family's rule
    from the case number, which is exactly what a delivered load should not
    require.
    """
    for name in _FIXTURES:
        legs = _legs(_project(name))
        assert sorted(legs) == list(range(1, 34)), name
        for case, three in sorted(legs.items()):
            assert [leg.name for leg in three] == [NOSE, MAIN_LEFT, MAIN_RIGHT], \
                f"{name} case {case}"
            # The two mains are mirror images in y -- of each other, and of the
            # nodes they deliver to.
            left, right = three[1], three[2]
            assert math.isclose(left.point[1], -right.point[1], abs_tol=1e-9)
            assert math.isclose(left.node[1], -right.node[1], abs_tol=1e-9)
            for leg in three:
                assert len(leg.force) == 3 and len(leg.point) == 3
                assert leg.strut_state in ("compressed", "static")


def test_the_unloaded_wheels_are_the_families_that_should_be_unloaded():
    """The zeros are not incidental: each one is the regulation's own statement.

    A guard that only counted three legs would pass if every leg were zero. This
    names which wheel each family lifts, so a case that quietly stops carrying a
    reaction fails here rather than shipping a deck with a missing wheel.
    """
    legs = _legs(_project("ga6_normal"))
    for case, three in sorted(legs.items()):
        nose, left, right = three
        if case in GROUND_ONE_WHEEL_CASES:              # 23.483: one main only
            assert not left.carries_load and right.carries_load, case
            assert not nose.carries_load, case
        elif case > 24:                                 # 23.499: nose only
            assert nose.carries_load, case
            assert not left.carries_load and not right.carries_load, case
        else:
            assert left.carries_load and right.carries_load, case
            # The nose is on the ground for the 3-wheel level (1-3) and the
            # nose-down braked roll (13-15); every other family lifts it.
            on_ground = case in (1, 2, 3, 13, 14, 15)
            assert nose.carries_load is on_ground, case


# --------------------------------------------------------------------------- #
# 2. The point is the printed column
# --------------------------------------------------------------------------- #
def test_the_delivered_point_is_the_manuals_printed_column():
    """G-GF-6 / design note 39 AP-1: axle 1-12 and 25/26/28/29/31/32, ground
    contact 13-24 and 27/30/33 -- and the *delivered* leg says which, so a reader
    of the CSV never has to know the families to know where the load acts."""
    for name in _FIXTURES:
        for case, three in sorted(_legs(_project(name)).items()):
            want = application_point_of(case)
            assert want in (AXLE, GROUND_CONTACT)
            for leg in three:
                assert leg.point_name == want, f"{name} case {case} {leg.name}"


def test_the_delivered_point_is_the_axle_or_the_patch_and_never_something_between():
    """The point is one of the two the manual names, at this case's attitude.

    Anchored to the geometry rather than to ``gear_loads``' own construction: on
    the axle families the delivered z is the axle waterline at this case's strut
    state, and on the ground-contact families it is a rolling radius below it,
    down the ground normal.
    """
    project = _project("ga6_normal")
    gear = project.geometry.landing_gear
    gra = ground_angles(project.landing, gear)
    for case, three in sorted(_legs(project).items()):
        state, index = attitude_of(case)
        angle = math.radians(gra[index])
        for leg, side in ((three[0], gear.nose_gear), (three[2], gear.main_gear)):
            axle = {"compressed": side.axle_compressed,
                    "static": side.axle_static,
                    "extended": side.axle_extended}[state]
            r = side.rolling_radius_in if leg.point_name == GROUND_CONTACT else 0.0
            assert math.isclose(leg.point[0], axle[0] + r * math.sin(angle), abs_tol=1e-9)
            assert math.isclose(leg.point[2], axle[1] - r * math.cos(angle), abs_tol=1e-9)


# --------------------------------------------------------------------------- #
# 3. The forces sum to the page, and the load factors follow
# --------------------------------------------------------------------------- #
#: p232's printed force cells for the GA-6, ``{case: (vn, dn, vm, dm)}``, with
#: the approved corrections already applied -- this is ``test_landing._P232``
#: merged with ``test_landing._CORRECTED["p232"]``, imported rather than copied
#: so a re-ruling moves one table.
def _p232_forces():
    from test_landing import _CORRECTED, _P232
    out = {}
    for case, row in _P232.items():
        cell = dict(zip(("vn", "dn", "vm", "dm", "sm"), row))
        cell.update(_CORRECTED["p232"].get(case, {}))
        out[case] = cell
    return out


def test_the_three_delivered_legs_sum_to_the_printed_page():
    """G-GF-6: the delivered set is the page, redistributed onto three wheels.

    p232 prints one *main* column carrying the per-wheel reaction; the delivered
    set puts it on the two wheels an airplane stands on (or the one, on 23.483).
    Summing the three legs must return the page's own ``VN + 2*VM`` -- which is
    also, exactly, the numerator LANDLOAD.BAS's ``NV`` loop uses. If the mirror,
    the one-wheel exception or the side family's second wheel were wrong, the sum
    would not close.
    """
    printed = _p232_forces()
    legs = _legs(_project("ga6_normal"))
    for case in range(1, 34):
        cell = printed[case]
        mains = 1 if case in GROUND_ONE_WHEEL_CASES else 2
        if case > 24:
            mains = 0                       # 23.499: no main reaction at all
        # p232 prints no main column for the 23.499 family; ``mains = 0`` is
        # what makes that a statement rather than a gap.
        want_z = cell["vn"] + mains * (cell["vm"] or 0.0)
        want_x = cell["dn"] + mains * (cell["dm"] or 0.0)
        got_x = sum(leg.force[0] for leg in legs[case])
        got_z = sum(leg.force[2] for leg in legs[case])
        band_z = max(0.5, abs(want_z) * REL)
        band_x = max(0.5, abs(want_x) * REL)
        assert abs(got_z - want_z) <= band_z, f"case {case} Fz {got_z} != {want_z}"
        assert abs(got_x - want_x) <= band_x, f"case {case} Fx {got_x} != {want_x}"


def test_the_side_family_puts_different_side_loads_on_the_two_wheels():
    """23.485(c): 0.5 W inboard on one wheel and 0.33 W outboard on the other,
    acting the **same** way globally and summing to the 0.83 W that ``NS`` states.

    LANDLOAD carries the second wheel's share on the *paired* case rather than on
    this one, so a delivered set built from one case alone would put 0.5 W on
    both wheels and overstate the side load by 20 %. The pairing owner is
    ``landing.side_partner``; this is the number that proves it was used.
    """
    _, reactions = build_landing(_project("ga6_normal"))
    by_case = {c.case: c for c in reactions}
    legs = _legs(_project("ga6_normal"))
    for case in range(19, 25):
        assert side_partner(case) is not None
        total = sum(leg.force[1] for leg in legs[case])
        want = by_case[case].ns * by_case[case].weight_lb
        assert math.isclose(total, want, rel_tol=1e-9), case
        assert math.isclose(abs(by_case[case].ns), 0.83, abs_tol=5e-3), case


def test_the_datum_load_factors_are_the_printed_formula_on_the_printed_page():
    """G-GF-6: NR/NV/ND rebuilt from p232's force cells, never from the module.

    ``NV = (VN + n*VM)/WL + LF*cos(rho)``, ``ND = (DN + n*DM)/WL + LF*sin(rho)``,
    ``NR = hypot(NV, ND)`` -- LANDLOAD.BAS's own loops, with ``n = 1`` on the
    one-wheel family and the lift term written as the *rotation* of a ground-line
    vertical rather than as ``+-LF*SIN(GRA)`` longhand. The longhand is where the
    manual's sign error lives (design note 38 §1.6, OQ-1): the corrected term is
    what a rotation through the case's own ``rho = -GRA`` gives, and the two
    differ only on the families the ruling touches -- which is why the tail-down
    cases 7-9 come out **exactly as printed** here.
    """
    printed = _p232_forces()
    project = _project("ga6_normal")
    _, reactions = build_landing(project)
    by_case = {c.case: c for c in reactions}
    gra = ground_angles(project.landing, project.geometry.landing_gear)
    lift = project.landing.lift_factor
    for case in range(1, 25):
        cell = printed[case]
        c = by_case[case]
        mains = 1 if case in GROUND_ONE_WHEEL_CASES else 2
        nv = (cell["vn"] + mains * cell["vm"]) / c.weight_lb
        nd = (cell["dn"] + mains * cell["dm"]) / c.weight_lb
        if case in GROUND_LIFT_CASES:
            rho = math.radians(-gra[attitude_of(case)[1]])
            nv += lift * math.cos(rho)
            nd += lift * math.sin(rho)
        nr = math.hypot(nv, nd)
        for name, want, got in (("NV", nv, c.nv), ("ND", nd, c.nd), ("NR", nr, c.nr)):
            band = max(1e-3, abs(want) * REL)
            assert abs(got - want) <= band, f"case {case} {name}: {got} != {want}"


def test_case_1_and_case_16_lock_at_the_ruled_numbers():
    """The two cells design note 38 names by value (G-GF-6).

    Case 1 is the ND lift term's own case: printed 3.287 / 3.216 / 0.679, ruled
    **3.269 / 3.216 / 0.585** -- ``NV`` unchanged because a cosine is even, and
    that is the tell that only the drag term moved. Case 16 is the independent
    corroboration: on the wheels-only families ``NR`` is frame-invariant, so the
    GF-1 rotation must leave it **exactly as printed at 1.703** while moving
    ``NV``/``ND`` from 1.238/1.170 to 1.413/0.951. A correction that broke that
    invariance would be the wrong correction.
    """
    _, reactions = build_landing(_project("ga6_normal"))
    by_case = {c.case: c for c in reactions}
    for name, want, got in (("NR", 3.269, by_case[1].nr),
                            ("NV", 3.216, by_case[1].nv),
                            ("ND", 0.585, by_case[1].nd)):
        assert abs(got - want) <= 1e-3, f"case 1 {name}: {got} != {want}"
    assert abs(by_case[16].nr - 1.703) <= 1e-3, by_case[16].nr      # printed
    assert abs(by_case[16].nv - 1.413) <= 1e-3, by_case[16].nv
    assert abs(by_case[16].nd - 0.951) <= 1e-3, by_case[16].nd
    # The tail-down family reproduces all three printed cells with no deviation
    # at all -- the BAS already carries the corrected sign there (note 38 §1.6).
    for name, want, got in (("NR", 3.167, by_case[7].nr),
                            ("NV", 3.059, by_case[7].nv),
                            ("ND", -0.820, by_case[7].nd)):
        assert abs(got - want) <= 1e-3, f"case 7 {name}: {got} != {want}"


def test_the_datum_moments_are_a_rotation_of_the_printed_ground_line_ones():
    """p233's second table: pitch invariant, roll and yaw rotated through rho.

    A moment vector rotates exactly as a force vector does under the same change
    of frame, so the magnitude of the (roll, yaw) pair is preserved and the
    pitching moment -- about the axis the rotation is taken around -- does not
    move at all. LANDLOAD.BAS's own ``PMOM = PMOMP`` says the second half; the
    first is what makes the transform a change of description rather than a
    change of load.
    """
    for name in _FIXTURES:
        _, reactions = build_landing(_project(name))
        for c in reactions:
            assert c.pitch == c.pitchp, f"{name} case {c.case}"
            before = math.hypot(c.rollp, c.yawp)
            after = math.hypot(c.roll, c.yaw)
            assert math.isclose(before, after, rel_tol=1e-9), f"{name} case {c.case}"


def test_the_fuselage_axis_angle_is_the_attitudes_ground_angle():
    """p231's FUSELAGE AXIS ANGLE column, per case rather than per family."""
    for name in _FIXTURES:
        project = _project(name)
        gra = ground_angles(project.landing, project.geometry.landing_gear)
        _, reactions = build_landing(project)
        for c in reactions:
            want = gra[attitude_of(c.case)[1]]
            assert math.isclose(c.fuselage_axis_angle_deg, want, abs_tol=1e-12), \
                f"{name} case {c.case}"
    # The GA-6's three printed angles (p230/p231): 4.057 / 4.724 / 15.
    _, ga = build_landing(_project("ga6_normal"))
    seen = {round(c.fuselage_axis_angle_deg, 3) for c in ga}
    assert seen == {4.057, 4.724, 15.0}, seen


# --------------------------------------------------------------------------- #
# 4. The CSV / text split
# --------------------------------------------------------------------------- #
def _landing_result(project):
    import sloads.modules  # noqa: F401  (registers every module)
    return registry.get("landing")(project)


def test_the_delivered_csv_is_body_frame_and_the_text_report_keeps_both():
    """G-GF-6, drift-guarded **both ways**.

    The CSV is the deliverable and carries the airplane datum alone; the text
    report is the analysis view and carries the manual's primed set beside it.
    Guarding one direction only would let the primed set quietly reappear in the
    CSV (a reader would take a ground-line number for a body-frame one, which is
    a rotation of the ground angle wrong) or quietly vanish from the report (the
    frame the manual prints and a gear engineer reads would stop shipping).
    """
    for name in _FIXTURES:
        result = _landing_result(_project(name))
        primed = {v.label for c in result.conditions for v in c.values
                  if v.frame == GROUND_LINE}
        datum = {v.label for c in result.conditions for v in c.values
                 if v.frame == AIRPLANE_DATUM}
        assert primed and datum, name
        rows = list(_csv.DictReader(_io.StringIO(io.load_cases_csv(result))))
        quantities = {r["Quantity"] for r in rows}
        assert not (primed & quantities), f"{name}: ground-line rows in the CSV"
        assert datum <= quantities, f"{name}: body-frame rows missing from the CSV"
        text = module_text_report("landing", result.conditions)
        for label in primed | datum:
            assert label in text, f"{name}: {label!r} missing from the text report"


def test_the_frame_split_is_owned_by_one_predicate():
    """Practice 3: the rule lives in ``frames.is_report_only``, not in the
    renderer. ``results_to_rows`` is the only channel that drops a row, and it
    drops exactly what that predicate names -- so a future frame is added in one
    place and both channels follow."""
    assert is_report_only(GROUND_LINE) is True
    assert is_report_only(AIRPLANE_DATUM) is False
    assert is_report_only("") is False          # a frameless value is delivered
    render = os.path.join(os.path.dirname(_HERE), "sloads", "report", "render.py")
    with open(render, encoding="utf-8") as fh:
        source = fh.read()
    assert source.count("if is_report_only(") == 1, \
        "the frame floor is applied somewhere other than results_to_rows"


def test_every_landing_value_names_a_known_frame_or_none():
    """A frame is a vocabulary, not free text: a typo would silently deliver a
    ground-line value as a body-frame one."""
    for name in _FIXTURES:
        for c in _landing_result(_project(name)).conditions:
            for v in c.values:
                assert v.frame in ("",) + FRAMES, (name, c.title, v.label, v.frame)


def test_the_angle_and_the_load_factors_are_never_scaled_to_ultimate():
    """G-GF-6: angle units ``deg``, blank SF column, and the value unmoved.

    The whole delivered set is ULTIMATE; an attitude and a load factor are not
    loads, so scaling them by 1.5 would be a wrong number rather than a mislabel.
    """
    result = _landing_result(_project("ga6_normal"))
    _, reactions = build_landing(_project("ga6_normal"))
    by_case = {c.case: c for c in reactions}
    rows = list(_csv.DictReader(_io.StringIO(io.load_cases_csv(result))))
    checked = 0
    for row in rows:
        if row["Quantity"] != "Fuselage axis angle":
            continue
        assert row["Units"] == "deg" and row["SF"] == "", row
        checked += 1
    assert checked >= 33, checked
    factors = [r for r in rows if r["Quantity"] == "Resultant load factor NR"]
    assert factors, "NR is not in the CSV"
    for row in factors:
        assert row["Units"] == "" and row["SF"] == "", row
    case_16 = next(r for r in factors if " — case 16 " in r["Condition"])
    assert math.isclose(float(case_16["Value"]), by_case[16].nr, rel_tol=1e-3)


def test_a_project_without_gear_geometry_still_refuses_rather_than_shipping_zeros():
    """The deliverable needs the axle stations; without them the honest answer is
    the refusal note 33 DS-3 already gives, not three legs at the origin."""
    project = _project("concept_heavy")
    try:
        _landing_result(project)
    except MissingInputError:
        return
    raise AssertionError("a project with no gear geometry produced a landing result")


# --------------------------------------------------------------------------- #
# 5. GF-7: one caption owner
# --------------------------------------------------------------------------- #
def test_the_frame_captions_are_the_manuals_own_words():
    """LANDLOAD.BAS lines 5140 / 5230 print the banner above each table."""
    assert caption(GROUND_LINE) == "with respect to ground line"
    assert caption(AIRPLANE_DATUM) == "with respect to airplane datum"
    for bad in ("", "body", "datum"):
        try:
            caption(bad)
        except ValueError:
            continue
        raise AssertionError(f"caption({bad!r}) did not raise")


def test_neither_gui_writes_the_frame_words_itself():
    """G-GF-7: one caption owner, and a guard that says so.

    Two prose copies of a frame label is how the main GUI came to say
    "(ground line)" on a table while the Oracle said nothing at all and the deck
    consumed the other frame. The words live in ``sloads.frames`` and every
    surface calls ``caption()``; this fails if either GUI spells them out again.
    """
    surfaces = [os.path.join(os.path.dirname(_HERE), p) for p in (
        "app/views/landing_loads.py", "oracle_app/results.py")]
    for path in surfaces:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        assert "caption(" in source, path
        for words in ("with respect to ground line",
                      "with respect to airplane datum"):
            assert words not in source, f"{path} spells out {words!r} itself"


def test_the_case_note_states_the_point_and_the_attitude():
    """A force and its point are one statement, and the point half is a word:
    which of Appendix A's two application points, and at what strut state."""
    result = _landing_result(_project("ga6_normal"))
    matrix = [c for c in result.conditions if " — case " in c.title]
    assert len(matrix) == 33
    for condition in matrix:
        case = int(condition.title.split(" — case ")[1].split(" ")[0])
        assert application_point_of(case) in condition.note, condition.title
        assert attitude_of(case)[0] in condition.note, condition.title
        assert caption(AIRPLANE_DATUM) in condition.note


def test_the_delivered_csv_states_its_frame_and_its_application_point():
    """#141: a CSV forwarded on its own says which frame and which point.

    The point used to be carried **numerically only** -- x/y/z per gear -- with
    the word ``axle`` living in the condition note and the GUI captions, both of
    which this channel drops. A standalone consumer could not tell case 1 acts
    at the axle except by comparing coordinates back to the geometry, and the
    two points are 15-25 in apart on a light single, which is a moment arm.
    Every delivered force row therefore names both, from the value itself.
    """
    for name in _FIXTURES:
        result = _landing_result(_project(name))
        rows = list(_csv.DictReader(_io.StringIO(io.load_cases_csv(result))))
        assert "Frame" in rows[0] and "Applied at" in rows[0], sorted(rows[0])
        forces = [r for r in rows if r["Units"].startswith("lbs-")
                  and " F" in r["Quantity"]]
        assert len(forces) >= 33 * 3 * 3, (name, len(forces))
        for row in forces:
            assert row["Frame"] == AIRPLANE_DATUM, (name, row)
            assert row["Applied at"] in (AXLE, GROUND_CONTACT), (name, row)


def test_the_csv_point_is_appendix_as_printed_column_case_by_case():
    """The column is the manual's, not a constant: cases 1-12 are the axle and
    13-24 the ground contact point, so a fixed word in either cell would read
    correct on half the matrix and wrong on the other half."""
    result = _landing_result(_project("ga6_normal"))
    rows = list(_csv.DictReader(_io.StringIO(io.load_cases_csv(result))))
    checked = 0
    for row in rows:
        if " — case " not in row["Condition"] or not row["Applied at"]:
            continue
        case = int(row["Condition"].split(" — case ")[1].split(" ")[0])
        assert row["Applied at"] == application_point_of(case), row
        checked += 1
    assert checked >= 33 * 3 * 6, checked


def test_the_reference_node_names_no_application_point():
    """The node is the leg reference point the reaction is transferred *to*,
    not the point the force acts at. Stamping it would say one force is applied
    in two places at once -- and its coordinates differ from the point's, which
    is the whole reason the transfer couple exists."""
    result = _landing_result(_project("ga6_normal"))
    rows = list(_csv.DictReader(_io.StringIO(io.load_cases_csv(result))))
    nodes = [r for r in rows if " node " in r["Quantity"]]
    assert len(nodes) >= 33 * 3 * 3, len(nodes)
    for row in nodes:
        assert row["Applied at"] == "", row
        assert row["Frame"] == AIRPLANE_DATUM, row


def test_every_landing_value_names_a_known_point_or_none():
    """A point is a vocabulary, not free text (the ``frame`` argument one step
    further): a typo delivers a load to a point that does not exist, and is
    indistinguishable downstream from delivery to the other point."""
    for name in _FIXTURES:
        for c in _landing_result(_project(name)).conditions:
            for v in c.values:
                assert v.point in ("",) + POINTS, (name, c.title, v.label, v.point)


def test_a_module_that_names_neither_gets_neither_column():
    """The two columns are ordinary columns under the data-shaped floor, so the
    all-empty prune removes them from every module that names no frame and no
    point -- #141 states the landing output, it does not widen every CSV."""
    project = _project("ga6_normal")
    import sloads.modules  # noqa: F401  (registers every module)
    result = registry.get("weight_estimate")(project)
    rows = list(_csv.DictReader(_io.StringIO(io.load_cases_csv(result))))
    assert rows, "weight_estimate produced no rows"
    assert "Frame" not in rows[0] and "Applied at" not in rows[0], sorted(rows[0])


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
