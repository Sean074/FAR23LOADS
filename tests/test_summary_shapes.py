"""The data-shaped summary tables and their one dispatch (#95, C210-8/27).

Owner directive (C210 build review 2026-08-23): "the SELECT table is awful.
All the summary tables on every page so far should be revised. The SELECT
table should be one line per case." And the 2026-08-26 CSV ruling: the screen
and the module CSV are written from the **same rows** (``report.summary_rows``),
so re-shaping one channel alone -- the same data printed two ways -- is the
defect these tests exist to keep out. This is an accepted deliverable-format
change: the frozen Imperial ``csv/*`` digests moved with it, values unchanged.
"""

import csv as csv_mod
import io as pyio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io, registry  # noqa: E402
from sloads.models import CaseRef, ConditionResult, LoadValue  # noqa: E402
from sloads.report import (  # noqa: E402
    SUMMARY_GROUP_BY,
    SUMMARY_SHAPES,
    critical_rows,
    governing_loads_table,
    results_to_rows,
    summary_rows,
    weight_station_rows,
)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _ga6():
    return io.load_project(_GA)


# --------------------------------------------------------------------------- #
# SELECT: one line per case (C210-27, owner directive)
# --------------------------------------------------------------------------- #
def test_select_renders_one_line_per_case_with_its_sf():
    """The stacked shape put 23 ga6 conditions on ~130 quantity rows with the
    per-case SF invisible on every wing case (all non-load quantities)."""
    mr = registry.get("select")(_ga6())
    rows = summary_rows("select", mr.conditions)
    assert len(rows) == len(mr.conditions)
    assert "Quantity" not in rows[0], "the stacked one-row-per-quantity shape is back"
    for row, cond in zip(rows, mr.conditions):
        assert row["Condition"] == cond.title
        assert float(str(row["SF"])) == cond.safety_factor
    wing = [r for r in rows if r["Component"] == "wing"]
    assert wing and all(r["SF"] == "1.5" for r in wing), (
        "the per-case SF must be visible on wing cases -- C210-27's complaint")


def test_select_load_cells_match_the_governing_loads_table():
    """critical_rows and governing_loads_table share the one-line core
    (_union_rows) and the ULT boundary helpers -- the M2-4 'cannot diverge'
    argument. Checked on the numbers: the h-tail totals agree cell for cell."""
    from sloads.modules.select import build_critical

    project = _ga6()
    cls = build_critical(project)
    htail = [c for c in cls.conditions if c.component == "htail"]
    reference = governing_loads_table(htail)
    mr = registry.get("select")(project)
    rows = [r for r in summary_rows("select", mr.conditions)
            if r["Component"] == "htail"]
    col = "Total tail load (lb)"
    assert [r[col] for r in rows] == [r[col] for r in reference]
    assert [r["SF"] for r in rows] == [r["SF"] for r in reference]


def test_the_select_csv_is_the_screen_table():
    """The CSV ruling (owner, 2026-08-26): one shape, both channels. The module
    CSV's header and row count are exactly summary_rows'."""
    project = _ga6()
    mr = registry.get("select")(project)
    rows = summary_rows("select", mr.conditions)
    parsed = list(csv_mod.reader(pyio.StringIO(io.load_cases_csv(mr))))
    assert parsed[0] == list(rows[0].keys())
    assert len(parsed) - 1 == len(rows)


def test_the_oracle_page_shows_the_same_rows_the_csv_holds():
    """The drift guard on the dispatch itself: the flight-envelope page's
    select block carries summary_rows' rows verbatim, and its grouping column
    is the registered one (presentation only -- the artifact stays flat)."""
    from oracle_app.results import step_results
    from sloads.units import UnitSystem

    project = _ga6()
    blocks = {b.module: b for b in step_results(project, "flight_envelope",
                                                UnitSystem.IMPERIAL)}
    block = blocks["select"]
    mr = registry.get("select")(project)
    assert list(block.rows) == summary_rows("select", mr.conditions)
    assert block.group_by == SUMMARY_GROUP_BY["select"] == "Component"


def test_the_grouped_screen_frames_drop_only_all_blank_columns():
    """One sub-table per component, each keeping exactly the quantity columns
    its rows fill; the union columns another component owns render nowhere as
    a wall of em-dashes."""
    from oracle_app.results import _block_frames, step_results
    from sloads.units import UnitSystem

    blocks = {b.module: b for b in step_results(_ga6(), "flight_envelope",
                                                UnitSystem.IMPERIAL)}
    frames = dict(_block_frames(blocks["select"]))
    assert set(frames) >= {"wing", "htail", "vtail", "fuselage"}
    assert "Total tail load (lb)" in frames["htail"].columns
    assert "Total tail load (lb)" not in frames["wing"].columns
    for frame in frames.values():
        assert "Component" not in frame.columns  # it became the sub-title


# --------------------------------------------------------------------------- #
# WTENV: one row per (weight, station) point (C210-8, owner extension)
# --------------------------------------------------------------------------- #
def test_wtenv_folds_weight_station_pairs_to_one_row_per_point():
    mr = registry.get("weight_envelope")(_ga6())
    rows = summary_rows("weight_envelope", mr.conditions)
    # The waterline column joined at design note 45, when the envelope vertices
    # gained WTENV's printed ZBAR. It is present on every row of a result set
    # that has one anywhere and dashed where the block has none, so the summary
    # and CG-limit blocks read exactly as before with one empty cell.
    assert rows is not None and list(rows[0].keys()) == [
        "Condition", "FAR", "Point", "Weight (lb)", "Station (in)",
        "Waterline (in)"]
    assert rows[0]["Waterline (in)"] == "—"
    by_point = {(r["Condition"], r["Point"]): r for r in rows}
    # The CG-limit block as corner x (station, weight) -- station and weight
    # entered as separate stacked values in the condition, folded here.
    corner = by_point[("Structural CG-limit stations and loadings", "Aft gross")]
    # 85.11 -> 85.09 with closed-form planform integration (2026-08-30, register
    # line in 02_approved_corrections): the structural CG limits are
    # XLEMAC-referenced, so they move with the wing MAC's 0.042 %.
    assert corner["Weight (lb)"] == "3400" and corner["Station (in)"] == "85.09"
    # The forward loading envelope: one row per vertex, not three.
    envelope = [r for r in rows
                if r["Condition"].startswith("Forward loading envelope")]
    values = next(c for c in mr.conditions
                  if c.title.startswith("Forward loading envelope")).values
    assert len(envelope) == len(values) // 3
    assert envelope[0]["Point"] == "Point 1"
    assert envelope[0]["Waterline (in)"] != "—"
    # And the aft edge folds the same way (note 45 WE-1): its keys carry an
    # `aft_` prefix so the two edges stay distinguishable when conditions are
    # flattened together, but the fold is the same fold.
    aft = [r for r in rows if r["Condition"].startswith("Aft loading envelope")]
    aft_values = next(c for c in mr.conditions
                      if c.title.startswith("Aft loading envelope")).values
    assert len(aft) == len(aft_values) // 3 == len(envelope)
    assert aft[0]["Point"] == "Aft point 1"


def test_an_unpaired_wtenv_value_keeps_its_label_and_dashes_the_gap():
    """A ballast 'none' marker has a weight cell and no station; the fold must
    keep its full explanatory label rather than inventing a pair."""
    rows = weight_station_rows([ConditionResult(
        title="Ballast to reach the structural limits", far_reference="23.25",
        values=[LoadValue("Aft gross ballast (none -- no loading at/below "
                          "gross weight)", 0.0, "lb", quantity="mass",
                          key="aft_gross_ballast_weight")])])
    assert rows == [{
        "Condition": "Ballast to reach the structural limits", "FAR": "23.25",
        "Point": "Aft gross ballast (none -- no loading at/below gross weight)",
        "Weight (lb)": "0", "Station (in)": "—"}]


# --------------------------------------------------------------------------- #
# The generic floor: all-empty columns are dropped (C210-8)
# --------------------------------------------------------------------------- #
def test_a_property_table_drops_the_blank_load_case_columns():
    """C210-8: geometry results rendered ID / Component / CG / Speed /
    Altitude / SF, all empty, with FAR holding the module name. The floor is
    Condition / FAR / Quantity / Value / Units."""
    mr = registry.get("configuration")(_ga6())
    rows = summary_rows("configuration", mr.conditions)
    assert set(rows[0]) <= {"Condition", "FAR", "Quantity", "Value", "Units"}


def test_the_floor_keeps_every_column_the_data_fills():
    """The prune is data-shaped, not a fixed schema: a condition set that does
    carry case identity (a ref, a speed) keeps exactly those columns."""
    rows = results_to_rows([ConditionResult(
        title="t", far_reference="23.1",
        values=[LoadValue("Load", 10.0, "lb")],
        case_ref=CaseRef(case_id="W-01", component="wing",
                         condition="PHAA", speed_kt=100.0))])
    assert {"ID", "Component", "Speed (kt)", "SF"} <= set(rows[0])
    assert "CG" not in rows[0] and "Altitude (ft)" not in rows[0]


def test_the_dispatch_is_the_single_source_of_summary_shapes():
    """Rule 3: the shapes are registered once and both channels read the
    registration -- a module named here must shape identically through
    summary_rows and through the CSV writer."""
    project = _ga6()
    for module in SUMMARY_SHAPES:
        mr = registry.get(module)(project)
        rows = summary_rows(module, mr.conditions)
        parsed = list(csv_mod.reader(pyio.StringIO(io.load_cases_csv(mr))))
        assert parsed[0] == list(rows[0].keys()), module


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
