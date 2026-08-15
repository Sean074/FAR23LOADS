# Critical review — the 0.6.0 candidate (2026-08-15)

**Charge:** critical review of everything shipped since the **v0.5.0 tag**
(2026-08-13), with a stated emphasis on the project documentation being
(a) up to date, (b) correct and (c) full coverage for the features added.
Conducted per [`CODE_REVIEW_PROCESS.md`](../10_standard/CODE_REVIEW_PROCESS.md):
a documentation audit over the whole `docs/` tree plus `CHANGELOG.md`, and an
adversarial pass over the new physics, gates and schema work — deepest on step 10
piece 3 (the newest and least-reviewed change), gate-and-trail verification on
the earlier commits, which each closed with their own session trail.

**Scope — the nine commits since the tag:**

| commit | change | tier |
|---|---|---|
| `51dfb73` | ONENGOUT fixture data: turboprop shaft power; turbofan recorded as a limitation | M |
| `fa41856` | Case identity ↔ deck `LOAD` id linkage (design note 17) | M |
| `1f9a73b` | A wing case row states the flight condition its loads were computed at (D-23) | M |
| `54a49d2` | **Step 9** — discrete control surfaces, the suite's first hinge moment, the T-tail transfer (plan 09 T6–T8) | L |
| `1dde92d` | Pressurization removed from scope (D-24) | S |
| `167b0a1` | Ground-loads design note (plan 18, decisions G-1…G-14) | — |
| `aff1646` | **Step 10 piece 1** — the governing safety-factor table (M4-8 / G-11) | L |
| `f72d337` | **Step 10 piece 2** — the weight/CG case model + gear inputs (schema v47) | L |
| `42ee49e` | **Step 10 piece 3** — ground/landing cases + the gear load report (schema v48) | L |

**Gate state at review time:** `ruff` clean; **1670 passed / 21 skipped**
(all 21 are reasoned fixture-shape skips); the real-solver round-trip leg
**60 passed in ~16 s** with the ground cases in; working tree clean at `42ee49e`.

---

## 0. Verdict

The release candidate is in substantially better shape than 0.5.0 was at its
review, and the process machinery installed since 2026-08-05 demonstrably worked
during this cycle: every one of the nine changes has its CHANGELOG entry, its
tiered history entry and its backlog removal; the three declared digest waves
match their predictions exactly (piece 2's "nothing moves" held; piece 3's
movement set is byte-for-byte the one G-13 predicted); the F-R2 section-numbering
owner absorbed a report-section insertion (§8) with zero manual reference fixes;
and two real defects (the side-family loading mislabel, the `is_handed` net test)
were found *by* the new work's own gates and filed with bodies in-session.

The findings concentrate in three places:

1. **The newest deliverable channel is not yet held to the suite's own output
   contract.** The gear report CSV carries no `-ULT` unit markers, no per-case
   `SF` column, and one flat-out wrong header in SI — everything its sibling
   channels were made to carry over the last two releases (R6-C2).
2. **One promised gate half is missing.** G-6's rotational check
   (`Iyy·θ̈ == PITCHP + lift term`, etc.) was committed to in the design note and
   not implemented; the ground cases' angular accelerations have no independent
   check (R6-T1).
3. **Documentation currency slipped in exactly the low-tech places** — a
   misplaced CHANGELOG heading, a stale plan status, a narrative that omits two
   post-tag changes, and an index entry never made — while the *hard*
   documentation (CONVENTIONS, theory citations, the gear_loads spec section)
   is current and correct.

Nothing found moves a shipped load number. The FAR 23 oracles are intact, the
concept-mode gates hold, and the G-6 translational identity — the step's
benchmark — is exact on every case of both fixtures.

---

## 1. Findings — output correctness (C)

### R6-C1 — Ground condition rows in the balance module result carry FAR 23.321 **[M]**

`balance.run()` derives each row's `far_reference` as:

```python
far = (... ) if (lateral or unsymmetrical) else ("23.349" if c.unbal_moment else "23.321")
```

A ground case is neither lateral nor unsymmetrical nor rolling, so every one of
the up-to-27 assembled ground conditions renders with **FAR 23.321** — the
*flight* balancing-condition reference — in the module result, the load-case CSV
and the Results Review page. Verified:

```
'Balanced case 3-wheel level landing (V-n 1, aft max landing)' | FAR 23.321
case_ref far: 23.479(a)     ← the CaseRef itself is correct
```

The case's own `CaseRef.far_reference` (23.479(a)/23.481/23.483/23.485/23.493)
is right everywhere identity flows through it (deck map, case index, gear
report), so this is a display-row defect, not an identity one — and the safety
factor is numerically unaffected (flight and ground families both derive 1.5).
But a controlling-document row citing the wrong regulation for a ground load is
exactly the class of wrongness this project treats as real.

**Recommendation:** the row should read the case's own `case_ref.far_reference`
whenever one exists, with the current literals as the no-ref fallback only.
One-line fix plus a pin asserting a ground row's FAR equals its `CaseRef`'s.

### R6-C2 — The gear report CSV does not meet the load-output contract's column rules **[M-H]**

The contract (`CLAUDE.md`, CONVENTIONS §3) is explicit: *"The `-ULT` marker is
part of the units string; every case states its SF."* Every sibling channel
complies — the span CSV's header is
`...,Fx (lbs-ULT),Fz (lbs-ULT),...,SF`. The new gear report CSV does not:

* **No units on any force/moment column** (`Ground-line V`, `Datum Fx`,
  `Transfer Mx`, …) and therefore no `-ULT` marker anywhere in the table — the
  ULTIMATE basis is stated only in the methods stamp above the table.
* **No `SF` column** — the factor (1.5, from the governing table) is applied but
  nowhere stated per case, which is the exact defect class F-R1 closed for the
  governing-loads tables in 0.5.0.
* **One wrong header in SI:** `Stroke (in)` is a fixed string while the value is
  converted — verified, the SI file shows `4.325464E+01` (mm) under an `(in)`
  header. `Design weight` and `Leg weight` carry no unit at all.

The mechanism is worth recording: the Imperial digest baseline covers the new
`gear_report` channel, but **no test reads the SI gear CSV**, so the SI header
defect had nothing to fail against. `test_ultimate_contract` passed because it
checks that view downloads route through an ULTIMATE channel, not what columns
the channel emits.

**Recommendation:** build `_GEAR_REPORT_FIELDS` from the resolved unit set
(labels with `-ULT` on load columns, plain labels on lengths/angles), add an
`SF` column, and add one SI-channel assertion (header labels + one converted
value) so the family cannot regress. This moves the `gear_report` digest — its
own declared wave.

### R6-C3 — "V-n" is printed for a number that is not a V-n point **[M]**

`BalancedCaseResult.vn_case` is overloaded to hold the LANDLOAD case number for
the ground family, and every rendering surface prints it with the flight
family's label:

* deck `$` header: `"...side load -- PORT -- V-n point 19, loading ..."`;
* deck case map: `"SUBCASE 8619 = LG-19 ... -- V-n 19 -- ..."`;
* module-result titles: `"Balanced case 3-wheel level landing (V-n 1, ...)"`;
* report §6 / Balanced Cases page column `"V-n point"`;
* `SkippedCondition.name`: the 23.499 skip records read `"(V-n 25)"`.

A reader who joins "V-n 19" to the flight envelope's V-n table lands on a real
(and unrelated) flight point — precisely the silent-wrong-join class the
case-identity work of design note 17 exists to prevent.

**Recommendation:** a family-aware label with one owner (e.g. "LANDLOAD case
19" / "ground case 19" for `is_ground` cases), applied at the deck header, the
case map, `run()`'s titles, the rows table and `SkippedCondition.name`. Display
wording only; no identity or number changes.

### R6-C4 — Hygiene (piece 3) **[S]**

* `balance.gear_sets(wheels, nvp)` — the `nvp` parameter is unused (its own
  docstring says so); drop it.
* `report/content._gear_stroke_table`'s docstring contains leftover literal
  concatenation text (`... of " + section_ref("results") + " and ...`) — a
  paste blemish visible to any doc reader.
* The gear report states the main-wheel contact patch at `+tread/2` (one wheel
  of the pair, twin by mirror); true and commented in code, but the CSV itself
  never says which wheel a `main` row describes.

---

## 2. Findings — tests and gates (T)

### R6-T1 — G-6's rotational gate half was promised and not implemented **[M-H]**

The design note (plan 18, G-6) states the gate as **four** lines:

```
n_z_solved == NVP,  n_x_solved == NDP,  n_y_solved == NS      (per family, exact)
Iyy·θ̈_solved == PITCHP + L·W·(x_lift − x_cg)                  (closed form, see G-7)
Ixx·φ̈_solved == ROLLP,   Izz·ψ̈_solved == YAWP
```

and adds: *"the one place the assembled case deliberately departs from LANDLOAD
is stated in the gate rather than hidden in slack — and the gate goes red if G-7
is ever changed without revisiting it."*

What shipped (`test_the_ground_closure_reproduces_landload`) is the
**translational half only** — exact, at `rel_tol 1e-9`, and genuinely
content-carrying. The rotational half does not exist:

* **pitch** (`θ̈`) has no independent check at all — and pitch is where the G-7a
  lift-lever-arm term lands, so the very protection the note argued for is the
  part that is missing;
* **roll/yaw** are exercised only through (i) the closure driving the residual
  to zero, which is self-consistent by construction, and (ii) the side-family
  reflection identity, which checks LANDLOAD's two hands against *each other*,
  not against the solve.

The comparison is non-trivial (LANDLOAD's `PITCHP`/`ROLLP`/`YAWP` are about the
CG on the ground line; the solve is about the mass centroid in body axes, on the
assembled tensor) — which is presumably why it slipped, and also why it is worth
having: a frame error in exactly that transfer is what it would catch.

**Recommendation:** implement the moment half as designed — rotate the solved
`I·ω̇` back through the case's own `ρ`, add the G-7a lift term to the pitch line,
and assert against `PITCHP`/`ROLLP`/`YAWP` per family. If any line cannot be
made exact, the tolerance and its cause get stated in the test, per the G-7a
precedent. Until it lands, the gap should be named in the test file's docstring
rather than left silent.

### R6-T2 — `NS` compared by magnitude only **[S]**

The closure gate asserts `abs(delta_ny) == abs(ns)`; the sign is policed only
indirectly by the hand pin. Cheap to tighten when R6-T1 is done (the hand
determines the expected sign).

---

## 3. Findings — documentation (D)

### R6-D1 — CHANGELOG: five `Added` entries sit under `### Fixed` **[S, currency]**

`[Unreleased]` has one `### Added` (line 13), one `### Fixed` (line 97), one
`### Changed` (line 262). The piece-3 `Fixed` heading was inserted *above* the
pre-existing entries rather than below them, so **step 10 piece 2, piece 1,
step 9, the T-tail transfer and the ONENGOUT fixture-data entries — all
`Added`-class — are now filed under `### Fixed`**. Keep-a-Changelog structure
defect; content itself is complete and correct.

**Recommendation:** move the two genuine fixes (the side-family loading label,
`is_handed`) into their own `### Fixed` placed after all `Added` entries.

### R6-D2 — Backlog "shipped since the tag" omits two post-tag changes **[S, currency]**

`00_backlog.md`'s current-state narrative lists ONENGOUT, the linkage, D-23 and
step 10 — but **step 9** (discrete control surfaces + hinge moment + T-tail,
`54a49d2`) and **D-24** (pressurization exclusion) are also post-tag (both sit
in `[Unreleased]` and above the release-cut entry in the history file) and are
absent from the sentence. A release-notes drafter working from this paragraph
would drop an L-tier feature from 0.6.0.

### R6-D3 — Plan 09's status header is stale **[S, currency]**

`09_distributed_empennage_loads_plan.md` still opens with *"PHASE 1 SHIPPED
2026-08-08 … **T6–T8 remain**"*. T6–T8 are step 9, shipped 2026-08-13 with a
full closure trail everywhere else. The plan of record contradicts the history
file. (Contrast: plan 18 was correctly marked COMPLETE at piece-3 closure.)

### R6-D4 — `docs/00_INDEX.md` has no entry for plan 18 **[S, currency]**

The index (which CLAUDE.md says "maps the whole tree") lists design notes
14–17 but not `18_step10_ground_cases_plan.md` — the decision record for the
release headline. This review document also needs its row when filed.

### R6-D5 — PROJECT_GUIDE §4's authoritative layout omits the new single-source owners **[M, coverage]**

The package tree in `PROJECT_GUIDE.md` §4 — named by CLAUDE.md as the
authoritative layout — contains none of `cg_cases.py` (piece 2's one resolver),
`safety_factors.py` (piece 1's authority) or `gear_loads.py` (piece 3's free
body). The staleness predates this cycle (`case_ids.py`, `rigid_body.py`,
`tail_geometry.py`, `aero_curves.py`, `migrations.py` are also absent, and the
three `export/` lines are mis-nested under `mass_distribution.py`), but this
cycle added three *SSOT owners* to a tree whose whole point is telling a reader
where the single sources live.

**Recommendation:** refresh the §4 tree once, and consider a drift guard in the
spirit of the DATA_DICTIONARY generator (assert every `sloads/*.py` module
appears in the tree) so it cannot rot again.

### R6-D6 — `balance` and `tail_span` have no PROGRAM_SPEC module section **[M, coverage]**

PROGRAM_SPEC claims to be the per-module spec, and `balance` and `tail_span`
are **registered calc modules** — the first carries the mission's primary
deliverable (and, since piece 3, the entire ground-case assembly), the second
carries steps 7–9's physics including the suite's first hinge moment. Neither
has a `###` section. Their behaviour is documented — CONVENTIONS, the plan
docs, theory_sources, the gear_loads/LANDLOAD spec sections — but the one place
a reader is told to look for "inputs/outputs/FAR conditions per module" skips
the two most mission-central modules. The gap predates 0.5.0; steps 9 and 10
each made it materially larger.

**Recommendation:** add both sections (the plan docs and history entries contain
essentially all the content; this is assembly, not authorship). Optionally guard
it: a test asserting every name in the registry appears as a PROGRAM_SPEC
heading.

### R6-D7 — The balancing-method theory doc does not cover the ground family **[M, coverage]**

`docs/20_theory/balanced_cases.md` is the theory document of record for the
balanced free-free method. It describes three families (symmetric, lateral,
23.427(a)) and is written throughout in terms of the case's V-n point (§ applied
sets, worked examples). The **fourth family** — no V-n point, base load factor
zero, the whole field solved, gear reactions and ground-line lift applied, the
LANDLOAD closed-form check — exists only in the plan doc and the
theory-*sources* table row. Tier-L closure put the citation in
`00_theory_sources.md` (correct), but the method document a future maintainer
will actually read now describes a three-family deliverable that ships four.

**Recommendation:** a ground-family section in `balanced_cases.md` (the piece-3
history entry and CONVENTIONS block are 80 % of the text), including the ρ
rotation and why `RESIDUAL_GATE` does not apply.

### R6-D8 — Hygiene: backlog priority-table ordering **[S]**

After piece 3's row removal the table runs 1, 2, 3, 7, 8, … and rows `31a`,
`30a`, `31` appear out of sequence. Permitted — the removal rule says
"priorities are an order, not IDs" and invites renumbering — but the *point* of
the column is order, and it currently isn't one. One renumbering pass next time
the table is touched.

---

## 4. What was checked and found sound

Stated so the clean areas are on the record, not merely un-mentioned:

* **Closure trails: 9/9.** Every commit since the tag has its CHANGELOG entry,
  its history entry at the right tier (three L, three M, one S, plus the plan
  and release-notes rows), and its backlog removal. D-23/D-24 are in the
  resolved-decisions register with dates and consequences.
* **Digest discipline held under load.** Three declared waves; each moved
  exactly its predicted channel set (verified by re-deriving the diff against
  the frozen baseline, not by trusting the claims). Piece 2's falsifiable
  "nothing moves" claim was true.
* **The structural guards earned their keep this cycle**: the F-R2 section
  owner renumbered §8/§9 and Appendix A references automatically; the schema
  hash tripped on both v48 result-type changes and was consciously updated with
  reasons; the bands registry absorbed the gear GID band with disjointness
  proved; DATA_DICTIONARY and GUI_design schema-line guards forced their own
  updates.
* **Piece 3 physics**: the G-6 translational identity is exact (`1e-9`) on
  every case of both fixtures; the transfer invariant is exact (`3.4e-16`)
  about an arbitrary reference; both negative controls fire; the solver-level
  gear-node assertion closes the two-artifact loop through sbeam in both unit
  systems; coverage pins (2 assembled / 5 report fixtures) match G-13's
  predictions; the side-family wheel-split choice is resultant-invariant
  (verified analytically: the y-distribution of equal-direction side loads
  cannot move any resultant component).
* **Pieces 1–2** (spot-checked at gate level): the SF table's zero-defaulted-
  rows pin, the migration's per-fixture FLIGHT-set equality guard, the MLW
  floor firing on the RJ alone and the carrier↔mass guard on dhc8 alone are all
  present and green; `weight.envelope.gross_weight` remains oracle-locked.
* **Step 9** (documentation-level + gates): full L-tier trail, dedicated
  theory-sources section for the hinge moment, PROGRAM_SPEC coverage of the
  discrete path (inside the export-bridge section — see R6-D6), and its
  mutation-teeth tests are in the suite. The physics itself was not re-derived
  in this review beyond its own gates; it closed 2026-08-13 with its plan's
  gate table.
* **CONVENTIONS, CLAUDE.md, theory_sources, LANDLOAD/gear_loads spec sections,
  methods-stamp limitation set** — current and consistent with the code as
  shipped, including the reworded `flight-only-body-deck` limitation and the
  new `ground-flight-separate-families` key, both pinned.

---

## 5. Recommended order of work

| # | finding | effort | when |
|---|---|---|---|
| 1 | R6-D1 CHANGELOG headings | S | before anything else touches `[Unreleased]` |
| 2 | R6-C1 ground rows' FAR reference | S | before 0.6.0 — wrong regulation in a deliverable row |
| 3 | R6-C2 gear CSV units/`-ULT`/SF + SI header | S–M | before 0.6.0 — its own digest wave |
| 4 | R6-C3 "V-n" label for ground cases | S | before 0.6.0 — rides C2's wave if batched |
| 5 | R6-D2/D3/D4 currency fixes (backlog sentence, plan 09 status, INDEX rows) | S | same session as 1 |
| 6 | R6-T1 rotational gate half (+T2) | M | before 0.6.0 if possible; else filed as a named gap in the test docstring |
| 7 | R6-D6 `balance`/`tail_span` spec sections | M | with the 0.6.0 doc pass |
| 8 | R6-D7 ground family in `balanced_cases.md` | M | with the 0.6.0 doc pass |
| 9 | R6-D5 PROJECT_GUIDE tree refresh (+ guard) | M | any gap |
| 10 | R6-C4 / R6-D8 hygiene | S | opportunistic, with a digest-neutral batch |

Items 2–4 move deliverable bytes and should be claimed as their own digest wave,
per the G-13 rule; items 1 and 5 move none.

**Per the lifecycle rule:** these findings are filed here with bodies; each goes
into the backlog as a descriptive-name row when promoted to work, and closes at
its tier when done. Nothing in this review was fixed in the review session, by
the review's own scoping decision.
