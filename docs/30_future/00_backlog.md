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

## Modules to port

### Phase 2 — Geometry & speeds
> **Build order (revised for data-flow):** `WINGGEOM` (done) → `WTENV` → `STRSPEED` → `MACHLIM`.
> Multi-engine is modelled **first-class in this phase** (layouts: 1 nose / 2 or 4
> wing, symmetric); full one-engine-out *loads* still land at `ONENGOUT`.
- [ ] `STRSPEED` — structural design speeds (airplane `W` and total power summed across `engines`).
- [ ] `MACHLIM` — Mach limit.

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

## Open design decisions (from PROJECT_GUIDE §8)

- [ ] **Graphics.** Replicate the original's graphics (weight envelope, V-n diagram, spanwise plots) as Streamlit charts? *Default: yes, per module, deferred to that module's phase.*
- [ ] **Multi-engine / twin layout.** First-class multi-engine `Project` support from now, or added at `ONENGOUT`? *Default: model the field now, exercise it at `ONENGOUT`.*
- [ ] **Standalone vs project-only inputs.** Maintain per-module example JSONs in addition to the two full-airplane projects? *Default: full projects are canonical; per-module slices are derived for tests.*
- [ ] **CSV vs combined workbook.** Also offer a single multi-sheet export (zip/xlsx) from the Home page? *Default: zip of per-module CSVs.*

## Known defects

- _(none recorded)_
