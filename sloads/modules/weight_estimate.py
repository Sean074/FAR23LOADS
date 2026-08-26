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

import math
from dataclasses import replace
from typing import List, NamedTuple, Tuple

from ..basic import basic_int
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
from ..load_keys import key_from_label as _key
from ..models import (
    ConditionResult,
    LoadValue,
    MassItem,
    MassItemKind,
    MissingInputError,
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
        raise MissingInputError("WTESTIMA needs at least one engine")
    if inp.seats < 1:
        raise MissingInputError("WTESTIMA needs at least one seat")

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
        total_structure = math.fsum(structure.values())
        total_systems = systems_total_frac * wto
        sum_weights = total_structure + powerplant + total_systems
        options_misc = wto - useful - sum_weights
        if options_misc >= 0:
            break
        wto *= 1.01

    empty = wto - useful

    # Operating empty weight (OEW) = manufacturer's empty + the flight crew, which
    # are operating items rather than payload. This is a derived reporting figure
    # only: `wto`/`useful`/`empty` (the Appendix-A oracles) are unchanged, and the
    # crew weight already sits inside `useful` (seats*170), so OEW is not summed
    # with the useful load. Payload occupants = (seats - crew).
    crew_weight = inp.crew * SEAT_WEIGHT_LB
    oew = empty + crew_weight

    def mass(label: str, value: float, key: str = "") -> LoadValue:
        # Weights are pounds-*mass* (quantity="mass" -> kg in SI, not N), and are
        # truncated with basic_int(...) to match the original program's printout.
        #
        # The group rows below are driven by the WT_*_FRACTIONS tables, whose
        # dict keys *are* the component names -- for those the label is data
        # rather than cosmetic text, so the key is derived from it. Rows written
        # out by hand pass their key explicitly (M4-9).
        return LoadValue(label, basic_int(value), "lb", quantity="mass",
                         key=key or _key(label))

    summary = ConditionResult(
        title="Estimated weight summary",
        far_reference=_FAR,
        values=[
            mass("Max take-off weight", wto, "max_take_off_weight"),
            mass("Useful load", useful, "useful_load"),
            mass("Empty weight", empty, "empty_weight"),
            mass("Crew (operating items)", crew_weight, "crew_operating_items"),
            mass("Operating empty weight (OEW)", oew, "operating_empty_weight"),
            LoadValue("Empty/take-off ratio", basic_int(100 * empty / wto) / 100, key="empty_take_off_ratio"),
            mass("Options & miscellaneous", options_misc, "options_and_miscellaneous"),
        ],
    )

    structure_result = ConditionResult(
        title="Structure group",
        far_reference=_FAR,
        values=[mass(name, structure[name]) for name in WT_STRUCTURE_FRACTIONS]
        + [mass("Total structure", total_structure, "total_structure")],
    )

    powerplant_result = ConditionResult(
        title="Powerplant group",
        far_reference=_FAR,
        values=[
            mass("Engine installed (incl. propeller)", installed, "engine_installed"),
            mass("Propeller (included above)", prop, "propeller"),
            mass("Fuel system", fuel_system, "fuel_system"),
            mass("Exhaust", exhaust, "exhaust"),
            mass("Other engine details", engine_other, "other_engine_details"),
            mass("Total powerplant", powerplant, "total_powerplant"),
        ],
    )

    systems_result = ConditionResult(
        title="Systems group",
        far_reference=_FAR,
        values=[mass(name, frac * wto) for name, frac in systems_fracs.items()]
        + [mass("Total systems weight", total_systems, "total_systems_weight")],
    )

    return [summary, structure_result, powerplant_result, systems_result]


# --------------------------------------------------------------------------- #
# Seeding the WTONECG weight data base
# --------------------------------------------------------------------------- #
# Estimate rows that are roll-ups or duplicates rather than discrete components,
# so they are skipped when seeding the itemized data base.
_SEED_SKIP_KEYS = frozenset({
    "total_structure",
    "total_powerplant",
    "total_systems_weight",
    "propeller",  # already inside "Engine installed"
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
    options_misc = next((v for v in summary.values if v.key == "options_and_miscellaneous"), None)
    for group in (structure, powerplant, systems):
        for v in group.values:
            if v.key in _SEED_SKIP_KEYS:
                continue
            items.append(MassItem(name=v.label, weight_lb=float(v.value), kind=MassItemKind.EMPTY))
    if options_misc is not None:
        items.append(MassItem(
            name=options_misc.label, weight_lb=float(options_misc.value), kind=MassItemKind.EMPTY,
        ))
    return items


# --------------------------------------------------------------------------- #
# The estimate against the weight data base (C210-9, issue #78)
# --------------------------------------------------------------------------- #
#: What WTESTIMA's output is for, in one sentence.
#:
#: **Nothing reads these figures.** WTONECG and WTENV are parallel siblings off
#: WTESTIMA in the suite's data flow (UG Table 2.2), but that flow runs through
#: the weight data base -- and here the data base is authored by the user, so the
#: estimate reaches it only when the main GUI's seed button copies it there
#: (:func:`estimate_to_mass_items`). Absent that, the estimate is a statistical
#: sanity figure standing beside the item total, which is the question the owner
#: asked on reaching the block during the Cessna 210 build: "what does this feed,
#: is it either/or with the item table, are the two compared?" (C210-9). The page
#: answered none of the three.
ADVISORY = (
    "Advisory: nothing reads these figures. WTONECG and WTENV take their mass "
    "properties from the itemized weight data base you enter, not from this "
    "statistical estimate — it is here to compare against your item total."
)


class EstimateVsItemized(NamedTuple):
    """One estimated weight beside the entered weight that answers to it.

    Weights are pounds, the calc's internal channel; the display boundary
    converts (``CONVENTIONS.md``). ``entered_lb`` of zero means the data base
    has nothing to compare against yet, which is why
    :func:`compare_with_itemized` drops the row rather than reporting a 100 %
    gap against an empty table.
    """

    quantity: str
    estimated_lb: float
    entered_lb: float

    @property
    def delta_lb(self) -> float:
        """Estimate minus entered — positive when the correlation reads high."""
        return self.estimated_lb - self.entered_lb

    @property
    def delta_pct(self) -> float:
        """:attr:`delta_lb` as a percentage of the entered weight."""
        return 100.0 * self.delta_lb / self.entered_lb if self.entered_lb else 0.0


def compare_with_itemized(project: Project) -> Tuple[EstimateVsItemized, ...]:
    """The estimate's headline weights beside the ones the project actually uses.

    A GA statistical correlation and a weighed airplane are not expected to
    agree closely, and the gap is ordinary scatter rather than an error in
    either -- WTESTIMA gives the Cessna 210 an empty weight of 2,688 lb against
    the type's roughly 2,200 (+22 %). What C210-9 found is that nothing said so,
    or showed the two numbers together at all.

    Both entered figures come from their own owners rather than being re-summed
    here: the empty weight from :meth:`WeightInput.database_totals`, the design
    take-off weight from :func:`sloads.cg_cases.max_takeoff_weight` (decision
    G-14) -- **not** from ``database_totals``' first element, which is the sum of
    every row including full fuel *and* full payload at once and is documented as
    a ceiling, not a loading.

    ``database_totals`` names its second element ``oew``, and it is the sum of
    the ``EMPTY`` rows only: it excludes the ``minimum`` crew that operating
    empty weight includes. It is compared here against WTESTIMA's **empty
    weight** and labelled as such, which is the like-for-like pair; the mislabel
    in the summary itself is filed separately (#94).

    Rows whose entered side is absent are dropped: an estimate beside an empty
    data base is not a comparison.
    """
    from ..cg_cases import max_takeoff_weight  # local: cg_cases imports models

    if project.weight is None or project.weight.estimation is None:
        return ()
    summary = estimate(replace(project.weight.estimation,
                               max_continuous_hp=resolve_max_continuous_hp(project)))[0]

    def estimated(key: str) -> float:
        return next((float(v.value) for v in summary.values if v.key == key), 0.0)

    _, empty_entered, _ = project.weight.database_totals()
    rows = (
        EstimateVsItemized("Empty weight", estimated("empty_weight"), empty_entered),
        EstimateVsItemized("Max take-off weight", estimated("max_take_off_weight"),
                           max_takeoff_weight(project, required=False)),
    )
    return tuple(r for r in rows if r.entered_lb > 0.0)


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "weight_estimate"


_CONCEPT_NOTE = (
    "Concept mode: WTESTIMA is a GA sanity estimate only -- it is out of its "
    "<=12,500 lb calibration band. Use the itemized/direct weight "
    "(WeightInput.database_totals) as the design weight."
)


def resolve_max_continuous_hp(project: Project) -> float:
    """Combined max-continuous power for the weight estimate (Step M2-6).

    Single-sourced from the engine list -- ``sum(engines[].max_cont_hp)`` -- so the
    Weight & Mass "max continuous power (total)" field can no longer silently drift
    from the per-engine Engine Mount ratings. Uses the stored estimation total only
    when ``estimation.override_max_continuous_hp`` is set, or as the fallback when no
    engine carries a max-continuous rating (older files / no engine slice)."""
    est = project.weight.estimation if project.weight is not None else None
    if est is None:  # run() has already refused; the same refusal for direct callers
        raise MissingInputError("Project has no 'weight.estimation' inputs for the weight_estimate module")
    if est.override_max_continuous_hp:
        return est.max_continuous_hp
    engine_sum = math.fsum((e.max_cont_hp or 0.0) for e in project.engines)
    return engine_sum or est.max_continuous_hp


def run(project: Project) -> ModuleResult:
    """Run WTESTIMA against a :class:`Project`'s ``weight.estimation`` inputs.

    In concept mode the statistical estimate is flagged as a sanity-only figure (the
    summary condition's note); the core :func:`estimate` is unchanged so the FAR23
    Appendix-A oracle still holds. The max-continuous power the estimate correlates
    against is resolved from the engine list (Step M2-6, :func:`resolve_max_continuous_hp`).
    """
    if project.weight is None or project.weight.estimation is None:
        raise MissingInputError("Project has no 'weight.estimation' inputs for the weight_estimate module")
    est = replace(project.weight.estimation,
                  max_continuous_hp=resolve_max_continuous_hp(project))
    conditions = estimate(est)
    if project.is_concept and conditions:
        conditions[0].note = _CONCEPT_NOTE
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
