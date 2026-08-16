"""The Project aggregate root + SCHEMA_VERSION (split from models.py at M3-1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .enums import EngineLayout
from .inputs import (
    AeroCoefficientsInput,
    AeroInput,
    AileronLoadsInput,
    EmpennageInput,
    EngineInput,
    FlapLoadsInput,
    FlightLoadsInput,
    FuselageMassInput,
    GeometryInput,
    LandingInput,
    OneEngineOutInput,
    SafetyFactorPolicyInput,
    SelectInput,
    StructuralSpeedsInput,
    TabLoadsInput,
    TailLoadsInput,
    TailMassInput,
    VTailLoadsInput,
    WeightInput,
    WingMassInput,
)
from .results import EnvelopeResult, LoadsResult, MassResult




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
# load-case ID, see sloads.case_ids) -- additive, older files load unchanged via
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
# an off-by-default Munk slender-body fuselage dCm/dalpha increment, sloads.
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
# v30 (Step M2-6) single-sources the last of the softer geometry/power double-entry:
# the wing scalars FlightLoadsInput.mac/wing_area_sqft/xw/zw, WingMassInput.
# dihedral_deg/wrp_waterline and LandingInput.wing_area_sqft are derived from
# Project.geometry (the WINGGEOM wing surface + the parametric wing) and no longer
# persisted; the fuselage LayoutInput.fuselage_length/width/height become a derived
# read-only summary of the GeometryInput.fuselage outline (also not persisted); and
# WeightEstimationInput gains override_max_continuous_hp (the weight estimate uses
# sum(engines[].max_cont_hp) unless overridden). All migrations are lenient -- an
# older file's stored copies are read but ignored (re-derived), the outline is
# defaulted from the length/width/height scalars when absent, and override defaults
# False. Fixtures fold the derived values (Appendix A oracles within +/-0.1%).
# v31 (Step M2-10) adds the operational-limitation targets to StructuralSpeedsInput
# (no_yellow_arc + target_vne/vno/vmo/mmo/vfe) -- advisory Subpart-G placard targets
# that never change any load. Migration is lenient: an older file simply lacks the
# keys and takes the defaults (no_yellow_arc False, all targets None).
# v32 (Step M2R-4) removes the write-back LandingInput.n field (a redundant mirror of
# LoadFactorResult.airplane_load_factor that build_landing wrote on render, tripping the
# unsaved-changes flag). Migration is lenient: an older file's "n" key is ignored by the
# tolerant landing_from_dict reader; the load factor is recomputed each run.
# v33 (Defect M4-7) adds safety_factor to CriticalCondition and to the four
# distributed-load results (WingLoadResult, BodyLoadResult, TailChordResult,
# ControlSurfaceLoadResult), so the sbeam export scales each case by its owning
# condition's limit->ultimate factor instead of a flat suite-wide 1.5. Migration is
# lenient: an older file simply lacks the key and takes the default
# (constants.ULTIMATE_FACTOR = 1.5), so every exported number is unchanged.
# v34 (Step M4-18) adds SurfaceInput.ref_axis_pct -- the surface's loads
# reference axis (LRA, the beam-model elastic axis) as a fraction of chord --
# and WingLoadResult.torsion_axis (the in-band label of the axis the cumulative
# torsion is stated about). The calc stays on the 25% chord (oracle-locked);
# the wing torsion is transferred to the LRA at the render/export boundary
# (net_loads.to_loads_ref_axis). Migration is lenient: an older file lacks both
# keys and takes the defaults (0.25 / "25% chord"), reproducing the original
# quarter-chord reporting bit-for-bit.
# v35 (Step M4-1) adds SurfaceInput.front_spar_pct / .rear_spar_pct -- the
# front/rear spar chord fractions that locate the wing carry-through the Ch 15
# fuselage moment closure reacts the unbalanced moment over (Ref 1 p103).
# Migration is lenient: an older file lacks both keys and they stay None, which
# means "not entered" -- derived_geometry.carry_through then substitutes
# constants.DEFAULT_FRONT_SPAR_PCT / _REAR_SPAR_PCT and marks the result
# ``assumed`` so the deliverable states the spar stations were assumed.
# v36 (Step G8.2) adds the document-control fields Project.revision /
# .checked_by / .approved_by / .description -- the controlling-document header of
# the Step-G8 summary report (title page + signature block). All four are
# free-text and default to "", so an older file loads unchanged and the title
# page simply omits the rows it has no value for.
# v37 (Step M4-9) adds LoadValue.key -- the stable machine identity of an output
# quantity, replacing the display label as the thing report/export/view/test code
# matches on. The field is persisted (the envelope slice stores the SELECT
# critical conditions' LoadValues), so a v36 file carries labels with no keys:
# migrations._v36_load_value_keys backfills them from the label using the frozen
# label->key table of the labels that could ever have been written. A label the
# table does not know keeps an empty key, which is the honest outcome -- the row
# still renders, it just cannot be matched by key until the file is recomputed.
# v39 (Step M4-2) unifies load-case identity: one case_id per physical condition.
# No key is added or removed -- what changes is which *string* a wing or ONENGOUT
# case carries. SELECT's separate wing band (W-40..49) is retired (its conditions
# now hold the fixed case_ids.WING_SLOTS id, the same one WINGINER/NETLOADS use for
# the same condition), a wing case's id follows its *name* rather than its list
# position, and ONENGOUT moves to its own VT-30.. band (it collided with
# select_vtail's VT-01.. before). The only persisted field affected is
# CriticalLoadSet.selected_case_ids, which references those strings: io drops an
# entry that matches no condition and states which, rather than silently ignoring
# it (a silently-dropped id widens the "governing set" export without saying so).
# v40 (Step F25-2) adds the dive-speed basis to the speeds slice -- ``vd_basis``
# plus its Mach-margin parameters (``mach_margin_min``/``mach_margin_basis``) and
# the rough-air speed ``vb_kt`` -- and **removes** ``speeds.mach_limit.mc``/
# ``.md``. Those two were a stale duplicate: stored in the file, ignored by the
# Streamlit page (which recomputed MC/MD from the design speeds) and honoured by
# the CLI, so the same project gave different MNE/MFC on different front-ends.
# MC/MD are now derived by structural_speeds and passed to mach_limit explicitly.
# The v39 hop drops the dead keys; ``vd_basis`` defaults to the speed-ratio route,
# so every pre-v40 project keeps exactly the numbers it had.
# B8a-1 (v43): ``VTailLoadsInput.vtail_root_waterline_z`` -- the fin's root
# waterline, explicit where known and derived-and-marked otherwise (plan 13
# decision L-1). Additive with a 0.0 "derive it" default, so no migration hop is
# needed: absent *is* the documented value, and every pre-v43 project keeps the
# derived placement it would have had.
# plan 09 T6 (v45): ``TailMassInput.hinges_span_in`` / ``.actuator_span_in`` --
# the control-surface attachment geometry ``control_load_mode = "discrete"``
# requires (decision T-17). Additive with empty/zero defaults, and absent *is* the
# documented value: no attachment geometry means the surface stays in the
# "smeared" mode it has always been in, so every pre-v45 project keeps exactly the
# distribution and exactly the deck it had. No migration hop.
# M4-8 / step 10 piece 1 (v46): ``Project.safety_factors`` -- the user's override
# layer over the governing safety-factor table (decision G-11). The table's rows
# themselves are code (``sloads.safety_factors``); only deviations are project
# data. Additive with a ``None`` "no overrides" default, and absent *is* the
# documented value: no override means the regulation's own derived factors, which
# is exactly what every pre-v46 project already got. No migration hop, and the
# shipped fixtures are byte-for-byte unchanged.
# Step 10 piece 2 (v47): the weight/CG case model and the gear inputs, one hop for
# the whole set (decisions G-2, G-3, G-4, G-5, G-14). ``CgCase`` gains ``analyses``
# and ``role``; ``FlightLoadsInput.cg_cases`` and ``LandingInput.cg_cases`` are
# **removed** in favour of the one tagged list; ``WeightInput`` gains
# ``max_landing_weight_lb`` (moved off ``LandingInput``) and
# ``max_takeoff_weight_lb``, and ``LandingInput.gross_weight_lb`` is removed with
# them; ``MassItem`` gains ``consumable``; ``LandingGearInput`` gains ``carrier``
# and ``attach``. Removals and a relocation, so this one **does** need a hop:
# ``migrations._v46_cg_case_model``, which is output-neutral by construction --
# every value it writes comes from the file's own.
# Step 10 piece 3 (v48): ``LandingGearInput.weight_lb`` -- the leg's own weight,
# whole leg trunnion down, which closes the gear load report's free body
# (decision G-12a). Additive with a ``0.0`` default, and absent *is* the
# documented value: "not stated", which the report prints as a blank inertia term
# with its reason rather than as a leg that weighs nothing. So no migration hop,
# and every pre-v48 project keeps exactly the numbers it had -- the assembled
# ground cases read gear mass from ``weight.items`` as they always did, and this
# field feeds the report alone.
# Body drag carrier (v49): ``LayoutInput.body_drag_waterline_z`` -- the waterline
# the airplane's non-wing drag is applied at in the assembled model (design note
# ``docs/30_future/20_body_drag_carrier_note.md``, decision D-1). Additive with a
# ``0.0`` default, and ``0.0`` means "derive it" -- the wing reference plane
# ``zw``, marked ``assumed`` and stated in-band, exactly as
# ``vtail_root_waterline_z`` handles the same class of question. So no migration
# hop, and every pre-v49 project takes the derived value.
SCHEMA_VERSION = 50  # CgCase.loading: explicit loading definition (D-25)


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
    # --- Document control (Step G8.2) -------------------------------------- #
    # The controlling-document header of the summary report. All default to ""
    # so a pre-v36 file loads unchanged and the title page simply omits the row.
    # ``revision`` is deliberately **free text** the engineer maintains (decision
    # G8-5), not an auto-incrementing counter: revision identity belongs to the
    # engineering process, and a tool-managed number would disagree with the
    # drawing/report system of record the moment the project is copied.
    revision: str = ""
    checked_by: str = ""
    approved_by: str = ""
    description: str = ""
    # --- Deliverable unit preference (M4-20) -------------------------------- #
    # ``"imperial"`` or ``"si"`` -- the system every *deliverable* is rendered in
    # (report, load-case CSV, sbeam decks). A **preference only**: it says nothing
    # about the units of the values stored beside it, which are always canonical
    # Imperial. ``io.py`` never converts, so a project written on an SI machine
    # holds the same numbers as one written on an Imperial machine.
    #
    # A plain ``str`` rather than ``units.UnitSystem``: ``sloads.units`` imports
    # from ``sloads.models``, so the enum cannot come the other way without a
    # cycle. Parse it with ``units.unit_system_from``.
    unit_system: str = "imperial"
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
    #: Per-surface empennage mass (plan 09 T-3): one entry per modelled tail
    #: surface. Absent -> that surface carries no distributed inertia.
    tail_mass: List["TailMassInput"] = field(default_factory=list)
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
    #: The governing safety-factor table's **override layer** (M4-8 / G-11). The
    #: derived rows live in :mod:`sloads.safety_factors`; ``None`` (the default,
    #: and every shipped fixture) means the regulation's own factors apply.
    safety_factors: Optional[SafetyFactorPolicyInput] = None
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

    # ----------------------------------------------------------------------- #
    # ⚠ Property proxies -- DO NOT REPLICATE THIS PATTERN (M4-12b / D-15)
    #
    # ``tail_loads`` and ``vtail_loads`` look like `Project` fields but are
    # properties over ``geometry.empennage.htail/.vtail`` (the single stored
    # home, Step G6). Two trap-doors follow, and both have bitten:
    #
    #   1. **Invisible to the dataclass protocol.** They are not in
    #      ``dataclasses.fields(Project)``, so ``asdict``/``replace``/any
    #      field-walking serializer silently omits them. ``io.py`` only
    #      round-trips them because it writes them by hand.
    #   2. **The setter silently no-ops.** Assigning ``None`` to a project with
    #      no ``geometry``/``empennage`` returns without storing anything -- the
    #      guard below exists so a `None` assignment does not conjure an empty
    #      empennage, but it means ``p.tail_loads = None; assert p.tail_loads is
    #      None`` can pass for the wrong reason, and a caller clearing the slice
    #      cannot tell success from a no-op.
    #
    # New per-domain slices go on ``Project`` as real dataclass fields, or on
    # their owning input object -- never as a proxy property. **Retirement is
    # backlog M4-10's** (per D-15): it moves ~40 call sites and belongs with the
    # ``project_from_dict`` rebuild that carries the legacy top-level keys.
    # ----------------------------------------------------------------------- #
    @property
    def tail_loads(self) -> Optional["TailLoadsInput"]:
        """Rational horizontal-tail inputs (Step G6: proxied from
        ``geometry.empennage.htail``, the single stored home). ``None`` when no
        empennage/h-tail geometry is present; SELECT/TAILDIST/BALLOADS read this.

        See the trap-door warning above before relying on assignment semantics."""
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


__all__ = [
    "SCHEMA_VERSION",
    "Project",
]
