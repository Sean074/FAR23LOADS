# Backlog — Open Work & Development Plan

The authoritative list of **open** items, mission-tagged and in priority order.
Items off the mission path live in [`02_parked.md`](02_parked.md) — real but
unscheduled; move them back here before working them. Completed milestones live
in [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).
Narratives: [`01_concept_loads_plan.md`](01_concept_loads_plan.md) (Phase C —
concept mode), [`03_gui_rework_plan.md`](03_gui_rework_plan.md) (Phase G — GUI
rework), [`05_step_g8_summary_report_plan.md`](05_step_g8_summary_report_plan.md)
(Step G8 — the summary report). Architecture:
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md);
per-module spec: [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md).

> **Lifecycle rule (hard requirement, per `CLAUDE.md`).** When an item here is
> finished, in the **same session**: (1) **remove** it from this file, (2) record
> it in [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
> at the depth its **closure tier** requires (S/M/L — see the CLAUDE.md tier
> table), and (3) add a `CHANGELOG.md` `[Unreleased]` entry. The backlog holds
> **open** items only — never leave a "✅ done" entry here.

**Naming rule (2026-08-05):** existing IDs (M4-x, F25-x, L-x) are kept for
traceability, but **no new parallel ID series** — new items get a descriptive
name here and a plain step identity at promotion.

**Definition of done** (every calc step closes against all of these): the module is
merged and self-registered; a `tests/test_<module>.py` passes (Appendix A/B
figures within ±0.1% where an oracle exists, **else a stated physics-closure /
invariant gate in CI — benchmark-first, written with the feature, per
`CLAUDE.md`**); a Streamlit page exists; the `Project` JSON schema is extended
and round-trips in `io.py` (`SCHEMA_VERSION` bumped, older files still load);
and the docs are synced per the closure tier.

> **Invariant:** no calc-math change to the FAR23 path — Appendix A oracles pass
> throughout; concept mode reduces exactly to FAR23 on GA inputs; ultimate-load
> output rules hold; `workflow.py` stays the single source of navigation truth.

---

## Mission (2026-08-05)

**A demonstrated concept-loads → sbeam sizing loop:** a concept configuration
goes in, per-component distributed ULTIMATE loads come out as `FORCE`/`MOMENT`
cards, and an exported deck **solves in sbeam with verified global equilibrium**
— continuously, in CI, not as a one-time check. The FAR23 replication core stays
oracle-locked throughout. Items are tagged **[E]** (essential to that loop) or
**[V]** (valuable, not blocking).

## Current state

All 22 Appendix-C programs are ported plus 2 modern modules (`configuration`,
`body_loads`). Phases 0–2, C, D, E, F, Phase 1, Phase G Steps **G0–G7** and
milestones **M1, M2, M2R, M3** are complete. The suite is green (ruff clean,
smoke test PASS), the FAR23 GA path is Appendix-A oracle-locked, and both
concept fixtures run end-to-end.

**Release status:** **sloads 0.3.0 cut 2026-07-23**, tag `v0.3.0`. The M4
maintainability sequence (M4-12, M4-11a, G8.1–G8.4a, M4-10, M4-9) shipped
2026-08-03/04; **M4-20** (deliverable units), **M3-3b** (Step G8 — the summary
report document) and **M4-2** (unified case identity + deck SUBCASE map, schema
v39) closed 2026-08-04/05. `[Unreleased]` is release-ripe — **cut 0.4.0** per the
cadence rule in `RELEASE_PROCESS.md`.

Reference-authority hierarchy: (1) `.BAS` listings + Appendix A printed output,
(2) User's Guide CFR quotes (Jan-1994), (3) Code-manual 1990 prose.

---

# Mission path (priority order)

### [E] sbeam round-trip CI harness *(new 2026-08-05, process review R9)*
C4's acceptance ("the exported BDF parses and solves in sbeam") was checked once
and never gated; the mission's core claim currently has no regression test.
Build a CI job/test that exports the flagship concept fixture's governing cases
via `--export-sbeam`, runs an actual sbeam solve on the deck (sbeam as a dev
dependency or a pinned checkout), and gates on: solve succeeds; reactions
balance the applied cards; spot-check values (root shear/bending vs the sloads
span CSV) within tolerance. **This is the single highest-value new test in the
project.** Effort: S–M. Pairs with the equilibrium invariant below (run it on
the same decks).

### [E] Global equilibrium invariant on exported decks *(new 2026-08-05, R9)*
Nothing asserts that an exported case's wing + body + tail cards sum to the
case's `n·W` with zero net moment about the reference point — closure today is
per-module. Add an export-boundary check (test + optional runtime warning):
for each exported case, Σ`FORCE` = n·W (within tolerance) and Σ moments ≈ 0
about the deck reference, in deck units. Cheap (S) and catches every future
seam error at the boundary where it matters.

### [E] M4-8 — Centralized two-layer safety-factor policy (foundation for 25.302) **[architecture]**
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
  class → factor + basis. Consumed by **both** `report/` **and** `sbeam_bridge`.
  `one_engine_out` migrates to it as the first client. **Can ship independently** —
  the carrier (M4-7), the per-producer mints (M4-13) and the read-side band
  validation (M4-14) are all in place. **[E — Layer 1]**
- **Layer 2 — agreed failure cases (project input; Phase F25 / 25.302).** A `Project`
  slice of **named** system-failure factors — `(name, far_reference="25.302",
  agreed_sf, basis)` — e.g. **`25.302 — MLA Loss → SF 1.25`**. These are *not* code
  constants and *not* computed from a probability by the tool: in practice loads and
  systems **agree** the SF per program (it depends on the demonstrated system
  reliability), so it is an engineering **input**. Each entry (a) renders as its own
  ULTIMATE load case (`25.302 MLA Loss`, `SF=1.25`, `lbs-ULT`) and (b) **records a
  design requirement levied on the system** — a loads↔systems interface artifact the
  tool can later surface as a "system reliability requirements" list. The resolver
  overlays these named factors on the Layer-1 defaults. **Coordinates with Phase F25.
  [V — Layer 2]**

**Note:** this is a *practical* 25.302 (agreed named-failure-case factors), distinct
from the full probabilistic **Appendix K** method, which the F25 gap analysis keeps
out of scope — see [`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md).

**Acceptance:** one resolver is the sole authority for every non-1.5 factor; `report/`
and `sbeam_bridge` produce identical factors for the same case; `one_engine_out`
migrated with oracles/tests unchanged; a Layer-2 named case (e.g. MLA loss @ 1.25)
round-trips through `io.py` and renders as `lbs-ULT SF=1.25`. Touches the CLAUDE.md
ultimate-load contract — land deliberately with tests.

### [E] M4-6 — Ground-case distributed fuselage (and wing) loads + pressurization
The heaviest open calc item. Ground-case fuselage inertia/reaction distribution
(gear reactions as applied external loads at the LGFACTOR landing load factor);
optionally the wing distribution under ground reaction; a pressurization case
that is never down-selected against flight. **Acceptance:** ground condition
produces distributed fuselage shear/bending with free-free closure; pressurized
case retained independent of the governing flight case; FAR23 flight oracles
unchanged. Source narrative: `03_gui_rework_plan.md` §5 item (3).
**Export note (2026-08-05):** the ground cases' gear-attachment reactions should
also reach the sbeam deck as `FORCE` cards at the gear attachment stations —
scope the deck half here rather than as a separate item.

### [E] L-1 — sbeam stick model: real stiffness + assembled airframe
Real/parametric section properties (today `_MAT1_E = 1.0e7` placeholder) and an
assembled combined-airframe export. Granularity per **D-7**: load-cards-only
default; assembled stick model opt-in behind a flag. **Note (2026-08-05):** the
load-application-axis question below should be answered before or with this item.

---

# Valuable (opportunistic — small, independent, or paired with a mission item)

### [V] Load-application axis vs elastic axis — document the torsion reference *(new 2026-08-05, R9)*
The exported `FORCE` application points sit on the sloads load-reference line;
`export/coordinates.py` documents frames but not the **shear-center/elastic-axis
offset** question — what torsion a deck consumer should attribute when the sbeam
beam axis differs from the load line (sbeam itself has no shear-center offset;
its grid line *is* the elastic axis). Write the convention into
`export/coordinates.py` + `PROGRAM_SPEC.md` sbeam-bridge section and stamp it in
the deck `$` header. Doc-only (S); prevents a silent-wrong-torsion class at the
consumer.

### [V] Gust spanwise-distribution decision *(new 2026-08-05, R9)*
Gust cases currently reuse the maneuver (Schrenk-based) spanwise shape.
Decide-and-document (or change): is that adequate for the concept mission, or do
gust cases need their own distribution? One study + a recorded decision in the
resolved-decision register (S). Not a defect — an undocumented assumption.

### [V] F25-0 — Verify pass (S, precedes any F25 build step)
Pull current CFR text for every *(verify)* row into
`reference/14CFR_Part25_loads_extracts.md`; correct the gap table; freeze
parameters. *(Done so far: 2026-07-20 `reference/14CFR_MC_MD_speed_margin.md`; 2026-08-08 `reference/14CFR_25_335_design_airspeeds.md` — 25.335(a)/(b)/(d) verbatim, which cleared the three *(verify)* tags in gap-analysis §1.3.)*

### [V] Upset-criterion speed increase (25.335(b)(1) / 23.335(b)(4)(i)) *(new 2026-08-08, from F25-2)*
25.335(b) requires the **greater of** the Mach margin and the (b)(1) upset
criterion: from stabilized flight at VC/MC, upset, flown 20 s along a path 7.5°
below the initial one, then pulled up at 1.5 g (0.5 g increment) — per
AC 25.335-1A. F25-2 shipped the Mach term only, so the margin check is
explicitly **not a sufficiency demonstration** and every margin-route output
says so. This closes that gap. Needs a drag/thrust model over the 20 s dive (the
rule permits calculation "if reliable or conservative aerodynamic data is
used"), so it is a real piece of work, not a formula. Effort: M. Reference text
already captured: `../../reference/14CFR_25_335_design_airspeeds.md`.

### [V] Mach-margin route for the FAR 23 categories *(new 2026-08-08, from F25-2)*
23.335(b)(4) offers the margin route to normal/utility/acrobatic (0.05 M) and to
commuter (0.07 M, rational analysis down to 0.05). F25-2 withheld it from all of
them (decision F25-2-a) so the Appendix A oracles stayed provably untouched;
`vd_basis = "mach_margin"` in a FAR 23 category currently raises. The machinery
is already in place — this is a category gate plus a per-category default in
`resolve_mach_margin`, and an oracle-unchanged test. Pairs with the dormant
"Distinct Commuter category" item. Effort: S.

### [V] Flutter-clearance Mach basis for transport concepts *(new 2026-08-08, from F25-2)*
MACHLIM's `MFC = 1.2·MD` is GA-lineage (MACHLIM.BAS, Ref 1 Ch 6). Even with the
RJ's dive speed corrected it gives **MFC 1.021** — transonic nonsense for a
subsonic transport, where flutter clearance is conventionally MD + ~0.05–0.10 M
(and 23.629/25.629 are framed as a margin, not a ratio). Noticed while
reproducing the F25-2 dive-speed defect. Needs a verified reference and a
recorded decision **before** any change — the 1.2 factor is oracle-locked to
Appendix A p160 (MFC 0.4836), so a change must be an opt-in variant, not an edit
to the GA path. Effort: S (study + decision) then S (variant).

### [V] F25-1 — Transport category "T" envelope pack (M)
25.337 floor 2.5 / negative −1.0; **VB per 25.335(d)** (F25-2 accepts VB as an
input and checks the 25.335(a) ordering; **computing** it, and the full
`VC ≥ VB + 1.32·U_ref` margin, both land here with the U_ref schedule — the VB
formula is the Pratt K_g already in the gust engine, so it is cheap once U_ref
exists); transport gust corner set —
Pratt engine with the 25.341 U_ref schedule + F_g; MZFW design weight.
Identity test: "T" with FAR 23 parameters reproduces the FAR 23 envelope. The
dive-speed machinery is already built (F25-2): "T" inherits
`structural_speeds.resolve_mach_margin` and the `vd_basis` enum unchanged — only
the category gate widens.
(Pattern: opt-in supplement per module, FAR 23 path untouched, "static
surrogate — not certification" banner. Full gap table:
[`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md).)

### [V] F25-4 — Ground-loads parameter variant (M)
LGFACTOR at 10/6 fps, lift = W, LDW/MTOW pairing; LANDLOAD tables documented as
surrogate. Coordinates with M4-6.

### [V] M4-3 — ONENGOUT data-flow + turboprop gate
(a) v-tail geometry provenance (`vtail_loads` slice vs `geometry`) — derive or
document; (b) gate 23.367 on `is_turboprop` (or caption) so it can't silently
run for a reciprocating/turbofan multi (23.367(a) is turbopropeller-specific,
Ref 1 Ch 11 p87); (c) the Ch 11 Method allows **VSF** (flapped stall) as an
alternative VMC substitute — the case table uses only VS (clean) today; add VSF
or document the omission.

### [V] M4-4 — Per-CG precise inertia in SELECT
Wire the persisted WTONECG per-CG inertia into SELECT's checked-maneuver `Iyy`
and v-tail `IZZ` (currently the Ch 9 approximations, which match the oracle).

### [V] M4-21 — Fuselage pitching load factor (Ch 15's missing half)
Ch 15 (Ref 1 p103) says to multiply the station weights by the **linear and
pitching** load factors; `body_loads` applies only `NZ`. Add the d'Alembert pitch
term at each station, `f_i += -m_i * θ̈ * (x_i - x_cg)`, for the unbalanced /
abrupt-pitch conditions (23.423). It is self-equilibrating by construction —
`Σ m_i (x_i - x_cg) ≡ 0` by definition of the CG, so it adds **zero net force**
and a net moment of `-Iyy*θ̈`; i.e. the mass-weighted form of a linear
distribution with net moment and no net shear. **Not a closure mechanism:** for
the balanced trim points `θ̈ = 0`, so M4-1 (shipped) stands on its own. Needs `θ̈`,
hence `Iyy` and an unbalanced pitching condition (`build_envelope` emits only
balanced trim points today) — pairs naturally with **M4-4**.

### [V] M4-19 — Distributed fuselage aero pitching moment (Multhopp/Nelson)
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

### [V] L-8g — CLI exports carry no methods & limitations stamp
`cli.py`'s `-o` load-case CSV and its `--export-sbeam` CSVs/BDFs have never
carried the G8.3 methods block that the GUI bundle stamps into every file, so a
headless export states its ULTIMATE basis, category and approved corrections
nowhere. (Units *are* stated — the column headers and the decks' `$` axis
comments carry them since M4-20 steps 3–5 — so this is a G8.3 coverage gap, not a
units one.) The writers already take `header_comment=`; the work is deciding
whether a headless export should change bytes, and threading
`csv_comment_block`/`bdf_comment_block` through `_export_sbeam`. Found while
implementing M4-20 step 5. **Note (M4-2):** every deck now carries its own `$`
subcase-map block regardless of `header_comment`, so a headless deck already
states its case identity — this item is now only about the methods/basis block.

### [V] L-8i — Per-page LIMIT CSVs ignore the unit toggle and state no units
`wing_loads`, `fuselage_loads`, `tail_loads` and `loads_plots` each build a
download CSV from their own row dicts (`csv.DictWriter` over `wing_load_rows(...)`
and friends) instead of a `sloads` writer, so those files are **Imperial in both
systems** — while the table rendered above them on the same page is converted —
and their column headers carry no unit at all. They are the LIMIT analysis-page
channel (the `CLAUDE.md` carve-out allows LIMIT *display*), but a downloaded file
still leaves the tool, so it owes a unit statement. The work is per-page: convert
the rows with the page's existing display helper and give the headers
unit-suffixed names, the same shape M4-20 step 4 applied to the sbeam CSVs. Found
while implementing M4-20 step 6; pairs with **L-8a** (parked).

### [V] Split `40_history/00_completed_development.md` by era *(new 2026-08-05, R11)*
6,038 lines and the third-most-churned file in the repo. Split by era/area with
an index file (the sbeam `40_history` layout is the template); with the tiered
closure rule, S-tier items become one-line entries. Deferred from the 2026-08-05
process-doc session because the file carries uncommitted in-flight changes.
Mechanical (S); do after the current working tree is committed.

---

## Open defects (index)

- **Derived ACRL wing case disagrees with the worked example's air load [Minor,
  found 2026-08-05 by M4-2's decision-7 gate].** With `wing_mass.cases` left empty,
  `wing_inertia.resolve_wing_cases` derives the wing cases from `envelope.critical`.
  Nz/Nx then reproduce the Appendix A figures closely for every ga6 condition, but
  the **ACRL** air-load point does not: SELECT's 23.349(a)(2) pick carries CL ≈ 1.30
  at 117.4 kt where the worked example (Ref 1 p217-221) enters CL 1.55 at 116 kt —
  a ~19% air-load difference for the same named condition. A derived ACRL case also
  carries `unbal_moment = 0`, since SELECT's condition does not name the unbalanced
  rolling moment (it comes from AILERON, Ch 13). **Only the derived route is
  affected** — every shipped example enters its cases explicitly, and explicit
  always wins — so no oracle or deliverable moves today. Decide which point ACRL
  should name (and where the rolling moment comes from) before the derived route is
  recommended for anything but a first pass. Pinned by
  `tests/test_wing_case_derivation.py::test_the_acrl_divergence_is_the_documented_one`,
  which fails if the two ever start agreeing — at which point close this and make
  the assertion an equality.
- **ATR-42 example: seven balanced points sit above the stall CL at 25,000 ft
  [Minor, found 2026-08-05 by M4-5's stall-clamp closure].** In
  `examples/atr42_100.project.json`, MAN A / MAN C / AC ROLL at 25,000 ft carry a
  balanced CL up to **1.767 against a Mach-adjusted stall CL of 1.478** (+0.29).
  The local Mach is pinned exactly at MC = 0.4555, so `_balance`'s
  dynamic-pressure iteration cannot raise q any further and never brings CL back
  onto the stall line: the airplane cannot reach n = 2.5 at that altitude within
  its own Mach cap and CLmax. The loads reported at those points are therefore
  not physically attainable. Not a solver defect and not an oracle fixture — a
  property of that example's speeds/altitude set (or of the Mach-cap handling:
  arguably the balance should report such a corner as *infeasible* rather than
  returning an unconverged point). Decide which, then either fix the fixture's
  altitude list / CLmax or teach `_balance` to flag a Mach-capped non-convergence.
  Pinned by
  `tests/test_aero_curves.py::test_the_atr42_stall_exceedance_is_the_documented_mach_capped_one`,
  which fails if the count or the cause changes. The GA oracle and both concept
  fixtures close cleanly.
- **M4-22 — Flight Envelope: SELECT Apply also persists un-applied geometry edits [Minor].**
  `app/views/flight_envelope.py:324` — the SELECT-inputs form handler writes the
  page's *probe copy* back to session state (`st.session_state["project"] =
  project`), and that copy already carries `fl_effective` from line 178. So
  pressing **Apply** inside the "SELECT search inputs" expander silently commits
  whatever the user typed into the **Apply geometry & altitudes** form (XTC / XTF /
  reference Mach / the altitudes editor) without pressing that form's own Apply —
  the M2-3 "persist only on Apply" contract, violated for a different form's
  fields. **Fix:** the SELECT handler should write only `select_input` onto the
  session project (`st.session_state["project"].select_input = si`), never the probe
  copy. Add a test asserting the SELECT Apply leaves `flight_loads` untouched — it
  fails today.
- **M4-23 — `flight_envelope.density_ratio` duplicates `constants.standard_atmosphere` [Minor].**
  `density_ratio` (promoted from `_sigma` in M4-12b) reproduces the sigma computed
  by `constants.standard_atmosphere` bit-for-bit. Collapse to one authority —
  `density_ratio` becomes a thin read of `standard_atmosphere`, or is deleted and
  its callers re-pointed. Numerically inert by construction: assert the Appendix A
  oracles and both concept fixtures are unchanged.
- **Conventions-extraction findings (2026-08-05) [Minor, S — batch as one fix].**
  From the `CONVENTIONS.md` charter extraction (§8 there): (a) `load_keys.py:11-12`
  cites `tests/test_load_keys.py` as its uniqueness guard but **the test file does
  not exist** — write the guard or fix the docstring; (b) `constants.py:15` cites
  25.303 as the SF authority while `report/methods.py:230` and the docs cite 23.303
  — align on 23.303 (Part 25 as equivalent); (c) add an explicit comment on
  `coordinates.py`'s module-level Imperial/SOLVER default; (d) `units.py` carries
  three partially-shared SI factor maps — consolidation candidate.

---

## Open design decisions requiring user input

- [ ] **D-5 — Appendix B twin fixture (blocks parked L-9).** The swept (C7) and
  ONENGOUT (C9) printed oracles want the 10-place twin turboprop as a fixture,
  but Appendix B is **not in the bundled PDF**. *Can the user supply a legible
  Appendix B or the original `.INP`/`.OUT` files?* Until then
  `examples/twin_turboprop.project.json` can't be built and these oracles stay
  blocked. **(Reviewed 2026-07-20: keep blocked as-is.)**

D-1 … D-18 (all but D-5) are answered and recorded in
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md).
