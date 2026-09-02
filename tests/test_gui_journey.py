"""The main GUI walked end to end, as a user walks it (#145).

Per-page coverage is extensive -- ``test_views_smoke`` renders every view,
``test_dirty_flag`` pins OG-F on the three that persist -- and every one of those
tests starts a *fresh* session with a *fresh* project on *one* page. The release
gate above them (``scripts/smoke_test.sh``, RELEASE_PROCESS §3.5) boots both
entry points and checks the root page answers 200. Neither shape can reach a
defect that needs a **journey**: load an example, touch something on one page,
and find the damage two pages later.

Both post-0.8.0 escapes of that shape were found by hand, not by the suite.
#143 needed load-example → Aerodynamic Data → one touch → Flight Envelope; the
schema-58 stale-process incident was likewise only visible by walking a loaded
example through the workflow. This file is that walk, in CI:

* **every bundled example** is loaded,
* **every** ``workflow.py`` step is visited **in order** -- the nav SSOT, so the
  journey cannot rot as pages are added or reordered,
* one **no-op interaction** per editable block on each page: every value-bearing
  widget is set to the value it already has and every ``Apply`` is pressed,
* the session -- widget state included -- is **carried from page to page**, which
  is what makes the walk a journey rather than 22 renders (the stale-widget class
  ``widget_keys`` exists for lives in exactly that carry-over),
* **every registered module** is run at the end, and must either run clean or
  refuse by name with :class:`MissingInputError`,
* and the project is asserted **byte-identical** across the whole walk, because
  no edit was intended anywhere in it.

That last assertion is the #143 catch: silent data *gain* -- a block attached by
a touch, persisted into the saved ``.project.json`` -- shows up here as a diff
against a walk that entered nothing. It is the #51 data-*loss* class from the
other side at the same time; on the first run of this file it caught both, in
one page (see :data:`KNOWN_OPEN` and the fixes in ``app/views/aero_coefficients``).
"""

import glob
import logging
import os
import sys

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEWS_DIR = os.path.join(_ROOT, "app", "views")
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))

# The __main__ self-runner has to put the repo root on the path itself, or every
# view fails on ``import app_shell`` (conftest.py does it under pytest).
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

pytest.importorskip("streamlit.testing.v1")

#: Widget kinds whose value the journey re-enters unchanged. ``st.data_editor``
#: is deliberately absent: AppTest cannot drive a canvas, and the frame it would
#: replay is the one the page just offered -- a no-op by construction that proves
#: nothing here. ``test_oracle_journey`` carries the recorder/replayer for the
#: places where the *frame* is the input under test.
_TOUCHABLE = ("number_input", "checkbox", "selectbox", "text_input", "radio",
              "slider", "multiselect", "text_area", "toggle")


#: Project paths a no-op Apply is **known** to change. All of them are #148,
#: behind the ``app/views/`` freeze lift (#29). Not a tolerance and not a silence: every entry is asserted to still
#: reproduce by :func:`test_the_known_open_diffs_still_reproduce` below, so a fix
#: turns this list red and forces its own removal rather than passing unnoticed.
#: They are the residue of #145's sweep: writes that are deliberate behaviour
#: landing on an Apply that entered nothing, or a rebuild dropping a field its own
#: form does not render, filed rather than fixed under the ``app/views/`` freeze.
KNOWN_OPEN = {
    # -- silent gain: a slice or value attached by an Apply that entered nothing
    "speeds.occupants": "the WTESTIMA seat count seeds occupants on any Apply, "
                        "not only on an edit to it",
    "speeds.mach_limit": "the Mach-limit block is attached with its defaults by "
                         "any Apply on a project that carries none",
    "weight.envelope": "the WTENV block is attached with the form's defaults by "
                       "any Apply on a project that carries none",
    # -- silent loss: a value dropped by a rebuild that does not render it
    "speeds.wing_area_sqft": "the D4.4 Geometry read-through clears the stored "
                             "wing area on any Apply when a wing surface exists",
    "speeds.chosen_va": "cleared by an Apply that does not render the chosen-speed "
                        "overrides",
    "speeds.chosen_vf": "cleared by an Apply that does not render the chosen-speed "
                        "overrides",
    "weight.items.wing_fraction": "the item table's Apply rebuilds each row from "
                                  "its columns and wing_fraction is not one",
    "engines.max_cont_hp": "the engine form renders the power fields for "
                           "reciprocating engines only, and its Apply writes the "
                           "unrendered field back as unset",
    "engines.takeoff_hp": "as engines.max_cont_hp",
    "engines.hub_weight_lb": "as engines.max_cont_hp, for the hub weight",
}

#: Between them these three walk every entry of :data:`KNOWN_OPEN`; see
#: :func:`test_every_known_open_diff_still_reproduces`.
_KNOWN_OPEN_WITNESSES = ("concept_heavy", "atr42_100", "concept_regional_jet")

#: Writes that are the **point** of the button pressed, not a defect. A form
#: whose whole subject is one ``Optional`` block *is* that block's named gesture
#: (#143's rule: created by a named click), so "Apply fuselage moment" storing a
#: disabled fuselage moment is the page doing its job —
#: ``tests/test_aero_coefficients_view.py`` pins that behaviour from the other
#: side. The journey presses every Apply on the page, so it sees these; they are
#: listed apart from :data:`KNOWN_OPEN` because they carry no backlog row and
#: nothing is waiting to fix them.
BY_DESIGN = {
    "aero_coeffs.fuselage_moment": "\"Apply fuselage moment\" is that block's own "
                                   "named gesture",
    "aero_coeffs.lateral_body_aero": "\"Apply lateral body aero\" likewise",
}


def _ids(paths):
    return [os.path.basename(p).replace(".project.json", "") for p in paths]


def _diffs(before, after, path=""):
    """Every leaf where the two project dicts differ, as ``dotted.path`` strings."""
    out = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            out += _diffs(before.get(key), after.get(key),
                          f"{path}.{key}" if path else key)
    elif (isinstance(before, list) and isinstance(after, list)
            and len(before) == len(after)):
        for i, (b, a) in enumerate(zip(before, after)):
            out += _diffs(b, a, f"{path}[{i}]")
    elif before != after:
        out.append(path)
    return out


def _key(diff):
    """A diff path reduced to its :data:`KNOWN_OPEN` key: list indices dropped,
    so ``weight.items[20].wing_fraction`` and ``[21]`` are one entry."""
    import re
    return re.sub(r"\[\d+\]", "", diff)


def _unexpected(diffs):
    """The diffs neither :data:`KNOWN_OPEN` nor :data:`BY_DESIGN` covers."""
    return [d for d in diffs
            if _key(d) not in KNOWN_OPEN and _key(d) not in BY_DESIGN]


def _touch_everything(at):
    """One no-op interaction with every editable block on the rendered page.

    Every value-bearing widget is re-entered with the value it is already
    showing, and every ``st.form_submit_button`` is pressed -- because a widget
    inside a form persists nothing until its Apply, so touching without
    submitting would assert nothing about the pages that matter. An Apply
    pressed over unedited widgets is precisely "no edit intended".

    **Disabled widgets are skipped**, which is what "editable" above has always
    meant: a page disables a control to say this cannot be entered here and now,
    and a journey that drove it anyway would assert about a gesture no browser
    user can make. Streamlit began refusing the interaction outright in 2026-09
    ("Cannot update a disabled radio widget"), which is how the test's own
    contract came to be enforced from the outside; the skip states it from the
    inside, and holds on the versions that still permit it.
    """
    touched = 0
    for kind in _TOUCHABLE:
        for widget in getattr(at, kind, []):
            if getattr(widget, "disabled", False):
                continue
            widget.set_value(widget.value)
            touched += 1
    for button in at.button:
        if getattr(button.proto, "form_id", "") and not getattr(button, "disabled", False):
            button.set_value(True)
    return touched


def _journey(example, touch=True):
    """Walk every workflow step in order on one session. Returns the end state."""
    from streamlit.testing.v1 import AppTest

    from sloads import io
    from sloads import workflow as wf

    project = io.load_project(example)
    before = io.project_to_dict(project)
    state = {"project": project}
    visited = []

    for step in wf.STEPS:
        view = os.path.join(_VIEWS_DIR, f"{step.key}.py")
        at = AppTest.from_file(view, default_timeout=60)
        for key, value in state.items():
            at.session_state[key] = value
        at.run()
        assert not at.exception, (
            f"{step.key} raised on arrival, walking {os.path.basename(example)}: "
            f"{[e.message for e in at.exception]}")
        if touch:
            _touch_everything(at)
            at.run()
            assert not at.exception, (
                f"{step.key} raised on a no-op interaction, walking "
                f"{os.path.basename(example)}: "
                f"{[e.message for e in at.exception]}")
        # Carry the whole session forward -- widget state included. Anything less
        # is 22 fresh sessions, and the class this file exists for lives in what
        # a widget remembers across a page change.
        state = dict(at.session_state.filtered_state)
        visited.append(step.key)

    return state["project"], before, visited


# --------------------------------------------------------------------------- #
# The journey
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _EXAMPLES, ids=_ids(_EXAMPLES))
def test_the_journey(example):
    """One walk, three assertions -- kept in one test because the walk is the
    expensive part and running it three times to ask three questions is the
    whole-pipeline-per-assertion shape #92 exists to remove.

    1. no page raises, on arrival or on one no-op interaction;
    2. the project is unchanged by the walk, bar :data:`KNOWN_OPEN` (OG-F over
       the journey -- the #143 silent-data-gain catch);
    3. every registered module then runs clean or refuses by name (#144's
       class: never an opaque failure two pages downstream).
    """
    from sloads import io, registry
    from sloads import workflow as wf
    from sloads.models import MissingInputError

    project, before, visited = _journey(example)

    assert visited == [s.key for s in wf.STEPS], (
        "the journey did not visit every workflow step in order")

    unexpected = _unexpected(_diffs(before, io.project_to_dict(project)))
    assert not unexpected, (
        f"walking {os.path.basename(example)} changed the project with no edit "
        f"entered anywhere: {unexpected}")

    for name in registry.available():
        try:
            registry.get(name)(project)
        except MissingInputError as exc:
            assert str(exc).strip(), f"{name} refused without naming what is missing"
        except Exception as exc:
            raise AssertionError(
                f"{name} failed on {os.path.basename(example)} after the journey "
                f"with {type(exc).__name__}: {exc}") from exc


# --------------------------------------------------------------------------- #
# The allowlist is asserted, not trusted
# --------------------------------------------------------------------------- #
def test_every_known_open_diff_still_reproduces():
    """Every :data:`KNOWN_OPEN` entry must still happen, or leave the list.

    A carve-out nobody re-measures is how a gate quietly stops testing what it
    claims to (``CLAUDE.md``: no silent caps). The three witness projects between
    them exercise all of them -- an entry that stops reproducing has been fixed,
    and this fails until it is deleted from the list and from the backlog.
    """
    from sloads import io

    seen = set()
    for name in _KNOWN_OPEN_WITNESSES:
        project, before, _ = _journey(
            os.path.join(_ROOT, "examples", f"{name}.project.json"))
        seen |= {_key(d) for d in _diffs(before, io.project_to_dict(project))}

    stale = set(KNOWN_OPEN) - seen
    assert not stale, (
        f"KNOWN_OPEN lists diffs that no longer happen: {sorted(stale)} — fixed, "
        "so delete the entry (and its #148 checklist line) instead of carrying it")


# --------------------------------------------------------------------------- #
# The rule the sweep applied, at its owner
# --------------------------------------------------------------------------- #
def test_an_apply_that_entered_nothing_creates_no_slice():
    """``app_shell.optional_slice``, the single owner of the app-side #143 rule."""
    from app_shell import optional_slice
    from sloads.models import AileronLoadsInput

    blank, filled = AileronLoadsInput(), AileronLoadsInput()
    filled.area_fwd_hinge_sqft = 12.0

    assert optional_slice.entered_nothing(blank)
    assert not optional_slice.entered_nothing(filled)
    # created out of nothing -> not created
    assert optional_slice.store(blank, None) is None
    # entered -> created
    assert optional_slice.store(filled, None) is filled
    # already there -> written back either way, so clearing a field still lands
    assert optional_slice.store(blank, blank) is blank
    # the seed form, for widgets that do not default to the dataclass defaults
    assert optional_slice.store(filled, None, seed=filled) is None
    assert optional_slice.store(filled, None, seed=blank) is filled


# --------------------------------------------------------------------------- #
# Two of the defects this file found on its first run (#145)
# --------------------------------------------------------------------------- #
def test_the_aero_apply_keeps_the_blocks_it_does_not_render():
    """The main Aero Apply rebuilds the whole slice; it must carry every field
    its form does not show. It dropped ``lateral_body_aero`` outright -- a
    populated L-7 block destroyed by pressing Apply on an unrelated form."""
    from streamlit.testing.v1 import AppTest

    from sloads import io
    from sloads.models.inputs import FuselageMomentInput, LateralBodyAeroInput

    project = io.load_project(os.path.join(_ROOT, "examples", "ga6_normal.project.json"))
    project.aero_coeffs.lateral_body_aero = LateralBodyAeroInput(
        enabled=True, cy_beta=-0.5, cn_beta=0.09)
    project.aero_coeffs.fuselage_moment = FuselageMomentInput(
        enabled=True, d_cm_dalpha=0.004)

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "aero_coefficients.py"),
                           default_timeout=60)
    at.session_state["project"] = project
    at.run()
    for button in at.button:
        if getattr(button.proto, "form_id", "") == "aero_coefficients_form":
            button.set_value(True)
    at.run()

    aero = at.session_state["project"].aero_coeffs
    assert aero.lateral_body_aero is not None, "Apply destroyed the L-7 block"
    assert aero.lateral_body_aero.cy_beta == -0.5
    assert aero.lateral_body_aero.cn_beta == 0.09
    assert aero.fuselage_moment is not None and aero.fuselage_moment.enabled


def test_the_aero_apply_does_not_move_the_stall_clamp():
    """``stall_cl`` is the FLTLOADS balance clamp and is not on this form.
    Rebuilding without it left it at ``0.0``, which ``normalize()`` reads as
    missing and refills from CLmax -- ga6 1.41 -> 1.4068, atr42_100 1.55 -> 2.009,
    on an Apply that entered nothing."""
    from streamlit.testing.v1 import AppTest

    from sloads import io

    for name, expected in (("ga6_normal", 1.41), ("atr42_100", 1.55)):
        project = io.load_project(os.path.join(_ROOT, "examples", f"{name}.project.json"))
        assert project.aero_coeffs.cruise.stall_cl == expected, "fixture moved"
        at = AppTest.from_file(os.path.join(_VIEWS_DIR, "aero_coefficients.py"),
                               default_timeout=60)
        at.session_state["project"] = project
        at.run()
        for button in at.button:
            if getattr(button.proto, "form_id", "") == "aero_coefficients_form":
                button.set_value(True)
        at.run()
        assert at.session_state["project"].aero_coeffs.cruise.stall_cl == expected, (
            f"{name}: a no-op Apply moved the stall clamp")


def test_a_module_with_an_invalid_input_is_named_not_fatal_to_the_page():
    """M2R-8 keeps an invalid input from vanishing; it must not take a whole page
    with it. Three bundled examples carry an aileron or flap slice with no area,
    and Results Review and Export were dead on all three (#145)."""
    from sloads import io, registry

    project = io.load_project(os.path.join(_ROOT, "examples", "ga6_normal.project.json"))
    project.aileron_loads.area_fwd_hinge_sqft = 0.0
    project.aileron_loads.area_aft_hinge_sqft = 0.0

    results, failures = registry.run_all_modules_reporting(project)
    assert results, "one bad slice emptied the whole run"
    assert [name for name, _ in failures] == ["aileron"], failures
    assert "area" in str(failures[0][1]), "the failure does not say what is wrong"
    # ...and the calc-side owner still fails the run outright, as M2R-8 requires.
    import pytest as _pytest
    with _pytest.raises(ValueError):
        registry.run_all_modules(project)


if __name__ == "__main__":  # needs streamlit; walks one example for speed
    test_the_journey(os.path.join(_ROOT, "examples", "ga6_normal.project.json"))
    test_every_known_open_diff_still_reproduces()
    test_an_apply_that_entered_nothing_creates_no_slice()
    test_the_aero_apply_keeps_the_blocks_it_does_not_render()
    test_the_aero_apply_does_not_move_the_stall_clamp()
    test_a_module_with_an_invalid_input_is_named_not_fatal_to_the_page()
    print("ok")
