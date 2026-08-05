# Backlog — Open Work & Development Plan

The authoritative list of **open** items, in priority order: **M4**
(post-0.3.0), **Phase F25**, the long-tail refinements, future directions, and
the one open design decision.

Completed milestones (M1, M2, M2R, M3 and the M4 maintainability sequence) live
in [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).
Narratives: [`01_concept_loads_plan.md`](01_concept_loads_plan.md) (Phase C —
concept mode), [`03_gui_rework_plan.md`](03_gui_rework_plan.md) (Phase G — GUI
rework), [`05_step_g8_summary_report_plan.md`](05_step_g8_summary_report_plan.md)
(Step G8 — the summary report). Architecture:
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md);
per-module spec: [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md).

> **Lifecycle rule (hard requirement, per `CLAUDE.md`).** When an item here is
> finished, in the **same session**: (1) **remove** it from this file, (2) **add**
> it to [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
> with its full step record, and (3) add a `CHANGELOG.md` `[Unreleased]` entry.
> The backlog holds **open** items only — never leave a "✅ done" entry here.

**Definition of done** (every step closes against all of these): the module is
merged and self-registered; a `tests/test_<module>.py` passes (Appendix A/B
figures within ±0.1% where an oracle exists, else physics-closure); a Streamlit
page exists; the `Project` JSON schema is extended and round-trips in `io.py`
(`SCHEMA_VERSION` bumped, older files still load); and the docs are synced
(`PROGRAM_SPEC.md`, `20_theory/00_theory_sources.md`, this backlog → history,
`CHANGELOG.md`).

> **Invariant:** no calc-math change to the FAR23 path — Appendix A oracles pass
> throughout; concept mode reduces exactly to FAR23 on GA inputs; ultimate-load
> output rules hold; `workflow.py` stays the single source of navigation truth.

---

## Current state

All 22 Appendix-C programs are ported plus 2 modern modules (`configuration`,
`body_loads`). Phases 0–2, C, D, E, F, Phase 1, Phase G Steps **G0–G7** and
milestones **M1, M2, M2R, M3** are complete. The suite is green (ruff clean,
smoke test PASS), the FAR23 GA path is Appendix-A oracle-locked, and both
concept fixtures run end-to-end.

**Release status:** **sloads 0.3.0 cut 2026-07-23**, tag `v0.3.0`. The M4
maintainability sequence (M4-12, M4-11a, G8.1–G8.4a, M4-10, M4-9) shipped
2026-08-03/04; its deliberately-deferred remainders are **M3-3b**, **M4-10b** and
**M4-11b** below.

Reference-authority hierarchy: (1) `.BAS` listings + Appendix A printed output,
(2) User's Guide CFR quotes (Jan-1994), (3) Code-manual 1990 prose.

---

# M4 — Post-release (priority order)

### M4-20 — Deliverables render in the user-selected unit system **[first — unblocks M3-3b]**

**Standard changed 2026-08-03** (`00_program_overview.md` *Deliverable units follow
the user's selection*; `SUMMARY_REPORT.md` §3.5): exports are no longer fixed to
Imperial — the whole bundle renders in the system the user chose. The docs are
updated; the code is not.

- **Selection plumbing.** Add a unit-system field to `Project` (`SCHEMA_VERSION`
  bump + lenient migration; absent → Imperial) recording the *preference* only —
  `io.py` still never converts stored values. The GUI sidebar toggle writes it;
  add `--units imperial|si` to `cli.py`, overriding the field per run. Re-point
  `components._active_system()` at the new field (per D-16).
- **Unit-aware writers.** `report/` (`load_cases_to_rows`, `text_report`, the
  module tables), the load-case CSV, `export/sbeam_bridge.py` (`FORCE`/`MOMENT`
  cards + span CSV) and the G8 report renderer take the system as a parameter and
  convert at that boundary. One system per bundle — the bundle writer passes a
  single value to every file, so two files can't disagree.
- **In-band statement.** BDF header comment naming the system; a units row or
  unit-suffixed column headers in each CSV; the report's title page and manifest.
- **Markers.** Extend `units.py` so the `-ULT` marker converts with the unit
  (`N-ULT`, `Nm-ULT`, `Nmm-ULT`, `kPa-ULT`). Design pressure has no SI result
  mapping today.
- **GUI.** The Export page states the system the bundle will be written in, beside
  the download control (`GUI_design.md` §7).
- **Tests.** Imperial output unchanged but for its new unit statement (strip-and-
  compare, per D-21); SI round-trip lossless to display precision; a bundle
  asserts one system across report + CSV + BDF; KEAS/altitude unconverted in both.
  Appendix A/B oracles untouched (calc is not in this path).

The aviation-standard carve-out is retained: airspeed (KEAS) and altitude (ft)
are never converted, and deliverables say so.

**Plan, decisions D-19 … D-22 and the risk table:
[`06_m4-20_deliverable_units_plan.md`](06_m4-20_deliverable_units_plan.md)**
(2026-08-04). Seven sub-steps; the spine is a **two-channel** split — the
human-readable deliverables render N/mm/N·m/kPa, the sbeam decks render the
consistent solver set **N/mm/N·mm/MPa** (D-19: N·m in a deck whose GRIDs are mm
is a silent 1000× torsion error, and kPa is the same error for a pressure).

**Step 1 shipped 2026-08-04** — `units.py`'s deliverable unit sets
(`Channel`/`DeliverableUnits`/`deliverable_units`/`units_statement`), the two
latent-defect fixes it carried (`lb-in` and `lb/in^2` had no SI mapping, so
**1580 values across the six examples** stayed Imperial inside an otherwise-SI
table; the dead `"knot"` row is gone), and the D-20 doc amendment
(`Pa-ULT` → `kPa-ULT`) with the D-19 solver-channel carve-out written into
`00_program_overview.md`, `SUMMARY_REPORT.md` §3.5 and CLAUDE.md.
**Step 2 shipped 2026-08-04** — `Project.unit_system` at **schema v38** (a
preference only; additive with a total default, so it needs no migration hop),
`units.unit_system_from`, CLI `--units imperial|si` with `resolve_units`
(flag → project → Imperial), and the sidebar toggle now writing the project field
so a unit change reads as an unsaved change (D-22). `components.active_system()`
re-pointed at the field — one function, no call-site changes.

**Step 3 shipped 2026-08-04** — the human channel: `io.load_cases_csv` /
`write_load_cases_csv` take `system=` and convert **once**, inside the writer.
`report/render.py` was not touched — it reads each `LoadValue.units` string, so
the SI column headers (`N-ULT`, `Nm-ULT`, `mm`) fell out of the existing
`_detect_unit`, and `Speed (kt)` / `Altitude (ft)` are byte-identical in both
systems. A guard pins `load_cases_csv` as the sole `convert_results` caller in
`io.py`, so the channel keeps exactly one conversion point.

**Step 4 shipped 2026-08-04** — the solver channel. `export/coordinates.py` is
the single scale point (`to_grid`/`to_force`/`to_moment`/`to_pressure`, which now
**raise** on a dimensionally inconsistent unit set), and all 17 sbeam writers take
`system=`. CSV cells go through the same three functions the cards do, so a span
CSV cannot disagree with the deck beside it. `--units si --export-sbeam` now
works; the temporary refusal is gone. **The solver set gained `MPa`:** step 1 left
pressure at the human channel's `kPa`, which is the D-19 defect one dimension over
(pressure is force/length², so an N/mm deck reads stresses in N/mm² = MPa), and
`is_consistent` now checks both derived dimensions. Imperial output changed by
**zero numeric characters** across all six examples × wing/tail/control — only
header rows and two `$` comment lines (D-21).

**Step 5 shipped 2026-08-04** — the in-band statement. `methods_statement` takes
`system=` and gains a `UNITS:` paragraph, so the block already wrapped per channel
(G8-3) carries the unit set into every file at once: `# UNITS: …` in each CSV,
`$ UNITS: …` in each BDF, the paragraph in `METHODS.txt`; the workbook, which has
no comment rows, gets a `Units` row on its *Project* sheet. The statement is
**bundle**-wide and names both channels (in SI: `N·m, kPa` for the readable files,
`N·mm, MPa` for the decks), because one stamp lands on both. The BASIS `-ULT`
marker list is now derived from the unit sets instead of hard-coded, and
`units_statement` names all four dimensions. **Defect fixed:** the Export page
built a `bdf_comment_block` and never applied it, so the four `.bdf` decks carried
*no* methods or units statement at all — every BDF writer now takes
`header_comment=` and a source test pins all five deck artifacts.

**Remaining: steps 6–7** — the Export page (it still calls the writers without a
system, so GUI downloads stay Imperial until step 6) and close-out.

### M3-3b — Step G8 remainder: the report document itself

G8.1–G8.3 and G8.4's coverage matrix shipped 2026-08-04 (the `sloads/report/`
package, the v36 document-control fields, the methods & limitations statement in
every export channel, the FAR 23 Subpart C coverage matrix). What remains is the
document:

- **G8.4 (rest) — `content.py`.** `Project` + `run_all_modules()` →
  `ReportDocument` (§§1–4 of the structure). Pure and fully testable on its own;
  `coverage.py` is already built and exported for it to consume. **This sub-step
  is unit-system-independent and may start before M4-20 lands.**
- **G8.5 — `latex.py` + `plots_tex.py`.** The `.tex` renderer (escaping,
  `longtable`, document-control block) and the three pgfplots figures (V-n,
  weight/CG, speed–altitude — the third has no GUI equivalent and is new work).
  **Blocked on M4-20**: a renderer written against the Imperial-only writers has
  to be retrofitted (`05_step_g8_summary_report_plan.md` §10.1).
- **G8.6 — `export/pdf.py` + the Export-page section.** Engine discovery
  (`tectonic` → `latexmk` → `pdflatex`), compile in a temp dir, surface failure
  as a caption. Write it against the existing `components.page` /
  `unit_number_input` helpers.
- **G8.7 — doc sync + close-out.**

Plan, locked decisions G8-1…G8-4 and the test matrix:
[`05_step_g8_summary_report_plan.md`](05_step_g8_summary_report_plan.md).
Document standard: [`../10_standard/SUMMARY_REPORT.md`](../10_standard/SUMMARY_REPORT.md).

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
or document the omission.

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
  class → factor + basis. Consumed by **both** `report/` **and** `sbeam_bridge`.
  `one_engine_out` migrates to it as the first client. **Can ship independently** —
  the carrier (M4-7), the per-producer mints (M4-13) and the read-side band
  validation (M4-14) are all in place.
- **Layer 2 — agreed failure cases (project input; Phase F25 / 25.302).** A `Project`
  slice of **named** system-failure factors — `(name, far_reference="25.302",
  agreed_sf, basis)` — e.g. **`25.302 — MLA Loss → SF 1.25`**. These are *not* code
  constants and *not* computed from a probability by the tool: in practice loads and
  systems **agree** the SF per program (it depends on the demonstrated system
  reliability), so it is an engineering **input**. Each entry (a) renders as its own
  ULTIMATE load case (`25.302 MLA Loss`, `SF=1.25`, `lbs-ULT`) and (b) **records a
  design requirement levied on the system** — a loads↔systems interface artifact the
  tool can later surface as a "system reliability requirements" list. The resolver
  overlays these named factors on the Layer-1 defaults. **Coordinates with Phase F25.**

**Note:** this is a *practical* 25.302 (agreed named-failure-case factors), distinct
from the full probabilistic **Appendix K** method, which the F25 gap analysis keeps
out of scope — see [`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md).

**Acceptance:** one resolver is the sole authority for every non-1.5 factor; `report/`
and `sbeam_bridge` produce identical factors for the same case; `one_engine_out`
migrated with oracles/tests unchanged; a Layer-2 named case (e.g. MLA loss @ 1.25)
round-trips through `io.py` and renders as `lbs-ULT SF=1.25`. Touches the CLAUDE.md
ultimate-load contract — land deliberately with tests.

### M4-10b — Retire the `tail_loads`/`vtail_loads` property proxies
`Project.tail_loads`/`.vtail_loads` are properties over
`geometry.empennage.htail`/`.vtail` whose setter **silently no-ops** when
assigning `None` to a project with no geometry (`models/project.py`, warning block
beside the definition). Replacing them with plain reads of `geometry.empennage.*`
is a ~90-site mechanical change (**73 reads, 19 writes** across 21 files), and the
risk is the **writes**: each of the 19 changes assignment semantics, so each needs
looking at rather than a regex. Kept separate from M4-10's migration chain
(shipped) so any regression is attributable.

**Acceptance:** the properties and their setters are gone from `models/project.py`;
all 6 examples still round-trip byte-identically; every frozen fixture in
`tests/fixtures_schema/` still loads; `test_migrations.py`'s
`test_pre_g6_file_lands_its_tail_slices_on_the_empennage` is rewritten against the
direct path.

### M4-11b — Split the highest-complexity view functions **[maintainability]**
The scaffold helpers (`unit_number_input`, `page_header`/`page`) exist and are
tested (M4-11a); the complexity-splitting half did not ship. CC re-measured with
`radon` on 2026-08-04:

| function | file | CC |
|---|---|---|
| `_tab_design_speeds` | `structural_speeds.py` | **F (72)** |
| `_three_view` | `configuration_layout.py` | **F (63)** |
| `_tab_vn` | `flight_envelope.py` | **F (44)** |
| `_tab_cg_inertia` | `weight_mass.py` | **E (40)** |
| `_subject_from_project` | `aircraft_comparison.py` | **E (34)** |
| `_tab_trim` | `flight_envelope.py` | **E (33)** |

Split each into seed / form / render (and `landing_reactions` per attitude), and
finish adopting `unit_number_input` in the views that still hand-pair
`to_display`/`to_imperial_scalar`. **Note `engine_mount` is already correct by a
different route** — it converts the whole `EngineInput` at Apply via
`units.to_imperial`, so per-field adoption there would double-convert; either
leave it or migrate the whole page in one move. `radon` is in the `dev` extra
(D-17, reporting only) — re-measure before and after.

### M4-22 — Flight Envelope: SELECT Apply also persists un-applied geometry edits **[Minor defect]**
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

### M4-23 — `flight_envelope.density_ratio` duplicates `constants.standard_atmosphere` **[Minor defect]**
`density_ratio` (promoted from `_sigma` in M4-12b) reproduces the sigma computed
by `constants.standard_atmosphere` bit-for-bit. Collapse to one authority —
`density_ratio` becomes a thin read of `standard_atmosphere`, or is deleted and
its callers re-pointed. Numerically inert by construction: assert the Appendix A
oracles and both concept fixtures are unchanged.

### M4-21 — Fuselage pitching load factor (Ch 15's missing half)
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

### M4-19 — Distributed fuselage aero pitching moment (Multhopp/Nelson)
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

---

# Phase F25 — FAR 25 concept coverage (post-0.3.0)

Extend the FAR 23 analyses into a **FAR 25 static surrogate** for
transport-category concepts. Full gap analysis, comparison table, and step
details: [`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md)
(2026-07-20). Pattern throughout: opt-in supplement per module (the shipped
`engine.include_far25` flag is the template); FAR 23 path untouched; every
Part 25 result carries the "static surrogate — not certification" banner.

**Preconditions met.** The label-string / io / app walls the 2026-07-21 review
wanted cleared before the supplement wave — M4-9, M4-10 and M4-11a — all shipped
2026-08-04. Only M4-11b remains of that batch, and it does not gate a new
quantity.

- **F25-0 — Verify pass (S, first).** Pull current CFR text for every
  *(verify)* row into `reference/14CFR_Part25_loads_extracts.md`; correct the
  gap table; freeze parameters. *(First row done 2026-07-20:
  `reference/14CFR_MC_MD_speed_margin.md`.)*
- **F25-1 — Transport category "T" envelope pack (M).** 25.337 floor 2.5 /
  negative −1.0; VB (25.335(d)); transport gust corner set — Pratt engine with
  the 25.341 U_ref schedule + F_g; MZFW design weight.
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
(The *practical* 25.302 case is Layer 2 of **M4-8** and is in scope there.)

---

# Long tail — refinements & scope extensions (priority order)

### L-1 — sbeam stick model: real stiffness + assembled airframe
Real/parametric section properties (today `_MAT1_E = 1.0e7` placeholder) and an
assembled combined-airframe export. Granularity per **D-7**: load-cards-only
default; assembled stick model opt-in behind a flag.

### L-2 — Flaps-extended tail loads: printed oracle completion
M1-2 landed the p176 landing-config polynomials and the p178 oracle rows for the
envelope; completing the SELECT→TAILDIST flaps-extended pipeline against the
printed cases (81/106/88/108) still needs the CG5–7 loadings added to the
fixtures. Also fold in the LEV LAND balanced point (Appendix A case 90, the
sink-speed/attitude iteration `FLTLOADS.BAS` lines 3410–3600) — currently
omitted from the flap corner set and undocumented.

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

### L-8a — SI-toggle & unit-label conformance in the GUI
The G6/G6b empennage + landing-gear sections hardcode ft²/in labels and ignore
the SI toggle — a `GUI_design.md §7` deviation. Make them respect the toggle
(adopting `unit_number_input`) or record the exception in `GUI_design.md §7`.
Pairs with **M4-20**, which fixes the same boundary on the export side.

### L-8g — CLI exports carry no methods & limitations stamp
`cli.py`'s `-o` load-case CSV and its `--export-sbeam` CSVs/BDFs have never
carried the G8.3 methods block that the GUI bundle stamps into every file, so a
headless export states its ULTIMATE basis, category and approved corrections
nowhere. (Units *are* stated — the column headers and the decks' `$` axis
comments carry them since M4-20 steps 3–5 — so this is a G8.3 coverage gap, not a
units one.) The writers already take `header_comment=`; the work is deciding
whether a headless export should change bytes, and threading
`csv_comment_block`/`bdf_comment_block` through `_export_sbeam`. Found while
implementing M4-20 step 5.

### L-8h — Three result units still have no SI mapping
`units._RESULT_TO_SI` has no entry for `ft^2` (6 values, wing area), `lb/ft^2`
(6, wing loading) or `ft/s` (5, sink rate), so those cells stay Imperial inside an
otherwise-converted SI table — the same class of defect M4-20 step 1 fixed for
`lb-in` and `lb/in^2`, at ~1/90th the count. (`ft`, 104 values, is altitude and is
correctly carved out.) Deferred from M4-20 step 1 because none is a *load*
quantity, so none reaches a deliverable through the ultimate boundary.

### L-8b — `help=` tooltip rollout completion
App-wide tooltip coverage is ~45%. Worst pages: flap loads 0/6, one-engine-out
0/7, wing loads 2/10 (structural speeds is complete at 21/21); the G6/G6b
sections add ~30 untooltipped widgets. Finish the rollout page by page.

### L-8c — Results/Export consolidation parity
Results Review "All results by section" omits the 8 folded modules' results —
map folded → host step so they appear. Human-label the folded-module CSVs on
Export ("balloads (CSV)" → a descriptive name).

### L-8d — Widget freshness audit (deferred from M2-7)
Input widgets pass both `key=` and `value=`, so Streamlit's session_state can win
over the project-seeded `value=` and show a stale field after the project changes
underneath (cross-page Apply, programmatic load). **Not a data-loss bug** (Apply
is required to persist, and per-page unit-suffixed keys limit the blast radius);
audit the `key=`+`value=` widgets and re-seed on a project change, or prove it
cannot occur. `tests/test_persistence.py` locks the data-persistence half.

### L-8e — Uncovered input fields & UX nits
Add widgets (or a documented JSON-only status) for the remaining uncovered
fields: `speeds.chosen_va`/`chosen_vf`, `one_engine_out.speeds_kt`,
`weight.envelope.fuselage_nose_x`/`fuselage_tail_x`. Plus: de-jargonize error
strings (no internal slice names); move the Geometry parametric form and the
Flight-Envelope altitude Apply out of the sidebar (or visually anchor them);
first-run Loads Plots info should use the linked `gate()`; the OEO "define ≥2
engines" warning needs a page link; save-filename sanitization; `st.spinner` on
heavy recomputes; migrate off the deprecated `use_container_width`.

### L-8f — Display-only and numerically-inert nits **[lowest priority]**
None of these change a load. V-n plot negative closure should show −1.0 at VD for
U/A categories (loads are right; display only); chosen VA is silently clamped to
VC (BASIC only raises — warn instead); 190-lb occupant caption for U/A
(23.25(a)(2)); MC-vs-MD Mach cap on cruise stall-line conditions (numerically
inert — comment or match BASIC); ENGLOADS `prop_blades` captured but unused;
AILERON positive-deflection coercion undocumented; WTONECG YBAR omitted;
TAILDIST average-chord only (not the guide's N-station-chord variants,
Figs 20.7–20.10).

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
- **Methods manual / DER package**: a consolidated front section (scope,
  assumptions, method per FAR condition group, approved deviations,
  oracle-vs-closure table) assembled from theory-sources + PROGRAM_SPEC +
  docstrings; then per-module walkthroughs in the `engine_loads.md` style
  (SELECT and FLTLOADS first).

---

## Open design decisions requiring user input

- [ ] **D-5 — Appendix B twin fixture (blocks L-9).** The swept (C7) and
  ONENGOUT (C9) printed oracles want the 10-place twin turboprop as a fixture,
  but Appendix B is **not in the bundled PDF**. *Can the user supply a legible
  Appendix B or the original `.INP`/`.OUT` files?* Until then
  `examples/twin_turboprop.project.json` can't be built and these oracles stay
  blocked. **(Reviewed 2026-07-20: keep blocked as-is.)**

D-1 … D-18 (all but D-5) are answered and recorded in
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md).

---

## Known defects (open) — index

Described in full above; this is the lookup.

- **M4-22** — Flight Envelope: the SELECT-inputs **Apply** also persists
  un-applied geometry/altitude edits (`flight_envelope.py:324` writes the probe
  copy). **[Minor]**
- **M4-23** — `flight_envelope.density_ratio` duplicates
  `constants.standard_atmosphere`'s sigma bit-for-bit. **[Minor]**
- **F25-2 (concept mode)** — no Mach-margin VD route exists, so the FAR 23
  `1.25·VC` floor binds unconditionally and inflates every dive-speed case on
  transport-class concepts. **[Major — scoped into F25-2, not a standalone fix]**
