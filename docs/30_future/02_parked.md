# Parked Items — off the mission path

Created 2026-08-05 (development process review,
[`../50_reviews/2026-08-05_development_process_review.md`](../50_reviews/2026-08-05_development_process_review.md),
R6). Items here are genuine and keep their full write-ups, but they are **not on the
path to the mission** stated in [`00_backlog.md`](00_backlog.md) (a demonstrated
concept-loads → sbeam sizing loop) — general completeness, GUI polish, and
reference-blocked oracle work. Nothing here is scheduled or ranked. To activate an item,
move it back to `00_backlog.md` with a mission tag; do not work parked items without
moving them first.

---

## M4 deferrals

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

---

## Phase F25 deferrals

(F25-0/1/2/4 remain in the backlog; details and the full gap table in
[`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md).)

- **F25-3 — Maneuver & tail surrogates (M).** Checked-maneuver 25.331(c)(2)
  static evaluation; yaw overswing case; 25.427/25.349 schedule checks.
- **F25-5 — Small gaps (S).** The 23.415/25.415 ground-gust module (serves both
  parts). *(The Part 25 ΔP combination rules that were the item's other half are
  out of scope as of 2026-08-14 — decision **D-24**, pressurization removed.)*

---

## Long tail — refinements & scope extensions

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
**The keyed half of the data-loss class shipped 2026-08-21 as #51** — a *project
generation* stamped into every project-seeded widget key
(`app_shell/widget_keys.py`), bumped once per project replacement (`adopt`, and
the JSON editor's Apply) and guarded by `tests/test_widget_freshness.py`. That
sweep also settled the rationale above: `app/views/`' Apply step defers the
overwrite to the user's click rather than preventing it, so those views were
stamped too. **The unkeyed half shipped 2026-08-22, closing #51's reopen:** the
98 `app/views/` widgets that carried no `key=` at all — whose Streamlit identity
derived from their *arguments*, stable whenever the seed value repeats, so a
value typed before a load survived it (reproduced on `structural_speeds`' VB
against `atr42_100`) — now all carry stamped keys, landed as one pass with
#44's unit-boundary rollout (`unit_number_input` stamps for its callers). The
guard's "no `key=` is per-render" premise was inverted to fail closed, with a
type-then-load reproduction test and a per-key shell allowlist. What stays
parked *here* is the rest of the audit — a widget that goes stale while the
project is **mutated** underneath it (a cross-page Apply, a seed chain), which
no generation bump covers because the project was never replaced.

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

### L-8h — Three result units still have no SI mapping
`units._RESULT_TO_SI` has no entry for `ft^2` (6 values, wing area), `lb/ft^2`
(6, wing loading) or `ft/s` (5, sink rate), so those cells stay Imperial inside an
otherwise-converted SI table — the same class of defect M4-20 step 1 fixed for
`lb-in` and `lb/in^2`, at ~1/90th the count. (`ft`, 104 values, is altitude and is
correctly carved out.) Deferred from M4-20 step 1 because none is a *load*
quantity, so none reaches a deliverable through the ultimate boundary.

### L-9 — FAR23 printed-oracle backfills ⛔ *blocked on reference material*
Close each as a mini-step **only if** a legible Appendix B / `.INP`/`.OUT`
surfaces (see backlog decision D-5): AIRLOAD4 swept printed spanwise table;
ONENGOUT printed twin oracle; LANDLOAD printed wheel-load matrix (p231–233 is
OCR-garbled — the reaction matrix stays closure-/legible-cell-locked).

---

## Parked 2026-08-16 — scope and deficiency review

Moved here by the 2026-08-16 review ([`../50_reviews/2026-08-16_scope_and_deficiency_review.md`](../50_reviews/2026-08-16_scope_and_deficiency_review.md) §2.2/§2.3): each item's stated effect on a delivered load is below the base method's own error bar, or the item is outside the FAR 23 mission (the Part 25 pack), or its consumer does not exist yet. Bodies are kept in full. **Power effects:** the seven-step plan of note 21 is parked; the *thrust `FORCE` at the engine hub* was carved out of it and stays ranked in the backlog. **Step 14:** the indeterminate-path half (continuous fuselage, carry-through element, redundant hinges — note 24 R-12) is parked here without a body of its own; the descoped row shipped 2026-08-17 as **consumer-editable** per-family `PBAR`/`MAT1` cards in the LRA deck (`lra_model.SECTION_FAMILIES`) — no input path, by decision: section properties are the sizing tool's output, so the seam is the deck, not the schema.

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

### [V] M4-4 — Per-CG precise inertia in SELECT
Wire the persisted WTONECG per-CG inertia into SELECT's checked-maneuver `Iyy`
and v-tail `IZZ` (currently the Ch 9 approximations, which match the oracle).

### [V] M4-3 — ONENGOUT data-flow + turboprop gate
(a) v-tail geometry provenance (`vtail_loads` slice vs `geometry`) — derive or
document; (b) gate 23.367 on `is_turboprop` (or caption) so it can't silently
run for a reciprocating/turbofan multi (23.367(a) is turbopropeller-specific,
Ref 1 Ch 11 p87); (c) the Ch 11 Method allows **VSF** (flapped stall) as an
alternative VMC substitute — the case table uses only VS (clean) today; add VSF
or document the omission.

**(b) sharpened by the fixture-data step (2026-08-13).** The turbofan case is now
a *stated* limitation rather than an unexamined one: `PROPELLER_ONLY_NOTE` owns
the wording and it ships as the `engine-failure-propeller-only` standing
limitation in every methods-and-limitations stamp. `concept_regional_jet` was
therefore **dropped** from that step and enters no `one_engine_out` slice — run
with a shaft-power surrogate it produced ~41–52 klb fin loads that never recover
(windmill drag identically zero on a 0-in propeller disc), i.e. exactly the
"wrong card outranks a missing card" case. **(b) closed 2026-08-16:** the run
is refused when the failed engine has no propeller diameter (`_case_inputs`
raises `MissingInputError`); (a) and (c) remain parked here.

### [V] `concept_heavy` has no landing-gear geometry and no `landing` slice *(new 2026-08-14, from step 10 decision G-13)*
It is the one shipped fixture with neither, so it produces no LANDLOAD output, no
gear load report and no ground cases of any kind. Two things it would buy, both
unavailable elsewhere: a **sixth** gear-report fixture (that artifact needs only
LANDLOAD output and gear geometry — no derivable mass loading — so its coverage
is 5 of 6 where the assembled ground cases reach only 2), and the only
**concept-mode** exercise of the FAR 23.473(g) `N ≥ 2.67` / `NLG ≥ 2.0` floor
warning, which is warn-only and has never fired on a shipped fixture. It would
**not** buy assembled ground cases — its single CG case is not derivable from its
weight database, the same pinned finding as the twins. Pure fixture data: gear
axle geometry at three strut states, tread, tyre/hub, strut stroke, tail-down
angle and three roled `GROUND` cases. Tier S. Effort: S.

### [V] M4-8 Layer 2 — agreed named failure-case factors (25.302) **[architecture]**
Layer 1 shipped 2026-08-14 as the **governing safety-factor table**
(`sloads/safety_factors.py`; history entry "Step 10 piece 1"). What remains is
Layer 2, which has a **different source of authority**: a `Project` slice of
**named** system-failure factors — `(name, far_reference="25.302", agreed_sf,
basis)`, e.g. **`25.302 — MLA Loss → SF 1.25`**. These are not code constants and
are not computed from a probability by the tool: in practice loads and systems
**agree** the factor per program, from the demonstrated system reliability, so it
is an engineering **input**. Each entry (a) renders as its own ULTIMATE load case
(`25.302 MLA Loss`, `SF=1.25`, `lbs-ULT`) and (b) records a **design requirement
levied on the system** — a loads↔systems interface artifact the tool can later
surface as a "system reliability requirements" list.

The shipped table is already the right shape to carry them: a named failure case
is one more row, with `status = override`'s declaration machinery (mandatory
basis, report + methods-stamp marking) reused unchanged. What it needs is the
input slice, the case-generation side, and `classify()` learning to route a named
failure case to its own row rather than to the family its FAR reference implies.
This is a *practical* 25.302, distinct from the full probabilistic **Appendix K**
method, which the F25 gap analysis keeps out of scope — see
[`../20_theory/01_far25_gap_analysis.md`](../20_theory/01_far25_gap_analysis.md).
**Acceptance:** a Layer-2 named case round-trips through `io.py` and renders as
`lbs-ULT SF=1.25`, and the governing table states it with its basis. Coordinates
with Phase F25. Effort: M.

### [V] CG-dependent MTOW — a non-flat weight–CG envelope top edge *(new 2026-08-14, from step 10 decision G-14)*
G-14 fixes MTOW as a **single scalar, constant between the forward and aft CG
limits** — the common case, and a stated assumption in the weights basis. On some
airplanes (the Boeing 777 among them) the maximum take-off weight **varies with
CG**, so the weight–CG envelope's top edge is not flat and the permissible weight
falls off toward one or both CG limits. Closing this means a permissible-weight
*boundary* rather than a scalar, plus the check that every entered loading sits
under it. The machinery is not as far away as it looks: the envelope is already
non-rectangular in the other direction — `WeightEnvelopeInput.fwd_regardless_weight`
makes the **forward** CG limit weight-dependent (ga6: 2,800 lb against a 3,400 lb
gross) — so this is a change to an existing boundary concept, not a new one.
Needs a decision on the input form (breakpoint pairs vs a second gross-weight
anchor) before code. Tier M. Effort: M.

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

### [V] Power effects on the wing — propeller-wake loads *(new 2026-08-15, user; design note agreed; the **hub thrust card** carved out and shipped 2026-08-17, #10 — the wake stays parked)*
Every wing case in the suite **was** exactly zero-thrust when this was parked
(measured: no powerplant `source` in any balanced case; the x-closure is the
drag alone, GA-6 PHAA `n_x = −0.61 g`) — and still is unless a thrust is
entered. The **hub thrust card was carved out of this item and shipped
2026-08-17** (#10): an entered `EngineInput.thrust_lb` puts one `engine-thrust`
source per engine into every flight case, and the x-closure becomes
`n_x = (D − ΣT)/W`. What stays parked is everything this item is really
about — the wake. The only power physics the suite models is FLAPLOAD's
slipstream, which stops at the flap panel, and ENGLOADS' 23.361/23.371
torque/gyro stop at the mount, although for a wing-mounted engine the rule
names "the mount **and its supporting structure**". Design note
[`21_power_effects_wing_note.md`](21_power_effects_wing_note.md) — **agreed
2026-08-15, decisions P-0…P-12** — settles: DATCOM §4.6.1–4.6.3 as the default
estimator (Digital DATCOM ex3 case 4 vs 3 is the printed oracle) with
field-by-field user override and the momentum-theory band as the single
distribution rule; `N_p` included; take-off power flaps-down / max-continuous
flaps-up; a `power_policy.py` table (the `safety_factors.py` pattern) minting a
`-P` variant of every clean wing family + `SLIP-P` on `BAL 1.4VSF` + Kind I
`361A1/361A2/371-k` (at VA) into the wing box; re-trim at V-n level then
assemble (the 1 % gate applies); pair torque reacted by an aileron-trim couple;
V-n and design speeds stay power-off; h-tail `-P` families under the same table;
v-tail terms deferred to L-7; user-defined thrust line (hub + incidence + toe);
`AeroCoeffSet.power_state` provenance flag. Sequencing in the note §8:
**the `atr42_100`/`dhc8_dash8` prerequisite is discharged** (Pri 5 / D-26,
2026-08-15, gave both their flight balanced cases; the note was written when
neither assembled one on HEAD) and the pre-Amdt-64 CFR pull. Rule basis pre-Amdt-64
FAR 23. Tier L. Effort: L (7 steps). Next artefact: the code implementation plan.

---

## Future directions (not yet scoped — placeholders, much later)

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
