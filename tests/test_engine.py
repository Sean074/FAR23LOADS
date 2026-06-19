"""Validate the calculation core against the FAR 23 LOADS manual appendices.

The reciprocating reference is the Continental IO-520-BB example printed in the
manual (full.txt:24910-25028). The comparison values below are the manual's
*printed* figures; per Decision 3 ("modernize the math", pi -> math.pi) they are
matched with an engineering tolerance of ±0.1% (rel_tol=1e-3) rather than exact
equality, so genuine drift still fails loudly while the pi modernization does not.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import EngineInput, EngineType, Rotor, RotorType, run_all
from farloads.modules import engine as calc

# Engineering tolerance for matching the manual's printed figures (see Decision 3).
TOL = 1e-3  # ±0.1% relative


def _value(result, label):
    for v in result.values:
        if v.label == label:
            return v.value
    raise KeyError(label)


def io520bb() -> EngineInput:
    """The reciprocating worked example (Continental IO-520-BB)."""
    return EngineInput(
        engine_designation="CONTINENTAL IO-520-BB",
        prop_designation="HARTZELL",
        engine_type=EngineType.RECIPROCATING,
        limit_load_factor=3.8,
        engine_weight_lb=505,
        engine_cg=(22.0, 0.0, -10.0),
        prop_weight_lb=74,
        prop_diameter_in=84,
        prop_blades=3,
        takeoff_rpm=2700,
        max_cont_rpm=2500,
        prop_cg=(-10.0, 0.0, 93.022),  # XPROP chosen so combined XPP = 17.91
        takeoff_hp=285,
        max_cont_hp=265,
        cylinders=6,
    )


def test_derived_quantities():
    inp = io520bb()
    assert calc.combined_weight(inp) == 579  # integers, pi-independent
    assert math.isclose(calc.takeoff_torque(inp), 554.3884, rel_tol=TOL)
    assert math.isclose(calc.max_cont_torque(inp), 556.7227, rel_tol=TOL)
    assert calc.torque_factor(inp) == 1.33
    xpp, ypp, zpp = calc.combined_cg(inp)
    assert math.isclose(xpp, 17.91, abs_tol=0.01)


def test_361_a1():
    r = calc.condition_361_a1(io520bb())
    assert math.isclose(_value(r, "Vertical load factor"), 2.85, abs_tol=1e-9)
    assert math.isclose(_value(r, "Vertical down load"), 1650.15, rel_tol=TOL)
    assert math.isclose(_value(r, "Engine mount torque"), -554.3884, rel_tol=TOL)


def test_361_a2():
    r = calc.condition_361_a2(io520bb())
    assert math.isclose(_value(r, "Vertical down load"), 2200.2, rel_tol=TOL)
    assert math.isclose(_value(r, "Torque factor"), 1.33, abs_tol=1e-9)
    assert math.isclose(_value(r, "Max continuous torque"), 556.7227, rel_tol=TOL)
    assert math.isclose(_value(r, "Engine mount torque"), -740.4412, rel_tol=TOL)


def test_363():
    r = calc.condition_363(io520bb())
    assert math.isclose(_value(r, "Side load factor"), 1.33, abs_tol=1e-9)
    assert math.isclose(_value(r, "Side load"), 770.07, rel_tol=TOL)


def test_reciprocating_runs_three_conditions():
    assert len(run_all(io520bb())) == 3


def turboprop() -> EngineInput:
    """A turboprop input exercising all six conditions (uses manual's gyro example)."""
    return EngineInput(
        engine_designation="PT6",
        prop_designation="HARTZELL",
        engine_type=EngineType.TURBOPROP,
        limit_load_factor=3.8,
        engine_weight_lb=400,
        engine_cg=(20.0, 0.0, 0.0),
        prop_weight_lb=50,
        prop_diameter_in=101,
        prop_blades=4,
        takeoff_rpm=2200,
        max_cont_rpm=2200,
        prop_cg=(-10.0, 0.0, 0.0),
        max_engine_torque=1970,
        cruise_torque=1800,
        hub_weight_lb=0.0,
        stop_time_s=0.3,
        rotors=[
            Rotor(diameter_in=10, weight_lb=19.34, max_rpm=-33750, rotor_type=RotorType.TURBINE),
            Rotor(diameter_in=9, weight_lb=15.66, max_rpm=33000, rotor_type=RotorType.TURBINE),
        ],
    )


def test_prop_inertia_matches_manual():
    # Manual hand calc: IProp = 50/32.174*(50.5/12)^2/3 = 9.174 slug-ft^2
    inp = turboprop()
    assert math.isclose(calc._prop_inertia(inp), 9.174, abs_tol=1e-2)


def test_measured_prop_inertia_overrides_geometry():
    from dataclasses import replace
    inp = replace(turboprop(), prop_inertia=12.5)
    assert calc._prop_inertia(inp) == 12.5  # geometry (9.174) ignored


def test_measured_rotor_inertia_overrides_geometry():
    from dataclasses import replace
    base = turboprop()
    geom = calc._rotor_inertia(base.rotors[0])
    measured = replace(base.rotors[0], inertia=0.5)
    assert calc._rotor_inertia(measured) == 0.5
    assert not math.isclose(geom, 0.5)  # the disk approximation differs


def test_gyro_thrust_matches_manual():
    # Manual: THRUST = 1970 * 230.38 / 101.2 = 4484.7 lb
    r = calc.condition_371_b(turboprop())
    assert math.isclose(_value(r, "Max continuous thrust"), 4484.7, abs_tol=1.0)


def test_turboprop_runs_six_conditions():
    assert len(run_all(turboprop())) == 6


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
