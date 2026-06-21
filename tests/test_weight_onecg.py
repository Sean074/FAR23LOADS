"""Validate WTONECG against the FAR 23 LOADS manual, Appendix A.

The worked example is the 6-place single's *aft gross weight* loading, whose
weight/CG/inertia report is printed in Appendix A p136. The itemized weight data
base is carried in ``examples/ga6_normal.project.json`` (the same file the engine
example uses), so this test exercises the JSON load path as well as the calc.

Per Decision 3 ("modernize the math", g kept at 32.174) the slug-ft^2 figures are
matched within ±0.1% of the manual's printed numbers; the lb-in^2 accumulator and
the weight are g-independent.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, WeightInput, io  # noqa: E402
from farloads.modules import weight_onecg as calc  # noqa: E402

TOL = 1e-3  # ±0.1% relative

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "ga6_normal.project.json",
)


def aft_gross_result():
    project = io.load_project(_EXAMPLE)
    return calc.weights_and_inertia(project.weight.items)


def _value(result, label):
    for v in result.values:
        if v.label == label:
            return v.value
    raise KeyError(label)


def test_weight_and_cg_match_manual():
    # Appendix A p136 (aft gross weight CG): WEIGHT 3400, XBAR 84.99936,
    # ZBAR 92.57932.
    r = aft_gross_result()
    assert _value(r, "Weight") == 3400
    assert math.isclose(_value(r, "XBAR (fus station)"), 84.99936, rel_tol=TOL)
    assert math.isclose(_value(r, "ZBAR (waterline)"), 92.57932, rel_tol=TOL)


def test_inertias_airplane_axes_match_manual():
    # Appendix A p136, slug-ft^2: IXX 1201.527, IYY 2058.209, IZZ 3022.766,
    # IXZ 134.4063.
    r = aft_gross_result()
    assert math.isclose(_value(r, "IXX"), 1201.527, rel_tol=TOL)
    assert math.isclose(_value(r, "IYY"), 2058.209, rel_tol=TOL)
    assert math.isclose(_value(r, "IZZ"), 3022.766, rel_tol=TOL)
    assert math.isclose(_value(r, "IXZ"), 134.4063, rel_tol=TOL)


def test_inertias_lb_in2_match_manual():
    # Appendix A p136, lb-in^2: IXX 5566051, IYY 9534613, IZZ 14002901, IXZ 622634.
    r = aft_gross_result()
    assert math.isclose(_value(r, "IXX (lb-in^2)"), 5566051, rel_tol=TOL)
    assert math.isclose(_value(r, "IYY (lb-in^2)"), 9534613, rel_tol=TOL)
    assert math.isclose(_value(r, "IZZ (lb-in^2)"), 14002901, rel_tol=TOL)
    assert math.isclose(_value(r, "IXZ (lb-in^2)"), 622634, rel_tol=TOL)


def test_principal_axes_match_manual():
    # Appendix A p136: IX(P) 1191.662, IY(P) 2058.209, IZ(P) 3032.632,
    # theta 4.198392 deg.
    r = aft_gross_result()
    assert math.isclose(_value(r, "IX(P) principal"), 1191.662, rel_tol=TOL)
    assert math.isclose(_value(r, "IY(P) principal"), 2058.209, rel_tol=TOL)
    assert math.isclose(_value(r, "IZ(P) principal"), 3032.632, rel_tol=TOL)
    assert math.isclose(_value(r, "Principal-axis angle theta"), 4.198392, rel_tol=2e-3)


def test_run_requires_items():
    raised = False
    try:
        calc.run(Project(name="no items", weight=WeightInput()))
    except ValueError:
        raised = True
    assert raised


def test_build_mass_persists_properties_and_round_trips():
    # build_mass emits the persisted Project.mass slice (R7): weight/CG/inertia in
    # lb-in^2, matching the WTONECG result and surviving the io round-trip.
    project = io.load_project(_EXAMPLE)
    mass = calc.build_mass(project)
    assert len(mass.cases) == 1
    c = mass.cases[0]
    assert c.weight_lb == 3400
    assert math.isclose(c.cg_x, 84.99936, rel_tol=TOL)
    assert math.isclose(c.iyy, 9534613, rel_tol=TOL)
    assert math.isclose(c.izz, 14002901, rel_tol=TOL)

    project.mass = mass
    rebuilt = io.project_from_dict(io.project_to_dict(project))
    assert rebuilt.mass is not None
    assert math.isclose(rebuilt.mass.cases[0].iyy, c.iyy, rel_tol=1e-9)


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
