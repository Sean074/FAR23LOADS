"""Whole-project Imperial<->SI display conversion (Project JSON Editor page).

Guards the two failure modes that matter for a field-name-driven converter:
a mass field (weight_lb, lbm) and a force field (load_lb, lbf) must use
*different* factors even though both end in "_lb", and the round trip through
project_dict_to_display/project_dict_to_imperial must be lossless (so Apply on
the editor page never silently drifts a project's numbers). Airspeed/altitude
must never be touched, per CLAUDE.md's aviation-standard-units decision.
"""

import math
import os

from farloads import UnitSystem, io
from farloads.units import project_dict_to_display, project_dict_to_imperial

_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def _round_trip_close(a, b, path=""):
    if isinstance(a, dict):
        for k in a:
            _round_trip_close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        for i, (x, y) in enumerate(zip(a, b)):
            _round_trip_close(x, y, f"{path}[{i}]")
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        assert math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9), f"{path}: {a} != {b}"
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


def test_mass_and_force_lb_fields_use_different_factors():
    # A pounds-mass weight (0.45359237 kg/lb) must not be confused with a
    # pounds-force load (4.4482216152605 N/lb) -- same "_lb" suffix, ~9.8x
    # different factor. Regression for the exact bug class this table exists
    # to prevent.
    d = {"weight_lb": 100.0, "load_lb": 100.0}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert math.isclose(si["weight_lb"], 45.359237, rel_tol=1e-9)
    assert math.isclose(si["load_lb"], 444.82216152605, rel_tol=1e-9)


def test_airspeed_and_altitude_are_never_converted():
    d = {"vh_kt": 150.0, "altitude_ft": 8000.0, "shoulder_altitude_ft": 12000.0}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert si == d


def test_unknown_field_passes_through_unconverted():
    d = {"some_future_field": 42.0}
    assert project_dict_to_display(d, UnitSystem.SI) == d


def test_imperial_is_a_no_op():
    d = {"weight_lb": 100.0, "engine_cg": [1.0, 2.0, 3.0]}
    assert project_dict_to_display(d, UnitSystem.IMPERIAL) == d
    assert project_dict_to_imperial(d, UnitSystem.IMPERIAL) == d


def test_round_trip_is_lossless_on_example_projects():
    for fname in ("ga6_normal.project.json", "dhc8_dash8.project.json", "concept_heavy.project.json"):
        project = io.load_project(os.path.join(_EXAMPLES, fname))
        original = io.project_to_dict(project)
        si = project_dict_to_display(original, UnitSystem.SI)
        back = project_dict_to_imperial(si, UnitSystem.SI)
        _round_trip_close(original, back)


def test_engine_cg_vector_converts_as_length():
    d = {"engine_cg": [10.0, 0.0, -5.0]}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert si["engine_cg"] == [254.0, 0.0, -127.0]
    back = project_dict_to_imperial(si, UnitSystem.SI)
    assert back["engine_cg"] == d["engine_cg"]


if __name__ == "__main__":
    test_mass_and_force_lb_fields_use_different_factors()
    test_airspeed_and_altitude_are_never_converted()
    test_unknown_field_passes_through_unconverted()
    test_imperial_is_a_no_op()
    test_round_trip_is_lossless_on_example_projects()
    test_engine_cg_vector_converts_as_length()
    print("OK")
