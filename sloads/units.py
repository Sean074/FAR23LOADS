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
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

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

# --------------------------------------------------------------------------- #
# Base factors for the *deliverable* dimensions (M4-20). Named, and derived from
# each other where they are dimensionally related, so a moment factor can never
# drift out of step with the force and length factors it is the product of --
# which is the invariant the sbeam deck's correctness rests on (D-19).
# --------------------------------------------------------------------------- #
LBF_TO_N = 4.4482216152605       # pound-force -> newton (exact, NIST)
IN_TO_MM = 25.4                  # inch -> millimetre (exact)
FT_TO_M = 0.3048                 # foot -> metre (exact)
PSI_TO_KPA = 6.894757            # lb/in^2 -> kilopascal

# Moments are force x length, and are computed as such rather than quoted, so
# the identity holds exactly in every unit set (see ``deliverable_units``).
LB_IN_TO_N_M = LBF_TO_N * (IN_TO_MM / 1000.0)    # lb-in -> N*m  (0.112984829...)
LB_IN_TO_N_MM = LBF_TO_N * IN_TO_MM              # lb-in -> N*mm (solver set)
FT_LB_TO_N_M = LBF_TO_N * FT_TO_M                # ft-lb -> N*m
# Pressure is force / length^2, and the solver set's length is the millimetre, so
# its stress unit is N/mm^2 = MPa -- *not* the kPa a human-readable deliverable
# uses (M4-20 step 4). Same D-19 argument as the moment: a deck in N and mm whose
# pressures are kPa is wrong by 1000x, silently.
PSI_TO_MPA = LBF_TO_N / (IN_TO_MM ** 2)          # lb/in^2 -> N/mm^2 (solver set)

# --------------------------------------------------------------------------- #
# Mass (step C2, plan 12 decision C-5) -- the one channel whose Imperial factor
# is NOT 1.0, and deliberately so.
# --------------------------------------------------------------------------- #
# A ``CONM2`` card carries **mass**, and the weight database stores **weight**
# (lb) -- so this channel's job is the division by g that every other channel
# never has to do. There is no such thing as an "Imperial identity" here,
# because the suite has no canonical mass unit to be identical to: the canonical
# quantity is a pound of *force*, and a consistent Imperial deck (lbf, in, s)
# measures mass in lbf*s^2/in. Hence the factor below, and hence this block is
# exempt from the all-1.0 rule the other dimensions follow (which is why
# ``test_imperial_is_the_all_one_identity`` enumerates its dimensions explicitly
# rather than sweeping every field).
#
# One standard gravity, expressed in each deck's length unit -- *derived*, not
# quoted twice, so ``force / (mass x length)`` comes out to the same number in
# both systems **exactly**. That equality is this channel's dimensional identity,
# the mass analogue of ``moment == force x length`` (D-19), and quoting
# 386.088 alongside 9806.65 would break it in the eighth digit for no reason.
#
# This is ISO 80000 standard gravity (9.80665 m/s^2 -> 386.0886 in/s^2), which
# differs by 1.5e-6 relative from ``constants.G`` (32.174 ft/s^2 = 386.088
# in/s^2), the rounded figure the ported calc uses. The difference is deliberate
# and confined to this channel: ``constants.G`` is oracle-bearing and must not
# move, while a CONM2 deck has no oracle and should carry the exact standard.
G_MM_S2 = 9806.65                # standard gravity in mm/s^2 (exact, ISO 80000)
G_IN_S2 = G_MM_S2 / IN_TO_MM     # ... the same gravity in in/s^2 (386.0886)

#: lb (weight) -> lbf*s^2/in (mass), the consistent Imperial deck unit ("slinch").
LB_TO_SLINCH = 1.0 / G_IN_S2
#: lb (weight) -> tonne (= N*s^2/mm), the consistent SI solver deck unit.
LB_TO_TONNE = LBF_TO_N / G_MM_S2

# Mass moment of inertia is mass x length^2, computed as such for the same
# reason moments are: the identity then holds exactly in every set. The database
# stores it as lb-in^2 (a *weight* basis, matching the item weights).
LB_IN2_TO_SLINCH_IN2 = LB_TO_SLINCH                      # lb-in^2 -> lbf*s^2*in
LB_IN2_TO_TONNE_MM2 = LB_TO_TONNE * (IN_TO_MM ** 2)      # lb-in^2 -> tonne*mm^2
# Human-channel mass: the units a weights report reads in, not a deck.
LB_TO_KG = 0.45359237                                    # lb -> kg (exact)
LB_IN2_TO_KG_M2 = LB_TO_KG * (IN_TO_MM / 1000.0) ** 2    # lb-in^2 -> kg*m^2

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
    "lb": (LBF_TO_N, "N"),                 # lbf -> N (force/load)
    "in": (IN_TO_MM, "mm"),                # in -> mm (position)
    "in^2": (6.4516e-04, "m²"),            # in^2 -> m^2 (surface area)
    "ft-lb": (FT_LB_TO_N_M, "N·m"),        # ft-lb -> N·m (moment/torque)
    "lb-in": (LB_IN_TO_N_M, "N·m"),        # lb-in -> N·m (root bending/torsion, pitching moment)
    "lb/in^2": (PSI_TO_KPA, "kPa"),        # lb/in^2 -> kPa (design pressure)
    "slug-ft^2": (1.3558179483314, "kg·m²"),  # slug-ft^2 -> kg·m^2 (inertia)
    "lb-in^2": (2.926396534292e-04, "kg·m²"),  # lb-in^2 -> kg·m^2 (inertia, mass basis)
}
# Airspeed and altitude are deliberately absent: they are aviation-standard
# (KEAS / ft) in both systems and are never converted. The calc emits them as
# ``kt(EAS)`` and ``ft``; a ``"knot"`` row lived here until M4-20 and converted
# nothing (no producer has ever emitted that string), but it would have silently
# broken the carve-out the day one did.

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
    "lbf": (LBF_TO_N, "N"),               # force
    "in": (IN_TO_MM, "mm"),               # length
    "sqft": (0.09290304, "m²"),           # area
    "ft-lb": (FT_LB_TO_N_M, "N·m"),       # moment (large)
    "lb-in": (LB_IN_TO_N_M, "N·m"),       # moment (small)
    "psi": (PSI_TO_KPA, "kPa"),           # pressure (lb/in^2)
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

    def w(v: Optional[float]) -> Optional[float]:  # weight: kg -> lb (optional field)
        return None if v is None else v / SI_PER_IMPERIAL["weight"]

    def w_(v: float) -> float:  # weight: kg -> lb (required field)
        return v / SI_PER_IMPERIAL["weight"]

    def ln(v: Optional[float]) -> Optional[float]:  # length: mm -> in (optional field)
        return None if v is None else v / SI_PER_IMPERIAL["length"]

    def ln_(v: float) -> float:  # length: mm -> in (required field)
        return v / SI_PER_IMPERIAL["length"]

    def tq(v: Optional[float]) -> Optional[float]:  # torque: N·m -> ft-lb
        return None if v is None else v / SI_PER_IMPERIAL["torque"]

    def p(v: Optional[float]) -> Optional[float]:  # power: kW -> hp
        return None if v is None else v / SI_PER_IMPERIAL["power"]

    def j(v: Optional[float]) -> Optional[float]:  # inertia: kg*m^2 -> slug-ft^2
        return None if v is None else v / SI_PER_IMPERIAL["inertia"]

    def cg(vec: Tuple[float, float, float]) -> Tuple[float, float, float]:  # length triple
        return (ln_(vec[0]), ln_(vec[1]), ln_(vec[2]))

    rotors = [
        replace(r, diameter_in=ln_(r.diameter_in), weight_lb=w_(r.weight_lb), inertia=j(r.inertia))
        for r in inp.rotors
    ]

    return replace(
        inp,
        engine_weight_lb=w_(inp.engine_weight_lb),
        prop_weight_lb=w_(inp.prop_weight_lb),
        hub_weight_lb=w(inp.hub_weight_lb),
        engine_cg=cg(inp.engine_cg),
        prop_cg=cg(inp.prop_cg),
        prop_diameter_in=ln_(inp.prop_diameter_in),
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
    "force": (LBF_TO_N, "N"),                     # lbf -> N
    "length_in": (IN_TO_MM, "mm"),                # in -> mm
    "area_sqft": (0.09290304, "m²"),              # sq ft -> m^2
    "torque": (FT_LB_TO_N_M, "N·m"),              # ft-lb -> N·m
    "moment_in": (LB_IN_TO_N_M, "N·m"),           # lb-in -> N·m
    "inertia_slugft2": (1.3558179483314, "kg·m²"),  # slug-ft^2 -> kg·m^2
    "inertia_lbin2": (2.926396534292e-04, "kg·m²"),  # lb-in^2 -> kg·m^2
    "power": (0.745699872, "kW"),                 # hp -> kW
    "pressure": (PSI_TO_KPA, "kPa"),              # lb/in^2 -> kPa
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


def _walk_convert(obj: Any, system: UnitSystem) -> Any:
    """Recursively convert every known dimensional leaf in a project JSON dict.

    Unknown numeric fields (not in :data:`_PROJECT_FIELD_KIND`) pass through
    unconverted -- safer than guessing a wrong factor for a field this table
    doesn't yet know about.
    """
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
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

    def _invert(obj: Any) -> Any:
        if isinstance(obj, dict):
            out: Dict[str, Any] = {}
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


# --------------------------------------------------------------------------- #
# Deliverable unit sets (M4-20)
# --------------------------------------------------------------------------- #
# Every deliverable is rendered in the unit system the user selected, not in the
# calc's internal Imperial (00_program_overview.md "Deliverable units follow the
# user's selection"; SUMMARY_REPORT.md 3.5). *Which* units that means depends on
# one more thing than the system: the channel the file belongs to.
#
# A human-readable deliverable reports a moment in N*m, because that is what an
# engineer reads and what the GUI already shows. A solver deck cannot: sbeam
# (NASTRAN) is only correct in a dimensionally *consistent* unit set, so a deck
# whose GRID coordinates are in mm and whose FORCE cards are in N must carry
# MOMENT cards in N*mm. Mixing the two is a silent 1000x torsion error in a file
# that parses perfectly and sizes structure wrongly (decision D-19).
#
# Both channels are the same *system*; they differ only in the moment unit, and
# every file states its own set in-band. One bundle is always one system.


class Channel(str, Enum):
    """Which kind of deliverable a unit set is for (see :func:`deliverable_units`)."""

    #: Report, load-case CSV, case index, text report, workbook -- read by people.
    HUMAN = "human"
    #: sbeam span/chordwise CSVs and FORCE/MOMENT bulk data -- read by a solver.
    SOLVER = "solver"


class Dimension(NamedTuple):
    """One dimension's conversion factor and its display label in some system."""

    factor: float
    label: str


class DeliverableUnits(NamedTuple):
    """The unit set one deliverable is written in.

    ``factor`` multiplies a canonical Imperial value to reach the target system,
    so **Imperial is the all-1.0 identity** -- a writer needs no
    ``if system == IMPERIAL`` branch anywhere, which is what makes "Imperial
    output is unchanged" structural rather than a promise.

    Airspeed and altitude are absent by design: they are aviation-standard
    (KEAS / ft) in both systems and are never converted.
    """

    system: UnitSystem
    channel: Channel
    force: Dimension
    length: Dimension
    moment: Dimension
    torque: Dimension
    pressure: Dimension
    mass: Dimension = Dimension(1.0, "lb")
    mass_inertia: Dimension = Dimension(1.0, "lb-in^2")

    @property
    def is_consistent(self) -> bool:
        """True if ``moment == force x length`` **and** ``pressure == force / length^2``.

        The invariant a solver deck rests on: every derived dimension is the
        product/quotient of the base ones, so a card cannot be off by a decimal
        power. Holds exactly for Imperial (1 x 1 = 1) and for the SOLVER set by
        construction. The HUMAN set deliberately fails it in SI (N*m and kPa
        against a mm length), which is why a deck must never be written from it.
        """
        moment_ok = abs(
            self.moment.factor - self.force.factor * self.length.factor) < 1e-12
        pressure_ok = abs(
            self.pressure.factor
            - self.force.factor / self.length.factor ** 2) < 1e-12
        return moment_ok and pressure_ok

    @property
    def gravity(self) -> float:
        """One standard gravity **in this set's own units** -- the ``GRAV`` value.

        The single owner of that number (CLAUDE.md practice 3). It is *not* the
        dimensional identity :attr:`is_mass_consistent` checks: that identity is
        ``force / (mass x length)``, which is 386.0886 in **both** systems by
        construction and is therefore g in in/s² wherever it is written. The
        acceleration a deck needs is ``force / mass`` -- 386.0886 in/s² Imperial,
        9806.65 mm/s² SI -- and the two differ by exactly ``length.factor``.

        Confusing them is invisible in Imperial (``length.factor == 1.0``) and
        25.4x low in SI, in a deck that parses cleanly: the D-19 failure class,
        found by the 2026-08-10 code review (finding C1) after shipping in the
        SI mass-check deck. Hence one owner and a drift guard, not an expression
        at the call site.

        Meaningful only for a mass-consistent set (:attr:`is_mass_consistent`);
        writers must resolve one through ``deliverable_units(system,
        Channel.SOLVER)`` before reading this.
        """
        return self.force.factor / self.mass.factor

    @property
    def is_mass_consistent(self) -> bool:
        """True if the mass pair satisfies ``F = m*a`` in this set's own units.

        The mass analogue of :attr:`is_consistent` (step C2, plan 12 decision
        C-5), and a **separate** property on purpose: the human channel carries
        readable mass (lb / kg) and deliberately fails this, exactly as it
        deliberately fails ``is_consistent`` in SI. Keeping them apart means
        adding the mass channel cannot change what any existing caller of
        ``is_consistent`` sees.

        Two identities, both exact by construction (the factors are derived, not
        quoted):

        * ``force / (mass x length) == g`` -- the same standard gravity in both
          systems, which is what makes a ``CONM2`` set accelerate to the right
          force under a ``GRAV`` card;
        * ``mass_inertia == mass x length^2``.
        """
        accel = self.force.factor / (self.mass.factor * self.length.factor)
        g_ok = abs(accel - G_IN_S2) < 1e-9 * G_IN_S2
        inertia_ok = abs(
            self.mass_inertia.factor
            - self.mass.factor * self.length.factor ** 2) < 1e-15
        return g_ok and inertia_ok


_IMPERIAL_LABELS = {
    "force": "lb", "length": "in", "moment": "lb-in",
    "torque": "ft-lb", "pressure": "lb/in^2",
}


def deliverable_units(
    system: UnitSystem, channel: Channel = Channel.HUMAN
) -> DeliverableUnits:
    """The unit set for a deliverable in ``system``, for ``channel``.

    Resolve this **once per bundle** and pass the result to every writer: that is
    what makes "one system per bundle" true by construction rather than by
    discipline, so two files in one export cannot disagree.
    """
    solver = channel == Channel.SOLVER
    if system == UnitSystem.IMPERIAL:
        one = {k: Dimension(1.0, v) for k, v in _IMPERIAL_LABELS.items()}
        # Mass is the one dimension with no Imperial identity to preserve: the
        # canonical stored quantity is a pound of *force*, so a consistent deck
        # unit is a division by g away (see LB_TO_SLINCH). The human channel
        # keeps the pound the whole suite reads in.
        mass = (Dimension(LB_TO_SLINCH, "lbf*s^2/in") if solver
                else Dimension(1.0, "lb"))
        mass_inertia = (Dimension(LB_IN2_TO_SLINCH_IN2, "lbf*s^2*in") if solver
                        else Dimension(1.0, "lb-in^2"))
        return DeliverableUnits(system=system, channel=channel,
                                mass=mass, mass_inertia=mass_inertia, **one)

    # The solver set's derived dimensions are the base ones combined, so the deck
    # is dimensionally consistent (D-19): N*mm = N x mm, MPa = N / mm^2. The human
    # set uses the units an engineering document reads in (N*m, kPa) and is
    # deliberately inconsistent against a mm length -- see ``is_consistent``.
    moment = (
        Dimension(LB_IN_TO_N_MM, "N·mm") if solver
        else Dimension(LB_IN_TO_N_M, "N·m")
    )
    pressure = (
        Dimension(PSI_TO_MPA, "MPa") if solver
        else Dimension(PSI_TO_KPA, "kPa")
    )
    mass = (Dimension(LB_TO_TONNE, "t") if solver
            else Dimension(LB_TO_KG, "kg"))
    mass_inertia = (Dimension(LB_IN2_TO_TONNE_MM2, "t·mm²") if solver
                    else Dimension(LB_IN2_TO_KG_M2, "kg·m²"))
    return DeliverableUnits(
        system=system,
        channel=channel,
        force=Dimension(LBF_TO_N, "N"),
        length=Dimension(IN_TO_MM, "mm"),
        moment=moment,
        torque=Dimension(FT_LB_TO_N_M, "N·m"),
        pressure=pressure,
        mass=mass,
        mass_inertia=mass_inertia,
    )


def unit_system_from(value: object, default: UnitSystem = UnitSystem.IMPERIAL) -> UnitSystem:
    """Parse a persisted/CLI unit-system string into a :class:`UnitSystem`.

    Anything unrecognised -- including ``None`` and ``""`` -- falls back to
    ``default`` (Imperial). A project file is not a place to raise: an unreadable
    preference must degrade to the documented default, never block the load of an
    otherwise-valid project.
    """
    if isinstance(value, UnitSystem):
        return value
    try:
        return UnitSystem(str(value).strip().lower())
    except (ValueError, AttributeError):
        return default


def system_name(system: UnitSystem) -> str:
    """The display name of a unit system, as an in-band statement spells it."""
    return "Imperial" if system == UnitSystem.IMPERIAL else "SI"


def units_statement(u: DeliverableUnits) -> str:
    """The in-band unit statement a deliverable carries, e.g. ``SI (N, mm, N·mm, MPa)``.

    Every exported file states its unit system in itself -- a header comment in a
    BDF, a header row or unit-suffixed column in a CSV, the title page and
    manifest in the report. A deliverable whose units must be inferred from the
    magnitude of its numbers is non-conforming (SUMMARY_REPORT.md 3.5).

    All four dimensions are named, pressure included: it is the dimension where a
    wrong set hides most easily (kPa vs. MPa is a silent 1000x, exactly as N*m vs.
    N*mm is -- see :meth:`DeliverableUnits.is_consistent`), and the tail/control
    solver CSVs carry a pressure column.
    """
    return (
        f"{system_name(u.system)} ({u.force.label}, {u.length.label}, "
        f"{u.moment.label}, {u.pressure.label})"
    )
