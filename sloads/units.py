"""Unit-system conversion at the input/output boundary.

The calculation core (:mod:`sloads.modules.engine`) works exclusively in the
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
from typing import List, Optional

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
    "area_sqft": 0.09290304,     # ft^2 -> m^2
    "inertia_lbin2": 2.926396534292e-04,  # lb-in^2 -> kg*m^2
}

# Display units for each "kind", by system. One unit per physical dimension
# (Phase G0): length -> in/mm, area -> ft²/m². ``inertia_lbin2`` is a distinct
# mass-basis inertia, not a duplicate of ``inertia``.
UNIT_LABELS = {
    UnitSystem.IMPERIAL: {
        "weight": "lb", "length": "in", "torque": "ft-lb", "power": "hp", "inertia": "slug-ft²",
        "area_sqft": "ft²", "inertia_lbin2": "lb-in²",
    },
    UnitSystem.SI: {
        "weight": "kg", "length": "mm", "torque": "N·m", "power": "kW", "inertia": "kg·m²",
        "area_sqft": "m²", "inertia_lbin2": "kg·m²",
    },
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


# --------------------------------------------------------------------------- #
# Scalar display converters for values *outside* LoadValue/ConditionResult --
# some modules (aileron/flap/tab, body_loads, net_loads, landing, taildist,
# one_engine_out) return small typed dataclasses (per-station/per-case) rather
# than LoadValue lists, so their GUI pages convert individual fields for
# display. These always convert Imperial -> the target system (one-way; the
# dataclass itself, which also feeds sbeam export and session-state
# persistence, is never touched -- only a display copy).
_SCALAR_TO_SI = {
    "lbf": (4.4482216152605, "N"),        # force
    "in": (25.4, "mm"),                   # length
    "sqft": (0.09290304, "m²"),           # area
    "ft-lb": (1.3558179483314, "N·m"),    # moment (large)
    "lb-in": (0.1129848333, "N·m"),       # moment (small)
    "psi": (6.894757, "kPa"),             # pressure (lb/in^2)
}


def to_si_scalar(value: float, unit: str, system: UnitSystem) -> float:
    """Convert one display value from its Imperial ``unit`` into ``system``.

    ``unit`` is one of :data:`_SCALAR_TO_SI`'s keys. Imperial is a no-op.
    """
    if system == UnitSystem.IMPERIAL or value is None or value == "":
        return value
    factor, _ = _SCALAR_TO_SI[unit]
    return value * factor


def si_scalar_label(unit: str, system: UnitSystem) -> str:
    """The display unit string for ``unit`` in ``system`` (Imperial passes through)."""
    if system == UnitSystem.IMPERIAL:
        return unit
    return _SCALAR_TO_SI[unit][1]


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
        max_accel_torque=tq(inp.max_accel_torque),
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


# --------------------------------------------------------------------------- #
# Whole-project display conversion (Project JSON Editor page, app/views/
# project_editor.py). Converts the *JSON dict* form of a Project (see
# sloads.io.project_to_dict) field-by-field, for display/hand-editing only.
# The canonical project.json on disk is always Imperial (io.py never calls
# this); the editor page converts SI -> Imperial before writing back via
# io.project_from_dict, so calc/tests/oracle fixtures are unaffected.
# --------------------------------------------------------------------------- #
# Kind -> (Imperial -> SI factor, SI label). Derived from an audit of every
# dimensional field in sloads/models.py; update both this table and
# _PROJECT_FIELD_KIND when a new dimensional field is added to the schema.
_KIND_FACTORS = {
    "mass": (0.45359237, "kg"),                  # lbm -> kg
    "force": (4.4482216152605, "N"),              # lbf -> N
    "length_in": (25.4, "mm"),                    # in -> mm
    "area_sqft": (0.09290304, "m²"),              # sq ft -> m^2
    "torque": (1.3558179483314, "N·m"),           # ft-lb -> N·m
    "moment_in": (0.1129848333, "N·m"),           # lb-in -> N·m
    "inertia_slugft2": (1.3558179483314, "kg·m²"),  # slug-ft^2 -> kg·m^2
    "inertia_lbin2": (2.926396534292e-04, "kg·m²"),  # lb-in^2 -> kg·m^2
    "power": (0.745699872, "kW"),                 # hp -> kW
    "pressure": (6.894757, "kPa"),                # lb/in^2 -> kPa
}

# JSON leaf key name -> kind. Airspeed (``_kt``) and altitude (``altitude_ft``,
# ``altitudes_ft``, ``max_operating_altitude_ft``, ``shoulder_altitude_ft``,
# ``increment_ft``) are deliberately absent -- they stay aviation-standard
# (KEAS / ft) in both systems, matching every other unit toggle in the GUI.
# Angles (``_deg``), dimensionless ratios/coefficients and counts are also
# absent (nothing to convert). ``load_lb``/``tail_load_lb`` are the two
# ``_lb``-suffixed fields that are *forces*, not weights -- everything else
# ending ``_lb`` is a pounds-mass weight.
_PROJECT_FIELD_KIND = {
    # mass (lb -> kg)
    "baggage_lb": "mass", "engine_weight_lb": "mass", "gross_weight_lb": "mass",
    "hub_weight_lb": "mass", "max_landing_weight_lb": "mass", "panel_weight_lb": "mass",
    "prop_weight_lb": "mass", "weight_lb": "mass", "wing_weight_lb": "mass",
    # force (lb -> N)
    "load_lb": "force", "tail_load_lb": "force",
    "fx": "force", "fy": "force", "fz": "force", "sx": "force", "sy": "force", "sz": "force",
    # length, inches (in -> mm) -- includes unsuffixed station/CG coordinates,
    # all documented as inches in models.py
    "airfoil_chord_in": "length_in", "diameter_in": "length_in",
    "engine_butt_line_in": "length_in", "htail_semispan_in": "length_in",
    "hub_diameter_in": "length_in", "mac_in": "length_in", "prop_diameter_in": "length_in",
    "rolling_radius_in": "length_in", "station_in": "length_in", "strut_stroke_in": "length_in",
    "tire_od_in": "length_in", "tread_in": "length_in", "vtail_span_in": "length_in",
    "xcg_in": "length_in", "x": "length_in", "y": "length_in", "z": "length_in",
    "cg_x": "length_in", "cg_y": "length_in", "cg_z": "length_in",
    "xcg": "length_in", "zcg": "length_in",
    # geometry lengths formerly stored in feet, now canonical inches (Phase G0)
    "airplane_length_in": "length_in", "vtail_mac_in": "length_in", "wing_span_in": "length_in",
    "h_tail_span_in": "length_in", "v_tail_span_in": "length_in",
    # area (sq ft -> m^2); the tab area (bare ``area_sqft``) was formerly in^2 (G0)
    "area_aft_hinge_sqft": "area_sqft", "area_fwd_hinge_sqft": "area_sqft",
    "elevator_aft_hinge_sqft": "area_sqft", "elevator_area_sqft": "area_sqft",
    "elevator_fwd_hinge_sqft": "area_sqft", "flap_area_one_side_sqft": "area_sqft",
    "htail_area_sqft": "area_sqft", "nacelle_frontal_area_sqft": "area_sqft",
    "rudder_aft_hinge_sqft": "area_sqft", "rudder_area_sqft": "area_sqft",
    "rudder_fwd_hinge_sqft": "area_sqft", "vtail_area_sqft": "area_sqft",
    "wing_area_sqft": "area_sqft", "area_sqft": "area_sqft",
    # torque (ft-lb -> N·m)
    "max_engine_torque": "torque", "cruise_torque": "torque", "max_accel_torque": "torque",
    # moment (lb-in -> N·m)
    "mxx": "moment_in", "myy": "moment_in", "mzz": "moment_in",
    # inertia
    "inertia": "inertia_slugft2", "prop_inertia": "inertia_slugft2",
    "ixx": "inertia_lbin2", "iyy": "inertia_lbin2", "izz": "inertia_lbin2", "ixz": "inertia_lbin2",
    # power (hp -> kW)
    "takeoff_hp": "power", "max_cont_hp": "power", "max_continuous_hp": "power",
    # pressure (lb/in^2 -> kPa)
    "psi": "pressure",
}

# Fields whose JSON value is a bare ``[x, y, z]`` array of inch coordinates
# rather than a keyed dict (see io.py's ``engine_to_dict``/``engine_from_dict``).
_VEC3_LENGTH_IN_FIELDS = {"engine_cg", "prop_cg"}


def _walk_convert(obj, system: UnitSystem):
    """Recursively convert every known dimensional leaf in a project JSON dict.

    Unknown numeric fields (not in :data:`_PROJECT_FIELD_KIND`) pass through
    unconverted -- safer than guessing a wrong factor for a field this table
    doesn't yet know about.
    """
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if key in _VEC3_LENGTH_IN_FIELDS and isinstance(value, list):
                factor = _KIND_FACTORS["length_in"][0]
                out[key] = [v * factor if isinstance(v, (int, float)) else v for v in value]
                continue
            kind = _PROJECT_FIELD_KIND.get(key)
            if kind is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
                out[key] = value * _KIND_FACTORS[kind][0]
            else:
                out[key] = _walk_convert(value, system)
        return out
    if isinstance(obj, list):
        return [_walk_convert(item, system) for item in obj]
    return obj


def project_dict_to_display(project_dict: dict, system: UnitSystem) -> dict:
    """Convert a ``project_to_dict`` result from Imperial into ``system`` for display.

    One-way (Imperial -> display). Airspeed and altitude fields are left
    Imperial/aviation-standard regardless of ``system`` (see module docstring).
    """
    if system == UnitSystem.IMPERIAL:
        return project_dict
    return _walk_convert(project_dict, system)


def project_dict_to_imperial(display_dict: dict, system: UnitSystem) -> dict:
    """Convert a (possibly hand-edited) display dict from ``system`` back to
    Imperial, the inverse of :func:`project_dict_to_display`."""
    if system == UnitSystem.IMPERIAL:
        return display_dict

    def _invert(obj):
        if isinstance(obj, dict):
            out = {}
            for key, value in obj.items():
                if key in _VEC3_LENGTH_IN_FIELDS and isinstance(value, list):
                    factor = _KIND_FACTORS["length_in"][0]
                    out[key] = [v / factor if isinstance(v, (int, float)) else v for v in value]
                    continue
                kind = _PROJECT_FIELD_KIND.get(key)
                if kind is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
                    out[key] = value / _KIND_FACTORS[kind][0]
                else:
                    out[key] = _invert(value)
            return out
        if isinstance(obj, list):
            return [_invert(item) for item in obj]
        return obj

    return _invert(display_dict)


def project_field_si_label(key: str) -> Optional[str]:
    """The SI display label for a known project-schema field name, else ``None``."""
    kind = _PROJECT_FIELD_KIND.get(key)
    return _KIND_FACTORS[kind][1] if kind else None
