# Backlog — Open Work & Development Plan

The authoritative list of **open** items, restructured (2026-07-20) around the
**path to the first concept-loads release** — three release milestones (M1–M3),
a post-release milestone (M4), the long-tail refinement list, and future
directions. Items carry their prior backlog IDs and/or the 2026-07-19 project
review IDs in parentheses for traceability
(see [`PROJECT_REVIEW_2026-07-19.md`](../../PROJECT_REVIEW_2026-07-19.md)).

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

> **Invariant (unchanged):** no calc-math change to the FAR23 path *except* the
> reviewed correctness fixes in M1, each of which lands with its own printed-
> oracle or listing-traceable test; Appendix A oracles pass throughout; concept
> mode reduces exactly to FAR23 on GA inputs; ultimate-load output rules hold;
> `workflow.py` stays the single source of navigation truth.

---

## Current state (as of 2026-07-20)

All 22 Appendix-C programs are ported plus 2 modern modules (`configuration`,
`body_loads`). Phases 0–2, C, D, E, F, Phase 1, and Phase G Steps G0–G6b are
complete (see history). The full suite is green (see CI for the current count;
401 passed at the 2026-07-20 snapshot, ~92% coverage), the FAR23 GA path is
Appendix-A oracle-locked, and the full-airframe concept fixture
(`examples/concept_regional_jet.project.json`) runs all 19 applicable modules
end-to-end through the concept branch with physics-closure tests.

The **2026-07-19 project review** (five parallel passes: two technical vs the
reference PDFs, GUI-live, docs/naming, backlog/release) found the port
essentially exact wherever a printed oracle exists, and a cluster of defects
exactly where the oracle net has holes. Those findings are the core of M1/M2
below. The review also settled the reference-authority hierarchy:
**(1) `.BAS` listings + Appendix A printed output, (2) the User's Guide's CFR
quotes (Jan-1994 text), (3) the Code manual's 1990 theory prose** — verify in
that order; the two PDFs each contain errors the other corrects (VD-minimum
prose vs 23.335; 23.361(c) pre-/post-Amdt-23-45 text; Nx sign).

---

# M1 — Correctness & traceability (release-blocking)

Calculation fixes from the review. Each is small, lands with a new oracle or
listing-traceable test, and updates `00_theory_sources.md` where the doc
currently records the defective behavior as if it were the source.


### M1-4 — 23.427 unsymmetrical tail: restore the full candidate set (review T6) **[Major — decided 2026-07-20: restore BASIC behavior]**
`select.py` filters `"UNCHECKED"` out of the 23.427 candidate search;
`SELECT.BAS` (lines 6025–6070) loads all 12 conditions including both unchecked
maneuvers, and 23.427 combines with "the loads prescribed in 23.421 **through**
23.425". The unchecked maneuver is frequently the largest H-tail load —
excluding it is non-conservative and was an undocumented deviation. **Fix:**
include the unchecked conditions, matching the BASIC; regression-test against
the Appendix A unsymmetrical rows; while there, check the RH-side sign
convention (BASIC signs by the case's balancing load `SGN(LT(HZCASE))`).

### M1-5 — One-engine-out 23.367(a)(2) case: `safety_factor = 1.0` (review T7)
The "VC (ultimate)" condition carries the default SF 1.5 although 23.367(a)(2)
loads are defined as ultimate (both references agree) — the export double-
factors it. One-line fix + test on the rendered units string.

### M1-6 — VC/VD coefficient clamp at W/S ≥ 100 (review T9)
`constants.py` keeps tapering K1/K2 past W/S = 100; FAR 23.335 and
STRSPEED.BAS clamp at 28.6 / 1.35. Inert for GA, non-conservative for the
heavy-concept band this tool targets. Two-line fix + boundary test.

### M1-7 — Aft-gross ballast reference point (review T8)
`weight_envelope.py` uses the full discretionary loading as the aft-gross
reference; the manual's hand calc (Ref 1 p28) uses the heaviest loading **not
exceeding gross** (3322 lb → 78 lb @ 103.7). The module returns 0 lb on the
manual's own database while its docstring claims the 78/418/158 match. Mirror
the `reg_cands` "≤ gross" logic; test against the p28 triple.

### M1-8 — AIRLOAD4 Mach threshold 0.4 vs 0.5 (was 2-14) *(verify)*
`airloads.py:73` triggers the swept/high-Mach branch at `design_mach > 0.4`;
the User's Guide says **0.5** (§9.1, §10.1). Verify vs Ref 1 Ch 12 /
AIRLOAD4.BAS; if 0.4 is unsourced, change `_AIRLOAD4_MACH` to 0.5, else
document the conservatism. (The 15° sweep trigger matches.)

### M1-9 — FLAPLOAD slipstream power: takeoff HP (was 2-15; review confirms) *(verify → fix)*
`flap.py` prefers `max_cont_hp`; FAR 23.457(b) specifies **takeoff power** and
the review confirmed both PDFs quote it (Ref 1 p109; UG p14-2; FLAPLOAD.BAS's
"MAX HP OF ONE ENGINE" prompt is the only ambiguity). Prefer `takeoff_hp`;
keep the Appendix A oracle (which used 250 hp) passing.

### M1-10 — Documentation consistency sweep (review D1–D3)
(a) **Reference filenames:** 17 citations across 8 docs point at
`reference/FAR23 loads (1).pdf` / `ADA324952.pdf`; the actual files are
`FAR23Loads_Code.pdf` / `FAR23Loads_UserGuide.pdf`. Global find-and-replace.
(b) **README/CLAUDE.md currency:** schema/test counts and the two-generations-
stale nav description ("4-phase sidebar"); stop baking hard counts into prose —
point at CI/CHANGELOG. (c) **Appendix-B status:** one canonical statement
("Appendix A oracle-locked; Appendix B absent from the bundled PDF; these
modules closure-locked") linked from README/PROGRAM_SPEC/theory doc instead of
the current contradiction. (d) Move the approved-corrections **register of
record** from `CLAUDE.md` into `docs/20_theory/` (CLAUDE.md links to it), and
add the User's Guide §17.2.1 (post-1994 CFR text) citation to
`engine_loads.md` as further corroboration of the 23.361(c) correction.

---

# M2 — Usability & robustness (release-blocking)

GUI and release-mechanics fixes from the review (G-numbers) plus the surviving
Phase-G steps. GUI evidence: review §2 screenshots.

### M2-1 — Loads Plots must recompute from the project (review G2)
The page reads `Project.loads`, which no code path ever constructs — phase 5
is permanently empty with instructions that cannot succeed. Recompute via
`build_net_loads`/`build_body_loads`/`build_tail_chordwise` exactly as
`export_report.py` does; delete the dead `if project.loads is not None`
guarded writes across the five loads views.

### M2-2 — Navigation: show the whole workflow; link between pages (review G3+G6)
`st.navigation(..., expanded=True)` so phases 3–6 (incl. Export) aren't hidden
behind "View 10 more"; `st.page_link` in the dashboard checklist and in every
"go set X first" gating message; fix the stale page names in those messages
("Wing Geometry", "Configuration & Layout").

### M2-3 — Dirty flag: move on-render writes into Apply handlers (review G4)
`structural_speeds.py` and `flight_envelope.py` (views) write to the project on
render, so "Unsaved changes" trips with zero user edits and the discard-confirm
dialog fires spuriously. Move the writes into the submit handlers; add a test
that a render pass leaves the project hash unchanged.

### M2-4 — Results Review header tables: units, ULT marking, SF (review G5)
The "Governing loads (SELECT)" tables drop `LoadValue.units` and the mandatory
`-ULT`/SF marking and print literal "None" in sparse cells — on the page whose
job is consolidated deliverable loads. Render units+ULT in headers (as Wing
Loads does), SF column, "—" for absent values.

### M2-5 — Aircraft Comparison: surface-planform fallback + phase move (review G7)
The subject aircraft shows "None" for W/S, span, area with the shipped examples
(reads the parametric layout; examples carry `geometry.surfaces`). Fall back to
surface-derived values; move (or link) the page into the Develop phase — the
fleet check belongs at definition time, not after Export.

### M2-6 — Step G6c — Geometry single-source cleanup (wing + fuselage tightening)
Close the remaining softer geometry double-entry surfaced by the G6 audit.
**Wing:** `FlightLoadsInput.mac`/`wing_area_sqft`/`xw`/`zw`,
`WingMassInput.dihedral_deg`/`wrp_waterline`, `LandingInput.wing_area_sqft`
become pure read-throughs from `Project.geometry`, override only behind an
explicit checkbox (STRSPEED's design-weight pattern). **Fuselage:** the
`GeometryInput.fuselage` outline is the sole shape source; the scalar
`LayoutInput` length/width/height present as a derived summary.
**Acceptance:** no wing/fuselage geometric quantity stored as an independently
editable copy without an override toggle; fixtures/oracles unchanged;
save→reload no-op.

### M2-7 — Step G7 — Persistence verification (G-3)
Verify every input-bearing value lives on a `Project` slice `io.py` round-trips
(no input-only `st.session_state`); drive save→reload on each example project
(now at schema 28) and diff. **Acceptance:** save→reload of every example is a
no-op; no input page holds input data outside `st.session_state["project"]`.

### M2-8 — Landing default CG derivation (review, landing minor)
`landing._cg_cases` derives "aft max landing" and "fwd max landing" from the
**same** heaviest mass case — the fwd/aft distinction is degenerate and
nose-gear/braked-roll loads are under-predicted unless explicit `cg_cases` are
given (UG fig 18.2 uses three distinct loadings). Derive fwd/aft stations from
the WTENV structural envelope, or refuse to auto-derive and require explicit
`cg_cases`; also consider the 23.473(g) floors (N ≥ 2.67, NLG ≥ 2.0) as a
warning note in concept mode.

### M2-9 — `scripts/smoke_test.sh` portability
Hardcodes `.venv/bin/*`; fails on any machine that installs differently. Use
`python -m` invocations / the active interpreter.

### M2-10 — Operational-speed linkage on the Design Speeds page (decided 2026-07-20: all three tiers)
The design speeds bound the eventual **operating limitations** — the page must
explain and surface this. Primary sources: Ref 1 **p47** (VNE/MNE = 0.9·VD/MD;
yellow arc VC→VNE; turbine airplanes use VMO/MMO ≤ VC/MC with the 23.335(b)(4)
margin — ≥ 0.05 Mach between MC and MD or the flight-test upset margin) and
FAR 23.1505 (VNE ≤ 0.9·VD; VNO ≤ lesser of VC or 0.89·VNE), 23.1511
(VFE ≤ VF), 23.629 (flutter clearance to 1.2·VD/MD — the MFC line MACHLIM
already outputs). Three tiers, one step:
- **Explain:** an expander on the Design Speeds tab presenting the constraint
  ladder with the citations above.
- **Derive:** a pure `operational_implications(speeds, mach)` calc returning
  the implied preliminary placards (VNE = 0.9·VD, MNE = 0.9·MD,
  VNO = min(VC, 0.89·VNE), VMO/MMO caps = VC/MC, VFE cap = VF, arc
  boundaries), rendered as a read-only advisory panel with an "operating
  limitations are set at certification (Subpart G), not by this tool" caption;
  unit-tested against the GA6 figures.
- **Constrain:** optional operational **targets** on `StructuralSpeedsInput`
  (target VNE or VMO/MMO, VNO, VFE + a turbine/no-yellow-arc flag; schema
  bump, lenient migration). On Apply, invert the ladder into required design
  minima (target VNE ⇒ VD ≥ VNE/0.9; target MMO ⇒ MD ≥ MMO + 0.05; target
  VMO ⇒ VC ≥ VMO; target VFE ⇒ VF ≥ VFE) and warn concretely when the chosen
  design speeds are infeasible; hook into `validation.py` so infeasibility
  also surfaces on the dashboard.
**Built on M1-1** (the VD floor fix, now landed) — an implied VNE from the
under-floored VD would have propagated the error into the advisory. Display/
validation only; no loads-math change. *(S–M; unblocked.)*

### M2-11 — Input data dictionary + short GUI user guide (review D4, part 1)
(a) A `project.json` **data dictionary** — field, type, units, default, owning
page, consuming modules — generated from the dataclasses (the schema is 28
versions deep and the only reference is `models.py`). (b) A **5–10 page GUI
user guide**: the workflow phases, what to enter where, the seed chain,
LIMIT-vs-ULTIMATE reading rules, one end-to-end `ga6_normal` walkthrough with
three or four hand-checkable numbers (the data already exists in the 0.2.0
verification baseline — it needs narrative).

---

# M3 — Cut the release: **sloads 0.3.0** (concept-loads v1)

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
Sean). **Attribution stays prominent:** describe the heritage as a modern open
replication of the FAR23 loads suite, citing the very public FAA/DOT report
**DOT/FAA/AR-96/46** (User's Guide for FAR23 Loads Program, 1997) and the
Hal C. McMaster CAE manual, with an explicit **non-affiliation** sentence
naming McGettrick Structural Engineering and DARcorporation.
**Acceptance:** one name everywhere (grep for `farloads`/`FAR23LOADS`/"FAR 23
LOADS" finds only the historical-attribution passages); imports/CLI/tests
green; docs and examples updated; disclaimer present in README and the GUI
footer/About.

### M3-2 — Release cut per `RELEASE_PROCESS.md`
Version 0.3.0; date and cut the (currently ~3-phases-deep) `[Unreleased]`
changelog; refresh the verification baseline as
`40_history/02_verification_baseline_0.3.0.md` **including the new M1 oracle
rows** (p155 VD, p178 landing-config, sweep closure, 23.427 set) and a
one-page **oracle-vs-closure status table**; run the fixed smoke test; tag.

### M3-3 — *Stretch:* Step G8 — Summary report (Export phase)
The consolidated four-section loads report (`03_gui_rework_plan.md` §4 Phase 6):
input summary; envelope plots (V-n, weight/CG, speed/altitude); conditions +
FAR coverage; results summary (VMT wing/fuselage, control/flap, gear, engine).
All load figures ULTIMATE with SF. **Include a methods/limitations statement
stamped into the exported deliverables** (CSV/BDF/report) so downstream sizing
inherits the concept-mode caveat the UI already shows. Ships with 0.3.0 if M1/M2
go fast; otherwise first item of M4.

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
run for a reciprocating/turbofan multi.

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

---

# Phase F25 — FAR 25 concept coverage (post-0.3.0)

Extend the FAR 23 analyses into a **FAR 25 static surrogate** for
transport-category concepts. Full gap analysis, comparison table, and step
details: [`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md)
(2026-07-20). Pattern throughout: opt-in supplement per module (the shipped
`engine.include_far25` flag is the template); FAR 23 path untouched; every
Part 25 result carries the "static surrogate — not certification" banner.

- **F25-0 — Verify pass (S, first).** Pull current CFR text for every
  *(verify)* row into `reference/14CFR_Part25_loads_extracts.md`; correct the
  gap table; freeze parameters.
- **F25-1 — Transport category "T" envelope pack (M).** 25.337 floor 2.5 /
  negative −1.0; VB (25.335(d)); transport gust corner set — Pratt engine with
  the 25.341 U_ref schedule + F_g; MZFW design weight. Depends on M1-6
  (M1-1/2 landed).
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
turbulence, 25.362, rational taxi, Appendix K.

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
predates commuter support too). Land as one step when a concept needs the tier.

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

### L-8 — Minor UX / reporting parity batch (was 2-21, extended by review notes)
ENGLOADS `prop_blades` captured but unused; AILERON positive-deflection
coercion undocumented; WTONECG YBAR omitted; TAILDIST average-chord only (not
the guide's N-station-chord variants, Figs 20.7–20.10). Plus review nits:
V-n plot negative closure should show −1.0 at VD for U/A categories (loads are
right; display only); chosen VA silently clamped to VC (BASIC only raises —
warn instead); 190-lb occupant caption for U/A (23.25(a)(2)); MC-vs-MD Mach cap
on cruise stall-line conditions (numerically inert; comment or match BASIC);
dashboard "Schema version" metric and BASIC program names are developer-facing;
save-filename sanitization; add `st.spinner` on the heavy recomputes; migrate
off the deprecated `use_container_width`.

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
- **M2-1** — Loads Plots page can never display results (`Project.loads` never
  constructed). **[Major, GUI]**

*(The Step-G6 half-migration breakage found by the 2026-07-19 review was
resolved 2026-07-20 — suite green, concept fixture runs end-to-end; see
history.)*
