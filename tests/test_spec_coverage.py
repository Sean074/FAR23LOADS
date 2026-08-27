"""Every registered module is specified in `PROGRAM_SPEC.md` (R6-D6 guard).

The document claims to be the per-module spec ("inputs/outputs/FAR conditions
per module"), and until 2026-08-15 two registered modules -- ``balance``, which
carries the mission's primary deliverable, and ``tail_span`` -- had no section
at all. Nothing could have caught that: the correspondence between a registry
name and its heading (``weight_estimate`` -> ``WTESTIMA``) lived only in a
reader's head.

`sloads/spec_names.py` owns that correspondence and this is its drift guard, in
both directions: a new module with no section fails, and a heading that matches
neither a module nor the stated non-module allowlist fails too.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.modules  # noqa: F401  (module registration)
from sloads.registry import available
from sloads.spec_names import NON_MODULE_SECTIONS, SPEC_HEADINGS

_SPEC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "10_standard", "PROGRAM_SPEC.md")


def _headings():
    """The leading token of every ``###`` section: the text before the em dash,
    minus any trailing ``(Step ...)`` parenthetical."""
    with open(_SPEC, encoding="utf-8") as fh:
        lines = [ln[4:].strip() for ln in fh if ln.startswith("### ")]
    out = []
    for line in lines:
        token = re.split(r"\s+—\s+", line, maxsplit=1)[0]
        out.append(token.split(" (")[0].strip())
    return out


def test_every_registered_module_has_a_spec_section():
    """The finding itself: a registered module with no section of its own."""
    headings = set(_headings())
    for name in available():
        heading = SPEC_HEADINGS.get(name)
        assert heading, (
            f"module {name!r} has no PROGRAM_SPEC heading in "
            f"sloads/spec_names.py -- add the module's section, then the map row")
        assert heading in headings, (
            f"module {name!r} maps to PROGRAM_SPEC heading {heading!r}, "
            f"which the document does not have")


def test_the_map_covers_the_registry_exactly():
    """No stale rows: a removed or renamed module fails here, not silently."""
    assert set(SPEC_HEADINGS) == set(available())


def test_every_spec_section_is_a_module_or_a_stated_exception():
    """The reverse direction -- a section that is not a calc module says so."""
    known = set(SPEC_HEADINGS.values()) | NON_MODULE_SECTIONS
    for token in _headings():
        assert token in known, (
            f"PROGRAM_SPEC section {token!r} is neither a registered module nor "
            f"on the NON_MODULE_SECTIONS allowlist in sloads/spec_names.py")


def test_the_allowlist_is_not_a_place_to_hide_a_module():
    """An exception that is really a module would defeat the guard above."""
    assert not (NON_MODULE_SECTIONS & set(available()))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
