"""Geometry page Apply must validate before persisting (M2R-6).

The sidebar **Apply geometry** used to store whatever was typed -- including an
invalid wing (e.g. Area S = 0) -- which then crashed ``configuration_properties``
in the page body and hit ``st.stop()``, blanking the *unrelated* empennage /
landing-gear / outline forms further down. The fix validates the candidate layout
first and rejects an invalid Apply with a targeted message, leaving the last valid
layout (and the rest of the page) intact.

Driven headlessly via ``AppTest``.
"""

import logging
import os
import sys

import pytest

from helpers import apply_button

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEW = os.path.join(_ROOT, "app", "views", "configuration_layout.py")
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")

# Under pytest ``conftest.py`` puts these on the path; the __main__ self-runner
# has to do it itself, or the view fails on ``import components``.
for _p in (_ROOT, os.path.join(_ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytest.importorskip("streamlit.testing.v1")


def _run(project):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(_VIEW, default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_invalid_apply_is_rejected_and_page_stays_alive():
    from sloads import io

    project = io.load_project(_GA6)
    before_area = project.geometry.parametric.wing_area_sqft
    assert before_area > 0

    at = _run(project)
    # Drive the wing area to 0 and Apply.
    {n.label: n for n in at.number_input}["Area S (ft²)"].set_value(0.0)
    apply_button(at, "layout_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]

    # (1) The invalid layout was NOT persisted -- the last valid area survives.
    assert at.session_state["project"].geometry.parametric.wing_area_sqft == before_area
    # (2) A targeted rejection message is shown.
    assert any("not applied" in (e.value or "").lower() for e in at.error), \
        [e.value for e in at.error]
    # (3) The page stayed alive: the unrelated empennage & landing-gear forms (which
    #     live *below* the old blanking st.stop()) still render their Apply buttons.
    apply_button(at, "empennage_form")
    apply_button(at, "landing_gear_form")


def test_valid_apply_persists():
    """A valid edit still applies (guard against over-rejection)."""
    from sloads import io

    project = io.load_project(_GA6)
    at = _run(project)
    {n.label: n for n in at.number_input}["Area S (ft²)"].set_value(200.0)
    apply_button(at, "layout_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].geometry.parametric.wing_area_sqft == 200.0
    assert not any("not applied" in (e.value or "").lower() for e in at.error)


if __name__ == "__main__":  # zero-dependency-ish fallback (needs streamlit)
    test_invalid_apply_is_rejected_and_page_stays_alive()
    test_valid_apply_persists()
    print("ok")
