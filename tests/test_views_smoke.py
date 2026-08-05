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
# Beyond-GA project: 4000 hp / ~50 seats -- regression fixture for the
# StreamlitValueAboveMaxError that fired when the weight-estimate power widget was
# capped at 3000 hp while seeding a loaded value above that cap. The Estimate tab
# now lives on the merged Weight & Mass Properties page (Step G3).
_BEYOND_GA = os.path.join(_ROOT, "examples", "dhc8_dash8.project.json")
_WEIGHT_ESTIMATE = os.path.join(_ROOT, "app", "views", "weight_mass.py")
_EXPORT = os.path.join(_ROOT, "app", "views", "export_report.py")
_VIEWS = sorted(glob.glob(os.path.join(_ROOT, "app", "views", "*.py")))
_ENTRYPOINT = os.path.join(_ROOT, "app", "Home.py")

pytest.importorskip("streamlit.testing.v1")


def _seeded_project(path=_EXAMPLE):
    from sloads import io
    return io.load_project(path)


def _run(path, project_path=_EXAMPLE):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(path, default_timeout=60)
    at.session_state["project"] = _seeded_project(project_path)
    at.run()
    return at


def test_entrypoint_builds_navigation():
    at = _run(_ENTRYPOINT)
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize("path", _VIEWS, ids=[os.path.basename(p) for p in _VIEWS])
def test_view_runs_without_exception(path):
    at = _run(path)
    assert not at.exception, [e.message for e in at.exception]


def test_weight_estimate_accepts_beyond_ga_power():
    """A loaded >3000 hp / >12-seat project must not trip a GA-tier widget cap."""
    at = _run(_WEIGHT_ESTIMATE, _BEYOND_GA)
    assert not at.exception, [e.message for e in at.exception]


def test_export_page_renders_with_every_slice_absent():
    """Step G8.6: the Export page (summary report included) has to survive an
    empty project -- it is the page an engineer lands on before any inputs exist,
    and every artifact on it is built from slices that are not there yet."""
    from streamlit.testing.v1 import AppTest

    from sloads import Project

    at = AppTest.from_file(_EXPORT, default_timeout=60)
    at.session_state["project"] = Project(name="empty")
    at.run()
    assert not at.exception, [e.message for e in at.exception]
