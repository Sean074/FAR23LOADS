"""Validate WINGGEOM against the FAR 23 LOADS manual, Appendix A.

The authoritative oracle is the 6-place single's **wing**, whose geometric
properties are printed in Appendix A p141 (AREA/SIDE 13257, MAC 69.246,
YLE(MAC) 87.854, XLE(MAC) 63.641, ASPECT RATIO 6.095). The manual's figures are
themselves a strip sum over a count ``H`` it never prints (the wing element table
lists 20), so they carry that run's own discretisation; WINGGEOM integrates the
same planform in closed form and lands within ±0.1% of every one of them
(``02_approved_corrections.md``, 2026-08-30).

The aileron exercises the *unsymmetric* code path. It was checked only loosely
(±2%) while the result depended on a strip count the manual does not tabulate;
closed-form integration removed that dependence, so it is a tight oracle again.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import value_of

from sloads import GeometryInput, Project, SurfaceInput, io
from sloads.modules import wing_geometry as calc

TOL = 1e-3  # ±0.1% relative

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "ga6_normal.project.json",
)


def _surface(results, name):
    for r in results:
        if r.title.endswith(name):
            return r
    raise KeyError(name)


def wing_results():
    project = io.load_project(_EXAMPLE)
    return calc.geometry_properties(project.geometry, project)


def test_wing_matches_manual():
    # Appendix A p141 wing: AREA/SIDE 13257, MAC 69.246, YLE(MAC) 87.854,
    # XLE(MAC) 63.641, ASPECT RATIO 6.095, span = 2*201 = 402.
    r = _surface(wing_results(), "wing")
    assert math.isclose(value_of(r, "area_per_side"), 13257, rel_tol=TOL)
    assert math.isclose(value_of(r, "mac"), 69.246, rel_tol=TOL)
    assert math.isclose(value_of(r, "yle_mac_butt_line_of_mac"), 87.854, rel_tol=TOL)
    assert math.isclose(value_of(r, "xle_mac_station_of_mac_le"), 63.641, rel_tol=TOL)
    assert math.isclose(value_of(r, "aspect_ratio"), 6.095, rel_tol=TOL)
    assert value_of(r, "span") == 402
    assert value_of(r, "total_area") == 2 * value_of(r, "area_per_side")


def test_aileron_unsymmetric_path():
    # Appendix A p142 aileron (not sym about CL): AREA/SIDE 932, MAC 11.645,
    # AR 7.036. Closed-form integration reaches all three within 0.04%.
    r = _surface(wing_results(), "aileron")
    assert r.note.startswith("Single side")
    assert math.isclose(value_of(r, "area_per_side"), 932, rel_tol=TOL)
    assert math.isclose(value_of(r, "mac"), 11.645, rel_tol=TOL)
    assert math.isclose(value_of(r, "aspect_ratio"), 7.036, rel_tol=TOL)
    # Single-side surface: span and total area are not doubled.
    assert value_of(r, "total_area") == value_of(r, "area_per_side")


def test_too_few_load_stations_is_rejected():
    # ``elements`` no longer drives the integral (it is the load-station count),
    # but it is still a real input and a degenerate value is still refused.
    bad = SurfaceInput(name="x", leading_edge=[(0, 0), (0, 10)],
                       trailing_edge=[(10, 0), (10, 10)], elements=1)
    raised = False
    try:
        calc.surface_properties(bad)
    except ValueError:
        raised = True
    assert raised


def test_rectangular_wing_closed_form():
    # A rectangular wing (chord 10, half-span 50, LE at x=0): MAC = chord = 10,
    # AR = (2*50)^2 / (2 * 10*50) = 10000/1000 = 10, span = 100, XLEMAC = 0.
    surf = SurfaceInput(
        name="rect", symmetric=True, elements=20,
        leading_edge=[(0, 0), (0, 50)], trailing_edge=[(10, 0), (10, 50)],
    )
    r = calc.surface_properties(surf)
    assert math.isclose(value_of(r, "mac"), 10.0, rel_tol=TOL)
    assert math.isclose(value_of(r, "aspect_ratio"), 10.0, rel_tol=TOL)
    assert math.isclose(value_of(r, "xle_mac_station_of_mac_le"), 0.0, abs_tol=1e-9)
    assert value_of(r, "span") == 100


def test_engine_stations_for_wing_layout():
    # A wing-mounted twin reports each engine's butt line + local wing chord.
    project = io.load_project(_EXAMPLE)
    from dataclasses import replace

    from fixtures import io520bb

    from sloads import EngineLayout

    left = replace(io520bb(), engine_designation="LEFT", engine_cg=(60.0, -60.0, 90.0))
    right = replace(io520bb(), engine_designation="RIGHT", engine_cg=(60.0, 60.0, 90.0))
    project.engines = [left, right]
    project.engine_layout = EngineLayout.TWIN_WING
    results = calc.geometry_properties(project.geometry, project)
    stations = _surface(results, "stations") if any(r.title.endswith("stations") for r in results) else None
    assert stations is not None
    assert value_of(stations, "engine_1_butt_line_y") == -60.0
    assert value_of(stations, "engine_2_butt_line_y") == 60.0


def test_run_requires_geometry():
    raised = False
    try:
        calc.run(Project(name="empty"))
    except ValueError:
        raised = True
    assert raised
    raised = False
    try:
        calc.run(Project(name="no surfaces", geometry=GeometryInput()))
    except ValueError:
        raised = True
    assert raised


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
    sys.exit(1 if failed else 0)
