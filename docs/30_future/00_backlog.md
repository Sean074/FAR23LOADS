# Backlog — Open Work & Development Plan

The authoritative list of **open** items, structured around the **path to the
first concept-loads release**: the release cut **M3**, the post-release milestone
**M4**, Phase F25, the long-tail refinement list, and future directions.
Milestones M1 and M2 (2026-07-19 review) completed 2026-07-20/21 and the
release-readiness milestone **M2R** (2026-07-21 review fixes, all eight items)
completed 2026-07-22 — see history. Items carry their source-review IDs in parentheses
([`PROJECT_REVIEW_2026-07-19.md`](../../PROJECT_REVIEW_2026-07-19.md),
[`CODE_REVIEW_2026-07-21.md`](../../CODE_REVIEW_2026-07-21.md)).

The architectural rationale lives in
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md); the
per-module spec is [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md); the
Phase-C narrative (locked decisions, schema, concept-mode invariants) is
[`01_concept_loads_plan.md`](01_concept_loads_plan.md); the Phase-G narrative
(GUI rework, locked decisions, page conventions) is
[`03_gui_rework_plan.md`](03_gui_rework_plan.md).

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

> **Invariant (unchanged):** no calc-math change to the FAR23 path — Appendix A
> oracles pass throughout; concept mode reduces exactly to FAR23 on GA inputs;
> ultimate-load output rules hold; `workflow.py` stays the single source of
> navigation truth.

---

## Current state (as of 2026-07-21)

All 22 Appendix-C programs are ported plus 2 modern modules (`configuration`,
`body_loads`). Phases 0–2, C, D, E, F, Phase 1, and Phase G Steps **G0–G7**
are complete, as are milestones **M1 (all 11 items)** and **M2 (all 11 items)**
from the 2026-07-19 review (see history). The suite is green (466 passed at the
2026-07-21 snapshot, ~93% coverage, ruff clean, `SCHEMA_VERSION = 32` — see CI
for current counts), the FAR23 GA path is Appendix-A oracle-locked including
the new M1 oracle rows (p155 VD, p178 landing-config, sweep closure), and both
concept fixtures run end-to-end.

The **2026-07-21 code & documentation review**
([`CODE_REVIEW_2026-07-21.md`](../../CODE_REVIEW_2026-07-21.md); per
`CODE_REVIEW_PROCESS.md`, emphasis maintainability / GUI ease-of-use &
coverage / documentation) confirmed the sprint's doc-sync discipline held
(6/6 artifacts on nearly every shipped change; zero stale backlog entries) and
found: 1 CRITICAL (stale schema line), a small set of release-blocking GUI and
doc-currency items (→ **M2R**, now complete — see history), and two structural maintainability walls
to clear **before** the FAR 25 / OpenVSP feature wave (→ M4-9/M4-10/M4-11).
Reference-authority hierarchy (unchanged): (1) `.BAS` listings + Appendix A
printed output, (2) User's Guide CFR quotes (Jan-1994), (3) Code-manual 1990
prose.

---

# M3 — Cut the release: **sloads 0.3.0** (concept-loads v1)

> **M2R (release-readiness fixes) is complete** — all eight items (M2R-1 … M2R-8
> from the 2026-07-21 review) landed 2026-07-21/22; see history. M3 is the next gate.

### M3-1 — Rename: FAR23LOADS → **sloads** (supersedes D-6; decided 2026-07-20)
**Full rename** — repo folder, Python package/import (`farloads` → `sloads`),
CLI command, GUI title/brand, README H1, pyproject name (PyPI `sloads` is
unclaimed, verified 2026-07-20). Rationale: (1) "FAR 23 LOADS" is the exact
name of a commercial product currently marketed by McGettrick Structural
Engineering / DARcorporation (see `reference/FAR-23-Loads-Brochure-2023.pdf`) —
an open reimplementation must not adopt that mark as its title; (2) the tool's
identity is a **concept development tool** extending beyond FAR 23 (concept
mode, Part 25 supplemental cases, sbeam handoff, later OpenVSP interfaces);
(3) `sloads` joins the family of **sbeam** and **smodal** ("s" = simple /
Sean). **Attribution stays prominent** (the M2R-2 sentence predates this step).
Rename-surface inventory (2026-07-21 review): 391 `farloads` refs in .py
across 95 files + 257 in docs + pyproject (name, console entry, `--cov`,
`include=`); the JSON schema, registry names, and session-state keys are
**clean** — saved project files survive untouched; delete/gitignore
`farloads.egg-info/`. **Batch with the rename (same churn event, review
recommendation):** split `models.py` (1,842 lines / 66 classes) into a
`models/` package by lifecycle (enums / input slices / result types / project).
**Acceptance:** one name everywhere (grep finds only historical-attribution
passages); imports/CLI/tests green; docs and examples updated; disclaimer
present in README and the GUI footer/About.

### M3-2 — Release cut per `RELEASE_PROCESS.md`
Version 0.3.0; date and cut the `[Unreleased]` changelog (~1,083 lines —
merge its ten duplicate `### Changed` headings while cutting); refresh the
verification baseline as `40_history/02_verification_baseline_0.3.0.md`
**including the new M1 oracle rows** (p155 VD, p178 landing-config, sweep
closure, 23.427 set) and a one-page **oracle-vs-closure status table**; run
the smoke test; tag.

### M3-3 — *Stretch:* Step G8 — Summary report (Export phase)
The consolidated four-section loads report (`03_gui_rework_plan.md` §4 Phase 6):
input summary; envelope plots (V-n, weight/CG, speed/altitude); conditions +
FAR coverage; results summary (VMT wing/fuselage, control/flap, gear, engine).
All load figures ULTIMATE with SF. **Include a methods/limitations statement
stamped into the exported deliverables** (CSV/BDF/report) so downstream sizing
inherits the concept-mode caveat the UI already shows. Ships with 0.3.0 if M2R
goes fast; otherwise first item of M4.

---

# M4 — Post-release (next after 0.3.0, priority order)

### M4-1 — Fuselage body loads: moment closure (review T5) **[Major]**
`body_loads` applies a single vertical wing reaction and closes ΣFz only; the
Ch 15 procedure (Ref 1 p103) reacts the unbalanced moment at the front/rear
spar attachments (and includes the pitching load factor). Verified: terminal
Myy ≠ 0 (the exported body set carries a net couple). Two-unknown spar-reaction
solve; validate terminal Myy ≈ 0 in the closure suite. **Until fixed, body-load
exports carry a caveat note** (add the note in M3 if this doesn't make 0.3.0).

### M4-2 — Unify `select_wing`/`one_engine_out` case identity (was 2-1)
One case-ID authority per component end-to-end: derive `WingMassInput.cases`
from `envelope.critical` when not given; link `one_engine_out` to
`select_vtail`'s `CriticalCondition` list. Touches WINGINER/NETLOADS iteration →
oracle re-check required.

### M4-3 — ONENGOUT data-flow + turboprop gate (was 2-17)
(a) v-tail geometry provenance (`vtail_loads` slice vs `geometry`) — derive or
document; (b) gate 23.367 on `is_turboprop` (or caption) so it can't silently
run for a reciprocating/turbofan multi (23.367(a) is turbopropeller-specific,
Ref 1 Ch 11 p87); (c) the Ch 11 Method allows **VSF** (flapped stall) as an
alternative VMC substitute — the case table uses only VS (clean) today; add VSF
or document the omission (surfaced during M1-5).

### M4-4 — Per-CG precise inertia in SELECT (was 2-2)
Wire the persisted WTONECG per-CG inertia into SELECT's checked-maneuver `Iyy`
and v-tail `IZZ` (currently the Ch 9 approximations, which match the oracle).

### M4-5 — Aero-coefficient curve plot (was 2-8; decided 2026-07-20: include)
CL–α / drag-polar / CM plot on Aerodynamic Data with the recovered-CL closure
check — catches coefficient-entry errors, which matter more for concept
aircraft with hand-built polynomials.

### M4-6 — Ground-case distributed fuselage (and wing) loads + pressurization (was 2-12)
The heaviest open calc item. Ground-case fuselage inertia/reaction distribution
(gear reactions as applied external loads at the LGFACTOR landing load factor);
optionally the wing distribution under ground reaction; a pressurization case
that is never down-selected against flight. **Acceptance:** ground condition
produces distributed fuselage shear/bending with free-free closure; pressurized
case retained independent of the governing flight case; FAR23 flight oracles
unchanged. Source narrative: `03_gui_rework_plan.md` §5 item (3).

### M4-7 — sbeam export ignores per-case safety factor (latent double-factor) **[correctness]**
`export/sbeam_bridge.py` hardcodes a flat `_SF = ULTIMATE_FACTOR` (1.5) on the wing
net-load results (`WingLoadResult`, which carry no per-case factor), so it does **not**
honor `ConditionResult.safety_factor`. Latent today (sbeam exports only wing net loads,
all LIMIT → ×1.5 is correct; the one non-default case, `one_engine_out`'s 23.367(a)(2)
ULTIMATE SF 1.0, never reaches the wing stick model), but a **double-factor trap** for
any ultimate-classified case that later flows to sbeam (25.367 wing ultimate, the M4-8
25.302 cases). The two export boundaries diverge: `report.py` respects the per-case
factor; `sbeam_bridge` does not. **Fix (couples with M4-8):** thread the load
classification / safety factor into the sbeam-consumed results and multiply by the
per-case factor via the M4-8 resolver instead of the flat `_SF`; test that an
ULTIMATE-classified case exports at its own factor (SF 1.0), not 1.5. Concrete driver
for M4-8.

### M4-8 — Centralized two-layer safety-factor policy (foundation for 25.302) **[architecture]**
Today the safety factor is decided ad hoc: `ConditionResult.safety_factor` defaults to
`ULTIMATE_FACTOR` (1.5) and only `one_engine_out` overrides it (→1.0). Centralize the
**policy** (not the carrier — `ConditionResult.safety_factor` stays the carrier) as a
single audited authority, so which conditions deviate from 1.5 is reviewable in one
place and Part-25 system-failure cases have a home. Two layers with **different sources
of authority** — do not conflate them:
- **Layer 1 — regulation-fixed (code).** A shared `LoadClass` (LIMIT / ULTIMATE / …)
  + a resolver `resolve(load_class, …) -> (factor, basis)`: `LIMIT → 1.5`,
  `ULTIMATE` (limit-treated-as-ultimate) `→ 1.0` (14 CFR 23.303/25.303), subsuming
  `constants.ULTIMATE_FACTOR`. The class is assigned at the case-definition site (the
  seed already exists: `one_engine_out._LoadCase.load_class`); the resolver turns
  class → factor + basis. Consumed by **both** `report.py` **and** `sbeam_bridge`
  (this is what M4-7 wires up). `one_engine_out` migrates to it as the first client.
- **Layer 2 — agreed failure cases (project input; Phase F25 / 25.302).** A `Project`
  slice of **named** system-failure factors — `(name, far_reference="25.302",
  agreed_sf, basis)` — e.g. **`25.302 — MLA Loss → SF 1.25`**. These are *not* code
  constants and *not* computed from a probability by the tool: in practice loads and
  systems **agree** the SF per program (it depends on the demonstrated system
  reliability), so it is an engineering **input**. Each entry (a) renders as its own
  ULTIMATE load case (`25.302 MLA Loss`, `SF=1.25`, `lbs-ULT`) and (b) **records a
  design requirement levied on the system** — a loads↔systems interface artifact the
  tool can later surface as a "system reliability requirements" list. The resolver
  overlays these named factors on the Layer-1 defaults.
**Note:** this is a *practical* 25.302 (agreed named-failure-case factors), distinct
from the full probabilistic **Appendix K** method, which the F25 gap analysis keeps
out of scope — see [`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md).
**Acceptance:** one resolver is the sole authority for every non-1.5 factor; `report.py`
and `sbeam_bridge` produce identical factors for the same case; `one_engine_out`
migrated with oracles/tests unchanged; a Layer-2 named case (e.g. MLA loss @ 1.25)
round-trips through `io.py` and renders as `lbs-ULT SF=1.25`. Touches the CLAUDE.md
ultimate-load contract — land deliberately with tests. **Layer 1 + M4-7 can ship
independently; Layer 2 coordinates with Phase F25.**

### M4-9 — `LoadValue.key`: de-string the load-case semantics **[maintainability, pre-F25]**
2026-07-21 review, top refactor. Semantics currently ride on display-label
strings: `report.py:204-260,307` (`_VERTICAL_LABELS`, `_GYRO_CASE_RE` label
regex), 13 view lookups, 144 test lookups — a cosmetic relabel silently blanks
CSV columns (`_val` returns `""`, no error) and breaks ~150 sites. Add
`key: str` to `LoadValue` (e.g. `fz_vertical`), match on key in
report/sbeam/views/tests, keep `label` cosmetic. Mechanical; **prerequisite for
F25 supplements emitting new quantities.**

### M4-10 — io.py migration chain + version-bump enforcement **[maintainability, pre-F25]**
Builds on M2R-7's tolerant `_filtered` readers (done). Replace the key-presence
sniffing (the 19-clause or-gate at
`io.py:936-945` + legacy shims; `project_from_dict` CC 51, io.py worst-MI file)
with `MIGRATIONS: dict[int, callable]` applied hop-by-hop before one tolerant
reader; check in **one frozen fixture file per historical schema version**
(only v20/v24 exist today); add the generic sentinel round-trip test (manual
`to_dict` field lists silently drop new fields); add a fields-hash test that
fails when persisted dataclasses change without a `SCHEMA_VERSION` bump
(discipline is currently unenforced).

### M4-11 — App scaffold helpers before the next view wave **[maintainability, pre-F25]**
~25–35% of the 6.3k-line app layer is repeated per-field idiom: 139
`number_input`s hand-pairing `to_display`/`to_imperial_scalar` (71+41 sites),
22 hand-rolled apply handlers, 20 identical page headers, 10 concept-banner
copies. Build `unit_number_input(...)` (renders converted, returns Imperial —
removes the silent-unit-bug hazard) and a `page(title, requires=...)` context
manager (header/gate/concept banner); adopt in the worst views first
(`_tab_design_speeds` CC 72 → split seed/form/render; `_three_view` CC 52;
`_tab_vn` CC 44; `landing_reactions` CC 66 per-attitude split). **Do this
before writing the F25/OpenVSP views, not after 30 views exist.** Est. 1.5–2k
lines removed.

### M4-12 — Contract & test-architecture cleanups (2026-07-21 review batch)
Promote the remaining cross-module private-symbol imports to public homes
(`_interp_x`, `_sigma`, `_maneuver_load_factors`, `htail_balance` family;
`app/` must not import `farloads` underscore names — the `_wtenv_cg_limits` →
`wtenv_cg_limits` case was promoted with M2R-5); `htail_balance` →
NamedTuple (stringly dict keys cross module boundaries); document the
`tail_loads`/`vtail_loads` property-proxy trap-doors (invisible to
`dataclasses.fields/replace/asdict`; silent None no-op) and do not replicate
the pattern — retire it at the rename break; write the
`sync_geometry_derived`-inside-`run()` convention into the porting contract;
consolidate the 9 duplicated `_value` test helpers + example builders into
`conftest.py`/`tests/helpers.py` (7 files import from `test_engine`); select
Apply buttons by form key, not list position (`test_dirty_flag.py:84,103`);
add a cspell config or delete the CODE_REVIEW_PROCESS cspell bullet.

---

# Phase F25 — FAR 25 concept coverage (post-0.3.0)

Extend the FAR 23 analyses into a **FAR 25 static surrogate** for
transport-category concepts. Full gap analysis, comparison table, and step
details: [`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md)
(2026-07-20). Pattern throughout: opt-in supplement per module (the shipped
`engine.include_far25` flag is the template); FAR 23 path untouched; every
Part 25 result carries the "static surrogate — not certification" banner.
**Preconditions (2026-07-21 review): M4-9, M4-10, and M4-11 land first** — F25
supplements emit new quantities and new fields, and the label-string/io/app
walls are cheapest to clear before the wave, not after.

- **F25-0 — Verify pass (S, first).** Pull current CFR text for every
  *(verify)* row into `reference/14CFR_Part25_loads_extracts.md`; correct the
  gap table; freeze parameters. *(First row done 2026-07-20:
  `reference/14CFR_MC_MD_speed_margin.md`.)*
- **F25-1 — Transport category "T" envelope pack (M).** 25.337 floor 2.5 /
  negative −1.0; VB (25.335(d)); transport gust corner set — Pratt engine with
  the 25.341 U_ref schedule + F_g; MZFW design weight. M1-6 (W/S ≥ 100
  coefficient clamp), M1-1/2 landed.
  Identity test: "T" with FAR 23 parameters reproduces the FAR 23 envelope.
- **F25-2 — Speeds & placards Part 25 variant (S→M).** 25.335 margins (VB
  margin; MD ≥ MC + **0.07** default, 0.05–0.07 only as explicit
  rational-analysis/HSPF override — see `reference/14CFR_MC_MD_speed_margin.md`)
  + the M2-10 ladder in VMO/MMO form. **Includes fixing a verified concept-mode
  defect (2026-07-20):** no Mach-margin route exists anywhere and the FAR 23
  (b)(1) floor `vd = max(chosen_vd, 1.25·VC)` binds unconditionally — a
  concept user cannot enter a margin-route VD. Demonstrated on the RJ fixture:
  its own `chosen_vd = 350` (MD 0.851, margin +0.097) is silently overridden
  to 387.5 kt → MD 0.9423, margin +0.19, inflating every dive-speed case and
  cascading into MACHLIM (MNE 0.848, MFC 1.13 — nonphysical for a transport).
  Fix: in concept/T mode offer the margin route as the VD basis (honor chosen
  VD when MD ≥ MC + margin; warn below 0.07; flag+annotate 0.05–0.07); keep
  the 1.25 floor for FAR 23 categories. Optional later: the 23.335(b)(4)(i)/
  25.335(b)(1) upset-criterion calculator (7.5°/20 s/1.5 g per AC 25.335-1A).
- **F25-3 — Maneuver & tail surrogates (M).** Checked-maneuver 25.331(c)(2)
  static evaluation; yaw overswing case; 25.427/25.349 schedule checks.
- **F25-4 — Ground-loads parameter variant (M).** LGFACTOR at 10/6 fps,
  lift = W, LDW/MTOW pairing; LANDLOAD tables documented as surrogate.
  Coordinates with M4-6.
- **F25-5 — Pressurization & small gaps (S).** Part 25 combination rules into
  M4-6; the 23.415/25.415 ground-gust module (serves both parts).

Out of scope, documented in the gap analysis: tuned-gust dynamics, continuous
turbulence, 25.362, rational taxi, the full probabilistic **Appendix K** method.
(The *practical* 25.302 case — agreed named system-failure factors such as
`25.302 — MLA Loss → SF 1.25`, negotiated loads↔systems rather than computed from a
probability — is Layer 2 of **M4-8** and is in scope there.)

---

# Long tail — refinements & scope extensions (priority order)

### L-1 — sbeam stick model: real stiffness + assembled airframe (was 2-4)
Real/parametric section properties (today `_MAT1_E = 1.0e7` placeholder) and an
assembled combined-airframe export. Granularity per **D-7**: load-cards-only
default; assembled stick model opt-in behind a flag.

### L-2 — Flaps-extended tail loads: printed oracle completion (was 2-6)
M1-2 lands the p176 landing-config polynomials and the p178 oracle rows for the
envelope; completing the SELECT→TAILDIST flaps-extended pipeline against the
printed cases (81/106/88/108) still needs the CG5–7 loadings added to the
fixtures. Also fold in the LEV LAND balanced point (Appendix A case 90, the
sink-speed/attitude iteration `FLTLOADS.BAS` lines 3410–3600) — currently
omitted from the flap corner set and undocumented (review minor).

### L-3 — V-tail large-deflection factor EFV → SELECT (was 2-3) ⚠️
**Not a simple wire-in — the naive fix breaks the 591-lb oracle by −47%**
(investigated 2026-07-16: `large_deflection_factor(30°, 0.353)=0.53`, not
~1.0). Reopen only after re-reading `SELECT.BAS` subroutines 8300/10000 to pin
down exactly what quantity the rudder EFV multiplies. The default-1.0
pass-through matches the oracle and stays until then.

### L-4 — Distinct Commuter category + VB (was 2-7)
The 19,000-lb/19-seat tier is encoded but dormant; neither VB (23.335(d)) nor
the 66-fps rough-air gust (23.341) is computed anywhere (the BASIC suite
predates commuter support too). Note the commuter MC→MD margin rule
(23.335(b)(4)(iii): 0.07 / rational / 0.05 floor —
`reference/14CFR_MC_MD_speed_margin.md`). Land as one step when a concept
needs the tier.

### L-5 — FLTLOADS enroute / speed-control config (was 2-19)
Third config — enroute (partial flaps / dive brakes / spoilers) with VPF
(UG §11.2.3, 23.373). Add an enroute `AeroCoeffSet` + VPF, or document the
omission (only then add 23.373 to the citation string).

### L-6 — AIRLOADS airplane-less-tail coefficient generation (was 2-18)
The guide's windows 4/6/8 (fuselage/nacelle CM, gear aero, per-station stall
CL) — implement the coefficient generator or keep as a tracked scope gap
(coefficients are entered by hand today, documented).

### L-7 — WINGINER Table 15.1 completeness (was 2-20)
Confirm vs WINGINER.BAS whether a THETADOT pitch-acceleration case is expected;
surface `DMYY` if a per-strip incremental torsion column is wanted.

### L-8 — UX / reporting parity batch (was 2-21; extended by the 07-19 and 07-21 reviews)
ENGLOADS `prop_blades` captured but unused; AILERON positive-deflection
coercion undocumented; WTONECG YBAR omitted; TAILDIST average-chord only (not
the guide's N-station-chord variants, Figs 20.7–20.10). Review nits (07-19):
V-n plot negative closure should show −1.0 at VD for U/A categories (loads are
right; display only); chosen VA silently clamped to VC (BASIC only raises —
warn instead); 190-lb occupant caption for U/A (23.25(a)(2)); MC-vs-MD Mach cap
on cruise stall-line conditions (numerically inert; comment or match BASIC);
save-filename sanitization; `st.spinner` on heavy recomputes; migrate off the
deprecated `use_container_width`. **New from the 2026-07-21 GUI review:**
finish the `help=` rollout on the Other-loads/Flight-loads pages (flap 0/6,
OEO 0/7, wing loads 2/10 vs speeds 21/21; app-wide ~45%); make the G6/G6b
empennage + landing-gear sections respect the SI toggle (hardcoded ft²/in
labels — a GUI_design §7 deviation — and ~30 widgets without tooltips) or
record the exception in GUI_design §7; Results Review "All results by section"
should include the 8 folded modules' results (map folded → host step);
human-label the folded-module CSVs on Export ("balloads (CSV)" → descriptive);
add widgets (or documented JSON-only status) for the remaining uncovered
fields: `speeds.chosen_va`/`chosen_vf`, `one_engine_out.speeds_kt`,
`weight.envelope.fuselage_nose_x`/`fuselage_tail_x`; de-jargonize error
strings (no internal slice names); move the Geometry parametric form and the
Flight-Envelope altitude Apply out of the sidebar (or visually anchor them);
first-run Loads Plots info should use the linked `gate()`; OEO "define ≥2
engines" warning needs a page link. **Widget freshness (deferred from M2-7):**
input widgets pass both `key=` and `value=`, so Streamlit's session_state can
win over the project-seeded `value=` and show a stale field after the project
changes underneath (cross-page Apply, programmatic load). Not a data-loss bug
(Apply is required to persist, and per-page unit-suffixed keys limit the blast
radius); audit the `key=`+`value=` widgets and re-seed on a project change (or
prove it cannot occur). `tests/test_persistence.py` locks the data-persistence
half.

### L-9 — FAR23 printed-oracle backfills ⛔ *blocked on reference material* (was 2-10)
Close each as a mini-step **only if** a legible Appendix B / `.INP`/`.OUT`
surfaces (see D-5): AIRLOAD4 swept printed spanwise table; ONENGOUT printed
twin oracle; LANDLOAD printed wheel-load matrix (p231–233 is OCR-garbled — the
reaction matrix stays closure-/legible-cell-locked).

---

# Future directions (not yet scoped — placeholders, much later)

- **OpenVSP interface.** Geometry **import/export** (`.vsp3`/DegenGeom ↔
  `GeometryInput`) and **aero import** (VSPAERO results as an
  `AeroCoeffSet`/span-load source). Deliberately unscoped; note that an aero
  import would also provide the natural cross-check whose absence D-3 accepted
  (revisit D-3's "closure proves insufficient" trigger when this lands).
- **Deeper sbeam integration** beyond L-1 (loads → sizing → updated
  weights/stiffness loop), and eventual **smodal** hand-off.
- **Additional load-case families** beyond the current FAR23 + Part 25
  supplemental set, as concept needs dictate.
- **Methods manual / DER package** (07-19 review D4 part 2): a consolidated
  front section (scope, assumptions, method per FAR condition group, approved
  deviations, oracle-vs-closure table) assembled from theory-sources +
  PROGRAM_SPEC + docstrings; then per-module walkthroughs in the
  `engine_loads.md` style (SELECT and FLTLOADS first).

---

## Open design decisions requiring user input

- [ ] **D-5 — Appendix B twin fixture (blocks L-9).** The swept (C7) and
  ONENGOUT (C9) printed oracles want the 10-place twin turboprop as a fixture,
  but Appendix B is **not in the bundled PDF**. *Can the user supply a legible
  Appendix B or the original `.INP`/`.OUT` files?* Until then
  `examples/twin_turboprop.project.json` can't be built and these oracles stay
  blocked. **(Reviewed 2026-07-20: keep blocked as-is.)**

### Resolved decisions (record; full rationale in history / plan docs)

| ID | Decision | Resolved |
|----|----------|----------|
| D-1 | Concept reference airplane = swept twin-turbofan regional jet (forces the AIRLOAD4 swept branch) | 2026-07-16 |
| D-2 | Concept gyroscopic rates: keep 23.371(b) fixed rates + guard/warn on exceedance | 2026-07-16 |
| D-3 | No sbeam-VLM validation backend; closure + fleet plausibility (revisit trigger: see OpenVSP note above) | 2026-07-16 |
| D-4 | Fleet comparison set (29 aircraft) sufficient as-is | 2026-07-16 |
| D-6 | ~~Keep "FAR23LOADS"~~ **Superseded → full rename to `sloads` at 0.3.0 (M3-1)** | 2026-07-20 |
| D-7 | sbeam export: load-cards-only default; assembled stick model behind a flag | 2026-07-16 |
| D-8 | Full-airplane project JSONs are the canonical input form; per-module slices derived | 2026-07-16 |
| D-9 | 23.427 unsymmetrical search: restore the full SELECT.BAS candidate set incl. unchecked (M1-4) | 2026-07-20 |
| D-10 | Aero-coefficient curve plot: include (M4-5) — supersedes the 2026-07-15 decline | 2026-07-20 |
| D-11 | Backlog restructured to release milestones; rename ships with the release as **sloads 0.3.0** | 2026-07-20 |

---

## Known defects (open)

- **M4-1** — fuselage body-load distribution carries an unreacted pitching
  couple (terminal Myy ≠ 0). **[Major]**
- **M4-7** — `sbeam_bridge` hardcodes a flat ×1.5 and ignores
  `ConditionResult.safety_factor` — **latent** (only LIMIT wing loads reach sbeam
  today), a double-factor trap for future ULTIMATE cases. **[correctness, latent]**
- **M4-9** — report/export semantics keyed on display-label strings; a
  cosmetic relabel silently blanks CSV columns. **[Major, latent]**

*(The Step-G6 half-migration breakage found by the 2026-07-19 review was
resolved 2026-07-20 — suite green, concept fixture runs end-to-end; see
history.)*
