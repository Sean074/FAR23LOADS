# Critical review — Oracle GUI, core analysis, above-oracle layer, main GUI & CI (2026-08-20)

**Charge:** whole-surface critical review of the suite across four areas — **(A) the
Oracle GUI** (`oracle_app/` + the shared `app_shell/`, against design note 32),
**(B) the core FAR23 analysis** (`sloads/modules/` and the SSOT owners, against
`CONVENTIONS.md` and the oracle contract), **(C) the functionality above the
oracle** (concept mode, balancing, export, report — against the mission loop and
the 2026-08-10 review's defect classes), and **(D) the default GUI and CI**
(`app/`, `workflow.py`, `.github/workflows/`, the test infrastructure and doc
drift guards). Conducted per
[`CODE_REVIEW_PROCESS.md`](../10_standard/CODE_REVIEW_PROCESS.md) as four
independent parallel deep passes followed by a cross-pass synthesis. Every
finding was verified by reading the code and, where behavioral, reproduced live
(AppTest probes, rendered-report inspection, guard-blindness demonstrations).
Already-filed backlog/parked items were excluded from re-reporting; the ones
judged critical or high-leverage are ranked in §6.

**Gate state at review:** `ruff` clean; `mypy` clean (76 files); full suite
**2430 passed, 20 skipped, 1 xfailed, 0 failed** (671 s serial / 269 s
`-n auto`); the single xfail is the recorded RJ-SI LRA sbeam condition-heuristic
limitation pinned by baseline 0.6.0. Baseline commit **`4b1ddcc`** (note 32
OG-F) — the OG-F work was in flight at review start and was committed mid-review;
all findings were re-checked against the committed tree, and the OG-F extraction
itself was reviewed (verdict: consistent for the main GUI; only CR-A-5/CR-D-10
below touches it).

**Keys.** Findings carry stable keys `CR-<PASS>-<n>` (pass A/B/C/D as above);
keys are citations for issues and PRs, not a priority order. Severities per
`CODE_REVIEW_PROCESS.md` §4. Closure tiers per `CLAUDE.md`.

---

## 0. Verdict

**No `[CRITICAL]` findings: no wrong load value was found in any shipped deck or
report byte.** The three export paths traced end-to-end (balanced deck, wing
headless, mass family) apply the ULT factor exactly once; the six-DOF card-text
closure gates are real in both unit systems; every 2026-08-10 CRITICAL/MAJOR fix
was audited and found genuinely closed with teeth (§5) — with one rot instance
(CR-C-1). The core calc's constants ownership, sign conventions, and cited
equations checked clean everywhere deep-read.

The ten `[MAJOR]` findings concentrate in three seams, none of which today's
gates can see:

1. **GUI data-entry integrity** (CR-A-1, CR-A-2, CR-D-1, CR-D-2): two edits in
   one Streamlit rerun can silently discard one on the oracle GUI's deepest
   pages; ten quantities are independently editable in 2–4 places with no
   owner marking; the shared Upload path reruns unboundedly in both GUIs; and a
   no-op Apply in SI silently rewrites stored Imperial values in ~7 main-GUI
   views. The numbers that *reach* the calc are correct — but what the user
   typed may not be what reached it.
2. **Guard blind spots over core invariants** (CR-B-1, CR-B-2, CR-B-3): the
   platform-stability drift guard is a substring grep that a live keyed pick in
   `select.py` already evades; the concept→FAR23 "exact reduction" identity is
   gated at ±0.1% rather than bit-for-bit; and the 23.361(b)(1) stoppage torque
   has no numeric assertion at all.
3. **Statements about the deliverable** (CR-C-1, CR-C-2, CR-C-3): the report
   declares the flagship balanced deliverable OVER its residual gate on every
   fixture with ground cases (143.9 % headline vs 0.624 % for the family the
   gate actually applies to), the newest deck family (LRA model) ships with no
   manifest row — the F-D2 class re-opened one release later — and the manifest
   mislabels the LIMIT-by-design inertia check "ULTIMATE". The 0.6.0
   capabilities outran their controlling document.

The repeated lesson (§4) is the one the repo's own rule 3 states: a gate that
does not read the **shipped artifact** — the rendered sentence, the zip's
namelist, the AST rather than a substring — rots the first time the code grows
past the shape the gate assumed.

---

## 1. Findings — MAJOR

### Pass A — Oracle GUI

**[MAJOR] CR-A-1 `oracle_app/form.py:255-294` (`record_at`/`rows_at`/`_PENDING`/`commit_pending`) — two edits in one render pass silently discard one of them when their record groups share a missing ancestor.**
WHY: `record_at` creates a fresh detached blank for **every group** that walks
through a missing ancestor — it never reuses an already-pending record for the
same `(owner, segment)`. On `configuration_layout` the groups
`geometry.parametric`, `geometry.empennage.htail`, `geometry.landing_gear.*`
each append their own `(Project, "geometry", <new blank>)` to `_PENDING`;
`commit_pending` attaches them in order and the last non-blank chain **clobbers**
the earlier ones. Reproduced through the real renderer under AppTest: on a blank
project, setting `geometry.empennage.htail.htail_area_sqft=32.5` and
`geometry.parametric.wing_area_sqft=180.0` in the same rerun leaves
`geometry.parametric is None` — the typed 180 is gone while the widget still
displays it. Two widget changes in one rerun is normal Streamlit behavior (fast
edits, `data_editor` batching), and a Save on the next rerun runs the sidebar
handler before the page body re-persists, so the loss reaches disk. No guard
test can see it: `test_dirty_flag.py` renders with no edits, and its persist
test edits exactly one field on a one-level-deep chain.
FIX: in `record_at`/`rows_at`, before building a blank, scan `_PENDING` for an
existing entry with the same `(id(owner), segment)` and reuse it; or key
`_PENDING` as a dict on `(id(owner), name)`. Add a two-edits-one-rerun AppTest.
CLASS-SWEEP: same defect in `rows_at` (list chains) and every page with ≥2
groups under one optional ancestor — `configuration_layout` (8 groups under
`geometry`), `weight_mass` (5 under `weight`), `landing_loads` (3 under
`landing`), `structural_speeds` (`speeds` + `speeds.mach_limit`). `app/` views
are unaffected (they persist whole slices on Apply). Tier M.

**[MAJOR] CR-A-2 `oracle_app/form.py` (`render_scalar`) + `sloads/field_registry.py` — decision OG-8's precondition is not met: the gear-geometry duplication is live and independently editable on two oracle pages, and OG-7's "entered scalar wins and is marked" has no marking in this GUI.**
WHY: OG-8 says the `geometry.landing_gear.*` vs
`landing.main_gear/nose_gear/tread_in` duplication "gets one owner before it is
put on an oracle page." Both copies shipped on oracle pages (Geometry and
Landing Loads) as plain editable widgets. Verified from the registry: **10
quantities have ≥2 independently-editable copies** in `oracle_input_paths()`,
including gear tread (`geometry.landing_gear.tread_in` / `landing.tread_in`),
both static axle positions, and wing reference area in **four** places
(`geometry.parametric`, `flight_loads`, `landing`, `speeds`). The registry
records the owner (`test_each_quantity_has_at_most_one_owning_field` passes),
but nothing in `render_scalar` disables, derives, or flags a non-owner copy — a
user entering tread on Geometry and a different tread on Landing feeds
inconsistent numbers to LANDLOAD with no warning. The GR-GEOM-3 marking
("entered scalar wins and is marked") likewise does not exist in the generic
renderer for `flight_loads.mac`/`wing_area_sqft`/`xw`/`zw`.
FIX: the registry already carries `is_owner`/`derived_from` — the generic
renderer should read it: render a non-owner copy disabled with a "derived from
`<owner>`" caption, or at minimum a mismatch warning when two copies disagree.
One edit in one renderer — which is what the single-renderer design bought.
CLASS-SWEEP: all 10 registry quantities; the two `airplane_length_in` copies
(htail/vtail) are the same class inside one page. Tier M.

### Pass B — core analysis

**[MAJOR] CR-B-1 `sloads/modules/select.py:484` — a keyed critical-case pick bypasses `_extreme`, and the drift guard cannot see it.**
WHY: `p = (min if want_min else max)(bal_a, key=lambda p: total(p)[0])` in
`select_htail_maneuver` (the 23.423(a) pick over the `BAL A` points — the very
worked example `_extreme`'s docstring uses for the platform-ulp failure) is a
raw builtin keyed pick. The `CONVENTIONS.md` §7 platform-stability row claims
"every keyed max/min pick" in `select.py` goes through `_extreme`; its guard
(`tests/test_select.py:410-416`) greps for lines containing `"max("`/`"min("`
**and** `"key="` — this construction contains neither substring, so the guard
passes while the invariant is broken (verified: zero hits with the line
present).
FIX: route through `_extreme(bal_a, lambda p: total(p)[0], largest=not
want_min)`; harden the guard to an AST walk (builtin `min`/`max` call with a
`key` kwarg) instead of a substring grep.
CLASS-SWEEP: raw keyed picks over load candidates outside the declared owner:
`sloads/modules/landing.py:596` (gear governing-case pick, whose own docstring
records that the family ties — "cases 19-22 share an identical VMP" — the one
sibling that should adopt the tie rule), `aileron.py:85-86`,
`one_engine_out.py:272`, `weight_envelope.py:285/297/302`. The §7 row scopes
the owner to `select.py` only, so these are convention-gap siblings rather than
guard violations. Tier M.

**[MAJOR] CR-B-2 `tests/test_concept.py:157-161` — the "concept reduces exactly to FAR23 on GA inputs" identity is gated at ±0.1 %, not exactly.**
WHY: `CLAUDE.md`, the backlog invariant block, and the test's own header
("must reproduce the whole pipeline **bit-for-bit**") state an exact identity;
`_assert_modules_identical` asserts floats with
`math.isclose(rel_tol=1e-3, abs_tol=1e-9)`. A concept-branch defect shifting
any delivered load by up to 0.1 % passes the only test that enforces the
superset invariant — the "tolerance used where exact equality is required"
defect from `CODE_REVIEW_PROCESS.md` §3.
FIX: tighten to exact equality (`fv.value == cv.value`) — the P1-3 analysis
says the only numeric branch echoes the user's load factors verbatim, so
bit-for-bit should hold; if it does not, that is itself a finding.
CLASS-SWEEP: `test_concept_load_factors_match_far23_caps` asserts with `==`
correctly; `test_concept_closure.py` gates are closure identities and
appropriately toleranced. No other reduction-identity test exists. Tier S
(test-only) — but blocking-class importance.

**[MAJOR] CR-B-3 `sloads/modules/engine.py:301` — the 23.361(b)(1) sudden-stoppage engine-mount torque has no numeric assertion anywhere.**
WHY: `tests/test_engine.py` pins only `_prop_inertia` (9.174 slug-ft²) for this
condition; `tests/test_engine_far25.py:57-59` asserts only that
25.361(a)(3)(i) equals 23.361(b)(1) (self-consistency, not a value). Policy
says twin-only cases are closure/formula-locked, but there is no formula check
of `I·ω/Δt` either — a regression in the rotor summation or Δt handling would
pass the suite. Compounding it, `int(-torq_total)` uses Python `int()`
(truncate toward zero) where BASIC `INT()` floors: for the negative reported
torque they differ by 1 ft-lb, and nothing pins which is intended
(`CONVENTIONS.md` §5 records the 3-decimal truncations at engine.py:58/65/112
but not this whole-integer one).
FIX: add a formula-closure assertion
(`torq == iprop·ω_prop/Δt + Σ irotor·ω_rotor/Δt` on the twin fixture, page-cited
if a legible Appendix B surfaces); verify `int()` vs `math.floor()` against
ENGLOADS.BAS in Appendix C (`reference/FAR23Loads_Code.pdf` p373 ff); same at
engine.py:434.
CLASS-SWEEP: the only two whole-integer truncations in the package are these
two sites; the 3-decimal truncations at engine.py:69/126 operate on positive
values where Python `int()` and BASIC `INT()` agree. Tier M.

### Pass C — above the oracle

**[MAJOR] CR-C-1 `sloads/report/content.py:1986` (`_manifest_rows`) — the LRA model deck ships in the Export bundle with no manifest row: the F-D2 defect class re-opened for the newest deliverable.**
WHY: `app/views/export_report.py:285` puts `lra_model.bdf` into
`_bdf_artifacts`, which `_zip_bundle()` writes as
`sbeam/<stem>_lra_model.bdf` — but `_manifest_rows` has no LRA row, and
`tests/test_report_content.py`'s exhaustive pin
(`{row[0] for row in rows} == set(SUMMARISED_IN)`, no `lra` entry) *proves* the
absence. The 0.5.0 baseline's gate claim "§4.7 manifest lists every artifact
the bundle carries" is now false; the CLI `--export-target lra` artifact is
likewise named in no controlling document. The 08-10 review's exact words for
this class: "an artifact the controlling document does not name travels without
a basis."
FIX: add the manifest row (gated on the same `run.cases` condition the view
uses) plus a `SUMMARISED_IN` entry; structurally (rule 3), add a gate that
opens the **actual zip** (`_zip_bundle` extracted into a pure helper) and
asserts `namelist() ⊆ manifest rows` — today no test reads the shipped zip, so
the next bundle addition re-opens the hole again.
CLASS-SWEEP: every other zip member has a row (wing/body/tail/control ×2,
balanced, mass ×3, gear, report/methods/case-index/SF — checked one by one).
`lra_loads.bdf` (CLI `--lra-import` route) is also un-manifested; same fix
site. Tier M.

**[MAJOR] CR-C-2 `sloads/report/content.py:1808-1816` (`_section_balanced`) + `app/views/balanced_cases.py:124-138` — the report's §6 declares the primary deliverable OVER its residual gate on every fixture with ground or 23.427(a) cases, with a retired cause named as the explanation.**
WHY: verified live — `build_report(ga6_normal)` §6 renders: *"44 case(s)
assembled. The worst pre-closure residual is **143.885 %** of n·W against a
**1 %** gate — OVER the gate; the usual cause is that the assembled model
carries no non-wing drag…"*. Three defects in one sentence: (1) `worst` is
computed over **all** cases, but `balanced_cases.md` §3/§9.4 and the deck's own
`$` headers state `RESIDUAL_GATE` does not apply to the lateral, 23.427(a) or
ground families (a ground case's pre-closure residual is the applied gear load
in full — 100 % by construction); the family the gate applies to sits at
**0.624 %**, comfortably inside. (2) The "no non-wing drag" cause was retired
2026-08-15 when the `body-axial` carrier landed. (3) The GUI page excludes only
`is_unsymmetrical_htail` (`worst_gui` = 100.000 %), so Balanced Cases shows the
same false warning. The controlling document contradicts the deck headers and
the theory doc about the flagship deliverable, in every ga6/RJ report shipped
since 0.6.0. No test pins the sentence — the gate reads the case objects, never
the rendered claim.
FIX: give the exemption predicate one owner in `balance`
(`residual_gate_applies(case)` — the deck headers already encode it three times
as prose), compute `worst` over that family only in both §6 and the GUI, state
the exempt families' standing beside it, delete the stale drag cause, and pin
the rendered sentence for a fixture that assembles ground cases.
CLASS-SWEEP: third site — `_balanced_cases_table`'s note (content.py:1712-1725)
names the rolling and UNSYMMETRICAL exemptions but not the **ground** rows at
100.000 % in the same table; fourth site — `app/views/balanced_cases.py:73-77`
caption still claims ground/fuselage/OEO are "a deliberate exclusion … covered
by the per-component analyses", false both ways since 0.6.0 (ground conditions
assemble; the per-component fuselage view is flight-only permanently per D-28).
One predicate owner fixes all four. Tier M.

**[MAJOR] CR-C-3 `sloads/report/content.py:2088-2091` — the manifest declares `inertia_only.bdf` "ULTIMATE"; the artifact is LIMIT by explicit design.**
WHY: `mass_cards.inertia_only_cards` writes `$ Per-node inertia load at
Nz = …, LIMIT (no SF)` in-band, and its docstring says LIMIT is deliberate
("applying a limit-to-ultimate factor to one side and not the other is the
obvious way to make this check pass while meaning nothing" — the roundtrip M-b
leg compares it unfactored). The controlling document and the file contradict
each other by 1.5×. Mitigated by "comparison only, never applied", but a basis
mislabel in the manifest is exactly the conformance class m14/F-R1 were fixed
for.
FIX: change the basis cell to "LIMIT (no SF) — comparison only, never applied";
add the basis text to the F-D2 manifest test so the cell is pinned, not just
the filename.
CLASS-SWEEP: every other manifest basis cell checked against its writer —
wing/body/tail/control/balanced/gear ULTIMATE claims all match;
`mass_model.bdf`'s "mass, NOT weight" and `mass_check.bdf`'s "no load cards"
are correct. Only this one lies. Tier S.

### Pass D — main GUI & CI

**[MAJOR] CR-D-1 `app_shell/sidebar.py:103-109` (+ `app_shell/project_state.py:117-123`) — the Upload project.json path re-loads and re-adopts on every rerun, ending in an unbounded `st.rerun()` loop; on a dirty project, Cancel in the discard dialog can never dismiss it.**
WHY: `st.file_uploader` returns the file on **every** script run while it sits
in the widget, and the handler is not edge-triggered: `if uploaded is not None:
safe_load(...); load_with_guard(...)`. `load_with_guard`'s clean path is
`adopt(new) → st.rerun()`, so run N+1 sees the same file, adopts again, and
reruns again — verified with a Streamlit probe (AppTest followed 99 consecutive
`st.rerun()`s with no cap). The dirty path is worse: `confirm_discard` reopens
each run, and its Cancel button is itself `st.rerun()`, which lands back in the
same branch — the dialog is inescapable until the user clears the uploader.
Open/Load-example are safe only because they are gated on `st.button` (true for
one run).
FIX: make the upload edge-triggered — store the processed upload identity
(`uploaded.file_id` or name+size) in session state, skip when it matches,
record it before `load_with_guard`.
CLASS-SWEEP: `oracle_app/Oracle.py:61` calls the same `render_shell_sidebar`,
so **both GUIs** carry it. Pre-dates the OG-B extraction (same code in old
`app/Home.py`) — a shipped defect on a promised feature (`GUI_design.md` §4,
`GUI_USER_GUIDE` §2), not an in-flight regression. Tier M.

**[MAJOR] CR-D-2 `app/views/flap_loads.py:57-80` (class) — hand-paired `to_display`/`to_imperial_scalar` around `number_input` survives in ~7 views; in SI, an Apply with nothing typed silently rewrites stored Imperial values and trips the dirty flag.**
WHY: `GUI_design.md` §7 states verbatim "A view that writes
`to_imperial_scalar` around a `number_input` is a defect" (the
`unit_number_input` untouched-field passthrough exists precisely for this).
Proven end-to-end via AppTest: load ga6_normal in SI, press flap-loads Apply
with zero edits → `flap_area_one_side_sqft` 10.7 → 10.700403345251134 and
`project_to_dict` ≠ snapshot (spurious "Unsaved changes"; violates §10
"loading … converts exactly once" and the lossless load→edit→save promise).
Drift compounds on every Apply. `tests/test_view_unit_roundtrip.py` pins only
`configuration_layout.py` for `app/` — none of the hand-paired views are
covered.
FIX: convert the remaining scalar sites to `unit_number_input`; for
`st.data_editor` grids, write back the caller's original value when the
converted-back cell is within display rounding of it. Extend
`test_view_unit_roundtrip` with a no-op-Apply-in-SI case per converted view
(the `test_apply_without_edits_leaves_values_bit_identical` shape).
CLASS-SWEEP: scalar sites — flap_loads (3 fields), aileron_loads:70-71 (2),
landing_loads:147-149 (3), flight_envelope:175-176,333, structural_speeds:354-356,
weight_mass:130-180 (+ grid helpers :263/:341), wing_loads:306-307. Grid sites
(fuselage_loads:111, tab_loads:79-86, wing_loads:115/287-290,
configuration_layout LE/TE table) share the shape at ulp-to-4-decimal
magnitude. `GUI_design.md` §11's claim that the §7 pattern is rolled out
"across all definition pages" over-claims. Tier M.

---

## 2. Findings — MINOR

**[MINOR] CR-A-3 `oracle_app/form.py:227` (`_persist`) — an Optional field can never be set to its falsy value.**
WHY: `if current == value or (current is None and not value): return` — a
`None`-valued `Optional[float]` renders as `0.0`, and a deliberate `0` is
indistinguishable from the seed, so `0` never persists (same for `False` into
`Optional[bool]`).
FIX: document the limitation in the field help, or render Optional scalars with
a set/unset affordance where zero is meaningful. Parked-with-number if no
ORIGINAL Optional field has a physically meaningful zero. Tier S.

**[MINOR] CR-A-4 `oracle_app/form.py:653` via `app_shell/components.py:139` — the oracle GUI exposes the "Switch to Concept" action.**
WHY: `render_step` calls `page_header` with `banner=True` (default), so an
out-of-band airplane shows the applicability banner **with the
Switch-to-Concept button**, which writes `speeds.category="C"` and seeds
`chosen_n/chosen_nneg` — concept mode is explicitly out of this GUI's scope
(OG-1). No `banner=False` anywhere in `oracle_app/`.
FIX: pass `banner=False` from `render_step` (or a shell flag rendering the
warning without the switch action). Tier S.

**[MINOR] CR-A-5 / CR-D-10 `app_shell/components.py:66-73` — `workflow_page_link` swallows all exceptions from `st.page_link` with a bare `except Exception: pass`.** *(Found independently by both passes.)*
WHY: the intended fallback (unregistered step / bare AppTest) is already
handled by `page_for` returning `None`; the try/except additionally hides
genuine `st.page_link` failures (bad page object, Streamlit API change) as
silent text degradation — a broken nav would ship green. In-flight OG-F code.
FIX: narrow to `StreamlitAPIException`, or drop the try/except entirely.
Tier S.

**[MINOR] CR-A-6 `oracle_app/form.py:433-437` (`render_curve`) — a partially-filled table row is silently dropped.**
WHY: `if not any(pd.isna(v) for v in values)` discards any row with one empty
cell on the persist path — a user adding a polyline corner and filling only X
sees the row vanish with no message (and reappear empty on rerun, which reads
as flakiness).
FIX: hold the row un-persisted with an `st.caption` noting incomplete rows are
not saved. Tier S.

**[MINOR] CR-B-4 `sloads/modules/select.py:257-258` — silent `nx = 0.0` when a V-n point's CG name has no matching weight case.**
WHY: `w = weights.get(p.cg, 0.0); nx = (-p.dx/w) if w else 0.0` — a persisted
`Project.envelope` whose CG-case names no longer match the current `weight`
slice yields a zero inertia-drag factor fed into WINGINER with nothing on the
page to show it. Same silent-skip in `select_htail_balancing:379-381`
(`continue` on an unmatched CG drops candidates from the 23.421 search).
FIX: raise (or emit an in-band note) on a CG name present in the envelope but
absent from `flight_cases(project)` — a mismatch is a stale-persistence defect,
not a zero. Tier M.

**[MINOR] CR-B-5 `tests/test_flight_envelope.py:55-56,72,98` — several Appendix-A oracle assertions are looser than the stated ±0.1 % with no in-line reason.**
WHY: `di.mc`/`di.md` at `rel_tol=2e-3`, the V-n sweep at `2e-3`, STALL 1G speed
at `5e-3`. Likely legitimate (3-significant-figure print quantizes at ~0.16 %;
the balance converges to ±0.005 in nz) — but the contract is `1e-3`, and an
unstated widened tolerance is where a 0.3 % drift would hide.
FIX: add a one-line reason beside each widened tolerance (print granularity /
convergence band), per the "printed figure + page citation next to each
assertion" rule. Tier S.

**[MINOR] CR-C-4 `sloads/export/mass_cards.py:316` (`massset_identity`) — two payload cases can mint one MASSSET LABEL.**
WHY: verified — "Max take-off forward CG" / "Max take-off aft CG" both label
`MAXTAKEO` (8-alnum truncation). SIDs stay unique so the solver is unaffected,
but the deck comment block, report mass-case table and any label-reading
consumer see two cases under one name.
FIX: disambiguate on collision (suffix a digit) or raise; one-line uniqueness
check + test. Tier S.

**[MINOR] CR-D-3 `sloads/workflow.py:108,155,164,187,190` — `requires` conflates upstream slices with the page's own input slice, so the Dashboard brands self-sufficient pages "⛔ blocked (open an upstream page first)".**
WHY: on a fresh project `weight_mass` (requires `weight` — entered on that very
page), `engine_mount` (`engines` — its own form), `tail_loads`/`tail_span_loads`
(`tail_loads` — entered on Geometry) and `one_engine_out` (`vtail_loads`) show
blocked with "open an upstream page first". None of those slices appears in any
step's `produces`, so `components._PRODUCER` has no target and the gate
degrades to a bare slice name with no link; the "Steps blocked" metric counts
them too.
FIX: split the concept (a `WorkflowStep.edits` field for self-owned slices, or
drop self-requirements), and add a `test_workflow.py` assertion that every
`requires` entry is some step's `produces` or declared self-entered — the
DAG-completeness guard that would have caught this.
CLASS-SWEEP: the four sites above; remaining `requires` entries resolve to
producers correctly. Tier M.

**[MINOR] CR-D-4 `docs/10_standard/00_program_overview.md:272-286`, `CLAUDE.md:102`, `DEVELOPMENT_PROCESS.md` §2 — three documents state the pre-2026-08-17 CI gate; §2 contradicts its own §0 table.**
WHY: `ci.yml` runs the 3.9/3.11 legs **only on push to main** (PR → 3.12
only); a PR that breaks 3.9 merges green by design. The overview says "CI runs
ruff + pytest on Python 3.9 / 3.11 / 3.12" with no asymmetry caveat;
`DEVELOPMENT_PROCESS.md` §2 still lists required checks `test (3.9)`,
`test (3.11)`, `sbeam-roundtrip (3.11)` — checks that do not exist on a PR —
while §0's table and ci.yml's own comment say the required set is
`test (3.12)`, `typecheck`, `sbeam-roundtrip (3.12)`. The asymmetric-gate class
applied to CI itself.
FIX: make ci.yml the stated authority (the lint-gate guard in
`test_app_shell.py` already does this for the ruff command — extend the
posture); correct §2's list; add the PR/main split sentence to the overview and
`CLAUDE.md`.
CLASS-SWEEP: `README.md:84` carries the same unqualified claim. Tier S.

**[MINOR] CR-D-5 `docs/10_standard/00_program_overview.md` §Dependency requirements — copies pyproject values and has drifted.**
WHY: `streamlit>=1.30` vs pyproject's `>=1.36` (a floor that exists because of
`st.navigation(expanded=...)`); the dev-extras list omits mypy, pre-commit,
radon and the ruff pin. Violates "standard docs point at owners, never copy
their values"; `test_doc_currency.py`'s VOLATILE patterns have no case for
version specifiers, so the class is invisible to the guard.
FIX: replace the copied lists with a pointer to `pyproject.toml`, or add a
`>=N.N` volatile pattern scoped to dependency names. Only live instance in
`10_standard/`. Tier S.

**[MINOR] CR-D-6 `docs/10_standard/00_program_overview.md:304-311` — the suite-runtime standard's own revisit clause has tripped and nothing is filed.**
WHY: the section claims "the suite in the tens of seconds and no test over
ten" with revisit triggers "~30 s single test or ~2 min parallel suite".
Measured: 269 s parallel (671 s serial), slowest test 62.3 s
(`test_case_ids::test_the_index_row_states_the_condition_its_cards_were_computed_at`),
15 tests over 16 s. `.pre-commit-config.yaml` already records the drift and
names the fix, but the standard doc still states the stale claim and no
backlog/issue row exists — the tripped threshold has no owner. The 62 s test is
the parallel critical-path floor.
FIX: file the split (test_case_ids + the four ~20-37 s deliverable-units/
balance tests share one shape: whole-pipeline re-runs per assertion); update
§Testing to point at `--durations` output instead of prose numbers. Tier S.

**[MINOR] CR-D-7 `docs/10_standard/GUI_USER_GUIDE.md:70-80` — the phase table promises a navigation the app doesn't have.**
WHY: it lists Aircraft Comparison under **Load-case plotting**, but
`workflow.py` puts it in **Export** (GUI_design §8.4 agrees with the code); and
the Flight-loads row omits **Tail Span Loads** and **Balanced Cases** — the two
pages carrying the mission's primary deliverable views. No guard derives this
table from `workflow.py`.
FIX: correct the table; optionally add a doc-currency-style check that every
`wf.STEPS` title appears in the guide under its phase. Tier S.

**[MINOR] CR-D-8 `tests/test_page_links.py:42-48` — the nav drift guard is one-directional: an orphan view file is invisible.**
WHY: `test_every_workflow_key_has_a_view_file` checks key→file only. A stray
`app/views/foo.py` never enters nav, still passes `test_views_smoke` (it globs
`views/*.py`), and no guard fails — a page can exist, be smoke-tested, and be
unreachable forever. No orphan exists today (stems == BY_KEY exactly) —
guard-shape, not a live defect.
FIX: one added assertion: `{view stems} == set(wf.BY_KEY)`.
CLASS-SWEEP: the other guards checked cut both ways (`test_spec_coverage`,
`test_workflow`, `test_doc_currency`) — this is the only one-way guard found.
Tier S.

---

## 3. Findings — NIT

- **[NIT] CR-A-7** `oracle_app/results.py:88-90` — `_LIMIT_NOTE` claims the
  basis travels "in its `Basis` column"; the tail chordwise table carries the
  marker in headers instead. Wording only.
- **[NIT] CR-A-8** `tests/test_oracle_gui.py:322-336` — the
  one-download-call-site scan covers only `oracle_app/*.py`;
  `app_shell/sidebar.py` renders a `st.download_button` inside the oracle GUI
  too (harmless today — project.json, not a load deliverable — but a future
  shell-side load artifact would evade G7's completeness argument). Also the
  CSV-stamp test at :355 accepts the ULTIMATE stamp anywhere in the payload
  rather than in the comment block.
- **[NIT] CR-A-9** `oracle_app/Oracle.py:57` — `_page` recomputes
  `wf.oracle_steps()[0]` per page (14×); hoist it.
- **[NIT] CR-B-6** `sloads/safety_factors.py:384-387` — `stamp()` silently
  skips an item without a `safety_factor` attribute (`hasattr` gate); record
  skips the way `defaulted` records unclassifiable cases.
- **[NIT] CR-C-5** `tests/test_export_equilibrium.py:333-338` — comment says
  the body deck's zero-lateral assertion "goes red the day the ground cases
  land"; they landed (0.6.0) in the assembled deck and D-28 made the
  per-component body deck flight-only permanently. Update to cite D-28.
- **[NIT] CR-C-6** `tests/test_ultimate_contract.py:43` — `export_report.py`
  is exempted wholesale from the CSV-basis scan on a comment's claim; narrow
  the skip to the current artifact names.
- **[NIT] CR-D-9** `app_shell/sidebar.py:120-124` — Download writes
  `{name}.json` while Save/Open use `.project.json`, so a downloaded file
  dropped into `projects/` is not listed by Open. Fix:
  `file_name=f"{fname}.project.json"`.
- **[NIT] CR-D-11** `cspell.json` exists but nothing runs it — no CI step, no
  pre-commit hook. "New domain terms → cspell.json" is a prose rule with no
  gate: the exact shape rule 3 forbids.

Also noted (stale parked entry, not a finding): `02_parked.md` **L-8a**
("G6/G6b sections hardcode ft²/in labels and ignore the SI toggle") is stale —
those forms now go through `unit_number_input`
(`configuration_layout.py:510` via `_u`) and `test_view_unit_roundtrip` proves
both directions; close as shipped.

---

## 4. Cross-pass classes (the structural findings)

Rule 3 ("make it structural") applied to what all four passes found
independently:

1. **Gates must read the shipped artifact, both ways.** The four worst guard
   blind spots share one shape: the gate checks a *proxy* of the deliverable —
   a substring grep instead of the AST (CR-B-1), rows-added instead of
   zip↔manifest set equality (CR-C-1), case objects instead of the rendered
   sentence (CR-C-2), key→file without file→key (CR-D-8), a scan scoped to one
   package (CR-A-8). Each was correct when written and rotted when the code
   grew past the assumed shape. The fix in every case is the same move:
   assert the artifact the user receives (AST, `namelist()`, rendered text,
   set equality in both directions).
2. **One-owner rules need a render-time consumer, not just a registry.** The
   field registry records ownership but nothing reads it at the widget
   (CR-A-2); the residual-gate exemption predicate exists as prose in three
   deck headers but has no code owner (CR-C-2); `workflow.requires` has no
   producer-completeness check (CR-D-3). In each case the SSOT exists — the
   missing half is the single consumer + drift guard.
3. **Non-edge-triggered / silently-swallowing handlers.** The upload loop
   (CR-D-1), the pending-record clobber (CR-A-1), the bare `except Exception`
   (CR-A-5/D-10), the `.get(…, 0.0)` CG fallback (CR-B-4), the `hasattr` skip
   (CR-B-6), the dropped curve row (CR-A-6): every one converts an abnormal
   state into silence. The error contract (`00_program_overview.md`) already
   forbids this shape in calc; the GUI/shell layer needs the same posture.
4. **Docs drifting from the artifact they describe** (CR-C-2 caption, CR-C-3
   basis cell, CR-D-4 CI matrix, CR-D-5 version floors, CR-D-6 runtime claim,
   CR-D-7 phase table): six instances across three passes. Where a guard
   pattern is cheap (version specifiers, phase-table derivation, manifest basis
   text) add it; otherwise replace the copied value with a pointer.

---

## 5. Prior-findings audit (2026-08-10 review)

Every 08-10 CRITICAL/MAJOR closure was re-verified against today's tree:

- **C1 (SI GRAV 25.4×): fix real.** `units.DeliverableUnits.gravity` is the
  single owner; the roundtrip leg solves the mass family in both systems and
  `test_the_c1_defect_would_have_failed_this_leg` rebuilds the exact defect and
  proves rejection.
- **F-C1/F-G3 (GID bands): real** — `export/bands.py` registry +
  exhaustiveness sweep (an un-registered base constant in `sloads/export`
  fails), subcase cross-pins, capacity-raising allocators.
- **F-C2/D-R5, F-C3/D-R4, F-C4, F-C5/6/7: real** (per-axis assertions, shared
  tributary helper raises, property-gate skip records).
- **F-D1/F-D3: real** — all ten CLI targets headless, stamped, one error
  contract. **F-D2: real for the 0.5.0 set — ROT FOUND:** the identical class
  re-opened for the 0.6.0 LRA deliverable (CR-C-1), because the closure was
  rows-added, not a bundle↔manifest gate.
- **F-G1: real** — six-DOF card-text closure, both systems, calibrated teeth
  test. **F-G2: real** — mass family solved per-case; sbeam's MASSSET gap
  pinned by a test designed to fail when sbeam fixes it.
- **F-R1…F-R5, D-R8: real** — per-case SF in every governing row, section
  numbering owner with resolve-tests, disclaimer leads the methods statement,
  limitations key set pinned and re-worded for the ground family.
- **Pinned exceptions (0.5.0/0.6.0 §3): no silent drift.** All pins pass —
  pitch ratchet under the 2.5 % stops, unsymmetrical split ≤0.08 %, D-29/D-30
  exceedance pins, wing-tie gate. The single xfail is the recorded RJ-SI LRA
  sbeam condition-heuristic limitation, pinned strict exactly as baseline
  0.6.0 states.

---

## 6. Backlog — already-filed items ranked critical / high-leverage

Not re-reported as findings; ranked here per rule 6 (first-order effect on
shipped content first). Items flagged by two passes independently are marked ×2.

| Rank | Item (where filed) | Why it outranks its band |
|---|---|---|
| 1 | **Three gear fields the GUI cannot reach** (`carrier`/`attach`/`weight_lb`; #29 review / note 32 §8) ×2 (A, D) | First-order defect in shipped export content: a GUI-built project exports a ground model with zero gear nodes. Outranks everything placement-related. |
| 2 | **#33 `_balance` has no failure channel** ×2 (B, C) | Both iteration loops (`flight_envelope.py:151/167`) return their last iterate on exhaustion with no signal; every V-n point, SELECT pick and balanced case downstream consumes it — a masked-defect risk with first-order reach on concept inputs. Band C under-ranks its blast radius. |
| 3 | **#31 ground-family fuselage per-station view** (C) | Ground loads exist only in the assembled deck; a frame-sizing consumer has no per-station ground shear/bending — half the sizing loop's fuselage story. |
| 4 | **`speeds.wing_area_sqft` dead input** (#29 review) ×2 (A, D) | An input the analysis ignores (18 % silent divergence measured on atr42); also one of CR-A-2's four editable wing-area copies, so fixing it shrinks that finding. Cheapest wrong-belief fix on the list. |
| 5 | **#32 Mach-capped points published with CM/CD extrapolated past the stall fit** ×2 (B, C) | Measured 3.3–44 % moves on the published tail split for 9 rows; 0 SELECTed today is fixture-dependent and the honesty marker is cheap. |
| 6 | **D-5 Appendix B twin fixture blocked** (B) | Standing consequence: the entire twin/turboprop family (ONENGOUT, 23.361(a)(3), (b)(1)) has no printed oracle — CR-B-3 is a direct symptom. |
| 7 | **Certification basis / case manifest (tier L)** (D) | Highest-leverage structural item before the second FAR 25 case lands; the coverage matrix is already blind to the three conditions the current flag adds. |
| 8 | **`scripts/smoke_test.sh` into CI** (review m20; D) | A dropped thread — history calls it "the stated gap" but no backlog row or issue carries it; the release-gate script is exercised only at release cut. |
| 9 | **L-8d widget freshness (`key=`+`value=`)** (D) | The one parked UX row that is a correctness-hazard class (stale widget after programmatic load); interacts with CR-D-2's fix — do together. |
| 10 | **L-8c Results Review omits the 8 folded modules' results** (D) | The consolidation page's own summary promises "every component"; display gap on a deliverable-adjacent page. |
| 11 | **GUI review #29 resumption** (A) | The field registry (OG-C/OG-14) now exists to turn its nine unswept pages into a test report — the sweep got cheaper. |
| 12 | **#19 mypy stage-2 ratchet over `sloads/export/`** (C) | The layer this review's MAJORs live beside; next-cheapest place to make defects structural. |
| — | **#14 aileron lift increment** (C) | Correctly gated on a sizing consumer (D-29); no change. |
| — | **Parked without the number (rule 6 lapses):** M4-4 (per-CG precise inertia in SELECT) and M4-3 legs (a)/(c) carry no stated effect magnitude; M4-21 is parked on a real dependency but states no estimate against the 5–10 % band. L-3 (rudder EFV) is correctly parked *with* its number (−47 % vs the 591-lb oracle). **L-8a is stale — close as shipped** (§3 note). | |
| — | **Parked `concept_heavy` gear fixture** (B) | The FAR 23.473(g) N ≥ 2.67 floor warning has never fired on any shipped fixture — an untested warn path in a delivered-load check; cheap Tier-S data. |

---

## 7. Coverage

- **Pass A** deep-read all of `oracle_app/` and `app_shell/`, verified every
  OG decision/gate: **satisfied and verified** — OG-1/G1, OG-2/G2, OG-3/G3,
  OG-5+14/G4, G5, OG-6 (as amended), G6/OG-13, G7 (with CR-A-8 caveats),
  G8+OG-10, OG-11, OG-12, OG-4/OG-B; **not satisfied** — OG-8 (CR-A-2) and the
  marking half of OG-7. The guard tests test real artifacts (payload bytes,
  AppTest session state, CLI byte-equality); the one hole is
  multi-edit-per-rerun behavior — exactly where CR-A-1 lives.
- **Pass B** deep-read `flight_envelope`, `select` (whole), `engine`,
  `airloads`, `safety_factors`, `constants`, `registry`, `report/render` (ULT
  boundary), `units` (boundary), targeted slices of `balance`/`body_loads`/
  `wing_inertia`; swept all of `sloads/` for owned-literal leaks, keyed picks,
  silent fallbacks, `int()` truncations. SSOT rows verified with teeth:
  platform-pick (hole found — CR-B-1), constants, SI-factor, envelope,
  safety-factor reproduction, case-id/deck-number, workflow nav, fsum. Not
  deep-read: `landing`, `tail_span`, `taildist`, `one_engine_out`,
  `structural_speeds`, most of `balance`, `io`, `models/` (swept only);
  equation verification was against the citations carried in code/tests, not
  fresh PDF page reads.
- **Pass C** traced five paths end-to-end (balanced deck, wing headless, mass
  family, LRA deck, report/bundle) — ULT applied exactly once on all;
  re-audited every 08-10 closure (§5); checked every manifest row against its
  writer and every 0.5.0/0.6.0 pinned exception.
- **Pass D** inspected `app/Home.py`, all of `app_shell/`, `workflow.py`, four
  views in full + the rest by targeted greps, both workflows, `pyproject.toml`,
  `conftest.py`, the doc drift guards, `scripts/`; ran live probes for CR-D-1
  and CR-D-2. CI coverage floor (`--cov=sloads` only — the three GUI packages
  and `cli.py` sit outside the 80 % floor) noted as deliberate per the
  overview's ratchet text; the ratchet note predates the two GUI packages and
  could name them when next touched.
