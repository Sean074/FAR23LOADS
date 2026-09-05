"""The one load basis: what a render states, and what protects the frozen GUI.

Design note 48 built ``report.LoadChannel`` as a *switch* -- an ULTIMATE channel
(case selection, the export deck, the case index, the oracle technical report)
and a LIMIT channel (the CLI and the app's per-module analysis surfaces). Note 49
**OR-116** removes the choice: every load sloads delivers is LIMIT, on every
surface, with its factor stated and applied nowhere. ``LoadChannel`` keeps a
single member so that a stale caller asking for ULTIMATE fails at import instead
of silently receiving limit loads; the parameter itself goes at #29, when the
frozen ``app/views/`` can be edited.

Gates here:

* **G-OR-44** -- the default is the project's one basis, so a caller that passes
  nothing gets it. This still keeps the frozen ``oracle_app`` correct *by
  construction* rather than by inspection (OR-77): the file names no channel,
  and the default inverted underneath it.
* **G-OR-47** -- a LIMIT render applies no factor, emits no ``-ULT`` marker
  except on the two already-ultimate families (OR-118), and states its basis
  with the instruction to apply the factor in the sizing analysis.
* **G-OR-71** -- no path in ``sloads/`` multiplies a load by a safety factor.
  The structural form of "stated, never applied"; see the scan at the foot of
  this file, and ``tests/test_deck_basis.py`` for the deck-side half (G-OR-73).
* the ``N/A`` half of **OR-82**: a condition prescribing no factor never prints
  one.
"""

import glob
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.modules  # noqa: F401
from sloads import io
from sloads.registry import run_all_modules
from sloads.report import (
    LoadChannel,
    format_value,
    module_text_report,
    summary_rows,
)
from sloads.safety_factors import prescribes_factor
from sloads.units import is_load_unit

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))
_GA = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


def _modules(path):
    return run_all_modules(io.load_project(path))


# --------------------------------------------------------------------------- #
# G-OR-44 -- the default is the project's one basis
# --------------------------------------------------------------------------- #
def test_the_renderers_default_to_limit():
    """No argument means LIMIT, in every channelled renderer.

    Inverted by note 49 OR-116: LIMIT is the project's only basis, so the
    default states it. This was ``..._default_to_ultimate`` while note 48's
    OR-77 kept ULTIMATE the default to leave the frozen ``oracle_app``
    unchanged by construction; the frozen file still passes no channel, and now
    gets the one basis the project has.
    """
    mr = [m for m in _modules(_GA) if m.module == "engine"][0]
    for default, explicit in (
        (module_text_report("Engine", mr.conditions),
         module_text_report("Engine", mr.conditions,
                            channel=LoadChannel.LIMIT)),
        (summary_rows(mr.module, mr.conditions),
         summary_rows(mr.module, mr.conditions, channel=LoadChannel.LIMIT)),
    ):
        assert default == explicit


def test_the_frozen_oracle_gui_passes_no_channel():
    """OR-77 in the form that actually protects the file.

    ``oracle_app/results.py`` is in the OR-13 frozen set and cannot be edited to
    opt in. The default exists *so that* it needs no edit -- which is what let
    OR-116 invert the basis underneath it without touching a frozen file. The
    assertion is only meaningful while the file names no channel, which is what
    this reads.
    """
    path = os.path.join(_ROOT, "oracle_app", "results.py")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    assert "LoadChannel" not in src, (
        "oracle_app/results.py names a channel; it is frozen (OR-13) and the "
        "ULTIMATE default exists precisely so it does not have to.")


def test_the_default_render_applies_no_factor_and_states_it():
    """The endpoint of OR-86, asserted on the default path (note 49 OR-116).

    Replaces ``test_the_ultimate_channel_still_applies_the_factor``. The engine
    module is the right witness twice over: its 23.367(a)(2) cases are computed
    already ultimate at SF = 1.0, so this also pins OR-118 -- the ``-ULT``
    marker survives exactly there.
    """
    mr = [m for m in _modules(_GA) if m.module == "engine"][0]
    text = module_text_report("Engine", mr.conditions)
    assert "Loads are LIMIT" in text
    condition = next(c for c in mr.conditions
                     if any(is_load_unit(v.units, v.quantity or "")
                            for v in c.values))
    load = next(v for v in condition.values
                if is_load_unit(v.units, v.quantity or ""))
    assert condition.safety_factor is not None
    # the calc's own number, unscaled -- and the factor still stated
    assert format_value(load.value) in text
    assert format_value(condition.safety_factor) in text


# --------------------------------------------------------------------------- #
# G-OR-47 -- what a LIMIT render says, and does not say
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_a_limit_render_never_marks_a_value_ultimate(path):
    for mr in _modules(path):
        text = module_text_report(mr.module, mr.conditions,
                                  channel=LoadChannel.LIMIT)
        assert "[ULTIMATE" not in text, f"{path}/{mr.module}"
        # OR-118: ``-ULT`` survives on the two families computed already
        # ultimate and nowhere else, so its presence is checked against the
        # cases rather than forbidden outright.
        already = [c for c in mr.conditions if c.safety_factor == 1.0]
        # Data lines only: the basis header *explains* the ``-ULT`` marker in
        # prose ("a load marked -ULT is already ultimate"), so a whole-text grep
        # would be satisfied by the explanation rather than by a value.
        values = "\n".join(ln for ln in text.splitlines() if ln.startswith("    "))
        if not already:
            assert "-ULT" not in values, f"{path}/{mr.module}"
            for row in summary_rows(mr.module, mr.conditions,
                                    channel=LoadChannel.LIMIT):
                for key, cell in row.items():
                    assert "-ULT" not in str(key), f"{path}/{mr.module}: {key}"


@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_a_limit_render_states_its_basis_and_points_at_the_deliverable(path):
    """``CONVENTIONS.md`` §3: the basis *and* who applies the factor, in band.

    Note 49 OR-116/OR-117: there is no longer an ULTIMATE deliverable to point
    at, so the pointer becomes an instruction -- apply it in the sizing
    analysis."""
    for mr in _modules(path):
        text = module_text_report(mr.module, mr.conditions,
                                  channel=LoadChannel.LIMIT)
        assert "Loads are LIMIT" in text
        assert "applied nowhere" in text
        assert "sizing analysis" in text


@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_a_limit_render_reports_the_calc_value_unscaled(path):
    """The whole point: the number is the calc's own, whatever the factor is."""
    for mr in _modules(path):
        text = module_text_report(mr.module, mr.conditions,
                                  channel=LoadChannel.LIMIT).replace(",", "")
        for c in mr.conditions:
            if c.safety_factor in (None, 1.0):
                continue        # nothing to distinguish scaled from unscaled
            for v in c.values:
                if not is_load_unit(v.units, v.quantity or "") or not v.value:
                    continue
                assert format_value(v.value) in text, (
                    f"{path}/{mr.module}: {v.label} is not at its LIMIT value")


# --------------------------------------------------------------------------- #
# OR-82 -- a condition that prescribes no factor never prints one
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("channel", list(LoadChannel), ids=lambda c: c.value)
def test_a_factorless_condition_prints_no_factor(channel):
    for mr in _modules(_GA):
        factorless = [c for c in mr.conditions if not prescribes_factor(c)]
        if not factorless:
            continue
        text = module_text_report(mr.module, factorless, channel=channel)
        assert "SF=1.5" not in text, f"{mr.module} claims a factor it lacks"
        for row in summary_rows(mr.module, factorless, channel=channel):
            assert row.get("SF", "") in ("", "N/A"), (mr.module, row.get("SF"))


if __name__ == "__main__":
    import traceback

    failed = 0
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        marks = getattr(fn, "pytestmark", [])
        args = [a for m in marks for a in (m.args[1] if m.name == "parametrize"
                                           else [])]
        try:
            if args:
                for a in args:
                    fn(a)
            else:
                fn()
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)


# --------------------------------------------------------------------------- #
# G-OR-71 -- no path in sloads/ multiplies a load by a safety factor
# --------------------------------------------------------------------------- #
#: The one place a ``* sf`` is not a safety factor. ``FLAPLOAD.BAS`` names the
#: flap area of one side ``SF``, and the port keeps the manual's variable names
#: so the code reads against the listing. Stated here with its reason rather
#: than filtered out silently: an exception nobody can see is how a scan like
#: this rots into a formality.
_NOT_A_SAFETY_FACTOR = {
    "sloads/modules/flap.py": "`sf` is the flap area of one side (sq ft), "
                              "FLAPLOAD.BAS's own name for it",
}

#: ``[\w.]*`` before each name is not decoration: the forms actually removed
#: from the tree were ``* c.safety_factor`` and ``* r.safety_factor``, and a
#: pattern anchored straight to the bare name matches neither. The teeth test
#: below found that gap; without it this scan would have shipped blind to the
#: exact spelling it exists to catch.
_MULTIPLY = re.compile(
    r"\*\s*_sf\(|\*\s*[\w.]*\bsf\b|\bsf\s*\*"
    r"|\*\s*[\w.]*\bsafety_factor\b|\bsafety_factor\s*\*"
    r"|\*\s*[\w.]*\bULTIMATE_FACTOR\b|\bULTIMATE_FACTOR\s*\*")


def test_no_path_in_sloads_multiplies_a_load_by_a_safety_factor():
    """**G-OR-71** -- design note 49 OR-116, the whole-tree form.

    The factor is stated and applied nowhere: not on a module view, not in a
    report, not in the exported deck. This is the structural version of that
    sentence, because prose cannot hold it -- the multiply was removed from 81
    sites across 7 files, and a single one creeping back would be invisible to
    every other gate in the suite except ``G-OR-72``, which sees only the
    balanced deck.

    A text scan is crude on purpose. It cannot be fooled by a helper's name or
    by which module the arithmetic hides in, and its one false positive is
    named above with the reason it is not a safety factor.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offenders = []
    for dirpath, _dirs, files in os.walk(os.path.join(root, "sloads")):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if rel in _NOT_A_SAFETY_FACTOR:
                continue
            with open(path, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    code = line.split("#", 1)[0]
                    if _MULTIPLY.search(code):
                        offenders.append(f"{rel}:{n}: {line.strip()}")
    assert not offenders, (
        "a load is multiplied by a safety factor; the factor is stated and "
        "applied nowhere (note 49 OR-116):\n  " + "\n  ".join(offenders))


def test_the_g_or_71_scan_would_catch_a_multiply():
    """The scan's teeth, since a pattern that matches nothing proves nothing."""
    assert _MULTIPLY.search("out = value * sf")
    assert _MULTIPLY.search("row = v.value * c.safety_factor")
    assert _MULTIPLY.search("y = station.myy * r.safety_factor")
    assert _MULTIPLY.search("fz = load.fz * _sf(result)")
    assert _MULTIPLY.search("x = ULTIMATE_FACTOR * limit")
    assert _MULTIPLY.search("x = limit * ULTIMATE_FACTOR")
    # ...and does not fire on reading or stating the factor, which is the whole
    # point: `_sf` and `_sf_str` survive OR-116, only the multiply goes.
    assert not _MULTIPLY.search("sf = _sf(result)")
    assert not _MULTIPLY.search('"SF": _sf_str(sf)')
    assert not _MULTIPLY.search("lf = [cl * q for cl, q in zip(clf, qs)]")
