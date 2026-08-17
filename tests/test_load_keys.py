"""LoadValue key uniqueness -- the guard :mod:`sloads.load_keys` cites (M4-9).

Every ``LoadValue`` in a ``ConditionResult`` carries a stable ``key``; the
flat load-case row (``report.load_cases_to_rows``) and the sbeam bridge index by
it, so a duplicate key within one condition would silently overwrite a cell.
This asserts uniqueness across every registered module on every example
project (conventions finding (a), 2026-08-05: the docstring cited this file
before it existed).
"""

import collections
import glob
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.modules  # noqa: E402,F401  -- self-registers every module
from sloads import io, registry  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))


@pytest.mark.parametrize("path", EXAMPLES, ids=os.path.basename)
def test_load_keys_unique_within_every_condition(path):
    project = io.load_project(path)
    ran = 0
    for name in registry.available():
        try:
            result = registry.get(name)(project)
        except Exception:  # noqa: BLE001 -- a module the example lacks inputs for
            continue
        ran += 1
        for cond in result.conditions:
            counts = collections.Counter(v.key for v in cond.values)
            dups = sorted(k for k, n in counts.items() if n > 1)
            assert not dups, f"{os.path.basename(path)} {name}: duplicate keys {dups}"
            assert all(v.key for v in cond.values), f"{name}: empty LoadValue key"
    assert ran > 0


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

