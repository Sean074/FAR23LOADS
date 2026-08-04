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

from sloads import (  # noqa: E402
    EngineWeightType,
    MassItemKind,
    Project,
    WeightEstimationInput,
    WeightInput,
)
from sloads.modules import weight_estimate as calc  # noqa: E402
from helpers import value_of  # noqa: E402


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


def test_summary_matches_manual():
    # Appendix A p133: MAX TAKE OFF WT 3468, USEFUL 1318, EMPTY 2150, ratio .62.
    r = calc.estimate(ga6_estimation())
    assert value_of(r, "Max take-off weight") == 3468
    assert value_of(r, "Useful load") == 1318
    assert value_of(r, "Empty weight") == 2150
    assert value_of(r, "Empty/take-off ratio") == 0.62
    assert value_of(r, "Options & miscellaneous") == 99


def test_operating_empty_weight_adds_crew():
    # OEW = empty + crew*170 is a derived reporting line; the oracle empty/MTOW
    # are unchanged. Appendix A default crew = 1 -> OEW 2150 + 170 = 2320.
    est = ga6_estimation()
    est.crew = 1
    r = calc.estimate(est)
    assert value_of(r, "Empty weight") == 2150            # oracle untouched
    assert value_of(r, "Max take-off weight") == 3468     # oracle untouched
    assert value_of(r, "Crew (operating items)") == 170
    assert value_of(r, "Operating empty weight (OEW)") == 2320
    # Two crew -> OEW rises by another 170, empty/MTOW still unchanged.
    est.crew = 2
    r2 = calc.estimate(est)
    assert value_of(r2, "Empty weight") == 2150
    assert value_of(r2, "Operating empty weight (OEW)") == 2490


def test_structure_group_matches_manual():
    # Appendix A p133 structure breakdown.
    r = calc.estimate(ga6_estimation())
    assert value_of(r, "Wing") == 359
    assert value_of(r, "Fuselage") == 340
    assert value_of(r, "Tail") == 81
    assert value_of(r, "Nacelle") == 50
    assert value_of(r, "Landing gear") == 198
    assert value_of(r, "Controls") == 52
    assert value_of(r, "Total structure") == 1081


def test_powerplant_group_matches_manual():
    # Appendix A p133: installed 490 (prop 83), fuel sys 52, exhaust 72,
    # other 86, total powerplant 700.
    r = calc.estimate(ga6_estimation())
    assert value_of(r, "Engine installed (incl. propeller)") == 490
    assert value_of(r, "Propeller (included above)") == 83
    assert value_of(r, "Fuel system") == 52
    assert value_of(r, "Exhaust") == 72
    assert value_of(r, "Other engine details") == 86
    assert value_of(r, "Total powerplant") == 700


def test_systems_group_matches_manual():
    # Appendix A p133 systems breakdown; single-engine "misc" prints 0
    # (the program prints an unset variable there -- preserved quirk).
    r = calc.estimate(ga6_estimation())
    assert value_of(r, "Instruments & nav equip") == 15
    assert value_of(r, "Pneumatics") == 3
    assert value_of(r, "Electrical") == 83
    assert value_of(r, "Electronics") == 0
    assert value_of(r, "Furnishings & equipment") == 152
    assert value_of(r, "Environmental & anti-ice") == 10
    assert value_of(r, "Misc other system wt") == 0
    assert value_of(r, "Total systems weight") == 268


def test_seed_mass_items_from_estimate():
    # The seeded data base carries every discrete component (not the group
    # totals or the propeller line already inside "Engine installed"), all as
    # empty-weight items with zero stations for the user to fill in.
    items = calc.estimate_to_mass_items(ga6_estimation())
    by_name = {it.name: it for it in items}

    assert "Total structure" not in by_name
    assert "Total powerplant" not in by_name
    assert "Total systems weight" not in by_name
    assert "Propeller (included above)" not in by_name

    # A representative component from each group, plus options/misc, at its
    # estimated weight and zero station.
    assert by_name["Wing"].weight_lb == 359
    assert by_name["Engine installed (incl. propeller)"].weight_lb == 490
    assert by_name["Electrical"].weight_lb == 83
    assert by_name["Options & miscellaneous"].weight_lb == 99
    assert all(it.kind == MassItemKind.EMPTY for it in items)
    assert all(it.x == 0 and it.y == 0 and it.z == 0 for it in items)


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
