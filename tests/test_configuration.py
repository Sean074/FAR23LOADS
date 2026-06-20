"""Tests for the configuration & layout module (modern addition, no oracle).

There is no manual regression oracle for this page, so the checks are:

1. **Internal consistency** -- the MAC/XLEMAC/Y_MAC the module reports (obtained by
   running the generated polylines through the WINGGEOM strip integrator) match the
   closed-form trapezoidal-wing relations to ±0.1%. This proves both the planform
   derivation and that the generated polylines feed WINGGEOM correctly.
2. **Appendix A sanity** -- a trapezoid approximating the Appendix A wing
   (area/side 13257 in², AR 6.095, p141) lands in the right neighbourhood of the
   manual MAC (69.246) / XLEMAC (63.641). The real Appendix A wing has an inboard
   strake, so this is a plausibility band (±10%), not an exact oracle.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import LayoutInput, Project  # noqa: E402
from farloads.modules.configuration import (  # noqa: E402
    configuration_properties,
    wing_planform,
)


def _values(project):
    """Flatten all (label -> value) pairs from the module result."""
    out = {}
    for cond in configuration_properties(project):
        for v in cond.values:
            out[v.label] = v.value
    return out


def _trapezoid(area_ft2=174.0, ar=6.0, taper=0.5, sweep_deg=3.0, le_root_x=45.0):
    return LayoutInput(
        wing_area_sqft=area_ft2, aspect_ratio=ar, taper_ratio=taper,
        le_sweep_deg=sweep_deg, le_root_x=le_root_x,
    )


def test_mac_matches_closed_form():
    layout = _trapezoid()
    span, c_root, c_tip, semi = wing_planform(layout)
    taper = layout.taper_ratio
    mac_cf = (2.0 / 3.0) * c_root * (1 + taper + taper**2) / (1 + taper)
    ymac_cf = (semi / 3.0) * (1 + 2 * taper) / (1 + taper)
    xlemac_cf = layout.le_root_x + ymac_cf * math.tan(math.radians(layout.le_sweep_deg))

    vals = _values(Project(name="t", configuration=layout))
    assert math.isclose(vals["MAC"], mac_cf, rel_tol=1e-3)
    assert math.isclose(vals["YLE(MAC) butt line of MAC"], ymac_cf, rel_tol=1e-3)
    assert math.isclose(vals["XLE(MAC) station of MAC LE"], xlemac_cf, rel_tol=1e-3)


def test_area_aspect_ratio_recovered():
    # The generated planform must round-trip back to the input S and AR (WINGGEOM).
    layout = _trapezoid(area_ft2=200.0, ar=8.0, taper=0.4)
    vals = _values(Project(name="t", configuration=layout))
    assert math.isclose(vals["Aspect ratio"], 8.0, rel_tol=1e-3)
    span = vals["Span"]
    assert math.isclose(span, math.sqrt(8.0 * 200.0) * 12.0, rel_tol=1e-3)


def test_appendix_a_sanity():
    # Appendix A wing: area/side 13257 in^2 -> total 184.1 ft^2; AR 6.095; root
    # chord 101 in / tip 44 in -> taper ~0.436 (p141). The strake makes this only a
    # plausibility band against the manual MAC 69.246 and MAC butt line 87.854.
    # (XLEMAC's absolute station depends on the real, strake-swept LE shape, which a
    # pure trapezoid cannot reproduce, so it is not asserted here.)
    layout = LayoutInput(
        wing_area_sqft=2 * 13257 / 144.0, aspect_ratio=6.095, taper_ratio=44.0 / 101.0,
        le_sweep_deg=4.0, le_root_x=45.0,
    )
    vals = _values(Project(name="appA", configuration=layout))
    assert math.isclose(vals["MAC"], 69.246, rel_tol=0.10)
    assert math.isclose(vals["YLE(MAC) butt line of MAC"], 87.854, rel_tol=0.10)


def test_stability_and_gear_present_when_data_given():
    layout = _trapezoid()
    layout.h_tail_area = 30.0
    layout.h_tail_arm = 180.0
    layout.nose_gear_x = 20.0
    layout.main_gear_x = 115.0
    layout.track = 90.0
    layout.gear_height = 35.0
    layout.root_waterline_z = 40.0
    vals = _values(Project(name="t", configuration=layout))
    assert vals["Horizontal tail volume V_H"] > 0
    assert "Neutral point (%MAC)" in vals
    assert "Tip-back angle" in vals
    assert "Overturn (turnover) angle" in vals


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
