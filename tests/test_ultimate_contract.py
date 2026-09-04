"""Load-basis contract guard for app-layer CSV downloads (M4-15; note 48 G-OR-45).

Every *load-bearing* CSV a view offers for download must carry its basis with the
file (``CONVENTIONS.md`` §3). Since design note 48 there are two bases and each
download declares which one it is on:

* **ULTIMATE** -- content built by the sbeam bridge or the case index, or a
  filename marked ``*_ULT.csv``. This is the export deliverable.
* **LIMIT** -- content built by ``load_cases_csv``, which on a per-module page is
  the LIMIT channel (OR-76/OR-79) and **must pass ``channel=LoadChannel.LIMIT``
  at the call**, or a filename marked ``*_LIMIT.csv``.

That last clause is the point of the inversion. The renderers default to
ULTIMATE so the frozen ``oracle_app`` is unchanged by construction (OR-77) --
which means a new page that simply forgets the argument ships ULTIMATE loads on
an analysis surface, silently and plausibly. Nothing at runtime would say so.
This gate does.

This is a source scan, not a runtime test: it reads ``app/views/*.py`` and checks
every ``download_button`` CSV ``file_name``. A new page adding a load CSV that
declares no basis fails here until the author declares one or (for a genuinely
non-load table) adds the filename to the explicit allowlist below -- the failure
is the point.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_VIEWS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "app", "views")

# Content expressions that mean the file is ULTIMATE by construction: the sbeam
# bridge renderers and the case index carry SF / -ULT units themselves.
# ``load_cases_csv`` is deliberately NOT here any more -- since note 48 it is the
# LIMIT channel on these pages, and it must say so at the call.
_ULT_CHANNEL = re.compile(r"sb\.|sbeam_bridge|case_index_csv")

#: The report-layer renderers whose channel is a *caller* decision. Finding one
#: of these in a download's context obliges the caller to state its channel.
_CHANNELLED = re.compile(r"load_cases_csv|load_cases_to_rows")

#: How a caller opts a per-module surface into LIMIT.
_LIMIT_OPT_IN = re.compile(r"channel\s*=\s*LoadChannel\.LIMIT")

# Non-load tables (geometry, design speeds, mass properties): no basis to state.
_NON_LOAD = {
    "wing_geometry.csv",
    "structural_speeds.csv",
    "mach_limit.csv",
    "weight_estimate.csv",
    "weight_cg_inertia.csv",
    "weight_envelope.csv",
}

# The consolidation page used to be skipped **wholesale**, on the strength of a
# comment saying every artifact it offers is ULTIMATE by construction (review
# CR-C-6): an exemption that grows silently with the file, since a new CSV added
# there would never be scanned. It is scanned like every other view now, and the
# two CSV downloads it carries are named here instead. Both take content built by
# the report/bridge channels earlier in the page, too far above the call for the
# context window below to see -- which is what the wholesale skip was standing in
# for. Add a CSV to that page and it fails here until it is named or marked.
_SKIP_FILES: set = set()

#: (view, csv name) pairs whose ULTIMATE channel is out of the context window,
#: with the owner that makes them ULTIMATE.
_ULT_BY_CONSTRUCTION = {
    # `module_csvs` is built by `report.load_cases_csv` at the top of the page,
    # on the LIMIT channel since note 48 (OR-79/OR-80) -- named here because the
    # call is far above the context window, and covered at runtime by G-OR-47.
    ("export_report.py", "{_stem}_{mr.module}.csv"): "report.load_cases_csv (LIMIT)",
    # `case_index_csv` is the bridge's own case index, built once per run.
    ("export_report.py", "{_stem}_case_index.csv"): "case_ids/case_index_csv",
}

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
            if (fn, name) in _ULT_BY_CONSTRUCTION:
                continue
            # Unmarked filename: read the download_button call and the few
            # lines building its content argument.
            line_no = src[: m.start()].count("\n")
            context = "\n".join(lines[max(0, line_no - 6):line_no + 2])
            if _CHANNELLED.search(context):
                # A renderer whose channel the caller chooses. On an app page
                # that choice is LIMIT and it has to be written down -- the
                # default is ULTIMATE, so silence here is not neutral.
                assert _LIMIT_OPT_IN.search(context), (
                    f"{fn}: CSV download '{name}' is built by a channelled "
                    "renderer but names no channel. A per-module page is the "
                    "LIMIT channel (note 48 OR-76): pass "
                    "channel=LoadChannel.LIMIT at the call. The renderer "
                    "defaults to ULTIMATE to protect the frozen oracle GUI "
                    "(OR-77), so omitting it ships ultimate loads silently."
                )
                continue
            assert _ULT_CHANNEL.search(context), (
                f"{fn}: CSV download '{name}' states no basis -- mark the "
                "filename *_LIMIT.csv or *_ULT.csv, route the content through "
                "an ULTIMATE channel (sbeam bridge / case index), pass "
                "channel=LoadChannel.LIMIT to a report renderer, or allowlist "
                "it here if it is not a load table."
            )
    # The scan must actually be seeing the app layer (guards against a moved dir).
    assert checked >= 10, f"only {checked} CSV downloads found under app/views"


def test_every_named_exemption_still_names_a_download():
    """An allowlist that outlives its entries is the wholesale skip again.

    Each `_ULT_BY_CONSTRUCTION` key has to match a `file_name=` this view still
    writes; a renamed or deleted artifact takes its exemption with it.
    """
    for (fn, name), owner in sorted(_ULT_BY_CONSTRUCTION.items()):
        path = os.path.join(_VIEWS, fn)
        assert os.path.exists(path), f"{fn} is gone; drop its exemption"
        with open(path, encoding="utf-8") as fh:
            found = {m.group("name") for m in _FILE_NAME.finditer(fh.read())}
        assert name in found, (
            f"{fn} no longer offers '{name}' (exempted as ULTIMATE via {owner}) "
            "-- remove the entry")


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
