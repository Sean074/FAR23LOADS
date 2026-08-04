"""Shared test input builders (M4-12a).

These used to live in ``test_engine.py``, which seven other test modules then
imported -- making a test module double as a library and coupling unrelated
suites to ``test_engine``'s import side effects. They are plain builders here;
no test module imports another test module. Lookup helpers live next door in
:mod:`helpers`.

Both examples are the manual's worked engine inputs (Reference 1 Appendix A
p131 for the reciprocating case); the figures they are asserted against stay in
the tests that use them, with their page citations.
"""

from sloads import EngineInput, EngineType, Rotor, RotorType


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
