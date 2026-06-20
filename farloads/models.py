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


class EngineLayout(str, Enum):
    """Where the engines sit, constrained to the layouts the suite models.

    The value's leading digit is the engine count, so ``expected_count`` reads it
    directly: one engine on the fuselage nose, or a symmetric pair / two pairs of
    wing-mounted engines. Wing layouts place engines at mirror-symmetric butt
    lines (``+y``/``-y``); the nose engine sits on the centreline (``y = 0``).
    """
    SINGLE_NOSE = "1N"
    TWIN_WING = "2W"
    QUAD_WING = "4W"

    @property
    def expected_count(self) -> int:
        return int(self.value[0])

    @property
    def is_wing_mounted(self) -> bool:
        return self.value.endswith("W")


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
class WeightEnvelopeInput:
    """Structural weight/CG limits for WTENV (the discretionary-loading envelope).

    The three CG limits are percentages of MAC; WTENV turns them into fuselage
    stations via ``X = XLEMAC + (pct/100)*MAC`` using the wing geometry
    (Reference 1 Ch 3). ``gross_weight`` is the structural gross weight (the aft-
    and forward-gross limits); ``fwd_regardless_weight`` is the reduced weight at
    which the forward-regardless limit applies. ``xlemac``/``mac`` are an optional
    direct override used only when no geometry slice is present (otherwise WTENV
    reads them from the ``wing_surface`` of ``Project.geometry``).
    """
    gross_weight: float = 0.0
    aft_gross_pct_mac: float = 0.0
    fwd_gross_pct_mac: float = 0.0
    fwd_regardless_pct_mac: float = 0.0
    fwd_regardless_weight: float = 0.0
    wing_surface: str = "wing"
    xlemac: Optional[float] = None
    mac: Optional[float] = None


@dataclass
class WeightInput:
    """The single shared weight database read by every mass-properties module.

    ``estimation`` drives WTESTIMA (the statistical first cut); ``items`` is the
    explicit, itemized mass list WTONECG and WTENV sum; ``envelope`` carries the
    structural CG limits WTENV needs. The pieces are loosely coupled: WTESTIMA
    estimates totals from the mission, the itemized list carries the per-item
    stations that estimation cannot supply, and the envelope adds the limit
    definitions.
    """
    estimation: Optional[WeightEstimationInput] = None
    items: List[MassItem] = field(default_factory=list)
    envelope: Optional[WeightEnvelopeInput] = None

    def direct_totals(self) -> Tuple[float, float, float]:
        """Take-off, empty and useful weights summed directly from ``items``.

        The concept-mode "direct-weight path": instead of WTESTIMA's GA-calibrated
        statistical estimate, derive ``(MTOW, OEW, useful)`` straight from the
        itemized data base -- MTOW is every item, OEW the empty-weight items, and
        useful load the minimum + discretionary items. This is the source of truth
        for weights above WTESTIMA's calibration band. Returns ``(0, 0, 0)`` for an
        empty data base.
        """
        mtow = sum(it.weight_lb for it in self.items)
        oew = sum(it.weight_lb for it in self.items if it.kind == MassItemKind.EMPTY)
        return mtow, oew, mtow - oew


# --------------------------------------------------------------------------- #
# Aerodynamic surface geometry (WINGGEOM) -- the Project.geometry slice
# --------------------------------------------------------------------------- #
XYPoint = Tuple[float, float]  # (fuselage station X, wing/butt station Y), inches


@dataclass
class SurfaceInput:
    """One aerodynamic surface for WINGGEOM, defined by its edge polylines.

    ``leading_edge``/``trailing_edge`` are lists of ``(X, Y)`` points ordered
    inboard -> outboard (fuselage station X, butt line Y, both inches), exactly as
    the original program prompts for them. ``elements`` is the strip count the
    chord is integrated over (``H`` in WINGGEOM.BAS; the Appendix A wing uses 20).
    ``symmetric`` marks a surface symmetric about the airplane centre plane (wing,
    horizontal/vertical tail) versus one defined on a single side (aileron, flap).
    """
    name: str
    leading_edge: List[XYPoint]
    trailing_edge: List[XYPoint]
    symmetric: bool = True
    elements: int = 20


@dataclass
class GeometryInput:
    """The aerodynamic-surface geometry database read by WINGGEOM and downstream.

    ``surfaces`` is the ordered list of surfaces to evaluate (wing first by
    convention, since wing ``XLEMAC``/``MAC`` seed WTENV and STRSPEED).
    """
    surfaces: List[SurfaceInput] = field(default_factory=list)

    def by_name(self, name: str) -> Optional[SurfaceInput]:
        for s in self.surfaces:
            if s.name == name:
                return s
        return None


# --------------------------------------------------------------------------- #
# Spanwise airloads (TAU + AIRLOADS, Schrenk) -- the Project.aero slice
# --------------------------------------------------------------------------- #
@dataclass
class AeroSurfaceInput:
    """Per-surface aerodynamic inputs AIRLOADS needs on top of the WINGGEOM planform.

    AIRLOADS reads the planform (chord polylines, strip count) from the matching
    ``Project.geometry`` surface of the same ``name``; this slice carries the
    aero data that geometry does not: the section lift-curve slope ``mo``, the
    spanwise zero-lift (twist) angles that drive the basic distribution, the
    TAU lift-curve-slope correction (or the taper/tip ratios to compute it), and
    the wing ``CL`` the combined distribution is evaluated at (Reference 1 Ch 7).

    ``twist`` is a list of ``(butt line Y, zero-lift angle deg)`` points ordered
    inboard -> outboard (the "selected wing stations and their angles" of the
    original program); the section angle at each strip is linearly interpolated
    from it. Leave ``twist`` empty for an untwisted wing (basic distribution 0).
    ``tau`` overrides the computed value when given (else it is derived from
    ``taper_ratio``/``tip_ratio`` per TAU.BAS).
    """
    name: str = "wing"
    section_slope: float = 0.1075        # mo, section lift-curve slope, per degree
    taper_ratio: float = 0.0             # tip chord / centreline chord (for TAU)
    tip_ratio: float = 0.0               # rounded-tip width / semi-span (for TAU)
    tau: Optional[float] = None          # override; else computed from taper/tip ratio
    twist: List[XYPoint] = field(default_factory=list)  # (Y, zero-lift angle deg), inboard->outboard
    target_cl: float = 1.0               # wing CL the combined distribution is evaluated at


@dataclass
class AeroInput:
    """The aerodynamic-input database read by AIRLOADS (one entry per surface)."""
    surfaces: List[AeroSurfaceInput] = field(default_factory=list)

    def by_name(self, name: str) -> Optional[AeroSurfaceInput]:
        for s in self.surfaces:
            if s.name == name:
                return s
        return None


# --------------------------------------------------------------------------- #
# Structural design speeds & maneuver load factors (STRSPEED) -- Project.speeds
# --------------------------------------------------------------------------- #
@dataclass
class MachLimitInput:
    """Inputs for MACHLIM (the Mach-limit lines on the flight-limits diagram).

    ``mc``/``md`` are the cruise/dive Mach limits (from STRSPEED at the shoulder
    altitude); MACHLIM tabulates the Mach-limited equivalent airspeeds from the
    shoulder altitude up to the max operating altitude in ``increment_ft`` steps
    (Reference 1 Ch 6).
    """
    mc: float = 0.0
    md: float = 0.0
    shoulder_altitude_ft: float = 0.0
    max_operating_altitude_ft: float = 0.0
    increment_ft: float = 1000.0


@dataclass
class StructuralSpeedsInput:
    """Inputs for STRSPEED (design speeds & limit maneuver load factors).

    Speeds are knots equivalent airspeed (KEAS). ``category`` is "N" (normal/
    commuter), "U" (utility), "A" (acrobatic) or "C" (concept). The FAR23 categories
    apply the 23.337 limit-maneuver-load-factor cap; **concept ("C")** bypasses that
    GA-only cap for >12,500 lb configurations and so *requires* an explicit
    ``chosen_n`` and ``chosen_nneg`` (used verbatim, with no FAR floor). ``weight_lb``
    and the wing area drive the load factor and minimum cruise speed; the wing area
    is read from the ``Project.geometry`` wing surface when present (else
    ``wing_area_sqft``). Each ``chosen_*`` speed is verified against (and raised to)
    its FAR minimum; leave one ``None`` to take the computed minimum directly (in
    concept mode the speed minimums are out-of-band advisories).
    """
    category: str = "N"
    weight_lb: float = 0.0
    wing_area_sqft: Optional[float] = None     # else read from geometry wing
    vh_kt: float = 0.0                          # max speed at sea level (KEAS)
    stall_clean_kt: float = 0.0                 # VS, flaps retracted at design weight
    stall_flap_kt: float = 0.0                  # VSF, flaps fully extended
    shoulder_altitude_ft: float = 0.0           # for the MC/MD Mach numbers
    wing_surface: str = "wing"
    chosen_vc: Optional[float] = None
    chosen_vd: Optional[float] = None
    chosen_va: Optional[float] = None
    chosen_vf: Optional[float] = None
    chosen_n: Optional[float] = None            # chosen positive maneuver load factor
    chosen_nneg: Optional[float] = None         # chosen negative maneuver load factor
    mach_limit: Optional[MachLimitInput] = None  # MACHLIM inputs (Project.speeds.mach_limit)


# --------------------------------------------------------------------------- #
# Flight envelope & balancing tail loads (FLTLOADS) -- Project.flight_loads
# --------------------------------------------------------------------------- #
@dataclass
class AeroCoeffSet:
    """One configuration's airplane-less-tail aerodynamic coefficients.

    These are the polynomial fits FLTLOADS balances against (FLTLOADS.BAS lines
    150-220): lift ``CL = C0 + C1*a + C2*a^2 + C3*a^3 + C4*a^4`` in angle of
    attack ``a`` (deg); drag ``CD = D0 + D1*CL + ... + D4*CL^4`` in ``CL``;
    pitching moment ``CM = M0 + M1*a + ... + M4*a^4`` in ``a``. They are produced
    by the Ch 7 aerodynamic-coefficients program (airplane less tail) and entered
    here as input (AIRLOADS, Step C1, does not yet emit them). ``stall_cl`` /
    ``neg_stall_cl`` are the positive/negative section-stall limits at the
    reference Mach. ``flaps_down`` selects the flaps-extended tail CP ``XTF`` over
    the flaps-up ``XTC`` (cruise = up; landing = down).
    """
    name: str                                   # "CRUISE" | "LANDING" | "ENROUTE"
    stall_cl: float
    neg_stall_cl: float
    lift: Tuple[float, float, float, float, float]    # C0..C4 (CL vs alpha deg)
    drag: Tuple[float, float, float, float, float]    # D0..D4 (CD vs CL)
    moment: Tuple[float, float, float, float, float]  # M0..M4 (CM vs alpha deg)
    flaps_down: bool = False


@dataclass
class CgCase:
    """One weight / centre-of-gravity case balanced over the flight envelope.

    The four corners of the WTENV weight-cg envelope (FLTLOADS.BAS prompts for
    four per configuration). ``xcg``/``zcg`` are the fuselage station and waterline
    of the CG (inches). Entered explicitly for now; a later step seeds these from
    ``Project.weight.envelope``.
    """
    name: str
    weight_lb: float
    xcg: float
    zcg: float


@dataclass
class FlightLoadsInput:
    """Inputs for FLTLOADS (the V-n flight envelope + balancing tail loads).

    Geometry scalars mirror FLTLOADS.BAS line 90: ``mac`` wing MAC (in);
    ``xtc``/``xtf`` the fuselage station of the horizontal-tail centre of pressure
    flaps-up (~5% tail MAC) / flaps-down (~25% tail MAC); ``xw``/``zw`` the
    fuselage station / waterline of 25% wing MAC; ``wing_area_sqft`` the wing area
    S (ft^2). ``mn`` is the Mach at which the aero coefficients were obtained
    (usually ~0.1; line 138). The design speeds (VA/VC/VD/VF), Mach limits
    (MC/MD) and the limit load factor come from ``Project.speeds`` (STRSPEED), the
    single owner. Each ``AeroCoeffSet`` in ``configurations`` is balanced over its
    ``cg_cases`` at every altitude in ``altitudes_ft``.
    """
    mac: float = 0.0
    wing_area_sqft: float = 0.0
    xw: float = 0.0
    zw: float = 0.0
    xtc: float = 0.0
    xtf: float = 0.0
    mn: float = 0.1
    altitudes_ft: List[float] = field(default_factory=lambda: [0.0])
    configurations: List[AeroCoeffSet] = field(default_factory=list)
    cg_cases: List[CgCase] = field(default_factory=list)


@dataclass
class LoadValue:
    """A single labelled output quantity with units (for clean rendering).

    ``units`` is the Imperial display string. ``quantity`` is an optional
    dimension hint used only to disambiguate SI conversion where the unit string
    alone is ambiguous: a bare ``"lb"`` is pounds-*force* for a load (→ N) but
    pounds-*mass* for a weight (→ kg). A weight sets ``quantity="mass"``; loads
    leave it blank and convert by unit string. See :mod:`farloads.units`.
    """
    label: str
    value: float
    units: str = ""
    quantity: str = ""


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


# --------------------------------------------------------------------------- #
# Flight-envelope results (FLTLOADS) -- the Project.envelope slice
# --------------------------------------------------------------------------- #
@dataclass
class VnPoint:
    """One balanced point on the flight envelope (one row of FLTLOADS V-n data).

    The balanced-flight-load output of FLTLOADS.BAS subroutine 3900 for one
    condition, configuration, CG case and altitude: equivalent airspeed, normal
    load factor, balanced angle of attack, Glauert compressibility factor, wing
    lift coefficient, the airplane-less-tail pitching moment ``M(W+F)``, the lift
    airplane-less-tail normal to the reference ``LZW``, the balancing horizontal
    tail load ``LT`` and the drag ``DX`` (lb / lb-in).
    """
    case: int
    condition: str
    config: str
    cg: str
    altitude_ft: float
    v_eas_kt: float
    nz: float
    alpha_deg: float
    g_corr: float
    cl: float
    m_wf: float
    lzw: float
    lt: float
    dx: float


@dataclass
class TailBalanceLoad:
    """The balancing horizontal-tail load at one V-n point (FLTLOADS, Ch 8).

    ``tail_cp_station`` is the fuselage station of the tail CP used (``XTC`` flaps
    up, ``XTF`` flaps down); ``tail_load_lb`` is the load that zeroes the pitching
    moment about the CG. SELECT (C6) later refines the CP rationally.
    """
    case: int
    condition: str
    tail_load_lb: float
    tail_cp_station: float
    flaps_down: bool


@dataclass
class EnvelopeResult:
    """The persisted flight-envelope slice written by FLTLOADS (read by SELECT,
    WINGINER). ``vn`` is the full balanced-condition matrix; ``tail_balance`` is
    the balancing tail load per point. ``critical`` is reserved for SELECT (C6)."""
    vn: List[VnPoint] = field(default_factory=list)
    tail_balance: List[TailBalanceLoad] = field(default_factory=list)


# Current project-schema version. Bump when the on-disk JSON shape changes so old
# saves can be migrated (see io.load_project). v2 adds the concept certification
# category ("C") and the WeightInput direct-weight path; v3 adds the aero slice
# (AeroInput, TAU + AIRLOADS spanwise lift); v4 adds the flight-loads input slice
# (FlightLoadsInput, FLTLOADS) and the envelope result slice (EnvelopeResult) --
# all additive, so older files load unchanged via the from_dict defaults.
SCHEMA_VERSION = 4


@dataclass
class Project:
    """The single, reloadable project that carries every module's inputs.

    One ``project.json`` holds the whole airplane; each module reads the slice it
    needs and appends its results. Phase 0 added the engine slice and Phase 1 the
    ``weight`` (mass-properties) slice; geometry, speeds and loads slices are
    added in later phases.

    Multi-engine is first-class: ``engines`` is the ordered list of engine-mount
    inputs and ``engine_layout`` constrains it to a modelled layout (1 nose / 2 or
    4 wing). The ``engine`` property returns the first engine so single-engine
    call sites and the legacy ``"engine"`` JSON key keep working unchanged.
    """
    schema_version: int = SCHEMA_VERSION
    name: str = ""
    engines: List["EngineInput"] = field(default_factory=list)
    engine_layout: Optional[EngineLayout] = None
    weight: Optional[WeightInput] = None
    geometry: Optional[GeometryInput] = None
    speeds: Optional[StructuralSpeedsInput] = None
    aero: Optional[AeroInput] = None
    flight_loads: Optional[FlightLoadsInput] = None
    envelope: Optional[EnvelopeResult] = None

    def __post_init__(self) -> None:
        if self.engine_layout is not None and self.engines:
            expected = self.engine_layout.expected_count
            if len(self.engines) != expected:
                raise ValueError(
                    f"engine_layout {self.engine_layout.value} expects {expected} "
                    f"engine(s), got {len(self.engines)}"
                )

    @property
    def engine(self) -> Optional["EngineInput"]:
        """The first/primary engine (compat shim for single-engine call sites)."""
        return self.engines[0] if self.engines else None

    @property
    def is_concept(self) -> bool:
        """True when the project is in concept mode (speeds ``category == "C"``).

        The single read-point modules use to decide whether the GA-only caps and
        statistical estimates apply (e.g. STRSPEED bypasses the 23.337 cap, WTESTIMA
        flags itself as a sanity-only figure)."""
        return self.speeds is not None and self.speeds.category.upper() == "C"
