"""Tests for the load-case CSV table (one row per structural load case)."""

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures import io520bb, turboprop

from sloads import UnitSystem, convert_results, run_all
from sloads.report import (
    envelope_extremes,
    has_load_case_data,
    load_cases_to_rows,
)


def _col(rows, contains):
    """The single column header containing a substring (units vary)."""
    keys = [k for k in rows[0] if contains in k]
    assert len(keys) == 1, (contains, list(rows[0]))
    return keys[0]


def test_reciprocating_has_one_row_per_condition():
    rows = load_cases_to_rows(run_all(io520bb()))
    assert len(rows) == 3  # 23.361(a)(1), (a)(2), 23.363
    assert [r["ID"] for r in rows] == ["LC1", "LC2", "LC3"]


def test_turboprop_expands_gyro_into_four_cases():
    rows = load_cases_to_rows(run_all(turboprop()))
    # 5 single-case conditions + 4 gyroscopic sign combinations = 9.
    assert len(rows) == 9
    gyro = [r for r in rows if r["FAR"] == "23.371(b)"]
    assert len(gyro) == 4
    pitch = _col(rows, "Myy")
    yaw = _col(rows, "Mzz")
    signs = {(float(r[pitch]) > 0, float(r[yaw]) > 0) for r in gyro}
    assert signs == {(True, True), (True, False), (False, True), (False, False)}


def test_envelope_extremes_is_two_sided():
    # A true load envelope keeps BOTH pointwise extremes: at station 1 the
    # governing positive value (4) and the governing negative one (-5) belong to
    # different cases -- a single max-|value| trace would report only -5.
    upper, lower = envelope_extremes([[1.0, -5.0, 3.0], [2.0, 4.0, -6.0]])
    assert upper == [2.0, 4.0, 3.0]
    assert lower == [1.0, -5.0, -6.0]


def test_every_row_has_a_location():
    # The sudden-stoppage and gyro conditions carry no explicit location; they
    # must inherit the combined-CG location used by the other cases.
    rows = load_cases_to_rows(run_all(turboprop()))
    lx = _col(rows, "Loc X")
    assert all(r[lx] != "" for r in rows)


def test_units_appear_in_headers():
    # All load output is ULTIMATE: the -ULT marker is part of the load's units string.
    imp = load_cases_to_rows(run_all(io520bb()))
    assert "(lbs-ULT)" in _col(imp, "Vertical load")
    assert "(ft-lb-ULT)" in _col(imp, "Engine mount torque")

    si = load_cases_to_rows(convert_results(run_all(io520bb()), UnitSystem.SI))
    assert "(N-ULT)" in _col(si, "Vertical load")
    assert "(Nm-ULT)" in _col(si, "Engine mount torque")


def test_blank_cells_for_inapplicable_loads():
    rows = load_cases_to_rows(run_all(io520bb()))
    side = _col(rows, "Side load")
    # 23.361(a)(1) is a torque/vertical case -> no side load.
    a1 = next(r for r in rows if r["FAR"] == "23.361(a)(1)")
    assert a1[side] == ""
    # 23.363 is the side-load case -> side load populated.
    s = next(r for r in rows if r["FAR"].startswith("23.363"))
    assert s[side] != ""


def _limit(results, far, key):
    """The calc's LIMIT value for one keyed quantity of one condition."""
    cond = next(c for c in results if c.far_reference == far)
    return next(v.value for v in cond.values if v.key == key)


def test_loads_are_ultimate_with_sf_column():
    # The CSV reports ULTIMATE = limit x 1.5; the SF column states the factor and the
    # force/moment headers carry the ULT marker (14 CFR 25.303).
    results = run_all(io520bb())
    rows = load_cases_to_rows(results)
    vert = _col(rows, "Vertical load")
    assert "ULT" in vert
    a2 = next(r for r in rows if r["FAR"] == "23.361(a)(2)")
    assert a2["SF"] == "1.5"
    limit_vert = _limit(results, "23.361(a)(2)", "fz_vertical")
    # rel_tol matches the 4-significant-figure display formatting of the CSV cell.
    import math
    assert math.isclose(float(a2[vert]), 1.5 * limit_vert, rel_tol=1e-3)
    # Limit is recoverable from ultimate / SF.
    assert math.isclose(float(a2[vert]) / float(a2["SF"]), limit_vert, rel_tol=1e-3)


def test_locations_are_not_scaled():
    # Geometry (the applied-at location) must stay limit/unscaled.
    results = run_all(io520bb())
    rows = load_cases_to_rows(results)
    lx = _col(rows, "Loc X")
    limit_x = _limit(results, "23.361(a)(2)", "loc_x")
    a2 = next(r for r in rows if r["FAR"] == "23.361(a)(2)")
    assert abs(float(a2[lx]) - limit_x) < 1e-6


# --------------------------------------------------------------------------- #
# M4-9: the label is cosmetic
# --------------------------------------------------------------------------- #
def _relabelled(results):
    """The same results with every display label replaced by a meaningless one.

    Keys, values, units and FAR references are untouched -- this is exactly the
    edit an engineer makes when rewording a report column.
    """
    return [
        replace(c, values=[replace(v, label=f"relabelled {i}-{j}")
                           for j, v in enumerate(c.values)])
        for i, c in enumerate(results)
    ]


def test_relabelling_every_load_value_leaves_the_csv_intact():
    """The regression M4-9 exists to prevent.

    Before ``LoadValue.key``, ``load_cases_to_rows`` matched on the display label,
    so rewording one silently blanked its column: the lookup returned ``None``,
    ``_val`` turned that into ``""``, and the CSV shipped with an empty cell and no
    error anywhere. Every number below must survive a wholesale relabel.
    """
    for build in (io520bb, turboprop):
        results = run_all(build())
        before = load_cases_to_rows(results)
        after = load_cases_to_rows(_relabelled(results))
        assert len(after) == len(before), f"{build.__name__}: relabelling changed the row count"
        # Guard the guard: an equality-only assertion also passes when the lookup
        # is broken for *both* sides and every load cell comes back blank. The
        # applied-at location is on every row (it falls back to the global one) and
        # some row carries a vertical load, so require both before comparing.
        # (A blank vertical *is* legitimate on 23.363, the pure side-load case.)
        vert, loc_x = _col(before, "Vertical load"), _col(before, "Loc X")
        assert any(row[vert] for row in after), \
            f"{build.__name__}: every vertical load blanked by the relabel"
        for row in after:
            assert row[loc_x] != "", f"{build.__name__}: applied-at X blanked by the relabel"
        for row_b, row_a in zip(before, after):
            for column, value in row_b.items():
                # "Case description" is display text and is *meant* to follow the
                # label; every other cell is data and must be untouched.
                if column == "Case description":
                    continue
                assert row_a[column] == value, (
                    f"{build.__name__}: column {column!r} changed when labels were "
                    f"reworded ({value!r} -> {row_a[column]!r})"
                )


def test_relabelling_does_not_hide_the_load_case_schema():
    """``has_load_case_data`` chose the CSV shape by label too, so a relabel could
    silently downgrade a load-case module to the generic property table."""
    for build in (io520bb, turboprop):
        results = run_all(build())
        assert has_load_case_data(results)
        assert has_load_case_data(_relabelled(results))


def test_gyro_subcases_survive_a_relabel():
    """The four 23.371(b) sign combinations were split out with a regex over the
    label (``"Case 1 (+Myy, +Mzz): Myy"``). They now come off the key."""
    results = run_all(turboprop())
    rows = [r for r in load_cases_to_rows(_relabelled(results)) if r["FAR"] == "23.371(b)"]
    assert len(rows) == 4
    pitch = _col(rows, "Pitch moment")
    yaw = _col(rows, "Yaw moment")
    assert all(r[pitch] and r[yaw] for r in rows)
    # and the four sub-case IDs are still distinct (EM-0Na..d), not collapsed.
    assert len({r["ID"] for r in rows}) == 4


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
