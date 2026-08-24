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


def _run(path, project_path=_EXAMPLE, project=None):
    """Render one view. ``project=`` seeds a mutated project directly, for the
    cases whose point is an input state no example file holds."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(path, default_timeout=60)
    at.session_state["project"] = (project if project is not None
                                   else _seeded_project(project_path))
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


# --------------------------------------------------------------------------- #
# A page that computes a quantity has to show it (#85). "No exception" is not
# the same as "rendered": the flap page's whole slipstream block was dead from
# the day it was written, and every smoke test above passed over it in silence.
# --------------------------------------------------------------------------- #
_FLAP = os.path.join(_ROOT, "app", "views", "flap_loads.py")


def test_flap_page_shows_the_slipstream_it_computes():
    """The GA-6 has propeller power, so the 23.457(b) block must be on the page.

    Read from the **rendered elements**, not from the source: the defect this
    guards was a source that looked right (``if "Slipstream factor" in vals``)
    against a dict keyed by ``LoadValue.key``, so the test that proves it is the
    one that looks at what the user sees (the G7 lesson).
    """
    at = _run(_FLAP)
    assert not at.exception, [e.message for e in at.exception]
    assert any("Slipstream" in s.value for s in at.subheader), \
        [s.value for s in at.subheader]
    shown = {m.label: m.value for m in at.metric}
    for label in ("Slipstream factor", "Flap load in slipstream (lb, LIMIT)"):
        assert label in shown, sorted(shown)
    # The governing number is printed, not left as an exercise: factor x the
    # VF-governed condition, ~1.47 x 630 on this airplane.
    assert float(shown["Slipstream factor"]) > 1.0
    assert int(shown["Flap load in slipstream (lb, LIMIT)"].replace(",", "")) > 0
    # ... and says nothing about a skip it did not make.
    assert not any("slipstream effect included" in w.value for w in at.warning)


def test_one_engine_out_page_states_the_condition_does_not_apply():
    """#84: the GA6 single must be told 23.367 does not apply to it, in the shared
    predicate's words -- the page's own ``len(engines) < 2`` test said something
    close, but missed the centreline twin and did not match what the module said."""
    at = _run(os.path.join(_ROOT, "app", "views", "one_engine_out.py"))
    assert not at.exception, [e.message for e in at.exception]
    said = " ".join(i.value for i in at.info)
    assert "FAR 23.367 does not apply" in said, said


def test_flap_page_says_when_the_slipstream_is_skipped():
    """#83: with the band entered but no engine record, the page must say the
    23.457(b) case is absent -- in *this* GUI too, not only in the oracle GUI.

    The flap view opened with a bare ``st.title`` until #83, so the #82 renderer
    (which hangs off ``page_header``) never reached it and the warning would have
    been oracle-GUI-only -- the exact divergence #82 was written to end.
    """
    project = _seeded_project()
    project.engines = []
    at = _run(_FLAP, project=project)
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "slipstream effect included" in shown, [w.value for w in at.warning]
    assert "Engine Mount Loads" in shown
    # The page still computes and shows the load it *can* justify.
    assert not any("Slipstream" in s.value for s in at.subheader), \
        [s.value for s in at.subheader]


def test_no_view_tests_a_display_label_against_a_key_dict():
    """`vals` dicts are keyed by ``LoadValue.key`` -- never by the label.

    Rule 3 drift guard. ``"Slipstream factor" in vals`` is always False against
    ``{v.key: ...}``, and it fails **silently**: the block simply never renders.
    This was the only instance in ``app/views`` when it was found (#85); the
    guard states that as an absolute so a second one cannot appear.
    """
    import re

    bad = re.compile(r'["\'][A-Z][^"\']*["\']\s+(?:not\s+)?in\s+vals\b')
    offenders = []
    for path in _VIEWS:
        with open(path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if line.lstrip().startswith("#"):
                    continue
                if bad.search(line):
                    offenders.append(f"{os.path.basename(path)}:{n}: {line.strip()}")
    assert not offenders, offenders
