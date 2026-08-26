"""Cross-page navigation links resolve to real workflow steps (M2-2, review G6).

Every ``st.page_link`` in the app goes through ``components.workflow_page_link``
(directly or via ``components.gate``), which derives a link's target path and
label from :mod:`sloads.workflow`. These static checks guard the two ways that
contract can rot:

* a link naming a step ``key`` that isn't in :data:`sloads.workflow.BY_KEY`
  (the stale-page-name bug the helper exists to prevent -- "Wing Geometry",
  "Configuration & Layout" -- would resurface as a broken link, not dead text);
* the helper's core assumption that a step ``key`` is also its view-file stem
  (``app/views/<key>.py``).

The AppTest smoke suite (``test_views_smoke``) covers that the links *render*;
this covers that they *point somewhere real*, without a Streamlit runtime.

**This file is ``app/``-scoped, deliberately** (design note 32, OG-F). OG-9 had
scheduled it to be parametrized over both GUI directories, on the sound reasoning
that a second GUI is invisible to an ``app/views/``-hardcoded guard. It does not
transfer: the oracle GUI has no view files at all (its pages are callables, gate
G2), so the first test below is false there by construction, and it makes no
``workflow_page_link`` calls, so the second would pass on an empty set and report
it as covered. What replaced the parametrization is structural rather than
another scan -- ``workflow_page_link`` no longer builds a path at all. It resolves
a step key to the running GUI's own page object through ``app_shell.nav``, so a
link cannot name a page that does not exist, in either front-end. The
``views/<key>.py`` assumption this file pins is now ``app/``'s alone, which is
exactly what it should be.
"""

import ast
import glob
import os
import re

from sloads import workflow as wf  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEWS_DIR = os.path.join(_ROOT, "app", "views")
_VIEWS = sorted(glob.glob(os.path.join(_VIEWS_DIR, "*.py")))


def test_every_workflow_key_has_a_view_file():
    """``workflow_page_link(key)`` maps ``key`` -> ``views/<key>.py``; every step
    key must have that file so no link can 404 (the helper's path assumption)."""
    for key in wf.BY_KEY:
        assert os.path.isfile(os.path.join(_VIEWS_DIR, f"{key}.py")), (
            f"workflow step {key!r} has no app/views/{key}.py"
        )


def test_every_view_file_is_a_workflow_step():
    """The other direction (CR-D-4/D-8, 2026-08-20 review): a stray
    ``app/views/foo.py`` never enters nav, still passes ``test_views_smoke``
    (which globs ``views/*.py``), and until this assertion existed no guard
    failed -- a page could exist, be smoke-tested, and be unreachable forever.
    Every other nav/spec guard in the suite cuts both ways; this one did not."""
    stems = {os.path.splitext(os.path.basename(p))[0] for p in _VIEWS}
    stems -= {"__init__"}
    orphans = sorted(stems - set(wf.BY_KEY))
    assert not orphans, (
        f"app/views/ file(s) with no workflow step -- unreachable pages: {orphans}. "
        "Add the step to sloads/workflow.py or delete the view."
    )


def _link_keys(tree: ast.AST):
    """Yield the literal step-key arguments of every ``workflow_page_link`` /
    ``gate`` call in ``tree``.

    ``workflow_page_link(key, ...)`` -- the first positional arg is the key.
    ``gate(message, *keys, kind=...)`` -- every positional arg after the message
    is a key. Non-literal args (e.g. the dashboard's ``s.key`` loop variable) are
    skipped; they are covered by :func:`test_every_workflow_key_has_a_view_file`.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
        if name == "workflow_page_link":
            positional = node.args[:1]
        elif name == "gate":
            positional = node.args[1:]
        else:
            continue
        for arg in positional:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                yield arg.value


def test_all_link_keys_are_valid_steps():
    """Every literal key handed to a link helper is a real workflow step."""
    seen = 0
    for path in _VIEWS:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for key in _link_keys(tree):
            seen += 1
            assert key in wf.BY_KEY, (
                f"{os.path.basename(path)} links to unknown workflow key {key!r}"
            )
    assert seen > 0, "no page-link keys found -- did the scan break?"


# --- the user guide's phase table is a view of the same graph (CR-D-7) -------

_GUIDE = os.path.join(_ROOT, "docs", "10_standard", "GUI_USER_GUIDE.md")
_PHASE_ROW = re.compile(r"^\|\s*\*\*(?P<phase>[^*]+)\*\*\s*\|(?P<pages>[^|]*)\|")


def _guide_phase_table():
    """(phase, [page titles]) rows of the guide's §2 phase table, in file order."""
    rows = []
    with open(_GUIDE, encoding="utf-8") as fh:
        for line in fh:
            m = _PHASE_ROW.match(line)
            if m and m.group("phase").strip() in wf.PHASES:
                pages = [t.strip() for t in m.group("pages").split("·") if t.strip()]
                rows.append((m.group("phase").strip(), pages))
    return rows


def test_the_gui_guide_phase_table_matches_the_workflow():
    """``GUI_USER_GUIDE.md`` §2 promises a navigation; ``workflow.py`` is the one
    that ships. They disagreed until 2026-08-25 (CR-D-7): the guide filed
    Aircraft Comparison under **Load-case plotting** where the graph puts it in
    **Export**, and its Flight-loads row omitted Tail Span Loads and Balanced
    Cases -- the two pages carrying the mission's primary distributed
    deliverable. Prose cannot hold a graph current, so this derives it."""
    expected = [(ph, [s.title for s in wf.STEPS if s.phase == ph]) for ph in wf.PHASES]
    assert _guide_phase_table() == expected, (
        "docs/10_standard/GUI_USER_GUIDE.md §2 phase table has drifted from "
        "sloads/workflow.py -- the navigation SSOT. Rebuild the table from the graph "
        "(phases in wf.PHASES order, pages as the step titles joined by ' · ')."
    )


if __name__ == "__main__":  # zero-dependency fallback runner
    test_every_workflow_key_has_a_view_file()
    test_every_view_file_is_a_workflow_step()
    test_all_link_keys_are_valid_steps()
    test_the_gui_guide_phase_table_matches_the_workflow()
    print("ok")
