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

from sloads import Project, WeightInput, io  # noqa: E402
from sloads.models import (  # noqa: E402
    MassItem,
    MassItemKind,
    WeightEnvelopeInput,
)
from sloads.modules import weight_envelope as calc  # noqa: E402
from helpers import value_of  # noqa: E402

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
    assert math.isclose(value_of(r, "Aft gross station"), 85.1, rel_tol=TOL)
    assert math.isclose(value_of(r, "Forward gross station"), 77.49, rel_tol=TOL)
    assert math.isclose(value_of(r, "Forward regardless station"), 72.64, rel_tol=TOL)


def test_minimum_and_maximum_loadings():
    # Min flight weight 2063 @ 73.09 (empty + pilot + 1/2 hr fuel);
    # max loading 3322 @ 84.56 (all six occupants + fuel, no ballast).
    r = results()
    assert math.isclose(value_of(r, "Minimum flight weight"), 2063, rel_tol=TOL)
    assert math.isclose(value_of(r, "Minimum flight weight station"), 73.09, rel_tol=TOL)
    assert math.isclose(value_of(r, "Maximum loading weight"), 3322, rel_tol=TOL)
    assert math.isclose(value_of(r, "Maximum loading station"), 84.56, rel_tol=TOL)


def test_ballast_weights_match_manual():
    # Ch 3 p22 ballast weights: aft 78, fwd gross 418, fwd regardless 158.
    r = results()
    assert math.isclose(value_of(r, "Aft gross ballast weight"), 78, rel_tol=TOL)
    assert math.isclose(value_of(r, "Forward gross ballast weight"), 418, rel_tol=TOL)
    assert math.isclose(value_of(r, "Forward regardless ballast weight"), 158, rel_tol=TOL)


def test_ballast_stations():
    # Forward gross station matches tightly; forward regardless within the hand-
    # calc rounding; aft gross is the exact moment balance (manual hand-rounded).
    r = results()
    assert math.isclose(value_of(r, "Forward gross ballast station"), 80.27, rel_tol=TOL)
    assert math.isclose(value_of(r, "Forward regardless ballast station"), 70.97, rel_tol=5e-3)
    aft = value_of(r, "Aft gross ballast station")
    assert 107.0 < aft < 110.0  # exact balance ~108.5; manual hand-calc gave 103.7


def test_four_structural_points_for_fltloads():
    # The four CG points handed to FLTLOADS (Appendix A V-n: CG1..CG4).
    r = results()
    assert value_of(r, "Aft gross point weight") == 3400
    assert value_of(r, "Forward regardless point weight") == 2800
    assert math.isclose(value_of(r, "Minimum weight point station"), 73.09, rel_tol=TOL)


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
    assert math.isclose(value_of(r, "Aft gross ballast weight"), 100.0, rel_tol=TOL)
    # ballast station is the exact moment balance (1200*115 - 1100*102.73)/100.
    assert math.isclose(value_of(r, "Aft gross ballast station"), 250.0, rel_tol=5e-3)


def test_aft_gross_degenerate_reference_reports_marker():
    # If the heaviest at-or-below-gross loading already sits at/aft of the aft-CG
    # limit, the aft-CG case needs no ballast: an explicit "(none ...)" marker is
    # emitted (0 lb), not a wild negative moment-balance station. concept_regional_jet
    # (full loading 34800 > gross 33000; reference 32800 @ 607.2, aft of the 593.8
    # limit) exercises this.
    p = io.load_project(os.path.join(os.path.dirname(_EXAMPLE), "concept_regional_jet.project.json"))
    r = calc.envelope(p, p.weight.envelope)
    labels = _labels(r)
    assert any(lbl.startswith("Aft gross ballast (none") for lbl in labels)
    assert "Aft gross ballast weight" not in labels  # no nonphysical station emitted


def test_ballast_marker_rows_not_dropped():
    # M1-7 hardening: a reference with no qualifying vertex emits an explicit marker
    # row rather than silently vanishing. On concept_regional_jet the forward-gross
    # candidate set is empty (no loading forward of the fwd-gross station).
    p = io.load_project(os.path.join(os.path.dirname(_EXAMPLE), "concept_regional_jet.project.json"))
    r = calc.envelope(p, p.weight.envelope)
    assert any(lbl.startswith("Forward gross ballast (none") for lbl in _labels(r))


def _fwd_regardless_project(nose_x, tail_x):
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
        _mi("aft", 200, 1060, MassItemKind.DISCRETIONARY),
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
    assert math.isclose(value_of(r, "Forward regardless ballast weight"), 50.0, rel_tol=TOL)
    assert math.isclose(value_of(r, "Forward regardless ballast station"), 580.0, rel_tol=5e-3)


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
    # dhc8_dash8 carries no fuselage outline: its forward-regardless moment balance
    # lands at -112 in (ahead of the station-0 datum). The datum fallback flags it
    # as nonphysical rather than emitting the negative station (M1-11).
    p = io.load_project(os.path.join(os.path.dirname(_EXAMPLE), "dhc8_dash8.project.json"))
    r = calc.envelope(p, p.weight.envelope)
    labels = _labels(r)
    assert any(
        lbl.startswith("Forward regardless ballast (none") and "ahead of the station-0 datum" in lbl
        for lbl in labels
    )
    assert "Forward regardless ballast weight" not in labels


def test_fwd_regardless_extent_from_geometry_outline_kept():
    # concept_regional_jet has a G1 fuselage outline [0, 1056]; its 63.7 in ballast
    # station is inside that extent, so the geometry-derived extent keeps it (proves
    # the outline path, not just the explicit override, feeds the guard) -- M1-11.
    p = io.load_project(os.path.join(os.path.dirname(_EXAMPLE), "concept_regional_jet.project.json"))
    r = calc.envelope(p, p.weight.envelope)
    assert math.isclose(value_of(r, "Forward regardless ballast station"), 63.714, rel_tol=5e-3)


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
