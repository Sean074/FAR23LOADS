"""A render pass must not mutate the project (M2-3, review G4).

The sidebar's "Unsaved changes" flag is ``project_to_dict(p) != saved_snapshot``
(``app/Home.py``). Two views used to *auto-seed* derived slices on every render --
``flight_envelope`` wrote ``flight_loads`` and ``structural_speeds`` wrote
``speeds.mach_limit`` -- so merely visiting them tripped the dirty flag with zero
user edits and fired the discard-confirm dialog spuriously.

These views now persist only on an explicit **Apply** (``st.form_submit_button``),
computing the live diagram from an in-memory copy. This test drives each view via
``AppTest`` with **no widget interaction** and asserts the seeded project's
serialized form is byte-for-byte unchanged -- the regression guard for the fix.
"""

import glob
import logging
import os

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEWS_DIR = os.path.join(_ROOT, "app", "views")
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))

# The views whose render must not mutate the project: the two the G4 review flagged
# (structural_speeds/flight_envelope) plus landing_loads (M2R-4 killed its on-render
# mutation, M2R-5 added a form-gated CG editor + SELECT-input form -- both persist only
# on Apply). Each reaches its persist path on an example that carries the upstream
# slices; on a sparser one it gates out early -- either way a plain render is a no-op.
_VIEWS = ["structural_speeds.py", "flight_envelope.py", "landing_loads.py"]

pytest.importorskip("streamlit.testing.v1")


def _ids(paths):
    return [os.path.basename(p) for p in paths]


@pytest.mark.parametrize("view", _VIEWS)
@pytest.mark.parametrize("example", _EXAMPLES, ids=_ids(_EXAMPLES))
def test_render_leaves_project_unchanged(view, example):
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(example)
    before = io.project_to_dict(project)  # a fresh snapshot dict

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, view), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]

    after = io.project_to_dict(at.session_state["project"])
    assert after == before, (
        f"{view} mutated the project on render for {os.path.basename(example)} "
        "(dirty flag would trip with no user edit)"
    )


_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


def _apply_buttons(at):
    return [b for b in at.button if "Apply" in (b.label or "")]


def test_mach_limit_persists_only_on_apply():
    """structural_speeds: MACHLIM is absent after a plain render, present after Apply."""
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(_GA6)
    project.speeds.mach_limit = None  # observe a fresh seed

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "structural_speeds.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].speeds.mach_limit is None, "render seeded MACHLIM"

    # The Speed-Altitude tab's Apply is the second "Apply" submit button.
    _apply_buttons(at)[1].set_value(True).run()
    assert at.session_state["project"].speeds.mach_limit is not None, "Apply did not persist"


def test_flight_loads_persists_only_on_apply():
    """flight_envelope: flight_loads is absent after a plain render, present after Apply."""
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(_GA6)
    project.flight_loads = None  # observe a fresh seed

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "flight_envelope.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].flight_loads is None, "render seeded flight_loads"

    _apply_buttons(at)[0].set_value(True).run()
    assert at.session_state["project"].flight_loads is not None, "Apply did not persist"


def test_landing_cg_editor_seeds_and_persists_on_apply():
    """M2R-5(a): the Landing Loads CG editor seeds from WTENV (fwd/aft stations +
    gross/fwd-regardless weights) but persists to landing.cg_cases only on Apply."""
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(_GA6)
    project.landing.cg_cases = []  # observe a fresh WTENV seed

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "landing_loads.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    # A plain render must not persist the seed.
    assert at.session_state["project"].landing.cg_cases == [], "render seeded cg_cases"

    _apply_buttons(at)[0].set_value(True).run()
    cases = at.session_state["project"].landing.cg_cases
    assert len(cases) == 3, "Apply did not persist the 3 seeded CG cases"
    # WTENV seed: aft-most / fwd-most structural CG stations (72.64 / 85.11 for GA6).
    xcgs = sorted(round(c.xcg, 1) for c in cases)
    assert xcgs == [72.6, 72.6, 85.1], xcgs
    # Weights: two max-landing rows at max_landing_weight, the light row at fwd-regardless.
    assert sorted(c.weight_lb for c in cases) == [2800.0, 3230.0, 3230.0]


def test_select_inputs_persist_only_on_apply():
    """M2R-5(b): the Critical Loads tab's SELECT-input form (aileron DN / basic Cm /
    wing weight) persists to project.select_input only on Apply."""
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(_GA6)
    project.select_input = None  # observe a fresh render

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "flight_envelope.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].select_input is None, "render seeded select_input"

    ni = {n.label: n for n in at.number_input}
    ni["Full-down aileron deflection, DN (deg)"].set_value(20.0)
    ni["Basic airfoil Cm (no aileron)"].set_value(-0.05)
    ni["Wing weight, WW (lb)"].set_value(300.0)
    # The SELECT-inputs form button is the only one labelled exactly "Apply" (the V-n
    # tab's is "Apply geometry & altitudes").
    select_apply = next(b for b in at.button if b.label == "Apply")
    select_apply.set_value(True).run()

    si = at.session_state["project"].select_input
    assert si is not None, "Apply did not persist select_input"
    assert si.full_down_aileron_deg == 20.0
    assert si.basic_airfoil_cm == -0.05
    assert si.wing_weight_lb == 300.0


if __name__ == "__main__":  # zero-dependency-ish fallback (needs streamlit)
    for _view in _VIEWS:
        for _ex in _EXAMPLES:
            test_render_leaves_project_unchanged(_view, _ex)
    test_mach_limit_persists_only_on_apply()
    test_flight_loads_persists_only_on_apply()
    test_landing_cg_editor_seeds_and_persists_on_apply()
    test_select_inputs_persist_only_on_apply()
    print("ok")
