"""Unit tests for the pure input-consistency predicates (``sloads.validation``).

Each predicate must fire on a crafted bad input and stay silent on well-formed
input -- in particular on the Appendix-A GA fixture (``examples/ga6_normal``),
where the tool reduces to the oracle-locked FAR 23 behaviour and nothing is
inconsistent.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import (
    LayoutInput,
    MassItem,
    MassItemKind,
    Project,
    SurfaceInput,
    consistency_warnings,
)
from sloads import io as sloads_io
from sloads.models import GeometryInput

_GA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "examples", "ga6_normal.project.json")


def _codes(project, page=None):
    return {w.code for w in consistency_warnings(project)
            if page is None or w.page == page}


def test_ga_fixture_is_clean():
    project = sloads_io.load_project(_GA)
    assert consistency_warnings(project) == []


def test_taper_gt_1_fires():
    project = Project(name="t", geometry=GeometryInput(parametric=LayoutInput(
        wing_area_sqft=150.0, aspect_ratio=7.0, taper_ratio=1.4, fuselage_length=300.0)))
    assert "taper_gt_1" in _codes(project)


def test_taper_le_1_silent():
    project = Project(name="t", geometry=GeometryInput(parametric=LayoutInput(
        wing_area_sqft=150.0, aspect_ratio=7.0, taper_ratio=0.5, fuselage_length=300.0)))
    assert "taper_gt_1" not in _codes(project)


def test_nonpositive_area_fires():
    project = Project(name="t", geometry=GeometryInput(parametric=LayoutInput(
        wing_area_sqft=0.0, aspect_ratio=7.0, taper_ratio=0.5, fuselage_length=300.0)))
    assert "nonpositive_area" in _codes(project)


def test_le_te_ordering_fires_when_le_behind_te():
    # Leading edge aft of the trailing edge (X_LE > X_TE) -- inverted chord.
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(100.0, 0.0), (110.0, 100.0)],
        trailing_edge=[(90.0, 0.0), (95.0, 100.0)])
    project = Project(name="t", geometry=GeometryInput(surfaces=[surf]))
    assert "le_te_ordering" in _codes(project, page="wing_geometry")


def test_le_te_ordering_silent_when_well_formed():
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(90.0, 0.0), (95.0, 100.0)],
        trailing_edge=[(120.0, 0.0), (118.0, 100.0)])
    project = Project(name="t", geometry=GeometryInput(surfaces=[surf]))
    assert "le_te_ordering" not in _codes(project)


def test_area_mismatch_fires():
    # WINGGEOM planform ~ (120 in chord * 400 in span)/144 = 333 ft^2, well away
    # from the 150 ft^2 claimed on Configuration & Layout.
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(0.0, 0.0), (0.0, 200.0)],
        trailing_edge=[(120.0, 0.0), (120.0, 200.0)])
    project = Project(
        name="t",
        geometry=GeometryInput(
            parametric=LayoutInput(wing_area_sqft=150.0, aspect_ratio=7.0, fuselage_length=300.0),
            surfaces=[surf]))
    assert "area_mismatch" in _codes(project)


def test_area_match_silent():
    # Planform (120 in * 200 in half-span, symmetric)/144 -> match config area.
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(0.0, 0.0), (0.0, 200.0)],
        trailing_edge=[(120.0, 0.0), (120.0, 200.0)])
    from sloads.modules.wing_geometry import surface_properties
    area_ft2 = next(v.value for v in surface_properties(surf).values
                    if v.label == "Total area") / 144.0
    project = Project(
        name="t",
        geometry=GeometryInput(
            parametric=LayoutInput(wing_area_sqft=area_ft2, aspect_ratio=7.0, fuselage_length=300.0),
            surfaces=[surf]))
    assert "area_mismatch" not in _codes(project)


def test_cg_outside_envelope_fires():
    project = sloads_io.load_project(_GA)
    # Push the loading CG far aft with a heavy tail-boom mass well behind any limit.
    project.weight.items.append(MassItem(
        name="ballast", weight_lb=5000.0, x=100000.0, y=0.0, z=0.0,
        ixx=0.0, iyy=0.0, izz=0.0, kind=MassItemKind.DISCRETIONARY))
    assert "cg_outside_envelope" in _codes(project, page="weight_cg_inertia")


def test_cg_check_skipped_without_envelope():
    project = sloads_io.load_project(_GA)
    project.weight.envelope = None  # no WTENV envelope -> check silently skipped
    assert "cg_outside_envelope" not in _codes(project)


def test_operational_target_infeasible_fires():
    # A target VNE above 0.9*VD (GA6 VD 212.5 -> cap 191.25) is infeasible and
    # surfaces on the Design Speeds page for the dashboard (M2-10).
    project = sloads_io.load_project(_GA)
    project.speeds.target_vne = 250.0  # needs VD >= 277.8, chosen VD 212.5
    assert "operational_target_infeasible" in _codes(project, page="structural_speeds")


def test_operational_target_feasible_silent():
    # A reachable target produces no warning (VNE 180 needs VD >= 200 <= 212.5).
    project = sloads_io.load_project(_GA)
    project.speeds.target_vne = 180.0
    assert "operational_target_infeasible" not in _codes(project)


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
