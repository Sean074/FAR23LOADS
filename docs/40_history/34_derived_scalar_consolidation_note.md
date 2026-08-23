# Note 33 — Derived-scalar consolidation: one owner per quantity, in the dataclasses

**Status: SHIPPED** (2026-08-21; PROPOSED and AGREED the same day). Tier **L** — a
contract change to the `Project` slice dataclasses and to calc function
signatures. [`CLAUDE.md`](../../CLAUDE.md) rule 1's gate was met before any code
was written.

**Owner's framing (2026-08-21):** *"Explain why we need non-owner duplicate
copies. Can they be consolidated? Change to the existing tests is acceptable, and
preferred to having redundant or potentially confusing redundant variables."*
This note answered the first question with a measurement and proposed the
consolidation the second asks for; **it shipped on 2026-08-21** and §7 records
what the implementation changed about it.

Conventions cited throughout: [`CONVENTIONS.md`](../10_standard/CONVENTIONS.md)
§7 (single-source-of-truth table — every cross-cutting quantity gets a code owner
**plus** a drift-guard test, never a prose rule); `CLAUDE.md` rule 3 (make it
structural) and rule 4 (generalize on first find). Prior art:
[note 32](../30_future/32_oracle_gui_note.md) OG-7/OG-8/OG-14 and the field registry they
built; finding **CR-A-2 `[MAJOR]`** in
[`../50_reviews/2026-08-20_critical_review.md`](../50_reviews/2026-08-20_critical_review.md).

---

## 1. What was measured

`field_registry.quantities()` reports **10 quantities with ≥2 independently
editable copies**. They are not one class, and the difference decides the remedy.

| Class | Quantities | Stored twice? | Resolved at run time? |
|---|---|---|---|
| **A — cache of a single stored value** | `flight_loads.mac`/`wing_area_sqft`/`xw`/`zw`, `wing_mass.dihedral_deg`/`wrp_waterline`, `landing.wing_area_sqft`, and the gear block `landing.main_gear`/`nose_gear`/`tread_in` | **No** | Yes — `derived_geometry.sync_geometry_derived` and `landing._effective_gear_input` |
| **B — genuine override** | `vtail_loads.gross_weight_lb`, `speeds.weight_lb`, `weight.envelope.mac` | Yes | Partly (see §2.3) |
| **C — entered twice, nothing reconciles them** | `speeds.mach_limit.shoulder_altitude_ft` vs `speeds.shoulder_altitude_ft`; `geometry.empennage.vtail.airplane_length_in` vs `htail.airplane_length_in` | Yes | **No** |

### 1.1 Class A is already consolidated *on disk*

This is the finding that reframes the whole item. `io.py` deliberately refuses to
write every class-A field:

* `flight_loads_to_dict` emits four keys and omits `mac`/`wing_area_sqft`/`xw`/`zw`
  — *"a legacy file's stored copies are ignored on load and re-derived, so
  save→reload is a no-op."*
* `landing_to_dict` pops `main_gear`, `nose_gear`, `tread_in` and `wing_area_sqft`
  — Step G6b's *"single stored home"*.
* `wing_mass_to_dict` pops `dihedral_deg` and `wrp_waterline`.

So `project.json` already holds each quantity **once**. The duplication that
CR-A-2 sees is in the *dataclass API*, and it reaches the user only because the
field registry lists both copies as enterable fields — which is why both GUIs
render two editable widgets for one number.

### 1.2 Why the cache field exists

Stated in `sync_geometry_derived`'s own docstring: it is *"a no-op for any slice
whose backing geometry is absent, so a directly-constructed test project that set
the value on the slice keeps working."* The consumers keep the matching fallback
(`landing._wing_area`, `structural_speeds._wing_area_sqft`, both raising
`MissingInputError` when neither source is present).

That fallback is real, but it does not require a **public, editable** field. All
six shipped examples carry a wing surface, a parametric wing and (five of six) a
`geometry.landing_gear`; both GUIs require the Geometry page before the pages that
consume these scalars. The fallback's only live client is hand-constructed test
projects.

### 1.3 A second reason the cache field exists — signature shape

`wing_inertia.inertia_units(geom: SurfaceInput, wm: WingMassInput)` receives the
**wing surface**, not `GeometryInput`, and `wrp_waterline`/`dihedral_deg` come
from the *parametric* slice the surface does not carry. The copy on
`WingMassInput` is how those two scalars reach a function that cannot look them
up. Note that the sibling call already does it the other way —
`net_loads.air_load_distribution(geom, aero, cl, v, wrp_waterline, dihedral_deg)`
takes them as parameters — so the target shape exists in the codebase already.

## 2. Three defects found while measuring

These are consequences of the duplication, not separate items, and each is
evidence for consolidating rather than decorating.

### 2.1 One quantity, two precedences

`landing._wing_area` prefers **the slice copy** and falls back to geometry;
`structural_speeds._wing_area_sqft` prefers **geometry** and falls back to the
slice. Opposite orders for the same quantity. It is masked today only because
`sync_geometry_derived` overwrites the landing copy before the module reads it —
one skipped sync, or a wing surface without a parametric slice, and two modules
resolve one number differently. Exactly the class `CONVENTIONS.md` §7 exists to
prevent, and it has no guard.

### 2.2 The GUI cannot honour OG-7 as written

OG-7 offers the derived scalars for direct entry under GR-GEOM-3 — *"an entered
scalar wins and is marked."* Nothing implements the **wins** half:
`sync_geometry_derived` assigns unconditionally whenever a wing surface exists, so
a value typed into `flight_loads.mac` is discarded on the next run. The oracle
GUI is therefore promising an entry that cannot take effect.

### 2.3 The registry documents a mechanism that does not exist

`speeds.weight_lb` is recorded as *"`weight.max_takeoff_weight_lb`
(read-through, Step D4.4; override checkbox)"*. There is no read-through:
`design_speed_values` uses `inp.weight_lb` verbatim. The only links are the
**reverse** fallback in `cg_cases.max_takeoff_weight` and the
`mtow_representation_drift` validation warning. The registry text overstates the
code and must be corrected whichever way this note goes.

## 3. Decisions proposed

| # | Decision |
|---|---|
| **DS-1** | **Class A stops being input.** The ten class-A fields are removed from their input dataclasses. They are not inputs — they are a cache of `geometry`, they are never persisted, and no shipped project supplies them. This is the whole of the consolidation the owner asked for; everything below is how. |
| **DS-2** | **One resolver owns the precedence.** `derived_geometry` gains the effective-value accessors (wing reference scalars; gear geometry) and becomes the **only** place the geometry-or-fallback order is written. `sync_geometry_derived`'s per-field assignments and `landing._effective_gear_input` both fold into it. `CONVENTIONS.md` §7 gains the row, with the drift guard rule 3 requires. |
| **DS-3** | **The fallback becomes explicit, not a shadow field.** With the slice copy gone, "no geometry" is an error with a message naming the Geometry page, not a silent second input. `MissingInputError` already says this; it becomes the only path. |
| **DS-4** | **Functions that need parametric scalars take them as parameters** (§1.3's existing pattern), rather than receiving them smuggled inside an input dataclass. `inertia_units` and its callers move to the `air_load_distribution` shape. |
| **DS-5** | **OG-7 is amended, not implemented.** Direct entry of a derived scalar is served by editing the **owner** — the planform, which is on the oracle GUI's own Geometry page. The copies are gone rather than marked. Building the real override would need a stored override flag per scalar, contradicting OG-13's no-new-stored-field rule, and is not proposed. |
| **DS-6** | **Class B keeps its field**, and the registry's `derived_from` text is corrected to say *override*, not *read-through* (§2.3). `render_scalar` marks these three — the surviving, and much smaller, half of CR-A-2. |
| **DS-7** | **Class C is out of scope for this note.** Both members are persisted, so removing either needs a schema hop and a migration; filed separately rather than smuggled in behind a no-hop change. Recorded here because §1's table would otherwise look complete. |

## 4. Acceptance gates

| # | Gate |
|---|---|
| **DG-1** | *No behaviour change.* Every Appendix A oracle passes at ±0.1 % and every closure gate holds, before and after. This refactor moves no equation; if a number moves, that is the finding. |
| **DG-2** | *The duplicates are gone from the registry.* **Shipped 2026-08-21: ten multi-copy quantities became four**, asserted as a named literal (`STILL_DUPLICATED` in `tests/test_field_registry.py`) rather than a count, so removing one duplicate cannot mask another being added. The four are the two class-B overrides (`max take-off weight`, `wing reference area`) and the two class-C pairs DS-7 defers (`airplane length`, `shoulder altitude`). The note first said "three"; that was written before the count was run and is corrected here to what the registry reports. |
| **DG-3** | *One precedence.* **Shipped**, in two halves (`tests/test_derived_geometry.py`): an AST guard that no module performs the wing strip integral outside its owner and the two accessors allowed to name it, checked against a deliberate violation to confirm it fails; and a numeric check that `landing._wing_area` and `structural_speeds._wing_area_sqft` return the same area on every shipped fixture — which, before the copies were removed, they could not be relied on to do. |
| **DG-4** | *Round-trip unchanged.* Every shipped example re-serialises byte-identically. Class A was never written, so this must hold trivially; it is the check that DS-1 really was storage-neutral. |
| **DG-5** | *The GUIs lose the second widget.* No oracle page and no `app/views/` page renders an editable widget for a consolidated quantity anywhere but its owner. |

## 5. Cost, measured

* **Read sites:** ~40 across `balance.py`, `select.py`, `flight_envelope.py`,
  `body_loads.py`, `balloads.py`, `net_loads.py`, `wing_inertia.py`,
  `report/content.py`. Mechanical (`fl.xw` → the resolver's `xw`), but they sit on
  oracle-locked paths, which is what DG-1 is for.
* **Construction sites in tests:** 14, in six files
  (`test_derived_geometry`, `test_flight_envelope`, `test_envelope_owner`,
  `test_landing`, `test_wing_case_derivation`, `test_wing_inertia`). These build
  a slice without geometry and must build the geometry instead. The owner has
  accepted this cost explicitly.
* **No migration hop**, and no `SCHEMA_VERSION` bump: `io` already omits every
  class-A field, and legacy keys are already documented as ignored-and-re-derived.
  This is the single largest reason to do class A now and class C separately.

## 6. Risks and what is explicitly accepted

* **A refactor across oracle-locked paths is the risk.** Mitigated by DG-1 and by
  sequencing: the groups land one at a time (wing-mass pair → gear block → wing
  areas → the `flight_loads` four), suite green between each, because a single
  commit touching forty call sites cannot be bisected usefully.
* **Hand-constructed projects lose a convenience.** A test that wants a wing area
  must now build a wing. Accepted deliberately: that convenience *is* the second
  opinion this note removes, and §2.1 shows what it costs when the two disagree.
* **The `app/views/` freeze.** Class A's consumers include frozen views. The
  freeze is for *GUI investment*; this is a calc-contract change that the views
  follow mechanically, in the same change, as the fix does not exist otherwise.
* **What this note does not do:** it does not implement OG-7's override (DS-5),
  does not touch class C (DS-7), and does not change any equation. A reader
  expecting CR-A-2 to be closed in full by this note should read DS-6: the
  renderer still has three overrides to mark, and that work rides #36.

---

## 7. What implementation changed about this note

Recorded because a note that shipped unamended usually means nobody checked it
against the code.

* **DS-1 said "nine" fields; it is ten** — `flight_loads` ×4, `wing_mass` ×2,
  `landing` ×4 (the gear block plus `wing_area_sqft`). A miscount in the
  proposal, not a scope change.
* **DG-2's target was wrong.** It predicted three surviving multi-copy
  quantities; the answer is **four**, because DS-7 defers two class-C pairs and
  only two class-B overrides remain. The gate now asserts the four by name.
* **`wing_inertia_distribution` lost two parameters, not none.** With `units`
  made required (DS-2 removed its second, differently-resolved construction
  path), `geom` and `wm` became unused — the signature is now
  `(case, units)`. Ruff found this; the note had not anticipated it.
* **Two `_effective` helpers existed, not one.** `landing._effective_gear_input`
  had a twin in `gear_loads._effective` performing the identical substitution.
  Both are gone; the note's §1 table had counted the duplication once.
* **`body_drag_waterline` held a fourth reader of `flight_loads.zw`** as the
  middle rung of a three-step fallback. Removed with the field: it was the same
  number one edit removed from the wing plane above it.
* **One test's subject disappeared rather than moved.**
  `test_sync_fills_derived_slices_from_geometry` asserted that the sync filled
  the copies; with no copies to fill it is now
  `test_every_wing_resolver_answers_from_the_one_source`, asserting the property
  the copies never had — that the resolvers are views of one computation.
* **A fixture had to stop deleting the wing.**
  `test_body_loads._no_wing_project` removed the planform to exercise the
  carry-through fallback. Under DS-3 that no longer reaches the fallback, it
  refuses; the fixture now makes the *spar stations* underivable (rear ahead of
  front), which is the condition `carry_through` actually tests and what the
  test was always about.
* **Cost came in at the estimate.** ~40 read sites and 14 test construction
  sites, as §5 predicted; no `SCHEMA_VERSION` bump and no migration hop, as §5
  predicted and as the examples' on-disk keys confirmed.

---

## 8. DS-7 executed — the class-C pairs retired (v55, issue #52)

**Status: AGREED 2026-08-22 in chat (working alone, `CLAUDE.md` rule 1), then
implemented the same day.** Tier **L**: a persisted-shape change with a
migration hop. Pulled into 0.7.0 by the backlog review of 2026-08-22 (BB-5):
both members of each pair render **side by side on one oracle page** — the
altitudes on `structural_speeds`, the lengths on `configuration_layout` — so a
beta user is shown two widgets for one physical quantity with nothing
reconciling them, and MC/MD could be computed at two different altitudes with
no warning. Every shipped example happened to agree, which is why nothing had
caught it.

### 8.1 Decisions

| # | Decision |
|---|---|
| **DS-7.1** | **The surviving homes.** *Shoulder altitude:* `speeds.shoulder_altitude_ft` survives (the more-read home — STRSPEED's MC/MD derivation, ONENGOUT's default altitude, the report's speeds table); `MachLimitInput.shoulder_altitude_ft` is removed and `mach_limit_lines` takes the altitude as an explicit argument, exactly as it already takes MC/MD (F25-2, v40). *Airplane length:* LF is a whole-airplane quantity, so neither tail is its owner — one field `geometry.empennage.airplane_length_in` on the parent `EmpennageInput`; both SELECT readers (the 23.423(b) pitch inertia and the 23.441 default IZZ) take it from `project`. Keeping it on `htail` with a v-tail cross-read was rejected: a v-tail-only project would store its length on a surface it does not have. |
| **DS-7.2** | **On disagreement the migration takes the value that governed the shipped output, and warns.** For the altitude that is the **MACHLIM** copy — every MNE/MFC table ever produced read it verbatim (the registry marked it `governs=True`) — so a legacy file's Mach-limit lines are unchanged by the hop. The two LF copies were each read by their own consumer, so neither governed the other; the **htail** value is taken (the surface whose load case SELECT runs first) and the warning names both numbers. A zero/absent member means "not entered" and loses silently to the non-zero one. Disagreement is *any* difference, not `isclose`: a file that was saved by this program wrote identical floats or it did not. |
| **DS-7.3** | **Warning channel.** The hop raises `warnings.warn` — the precedent is `io.py`'s v39 stale-case-id drop. In the GUIs a Python warning only reaches the terminal, so `app_shell.project_state.safe_load` **captures** the warnings raised while the file is read and surfaces them as `st.toast` on the page that loaded it (the channel `apply_schema_check` already uses, because the adopt path ends in `st.rerun()` and an ordinary `st.warning` would not survive it — the note first said `st.warning`; implementation corrected it); the CLI sees them on stderr as before. |
| **DS-7.4** | **The freeze.** `app/views/structural_speeds.py` wrote both altitude fields and `app/views/configuration_layout.py` rendered both LF widgets; each loses the retired widget/kwarg and nothing else. The 2026-08-22 freeze amendment lifts the freeze "for exactly this hop"; these lines are that hop. |

### 8.2 Gates

| # | Gate |
|---|---|
| **DG-6** | *No behaviour change on agreeing files.* Every Appendix A oracle at ±0.1 % and every closure gate holds; all six shipped examples, which agree on both pairs, migrate to v55 with no warning and produce identical `run_all` output. |
| **DG-7** | *The migration keeps the governing value and says so.* A v54 fixture with disagreeing pairs migrates to the MACHLIM altitude and the htail length, raising one warning per pair that names both numbers; a fixture with one member zero migrates silently to the other. |
| **DG-2 (shrunk)** | `STILL_DUPLICATED` in `tests/test_field_registry.py` goes from four to the two class-B overrides. |
| **DG-5 (completed)** | Neither oracle page renders a second editable widget for either quantity — the registry loses the two rows, which is the whole of the GUI half. |

### 8.3 What changed on disk

`SCHEMA_VERSION` 54 → 55; hop `54: _v54_one_shoulder_altitude_one_airplane_length`.
A v54 file's `speeds.mach_limit.shoulder_altitude_ft` is dropped (its value
reconciled into `speeds.shoulder_altitude_ft` per DS-7.2); its
`geometry.empennage.{htail,vtail}.airplane_length_in` are dropped (reconciled
into `geometry.empennage.airplane_length_in`). Files older than v27 reach the
hop after `_v27_empennage` has folded their top-level `tail_loads`/`vtail_loads`
into `geometry.empennage`, so one hop covers every supported version.
