"""Formula-closure tests for the optional FAR 25 supplemental engine cases.

These cover the additive 14 CFR 25.361 / 25.371 conditions enabled by
``Project.include_far25`` (turbopropeller only). No McMaster worked example exists
for Part 25, so the checks are hand-calc closures traced to
``reference/14CFR_Part25_engine_torque.md`` -- not a printed oracle. The FAR 23
path stays oracle-locked in ``test_engine.py`` and must be unchanged by this flag.

The flag now appends only the three *non-duplicative* cases (sudden stoppage +
1g vertical, max engine acceleration torque, and the A2-vertical gyro). After the
AC 23-19A correction the FAR 25 torque cases 25.361(a)(1)(i)/(ii)/(iii) became
exact duplicates of the corrected 23.361(a)(1)/(a)(2)/(a)(3) and were removed.
"""

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from dataclasses import replace

from fixtures import io520bb, turboprop  # noqa: E402
from helpers import value_of  # noqa: E402

from sloads import EngineLayout, Project, run_all
from sloads import io as fio
from sloads.modules import engine as calc

TOL = 1e-3  # ±0.1% relative


def test_far25_off_by_default_is_far23_only():
    # The opt-in flag defaults off; the FAR 23 output (6 turboprop conditions) is
    # unchanged, and turning it on appends the three supplemental FAR 25 cases.
    assert len(run_all(turboprop())) == 6
    assert len(run_all(turboprop(), include_far25=True)) == 9


def test_far25_recip_adds_nothing():
    # 25.361(a)(2) is turbine-scoped, so reciprocating engines get no FAR 25 cases.
    assert calc.run_far25(io520bb()) == []
    assert len(run_all(io520bb(), include_far25=True)) == 3


def test_far25_supplement_drops_duplicate_torque_cases():
    # The reduced supplement no longer re-emits the corrected-FAR-23 torque cases:
    # only the genuinely additive references remain.
    refs = [c.far_reference for c in calc.run_far25(turboprop())]
    assert refs == ["25.361(a)(3)(i)", "25.361(a)(3)(ii)", "25.371"]
    assert "25.361(a)(1)(i)" not in refs


def test_25_361_a3i_stoppage_plus_1g():
    # Same stoppage torque as 23.361(b)(1), now with a simultaneous 1g vertical.
    f23 = value_of(calc.condition_361_b1(turboprop()), "mx_mount_torque")
    r = calc.condition_25_361_a3i(turboprop())
    assert value_of(r, "mx_mount_torque") == f23  # identical torque
    assert math.isclose(value_of(r, "fz_vertical"), 450.0, rel_tol=TOL)  # 1g*450


def test_25_361_a3ii_defaults_to_max_engine_torque():
    # No separate accelerating torque supplied -> falls back to max engine torque,
    # flagged via the note so the assumption is visible.
    r = calc.condition_25_361_a3ii(turboprop())
    assert math.isclose(value_of(r, "mx_mount_torque"), -1970.0, rel_tol=TOL)
    assert r.note and "defaulted" in r.note


def test_25_361_a3ii_uses_supplied_accel_torque():
    inp = replace(turboprop(), max_accel_torque=2500.0)
    r = calc.condition_25_361_a3ii(inp)
    assert math.isclose(value_of(r, "mx_mount_torque"), -2500.0, rel_tol=TOL)
    assert not r.note  # ConditionResult.note is str; "" means no note


def test_25_371_uses_a2_load_factor_not_fixed_25g():
    # The simultaneous vertical uses the project's limit load factor (3.8 -> 1710 lb),
    # not the fixed 2.5g of the FAR 23 gyro case.
    r = calc.condition_25_371(turboprop())
    assert math.isclose(value_of(r, "vertical_limit_load_a2_load"), 1710.0, rel_tol=TOL)


def test_25_371_gyro_moments_match_far23_fixed_rates():
    # Conservative stand-in reuses the fixed 23.371(b) rates -> identical Myy/Mzz.
    f23 = calc.condition_371_b(turboprop())
    f25 = calc.condition_25_371(turboprop())
    assert math.isclose(
        value_of(f25, "myy_due_to_2_5_rad_s_yaw_pm"),
        value_of(f23, "myy_due_to_2_5_rad_s_yaw_pm"),
        rel_tol=TOL,
    )


def test_25_371_no_declared_rates_no_warning():
    # Default (no advisory rates): fixed FAR 23.371(b) stand-in, no under-prediction
    # warning -- the GA/oracle path is untouched.
    r = calc.condition_25_371(turboprop())
    assert "UNDER-PRED" not in r.note.upper()
    assert "conservative concept stand-in" in r.note.lower()


def test_25_371_declared_rates_below_standin_no_warning():
    # Declaring rates at or below the fixed stand-in leaves the result conservative:
    # no warning, moment unchanged.
    inp = replace(turboprop(), design_yaw_rate_rad_s=2.0, design_pitch_rate_rad_s=0.8)
    base = calc.condition_25_371(turboprop())
    r = calc.condition_25_371(inp)
    assert "UNDER-PRED" not in r.note.upper()
    assert value_of(r, "myy_due_to_2_5_rad_s_yaw_pm") == value_of(base, "myy_due_to_2_5_rad_s_yaw_pm")


def test_25_371_declared_rate_above_standin_warns_but_keeps_value():
    # A declared yaw rate above 2.5 rad/s flags the result as under-predicting, but
    # the moment stays at the fixed stand-in value (advisory rate, not a re-derivation).
    base = calc.condition_25_371(turboprop())
    inp = replace(turboprop(), design_yaw_rate_rad_s=3.5)  # 3.5 > 2.5
    r = calc.condition_25_371(inp)
    assert r.note.upper().startswith("WARNING")
    assert "UNDER-PRED" in r.note.upper()
    assert "yaw 3.5 > 2.5" in r.note
    # Moment value is identical to the no-override fixed stand-in.
    assert value_of(r, "myy_due_to_2_5_rad_s_yaw_pm") == value_of(base, "myy_due_to_2_5_rad_s_yaw_pm")
    assert value_of(r, "mzz_due_to_1_rad_s_pitch_pm") == value_of(base, "mzz_due_to_1_rad_s_pitch_pm")


def test_25_371_declared_pitch_rate_above_standin_warns():
    inp = replace(turboprop(), design_pitch_rate_rad_s=1.5)  # 1.5 > 1.0
    r = calc.condition_25_371(inp)
    assert r.note.upper().startswith("WARNING")
    assert "pitch 1.5 > 1" in r.note


def test_25_371_advisory_rates_round_trip():
    # New optional EngineInput fields survive JSON round-trip (schema v23).
    project = Project(
        name="tp",
        engines=[replace(turboprop(), design_yaw_rate_rad_s=3.5, design_pitch_rate_rad_s=1.2)],
        engine_layout=EngineLayout.SINGLE_NOSE, include_far25=True,
    )
    back = fio.project_from_dict(fio.project_to_dict(project))
    assert back.engines[0].design_yaw_rate_rad_s == 3.5
    assert back.engines[0].design_pitch_rate_rad_s == 1.2
    r = [c for c in calc.run(back).conditions if c.far_reference == "25.371"][0]
    assert r.note.upper().startswith("WARNING")


def test_project_flag_appends_far25():
    project = Project(
        name="tp", engines=[turboprop()],
        engine_layout=EngineLayout.SINGLE_NOSE, include_far25=True,
    )
    mr = calc.run(project)
    refs = [c.far_reference for c in mr.conditions]
    assert "25.361(a)(3)(ii)" in refs and "25.371" in refs
    assert len(mr.conditions) == 9


def test_far25_json_round_trips():
    project = Project(
        name="tp", engines=[replace(turboprop(), max_accel_torque=2500.0)],
        engine_layout=EngineLayout.SINGLE_NOSE, include_far25=True,
    )
    back = fio.project_from_dict(fio.project_to_dict(project))
    assert back.include_far25 is True
    assert back.engines[0].max_accel_torque == 2500.0
    assert len(calc.run(back).conditions) == 9


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
