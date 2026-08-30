# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

**Live cycle only.** This file holds the current release cycle plus the previous
release cut. Older blocks roll into frozen, do-not-edit archives at each release
(`RELEASE_PROCESS.md` §4): the 0.7.1 and 0.7.2 release cuts are in
[`41_completed_development_to_0.8.0.md`](41_completed_development_to_0.8.0.md),
the 0.7.0 cycle and the 0.7.0 cut in
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

## Release cut: **sloads 0.8.1** (the defects the 0.8.0 cut shipped, and the gates that let them ship), tag `v0.8.1`, 2026-08-29

**Objective.** Close band **B1** — the patch band the owner opened 2026-08-28
against defects found in *released* 0.8.0 output — and cut when it is empty.
The band was extended twice in flight by owner ruling, both on 2026-08-29: with
the three documentation items the independent review of `dev/v0.8.1` raised
(#140–#142, folded in rather than opening a 0.8.2 band), and with the two
process gates the post-0.8.0 escape assessment filed the same day (#145/#146).
Band B1 emptied 2026-08-29.

**Deliverables** (the `[0.8.1]` changelog section is the release note):
- **The LANDLOAD correction train** (notes 38/39, tier L): `BETA`'s sign on the
  ground-roll and tail-down attitudes, corrected at the origin on the evidence
  of Appendix A's own braked-roll construction figure (#133, with the
  datum-frame lift term and moment transform swept as the same sign class —
  both entered in the approved-corrections register); the ground reaction
  applied where the manual applies it — axle on the landing attitudes, ground
  contact on the ground-roll families, the manual's own printed column — ending
  up to 524,302 lb-in of invented pitching moment (#139); and the half of the
  printout the replication never shipped (#134): every case now emits three
  wheels with airplane-datum `Fx/Fy/Fz`, the application point `x/y/z`, the
  fuselage-axis angle, the datum load factors NR/NV/ND and the unbalanced
  moments, frame and point named **on the value** (`LoadValue.frame`/`.point`,
  schema **v57 → v59** in two recorded identity hops, #141).
- **The oracle is whole again:** p231–p233 re-rendered legible at 200 dpi and
  every printed LANDLOAD cell locked (72 more cells, all 33 cases); the ga6
  light-landing fixture weight restored to the manual's **2800 lb**, un-hiding
  the light-loading WR defect its back-solved 2803 lb had been absorbing — an
  input derived from an output cannot also test it.
- **The GUI defect pair from the GA6 V-n diagnosis:** an Optional record block
  is created and removed by a named gesture — a stray touch no longer attaches
  a phantom zero-coefficient set that saves with the file (#143); a lift
  polynomial with no alpha lever is refused as a named `MissingInputError`
  instead of iterated 400 trips into a `SolverFailure` (#144). Beside them: a
  `null` in a project file refused by name, one failing module no longer takes
  a whole results page down, a blank LIMNZ no longer resolves to zero through a
  half-entered planform, and the last-ulp formatting hang (#147).
- **The escape assessment's process gates,** closed in-band: the CI **GUI
  journey** — every bundled example walked through every `workflow.py` step
  with the project asserted byte-identical, now named in `RELEASE_PROCESS`
  §3.5 beside the boot smoke and a manual walkthrough line (#145); and **oracle
  provenance / gate independence** — every oracle cell states where its number
  came from, a back-solved input is disqualified, and no gate may re-derive the
  rule it checks (#146).
- **Breaking:** Python **3.10 is the floor** (#132) — 0.8.0's `>= 3.9` claim
  was refused at install by Streamlit 1.51's own metadata; the classifier set,
  CI matrix and floor are now one guarded claim.
- **Version** `0.8.0` → **`0.8.1`** (owner re-cut ruling 2026-08-28: a patch
  band for released-defect correction; the schema hops are additive/identity
  with old saves migrating, so the load-case CSV widens by two stated columns
  without breaking shape).
- **Changelog cut** — `scripts/build_changelog.py 0.8.1 --date 2026-08-29`:
  **20 fragments** consumed into `## [0.8.1]` across Breaking / Added /
  Changed / Fixed, **14 history entries** rolled to the top of this file, a
  fresh empty `[Unreleased]` opened; released sections byte-untouched.
- **History roll** (`RELEASE_PROCESS.md` §4.3): notes **38** (ground frame) and
  **39** (application point) carry *SHIPPED* headers and move to `40_history/`
  (42/43); notes 32/34 stay with their open GUI milestones. The live file
  passed the **1,500-line threshold**, so everything below the 0.8.0 cut block
  froze verbatim into
  [`41_completed_development_to_0.8.0.md`](41_completed_development_to_0.8.0.md)
  (the 0.7.2 and 0.7.1 release cuts).
- **Verification baseline:** the corrected LANDLOAD figures are pinned by the
  full Appendix A p230–p233 page locks in `tests/test_landing.py` — the printed
  pages are the baseline of record, cell for cell, which is stronger than a
  recorded-output archive; the two deliberate departures from the manual's
  *program* (the `BETA` sign class) are in
  [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md).
- **Gates at cut:** `pytest` **3177 passed / 32 skipped / 1 xfailed / 0
  failed**, `ruff` clean, `mypy` clean (`sloads/`), `scripts/smoke_test.sh`
  **PASS** (both front-ends boot, CLI CSV checked),
  `scripts/backlog_issues.py check` clean,
  `scripts/branch_protection_snapshot.py --check` matches on 7 tracked keys,
  no open CRITICAL/MAJOR review findings.

**Key decisions.** *The assessment ran before the cut, and its findings became
band rows, not prose.* The post-0.8.0 escape assessment traced every escape to
a gate that measured the wrong thing — a boot check where use was the risk, a
binary oracle rule where provenance was the risk — and both fixes shipped
inside the same milestone as the defects they answer (#145/#146), per rule 3:
structural gates, never prose rules. The owner's re-cut rulings held the line
against milestone sprawl twice: the documentation band folded into B1 rather
than becoming 0.8.2, and the milestone list stayed 0.8.1 → 0.9.0 → 1.0.0.
The `BETA` sign was corrected **at the origin** on the manual's own
construction figures rather than patched downstream, and #139's lesson — the
gate that should have caught it was making the correction itself — is now the
named gate-independence rule. **Band B1 retired with the cut; band B2 (0.9.0 —
main-GUI development, anchored by #29) is the milestone in flight.**

- **The word travels with the value: frame and application point stated in-band
  in the delivered CSV (tier M, schema v59, 2026-08-29)** — the 2026-08-29
  independent review of `dev/v0.8.1` raised that the corrected landing output
  #133/#134/#139 shipped is not self-describing: the CSV names neither the frame
  its numbers are in nor the point each force acts at. Both facts already existed
  on the calc side — `LoadValue.frame` since schema v58 (note 38 GF-6/GF-7), the
  point in `landing.case_note()` and both GUI captions — and this one channel
  dropped them, because `results_to_rows` reads neither the note nor the frame
  for output. The point therefore reached a consumer as coordinates alone, and
  the axle and the ground contact point are a rolling radius apart, so guessing
  wrong is a moment arm rather than a caption. Two channels were on the table
  (the issue left it open): the project-scoped methods preamble, which prints on
  every module's CSV and could not name a *per-case* point when cases 1–33 split
  between the two, and per-row columns. The columns won, and the point took the
  same posture the frame already had rather than a second one: `LoadValue.point`,
  a vocabulary (`gear_loads.POINTS`) and not free text, stamped per leg from
  `application_point_of` — the single owner design note 39 AP-1 already
  established — and read once, at the render boundary, into an `Applied at`
  column beside a new `Frame` column. Deriving it there instead, by parsing the
  note or re-deriving from the case number, was rejected: it re-establishes
  exactly the label/note string-matching M4-9 removed, where a reworded sentence
  silently blanks a column. The reference-node rows deliberately name no point —
  the node is where the reaction is transferred *to*, and stamping it would say
  one force is applied in two places at once. No load moved: five landing CSV
  digests changed, every other frozen Imperial channel is byte-identical, and the
  Appendix A oracles and twin closures are untouched. Guards:
  `test_the_delivered_csv_states_its_frame_and_its_application_point` (every
  delivered force row on every fixture names both),
  `test_the_csv_point_is_appendix_as_printed_column_case_by_case` (the column is
  the manual's, so a constant word would read correct on half the matrix),
  `test_the_reference_node_names_no_application_point`,
  `test_every_landing_value_names_a_known_point_or_none` and
  `test_a_module_that_names_neither_gets_neither_column` — the last pinning that
  #141 states the landing output and does not widen every CSV. **The schema hops
  v58 → v59**, an identity (`_hop_58`; `""` means exactly what v58 meant) for the
  reason v58 itself hopped: `LoadValue` is persisted inside
  `critical.conditions[].loads`, so a display-neutral addition is still a shape
  change. It stays tier M under the 2026-08-29 re-cut's second ruling — no load,
  no quantity, no physics and no theory citation to make — with the hop named
  here so the schema move is on the record rather than inferred from a diff
  (issue #141).

- **The set that carries no airplane (#144, tier M, 2026-08-29)** — Found
  diagnosing a GA6 V-n failure that named nothing: a coefficient set had reached
  the balance with every lift coefficient zero, and the only evidence the user
  got was "did not converge in 400 iterations … reached NZ=0 at alpha=41.3861
  deg". The refusal is stated where the value is consumed, for every writer,
  because more than one can produce it (#143 is the writer this one came from,
  and it is fixed separately) — the same ruling the #81 stall-CL, weightless-CG
  and tail-CP-at-datum guards on that function already carry.
  The line is drawn at *no alpha lever*, `C1..C4` all zero, rather than at the
  identically-zero polynomial the report showed. A constant-CL set (`C0`
  non-zero, no slope) hangs the inner loop the same way and for the same reason:
  NZ cannot move, so the iteration has nothing to iterate. That is unsolvable,
  not merely implausible, which is what separates it from the neighbouring
  `aero_lift_slope_sign` warning — a negative or over-large slope still
  balances, and stays a `ConsistencyWarning` rather than becoming a run failure.
  The other two polynomials are ruled on explicitly in the guard's docstring and
  executed in the test: an all-zero drag or moment polynomial must still run,
  because `CD = 0` and `CM = 0` are values a set may honestly carry, while an
  all-zero lift polynomial is a statement that there is no airplane to balance.
  The test drives both entry points that share `balance_configs`, and builds its
  phantom set the way the GUI does — blank coefficients with `stall_cl` filled
  from `clmax_flap` — asserting that fill first, so the case cannot quietly stop
  proving anything by starting to trip the #81 guard instead.

- **The printer that amplified the noise the package had already been taught to
  suppress (#147, tier M, 2026-08-29)** — Found running down a red fast gate on
  a **docs-only** commit: `test_imperial_output_matches_the_frozen_baseline`
  failed on the Linux 3.12 leg naming `concept_regional_jet`'s landing channels,
  and passed on macOS. `CONVENTIONS.md` §7 already carried the rule this
  violates — a byte in a deck or report must not depend on the libm build, FMA
  or the interpreter's `sum()` — with three owners: `picks.extreme` for keyed
  picks, `sbeam_bridge._fmt3` for card-component dust, and `math.fsum` at every
  summation. The human-channel formatter was never one of them, and it was the
  one place where an ulp of difference was not damped but *amplified*: its two
  branches are `str(int(value))` and `f"{value:.4g}"`, and the test between them
  was exact equality with the integer.
  The evidence that settled it needed no second platform. The shipped output
  already disagreed with itself: case 12 of `concept_regional_jet` prints the
  unbalanced yawing moment as `-687258` on the datum row and `-6.873e+05` on the
  body-frame row — the same load, one ulp apart, two precisions — and case 18
  prints the main drag reaction as `12768` on one row and `1.277e+04` on
  another. A sweep found 95 ulp-unstable cells in that one example's landing
  output alone. Landing is where it surfaced because landing is the trig-heavy
  path the #133/#134/#139 rotations built, and `sin`/`cos` are exactly where two
  libm builds part company.
  The fix is one line of quantization rather than a widened branch, because the
  quantity being made stable is *what the reader sees*: rounding to twelve
  significant figures first makes both branches read the same number, and the
  residual knife edge — a value within an ulp of a twelfth-digit boundary — is
  one no deliverable distinguishes. The guard is stated on real values, not
  invented ones (`test_no_printed_deliverable_cell_hangs_on_the_last_ulp` walks
  every value of every condition of the failing example's landing module under
  ±4 ulp, with a non-vacuity floor), and the row in §7 gains the formatter as an
  owner so the next printer added has somewhere to be listed. `tests/
  test_platform_stability.py`'s docstring had recorded the precedent a week
  earlier: 3.12's compensated `sum()` moved values "where a value sat on a print
  boundary" and the digest failed on the 3.12 leg only. That fix removed a
  source of noise; this one removes the amplifier, which is why the class is
  closed at the printer and not at the next quantity to land on an integer.

- **A back-solved input, an unusable oracle page, and the loop that closed between them (tier M, 2026-08-29)** —
  Step C10 recorded that Appendix A's wheel-load table was OCR-garbled and that
  the GA6 light-landing weight "was back-solved from the legible side-load cell
  (½·1.33·W = 1864)". Two consequences followed from that one move and neither
  was visible from inside the codebase: the fixture carried **2803 lb** where
  every other statement of the same quantity said 2800 (WTENV's
  forward-regardless weight, the `CG3` flight point at the identical station and
  waterline, and `cg_cases.seed_landing_cases`, which takes this case's weight
  straight from the envelope anchor), and the braked-roll family was left with
  **no printed-value oracle at all** — an input derived from an output cannot
  also test it. The family ran on internal identities, which is what let #135's
  `WR` defect sit undetected in shipped ULTIMATE loads.
  Reading the rendered p231 broke the circle: the cell prints **1862**, not
  1864, and `1862/0.665 = 2800.0` exactly. The fixture is corrected to 2800,
  which closes the +0.107 % residual #135 deliberately left rather than absorbed
  into a widened tolerance, and the ground `fwd light` case becomes identical to
  the flight `CG3` point it was always the same corner of. Cases 15, 18, 23, 24
  and 31–33 move 0.107 %; no other fixture is affected. The page then yields
  what it had been assumed not to: `test_landload_braked_roll_printed_cells`
  locks cases 16/17 and 18 on p231 and case 18's airplane-datum pair on p232 at
  ±0.1 %, the 23.493 family's first printed-value oracle, and the cells are
  recorded in `theory_sources.md` as **transcriptions from the rendered page,
  not OCR extractions**, since that distinction is exactly what failed here.
  Two structural consequences beyond the number. The drift that hid for a year
  was that `seed_landing_cases` is only ever *offered* to the GUI and never
  checked against what a project carries, so
  `test_a_seeded_fwd_light_case_weighs_what_the_seed_gives_it` now makes the
  seed a checked invariant on every fixture, exempting a case that states its
  own D-25 loading (`baron_58`'s fwd light closes at 4,440 lb against a 4,200 lb
  anchor — a different quantity, correctly not a drift). And the p232 pair gives design note 38's
  open GF-1 question its first transcribed deviated-from cells (Fz 1733 /
  Fx 1638), which the blocking GF-3″ register entry needs. It was first read, the
  same day, as *refuting* GF-1 — the shipped `PHIM = atan(0.8) + GRA2` gives
  1733.0 / 1637.9 where GF-1's `atan(0.8) − GRA2` gives 1978.4 / 1331.2 — and
  that reading was withdrawn within the day (note 38 §1.12): `LANDLOAD.BAS`
  computes the pair *from* the printed angle on the same line
  (`VM(L)=RMP(L)*COS(PHIM(L)/57.3)`), so the two cells are one measurement and
  cannot adjudicate the sign of the rotation that produced them. A printed
  number overrules an argument only when it is independent of it.

- **Where the load acts: the printed column the OCR lost, and a gate that was
  correcting the code instead of testing it (tier L, 2026-08-29)** —

  **Objective.** Give the landing deliverable a point of application that is the
  manual's, opening issue #134 (design note 38 GF-6, "a load and its point are
  one statement"). The first check made before emitting anything was whether the
  point about to be emitted was the point the deck already transferred from. It
  was not, on twelve of the 33 cases, and the item stopped there: a defect with
  first-order effect on shipped content outranks the fidelity item that exposes
  it (`CLAUDE.md` rule 6), so #139 was filed, design note 39 written and agreed,
  and #134 re-ordered behind it — the same sequence #133 forced a day earlier,
  for the same reason.

  **What was wrong.** `gear_loads` transferred every case from the tyre contact
  patch. Appendix A applies cases 1–12 at the **axle** ("CENTER OF EACH WHEEL")
  and 13–24 at the **ground contact point**, with 25/26, 28/29, 31/32 at "CL
  AXLE" and 27, 30, 33 at "GROUND" — a column in the p231/p232/p233 headers that
  had been unreadable in the scan since 2026-08-15 and was recovered at 200 dpi
  on 2026-08-29. The consequence is a spurious `r × F` pitching moment on every
  balanced landing case, absorbed into the solved `q̈` and shipped in the deck's
  `MOMENT` cards. The split is not editorial: level-landing drag is a **spin-up**
  load, whose reaction reaches the leg through the bearing at the axle, while
  braking torque is internal to the wheel/leg free body and leaves the patch
  force where it acts.

  **The evidence, and why it counts.** LANDLOAD prints its own unbalanced
  pitching moment `PITCHP`; the assembled case reports a pre-closure residual;
  the two are the same quantity up to G-7a's distributed lift, which the manual
  nets at the CG. Nothing in `residual My − G-7a lift == PITCHP` is derived from
  the application point, so it adjudicates it — and it reproduces the printed
  column on all six fixtures with gear, closing to ≤62 lb-in at the column's
  point against 20,964–665,862 lb-in at the other one, splitting exactly at the
  column's own family boundary. On ga6's LG-01/02/03 `PITCHP` is exactly zero, so
  the entire patch residual was invented; at the axle what remains is the lift
  moment the suite knowingly adds, to 0.1 / −1.8 / −0.5 lb-in.

  **Deliverables.** `application_point` / `application_point_of` (`AXLE` /
  `GROUND_CONTACT`) own the point; `GearLegLoad.point` and `AppliedWheel.point`
  carry it beside `patch`, which stays reported because a gear analysis starts
  there (AP-3); `transfer_couple` takes it. No reaction changes — the forces are
  LANDLOAD's own — so every Appendix A oracle and printed-cell lock passes
  unmodified, which is itself the acceptance criterion G-AP-5 states. `LG-04`'s
  pre-closure `My` moves −179,232 → −158,271 lb-in, `q̈` −1.925e-2 → −1.701e-2;
  the frozen Imperial digest, `balanced_cases.md` §9.5, `CONVENTIONS.md` §1/§7,
  `PROGRAM_SPEC.md` and `theory_sources.md` move with them. The sbeam roundtrip
  stayed green, as note 39's OQ-A2 predicted and did not assume.

  **Test.** **G-AP-1** — the identity on every balanced ground case of every
  bundled fixture at `1e-4 · n·W·MAC` (worst measured 2.65e-5, baron_58 LG-17).
  **G-AP-2** — the point against a case-by-case *transcription* of the printed
  column, never against the rule the code applies, since two copies of one rule
  cannot disagree. **G-AP-3** — a structural guard that the package builds an
  application point in exactly one place. The two existing negative controls were
  re-anchored to `point`: one of them, the static-axle control, had read `patch`
  and would have silently lost the ability to fire.

  **Key decisions.** AP-1 the printed column, as physics and not as a label; AP-2
  one owner for the point; AP-3 the patch stays reported; AP-4 no reaction moves,
  which keeps the whole oracle surface outside the change; AP-5 ship the gate
  that found it rather than a widened tolerance; AP-6 tier L, ahead of #134.

  **The lesson, which is about a test and not about the code.** The rotational
  gate had been moving the applied load from the tyre to the axle *inside the
  test* since 2026-08-15, on exactly cases 1–12, with a comment recording that
  getting it wrong "is not subtle: the level family misses by 12 % (21,000 lb-in
  on ga6_normal case 4)". The number was right, measured, and written down; it
  was read as bookkeeping between two conventions rather than as a defect,
  because the point the code used had no independent statement to be wrong
  against until the column was recovered. A gate that corrects the code before
  comparing is not testing the code — it is agreeing with it. The correction now
  lives at the origin and the gate makes none of its own, which also let the
  braked-roll pitch line drop the 5 % slack it had carried for #133: **every
  family closes on one bound.** Design note 38 §1.7 had audited this chain
  end-to-end and passed it, checking that the transfer was consistent — which is
  precisely what a wrong point preserves. Its verdict is overturned in place.

  **A duplicate removed on the way through** (rule 4): `transfer_couple` was
  implemented twice, identically, in `gear_loads` and in `export/coordinates`,
  each docstring claiming to be note 24 R-11's single owner. Consolidated onto
  the calc layer, since the export side can import it and not the reverse, with
  the name re-exported so no export call site moved.

- **The gate that proved boot, and the walk that proved use (#145, tier M,
  2026-08-29)** — The GUI release gate started both front-ends and checked the
  root page answered 200. Every automated test above it rendered **one** page,
  with a **fresh** session, on a **fresh** project, and almost always on
  `ga6_normal`. Between those two shapes sat the defect class that had produced
  both post-0.8.0 escapes: load an example, touch something, find the damage two
  pages later. `tests/test_gui_journey.py` closes it by walking every bundled
  example through every `workflow.py` step in order — one session carried
  forward, widget state included, since the stale-widget class `widget_keys`
  exists for lives in exactly that carry-over — pressing every Apply over
  untouched widgets and then running every registered module. Its assertion is
  that the project comes out byte-identical, because nothing was entered.
  It failed on its first run, and what it found was the reason to have written
  it. #143's ruling — an `Optional` record is created and removed by a named
  gesture, never attached by a touch — had been implemented in the oracle GUI
  through its field registry, and the main GUI, whose pages are hand-written, had
  never received it. Pressing Apply on a page nobody had filled in attached a
  zero-valued slice; on the sparser examples the walk collected eight of them,
  and two were load-bearing: a zero-area `flap_loads` and a zero-cylinder engine
  make their modules raise, so **Results Review and Export were both dead on
  three of the seven shipped examples** — reachable by opening a bundled project
  and clicking Apply. `app_shell/optional_slice.py` is the single owner of the
  app-side rule, which is narrower than the oracle GUI's add/remove pair because
  here the Apply *is* the named gesture: it may fill a slice in and may empty one
  out, but it may not create one out of nothing. "Entered nothing" is read off
  the dataclass defaults rather than a per-page field list, with a `seed=` form
  for the forms whose widget defaults are not the dataclass's, and the walk is
  the drift guard — a new page that writes an `Optional` slice directly fails the
  day it is written.
  The sweep (practice 4) found the same shape inverted three more times: a
  wholesale rebuild that enumerates the fields its own form renders **deletes**
  every field it does not. The Aero Apply destroyed a populated `lateral_body_aero`
  block and re-derived `cruise.stall_cl` from CLmax — the exact failure the
  neighbouring fuselage-moment form carries a paragraph of comment about guarding
  against, worth +30 % on the atr42_100 stall clamp; the Payload Cases Apply
  deleted the `LoadingDefinition` off three of baron_58's six CG cases, which is
  what produces their mass model; the engine form wrote unset `Optional` power
  fields back as stated zeros, #121's class from the writing side.
  The crash had a second cause, and the first attempt at it was wrong. Two modules
  raise a plain `ValueError` for a slice that exists with nothing in it, and the
  obvious move — refuse by name so "run every module" skips them — was made and
  then reverted: `test_cli.py::test_an_invalid_control_surface_input_fails_rather_than_vanishing`
  is m2 ruling that a zero aileron area is an *invalid* input and must fail the
  run, not an absent one to be skipped, precisely so a deck cannot come out one
  case short in silence. The ruling stands and the fix moved to the consumer:
  `run_all_modules_reporting` hands the failures back beside the results, and the
  two pages name the module instead of dying with it. The lesson is the cheaper
  one to have learned from a red test than from a review — a page crashing is not
  evidence that the exception is wrong, only that its reader is.
  The residue is ten writes the walk still sees, kept in the file's `KNOWN_OPEN`
  list with a backlog row and — the part that matters — a test asserting each one
  still reproduces, so an entry cannot outlive the defect it names. The lesson is
  narrower than "test the GUI": per-page coverage and a boot check are both real
  gates and neither can see a journey, and the cheapest thing that can is a walk
  that enters nothing and demands the project come back unchanged.

- **A load and a point and a named frame: the half of LANDLOAD's printout the
  replication had never shipped (tier L, 2026-08-29)** —

  **Objective.** Close design note 38's second deliverable (GF-6/GF-7, issue
  #134): make the landing output what a stress model can consume. LANDLOAD
  prints its whole 33-case matrix **twice** — once with respect to the ground
  line, once with respect to the airplane datum, each under its own banner — and
  `run()` shipped the first set only, with no application point, no attitude and
  no frame label, while the export deck consumed the other frame. A reader
  moving between the Oracle's table and the deck had no stated bridge, and the
  two differ by a rotation of the ground angle. The item waited on two ordering
  conditions and outlived both in the same session: the `BETA` sign (#133) and
  the application point (#139), each of which would otherwise have shipped a
  number this item then had to move.

  **What was missing.** Five things, all of them printed in 1990: the
  fuselage-axis angle per case (p231's own column); the airplane-datum table
  (p232 — `vm/dm/vn/dn` were computed and never reached `ModuleResult`); the
  NR/NV/ND datum load factors (not computed at all); the frame labels (the main
  GUI said "(ground line)" in prose, the Oracle said nothing); and the point of
  application, which lived only in the gear free-body report and the deck.

  **Deliverables.** New `sloads/frames.py` — the two frames, the manual's own
  caption words (`LANDLOAD.BAS` lines 5140/5230), the report-vs-deliver rule
  (`is_report_only`) and the rotation between the frames (`rotation_deg`,
  `to_airplane_datum`, `to_ground_line`, moved down from `gear_loads` so
  `landing` can reach them). `LoadValue` gains `frame` — **schema v57 → v58**
  with an identity hop, because `LoadValue` is persisted inside
  `critical.conditions[].loads`. `gear_loads` gains `DeliveredLeg` and
  `delivered_legs` / `delivered_gear_legs`: the three wheels of a case, in report
  order, built *from* `applied_wheels` rather than beside it, with the wheels it
  drops emitted at zero and their point and node still stated. `landing.run()`
  emits, per case: the three wheels' `Fx, Fy, Fz` and `x, y, z` and node, the
  fuselage-axis angle, NR/NV/ND, and p233's datum unbalanced moments — with the
  strut state and Appendix A's point-of-load column in the condition note. The
  critical-reaction summaries render through the same builder, so a family's
  summary cannot state its case differently from the matrix row it points at.
  Both GUIs gain the datum table and caption every reactions table from
  `frames.caption`. The main GUI's landing page and the Oracle's landing block
  both say which frame each row is in, in the manual's words.

  **Two more sign errors, and the reason they could not be typed.** The datum
  drag load factor's lift term is written `+LF*SIN(GRA)` in the `.BAS` and the
  datum moment transform rotates by `+GRA` — the third and fourth instances of
  the class #133 adjudicated, in the two quantities that entry could not reach
  because neither existed in sloads. Neither is written longhand here: the lift
  is `to_airplane_datum(LF, 0, ρ)` and the moments are
  `to_airplane_datum(YAWP, ROLLP, ρ)`, rotated through the case's own **measured**
  `ρ`. The corrected value is what a rotation gives; there is no second place a
  `+` could be typed for a `−`. Approved deviation registered under #134.

  **Test.** New `tests/test_landing_deliverable.py` (18 gates, G-GF-6/G-GF-7):
  three legs on every case of every bundled example and the *right* wheels
  unloaded per family; the point is the printed column and is the axle or the
  patch and nothing between, checked against the geometry rather than against
  `gear_loads`' own construction; the three legs **sum to p232's own force
  cells** and the datum factors are that sum through the printed loops — derived
  from the page, never from the module under test; case 1 and case 16 lock at the
  ruled numbers; the datum moments preserve their magnitude and leave pitch
  invariant; the CSV/text split guarded **both ways**; the frame split owned by
  one predicate; neither GUI writing the frame words itself. Plus 72 new
  Appendix A cells in `test_landing.py::test_landload_p232_airplane_datum_load_factors`.

  **Key decisions.** *(1)* The primed set leaves the CSV, so the datum moments
  had to be built — otherwise the deliverable would carry no moment at all. That
  answers design note 38 §5.4's one open disposition, in the item that needed it.
  *(2)* Three legs always, zeros included: which gears a family lifts is a fact
  about the case, and omitting them makes the reader reconstruct the rule from
  the case number. *(3)* The deliverable is built from the deck's own wheels, not
  beside them — #139 had just shown what two constructions of the same statement
  cost. *(4)* The LANDLOAD case families moved to `modules/landing.py`, which
  draws those lines already, and `attitude_of` with them; the 23.485 pairing that
  `NS` and the deck each derived separately became one `side_partner`.

  **What the numbers said back.** Three invariants the correction did not aim at:
  the tail-down family reproduces **all three** printed p232 cells exactly, because
  the `.BAS` already carries the corrected sign there — the manual is internally
  inconsistent, and one of its attitudes is right; `NV` does not move on cases
  1–12, because a cosine is even; and `NR` stays printed to the digit on the
  wheels-only families 16–24 (1.703, 1.330), because a rotation preserves a
  resultant. A correction that broke any of the three would have been the wrong
  correction.

- **The pages were never illegible (tier M, 2026-08-29)** — Step C10 recorded
  Appendix A's three LANDLOAD result pages as OCR-garbled, and the project took
  that as a property of the pages rather than of the extraction method. For a
  year the module's 24-main/33-nose matrix was validated by formula closure plus
  whichever cells happened to survive the text layer, with cases 13–33 resting
  on internal identities alone. Two defects lived in exactly that gap and were
  found the day before this one, both by reading a single rendered cell: the
  gross-weight ratio applied to LANDLOAD's light loading (#135) and a fixture
  weight back-solved from a mis-OCR'd number (#137), the second of which had
  quietly made an input a function of the output it was used to check.
  Rendered at 200 dpi the pages read cleanly, so all three were transcribed:
  p231 ground line, p232 airplane datum and p233 limit unbalanced moments, every
  cell of every one of the 33 cases, now locked at each page's own print
  resolution. The port reproduced all of it with no calc change — the coverage
  was missing, not the physics. Three things follow. The open sub-finding on
  design note 38 §1.11 is closed, and with it the property that a 40 % move in
  the supplementary-nose reactions could leave the suite green. Design note 38's
  blocking gate GF-3″ — a register entry stating its whole deviation surface in
  values transcribed from the page rather than computed from the pre-fix code —
  now has that set, in executable form, and it shows GF-1 and GF-2′ costing
  different things: GF-1 departs only from p232, while GF-2′ additionally departs
  from p231 and p233 rows that match the port exactly today, so the register must
  price them apart. And p233 turned out to print a **second** ground-to-datum
  rotation, `RMOM = RMOMP·cos GA + YMOMP·sin GA`, applied with the same sign on
  every attitude where PHIM/PHIN switch sign between them — a third instance of
  the note's own sweep class, after PHIM/PHIN and the datum ND lift term, and
  like that one it is not ported and can only arrive through the #134 reporting
  item. The standing lesson is narrower than "read the sources": an OCR failure
  and an illegible page are not the same finding, and the citations now record
  which of the two a cell came from.

## Step — LANDLOAD's `BETA` sign, and the figure that settled it (tier L, 2026-08-29, issue #133)

**Objective.** Adjudicate and correct the sign `LANDLOAD.BAS` carries in
`BETA(2)`/`BETA(3)`, which set both the ground-roll lever arms and the
airplane-datum resolution of every attitude-1 ground case — quantities that reach
the exported deck as ULTIMATE loads.

**Deliverables.** `beta = (gamma - gra1, -gra2, -gra3)` at `landing.py:229`, plus
the `ap[1]` call site that read the literal `gra2` rather than `beta[1]`.
Attitude 3's two compensating negations — `bp[2]` written longhand with a flipped
second term, and `PHIM(7–9) = −BETA(3)` — are removed as redundant, moving no
number and leaving the sign in one place. `cp[1]` stays on `+gra2`: it builds the
contact-patch line, and the figure confirms `CP` unchanged. The `ρ` pin is
flipped and renamed; the register entry supersedes the declined decision of
2026-08-15; `PROGRAM_SPEC`, `theory_sources` and `balanced_cases.md` §9.5 follow.

**Test.** `test_rho_is_minus_the_ground_angle_in_every_attitude` — `ρ == −GRA`
exactly, every case, every gear fixture, against `ground_angles` directly. The
p230 arm oracle re-pins to p235's figure (77.052 / 17.760 / 94.811, `CP` 42.981
unchanged); the p231/p232/p233 page locks gain a `_CORRECTED` table whose every
value is derived from Appendix A's own printed formulas with the single
substitution `BETA(2) = −GRA(2)`, never from the module under test — the two
agree to ~1e-5 relative. No lock removed; the printed cells stay transcribed as
the thing deviated from.

**Key decisions.** *The manual contradicts itself, and that is what made this
adjudicable.* Three sessions of frame reasoning had produced arguments on both
sides and two of them were wrong: a `DP`-as-wheelbase argument whose premise was
false (`DP` is axle-to-axle normal to the resultant, and the patch separation is
94.622, not the 94.811 it asserted), and a reading of the p232 force cells as
refuting the correction, withdrawn within the day because `LANDLOAD.BAS` computes
those cells *from* the angle they were taken to test. What settled it was not an
argument at all: Appendix A's construction figures. p234 states the rule the code
implements for one attitude out of three; p235 prints the braked-roll arms the
corrected sign produces, against the table its own program printed. **A printed
number overrules an argument only when it is independent of it** — the lesson the
withdrawn p232 reading paid for, and the reason the p235 figure counts where the
p232 cells did not.

The correction has an independent witness, which is why it can be believed
without the figure: the assembled ground case's pre-closure residual pitching
moment, measured against LANDLOAD's *own* printed unbalanced moments — a quantity
the fix does not touch. On `ga6_normal` case 13 it falls from **−757.1 to −0.7
lb-in** and `q̈` from −8.0e-5 to −7.4e-8. The wrong-signed lever arm was what
that residual had been reading all along; §1.8 had found it and read it as
evidence *against* the correction, because at that point only one of the two use
sites was being fixed.

*Fix at the origin, not the use sites.* The defect's whole shape was one value
read twice, with one attitude patched at both its readers and another at neither
— the signature of a sign fixed where it was noticed. Correcting `beta` and
deleting the compensations puts it in one place and makes the field comment
("resultant-to-FS angle") true for the first time.

*The enabler is retired.* `ground_rotation_deg` recovers `ρ` from each case's own
two resolutions, which is self-consistent by construction and structurally cannot
see a sign error; its docstring said so and treated that as a feature —
"never has to adjudicate a sign inconsistency that is in LANDLOAD.BAS itself".
Its own measured output had isolated attitude 2 for months (−4.0570 level,
−15.0003 tail down, +4.7253 ground roll). The absolute gate now sits upstream of
it, with its assumption stated: the nose-up sense of `GRA` is derived on tricycle
geometry, the only arrangement the suite models.

- **LANDLOAD's light loading took the gross-weight ratio it is not given (tier M, 2026-08-29)** —
  Reviewing the GA6 braked-roll nose-clear family (cases 16–18) against Appendix A
  turned up a defect the closure tests could not see. `LANDLOAD.BAS` states the
  per-case weight table three times (lines 820–900) and the light loading is the
  exception throughout: `WL(15) = WL(18) = WL(23) = WL(24) = WCG(3)`, with no
  `WR = GW/MLW`, because that loading already sits below the landing weight. The
  port's braked-roll loop wrote `wcg[(m - 13) % 3] * wr` for all three loadings,
  overstating cases 15 and 18 by the ratio — 5.0 % on the GA6, 6.1 % on the
  regional-jet fixture. The suite stayed green because the braked-roll family
  carried **no printed-value oracle**: `theory_sources.md` records p231–233 as
  OCR-garbled in the bundled PDF, so the family was held by internal identities
  (`DMP = 0.8·VMP`, `VNP = 1.33W − 2·VMP`), every one of which the defect
  satisfies. It surfaced only when the page was read directly — printed VMP 1862
  / DMP 1490 against 1962 / 1570 as shipped. Fixed by carrying the BASIC's
  exception, which the module already spelled out correctly at its three other
  sites; the guard therefore pins the rule at all four (and at the two
  max-landing loadings that *do* take `WR`) rather than regression-testing the
  single line that was wrong, per the generalize-on-first-find rule. A residual
  +0.107 % remains and is **not** absorbed: the fixture's light-landing weight,
  2803 lb, was itself back-solved from this same printed cell when it was read as
  1864, and `1862/0.665 = 2800.0` — the fwd-regardless weight p230 prints. That
  correction is filed separately because it moves a shared input with a wider
  blast radius, so case 18 is guarded here by the weight-independent identity
  `VMP(18) = VMP(23) = VMP(24)` instead of a ±0.1 % lock. Two findings came out
  of the same reading and are filed rather than fixed here: the braked-roll and
  supplementary-nose families still have no printed-value oracle on any fixture,
  and the p232 datum pair (Fz 1733 / Fx 1638) reproduces under the shipped
  `PHIM = atan(0.8) + GRA2`, which pins the fidelity of the port and supplies
  design note 38's GF-1 with transcribed deviated-from cells — not, as first
  read, evidence about the rotation's sign, since `LANDLOAD.BAS` derives that
  pair from the printed angle on the same line (withdrawn the same day, note 38
  §1.12).

- **The guard that restored the defect it was added to prevent (#122, tier M, 2026-08-29)** —
  Every shipped fixture types its `engines[].limit_load_factor`, so the OV-7
  derive path had never been walked by a test. #71's mutation sweep runs every
  module over every shipped fixture with the planform half-entered and allows
  only `ValueError` out; it passed, because `effective_engine` caught the
  planform's refusal and let the blank stand. Reproducing the reported
  `TypeError` found nothing — the traceback really was gone — but blanking LIMNZ
  in the test rather than in a fixture showed what had replaced it: a
  half-entered wing resolved LIMNZ to 0 and every mount case with it, which is
  precisely the C210-41 defect the derive exists to close. A sweep that asks
  only "did anything escape?" cannot see this: suppressing the exception is one
  of the ways to pass it. So the gate is stated on the *refusal*, not on its
  type — `test_the_limnz_derive_refuses_rather_than_resolving_to_zero` asserts
  the intact planform derives the 23.337 limit, that each of the nine mid-entry
  mutations raises naming `'wing'`, and that an absent wing surface still
  answers off STRSPEED's typed fallback.
  Two structural points beyond the one line. The fix asks
  `derived_geometry.planform_area_sqft` — the precondition's existing owner —
  rather than restating the check inside the engine module (rule 3), which is
  the same discipline #71 imposed on the five strip sweeps. And the new sweep
  `test_a_derive_by_default_field_refuses_through_a_half_entered_planform` runs
  over a mapping of the OV-7 inputs that derive *through geometry*, blanking
  them in the test so the guard cannot be hidden again by a fixture entering the
  number — which is exactly how #122 was found on `baron_58` and then
  re-concealed when the example took the POH's +4.2 [C]. Adding a future
  derive-by-default field to that mapping is the whole of covering it (rule 4);
  today only LIMNZ routes through a planform, the mass-selector derives reading
  `weight.items`, which cannot see one.

- **The door that only opened (#143, tier M, 2026-08-29)** — The writer half of
  the defect class #144 closed at the consumer, found the same day diagnosing
  the same GA6 V-n failure. `commit_pending`'s rule was that a record the render
  pass created is attached only if the pass put something in it, which is what
  makes a page visit clean (OG-F) — but "something" is any non-blank field, and
  the LANDING coefficient set's own flaps-down flag is a field. Ticking it said
  nothing about the airplane and attached a complete zero-coefficient set;
  `normalize()` then filled its `stall_cl` from `clmax_flap`, so the record was
  permanently non-blank and un-checking could not take it back. Silent data
  *gain*, the inverse of the #51 class, persisting into a saved project file —
  and #144's refusal, once it landed, ended by telling the user to "remove the
  set" through a GUI that had no control for it: an Optional record was a
  one-way door, exactly the finding #72/PB-20 made one level down about a scalar
  override.
  The fix is the row-deletion contract lifted one level: an Optional record is
  created by a named click and removed by a named click, and until it exists its
  fields are off the page behind a caption that says which ones — the same
  answer `_empty_table_note` already gave for an empty table, because it is the
  same question. Two structural points. It is stated for **every** Optional
  record block, not the one it was found on (rule 4): the set of them is read
  from the registry through `optional_steps`, there is no list in the GUI, and
  the parametrised guard
  `test_every_optional_record_block_is_added_and_removed_by_name` walks every
  one of them — detaching each, proving a render and a revisit attach nothing,
  then adding and removing by name. And the add writes *through* rather than
  into `_PENDING`, so the record-block half of the #35/CR-A-1 pending clobber is
  now unreachable rather than guarded: one click is one rerun, so two blocks
  cannot mint competing blanks. The pending path that can still race is the one
  `rows_at` walks, where two tables share a missing ancestor and neither is a
  click; `test_dirty_flag.py` says so where the CR-A-1 cases live.
  The evidence that the posture does not cost the GUI its job is the round-trip
  journey: it types both example airplanes into an empty project from nothing,
  performing exactly the clicks a user would — the answer page carries a record
  wherever it does not offer to add one — and still reproduces the reduced
  answer key byte for byte.

- **The crash was in the widget; the defect was in the loader (#121, tier M, 2026-08-29)** —
  The row was filed as a view bug: `select_input.full_down_aileron_deg` defaults
  to `None`, the registry's sentinel-default class (#98/C210-49), and
  `app/views/flight_envelope.py:345` dies on `float(None)`. Two thirds of that
  is wrong, and the correction is what moved the fix. The field is declared
  `float = 0.0` and is not in `field_registry.SENTINEL_DEFAULTS`; the oracle GUI
  cannot produce a `None` for it, because `form._clear_optional` writes `None`
  only where the annotation admits it. The `None` came from the **file**:
  `io._filtered` coerced numeric containers (#76) and declared scalars out of
  scope, so a JSON `null` was passed through to a field that had no such state,
  and every consumer downstream inherited it. The aileron field was the instance
  that surfaced; the class is every non-`Optional` scalar in the schema.
  That relocated the fix from the widget to the boundary, and the owner ruled it
  there. Hardening the ~137 `float(...)` calls in `app/views` would have covered
  one directory, left `oracle_app/`, the CLI and the calc modules holding the
  same `None`, opened the frozen views tree, and rotted at the next widget
  written; the loader is the one place JSON becomes a dataclass, so one guard
  covers all of it and covers a field added later on the day it is added
  (rule 3 + rule 4). `_reject_nulls` reads the nullable set off the annotations
  and is called from `_filtered` plus the ten readers that name their fields
  explicitly, so the rule has one owner and one message rather than a second,
  driftable copy — the same discipline `_coerced` took for #76.
  The refusal is deliberate, not a default. Reading the `null` as the field's
  declared default would leave the file and the loaded project disagreeing with
  nothing said, which is #122's silent zeroing wearing the other face — and one
  reader was already doing it: `fuselage_mass_from_dict` wrote
  `bool(d.get("stations_are_override", False))`, turning a `null` into `False`
  and an override the user had asked for into an override they had not. That
  came out of the guard's own sweep, not out of the report (rule 4).
  The gate is stated over the class in both directions, because closing either
  half alone re-opens the other:
  `test_a_null_is_refused_by_name_or_lands_as_a_meaningful_none` nulls every
  scalar leaf of every shipped example in turn — 3,591 of them — and allows only
  two outcomes, a `ValueError` naming the field or a round-trip that visibly
  changes, so neither a traceback nor a swallowed default can pass. A sweep
  asserting only "nothing escaped" would pass with every null defaulted, which
  is the lesson #122 wrote down. Two guards stand behind the refusal being safe
  to turn on: `test_no_model_field_defaults_to_none_outside_an_optional_annotation`
  fails the build the day a field is added that this app would write as `null`
  and then refuse to read, and `test_an_optional_field_keeps_its_null` pins the
  states where `None` is the answer.
  The row's remaining third — the `float(field)` sweep of `app/views` — is
  discharged as a guard rather than as 137 edits, and it found nothing:
  `test_render_survives_every_optional_blank` blanks every `Optional` scalar on
  the project (65–88 per example, read off the annotations, not off a fixture)
  and renders each view, and all 21 combinations pass. The views already handle
  their genuine blanks; the only `None` they could not survive was the one the
  loader should never have admitted. The half the row leaves open is unchanged —
  rendering the blank *as the oracle GUI does*, an empty widget with the derived
  value stated, is a layout question and stays with #29's freeze lift. The
  `app/views/` freeze was not opened: nothing under it changed.

- **Python 3.10 is the floor, and the support claim is one claim (#132, tier M,
  2026-08-28)** — 0.8.0's first full-matrix run on `main` failed at install on
  the 3.9 leg: `streamlit >= 1.51` (the #129 `width=` floor) declares
  `Requires-Python >= 3.10`, and the floor bump had verified the API but not
  the interpreter support behind it. The owner dropped 3.9 (EOL 2025-10;
  Streamlit dropped it at 1.51) over re-arming `use_container_width` on the
  plotly sites, and the fix made the support claim structural: `requires-python`,
  the trove classifiers and the `ci.yml` full matrix now state one set, guarded
  by `test_the_python_support_claim_is_one_claim_in_three_places` (classifiers ≡
  matrix, floor = smallest tested leg, mutation-verified both ways); the
  dependency-side half of the class stays with the full-matrix install on
  `main`, where this instance surfaced. Docs stating the matrix swept
  (`CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `00_program_overview.md`,
  `DEVELOPMENT_PROCESS.md`, `RELEASE_PROCESS.md`, `WORKFLOW_COMMANDS.txt`,
  `CONVENTIONS.md`); B905/RUF007 parked beside `UP` as deliberate churn.

- **Two one-way doors in the oracle GUI (#72, PB-20/PB-23, tier M,
  2026-08-25).** Both halves of this item were the same shape: a state the user
  could enter and not leave. An `Optional` override could be filled but never
  emptied, and a table row could be added anywhere but deleted only from the
  end — and because this GUI is the only editor its projects have, "edit the
  JSON" was not an escape from either. The review's fix for the first (write
  `None` when the widget comes back empty) was tested before it was written and
  does not work: a number-seeded `st.number_input` cannot be emptied at all —
  the frontend restores the last value on blur and `NumberInputSerde.deserialize`
  reads an empty submission as the seed — so no handling of the return path can
  un-fill a field, and the clear has to be an affordance. That made the fix
  structural rather than local: the widget's own state is the only door, it may
  only be written before the widget is instantiated, and the key it is written
  under is spelled two ways (the converted mode suffixes the active unit system,
  the fixed-unit and dimensionless modes must not, so a unit-agnostic number
  survives the switch). One owner now names that key for the widget and for the
  clear alike, so the two cannot drift into clearing a widget that does not
  exist. The row half turned out to carry the counter defect of #88 in mirror
  image: a deletion that does not re-size the row counter is undone by the very
  next render, which grows the list back up to the retained count and returns
  the deleted row as a blank — so the delete runs as a callback, which is the
  only moment a widget's state can be re-sized. Two smaller findings closed with
  them, both about the GUI saying nothing where it had acted: the Save-to-disk
  confirmation was emitted immediately before the `st.rerun()` that discards it,
  so the one action with an effect outside the session had never once been
  confirmed on screen; and a cleared required table cell restored its old value
  in silence, which is the right behaviour reading as the wrong one — a grid
  that ate the edit. The contract both halves now answer to is stated once, in
  `GUI_design.md`, beside the #35 rule it completes: unfilled is empty, a typed
  0 is real, **and the door opens both ways**.

## Step — Derive-by-default overrides: one mechanism for the duplicated-input class (#97, design note 36, tier L, 2026-08-27)

**Objective.** Close the eight C210 findings that were one defect class — an
input duplicating a value the project already holds, asked blank, with a silent
fallback or a silent skew behind it (C210-13/15/29-seed/31/36/38/39/41) — with
**one mechanism** instead of eight patches: falsy-means-derive /
typed-means-override at **calc level** (a blank field in any project file
derives, CLI and GUI alike — owner ruling), one named resolver per quantity,
the computed value shown beside each collapsed field, and a drift guard that
makes the mechanism the single-source owner rather than a convention
(design note `docs/40_history/39_derive_override_note.md`, agreed 2026-08-26;
decisions OV-1…OV-12, gates G-OV-1…G-OV-6).

**Deliverables.**
- **The resolvers (OV-2), each a pre-existing owned computation** — no new
  physics: `derived_geometry.planform_aspect_ratio` (the one AR spelling,
  OV-5; both strip sweeps now call it) with `wing_aspect_ratio(project)` for
  the h-tail's blank ARW; `taper_ratio_from_planform` /
  `tip_ratio_from_planform` feeding `airloads.resolved_tau` (the TAU
  resolution spelled once); `flight_envelope.gust_at_vf` (the GUST VF corner
  factor, same `_gust_load_factor`/`_gust_ude` internals — bit-for-bit) read
  by `flap.resolved_ng`; `select.wing_lift_slope_per_rad` (cruise C1 × 57.3),
  `select.effective_tail_inputs` and `select.resolved_full_down_aileron_deg`;
  `engine.effective_engine`/`resolved_engines` (LIMNZ ← `design_speed_values
  (project).n`; weight/CG ← the `engine_mass_item`/`prop_mass_item` row,
  matched with `same_name`, refused by name when absent — every engine
  consumer swept onto the one accessor: mount loads, LRA export, WINGGEOM
  stations, nacelle sketch, OEI, hub thrust, applicability); WTENV's
  `gross_weight or max_takeoff_weight(project)` (recursion-safe: the G-14
  reverse fallback reads the raw field only when non-zero); and
  `airloads.resolve_aero_surfaces` (a schema-default aero row per unpaired
  **symmetric** planform, per name, nothing written to the project — OV-8).
- **Schema v56 (OV-10):** additive `SurfaceInput.tip_cap_width_in` (OV-4 —
  the rounding the polylines cannot carry, entered once with the wing) and the
  two engine selectors; 55→56 **identity hop** (`migrations._hop_55`), floor
  55, examples re-stamped, fields hash updated, `DATA_DICTIONARY` regenerated.
- **Registry + GUI (OV-9/OV-11):** `field_registry.COLLAPSED_OVERRIDES` — the
  collapsed set enumerated once — with `derived_from` + a record-aware
  resolver in `EXTERNAL_VALUES` per path; `oracle_app.form._collapsed_note`
  renders "Blank — derives from ⟨owner⟩ (currently X)" / the override caption
  with a > 1e-9 disagreement warning, never disabled; the stall-CL rows
  register `normalize()`'s shipped fill-through (OV-3, C210-15 ruling text;
  `flaps_down.neg_stall_cl` stays the documented #81 gap).
- **Mismatch surfaced (G-OV-6):** `validation._check_derive_overrides` —
  `aileron_deflection_mismatch`, `engine_mass_row_mismatch` (> 1e-6, the
  consistency channel); the no-such-row refusal lives in
  `engine.selected_mass_row`.

**Test / Acceptance.** `tests/test_derive_override.py` (23 tests): G-OV-2
derive-equals-owner on ga6 with each field blanked in turn (rel 1e-9; NG and
LIMNZ exact — same call); G-OV-3 the defect dies, each test stating the
pre-fix failure (τ 0.206209 on a tapered wing, the bare ARW
`ZeroDivisionError`, the zeroed mount loads, the never-analysed surface);
G-OV-4 the OV-11 drift guard (every collapsed path linked and resolvable, no
owned-quantity copy without its link); G-OV-5 v56 round-trip + the v55 hop
(`test_migrations.py::test_a_v55_file_loads_through_the_identity_hop_unchanged`);
G-OV-6 the two warning codes and the by-name refusal. **G-OV-1:** the full
suite (2,918 tests) passes with every Appendix A oracle and twin closure
untouched; the only digest movement is `csv/airloads`/`txt/airloads` on the
four fixtures carrying unpaired htail/vtail planforms — the OV-8 seed
appending their spanwise views, wing blocks byte-identical (OV-12: where a
blank used to produce a silently wrong number, the number changing to the
derived one *is* the fix).

**Key decisions.** All owner-ruled in note 36: calc-level derivation, not a
GUI affordance (OV-1, no 0.0→None migrations — a falsy authored value is never
load-bearing in scope); the engine↔mass linkage as an explicit row selector,
never a role tag (OV-7); seeded aero rows carry geometry values only (OV-8;
#98's caption owes the visibility); the main GUI needs no change for
correctness — the calc derives for both front-ends — with caption parity
recorded against #29 (OV-9); `wing_weight_lb` and the SELECT copies (C210-22/
25) stay at #95 and wire onto this mechanism when that row lands.

## Step — The geometry-page presentation family: quantity-true placement and one summary shape per module (#95, tier M, 2026-08-27)

Ten C210 findings (C210-1/2/3/5/6/8/22/25/26/27), closed as three mechanisms.
**One summary shape, both channels:** `report.summary_rows` is the single
dispatch the module CSV, the oracle results page and Results Review all render
through (`SUMMARY_SHAPES`; CONVENTIONS §7 row) — SELECT one line per case with
its per-case SF via `critical_rows`, sharing `governing_loads_table`'s
one-line core so the M2-4 tables cannot diverge; WTENV one row per
(weight, station) point via `weight_station_rows`, paired on the machine
`LoadValue.key`; every other property module the data-shaped floor
(`results_to_rows` drops all-empty columns). The owner's CSV ruling made this
an accepted deliverable-format change: only the `csv/*` Imperial digests
moved — text, sbeam and index channels are byte-identical. **Derives and
disclosures on the #97 mechanism:** SE/SR blank-derive from their own hinge
halves with a 1 %-tolerance mismatch warning (the Appendix A inputs' own
rounding is 0.2–0.7 % and stays silent); the v-tail wing span blank-derives
from the WINGGEOM integrator's span, read through `effective_vtail_inputs` by
SELECT, ONENGOUT and the tail-span split alike; the 0 → 0.09·MTOW wing-weight
and rod-IZZ fallbacks are disclosed beside their fields and the SELECT block
captions both rod inertias against WTONECG's database values (C210-25).
**Placement and seeding:** `DISPLAY_GROUPS` renders a field on the page its
quantity belongs to (the h-tail record's wing aero with the aero data, the
SELECT trio each to its home) without moving it off its record;
`RECORD_SEEDS` offers the parametric wing from a typed planform behind a
button (GR-GEOM-3 — seeded and overridable, a visit never dirties the
project); `fuselage_length` renders disabled exactly while an outline exists.
Guards: `tests/test_summary_shapes.py` (10 tests, incl. the screen-equals-CSV
drift guards) plus the extended select/validation/configuration/registry
suites; the G7 CSV gate now requires the SF column exactly where a `-ULT`
column exists, since the always-blank SF on property tables was C210-27's own
complaint.

## Step #123 — The landing load factor is entered as N, not NLG (note 37, tier L, schema v57, 2026-08-27)

**Objective.** Kill a defect with a first-order effect on shipped output by removing its class.
`LandingInput.gear_load_factor` was an NLG override that superseded LGFACTOR's energy result;
because `VMP = ½·NLG·W·AP/DP` reads NLG and nothing else, an entered NLG made the wing lift
factor `L` **inert on the vertical gear reaction** — the user changed the lift assumption and
no wheel load moved — while the page kept reporting the *energy-derived* N the reactions were
not computed from, and the `0.0` sentinel gave "unset" and a legal value one encoding. Vertical
equilibrium at peak load is `N = NLG + L`: three quantities, one equation, two degrees of
freedom, and which two are inputs decides whether L moves the reaction. The fix inverts the
pair — **`N` and `L` are the inputs; `NLG = N − L` is derived, reported, and never entered.**

**Deliverables.**

- **`landing.governing_load_factors`** — the one owner of the governing pair: entered `N`
  (`LandingInput.airplane_load_factor`, `Optional`, no sentinel) when filled, else the energy
  value; `NLG = N − L` derived nowhere else; `N ≤ L` refused by name (LF-5 — with the L cap
  gone, the only guard between `K = NAP/NLG·K0` and a zero or sign-flipped NLG).
- **The `L ≤ 0.667` refusal and widget cap removed** (LF-4): 0.667 is FAR 23.473's default and
  1.0 the FAR 25.473(a)(2) basis; both GUIs caption them as guidance through one shared string
  (`app_shell.components.LANDING_L_FAR_CAPTION`).
- **The 23.473(g) floor policy** (LF-6, one owner + drift guard, practice 3):
  `landing.far23_473g_floor_violations` with the floors in `constants.py`; a governing pair
  below `N ≥ 2.67` / `NLG ≥ 2.0` is a named refusal in a FAR 23 category (`build_landing`) and
  a warn-only note in concept (`run`), superseding the M2-8 concept-only warning.
- **Schema v56 → 57, semantic hop** (LF-8): `N = gear_load_factor + lift_factor` where the old
  override was non-zero, else unfilled; the old key is dropped. The hop reproduces every NLG
  the reaction path read, so no load number moves (LF-11). `ga6_normal`/`cessna_210` carry
  `N = 3.167` (LF-9 — p230 reproduces at NLG 2.5 and at no other value); the three concept
  examples are set to `N = 2.67`, not the hop's 2.6670 (LF-10 — a 0.11 % rounding artifact
  would have started three shipped examples warning on nothing real; NLG moves +0.15 %, the
  only moved numbers in the fleet). `field_registry` row replaced with origin `SLOADS`,
  `supplied` (demonstrably load-bearing, G5): LGFACTOR.BAS had an NLG override, never an N
  input (LF-12).
- **Both GUIs** (LF-7): `app/` seeds N from the computed energy value with a "Computed N
  governs" checkbox as the way back; the oracle GUI renders the unfilled Optional with
  "✕ clear" and a landing group note stating the computed → governing pair. `NLG` renders as a
  derived output in both; `landing.below_energy_caution` (one owner) fires when the entered N
  undercuts the energy value. The module output gains governing-N/NLG rows beside the
  oracle-locked energy rows (the S2 fix at the deliverable, not only on screen).
- **Docs.** `PROGRAM_SPEC.md` §LGFACTOR/§LANDLOAD rewritten (including the sentence that
  recorded the split as intended behaviour); `theory_sources.md` grown the FAR 23.473(g) /
  25.473(a)(2) lift-basis row and the governing-pair citation; the schema ledger
  (`test_schema_guards.py` + `project.py`) records v57; `DATA_DICTIONARY.md` and the guide
  tables regenerated; guide chapter 14 rewritten with its screenshot recaptured. Note 37's two
  arithmetic slips corrected in place, marked as implementation corrections (LF-5's inverted
  refusal; G-LF-2's K/γ figures).

**Test / Acceptance (gates G-LF-1 … G-LF-6, all in CI).**

- **G-LF-1 (oracle invariance):** the p236 Appendix-A assertions pass unmodified —
  `landing_load_factor` is untouched (LF-3); p230 passes with ga6 at `N = 3.167`.
- **G-LF-2 (L moves the reaction):** on ga6 at fixed N, raising L 0.667 → 1.0 lowers NLG
  2.500 → 2.167 and every case-4–12 VMP by exactly 2.167/2.5, and raises K to
  `(3.167/2.167)·0.256133 = 0.3743` (γ 20.52°); the pre-fix behaviour — no change at all — is
  in the test's docstring.
- **G-LF-3 (N recoverable from the reactions):** `NVP == N` exactly (rel 1e-9) on cases 4–9
  and `NVP == ½·NLG + L` on 10–12, for every bundled example.
- **G-LF-4 (the guards):** `N ≤ L` refused by name; the floors block in FAR 23 (energy-governed
  *and* entered-N paths) and warn in concept; the floor constants drift-guarded; all six
  examples pass their own category's rule.
- **G-LF-5 (schema round-trip):** the frozen v56 fixture hops to `N = 3.167` with the old key
  gone, the `0.0` sentinel loads to unfilled, `applied_hops(56) == [56]`, and the migrated
  project's 33-case matrix is bit-identical to the current fixture's.
- **G-LF-6 (both GUIs):** the caption enumerated once and consumed by both GUI sources
  (guarded); the below-computed-N caution fires on `cessna_210` (3.1670 vs 3.3885) and not on
  ga6. Imperial digests deliberately regenerated: landing channels on all fleet examples (the
  new governing rows), balance/gear/deck channels on the three concept fixtures only (the
  LF-10 nudge) — ga6/cessna/baron load channels byte-identical, as LF-11 promised.

**Key decisions.** LF-1 … LF-12 in `docs/40_history/40_landing_load_factor_note.md` (AGREED
2026-08-27); implementation choices in session: energy + governing rows both reported (not
governing-only), one solo-close commit, floor policy homed in `modules/landing.py` with
constants in `constants.py`.

## Step — Hidden required fields rendered or captioned (#98, tier M, 2026-08-27)

The `_SLDS`-origin filter hid fields the user must state (C210-46/49/29): every
tab silently defaulted to the h-tail because `tab_loads.tabs[].surface` was
never rendered, an oracle-built project could not export ground cases because
both gear legs' `carrier`/`attach`/`weight_lb` were hidden with sentinel
defaults, and an empty `aero.surfaces` list showed a bare rows counter with no
trace of the AIRLOADS block behind it. The fix is two structural classes rather
than three patches (rule 4): **row selectors** — a `name`/`surface` leaf on a
list record, which a page can never resolve positionally — are rendered
(`supplied=True`, selectboxes over `models.inputs.TAB_SURFACES`/`TAIL_SURFACES`)
with unknown surfaces refused by name (`require_surface`; the silent
`_TAB_COMPONENT.get(..., "wing")` fallback and the silently-inert `tail_mass`
row died with it), guarded by
`test_field_registry.py::test_a_list_row_selector_is_always_asked`; **sentinel
defaults** are registered in `field_registry.SENTINEL_DEFAULTS`, rendered, and
guarded by `::test_a_sentinel_default_field_is_always_asked`; and the empty-list
caption is generated from the page's own field set at `render_table`'s one early
return, so every empty list gains it and it cannot drift. Every new `supplied`
mark carries a G5 demonstration in `tests/test_oracle_inputs.py` (the tab
misroute, the override that went nowhere, the unmatched aero row's refusal, the
carrier warning, the omitted gear node, the open free body); the supplied-ratio
dial moved 10 % → 15 % with the reason stated. SSOT row: `CONVENTIONS.md` §7.

**#99 — Oracle page placement and the validation/error-display pair
(2026-08-26).** The first 0.8.0 item, four C210 build-review findings sharing
one page and one channel. Placement (C210-37/44): the aileron/flap planform
geometry and the engine layout are configuration, so their registry rows are
re-tagged to the Geometry page and sit beside the empennage forms — the slices
do not move (the single-consumer pattern stands), the oracle page set being
registry-derived makes the move a tag, and
`test_control_surface_planform_geometry_renders_on_the_geometry_page` guards
the decision; the Aileron Loads page becomes results-only and says so through
the existing no-input branch. Validation (C210-21/14): the load-bearing-zero
class gets the `cg_case_without_weight` treatment — `build_envelope` refuses a
0/unset `xtc`/`xtf` by name for exactly the configs that would read it, with
`tail_cp_station_unset` warning on the page first — and
`landing_light_not_lighter` closes the role-contradiction gap the M4-17d
hierarchy checks left at the equal-weight boundary. Display (C210-24): the
not-ready catch keeps its one-liner, adds the exception type, and carries a
module:line-first traceback into an expander, closing the display half of #71.

## Step — The oracle GUI user guide (#96, note 34, tier M, 2026-08-27)

Design note 34's guide built to plan in the six UG-10 stages, gates first:
`docs/60_guide/` with generated field tables (`docs/generate_data_dict.py` →
`_generated/`, UG-3), workflow-derived chapter order (UG-7), Playwright
screenshot capture (`scripts/capture_guide_shots.py`, UG-4), fourteen
eight-section chapters, front matter carrying the single LIMIT/ULTIMATE
statement (UG-8), and the two end-to-end appendices — `ga6_normal` in
Imperial against the printed Appendix A checkpoints, and the new
`examples/baron_58.project.json` (UG-9: TCDS-sourced Baron 58, every
estimate marked in its sources register) worked entirely in SI and closed
on the channel-free stored project (UG-12). Gates G-UG-1…G-UG-6 landed in
stage 1 and checked every chapter on arrival (`tests/test_guide.py`); the
twin joined the oracle-reduction `EXACT` set and the ground-coverage pin.
Two latent defects the twin exposed were filed with bodies the same session
(#121, #122). `GUI_USER_GUIDE.md` stays the full-app guide (UG-2), now
cross-linked both ways.

- **Page-order dependencies are declared and stated; the non-owner mark reaches
  external owners and composites (#69 + #89, tier M, 2026-08-25)** — Two defects with
  one root: the GUI knew a thing about a field's provenance and did not say it.
  `WorkflowStep` gains `reads`, the slices a step's numbers depend on that neither
  gate the run nor are entered on the page, and `app_shell.components.render_page_order_reads`
  states them on every visit — caption when the dependency is filled, warning while it
  is not. The instrument matters: `requires` blocks, and the flap and weight-estimate
  calcs are correct with no engine at all, so enforcing would have refused a valid
  glider run to fix a page-order problem. Declaring and stating leaves the calc alone.
  The dependencies were found by sweeping every step's modules by AST rather than from
  the two reported instances: seven across four steps, and that sweep is now the guard
  (`test_every_page_order_dependency_is_declared`), with a reverse test failing on a
  stale declaration. On the marking side, `_copy_note`'s early return on
  `owner_is_external` is gone — all six EXTERNAL rows are captioned with their owner in
  words, never disabled (the owner is an expression, and one of them is the calc's
  fallback), and a new `FieldEntry.resolves` carries the true sentence where `governs`
  alone would state the rule wrongly. Marking them exposed #89's latent door in the
  same session: `engines[].engine_cg` is a tuple, and the mark only ever reached
  scalars, so `render_field` now forwards the project to every branch. The render guard
  counts marks per owner phrase rather than searching for it once — two fields on the
  Engine Mount page name the same external owner, and a substring test passed while the
  tuple beside the scalar rendered bare. `st.columns(0)` guarded with it. No calc
  changed: the Imperial baseline digests and every oracle are untouched.

## Step #93 — Pre-production schema floor: read only the current `SCHEMA_VERSION` (tier L, 2026-08-25)

**Objective.** Stop carrying compatibility this project does not need. `sloads/migrations.py`
migrated any file from v18 up through twelve shape hops, plus a v0 bare-`EngineInput` branch —
632 lines of code and 439 of test guarding the ability to read files written by builds that
never shipped to anyone. Pre-production, no prior analysis has to stay readable. The floor
moves to the current version and everything below it goes; the hop *machinery* stays, empty,
so the first post-production shape change registers a hop unchanged.

The item was raised by the owner at the close of #68, which had just fixed the GUI's migration
notice. That fix is what surfaced this: the notice could only ever have fired on the six
bundled examples, which had sat at v41 for fourteen versions and ran hops 43, 46 and 54 in
memory on every load. The repo's own fixtures were the only prior-schema files in existence.

**Deliverables.**

- **The examples re-stamped at v55, first, through the chain still standing.** `migrate(raw)`
  written back at the same `indent=2`, so the diff is only what the hops touch (16–111 lines
  per file, nearly all the v46 cg-case reshape) and the hand-authored key order survives.
- **`migrations.py` rewritten as a gate.** `MIGRATIONS = {}`, `SUPPORTED_FLOOR =
  SCHEMA_VERSION`, and `migrate` raising the new `SchemaVersionError` — a `ValueError`, so it
  lands in the documented error contract and every front-end's existing load handling reports
  it with no new branch — for anything older, newer or unversioned, naming both versions.
  `source_schema_version` moved here from `io.py` and now answers `-1` for an unversioned
  dict rather than defaulting it to the floor: an unstamped dict is not an old project file,
  it is one nobody wrote as a project file, and the gate has to be able to say so.
- **One decider.** The gate sits inside `io.project_from_dict`, the funnel CLI, both GUIs and
  every test load through. `io.schema_status`, `app_shell.project_state.apply_schema_check`
  and the JSON editor's copy of the same classification are deleted; `safe_load` keeps the
  dict-reader signature #68 gave it and reports the refusal through the error path it already
  had. `read_project_dict` stays — that split was right for its own reasons.
- **The v0 bare-engine branch and `is_project_dict` retired.** A dict with no
  `schema_version` is refused by the gate, which discriminates a foreign file better than the
  key-set intersection did, and the reader no longer makes the distinction at all.
- **Eleven frozen legacy fixtures deleted**, leaving `tests/fixtures_schema/v55_current.json`.
  The tests that read them were re-homed rather than dropped where the property under test
  outlived the hop: the fuselage-outline defaulting, the empennage slice properties and the
  absent-`unit_system`-is-Imperial rule are now written against current-schema dicts, because
  none of them was ever about the vintage.
- **Docs.** `PROJECT_GUIDE.md` §5 (the rule, and what changing a persisted dataclass now
  requires), `00_program_overview.md`'s error-handling table, `GUI_design.md` §10's load path,
  `CONVENTIONS.md`'s SSOT row for the two twice-persisted quantities (its guard cited a hop
  test that no longer exists), `PROGRAM_SPEC.md`'s cg-case note, and the fields-hash
  tripwire's own failure message, which told the next developer to write a hop.

**Test / Acceptance.**

- Output-neutrality of the re-stamp proved two ways before anything was deleted: the `Project`
  loaded from each pre-regeneration file and from its replacement are **identical dicts**, all
  six fixtures; and `tests/fixtures_imperial/digests.json` — every deliverable channel of every
  example — did not move. Decision **G-3b**'s own guard (the `FLIGHT`-tagged set equals the
  pre-hop `flight_loads.cg_cases`) was re-run against the pre-regeneration files and passed on
  all six, flight and ground, then retired with the hop it guarded.
- **New structural guard (rule 3):**
  `test_schema_guards.py::test_every_bundled_example_is_written_at_the_current_version`, read
  off **disk** rather than off a loaded `Project` — asking the built object is precisely the
  #68 defect and would make the test vacuous exactly when it matters. Mutation-tested by
  re-stamping an example at 41.
- **Second structural guard:** `test_app_shell.py::test_no_gui_decides_whether_a_file_is_readable`,
  an AST walk for the names that do the deciding (`schema_status`, `source_schema_version`,
  `SCHEMA_VERSION`, `SUPPORTED_FLOOR`, `migrate`, `MIGRATIONS`) anywhere under a GUI or the
  shell. Reading `project.schema_version` to *display* it, as the dashboard metric does, is
  not deciding and is not flagged. Mutation-tested by importing `SCHEMA_VERSION` into
  `app_shell/project_state.py`.
- `test_migrations.py` rewritten as the gate's tests: refusal in both directions and for an
  unversioned dict, the string-version trap, the refusal reaching a front-end through
  `project_from_dict`, and — so the kept machinery is not decorative —
  `test_a_registered_hop_still_runs`, which registers a hop, watches it fire, and unregisters
  it.
- Whole suite green; net ~1,100 lines removed.

**Key decisions.**

1. **Refuse, do not warn, in both directions.** The old chain let a *newer* file through on
   "read what you understand". Pre-production that means presenting a partial read of another
   build's schema as this build's answer, which is the same dishonesty as silently upgrading
   an old one.
2. **Keep the chain, empty.** Deleting the mechanism and rebuilding it from git history at
   production would be a second design exercise for no saving; `MIGRATIONS` and `applied_hops`
   cost nothing standing still, and the reversal is two edits — lower the floor, register the
   hops.
3. **The examples are the floor's only customers, so the guard is on the examples.** With
   `SUPPORTED_FLOOR == SCHEMA_VERSION`, a stale example is not a compatibility question but a
   broken example: the app would refuse to open its own bundled projects. That test is what
   makes the next version bump safe.
4. **The retired hops are recorded, not merely deleted.** The archaeology table that
   reconstructed which schema version each legacy path belonged to (M4-10) stays in
   `docs/40_history/11_completed_development_to_0.5.0.md`, and `migrations.py`'s docstring
   points at it.

- **Flutter clearance leaves the tool, and the register learns a third category
  (#79, C210-19, tier M, 2026-08-26)** — MACHLIM printed a flutter-clearance Mach
  `MFC = 1.2·MD` and its per-altitude `V(FC)` because `MACHLIM.BAS` does, and this
  project's default is to replicate what the manual prints. The owner's directive at the
  Cessna 210 build review reversed that here on two grounds: flutter substantiation is
  23.629 rather than a design load, so nothing downstream sizes to it; and the symbol is
  actively misleading to the Part 25 audience this tool now serves, who read `VFC`/`MFC`
  as §25.253's maximum-speed-for-stability pair. A quantity nobody uses, under a name
  that means something else, is worse than an absent one. Removed from the calc, the
  report series, the workbook column, the Speed–Altitude chart and the theory document;
  MNE and the V(MC)/V(MNE)/V(MD) lines are untouched and still oracle-locked, which is
  why this was surgery rather than a sweep — both quantities live in the same six lines.
  The interesting part is the record. Dropping a printed Appendix A output is not an
  approved *correction*: the corrections register exists to say "the manual is wrong and
  here is the right number", and Appendix A's MFC 0.4836 is the right answer to the
  equation the original program runs. Recorded under a new **Withdrawn from scope**
  heading that states the difference explicitly, so a later reader cannot mistake a
  narrowed replication for a fault found in the source. The drift guard is an AST scan
  over every shipped package rather than a test of the module's output, because the
  quantity was computed in two places — `mach_limit.py` and the main GUI's chart, which
  carried its own `1.2 * md` — and removing only the first would have left the line still
  drawn from a local copy. That is the same shape as the defect the removal was about.

- **A sidebar that does the arithmetic the build was doing by hand — and one
  answer to "which MAC?" (#80, C210 build review 2026-08-23, tier M,
  2026-08-26)** — The row asked for two conversions; building them found a
  defect underneath. The %MAC↔station relation was spelled four times across the
  calc package, the report and a view, and the spellings had quietly diverged
  not on the arithmetic but on the reference: WTENV honoured the weight
  envelope's typed XLEMAC/MAC override, the report's `% MAC` column read the
  planform regardless, and the two are drawn on the same chart. `mac_reference`
  now resolves that once — override, else planform (the C210-13 blank-derive
  fallback) — and carries which of the two it was, so a display can name it; the
  relation and its inverse live beside it, with an AST drift guard over every
  shipped package, and the aerodynamic consumers pass a planform reference
  explicitly rather than resolving one. The airspeed half needed the same
  completion in miniature: `convert_airspeed` only ever ran from KEAS, so the
  conversion a user actually has to make — from the KCAS on a POH or a placard —
  had no owner until `eas_from_airspeed` inverted it exactly. Both Tools are
  display-only and both delegate to those owners: the no-dual-path rule holds
  for a sidebar as firmly as for a page. Nothing in the frozen Imperial baseline
  moves, because no shipped example carries the override that made the two
  frames disagree — which is precisely why the guard builds one that does.

## Step — TAILDIST states the aero state of each case it distributes (#100, note 35, tier L, 2026-08-27)

**Objective.** Close C210-32 (owner directive: "record the alpha, beta and
rudder or elevator deflections for each case" in TAILDIST, with the
slope/effectiveness intermediates once per component): the aero state that
produced each distributed tail case was computed upstream and discarded — for
several conditions not even computed loose — and the page that distributes a
case could not say what state made it.

**Deliverables.**
- `CriticalCondition.alpha_tail_deg` / `delta_deg` / `q_psf` (AS-1): additive
  `None`-default **result** fields beside L-7's `beta_deg`; `io.py` reads
  them with the same `d.get` pattern, no migration hop, `SCHEMA_VERSION`
  unchanged (AS-7, the `beta_deg`/`body_axial_clamped` ledger class).
- Every SELECT tail emitter publishes the state its method actually used
  (AS-2): balancing the balance AT and moment-balance δ (the same locals as
  the loose oracle-checked `LoadValue`s, AS-6), unchecked the trim AT plus
  the signed full throw, checked and gust the trim state (the labelled
  increment is what separates trim from total), the unsymmetrical case a copy
  of its governing source; v-tail fin AoA 0 / −19.5 / −15 / −gust-β with the
  rudder throw, and q stamped centrally in `_htail_condition` from the
  governing point itself.
- `TailChordResult` carries the four fields across; TAILDIST renders them
  ahead of the stations (`taildist.aero_state_values`) with the AS-4 fixed
  reasons where a method defines no value (checked δ, side-gust q, h-tail β)
  and the "re-run SELECT" statement on a stale persisted set; angles and q
  are non-load units, never SF-scaled (CONVENTIONS §3).
- `taildist.component_constants`: AHT (h-tail) / AVT + EFFECTV (v-tail)
  printed once per component by calling the same owners inside the loads.
  The finite-surface slope `2π/(1+2/AR)` consolidated to
  `_vtail.lift_curve_slope` (AS-5) — the three inline `select.py` spellings
  replaced by calls, ONENGOUT renamed onto the shared owner.
- Docs: `theory_sources.md` `select`/`taildist` rows grew the published-state
  sentences; `PROGRAM_SPEC.md` TAILDIST section; the schema-guard ledger
  entry.

**Test.** `tests/test_taildist_aero_state.py` — G-AS-1: on the Appendix A
GA6, `BAL UP RETRACTED`'s structured fields equal the loose `LoadValue`s
bit-for-bit and δ matches Appendix A's −5.39° (Ch 9 case 202). G-AS-2: on
every shipped fixture the published state reconstructs the stamped
`LT25`/`LT50` through the method's own equations (rel 1e-9, per family).
G-AS-3: every TAILDIST condition states each of AoA/β/δ/q or its AS-4
reason. G-AS-4: a stale persisted set renders the "re-run SELECT" statement,
never a value. G-AS-5: the §1 per-label literals plus the one-spelling slope
drift guard. AS-8 (no load number moves) is the rest of the suite: only the
`csv/taildist` / `txt/taildist` digests changed.

**Key decisions.** The published state is the state the method used, never a
derived "total effective" one — the equivalent-gust-Δα extension is parked
with the owner's ruling (`02_parked.md`). Disclosure reasons are fixed
strings owned by `taildist` (AS-4), so "cannot supply" is a statement, not a
blank. Reading the slope/effectiveness owners from TAILDIST is not
recomputing another module's quantity (the `surface_geom` precedent); making
the slope single-source is what guarantees the printed intermediate is
arithmetically the one inside the loads (rule 3).

- **Two GUI copies that told the truth about the wrong number (#70, PB-16/PB-17,
  2026-08-25).** Both halves of this item were the same failure in different
  clothes: a widget stating something about the analysis that the analysis did
  not do. The unit radio was exempted from the project-generation stamp on the
  stated grounds that stamping it "would reset the user's unit choice on every
  project they open" — which is precisely what it is for, because `unit_system`
  is a field of `Project`; the exemption was argued from the widget's subject
  matter rather than from where its value lives, and the result was that loading
  an SI file into an Imperial session edited the file on the way in and flagged
  it unsaved. The wing-area copy was registered against
  `geometry.parametric.wing_area_sqft` while STRSPEED integrates the
  `speeds.wing_surface` planform, so the disabled widget — a widget whose whole
  claim is "this is what the calc uses" — displayed 500.0 against the 497.75 in
  the answer. Fixing the second exposed why it was possible: four separate
  implementations of the same strip integral, guarded by a sweep that scanned
  `sloads/modules/` alone and allowlisted two of the four, so `validation.py`
  grew a third outside its view and the GUI a fourth number that was not the
  integral at all. The integral now has one owner (`planform_area_sqft`), the
  callers keep only their policy for an absent planform, the sweep covers the
  package, and the registry can resolve an external owner's value through the
  same function the calc calls (`EXTERNAL_VALUES`) — which also made the row's
  conditional nature expressible: with no wing surface the field stops being
  inert and becomes what STRSPEED reads, so it goes live rather than staying
  disabled against the advice of its own `MissingInputError`. Two smaller
  defects came out with them, on the generalize-on-first-find rule: the
  wing-area mismatch warning was tagged for Configuration & Layout twice, so
  that page said it twice and Design Speeds never; and captions quoting an
  owner's current value quoted it in Imperial beside a widget rendering SI.

- **The weight estimate says what reads it, and stands beside the weights the project uses (#78, C210-9, tier M, 2026-08-26)** — The Cessna 210 build stopped at the weight-estimation block and asked three questions —
what does this feed, is it either/or with the item table, are the two compared — and the
page answered none of them (C210-9). The answers were "nothing", "no" and "no", but they
were only recoverable by reading the code: `PROGRAM_SPEC` said WTESTIMA *feeds* WTONECG
and WTENV, which is true of the original suite's data flow and false of this
implementation, where the flow runs through a weight data base the user authors and the
estimate reaches it only through a seed button. Fixed at both ends — the module now owns
the sentence (`weight_estimate.ADVISORY`) so both front-ends and the spec say the same
thing, and `compare_with_itemized` puts the estimate beside the weights the project
actually uses, drawing each entered figure from its existing owner rather than re-summing
the item table. The comparison is deliberately unthresholded: a GA correlation and a
weighed airplane are not expected to agree, +22 % on the C210 is scatter rather than
error, and a page that ruled on the gap would be answering a question the finding did not
ask. The other half of #78 — the seed button — turned out to have shipped long before the
review that filed it as missing; what survives there is that its rows arrive silently
zero-stationed and untagged and that it wipes an authored table, which is main-GUI work
behind the `app/views/` freeze.

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

## Release cut: **sloads 0.8.0** (oracle-GUI development: derive-by-default, the user guide, and the landing load factor entered as N), tag `v0.8.0`, 2026-08-28

**Objective.** Close band B — **oracle-GUI development**, the plan the 0.7.2
re-cut set — and cut when it is empty. The band was extended twice in flight by
owner ruling: 2026-08-27 with the landing load-factor defect and its sweep
finding (#123/#124, note 37), and again the same day with the four cut-blocking
rows of the
[production-release review](../50_reviews/2026-08-27_oracle_gui_production_review.md)
(#126–#129). 27 issues closed on the milestone.

**Deliverables** (the `[0.8.0]` changelog section is the release note):
- **Derive-by-default overrides** (#97, note 36, tier L, schema v56): one
  mechanism for the duplicated-input class — a field the calc can derive is
  derived unless overridden, the registry's `derived_from` links drift-guarded;
  **#98** rendered or captioned every hidden required field over it, and
  **#95** re-shaped the geometry pages' presentation on the same mechanism.
- **The oracle GUI user guide** (#96, note 34, tier M): six stages, chapters
  1–14, both worked-example appendices (the C210 and the guide-built
  baron_58) — the build that surfaced #121/#122, both filed with bodies
  (rule 5) rather than fixed in the writing session.
- **The landing load factor is entered as N, not NLG** (#123, note 37, tier L,
  schema v57 — a *semantic* hop: `N = gear_load_factor + lift_factor`, old
  saves migrated by key). The wing-lift factor moves the gear reaction again;
  the Appendix A p236 oracles pass unmodified (G-LF-1). Its HP-precedence
  sweep finding closed as **#124**: one owner for the max-continuous-HP rule,
  read by module and GUI alike.
- **The production-release review and its blockers**, all tier S, closed
  in-band: **#126** the Tools %MAC↔station input through the unit boundary;
  **#127** the smoke gate boots *both* front-ends (the release whose headline
  was the oracle GUI had a §3.5 gate booting only the other one); **#128** a
  design note's status cannot claim unbuilt work (notes 32/35 corrected, the
  claim guarded); **#129** the `use_container_width` migration taken whole
  (73 sites, both GUIs and the shell), the Streamlit floor moved to the layout
  API the code calls, and the **dependency ceiling policy stated**: no upper
  bound, deliberately, resting on CI's unpinned install — all three halves
  drift-guarded.
- **Maturity stated once:** `Development Status :: 4 - Beta` (the classifier
  describes the whole distribution) with the owner's mixed-state sentence in
  `app_shell.components.RELEASE_STATE`, consumed by both GUIs' About panel and
  pinned verbatim in `README.md`/`CAPABILITIES.md` by the doc-currency guard.
- **Also in the band:** the pre-production schema floor (#93, tier L — read
  only the current `SCHEMA_VERSION`, migrations become a gate); TAILDIST
  states the aero state of each case it distributes (#100, note 35, tier L);
  flutter clearance leaves the tool (#103); the sidebar tools section; the
  page-order dependency statements; and the oracle-GUI defect closures of the
  cycle (#70, #72, #76-class residue, #78's advisory caption among them).
- **Version** `0.7.2` → **`0.8.0`** (MINOR: new GUI capability). **Schema v55
  → v57** in two recorded hops (v56 additive, v57 semantic), older saves
  loading through both.
- **Changelog cut** — `scripts/build_changelog.py 0.8.0 --date 2026-08-28`:
  **39 fragments** consumed into `## [0.8.0]` across Added / Changed / Fixed /
  Removed, **14 history entries** rolled to the top of this file, a fresh
  empty `[Unreleased]` opened; released sections byte-untouched.
- **History roll** (`RELEASE_PROCESS.md` §4.3): notes **35, 36, 37** carry
  *SHIPPED* status headers and move to `40_history/`; notes 32/34 read
  AGREED…BUILT and stay with their open GUI milestones. The live file stands
  at well under the 1,500-line threshold — no freeze.
- **Verification baseline:** unchanged from
  [`36_verification_baseline_0.7.0.md`](36_verification_baseline_0.7.0.md).
  No calc-math change on the FAR 23 path: the one semantic change (landing N)
  is oracle-invariant by its own gate (G-LF-1, p236 assertions unmodified) and
  the delivered-load consequences are pinned by G-LF-2…G-LF-6 rather than by a
  new baseline.
- **Gates at cut:** `pytest` **3060 passed / 30 skipped / 1 xfailed / 0
  failed**, `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/
  scripts/` clean, `mypy` clean (`sloads/`), `scripts/smoke_test.sh` **PASS**
  (both front-ends boot, the oracle through its console script),
  `scripts/backlog_issues.py check` clean, no open CRITICAL/MAJOR review
  findings.

**Key decisions.** *The review ran before the cut started this time.* 0.7.2's
lesson — a release nearly cut is not cut — became 0.8.0's process: the
production-release review was commissioned against the release *claim* ("oracle
GUI production ready") before any cut step ran, found the claim four small
fixes short, and every blocker closed in-band with its structural guard. The
classifier ruling (`4 - Beta`) chose the honest whole-distribution statement
over the flattering per-front-end one, and put the sentence that carries the
nuance under one owner. The ceiling-policy ruling took the
`use_container_width` migration **whole** across both GUIs — splitting it by
fix site would have left half the removal bomb armed — and recorded "no upper
bound" as a decision with the CI mechanism that makes it safe, not an
omission. **Band B retired with the cut; band B2 (0.9.0 — main-GUI
development, anchored by #29) is the milestone in flight.**

