"""Tests for the load-case CSV table (one row per structural load case)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import convert_results, run_all, UnitSystem  # noqa: E402
from farloads.report import load_cases_to_rows  # noqa: E402
from test_engine import io520bb, turboprop  # noqa: E402


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


def test_every_row_has_a_location():
    # The sudden-stoppage and gyro conditions carry no explicit location; they
    # must inherit the combined-CG location used by the other cases.
    rows = load_cases_to_rows(run_all(turboprop()))
    lx = _col(rows, "Loc X")
    assert all(r[lx] != "" for r in rows)


def test_units_appear_in_headers():
    imp = load_cases_to_rows(run_all(io520bb()))
    assert "(lb)" in _col(imp, "Vertical load")
    assert "(ft-lb)" in _col(imp, "Engine mount torque")

    si = load_cases_to_rows(convert_results(run_all(io520bb()), UnitSystem.SI))
    assert "(N)" in _col(si, "Vertical load")
    assert "(N·m)" in _col(si, "Engine mount torque")


def test_blank_cells_for_inapplicable_loads():
    rows = load_cases_to_rows(run_all(io520bb()))
    side = _col(rows, "Side load")
    # 23.361(a)(1) is a torque/vertical case -> no side load.
    a1 = next(r for r in rows if r["FAR"] == "23.361(a)(1)")
    assert a1[side] == ""
    # 23.363 is the side-load case -> side load populated.
    s = next(r for r in rows if r["FAR"].startswith("23.363"))
    assert s[side] != ""


def _limit(results, far, label):
    """The calc's LIMIT value for a labelled quantity of one condition."""
    cond = next(c for c in results if c.far_reference == far)
    return next(v.value for v in cond.values if v.label == label)


def test_loads_are_ultimate_with_sf_column():
    # The CSV reports ULTIMATE = limit x 1.5; the SF column states the factor and the
    # force/moment headers carry the ULT marker (14 CFR 25.303).
    results = run_all(io520bb())
    rows = load_cases_to_rows(results)
    vert = _col(rows, "Vertical load")
    assert "ULT" in vert
    a2 = next(r for r in rows if r["FAR"] == "23.361(a)(2)")
    assert a2["SF"] == "1.5"
    limit_vert = _limit(results, "23.361(a)(2)", "Vertical down load")
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
    limit_x = _limit(results, "23.361(a)(2)", "Applied at X")
    a2 = next(r for r in rows if r["FAR"] == "23.361(a)(2)")
    assert abs(float(a2[lx]) - limit_x) < 1e-6


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
