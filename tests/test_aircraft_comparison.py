"""Unit test for the Aircraft Comparison page's subject-assembly helper.

The page (``app/views/aircraft_comparison.py``) builds its comparison
:class:`~sloads.fleet.Subject` from whichever project slices are present, with a
documented priority per metric (backlog F2 step 2). The GUI itself is smoke-tested
by ``test_views_smoke.py``; this test pins the pure assembly logic: a populated
project yields a fully-metricked subject, a bare project yields ``None`` (no MTOW).

The view module runs Streamlit in *bare* mode on import (no ``AppTest``), which is
safe -- the page-level ``st.*`` calls are no-ops there -- so we load it directly and
call the private helper.
"""

import importlib.util
import logging
import os

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLE = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


def _load_view():
    path = os.path.join(_ROOT, "app", "views", "aircraft_comparison.py")
    spec = importlib.util.spec_from_file_location("aircraft_comparison", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_subject_from_example_project():
    # The GA-6 example carries a design weight (speeds) + installed power (engines)
    # and no parametric layout, but it *does* carry a WINGGEOM wing surface -- so the
    # geometric axes (area/AR/span) resolve from the surface fallback (M2-5), and the
    # subject is fully placed.
    from sloads import io
    view = _load_view()
    subject = view._subject_from_project(io.load_project(_EXAMPLE))
    assert subject is not None
    assert subject.mtow_lb > 0
    assert subject.power_hp and subject.power_hp > 0


def test_subject_geometric_axes_from_wing_surface():
    # M2-5: a project with geometry.surfaces (WINGGEOM planform) but no parametric
    # layout resolves wing area, aspect ratio and span from the wing surface. The GA-6
    # example carries no speeds.wing_area_sqft, so W/S is *only* computable via this
    # fallback. The recovered AR/span match the Appendix A wing (AR 6.095, span 33.5 ft).
    import math

    from sloads import io
    view = _load_view()
    subject = view._subject_from_project(io.load_project(_EXAMPLE))
    assert subject.wing_area_ft2 and subject.wing_area_ft2 > 0
    assert subject.w_s and subject.w_s > 0
    assert math.isclose(subject.aspect_ratio_effective, 6.095, rel_tol=1e-3)
    assert subject.span is not None and math.isclose(subject.span, 33.5, rel_tol=1e-2)


def test_area_priority_surface_over_speeds():
    # M2-5 priority: parametric -> surface -> speeds. When a project has both a
    # WINGGEOM wing surface and a scalar speeds.wing_area_sqft (and no parametric),
    # the computed planform wins.
    from sloads import io
    view = _load_view()
    project = io.load_project(os.path.join(_ROOT, "examples", "atr42_100.project.json"))
    assert project.speeds.wing_area_sqft  # the fixture carries a scalar area
    surf = view._wing_surface_props(project)
    assert surf.get("total_area")
    subject = view._subject_from_project(project)
    from sloads.constants import IN2_PER_FT2
    assert subject.wing_area_ft2 == surf["total_area"] / IN2_PER_FT2
    assert subject.wing_area_ft2 != project.speeds.wing_area_sqft


def test_subject_geometric_axes_from_configuration():
    # A project with a configuration slice resolves wing area + AR, and the subject's
    # span derives from sqrt(AR * S) even with no explicitly stored span.
    from sloads import (
        EngineInput,
        GeometryInput,
        LayoutInput,
        Project,
        StructuralSpeedsInput,
    )
    view = _load_view()
    project = Project(
        name="Synthetic",
        geometry=GeometryInput(parametric=LayoutInput(wing_area_sqft=180.0, aspect_ratio=7.5)),
        speeds=StructuralSpeedsInput(weight_lb=2450.0),
        engines=[EngineInput(max_cont_hp=180.0)],
    )
    subject = view._subject_from_project(project)
    assert subject is not None
    assert subject.mtow_lb == 2450.0
    assert subject.wing_area_ft2 == 180.0
    assert subject.power_hp == 180.0
    assert subject.aspect_ratio_effective == 7.5
    assert subject.span is not None and abs(subject.span - (7.5 * 180.0) ** 0.5) < 1e-9


def test_subject_is_none_without_mtow():
    from sloads import Project
    view = _load_view()
    assert view._subject_from_project(Project(name="")) is None


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
