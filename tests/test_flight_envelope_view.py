"""Flight Envelope page: each form persists only its own fields (M4-22).

The SELECT-inputs form handler used to write the page's *probe* copy of the
project back into session state -- and that copy already carries ``fl_effective``,
the live merge of the "Apply geometry & altitudes" widgets. So pressing **Apply**
inside the SELECT expander silently committed whatever the user had typed into the
geometry form (XTC / XTF / reference Mach / the altitudes editor) without that
form's own Apply ever being pressed: the M2-3 "persist only on Apply" contract,
violated for a different form's fields.

Driven headlessly via ``AppTest``.
"""

import logging
import os
import sys

import pytest
from helpers import apply_button

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEW = os.path.join(_ROOT, "app", "views", "flight_envelope.py")
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")

# Under pytest ``conftest.py`` puts these on the path; the __main__ self-runner
# has to do it itself, or the view fails on ``import app_shell``.
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytest.importorskip("streamlit.testing.v1")

_XTC = "Tail CP X, flaps up XTC (in)"


def _run(project):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(_VIEW, default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _num(at, label):
    hits = [n for n in at.number_input if n.label == label]
    assert hits, f"no number_input labelled {label!r}; have {[n.label for n in at.number_input]}"
    return hits[0]


def test_select_apply_does_not_persist_un_applied_geometry():
    from sloads import io

    project = io.load_project(_GA6)
    before_xtc = project.flight_loads.xtc
    at = _run(project)

    # Type a new XTC into the geometry form but do NOT press its Apply; then
    # Apply the unrelated SELECT-inputs form.
    _num(at, _XTC).set_value(float(before_xtc) + 10.0)
    _num(at, "Basic airfoil Cm (no aileron)").set_value(-0.075)
    apply_button(at, "select_inputs_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]

    saved = at.session_state["project"]
    # (1) The SELECT input this form owns *is* persisted.
    assert saved.select_input.basic_airfoil_cm == pytest.approx(-0.075)
    # (2) The un-applied geometry edit is not.
    assert saved.flight_loads.xtc == pytest.approx(before_xtc)


def test_geometry_apply_still_persists_geometry():
    """Guard against over-narrowing: the geometry form's own Apply still saves."""
    from sloads import io

    project = io.load_project(_GA6)
    before_xtc = project.flight_loads.xtc
    at = _run(project)

    _num(at, _XTC).set_value(float(before_xtc) + 10.0)
    apply_button(at, "flight_geometry_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].flight_loads.xtc == pytest.approx(before_xtc + 10.0)


if __name__ == "__main__":  # zero-dependency-ish fallback (needs streamlit)
    test_select_apply_does_not_persist_un_applied_geometry()
    test_geometry_apply_still_persists_geometry()
    print("ok")
