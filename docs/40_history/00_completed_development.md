# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

**Live cycle only.** This file holds the current release cycle plus the previous
release cut. Older blocks roll into frozen, do-not-edit archives at each release
(`RELEASE_PROCESS.md` §4): the 0.7.0 cycle and the 0.7.0 cut are in
[`37_completed_development_to_0.7.1.md`](37_completed_development_to_0.7.1.md),
the 0.6.0 cycle and the 0.5.0 cut in
[`35_completed_development_to_0.6.0.md`](35_completed_development_to_0.6.0.md),
everything before 0.5.0 in
[`11_completed_development_to_0.5.0.md`](11_completed_development_to_0.5.0.md).
Tier S closures do not write here (a `changes/` fragment is their record); tier M
writes one paragraph, tier L the full step format — **as a `changes/<slug>.history.md`
fragment** (design note 28 MD-4), rolled to the top of this file at release cut, so
concurrent PRs never edit the same line here. Only the release-cut block itself is
written directly, by the release manager.

---

- **The stall fill gets a second caller, and the balance gets a refusal (issue
  #81, C210-23, tier M, 2026-08-24)** — The M1-1b fill that keeps the CLmax trio
  and the per-config stall CLs consistent was written into `__post_init__`, which
  is the right place for a slice that is built in one go and no place at all for
  one that is assembled field by field. The oracle GUI does the latter: it seeds
  the coefficient sets blank and writes the CLmax trio afterwards, a widget per
  rerun, so the constructor never ran a second time, the live sets kept a stall CL
  of zero, and both Flight Envelope and SELECT died on a division by it. The
  workaround that kept the C210 build moving — save, reload — is the tell: the
  loader constructs, so the file was always right and only the session was wrong.
  The fix needed no new call site. `sloads.derived` already existed for the
  neighbouring problem (a derived slice whose only writer was one GUI, #62/PB-1)
  and the oracle form already calls `refresh_derived` after every persist, so the
  fill was extracted to `AeroCoefficientsInput.normalize` and registered there;
  what the module gained was a second table, because a *derived* slice and a
  *normalized* one are not the same thing — the first is a result the project
  could rebuild from scratch and the field registry excludes from the input set,
  the second is authored input whose fields fill each other in, and letting
  `aero_coeffs` into the first would have put user input under the G5 reduction's
  drop-and-re-derive. Beside the fill, the balance now refuses: `balance_configs`,
  the choke point `build_envelope` and `trim_sweep` share, names the set, the
  quantity and the page rather than letting a stall speed divide by zero — the
  #84 lesson, that a condition the airplane has not stated is refused rather than
  computed, applied one layer down. The sweep item that came with the issue could
  not be closed as it was written. `flaps_down.neg_stall_cl` is not a fill that
  was forgotten; it has no source to fill from, since the schema carries no
  `clmax_flap_neg` and the clean negative CLmax is a different number — Appendix
  A's landing set prints −0.41 against a clean −0.59, so the obvious fill would
  have injected a 44 % error into the flaps-extended negative band. Left at zero
  it does not crash but clamps that band at CL = 0, which the balance reports as
  a quietly small load, so it is now a validation warning and the schema field
  that would let it fill symmetrically is filed as its own item.

**One consistency-warning renderer for both GUIs (issue #82, C210-35, tier M,
2026-08-24).** The finding was that the oracle GUI renders no part of the
`consistency_warnings` channel; the cause turned out to be one layer down. The
`page` tag each warning carries was never checked against anything, and two tags
had gone stale — `weight_cg_inertia`, left behind when the weights page became
`weight_mass` at Step G3, and `wing_geometry`, left behind when Step G1 merged
that page into `configuration_layout`. Between them they carried 19 of the
module's checks, 14 in the weights group alone, and they kept working in `app/`
only because two views compared against the old strings by hand. So the channel
was not merely unrendered in the second GUI: its largest group was propped up by
a literal in one file and was dark everywhere else, which is why a contradictory
`wing_fraction` entry could survive an entire build review unshown and cost three
round-trips to diagnose from the saved file. Both halves were fixed at the level
that makes them structural rather than patched. Every tag is now a
`sloads.workflow.STEPS` key — `workflow.py` is the nav SSOT, so a tag naming
anything else names a page no GUI has — with a rule-3 guard over both the
`PAGE_*` constants and the tags the live checks emit. And the rendering has one
owner, `app_shell.components.render_consistency_warnings`, called by
`page_header` from the step key it already holds: the same place, and for the
same reason, as the applicability banner. That choice is what makes the fix
cover all fourteen oracle pages and every main-GUI view at once instead of
page by page, and it removed the six open-coded loops rather than adding a
seventh; `aero_coefficients.py` and `export_report.py` were migrated onto
`page_header` with `banner=False` so nothing but the warnings changed on them.
Warnings tagged `export_report` were deliberately left main-GUI-only by owner
call: the oracle GUI has no export page and no way to set a safety-factor
override, so a warning about one concerns state it can neither create nor act on,
and the guard permits a tag that is a workflow key without being an oracle step.
Verified on the C210 build file: all six of the warnings the owner saw in the
main GUI now render on the oracle GUI, on the pages that own them.

**Flap slipstream applied to the deliverable (issue #85, C210-47/C210-40 family,
tier M, 2026-08-24).** The C210 build review reached the flap page with an engine
record present for the first time in the project's history — no prior fixture
carried both a flap slice and an engine — and the FAR 23.457(b) block finally
computed. It computed, printed, and was then discarded: `build_flap` exported
`max(critical, gust-combined)` as the single flap case, so the deck shipped 972.8
lbs-ULT against a slipstream design load of 1,156.6, understating shipped content
by 19 %. The fix delivers the slipstream as a second case beside the
gust-combined one rather than folding it in, on two owner rulings taken in chat
before code (rule 1): the two are **independent** worst cases and are enveloped,
never stacked; and the factored load is stated over the whole flap because
`ControlSurfaceLoadResult` has no spanwise dimension — the review's preferred
per-strip banded envelope would be an L-tier schema change, and inventing the
flap's span extent from a project that leaves `inboard_y_in`/`outboard_y_in`
unset would violate T-17. One implementation rule was settled on the physics
rather than by owner call: the factor is `(Vss/VF)²`, so it scales the VF-governed
condition, not the stall-speed ones — a distinction with no numeric effect on the
manual's airplane (whose critical condition is 2G at VF) and a real one on any
airplane where a stall-speed condition governs. Closing the item exposed a second
defect in the same file: the main GUI's slipstream block tested a display label
against a key-keyed dict and so had never rendered at all, which is why C210-47
was verified through the oracle GUI's report path. It was folded in under rule 4,
and since a sweep found it to be the only instance in `app/views`, its drift
guard is stated as an absolute. No printed oracle exists for an applied
slipstream load — Appendix A prints the factor and the gust-combined 819 lb and
nothing built from the two together — so the definition of done is the stated
closure gate rule 2 requires in place of one: `factor × max(LF 2G-at-VF, LF
gust-at-VF)`, not the factors stacked, with an engine-less project exporting
byte-identically to before. The frozen Imperial digests moved on the flap
channels of the propeller examples, which is the intended change announcing
itself, and were regenerated.

- **The load boundary types its own numbers (issue #76, C210-7 residual, tier M,
  2026-08-24)** — The reported defect was narrow: a project saved while the
  oracle GUI's geometry grid was handing text back kept its wing corners as
  strings, and reloading it re-crashed WINGGEOM with `TypeError: unsupported
  operand type(s) for -: 'str' and 'str'`. The review's mitigation — the repaired
  grid fixes the corners on the next Geometry render — turned out to hold only in
  the GUI the defect was found in: in the main GUI the same strings kill
  `to_display` on the Configuration & Layout page, which is the page that would
  have done the repairing, so the file was unopenable there in a way nothing had
  noticed. That made the loader the only boundary worth fixing, since the module,
  both front-ends and the CLI all sit behind it. Reading the model's own
  annotations for the class rather than the field then showed how thin the
  existing coverage was: of eighteen numeric containers in the schema, exactly one
  — `FlightLoadsInput.altitudes_ft` — coerced its members, and the rest, including
  three `hinges_span_in` lists that feed the sbeam control-surface export and both
  engine CG vectors, took whatever JSON held. So the rule is now stated once and
  derived: `io._numeric_shape` reads the shape off the dataclass hint, `_filtered`
  applies it to every splat, and the three readers that name their fields
  explicitly call the same coercer instead of keeping a second copy that could
  drift. Text that parses is repaired out loud through the load path's existing
  warning channel (one message per field, not per member — a twenty-point polyline
  is one event), which keeps a crash-damaged file openable so the grid can finish
  the repair; text that does not parse raises `ValueError` naming the field and the
  member, which the GUI already renders as `st.error` rather than a traceback.
  Scalars were left out deliberately: the class that produces this damage is the
  grid-writable container, and a blanket numeric coercion would have to reason
  about `Optional`, enums and bools for no observed defect. The guard is the whole
  fixture rather than the one field — the GA-6 project reloaded with every list
  member written as text must return bit-identical values from seventeen modules.

- **A 23.367 applicability gate, single-sourced across the module, both GUIs and
  the coverage table (issue #84, C210-43, tier M, 2026-08-24)** — The finding was
  a false verdict: on the C210's centreline single, One Engine Out printed zero
  tail load and zero yaw rate at all three speeds while stating the airplane was
  uncontrollable and likely below VMC. The arithmetic was never wrong. FAR
  23.367's forcing is `thrust · BLENG`, and with the only engine at BL 0 that
  product is identically zero, so the simulation marched sixty seconds of nothing
  and then reported — correctly, on its own terms — that recovery never happened.
  Every intermediate around it verified to the digit, which is precisely why the
  result was believable. What was missing was the question that comes before the
  simulation: does this airplane have the condition at all. The predicate turned
  out to exist already, in `report/coverage.py`, whose 23.367 row has always
  marked the C210 not-applicable — so the tool held the right answer in one place
  and acted on the wrong one in three others. The fix was therefore consolidation
  rather than a new rule: `applicability.engine_failure_not_applicable` states it
  once, and the module's refusal, the oracle GUI's withheld form and the coverage
  row are readers of it. Coverage's old test was also weaker than the physics —
  `len(engines) > 1` calls a twin applicable even when the *failed* engine is the
  centreline one, which is the same zero moment arm — so the shared predicate
  covers a case none of the three had. Coverage keeps its own turbopropeller
  clause layered on top, deliberately: 23.367(a)'s regulatory scope is a
  statement about which airplanes must show the condition, while the module
  models any propeller installation, and `PROPELLER_ONLY_NOTE` already records
  that split. Two boundaries were drawn rather than blurred. An empty engine list
  is *not* an applicability finding — it is an unfinished project, and the
  module's existing "needs Project.engines" refusal says so better — so the
  predicate stays silent there unless the layout settles it. And the GUI table
  keying pages to predicates lives in `sloads`, not the front-end: the oracle
  GUI's own drift guard rejected the first attempt for writing a workflow step
  key as a literal (OG-2/G2), and the key set is guarded against the #82 stale-tag
  defect in the same move.

- **A row counter that deleted, and a row that stopped the calc (code review
  2026-08-24, tier M)** — The 0.7.2 code review of `oracle_app/` and `app_shell/`
  found the shell in good order and two live defects, both inside eight lines of
  one function. `render_table` sized a list record by reconciling the model to a
  number input, against the project's own attached list, so the widget wrote to
  the project in both directions during a render pass. Counting down popped
  entered rows — 21 of 24 weight items on one keystroke, no confirmation, no undo,
  blanks on the way back up, and a truncated project that saved — which is the
  same failure the generation stamp was built for at #51, closed there for the
  path where Streamlit's retained state caused it and left open for the path where
  the user does. The same pop also fired on a plain page revisit whenever the
  project had been mutated rather than replaced underneath the retained count, the
  case `02_parked.md` L-8d parks and #78's seed button was about to trigger.
  Counting up was the more surprising half: the seeded row joins the project
  immediately, because `commit_pending`'s blank-record rule governs records a pass
  creates and not rows appended to a list that is already attached — and for the
  CG-case table that row is a `FLIGHT`-tagged case of zero weight, which every
  balance divides by, so asking for one more row killed the entire flight envelope
  and SELECT. What made that invisible was a third thing: the results renderer
  caught `ZeroDivisionError` as *not ready yet*, so a page that had been working a
  second earlier said only that it was unfinished. The fix keeps the counter (it
  is what the journey test types projects through) but makes it non-destructive —
  the model wins, and a deletion is a named button that says which rows go — and
  puts the refusal where it belongs for every writer rather than for the GUI that
  happened to produce it: `build_envelope` names a weightless case, `validation`
  warns before anything runs, and `ZeroDivisionError` is out of the not-ready
  catch, which is the narrow half of #71. The page's caption, which had promised
  that incomplete rows are not saved, now states the rule that actually applies to
  each kind of row.

- **Whole-project results zip in the shared sidebar (C210-45 / backlog 19c,
  tier M, 2026-08-23)** — The C210 oracle-GUI build review left the owner
  collecting thirteen pages of results one hand-clicked download at a time;
  no control delivered a complete results set. The shared sidebar now builds
  one zip per project: every registered module run in registration order,
  each contributing the CLI's own text report and load-case CSV (same owners:
  `module_text_report`, `io.load_cases_csv` + `csv_comment_block`, results
  stamped from the governing safety-factor table exactly as
  `registry.run_all_modules` does), plus the serialized project and a
  `MANIFEST.txt` naming every module's outcome — skip-and-manifest per the
  error contract (`MissingInputError` = skipped, `ValueError` = failed and
  said so; anything else propagates, M2R-8). The builder
  (`sloads/report/results_zip.py`) is pure and clock-free, so two builds of
  one project are byte-identical; `tests/test_results_zip.py` asserts on the
  zip bytes (manifest completeness, member pairing, ULT header, basis
  statement, project round-trip, determinism), and the oracle GUI's G7
  call-site gate was extended to admit the zip by its naming owner with the
  payload gate stated in place.

## Release cut: **sloads 0.7.2** (the bugs the build review found, and the review that found two more), tag `v0.7.2`, 2026-08-25

**Objective.** Ship the seven `b`-class defects the 0.7.1 Cessna 210 build
review classified as *bug → 0.7.2*, then — at the owner's direction, with the
cut already started and walked back — **review the oracle GUI's code** before
closing, and re-cut the table for the two GUI milestones that follow. The
milestone is therefore defect-only by construction: no new capability, no calc
math changed on the FAR 23 path, no schema hop.

**Deliverables** (the `[0.7.2]` changelog section is the release note):
- **The seven carried defects**, each closed with its own tiered trail:
  **#82** the oracle GUI's dark consistency-warning channel and two `page` tags
  naming pages that no longer existed (19 checks propped up by stale names);
  **#86** Tail Span Loads publishing lb-in moments through the ft-lb `torque`
  channel — every figure 12× its label in both systems; **#85** the flap
  slipstream amplification computed, printed and then *not applied* to the
  delivered load, in a block that had never rendered at all; **#83** the
  23.457(b) slipstream case skipped in silence; **#84** One Engine Out
  simulating a condition a single-engine airplane cannot have and reporting a
  false *uncontrollable* verdict; **#76** the load boundary storing whatever
  JSON held, so a grid's text corners reloaded and re-crashed WINGGEOM; **#81**
  the M1-1b stall fill that only ran at construction, leaving the from-blank
  session dividing by a zero stall CL.
- **The code review** —
  [`../50_reviews/2026-08-24_oracle_gui_code_review.md`](../50_reviews/2026-08-24_oracle_gui_code_review.md):
  a code-level pass over `oracle_app/` + `app_shell/` (2,676 lines), the side
  the build review could not see. It found the shell sound and **two live
  first-order defects inside eight lines of one function**, closed as **#88**:
  the row counter deleted entered rows with no confirmation or undo (21 of 24
  weight items on one keystroke, saved in that state), and the row it *added*
  was a zero-weight CG case that stopped the whole flight envelope — reported
  as "cannot run yet", which is why nobody saw it. The narrow half of **#71**
  (`ZeroDivisionError` out of the not-ready catch) came with it.
- **The re-cut** (`00_backlog.md`, priority table): **0.8.0 — oracle-GUI
  development**, **0.9.0 — main-GUI development and bug correction** (#29 and
  its findings move there), 1.0.0 unchanged. Placement is **by fix site**, so
  shared-`app_shell` work rides with the oracle milestone; **#89** was filed
  for the review's two latent findings.
- **Version** `0.7.1` → **`0.7.2`** (PATCH: defect fixes only, **no calc-math
  change and no schema change** — `SCHEMA_VERSION` stays at v55).
- **Changelog cut** — `scripts/build_changelog.py 0.7.2 --date 2026-08-25`:
  **8 fragments** consumed into `## [0.7.2]` (Fixed only — the first
  single-section release), **6 history entries** rolled to the top of this
  file, a fresh empty `[Unreleased]` opened; released sections byte-untouched.
- **History roll** (`RELEASE_PROCESS.md` §4.3): no `30_future/` note carries a
  *shipped* status header this cycle, so nothing moved on that rule — but the
  live file reached **1,516 lines**, past the 1,500 threshold, so the 0.7.0
  cycle and cut were frozen verbatim into
  [`37_completed_development_to_0.7.1.md`](37_completed_development_to_0.7.1.md)
  (1,221 lines) and the live record is back to **313**.
- **Verification baseline:** unchanged from
  [`36_verification_baseline_0.7.0.md`](36_verification_baseline_0.7.0.md).
  No calc math moved on the FAR 23 path: every fix is a boundary, a refusal, a
  render or a units label, and the Appendix A oracles are the same tests
  passing on the same figures. The two changes that touch delivered numbers do
  so by *correcting* them — #85's slipstream factor now multiplies the flap
  load it was printed beside, and #86's moments now carry the unit they are in
  — and both are pinned by their own tests rather than by a new baseline.
- **Gates at cut:** `pytest` **2765 passed / 30 skipped / 1 xfailed / 0
  failed**, `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/
  scripts/` clean, `mypy` clean (`sloads/`), `scripts/smoke_test.sh` **PASS**,
  `scripts/backlog_issues.py check` clean, no open CRITICAL/MAJOR review
  findings.

**Key decisions.** *A release that is nearly cut is not cut.* The changelog
build had already run — fragments consumed, history rolled — when the owner
stopped it to review the GUI's code first; the cut was reverted wholesale and
the milestone gained two defects it would otherwise have shipped with, one of
which destroys the user's weight database on a single keystroke. The review
that found them was scoped *away* from the ground the build review had already
covered, which is why it read code rather than pages. Two rulings of record
came out of the re-cut. Rows are placed **by fix site**, not by which GUI
benefits, so the shared shell is worked once. And the **mission stays at
1.0.0**: the full-span balanced free-free airplane model — the deliverable the
backlog's own §Mission names first — now sits behind two GUI-focused releases,
a choice taken explicitly with the alternative offered and declined, and
written into the table as ruling 4 so a later reader finds a decision rather
than a drift. Finally, the closure discipline caught its own author twice this
cycle: a table row added without an issue behind it failed
`test_backlog_issues` at #88's close, and narrowing the results catch to
`MissingInputError` alone — which the review had recommended — broke the
documented error contract and was caught by `test_oracle_journey` before it
could ship.

## Release cut: **sloads 0.7.1** (the beta tested by building an airplane in it), tag `v0.7.1`, 2026-08-23

**Objective.** Test the 0.7.0 oracle-GUI beta the way a first-time user would —
by **building a Cessna 210 from a blank project, by hand, in the oracle GUI**,
every value typed by the owner from public data — and ship what that exercise
found. The milestone's content is therefore not a feature list chosen in
advance: it is whatever a real build surfaced, classified as it was found
(**a** interface broken → pulls the release back; **b** bug → 0.7.2; **c**
development → backlog), with each finding's body written in the session that
raised it.

**Deliverables** (the `[0.7.1]` changelog section is the release note):
- **The build review** —
  [`../50_reviews/2026-08-23_c210_oracle_gui_build_review.md`](../50_reviews/2026-08-23_c210_oracle_gui_build_review.md):
  all **fourteen** oracle pages built and reviewed, then the G6 hand-off into
  the main GUI through Balanced Cases and Tail Span Loads. **51 findings**,
  every one with a body and a disposition — **a = 2** (both fixed in-session,
  **none surviving**, so 0.8.0 keeps its planned content), **b = 7**
  (#76/#81/#82/#83/#84/#85/#86, the 0.7.2 list), **c = 42** (backlog rows
  #73/#77/#78/#79 and band C row 7a).
- **The two `a`'s, fixed in the cycle:** the oracle grid's **write-back
  remount race** (C210-4/C210-11 — every committed cell rebuilt the frame,
  changing `st.data_editor`'s widget identity, so a keystroke in flight was
  discarded; a typed `-25` became `25`; the 21-row items table was
  "impossible to enter"), fixed with a per-visit **stable frame**; and a
  polyline grid **typed from blank** crashing the Geometry page on string
  corners, fixed with a float-typed frame and a parsing boundary.
- **The results zip** (C210-45, tier M, above): the one control that delivers
  a project's complete results set, in both GUIs.
- **Two doc/UX closures:** every grid page states that a part-filled row is
  not saved; SELECT's search scope stated in `00_theory_sources.md` (the
  candidate pool is the entire balanced V-n matrix).
- **Standing owner rulings produced by the exercise:** the **C210-15 fidelity
  ruling** — the oracle GUI's fidelity target is the *analysis contract*, not
  the original prompt sequence, so UX may improve freely while consumed values
  stay correct; the OG-1 scope bound with its display-only-utility refinement;
  and the C210-31 **collapsed-override** pattern as the template for every
  derivable duplicate.
- **Version** `0.7.0` → **`0.7.1`** in `pyproject.toml` (PATCH: defect fixes
  plus one additive GUI capability, **no calc-math change and no schema
  change** — `SCHEMA_VERSION` stays at v55).
- **Changelog cut** — `scripts/build_changelog.py 0.7.1 --date 2026-08-23`:
  **5 fragments** consumed into `## [0.7.1]` (Added / Changed / Fixed), **1
  history entry** rolled to the top of this file, a fresh empty `[Unreleased]`
  opened; released sections byte-untouched.
- **History roll** (`RELEASE_PROCESS.md` §4.3): nothing to move — no
  `30_future/` note carries a *shipped* status header this cycle — and the
  live file is **1,245 lines**, under the 1,500-line threshold, so no archive
  was frozen.
- **Verification baseline:** unchanged from
  [`36_verification_baseline_0.7.0.md`](36_verification_baseline_0.7.0.md).
  This release changed no calc math: the oracle tests are the same tests
  passing on the same figures, and the one new output path (the results zip)
  renders through the existing report/CSV owners rather than computing
  anything. A new baseline document would restate 0.7.0's numbers verbatim,
  which the §4.5 rule exists to avoid.
- **Gates at cut:** `pytest` **2725 passed / 30 skipped / 1 xfailed / 0
  failed**, `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/
  scripts/` clean, `mypy` clean (`sloads/`), `scripts/smoke_test.sh` **PASS**,
  `scripts/backlog_issues.py check` clean, no open CRITICAL/MAJOR review
  findings.

**Key decisions.** *An interface is tested by building something in it, not by
reading it.* Thirteen of the 51 findings were reachable only because a real
airplane's data disagreed with the form's assumptions — the slipstream
amplification that no prior fixture could trigger (no project carried both a
flap slice and an engine), the point-mass wing fuel, the tail moment column
mislabeled by a factor of twelve. The classification rule was set **before**
the build and honoured: the `a` class was defined to pull the release back,
two `a`'s were found, both were fixed in the session that found them, and the
0.8.0 plan therefore stands unchanged — a rule that costs nothing when it is
never triggered would not have been a rule. Three closings were the owner's
call rather than the checklist's: the comparison against the bundled
`examples/cessna_210.project.json` is **deferred** past the cut (the
no-consult rule stays in force until it runs), the review was closed
**without** a final save of the G6 session edits — so the project on disk
predates them and the edit list in closing check 2 is the record — and no
Export & Report artifact was pasted, leaving the balanced-case equilibrium
gate (worst force residual **0.068 %** of n·W against a 2.5 % limit, pitch
**0.001 %** against 1 %) as the physics close of record. Each is written into
the review's status block as a limit on what the milestone demonstrated,
rather than left for a reader to infer from a missing artifact.
