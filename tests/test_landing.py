"""Landing / ground loads (Step C10): LGFACTOR.BAS + LANDLOAD.BAS port.

Two oracle bands (Reference 1 Ch 20):

* **LGFACTOR is fully oracle-locked** against Appendix A "Landing Load Factor"
  p236: descent velocity ``V = 4.4*(W/S)^0.25`` (9.0048 fps), airplane load factor
  ``N`` (3.0951) and gear factor ``NLG = N - L`` (2.4281). N is within +0.07% of the
  printed value -- the expected Decision-3 drift from ``G = 32.174`` vs the program's
  ``32.2`` (still inside +-0.1%).

* **LANDLOAD's gear-geometry intermediates are oracle-locked** against Appendix A
  "Landing Loads with Respect to Ground Line" p230: the drag factor ``K`` (0.324),
  ``GAMMA = arctan(K)`` (17.978), the ground angles (4.057 / 4.724 / 15 deg), ``BETA``
  (13.921 / 4.724 / 15) and the ``AP/BP/DP/CP`` lever-arm table. The printed
  *wheel-load* table on p231-233 is heavily OCR-garbled in the bundled PDF (column
  headers and most numbers are scrambled), so the full 24-main / 33-nose matrix is
  validated by **formula closure plus the handful of legible cells** -- the same
  precedent as ONENGOUT (Step C9). The legible cells: case 1 (3-wheel level, aft)
  VMP 3144 / VNP 1787 / nose resultant 1879; the side-load cases VMP 2261 with
  SMP -1700 (LT drift) / 1122 (RT drift).

Note LANDLOAD takes the **gear load factor as a rounded design input** (2.5 on
p230), distinct from LGFACTOR's computed 2.428 -- the oracle's ``NAP = NLG + L``
is 3.167 = 2.5 + 0.667.

Reference: LGFACTOR.BAS (Appendix C p483), LANDLOAD.BAS (Appendix C p468); Ref 1
Ch 20; oracles Appendix A p230, p236.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import io  # noqa: E402
from farloads.models import CgCase, LandingGearInput, LandingInput  # noqa: E402
from farloads.modules.landing import (  # noqa: E402
    _geometry,
    build_landing,
    landing_load_factor,
    landing_reactions,
    run,
)

REL = 1e-3  # +-0.1%

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _ga_landing() -> LandingInput:
    """The Appendix A GA-6 landing inputs (p230 gear geometry, p236 LGFACTOR)."""
    return LandingInput(
        wing_area_sqft=184.125, max_landing_weight_lb=3230, gross_weight_lb=3400,
        strut_stroke_in=7, tire_od_in=19, hub_diameter_in=7, lift_factor=0.667,
        main_gear=LandingGearInput((96.3, 55.9), (96.7, 59.6), (96.2, 54.2), 8.0, "O"),
        nose_gear=LandingGearInput((1.9, 46.9), (2.4, 49.5), (1.6, 45.1), 5.7, "O"),
        tread_in=114.5, tail_down_angle_deg=15.0, gear_load_factor=2.5,
        cg_cases=[CgCase("aft max landing", 3230, 85.1, 93),
                  CgCase("fwd max landing", 3230, 76.12, 93),
                  CgCase("fwd light", 2803, 72.64, 92)],
    )


# --------------------------------------------------------------------------- #
# LGFACTOR -- fully oracle-locked (Appendix A p236)
# --------------------------------------------------------------------------- #
def test_lgfactor_oracle():
    r = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, main_is_oleo=True)
    assert math.isclose(r.sink_rate_fps, 9.004822, rel_tol=REL), r.sink_rate_fps
    assert math.isclose(r.airplane_load_factor, 3.095102, rel_tol=REL), r.airplane_load_factor
    assert math.isclose(r.gear_load_factor, 2.428102, rel_tol=REL), r.gear_load_factor


def test_lgfactor_velocity_clamp():
    """V = 4.4*(W/S)^0.25 is clamped to 7..10 fps (FAR 23.473(d))."""
    light = landing_load_factor(200, 500, 7, 19, 7, 0.5, True)   # tiny W/S -> 7
    heavy = landing_load_factor(50, 12000, 7, 19, 7, 0.667, True)  # large W/S -> 10
    assert math.isclose(light.sink_rate_fps, 7.0)
    assert math.isclose(heavy.sink_rate_fps, 10.0)


def test_lgfactor_spring_vs_oleo():
    """A spring strut (eta 0.5) absorbs less energy than an oleo (0.75) -> higher N."""
    oleo = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, main_is_oleo=True)
    spring = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, main_is_oleo=False)
    assert spring.airplane_load_factor > oleo.airplane_load_factor


# --------------------------------------------------------------------------- #
# LANDLOAD geometry -- oracle-locked (Appendix A p230)
# --------------------------------------------------------------------------- #
def test_landload_geometry_oracle():
    inp = _ga_landing()
    g = _geometry(inp, inp.gear_load_factor, inp.cg_cases)
    assert math.isclose(g.k, 0.324, rel_tol=3e-3), g.k
    assert math.isclose(g.gamma_deg, 17.978, rel_tol=3e-3), g.gamma_deg
    # Ground angles: 3-/2-wheel level, ground roll, tail down.
    assert math.isclose(g.gra[0], 4.057, rel_tol=3e-3), g.gra
    assert math.isclose(g.gra[1], 4.724, rel_tol=3e-3), g.gra
    assert g.gra[2] == 15.0
    # BETA per attitude.
    assert math.isclose(g.beta[0], 13.921, rel_tol=3e-3), g.beta
    assert math.isclose(g.beta[1], 4.724, rel_tol=3e-3), g.beta


def test_landload_lever_arms_oracle():
    """The BP / DP / ground-roll AP-CP lever arms reproduce the p230 table exactly."""
    inp = _ga_landing()
    g = _geometry(inp, inp.gear_load_factor, inp.cg_cases)
    # Level-attitude BP for the three CG cases (p230).
    assert math.isclose(g.bp[0][0], 19.796, rel_tol=2e-3), g.bp[0]
    assert math.isclose(g.bp[0][1], 28.512, rel_tol=2e-3), g.bp[0]
    assert math.isclose(g.bp[0][2], 31.649, rel_tol=2e-3), g.bp[0]
    # Ground-roll lever arms (AP / BP / DP / CP) reproduce p230 to the printed digits.
    assert math.isclose(g.ap[1][0], 78.836, rel_tol=2e-3), g.ap[1]
    assert math.isclose(g.bp[1][0], 14.311, rel_tol=2e-3), g.bp[1]
    assert math.isclose(g.dp[1][0], 93.147, rel_tol=2e-3), g.dp[1]
    assert math.isclose(g.cp[1][1], 42.981, rel_tol=2e-3), g.cp[1]
    # Tail-down BP (vertical reactions).
    assert math.isclose(g.bp[2][2], 13.511, rel_tol=2e-3), g.bp[2]


# --------------------------------------------------------------------------- #
# LANDLOAD wheel loads -- legible-cell spot-checks + formula closure
# --------------------------------------------------------------------------- #
def test_landload_legible_cells():
    """Spot-check the wheel-load cells that survive the p231 OCR."""
    inp = _ga_landing()
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    rx = {c.case: c for c in landing_reactions(inp, lf, inp.cg_cases)}
    # Case 1 -- 3-wheel level, aft max landing.
    assert math.isclose(rx[1].vmp, 3144, rel_tol=3e-3), rx[1].vmp
    assert math.isclose(rx[1].vnp, 1787, rel_tol=3e-3), rx[1].vnp
    assert math.isclose(rx[1].result, 1879, rel_tol=3e-3), rx[1].result
    # Side-load cases -- vertical 2261, side -1700 (LT) / 1122 (RT).
    assert math.isclose(rx[19].vmp, 2261, rel_tol=3e-3), rx[19].vmp
    assert math.isclose(rx[19].smp, -1700, rel_tol=3e-3), rx[19].smp
    assert math.isclose(rx[20].smp, 1122, rel_tol=3e-3), rx[20].smp


def test_landload_case_formulas():
    """Closure on the FAR-section reaction formulas (LANDLOAD.BAS 910-1900)."""
    inp = _ga_landing()
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    g = _geometry(inp, inp.gear_load_factor, inp.cg_cases)
    rx = {c.case: c for c in landing_reactions(inp, lf, inp.cg_cases)}
    nlg, k = inp.gear_load_factor, g.k
    w1 = inp.cg_cases[0].weight_lb
    # 3-wheel level (case 1): VMP = .5*NLG*W*AP/DP, DMP = K*VMP, resultant.
    assert math.isclose(rx[1].vmp, 0.5 * nlg * w1 * g.ap[0][0] / g.dp[0][0], rel_tol=1e-9)
    assert math.isclose(rx[1].dmp, k * rx[1].vmp, rel_tol=1e-9)
    assert math.isclose(rx[1].rmp, math.hypot(rx[1].vmp, rx[1].dmp), rel_tol=1e-9)
    # 2-wheel level (case 4): VMP = .5*NLG*W, no nose reaction.
    assert math.isclose(rx[4].vmp, 0.5 * nlg * w1, rel_tol=1e-9)
    assert rx[4].vnp == 0.0
    # Tail-down (case 7): vertical only, DMP = 0.
    assert rx[7].dmp == 0.0
    # Braked roll (case 13): DMP = 0.8*VMP, VNP = 1.33*W - 2*VMP.
    assert math.isclose(rx[13].dmp, 0.8 * rx[13].vmp, rel_tol=1e-9)
    assert math.isclose(rx[13].vnp, 1.33 * inp.cg_cases[0].weight_lb
                        * (inp.gross_weight_lb / inp.max_landing_weight_lb)
                        - 2 * rx[13].vmp, rel_tol=1e-9)
    # Supplementary nose (case 25): VNP = 2.25*static-load, DNP = 0.8*VNP, side = 0.7*VNP.
    assert math.isclose(rx[25].dnp, 0.8 * rx[25].vnp, rel_tol=1e-9)
    assert math.isclose(rx[27].snp, 0.7 * rx[27].vnp, rel_tol=1e-9)


def test_landload_pipeline_and_run():
    """The GA-6 example flows through build_landing/run; LGFACTOR N persists."""
    p = io.load_project(_GA)
    lf, rx = build_landing(p)
    assert len(rx) == 33
    assert math.isclose(lf.airplane_load_factor, 3.0951, rel_tol=2e-3)
    assert p.landing.n is not None and math.isclose(p.landing.n, lf.airplane_load_factor)
    mod = run(p)
    assert mod.module == "landing"
    titles = [c.title for c in mod.conditions]
    assert titles[0].startswith("Landing load factor")
    assert any("Braked roll" in t for t in titles)


def test_landing_io_roundtrip():
    """The landing slice round-trips (nested gear + CG cases); older files load."""
    p = io.load_project(_GA)
    d = io.project_to_dict(p)
    p2 = io.project_from_dict(d)
    assert p2.landing.gear_load_factor == 2.5
    assert p2.landing.main_gear.strut == "O"
    assert p2.landing.main_gear.axle_static == (96.7, 59.6)
    assert p2.landing.cg_cases[0].xcg == 85.1
    d.pop("landing", None)
    p3 = io.project_from_dict(d)
    assert p3.landing is None


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
