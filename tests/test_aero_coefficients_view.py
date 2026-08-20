"""Aerodynamic Data page: the M4-5 curve section and the CLmax-carry-through fix.

Two things the pure-calc tests cannot see:

* the coefficient-curve section renders on a full project **and** degrades to
  curves-only when there is no balanced envelope to overlay (the page must never
  depend on FLTLOADS being runnable);
* **the fuselage-moment Apply must not touch the CLmax scalars.** That form
  rebuilt the whole ``aero_coeffs`` slice without them, so ``__post_init__``
  re-derived them from the per-config ``stall_cl`` -- silently moving VS (and
  hence VA/VF on the Structural Speeds page) wherever the two legitimately
  differ, which on the Appendix A GA fixture they do (1.4068 vs 1.41). Same
  defect class as M4-22: a form handler writing a slice it does not own.

Driven headlessly via ``AppTest``.
"""

import logging
import math
import os
import sys

import pytest

from helpers import apply_button

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEW = os.path.join(_ROOT, "app", "views", "aero_coefficients.py")
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")
_RJ = os.path.join(_ROOT, "examples", "concept_regional_jet.project.json")

for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytest.importorskip("streamlit.testing.v1")


def _run(project):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(_VIEW, default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _ga6():
    from sloads import io
    return io.load_project(_GA6)


def _rj():
    """The regional-jet concept -- the fixture whose fuselage outline renders the
    Munk estimator's Apply form (ga6 carries no outline, so the form is absent)."""
    from sloads import io
    return io.load_project(_RJ)


def test_the_curve_section_renders_with_the_envelope_overlay():
    at = _run(_ga6())
    # One three-panel figure for the single (cruise) configuration.
    assert len(at.get("plotly_chart")) == 1
    assert any("Coefficient curves" in str(h.value) for h in at.get("subheader"))
    # The closure metrics are present and the page reports no exceedance banner.
    labels = [m.label for m in at.get("metric")]
    assert "Recovered-CL closure" in labels
    assert "Stall-clamp margin" in labels
    assert not [w for w in at.warning if "exceeds the stall CL" in str(w.value)]


def test_the_curves_render_without_a_balanced_envelope():
    """No speeds slice -> no overlay, but the curves themselves still draw."""
    project = _ga6()
    project.speeds = None
    at = _run(project)
    assert len(at.get("plotly_chart")) == 1
    assert not [m for m in at.get("metric") if m.label == "Recovered-CL closure"]
    assert any("Curves only" in str(i.value) for i in at.get("info"))


def test_an_empty_project_stops_before_the_curves():
    from sloads import Project

    at = _run(Project(name="empty"))
    assert not at.get("plotly_chart")


def test_a_coefficient_entry_error_surfaces_as_a_page_warning():
    from dataclasses import replace

    project = _ga6()
    cruise = project.aero_coeffs.cruise
    project.aero_coeffs.cruise = replace(cruise, drag=(-0.05, 0.0, 0.001, 0.0, 0.0))
    at = _run(project)
    assert any("drag polar" in str(w.value) for w in at.warning)


def test_applying_the_fuselage_moment_preserves_the_clmax_scalars():
    """The batched M4-5 fix: the fuselage-moment form owns only its sub-slice.

    Driven on the regional-jet concept, the one shipped fixture whose geometry
    renders the estimator's form. It carries clmax_clean 1.3983 against a
    per-config stall_cl of 1.4, and a clmax_flap of 2.2035 with **no** flaps-down
    coefficient set to re-derive it from -- so before the fix this Apply moved
    the first and zeroed the second.
    """
    project = _rj()
    before = (project.aero_coeffs.clmax_clean, project.aero_coeffs.clmax_clean_neg,
              project.aero_coeffs.clmax_flap)
    assert not math.isclose(before[0], project.aero_coeffs.cruise.stall_cl, rel_tol=1e-9), (
        "fixture no longer distinguishes clmax_clean from stall_cl; the guard is moot")
    assert before[2] and project.aero_coeffs.flaps_down is None

    at = _run(project)
    apply_button(at, "fuselage_moment_form").click().run()
    assert not at.exception, [e.message for e in at.exception]

    after = at.session_state["project"].aero_coeffs
    assert math.isclose(after.clmax_clean, before[0], rel_tol=1e-12)
    assert math.isclose(after.clmax_clean_neg, before[1], rel_tol=1e-12)
    assert math.isclose(after.clmax_flap, before[2], rel_tol=1e-12)
    # And the form still did its own job.
    assert after.fuselage_moment is not None


def test_applying_the_fuselage_moment_leaves_the_design_speeds_untouched():
    """The consequence the CLmax drift actually had: VS/VSF -> VA/VF."""
    from sloads.modules.structural_speeds import design_speed_values

    project = _rj()
    before = design_speed_values(project, project.speeds)

    at = _run(project)
    apply_button(at, "fuselage_moment_form").click().run()
    after_project = at.session_state["project"]
    after = design_speed_values(after_project, after_project.speeds)

    for key in ("vs", "vsf", "va", "vf"):
        assert math.isclose(getattr(after, key), getattr(before, key), rel_tol=1e-12), (
            f"{key} moved when only the fuselage moment was applied")


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print(f"ok  {_name}")
    print("all aero-coefficients view tests passed")
