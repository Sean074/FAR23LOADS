"""Wing inertia loads (Step C3): WINGINER port.

Oracle-locked against the Appendix A "Wing Inertia Loads" worked example
(p217-221): the iterated root/tip area density and the unit + combined inertia
distributions along the 25% chord. The math is faithful to WINGINER.BAS, so these
match the manual's printed integers; small quantities use an absolute floor.

Reference: WINGINER.BAS (Appendix C p455-458), Ref 1 Ch 13; Appendix A p217-221.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, WingLoadCase, io  # noqa: E402
from farloads.modules import wing_inertia as wi  # noqa: E402
from farloads.modules.wing_inertia import inertia_units, wing_inertia_distribution  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _units():
    p = io.load_project(_GA)
    geom = p.geometry.by_name("wing")
    return geom, p.wing_mass, inertia_units(geom, p.wing_mass)


def _close(a, e, rel=2e-3, abs_=2.0):
    return math.isclose(a, e, rel_tol=rel, abs_tol=abs_)


def test_root_tip_density_match_appendix_a():
    _, _, u = _units()
    assert math.isclose(u.density_root, 2.213, abs_tol=0.002)   # lb/ft^2, p217
    assert math.isclose(u.density_tip, 2.102, abs_tol=0.002)


def test_unit_vertical_distribution_matches_appendix_a():
    geom, wm, u = _units()
    r = wing_inertia_distribution(geom, wm, WingLoadCase("1001", nz=-1.0, nx=0.0), u)
    root = r.stations[0]
    assert _close(root.sz, -167)        # cumulative panel mass, p220
    assert _close(root.mxx, -16158)
    assert _close(root.myy, 4482)


def test_unit_drag_distribution_matches_appendix_a():
    geom, wm, u = _units()
    r = wing_inertia_distribution(geom, wm, WingLoadCase("1002", nz=0.0, nx=1.0), u)
    root = r.stations[0]
    assert _close(root.sx, 167)
    assert _close(root.mzz, 16158)
    assert _close(root.myy, 1698)


def test_unit_roll_distribution_matches_appendix_a():
    geom, wm, u = _units()
    r = wing_inertia_distribution(geom, wm, WingLoadCase("1003", unbal_moment=-100000), u)
    tip = r.stations[-1]
    assert _close(tip.fz, -30, abs_=1.5)   # FZ = W*Y*1e5/Iwxx, p220
    assert _close(tip.sz, -30, abs_=1.5)
    assert _close(tip.myy, 337, abs_=2.0)


def test_combined_torsion_case_matches_appendix_a():
    # Case 138 TORS: Nz -2.54, Nx -0.1318, no roll (p221).
    geom, wm, u = _units()
    r = wing_inertia_distribution(geom, wm, WingLoadCase("138", nz=-2.54, nx=-0.1318), u)
    root = r.stations[0]
    assert _close(root.sz, -423)
    assert _close(root.sx, -22, abs_=2.0)
    assert _close(root.mxx, -41041)
    assert _close(root.myy, 11161)
    assert _close(root.mzz, -2130)


def test_inboard_strips_carry_no_panel_mass():
    # Strips inboard of the rib (BL 23) have zero panel weight (WINGINER.BAS 770).
    geom, wm, u = _units()
    r = wing_inertia_distribution(geom, wm, WingLoadCase("v", nz=1.0), u)
    assert r.stations[0].fz == 0.0     # Y = 5.025 < 23
    assert r.stations[1].fz == 0.0     # Y = 15.075 < 23


def test_concentrated_weight_adds_inboard_shear():
    # A concentrated weight adds its full load to the shear at every inboard station.
    from farloads import WingMassInput
    geom, _, _ = _units()
    base = wing_inertia_distribution(
        geom, WingMassInput(panel_weight_lb=165, tip_root_density_ratio=0.95, inboard_rib_y=23,
                            wrp_waterline=78.5, dihedral_deg=6.0), WingLoadCase("v", nz=1.0))
    from farloads import ConcentratedWeight
    withcw = wing_inertia_distribution(
        geom, WingMassInput(panel_weight_lb=165, tip_root_density_ratio=0.95, inboard_rib_y=23,
                            wrp_waterline=78.5, dihedral_deg=6.0,
                            concentrated=[ConcentratedWeight("store", 100.0, x=83.0, y=100.0, z=87.0)]),
        WingLoadCase("v", nz=1.0))
    # Root shear rises by the full 100 lb; a station outboard of the weight is unchanged.
    assert math.isclose(withcw.stations[0].sz - base.stations[0].sz, 100.0, abs_tol=1e-6)
    assert math.isclose(withcw.stations[-1].sz, base.stations[-1].sz, abs_tol=1e-6)


def test_run_requires_wing_mass_slice():
    try:
        wi.run(Project(name="no-wing-mass"))
    except ValueError:
        return
    raise AssertionError("expected ValueError when the wing_mass slice is missing")


def test_run_produces_one_condition_per_case():
    result = wi.run(io.load_project(_GA))
    assert result.module == "wing_inertia"
    assert len(result.conditions) == 3   # PHAA / TORS / ACRL


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
