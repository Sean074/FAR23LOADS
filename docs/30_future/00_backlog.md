# Backlog — Open Work

The authoritative list of **open** items: modules not yet ported, open design
decisions, and known defects. The dependency-ordered rationale lives in
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md); the
per-module spec is [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md).

> **Lifecycle rule (hard requirement, per `CLAUDE.md`).** When an item here is
> finished, in the **same session**: (1) **remove** it from this file, (2) **add**
> it to [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
> with its full record, and (3) add a `CHANGELOG.md` `[Unreleased]` entry. The
> backlog holds open items only — never leave a "✅ done" entry here.

Each module is "done" when: the module is merged, a `tests/test_<module>.py`
passes against the Appendix A/B figures, a GUI page exists, the `Project` JSON
schema is extended, and `docs/` (this file, the history, the per-module theory
citation) are updated.

## Phase C — Initial-concept loads tool (active plan)

The current development thrust re-scopes the suite into an **initial-concept
distributed-loads tool** (can exceed FAR23 weight/seat limits; per-component
distributed loads; export to **sbeam**). The full narrative, locked decisions,
schema additions and per-step detail live in
[`01_concept_loads_plan.md`](01_concept_loads_plan.md). Locked decisions: concept
mode (generalize the FAR23 caps), Schrenk analytical aero, sbeam FORCE/MOMENT
export bridge, vertical-slice-first build order.

The Phase-C steps **re-sequence** the Phase 3/4 module ports below (vertical slice
first) and add concept-specific work. The FAR23 path stays oracle-locked
(Appendix A/B ±0.1%); concept mode reduces exactly to it on GA inputs.

- [ ] **C1 — AIRLOADS (Schrenk) + TAU.** Spanwise `cl·c` distribution → `Project.aero.spanwise`.
- [ ] **C2 — FLTLOADS.** V-n envelope + balancing tail loads → `Project.envelope.vn`/`tail_balance`.
- [ ] **C3 — WINGINER + NETLOADS.** Wing net span shear/BM/torsion (adds a spanwise wing-mass-distribution input).
- [ ] **C4 — sbeam export bridge.** `farloads/export/sbeam_bridge.py` — FORCE/MOMENT cards + span-load CSV + optional CBAR stick model.
- [ ] **C5 — Configuration & Layout page + fleet assessment.** Supersedes the "Configuration & Layout page" modern-addition item below.
- [ ] **C6 — SELECT + fuselage/body distributed loads.**
- [ ] **C7 — TAILDIST + AIRLOAD4.** Chordwise tail loads; swept/high-Mach spanwise airloads.
- [ ] **C8 — Control-surface simplified distributions.** AILERON / FLAPLOAD / TABLOADS.

## Modules to port

### Phase 3 — Aero coefficients & flight envelope
- [ ] `TAU` — helper (off-menu).
- [ ] `AIRLOADS` / `AIRLOAD4` — aero coefficients.
- [ ] `FLTLOADS` — flight loads, incl. balancing tail loads.
- [ ] `SELECT` — rational critical wing/tail/fuselage loads. **`AIRLOADS`⇄`SELECT` iterate — build them together.**
- [ ] `BALLOADS` — balanced-tail-load verification utility (off-menu); may be deferred or built alongside `SELECT`.

### Phase 4 — Component loads (largely independent; parallelizable after Phases 1–3)
- [ ] `WINGINER` — wing inertia loads.
- [ ] `NETLOADS` — net loads.
- [ ] `AILERON` — aileron loads.
- [ ] `FLAPLOAD` — flap loads.
- [ ] `TABLOADS` — tab loads.
- [ ] `TAILDIST` — tail load distribution.
- [ ] `ONENGOUT` — one-engine-out (exercises multi-engine `Project` support).
- [ ] `LGFACTOR` — landing-gear load factors.
- [ ] `LANDLOAD` — landing loads.

> **Faster-value alternative** (recorded fallback, not the default): after Phase 0,
> build the vertical slice `WTESTIMA → WINGGEOM → STRSPEED → FLTLOADS → SELECT →
> NETLOADS` end-to-end to prove the shared model before filling in the rest.

## Modern additions (no `.BAS` oracle)

### Configuration & Layout page
> **Now tracked as Phase-C Step C5** (see [`01_concept_loads_plan.md`](01_concept_loads_plan.md)
> and the Phase C list above). The detailed deliverables below remain the spec for
> that step, extended with a heavier/concept fleet tier for the configuration
> assessment.

- [ ] **`configuration` — general configuration & layout page.** A modern addition
  (no original `.BAS`; **no manual regression oracle** — use Appendix A/B geometry
  as *sanity* fixtures, asserting derived `MAC`/`XLEMAC` match what WINGGEOM/WTENV
  already reproduce). Becomes the single geometric **source of truth** that seeds
  the downstream mass-properties, geometry and speeds pages.
  - **Model.** New `Project.configuration` slice (`LayoutInput`): fuselage L/W/H +
    datum; parametric wing (area, AR, taper, dihedral, LE sweep, LE-root station,
    root waterline); tail areas + arms (H & V); landing gear (nose/main station,
    track, gear height); engine x mirrored from `EngineInput.engine_cg` (engine
    module stays authoritative — page reads for drawing, writes back on move). Bump
    `SCHEMA_VERSION`; extend `io.py` round-trip.
  - **Calc.** New `modules/configuration.py` (pure, registered): derive `MAC`,
    `XLEMAC`, `Y_MAC` from the planform; generate WINGGEOM LE/TE polylines; assign
    component `MassItem.x/z` stations (fills the zeros `estimate_to_mass_items`
    leaves); static margin (tail-volume neutral-point estimate − CG %MAC); tip-back
    & overturn angles; prop/tail ground clearance.
  - **Page** (`app/pages/00_Configuration_Layout.py`, numbered ahead of Weight
    Estimate). Left: slider / number-input groups (Fuselage / Wing / Tail / Gear /
    Engines) — **no new dependency**, live rerun. Center: three-view (Plotly, three
    2-D subplots top/side/front) with CG and NP marked. Right/below: assessment
    panel (MAC, XLEMAC, static margin, tip-back/overturn, clearances) + **W/S vs
    W/P** fleet comparison plot (extend `app/data/reference_aircraft.csv`). Seed
    buttons mirroring the Weight Estimate "Seed" pattern: push stations → Weight DB
    (WTONECG), generate wing geometry (WINGGEOM), set `XLEMAC`/`MAC` (WTENV/STRSPEED).
  - **Migrates inputs here** (other pages become refine-only): wing planform params,
    fuselage dims (new — no current home), landing-gear geometry (new), engine/tail
    positions.
  - **Build order.** (1) `LayoutInput` + `io` round-trip + schema bump → (2)
    derivation calc + Appendix-A sanity test → (3) three-view renderer → (4) page +
    sliders → (5) seeding into WTONECG/WTENV/WINGGEOM → (6) comparison plot → (7)
    docs (`PROGRAM_SPEC`, `PROJECT_GUIDE` layout/schema, `20_theory` citation,
    backlog→completed, `CHANGELOG`).
  - **Origin.** Realizes the `docs/30_future/Phase1_2_review.md` feedback (geometry
    on the weight page, 3-view, in-service comparison plots) consolidated into one page.

## Open design decisions (from PROJECT_GUIDE §8)

- [ ] **Graphics.** Replicate the original's graphics (weight envelope, V-n diagram, spanwise plots) as Streamlit charts? *Default: yes, per module, deferred to that module's phase.*
- [ ] **Multi-engine / twin layout.** First-class multi-engine `Project` support from now, or added at `ONENGOUT`? *Default: model the field now, exercise it at `ONENGOUT`.*
- [ ] **Standalone vs project-only inputs.** Maintain per-module example JSONs in addition to the two full-airplane projects? *Default: full projects are canonical; per-module slices are derived for tests.*
- [ ] **CSV vs combined workbook.** Also offer a single multi-sheet export (zip/xlsx) from the Home page? *Default: zip of per-module CSVs.*

## Known defects

- _(none recorded)_
