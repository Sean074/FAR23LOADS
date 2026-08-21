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


def _gui_dirs():
    """Repo-root directories holding a Streamlit entry point -- i.e. a GUI.

    Derived, not listed: adding the oracle GUI adds it here automatically, which
    is the moment gate G8 stops being a formality.
    """
    found = []
    for name in sorted(os.listdir(_ROOT)):
        path = os.path.join(_ROOT, name)
        if name in _NOT_GUI or name.startswith((".", "__")) or not os.path.isdir(path):
            continue
        if any(_is_entrypoint(_parse(f)) for f in _py_files(path)):
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


def test_the_gui_discovery_finds_a_gui():
    """Guard the guard: a renamed GUI directory must fail here, not silently
    empty out the two assertions below."""
    guis = _gui_dirs()
    assert guis, (
        "no Streamlit entry point found outside app_shell/ -- either a GUI "
        "directory moved or _NOT_GUI now excludes it; G8 is not being checked"
    )
    assert os.path.join(_ROOT, "app") in guis


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


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
