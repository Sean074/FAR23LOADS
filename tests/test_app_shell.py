"""The app-layer shell has exactly one owner (design note 32, gate G8).

``app_shell/`` exists so a second front-end (the oracle GUI, note 32) cannot
grow its own copy of the project-file widget, the dirty guard, the units toggle
or the unit-input boundary. A prose rule would not survive that: the copy would
be added by whoever writes the second GUI, in a hurry, and nothing would fail.
So the rule is a test (``CLAUDE.md`` rule 3).

Three assertions, all live with one GUI and all sharper with two:

1. **No GUI package redefines a shell symbol.** This is G8 itself.
2. **The shell never imports a GUI package.** Without this the "single owner"
   is only nominal -- a shell that reaches back into ``app/`` is a component of
   that GUI wearing a shared name, and the second GUI would inherit the first
   one's pages.
3. **The GUI discovery actually finds something.** Assertions 1 and 2 are
   vacuous if :func:`_gui_dirs` returns nothing, which is exactly what a
   renamed directory would cause. The set is *derived* (a directory holding a
   Streamlit entry point) rather than hardcoded, so the day ``oracle_app/``
   lands it is covered without this file being touched -- the same
   derive-don't-list rule the nav guard follows.
"""

import ast
import json
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHELL_DIR = os.path.join(_ROOT, "app_shell")

#: Directories that hold Python but are never a GUI, skipped before parsing.
_NOT_GUI = {"app_shell", "sloads", "tests", "scripts", "docs", "examples",
            "reference", "changes", "build", "dist", "projects"}


def _parse(path):
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def _py_files(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "__"))]
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _is_entrypoint(tree):
    """A Streamlit entry point calls ``st.set_page_config`` at module level."""
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        fn = node.value.func
        if isinstance(fn, ast.Attribute) and fn.attr == "set_page_config":
            return True
    return False


#: The GUI packages, by name. A literal, because discovery alone cannot tell a
#: GUI that has gone missing from a GUI that was never there: the set used to be
#: "directories holding a ``set_page_config`` call", which made discovery depend
#: on the very property the gates below check. Wrapping ``Oracle.py``'s call in
#: a helper would have dropped ``oracle_app/`` out of G8, OG-10, the lint gate
#: and the back-import test at once, all four still green (review PB-11). Adding
#: a third front-end is a one-line edit here, and until it is made the discovery
#: test says so.
_EXPECTED_GUIS = {"app", "oracle_app"}


def _gui_dirs():
    """Repo-root directories that are a GUI package.

    Discovery is by directory -- a top-level package that is neither the shell,
    the calc package, nor tooling -- so nothing a GUI *does* can remove it from
    the gates that check what it does. ``test_the_gui_discovery_finds_every_gui``
    pins the result against :data:`_EXPECTED_GUIS`.
    """
    found = []
    for name in sorted(os.listdir(_ROOT)):
        path = os.path.join(_ROOT, name)
        # Leading "_" is the repo's own scratch convention (``_to_delete/``),
        # gitignored and never shipped.
        if name in _NOT_GUI or name.startswith((".", "_")) or not os.path.isdir(path):
            continue
        if any(True for _ in _py_files(path)):
            found.append(path)
    return found


def _top_level_names(tree):
    """Names bound at module level: functions, classes and simple assignments."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _shell_public_names():
    names = set()
    for path in _py_files(_SHELL_DIR):
        names |= {n for n in _top_level_names(_parse(path)) if not n.startswith("_")}
    return names


# --------------------------------------------------------------------------- #
# The lint gate covers every GUI, and says so identically everywhere
# --------------------------------------------------------------------------- #
#: Every file that *states* the merge gate's ruff command. CI is the authority;
#: the rest are copies, and a copy that drifts is a developer running a
#: different gate from the one that will fail their PR. Adding ``app_shell/``
#: meant editing nine of these by hand, and ``oracle_app/`` ten -- the second
#: time is when a convention gets a guard rather than another sweep
#: (``CLAUDE.md`` rule 3).
_LINT_AUTHORITY = os.path.join(".github", "workflows", "ci.yml")
_LINT_STATEMENTS = (
    _LINT_AUTHORITY,
    "CLAUDE.md",
    "README.md",
    os.path.join(".github", "PULL_REQUEST_TEMPLATE.md"),
    os.path.join(".pre-commit-config.yaml"),
    os.path.join("scripts", "solo_close.sh"),
    os.path.join("tests", "test_solo_scripts.py"),
    os.path.join("docs", "10_standard", "00_program_overview.md"),
    os.path.join("docs", "10_standard", "CODE_REVIEW_PROCESS.md"),
    os.path.join("docs", "10_standard", "PROJECT_GUIDE.md"),
    os.path.join("docs", "10_standard", "RELEASE_PROCESS.md"),
)

#: The target list ends at the end of the command: a backtick or quote closing
#: an inline code span, a line continuation, or a trailing ``#`` comment (the
#: README and PROJECT_GUIDE shell blocks annotate the line with ``# lint``).
_RUFF_COMMAND = re.compile(r"ruff check (?P<targets>[^`\n\\\"'#]+)")


def _lint_targets(relative_path):
    """The ruff target list as stated in one file, or ``None`` if it states none."""
    with open(os.path.join(_ROOT, relative_path), encoding="utf-8") as fh:
        for line in fh:
            match = _RUFF_COMMAND.search(line)
            if match and "sloads/" in match.group("targets"):
                return " ".join(match.group("targets").split())
    return None


def test_the_lint_gate_covers_every_gui():
    """A GUI outside the lint gate is unlinted code with a green CI badge."""
    targets = _lint_targets(_LINT_AUTHORITY)
    assert targets, f"no ruff command found in {_LINT_AUTHORITY}"
    for gui in _gui_dirs():
        name = os.path.basename(gui)
        assert f"{name}/" in targets, (
            f"{name}/ is a GUI directory but is not in CI's lint gate "
            f"({targets!r}) -- it would ship unlinted")


def test_every_statement_of_the_lint_gate_says_the_same_thing():
    """CI is the authority; every document and script that repeats the command
    must repeat it exactly, or somebody is running a different gate."""
    authority = _lint_targets(_LINT_AUTHORITY)
    disagreeing = {
        path: stated for path in _LINT_STATEMENTS
        if (stated := _lint_targets(path)) is not None and stated != authority
    }
    missing = [path for path in _LINT_STATEMENTS if _lint_targets(path) is None]
    assert not disagreeing, (
        f"these state a different lint gate from {_LINT_AUTHORITY} "
        f"({authority!r}): {disagreeing}")
    assert not missing, (
        f"these are listed as stating the lint gate but no longer do: {missing} "
        "-- remove them from _LINT_STATEMENTS or restore the command")


def test_the_gui_discovery_finds_every_gui():
    """Guard the guard: the discovered set is *exactly* the GUIs this repo has.

    Not "is non-empty", and not "contains ``app``" -- both were true of a
    discovery that had silently lost ``oracle_app/`` (review PB-11), and every
    gate in this file is only as wide as this set.
    """
    found = {os.path.basename(d) for d in _gui_dirs()}
    assert found == _EXPECTED_GUIS, (
        f"GUI discovery returned {sorted(found)}, expected {sorted(_EXPECTED_GUIS)} "
        "-- a front-end moved, was added, or is being excluded by _NOT_GUI; "
        "until this set is right, G8/OG-10 and the lint gate are not checking it"
    )
    for name in _EXPECTED_GUIS:
        assert any(_is_entrypoint(_parse(f))
                   for f in _py_files(os.path.join(_ROOT, name))), (
            f"{name}/ holds no module-level st.set_page_config -- it is listed "
            "as a GUI but has no entry point")


def _page_config_calls(tree):
    """Every ``st.set_page_config`` call in a module, at any nesting depth."""
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "set_page_config"]


def test_each_gui_configures_its_page_exactly_once():
    """OG-10, restated: **exactly one ``set_page_config`` per GUI entry point,
    and none anywhere else in that GUI.**

    The rule used to read "only ``Home.py`` calls it", which names a file rather
    than a role and says nothing about a second front-end. Streamlit raises if a
    page calls it twice, and a view that calls it under ``st.navigation`` breaks
    the app for the whole session -- so the failure is loud but only at runtime,
    and only on the page that carries it.
    """
    for gui in _gui_dirs():
        entry_points = []
        for path in _py_files(gui):
            calls = _page_config_calls(_parse(path))
            if not calls:
                continue
            relative = os.path.relpath(path, _ROOT)
            assert len(calls) == 1, (
                f"{relative} calls st.set_page_config {len(calls)} times")
            assert _is_entrypoint(_parse(path)), (
                f"{relative} calls st.set_page_config but not at module level -- "
                "a page under st.navigation must not configure the page")
            entry_points.append(relative)
        assert len(entry_points) == 1, (
            f"{os.path.basename(gui)}/ has {len(entry_points)} entry points "
            f"({entry_points}) -- exactly one per GUI (note 32, OG-10)")


def test_the_shell_does_not_configure_the_page():
    """The shell is imported by both entry points, so a ``set_page_config``
    there would be the first Streamlit call of whichever GUI imported it -- and
    would silently take the choice away from both."""
    for path in _py_files(_SHELL_DIR):
        assert not _page_config_calls(_parse(path)), (
            f"{os.path.relpath(path, _ROOT)} configures the page; that belongs "
            "to each GUI's entry point (note 32, OG-10)")


def test_the_shell_is_not_redefined_by_any_gui():
    """Gate G8: no symbol in the shared shell is defined twice across the GUIs."""
    shell = _shell_public_names()
    assert shell, "app_shell exports nothing -- the extraction is not in place"

    offenders = []
    for gui in _gui_dirs():
        for path in _py_files(gui):
            clash = _top_level_names(_parse(path)) & shell
            if clash:
                offenders.append(f"{os.path.relpath(path, _ROOT)}: {sorted(clash)}")
    assert not offenders, (
        "these GUI modules redefine a name the shell already owns -- import it "
        "from app_shell instead of keeping a private copy (note 32, OG-4/G8):\n"
        + "\n".join(offenders)
    )


def test_the_shell_does_not_import_a_gui():
    """The shell owns; it is not owned. No back-edge into a front-end package."""
    gui_names = {os.path.basename(d) for d in _gui_dirs()}
    offenders = []
    for path in _py_files(_SHELL_DIR):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                roots = [(node.module or "").split(".")[0]]
            else:
                continue
            for root in roots:
                if root in gui_names:
                    offenders.append(f"{os.path.relpath(path, _ROOT)}: imports {root!r}")
    assert not offenders, (
        "the shared shell imports a GUI package, so it is not a shared owner:\n"
        + "\n".join(offenders)
    )


# --- #34: the Upload path is edge-triggered ---------------------------------
#
# ``st.file_uploader`` returns the same file object on every rerun while it
# sits in the widget; before #34 the sidebar re-loaded and re-adopted it each
# run, ending in an unbounded ``st.rerun()`` loop (and, on a dirty project, a
# discard dialog Cancel could never dismiss). ``AppTest`` cannot drive the
# uploader widget, so the script stubs it with a fake upload of a fixed
# ``file_id`` and counts ``load_with_guard`` calls: the real edge invariant.

_UPLOAD_SCRIPT = """
import io, json, streamlit as st

class _FakeUpload(io.BytesIO):
    name = "uploaded.project.json"
    file_id = "{file_id}"
    @property
    def size(self):
        return len(self.getvalue())

from sloads import io as sloads_io, Project
_example = {example!r}
if _example:
    with open(_example, encoding="utf-8") as _fh:
        _doc = json.load(_fh)
else:
    _doc = json.loads(sloads_io.project_to_json(Project(name="from-upload")))
_doc.update({extra})
_payload = json.dumps(_doc).encode()

import app_shell.sidebar as sb
from app_shell.project_state import ensure_project, load_with_guard

_calls = st.session_state.setdefault("_guard_calls", [])

def _counting(new_project, source):
    _calls.append(source)
    load_with_guard(new_project, source)

project = ensure_project()
if {dirty}:
    project.name = "edited-since-save"
# AppTest runs in-process: the stubs are module globals every later test would
# inherit, so they are restored on every exit -- including the adopt path's
# ``st.rerun()``.
_real_uploader, _real_guard = st.file_uploader, sb.load_with_guard
st.file_uploader = lambda *a, **k: _FakeUpload(_payload)
sb.load_with_guard = _counting
try:
    with sb.render_shell_sidebar(project):
        pass
finally:
    st.file_uploader, sb.load_with_guard = _real_uploader, _real_guard
"""


def _upload_app(*, dirty: bool, file_id: str = "upload-1", extra: "dict | None" = None,
                example: str = ""):
    from streamlit.testing.v1 import AppTest

    return AppTest.from_string(
        _UPLOAD_SCRIPT.format(dirty=dirty, file_id=file_id, extra=repr(extra or {}),
                              example=example),
        default_timeout=60,
    )


def test_an_upload_is_processed_exactly_once_across_reruns():
    """Clean project: the upload adopts once; reruns with the file still in the
    widget do not re-adopt (the pre-#34 behavior re-adopted on every run —
    an unbounded rerun loop, resetting the dirty baseline each time)."""
    at = _upload_app(dirty=False)
    at.run()
    assert at.session_state["project"].name == "from-upload"
    assert at.session_state["_guard_calls"] == ["uploaded.project.json"]

    # A user edit after the upload must survive the next rerun un-clobbered
    # (``engineer``: the name has a sidebar widget of its own since #65, and a
    # widget writes back over a mutation made behind it -- by design, #51).
    at.session_state["project"].engineer = "edited-after-upload"
    at.run()
    assert at.session_state["project"].engineer == "edited-after-upload"
    assert at.session_state["_guard_calls"] == ["uploaded.project.json"]


def test_cancelling_the_discard_dialog_actually_cancels_an_upload():
    """Dirty project: the guard fires once; the rerun a dialog Cancel issues
    does not re-invoke it, so Cancel dismisses the dialog for good and the
    dirty project survives (pre-#34 the dialog reopened every run)."""
    at = _upload_app(dirty=True)
    at.run()
    assert at.session_state["_guard_calls"] == ["uploaded.project.json"]
    assert at.session_state["project"].name == "edited-since-save"

    at.run()  # what Cancel's st.rerun() executes
    assert at.session_state["_guard_calls"] == ["uploaded.project.json"]
    assert at.session_state["project"].name == "edited-since-save"


def test_a_migration_warning_reaches_the_page_as_a_toast():
    """DS-7.3 (#52): a hop that had to choose between two disagreeing copies
    says so with ``warnings.warn``, which a Streamlit page would swallow.
    ``safe_load`` captures it and toasts it — the same channel the schema
    check uses, since the adopt path ends in ``st.rerun()``. The adopted
    project carries the governing (MACHLIM) altitude."""
    at = _upload_app(dirty=False, extra={
        "schema_version": 54,
        "speeds": {"shoulder_altitude_ft": 10000,
                   "mach_limit": {"shoulder_altitude_ft": 12000,
                                  "max_operating_altitude_ft": 18000}},
    })
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].speeds.shoulder_altitude_ft == 12000
    toasts = [t.value for t in at.toast]
    assert any("shoulder altitude" in t and "10000" in t and "12000" in t for t in toasts), toasts


def test_opening_an_older_file_says_it_was_migrated():
    """PB-14 (#68): the version the file was *written* at is gone by the time the
    GUI sees the project -- ``project_from_dict`` runs ``migrate``, which stamps
    the dict at ``SCHEMA_VERSION``. The schema check asked the built project, so
    it always read "ok": a user opening a v41 file was never told it had been
    upgraded, and would rewrite it at the current version on save. The check now
    reads ``io.source_schema_version`` off the raw dict.

    On a real example, not a synthetic ``schema_version`` key, because the whole
    point is the round trip through the hop chain.
    """
    from sloads.models import SCHEMA_VERSION

    example = os.path.join(_ROOT, "examples", "dhc8_dash8.project.json")
    with open(example, encoding="utf-8") as fh:
        on_disk = json.load(fh)["schema_version"]
    assert on_disk < SCHEMA_VERSION, (
        f"the examples are at the current schema ({on_disk}) -- this test needs "
        "an older file to migrate; point it at a fixture under tests/fixtures_schema/")

    at = _upload_app(dirty=False, example=example)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    toasts = [t.value for t in at.toast]
    assert any(f"Migrated from schema {on_disk} to {SCHEMA_VERSION}" in t
               for t in toasts), toasts
    assert at.session_state["project"].schema_version == SCHEMA_VERSION


def test_opening_a_current_file_says_nothing():
    """The other half: the notice is about a migration, so a file already at the
    current version must not toast one. (This is what stayed true while the
    older-file half was dead, which is why nothing failed.)"""
    from sloads.models import SCHEMA_VERSION

    at = _upload_app(dirty=False, extra={"schema_version": SCHEMA_VERSION})
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert not [t.value for t in at.toast if "Migrated from schema" in t.value], (
        [t.value for t in at.toast])


def test_no_gui_decides_the_schema_status_from_the_built_project():
    """Rule 3, structural: the pre-migration version has one reader
    (``io.source_schema_version``) and ``schema_status`` is asked with it.

    Passing ``project.schema_version`` is not a wrong-looking call -- it reads
    perfectly, and was in both GUIs for months (review PB-14). So the guard is
    on the argument: a status call whose argument is an attribute access is the
    defect, wherever it is written.
    """
    offenders = []
    for gui in list(_gui_dirs()) + [_SHELL_DIR]:
        for path in _py_files(gui):
            for node in ast.walk(_parse(path)):
                if not isinstance(node, ast.Call):
                    continue
                if getattr(node.func, "attr", None) != "schema_status" or not node.args:
                    continue
                # The defect is reading the stamp off a *built* object: it is
                # current by then, whatever the file said. A value passed in
                # (``apply_schema_check``'s own ``source_version``) is fine --
                # the guard is on where the number comes from, not its spelling.
                stamp_read = [n for n in ast.walk(node.args[0])
                              if isinstance(n, ast.Attribute)
                              and n.attr == "schema_version"]
                if stamp_read:
                    offenders.append(
                        f"{os.path.relpath(path, _ROOT)}:{node.lineno}: "
                        "schema_status(<something>.schema_version)")
    assert not offenders, (
        "schema_status() is being asked about something other than the version "
        "the file was written at -- the built project's stamp is always current, "
        "so the migration notice can never fire (PB-14):\n" + "\n".join(offenders))


def test_a_fresh_upload_is_processed_again():
    """A new upload mints a new ``file_id``; the edge re-arms — the once-only
    latch is per upload, not forever."""
    at = _upload_app(dirty=False)
    at.run()
    assert at.session_state["_guard_calls"] == ["uploaded.project.json"]
    at.session_state["_uploader_processed"] = "some-older-upload"
    at.run()
    assert at.session_state["_guard_calls"] == ["uploaded.project.json"] * 2


# --------------------------------------------------------------------------- #
# The project-file block renders after the page (#64, review 2026-08-22 PB-4)
# --------------------------------------------------------------------------- #
_ORACLE_ENTRY = '''
import runpy, streamlit as st
_real = st.download_button
def _recording(label, data, **kw):
    st.session_state["_payload"] = data
    return _real(label, data, **kw)
st.download_button = _recording  # in-process stub: restored below
try:
    runpy.run_path("{entry}", run_name="__main__")
finally:
    st.download_button = _real
'''


def _oracle_entry_point():
    from streamlit.testing.v1 import AppTest

    from sloads import io as sloads_io
    from sloads.field_registry import reduce_to_oracle_inputs

    at = AppTest.from_string(
        _ORACLE_ENTRY.format(entry=os.path.join(_ROOT, "oracle_app", "Oracle.py")),
        default_timeout=60)
    at.session_state["project"] = reduce_to_oracle_inputs(
        sloads_io.load_project(os.path.join(_ROOT, "examples", "ga6_normal.project.json")))
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _dirty_caption(at):
    return next(c.value for c in at.sidebar.caption if "nsaved changes" in c.value)


def test_the_download_and_the_dirty_flag_describe_this_reruns_edit():
    """PB-4's reproduction on the real oracle entry point: one edit, then the
    payload, the caption and the row-expander title read in the *same* run.
    Before #64 all three were one rerun behind (the sidebar serialised before
    the page persisted) while the oracle GUI -- no Apply -- had no second
    rerun to catch up on."""
    import json

    at = _oracle_entry_point()
    assert _dirty_caption(at) == "⚪ No unsaved changes"
    ar = next(w for w in at.number_input if w.key.endswith("geometry.parametric.aspect_ratio"))
    ar.set_value(ar.value + 1).run()
    assert not at.exception, [e.message for e in at.exception]

    project = at.session_state["project"]
    assert json.loads(at.session_state["_payload"])["geometry"]["parametric"]["aspect_ratio"] \
        == project.geometry.parametric.aspect_ratio
    assert _dirty_caption(at) == "🟠 Unsaved changes"

    name = next(w for w in at.text_input if w.key.endswith("geometry.surfaces[].0.name"))
    name.set_value("mainplane").run()
    assert [e.label for e in at.expander if e.label.startswith("1 · ")] == ["1 · mainplane"]


_STOPPING_PAGE = '''
import streamlit as st
from app_shell.components import stop_page
from app_shell.project_state import ensure_project
from app_shell.sidebar import render_shell_sidebar
project = ensure_project()
project.name = "edited"
if {wrapped}:
    with render_shell_sidebar(project):
        st.error("no speeds yet")
        stop_page()
        st.session_state["_after_stop"] = True
else:
    stop_page()
    st.session_state["_after_stop"] = True
'''


def test_the_project_file_block_survives_a_page_that_stops():
    """The ``app/`` views leave early when a prerequisite is missing; the block
    reserved above the page is still filled, and with *this* run's state --
    ``st.stop()`` discards everything emitted after it, so rendering behind
    the page in the plain sense lost Save/Download on exactly those pages."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_STOPPING_PAGE.format(wrapped=True), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert "_after_stop" not in at.session_state
    assert [e.value for e in at.error] == ["no speeds yet"]
    assert _dirty_caption(at) == "🟠 Unsaved changes"
    assert [b.label for b in at.sidebar.button if "Save" in b.label] == ["💾 Save to disk"]
    assert [h.value for h in at.sidebar.header] == ["Units", "Project file"]


def test_stop_page_is_st_stop_outside_the_shell():
    """A view driven standalone (no sidebar around it) still just stops."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_STOPPING_PAGE.format(wrapped=False), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert "_after_stop" not in at.session_state


def test_no_view_calls_st_stop_directly():
    """Drift guard for the sweep: the page exit is the shell's ``stop_page``."""
    views = os.path.join(_ROOT, "app", "views")
    offenders = [f for f in sorted(os.listdir(views)) if f.endswith(".py")
                 and re.search(r"^\s*st\.stop\(\)", open(os.path.join(views, f), encoding="utf-8").read(), re.M)]
    assert offenders == [], f"st.stop() discards the shell's project-file block; call stop_page(): {offenders}"


# --------------------------------------------------------------------------- #
# The project is named in the sidebar; Save never overwrites unasked (#65, PB-6)
# --------------------------------------------------------------------------- #
_NAMED_SCRIPT = """
import os, streamlit as st
from sloads import io as sloads_io
sloads_io.default_projects_dir = lambda: {projects_dir!r}
_real_download = st.download_button
def _recording(label, data, **kw):
    st.session_state["_download_name"] = kw["file_name"]
    return _real_download(label, data, **kw)
st.download_button = _recording
try:
    from app_shell.project_state import ensure_project, saved_path
    from app_shell.sidebar import render_shell_sidebar
    project = ensure_project()
    with render_shell_sidebar(project):
        pass
    st.session_state["_saved_path"] = saved_path()
finally:
    st.download_button = _real_download
"""


def _named_app(projects_dir):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_NAMED_SCRIPT.format(projects_dir=str(projects_dir)),
                             default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _name_widget(at):
    return next(w for w in at.sidebar.text_input if w.label == "Project name")


def _save(at):
    next(b for b in at.sidebar.button if "Save" in b.label).click().run()
    assert not at.exception, [e.message for e in at.exception]


def test_project_filename_is_one_sanitiser():
    """``[^A-Za-z0-9._-]`` → ``_``, collapsed, trimmed, capped, never empty."""
    from sloads.io import PROJECT_STEM_MAX, project_filename

    assert project_filename("") == "project.project.json"
    assert project_filename("  ./  ") == "project.project.json"
    assert project_filename("GA-6 Normal") == "GA-6_Normal.project.json"
    assert project_filename("Cessna 210 Centurion — Continental IO-520-A") == \
        "Cessna_210_Centurion_Continental_IO-520-A.project.json"
    long = project_filename('ATR 42-300 ("ATR 42-100" prototype designation never entered '
                            'production; -300 is the closest PW120-powered production analog)')
    assert long.endswith(".project.json") and len(long) <= PROJECT_STEM_MAX + len(".project.json")
    assert long.startswith("ATR_42-300_ATR_42-100_prototype")
    assert "/" not in project_filename("a/b\\c:d") and project_filename("a/b\\c:d") == "a_b_c_d.project.json"


def test_the_sidebar_names_the_project_and_its_file(tmp_path):
    """The name widget is the shell's (both GUIs); Download and Save use the
    sanitised name; the ``app/`` dashboard no longer carries a second widget."""
    at = _named_app(tmp_path)
    assert at.session_state["_download_name"] == "project.project.json"
    _name_widget(at).set_value("GA-6 Normal / study").run()
    assert at.session_state["project"].name == "GA-6 Normal / study"
    assert at.session_state["_download_name"] == "GA-6_Normal_study.project.json"
    assert _dirty_caption(at) == "🟠 Unsaved changes"

    dashboard = open(os.path.join(_ROOT, "app", "views", "dashboard.py"), encoding="utf-8").read()
    assert '"Project name"' not in dashboard, "two widgets for project.name flip-flop"


def test_save_writes_a_fresh_name_and_then_its_own_file_unasked(tmp_path):
    at = _named_app(tmp_path)
    _name_widget(at).set_value("Study A").run()
    _save(at)
    path = tmp_path / "Study_A.project.json"
    assert path.is_file()
    assert at.session_state["_saved_path"] == str(path)
    assert _dirty_caption(at) == "⚪ No unsaved changes"

    at.session_state["project"].engineer = "me"
    at.run()
    _save(at)  # its own file: written again, no question asked
    assert '"engineer": "me"' in path.read_text(encoding="utf-8")
    assert _dirty_caption(at) == "⚪ No unsaved changes"


def test_save_over_another_project_asks_first(tmp_path):
    """PB-6's loss: a second project named like the first replaced it on disk.
    Now the existing file is untouched until the overwrite is confirmed."""
    other = tmp_path / "Study_A.project.json"
    other.write_text('{"keep": "me"}', encoding="utf-8")
    at = _named_app(tmp_path)
    _name_widget(at).set_value("Study A").run()
    _save(at)
    assert other.read_text(encoding="utf-8") == '{"keep": "me"}'
    assert at.session_state["_saved_path"] is None
    assert _dirty_caption(at) == "🟠 Unsaved changes"


def test_open_records_the_file_so_save_goes_back_to_it(tmp_path):
    from sloads import Project
    from sloads import io as sloads_io

    src = tmp_path / "Mine.project.json"
    sloads_io.save_project(Project(name="Mine"), str(src))
    at = _named_app(tmp_path)
    next(b for b in at.sidebar.button if b.label == "Open").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].name == "Mine"
    assert at.session_state["_saved_path"] == str(src)
    at.session_state["project"].engineer = "me"
    at.run()
    _save(at)
    assert '"engineer": "me"' in src.read_text(encoding="utf-8")

if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
