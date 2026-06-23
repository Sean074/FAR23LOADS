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
    """FAR 23.361(a)(1): limit takeoff torque + 75% limit maneuver vertical load.

    **Approved correction (AC 23-19A).** 23.361(c) directs the mean-torque factor
    to be applied to the limit engine torque considered under *all* of paragraph
    (a) -- this takeoff case included -- so the design torque is
    ``factor x mean takeoff torque`` (the same factor as (a)(2)). Amendment 23-26
    omitted the factor here, a non-conservative drafting error that yields lower
    loads; Amendment 23-45 restored it, and AC 23-19A directs applying it
    regardless of certification basis. McMaster's manual encodes the pre-23-45
    *unfactored* form (Appendix A prints 554.39 ft-lb for the IO-520-BB); this
    suite applies the correction (737.34 ft-lb) -- an approved, documented
    deviation from the oracle (see CLAUDE.md "Approved corrections to the source").
    For a turbopropeller the result (1.25 x mean takeoff torque) is identical to
    25.361(a)(1)(i).
    """
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    n75 = 0.75 * inp.limit_load_factor
    vload = n75 * ppwt
    factor = torque_factor(inp)
    base_torque = inp.max_engine_torque if inp.is_turboprop else takeoff_torque(inp)
    torque = factor * base_torque
    return ConditionResult(
        title="Limit takeoff torque (factor x mean) with 75% limit maneuver vertical load factor",
        far_reference="23.361(a)(1)",
        values=[
            LoadValue("Vertical load factor", n75),
            LoadValue("Vertical down load", vload, "lb"),
            LoadValue("Applied at X", cg[0], "in"),
            LoadValue("Applied at Y", cg[1], "in"),
            LoadValue("Applied at Z", cg[2], "in"),
            LoadValue("Torque factor", factor),
            LoadValue("Mean takeoff torque", base_torque, "ft-lb"),
            LoadValue("Engine mount torque", -torque, "ft-lb"),
        ],
        note=(
            "Mean-torque factor applied to the takeoff case per AC 23-19A "
            "(23.361(c); Amdt 23-45 correction of the Amdt 23-26 omission). "
            "McMaster's manual leaves this case unfactored (554.39 ft-lb)."
        ),
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
    """FAR 23.361(a)(3): turboprop propeller control malfunction (turboprop only).

    **Approved correction (AC 23-19A).** Paragraph (a)(3) is *"a limit engine
    torque corresponding to takeoff power and propeller speed, multiplied by a
    factor accounting for propeller control system malfunction"* (1.6 absent a
    rational analysis). That base "limit engine torque corresponding to takeoff
    power and propeller speed" is the same quantity as (a)(1), and 23.361(c)
    directs the mean-torque factor (1.25 turbopropeller) onto *all* limit engine
    torques considered under paragraph (a). The design torque is therefore
    ``1.6 x 1.25 x mean takeoff torque`` (= 2.0 x mean). Amendment 23-26 omitted
    the (c) factor here, a non-conservative drafting error (lower loads) that
    Amendment 23-45 restored; AC 23-19A directs applying it regardless of
    certification basis. McMaster's manual / ``ENGLOADS.BAS`` (``TTP=1.6*ENGTORQ``)
    encode the pre-23-45 form (1.6 x mean only), so this is an approved, documented
    deviation from the oracle -- the same correction already applied to
    ``condition_361_a1`` (see CLAUDE.md "Approved corrections to the source").
    """
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    factor = torque_factor(inp)  # 1.25 turbopropeller (23.361(c))
    base_torque = inp.max_engine_torque  # mean takeoff torque
    torque = TURBOPROP_MALFUNCTION_FACTOR * factor * base_torque
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
            LoadValue("Torque factor", factor),
            LoadValue("Malfunction factor", TURBOPROP_MALFUNCTION_FACTOR),
            LoadValue("Mean takeoff torque", base_torque, "ft-lb"),
            LoadValue("Engine mount torque", -torque, "ft-lb"),
        ],
        note=(
            "Mean-torque factor (1.25) applied to the malfunction case per "
            "AC 23-19A (23.361(c); Amdt 23-45 correction of the Amdt 23-26 "
            "omission): torque = 1.6 x 1.25 x mean takeoff torque. McMaster's "
            "manual / ENGLOADS.BAS leave this 1.25 factor off (1.6 x mean only)."
        ),
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
# Optional FAR 25 supplemental conditions (turbopropeller installations)
# --------------------------------------------------------------------------- #
# An *additive* superset enabled by ``Project.include_far25``. The FAR 23 core
# above is untouched and stays oracle-locked; these append on top. Ported from
# 14 CFR 25.361 / 25.371 (see ``reference/14CFR_Part25_engine_torque.md``).
#
# Scope: turbopropeller engines only. 25.361(a)(2) defines a limit-torque factor
# only for turbopropeller (1.25 x mean torque) and "other turbine engines"
# (= max accelerating torque); it is silent on reciprocating engines, and this
# tool's mass/gyro math is propeller-centric. No McMaster worked example exists
# for Part 25, so these are formula-closure checked, not locked to a printed
# figure (the LANDLOAD precedent).
#
# *Reduced to the non-duplicative cases only.* After the AC 23-19A correction to
# 23.361(a)(1) (which factors the takeoff torque), the FAR 25 torque cases
# 25.361(a)(1)(i)/(ii)/(iii) became bit-for-bit duplicates of the corrected
# 23.361(a)(1)/(a)(2)/(a)(3) for a turbopropeller, so they were removed. What
# remains is genuinely additive over the FAR 23 set:
#   - 25.361(a)(3)(ii) maximum engine acceleration torque -- no FAR 23 analog;
#   - 25.361(a)(3)(i) sudden stoppage combined with a simultaneous 1g vertical
#     load (23.361(b)(1) reports the torque alone);
#   - 25.371 gyroscopic loads using the project's A2 limit load factor for the
#     simultaneous vertical (23.371(b) uses the fixed 2.5g of the oracle).
# These stay behind the opt-in flag (off for any GA/oracle run) so the FAR 23
# Appendix A/B outputs are unchanged -- making them unconditional would alter the
# Appendix B turboprop case count and gyro vertical, breaking oracle-lock.


def _stoppage_torque(inp: EngineInput):
    """Total sudden-stoppage reaction torque (ft-lb) + per-rotor inertia detail.

    The prop + rotor angular momentum shed over ``stop_time_s``. Shared by the
    FAR 25 sudden-deceleration case; FAR 23.361(b)(1) keeps its own inline copy so
    its oracle output stays byte-identical.
    """
    iprop = _prop_inertia(inp)
    dt = inp.stop_time_s
    torq = iprop * (_omega(inp.takeoff_rpm) / dt)
    detail = [LoadValue("Ixx propeller", iprop, "slug-ft^2")]
    for i, rotor in enumerate(inp.rotors, start=1):
        irotor = _rotor_inertia(rotor)
        torq += irotor * (_omega(rotor.max_rpm) / dt)
        detail.append(LoadValue(f"Ixx rotor({i})", irotor, "slug-ft^2"))
    detail.append(LoadValue("Time to stop", dt, "s"))
    return torq, detail


def condition_25_361_a3i(inp: EngineInput) -> ConditionResult:
    """FAR 25.361(a)(3)(i): sudden engine deceleration (stoppage) torque at 1g.

    Same stoppage torque as 23.361(b)(1), but FAR 25 applies it simultaneously
    with 1g level flight loads.
    """
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    torq_total, detail = _stoppage_torque(inp)
    values = list(detail)
    values.extend([
        LoadValue("Vertical load factor", 1.0),
        LoadValue("Vertical down load", 1.0 * ppwt, "lb"),
        LoadValue("Applied at X", cg[0], "in"),
        LoadValue("Applied at Y", cg[1], "in"),
        LoadValue("Applied at Z", cg[2], "in"),
        LoadValue("Engine mount torque", int(-torq_total), "ft-lb"),
    ])
    return ConditionResult(
        title="Sudden engine deceleration (stoppage) torque with 1g level flight loads",
        far_reference="25.361(a)(3)(i)",
        values=values,
        note="Clockwise from pilot's view is positive.",
    )


def condition_25_361_a3ii(inp: EngineInput) -> ConditionResult:
    """FAR 25.361(a)(3)(ii): maximum engine acceleration torque at 1g.

    Uses the supplied ``max_accel_torque``; if none is given it falls back to the
    max engine torque and the condition is flagged so the assumption is visible.
    """
    ppwt = combined_weight(inp)
    cg = combined_cg(inp)
    defaulted = inp.max_accel_torque is None
    accel_torque = inp.max_engine_torque if defaulted else inp.max_accel_torque
    note = None
    if defaulted:
        note = "Max accelerating torque defaulted to max engine torque (no separate value supplied)."
    return ConditionResult(
        title="Maximum engine acceleration torque with 1g level flight loads",
        far_reference="25.361(a)(3)(ii)",
        values=[
            LoadValue("Vertical load factor", 1.0),
            LoadValue("Vertical down load", 1.0 * ppwt, "lb"),
            LoadValue("Applied at X", cg[0], "in"),
            LoadValue("Applied at Y", cg[1], "in"),
            LoadValue("Applied at Z", cg[2], "in"),
            LoadValue("Max accelerating torque", accel_torque, "ft-lb"),
            LoadValue("Engine mount torque", -accel_torque, "ft-lb"),
        ],
        note=note,
    )


def condition_25_371(inp: EngineInput) -> ConditionResult:
    """FAR 25.371: gyroscopic loads at max continuous RPM (turbopropeller).

    25.371 derives the body pitch/yaw rates from the maneuver/gust/ground
    conditions of 25.331/341/349/351/473/479/481 -- which this tool does not
    solve. As a conservative initial-concept stand-in the fixed FAR 23.371(b)
    rates (2.5 rad/s yaw, 1 rad/s pitch) are used: anything heavier than a light
    GA single maneuvers slower, so these bound the maneuver-derived rates and the
    gyro moment (linear in body rate) is over-estimated. The simultaneous vertical
    load uses the project's actual A2 limit load factor (25.333(b)) rather than the
    fixed 2.5g, so it is not under-conservative when A2 > 2.5.
    """
    iprop = _prop_inertia(inp)
    omega_prop = _omega(inp.max_cont_rpm)

    tpitch = iprop * omega_prop
    for rotor in inp.rotors:
        tpitch += _rotor_inertia(rotor) * _omega(rotor.max_rpm)

    m_yaw = YAW_RATE * tpitch
    m_pitch = PITCH_RATE * tpitch
    thrust = inp.max_engine_torque * omega_prop / VSF
    vload = inp.limit_load_factor * combined_weight(inp)

    values = [
        LoadValue("Myy due to 2.5 rad/s yaw (+/-)", m_yaw, "ft-lb"),
        LoadValue("Mzz due to 1 rad/s pitch (+/-)", m_pitch, "ft-lb"),
        LoadValue("Vertical limit-load (A2) load", vload, "lb"),
        LoadValue("Max continuous thrust", thrust, "lb"),
    ]
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
        far_reference="25.371",
        values=values,
        note=(
            "Conservative concept stand-in: fixed FAR 23.371(b) rates (2.5 rad/s "
            "yaw, 1 rad/s pitch) used in lieu of the 25.371 maneuver-derived rates; "
            "valid while the concept's actual rates stay at or below these. All four "
            "sign combinations of Myy/Mzz are combined with the A2 vertical load and "
            "max-continuous thrust acting simultaneously."
        ),
    )


def run_far25(inp: EngineInput) -> List[ConditionResult]:
    """Optional FAR 25 supplemental engine cases. Turbopropeller only; empty otherwise.

    Only the cases that are *not* duplicated by the corrected FAR 23 set: sudden
    stoppage with a simultaneous 1g vertical, maximum engine acceleration torque
    (no FAR 23 analog), and the A2-vertical gyroscopic case. The FAR 25 torque
    cases 25.361(a)(1)(i)/(ii)/(iii) were removed as exact duplicates of the
    corrected 23.361(a)(1)/(a)(2)/(a)(3).
    """
    if not inp.is_turboprop:
        return []
    return [
        condition_25_361_a3i(inp),
        condition_25_361_a3ii(inp),
        condition_25_371(inp),
    ]


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def run_all(inp: EngineInput, *, include_far25: bool = False) -> List[ConditionResult]:
    """Evaluate every applicable FAR 23 condition for the given input.

    When ``include_far25`` is set, the optional FAR 25 cases (turbopropeller only)
    are appended after the FAR 23 set; the FAR 23 conditions themselves are
    unchanged either way.
    """
    results = [
        condition_361_a1(inp),
        condition_361_a2(inp),
        condition_363(inp),
    ]
    if inp.is_turboprop:
        results.append(condition_361_a3(inp))
        results.append(condition_361_b1(inp))
        results.append(condition_371_b(inp))
    if include_far25:
        results.extend(run_far25(inp))
    return results


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #

MODULE_NAME = "engine"


def run(project: Project) -> ModuleResult:
    """Run the engine-mount module against a :class:`Project`.

    Evaluates the FAR 23 conditions for **every** engine in ``project.engines``
    and concatenates them into one :class:`ModuleResult`. With a single engine the
    output is identical to evaluating that engine alone; with two or four
    (wing-mounted) engines each condition's title is prefixed with the engine's
    designation so the per-engine groups stay distinct. ``run_all`` remains the
    direct ``EngineInput`` -> conditions function used by the calc tests.
    """
    if not project.engines:
        raise ValueError("Project has no engines for the engine module")

    single = len(project.engines) == 1
    conditions: List[ConditionResult] = []
    for i, eng in enumerate(project.engines, start=1):
        for cond in run_all(eng, include_far25=project.include_far25):
            if not single:
                tag = eng.engine_designation or f"engine {i}"
                cond = ConditionResult(
                    title=f"[{tag}] {cond.title}",
                    far_reference=cond.far_reference,
                    values=cond.values,
                    note=cond.note,
                )
            conditions.append(cond)
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
