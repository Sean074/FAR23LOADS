"""Ultimate-load contract guard for app-layer CSV downloads (defect M4-15).

Every *load-bearing* CSV a view offers for download must carry its basis with the
file (CLAUDE.md "Ultimate-load output"): either it is routed through an ULTIMATE
channel (the sbeam bridge CSVs / the report-layer load-case rows -- ``SF`` column,
``-ULT`` units), or it is a LIMIT analysis artifact whose filename is marked
``*_LIMIT.csv`` with in-band LIMIT markers (a ``Basis`` column or LIMIT-marked
column headers).

This is a source scan, not a runtime test: it reads ``app/views/*.py`` and checks
every ``download_button`` CSV ``file_name``. A new page adding a load CSV with a
neutral name fails here until the author either marks the basis or (for a
genuinely non-load table) adds the filename to the explicit allowlist below --
the failure is the point.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_VIEWS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "app", "views")

# Content expressions that mean the file is ULTIMATE by construction (the sbeam
# bridge renderers and the report-layer rows carry SF / -ULT units themselves).
_ULT_CHANNEL = re.compile(
    r"sb\.|sbeam_bridge|load_cases_csv|load_cases_to_rows|case_index_csv")

# Non-load tables (geometry, design speeds, mass properties): no basis to state.
_NON_LOAD = {
    "wing_geometry.csv",
    "structural_speeds.csv",
    "mach_limit.csv",
    "weight_estimate.csv",
    "weight_cg_inertia.csv",
    "weight_envelope.csv",
}

# The consolidation page: every artifact is ULTIMATE by construction (its content
# comes from the bridge / report channels; locked by the M4-7/M4-13 suites).
_SKIP_FILES = {"export_report.py"}

_FILE_NAME = re.compile(r'file_name=f?"(?P<name>[^"]+\.csv)"')


def test_csv_downloads_state_their_basis():
    checked = 0
    for fn in sorted(os.listdir(_VIEWS)):
        if not fn.endswith(".py") or fn in _SKIP_FILES:
            continue
        with open(os.path.join(_VIEWS, fn), encoding="utf-8") as fh:
            src = fh.read()
        lines = src.splitlines()
        for m in _FILE_NAME.finditer(src):
            name = m.group("name")
            if os.path.basename(name) in _NON_LOAD:
                continue
            checked += 1
            if name.endswith("_LIMIT.csv") or name.endswith("_ULT.csv"):
                continue
            # Unmarked filename: the content must come from an ULTIMATE channel.
            # Look at the download_button call and the few lines building its
            # content argument.
            line_no = src[: m.start()].count("\n")
            context = "\n".join(lines[max(0, line_no - 6):line_no + 2])
            assert _ULT_CHANNEL.search(context), (
                f"{fn}: CSV download '{name}' states no basis -- mark the "
                "filename *_LIMIT.csv (with in-band LIMIT markers) or route the "
                "content through an ULTIMATE channel (sbeam bridge / "
                "load_cases_csv), or allowlist it here if it is not a load table."
            )
    # The scan must actually be seeing the app layer (guards against a moved dir).
    assert checked >= 10, f"only {checked} CSV downloads found under app/views"


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
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
