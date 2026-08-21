# Oracle GUI — a second front-end over the one analysis model

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-08-19 (owner, in session) — the oracle GUI is the next
development phase.** OG-A (the `bas` sentinel defect, §3) shipped 2026-08-19 as
an independent tier-S fix; everything else is unbuilt. The GUI freeze is lifted
for this note's work (§8). One decision was added at agreement — **OG-14**, the
single registry — which changes what OG-5 / step OG-C build; the rest of the
note is agreed as written.

A **second, independently launched Streamlit GUI** that exposes only the
capability of the original McMaster **FAR 23 LOADS** suite: the original
programs' inputs, and **CSV + text** output. It exists beside the current
`app/` GUI. Both are thin shells over the **same** `sloads/` calc package —
the aim stated by the user 2026-08-19 is *"two GUI interfaces, one analysis
model"*, with the oracle interface simply using much less of the analysis
tools.

This note is **architecture and scope**, not physics. No oracle moves, no load
equation changes, no schema hop (OG-13). `CONVENTIONS.md` is cited only for the
LIMIT→ULTIMATE output contract (§5), which the new front-end inherits rather
than re-implements.

Sources reviewed: `CLAUDE.md` (architecture, tiered closure, required
practices), `PROJECT_GUIDE.md` §4/§7, `PROGRAM_SPEC.md` (module→UG § map, the
22/20 program counts), `sloads/workflow.py`, `sloads/models/inputs.py`,
`sloads/io.py`, `sloads/report/render.py`, `app/Home.py`, `app/components.py`,
`app/limit_csv.py`, `app/views/*.py`, `tests/test_page_links.py`,
`tests/test_ultimate_contract.py`, `tests/test_package_layout.py`,
`50_reviews/2026-08-16_gui_user_review.md` (the GUI freeze).

---

## 1. Why this is not a fork

`CLAUDE.md` already states the architecture this note relies on: *"Shared pure-calc
package + thin I/O shells. Calc never does I/O; GUI, CLI and tests are
interchangeable front-ends."* An oracle GUI is a **third front-end** beside
`app/` and `cli.py`. Nothing in `sloads/` is added, branched or conditioned on
which GUI is running.

**Measured — the calc is not leaking into the view layer today.** The 22 files
in `app/views/` carry 0–9 module-level `def`s each (median 1) against 6–17
`sloads` imports each: they call owners, they do not compute. The dual-path risk
is therefore **not** in the views. It is one level up, in the app-layer shell —
`app/components.py` (325 LOC), `app/limit_csv.py` (128 LOC) and `app/Home.py`'s
project open/save/units/dirty-guard. Both GUIs need all three, and a copy is
exactly the dual path this note exists to prevent (OG-4).

## 2. Measured baseline (2026-08-19, `examples/ga6_normal.project.json`)

`ga6_normal` **is** the Appendix A GA-6 airplane, so what it populates is the
closest thing the repo has to the original suite's own data set.

| Quantity | Value |
|---|---|
| Distinct input schema paths in `Project` (list indices collapsed) | **295** |
| — plain scalar fields | 182 |
| — columns inside repeating lists (~12 tables) | 113 |
| Leaf slots fully expanded | 722 |
| Populated by `ga6_normal` | 466 |
| Registered calc modules that **run** on `ga6_normal` unmodified | **22 of 23** |

The single non-runner is `one_engine_out` (`MissingInputError` — its slice is
absent), and that is correct: ONENGOUT is an original program with no case on a
single-engine airplane. `ga6_normal` also leaves `safety_factors`,
`include_far25`, `envelope`, `loads` and all six metadata fields empty.

**This is the load-bearing measurement of the note: the oracle chain already
runs on a proper subset of the input model.** Nothing has to be bent to allow a
reduced-input front-end; the reduced input set is already sufficient.

**Where the reduction actually is.** Most of the 182 scalars map onto the
original programs' data screens. The clear sloads additions among scalars are
modest: metadata (6), the FAR 25 / concept speed targets and Mach-margin route
in `speeds` (~10), `geometry.landing_gear` and its `landing` duplicate (~18),
`lateral_body_aero`, the aileron/flap span-placement fields (~8), and the
derived caches (`flight_loads.mac/wing_area_sqft/xw/zw`). **The list half is
where the cut lands**: `MassItem` carries 12 columns of which the original
needed roughly three (name, weight, arm) — `y`, `z`, `ixx`, `iyy`, `izz`,
`component`, `consumable`, `wing_fraction` are all sloads mass-model work — and
`weight.cg_cases[]` (7 columns) and the fuselage outline/section geometry are
sloads entirely. Estimated oracle set: **~120–140 scalars + ~4 tables (~30
columns)**, i.e. roughly half the total surface but ~75 % off the table half,
which is where the current UI's bulk sits (`weight_mass.py` 853 LOC,
`configuration_layout.py` 952 LOC).

The estimate is an estimate. OG-5 replaces it with a classified, guarded list.

**Measured, 2026-08-19 (OG-C + G5):** **219 of 323** fields are `ORIGINAL`, plus
11 the front-end supplies — so the oracle GUI leaves **93** fields (29 %) at
their defaults, not the ~50 % this section guessed. The estimate was low in one
specific place and it is worth recording why: it assumed the wing planform
polylines and the per-item inertias were sloads' and could be dropped. Both are
inputs of a named `.BAS` program, and G5 is what showed it — Appendix A p136's
IXX comes out 66.7 against the printed 1201.527 without the item inertias. The
real cut is where §2 said it was (the mass-model and cg-case columns, the gear
and body-outline additions, the FAR 25 / concept route), just smaller.

## 3. The page set is already in the SSOT

`WorkflowStep` carries **`bas`** — *"the original McMaster program(s), or `None`
for a modern page."* The oracle GUI's page list is therefore **derived** from
`workflow.py`, not a second list that can drift (OG-2).

| | n | steps |
|---|---|---|
| `.bas` set | 15 | `configuration_layout` WINGGEOM · `weight_mass` WTESTIMA+WTONECG+WTENV · `structural_speeds` STRSPEED+MACHLIM · `flight_envelope` FLTLOADS+SELECT · `wing_loads` AIRLOADS+WINGINER+NETLOADS · `fuselage_loads` NETLOADS · `tail_loads` TAILDIST+BALLOADS · `aileron_loads` AILERON · `flap_loads` FLAPLOAD · `tab_loads` TABLOADS · `engine_mount` ENGLOADS · `one_engine_out` ONENGOUT · `landing_loads` LGFACTOR+LANDLOAD · **+ `tail_span_loads` and `balanced_cases`, see the defect below** |
| `.bas` unset | 7 | `dashboard`, `project_editor`, `aero_coefficients`, `loads_plots`, `aircraft_comparison`, `results_review`, `export_report` |

**Defect found writing this note (OG-3).** `tail_span_loads` and
`balanced_cases` have `bas` set to an **em-dash `"—"`, not `None`**. Both are
modern sloads capability (plans 09 and 11). `"—"` is truthy, so the natural
filter `[s for s in STEPS if s.bas]` silently pulls two sloads-only pages into
the "original programs" set. The true oracle page count is **13**. This is a
latent wrong-answer in the nav SSOT and is worth fixing whether or not this GUI
is built — it is filed and fixed under OG-3 as a tier-S change, ahead of and
independent of the rest of this note (rule 4: the fix sweeps the field, and the
guard in OG-2 is what stops it recurring). **Fixed 2026-08-19** — see OG-A in §7.

## 4. Decisions

| # | Decision |
|---|---|
| **OG-1** | The oracle GUI is a **front-end only**. It imports `sloads` and the shared app shell; it contains no load calculation, no unit conversion and no result derivation of its own. `sloads/` gains nothing and branches on nothing. **One analysis model is the acceptance criterion, not an aspiration** — gate G1. |
| **OG-2** | Its page set is **derived at runtime** from `sloads.workflow.STEPS`. A hand-maintained page list in the oracle GUI is prohibited; a guard test asserts the derived set equals the GUI's rendered set. **Amended 2026-08-19 (owner, in session), building OG-C:** the rule was `bas is not None`, which is not closed — `aero_coeffs` is required by `structural_speeds` and `flight_envelope` but produced by `aero_coefficients`, whose `bas` is `None`, leaving 22 fields unenterable and **G5 unsatisfiable**. The rule is now *runs a `.BAS` program, **or** produces a slice such a step requires* — still fully derived, which is the part that mattered. Owner: `workflow.oracle_steps()`. The oracle set is **14** pages, not 13. |
| **OG-3** | `tail_span_loads.bas` and `balanced_cases.bas` become `None` (they are `"—"` today). Tier S, shipped ahead of the rest. |
| **OG-4** | **Prerequisite.** The app-layer shell shared by both GUIs — `components.py`, `limit_csv.py`, and `Home.py`'s project open/save/units/dirty-guard helpers (`_has_unsaved_changes`, `_confirm_discard`, `_load_with_guard`) — is extracted to a **single owner** before the second GUI exists. Neither GUI may hold a private copy. This is the one structural item; skipping it *is* the dual path, relocated from the calc to the shell (rule 3). |
| **OG-5** | A **field-origin registry** classifies every input field as `original` (an input of a named `.BAS` program) or `sloads` (added capability), with a **drift-guard test** so a new field cannot be added without declaring which world it belongs to. Code-owned, not a prose list (rule 3). Scope: the fields reachable from the 13 oracle pages. Source of truth for the classification: UG §3–§22 per-module input lists + the Appendix A echo prints. **Superseded in shape by OG-14:** origin is one column of the single registry, not a registry of its own. |
| **OG-6** | Output is **CSV and text only**, through the **existing owners** — `sloads.io.load_cases_csv` (with `report.csv_comment_block`) and `sloads.report.render.module_text_report`. No new renderer, no per-page bespoke CSV. Plots, LaTeX/PDF, sbeam decks, CONM2/LRA and the workbook are **out of scope for this GUI** and remain fully available in `app/`. **Amended 2026-08-20 (owner), building OG-E: a third owner, `app_shell.limit_csv`.** Two owners give a page its load cases and nothing else — and the load cases are not what AIRLOADS, NETLOADS and TAILDIST *print*. Their printed output, which is what Appendix A **is**, is the spanwise/chordwise station table; it is in no `ModuleResult`, being built from `wing_load_rows`/`body_load_rows`/`build_tail_chordwise` and rendered by `app_shell/limit_csv.py`. That module is neither a new renderer nor a bespoke CSV — it is the shared shell owner **OG-B extracted for exactly this channel**, so the amendment adds no path, it names one that already existed. This was written before OG-B, not as a deliberate exclusion. Those tables are LIMIT (the `CONVENTIONS.md` §3 analysis-page carve-out) and state it in-band and in a `*_LIMIT.csv` filename, which §5 already anticipated. An oracle GUI that cannot show the oracle's own printout is not one. |
| **OG-7** | Fields the original entered **directly** that sloads now **derives** (`flight_loads.mac`/`wing_area_sqft`/`xw`/`zw`, `weight.estimation.max_continuous_hp`, the `geometry.parametric` consolidation) are offered for direct entry in the oracle GUI under the **existing** rule GR-GEOM-3 — *planform primary, analysis scalars derived, an entered scalar wins and is marked*. No new mechanism. |
| **OG-8** | The gear-geometry duplication (`geometry.landing_gear.*` vs `landing.main_gear`/`nose_gear`/`tread_in`) gets **one owner** before it is put on an oracle page. This is one of the five duplicate-owner instances the 2026-08-16 GUI review already found; it is closed by that review's field-ownership registry, not by a patch here. |
| **OG-9** | `tests/test_ultimate_contract.py` and `tests/test_page_links.py` are **parametrized over both GUI directories** in the same change that creates the second one. Both hardcode `app/views/` today, so a second GUI is invisible to them and could ship an unmarked LIMIT CSV with CI green (rule 4). **Amended 2026-08-20 (owner), building OG-E: parametrizing the ultimate-contract scan over `oracle_app/` would be worse than not doing it.** The scan matches a literal `file_name="….csv"`; a derived GUI has none, so the parametrized case would pass on an empty set and *report* the second GUI as covered. The diagnosis was right and the remedy does not transfer: OG-E's G7 checks the payload bytes instead, and holds the package to one download call site so the check is complete. What OG-F still owes is `test_page_links.py` (a link scan, which does transfer) and the `app/` half of the contract scan. |
| **OG-10** | The "only `Home.py` calls `st.set_page_config`" rule becomes **"exactly one call per GUI entry point"**, stated in `PROJECT_GUIDE.md` and guarded. **✅ shipped 2026-08-20**, and guarded in three parts rather than one: exactly one call per entry point, exactly one entry point per GUI, and **none in the shell** — which is the case the old rule could not even express, since the shell is imported by both GUIs and a `set_page_config` there would be the first Streamlit call of whichever one ran. |
| **OG-11** | The oracle GUI is launched by its **own console script** in `[project.scripts]` (today: only `sloads = "cli:main"`), plus a documented `streamlit run` path. It is not a flag on the existing app. |
| **OG-12** | `one_engine_out` **is** an oracle page (ONENGOUT is an original program). It is inert on single-engine projects, which is the correct behaviour, not a gap. |
| **OG-13** | **No schema hop and no new stored field.** The oracle GUI writes the same `project.json` as `app/`; fields it does not expose keep their defaults. A project is fully portable between the two GUIs in both directions. |
| **OG-14** | **One registry, not two** *(added at agreement, 2026-08-19)*. OG-5's field-**origin** registry and the 2026-08-16 GUI review's field-**ownership** registry (GR-INPUT-2) are the same table under two names: same key (the input field path), different value columns. They are built **once**, as a single code-owned registry with one drift guard: `field path │ owning slice │ editing page │ origin`. OG-8 already conceded the overlap in one direction — the gear duplication "is closed by that review's field-ownership registry, not by a patch here" — and building the ownership half separately would leave that registry to be re-derived for OG-5. Consequences: step **OG-C** builds all four columns, not two; gates **G4** (origin total) and the review's duplicate-owner guard are two assertions over one table; and the registry becomes the mechanism that makes the GUI review's nine unswept pages a test report rather than another hand sweep, which is why it is scheduled before the review resumes. |

## 5. What the oracle GUI inherits and must not re-state

- **LIMIT→ULTIMATE**: every load it renders or downloads is ULTIMATE, produced by
  the same render/export boundary (`CONVENTIONS.md`; `PROGRAM_SPEC.md` "Limit vs.
  ultimate"). It applies no factor of its own. Any LIMIT artifact carries the
  basis in-band and the `*_LIMIT.csv` filename — enforced by OG-9's parametrized
  guard.
- **Units**: `units.deliverable_units(system, channel)`, resolved once, in the
  shared shell. The oracle GUI adds no unit control of its own beyond the
  shared one.
- **Safety factors**: `sloads/safety_factors.py` remains the authority; an
  unclassifiable case is flagged, never defaulted, in both GUIs identically.

## 6. Acceptance gates

| # | Gate |
|---|---|
| **G1** | *No dual path.* A source scan asserts the oracle GUI package imports its numbers from `sloads` (and the shared shell) only — no arithmetic on load quantities, no local unit conversion, no private CSV writer. **✅ shipped 2026-08-20**, `tests/test_oracle_gui.py`: an import allowlist (`sloads`, `app_shell`, `streamlit`, `pandas`, and the stdlib introspection the renderer is built from — no numerical library, because there is nothing here to compute), no Imperial→SI factor literal, no CSV writer. |
| **G2** | *Page set is derived.* The oracle GUI's rendered page keys `==` `{s.key for s in STEPS if s.bas is not None}`; adding a `bas` to a step adds a page with no GUI edit. **✅ shipped 2026-08-20** — as amended by OG-2, the owner is `workflow.oracle_steps()`. The assertion that carries the weight is not *the list is right* but **there is no list**: no workflow step key appears as a string literal anywhere in `oracle_app/`, and the one `st.navigation` call is built from `oracle_steps()`. A correct hand-written page list stops being correct the day a step gains a `bas`. |
| **G3** | *No `"—"` sentinels.* Every `WorkflowStep.bas` is either `None` or a non-empty program name matching `[A-Z0-9+]+`. |
| **G4** | *Origin registry is total.* Every field reachable from an oracle page carries an `original`/`sloads` tag; an untagged field fails. |
| **G5** | *Oracle inputs suffice.* With **only** `origin=original` fields populated from `ga6_normal`, all oracle-page modules run and every Appendix A oracle test still passes at ±0.1 %. This is the gate that proves the reduced input set is real rather than asserted. **✅ shipped 2026-08-19**, `tests/test_oracle_inputs.py`. One amendment, forced by building it: the input set is `original` **∪ `supplied`** — the fields the oracle GUI *writes* without asking, because this model carries as data what the original carried by position (which surface a planform describes; which of LANDLOAD's three loadings a CG case is). Eleven fields, each earning the mark by being structurally required or by demonstrably moving a number. `origin` is left answering only its own question. |
| **G6** | *Round-trip.* A project saved by the oracle GUI loads in `app/` unchanged, and vice versa (byte-identical after `io` normalisation). **✅ shipped 2026-08-20**, `tests/test_oracle_gui.py`: the reduced form of every shipped example re-serialises byte-identically, and the reduced `ga6_normal` is handed to `app/Home.py` and three `app/views/` pages under `AppTest` without an exception. |
| **G7** | *Output contract.* Every CSV the oracle GUI offers passes the parametrized ultimate-contract scan; every text report carries the same ULT marker and SF statement as `cli.py`'s. **✅ shipped 2026-08-20**, `tests/test_oracle_gui.py` — **not** by the parametrized scan, which cannot see this GUI. `tests/test_ultimate_contract.py` matches a literal `file_name="….csv"` in `app/views/*.py`; the oracle GUI's filenames are computed from the step key, so OG-9's parametrization would find no literal and **pass on an empty set** — a green gate over an unchecked front-end, which is the exact failure OG-9 exists to prevent. G7 therefore reads the **payloads**: `results.page_artifacts()` returns every file a page offers, bytes included, and the gate asserts ULTIMATE (the `csv_comment_block` stamp + an `SF` column) or LIMIT (in-band **and** a `*_LIMIT.csv` name) on each. Completeness is structural rather than assumed: a second guard asserts the package holds **exactly one `st.download_button` call site**, fed from that same function, so no artifact can exist that the gate never saw. The text half is byte equality with `cli.py`'s own report, title line aside — the same call, not a resembling one. |
| **G8** | *Shell is single-owned.* No symbol in the shared shell is defined twice across the two GUI packages. |

## 7. Steps

| # | Step | Tier |
|---|---|---|
| **OG-A** | Fix the two `bas = "—"` rows to `None`; add gate G3. Independent of everything else. **✅ shipped 2026-08-19** — both rows are `None`, guard `tests/test_workflow.py::test_bas_is_a_program_name_or_none` asserts the shape, oracle page count is the true **13**. | S |
| **OG-B** | Extract the shared app shell to one owner; both existing front-ends switch to it; gate G8. **Prerequisite for OG-D.** **✅ shipped 2026-08-19** — `app_shell/` (`components`, `project_state`, `sidebar`, `limit_csv`), an installed package rather than a directory on Streamlit's implicit entrypoint path, so a second entry point can import it without inheriting the first one's `sys.path`. `app/Home.py` is now only its own nav + one `set_page_config`. Gate G8 is `tests/test_app_shell.py`, with the GUI set **derived** (a directory holding a `set_page_config` entry point) so the oracle GUI activates it on arrival. | L (moves an architectural boundary; `PROJECT_GUIDE.md` §4 tree changes) |
| **OG-C** | The **single field registry** + drift guard (OG-5 as reshaped by **OG-14**). **✅ shipped 2026-08-19** — `sloads/field_registry.py`, **six** columns not four (`quantity` and owner-or-`derived_from` were added at build time: the review's duplicate class is one quantity in two fields, which four columns cannot express). 323 fields, 207 `ORIGINAL` / 116 `SLOADS`, every row cited; 18 duplicated quantities recorded, the review's five plus a sixth. Gates G4 and the duplicate-owner class close in `tests/test_field_registry.py`. `docs/generate_data_dict.py`'s private `PAGE_OVERRIDES` is deleted in favour of the registry. **G5 followed 2026-08-19** and corrected **twelve** of these rows — see below. | M |
| **OG-C2** | **Gate G5** — run the registry rather than trust it. **✅ shipped 2026-08-19**, `tests/test_oracle_inputs.py`: the reduced project's numbers, module-by-module, against the full one on five of the six shipped examples, plus four Appendix A figures restated directly on it. Twelve rows moved `SLOADS` → `ORIGINAL` on the gate's evidence (per-item inertia, the WTONECG loading-hierarchy tag, the wing edge polylines and strip count, the three CG-case corners, WTESTIMA's engine-weight code, ENGLOADS' engine type); the `supplied` column was added for the eleven the front-end writes. Final shape: **323 fields, 219 `ORIGINAL` (68 %) + 11 supplied, 93 omitted entirely.** | M |
| **OG-D** | The oracle GUI: entry point (OG-11), derived nav (OG-2), generic form renderer over `origin=original`; gates G1, G2, G6. **✅ shipped 2026-08-20** — `oracle_app/` (`Oracle.py` + `form.py`) and the `sloads-oracle` launcher (`oracle.py`). **Fourteen pages, no fourteen page files**: the nav is `st.Page(callable)` bound to a step key, so G2's "adding a `bas` adds a page with no GUI edit" holds literally — a `views/<key>.py` per page would have been a hand-maintained page list wearing a different hat. 230 fields across 35 record groups, every widget's shape from `field_registry.field_type` (added here), its unit from `units.field_unit`, and its help from the registry's `basis`, so each field names the `.BAS` program that asked for it. Gates in `tests/test_oracle_gui.py`: G1 (import allowlist, no unit-factor literal, no private CSV writer), G2 (**no step key appears as a string literal anywhere in the GUI**), G6 (the reduced project reloads byte-identically and opens in `app/`), plus every page rendered under `AppTest` on both a loaded and an empty project. | M |
| **OG-E** | CSV + text output through the existing owners (OG-6); gate G7. **✅ shipped 2026-08-20** — `oracle_app/results.py`, one results renderer for all fourteen pages, plus `labels.py` (the spelling table both renderers share). A page's programs are `workflow.step_modules()`: its own `module` plus the contributors folded into it, so Weight & Mass Properties runs all three of WTESTIMA+WTONECG+WTENV because `workflow.py` says so. **Re-tiered S → M and re-scoped**, for two reasons found on arrival. First, the step as written was downloads only, and `render_step` computed nothing at all — a download button under a page with no result is not a page, so running the programs and showing the tables came with it. Second, G7 could not be met by OG-F's parametrization (see the gate). `FOLDED_MODULES` became a `module → owning step` mapping in the same change: a page headed "WTESTIMA+WTONECG+WTENV" must show all three, and a flat tuple cannot say which page WTESTIMA belongs to. Membership reads (`in`, `set()`) are unaffected. | M |
| **OG-F** | Parametrize the two `app/views/`-hardcoded guards over both GUI dirs (OG-9); `set_page_config` rule restated (OG-10). **Reduced by OG-E**: the ultimate-contract half is closed for the oracle GUI by G7's payload gate, and OG-9's parametrization of *that* scan is withdrawn as unsound (see OG-9). What remains is `test_page_links.py` over both dirs and OG-10. **✅ shipped 2026-08-20 — and OG-9 is withdrawn in full.** Its second half does not transfer either, for a matching reason: `test_page_links.py` asserts `app/views/<key>.py` exists per step (false by construction for a GUI with no page files) and scans for `workflow_page_link` calls the oracle GUI does not make (a vacuous pass). What replaced it is structural: `workflow_page_link` no longer builds a path at all. It resolves a step key to the running GUI's own `st.Page` through the new `app_shell/nav.py`, both entry points register the page set they hand `st.navigation`, and a link therefore cannot name a page its GUI does not carry. That also removes the last `app/`-shaped fact from the shared shell — the `views/<key>.py` assumption OG-B left behind. **The sweep's real find was a defect** (see the risk note below); OG-10 is restated in `PROJECT_GUIDE.md` §5 and `CLAUDE.md` and guarded both ways (exactly one `set_page_config` per entry point; none in a view, none in the shell). | M |

Rough size for OG-D + OG-E: **~600–800 LOC of new front-end**, against the 8,337
LOC of `app/views/` it does not touch. OG-B and OG-C are the real cost.

## 8. Risks and what is explicitly accepted

- **A guard that reaches only one GUI is worse than no guard, and OG-F found
  what that costs** *(added 2026-08-20, closing OG-F)*. Both halves of OG-9 were
  written on a correct diagnosis — an `app/views/`-hardcoded guard cannot see a
  second front-end — and neither remedy survived contact, because the second
  front-end has no views to point at. What the sweep was actually owed was the
  guard whose *mechanism* transfers: `test_dirty_flag.py`'s "a render pass must
  not mutate the project". Parametrized over the oracle GUI it failed
  immediately, on **9 of its 14 pages with the fully-populated oracle fixture**
  and 12 of 14 with a sparser one, for two reasons the second GUI's shape made
  new: the generic renderer attached a record to the project merely to give its
  widgets somewhere to write, and it rewrote every field it rendered, turning a
  JSON `45` into `45.0`. In SI it was worse than cosmetic — a station converted
  out to millimetres and back came home as `115.99999999999999`, so an SI user's
  geometry walked on every rerun. All three are fixed in `oracle_app/form.py`
  (a created record is committed only if the pass leaves something in it; a
  write that changes nothing does not happen; an untouched converted field
  returns the stored value rather than a reconstruction), and the contract is
  now asserted for both GUIs. The lesson is the one OG-E started: **before
  parametrizing a guard over a second target, check that it can fail there.**
- **Two GUIs to maintain.** Accepted deliberately: the oracle GUI's scope is
  frozen by definition — it tracks the original suite, which cannot grow. Its
  maintenance burden is bounded by OG-2/OG-5 (both derived) and OG-4 (shared
  shell), so new sloads capability lands in `app/` and is invisible here by
  construction.
- **The GUI freeze — lifted for this note, 2026-08-19 (owner).**
  `50_reviews/2026-08-16_scope_and_deficiency_review.md` §Streamlit UI froze GUI
  investment; the freeze was carried past the 0.6.0 cut and held pending the GUI
  review (#29). The decision this note asked for is **taken: the oracle GUI is
  the next development phase, and the freeze does not block it.** Two things are
  worth recording about *why the decision changes less than it appears to*.
  First, the freeze was never the binding constraint on the near work — OG-A and
  OG-B are hygiene and structure rather than GUI investment, OG-C is a registry
  with no GUI code, and G5 is a test; the freeze binds only at OG-D/OG-E. What
  actually blocked step one was this note's own `PROPOSED` status, OG-B being
  tier L and `CLAUDE.md` rule 1 gating tier-L code on an AGREED note. Second,
  the decision is still taken **with** #29's findings rather than around them:
  OG-14 folds the review's own registry into OG-C, and OG-8 already routes the
  gear duplication through it. What the lift defers is the review's placement
  batch for `app/` — accepted, with the two exceptions that outrank it under
  rule 6 because they are defects in shipped behaviour, not placement: the gear
  reference point having no widget (so the export omits the node), and
  `speeds.wing_area_sqft` being an input nothing reads.
- **OG-C is a judgement pass, not a mechanical one.** Roughly 30 of the ~295
  paths are genuinely borderline (fields the original entered under a different
  name, fields sloads split or consolidated). These are ruled on by the owner
  and recorded in the registry, not decided by the implementer. **Revised by G5
  (2026-08-19):** twelve of the borderline rows turned out not to need a
  judgement at all — the printed Appendix A figures decide them, and decided
  them against the table as first written. The lesson for the rest of this
  phase is the ordering: a classification that changes a delivered number is
  settled by running it, and only what survives that is a judgement call.
- **What this note does not do.** It does not reduce the module count — all 22
  registered modules *are* original programs. sloads added capability mostly as
  extra inputs and extra outputs on the same modules. The oracle GUI therefore
  still reaches nearly every module; it simply asks for less and offers less.
