"""Platform-stable deliverable bytes (``CONVENTIONS.md`` §7, 2026-08-16).

A byte in a deck or report must not depend on the libm build, FMA, or the
interpreter's ``sum()``. Three owners, three guards:

* ``picks.extreme`` -- keyed picks are first-in-order inside a relative tie
  band, and **this file** walks the package's AST so no builtin ``min``/``max``
  with a ``key=`` can re-appear anywhere in ``sloads/``. The owner was
  ``select._extreme``, private to one module, until review 2026-08-20 CR-B-1
  found a live keyed pick in ``select`` itself that the old substring grep could
  not see (``(min if want_min else max)(...)`` contains neither ``max(`` nor
  ``min(`` next to ``key=``) plus the same defect class in five other modules
  and in the exporters;
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

import ast
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads
from sloads.picks import extreme

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
        "it, 3.10/3.11 do not) -- use math.fsum, or `sum(1 for ...)` for a count:\n  "
        + "\n  ".join(hits))


def _keyed_picks(source, label):
    """``[(lineno, dump)]`` for every builtin ``min``/``max`` call in ``source``
    that carries a ``key=`` keyword.

    An AST walk, not a grep: CR-B-1's live bypass was
    ``(min if want_min else max)(bal_a, key=...)``, which contains neither
    ``min(`` nor ``max(``. Matched on the *callee expression*, so the
    conditional form, an aliased ``builtins.max``, and a call spread over
    several lines all read the same to the guard.

    What it deliberately does not see: a pick written as an accumulation loop
    (``if v > best: best = v``), which no static walk can distinguish from
    ordinary arithmetic. §7's wording is scoped to match this guard exactly --
    the shape it names is the shape it enforces.
    """
    def is_builtin_min_max(node):
        if isinstance(node, ast.Name):
            return node.id in ("min", "max")
        if isinstance(node, ast.IfExp):  # (min if c else max)(...)
            return is_builtin_min_max(node.body) or is_builtin_min_max(node.orelse)
        return False

    hits = []
    for node in ast.walk(ast.parse(source, filename=label)):
        if not isinstance(node, ast.Call) or not is_builtin_min_max(node.func):
            continue
        if any(kw.arg == "key" for kw in node.keywords):
            hits.append((node.lineno, ast.dump(node.func)))
    return hits


def test_every_keyed_pick_in_sloads_goes_through_picks_extreme():
    hits = []
    for root, _dirs, files in os.walk(_PKG):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, _PKG)
            with open(path, encoding="utf-8") as fh:
                for lineno, _dump in _keyed_picks(fh.read(), rel):
                    hits.append(f"{rel}:{lineno}")
    assert not hits, (
        "a keyed built-in min()/max() is not platform-stable: candidates whose "
        "keys tie in exact arithmetic can land either side of the other by an ulp "
        "on a different libm or Python version, and the pick -- a case, a node, a "
        "pivot row -- flips with them. Route it through sloads.picks.extreme:\n  "
        + "\n  ".join(hits))


def test_extreme_pick_is_first_in_order_across_a_platform_ulp_tie():
    """The keyed pick is stable under last-ulp noise (CI vs local).

    ``BAL A`` at two altitudes carries the same VA and hence the same rudder load;
    on the developer's Mac the two keys are bit-identical and ``max`` returns the
    first, on the Linux CI runner one lands an ulp above the other and ``max``
    returned the *second* -- a different V-n case in the deck for a difference
    no printed digit shows. ``extreme`` picks the first candidate inside a
    ``TIE_REL`` relative band of the extreme, so both platforms agree; a
    genuinely larger candidate anywhere in the list still wins.
    """
    base = 4287.797363708473
    up = math.nextafter(base, math.inf)
    # bit-exact tie -> first (what max() did, so nothing moves locally)
    assert extreme(["a", "b"], {"a": base, "b": base}.__getitem__) == "a"
    # one-ulp tie either way -> still the first
    assert extreme(["a", "b"], {"a": base, "b": up}.__getitem__) == "a"
    assert extreme(["a", "b"], {"a": up, "b": base}.__getitem__) == "a"
    assert extreme(["a", "b"], {"a": -base, "b": -up}.__getitem__,
                   largest=False) == "a"
    # a real difference wins wherever it sits
    assert extreme(["a", "b"], {"a": base, "b": base * 1.001}.__getitem__) == "b"
    assert extreme(["a", "b"], {"a": base, "b": base * 0.999}.__getitem__,
                   largest=False) == "b"


def test_the_keyed_pick_guard_recognises_the_shapes_it_must():
    # the plain forms, and the CR-B-1 bypass the substring grep could not see
    assert _keyed_picks("p = max(cands, key=f)", "t") == [(1, "Name(id='max', ctx=Load())")]
    assert len(_keyed_picks("p = min(cands, key=f)", "t")) == 1
    assert len(_keyed_picks("p = (min if want_min else max)(cands, key=f)", "t")) == 1
    assert len(_keyed_picks("p = max(\n    cands,\n    key=f,\n)", "t")) == 1
    # and what it must not flag
    assert _keyed_picks("p = extreme(cands, f, largest=False)", "t") == []
    assert _keyed_picks("s = max(abs(v) for v in row)", "t") == []
    assert _keyed_picks("b = max(keys) if largest else min(keys)", "t") == []
    assert _keyed_picks("d = frame.max(key='x')", "t") == []       # attribute, not builtin


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
