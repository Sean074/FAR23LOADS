# sloads — GUI Design & Structure

The authoritative description of how the Streamlit GUI is designed and the
standards every page — especially the airplane-**definition** pages — must meet.
Read this before adding or changing a view.

**See also:** [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) — architecture rationale and
the shared pure-calc/thin-shell split; [`00_program_overview.md`](00_program_overview.md)
— coding standards, the error-handling contract and the units convention;
[`../40_history/05_phase_d_gui_workflow_plan.md`](../40_history/05_phase_d_gui_workflow_plan.md) —
the Phase-D narrative (assessment, the six-section target, locked decisions
D-1…D-7, page conventions §5) this doc references rather than repeats;
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) — **Phase E**, the open
GUI usability & concept-awareness work whose target standards are set out below.

---

## 1. Purpose & scope

The GUI lets an engineer **build an airplane, review that the inputs are right,
run the FAR 23 loads workflow, and export** the results (per-module CSVs and the
sbeam `FORCE`/`MOMENT` bulk-data cards). It is a concept-aware **superset** of the
FAR 23 replication: it can describe airplanes that exceed the FAR 23 applicability
limits (higher MTOW, more occupants) while making the user aware they are outside
the certificated band — and it reduces exactly to the oracle-locked FAR 23
behaviour on GA inputs (see §9).

Every page is a thin I/O shell over the shared pure-calc package: the GUI does no
load math of its own. Calc always runs in the Imperial units of the original
programs; SI and unit presentation are applied only at the render boundary (§7).

---

## 2. Architecture at a glance

The system is a **shared pure-calc package + interchangeable thin front-ends**
(GUI, CLI, tests). The GUI carries **one reloadable `Project`** in
`st.session_state["project"]`; every page reads the slices it needs off that
`Project` and writes its own slice back. Navigation is generated from
`sloads/workflow.py`, the single source of truth for *what the suite does and in
what order*.

```
project.json ──io.load_project──▶ Project ──▶ view widgets ──▶ Project
                                     │                            │
                                     └────── registry / report ◀──┘
                                              (results, CSV, sbeam)
```

`app/Home.py` is the entry point; `app/views/<key>.py` is one page each;
`sloads/models.py` holds `Project` and its per-domain slices; `sloads/io.py`
is the only dataclass⇔JSON mapper; `sloads/units.py` owns unit conversion.

---

## 3. Navigation model

The sidebar is built by `st.navigation` in `app/Home.py` from
`sloads/workflow.py` — **not** from a `pages/` directory — so page order and
titles come from workflow metadata, not filename numbers. Since Step G2 the
sections follow the FAR 23 analysis flow — an un-numbered **Start** app-shell group
above the six numbered analysis-flow phases:

    Start ─▶ 1 · Develop V-n diagram ─▶ 2 · Flight loads ─▶ 3 · Other loads ─▶
    4 · Landing loads ─▶ 5 · Load-case plotting ─▶ 6 · Export

Each `WorkflowStep` names its `key` (= the view file stem), `title`, `phase`, the
calc `module` behind it, and the project slices it `requires`/`produces` — the
seed of a dependency DAG that also drives the Dashboard completeness panel.
A step whose *own form* enters a required slice declares it in `edits` (#45,
CR-D-3, declared minimally — only where a `requires` has no producing step):
`workflow.missing_upstream` / `missing_self_entered` split the missing slices by
remedy, so a self-sufficient page (Weight & Mass Properties, Engine Mount Loads)
is never reported "blocked" on a fresh project — its guidance points at its own
form. A DAG-completeness guard (`tests/test_workflow.py`) holds every `requires`
to *some step's `produces` or some step's `edits`*, with a field-registry rot
companion on the `edits` declarations. A fourth list, `reads` (#69), names the
slices a step's numbers depend on that none of the three cover — read here,
entered on a **later** page — declared so the page can say so; see *A page says
which later page its numbers depend on* below. A page
is exactly `app/views/<step.key>.py`. Since Step G3 the **Develop V-n diagram**
section — the definition pages this doc is chiefly about — is five consolidated
pages, several using `st.tabs` to gather formerly-separate pages: **Geometry**;
**Weight & Mass Properties** (tabs: Estimate · Weight, CG & Inertia · Payload
Cases · Weight / CG Envelope); **Structural Speeds** (tabs: Design Speeds ·
Speed–Altitude Envelope); **Aerodynamic Data**; and **Flight Envelope (V-n)**
(tabs: V-n diagram · Critical Loads (SELECT) · Trim & Stability — the last, Step G5,
plots the balancing tail load swept across the CG range and the tail-volume static
margin).

The analysis-flow phases and their per-page mapping are in
[`../30_future/03_gui_rework_plan.md §4`](../30_future/03_gui_rework_plan.md); the
superseded Phase-D six-section grouping is in
[`../40_history/05_phase_d_gui_workflow_plan.md §2`](../40_history/05_phase_d_gui_workflow_plan.md).

---

## 4. Global sidebar (`Home.py`)

`Home.py` owns the two controls that appear on every page, built once *around*
`pg.run()` (`with render_shell_sidebar(project): pg.run()` — both GUIs):

- **Unit-system toggle** — an Imperial/SI radio writing
  `st.session_state["unit_system"]` (a `UnitSystem` enum). It changes how inputs
  and results are *displayed* **and it is the selection that every exported
  deliverable is rendered in** (report, load-case CSV, span CSVs, sbeam BDF —
  `00_program_overview.md`, *Deliverable units follow the user's selection*); the
  toggle persists into the project's unit-system field so a headless re-render
  reproduces it. Calc and the stored `project.json` values stay Imperial (§7).
- **Project-file widget** — Open a saved project (local `projects/`), New-from-
  example (`examples/*.project.json`), browser Upload, plus Save-to-disk and
  Download. An unsaved-changes guard (`_has_unsaved_changes` vs. a
  `_saved_project_snapshot`, and the `_confirm_discard` dialog) protects an edited
  session from being clobbered by a load. Every load path fires **once per user
  action**: the buttons are edge-triggered by construction, and Upload latches on
  the upload's identity (`st.file_uploader` returns the same file on every rerun
  while it sits in the widget — acting on presence alone re-adopts forever;
  #34, guard in `tests/test_app_shell.py`). Cancelling the discard dialog
  therefore genuinely cancels. Download writes `<name>.project.json` — the same
  suffix Save uses — so a downloaded file dropped into `projects/` is listed by
  Open.
- **The project is named here, and Save never overwrites unasked** (#65,
  review 2026-08-22 PB-6). `project.name` is document metadata, not an oracle
  input, so no oracle page rendered it and a project built there saved as
  `project.project.json` over the last, every time. The **Project name** widget
  is the sidebar's — one widget, both GUIs; the `app/` dashboard's copy is gone
  (two widgets for one field write their retained state over each other). One
  sanitiser, `io.project_filename(name)` (`[^A-Za-z0-9._-]` → `_`, collapsed,
  trimmed, capped at `io.PROJECT_STEM_MAX`), names both the saved and the
  downloaded file. `project_state` remembers the `projects/` file a project was
  opened from or last saved to (`SAVED_PATH_KEY`): Save writes *that* file
  back unasked and confirms (`confirm_overwrite`) before replacing any other
  existing file. Guards in `tests/test_app_shell.py`.
- **The project-file block renders after the page** (#64, review 2026-08-22
  PB-4). The rerun that carries a widget edit runs the sidebar before the page
  that persists it, so a block rendered above `pg.run()` served the *previous*
  interaction's project as the download and called it clean — in the oracle GUI
  (no Apply) every last edit, in `app/` the Apply's own merge. The units block
  stays first (`active_system()` reads it); the sidebar reserves the block's
  slot, wraps the page, and fills the slot on exit. A page therefore never calls
  `st.stop()` — Streamlit discards everything emitted after it, the slot
  included — but `app_shell.components.stop_page()`, which the sidebar catches
  (standalone it *is* `st.stop()`). Guards in `tests/test_app_shell.py`: one
  edit, then payload, caption and expander title read in the same run on the
  real oracle entry point; a stopping page keeps Save/Download; no view calls
  `st.stop()`.

---

## 5. Shared `Project` & data flow

`Project` holds one slice per domain (`configuration`, `geometry`, `weight`,
`speeds`, `aero`/`aero_coeffs`, `flight_loads`, `wing_mass`, `landing`, `engines`,
… and the result slices `mass`/`envelope`/`loads`). Two rules keep the pages
consistent:

- **Read, don't re-ask.** A page must not prompt for a quantity another slice
  already owns — it reads it. Where a page's field overlaps upstream data, it
  seeds its default from that data instead of showing a blank.
- **Merge, don't wholesale-replace** a slice shared with other pages/edits — only
  the sole owner of a slice may reconstruct it in full on Apply.
- **A widget belongs to the project it was seeded from** (#51, 2026-08-21).
  Streamlit widget state, once registered under a key, beats the `value=`
  argument on every later rerun — and GUI widget keys are stable across projects
  (a registry path in the oracle form, a hand-written name in `app/views/`). So a
  page **visited before** a load kept rendering its own retained state and, since
  these widgets persist what they return, wrote that state back over the project
  that had just been loaded: opening the oracle GUI on the seed project, visiting
  Weight & Mass Properties and loading `atr42_100` showed zeros and popped all 21
  weight items and 8 CG cases out of the loaded project — with no Apply step in
  that GUI, on the load's own rerun. Every widget seeded from the project
  therefore keys itself through `app_shell/widget_keys.py:widget_key`, which
  stamps the key with a *project generation* bumped exactly once per replacement
  (`project_state.adopt`, and the JSON editor's Apply — the only two places that
  replace it). A mutation, an Apply or a unit switch is not a replacement and
  keeps its widgets. **No key at all is the same defect** (#51's reopen,
  closed 2026-08-22): an unkeyed widget derives its Streamlit identity from its
  *arguments* — `value=` included — so its retained state survives a load
  whenever the loaded field repeats the seed, which `Project(name="")` makes
  the common case. Every input widget therefore carries a stamped `key=`;
  the only exemptions are the shell's own session-state widgets (the unit
  radio, the load-path pickers), named **per key** on an explicit allowlist
  with a companion test that fails when an entry stops naming a real widget.
  Guards: `tests/test_widget_freshness.py` — render → load → re-render leaves
  the session project equal to the loaded file, on every oracle page and every
  shipped example; a type-then-load reproduction that asserts the typed value
  does not survive; and an AST walk that fails on any GUI input widget without
  a stamped key.
- **A copy says it is a copy** (#36, CR-A-2). Where a quantity is held by more
  than one field, `sloads/field_registry.py` names the owner, and the renderer
  **reads that** rather than presenting every holder as an independent input.
  Which of two markings applies is decided by `FieldEntry.governs` — *does the
  calc honour this copy?* — because the answer changes what the page may safely
  do:
  - `governs=False`, **display-only**: the consumer resolves the owner, so the
    widget renders **disabled** at the value that actually governs, captioned
    with the owner's path. `speeds.wing_area_sqft` is the case that named the
    rule — STRSPEED integrates the wing planform and only falls back to this
    field when no wing surface exists, which no GUI-built project lacks, so a
    value typed here was silently ignored (18 % divergence measured on atr42).
  - `governs=True`, **override**: some module reads the field verbatim, so it
    stays **editable** and is captioned with the owner and the owner's current
    value; a disagreement draws a warning. It warns rather than corrects,
    because disagreeing is what an override is for. Disabling one of these would
    remove a capability and substituting the owner's value would change results.

  A display-only copy is never written back from a render — the page shows the
  governing value while the stored copy keeps whatever it held, so visiting a
  page still cannot dirty a project (OG-F). Guards:
  `tests/test_oracle_gui.py` renders every copy's page and fails on one that does
  not name its owner (and on a display-only one that is still editable);
  `tests/test_field_registry.py` fails if an owner row claims `governs`.

  **An owner that is not a field is still an owner** (#69, C210-41). Some
  quantities are owned by an expression rather than a row — engine count is
  `len(Project.engines)`, engine mass and CG are the weight database (D-25), the
  engine-mount limit load factor is the computed 23.337 limit — and the registry
  says so with `EXTERNAL + <where it lives>`. Those rows are marked like any
  other copy, naming the owner in words. Two differences, both forced by the
  owner being an expression: they are **never disabled** (there is no path to
  read a substitute value from, and one of them — the weight estimate's
  horsepower — is the *fallback* the calc uses when the owner is empty), and
  where `governs` alone would state the rule wrongly the row carries the true
  sentence in `resolves`. Every EXTERNAL row must state one or the other; a
  silent default is what let five of them ship as peer inputs.

  **The mark reaches composites too** (#89). `_copy_note` was called from
  `render_scalar` alone, so a non-owner tuple, curve or enum set rendered bare —
  latent until `engines[].engine_cg`, a three-member tuple copied from the weight
  database, became the first one. Composite marks are captions and never
  disable, so a *display-only* composite would need a mark the renderer cannot
  give; the registry may not hold one, and
  `tests/test_oracle_gui.py::test_no_non_owner_field_needs_a_mark_the_renderer_cannot_give`
  fails if it does. The per-page render guard counts marks per owner phrase
  rather than searching for it once, because two fields on the Engine Mount page
  name the same external owner and a substring test passed while the tuple
  beside the scalar rendered unmarked.
- **A page says which later page its numbers depend on** (#69, PB-15/PB-19).
  A step's numbers can read a slice that neither gates the run (`requires`) nor
  is entered on the page (`edits`): Flap Loads computes its FAR 23.457(b)
  slipstream case from an engine record entered two pages later, and WTESTIMA
  correlates against the engine list's combined power rather than the horsepower
  typed beside it. Run the page first and it shows a complete-looking answer;
  download it, fill the later page, and the numbers move — ~19 % of the
  governing flap load on the C210, because the slipstream is a whole delivered
  case that did not exist yet.

  `requires` is the wrong instrument: it *blocks*, and both calcs are correct
  with no engine at all — a glider has no slipstream case to omit. So the
  dependency is declared on the step (`WorkflowStep.reads`) and **stated**, not
  enforced: `app_shell.components.render_page_order_reads` names the slice and
  the page that enters it on every visit (it is provenance either way), and
  turns from a caption into a warning while that page is still empty. The loud
  channel stays `consistency_warnings`. Guards:
  `tests/test_workflow.py::test_every_page_order_dependency_is_declared` walks
  each step's modules by AST and fails on a slice read from a later page that
  the step has not declared, with the reverse test failing on a stale one.
  The durable fix for a copy that need not exist at all is to remove it —
  [note 33](../40_history/34_derived_scalar_consolidation_note.md) did that for
  ten of them, and this marking covers the remainder.
- **A derived slice has one writer, and no Apply to miss** (#62, 2026-08-23).
  `Project.mass` is WTONECG over `weight.items` and nothing else; storing it is a
  convenience for its readers (One Engine Out, Configuration's tip-back CG, the
  CG-case waterline) and the workflow ✅. The only thing that writes it is
  `sloads/derived.py:refresh_derived` — called by the `app/` Weight page on
  Apply and by the oracle form after every persist, and by gate G5's reduction
  after it drops the stored slice. Before this the oracle GUI wrote it nowhere:
  a fresh twin could never reach One Engine Out and Configuration fell back to
  a 25 %-MAC estimate while the page said nothing (review 2026-08-22 PB-1).
  Each refresher is idempotent by value, so a visit still dirties nothing.
- **The oracle GUI's project is what gate G5 tests** (#62, 2026-08-23). The
  registry reduction drops every field outside the input set, every *record*
  the GUI never creates (a turbine rotor row), and the stored result slices —
  then re-derives what the GUI would have written. Its second leg,
  `tests/test_oracle_journey.py`, types the GA-6 and the DHC-8 from a blank
  project through the pages' own widgets and requires the result to *be* the
  reduced key: document, every page's downloads byte-for-byte, save → reload a
  fixed point. What that made visible is on the page rather than in the gate:
  `weight.items[].component` and `wing_fraction` are rendered (the same
  which-beam question BODYLOAD asked by position), and the Fuselage Loads table
  states what it rests on — untagged items lumped on the fuselage by inference,
  a wing-mass tie that does not close, a tail surface with no item at all. The
  one divergence that is decided rather than discovered — the twins' turbine
  rotors, a sloads model the original ENGLOADS never had — is declared per
  example with its number (−16 % DHC-8 mount torque), not rendered.
- **A selector name is seeded, unique, and matched ignoring case; a coded
  field is a choice** (#63, 2026-08-23). What the original suite expressed
  by position this model carries as a name the calc keys on — the surface,
  the CG case, the coefficient set — and the oracle form used to seed each
  `""` and ask nothing more: two CG cases with one name collapsed to one
  entry and TAILDIST changed in 7 of 13 rows with every page reporting
  success (review 2026-08-22 PB-5). `sloads/selectors.py` owns the three
  rules: `keyed` builds the dictionaries `select.py` reads and refuses a
  duplicate; `duplicate_selectors` is the same check in the form's words, and
  `render_step` withholds a page's results while it speaks; `NAME_SEEDS` names
  a new row (`wing` first — everything downstream keys on it, PB-9 — then
  `CG1 … CGn`, `CRUISE` / `LANDING`), skipping names already taken and never
  counting as a touch. `by_name` matches through `models.same_name` (case and
  edge spaces forgiven), so `Wing` no longer blocks eight pages. The FAR 23
  category and the strut type are **codes**, not text (PB-8): `models.CATEGORIES`
  / `STRUT_TYPES` are the one table both GUIs offer (`field_registry.CODED_FIELDS`
  says which `str` fields carry a code), the owners upper-case at construction,
  and every consumer goes through `normalise_code`, which refuses an unknown
  code by name rather than reading it as Normal (`"Utility"` used to give 3.8).
- **A widget never deletes entered data, and a row it creates is the project's**
  (code review 2026-08-24). The oracle form's row counter sizes a list record
  against the project's own attached list, so it wrote to the project in both
  directions during a render pass: counting down popped entered rows (21 of 24
  weight items on one keystroke, no confirmation, no undo, blanks on the way back
  up, and the truncated project saved), and it did the same with no interaction at
  all whenever the model had grown underneath a retained count — the `02_parked.md`
  L-8d mutation case, which no generation bump covers. The rule now: **the model
  wins**, growth is the only thing a counter does, and a deletion is a separate
  named button stating which rows go. Counting up is the other half — the seeded
  row joins the project immediately (`commit_pending`'s blank-record rule, OG-F,
  governs records a pass *creates*, not rows appended to an attached list), so a
  blank row is real, saved, and reaches the calc: a zero-weight `FLIGHT` CG case
  is one every balance divides by. A page that creates rows says so in its caption
  — the grid rule (an empty cell is held out) and the counter rule (the row is
  yours the moment it appears) are different and are both stated — and the calc
  refuses the degenerate row **by name** at the point that divides
  (`flight_envelope.build_envelope`), with `validation.cg_case_without_weight`
  warning before anything runs.
- **A cross-field rule is asked, never enforced at construction** (#66,
  review 2026-08-22 PB-7). `Project.__post_init__` used to raise when
  `engine_layout` disagreed with `len(engines)` — two widgets on one page,
  set in either order — so the in-session project accepted the state, Save
  wrote it, and the loader refused the file. The rule is now
  `Project.engine_layout_problem()` with three readers: the loader warns
  (surfaced as a toast by `safe_load`, the file loads), the oracle form
  withholds the page's results (the same block as the selector check), and
  the one consumer of the layout (WINGGEOM's engine stations) refuses by
  name. `app/`'s Engine Mount derives the count from the layout, so it cannot
  disagree. Guard: `tests/test_engine_layout_consistency.py`.

The established **seed-chain** (each seeds the next when its target is unset):
Configuration & Layout → WINGGEOM wing surface → Weight DB component stations;
Weight Estimate → Weight DB items; Configuration & Layout `dihedral` / tail spans
→ Wing Loads / Tail Loads; existing wing surface → Configuration & Layout
parametric wing fields. (STRSPEED `MC`/`MD`/shoulder altitude were formerly seeded
into the Mach Limit page; as of Step E7 the **Speed–Altitude Envelope** page instead
*reads them through* read-only from `speeds` — not an editable seed — so they are
never entered twice.)

---

## 6. Page anatomy & conventions

The contract that makes pages copy-of-the-pattern (full list in
[`05_phase_d_gui_workflow_plan.md §5`](../40_history/05_phase_d_gui_workflow_plan.md)):

- **A page opens with `components.page_header(key)`** — M4-11. It renders
  the title, the optional caption and the FAR 23 applicability banner, and
  returns the `PageContext` (`project`, `system`, `U`) every view needs. `key` is
  the `workflow.BY_KEY` step key — the view's own filename stem — so **the title
  comes from `workflow.py`**, the single source of navigation truth, instead of
  being restated per page. Upstream gating is each page's own `gate()` call with
  page-specific wording; the `page()` context manager that once promised a
  generic automatic gate accrued zero callers and was removed (#45) — the
  hand-written gates are the pattern of record.
- **Inputs live in an `st.form`** with a single **Apply/Compute** submit — the
  page does not recompute on every keystroke. **Every form carries a unique
  string key** (`st.form("empennage_form")`) — tests select its Apply button
  through that key, never by position or label (M4-12a).
- **Apply merges** targeted fields onto the existing slice; a sole-owner page may
  fully reconstruct its own slice. **A form may never rebuild an input dataclass
  from the widgets it happens to render** (#36): every field the form does not
  render then reverts to its *default*, which deletes what the project stated
  without touching a widget or showing a message. Build the new value with
  `dataclasses.replace(existing, ...)`, or — where the result is post-processed
  field-by-field, as the engine page's `to_imperial` pass is — carry the
  unrendered fields across by name and say why. Measured 2026-08-21, four forms
  had drifted: the landing-gear form dropped the G-2 carrier, the G-12 trunnion
  node and the G-12a leg weight (so a GUI-built project exported a ground model
  with **no gear nodes at all**), the empennage form dropped the fin root
  waterline, the engine form dropped `mounted_on`, and the wing-aero form wiped
  the profile-drag and section-Cm polars. The guard is one-sided and page-generic
  — `tests/test_configuration_layout_view.py` presses every Apply on every page
  **without touching a widget** and fails if anything the project stated has
  become unstated. Apply may add (a seeded `occupants`, an optional sub-record
  materialised as explicitly disabled) and may re-derive; it may not delete.
- **No airplane-shaped widget defaults** — a blank project opens with neutral
  defaults, not Appendix-A numbers baked into `value=`.
- **LIMIT vs. ULTIMATE marking** — deliverables (CSV, sbeam cards, Review/Export)
  are ULTIMATE; a per-module *analysis* page may show LIMIT values **only** when
  explicitly marked (a caption + a `LIMIT` marker per column). See
  [`00_program_overview.md`](00_program_overview.md) and `CLAUDE.md`.
  **A LIMIT download must carry the basis in-band (M4-15):** the filename ends
  `_LIMIT.csv` *and* the content states it (a `Basis` column, or LIMIT-marked
  column headers) — an on-page caption does not travel with the file. Pages may
  pair it with the ULTIMATE twin from the sbeam bridge (`*_ULT.csv`, `SF`
  column), as Wing Loads / Fuselage Loads do.
  `tests/test_ultimate_contract.py` scans every view's CSV `download_button`
  and fails on an unmarked load CSV that doesn't route through an ULTIMATE
  channel.

---

## 7. Units at the boundary (the definition-page input pattern)

Imperial is the canonical internal system; the *displayed and exported* system is
whichever the user selected. Results are converted with `convert_results` /
`si_scalar_label` / `to_si_scalar`.

**Input widgets go through one helper — `components.unit_number_input`** (M4-11).
It is the entire input unit boundary: the caller passes canonical Imperial in and
gets canonical Imperial back, so a page cannot convert twice, convert the wrong
way, or forget to convert on the way home. **A view that writes
`to_imperial_scalar` around a `number_input` is a defect** — that hand-paired
idiom is what the helper replaces, and doing both double-converts (a 184 ft²
wing stored as 1982 ft², silently, in SI only). The rollout completed
2026-08-22 (#44, one pass with #51): every scalar `number_input` in
`app/views/` now goes through the helper — the `data_editor` grids remain the
one hand-converted surface, converted per column at Apply.

```python
from components import ALTITUDE_FT, KEAS, page_header, unit_number_input

project, system, U = page_header("configuration_layout")      # title + banner + context

area  = unit_number_input("Wing area S", layout.wing_area_sqft,   # converted
                          kind="area_sqft", key="w_area")
v_a   = unit_number_input("VA", speeds.va, fixed_unit=KEAS, key="va")   # never converted
alt   = unit_number_input("Shoulder altitude", inp.alt,
                          fixed_unit=ALTITUDE_FT, key="alt")           # never converted
taper = unit_number_input("Taper ratio λ", layout.taper_ratio, key="taper")  # dimensionless
...
layout.wing_area_sqft = area      # already Imperial -- no conversion on Apply
```

Exactly one of three modes applies per field, and the mode is **stated by the
caller, never inferred from the label**:

| mode | what it does |
|---|---|
| `kind="area_sqft"` (any `UNIT_LABELS` kind) | converts the seed, suffixes the label with the active system's unit, converts the entry back to Imperial, and suffixes the widget key with the system so a unit switch re-seeds. `min_value`/`max_value` are Imperial too and convert with the value. |
| `fixed_unit=KEAS` / `fixed_unit=ALTITUDE_FT` | the **aviation carve-out**: shows the unit, converts nothing, and does *not* suffix the key (the number means the same in both systems, so the field must survive a switch). |
| neither | dimensionless (ratios, counts, angles in degrees) — no suffix, no conversion. |

Passing both `kind=` and `fixed_unit=` raises `ValueError`: a field is on the
conversion path or off it, never ambiguously both.

An **untouched** field returns the caller's own Imperial value rather than
converting the rounded display seed home — otherwise an SI user's project would
drift by the rounding on every Apply, silently and forever.

**Unfilled is empty, and a typed 0 is real** (#35, CR-A-3). Orthogonally to the
three unit modes, `unit_number_input` accepts `value=None`: the widget renders
**empty** and returns `None` until the user enters a number. An unfilled
`Optional` field SHALL be seeded `None`, never a fake `0.0` — with a zero seed a
deliberate 0 (sea level into `one_engine_out.altitude_ft`, a datum-at-nose
station) is indistinguishable from "not entered" and can never be persisted. The
oracle GUI's generic renderer follows this for every Optional scalar and table
cell: a value that comes back from an empty-seeded widget — including 0 — is a
real entry and lands. Guards: `tests/test_dirty_flag.py`
(typed-zero-lands, unfilled-renders-empty-and-stays-absent).

**Aviation-standard exception:** airspeed (KEAS) and altitude (ft) stay in
aviation units in *both* systems and are never converted — do not add a unit kind
for them; use `fixed_unit=`. Where a deliverable reports them it says so, so an
SI reader does not read an unconverted speed as an oversight.

**Where the selection is read.** Exactly one function reads it:
`components.active_system()` (decision D-16). Since **M4-20 step 2** it returns
`Project.unit_system` (the sidebar toggle writes that field, per D-22), with the
session key surviving only as the fallback for a render that has no project yet.
Views SHALL NOT read `st.session_state["unit_system"]` directly — twelve did until
M4-20 step 6, a second authority for the same decision that made step 2's re-point
reach only the views going through `unit_number_input`/`page`.

Unit **kinds** and their factors/labels live in `SI_PER_IMPERIAL` / `UNIT_LABELS`
in `sloads/units.py` (both views of the one factor owner, `HUMAN_SI` —
`CONVENTIONS.md` §7). The helper is pinned by `tests/test_app_components.py`
(round-trip per kind, per system, plus the carve-out and key discipline) and
end-to-end through real views in both systems by
`tests/test_view_unit_roundtrip.py`.

**Exports follow the toggle too.** The toggle is not display-only: the export
bundle (report, load-case CSV, span CSVs, sbeam BDF) is rendered in the selected
system, one system per bundle, each file stating it in-band — see
[`SUMMARY_REPORT.md`](SUMMARY_REPORT.md) §3.5 for the full rule. The Export page
SHALL show which system the bundle will be written in, next to the download
control, so the choice is visible at the point of export rather than only in the
sidebar. Implemented in **M4-20 step 6**: the page resolves `active_system()`
**once** into a local and hands that one value to every artifact call, and its
caption is built from `deliverable_units` itself so it cannot drift from the
files. Every other view's download buttons take their page's system the same way,
including the per-page **LIMIT** CSVs: `app_shell/limit_csv.py` (L-8i, 2026-08-16) is
the one owner of each page's column→unit map, conversion and unit-suffixed
headers, feeding both the on-screen table and the download (`wing_loads`,
`fuselage_loads`, `tail_loads`; `loads_plots` was already converted and labels
its units in the `Field` cell). These state their units in the headers and
their basis in the `Basis` column / filename, with **no** `units_statement`
line — they are the LIMIT analysis-page channel, not a deliverable
(`CONVENTIONS.md` §3). Guard: `tests/test_limit_csv.py`.

**The Summary report section (Step G8.6).** The Export page's report section
follows the same one-system rule and adds one convention worth stating, because
it is the app's only genuinely *slow* action. The `.tex` renders on every page
run and downloads unconditionally; the **PDF is compiled on demand**, behind a
`Compile PDF` button, and the bytes are held in session state (`report_pdf_bytes`,
keyed by `report_pdf_key` — the `.tex` they came from) so the result survives the
next widget interaction and joins the bundle `.zip`. When the key no longer
matches the current `.tex`, the page says the inputs changed rather than offering
a stale document. A machine with no TeX engine gets a caption naming the engines
it looked for and the `SLOADS_TEX_ENGINE` override — never an exception, and never
a missing `.tex`.

---

## 8. Airplane-definition page standards

The design bar every definition page builds to. Where a page does not yet meet a
standard, the rollout is tracked in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) **Phase E**.

### 8.1 Explanation

Every domain input widget carries a `help=` tooltip; dense and grid pages
(the unified Geometry page — parametric layout, fuselage outline and WINGGEOM
surface planforms, Step G1 — Aerodynamic Data coefficients, Weight/CG inertias,
and a short one on Structural Speeds)
additionally carry a collapsible **"ℹ️ Parameter guide"** expander. Jargon (MAC,
XLEMAC, static margin, neutral point, tip-back/overturn, shoulder altitude, KEAS,
the aero `C0…C4` polynomials, per-item inertias and the parallel-axis convention)
is defined for the user, with FAR paragraph + Reference-1 program/chapter
citations. The three `st.data_editor` grid pages (Weight/CG inertias, Wing
Geometry LE/TE points, the Aero `C0…C4` table) explain their columns in the guide
expander rather than per column. *(Implemented — Phase E2.)*

### 8.2 Graphical review

Every page that takes substantial numeric input offers a plot or derived readout
that lets the user *see* whether the inputs are self-consistent:

| Page | Graphical review |
|------|------------------|
| Geometry (Step G1: parametric + fuselage outline + WINGGEOM planforms; Step G6/G6b: single-source empennage + landing gear) | Three-view (CG, neutral point, **gear strut + wheels** from the axle geometry, fuselage outline, mass bubbles, engines, **elevator/rudder** shaded from the aft Saft/S band); per-surface planform-derived Area/MAC/XLEMAC/AR/span. The **Empennage & control surfaces** (Step G6) and **Landing gear** (Step G6b) sections are the single input homes for the h-/v-tail + elevator/rudder (`GeometryInput.empennage`) and the tricycle-gear axle geometry (`GeometryInput.landing_gear`), feeding both this three-view and the tail-/ground-load analysis |
| Flight Envelope (V-n) | Continuous LIMIT design envelope (curved stall boundary, flaps-up/down manoeuvre envelope, gust lines) overlaid on the rigorous Mach-corrected balanced corner points *(consolidated — Phase E6)* |
| Weight/CG/Inertia | CG marker + mass-distribution plot (with WTENV limits when defined) *(implemented — Phase E3)* |
| Aerodynamic Data | Echo tables only *(curve plot deferred — see backlog)*; **fuselage pitching-moment (Munk) estimate** — volume/fineness/k₂−k₁/ΔM1 from the Geometry outline, off-by-default, overridable (Step G4) |
| Aircraft Comparison (Export) | Parameter table + six fleet scatters (loading, weight, geometry) *(Phase F, Step F2)* |

The continuous LIMIT design envelope is built by the pure `sloads/vn_diagram.py`
helper from the STRSPEED design speeds + limit load factors; its gust lines are the
textbook Pratt form (14 CFR 23.341) and are explicitly captioned as approximate.
It is drawn as a grey backdrop on the **Flight Envelope (V-n)** page (FLTLOADS)
behind the rigorous, Mach-corrected balanced corner points, so the envelope visibly
bounds them — a single consolidated V-n. (Originally a separate diagram on
Structural Speeds in Phase E3; merged onto Flight Envelope in Phase E6 to remove the
redundancy. The Structural Speeds page now shows only the numeric design-speed
tables and points to the Flight Envelope page.)

### 8.3 Input-consistency validation

Pages surface explicit `st.warning`s on inconsistent input — taper ratio > 1,
non-positive area, leading-/trailing-edge point ordering, a wing-area mismatch
between Configuration & Layout and Wing/Surface Geometry, a CG outside the
weight-CG envelope, or a per-case `safety_factor` outside the legal [1.0, 1.5]
band (M4-14; rendered on the Export page, where the consequence lives). The
checks are pure predicates in `sloads/validation.py`
(`consistency_warnings(project)`), each tagged with the page that renders it; the
CG-envelope check compares the WTONECG CG against the WTENV structural envelope and
is silently skipped when that envelope (or the wing geometry it needs) is absent.

**One renderer, both GUIs, and the tag is a workflow key (#82, 2026-08-24).**
`app_shell.components.render_consistency_warnings(project, key)` is the **only**
consumer of `consistency_warnings` in either front-end, and `page_header` calls
it from the step key it already holds — so every page that opens with the shared
header shows the warnings tagged for it, in `app/` and in `oracle_app/` alike,
with no per-page call to forget. Two things were wrong before it, and they
compounded: the main GUI open-coded the loop in six views, and
`oracle_app`/`app_shell` had **no consumer of `ConsistencyWarning` at all** — so
a page-targeted entry-error channel that is part of the analysis contract
(C210-15) was dark exactly where entries are made, and a detected contradictory
`wing_fraction` entry survived a whole build review unshown (C210-35). Worse,
two `page` tags named pages that no longer existed — `weight_cg_inertia` (the
weights page has been `weight_mass` since Step G3) and `wing_geometry` (merged
into `configuration_layout` at Step G1) — covering 19 checks, 14 of them the
weights group, reachable only because two views compared against the old strings
by hand. **Every `page` tag is now a `sloads.workflow.STEPS` key**, the nav SSOT,
guarded by `tests/test_validation.py::test_every_warning_targets_a_real_page`
over both the `PAGE_*` constants and the tags the live checks actually emit
(rule 3). A page may re-state one warning next to the result it bears on via
`only_codes=` — the Design Speeds page's operational-limitations tab is the one
instance. Warnings tagged `export_report` stay main-GUI-only: the oracle GUI has
no export page and no way to set a safety-factor override, so the guard permits a
tag that is a workflow key without being an oracle step (OG-2 scope).
The Project JSON Editor additionally scans the **raw** edited dict at Apply for
invalid `safety_factor` values (via the public `validation.safety_factor_valid`)
and warns that they were reset — `io.py`'s readers coerce any invalid persisted
factor to the conservative 1.5 default on load, so the built project cannot show
what was typed. *(Implemented — Phase E3; safety-factor check M4-14.)*

### 8.4 Fleet comparison — the Aircraft Comparison page

The airplane is placed against the reference fleet in
`app/data/reference_aircraft.csv` (29 aircraft spanning GA singles to ~41,000-lb /
50-seat regional turboprops, so a concept airplane has real comparators) on **one
dedicated page** — **Aircraft Comparison**, in the Export phase before Results
Review (`app/views/aircraft_comparison.py`, GUI-only `WorkflowStep`). The two input
pages (Configuration & Layout, Weight Estimate) **no longer** carry a fleet block —
the comparison lives in exactly one place (Phase F, Step F2). The page carries a
quantitative readout (nearest-3 similar aircraft, W/S & W/P percentile band, outlier
flags), a **parameter table** (subject row on top, then the nearest-N over MTOW,
OEW, power, W/S, W/P, wingspan, wing area, aspect ratio, seats), and **six scatter
tabs**: W/S-vs-W/P, MTOW-vs-OEW, and four geometric scatters (wingspan / wing area /
aspect ratio / seats vs. MTOW).

The numeric core is the pure, unit-tested `sloads/fleet.py`
(`fleet_stats(subject, fleet)` → `FleetStats`; no pandas / file access / Streamlit);
the CSV load and rendering are owned by the page itself. Locked decisions
(Step E4, 2026-07-15): **D-E4-1** pure core in `sloads/fleet.py`; **D-E4-2**
nearest-N uses a normalized-Euclidean distance over whichever metrics the subject
supplies (always log-MTOW; add W/S and W/P when known), and the outlier flag is the
fleet **p10–p90** band; **D-E4-3** the readout lists the **nearest 3** from the
whole fleet, with jets (`max_hp = 0`, no shaft power) excluded from W/P distance and
the W/P percentile only, never from the comparator pool. Step F2 decisions
(2026-07-16): **D-F2-a** the nearest-N distance stays on MTOW / W/S / W/P — the
geometry (span / area / AR / seats) is **presentation-only** (table columns and plot
axes), never a distance term; **D-F2-b** six tabs, one plot each; **D-F2-c** no
category coloring (two-series `Reference fleet` vs `This airplane`). *(Implemented —
Phase F, Step F2; the shared `render_fleet_comparison` wrapper on the two input
pages, its Phase-E4 home, was removed.)*

**M2-5 (2026-07-20).** The comparison **subject** now resolves its wing geometry from
the WINGGEOM planform when no parametric layout is present:
`_subject_from_project` reads wing **area** `parametric → geometry.by_name("wing")
surface (Total area ÷ 144) → speeds.wing_area_sqft`, wing **AR** and **span**
`parametric → surface` (span set directly from the surface Span ÷ 12, not
back-derived from √(AR·area)). Most shipped examples carry `geometry.surfaces` rather
than a parametric layout, so this is what fills W/S / area / span / AR for them (e.g.
GA-6 recovers AR 6.095 / span 33.5 ft). The page **stays in the Export phase** (the
single navigation-truth order in `workflow.py` is unchanged); a workflow-derived
`page_link` on the **Weight & Mass Properties** page makes the fleet check reachable
at definition time.

---

## 9. FAR 23 applicability & concept-awareness (warn-but-allow)

The tool must let a user describe an airplane **beyond** FAR 23 while making clear
it is outside the certificated band — never blocking. The design:

- **Limits encoded once** in `sloads/constants.py`
  (`FAR23_MAX_WEIGHT_LB = 12500`, `FAR23_MAX_PASSENGER_SEATS = 9`, and the encoded-
  but-dormant commuter tier `FAR23_COMMUTER_MAX_WEIGHT_LB = 19000` /
  `FAR23_COMMUTER_MAX_PASSENGER_SEATS = 19`; `DEFAULT_FLIGHT_CREW = 1`, the crew
  assumed when no weight-estimation slice is present). The commuter tier is dormant
  until a distinct Commuter category exists (backlog).
- **A pure `far23_applicability(project)` helper** (`sloads/applicability.py`)
  returns the structured exceedances (`Exceedance(field, value, limit, label)`); no
  Streamlit, unit-testable, and yields *no* exceedances on Appendix-A GA inputs.
  The MTOW check reads `speeds.weight_lb`, falling back to the Weight DB total; the
  seat check compares `passenger seats = effective_occupants − effective_crew`
  against 9, where the crew is the user-set `WeightEstimationInput.crew`.
- **A non-blocking banner** (`app_shell.components.render_applicability_banner`) on the
  Dashboard and the definition pages when a non-concept airplane exceeds a limit —
  "exceeds FAR 23 applicability; results are concept-mode extrapolation" — with a
  one-click **"Switch to Concept"** action that also seeds the concept load factors
  from the computed FAR 23.337 values so the flip never breaks the downstream calc.
  The action is **`app/`-only**: `switch_action=False` (via `page_header`/`page`)
  renders the same warning without the button for a GUI that carries no concept
  page — the oracle GUI passes it, and `tests/test_oracle_gui.py` guards both the
  behaviour and the drift (review 2026-08-20 CR-A-4).
- **`occupants` is a first-class field** (`StructuralSpeedsInput.occupants`,
  co-located with `category` + `weight_lb`; seeds its default from the Weight
  Estimate seat count; echoed read-only on Configuration & Layout), driving the
  seat-count check. **`crew` is a user-set field** (`WeightEstimationInput.crew`,
  co-located with `seats`; default 1) that is subtracted from occupants for the
  seat check and carried in the **operating empty weight** (WTESTIMA reports a
  derived `OEW = empty + crew×170` line; the manufacturer's-empty oracle is
  unchanged).
- **Concept mode** (`speeds.category == "C"`, surfaced by `Project.is_concept`)
  lets the user set their own limit load factors and, on GA inputs, reduces
  exactly to the FAR 23 result.

*(Implemented — Phase E1, schema v22.)*

---

## 10. JSON persistence

`sloads/io.py` is the **only** dataclass⇔JSON mapper. `project.json` **values** are
always canonical Imperial (`io.py` never converts units); the project's
unit-system field records the user's *display/export preference* only and never
changes how a stored value is interpreted. The load path carries no unit
assumption, so loading an Imperial file under an SI toggle converts exactly once,
at each page's render boundary. `Project` carries a `schema_version`
(`models.py`, `SCHEMA_VERSION`), and pre-production that version is the only one
this build reads (#93).

Every load path is hardened (Phase E5): the three sidebar actions (Open saved,
Load example, Upload) and the Project JSON Editor's **Apply**
(`app/views/project_editor.py`, which round-trips the whole project as JSON in the
selected units via `project_dict_to_display` / `project_dict_to_imperial`) all show
a graceful `st.error` on a malformed / wrong-shape file instead of a traceback.

**A file at any version but the current one is one of those errors** (#93). The
decision is not the GUI's: `migrations.migrate`, reached through
`io.project_from_dict`, raises `SchemaVersionError` — a `ValueError`, so the load
paths' existing except clauses report it and no project is adopted. The shell
classifies nothing itself, which is the structural half of the fix: until #68 it
compared the *built* project's stamp, already normalised by the loader, so the
check always read "ok" (review PB-14). Guards:
`tests/test_app_shell.py::test_no_gui_decides_whether_a_file_is_readable` and
`::test_opening_an_older_file_is_refused_and_adopts_nothing`.

A reader that flags something about an otherwise-readable file (an engine
layout/count disagreement, #66) still warns rather than refusing;
`project_state.safe_load` captures those warnings and shows them as toasts,
because the adopt path ends in `st.rerun()`.

---

## 11. Status & open work

**Implemented today:** the workflow-aligned navigation (Start + six analysis-flow
phases since Step G2; the Phase-D six-section grouping it re-sequenced), the global unit toggle and
project-file widget, the shared-`Project` data flow and seed-chain, the
form+Apply/merge page conventions, the unit-boundary input pattern across all
definition pages (§7; the last seven hand-paired views moved onto the helper
2026-08-22, #44), the Configuration & Layout three-view, the
FAR 23 applicability banner + `occupants`/`crew` fields and OEW line (§9,
Phase E1), the per-widget `help=` tooltips + parameter-guide expanders across
the six Airplane pages (§8.1, Phase E2), and the V-n diagram +
Weight/CG mass-distribution plot + input-consistency warnings (§8.2/§8.3,
Phase E3; the V-n later consolidated onto the Flight Envelope page in Phase E6),
and the dedicated **Aircraft Comparison** page — parameter table + six fleet
scatters + nearest-3 / percentile band / outlier flags via the pure
`sloads/fleet.py` (§8.4, Phase E4 core; consolidated onto its own Export-phase
page in Phase F, Step F2), and the graceful, schema-aware load path across the
sidebar and the JSON Editor (§10, Phase E5).

**Phase E is complete** — all steps E1–E5 have shipped.

The schema field list is **single-sourced in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)** (generated; it prints the current
`SCHEMA_VERSION`, whose owner is `sloads/models/project.py`); the per-step migration history is recorded in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
(recent steps: v29 single-source CLmax
stall; v30 M2-6 wing/fuselage derived geometry; v31 M2-10 operational placards;
v32 M2R-2 `LandingInput.n` write-back removed; v33 M4-7 per-case
`safety_factor` on `CriticalCondition` + the four distributed-load results;
v34 M4-18 `SurfaceInput.ref_axis_pct` (the loads reference axis, LRA) +
`WingLoadResult.torsion_axis`; v35 M4-1 `SurfaceInput.front_spar_pct`/
`.rear_spar_pct` (the wing carry-through the Ch 15 fuselage moment closure
reacts over; `None` = not entered → assumed default); v36 G8.2
`Project.revision`/`.checked_by`/`.approved_by`/`.description` — the summary
report's document-control header, all free text defaulting to `""`; v37 M4-9
`LoadValue.key`, the stable machine identity that replaced the display label as
the thing report/export/view/test code matches on — the first hop with a real
data backfill, `migrations._v36_load_value_keys`; v38 M4-20
`Project.unit_system`, the system every *deliverable* is rendered in — a
**preference only**, never a claim about the units of the values stored beside
it, which stay canonical Imperial. Additive with a total default, so it needs no
migration hop: absent *is* its documented value, Imperial. The sidebar
Imperial/SI toggle writes it, so changing units is a project edit and shows as an
unsaved change (D-22); v39 M4-2 unified load-case identity — no field added or
removed, but a wing or ONENGOUT case's `case_id` **string** changes (SELECT's
retired `W-40..49` band, wing ids now keyed to the condition's name rather than
its list position, ONENGOUT moved to its own `VT-30..` band). The one persisted
field that references those strings, `CriticalLoadSet.selected_case_ids`, is
validated on load: an id matching no condition is dropped with a warning rather
than silently ignored); v40 F25-2 the dive-speed basis — `speeds.vd_basis`
(`speed_ratio` | `mach_margin`, the two routes 14 CFR 25.335(b) offers
disjunctively) plus `mach_margin_min`/`mach_margin_basis` and the rough-air
speed `vb_kt`, and the **removal** of `speeds.mach_limit.mc`/`.md`. Those two
were a stale duplicate — stored in the file, ignored by the Speed–Altitude tab
(which recomputed MC/MD from the design speeds) and honoured by the CLI, so one
project reported two different MNE/MFC depending on the front-end. MC/MD are now
derived by `structural_speeds` and passed to `mach_limit` explicitly; hop
`migrations._v39_mach_limit_mc_md` drops the dead keys, and `vd_basis` defaults
to the speed-ratio route so no existing project's numbers move); v41 plan 11 B1
`MassItem.component` — the explicit component tag that makes `weight.items` the
mass single source of truth (absent → inferred from the item's position), plus
`FuselageMassInput.stations_are_override` marking a hand-entered station table as
deliberate rather than merely present; v42 plan 09 T1 the distributed empennage —
`Project.tail_mass` (a `TailMassInput` per modelled tail surface: uniform area
density, whole-surface weight) and `LoadsResult.htail_span`/`.vtail_span`, the
spanwise tail distributions the empennage deck is written from. Additive with
total defaults, so no hop: a project with no empennage mass writes no key and
round-trips byte-identically to a pre-v42 file. The tail *planform* is not a new
field — decision T-1 reuses `SurfaceInput` via an optional `"htail"`/`"vtail"`
entry in `geometry.surfaces`, validated against the oracle-authoritative scalar
area/span to 1 % and **derived as a rectangle, marked assumed**, when absent);
v43 plan 13 B8a-1 the fin's vertical placement — `VTailLoadsInput.
vtail_root_waterline_z`, the waterline of the vertical-tail root, `0` meaning
"derive it and mark it assumed". Additive with a default, so no hop: a pre-v43
project keeps the placement it would have been given. It exists because the fin's
height above the CG is the lever arm of the roll moment a side load makes, and
the load path previously used `0` — modelling `ga6_normal`'s fin 64.5 in *below*
its own CG and reversing that moment's sign); v44 the empennage mass SSOT —
`TailMassInput.weight_is_override`, which demotes the entered `panel_weight_lb`
to an explicit override of the `htail`/`vtail`-tagged `weight.items`, exactly as
v41 did for `FuselageMassInput.stations_are_override`. Hop
`migrations._v43_tail_mass_override` marks a non-zero entered weight as
deliberate so a pre-v44 project's tail loads do not move under it; a project that
entered nothing — which is *every* shipped fixture, and why every h-tail deck the
suite produced was silently air-only — now derives the surface weight from the
item data base and gains the inertia it should always have had; v45 plan 09 T6
the discrete control-surface load path — `TailMassInput.hinges_span_in` and
`.actuator_span_in`, the hinge and actuator span stations
`control_load_mode = "discrete"` requires (and refuses to run without, since a
silent fall back to `"smeared"` would report a localized load path the deck does
not contain). Additive with empty defaults, so no hop: absent *is* the
documented value — no attachment geometry means the surface stays in the smeared
mode every pre-v45 project was already in, and every shipped deck is unchanged
to the byte; v46 M4-8 / step 10 piece 1 `Project.safety_factors` — the **override
layer** over the governing safety-factor table (decision G-11). The table's rows
are code (`sloads/safety_factors.py`), so a project file records only deviations
from the regulation, never the regulation itself. Additive with a `None` default
and written only when it carries an override, so absent *is* the documented value
— the factors 14 CFR 23.303/25.303 derives — and every shipped fixture is
byte-for-byte unchanged; v47 step 10 piece 2 the **weight/CG case model and the
gear inputs**, one hop for the whole set (decisions G-2, G-3, G-4, G-5, G-14).
`CgCase` gains `analyses` (a *set* of `FLIGHT`/`GROUND`, so one case can feed
several analyses instead of being entered twice and drifting apart) and `role`
(`aft_max_landing` | `fwd_max_landing` | `fwd_light`), which retires LANDLOAD's
positional-plus-name-matched contract — a renamed case used to silently reorder
an oracle-locked reaction table. `FlightLoadsInput.cg_cases` and
`LandingInput.cg_cases` are **removed**: the first had been a derived copy of
`weight.cg_cases` since v19 kept in step by a *page* rather than by the model,
and the second never joined the SSOT at all. `WeightInput` gains
`max_landing_weight_lb` (moved off `LandingInput`) and `max_takeoff_weight_lb`,
and `LandingInput.gross_weight_lb` is **removed** with them — its
`max(landing cg_cases)` fallback returned MLW, not MTOW, making `WR = 1.0` and
understating the braked-roll/side/nose cases by ~5 % for any project that left
it unset. `MassItem` gains `consumable` (mission fuel, burned down before payload
is dropped for a GROUND target) and `LandingGearInput` gains `carrier`
(`body` | `wing`, **no default**) and `attach`. Removals and a relocation, so
this one needs a hop: `migrations._v46_cg_case_model`, output-neutral by
construction — every value it writes comes from the file's own, MTOW from
`speeds.weight_lb`, which measurement showed equals the other four
representations on every shipped fixture; v48 step 10 piece 3
`LandingGearInput.weight_lb`, the leg's own weight whole-leg-trunnion-down, which
closes the gear load report's free body (G-12a) — additive with a `0.0` default,
and absent *is* the documented value, "not stated", which the report prints as a
blank inertia term with its reason rather than as a leg that weighs nothing;
v49 the body drag carrier `LayoutInput.body_drag_waterline_z`, the waterline the
airplane's **non-wing** drag is applied at in the assembled model (design note
`../40_history/24_body_drag_carrier_note.md`, decision D-1). Additive with a `0.0`
default meaning "derive it" — the wing reference plane `zw`, marked assumed and
stated in-band, exactly as v43's `vtail_root_waterline_z` handles the same class
of question — so no hop, and a pre-v49 project takes the derived value. It exists
because that waterline is the *only* free parameter of the body-axial load (its
fuselage station reaches no gate), and the obvious geometric candidate,
`root_waterline_z`, is the **wing** root: deriving from it puts `ga6_normal`'s
`SIDE GUST` pitch residual over the 1 % gate;
v50 the explicit loading definition `CgCase.loading` (decision **D-25**, design
note `../40_history/25_d25_cgcase_loading_note.md`) — which discretionary items a
payload case carries, the fraction of any consumable row that is aboard, and an
optional entered ballast row. Additive and **optional**, so no hop: absent is the
documented value, "derive the loading by searching the item database", which is
what every pre-v50 project does bit-for-bit. Where it *is* entered the loading is
authoritative and the case's `weight_lb`/`xcg`/`zcg` become a checked echo of it;
v51 the entered side-of-body butt line `SurfaceInput.sob_y_in` (decision
**BM-1**, note `../30_future/24_lra_beam_model_review_note.md`) — one quantity
read by the wing SOB reporting node and the h-tail attachment. Additive and
optional, so no hop: absent falls back to half the fuselage width, marked
assumed;
v52 the LRA beam model's inputs (step 12, implementation note
`../40_history/27_lra_model_implementation_note.md`) — `FuselageSection.z_centre`
(the section-centre waterline the fuselage LRA runs through, note 24 R-4),
`EngineInput.mounted_on` ("fuselage" | "wing", decision BM-4),
`AileronLoadsInput`/`FlapLoadsInput` butt-line + hinge/actuator fields, and
`SurfaceInput.ref_axis_pct` widened to Optional (R-7c: `None` = "not entered";
reporting reads the effective 25 % through `SurfaceInput.ref_axis`, and the
reader maps a stored 0.25 — which the pre-v52 writer emitted unconditionally —
back to unset). All additive/widening with unchanged effective defaults, so no
hop.
This paragraph's version number is guarded by
`tests/test_data_dictionary.py::test_gui_design_schema_line_current` — update
it (and this list) with every `SCHEMA_VERSION` bump.
Phases D–F (the six-section GUI restructure, the
usability/concept-awareness work, and fleet comparison) are all complete, and Phase G
is under way (G0–G6 + G6b shipped). The **open GUI plan is now
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) → Phase G** — the
workflow-aligned rework (one-unit-per-dimension, single-source-of-truth geometry,
re-sequenced analysis-flow navigation, fuselage-moment/trim-plot/empennage
features); its narrative and locked decisions G-1…G-4 are in
[`../30_future/03_gui_rework_plan.md`](../30_future/03_gui_rework_plan.md). The
Phase-D narrative is in
[`../40_history/05_phase_d_gui_workflow_plan.md`](../40_history/05_phase_d_gui_workflow_plan.md).
