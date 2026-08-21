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


if __name__ == "__main__":  # zero-dependency fallback runner
    test_every_workflow_key_has_a_view_file()
    test_all_link_keys_are_valid_steps()
    print("ok")
