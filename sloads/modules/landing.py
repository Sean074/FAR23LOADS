"""Landing / ground loads, from LGFACTOR.BAS and LANDLOAD.BAS (Reference 1 Ch 20).

Two programs cover the FAR Part 23 Subpart C ground-load conditions:

**LGFACTOR** (FAR 23.473(d)-(g)) estimates the landing load factor from the
drop-test work-energy balance. The limit descent velocity is the FAR 23.473(d)
formula ``V = 4.4*(W/S)^0.25`` clamped to ``7 <= V <= 10`` fps; the flat-tyre
deflection is ``(OD - hub)/6`` inches and the strut stroke ``SSTRUT``. With tyre
and strut energy efficiencies (0.3 tyre; 0.5 spring / 0.75 oleo) the airplane
load factor is the absorbed-energy ratio::

    N = [W*V^2/(2g) + W*(1-L)*(SSTRUT + d_tire)/12]
        / [W*(eta_tire*d_tire + eta_strut*SSTRUT)/12]

and the landing-gear factor is ``NLG = N - L``.

The *governing* pair the reaction solve runs at is owned by
``governing_load_factors`` (note 37): ``N`` is the entered
``landing.airplane_load_factor`` when filled (the manual's LANDLOAD runs at a
rounded design N -- 3.167 on p230), else the energy value, and ``NLG = N - L``
is always derived, so the wing lift factor moves the reaction. The FAR 23.473(g)
floors (``far23_473g_floor_violations``) refuse in a FAR 23 category and warn in
concept.

**LANDLOAD** (FAR 23.473-23.499) computes the tricycle-gear reaction loads for the
level (3-wheel and 2-wheel), tail-down, one-wheel, braked-roll, side and
supplementary-nose-wheel ground conditions. The drag load factor of FAR 23
Appendix C is scaled by the airplane/gear load-factor ratio to give drag as if no
lift were assumed (``K = NAP/NLG * K0``); the lever arms ``AP/BP/DP/CP`` of
Appendix C Fig C23.1 are formed for each attitude and CG, then the per-wheel
vertical / drag / side reactions follow per FAR section.

Reads the three explicit per-CG loadings as the **roled ``GROUND`` weight/CG
cases** of the one shared list (decision G-3/G-3a; required since M2-8 -- **not**
derived from ``Project.mass``, which this module does not read at all, so the
landing workflow step requires no ``mass`` slice: M4-17a), both design weights
from their single owners on ``WeightInput`` (G-4 / G-14), the gear strut geometry
from ``Project.geometry.landing_gear`` (Step G6b) and the wing area from
``Project.geometry`` when not given explicitly.
**Tricycle gear only** (UG Table 2.1).

``run`` emits the LGFACTOR condition, one critical-reaction summary per FAR ground
family, **and** the full 33-case reaction matrix, so the ULTIMATE deliverable
(CSV / Review / Export) carries every case the LIMIT analysis screen shows,
including the unbalanced moments and the ground-line inertia factors (M4-17e).

Reference: LGFACTOR.BAS (Appendix C p483), LANDLOAD.BAS (Appendix C p468); Ref 1
Ch 20 p126-130; oracles Appendix A "Landing Load Factor" p236
(V 9.0048 / N 3.0951 / NLG 2.4281) and "Landing Loads with Respect to Ground Line"
p230 (K 0.324 / GAMMA 17.978 / the AP-BP-DP-CP lever-arm table).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, NamedTuple, Optional, Sequence, Tuple

from ..basic import basic_trunc3
from ..case_ids import CaseIdAllocator
from ..cg_cases import landing_role_cases, max_landing_weight, max_takeoff_weight
from ..constants import FAR23_473G_N_FLOOR, FAR23_473G_NLG_FLOOR, IN_PER_FT, G
from ..frames import (
    AIRPLANE_DATUM,
    GROUND_LINE,
    caption,
    rotation_deg,
    to_airplane_datum,
)
from ..models import (
    STRUT_TYPES,
    CaseRef,
    CgCase,
    ConditionResult,
    GearReactionCase,
    LandingGearGeometry,
    LandingInput,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    normalise_code,
)
from ..picks import extreme
from ..registry import register

if TYPE_CHECKING:            # pragma: no cover - typing only
    from ..gear_loads import DeliveredLeg

MODULE_NAME = "landing"

ETA_TIRE = 0.3
ETA_SPRING = 0.5
ETA_OLEO = 0.75


class LoadFactorResult(NamedTuple):
    """LGFACTOR output: sink rate (fps), airplane load factor N, gear factor NLG."""
    sink_rate_fps: float
    airplane_load_factor: float    # N
    gear_load_factor: float        # NLG = N - L


def landing_load_factor(wing_area_sqft: float, weight_lb: float, strut_stroke_in: float,
                        tire_od_in: float, hub_diameter_in: float, lift_factor: float,
                        main_is_oleo: bool) -> LoadFactorResult:
    """Estimate the landing load factor (LGFACTOR.BAS lines 40-160).

    ``lift_factor`` (L) is a free number (note 37, LF-4: 0.667 is the FAR 23.473
    default, 1.0 the FAR 25.473(a)(2) basis -- guidance, not a cap); the descent
    velocity is clamped to 7-10 fps per FAR 23.473(d). Returns the sink rate,
    airplane load factor N and landing-gear factor ``NLG = N - L``."""
    if wing_area_sqft <= 0 or weight_lb <= 0:
        raise ValueError("LGFACTOR needs positive wing area and landing weight")
    v = 4.4 * (weight_lb / wing_area_sqft) ** 0.25
    v = min(10.0, max(7.0, v))
    d_tire = (tire_od_in - hub_diameter_in) / 6.0    # flat-tyre deflection, in
    eta_strut = ETA_OLEO if main_is_oleo else ETA_SPRING
    numerator = (weight_lb * v ** 2 / (2.0 * G)
                 + weight_lb * (1.0 - lift_factor) * (strut_stroke_in + d_tire) / IN_PER_FT)
    denominator = weight_lb * (ETA_TIRE * d_tire + eta_strut * strut_stroke_in) / IN_PER_FT
    if denominator <= 0:
        raise ValueError("LGFACTOR strut/tyre stroke must be positive")
    n = numerator / denominator
    return LoadFactorResult(sink_rate_fps=v, airplane_load_factor=n,
                            gear_load_factor=n - lift_factor)


def governing_load_factors(inp: LandingInput,
                           lf_result: LoadFactorResult) -> Tuple[float, float]:
    """The governing ``(N, NLG)`` the reaction solve runs at (note 37, LF-1/LF-3).

    ``N`` is ``inp.airplane_load_factor`` when entered (the manual's LANDLOAD runs
    at a rounded design N -- 3.167 on p230, where LGFACTOR's energy value is
    3.095), else the energy value; ``NLG = N - L`` is derived here and nowhere
    else, so the wing lift factor L always moves the gear reaction. Refuses
    ``N <= L`` by name (LF-5): with the L cap gone that is the only guard between
    ``K = NAP/NLG * K0`` and a zero or negative NLG.
    """
    n = (inp.airplane_load_factor if inp.airplane_load_factor is not None
         else lf_result.airplane_load_factor)
    if n <= inp.lift_factor:
        raise ValueError(
            f"landing N must exceed the wing lift factor L: N={n:.4f}, "
            f"L={inp.lift_factor:.4f} gives NLG = N - L = {n - inp.lift_factor:.4f}, "
            "and the gear reaction solve needs NLG > 0 (K = NAP/NLG * K0)")
    return n, n - inp.lift_factor


def far23_473g_floor_violations(n: float, nlg: float) -> List[str]:
    """The FAR 23.473(g) floors, stated once (note 37, LF-6; practice 3).

    Returns one message per floor the governing pair sits below (empty = clear).
    The *policy* -- refuse in a FAR 23 category, warn in concept -- is applied by
    ``build_landing``/``run`` on this single owner's output; the numbers live in
    ``constants.py`` with the drift guard in ``tests/test_landing.py``.
    """
    floors = []
    if n < FAR23_473G_N_FLOOR:
        floors.append(f"N={n:.3f} < {FAR23_473G_N_FLOOR}")
    if nlg < FAR23_473G_NLG_FLOOR:
        floors.append(f"NLG={nlg:.3f} < {FAR23_473G_NLG_FLOOR}")
    return floors


# Drag load factor K0 of FAR 23 Appendix C 23.1 (interpolated 0.25 -> 0.33).
def _appendix_c_k0(weight_lb: float) -> float:
    if weight_lb <= 3000:
        return 0.25
    if weight_lb >= 6000:
        return 0.33
    return 0.25 + (weight_lb - 3000) / (6000 - 3000) * (0.33 - 0.25)


class _Geometry(NamedTuple):
    """LANDLOAD landing-gear geometry intermediates (LANDLOAD.BAS lines 50-720)."""
    k: float                       # drag load factor (lift-corrected)
    gamma_deg: float               # arctan(K)
    gra: Tuple[float, float, float]   # ground angle: level, ground-roll, tail-down (deg)
    beta: Tuple[float, float, float]  # resultant-to-FS angle per attitude (deg)
    # ap/bp/dp[j][i]: lever arms for attitude j (0 level, 1 roll, 2 tail-down) and CG i
    ap: List[List[float]]
    bp: List[List[float]]
    dp: List[List[float]]
    cp: List[List[float]]          # ground-roll vertical offset (attitude 1 only)


def _ground_angle(xm: float, zm: float, xn: float, zn: float,
                  rm: float, rn: float) -> float:
    """The ground angle for one attitude: the slope of the axle line less the
    slope of the wheel-contact line (LANDLOAD.BAS lines 50-720).

    Module-level, and read by :func:`sloads.gear_loads.ground_angles` as well as
    by :func:`_geometry`, because the gear load report puts the **contact patch**
    at ``x + r*sin(GRA)`` / ``z - r*cos(GRA)`` and therefore needs the same angle
    the reaction was computed at. A second copy of this formula beside the report
    is exactly the drift ``CLAUDE.md`` practice 3 forbids -- and it would be a
    quiet one, since both copies would look right and differ only in which axle
    state they were handed.
    """
    return math.degrees(
        math.atan((zm - zn) / (xm - xn))
        - math.atan((rm - rn) / (((xm - xn) ** 2 + (zm - zn) ** 2) ** 0.5)))


def ground_angles(inp: LandingInput, gear: LandingGearGeometry
                  ) -> Tuple[float, float, float]:
    """``GRA(1..3)`` -- the ground angle in each of LANDLOAD's three attitudes.

    ``(level, ground-roll, tail-down)``, in degrees. The first two are geometry
    (the compressed and static axle states); the third is the entered tail-down
    bump angle. Independent of weight, CG and load factor, which is why this can
    be asked of the input slice alone -- the gear report needs the angles without
    re-running the reaction solve.
    """
    mg, ng = gear.main_gear, gear.nose_gear
    rm, rn = mg.rolling_radius_in, ng.rolling_radius_in
    return (_ground_angle(*mg.axle_compressed, *ng.axle_compressed, rm, rn),
            _ground_angle(*mg.axle_static, *ng.axle_static, rm, rn),
            inp.tail_down_angle_deg)


def _geometry(inp: LandingInput, gear: LandingGearGeometry, nlg: float,
              cgs: List[CgCase], mlw: float) -> _Geometry:
    """Ground angles, BETA and the AP/BP/DP/CP lever arms (LANDLOAD.BAS 50-720)."""
    nap = nlg + inp.lift_factor
    k0 = _appendix_c_k0(mlw)
    k = nap / nlg * k0
    gamma = math.degrees(math.atan(k))

    mg, ng = gear.main_gear, gear.nose_gear
    xm_c, zm_c = mg.axle_compressed
    xn_c, zn_c = ng.axle_compressed
    xm_s, zm_s = mg.axle_static
    xn_s, zn_s = ng.axle_static
    rm, rn = mg.rolling_radius_in, ng.rolling_radius_in

    gra1, gra2, gra3 = ground_angles(inp, gear)
    gra = (gra1, gra2, gra3)
    # BETA is the **resultant-to-FS angle** for each attitude, and Appendix A
    # p234 states the rule the whole table follows:
    #
    #     BETA = GAMMA - GROUND ANGLE
    #
    # with GAMMA = arctan(K) where the drag tilts the resultant (level), and
    # GAMMA = 0 for the ground-roll and tail-down attitudes, whose reaction is
    # normal to the ground and whose drag rides the separate .8*CP term.
    # Positive GROUND ANGLE is nose-up: all three attitudes come from the same
    # axle geometry rising aft, and a tail-down landing -- unambiguously nose-up
    # -- is the entered +15.
    #
    # LANDLOAD.BAS writes ``(GAMMA-GRA(1), +GRA(2), +GRA(3))``, carrying the
    # wrong sign on attitudes 2 and 3. Attitude 3 negates it back at *both* its
    # use sites (BP longhand, PHIM = -BETA(3)) and so comes out right; attitude 2
    # negates it at neither, so its lever arms *and* its PHIM/PHIN are both
    # wrong. Corrected here, at the origin, rather than at the use sites --
    # design note 38 GF-1/GF-2', AGREED 2026-08-29; approved-deviation register
    # entry in docs/20_theory/02_approved_corrections.md.
    #
    # The manual's own braked-roll figure (p235) prints the corrected arms:
    # AP 77.052 / BP 17.760 / DP 94.811, against its p230 table's 69.886 /
    # 23.260 / 93.147. CP is unchanged (it enters through cos, and is even).
    beta = (gamma - gra1, -gra2, -gra3)

    def fn_ap(xcg, xn, b, zcg, zn):
        return ((xcg - xn) * math.cos(math.radians(b))
                - (zcg - zn) * math.sin(math.radians(b)))

    def fn_bp(xm, xcg, b, zcg, zm):
        return ((xm - xcg) / math.cos(math.radians(b))
                + ((zcg - zm) - (xm - xcg) * math.tan(math.radians(b)))
                * math.sin(math.radians(b)))

    def fn_dp(xm, xn, b, zm, zn):
        return ((xm - xn) * math.cos(math.radians(b))
                - (zm - zn) * math.sin(math.radians(b)))

    n_cg = len(cgs)
    ap = [[0.0] * n_cg for _ in range(3)]
    bp = [[0.0] * n_cg for _ in range(3)]
    dp = [[0.0] * n_cg for _ in range(3)]
    cp = [[0.0] * n_cg for _ in range(3)]

    # Attitude 0 -- 3-/2-point level (compressed axle positions).
    for i, cg in enumerate(cgs):
        ap[0][i] = fn_ap(cg.xcg, xn_c, beta[0], cg.zcg, zn_c)
        bp[0][i] = fn_bp(xm_c, cg.xcg, beta[0], cg.zcg, zm_c)
        dp[0][i] = fn_dp(xm_c, xn_c, beta[0], zm_c, zn_c)
    # Attitude 2 -- tail down (only BP; vertical reactions, GRA(3)). This was
    # written longhand with a negated second term, which is ``fn_bp`` at
    # ``-GRA(3)`` -- the compensation that hid the ``beta`` sign error on this
    # attitude. With ``beta[2]`` corrected the compensation is redundant, and
    # the arm goes through the same ``fn_bp`` as every other attitude. The
    # numbers are unchanged: this is a consolidation, not a behaviour change.
    for i, cg in enumerate(cgs):
        bp[2][i] = fn_bp(xm_c, cg.xcg, beta[2], cg.zcg, zm_c)
    # Attitude 1 -- ground roll (static axle positions), plus the CP vertical offset.
    for i, cg in enumerate(cgs):
        ap[1][i] = fn_ap(cg.xcg, xn_s, beta[1], cg.zcg, zn_s)
        bp[1][i] = fn_bp(xm_s, cg.xcg, beta[1], cg.zcg, zm_s)
        dp[1][i] = fn_dp(xm_s, xn_s, beta[1], zm_s, zn_s)
        zt = zn_s - rn * math.cos(math.radians(gra2))
        xt = xn_s + rn * math.sin(math.radians(gra2))
        zl = zm_s - rm * math.cos(math.radians(gra2))
        xl = xm_s + rm * math.sin(math.radians(gra2))
        zs = zt + (cg.xcg - xt) * (zl - zt) / (xl - xt)
        cp[1][i] = (cg.zcg - zs) * math.cos(math.radians(gra2))

    # The BASIC truncates the printed AP/BP/DP/CP to 3 decimals (lines 780-790).
    for tbl in (ap, bp, dp, cp):
        for j in range(3):
            for i in range(n_cg):
                tbl[j][i] = basic_trunc3(tbl[j][i])
    return _Geometry(k=k, gamma_deg=gamma, gra=gra, beta=beta, ap=ap, bp=bp, dp=dp, cp=cp)


# Case metadata: (1-based case, attitude index j, CG index i, family, FAR ref).
# Attitude j: 0 level, 1 ground-roll, 2 tail-down.
_MAIN_FAMILIES = {
    range(1, 4): ("3-wheel level landing", "23.479(a)"),
    range(4, 7): ("2-wheel level landing (nose clear)", "23.479(a)"),
    range(7, 10): ("tail-down landing", "23.481"),
    range(10, 13): ("one-wheel landing", "23.483"),
    range(13, 16): ("braked roll (nose down)", "23.493"),
    range(16, 19): ("braked roll (nose clear)", "23.493"),
    range(19, 25): ("side load", "23.485"),
}
_NOSE_FAMILY = ("supplementary nose-wheel", "23.499")


#: The LANDLOAD case families, as ranges over the manual's own 1..33 numbering.
#: They live here because this module *is* the case numbering -- ``_family``,
#: ``_loading_index`` and the reaction loops below draw exactly these lines, and
#: the ``lf*WL`` term in ``nvp`` is applied to precisely
#: :data:`GROUND_LIFT_CASES`. They used to be declared in ``modules/balance.py``,
#: beside the deck that consumes them and away from the code that draws them
#: (design note 38 GF-6, #134: the datum load factors need the lift split, and a
#: second copy of it in this file would have been the drift practice 3 forbids).
#: ``balance`` and ``gear_loads`` import them from here.

#: The families that carry wing lift: 23.479/481/483 (the airplane is still
#: flying). **The regulation draws the same line** -- 23.473(a) lets these be met
#: at the design landing weight, which is why LANDLOAD scales them differently
#: from the gross-weight 23.485/23.493 families. The family split, the lift split
#: and the weight split are one split.
GROUND_LIFT_CASES = range(1, 13)

#: The 23.483 one-wheel family: a single main gear carries the whole reaction, so
#: the case has a hand and LANDLOAD supplies **neither** twin (there is no sign
#: flip anywhere in cases 10-12 -- they are the three loadings, one hand each).
GROUND_ONE_WHEEL_CASES = range(10, 13)

#: The 23.485 side family: three loadings x **two drift directions**, so LANDLOAD
#: supplies **both** hands. Only the odd member of each pair is assembled and the
#: even one becomes an independent check on the reflection operator (G-8).
GROUND_SIDE_CASES = range(19, 25)

#: The ground families the assembled deck carries: 1-24. The 23.499 supplementary
#: nose-wheel family (25-33) is deliberately absent -- it is a gear-design case
#: with no airplane in equilibrium (``balance.SKIP_REASONS``' ``gear-design-only``),
#: which is also why it carries no datum load factors.
BALANCED_GROUND_CASES = range(1, 25)


#: Which strut state and which ground angle each LANDLOAD case is computed at
#: (G-12), beside the rest of the case-family knowledge it belongs with. It
#: lived in ``gear_loads`` until design note 38 GF-6 (#134), which needs the
#: attitude here to state p231's FUSELAGE AXIS ANGLE per case.
#: ``(strut state, ground-angle index)`` where the index is into
#: :func:`ground_angles`' ``(level, ground-roll, tail-down)``. Cases 1-12 are
#: the landing attitudes and use the **compressed**
#: axle; 13-33 are the handling ones and use the **static** axle -- the manual's
#: own split, followed rather than re-decided.
_ATTITUDES: Tuple[Tuple[range, str, int], ...] = (
    (range(1, 7), "compressed", 0),      # level 3-/2-wheel
    (range(7, 10), "compressed", 2),     # tail-down
    (range(10, 13), "compressed", 0),    # one-wheel
    (range(13, 34), "static", 1),        # braked roll, side, supplementary nose
)


def attitude_of(case: int) -> Tuple[str, int]:
    """``(strut state, ground-angle index)`` for LANDLOAD case number ``case``.

    Raises for a case outside 1-33 rather than defaulting: an unmapped case would
    silently take the last attitude in the table, which is the class of error a
    lookup with a fallback always produces.
    """
    for rng, state, gra_index in _ATTITUDES:
        if case in rng:
            return state, gra_index
    raise ValueError(f"no ground attitude for LANDLOAD case {case!r} (expected 1-33)")


def side_partner(case: int) -> Optional[int]:
    """The other drift direction of a 23.485 pair, or ``None`` outside the family.

    The pairs are ``(19, 20)``, ``(21, 22)``, ``(23, 24)`` -- three loadings x two
    directions, so the partner of an odd member is the next case and of an even
    member the previous one. LANDLOAD needs the pairing twice over: ``NNS`` is
    ``(SMP - SMP_partner)/WL`` (the two wheels of one airplane carry *different*
    side loads, 0.5 W inboard and 0.33 W outboard, acting the same way globally),
    and the assembled deck reads the partner's ``SMP`` for its second wheel
    rather than re-deriving the percentages. One owner, because ``case + 1`` is
    right for half the family and wrong for the other half.
    """
    if case not in GROUND_SIDE_CASES:
        return None
    return case + 1 if case % 2 else case - 1


def _family(case: int) -> Tuple[str, str]:
    for rng, fam in _MAIN_FAMILIES.items():
        if case in rng:
            return fam
    return _NOSE_FAMILY


def _loading_index(case: int) -> int:
    """Which of the three roled loadings case ``case`` is computed at.

    The single owner of a mapping LANDLOAD.BAS states three times -- in the ``WL``
    weight table (lines 820-900), in the ``AP``/``BP``/``CP`` lever-arm lookups and
    in the unbalanced-moment tables -- and which is **not** a simple 3-cycle
    throughout:

    * **1-18** cycle the three loadings, so ``(m - 1) % 3``;
    * **19-24** are three loadings x **two drift directions** (23.485's inboard/
      outboard pair), so ``(m - 19) // 2``: cases 19/20 share the aft loading,
      21/22 the forward one, 23/24 the light one -- exactly what ``wl[19] =
      wl[20] = wcg[0]*wr`` and the ``((19,0),(20,0),(21,1),(22,1),(23,2),(24,2))``
      moment tables already say;
    * **25-33** are three loadings x three components, so ``(m - 25) // 3``.

    **This corrects a mislabelling** (found 2026-08-15, building the assembled
    ground cases). The per-case record took ``(m - 1) % 3`` for every case up to
    24, so on the side family it named the wrong loading on **five of six cases**
    -- case 21 is computed at the *forward max landing* loading and was reported
    against *fwd light*, and so on. ``cg_name`` was documented as cosmetic and
    the reactions themselves were always right, so no load ever moved; what moved
    is the label a reader joins the case to its loading by, and the ``CG`` column
    of the exported case index. Assembling these cases is what made it matter:
    the balanced case has to build its inertia set at the loading its reactions
    were computed at, and it asks here.
    """
    if case <= 18:
        return (case - 1) % 3
    if case <= 24:
        return (case - 19) // 2
    return (case - 25) // 3


def landing_reactions(inp: LandingInput, gear: LandingGearGeometry,
                      lf_result: LoadFactorResult,
                      cgs: List[CgCase], *, mlw: float,
                      mtow: float) -> List[GearReactionCase]:
    """The 24 main-wheel + 33 nose-wheel ground-condition reactions (LANDLOAD.BAS).

    ``cgs`` is the ordered [aft-max-landing, fwd-max-landing, fwd-light] loading;
    LANDLOAD cycles the three through each condition family. **The order is the
    contract** -- the weight tables below index ``cgs`` positionally, and the
    ``cg_name`` carried on each record is cosmetic. The order comes from each
    case's explicit ``role`` (decision G-3a), resolved by
    :func:`sloads.cg_cases.landing_role_cases`.

    ``mlw`` and ``mtow`` are the two design weights, passed in from their single
    owners on ``WeightInput`` (G-4 / G-14) rather than read off this slice: ``mlw``
    is the reduced landing weight of 23.473(b)/(c) and sets ``K0``, and the ratio
    ``WR = mtow/mlw`` scales cases 13-22 to the take-off weight."""
    if len(cgs) != 3:
        raise ValueError("LANDLOAD needs exactly 3 CG cases (aft/fwd max landing, fwd light)")
    _, nlg = governing_load_factors(inp, lf_result)
    lf = inp.lift_factor
    geo = _geometry(inp, gear, nlg, cgs, mlw)
    k = geo.k
    ap, bp, dp, cp = geo.ap, geo.bp, geo.dp, geo.cp
    wr = mtow / mlw if mlw else 1.0
    wcg = [cg.weight_lb for cg in cgs]

    # Per-case weight WL (1-based index 1..24), LANDLOAD.BAS lines 820-900.
    # The braked-roll and side cases run at gross (WR = GW/MLW) on the two *max
    # landing* loadings only -- the third (light) loading is already below the
    # landing weight, so lines 860/870/900 carry it bare: WL(15), WL(18), WL(23)
    # and WL(24) are WCG(3) with no WR. The same exception is spelled out again
    # in the supplementary-nose branch below (2.25*WCG*WR only for i < 2).
    wl = [0.0] * 25
    for m in range(1, 13):
        wl[m] = wcg[(m - 1) % 3]
    for m in range(13, 19):
        i = (m - 13) % 3
        wl[m] = wcg[i] * (wr if i < 2 else 1.0)
    wl[19] = wl[20] = wcg[0] * wr
    wl[21] = wl[22] = wcg[1] * wr
    wl[23] = wl[24] = wcg[2]

    # --- Main-wheel reactions (per wheel) -------------------------------------
    vmp = [0.0] * 25
    for m in (1, 2, 3):                         # 3-wheel level
        i = m - 1
        vmp[m] = 0.5 * nlg * wl[m] * ap[0][i] / dp[0][i]
    for m in range(4, 13):                       # 2-wheel level / tail-down / one-wheel
        vmp[m] = 0.5 * nlg * wl[m]
    for m in (13, 14, 15):                       # braked roll nose down
        i = m - 13
        vmp[m] = 0.5 * 1.33 * wl[m] * ap[1][i] / (0.8 * cp[1][i] + dp[1][i])
    for m in range(16, 25):                      # braked nose clear + side load
        vmp[m] = 0.5 * 1.33 * wl[m]

    dmp = [0.0] * 25
    for m in list(range(1, 7)) + list(range(10, 13)):   # K*VMP (level / one-wheel)
        dmp[m] = k * vmp[m]
    for m in range(13, 19):                              # braked: 0.8*VMP
        dmp[m] = 0.8 * vmp[m]
    # cases 7-9 (tail-down) and 16-24 keep DMP=0 except braked above.

    smp = [0.0] * 25
    smp[19] = -0.5 * wl[19]
    smp[20] = 0.33 * wl[20]
    smp[21] = -0.5 * wl[21]
    smp[22] = 0.33 * wl[22]
    smp[23] = -0.5 * wl[23]
    smp[24] = 0.33 * wl[24]

    rmp = [(_sq(vmp[m]) + _sq(dmp[m])) ** 0.5 for m in range(25)]

    # --- Nose-wheel reactions (33 cases) --------------------------------------
    vnp = [0.0] * 34
    for m in (1, 2, 3):
        i = m - 1
        vnp[m] = nlg * wl[m] * bp[0][i] / dp[0][i]
    for m in (13, 14, 15):
        vnp[m] = 1.33 * wl[m] - 2 * vmp[m]
    # Supplementary nose-wheel (23.499): aft 25/28/31, fwd 26/29/32, side 27/30/33.
    for base, i in ((25, 0), (28, 1), (31, 2)):
        vnp[base] = vnp[base + 1] = vnp[base + 2] = (
            2.25 * wcg[i] * (wr if i < 2 else 1.0) * bp[1][i] / dp[1][i])

    dnp = [0.0] * 34
    for m in (1, 2, 3):
        dnp[m] = k * vnp[m]
    for base in (25, 28, 31):
        dnp[base] = 0.8 * vnp[base]
        dnp[base + 1] = -0.4 * vnp[base + 1]

    snp = [0.0] * 34
    for base in (25, 28, 31):
        snp[base + 2] = 0.7 * vnp[base + 2]

    result = [(_sq(vnp[m]) + _sq(dnp[m])) ** 0.5 for m in range(34)]

    # --- Inertia factors (ground line) ----------------------------------------
    nvp = [0.0] * 25
    for m in range(1, 10):
        nvp[m] = (2 * vmp[m] + vnp[m] + lf * wl[m]) / wl[m]
    for m in range(10, 13):
        nvp[m] = (vmp[m] + lf * wl[m]) / wl[m]
    for m in range(13, 25):
        nvp[m] = (2 * vmp[m] + vnp[m]) / wl[m]
    ndp = [0.0] * 25
    for m in range(1, 10):
        ndp[m] = (2 * dmp[m] + dnp[m]) / wl[m]
    for m in range(10, 13):
        ndp[m] = (dmp[m] + dnp[m]) / wl[m]
    for m in range(13, 25):
        ndp[m] = (2 * dmp[m] + dnp[m]) / wl[m]
    ns = [0.0] * 25
    for m in GROUND_SIDE_CASES:
        partner = side_partner(m)
        assert partner is not None            # every side case has one
        ns[m] = (smp[m] - smp[partner]) / wl[m]

    # --- Unbalanced moments (ground line, about the airplane CG) ---------------
    pitchp = [0.0] * 25
    for m, (j, i) in {4: (0, 0), 5: (0, 1), 6: (0, 2), 7: (2, 0), 8: (2, 1),
                      9: (2, 2), 10: (0, 0), 11: (0, 1), 12: (0, 2)}.items():
        mult = -2 if m <= 9 else -1
        pitchp[m] = mult * rmp[m] * bp[j][i]
    for m, i in ((16, 0), (17, 1), (18, 2)):
        pitchp[m] = -2 * (vmp[m] * bp[1][i] + dmp[m] * cp[1][i])
    for m, i in ((19, 0), (20, 0), (21, 1), (22, 1), (23, 2), (24, 2)):
        pitchp[m] = -2 * vmp[m] * bp[1][i]
    rollp = [0.0] * 25
    for m in range(10, 13):
        rollp[m] = vmp[m] * gear.tread_in / 2
    for m, i in ((19, 0), (20, 0), (21, 1), (22, 1), (23, 2), (24, 2)):
        sign = -1 if m % 2 else 1
        rollp[m] = sign * 0.83 * wl[m] * cp[1][i]
    yawp = [0.0] * 25
    for m in range(10, 13):
        yawp[m] = -dmp[m] * gear.tread_in / 2
    for m, i in ((19, 0), (20, 0), (21, 1), (22, 1), (23, 2), (24, 2)):
        sign = -1 if m % 2 else 1
        yawp[m] = sign * 0.83 * wl[m] * bp[1][i]

    # --- Airplane-datum reactions (resolve the resultants through PHIM/PHIN) ----
    beta = geo.beta
    phim = [0.0] * 34
    for m in range(1, 7):
        phim[m] = beta[0]
    for m in range(7, 10):
        phim[m] = beta[2]      # was -beta[2]; the sign now lives in beta alone
    for m in range(10, 13):
        phim[m] = beta[0]
    for m in range(13, 19):
        phim[m] = math.degrees(math.atan(0.8)) + beta[1]
    for m in range(19, 25):
        phim[m] = beta[1]
    phin = [0.0] * 34
    for m in (1, 2, 3):
        phin[m] = beta[0]
    for m in (13, 14, 15):
        phin[m] = beta[1]
    for base in (25, 28, 31):
        phin[base] = math.degrees(math.atan(0.8)) + beta[1]
        phin[base + 1] = math.degrees(math.atan(-0.4)) + beta[1]
        phin[base + 2] = beta[1]
    vm = [rmp[m] * math.cos(math.radians(phim[m])) for m in range(25)]
    dm = [rmp[m] * math.sin(math.radians(phim[m])) for m in range(25)]
    vn = [result[m] * math.cos(math.radians(phin[m])) for m in range(34)]
    dn = [result[m] * math.sin(math.radians(phin[m])) for m in range(34)]

    # --- Airplane-datum load factors and moments (p232/p233; note 38 GF-6) ----
    # ``rho``, the ground-line -> airplane-datum rotation, taken from each case's
    # **own two resolutions** of one reaction rather than from ``GRA``
    # (:func:`sloads.frames.rotation_deg`). Nothing below therefore restates a
    # sign, which matters: the two sign errors design note 38 adjudicated (#133's
    # PHIM and OQ-1's lift term) were both a ``GRA`` written out longhand with a
    # ``+`` where the physics wanted a ``-``. The main pair resolves on every
    # case 1-24; the 23.499 family (25-33) is nose-only, carries no airplane in
    # equilibrium and so gets no datum factors at all -- as ``nvp``/``ndp`` do not.
    rho = [0.0] * 25
    for m in range(1, 25):
        rho[m] = rotation_deg(vm[m], dm[m], vmp[m], dmp[m])

    nv = [0.0] * 25
    nd = [0.0] * 25
    nr = [0.0] * 25
    for m in range(1, 25):
        # The main wheels the case puts on the ground. LANDLOAD.BAS writes the
        # 23.483 family as ``VM(L)/WL(L)`` where every other line has ``2*VM(L)``
        # -- one gear carries the whole reaction, which is the *definition* of
        # the one-wheel condition rather than an exception to it.
        mains = 1 if m in GROUND_ONE_WHEEL_CASES else 2
        nv[m] = (vn[m] + mains * vm[m]) / wl[m]
        nd[m] = (dn[m] + mains * dm[m]) / wl[m]
    for m in GROUND_LIFT_CASES:
        # G-7a / OQ-1: the lift is perpendicular to the flight path, so it is a
        # ground-line **vertical**, and it enters the airplane's axes tilted by
        # the same ``rho`` every reaction was tilted by. LANDLOAD.BAS writes the
        # two components longhand as ``+LF*COS(GRA)`` and ``+LF*SIN(GRA)``, and
        # the drag one carries the wrong sign -- the second instance of the #133
        # class (design note 38 §1.6). Rotating the vector cannot carry that
        # error: it is the corrected value by construction. The p232 cells this
        # deviates from are registered in
        # ``docs/20_theory/02_approved_corrections.md``.
        lift_v, lift_d = to_airplane_datum(lf, 0.0, rho[m])
        nv[m] += lift_v
        nd[m] += lift_d
    for m in range(1, 25):
        nr[m] = (_sq(nv[m]) + _sq(nd[m])) ** 0.5
    # ``NNS`` is not repeated in this frame: the side axis is normal to the
    # rotation, so the ground-line and datum side factors are the same number.

    # The same unbalanced moments in the airplane datum (p233's second table).
    # A moment vector rotates exactly as a force vector does under the same
    # change of frame, so this is ``to_airplane_datum`` again -- with the pairing
    # ``v = YAW`` (yaw is about the vertical axis) and ``d = ROLL`` (roll is
    # about the drag axis). The pitching moment is about the axis the rotation is
    # taken around and is invariant, which is LANDLOAD.BAS's own ``PMOM =
    # PMOMP``. Its ``RMOM``/``YMOM`` lines rotate the other way (+GRA) -- the
    # third instance of the same sign class (note 38 §1.13), corrected here for
    # the same reason and registered with the ND lift term.
    pitch = [0.0] * 25
    roll = [0.0] * 25
    yaw = [0.0] * 25
    for m in range(1, 25):
        pitch[m] = pitchp[m]
        yaw[m], roll[m] = to_airplane_datum(yawp[m], rollp[m], rho[m])

    # --- Assemble per-case records --------------------------------------------
    # LG- ids are minted here, in this loop's fixed 1..33 order (the manual's own
    # case numbering, unrelated to but reused for traceability in CaseRef.condition).
    allocator = CaseIdAllocator()
    cases: List[GearReactionCase] = []
    for m in range(1, 34):
        fam, far = _family(m)
        i = _loading_index(m)
        cg_name = cgs[i].name if i < len(cgs) else ""
        case_ref = CaseRef(
            case_id=allocator.next_id("landing_gear"),
            component="landing_gear",
            condition=f"{fam} (case {m})",
            cg=cg_name,
            far_reference=far,
        )
        cases.append(GearReactionCase(
            case=m, description=fam, far_reference=far, cg_name=cg_name,
            # The 23.499 family (25-33) indexes ``wcg`` directly rather than the
            # 1..24 ``wl`` table, and applies ``wr`` to the first two loadings
            # only -- the same rule its ``VNP`` is built with just above.
            weight_lb=(wl[m] if m <= 24 else wcg[i] * (wr if i < 2 else 1.0)),
            # ``cg_name`` is the loading's name and ``weight_lb`` the weight the
            # case is computed at; both come from ``_loading_index``, so a reader
            # cannot be shown one loading's name beside another's weight.
            vmp=vmp[m] if m <= 24 else 0.0,
            dmp=dmp[m] if m <= 24 else 0.0,
            smp=smp[m] if m <= 24 else 0.0,
            rmp=rmp[m] if m <= 24 else 0.0,
            vnp=vnp[m], dnp=dnp[m], snp=snp[m], result=result[m],
            vm=vm[m] if m <= 24 else 0.0, dm=dm[m] if m <= 24 else 0.0,
            vn=vn[m], dn=dn[m],
            nvp=nvp[m] if m <= 24 else 0.0, ndp=ndp[m] if m <= 24 else 0.0,
            ns=ns[m] if m <= 24 else 0.0,
            pitchp=pitchp[m] if m <= 24 else 0.0,
            rollp=rollp[m] if m <= 24 else 0.0,
            yawp=yawp[m] if m <= 24 else 0.0,
            # p231's FUSELAGE AXIS ANGLE column: this case's attitude, stated
            # per case rather than per family so a reader never has to know
            # which family a case number belongs to.
            fuselage_axis_angle_deg=geo.gra[attitude_of(m)[1]],
            nr=nr[m] if m <= 24 else 0.0,
            nv=nv[m] if m <= 24 else 0.0,
            nd=nd[m] if m <= 24 else 0.0,
            pitch=pitch[m] if m <= 24 else 0.0,
            roll=roll[m] if m <= 24 else 0.0,
            yaw=yaw[m] if m <= 24 else 0.0,
            case_ref=case_ref))
    return cases


def _sq(x: float) -> float:
    return x * x


# --------------------------------------------------------------------------- #
# Project glue: resolve inputs, run LGFACTOR + LANDLOAD, emit a ModuleResult.
# --------------------------------------------------------------------------- #
def _wing_area(project: Project) -> float:
    """Wing area S (ft^2) for LGFACTOR, from the geometry wing — note 33, DS-2.

    **One precedence, shared with STRSPEED.** This used to prefer a
    ``landing.wing_area_sqft`` copy and fall back to geometry, while
    :func:`sloads.modules.structural_speeds._wing_area_sqft` preferred geometry
    and fell back to its own slice copy — opposite orders for one quantity,
    masked only because ``sync_geometry_derived`` overwrote the landing copy
    before this ran. The copy is gone (DS-1) and the planform is the answer --
    resolved by :func:`sloads.derived_geometry.planform_area_sqft`, which is now
    the only place the strip integral is read for this quantity (#70): this
    function and STRSPEED's still each own their *policy* (LGFACTOR refuses,
    STRSPEED falls back), but neither owns the arithmetic any more.
    """
    from ..derived_geometry import planform_area_sqft

    area = planform_area_sqft(project, "wing")
    if area is not None:
        return area
    raise MissingInputError(
        "landing needs the wing area: add a 'wing' surface to the geometry slice "
        "(Configuration & Layout). LGFACTOR reads the planform, not a second copy.")


def _cg_cases(project: Project) -> List[CgCase]:
    """LANDLOAD's three loadings, in role order (decision G-3a).

    LANDLOAD cycles three *distinct* loadings -- aft max landing, fwd max landing
    and fwd light (UG fig 18.2); the fwd/aft distinction drives the nose-gear and
    braked-roll lever arms (``AP``/``BP``/``CP`` about ``xcg``). These are **not**
    auto-derived (M2-8): the earlier fallback took both max-landing corners from the
    single heaviest ``Project.mass`` case, which cannot supply distinct fwd/aft CG
    stations -- the pair was degenerate and the nose-gear/braked-roll reactions were
    under-predicted. Callers must supply the three explicit stations (the WTENV
    structural fwd/aft CG limits are the intended source; see
    ``validation.wtenv_cg_limits`` and, for the forward limit read *at* the landing
    weight, ``validation.wtenv_fwd_cg_limit_at_weight``).

    The three are consumed **positionally** by ``landing_reactions``. Until step 10
    piece 2 that order was recovered by matching names against
    ``validation.LANDING_CG_NAMES``, falling back to entry order with a warning --
    a renamed case silently reordered an oracle-locked reaction table. It is now an
    explicit ``CgCase.role``, resolved by :func:`sloads.cg_cases.landing_role_cases`,
    which raises rather than reordering or padding. Any further ``GROUND``-tagged
    case without a role is assembled and distributed but never reaches here, so the
    tag can grow while this module keeps its exact three-loading contract."""
    return landing_role_cases(project)


def gear_geometry(project: Project) -> LandingGearGeometry:
    """The one stored gear geometry (Step G6b), or a refusal — note 33, DS-2/DS-3.

    ``geometry.landing_gear`` is the single home. This used to be
    ``_effective_gear_input``, which copied the geometry onto a replacement
    ``LandingInput`` so the calc could keep reading ``inp.main_gear``; the slice
    carried the same three fields, so a project could state a second, unreachable
    opinion of the gear. The fields are gone (note 33, DS-1) and the geometry is
    passed to the functions that need it instead.

    Raising here is DS-3: with no slice copy to fall back on, absent geometry is
    an error naming the page that owns it, not a silent set of zero-length legs.
    """
    geom = project.geometry
    lg = geom.landing_gear if geom is not None else None
    if lg is None:
        raise MissingInputError(
            "landing needs the gear geometry: set geometry.landing_gear (the axle "
            "positions at the three strut states, rolling radius and tread) on the "
            "Configuration & Layout page.")
    return lg


def build_landing(project: Project) -> Tuple[LoadFactorResult, List[GearReactionCase]]:
    """Run LGFACTOR then LANDLOAD; return the load factor and the reaction table.

    Pure with respect to ``project`` (M2R-4): the gear geometry and the derived
    gross-weight default are resolved onto a local *effective* input copy; nothing is
    written back to ``Project.landing`` (the airplane load factor ``N`` is returned on
    ``LoadFactorResult.airplane_load_factor``, not stored)."""
    if project.landing is None:
        raise MissingInputError("landing needs the 'landing' input slice")
    inp = project.landing
    gear = gear_geometry(project)
    s = _wing_area(project)
    # Both design weights are read from their single owners on ``WeightInput``
    # (G-4 / G-14). MLW raises when unset rather than falling back; MTOW replaces
    # the ``max(landing cg_cases)`` fallback that used to fill ``GW``, which
    # returned **MLW** and silently made ``WR = 1.0``, understating the braked-roll,
    # side and supplementary-nose cases by ~5 %.
    mlw = max_landing_weight(project)
    mtow = max_takeoff_weight(project)
    lf = landing_load_factor(s, mlw, inp.strut_stroke_in,
                             inp.tire_od_in, inp.hub_diameter_in, inp.lift_factor,
                             normalise_code(gear.main_gear.strut, STRUT_TYPES, "main-gear strut type") == "O")
    cgs = _cg_cases(project)
    # FAR 23.473(g) floors on the *governing* pair (note 37, LF-6): a refusal in a
    # FAR 23 category (a user-entered N in a certificated category can be wrong in
    # a way the derived-only N never could), a warn-only note (in ``run``) in
    # concept. One policy owner: ``far23_473g_floor_violations``.
    n_gov, nlg_gov = governing_load_factors(inp, lf)
    if not project.is_concept:
        floors = far23_473g_floor_violations(n_gov, nlg_gov)
        if floors:
            raise ValueError(
                "23.473(g) floor not met (" + "; ".join(floors) + "): a FAR 23 "
                f"category requires N >= {FAR23_473G_N_FLOOR} and "
                f"NLG >= {FAR23_473G_NLG_FLOOR}. Enter a higher landing N, or a "
                "stiffer gear if the energy value governs.")
    reactions = landing_reactions(inp, gear, lf, cgs, mlw=mlw, mtow=mtow)
    return lf, reactions


def energy_load_factor_estimate(project: Project) -> Optional[LoadFactorResult]:
    """LGFACTOR's energy result from the stored inputs, or ``None`` -- never raises.

    A display helper for both GUIs (note 37, LF-7): the seed for the governing-N
    widget and the "entered N is below the computed N" caution both need the
    energy value on a page that may not yet be computable. One owner here so the
    two front-ends cannot restate the LGFACTOR call differently.
    """
    try:
        if project.landing is None:
            return None
        inp = project.landing
        gear = gear_geometry(project)
        return landing_load_factor(
            _wing_area(project), max_landing_weight(project), inp.strut_stroke_in,
            inp.tire_od_in, inp.hub_diameter_in, inp.lift_factor,
            normalise_code(gear.main_gear.strut, STRUT_TYPES, "main-gear strut type") == "O")
    except (MissingInputError, ValueError, ZeroDivisionError):
        return None


def below_energy_caution(project: Project) -> Optional[str]:
    """The "entered N is below the computed N" caution, or ``None`` (note 37, LF-7).

    Not a refusal: a rounded-down design N is legal (the floors are the hard
    bound), but running the reactions below the drop-test energy value deserves a
    stated warning. One owner for both GUIs; ``cessna_210`` trips it (3.1670
    entered vs 3.3885 computed), ``ga6_normal`` does not (3.167 vs 3.0951).
    """
    inp = project.landing
    if inp is None or inp.airplane_load_factor is None:
        return None
    est = energy_load_factor_estimate(project)
    if est is None or inp.airplane_load_factor >= est.airplane_load_factor:
        return None
    return (f"Entered N = {inp.airplane_load_factor:.4f} is below LGFACTOR's "
            f"computed (energy) N = {est.airplane_load_factor:.4f}: the reactions "
            "run below the drop-test work-energy estimate for this gear.")


def _critical(cases: List[GearReactionCase], far: str) -> Optional[GearReactionCase]:
    """The case of the given FAR family with the largest resultant ground reaction.

    Ranked on the **full three-component** reaction magnitude -- sqrt(V^2+D^2+S^2)
    for the main wheel and likewise for the nose -- not on the stored ``rmp``/
    ``result``, which are the two-component sqrt(V^2+D^2) values LANDLOAD prints and
    exclude the side load entirely. For the 23.485 side family that made the pick a
    tie-break accident: cases 19-22 share an identical VMP, so ``max`` returned
    whichever came first (M4-17e). Ranking only -- no stored value changes, so the
    oracles are unaffected."""
    family = [c for c in cases if c.far_reference == far]
    if not family:
        return None

    def magnitude(c: GearReactionCase) -> float:
        return max((_sq(c.vmp) + _sq(c.dmp) + _sq(c.smp)) ** 0.5,
                   (_sq(c.vnp) + _sq(c.dnp) + _sq(c.snp)) ** 0.5)

    # The tie rule, not raw ``max``: this family is the documented tie above
    # (cases 19-22 share a VMP), so the winner is the first in case order, on
    # every platform (CR-B-1; ``picks.extreme``).
    return extreme(family, magnitude)


def _case_values(c: GearReactionCase,
                 legs: Sequence["DeliveredLeg"] = ()) -> List[LoadValue]:
    """The per-case LoadValues for one LANDLOAD ground condition.

    Three sets, and the frame each is stated in is carried on the value itself
    (:mod:`sloads.frames`, design note 38 GF-6/GF-7) rather than left to a column
    header or a caption:

    * **The delivered load** -- for each of the three wheels (nose, left main,
      right main, in that order, *all three on every case*), the airplane-datum
      force ``Fx, Fy, Fz``, the location ``x, y, z`` it acts at, and the gear
      reference point it is delivered to. A wheel this case does not load is
      emitted at **zero** rather than omitted: which gears a family lifts clear
      is a fact about the case, and leaving it out makes the reader reconstruct
      it. The point is the manual's own printed column, not an inference -- see
      :func:`sloads.gear_loads.application_point_of` (design note 39).
    * **The airplane-datum scalars** -- the ``NR``/``NV``/``ND`` load factors of
      p232 and the unbalanced moments of p233's second table.
    * **The ground-line ("prime") set** -- the frame the manual prints and a gear
      engineer reads. Marked :data:`~sloads.frames.GROUND_LINE`, which keeps it
      in the text report and out of the delivered CSV (GF-6): the CSV is the
      body-frame deliverable, and the primed set is the analysis view beside it.

    Forces (``lb``) and moments (``lb-in``) are load quantities: ``report.py``
    marks them ``lbs-ULT`` / ``lb-in-ULT`` and scales them by the case
    ``safety_factor``. Locations (``in``), the fuselage-axis angle (``deg``) and
    the load factors (dimensionless) are **not** loads: they take no ``-ULT``
    marker, are never scaled, and render with a blank SF column.

    Cases 25-33 are the 23.499 supplementary-nose family: they have no main-wheel
    reaction, no unbalanced moment and no inertia factor (all structurally zero in
    ``landing_reactions``), so those *primed* rows are omitted rather than emitted
    as zeros. The three-wheel delivered set is emitted for them like any other
    case -- that is the point of it.
    """
    out: List[LoadValue] = []
    for leg in legs:
        stem = leg.key_stem
        label = leg.name[0].upper() + leg.name[1:]
        # The point rides on the value, not only in the note (#141): the note is
        # the reader's sentence and the CSV drops it, so a delivered force and
        # the *named* point it acts at travel together to every channel.
        at = leg.point_name
        for axis, force, coord, node in zip("xyz", leg.force, leg.point, leg.node):
            out.append(LoadValue(f"{label} F{axis}", force, "lb",
                                 key=f"{stem}_f{axis}", frame=AIRPLANE_DATUM, point=at))
            out.append(LoadValue(f"{label} {axis}", coord, "in",
                                 key=f"{stem}_{axis}", frame=AIRPLANE_DATUM, point=at))
            # The node is the leg's reference point the reaction is transferred
            # *to*, not the point the force acts at, so it names none: stamping
            # it ``at`` would say the force is applied in two places at once.
            out.append(LoadValue(f"{label} node {axis}", node, "in",
                                 key=f"{stem}_node_{axis}", frame=AIRPLANE_DATUM))
    # p231's FUSELAGE AXIS ANGLE column. An attitude, in neither frame -- it is
    # the angle *between* them -- so it names none and is delivered unscaled.
    out.append(LoadValue("Fuselage axis angle", c.fuselage_axis_angle_deg, "deg",
                         key="fuselage_axis_angle"))
    nose = [LoadValue("Vertical nose", c.vnp, "lb", key="vertical_nose", frame=GROUND_LINE),
            LoadValue("Drag nose", c.dnp, "lb", key="drag_nose", frame=GROUND_LINE),
            LoadValue("Side nose", c.snp, "lb", key="side_nose", frame=GROUND_LINE),
            LoadValue("Resultant nose", c.result, "lb", key="resultant_nose", frame=GROUND_LINE)]
    if c.case > 24:
        return out + nose
    return out + [
        LoadValue("Resultant load factor NR", c.nr, "", key="resultant_load_factor_nr",
                  frame=AIRPLANE_DATUM),
        LoadValue("Vertical load factor NV", c.nv, "", key="vertical_load_factor_nv",
                  frame=AIRPLANE_DATUM),
        LoadValue("Drag load factor ND", c.nd, "", key="drag_load_factor_nd",
                  frame=AIRPLANE_DATUM),
        LoadValue("Unbalanced pitching moment (datum)", c.pitch, "lb-in",
                  key="unbalanced_pitching_moment_datum", frame=AIRPLANE_DATUM),
        LoadValue("Unbalanced rolling moment (datum)", c.roll, "lb-in",
                  key="unbalanced_rolling_moment_datum", frame=AIRPLANE_DATUM),
        LoadValue("Unbalanced yawing moment (datum)", c.yaw, "lb-in",
                  key="unbalanced_yawing_moment_datum", frame=AIRPLANE_DATUM),
        # NS is common to both frames: the side axis is normal to the rotation,
        # so there is one side inertia factor, not two. It is grouped with the
        # ground-line set because that is where the manual prints it.
        LoadValue("Vertical main per wheel", c.vmp, "lb", key="vertical_main_per_wheel",
                  frame=GROUND_LINE),
        LoadValue("Drag main per wheel", c.dmp, "lb", key="drag_main_per_wheel",
                  frame=GROUND_LINE),
        LoadValue("Side main per wheel", c.smp, "lb", key="side_main_per_wheel",
                  frame=GROUND_LINE),
        LoadValue("Resultant main per wheel", c.rmp, "lb", key="resultant_main_per_wheel",
                  frame=GROUND_LINE),
    ] + nose + [
        LoadValue("Unbalanced pitching moment", c.pitchp, "lb-in",
                  key="unbalanced_pitching_moment", frame=GROUND_LINE),
        LoadValue("Unbalanced rolling moment", c.rollp, "lb-in",
                  key="unbalanced_rolling_moment", frame=GROUND_LINE),
        LoadValue("Unbalanced yawing moment", c.yawp, "lb-in",
                  key="unbalanced_yawing_moment", frame=GROUND_LINE),
        LoadValue("Vertical inertia factor NVP", c.nvp, "",
                  key="vertical_inertia_factor_nvp", frame=GROUND_LINE),
        LoadValue("Drag inertia factor NDP", c.ndp, "",
                  key="drag_inertia_factor_ndp", frame=GROUND_LINE),
        LoadValue("Side inertia factor NS", c.ns, "",
                  key="side_inertia_factor_ns", frame=GROUND_LINE),
    ]


def case_note(legs: Sequence["DeliveredLeg"]) -> str:
    """The in-band statement of *where* and *in what attitude* a case is applied.

    The two facts a delivered ground load needs that are not numbers: the strut
    state the geometry was taken at, and which of Appendix A's two application
    points this family is applied at (design note 39). They ride on the condition
    rather than in a document beside it, because a force and its point are one
    statement and the point half is a word.
    """
    if not legs:
        return ""
    return (f"Applied at the {legs[0].point_name}, struts {legs[0].strut_state} "
            f"(Appendix A's printed point-of-load column). Forces and locations "
            f"are {caption(AIRPLANE_DATUM)}; the primed set is "
            f"{caption(GROUND_LINE)}.")


def run(project: Project) -> ModuleResult:
    """Run LGFACTOR + LANDLOAD: the ground-load conditions (FAR 23.473-23.499)."""
    lf, reactions = build_landing(project)
    inp = project.landing
    assert inp is not None  # build_landing raised otherwise
    n_gov, nlg_gov = governing_load_factors(inp, lf)
    note = "Tricycle gear only (UG Table 2.1)."
    if inp.airplane_load_factor is not None:
        note += (f" The reactions run at the entered N = {n_gov:.4f} "
                 f"(NLG = N - L = {nlg_gov:.4f}); the energy N/NLG rows are "
                 "LGFACTOR's drop-test estimate.")
    if project.is_concept:
        note += " Concept mode -- unverified extrapolation past the FAR23 band."
        # FAR 23.473(g) on the *governing* pair: warn-only in concept (a FAR 23
        # category refuses instead, in ``build_landing`` -- note 37, LF-6). The
        # energy N/NLG are left untouched, so the Appendix-A oracle (N 3.0951 /
        # NLG 2.4281) is unaffected.
        floors = far23_473g_floor_violations(n_gov, nlg_gov)
        if floors:
            note += (" 23.473(g) floor not met (" + "; ".join(floors)
                     + f"): the regulation requires N >= {FAR23_473G_N_FLOOR} "
                     f"and NLG >= {FAR23_473G_NLG_FLOOR}.")

    conditions = [ConditionResult(
        title="Landing load factor (LGFACTOR)",
        far_reference="23.473",
        values=[
            LoadValue("Sink rate", lf.sink_rate_fps, "ft/s", key="sink_rate"),
            LoadValue("Airplane load factor N", lf.airplane_load_factor, "", key="airplane_load_factor_n"),
            LoadValue("Landing gear factor NLG", lf.gear_load_factor, "", key="landing_gear_factor_nlg"),
            # The pair the reaction matrix actually ran at (note 37: equal to the
            # energy rows above unless the user entered N). Fixes symptom S2 --
            # the page used to report only an N the reactions were not computed
            # from whenever the old NLG override was set.
            LoadValue("Governing airplane load factor N", n_gov, "", key="governing_airplane_load_factor_n"),
            LoadValue("Governing gear factor NLG", nlg_gov, "", key="governing_gear_factor_nlg"),
        ],
        note=note,
    )]
    # The delivered three-wheel set (design note 38 GF-6). ``gear_loads`` reads
    # this module -- it needs ``build_landing``, ``attitude_of`` and the case
    # families -- so the import is here rather than at the top: the deliverable
    # is assembled *from* the free bodies, and assembling it a second time in
    # this file to avoid the cycle is exactly the duplication that would drift.
    from ..gear_loads import delivered_gear_legs, gear_case_loads
    legs_by_case = delivered_gear_legs(gear_case_loads(project))

    # One summary condition per FAR ground-load family (the critical wheel reaction).
    for far, title in (("23.479(a)", "Level landing"), ("23.481", "Tail-down landing"),
                       ("23.483", "One-wheel landing"), ("23.485", "Side load"),
                       ("23.493", "Braked roll"), ("23.499", "Supplementary nose wheel")):
        c = _critical(reactions, far)
        if c is None:
            continue
        legs = legs_by_case.get(c.case, ())
        # The summary states the *same* case the matrix row does, through the
        # same builder -- it names which case governs the family, and a second
        # hand-written value list beside it would be free to drift into a
        # different frame or a different application point from the row it
        # points at. Design note 38 GF-6: every channel, one statement.
        conditions.append(ConditionResult(
            title=f"{title} (critical reaction)",
            far_reference=far,
            values=([LoadValue("Case", float(c.case), "", key="case")]
                    + _case_values(c, legs)),
            note=case_note(legs),
            case_ref=c.case_ref,
        ))
    # The full 33-case matrix (M4-17e), so the ULTIMATE deliverable (CSV / Results
    # Review / Export) is no longer thinner than the LIMIT analysis screen, and the
    # unbalanced moments + ground-line inertia factors -- a third of the original
    # LANDLOAD printout, and the gear-attachment inputs M4-6 needs -- actually ship.
    # Each row reuses its own CaseRef, so a summary condition and its matrix row
    # share a case id: they are the same physical case.
    for c in reactions:
        legs = legs_by_case.get(c.case, ())
        conditions.append(ConditionResult(
            title=f"{c.description} — case {c.case} ({c.cg_name})",
            far_reference=c.far_reference,
            values=_case_values(c, legs),
            note=case_note(legs),
            case_ref=c.case_ref,
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
