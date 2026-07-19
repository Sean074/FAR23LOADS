"""Unit test for the Aircraft Comparison page's subject-assembly helper.

The page (``app/views/aircraft_comparison.py``) builds its comparison
:class:`~farloads.fleet.Subject` from whichever project slices are present, with a
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
    # but no configuration slice, so MTOW and power resolve while the geometric axes
    # stay absent -- the subject is still placed (not dropped).
    from farloads import io
    view = _load_view()
    subject = view._subject_from_project(io.load_project(_EXAMPLE))
    assert subject is not None
    assert subject.mtow_lb > 0
    assert subject.power_hp and subject.power_hp > 0


def test_subject_geometric_axes_from_configuration():
    # A project with a configuration slice resolves wing area + AR, and the subject's
    # span derives from sqrt(AR * S) even with no explicitly stored span.
    from farloads import (
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
    from farloads import Project
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
