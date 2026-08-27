"""The oracle GUI's acceptance gates (design note 32, step OG-D).

Three gates from the note, plus the guards the generic renderer needs to stay
honest:

* **G1 — no dual path.** ``oracle_app/`` imports its numbers from ``sloads`` and
  the shared shell only: no unit factor of its own, no arithmetic library, no
  private CSV writer. The second front-end exists to ask for less, not to
  recompute anything.
* **G2 — the page set is derived.** The rendered pages are exactly
  :func:`sloads.workflow.oracle_steps`, and no module in the GUI holds a literal
  list of step keys. Adding a ``bas`` to a workflow step must add a page with no
  edit to the GUI at all -- so the test that matters is not "the list is right"
  but "there is no list".
* **G6 — round-trip.** A project the oracle GUI would save opens in ``app/``
  unchanged, and re-saves byte-identically. OG-13's promise from the outside:
  one schema, two front-ends, no hop.

The smoke run is the one that earns its keep day to day: fourteen pages built
from one renderer means a single introspection mistake takes out every page, and
a registry row whose type the renderer cannot map is a crash rather than a
missing widget.
"""

import ast
import glob
import io as _io
import json
import logging
import os
import re
from itertools import takewhile

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

from helpers import widget_editing, widgets_editing  # noqa: E402

from app_shell.components import active_system  # noqa: E402
from sloads import (
    UnitSystem,
    io,
)
from sloads import field_registry as fr  # noqa: E402
from sloads import workflow as wf  # noqa: E402
from sloads.field_registry import reduce_to_oracle_inputs  # noqa: E402
from sloads.units import AVIATION_STANDARD, to_display  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GUI = os.path.join(_ROOT, "oracle_app")
_ENTRYPOINT = os.path.join(_GUI, "Oracle.py")
_EXAMPLES = os.path.join(_ROOT, "examples")
_EXAMPLE = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_SOURCES = sorted(glob.glob(os.path.join(_GUI, "*.py")))
#: The shared shell renders *inside* this GUI, so a download it offers is a
#: download the oracle GUI offers. Scanning only ``oracle_app/`` made G7's
#: completeness argument true of half the running app (review CR-A-8).
_SHELL = os.path.join(_ROOT, "app_shell")
_DOWNLOAD_SOURCES = _SOURCES + sorted(glob.glob(os.path.join(_SHELL, "*.py")))

pytest.importorskip("streamlit.testing.v1")


def _file_name_of(call):
    """The ``file_name=`` a ``download_button`` call writes, as a literal.

    An f-string is flattened to its literal parts (``f"{fname}.project.json"``
    -> ``".project.json"``), which is all this gate needs: the extension is what
    says whether the file is a load deliverable. ``None`` when the argument is
    not a string literal at all -- which fails the check rather than passing it.
    """
    for kw in call.keywords:
        if kw.arg != "file_name":
            continue
        node = kw.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(v.value for v in node.values
                           if isinstance(v, ast.Constant) and isinstance(v.value, str))
        # The shell names the project file through its one sanitiser (#65);
        # the call *is* the statement that the file is ``<stem>.project.json``.
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "project_filename":
            from sloads.io import PROJECT_SUFFIX
            return PROJECT_SUFFIX
        # Likewise the results zip's one naming owner (C210-45): the call *is*
        # the statement that the file is ``<stem>_results.zip``
        # (``test_results_zip.py`` asserts the suffix on the real name).
        if isinstance(node, ast.Call) and (
                getattr(node.func, "id", "") or getattr(node.func, "attr", "")
        ) in ("results_zip_name", "_results_zip_name"):
            return "_results.zip"
    return None


def _parse(path):
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def _seeded():
    return io.load_project(_EXAMPLE)


# --------------------------------------------------------------------------- #
# G1 -- no dual path
# --------------------------------------------------------------------------- #
#: What the oracle GUI may import. ``sloads`` and ``app_shell`` are the owners;
#: ``streamlit``/``pandas`` are the presentation layer; the rest is stdlib
#: introspection the generic renderer is built out of. A numerical library is
#: deliberately absent: there is nothing here to compute.
_ALLOWED_IMPORTS = {
    "sloads", "app_shell", "oracle_app", "streamlit", "pandas",
    "dataclasses", "typing", "enum", "__future__",
    # stdlib formatting for the C210-24 not-ready traceback (#99) -- display
    # of an exception the calc already raised, nothing to compute with.
    "traceback",
}

def test_the_oracle_gui_imports_only_owners_and_presentation():
    """Gate G1, first half: nothing to compute with, nowhere else to get a number."""
    offenders = []
    for path in _SOURCES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                roots = [(node.module or "").split(".")[0]]
            else:
                continue
            for root in roots:
                if root and root not in _ALLOWED_IMPORTS:
                    offenders.append(f"{os.path.relpath(path, _ROOT)}: imports {root!r}")
    assert not offenders, (
        "the oracle GUI imports something outside sloads / app_shell / the "
        "presentation layer -- it is a front-end, not a second analysis path "
        "(note 32, OG-1/G1):\n" + "\n".join(offenders))


def test_the_oracle_gui_holds_no_unit_factor_of_its_own():
    """Gate G1, second half: every conversion goes through ``sloads.units``.

    The scan is not here. It lives with the factors it derives from --
    ``test_units.test_si_factor_literals_have_one_owner`` -- and covers all four
    packages at once, because a second regex over a second hand-typed list of
    the same numbers is the duplication G1 is about (review PB-12: this file's
    copy held eight literals, ``test_units``'s held five others, and neither
    looked at ``app_shell/``, which renders inside this GUI).

    What is asserted here is that the delegation still points at this GUI: an
    owner's scan that quietly stops covering ``oracle_app/`` would leave G1
    green over an unscanned front-end.
    """
    from test_units import _FACTOR_OWNER, _FACTOR_SCAN_PACKAGES

    assert os.path.basename(_GUI) in _FACTOR_SCAN_PACKAGES, (
        "the units factor scan no longer covers the oracle GUI -- G1's second "
        "half is not being checked anywhere")
    assert os.path.basename(_SHELL) in _FACTOR_SCAN_PACKAGES, (
        "the shared shell renders inside this GUI; a factor literal there is a "
        "factor literal here")
    assert os.path.isfile(os.path.join(_ROOT, _FACTOR_OWNER))


def test_the_oracle_gui_writes_no_deliverable_of_its_own():
    """Gate G1, third half: no private CSV writer. Every file the GUI offers is
    rendered by ``sloads.io``/``sloads.report`` or by ``app_shell.limit_csv``
    (OG-6 as amended) -- a ``to_csv`` here would be a fourth format nothing
    else in the project can vouch for."""
    offenders = []
    for path in _SOURCES:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        for marker in ("to_csv(", "csv.writer", "DictWriter"):
            if marker in source:
                offenders.append(f"{os.path.relpath(path, _ROOT)}: {marker}")
    assert not offenders, (
        "the oracle GUI builds a CSV itself -- route it through the existing "
        "owners (note 32, OG-6/G7):\n" + "\n".join(offenders))


# --------------------------------------------------------------------------- #
# G2 -- the page set is derived
# --------------------------------------------------------------------------- #
def test_there_is_no_page_list_in_the_gui():
    """Gate G2, the part that actually prevents drift.

    A correct hand-written page list is still a hand-written page list: it stops
    being correct the day a workflow step gains a ``bas``. So the assertion is
    that no step key appears as a string literal anywhere in the GUI at all.
    """
    keys = set(wf.BY_KEY)
    offenders = []
    for path in _SOURCES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Constant) and node.value in keys:
                offenders.append(
                    f"{os.path.relpath(path, _ROOT)}:{node.lineno}: {node.value!r}")
    assert not offenders, (
        "a workflow step key is written out in the oracle GUI -- its page set "
        "is derived from workflow.oracle_steps() and must stay so (OG-2/G2):\n"
        + "\n".join(offenders))


def _module_assignments(tree):
    """``{name: value node}`` for the entry point's module-level assignments."""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = node.value
    return out


def _derives_from(node, assignments, wanted, _seen=None):
    """True if ``node`` reaches a call to ``wanted``, following module names."""
    _seen = _seen or set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Attribute) and inner.attr == wanted:
            return True
        if isinstance(inner, ast.Name) and inner.id in assignments and inner.id not in _seen:
            _seen.add(inner.id)
            if _derives_from(assignments[inner.id], assignments, wanted, _seen):
                return True
    return False


def test_the_entry_point_navigates_the_derived_step_set():
    """Gate G2: the navigated page set is built from ``oracle_steps()`` -- and
    the page set the link helper resolves against is *the same one* (OG-F).

    Two page sets built from the same source would still drift the day one of
    them gains a filter; the assertion is that there is one set, derived, used
    twice.
    """
    tree = ast.parse(open(_ENTRYPOINT, encoding="utf-8").read())
    assignments = _module_assignments(tree)
    calls = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in ("navigation", "register_pages"):
                calls.setdefault(name, []).append(node)

    assert len(calls.get("navigation", [])) == 1, "expected exactly one st.navigation call"
    assert len(calls.get("register_pages", [])) == 1, (
        "the oracle GUI must register its page set exactly once, for the links")
    for name, call in ((n, c[0]) for n, c in calls.items()):
        assert _derives_from(call.args[0], assignments, "oracle_steps"), (
            f"{name}() is not built from workflow.oracle_steps()")


def test_the_derived_page_set_is_the_fourteen_oracle_steps():
    """The set itself, so a change to ``oracle_steps`` is visible here too.

    ``oracle_steps()`` *is* ``STEPS`` filtered by ``oracle_step_keys()``, so
    asserting one against the other compares the workflow with itself (review
    PB-10). What is worth pinning is the two facts the GUI depends on: the order
    is the workflow's, and the selection is a strict subset of it -- fourteen of
    the twenty-two, not a re-ordering and not the whole suite.
    """
    keys = [s.key for s in wf.oracle_steps()]
    order = [s.key for s in wf.STEPS]
    assert set(keys) < set(order), "the oracle GUI must carry a subset of the workflow"
    assert keys == [k for k in order if k in set(keys)], (
        "the oracle GUI's pages are in an order of their own -- they are the "
        "workflow's steps and must appear in the workflow's sequence")
    assert len(keys) == 14


# --------------------------------------------------------------------------- #
# The renderer
# --------------------------------------------------------------------------- #
#: A one-page script: the whole GUI body is ``render_step`` bound to a key, so
#: this is exactly what ``Oracle.py``'s navigation runs for that page.
_PAGE_SCRIPT = "from oracle_app.form import render_step\nrender_step({key!r})\n"


def _render(key, project=None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_PAGE_SCRIPT.format(key=key), default_timeout=60)
    at.session_state["project"] = project if project is not None else _seeded()
    at.run()
    return at


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_oracle_page_renders(key):
    """One renderer, fourteen pages: an introspection mistake takes out all of
    them, and a field type it cannot map is a crash, not a missing widget."""
    at = _render(key)
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_oracle_page_renders_on_an_empty_project(key):
    """The state the GUI is *for*: a blank project, every slice absent. The
    renderer has to create the records rather than gate on them."""
    from sloads import Project

    at = _render(key, Project(name=""))
    assert not at.exception, [e.message for e in at.exception]


# --------------------------------------------------------------------------- #
# Scope -- concept mode is not this GUI's (OG-1; review 2026-08-20 CR-A-4)
# --------------------------------------------------------------------------- #
# The shared header rendered the applicability banner with its default
# ``switch_action=True``, so an out-of-band airplane got a **Switch to Concept**
# button on a front-end that carries no concept page and shows no concept field:
# one click wrote ``speeds.category="C"`` and seeded ``chosen_n``/``chosen_nneg``
# into a project the user could then only get back in ``app/``. The warning
# itself belongs here -- it says the numbers are an extrapolation -- so the fix
# is warning-without-action, not ``banner=False``.
def _out_of_band():
    """The Appendix-A GA single re-stated above the 12,500 lb FAR 23 ceiling.

    Both members move together because the gate reads the MTOW SSOT (G-14) and
    ``speeds.weight_lb`` is its derived read.
    """
    project = _seeded()
    project.weight.max_takeoff_weight_lb = 20000.0
    project.speeds.weight_lb = 20000.0
    return project


def test_an_out_of_band_airplane_is_warned_but_offered_no_concept_switch():
    """The banner states the exceedance; the action that leaves this GUI's
    scope is gone."""
    at = _render(sorted(wf.oracle_step_keys())[0], _out_of_band())
    assert not at.exception, [e.message for e in at.exception]

    warnings = " ".join(w.value for w in at.warning)
    assert "Exceeds FAR 23 applicability" in warnings, (
        "the oracle GUI stopped telling an out-of-band airplane its results are "
        "a concept-mode extrapolation")
    labels = [b.label for b in at.button]
    assert "Switch to Concept" not in labels, (
        "the oracle GUI offers the switch to concept mode, which it does not "
        "carry a single page or field for (OG-1, CR-A-4)")


# --------------------------------------------------------------------------- #
# The entry-error channel (#82, C210-35)
# --------------------------------------------------------------------------- #
def _contradictory_wing_row():
    """The C210-35 entry: a wing-tagged mass row also carrying ``wing_fraction``.

    ``wing_fraction`` is the wing-reacted fraction of a row tagged to *another*
    component, so 1 on a wing row is a contradiction the checks name. This is the
    exact entry that survived a whole build review unshown.
    """
    from sloads.models import MassComponent

    project = _seeded()
    item = next(i for i in project.weight.items
                if i.component == MassComponent.WING)
    item.wing_fraction = 1.0
    return project


def test_an_entry_error_is_shown_on_the_page_that_owns_it():
    """The oracle GUI renders the ``consistency_warnings`` channel (#82).

    Until this, ``oracle_app``/``app_shell`` had no consumer of
    ``ConsistencyWarning`` at all: a page-targeted entry-error channel that is
    part of the analysis contract (C210-15) was dark exactly where entries are
    made. Read from the rendered warnings, not from the source.
    """
    at = _render("weight_mass", _contradictory_wing_row())
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "wing_fraction" in shown, (
        "the oracle GUI's weights page does not show the entry-error warning "
        "its own validator raises")


def test_a_page_states_the_later_page_its_numbers_depend_on():
    """The #69 mark, read from the rendered page (PB-15/PB-19).

    Flap Loads computes its FAR 23.457(b) slipstream case from an engine record
    entered two pages later. With the engine present the numbers are final, and
    the page says where they came from -- provenance, not an alarm.
    """
    at = _render("flap_loads")
    assert not at.exception, [e.message for e in at.exception]
    said = " ".join((c.value or "") for c in at.caption)
    assert "engines" in said and "Engine Mount Loads" in said, (
        "the Flap page does not say its numbers read the engine record entered "
        "on a later page")


def test_a_page_warns_while_the_later_page_is_still_empty():
    """The state the defect was filed on: the page shows a complete-looking
    answer, the user downloads it, fills the Engine page, and the governing flap
    load moves ~19 % (the C210's slipstream case). The caption becomes a warning
    while the dependency is unfilled, so the numbers are never quietly final."""
    import dataclasses

    at = _render("flap_loads", dataclasses.replace(_seeded(), engines=[]))
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "not entered yet" in shown and "will change" in shown, (
        "with no engine entered, the Flap page does not warn that its numbers "
        f"are provisional; warnings were {[w.value for w in at.warning]}")


def test_a_page_with_no_later_page_dependency_says_nothing():
    """The mark is targeted like the warnings channel is: the Aileron page reads
    nothing entered downstream, so it must stay quiet. A note on every page is a
    note nobody reads."""
    at = _render("aileron_loads")
    assert not at.exception, [e.message for e in at.exception]
    said = " ".join((c.value or "") for c in at.caption)
    assert "These numbers also read" not in said


def test_an_entry_error_is_not_shown_on_a_page_that_does_not_own_it():
    """The ``page`` tag is honoured, not ignored: the same project's warning
    must not appear on an unrelated page, or every page becomes a wall of text
    and the targeting the channel is built on means nothing."""
    at = _render("flap_loads", _contradictory_wing_row())
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "wing_fraction" not in shown, shown


def test_the_flap_page_says_when_the_slipstream_case_is_skipped():
    """#83 (C210-40) on the GUI the C210 was built in.

    The build entered the slipstream band (AF 15.2, BLPROP 0) with no engine
    record yet, and the page printed a critical flap load with the 23.457(b)
    amplification silently absent -- since #85, a delivered case that does not
    exist. The warning rides #82's channel, so the oracle GUI gets it with no
    per-page wiring at all.
    """
    project = _seeded()
    project.engines = []
    at = _render("flap_loads", project)
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "slipstream effect included" in shown, [w.value for w in at.warning]
    assert "Engine Mount Loads" in shown, shown


def test_the_one_engine_out_page_withholds_its_form_on_a_single(monkeypatch):
    """#84 (C210-43): the page for a condition the airplane cannot have takes no
    input at all -- it says why and stops, instead of collecting a simulation's
    worth of transient inputs for a run that prints zeros under a false
    "uncontrollable" verdict."""
    project = _seeded()
    assert len(project.engines) == 1, "the GA6 fixture is the single this is about"
    at = _render("one_engine_out", project)
    assert not at.exception, [e.message for e in at.exception]
    said = " ".join(i.value for i in at.info)
    assert "FAR 23.367 does not apply" in said, said
    # No form, and no results table underneath it.
    assert not at.number_input, [w.label for w in at.number_input]
    assert not at.subheader, [s.value for s in at.subheader]


def test_the_aero_page_fills_the_stall_cl_it_was_given_field_by_field():
    """#81 (C210-23), on the real path rather than a stand-in for it.

    This GUI creates the coefficient sets blank and writes the CLmax trio
    afterwards, one widget at a time, so ``__post_init__`` -- which had the only
    copy of the M1-1b fill -- never ran again. The live sets kept
    ``stall_cl = 0.0`` and Flight Envelope and SELECT died on "float division by
    zero" until the project was saved and reloaded. Rendering the page must now
    leave a runnable slice behind, which is what ``refresh_derived`` (already
    called after every persist) does.
    """
    from sloads.models import AeroCoefficientsInput, AeroCoeffSet
    from sloads.modules.flight_envelope import build_envelope

    project = _seeded()
    authored = project.aero_coeffs.cruise
    project.aero_coeffs = AeroCoefficientsInput(cruise=AeroCoeffSet(
        name="CRUISE", lift=authored.lift, drag=authored.drag, moment=authored.moment))
    project.aero_coeffs.clmax_clean = 1.4068
    project.aero_coeffs.clmax_clean_neg = -0.59
    project.aero_coeffs.clmax_flap = 1.5857
    assert project.aero_coeffs.cruise.stall_cl == 0.0, "the state this is about"

    at = _render("aero_coefficients", project)
    assert not at.exception, [e.message for e in at.exception]
    live = at.session_state["project"]
    assert live.aero_coeffs.cruise.stall_cl == 1.4068
    assert live.aero_coeffs.cruise.neg_stall_cl == -0.59
    # The reported symptom, gone: the envelope runs without a save-and-reload.
    assert build_envelope(live).vn


# --------------------------------------------------------------------------- #
# The row counter is not a delete key (code review 2026-08-24). ``rows`` is the
# project's own attached list, so the ``rows.pop()`` that used to size it down
# destroyed entered data during a render pass.
# --------------------------------------------------------------------------- #
def _count_key(at, path):
    return next(w.key for w in at.number_input
                if (w.key or "").endswith(f"{path}[].count"))


def test_counting_down_does_not_delete_entered_rows():
    """Typing 3 dropped 21 of 24 weight items, with no confirmation and no undo:
    counting back up returned blanks, and the truncated project saved. The mass
    item database is the D-25b mass SSOT, so this reaches every balanced case and
    every exported deck -- the user-triggered half of the #51 data-loss class."""
    project = _seeded()
    before = [i.name for i in project.weight.items]
    assert len(before) > 3, "the fixture must have rows to lose"

    at = _render("weight_mass", project)
    at.number_input(key=_count_key(at, "weight.items")).set_value(3).run()

    kept = at.session_state["project"].weight.items
    assert [i.name for i in kept] == before, "counting down must not delete rows"
    said = " ".join(w.value for w in at.warning)
    assert "does not delete entered rows" in said, said


def test_the_model_wins_when_a_retained_count_is_stale():
    """The same pop fired with **no user interaction**: a project mutated (not
    replaced) underneath a retained count was truncated to it on the next render.
    No generation bump covers that -- it is exactly what ``02_parked.md`` L-8d
    parks -- and #78's planned seed button is such a writer."""
    from dataclasses import replace as _replace

    project = _seeded()
    at = _render("weight_mass", project)
    live = at.session_state["project"]
    grown = len(live.weight.items) + 6
    live.weight.items.extend(
        _replace(live.weight.items[0], name=f"added {i}") for i in range(6))

    at.run()  # a plain revisit: nothing touched
    assert len(at.session_state["project"].weight.items) == grown


def test_deleting_surplus_rows_takes_a_deliberate_click():
    """Deletion is still possible -- it is a named button, not a side effect of
    a stray click on the counter's minus stepper."""
    project = _seeded()
    at = _render("weight_mass", project)
    before = len(project.weight.items)
    at.number_input(key=_count_key(at, "weight.items")).set_value(before - 2).run()

    button = next(b for b in at.button if "Delete the last" in b.label)
    assert "2" in button.label, button.label
    button.click().run()
    assert len(at.session_state["project"].weight.items) == before - 2


# --------------------------------------------------------------------------- #
# An override is not a one-way door, and a row is deleted where it sits (#72)
# --------------------------------------------------------------------------- #
def _clear_keys(at):
    return [b.key.split("::")[-1][: -len(".clear")] for b in at.button
            if (b.key or "").endswith(".clear")]


def test_a_filled_number_widget_cannot_be_emptied_from_the_frontend():
    """Why the clear is a button and not three lines on the return path.

    PB-20 proposed writing ``None`` when the widget comes back empty. It cannot
    work: an empty submission is deserialized as **the seed**, so a filled
    ``st.number_input`` never comes back empty and the return path never sees the
    clear. Asserted against Streamlit\'s own serde rather than through
    ``AppTest``, which writes widget state directly and so models the
    *programmatic* clear (what the button does), not the user\'s keystroke. If a
    future Streamlit returns ``None`` here, this fails and the button can go.
    """
    from streamlit.elements.widgets.number_input import NumberInputSerde
    from streamlit.proto.NumberInput_pb2 import NumberInput as NumberInputProto

    serde = NumberInputSerde(value=180.0, data_type=NumberInputProto.FLOAT,
                             min_value=-1e308, max_value=1e308)
    assert serde.deserialize(None) == 180.0, "an emptied widget now reports itself"
    assert NumberInputSerde(value=None, data_type=NumberInputProto.FLOAT,
                            min_value=-1e308, max_value=1e308).deserialize(None) is None


def test_a_filled_optional_override_can_be_cleared_back_to_computed():
    """PB-20: once ``chosen_vc``, ``gear_load_factor``, ``tau`` or ``envelope.mac``
    held a number this GUI could not un-set it, and it has no JSON editor -- so an
    override entered to try a number was permanent. Clearing is a named click, and
    the field goes back to unfilled, where the program's own value governs."""
    project = _seeded()
    project.speeds.chosen_vc = 180.0
    at = _render("structural_speeds", project)

    button = next(b for b in at.button if (b.key or "").endswith("speeds.chosen_vc.clear"))
    button.click().run()
    assert at.session_state["project"].speeds.chosen_vc is None
    assert next(w for w in at.number_input if "chosen_vc" in (w.key or "")).value is None

    # ... and it is an ordinary unfilled field again, not a dead one.
    next(w for w in at.number_input if "chosen_vc" in (w.key or "")).set_value(150.0).run()
    assert at.session_state["project"].speeds.chosen_vc == 150.0


def test_only_a_filled_optional_field_offers_a_clear():
    """The drift guard on the affordance: a clear button on a **required** field
    would offer a state the model does not have, and one on an empty field would
    be furniture. Every button is checked back against the registry entry of the
    field it clears."""
    from oracle_app.form import _unwrap_optional

    seen = 0
    for key in sorted(wf.oracle_step_keys()):
        at = _render(key)
        for widget_path in _clear_keys(at):
            path = re.sub(r"\.\d+\.", ".", widget_path)
            hint = fr.field_type(path)
            assert hint is not None, f"{key}: clear button on {path}, not a registry field"
            _inner, optional = _unwrap_optional(hint)
            assert optional, f"{key}: {path} is required -- it cannot be unfilled"
            seen += 1
    assert seen, "no filled Optional field in any fixture -- the guard proves nothing"


def test_a_converted_field_clears_in_si_too():
    """The widget key a converted field registers carries the active system, and a
    clear that computed that key a second time would empty a widget that does not
    exist. One owner names it (``components.number_input_name``); this is that
    agreement seen from the outside, on the mode where the two spellings differ."""
    project = _seeded()
    project.unit_system = UnitSystem.SI.value
    project.weight.envelope.mac = 58.0            # a length: converted, suffixed key
    at = _render("weight_mass", project)
    next(b for b in at.button
         if (b.key or "").endswith("weight.envelope.mac.clear")).click().run()
    assert at.session_state["project"].weight.envelope.mac is None


def test_a_field_the_owner_governs_offers_no_clear():
    """A display-only copy is disabled and shows the value that governs (#36), so
    there is nothing on it for the user to clear."""
    project = _seeded()
    project.speeds.wing_area_sqft = 174.0   # a copy the wing planform owns
    at = _render("structural_speeds", project)
    assert "speeds.wing_area_sqft" not in _clear_keys(at)


def test_a_row_is_deleted_where_it_sits_and_does_not_come_back():
    """PB-23: a row could only be removed from the **end** (the counter plus
    #88's surplus button), so dropping item 3 of 24 meant deleting twenty-one
    rows and retyping twenty. The counter has to follow the deletion -- left
    where it was, the next render grows the list straight back up to it, which is
    the #88 defect wearing the other sign."""
    project = _seeded()
    at = _render("weight_mass", project)
    before = [i.name for i in at.session_state["project"].weight.items]
    assert len(before) > 3, "the fixture must have rows to delete"

    picker = next(w for w in at.selectbox if (w.key or "").endswith("_delete_choice.weight.items[]"))
    picker.set_value(2).run()
    button = next(b for b in at.button if (b.key or "").endswith("weight.items[].2.delete"))
    assert before[2] in button.label, button.label
    button.click().run()

    after = [i.name for i in at.session_state["project"].weight.items]
    assert after == before[:2] + before[3:], "the wrong row went"
    at.run()  # a plain revisit: the counter must not re-grow what was deleted
    assert [i.name for i in at.session_state["project"].weight.items] == after


def test_a_composite_row_is_deleted_from_inside_its_own_expander():
    """The other table shape: rows holding a polyline get an expander each, so the
    delete control goes in the row rather than under the grid."""
    project = _seeded()
    at = _render("configuration_layout", project)
    before = [s.name for s in at.session_state["project"].geometry.surfaces]
    assert len(before) > 1, "the fixture must have surfaces to delete"

    button = next(b for b in at.button
                  if (b.key or "").endswith("geometry.surfaces[].1.delete"))
    assert before[1] in button.label, button.label
    button.click().run()
    assert [s.name for s in at.session_state["project"].geometry.surfaces] == before[:1]
    at.run()
    assert [s.name for s in at.session_state["project"].geometry.surfaces] == before[:1]


class _GridStub:
    """``st`` with its grid replaced: ``AppTest`` cannot drive a ``data_editor``
    (a canvas), so the write-back path is exercised by direct call, as
    ``tests/test_dirty_flag.py`` does for curves. Everything else falls through
    to the real module."""

    def __init__(self, edited):
        self._edited = edited
        self.captions = []

    def __getattr__(self, name):
        import streamlit as real_st
        return getattr(real_st, name)

    def data_editor(self, frame, **_kwargs):
        return self._edited

    def caption(self, text, *_args, **_kwargs):
        self.captions.append(text)


def _replayed_grid(rows, paths, prefix, cells):
    """``_render_flat_table`` over ``rows``, fed ``cells`` as the edited grid.

    ``cells`` is one dict per row, keyed by registry path, so the test states
    what the user typed and the harness -- not the test -- builds the headers the
    renderer expects."""
    import pandas as pd

    from oracle_app import form
    from sloads.units import field_unit, unit_label

    system = active_system()
    header = {
        p: f"{form._field_label(p)} ({unit_label(field_unit(form._leaf(p)), system)})"
           .replace(" ()", "")
        for p in paths
    }
    edited = pd.DataFrame([{header[p]: row[p] for p in paths} for row in cells],
                          columns=[header[p] for p in paths])
    stub = _GridStub(edited)
    original = form.st
    form.st = stub
    try:
        form._render_flat_table(rows, list(paths), prefix)
    finally:
        form.st = original
    return stub


def test_an_emptied_optional_grid_cell_unfills_the_field():
    """PB-20 inside a grid. This half already worked -- ``_cell_in`` writes
    ``None`` for an Optional column -- and it is pinned here so the scalar fix
    cannot drift away from it: ``aero.surfaces[].tau``, one of the four fields
    the finding names, is a grid cell and not a widget."""
    from sloads.models import WingLoadCase

    rows = [WingLoadCase(name="C1", case=1, nz=3.8)]
    paths = ["wing_mass.cases[].case", "wing_mass.cases[].nz"]
    _replayed_grid(rows, paths, "wing_mass.cases[]",
                   [{"wing_mass.cases[].case": float("nan"),
                     "wing_mass.cases[].nz": 3.8}])
    assert rows[0].case is None, "an emptied Optional cell must unfill the field"
    assert rows[0].nz == 3.8, "the untouched cell moved"


def test_an_emptied_required_grid_cell_says_the_old_value_was_kept():
    """The other half of the same keystroke (PB-23). A required column has no
    ``None`` to be set to, so the old number goes back in the cell -- correct,
    and until now silent, which read as a grid that had eaten the edit."""
    from sloads.models import MassItem

    rows = [MassItem(name="Wing", weight_lb=250.0, x=100.0, y=0.0, z=0.0)]
    paths = ["weight.items[].name", "weight.items[].weight_lb", "weight.items[].x"]
    stub = _replayed_grid(rows, paths, "weight.items[]",
                          [{"weight.items[].name": "Wing",
                            "weight.items[].weight_lb": float("nan"),
                            "weight.items[].x": 100.0}])
    assert rows[0].weight_lb == 250.0, "a required field has no None to be set to"
    said = " ".join(stub.captions)
    assert "cannot be empty" in said and "previous value was kept" in said, said
    assert "Weight" in said, "the caption must name the column that refused"


def test_a_blank_cg_case_does_not_read_as_not_ready():
    """A row the counter adds is in the project at once -- and a weight/CG case
    with no weight is one every balance divides by. It took out the whole Flight
    Envelope, reported as "cannot run yet", the sentence that means *keep
    typing*: a page that had been working a second earlier said only that it was
    unfinished. Refused by name now, and warned about before it is run."""
    from sloads.validation import consistency_warnings

    project = _seeded()
    at = _render("weight_mass", project)
    live = at.session_state["project"]
    key = _count_key(at, "weight.cg_cases")
    at.number_input(key=key).set_value(len(live.weight.cg_cases) + 1).run()

    live = at.session_state["project"]
    assert live.weight.cg_cases[-1].weight_lb == 0.0, "the state this is about"
    codes = [w.code for w in consistency_warnings(live)]
    assert "cg_case_without_weight" in codes, codes
    said = " ".join(w.message for w in consistency_warnings(live)
                    if w.code == "cg_case_without_weight")
    assert "divides by the case weight" in said, said


def test_a_not_ready_note_carries_the_type_and_a_traceback():
    """C210-24 (#99, the display half of #71): "cannot run yet — float division
    by zero" gave no type, no module:line, no traceback -- root-causing meant
    leaving the GUI. The friendly one-liner stays; the exception type joins it
    and the block carries the traceback, module:line first, for the expander."""
    from oracle_app import results as oracle_results
    from sloads import UnitSystem
    from sloads.models import Project

    block = oracle_results._module_block(Project(name="t"), "flight_envelope",
                                         UnitSystem.IMPERIAL)
    assert "MissingInputError" in block.note, block.note
    assert block.traceback, "the not-ready block must carry the traceback"
    first = block.traceback.splitlines()[0]
    assert ".py:" in first and " in " in first, first
    assert "Traceback" in block.traceback, "the full traceback follows the frame line"


def test_no_oracle_page_can_reach_the_concept_switch():
    """The drift guard behind the assertion above (``CLAUDE.md`` rule 3).

    Every shared-header call in the GUI has to disclaim the switch action --
    either by not rendering the banner at all or by rendering it without its
    button. A fifteenth page added the day this file is not touched inherits the
    shell default, and the behavioural test above only exercises one page.
    """
    offenders = []
    for path in _SOURCES:
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name not in ("page", "page_header", "render_applicability_banner"):
                continue
            passed = {kw.arg: kw.value for kw in node.keywords}
            off = [k for k in ("switch_action", "banner")
                   if isinstance(passed.get(k), ast.Constant) and passed[k].value is False]
            if not off:
                offenders.append(f"{os.path.relpath(path, _ROOT)}:{node.lineno}: {name}()")
    assert not offenders, (
        "an oracle-GUI page renders the shared header without disclaiming the "
        "switch-to-Concept action -- pass switch_action=False (CR-A-4):\n"
        + "\n".join(offenders))


def test_every_page_shows_every_field_the_registry_gives_it():
    """No field in the input set is dropped on the floor: the page groups
    partition the registry's rows for that page exactly."""
    from oracle_app.form import page_groups

    keep = fr.oracle_input_paths()
    shown = {p for key in wf.oracle_step_keys()
             for _prefix, paths in page_groups(key) for p in paths}
    expected = {row.path for row in fr.REGISTRY
                if row.path in keep and row.page in wf.oracle_step_keys()}
    assert shown == expected


def test_every_input_field_lands_on_an_oracle_page():
    """The other direction: a field in the input set whose editing page is not
    an oracle page would be unenterable, which is what amended OG-2."""
    keep = fr.oracle_input_paths()
    orphans = sorted(row.path for row in fr.REGISTRY
                     if row.path in keep and row.page not in wf.oracle_step_keys())
    assert not orphans, (
        "these fields are in the oracle GUI's input set but their editing page "
        f"is not an oracle page, so nothing can enter them: {orphans}")


def test_every_composite_field_declares_its_member_labels():
    """``MEMBER_LABELS`` is presentation, but it is hand-written, so it gets the
    same totality treatment as everything else here: a new composite field in
    the input set must be named, not silently rendered as "1, 2"."""
    from oracle_app.form import MEMBER_LABELS, _enum_of, _list_element, is_composite

    missing = sorted(
        path.rsplit(".", 1)[-1] for path in fr.oracle_input_paths()
        if is_composite(fr.field_type(path))
        # An enum set is a multiselect, not a row of members: its labels are the
        # enum's own names.
        and _enum_of(_list_element(fr.field_type(path))) is None
        and path.rsplit(".", 1)[-1] not in MEMBER_LABELS)
    assert not missing, (
        f"composite fields with no member labels in oracle_app.form: {missing}")


def test_the_aviation_units_agree_with_the_shell():
    """``units.AVIATION_STANDARD`` supplies ``unit_number_input``'s
    ``fixed_unit``, so its values must be the shell's own two labels -- not a
    third spelling of "knots". Since #73 the shell re-exports the units module's
    own constant rather than declaring a second one, which is what let the two
    spell the same unit differently in the first place."""
    from app_shell.components import ALTITUDE_FT, KEAS

    assert set(AVIATION_STANDARD.values()) == {KEAS, ALTITUDE_FT}


# --------------------------------------------------------------------------- #
# G7 -- output contract
# --------------------------------------------------------------------------- #
# The gate reads the *payloads*, not the source. ``test_ultimate_contract.py``
# scans ``app/views/*.py`` for a literal ``file_name="....csv"`` and matches the
# call that built it; pointed at a derived GUI it would find no literal and pass
# on an empty set -- a green gate over an unchecked front-end, which is the
# failure OG-9 exists to prevent. So the subject here is
# ``results.page_artifacts``: the bytes a user actually downloads. Completeness
# comes from the call-site test below -- one ``download_button`` in the package,
# fed from the same function this gate reads.
_STAMP = "# BASIS: All loads reported here are ULTIMATE"
_TEXT_HEADER = "Loads are ULTIMATE (= limit x SF); load factors are limit."


#: G7's fixtures. One airplane in one unit system was not a gate over the GUI's
#: output, it was a gate over one column of it (review PB-13): on ``ga6_normal``
#: the single-engine block means ``one_engine_out`` has no conditions at all and
#: ``body_loads`` produces none either, so two pages' artifacts were asserted
#: over an empty list -- and IMPERIAL alone never exercised the SI conversion
#: the download applies. The pair is a single and a twin, one system each; the
#: completeness test below is what stops it thinning back out.
_G7_FIXTURES = (("ga6_normal", UnitSystem.IMPERIAL), ("atr42_100", UnitSystem.SI))
_G7_IDS = [f"{example}-{system.name.lower()}" for example, system in _G7_FIXTURES]


def _fixture_project(example):
    return io.load_project(os.path.join(_EXAMPLES, f"{example}.project.json"))


def _artifacts(key, example="ga6_normal", system=UnitSystem.IMPERIAL, project=None):
    from oracle_app.results import page_artifacts

    return page_artifacts(
        project if project is not None else _fixture_project(example), key, system)


def test_the_output_gate_is_run_over_a_single_and_a_twin_in_both_systems():
    """Guard the fixtures: G7 says nothing about a page whose conditions the one
    fixture happens not to produce, and nothing about a conversion the one unit
    system never applies."""
    assert {system for _, system in _G7_FIXTURES} == set(UnitSystem), (
        "G7 runs in one unit system -- the SI download is unchecked")
    engines = {example: len(_fixture_project(example).engines)
               for example, _ in _G7_FIXTURES}
    assert min(engines.values()) == 1 and max(engines.values()) > 1, (
        f"G7 needs a single *and* a twin among its fixtures: {engines}")


def test_every_oracle_page_that_runs_a_program_offers_a_file():
    """The completeness half of G7: a page that runs a ``.BAS`` program must put
    a file on the page for at least one of the fixtures.

    Pages that run nothing (``aero_coefficients`` is input-only) are exempt by
    the workflow's own answer, not by name. A page that runs a program and
    produces nothing on *either* fixture is either broken or carries a condition
    no fixture reaches -- and both of those were what the payload assertions
    below quietly iterated past on an empty artifact list (review PB-13).
    """
    running = [key for key in sorted(wf.oracle_step_keys()) if wf.step_modules(key)]
    assert running, "no oracle page runs a program -- the gate is vacuous"
    coverage = {
        key: [ident for (example, system), ident in zip(_G7_FIXTURES, _G7_IDS)
              if _artifacts(key, example, system)]
        for key in running
    }
    missing = sorted(key for key, on in coverage.items() if not on)
    assert not missing, (
        "these pages run a program but offer no file on any G7 fixture "
        f"({_G7_IDS}): {missing}")


def test_the_gui_has_exactly_one_download_call_site():
    """What makes the payload gate *complete*: every file the oracle GUI offers
    is an ``Artifact`` from ``page_artifacts``, because there is nowhere else a
    download can be created. A second call site would be an artifact G7 never
    saw."""
    sites = []
    for path in _DOWNLOAD_SOURCES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "download_button":
                sites.append((os.path.relpath(path, _ROOT), node.lineno,
                              _file_name_of(node)))

    renderer = [s for s in sites if s[0] == os.path.join("oracle_app", "results.py")]
    assert len(renderer) == 1, (
        "the oracle GUI offers a load download from somewhere other than the one "
        "renderer -- gate G7 reads page_artifacts() and would not see it:\n"
        + "\n".join(f"{f}:{n}" for f, n, _ in renderer))

    # The shell's own downloads are allowed, and bounded: the project file is an
    # input, not a load deliverable, so it is outside G7 by content rather than
    # by which directory it lives in. Anything else the shell offers is a file a
    # user gets from this GUI that page_artifacts() never saw.
    # The results zip (C210-45) *is* a load deliverable, and its payload gate is
    # ``tests/test_results_zip.py``, which reads the artifact bytes the way this
    # file's G7 reads ``page_artifacts()``: the zip's members come from the same
    # two owners the per-page artifacts do (``module_text_report`` and
    # ``io.load_cases_csv`` + ``csv_comment_block``), so the ULT marker and the
    # basis statement are asserted on the bytes a user receives, not assumed.
    others = [s for s in sites if s not in renderer]
    offenders = [f"{f}:{n} -> {name}" for f, n, name in others
                 if name is None or not name.endswith((".project.json",
                                                       "_results.zip"))]
    assert not offenders, (
        "the shared shell offers a download the oracle GUI's output gate cannot "
        "see -- route it through results.page_artifacts() or state why it is not "
        "a load deliverable:\n" + "\n".join(offenders))


@pytest.mark.parametrize("example,system", _G7_FIXTURES, ids=_G7_IDS)
@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_csv_the_oracle_gui_offers_states_its_basis(key, example, system):
    """Gate G7, the CSV half: ULTIMATE by the stamp and an ``SF`` column, or
    LIMIT in-band *and* in a ``*_LIMIT.csv`` filename. A load CSV with a neutral
    name and no basis is the M4-15 defect class."""
    for art in _artifacts(key, example, system):
        if not art.file_name.endswith(".csv"):
            continue
        body = [ln for ln in art.payload.splitlines() if not ln.startswith("#")]
        header = body[0] if body else ""
        if art.file_name.endswith("_LIMIT.csv"):
            assert "LIMIT" in art.payload, (
                f"{art.file_name} is named LIMIT but never says so in-band")
            assert _STAMP not in art.payload, (
                f"{art.file_name} claims ULTIMATE and LIMIT at once")
        else:
            # In the **comment block**, not merely somewhere in the payload
            # (review CR-A-8): a stamp that only has to appear anywhere is
            # satisfied by a data row that happens to contain the words, and a
            # consumer reads the head of the file, not a grep of it.
            head = list(takewhile(lambda ln: ln.startswith("#"),
                                  art.payload.splitlines()))
            assert any(ln.startswith(_STAMP) for ln in head), (
                f"{art.file_name} leaves the oracle GUI with no basis statement "
                f"in its comment block -- pass report.csv_comment_block(project)")
            # The SF column is required exactly where a load was scaled (M4-8:
            # the factor is stated where it is applied). A pure property table
            # (geometry, mass properties -- no ``-ULT`` column anywhere)
            # carries no SF since #95/C210-8: the always-blank SF column on
            # those tables was C210-27's own complaint, not a basis statement.
            if "-ULT" in header:
                assert "SF" in header.split(","), (
                    f"{art.file_name} carries ULTIMATE loads but no per-case "
                    "SF column")
            else:
                assert "-ULT" not in art.payload.split("\n", len(head) + 1)[-1] or \
                    "SF" in header.split(","), (
                    f"{art.file_name} has -ULT data beyond the header row but "
                    "no SF column")


@pytest.mark.parametrize("example,system", _G7_FIXTURES, ids=_G7_IDS)
@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_text_report_says_what_the_cli_says(key, example, system):
    """Gate G7, the text half: the same ULT marker and per-case SF statement as
    ``cli.py``'s, which is guaranteed by being the same call -- so the assertion
    is byte equality with the CLI's own output, title line aside."""
    from sloads import convert_results, registry
    from sloads.report import module_text_report, text_report

    project = _fixture_project(example)
    for art in _artifacts(key, project=project, system=system):
        if not art.file_name.endswith(".txt"):
            continue
        assert _TEXT_HEADER in art.payload, f"{art.file_name} drops the ULT statement"
        assert "[ULTIMATE, SF=" in art.payload, f"{art.file_name} states no per-case SF"
        module = art.file_name[: -len(".txt")]
        result = registry.get(module)(project)
        converted = convert_results(result.conditions, system)
        # cli.py: module_text_report(result.module, convert_results(...)).
        expected = module_text_report(module, converted)
        assert art.payload.splitlines()[1:] == expected.splitlines()[1:], (
            f"{art.file_name} differs from the CLI's report for {module}")
        if module == "engine" and project.engine is not None:
            # cli.py:541 takes a different branch for this one module: it prints
            # ``text_report``, which heads the same body with the engine and
            # propeller identification. "Byte equality with the CLI's output"
            # was therefore not true here (review PB-13). The artifact keeps the
            # module report -- what is pinned is that the *body* is one text, so
            # the two cannot drift apart under one owner's edit.
            richer = text_report(
                project.engine, converted,
                unit_system="Imperial" if system == UnitSystem.IMPERIAL else "SI")
            basis = richer.splitlines().index(_TEXT_HEADER)
            assert richer.splitlines()[basis:] == expected.splitlines()[
                expected.splitlines().index(_TEXT_HEADER):], (
                "cli.py's engine report and the GUI's engine.txt no longer share "
                "a body -- one of the two owners changed alone")


@pytest.mark.parametrize("example,system", _G7_FIXTURES, ids=_G7_IDS)
def test_no_page_offers_two_files_with_the_same_name(example, system):
    """The download widget's key is the filename, so a collision is both a
    duplicate-key crash and two different files under one name."""
    for key in sorted(wf.oracle_step_keys()):
        names = [a.file_name for a in _artifacts(key, example, system)]
        assert len(names) == len(set(names)), (key, names)


def test_the_station_tables_are_keyed_by_module_not_by_page():
    """The one hand-declared table in the results renderer. Keyed by module
    because which row builder a program has is a fact about the program -- and
    keying it by page would put a step key back in the GUI (gate G2)."""
    from oracle_app.results import STATION_TABLES
    from sloads import registry

    assert set(STATION_TABLES) <= set(registry.available())
    assert not set(STATION_TABLES) & set(wf.BY_KEY)


def test_every_page_runs_the_programs_its_bas_string_claims():
    """OG-E's premise: a page headed "WTESTIMA+WTONECG+WTENV" shows all three.
    The modules come from ``workflow.step_modules``, so this is really a check
    that the renderer runs what the SSOT gives it and drops nothing."""
    from oracle_app.results import step_results
    from sloads import UnitSystem

    project = _seeded()
    for key in sorted(wf.oracle_step_keys()):
        blocks = step_results(project, key, UnitSystem.IMPERIAL)
        if len(blocks) == 1 and not blocks[0].module:
            continue  # gated: upstream slices missing, which the page says
        shown = {b.module for b in blocks}
        assert shown == set(wf.step_modules(key)), key


def test_a_page_with_no_program_of_its_own_shows_no_results():
    """Aerodynamic Data is on the page set because it *produces* a slice the
    ``.BAS`` steps require (OG-2 as amended), not because it runs one. An empty
    Results heading would be a worse answer than none."""
    from oracle_app.results import step_results
    from sloads import UnitSystem

    for key in sorted(wf.oracle_step_keys()):
        if wf.step_modules(key):
            continue
        assert step_results(_seeded(), key, UnitSystem.IMPERIAL) == []


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_the_results_block_survives_an_empty_project(key):
    """The blank-project path: every program is unrunnable and the page has to
    say so rather than raise."""
    from oracle_app.results import step_results
    from sloads import UnitSystem
    from sloads.models import Project

    for block in step_results(Project(name=""), key, UnitSystem.IMPERIAL):
        assert block.note or block.rows, (key, block.title)


def test_a_self_sufficient_page_is_not_sent_upstream():
    """#45 (CR-D-3), measured BB-4: on a fresh project ``weight_mass`` and
    ``engine_mount`` are missing only slices *their own form enters*, so the
    blocked note must point at the form above — "run the pages before this one
    first" was wrong guidance on the beta's first-run path. A genuinely
    dependent page keeps the upstream wording."""
    from oracle_app.results import step_results
    from sloads import UnitSystem
    from sloads.models import Project

    fresh = Project(name="")
    for key in ("weight_mass", "engine_mount"):
        (block,) = step_results(fresh, key, UnitSystem.IMPERIAL)
        assert "fill in the form above" in (block.note or ""), (key, block.note)
        assert "run the pages before" not in (block.note or ""), (key, block.note)
    (block,) = step_results(fresh, "structural_speeds", UnitSystem.IMPERIAL)
    assert "run the pages before this one first" in (block.note or "")
    assert "`aero_coeffs`" in block.note


# --------------------------------------------------------------------------- #
# G6 -- round-trip
# --------------------------------------------------------------------------- #
def _examples():
    return sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json")))


@pytest.mark.parametrize("path", _examples(), ids=lambda p: os.path.basename(p))
def test_a_project_the_oracle_gui_would_save_reloads_identically(path):
    """Gate G6: what the second front-end writes is the same ``project.json``
    the first one does -- no schema hop, no dropped slice on reload (OG-13)."""
    reduced = reduce_to_oracle_inputs(io.load_project(path))
    once = io.project_to_json(reduced)
    twice = io.project_to_json(io.project_from_dict(json.loads(once)))
    assert once == twice


def test_a_project_the_oracle_gui_would_save_opens_in_the_full_app():
    """Gate G6, the direction that matters to a user: hand the reduced project
    to ``app/`` and it builds, pages and all."""
    from streamlit.testing.v1 import AppTest

    reduced = reduce_to_oracle_inputs(io.load_project(_EXAMPLE))
    for view in ("Home.py", os.path.join("views", "configuration_layout.py"),
                 os.path.join("views", "weight_mass.py"),
                 os.path.join("views", "dashboard.py")):
        at = AppTest.from_file(os.path.join(_ROOT, "app", view), default_timeout=60)
        at.session_state["project"] = io.project_from_dict(
            json.loads(io.project_to_json(reduced)))
        at.run()
        assert not at.exception, (view, [e.message for e in at.exception])


def test_the_oracle_entry_point_builds():
    """The entry point itself: one ``set_page_config``, a derived navigation.

    Gate G2's *outcome*, read off the running app rather than off its source.
    The AST scan above is a drift hint -- it proves the expression that builds
    the navigation mentions ``oracle_steps``, which stayed true of a page set
    that had been filtered, re-ordered or built twice (review PB-10). This runs
    the entry point and asks the page set it actually registered, which is the
    same mapping ``st.navigation`` was handed (``app_shell.nav.register_pages``,
    OG-F), what it contains.
    """
    from streamlit.testing.v1 import AppTest

    from app_shell import nav

    at = AppTest.from_file(_ENTRYPOINT, default_timeout=60)
    at.session_state["project"] = _seeded()
    at.run()
    assert not at.exception, [e.message for e in at.exception]

    pages = at.session_state[nav.PAGES]
    assert list(pages) == [step.key for step in wf.oracle_steps()], (
        "the navigated page set is not workflow.oracle_steps() in order "
        f"(gate G2): {list(pages)}")
    assert {p.title for p in pages.values()} == {s.title for s in wf.oracle_steps()}, (
        "a page carries a title the workflow step does not")
    # The landing page is the first oracle step, and there is exactly one.
    defaults = [k for k, p in pages.items() if getattr(p, "_default", False)]
    assert defaults == [wf.oracle_steps()[0].key], defaults


def test_the_launcher_points_at_the_entry_point():
    """OG-11's console script resolves to the file it claims to run."""
    import oracle

    assert os.path.isfile(oracle.entry_point_path())
    assert os.path.samefile(oracle.entry_point_path(), _ENTRYPOINT)


def test_the_launcher_reports_a_missing_entry_point_instead_of_raising():
    import contextlib

    import oracle

    original = oracle.ENTRY_POINT
    oracle.ENTRY_POINT = os.path.join("oracle_app", "NotHere.py")
    try:
        stderr = _io.StringIO()
        with contextlib.redirect_stderr(stderr):
            assert oracle.main([]) == 2
        assert "not found" in stderr.getvalue()
    finally:
        oracle.ENTRY_POINT = original


# --------------------------------------------------------------------------- #
# One owner at render (#36, CR-A-2)
# --------------------------------------------------------------------------- #
def _copies():
    """Every non-owner copy of a shared quantity that the oracle GUI renders."""
    oracle = fr.oracle_input_paths()
    out = []
    for rows in fr.quantities().values():
        for row in rows:
            if (not row.is_owner and not row.owner_is_external
                    and row.owner_path and row.path in oracle):
                out.append(row)
    return sorted(out, key=lambda r: r.path)


#: A results page whose only block carries rows and **no** download (#89).
#:
#: The stub is installed **on the real module**: ``AppTest.from_string`` execs
#: this in the running process, so ``r.step_results = ...`` rebinds the module
#: attribute for everything that imports it afterwards, not just for this page.
#: The test below therefore restores it -- see the note there.
_NO_ARTIFACT_SCRIPT = """
import oracle_app.results as r
from sloads.units import UnitSystem
r.step_results = lambda project, key, system: [
    r.ResultBlock(module="flap", title="Flap loads",
                  rows=({"Quantity": "critical load", "Value": 629.0},))
]
r.render_results(None, "flap_loads", UnitSystem.IMPERIAL)
"""


def test_a_result_block_with_no_download_does_not_take_the_page_down():
    """``st.columns(0)`` raises (code review 2026-08-24 §4.3, #89).

    Latent, not live: every block that reaches the download row happens to carry
    at least one artifact today, so the crash waits on the first block that has
    a table and nothing to download -- a new program's results, or an export
    withheld because an input is missing. Pinned here rather than left to that
    coincidence, since nothing in the type says a block must have artifacts.
    """
    from streamlit.testing.v1 import AppTest

    import oracle_app.results as results_module

    # The script stubs ``step_results`` on the real module, in this process
    # (see :data:`_NO_ARTIFACT_SCRIPT`), so without this restore every later
    # test that imports it gets a one-block stub for a page called "flap"
    # instead of the renderer. It was harmless when written because nothing
    # after it read ``step_results``; it stopped being harmless the moment
    # something did, and the symptom was a ``KeyError`` in an unrelated test
    # that varied with the xdist worker split. Restored rather than rewritten
    # because the stub is the point of the test.
    original = results_module.step_results
    try:
        at = AppTest.from_string(_NO_ARTIFACT_SCRIPT, default_timeout=60)
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        assert any("Flap loads" in (h.value or "") for h in at.subheader)
    finally:
        results_module.step_results = original


def test_no_apptest_script_leaves_a_stub_on_a_real_module():
    """The isolation rule the test above had to learn (rule 3, structural).

    ``AppTest.from_string`` runs its script in **this** process, so an assignment
    to a module attribute inside one is a permanent monkeypatch with no undo:
    every later test importing that name gets the stub, and the failure surfaces
    somewhere else entirely. One script needs to do it; the guard is that a
    second cannot appear without a restore, since the next one will be found the
    same expensive way — by bisecting an unrelated ``KeyError``.

    Reads the script constants themselves, so a new one is covered the moment it
    is written.
    """
    import ast

    tree = ast.parse(open(__file__, encoding="utf-8").read(), filename=__file__)
    scripts = {
        target.id: node.value.value
        for node in tree.body if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.endswith("_SCRIPT")
        and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    }
    assert scripts, "no AppTest scripts found — the scan has stopped scanning"
    #: Scripts that install a stub on purpose, each restoring it in a ``finally``.
    _ALLOWED = {"_NO_ARTIFACT_SCRIPT"}
    offenders = []
    for name, body in scripts.items():
        if name in _ALLOWED:
            continue
        try:
            nodes = list(ast.walk(ast.parse(body)))
        except SyntaxError:
            # A ``str.format`` template (``_PAGE_SCRIPT``) is not parseable
            # until its placeholders are filled. Scanned textually instead, so
            # a template cannot become the hole in this guard.
            if re.search(r"^\s*\w+\.\w+\s*=\s*[^=]", body, re.M):
                offenders.append(name)
            continue
        if any(isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Attribute) for t in n.targets)
               for n in nodes):
            offenders.append(name)
    assert not offenders, (
        "these AppTest scripts assign to a module attribute, which outlives the "
        "test: restore it in a finally and add it to _ALLOWED — " + repr(sorted(set(offenders))))


def _external_copies():
    """Every copy the oracle GUI renders whose owner is **not** a field (#69).

    ``EXTERNAL`` rows: the engine weight and CG (owner: the weight database,
    D-25), the engine-mount limit load factor (the computed 23.337 limit), the
    weight estimate's engine count and horsepower (the engine list). Until #69
    ``_copy_note`` returned early on exactly these, so the half of the registry
    that says "owned, but not by a field" rendered as silent peer inputs.
    """
    oracle = fr.oracle_input_paths()
    return sorted((row for row in fr.REGISTRY
                   if row.owner_is_external and row.path in oracle),
                  key=lambda r: r.path)


def test_the_registry_still_has_external_copies_to_mark():
    """Guard the guard, as above: no external rows left means retire the branch,
    not keep a parametrized test with an empty parameter list."""
    assert _external_copies(), "no EXTERNAL copies left: retire the mark, do not keep a vacuous guard"


def test_every_external_copy_states_how_it_resolves():
    """An EXTERNAL row's caption is a deliberate answer, never a default.

    ``governs`` says the calc reads this field; ``resolves`` overrides the
    sentence where the rule is conditional -- the weight estimate's horsepower
    is ignored in favour of the engine sum *unless* the override switch beside
    it is set, and neither plain sentence is true of it. Defaulting silently to
    one of them is how the wrong one ships, which is the same reasoning
    ``test_every_copy_declares_whether_it_governs`` applies to field copies.
    """
    for row in _external_copies():
        assert row.governs or row.resolves, (
            f"{row.path}: EXTERNAL owner {row.external_owner!r} with no stated "
            "resolution -- set governs=True if the calc reads this field, or "
            "give `resolves` the sentence that is actually true")
        assert row.external_owner, (
            f"{row.path}: EXTERNAL declaration has no owner phrase before its "
            "parenthesised note")


@pytest.mark.parametrize("page", sorted({r.page for r in _external_copies()}))
def test_no_external_copy_renders_as_a_plain_widget(page):
    """The #36 mark reaching the rows it always skipped (#69, C210-41).

    Rendered end to end rather than asserted structurally, because the defect
    #89 names is precisely a *route* that never reaches the marker:
    ``_copy_note`` was called from ``render_scalar`` alone, so the engine CG --
    a three-member tuple, and a copy of the weight database -- would still have
    shipped unmarked with the registry saying otherwise. A page render is the
    only thing that proves the route.

    Counted per owner phrase, not merely searched for: two fields on the Engine
    Mount page name the *same* external owner (the weight database owns both the
    engine weight and the engine CG), so a plain substring test passes on the
    scalar's caption while the tuple beside it renders bare -- which is exactly
    the regression this is here to catch.
    """
    rows = [r for r in _external_copies() if r.page == page]
    at = _render(page)
    assert not at.exception, [e.message for e in at.exception]

    captions = [c.value or "" for c in at.caption]
    for owner in sorted({r.external_owner for r in rows}):
        want = sum(1 for r in rows if r.external_owner == owner)
        got = sum(1 for c in captions if owner in c)
        assert got >= want, (
            f"page {page!r} names external owner {owner!r} in {got} caption(s) "
            f"but {want} field(s) there are copies of it "
            f"({[r.path for r in rows if r.external_owner == owner]}); one of "
            "them renders as an independent input")


def test_the_wing_area_widget_shows_the_area_that_governs():
    """PB-17: the disabled copy displayed a number STRSPEED does not use.

    ``speeds.wing_area_sqft`` was registered as a copy of
    ``geometry.parametric.wing_area_sqft`` and the disabled widget showed that
    field, but ``structural_speeds`` integrates the ``speeds.wing_surface``
    planform: 500.0 on screen against the 497.75 in the answer, and on a
    hand-typed project two unrelated numbers. A disabled widget is a *statement
    about the calc*, so the wrong number there is worse than an empty box.
    """
    from sloads import field_registry as reg
    from sloads import io as sloads_io
    from sloads.modules.structural_speeds import _wing_area_sqft

    project = sloads_io.load_project(
        os.path.join(_EXAMPLES, "concept_regional_jet.project.json"))
    governing = _wing_area_sqft(project, project.speeds)
    assert governing != pytest.approx(project.geometry.parametric.wing_area_sqft), (
        "this example no longer distinguishes the planform from the parametric "
        "area, so it cannot show which one the widget displays")
    assert reg.external_value("speeds.wing_area_sqft", project) == pytest.approx(governing)

    at = _render("structural_speeds", project)
    assert not at.exception, [e.message for e in at.exception]
    shown = [w for w in at.number_input if (w.label or "").lower().startswith("wing area")]
    assert shown, [w.label for w in at.number_input]
    assert shown[0].disabled, "the copy is enterable while a planform governs it"
    assert shown[0].value == pytest.approx(governing, rel=1e-9), (
        f"the widget shows {shown[0].value}; STRSPEED uses {governing}")


def test_the_wing_area_widget_goes_live_when_no_planform_governs_it():
    """The other half, and why the row is ``resolves`` rather than display-only.

    With no such surface the field stops being inert and becomes the value
    STRSPEED reads -- which is what its own ``MissingInputError`` tells the user
    to set. Disabling it unconditionally (the state before #70) made that
    instruction impossible to follow.
    """
    from sloads import io as sloads_io

    project = sloads_io.load_project(
        os.path.join(_EXAMPLES, "concept_regional_jet.project.json"))
    from sloads.models import same_name
    project.geometry.surfaces = [s for s in project.geometry.surfaces
                                 if not same_name(s.name, project.speeds.wing_surface)]

    at = _render("structural_speeds", project)
    assert not at.exception, [e.message for e in at.exception]
    shown = [w for w in at.number_input if (w.label or "").lower().startswith("wing area")]
    assert shown and not shown[0].disabled, (
        "with no wing planform the field is the one STRSPEED reads, and the GUI "
        "still refuses to let it be entered")


def test_no_non_owner_field_needs_a_mark_the_renderer_cannot_give():
    """The composite mark is a caption, so a display-only composite is unmarkable.

    ``render_tuple``/``render_curve``/``render_enum_set`` are N sub-widgets with
    no single value to substitute, so they caption and never disable. A
    ``display_only`` composite would therefore need a mark the renderer cannot
    give, and would ship silently editable -- #89's mechanism, one door further
    in. The registry is not allowed to hold one.
    """
    from oracle_app.form import is_composite

    stray = [row.path for row in fr.REGISTRY
             if row.path in fr.oracle_input_paths() and row.display_only
             and is_composite(fr.field_type(row.path))]
    assert not stray, (
        "these are display-only copies of a composite type, which the form can "
        "caption but not disable -- make them overrides (governs=True) or give "
        f"the composite renderers a disabled path: {stray}")


def test_the_registry_still_has_copies_to_mark():
    """Guard the guard. The consolidation (note 33) removed most of the copies,
    and if the rest ever go the tests below would pass by having nothing to
    check — which is exactly how a rule quietly stops being enforced."""
    assert _copies(), "no non-owner copies left: retire the marking, do not keep a vacuous guard"


@pytest.mark.parametrize("path", [r.path for r in _copies()])
def test_no_copy_of_a_shared_quantity_renders_as_a_plain_widget(path):
    """A non-owner copy must say so on the page (#36, CR-A-2).

    Before this, the registry knew which field owned each shared quantity and the
    renderer did not read it, so wing reference area was independently editable on
    four pages and gear tread on two, with nothing warning that the numbers
    disagreed. Every copy now renders either **disabled** (display-only: the
    consumer resolves the owner, so anything entered here is inert) or **marked**
    (an override the calc honours), and each states the owner's path.
    """
    row = fr.entry(path)
    at = _render(row.page)
    assert not at.exception, [e.message for e in at.exception]

    captions = " ".join(c.value or "" for c in at.caption)
    assert row.owner_path in captions, (
        f"{path} renders on page {row.page!r} without naming its owner "
        f"{row.owner_path!r}; the page implies an independent input")

    hits = widgets_editing(at, path)
    widget = hits[0] if hits else None
    if widget is not None and not row.governs:
        assert widget.disabled, (
            f"{path} is display-only — the analysis resolves {row.owner_path!r} "
            "instead — but its widget is editable, so a value typed here is "
            "silently ignored")


def test_a_display_only_copy_shows_the_value_that_governs():
    """The dead wing-area input (#36; #29 review, note 32 §8).

    ``speeds.wing_area_sqft`` was editable on Structural Speeds while STRSPEED
    resolved the wing planform instead — an 18 % divergence measured on atr42,
    with the page showing the number the analysis did not use. It now renders
    disabled at the owner's value.
    """
    project = io.load_project(_EXAMPLE)
    project.speeds.wing_area_sqft = 1.0          # a value the analysis ignores
    at = _render("structural_speeds", project)
    assert not at.exception, [e.message for e in at.exception]

    widget = widget_editing(at, "speeds.wing_area_sqft")
    assert widget.disabled
    owner = project.geometry.parametric.wing_area_sqft
    assert widget.value == pytest.approx(to_display(owner, "area_sqft", active_system()), rel=1e-6)
    # ...and rendering it did not write the displayed value back over the stored
    # one: visiting a page must leave the project alone (OG-F).
    assert project.speeds.wing_area_sqft == 1.0


def test_an_override_that_disagrees_with_its_owner_warns():
    """An override may differ — that is what it is for — so this warns, it does
    not correct. ``speeds.weight_lb`` is read verbatim by STRSPEED while
    ``weight.max_takeoff_weight_lb`` is the MTOW owner (G-14); the two silently
    disagreeing is the wrong-belief half of CR-A-2."""
    project = io.load_project(_EXAMPLE)
    project.speeds.weight_lb = project.weight.max_takeoff_weight_lb + 500.0
    at = _render("structural_speeds", project)
    assert not at.exception, [e.message for e in at.exception]
    assert any("max_takeoff_weight_lb" in (w.value or "") for w in at.warning), (
        "a design weight disagreeing with the MTOW owner drew no warning")

    project.speeds.weight_lb = project.weight.max_takeoff_weight_lb
    agreed = _render("structural_speeds", project)
    assert not any("max_takeoff_weight_lb" in (w.value or "") for w in agreed.warning), (
        "agreement must be quiet, or the warning is noise nobody reads")


# --- #98 (C210-29): an empty list table says what it hides ------------------- #


def test_an_empty_list_table_says_what_it_hides():
    """At zero rows `render_table` used to return before either row branch, so
    the whole AIRLOADS block -- section slope, the TAU ratios, target CL, the
    twist/CDO(Y)/CM(Y) grids -- had no visible trace ("I can not find that
    anywhere", C210-29). The caption is **generated from the page's own field
    set**: hand-written it would be one caption per list, drifting the moment a
    field is added; generated, every empty list in the GUI gains it (rule 4)."""
    from oracle_app.form import _empty_table_note, page_groups

    groups = dict(page_groups("wing_loads"))
    note = _empty_table_note("Surfaces", groups["aero.surfaces[]"])
    assert note.startswith("0 rows")
    for trace in ("Section Slope", "Tau", "Target CL", "Twist", "Profile Drag",
                  "Section CM"):
        assert trace in note, (trace, note)
    # Generated for *every* list, not just the one the review caught.
    tabs = dict(page_groups("tab_loads"))["tab_loads.tabs[]"]
    assert "Surface" in _empty_table_note("Tabs", tabs)


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))


def test_grid_pages_carry_the_commit_hint():
    """C210 review 2026-08-23: a part-filled grid row is held out of the project,
    which is invisible until it vanishes on a rerun — so every page that renders
    a ``st.data_editor`` says so once, and a page with no grid does not nag.
    (The hint's original Enter warning was the C210-4 remount race, fixed by
    ``_stable_frame``.)"""
    hint = "fill every column to keep the row"
    at = _render("configuration_layout")   # surfaces/sections grids
    assert any(hint in c.value for c in at.caption), (
        "a grid page must carry the incomplete-row hint")
    at = _render("structural_speeds")      # scalars only
    assert not any(hint in c.value for c in at.caption), (
        "a page with no grid must not carry the hint")


# --------------------------------------------------------------------------- #
# A field is shown at its own precision, under its own name (#73, PB-22)
# --------------------------------------------------------------------------- #
def _number_widgets(at):
    """Every ``st.number_input`` on a rendered page, by label."""
    return {w.label: w for w in at.number_input}


def test_a_coefficient_is_shown_at_the_precision_it_was_entered():
    """The defect in one line: FLTLOADS' lift polynomial C1 is ``0.320479`` and
    the widget rendered ``0.3205``. The stored value was never touched — but
    this persona reads the coefficients off the screen to check them against the
    manual, so a coefficient the screen rounds is a coefficient nobody can
    check (PB-22). Asserted on the format *applied to the value*, not on the
    format string, because it is the rendered number that was wrong."""
    from sloads.units import DIMENSIONLESS_FORMAT

    project = io.load_project(_EXAMPLE)
    project.aero_coeffs.cruise.lift = (0.320479, 0.081234, 0.0, 0.0, 0.0)
    project.aero_coeffs.cruise.moment = (0.004128, 0.0, 0.0, 0.0, 0.0)
    at = _render("aero_coefficients", project)
    assert not at.exception, [e.message for e in at.exception]

    shown = [w.proto.format % w.value for w in at.number_input
             if w.value in (0.320479, 0.004128)]
    assert shown, "the coefficient widgets did not render"
    assert set(shown) == {"0.320479", "0.004128"}, shown
    assert DIMENSIONLESS_FORMAT % 0.004128 == "0.004128"


def test_a_dimensioned_field_keeps_its_fixed_decimals():
    """The other half of the per-unit rule, and the reason it is per-unit rather
    than ``%g`` everywhere: six *significant* figures on a station or an area
    loses precision a fixed four decimals keeps (184.12113907866492 renders
    ``184.121``, against ``184.1211``)."""
    from sloads.units import DIMENSIONAL_FORMAT, display_format, field_unit

    assert display_format(field_unit("wing_area_sqft")) == DIMENSIONAL_FORMAT
    assert display_format(field_unit("chosen_vc")) == DIMENSIONAL_FORMAT
    at = _render("structural_speeds")
    areas = [w for w in at.number_input if "Wing Area" in w.label]
    assert areas and all(w.proto.format == DIMENSIONAL_FORMAT for w in areas)


_FORMAT_LITERAL = re.compile(r'^%[0-9.]*[feg]$')


@pytest.mark.parametrize("path", _DOWNLOAD_SOURCES)
def test_no_renderer_writes_a_number_format_of_its_own(path):
    """Widget precision is a property of the **quantity**, so ``sloads.units``
    owns it (``display_format``) and no page may write a format literal: a
    renderer passing its own is a renderer being right about a field it does not
    know, which is how every float widget in this GUI came to show four decimals
    (PB-22, practice 3).

    ``app/views/`` is deliberately outside this scan — it is frozen pending the
    main-GUI review (#29), and its coefficient entry is a grid, which does not
    carry the defect."""
    for node in ast.walk(_parse(path)):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "format" and isinstance(kw.value, ast.Constant) \
                    and isinstance(kw.value.value, str) \
                    and _FORMAT_LITERAL.match(kw.value.value):
                raise AssertionError(
                    f"{os.path.basename(path)}:{node.lineno}: format="
                    f"{kw.value.value!r} — call sloads.units.display_format(unit)")


def test_a_hand_declared_label_names_a_field_that_exists():
    """``FIELD_LABELS`` is hand-written presentation, so it rots the moment a
    field is renamed — silently, because a label for a field nobody renders
    simply never appears. The guard is the same one ``MEMBER_LABELS`` carries."""
    from oracle_app.labels import FIELD_LABELS

    leaves = {p.rsplit(".", 1)[-1].replace(fr.LIST_MARKER, "") for p in fr.BY_PATH}
    unknown = sorted(set(FIELD_LABELS) - leaves)
    assert not unknown, f"labels for fields that are not in the input set: {unknown}"


def test_a_hand_declared_label_does_not_swallow_the_unit():
    """An override replaces the field's *name*, never its unit — otherwise a
    hand-written label is one place a deflection can lose its degrees."""
    from oracle_app.form import _field_label

    assert _field_label("geometry.empennage.htail.elevator_te_down_deg").endswith("(deg)")
    assert _field_label("geometry.empennage.htail.xt25") == "H-tail quarter-chord station"


def test_a_unit_suffix_is_matched_longest_first():
    """``design_pitch_rate_rad_s`` ends in both ``_s`` and ``_rad_s``, and the
    short match split the unit in half: *Design Pitch Rate Rad (s)*. Dict order
    is the author's; the matcher's order has to be stated (PB-22)."""
    from oracle_app.form import _field_label

    assert _field_label("engines[].design_pitch_rate_rad_s") == "Design Pitch Rate (rad/s)"
    assert _field_label("engines[].design_yaw_rate_rad_s") == "Design Yaw Rate (rad/s)"
    assert _field_label("engines[].stop_time_s") == "Stop Time (s)"


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_no_widget_label_nests_its_units_in_parentheses(key):
    """The renderer appends a unit as ``f"{label} ({unit})"``, so a unit that is
    itself parenthesised gives *Chosen Vc (kt (EAS))*. Fixed at the unit owner —
    the airspeed label is **KEAS**, the one word the rest of the tool already
    uses — rather than by teaching every renderer to inspect the string."""
    at = _render(key)
    nested = [w.label for w in at.number_input if re.search(r"\(.*\(", w.label)]
    assert not nested, nested


def test_the_coefficient_mach_field_says_what_it_is():
    """The one field on the V-n page whose name gives no clue was the one field
    whose help named a different quantity: ``mn``'s registry basis read
    "FLTLOADS gust/manoeuvre matrix" while it is the Mach the coefficients were
    measured at (PB-22). The help is built from the basis, so the fix is at the
    registry row."""
    assert "gust" not in fr.BY_PATH["flight_loads.mn"].basis.lower()
    at = _render("flight_envelope")
    mach = [w for w in at.number_input if w.label == "Coefficient Mach number"]
    assert mach, [w.label for w in at.number_input]
    assert "Mach" in (mach[0].help or "")


def test_the_root_group_caption_is_not_a_path():
    """Group captions are the schema path, in backticks. The root group has no
    path, and ``(project)`` rendered as code reads as one that exists (PB-22)."""
    at = _render("engine_mount")
    assert not any("(project)" in (c.value or "") for c in at.caption)


# --------------------------------------------------------------------------- #
# What a grid does with a keystroke (#77, C210-4 residual)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_a_page_with_a_grid_says_how_a_cell_commits(key):
    """Streamlit's grid keeps the cell editor open on Enter and the next
    keystroke discards the value — its behaviour, reproduced in a bare app, so
    the remedy is a sentence and the sentence has to be on every page that can
    lose an entry to it (#77).

    Two-sided on purpose. The note was said here until 2026-08-23 and then
    withdrawn as fixed, because Enter dropping an entry was *also* a symptom of
    C210-4, the remount race that was ours: closing that race retired the
    warning for a defect it did not cover. Asserting only "a grid page says it"
    would let the same withdrawal happen again on a page that quietly stopped
    rendering a grid; asserting the absence too means the note and the grids
    move together.
    """
    from app_shell.components import GRID_COMMIT_NOTE
    from oracle_app.form import _page_has_grid, page_groups, step_not_applicable

    project = _seeded()
    # A page for a condition this airplane cannot have collects nothing at all
    # (#84, C210-43) -- no form, so no grid and nothing to say about one.
    expected = (_page_has_grid(page_groups(key))
                and not step_not_applicable(key, project))
    at = _render(key, project)
    said = [c for c in at.caption if (c.value or "") == GRID_COMMIT_NOTE]
    assert bool(said) == expected, (key, expected, [c.value for c in at.caption])


def test_at_least_one_oracle_page_has_a_grid():
    """Anchors the test above: if the whole GUI stopped rendering grids, its
    two-sided assertion would pass vacuously on all fourteen pages."""
    from oracle_app.form import _page_has_grid, page_groups

    assert any(_page_has_grid(page_groups(k)) for k in wf.oracle_step_keys())


def test_the_grid_commit_note_is_spelled_once():
    """One string, one owner (rule 3). Fourteen of the sixteen
    ``st.data_editor`` call sites are in ``app/views/``, whose layout is frozen
    pending #29 — so the note lives in the shell rather than the GUI that says
    it today, and the main GUI adopts it by importing rather than by retyping a
    sentence that would then drift.
    """
    from app_shell.components import GRID_COMMIT_NOTE

    fragment = "Enter leaves the cell"
    owner = os.path.join(_SHELL, "components.py")
    assert fragment in GRID_COMMIT_NOTE
    sources = _DOWNLOAD_SOURCES + sorted(
        glob.glob(os.path.join(_ROOT, "app", "views", "*.py")))
    spelled = [p for p in sources
               if os.path.abspath(p) != os.path.abspath(owner)
               and fragment in open(p, encoding="utf-8").read()]
    assert not spelled, spelled


# --------------------------------------------------------------------------- #
# What the weight estimate is for (#78, C210-9)
# --------------------------------------------------------------------------- #
def test_the_weight_estimate_block_says_it_feeds_nothing():
    """WTESTIMA sits above WTONECG and WTENV on the page and feeds neither: the
    itemized data base is the sole source of every downstream mass property.
    Rendered above the estimate's own table, so it is read before the numbers
    rather than as a footnote to them (C210-9)."""
    from oracle_app.results import step_results
    from sloads.modules.weight_estimate import ADVISORY

    blocks = {b.module: b for b in step_results(_seeded(), "weight_mass",
                                                UnitSystem.IMPERIAL)}
    assert ADVISORY in blocks["weight_estimate"].advisory

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(
        "from oracle_app.results import render_results\n"
        "from sloads import UnitSystem\n"
        "import streamlit as st\n"
        "render_results(st.session_state['project'], 'weight_mass', UnitSystem.IMPERIAL)\n",
        default_timeout=60)
    at.session_state["project"] = _seeded()
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any(ADVISORY in (c.value or "") for c in at.caption)


def test_only_the_advisory_module_carries_one():
    """Keyed by module in ``MODULE_ADVISORIES``, so a caption cannot leak onto
    the two programs on this page whose output *is* consumed downstream —
    which would say the opposite of the truth about them."""
    from oracle_app.results import step_results

    blocks = {b.module: b for b in step_results(_seeded(), "weight_mass",
                                                UnitSystem.IMPERIAL)}
    assert not blocks["weight_onecg"].advisory
    assert not blocks["weight_envelope"].advisory


def test_the_estimate_comparison_is_shown_in_the_page_unit_system():
    """The delta crosses the same display boundary as every other figure on the
    page: an SI page states kilograms, not the calc's internal pounds."""
    from oracle_app.results import weight_estimate_advisory

    project = _seeded()
    assert "lb" in weight_estimate_advisory(project, UnitSystem.IMPERIAL)
    si = weight_estimate_advisory(project, UnitSystem.SI)
    assert "kg" in si and " lb" not in si
