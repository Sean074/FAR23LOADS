# Conventions Charter — Axes, Signs, Units, Load Contract, Case Identity

**Authoritative single source** for every axis/sign/unit/reference convention in sloads
(2026-08-05 process review, R8). The rules:

1. **Every physics or export step's design note must cite the sections of this charter
   it relies on, before code is written** (CLAUDE.md rule 1).
2. **Make it structural:** any cross-cutting convention gets a single-source code owner
   **plus a drift-guard test** the first time it is needed (§7 table) — never a prose
   rule alone. The units/SI history (three rebuilds before M4-20) is the cautionary
   precedent.
3. **A change to any convention here is a breaking change** — L-tier step, update this
   file, sweep every consumer.

Facts verified against code 2026-08-05, with citations. Line numbers drift — the cited
file + symbol is the anchor.

---

## 1. Frames and axes

- **sloads internal frame:** Imperial airplane axes, all lengths in **inches** —
  `x` = fuselage station, **+aft**; `y` = butt line, **+right** (starboard);
  `z` = waterline, **+up**. Loads: `fz` = lift (+up), `fx` = drag (+aft), `myy` = wing
  torsion about the spanwise y-axis (`sloads/export/coordinates.py:3-11`).
- **sbeam deck frame:** NASTRAN basic CID 0, right-handed; the sloads frame already
  matches, so the transform is the **identity** (`coordinates.py:13-16`,
  `SBEAM_CID = 0`).
- **`export/coordinates.py` is the single edit-point** for any sign flip, axis swap, or
  unit scale in the export channel — the **only** place a load or coordinate is
  multiplied by anything on its way to a deck. `sbeam_bridge` arithmetic is unit-free
  and routes every dimensional value through `to_grid`/`to_force`/`to_moment`/
  `to_pressure`; `_checked()` rejects dimensionally inconsistent unit sets at
  deck-write time.
- **Reporting rules** (`SUMMARY_REPORT.md` §3.3): torsion always names its axis (wing
  LRA as %chord); moments state their sign convention; maxima carry a station;
  envelopes are two-sided.
- **Mass units are a distinct channel, and the one exemption from the all-1.0
  Imperial identity (C-5, 2026-08-08).** `CONM2` carries **mass**; the database
  stores **weight**. `DeliverableUnits.mass`/`.mass_inertia` on the SOLVER channel
  are lbf·s²/in and t; the HUMAN channel keeps lb and kg. The identity is
  `force / (mass × length) == g` — exact, and the *same number* in both systems
  (one standard gravity, expressed per length unit, derived once) — plus
  `mass_inertia == mass × length²`. `is_mass_consistent` is separate from
  `is_consistent` so the human channel can fail it without changing what any
  existing caller sees, and a writer refuses a set that fails it.
- **Inertia is never applied twice (C-6).** The `FORCE`/`MOMENT` deck is the
  *total* applied load and already contains inertia. No deck may both apply it
  and accelerate a mass set: the mass-check deck therefore carries **no load
  cards at all**, and sloads' inertia-only set is marked a comparison artifact
  in-band. This is structural, not a warning, because the failure reads as a
  heavier airplane rather than as a crash.
- **`weight.items` is the mass single source of truth (B-2, 2026-08-08).** One mass
  model, owned by `sloads/mass_distribution.py`. `MassItem.component` tags which
  structural component reacts each item's weight (`wing` / `fuselage` / `htail` /
  `vtail`); the tag is **explicit**, because every item in every project sits at
  `y = 0` (lumped airplane totals on the centreline) and no geometric inference can
  separate a wing-mounted engine from a fuselage one. The Ch 15 fuselage beam is
  *derived* from the tagged database; `fuselage_mass.stations` is an explicit
  override, and the difference is always reported, never silently taken.
- **The fuselage beam carries everything except the wing.** The empennage included
  — it hangs off the aft fuselage, so that beam reacts its weight. The wing is the
  one exclusion: it enters as the carry-through *reaction*, and applying it as mass
  as well would count it twice (the seam rule below). Hence the invariant
  `Σ(wing items) + Σ(beam stations) == Σ(all items) == W`, guarded by
  `mass_distribution.partition_closes`.
- **A cumulative torsion is not a free moment (2026-08-08).** `WingStationLoad.myy`
  is the torsion about the *root* reference and already contains the sweep and
  dihedral transfer of outboard shear inboard. Only the section `Cm` is a free
  moment. Any assembly that applies a strip's position offset must use the free
  moment alone, or it double-counts the transfer — worth 20 % of n·W·MAC.
- **An assembled balanced case closes in three symmetric DOF** — x, z and pitch —
  by mass-proportional relief. All three are decoupled because the loading's
  centroid *is* the CG. The x DOF is not optional: nothing else in an assembled
  model reacts drag, and FAR 23's `nx` is that quantity.
- **The residual is part of the deliverable.** A balanced case states its
  pre-closure residual and the relief applied, in the result, the UI and the deck
  header — the gate is on the physics, not on the correction.
- **A load that a free-body cut introduces is never applied in the assembled model**
  (plan 11 §4). Each per-component deck takes a cut and carries the cut reaction as
  an applied load; those reactions must not reappear in an assembled deck, where the
  solver recovers them.
- **Per-component moment reference for an exported deck (E-2, 2026-08-08).** A deck's
  moment resultant is meaningless without the point it is about, and there is no single
  airplane-wide point every deck can use — the decks are per-component beam models, not
  an assembled airframe. Each therefore states its closure about **its own** reference,
  taken from the deck's own `GRID` cards so the claim is verifiable from the file alone:
  **wing → its root station**, **body → its aft-most station** (the point the terminal
  cumulative `Myy` is stated about), **tail → its leading-edge chord station**. Control
  decks carry no geometry and state a force closure only.
- **Beam torsion is not a rigid-body moment.** The exported wing `Myy` is a beam torsion
  about the LRA. Because the station `x` sweeps aft and the station `z` rises with
  dihedral, the rigid transfer term `Σ (p − ref) × F` is of the *same order* as the
  torsion itself (≈ −93,300 lb-in against a −91,400 lb-in root torsion on `ga6_normal`
  PHAA). A deck's torsion claim is therefore about its applied `MOMENT` cards; only the
  bending claim integrates the `FORCE` lever arms. `export/equilibrium.Resultant` carries
  both sums (`m0` and `m`) so a checker cannot silently use the wrong one.
- **Open question (filed on the backlog):** the load-application axis vs elastic-axis
  convention for deck consumers — sbeam's grid line *is* its elastic axis; the torsion
  a consumer should attribute when the beam axis differs from the sloads load-reference
  line is not yet stamped in the deck header.

## 2. Units

- **Imperial is canonical internal**; calc runs in the original program's units. SI is
  presentation only, converted at the boundary (`sloads/units.py:1-12`,
  `00_program_overview.md` Units).
- **Two deliverable channels (M4-20 decision D-19):** `Channel.HUMAN` (reports, CSVs,
  workbook: N·m, kPa) vs `Channel.SOLVER` (sbeam span CSVs + bulk data: **N·mm**,
  **MPa** — every derived unit is the base units combined). Resolve the set **once per
  bundle** with `units.deliverable_units(system, channel)` and pass it to every writer;
  never mint one per file. `DeliverableUnits.is_consistent` enforces
  moment = force×length and pressure = force/length².
- **Airspeed/altitude carve-out:** KEAS and ft in both systems, never converted
  (`units.py:95-99`).
- **In-band statement mandatory:** every deliverable file states its unit set
  (`units_statement`, `units.py:530`).
- **The `-ULT` marker is part of the units string** — it converts with the unit
  (`lbs-ULT`/`N-ULT`, `lb-in-ULT`/`Nmm-ULT`, `lb/in^2-ULT`/`MPa-ULT`); mapping table
  `_ULT_UNITS` in `sloads/report/render.py:101`. Non-load units never carry it.

## 3. LIMIT → ULTIMATE contract

- **Calc emits LIMIT; every deliverable is ULTIMATE.** The factor is applied exactly
  once, at the render/export boundary: `report/render.py` (`results_to_rows`,
  `to_ultimate`) and `export/sbeam_bridge.py` (`_sf()`).
- **Loads only** — forces/moments/pressures. Never geometry, weights, inertias, areas,
  speeds, angles, or dimensionless load factors (`_is_load_unit`,
  `render.py:66-95`; `load_keys.py` marks application points "geometry, never scaled").
- `ConditionResult.safety_factor` is the **carrier** (default
  `constants.ULTIMATE_FACTOR = 1.5`); **1.0 means "already at ultimate"** — still
  ULTIMATE output, marked `ULT SF=1.0`. The per-case field is the future
  23.302/25.302/Appendix-K hook; the centralized **policy** resolver is backlog item
  M4-8.
- Uniform per-case scaling preserves closure: `sum(dFz) == sf × root` survives the
  boundary (`sbeam_bridge.py:234`).
- Per-module analysis pages may display LIMIT only with the explicit LIMIT marker and a
  pointer to the ultimate deliverables (the CLAUDE.md carve-out).

## 4. Case identity

- `CaseRef` (`models/results.py:17-40`): `case_id = "<component>-<seq>"` (`W-01`,
  `HT-03`, `VT-02`, `F-04`, `EM-01`, `LG-05`), minted **once** by the first module that
  names the condition, never re-minted. Prefix taxonomy + banded allocator:
  `sloads/case_ids.py`.
- Row identity: stable `LoadValue.key` (machine identity) vs cosmetic `label` (M4-9);
  cross-module keys centralized in `sloads/load_keys.py`.
- **One ID per physical condition (M4-2).** Two modules delivering the same case carry
  the *same* `CaseRef` — SELECT's wing `CriticalCondition` and the WINGINER/NETLOADS
  distribution derived from it are one case with one id, not two. The wing `seq` is a
  property of the condition (`case_ids.WING_SLOTS`), not of its position in a list, so
  ids do not float when the envelope or the case list changes. Modules that mint their
  own sequence into a shared prefix are **banded** (`case_ids.py`; ONENGOUT at
  `VT-30..`), and `tests/test_case_ids.py` fails on any collision.
- **Deck-side identity (M4-2).** A solver deck's `SUBCASE` and load-set `SID` are one
  integer derived from the case id — `case_ids.subcase_id` (`W-03` → 103) — never the
  case's position in the export, so a filtered export cannot renumber what survives.
  Each deck carries a `$` subcase-map block and the case-index CSV a `SUBCASE` column.

## 5. Preserved ENGLOADS conventions (verified in code)

- Engine-mount reaction torque is reported **negative**
  (`sloads/modules/engine.py:165, 195, 256, 285`).
- **Clockwise from the pilot's view is positive** for rotor RPM and stoppage torque
  (`engine.py:8`, `models/inputs.py:50`).
- BASIC 3-decimal truncation `int(v*1000)/1000` is preserved where it affects a
  compared figure (`engine.py:58, 65, 112`) — never add or remove one without checking
  the `.BAS` source.

## 6. Concept-mode benchmark rule (R10)

Where a printed oracle exists, the ±0.1% page-cited oracle test is the gate. Where none
exists (concept mode), the gate is a **stated physics-closure or invariant test in CI,
written with the feature** — e.g. free-free closure residuals, ΣF/ΣM equilibrium at the
export boundary, reduction-to-FAR23 identity on GA inputs. "No oracle" never means
"no gate".

## 7. Single-source owners and their drift guards

| Convention | Owner | Guard test |
|---|---|---|
| Nav / step graph | `sloads/workflow.py` (`STEPS`, `PHASES`) | `tests/test_workflow.py::test_every_registered_module_has_a_step` |
| Deliverable unit sets | `units.deliverable_units` | `tests/test_deliverable_units.py` (identity, consistency, channel) |
| Export axes/scale | `export/coordinates.py` | `tests/test_sbeam_bridge.py::test_grids_match_station_geometry` + closure/SF tests |
| Case IDs | `sloads/case_ids.py` | `tests/test_case_ids.py` |
| Load-case row keys | `sloads/load_keys.py` | **flagged — see §8** |
| Data dictionary | `docs/generate_data_dict.py` (generated doc) | `tests/test_data_dictionary.py::test_committed_doc_matches_generator` |
| ULT unit mapping | `report/render.py` `_ULT_UNITS` | render/SF tests in `tests/test_report_render.py` |

When a new sign/unit/ID-sensitive quantity appears, create its owner + guard test first
and add the row here.

## 8. Flagged inconsistencies (2026-08-05 extraction — filed on the backlog)

1. **`tests/test_load_keys.py` does not exist**, though `load_keys.py:11-12` cites it as
   the uniqueness guard — the guard is missing or the docstring is stale.
2. `constants.py:15` cites **25.303** as the SF authority; `report/methods.py:230` and
   this project's docs say **23.303** (Part 25 equivalent). Same 1.5 — inconsistent
   primary citation.
3. `coordinates.py` module-level default (`IMPERIAL = deliverable_units(IMPERIAL,
   Channel.SOLVER)`) means un-parameterised calls silently emit Imperial inches —
   intentional back-compat, but an implicit assumption worth an explicit comment.
4. `units.py` carries three partially-shared SI factor maps (`_RESULT_TO_SI`,
   `_SCALAR_TO_SI`, `_KIND_FACTORS`) — derived from shared constants only in part;
   a consolidation candidate under rule 2.
