# Oracle GUI code review + backlog re-cut (milestone 0.7.2)

**Status (2026-08-24): CLOSED — §5 decided by the owner, all three the recommended
way.** The narrow half of #71 came into 0.7.2 with the row-counter fix; **#79** and
**#46** stay in 0.8.0. The row-counter defect (§3.1 + §3.2) and the #71 half (§3.3)
were implemented and closed the same session
(`changes/oracle-row-counter-not-a-delete-key.*`); the table in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) carries the re-cut. One
correction to §5.1 recorded in the closure: narrowing `_NOT_READY` to
`MissingInputError` alone — which §3.3 implied — breaks the *documented* error
contract, because a module raises a bare `ValueError` for input that is present but
unusable (`torque_factor` on a missing cylinder count, caught immediately by
`test_oracle_journey`). Only `ZeroDivisionError` was removed.

**Superseded status (as raised): OPEN — awaiting owner decisions on §5.** Requested by the owner
before closing 0.7.2, to answer three questions: what else belongs in **0.7.2**, what the
revised **0.8.0** (oracle-GUI development) should carry, and what the proposed **0.9.0**
(main-GUI development and bug correction) should carry. Milestone branch `dev/v0.7.2`;
the seven `b`-class items of 0.7.2 (#76/#81/#82/#83/#84/#85/#86) are closed and committed.
The release cut was started and **walked back** at the owner's direction so this review
could run first.

## 1. Aim and method

A **code** review of `oracle_app/` and `app_shell/` (2,676 lines across 12 modules), plus
a review of `docs/30_future/` for the re-cut. Deliberately *not* a second functional
walkthrough: the C210 build review (2026-08-23) did that from the outside and produced 51
findings, whose unfixed remainder is already filed as #67–#74 and #77–#80. The gap that
review could not see is the code beneath it, which is what this one reads.

Owner rulings taken as given for the allocation (2026-08-24, in session):

1. **0.7.2 admits defects with a first-order effect on shipped output, at any size.**
   Presentation, UX and capability wait.
2. Rows are placed **by fix site** — work whose implementation is in the shared
   `app_shell/` lands in 0.8.0 with the oracle work, even when the main GUI benefits.
3. **The mission stays at 1.0.0**, behind both GUI milestones. §5.4 states the resulting
   delay explicitly, so it is a recorded choice rather than drift.

Findings carry **descriptive names, not a new ID series** (`CLAUDE.md` rule 5). Every
claim below was reproduced headless against `examples/ga6_normal.project.json`; the
transcripts are in §3.

## 2. Verdict

**Two first-order defects, both in one function and both new.** `oracle_app/form.py`'s
`render_table` row-count widget destroys data on one path and attaches invalid data on the
other. Everything else this review turned up is either already filed (#70, #71, #72) or
latent with no live trigger (§4).

That the two live defects sit in the same eight lines is worth stating plainly: the rest
of the shell reads as carefully built, and the section below on **what was checked and
found sound** (§4.3) is longer than the defect list. The row-count widget is the one place
where a widget writes to the project's own attached list during a render pass, and it is
the only place in either GUI that calls `.pop()` on user data (`app/views/` has none).

| Finding | Class | Live? | Proposed |
|---|---|---|---|
| **Row-count widget deletes rows with no confirmation or undo** | defect, data loss | **yes** | 0.7.2 |
| **Row-count widget attaches a blank row that breaks downstream pages and saves to disk** | defect, first-order | **yes** | 0.7.2 |
| Results renderer reports genuine failures as "cannot run yet" | defect, diagnosis | yes | 0.7.2 (narrow half) or 0.8.0 — §5.1 |
| Non-owner marking cannot reach a composite field | latent | no | 0.8.0 (drift guard) |
| A result block with rows and no artifacts raises in `st.columns(0)` | latent | no | 0.8.0 (nit) |

## 3. Findings

### 3.1 The row-count widget deletes rows with no confirmation and no undo *(0.7.2)*

`render_table` sizes a list record from a `st.number_input`, then reconciles the model to
it in place (`oracle_app/form.py:797-804`):

```python
count = st.number_input(..., min_value=0, value=len(rows), step=1, ...)
while len(rows) < count:
    rows.append(seeded(cls, prefix, len(rows), ...))
while len(rows) > count:
    rows.pop()
```

`rows` is the project's own attached list, so both loops mutate the project during the
render pass. Typing a smaller number — or one stray click on the widget's `−` stepper —
deletes rows immediately and irrecoverably:

```
items before: 24
count widget: ('Items — rows', 'g0::weight.items[].count', 24)
items after count=3: 3
items after count=21 again: 21
names now: ['Wing, outboard', 'Horiz tail', 'Vert tail', '', '', '']
```

Raising the count back does not restore anything: the rows return as blanks. The only
recovery is reloading the file, which discards every other unsaved edit in the session.

**Effect is first-order.** The weight item database is the mass SSOT (D-25b): it drives
`Project.mass`, the CG cases, the inertias SELECT balances with, the fuselage beam
distribution and every exported deck. And a project truncated this way saves silently —
which is the exact scenario `app_shell/widget_keys.py` documents as the reason the
generation stamp exists ("all 21 `weight.items` … were popped, and saving from there put
the emptied project on disk"). That defect (#51) blocked the 0.7.0 cut. The stamp fixed
the *state-triggered* path; the user-triggered path through the same widget was never
closed.

**A second path, latent today.** The retained count also beats the model when the project
is mutated underneath it without being *replaced* — no generation bump covers that, which
is precisely the remainder `02_parked.md` L-8d parks. Six items added to the project by
another writer vanish on the next render, with no user interaction at all:

```
render 1 — items: 24
mutated to      : 30
render 2 — items: 24
survivors       : ['6th person', 'Fuel to gross wt', 'Ballast']
```

No writer inside the oracle GUI grows a registry list today, so this half is **latent** —
but #78 (item table seeded from the weight estimate) is exactly such a writer, and it is
already planned. Fixing the widget now closes both.

### 3.2 The row-count widget attaches a blank row that breaks downstream pages *(0.7.2)*

The other loop is worse, because the row it attaches is not empty of consequence.
Incrementing the CG-cases count on the Weight & Mass page:

```
cg_cases before: 7 | flight cases: 4
cg_cases after : 8
new row        : CG8 w= 0.0 xcg= 0.0 analyses={AnalysisKind.FLIGHT}
flight cases   : 5
envelope: ZeroDivisionError float division by zero
```

The seeded row carries weight 0 at station 0 and is tagged `FLIGHT`, so `cg_cases.flight_cases`
picks it up and `build_envelope` divides by its zero weight. **The entire Flight Envelope
and SELECT stop working** — and because the results renderer catches `ZeroDivisionError`
(§3.3), the page says "cannot run yet", which reads as *not finished entering* rather than
*you just broke it*. In the C210 build that same sentence hid #81 for a whole session.

Three things compound here:

- The blank row is **attached immediately**, not on commit. `commit_pending`'s
  blank-record rule (OG-F) governs records this pass *created*; a row appended to an
  already-attached list is outside it.
- It **saves to disk** in that state, and reloads as a real CG case.
- The page's own caption says the opposite of what happened: *"Table rows with an empty
  cell are not saved — fill every column to keep the row."* That is true of grid cells
  (`_cell_in`'s NaN guard, `render_curve`'s partial-row rule) and false of count-widget
  rows, which attach fully blank. A user who reads the caption is told the tool protects
  them from exactly the state it just created.

**Suggested shape of the fix** (one site, both findings): the count widget stops being a
destructive editor. Rows are added by an explicit **Add row** action and removed by a
per-row control that confirms (which is #72's "per-row delete", promoted from nit to
defect fix by §3.1); the model wins over a retained count whenever they disagree; and a
seeded row is held out of the project until it is no longer blank — the rule
`commit_pending` already applies one level up, extended to list rows, so the page's
caption becomes true rather than aspirational.

### 3.3 Genuine failures are reported as "cannot run yet" *(already #71 — scope decision in §5.1)*

`oracle_app/results.py:84`:

```python
_NOT_READY = (ValueError, ZeroDivisionError)
```

`MissingInputError` subclasses `ValueError`, so this catches **every** `ValueError` in the
calc, plus `ZeroDivisionError`, which is not a `ValueError` at all and is never a
"not ready" signal — it is arithmetic that went wrong. This is filed as #71 (PB-18) and
remains open. Two things this cycle add to it: #76's loader now raises `ValueError` by
name for a malformed numeric container, and #81's `balance_configs` now raises
`MissingInputError` for a zero stall CL — both of which are *good* messages that this
catch renders as the same flat "cannot run yet — <message>", with no type, no location and
no traceback (C210-24). It is also what hides §3.2 from the user.

## 4. What was checked and found sound

Recording the negative results, because they say where not to look next.

### 4.1 Units — the #86 class does not recur in the shell
`app_shell/limit_csv.py` declares the wing and fuselage station moments as `lb-in`
(`_WING_UNITS`, `_BODY_UNITS`). Verified against the producers rather than assumed:
`net_loads` publishes `LoadValue(..., "lb-in")` for root Mxx/Myy/Mzz and
`BodyStationLoad`'s docstring states inch-pounds. The tail chordwise table converts
`lt25`/`lt50` through the `lbf` channel; a spot check of the module's own `"lb"` channel
gives 925.0128 lb → 4114.66 N (×4.448, force, not mass). No 12× and no 9.8× anywhere in
this file.

### 4.2 The unit boundary and widget identity
`unit_number_input`'s untouched-value guard (return the caller's Imperial value when the
widget comes back equal to the seed) is correct and is what stops an SI project drifting a
hair per render; bounds convert with the value. `widget_key` handles `None` and is
idempotent within a generation. The sidebar's upload handler is edge-triggered on the file
identity, recorded *before* the guard so Cancel genuinely cancels. `stop_page`/the
reserved sidebar slot ordering (#64) does what its docstring claims.

### 4.3 Not defects
- **Download-button keys are not generation-stamped** (`results.py:312`). Harmless: the
  payload is passed by value on the same render, so there is no stale state to serve.
- **`render_tuple` has no `None` guard** where `render_scalar` has one. I tried to drive a
  cleared member through it and could not: the widget does not return `None` for a
  float-seeded input. Not filed.
- **Composite fields never render a non-owner mark** (`_copy_note` is reachable only from
  `render_scalar`). Zero composite non-owner rows exist in the registry today, so this is
  latent — a drift guard, not a defect (§5.2).

## 5. Proposed re-cut

### 5.1 0.7.2 — add one row (owner decision on a second)

| Add | What | Tier |
|---|---|---|
| **The oracle row-count widget is a destructive editor** — §3.1 + §3.2, one fix site | data loss on count-down; a blank row attached, saved, and breaking the envelope on count-up; the page's "not saved until complete" caption made true | M |

**Owner decision:** whether to pull the **narrow half of #71** into 0.7.2 with it —
dropping `ZeroDivisionError` from `_NOT_READY` and catching `MissingInputError` rather
than every `ValueError`. It is not itself wrong output, so it does not meet the stated
0.7.2 bar; but it is what makes §3.2 invisible, and the two share a symptom. My
recommendation is **yes, the narrow half only** (the type/traceback presentation half,
C210-24, stays in 0.8.0 with #73).

Nothing else found in this review meets the 0.7.2 bar.

### 5.2 0.8.0 — oracle-GUI development

Existing rows, unchanged in content: **#67** (gate rot), **#68** (schema notice),
**#69** (page-order dependencies), **#70** (unit radio beats a loaded project),
**#71** (error masking — remainder), **#72** (clearable Optionals, per-row delete),
**#73** (form presentation, the 26-finding C210 family), **#74** (note 32 drift),
**#77** (geometry-page presentation + the SELECT table shape), **#78** (oracle half).

Placed here **by fix site** per the owner's ruling, though both GUIs benefit:
**#80** (sidebar Tools — one shared `app_shell` implementation), **#70** (the shell's unit
radio).

New from this review: the **composite non-owner drift guard** (§4.3) — a guard asserting
that every non-owner field in the oracle input set is one the renderer can actually mark,
so the first composite one cannot ship unmarked; and the **`st.columns(0)`** guard in
`render_results`.

**Owner decision:** **#79** (flutter-clearance removal) is neither GUI — its fix site is
`mach_limit.py`, `report/content.py` and the design-speeds doc. It is an owner directive
and arguably misleading shipped content. I have left it in 0.8.0 rather than moving it to
0.7.2 or 0.9.0; say if it should move.

### 5.3 0.9.0 — main-GUI development and bug correction

**#5/#29** (GUI review resumption — the five unswept sections; this is the milestone's
anchor), **#78** (main-GUI seed-button half), **#21** (main half), and, promoted from
`02_parked.md` at that review's re-cut as the current table already anticipates:
**L-8c** (Results Review omits the eight folded modules), **L-8e** (uncovered input fields
and UX nits), **L-8f** (display-only nits), **M4-11b** (the six F/E-complexity view
functions), and the mutation half of **L-8d** — which §3.1's second path shows is a real
mechanism, not a theoretical one.

**#46** (docs/CI conformance sweep) is hygiene belonging to neither GUI. It is small and
independent; I would keep it in 0.8.0 rather than let it slip two milestones.

### 5.4 1.0.0 — unchanged, with the delay stated

Band C is unchanged: **#14** (aileron lift increment), **#7a** (wing fuel as a distributed
band — the owner's C210-50), **#31** (ground-case fuselage stations), **#32** (past-fit
markers), **#47** (certification basis / case manifest).

**Recorded consequence of the ruling in §1.3:** the project's stated primary deliverable —
the full-span balanced free-free airplane model and the demonstrated concept-loads → sbeam
sizing loop (plans 09/11/12, notes 21/24) — now sits behind **two** GUI-focused releases.
At the observed cadence of this milestone that is a substantial deferral of the mission
the backlog's own §Mission names first. This is the owner's explicit choice, taken with
the alternative (re-ranking mission rows against the GUI rows on merit) offered and
declined; it is written here so a later reader finds a decision rather than a drift.

## 6. What this review did not cover

`app/views/` (21 modules) — that is #29's subject and the 0.9.0 anchor; the only claim made
about it here is the grep result that it contains no `.pop()` on user data. The pure-calc
package beyond the shell's own call sites. And a functional walkthrough of the fourteen
pages, deliberately (§1).
