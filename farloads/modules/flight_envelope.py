"""Flight envelope (V-n diagram) + balancing tail loads, from FLTLOADS.BAS.

FLTLOADS balances the airplane at every corner of the FAR 23.333 maneuver and
gust flight envelope: at each point it finds the angle of attack that produces
the required normal load factor and the horizontal-tail load that zeroes the
pitching moment about the CG. The balanced matrix (one row per condition x CG x
altitude) is the core of the loads analysis -- SELECT prunes it to the critical
points and WINGINER/NETLOADS consume the wing loads (Reference 1 Ch 8).

The balance (FLTLOADS.BAS subroutine 3900) takes the airplane-*less-tail*
aerodynamic coefficients as polynomials (produced by the Ch 7 aero-coefficients
program and entered as input here -- AIRLOADS/Step C1 does not yet emit them):

    CL = C0 + (C1*a + C2*a^2 + C3*a^3 + C4*a^4) * G/Gmn        (a = AoA, deg)
    CD = D0 + D1*CL + D2*CL^2 + D3*CL^3 + D4*CL^4
    CM = M0 + (M1*a + M2*a^2 + M3*a^3 + M4*a^4) * G/Gmn

with the Glauert compressibility factor ``G = 1/sqrt(1 - M^2)`` applied relative
to the reference Mach ``Mn`` at which the coefficients were obtained. Wing forces
relative to the wind and rotated into the airplane reference:

    L = CL*Q*S,  D = CD*Q*S,  M = CM*Q*S*MAC,   Q = V^2/295   (V in KEAS)
    LZ = L*cos(a) + D*sin(a),  DX = D*cos(a) - L*sin(a)

The balancing horizontal-tail load takes moments about the CG (Ch 8 "Equations"):

    LT = [MM + LZ*(Xcg - Xw) - DX*(Zcg - Zw)] / (XT - Xcg)
    NZ = (LZ + LT) / W

where ``Xw``/``Zw`` are the station/waterline of 25% wing MAC and ``XT`` the tail
centre of pressure (``XTC`` ~ 5% tail MAC flaps-up, ``XTF`` ~ 25% flaps-down; the
Ch 8 "Assumption" -- SELECT later refines this rationally). The angle of attack
is iterated until ``NZ`` matches the required load factor; for stall-line
conditions the dynamic pressure is then iterated until ``CL`` equals the
Mach-adjusted stall ``CL``. The stall CL varies with Mach by a least-squares fit
to the CLmax-vs-Mach curve of an AR-6 23016/23009 wing (Ch 8).

Gust load factors (FAR 23.341, subroutine 4864):

    mu = 2(W/S) / (rho * (MAC/12) * a * g),   Kg = 0.88*mu / (5.3 + mu)
    NZ = 1 + NG * Kg * Ude * V * a / (498 * W/S)

with ``a`` the wing lift-curve slope per degree (C1, Glauert-corrected) and the
derived gust velocity ``Ude`` 50 fps at VC / 25 fps at VD (tapering above
20,000 ft). The maneuver/gust corner set per category follows FLTLOADS.BAS lines
1000-1594 (cruise configuration).

Reference: FLTLOADS.BAS (Appendix C p421-428), Ref 1 Ch 8; worked example
Appendix A "V-n Data" p179-180 (cruise, CG1: MAN A V 121.3 / NZ +3.80 / LZW
+12419 / LT +493; GUST +C NZ +3.96; BAL A LT +18).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from ..models import (
    AeroCoeffSet,
    CgCase,
    ConditionResult,
    EnvelopeResult,
    FlightLoadsInput,
    LoadValue,
    ModuleResult,
    Project,
    TailBalanceLoad,
    VnPoint,
)
from ..registry import register
from .structural_speeds import _maneuver_load_factors, design_speeds

_FAR = "23.333/23.337/23.341/23.421"
_DEG = 57.2957795  # FLTLOADS.BAS uses 57.3; kept as a named factor for clarity
_RAD = math.pi / 180.0


# --------------------------------------------------------------------------- #
# Atmosphere & compressibility (FLTLOADS.BAS subroutine 3900)
# --------------------------------------------------------------------------- #
# FLTLOADS uses its own speed-of-sound constant (518.688 vs the shared
# standard_atmosphere's 518.4); the ~0.03% difference matters near the Mach cap,
# so the program's exact form is replicated here for oracle fidelity. The density
# ratio is identical to constants.standard_atmosphere.
def _sigma(alt_ft: float) -> float:
    if alt_ft > 35332.0:
        return (7.2725e-04 * math.exp(-4.778e-05 * (alt_ft - 35332.0))) / 0.002378
    return (1.0 - 6.879e-06 * alt_ft) ** 4.258


def _speed_of_sound(alt_ft: float) -> float:
    if alt_ft > 35332.0:
        return 575.0
    return 29.02436 * math.sqrt(518.688 - 0.003566 * alt_ft)


def _clmax_curve(mach: float) -> float:
    """CLmax as a function of Mach (Ch 8 least-squares fit, AR-6 23016/23009)."""
    m = mach
    return (1.19367 + 0.32739 * m + 10.8352 * m ** 2 - 44.4985 * m ** 3
            + 51.8759 * m ** 4 - 19.5434 * m ** 5)


def _poly(coeffs, x: float) -> float:
    return sum(c * x ** i for i, c in enumerate(coeffs))


# --------------------------------------------------------------------------- #
# The balance (FLTLOADS.BAS subroutine 3900)
# --------------------------------------------------------------------------- #
@dataclass
class _Balanced:
    v_eas: float
    nz: float
    alpha: float
    g: float
    cl: float
    mm: float
    lz: float
    lt: float
    dx: float


def _balance(n: float, v_init: float, mach_cap: float, config: AeroCoeffSet,
             cg: CgCase, fl: FlightLoadsInput, altitude_ft: float) -> _Balanced:
    """Balance one flight condition: solve AoA for load factor ``n`` (subr 3900).

    ``v_init`` is the equivalent airspeed (a guess for stall-line conditions,
    where the dynamic pressure is then iterated until CL hits the stall limit).
    """
    xt = fl.xtf if config.flaps_down else fl.xtc
    s = fl.wing_area_sqft
    mac = fl.mac
    gmn = 1.0 / math.sqrt(1.0 - fl.mn ** 2)
    kmn = _clmax_curve(fl.mn)
    c0, c1, c2, c3, c4 = config.lift
    sig = _sigma(altitude_ft)
    a_sound = _speed_of_sound(altitude_ft)

    q = v_init ** 2 / 295.0
    last: Optional[_Balanced] = None
    for _ in range(200):  # outer: dynamic-pressure iteration (stall line)
        v = math.sqrt(295.0 * q)
        vt = v / math.sqrt(sig)
        mh = vt / a_sound
        if mh > mach_cap:
            mh = mach_cap
        vt = mh * a_sound
        v = vt * math.sqrt(sig)
        q = v ** 2 / 295.0
        g = 1.0 / math.sqrt(1.0 - mh ** 2)
        stall_cl = config.stall_cl * _clmax_curve(mh) / kmn
        neg_stall_cl = config.neg_stall_cl * _clmax_curve(mh) / kmn

        al = -10.0 if n < 0 else 10.0
        da = 10.0
        cl = lz = dx = mm = 0.0
        for _ in range(400):  # inner: angle-of-attack iteration
            cl = c0 + (c1 * al + c2 * al ** 2 + c3 * al ** 3 + c4 * al ** 4) * g / gmn
            cd = _poly(config.drag, cl)
            cm = config.moment[0] + (config.moment[1] * al + config.moment[2] * al ** 2
                                     + config.moment[3] * al ** 3 + config.moment[4] * al ** 4) * g / gmn
            ll = cl * q * s
            d = cd * q * s
            mm = cm * q * s * mac
            lz = ll * math.cos(al * _RAD) + d * math.sin(al * _RAD)
            dx = d * math.cos(al * _RAD) - ll * math.sin(al * _RAD)
            lt = (lz * (cg.xcg - fl.xw) - dx * (cg.zcg - fl.zw) + mm) / (xt - cg.xcg)
            nz = (lz + lt) / cg.weight_lb
            if n - 0.005 <= nz <= n + 0.005:
                break
            da = 0.75 * da
            if nz > n + 0.005:
                al -= da
            elif nz < n - 0.005:
                al += da
            if da < 0.005:
                da = 0.005
        last = _Balanced(v_eas=v, nz=nz, alpha=al, g=g, cl=cl, mm=mm, lz=lz,
                         lt=(lz * (cg.xcg - fl.xw) - dx * (cg.zcg - fl.zw) + mm) / (xt - cg.xcg),
                         dx=dx)

        # Dynamic-pressure iteration to bring CL onto the (Mach-adjusted) stall line.
        if neg_stall_cl - 0.005 <= cl <= stall_cl + 0.005:
            break
        nw = n * cg.weight_lb
        if cl > stall_cl + 0.005:
            q = q + 0.75 * (-q / ((cl - stall_cl) * s * q / nw - 1.0) - q)
        elif cl < neg_stall_cl - 0.005:
            q = q + 0.75 * (-q / ((cl - neg_stall_cl) * s * q / nw - 1.0) - q)
    assert last is not None
    return last


def _gust_ude(ref: str, altitude_ft: float) -> float:
    """Derived gust velocity Ude (fps): 50 @ VC, 25 @ VD/VF, tapering >20,000 ft."""
    h = altitude_ft
    if ref == "C":
        return 50.0 if h <= 20000.0 else 50.0 - (25.0 / 30000.0) * (h - 20000.0)
    if ref == "D":
        return 25.0 if h <= 20000.0 else 25.0 - (12.5 / 30000.0) * (h - 20000.0)
    return 25.0  # VF


def _gust_load_factor(ng: int, v: float, mach_cap: float, ref: str, config: AeroCoeffSet,
                      cg: CgCase, fl: FlightLoadsInput, altitude_ft: float) -> float:
    """Gust normal load factor (FAR 23.341, subroutine 4864).

    ``ref`` is the speed the gust is applied at ("C" = VC, "D" = VD, "F" = VF),
    selecting the derived gust velocity Ude.
    """
    h = altitude_ft
    sig = _sigma(h)
    ude = _gust_ude(ref, h)
    vt = v / math.sqrt(sig)
    a_sound = _speed_of_sound(h)
    mh = vt / a_sound
    if mh > mach_cap:
        mh = mach_cap
    vt = mh * a_sound
    v = vt * math.sqrt(sig)
    g = 1.0 / math.sqrt(1.0 - mh ** 2)
    gmn = 1.0 / math.sqrt(1.0 - fl.mn ** 2)
    c1 = config.lift[1] * g / gmn          # lift-curve slope per deg, Glauert-corrected
    rho = 0.002378 * sig
    ws = cg.weight_lb / fl.wing_area_sqft
    ug = 2.0 * ws / (rho * fl.mac / 12.0 * c1 * _DEG * 32.2)
    kg = 0.88 * ug / (5.3 + ug)
    return 1.0 + ng * kg * ude * v * c1 * _DEG / (498.0 * ws)


# --------------------------------------------------------------------------- #
# Design speeds / load factors (read from STRSPEED, the owner)
# --------------------------------------------------------------------------- #
@dataclass
class _DesignInputs:
    va: float
    vc: float
    vd: float
    vf: float
    mc: float
    md: float
    n_pos: float
    n_neg: float
    category: str


def _design_inputs(project: Project) -> _DesignInputs:
    """Pull VA/VC/VD/VF, MC/MD and the limit load factors from STRSPEED."""
    vals = {}
    for cond in design_speeds(project, project.speeds):
        for lv in cond.values:
            vals[lv.label] = lv.value
    sp = project.speeds
    cat = sp.category.upper()
    n_pos, _, n_neg, _ = _maneuver_load_factors(cat, sp.weight_lb, sp.chosen_n, sp.chosen_nneg)
    return _DesignInputs(
        va=vals["Maneuver speed VA"], vc=vals["Cruise speed VC"],
        vd=vals["Dive speed VD"], vf=vals["Flap speed VF"],
        mc=vals["Cruise Mach MC"], md=vals["Dive Mach MD"],
        n_pos=n_pos, n_neg=n_neg, category=cat,
    )


# --------------------------------------------------------------------------- #
# Cruise maneuver + gust corner set (FLTLOADS.BAS lines 1000-1594)
# --------------------------------------------------------------------------- #
def _config_points(config: AeroCoeffSet, cg: CgCase, fl: FlightLoadsInput,
                   alt: float, di: _DesignInputs, case: int) -> "tuple[List[VnPoint], int]":
    """The cruise maneuver+gust V-n corner points for one config / CG / altitude."""
    w = cg.weight_lb
    s = fl.wing_area_sqft
    pts: List[VnPoint] = []
    state = {"v9": 0.0}

    def stall_v(n: float, clmax: float) -> float:
        # FLTLOADS.BAS: V = 0.9*sqrt(N*W*295/(CLmax*S)); N and CLmax share a sign.
        return 0.9 * math.sqrt(n * w * 295.0 / (clmax * s))

    def add(cond: str, n: float, v: float, cap: float) -> _Balanced:
        nonlocal case
        b = _balance(n, v, cap, config, cg, fl, alt)
        case += 1
        pts.append(VnPoint(
            case=case, condition=cond, config=config.name, cg=cg.name, altitude_ft=alt,
            v_eas_kt=b.v_eas, nz=b.nz, alpha_deg=b.alpha, g_corr=b.g, cl=b.cl,
            m_wf=b.mm, lzw=b.lz, lt=b.lt, dx=b.dx,
        ))
        return b

    def add_gust(cond: str, ng: int, v: float, cap: float, ref: str) -> _Balanced:
        n = _gust_load_factor(ng, v, cap, ref, config, cg, fl, alt)
        return add(cond, n, v, cap)

    cat = di.category
    np_, nneg = di.n_pos, di.n_neg
    scl, ncl = config.stall_cl, config.neg_stall_cl

    add("STALL 1G", 1.0, stall_v(1.0, scl), di.md)
    state["v9"] = add("STALL +N", np_, stall_v(np_, scl), di.md).v_eas
    add("MAN A", np_, di.va, di.mc)
    add("MAN C", np_, di.vc, di.mc)
    add("MAN D", np_, di.vd, di.md)
    add("MAN -D", -1.0 if cat in ("U", "A") else 0.0, di.vd, di.md)
    add("MAN -C", nneg, di.vc, di.mc)
    add("STALL -N", nneg, stall_v(nneg, ncl), di.md)
    add("STALL -1G", -1.0, stall_v(-1.0, ncl), di.md)
    add_gust("GUST +C", 1, di.vc, di.mc, "C")
    add_gust("GUST +D", 1, di.vd, di.md, "D")
    add_gust("GUST -D", -1, di.vd, di.md, "D")
    add_gust("GUST -C", -1, di.vc, di.mc, "C")
    add("BAL A", 1.0, di.va, di.mc)
    add("BAL C", 1.0, di.vc, di.mc)
    add("BAL D", 1.0, di.vd, di.md)
    add("ST ROL A", 2.0 * np_ / 3.0, di.va, di.mc)
    add("ST ROL C", 2.0 * np_ / 3.0, di.vc, di.mc)
    add("ST ROL D", 2.0 * np_ / 3.0, di.vd, di.md)
    acc_n = 0.85 * np_ if w <= 1000.0 else np_ * (1.7 + 0.05 * (w - 1000.0) / 11500.0) / 2.0
    add("AC ROLL", acc_n, state["v9"], di.mc)
    return pts, case


# --------------------------------------------------------------------------- #
# Envelope builder + Project entry point
# --------------------------------------------------------------------------- #
def build_envelope(project: Project) -> EnvelopeResult:
    """Compute the full balanced V-n matrix + balancing tail loads (the
    :class:`EnvelopeResult` payload for ``Project.envelope``)."""
    fl = project.flight_loads
    if fl is None:
        raise ValueError("Project has no 'flight_loads' inputs for the flight_envelope module")
    if project.speeds is None:
        raise ValueError("flight_envelope needs 'speeds' (STRSPEED) for the design speeds")
    if not fl.configurations:
        raise ValueError("flight_envelope needs at least one configuration")
    if not fl.cg_cases:
        raise ValueError("flight_envelope needs at least one CG case")

    di = _design_inputs(project)
    vn: List[VnPoint] = []
    tail: List[TailBalanceLoad] = []
    case = 0
    for alt in fl.altitudes_ft:
        for config in fl.configurations:
            # Flapped (landing/take-off) envelopes are investigated at sea level
            # only (FLTLOADS.BAS line 3000).
            if config.flaps_down and alt > 0:
                continue
            xt = fl.xtf if config.flaps_down else fl.xtc
            for cg in fl.cg_cases:
                pts, case = _config_points(config, cg, fl, alt, di, case)
                vn.extend(pts)
                for p in pts:
                    tail.append(TailBalanceLoad(
                        case=p.case, condition=p.condition, tail_load_lb=p.lt,
                        tail_cp_station=xt, flaps_down=config.flaps_down,
                    ))
    return EnvelopeResult(vn=vn, tail_balance=tail)


def _point_conditions(env: EnvelopeResult, concept: bool) -> List[ConditionResult]:
    """Render each V-n point as a reportable :class:`ConditionResult`."""
    note = ("Concept mode -- unverified extrapolation past the FAR23 band; the "
            "envelope uses the user load factors." if concept else "")
    out: List[ConditionResult] = []
    for p in env.vn:
        out.append(ConditionResult(
            title=f"{p.config} {p.cg} @ {p.altitude_ft:.0f} ft, case {p.case}: {p.condition}",
            far_reference=_FAR,
            values=[
                LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)"),
                LoadValue("Load factor NZ", p.nz),
                LoadValue("Angle of attack", p.alpha_deg, "deg"),
                LoadValue("Compressibility G", p.g_corr),
                LoadValue("Wing CL", p.cl),
                LoadValue("Pitching moment M(W+F)", p.m_wf, "lb-in"),
                LoadValue("Lift less tail LZW", p.lzw, "lb"),
                LoadValue("Balancing tail load LT", p.lt, "lb"),
                LoadValue("Drag DX", p.dx, "lb"),
            ],
            note=note,
        ))
    return out


MODULE_NAME = "flight_envelope"


def run(project: Project) -> ModuleResult:
    """Run FLTLOADS against a :class:`Project`'s flight-loads + speeds inputs."""
    env = build_envelope(project)
    return ModuleResult(module=MODULE_NAME,
                        conditions=_point_conditions(env, project.is_concept))


register(MODULE_NAME, run)
