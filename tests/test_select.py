"""Critical wing-load selection (Step C6): SELECT.BAS port.

The FAR23 path is oracle-locked against the Appendix A "Critical Wing Loads"
summary in the 6-place loads report. SELECT searches the balanced V-n matrix
(FLTLOADS, cruise, CGs 1-4, altitudes 0 / 12000 / 18000 ft) for the governing
wing condition of each design point:

    CASE  ANGLE   CL       V KEAS   CG    ALT     COND       FAR
     22   PHAA    +1.519   117.40   CG2      0    STALL +N   23.333(b)
    145   PLAA    +0.472   212.40   CG2  12000    MAN D      23.333(b)
    150   PMAA    +0.810   170.00   CG2  12000    GUST +C    23.333(c)or(b)
    173   NMAA    -0.433   170.00   CG3  12000    GUST -C    23.333(c)or(b)
    160   ACRL    +1.328   116.00   CG2  12000    AC ROLL    23.349(a)(2)
    138   TORS    +0.470   170.00   CG1  12000    ST ROL C   23.349(b)

(The 6-place loads report uses full-down aileron = 15 deg and basic-airfoil
cm = -0.03 for the steady-roll torsion search.) Our renumbered envelope assigns
different integer case numbers, so the regression asserts the selected
*condition*, CL and V (the V-n oracle) -- not the manual's case index.

Reference: SELECT.BAS (Appendix C, lines ~2990-3540), Ref 1 Ch 9; Appendix A
loads report "Critical Wing Loads".
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, SelectInput, TailLoadsInput, VTailLoadsInput, io  # noqa: E402
from farloads.modules import select  # noqa: E402
from farloads.modules.flight_envelope import build_envelope  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _ga6_three_altitudes() -> Project:
    """The 6-place GA project with the Appendix A altitude set (0/12000/18000 ft)
    and the loads-report steady-roll inputs."""
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.select_input = SelectInput(full_down_aileron_deg=15.0, basic_airfoil_cm=-0.03)
    return p


# Appendix A "General input for calculation of horiz tail loads" (6-place report).
_TAIL = TailLoadsInput(
    tail_incidence_deg=2.0, wing_zero_lift_cruise_deg=3.988146,
    aspect_ratio_wing=6.095, aspect_ratio_htail=4.017, htail_area_sqft=36.944,
    elevator_effectiveness=0.614, xt25=261.027, xt50=270.357,
    elevator_te_up_deg=30.0, elevator_te_down_deg=20.0, elevator_area_sqft=16.403,
    elevator_fwd_hinge_sqft=1.639, elevator_aft_hinge_sqft=14.792,
    airplane_length_ft=26.522, wing_lift_slope_per_rad=4.605,
)


# Appendix A "Input for vertical tail" (6-place report).
_VTAIL = VTailLoadsInput(
    rudder_deflection_deg=30.0, vtail_area_sqft=14.84, rudder_area_sqft=5.236,
    rudder_fwd_hinge_sqft=0.57, rudder_aft_hinge_sqft=4.63, aspect_ratio_vtail=1.52,
    vtail_mac_ft=3.367, xv25=266.83, airplane_length_ft=26.522, wing_span_ft=33.5,
    gross_weight_lb=3400.0,
)


def _by_label(project: Project):
    # The wing-condition view (used by the wing-focused tests).
    cls = select.build_critical(project)
    by_label = {c.label: c for c in cls.conditions if c.component == "wing"}
    vn = {v.case: v for v in build_envelope(project).vn}
    return by_label, vn


def _vals(cond):
    return {lv.label: lv.value for lv in cond.loads}


def test_critical_wing_conditions_match_appendix_a():
    p = _ga6_three_altitudes()
    by_label, vn = _by_label(p)
    # (label, source V-n condition, CL, V KEAS) from the Appendix A summary.
    expect = [
        ("PHAA", "STALL +N", 1.519, 117.40),
        ("PLAA", "MAN D", 0.472, 212.40),
        ("PMAA", "GUST +C", 0.810, 170.00),
        ("NMAA", "GUST -C", -0.433, 170.00),
        ("ACRL", "AC ROLL", 1.328, 116.00),
        ("TORS", "ST ROL C", 0.470, 170.00),
    ]
    assert set(by_label) == {lbl for lbl, *_ in expect}
    for label, cond_name, cl, v in expect:
        c = by_label[label]
        assert vn[c.case].condition == cond_name, (label, vn[c.case].condition)
        vals = _vals(c)
        # SELECT carries the CL/V the FLTLOADS balance produced; the AoA iteration
        # converges NZ only to +-0.005 (flight_envelope.py), so the selected CL
        # inherits ~0.5% noise -- the FLTLOADS oracle tolerance, not 0.1%.
        assert math.isclose(vals["CL"], cl, rel_tol=5e-3, abs_tol=3e-3), (label, vals["CL"], cl)
        assert math.isclose(vals["V (EAS)"], v, rel_tol=2e-3), (label, vals["V (EAS)"], v)


def test_phaa_is_positive_high_aoa_at_limit_n():
    # PHAA is the positive-high-angle-of-attack stall corner at the limit load
    # factor (Appendix A: NZ +3.8).
    p = _ga6_three_altitudes()
    by_label, _ = _by_label(p)
    assert math.isclose(_vals(by_label["PHAA"])["Load factor NZ"], 3.80, abs_tol=0.01)
    assert _vals(by_label["NMAA"])["Load factor NZ"] < 0      # down load
    assert _vals(by_label["PMAA"])["CL"] > 0


def test_select_far23_far_references():
    p = _ga6_three_altitudes()
    by_label, _ = _by_label(p)
    assert by_label["PHAA"].far_reference == "23.333(b)"
    assert by_label["ACRL"].far_reference == "23.349(a)(2)"
    assert by_label["TORS"].far_reference == "23.349(b)"
    assert all(c.component == "wing" for c in by_label.values())


def test_run_returns_module_result():
    p = _ga6_three_altitudes()
    result = select.run(p)
    assert result.module == "select"
    assert len(result.conditions) >= 6   # 6 wing + 4 fuselage (no tail_loads)
    assert result.conditions[0].far_reference  # FAR cite rendered


def test_critical_set_round_trips_through_io():
    p = _ga6_three_altitudes()
    p.envelope = build_envelope(p)
    p.envelope.critical = select.build_critical(p)
    rebuilt = io.project_from_dict(io.project_to_dict(p))
    assert rebuilt.envelope.critical is not None
    labels = {c.label for c in rebuilt.envelope.critical.conditions}
    assert {"PHAA", "PLAA", "PMAA", "NMAA", "ACRL", "TORS"} <= labels


def test_select_uses_persisted_envelope_when_present():
    # When Project.envelope is already populated, SELECT searches it directly
    # rather than rebuilding from flight_loads.
    p = _ga6_three_altitudes()
    p.envelope = build_envelope(p)
    p.flight_loads = None  # force the persisted-envelope path
    cls = select.build_critical(p)
    assert len(cls.conditions) == 6


def test_rational_balancing_tail_load_hand_calc():
    # Ch 9 "Hand Calculation of Rational Balanced Tail Load" (case 202): the
    # STALL +N / CG1 / 18000 ft point resolves to LT25 +907.62, camber LT50
    # -387.78, elevator deflection -5.39 deg, total LT 519.845, CP 6.35% tail MAC.
    # Our envelope inherits FLTLOADS' +-0.005-NZ noise, so ~0.2% here.
    p = _ga6_three_altitudes()
    fl = p.flight_loads
    cg1 = next(c for c in fl.cg_cases if c.name == "CG1")
    pt = next(v for v in build_envelope(p).vn
              if v.condition == "STALL +N" and v.cg == "CG1" and v.altitude_ft == 18000)
    b = select.htail_balance(pt, cg1, fl.xw, fl.zw, _TAIL)
    assert math.isclose(b["LT25"], 907.62, rel_tol=3e-3), b["LT25"]
    assert math.isclose(b["LT50"], -387.78, rel_tol=5e-3), b["LT50"]
    assert math.isclose(b["AT"], 7.747, abs_tol=0.05), b["AT"]   # alpha carries FLTLOADS noise
    assert math.isclose(b["DELTA"], -5.39, abs_tol=0.03), b["DELTA"]
    assert math.isclose(b["LT"], 519.845, rel_tol=3e-3), b["LT"]
    assert math.isclose(b["CP"], 6.35, abs_tol=0.1), b["CP"]


def test_critical_htail_balancing_match_appendix_a():
    # Appendix A "Critical Horizontal Tail Loads": UP balancing flaps retracted is
    # case 202 STALL +N CG1 18000 (LT +519.85); DOWN is case 165 MAN D CG3 12000
    # (LT -613.92). (Flaps-extended balancing needs the flapped envelope, not built.)
    p = _ga6_three_altitudes()
    p.tail_loads = _TAIL
    cls = select.build_critical(p)
    htail = {c.label: c for c in cls.conditions if c.component == "htail"}
    vn = {v.case: v for v in build_envelope(p).vn}
    assert {"BAL UP RETRACTED", "BAL DN RETRACTED"} <= set(htail)

    up = htail["BAL UP RETRACTED"]
    assert vn[up.case].condition == "STALL +N" and vn[up.case].cg == "CG1"
    assert math.isclose(_vals(up)["Total tail load"], 519.85, rel_tol=5e-3)

    dn = htail["BAL DN RETRACTED"]
    assert vn[dn.case].condition == "MAN D" and vn[dn.case].cg == "CG3"
    assert math.isclose(_vals(dn)["Total tail load"], -613.92, rel_tol=5e-3)
    assert up.far_reference == "23.421" and dn.far_reference == "23.421"


def test_htail_maneuver_loads_match_appendix_a():
    # Appendix A "Critical Horizontal Tail Loads" (maneuver, flaps retracted):
    # unchecked down -1397.8 (case 274), unchecked up +1227.2 (34), checked down
    # -671.5 (56), checked up +787.8 (204). Values carry FLTLOADS ~0.3% V-n noise;
    # the deflection increments and pitch inertia are exact.
    p = _ga6_three_altitudes()
    p.tail_loads = _TAIL
    h = {c.label: c for c in select.build_critical(p).conditions if c.component == "htail"}
    assert math.isclose(_vals(h["UNCHECKED MAN DN"])["Total tail load"], -1397.8, rel_tol=5e-3)
    assert math.isclose(_vals(h["UNCHECKED MAN DN"])["Elevator-deflection increment (cp 50%)"],
                        -1346.5, rel_tol=3e-3)
    assert math.isclose(_vals(h["UNCHECKED MAN UP"])["Total tail load"], 1227.2, rel_tol=5e-3)
    assert math.isclose(_vals(h["CHECKED MAN DN"])["Total tail load"], -671.5, rel_tol=5e-3)
    assert math.isclose(_vals(h["CHECKED MAN DN"])["Pitch inertia Iyy"], 2242.8, rel_tol=2e-3)
    assert math.isclose(_vals(h["CHECKED MAN UP"])["Total tail load"], 787.8, rel_tol=5e-3)


def test_htail_gust_and_unsymmetrical_match_appendix_a():
    # Up gust +908.6, down gust -1292.8 (flaps retracted, 23.425(a)(1));
    # unsymmetrical total -1111.8 (RH -646.4, LH -465.4, 72% on the other side).
    p = _ga6_three_altitudes()
    p.tail_loads = _TAIL
    h = {c.label: c for c in select.build_critical(p).conditions if c.component == "htail"}
    assert math.isclose(_vals(h["GUST UP RETRACTED"])["Total tail load"], 908.6, rel_tol=5e-3)
    assert math.isclose(_vals(h["GUST UP RETRACTED"])["Gust increment (cp 25%)"], 1017.0, rel_tol=3e-3)
    assert math.isclose(_vals(h["GUST DN RETRACTED"])["Total tail load"], -1292.8, rel_tol=5e-3)

    u = _vals(h["UNSYMMETRICAL"])
    assert math.isclose(u["Total tail load"], -1111.8, rel_tol=5e-3)
    assert math.isclose(u["RH side load"], -646.4, rel_tol=5e-3)
    assert math.isclose(u["LH side load"], -465.4, rel_tol=5e-3)
    assert math.isclose(u["Other-side percent"], 72.0, abs_tol=0.1)


def test_ef_large_deflection_chart():
    # SELECT.BAS subr 10000 reproduces the back-solved oracle factors.
    assert math.isclose(select._ef(30.0, 16.403 / 36.944), 0.5419, abs_tol=2e-3)
    assert math.isclose(select._ef(20.0, 16.403 / 36.944), 0.7011, abs_tol=2e-3)
    assert select._ef(0.0, 0.0) == 1.0


def _ga6_with_landing():
    # GA6 + a synthetic LANDING config (flaps extended). The real landing aero
    # polynomials are not in the repo, so the flaps-extended tail loads are
    # validated by closure (balancing tail balances the flapped condition), not the
    # printed flaps-extended oracle (Appendix A cases 81/106/88/108).
    import copy

    p = _ga6_three_altitudes()
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    cruise = p.flight_loads.configurations[0]
    landing = copy.deepcopy(cruise)
    landing.name, landing.flaps_down = "LANDING", True
    landing.stall_cl, landing.neg_stall_cl = 1.9, -0.8
    p.flight_loads.configurations = [cruise, landing]
    p.tail_loads = _TAIL
    return p


def test_htail_flaps_extended_balancing_and_gust_present():
    # Step C6 R4: with the flapped envelope, SELECT adds the flaps-extended
    # balancing (23.421) and gust (23.425(a)(2)) tail loads.
    p = _ga6_with_landing()
    h = {c.label: c for c in select.build_critical(p).conditions if c.component == "htail"}
    assert {"BAL UP EXTENDED", "BAL DN EXTENDED",
            "GUST UP EXTENDED", "GUST DN EXTENDED"} <= set(h)
    # The flaps-extended balancing references a LANDING-config V-n point.
    vn = {v.case: v for v in build_envelope(p).vn}
    assert vn[h["BAL UP EXTENDED"].case].config == "LANDING"


def test_htail_extended_balancing_closure():
    # Closure: the rational balancing tail load zeroes the pitching moment about the
    # CG for the selected flaps-extended condition (LT = LT25 + LT50).
    p = _ga6_with_landing()
    h = {c.label: c for c in select.build_critical(p).conditions if c.component == "htail"}
    for label in ("BAL UP EXTENDED", "BAL DN EXTENDED"):
        v = _vals(h[label])
        assert math.isclose(v["Total tail load"],
                            v["AoA load LT25 (cp 25%)"] + v["Camber/elevator load LT50 (cp 50%)"],
                            rel_tol=1e-6)


def test_critical_fuselage_conditions_match_appendix_a():
    # Appendix A "Critical Fuselage Loads": max fuselage down load on wing 13347.6
    # (GUST +C), aft down bending load 12569.6, aft up bending -6390.3 (GUST -C),
    # greatest vertical inertia factor NZ 5.81. ~0.15% FLTLOADS V-n noise.
    p = _ga6_three_altitudes()
    f = {c.label: c for c in select.build_critical(p).conditions if c.component == "fuselage"}
    assert set(f) == {"MAX DOWN LOAD ON WING", "AFT DOWN BENDING", "AFT UP BENDING", "GREATEST NZ"}
    assert math.isclose(_vals(f["MAX DOWN LOAD ON WING"])["Fuselage down load on wing"],
                        13347.6, rel_tol=3e-3)
    assert math.isclose(_vals(f["AFT DOWN BENDING"])["Fuselage down load on wing"], 12569.6, rel_tol=3e-3)
    assert math.isclose(_vals(f["AFT UP BENDING"])["Fuselage load on wing"], -6390.3, rel_tol=3e-3)
    assert math.isclose(_vals(f["GREATEST NZ"])["Load factor NZ"], 5.81, rel_tol=3e-3)


def test_wing_and_fuselage_when_no_tail_loads():
    # Without tail_loads/vtail_loads, SELECT still writes the wing + fuselage sets
    # (the fuselage conditions need only the V-n matrix).
    p = _ga6_three_altitudes()
    cls = select.build_critical(p)
    assert {c.component for c in cls.conditions} == {"wing", "fuselage"}


def test_critical_vtail_loads_match_appendix_a():
    # Appendix A "Critical Vertical Tail Loads": sudden full rudder +591 (rudder
    # load 167), yaw-to-sideslip 19.5 deg total -92 (yaw -684, rudder 591), yaw 15
    # neutral -526, side gust at VC +604 (IZZ 4169.2 slug-ft^2). The
    # rudder-deflection loads carry the EFV~1.009 large-deflection chart factor
    # (default 1.0, not legible in the source); the AoA/gust loads are exact.
    p = _ga6_three_altitudes()
    p.vtail_loads = _VTAIL
    cls = select.build_critical(p)
    vt = {c.label: c for c in cls.conditions if c.component == "vtail"}
    assert set(vt) == {"SUDDEN RUDDER", "YAW TO SIDESLIP", "YAW 15 NEUTRAL", "SIDE GUST"}

    v1 = _vals(vt["SUDDEN RUDDER"])
    assert math.isclose(v1["Total tail load"], 591, rel_tol=1.5e-2)         # +EFV ~1%
    assert math.isclose(v1["Load on rudder"], 167, rel_tol=1.5e-2)

    v2 = _vals(vt["YAW TO SIDESLIP"])
    assert math.isclose(v2["Load due to yaw 19.5deg (cp 25%)"], -684, rel_tol=3e-3)  # exact
    assert math.isclose(v2["Load due to rudder (cp 50%)"], 591, rel_tol=1.5e-2)

    v3 = _vals(vt["YAW 15 NEUTRAL"])
    assert math.isclose(v3["Total tail load (cp 25%)"], -526, rel_tol=3e-3)  # exact

    v4 = _vals(vt["SIDE GUST"])
    assert math.isclose(v4["Total tail load (cp 25%)"], 604, rel_tol=3e-3)   # exact
    assert math.isclose(v4["Yaw inertia IZZ"], 4169.164, rel_tol=1e-3)


def test_vtail_far_references():
    p = _ga6_three_altitudes()
    p.vtail_loads = _VTAIL
    vt = {c.label: c for c in select.build_critical(p).conditions if c.component == "vtail"}
    assert vt["SUDDEN RUDDER"].far_reference == "23.441(a)(1)"
    assert vt["SIDE GUST"].far_reference == "23.443(b)"


def test_vtail_large_deflection_factor_recovers_oracle():
    # Setting EFV to the chart value (~1.009) recovers the printed rudder load 591.
    p = _ga6_three_altitudes()
    p.vtail_loads = VTailLoadsInput(**{**_VTAIL.__dict__, "rudder_large_deflection_factor": 1.009})
    vt = {c.label: c for c in select.build_critical(p).conditions if c.component == "vtail"}
    assert math.isclose(_vals(vt["SUDDEN RUDDER"])["Total tail load"], 591, rel_tol=4e-3)


def test_concept_flag_in_report():
    p = _ga6_three_altitudes()
    p.speeds.category = "C"
    p.speeds.chosen_n = 4.0
    p.speeds.chosen_nneg = -2.0
    result = select.run(p)
    assert any("Concept mode" in c.note for c in result.conditions)


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
