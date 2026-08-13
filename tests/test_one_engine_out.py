"""One engine out vertical-tail loads (Step C9): ONENGOUT.BAS port (FAR 23.367).

The printed Appendix B (10-place twin turboprop) one-engine-out oracle is **absent**
from the bundled references (Reference 1 carries only the Appendix A GA single; the FAA
User's Guide Ch 22 gives partial inputs and no output numbers). So C9 is locked at the
**sub-formula level** -- each algebraic step verified exactly against ONENGOUT.BAS
(engine thrust, windmill drag, AVT lift slope, EFFECTV, EF chart, density ratio) -- plus
**integration/physics closure** (recovery, yaw-rate peak, time-step convergence) and a
**refactor-parity** check that the shared v-tail helpers match SELECT's. The printed twin
oracle stays a deferred item.

The module was unrunnable on shipped data until 2026-08-13: ``atr42_100`` and
``dhc8_dash8`` entered the ``one_engine_out`` slice but no engine horsepower, so the whole
simulation path was exercised only on constructed inputs (backlog "ONENGOUT fixture data";
the ``tail_mass`` gap was the same class). Both fixtures now carry take-off and
max-continuous shaft power, and :func:`test_the_shipped_turboprops_execute_onengout` is the
gate that keeps the module's own deliverable path covered by CI.

Reference: ONENGOUT.BAS (Appendix C pp. 492-494); Reference 1 Ch 11 pp. 87-88;
FAA User's Guide (DOT/FAA/AR-96/46) Ch 22.
"""

import math
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import EngineLayout, OneEngineOutInput, io  # noqa: E402
from sloads.constants import KT_TO_FPS_SUITE, standard_atmosphere  # noqa: E402
from sloads.models import MassCase, MassResult  # noqa: E402
from sloads.modules import one_engine_out as oeo  # noqa: E402
from sloads.modules import select as sel  # noqa: E402
from sloads.modules._vtail import (  # noqa: E402
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
    keys = {v.key for v in mr.conditions[0].values}
    assert {"max_tail_load", "max_yawing_velocity", "engine_thrust", "windmill_drag"} <= keys


def test_safety_factors_by_failure_mode():
    """M1-5 (review T7): the 23.367(a)(2) VC loads are ultimate (SF 1.0 -- limit
    treated as ultimate); the (a)(1) VD fuel-flow case and the VS (VMC substitute)
    case are limit (SF 1.5). See Ref 1 Ch 11 p87 / 14 CFR 23.367(a)(1)-(2)."""
    p = _twin()
    mr = oeo.run(p)
    sf = {c.title: c.safety_factor for c in mr.conditions}
    assert sf["One engine out — VC (ultimate)"] == 1.0   # 23.367(a)(2) turbine failure -> ultimate
    assert sf["One engine out — VD (limit)"] == 1.5      # 23.367(a)(1) fuel-flow -> limit
    assert sf["One engine out — VS"] == 1.5              # VMC substitute -> limit
    # The regulatory basis is carried on each condition's note.
    vc = next(c for c in mr.conditions if c.title.endswith("VC (ultimate)"))
    assert "23.367(a)(2)" in vc.note and "ULTIMATE" in vc.note


def test_load_case_owns_sf_and_speed_range():
    """The SF is an attribute of the case definition (its LIMIT/ULTIMATE
    classification), not the speed; the case also carries the speed range it is
    considered over, and is evaluated at the range's critical (high) end."""
    p = _twin()
    cases = {lc.label: lc for lc in oeo._load_cases(p, p.one_engine_out)}
    vc, vd, vs = cases["VC (ultimate)"], cases["VD (limit)"], cases["VS"]
    # SF follows the case's classification, not its speed.
    assert (vc.load_class, vc.safety_factor) == ("ULTIMATE", 1.0)   # 23.367(a)(2)
    assert (vd.load_class, vd.safety_factor) == ("LIMIT", 1.5)      # 23.367(a)(1) -- a failure, still 1.5
    assert (vs.load_class, vs.safety_factor) == ("LIMIT", 1.5)
    # The case defines a speed range; it is evaluated at the critical (high) end.
    assert vc.v_hi_kt == float(p.speeds.chosen_vc)
    assert vd.v_hi_kt == float(p.speeds.chosen_vd)
    assert vc.v_lo_kt <= vc.v_hi_kt and vd.v_lo_kt <= vd.v_hi_kt  # VMC floor <= ceiling


def test_rendered_loads_are_ultimate_with_correct_sf():
    """The rendered deliverable carries the -ULT marker and each case's SF: the VC
    ultimate case at SF 1.0, the VD/VS limit cases at SF 1.5 (M1-5)."""
    from sloads import report
    p = _twin()
    rows = {r["Condition"]: r for r in report.load_cases_to_rows(oeo.run(p).conditions)}
    vc = rows["one engine out — VC (ultimate)"]
    vd = rows["one engine out — VD (limit)"]
    assert vc["SF"] == "1" and vd["SF"] == "1.5"
    # Load columns carry the ULTIMATE marker in their units string, not a bare limit load.
    load_cols = [k for k in vc if "load" in k.lower() or "moment" in k.lower() or "Thrust" in k]
    assert load_cols and all("-ULT" in k for k in load_cols)


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


#: The shipped fixtures that can execute ONENGOUT, with the engine each carries and
#: its EASA TCDS IM.E.041 issue 07 (20 Dec 2023) §5 sea-level ratings, converted from
#: the certificated kW at 745.7 W/shp and rounded to the nearest 10 shp:
#:
#:   PW120  max take-off 1491 kW = 1999.5 shp -> 2000; max continuous 1268 kW = 1700.4 -> 1700
#:   PW121  max take-off 1603 kW = 2149.7 shp -> 2150; max continuous 1454 kW = 1949.8 -> 1950
#:
#: Both fields are entered rather than left to ``_engine_power``'s fallback: which
#: rating a case runs at is the user's choice (``use_takeoff_power``), and a fallback
#: makes that choice silently when only one field is present.
_TURBOPROP_FIXTURES = {
    "atr42_100.project.json": (2000.0, 1700.0),
    "dhc8_dash8.project.json": (2150.0, 1950.0),
}


def test_the_shipped_turboprops_execute_onengout():
    """**The fixture-coverage gate.** ONENGOUT must run on shipped data, not only on
    constructed inputs — every engine carries both ratings, every speed case produces a
    positive tail load, and the high-speed cases recover.

    The VS case is expected NOT to recover on either airplane: full asymmetric power at
    the clean stall speed is below VMC, which is a real result and is stated in band on
    the case (``NOT recovered ... likely below VMC``) rather than suppressed. Asserted,
    so that a change which quietly made VS recover has to say so here."""
    for name, (takeoff, max_cont) in _TURBOPROP_FIXTURES.items():
        p = io.load_project(os.path.join(_EXAMPLES, name))
        for e in p.engines:
            assert e.takeoff_hp == takeoff, (name, e.engine_designation, e.takeoff_hp)
            assert e.max_cont_hp == max_cont, (name, e.engine_designation, e.max_cont_hp)

        result = oeo.run(p)
        titles = [c.title for c in result.conditions]
        assert len(titles) == 3, (name, titles)
        for cond in result.conditions:
            values = {v.label: v.value for v in cond.values}
            assert values["Max tail load"] > 0.0, (name, cond.title)
            assert values["Engine thrust"] > 0.0 and values["Windmill drag"] > 0.0, (
                name, cond.title)
            recovered = "NOT recovered" not in cond.note
            assert recovered == (not cond.title.endswith("VS")), (name, cond.title)


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
