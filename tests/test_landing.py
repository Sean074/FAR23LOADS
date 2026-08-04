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
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.models import (  # noqa: E402
    CgCase,
    LandingGearInput,
    LandingInput,
    Project,
    StructuralSpeedsInput,
)
from sloads.modules.landing import (  # noqa: E402
    _geometry,
    build_landing,
    landing_load_factor,
    landing_reactions,
    run,
)
from helpers import apply_button  # noqa: E402

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
    """The GA-6 example flows through build_landing/run; N is returned, not stored."""
    p = io.load_project(_GA)
    lf, rx = build_landing(p)
    assert len(rx) == 33
    assert math.isclose(lf.airplane_load_factor, 3.0951, rel_tol=2e-3)
    mod = run(p)
    assert mod.module == "landing"
    titles = [c.title for c in mod.conditions]
    assert titles[0].startswith("Landing load factor")
    assert any("Braked roll" in t for t in titles)


def test_render_leaves_project_unchanged():
    """M2R-4: rendering Landing Loads must not mutate the project -- build_landing/run
    are pure, so the serialized project (the exact unsaved-changes predicate) is
    unchanged. Covers both the geometry-gear sync and the derived gross-weight path."""
    # (a) Full GA-6 fixture: geometry gear present, gross_weight_lb set.
    p = io.load_project(_GA)
    before = io.project_to_dict(p)
    build_landing(p)
    run(p)
    assert io.project_to_dict(p) == before, "build_landing/run mutated the project"

    # (b) gross_weight_lb == 0 -> the heaviest-CG default is resolved on a local copy,
    #     never written back onto the input slice.
    p2 = Project(name="gw0", landing=replace(_ga_landing(), gross_weight_lb=0.0))
    before2 = io.project_to_dict(p2)
    lf, _ = build_landing(p2)
    assert p2.landing.gross_weight_lb == 0.0
    assert lf.airplane_load_factor > 0
    assert io.project_to_dict(p2) == before2


def test_landing_io_roundtrip():
    """The landing slice round-trips (CG cases + non-geometry params); the gear
    geometry (Step G6b) round-trips under geometry.landing_gear, not the landing
    block; older files migrate."""
    p = io.load_project(_GA)
    d = io.project_to_dict(p)
    p2 = io.project_from_dict(d)
    assert p2.landing.gear_load_factor == 2.5
    assert p2.landing.cg_cases[0].xcg == 85.1
    # Gear geometry is the single-source geometry.landing_gear (not on the landing block).
    assert "main_gear" not in d["landing"] and "tread_in" not in d["landing"]
    lg = p2.geometry.landing_gear
    assert lg.main_gear.strut == "O"
    assert lg.main_gear.axle_static == (96.7, 59.6)
    assert lg.tread_in == p.geometry.landing_gear.tread_in
    # Dropping the landing block leaves no landing slice (gear stays under geometry).
    d.pop("landing", None)
    p3 = io.project_from_dict(d)
    assert p3.landing is None
    assert p3.geometry.landing_gear is not None


# --------------------------------------------------------------------------- #
# M2-8 -- explicit CG cases required; concept-mode 23.473(g) floor warning
# --------------------------------------------------------------------------- #
def test_landing_requires_explicit_cg_cases():
    """No auto-derivation from Project.mass: LANDLOAD needs three distinct CG
    loadings, so an empty ``cg_cases`` (even with a mass slice present) raises a
    clear error rather than silently building a degenerate fwd/aft pair (M2-8)."""
    inp = replace(_ga_landing(), cg_cases=[])
    try:
        build_landing(Project(landing=inp))
        raise AssertionError("expected ValueError for missing cg_cases")
    except ValueError as e:
        assert "cg_cases" in str(e)


def _soft_strut_landing() -> LandingInput:
    """GA-6 gear with an over-soft oleo stroke so N/NLG fall below the 23.473(g)
    floors (N < 2.67, NLG < 2.0) -- the trigger for the concept-mode warning."""
    return replace(_ga_landing(), strut_stroke_in=25.0)


def test_landing_473g_floor_warning_concept():
    """Concept mode notes the 23.473(g) floor when N < 2.67 or NLG < 2.0."""
    lf, _ = build_landing(Project(landing=_soft_strut_landing()))
    assert lf.airplane_load_factor < 2.67 and lf.gear_load_factor < 2.0
    mod = run(Project(landing=_soft_strut_landing(),
                      speeds=StructuralSpeedsInput(category="C")))
    note = mod.conditions[0].note
    assert "23.473(g)" in note and "N=" in note and "NLG=" in note


def test_landing_473g_floor_not_warned_in_far23():
    """The floor note is concept-gated: a FAR23 project below the floor is silent
    (the computed N/NLG are unchanged in both modes -- warn-only)."""
    mod = run(Project(landing=_soft_strut_landing(),
                      speeds=StructuralSpeedsInput(category="N")))
    assert "23.473(g)" not in mod.conditions[0].note


# --------------------------------------------------------------------------- #
# M4-17 -- oracle regression guard, the undelivered outputs, ranking and ordering
# --------------------------------------------------------------------------- #
def test_appendix_a_oracles_unchanged_through_the_project_pipeline():
    """Regression guard for M4-17: the p230/p236 oracles re-asserted *through*
    ``build_landing(load_project(...))``, so a seed / ordering / emission change that
    leaked into the math fails here and not only in the low-level helpers."""
    p = io.load_project(_GA)
    lf, rx = build_landing(p)
    # p236 LGFACTOR.
    assert math.isclose(lf.sink_rate_fps, 9.004822, rel_tol=REL), lf.sink_rate_fps
    assert math.isclose(lf.airplane_load_factor, 3.095102, rel_tol=2e-3), lf
    assert math.isclose(lf.gear_load_factor, 2.428102, rel_tol=2e-3), lf
    # p230 legible wheel-load cells (the reaction table the seed feeds).
    by_case = {c.case: c for c in rx}
    assert math.isclose(by_case[1].vmp, 3144, rel_tol=3e-3), by_case[1].vmp
    assert math.isclose(by_case[1].vnp, 1787, rel_tol=3e-3), by_case[1].vnp
    assert math.isclose(by_case[19].smp, -1700, rel_tol=3e-3), by_case[19].smp


def test_unbalanced_moments_closure():
    """Closure on PITCHP/ROLLP/YAWP (LANDLOAD.BAS 1910-2090) -- computed since the
    original port but delivered nowhere and asserted nowhere until M4-17e."""
    inp = _ga_landing()
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    g = _geometry(inp, inp.gear_load_factor, inp.cg_cases)
    rx = {c.case: c for c in landing_reactions(inp, lf, inp.cg_cases)}
    wr = inp.gross_weight_lb / inp.max_landing_weight_lb
    # 2-wheel level (4) and tail-down (7): -2 * RMP * BP for the attitude/CG pair.
    assert math.isclose(rx[4].pitchp, -2 * rx[4].rmp * g.bp[0][0], rel_tol=1e-9)
    assert math.isclose(rx[7].pitchp, -2 * rx[7].rmp * g.bp[2][0], rel_tol=1e-9)
    # One-wheel (10): a single wheel, so -1 * RMP * BP, plus roll/yaw about the tread.
    assert math.isclose(rx[10].pitchp, -1 * rx[10].rmp * g.bp[0][0], rel_tol=1e-9)
    assert math.isclose(rx[10].rollp, rx[10].vmp * inp.tread_in / 2, rel_tol=1e-9)
    assert math.isclose(rx[10].yawp, -rx[10].dmp * inp.tread_in / 2, rel_tol=1e-9)
    # Braked roll nose clear (16): the drag reaction acts at the CP vertical offset.
    assert math.isclose(rx[16].pitchp,
                        -2 * (rx[16].vmp * g.bp[1][0] + rx[16].dmp * g.cp[1][0]), rel_tol=1e-9)
    # Side load (19/20): pitch from the vertical only; roll/yaw are the 0.83 W couple,
    # signed by the drift direction (odd case = left drift).
    w19 = inp.cg_cases[0].weight_lb * wr
    assert math.isclose(rx[19].pitchp, -2 * rx[19].vmp * g.bp[1][0], rel_tol=1e-9)
    assert math.isclose(rx[19].rollp, -0.83 * w19 * g.cp[1][0], rel_tol=1e-9)
    assert math.isclose(rx[20].rollp, +0.83 * w19 * g.cp[1][0], rel_tol=1e-9)
    assert math.isclose(rx[19].yawp, -0.83 * w19 * g.bp[1][0], rel_tol=1e-9)
    # 3-wheel level (1-3) is balanced, and the supplementary-nose family has no moment.
    assert rx[1].pitchp == rx[1].rollp == rx[1].yawp == 0.0
    for m in range(25, 34):
        assert rx[m].pitchp == rx[m].rollp == rx[m].yawp == 0.0, m


def test_ground_line_inertia_factors_closure():
    """Closure on NVP/NDP/NS (LANDLOAD.BAS 1910-2000): the three lift/wheel regimes."""
    inp = _ga_landing()
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    rx = {c.case: c for c in landing_reactions(inp, lf, inp.cg_cases)}
    lift, wr = inp.lift_factor, inp.gross_weight_lb / inp.max_landing_weight_lb
    w1 = inp.cg_cases[0].weight_lb
    # Cases 1-9: both mains + the nose, with the wing lift carried.
    assert math.isclose(rx[1].nvp, (2 * rx[1].vmp + rx[1].vnp + lift * w1) / w1, rel_tol=1e-9)
    assert math.isclose(rx[1].ndp, (2 * rx[1].dmp + rx[1].dnp) / w1, rel_tol=1e-9)
    # Cases 10-12 (one wheel): a single main reaction.
    assert math.isclose(rx[10].nvp, (rx[10].vmp + lift * w1) / w1, rel_tol=1e-9)
    assert math.isclose(rx[10].ndp, (rx[10].dmp + rx[10].dnp) / w1, rel_tol=1e-9)
    # Cases 13-24: braked roll / side load carry no lift term.
    w13 = w1 * wr
    assert math.isclose(rx[13].nvp, (2 * rx[13].vmp + rx[13].vnp) / w13, rel_tol=1e-9)
    # NS is the side-load pair difference over the case weight, and zero elsewhere.
    assert math.isclose(rx[19].ns, (rx[19].smp - rx[20].smp) / w13, rel_tol=1e-9)
    assert math.isclose(rx[20].ns, (rx[20].smp - rx[19].smp) / w13, rel_tol=1e-9)
    assert rx[1].ns == 0.0 and rx[13].ns == 0.0
    for m in range(25, 34):
        assert rx[m].nvp == rx[m].ndp == rx[m].ns == 0.0, m


def test_run_emits_full_case_matrix():
    """M4-17e: run() carries the 33-case matrix alongside the 7 summary conditions,
    so the ULTIMATE deliverable is not thinner than the LIMIT analysis screen."""
    p = io.load_project(_GA)
    mod = run(p)
    _, rx = build_landing(p)
    assert len(mod.conditions) == 1 + 6 + 33, len(mod.conditions)
    matrix = [c for c in mod.conditions if " — case " in c.title]
    assert len(matrix) == 33
    # A summary condition and its matrix row are the same physical case -> same id.
    assert ({c.case_ref.case_id for c in matrix}
            == {c.case_ref.case_id for c in rx})
    labels = {v.label for v in matrix[0].values}
    for expected in ("Unbalanced pitching moment", "Unbalanced rolling moment",
                     "Unbalanced yawing moment", "Vertical inertia factor NVP",
                     "Drag inertia factor NDP", "Side inertia factor NS"):
        assert expected in labels, expected
    # Cases 25-33 are nose-only (no main reaction, moment or inertia factor).
    nose_only = [c for c in matrix if c.title.startswith("supplementary")]
    assert len(nose_only) == 9
    assert {v.label for v in nose_only[0].values} == {
        "Vertical nose", "Drag nose", "Side nose", "Resultant nose"}
    # One uniform factor across the module (14 CFR 23.303).
    assert {c.safety_factor for c in mod.conditions} == {1.5}


def test_landing_csv_is_ultimate_and_carries_moments_and_factors():
    """The CSV reports every case ULTIMATE: forces lbs-ULT and moments lb-in-ULT at
    SF 1.5, while the dimensionless inertia factors pass through **unscaled** with
    blank units and a blank SF (they are load factors -- CLAUDE.md ultimate rules)."""
    import csv as _csv

    from sloads.report import has_load_case_data

    p = io.load_project(_GA)
    mod = run(p)
    _, rx = build_landing(p)
    by_case = {c.case: c for c in rx}
    # Landing is a per-quantity table, not the single-point-load schema, so it routes
    # through results_to_rows -- report._LOAD_CASE_LABELS is deliberately not extended.
    assert has_load_case_data(mod.conditions) is False
    rows = list(_csv.DictReader(io.load_cases_csv(mod).splitlines()))
    matrix = [r for r in rows if " — case 16 " in r["Condition"]]
    quantities = {r["Quantity"]: r for r in matrix}
    force = quantities["Vertical main per wheel"]
    assert force["Units"] == "lbs-ULT" and force["SF"] == "1.5"
    assert math.isclose(float(force["Value"]), by_case[16].vmp * 1.5, rel_tol=1e-3)
    moment = quantities["Unbalanced pitching moment"]
    assert moment["Units"] == "lb-in-ULT" and moment["SF"] == "1.5"
    assert math.isclose(float(moment["Value"]), by_case[16].pitchp * 1.5, rel_tol=1e-3)
    factor = quantities["Vertical inertia factor NVP"]
    assert factor["Units"] == "" and factor["SF"] == "", factor
    assert math.isclose(float(factor["Value"]), by_case[16].nvp, rel_tol=1e-3)


def test_critical_ranking_includes_side_load():
    """M4-17e: _critical ranks on the full sqrt(V^2+D^2+S^2), not the printed
    two-component RMP/RESULT. Numerically inert on the bundled examples (the picks are
    unchanged) -- the point is that the 23.485 pick is no longer a tie-break accident."""
    from dataclasses import replace as _replace

    from sloads.modules.landing import _critical

    inp = _ga_landing()
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    rx = landing_reactions(inp, lf, inp.cg_cases)
    for far, case in (("23.479(a)", 4), ("23.481", 7), ("23.483", 10),
                      ("23.485", 19), ("23.493", 16), ("23.499", 28)):
        assert _critical(rx, far).case == case, (far, _critical(rx, far).case)
    # With an inflated side load on case 22 the pick must follow it; the old
    # max(rmp, result) ranking could not see SMP at all.
    boosted = [_replace(c, smp=c.smp * 10) if c.case == 22 else c for c in rx]
    assert _critical(boosted, "23.485").case == 22


def test_cg_cases_reordered_by_canonical_name():
    """M4-17d: the three canonical loadings are consumed positionally, so a shuffled
    (but canonically named) set is reordered by the calc and gives identical
    reactions; a non-canonical set stays in row order exactly as before."""
    inp = _ga_landing()
    shuffled = replace(inp, cg_cases=[inp.cg_cases[2], inp.cg_cases[0], inp.cg_cases[1]])
    ordered = build_landing(Project(landing=inp))[1]
    reordered = build_landing(Project(landing=shuffled))[1]
    assert [c.vmp for c in reordered] == [c.vmp for c in ordered]
    assert [c.cg_name for c in reordered] == [c.cg_name for c in ordered]
    # Non-canonical names: positional, so the shuffle *does* change the answer.
    renamed = replace(inp, cg_cases=[replace(c, name=f"loading {i}")
                                     for i, c in enumerate(shuffled.cg_cases)])
    assert [c.vmp for c in build_landing(Project(landing=renamed))[1]] != [c.vmp for c in ordered]


def test_seed_never_emits_a_zero_waterline():
    """M4-17c: with no waterline source the Landing Loads seed leaves the cell blank
    and the page **refuses to compute** -- it no longer defaults zcg to 0.0 and
    silently produces nonphysical reactions.

    Driven through ``AppTest`` (the view is a page script, not an importable module;
    same precedent as tests/test_dirty_flag.py). The paired positive case -- a real
    waterline and the interpolated forward station -- is
    ``test_dirty_flag.test_landing_cg_editor_seeds_and_persists_on_apply``.
    """
    try:   # the zero-dependency __main__ runner has neither pytest nor streamlit
        from streamlit.testing.v1 import AppTest
    except ImportError:  # pragma: no cover - exercised only by the fallback runner
        print("SKIP test_seed_never_emits_a_zero_waterline (no streamlit)")
        return

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # conftest.py does this under pytest; repeat it so the __main__ runner can resolve
    # the view's shared ``components`` import too.
    if os.path.join(root, "app") not in sys.path:
        sys.path.insert(0, os.path.join(root, "app"))
    view = os.path.join(root, "app", "views", "landing_loads.py")
    p = io.load_project(_GA)
    p.landing.cg_cases = []   # force a fresh seed
    p.mass = None             # ...with no waterline source

    at = AppTest.from_file(view, default_timeout=60)
    at.session_state["project"] = p
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    # The missing source is named, not silently defaulted.
    warnings = " ".join(w.value for w in at.warning)
    assert "Zcg waterline" in warnings and "Project.mass" in warnings, warnings
    # Apply cannot persist an incomplete row, and the reactions never compute.
    apply_button(at, "landing_loads_form").set_value(True).run()
    assert at.session_state["project"].landing.cg_cases == [], "saved a blank waterline"
    assert any("not saved" in e.value for e in at.error), [e.value for e in at.error]
    assert not any("Gear reaction loads" in s.value for s in at.subheader), \
        "reactions computed without a waterline"


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
