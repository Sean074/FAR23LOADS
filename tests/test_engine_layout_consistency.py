"""An engine layout that disagrees with the engine count (#66; review 2026-08-22 PB-7).

``engine_layout`` (``2W``: two engines on the wing) and ``engines`` are two
widgets on one page, set in either order. The constructor used to enforce
their agreement, so the in-session project accepted the disagreement, Save
wrote it, and the loader refused the file -- lost work. The rule now has one
owner, :meth:`Project.engine_layout_problem`, and three readers: the loader
flags (the file loads), the oracle page withholds its results, and the one
consumer of the layout refuses by name.
"""

from __future__ import annotations

import os
import warnings

import pytest

from sloads import EngineLayout, Project, io, registry
from sloads.field_registry import reduce_to_oracle_inputs

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


def _mismatched() -> Project:
    """The review's reproduction: the reduced GA-6 (one engine) set to ``2W``."""
    project = reduce_to_oracle_inputs(io.load_project(_GA6))
    assert len(project.engines) == 1
    project.engine_layout = EngineLayout.TWIN_WING
    return project


def test_the_rule_has_one_owner_and_says_the_numbers():
    project = _mismatched()
    assert project.engine_layout_problem() == "engine_layout 2W expects 2 engine(s), got 1"
    project.engine_layout = EngineLayout.SINGLE_NOSE
    assert project.engine_layout_problem() is None
    assert Project(name="no engines", engine_layout=EngineLayout.TWIN_WING).engine_layout_problem() is None


def test_a_mismatched_state_saves_reloads_and_is_flagged():
    """Save -> reload is a round trip with a warning, not a refusal."""
    text = io.project_to_json(_mismatched())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        back = io.project_from_dict(__import__("json").loads(text))
    assert back.engine_layout is EngineLayout.TWIN_WING and len(back.engines) == 1
    assert [str(w.message) for w in caught] == [
        "engine_layout 2W expects 2 engine(s), got 1; fix the engine layout on the Engine Mount page"]
    assert io.project_to_json(back) == text


def test_winggeom_refuses_the_mismatch_by_name():
    with pytest.raises(ValueError, match="engine_layout 2W expects 2 engine"):
        registry.get("wing_geometry")(_mismatched())


def test_the_oracle_page_withholds_its_results_until_they_agree():
    from streamlit.testing.v1 import AppTest

    script = '''
import streamlit as st
from oracle_app.form import render_step
render_step("engine_mount")
'''
    project = _mismatched()
    at = AppTest.from_string(script, default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any("engine_layout 2W expects 2 engine(s), got 1" in e.value
               and "Engine Mount" in e.value for e in at.error)
    assert not [h for h in at.header if h.value == "Results"]

    project.engine_layout = EngineLayout.SINGLE_NOSE
    at = AppTest.from_string(script, default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.error and [h for h in at.header if h.value == "Results"]


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
