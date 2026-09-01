"""Validate WTENV against the FAR 23 LOADS manual, Appendix A / Chapter 3.

The 6-place single's worked example (Ch 3 p21-22, with the structural CG points
echoed in the Appendix A FLTLOADS V-n table) gives:

* structural-limit stations  85.1 (aft gross), 77.49 (fwd gross), 72.64 (fwd
  regardless), from XLEMAC 63.641 + pct*MAC 69.246;
* minimum flight weight 2063 lb @ 73.09; maximum loading 3322 lb @ 84.56;
* ballast WEIGHTS 78 / 418 / 158 lb (aft gross / fwd gross / fwd regardless).

The ballast *stations* are matched where the manual's hand calc did not round the
limit station: forward gross 80.27 (±0.1%) and forward regardless 70.97 (±0.5%,
hand-calc rounding). The aft-gross ballast station is the *exact* moment balance
(~108.5), not the manual's hand-rounded 103.7 (which used the limit station 85.0
rather than 85.107); see the module docstring. The weight is the robust oracle.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import value_of

from sloads import Project, WeightInput, io
from sloads.models import (
    MassItem,
    MassItemKind,
    WeightEnvelopeInput,
)
from sloads.modules import weight_envelope as calc

TOL = 1e-3  # ±0.1% relative

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "ga6_normal.project.json",
)


def results():
    project = io.load_project(_EXAMPLE)
    return calc.envelope(project, project.weight.envelope)


def test_structural_limit_stations():
    # Ch 3 p21: 63.641 + .31/.20/.13 * 69.246 = 85.1 / 77.49 / 72.64.
    r = results()
    assert math.isclose(value_of(r, "aft_gross_station"), 85.1, rel_tol=TOL)
    assert math.isclose(value_of(r, "forward_gross_station"), 77.49, rel_tol=TOL)
    assert math.isclose(value_of(r, "forward_regardless_station"), 72.64, rel_tol=TOL)


def test_minimum_and_maximum_loadings():
    # Min flight weight 2063 @ 73.09 (empty + pilot + 1/2 hr fuel);
    # max loading 3322 @ 84.56 (all six occupants + fuel, no ballast).
    r = results()
    assert math.isclose(value_of(r, "minimum_flight_weight"), 2063, rel_tol=TOL)
    assert math.isclose(value_of(r, "minimum_flight_weight_station"), 73.09, rel_tol=TOL)
    assert math.isclose(value_of(r, "maximum_loading_weight"), 3322, rel_tol=TOL)
    assert math.isclose(value_of(r, "maximum_loading_station"), 84.56, rel_tol=TOL)


def test_ballast_weights_match_manual():
    # Ch 3 p22 ballast weights: aft 78, fwd gross 418, fwd regardless 158.
    r = results()
    assert math.isclose(value_of(r, "aft_gross_ballast_weight"), 78, rel_tol=TOL)
    assert math.isclose(value_of(r, "forward_gross_ballast_weight"), 418, rel_tol=TOL)
    assert math.isclose(value_of(r, "forward_regardless_ballast_weight"), 158, rel_tol=TOL)


def test_ballast_stations():
    # Forward gross station matches tightly; forward regardless within the hand-
    # calc rounding; aft gross is the exact moment balance (manual hand-rounded).
    r = results()
    # The ballast stations solve a moment balance against the WTENV structural
    # CG limits, which are XLEMAC-referenced -- so they carry the wing MAC's
    # 0.042 % shift under closed-form planform integration (2026-08-30, register
    # line in 02_approved_corrections). Forward gross 80.27 -> 80.145 (0.16 %),
    # forward regardless 70.97 -> 70.751, both still inside the hand-calc
    # rounding the second one was always gated at.
    assert math.isclose(value_of(r, "forward_gross_ballast_station"), 80.145, rel_tol=1e-3)
    assert math.isclose(value_of(r, "forward_regardless_ballast_station"), 70.97, rel_tol=5e-3)
    aft = value_of(r, "aft_gross_ballast_station")
    assert 107.0 < aft < 110.0  # exact balance ~108.5; manual hand-calc gave 103.7


def test_four_structural_points_for_fltloads():
    # The four CG points handed to FLTLOADS (Appendix A V-n: CG1..CG4).
    r = results()
    assert value_of(r, "aft_gross_point_weight") == 3400
    assert value_of(r, "forward_regardless_point_weight") == 2800
    assert math.isclose(value_of(r, "minimum_weight_point_station"), 73.09, rel_tol=TOL)


def _labels(conditions):
    return [v.label for c in conditions for v in c.values]


def _mi(name, w, x, kind):
    return MassItem(name=name, weight_lb=w, x=x, y=0.0, z=0.0,
                    ixx=0.0, iyy=0.0, izz=0.0, kind=kind)


def _over_gross_project(disc_c_station):
    """A synthetic database whose FULL loading (1500 lb) exceeds gross (1200 lb).

    XLEMAC 100 / MAC 50 -> aft-gross limit station = 100 + 0.30*50 = 115.
    The forward-loading vertices are (700, 108.57), (900, 104.44), (1100, 102.73),
    (1500, x). ``disc_c_station`` places the heaviest (aft) discretionary item, so
    it selects whether the heaviest at-or-below-gross vertex lands forward of the
    aft limit (positive ballast) or the full loading pushes it aft.
    """
    items = [
        _mi("empty", 600, 110, MassItemKind.EMPTY),
        _mi("crew", 100, 100, MassItemKind.MINIMUM),
        _mi("fwd_a", 200, 90, MassItemKind.DISCRETIONARY),
        _mi("fwd_b", 200, 95, MassItemKind.DISCRETIONARY),
        _mi("aft_c", 400, disc_c_station, MassItemKind.DISCRETIONARY),
    ]
    env = WeightEnvelopeInput(
        gross_weight=1200, aft_gross_pct_mac=30, fwd_gross_pct_mac=10,
        fwd_regardless_pct_mac=5, fwd_regardless_weight=1000, xlemac=100, mac=50,
    )
    return Project(name="over-gross", weight=WeightInput(items=items, envelope=env))


def test_aft_gross_uses_heaviest_loading_below_gross():
    # M1-7: when the full discretionary loading (1500) exceeds gross (1200), the
    # aft-gross reference is the heaviest vertex NOT exceeding gross (1100 @ 102.73,
    # forward of the aft limit) -> positive ballast, NOT the 0 the prior code emitted
    # from the negative (gross - max_load) difference.
    p = _over_gross_project(disc_c_station=130)
    r = calc.envelope(p, p.weight.envelope)
    assert math.isclose(value_of(r, "aft_gross_ballast_weight"), 100.0, rel_tol=TOL)
    # ballast station is the exact moment balance (1200*115 - 1100*102.73)/100.
    assert math.isclose(value_of(r, "aft_gross_ballast_station"), 250.0, rel_tol=5e-3)


def _degenerate_project(nose_x=None, tail_x=None):
    """Synthetic DB for the two degenerate-reference markers (M1-7).

    XLEMAC 1000 / MAC 200: aft-gross limit 1060, fwd-gross 1020. Empty + crew
    sit at 1050; the only discretionary rows are *aft* (1150), so (a) the
    heaviest at-or-below-gross loading already sits at/aft of the aft limit --
    the aft-gross case needs no ballast -- and (b) no loading is forward of the
    fwd-gross station. Until D-27 ``concept_regional_jet`` exercised both as
    shipped; its limit-point cases now have real forward loadings, so the
    conditions are built here rather than the guards deleted.
    """
    items = [
        _mi("empty", 600, 1050, MassItemKind.EMPTY),
        _mi("crew", 100, 1050, MassItemKind.MINIMUM),
        _mi("aft-1", 200, 1150, MassItemKind.DISCRETIONARY),
        _mi("aft-2", 200, 1150, MassItemKind.DISCRETIONARY),
    ]
    env = WeightEnvelopeInput(
        gross_weight=1000, aft_gross_pct_mac=30, fwd_gross_pct_mac=10,
        fwd_regardless_pct_mac=10, fwd_regardless_weight=800, xlemac=1000, mac=200,
        fuselage_nose_x=nose_x, fuselage_tail_x=tail_x,
    )
    return Project(name="degenerate", weight=WeightInput(items=items, envelope=env))


def test_aft_gross_degenerate_reference_reports_marker():
    # If the heaviest at-or-below-gross loading already sits at/aft of the aft-CG
    # limit, the aft-CG case needs no ballast: an explicit "(none ...)" marker is
    # emitted (0 lb), not a wild negative moment-balance station.
    p = _degenerate_project()
    r = calc.envelope(p, p.weight.envelope)
    labels = _labels(r)
    assert any(lbl.startswith("Aft gross ballast (none") for lbl in labels)
    assert "Aft gross ballast weight" not in labels  # no nonphysical station emitted


def test_ballast_marker_rows_not_dropped():
    # M1-7 hardening: a reference with no qualifying vertex emits an explicit marker
    # row rather than silently vanishing -- here the forward-gross candidate set is
    # empty (no loading forward of the fwd-gross station).
    p = _degenerate_project()
    r = calc.envelope(p, p.weight.envelope)
    assert any(lbl.startswith("Forward gross ballast (none") for lbl in _labels(r))


def _fwd_regardless_project(nose_x, tail_x, aft_x=1060):
    """Synthetic DB whose forward-loading vertices all sit just aft of the forward-
    regardless limit, so the moment-balance ballast lands at a large FORWARD station
    (~580 in). ``nose_x``/``tail_x`` set the explicit fuselage extent override that
    decides whether that station is physical (kept) or nonphysical (marker) -- M1-11.

    XLEMAC 1000 / MAC 200 -> fwd-regardless limit = 1000 + 0.10*200 = 1020. The
    vertices are (700, 1042.86), (900, 1035.6), (1100, 1040); the heaviest at/below
    the regardless weight (1150) is 1100 @ 1040, 20 in aft of the limit -> ballast
    weight 50 lb at station (1150*1020 - 1100*1040)/50 = 580.
    """
    items = [
        _mi("empty", 600, 1050, MassItemKind.EMPTY),
        _mi("crew", 100, 1000, MassItemKind.MINIMUM),
        _mi("fwd", 200, 1010, MassItemKind.DISCRETIONARY),
        _mi("aft", 200, aft_x, MassItemKind.DISCRETIONARY),
    ]
    env = WeightEnvelopeInput(
        gross_weight=1100, aft_gross_pct_mac=30, fwd_gross_pct_mac=10,
        fwd_regardless_pct_mac=10, fwd_regardless_weight=1150, xlemac=1000, mac=200,
        fuselage_nose_x=nose_x, fuselage_tail_x=tail_x,
    )
    return Project(name="fwd-reg", weight=WeightInput(items=items, envelope=env))


def test_fwd_regardless_station_inside_extent_kept():
    # With a generous fuselage extent the ~580 in ballast station is physical: the
    # normal weight + station rows are emitted (no marker).
    p = _fwd_regardless_project(nose_x=500, tail_x=1200)
    r = calc.envelope(p, p.weight.envelope)
    assert math.isclose(value_of(r, "forward_regardless_ballast_weight"), 50.0, rel_tol=TOL)
    assert math.isclose(value_of(r, "forward_regardless_ballast_station"), 580.0, rel_tol=5e-3)


def test_fwd_regardless_station_outside_extent_marks_none():
    # Same loading, but a fuselage nose at 900 in makes the 580 in ballast station
    # forward of the fuselage -> nonphysical -> explicit "(none -- ... outside the
    # fuselage extent [900, 1200])" marker instead of the wild station (M1-11).
    p = _fwd_regardless_project(nose_x=900, tail_x=1200)
    r = calc.envelope(p, p.weight.envelope)
    labels = _labels(r)
    assert any(
        lbl.startswith("Forward regardless ballast (none") and "outside the fuselage extent" in lbl
        for lbl in labels
    )
    assert "Forward regardless ballast weight" not in labels


def test_fwd_regardless_negative_station_marks_none_via_datum():
    # A project with NO explicit extent and NO fuselage outline degrades to the
    # station-0 datum with an unbounded tail, and a moment balance that lands ahead
    # of the nose is flagged rather than emitted as a negative station (M1-11).
    #
    # This was dhc8_dash8 at -112 in until D-26 zoned that fixture's cabin and
    # holds, then cessna_210 at -3 in until T-8a gave the three real types a
    # published fuselage outline -- which is exactly the "if a shipped fixture ever
    # stops reaching it, build the loading here rather than deleting the guard"
    # this comment has carried twice. Built here now: the aft discretionary item
    # at 1300 in puts the 1100 lb vertex at cg 1083.6, so the balance against the
    # 1150 lb / 1020 in regardless limit is (1150*1020 - 1100*1083.6)/50 = -380 in.
    p = _fwd_regardless_project(nose_x=None, tail_x=None, aft_x=1300)
    r = calc.envelope(p, p.weight.envelope)
    labels = _labels(r)
    assert any(
        lbl.startswith("Forward regardless ballast (none") and "ahead of the station-0 datum" in lbl
        for lbl in labels
    )
    assert "Forward regardless ballast weight" not in labels


def test_fwd_regardless_extent_from_geometry_outline_kept():
    # The G1 fuselage outline supplies the extent when no explicit override is
    # entered (proves the outline path, not just the override, feeds the guard --
    # M1-11): the ~580 in ballast station of the synthetic DB is inside an
    # outline running [500, 1200] and is kept. (Was read off
    # ``concept_regional_jet``'s 63.7 in station until D-27 gave that fixture
    # limit-point cases whose forward-regardless corner needs no such ballast.)
    from sloads.models import FuselageOutline, FuselageSection, GeometryInput

    p = _fwd_regardless_project(nose_x=None, tail_x=None)
    p.geometry = GeometryInput(fuselage=FuselageOutline(sections=[
        FuselageSection(500.0, 0.0, 0.0), FuselageSection(800.0, 60.0, 60.0),
        FuselageSection(1200.0, 6.0, 9.0)]))
    r = calc.envelope(p, p.weight.envelope)
    assert math.isclose(value_of(r, "forward_regardless_ballast_weight"), 50.0, rel_tol=TOL)
    assert math.isclose(value_of(r, "forward_regardless_ballast_station"), 580.0, rel_tol=5e-3)


def test_run_requires_envelope_inputs():
    raised = False
    try:
        calc.run(Project(name="empty"))
    except ValueError:
        raised = True
    assert raised
    raised = False
    try:
        calc.run(Project(name="no envelope", weight=WeightInput()))
    except ValueError:
        raised = True
    assert raised


# --------------------------------------------------------------------------- #
# Design note 45 -- the aft edge (issue #157)
# --------------------------------------------------------------------------- #
#: Appendix A p138's weight data base, transcribed (note 45 WE-5).
#:
#: This is NOT ``ga6_normal``. The manual runs WTENV twice on two different data
#: bases: Chapter 3's, which has no baggage row and whose maximum loading is
#: 3322 @ 84.56, and Appendix A's, which adds ``66 BAGGAGE 120.00 @ 180.00`` and
#: reaches 3442 @ 87.89. ``ga6_normal`` is the Chapter 3 one, and the Ch 3
#: ballast lock above (78 / 418 / 158) is computed from its no-baggage maximum,
#: so the fixture cannot be "completed" to match Appendix A without breaking it.
#: The only printed edge tables in the manual are p139's, on this data base --
#: hence a transcription here rather than a shipped example project.
_P138_EMPTY = (
    ("WING, OUTBOARD", 330.0, 97.87, 87.73), ("HORIZ TAIL", 42.0, 270.36, 111.0),
    ("VERT TAIL", 23.0, 276.93, 137.76), ("MAIN GEAR WHEE", 45.0, 97.0, 69.0),
    ("MAIN GEAR STRU", 110.0, 97.0, 78.0), ("NOSE GEAR WHEE", 9.0, 1.0, 52.0),
    ("NOSE GEAR STRU", 40.0, 1.0, 65.0), ("FLIGHT CONTROL", 57.0, 123.0, 105.0),
    ("NACELLE", 62.0, 21.0, 92.0), ("ENGINE INSTALL", 505.0, 22.0, 92.0),
    ("PROPELLER", 74.0, -10.0, 100.0), ("SYSTEMS", 88.0, 60.0, 100.0),
    ("FURNISHINGS", 175.0, 105.0, 100.0), ("UNUSABLE FUEL", 12.0, 73.0, 80.0),
    ("FUSELAGE STRUC", 250.0, 99.0, 80.0),
)
_P138_MINIMUM = (("PILOT", 170.0, 75.0, 100.0), ("30 MIN FUEL", 71.0, 70.0, 82.0))
_P138_DISCRETIONARY = (
    ("COPILOT", 170.0, 75.0, 100.0), ("3RD PERSON", 170.0, 111.0, 100.0),
    ("4TH PERSON", 170.0, 111.0, 100.0), ("5TH PERSON", 170.0, 150.0, 100.0),
    ("6TH PERSON", 170.0, 150.0, 100.0), ("BAGGAGE", 120.0, 180.0, 110.0),
    ("FUEL TO FULL", 409.0, 70.0, 87.0),
)

#: Appendix A p139, both printed blocks: ``(XBAR, ZBAR, WEIGHT)`` per vertex, in
#: print order. The minimum-weight vertex heads each edge, as the program prints
#: it (``WTENV.BAS`` 760). Item names are NOT asserted: the manual's sort is
#: unstable and additionally shuffles the blank records of its dimensioned
#: array, so the printed order within the two equal-station pairs
#: (3RD/4TH at 111.00, 5TH/6TH at 150.00) is a function of the array size rather
#: than of the airplane -- and it cannot move a number, because tied items share
#: a station (note 45 WE-4, §1.5).
_P139_FORWARD = (
    (73.09, 90.73, 2063.0), (72.58, 90.11, 2472.0), (72.74, 90.75, 2642.0),
    (75.05, 91.31, 2812.0), (77.10, 91.80, 2982.0), (81.03, 92.24, 3152.0),
    (84.56, 92.64, 3322.0), (87.89, 93.25, 3442.0),
)
_P139_AFT = (
    (73.09, 90.73, 2063.0), (78.97, 91.79, 2183.0), (84.10, 92.38, 2353.0),
    (88.54, 92.89, 2523.0), (89.96, 93.34, 2693.0), (91.21, 93.74, 2863.0),
    (90.30, 94.09, 3033.0), (87.89, 93.25, 3442.0),
)


def _p138_project(discretionary=_P138_DISCRETIONARY):
    """Appendix A p138's data base as a Project. Only ``weight.items`` is needed:
    :func:`loading_envelope` reads nothing else."""
    items = [MassItem(name=n, weight_lb=w, x=x, z=z, kind=k)
             for k, rows in ((MassItemKind.EMPTY, _P138_EMPTY),
                             (MassItemKind.MINIMUM, _P138_MINIMUM),
                             (MassItemKind.DISCRETIONARY, discretionary))
             for n, w, x, z in rows]
    return Project(name="Appendix A p138", weight=WeightInput(items=items))


def test_both_edges_reproduce_appendix_a_p139():
    """G-WE-1: all 16 printed rows, all three printed columns, to +/-0.1%.

    Appendix A p139, "ENVELOPE OF DISCRETIONARY LOAD FOR" -- the forward block
    (WTENV.BAS 280-330, "NOW PRINTING FORWARD EDGE OF ENVELOPE") and the aft
    block (390-500, "NOW PRINTING AFT EDGE OF ENVELOPE").
    """
    project = _p138_project()
    for aft, printed in ((False, _P139_FORWARD), (True, _P139_AFT)):
        edge = calc.loading_envelope(project, aft=aft)
        assert len(edge) == len(printed), ("p139 prints "
            f"{len(printed)} vertices on the {'aft' if aft else 'forward'} edge")
        for vertex, (xbar, zbar, weight) in zip(edge, printed):
            where = f"{'aft' if aft else 'forward'} edge, {weight:.0f} lb"
            assert math.isclose(vertex.weight, weight, rel_tol=TOL), where
            assert math.isclose(vertex.station, xbar, rel_tol=TOL), where
            assert math.isclose(vertex.waterline, zbar, rel_tol=TOL), where


def test_the_two_edges_close_the_envelope():
    """Both sweeps start at the minimum flight weight and end at the same full
    loading -- what makes the two edges one closed envelope (WTENV.BAS 330/500
    are the same subroutine over the same items in opposite order)."""
    project = _p138_project()
    forward = calc.loading_envelope(project, aft=False)
    aft = calc.loading_envelope(project, aft=True)
    assert forward[0] == aft[0]
    assert forward[-1] == aft[-1]


def test_the_aft_edge_leaves_the_structural_box_on_ga6():
    """The reason the figure needs both edges (note 45 §1.6). The forward edge
    stays inside the aft-gross CG limit the whole way; the aft edge does not.

    Ch 3 p21 says that is expected and not a defect -- the limits bound what the
    pilot may fly, not what the airplane can physically hold."""
    project = io.load_project(_EXAMPLE)
    aft_limit = value_of(results(), "aft_gross_station")
    forward = calc.loading_envelope(project, aft=False)
    aft = calc.loading_envelope(project, aft=True)
    assert max(v.station for v in forward) < aft_limit
    assert max(v.station for v in aft) > aft_limit


def test_the_aft_edge_adds_a_condition_and_changes_no_existing_one():
    """G-WE-2: the OR-15 admission is additive.

    The four pre-existing conditions keep their titles, notes and order, the aft
    edge is appended after them, and every legacy key still carries its own
    label and units. The pre-existing *values* are held by every other test in
    this file, which is unedited by note 45 (G-WE-3)."""
    r = results()
    assert [c.title for c in r[:4]] == [
        "Weight envelope summary",
        "Structural CG-limit stations and loadings",
        "Ballast to reach the structural limits",
        "Forward loading envelope (weight, station)",
    ]
    assert len(r) == 5 and r[4].title.startswith("Aft loading envelope")
    forward = next(c for c in r if c.title.startswith("Forward loading"))
    legacy = [v for v in forward.values if not v.key.endswith("_waterline")]
    assert [v.key for v in legacy] == [
        k for i in range(1, len(legacy) // 2 + 1)
        for k in (f"point_{i}_weight", f"point_{i}_station")]
    assert all(v.units == "lb" and v.quantity == "mass"
               for v in legacy if v.key.endswith("_weight"))
    assert all(v.units == "in" for v in legacy if v.key.endswith("_station"))


def test_the_forward_edge_has_exactly_one_owner():
    """G-WE-4: ``loading_envelope_points`` is the station-only projection of the
    same sweep, not a second walk -- so the GUI chart and the report can never
    be shown different vertices."""
    for name in ("ga6_normal", "cessna_210", "dhc8_dash8", "concept_heavy"):
        path = os.path.join(os.path.dirname(_EXAMPLE), f"{name}.project.json")
        project = io.load_project(path)
        assert calc.loading_envelope_points(project) == [
            (v.weight, v.station) for v in calc.loading_envelope(project)]


def test_an_edge_is_invariant_to_the_entry_order_of_equal_station_items():
    """G-WE-5: the determinism WE-4 asks for.

    p138 ties 3RD/4TH PERSON at station 111.00 and 5TH/6TH at 150.00. Swapping
    each pair in the data base must not move a vertex -- tied items contribute
    the same weight at the same station, so the cumulative point is identical
    whichever is counted first. This is why the manual's unstable sort order is
    not reproduced: it is unobservable in the numbers."""
    swapped = list(_P138_DISCRETIONARY)
    swapped[1], swapped[2] = swapped[2], swapped[1]   # 3RD <-> 4TH  (x=111)
    swapped[3], swapped[4] = swapped[4], swapped[3]   # 5TH <-> 6TH  (x=150)
    for aft in (False, True):
        assert (calc.loading_envelope(_p138_project(tuple(swapped)), aft=aft)
                == calc.loading_envelope(_p138_project(), aft=aft))


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
