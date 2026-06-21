"""One-engine-out vertical-tail loads (ONENGOUT.BAS, Reference 1 Ch 11).

FAR 23.367 (unsymmetrical loads due to engine failure). When the critical engine
fails on a multi-engine airplane, the residual thrust/windmill-drag asymmetry yaws
the airplane about its vertical axis; the pilot -- assumed to act at the peak yaw
rate but not earlier than 2 s after the failure (23.367(b)) -- applies full rudder
over a finite travel time and recovers. ONENGOUT integrates that yaw transient and
reports the **maximum vertical-tail load**.

This is a time-marching simulation (Euler, ``time_step_s`` step), not a static
condition like SELECT's v-tail loads -- but it shares SELECT's v-tail aero terms
(``vtail_lift_slope`` AVT, ``rudder_effectiveness`` EFFECTV, ``large_deflection_factor``
EF; see :mod:`farloads.modules._vtail`). Per ONENGOUT.BAS, with ``Q = V^2/295``:

    SLOPELT25 = AVT/57.3                                 # per deg
    VTFPS     = (V/sqrt(sigma)) * 1.15 * 88/60           # true airspeed, ft/s
    THRUST    = MAXHP*550*.85 / VTFPS                    # engine thrust, lb
    DRAG      = .85*.232*(.002378*sigma)*VTFPS^2*DIA^2   # windmill drag, lb (Glauert)
    LT25 = (THETA + damp)*SLOPELT25*Q*SVT/144            # angle-of-attack load (25% MAC)
    LT50 = EF*EFFECTV*SLOPELT25*RUD*Q*SVT/144            # camber/rudder load (50% MAC)
    MOM  = thrust/windmill schedule - LT25*(XT25-XCG) - LT50*(XT50-XCG)
    THETA2DOT = MOM/12/IZZ*57.3 ; integrate THETADOT, THETA until recovery (THETA<0).

Units mirror the BASIC: vertical-tail/rudder areas in **square inches**, stations and
butt line in **inches**, ``IZZ`` in **slug-ft^2**, angles in **degrees**.

Validation note: Appendix B (the 10-place twin turboprop) -- the printed one-engine-out
oracle -- is **absent** from the bundled reference PDFs (Reference 1 carries only the
Appendix A GA single; the FAA User's Guide Ch 22 gives partial inputs and no output
numbers). C9 is therefore locked at the sub-formula level (each step exact to
ONENGOUT.BAS) plus integration/physics closure; the printed twin oracle and an
``examples/twin_turboprop.project.json`` fixture are recorded as deferred items.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..constants import KT_TO_FPS_SUITE, LBIN2_PER_SLUGFT2, standard_atmosphere
from ..models import (
    ConditionResult,
    EngineInput,
    LoadValue,
    MassCase,
    ModuleResult,
    OneEngineOutInput,
    Project,
    VTailLoadsInput,
)
from ..registry import register
from ._vtail import large_deflection_factor, rudder_effectiveness, vtail_lift_slope

MODULE_NAME = "one_engine_out"

_DEG = 57.3              # ONENGOUT.BAS deg/rad
_RHO0 = 0.002378         # sea-level density, slug/ft^3
_Q_DIVISOR = 295.0       # Q = V^2/295
_IN2_PER_FT2 = 144.0
_MAX_SIM_TIME_S = 60.0   # bound the march; no recovery by here => uncontrollable (flag it)
_CORRECTIVE_DELAY_S = 2.0  # FAR 23.367(b): not earlier than 2 s after failure


@dataclass
class HistoryRow:
    """One Euler step of the yaw transient (ONENGOUT.BAS history line)."""
    time: float
    theta: float          # yaw angle, deg
    theta_dot: float      # yaw rate, deg/s
    theta_2dot: float     # yaw accel, deg/s^2
    lt25: float           # angle-of-attack load (25% MAC), lb
    lt50: float           # camber/rudder load (50% MAC), lb
    lt: float             # total tail load, lb
    rudder_deg: float     # rudder deflection, deg
    moment: float         # net yaw moment, in-lb


@dataclass
class CaseInputs:
    """The resolved scalar inputs for one speed case (BASIC variable names)."""
    arvt: float
    svt_in2: float
    sr_in2: float
    defl_rud_max: float
    xcg: float
    xt25: float
    xt50: float
    v_kt: float
    alt_ft: float
    izz: float
    bleng: float
    maxhp: float
    dia_ft: float
    time2decay: float
    time2drag: float
    inctimerud: float
    dt: float


@dataclass
class CaseSummary:
    """The headline outputs of one one-engine-out speed case."""
    thrust_lb: float
    windmill_drag_lb: float
    max_yaw_rate_deg_s: float
    max_tail_load_lb: float
    lt25_at_peak_lb: float
    lt50_at_peak_lb: float
    time_to_recovery_s: float
    recovered: bool


def engine_thrust_and_drag(c: CaseInputs) -> Tuple[float, float, float]:
    """Engine thrust, windmill drag (lb) and true airspeed (ft/s) at the case speed.

    ONENGOUT.BAS lines 203-211: sea-level-equivalent ``V`` is converted to true
    airspeed via the density ratio, then thrust ``MAXHP*550*.85/VTFPS`` and the
    windmilling-propeller drag ``.85*.232*rho*VTFPS^2*DIA^2`` (Glauert)."""
    sigma = standard_atmosphere(c.alt_ft)[1]
    vtfps = (c.v_kt / sigma ** 0.5) * KT_TO_FPS_SUITE
    thrust = c.maxhp * 550.0 * 0.85 / vtfps
    rho = _RHO0 * sigma
    drag = 0.85 * 0.232 * rho * vtfps ** 2 * c.dia_ft ** 2
    return thrust, drag, vtfps


def simulate(c: CaseInputs) -> Tuple[List[HistoryRow], CaseSummary]:
    """Integrate the yaw transient for one speed case (ONENGOUT.BAS 203-410).

    Returns the full time history and the case summary (max tail load, max yaw rate,
    time to recovery). Mirrors the BASIC statement order exactly."""
    thrust, drag, _ = engine_thrust_and_drag(c)
    mom_eng = thrust * c.bleng
    mom_windmill = drag * c.bleng
    slope_lt25 = vtail_lift_slope(c.arvt) / _DEG          # per deg
    sr_over_sv = c.sr_in2 / c.svt_in2
    effectv = rudder_effectiveness(sr_over_sv)
    q = c.v_kt ** 2 / _Q_DIVISOR

    theta = theta_dot = theta_2dot = 0.0
    theta_dot_max = lt_max = 0.0
    lt25 = lt50 = 0.0
    defl_rud = 0.0
    time = 0.0
    time_init_rud = time_rud_max = 1.0e9
    mark = False
    lt25_at_peak = lt50_at_peak = 0.0
    rows: List[HistoryRow] = []
    recovered = False
    max_steps = int(_MAX_SIM_TIME_S / c.dt) + 1

    for _ in range(max_steps):
        # Rudder ramp once corrective action has been initiated (line ~205).
        if (time >= _CORRECTIVE_DELAY_S and theta_dot < theta_dot_max
                and time < time_rud_max and time >= time_init_rud):
            defl_rud = c.defl_rud_max * (time - time_init_rud) / c.inctimerud
        ef = large_deflection_factor(defl_rud, sr_over_sv)
        vdamp_fps = theta_dot / _DEG * (c.xt25 - c.xcg) / 12.0
        vdamp_kt = vdamp_fps / KT_TO_FPS_SUITE
        damp_angle = _DEG * math.atan(vdamp_kt / c.v_kt)
        slope_lt50 = ef * effectv * slope_lt25
        lt25 = (theta + damp_angle) * slope_lt25 * q * c.svt_in2 / _IN2_PER_FT2
        lt50 = (slope_lt50 * defl_rud) * q * c.svt_in2 / _IN2_PER_FT2
        lt = lt25 + lt50

        # Net yaw moment: thrust decay then windmill-drag buildup, less the tail loads.
        moment = _moment(time, c, mom_eng, mom_windmill, lt25, lt50)
        theta_2dot = moment / 12.0 / c.izz * _DEG
        theta_dot = theta_dot + theta_2dot * c.dt
        theta = theta + theta_dot * c.dt + 0.5 * theta_2dot * c.dt ** 2

        if theta_dot > theta_dot_max:
            theta_dot_max = theta_dot
        if lt > lt_max:
            lt_max = lt
            lt25_at_peak, lt50_at_peak = lt25, lt50
        if time < _CORRECTIVE_DELAY_S:
            defl_rud = 0.0
        # Initiate corrective action at the first t>=2 s where the yaw rate stops rising.
        if time >= _CORRECTIVE_DELAY_S and theta_dot < theta_dot_max and not mark:
            time_init_rud = time
            time_rud_max = time_init_rud + c.inctimerud
            mark = True
        if time > time_rud_max:
            defl_rud = c.defl_rud_max

        rows.append(HistoryRow(time, theta, theta_dot, theta_2dot, lt25, lt50, lt,
                               defl_rud, moment))
        time = time + c.dt
        if theta < 0.0:           # recovery complete (yaw swings back through zero)
            recovered = True
            break

    summary = CaseSummary(
        thrust_lb=thrust, windmill_drag_lb=drag,
        max_yaw_rate_deg_s=theta_dot_max, max_tail_load_lb=lt_max,
        lt25_at_peak_lb=lt25_at_peak, lt50_at_peak_lb=lt50_at_peak,
        time_to_recovery_s=rows[-1].time if rows else 0.0,
        recovered=recovered,
    )
    return rows, summary


def _moment(time: float, c: CaseInputs, mom_eng: float, mom_windmill: float,
            lt25: float, lt50: float) -> float:
    """Net yaw moment about the CG at ``time`` (ONENGOUT.BAS 282-286, in-lb).

    Thrust ramps from its full value down to zero over ``time2decay``; windmill drag
    then ramps up over ``[time2decay, time2drag]`` and holds. The vertical-tail loads
    (resolved at their fuselage stations) oppose the moment throughout."""
    tail = lt25 * (c.xt25 - c.xcg) + lt50 * (c.xt50 - c.xcg)
    if time <= 0.0:
        return 0.0
    if time < c.time2decay:
        return mom_eng - mom_eng * (c.time2decay - time) / c.time2decay - tail
    if time == c.time2decay:
        return mom_eng - tail
    if time < c.time2drag:
        return (mom_eng + mom_windmill * (time - c.time2decay) / (c.time2drag - c.time2decay)
                - tail)
    return mom_eng + mom_windmill - tail


# --------------------------------------------------------------------------- #
# Project plumbing
# --------------------------------------------------------------------------- #
def _heaviest_case(project: Project) -> MassCase:
    if project.mass is None or not project.mass.cases:
        raise ValueError("one_engine_out needs Project.mass (run WTONECG first)")
    return max(project.mass.cases, key=lambda m: m.weight_lb)


def _engine_power(eng: EngineInput, use_takeoff: bool) -> float:
    """Max horsepower of one engine (MAXHP). Prefers take-off or max-continuous per
    ``use_takeoff``, falling back to the other when one is unset."""
    primary = eng.takeoff_hp if use_takeoff else eng.max_cont_hp
    other = eng.max_cont_hp if use_takeoff else eng.takeoff_hp
    hp = primary if primary else other
    if not hp:
        raise ValueError(
            "one_engine_out needs the failed engine's horsepower "
            "(EngineInput.max_cont_hp or takeoff_hp)")
    return float(hp)


def _speed_cases(project: Project, oeo: OneEngineOutInput) -> List[Tuple[str, str, float]]:
    """The (label, FAR reference, speed) cases to evaluate.

    Default: VC (ultimate, 23.367(a)(2)), VD (limit, 23.367(a)(1)) and VS, taken from
    ``Project.speeds``. ``oeo.speeds_kt`` overrides with an explicit speed list."""
    sp = project.speeds
    if oeo.speeds_kt:
        return [(f"V={v:g} kt", "23.367", float(v)) for v in oeo.speeds_kt]
    if sp is None:
        raise ValueError("one_engine_out needs Project.speeds (or OneEngineOutInput.speeds_kt)")
    cases: List[Tuple[str, str, float]] = []
    if sp.chosen_vc:
        cases.append(("VC (ultimate)", "23.367(a)(2)", float(sp.chosen_vc)))
    if sp.chosen_vd:
        cases.append(("VD (limit)", "23.367(a)(1)", float(sp.chosen_vd)))
    if sp.stall_clean_kt:
        cases.append(("VS", "23.367", float(sp.stall_clean_kt)))
    if not cases:
        raise ValueError("one_engine_out found no speeds; set chosen_vc/chosen_vd on Project.speeds")
    return cases


def _case_inputs(project: Project, v_kt: float) -> CaseInputs:
    """Assemble the scalar simulation inputs for one speed from the project slices."""
    oeo = project.one_engine_out
    vt: Optional[VTailLoadsInput] = project.vtail_loads
    if oeo is None:
        raise ValueError("one_engine_out needs the 'one_engine_out' input slice")
    if vt is None:
        raise ValueError("one_engine_out needs Project.vtail_loads (vertical-tail geometry)")
    if not project.engines:
        raise ValueError("one_engine_out needs Project.engines (the failed engine)")
    if not (0 <= oeo.failed_engine_index < len(project.engines)):
        raise ValueError(f"failed_engine_index {oeo.failed_engine_index} out of range")
    eng = project.engines[oeo.failed_engine_index]

    case = _heaviest_case(project)
    izz = oeo.izz_slugft2 or (case.izz / LBIN2_PER_SLUGFT2)
    xcg = oeo.xcg_in or case.cg_x
    alt = oeo.altitude_ft if oeo.altitude_ft is not None else (
        project.speeds.shoulder_altitude_ft if project.speeds else 0.0)
    if izz <= 0:
        raise ValueError("one_engine_out needs a non-zero IZZ (Project.mass or izz_slugft2)")

    return CaseInputs(
        arvt=vt.aspect_ratio_vtail,
        svt_in2=vt.vtail_area_sqft * _IN2_PER_FT2,
        sr_in2=vt.rudder_area_sqft * _IN2_PER_FT2,
        defl_rud_max=vt.rudder_deflection_deg,
        xcg=xcg,
        xt25=vt.xv25,
        xt50=vt.xv50,
        v_kt=v_kt,
        alt_ft=alt,
        izz=izz,
        bleng=abs(eng.engine_cg[1]),
        maxhp=_engine_power(eng, oeo.use_takeoff_power),
        dia_ft=eng.prop_diameter_in / 12.0,
        time2decay=oeo.thrust_decay_time_s,
        time2drag=oeo.windmill_drag_time_s,
        inctimerud=oeo.rudder_travel_time_s,
        dt=oeo.time_step_s,
    )


def time_history(project: Project, speed_label: str) -> List[HistoryRow]:
    """The full Euler time history for one named speed case (for the UI re-run).

    ``speed_label`` matches a :class:`ConditionResult` title produced by :func:`run`
    (e.g. ``"VC (ultimate)"``)."""
    for label, _ref, v_kt in _speed_cases(project, project.one_engine_out):
        if label == speed_label:
            rows, _ = simulate(_case_inputs(project, v_kt))
            return rows
    raise ValueError(f"unknown one-engine-out speed case {speed_label!r}")


def run(project: Project) -> ModuleResult:
    """Run ONENGOUT: the one-engine-out maximum vertical-tail load at each speed.

    One :class:`ConditionResult` per speed (VC ultimate / VD limit / VS): engine
    thrust, windmill drag, maximum yawing velocity, **maximum tail load**, the 25%/50%
    MAC loads at the peak, and the time to recovery (FAR 23.367)."""
    oeo = project.one_engine_out
    if oeo is None:
        raise ValueError("one_engine_out needs the 'one_engine_out' input slice")
    if oeo.thrust_decay_time_s <= 0 or oeo.windmill_drag_time_s <= 0 or oeo.rudder_travel_time_s <= 0:
        raise ValueError(
            "one_engine_out needs positive thrust_decay_time_s, windmill_drag_time_s "
            "and rudder_travel_time_s")

    conditions: List[ConditionResult] = []
    for label, far_ref, v_kt in _speed_cases(project, oeo):
        c = _case_inputs(project, v_kt)
        _rows, s = simulate(c)
        conditions.append(ConditionResult(
            title=f"One engine out — {label}",
            far_reference=far_ref,
            values=[
                LoadValue("V (EAS)", c.v_kt, "kt(EAS)"),
                LoadValue("Engine thrust", s.thrust_lb, "lb"),
                LoadValue("Windmill drag", s.windmill_drag_lb, "lb"),
                LoadValue("Max yawing velocity", s.max_yaw_rate_deg_s, "deg/s"),
                LoadValue("Max tail load", s.max_tail_load_lb, "lb"),
                LoadValue("Load at 25% MAC (at peak)", s.lt25_at_peak_lb, "lb"),
                LoadValue("Load at 50% MAC (at peak)", s.lt50_at_peak_lb, "lb"),
                LoadValue("Time to recovery", s.time_to_recovery_s, "s"),
            ],
            note=(f"Failed engine #{oeo.failed_engine_index} at butt line {c.bleng:g} in; "
                  f"IZZ {c.izz:g} slug-ft^2."
                  + ("" if s.recovered else
                     f" NOT recovered within {_MAX_SIM_TIME_S:g} s — the airplane is "
                     "uncontrollable at this speed (likely below VMC); the tail load and "
                     "yaw rate are the values at the simulation limit.")),
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
