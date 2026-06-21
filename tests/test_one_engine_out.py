"""One engine out vertical-tail loads (Step C9): ONENGOUT.BAS port (FAR 23.367).

The printed Appendix B (10-place twin turboprop) one-engine-out oracle is **absent**
from the bundled references (Reference 1 carries only the Appendix A GA single; the FAA
User's Guide Ch 22 gives partial inputs and no output numbers). So C9 is locked at the
**sub-formula level** -- each algebraic step verified exactly against ONENGOUT.BAS
(engine thrust, windmill drag, AVT lift slope, EFFECTV, EF chart, density ratio) -- plus
**integration/physics closure** (recovery, yaw-rate peak, time-step convergence) and a
**refactor-parity** check that the shared v-tail helpers match SELECT's. The printed twin
oracle + an ``examples/twin_turboprop.project.json`` fixture are deferred items.

Reference: ONENGOUT.BAS (Appendix C pp. 492-494); Reference 1 Ch 11 pp. 87-88;
FAA User's Guide (DOT/FAA/AR-96/46) Ch 22.
"""

import math
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import EngineLayout, OneEngineOutInput, io  # noqa: E402
from farloads.constants import KT_TO_FPS_SUITE, standard_atmosphere  # noqa: E402
from farloads.models import MassCase, MassResult  # noqa: E402
from farloads.modules import one_engine_out as oeo  # noqa: E402
from farloads.modules import select as sel  # noqa: E402
from farloads.modules._vtail import (  # noqa: E402
    large_deflection_factor,
    rudder_effectiveness,
    vtail_lift_slope,
)

REL = 1e-3  # ±0.1%

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _twin():
    """The GA6 example turned into a synthetic twin so ONENGOUT has a failed engine,
    mass/inertia and a 50%-MAC v-tail station (no oracle -- a closure fixture)."""
    p = io.load_project(_GA)
    e = p.engines[0]
    p.engines = [replace(e, engine_designation="LEFT", engine_cg=(22.0, -60.0, -10.0)),
                 replace(e, engine_designation="RIGHT", engine_cg=(22.0, 60.0, -10.0))]
    p.engine_layout = EngineLayout.TWIN_WING
    p.vtail_loads.xv50 = p.vtail_loads.xv25 + 12.0
    p.mass = MassResult(cases=[MassCase(name="gross", weight_lb=3400, cg_x=110.0, izz=3.0e7)])
    p.one_engine_out = OneEngineOutInput(
        thrust_decay_time_s=0.5, windmill_drag_time_s=1.5,
        rudder_travel_time_s=0.3, time_step_s=0.05)
    return p


# --------------------------------------------------------------------------- #
# Sub-formula exactness (each step locked to ONENGOUT.BAS)
# --------------------------------------------------------------------------- #
def test_thrust_and_windmill_drag_formula():
    """ONENGOUT.BAS 205-208: thrust = MAXHP*550*.85/VTFPS; drag = .85*.232*rho*VTFPS^2*DIA^2."""
    p = _twin()
    c = oeo._case_inputs(p, 150.0)
    thrust, drag, vtfps = oeo.engine_thrust_and_drag(c)
    sigma = standard_atmosphere(c.alt_ft)[1]
    exp_vtfps = (c.v_kt / sigma ** 0.5) * KT_TO_FPS_SUITE
    exp_thrust = c.maxhp * 550.0 * 0.85 / exp_vtfps
    exp_drag = 0.85 * 0.232 * (0.002378 * sigma) * exp_vtfps ** 2 * c.dia_ft ** 2
    assert math.isclose(vtfps, exp_vtfps, rel_tol=1e-12)
    assert math.isclose(thrust, exp_thrust, rel_tol=1e-12), thrust
    assert math.isclose(drag, exp_drag, rel_tol=1e-12), drag


def test_vtail_lift_slope_formula():
    """AVT = 2*pi/(1 + 2/ARVT)."""
    assert math.isclose(vtail_lift_slope(1.5), 2.0 * math.pi / (1.0 + 2.0 / 1.5), rel_tol=1e-12)


def test_rudder_effectiveness_cubic():
    """EFFECTV = .014844 + 2.7358 r - 4.4679 r^2 + 3.0306 r^3 (r = SR/SV)."""
    r = 0.27
    exp = 0.014844 + 2.7358 * r - 4.4679 * r ** 2 + 3.0306 * r ** 3
    assert math.isclose(rudder_effectiveness(r), exp, rel_tol=1e-12)


# --------------------------------------------------------------------------- #
# Refactor parity: the shared helpers must equal SELECT's private ones
# --------------------------------------------------------------------------- #
def test_shared_helpers_match_select():
    p = io.load_project(_GA)
    vt = p.vtail_loads
    assert math.isclose(sel._avt(vt), vtail_lift_slope(vt.aspect_ratio_vtail), rel_tol=1e-12)
    assert math.isclose(sel._effectv(vt),
                        rudder_effectiveness(vt.rudder_area_sqft / vt.vtail_area_sqft), rel_tol=1e-12)
    for defl in (0.0, 5.0, 12.0, 25.0):
        for ratio in (0.0, 0.1, 0.2, 0.35, 0.5):
            assert math.isclose(sel._ef(defl, ratio),
                                large_deflection_factor(defl, ratio), rel_tol=1e-12)


# --------------------------------------------------------------------------- #
# Integration / physics closure
# --------------------------------------------------------------------------- #
def test_recovery_and_peak_yaw_rate():
    """A controllable case recovers (THETA swings back through 0) and the yaw rate
    peaks before the rudder brings it back -- the basic 23.367 transient shape."""
    p = _twin()
    rows, s = oeo.simulate(oeo._case_inputs(p, float(p.speeds.chosen_vc)))
    assert s.recovered
    assert rows[-1].theta < 0.0                       # swung back through zero
    assert s.max_tail_load_lb > 0.0
    assert s.max_yaw_rate_deg_s > 0.0
    peak = max(range(len(rows)), key=lambda i: rows[i].theta_dot)
    assert rows[peak].theta_dot < rows[0].theta_dot or rows[-1].theta_dot < rows[peak].theta_dot
    assert math.isclose(rows[peak].theta_dot, s.max_yaw_rate_deg_s, rel_tol=REL)


def test_time_step_convergence():
    """Halving the Euler step changes the max tail load by only a few percent
    (first-order integration converges)."""
    p = _twin()
    _, s_coarse = oeo.simulate(oeo._case_inputs(p, float(p.speeds.chosen_vc)))
    p.one_engine_out.time_step_s = 0.025
    _, s_fine = oeo.simulate(oeo._case_inputs(p, float(p.speeds.chosen_vc)))
    assert math.isclose(s_coarse.max_tail_load_lb, s_fine.max_tail_load_lb, rel_tol=0.05), (
        s_coarse.max_tail_load_lb, s_fine.max_tail_load_lb)


def test_below_vmc_flagged_not_recovered():
    """At a low speed the rudder can't arrest the yaw; the run is bounded and flagged."""
    p = _twin()
    _, s = oeo.simulate(oeo._case_inputs(p, 50.0))
    assert not s.recovered
    assert s.time_to_recovery_s <= oeo._MAX_SIM_TIME_S


# --------------------------------------------------------------------------- #
# run() structure + time_history + io round-trip
# --------------------------------------------------------------------------- #
def test_run_structure():
    p = _twin()
    mr = oeo.run(p)
    assert mr.module == "one_engine_out"
    assert [c.title for c in mr.conditions] == [
        "One engine out — VC (ultimate)", "One engine out — VD (limit)", "One engine out — VS"]
    labels = {v.label for v in mr.conditions[0].values}
    assert {"Max tail load", "Max yawing velocity", "Engine thrust", "Windmill drag"} <= labels


def test_time_history_matches_case():
    p = _twin()
    rows = oeo.time_history(p, "VC (ultimate)")
    rows2, _ = oeo.simulate(oeo._case_inputs(p, float(p.speeds.chosen_vc)))
    assert len(rows) == len(rows2)
    assert math.isclose(rows[-1].lt, rows2[-1].lt, rel_tol=1e-12)


def test_missing_slice_raises():
    p = _twin()
    p.one_engine_out = None
    try:
        oeo.run(p)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_io_roundtrip():
    """The one_engine_out slice (and VTailLoadsInput.xv50) round-trip; an older file
    without the slice still loads (None)."""
    p = io.load_project(_GA)
    assert io.project_from_dict(io.project_to_dict(p)).one_engine_out is None
    p.one_engine_out = OneEngineOutInput(thrust_decay_time_s=0.5, windmill_drag_time_s=1.0,
                                         rudder_travel_time_s=0.3, failed_engine_index=1)
    p.vtail_loads.xv50 = 270.0
    p2 = io.project_from_dict(io.project_to_dict(p))
    assert p2.one_engine_out.thrust_decay_time_s == 0.5
    assert p2.one_engine_out.failed_engine_index == 1
    assert p2.vtail_loads.xv50 == 270.0


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
