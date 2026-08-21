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

**Both GUIs owe this contract** (design note 32, OG-F). It is stated once, here,
and asserted twice because the two front-ends are driven differently: ``app/``
has a file per view, and the oracle GUI has one renderer bound to a step key. Its
fourteen pages were all failing this when the guard first reached them -- the
generic renderer attached a record to the project merely to give its widgets
somewhere to write, and rewrote every field it rendered, turning a JSON ``45``
into ``45.0``: the same number, a different file, and an "Unsaved changes" flag
the user never earned. Nine of fourteen pages tripped it on the fully-populated
oracle fixture. The fix is in ``oracle_app/form.py``: a created record stays
detached until the pass leaves something in it, and a write that would not change
the value does not happen. The pair of tests below is what pins it -- a render
changes nothing, **and** an edit still lands, because "never write" would pass
the first one on its own.
"""

import glob
import logging
import os
import sys

import pytest

from helpers import apply_button

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEWS_DIR = os.path.join(_ROOT, "app", "views")
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))

# Under pytest ``conftest.py`` puts these on the path; the __main__ self-runner
# has to do it itself, or every view fails on ``import app_shell``.
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

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

    from sloads import io

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


#: The oracle GUI's page body: one renderer bound to a step key, which is exactly
#: what its ``st.Page`` callable runs. There is no view file to point ``AppTest``
#: at, by design (note 32, G2) -- so the contract is driven through the same
#: entry every page uses.
_ORACLE_SCRIPT = "from oracle_app.form import render_step\nrender_step({key!r})\n"


def _oracle_keys():
    from sloads import workflow as wf

    return sorted(wf.oracle_step_keys())


@pytest.mark.parametrize("key", _oracle_keys())
@pytest.mark.parametrize("example", _EXAMPLES, ids=_ids(_EXAMPLES))
def test_an_oracle_page_render_leaves_the_project_unchanged(key, example):
    """The same contract as above, for the second GUI -- every page, not a
    chosen three: fourteen pages from one renderer means one mistake mutates
    all of them."""
    from streamlit.testing.v1 import AppTest

    from sloads import io

    project = io.load_project(example)
    before = io.project_to_dict(project)

    at = AppTest.from_string(_ORACLE_SCRIPT.format(key=key), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]

    after = io.project_to_dict(at.session_state["project"])
    assert after == before, (
        f"the oracle GUI's {key} page mutated the project on render for "
        f"{os.path.basename(example)} (dirty flag would trip with no user edit)"
    )


def _number_for(at, path):
    """The number widget for a registry ``path``.

    Not ``at.number_input(key=path)``: the shell's ``unit_number_input``
    appends the active unit system to the key so a system switch re-seeds the
    widget, and a test that hardcoded the suffix would pin an implementation
    detail of another module.
    """
    for widget in at.number_input:
        if widget.key == path or widget.key.startswith(f"{path}_"):
            return widget
    raise KeyError(f"no number input for {path!r}")


def test_an_oracle_page_still_persists_what_the_user_types():
    """The other half, without which "never write anything" would pass.

    Two directions: a field on a record the project already has, and a field on
    a record it does not -- where the write has to attach the record too, or the
    oracle GUI could not build a project from scratch, which is its whole job.
    """
    from streamlit.testing.v1 import AppTest

    from sloads import io
    from sloads.models import Project

    project = io.load_project(_GA6)
    at = AppTest.from_string(_ORACLE_SCRIPT.format(key="structural_speeds"),
                             default_timeout=60)
    at.session_state["project"] = project
    at.run()
    _number_for(at, "speeds.weight_lb").set_value(3407.0).run()
    assert at.session_state["project"].speeds.weight_lb == 3407.0

    blank = AppTest.from_string(_ORACLE_SCRIPT.format(key="structural_speeds"),
                                default_timeout=60)
    blank.session_state["project"] = Project(name="")
    blank.run()
    assert blank.session_state["project"].speeds is None, (
        "an untouched page attached its record anyway")
    _number_for(blank, "speeds.weight_lb").set_value(1234.0).run()
    speeds = blank.session_state["project"].speeds
    assert speeds is not None and speeds.weight_lb == 1234.0, (
        "a typed value did not attach the record it belongs to")




# Apply buttons are selected through their **form key**, never positionally
# (M4-12a): ``at.button`` is one flat list across every form on the page, so an
# index silently rebinds to a different form as soon as a view gains, loses or
# reorders one -- and the test keeps passing while asserting something else. See
# ``helpers.apply_button``, which also fails loudly on an unknown key.


def test_mach_limit_persists_only_on_apply():
    """structural_speeds: MACHLIM is absent after a plain render, present after Apply."""
    from streamlit.testing.v1 import AppTest

    from sloads import io

    project = io.load_project(_GA6)
    project.speeds.mach_limit = None  # observe a fresh seed

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "structural_speeds.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].speeds.mach_limit is None, "render seeded MACHLIM"

    apply_button(at, "mach_limit_form").set_value(True).run()
    assert at.session_state["project"].speeds.mach_limit is not None, "Apply did not persist"


def test_flight_loads_persists_only_on_apply():
    """flight_envelope: flight_loads is absent after a plain render, present after Apply."""
    from streamlit.testing.v1 import AppTest

    from sloads import io

    project = io.load_project(_GA6)
    project.flight_loads = None  # observe a fresh seed

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "flight_envelope.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].flight_loads is None, "render seeded flight_loads"

    apply_button(at, "flight_geometry_form").set_value(True).run()
    assert at.session_state["project"].flight_loads is not None, "Apply did not persist"


def test_landing_cases_are_seeded_from_wtenv_only_on_the_button():
    """M2R-5(a), re-homed by decision G-3: the WTENV seed for LANDLOAD's three
    loadings moved to the Weight/CG page's Payload Cases tab with the editor, and
    is still **offered**, never written by a plain render.

    The seed itself is now a pure calc helper (:func:`sloads.cg_cases.
    seed_landing_cases`) rather than view code, so the numbers are asserted
    directly; the page is still driven through ``AppTest`` for the half that
    matters here -- that a plain render writes nothing.
    """
    from sloads import io
    from sloads.cg_cases import seed_landing_cases
    from sloads.models import GROUND_CASE_ROLE_ORDER

    project = io.load_project(_GA6)
    before = io.project_to_dict(project)

    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "weight_mass.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert io.project_to_dict(at.session_state["project"]) == before, \
        "rendering the page mutated the project"

    # The seeded values themselves: WTENV stations interpolated at each row's own
    # weight (M4-17c). The aft station is the aft-gross limit (85.11); 76.12 in at
    # the 3230 lb max landing weight (Appendix A p230; between 72.643 in @ 2800 lb
    # and 77.490 in @ 3400 lb) and 72.64 in at the 2800 lb light weight. It was
    # 72.6 for both forward rows before M4-17c (the weight-agnostic hull).
    fresh = io.load_project(_GA6)
    fresh.weight.cg_cases = [c for c in fresh.weight.cg_cases if c.role is None]
    seeded, missing = seed_landing_cases(fresh)
    assert not missing, missing
    assert sorted(round(c.xcg, 1) for c in seeded) == [72.6, 76.1, 85.1]
    assert sorted(c.weight_lb for c in seeded) == [2800.0, 3230.0, 3230.0]
    # The waterline comes from the WTONECG mass slice the example carries (M4-17a);
    # it is never zero-filled (M4-17c).
    assert all(c.zcg > 0 for c in seeded), [c.zcg for c in seeded]
    assert [c.role for c in seeded] == list(GROUND_CASE_ROLE_ORDER)


def test_select_inputs_persist_only_on_apply():
    """M2R-5(b): the Critical Loads tab's SELECT-input form (aileron DN / basic Cm /
    wing weight) persists to project.select_input only on Apply."""
    from streamlit.testing.v1 import AppTest

    from sloads import io

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
    apply_button(at, "select_inputs_form").set_value(True).run()

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
    test_landing_cases_are_seeded_from_wtenv_only_on_the_button()
    test_select_inputs_persist_only_on_apply()
    print("ok")
