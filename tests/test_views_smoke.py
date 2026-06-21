"""Smoke test: every Streamlit view (and the entrypoint) runs without raising.

Uses Streamlit's headless ``AppTest`` to execute each page with the GA-6 example
project seeded into session state, then asserts the script produced no uncaught
exception. This is a cheap regression guard for the GUI layer (which the pure-calc
tests don't cover): it would have caught, for example, a page still calling the
removed single-engine ``Project(engine=...)`` API after the multi-engine refactor.
"""

import glob
import logging
import os

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLE = os.path.join(_ROOT, "examples", "ga6_normal.project.json")
_VIEWS = sorted(glob.glob(os.path.join(_ROOT, "app", "views", "*.py")))
_ENTRYPOINT = os.path.join(_ROOT, "app", "Home.py")

pytest.importorskip("streamlit.testing.v1")


def _seeded_project():
    from farloads import io
    return io.load_project(_EXAMPLE)


def _run(path):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(path, default_timeout=60)
    at.session_state["project"] = _seeded_project()
    at.run()
    return at


def test_entrypoint_builds_navigation():
    at = _run(_ENTRYPOINT)
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize("path", _VIEWS, ids=[os.path.basename(p) for p in _VIEWS])
def test_view_runs_without_exception(path):
    at = _run(path)
    assert not at.exception, [e.message for e in at.exception]
