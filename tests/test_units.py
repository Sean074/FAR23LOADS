"""Unit-system conversion tests.

The point of the SI toggle is that it is *purely* a presentation layer: SI
inputs converted to Imperial must produce the same loads as the Imperial run,
and the reported numbers must match the Imperial result times the documented
conversion factor. These tests pin both properties.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import (  # noqa: E402
    UnitSystem,
    convert_results,
    run_all,
    to_display,
    to_imperial,
)
from farloads.units import _convert_value  # noqa: E402
from farloads.models import LoadValue  # noqa: E402
from test_engine import io520bb, turboprop  # noqa: E402


def _value(result, label):
    for v in result.values:
        if v.label == label:
            return v
    raise KeyError(label)


def test_imperial_is_identity():
    inp = turboprop()
    assert to_imperial(inp, UnitSystem.IMPERIAL) is inp
    results = run_all(inp)
    assert convert_results(results, UnitSystem.IMPERIAL) is results


def test_si_round_trip_reproduces_imperial():
    # Express the Imperial example in SI, feed it back through to_imperial, and
    # the loads must match the native Imperial run to floating-point precision.
    imp = io520bb()
    si = to_imperial(imp, UnitSystem.IMPERIAL)  # no-op, just the same object
    # Build an SI-valued input by converting each field to display units.
    si_input = _to_si_input(imp)
    back = to_imperial(si_input, UnitSystem.SI)

    r_native = run_all(imp)
    r_round = run_all(back)
    for a, b in zip(r_native, r_round):
        for va, vb in zip(a.values, b.values):
            assert math.isclose(va.value, vb.value, rel_tol=1e-9, abs_tol=1e-6), va.label


def test_result_force_converts_to_newtons():
    r = run_all(io520bb())[0]  # 23.361(a)(1)
    vload_lb = _value(r, "Vertical down load").value
    si = convert_results([r], UnitSystem.SI)[0]
    vload_n = _value(si, "Vertical down load").value
    assert _value(si, "Vertical down load").units == "N"
    assert math.isclose(vload_n, vload_lb * 4.4482216152605, rel_tol=1e-9)


def test_result_moment_converts_to_newton_metres():
    v = _convert_value(LoadValue("Engine mount torque", -100.0, "ft-lb"))
    assert v.units == "N·m"
    assert math.isclose(v.value, -135.58179483314, rel_tol=1e-9)


def test_dimensionless_passes_through():
    v = _convert_value(LoadValue("Vertical load factor", 2.85, ""))
    assert v.units == "" and v.value == 2.85


def test_to_display_inverts_to_imperial_scalar():
    for kind, val in [("weight", 505.0), ("length", 84.0), ("torque", 1970.0), ("power", 285.0)]:
        si = to_display(val, kind, UnitSystem.SI)
        assert math.isclose(si / _factor(kind), val, rel_tol=1e-12)


# --- helpers ---------------------------------------------------------------- #
def _factor(kind):
    from farloads.units import SI_PER_IMPERIAL
    return SI_PER_IMPERIAL[kind]


def _to_si_input(imp):
    """Convert an Imperial EngineInput into an equivalent SI-valued one."""
    from dataclasses import replace

    def w(v):
        return None if v is None else to_display(v, "weight", UnitSystem.SI)

    def l(v):
        return None if v is None else to_display(v, "length", UnitSystem.SI)

    def tq(v):
        return None if v is None else to_display(v, "torque", UnitSystem.SI)

    def p(v):
        return None if v is None else to_display(v, "power", UnitSystem.SI)

    rotors = [replace(r, diameter_in=l(r.diameter_in), weight_lb=w(r.weight_lb)) for r in imp.rotors]
    return replace(
        imp,
        engine_weight_lb=w(imp.engine_weight_lb),
        prop_weight_lb=w(imp.prop_weight_lb),
        hub_weight_lb=w(imp.hub_weight_lb),
        engine_cg=tuple(l(c) for c in imp.engine_cg),
        prop_cg=tuple(l(c) for c in imp.prop_cg),
        prop_diameter_in=l(imp.prop_diameter_in),
        max_engine_torque=tq(imp.max_engine_torque),
        cruise_torque=tq(imp.cruise_torque),
        takeoff_hp=p(imp.takeoff_hp),
        max_cont_hp=p(imp.max_cont_hp),
        rotors=rotors,
    )


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
