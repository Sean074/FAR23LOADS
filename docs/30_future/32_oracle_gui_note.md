# Oracle GUI — a second front-end over the one analysis model

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: PROPOSED 2026-08-19 — no code.**

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
guard in OG-2 is what stops it recurring).

## 4. Decisions

| # | Decision |
|---|---|
| **OG-1** | The oracle GUI is a **front-end only**. It imports `sloads` and the shared app shell; it contains no load calculation, no unit conversion and no result derivation of its own. `sloads/` gains nothing and branches on nothing. **One analysis model is the acceptance criterion, not an aspiration** — gate G1. |
| **OG-2** | Its page set is **derived at runtime** from `sloads.workflow.STEPS` by `bas is not None`. A hand-maintained page list in the oracle GUI is prohibited; a guard test asserts the derived set equals the GUI's rendered set. |
| **OG-3** | `tail_span_loads.bas` and `balanced_cases.bas` become `None` (they are `"—"` today). Tier S, shipped ahead of the rest. |
| **OG-4** | **Prerequisite.** The app-layer shell shared by both GUIs — `components.py`, `limit_csv.py`, and `Home.py`'s project open/save/units/dirty-guard helpers (`_has_unsaved_changes`, `_confirm_discard`, `_load_with_guard`) — is extracted to a **single owner** before the second GUI exists. Neither GUI may hold a private copy. This is the one structural item; skipping it *is* the dual path, relocated from the calc to the shell (rule 3). |
| **OG-5** | A **field-origin registry** classifies every input field as `original` (an input of a named `.BAS` program) or `sloads` (added capability), with a **drift-guard test** so a new field cannot be added without declaring which world it belongs to. Code-owned, not a prose list (rule 3). Scope: the fields reachable from the 13 oracle pages. Source of truth for the classification: UG §3–§22 per-module input lists + the Appendix A echo prints. |
| **OG-6** | Output is **CSV and text only**, through the **existing owners** — `sloads.io.load_cases_csv` (with `report.csv_comment_block`) and `sloads.report.render.module_text_report`. No new renderer, no per-page bespoke CSV. Plots, LaTeX/PDF, sbeam decks, CONM2/LRA and the workbook are **out of scope for this GUI** and remain fully available in `app/`. |
| **OG-7** | Fields the original entered **directly** that sloads now **derives** (`flight_loads.mac`/`wing_area_sqft`/`xw`/`zw`, `weight.estimation.max_continuous_hp`, the `geometry.parametric` consolidation) are offered for direct entry in the oracle GUI under the **existing** rule GR-GEOM-3 — *planform primary, analysis scalars derived, an entered scalar wins and is marked*. No new mechanism. |
| **OG-8** | The gear-geometry duplication (`geometry.landing_gear.*` vs `landing.main_gear`/`nose_gear`/`tread_in`) gets **one owner** before it is put on an oracle page. This is one of the five duplicate-owner instances the 2026-08-16 GUI review already found; it is closed by that review's field-ownership registry, not by a patch here. |
| **OG-9** | `tests/test_ultimate_contract.py` and `tests/test_page_links.py` are **parametrized over both GUI directories** in the same change that creates the second one. Both hardcode `app/views/` today, so a second GUI is invisible to them and could ship an unmarked LIMIT CSV with CI green (rule 4). |
| **OG-10** | The "only `Home.py` calls `st.set_page_config`" rule becomes **"exactly one call per GUI entry point"**, stated in `PROJECT_GUIDE.md` and guarded. |
| **OG-11** | The oracle GUI is launched by its **own console script** in `[project.scripts]` (today: only `sloads = "cli:main"`), plus a documented `streamlit run` path. It is not a flag on the existing app. |
| **OG-12** | `one_engine_out` **is** an oracle page (ONENGOUT is an original program). It is inert on single-engine projects, which is the correct behaviour, not a gap. |
| **OG-13** | **No schema hop and no new stored field.** The oracle GUI writes the same `project.json` as `app/`; fields it does not expose keep their defaults. A project is fully portable between the two GUIs in both directions. |

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
| **G1** | *No dual path.* A source scan asserts the oracle GUI package imports its numbers from `sloads` (and the shared shell) only — no arithmetic on load quantities, no local unit conversion, no private CSV writer. |
| **G2** | *Page set is derived.* The oracle GUI's rendered page keys `==` `{s.key for s in STEPS if s.bas is not None}`; adding a `bas` to a step adds a page with no GUI edit. |
| **G3** | *No `"—"` sentinels.* Every `WorkflowStep.bas` is either `None` or a non-empty program name matching `[A-Z0-9+]+`. |
| **G4** | *Origin registry is total.* Every field reachable from an oracle page carries an `original`/`sloads` tag; an untagged field fails. |
| **G5** | *Oracle inputs suffice.* With **only** `origin=original` fields populated from `ga6_normal`, all oracle-page modules run and every Appendix A oracle test still passes at ±0.1 %. This is the gate that proves the reduced input set is real rather than asserted. |
| **G6** | *Round-trip.* A project saved by the oracle GUI loads in `app/` unchanged, and vice versa (byte-identical after `io` normalisation). |
| **G7** | *Output contract.* Every CSV the oracle GUI offers passes the parametrized ultimate-contract scan; every text report carries the same ULT marker and SF statement as `cli.py`'s. |
| **G8** | *Shell is single-owned.* No symbol in the shared shell is defined twice across the two GUI packages. |

## 7. Steps

| # | Step | Tier |
|---|---|---|
| **OG-A** | Fix the two `bas = "—"` rows to `None`; add gate G3. Independent of everything else. | S |
| **OG-B** | Extract the shared app shell to one owner; both existing front-ends switch to it; gate G8. **Prerequisite for OG-D.** | L (moves an architectural boundary; `PROJECT_GUIDE.md` §4 tree changes) |
| **OG-C** | Field-origin registry + drift guard (OG-5); gates G4, G5. The classification pass is the bulk of the intellectual work and needs the owner's ruling on the borderline rows. | M |
| **OG-D** | The oracle GUI: entry point (OG-11), derived nav (OG-2), generic form renderer over `origin=original`; gates G1, G2, G6. | M |
| **OG-E** | CSV + text output through the existing owners (OG-6); gate G7. | S |
| **OG-F** | Parametrize the two `app/views/`-hardcoded guards over both GUI dirs (OG-9); `set_page_config` rule restated (OG-10). | M |

Rough size for OG-D + OG-E: **~600–800 LOC of new front-end**, against the 8,337
LOC of `app/views/` it does not touch. OG-B and OG-C are the real cost.

## 8. Risks and what is explicitly accepted

- **Two GUIs to maintain.** Accepted deliberately: the oracle GUI's scope is
  frozen by definition — it tracks the original suite, which cannot grow. Its
  maintenance burden is bounded by OG-2/OG-5 (both derived) and OG-4 (shared
  shell), so new sloads capability lands in `app/` and is invisible here by
  construction.
- **The GUI freeze.** `50_reviews/2026-08-16_scope_and_deficiency_review.md`
  §Streamlit UI froze GUI investment; the freeze was carried past the 0.6.0 cut
  and holds pending the GUI review (#29). This note is new GUI construction and
  therefore **requires a recorded decision to proceed**, taken with #29's
  findings rather than around them. OG-A and OG-B are hygiene and structure, not
  GUI investment, and are not blocked by the freeze.
- **OG-C is a judgement pass, not a mechanical one.** Roughly 30 of the ~295
  paths are genuinely borderline (fields the original entered under a different
  name, fields sloads split or consolidated). These are ruled on by the owner
  and recorded in the registry, not decided by the implementer.
- **What this note does not do.** It does not reduce the module count — all 22
  registered modules *are* original programs. sloads added capability mostly as
  extra inputs and extra outputs on the same modules. The oracle GUI therefore
  still reaches nearly every module; it simply asks for less and offers less.
