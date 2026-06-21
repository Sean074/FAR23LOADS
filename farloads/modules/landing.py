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

**LANDLOAD** (FAR 23.473-23.499) computes the tricycle-gear reaction loads for the
level (3-wheel and 2-wheel), tail-down, one-wheel, braked-roll, side and
supplementary-nose-wheel ground conditions. The drag load factor of FAR 23
Appendix C is scaled by the airplane/gear load-factor ratio to give drag as if no
lift were assumed (``K = NAP/NLG * K0``); the lever arms ``AP/BP/DP/CP`` of
Appendix C Fig C23.1 are formed for each attitude and CG, then the per-wheel
vertical / drag / side reactions follow per FAR section.

Reads the per-CG weight & CG from ``Project.mass`` (WTONECG) and the wing area
from ``Project.geometry`` when not given explicitly; the gear strut geometry is
``Project.landing``. **Tricycle gear only** (UG Table 2.1).

Reference: LGFACTOR.BAS (Appendix C p483), LANDLOAD.BAS (Appendix C p468); Ref 1
Ch 20 p126-130; oracles Appendix A "Landing Load Factor" p236
(V 9.0048 / N 3.0951 / NLG 2.4281) and "Landing Loads with Respect to Ground Line"
p230 (K 0.324 / GAMMA 17.978 / the AP-BP-DP-CP lever-arm table).
"""

from __future__ import annotations

import math
from typing import List, NamedTuple, Optional, Tuple

from ..constants import G
from ..models import (
    CgCase,
    ConditionResult,
    GearReactionCase,
    LandingInput,
    LoadValue,
    ModuleResult,
    Project,
)
from ..registry import register

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

    ``lift_factor`` (L) must not exceed 0.667; the descent velocity is clamped to
    7-10 fps per FAR 23.473(d). Returns the sink rate, airplane load factor N and
    landing-gear factor ``NLG = N - L``."""
    if wing_area_sqft <= 0 or weight_lb <= 0:
        raise ValueError("LGFACTOR needs positive wing area and landing weight")
    if lift_factor > 0.667:
        raise ValueError("lift factor L must not exceed 0.667 (FAR 23.473)")
    v = 4.4 * (weight_lb / wing_area_sqft) ** 0.25
    v = min(10.0, max(7.0, v))
    d_tire = (tire_od_in - hub_diameter_in) / 6.0    # flat-tyre deflection, in
    eta_strut = ETA_OLEO if main_is_oleo else ETA_SPRING
    numerator = (weight_lb * v ** 2 / (2.0 * G)
                 + weight_lb * (1.0 - lift_factor) * (strut_stroke_in + d_tire) / 12.0)
    denominator = weight_lb * (ETA_TIRE * d_tire + eta_strut * strut_stroke_in) / 12.0
    if denominator <= 0:
        raise ValueError("LGFACTOR strut/tyre stroke must be positive")
    n = numerator / denominator
    return LoadFactorResult(sink_rate_fps=v, airplane_load_factor=n,
                            gear_load_factor=n - lift_factor)


def _trunc3(x: float) -> float:
    """Truncate to 3 decimals to mirror the BASIC ``INT(x*1000)/1000`` lever arms."""
    return int(x * 1000) / 1000


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


def _geometry(inp: LandingInput, nlg: float, cgs: List[CgCase]) -> _Geometry:
    """Ground angles, BETA and the AP/BP/DP/CP lever arms (LANDLOAD.BAS 50-720)."""
    nap = nlg + inp.lift_factor
    k0 = _appendix_c_k0(inp.max_landing_weight_lb)
    k = nap / nlg * k0
    gamma = math.degrees(math.atan(k))

    mg, ng = inp.main_gear, inp.nose_gear
    xm_c, zm_c = mg.axle_compressed
    xn_c, zn_c = ng.axle_compressed
    xm_s, zm_s = mg.axle_static
    xn_s, zn_s = ng.axle_static
    rm, rn = mg.rolling_radius_in, ng.rolling_radius_in

    # Ground angle for the 3-/2-wheel level attitude (J=1) and ground roll (J=2):
    # the slope of the axle line less the slope of the wheel-contact line.
    def ground_angle(xm: float, zm: float, xn: float, zn: float) -> float:
        return math.degrees(
            math.atan((zm - zn) / (xm - xn))
            - math.atan((rm - rn) / (((xm - xn) ** 2 + (zm - zn) ** 2) ** 0.5)))

    gra1 = ground_angle(xm_c, zm_c, xn_c, zn_c)   # level (compressed)
    gra2 = ground_angle(xm_s, zm_s, xn_s, zn_s)   # ground roll (static)
    gra3 = inp.tail_down_angle_deg
    gra = (gra1, gra2, gra3)
    beta = (gamma - gra1, gra2, gra3)

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
    # Attitude 2 -- tail down (only BP; vertical reactions, GRA(3)).
    for i, cg in enumerate(cgs):
        bp[2][i] = ((xm_c - cg.xcg) * math.cos(math.radians(gra3))
                    - (cg.zcg - zm_c) * math.sin(math.radians(gra3)))
    # Attitude 1 -- ground roll (static axle positions), plus the CP vertical offset.
    for i, cg in enumerate(cgs):
        ap[1][i] = fn_ap(cg.xcg, xn_s, gra2, cg.zcg, zn_s)
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
                tbl[j][i] = _trunc3(tbl[j][i])
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


def _family(case: int) -> Tuple[str, str]:
    for rng, fam in _MAIN_FAMILIES.items():
        if case in rng:
            return fam
    return _NOSE_FAMILY


def landing_reactions(inp: LandingInput, lf_result: LoadFactorResult,
                      cgs: List[CgCase]) -> List[GearReactionCase]:
    """The 24 main-wheel + 33 nose-wheel ground-condition reactions (LANDLOAD.BAS).

    ``cgs`` is the ordered [aft-max-landing, fwd-max-landing, fwd-light] loading;
    LANDLOAD cycles the three through each condition family."""
    if len(cgs) != 3:
        raise ValueError("LANDLOAD needs exactly 3 CG cases (aft/fwd max landing, fwd light)")
    nlg = inp.gear_load_factor or lf_result.gear_load_factor
    lf = inp.lift_factor
    geo = _geometry(inp, nlg, cgs)
    k = geo.k
    ap, bp, dp, cp = geo.ap, geo.bp, geo.dp, geo.cp
    wr = inp.gross_weight_lb / inp.max_landing_weight_lb if inp.max_landing_weight_lb else 1.0
    wcg = [cg.weight_lb for cg in cgs]

    # Per-case weight WL (1-based index 1..24); cases 13-22 use gross (WR), 23-24 the
    # light landing weight directly (LANDLOAD.BAS lines 820-900).
    wl = [0.0] * 25
    for m in range(1, 13):
        wl[m] = wcg[(m - 1) % 3]
    for m in range(13, 19):
        wl[m] = wcg[(m - 13) % 3] * wr
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
    for m, partner in ((19, 20), (20, 19), (21, 22), (22, 21), (23, 24), (24, 23)):
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
        rollp[m] = vmp[m] * inp.tread_in / 2
    for m, i in ((19, 0), (20, 0), (21, 1), (22, 1), (23, 2), (24, 2)):
        sign = -1 if m % 2 else 1
        rollp[m] = sign * 0.83 * wl[m] * cp[1][i]
    yawp = [0.0] * 25
    for m in range(10, 13):
        yawp[m] = -dmp[m] * inp.tread_in / 2
    for m, i in ((19, 0), (20, 0), (21, 1), (22, 1), (23, 2), (24, 2)):
        sign = -1 if m % 2 else 1
        yawp[m] = sign * 0.83 * wl[m] * bp[1][i]

    # --- Airplane-datum reactions (resolve the resultants through PHIM/PHIN) ----
    beta = geo.beta
    phim = [0.0] * 34
    for m in range(1, 7):
        phim[m] = beta[0]
    for m in range(7, 10):
        phim[m] = -beta[2]
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

    # --- Assemble per-case records --------------------------------------------
    cases: List[GearReactionCase] = []
    for m in range(1, 34):
        fam, far = _family(m)
        i = (m - 1) % 3 if m <= 24 else (m - 25) // 3
        cg_name = cgs[i].name if i < len(cgs) else ""
        cases.append(GearReactionCase(
            case=m, description=fam, far_reference=far, cg_name=cg_name,
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
            yawp=yawp[m] if m <= 24 else 0.0))
    return cases


def _sq(x: float) -> float:
    return x * x


# --------------------------------------------------------------------------- #
# Project glue: resolve inputs, run LGFACTOR + LANDLOAD, emit a ModuleResult.
# --------------------------------------------------------------------------- #
def _wing_area(project: Project, inp: LandingInput) -> float:
    if inp.wing_area_sqft > 0:
        return inp.wing_area_sqft
    if project.geometry is not None:
        wing = project.geometry.by_name("wing")
        if wing is not None:
            from .wing_geometry import surface_properties
            r = surface_properties(wing)
            total_in2 = next(v.value for v in r.values if v.label == "Total area")
            return total_in2 / 144.0
    raise ValueError("landing needs a wing area (landing.wing_area_sqft or a geometry wing)")


def _cg_cases(project: Project, inp: LandingInput) -> List[CgCase]:
    """The three landing CG cases: explicit overrides else derived from Project.mass."""
    if inp.cg_cases:
        if len(inp.cg_cases) != 3:
            raise ValueError("landing.cg_cases must have exactly 3 entries (or be empty)")
        return inp.cg_cases
    if project.mass is None or not project.mass.cases:
        raise ValueError("landing needs 'mass' (WTONECG) or explicit landing.cg_cases")
    # Heaviest case = max-landing; derive aft/fwd by CG station; lightest = fwd-light.
    by_weight = sorted(project.mass.cases, key=lambda c: c.weight_lb, reverse=True)
    heavy = by_weight[0]
    light = by_weight[-1]
    return [
        CgCase("aft max landing", heavy.weight_lb, heavy.cg_x, heavy.cg_z),
        CgCase("fwd max landing", heavy.weight_lb, heavy.cg_x, heavy.cg_z),
        CgCase("fwd light", light.weight_lb, light.cg_x, light.cg_z),
    ]


def build_landing(project: Project) -> Tuple[LoadFactorResult, List[GearReactionCase]]:
    """Run LGFACTOR then LANDLOAD; return the load factor and the reaction table."""
    if project.landing is None:
        raise ValueError("landing needs the 'landing' input slice")
    inp = project.landing
    s = _wing_area(project, inp)
    lf = landing_load_factor(s, inp.max_landing_weight_lb, inp.strut_stroke_in,
                             inp.tire_od_in, inp.hub_diameter_in, inp.lift_factor,
                             inp.main_gear.strut == "O")
    cgs = _cg_cases(project, inp)
    # Fill gross weight from the heaviest CG case when not given.
    if inp.gross_weight_lb <= 0:
        inp.gross_weight_lb = max(cg.weight_lb for cg in cgs)
    reactions = landing_reactions(inp, lf, cgs)
    inp.n = lf.airplane_load_factor
    return lf, reactions


def _critical(cases: List[GearReactionCase], far: str) -> Optional[GearReactionCase]:
    """The case of the given FAR family with the largest resultant ground reaction."""
    family = [c for c in cases if c.far_reference == far]
    if not family:
        return None
    return max(family, key=lambda c: max(c.rmp, c.result))


def run(project: Project) -> ModuleResult:
    """Run LGFACTOR + LANDLOAD: the ground-load conditions (FAR 23.473-23.499)."""
    lf, reactions = build_landing(project)
    note = "Tricycle gear only (UG Table 2.1)."
    if project.is_concept:
        note += " Concept mode -- unverified extrapolation past the FAR23 band."

    conditions = [ConditionResult(
        title="Landing load factor (LGFACTOR)",
        far_reference="23.473",
        values=[
            LoadValue("Sink rate", lf.sink_rate_fps, "ft/s"),
            LoadValue("Airplane load factor N", lf.airplane_load_factor, ""),
            LoadValue("Landing gear factor NLG", lf.gear_load_factor, ""),
        ],
        note=note,
    )]
    # One summary condition per FAR ground-load family (the critical wheel reaction).
    for far, title in (("23.479(a)", "Level landing"), ("23.481", "Tail-down landing"),
                       ("23.483", "One-wheel landing"), ("23.485", "Side load"),
                       ("23.493", "Braked roll"), ("23.499", "Supplementary nose wheel")):
        c = _critical(reactions, far)
        if c is None:
            continue
        conditions.append(ConditionResult(
            title=f"{title} (critical reaction)",
            far_reference=far,
            values=[
                LoadValue("Case", float(c.case), ""),
                LoadValue("Vertical main per wheel", c.vmp, "lb"),
                LoadValue("Drag main per wheel", c.dmp, "lb"),
                LoadValue("Side main per wheel", c.smp, "lb"),
                LoadValue("Resultant main per wheel", c.rmp, "lb"),
                LoadValue("Vertical nose", c.vnp, "lb"),
                LoadValue("Drag nose", c.dnp, "lb"),
                LoadValue("Side nose", c.snp, "lb"),
                LoadValue("Resultant nose", c.result, "lb"),
            ],
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
