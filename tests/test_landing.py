"""Landing / ground loads (Step C10): LGFACTOR.BAS + LANDLOAD.BAS port.

Two oracle bands (Reference 1 Ch 20):

* **LGFACTOR is fully oracle-locked** against Appendix A "Landing Load Factor"
  p236: descent velocity ``V = 4.4*(W/S)^0.25`` (9.0048 fps), airplane load factor
  ``N`` (3.0951) and gear factor ``NLG = N - L`` (2.4281). N is within +0.07% of the
  printed value -- the expected Decision-3 drift from ``G = 32.174`` vs the program's
  ``32.2`` (still inside +-0.1%).

* **LANDLOAD is fully oracle-locked** against Appendix A: p230 "Landing Loads with
  Respect to Ground Line" for the intermediates -- the drag factor ``K`` (0.324),
  ``GAMMA = arctan(K)`` (17.978), the ground angles (4.057 / 4.724 / 15 deg), ``BETA``
  (13.921 / 4.724 / 15) and the ``AP/BP/DP/CP`` lever-arm table -- and then **every
  printed cell** of p231 (ground line), p232 (airplane datum) and p233 (limit
  unbalanced moments), for all 33 cases.

  Those three pages are OCR-garbled in the bundled PDF and were recorded from
  2026-08-15 as unusable, so the 24-main / 33-nose matrix was held by formula
  closure plus a handful of legible cells -- the ONENGOUT (Step C9) precedent.
  **They are garbled, not illegible**: rendered at 200 dpi they read cleanly, and
  the tables were transcribed on 2026-08-29. Reading them found two defects that
  had lived in the gap (#135, #137), one of which had made a fixture input a
  function of the output it was used to check. Transcription and OCR extraction
  are not the same failure mode, which is why the citations now say which one a
  cell came from.

Note the manual's LANDLOAD runs at a **rounded design load factor** distinct from
LGFACTOR's computed 2.428: since note 37 that is entered as the governing
**airplane** load factor ``N = 3.167`` (the oracle's ``NAP = NLG + L`` =
2.5 + 0.667) and ``NLG = N - L = 2.5`` is derived -- never entered -- so the
wing lift factor L always moves the gear reaction (gate G-LF-2).

Reference: LGFACTOR.BAS (Appendix C p483), LANDLOAD.BAS (Appendix C p468); Ref 1
Ch 20; oracles Appendix A p230, p236.
"""

import math
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io
from sloads.cg_cases import landing_role_cases
from sloads.models import (
    AnalysisKind,
    CgCase,
    GeometryInput,
    GroundCaseRole,
    LandingGearGeometry,
    LandingGearInput,
    LandingInput,
    Project,
    StructuralSpeedsInput,
    WeightInput,
)
from sloads.modules.landing import (
    _geometry,
    build_landing,
    landing_load_factor,
    landing_reactions,
    run,
)

REL = 1e-3  # +-0.1%

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


#: The Appendix A GA-6 design weights, which left ``LandingInput`` at decisions
#: G-4 / G-14 and are now passed to ``landing_reactions`` explicitly.
_MLW, _MTOW = 3230.0, 3400.0
# The governing NLG the ga6 fixture runs at: the entered N = 3.167 (LF-9, the
# manual's rounded design value -- p230 reproduces at no other NLG) minus
# L = 0.667. Stated as the literal the oracle used, not re-derived in float.
_GA_NLG = 2.5

#: The three roled loadings, in the order LANDLOAD consumes them.
_GA_CGS = [
    CgCase("aft max landing", 3230, 85.1, 93,
           {AnalysisKind.GROUND}, GroundCaseRole.AFT_MAX_LANDING),
    CgCase("fwd max landing", 3230, 76.12, 93,
           {AnalysisKind.GROUND}, GroundCaseRole.FWD_MAX_LANDING),
    # 2800 lb is WTENV's forward-regardless weight, which is what
    # ``cg_cases.seed_landing_cases`` gives this case and what p230 prints. It
    # read 2803 until 2026-08-29: the weight had been back-solved from the p231
    # side-load cell when that cell was OCR'd as 1864 (0.5*1.33*W), and the
    # rendered page prints 1862 -- 1862/0.665 = 2800.0 exactly.
    CgCase("fwd light", 2800, 72.64, 92,
           {AnalysisKind.GROUND}, GroundCaseRole.FWD_LIGHT),
]


def _ga_weight() -> WeightInput:
    """The weight slice the landing conditions now read: both design weights and
    the three roled GROUND cases (decisions G-3 / G-4 / G-14)."""
    return WeightInput(cg_cases=list(_GA_CGS),
                       max_landing_weight_lb=_MLW, max_takeoff_weight_lb=_MTOW)


def _ga_project(landing: LandingInput = None, **kw) -> Project:
    kw.setdefault("geometry", GeometryInput(surfaces=[_ga_wing()],
                                           landing_gear=_ga_gear()))
    return Project(landing=landing or _ga_landing(), weight=_ga_weight(), **kw)


def _ga_landing() -> LandingInput:
    """The Appendix A GA-6 landing inputs (p236 LGFACTOR).

    The gear *geometry* is :func:`_ga_gear`, on the geometry slice where it is
    stored (note 33, DS-1) rather than duplicated onto this one.
    """
    return LandingInput(
        strut_stroke_in=7, tire_od_in=19, hub_diameter_in=7, lift_factor=0.667,
        tail_down_angle_deg=15.0, airplane_load_factor=3.167,
    )


def _ga_wing():
    """The GA-6 wing planform, for the S LGFACTOR reads.

    Note 33 (DS-1/DS-3) removed ``landing.wing_area_sqft``: the area is the
    planform's strip integral, with no slice copy to state a second one. The
    planform comes from the shipped fixture rather than being retyped here, and
    integrates to 184.121 ft² against Appendix A's printed 184.125 — inside the
    ±0.1 % oracle band, which is the whole point of reading the geometry.
    """
    return io.load_project(_GA).geometry.by_name("wing")


def _ga_gear() -> LandingGearGeometry:
    """The Appendix A GA-6 gear geometry (p230)."""
    return LandingGearGeometry(
        main_gear=LandingGearInput((96.3, 55.9), (96.7, 59.6), (96.2, 54.2), 8.0, "O"),
        nose_gear=LandingGearInput((1.9, 46.9), (2.4, 49.5), (1.6, 45.1), 5.7, "O"),
        tread_in=114.5,
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
    g = _geometry(inp, _ga_gear(), _GA_NLG, _GA_CGS, _MLW)
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
    g = _geometry(inp, _ga_gear(), _GA_NLG, _GA_CGS, _MLW)
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
# LANDLOAD wheel loads -- the full printed Appendix A output (p231/p232/p233)
# --------------------------------------------------------------------------- #
# Every cell of the three printed LANDLOAD tables, transcribed from the pages
# rendered at 200 dpi (2026-08-29) rather than extracted by OCR. That
# distinction is the whole history of this module's oracle coverage: the
# bundled PDF's *text layer* for these pages is garbled, and from 2026-08-15
# the project recorded them as unusable and held cases 13-33 on internal
# identities alone. Two defects lived in that gap -- the ``WL(18)`` gross-weight
# ratio (#135) and a fixture weight that had been back-solved from a
# mis-OCR'd cell (#137), which also meant an input was derived from the output
# it was then used to check. The pages read cleanly rendered.
#
# The printed resolution is the tolerance: integer columns lock at +-0.5 or
# +-0.1 %, whichever is looser (a 153 lb cell cannot be read closer than half a
# pound, which is already 0.33 %); three-decimal columns at +-0.0005 or +-0.1 %.
#
# These values are also the deviated-from set design note 38's GF-3" must
# state: GF-1 moves the p232 columns for cases 13-33 and GF-2' moves p231 cases
# 13-15 and 25-33 and the p233 moments for 16-24. Transcribed here, they are
# executable rather than prose. If a deviation is approved, the affected rows
# move to the corrected values with the register entry cited beside them --
# they are never deleted.

#: p231 "VALUES ARE WITH RESPECT TO GROUND LINE - DENOTED BY P (PRIME)".
_P231_COLS = ("vnp", "dnp", "snp", "result", "vmp", "dmp", "smp", "rmp",
              "nvp", "ndp", "ns")
_P231 = {
    1: (1787, 580, 0, 1879, 3144, 1020, 0, 3305, 3.167, 0.811, 0.00),
    2: (2574, 835, 0, 2706, 2751, 893, 0, 2892, 3.167, 0.811, 0.00),
    3: (2476, 804, 0, 2604, 2262, 734, 0, 2378, 3.167, 0.811, 0.00),
    4: (0, 0, 0, 0, 4038, 1310, 0, 4245, 3.167, 0.811, 0.00),
    5: (0, 0, 0, 0, 4038, 1310, 0, 4245, 3.167, 0.811, 0.00),
    6: (0, 0, 0, 0, 3500, 1136, 0, 3680, 3.167, 0.811, 0.00),
    7: (0, 0, 0, 0, 4038, 0, 0, 4038, 3.167, 0.000, 0.00),
    8: (0, 0, 0, 0, 4038, 0, 0, 4038, 3.167, 0.000, 0.00),
    9: (0, 0, 0, 0, 3500, 0, 0, 3500, 3.167, 0.000, 0.00),
    10: (0, 0, 0, 0, 4038, 1310, 0, 4245, 1.917, 0.406, 0.00),
    11: (0, 0, 0, 0, 4038, 1310, 0, 4245, 1.917, 0.406, 0.00),
    12: (0, 0, 0, 0, 3500, 1136, 0, 3680, 1.917, 0.406, 0.00),
    13: (1714, 0, 0, 1714, 1404, 1123, 0, 1798, 1.330, 0.661, 0.00),
    14: (2044, 0, 0, 2044, 1239, 991, 0, 1587, 1.330, 0.583, 0.00),
    15: (1773, 0, 0, 1773, 975, 780, 0, 1249, 1.330, 0.557, 0.00),
    16: (0, 0, 0, 0, 2261, 1809, 0, 2895, 1.330, 1.064, 0.00),
    17: (0, 0, 0, 0, 2261, 1809, 0, 2895, 1.330, 1.064, 0.00),
    18: (0, 0, 0, 0, 1862, 1490, 0, 2385, 1.330, 1.064, 0.00),
    19: (0, 0, 0, 0, 2261, 0, -1700, 2261, 1.330, 0.000, -0.83),
    20: (0, 0, 0, 0, 2261, 0, 1122, 2261, 1.330, 0.000, 0.83),
    21: (0, 0, 0, 0, 2261, 0, -1700, 2261, 1.330, 0.000, -0.83),
    22: (0, 0, 0, 0, 2261, 0, 1122, 2261, 1.330, 0.000, 0.83),
    23: (0, 0, 0, 0, 1862, 0, -1400, 1862, 1.330, 0.000, -0.83),
    24: (0, 0, 0, 0, 1862, 0, 924, 1862, 1.330, 0.000, 0.83),
    # Supplementary nose-wheel conditions (23.499) -- nose columns only.
    25: (1175, 940, 0, 1505, None, None, None, None, None, None, None),
    26: (1175, -470, 0, 1266, None, None, None, None, None, None, None),
    27: (1175, 0, 823, 1175, None, None, None, None, None, None, None),
    28: (1910, 1528, 0, 2446, None, None, None, None, None, None, None),
    29: (1910, -764, 0, 2058, None, None, None, None, None, None, None),
    30: (1910, 0, 1337, 1910, None, None, None, None, None, None, None),
    31: (1802, 1442, 0, 2308, None, None, None, None, None, None, None),
    32: (1802, -721, 0, 1941, None, None, None, None, None, None, None),
    33: (1802, 0, 1262, 1802, None, None, None, None, None, None, None),
}
#: Column print resolution, in the printed unit.
_P231_RES = dict(vnp=1, dnp=1, snp=1, result=1, vmp=1, dmp=1, smp=1, rmp=1,
                 nvp=1e-3, ndp=1e-3, ns=1e-2)

#: p232 "VALUES ARE WITH RESPECT TO AIRPLANE DATUM" -- the force columns.
#: The page's NR/NV/ND load-factor columns are transcribed in design note 38
#: (GF-6/#134), not here: ``run()`` does not compute them yet.
_P232_COLS = ("vn", "dn", "vm", "dm", "sm")
_P232 = {
    1: (1823, 452, 3208, 795, 0), 2: (2626, 651, 2807, 696, 0),
    3: (2527, 626, 2308, 572, 0),
    4: (0, 0, 4120, 1021, 0), 5: (0, 0, 4120, 1021, 0), 6: (0, 0, 3572, 885, 0),
    7: (0, 0, 3900, -1045, 0), 8: (0, 0, 3900, -1045, 0), 9: (0, 0, 3381, -906, 0),
    10: (0, 0, 4120, 1021, 0), 11: (0, 0, 4120, 1021, 0), 12: (0, 0, 3572, 885, 0),
    13: (1708, 141, 1307, 1235, 0), 14: (2037, 168, 1153, 1090, 0),
    15: (1767, 146, 908, 858, 0),
    16: (0, 0, 2104, 1989, 0), 17: (0, 0, 2104, 1989, 0), 18: (0, 0, 1733, 1638, 0),
    19: (0, 0, 2253, 186, -1700), 20: (0, 0, 2253, 186, 1122),
    21: (0, 0, 2253, 186, -1700), 22: (0, 0, 2253, 186, 1122),
    23: (0, 0, 1856, 153, -1400), 24: (0, 0, 1856, 153, 924),
    25: (1094, 1034, None, None, 0), 26: (1210, -372, None, None, 0),
    27: (1171, 97, None, None, 823),
    28: (1778, 1680, None, None, 0), 29: (1967, -604, None, None, 0),
    30: (1904, 157, None, None, 1337),
    31: (1677, 1585, None, None, 0), 32: (1855, -570, None, None, 0),
    33: (1796, 148, None, None, 1262),
}

#: p233 "LIMIT UNBALANCED MOMENTS", the ground-line columns. The page's
#: airplane-datum moment columns are a *second* ground-to-datum rotation, and
#: they carry the note-38 sign question -- see ``theory_sources.md`` and note 38
#: §1.13. They are not asserted here because ``run()`` emits only the primed set.
_P233_COLS = ("pitchp", "rollp", "yawp")
_P233 = {
    1: (0, 0, 0), 2: (0, 0, 0), 3: (0, 0, 0),
    4: (-168058, 0, 0), 5: (-242054, 0, 0), 6: (-232918, 0, 0),
    7: (-9827, 0, 0), 8: (-79870, 0, 0), 9: (-94579, 0, 0),
    10: (-84029, 231147, -75000), 11: (-121027, 231147, -75000),
    12: (-116459, 200375, -65016),
    13: (0, 0, 0), 14: (0, 0, 0), 15: (0, 0, 0),
    16: (-217530, 0, 0), 17: (-260675, 0, 0), 18: (-225167, 0, 0),
    19: (-64716, -119206, -40387), 20: (-64716, 119206, 40387),
    21: (-105186, -121293, -65642), 22: (-105186, 121293, 65642),
    23: (-99232, -98238, -61927), 24: (-99232, 98238, 61927),
}


def _ga_reactions():
    """The Appendix A GA-6 gear reactions, keyed by the manual's case number."""
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    return {c.case: c for c in landing_reactions(_ga_landing(), _ga_gear(), lf,
                                                 _GA_CGS, mlw=_MLW, mtow=_MTOW)}


def _assert_page(table, cols, page, resolution=None):
    """Lock every transcribed cell of one printed page, and count them."""
    rx = _ga_reactions()
    n = 0
    for case, row in sorted(table.items()):
        for col, printed in zip(cols, row):
            if printed is None:
                continue          # column not printed for this family
            res = (resolution or {}).get(col, 1)
            # p232's SM column is the side load in the datum frame, which is
            # the ground-line one: a rotation about y leaves y alone. It is
            # carried on ``smp``/``snp`` by family, not under a second name.
            attr = col
            if col == "sm":
                attr = "smp" if case <= 24 else "snp"
            got = getattr(rx[case], attr)
            band = max(res / 2.0, abs(printed) * REL)
            assert abs(got - printed) <= band, (
                f"{page} case {case} {col.upper()}: printed {printed}, "
                f"sloads {got:.4f} (band +-{band:g})")
            n += 1
    return n


def test_landload_p231_ground_line_table():
    """Appendix A p231, every printed cell: all 33 cases, ground line.

    Reactions, resultants and the NVP/NDP/NS ground-line inertia factors for
    the level (1-12), braked-roll (13-18), side (19-24) and supplementary-nose
    (25-33) families. Until 2026-08-29 only cases 1 and 19 were locked here.
    """
    assert _assert_page(_P231, _P231_COLS, "p231", _P231_RES) == 300


def test_landload_p232_airplane_datum_table():
    """Appendix A p232, every printed force cell: all 33 cases, airplane datum.

    This is the frame the exported deck and the gear reference-point loads
    consume, and the one design note 38 (GF-1) holds open: the manual resolves
    the ground-roll families with ``+GRA`` where it resolves level and tail-down
    with ``-GRA``. These cells are what the port reproduces today and what a
    GF-1 correction would deviate from -- for cases 13-33, most of this table.

    The side column is asserted across both frames on purpose: the resolution
    is a rotation about the y axis, so SM is frame-invariant by construction.
    """
    assert _assert_page(_P232, _P232_COLS, "p232") == 147


def test_landload_p233_unbalanced_moments_table():
    """Appendix A p233, the ground-line LIMIT UNBALANCED MOMENTS columns.

    The independent reference §1.8 of note 38 discovered the hard way. It also
    re-checks the two 2026-08-29 fixes from outside their own formulas: case
    18's PITCHP is built from VMP(18)/DMP(18), so the pre-#135 reactions miss
    this printed cell by about 5 %.
    """
    assert _assert_page(_P233, _P233_COLS, "p233") == 72


def test_the_light_loading_never_takes_the_gross_weight_ratio():
    """``WR`` is applied to the two *max landing* loadings only.

    ``LANDLOAD.BAS`` states the exception three times (lines 860/870/900 and the
    23.499 branch at 2160-2180): the braked-roll, side and supplementary-nose
    families run at gross on ``WCG(1)``/``WCG(2)``, but the third (light)
    loading is already below the landing weight and is carried **bare** --
    ``WL(15) = WL(18) = WL(23) = WL(24) = WCG(3)``, and ``2.25*WCG(3)`` with no
    ``WR`` for cases 31-33.

    sloads applied ``WR`` to all three in the 13-18 loop, which overstated
    cases 15 and 18 by the ratio (2950.5 lb instead of 2803 on the GA6, VMP
    1962.1 instead of 1864.0). Found 2026-08-29 reading Appendix A p231 against
    the module: the printed VMP for case 18 is **1862** and its DMP **1490**,
    against 1962/1570 as shipped. The other three sites were already correct,
    so this pins the rule at every site rather than the one that was wrong.
    """
    inp = _ga_landing()
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    rx = {c.case: c for c in landing_reactions(inp, _ga_gear(), lf, _GA_CGS,
                                               mlw=_MLW, mtow=_MTOW)}
    light = _GA_CGS[2].weight_lb
    wr = _MTOW / _MLW
    assert wr > 1.0, "the GA6 fixture must exercise a non-unit WR"

    # Every case computed at the light loading reports it bare ...
    for m in (15, 18, 23, 24, 31, 32, 33):
        assert math.isclose(rx[m].weight_lb, light, rel_tol=1e-12), (
            f"case {m} runs at {rx[m].weight_lb}, not the bare light loading "
            f"{light} (LANDLOAD.BAS 860/870/900)")
    # ... while the two max-landing loadings in the same families take WR.
    for m, i in ((13, 0), (14, 1), (16, 0), (17, 1), (19, 0), (21, 1)):
        assert math.isclose(rx[m].weight_lb, _GA_CGS[i].weight_lb * wr,
                            rel_tol=1e-12), f"case {m} lost WR"

    # The consequence the printed table checks: cases 18, 23 and 24 share one
    # formula (0.5*1.33*WCG(3)), so they must print one number.
    assert math.isclose(rx[18].vmp, 0.5 * 1.33 * light, rel_tol=1e-12)
    assert math.isclose(rx[18].vmp, rx[23].vmp, rel_tol=1e-12)
    assert math.isclose(rx[18].vmp, rx[24].vmp, rel_tol=1e-12)
    assert math.isclose(rx[18].dmp, 0.8 * rx[18].vmp, rel_tol=1e-12)


def test_landload_case_formulas():
    """Closure on the FAR-section reaction formulas (LANDLOAD.BAS 910-1900)."""
    inp = _ga_landing()
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    g = _geometry(inp, _ga_gear(), _GA_NLG, _GA_CGS, _MLW)
    rx = {c.case: c for c in landing_reactions(inp, _ga_gear(), lf, _GA_CGS, mlw=_MLW, mtow=_MTOW)}
    nlg, k = _GA_NLG, g.k
    w1 = _GA_CGS[0].weight_lb
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
    assert math.isclose(rx[13].vnp, 1.33 * _GA_CGS[0].weight_lb
                        * (_MTOW / _MLW)
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
    unchanged. Covers the geometry-gear sync, which is the one remaining local-copy
    path: the derived gross-weight fallback it also used to cover left with
    ``landing.gross_weight_lb`` at decision G-14."""
    p = io.load_project(_GA)
    before = io.project_to_dict(p)
    build_landing(p)
    run(p)
    assert io.project_to_dict(p) == before, "build_landing/run mutated the project"


def test_landing_io_roundtrip():
    """The landing slice round-trips (the non-geometry LGFACTOR params); the gear
    geometry (Step G6b) round-trips under geometry.landing_gear, not the landing
    block; the weight/CG cases and both design weights round-trip under
    ``weight`` (G-3b / G-4 / G-14); older files migrate."""
    p = io.load_project(_GA)
    d = io.project_to_dict(p)
    p2 = io.project_from_dict(d)
    assert p2.landing.airplane_load_factor == 3.167
    assert landing_role_cases(p2)[0].xcg == 85.1
    assert p2.weight.max_landing_weight_lb == 3230
    assert p2.weight.max_takeoff_weight_lb == 3400
    for key in ("cg_cases", "gross_weight_lb", "max_landing_weight_lb"):
        assert key not in d["landing"], key
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
    loadings, so a project with no roled GROUND case (even with a mass slice
    present) raises a clear error rather than silently building a degenerate
    fwd/aft pair (M2-8), naming where they are entered (G-3)."""
    try:
        build_landing(Project(landing=_ga_landing(),
                              geometry=GeometryInput(surfaces=[_ga_wing()],
                                                     landing_gear=_ga_gear()),
                              weight=WeightInput(max_landing_weight_lb=_MLW,
                                                 max_takeoff_weight_lb=_MTOW)))
        raise AssertionError("expected ValueError for missing GROUND cases")
    except ValueError as e:
        assert "GROUND" in str(e) and "role" in str(e)


def _soft_strut_landing() -> LandingInput:
    """GA-6 gear with an over-soft oleo stroke so the *energy* N/NLG fall below
    the 23.473(g) floors (N < 2.67, NLG < 2.0), and no entered N, so the energy
    pair governs -- the trigger for the floor policy (note 37, LF-6)."""
    return replace(_ga_landing(), strut_stroke_in=25.0, airplane_load_factor=None)


def test_landing_473g_floor_warning_concept():
    """Concept mode notes the 23.473(g) floor when the governing pair sits below
    it (warn-only: the computed N/NLG are left untouched)."""
    lf, _ = build_landing(_ga_project(_soft_strut_landing(),
                                      speeds=StructuralSpeedsInput(category="C")))
    assert lf.airplane_load_factor < 2.67 and lf.gear_load_factor < 2.0
    mod = run(_ga_project(_soft_strut_landing(),
                          speeds=StructuralSpeedsInput(category="C")))
    note = mod.conditions[0].note
    assert "23.473(g)" in note and "N=" in note and "NLG=" in note


def test_landing_473g_floor_blocks_in_far23():
    """G-LF-4 (note 37, LF-6): a FAR 23 category (N/U/A) below the 23.473(g)
    floors is a named refusal, not a silent pass. It was warn-only *and*
    concept-only while N was derived and could not be wrong; a user-supplied N
    in a certificated category can be."""
    try:
        build_landing(_ga_project(_soft_strut_landing(),
                                  speeds=StructuralSpeedsInput(category="N")))
        raise AssertionError("expected the 23.473(g) refusal")
    except ValueError as e:
        assert "23.473(g)" in str(e) and "N=" in str(e)
    # An entered N below the floor is refused the same way -- the entry path is
    # the one that made the floor reachable in a FAR 23 category at all.
    try:
        build_landing(_ga_project(replace(_ga_landing(), airplane_load_factor=2.5),
                                  speeds=StructuralSpeedsInput(category="N")))
        raise AssertionError("expected the 23.473(g) refusal on an entered N")
    except ValueError as e:
        assert "23.473(g)" in str(e)


def test_landing_n_le_l_is_refused_by_name():
    """G-LF-4 (note 37, LF-5): with the L cap gone, ``N <= L`` is the one guard
    between ``K = NAP/NLG * K0`` and a zero or sign-flipped NLG."""
    lf = landing_load_factor(184.125, 3230, 7, 19, 7, 0.667, True)
    inp = replace(_ga_landing(), airplane_load_factor=0.5)
    try:
        landing_reactions(inp, _ga_gear(), lf, _GA_CGS, mlw=_MLW, mtow=_MTOW)
        raise AssertionError("expected the N <= L refusal")
    except ValueError as e:
        assert "N=" in str(e) and "L=" in str(e) and "NLG" in str(e)


def test_landing_473g_floor_constants_drift_guard():
    """Practice 3 (note 37, LF-6): the floors are regulation text with one code
    owner -- the constants and the policy function may not drift apart, and the
    numbers are 23.473(g)'s, not anyone's tuning."""
    from sloads.constants import FAR23_473G_N_FLOOR, FAR23_473G_NLG_FLOOR
    from sloads.modules.landing import far23_473g_floor_violations
    assert FAR23_473G_N_FLOOR == 2.67 and FAR23_473G_NLG_FLOOR == 2.0
    assert far23_473g_floor_violations(2.67, 2.0) == []
    both = far23_473g_floor_violations(2.669, 1.999)
    assert len(both) == 2 and "2.67" in both[0] and "2.0" in both[1]


def test_lift_factor_moves_the_gear_reaction():
    """G-LF-2 (note 37): the defect dies, stated as a test. Before the fix the
    stored NLG override made L **inert** on the vertical reaction -- raising L
    0.667 -> 1.0 at a fixed entered NLG changed *no wheel load at all* (the user
    changed the lift assumption and no reaction moved). At a fixed governing
    ``N``, NLG = N - L: raising L 0.667 -> 1.0 on ga6 lowers NLG 2.500 -> 2.167
    and every case-4-12 VMP by the same ratio, and raises K/gamma."""
    p = io.load_project(_GA)
    _, rx = build_landing(p)
    p.landing = replace(p.landing, lift_factor=1.0)
    lf2, rx2 = build_landing(p)
    from sloads.modules.landing import governing_load_factors
    n, nlg = governing_load_factors(p.landing, lf2)
    assert math.isclose(n, 3.167) and math.isclose(nlg, 2.167)
    by, by2 = {c.case: c for c in rx}, {c.case: c for c in rx2}
    for m in range(4, 13):
        assert math.isclose(by2[m].vmp / by[m].vmp, 2.167 / 2.5, rel_tol=1e-9), m
    # K rises with L at fixed N: K = NAP/NLG * K0 = (3.167/2.167)*0.256133
    # = 0.3743, gamma 20.52 deg (the note's printed 0.3586/19.72 was an
    # arithmetic slip, corrected with the note in this change).
    g = _geometry(p.landing, _ga_gear(), nlg, _GA_CGS, _MLW)
    assert math.isclose(g.k, 3.167 / 2.167 * 0.256133, rel_tol=1e-4), g.k
    assert math.isclose(g.gamma_deg, 20.522, rel_tol=1e-3), g.gamma_deg


def test_nvp_recovers_the_governing_n_on_every_example():
    """G-LF-3 (note 37): N is recoverable from the reactions -- ``NVP == N``
    exactly on the full-lift cases 4-9 and ``NVP == 0.5*NLG + L`` on the
    one-wheel cases 10-12, for every bundled example with a landing slice. The
    closure gate rule 2 requires with the feature."""
    from sloads.modules.landing import governing_load_factors
    checked = 0
    for name in sorted(os.listdir(_EXAMPLES)):
        if not name.endswith(".project.json"):
            continue
        p = io.load_project(os.path.join(_EXAMPLES, name))
        if p.landing is None:
            continue
        lf, rx = build_landing(p)
        n, nlg = governing_load_factors(p.landing, lf)
        by = {c.case: c for c in rx}
        for m in range(4, 10):
            assert math.isclose(by[m].nvp, n, rel_tol=1e-9), (name, m)
        for m in range(10, 13):
            assert math.isclose(by[m].nvp, 0.5 * nlg + p.landing.lift_factor,
                                rel_tol=1e-9), (name, m)
        checked += 1
    assert checked >= 6, "the bundled fleet shrank"


def test_below_energy_caution_fires_on_cessna_not_ga6():
    """G-LF-6's caution half (note 37, LF-7): cessna_210 enters N = 3.167 below
    its computed 3.3885 and is told so; ga6 enters 3.167 above its 3.0951 and is
    not. One owner (``below_energy_caution``) serves both GUIs."""
    from sloads.modules.landing import below_energy_caution
    assert below_energy_caution(io.load_project(_GA)) is None
    caution = below_energy_caution(
        io.load_project(os.path.join(_EXAMPLES, "cessna_210.project.json")))
    assert caution is not None and "3.1670" in caution and "3.3885" in caution


def test_lift_factor_caption_is_shared_by_both_guis():
    """G-LF-6's caption half: the FAR-defaults guidance is enumerated once
    (``app_shell.components.LANDING_L_FAR_CAPTION``) and both GUIs consume that
    symbol -- the L widget carries no cap in either."""
    from app_shell.components import LANDING_L_FAR_CAPTION
    assert "0.667" in LANDING_L_FAR_CAPTION and "23.473" in LANDING_L_FAR_CAPTION
    assert "1.0" in LANDING_L_FAR_CAPTION and "25.473(a)(2)" in LANDING_L_FAR_CAPTION
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in (os.path.join("app", "views", "landing_loads.py"),
                os.path.join("oracle_app", "form.py")):
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            assert "LANDING_L_FAR_CAPTION" in fh.read(), rel


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
    g = _geometry(inp, _ga_gear(), _GA_NLG, _GA_CGS, _MLW)
    rx = {c.case: c for c in landing_reactions(inp, _ga_gear(), lf, _GA_CGS, mlw=_MLW, mtow=_MTOW)}
    wr = _MTOW / _MLW
    # 2-wheel level (4) and tail-down (7): -2 * RMP * BP for the attitude/CG pair.
    assert math.isclose(rx[4].pitchp, -2 * rx[4].rmp * g.bp[0][0], rel_tol=1e-9)
    assert math.isclose(rx[7].pitchp, -2 * rx[7].rmp * g.bp[2][0], rel_tol=1e-9)
    # One-wheel (10): a single wheel, so -1 * RMP * BP, plus roll/yaw about the tread.
    assert math.isclose(rx[10].pitchp, -1 * rx[10].rmp * g.bp[0][0], rel_tol=1e-9)
    assert math.isclose(rx[10].rollp, rx[10].vmp * _ga_gear().tread_in / 2, rel_tol=1e-9)
    assert math.isclose(rx[10].yawp, -rx[10].dmp * _ga_gear().tread_in / 2, rel_tol=1e-9)
    # Braked roll nose clear (16): the drag reaction acts at the CP vertical offset.
    assert math.isclose(rx[16].pitchp,
                        -2 * (rx[16].vmp * g.bp[1][0] + rx[16].dmp * g.cp[1][0]), rel_tol=1e-9)
    # Side load (19/20): pitch from the vertical only; roll/yaw are the 0.83 W couple,
    # signed by the drift direction (odd case = left drift).
    w19 = _GA_CGS[0].weight_lb * wr
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
    rx = {c.case: c for c in landing_reactions(inp, _ga_gear(), lf, _GA_CGS, mlw=_MLW, mtow=_MTOW)}
    lift, wr = inp.lift_factor, _MTOW / _MLW
    w1 = _GA_CGS[0].weight_lb
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
    keys = {v.key for v in matrix[0].values}
    for expected in ("unbalanced_pitching_moment", "unbalanced_rolling_moment",
                     "unbalanced_yawing_moment", "vertical_inertia_factor_nvp",
                     "drag_inertia_factor_ndp", "side_inertia_factor_ns"):
        assert expected in keys, expected
    # Cases 25-33 are nose-only (no main reaction, moment or inertia factor).
    nose_only = [c for c in matrix if c.title.startswith("supplementary")]
    assert len(nose_only) == 9
    assert {v.key for v in nose_only[0].values} == {
        "vertical_nose", "drag_nose", "side_nose", "resultant_nose"}
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
    rx = landing_reactions(inp, _ga_gear(), lf, _GA_CGS, mlw=_MLW, mtow=_MTOW)
    for far, case in (("23.479(a)", 4), ("23.481", 7), ("23.483", 10),
                      ("23.485", 19), ("23.493", 16), ("23.499", 28)):
        assert _critical(rx, far).case == case, (far, _critical(rx, far).case)
    # With an inflated side load on case 22 the pick must follow it; the old
    # max(rmp, result) ranking could not see SMP at all.
    boosted = [_replace(c, smp=c.smp * 10) if c.case == 22 else c for c in rx]
    assert _critical(boosted, "23.485").case == 22


def test_the_role_fixes_the_order_not_the_name(tmp_path):
    """Decision G-3a: LANDLOAD's positional contract is now ``CgCase.role``.

    The failure this replaces was silent. The three loadings are consumed
    positionally (``wl[19] = wcg[0]*wr``), the order used to be recovered by
    matching names against a canonical triple, and a *renamed* case fell back to
    entry order with only a warning -- so renaming a row reordered an
    oracle-locked reaction table. With the role explicit, a shuffled list gives
    identical reactions and renaming changes nothing at all.
    """
    p = io.load_project(_GA)
    ordered = build_landing(p)[1]

    shuffled = io.load_project(_GA)
    cases = shuffled.weight.cg_cases
    ground = [c for c in cases if c.role is not None]
    shuffled.weight.cg_cases = ([c for c in cases if c.role is None]
                                + [ground[2], ground[0], ground[1]])
    assert [c.vmp for c in build_landing(shuffled)[1]] == [c.vmp for c in ordered]

    renamed = io.load_project(_GA)
    renamed.weight.cg_cases = [
        replace(c, name=f"loading {i}") if c.role is not None else c
        for i, c in enumerate(renamed.weight.cg_cases)]
    assert [c.vmp for c in build_landing(renamed)[1]] == [c.vmp for c in ordered]


def test_a_missing_or_duplicated_role_raises_rather_than_padding():
    """The role contract refuses; it never reorders or pads to three."""
    p = io.load_project(_GA)
    p.weight.cg_cases = [c for c in p.weight.cg_cases
                         if c.role != GroundCaseRole.FWD_LIGHT]
    try:
        build_landing(p)
        raise AssertionError("expected a ValueError for the missing role")
    except ValueError as e:
        assert "fwd_light" in str(e)


def test_the_page_refuses_to_compute_without_a_waterline():
    """M4-17c, re-armed for G-3: a landing case with no waterline blocks the page.

    The CG table moved to the Weight/CG page at decision G-3, so this no longer
    tests a seed -- it tests the gate that survived it. The page must name the
    incomplete case and refuse, rather than computing on a zero waterline, which
    puts the CG on the ground line, inverts the nose-gear reaction and inflates
    the braked-roll main loads ~2.6x.

    Driven through ``AppTest`` (the view is a page script, not an importable
    module; same precedent as tests/test_dirty_flag.py).
    """
    try:   # the zero-dependency __main__ runner has neither pytest nor streamlit
        from streamlit.testing.v1 import AppTest
    except ImportError:  # pragma: no cover - exercised only by the fallback runner
        print("SKIP test_the_page_refuses_to_compute_without_a_waterline (no streamlit)")
        return

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # conftest.py does this under pytest; repeat it so the __main__ runner can resolve
    # the view's shared ``app_shell`` import too.
    if root not in sys.path:
        sys.path.insert(0, root)
    view = os.path.join(root, "app", "views", "landing_loads.py")
    p = io.load_project(_GA)
    p.weight.cg_cases = [replace(c, zcg=0.0) if c.role is not None else c
                         for c in p.weight.cg_cases]

    at = AppTest.from_file(view, default_timeout=60)
    at.session_state["project"] = p
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    blocked = " ".join(i.value for i in at.info)
    assert "Zcg waterline" in blocked, blocked
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
