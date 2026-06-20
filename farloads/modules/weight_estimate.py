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
    MassItem,
    MassItemKind,
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

    def mass(label: str, value: float) -> LoadValue:
        # Weights are pounds-*mass* (quantity="mass" -> kg in SI, not N), and are
        # truncated with int(...) to match the original program's printout.
        return LoadValue(label, int(value), "lb", quantity="mass")

    summary = ConditionResult(
        title="Estimated weight summary",
        far_reference=_FAR,
        values=[
            mass("Max take-off weight", wto),
            mass("Useful load", useful),
            mass("Empty weight", empty),
            LoadValue("Empty/take-off ratio", int(100 * empty / wto) / 100),
            mass("Options & miscellaneous", options_misc),
        ],
    )

    structure_result = ConditionResult(
        title="Structure group",
        far_reference=_FAR,
        values=[mass(name, structure[name]) for name in WT_STRUCTURE_FRACTIONS]
        + [mass("Total structure", total_structure)],
    )

    powerplant_result = ConditionResult(
        title="Powerplant group",
        far_reference=_FAR,
        values=[
            mass("Engine installed (incl. propeller)", installed),
            mass("Propeller (included above)", prop),
            mass("Fuel system", fuel_system),
            mass("Exhaust", exhaust),
            mass("Other engine details", engine_other),
            mass("Total powerplant", powerplant),
        ],
    )

    systems_result = ConditionResult(
        title="Systems group",
        far_reference=_FAR,
        values=[mass(name, frac * wto) for name, frac in systems_fracs.items()]
        + [mass("Total systems weight", total_systems)],
    )

    return [summary, structure_result, powerplant_result, systems_result]


# --------------------------------------------------------------------------- #
# Seeding the WTONECG weight data base
# --------------------------------------------------------------------------- #
# Estimate rows that are roll-ups or duplicates rather than discrete components,
# so they are skipped when seeding the itemized data base.
_SEED_SKIP_LABELS = frozenset({
    "Total structure",
    "Total powerplant",
    "Total systems weight",
    "Propeller (included above)",  # already inside "Engine installed"
})


def estimate_to_mass_items(inp: WeightEstimationInput) -> List[MassItem]:
    """Build seed :class:`MassItem` rows from the statistical weight estimate.

    Expands the estimate's structure, powerplant and systems component weights
    (plus the summary's options/miscellaneous) into the itemized weight data base
    WTONECG sums. WTESTIMA supplies only the component *weights*; stations and
    per-item inertias are left at zero for the user to fill in. Every seeded row
    is part of the empty weight (``MassItemKind.EMPTY``).
    """
    summary, structure, powerplant, systems = estimate(inp)
    items: List[MassItem] = []
    options_misc = next((v for v in summary.values if v.label == "Options & miscellaneous"), None)
    for group in (structure, powerplant, systems):
        for v in group.values:
            if v.label in _SEED_SKIP_LABELS:
                continue
            items.append(MassItem(name=v.label, weight_lb=float(v.value), kind=MassItemKind.EMPTY))
    if options_misc is not None:
        items.append(MassItem(
            name=options_misc.label, weight_lb=float(options_misc.value), kind=MassItemKind.EMPTY,
        ))
    return items


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "weight_estimate"


_CONCEPT_NOTE = (
    "Concept mode: WTESTIMA is a GA sanity estimate only -- it is out of its "
    "<=12,500 lb calibration band. Use the itemized/direct weight "
    "(WeightInput.direct_totals) as the design weight."
)


def run(project: Project) -> ModuleResult:
    """Run WTESTIMA against a :class:`Project`'s ``weight.estimation`` inputs.

    In concept mode the statistical estimate is flagged as a sanity-only figure (the
    summary condition's note); the core :func:`estimate` is unchanged so the FAR23
    Appendix-A oracle still holds.
    """
    if project.weight is None or project.weight.estimation is None:
        raise ValueError("Project has no 'weight.estimation' inputs for the weight_estimate module")
    conditions = estimate(project.weight.estimation)
    if project.is_concept and conditions:
        conditions[0].note = _CONCEPT_NOTE
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
