"""Data models for engine-mount load inputs and results.

These dataclasses replace the loose global variables of ENGLOADS.BAS with a
structured, validated input set and a uniform result type, keeping the
calculation layer (``modules/engine.py``) free of any I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

Vec3 = Tuple[float, float, float]


class EngineType(str, Enum):
    RECIPROCATING = "R"
    TURBOPROP = "T"


class RotorType(str, Enum):
    COMPRESSOR = "C"
    TURBINE = "T"


class RotorDirection(str, Enum):
    CLOCKWISE = "CW"          # viewed from rear of engine looking forward
    COUNTERCLOCKWISE = "CC"


class EngineWeightType(str, Enum):
    """Engine family used by WTESTIMA's installed-weight correlation (WTESTIMA.BAS
    lines 230-290): the two-letter codes of the original program."""
    RECIP_4CYCLE = "RF"
    RECIP_2CYCLE = "RT"
    TURBOCHARGED = "TC"
    TURBOPROP = "TP"
    LIQUID_COOLED = "LC"


class MassItemKind(str, Enum):
    """Where a mass item sits in the loading hierarchy of WTONECG/WTENV.

    Mirrors the data-base partition of WTONECG.BAS (empty-weight items, then
    minimum-flight-weight items, then discretionary useful-load items).
    """
    EMPTY = "empty"                  # part of the empty weight
    MINIMUM = "minimum"              # in minimum flight weight, not empty (pilot, reserve fuel)
    DISCRETIONARY = "discretionary"  # optional useful load (passengers, fuel, baggage, ballast)


@dataclass
class Rotor:
    """A turbine or compressor rotor, used for sudden-stoppage and gyro loads.

    Provide ``inertia`` directly when a measured polar moment of inertia is
    known; otherwise it is approximated as a solid disk from ``diameter_in`` and
    ``weight_lb``.
    """
    diameter_in: float          # rotor diameter, inches
    weight_lb: float            # rotor weight, lb
    max_rpm: float              # signed; clockwise (pilot's view) is positive
    rotor_type: RotorType = RotorType.TURBINE
    direction: RotorDirection = RotorDirection.CLOCKWISE
    inertia: Optional[float] = None  # measured polar inertia, slug-ft^2 (overrides geometry)


@dataclass
class EngineInput:
    """Complete input set for an engine-mount loads run.

    Field names follow the manual; turboprop-only fields are optional and only
    required when ``engine_type`` is TURBOPROP.
    """
    # Identification
    engine_designation: str = ""        # e.g. "CONTINENTAL IO-520-BB"
    prop_designation: str = ""          # e.g. "HAM STD 1803"
    engine_type: EngineType = EngineType.RECIPROCATING

    # Common inputs
    limit_load_factor: float = 0.0      # LIMNZ
    engine_weight_lb: float = 0.0       # ENGWT
    engine_cg: Vec3 = (0.0, 0.0, 0.0)   # XENG, YENG, ZENG
    prop_weight_lb: float = 0.0         # PROPWT
    prop_diameter_in: float = 0.0       # PROPDIA
    prop_inertia: Optional[float] = None  # measured propeller polar inertia, slug-ft^2 (overrides geometry)
    prop_blades: int = 0                # NOBLADES
    takeoff_rpm: float = 0.0            # TORPM
    max_cont_rpm: float = 0.0           # CONTRPM
    prop_cg: Vec3 = (0.0, 0.0, 0.0)     # XPROP, YPROP, ZPROP

    # Reciprocating-only
    takeoff_hp: Optional[float] = None      # TOHP
    max_cont_hp: Optional[float] = None     # MAXCONTHP
    cylinders: Optional[int] = None         # CYL

    # Turboprop-only
    max_engine_torque: Optional[float] = None   # ENGTORQ, ft-lb
    cruise_torque: Optional[float] = None       # CRUZTORQ, ft-lb
    hub_weight_lb: Optional[float] = None       # HUBWT
    stop_time_s: Optional[float] = None         # DT, sudden-stoppage time
    rotors: List[Rotor] = field(default_factory=list)

    @property
    def is_turboprop(self) -> bool:
        return self.engine_type == EngineType.TURBOPROP


# --------------------------------------------------------------------------- #
# Mass properties (WTESTIMA / WTONECG) -- the Project.weight slice
# --------------------------------------------------------------------------- #
@dataclass
class MassItem:
    """One row of the weight database: a component's weight and station.

    ``weight_lb`` at fuselage station ``x``, butt line ``y`` and waterline ``z``
    (all inches). ``ixx``/``iyy``/``izz`` are the item's *own* moments of inertia
    about its CG in **lb-in^2** (the units the original data base stores), added
    to the parallel-axis transfer in WTONECG; leave them 0 for a point mass.
    """
    name: str
    weight_lb: float
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    ixx: float = 0.0
    iyy: float = 0.0
    izz: float = 0.0
    kind: MassItemKind = MassItemKind.EMPTY


@dataclass
class WeightEstimationInput:
    """Mission inputs for WTESTIMA (the statistical weight estimate)."""
    airplane: str = ""
    max_continuous_hp: float = 0.0   # HP -- total of all engines
    engines: int = 1                 # NOENGS
    seats: int = 1                   # SEATS (170 lb each)
    cruise_hours: float = 0.0        # HOURS on full tanks at cruise power
    baggage_lb: float = 0.0          # BAG
    pressurized: bool = False        # P$ = "P"
    engine_weight_type: EngineWeightType = EngineWeightType.RECIP_4CYCLE


@dataclass
class WeightInput:
    """The single shared weight database read by every mass-properties module.

    ``estimation`` drives WTESTIMA (the statistical first cut); ``items`` is the
    explicit, itemized mass list WTONECG (and later WTENV) sum. The two are
    loosely coupled: WTESTIMA estimates totals from the mission, the itemized
    list carries the per-item stations that estimation cannot supply.
    """
    estimation: Optional[WeightEstimationInput] = None
    items: List[MassItem] = field(default_factory=list)


@dataclass
class LoadValue:
    """A single labelled output quantity with units (for clean rendering)."""
    label: str
    value: float
    units: str = ""


@dataclass
class ConditionResult:
    """Result of one FAR 23 load condition."""
    title: str
    far_reference: str
    values: List[LoadValue] = field(default_factory=list)
    note: str = ""


@dataclass
class ModuleResult:
    """The output of one suite module: its name plus the conditions it produced.

    Every module's ``run(project)`` returns this uniform type so the registry,
    CLI and GUI can treat all 22 programs identically.
    """
    module: str
    conditions: List[ConditionResult] = field(default_factory=list)


# Current project-schema version. Bump when the on-disk JSON shape changes so old
# saves can be migrated (see io.load_project).
SCHEMA_VERSION = 1


@dataclass
class Project:
    """The single, reloadable project that carries every module's inputs.

    One ``project.json`` holds the whole airplane; each module reads the slice it
    needs and appends its results. Phase 0 added the ``engine`` slice and Phase 1
    the ``weight`` (mass-properties) slice; geometry, speeds and loads slices are
    added in later phases.
    A list-valued multi-engine layout (Appendix B is a twin) is deferred to the
    ONENGOUT phase per the project guide.
    """
    schema_version: int = SCHEMA_VERSION
    name: str = ""
    engine: Optional[EngineInput] = None
    weight: Optional[WeightInput] = None
