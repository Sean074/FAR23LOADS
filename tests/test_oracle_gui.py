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

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

from sloads import field_registry as fr  # noqa: E402
from sloads import io  # noqa: E402
from sloads import workflow as wf  # noqa: E402
from sloads.field_registry import reduce_to_oracle_inputs  # noqa: E402
from sloads.units import AVIATION_STANDARD  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GUI = os.path.join(_ROOT, "oracle_app")
_ENTRYPOINT = os.path.join(_GUI, "Oracle.py")
_EXAMPLES = os.path.join(_ROOT, "examples")
_EXAMPLE = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_SOURCES = sorted(glob.glob(os.path.join(_GUI, "*.py")))

pytest.importorskip("streamlit.testing.v1")


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
}

#: Imperial->SI factors. A literal from this set inside a front-end means it has
#: started converting on its own -- the defect class ``units.py`` is the single
#: owner of (CONVENTIONS.md §7). Mirrors ``test_constants.py``'s scan.
_SI_FACTORS = re.compile(
    r"\b(25\.4|0\.3048|0\.45359|4\.4482|1\.35581|6\.89475|9\.80665|386\.0)")


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
    """Gate G1, second half: every conversion goes through ``sloads.units``."""
    offenders = []
    for path in _SOURCES:
        with open(path, encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if _SI_FACTORS.search(line):
                    offenders.append(f"{os.path.relpath(path, _ROOT)}:{number}: {line.strip()}")
    assert not offenders, (
        "a unit factor literal in a GUI package -- convert through "
        "sloads.units (owner) or app_shell's unit_number_input:\n"
        + "\n".join(offenders))


def test_the_oracle_gui_writes_no_deliverable_of_its_own():
    """Gate G1, third half: no private CSV writer. OG-E routes output through
    ``sloads.io``/``sloads.report``; until then there is none at all."""
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


def test_the_entry_point_navigates_the_derived_step_set():
    """Gate G2: the navigation argument is built from ``oracle_steps()``."""
    source = open(_ENTRYPOINT, encoding="utf-8").read()
    calls = [n for n in ast.walk(ast.parse(source))
             if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "navigation"]
    assert len(calls) == 1, "expected exactly one st.navigation call"
    names = {n.attr for n in ast.walk(calls[0]) if isinstance(n, ast.Attribute)}
    assert "oracle_steps" in names, (
        "st.navigation does not derive its pages from workflow.oracle_steps()")


def test_the_derived_page_set_is_the_fourteen_oracle_steps():
    """The set itself, so a change to ``oracle_steps`` is visible here too."""
    keys = [s.key for s in wf.oracle_steps()]
    assert keys == [s.key for s in wf.STEPS if s.key in wf.oracle_step_keys()]
    assert set(keys) == wf.oracle_step_keys()
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
    from oracle_app.form import MEMBER_LABELS, is_composite

    from oracle_app.form import _enum_of, _list_element

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
    third spelling of "knots"."""
    from app_shell.components import ALTITUDE_FT, KEAS

    assert set(AVIATION_STANDARD.values()) == {KEAS, ALTITUDE_FT}


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
    """The entry point itself: one ``set_page_config``, a derived navigation."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(_ENTRYPOINT, default_timeout=60)
    at.session_state["project"] = _seeded()
    at.run()
    assert not at.exception, [e.message for e in at.exception]


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


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
