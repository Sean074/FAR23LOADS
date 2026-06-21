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

> **C6 — SELECT + fuselage/body distributed loads** shipped — see
> [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).
> Deferred follow-ups the C6 build did **not** include:
> - **Flaps-extended tail-load oracle.** R3/R4 (flapped V-n envelope + flaps-extended
>   balancing/gust) are closure-validated; matching the Appendix A flaps-extended
>   cases (81/106/88/108) needs the real landing-config aero polynomials and the
>   CG5–7 loadings added to the fixtures.
> - **Per-CG precise inertia in SELECT.** `Project.mass` is persisted (WTONECG) but
>   SELECT's checked-maneuver `Iyy` and v-tail `IZZ` still use the Ch 9
>   approximations (which match the oracle); wire the per-CG persisted inertia.
> - **V-tail large-deflection factor `EFV`.** Modelled as an input (default 1.0)
>   because its chart (SELECT.BAS subr 10000 at δ=0) is illegible in the scan.
> - **`BALLOADS`** verification utility (off-menu) — the rational balancing method
>   now lives in SELECT; the standalone cross-check tool is still unbuilt.

- [ ] **C7 — TAILDIST + AIRLOAD4.** Chordwise tail loads; swept/high-Mach spanwise airloads.
- [ ] **C8 — Control-surface simplified distributions.** AILERON / FLAPLOAD / TABLOADS.

## Modules to port

### Phase 3 — Aero coefficients & flight envelope
- [ ] `AIRLOAD4` — swept / high-Mach spanwise airloads (sweepback adjustment to
  Schrenk). Low-speed `AIRLOADS` + the `TAU` helper landed in Step C1; `AIRLOAD4`
  is scheduled in C7.
- [x] `SELECT` — rational critical wing/tail/fuselage loads (shipped in Step C6).
- [ ] `BALLOADS` — balanced-tail-load verification utility (off-menu); the rational
  balancing method now lives in SELECT, so this standalone cross-check is optional.

### Phase 4 — Component loads (largely independent; parallelizable after Phases 1–3)
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

> The **Configuration & Layout page** (`configuration` module) shipped in Step C5 —
> see [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).
> Deferred follow-ups that the C5 build did **not** include:
> - Seed buttons beyond WINGGEOM: push component stations → Weight DB (WTONECG) and
>   set `XLEMAC`/`MAC` directly into WTENV/STRSPEED (C5 seeds only the wing geometry
>   surface, which WTENV/STRSPEED already read from `Project.geometry`).
> - `MassItem.x/z` station assignment (filling the zeros `estimate_to_mass_items`
>   leaves) and engine write-back-on-move from the three-view.
> - Tail/prop ground-clearance refinement and a true CG (rather than the 25%-MAC
>   first cut) once a mass slice is present.

## Open design decisions (from PROJECT_GUIDE §8)

- [ ] **Graphics.** Replicate the original's graphics (weight envelope, V-n diagram, spanwise plots) as Streamlit charts? *Default: yes, per module, deferred to that module's phase.*
- [ ] **Multi-engine / twin layout.** First-class multi-engine `Project` support from now, or added at `ONENGOUT`? *Default: model the field now, exercise it at `ONENGOUT`.*
- [ ] **Standalone vs project-only inputs.** Maintain per-module example JSONs in addition to the two full-airplane projects? *Default: full projects are canonical; per-module slices are derived for tests.*
- [ ] **CSV vs combined workbook.** Also offer a single multi-sheet export (zip/xlsx) from the Home page? *Default: zip of per-module CSVs.*

## Known defects

- _(none recorded)_
