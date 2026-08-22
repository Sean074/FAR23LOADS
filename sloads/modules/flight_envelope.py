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
from dataclasses import dataclass, replace
from typing import List, Optional

from ..aero_curves import clmax_curve as _clmax_curve
from ..aero_curves import drag_cd, lift_cl, moment_cm
from ..cg_cases import flight_cases
from ..constants import (
    DEG_PER_RAD,
    GUST_LOAD_FACTOR_DIVISOR,
    IN_PER_FT,
    RAD_PER_DEG,
    RHO_SL,
    G,
    dynamic_pressure_psf,
    eas_from_dynamic_pressure,
    gust_alleviation_factor,
    standard_atmosphere,
)
from ..convergence import SolveState, solver_failure
from ..derived_geometry import (
    WingReference,
    require_wing_reference,
    sync_geometry_derived,
)
from ..models import (
    AeroCoeffSet,
    CgCase,
    ConditionResult,
    EnvelopeResult,
    FlightLoadsInput,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    TailBalanceLoad,
    VnPoint,
)
from ..registry import register
from .structural_speeds import design_speeds, maneuver_load_factors

# 23.345 = high-lift devices (the flaps-down envelope, n<=2 at sea level).
_FAR = "23.333/23.337/23.341/23.345/23.421"

# Trip bounds on the balance's two iterations (FLTLOADS.BAS spun both without a
# bound). Named because the refusals quote them: exhausting either is a defect,
# not a tuning knob -- no shipped fixture takes more than 6 outer trips, and the
# only solve that ever reaches the bound is a clamped one, which now breaks out.
_OUTER_TRIPS = 200
_INNER_TRIPS = 400


# --------------------------------------------------------------------------- #
# Atmosphere & compressibility (FLTLOADS.BAS subroutine 3900)
# --------------------------------------------------------------------------- #
# Both the density ratio (M4-23) and the speed of sound are *read* from the one
# shared atmosphere in ``constants``. FLTLOADS.BAS carried its own speed-of-sound
# constants (518.688 deg R at sea level, 575 kt above the tropopause, vs the shared
# law's 518.4 / 574.94): +0.03 % in ``a``, measured 2026-08-17 to move no printed
# oracle (only the SELECT regression pins and the frozen digest), so per the
# exact-by-default policy the private atmosphere was retired (review C-7).
def density_ratio(alt_ft: float) -> float:
    return standard_atmosphere(alt_ft)[1]


def _speed_of_sound(alt_ft: float) -> float:
    return standard_atmosphere(alt_ft)[0]


# The coefficient polynomials and the CLmax-vs-Mach fit live in
# ``sloads.aero_curves`` (M4-5) so the Aerodynamic Data page's plotted curve and
# this balance evaluate one authority; the arithmetic is unchanged (bit-for-bit,
# Appendix A oracle-locked).


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
    #: How the dynamic-pressure iteration ended (:mod:`sloads.convergence`).
    #: Only ``CONVERGED`` or ``CLAMPED`` is ever returned -- ``FAILED`` is raised.
    state: SolveState = SolveState.CONVERGED


def _balance(n: float, v_init: float, mach_cap: float, config: AeroCoeffSet,
             cg: CgCase, fl: FlightLoadsInput, wr: WingReference,
             altitude_ft: float) -> _Balanced:
    """Balance one flight condition: solve AoA for load factor ``n`` (subr 3900).

    ``v_init`` is the equivalent airspeed (a guess for stall-line conditions,
    where the dynamic pressure is then iterated until CL hits the stall limit).

    Both loops report how they ended (#33, :mod:`sloads.convergence`). The
    angle-of-attack loop has one acceptable end -- the load factor inside its
    ±0.005 band -- and **raises** otherwise. The dynamic-pressure loop has two:
    CL on the (Mach-adjusted) stall line, or a **clamped** solve, where the Mach
    cap pins the true airspeed so ``q`` returns to the same value every trip and
    the iteration has no lever. Clamped is a real flight state, not a defect
    (decision **D-30**): the airplane is stall-limited at that altitude, which
    **23.333(b)** excludes from the manoeuvring envelope rather than owing. It is
    detected as an exact fixed point in ``q``, so breaking on it is arithmetically
    the same as spinning out the remaining trips -- every one of them recomputes
    the identical inner solve from the identical ``q``. Exhausting the trips with
    ``q`` still moving is neither, and raises.
    """
    xt = fl.xtf if config.flaps_down else fl.xtc
    s = wr.s_sqft
    mac = wr.mac
    gmn = 1.0 / math.sqrt(1.0 - fl.mn ** 2)
    kmn = _clmax_curve(fl.mn)
    sig = density_ratio(altitude_ft)
    a_sound = _speed_of_sound(altitude_ft)

    q = dynamic_pressure_psf(v_init)
    last: Optional[_Balanced] = None
    q_prev: Optional[float] = None
    for _ in range(_OUTER_TRIPS):  # outer: dynamic-pressure iteration (stall line)
        v = eas_from_dynamic_pressure(q)
        vt = v / math.sqrt(sig)
        mh = vt / a_sound
        if mh > mach_cap:
            mh = mach_cap
        vt = mh * a_sound
        v = vt * math.sqrt(sig)
        q = dynamic_pressure_psf(v)
        g = 1.0 / math.sqrt(1.0 - mh ** 2)
        stall_cl = config.stall_cl * _clmax_curve(mh) / kmn
        neg_stall_cl = config.neg_stall_cl * _clmax_curve(mh) / kmn
        # The Mach cap above pins ``v`` (and so ``q``) to one value; if this trip
        # asks the inner solve the same question as the last, no further trip can
        # answer it differently. That is the clamp, tested exactly.
        no_lever = q == q_prev
        q_prev = q

        al = -10.0 if n < 0 else 10.0
        da = 10.0
        cl = lz = dx = mm = 0.0
        for _ in range(_INNER_TRIPS):  # inner: angle-of-attack iteration
            cl = lift_cl(config, al, g, gmn)
            cd = drag_cd(config, cl)
            cm = moment_cm(config, al, g, gmn)
            ll = cl * q * s
            d = cd * q * s
            mm = cm * q * s * mac
            lz = ll * math.cos(al * RAD_PER_DEG) + d * math.sin(al * RAD_PER_DEG)
            dx = d * math.cos(al * RAD_PER_DEG) - ll * math.sin(al * RAD_PER_DEG)
            lt = (lz * (cg.xcg - wr.xw) - dx * (cg.zcg - wr.zw) + mm) / (xt - cg.xcg)
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
        else:  # trips exhausted with NZ outside its band -- no balance exists here
            raise solver_failure(
                "the flight-envelope angle-of-attack iteration",
                trips=_INNER_TRIPS,
                detail=(f"target n={n:.4g}, reached NZ={nz:.6g} at alpha={al:.6g} deg, "
                        f"V={v:.6g} kt(EAS), {altitude_ft:.0f} ft, CG '{cg.name}', "
                        f"config '{config.name}'"),
            )
        last = _Balanced(v_eas=v, nz=nz, alpha=al, g=g, cl=cl, mm=mm, lz=lz,
                         lt=(lz * (cg.xcg - wr.xw) - dx * (cg.zcg - wr.zw) + mm) / (xt - cg.xcg),
                         dx=dx)

        # Dynamic-pressure iteration to bring CL onto the (Mach-adjusted) stall line.
        if neg_stall_cl - 0.005 <= cl <= stall_cl + 0.005:
            break
        if no_lever:  # q is a fixed point off the stall line: stall-limited (D-30)
            last.state = SolveState.CLAMPED
            break
        nw = n * cg.weight_lb
        if cl > stall_cl + 0.005:
            q = q + 0.75 * (-q / ((cl - stall_cl) * s * q / nw - 1.0) - q)
        elif cl < neg_stall_cl - 0.005:
            q = q + 0.75 * (-q / ((cl - neg_stall_cl) * s * q / nw - 1.0) - q)
    else:  # trips exhausted with q still moving: neither on the stall line nor pinned
        raise solver_failure(
            "the flight-envelope dynamic-pressure iteration",
            trips=_OUTER_TRIPS,
            detail=(f"CL={cl:.6g} against a stall band [{neg_stall_cl:.6g}, "
                    f"{stall_cl:.6g}] at n={n:.4g}, V={v:.6g} kt(EAS), "
                    f"{altitude_ft:.0f} ft, CG '{cg.name}', config '{config.name}'"),
        )
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
                      cg: CgCase, fl: FlightLoadsInput, wr: WingReference,
                      altitude_ft: float) -> float:
    """Gust normal load factor (FAR 23.341, subroutine 4864).

    ``ref`` is the speed the gust is applied at ("C" = VC, "D" = VD, "F" = VF),
    selecting the derived gust velocity Ude.
    """
    h = altitude_ft
    sig = density_ratio(h)
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
    rho = RHO_SL * sig
    ws = cg.weight_lb / wr.s_sqft
    ug = 2.0 * ws / (rho * wr.mac / IN_PER_FT * c1 * DEG_PER_RAD * G)
    kg = gust_alleviation_factor(ug)
    return 1.0 + ng * kg * ude * v * c1 * DEG_PER_RAD / (GUST_LOAD_FACTOR_DIVISOR * ws)


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


def design_inputs(project: Project) -> _DesignInputs:
    """Pull VA/VC/VD/VF, MC/MD and the limit load factors from STRSPEED."""
    sp = project.speeds
    if sp is None:  # both callers have already refused; the same refusal for direct callers
        raise MissingInputError("flight_envelope needs 'speeds' (STRSPEED) for the design speeds")
    vals = {}
    for cond in design_speeds(project, sp):
        for lv in cond.values:
            vals[lv.key] = lv.value
    cat = sp.category.upper()
    n_pos, _, n_neg, _ = maneuver_load_factors(cat, sp.weight_lb, sp.chosen_n, sp.chosen_nneg)
    return _DesignInputs(
        va=vals["maneuver_speed_va"], vc=vals["cruise_speed_vc"],
        vd=vals["dive_speed_vd"], vf=vals["flap_speed_vf"],
        mc=vals["cruise_mach_mc"], md=vals["dive_mach_md"],
        n_pos=n_pos, n_neg=n_neg, category=cat,
    )


# --------------------------------------------------------------------------- #
# Cruise maneuver + gust corner set (FLTLOADS.BAS lines 1000-1594)
# --------------------------------------------------------------------------- #
def _config_points(config: AeroCoeffSet, cg: CgCase, fl: FlightLoadsInput,
                   wr: WingReference, alt: float, di: _DesignInputs,
                   case: int) -> "tuple[List[VnPoint], int, List[int]]":
    """The cruise maneuver+gust V-n corner points for one config / CG / altitude.

    Returns the points, the running case counter, and the case numbers whose
    balance came back **clamped** (#33) -- the stall-limited corners.
    """
    w = cg.weight_lb
    s = wr.s_sqft
    pts: List[VnPoint] = []
    clamped: List[int] = []
    state = {"v9": 0.0}

    def stall_v(n: float, clmax: float) -> float:
        # FLTLOADS.BAS: V = 0.9*sqrt(N*W*295/(CLmax*S)); N and CLmax share a sign.
        return 0.9 * eas_from_dynamic_pressure(n * w / (clmax * s))

    def add(cond: str, n: float, v: float, cap: float) -> _Balanced:
        nonlocal case
        b = _balance(n, v, cap, config, cg, fl, wr, alt)
        case += 1
        if b.state is SolveState.CLAMPED:
            clamped.append(case)
        pts.append(VnPoint(
            case=case, condition=cond, config=config.name, cg=cg.name, altitude_ft=alt,
            v_eas_kt=b.v_eas, nz=b.nz, alpha_deg=b.alpha, g_corr=b.g, cl=b.cl,
            m_wf=b.mm, lzw=b.lz, lt=b.lt, dx=b.dx,
        ))
        return b

    def add_gust(cond: str, ng: int, v: float, cap: float, ref: str) -> _Balanced:
        n = _gust_load_factor(ng, v, cap, ref, config, cg, fl, wr, alt)
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
    return pts, case, clamped


def _flap_config_points(config: AeroCoeffSet, cg: CgCase, fl: FlightLoadsInput,
                        wr: WingReference, alt: float, di: _DesignInputs,
                        case: int) -> "tuple[List[VnPoint], int, List[int]]":
    """The flaps-extended (LANDING) V-n corner set at the flap speed VF
    (FLTLOADS.BAS subroutine 3000): the flap envelope is limited to n=2 (FAR 23.345)
    and investigated at sea level only. Conditions: stall at 2/3 g / 1 g / 2 g, the
    n=2 and n=0 maneuver points at VF, the +/- gusts at VF (Ude 25 fps), and the VF /
    1.4 Vs balancing points.

    BAL 1.4VSF balances the airplane at 1.4x the **1-g flaps-down stall (STALL 1GL)**
    speed -- FLTLOADS.BAS (Code.pdf p300-302) saves the STALL 1GL speed for this
    condition, and Appendix A p178 case 9 prints V 83.6 kt / LT -430 lb (landing-config
    polynomials p176). (Earlier code balanced at 1.4x the STALL 2G speed, giving a
    balance speed ~1.4x too high and a tail load ~2.2x too large -- review finding T2.)"""
    w, s = cg.weight_lb, wr.s_sqft
    scl = config.stall_cl
    pts: List[VnPoint] = []
    clamped: List[int] = []

    def stall_v(n: float) -> float:
        return 0.9 * eas_from_dynamic_pressure(n * w / (scl * s))

    def add(cond: str, n: float, v: float, cap: float) -> _Balanced:
        nonlocal case
        b = _balance(n, v, cap, config, cg, fl, wr, alt)
        case += 1
        if b.state is SolveState.CLAMPED:
            clamped.append(case)
        pts.append(VnPoint(
            case=case, condition=cond, config=config.name, cg=cg.name, altitude_ft=alt,
            v_eas_kt=b.v_eas, nz=b.nz, alpha_deg=b.alpha, g_corr=b.g, cl=b.cl,
            m_wf=b.mm, lzw=b.lz, lt=b.lt, dx=b.dx,
        ))
        return b

    def add_gust(cond: str, ng: int, v: float, cap: float) -> _Balanced:
        n = _gust_load_factor(ng, v, cap, "F", config, cg, fl, wr, alt)
        return add(cond, n, v, cap)

    add("STAL 2/3G", 2.0 / 3.0, stall_v(2.0 / 3.0), di.mc)
    v_1gl = add("STALL 1GL", 1.0, stall_v(1.0), di.mc).v_eas
    add("STALL 2G", 2.0, stall_v(2.0), di.mc)
    add("MAN 2G VF", 2.0, di.vf, di.mc)
    add("MAN 0G VF", 0.0, di.vf, di.mc)
    add_gust("GUST VF", 1, di.vf, di.mc)
    add_gust("GUST -VF", -1, di.vf, di.mc)
    add("BAL VF", 1.0, di.vf, di.mc)
    add("BAL 1.4VSF", 1.0, 1.4 * v_1gl, di.mc)
    return pts, case, clamped


# --------------------------------------------------------------------------- #
# Envelope builder + Project entry point
# --------------------------------------------------------------------------- #
def balance_configs(aero) -> List[AeroCoeffSet]:
    """The airplane-less-tail coefficient sets the balance runs over.

    The cruise (flaps-up) set first, then the flaps-down set. Step G4 folds the
    off-by-default Munk fuselage ``dCm/dalpha`` increment into each config's M1 on a
    *local copy* -- the stored raw coefficients are left untouched, and a disabled
    (or zero) increment is a no-op so the Appendix A/B oracles stay bit-for-bit.
    Shared by :func:`build_envelope` and :func:`trim_sweep` so both see the same
    (fuselage-augmented) coefficients.
    """
    configs: List[AeroCoeffSet] = []
    if aero is not None:
        if aero.cruise is not None:
            configs.append(aero.cruise)
        if aero.flaps_down is not None:
            configs.append(aero.flaps_down)
        fm = aero.fuselage_moment
        if fm is not None and fm.enabled and fm.d_cm_dalpha:
            configs = [
                replace(c, moment=(c.moment[0], c.moment[1] + fm.d_cm_dalpha,
                                   c.moment[2], c.moment[3], c.moment[4]))
                for c in configs
            ]
    return configs


def build_envelope(project: Project) -> EnvelopeResult:
    """Compute the full balanced V-n matrix + balancing tail loads (the
    :class:`EnvelopeResult` payload for ``Project.envelope``)."""
    sync_geometry_derived(project)
    fl = project.flight_loads
    if fl is None:
        raise MissingInputError("Project has no 'flight_loads' inputs for the flight_envelope module")
    wr = require_wing_reference(project)
    if project.speeds is None:
        raise MissingInputError("flight_envelope needs 'speeds' (STRSPEED) for the design speeds")
    configs = balance_configs(project.aero_coeffs)
    if not configs:
        raise MissingInputError(
            "flight_envelope needs 'aero_coeffs' (cruise and/or flaps-down coefficient sets)"
        )
    cg_cases = flight_cases(project)
    if not cg_cases:
        raise MissingInputError("flight_envelope needs at least one CG case")

    di = design_inputs(project)
    vn: List[VnPoint] = []
    tail: List[TailBalanceLoad] = []
    clamped: List[int] = []
    case = 0
    for alt in fl.altitudes_ft:
        for config in configs:
            # Flapped (landing/take-off) envelopes are investigated at sea level
            # only (FLTLOADS.BAS line 3000).
            if config.flaps_down and alt > 0:
                continue
            xt = fl.xtf if config.flaps_down else fl.xtc
            corner = _flap_config_points if config.flaps_down else _config_points
            for cg in cg_cases:
                pts, case, cl_cases = corner(config, cg, fl, wr, alt, di, case)
                vn.extend(pts)
                clamped.extend(cl_cases)
                for p in pts:
                    tail.append(TailBalanceLoad(
                        case=p.case, condition=p.condition, tail_load_lb=p.lt,
                        tail_cp_station=xt, flaps_down=config.flaps_down,
                    ))
    return EnvelopeResult(vn=vn, tail_balance=tail, clamped_cases=sorted(clamped))


# --------------------------------------------------------------------------- #
# Trim sweep -- balancing tail load vs CG station (Step G5, GUI plot support)
# --------------------------------------------------------------------------- #
@dataclass
class TrimCurve:
    """Balancing tail load LT vs CG station for one BAL (1-g trim) condition.

    ``lt_lb`` is the **LIMIT** balancing tail load (the calc stays limit; the
    render/export boundary applies the ultimate factor). One entry per station in
    ``xcg_in``; ``nz``/``v_eas_kt`` are the converged load factor and EAS at each.
    """
    condition: str
    xcg_in: List[float]
    lt_lb: List[float]
    nz: List[float]
    v_eas_kt: List[float]


def trim_sweep(project: Project, *, weight_lb: float, zcg: float,
               xcg_stations: List[float], altitude_ft: float = 0.0) -> List[TrimCurve]:
    """Balancing tail load LT vs CG station for the BAL (1-g trim) conditions.

    Re-runs the FLTLOADS balance (:func:`_balance`, subroutine 3900) at each CG
    station in ``xcg_stations`` -- holding weight, waterline ``zcg`` and every other
    flight-loads / speeds input fixed -- for the three balanced trim conditions
    (BAL A at VA, BAL C at VC, BAL D at VD, all at ``n = 1``). Pure calc: it adds no
    load equations, only sweeps the existing balance across CG, so the returned
    ``lt_lb`` at a station that coincides with a project CG case reproduces that
    case's :func:`build_envelope` BAL load exactly (the Step G5 trim plot's
    traceability guarantee). Uses the cruise (flaps-up) coefficient set, including
    the Step G4 fuselage-moment increment when enabled. LIMIT output.
    """
    sync_geometry_derived(project)
    fl = project.flight_loads
    if fl is None:
        raise MissingInputError("trim_sweep needs 'flight_loads' inputs")
    wr = require_wing_reference(project)
    if project.speeds is None:
        raise MissingInputError("trim_sweep needs 'speeds' (STRSPEED) for the design speeds")
    cruise = next((c for c in balance_configs(project.aero_coeffs) if not c.flaps_down), None)
    if cruise is None:
        raise MissingInputError("trim_sweep needs a flaps-up (cruise) aero coefficient set")
    di = design_inputs(project)
    specs = (("BAL A", di.va, di.mc), ("BAL C", di.vc, di.mc), ("BAL D", di.vd, di.md))
    curves: List[TrimCurve] = []
    for cond, v, cap in specs:
        xs: List[float] = []
        lts: List[float] = []
        nzs: List[float] = []
        vs: List[float] = []
        for x in xcg_stations:
            cg = CgCase(name="sweep", weight_lb=weight_lb, xcg=x, zcg=zcg)
            b = _balance(1.0, v, cap, cruise, cg, fl, wr, altitude_ft)
            xs.append(x)
            lts.append(b.lt)
            nzs.append(b.nz)
            vs.append(b.v_eas)
        curves.append(TrimCurve(condition=cond, xcg_in=xs, lt_lb=lts, nz=nzs, v_eas_kt=vs))
    return curves


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
                LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)", key="v_eas"),
                LoadValue("Load factor NZ", p.nz, key="load_factor_nz"),
                LoadValue("Angle of attack", p.alpha_deg, "deg", key="angle_of_attack"),
                LoadValue("Compressibility G", p.g_corr, key="compressibility_g"),
                LoadValue("Wing CL", p.cl, key="wing_cl"),
                LoadValue("Pitching moment M(W+F)", p.m_wf, "lb-in", key="pitching_moment_m_w_f"),
                LoadValue("Lift less tail LZW", p.lzw, "lb", key="lift_less_tail_lzw"),
                LoadValue("Balancing tail load LT", p.lt, "lb", key="balancing_tail_load_lt"),
                LoadValue("Drag DX", p.dx, "lb", key="drag_dx"),
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

# --------------------------------------------------------------------------- #
# Public surface (M4-12b). Names not listed here are module-private: an
# underscore-free name outside this list is still not an import contract, and
# ``app/`` must import nothing underscored from ``sloads``.
# --------------------------------------------------------------------------- #
__all__ = [
    "MODULE_NAME",
    "TrimCurve",
    "build_envelope",
    "density_ratio",
    "design_inputs",
    "run",
    "trim_sweep",
]
