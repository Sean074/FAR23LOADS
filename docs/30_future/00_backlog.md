# Backlog — Open Work & Development Plan

The authoritative list of **open** items: suite programs not yet ported, modern
additions, deferred refinements, open design decisions, and known defects — in
dependency order, as a step-by-step plan. The architectural rationale lives in
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md); the
per-module spec is [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md); the
Phase-C narrative (locked decisions, schema, concept-mode invariants) is
[`01_concept_loads_plan.md`](01_concept_loads_plan.md).

> **Lifecycle rule (hard requirement, per `CLAUDE.md`).** When an item here is
> finished, in the **same session**: (1) **remove** it from this file, (2) **add**
> it to [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
> with its full step record, and (3) add a `CHANGELOG.md` `[Unreleased]` entry.
> The backlog holds **open** items only — never leave a "✅ done" entry here.

**Definition of done** (every step closes against all of these):
the module is merged and self-registered; a `tests/test_<module>.py` passes
(Appendix A/B figures within ±0.1% where an oracle exists, else physics-closure);
a Streamlit page exists; the `Project` JSON schema is extended and round-trips in
`io.py` (`SCHEMA_VERSION` bumped, older files still load); and the four docs are
synced (`PROGRAM_SPEC.md`, `20_theory/00_theory_sources.md`, this backlog →
history, `CHANGELOG.md`).

---

## Current state (snapshot)

**Shipped:** Phases 0–2 and Phase-C Steps **C0–C9**. Of Reference 1's 22
Appendix-C programs, **19 are ported** (ENGLOADS, WTESTIMA, WTONECG, WTENV,
WINGGEOM, STRSPEED, MACHLIM, TAU, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, WINGINER,
NETLOADS, TAILDIST, AILERON, FLAPLOAD, TABLOADS, ONENGOUT), plus **2 modern modules**
with no `.BAS` oracle (`configuration`, `body_loads`). Schema is at
**`SCHEMA_VERSION = 14`**; 198 tests pass; coverage ~89%. The wing distributed-loads
vertical slice (geometry → speeds → envelope → airloads → inertia → net → sbeam
export), the critical-load selection (wing / h-tail / v-tail / fuselage), the
chordwise tail distribution, the simplified control-surface distributions
(aileron / flap / tab) and the one-engine-out vertical-tail transient are complete
(the first three oracle-locked; ONENGOUT closure-locked — no Appendix-B oracle exists).

**Remaining suite programs (3):** BALLOADS, LGFACTOR, LANDLOAD.

The plan below continues the Phase-C step numbering (C10 onward). The FAR23 path
stays oracle-locked (Appendix A/B ±0.1%); concept mode is a superset that reduces
exactly to it on GA inputs.

---

## Development plan (dependency-ordered)

### Step C10 — Landing loads (LGFACTOR → LANDLOAD)
**Objective.** Ground-load conditions: the landing load factor and the gear
reaction loads for each ground case.
**Deliverables.**
- `modules/landing.py` with the `LGFACTOR` load-factor helper (`23.473`/`23.725`,
  → `Project.landing.n`) and `LANDLOAD` (`23.473–23.511`: level, tail-down,
  one-wheel, side, braked) reaction loads, reading `Project.landing.n`,
  `Project.mass` (weight/CG) and `Project.geometry` (gear geometry).
- Streamlit page; schema + `io.py` round-trip. **Tricycle gear only** (UG Table 2.1).
**Test/Acceptance.** Appendix A/B `LGFACTOR` / `LANDLOAD` tables ±0.1%.
**Dependencies.** WTONECG (`Project.mass`, done), Configuration/WINGGEOM gear
geometry (done C5).

### Step C11 — BALLOADS (balanced-tail-load verification utility) — *optional*
**Objective.** The off-pipeline cross-check that recomputes the rational
balanced-tail-load centers of pressure (`LT25`/`LT50`/elevator load) to verify
the approximate `XTC`/`XTF` that FLTLOADS uses and SELECT now refines.
**Deliverables.** `modules/balloads.py` (or a verification helper) reading the
FLTLOADS V-n / geometry / mass inputs; no pipeline output other than a report.
**Test/Acceptance.** Matches SELECT's rational `XTC`/`XTF` and the Ch 9 case-202
hand-calc (`LT = 519.845 lb`).
**Note.** Low priority — the rational balancing method already lives in SELECT;
this is a teaching/verification tool. Defer unless a cross-check is wanted.

---

## Deferred refinements (carried from shipped steps)

These do not block the plan above; close each under its own mini-step (history +
changelog entry) when done.

- **AIRLOAD4 swept spanwise printed oracle (from C7).** The swept branch is
  validated by the reduction invariant (Λ=0 / low Mach ≡ AIRLOADS exactly) and
  redistribution closure; matching a *printed* Appendix B swept spanwise table
  needs a legible swept fixture (the missing `examples/twin_turboprop.project.json`
  — see "Open design decisions"). Close as a mini-step when the fixture lands.
- **Flaps-extended chordwise tail rows (from C7).** TAILDIST reproduces all 13
  horizontal + 4 vertical Appendix A chordwise rows via `chordwise_pressures`, but
  the SELECT→TAILDIST pipeline emits only the 9 flaps-retracted horizontal
  conditions until the flapped V-n landing aero (the C6 deferral below) is added.
- **Flaps-extended tail-load printed oracle (from C6).** R3/R4 (flapped V-n
  envelope + flaps-extended balancing / gust) are **closure-validated**. Matching
  the printed Appendix A flaps-extended cases (81 / 106 / 88 / 108) needs the real
  landing-config aero polynomials and the CG5–7 loadings added to the fixtures.
- **Per-CG precise inertia in SELECT (from C6).** `Project.mass` is now persisted
  (WTONECG), but SELECT's checked-maneuver `Iyy` and v-tail `IZZ` still use the
  Ch 9 approximations (which match the oracle). Wire the persisted per-CG inertia.
- **V-tail large-deflection factor `EFV` → SELECT backfill (from C6/C9).** The legible
  large-deflection chart (Dommasch fig 12:3) now lives in
  `farloads/modules/_vtail.large_deflection_factor` (recovered for ONENGOUT, C9). SELECT's
  static v-tail rudder load still uses the `VTailLoadsInput.rudder_large_deflection_factor`
  input (default 1.0); wire the recovered curve into SELECT's `_vt_rudder_load` as a
  mini-step (it shifts the rudder-deflection load ~1%; needs a re-baselined oracle check).
- **ONENGOUT printed twin oracle (from C9).** C9 is closure- + sub-formula-locked because
  the printed Appendix B one-engine-out tables are **absent** from the bundled references
  (Appendix B is not in `reference/FAR23 loads (1).pdf`; FAA User's Guide Ch 22 gives
  partial inputs / no outputs). Add the printed ±0.1% oracle if a legible Appendix B (or an
  `ONENGOUT.OUT`) surfaces, alongside the `examples/twin_turboprop.project.json` fixture below.
- **Configuration seeding follow-ups (from C5).** C5 seeds only the wing geometry
  surface. Still open: push component stations → Weight DB (WTONECG) and set
  `XLEMAC`/`MAC` directly into WTENV/STRSPEED; `MassItem.x/z` station assignment
  (filling the zeros `estimate_to_mass_items` leaves) and engine write-back from
  the three-view; tail/prop ground-clearance refinement; a true CG (rather than the
  25%-MAC first cut) once a mass slice is present.

---

## Modern UI niceties (no `.BAS` oracle)

- **Home page — Engineer & Date fields.** Add optional `Engineer:` and `Date:`
  metadata alongside the Project Name, carried in the project JSON and shown on
  reports. *(From the GUI review; the rest of that review — auto-populating the
  Weight, CG & Inertia page, a three-view, and the MTOW-vs-OEW fleet plot — shipped
  in the seed-mass-items helper and Step C5.)*
- **Combined workbook export.** Offer a single multi-sheet export (zip of
  per-module CSVs, or `.xlsx`) from the Home page. *(Default: zip of per-module CSVs.)*
- **Per-module graphics audit.** Confirm every module that the original rendered as
  a plot (weight envelope, V-n diagram, spanwise / shear-BM-torsion, Mach lines,
  three-view) has an equivalent Streamlit chart. *(Most exist; audit for gaps as
  C7–C10 land.)*

---

## Open design decisions

- [ ] **Test fixtures — Appendix B twin.** The swept tables (C7) and the ONENGOUT
  printed oracle (C9) want the 10-place twin turboprop (Appendix B) as a fixture. Today
  only `examples/ga6_normal.project.json` (Appendix A) and
  `examples/concept_heavy.project.json` (concept) exist; the engine module's Appendix-B
  turboprop case is encoded **inline** in `tests/test_engine.py`, not as a project file.
  **Blocked:** Appendix B is **not in the bundled `reference/FAR23 loads (1).pdf`** (it
  holds only the Appendix A GA single, physical pp. 128–247; Appendix C source from 248),
  so the twin geometry/loads can't be transcribed from the reference. *Needs a legible
  Appendix B (or the original `.INP`/`.OUT` files) before `examples/twin_turboprop.project.json`
  can be built.*
- [ ] **Standalone vs project-only inputs.** Maintain per-module example JSONs in
  addition to the full-airplane projects? *Default: full projects are canonical;
  per-module slices are derived for tests.*
- [ ] **sbeam VLM cross-check.** Build the optional sbeam-VLM backend to validate
  concept Schrenk distributions? *Default: out of Phase C; revisit after C8.*
- [ ] **Naming.** "FAR23LOADS" undersells the concept scope. Keep the name, or
  adopt a "Concept Loads" sub-brand? *(Non-blocking.)*

---

## Release / versioning

- [ ] **Cut the first post-0.1.0 release.** `pyproject.toml` is still at
  `version = 0.1.0` (the Phase 0 baseline) while the entire Phase 1–2 + C0–C6 body
  of work sits in `CHANGELOG.md [Unreleased]`. Per
  [`../10_standard/RELEASE_PROCESS.md`](../10_standard/RELEASE_PROCESS.md), a
  completed roadmap phase warrants a release: bump the version (MINOR per ported
  module is many bumps — pragmatically cut one `0.2.0` for the Phase 1–2 + Phase-C
  body), date the changelog, and tag. *(Versioning/tagging is the user's to run.)*

---

## Known defects

- _(none recorded)_
