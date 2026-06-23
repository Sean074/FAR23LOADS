"""Formula-closure tests for the optional FAR 25 engine cases.

These cover the additive 14 CFR 25.361 / 25.371 conditions enabled by
``Project.include_far25`` (turbopropeller only). No McMaster worked example exists
for Part 25, so the checks are hand-calc closures traced to
``reference/14CFR_Part25_engine_torque.md`` -- not a printed oracle. The FAR 23
path stays oracle-locked in ``test_engine.py`` and must be unchanged by this flag.
"""

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from dataclasses import replace

from farloads import EngineLayout, Project, run_all
from farloads import io as fio
from farloads.modules import engine as calc
from test_engine import _value, io520bb, turboprop

TOL = 1e-3  # ±0.1% relative


def test_far25_off_by_default_is_far23_only():
    # The opt-in flag defaults off; the FAR 23 output (6 turboprop conditions) is
    # unchanged, and turning it on appends the six FAR 25 cases.
    assert len(run_all(turboprop())) == 6
    assert len(run_all(turboprop(), include_far25=True)) == 12


def test_far25_recip_adds_nothing():
    # 25.361(a)(2) is turbine-scoped, so reciprocating engines get no FAR 25 cases.
    assert calc.run_far25(io520bb()) == []
    assert len(run_all(io520bb(), include_far25=True)) == 3


def test_25_361_a1i_applies_125_to_takeoff():
    # 25.361(a)(1)(i): 1.25 x mean takeoff torque, 0.75 Nz vertical (450 lb combined).
    r = calc.condition_25_361_a1i(turboprop())
    assert math.isclose(_value(r, "Vertical load factor"), 2.85, abs_tol=1e-9)
    assert math.isclose(_value(r, "Vertical down load"), 1282.5, rel_tol=TOL)  # 2.85*450
    assert math.isclose(_value(r, "Engine mount torque"), -2462.5, rel_tol=TOL)  # -1.25*1970


def test_far23_corrected_takeoff_equals_far25_for_turboprop():
    # After the AC 23-19A correction, FAR 23.361(a)(1) also factors the takeoff
    # torque (1.25 for a turboprop), so it now coincides with 25.361(a)(1)(i):
    # both are 1.25 x mean takeoff torque (= 1.25 x 1970 = 2462.5).
    f23 = _value(calc.condition_361_a1(turboprop()), "Engine mount torque")
    f25 = _value(calc.condition_25_361_a1i(turboprop()), "Engine mount torque")
    assert math.isclose(f23, f25, rel_tol=TOL)
    assert math.isclose(f23, -2462.5, rel_tol=TOL)


def test_25_361_a1ii_max_continuous():
    # 25.361(a)(1)(ii): 1.25 x mean max-cont torque, full Nz vertical.
    r = calc.condition_25_361_a1ii(turboprop())
    assert math.isclose(_value(r, "Vertical down load"), 1710.0, rel_tol=TOL)  # 3.8*450
    assert math.isclose(_value(r, "Engine mount torque"), -2250.0, rel_tol=TOL)  # -1.25*1800


def test_25_361_a1iii_feather_malfunction():
    # 25.361(a)(1)(iii): 1.6 x takeoff torque at 1g.
    r = calc.condition_25_361_a1iii(turboprop())
    assert math.isclose(_value(r, "Vertical load factor"), 1.0, abs_tol=1e-9)
    assert math.isclose(_value(r, "Engine mount torque"), -3152.0, rel_tol=TOL)  # -1.6*1970


def test_25_361_a3i_stoppage_plus_1g():
    # Same stoppage torque as 23.361(b)(1), now with a simultaneous 1g vertical.
    f23 = _value(calc.condition_361_b1(turboprop()), "Engine mount torque")
    r = calc.condition_25_361_a3i(turboprop())
    assert _value(r, "Engine mount torque") == f23  # identical torque
    assert math.isclose(_value(r, "Vertical down load"), 450.0, rel_tol=TOL)  # 1g*450


def test_25_361_a3ii_defaults_to_max_engine_torque():
    # No separate accelerating torque supplied -> falls back to max engine torque,
    # flagged via the note so the assumption is visible.
    r = calc.condition_25_361_a3ii(turboprop())
    assert math.isclose(_value(r, "Engine mount torque"), -1970.0, rel_tol=TOL)
    assert r.note and "defaulted" in r.note


def test_25_361_a3ii_uses_supplied_accel_torque():
    inp = replace(turboprop(), max_accel_torque=2500.0)
    r = calc.condition_25_361_a3ii(inp)
    assert math.isclose(_value(r, "Engine mount torque"), -2500.0, rel_tol=TOL)
    assert r.note is None


def test_25_371_uses_a2_load_factor_not_fixed_25g():
    # The simultaneous vertical uses the project's limit load factor (3.8 -> 1710 lb),
    # not the fixed 2.5g of the FAR 23 gyro case.
    r = calc.condition_25_371(turboprop())
    assert math.isclose(_value(r, "Vertical limit-load (A2) load"), 1710.0, rel_tol=TOL)


def test_25_371_gyro_moments_match_far23_fixed_rates():
    # Conservative stand-in reuses the fixed 23.371(b) rates -> identical Myy/Mzz.
    f23 = calc.condition_371_b(turboprop())
    f25 = calc.condition_25_371(turboprop())
    assert math.isclose(
        _value(f25, "Myy due to 2.5 rad/s yaw (+/-)"),
        _value(f23, "Myy due to 2.5 rad/s yaw (+/-)"),
        rel_tol=TOL,
    )


def test_project_flag_appends_far25():
    project = Project(
        name="tp", engines=[turboprop()],
        engine_layout=EngineLayout.SINGLE_NOSE, include_far25=True,
    )
    mr = calc.run(project)
    refs = [c.far_reference for c in mr.conditions]
    assert "25.361(a)(1)(i)" in refs and "25.371" in refs
    assert len(mr.conditions) == 12


def test_far25_json_round_trips():
    project = Project(
        name="tp", engines=[replace(turboprop(), max_accel_torque=2500.0)],
        engine_layout=EngineLayout.SINGLE_NOSE, include_far25=True,
    )
    back = fio.project_from_dict(fio.project_to_dict(project))
    assert back.include_far25 is True
    assert back.engines[0].max_accel_torque == 2500.0
    assert len(calc.run(back).conditions) == 12


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
