"""The two load channels: what each renders, and what protects the frozen GUI.

Design note 48. ``report.LoadChannel`` splits every per-module renderer into an
ULTIMATE channel (case selection, the export deck, the case index, the oracle
technical report) and a LIMIT channel (the CLI and the app's per-module analysis
surfaces, where the factor is stated and not applied).

Gates here:

* **G-OR-44** -- the default is ULTIMATE, so a caller that passes nothing gets
  today's behaviour. This is what keeps the frozen ``oracle_app`` output
  unchanged *by construction* rather than by inspection (OR-77), and it is
  asserted at the call sites as well as in the renderers.
* **G-OR-47** -- a LIMIT render applies no factor, emits no ``-ULT`` marker, and
  states its basis with a pointer to the ultimate deliverables.
* the ``N/A`` half of **OR-82** on both channels: a condition prescribing no
  factor never prints one.
"""

import glob
import os
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
# G-OR-44 -- the default is ULTIMATE
# --------------------------------------------------------------------------- #
def test_the_renderers_default_to_ultimate():
    """No argument means today's behaviour, in every channelled renderer."""
    mr = [m for m in _modules(_GA) if m.module == "engine"][0]
    for default, explicit in (
        (module_text_report("Engine", mr.conditions),
         module_text_report("Engine", mr.conditions,
                            channel=LoadChannel.ULTIMATE)),
        (summary_rows(mr.module, mr.conditions),
         summary_rows(mr.module, mr.conditions, channel=LoadChannel.ULTIMATE)),
    ):
        assert default == explicit


def test_the_frozen_oracle_gui_passes_no_channel():
    """OR-77 in the form that actually protects the file.

    ``oracle_app/results.py`` is in the OR-13 frozen set and cannot be edited to
    opt in. The default is ULTIMATE *so that* it needs no edit -- an assertion
    that is only true while the file names no channel, which is what this reads.
    """
    path = os.path.join(_ROOT, "oracle_app", "results.py")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    assert "LoadChannel" not in src, (
        "oracle_app/results.py names a channel; it is frozen (OR-13) and the "
        "ULTIMATE default exists precisely so it does not have to.")


def test_the_ultimate_channel_still_applies_the_factor():
    mr = [m for m in _modules(_GA) if m.module == "engine"][0]
    text = module_text_report("Engine", mr.conditions)
    assert "Loads are ULTIMATE" in text
    assert "-ULT" in text
    condition = next(c for c in mr.conditions
                     if any(is_load_unit(v.units, v.quantity or "")
                            for v in c.values))
    load = next(v for v in condition.values
                if is_load_unit(v.units, v.quantity or ""))
    assert condition.safety_factor is not None
    assert format_value(load.value * condition.safety_factor) in text


# --------------------------------------------------------------------------- #
# G-OR-47 -- what a LIMIT render says, and does not say
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_a_limit_render_never_marks_a_value_ultimate(path):
    for mr in _modules(path):
        text = module_text_report(mr.module, mr.conditions,
                                  channel=LoadChannel.LIMIT)
        assert "-ULT" not in text, f"{path}/{mr.module}"
        assert "[ULTIMATE" not in text, f"{path}/{mr.module}"
        for row in summary_rows(mr.module, mr.conditions,
                                channel=LoadChannel.LIMIT):
            for key, cell in row.items():
                assert "-ULT" not in str(key), f"{path}/{mr.module}: {key}"


@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_a_limit_render_states_its_basis_and_points_at_the_deliverable(path):
    """``CONVENTIONS.md`` §3: the marker *and* the pointer, in band."""
    for mr in _modules(path):
        text = module_text_report(mr.module, mr.conditions,
                                  channel=LoadChannel.LIMIT)
        assert "Loads are LIMIT" in text
        assert "not applied" in text
        assert "deliverables" in text


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
