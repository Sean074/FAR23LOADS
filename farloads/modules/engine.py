"""Pure engine-mount load calculations, ported from ENGLOADS.BAS.

Every function takes an :class:`EngineInput` and returns one or more
:class:`ConditionResult` objects. No printing, no I/O -- this is the testable
core that reproduces the FAR 23 LOADS manual's worked examples.

Sign convention (from the original program): engine-mount reaction torque is
reported negative, and "clockwise from the pilot's view is positive" for rotor
RPM and stoppage torque.
"""

from __future__ import annotations

import itertools
from typing import List

from ..constants import (
    G,
    GYRO_VERTICAL_LOAD_FACTOR,
    HP_TO_TORQUE,
    PITCH_RATE,
    RPM_TO_RAD_S,
    TURBOPROP_MALFUNCTION_FACTOR,
    TURBOPROP_TORQUE_FACTOR,
    TWO_PI,
    VSF,
    YAW_RATE,
    reciprocating_torque_factor,
)
from ..models import (
    ConditionResult,
    EngineInput,
    LoadValue,
    ModuleResult,
    Project,
    Rotor,
    Vec3,
)
from ..registry import register


# --------------------------------------------------------------------------- #
# Derived / shared quantities
# --------------------------------------------------------------------------- #

def combined_weight(inp: EngineInput) -> float:
    """PPWT -- combined propeller + engine weight, lb."""
    return inp.prop_weight_lb + inp.engine_weight_lb


def combined_cg(inp: EngineInput) -> Vec3:
    """Weight-averaged CG of prop + engine (XPP, YPP, ZPP).

    Truncated to 3 decimals exactly as the BASIC did (INT(x*1000)/1000).
    """
    ppwt = combined_weight(inp)
    if ppwt == 0:
        return (0.0, 0.0, 0.0)

    def trunc3(v: float) -> float:
        return int(v * 1000) / 1000

    out = []
    for prop_c, eng_c in zip(inp.prop_cg, inp.engine_cg):
        out.append(trunc3((inp.prop_weight_lb * prop_c + inp.engine_weight_lb * eng_c) / ppwt))
    return (out[0], out[1], out[2])


def torque_from_hp(hp: float, rpm: float) -> float:
    """Engine torque (ft-lb) from horsepower and RPM: HP*33000/(2*pi*RPM)."""
    return hp * HP_TO_TORQUE / (TWO_PI * rpm)


def takeoff_torque(inp: EngineInput) -> float:
    """TOTORQ for reciprocating engines."""
    return torque_from_hp(inp.takeoff_hp, inp.takeoff_rpm)


def max_cont_torque(inp: EngineInput) -> float:
    """CONTTORQ for reciprocating engines."""
    return torque_from_hp(inp.max_cont_hp, inp.max_cont_rpm)


def torque_factor(inp: EngineInput) -> float:
    """Torque multiplication factor used in 23.361(a)(2)."""
    if inp.is_turboprop:
        return TURBOPROP_TORQUE_FACTOR
    return reciprocating_torque_factor(inp.cylinders)


def _omega(rpm: float) -> float:
    """RPM -> rad/s."""
    return rpm * RPM_TO_RAD_S


def _prop_inertia(inp: EngineInput) -> float:
    """IPROP -- propeller blade polar inertia about the shaft, slug-ft^2.

    Uses the measured ``prop_inertia`` when supplied; otherwise approximates the
    blades only (PROPWT - HUBWT) as thin rods, I = m*L^2/3 with the blade length
    taken as the prop radius.
    """
    if inp.prop_inertia is not None:
        return inp.prop_inertia
    blade_weight = inp.prop_weight_lb - (inp.hub_weight_lb or 0.0)
    radius_ft = inp.prop_diameter_in / 2 / 12
    val = blade_weight / G * radius_ft ** 2 / 3
    return int(val * 1000) / 1000  # BASIC truncated to 3 decimals


def _rotor_inertia(rotor: Rotor) -> float:
    """IROTOR -- rotor polar inertia, slug-ft^2.

    Uses the rotor's measured ``inertia`` when supplied; otherwise approximates a
    solid disk, I = 0.5*m*r^2.
    """
    if rotor.inertia is not None:
        return rotor.inertia
    radius_ft = rotor.diameter_in / 2 / 12
    return 0.5 * rotor.weight_lb / G * radius_ft ** 2


# --------------------------------------------------------------------------- #
# Individual FAR 23 conditions
# --------------------------------------------------------------------------- #

def condition_361_a1(inp: EngineInput) -> ConditionResult:
    """FAR 23.361(a)(1): limit takeoff torque + 75% limit maneuver vertical load."""
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    n75 = 0.75 * inp.limit_load_factor
    vload = n75 * ppwt
    torque = inp.max_engine_torque if inp.is_turboprop else takeoff_torque(inp)
    return ConditionResult(
        title="Limit takeoff torque with 75% limit maneuver vertical load factor",
        far_reference="23.361(a)(1)",
        values=[
            LoadValue("Vertical load factor", n75),
            LoadValue("Vertical down load", vload, "lb"),
            LoadValue("Applied at X", cg[0], "in"),
            LoadValue("Applied at Y", cg[1], "in"),
            LoadValue("Applied at Z", cg[2], "in"),
            LoadValue("Engine mount torque", -torque, "ft-lb"),
        ],
    )


def condition_361_a2(inp: EngineInput) -> ConditionResult:
    """FAR 23.361(a)(2): factor x max continuous torque + 100% limit vertical load."""
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    n100 = inp.limit_load_factor
    vload = n100 * ppwt
    factor = torque_factor(inp)
    base_torque = inp.cruise_torque if inp.is_turboprop else max_cont_torque(inp)
    torque = factor * base_torque
    return ConditionResult(
        title="Factor times max continuous torque with 100% limit maneuver vertical load factor",
        far_reference="23.361(a)(2)",
        values=[
            LoadValue("Vertical load factor", n100),
            LoadValue("Vertical down load", vload, "lb"),
            LoadValue("Applied at X", cg[0], "in"),
            LoadValue("Applied at Y", cg[1], "in"),
            LoadValue("Applied at Z", cg[2], "in"),
            LoadValue("Torque factor", factor),
            LoadValue("Max continuous torque", base_torque, "ft-lb"),
            LoadValue("Engine mount torque", -torque, "ft-lb"),
        ],
    )


def condition_363(inp: EngineInput) -> ConditionResult:
    """FAR 23.363: side load independent of other flight loads."""
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    ny = max(inp.limit_load_factor / 3, 1.33)
    side_load = ny * ppwt
    return ConditionResult(
        title="Side load independent of other flight loads",
        far_reference="23.363(a)&(b)",
        values=[
            LoadValue("Vertical load factor", 0.0),
            LoadValue("Side load factor", ny),
            LoadValue("Side load", side_load, "lb"),
            LoadValue("Applied at X", cg[0], "in"),
            LoadValue("Applied at Y", cg[1], "in"),
            LoadValue("Applied at Z", cg[2], "in"),
        ],
    )


def condition_361_a3(inp: EngineInput) -> ConditionResult:
    """FAR 23.361(a)(3): turboprop propeller control malfunction (turboprop only)."""
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    torque = TURBOPROP_MALFUNCTION_FACTOR * inp.max_engine_torque
    vload = 1.0 * ppwt
    return ConditionResult(
        title="Turboprop propeller control malfunction",
        far_reference="23.361(a)(3)",
        values=[
            LoadValue("Vertical load factor", 1.0),
            LoadValue("Vertical down load", vload, "lb"),
            LoadValue("Applied at X", cg[0], "in"),
            LoadValue("Applied at Y", cg[1], "in"),
            LoadValue("Applied at Z", cg[2], "in"),
            LoadValue("Engine mount torque", -torque, "ft-lb"),
        ],
    )


def condition_361_b1(inp: EngineInput) -> ConditionResult:
    """FAR 23.361(b)(1): torque from sudden engine stoppage (turboprop only)."""
    iprop = _prop_inertia(inp)
    omega_prop = _omega(inp.takeoff_rpm)
    dt = inp.stop_time_s
    torq_prop = iprop * (omega_prop / dt)

    torq_rotors = 0.0
    rotor_values: List[LoadValue] = []
    for i, rotor in enumerate(inp.rotors, start=1):
        irotor = _rotor_inertia(rotor)
        torq_rotors += irotor * (_omega(rotor.max_rpm) / dt)
        rotor_values.append(LoadValue(f"Ixx rotor({i})", irotor, "slug-ft^2"))

    torq_total = torq_prop + torq_rotors
    values = [LoadValue("Ixx propeller", iprop, "slug-ft^2")]
    values.extend(rotor_values)
    values.append(LoadValue("Time to stop", dt, "s"))
    values.append(LoadValue("Engine mount torque", int(-torq_total), "ft-lb"))
    return ConditionResult(
        title="Torque for sudden stoppage due to malfunction or structural failure",
        far_reference="23.361(b)(1)",
        values=values,
        note="Clockwise from pilot's view is positive.",
    )


def condition_371_b(inp: EngineInput) -> ConditionResult:
    """FAR 23.371(b): gyroscopic loads at max continuous RPM (turboprop only).

    The two gyroscopic moments -- the pitching moment Myy produced by the
    2.5 rad/s yaw rate and the yawing moment Mzz produced by the 1 rad/s pitch
    rate -- each act in either direction. FAR 23.371(b) requires the engine
    mount to sustain *all* combinations of these loads, so the four sign
    permutations of (Myy, Mzz) are each enumerated below, every one applied
    simultaneously with the steady 2.5g vertical load and the max-continuous
    thrust (which act in a single sense in every case).
    """
    iprop = _prop_inertia(inp)
    omega_prop = _omega(inp.max_cont_rpm)

    tpitch = iprop * omega_prop
    for rotor in inp.rotors:
        irotor = _rotor_inertia(rotor)
        tpitch += irotor * _omega(rotor.max_rpm)

    m_yaw = YAW_RATE * tpitch     # Myy due to 2.5 rad/s yaw
    m_pitch = PITCH_RATE * tpitch  # Mzz due to 1 rad/s pitch
    thrust = inp.max_engine_torque * omega_prop / VSF
    vload = GYRO_VERTICAL_LOAD_FACTOR * combined_weight(inp)

    # Component magnitudes (the four loads to be combined).
    values = [
        LoadValue("Myy due to 2.5 rad/s yaw (+/-)", m_yaw, "ft-lb"),
        LoadValue("Mzz due to 1 rad/s pitch (+/-)", m_pitch, "ft-lb"),
        LoadValue("Vertical 2.5g load", vload, "lb"),
        LoadValue("Max continuous thrust", thrust, "lb"),
    ]

    # Enumerate each load case the mount must be checked against: every sign
    # combination of the two gyroscopic moments. The vertical 2.5g load and the
    # max-continuous thrust (listed once above) are applied simultaneously in
    # every case, so only the varying signed moments are spelled out per case.
    for case, (syaw, spitch) in enumerate(
        itertools.product((+1, -1), repeat=2), start=1
    ):
        ytag = "+" if syaw > 0 else "-"
        ptag = "+" if spitch > 0 else "-"
        prefix = f"Case {case} ({ytag}Myy, {ptag}Mzz)"
        values.append(LoadValue(f"{prefix}: Myy", syaw * m_yaw, "ft-lb"))
        values.append(LoadValue(f"{prefix}: Mzz", spitch * m_pitch, "ft-lb"))

    return ConditionResult(
        title="Gyroscopic loads on engine mount at max continuous RPM",
        far_reference="23.371(b)",
        values=values,
        note=(
            "FAR 23.371(b) requires all four load cases above to be assessed: "
            "every sign combination of the gyroscopic pitching (Myy) and yawing "
            "(Mzz) moments, each combined with the 2.5g vertical load and the "
            "max-continuous thrust acting simultaneously."
        ),
    )


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def run_all(inp: EngineInput) -> List[ConditionResult]:
    """Evaluate every applicable FAR 23 condition for the given input."""
    results = [
        condition_361_a1(inp),
        condition_361_a2(inp),
        condition_363(inp),
    ]
    if inp.is_turboprop:
        results.append(condition_361_a3(inp))
        results.append(condition_361_b1(inp))
        results.append(condition_371_b(inp))
    return results


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #

MODULE_NAME = "engine"


def run(project: Project) -> ModuleResult:
    """Run the engine-mount module against a :class:`Project`.

    Reads the ``engine`` slice of the project (an :class:`EngineInput`) and
    returns its FAR 23 conditions wrapped as a :class:`ModuleResult`. This is the
    uniform entry point the registry, CLI and GUI call; ``run_all`` remains the
    direct ``EngineInput`` -> conditions function used by the calc tests.
    """
    if project.engine is None:
        raise ValueError("Project has no 'engine' slice for the engine module")
    return ModuleResult(module=MODULE_NAME, conditions=run_all(project.engine))


register(MODULE_NAME, run)
