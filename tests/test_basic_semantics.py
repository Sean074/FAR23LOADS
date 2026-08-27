"""Single-owner guard for the BASIC ``INT()`` port (CLAUDE.md rule 3).

GW-BASIC ``INT()`` floors; Python ``int()`` truncates toward zero. The two agree
on non-negative arguments, so a port that spells one as the other is right until
the quantity first goes negative and then quietly reports one unit less --
23.361(b)(1)'s stoppage torque, whose argument is negative by construction, is
where that landed (CR-B-3, #40). The semantics now have one owner,
``sloads.basic``, and this file is its drift guard: the calc layer may not
open-code the conversion again.
"""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_constants import _code_lines, _package_sources

from sloads.basic import basic_int, basic_trunc3

_OWNER = os.path.join("sloads", "basic.py")

#: ``int()`` call sites in the calc layer that are *not* a ``.BAS`` ``INT()``
#: port, each with the reason it is exempt. Anything else must use the owner.
_ALLOWED = {
    os.path.join("sloads", "modules", "one_engine_out.py"):
        "max_steps -- a simulation step count, not a printed-value truncation",
}


def test_basic_int_floors_where_python_int_truncates():
    """The whole point: they part company on negatives, and BASIC floors."""
    assert basic_int(-6824.624095864674) == -6825.0
    assert int(-6824.624095864674) == -6824          # the defect this replaced
    assert basic_int(1234.99) == 1234.0 == int(1234.99)  # agree when positive
    assert basic_int(-7.0) == -7.0                   # exact integers are fixed points
    for x in (-6824.6, -0.5, -1e-9, 0.0, 0.5, 6824.6):
        assert basic_int(x) == math.floor(x)


def test_basic_trunc3_is_the_three_decimal_form():
    assert basic_trunc3(16.6666) == 16.666
    assert basic_trunc3(-16.6661) == -16.667   # floors: int() would give -16.666
    assert basic_trunc3(0.0) == 0.0


def test_no_open_coded_basic_int_in_the_calc_modules():
    """Every ``int(...)`` in ``sloads/modules/`` is a ``.BAS`` ``INT()`` port
    unless it is on the reasoned allowlist above -- so a new one has to be
    classified rather than defaulted to Python's semantics."""
    hits = []
    for rel, text in _package_sources(os.path.join("sloads", "modules")):
        if rel == _OWNER or rel in _ALLOWED:
            continue
        for code in _code_lines(text):
            if re.search(r"(?<![\w.])int\(", code):
                hits.append(f"{rel}: {code.strip()!r} -> use sloads.basic.basic_int")
    assert not hits, "\n".join(hits)


def test_the_three_decimal_idiom_has_one_owner():
    """``int(x*1000)/1000`` open-coded anywhere is a second declaration of the
    truncation, and one that gets negative arguments wrong."""
    hits = [f"{rel}: {code.strip()!r}"
            for rel, text in _package_sources("sloads", "app", "scripts", "cli.py")
            if rel != _OWNER
            for code in _code_lines(text)
            if re.search(r"int\([^()]*\*\s*1000\)\s*/\s*1000", code)]
    assert not hits, "\n".join(hits)


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
