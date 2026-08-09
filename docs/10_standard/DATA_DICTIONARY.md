# `project.json` Input Data Dictionary

> **Generated file — do not edit by hand.** Produced by [`docs/generate_data_dict.py`](../generate_data_dict.py) from `sloads/models.py`. Regenerate after any schema change: `.venv/bin/python docs/generate_data_dict.py`.

Schema version: **41**.

This dictionary covers the **input** slices of `Project` (`sloads/models.py`) — the fields that make up a `project.json`. The result slices (`envelope`, `mass`, `loads`) are computed outputs and are out of scope.

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
| `weight` | `?` | Weight & Mass Properties | `configuration`, `weight_envelope`, `weight_estimate`, `weight_onecg` | Weight database (WTESTIMA / WTONECG / WTENV) |
| `geometry` | `?` | Geometry | `airloads`, `balance`, `configuration`, `flap`, `landing`, `net_loads`, `structural_speeds`, `weight_envelope`, `wing_geometry`, `wing_inertia` | Geometry single-source (WINGGEOM + fuselage + empennage) |
| `speeds` | `?` | Structural Speeds | `aileron`, `flap`, `flight_envelope`, `mach_limit`, `one_engine_out`, `structural_speeds`, `tab` | Structural design speeds & load factors (STRSPEED) |
| `aero` | `?` | Aerodynamic Data | `airloads`, `balance`, `net_loads` | Spanwise airload inputs (AIRLOADS) |
| `aero_coeffs` | `?` | Aerodynamic Data | `flight_envelope`, `one_engine_out`, `select`, `structural_speeds` | Airplane-less-tail aero coefficients (FLTLOADS input) |
| `flight_loads` | `?` | Flight Envelope (V-n) | `balance`, `balloads`, `body_loads`, `flight_envelope`, `select`, `wing_inertia` | Flight envelope / balancing tail loads (FLTLOADS) |
| `wing_mass` | `?` | Wing Loads | `balance`, `net_loads`, `wing_inertia` | Wing-mass distribution & load cases (WINGINER) |
| `fuselage_mass` | `?` | Fuselage Loads | `body_loads` | Fuselage mass distribution (SELECT / Ch 15) |
| `select_input` | `?` | Wing Loads / Tail Loads | `select` | Critical-load selection inputs (SELECT) |
| `tail_loads` | `TailLoadsInput` | Geometry (empennage, Step G6) | `balloads`, `body_loads`, `select`, `taildist` | Rational horizontal-tail inputs (via geometry.empennage) |
| `vtail_loads` | `VTailLoadsInput` | Geometry (empennage, Step G6) | `one_engine_out`, `select`, `taildist` | Rational vertical-tail inputs (via geometry.empennage) |
| `aileron_loads` | `?` | Aileron Loads | `aileron` | Aileron simplified loads (AILERON) |
| `flap_loads` | `?` | Flap Loads | `flap` | Flap simplified loads (FLAPLOAD) |
| `tab_loads` | `?` | Tab Loads | `tab` | Tab simplified loads (TABLOADS) |
| `one_engine_out` | `?` | One Engine Out | `one_engine_out` | One-engine-out v-tail loads (ONENGOUT) |
| `landing` | `?` | Landing Loads | `landing` | Landing loads (LANDLOAD / GEARLOAD) |
| `include_far25` | `bool` | Engine Mount Loads | `engine` | Opt-in FAR 25 supplemental cases (flag) |

## Field tables

One table per input dataclass, in slice order (nested types follow the slice that first references them). A field typed as another dataclass is detailed in that dataclass's own table.

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

## Enumerations

- **`EngineLayout`** — `SINGLE_NOSE` = `'1N'`, `TWIN_WING` = `'2W'`, `QUAD_WING` = `'4W'`. Where the engines sit, constrained to the layouts the suite models.
- **`EngineType`** — `RECIPROCATING` = `'R'`, `TURBOPROP` = `'T'`.
- **`EngineWeightType`** — `RECIP_4CYCLE` = `'RF'`, `RECIP_2CYCLE` = `'RT'`, `TURBOCHARGED` = `'TC'`, `TURBOPROP` = `'TP'`, `LIQUID_COOLED` = `'LC'`. Engine family used by WTESTIMA's installed-weight correlation (WTESTIMA.BAS     lines 230-290): the two-letter codes of the original program.
- **`MassComponent`** — `WING` = `'wing'`, `FUSELAGE` = `'fuselage'`, `HTAIL` = `'htail'`, `VTAIL` = `'vtail'`. Which structural component a mass item is carried by (plan 11 B-2, step B1).
- **`MassItemKind`** — `EMPTY` = `'empty'`, `MINIMUM` = `'minimum'`, `DISCRETIONARY` = `'discretionary'`. Where a mass item sits in the loading hierarchy of WTONECG/WTENV.
- **`RotorDirection`** — `CLOCKWISE` = `'CW'`, `COUNTERCLOCKWISE` = `'CC'`.
- **`RotorType`** — `COMPRESSOR` = `'C'`, `TURBINE` = `'T'`.
- **`TailType`** — `CONVENTIONAL` = `'conventional'`, `T_TAIL` = `'t_tail'`, `V_TAIL` = `'v_tail'`, `CRUCIFORM` = `'cruciform'`. Empennage arrangement, for the Configuration & Layout three-view.
- **`VdBasis`** — `SPEED_RATIO` = `'speed_ratio'`, `MACH_MARGIN` = `'mach_margin'`. Which regulatory route sets the design dive speed VD (F25-2).

