# Appendix B.2 and chord bending — reopening OR-70

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: AGREED 2026-09-03 (owner, in session — `CLAUDE.md` rule 1's
working-alone path).** Milestone: **0.8.2** (D-4). Closure tier **L**: the
owner's ruling on D-6 takes the structural fix, which adds a field to
`LoadValue` and edits a **frozen** module under an **OR-15 admission** — the
same shape as note 45, which was tier L for the same reasons. The draft's
tier-M estimate assumed D-6's default (guard-side parsing) and D-3's default
(no figure); both were overruled.

Note 46 §2 records **OR-70 — "Appendix B.2 is not widened"** as *filed, not
done*, on the reasoning that "adding `Mzz` beside a body-axis `Mz` in B.1 would
put the two conventions in one appendix without a reader-visible reason." This
note reviews that reasoning against what the code actually does, finds it does
not survive the review, and states what changing it costs.

Sources reviewed: `sloads/report/oracle_sections.py`
(`_CUMULATIVE_LOADS`, `_APPLIED_LOADS`, `_NOMENCLATURE`, `_nomenclature_table`,
`_derivation_note`, `_wing_summary_table`, `_DISTRIBUTION_FIGURES`),
`sloads/export/sbeam_bridge.py` (`_span_csv_fields`, `_SPAN_CSV_CONVENTIONS`),
`sloads/modules/net_loads.py:272-282`, `docs/10_standard/ORACLE_REPORT.md`
§3.3, `docs/30_future/44_oracle_report_note.md` OR-55, note 46 OR-69/OR-70,
`docs/20_theory/00_theory_sources.md` (AIRLOADS/WINGINER rows).

---

## 1. The review

### 1.1 The rationale OR-70 gives is already satisfied, in print

OR-70's objection is that B.2's beam-convention `Mzz` would sit beside B.1's
body-axis `Mz` with nothing telling the reader they differ. But **B.2 already
prints `Mxx` beside B.1's `Mx`**, which is the same pair of conventions, and
§3.2's notation table already carries the sentence that disambiguates them:

> "the carried `Mxx` and `Myy` are the beam's own positive-magnitude bending and
> torsion, so `Mxx` and `Mx` share a sense and a **chordwise bending would
> not**."

That clause was written to forward-reference a column that is not there. The
reader-visible reason OR-70 says is missing is already printed, in the one table
the standard makes the owner of the distinction. Widening B.2 does not introduce
a second convention into the appendix; it adds the one row of the existing
convention whose sign the notation already warns about.

A stronger precedent sits one file away: **OR-69** settled exactly this question
for `wing_span_loads.csv`, which prints body-axis `Mz` and beam `Mzz` *in the
same row* and names both conventions in its header. If a CSV may carry the pair
with a stated reason, an appendix whose `Mz` column is identically zero may
carry it with the same reason.

### 1.2 The exposure is not a rounding term

`Mzz` is oracle-locked (Appendix A p222, root −81,483 lb-in) and is delivered by
every wing case the suite runs. Root values from today's build:

| Airplane | Case | `Mxx` | `Myy` | `Mzz` | `\|Mzz\|/\|Myy\|` |
|---|---|---:|---:|---:|---:|
| ga6_normal | PHAA | 455,138 | −60,878 | −81,417 | **1.34** |
| ga6_normal | TORS | 282,133 | −46,237 | 1,839 | 0.04 |
| ga6_normal | ACRL | 389,966 | −48,244 | −86,959 | **1.80** |
| baron_58 | PHAA | 530,924 | −80,630 | −84,502 | **1.05** |
| baron_58 | TORS | 192,293 | −49,667 | −27,688 | 0.56 |

(limit, lb-in, root station.) On four of five cases the chord bending the
appendix omits is **larger than the torsion it prints**, and it gets neither a
column in B.2 nor a figure in 3.4.

### 1.3 Three statements in the tree disagree about `Mzz`'s status

- `oracle_sections.py:2158` says chord bending "is not delivered by this
  analysis (owner decision, iteration 3)". It **is** delivered: `net_loads`
  publishes `root_chord_bending_mzz` and `WingStationLoad.mzz` carries the
  distribution.
- OR-55 (note 44) omits `Mzz` from the **figures** of 3.4, with a stated reason
  that is about plotting — "four pages of drawing for a load nobody reads off a
  plot". That reason does not transfer to a table the reader looks a number up
  in, and OR-55 never claimed it did.
- ORACLE_REPORT.md §3.3 already requires the applied set to close onto "the
  published `Sz`, `Sx`, `Mxx`, `Myy` **and `Mzz`**" — a gate (G-OR-35) that
  names a quantity the appendix does not publish. `Mzz` is published only in
  `wing_span_loads.csv`, so a reader holding the report alone cannot check the
  gate the report states.

So the appendix omits a column that the analysis computes, that the standard's
own closure gate names, that the companion CSV prints, and that §3.3 already
prints at the root.

### 1.4 A live defect found in passing (independent of the decision)

Measured on today's GA6 build. §3.2's notation table defines

```
X Y Z  Fx Fy Fz  Mx My Mz  Sz Sx Mxx Myy
```

and §3.3's root table prints

```
Root shear Sz | Root bending Mxx | Root torsion Myy (25% chord)
              | Root drag shear Sx | Root chord bending Mzz
```

Every symbol those headings name is defined **except `Mzz`**. ORACLE_REPORT.md
§3.3 says: *"A column heading anywhere in section 3 **SHALL** name a symbol from
that table and nothing else."* The guard,
`tests/test_oracle_report.py::test_section_three_defines_every_symbol_its_tables_use`,
walks only the two **appendix** tables, so the SHALL is unguarded exactly where
it is broken — and it is broken on a table that has shipped.

This is a defect on shipped content and does not depend on how OR-70 is ruled:
`Mzz` needs a notation row either way, and the guard needs to walk every section-3
table. `CLAUDE.md` rule 4 (generalize on first find) makes the guard part of the
fix, not a follow-up.

---

## 2. The rulings (owner, 2026-09-03, in session)

| | Decision | Ruling |
|---|---|---|
| **D-1** | Is OR-70 reversed? | **(a) Reversed.** B.2 gains `Mzz`. |
| **D-2** | If kept, what reason? | **Not applicable** — D-1 reversed it. |
| **D-3** | Does 3.4 get a fifth figure? | **Yes.** OR-55's `Mzz` omission is reversed with it. |
| **D-4** | Which milestone? | **0.8.2.** |
| **D-5** | Restate the sign in B.2's note, or cross-reference? | **Restate**, overruling the draft's default. |
| **D-6** | How does the guard read a §3.3 heading? | **The structural fix**, and the **OR-15 admission is granted**. |

D-3 and D-6 each widen the work past what §3 of the draft planned: D-3 reverses
a note-44 decision, and D-6 spends a frozen-file admission and adds a field to a
result type. Both are recorded below as decisions in their own right rather than
as consequences of D-1, so that a later reader finds the ruling and not only its
effect.

### 2.1 Decisions of record

| ID | Decision | Depends on |
|---|---|---|
| **OR-71** | **Appendix B.2 states chord bending `Mzz`,** as its fifth cumulative column, with the recurrence `Mzz(i) = Mzz(i+1) + Sx(i+1) dy` printed in 3.2 beside the other four. **Supersedes OR-70.** The reason OR-70 gave does not survive §1.1: B.2 already prints `Mxx` beside B.1's `Mx`, and the notation table already carries the sentence that separates the two conventions. The reason the code gave — "not delivered by this analysis" — was never true of the number (§1.3). | OR-70 (supersedes) |
| **OR-72** | **3.4 plots every column B.2 tabulates,** so chord bending gets the fifth figure. **Supersedes OR-55's `Mzz` omission**, which rested on it being "a load nobody reads off a plot"; at the root it exceeds the torsion that does get a figure on four of the five example cases (§1.2). The figure list and the column list are tied by a gate, so a sixth column cannot arrive unplotted by omission rather than by decision. | OR-71 |
| **OR-73** | **B.2's note restates the sign** rather than only pointing at 3.2. The draft argued the cross-reference on `CLAUDE.md` rule 3 (one home per convention); the owner ruled the other way, and the rule is not violated: 3.2's notation table remains the **definition**, and B.2's note is a restatement that names it. The reader B.2 is written for looks a number up and does not read the section front to back, and B.1's `Mz` being identically zero means nothing on the page would otherwise warn them the two differ in sense. | OR-71 |
| **OR-74** | **A notation symbol is data on the value, not a substring of its label.** `LoadValue` gains `symbol`, the third instance of the move `frame` and `point` already made; `net_loads` populates it for every wing root value. The guard reads the field, so a heading may be reworded freely and a symbol that leaves the notation still fails — where parsing could not work at all, since `"Root torsion Myy (25% chord)"` does not end in its symbol. This is the fix for §1.4 and the generalisation `CLAUDE.md` rule 4 asks for. | §1.4 |
| **OR-75** | **The notation guard walks section 3's own tables, not only the appendix's.** The SHALL says "anywhere in section 3"; the guard covered two of its tables, which is why §1.4 shipped. Appendix columns are bare symbols and are checked as strings; 3.3's are prose and are checked through OR-74's field, including that the label actually prints the symbol it declares. | OR-74 |

### 2.2 The OR-15 admission of 2026-09-03 (second)

**Frozen file changed:** `sloads/modules/net_loads.py` — the six root
`LoadValue`s gain `symbol=`. **Admitted by the owner in session under D-6.**
The manifest in `tests/test_frozen_set.py` is updated in the same commit per
G-OR-9.

**Why it prevents progress (OR-15 row 1).** The report cannot be built
*truthfully* without it: §3.3 prints a column heading naming a symbol the
report's own notation table does not define, against a SHALL the report states
about itself. The alternative — a guard that parses the symbol back out of
display prose — is not available, because the label the parse would have to
handle (`"Root torsion Myy (25% chord)"`) does not put the symbol where a parse
could find it, and two different labels carry the same symbol. Leaving it
unfixed means shipping a document that breaks a rule it prints.

**No oracle moves.** The change is a defaulted field on a result type and a
keyword on six constructor calls. No value, unit, key or label changes, and
`report.render.results_to_rows` builds its columns explicitly, so no CSV and no
Imperial digest is touched.

**`SCHEMA_VERSION` bumps to 60, with an identity hop.** The draft asserted the
opposite — that `LoadValue` is a result `Project` holds no field of, on the
`BalancedCaseResult` precedent — and the fields-hash tripwire refuted it:
`LoadValue` **is** persisted, inside `critical.conditions[].loads`, which
`io.py` reads through `_filtered` and the writer emits by `asdict`. That is
exactly the case the tripwire exists to catch, and it caught it. The precedent
that actually governs is one class nearer: **v58 added `LoadValue.frame` and v59
added `LoadValue.point`**, each additive, each an identity hop, each a shape
change for this same persistence reason. `symbol` is the third, so v60 gets
`migrations._hop_59` (identity), a `tests/fixtures_schema/v60_current.json`, and
the bundled examples re-stamped.

---

### 2.3 The decisions as they were put

**D-1 (the decision this note exists for). Is OR-70 reversed?**
- (a) **Reverse it**: B.2 gains an `Mzz` column, and the appendix becomes the
  full set the closure gate names. Cost: §3; ~1 line of `_CUMULATIVE_LOADS`,
  one recurrence line, one notation row, table-note wording, doc edits. No
  export changes, so the Imperial digests do not move.
- (b) **Keep it**, and instead fix the *statements*: correct the stale "not
  delivered" comment, restate OR-70's reason as the one that survives review
  (which is not the convention argument — see D-2), and add the notation row.
- (c) Keep it and say nothing. Not recommended: §1.3's disagreement stays in the
  tree, and §1.4's defect is still there.

**D-2. If OR-70 is kept, what is the reason of record?** The convention argument
does not survive §1.1. A defensible replacement is *scope*: chord bending is not
a wing-sizing quantity for these airplanes, and the appendix is a sizing deck.
But that reason has to hold against §1.2's numbers, where `|Mzz| > |Myy|` on four
of five cases. The owner should either state a reason that survives, or reverse.
**A decision of record with a rationale that has been shown false is worse than
either outcome.**

**D-3. Does 3.4 get a fifth figure?** OR-55 says no, on drawing cost. This note
does **not** propose reopening it — a table and a plot are different asks, and
§1.2's numbers argue for the lookup, not the curve. Flagged so the ruling on D-1
is not silently read as a ruling on OR-55.

**D-4. Which milestone?** 0.8.2 is a report milestone and B.2 is a report table,
so the work is in scope by OR-6. Against: the milestone is at §2, and #154/#160
are already held. §1.4's defect argues for 0.8.2 regardless of D-1, since it is
a broken SHALL on content already issued.

**D-5. Does the report state `Mzz`'s sign relative to `Mz` in B.2's own note, or
rely on the notation table?** The notation table is the SSOT and already carries
it (§1.1). A second statement in B.2's note is a second home for a convention —
`CLAUDE.md` rule 3 argues for the cross-reference, not the restatement. Default:
B.2's note points at 3.2 and does not restate.

**D-6. How does the widened guard read a §3.3 heading?** The appendix headings
are bare symbols (`Mxx (lb-in-ULT)`), so the existing `split(" (")` works.
§3.3's are phrases (`Root chord bending Mzz (lb-in-ULT)`) built from
`LoadValue.label`, so the guard needs a rule: match the heading's **last word
before the units** against the notation, or make `LoadValue.label` carry the
symbol in a fixed position. The second is the structural fix but reaches into
`sloads/modules/net_loads.py` — a **frozen file**, needing an OR-15 admission.
Default: the guard's own rule, and the module untouched.

---

## 3. As built

### 3.1 Code

| File | Change |
|---|---|
| `sloads/models/results.py` | `LoadValue` gains `symbol: str = ""`, documented as the third instance of the `frame`/`point` move (OR-74). |
| `sloads/modules/net_loads.py` **(frozen — OR-15, §2.2)** | The six root `LoadValue`s carry `symbol=` (`Sz`, `Mxx`, `Myy`, `Myy`, `Sx`, `Mzz`). Both torsions are `Myy`: the axis qualifier separates the labels, not the quantity — which is why "the last word of the label" was never a usable rule. |
| `tests/test_frozen_set.py` | The `net_loads.py` manifest hash, updated in the same commit per G-OR-9. |
| `sloads/report/oracle_sections.py` | `_CUMULATIVE_LOADS` gains `("mzz", "moment", "Mzz")`; the stale "not delivered by this analysis" comment is replaced with what the column is and why it is there (OR-71). |
| `sloads/report/oracle_sections.py` | `_NOMENCLATURE` gains `("Mzz", "Chord bending moment about Z", "moment", "cumulative")`; the table's note names all three beam symbols and states that `Mzz` is the negation of a body-axis `Mz` (was: "a chordwise bending would not", forward-referencing a column that did not exist). |
| `sloads/report/oracle_sections.py` | `_derivation_note` prints the fifth recurrence `Mzz(i) = Mzz(i+1) + Sx(i+1) dy` and names the `Sx`-into-`Mzz` term as a position transfer alongside the `Sz`-into-`Mxx` one. |
| `sloads/report/oracle_sections.py` | `_cumulative_table`'s note restates the sign and names 3.2 as the definition (OR-73). |
| `sloads/report/oracle_sections.py` | `_DISTRIBUTION_FIGURES` gains `("wing_chord_bending_mzz", "mzz", "moment", "Chord bending Mzz")` (OR-72). |

B.1, the export, `wing_span_loads.csv` and the whole of `sloads/modules/`'s
arithmetic are untouched. No number changes value: a column the result already
carried becomes a column that is printed.

### 3.2 Standard

- `ORACLE_REPORT.md` §3.3: the "Appendix B is a structures deck" bullet lists
  B.2 as `Sz`, `Sx`, `Mxx`, `Myy`, `Mzz`; the 3.4 bullet lists five figures;
  new bullets record OR-71 … OR-75; §8 gains the matching Conformance rows.
- `docs/30_future/46_applied_wing_load_set_note.md` §2: OR-70 marked
  **superseded by OR-71**, the row kept rather than deleted.
- `docs/30_future/44_oracle_report_note.md`: OR-55's `Mzz` sentence marked
  **superseded by OR-72**; §2.2's admission recorded beside the first one.
- `docs/20_theory/00_theory_sources.md`: no new citation — the `Mzz` recurrence
  is already carried by the WINGINER row (`1g drag Mzz=ΣSx·dy`); the tier-L
  citation requirement is met by that row, stated here rather than duplicated.

### 3.3 Gates

| Gate | Where |
|---|---|
| **G-OR-39** | B.2 prints `Mzz` and every printed value equals the module's own station `mzz` scaled by that case's safety factor, for every row of every case. `tests/test_oracle_report.py::test_the_cumulative_table_carries_the_chord_bending` |
| **G-OR-40** | B.2's note states that its moments are the beam's own and that `Mzz` is the negation of a body-axis `Mz` (OR-73). `…::test_the_cumulative_table_says_its_moments_are_the_beams_own` |
| **G-OR-41** | The set of quantities 3.4 plots equals the set B.2 tabulates (OR-72) — a column cannot arrive unplotted by omission. `…::test_every_cumulative_column_is_also_plotted` |
| **G-OR-42** | Every `LoadValue` section 3 renders declares a `symbol`, that symbol is defined by 3.2's notation table, and the value's own label prints it (OR-74/OR-75). `…::test_section_three_defines_every_symbol_its_tables_use`, widened from the two appendix tables to 3.3 as well |
| **G-OR-43** | 3.2 prints a recurrence for every column B.2 carries, `Mzz` included. `…::test_section_three_states_how_the_cumulative_loads_are_built` |

### 3.4 Verification

```bash
.venv/bin/ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/
.venv/bin/mypy
.venv/bin/python -m pytest
```

The Imperial digests are expected **not** to move: `results_to_rows` builds its
columns explicitly, so a defaulted field on `LoadValue` reaches no CSV, and no
export changed. A digest that does move is a finding, not a regeneration.

Before closing, compile the GA6 `report.tex` and read B.2 and 3.4: B.2 goes from
7 to 8 columns on a landscape `small` table (widest cell a six-figure moment),
and 3.4 goes from four figures to five.

### 3.5 Closure

Tier **L** (§0): this note AGREED, the `theory_sources.md` position stated in
the PR per §3.2, `changes/<slug>.fixed.md` + `.changed.md` + a full-step-format
`changes/<slug>.history.md`, and the frozen-set manifest updated in the same
commit naming its OR-15 authority.
