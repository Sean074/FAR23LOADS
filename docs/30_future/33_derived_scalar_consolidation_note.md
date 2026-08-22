# Note 33 — Derived-scalar consolidation: one owner per quantity, in the dataclasses

**Status: PROPOSED** (2026-08-21). Tier **L** — a contract change to the
`Project` slice dataclasses and to calc function signatures. Under
[`CLAUDE.md`](../../CLAUDE.md) rule 1 the code waits for this note at **AGREED**.

**Owner's framing (2026-08-21):** *"Explain why we need non-owner duplicate
copies. Can they be consolidated? Change to the existing tests is acceptable, and
preferred to having redundant or potentially confusing redundant variables."*
This note answers the first question with a measurement, and proposes the
consolidation the second asks for.

Conventions cited throughout: [`CONVENTIONS.md`](../10_standard/CONVENTIONS.md)
§7 (single-source-of-truth table — every cross-cutting quantity gets a code owner
**plus** a drift-guard test, never a prose rule); `CLAUDE.md` rule 3 (make it
structural) and rule 4 (generalize on first find). Prior art:
[note 32](32_oracle_gui_note.md) OG-7/OG-8/OG-14 and the field registry they
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
| **DS-1** | **Class A stops being input.** The nine class-A fields are removed from their input dataclasses. They are not inputs — they are a cache of `geometry`, they are never persisted, and no shipped project supplies them. This is the whole of the consolidation the owner asked for; everything below is how. |
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
| **DG-2** | *The duplicates are gone from the registry.* `field_registry.quantities()` reports **three** multi-copy quantities (class B), not ten — asserted, so a re-introduced copy fails CI. |
| **DG-3** | *One precedence.* A guard asserts there is exactly one code site resolving each consolidated quantity — the §2.1 divergence cannot reappear. |
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
