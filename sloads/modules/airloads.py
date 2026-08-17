"""Spanwise wing airloads by Schrenk's method, from AIRLOADS.BAS + TAU.BAS.

AIRLOADS computes the spanwise lift distribution of the wing -- the ``c*cl``
("span load") at each spanwise strip -- which every downstream wing-load module
(FLTLOADS balancing, WINGINER inertia relief, NETLOADS net shear/BM/torsion, the
sbeam export) consumes. The method is **Schrenk's** (Reference 1 Ch 7, p46-47;
accepted by the CAA per CAM 04 App V): average the planform-chord lift
distribution with an elliptic one. It splits into two parts (Peery, *Aircraft
Structures*):

* an **additive** distribution -- the lift of an untwisted wing, normalized to a
  wing ``CL`` of 1 (it scales linearly with the operating ``CL``); and
* a **basic** distribution -- the zero-net-lift redistribution produced by wing
  twist/washout (it integrates to zero wing lift but is non-zero locally).

The operating span load at a target ``CL`` is ``c*cl = (c*cl)_additive * CL +
(c*cl)_basic``.

Equations (Ref 1 Ch 7, p46-47), per strip with mid-station ``ye``, chord ``c``
and width ``dy`` (the WINGGEOM strip integrator, reused here so the stations line
up element-for-element with the geometry table):

    S    = 2*SUM(c*dy)                          total wing area (both sides)
    B    = 2*ytip                               span, tip to tip
    Mo   = SUM(mo*c*dy)/(S/2)                    wing zero-twist lift-curve slope
    (c*cl)_additive = 0.5*( mo*c/Mo + 4S/(pi*B)*sqrt(1-(2*ye/B)^2) )   [for CL=1]
    Awo  = SUM(mo*c*ac*dy)/SUM(mo*c*dy)          chord-weighted mean zero-lift angle
    aa   = ac - Awo                              section angle from wing zero-lift line
    (c*cl)_basic = (mo/2)*aa*c

where ``mo`` is the section lift-curve slope (per degree) and ``ac`` the section
zero-lift angle (per degree), interpolated along the span from the input twist
table. The wing lift-curve slope ``M = mo_rad/(1 + mo_rad/(pi*AR)*(1+tau))``
(Peery eq 9.59) uses the TAU planform correction (``TAU.BAS``, p407).

Limitation: the cosine fairing of the basic distribution across a flap/aileron
lift discontinuity (Ref 1 p47) is not modelled -- the Appendix A wing has no such
discontinuity, and it only arises with deflected flaps (a later step). The basic
distribution is therefore the unfaired one here.

Reference: AIRLOADS.BAS / TAU.BAS, Ref 1 Ch 7 p46-47, TAU curve-fit p407;
worked example Appendix A p161-162 (additive CC(LA1) elem 1 = 91.05576; basic
Awo = 3.988146, CC(lb) elem 1 = +5.09762, Clb elem 1 = 0.05193).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from ..constants import DEG_PER_RAD, IN2_PER_FT2, dynamic_pressure_psf
from ..models import (
    AeroSurfaceInput,
    ConditionResult,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    SurfaceInput,
    WingLoadResult,
    WingStationLoad,
)
from ..registry import register
from .wing_geometry import interp_x

_FAR = "23.301"  # airload distribution basis (Schrenk)

# AIRLOAD4 auto-select thresholds: use the swept branch when the 25%-chord sweep
# exceeds 15 deg or the design Mach exceeds 0.4.
#
# Mach threshold — Ref-1-vs-User's-Guide conflict (M1-8, resolved 2026-07-20):
# Ref 1 (McMaster, the primary source of truth) states the trigger as "Mach >.4
# or sweepback > 15 degrees" (FAR23Loads_Code.pdf, Ch 12 aileron-torsion air-loads
# section); the FAA User's Guide §9.1/§10.1 instead says "greater than 0.5". No
# `.BAS` oracle pins it either way — AIRLOAD4 selection in the original suite is a
# human-operator choice, not a hardcoded `IF MN > …` (the listing has no Mach
# comparison), so the threshold is a documentation value only. We keep Ref 1's 0.4:
# it is the higher-authority source and the conservative choice (triggers the swept
# branch earlier), and it is nearly moot for output anyway — compressibility is
# carried upstream by FLTLOADS' Glauert CL, so high Mach alone leaves the span-load
# shape unchanged. See docs/20_theory/00_theory_sources.md (AIRLOAD4 row).
_AIRLOAD4_SWEEP_DEG = 15.0
_AIRLOAD4_MACH = 0.4


def use_airload4(aero: AeroSurfaceInput) -> bool:
    """True when the swept / high-Mach AIRLOAD4 branch applies (Ref 1 Ch 12)."""
    return abs(aero.sweep_deg) > _AIRLOAD4_SWEEP_DEG or aero.design_mach > _AIRLOAD4_MACH


# --------------------------------------------------------------------------- #
# TAU -- lift-curve-slope planform correction (TAU.BAS, p407)
# --------------------------------------------------------------------------- #
# Quartic curve-fits in taper ratio for three tip ratios, per ANC(1) "Spanwise
# Air Load Distribution" (1938); linearly interpolated by tip ratio. Tip ratio is
# the rounded-tip width / semi-span (0 = square tip); taper ratio is tip chord /
# centreline chord. TAU.BAS lines 7010-7110.
_TAU_FIT = {
    0.0: (0.206209, -1.26146, 3.05385, -2.8027, 0.976801),    # square tip
    0.1: (0.112203, -0.575843, 1.08306, -0.696856, 0.194241),
    0.2: (0.0302789, 0.0294027, -0.470926, 0.880983, -0.394766),
    1.0: (0.0, 0.0, 0.0, 0.0, 0.0),                           # fully rounded -> 0
}


def _poly(coeffs, x: float) -> float:
    return math.fsum(c * x ** i for i, c in enumerate(coeffs))


def _tau(taper_ratio: float, tip_ratio: float) -> float:
    """TAU planform correction, interpolated by tip ratio (TAU.BAS p407)."""
    knots = sorted(_TAU_FIT)
    if tip_ratio <= knots[0]:
        return _poly(_TAU_FIT[knots[0]], taper_ratio)
    if tip_ratio >= knots[-1]:
        return _poly(_TAU_FIT[knots[-1]], taper_ratio)
    for lo, hi in zip(knots, knots[1:]):
        if lo <= tip_ratio <= hi:
            tlo = _poly(_TAU_FIT[lo], taper_ratio)
            thi = _poly(_TAU_FIT[hi], taper_ratio)
            return tlo + (tip_ratio - lo) * (thi - tlo) / (hi - lo)
    return _poly(_TAU_FIT[knots[-1]], taper_ratio)  # pragma: no cover


# --------------------------------------------------------------------------- #
# Schrenk spanwise distribution
# --------------------------------------------------------------------------- #
@dataclass
class SpanwiseTable:
    """The per-strip Schrenk distribution plus the surface scalars.

    All lists are inboard -> outboard, one entry per strip, aligned with the
    WINGGEOM element table. ``ccl_*`` are the ``c*cl`` span loads (inches); the
    bare ``cl_*`` are the section lift coefficients (``ccl/c``). ``recovered_cl``
    is the discrete integral of the total distribution (the closure check; should
    match ``target_cl``); ``recovered_cl_additive`` is the additive-only integral
    (the manual's "CL=1.00061").
    """
    ye: List[float] = field(default_factory=list)
    chord: List[float] = field(default_factory=list)
    cl_additive: List[float] = field(default_factory=list)
    ccl_additive: List[float] = field(default_factory=list)
    cl_basic: List[float] = field(default_factory=list)
    ccl_basic: List[float] = field(default_factory=list)
    cl_total: List[float] = field(default_factory=list)
    ccl_total: List[float] = field(default_factory=list)
    mo_wing: float = 0.0       # Mo, wing zero-twist lift-curve slope (per deg)
    m_wing: float = 0.0        # M, wing lift-curve slope incl. AR/TAU (per deg)
    tau: float = 0.0
    awo: float = 0.0           # chord-weighted mean zero-lift angle (deg)
    area_total: float = 0.0    # S, in^2
    span: float = 0.0          # B, in
    mac: float = 0.0           # mean aerodynamic chord (in), for the AIRLOAD4 sweep term
    aspect_ratio: float = 0.0
    target_cl: float = 1.0
    recovered_cl: float = 0.0
    recovered_cl_additive: float = 0.0
    sweep_deg: float = 0.0     # 25%-chord sweep applied (AIRLOAD4); 0 = unswept
    airload4: bool = False     # True when the swept/high-Mach branch was used


def _twist_angle(twist, ye: float) -> float:
    """Section zero-lift angle (deg) at butt line ``ye`` from the twist table.

    ``twist`` is a list of ``(butt line Y, angle deg)`` points; reuse the WINGGEOM
    edge interpolator by passing ``(angle, Y)`` pairs so it returns the angle at
    ``ye``. An empty table means an untwisted wing (angle 0 -> zero basic lift).
    """
    if not twist:
        return 0.0
    return interp_x([(ang, yb) for (yb, ang) in twist], ye)


def schrenk_distribution(geom: SurfaceInput, aero: AeroSurfaceInput) -> SpanwiseTable:
    """Spanwise Schrenk additive + basic + combined distribution for one surface."""
    if geom.elements < 2:
        raise ValueError(f"surface '{geom.name}' needs >= 2 integration elements")
    if len(geom.leading_edge) < 2 or len(geom.trailing_edge) < 2:
        raise ValueError(f"surface '{geom.name}' needs >= 2 LE and TE points")

    yroot = geom.leading_edge[0][1]
    ytip = geom.leading_edge[-1][1]
    h = geom.elements
    dy = (ytip - yroot) / h
    mo = aero.section_slope

    # First strip pass: geometry, the slope sums Mo and Awo's denominator.
    ye_list: List[float] = []
    chord: List[float] = []
    ac_list: List[float] = []
    area_side = 0.0           # SUM(c*dy) on one side
    sum_c2dy = 0.0            # SUM(c^2*dy), for the mean aerodynamic chord
    sum_mocdy = 0.0           # SUM(mo*c*dy)
    sum_mocac = 0.0           # SUM(mo*c*ac*dy)
    for el in range(h):
        ye = yroot + dy / 2 + el * dy
        c = interp_x(geom.trailing_edge, ye) - interp_x(geom.leading_edge, ye)
        ac = _twist_angle(aero.twist, ye)
        ye_list.append(ye)
        chord.append(c)
        ac_list.append(ac)
        area_side += c * dy
        sum_c2dy += c * c * dy
        sum_mocdy += mo * c * dy
        sum_mocac += mo * c * ac * dy

    area_total = 2 * area_side                       # S, both sides (symmetric wing)
    span = 2 * ytip if geom.symmetric else (ytip - yroot)
    mo_wing = sum_mocdy / area_side                  # Mo = SUM(mo*c*dy)/(S/2)
    awo = sum_mocac / sum_mocdy if sum_mocdy else 0.0
    aspect_ratio = (2 * ytip) ** 2 / (2 * area_side) if geom.symmetric else (ytip - yroot) ** 2 / area_side
    mo_rad = mo * DEG_PER_RAD                          # section slope per radian
    m_wing = mo / (1 + mo_rad / (math.pi * aspect_ratio) * (1 + aero.tau if aero.tau is not None
                                                       else 1 + _tau(aero.taper_ratio, aero.tip_ratio)))

    mac = sum_c2dy / area_side if area_side else 0.0   # MAC = SUM(c^2*dy)/SUM(c*dy)
    airload4 = use_airload4(aero)
    table = SpanwiseTable(
        mo_wing=mo_wing, awo=awo, area_total=area_total, span=span, mac=mac,
        aspect_ratio=aspect_ratio, m_wing=m_wing, target_cl=aero.target_cl,
        tau=aero.tau if aero.tau is not None else _tau(aero.taper_ratio, aero.tip_ratio),
        sweep_deg=aero.sweep_deg if airload4 else 0.0, airload4=airload4,
    )

    # Second pass: additive (CL=1), basic (twist), and the combined span load.
    ell = 4 * area_total / (math.pi * span)               # 4S/(pi*B), elliptic peak chord
    sum_ccl_add = sum_ccl_tot = 0.0
    for ye, c, ac in zip(ye_list, chord, ac_list):
        ccl_add = 0.5 * (mo * c / mo_wing + ell * math.sqrt(1 - (2 * ye / span) ** 2))
        aa = ac - awo
        ccl_bas = (mo / 2) * aa * c
        ccl_tot = ccl_add * aero.target_cl + ccl_bas
        table.ye.append(ye)
        table.chord.append(c)
        table.ccl_additive.append(ccl_add)
        table.cl_additive.append(ccl_add / c)
        table.ccl_basic.append(ccl_bas)
        table.cl_basic.append(ccl_bas / c)
        table.ccl_total.append(ccl_tot)
        table.cl_total.append(ccl_tot / c)
        sum_ccl_add += ccl_add * dy
        sum_ccl_tot += ccl_tot * dy

    if airload4 and aero.sweep_deg:
        # AIRLOAD4 sweepback: redistribute + renormalize the operating (target-CL)
        # distribution. The additive/basic split stays the unswept decomposition;
        # only the combined ``ccl_total`` is swept (report + closure at target CL).
        # The deliverable path re-applies this per condition at its own CL.
        swept = _sweep_operating(table.ccl_total, table.ye, span, mac,
                                 aero.target_cl, area_side, dy, aero.sweep_deg)
        table.ccl_total = swept
        table.cl_total = [cc / c for cc, c in zip(swept, table.chord)]

    table.recovered_cl_additive = math.fsum(ca * dy for ca in table.ccl_additive) / area_side
    table.recovered_cl = math.fsum(ct * dy for ct in table.ccl_total) / area_side
    return table


def _sweep_operating(ccl_op: List[float], ye: List[float], span: float, mac: float,
                     cl_op: float, area_side: float, dy: float,
                     sweep_deg: float) -> List[float]:
    """Sweepback redistribution + renormalization of an OPERATING span load (AIRLOAD4.BAS).

    Pope & Haney (JAS Aug 1949 p505 Eq. 12.38; Pope, *Basic Wing and Airfoil
    Theory* 1951) redistribute the operating ``c*cl`` for sweepback and then
    renormalize it back to the operating ``CL``. AIRLOAD4.BAS does this on the
    *combined operating* distribution (``COL16 = c*kcl/(MAC*CL)``), not the
    additive part alone, so wing twist is redistributed too:

        COL18 = (1 - 2y/b)*2*(1 - cos Λ)         Pope sweep term (dimensionless)
        COL19 = COL16 - COL18                    swept, NOT yet renormalized
        CLCOL19 = SUM(COL19*c*dy)/(S/2)          recovered CL of the swept dist.
        COL20 = COL19 / CLCOL19                  <-- renormalize to the operating CL

    Working directly in ``c*cl`` units (COL19*MAC*CL): ``delta`` is the Pope term
    scaled to ``c*cl`` at the operating CL, and the ``COL19 -> COL20`` divide
    becomes a single ``cl_op / recovered`` rescale where ``recovered`` is the swept
    distribution's *span-load* CL (``SUM(c*cl)*dy/(S/2)``), so the result
    re-integrates to ``cl_op`` **exactly**. This ``COL20`` renormalization is the
    step the original port omitted (M1-3): without it the swept ``c*cl`` integrates
    to less than ``cl_op`` (0.94 at Λ=20°, 0.87 at Λ=30°), losing 6-13% of the lift.

    Normalization note (documented deviation): the verbatim COL16 line in the
    bundled listing is OCR-garbled, and the reconstructed ``COL16 = c*kcl/(MAC*CL)``
    makes ``CLCOL19 = SUM(COL19*c*dy)/(S/2)`` a chord-weighted sum that closes only
    to ~0.3% (recovered_cl 0.4983 on the flagship, not 0.5000). Per project
    Decision 3 ("modernize the math") and M1-3's closure requirement, this uses the
    physically-correct span-load renormalization (no extra chord weight), which
    restores exactly the operating CL. Same intent as COL20; differs from the
    literal chord-weighted form by ~0.3%. Reduces to the additive-only result on an
    untwisted wing.

    Compressibility (high Mach) is already carried by the operating ``CL`` from
    FLTLOADS' Glauert factor, so the high-Mach trigger adds no further shape change
    here. The Pope term vanishes at the tip and at Λ=0.
    """
    cos_lam = math.cos(math.radians(sweep_deg))
    col19 = [cc - (1.0 - 2.0 * y / span) * 2.0 * (1.0 - cos_lam) * mac * cl_op
             for cc, y in zip(ccl_op, ye)]
    recovered = math.fsum(c19 * dy for c19 in col19) / area_side if area_side else 0.0
    factor = cl_op / recovered if recovered else 1.0
    return [c19 * factor for c19 in col19]


def _interp_yv(table, y: float, default: float = 0.0) -> float:
    """Interpolate a ``(butt line Y, value)`` table at ``y`` (reuses interp_x)."""
    if not table:
        return default
    return interp_x([(v, yb) for (yb, v) in table], y)


def air_load_distribution(geom: SurfaceInput, aero: AeroSurfaceInput, cl: float,
                          v_eas_kt: float, wrp_waterline: float,
                          dihedral_deg: float) -> WingLoadResult:
    """Air-load shear / bending / torsion along the 25% chord (AIRLOADS.BAS 4500-5060).

    Scales the C1 Schrenk section-lift distribution to the operating wing ``cl``,
    builds per-strip lift/drag/pitching-moment forces at dynamic pressure
    ``q = V^2/295`` (V in KEAS), rotates them into the airplane reference by the
    angle of attack ``ANRW2WL = CL/M - Awo`` (M the wing lift-curve slope), and
    integrates tip->root to the cumulative shears, bending moments and torsion.
    Drag per strip is the computed induced drag ``cl*ai/57.3`` plus the input
    section profile drag ``CDO`` (``aero.profile_drag``); torsion sums the lift
    offset about the 25% chord, the drag offset in Z and the section pitching
    moment (``aero.section_cm``). Stations are ordered root->tip.

    Reference: AIRLOADS.BAS subroutine 4500 (lines 4600-5060); worked example
    Appendix A "Airloads for Case 22 PHAA" p206 (CL 1.52, V 117.4: root SZ +6470,
    MXX +516955, MYY -79003, MZZ -91283).
    """
    t = schrenk_distribution(geom, aero)
    h = len(t.ye)
    dy = (t.ye[-1] - t.ye[0]) / (h - 1) if h > 1 else 0.0  # uniform strip width
    mo = aero.section_slope
    alpha = cl / t.m_wing                       # ALPHA = CL/(MM/57.3), deg
    an = alpha - t.awo                           # ANRW2WL, deg
    q = dynamic_pressure_psf(v_eas_kt)
    cos_an, sin_an = math.cos(an / DEG_PER_RAD), math.sin(an / DEG_PER_RAD)

    # Operating section cl per strip (unswept additive/basic scaled to this case CL).
    # On the AIRLOAD4 swept branch, redistribute + renormalize the combined operating
    # span load at THIS condition's CL -- AIRLOAD4.BAS sweeps the operating distribution
    # per case, so the twist contribution is swept and the result re-integrates to `cl`.
    kcl_list = [t.cl_basic[j] + cl * t.cl_additive[j] for j in range(h)]
    if t.airload4 and t.sweep_deg:
        ccl_op = [k * t.chord[j] for j, k in enumerate(kcl_list)]
        ccl_op = _sweep_operating(ccl_op, t.ye, t.span, t.mac, cl,
                                  t.area_total / 2.0, dy, t.sweep_deg)
        kcl_list = [cc / t.chord[j] for j, cc in enumerate(ccl_op)]

    # Per-strip forces (root->tip) and the 25% chord coordinates.
    cx25: List[float] = []
    zc: List[float] = []
    lz: List[float] = []
    dx: List[float] = []
    ml: List[float] = []
    for j in range(h):
        ye = t.ye[j]
        c = t.chord[j]
        kcl = kcl_list[j]                                      # operating section cl (swept if AIRLOAD4)
        refang = _twist_angle(aero.twist, ye)                  # WL to section zero-lift
        ai = (alpha - t.awo + refang) - kcl / mo              # induced angle of attack
        cid = kcl * ai / DEG_PER_RAD                                  # induced drag coefficient
        cd = _interp_yv(aero.profile_drag, ye) + cid           # + section profile drag
        cm = _interp_yv(aero.section_cm, ye)
        lift = kcl * c * dy * q / IN2_PER_FT2
        drag = cd * c * dy * q / IN2_PER_FT2
        moment = cm * c * c * dy * q / IN2_PER_FT2
        lz.append(lift * cos_an + drag * sin_an)
        dx.append(drag * cos_an - lift * sin_an)
        ml.append(moment)
        cx25.append(interp_x(geom.leading_edge, ye) + 0.25 * c)
        zc.append(wrp_waterline + math.tan(dihedral_deg / DEG_PER_RAD) * ye)

    # Integrate tip->root: cumulative shears, bending moments and torsion.
    sz = [0.0] * h
    sx = [0.0] * h
    mxx = [0.0] * h
    mzz = [0.0] * h
    tyy = [0.0] * h
    tvyy = [0.0] * h
    trq = [0.0] * h
    sz[h - 1] = lz[h - 1]
    sx[h - 1] = dx[h - 1]
    trq[h - 1] = ml[h - 1]
    for i in range(h - 2, -1, -1):
        sz[i] = sz[i + 1] + lz[i]
        sx[i] = sx[i + 1] + dx[i]
        mxx[i] = mxx[i + 1] + sz[i + 1] * dy
        mzz[i] = mzz[i + 1] + sx[i + 1] * (t.ye[i + 1] - t.ye[i])
        tyy[i] = tyy[i + 1] - sz[i + 1] * (cx25[i + 1] - cx25[i])
        tvyy[i] = tvyy[i + 1] + sx[i + 1] * (zc[i + 1] - zc[i])
        trq[i] = trq[i + 1] + ml[i]

    stations = [
        WingStationLoad(
            x=cx25[i], y=t.ye[i], z=zc[i], fx=dx[i], fz=lz[i], sx=sx[i], sz=sz[i],
            mxx=mxx[i], myy=tyy[i] + tvyy[i] + trq[i], mzz=mzz[i],
        )
        for i in range(h)
    ]
    return WingLoadResult(case="", stations=stations)


def spanwise_distribution(geom: SurfaceInput, aero: AeroSurfaceInput) -> ConditionResult:
    """One surface's Schrenk distribution as a reportable :class:`ConditionResult`.

    Scalars first (slopes, TAU, span, the closure check), then the combined span
    load ``c*cl`` and section ``cl`` at each strip. The additive/basic split lives
    on :func:`schrenk_distribution`'s :class:`SpanwiseTable` for downstream use.
    """
    t = schrenk_distribution(geom, aero)
    values: List[LoadValue] = [
        LoadValue("Wing lift-curve slope Mo", t.mo_wing, "1/deg", key="wing_lift_curve_slope_mo"),
        LoadValue("Wing lift-curve slope M (AR,TAU)", t.m_wing, "1/deg", key="wing_lift_curve_slope_m_ar_tau"),
        LoadValue("TAU planform correction", t.tau, key="tau_planform_correction"),
        LoadValue("Aspect ratio", t.aspect_ratio, key="aspect_ratio"),
        LoadValue("Total wing area S", t.area_total, "in^2", key="total_wing_area_s"),
        LoadValue("Span B", t.span, "in", key="span_b"),
        LoadValue("Mean zero-lift angle Awo", t.awo, "deg", key="mean_zero_lift_angle_awo"),
        LoadValue("Target CL", t.target_cl, key="target_cl"),
        LoadValue("Recovered CL (closure)", t.recovered_cl, key="recovered_cl_closure"),
    ]
    for i, (ye, ccl, cl) in enumerate(zip(t.ye, t.ccl_total, t.cl_total), start=1):
        values.append(LoadValue(f"Elem {i} (Y={ye:.3f}) c*cl", ccl, "in",
                                key=f"elem{i}_ccl"))
        values.append(LoadValue(f"Elem {i} (Y={ye:.3f}) cl", cl, key=f"elem{i}_cl"))
    method = ("Schrenk + AIRLOAD4 sweep correction (Ref 1 Ch 12)"
              if t.airload4 else "Schrenk method (Ref 1 Ch 7)")
    return ConditionResult(
        title=f"Spanwise airload distribution: {geom.name}",
        far_reference=_FAR,
        values=values,
        note=f"{method}; span load c*cl at CL={t.target_cl:g}.",
    )


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "airloads"


def run(project: Project) -> ModuleResult:
    """Run AIRLOADS over every aero surface that has a matching planform."""
    if project.aero is None or not project.aero.surfaces:
        raise MissingInputError("Project has no 'aero' surfaces for the airloads module")
    if project.geometry is None or not project.geometry.surfaces:
        raise MissingInputError("airloads needs 'geometry' surfaces for the wing planform")

    conditions: List[ConditionResult] = []
    for aero in project.aero.surfaces:
        geom = project.geometry.by_name(aero.name)
        if geom is None:
            raise ValueError(f"aero surface '{aero.name}' has no matching geometry surface")
        cond = spanwise_distribution(geom, aero)
        if project.is_concept:
            cond.note += " Concept mode -- unverified extrapolation past the FAR23 band."
        conditions.append(cond)
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
