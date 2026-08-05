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
- **F25-5 — Pressurization & small gaps (S).** Part 25 combination rules into
  M4-6; the 23.415/25.415 ground-gust module (serves both parts).

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

### L-8a — SI-toggle & unit-label conformance in the GUI
The G6/G6b empennage + landing-gear sections hardcode ft²/in labels and ignore
the SI toggle — a `GUI_design.md §7` deviation. Make them respect the toggle
(adopting `unit_number_input`) or record the exception in `GUI_design.md §7`.
Pairs with **M4-20**, which fixed the same boundary on the export side.

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
