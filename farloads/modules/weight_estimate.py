"""Statistical weight estimation, ported from WTESTIMA.BAS (Hal C. McMaster).

WTESTIMA is the head of the mass-properties pipeline: from a handful of mission
inputs (power, seats, endurance, baggage, pressurization, engine family) it
estimates the take-off, empty and component weights that seed the weight data
base the rest of the suite reads. It is a statistical correlation, not a load
calculation -- see Reference 1 Ch 2 and the User's Guide Tables 3.1/3.2.

The original prints every figure through ``INT(...)`` (truncation toward zero);
that truncation is preserved here so the figures match the manual's printout
exactly. The single-engine "misc other system wt" reads 0 because the BASIC
prints an unset variable on that path -- preserved as a documented quirk.

Reference: WTESTIMA.BAS, Appendix C p374-376; worked example Appendix A p133.
"""

from __future__ import annotations

from typing import List

from ..constants import (
    SEAT_WEIGHT_LB,
    WT_ENGINE_OTHER_FRACTION,
    WT_EXHAUST_FRACTION_MULTI,
    WT_EXHAUST_FRACTION_SINGLE,
    WT_FUEL_COEFF_2CYCLE,
    WT_FUEL_COEFF_RECIP,
    WT_FUEL_COEFF_TURBOPROP,
    WT_FUEL_SYSTEM_FRACTION,
    WT_K_BASE,
    WT_K_LIQUID_COOLED,
    WT_K_MULTI_ENGINE,
    WT_K_ONE_SEAT,
    WT_K_PRESSURIZED,
    WT_K_RECIP_2CYCLE,
    WT_K_TURBOCHARGED,
    WT_K_TURBOPROP,
    WT_PROP_COEFF,
    WT_PROP_EXPONENT,
    WT_STRUCTURE_FRACTIONS,
    WT_SYSTEMS_MULTI,
    WT_SYSTEMS_MULTI_TOTAL_FRACTION,
    WT_SYSTEMS_SINGLE,
    WT_SYSTEMS_SINGLE_TOTAL_FRACTION,
    installed_engine_weight,
)
from ..models import (
    ConditionResult,
    LoadValue,
    ModuleResult,
    Project,
    WeightEstimationInput,
)
from ..registry import register

_FAR = "23.25"  # weight limits


def _empty_to_takeoff_ratio(inp: WeightEstimationInput) -> float:
    """K, the empty/take-off weight ratio (WTESTIMA.BAS lines 330-400)."""
    et = inp.engine_weight_type.value
    k = WT_K_BASE
    if inp.seats == 1:
        k += WT_K_ONE_SEAT
    if inp.pressurized:
        k += WT_K_PRESSURIZED
    if inp.engines > 1:
        k += WT_K_MULTI_ENGINE
    if et == "TP":
        k += WT_K_TURBOPROP
    elif et == "RT":
        k += WT_K_RECIP_2CYCLE
    elif et == "TC":
        k += WT_K_TURBOCHARGED
    elif et == "LC":
        k += WT_K_LIQUID_COOLED
    return k


def _fuel_weight(inp: WeightEstimationInput) -> float:
    """Mission fuel weight (WTESTIMA.BAS lines 410-430)."""
    et = inp.engine_weight_type.value
    if et == "RT":
        coeff = WT_FUEL_COEFF_2CYCLE
    elif et == "TP":
        coeff = WT_FUEL_COEFF_TURBOPROP
    else:  # RF / TC / LC
        coeff = WT_FUEL_COEFF_RECIP
    return coeff * inp.max_continuous_hp * inp.cruise_hours


def estimate(inp: WeightEstimationInput) -> List[ConditionResult]:
    """Estimate take-off, empty and component weights for the airplane.

    Returns four labelled groups (summary, structure, powerplant, systems). Every
    figure is truncated with ``int(...)`` to match the original program's printout.
    """
    if inp.engines < 1:
        raise ValueError("WTESTIMA needs at least one engine")
    if inp.seats < 1:
        raise ValueError("WTESTIMA needs at least one seat")

    k = _empty_to_takeoff_ratio(inp)
    fuel = _fuel_weight(inp)
    seats_weight = inp.seats * SEAT_WEIGHT_LB
    useful = fuel + seats_weight + inp.baggage_lb
    wto = useful / (1.0 - k)

    # Constant (HP-driven) powerplant weights.
    installed = installed_engine_weight(inp.engine_weight_type.value, inp.max_continuous_hp, inp.engines)
    prop = inp.engines * WT_PROP_COEFF * (inp.max_continuous_hp / inp.engines) ** WT_PROP_EXPONENT
    fuel_system = WT_FUEL_SYSTEM_FRACTION * installed
    exhaust = (WT_EXHAUST_FRACTION_MULTI if inp.engines >= 2 else WT_EXHAUST_FRACTION_SINGLE) * installed
    engine_other = WT_ENGINE_OTHER_FRACTION * installed
    powerplant = installed + fuel_system + exhaust + engine_other

    multi = inp.engines > 1
    systems_fracs = WT_SYSTEMS_MULTI if multi else WT_SYSTEMS_SINGLE
    systems_total_frac = WT_SYSTEMS_MULTI_TOTAL_FRACTION if multi else WT_SYSTEMS_SINGLE_TOTAL_FRACTION

    # Inflate take-off weight by 1% until options/misc is non-negative
    # (WTESTIMA.BAS line 870: IF OPTMISC<0 THEN WTO=1.01*WTO:GOTO 500).
    while True:
        structure = {name: frac * wto for name, frac in WT_STRUCTURE_FRACTIONS.items()}
        total_structure = sum(structure.values())
        total_systems = systems_total_frac * wto
        sum_weights = total_structure + powerplant + total_systems
        options_misc = wto - useful - sum_weights
        if options_misc >= 0:
            break
        wto *= 1.01

    empty = wto - useful

    def lb(value: float) -> int:
        return int(value)

    summary = ConditionResult(
        title="Estimated weight summary",
        far_reference=_FAR,
        values=[
            LoadValue("Max take-off weight", lb(wto), "lb"),
            LoadValue("Useful load", lb(useful), "lb"),
            LoadValue("Empty weight", lb(empty), "lb"),
            LoadValue("Empty/take-off ratio", int(100 * empty / wto) / 100),
            LoadValue("Options & miscellaneous", lb(options_misc), "lb"),
        ],
    )

    structure_result = ConditionResult(
        title="Structure group",
        far_reference=_FAR,
        values=[LoadValue(name, lb(structure[name]), "lb") for name in WT_STRUCTURE_FRACTIONS]
        + [LoadValue("Total structure", lb(total_structure), "lb")],
    )

    powerplant_result = ConditionResult(
        title="Powerplant group",
        far_reference=_FAR,
        values=[
            LoadValue("Engine installed (incl. propeller)", lb(installed), "lb"),
            LoadValue("Propeller (included above)", lb(prop), "lb"),
            LoadValue("Fuel system", lb(fuel_system), "lb"),
            LoadValue("Exhaust", lb(exhaust), "lb"),
            LoadValue("Other engine details", lb(engine_other), "lb"),
            LoadValue("Total powerplant", lb(powerplant), "lb"),
        ],
    )

    systems_result = ConditionResult(
        title="Systems group",
        far_reference=_FAR,
        values=[LoadValue(name, lb(frac * wto), "lb") for name, frac in systems_fracs.items()]
        + [LoadValue("Total systems weight", lb(total_systems), "lb")],
    )

    return [summary, structure_result, powerplant_result, systems_result]


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "weight_estimate"


def run(project: Project) -> ModuleResult:
    """Run WTESTIMA against a :class:`Project`'s ``weight.estimation`` inputs."""
    if project.weight is None or project.weight.estimation is None:
        raise ValueError("Project has no 'weight.estimation' inputs for the weight_estimate module")
    return ModuleResult(module=MODULE_NAME, conditions=estimate(project.weight.estimation))


register(MODULE_NAME, run)
