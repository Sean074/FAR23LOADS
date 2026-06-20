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

from farloads import Project, StructuralSpeedsInput, io  # noqa: E402
from farloads.modules import structural_speeds as calc  # noqa: E402

TOL = 1e-3  # ±0.1% relative

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
    base = dict(weight_lb=3400, wing_area_sqft=184.125, stall_clean_kt=62.226,
                stall_flap_kt=58.611, chosen_vc=170, chosen_vd=212.5)
    u = calc.design_speeds(Project(name="u"), StructuralSpeedsInput(category="U", **base))
    a = calc.design_speeds(Project(name="a"), StructuralSpeedsInput(category="A", **base))
    assert math.isclose(_value(u, "Limit positive load factor"), 4.4, rel_tol=TOL)
    assert math.isclose(_value(u, "Limit negative load factor"), -0.4 * 4.4, rel_tol=TOL)
    assert math.isclose(_value(a, "Limit positive load factor"), 6.0, rel_tol=TOL)
    assert math.isclose(_value(a, "Limit negative load factor"), -0.5 * 6.0, rel_tol=TOL)


def test_concept_bypasses_cap():
    # Category C (concept): the user's n / n_neg are used verbatim, with no
    # FAR 23.337 formula or cap -- even above the 12,500 lb GA band.
    inp = StructuralSpeedsInput(category="C", weight_lb=18000, wing_area_sqft=280,
                                stall_clean_kt=95, stall_flap_kt=82,
                                chosen_vc=250, chosen_vd=312.5,
                                chosen_n=4.0, chosen_nneg=-2.0)
    r = calc.design_speeds(Project(name="c"), inp)
    assert _value(r, "Limit positive load factor") == 4.0
    assert _value(r, "Limit negative load factor") == -2.0


def test_concept_requires_explicit_load_factors():
    # Concept mode without chosen_n/chosen_nneg is an error (there is no FAR floor
    # to fall back on).
    inp = StructuralSpeedsInput(category="C", weight_lb=18000, wing_area_sqft=280,
                                stall_clean_kt=95, stall_flap_kt=82,
                                chosen_vc=250, chosen_vd=312.5)
    raised = False
    try:
        calc.design_speeds(Project(name="c"), inp)
    except ValueError:
        raised = True
    assert raised


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
