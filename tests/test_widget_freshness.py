"""A loaded project must reach the widgets, and stale widgets must not overwrite it.

The defect (2026-08-21, backlog Pri 1 / issue #51 — the data-loss half of parked
**L-8d**). Streamlit widget state, once registered under a key, wins over the
``value=`` argument on every later rerun, and both GUIs key their widgets by
something stable across projects: the registry path in ``oracle_app/form.py``, a
hand-written name in ``app/views/``. ``adopt()`` replaced
``st.session_state["project"]`` and touched no widget key — so a page **visited
before** a load kept rendering its own retained state, and, because these
widgets persist what they return, wrote that state back over the project that
had just been loaded. Open the oracle GUI on the seed ``Project(name="")``,
visit Weight & Mass Properties, load ``atr42_100``: the page showed ``0`` / ``""``
/ 0 rows, the row-count widget held ``0``, and all 21 ``weight.items`` and all 8
``weight.cg_cases`` were popped out of the loaded project. Save from there and the file
on disk goes too.

The fix is one stamp on the key (:mod:`app_shell.widget_keys`), bumped by the
one function that means "the project was replaced". This module holds it to the
two halves of the contract, per page shape, and adds the guard that keeps new
widgets inside it:

* **render → adopt → re-render** leaves the session project equal to the loaded
  file (every oracle page, on every shipped example), and the widgets show the
  loaded values rather than the ones they held;
* the same for ``app/views/``, whose Apply step defers the overwrite rather
  than preventing it — the rationale parked L-8d rested on, which is why the
  sweep (practice 4) had to check it rather than assume it;
* **no input widget skips the stamp** — an AST walk over both GUIs, so the next
  widget added is fresh by construction instead of by review. Since #51's
  reopen (2026-08-22) that includes widgets with **no key at all**: an unkeyed
  widget's identity derives from its arguments, so its retained state survives
  a load whenever the loaded field repeats the seed — the common case, because
  the seed is ``Project(name="")``. The only exemptions are the shell's own
  session-state widgets, named per key with a companion that fails when an
  entry stops naming anything;
* **the sidebar survives a load intact** — the exemption list is the one part of
  the stamp a human decides, and #70 (PB-16) is what a wrong decision looks
  like: the unit radio was exempted as "the user's choice" when ``unit_system``
  is a field of the project, so a load could not change it and dirtied the file
  it had just read. The behavioural half below holds every shipped example to
  "loading a file leaves it clean", which no future exemption can argue past.
"""

import ast
import glob
import json
import logging
import os
import sys
import tempfile

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytest.importorskip("streamlit.testing.v1")

from sloads import io  # noqa: E402
from sloads import workflow as wf  # noqa: E402

_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))
_ATR42 = os.path.join(_ROOT, "examples", "atr42_100.project.json")


def _ids(paths):
    return [os.path.basename(p) for p in paths]


#: The load, driven the way the GUI drives it. ``adopt()`` runs at the top of a
#: rerun (the sidebar's load path ends in ``st.rerun()``), so the page that
#: re-renders below it is the page the user was already looking at.
_SCRIPT = """
import streamlit as st

from app_shell.project_state import adopt, ensure_project
from oracle_app.form import render_step
from sloads import io

ensure_project()
if st.session_state.pop("_load_now", False):
    adopt(io.load_project({path!r}))
render_step({key!r})
"""


def _visited_then_loaded(key, example, timeout=60):
    """An oracle page rendered on the seed project, then loaded into."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_SCRIPT.format(path=example, key=key), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    at.session_state["_load_now"] = True
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
@pytest.mark.parametrize("example", _EXAMPLES, ids=_ids(_EXAMPLES))
def test_a_loaded_project_survives_the_page_that_was_already_open(key, example):
    """Every page, every example: the load's own rerun must not lose a field.

    One renderer builds all fourteen pages, so one stale widget is fourteen
    pages' worth of data loss; and the loss is per-field, so the assertion is
    the whole serialized project, not a sampled value.
    """
    at = _visited_then_loaded(key, example)

    expected = io.project_to_dict(io.load_project(example))
    after = io.project_to_dict(at.session_state["project"])
    assert after == expected, (
        f"the oracle GUI's {key} page, open before the load, wrote its own stale "
        f"widget state over {os.path.basename(example)}")


def test_the_widgets_show_the_loaded_project_not_what_they_held():
    """The display half — the same defect seen from the page.

    Without it, "never write anything back" would pass the test above while the
    user still stared at zeros. Weight & Mass Properties is the page the defect
    was found on: a scalar, a text field and a table whose row count gates 21
    rows out of existence.
    """
    at = _visited_then_loaded("weight_mass", _ATR42)
    project = io.load_project(_ATR42)

    from helpers import widget_editing

    mtow = widget_editing(at, "weight.max_takeoff_weight_lb")
    assert mtow.value == pytest.approx(project.weight.max_takeoff_weight_lb, rel=1e-6)

    counts = [w.value for w in at.number_input if (w.label or "").endswith("rows")]
    assert len(project.weight.items) in counts, (
        f"the row-count widgets read {counts}; the loaded project has "
        f"{len(project.weight.items)} weight items")

    session = at.session_state["project"]
    assert len(session.weight.items) == len(project.weight.items)
    assert len(session.weight.cg_cases) == len(project.weight.cg_cases)


# --------------------------------------------------------------------------- #
# The shell sidebar: a load must reach it, and must not dirty what it loaded
# --------------------------------------------------------------------------- #
_SHELL_SCRIPT = """
import streamlit as st

from app_shell.project_state import adopt, ensure_project
from app_shell.sidebar import render_shell_sidebar
from sloads import io

ensure_project()
if st.session_state.pop("_load_now", False):
    adopt(io.load_project(st.session_state["_load_path"]))
with render_shell_sidebar(st.session_state["project"]):
    st.write("page body")
"""


def _shell_then_loaded(example, timeout=90, before=None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_SHELL_SCRIPT, default_timeout=timeout)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    if before is not None:
        before(at)
        assert not at.exception, [e.message for e in at.exception]
    at.session_state["_load_path"] = example
    at.session_state["_load_now"] = True
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _switch_to_si(at):
    """Give the sidebar a state of its own to hold, so 'it stayed clean' means
    something: with every widget agreeing with the file, a stale one is
    invisible."""
    from sloads import UnitSystem

    at.radio[0].set_value("SI").run()
    assert at.session_state["project"].unit_system == UnitSystem.SI.value


@pytest.mark.parametrize("example", _EXAMPLES, ids=_ids(_EXAMPLES))
def test_loading_a_file_through_the_shell_leaves_it_clean(example):
    """The general form of PB-16: a load is a read, and a read edits nothing.

    Anything in the sidebar still holding the previous project's state writes it
    onto the loaded one during the load's own rerun, so the file the user just
    opened is dirty before they touch it -- and 'Unsaved changes' beside a file
    nobody changed is the caption that teaches users to ignore the caption. This
    is the behavioural guard behind ``_SHELL_OWNED_KEYS``: a future exemption
    that turns out to be project data fails here whatever its rationale said.
    """
    at = _shell_then_loaded(example, before=_switch_to_si)
    from app_shell.project_state import SAVED_SNAPSHOT_KEY

    project = at.session_state["project"]
    assert io.project_to_dict(project) == at.session_state[SAVED_SNAPSHOT_KEY], (
        f"the shell dirtied {os.path.basename(example)} while loading it")
    assert io.project_to_dict(project) == io.project_to_dict(io.load_project(example))


def test_the_unit_radio_adopts_the_loaded_projects_system():
    """PB-16 itself, in the direction that reproduced it.

    ``unit_system`` is a field of ``Project`` (M4-20 D-22), so an SI-saved file
    opened in an Imperial session must arrive as SI. Unstamped, the radio's
    retained state beat ``index=`` and wrote Imperial back over it.
    """
    from sloads import UnitSystem

    # Written outside ``examples/``: that directory is globbed by this file and
    # several others, in a parallel run.
    saved_si = io.load_project(_ATR42)
    saved_si.unit_system = UnitSystem.SI.value
    with tempfile.TemporaryDirectory() as tmp:
        si_file = os.path.join(tmp, "si.project.json")
        with open(si_file, "w", encoding="utf-8") as handle:
            json.dump(io.project_to_dict(saved_si), handle)
        at = _shell_then_loaded(si_file, before=_switch_to_si)
        assert at.session_state["project"].unit_system == UnitSystem.SI.value

    # ...and back the other way: the session is SI, the file says Imperial.
    at = _shell_then_loaded(_ATR42, before=_switch_to_si)
    assert at.session_state["project"].unit_system == UnitSystem.IMPERIAL.value, (
        "the sidebar's unit radio kept its own selection across a load and put "
        "it back on the loaded project")
    assert at.radio[0].value == "Imperial"


# --------------------------------------------------------------------------- #
# app/views: the Apply step defers the overwrite, it does not prevent it
# --------------------------------------------------------------------------- #
_VIEWS_DIR = os.path.join(_ROOT, "app", "views")

#: The three view shapes the sweep has to cover: a form of scalars, a data
#: editor of rows, and a view whose widgets are built per named record.
_VIEWS = ["structural_speeds.py", "weight_mass.py", "engine_mount.py"]

_VIEW_SCRIPT = """
import streamlit as st

from app_shell.project_state import adopt, ensure_project
from sloads import io

ensure_project()
if st.session_state.pop("_load_now", False):
    adopt(io.load_project({path!r}))
exec(compile(open({view!r}).read(), {view!r}, "exec"))
"""


@pytest.mark.parametrize("view", _VIEWS)
def test_a_view_open_before_a_load_re_seeds_from_what_was_loaded(view):
    """``app/views/`` keys are hand-written and equally stable across projects.

    Its Apply step means the stale values land on the user's click rather than
    on the load's rerun — later, not never, and with the user believing they
    just confirmed what they were shown. The widgets must therefore re-seed from
    the loaded project here too.
    """
    from streamlit.testing.v1 import AppTest

    path = os.path.join(_VIEWS_DIR, view)
    at = AppTest.from_string(
        _VIEW_SCRIPT.format(path=_ATR42, view=path), default_timeout=90)
    from app_shell.widget_keys import unstamped

    at.run()
    assert not at.exception, [e.message for e in at.exception]
    seeded = {w.key for w in at.number_input if w.key}

    at.session_state["_load_now"] = True
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    loaded = {w.key: w.value for w in at.number_input if w.key}

    assert seeded and loaded, f"{view} rendered no keyed inputs to check"
    # The same fields (the page did not change shape) as different widgets (so
    # none of them can still be holding the discarded project).
    assert {unstamped(k) for k in seeded} & {unstamped(k) for k in loaded}, (
        f"{view} rendered a different field set before and after the load; the "
        "comparison below would be vacuous")
    assert not (seeded & set(loaded)), (
        f"{view} re-used widget keys across a project replacement: "
        f"{sorted(seeded & set(loaded))[:5]} — those widgets keep the state of "
        "the project that was discarded, and its Apply writes them back")
    assert any(v for v in loaded.values()), (
        f"{view} showed nothing after the load")


def test_a_value_typed_before_the_load_does_not_survive_it():
    """The reproduction from #51's reopen comment: type first, then load.

    Before every input widget carried a stamped key, an unkeyed widget derived
    its Streamlit identity from its arguments -- ``value=`` included -- so a
    number typed into it was retained across the load whenever the loaded field
    repeated the seed (the common case: the seed is ``Project(name="")``),
    entered the project on the user's Apply, and reached disk. The stamp
    retires the edited widget by renaming it, so after the load the field must
    be a *new* widget showing the loaded value, not the typed one.
    """
    from streamlit.testing.v1 import AppTest

    from app_shell.widget_keys import unstamped

    path = os.path.join(_VIEWS_DIR, "structural_speeds.py")
    at = AppTest.from_string(
        _VIEW_SCRIPT.format(path=_ATR42, view=path), default_timeout=90)
    at.run()
    assert not at.exception, [e.message for e in at.exception]

    sentinel = 123.25  # matches nothing in atr42_100 (vh_kt is 265)
    vh = next(w for w in at.number_input if unstamped(w.key or "") == "ss_vh")
    vh.set_value(sentinel).run()
    assert not at.exception, [e.message for e in at.exception]
    key_before = vh.key

    at.session_state["_load_now"] = True
    at.run()
    assert not at.exception, [e.message for e in at.exception]

    vh_after = next(w for w in at.number_input if unstamped(w.key or "") == "ss_vh")
    assert vh_after.key != key_before, (
        "the load did not retire the edited widget: it kept its key, so it "
        "still holds the value typed against the discarded project")
    expected = io.load_project(_ATR42).speeds.vh_kt
    assert vh_after.value == pytest.approx(expected), (
        f"VH shows {vh_after.value} after the load; the typed {sentinel} should "
        f"have been replaced by the loaded {expected}")
    after = io.project_to_dict(at.session_state["project"])
    assert after == io.project_to_dict(io.load_project(_ATR42)), (
        "the load's own rerun changed the loaded project")


# --------------------------------------------------------------------------- #
# The guard: no widget seeded from the project skips the stamp
# --------------------------------------------------------------------------- #
#: Streamlit calls that carry user input back to the caller. ``st.button`` and
#: the download buttons are excluded: they hold no value to go stale.
_INPUT_CALLS = {
    "number_input", "text_input", "text_area", "checkbox", "toggle", "radio",
    "selectbox", "multiselect", "slider", "select_slider", "data_editor",
    "date_input", "time_input", "color_picker",
    # Missed by the first cut (#51's reopen): equally stateful, equally stale.
    "pills", "segmented_control", "file_uploader", "camera_input",
    "audio_input", "chat_input",
}

#: Widgets whose keys are the shell's own session state, not project data: the
#: load-path pickers and the file uploader. These must **survive** a load —
#: stamping them would reset the picker the user is loading *through*. Named
#: **per key**, not per file (#43's lesson: a whole-file exemption keeps
#: exempting whatever the file grows), and the two companion tests below fail
#: when an entry stops naming a real widget, or starts naming project data.
#:
#: ``_unit_system_radio`` was on this list until #70 (review 2026-08-22 PB-16) on
#: the stated grounds that stamping it "would reset the user's unit choice on
#: every project they open". That is what it is *for*: ``unit_system`` is a field
#: of ``Project`` (M4-20 D-22), so the exemption made the radio's retained state
#: beat a loaded file's own setting and dirty it on the way in. An exemption
#: argued from the widget's subject matter rather than from where its value lives
#: is the failure mode this allowlist has to keep out.
_SHELL_OWNED_KEYS = {
    "_open_saved_choice", "_open_example_choice", "_uploader",
}


def _stamped(node):
    """Is this widget's key stamped with the project generation?

    A widget with no ``key=`` fails too (issue #51's reopen): an unkeyed
    widget's Streamlit identity derives from its *arguments* -- ``value=``
    included -- so its retained state survives a project load whenever the
    loaded field repeats the seed. The seed is ``Project(name="")``, which most
    loaded fields repeat, so "no key" is the defect, not an exemption.
    """
    for keyword in node.keywords:
        if keyword.arg != "key":
            continue
        if isinstance(keyword.value, ast.Constant) \
                and keyword.value.value in _SHELL_OWNED_KEYS:
            return True  # shell session state by name; must survive a load
        for sub in ast.walk(keyword.value):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                    and sub.func.id == "widget_key":
                return True
        return False
    return False  # no key= at all: argument-derived identity, equally stale


def _widget_calls(path):
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in _INPUT_CALLS:
            yield node


def _gui_sources():
    for package in ("app", "app_shell", "oracle_app"):
        for path in sorted(glob.glob(os.path.join(_ROOT, package, "**", "*.py"),
                                     recursive=True)):
            yield os.path.relpath(path, _ROOT), path


@pytest.mark.parametrize("relative,path", list(_gui_sources()),
                         ids=[r for r, _p in _gui_sources()])
def test_every_project_widget_key_is_stamped(relative, path):
    """The structural half (``CLAUDE.md`` rule 3): a convention with a guard.

    ``unit_number_input`` stamps for its callers, so a view on the unit boundary
    passes with no change; anything calling Streamlit directly has to pass a
    stamped ``key=``, and this fails on the first one that does not -- including
    a widget with no key at all (#51: argument-derived identity retains state
    across a load just the same).
    """
    unstamped = [f"{relative}:{node.lineno} st.{node.func.attr}"
                 for node in _widget_calls(path) if not _stamped(node)]
    assert not unstamped, (
        "these widgets are seeded from the project but keyed the same across a "
        "project replacement, so a load leaves them holding the discarded "
        "project's values (app_shell/widget_keys.py):\n  " + "\n  ".join(unstamped))


def test_every_shell_owned_key_still_names_a_widget():
    """The companion (#43's lesson): an exemption that names nothing exempts
    everything it might one day match. Each allowlisted key must appear as the
    literal ``key=`` of some input widget in the GUI sources."""
    found = set()
    for _relative, path in _gui_sources():
        for node in _widget_calls(path):
            for keyword in node.keywords:
                if keyword.arg == "key" and isinstance(keyword.value, ast.Constant):
                    found.add(keyword.value.value)
    missing = _SHELL_OWNED_KEYS - found
    assert not missing, (
        f"_SHELL_OWNED_KEYS entries no longer name any widget: {sorted(missing)} "
        "— remove them (or re-point them) so the allowlist stays exact")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
