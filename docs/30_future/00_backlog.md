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

**Shipped:** Phases 0–2 and Phase-C Steps **C0–C6**. Of Reference 1's 22
Appendix-C programs, **13 are ported** (ENGLOADS, WTESTIMA, WTONECG, WTENV,
WINGGEOM, STRSPEED, MACHLIM, TAU, AIRLOADS, FLTLOADS, SELECT, WINGINER, NETLOADS),
plus **2 modern modules** with no `.BAS` oracle (`configuration`, `body_loads`).
Schema is at **`SCHEMA_VERSION = 11`**; 167 tests pass; coverage ~90%. The wing
distributed-loads vertical slice (geometry → speeds → envelope → airloads →
inertia → net → sbeam export) and the critical-load selection (wing / h-tail /
v-tail / fuselage) are complete and oracle-locked.

**Remaining suite programs (9):** AIRLOAD4, BALLOADS, AILERON, FLAPLOAD,
TABLOADS, TAILDIST, ONENGOUT, LGFACTOR, LANDLOAD.

The plan below continues the Phase-C step numbering (C7 onward). The FAR23 path
stays oracle-locked (Appendix A/B ±0.1%); concept mode is a superset that reduces
exactly to it on GA inputs.

---

## Development plan (dependency-ordered)

### Step C7 — TAILDIST + AIRLOAD4 (tail distributed loads; swept/high-Mach airloads)
**Objective.** Chordwise horizontal/vertical-tail load distribution for SELECT's
critical tail conditions, and the swept / high-Mach spanwise-airload branch for
concept jets.
**Deliverables.**
- `modules/taildist.py` (registers `"taildist"`) → chordwise tail loads (additive
  α-load at 25% chord + camber load at 50% chord, Ref 1 Ch 10) for the critical
  horizontal and vertical tail cases, reading `Project.envelope.critical` (SELECT)
  and `Project.geometry` (h-tail/v-tail); plus the sbeam tail export.
- `AIRLOAD4` branch inside `modules/airloads.py` (sweepback / high-Mach adjustment
  to Schrenk, `AIRLOAD4.BAS`), auto-selected by sweep / Mach.
- Streamlit tail-distribution page; `Project` schema + `io.py` round-trip.
**Test/Acceptance.** Appendix A/B tail-distribution tables and the Appendix B
swept spanwise tables ±0.1%.
**Dependencies.** SELECT (C6) for the critical conditions; AIRLOADS (C1) for the
spanwise base.

### Step C8 — Control-surface simplified distributions (AILERON / FLAPLOAD / TABLOADS)
**Objective.** The explicit concept-tool requirement: control surfaces use
**standard simplified distributions**.
**Deliverables.** `modules/aileron.py`, `modules/flap.py`, `modules/tab.py` —
FAR-style simplified pressure distributions (uniform / triangular per
23.349 / 23.345 / 23.455 / 23.457 / 23.459), hinge moments + distributed loads +
CSV + sbeam bridge. Read `Project.speeds` (STRSPEED design speeds/load factors)
and `Project.geometry.<surface>`; `Project.aero` for FLAPLOAD. Streamlit pages;
schema + `io.py` round-trip.
**Test/Acceptance.** Appendix A/B `AILERON` / `FLAPLOAD` / tab tables ±0.1%.
**Dependencies.** STRSPEED (done), WINGGEOM (done).

### Step C9 — ONENGOUT (one-engine-out vertical-tail loads)
**Objective.** Asymmetric vertical-tail loads from an engine failure — the first
module to exercise the first-class multi-engine `Project` (resolved Phase 2).
**Deliverables.** `modules/one_engine_out.py` → asymmetric v-tail loads, reading
`Project.geometry`, `Project.mass` (WTONECG inertia), `Project.engines[]` and
`Project.speeds` (per UG Table 2.2). Streamlit page; schema + `io.py` round-trip.
**Test/Acceptance.** Appendix B (twin turboprop) one-engine-out tables ±0.1%.
**Dependencies.** WTONECG (`Project.mass`, done C6), multi-engine layout (done).
**Note.** Needs an Appendix-B twin fixture (see "Test fixtures" below).

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

- **Flaps-extended tail-load printed oracle (from C6).** R3/R4 (flapped V-n
  envelope + flaps-extended balancing / gust) are **closure-validated**. Matching
  the printed Appendix A flaps-extended cases (81 / 106 / 88 / 108) needs the real
  landing-config aero polynomials and the CG5–7 loadings added to the fixtures.
- **Per-CG precise inertia in SELECT (from C6).** `Project.mass` is now persisted
  (WTONECG), but SELECT's checked-maneuver `Iyy` and v-tail `IZZ` still use the
  Ch 9 approximations (which match the oracle). Wire the persisted per-CG inertia.
- **V-tail large-deflection factor `EFV` (from C6).** Modelled as a
  `VTailLoadsInput` input (default 1.0) because its chart (SELECT.BAS subr 10000 at
  δ=0) is illegible in the scan. Recover the real curve if a legible source appears.
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

- [ ] **Test fixtures — Appendix B twin.** ONENGOUT (C9) and the swept tables
  (C7) need the 10-place twin turboprop (Appendix B) as a fixture. Today only
  `examples/ga6_normal.project.json` (Appendix A) and
  `examples/concept_heavy.project.json` (concept) exist; the engine module's
  Appendix-B turboprop case is encoded **inline** in `tests/test_engine.py`, not as
  a project file. *Default: add `examples/twin_turboprop.project.json` when C9 lands.*
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
