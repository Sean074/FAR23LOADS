"""Platform-stable deliverable bytes (``CONVENTIONS.md`` §7, 2026-08-16).

A byte in a deck or report must not depend on the libm build, FMA, or the
interpreter's ``sum()``. Three owners, three guards:

* ``select._extreme`` -- critical-case picks are first-in-order inside a
  relative tie band (``tests/test_select.py``);
* ``sbeam_bridge._fmt3`` -- vector-card components snap dust and ``-0`` to
  ``0.000000E+00`` (``tests/test_sbeam_bridge.py``);
* **this file** -- every float summation in ``sloads/`` is ``math.fsum``, which
  is exactly rounded and therefore identical on every platform and Python
  version. Python 3.12 changed the built-in ``sum()`` of floats to compensated
  (Neumaier) summation, so ``sum(ld.fz for ld in loads)`` on 3.12 landed a few
  ulp from 3.9/3.11 and the developer's Mac; where a value sat on a print
  boundary (an integer-valued residual, a 7th-digit tie in a FORCE card) the
  frozen Imperial digest failed on the 3.12 leg only. ``fsum`` closes the class
  rather than chasing the next knife-edge; the digest was regenerated once,
  deliberately, when the sweep landed (20 lines, all last-digit).

The only built-in ``sum`` left is the counting idiom ``sum(1 for ...)``, which
is integer arithmetic and exact everywhere.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads

_PKG = os.path.dirname(os.path.abspath(sloads.__file__))

#: A built-in ``sum(`` call -- not ``fsum(``, not ``.sum(``, not the ``sum(1 for``
#: counting idiom.
_BARE_SUM = re.compile(r"(?<![\w.])sum\((?!1 for\b)")


def _code_lines(path):
    """(lineno, text) for the lines of ``path`` that are code -- docstrings and
    comment lines dropped, trailing comments stripped -- so prose that *mentions*
    ``sum(items)`` does not trip the guard."""
    out = []
    in_doc = False
    with open(path, encoding="utf-8") as fh:
        for n, ln in enumerate(fh, 1):
            stripped = ln.strip()
            if in_doc:
                if stripped.count('"""') % 2 == 1:
                    in_doc = False
                continue
            if stripped.count('"""') % 2 == 1:
                in_doc = True
                continue
            if stripped.startswith("#"):
                continue
            out.append((n, ln.partition("  #")[0]))
    return out


def test_every_float_summation_in_sloads_is_fsum():
    hits = []
    for root, _dirs, files in os.walk(_PKG):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            for n, text in _code_lines(path):
                if _BARE_SUM.search(text):
                    hits.append(f"{os.path.relpath(path, _PKG)}:{n}: {text.strip()}")
    assert not hits, (
        "built-in sum() over floats is not platform-stable (Python 3.12 compensates "
        "it, 3.9/3.11 do not) -- use math.fsum, or `sum(1 for ...)` for a count:\n  "
        + "\n  ".join(hits))


def test_the_guard_recognises_the_shapes_it_must():
    assert _BARE_SUM.search("x = sum(a for a in b)")
    assert _BARE_SUM.search("total = sum(raw)")
    assert not _BARE_SUM.search("n = sum(1 for r in rows if r.ok)")
    assert not _BARE_SUM.search("x = math.fsum(a for a in b)")
    assert not _BARE_SUM.search("y = fsum(vals)")
    assert not _BARE_SUM.search("z = arr.sum(axis=0)")


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok   {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
