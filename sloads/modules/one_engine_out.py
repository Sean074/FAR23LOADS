"""One-engine-out vertical-tail loads (ONENGOUT.BAS, Reference 1 Ch 11).

FAR 23.367 (unsymmetrical loads due to engine failure). When the critical engine
fails on a multi-engine airplane, the residual thrust/windmill-drag asymmetry yaws
the airplane about its vertical axis; the pilot -- assumed to act at the peak yaw
rate but not earlier than 2 s after the failure (23.367(b)) -- applies full rudder
over a finite travel time and recovers. ONENGOUT integrates that yaw transient and
reports the **maximum vertical-tail load**.

This is a time-marching simulation (Euler, ``time_step_s`` step), not a static
condition like SELECT's v-tail loads -- but it shares SELECT's v-tail aero terms
(``lift_curve_slope`` AVT, ``rudder_effectiveness`` EFFECTV, ``large_deflection_factor``
EF; see :mod:`sloads.modules._vtail`). Per ONENGOUT.BAS, with ``Q = V^2/295``:

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
ONENGOUT.BAS) plus integration/physics closure; the printed twin oracle stays a
deferred item. The two shipped twin-turboprop fixtures (``atr42_100``,
``dhc8_dash8``) execute this module end to end -- they carry take-off and
max-continuous shaft power from EASA TCDS IM.E.041 -- and
``tests/test_one_engine_out.py`` gates that they keep doing so.

**Coverage limitation:** :data:`PROPELLER_ONLY_NOTE` -- the model is propeller-only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, NamedTuple, Optional, Tuple

from ..applicability import engine_failure_not_applicable
from ..case_ids import VTAIL_BAND_ONENGOUT, CaseIdAllocator
from ..constants import (
    DEG_PER_RAD,
    FT_LB_S_PER_HP,
    IN2_PER_FT2,
    IN_PER_FT,
    KT_TO_FPS,
    LBIN2_PER_SLUGFT2,
    RHO_SL,
    ULTIMATE_FACTOR,
    dynamic_pressure_psf,
    standard_atmosphere,
)
from ..models import (
    CaseRef,
    ConditionResult,
    EngineInput,
    LoadValue,
    MassCase,
    MissingInputError,
    ModuleResult,
    OneEngineOutInput,
    Project,
    VTailLoadsInput,
)
from ..picks import extreme
from ..registry import register
from ._vtail import large_deflection_factor, lift_curve_slope, rudder_effectiveness

MODULE_NAME = "one_engine_out"

#: The 23.367 asymmetry model is **propeller-only**, and this is the single owner
#: of that statement (report stamp, spec and UI quote it rather than paraphrase).
#: Both terms of the yawing moment are propeller relations taken straight from
#: ONENGOUT.BAS: the live engine's thrust is ``HP*550*0.85/V`` (shaft power over
#: true airspeed) and the failed engine's drag is Glauert windmilling on the disc,
#: ``~DIA^2``. Neither has a turbofan/turbojet form here -- run against a fan
#: installation the thrust term is a shaft-power surrogate and the windmill term
#: collapses to zero with the propeller diameter, which understates the asymmetry
#: and mis-times it. FAR 23.367(a) is itself turbopropeller-specific (Ref 1 Ch 11
#: p87), so this is a gap in coverage rather than in accuracy. The statement is
#: **enforced** (M4-3(b), 2026-08-16): :func:`_case_inputs` refuses to simulate
#: when the failed engine carries no propeller disc (``prop_diameter_in <= 0``),
#: which is the one signal the model itself depends on -- ``EngineType`` has no
#: turbofan member (a fan installation is entered as ``T`` with a 0-in disc), so
#: engine type cannot be the gate. Reciprocating twins remain runnable: they are
#: propeller installations, and the regulatory turboprop scope of 23.367(a) is
#: carried by the coverage table (``report/coverage.py``), not by this module.
PROPELLER_ONLY_NOTE = (
    "the one-engine-out yaw transient (23.367) is modelled for PROPELLER "
    "installations only -- thrust is shaft power over true airspeed and the "
    "failed-engine drag is Glauert windmilling on the propeller disc, so a "
    "turbofan or turbojet installation is NOT covered and its asymmetry would be "
    "understated; the module refuses to run when the failed engine has no "
    "propeller diameter"
)

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
    vtfps = (c.v_kt / sigma ** 0.5) * KT_TO_FPS
    thrust = c.maxhp * FT_LB_S_PER_HP * 0.85 / vtfps
    rho = RHO_SL * sigma
    drag = 0.85 * 0.232 * rho * vtfps ** 2 * c.dia_ft ** 2
    return thrust, drag, vtfps


def simulate(c: CaseInputs) -> Tuple[List[HistoryRow], CaseSummary]:
    """Integrate the yaw transient for one speed case (ONENGOUT.BAS 203-410).

    Returns the full time history and the case summary (max tail load, max yaw rate,
    time to recovery). Mirrors the BASIC statement order exactly."""
    thrust, drag, _ = engine_thrust_and_drag(c)
    mom_eng = thrust * c.bleng
    mom_windmill = drag * c.bleng
    slope_lt25 = lift_curve_slope(c.arvt) / DEG_PER_RAD          # per deg
    sr_over_sv = c.sr_in2 / c.svt_in2
    effectv = rudder_effectiveness(sr_over_sv)
    q = dynamic_pressure_psf(c.v_kt)

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
        vdamp_fps = theta_dot / DEG_PER_RAD * (c.xt25 - c.xcg) / IN_PER_FT
        vdamp_kt = vdamp_fps / KT_TO_FPS
        damp_angle = DEG_PER_RAD * math.atan(vdamp_kt / c.v_kt)
        slope_lt50 = ef * effectv * slope_lt25
        lt25 = (theta + damp_angle) * slope_lt25 * q * c.svt_in2 / IN2_PER_FT2
        lt50 = (slope_lt50 * defl_rud) * q * c.svt_in2 / IN2_PER_FT2
        lt = lt25 + lt50

        # Net yaw moment: thrust decay then windmill-drag buildup, less the tail loads.
        moment = _moment(time, c, mom_eng, mom_windmill, lt25, lt50)
        theta_2dot = moment / IN_PER_FT / c.izz * DEG_PER_RAD
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
        raise MissingInputError("one_engine_out needs Project.mass (run WTONECG first)")
    # Two mass cases weighing the same is ordinary input, and the pick selects a
    # published case -- so it takes the tie rule (CR-B-1; ``picks.extreme``).
    return extreme(project.mass.cases, lambda m: m.weight_lb)


def _engine_power(eng: EngineInput, use_takeoff: bool) -> float:
    """Max horsepower of one engine (MAXHP). Prefers take-off or max-continuous per
    ``use_takeoff``, falling back to the other when one is unset."""
    primary = eng.takeoff_hp if use_takeoff else eng.max_cont_hp
    other = eng.max_cont_hp if use_takeoff else eng.takeoff_hp
    hp = primary if primary else other
    if not hp:
        raise MissingInputError(
            "one_engine_out needs the failed engine's horsepower "
            "(EngineInput.max_cont_hp or takeoff_hp)")
    return float(hp)


class _LoadCase(NamedTuple):
    """One 23.367 engine-failure design case.

    A load case is defined by its **failure condition**, and that definition -- not
    the speed -- owns two things:

    - ``safety_factor``: set by how the governing regulation *classifies* the load
      (``load_class`` LIMIT vs ULTIMATE), per 14 CFR 23.303. A LIMIT case renders at
      1.5; a case the rule defines as ULTIMATE (or an inherently-ultimate value) is
      SF 1.0 -- a "limit treated as ultimate". Being a *failure* case does **not**
      by itself reduce the factor (the fuel-flow failure below is a failure and is
      still LIMIT / 1.5); only the regulation's classification does.
    - the **speed range** ``[v_lo_kt, v_hi_kt]`` over which the case is considered.
      Because the tail load grows with dynamic pressure (~V^2), the critical load is
      at the top of the range, so the case is evaluated at ``v_hi_kt``; ``v_lo_kt``
      (the VMC floor) records the low end for traceability.

    ``safety_factor`` and ``basis`` live here rather than defaulting at the
    ``ConditionResult`` level so each case's limit/ultimate status is explicit and
    traceable to its definition."""
    label: str
    far_reference: str
    load_class: str          # "LIMIT" | "ULTIMATE" -- set by the case definition, not the speed
    safety_factor: float     # follows from load_class / the regulation, independent of speed
    v_lo_kt: float           # speed range the case is considered over: low end (~VMC) ...
    v_hi_kt: float           # ... to high end = the critical, evaluated speed
    basis: str


# 23.367(a) (TURBOPROPELLER airplanes -- gating on is_turboprop is backlog M4-3;
# Ref 1 Ch 11 p87) defines two failure-condition cases. Each case's DEFINITION fixes
# its safety factor (via how the rule classifies the load) AND the speed range it is
# considered over; the speed does not determine the factor. VMC is the minimum
# control speed, and the Method allows Vs or VSF to be substituted for it:
#   (a)(1) power failure from FUEL-FLOW INTERRUPTION -- LIMIT (SF 1.5), VMC->VD
#   (a)(2) COMPRESSOR-FROM-TURBINE DISCONNECTION / TURBINE-BLADE LOSS
#                                                   -- ULTIMATE (SF 1.0), VMC->VC
# The VMC-floor point (VS substituted for VMC) is reported as a LIMIT design point
# (SF 1.5, decided 2026-07-20) -- the shared low end of both ranges.
_BASIS_VC = ("Case: disconnection of the engine compressor from the turbine or loss of "
             "the turbine blades (23.367(a)(2)). The case definition classifies these "
             "loads as ULTIMATE, so SF=1.0 (limit treated as ultimate -- the factor is "
             "set by the case, not the speed; applying 1.5 would double-factor it). "
             "Considered from VMC (minimum control speed) up to VC; critical at VC.")
_BASIS_VD = ("Case: power failure from fuel-flow interruption (23.367(a)(1)). The case "
             "definition classifies these loads as LIMIT, so SF=1.5 (14 CFR 23.303) -- a "
             "failure case that keeps the full factor. Considered from VMC up to VD; "
             "critical at VD.")
_BASIS_VS = ("VMC floor of the engine-failure cases: VS (clean 1-g stall, from CLmax per "
             "M1-1b) substituted for VMC (minimum control speed) per Ref 1 Ch 11 Method; "
             "reported as a LIMIT design point, SF=1.5.")
_BASIS_OVERRIDE = ("Explicit user-supplied speed; the case is taken as LIMIT (SF=1.5) "
                   "absent a failure-condition classification.")


def _load_cases(project: Project, oeo: OneEngineOutInput) -> List[_LoadCase]:
    """The 23.367 engine-failure design cases, as a case-definition table.

    Each :class:`_LoadCase` declares its own ``load_class``/``safety_factor`` (from the
    case's regulatory classification -- see that class) and the speed range it is
    considered over; it is evaluated at the range's critical (high) end. The
    render/export layer multiplies the calc's LIMIT loads by ``safety_factor`` to emit
    ULTIMATE deliverables. Future 23.367-adjacent cases (flight-test factors, a 14 CFR
    23.302/25.302 probability-interpolated factor of 1.0-1.5) slot in as new rows with
    their own classification and factor. ``oeo.speeds_kt`` overrides with an explicit
    speed list, each a LIMIT case at that single speed."""
    sp = project.speeds
    if oeo.speeds_kt:
        return [_LoadCase(f"V={v:g} kt", "23.367", "LIMIT", ULTIMATE_FACTOR,
                          float(v), float(v), _BASIS_OVERRIDE) for v in oeo.speeds_kt]
    if sp is None:
        raise MissingInputError("one_engine_out needs Project.speeds (or OneEngineOutInput.speeds_kt)")
    # VS (the VMC substitute / shared low end of both cases' speed ranges) is derived
    # from CLmax (M1-1b); available only when Project.aero_coeffs is present.
    try:
        from .structural_speeds import design_speed_values
        vs = design_speed_values(project, sp).vs
    except (ValueError, ZeroDivisionError):
        vs = 0.0
    cases: List[_LoadCase] = []
    if sp.chosen_vc:
        v_hi = float(sp.chosen_vc)
        cases.append(_LoadCase("VC (ultimate)", "23.367(a)(2)", "ULTIMATE", 1.0,
                               vs or v_hi, v_hi, _BASIS_VC))
    if sp.chosen_vd:
        v_hi = float(sp.chosen_vd)
        cases.append(_LoadCase("VD (limit)", "23.367(a)(1)", "LIMIT", ULTIMATE_FACTOR,
                               vs or v_hi, v_hi, _BASIS_VD))
    if vs:
        cases.append(_LoadCase("VS", "23.367", "LIMIT", ULTIMATE_FACTOR,
                               float(vs), float(vs), _BASIS_VS))
    if not cases:
        raise MissingInputError("one_engine_out found no speeds; set chosen_vc/chosen_vd on Project.speeds")
    return cases


def _case_inputs(project: Project, v_kt: float) -> CaseInputs:
    """Assemble the scalar simulation inputs for one speed from the project slices."""
    oeo = project.one_engine_out
    # Through SELECT's effective v-tail inputs (#95, C210-5): a blank rudder
    # area SR derives from its hinge halves there, and the 23.367 simulation
    # must size the same rudder SELECT does.
    from .select import effective_vtail_inputs

    vt: Optional[VTailLoadsInput] = effective_vtail_inputs(project)
    if oeo is None:
        raise MissingInputError("one_engine_out needs the 'one_engine_out' input slice")
    if vt is None:
        raise MissingInputError("one_engine_out needs Project.vtail_loads (vertical-tail geometry)")
    if not project.engines:
        raise MissingInputError("one_engine_out needs Project.engines (the failed engine)")
    # The condition has to exist before it can be simulated. Without this the
    # march ran with ``thrust * bleng == 0`` -- no forcing at all -- and reported
    # zero tail load, zero yaw rate and "NOT recovered ... uncontrollable" for an
    # airplane that cannot have an engine-out case (#84, C210-43). The predicate
    # is ``applicability``'s, shared with the coverage table and the GUI, so the
    # three cannot answer differently.
    na = engine_failure_not_applicable(project)
    if na:
        raise MissingInputError(f"one_engine_out: {na}")
    if not (0 <= oeo.failed_engine_index < len(project.engines)):
        raise ValueError(f"failed_engine_index {oeo.failed_engine_index} out of range")
    from .engine import effective_engine
    eng = effective_engine(project, project.engines[oeo.failed_engine_index])
    if not eng.prop_diameter_in or eng.prop_diameter_in <= 0:
        raise MissingInputError(
            f"one_engine_out: engine {oeo.failed_engine_index} "
            f"({eng.engine_designation or 'unnamed'}) has no propeller diameter -- "
            + PROPELLER_ONLY_NOTE)

    case = _heaviest_case(project)
    izz = oeo.izz_slugft2 or (case.izz / LBIN2_PER_SLUGFT2)
    xcg = oeo.xcg_in or case.cg_x
    alt = oeo.altitude_ft if oeo.altitude_ft is not None else (
        project.speeds.shoulder_altitude_ft if project.speeds else 0.0)
    if izz <= 0:
        raise MissingInputError("one_engine_out needs a non-zero IZZ (Project.mass or izz_slugft2)")

    return CaseInputs(
        arvt=vt.aspect_ratio_vtail,
        svt_in2=vt.vtail_area_sqft * IN2_PER_FT2,
        sr_in2=vt.rudder_area_sqft * IN2_PER_FT2,
        defl_rud_max=vt.rudder_deflection_deg,
        xcg=xcg,
        xt25=vt.xv25,
        xt50=vt.xv50,
        v_kt=v_kt,
        alt_ft=alt,
        izz=izz,
        bleng=abs(eng.engine_cg[1]),
        maxhp=_engine_power(eng, oeo.use_takeoff_power),
        dia_ft=eng.prop_diameter_in / IN_PER_FT,
        time2decay=oeo.thrust_decay_time_s,
        time2drag=oeo.windmill_drag_time_s,
        inctimerud=oeo.rudder_travel_time_s,
        dt=oeo.time_step_s,
    )


def time_history(project: Project, speed_label: str) -> List[HistoryRow]:
    """The full Euler time history for one named speed case (for the UI re-run).

    ``speed_label`` matches a :class:`ConditionResult` title produced by :func:`run`
    (e.g. ``"VC (ultimate)"``)."""
    oeo = project.one_engine_out
    if oeo is None:
        raise MissingInputError("one_engine_out needs the 'one_engine_out' input slice")
    for lc in _load_cases(project, oeo):
        if lc.label == speed_label:
            rows, _ = simulate(_case_inputs(project, lc.v_hi_kt))
            return rows
    raise ValueError(f"unknown one-engine-out speed case {speed_label!r}")


def run(project: Project) -> ModuleResult:
    """Run ONENGOUT: the one-engine-out maximum vertical-tail load at each speed.

    One :class:`ConditionResult` per speed (VC ultimate / VD limit / VS): engine
    thrust, windmill drag, maximum yawing velocity, **maximum tail load**, the 25%/50%
    MAC loads at the peak, and the time to recovery (FAR 23.367)."""
    oeo = project.one_engine_out
    if oeo is None:
        raise MissingInputError("one_engine_out needs the 'one_engine_out' input slice")
    if oeo.thrust_decay_time_s <= 0 or oeo.windmill_drag_time_s <= 0 or oeo.rudder_travel_time_s <= 0:
        raise ValueError(
            "one_engine_out needs positive thrust_decay_time_s, windmill_drag_time_s "
            "and rudder_travel_time_s")

    # Own allocator, scoped to this run: ONENGOUT's dynamic 23.367 case is not one
    # of SELECT's vtail-critical conditions, so it is a different case object with
    # its own ID -- seeded into its own disjoint band (VTAIL_BAND_ONENGOUT) rather
    # than sharing SELECT's counter. Before M4-2 it started at VT-01 like SELECT's
    # own sequence, so the two minted the *same* id for different physical cases
    # (M4-2 decision 5); tests/test_case_ids.py is the guard.
    allocator = CaseIdAllocator()
    allocator.seed("vtail", VTAIL_BAND_ONENGOUT)
    conditions: List[ConditionResult] = []
    for lc in _load_cases(project, oeo):
        c = _case_inputs(project, lc.v_hi_kt)
        _rows, s = simulate(c)
        case_ref = CaseRef(
            case_id=allocator.next_id("vtail"), component="vtail",
            condition=f"one engine out — {lc.label}", speed_kt=c.v_kt,
            far_reference=lc.far_reference)
        conditions.append(ConditionResult(
            title=f"One engine out — {lc.label}",
            far_reference=lc.far_reference,
            safety_factor=lc.safety_factor,
            case_ref=case_ref,
            values=[
                LoadValue("V (EAS)", c.v_kt, "kt(EAS)", key="v_eas"),
                LoadValue("Engine thrust", s.thrust_lb, "lb", key="engine_thrust"),
                LoadValue("Windmill drag", s.windmill_drag_lb, "lb", key="windmill_drag"),
                LoadValue("Max yawing velocity", s.max_yaw_rate_deg_s, "deg/s", key="max_yawing_velocity"),
                LoadValue("Max tail load", s.max_tail_load_lb, "lb", key="max_tail_load"),
                LoadValue("Load at 25% MAC (at peak)", s.lt25_at_peak_lb, "lb", key="load_at_25_pct_mac_at_peak"),
                LoadValue("Load at 50% MAC (at peak)", s.lt50_at_peak_lb, "lb", key="load_at_50_pct_mac_at_peak"),
                LoadValue("Time to recovery", s.time_to_recovery_s, "s", key="time_to_recovery"),
            ],
            note=(f"{lc.basis} "
                  f"Failed engine #{oeo.failed_engine_index} at butt line {c.bleng:g} in; "
                  f"IZZ {c.izz:g} slug-ft^2."
                  + ("" if s.recovered else
                     f" NOT recovered within {_MAX_SIM_TIME_S:g} s — the airplane is "
                     "uncontrollable at this speed (likely below VMC); the tail load and "
                     "yaw rate are the values at the simulation limit.")),
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
