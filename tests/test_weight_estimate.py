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
    assert value_of(r, "max_take_off_weight") == 3468
    assert value_of(r, "useful_load") == 1318
    assert value_of(r, "empty_weight") == 2150
    assert value_of(r, "empty_take_off_ratio") == 0.62
    assert value_of(r, "options_and_miscellaneous") == 99


def test_operating_empty_weight_adds_crew():
    # OEW = empty + crew*170 is a derived reporting line; the oracle empty/MTOW
    # are unchanged. Appendix A default crew = 1 -> OEW 2150 + 170 = 2320.
    est = ga6_estimation()
    est.crew = 1
    r = calc.estimate(est)
    assert value_of(r, "empty_weight") == 2150            # oracle untouched
    assert value_of(r, "max_take_off_weight") == 3468     # oracle untouched
    assert value_of(r, "crew_operating_items") == 170
    assert value_of(r, "operating_empty_weight") == 2320
    # Two crew -> OEW rises by another 170, empty/MTOW still unchanged.
    est.crew = 2
    r2 = calc.estimate(est)
    assert value_of(r2, "empty_weight") == 2150
    assert value_of(r2, "operating_empty_weight") == 2490


def test_structure_group_matches_manual():
    # Appendix A p133 structure breakdown.
    r = calc.estimate(ga6_estimation())
    assert value_of(r, "wing") == 359
    assert value_of(r, "fuselage") == 340
    assert value_of(r, "tail") == 81
    assert value_of(r, "nacelle") == 50
    assert value_of(r, "landing_gear") == 198
    assert value_of(r, "controls") == 52
    assert value_of(r, "total_structure") == 1081


def test_powerplant_group_matches_manual():
    # Appendix A p133: installed 490 (prop 83), fuel sys 52, exhaust 72,
    # other 86, total powerplant 700.
    r = calc.estimate(ga6_estimation())
    assert value_of(r, "engine_installed") == 490
    assert value_of(r, "propeller") == 83
    assert value_of(r, "fuel_system") == 52
    assert value_of(r, "exhaust") == 72
    assert value_of(r, "other_engine_details") == 86
    assert value_of(r, "total_powerplant") == 700


def test_systems_group_matches_manual():
    # Appendix A p133 systems breakdown; single-engine "misc" prints 0
    # (the program prints an unset variable there -- preserved quirk).
    r = calc.estimate(ga6_estimation())
    assert value_of(r, "instruments_and_nav_equip") == 15
    assert value_of(r, "pneumatics") == 3
    assert value_of(r, "electrical") == 83
    assert value_of(r, "electronics") == 0
    assert value_of(r, "furnishings_and_equipment") == 152
    assert value_of(r, "environmental_and_anti_ice") == 10
    assert value_of(r, "misc_other_system_wt") == 0
    assert value_of(r, "total_systems_weight") == 268


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


# --------------------------------------------------------------------------- #
# The estimate against the data base (C210-9, #78)
# --------------------------------------------------------------------------- #
def _project_with_items(items):
    return Project(name="cmp",
                   weight=WeightInput(estimation=ga6_estimation(), items=items))


def test_the_estimate_is_compared_against_the_weight_the_project_uses():
    """C210-9: the estimate and the item table are never shown together, so a
    +22 % correlation gap reads as a discrepancy nobody explains. Both entered
    figures come from their owners — the empty weight from ``database_totals``,
    MTOW from ``cg_cases.max_takeoff_weight`` (G-14) — never re-summed here."""
    from sloads.models import MassItem

    project = _project_with_items([
        MassItem(name="airframe", weight_lb=1000.0, x=100.0, kind=MassItemKind.EMPTY),
        MassItem(name="fuel", weight_lb=200.0, x=100.0, kind=MassItemKind.DISCRETIONARY),
    ])
    project.weight.max_takeoff_weight_lb = 1500.0
    rows = {r.quantity: r for r in calc.compare_with_itemized(project)}
    assert set(rows) == {"Empty weight", "Max take-off weight"}
    assert rows["Empty weight"].entered_lb == 1000.0        # EMPTY rows only
    assert rows["Max take-off weight"].entered_lb == 1500.0  # the SSOT, not the row sum
    empty = rows["Empty weight"]
    assert empty.delta_lb == empty.estimated_lb - 1000.0
    assert empty.delta_pct == 100.0 * empty.delta_lb / 1000.0


def test_the_take_off_comparison_is_not_the_sum_of_every_row():
    """``database_totals()[0]`` is documented as a **ceiling** — it holds full
    fuel and full payload at once, which no loading does — so comparing the
    estimate against it would report a gap against a weight the airplane never
    has. The design take-off weight is a different owner and is the one used."""
    from sloads.models import MassItem

    project = _project_with_items([
        MassItem(name="airframe", weight_lb=1000.0, x=100.0, kind=MassItemKind.EMPTY),
        MassItem(name="fuel", weight_lb=900.0, x=100.0, kind=MassItemKind.DISCRETIONARY),
    ])
    project.weight.max_takeoff_weight_lb = 1500.0
    rows = {r.quantity: r for r in calc.compare_with_itemized(project)}
    assert project.weight.database_totals()[0] == 1900.0
    assert rows["Max take-off weight"].entered_lb == 1500.0


def test_an_empty_data_base_is_not_compared_against():
    """An estimate beside no items is not a comparison, and reporting it as a
    100 % gap against zero would be a verdict on an unfinished project."""
    project = _project_with_items([])
    assert calc.compare_with_itemized(project) == ()


def test_a_project_with_no_estimation_inputs_compares_nothing():
    """The advisory renders on a blank page too; the comparison half simply has
    nothing to say, rather than raising into the results renderer."""
    assert calc.compare_with_itemized(Project(name="x")) == ()
    assert calc.compare_with_itemized(Project(name="x", weight=WeightInput())) == ()


def test_the_advisory_says_nothing_reads_the_estimate():
    """The sentence is a fact about WTESTIMA, so it is owned by the module and
    not by whichever page happens to render it (C210-9). It has to survive
    contact with ``PROGRAM_SPEC``'s "feeds WTONECG *and* WTENV", which is the
    suite's data flow *through the data base* — a base the user authors here, so
    the estimate reaches it only via the seed button."""
    assert "nothing reads these figures" in calc.ADVISORY
    assert "itemized weight data base" in calc.ADVISORY



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
