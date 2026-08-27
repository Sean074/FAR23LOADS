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

from sloads import (
    EmpennageInput,
    GeometryInput,
    LandingGearGeometry,
    LandingGearInput,
    LayoutInput,
    MassCase,
    MassResult,
    Project,
    TailLoadsInput,
    TailType,
    VTailLoadsInput,
)


def _gear_geom(main_x, nose_x, track=90.0, static_z=10.0, rr=5.0):
    """Step G6b single-source gear geometry: static axle Z and rolling radius chosen
    so the ground line (static Z - rr) is 5 in, i.e. gear_height = root waterline - 5."""
    return LandingGearGeometry(
        main_gear=LandingGearInput(axle_static=(main_x, static_z), rolling_radius_in=rr),
        nose_gear=LandingGearInput(axle_static=(nose_x, static_z), rolling_radius_in=rr),
        tread_in=track,
    )


def _emp(h_area=30.0, h_semispan=60.0, v_area=18.0, v_span=48.0,
         xt25=270.0, xv25=265.0, e_aft=0.0, r_aft=0.0):
    """Step G6: a single-source empennage (htail/vtail) for the three-view /
    stability / component-station tests -- the analysis-native area/span/station."""
    return EmpennageInput(
        htail=TailLoadsInput(htail_area_sqft=h_area, htail_semispan_in=h_semispan,
                             xt25=xt25, elevator_aft_hinge_sqft=e_aft),
        vtail=VTailLoadsInput(vtail_area_sqft=v_area, vtail_span_in=v_span,
                              xv25=xv25, rudder_aft_hinge_sqft=r_aft),
    )
from helpers import values_by_key  # noqa: E402

from sloads.modules.configuration import (  # noqa: E402
    cg_estimate,
    component_stations,
    configuration_properties,
    match_component_station,
    tail_planform,
    wing_planform,
)


def _props(project):
    """Every configuration property as ``{label: value}`` (the module's flat table)."""
    return values_by_key(configuration_properties(project))


def _labels(project):
    """Every configuration property label (the display text, not the key)."""
    return {v.label for c in configuration_properties(project) for v in c.values}


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

    vals = _props(Project(name="t", geometry=GeometryInput(parametric=layout)))
    assert math.isclose(vals["mac"], mac_cf, rel_tol=1e-3)
    assert math.isclose(vals["yle_mac_butt_line_of_mac"], ymac_cf, rel_tol=1e-3)
    assert math.isclose(vals["xle_mac_station_of_mac_le"], xlemac_cf, rel_tol=1e-3)


def test_area_aspect_ratio_recovered():
    # The generated planform must round-trip back to the input S and AR (WINGGEOM).
    layout = _trapezoid(area_ft2=200.0, ar=8.0, taper=0.4)
    vals = _props(Project(name="t", geometry=GeometryInput(parametric=layout)))
    assert math.isclose(vals["aspect_ratio"], 8.0, rel_tol=1e-3)
    span = vals["span"]
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
    vals = _props(Project(name="appA", geometry=GeometryInput(parametric=layout)))
    assert math.isclose(vals["mac"], 69.246, rel_tol=0.10)
    assert math.isclose(vals["yle_mac_butt_line_of_mac"], 87.854, rel_tol=0.10)


def test_stability_and_gear_present_when_data_given():
    layout = _trapezoid()
    layout.root_waterline_z = 40.0
    # Step G6: h-tail area + 25%-MAC station (xt25 well aft -> positive derived arm).
    emp = EmpennageInput(htail=TailLoadsInput(htail_area_sqft=30.0, xt25=250.0))
    vals = _props(Project(name="t", geometry=GeometryInput(
        parametric=layout, empennage=emp, landing_gear=_gear_geom(115.0, 20.0))))
    assert vals["horizontal_tail_volume_v_h"] > 0
    assert "neutral_point_pct_mac" in vals
    assert "tip_back_angle" in vals
    assert "overturn_turnover_angle" in vals


def _gear_layout():
    layout = _trapezoid()
    layout.root_waterline_z = 40.0
    return layout


def _gear_project(layout, **kw):
    return Project(name="t", geometry=GeometryInput(
        parametric=layout, landing_gear=_gear_geom(115.0, 20.0)), **kw)


def test_cg_estimate_falls_back_to_quarter_mac_without_mass():
    # Step D4.5: no Project.mass -> the pre-D4.5 25%-MAC / wing-waterline first cut.
    layout = _gear_layout()
    project = Project(name="t", geometry=GeometryInput(parametric=layout))
    geom = _props(project)
    x_cg, z_cg, source = cg_estimate(project, layout, geom["mac"],
                                     geom["xle_mac_station_of_mac_le"])
    assert math.isclose(x_cg, geom["xle_mac_station_of_mac_le"] + 0.25 * geom["mac"])
    assert z_cg == layout.root_waterline_z
    assert source == "25% MAC estimate"


def test_cg_estimate_uses_mass_when_present():
    # Step D4.5: Project.mass (WTONECG's itemized loading) is the true CG.
    layout = _gear_layout()
    mass = MassResult(cases=[MassCase(name="itemized loading", weight_lb=2000.0, cg_x=123.4, cg_z=56.7)])
    project = Project(name="t", geometry=GeometryInput(parametric=layout), mass=mass)
    geom = _props(project)
    x_cg, z_cg, source = cg_estimate(project, layout, geom["mac"],
                                     geom["xle_mac_station_of_mac_le"])
    assert (x_cg, z_cg, source) == (123.4, 56.7, "Weight DB")


def test_gear_condition_label_reflects_cg_source():
    layout = _gear_layout()
    mass = MassResult(cases=[MassCase(name="itemized loading", weight_lb=2000.0, cg_x=123.4, cg_z=56.7)])
    # The CG source rides in the *label* (display text); the key is stable (M4-9).
    with_mass = _labels(_gear_project(layout, mass=mass))
    without_mass = _labels(_gear_project(layout))
    assert "CG station (Weight DB)" in with_mass
    assert "CG station (25% MAC estimate)" in without_mass
    assert _props(_gear_project(layout, mass=mass))["cg_station"] == 123.4


def _full_layout():
    return LayoutInput(
        fuselage_length=300.0, fuselage_width=48.0, fuselage_height=60.0, datum_x=0.0,
        wing_area_sqft=174.0, aspect_ratio=6.0, taper_ratio=0.6,
        le_sweep_deg=2.0, le_root_x=90.0, root_waterline_z=40.0,
    )


def test_component_stations_wing_and_fuselage():
    # Step D4.3: approximate stations derived from LayoutInput's coarse scalars.
    layout = _full_layout()
    stations = component_stations(layout)
    wing_x, wing_y, wing_z = stations["wing"]
    assert layout.le_root_x < wing_x < layout.le_root_x + 60.0   # inside the root chord
    assert wing_y == 0.0 and wing_z == layout.root_waterline_z
    assert stations["fuselage"] == (150.0, 0.0, 40.0)   # datum + length/2


def test_component_stations_tail_stations_and_lumped_average():
    # Step G6: the h-/v-tail stations are the empennage 25%-MAC stations xt25/xv25.
    layout = _full_layout()
    stations = component_stations(layout, _emp(h_area=30.0, v_area=18.0, xt25=270.0, xv25=265.0))
    assert math.isclose(stations["h_tail"][0], 270.0)
    assert math.isclose(stations["v_tail"][0], 265.0)
    # Area-weighted average (h_area=30, v_area=18) sits between the two, closer to h.
    tail_x = stations["tail"][0]
    assert stations["v_tail"][0] < tail_x < stations["h_tail"][0]
    expected = (30.0 * 270.0 + 18.0 * 265.0) / 48.0
    assert math.isclose(tail_x, expected)


def test_component_stations_gear_and_lumped_average():
    # Step G6b: gear stations from the single-source axle geometry. _gear_geom puts the
    # ground line at WL 5, so gear_height = 40 - 5 = 35 and strut mid-height = 40 - 35/2.
    layout = _full_layout()
    stations = component_stations(layout, None, _gear_geom(150.0, 30.0))
    gear_z = layout.root_waterline_z - 35.0 / 2.0
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


def _tail_layout(tail_type=TailType.CONVENTIONAL, **overrides):
    kwargs = dict(
        fuselage_length=300.0, fuselage_width=48.0, fuselage_height=60.0, datum_x=0.0,
        wing_area_sqft=174.0, aspect_ratio=6.0, taper_ratio=0.6,
        le_sweep_deg=2.0, le_root_x=90.0, root_waterline_z=40.0,
        tail_type=tail_type,
    )
    kwargs.update(overrides)
    return LayoutInput(**kwargs)


# h-tail semi-span 60 (span 120 = 10 ft), v-tail span 48 (4 ft) -- Step G6 empennage.
def _tail_e(**overrides):
    return _emp(h_semispan=60.0, v_span=48.0, **overrides)


def test_tail_planform_empty_when_no_empennage():
    # No empennage geometry -> nothing drawn (backward-compatible).
    layout = _full_layout()
    assert layout.tail_type == TailType.CONVENTIONAL
    assert tail_planform(layout, None) == {}


def test_tail_planform_conventional_draws_h_and_v_tail_near_fuselage():
    layout = _tail_layout(TailType.CONVENTIONAL)
    panels = tail_planform(layout, _tail_e())
    assert set(panels) == {"h_tail", "v_tail"}
    fin_root_z = layout.root_waterline_z + layout.fuselage_height / 2.0
    # No explicit h_tail_z -> conventional tail sits at the fuselage waterline.
    h_z = panels["h_tail"]["side"][0][1]
    assert math.isclose(h_z, layout.root_waterline_z)
    v_z0 = panels["v_tail"]["side"][0][1]
    assert math.isclose(v_z0, fin_root_z)


def test_tail_planform_draws_elevator_and_rudder_when_hinge_areas_set():
    # Step G6: the elevator/rudder are drawn as the aft Saft/S chord band.
    layout = _tail_layout(TailType.CONVENTIONAL)
    panels = tail_planform(layout, _tail_e(e_aft=12.0, r_aft=6.0))
    assert "elevator" in panels and "rudder" in panels
    # Elevator band is aft of the h-tail LE (hinge -> TE).
    x_le = panels["h_tail"]["top"][0][0]
    x_hinge = panels["elevator"]["top"][0][0]
    assert x_hinge > x_le


def test_tail_planform_t_tail_places_h_tail_atop_fin():
    layout = _tail_layout(TailType.T_TAIL)
    panels = tail_planform(layout, _tail_e())
    fin_root_z = layout.root_waterline_z + layout.fuselage_height / 2.0
    v_span_in = 48.0
    h_z = panels["h_tail"]["side"][0][1]
    assert math.isclose(h_z, fin_root_z + v_span_in)


def test_tail_planform_t_tail_respects_explicit_h_tail_z():
    layout = _tail_layout(TailType.T_TAIL, h_tail_z=25.0)
    panels = tail_planform(layout, _tail_e())
    h_z = panels["h_tail"]["side"][0][1]
    assert math.isclose(h_z, layout.root_waterline_z + 25.0)


def test_tail_planform_cruciform_places_h_tail_mid_fin():
    layout = _tail_layout(TailType.CRUCIFORM)
    panels = tail_planform(layout, _tail_e())
    fin_root_z = layout.root_waterline_z + layout.fuselage_height / 2.0
    v_span_in = 48.0
    h_z = panels["h_tail"]["side"][0][1]
    assert math.isclose(h_z, fin_root_z + v_span_in * 0.5)


def test_tail_planform_v_tail_draws_two_diagonal_panels_not_h_v():
    layout = _tail_layout(TailType.V_TAIL)
    panels = tail_planform(layout, _tail_e())
    assert set(panels) == {"v_tail_left", "v_tail_right"}
    left_y = panels["v_tail_left"]["front"][1][0]
    right_y = panels["v_tail_right"]["front"][1][0]
    assert left_y < 0 < right_y
    assert math.isclose(left_y, -right_y)


def test_default_fuselage_outline_from_scalars():
    # Step G1: a body outline is defaulted from the coarse length/width/height
    # scalars -- nose point, max section at 0.35L, tapered tail cone.
    from sloads import default_fuselage_outline
    layout = LayoutInput(fuselage_length=300.0, fuselage_width=48.0,
                         fuselage_height=54.0, datum_x=10.0)
    outline = default_fuselage_outline(layout)
    assert outline is not None
    xs = [s.x for s in outline.sections]
    assert xs[0] == 10.0                        # nose at the datum
    assert math.isclose(xs[1], 10.0 + 0.35 * 300.0)
    assert math.isclose(xs[2], 10.0 + 300.0)    # tail
    assert outline.sections[1].width == 48.0 and outline.sections[1].height == 54.0
    assert outline.sections[0].width == 0.0     # pointed nose


def test_default_fuselage_outline_none_without_length():
    # No fuselage length -> no outline (draw nothing, as before the outline existed).
    from sloads import default_fuselage_outline
    assert default_fuselage_outline(LayoutInput()) is None


def test_match_component_station_prefers_specific_over_lumped():
    layout = _full_layout()
    stations = component_stations(layout, _emp(xt25=270.0, xv25=265.0), _gear_geom(150.0, 30.0))
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
