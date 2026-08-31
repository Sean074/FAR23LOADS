# WTENV's aft edge — completing the loading-envelope port

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-08-31 (owner, in session — `CLAUDE.md` rule 1's
working-alone path); nothing built.** Milestone: **0.8.2**, admitted under
note 44 **OR-15 row 1** by owner decision in the same session. Closure tier **L**.

`WTENV.BAS` computes **two** edges of the useful-load envelope — a forward one
and an aft one — by sorting the discretionary items ascending, sweeping,
re-sorting descending, and sweeping again. Our port implements the ascending
sweep only. This note settles completing it: the aft edge, the per-vertex item
name and waterline the original also prints, the oracle that locks all three,
and the fixture question that decides where the oracle test can live.

The occasion is section 2.2 of the oracle technical report (note 44), which is
to carry the p140 figure. The *reason* is that the port is short an output the
manual prints — a defect that exists whether or not the figure is ever drawn.

Sources reviewed: `reference/FAR23Loads_Code.pdf` Appendix C pp. 382–383
(`WTENV.BAS` listing), Ch 3 pp. 21–22, Appendix A pp. 138–140;
`sloads/modules/weight_envelope.py`; `docs/20_theory/00_theory_sources.md`
(the `weight_envelope` row); `docs/30_future/44_oracle_report_note.md` §6;
`app/views/weight_mass.py` `_tab_envelope`.

---

## 1. The evidence

### 1.1 The original computes both edges

`WTENV.BAS`, Appendix C p. 382–383, read from the page rendered at 300 dpi
(the OCR text layer for these lines is garbled; the printed lines are
unambiguous):

```
180 PRINT "SORTING IN ASCENDING ORDER OF FUSELAGE STATIONS ..."
200 FOR I=N+1 TO M-1
210   FOR J=I+1 TO M
220     IF X(I)<X(J) THEN GOTO 260
230-250   ... swap items I and J ...
260   NEXT J
270 NEXT I
280 PRINT "NOW PRINTING FORWARD EDGE OF ENVELOPE"
330 GOSUB 657
390 PRINT "NOW SORTING IN DESCENDING ORDER OF FUS STA ..."
400 FOR I=N+1 TO M-1
410   FOR J=I+1 TO M
420     IF X(I)>X(J) THEN GOTO 460
430-450   ... swap items I and J ...
460   NEXT J
470 NEXT I
490 PRINT "NOW PRINTING AFT EDGE OF ENVELOPE"
500 GOSUB 657
```

One sweep subroutine, called twice, with the sort reversed between the calls.
The subroutine (657–795) accumulates weight, `S2 = Σw·x` and `S3 = Σw·z` from
record 1, begins printing at the minimum-weight record, and prints three
columns per vertex:

```
760 IF I=N THEN LPRINT USING B$;"MINIMUM WEIGHT",XBAR,ZBAR,S1
770 IF I>N THEN LPRINT USING B$;N$(I),XBAR,ZBAR,S1
```

So the original emits, per vertex: **the name of the item just added**, the
fuselage station, **the waterline**, and the cumulative weight.

### 1.2 What we ported

`weight_envelope._forward_sequence` performs the ascending sweep and returns
`(weight, station)` pairs. `loading_envelope_points` is its public face. The
module's fourth `ConditionResult`, *"Forward loading envelope (weight, station)"*,
publishes them as `point_<i>_weight` / `point_<i>_station`.

Three of the original's outputs are therefore absent: **the aft edge**, **the
item name per vertex**, and **the waterline per vertex**. Nothing about the
port is wrong; it is incomplete, and it has been since the module was written.

### 1.3 The manual runs WTENV on two different data bases

This is the fact that decides the fixture question, and it is easy to miss.

| | Data base | Max loading |
|---|---|---|
| **Ch 3 pp. 21–22** | the GA6 database **without** a baggage row | 3322 lb @ 84.56 in |
| **Appendix A pp. 138–139** | the same database **plus** `66 BAGGAGE 120.00 @ 180.00` | 3442 lb @ 87.89 in |

`examples/ga6_normal.project.json` is the **Ch 3** database — its seven
discretionary rows carry no baggage, and its forward sweep terminates at
3322 @ 84.56. That is deliberate and load-bearing: the Ch 3 ballast oracle
(78 / 418 / 158 lb, `theory_sources.md`) is computed *from* 3322 @ 84.56,
2982 @ 77.10 and 2642 @ 72.74. Adding a baggage row to `ga6_normal` to reach
Appendix A would move all three and break that lock.

Ch 3 prints no edge table at all; it directs the reader to Appendix A
("*The resulting envelope of all possible loading and the structure limit
envelope are plotted on the figure in the example loads report in appendix A*",
p. 22). **The only printed edge tables in the manual are Appendix A p. 139, on
the with-baggage database.**

### 1.4 The oracle reproduces, on all three printed columns

Both edges, swept from the p138 database, against p139 as printed
(`XBAR ZBAR WEIGHT`):

| Added | computed | printed |
|---|---|---|
| MINIMUM WEIGHT | 73.09 90.72 2063.0 | 73.09 90.73 2063.0 |
| **Forward edge** | | |
| FUEL TO FULL | 72.58 90.11 2472.0 | 72.58 90.11 2472.0 |
| COPILOT | 72.74 90.75 2642.0 | 72.74 90.75 2642.0 |
| 4TH / 3RD PERSON | 75.05 91.30 2812.0 | 75.05 91.31 2812.0 |
| 3RD / 4TH PERSON | 77.10 91.80 2982.0 | 77.10 91.80 2982.0 |
| 6TH / 5TH PERSON | 81.03 92.24 3152.0 | 81.03 92.24 3152.0 |
| 5TH / 6TH PERSON | 84.56 92.64 3322.0 | 84.56 92.64 3322.0 |
| BAGGAGE | 87.89 93.24 3442.0 | 87.89 93.25 3442.0 |
| **Aft edge** | | |
| BAGGAGE | 78.97 91.78 2183.0 | 78.97 91.79 2183.0 |
| 5TH PERSON | 84.10 92.38 2353.0 | 84.10 92.38 2353.0 |
| 6TH PERSON | 88.54 92.89 2523.0 | 88.54 92.89 2523.0 |
| 3RD PERSON | 89.96 93.34 2693.0 | 89.96 93.34 2693.0 |
| 4TH PERSON | 91.21 93.74 2863.0 | 91.21 93.74 2863.0 |
| COPILOT | 90.30 94.09 3033.0 | 90.30 94.09 3033.0 |
| FUEL TO FULL | 87.89 93.24 3442.0 | 87.89 93.25 3442.0 |

Every value is inside ±0.1 %; the largest disagreement is 0.01 in on a
waterline, which is the page's own last printed digit.

### 1.5 The printed tie order is an artifact, not a result

Four items tie on fuselage station: `3RD`/`4TH PERSON` at 111.00 and
`5TH`/`6TH PERSON` at 150.00. Both of the `.BAS` comparisons are **strict**
(`<` at 220, `>` at 420) — verified on the rendered page, not from OCR — so
equal elements are swapped and the sort is unstable in both directions.
Simulating that sort on the seven printed discretionary records reproduces the
forward edge's printed label order exactly and **fails** on the aft edge, where
the manual prints `5TH` before `6TH` and `3RD` before `4TH`.

The explanation is that the sort runs over the whole dimensioned array
(`FOR I=N+1 TO M-1`, `M` being the user's answer to *"maximum number of weight
items"*, default 100), not over the occupied records. Blank records carry
`X = 0` and are excluded from the *print* by line 665 but not from the *sort*,
so they migrate through the array and permute the tied real records by an amount
that depends on the declared array size. **The printed tie order is a property
of a 1988 BASIC array dimension, not of the airplane.**

It also cannot change a number: tied items sit at the same station, so the
cumulative `(weight, station, waterline)` triple at each vertex is identical
whichever of them is counted first. Only which of two identical labels attaches
to which of two identical points moves. Hence WE-4.

### 1.6 The aft edge is where the interesting behaviour is

On `ga6_normal` the forward edge never leaves the structural box (72.58 →
84.56 in, against an aft-gross limit of 85.094 in). The aft edge reaches
**87.32 in at 2743 lb** — 2.2 in aft of the aft-gross CG limit at 81 % of gross
weight. Ch 3 p. 21 says this is expected and not a defect: *"The envelope of all
possible discretionary useful load will probably extend beyond the structural
limits for weight and cg range. That is not a problem. The pilot will be
responsible for loading the airplane within the limits for every flight."*

Two consequences. First, a document that plots only the forward edge shows the
half that never approaches a limit and omits the half that exceeds one — the
figure's containment reading would be wrong, not merely partial. Second, the
manual's own claim at Ch 3 p. 22 — *"the General Aviation 6 Place Airplane can
be loaded with six 170 pound people with full fuel and not exceed the gross
weight limit or the aft cg limit"* — is a statement about the loop's closure
that our output cannot currently support.

---

## 2. Decisions (WE-1 … WE-8)

| # | Decision | Rationale |
|---|---|---|
| **WE-1** | **WTENV gains the aft edge**, ported from `WTENV.BAS` 390–500. This is completion of an existing port, not new physics: the same sweep over the same items in the opposite station order. | The program computes it, the manual prints it, and Ch 3 instructs the reader to plot both. A port that emits one of two printed tables is incomplete regardless of what consumes it. |
| **WE-2** | **One sweep, parametrised by direction** — the existing `_forward_sequence` becomes a direction-taking sweep and both edges call it, mirroring the `.BAS`'s single `GOSUB 657` invoked twice. No second implementation of the cumulative walk, in this module or beside it. | The consolidation rule (`CLAUDE.md` rule 3, and the G-3b precedent). A drift-guarded second copy was considered and rejected: the thing it would protect — the freeze — is better served by proving the existing outputs unchanged (G-WE-2) than by not touching the file. |
| **WE-3** | **Each vertex carries the name of the item added and its waterline**, alongside weight and station — the `.BAS`'s three printed columns plus the label of line 770. New `LoadValue` keys only. | These are outputs of the original that were dropped, on the same footing as the aft edge. The name is also what lets a consumer identify a vertex without re-deriving the sort, which OR-6 forbids. |
| **WE-4** | **Ties are broken stably (entry order); the label gate compares up to permutation within an equal-station group.** The `.BAS`'s unstable order is *not* reproduced. | §1.5: the printed order is a function of the declared array size and the blank-record migration it causes, and it cannot move a number. Porting it would mean porting `DIM` as an input. Stable order happens to reproduce the printed aft edge exactly and differs from the printed forward edge only in which of two identical labels sits on which of two identical points. |
| **WE-5** | **The oracle test runs on a new Appendix-A data base, transcribed from p. 138 and held in the test**, not as a shipped `examples/*.json`. `examples/ga6_normal.project.json` is **not** modified. | §1.3: `ga6_normal` is the Ch 3 database and the Ch 3 ballast lock (78/418/158) is computed from its no-baggage maximum. Adding baggage to reach Appendix A would break a standing oracle to gain one. A test-local transcription costs nothing to maintain and keeps the page citation beside the numbers, per the math-fidelity rule. |
| **WE-6** | **No existing output changes.** The four current `ConditionResult`s keep their titles, notes, `LoadValue` labels, keys, units and values on every bundled fixture, and that is asserted rather than asserted-to. | This is the substance of the OR-13 freeze. The freeze exists so the report cannot perturb the solver; honouring it by *proof* is stronger than honouring it by not opening the file, and it is what makes the admission safe to grant. |
| **WE-7** | **The ballast reference selection continues to read the forward edge only.** The aft edge is a reporting output; no delivered load, load factor, CG case or balanced condition moves. | `WTENV.BAS` contains no ballast routine at all — our ballast implements the Ch 3 pp. 21–22 hand calculation, which reasons on the forward loading. Widening it to the aft edge would be a change to a delivered quantity and is out of scope here; if it is ever wanted it is its own note. |
| **WE-8** | **The consumer is section 2.2 of the oracle report**, whose figure draws the closed structural-limit polygon, both loading edges, numbered vertices keyed to a table, and the entered CG cases marked. The report's SHALLs and conformance rows land in `10_standard/ORACLE_REPORT.md` under note 44's protocol (OR-8/OR-9); nothing about report content is decided here. | Keeps the two subjects apart: this note owns the solver's output, note 44 owns what the document says about it. Recorded so the note's purpose is legible without reading the report note. |

---

## 3. Acceptance gates (G-WE-1 … G-WE-5)

| Gate | Assertion |
|---|---|
| **G-WE-1** | On the Appendix-A data base (WE-5), both edges reproduce **Appendix A p. 139** — all 16 printed rows (the minimum-weight vertex heads each edge), all three printed columns (`XBAR`, `ZBAR`, `WEIGHT`) — to ±0.1 %, with the printed numbers and the page citation in the test. |
| **G-WE-2** | On every bundled fixture, the module's four pre-existing `ConditionResult`s are unchanged: same titles, same notes, same `LoadValue` sequence, and every value equal to the pre-change result. The frozen-file admission changes nothing that existed. |
| **G-WE-3** | The Ch 3 pp. 21–22 oracle on `ga6_normal` is untouched — limit stations 85.1 / 77.49 / 72.64, minimum flight 2063 @ 73.09, maximum loading 3322 @ 84.56, ballast 78 / 418 / 158 at their stations. The existing tests carry this; it must still pass unedited. |
| **G-WE-4** | The forward edge produced by the direction-taking sweep is **identical** to `loading_envelope_points(project)` on every fixture — the WE-2 single-owner claim, asserted rather than assumed. |
| **G-WE-5** | Every vertex label on both edges matches p. 139 **up to permutation within an equal-station group** (WE-4), and the group partition itself matches exactly. A label that moves between groups is a failure. |

`G-OR-9` already governs the manifest: the commit that edits
`sloads/modules/weight_envelope.py` updates `tests/test_frozen_set.py`'s
SHA-256 beside it and names its authority — this note plus the OR-15 issue
number — in the message. Not restated as a gate here.

---

## 4. Sequencing

1. **This note PR** (`note/45-wtenv-aft-edge`), merged at `AGREED — no code`.
2. **An issue filed** for the port gap, carrying §1.1–§1.2 as its body. OR-15
   row 1 requires the number in the fixing commit; the issue is also the
   `CLAUDE.md` rule 5 record that this was found by reading frozen code.
3. **The implementation PR** — WE-1 … WE-7, G-WE-1 … G-WE-5, the frozen-set
   hash, the `theory_sources.md` `weight_envelope` row extended with the
   Appendix C p. 382–383 line citation and the p. 139 oracle band, a
   `changes/<slug>.added.md` fragment and a full-step-format
   `changes/<slug>.history.md`. Flips this note to `shipped <date>`.
4. **The §2.2 figure** — note 44's protocol, `ORACLE_REPORT.md` §3.3 SHALLs and
   §8 conformance rows. Separate from step 3 so the solver change stands or
   falls on its own oracle.

Steps 3 and 4 may share a PR only if the owner prefers; the gates are
independent either way.

---

## 5. Risks and what is deliberately not done

- **Scope.** 0.8.2 was scoped as report-only, and this is solver work inside
  it. The admission is OR-15 row 1 and the owner's, taken 2026-08-31 on the
  reasoning of §1.6: the report cannot draw this figure truthfully without it,
  and drawing the forward edge alone would mislead. Recorded here so the
  exception is legible at the 0.8.2 cut rather than inferred.
- **The freeze.** Opening a frozen file for a *view*'s benefit is the pressure
  OR-13 was written to resist. The mitigation is WE-6/G-WE-2: the change is
  provably additive, and the proof is a test rather than a claim in a commit
  message.
- **`ga6_normal` cannot exercise G-WE-1.** It is the Ch 3 database (§1.3), so
  the p139 lock necessarily lives on the WE-5 transcription. The GA6 fixture
  still exercises both edges through G-WE-2/G-WE-3/G-WE-4 — it simply has no
  printed edge table to be checked against.
- **Not done: the aft-edge ballast** (WE-7), **the `.BAS` tie order** (WE-4),
  and **any change to how the GUI's Weight/CG Envelope tab plots today** — the
  tab will gain the aft edge for free through `loading_envelope_points`' sibling,
  but that is display and rides the ordinary rules, not this note.
- **Not done: the `symmetric: true` finding on `examples/baron_58.project.json`**
  (WINGGEOM reports the fin's area and span doubled). Unrelated, found in the
  same reading, and filed separately under OR-14.
