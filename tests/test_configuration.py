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

from farloads import LayoutInput, MassCase, MassResult, Project  # noqa: E402
from farloads.modules.configuration import (  # noqa: E402
    cg_estimate,
    component_stations,
    configuration_properties,
    match_component_station,
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


def _gear_layout():
    layout = _trapezoid()
    layout.nose_gear_x = 20.0
    layout.main_gear_x = 115.0
    layout.track = 90.0
    layout.gear_height = 35.0
    layout.root_waterline_z = 40.0
    return layout


def test_cg_estimate_falls_back_to_quarter_mac_without_mass():
    # Step D4.5: no Project.mass -> the pre-D4.5 25%-MAC / wing-waterline first cut.
    layout = _gear_layout()
    project = Project(name="t", configuration=layout)
    geom = _values(project)
    x_cg, z_cg, source = cg_estimate(project, layout, geom)
    assert math.isclose(x_cg, geom["XLE(MAC) station of MAC LE"] + 0.25 * geom["MAC"])
    assert z_cg == layout.root_waterline_z
    assert source == "25% MAC estimate"


def test_cg_estimate_uses_mass_when_present():
    # Step D4.5: Project.mass (WTONECG's itemized loading) is the true CG.
    layout = _gear_layout()
    mass = MassResult(cases=[MassCase(name="itemized loading", weight_lb=2000.0, cg_x=123.4, cg_z=56.7)])
    project = Project(name="t", configuration=layout, mass=mass)
    geom = _values(project)
    x_cg, z_cg, source = cg_estimate(project, layout, geom)
    assert (x_cg, z_cg, source) == (123.4, 56.7, "Weight DB")


def test_gear_condition_label_reflects_cg_source():
    layout = _gear_layout()
    mass = MassResult(cases=[MassCase(name="itemized loading", weight_lb=2000.0, cg_x=123.4, cg_z=56.7)])
    with_mass = _values(Project(name="t", configuration=layout, mass=mass))
    without_mass = _values(Project(name="t", configuration=layout))
    assert "CG station (Weight DB)" in with_mass
    assert "CG station (25% MAC estimate)" in without_mass
    assert with_mass["CG station (Weight DB)"] == 123.4


def _full_layout():
    return LayoutInput(
        fuselage_length=300.0, fuselage_width=48.0, fuselage_height=60.0, datum_x=0.0,
        wing_area_sqft=174.0, aspect_ratio=6.0, taper_ratio=0.6,
        le_sweep_deg=2.0, le_root_x=90.0, root_waterline_z=40.0,
        h_tail_area=30.0, h_tail_arm=180.0, v_tail_area=18.0, v_tail_arm=175.0,
        nose_gear_x=30.0, main_gear_x=150.0, track=90.0, gear_height=35.0,
    )


def test_component_stations_wing_and_fuselage():
    # Step D4.3: approximate stations derived from LayoutInput's coarse scalars.
    layout = _full_layout()
    stations = component_stations(layout)
    wing_x, wing_y, wing_z = stations["wing"]
    assert layout.le_root_x < wing_x < layout.le_root_x + 60.0   # inside the root chord
    assert wing_y == 0.0 and wing_z == layout.root_waterline_z
    assert stations["fuselage"] == (150.0, 0.0, 40.0)   # datum + length/2


def test_component_stations_tail_arms_and_lumped_average():
    layout = _full_layout()
    stations = component_stations(layout)
    wing_x = stations["wing"][0]
    assert math.isclose(stations["h_tail"][0], wing_x + 180.0)
    assert math.isclose(stations["v_tail"][0], wing_x + 175.0)
    # Area-weighted average (h_tail_area=30, v_tail_area=18) sits between the two,
    # closer to h_tail (the larger surface).
    tail_x = stations["tail"][0]
    assert stations["v_tail"][0] < tail_x < stations["h_tail"][0]
    expected = (30.0 * stations["h_tail"][0] + 18.0 * stations["v_tail"][0]) / 48.0
    assert math.isclose(tail_x, expected)


def test_component_stations_gear_and_lumped_average():
    layout = _full_layout()
    stations = component_stations(layout)
    gear_z = layout.root_waterline_z - layout.gear_height / 2.0
    assert stations["main_gear"] == (150.0, 0.0, gear_z)
    assert stations["nose_gear"] == (30.0, 0.0, gear_z)
    # Weight-weighted ~3:1 main:nose average for a single lumped "Landing gear" item.
    assert math.isclose(stations["landing_gear"][0], (3.0 * 150.0 + 1.0 * 30.0) / 4.0)
    assert math.isclose(stations["landing_gear"][2], gear_z)


def test_component_stations_omits_ungiven_components():
    # A bare wing-only layout must not fabricate tail/gear/fuselage stations.
    layout = LayoutInput(wing_area_sqft=174.0, aspect_ratio=6.0, le_root_x=90.0)
    stations = component_stations(layout)
    assert set(stations) == {"wing"}


def test_match_component_station_prefers_specific_over_lumped():
    layout = _full_layout()
    stations = component_stations(layout)
    assert match_component_station("Wing", stations) == stations["wing"]
    assert match_component_station("Fuselage", stations) == stations["fuselage"]
    assert match_component_station("Horizontal tail", stations) == stations["h_tail"]
    assert match_component_station("Vertical tail", stations) == stations["v_tail"]
    # WTESTIMA's single lumped "Tail" item -- must not accidentally match h_tail/v_tail.
    assert match_component_station("Tail", stations) == stations["tail"]
    assert match_component_station("Landing gear", stations) == stations["landing_gear"]
    assert match_component_station("Nacelle", stations) is None


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
