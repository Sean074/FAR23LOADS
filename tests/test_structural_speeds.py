"""Validate STRSPEED against the FAR 23 LOADS manual, Appendix A.

The 6-place single's structural speeds and load factors are printed in the
Appendix A V-n / geometry table: VA 121.3, VC 170, VD 212.5, VF 105.5 (KEAS);
limit load factor +3.8 / -1.52; and MC 0.323 / MD 0.403 at the 12000 ft shoulder
altitude. The maneuver speed VA = VS*sqrt(n) and flap speed VF = 1.8*VSF are
computed from the (input) clean/flap stall speeds, so they validate the equations
rather than echoing inputs; VC is chosen and VD is its 1.25 floor.

Per Decision 3 the figures are matched within ±0.1%; the wing area (read from the
WINGGEOM geometry slice, 2*13257/144 = 184.1 ft^2) is g-independent.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import AeroCoefficientsInput, Project, StructuralSpeedsInput, io  # noqa: E402
from farloads.constants import (  # noqa: E402
    cruise_speed_coefficient,
    dive_ratio_coefficient,
)
from farloads.modules import structural_speeds as calc  # noqa: E402

TOL = 1e-3  # ±0.1% relative


def _project_clmax(name, clmax_clean, clmax_flap):
    """A Project carrying only the CLmax (stall-speed source) on aero_coeffs -- the
    minimum STRSPEED needs to derive VS/VSF (M1-1b)."""
    return Project(name=name, aero_coeffs=AeroCoefficientsInput(
        clmax_clean=clmax_clean, clmax_flap=clmax_flap))

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "ga6_normal.project.json",
)


def results():
    project = io.load_project(_EXAMPLE)
    return calc.design_speeds(project, project.speeds)


def _value(conditions, label):
    for c in conditions:
        for v in c.values:
            if v.label == label:
                return v.value
    raise KeyError(label)


def test_maneuver_load_factors():
    # W = 3400, normal: n = 2.1 + 24000/13400 = 3.891 -> capped 3.8; n_neg = -1.52.
    r = results()
    assert math.isclose(_value(r, "Limit positive load factor"), 3.8, rel_tol=TOL)
    assert math.isclose(_value(r, "Limit negative load factor"), -1.52, rel_tol=TOL)
    assert math.isclose(_value(r, "Wing loading W/S"), 3400 / 184.125, rel_tol=2e-3)


def test_design_speeds_match_manual():
    # Appendix A: VA 121.3, VC 170, VD 212.5, VF 105.5 (KEAS).
    r = results()
    assert math.isclose(_value(r, "Maneuver speed VA"), 121.3, rel_tol=TOL)
    assert math.isclose(_value(r, "Cruise speed VC"), 170, rel_tol=TOL)
    assert math.isclose(_value(r, "Dive speed VD"), 212.5, rel_tol=TOL)
    assert math.isclose(_value(r, "Flap speed VF"), 105.5, rel_tol=TOL)


def test_vd_floor_no_chosen_speeds():
    # Appendix A p155, Cat N, no chosen speeds: FAR 23.335(b) requires
    # VD >= max(K_d*VCmin, 1.25*VC). Here K_d*VCmin = 1.40*141.8 = 198.53 kt
    # governs over 1.25*VCmin = 177.26. (Pre-fix code returned 177.26 -- 10.7%
    # non-conservative; STRSPEED.BAS V2DMIN=K2*V1CMIN, lines 380/390.)
    inp = StructuralSpeedsInput(category="N", weight_lb=3400, wing_area_sqft=184.125,
                                vh_kt=190)
    r = calc.design_speeds(_project_clmax("n", 1.4068, 1.5857), inp)
    assert math.isclose(_value(r, "Dive speed VD"), 198.53, rel_tol=TOL)          # p155
    assert math.isclose(_value(r, "Minimum dive VD(min)"), 198.53, rel_tol=TOL)


def test_minimum_cruise_speed():
    # K_c = 33 (W/S = 18.47 < 20); VC(min) = 33*sqrt(18.47) = 141.8 kt.
    r = results()
    assert math.isclose(_value(r, "Minimum cruise VC(min)"), 141.8, rel_tol=2e-3)


def test_cruise_and_dive_mach_at_shoulder():
    # At 12000 ft: MC 0.323, MD 0.403.
    r = results()
    assert math.isclose(_value(r, "Cruise Mach MC"), 0.323, rel_tol=3e-3)
    assert math.isclose(_value(r, "Dive Mach MD"), 0.403, rel_tol=3e-3)


def test_utility_and_acrobatic_caps():
    # Category caps: utility 4.4, acrobatic 6.0; negative -0.4n / -0.5n.
    base = dict(weight_lb=3400, wing_area_sqft=184.125, chosen_vc=170, chosen_vd=212.5)
    u = calc.design_speeds(_project_clmax("u", 1.4068, 1.5857),
                           StructuralSpeedsInput(category="U", **base))
    a = calc.design_speeds(_project_clmax("a", 1.4068, 1.5857),
                           StructuralSpeedsInput(category="A", **base))
    assert math.isclose(_value(u, "Limit positive load factor"), 4.4, rel_tol=TOL)
    assert math.isclose(_value(u, "Limit negative load factor"), -0.4 * 4.4, rel_tol=TOL)
    assert math.isclose(_value(a, "Limit positive load factor"), 6.0, rel_tol=TOL)
    assert math.isclose(_value(a, "Limit negative load factor"), -0.5 * 6.0, rel_tol=TOL)


def test_concept_bypasses_cap():
    # Category C (concept): the user's n / n_neg are used verbatim, with no
    # FAR 23.337 formula or cap -- even above the 12,500 lb GA band.
    inp = StructuralSpeedsInput(category="C", weight_lb=18000, wing_area_sqft=280,
                                chosen_vc=250, chosen_vd=312.5,
                                chosen_n=4.0, chosen_nneg=-2.0)
    r = calc.design_speeds(_project_clmax("c", 2.101, 2.821), inp)
    assert _value(r, "Limit positive load factor") == 4.0
    assert _value(r, "Limit negative load factor") == -2.0


def test_concept_requires_explicit_load_factors():
    # Concept mode without chosen_n/chosen_nneg is an error (there is no FAR floor
    # to fall back on).
    inp = StructuralSpeedsInput(category="C", weight_lb=18000, wing_area_sqft=280,
                                chosen_vc=250, chosen_vd=312.5)
    raised = False
    try:
        calc.design_speeds(_project_clmax("c", 2.101, 2.821), inp)
    except ValueError:
        raised = True
    assert raised


def test_speed_coefficients_clamp_at_wing_loading_100():
    # FAR 23.335 tabulates Kc/Kd only to W/S = 100 (28.6 / 1.35). Past 100 the
    # coefficients HOLD at those endpoints; prior code kept extrapolating the taper
    # (non-conservative for the heavy-concept band). M1-6 (review T9).
    for cat in ("N", "U", "A"):
        # Continuous at the boundary: the taper reaches the endpoint exactly at 100.
        assert math.isclose(cruise_speed_coefficient(cat, 100.0), 28.6, rel_tol=TOL)
        assert math.isclose(dive_ratio_coefficient(cat, 100.0), 1.35, rel_tol=TOL)
        # Clamped (not extrapolated below the endpoint) well past 100.
        assert cruise_speed_coefficient(cat, 180.0) == cruise_speed_coefficient(cat, 100.0)
        assert dive_ratio_coefficient(cat, 180.0) == dive_ratio_coefficient(cat, 100.0)
        assert math.isclose(cruise_speed_coefficient(cat, 180.0), 28.6, rel_tol=TOL)
        assert math.isclose(dive_ratio_coefficient(cat, 180.0), 1.35, rel_tol=TOL)


def test_out_of_band_note_above_wing_loading_100():
    # A concept with W/S > 100 gets an OUT-OF-BAND note on the design-speeds
    # condition; a GA aircraft (W/S ~ 20) does not. M1-6 (review T9).
    inp = StructuralSpeedsInput(category="C", weight_lb=40000, wing_area_sqft=280,
                                chosen_vc=300, chosen_vd=375,
                                chosen_n=4.0, chosen_nneg=-2.0)
    r = calc.design_speeds(_project_clmax("c", 2.101, 2.821), inp)
    speeds = next(c for c in r if c.title == "Structural design speeds")
    assert "OUT-OF-BAND" in speeds.note

    ga = next(c for c in results() if c.title == "Structural design speeds")
    assert ga.note == ""


def test_run_requires_speeds():
    raised = False
    try:
        calc.run(Project(name="empty"))
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
