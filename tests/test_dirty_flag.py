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
from helpers import apply_button, widget_editing

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
    """The number widget for a registry ``path`` (shared helper).

    Not ``at.number_input(key=path)``: the shell decorates the key on both sides
    -- the active unit system, the project generation -- and a test that
    hardcoded either would pin another module's implementation detail.
    """
    return widget_editing(at, path)


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


def _value_at(project, path):
    obj = project
    for segment in path.split("."):
        obj = getattr(obj, segment)
    return obj


#: One field pair per affected page shape (#35, CR-A-1): each pair sits in two
#: different record groups under the same missing ancestor, which is exactly
#: where the pending-record clobber lived -- every group used to mint its own
#: blank ancestor and the last one committed won, discarding the other edit.
#:
#: ``landing_loads`` is the exception since note 33. It had three groups under
#: ``landing`` only because the gear geometry was duplicated onto that slice; the
#: consolidation removed the duplicates, so the page now has **one** group and
#: therefore **cannot** exercise the clobber -- the renderer resolves the record
#: once per group, so with one group there is no second walk to mint a second
#: blank. Measured, not assumed: reintroducing CR-A-1 fails the other three cases
#: and this one still passes. It is kept as a plain two-edits-one-rerun check on
#: the page (worth having, and it costs nothing), and the clobber coverage rests
#: on the three multi-group pages above.
_TWO_EDIT_PAIRS = [
    ("configuration_layout",
     ("geometry.parametric.wing_area_sqft", 180.0),
     ("geometry.empennage.htail.htail_area_sqft", 32.5)),
    # v55 (#52): the one airplane length sits directly on geometry.empennage,
    # a scalar group beside the htail record group under the same missing
    # ancestor -- the clobber shape again, and the oracle page's only LF widget.
    ("configuration_layout",
     ("geometry.empennage.airplane_length_in", 318.264),
     ("geometry.empennage.htail.htail_area_sqft", 32.5)),
    ("weight_mass",
     ("weight.estimation.baggage_lb", 120.0),
     ("weight.envelope.gross_weight", 2400.0)),
    ("landing_loads",
     ("landing.tire_od_in", 19.5),
     ("landing.hub_diameter_in", 7.25)),
    ("structural_speeds",
     ("speeds.weight_lb", 1234.0),
     ("speeds.mach_limit.max_operating_altitude_ft", 20000.0)),
]


@pytest.mark.parametrize("key,first,second", _TWO_EDIT_PAIRS,
                         ids=[f"{p[0]}:{p[1][0].rsplit('.', 1)[-1]}" for p in _TWO_EDIT_PAIRS])
def test_two_edits_in_one_rerun_both_persist(key, first, second):
    """#35 (CR-A-1): two widget changes in one rerun -- fast typing,
    ``data_editor`` batching -- must both land, on a blank project where their
    shared ancestor record does not exist yet. Before the fix the two groups
    each created their own detached blank and one edit silently vanished while
    its widget still displayed it."""
    from streamlit.testing.v1 import AppTest

    from sloads.models import Project

    at = AppTest.from_string(_ORACLE_SCRIPT.format(key=key), default_timeout=60)
    at.session_state["project"] = Project(name="")
    at.run()
    _number_for(at, first[0]).set_value(first[1])
    _number_for(at, second[0]).set_value(second[1])
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    project = at.session_state["project"]
    assert _value_at(project, first[0]) == first[1], (
        f"{first[0]} was discarded when {second[0]} was edited in the same rerun")
    assert _value_at(project, second[0]) == second[1], (
        f"{second[0]} was discarded when {first[0]} was edited in the same rerun")


def test_a_typed_zero_lands_in_an_unfilled_optional_field():
    """#35 (CR-A-3): sea level is a real answer. An unfilled Optional scalar
    used to render as ``0.0``, making a deliberate 0 indistinguishable from the
    seed -- it could never be persisted."""
    from streamlit.testing.v1 import AppTest

    from sloads.models import Project

    at = AppTest.from_string(_ORACLE_SCRIPT.format(key="one_engine_out"),
                             default_timeout=60)
    at.session_state["project"] = Project(name="")
    at.run()
    widget = _number_for(at, "one_engine_out.altitude_ft")
    assert widget.value is None, (
        "an unfilled Optional field rendered a fake 0 instead of empty")
    widget.set_value(0.0).run()
    assert not at.exception, [e.message for e in at.exception]
    oeo = at.session_state["project"].one_engine_out
    assert oeo is not None and oeo.altitude_ft == 0.0, (
        "a typed 0 into an unfilled Optional field did not persist")


def test_an_unfilled_optional_field_renders_empty_and_stays_absent():
    """The other half of the CR-A-3 fix: rendering an Optional as empty must
    not turn a plain visit into an edit -- the field stays ``None`` until the
    user actually enters a number."""
    from streamlit.testing.v1 import AppTest

    from sloads import io

    project = io.load_project(_GA6)
    project.speeds.chosen_vc = None
    at = AppTest.from_string(_ORACLE_SCRIPT.format(key="structural_speeds"),
                             default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert _number_for(at, "speeds.chosen_vc").value is None
    assert at.session_state["project"].speeds.chosen_vc is None, (
        "rendering an unfilled Optional field wrote something into it")


class _CurveStub:
    """A container standing in for ``st``: hands ``render_curve`` a crafted
    edited table and records what it captions. ``AppTest`` cannot drive a
    ``data_editor``, so the persist path is exercised by direct call."""

    def __init__(self, edited):
        self._edited = edited
        self.captions = []
        self.frames = []

    def markdown(self, *args, **kwargs):
        pass

    def data_editor(self, frame, *_args, **_kwargs):
        self.frames.append(frame)
        return self._edited

    def caption(self, text):
        self.captions.append(text)


def _rendered_curve(rows):
    """``render_curve`` on a blank surface fed ``rows`` as the edited table."""
    import pandas as pd

    from oracle_app import form
    from sloads.models import SurfaceInput

    record = form.blank(SurfaceInput)
    stub = _CurveStub(pd.DataFrame(rows, columns=["X", "Y"]))
    form.render_curve(record, "geometry.surfaces[].leading_edge",
                      key="t.leading_edge", container=stub)
    return record, stub


def test_an_incomplete_curve_row_is_held_out_and_said_so():
    """#35 (CR-A-6): a row with an empty cell stays out of the stored curve --
    that part is unchanged -- but the page now says so instead of letting the
    half-typed row silently vanish on the next rerun."""
    record, stub = _rendered_curve([[10.0, float("nan")], [1.0, 2.0]])
    assert record.leading_edge == [(1.0, 2.0)], "a complete row must still persist"
    assert stub.captions, "an incomplete row was dropped with no message"

    # An all-empty row is a freshly added one, not a partial entry: no caption.
    record, stub = _rendered_curve([[1.0, 2.0], [float("nan"), float("nan")]])
    assert record.leading_edge == [(1.0, 2.0)]
    assert not stub.captions, "a freshly added blank row must not nag"


def test_a_curve_typed_from_blank_is_numeric():
    """C210-7 (Cessna 210 build review, 2026-08-23): the polyline grid of a blank
    surface is an *empty* frame, and an empty frame's columns are object-typed,
    which the grid renders as text -- so every corner typed from blank came back
    as strings, was stored as string tuples and crashed WINGGEOM on
    ``ytip - yroot``. Two guards: the frame handed to the grid is numeric even
    with no rows, and a cell that still arrives as text is parsed, never stored."""
    import numpy as np

    record, stub = _rendered_curve([])
    assert record.leading_edge == []
    (frame,) = stub.frames
    assert frame.empty
    assert all(np.issubdtype(dt, np.number) for dt in frame.dtypes), (
        f"an empty curve frame must be numeric so the grid takes numbers: {dict(frame.dtypes)}")

    record, _ = _rendered_curve([["28", "0"], ["28", "220.5"]])
    assert record.leading_edge == [(28.0, 0.0), (28.0, 220.5)]
    assert all(isinstance(v, float) for pt in record.leading_edge for v in pt), (
        "a text cell reached the model unparsed")


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
