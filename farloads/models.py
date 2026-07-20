"""Data models for engine-mount load inputs and results.

These dataclasses replace the loose global variables of ENGLOADS.BAS with a
structured, validated input set and a uniform result type, keeping the
calculation layer (``modules/engine.py``) free of any I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .constants import ULTIMATE_FACTOR

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
    # FAR 25-only (optional concept-mode superset; see Project.include_far25)
    max_accel_torque: Optional[float] = None    # FAR 25.361(a)(3)(ii) max accelerating torque, ft-lb
                                                # (blank -> falls back to max_engine_torque)
    # Concept-mode advisory rates: the concept's real 25.371 body pitch/yaw rates,
    # if known. Used ONLY to guard condition_25_371's fixed FAR 23.371(b) stand-in
    # (2.5 rad/s yaw, 1 rad/s pitch): when either declared rate exceeds the stand-in
    # the gyro moment (linear in body rate) is non-conservative, so the result
    # carries an under-prediction warning. Advisory only -- they do NOT change the
    # computed moment (D-2: keep the fixed stand-in, guard + warn, no rate-derivation
    # math). Blank -> no guard, fixed stand-in unchanged.
    design_yaw_rate_rad_s: Optional[float] = None    # concept real yaw rate (25.371)
    design_pitch_rate_rad_s: Optional[float] = None  # concept real pitch rate (25.371)

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
    seats: int = 1                   # SEATS (170 lb each) -- total occupant seats
    crew: int = 1                    # flight crew (170 lb each); part of the operating
                                     # empty weight (OEW = empty + crew*170), not payload.
                                     # Also the required-crew count the FAR 23 seat-limit
                                     # check subtracts (passenger seats = occupants - crew).
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

    ``cg_cases`` (Step D5) is the shared list of named loading scenarios --
    weight + CG points entered once on the Weight/CG Grid & Payload Cases page,
    overlaid on the ``weight_envelope`` chart and merged into
    ``FlightLoadsInput.cg_cases`` by the Flight Envelope page, so the two can no
    longer diverge (the calc modules that balance/select over CG cases keep
    reading ``FlightLoadsInput.cg_cases`` unchanged).
    """
    estimation: Optional[WeightEstimationInput] = None
    items: List[MassItem] = field(default_factory=list)
    envelope: Optional[WeightEnvelopeInput] = None
    cg_cases: List["CgCase"] = field(default_factory=list)

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
class FuselageSection:
    """One fuselage cross-section station for the body outline (Step G1).

    ``x`` is the fuselage station (in); ``width``/``height`` the maximum body
    width and height (in) at that station. The cross-sectional area used by the
    G4 slender-body pitching-moment estimator is derived as an ellipse
    (``pi/4 * width * height``) -- the sections are the station-area table that
    both the three-view body profile and that estimator read.
    """
    x: float
    width: float
    height: float


@dataclass
class FuselageOutline:
    """The fuselage body outline: cross-sections ordered nose -> tail (Step G1).

    A station-area table (:class:`FuselageSection` list) that gives both the
    three-view body profile and the cross-sectional-area distribution the G4
    fuselage pitching-moment estimator consumes. For older projects (which carry
    only the ``fuselage_length``/``_width``/``_height`` scalars on the parametric
    slice) it is defaulted from those scalars by
    :func:`default_fuselage_outline` when the project loads.
    """
    sections: List[FuselageSection] = field(default_factory=list)


@dataclass
class GeometryInput:
    """The single geometry source of truth (Step G1): parametric layout, the
    WINGGEOM lifting-surface planforms, and the fuselage outline.

    Unifies what used to be two slices -- ``Project.configuration`` (the
    parametric ``LayoutInput``) and ``Project.geometry`` (the surface planforms)
    -- into one, so geometry is owned and edited on exactly one page and every
    downstream page reads it read-only.

    ``surfaces`` is the ordered list of lifting surfaces to evaluate (wing first
    by convention, since wing ``XLEMAC``/``MAC`` seed WTENV and STRSPEED); the
    oracle-locked calc (AIRLOADS, WINGINER, NETLOADS, ...) reads it unchanged via
    :meth:`by_name`/``surfaces``. ``parametric`` is the parametric fuselage/wing/
    tail/gear geometry the Geometry page edits and then *seeds* into ``surfaces``
    (WINGGEOM polylines) and downstream (WTENV/STRSPEED ``XLEMAC``/``MAC``).
    ``fuselage`` is the body outline (station-area table) for the three-view and
    the G4 moment estimator. ``empennage`` (Step G6) is the single-source horizontal-
    /vertical-tail + elevator/rudder geometry the three-view draws and the rational
    tail-load analysis consumes (``Project.tail_loads``/``.vtail_loads`` proxy to it).
    """
    surfaces: List[SurfaceInput] = field(default_factory=list)
    parametric: Optional["LayoutInput"] = None
    fuselage: Optional[FuselageOutline] = None
    empennage: Optional["EmpennageInput"] = None
    landing_gear: Optional["LandingGearGeometry"] = None

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
    # Section coefficient tables for the air-load distribution (AIRLOADS load
    # option, Step C3). ``profile_drag`` is the section profile-drag coefficient
    # CDO at selected butt lines (AIRLOADS.BAS line 2770; the induced drag is
    # computed from the lift distribution and added). ``section_cm`` is the
    # section pitching-moment coefficient at selected butt lines (line 2960). Both
    # are ``(Y, coeff)`` points inboard->outboard, linearly interpolated; leave
    # empty for the C1 span-load-only path.
    profile_drag: List[XYPoint] = field(default_factory=list)   # (Y, CDO)
    section_cm: List[XYPoint] = field(default_factory=list)      # (Y, CM)
    # Swept / high-Mach branch (AIRLOAD4.BAS, Step C7). ``sweep_deg`` is the 25%-
    # chord sweepback (deg; negative = sweptforward) and ``design_mach`` the Mach
    # at which airloads are wanted. AIRLOAD4's sweep redistribution of the additive
    # Schrenk distribution is auto-selected when ``|sweep_deg| > 15`` or
    # ``design_mach > 0.4`` (Ref 1 Ch 12); both default to 0 (the low-speed
    # AIRLOADS path, unchanged).
    sweep_deg: float = 0.0
    design_mach: float = 0.0


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
    occupants: Optional[int] = None            # total souls on board; the FAR 23 seat-limit
                                               # check counts passenger seats = occupants - crew.
                                               # None -> seeded from Project.weight.seats by
                                               # farloads.applicability.effective_occupants
    wing_area_sqft: Optional[float] = None     # else read from geometry wing
    vh_kt: float = 0.0                          # max speed at sea level (KEAS)
    # Stall speeds VS/VSF are DERIVED from the maximum lift coefficients that live
    # on Project.aero_coeffs (clmax_clean/clmax_flap): VS = sqrt(295*(W/S)/CLmax)
    # at the design weight (User's Guide p7-5). CLmax is entered once, on the
    # Aerodynamic Data page; STRSPEED reads it (M1-1b). No stall-speed scalar here.
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
    lift: Tuple[float, float, float, float, float]    # C0..C4 (CL vs alpha deg)
    drag: Tuple[float, float, float, float, float]    # D0..D4 (CD vs CL)
    moment: Tuple[float, float, float, float, float]  # M0..M4 (CM vs alpha deg)
    # stall_cl/neg_stall_cl are DERIVED read-throughs of the parent
    # AeroCoefficientsInput's clmax_clean/clmax_clean_neg (cruise) or clmax_flap
    # (flaps_down); AeroCoefficientsInput.__post_init__ keeps them consistent.
    # FLTLOADS reads these; they are not authored per-config (M1-1b single-source).
    stall_cl: float = 0.0
    neg_stall_cl: float = 0.0
    flaps_down: bool = False


@dataclass
class FuselageMomentInput:
    """Munk slender-body fuselage pitching-moment increment (Step G4).

    An off-by-default augmentation of the airplane-less-tail moment slope: when
    ``enabled`` the FLTLOADS balance adds ``d_cm_dalpha`` (per degree) to every
    configuration's ``M1`` (dCm/dalpha), so a concept airplane built from a
    planform can pick up its fuselage pitching moment from the G1 outline instead
    of the user hand-folding it into the input coefficients. ``d_cm_dalpha`` is
    the Munk estimate (``farloads.fuselage_moment.estimate``) and is overridable.

    Default ``enabled=False`` / ``0.0`` contributes nothing, so the Appendix A/B
    oracles (whose coefficients already include the fuselage) are untouched.
    """
    enabled: bool = False
    d_cm_dalpha: float = 0.0    # per degree; added to the airplane-less-tail M1


@dataclass
class AeroCoefficientsInput:
    """Airplane-less-tail aerodynamic coefficient sets -- ``Project.aero_coeffs``.

    The single owner of the Ch 7 aero-coefficients program's output (cruise and,
    optionally, flaps-down): the Airplane-section **Aero Coefficients** page
    writes this slice; ``flight_envelope`` (FLTLOADS) reads it read-only rather
    than asking for coefficients itself (Phase D, Step D4.1). ``cruise`` is the
    flaps-up set balanced at every altitude in ``FlightLoadsInput.altitudes_ft``;
    ``flaps_down`` (when present) is balanced at sea level only per FLTLOADS.BAS
    line 3000 -- see ``flight_envelope.build_envelope``. ``fuselage_moment`` is
    the optional off-by-default Munk fuselage dCm/dalpha increment (Step G4),
    added to both configs' ``M1`` when enabled.
    """
    cruise: Optional[AeroCoeffSet] = None
    flaps_down: Optional[AeroCoeffSet] = None
    fuselage_moment: Optional[FuselageMomentInput] = None
    # Maximum lift coefficients -- the single authored source for stall (M1-1b).
    # clmax_clean/clmax_clean_neg = clean (cruise) positive/negative CLmax;
    # clmax_flap = flaps-down positive CLmax. STRSPEED/flap/one_engine_out derive
    # VS/VSF from these; FLTLOADS reads the mirrored per-config stall_cl. Kept
    # decoupled from the polynomial sets so an airplane with stall data but no
    # balance polynomials (e.g. a GA single with no flaps-down set) still carries
    # its CLmax. __post_init__ keeps clmax_* and the config stall_cl consistent.
    clmax_clean: float = 0.0
    clmax_clean_neg: float = 0.0
    clmax_flap: float = 0.0

    def __post_init__(self) -> None:
        # Keep the two stall representations consistent without ever overwriting an
        # explicitly-authored value (fill-if-missing, both directions). The top-level
        # clmax_* feed the *stall speed* VS/VSF (STRSPEED); the per-config stall_cl is
        # the FLTLOADS balance clamp. They usually coincide, but the manual enters
        # them independently and they can differ slightly (e.g. Appendix A ga6:
        # clmax_clean 1.4068 from the printed VS vs FLTLOADS stall_cl 1.41 -- the 0.9
        # stall-margin factor). So each is preserved when set; a missing one is filled
        # from the other so a project needs only provide whichever it has.
        if not self.clmax_clean and self.cruise is not None and self.cruise.stall_cl:
            self.clmax_clean = self.cruise.stall_cl
            self.clmax_clean_neg = self.cruise.neg_stall_cl
        if not self.clmax_flap and self.flaps_down is not None and self.flaps_down.stall_cl:
            self.clmax_flap = self.flaps_down.stall_cl
        if self.cruise is not None and not self.cruise.stall_cl and self.clmax_clean:
            self.cruise.stall_cl = self.clmax_clean
            self.cruise.neg_stall_cl = self.clmax_clean_neg
        if self.flaps_down is not None and not self.flaps_down.stall_cl and self.clmax_flap:
            self.flaps_down.stall_cl = self.clmax_flap


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
    (MC/MD) and the limit load factor come from ``Project.speeds`` (STRSPEED);
    the airplane-less-tail coefficient sets come from ``Project.aero_coeffs``
    (Step D4.1 -- previously carried here as ``configurations``). Each set is
    balanced over ``cg_cases`` at every altitude in ``altitudes_ft``.
    """
    mac: float = 0.0
    wing_area_sqft: float = 0.0
    xw: float = 0.0
    zw: float = 0.0
    xtc: float = 0.0
    xtf: float = 0.0
    mn: float = 0.1
    altitudes_ft: List[float] = field(default_factory=lambda: [0.0])
    cg_cases: List[CgCase] = field(default_factory=list)

    def merged(self, *, mac: float, wing_area_sqft: float, xw: float, zw: float,
               xtc: float, xtf: float, mn: float, altitudes_ft: List[float],
               cg_cases: List[CgCase]) -> "FlightLoadsInput":
        """One page-edit merged into this slice.

        Step D5 exposes ``altitudes_ft`` as a real, fully-editable list on the
        Flight Envelope page (multi-altitude V-n), and ``cg_cases`` is now read
        from the shared ``WeightInput.cg_cases`` the Weight/CG Grid page owns
        rather than edited here -- so every field the page can show is edited (or
        passed through) in full on every Apply; there is no partial/"preserve
        what wasn't shown" state left to merge.
        """
        return FlightLoadsInput(
            mac=mac, wing_area_sqft=wing_area_sqft, xw=xw, zw=zw, xtc=xtc,
            xtf=xtf, mn=mn, altitudes_ft=list(altitudes_ft), cg_cases=list(cg_cases),
        )


# --------------------------------------------------------------------------- #
# Wing inertia loads (WINGINER) -- the Project.wing_mass slice
# --------------------------------------------------------------------------- #
@dataclass
class ConcentratedWeight:
    """A concentrated wing mass item (gear, engine, fuel tank, store).

    ``weight_lb`` at fuselage station ``x``, butt line ``y`` and waterline ``z``
    (inches). WINGINER adds it as a spanwise step in shear/moment/torsion
    (WINGINER.BAS lines 580-593, 1180-1610)."""
    name: str
    weight_lb: float
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class WingLoadCase:
    """One critical wing condition WINGINER/NETLOADS evaluate (WINGINER.BAS 1660-1710).

    ``case`` references a :class:`VnPoint` in ``Project.envelope.vn``; ``nz``/``nx``
    (= ``-DX/W`` inertia drag factor) and the air-load ``cl``/``v_eas_kt`` default
    from that point when not given explicitly. ``unbal_moment`` is the unbalanced
    rolling moment (in-lb) for an accelerated-roll case (FAR 23.349; zero
    otherwise). This is the C3-before-SELECT bridge: the critical conditions come
    straight from the FLTLOADS V-n matrix (C2) since SELECT (C6) is not built yet.
    """
    name: str                              # "PHAA" / "ACRL" / "TORS" / ...
    case: Optional[int] = None
    nz: Optional[float] = None
    nx: Optional[float] = None
    unbal_moment: float = 0.0
    cl: Optional[float] = None
    v_eas_kt: Optional[float] = None


@dataclass
class WingMassInput:
    """Inputs for WINGINER (the spanwise wing-mass distribution + load cases).

    The outboard wing panel mass is modelled as an area density that tapers
    linearly from root to tip: WINGINER iterates the root density until the
    integrated panel mass equals ``panel_weight_lb`` (WINGINER.BAS lines 690-880).
    ``tip_root_density_ratio`` (DR) is the tip/root area-density ratio;
    ``inboard_rib_y`` (RSTA) the butt line where the panel begins; ``wrp_waterline``
    the waterline of the wing reference plane (25% chord) at the centreline and
    ``dihedral_deg`` its slope. ``concentrated`` carries discrete wing masses.
    ``cases`` is the set of critical conditions to combine (vertical + drag +
    rolling inertia). The planform is read from the matching ``Project.geometry``
    surface (``surface``).
    """
    panel_weight_lb: float = 0.0
    tip_root_density_ratio: float = 1.0
    inboard_rib_y: float = 0.0
    wrp_waterline: float = 0.0
    dihedral_deg: float = 0.0
    surface: str = "wing"
    concentrated: List[ConcentratedWeight] = field(default_factory=list)
    cases: List[WingLoadCase] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Fuselage mass distribution (SELECT / fuselage net loads) -- Project.fuselage_mass
# --------------------------------------------------------------------------- #
@dataclass
class FuselageStation:
    """One longitudinal fuselage reference station for the net-load integration.

    ``x`` is the fuselage station (in); ``weight_lb`` the lumped mass carried at
    that station (structure + fixed equipment + the payload apportioned to the
    body). The body inertia distribution for the fuselage net loads is built from
    these stations.
    """
    x: float
    weight_lb: float = 0.0


@dataclass
class FuselageMassInput:
    """Inputs for the fuselage net-load distribution (SELECT / Ref 1 Ch 15).

    The fuselage longitudinal mass distribution (``stations``, nose-to-tail) carried
    along the body axis at waterline ``ref_waterline``. The applied external loads
    (balancing tail load, wing reaction, gear) are taken from ``Project.envelope``
    and ``Project.configuration``/``geometry`` at integration time, not stored here.
    A modern default (lumped per-station masses) with no manual precedent, fully
    user-overridable -- mirrors the C3 ``WingMassInput`` modelling note (a documented
    default that the user can override).
    """
    stations: List[FuselageStation] = field(default_factory=list)
    ref_waterline: float = 0.0


# --------------------------------------------------------------------------- #
# Critical-load selection inputs (SELECT) -- Project.select_input
# --------------------------------------------------------------------------- #
@dataclass
class SelectInput:
    """Inputs for SELECT's critical-load search (Ch 9) beyond the V-n matrix.

    The wing steady-roll torsion condition (FAR 23.349(b)) scores the aileron-
    induced wing torsion ``(cm - 0.01*aileron_deg)*G*V^2`` (SELECT.BAS 3440-3460),
    so it needs ``full_down_aileron_deg`` (the full-down aileron deflection, DN)
    and ``basic_airfoil_cm`` (the section pitching-moment coefficient with no
    aileron deflection). The rational horizontal/vertical-tail and fuselage search
    inputs (tail incidence, elevator/rudder geometry, effectiveness) are added with
    those components in a later C6 increment.
    """
    full_down_aileron_deg: float = 0.0
    basic_airfoil_cm: float = 0.0
    # Critical fuselage-condition search (Ch 9): the wing weight WW reacted at the
    # wing (the fuselage load on the wing is LZW - NZ*WW). 0 -> default 0.09*MTOW.
    wing_weight_lb: float = 0.0


# --------------------------------------------------------------------------- #
# Rational horizontal-tail load inputs (SELECT) -- Project.tail_loads
# --------------------------------------------------------------------------- #
@dataclass
class TailLoadsInput:
    """Geometry/aero inputs for SELECT's rational horizontal-tail loads (Ch 9).

    The rational balancing tail load resolves the total balanced load into the
    angle-of-attack load at 25% tail MAC and the camber (elevator) load at 50%
    (the BALLOADS method): tail angle of attack ``AT = alpha_wl + IT - E`` with
    downwash ``E = 114.6*CL/(pi*ARW)`` (Perkins & Hage Eq 5-23), tail lift slope
    ``AHT = 2*pi/(1 + 2/ARHT)``, ``LT25 = (AT*AHT/57.3)*Q*ST``, then the elevator
    deflection and camber load ``LT50`` from balancing the pitching moment about
    the CG; the total balanced tail load is ``LT = LT25 + LT50``.

    Fields mirror the manual's "General input for calculation of horiz tail loads":
    tail incidence ``IT`` (WL to chord), the wing zero-lift-line angle per
    configuration (``IW``: cruise / enroute / landing), the wing & tail aspect
    ratios, tail area ``ST``, the elevator effectiveness (the deflection lift as a
    fraction of ``AHT``), and the fuselage stations of 25% / 50% tail MAC. ``XW``/
    ``ZW`` (25% wing MAC) and the per-CG ``XCG``/``ZCG`` come from
    ``Project.flight_loads``. The horizontal-tail maneuver/gust/unsymmetrical, the
    flaps-extended balancing (which needs the flapped V-n envelope), the vertical
    tail and the fuselage net loads are later C6 increments.
    """
    tail_incidence_deg: float = 0.0            # IT (WL to tail chord)
    wing_zero_lift_cruise_deg: float = 0.0     # IW, cruise config
    wing_zero_lift_enroute_deg: float = 0.0    # IW, enroute config
    wing_zero_lift_landing_deg: float = 0.0    # IW, landing config
    aspect_ratio_wing: float = 0.0             # ARW (downwash)
    aspect_ratio_htail: float = 0.0            # ARHT (tail lift slope)
    htail_area_sqft: float = 0.0               # ST
    elevator_effectiveness: float = 0.0        # dalpha/ddelta_e as a fraction of AHT
    xt25: float = 0.0                          # fuselage station of 25% tail MAC
    xt50: float = 0.0                          # fuselage station of 50% tail MAC
    # Maneuver / gust (FAR 23.423 / 23.425) -- elevator geometry, airplane length
    # (for the approximate pitch inertia) and the wing lift slope (for the gust
    # downwash relief). Used by the unchecked/checked-maneuver and gust searches.
    elevator_te_up_deg: float = 0.0            # EUP (full trailing-edge-up)
    elevator_te_down_deg: float = 0.0          # EDN (full trailing-edge-down)
    elevator_area_sqft: float = 0.0            # SE (total elevator area)
    elevator_fwd_hinge_sqft: float = 0.0       # SEFWDHL
    elevator_aft_hinge_sqft: float = 0.0       # SEAFTHL
    airplane_length_in: float = 0.0            # LF (inches; Iyy uses LF_ft = LF_in/12)
    wing_lift_slope_per_rad: float = 0.0       # AW (gust downwash relief 1 - 36*aw/ARW)
    # Chordwise distribution (TAILDIST, Ch 10) -- the horizontal-tail semi-span
    # (BLHTAIL, inches) sets the average tail chord CAVE = S/B for the chordwise
    # profile. The elevator areas above (full both-sides, sq ft) supply the hinge-
    # line chord station; 0 disables the chordwise distribution for this surface.
    htail_semispan_in: float = 0.0             # BLHTAIL (tail semi-span, inches)


# --------------------------------------------------------------------------- #
# Rational vertical-tail load inputs (SELECT) -- Project.vtail_loads
# --------------------------------------------------------------------------- #
@dataclass
class VTailLoadsInput:
    """Geometry/aero inputs for SELECT's rational vertical-tail loads (Ch 9).

    The vertical-tail side loads (FAR 23.441 maneuver / 23.443 gust) are computed at
    the V-n ``BAL A`` (VA) and ``BAL C`` (VC) points with the tail lift slope
    ``AVT = 2*pi/(1 + 2/ARVT)`` and the rudder effectiveness ``EFFECTV`` (a cubic in
    the rudder/tail area ratio ``SR/SV``; SELECT.BAS):

      * sudden full rudder      ``LV = RD*EFV*EFFECTV*AVT/57.3 * V^2/295 * SV``
      * yaw to sideslip 19.5deg ``LV + (-19.5*AVT/57.3 * V^2/295 * SV)``
      * yaw 15deg rudder neutral ``-15*AVT/57.3 * V^2/295 * SV``
      * side gust at VC          ``KGT*UDE*V*AVT*SV/498`` with the gust mass ratio
                                 ``UGT = 2W/(rho*VMAC*g*AVT*SV*(K/LXVT)^2)``,
                                 ``KGT = .88*UGT/(5.3+UGT)``, radius of gyration
                                 ``K = sqrt(IZZ/(W/g))`` and tail arm
                                 ``LXVT = (XV25 - XCG)/12``.

    ``EFV`` is the large-deflection effectiveness factor (SELECT.BAS subr 10000, a
    chart in the rudder area ratio); it is ~1.0 and not legible in the scanned
    source, so it defaults to 1.0 and is overridable -- the rudder-deflection loads
    then carry ~1% (the angle-of-attack and gust loads are independent of it and
    match tightly). ``izz_slugft2`` overrides the default airplane yaw inertia
    ``IZZ = (Wwing/g)*B^2/12 + ((0.62*GW - Wwing)/g)*LF^2/12`` (``Wwing = 0.09*GW``).
    The per-CG IZZ override is a later refinement.
    """
    rudder_deflection_deg: float = 0.0         # RD (full rudder)
    vtail_area_sqft: float = 0.0               # SV
    rudder_area_sqft: float = 0.0              # SR
    rudder_fwd_hinge_sqft: float = 0.0         # SRFWDHL
    rudder_aft_hinge_sqft: float = 0.0         # SRAFTHL
    aspect_ratio_vtail: float = 0.0            # ARVT
    vtail_mac_in: float = 0.0                  # VMAC (inches; VMAC_ft = VMAC_in/12)
    xv25: float = 0.0                          # fuselage station of 25% vtail MAC
    xv50: float = 0.0                          # fuselage station of 50% vtail MAC (ONENGOUT camber load)
    airplane_length_in: float = 0.0            # LF (inches; IZZ uses LF_ft = LF_in/12)
    wing_span_in: float = 0.0                  # B (inches; IZZ uses B_ft = B_in/12)
    gross_weight_lb: float = 0.0               # GW (IZZ default; 0 -> use the heaviest CG case)
    rudder_large_deflection_factor: float = 1.0  # EFV (subr 10000 chart; ~1.0)
    izz_slugft2: float = 0.0                   # 0 -> compute the default IZZ
    # Chordwise distribution (TAILDIST, Ch 10) -- the vertical-tail span (BLHTAIL,
    # inches; the single surface, so its full span) sets the average chord
    # CAVE = SV/B. 0 disables the chordwise distribution for the vertical tail.
    vtail_span_in: float = 0.0                 # BLHTAIL (vertical-tail span, inches)


# --------------------------------------------------------------------------- #
# Single-source empennage geometry (Step G6) -- GeometryInput.empennage
# --------------------------------------------------------------------------- #
@dataclass
class EmpennageInput:
    """Single-source empennage + control-surface geometry (Step G6).

    The horizontal- and vertical-tail definitions (including the elevator and
    rudder) are entered **once** here, on the Geometry page, and drive *both* the
    three-view sketch (``configuration.tail_planform`` reads the areas/spans/stations
    and the hinge-line chord fraction ``Saft/S`` to draw the elevator/rudder) *and*
    the rational tail-load analysis. ``htail``/``vtail`` carry the native tail-load
    inputs -- the same :class:`TailLoadsInput` / :class:`VTailLoadsInput` the
    SELECT/TAILDIST/BALLOADS/ONENGOUT modules read via the ``Project.tail_loads`` /
    ``Project.vtail_loads`` properties (which now proxy to this slice); ``None`` means
    that surface's rational loads are not modelled.

    This supersedes the duplicated ``LayoutInput`` h-/v-tail area/span/arm fields
    (retired in G6): the three-view and the tail-volume static-margin estimate now
    read the analysis-native values here, so the empennage geometry is stored in
    exactly one place. The tail *arm* is derived where needed (25% tail MAC station
    ``xt25``/``xv25`` minus the 25% wing MAC station), not stored twice.
    """
    htail: Optional[TailLoadsInput] = None
    vtail: Optional[VTailLoadsInput] = None


# --------------------------------------------------------------------------- #
# Control-surface simplified loads (AILERON / FLAPLOAD / TABLOADS) -- Step C8
# --------------------------------------------------------------------------- #
@dataclass
class AileronLoadsInput:
    """Inputs for AILERON (FAR 23.349 / 23.455 / CAM 3.222), Ref 1 Ch 16.

    The deflected-aileron load ``LAIL = 0.04*DEFL*SA*V^2/295`` is evaluated at the
    three rolling-condition speeds (full deflection at VA, then ``(VA/VC)*DEFL`` at
    VC and ``0.5*(VA/VD)*DEFL`` at VD) and the largest up/down loads are selected.
    VA/VC/VD come from ``Project.speeds`` (STRSPEED); this slice carries only the
    aileron's own geometry: the up/down deflection limits and the area forward of
    and aft of the hinge line (``SAFWD``/``SAAFT``, sq ft). The chordwise pressure
    is constant from the leading edge to the hinge line (``W = LAIL/(SAFWD +
    0.5*SAAFT)``) and tapers to zero at the trailing edge.
    """
    down_deflection_deg: float = 0.0           # ADEG (full trailing-edge-down, +)
    up_deflection_deg: float = 0.0             # AUPDEG (full trailing-edge-up, magnitude)
    area_fwd_hinge_sqft: float = 0.0           # SAFWD
    area_aft_hinge_sqft: float = 0.0           # SAAFT
    surface: str = "aileron"


@dataclass
class FlapLoadsInput:
    """Inputs for FLAPLOAD (FAR 23.345 / 23.457), Ref 1 Ch 17.

    The critical flap load is the largest of four flaps-extended conditions (1G and
    2G stall, 2G at VF, and the flaps-extended gust at VF), with the flap section
    lift built from the wing angle of attack plus the flap deflection (Abbott & von
    Doenhoff Fig 98): ``CLf = (-2.6E+2.6)*delta_rad + (0.59E+0.08)*CLw``. The
    chordwise distribution tapers from the leading edge to half that pressure at the
    trailing edge.

    Stall speeds VS/VSF are derived from the CLmax on ``Project.aero_coeffs``
    (``clmax_clean``/``clmax_flap``) at the design weight, and the flap design
    speed VF comes from ``Project.speeds``;
    the design weight from ``Project.speeds.weight_lb``; the wing area from the
    ``Project.geometry`` wing surface; and the propeller power/diameter from
    ``Project.engines[0]`` for the FAR 23.457(b) slipstream amplification. This
    slice carries the flap-specific data: the flaps-extended gust load factor, the
    flap area on one side, the flap deflection, the flap/wing chord ratio, and the
    nacelle/fuselage frontal area + engine butt line for the slipstream geometry.
    """
    gust_load_factor: float = 0.0              # NG (flaps-extended gust limit factor)
    flap_area_one_side_sqft: float = 0.0       # SF
    flap_deflection_deg: float = 0.0           # DELTA
    flap_chord_ratio: float = 0.0              # E = flap chord / wing chord
    nacelle_frontal_area_sqft: float = 0.0     # AF (nacelle or fuselage frontal area)
    engine_butt_line_in: float = 0.0           # BLPROP (0 -> fuselage-mounted)
    surface: str = "flap"


@dataclass
class TabSpec:
    """One control-surface tab for TABLOADS (FAR 23.409 / CAM 3.224), Ref 1 Ch 18.

    Full tab deflection at VC: ``LTAB = 0.0446*(1-E)*delta*Q*STAB/144`` with the
    chord ratio ``E = MACTAB/CAIRFOIL`` and a trapezoidal chordwise distribution
    whose leading-edge pressure is twice the trailing-edge pressure. ``surface`` is
    the host surface the tab sits on ("wing" / "htail" / "vtail"); ``station_in`` is
    the butt line (wing/htail) or water line (vtail) of the tab MAC; ``area_sqft``
    is in square feet (the canonical display unit; the original program worked in
    square inches, STAB, which the calc restores internally via ``*144``)."""
    surface: str = "htail"                     # host surface (wing/htail/vtail)
    mac_in: float = 0.0                        # MACTAB (tab MAC chord, in)
    area_sqft: float = 0.0                     # STAB (tab area, sq ft; STAB_in = area_sqft*144)
    station_in: float = 0.0                    # BL (wing/htail) or WL (vtail) of tab MAC
    airfoil_chord_in: float = 0.0             # CAIRFOIL (host-airfoil chord at the tab MAC, in)
    deflection_deg: float = 0.0                # DELTATAB (max tab deflection, deg)


@dataclass
class TabLoadsInput:
    """Inputs for TABLOADS: the set of control-surface tabs to size (Ref 1 Ch 18).

    VC comes from ``Project.speeds`` (the shoulder-point cruise speed); each
    :class:`TabSpec` carries its own geometry and deflection."""
    tabs: List[TabSpec] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# One-engine-out vertical-tail loads (ONENGOUT) -- the Project.one_engine_out slice
# --------------------------------------------------------------------------- #
@dataclass
class OneEngineOutInput:
    """Inputs for ONENGOUT (FAR 23.367, Reference 1 Ch 11; ONENGOUT.BAS).

    ONENGOUT is a **time-marching yaw simulation**: the failed engine creates an
    unbalanced yaw moment about the airplane vertical axis (``IZZ``); the airplane
    yaws until the pilot -- assumed to act at peak yaw rate, but not earlier than 2 s
    after the failure (23.367(b)) -- applies full rudder over ``rudder_travel_time_s``
    and recovers. The headline output is the maximum vertical-tail load.

    This slice carries only the failure-transient timing the simulation needs; the
    rest is read from existing slices:

      * engine thrust / windmill drag <- the failed ``Project.engines[i]``
        (max-continuous HP, propeller diameter, engine butt line ``y``);
      * vertical-tail geometry (ARVT, area, rudder area, full deflection, 25%/50% MAC
        stations) <- ``Project.vtail_loads`` (the ``xv50`` station added with this step);
      * yaw inertia ``IZZ`` and the CG station <- ``Project.mass`` (WTONECG), heaviest
        loading, unless overridden here;
      * the speeds and altitude <- ``Project.speeds`` (VC ultimate / VD limit / VS).

    Time history (engine thrust schedule): thrust ramps to zero over
    ``thrust_decay_time_s``, windmill drag ramps up over
    ``[thrust_decay_time_s, windmill_drag_time_s]`` then holds (Glauert max).
    ``time_step_s`` is the Euler step (the program suggests 0.05 s).
    """
    thrust_decay_time_s: float = 0.0           # TIME2DECAY (thrust -> 0)
    windmill_drag_time_s: float = 0.0          # TIME2DRAG (windmill drag -> max)
    rudder_travel_time_s: float = 0.0          # INCTIMERUD (time to full rudder)
    time_step_s: float = 0.05                  # DT (Euler step; program suggests 0.05)
    failed_engine_index: int = 0               # which Project.engines[] entry fails
    use_takeoff_power: bool = False            # MAXHP = take-off HP (else max-continuous)
    altitude_ft: Optional[float] = None        # default: Project.speeds.shoulder_altitude_ft
    speeds_kt: List[float] = field(default_factory=list)  # default: [VC, VD, VS] from speeds
    izz_slugft2: float = 0.0                   # 0 -> from Project.mass (heaviest case)
    xcg_in: float = 0.0                        # 0 -> from Project.mass (heaviest case)


# --------------------------------------------------------------------------- #
# Landing / ground loads (LGFACTOR + LANDLOAD) -- the Project.landing slice
# --------------------------------------------------------------------------- #
@dataclass
class LandingGearInput:
    """One landing-gear leg's strut geometry for LANDLOAD (tricycle gear only).

    The axle ``(X, Z)`` fuselage-station / waterline (inches) at the three strut
    states LANDLOAD.BAS prompts for, ordered ``[compressed, static, extended]``:
    the 25%-compressed position (oleo) or 100%-compressed (spring), the static
    position, and the fully extended (reference) position. ``rolling_radius_in`` is
    the tyre rolling radius; ``strut`` is the strut type ("O" oleo / "S" spring)."""
    axle_compressed: XYPoint = (0.0, 0.0)   # (X, Z) at 25% (oleo) / 100% (spring) deflection
    axle_static: XYPoint = (0.0, 0.0)       # (X, Z) static
    axle_extended: XYPoint = (0.0, 0.0)     # (X, Z) fully extended (reference)
    rolling_radius_in: float = 0.0          # RM / RN
    strut: str = "O"                        # "O" oleo | "S" spring


@dataclass
class LandingInput:
    """Inputs for the ground-load conditions (LGFACTOR + LANDLOAD), Ref 1 Ch 20.

    LGFACTOR (FAR 23.473(d)-(g)) estimates the landing load factor from the
    drop-test work-energy balance: the limit descent velocity ``V = 4.4*(W/S)^0.25``
    (clamped 7-10 fps), the flat-tyre deflection ``(OD - hub)/6`` and the strut
    stroke, with tyre/strut efficiencies (0.3 tyre; 0.5 spring / 0.75 oleo). The
    airplane load factor ``N`` is the absorbed energy ratio and the gear factor is
    ``NLG = N - L``; ``n`` persists ``N`` into ``Project.landing.n``.

    LANDLOAD (FAR 23.473-23.499) then computes the tricycle-gear reaction loads for
    the level, tail-down, one-wheel, braked-roll, side and supplementary-nose-wheel
    ground conditions, reading the gross / max-landing weights and the per-CG
    weight & CG from ``Project.mass`` (WTONECG) unless overridden by ``cg_cases``.

    The reduced landing weight (FAR 23.473(b)/(c); typically 0.95*MTOW) applies to
    the level / tail-down / one-wheel cases; the side, braked-roll and nose
    supplementary cases use the max take-off (gross) weight via ``WR = GW/W``.
    **Tricycle gear only** (UG Table 2.1)."""
    # LGFACTOR (landing load factor)
    wing_area_sqft: float = 0.0                # S (else read from geometry wing)
    max_landing_weight_lb: float = 0.0         # W (LGFACTOR + LANDLOAD reduced weight)
    gross_weight_lb: float = 0.0               # GW (0 -> from Project.mass heaviest case)
    strut_stroke_in: float = 0.0               # SSTRUT (fully extended -> compressed)
    tire_od_in: float = 0.0                    # OD (outer diameter of tyre)
    hub_diameter_in: float = 0.0               # ID (hub diameter)
    lift_factor: float = 0.667                 # L (wing lift factor, <= 0.667)
    # LANDLOAD (gear geometry)
    main_gear: LandingGearInput = field(default_factory=LandingGearInput)
    nose_gear: LandingGearInput = field(default_factory=LandingGearInput)
    tread_in: float = 0.0                      # TREAD (distance between main wheels)
    tail_down_angle_deg: float = 0.0           # GRA(3) (ground line to WL, tail-down bump)
    gear_load_factor: float = 0.0              # NLG override; 0 -> from LGFACTOR (N - L)
    # Per-CG weight & CG (aft-max-landing / fwd-max-landing / fwd-light); empty ->
    # derived from Project.mass (WTONECG). Each CgCase: name, weight_lb, xcg, zcg.
    cg_cases: List["CgCase"] = field(default_factory=list)
    n: Optional[float] = None                  # LGFACTOR airplane load factor (result)


# --------------------------------------------------------------------------- #
# Single-source landing-gear geometry (Step G6b) -- GeometryInput.landing_gear
# --------------------------------------------------------------------------- #
@dataclass
class LandingGearGeometry:
    """Single-source landing-gear geometry (Step G6b).

    The tricycle-gear geometry native to LANDLOAD -- the main/nose axle ``(X, Z)`` at
    the three strut states (compressed/static/extended), rolling radius and strut
    type, plus the ``tread`` between the main wheels -- is entered **once** here, on
    the Geometry page, and drives *both* the three-view (strut + wheels) and the
    ground-load analysis. It supersedes the duplicated coarse ``LayoutInput`` gear
    fields (``main_gear_x``/``nose_gear_x``/``track``/``gear_height``, retired in
    G6b): the three-view and the tip-back / overturn / prop-clearance estimate now
    derive the station/track/height from the native axle geometry (ground = static
    axle ``Z`` minus rolling radius). The LANDLOAD calc reads these via
    ``landing.build_landing`` (which syncs them onto ``Project.landing`` before the
    reaction solve, so the math is unchanged); the non-geometry LANDLOAD inputs
    (weights, strut stroke, tyre OD/hub, lift factor, tail-down angle) stay on
    ``Project.landing``.
    """
    main_gear: LandingGearInput = field(default_factory=LandingGearInput)
    nose_gear: LandingGearInput = field(default_factory=LandingGearInput)
    tread_in: float = 0.0                       # TREAD (distance between main wheels)


class TailType(str, Enum):
    """Empennage arrangement, for the Configuration & Layout three-view.

    Drives how ``farloads.modules.configuration.tail_planform`` places the
    horizontal/vertical tail surfaces relative to each other; a layout sketch
    distinction only, not a structural classification."""
    CONVENTIONAL = "conventional"
    T_TAIL = "t_tail"
    V_TAIL = "v_tail"
    CRUCIFORM = "cruciform"


# --------------------------------------------------------------------------- #
# General configuration & layout (modern addition) -- GeometryInput.parametric
# --------------------------------------------------------------------------- #
@dataclass
class LayoutInput:
    """General configuration & layout: the geometric source of truth.

    A modern addition (no original ``.BAS``; **no manual regression oracle** --
    Appendix A/B geometry is used only as a *sanity* fixture, asserting the derived
    ``MAC``/``XLEMAC`` match what WINGGEOM reproduces). This slice owns the
    high-level parametric geometry the configuration page edits, then *seeds*
    downstream pages (WINGGEOM polylines, WTENV/STRSPEED ``XLEMAC``/``MAC``,
    WTONECG component stations).

    Coordinates are inches in the airplane axes used throughout the suite:
    fuselage station ``X`` (aft positive from the datum), butt line ``Y`` and
    waterline ``Z``. Engine positions are **not** stored here -- they stay owned by
    ``EngineInput.engine_cg`` (the page reads them for drawing and writes back on a
    move), per the ownership rule in ``PROGRAM_SPEC.md``.

    The wing is parametric (area, aspect ratio, taper, sweep, dihedral); the
    configuration module turns it into the WINGGEOM ``leading_edge``/
    ``trailing_edge`` polylines and the trapezoidal-wing ``MAC``/``XLEMAC``/
    ``Y_MAC`` (cross-checked against the WINGGEOM strip integrator). The empennage
    (tail + elevator/rudder) geometry lives in the single-source
    ``GeometryInput.empennage`` (Step G6) and the landing-gear geometry in
    ``GeometryInput.landing_gear`` (Step G6b); this slice keeps only the empennage
    *arrangement* (``tail_type``) and h-tail drawing offset (``h_tail_z``).
    """
    # Fuselage
    fuselage_length: float = 0.0     # overall length, in
    fuselage_width: float = 0.0      # max width, in
    fuselage_height: float = 0.0     # max height, in
    datum_x: float = 0.0             # fuselage station of the nose datum reference, in
    # Wing (parametric planform)
    wing_area_sqft: float = 0.0      # reference (total) wing area S, ft^2
    aspect_ratio: float = 0.0        # AR = b^2 / S
    taper_ratio: float = 1.0         # tip chord / root (centreline) chord
    dihedral_deg: float = 0.0        # geometric dihedral
    le_sweep_deg: float = 0.0        # leading-edge sweep
    le_root_x: float = 0.0           # fuselage station of the LE at the centreline, in
    root_waterline_z: float = 0.0    # waterline of the root chord (25% MAC reference), in
    # Empennage arrangement + drawing offset only. The tail area/span/arm moved to
    # the single-source GeometryInput.empennage (Step G6); the three-view and the
    # stability estimate read the analysis-native values there (htail/vtail area,
    # span and the 25%-MAC stations), so nothing is entered twice.
    tail_type: TailType = TailType.CONVENTIONAL  # empennage arrangement (layout sketch only)
    h_tail_z: float = 0.0            # h-tail vertical offset from root_waterline_z, in
    # Landing-gear geometry moved to the single-source GeometryInput.landing_gear
    # (Step G6b): the three-view and the tip-back/overturn/clearance estimate derive
    # the station/track/height from the native LANDLOAD axle geometry there.


# Default fuselage-outline shape (fractions of overall length / max cross-section)
# used to seed a body outline from the coarse length/width/height scalars for a
# project that predates the G1 outline. A first-order nose-cone -> constant-section
# -> tail-cone form; documented here so a refinement is a one-line change.
_FUSE_MAX_SECTION_FRAC = 0.35       # station of the max cross-section, fraction of L
_FUSE_TAIL_WIDTH_FRAC = 0.10        # tail-end width, fraction of max width
_FUSE_TAIL_HEIGHT_FRAC = 0.15       # tail-end height, fraction of max height


def default_fuselage_outline(parametric: "LayoutInput") -> Optional[FuselageOutline]:
    """A first-order fuselage outline from the parametric length/width/height.

    Three sections nose -> tail: a pointed nose at the datum, the max cross-section
    at :data:`_FUSE_MAX_SECTION_FRAC` of the length, and a tapered tail cone. Used
    to migrate an older project (which carries only the scalars) to the G1 body
    outline. Returns ``None`` when no fuselage length is set (draw nothing, exactly
    as before the outline existed).
    """
    length = parametric.fuselage_length
    if length <= 0:
        return None
    x0 = parametric.datum_x
    w, h = parametric.fuselage_width, parametric.fuselage_height
    return FuselageOutline(sections=[
        FuselageSection(x0, 0.0, 0.0),
        FuselageSection(x0 + _FUSE_MAX_SECTION_FRAC * length, w, h),
        FuselageSection(x0 + length, _FUSE_TAIL_WIDTH_FRAC * w, _FUSE_TAIL_HEIGHT_FRAC * h),
    ])


@dataclass
class CaseRef:
    """A stable, traceable identity for one delivered structural load case (Step D1).

    ``case_id`` is ``"<component>-<seq>"`` (``"W-01"``, ``"HT-03"``, ``"VT-02"``,
    ``"F-04"``, ``"EM-01"``, ``"LG-05"``, ...) -- see ``farloads.case_ids`` for the
    six-entry component-prefix taxonomy (control surfaces fold into their host
    structural component; the surface identity lives in ``condition``, not a
    separate prefix). Minted **once**, by the module that first names the physical
    condition, and carried unchanged by every downstream stage that derives a
    result from that same case (never re-minted) -- see ``docs/30_future/
    00_backlog.md`` Step D1 for the full design, including the accepted gap where
    the wing (``select_wing`` vs. ``WingMassInput.cases``) and vertical-tail
    (``select_vtail`` vs. ``one_engine_out``) pipelines mint two independent
    sequences that share a prefix but are not the same case object.
    """
    case_id: str
    component: str          # "wing" | "htail" | "vtail" | "fuselage" | "engine_mount" | "landing_gear"
    condition: str          # human label, e.g. "PHAA", "down aileron", "sudden rudder"
    cg: str = ""
    speed_kt: Optional[float] = None
    altitude_ft: Optional[float] = None
    far_reference: str = ""


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
    """Result of one FAR 23 load condition.

    ``safety_factor`` is the per-case factor the render/export layer multiplies the
    LIMIT load quantities by to report ULTIMATE loads (14 CFR 25.303 -> 1.5). It is
    per-case so a future 14 CFR 25.302 / Appendix K refinement can give a failure
    case a probability-interpolated factor (1.0-1.5); the calc itself always emits
    LIMIT values, so the regression oracles are unaffected.
    """
    title: str
    far_reference: str
    values: List[LoadValue] = field(default_factory=list)
    note: str = ""
    safety_factor: float = ULTIMATE_FACTOR
    case_ref: Optional[CaseRef] = None


@dataclass
class ModuleResult:
    """The output of one suite module: its name plus the conditions it produced.

    Every module's ``run(project)`` returns this uniform type so the registry,
    CLI and GUI can treat all 22 programs identically.
    """
    module: str
    conditions: List[ConditionResult] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Mass-properties results (WTONECG) -- the Project.mass slice
# --------------------------------------------------------------------------- #
@dataclass
class MassCase:
    """Weight, CG and inertia for one loading (one WTONECG result).

    The persisted form of WTONECG's per-loading output: total ``weight_lb`` at the
    CG (``cg_x``/``cg_y``/``cg_z``, in) with the moments and product of inertia
    about that CG in **lb-in^2** (the weight-database unit; convert to slug-ft^2 by
    dividing by ``constants.LBIN2_PER_SLUGFT2``). ``name`` labels the loading
    (e.g. "aft gross", "fwd gross", "min weight"); ``gear_down`` distinguishes the
    gear-up/down pair for retractable gear.
    """
    name: str
    weight_lb: float = 0.0
    cg_x: float = 0.0
    cg_y: float = 0.0
    cg_z: float = 0.0
    ixx: float = 0.0
    iyy: float = 0.0
    izz: float = 0.0
    ixz: float = 0.0
    gear_down: bool = True


@dataclass
class MassResult:
    """The persisted mass-properties slice (``Project.mass``), written by WTONECG.

    Carries the weight/CG/inertia of each structural-limit loading (up to the four
    CG cases x gear up/down). SELECT reads the inertia for the maneuver/gust
    balancing and unbalanced-load conditions; FLTLOADS/LANDLOAD read weight & CG.
    Introduced in Step C6 -- the point at which a consumer (SELECT) finally needs
    the long-deferred persisted ``Project.mass`` (see the WTONECG note in
    ``PROGRAM_SPEC.md``)."""
    cases: List[MassCase] = field(default_factory=list)


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
    # Stamped by SELECT (case_ids.py) when this point is chosen as a governing
    # critical condition -- the same CaseRef as the CriticalCondition it produced.
    # None for the bulk of the V-n matrix (never selected).
    case_ref: Optional["CaseRef"] = None


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
class CriticalCondition:
    """One governing (critical) load condition selected/computed by SELECT (Ch 9).

    SELECT scans the FLTLOADS V-n matrix (plus inertia and geometry) and, per
    component, computes the rational critical loads and names the governing point.
    ``component`` is "wing" / "htail" / "vtail" / "fuselage"; ``label`` is the FAR
    condition tag (wing PHAA/PMAA/PLAA/NMAA; h-tail balancing/maneuver/gust/
    unsymmetrical; v-tail 23.441/23.443; fuselage 23.301/23.331/23.351/23.471).
    ``case`` references the source :class:`VnPoint` in ``Project.envelope.vn`` (or
    ``None`` for a derived condition); ``far_reference`` cites the regulation.
    ``loads`` carries the governing scalar quantities (n, CL, V, tail load, shear,
    bending, ...) as labelled :class:`LoadValue`s so report/units render unchanged.

    For horizontal/vertical-tail conditions, ``lt25``/``lt50`` carry the load
    resolved at 25% MAC (angle-of-attack) and 50% MAC (camber) -- the rational
    split TAILDIST (C7) distributes chordwise. They are ``None`` for wing/fuselage
    conditions (and for tail conditions emitted before C7)."""
    component: str
    label: str
    far_reference: str = ""
    case: Optional[int] = None
    loads: List[LoadValue] = field(default_factory=list)
    lt25: Optional[float] = None
    lt50: Optional[float] = None
    case_ref: Optional[CaseRef] = None
    note: str = ""


@dataclass
class CriticalLoadSet:
    """The governing critical-load set per component (SELECT -> ``envelope.critical``).

    One :class:`CriticalCondition` per (component, FAR condition). Read by AIRLOADS/
    AIRLOAD4 (iterative -- SELECT names the conditions they evaluate), WINGINER and
    TAILDIST (the ownership table in ``PROGRAM_SPEC.md``).

    ``selected_case_ids`` (Step D5) is the engineer's opt-out subset -- the
    Critical Loads page persists the ``case_id`` of every condition the engineer
    keeps for the deliverable; an empty list means "no filter, use every computed
    condition" (the default, and the whole behavior for any project that predates
    this field or never visits the page). Structural calc modules (WINGINER,
    NETLOADS, body_loads, the sbeam bridge) deliberately keep reading
    ``conditions`` directly -- the selection never changes what the
    load-producing modules compute. It governs what the *Results Review* GUI
    page displays, and (Step D8.3) an opt-in "governing set" toggle on the
    *Export* page that filters the fuselage/tail sbeam artifacts and the case
    index -- wing and control-surface exports are unaffected (their case ids
    don't overlap this set; see ``sbeam_bridge.filter_by_selected_case_ids``).
    """
    conditions: List[CriticalCondition] = field(default_factory=list)
    selected_case_ids: List[str] = field(default_factory=list)

    def selected(self) -> List[CriticalCondition]:
        """``conditions`` filtered to ``selected_case_ids``, or all of them when
        that list is empty (no filter applied)."""
        if not self.selected_case_ids:
            return self.conditions
        ids = set(self.selected_case_ids)
        return [c for c in self.conditions if c.case_ref and c.case_ref.case_id in ids]


@dataclass
class EnvelopeResult:
    """The persisted flight-envelope slice written by FLTLOADS (read by SELECT,
    WINGINER). ``vn`` is the full balanced-condition matrix; ``tail_balance`` is
    the balancing tail load per point. ``critical`` is the per-component governing
    load set SELECT (C6) computes from that matrix."""
    vn: List[VnPoint] = field(default_factory=list)
    tail_balance: List[TailBalanceLoad] = field(default_factory=list)
    critical: Optional[CriticalLoadSet] = None


# --------------------------------------------------------------------------- #
# Wing distributed loads (WINGINER / NETLOADS) -- the Project.loads slice
# --------------------------------------------------------------------------- #
@dataclass
class WingStationLoad:
    """Distributed load at one wing station along the 25% chord (airplane axes).

    Coordinates ``x``/``y``/``z`` (in) of the quarter chord; per-strip forces
    ``fx`` (drag) and ``fz`` (lift); cumulative shears ``sx``/``sz``; bending
    ``mxx`` (about X, from lift) and ``mzz`` (about Z, from drag); ``myy`` total
    torsion about Y (lift offset + drag offset + section pitching moment). Pounds
    and inch-pounds (AIRLOADS.BAS 4700-5060 / WINGINER.BAS / NETLOADS.BAS)."""
    x: float
    y: float
    z: float
    fx: float
    fz: float
    sx: float
    sz: float
    mxx: float
    myy: float
    mzz: float


@dataclass
class WingLoadResult:
    """One condition's spanwise wing load table (root-last, mirroring the manual)."""
    case: str
    nz: float = 0.0
    nx: float = 0.0
    stations: List[WingStationLoad] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None


@dataclass
class BodyStationLoad:
    """Net load at one longitudinal fuselage station (airplane body axes).

    ``x`` fuselage station (in); per-segment applied forces ``fx`` (axial), ``fy``
    (side), ``fz`` (vertical); cumulative shears ``sx``/``sy``/``sz``; bending
    ``myy`` (about Y, from the vertical load), ``mzz`` (about Z, from the side
    load) and torsion ``mxx`` (about the body X axis). Pounds and inch-pounds
    (fuselage net distribution, Ref 1 Ch 15)."""
    x: float
    fx: float
    fy: float
    fz: float
    sx: float
    sy: float
    sz: float
    mxx: float
    myy: float
    mzz: float


@dataclass
class BodyLoadResult:
    """One condition's longitudinal fuselage net-load table (nose-to-tail)."""
    case: str
    stations: List[BodyStationLoad] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None


@dataclass
class TailChordStation:
    """One chordwise station of a tail load distribution (TAILDIST, Ref 1 Ch 10).

    ``x`` is the chord station aft of the leading edge (in); ``psi`` the net load
    intensity there (lb/in^2), the algebraic sum of the angle-of-attack ("additive")
    and camber distributions. Five stations define the piecewise-linear profile:
    leading edge, quarter chord, trailing edge and the hinge-line chord stations."""
    x: float
    psi: float


@dataclass
class TailChordResult:
    """One critical tail condition's chordwise load distribution (TAILDIST, Ch 10).

    ``component`` is "htail" / "vtail"; ``case`` the SELECT condition label; ``lt25``
    /``lt50`` the angle-of-attack (25% MAC) and camber (50% MAC) loads it resolves
    (lb); ``stations`` the five chordwise pressure points (leading-edge first).
    ``far_reference`` is copied from the source :class:`CriticalCondition` so the
    distribution keeps the governing condition's citation (23.421 balancing, 23.423
    maneuver, 23.425 gust, 23.427 unsymmetrical h-tail; 23.441/23.443 v-tail) rather
    than a single hardcoded value."""
    case: str
    component: str
    lt25: float
    lt50: float
    stations: List[TailChordStation] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None
    far_reference: str = ""


@dataclass
class ControlSurfaceStation:
    """One chordwise station of a control-surface simplified distribution (Step C8).

    ``x`` is the fractional chord aft of the leading edge (0 = LE, 1 = TE); ``psi``
    is the load intensity there (lb/in^2). The simplified FAR-style profiles use a
    few stations: aileron (constant LE->hinge, taper to 0 at TE), flap (LE->half at
    TE), tab (trapezoid, LE = 2x TE)."""
    x: float
    psi: float


@dataclass
class ControlSurfaceLoadResult:
    """One critical control-surface load + its simplified chordwise distribution.

    ``surface`` is the control surface ("aileron" / "flap" / "tab:htail" ...);
    ``case`` the FAR condition tag ("down aileron" / "up aileron" / "flap 23.345(a)"
    / "flap gust-combined" / "<surface> tab"); ``load_lb`` the critical load and
    ``v_kt`` the speed it occurs at; ``stations`` the simplified chordwise pressure
    profile (leading-edge first). Produced by AILERON / FLAPLOAD / TABLOADS (C8)."""
    surface: str
    case: str
    load_lb: float
    v_kt: float = 0.0
    stations: List[ControlSurfaceStation] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None


@dataclass
class GearReactionCase:
    """One LANDLOAD ground-condition wheel-load case (LANDLOAD.BAS output tables).

    The reaction loads for one of the 24 main-wheel / 33 nose-wheel ground cases,
    carried both with respect to the **ground line** (the "prime" P loads) and with
    respect to the **airplane datum**, plus the unbalanced moments and the inertia
    factors. ``case`` is the 1-based case number; ``description`` the FAR condition
    family; ``cg_name`` the loading. All loads in pounds; moments in inch-pounds;
    angles in degrees (Ref 1 Ch 20)."""
    case: int
    description: str
    far_reference: str
    cg_name: str
    # Ground-line ("prime") reactions
    vmp: float = 0.0    # vertical main, per wheel
    dmp: float = 0.0    # drag main
    smp: float = 0.0    # side main
    rmp: float = 0.0    # resultant main = sqrt(vmp^2 + dmp^2)
    vnp: float = 0.0    # vertical nose
    dnp: float = 0.0    # drag nose
    snp: float = 0.0    # side nose
    result: float = 0.0  # resultant nose = sqrt(vnp^2 + dnp^2)
    # Airplane-datum reactions
    vm: float = 0.0
    dm: float = 0.0
    vn: float = 0.0
    dn: float = 0.0
    # Inertia factors (ground line / airplane datum)
    nvp: float = 0.0
    ndp: float = 0.0
    ns: float = 0.0
    nv: float = 0.0
    nd: float = 0.0
    nns: float = 0.0
    # Unbalanced moments about the airplane CG (ground line)
    pitchp: float = 0.0
    rollp: float = 0.0
    yawp: float = 0.0
    case_ref: Optional[CaseRef] = None


@dataclass
class LoadsResult:
    """The persisted distributed-loads slice (``Project.loads``).

    ``wing_air`` is the AIRLOADS air-load distribution, ``wing_inertia`` the
    WINGINER inertia distribution, and ``wing_net`` their algebraic sum (NETLOADS)
    -- the headline wing structural deliverable (root shear/BM/torsion). One
    :class:`WingLoadResult` per critical condition. ``body_net`` is the fuselage
    longitudinal net-load distribution per critical condition (SELECT, C6) -- the
    body analogue of ``wing_net``. ``tail_chordwise`` is the chordwise tail-load
    distribution per critical horizontal/vertical-tail condition (TAILDIST, C7)."""
    wing_air: List[WingLoadResult] = field(default_factory=list)
    wing_inertia: List[WingLoadResult] = field(default_factory=list)
    wing_net: List[WingLoadResult] = field(default_factory=list)
    body_net: List[BodyLoadResult] = field(default_factory=list)
    tail_chordwise: List[TailChordResult] = field(default_factory=list)
    control_surface: List[ControlSurfaceLoadResult] = field(default_factory=list)


# Current project-schema version. Bump when the on-disk JSON shape changes so old
# saves can be migrated (see io.load_project). v2 adds the concept certification
# category ("C") and the WeightInput direct-weight path; v3 adds the aero slice
# (AeroInput, TAU + AIRLOADS spanwise lift); v4 adds the flight-loads input slice
# (FlightLoadsInput, FLTLOADS) and the envelope result slice (EnvelopeResult);
# v5 adds the wing-mass input slice (WingMassInput, WINGINER), the wing
# distributed-loads result slice (LoadsResult, WINGINER/NETLOADS) and the
# section profile-drag / moment tables on AeroSurfaceInput -- all additive, so
# older files load unchanged via the from_dict defaults; v6 adds the configuration
# & layout input slice (LayoutInput, the modern Configuration & Layout page) --
# additive, older files load unchanged; v7 (Step C6) adds the persisted mass slice
# (MassResult, WTONECG), the fuselage mass-distribution input (FuselageMassInput),
# the SELECT critical-load set (CriticalLoadSet on EnvelopeResult.critical) and the
# fuselage net distribution (BodyLoadResult on LoadsResult.body_net) -- all
# additive, older files load unchanged via the from_dict defaults; v8 adds the
# SELECT search-input slice (SelectInput, the wing steady-roll aileron inputs) --
# additive; v9 adds the rational horizontal-tail load inputs (TailLoadsInput) --
# additive; v10 adds the rational vertical-tail load inputs (VTailLoadsInput) --
# additive; v11 extends TailLoadsInput with the elevator/maneuver/gust fields
# (FAR 23.423/23.425 horizontal-tail loads) -- additive (new fields default to 0);
# v12 (Step C7) adds the tail semi-span/span fields on TailLoadsInput/VTailLoadsInput
# (TAILDIST chordwise average chord) and the chordwise tail-load result slice
# (TailChordResult on LoadsResult.tail_chordwise) -- all additive, older files load
# unchanged via the from_dict defaults; v13 (Step C8) adds the control-surface
# simplified-load input slices (AileronLoadsInput, FlapLoadsInput, TabLoadsInput)
# and the control-surface result slice (ControlSurfaceLoadResult on
# LoadsResult.control_surface) -- all additive, older files load unchanged via the
# from_dict defaults; v14 (Step C9) adds the one-engine-out input slice
# (OneEngineOutInput, ONENGOUT) and the 50%-MAC v-tail station (VTailLoadsInput.xv50)
# -- additive, older files load unchanged via the from_dict defaults; v15 (Step C10)
# adds the landing / ground-load input slice (LandingInput, LGFACTOR + LANDLOAD) on
# Project.landing -- additive, older files load unchanged via the from_dict defaults;
# v16 (Step D1) adds the CaseRef dataclass and an optional case_ref field on
# ConditionResult, VnPoint, CriticalCondition, WingLoadResult, BodyLoadResult,
# TailChordResult, ControlSurfaceLoadResult and GearReactionCase (the structured
# load-case ID, see farloads.case_ids) -- additive, older files load unchanged via
# the from_dict defaults (case_ref = None, back-filled on the next compute).
# v17 (Step D3) adds Project.engineer / Project.date (freeform text project
# metadata, shown on the dashboard and in exports) -- additive, default "".
# v18 (Step D4.1) adds the Project.aero_coeffs slice (AeroCoefficientsInput,
# moved out of FlightLoadsInput.configurations) -- additive; older files migrate
# via _legacy_aero_coeffs_from_flight_loads.
# v19 (Step D5) adds WeightInput.cg_cases (the shared loading-scenario list the
# new Weight/CG Grid & Payload Cases page owns, read by the Weight/CG Envelope
# chart and merged into FlightLoadsInput.cg_cases by the Flight Envelope page so
# the two can no longer diverge) and CriticalLoadSet.selected_case_ids (the
# opt-out governing-case selection SELECT's page persists for Review/Export) --
# both additive, older files migrate via _legacy_cg_cases_from_flight_loads /
# default to an empty (unfiltered) selection.
# v20 adds LayoutInput.tail_type/h_tail_span_ft/h_tail_z/v_tail_span_ft (the
# empennage arrangement + minimal span/offset geometry the Configuration &
# Layout three-view needs to draw a tail shape) -- all additive with defaults
# that reproduce today's "no tail drawn" rendering, older files migrate for free.
# v21 adds StructuralSpeedsInput.occupants (total souls on board; drives the FAR 23
# passenger-seat applicability check) -- additive, default None, older files load
# with occupants unset (the check falls back to WeightInput.seats).
# v22 adds WeightEstimationInput.crew (flight crew; part of the operating empty
# weight OEW = empty + crew*170, and the required-crew count the FAR 23 seat-limit
# check subtracts) -- additive, default 1, older files load with crew = 1.
# v23 adds EngineInput.design_yaw_rate_rad_s / design_pitch_rate_rad_s (concept's
# real 25.371 body rates, advisory) -- additive, default None; used only to guard
# condition_25_371's fixed FAR 23.371(b) stand-in (warn when a declared rate exceeds
# it). Older files load with both unset (no guard, fixed stand-in unchanged).
# v24 (Phase G0) renames the ft/in^2 geometry inputs to canonical display units --
# one unit per dimension: length -> in, area -> ft^2. SelectInput.airplane_length_ft
# -> airplane_length_in, VTailLoadsInput.{airplane_length_ft,wing_span_ft,vtail_mac_ft}
# -> *_in (each x12), LayoutInput.{h_tail_span_ft,v_tail_span_ft} -> *_in (x12), and
# TabSpec.area_sqin -> area_sqft (/144). Calc is unchanged in result (the ft/in^2
# math is restored internally); io.py migrates the legacy keys/values on load.
# v25 (Phase G1) unifies geometry into one slice: the parametric LayoutInput (was
# the separate top-level Project.configuration) and a new FuselageOutline move onto
# GeometryInput as .parametric and .fuselage, alongside the unchanged .surfaces. A
# legacy file's top-level "configuration" key is folded into geometry.parametric and
# the fuselage outline is defaulted from the length/width/height scalars on load
# (default_fuselage_outline); the oracle-locked .surfaces consumers are untouched.
# v26 (Phase G4) adds AeroCoefficientsInput.fuselage_moment (FuselageMomentInput:
# an off-by-default Munk slender-body fuselage dCm/dalpha increment, farloads.
# fuselage_moment) that flight_envelope adds to the airplane-less-tail M1 only when
# enabled -- additive, default None -> disabled -> Appendix A/B oracles bit-for-bit
# unchanged; older files load with no fuselage moment.
# v27 (Phase G6) makes GeometryInput.empennage (EmpennageInput: htail/vtail) the
# single source for the tail + elevator/rudder geometry: Project.tail_loads /
# .vtail_loads become properties proxying to it, and the duplicated LayoutInput
# h-/v-tail area/span/arm fields are retired. io migrates legacy top-level
# tail_loads/vtail_loads (and legacy LayoutInput tail fields) into geometry.empennage;
# the derived slices are byte-identical, so the SELECT tail-load oracles are unchanged.
# v28 (Phase G6b) makes GeometryInput.landing_gear (LandingGearGeometry: main/nose
# axle 3-states + tread) the single source for the landing-gear geometry: the coarse
# LayoutInput gear fields (main_gear_x/nose_gear_x/track/gear_height) are retired (the
# three-view + tip-back/overturn/clearance derive them from the native axle geometry),
# and LANDLOAD reads the gear via a sync onto Project.landing (math unchanged -> the
# Appendix A ground-load oracle is byte-identical). io migrates a pre-v28 file's
# top-level landing gear (and legacy LayoutInput gear fields) into geometry.landing_gear.
SCHEMA_VERSION = 29


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
    engineer: str = ""
    date: str = ""
    engines: List["EngineInput"] = field(default_factory=list)
    engine_layout: Optional[EngineLayout] = None
    weight: Optional[WeightInput] = None
    geometry: Optional[GeometryInput] = None
    speeds: Optional[StructuralSpeedsInput] = None
    aero: Optional[AeroInput] = None
    aero_coeffs: Optional[AeroCoefficientsInput] = None
    flight_loads: Optional[FlightLoadsInput] = None
    envelope: Optional[EnvelopeResult] = None
    mass: Optional[MassResult] = None
    wing_mass: Optional[WingMassInput] = None
    fuselage_mass: Optional[FuselageMassInput] = None
    select_input: Optional[SelectInput] = None
    # tail_loads / vtail_loads are properties (Step G6) proxying to the single-source
    # GeometryInput.empennage.htail / .vtail -- see below. They are NOT dataclass
    # fields, so construct via geometry=GeometryInput(empennage=...) or assign after.
    aileron_loads: Optional[AileronLoadsInput] = None
    flap_loads: Optional[FlapLoadsInput] = None
    tab_loads: Optional[TabLoadsInput] = None
    one_engine_out: Optional[OneEngineOutInput] = None
    landing: Optional[LandingInput] = None
    loads: Optional[LoadsResult] = None
    # Opt-in FAR 25 superset: when True the engine module appends the optional
    # 14 CFR 25.361/25.371 cases (turbopropeller only) on top of the oracle-locked
    # FAR 23 conditions. Defaults off, so GA projects are byte-identical.
    include_far25: bool = False

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

    def _ensure_empennage(self) -> "EmpennageInput":
        """The single-source empennage slice, created (with its geometry) on demand."""
        if self.geometry is None:
            self.geometry = GeometryInput()
        if self.geometry.empennage is None:
            self.geometry.empennage = EmpennageInput()
        return self.geometry.empennage

    @property
    def tail_loads(self) -> Optional["TailLoadsInput"]:
        """Rational horizontal-tail inputs (Step G6: proxied from
        ``geometry.empennage.htail``, the single stored home). ``None`` when no
        empennage/h-tail geometry is present; SELECT/TAILDIST/BALLOADS read this."""
        emp = self.geometry.empennage if self.geometry is not None else None
        return emp.htail if emp is not None else None

    @tail_loads.setter
    def tail_loads(self, value: Optional["TailLoadsInput"]) -> None:
        if value is None and (self.geometry is None or self.geometry.empennage is None):
            return
        self._ensure_empennage().htail = value

    @property
    def vtail_loads(self) -> Optional["VTailLoadsInput"]:
        """Rational vertical-tail inputs (Step G6: proxied from
        ``geometry.empennage.vtail``, the single stored home). ``None`` when no
        empennage/v-tail geometry is present; SELECT/ONENGOUT/TAILDIST read this."""
        emp = self.geometry.empennage if self.geometry is not None else None
        return emp.vtail if emp is not None else None

    @vtail_loads.setter
    def vtail_loads(self, value: Optional["VTailLoadsInput"]) -> None:
        if value is None and (self.geometry is None or self.geometry.empennage is None):
            return
        self._ensure_empennage().vtail = value
