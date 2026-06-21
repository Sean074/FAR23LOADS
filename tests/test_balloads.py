"""BALLOADS verification utility (Step C11): cross-check of FLTLOADS' approximate
balancing-tail CP against SELECT's rational recomputation.

Oracle: Reference 1 Ch 9 case-202 hand-calc -- the up balancing tail load with
flaps retracted is LT = 519.845 lb (LT25 +907.62, LT50 -387.78, elevator
deflection -5.39 deg, CP 6.35% tail MAC). BALLOADS reuses select.htail_balance,
so its per-condition split must equal SELECT's selected balancing loads exactly.

Reference: BALLOADS.BAS (Appendix C p497), Ref 1 Ch 8-9; Appendix A
"Critical Horiz Tail Loads".
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, SelectInput, TailLoadsInput, io  # noqa: E402
from farloads.modules import balloads, select  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")

# Appendix A "General input for calculation of horiz tail loads" (6-place report);
# same fixture as tests/test_select.py.
_TAIL = TailLoadsInput(
    tail_incidence_deg=2.0, wing_zero_lift_cruise_deg=3.988146,
    aspect_ratio_wing=6.095, aspect_ratio_htail=4.017, htail_area_sqft=36.944,
    elevator_effectiveness=0.614, xt25=261.027, xt50=270.357,
    elevator_te_up_deg=30.0, elevator_te_down_deg=20.0, elevator_area_sqft=16.403,
    elevator_fwd_hinge_sqft=1.639, elevator_aft_hinge_sqft=14.792,
    airplane_length_ft=26.522, wing_lift_slope_per_rad=4.605,
)


def _ga6() -> Project:
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.select_input = SelectInput(full_down_aileron_deg=15.0, basic_airfoil_cm=-0.03)
    p.tail_loads = _TAIL
    return p


def test_case_202_up_balancing_load():
    """The largest up balancing load (case 202) matches the Ch 9 hand-calc."""
    rows = balloads.verify_balancing(_ga6())
    up = max(rows, key=lambda r: r["LT"])
    assert math.isclose(up["LT"], 519.845, rel_tol=3e-3), up["LT"]
    assert math.isclose(up["LT25"], 907.62, rel_tol=3e-3), up["LT25"]
    assert math.isclose(up["LT50"], -387.78, rel_tol=5e-3), up["LT50"]
    assert math.isclose(up["DELTA"], -5.39, abs_tol=0.03), up["DELTA"]
    assert math.isclose(up["CP"], 6.35, abs_tol=0.1), up["CP"]


def test_matches_select_balancing():
    """BALLOADS reuses select.htail_balance, so the rational up/down balancing
    loads equal SELECT's selected BAL RETRACTED conditions exactly."""
    project = _ga6()
    rows = balloads.verify_balancing(project)
    sel = {c.label: c for c in select.select_htail_balancing(project)}
    up = max(rows, key=lambda r: r["LT"])
    dn = min(rows, key=lambda r: r["LT"])
    assert math.isclose(up["LT"], sel["BAL UP RETRACTED"].loads[0].value, rel_tol=1e-9)
    assert math.isclose(dn["LT"], sel["BAL DN RETRACTED"].loads[0].value, rel_tol=1e-9)


def test_rational_station_confirms_approx_xtc():
    """The rational CP station sits within ~1 in of FLTLOADS' assumed XTC (the
    verification BALLOADS exists to perform)."""
    project = _ga6()
    project.flight_loads.xtc = _TAIL.xt25 + (6.35 - 25.0) * (_TAIL.xt50 - _TAIL.xt25) / 25.0
    up = max(balloads.verify_balancing(project), key=lambda r: r["LT"])
    assert abs(up["DXT"]) < 1.0


def test_run_emits_conditions():
    res = balloads.run(_ga6())
    assert res.module == "balloads"
    assert res.conditions
    assert all(c.far_reference == "23.421" for c in res.conditions)


if __name__ == "__main__":
    test_case_202_up_balancing_load()
    test_matches_select_balancing()
    test_rational_station_confirms_approx_xtc()
    test_run_emits_conditions()
    print("ok")
