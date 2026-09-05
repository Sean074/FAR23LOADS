# Module analysis is a LIMIT channel — #154 and the boundary it exposed

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: AGREED, 2026-09-04 (owner).** R1–R4 were agreed 2026-09-03; **R5
(OR-86)** and **D-a … D-f** were ruled 2026-09-04, four of them against this
note's first recommendation. §3 is written against the rulings as taken.
Milestone **0.8.2** for the LIMIT channel and the #154 fix; **0.8.3** for the
render/export boundary (OR-86) and the safety-factor page (OR-85). Closure tier
**L**: this narrows the LIMIT→ULTIMATE contract that `CONVENTIONS.md` §3 and
`CLAUDE.md` both state, so it is a contract change, not a behaviour tweak.

**#154** was filed as a small false claim: a `ConditionResult` holding no load
still carries `safety_factor = 1.5`, so a geometry table prints an ULTIMATE
banner. Reviewing it turned up something larger behind it — the factor is applied
on many more surfaces than the contract's purpose requires — and the owner's
ruling addresses that first. #154 proper survives as one decision inside it
(OR-82), because LIMIT rendering removes the *scaling*, not the *claim*.

Sources reviewed: `sloads/report/render.py` (`_is_load_unit`, `_ult`,
`_ult_units`, `results_to_rows`, `summary_rows`, `governing_loads_table`,
`critical_rows`, `load_cases_to_rows`, `module_text_report`, `text_report`),
`sloads/safety_factors.py` (`FAMILIES`, `classify`, `GoverningTable.stamp`,
`factor_for`), `sloads/models/results.py` (the eight `safety_factor` carriers),
`sloads/io.py` (`_safety_factor`, `load_cases_csv`), `sloads/registry.py`
(`run_all_modules`), `tests/imperial_baseline.py`, `tests/test_schema_guards.py`,
`tests/test_frozen_set.py`, `docs/10_standard/CONVENTIONS.md` §3,
`docs/30_future/44_oracle_report_note.md` §10.

---

## 1. The review

### 1.1 The claim is false in shipped output today, not latently

```
$ .venv/bin/python cli.py wing_geometry examples/ga6_normal.project.json
Aerodynamic surface geometry: wing
  FAR geometry   [ULTIMATE, SF=1.5]
    Area per side       1.326e+04 in^2
```

`render.py:730` and `:766` print that banner unconditionally from
`r.safety_factor`. No number is wrong — `_ult` scales on `_is_load_unit`, not on
the stamp — but a wing area has no safety factor and the line says it has one.

### 1.2 The factor reaches much further than the contract needs

The same run, on a module that does emit loads:

```
$ .venv/bin/python cli.py engine examples/ga6_normal.project.json
  FAR 23.361(a)(1)   [ULTIMATE, SF=1.5]
    Vertical down load        2475 lbs-ULT      # the calc value is 1650 lb
    Mean takeoff torque       831.6 ft-lb-ULT   # the calc value is 554.4 ft-lb
```

A per-module analysis page is not a deliverable. The purpose of the
LIMIT→ULTIMATE contract — one factor, applied once, where the structure is sized
— is served at case selection and at the export deck. Applying it on every module
view as well buys nothing and costs the analyst the number the method actually
computed. `CONVENTIONS.md` §3 already anticipates the carve-out in its last
bullet: *"Per-module analysis pages may display LIMIT only with the explicit
LIMIT marker and a pointer to the ultimate deliverables."* R1 takes that
carve-out as the rule for those surfaces rather than an option.

Note the second line: **mean takeoff torque is being factored**, 554.4 → 831.6.
That is an engine characteristic in load units, not a structural load. It is the
same defect class as #154 pointing the other way — units are not a reliable test
of what a load is — and it is filed, not fixed here (§2.4).

### 1.3 The measured scope of #154

Every registered module on `examples/ga6_normal.project.json`, each condition
classified by whether any of its values passes `_is_load_unit`:

| Condition content | Count |
|---|---:|
| No load-unit value at all | **44** |
| Mixed — loads beside geometry/coefficients | 289 |
| Every value a load | 10 |

The 44, by the family `safety_factors.classify()` returns:

| Family | Count | Examples |
|---|---:|---|
| `reference_data` | 23 | `wing_geometry` (7), `weight_envelope` (5), `weight_estimate` (4), `configuration` (3) |
| `flight` | 17 | `mach_limit` (8), `select` wing (6), `structural_speeds` (3) |
| `general` | 3 | `airloads` spanwise distributions |
| `ground` | 1 | `landing` LGFACTOR |

### 1.4 Every producer of those 44 is frozen

`configuration`, `wing_geometry`, `weight_envelope`, `weight_estimate`,
`weight_onecg`, `structural_speeds`, `mach_limit`, `airloads`, `select`,
`taildist`, `landing`, `balance` — all twelve are in the OR-13 frozen set. So no
fix may ask a producer to declare itself factorless: an explicit
`safety_factor=None` at the emit sites, or a `no_factor` flag on the producer,
would need an OR-15 admission across twelve files. The classification must be
derivable from what a condition already publishes. That vindicates note 44 §10's
instinct to put the fix at the data model, and it decides more of §2 than
anything else here.

### 1.5 The units test is not the load test

A content-only rule ("no load-unit value ⇒ no factor") gets one group wrong in
the direction that matters. `select`'s six *Critical wing load* conditions carry
only CL, V (EAS), Nz, Nx and altitude in `.values`; their loads live on
`WingLoadResult`, and they feed `net_loads` and the sbeam deck. Blanking their
factor would print `N/A` in the case index against six wing cases whose bulk-data
cards are factored — worse than the banner #154 was filed for.

**Corrected 2026-09-04.** This note first named `airloads`' three spanwise
distributions alongside them. Measurement says otherwise: those conditions
publish lift-curve slopes, `in`, `in^2`, `deg` and dimensionless `cl` — the
distribution's loads are not on them — and they carry **no `case_ref`**. They are
correctly factorless. The discriminator that separates the two groups is in
§2.2 D-e.

### 1.6 What the fix does not have to touch

- **`ConditionResult` is not persisted.** Only `CriticalCondition` is
  (`io.py:929`). And `tests/test_schema_guards.py`'s fields hash covers field
  *names*, not types, so `float → Optional[float]` on `ConditionResult` moves
  no hash and needs **no `SCHEMA_VERSION` hop** — unlike #169.
- The other seven `safety_factor` carriers (`WingLoadResult`, `TailSpanResult`,
  `BalancedCaseResult`, `BodyLoadResult`, `TailChordResult`,
  `ControlSurfaceLoadResult`, `CriticalCondition`) always carry loads, so the
  `None` case cannot arise on them. Six are persisted; leaving them `float`
  keeps this change entirely off disk.

---

## 2. The rulings

### 2.1 Agreed in session

| | Ruling | Becomes |
|---|---|---|
| **R1** | Every per-module view renders LIMIT — **except** the oracle GUI, which keeps ULTIMATE | OR-76, OR-77 |
| **R2** | The oracle technical report stays ULTIMATE throughout, §3 and Appendix B alike | OR-78 |
| **R3** | The safety-factor page carries the load-bearing FAR families, on its own workflow step, reusing `SafetyFactorOverride` | OR-85 |
| **R4** | The LIMIT change lands in 0.8.2; the page in 0.8.3 | OR-85 |
| **R5** | The factor is **stated, never applied** — the direction of travel; 0.8.2 takes the R1 half of it only | OR-86 |

R2 is what makes R4 safe: 0.8.2's deliverable does not move, so this is a change
to the analysis front-ends only.

#### OR-76 — Module analysis surfaces are a LIMIT channel

The CLI text reports, the app's per-module result tables and its per-page
"Download … (text)" buttons **SHALL** render LIMIT values, explicitly marked.
ULTIMATE **SHALL** remain the channel of case selection
(`governing_loads_table`, `critical_rows`) and of the export deliverable
(`sloads/export/`). The factor is still *decided* once, by the governing table;
what narrows is where it is *applied*.

#### OR-77 — The renderer's default is the frozen file's protection

`oracle_app/results.py` is in the OR-13 frozen set and calls the same two
renderers the app and CLI do (`module_text_report`, `summary_rows`). It cannot be
edited to pass a channel argument. Therefore the new channel parameter **SHALL**
default to today's ULTIMATE behaviour, and `app/` and `cli.py` **SHALL** opt into
LIMIT explicitly.

This inverts the usual instinct — the new rule is not the default — and that is
deliberate: it is the only arrangement in which the frozen file's output is
unchanged **by construction** rather than by inspection, and it makes G-OR-44 a
byte comparison rather than an argument. The freeze itself is a SHA-256 manifest
over file *content* (G-OR-9), so no admission is triggered either way; this is
about the oracle GUI's fidelity contract (C210-15), not about the manifest.

#### OR-78 — The oracle technical report is ULTIMATE throughout

The report is a deliverable, not a module view. Every section — §3's wing-load
tables and figures as much as Appendix B's structures deck — **SHALL** stay
ULTIMATE. `ORACLE_REPORT.md` needs no change, and no 0.8.2 report content moves.

#### OR-86 — State the factor, never apply it (direction of travel, scoped)

Ruled 2026-09-04, on the owner's proposal that every load sloads produces be
LIMIT and the ultimate scaling be removed outright. The principle is **adopted**;
its scope is **split**, and the split is the ruling.

**The principle.** Multiplying a limit load by its factor is not sloads' job.
The governing table decides each case's factor and every artifact **states** it —
the `SF` column, the deck's header comment, the CSV's basis block — and nothing
multiplies. A consumer applies it once, knowingly, per case. This is the same
motion as OR-76 taken to its conclusion: the factor is *decided* once and
*applied* nowhere.

**Why the field itself survives.** The proposal's second half — delete
`safety_factor` — is refused, on one fact: **not every case is 1.5**. Two
families in `sloads/safety_factors.py` sit at SF = 1.0 because the regulation
prescribes an already-ultimate load — `engine_ultimate` (23.367(a)(2)) and
`emergency` (23.561(b), the 9 g emergency-landing inertia factors). The field is
the only place that knowledge lives; relabelling those cases "limit" and letting
a consumer apply 1.5 sizes the 9 g case at 13.5 g. Removing the field would also
mean nine OR-15 admissions (the frozen modules that *set* it), a
`SCHEMA_VERSION` hop across seven persisted carriers, and the deletion of the
G-11/M4-8 single authority built to stop the factor being decided ad hoc.

**The scope split.** Extending the principle past the module views changes what
`CLAUDE.md`'s Phase C mission calls the deliverable (*"per-component distributed
**ULTIMATE** loads … as `FORCE`/`MOMENT` bulk-data cards"*) and what
`CONVENTIONS.md` §3 states as the load-output contract. That is a mission-level
change, not a channel decision. Therefore:

* **0.8.2 takes the R1 half only** — module analysis surfaces render LIMIT.
  OR-78 stands unchanged: the oracle technical report and the export deck stay
  ULTIMATE, so no 0.8.2 report content moves and section 2's completed review
  still describes what the reader sees.
* **0.8.3 opens the render/export boundary as its own note**, at the top of the
  milestone, where the deck, `CONVENTIONS.md` §3 and the mission statement are
  changed together or not at all. It is that note, not this one, that removes
  `_ult` from `sloads/export/`.

This note is unchanged below except where §2.2 reads on it: nothing in §2.2 may
be decided in a way that the 0.8.3 boundary note would have to undo.

### 2.2 Ruled 2026-09-04

All six were put to the owner with a recommendation; **four were ruled against
the recommendation as first written** (D-b, D-c, D-e, and the scope of D-a),
each because tracing or measuring the code changed the answer. The revisions are
recorded in place rather than silently replaced.

#### D-a — The per-module load-case CSV — **RULED 2026-09-04 (owner): LIMIT**

`io.load_cases_csv` → `render.load_cases_to_rows` (`render.py:679`) scales the
same way the text report does, and is digested as the `csv/{module}` channel. It
is a per-module channel by shape and machine-readable by use.

Tracing its call sites, 2026-09-04, found thirteen production callers in four
groups, not the two this note first implied: eight per-module download buttons in
`app/views/`, `cli.py:537`, the report bundle (`export_report.py:223`, which is
D-b's question, not this one), and the frozen `oracle_app/results.py:233`, which
keeps ULTIMATE by the OR-77 default without an edit.

**The site this note first missed:** `sloads/report/results_zip.py:117`, the
sidebar's "Download results (zip)". That sidebar is `app_shell/sidebar.py`,
shared by *both* GUIs (`app/Home.py:37`, `oracle_app/Oracle.py:41`), so D-a
silently decides the zip as well, and the zip is reachable from the oracle GUI.
It resolves under OR-77 and only under OR-77: `app_shell/sidebar.py` is **not**
in the frozen manifest, so it can take a channel argument defaulting to ULTIMATE
— `app/Home.py` opts in, frozen `oracle_app/Oracle.py` passes nothing and its
bytes are unchanged.

*Recommendation:* **LIMIT**, keeping its existing `SF` column so the factor is
stated without being applied. Anything else splits the text and CSV renderings of
one module across two channels — the F-R1 defect class in a new dress. OR-86
points the same way: the CSV is a module view, and the deliverable it is not is
the sbeam deck. → would become **OR-79**.

Two consequences to accept with it: `results_zip.py`'s safety-factor docstring
paragraph ("a zip member can never state a different factor than the deliverable
would") must be reworded to "than the page it mirrors"; and
`tests/test_ultimate_contract.py`'s guard changes direction — from "every
`app/views/` CSV download routes through the ultimate boundary" to a per-site
channel table. That is a strengthening, not a relaxation, and it is G-OR-45's
proper shape.

#### D-b — The report bundle's per-module text — **RULED 2026-09-04 (owner): LIMIT**

`app/views/export_report.py:143` bundles per-module text reports into the report
bundle. R2 says the report stays ULTIMATE; R1 says module views go LIMIT.

Traced 2026-09-04. The joined string has **two** exits, not one:
`export_report.py:516`, a bare "Combined text report (all modules)" page
download, and line 404 → `bundle_members(text_report=...)` →
`<stem>_report.txt` inside the export bundle zip. The bundle here is the
*summary* report (`SUMMARY_REPORT.md`); the oracle technical report is built
separately through `oracle_package.py` and is untouched either way.

*Recommendation, revised:* **LIMIT** — the first draft of this note recommended
ULTIMATE on the grounds that "the artifact, not the shape, decides the channel",
and line 516 kills that reasoning: the same string is a bare page download three
lines below the per-module CSVs D-a sends to LIMIT. The bundle's ultimate content
is what gets sized to — the sbeam BDF artifacts, the case index, and
`component_loads` (line 149, a separate path, unchanged by OR-78).
`<stem>_report.txt` is a transcript of thirteen module pages, and a zip in which
`<stem>_report.txt` and `<stem>_wing_loads.csv` state one load at 1.5× each other
is F-R1 inside a single archive. → would become **OR-80**.

Requires with it: the `bundle.py` manifest row for `_report.txt` states its
channel (the manifest's whole job is that a recipient cannot mistake what they
hold — `tests/test_bundle_manifest.py`); `methods_statement` carries the one-line
statement of both channels, being already the bundle's basis document; and
**OR-78 takes a one-clause carve-out** — it was written about the oracle
technical report, and the export bundle's module-view transcript is excepted, so
the two rulings cannot later be read against each other.

#### D-c — How LIMIT is marked — **RULED 2026-09-04 (owner)**

**Ruling.** LIMIT is the **global default**, stated once in the GUI text and in
the standard: *all loads are LIMIT unless specified*. There is no per-artifact
LIMIT marker — no `-LIM` suffix, no `*_LIMIT.csv` filename, no `Basis = LIMIT`
column. → **OR-81**.

This supersedes the recommendation this note first carried (plain units plus a
per-artifact header line) and, more importantly, it supersedes **M4-15**, the
existing in-band LIMIT-marking convention recorded in `PROGRAM_SPEC.md`
(lines 98–110) and `GUI_design.md` (§6, "LIMIT vs. ULTIMATE marking"). M4-15
exists because LIMIT was the *exception* on a deliverable and had to announce
itself in-band; once LIMIT is the default the announcement is noise, and a
marker that says what the default already says is decoration. The sweep it
implies is part of the work, not a follow-up:

* `net_loads.wing_load_rows` and `body_loads.body_load_rows` stop appending
  `Basis = LIMIT` — **both are frozen modules**, so this is the first part of
  this note that needs an **OR-15 admission**, or it waits for the freeze to
  lift. Named here rather than worked around.
* `wing_loads.py:389` `net_wing_loads_LIMIT.csv` and its Fuselage Loads twin
  lose the `_LIMIT` stem; the `*_ULT.csv` twins are decided by the scope
  question below, not here.
* `PROGRAM_SPEC.md` §limit-vs-ultimate and `GUI_design.md` §6 are rewritten to
  state the default, not the marking rule.
* `tests/test_ultimate_contract.py` inverts: it stops enforcing that an
  unmarked load CSV routes through an ULTIMATE channel, and starts enforcing
  that a load surface marks itself **only** when it is an exception.

**When OR-81 can actually land — a consequence of the option-1 split.** The
owner confirmed 2026-09-04 that OR-86's "remove the application" sentence states
the **endpoint**, not a reversal: 0.8.2 still takes the R1 half only. But a
default is only a default when there is one channel. Through 0.8.2 the ULTIMATE
channel still exists — the export deck and the oracle report keep the factor
under OR-78 — so an unmarked LIMIT CSV would sit in the same bundle as an
ULTIMATE BDF with nothing distinguishing them, which is the exact confusion
M4-15 was written to prevent. Therefore:

* **0.8.2** — the module views go LIMIT and stay marked, M4-15 as it stands. No
  `Basis = LIMIT` is removed, so **no OR-15 admission is needed** and the frozen
  `net_loads`/`body_loads` row shapes are untouched.
* **0.8.3** — the boundary note removes the last multiply, at which point the
  ULTIMATE channel is gone, M4-15 retires, and the markers come out in one
  sweep, by then against an unfrozen tree.

OR-81 is therefore recorded here as the **agreed endpoint convention**, and its
removal work is scheduled with the boundary note, not with this one.

**The exception the ruling leaves standing.** "Unless specified" is not empty:
two families are computed already-ultimate because the regulation prescribes
them so — `engine_ultimate` (23.367(a)(2)) and `emergency` (23.561(b)) — and
their loads must say so, or a consumer applying 1.5 to a 9 g case sizes it at
13.5 g (OR-86). So the marker vocabulary is not deleted; it **inverts**. `-ULT`
survives on exactly those cases and nowhere else, and it becomes rare enough to
be conspicuous, which is the point of a marker.

#### D-d — #154 proper — **RULED 2026-09-04 (owner): agreed as recommended**

LIMIT rendering removes the scaling, **not** the claim: a geometry table would
still print `SF=1.5` unless a factorless condition carries nothing.

*Recommendation:* keep the 2026-08-30 ruling. `ConditionResult.safety_factor`
becomes `Optional[float]`, rendered `N/A`; a mixed condition keeps its factor and
shows N/A against its non-load rows. No schema hop (§1.6). The seven other
carriers stay `float`, with the reason recorded — each exists only to carry a
load. → **OR-82**.

Consequence to accept with it: `format_value(None)` raises `TypeError` today, and
`_ult(load, "lb", "", None)` would too. That is the desirable behaviour — a load
inside a factorless condition should fail loudly rather than silently take 1.0 —
and it is what G-OR-46 guards from the other side.

#### D-e — The classifier, and the stragglers — **RULED 2026-09-04 (owner)**

**Measured 2026-09-04**, `registry.run_all_modules` over both shipped examples.
Of GA6's 343 conditions, 44 hold no load-unit value. `reference_data` catches 23
of them; the other 21 classify as `flight`, `general` or `ground`:

| Module | FAR ref | n | Example |
|---|---|---|---|
| `mach_limit` | 23.335(b) | 8 | Mach limit line at 12000 ft |
| `select` | 23.333(b) / 23.333(c)or(b) / 23.349(a)(2) / 23.349(b) | 6 | Critical wing load PHAA (case 22) |
| `airloads` | 23.301 | 3 | Spanwise airload distribution: wing |
| `structural_speeds` | 23.335, 23.335(b), 23.337 | 3 | Limit maneuver load factors |
| `landing` | 23.473 | 1 | Landing load factor (LGFACTOR) |

**A family/`_EXACT` rule cannot do this** — the recommendation this note first
carried is withdrawn. `23.337` is genuinely the manoeuvre flight-load
regulation; `structural_speeds` publishes *the load factors themselves* under it
and any module publishing a manoeuvre load case would too. Blanking by FAR
reference makes the answer depend on which module happened to cite the section
first, which is the word-order fragility `classify` already refuses elsewhere.

**The discriminator is already in the data model.** A condition prescribes no
factor exactly when it holds **no load-unit value *and* no `case_ref`**. Counted
over both examples:

| | has `case_ref` | no `case_ref` |
|---|---|---|
| **holds a load** | 95 (GA6) / 99 (Baron) | 204 / 394 |
| **holds no load** | **6 / 6** — `select`, protected | **38 / 38** — factorless |

The 38 is stable across two airframes whose totals differ by 194 conditions, and
the 6 is exactly §1.5's group: `select`'s critical wing cases, whose loads live
on `WingLoadResult` and whose deck cards are factored. The `case_ref` clause is
not a patch on the content test — it is the clause that protects the case index
from printing `N/A` against a factored case.

*Recommendation:* one owner in `sloads/safety_factors.py` —
`prescribes_factor(item) -> bool`, consulted by `factor_for`, which returns a
`Resolution` with `factor=None` for a condition that fails it. The `FAMILIES`
table is **unchanged**: it still owns *which* factor a case takes; the new
predicate owns *whether* one is prescribed at all. Single owner plus a
drift-guard test, per CLAUDE.md rule 3. → **OR-83**.

The mechanical consequence stands from the first draft:
`registry.run_all_modules` re-stamps every condition through
`GoverningTable.stamp`, so the `Optional` default of D-d is overwritten unless
the table itself learns the concept. A bare `hasattr`-style skip inside `stamp`
is rejected — that method's own docstring records `unstampable` because a silent
skip is how the F-R1 defect class returns.

**One risk to state.** The predicate's load half is `render._is_load_unit`, the
same helper that scales "Mean takeoff torque" 554.4 → 831.6 ft-lb (§2.4). If it
is wrong about what a load is, it is wrong here too — an engine characteristic
in `ft-lb` makes its condition look load-bearing and keeps a factor it should
not have. That is the benign direction (a stated factor, never an applied one,
once OR-86's endpoint lands) and it means the two findings share one owner: the
torque fix is the same edit as tightening this predicate, which is why §2.4
files it rather than folding it in.

#### D-f — The Imperial baseline — **RULED 2026-09-04 (owner): regenerate**

`tests/imperial_baseline.py:83` digests `module_text_report` output as
`txt/{module}` for every example, and `io.load_cases_csv` as `csv/{module}`. The
baseline exists to represent what the CLI builds, so it follows the CLI.

*Recommendation:* regenerate `fixtures_imperial/digests.json`, and state in the
commit and in `CHANGELOG.md` that the change to Imperial output is intended — the
module's own docstring makes that a deliberate act. The regeneration is also the
**proof** that nothing else moved: the diff must touch `txt/*` and `csv/*` only.
→ would become **OR-84**.

### 2.3 Deferred to 0.8.3 — the safety-factor page (OR-85)

R3/R4. A new `app/views/` page and a `workflow.py` step listing the load-bearing
FAR families — the seven of `FAMILIES` minus `reference_data` — each row editable
with a **mandatory basis** (G-11). Non-load condition types do not appear on it,
which is the page's expression of "only loads get a safety factor".

It needs **no schema change**: `SafetyFactorPolicyInput` /
`SafetyFactorOverride` already round-trip through `io.py`, are validated
(`_check_safety_factor_overrides` — mandatory basis, out-of-range, and the
certification-risk warning for an override below the regulation), feed
`GoverningTable.for_project`, and export as `<project>_safety_factors.csv`. What
is missing is only the GUI: the table is written to CSV in `export_report.py` and
is displayed or edited nowhere. `app/` only — `oracle_app`'s shell files are
frozen.

Its own note at 0.8.3, with its own gates. Recorded here so the 0.8.2 work is
shaped to fit it.

### 2.4 Findings filed, not fixed

- **Mean takeoff torque is factored** (§1.2), 554.4 → 831.6 ft-lb, because
  `_is_load_unit` tests the unit alone. With OR-76 in place the exposure shrinks
  to case selection and the export, where it may not arise at all. Filed with a
  body as **#170**; scoped to those two surfaces. Not folded in here: it is a question about
  what a load *is*, and answering it inside a channel change would hide it.
- **The report's §3 load tables print 1.5× the printed oracle.** Appendix A is a
  LIMIT oracle; the oracle tests compare at calc level and never cross the render
  boundary, so nothing catches it — the report is simply not directly readable
  against p131 today. Not a defect (OR-78 makes it the intended channel), but it
  is the strongest argument for OR-86's 0.8.3 half, and it is recorded here so
  that note opens with it.
- **`examples/ga6_normal.project.json` and `examples/concept_regional_jet.project.json`
  are stored at 1-space JSON indent** while `io.save_project` writes `indent=2`,
  so any programmatic re-stamp reformats them wholesale. Tier-S sweep, carried
  over from #169; filed as **#171**.

---

## 3. As-built plan

Written against the rulings of 2026-09-04 as taken, not against this note's
first recommendations. Scope is **0.8.2 only**: the module-view channel and
#154. The render/export boundary (OR-86) and the marker sweep (OR-81) are the
0.8.3 note's work, and are named below where they would otherwise look missing.

### 3.1 Code

| File | Change |
|---|---|
| `sloads/report/render.py` | Keyword-only `channel` parameter on `module_text_report`, `text_report`, `results_to_rows`/`summary_rows` and `load_cases_to_rows`, **defaulting to ULTIMATE** (OR-77). The LIMIT path applies no factor, emits plain units, and states its marker; the per-case banner at `:730`/`:766` reads `[LIMIT — SF=… applies]`. |
| `sloads/io.py` | `load_cases_csv` / `write_load_cases_csv` pass `channel` through (OR-79). |
| `sloads/models/results.py` | `ConditionResult.safety_factor: Optional[float]`, contract paragraph rewritten (OR-82). The seven persisted carriers stay `float` — each exists only to carry a load — with the asymmetry's reason stated so it is not read later as an oversight. |
| `sloads/safety_factors.py` | New owner `prescribes_factor(item) -> bool` — *no load-unit value **and** no `case_ref`* — consulted by `factor_for`, which returns a `Resolution` with `factor=None` when it fails (OR-83). **`FAMILIES`, `LoadClass`, `DERIVED_FACTOR` and `_EXACT` are unchanged**: the table still owns *which* factor a case takes; the predicate owns *whether* one is prescribed. `stamp()` writes `None` through, with no `hasattr` gate. |
| `sloads/report/results_zip.py` | Takes the channel; its safety-factor docstring paragraph is reworded from "never a different factor than the deliverable would" to "than the page it mirrors". |
| `app_shell/sidebar.py` | Passes a channel to `results_zip_bytes`, defaulting to ULTIMATE. Not frozen, so this is editable — and the default is what keeps the frozen `oracle_app/Oracle.py` unchanged without an argument (OR-77). |
| `sloads/report/bundle.py` | **Unchanged — plan corrected in implementation.** The bundle manifest carries file *names* only (`BundleMember.manifest_name`, a one-row-covers-many spelling); it has no description column for a channel to go in. |
| `sloads/report/methods.py` | `methods_statement` takes the channel and states the file's own basis: LIMIT names the factor as stated-not-applied, says `N/A` means no factor applies, and points at the ULTIMATE deliverables. `csv_comment_block` / `bdf_comment_block` pass it through, so a CSV forwarded on its own states **its** basis rather than the bundle's — which is what G8.3 asks for and what a manifest row could not have delivered. |
| `cli.py` | Two sites opt into LIMIT: `:541` (`text_report`), `:543` (`module_text_report`). |
| `app/Home.py` | Opts the shared sidebar into LIMIT. |
| `app/views/` | **Eleven** sites opt in: `configuration_layout` (2), `engine_mount` (2), `export_report` (2, OR-80), `flight_envelope`, `landing_loads`, `results_review`, `structural_speeds` (4), `weight_mass` (6), `wing_loads` (2). |

**Two call sites this plan missed, found by the work itself:**

* `app/views/engine_mount.py` builds a CSV from `load_cases_to_rows` directly,
  not through `load_cases_csv` — so it was in none of the greps behind §3.1's
  inventory of thirteen. **G-OR-45 caught it on the gate's first run**, which is
  the behaviour the inversion was written for: the renderers default to
  ULTIMATE, so a site that names no channel ships ultimate loads silently and
  plausibly, and only a source-level gate says so.
* `summary_rows` dispatches to a registered `SUMMARY_SHAPES` shaper and was
  dropping the channel on the floor, so SELECT's one-line-per-case table still
  emitted `lbs-ULT` headers on a LIMIT surface. Fixed with an explicit
  `_CHANNELLED_SHAPES = {"select"}`: `weight_envelope`'s rows are weights and
  stations, never loads, so it takes no channel rather than accepting one and
  ignoring it. G-OR-47 is what caught this and what catches the next one.

**Untouched by design, and deliberately so:**

* `oracle_app/**` — frozen; OR-77's default keeps its output byte-identical
  without an edit, which is what makes G-OR-44 a byte comparison rather than an
  argument.
* `sloads/export/**` and every report section — OR-78. The four multiply sites
  (`balanced_deck:383`, `lra_import:248`, `lra_model:820`, `sbeam_bridge:825`)
  are the 0.8.3 note's, not this one's.
* `governing_loads_table` and `critical_rows` — case selection stays ULTIMATE.
* `net_loads.wing_load_rows` / `body_loads.body_load_rows` — frozen, and their
  `Basis = LIMIT` columns stay until M4-15 retires with OR-81 in 0.8.3.
  **No OR-15 admission is sought or needed.**

`app/views/results_review.py` needs care: it renders per-module `summary_rows`
**and** `governing_loads_table` on one page, so after this it shows both
channels and each must carry its own marker.

### 3.2 Standard

- `CONVENTIONS.md` §3 — the last bullet's carve-out becomes the rule for module
  surfaces and names the marker; the first bullet is sharpened to name the two
  boundaries that still apply a factor. A forward pointer records that OR-86's
  endpoint removes both in 0.8.3, so the two notes cannot be read as
  contradicting each other.
- `CLAUDE.md` "Load-output contract" — the same narrowing, in its one paragraph.
- `PROGRAM_SPEC.md` — the limit-vs-ultimate scope statement (lines 98–110) gains
  the module-view channel. **M4-15's in-band LIMIT marking stays**: while the
  ULTIMATE channel exists, an unmarked LIMIT CSV beside an ULTIMATE BDF is the
  confusion M4-15 was written to prevent.
- `GUI_design.md` §6 — likewise unchanged in substance, extended to the pages
  this change moves.
- `ORACLE_REPORT.md` — **no change** (OR-78). Stated so the absence is
  deliberate.

### 3.3 Gates

- **G-OR-44** — a no-argument call to `module_text_report`, `summary_rows`,
  `text_report`, `load_cases_csv` and `results_zip_bytes` changes **no load
  value and no units string** from the pre-change ULTIMATE output. The frozen
  oracle GUI's protection (OR-77).

  **Amended in implementation, 2026-09-04 (owner).** The first form of this gate
  promised *byte*-identity, and that cannot hold alongside OR-82: #154's fix is
  channel-independent, so a condition that prescribes no factor now prints `N/A`
  in its `SF` cell on the ULTIMATE channel too. Measured, that alone moves **62
  of the 330** Imperial digests, all in `txt/*`, with no caller yet opting into
  LIMIT — and zero `csv/*`, `sbeam/*`, `case_index` or `gear_report`. The owner
  ruled the change correct on its merits: geometry, weights and speeds should
  never have carried a factor, and `N/A` is truer than a fabricated 1.5.

  So the oracle GUI's Results page **does** change, in exactly one way: an SF
  cell that stated a factor which does not exist now says so. No number moves,
  no frozen file is edited, G-OR-9's manifest hash is untouched, and no OR-15
  admission arises. C210-15 makes the fidelity target the analysis contract
  rather than the pixels, and this is the contract being met, not broken.
- **G-OR-45** — `tests/test_ultimate_contract.py` inverts into a **channel
  table**: every load surface in `app/`, `cli.py` and the bundle declares LIMIT
  or ULTIMATE and is checked against it. A new page with an undeclared load
  download fails. This replaces the current "must route through an ULTIMATE
  channel" assertion and is a strengthening, not a relaxation.
- **G-OR-46** — both directions of the factorless rule, across all six examples:
  a condition resolving to no factor holds no load-unit value **and** no
  `case_ref`; a condition holding either resolves to a float (OR-82/OR-83).
- **G-OR-47** — no LIMIT-channel render emits `-ULT`, and every one states its
  LIMIT marker (OR-81 as it applies in 0.8.2).
- **G-OR-48** — the regenerated Imperial baseline moves in `txt/*` and `csv/*`
  **only** (OR-84). Measured on regeneration, 2026-09-04: **184 of 330** digests
  moved — all 118 `txt/*` and 66 of the 118 `csv/*` — and **146 did not**,
  including **every** `sbeam/*` (83), `case_index` (6) and `gear_report` (5).

  The note first predicted 236/94, assuming all 118 CSVs would move. Only 66 do:
  a module whose summary table carries no load column renders identically on
  either channel, so the diff touches exactly the files that state loads. That
  is a sharper result than the prediction, not a weaker one.

  `case_index`'s immobility is the direct empirical check on OR-83: every
  case-index row has a `case_ref`, so if one moved, `select`'s six critical wing
  cases would have been wrongly blanked — the failure §1.5 predicts. It did not
  move.

  `tests/imperial_baseline.py` itself changed with this: it rendered the human
  channel with no argument, which after OR-77 means ULTIMATE, and the baseline
  exists to represent what `cli.py` builds. It now passes
  `channel=LoadChannel.LIMIT`, or it would have frozen bytes no shipped command
  produces.
- The existing guards are extended, not replaced: zero `defaulted` rows on every
  shipped fixture, and `unstampable` still empty.

### 3.4 Verification

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/
.venv/bin/mypy
.venv/bin/python tests/imperial_baseline.py     # deliberate; diff before committing
```

By hand, the three reads that are the point of the change: the `wing_geometry`
CLI report (no ULTIMATE banner, no factor, `N/A` in the SF column), the `engine`
CLI report (1650 lb and 554.4 ft-lb, marked LIMIT), and the oracle GUI's Results
page, whose loads must be identical to before — its only permitted difference is
the `N/A` of G-OR-44's amendment.

### 3.5 Closure

**Tier L.** Contract change (`CONVENTIONS.md` §3, `CLAUDE.md`), so: this note
agreed first (done, 2026-09-04), the amended convention cited, `changes/`
fragments (`.changed.md` + `.fixed.md`), and a history fragment in **full step
format** — which must state in its own sentence that the Imperial baseline was
deliberately regenerated and why (the `imperial_baseline` docstring makes that
an obligation, not a courtesy), as must `CHANGELOG.md`. The #154 backlog row is
removed at close.

**No `SCHEMA_VERSION` hop** — `ConditionResult` is not persisted and no
persisted carrier changes type (§1.6). **No frozen file is edited**, so no OR-15
admission is sought; if implementation turns one up, it is named and the turn
stops.
