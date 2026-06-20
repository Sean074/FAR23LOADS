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

from ..constants import PI
from ..models import (
    AeroSurfaceInput,
    ConditionResult,
    LoadValue,
    ModuleResult,
    Project,
    SurfaceInput,
    WingLoadResult,
    WingStationLoad,
)
from ..registry import register
from .wing_geometry import _interp_x

_DEG = 57.3  # AIRLOADS.BAS uses 57.3 for the rad<->deg factor; kept for fidelity

_FAR = "23.301"  # airload distribution basis (Schrenk)


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
    return sum(c * x ** i for i, c in enumerate(coeffs))


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
    aspect_ratio: float = 0.0
    target_cl: float = 1.0
    recovered_cl: float = 0.0
    recovered_cl_additive: float = 0.0


def _twist_angle(twist, ye: float) -> float:
    """Section zero-lift angle (deg) at butt line ``ye`` from the twist table.

    ``twist`` is a list of ``(butt line Y, angle deg)`` points; reuse the WINGGEOM
    edge interpolator by passing ``(angle, Y)`` pairs so it returns the angle at
    ``ye``. An empty table means an untwisted wing (angle 0 -> zero basic lift).
    """
    if not twist:
        return 0.0
    return _interp_x([(ang, yb) for (yb, ang) in twist], ye)


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
    sum_mocdy = 0.0           # SUM(mo*c*dy)
    sum_mocac = 0.0           # SUM(mo*c*ac*dy)
    for el in range(h):
        ye = yroot + dy / 2 + el * dy
        c = _interp_x(geom.trailing_edge, ye) - _interp_x(geom.leading_edge, ye)
        ac = _twist_angle(aero.twist, ye)
        ye_list.append(ye)
        chord.append(c)
        ac_list.append(ac)
        area_side += c * dy
        sum_mocdy += mo * c * dy
        sum_mocac += mo * c * ac * dy

    area_total = 2 * area_side                       # S, both sides (symmetric wing)
    span = 2 * ytip if geom.symmetric else (ytip - yroot)
    mo_wing = sum_mocdy / area_side                  # Mo = SUM(mo*c*dy)/(S/2)
    awo = sum_mocac / sum_mocdy if sum_mocdy else 0.0
    aspect_ratio = (2 * ytip) ** 2 / (2 * area_side) if geom.symmetric else (ytip - yroot) ** 2 / area_side
    mo_rad = mo * 180.0 / PI                          # section slope per radian
    m_wing = mo / (1 + mo_rad / (PI * aspect_ratio) * (1 + aero.tau if aero.tau is not None
                                                       else 1 + _tau(aero.taper_ratio, aero.tip_ratio)))

    table = SpanwiseTable(
        mo_wing=mo_wing, awo=awo, area_total=area_total, span=span,
        aspect_ratio=aspect_ratio, m_wing=m_wing, target_cl=aero.target_cl,
        tau=aero.tau if aero.tau is not None else _tau(aero.taper_ratio, aero.tip_ratio),
    )

    # Second pass: additive (CL=1), basic (twist), and the combined span load.
    ell = 4 * area_total / (PI * span)               # 4S/(pi*B), elliptic peak chord
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

    table.recovered_cl_additive = sum_ccl_add / area_side
    table.recovered_cl = sum_ccl_tot / area_side
    return table


def _interp_yv(table, y: float, default: float = 0.0) -> float:
    """Interpolate a ``(butt line Y, value)`` table at ``y`` (reuses _interp_x)."""
    if not table:
        return default
    return _interp_x([(v, yb) for (yb, v) in table], y)


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
    q = v_eas_kt ** 2 / 295.0
    cos_an, sin_an = math.cos(an / _DEG), math.sin(an / _DEG)

    # Per-strip forces (root->tip) and the 25% chord coordinates.
    cx25: List[float] = []
    zc: List[float] = []
    lz: List[float] = []
    dx: List[float] = []
    ml: List[float] = []
    for j in range(h):
        ye = t.ye[j]
        c = t.chord[j]
        kcl = t.cl_basic[j] + cl * t.cl_additive[j]            # operating section cl
        refang = _twist_angle(aero.twist, ye)                  # WL to section zero-lift
        ai = (alpha - t.awo + refang) - kcl / mo              # induced angle of attack
        cid = kcl * ai / _DEG                                  # induced drag coefficient
        cd = _interp_yv(aero.profile_drag, ye) + cid           # + section profile drag
        cm = _interp_yv(aero.section_cm, ye)
        lift = kcl * c * dy * q / 144.0
        drag = cd * c * dy * q / 144.0
        moment = cm * c * c * dy * q / 144.0
        lz.append(lift * cos_an + drag * sin_an)
        dx.append(drag * cos_an - lift * sin_an)
        ml.append(moment)
        cx25.append(_interp_x(geom.leading_edge, ye) + 0.25 * c)
        zc.append(wrp_waterline + math.tan(dihedral_deg / _DEG) * ye)

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
        LoadValue("Wing lift-curve slope Mo", t.mo_wing, "1/deg"),
        LoadValue("Wing lift-curve slope M (AR,TAU)", t.m_wing, "1/deg"),
        LoadValue("TAU planform correction", t.tau),
        LoadValue("Aspect ratio", t.aspect_ratio),
        LoadValue("Total wing area S", t.area_total, "in^2"),
        LoadValue("Span B", t.span, "in"),
        LoadValue("Mean zero-lift angle Awo", t.awo, "deg"),
        LoadValue("Target CL", t.target_cl),
        LoadValue("Recovered CL (closure)", t.recovered_cl),
    ]
    for i, (ye, ccl, cl) in enumerate(zip(t.ye, t.ccl_total, t.cl_total), start=1):
        values.append(LoadValue(f"Elem {i} (Y={ye:.3f}) c*cl", ccl, "in"))
        values.append(LoadValue(f"Elem {i} (Y={ye:.3f}) cl", cl))
    return ConditionResult(
        title=f"Spanwise airload distribution: {geom.name}",
        far_reference=_FAR,
        values=values,
        note=f"Schrenk method (Ref 1 Ch 7); span load c*cl at CL={t.target_cl:g}.",
    )


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "airloads"


def run(project: Project) -> ModuleResult:
    """Run AIRLOADS over every aero surface that has a matching planform."""
    if project.aero is None or not project.aero.surfaces:
        raise ValueError("Project has no 'aero' surfaces for the airloads module")
    if project.geometry is None or not project.geometry.surfaces:
        raise ValueError("airloads needs 'geometry' surfaces for the wing planform")

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
