"""Sanity-check the bundled reference-aircraft data set.

``app/data/reference_aircraft.csv`` feeds the Weight Estimate page's MTOW-vs-OEW
comparison plot. It is reference data only (never enters a FAR computation), but a
malformed row would break the chart, so this test guards its shape and basic
physical plausibility without importing Streamlit or plotly.
"""

import csv
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(REPO_ROOT, "app", "data", "reference_aircraft.csv")

_REQUIRED_COLUMNS = {
    "aircraft", "mtow_lb", "oew_lb", "max_hp", "engines",
    "engine_type", "seats", "wingspan_ft", "wing_area_ft2",
}


def _rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        # The file carries a leading "# ..." comment block before the header.
        data = (line for line in fh if not line.startswith("#"))
        return list(csv.DictReader(data))


def test_columns_present():
    rows = _rows()
    assert rows, "reference_aircraft.csv has no data rows"
    assert _REQUIRED_COLUMNS.issubset(rows[0].keys())


def test_weights_positive_and_oew_below_mtow():
    for row in _rows():
        mtow = float(row["mtow_lb"])
        oew = float(row["oew_lb"])
        assert mtow > 0, f"{row['aircraft']}: MTOW must be positive"
        assert oew > 0, f"{row['aircraft']}: OEW must be positive"
        assert oew < mtow, f"{row['aircraft']}: OEW ({oew}) must be below MTOW ({mtow})"


def test_expected_aircraft_present():
    names = {row["aircraft"] for row in _rows()}
    for expected in ("Cessna 150", "Van's RV-10", "ATR 42-500", "de Havilland Dash 8-100"):
        assert expected in names, f"missing reference aircraft: {expected}"


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
    raise SystemExit(1 if failed else 0)
