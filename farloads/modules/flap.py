"""Flap loads, from FLAPLOAD.BAS (Reference 1 Ch 17).

The flaps are sized for the critical flaps-extended condition of FAR 23.345 /
23.457(a). The flap section lift is the wing-angle-of-attack contribution plus the
deflection contribution, both from Abbott & von Doenhoff Fig 98::

    D1 = -2.6*E + 2.6        (dCLf/d(delta), per rad)      E = flap chord / wing chord
    D2 =  0.59*E + 0.08      (dCLf/dCLw)
    CLf = D1*delta_rad + D2*CLw,   CLw = n*W/(Q*SW),   Q = V^2/295

evaluated for four conditions and the largest taken:

    1G stall (V=VSF) | 2G stall (V=sqrt(2)*VSF) | 2G at VF | NG-gust at VF
    LF = CLf * Q * SF                                       23.345(a)

The chordwise distribution tapers from the leading edge to half that pressure at
the trailing edge, so ``LE psi = LF / 0.75 / SF / 144``.

Two amplifications are reported alongside the critical load:

* **Slipstream** (FAR 23.457(b)) -- a momentum-theory subroutine (FLAPLOAD.BAS
  sub 500) finds the fully-developed slipstream velocity ``U1`` that absorbs
  0.85*MAXHP, contracts the prop disk area to the flap and adds the nacelle/body
  frontal area to get the slipstream band (BL_eng +/- radius); the flap load in
  the slipstream is raised by ``(V_ss/VF)^2``.
* **Head-on 25 fps gust** (FAR 23.345(c)(1)) -- the load is raised by
  ``((VF_fps + 25)/VF_fps)^2``.

VS/VSF/VF and the design weight come from ``Project.speeds`` (STRSPEED); the wing
area from the ``Project.geometry`` wing surface; the propeller MAXHP/diameter from
``Project.engines[0]``. The flap geometry is ``Project.flap_loads``.

Reference: FLAPLOAD.BAS (Appendix C p452-454); Ref 1 Ch 17 p109-110; worked
example Appendix A "Critical Flap Loads" p201 (CLf 1.7046/1.7046/1.5593/1.5476;
LF 212/424/629/624; critical 629 lb, LE 0.545 psi; slipstream x1.407; gust
x1.301; combined 819 lb).
"""

from __future__ import annotations

import math
from typing import List, NamedTuple

from ..constants import KT_TO_FPS_SUITE
from ..models import (
    ConditionResult,
    ControlSurfaceLoadResult,
    ControlSurfaceStation,
    LoadValue,
    ModuleResult,
    Project,
)
from ..registry import register
from .structural_speeds import _wing_area_sqft, design_speed_values

MODULE_NAME = "flap"

_SQIN_PER_SQFT = 144.0
_RHO = 0.002378  # slug/ft^3, sea-level density (FLAPLOAD.BAS sub 500)


class FlapResult(NamedTuple):
    """Critical flap load (+ amplifications) from FLAPLOAD.BAS."""
    clf: List[float]            # the four condition flap CLs
    clw: List[float]            # the four condition wing CLs
    lf: List[float]             # the four condition flap loads (lb)
    critical_lf_lb: float       # FAR 23.345(a) critical
    le_pressure_psi: float      # leading-edge pressure (TE = half)
    # Slipstream (FAR 23.457(b)); 0 when no engine power is supplied.
    slipstream_factor: float
    slipstream_velocity_kt: float
    slipstream_bl_inboard: float
    slipstream_bl_outboard: float
    # Head-on gust (FAR 23.345(c)(1)).
    gust_factor: float
    combined_gust_lb: float


def _slipstream_velocity(vf_kt: float, maxhp: float, pdia_in: float):
    """Fully-developed slipstream velocity ``U1`` (ft/s) absorbing 0.85*MAXHP, and
    the disk velocity ``U`` (FLAPLOAD.BAS sub 500, momentum theory)."""
    pdia_ft = pdia_in / 12.0
    area = math.pi * pdia_ft ** 2 / 4.0
    vf_fps = vf_kt * KT_TO_FPS_SUITE
    u1 = 0.0
    # Iterate U1 upward (the BASIC steps by 0.5) until the absorbed power reaches
    # 0.85*MAXHP: HP = area*rho*(U1-Vf)*(U1+Vf)^2 / (4*550).
    while True:
        hp_try = area * _RHO * (u1 - vf_fps) * (u1 + vf_fps) ** 2 / (4.0 * 550.0)
        if hp_try >= 0.85 * maxhp:
            break
        u1 += 0.5
        if u1 > 1.0e5:  # guard (never reached for realistic inputs)
            break
    u = (vf_fps + u1) / 2.0
    return u1, u, area


def flap_loads(vs: float, vsf: float, vf: float, weight: float, ng: float,
               sf: float, sw: float, delta_deg: float, e: float,
               maxhp: float = 0.0, pdia_in: float = 0.0, blprop: float = 0.0,
               af_sqft: float = 0.0) -> FlapResult:
    """Critical flap load + slipstream/gust amplifications (FLAPLOAD.BAS).

    ``vs``/``vsf`` clean/flapped stall (kt), ``vf`` flap design speed, ``weight``
    MTOW, ``ng`` flaps-extended gust factor, ``sf`` flap area one side (sq ft),
    ``sw`` wing area (sq ft), ``delta_deg`` flap deflection, ``e`` flap/wing chord
    ratio. Slipstream is computed only when ``maxhp > 0``."""
    if sf <= 0 or sw <= 0:
        raise ValueError("flap and wing areas must be positive")
    d1 = -2.6 * e + 2.6
    d2 = 0.59 * e + 0.08
    delta_rad = math.radians(delta_deg)

    # Dynamic pressures and wing CLs for the four flaps-extended conditions.
    q1 = vsf ** 2 / 295.0                       # 1G stall
    q2 = (math.sqrt(2.0) * vsf) ** 2 / 295.0    # 2G stall
    qvf = vf ** 2 / 295.0                        # at VF
    clw = [
        1.0 * weight / (q1 * sw),
        2.0 * weight / (q2 * sw),
        2.0 * weight / (qvf * sw),
        ng * weight / (qvf * sw),
    ]
    qs = [q1, q2, qvf, qvf]
    clf = [d1 * delta_rad + d2 * c for c in clw]
    lf = [cl * q * sf for cl, q in zip(clf, qs)]
    critical = max(lf)
    le_psi = critical / 0.75 / sf / _SQIN_PER_SQFT

    # Slipstream (FAR 23.457(b)).
    slip_factor = slip_v_kt = bl_in = bl_out = 0.0
    if maxhp > 0 and pdia_in > 0:
        u1, u, aprop = _slipstream_velocity(vf, maxhp, pdia_in)
        a1 = aprop * u / u1 if u1 > 0 else 0.0   # contracted slipstream area at flap
        atot = a1 + af_sqft
        rtot_in = ((4.0 * atot / math.pi) ** 0.5 / 2.0) * 12.0
        bl_in = blprop - rtot_in
        bl_out = blprop + rtot_in
        slip_v_kt = u1 / KT_TO_FPS_SUITE
        slip_factor = slip_v_kt ** 2 / vf ** 2

    # Head-on 25 fps gust (FAR 23.345(c)(1)).
    vf_fps = vf * KT_TO_FPS_SUITE
    gust_factor = ((vf_fps + 25.0) / vf_fps) ** 2
    combined = gust_factor * critical

    return FlapResult(
        clf=clf, clw=clw, lf=lf, critical_lf_lb=critical, le_pressure_psi=le_psi,
        slipstream_factor=slip_factor, slipstream_velocity_kt=slip_v_kt,
        slipstream_bl_inboard=bl_in, slipstream_bl_outboard=bl_out,
        gust_factor=gust_factor, combined_gust_lb=combined,
    )


def _engine_power(project: Project):
    """``(MAXHP, prop diameter in)`` from the first engine, or ``(0, 0)``."""
    eng = project.engine
    if eng is None:
        return 0.0, 0.0
    hp = eng.max_cont_hp or eng.takeoff_hp or 0.0
    return hp or 0.0, eng.prop_diameter_in or 0.0


def _compute(project: Project) -> FlapResult:
    if project.flap_loads is None:
        raise ValueError("flap needs the 'flap_loads' input slice")
    if project.speeds is None:
        raise ValueError("flap needs 'speeds' (STRSPEED VS/VSF/VF)")
    inp = project.flap_loads
    sp = project.speeds
    sv = design_speed_values(project, sp)
    sw = _wing_area_sqft(project, sp)
    maxhp, pdia = _engine_power(project)
    return flap_loads(
        vs=sp.stall_clean_kt, vsf=sp.stall_flap_kt, vf=sv.vf, weight=sp.weight_lb,
        ng=inp.gust_load_factor, sf=inp.flap_area_one_side_sqft, sw=sw,
        delta_deg=inp.flap_deflection_deg, e=inp.flap_chord_ratio,
        maxhp=maxhp, pdia_in=pdia, blprop=inp.engine_butt_line_in,
        af_sqft=inp.nacelle_frontal_area_sqft,
    )


def build_flap(project: Project) -> List[ControlSurfaceLoadResult]:
    """The governing flap load (gust-combined envelope) as a result record."""
    r = _compute(project)
    surface = project.flap_loads.surface
    sv = design_speed_values(project, project.speeds)
    load = max(r.critical_lf_lb, r.combined_gust_lb)
    case = "flap gust-combined" if r.combined_gust_lb >= r.critical_lf_lb else "flap 23.345(a)"
    le = load / 0.75 / project.flap_loads.flap_area_one_side_sqft / _SQIN_PER_SQFT
    stations = [
        ControlSurfaceStation(x=0.0, psi=le),
        ControlSurfaceStation(x=1.0, psi=le / 2.0),
    ]
    return [ControlSurfaceLoadResult(
        surface=surface, case=case, load_lb=load, v_kt=sv.vf, stations=stations)]


def run(project: Project) -> ModuleResult:
    """Run FLAPLOAD: the critical flaps-extended flap load (FAR 23.345 / 23.457)."""
    if project.flap_loads is None:
        raise ValueError("Project has no 'flap_loads' inputs for the flap module")
    r = _compute(project)
    values = [
        LoadValue("Critical flap load (23.345(a))", r.critical_lf_lb, "lb"),
        LoadValue("LE pressure (TE = half)", r.le_pressure_psi, "lb/in^2"),
        LoadValue("Flap CL 1G stall", r.clf[0]),
        LoadValue("Flap CL 2G stall", r.clf[1]),
        LoadValue("Flap CL 2G at VF", r.clf[2]),
        LoadValue("Flap CL gust at VF", r.clf[3]),
        LoadValue("Flap load 1G stall", r.lf[0], "lb"),
        LoadValue("Flap load 2G stall", r.lf[1], "lb"),
        LoadValue("Flap load 2G at VF", r.lf[2], "lb"),
        LoadValue("Flap load gust at VF", r.lf[3], "lb"),
        LoadValue("Head-on gust factor", r.gust_factor),
        LoadValue("Flap load combined w/ gust", r.combined_gust_lb, "lb"),
    ]
    if r.slipstream_factor > 0:
        values.extend([
            LoadValue("Slipstream factor", r.slipstream_factor),
            LoadValue("Slipstream velocity at flap", r.slipstream_velocity_kt, "kt(EAS)"),
            LoadValue("Slipstream inboard BL", r.slipstream_bl_inboard, "in"),
            LoadValue("Slipstream outboard BL", r.slipstream_bl_outboard, "in"),
        ])
    note = ("Critical flaps-extended load (Abbott & von Doenhoff Fig 98); chordwise "
            "taper LE -> half at TE. Slipstream FAR 23.457(b), gust FAR 23.345(c)(1).")
    if project.is_concept:
        note += " Concept mode -- unverified extrapolation past the FAR23 band."
    return ModuleResult(module=MODULE_NAME, conditions=[ConditionResult(
        title="Critical flap loads", far_reference="23.345", values=values, note=note)])


register(MODULE_NAME, run)
