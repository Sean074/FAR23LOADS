"""Validate WTESTIMA against the FAR 23 LOADS manual, Appendix A.

The worked example is the 6-place single-engine GA airplane whose estimated
weight report is printed in Appendix A p133 (HP 265, 6 seats, 3 hr endurance,
unpressurized 4-cycle recip). The original program prints every figure through
``INT(...)``, so the oracle values are exact integers and matched exactly; only
the dimensionless empty/take-off ratio is a truncated decimal.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import EngineWeightType, Project, WeightEstimationInput, WeightInput  # noqa: E402
from farloads.modules import weight_estimate as calc  # noqa: E402


def _raises_value_error(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def ga6_estimation() -> WeightEstimationInput:
    """Appendix A p133 inputs (6-place single, 265 hp, 4-cycle recip)."""
    return WeightEstimationInput(
        airplane="6 PLACE SINGLE ENGINE GENERAL AVIATION",
        max_continuous_hp=265,
        engines=1,
        seats=6,
        cruise_hours=3,
        baggage_lb=0,
        pressurized=False,
        engine_weight_type=EngineWeightType.RECIP_4CYCLE,
    )


def _value(results, label):
    for r in results:
        for v in r.values:
            if v.label == label:
                return v.value
    raise KeyError(label)


def test_summary_matches_manual():
    # Appendix A p133: MAX TAKE OFF WT 3468, USEFUL 1318, EMPTY 2150, ratio .62.
    r = calc.estimate(ga6_estimation())
    assert _value(r, "Max take-off weight") == 3468
    assert _value(r, "Useful load") == 1318
    assert _value(r, "Empty weight") == 2150
    assert _value(r, "Empty/take-off ratio") == 0.62
    assert _value(r, "Options & miscellaneous") == 99


def test_structure_group_matches_manual():
    # Appendix A p133 structure breakdown.
    r = calc.estimate(ga6_estimation())
    assert _value(r, "Wing") == 359
    assert _value(r, "Fuselage") == 340
    assert _value(r, "Tail") == 81
    assert _value(r, "Nacelle") == 50
    assert _value(r, "Landing gear") == 198
    assert _value(r, "Controls") == 52
    assert _value(r, "Total structure") == 1081


def test_powerplant_group_matches_manual():
    # Appendix A p133: installed 490 (prop 83), fuel sys 52, exhaust 72,
    # other 86, total powerplant 700.
    r = calc.estimate(ga6_estimation())
    assert _value(r, "Engine installed (incl. propeller)") == 490
    assert _value(r, "Propeller (included above)") == 83
    assert _value(r, "Fuel system") == 52
    assert _value(r, "Exhaust") == 72
    assert _value(r, "Other engine details") == 86
    assert _value(r, "Total powerplant") == 700


def test_systems_group_matches_manual():
    # Appendix A p133 systems breakdown; single-engine "misc" prints 0
    # (the program prints an unset variable there -- preserved quirk).
    r = calc.estimate(ga6_estimation())
    assert _value(r, "Instruments & nav equip") == 15
    assert _value(r, "Pneumatics") == 3
    assert _value(r, "Electrical") == 83
    assert _value(r, "Electronics") == 0
    assert _value(r, "Furnishings & equipment") == 152
    assert _value(r, "Environmental & anti-ice") == 10
    assert _value(r, "Misc other system wt") == 0
    assert _value(r, "Total systems weight") == 268


def test_run_requires_weight_slice():
    assert _raises_value_error(lambda: calc.run(Project(name="empty")))
    assert _raises_value_error(lambda: calc.run(Project(name="no estimation", weight=WeightInput())))


def test_run_returns_module_result():
    project = Project(name="x", weight=WeightInput(estimation=ga6_estimation()))
    mr = calc.run(project)
    assert mr.module == "weight_estimate"
    assert mr.conditions


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
