# `project.json` Input Data Dictionary

> **Generated file — do not edit by hand.** Produced by [`docs/generate_data_dict.py`](../generate_data_dict.py) from `farloads/models.py`. Regenerate after any schema change: `.venv/bin/python docs/generate_data_dict.py`.

Schema version: **31**.

This dictionary covers the **input** slices of `Project` (`farloads/models.py`) — the fields that make up a `project.json`. The result slices (`envelope`, `mass`, `loads`) are computed outputs and are out of scope.

**Column meaning & caveats:**

- *Type* / *Default* are introspected from the dataclass (`typing.get_type_hints` / `dataclasses.fields`) — authoritative.
- *Units / notes* reproduces the field's inline `# comment` verbatim (falling back to a guess from the name suffix, e.g. `_lb`→lb). Comments are prose, not a structured units field — treat it as a hint.
- *Owning page* and *Consumed by* are **slice-level**, not per-field: `workflow.py` tracks data flow per slice, so every field inherits its root slice's page and consumer list. Owning page is the workflow step that `produces` the slice (with a small override table in the generator for slices workflow doesn't attribute); *Consumed by* lists the calc modules whose source reads `.<slice>`.

## Project slice map

The top-level `Project` fields. `name`/`engineer`/`date` are free-text metadata; `schema_version` is set by `io.py`. The rest are the input slices detailed below.

| Slice | Type | Owning page | Consumed by | Role |
| --- | --- | --- | --- | --- |
| `engines` | `List[EngineInput]` | Engine Mount Loads | `engine`, `flap`, `one_engine_out`, `weight_estimate`, `wing_geometry` | Engine-mount inputs (one per engine) |
| `engine_layout` | `EngineLayout (enum)` | Engine Mount Loads | `wing_geometry` | Engine layout constraint (enum) |
| `weight` | `WeightInput` | Weight & Mass Properties | `configuration`, `weight_envelope`, `weight_estimate`, `weight_onecg` | Weight database (WTESTIMA / WTONECG / WTENV) |
| `geometry` | `GeometryInput` | Geometry | `airloads`, `configuration`, `flap`, `landing`, `net_loads`, `structural_speeds`, `weight_envelope`, `wing_geometry`, `wing_inertia` | Geometry single-source (WINGGEOM + fuselage + empennage) |
| `speeds` | `StructuralSpeedsInput` | Structural Speeds | `aileron`, `flap`, `flight_envelope`, `mach_limit`, `one_engine_out`, `structural_speeds`, `tab` | Structural design speeds & load factors (STRSPEED) |
| `aero` | `AeroInput` | Aerodynamic Data | `airloads`, `net_loads` | Spanwise airload inputs (AIRLOADS) |
| `aero_coeffs` | `AeroCoefficientsInput` | Aerodynamic Data | `flight_envelope`, `one_engine_out`, `select`, `structural_speeds` | Airplane-less-tail aero coefficients (FLTLOADS input) |
| `flight_loads` | `FlightLoadsInput` | Flight Envelope (V-n) | `balloads`, `body_loads`, `flight_envelope`, `select`, `wing_inertia` | Flight envelope / balancing tail loads (FLTLOADS) |
| `wing_mass` | `WingMassInput` | Wing Loads | `net_loads`, `wing_inertia` | Wing-mass distribution & load cases (WINGINER) |
| `fuselage_mass` | `FuselageMassInput` | Fuselage Loads | `body_loads` | Fuselage mass distribution (SELECT / Ch 15) |
| `select_input` | `SelectInput` | Wing Loads / Tail Loads | `select` | Critical-load selection inputs (SELECT) |
| `tail_loads` | `TailLoadsInput` | Geometry (empennage, Step G6) | `balloads`, `body_loads`, `select`, `taildist` | Rational horizontal-tail inputs (via geometry.empennage) |
| `vtail_loads` | `VTailLoadsInput` | Geometry (empennage, Step G6) | `one_engine_out`, `select`, `taildist` | Rational vertical-tail inputs (via geometry.empennage) |
| `aileron_loads` | `AileronLoadsInput` | Aileron Loads | `aileron` | Aileron simplified loads (AILERON) |
| `flap_loads` | `FlapLoadsInput` | Flap Loads | `flap` | Flap simplified loads (FLAPLOAD) |
| `tab_loads` | `TabLoadsInput` | Tab Loads | `tab` | Tab simplified loads (TABLOADS) |
| `one_engine_out` | `OneEngineOutInput` | One Engine Out | `one_engine_out` | One-engine-out v-tail loads (ONENGOUT) |
| `landing` | `LandingInput` | Landing Loads | `landing` | Landing loads (LANDLOAD / GEARLOAD) |
| `include_far25` | `bool` | Engine Mount Loads | `engine` | Opt-in FAR 25 supplemental cases (flag) |

## Field tables

One table per input dataclass, in slice order (nested types follow the slice that first references them). A field typed as another dataclass is detailed in that dataclass's own table.

### `EngineInput`

Complete input set for an engine-mount loads run.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `engine_designation` | `str` | e.g. "CONTINENTAL IO-520-BB" | `''` |
| `prop_designation` | `str` | e.g. "HAM STD 1803" | `''` |
| `engine_type` | `EngineType` |  | `EngineType.RECIPROCATING` |
| `limit_load_factor` | `float` | LIMNZ | `0.0` |
| `engine_weight_lb` | `float` | ENGWT | `0.0` |
| `engine_cg` | `Tuple[float, float, float]` | XENG, YENG, ZENG | `(0.0, 0.0, 0.0)` |
| `prop_weight_lb` | `float` | PROPWT | `0.0` |
| `prop_diameter_in` | `float` | PROPDIA | `0.0` |
| `prop_inertia` | `Optional[float]` | measured propeller polar inertia, slug-ft^2 (overrides geometry) | `None` |
| `prop_blades` | `int` | NOBLADES | `0` |
| `takeoff_rpm` | `float` | TORPM | `0.0` |
| `max_cont_rpm` | `float` | CONTRPM | `0.0` |
| `prop_cg` | `Tuple[float, float, float]` | XPROP, YPROP, ZPROP | `(0.0, 0.0, 0.0)` |
| `takeoff_hp` | `Optional[float]` | TOHP | `None` |
| `max_cont_hp` | `Optional[float]` | MAXCONTHP | `None` |
| `cylinders` | `Optional[int]` | CYL | `None` |
| `max_engine_torque` | `Optional[float]` | ENGTORQ, ft-lb | `None` |
| `cruise_torque` | `Optional[float]` | CRUZTORQ, ft-lb | `None` |
| `hub_weight_lb` | `Optional[float]` | HUBWT | `None` |
| `stop_time_s` | `Optional[float]` | DT, sudden-stoppage time | `None` |
| `rotors` | `List[Rotor]` |  | `[] (factory)` |
| `max_accel_torque` | `Optional[float]` | FAR 25.361(a)(3)(ii) max accelerating torque, ft-lb | `None` |
| `design_yaw_rate_rad_s` | `Optional[float]` | concept real yaw rate (25.371) | `None` |
| `design_pitch_rate_rad_s` | `Optional[float]` | concept real pitch rate (25.371) | `None` |

### `Rotor`

A turbine or compressor rotor, used for sudden-stoppage and gyro loads.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `diameter_in` | `float` | rotor diameter, inches | `**required**` |
| `weight_lb` | `float` | rotor weight, lb | `**required**` |
| `max_rpm` | `float` | signed; clockwise (pilot's view) is positive | `**required**` |
| `rotor_type` | `RotorType` |  | `RotorType.TURBINE` |
| `direction` | `RotorDirection` |  | `RotorDirection.CLOCKWISE` |
| `inertia` | `Optional[float]` | measured polar inertia, slug-ft^2 (overrides geometry) | `None` |

### `WeightInput`

The single shared weight database read by every mass-properties module.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `estimation` | `Optional[WeightEstimationInput]` |  | `None` |
| `items` | `List[MassItem]` |  | `[] (factory)` |
| `envelope` | `Optional[WeightEnvelopeInput]` |  | `None` |
| `cg_cases` | `List[CgCase]` |  | `[] (factory)` |

### `WeightEstimationInput`

Mission inputs for WTESTIMA (the statistical weight estimate).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `airplane` | `str` |  | `''` |
| `max_continuous_hp` | `float` | HP -- combined total; override value (see class doc) | `0.0` |
| `override_max_continuous_hp` | `bool` | use the stored total instead of the engine sum | `False` |
| `engines` | `int` | NOENGS | `1` |
| `seats` | `int` | SEATS (170 lb each) -- total occupant seats | `1` |
| `crew` | `int` | flight crew (170 lb each); part of the operating | `1` |
| `cruise_hours` | `float` | HOURS on full tanks at cruise power | `0.0` |
| `baggage_lb` | `float` | BAG | `0.0` |
| `pressurized` | `bool` | P$ = "P" | `False` |
| `engine_weight_type` | `EngineWeightType` |  | `EngineWeightType.RECIP_4CYCLE` |

### `MassItem`

One row of the weight database: a component's weight and station.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `name` | `str` |  | `**required**` |
| `weight_lb` | `float` | lb | `**required**` |
| `x` | `float` |  | `0.0` |
| `y` | `float` |  | `0.0` |
| `z` | `float` |  | `0.0` |
| `ixx` | `float` |  | `0.0` |
| `iyy` | `float` |  | `0.0` |
| `izz` | `float` |  | `0.0` |
| `kind` | `MassItemKind` |  | `MassItemKind.EMPTY` |

### `WeightEnvelopeInput`

Structural weight/CG limits for WTENV (the discretionary-loading envelope).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `gross_weight` | `float` |  | `0.0` |
| `aft_gross_pct_mac` | `float` | % MAC | `0.0` |
| `fwd_gross_pct_mac` | `float` | % MAC | `0.0` |
| `fwd_regardless_pct_mac` | `float` | % MAC | `0.0` |
| `fwd_regardless_weight` | `float` |  | `0.0` |
| `wing_surface` | `str` |  | `'wing'` |
| `xlemac` | `Optional[float]` |  | `None` |
| `mac` | `Optional[float]` |  | `None` |
| `fuselage_nose_x` | `Optional[float]` |  | `None` |
| `fuselage_tail_x` | `Optional[float]` |  | `None` |

### `CgCase`

One weight / centre-of-gravity case balanced over the flight envelope.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `name` | `str` |  | `**required**` |
| `weight_lb` | `float` | lb | `**required**` |
| `xcg` | `float` |  | `**required**` |
| `zcg` | `float` |  | `**required**` |

### `GeometryInput`

The single geometry source of truth (Step G1): parametric layout, the WINGGEOM lifting-surface planforms, and the fuselage outline.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `surfaces` | `List[SurfaceInput]` |  | `[] (factory)` |
| `parametric` | `Optional[LayoutInput]` |  | `None` |
| `fuselage` | `Optional[FuselageOutline]` |  | `None` |
| `empennage` | `Optional[EmpennageInput]` |  | `None` |
| `landing_gear` | `Optional[LandingGearGeometry]` |  | `None` |

### `SurfaceInput`

One aerodynamic surface for WINGGEOM, defined by its edge polylines.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `name` | `str` |  | `**required**` |
| `leading_edge` | `List[Tuple[float, float]]` |  | `**required**` |
| `trailing_edge` | `List[Tuple[float, float]]` |  | `**required**` |
| `symmetric` | `bool` |  | `True` |
| `elements` | `int` |  | `20` |

### `LayoutInput`

General configuration & layout: the geometric source of truth.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `fuselage_length` | `float` | overall length, in -- derived summary (M2-6) | `0.0` |
| `fuselage_width` | `float` | max width, in -- derived summary (M2-6) | `0.0` |
| `fuselage_height` | `float` | max height, in -- derived summary (M2-6) | `0.0` |
| `datum_x` | `float` | fuselage station of the nose datum reference, in | `0.0` |
| `wing_area_sqft` | `float` | reference (total) wing area S, ft^2 | `0.0` |
| `aspect_ratio` | `float` | AR = b^2 / S | `0.0` |
| `taper_ratio` | `float` | tip chord / root (centreline) chord | `1.0` |
| `dihedral_deg` | `float` | geometric dihedral | `0.0` |
| `le_sweep_deg` | `float` | leading-edge sweep | `0.0` |
| `le_root_x` | `float` | fuselage station of the LE at the centreline, in | `0.0` |
| `root_waterline_z` | `float` | waterline of the root chord (25% MAC reference), in | `0.0` |
| `tail_type` | `TailType` | empennage arrangement (layout sketch only) | `TailType.CONVENTIONAL` |
| `h_tail_z` | `float` | h-tail vertical offset from root_waterline_z, in | `0.0` |

### `FuselageOutline`

The fuselage body outline: cross-sections ordered nose -> tail (Step G1).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `sections` | `List[FuselageSection]` |  | `[] (factory)` |

### `EmpennageInput`

Single-source empennage + control-surface geometry (Step G6).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `htail` | `Optional[TailLoadsInput]` |  | `None` |
| `vtail` | `Optional[VTailLoadsInput]` |  | `None` |

### `LandingGearGeometry`

Single-source landing-gear geometry (Step G6b).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `main_gear` | `LandingGearInput` |  | `LandingGearInput() (factory)` |
| `nose_gear` | `LandingGearInput` |  | `LandingGearInput() (factory)` |
| `tread_in` | `float` | TREAD (distance between main wheels) | `0.0` |

### `FuselageSection`

One fuselage cross-section station for the body outline (Step G1).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `x` | `float` |  | `**required**` |
| `width` | `float` |  | `**required**` |
| `height` | `float` |  | `**required**` |

### `TailLoadsInput`

Geometry/aero inputs for SELECT's rational horizontal-tail loads (Ch 9).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `tail_incidence_deg` | `float` | IT (WL to tail chord) | `0.0` |
| `wing_zero_lift_cruise_deg` | `float` | IW, cruise config | `0.0` |
| `wing_zero_lift_enroute_deg` | `float` | IW, enroute config | `0.0` |
| `wing_zero_lift_landing_deg` | `float` | IW, landing config | `0.0` |
| `aspect_ratio_wing` | `float` | ARW (downwash) | `0.0` |
| `aspect_ratio_htail` | `float` | ARHT (tail lift slope) | `0.0` |
| `htail_area_sqft` | `float` | ST | `0.0` |
| `elevator_effectiveness` | `float` | dalpha/ddelta_e as a fraction of AHT | `0.0` |
| `xt25` | `float` | fuselage station of 25% tail MAC | `0.0` |
| `xt50` | `float` | fuselage station of 50% tail MAC | `0.0` |
| `elevator_te_up_deg` | `float` | EUP (full trailing-edge-up) | `0.0` |
| `elevator_te_down_deg` | `float` | EDN (full trailing-edge-down) | `0.0` |
| `elevator_area_sqft` | `float` | SE (total elevator area) | `0.0` |
| `elevator_fwd_hinge_sqft` | `float` | SEFWDHL | `0.0` |
| `elevator_aft_hinge_sqft` | `float` | SEAFTHL | `0.0` |
| `airplane_length_in` | `float` | LF (inches; Iyy uses LF_ft = LF_in/12) | `0.0` |
| `wing_lift_slope_per_rad` | `float` | AW (gust downwash relief 1 - 36*aw/ARW) | `0.0` |
| `htail_semispan_in` | `float` | BLHTAIL (tail semi-span, inches) | `0.0` |

### `VTailLoadsInput`

Geometry/aero inputs for SELECT's rational vertical-tail loads (Ch 9).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `rudder_deflection_deg` | `float` | RD (full rudder) | `0.0` |
| `vtail_area_sqft` | `float` | SV | `0.0` |
| `rudder_area_sqft` | `float` | SR | `0.0` |
| `rudder_fwd_hinge_sqft` | `float` | SRFWDHL | `0.0` |
| `rudder_aft_hinge_sqft` | `float` | SRAFTHL | `0.0` |
| `aspect_ratio_vtail` | `float` | ARVT | `0.0` |
| `vtail_mac_in` | `float` | VMAC (inches; VMAC_ft = VMAC_in/12) | `0.0` |
| `xv25` | `float` | fuselage station of 25% vtail MAC | `0.0` |
| `xv50` | `float` | fuselage station of 50% vtail MAC (ONENGOUT camber load) | `0.0` |
| `airplane_length_in` | `float` | LF (inches; IZZ uses LF_ft = LF_in/12) | `0.0` |
| `wing_span_in` | `float` | B (inches; IZZ uses B_ft = B_in/12) | `0.0` |
| `gross_weight_lb` | `float` | GW (IZZ default; 0 -> use the heaviest CG case) | `0.0` |
| `rudder_large_deflection_factor` | `float` | EFV (subr 10000 chart; ~1.0) | `1.0` |
| `izz_slugft2` | `float` | 0 -> compute the default IZZ | `0.0` |
| `vtail_span_in` | `float` | BLHTAIL (vertical-tail span, inches) | `0.0` |

### `LandingGearInput`

One landing-gear leg's strut geometry for LANDLOAD (tricycle gear only).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `axle_compressed` | `Tuple[float, float]` | (X, Z) at 25% (oleo) / 100% (spring) deflection | `(0.0, 0.0)` |
| `axle_static` | `Tuple[float, float]` | (X, Z) static | `(0.0, 0.0)` |
| `axle_extended` | `Tuple[float, float]` | (X, Z) fully extended (reference) | `(0.0, 0.0)` |
| `rolling_radius_in` | `float` | RM / RN | `0.0` |
| `strut` | `str` | "O" oleo \| "S" spring | `'O'` |

### `StructuralSpeedsInput`

Inputs for STRSPEED (design speeds & limit maneuver load factors).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `category` | `str` |  | `'N'` |
| `weight_lb` | `float` | lb | `0.0` |
| `occupants` | `Optional[int]` | total souls on board; the FAR 23 seat-limit | `None` |
| `wing_area_sqft` | `Optional[float]` | else read from geometry wing | `None` |
| `vh_kt` | `float` | max speed at sea level (KEAS) | `0.0` |
| `shoulder_altitude_ft` | `float` | for the MC/MD Mach numbers | `0.0` |
| `wing_surface` | `str` |  | `'wing'` |
| `chosen_vc` | `Optional[float]` |  | `None` |
| `chosen_vd` | `Optional[float]` |  | `None` |
| `chosen_va` | `Optional[float]` |  | `None` |
| `chosen_vf` | `Optional[float]` |  | `None` |
| `chosen_n` | `Optional[float]` | chosen positive maneuver load factor | `None` |
| `chosen_nneg` | `Optional[float]` | chosen negative maneuver load factor | `None` |
| `mach_limit` | `Optional[MachLimitInput]` | MACHLIM inputs (Project.speeds.mach_limit) | `None` |
| `no_yellow_arc` | `bool` | turbine / 23.335(b)(4): use VMO/MMO | `False` |
| `target_vne` | `Optional[float]` | desired never-exceed VNE (KEAS) | `None` |
| `target_vno` | `Optional[float]` | desired max structural cruise VNO (KEAS) | `None` |
| `target_vmo` | `Optional[float]` | desired max operating VMO (KEAS, turbine) | `None` |
| `target_mmo` | `Optional[float]` | desired max operating MMO (Mach, turbine) | `None` |
| `target_vfe` | `Optional[float]` | desired flap extended VFE (KEAS) | `None` |

### `MachLimitInput`

Inputs for MACHLIM (the Mach-limit lines on the flight-limits diagram).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `mc` | `float` |  | `0.0` |
| `md` | `float` |  | `0.0` |
| `shoulder_altitude_ft` | `float` | ft | `0.0` |
| `max_operating_altitude_ft` | `float` | ft | `0.0` |
| `increment_ft` | `float` | ft | `1000.0` |

### `AeroInput`

The aerodynamic-input database read by AIRLOADS (one entry per surface).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `surfaces` | `List[AeroSurfaceInput]` |  | `[] (factory)` |

### `AeroSurfaceInput`

Per-surface aerodynamic inputs AIRLOADS needs on top of the WINGGEOM planform.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `name` | `str` |  | `'wing'` |
| `section_slope` | `float` | mo, section lift-curve slope, per degree | `0.1075` |
| `taper_ratio` | `float` | tip chord / centreline chord (for TAU) | `0.0` |
| `tip_ratio` | `float` | rounded-tip width / semi-span (for TAU) | `0.0` |
| `tau` | `Optional[float]` | override; else computed from taper/tip ratio | `None` |
| `twist` | `List[Tuple[float, float]]` | (Y, zero-lift angle deg), inboard->outboard | `[] (factory)` |
| `target_cl` | `float` | wing CL the combined distribution is evaluated at | `1.0` |
| `profile_drag` | `List[Tuple[float, float]]` | (Y, CDO) | `[] (factory)` |
| `section_cm` | `List[Tuple[float, float]]` | (Y, CM) | `[] (factory)` |
| `sweep_deg` | `float` | deg | `0.0` |
| `design_mach` | `float` |  | `0.0` |

### `AeroCoefficientsInput`

Airplane-less-tail aerodynamic coefficient sets -- ``Project.aero_coeffs``.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `cruise` | `Optional[AeroCoeffSet]` |  | `None` |
| `flaps_down` | `Optional[AeroCoeffSet]` |  | `None` |
| `fuselage_moment` | `Optional[FuselageMomentInput]` |  | `None` |
| `clmax_clean` | `float` |  | `0.0` |
| `clmax_clean_neg` | `float` |  | `0.0` |
| `clmax_flap` | `float` |  | `0.0` |

### `AeroCoeffSet`

One configuration's airplane-less-tail aerodynamic coefficients.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `name` | `str` | "CRUISE" \| "LANDING" \| "ENROUTE" | `**required**` |
| `lift` | `Tuple[float, float, float, float, float]` | C0..C4 (CL vs alpha deg) | `**required**` |
| `drag` | `Tuple[float, float, float, float, float]` | D0..D4 (CD vs CL) | `**required**` |
| `moment` | `Tuple[float, float, float, float, float]` | M0..M4 (CM vs alpha deg) | `**required**` |
| `stall_cl` | `float` |  | `0.0` |
| `neg_stall_cl` | `float` |  | `0.0` |
| `flaps_down` | `bool` |  | `False` |

### `FuselageMomentInput`

Munk slender-body fuselage pitching-moment increment (Step G4).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `enabled` | `bool` |  | `False` |
| `d_cm_dalpha` | `float` | per degree; added to the airplane-less-tail M1 | `0.0` |

### `FlightLoadsInput`

Inputs for FLTLOADS (the V-n flight envelope + balancing tail loads).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `mac` | `float` | derived from geometry (Step M2-6); not persisted | `0.0` |
| `wing_area_sqft` | `float` | derived from geometry (Step M2-6); not persisted | `0.0` |
| `xw` | `float` | derived from geometry (Step M2-6); not persisted | `0.0` |
| `zw` | `float` | derived from geometry (Step M2-6); not persisted | `0.0` |
| `xtc` | `float` |  | `0.0` |
| `xtf` | `float` |  | `0.0` |
| `mn` | `float` |  | `0.1` |
| `altitudes_ft` | `List[float]` | ft | `[0.0] (factory)` |
| `cg_cases` | `List[CgCase]` |  | `[] (factory)` |

### `WingMassInput`

Inputs for WINGINER (the spanwise wing-mass distribution + load cases).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `panel_weight_lb` | `float` | lb | `0.0` |
| `tip_root_density_ratio` | `float` |  | `1.0` |
| `inboard_rib_y` | `float` |  | `0.0` |
| `wrp_waterline` | `float` | derived from geometry.parametric (Step M2-6); not persisted | `0.0` |
| `dihedral_deg` | `float` | derived from geometry.parametric (Step M2-6); not persisted | `0.0` |
| `surface` | `str` |  | `'wing'` |
| `concentrated` | `List[ConcentratedWeight]` |  | `[] (factory)` |
| `cases` | `List[WingLoadCase]` |  | `[] (factory)` |

### `ConcentratedWeight`

A concentrated wing mass item (gear, engine, fuel tank, store).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `name` | `str` |  | `**required**` |
| `weight_lb` | `float` | lb | `**required**` |
| `x` | `float` |  | `0.0` |
| `y` | `float` |  | `0.0` |
| `z` | `float` |  | `0.0` |

### `WingLoadCase`

One critical wing condition WINGINER/NETLOADS evaluate (WINGINER.BAS 1660-1710).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `name` | `str` | "PHAA" / "ACRL" / "TORS" / ... | `**required**` |
| `case` | `Optional[int]` |  | `None` |
| `nz` | `Optional[float]` |  | `None` |
| `nx` | `Optional[float]` |  | `None` |
| `unbal_moment` | `float` |  | `0.0` |
| `cl` | `Optional[float]` |  | `None` |
| `v_eas_kt` | `Optional[float]` | KEAS | `None` |

### `FuselageMassInput`

Inputs for the fuselage net-load distribution (SELECT / Ref 1 Ch 15).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `stations` | `List[FuselageStation]` |  | `[] (factory)` |
| `ref_waterline` | `float` |  | `0.0` |

### `FuselageStation`

One longitudinal fuselage reference station for the net-load integration.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `x` | `float` |  | `**required**` |
| `weight_lb` | `float` | lb | `0.0` |

### `SelectInput`

Inputs for SELECT's critical-load search (Ch 9) beyond the V-n matrix.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `full_down_aileron_deg` | `float` | deg | `0.0` |
| `basic_airfoil_cm` | `float` |  | `0.0` |
| `wing_weight_lb` | `float` | lb | `0.0` |

### `AileronLoadsInput`

Inputs for AILERON (FAR 23.349 / 23.455 / CAM 3.222), Ref 1 Ch 16.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `down_deflection_deg` | `float` | ADEG (full trailing-edge-down, +) | `0.0` |
| `up_deflection_deg` | `float` | AUPDEG (full trailing-edge-up, magnitude) | `0.0` |
| `area_fwd_hinge_sqft` | `float` | SAFWD | `0.0` |
| `area_aft_hinge_sqft` | `float` | SAAFT | `0.0` |
| `surface` | `str` |  | `'aileron'` |

### `FlapLoadsInput`

Inputs for FLAPLOAD (FAR 23.345 / 23.457), Ref 1 Ch 17.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `gust_load_factor` | `float` | NG (flaps-extended gust limit factor) | `0.0` |
| `flap_area_one_side_sqft` | `float` | SF | `0.0` |
| `flap_deflection_deg` | `float` | DELTA | `0.0` |
| `flap_chord_ratio` | `float` | E = flap chord / wing chord | `0.0` |
| `nacelle_frontal_area_sqft` | `float` | AF (nacelle or fuselage frontal area) | `0.0` |
| `engine_butt_line_in` | `float` | BLPROP (0 -> fuselage-mounted) | `0.0` |
| `surface` | `str` |  | `'flap'` |

### `TabLoadsInput`

Inputs for TABLOADS: the set of control-surface tabs to size (Ref 1 Ch 18).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `tabs` | `List[TabSpec]` |  | `[] (factory)` |

### `TabSpec`

One control-surface tab for TABLOADS (FAR 23.409 / CAM 3.224), Ref 1 Ch 18.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `surface` | `str` | host surface (wing/htail/vtail) | `'htail'` |
| `mac_in` | `float` | MACTAB (tab MAC chord, in) | `0.0` |
| `area_sqft` | `float` | STAB (tab area, sq ft; STAB_in = area_sqft*144) | `0.0` |
| `station_in` | `float` | BL (wing/htail) or WL (vtail) of tab MAC | `0.0` |
| `airfoil_chord_in` | `float` | CAIRFOIL (host-airfoil chord at the tab MAC, in) | `0.0` |
| `deflection_deg` | `float` | DELTATAB (max tab deflection, deg) | `0.0` |

### `OneEngineOutInput`

Inputs for ONENGOUT (FAR 23.367, Reference 1 Ch 11; ONENGOUT.BAS).

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `thrust_decay_time_s` | `float` | TIME2DECAY (thrust -> 0) | `0.0` |
| `windmill_drag_time_s` | `float` | TIME2DRAG (windmill drag -> max) | `0.0` |
| `rudder_travel_time_s` | `float` | INCTIMERUD (time to full rudder) | `0.0` |
| `time_step_s` | `float` | DT (Euler step; program suggests 0.05) | `0.05` |
| `failed_engine_index` | `int` | which Project.engines[] entry fails | `0` |
| `use_takeoff_power` | `bool` | MAXHP = take-off HP (else max-continuous) | `False` |
| `altitude_ft` | `Optional[float]` | default: Project.speeds.shoulder_altitude_ft | `None` |
| `speeds_kt` | `List[float]` | default: [VC, VD, VS] from speeds | `[] (factory)` |
| `izz_slugft2` | `float` | 0 -> from Project.mass (heaviest case) | `0.0` |
| `xcg_in` | `float` | 0 -> from Project.mass (heaviest case) | `0.0` |

### `LandingInput`

Inputs for the ground-load conditions (LGFACTOR + LANDLOAD), Ref 1 Ch 20.

| Field | Type | Units / notes | Default |
| --- | --- | --- | --- |
| `wing_area_sqft` | `float` | S -- derived from the geometry wing | `0.0` |
| `max_landing_weight_lb` | `float` | W (LGFACTOR + LANDLOAD reduced weight) | `0.0` |
| `gross_weight_lb` | `float` | GW (0 -> from Project.mass heaviest case) | `0.0` |
| `strut_stroke_in` | `float` | SSTRUT (fully extended -> compressed) | `0.0` |
| `tire_od_in` | `float` | OD (outer diameter of tyre) | `0.0` |
| `hub_diameter_in` | `float` | ID (hub diameter) | `0.0` |
| `lift_factor` | `float` | L (wing lift factor, <= 0.667) | `0.667` |
| `main_gear` | `LandingGearInput` |  | `LandingGearInput() (factory)` |
| `nose_gear` | `LandingGearInput` |  | `LandingGearInput() (factory)` |
| `tread_in` | `float` | TREAD (distance between main wheels) | `0.0` |
| `tail_down_angle_deg` | `float` | GRA(3) (ground line to WL, tail-down bump) | `0.0` |
| `gear_load_factor` | `float` | NLG override; 0 -> from LGFACTOR (N - L) | `0.0` |
| `cg_cases` | `List[CgCase]` |  | `[] (factory)` |
| `n` | `Optional[float]` | LGFACTOR airplane load factor (result) | `None` |

## Enumerations

- **`EngineLayout`** — `SINGLE_NOSE` = `'1N'`, `TWIN_WING` = `'2W'`, `QUAD_WING` = `'4W'`. Where the engines sit, constrained to the layouts the suite models.
- **`EngineType`** — `RECIPROCATING` = `'R'`, `TURBOPROP` = `'T'`.
- **`EngineWeightType`** — `RECIP_4CYCLE` = `'RF'`, `RECIP_2CYCLE` = `'RT'`, `TURBOCHARGED` = `'TC'`, `TURBOPROP` = `'TP'`, `LIQUID_COOLED` = `'LC'`. Engine family used by WTESTIMA's installed-weight correlation (WTESTIMA.BAS     lines 230-290): the two-letter codes of the original program.
- **`MassItemKind`** — `EMPTY` = `'empty'`, `MINIMUM` = `'minimum'`, `DISCRETIONARY` = `'discretionary'`. Where a mass item sits in the loading hierarchy of WTONECG/WTENV.
- **`RotorDirection`** — `CLOCKWISE` = `'CW'`, `COUNTERCLOCKWISE` = `'CC'`.
- **`RotorType`** — `COMPRESSOR` = `'C'`, `TURBINE` = `'T'`.
- **`TailType`** — `CONVENTIONAL` = `'conventional'`, `T_TAIL` = `'t_tail'`, `V_TAIL` = `'v_tail'`, `CRUCIFORM` = `'cruciform'`. Empennage arrangement, for the Configuration & Layout three-view.

