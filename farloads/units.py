"""Unit-system conversion at the input/output boundary.

The calculation core (:mod:`farloads.modules.engine`) works exclusively in the
Imperial units of the original ENGLOADS.BAS, so it reproduces the FAR 23 LOADS
manual's worked examples within tolerance. To offer SI input/output without
touching that physics, this module converts:

* SI **inputs** -> Imperial, before a run (:func:`to_imperial`), and
* Imperial **results** -> SI, for display/report (:func:`convert_results`).

Imperial is the canonical internal system; SI is purely a presentation choice.
"""

from __future__ import annotations

from dataclasses import replace
from enum import Enum
from typing import List

from .models import ConditionResult, EngineInput, LoadValue


class UnitSystem(str, Enum):
    IMPERIAL = "imperial"
    SI = "si"


# --------------------------------------------------------------------------- #
# Scalar conversion factors
# --------------------------------------------------------------------------- #
# One Imperial unit equals this many SI units (multiply Imperial -> SI; divide
# SI -> Imperial). Exact NIST conversion factors.
SI_PER_IMPERIAL = {
    "weight": 0.45359237,        # lb (mass) -> kg
    "length": 25.4,              # in -> mm
    "torque": 1.3558179483314,   # ft-lb -> N*m
    "power": 0.745699872,        # hp -> kW
    "inertia": 1.3558179483314,  # slug-ft^2 -> kg*m^2
}

# Display units for each "kind", by system.
UNIT_LABELS = {
    UnitSystem.IMPERIAL: {"weight": "lb", "length": "in", "torque": "ft-lb", "power": "hp", "inertia": "slug-ft²"},
    UnitSystem.SI: {"weight": "kg", "length": "mm", "torque": "N·m", "power": "kW", "inertia": "kg·m²"},
}

# Conversion for result quantities, keyed by the Imperial ``units`` string a
# LoadValue carries. Value: (Imperial->SI factor, SI unit label). Units not
# listed (dimensionless "", "s", RPM, "deg") are system-independent and pass
# through. Note: a bare "lb" here is pounds-*force* (a load -> N); a *weight* in
# pounds-*mass* must instead set ``LoadValue.quantity = "mass"`` (see below), so
# the same "lb" label maps to kg, not N.
_RESULT_TO_SI = {
    "lb": (4.4482216152605, "N"),          # lbf -> N (force/load)
    "in": (25.4, "mm"),                    # in -> mm (position)
    "in^2": (6.4516e-04, "m²"),            # in^2 -> m^2 (surface area)
    "knot": (0.514444, "m/s"),             # knot -> m/s (airspeed)
    "ft-lb": (1.3558179483314, "N·m"),     # ft-lb -> N·m (moment/torque)
    "slug-ft^2": (1.3558179483314, "kg·m²"),  # slug-ft^2 -> kg·m^2 (inertia)
    "lb-in^2": (2.926396534292e-04, "kg·m²"),  # lb-in^2 -> kg·m^2 (inertia, mass basis)
}

# SI conversion keyed by an explicit dimension hint, used when the unit string is
# ambiguous. Currently only "mass": a weight reported in "lb" is pounds-mass and
# must convert to kg (a load in "lb" is pounds-force and converts to N via the
# table above). Takes precedence over the unit-string table.
_SI_BY_QUANTITY = {
    "mass": (0.45359237, "kg"),            # lb (mass) -> kg
}


def labels_for(system: UnitSystem) -> dict:
    """Display unit strings ({"weight": ..., "length": ...}) for a system."""
    return UNIT_LABELS[system]


def to_display(value: float, kind: str, system: UnitSystem) -> float:
    """Convert one canonical Imperial input value into the chosen system.

    Used to seed the GUI's default field values so they read sensibly in SI.
    """
    if system == UnitSystem.IMPERIAL:
        return value
    return value * SI_PER_IMPERIAL[kind]


def to_imperial_scalar(value: float, kind: str, system: UnitSystem) -> float:
    """Convert one user-entered value (in ``system``) back to Imperial."""
    if system == UnitSystem.IMPERIAL:
        return value
    return value / SI_PER_IMPERIAL[kind]


# --------------------------------------------------------------------------- #
# Whole-input conversion
# --------------------------------------------------------------------------- #
def to_imperial(inp: EngineInput, system: UnitSystem) -> EngineInput:
    """Return ``inp`` with every dimensional field converted SI -> Imperial.

    Dimensionless quantities (load factor, blade/cylinder counts), angular
    speeds (RPM) and times are system-independent and pass through unchanged.
    """
    if system == UnitSystem.IMPERIAL:
        return inp

    def w(v):  # weight: kg -> lb
        return None if v is None else v / SI_PER_IMPERIAL["weight"]

    def ln(v):  # length: mm -> in
        return None if v is None else v / SI_PER_IMPERIAL["length"]

    def tq(v):  # torque: N·m -> ft-lb
        return None if v is None else v / SI_PER_IMPERIAL["torque"]

    def p(v):  # power: kW -> hp
        return None if v is None else v / SI_PER_IMPERIAL["power"]

    def j(v):  # inertia: kg*m^2 -> slug-ft^2
        return None if v is None else v / SI_PER_IMPERIAL["inertia"]

    def cg(vec):  # length triple
        return tuple(ln(c) for c in vec)

    rotors = [
        replace(r, diameter_in=ln(r.diameter_in), weight_lb=w(r.weight_lb), inertia=j(r.inertia))
        for r in inp.rotors
    ]

    return replace(
        inp,
        engine_weight_lb=w(inp.engine_weight_lb),
        prop_weight_lb=w(inp.prop_weight_lb),
        hub_weight_lb=w(inp.hub_weight_lb),
        engine_cg=cg(inp.engine_cg),
        prop_cg=cg(inp.prop_cg),
        prop_diameter_in=ln(inp.prop_diameter_in),
        prop_inertia=j(inp.prop_inertia),
        max_engine_torque=tq(inp.max_engine_torque),
        cruise_torque=tq(inp.cruise_torque),
        takeoff_hp=p(inp.takeoff_hp),
        max_cont_hp=p(inp.max_cont_hp),
        rotors=rotors,
    )


# --------------------------------------------------------------------------- #
# Result conversion
# --------------------------------------------------------------------------- #
def _convert_value(v: LoadValue) -> LoadValue:
    # A dimension hint (currently only "mass") disambiguates an otherwise
    # ambiguous unit string and takes precedence over the unit-string table.
    conv = _SI_BY_QUANTITY.get(v.quantity) if v.quantity else None
    if conv is None:
        conv = _RESULT_TO_SI.get(v.units)
    if conv is None:
        return v
    factor, label = conv
    return replace(v, value=v.value * factor, units=label)


def convert_results(
    results: List[ConditionResult], system: UnitSystem
) -> List[ConditionResult]:
    """Convert every result quantity from Imperial into the chosen system."""
    if system == UnitSystem.IMPERIAL:
        return results
    return [replace(r, values=[_convert_value(v) for v in r.values]) for r in results]
