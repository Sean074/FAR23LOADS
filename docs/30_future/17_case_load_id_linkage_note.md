# Design note — case identity ↔ deck LOAD id linkage (report + GUI)

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: shipped 2026-08-13.** Written before code and agreed in chat per
`CLAUDE.md` required practice 1; decision 1 (two LOAD columns) and decision 5
(the `SUBCASE` word kept in the headers) are the user's calls of that date.
Conventions cited, never restated:
[`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md) §4 (case
identity, deck-side identity). Deck-side numbering is M4-2 decisions 8/9/10 and
**D-R7**; the ID taxonomy is `sloads/case_ids.py`.

## 1. What is missing

A consumer holding an sbeam result labelled `SUBCASE 103` can already trace it
back through the deck's own `$` SUBCASE MAP block
(`export/sbeam_bridge.subcase_map_block`) and the case-index **CSV**, which
carries an `ID` column and a `SUBCASE` column
(`sbeam_bridge.case_index_rows_from`, `_CASE_INDEX_FIELDS`).

Neither the **summary report** nor the **GUI** ever states that integer:

* `report/content._case_index_table` emits `ID, Component, Condition, CG, Speed,
  Altitude, FAR, SF` — no deck number. Its note tells the reader the IDs "appear
  in the sbeam FORCE/MOMENT cards" without giving the key to join on.
* The GUI names cases four different ways, each an independent f-string:
  `views/flight_envelope.py` (`f"{c.label} ({cid})"` selection checkboxes),
  `views/loads_plots.py` (`_case_label` + the multiselect `format_func`),
  `views/export_report.py` (the deselection list), `views/results_review.py` /
  `views/balanced_cases.py` (case tables; the latter mentions `SUBCASE` in prose
  only).

So the deliverable's three identities — the SLOADS case id, the deck `LABEL`,
and the deck `LOAD`/`SUBCASE` integer — are stated together in exactly one
artefact (the CSV) and nowhere a human reads.

## 2. Decisions taken

| # | Decision | Alternative rejected |
|---|---|---|
| **1** | **Two LOAD columns, not one** (user, 2026-08-13): the case index carries a *component-deck* LOAD id and an *assembled-deck* LOAD id, each blank where that case has none | One "LOAD" column. Rejected: a case has **two** legitimate deck numbers — `W-05` is `105` in the wing component deck (`case_ids.subcase_id`) and `5105`/`7105`/`8105` in the assembled full-span deck (`balanced_subcase_id`, D-R7). One unqualified column is wrong for whichever family it is not showing, and silently so |
| **2** | Row-level fill: a per-component case fills the component column; a **handed** id (`W-05R`) fills only the assembled column (`subcase_id` deliberately refuses a hand); a symmetric case that appears in both decks fills **both** (`105` and `5105`) | Split the index into two tables per deck family. Rejected: it breaks the one-row-per-`case_id` dedupe that M4-2 decision 1 exists to produce |
| **3** | Elsewhere — the per-module report tables and each GUI page — **one** deck-qualified column, because those views already know which deck family they are showing | Repeat both columns everywhere. Rejected: four more places for the pair to drift |
| **4** | The number's single owner is **`case_ids`**, exposed as `deck_load_id(case_id, family)` (+ a both-families convenience). `sbeam_bridge._subcase_column`'s "which minter, blank if unmappable" logic moves there and `sbeam_bridge` calls it | Import the private `_subcase_column` from `export/` into `report/` and `app/`. Rejected outright: report and GUI must not reach into the export layer's privates, and `CLAUDE.md` rule 3 requires a single-source owner + drift guard the first time a convention is needed in a second place |
| **5** | Column headers name **both** solver words — `LOAD/SUBCASE (component)` and `LOAD/SUBCASE (assembled)` — since the deck uses one integer for both `SUBCASE n` and `LOAD = n`, and consumers grep for either | Pick one word. Rejected: renaming the CSV's existing `SUBCASE` column outright breaks any consumer keyed to it; keeping the word inside the new header does not |
| **6** | A case with **no** `CaseRef` states an explicit blank in both columns, never the positional fallback number | Print `_sid`'s positional fallback (`sid_base + index`). Rejected: that number is exactly the unstable, position-dependent id M4-2 decision 8 removed — publishing it in a document invites a reader to key on it |

## 3. What the linkage reads as

Deck (unchanged, stated here as the target of the join):

```
SUBCASE 103
  LABEL = W-03
  TITLE = PHAA (Nz=3.8, Nx=0.5)
  LOAD  = 103
```

Case index (report table and CSV, same columns and same order):

| ID | LOAD/SUBCASE (component) | LOAD/SUBCASE (assembled) | Component | Condition | CG | Speed (kt) | Altitude (ft) | FAR | SF |
|---|---|---|---|---|---|---|---|---|---|
| `W-03` | 103 | 5103 | wing | PHAA | CGfwd | … | … | 23.333(b) | 1.5 |
| `HT-09R` | — | 7209 | htail | 23.427(a) unsym | … | … | … | 23.427(a) | 1.5 |

GUI, one shared formatter instead of four f-strings —
`W-03 · LOAD 103 · PHAA · FAR 23.333(b)`.

## 4. Files that change

| File | Change |
|---|---|
| `sloads/case_ids.py` | new `deck_load_id(case_id, family)` (+ both-families helper); the handed/unhanded and unmappable rules move here from `sbeam_bridge._subcase_column` |
| `sloads/export/sbeam_bridge.py` | `_subcase_column` becomes a thin call; `_CASE_INDEX_FIELDS` and `case_index_rows_from` grow the second column and the header rename |
| `sloads/report/content.py` | `_case_index_table` grows both columns; its `note` states the join explicitly and points the per-module tables at this table |
| `sloads/report/render.py` | `governing_loads_table` (report §Results, the Critical Loads tab and Results Review all render it) gained `ID` + a component-deck `LOAD` column — decision 3's one qualified column, rather than the pair |
| `sloads/export/balanced_deck.py` | `balanced_case_rows` gained `ID` + an assembled-deck `LOAD`; the deck's own `$` map block now leads with the case id |
| `app/views/flight_envelope.py`, `loads_plots.py` | the case labels an engineer picks from go through `case_ids.case_label`; `export_report.py` passes the assembled cases so the index's second column fills, and `results_review.py` / `balanced_cases.py` inherit the columns through the two shared table builders above |
| `docs/10_standard/CONVENTIONS.md` §4 | the ID ↔ `LABEL` ↔ `LOAD`/`SUBCASE` chain stated once, plus the owner row in §7's table |
| `docs/10_standard/PROGRAM_SPEC.md` | M4-2 decision 10's sentence (Tier M requirement) |

## 5. Gate (CI)

No oracle applies — this is deliverable identity, so the gate is an invariant
test (`CLAUDE.md` practice 2 / rule 3), in `tests/test_case_ids.py` with the
existing uniqueness guard:

| Gate | Assertion |
|---|---|
| the column is the deck's own number | for every case in a full fixture run, the index's component column == the `SUBCASE`/`SID` integer that deck writer actually emits, parsed from the deck text; same for the assembled column against `balanced_deck` |
| no silent blank | a case carrying a `CaseRef` fills at least one of the two columns |
| report == CSV | the report case-index table's rows equal the CSV's rows, column for column |
| handedness | a handed id fills only the assembled column; its unhanded twin id is unaffected |

## 6. Closure tier

Closed 2026-08-13: `CHANGELOG.md` `[Unreleased]`, backlog row removed,
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
("Case identity ↔ deck LOAD id linkage"), `PROGRAM_SPEC.md` (deck case identity)
and `CONVENTIONS.md` §4 + §7. One deviation from §4 as written: the assembled
deck's own `$` map block also gained the case id — it was the one deck family
whose comment block named the condition only, so it could not be joined without
reading its case control, and the gate parses that block.

**Tier M** — behaviour change to existing output (report, CSV header, GUI
labels), so: `CHANGELOG.md` + backlog removal + one-line history entry +
the `PROGRAM_SPEC.md` / `CONVENTIONS.md` sections above. Effort M. Regenerates
the report digest once.

## 7. Sequencing

Shipped alone; **backlog row 1 stays open** and should be taken next ("a wing case row can name a flight
condition its loads were not computed at",
[`00_backlog.md`](00_backlog.md)). Both change the same case-index rows, so the
second one pays a second digest regeneration (this one already spent its own). Row 1's open decision — whether the row's CG / speed
/ altitude / FAR come from SELECT's `CaseRef` or from the case's own `cl` /
`v_eas_kt` — is orthogonal to this note and still unresolved.
