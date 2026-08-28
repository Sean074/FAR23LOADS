# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

**Live cycle only.** This file holds the current release cycle plus the previous
release cut. Older blocks roll into frozen, do-not-edit archives at each release
(`RELEASE_PROCESS.md` §4): the 0.7.0 cycle and the 0.7.0 cut are in
[`37_completed_development_to_0.7.1.md`](37_completed_development_to_0.7.1.md),
the 0.6.0 cycle and the 0.5.0 cut in
[`35_completed_development_to_0.6.0.md`](35_completed_development_to_0.6.0.md),
everything before 0.5.0 in
[`11_completed_development_to_0.5.0.md`](11_completed_development_to_0.5.0.md).
Tier S closures do not write here (a `changes/` fragment is their record); tier M
writes one paragraph, tier L the full step format — **as a `changes/<slug>.history.md`
fragment** (design note 28 MD-4), rolled to the top of this file at release cut, so
concurrent PRs never edit the same line here. Only the release-cut block itself is
written directly, by the release manager.

---

- **Two one-way doors in the oracle GUI (#72, PB-20/PB-23, tier M,
  2026-08-25).** Both halves of this item were the same shape: a state the user
  could enter and not leave. An `Optional` override could be filled but never
  emptied, and a table row could be added anywhere but deleted only from the
  end — and because this GUI is the only editor its projects have, "edit the
  JSON" was not an escape from either. The review's fix for the first (write
  `None` when the widget comes back empty) was tested before it was written and
  does not work: a number-seeded `st.number_input` cannot be emptied at all —
  the frontend restores the last value on blur and `NumberInputSerde.deserialize`
  reads an empty submission as the seed — so no handling of the return path can
  un-fill a field, and the clear has to be an affordance. That made the fix
  structural rather than local: the widget's own state is the only door, it may
  only be written before the widget is instantiated, and the key it is written
  under is spelled two ways (the converted mode suffixes the active unit system,
  the fixed-unit and dimensionless modes must not, so a unit-agnostic number
  survives the switch). One owner now names that key for the widget and for the
  clear alike, so the two cannot drift into clearing a widget that does not
  exist. The row half turned out to carry the counter defect of #88 in mirror
  image: a deletion that does not re-size the row counter is undone by the very
  next render, which grows the list back up to the retained count and returns
  the deleted row as a blank — so the delete runs as a callback, which is the
  only moment a widget's state can be re-sized. Two smaller findings closed with
  them, both about the GUI saying nothing where it had acted: the Save-to-disk
  confirmation was emitted immediately before the `st.rerun()` that discards it,
  so the one action with an effect outside the session had never once been
  confirmed on screen; and a cleared required table cell restored its old value
  in silence, which is the right behaviour reading as the wrong one — a grid
  that ate the edit. The contract both halves now answer to is stated once, in
  `GUI_design.md`, beside the #35 rule it completes: unfilled is empty, a typed
  0 is real, **and the door opens both ways**.

## Step — Derive-by-default overrides: one mechanism for the duplicated-input class (#97, design note 36, tier L, 2026-08-27)

**Objective.** Close the eight C210 findings that were one defect class — an
input duplicating a value the project already holds, asked blank, with a silent
fallback or a silent skew behind it (C210-13/15/29-seed/31/36/38/39/41) — with
**one mechanism** instead of eight patches: falsy-means-derive /
typed-means-override at **calc level** (a blank field in any project file
derives, CLI and GUI alike — owner ruling), one named resolver per quantity,
the computed value shown beside each collapsed field, and a drift guard that
makes the mechanism the single-source owner rather than a convention
(design note `docs/30_future/36_derive_override_note.md`, agreed 2026-08-26;
decisions OV-1…OV-12, gates G-OV-1…G-OV-6).

**Deliverables.**
- **The resolvers (OV-2), each a pre-existing owned computation** — no new
  physics: `derived_geometry.planform_aspect_ratio` (the one AR spelling,
  OV-5; both strip sweeps now call it) with `wing_aspect_ratio(project)` for
  the h-tail's blank ARW; `taper_ratio_from_planform` /
  `tip_ratio_from_planform` feeding `airloads.resolved_tau` (the TAU
  resolution spelled once); `flight_envelope.gust_at_vf` (the GUST VF corner
  factor, same `_gust_load_factor`/`_gust_ude` internals — bit-for-bit) read
  by `flap.resolved_ng`; `select.wing_lift_slope_per_rad` (cruise C1 × 57.3),
  `select.effective_tail_inputs` and `select.resolved_full_down_aileron_deg`;
  `engine.effective_engine`/`resolved_engines` (LIMNZ ← `design_speed_values
  (project).n`; weight/CG ← the `engine_mass_item`/`prop_mass_item` row,
  matched with `same_name`, refused by name when absent — every engine
  consumer swept onto the one accessor: mount loads, LRA export, WINGGEOM
  stations, nacelle sketch, OEI, hub thrust, applicability); WTENV's
  `gross_weight or max_takeoff_weight(project)` (recursion-safe: the G-14
  reverse fallback reads the raw field only when non-zero); and
  `airloads.resolve_aero_surfaces` (a schema-default aero row per unpaired
  **symmetric** planform, per name, nothing written to the project — OV-8).
- **Schema v56 (OV-10):** additive `SurfaceInput.tip_cap_width_in` (OV-4 —
  the rounding the polylines cannot carry, entered once with the wing) and the
  two engine selectors; 55→56 **identity hop** (`migrations._hop_55`), floor
  55, examples re-stamped, fields hash updated, `DATA_DICTIONARY` regenerated.
- **Registry + GUI (OV-9/OV-11):** `field_registry.COLLAPSED_OVERRIDES` — the
  collapsed set enumerated once — with `derived_from` + a record-aware
  resolver in `EXTERNAL_VALUES` per path; `oracle_app.form._collapsed_note`
  renders "Blank — derives from ⟨owner⟩ (currently X)" / the override caption
  with a > 1e-9 disagreement warning, never disabled; the stall-CL rows
  register `normalize()`'s shipped fill-through (OV-3, C210-15 ruling text;
  `flaps_down.neg_stall_cl` stays the documented #81 gap).
- **Mismatch surfaced (G-OV-6):** `validation._check_derive_overrides` —
  `aileron_deflection_mismatch`, `engine_mass_row_mismatch` (> 1e-6, the
  consistency channel); the no-such-row refusal lives in
  `engine.selected_mass_row`.

**Test / Acceptance.** `tests/test_derive_override.py` (23 tests): G-OV-2
derive-equals-owner on ga6 with each field blanked in turn (rel 1e-9; NG and
LIMNZ exact — same call); G-OV-3 the defect dies, each test stating the
pre-fix failure (τ 0.206209 on a tapered wing, the bare ARW
`ZeroDivisionError`, the zeroed mount loads, the never-analysed surface);
G-OV-4 the OV-11 drift guard (every collapsed path linked and resolvable, no
owned-quantity copy without its link); G-OV-5 v56 round-trip + the v55 hop
(`test_migrations.py::test_a_v55_file_loads_through_the_identity_hop_unchanged`);
G-OV-6 the two warning codes and the by-name refusal. **G-OV-1:** the full
suite (2,918 tests) passes with every Appendix A oracle and twin closure
untouched; the only digest movement is `csv/airloads`/`txt/airloads` on the
four fixtures carrying unpaired htail/vtail planforms — the OV-8 seed
appending their spanwise views, wing blocks byte-identical (OV-12: where a
blank used to produce a silently wrong number, the number changing to the
derived one *is* the fix).

**Key decisions.** All owner-ruled in note 36: calc-level derivation, not a
GUI affordance (OV-1, no 0.0→None migrations — a falsy authored value is never
load-bearing in scope); the engine↔mass linkage as an explicit row selector,
never a role tag (OV-7); seeded aero rows carry geometry values only (OV-8;
#98's caption owes the visibility); the main GUI needs no change for
correctness — the calc derives for both front-ends — with caption parity
recorded against #29 (OV-9); `wing_weight_lb` and the SELECT copies (C210-22/
25) stay at #95 and wire onto this mechanism when that row lands.

## Step — The geometry-page presentation family: quantity-true placement and one summary shape per module (#95, tier M, 2026-08-27)

Ten C210 findings (C210-1/2/3/5/6/8/22/25/26/27), closed as three mechanisms.
**One summary shape, both channels:** `report.summary_rows` is the single
dispatch the module CSV, the oracle results page and Results Review all render
through (`SUMMARY_SHAPES`; CONVENTIONS §7 row) — SELECT one line per case with
its per-case SF via `critical_rows`, sharing `governing_loads_table`'s
one-line core so the M2-4 tables cannot diverge; WTENV one row per
(weight, station) point via `weight_station_rows`, paired on the machine
`LoadValue.key`; every other property module the data-shaped floor
(`results_to_rows` drops all-empty columns). The owner's CSV ruling made this
an accepted deliverable-format change: only the `csv/*` Imperial digests
moved — text, sbeam and index channels are byte-identical. **Derives and
disclosures on the #97 mechanism:** SE/SR blank-derive from their own hinge
halves with a 1 %-tolerance mismatch warning (the Appendix A inputs' own
rounding is 0.2–0.7 % and stays silent); the v-tail wing span blank-derives
from the WINGGEOM integrator's span, read through `effective_vtail_inputs` by
SELECT, ONENGOUT and the tail-span split alike; the 0 → 0.09·MTOW wing-weight
and rod-IZZ fallbacks are disclosed beside their fields and the SELECT block
captions both rod inertias against WTONECG's database values (C210-25).
**Placement and seeding:** `DISPLAY_GROUPS` renders a field on the page its
quantity belongs to (the h-tail record's wing aero with the aero data, the
SELECT trio each to its home) without moving it off its record;
`RECORD_SEEDS` offers the parametric wing from a typed planform behind a
button (GR-GEOM-3 — seeded and overridable, a visit never dirties the
project); `fuselage_length` renders disabled exactly while an outline exists.
Guards: `tests/test_summary_shapes.py` (10 tests, incl. the screen-equals-CSV
drift guards) plus the extended select/validation/configuration/registry
suites; the G7 CSV gate now requires the SF column exactly where a `-ULT`
column exists, since the always-blank SF on property tables was C210-27's own
complaint.

## Step #123 — The landing load factor is entered as N, not NLG (note 37, tier L, schema v57, 2026-08-27)

**Objective.** Kill a defect with a first-order effect on shipped output by removing its class.
`LandingInput.gear_load_factor` was an NLG override that superseded LGFACTOR's energy result;
because `VMP = ½·NLG·W·AP/DP` reads NLG and nothing else, an entered NLG made the wing lift
factor `L` **inert on the vertical gear reaction** — the user changed the lift assumption and
no wheel load moved — while the page kept reporting the *energy-derived* N the reactions were
not computed from, and the `0.0` sentinel gave "unset" and a legal value one encoding. Vertical
equilibrium at peak load is `N = NLG + L`: three quantities, one equation, two degrees of
freedom, and which two are inputs decides whether L moves the reaction. The fix inverts the
pair — **`N` and `L` are the inputs; `NLG = N − L` is derived, reported, and never entered.**

**Deliverables.**

- **`landing.governing_load_factors`** — the one owner of the governing pair: entered `N`
  (`LandingInput.airplane_load_factor`, `Optional`, no sentinel) when filled, else the energy
  value; `NLG = N − L` derived nowhere else; `N ≤ L` refused by name (LF-5 — with the L cap
  gone, the only guard between `K = NAP/NLG·K0` and a zero or sign-flipped NLG).
- **The `L ≤ 0.667` refusal and widget cap removed** (LF-4): 0.667 is FAR 23.473's default and
  1.0 the FAR 25.473(a)(2) basis; both GUIs caption them as guidance through one shared string
  (`app_shell.components.LANDING_L_FAR_CAPTION`).
- **The 23.473(g) floor policy** (LF-6, one owner + drift guard, practice 3):
  `landing.far23_473g_floor_violations` with the floors in `constants.py`; a governing pair
  below `N ≥ 2.67` / `NLG ≥ 2.0` is a named refusal in a FAR 23 category (`build_landing`) and
  a warn-only note in concept (`run`), superseding the M2-8 concept-only warning.
- **Schema v56 → 57, semantic hop** (LF-8): `N = gear_load_factor + lift_factor` where the old
  override was non-zero, else unfilled; the old key is dropped. The hop reproduces every NLG
  the reaction path read, so no load number moves (LF-11). `ga6_normal`/`cessna_210` carry
  `N = 3.167` (LF-9 — p230 reproduces at NLG 2.5 and at no other value); the three concept
  examples are set to `N = 2.67`, not the hop's 2.6670 (LF-10 — a 0.11 % rounding artifact
  would have started three shipped examples warning on nothing real; NLG moves +0.15 %, the
  only moved numbers in the fleet). `field_registry` row replaced with origin `SLOADS`,
  `supplied` (demonstrably load-bearing, G5): LGFACTOR.BAS had an NLG override, never an N
  input (LF-12).
- **Both GUIs** (LF-7): `app/` seeds N from the computed energy value with a "Computed N
  governs" checkbox as the way back; the oracle GUI renders the unfilled Optional with
  "✕ clear" and a landing group note stating the computed → governing pair. `NLG` renders as a
  derived output in both; `landing.below_energy_caution` (one owner) fires when the entered N
  undercuts the energy value. The module output gains governing-N/NLG rows beside the
  oracle-locked energy rows (the S2 fix at the deliverable, not only on screen).
- **Docs.** `PROGRAM_SPEC.md` §LGFACTOR/§LANDLOAD rewritten (including the sentence that
  recorded the split as intended behaviour); `theory_sources.md` grown the FAR 23.473(g) /
  25.473(a)(2) lift-basis row and the governing-pair citation; the schema ledger
  (`test_schema_guards.py` + `project.py`) records v57; `DATA_DICTIONARY.md` and the guide
  tables regenerated; guide chapter 14 rewritten with its screenshot recaptured. Note 37's two
  arithmetic slips corrected in place, marked as implementation corrections (LF-5's inverted
  refusal; G-LF-2's K/γ figures).

**Test / Acceptance (gates G-LF-1 … G-LF-6, all in CI).**

- **G-LF-1 (oracle invariance):** the p236 Appendix-A assertions pass unmodified —
  `landing_load_factor` is untouched (LF-3); p230 passes with ga6 at `N = 3.167`.
- **G-LF-2 (L moves the reaction):** on ga6 at fixed N, raising L 0.667 → 1.0 lowers NLG
  2.500 → 2.167 and every case-4–12 VMP by exactly 2.167/2.5, and raises K to
  `(3.167/2.167)·0.256133 = 0.3743` (γ 20.52°); the pre-fix behaviour — no change at all — is
  in the test's docstring.
- **G-LF-3 (N recoverable from the reactions):** `NVP == N` exactly (rel 1e-9) on cases 4–9
  and `NVP == ½·NLG + L` on 10–12, for every bundled example.
- **G-LF-4 (the guards):** `N ≤ L` refused by name; the floors block in FAR 23 (energy-governed
  *and* entered-N paths) and warn in concept; the floor constants drift-guarded; all six
  examples pass their own category's rule.
- **G-LF-5 (schema round-trip):** the frozen v56 fixture hops to `N = 3.167` with the old key
  gone, the `0.0` sentinel loads to unfilled, `applied_hops(56) == [56]`, and the migrated
  project's 33-case matrix is bit-identical to the current fixture's.
- **G-LF-6 (both GUIs):** the caption enumerated once and consumed by both GUI sources
  (guarded); the below-computed-N caution fires on `cessna_210` (3.1670 vs 3.3885) and not on
  ga6. Imperial digests deliberately regenerated: landing channels on all fleet examples (the
  new governing rows), balance/gear/deck channels on the three concept fixtures only (the
  LF-10 nudge) — ga6/cessna/baron load channels byte-identical, as LF-11 promised.

**Key decisions.** LF-1 … LF-12 in `docs/30_future/37_landing_load_factor_note.md` (AGREED
2026-08-27); implementation choices in session: energy + governing rows both reported (not
governing-only), one solo-close commit, floor policy homed in `modules/landing.py` with
constants in `constants.py`.

## Step — Hidden required fields rendered or captioned (#98, tier M, 2026-08-27)

The `_SLDS`-origin filter hid fields the user must state (C210-46/49/29): every
tab silently defaulted to the h-tail because `tab_loads.tabs[].surface` was
never rendered, an oracle-built project could not export ground cases because
both gear legs' `carrier`/`attach`/`weight_lb` were hidden with sentinel
defaults, and an empty `aero.surfaces` list showed a bare rows counter with no
trace of the AIRLOADS block behind it. The fix is two structural classes rather
than three patches (rule 4): **row selectors** — a `name`/`surface` leaf on a
list record, which a page can never resolve positionally — are rendered
(`supplied=True`, selectboxes over `models.inputs.TAB_SURFACES`/`TAIL_SURFACES`)
with unknown surfaces refused by name (`require_surface`; the silent
`_TAB_COMPONENT.get(..., "wing")` fallback and the silently-inert `tail_mass`
row died with it), guarded by
`test_field_registry.py::test_a_list_row_selector_is_always_asked`; **sentinel
defaults** are registered in `field_registry.SENTINEL_DEFAULTS`, rendered, and
guarded by `::test_a_sentinel_default_field_is_always_asked`; and the empty-list
caption is generated from the page's own field set at `render_table`'s one early
return, so every empty list gains it and it cannot drift. Every new `supplied`
mark carries a G5 demonstration in `tests/test_oracle_inputs.py` (the tab
misroute, the override that went nowhere, the unmatched aero row's refusal, the
carrier warning, the omitted gear node, the open free body); the supplied-ratio
dial moved 10 % → 15 % with the reason stated. SSOT row: `CONVENTIONS.md` §7.

**#99 — Oracle page placement and the validation/error-display pair
(2026-08-26).** The first 0.8.0 item, four C210 build-review findings sharing
one page and one channel. Placement (C210-37/44): the aileron/flap planform
geometry and the engine layout are configuration, so their registry rows are
re-tagged to the Geometry page and sit beside the empennage forms — the slices
do not move (the single-consumer pattern stands), the oracle page set being
registry-derived makes the move a tag, and
`test_control_surface_planform_geometry_renders_on_the_geometry_page` guards
the decision; the Aileron Loads page becomes results-only and says so through
the existing no-input branch. Validation (C210-21/14): the load-bearing-zero
class gets the `cg_case_without_weight` treatment — `build_envelope` refuses a
0/unset `xtc`/`xtf` by name for exactly the configs that would read it, with
`tail_cp_station_unset` warning on the page first — and
`landing_light_not_lighter` closes the role-contradiction gap the M4-17d
hierarchy checks left at the equal-weight boundary. Display (C210-24): the
not-ready catch keeps its one-liner, adds the exception type, and carries a
module:line-first traceback into an expander, closing the display half of #71.

## Step — The oracle GUI user guide (#96, note 34, tier M, 2026-08-27)

Design note 34's guide built to plan in the six UG-10 stages, gates first:
`docs/60_guide/` with generated field tables (`docs/generate_data_dict.py` →
`_generated/`, UG-3), workflow-derived chapter order (UG-7), Playwright
screenshot capture (`scripts/capture_guide_shots.py`, UG-4), fourteen
eight-section chapters, front matter carrying the single LIMIT/ULTIMATE
statement (UG-8), and the two end-to-end appendices — `ga6_normal` in
Imperial against the printed Appendix A checkpoints, and the new
`examples/baron_58.project.json` (UG-9: TCDS-sourced Baron 58, every
estimate marked in its sources register) worked entirely in SI and closed
on the channel-free stored project (UG-12). Gates G-UG-1…G-UG-6 landed in
stage 1 and checked every chapter on arrival (`tests/test_guide.py`); the
twin joined the oracle-reduction `EXACT` set and the ground-coverage pin.
Two latent defects the twin exposed were filed with bodies the same session
(#121, #122). `GUI_USER_GUIDE.md` stays the full-app guide (UG-2), now
cross-linked both ways.

- **Page-order dependencies are declared and stated; the non-owner mark reaches
  external owners and composites (#69 + #89, tier M, 2026-08-25)** — Two defects with
  one root: the GUI knew a thing about a field's provenance and did not say it.
  `WorkflowStep` gains `reads`, the slices a step's numbers depend on that neither
  gate the run nor are entered on the page, and `app_shell.components.render_page_order_reads`
  states them on every visit — caption when the dependency is filled, warning while it
  is not. The instrument matters: `requires` blocks, and the flap and weight-estimate
  calcs are correct with no engine at all, so enforcing would have refused a valid
  glider run to fix a page-order problem. Declaring and stating leaves the calc alone.
  The dependencies were found by sweeping every step's modules by AST rather than from
  the two reported instances: seven across four steps, and that sweep is now the guard
  (`test_every_page_order_dependency_is_declared`), with a reverse test failing on a
  stale declaration. On the marking side, `_copy_note`'s early return on
  `owner_is_external` is gone — all six EXTERNAL rows are captioned with their owner in
  words, never disabled (the owner is an expression, and one of them is the calc's
  fallback), and a new `FieldEntry.resolves` carries the true sentence where `governs`
  alone would state the rule wrongly. Marking them exposed #89's latent door in the
  same session: `engines[].engine_cg` is a tuple, and the mark only ever reached
  scalars, so `render_field` now forwards the project to every branch. The render guard
  counts marks per owner phrase rather than searching for it once — two fields on the
  Engine Mount page name the same external owner, and a substring test passed while the
  tuple beside the scalar rendered bare. `st.columns(0)` guarded with it. No calc
  changed: the Imperial baseline digests and every oracle are untouched.

## Step #93 — Pre-production schema floor: read only the current `SCHEMA_VERSION` (tier L, 2026-08-25)

**Objective.** Stop carrying compatibility this project does not need. `sloads/migrations.py`
migrated any file from v18 up through twelve shape hops, plus a v0 bare-`EngineInput` branch —
632 lines of code and 439 of test guarding the ability to read files written by builds that
never shipped to anyone. Pre-production, no prior analysis has to stay readable. The floor
moves to the current version and everything below it goes; the hop *machinery* stays, empty,
so the first post-production shape change registers a hop unchanged.

The item was raised by the owner at the close of #68, which had just fixed the GUI's migration
notice. That fix is what surfaced this: the notice could only ever have fired on the six
bundled examples, which had sat at v41 for fourteen versions and ran hops 43, 46 and 54 in
memory on every load. The repo's own fixtures were the only prior-schema files in existence.

**Deliverables.**

- **The examples re-stamped at v55, first, through the chain still standing.** `migrate(raw)`
  written back at the same `indent=2`, so the diff is only what the hops touch (16–111 lines
  per file, nearly all the v46 cg-case reshape) and the hand-authored key order survives.
- **`migrations.py` rewritten as a gate.** `MIGRATIONS = {}`, `SUPPORTED_FLOOR =
  SCHEMA_VERSION`, and `migrate` raising the new `SchemaVersionError` — a `ValueError`, so it
  lands in the documented error contract and every front-end's existing load handling reports
  it with no new branch — for anything older, newer or unversioned, naming both versions.
  `source_schema_version` moved here from `io.py` and now answers `-1` for an unversioned
  dict rather than defaulting it to the floor: an unstamped dict is not an old project file,
  it is one nobody wrote as a project file, and the gate has to be able to say so.
- **One decider.** The gate sits inside `io.project_from_dict`, the funnel CLI, both GUIs and
  every test load through. `io.schema_status`, `app_shell.project_state.apply_schema_check`
  and the JSON editor's copy of the same classification are deleted; `safe_load` keeps the
  dict-reader signature #68 gave it and reports the refusal through the error path it already
  had. `read_project_dict` stays — that split was right for its own reasons.
- **The v0 bare-engine branch and `is_project_dict` retired.** A dict with no
  `schema_version` is refused by the gate, which discriminates a foreign file better than the
  key-set intersection did, and the reader no longer makes the distinction at all.
- **Eleven frozen legacy fixtures deleted**, leaving `tests/fixtures_schema/v55_current.json`.
  The tests that read them were re-homed rather than dropped where the property under test
  outlived the hop: the fuselage-outline defaulting, the empennage slice properties and the
  absent-`unit_system`-is-Imperial rule are now written against current-schema dicts, because
  none of them was ever about the vintage.
- **Docs.** `PROJECT_GUIDE.md` §5 (the rule, and what changing a persisted dataclass now
  requires), `00_program_overview.md`'s error-handling table, `GUI_design.md` §10's load path,
  `CONVENTIONS.md`'s SSOT row for the two twice-persisted quantities (its guard cited a hop
  test that no longer exists), `PROGRAM_SPEC.md`'s cg-case note, and the fields-hash
  tripwire's own failure message, which told the next developer to write a hop.

**Test / Acceptance.**

- Output-neutrality of the re-stamp proved two ways before anything was deleted: the `Project`
  loaded from each pre-regeneration file and from its replacement are **identical dicts**, all
  six fixtures; and `tests/fixtures_imperial/digests.json` — every deliverable channel of every
  example — did not move. Decision **G-3b**'s own guard (the `FLIGHT`-tagged set equals the
  pre-hop `flight_loads.cg_cases`) was re-run against the pre-regeneration files and passed on
  all six, flight and ground, then retired with the hop it guarded.
- **New structural guard (rule 3):**
  `test_schema_guards.py::test_every_bundled_example_is_written_at_the_current_version`, read
  off **disk** rather than off a loaded `Project` — asking the built object is precisely the
  #68 defect and would make the test vacuous exactly when it matters. Mutation-tested by
  re-stamping an example at 41.
- **Second structural guard:** `test_app_shell.py::test_no_gui_decides_whether_a_file_is_readable`,
  an AST walk for the names that do the deciding (`schema_status`, `source_schema_version`,
  `SCHEMA_VERSION`, `SUPPORTED_FLOOR`, `migrate`, `MIGRATIONS`) anywhere under a GUI or the
  shell. Reading `project.schema_version` to *display* it, as the dashboard metric does, is
  not deciding and is not flagged. Mutation-tested by importing `SCHEMA_VERSION` into
  `app_shell/project_state.py`.
- `test_migrations.py` rewritten as the gate's tests: refusal in both directions and for an
  unversioned dict, the string-version trap, the refusal reaching a front-end through
  `project_from_dict`, and — so the kept machinery is not decorative —
  `test_a_registered_hop_still_runs`, which registers a hop, watches it fire, and unregisters
  it.
- Whole suite green; net ~1,100 lines removed.

**Key decisions.**

1. **Refuse, do not warn, in both directions.** The old chain let a *newer* file through on
   "read what you understand". Pre-production that means presenting a partial read of another
   build's schema as this build's answer, which is the same dishonesty as silently upgrading
   an old one.
2. **Keep the chain, empty.** Deleting the mechanism and rebuilding it from git history at
   production would be a second design exercise for no saving; `MIGRATIONS` and `applied_hops`
   cost nothing standing still, and the reversal is two edits — lower the floor, register the
   hops.
3. **The examples are the floor's only customers, so the guard is on the examples.** With
   `SUPPORTED_FLOOR == SCHEMA_VERSION`, a stale example is not a compatibility question but a
   broken example: the app would refuse to open its own bundled projects. That test is what
   makes the next version bump safe.
4. **The retired hops are recorded, not merely deleted.** The archaeology table that
   reconstructed which schema version each legacy path belonged to (M4-10) stays in
   `docs/40_history/11_completed_development_to_0.5.0.md`, and `migrations.py`'s docstring
   points at it.

- **Flutter clearance leaves the tool, and the register learns a third category
  (#79, C210-19, tier M, 2026-08-26)** — MACHLIM printed a flutter-clearance Mach
  `MFC = 1.2·MD` and its per-altitude `V(FC)` because `MACHLIM.BAS` does, and this
  project's default is to replicate what the manual prints. The owner's directive at the
  Cessna 210 build review reversed that here on two grounds: flutter substantiation is
  23.629 rather than a design load, so nothing downstream sizes to it; and the symbol is
  actively misleading to the Part 25 audience this tool now serves, who read `VFC`/`MFC`
  as §25.253's maximum-speed-for-stability pair. A quantity nobody uses, under a name
  that means something else, is worse than an absent one. Removed from the calc, the
  report series, the workbook column, the Speed–Altitude chart and the theory document;
  MNE and the V(MC)/V(MNE)/V(MD) lines are untouched and still oracle-locked, which is
  why this was surgery rather than a sweep — both quantities live in the same six lines.
  The interesting part is the record. Dropping a printed Appendix A output is not an
  approved *correction*: the corrections register exists to say "the manual is wrong and
  here is the right number", and Appendix A's MFC 0.4836 is the right answer to the
  equation the original program runs. Recorded under a new **Withdrawn from scope**
  heading that states the difference explicitly, so a later reader cannot mistake a
  narrowed replication for a fault found in the source. The drift guard is an AST scan
  over every shipped package rather than a test of the module's output, because the
  quantity was computed in two places — `mach_limit.py` and the main GUI's chart, which
  carried its own `1.2 * md` — and removing only the first would have left the line still
  drawn from a local copy. That is the same shape as the defect the removal was about.

- **A sidebar that does the arithmetic the build was doing by hand — and one
  answer to "which MAC?" (#80, C210 build review 2026-08-23, tier M,
  2026-08-26)** — The row asked for two conversions; building them found a
  defect underneath. The %MAC↔station relation was spelled four times across the
  calc package, the report and a view, and the spellings had quietly diverged
  not on the arithmetic but on the reference: WTENV honoured the weight
  envelope's typed XLEMAC/MAC override, the report's `% MAC` column read the
  planform regardless, and the two are drawn on the same chart. `mac_reference`
  now resolves that once — override, else planform (the C210-13 blank-derive
  fallback) — and carries which of the two it was, so a display can name it; the
  relation and its inverse live beside it, with an AST drift guard over every
  shipped package, and the aerodynamic consumers pass a planform reference
  explicitly rather than resolving one. The airspeed half needed the same
  completion in miniature: `convert_airspeed` only ever ran from KEAS, so the
  conversion a user actually has to make — from the KCAS on a POH or a placard —
  had no owner until `eas_from_airspeed` inverted it exactly. Both Tools are
  display-only and both delegate to those owners: the no-dual-path rule holds
  for a sidebar as firmly as for a page. Nothing in the frozen Imperial baseline
  moves, because no shipped example carries the override that made the two
  frames disagree — which is precisely why the guard builds one that does.

## Step — TAILDIST states the aero state of each case it distributes (#100, note 35, tier L, 2026-08-27)

**Objective.** Close C210-32 (owner directive: "record the alpha, beta and
rudder or elevator deflections for each case" in TAILDIST, with the
slope/effectiveness intermediates once per component): the aero state that
produced each distributed tail case was computed upstream and discarded — for
several conditions not even computed loose — and the page that distributes a
case could not say what state made it.

**Deliverables.**
- `CriticalCondition.alpha_tail_deg` / `delta_deg` / `q_psf` (AS-1): additive
  `None`-default **result** fields beside L-7's `beta_deg`; `io.py` reads
  them with the same `d.get` pattern, no migration hop, `SCHEMA_VERSION`
  unchanged (AS-7, the `beta_deg`/`body_axial_clamped` ledger class).
- Every SELECT tail emitter publishes the state its method actually used
  (AS-2): balancing the balance AT and moment-balance δ (the same locals as
  the loose oracle-checked `LoadValue`s, AS-6), unchecked the trim AT plus
  the signed full throw, checked and gust the trim state (the labelled
  increment is what separates trim from total), the unsymmetrical case a copy
  of its governing source; v-tail fin AoA 0 / −19.5 / −15 / −gust-β with the
  rudder throw, and q stamped centrally in `_htail_condition` from the
  governing point itself.
- `TailChordResult` carries the four fields across; TAILDIST renders them
  ahead of the stations (`taildist.aero_state_values`) with the AS-4 fixed
  reasons where a method defines no value (checked δ, side-gust q, h-tail β)
  and the "re-run SELECT" statement on a stale persisted set; angles and q
  are non-load units, never SF-scaled (CONVENTIONS §3).
- `taildist.component_constants`: AHT (h-tail) / AVT + EFFECTV (v-tail)
  printed once per component by calling the same owners inside the loads.
  The finite-surface slope `2π/(1+2/AR)` consolidated to
  `_vtail.lift_curve_slope` (AS-5) — the three inline `select.py` spellings
  replaced by calls, ONENGOUT renamed onto the shared owner.
- Docs: `theory_sources.md` `select`/`taildist` rows grew the published-state
  sentences; `PROGRAM_SPEC.md` TAILDIST section; the schema-guard ledger
  entry.

**Test.** `tests/test_taildist_aero_state.py` — G-AS-1: on the Appendix A
GA6, `BAL UP RETRACTED`'s structured fields equal the loose `LoadValue`s
bit-for-bit and δ matches Appendix A's −5.39° (Ch 9 case 202). G-AS-2: on
every shipped fixture the published state reconstructs the stamped
`LT25`/`LT50` through the method's own equations (rel 1e-9, per family).
G-AS-3: every TAILDIST condition states each of AoA/β/δ/q or its AS-4
reason. G-AS-4: a stale persisted set renders the "re-run SELECT" statement,
never a value. G-AS-5: the §1 per-label literals plus the one-spelling slope
drift guard. AS-8 (no load number moves) is the rest of the suite: only the
`csv/taildist` / `txt/taildist` digests changed.

**Key decisions.** The published state is the state the method used, never a
derived "total effective" one — the equivalent-gust-Δα extension is parked
with the owner's ruling (`02_parked.md`). Disclosure reasons are fixed
strings owned by `taildist` (AS-4), so "cannot supply" is a statement, not a
blank. Reading the slope/effectiveness owners from TAILDIST is not
recomputing another module's quantity (the `surface_geom` precedent); making
the slope single-source is what guarantees the printed intermediate is
arithmetically the one inside the loads (rule 3).

- **Two GUI copies that told the truth about the wrong number (#70, PB-16/PB-17,
  2026-08-25).** Both halves of this item were the same failure in different
  clothes: a widget stating something about the analysis that the analysis did
  not do. The unit radio was exempted from the project-generation stamp on the
  stated grounds that stamping it "would reset the user's unit choice on every
  project they open" — which is precisely what it is for, because `unit_system`
  is a field of `Project`; the exemption was argued from the widget's subject
  matter rather than from where its value lives, and the result was that loading
  an SI file into an Imperial session edited the file on the way in and flagged
  it unsaved. The wing-area copy was registered against
  `geometry.parametric.wing_area_sqft` while STRSPEED integrates the
  `speeds.wing_surface` planform, so the disabled widget — a widget whose whole
  claim is "this is what the calc uses" — displayed 500.0 against the 497.75 in
  the answer. Fixing the second exposed why it was possible: four separate
  implementations of the same strip integral, guarded by a sweep that scanned
  `sloads/modules/` alone and allowlisted two of the four, so `validation.py`
  grew a third outside its view and the GUI a fourth number that was not the
  integral at all. The integral now has one owner (`planform_area_sqft`), the
  callers keep only their policy for an absent planform, the sweep covers the
  package, and the registry can resolve an external owner's value through the
  same function the calc calls (`EXTERNAL_VALUES`) — which also made the row's
  conditional nature expressible: with no wing surface the field stops being
  inert and becomes what STRSPEED reads, so it goes live rather than staying
  disabled against the advice of its own `MissingInputError`. Two smaller
  defects came out with them, on the generalize-on-first-find rule: the
  wing-area mismatch warning was tagged for Configuration & Layout twice, so
  that page said it twice and Design Speeds never; and captions quoting an
  owner's current value quoted it in Imperial beside a widget rendering SI.

- **The weight estimate says what reads it, and stands beside the weights the project uses (#78, C210-9, tier M, 2026-08-26)** — The Cessna 210 build stopped at the weight-estimation block and asked three questions —
what does this feed, is it either/or with the item table, are the two compared — and the
page answered none of them (C210-9). The answers were "nothing", "no" and "no", but they
were only recoverable by reading the code: `PROGRAM_SPEC` said WTESTIMA *feeds* WTONECG
and WTENV, which is true of the original suite's data flow and false of this
implementation, where the flow runs through a weight data base the user authors and the
estimate reaches it only through a seed button. Fixed at both ends — the module now owns
the sentence (`weight_estimate.ADVISORY`) so both front-ends and the spec say the same
thing, and `compare_with_itemized` puts the estimate beside the weights the project
actually uses, drawing each entered figure from its existing owner rather than re-summing
the item table. The comparison is deliberately unthresholded: a GA correlation and a
weighed airplane are not expected to agree, +22 % on the C210 is scatter rather than
error, and a page that ruled on the gap would be answering a question the finding did not
ask. The other half of #78 — the seed button — turned out to have shipped long before the
review that filed it as missing; what survives there is that its rows arrive silently
zero-stationed and untagged and that it wipes an authored table, which is main-GUI work
behind the `app/views/` freeze.

- **The stall fill gets a second caller, and the balance gets a refusal (issue
  #81, C210-23, tier M, 2026-08-24)** — The M1-1b fill that keeps the CLmax trio
  and the per-config stall CLs consistent was written into `__post_init__`, which
  is the right place for a slice that is built in one go and no place at all for
  one that is assembled field by field. The oracle GUI does the latter: it seeds
  the coefficient sets blank and writes the CLmax trio afterwards, a widget per
  rerun, so the constructor never ran a second time, the live sets kept a stall CL
  of zero, and both Flight Envelope and SELECT died on a division by it. The
  workaround that kept the C210 build moving — save, reload — is the tell: the
  loader constructs, so the file was always right and only the session was wrong.
  The fix needed no new call site. `sloads.derived` already existed for the
  neighbouring problem (a derived slice whose only writer was one GUI, #62/PB-1)
  and the oracle form already calls `refresh_derived` after every persist, so the
  fill was extracted to `AeroCoefficientsInput.normalize` and registered there;
  what the module gained was a second table, because a *derived* slice and a
  *normalized* one are not the same thing — the first is a result the project
  could rebuild from scratch and the field registry excludes from the input set,
  the second is authored input whose fields fill each other in, and letting
  `aero_coeffs` into the first would have put user input under the G5 reduction's
  drop-and-re-derive. Beside the fill, the balance now refuses: `balance_configs`,
  the choke point `build_envelope` and `trim_sweep` share, names the set, the
  quantity and the page rather than letting a stall speed divide by zero — the
  #84 lesson, that a condition the airplane has not stated is refused rather than
  computed, applied one layer down. The sweep item that came with the issue could
  not be closed as it was written. `flaps_down.neg_stall_cl` is not a fill that
  was forgotten; it has no source to fill from, since the schema carries no
  `clmax_flap_neg` and the clean negative CLmax is a different number — Appendix
  A's landing set prints −0.41 against a clean −0.59, so the obvious fill would
  have injected a 44 % error into the flaps-extended negative band. Left at zero
  it does not crash but clamps that band at CL = 0, which the balance reports as
  a quietly small load, so it is now a validation warning and the schema field
  that would let it fill symmetrically is filed as its own item.

**One consistency-warning renderer for both GUIs (issue #82, C210-35, tier M,
2026-08-24).** The finding was that the oracle GUI renders no part of the
`consistency_warnings` channel; the cause turned out to be one layer down. The
`page` tag each warning carries was never checked against anything, and two tags
had gone stale — `weight_cg_inertia`, left behind when the weights page became
`weight_mass` at Step G3, and `wing_geometry`, left behind when Step G1 merged
that page into `configuration_layout`. Between them they carried 19 of the
module's checks, 14 in the weights group alone, and they kept working in `app/`
only because two views compared against the old strings by hand. So the channel
was not merely unrendered in the second GUI: its largest group was propped up by
a literal in one file and was dark everywhere else, which is why a contradictory
`wing_fraction` entry could survive an entire build review unshown and cost three
round-trips to diagnose from the saved file. Both halves were fixed at the level
that makes them structural rather than patched. Every tag is now a
`sloads.workflow.STEPS` key — `workflow.py` is the nav SSOT, so a tag naming
anything else names a page no GUI has — with a rule-3 guard over both the
`PAGE_*` constants and the tags the live checks emit. And the rendering has one
owner, `app_shell.components.render_consistency_warnings`, called by
`page_header` from the step key it already holds: the same place, and for the
same reason, as the applicability banner. That choice is what makes the fix
cover all fourteen oracle pages and every main-GUI view at once instead of
page by page, and it removed the six open-coded loops rather than adding a
seventh; `aero_coefficients.py` and `export_report.py` were migrated onto
`page_header` with `banner=False` so nothing but the warnings changed on them.
Warnings tagged `export_report` were deliberately left main-GUI-only by owner
call: the oracle GUI has no export page and no way to set a safety-factor
override, so a warning about one concerns state it can neither create nor act on,
and the guard permits a tag that is a workflow key without being an oracle step.
Verified on the C210 build file: all six of the warnings the owner saw in the
main GUI now render on the oracle GUI, on the pages that own them.

**Flap slipstream applied to the deliverable (issue #85, C210-47/C210-40 family,
tier M, 2026-08-24).** The C210 build review reached the flap page with an engine
record present for the first time in the project's history — no prior fixture
carried both a flap slice and an engine — and the FAR 23.457(b) block finally
computed. It computed, printed, and was then discarded: `build_flap` exported
`max(critical, gust-combined)` as the single flap case, so the deck shipped 972.8
lbs-ULT against a slipstream design load of 1,156.6, understating shipped content
by 19 %. The fix delivers the slipstream as a second case beside the
gust-combined one rather than folding it in, on two owner rulings taken in chat
before code (rule 1): the two are **independent** worst cases and are enveloped,
never stacked; and the factored load is stated over the whole flap because
`ControlSurfaceLoadResult` has no spanwise dimension — the review's preferred
per-strip banded envelope would be an L-tier schema change, and inventing the
flap's span extent from a project that leaves `inboard_y_in`/`outboard_y_in`
unset would violate T-17. One implementation rule was settled on the physics
rather than by owner call: the factor is `(Vss/VF)²`, so it scales the VF-governed
condition, not the stall-speed ones — a distinction with no numeric effect on the
manual's airplane (whose critical condition is 2G at VF) and a real one on any
airplane where a stall-speed condition governs. Closing the item exposed a second
defect in the same file: the main GUI's slipstream block tested a display label
against a key-keyed dict and so had never rendered at all, which is why C210-47
was verified through the oracle GUI's report path. It was folded in under rule 4,
and since a sweep found it to be the only instance in `app/views`, its drift
guard is stated as an absolute. No printed oracle exists for an applied
slipstream load — Appendix A prints the factor and the gust-combined 819 lb and
nothing built from the two together — so the definition of done is the stated
closure gate rule 2 requires in place of one: `factor × max(LF 2G-at-VF, LF
gust-at-VF)`, not the factors stacked, with an engine-less project exporting
byte-identically to before. The frozen Imperial digests moved on the flap
channels of the propeller examples, which is the intended change announcing
itself, and were regenerated.

- **The load boundary types its own numbers (issue #76, C210-7 residual, tier M,
  2026-08-24)** — The reported defect was narrow: a project saved while the
  oracle GUI's geometry grid was handing text back kept its wing corners as
  strings, and reloading it re-crashed WINGGEOM with `TypeError: unsupported
  operand type(s) for -: 'str' and 'str'`. The review's mitigation — the repaired
  grid fixes the corners on the next Geometry render — turned out to hold only in
  the GUI the defect was found in: in the main GUI the same strings kill
  `to_display` on the Configuration & Layout page, which is the page that would
  have done the repairing, so the file was unopenable there in a way nothing had
  noticed. That made the loader the only boundary worth fixing, since the module,
  both front-ends and the CLI all sit behind it. Reading the model's own
  annotations for the class rather than the field then showed how thin the
  existing coverage was: of eighteen numeric containers in the schema, exactly one
  — `FlightLoadsInput.altitudes_ft` — coerced its members, and the rest, including
  three `hinges_span_in` lists that feed the sbeam control-surface export and both
  engine CG vectors, took whatever JSON held. So the rule is now stated once and
  derived: `io._numeric_shape` reads the shape off the dataclass hint, `_filtered`
  applies it to every splat, and the three readers that name their fields
  explicitly call the same coercer instead of keeping a second copy that could
  drift. Text that parses is repaired out loud through the load path's existing
  warning channel (one message per field, not per member — a twenty-point polyline
  is one event), which keeps a crash-damaged file openable so the grid can finish
  the repair; text that does not parse raises `ValueError` naming the field and the
  member, which the GUI already renders as `st.error` rather than a traceback.
  Scalars were left out deliberately: the class that produces this damage is the
  grid-writable container, and a blanket numeric coercion would have to reason
  about `Optional`, enums and bools for no observed defect. The guard is the whole
  fixture rather than the one field — the GA-6 project reloaded with every list
  member written as text must return bit-identical values from seventeen modules.

- **A 23.367 applicability gate, single-sourced across the module, both GUIs and
  the coverage table (issue #84, C210-43, tier M, 2026-08-24)** — The finding was
  a false verdict: on the C210's centreline single, One Engine Out printed zero
  tail load and zero yaw rate at all three speeds while stating the airplane was
  uncontrollable and likely below VMC. The arithmetic was never wrong. FAR
  23.367's forcing is `thrust · BLENG`, and with the only engine at BL 0 that
  product is identically zero, so the simulation marched sixty seconds of nothing
  and then reported — correctly, on its own terms — that recovery never happened.
  Every intermediate around it verified to the digit, which is precisely why the
  result was believable. What was missing was the question that comes before the
  simulation: does this airplane have the condition at all. The predicate turned
  out to exist already, in `report/coverage.py`, whose 23.367 row has always
  marked the C210 not-applicable — so the tool held the right answer in one place
  and acted on the wrong one in three others. The fix was therefore consolidation
  rather than a new rule: `applicability.engine_failure_not_applicable` states it
  once, and the module's refusal, the oracle GUI's withheld form and the coverage
  row are readers of it. Coverage's old test was also weaker than the physics —
  `len(engines) > 1` calls a twin applicable even when the *failed* engine is the
  centreline one, which is the same zero moment arm — so the shared predicate
  covers a case none of the three had. Coverage keeps its own turbopropeller
  clause layered on top, deliberately: 23.367(a)'s regulatory scope is a
  statement about which airplanes must show the condition, while the module
  models any propeller installation, and `PROPELLER_ONLY_NOTE` already records
  that split. Two boundaries were drawn rather than blurred. An empty engine list
  is *not* an applicability finding — it is an unfinished project, and the
  module's existing "needs Project.engines" refusal says so better — so the
  predicate stays silent there unless the layout settles it. And the GUI table
  keying pages to predicates lives in `sloads`, not the front-end: the oracle
  GUI's own drift guard rejected the first attempt for writing a workflow step
  key as a literal (OG-2/G2), and the key set is guarded against the #82 stale-tag
  defect in the same move.

- **A row counter that deleted, and a row that stopped the calc (code review
  2026-08-24, tier M)** — The 0.7.2 code review of `oracle_app/` and `app_shell/`
  found the shell in good order and two live defects, both inside eight lines of
  one function. `render_table` sized a list record by reconciling the model to a
  number input, against the project's own attached list, so the widget wrote to
  the project in both directions during a render pass. Counting down popped
  entered rows — 21 of 24 weight items on one keystroke, no confirmation, no undo,
  blanks on the way back up, and a truncated project that saved — which is the
  same failure the generation stamp was built for at #51, closed there for the
  path where Streamlit's retained state caused it and left open for the path where
  the user does. The same pop also fired on a plain page revisit whenever the
  project had been mutated rather than replaced underneath the retained count, the
  case `02_parked.md` L-8d parks and #78's seed button was about to trigger.
  Counting up was the more surprising half: the seeded row joins the project
  immediately, because `commit_pending`'s blank-record rule governs records a pass
  creates and not rows appended to a list that is already attached — and for the
  CG-case table that row is a `FLIGHT`-tagged case of zero weight, which every
  balance divides by, so asking for one more row killed the entire flight envelope
  and SELECT. What made that invisible was a third thing: the results renderer
  caught `ZeroDivisionError` as *not ready yet*, so a page that had been working a
  second earlier said only that it was unfinished. The fix keeps the counter (it
  is what the journey test types projects through) but makes it non-destructive —
  the model wins, and a deletion is a named button that says which rows go — and
  puts the refusal where it belongs for every writer rather than for the GUI that
  happened to produce it: `build_envelope` names a weightless case, `validation`
  warns before anything runs, and `ZeroDivisionError` is out of the not-ready
  catch, which is the narrow half of #71. The page's caption, which had promised
  that incomplete rows are not saved, now states the rule that actually applies to
  each kind of row.

- **Whole-project results zip in the shared sidebar (C210-45 / backlog 19c,
  tier M, 2026-08-23)** — The C210 oracle-GUI build review left the owner
  collecting thirteen pages of results one hand-clicked download at a time;
  no control delivered a complete results set. The shared sidebar now builds
  one zip per project: every registered module run in registration order,
  each contributing the CLI's own text report and load-case CSV (same owners:
  `module_text_report`, `io.load_cases_csv` + `csv_comment_block`, results
  stamped from the governing safety-factor table exactly as
  `registry.run_all_modules` does), plus the serialized project and a
  `MANIFEST.txt` naming every module's outcome — skip-and-manifest per the
  error contract (`MissingInputError` = skipped, `ValueError` = failed and
  said so; anything else propagates, M2R-8). The builder
  (`sloads/report/results_zip.py`) is pure and clock-free, so two builds of
  one project are byte-identical; `tests/test_results_zip.py` asserts on the
  zip bytes (manifest completeness, member pairing, ULT header, basis
  statement, project round-trip, determinism), and the oracle GUI's G7
  call-site gate was extended to admit the zip by its naming owner with the
  payload gate stated in place.

## Release cut: **sloads 0.8.0** (oracle-GUI development: derive-by-default, the user guide, and the landing load factor entered as N), tag `v0.8.0`, 2026-08-28

**Objective.** Close band B — **oracle-GUI development**, the plan the 0.7.2
re-cut set — and cut when it is empty. The band was extended twice in flight by
owner ruling: 2026-08-27 with the landing load-factor defect and its sweep
finding (#123/#124, note 37), and again the same day with the four cut-blocking
rows of the
[production-release review](../50_reviews/2026-08-27_oracle_gui_production_review.md)
(#126–#129). 27 issues closed on the milestone.

**Deliverables** (the `[0.8.0]` changelog section is the release note):
- **Derive-by-default overrides** (#97, note 36, tier L, schema v56): one
  mechanism for the duplicated-input class — a field the calc can derive is
  derived unless overridden, the registry's `derived_from` links drift-guarded;
  **#98** rendered or captioned every hidden required field over it, and
  **#95** re-shaped the geometry pages' presentation on the same mechanism.
- **The oracle GUI user guide** (#96, note 34, tier M): six stages, chapters
  1–14, both worked-example appendices (the C210 and the guide-built
  baron_58) — the build that surfaced #121/#122, both filed with bodies
  (rule 5) rather than fixed in the writing session.
- **The landing load factor is entered as N, not NLG** (#123, note 37, tier L,
  schema v57 — a *semantic* hop: `N = gear_load_factor + lift_factor`, old
  saves migrated by key). The wing-lift factor moves the gear reaction again;
  the Appendix A p236 oracles pass unmodified (G-LF-1). Its HP-precedence
  sweep finding closed as **#124**: one owner for the max-continuous-HP rule,
  read by module and GUI alike.
- **The production-release review and its blockers**, all tier S, closed
  in-band: **#126** the Tools %MAC↔station input through the unit boundary;
  **#127** the smoke gate boots *both* front-ends (the release whose headline
  was the oracle GUI had a §3.5 gate booting only the other one); **#128** a
  design note's status cannot claim unbuilt work (notes 32/35 corrected, the
  claim guarded); **#129** the `use_container_width` migration taken whole
  (73 sites, both GUIs and the shell), the Streamlit floor moved to the layout
  API the code calls, and the **dependency ceiling policy stated**: no upper
  bound, deliberately, resting on CI's unpinned install — all three halves
  drift-guarded.
- **Maturity stated once:** `Development Status :: 4 - Beta` (the classifier
  describes the whole distribution) with the owner's mixed-state sentence in
  `app_shell.components.RELEASE_STATE`, consumed by both GUIs' About panel and
  pinned verbatim in `README.md`/`CAPABILITIES.md` by the doc-currency guard.
- **Also in the band:** the pre-production schema floor (#93, tier L — read
  only the current `SCHEMA_VERSION`, migrations become a gate); TAILDIST
  states the aero state of each case it distributes (#100, note 35, tier L);
  flutter clearance leaves the tool (#103); the sidebar tools section; the
  page-order dependency statements; and the oracle-GUI defect closures of the
  cycle (#70, #72, #76-class residue, #78's advisory caption among them).
- **Version** `0.7.2` → **`0.8.0`** (MINOR: new GUI capability). **Schema v55
  → v57** in two recorded hops (v56 additive, v57 semantic), older saves
  loading through both.
- **Changelog cut** — `scripts/build_changelog.py 0.8.0 --date 2026-08-28`:
  **39 fragments** consumed into `## [0.8.0]` across Added / Changed / Fixed /
  Removed, **14 history entries** rolled to the top of this file, a fresh
  empty `[Unreleased]` opened; released sections byte-untouched.
- **History roll** (`RELEASE_PROCESS.md` §4.3): notes **35, 36, 37** carry
  *SHIPPED* status headers and move to `40_history/`; notes 32/34 read
  AGREED…BUILT and stay with their open GUI milestones. The live file stands
  at well under the 1,500-line threshold — no freeze.
- **Verification baseline:** unchanged from
  [`36_verification_baseline_0.7.0.md`](36_verification_baseline_0.7.0.md).
  No calc-math change on the FAR 23 path: the one semantic change (landing N)
  is oracle-invariant by its own gate (G-LF-1, p236 assertions unmodified) and
  the delivered-load consequences are pinned by G-LF-2…G-LF-6 rather than by a
  new baseline.
- **Gates at cut:** `pytest` **3060 passed / 30 skipped / 1 xfailed / 0
  failed**, `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/
  scripts/` clean, `mypy` clean (`sloads/`), `scripts/smoke_test.sh` **PASS**
  (both front-ends boot, the oracle through its console script),
  `scripts/backlog_issues.py check` clean, no open CRITICAL/MAJOR review
  findings.

**Key decisions.** *The review ran before the cut started this time.* 0.7.2's
lesson — a release nearly cut is not cut — became 0.8.0's process: the
production-release review was commissioned against the release *claim* ("oracle
GUI production ready") before any cut step ran, found the claim four small
fixes short, and every blocker closed in-band with its structural guard. The
classifier ruling (`4 - Beta`) chose the honest whole-distribution statement
over the flattering per-front-end one, and put the sentence that carries the
nuance under one owner. The ceiling-policy ruling took the
`use_container_width` migration **whole** across both GUIs — splitting it by
fix site would have left half the removal bomb armed — and recorded "no upper
bound" as a decision with the CI mechanism that makes it safe, not an
omission. **Band B retired with the cut; band B2 (0.9.0 — main-GUI
development, anchored by #29) is the milestone in flight.**

## Release cut: **sloads 0.7.2** (the bugs the build review found, and the review that found two more), tag `v0.7.2`, 2026-08-25

**Objective.** Ship the seven `b`-class defects the 0.7.1 Cessna 210 build
review classified as *bug → 0.7.2*, then — at the owner's direction, with the
cut already started and walked back — **review the oracle GUI's code** before
closing, and re-cut the table for the two GUI milestones that follow. The
milestone is therefore defect-only by construction: no new capability, no calc
math changed on the FAR 23 path, no schema hop.

**Deliverables** (the `[0.7.2]` changelog section is the release note):
- **The seven carried defects**, each closed with its own tiered trail:
  **#82** the oracle GUI's dark consistency-warning channel and two `page` tags
  naming pages that no longer existed (19 checks propped up by stale names);
  **#86** Tail Span Loads publishing lb-in moments through the ft-lb `torque`
  channel — every figure 12× its label in both systems; **#85** the flap
  slipstream amplification computed, printed and then *not applied* to the
  delivered load, in a block that had never rendered at all; **#83** the
  23.457(b) slipstream case skipped in silence; **#84** One Engine Out
  simulating a condition a single-engine airplane cannot have and reporting a
  false *uncontrollable* verdict; **#76** the load boundary storing whatever
  JSON held, so a grid's text corners reloaded and re-crashed WINGGEOM; **#81**
  the M1-1b stall fill that only ran at construction, leaving the from-blank
  session dividing by a zero stall CL.
- **The code review** —
  [`../50_reviews/2026-08-24_oracle_gui_code_review.md`](../50_reviews/2026-08-24_oracle_gui_code_review.md):
  a code-level pass over `oracle_app/` + `app_shell/` (2,676 lines), the side
  the build review could not see. It found the shell sound and **two live
  first-order defects inside eight lines of one function**, closed as **#88**:
  the row counter deleted entered rows with no confirmation or undo (21 of 24
  weight items on one keystroke, saved in that state), and the row it *added*
  was a zero-weight CG case that stopped the whole flight envelope — reported
  as "cannot run yet", which is why nobody saw it. The narrow half of **#71**
  (`ZeroDivisionError` out of the not-ready catch) came with it.
- **The re-cut** (`00_backlog.md`, priority table): **0.8.0 — oracle-GUI
  development**, **0.9.0 — main-GUI development and bug correction** (#29 and
  its findings move there), 1.0.0 unchanged. Placement is **by fix site**, so
  shared-`app_shell` work rides with the oracle milestone; **#89** was filed
  for the review's two latent findings.
- **Version** `0.7.1` → **`0.7.2`** (PATCH: defect fixes only, **no calc-math
  change and no schema change** — `SCHEMA_VERSION` stays at v55).
- **Changelog cut** — `scripts/build_changelog.py 0.7.2 --date 2026-08-25`:
  **8 fragments** consumed into `## [0.7.2]` (Fixed only — the first
  single-section release), **6 history entries** rolled to the top of this
  file, a fresh empty `[Unreleased]` opened; released sections byte-untouched.
- **History roll** (`RELEASE_PROCESS.md` §4.3): no `30_future/` note carries a
  *shipped* status header this cycle, so nothing moved on that rule — but the
  live file reached **1,516 lines**, past the 1,500 threshold, so the 0.7.0
  cycle and cut were frozen verbatim into
  [`37_completed_development_to_0.7.1.md`](37_completed_development_to_0.7.1.md)
  (1,221 lines) and the live record is back to **313**.
- **Verification baseline:** unchanged from
  [`36_verification_baseline_0.7.0.md`](36_verification_baseline_0.7.0.md).
  No calc math moved on the FAR 23 path: every fix is a boundary, a refusal, a
  render or a units label, and the Appendix A oracles are the same tests
  passing on the same figures. The two changes that touch delivered numbers do
  so by *correcting* them — #85's slipstream factor now multiplies the flap
  load it was printed beside, and #86's moments now carry the unit they are in
  — and both are pinned by their own tests rather than by a new baseline.
- **Gates at cut:** `pytest` **2765 passed / 30 skipped / 1 xfailed / 0
  failed**, `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/
  scripts/` clean, `mypy` clean (`sloads/`), `scripts/smoke_test.sh` **PASS**,
  `scripts/backlog_issues.py check` clean, no open CRITICAL/MAJOR review
  findings.

**Key decisions.** *A release that is nearly cut is not cut.* The changelog
build had already run — fragments consumed, history rolled — when the owner
stopped it to review the GUI's code first; the cut was reverted wholesale and
the milestone gained two defects it would otherwise have shipped with, one of
which destroys the user's weight database on a single keystroke. The review
that found them was scoped *away* from the ground the build review had already
covered, which is why it read code rather than pages. Two rulings of record
came out of the re-cut. Rows are placed **by fix site**, not by which GUI
benefits, so the shared shell is worked once. And the **mission stays at
1.0.0**: the full-span balanced free-free airplane model — the deliverable the
backlog's own §Mission names first — now sits behind two GUI-focused releases,
a choice taken explicitly with the alternative offered and declined, and
written into the table as ruling 4 so a later reader finds a decision rather
than a drift. Finally, the closure discipline caught its own author twice this
cycle: a table row added without an issue behind it failed
`test_backlog_issues` at #88's close, and narrowing the results catch to
`MissingInputError` alone — which the review had recommended — broke the
documented error contract and was caught by `test_oracle_journey` before it
could ship.

## Release cut: **sloads 0.7.1** (the beta tested by building an airplane in it), tag `v0.7.1`, 2026-08-23

**Objective.** Test the 0.7.0 oracle-GUI beta the way a first-time user would —
by **building a Cessna 210 from a blank project, by hand, in the oracle GUI**,
every value typed by the owner from public data — and ship what that exercise
found. The milestone's content is therefore not a feature list chosen in
advance: it is whatever a real build surfaced, classified as it was found
(**a** interface broken → pulls the release back; **b** bug → 0.7.2; **c**
development → backlog), with each finding's body written in the session that
raised it.

**Deliverables** (the `[0.7.1]` changelog section is the release note):
- **The build review** —
  [`../50_reviews/2026-08-23_c210_oracle_gui_build_review.md`](../50_reviews/2026-08-23_c210_oracle_gui_build_review.md):
  all **fourteen** oracle pages built and reviewed, then the G6 hand-off into
  the main GUI through Balanced Cases and Tail Span Loads. **51 findings**,
  every one with a body and a disposition — **a = 2** (both fixed in-session,
  **none surviving**, so 0.8.0 keeps its planned content), **b = 7**
  (#76/#81/#82/#83/#84/#85/#86, the 0.7.2 list), **c = 42** (backlog rows
  #73/#77/#78/#79 and band C row 7a).
- **The two `a`'s, fixed in the cycle:** the oracle grid's **write-back
  remount race** (C210-4/C210-11 — every committed cell rebuilt the frame,
  changing `st.data_editor`'s widget identity, so a keystroke in flight was
  discarded; a typed `-25` became `25`; the 21-row items table was
  "impossible to enter"), fixed with a per-visit **stable frame**; and a
  polyline grid **typed from blank** crashing the Geometry page on string
  corners, fixed with a float-typed frame and a parsing boundary.
- **The results zip** (C210-45, tier M, above): the one control that delivers
  a project's complete results set, in both GUIs.
- **Two doc/UX closures:** every grid page states that a part-filled row is
  not saved; SELECT's search scope stated in `00_theory_sources.md` (the
  candidate pool is the entire balanced V-n matrix).
- **Standing owner rulings produced by the exercise:** the **C210-15 fidelity
  ruling** — the oracle GUI's fidelity target is the *analysis contract*, not
  the original prompt sequence, so UX may improve freely while consumed values
  stay correct; the OG-1 scope bound with its display-only-utility refinement;
  and the C210-31 **collapsed-override** pattern as the template for every
  derivable duplicate.
- **Version** `0.7.0` → **`0.7.1`** in `pyproject.toml` (PATCH: defect fixes
  plus one additive GUI capability, **no calc-math change and no schema
  change** — `SCHEMA_VERSION` stays at v55).
- **Changelog cut** — `scripts/build_changelog.py 0.7.1 --date 2026-08-23`:
  **5 fragments** consumed into `## [0.7.1]` (Added / Changed / Fixed), **1
  history entry** rolled to the top of this file, a fresh empty `[Unreleased]`
  opened; released sections byte-untouched.
- **History roll** (`RELEASE_PROCESS.md` §4.3): nothing to move — no
  `30_future/` note carries a *shipped* status header this cycle — and the
  live file is **1,245 lines**, under the 1,500-line threshold, so no archive
  was frozen.
- **Verification baseline:** unchanged from
  [`36_verification_baseline_0.7.0.md`](36_verification_baseline_0.7.0.md).
  This release changed no calc math: the oracle tests are the same tests
  passing on the same figures, and the one new output path (the results zip)
  renders through the existing report/CSV owners rather than computing
  anything. A new baseline document would restate 0.7.0's numbers verbatim,
  which the §4.5 rule exists to avoid.
- **Gates at cut:** `pytest` **2725 passed / 30 skipped / 1 xfailed / 0
  failed**, `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/
  scripts/` clean, `mypy` clean (`sloads/`), `scripts/smoke_test.sh` **PASS**,
  `scripts/backlog_issues.py check` clean, no open CRITICAL/MAJOR review
  findings.

**Key decisions.** *An interface is tested by building something in it, not by
reading it.* Thirteen of the 51 findings were reachable only because a real
airplane's data disagreed with the form's assumptions — the slipstream
amplification that no prior fixture could trigger (no project carried both a
flap slice and an engine), the point-mass wing fuel, the tail moment column
mislabeled by a factor of twelve. The classification rule was set **before**
the build and honoured: the `a` class was defined to pull the release back,
two `a`'s were found, both were fixed in the session that found them, and the
0.8.0 plan therefore stands unchanged — a rule that costs nothing when it is
never triggered would not have been a rule. Three closings were the owner's
call rather than the checklist's: the comparison against the bundled
`examples/cessna_210.project.json` is **deferred** past the cut (the
no-consult rule stays in force until it runs), the review was closed
**without** a final save of the G6 session edits — so the project on disk
predates them and the edit list in closing check 2 is the record — and no
Export & Report artifact was pasted, leaving the balanced-case equilibrium
gate (worst force residual **0.068 %** of n·W against a 2.5 % limit, pitch
**0.001 %** against 1 %) as the physics close of record. Each is written into
the review's status block as a limit on what the milestone demonstrated,
rather than left for a reader to infer from a missing artifact.
