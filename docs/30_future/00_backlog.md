# Backlog — Open Work & Development Plan

The authoritative list of **open** items. The first concept-loads release —
**sloads 0.3.0, cut 2026-07-23** — is out; the structure is now the
post-release milestone **M4**, Phase F25, the long-tail refinement list, and
future directions. The completed-milestone record (M1, M2, M2R, M3) lives in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md);
the source reviews are
[`PROJECT_REVIEW_2026-07-19.md`](../../PROJECT_REVIEW_2026-07-19.md) and
[`CODE_REVIEW_2026-07-21.md`](../../CODE_REVIEW_2026-07-21.md).

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

## Current state

All 22 Appendix-C programs are ported plus 2 modern modules (`configuration`,
`body_loads`). Phases 0–2, C, D, E, F, Phase 1, Phase G Steps **G0–G7** and
milestones **M1, M2, M2R, M3** are complete — see history for the step records
and `40_history/02_verification_baseline_0.3.0.md` for the release baseline.
The suite is green (ruff clean, smoke test PASS; see CI for current test and
coverage counts), the FAR23 GA path is Appendix-A oracle-locked, and both
concept fixtures run end-to-end.

**Release status:** **sloads 0.3.0 cut 2026-07-23**, tag `v0.3.0`. M3-3 (Step G8
summary report) did not ship with 0.3.0 and opens M4 below.

Reference-authority hierarchy (unchanged): (1) `.BAS` listings + Appendix A
printed output, (2) User's Guide CFR quotes (Jan-1994), (3) Code-manual 1990
prose.

---

# M4 — Post-release (next after 0.3.0, priority order)

### M3-3 — Step G8 — Summary report (Export phase) **[first item of M4, was the M3 stretch]**
The consolidated four-section loads report (`03_gui_rework_plan.md` §4 Phase 6):
input summary; envelope plots (V-n, weight/CG, speed/altitude); conditions +
FAR coverage; results summary (VMT wing/fuselage, control/flap, gear, engine).
All load figures ULTIMATE with SF. **Include a methods/limitations statement
stamped into the exported deliverables** (CSV/BDF/report) so downstream sizing
inherits the concept-mode caveat the UI already shows.

**Specified and planned (2026-08-03).** Document standard (structure, required
and excluded content, conformance checklist):
[`../10_standard/SUMMARY_REPORT.md`](../10_standard/SUMMARY_REPORT.md).
Implementation plan (locked decisions, `sloads/report/` layout, sub-steps
G8.1–G8.7, risks, test matrix):
[`05_step_g8_summary_report_plan.md`](05_step_g8_summary_report_plan.md).
No calc change — the Appendix A oracles and the ultimate-load contract are the
invariant.

### M4-2 — Unify `select_wing`/`one_engine_out` case identity
One case-ID authority per component end-to-end: derive `WingMassInput.cases`
from `envelope.critical` when not given; link `one_engine_out` to
`select_vtail`'s `CriticalCondition` list. Touches WINGINER/NETLOADS iteration →
oracle re-check required.

### M4-3 — ONENGOUT data-flow + turboprop gate
(a) v-tail geometry provenance (`vtail_loads` slice vs `geometry`) — derive or
document; (b) gate 23.367 on `is_turboprop` (or caption) so it can't silently
run for a reciprocating/turbofan multi (23.367(a) is turbopropeller-specific,
Ref 1 Ch 11 p87); (c) the Ch 11 Method allows **VSF** (flapped stall) as an
alternative VMC substitute — the case table uses only VS (clean) today; add VSF
or document the omission (surfaced during M1-5).

### M4-4 — Per-CG precise inertia in SELECT
Wire the persisted WTONECG per-CG inertia into SELECT's checked-maneuver `Iyy`
and v-tail `IZZ` (currently the Ch 9 approximations, which match the oracle).

### M4-5 — Aero-coefficient curve plot (decision D-10)
CL–α / drag-polar / CM plot on Aerodynamic Data with the recovered-CL closure
check — catches coefficient-entry errors, which matter more for concept
aircraft with hand-built polynomials.

### M4-6 — Ground-case distributed fuselage (and wing) loads + pressurization
The heaviest open calc item. Ground-case fuselage inertia/reaction distribution
(gear reactions as applied external loads at the LGFACTOR landing load factor);
optionally the wing distribution under ground reaction; a pressurization case
that is never down-selected against flight. **Acceptance:** ground condition
produces distributed fuselage shear/bending with free-free closure; pressurized
case retained independent of the governing flight case; FAR23 flight oracles
unchanged. Source narrative: `03_gui_rework_plan.md` §5 item (3).

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
  — M4-7 (shipped) wired the *carrier* (`safety_factor` on the four
  distributed-load results, read per result by `sbeam_bridge._sf()`); this item
  replaces the ad-hoc **policy** behind it, building on M4-13 (shipped — every
  producer now mints once) and M4-14 (shipped — read-side band validation and
  the shared `validation.safety_factor_valid` predicate).
  `one_engine_out` migrates to it as the first client.
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
ultimate-load contract — land deliberately with tests. **Layer 1 can ship
independently (M4-7's carrier and M4-13's per-producer mints are already in
place, and M4-14's read-side band validation closes the input side);
Layer 2 coordinates with Phase F25.**

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
`app/` must not import `sloads` underscore names — the `_wtenv_cg_limits` →
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

### M4-21 — Fuselage pitching load factor (Ch 15's missing half; split from M4-1)
Ch 15 (Ref 1 p103) says to multiply the station weights by the **linear and
pitching** load factors; `body_loads` applies only `NZ`. Add the d'Alembert pitch
term at each station, `f_i += -m_i * θ̈ * (x_i - x_cg)`, for the unbalanced /
abrupt-pitch conditions (23.423). It is self-equilibrating by construction —
`Σ m_i (x_i - x_cg) ≡ 0` by definition of the CG, so it adds **zero net force**
and a net moment of `-Iyy*θ̈`; i.e. the mass-weighted form of a linear
distribution with net moment and no net shear. **Not a closure mechanism:** for
the balanced trim points `θ̈ = 0`, so M4-1 stands on its own. Needs `θ̈`, hence
`Iyy` and an unbalanced pitching condition (`build_envelope` emits only balanced
trim points today) — pairs naturally with **M4-4** (per-CG precise inertia).

### M4-19 — Distributed fuselage aero pitching moment (Multhopp/Nelson; split from M4-1)
Step G4's `sloads/fuselage_moment.py` returns a **scalar** Munk slope
`dCm/dα = (k2-k1)*Vol/(S*mac)`, folded into `M1` for the trim solve only — the
body's own aero moment never reaches the beam, and the Munk form is the ideal-flow
limit (it assumes the local flow angle equals free-stream α at every station, so
it over-predicts the destabilizing slope for a real wing-body, typically by
10–40 %, because the aft body sits in downwash). Replace/extend with the Multhopp
strip form (Nelson, *Flight Stability and Automatic Control* §2.3, Eqs. 2.62–2.63;
same core as DATCOM 4.2.1.1 with its viscous cross-flow addition; primary sources
Multhopp NACA TM-1036, Gilruth & White NACA TR-711):

    Cm0,fus = (k2-k1)/(36.5*S*c̄) * ∫ w_f^2 * (α_0w + i_f) dx
    Cmα,fus =        1/(36.5*S*c̄) * ∫ w_f^2 * (∂ε_u/∂α)  dx

This buys three things Munk cannot: a **Cm0** (via body incidence `i_f`), wing
interference realism (`∂ε_u/∂α` > 1 ahead of the wing, small and recovering aft
of it), and a **per-station integrand** — a genuine distributed body pitching load
for `body_loads`, which also shifts `M_ub`. Keep the G4 scalar API as the integral
of the distribution so `flight_envelope._apply_fuselage_moment` is unchanged and
off-by-default stays off (Appendix A/B bit-for-bit). New inputs: `i_f` and the
wing root-chord station for the `∂ε_u/∂α` curve. Update
`reference/fuselage_pitching_moment.md` (which currently documents the Munk-only
scope and its deliberate omissions) alongside the calc.

### M4-20 — Deliverables render in the user-selected unit system

**Standard changed 2026-08-03** (`00_program_overview.md` *Deliverable units follow
the user's selection*; `SUMMARY_REPORT.md` §3.5): exports are no longer fixed to
Imperial — the whole bundle renders in the system the user chose. The docs are
updated; the code is not. Work:

- **Selection plumbing.** Add a unit-system field to `Project` (`SCHEMA_VERSION`
  bump + lenient migration; absent → Imperial) recording the *preference* only —
  `io.py` still never converts stored values. The GUI sidebar toggle writes it;
  add `--units imperial|si` to `cli.py`, overriding the field per run.
- **Unit-aware writers.** `report.py` (`load_cases_to_rows`, `text_report`,
  the module tables), the load-case CSV, `export/sbeam_bridge.py` (`FORCE`/`MOMENT`
  cards + span CSV) and the G8 report renderer take the system as a parameter and
  convert at that boundary. One system per bundle — the bundle writer passes a
  single value to every file, so two files can't disagree.
- **In-band statement.** BDF header comment naming the system; a units row or
  unit-suffixed column headers in each CSV; the report's title page and manifest.
- **Markers.** Extend `units.py` so the `-ULT` marker converts with the unit
  (`N-ULT`, `Nm-ULT`, `Pa-ULT`); **`Pa-ULT` is new** — there is no SI pressure kind
  today (`00_program_overview.md`'s load table had `—`). Add the design-pressure
  kind and its factor.
- **GUI.** The Export page states the system the bundle will be written in, beside
  the download control (`GUI_design.md` §7).
- **Tests.** Imperial output byte-identical to today (default path unchanged);
  SI round-trip Imperial → SI → Imperial lossless to display precision; a bundle
  asserts one system across report + CSV + BDF; KEAS/altitude unconverted in both.
  Appendix A/B oracles untouched (calc is not in this path).

**Blocks Step G8's units conformance tests** (`05_step_g8_summary_report_plan.md`
§10.1, resolved against this item). Note the aviation-standard carve-out is
retained: airspeed (KEAS) and altitude (ft) are never converted, and deliverables
say so.

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

### L-1 — sbeam stick model: real stiffness + assembled airframe
Real/parametric section properties (today `_MAT1_E = 1.0e7` placeholder) and an
assembled combined-airframe export. Granularity per **D-7**: load-cards-only
default; assembled stick model opt-in behind a flag.

### L-2 — Flaps-extended tail loads: printed oracle completion
M1-2 lands the p176 landing-config polynomials and the p178 oracle rows for the
envelope; completing the SELECT→TAILDIST flaps-extended pipeline against the
printed cases (81/106/88/108) still needs the CG5–7 loadings added to the
fixtures. Also fold in the LEV LAND balanced point (Appendix A case 90, the
sink-speed/attitude iteration `FLTLOADS.BAS` lines 3410–3600) — currently
omitted from the flap corner set and undocumented (review minor).

### L-3 — V-tail large-deflection factor EFV → SELECT ⚠️
**Not a simple wire-in — the naive fix breaks the 591-lb oracle by −47%**
(investigated 2026-07-16: `large_deflection_factor(30°, 0.353)=0.53`, not
~1.0). Reopen only after re-reading `SELECT.BAS` subroutines 8300/10000 to pin
down exactly what quantity the rudder EFV multiplies. The default-1.0
pass-through matches the oracle and stays until then.

### L-4 — Distinct Commuter category + VB
The 19,000-lb/19-seat tier is encoded but dormant; neither VB (23.335(d)) nor
the 66-fps rough-air gust (23.341) is computed anywhere (the BASIC suite
predates commuter support too). Note the commuter MC→MD margin rule
(23.335(b)(4)(iii): 0.07 / rational / 0.05 floor —
`reference/14CFR_MC_MD_speed_margin.md`). Land as one step when a concept
needs the tier.

### L-5 — FLTLOADS enroute / speed-control config
Third config — enroute (partial flaps / dive brakes / spoilers) with VPF
(UG §11.2.3, 23.373). Add an enroute `AeroCoeffSet` + VPF, or document the
omission (only then add 23.373 to the citation string).

### L-6 — AIRLOADS airplane-less-tail coefficient generation
The guide's windows 4/6/8 (fuselage/nacelle CM, gear aero, per-station stall
CL) — implement the coefficient generator or keep as a tracked scope gap
(coefficients are entered by hand today, documented).

### L-7 — WINGINER Table 15.1 completeness
Confirm vs WINGINER.BAS whether a THETADOT pitch-acceleration case is expected;
surface `DMYY` if a per-strip incremental torsion column is wanted.

### L-8 — UX / reporting parity batch (extended by the 07-19 and 07-21 reviews)
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

### L-9 — FAR23 printed-oracle backfills ⛔ *blocked on reference material*
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
  (revisit D-3's "closure proves insufficient" trigger when this lands — see the
  [resolved-decision register](../40_history/03_resolved_decisions.md)).
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

Decisions D-1 … D-11, once answered, moved to the register:
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md).

---

## Known defects (open) — index

Described in full above; this is the lookup.

- **M4-9** — report/export semantics keyed on display-label strings; a cosmetic
  relabel silently blanks CSV columns. **[Major, latent]**
