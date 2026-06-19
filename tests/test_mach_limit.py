"""Validate MACHLIM against the FAR 23 LOADS manual, Appendix A.

The 6-place single's Mach-limit lines are printed in Appendix A p160: inputs
MC 0.323, MD 0.403, shoulder 12000 ft, max operating 18000 ft, 1000 ft steps;
outputs MNE 0.3627, MFC 0.4836 and the per-altitude Mach-limited equivalent
airspeeds, e.g. at 12000 ft V(MC) 170.16, V(MNE) 191.08, V(MD) 212.31, V(FC)
254.77, falling to V(MC) 150.77 at 18000 ft.

Per Decision 3 the figures are matched within ±0.1%; the shared
``standard_atmosphere`` uses a = 29.02436 vs the program's 29.02 (~0.01%).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import MachLimitInput, Project, StructuralSpeedsInput, io  # noqa: E402
from farloads.modules import mach_limit as calc  # noqa: E402

TOL = 1e-3  # ±0.1% relative

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "ga6_normal.project.json",
)


def results():
    project = io.load_project(_EXAMPLE)
    return calc.mach_limit_lines(project.speeds.mach_limit)


def _value(conditions, label):
    for c in conditions:
        for v in c.values:
            if v.label == label:
                return v.value
    raise KeyError(label)


def _line_at(conditions, altitude):
    for c in conditions:
        if c.title.endswith(f"{altitude:g} ft"):
            return c
    raise KeyError(altitude)


def test_mne_and_mfc():
    # MNE = 0.9*MD = 0.3627; MFC = 1.2*MD = 0.4836.
    r = results()
    assert math.isclose(_value(r, "Never-exceed Mach MNE"), 0.3627, rel_tol=TOL)
    assert math.isclose(_value(r, "Flutter-clearance Mach MFC"), 0.4836, rel_tol=TOL)


def test_line_at_shoulder_altitude():
    # 12000 ft: V(MC) 170.16, V(MNE) 191.08, V(MD) 212.31, V(FC) 254.77.
    line = _line_at(results(), 12000)
    assert math.isclose(_value([line], "V(MC)"), 170.16, rel_tol=TOL)
    assert math.isclose(_value([line], "V(MNE)"), 191.08, rel_tol=TOL)
    assert math.isclose(_value([line], "V(MD)"), 212.31, rel_tol=TOL)
    assert math.isclose(_value([line], "V(FC)"), 254.77, rel_tol=TOL)


def test_line_at_max_altitude():
    # 18000 ft: V(MC) 150.77, V(MD) 188.11.
    line = _line_at(results(), 18000)
    assert math.isclose(_value([line], "V(MC)"), 150.77, rel_tol=TOL)
    assert math.isclose(_value([line], "V(MD)"), 188.11, rel_tol=TOL)


def test_altitude_rows_span_shoulder_to_max():
    # Shoulder (12000) through max (18000) in 1000 ft steps => 7 altitude lines.
    lines = [c for c in results() if c.title.startswith("Mach limit line")]
    assert len(lines) == 7
    assert lines[0].title.endswith("12000 ft")
    assert lines[-1].title.endswith("18000 ft")


def test_vfc_is_120_percent_of_vmd():
    # V(FC) = 1.2 * V(MD) at every altitude (MFC = 1.2*MD).
    line = _line_at(results(), 15000)
    assert math.isclose(_value([line], "V(FC)"), 1.2 * _value([line], "V(MD)"), rel_tol=1e-9)


def test_run_requires_mach_limit_inputs():
    raised = False
    try:
        calc.run(Project(name="no speeds"))
    except ValueError:
        raised = True
    assert raised
    raised = False
    try:
        calc.run(Project(name="no mach", speeds=StructuralSpeedsInput()))
    except ValueError:
        raised = True
    assert raised


def test_above_tropopause_uses_constant_speed_of_sound():
    # Above 35332 ft the speed of sound is constant (~575 kt); two high altitudes
    # share the same a, so V scales only with sqrt(sigma).
    inp = MachLimitInput(mc=0.5, md=0.6, shoulder_altitude_ft=36000,
                         max_operating_altitude_ft=40000, increment_ft=2000)
    r = calc.mach_limit_lines(inp)
    lines = [c for c in r if c.title.startswith("Mach limit line")]
    assert len(lines) == 3  # 36000, 38000, 40000
    # V(MD) decreases monotonically with altitude (sigma falls).
    vmd = [_value([line], "V(MD)") for line in lines]
    assert vmd[0] > vmd[1] > vmd[2]


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
