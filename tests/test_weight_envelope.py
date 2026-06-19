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

from farloads import Project, WeightInput, io  # noqa: E402
from farloads.modules import weight_envelope as calc  # noqa: E402

TOL = 1e-3  # ±0.1% relative

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "ga6_normal.project.json",
)


def results():
    project = io.load_project(_EXAMPLE)
    return calc.envelope(project, project.weight.envelope)


def _value(conditions, label):
    for c in conditions:
        for v in c.values:
            if v.label == label:
                return v.value
    raise KeyError(label)


def test_structural_limit_stations():
    # Ch 3 p21: 63.641 + .31/.20/.13 * 69.246 = 85.1 / 77.49 / 72.64.
    r = results()
    assert math.isclose(_value(r, "Aft gross station"), 85.1, rel_tol=TOL)
    assert math.isclose(_value(r, "Forward gross station"), 77.49, rel_tol=TOL)
    assert math.isclose(_value(r, "Forward regardless station"), 72.64, rel_tol=TOL)


def test_minimum_and_maximum_loadings():
    # Min flight weight 2063 @ 73.09 (empty + pilot + 1/2 hr fuel);
    # max loading 3322 @ 84.56 (all six occupants + fuel, no ballast).
    r = results()
    assert math.isclose(_value(r, "Minimum flight weight"), 2063, rel_tol=TOL)
    assert math.isclose(_value(r, "Minimum flight weight station"), 73.09, rel_tol=TOL)
    assert math.isclose(_value(r, "Maximum loading weight"), 3322, rel_tol=TOL)
    assert math.isclose(_value(r, "Maximum loading station"), 84.56, rel_tol=TOL)


def test_ballast_weights_match_manual():
    # Ch 3 p22 ballast weights: aft 78, fwd gross 418, fwd regardless 158.
    r = results()
    assert math.isclose(_value(r, "Aft gross ballast weight"), 78, rel_tol=TOL)
    assert math.isclose(_value(r, "Forward gross ballast weight"), 418, rel_tol=TOL)
    assert math.isclose(_value(r, "Forward regardless ballast weight"), 158, rel_tol=TOL)


def test_ballast_stations():
    # Forward gross station matches tightly; forward regardless within the hand-
    # calc rounding; aft gross is the exact moment balance (manual hand-rounded).
    r = results()
    assert math.isclose(_value(r, "Forward gross ballast station"), 80.27, rel_tol=TOL)
    assert math.isclose(_value(r, "Forward regardless ballast station"), 70.97, rel_tol=5e-3)
    aft = _value(r, "Aft gross ballast station")
    assert 107.0 < aft < 110.0  # exact balance ~108.5; manual hand-calc gave 103.7


def test_four_structural_points_for_fltloads():
    # The four CG points handed to FLTLOADS (Appendix A V-n: CG1..CG4).
    r = results()
    assert _value(r, "Aft gross point weight") == 3400
    assert _value(r, "Forward regardless point weight") == 2800
    assert math.isclose(_value(r, "Minimum weight point station"), 73.09, rel_tol=TOL)


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
