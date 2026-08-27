"""Trim sweep -- balancing tail load vs CG (Step G5, GUI plot support).

The Flight Envelope page's "Trim & Stability" tab plots the balancing horizontal-
tail load at 1-g trim (FLTLOADS BAL A/C/D) swept across the CG range, plus the
tail-volume static margin. Both are *plots over existing calc*: the trim sweep
re-runs the FLTLOADS balance (subroutine 3900) at interpolated CG stations, and
the neutral point comes from the Configuration module. These tests lock in the
traceability guarantee -- a swept station that coincides with a project CG case
reproduces that case's ``build_envelope`` BAL load exactly.

Reference: FLTLOADS.BAS (Appendix C p421-428), Ref 1 Ch 8; Appendix A p179-180.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io
from sloads.modules.configuration import run as configuration_run
from sloads.modules.flight_envelope import build_envelope, trim_sweep

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_JET = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")


def _bal(env, cg_name, condition):
    return next(p.lt for p in env.vn if p.cg == cg_name and p.condition == condition)


def test_trim_sweep_reproduces_envelope_bal_loads():
    """A swept station that coincides with a CG case reproduces that case's
    ``build_envelope`` BAL load exactly (the trim plot's traceability guarantee).

    Appendix A CG1 (xcg 85.1) and CG2 (xcg 77.49) share weight 3400 lb / zcg 93,
    so one sweep at that weight/zcg must reproduce *both* cases' BAL A/C/D loads.
    """
    project = io.load_project(_GA)
    env = build_envelope(project)
    curves = {c.condition: c for c in
              trim_sweep(project, weight_lb=3400.0, zcg=93.0, xcg_stations=[77.49, 85.1])}
    for cond in ("BAL A", "BAL C", "BAL D"):
        lt_cg2, lt_cg1 = curves[cond].lt_lb  # stations [77.49 (CG2), 85.1 (CG1)]
        assert math.isclose(lt_cg2, _bal(env, "CG2", cond), rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(lt_cg1, _bal(env, "CG1", cond), rel_tol=1e-9, abs_tol=1e-6)


def test_trim_sweep_lt_rises_moving_aft():
    """Trim tail load increases (download decreases) as the CG moves aft -- the
    balance shortens the tail moment arm ``XT - Xcg`` while lengthening the wing-
    lift arm ``Xcg - Xw``. Physical-shape sanity for the plot."""
    project = io.load_project(_GA)
    curves = trim_sweep(project, weight_lb=3400.0, zcg=93.0,
                        xcg_stations=[75.0, 80.0, 85.0])
    for cur in curves:
        assert cur.lt_lb[0] < cur.lt_lb[1] < cur.lt_lb[2], (cur.condition, cur.lt_lb)


def test_trim_sweep_converges_to_unit_load_factor():
    """Every BAL point is a 1-g trim, so the balanced NZ is ~1 at every station."""
    project = io.load_project(_GA)
    curves = trim_sweep(project, weight_lb=3400.0, zcg=93.0,
                        xcg_stations=[77.0, 81.0, 85.0])
    for cur in curves:
        for nz in cur.nz:
            assert abs(nz - 1.0) <= 0.01, (cur.condition, nz)


def test_static_margin_neutral_point_available_for_layout_project():
    """The static-margin sweep reads the tail-volume neutral point from the
    Configuration module; a project with a parametric layout exposes it as a
    sensible %MAC, and the sweep arithmetic (SM = NP - CG) falls with aft CG."""
    project = io.load_project(_JET)
    vals = {lv.label: lv.value for c in configuration_run(project).conditions for lv in c.values}
    np_pct = vals["Neutral point (%MAC)"]
    xlemac = vals["XLE(MAC) station of MAC LE"]
    mac_in = vals["MAC"]
    assert 0.0 < np_pct < 150.0
    fwd_pct = (595.0 - xlemac) / mac_in * 100.0
    aft_pct = (620.0 - xlemac) / mac_in * 100.0
    assert (np_pct - fwd_pct) > (np_pct - aft_pct)  # static margin shrinks moving aft


def test_trim_sweep_needs_cruise_config():
    """Without any flaps-up (cruise) coefficient set the sweep raises, rather than
    silently using a flaps-down set at cruise speeds."""
    project = io.load_project(_GA)
    project.aero_coeffs.cruise = None
    try:
        trim_sweep(project, weight_lb=3400.0, zcg=93.0, xcg_stations=[80.0])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError with no cruise coefficient set")


if __name__ == "__main__":
    test_trim_sweep_reproduces_envelope_bal_loads()
    print("ok reproduces envelope BAL loads")
    test_trim_sweep_lt_rises_moving_aft()
    print("ok LT rises moving aft")
    test_trim_sweep_converges_to_unit_load_factor()
    print("ok NZ ~ 1 at every station")
    test_static_margin_neutral_point_available_for_layout_project()
    print("ok neutral point / static margin")
    test_trim_sweep_needs_cruise_config()
    print("ok needs cruise config")
    print("all trim-sweep tests passed")
