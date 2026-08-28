# Oracle GUI production-release review (milestone 0.8.0)

**Status (2026-08-28): CLOSED — §5 decided by the owner, all four the recommended
way.** §5.1 the Tools unit defect stands **BLOCKS-CUT** (#126); §5.2 the design-note
status finding is **one row** with the guard as its substance (#128); §5.3 the
`Development Status` classifier is **`4 - Beta`** with the mixed state stated by one
owner, implemented in-session (`changes/release-state-and-maturity-classifier.changed.md`);
§5.4 the `use_container_width` migration **splits out of parked `L-8e` into band B**
(#129, carrying the `app/views/` half with it). The five rows are filed as
#126–#130 and `backlog_issues.py check` exits 0.

**Superseded status (as raised): OPEN — awaiting owner decisions on §5.** A pre-cut code review
of the oracle GUI's production surface, run at the owner's request with the aim stated
as *a production release of the Oracle GUI*. Milestone branch `dev/v0.8.0`; band B of
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) holds one open row (#124).

**Verdict up front: not ready to tag — five BLOCKS-CUT rows, four of them tier S and
none of them physics.** No defect was found that moves a load, and no defect was found
in the render/persist core. See §2.

## 1. Aim, scope and method

**Scope of record (owner, in session):** the oracle GUI's *production surface* —
`oracle_app/` + `app_shell/` + `oracle.py` (13 modules, 3,807 lines) and the `sloads`
entry points they consume — read as the shipped product, plus the release gates that
stand in front of it (`RELEASE_PROCESS.md` §3, `docs/30_future/`). The FAR23 calc core,
the export bridge and `app/views/` are out of scope except where a finding in the shell
sweeps into them under rule 4.

**Method — four passes, every claim reproduced headless.** (1) The contract pass: each
module read against note 32's decisions OG-1…OG-14 and its gates G1–G8, and against
`CLAUDE.md`'s required practices. (2) The state pass: widget identity, the persist path,
the dirty guard, the unit boundary and the frame cache. (3) Three **defect-class sweeps**
run as executable probes rather than by reading — the #71 mid-entry planform set, the
blank-Optional set (#121/#122's class), and a blank-row-in-every-list set — each against
all fourteen oracle pages. (4) The release pass: the pre-release checklist, the closure
fragments, the design-note status lines and the dependency floor.

Findings carry **descriptive names, not a new ID series** (`CLAUDE.md` rule 5). Probe
scripts and transcripts are quoted inline in §3.

**Gate state at review (2026-08-27, this session):**

| Gate | Result |
|---|---|
| `pytest` | **3038 passed**, 30 skipped, 1 xfailed, 137.6 s |
| `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/` | clean |
| `mypy` | clean — no issues in 83 source files |
| `build_changelog.py --dry-run` | runs clean; reads as a 0.8.0 release note |

## 2. Verdict

**The surface is sound; the release is not yet assembled.** Every finding below is either
release process, documentation currency, or one display-only defect in this band's own new
feature. Nothing was found in the renderer, the persist path, the widget-identity
mechanism or the results path — the three defect-class sweeps of §3.6 returned **0 failures
in 154 page renders** against exactly the input states that produced #35, #51, #71, #88,
#121 and #122.

| # | Finding | Class | Live? | Proposed |
|---|---|---|---|---|
| 1 | **Band B is not empty** — #124 open; the cut signal is "cut 0.8.0 when band B is empty" | process | — | **BLOCKS-CUT** |
| 2 | **The release smoke gate never launches the oracle GUI** — `RELEASE_PROCESS.md` §3.5 / `scripts/smoke_test.sh` start `app/Home.py` only | process gap | **yes** | **BLOCKS-CUT**, tier S (#127) |
| 3 | **Design note 32 says the oracle GUI is unbuilt; note 35 says "Nothing below is built yet"** — both roll to `40_history/` at this cut in that state | doc currency | **yes** | **BLOCKS-CUT**, tier S ×2 (#128) |
| 4 | **The %MAC ↔ station Tool reinterprets its entered station on a unit switch** — the one converted number input in the codebase outside the unit boundary | defect, display-only | **yes** | **BLOCKS-CUT**, tier S (#126) |
| 5 | **`Development Status :: 3 - Alpha` against a stated production release** | claim | — | **BLOCKS-CUT** (decide, don't drift) |
| 6 | **11 `use_container_width` sites left in `app_shell/` on an unbounded `streamlit>=1.36`** — deprecated with removal scheduled | forward-compat | not yet | KNOWN-ISSUE → 0.8.0 row (#129) |
| 7 | **`oracle_app/form.py` reaches into `field_registry._locate`** — the only private cross-module access in the shell | hygiene | no | band D (#130) |

Findings 2–4 are together perhaps forty lines of change. The band-B row (#124) is already
scoped tier S. This is a cut that is two hours of work away, not a release that needs
rework.

## 3. Findings

### 3.1 Band B is not empty — the cut signal is unmet (BLOCKS-CUT)

The priority table's own signal is *"Band B — 0.8.0 … cut when empty"*. One row stands:
**#124**, the max-continuous-HP precedence written twice. Reproduced:

- `sloads/modules/weight_estimate.py:345-359` — `resolve_max_continuous_hp(project)`:
  `est.max_continuous_hp` if `override_max_continuous_hp`, else
  `math.fsum(e.max_cont_hp or 0.0 for e in engines) or est.max_continuous_hp`.
- `app/views/weight_mass.py:206-208` — the same precedence, inline, over a locally
  computed `_engine_hp_sum` (`sum(...)`, line 118).

The two agree today. They are two spellings of one rule, which is what practice 3 forbids,
and the summation differs (`math.fsum` vs `sum`) so they are not even textually the same
computation. The row is correctly scoped: the view reads the owner, the inline copy is
deleted, and a drift guard lands if a second consumer remains.

One implementation note for whoever closes it: the view cannot call the owner directly as
written — `resolve_max_continuous_hp` takes a `Project` and raises `MissingInputError`
when `weight.estimation` is absent, while the view holds a detached `inp` before Apply.
The owner needs an input-level entry point (`resolve_max_continuous_hp(estimation, engines)`
with the project-level function as a thin wrapper) for the view to have something to call.

### 3.2 The release smoke gate never launches the oracle GUI (BLOCKS-CUT, tier S)

`RELEASE_PROCESS.md` §3.5 is a **hard gate**:

> `scripts/smoke_test.sh` exits 0 — it starts `app/Home.py` headless, checks the root
> page renders (HTTP 200, no traceback in the server log) …

`scripts/smoke_test.sh:56` runs `streamlit run app/Home.py` and nothing else. For a
release whose headline deliverable is the *other* front-end, the one gate that proves a
real Streamlit server boots the entry point does not point at it.

This is narrower than it first looks, and the row should say so: `Oracle.py` **is**
exercised in-process by `AppTest` (`tests/test_app_shell.py:508`,
`tests/test_oracle_gui.py:1252`), so `st.set_page_config`, `st.navigation` and the
sidebar context manager are all covered. What is not covered anywhere is the server boot
and the `sloads-oracle` console script actually launching — `tests/test_oracle_gui.py:1273`
asserts only that `oracle.entry_point_path()` resolves to the right file.

**Done:** `smoke_test.sh` starts both entry points (or takes the entry point as an
argument and is invoked twice), §3.5's checklist line names both, and the
`sloads-oracle` launcher is smoked rather than path-checked.

### 3.3 Two design notes describe the shipped GUI as unbuilt (BLOCKS-CUT, tier S ×2)

`docs/30_future/32_oracle_gui_note.md:5` — the design note of record for the surface
this release ships:

> **Status: AGREED 2026-08-19 … OG-A … shipped 2026-08-19 as an independent tier-S fix;
> **everything else is unbuilt**.

OG-A…OG-F shipped 2026-08-18/20 and eight further issues (#94–#100) were built on them
in this band.

`docs/30_future/35_taildist_aero_state_note.md:11` — same shape:

> Agreed as drafted, with one scope ruling … **Nothing below is built yet.**

It shipped as #100 on 2026-08-27 (`changes/taildist-aero-state.changed.md`;
`sloads/modules/taildist.py:84` `aero_state_values`).

Note 34 is the counter-example and the model: *"AGREED 2026-08-26 …; BUILT 2026-08-27
(#96 …)"*. Notes 36 and 37 both say SHIPPED.

This blocks the cut rather than trailing it because `RELEASE_PROCESS.md` §4 step 3 rolls
the notes into `docs/40_history/` at the cut. A note that says "unbuilt" entering the
permanent record of the release that built it is not a stale file to fix later; it is a
wrong entry in the history.

**Make it structural (practice 3).** `tests/test_doc_currency.py` guards standard docs
against volatile literals; nothing guards a design note's status line. A note whose
issue is closed, or whose `changes/*.md` fragment exists, must not still read AGREED with
an unbuilt claim. That guard is the row, not the two edits.

### 3.4 The %MAC ↔ station Tool reinterprets its station on a unit switch (BLOCKS-CUT, tier S)

`app_shell/sidebar.py:366` renders the station input as a bare `st.number_input` seeded
with a converted length, keyed `widget_key("_tool_station")` — **no unit-system suffix**:

```python
entered = st.number_input(f"Fuselage station ({length_label})",
                          value=float(to_display(ref.xlemac, "length", system)),
                          step=1.0, key=widget_key("_tool_station"))
station = to_imperial_scalar(float(entered), "length", system)
```

Streamlit lets a keyed widget's retained state outvote `value=`. The shell's own boundary,
`components.unit_number_input`, exists to close exactly this: `number_input_name` appends
`_{system}` to the key on the converted path *"so a unit switch re-seeds the field instead
of reusing the stale number"*. This call site does not go through it.

**Reproduced** (`AppTest` over `render_shell_sidebar` on `ga6_normal`, direction
`station → % MAC`, toggling only the units radio):

```
IMPERIAL | Fuselage station (in) = 63.641   ->  % MAC   0.00
SI       | Fuselage station (mm) = 63.641   ->  % MAC -88.29
```

The number does not move, the label changes from `in` to `mm`, and the answer changes by
88 points of MAC. Nothing is stored and no load moves — the Tools panel is display-only
and `test_the_tools_section_writes_nothing_to_the_project` pins that — so this is a wrong
answer on screen, not corrupted data.

**Rule-4 sweep, run:** every `number_input(` call site in `app_shell/`, `oracle_app/` and
`app/views/` was checked. This is the **only** one that converts a quantity and does not
carry the system in its key. `app/views/engine_mount.py`'s `k(name, unitful=True)` and
`app/views/flight_envelope.py`'s `_num` both suffix correctly; `oracle_app/form.py` routes
everything through the boundary. The class does not exist elsewhere.

**Done:** the station input goes through `unit_number_input(..., kind="length")` like every
other converted number in either GUI, and a guard test drives the Tools panel across a unit
toggle and asserts the %MAC answer is invariant — the drift guard practice 3 requires, which
the Tools row (#80) shipped without: `tests/test_app_shell.py` has four Tools tests and none
of them runs in SI.

### 3.5 The production-release claim (BLOCKS-CUT — a decision, not a defect)

`pyproject.toml:17` carries `Development Status :: 3 - Alpha`. The aim stated for this cut
is a production release of the oracle GUI. The classifier is a claim made to anyone who
installs the package, and the `About` panel's *"results are **not certified** …"* notice
is a different claim about a different thing. Either the classifier moves to
`4 - Beta` / `5 - Production/Stable` at the version bump, or the release is described as
what the classifier says it is. Recorded here so the cut makes the choice deliberately.

### 3.6 What was checked and found sound

This section is longer than the defect list, which is the honest summary of the surface.

**Three defect-class sweeps, run as probes, 0 failures in 154 page renders.**

1. **Mid-entry planform (#71's class).** The nine `_MID_ENTRY` mutations from
   `tests/test_derived_geometry.py` (`le[:1]`, `te[]`, `te=le`, `swapped`, `zero span`,
   `dup station`, `elements=1`, …) applied to `ga6_normal`'s wing, each rendered on all
   fourteen oracle pages: **0 bad of 126**. Every one refuses by name through `_NOT_READY`.
2. **Blank Optional (#121/#122's class).** Every Optional scalar in
   `field_registry.oracle_input_paths()` set to `None` simultaneously, all fourteen pages:
   **0 bad of 14**. This is the class that crashed `app/views/flight_envelope.py` with
   `float(None)` — the oracle GUI's registry-derived renderer is immune to it by
   construction, because it asks the annotation what widget to build.
3. **Blank rows in every list.** A blank project with one seeded row appended to each of
   the eleven list records the oracle pages carry (`weight.items[]`, `weight.cg_cases[]`,
   `engines[]`, `aero.surfaces[]`, `geometry.surfaces[]`, `geometry.fuselage.sections[]`,
   `wing_mass.cases[]`, `wing_mass.concentrated[]`, `fuselage_mass.stations[]`,
   `tail_mass[]`, `tab_loads.tabs[]`), all fourteen pages: **0 bad of 14**.

**The grid/unit interaction, checked and correct.** The suspicion was that
`st.data_editor`'s retained edit state, keyed without a unit suffix, would survive a unit
toggle and be re-applied against a converted frame. It does not: the column headers carry
the unit (`X (in)` / `X (mm)`), so a system switch invalidates the edit keys and Streamlit
drops them. Walked headless — an Imperial edit of `weight.items[0]` to `X = 100` persisted
as `x = 100.0`, and the SI toggle left it at `100.0` with the editor state emptied. The
`_stable_frame` cache key already carries `system.value`.

**The unit boundary itself.** `unit_number_input`'s three modes, the per-system key suffix
on the converted path only, the untouched-field short circuit that returns the caller's own
Imperial float rather than round-tripping it, the Imperial-in bounds conversion, and
`_seeded_number`'s pinning of a disabled widget to its governing seed — all read correct
and all carry tests. `clear_number_input`'s key derivation was checked against all four
render paths in `form.render_scalar` (int, converted float, fixed-unit, dimensionless);
they agree in every case.

**Widget identity.** The generation stamp is applied at every project-seeded call site;
`widget_key` is idempotent within a generation. (Noted and dismissed: stamping an
*already-stamped* key from an older generation would nest — `g12::g1::foo` — but no call
site stamps across a generation boundary, and `tests/test_widget_freshness.py` guards the
one that would matter.)

**Note 32's gates.** G1 (no dual path: no calc, no unit factor, no private CSV writer in
`oracle_app/`), G2 (the page set derived from `workflow.oracle_steps()`, no page list in
the GUI), G6 (round-trip), G7 (download payloads read directly, one call site), G8 (the
shell owns what both GUIs share) are all enforced by `tests/test_oracle_gui.py` (88 tests)
and `tests/test_app_shell.py` (30). The `set_page_config`-once rule holds.

**The results path.** `_NOT_READY = (ValueError,)` is correct against the documented error
contract — `MissingInputError` subclasses `ValueError` (`sloads/models/inputs.py:33`) and
`ZeroDivisionError` is deliberately outside it (#71). The `st.columns(0)` guard, the
grouped sub-tables, the LIMIT/ULTIMATE captions and the traceback expander all check out.

**The sidebar's ordering contract.** The reserved-slot pattern (units → slot → tools →
about, slot filled in `finally` after `pg.run()`), `StopPage` as a `BaseException` so a
view's `except Exception` cannot swallow it, and the edge-triggered uploader are each
non-obvious and each right for a stated reason.

**Closure hygiene.** `build_changelog.py --dry-run` assembles a coherent 0.8.0 across
Added / Changed / Fixed / Removed with tier and issue on every bullet; the tier-M/L items
each carry their `history` fragment. Spot-checked #93, #96, #97, #100, #123 — all present
at the right depth.

### 3.7 Two hygiene rows (not blocking)

**`use_container_width` on an unbounded Streamlit floor.** Eleven sites remain in
`app_shell/` (`sidebar.py` ×7, `project_state.py` ×4) while `oracle_app/` has already
migrated to `width="stretch"`. Streamlit 1.58 documents the parameter as *"deprecated and
will be removed in a future release"* on both `st.button` and `st.dataframe`, and
`pyproject.toml:29` pins `streamlit>=1.36` with **no upper bound** — so the release that
removes it breaks Open / Save / Download / Build-results-zip in *both* GUIs for anyone who
installs fresh. The item is currently parked inside `L-8e`, a main-GUI omnibus row; by the
2026-08-24 re-cut's rule 2 (rows are placed by fix site) the `app_shell/` half belongs in
0.8.0 with the shell work. Filed as its own row; the migration itself is mechanical.

**A private cross-module reach.** `oracle_app/form.py:709` calls `fr._locate(paths[0])` —
the only access to a `sloads` private from either shell package (checked by scan). It wants
"the dataclass this path lives on"; that is a public question and the registry should
answer it publicly. Band D, when the module is next touched.

## 4. Cut readiness

**Not ready.** In order:

1. Close **#124** (tier S) — band B empties.
2. Fix **§3.2** (smoke both entry points; §3.5's checklist line names both) — tier S.
3. Fix **§3.3** (notes 32 and 35 state what shipped) + the status guard — tier S ×2.
4. Fix **§3.4** (the Tools station input through the unit boundary + an SI guard) — tier S.
5. Decide **§3.5** (the `Development Status` classifier) at the version bump.

Then `RELEASE_PROCESS.md` §3 end to end. Two of its gates are outside this review's reach
and are the owner's to run at the cut:

- `scripts/backlog_issues.py check` — every priority-table row names an open issue and
  vice versa (MD-5). This review read the table, not GitHub; an open issue that is *not*
  in the table would not have been visible here.
- `scripts/branch_protection_snapshot.py --check` — the one comparison CI cannot make.

**A map drift found and closed while filing this review's rows.**
`.github/backlog_issue_map.json` had fallen behind the table: `backlog_issues.py plan`
reported rows **#121, #122 and #124** as `NEW`, because `create` skips only titles it finds
in the map and those three were opened outside it — so a `create` run would have posted
**three duplicate issues** for work that already had one. The five rows below were
therefore opened by hand and their `(#N)` written into the table directly; the map was then
reconciled from the table (40 → 48 entries, every row's owning `(#N)` read from its row
line rather than from the truncated title `_plain` produces). `backlog_issues.py check`
now exits 0 — every row names an open issue, every `band:*` issue appears in the table, and
every row's issue sits on the milestone its band header names. §3.1's gate is green.

Two notes for whoever next runs the bridge. `_plain` truncates a title at 120 characters,
so a long row's trailing `(#N)` is **not** in the map key — a reconciliation must read the
ref from the row line, and the "first `(#N)` owns the row" rule applies there. And the
label heuristic keys on the words *defect* / *hygiene* appearing in a row title, so §3.4's
row parsed as `kind:step`; it was relabelled `kind:defect` at creation rather than
contorting the title to satisfy a regex.

**Rows filed (2026-08-27, this session):** #126 (§3.4, band B), #127 (§3.2, band B),
#128 (§3.3, band B), #129 (§3.7 `use_container_width`, band B), #130 (§3.7 private reach,
band D). The four band-B issues carry the 0.8.0 milestone.

## 5. Decisions requested of the owner

**All four answered 2026-08-28, the recommended way in each case.** The rulings are
recorded inline below; §5.3's answer went further than the question asked and is
written out in full.

1. **RULED BLOCKS-CUT (owner, 2026-08-28).** §3.4 — is the Tools unit defect BLOCKS-CUT or KNOWN-ISSUE? Ranked BLOCKS-CUT here
   on the ground that it is a wrong number on screen, in this band's own new feature, with
   a tier-S fix. The counter-argument is real: it is display-only, stores nothing, moves no
   load, and the 0.7.2 ruling admitted only defects with a first-order effect on *shipped
   output*. Either ranking is defensible; the recommendation is to fix it, because the fix
   is smaller than the argument about it.
2. **RULED one row (owner, 2026-08-28)** — as filed, #128. §3.3 — one row or three? The two note edits are trivial; the structural guard
   (practice 3) is the substance. Recommended as one row: "a design note's status cannot
   claim unbuilt work", with the two corrections as its first sweep.
3. **RULED (owner, 2026-08-28) — see the note below.** §3.5 — what does the `Development Status` classifier say at the 0.8.0 tag?
4. **RULED split out into band B (owner, 2026-08-28)** — #129, and it carries the `app/views/` half too, since an upstream removal breaks both front-ends at once. §3.7 — does the `app_shell/` half of the `use_container_width` migration split out of
   the parked `L-8e` into 0.8.0 (rule 2, fix site), or ride to 0.9.0 with the rest?**
   Recommended: split it out and take it in this band, because the unbounded dependency
   floor makes it a time bomb rather than a nit.

### 5.3 in full — the release-state statement and the classifier

The owner's answer was a *sentence*, not a trove value: *"Core analysis developed per
FAR 23 loads and Oracle GUI production ready; additional features and full sloads GUI in
beta."* `Development Status` cannot carry that — it takes one value from a fixed PyPI
vocabulary — so the ruling was split, and both halves shipped in-session:

- **The classifier is `4 - Beta`.** Not `5 - Production/Stable`: the classifier describes
  the whole distribution, a fresh installer gets both front-ends, and the owner's own
  sentence puts one of them in beta. It understates the oracle GUI, which is what a
  single-valued vocabulary does to a mixed state.
- **The sentence gets one owner**, `app_shell.components.RELEASE_STATE`, consumed by both
  GUIs' About panel and carried verbatim by `README.md` and `CAPABILITIES.md`. Four
  hand-written copies is the documentation-currency failure mode this project has already
  paid for; markdown cannot import a symbol, so the guard
  (`tests/test_doc_currency.py`) pins the documents to the constant and fails on **any
  second spelling** anywhere in the tree. Both halves were verified to fail on a mutation
  rather than assumed to work.
- **It is in front of the user, not only in the metadata.** The About panel every page
  inherits now states it. `Development Status :: 4 - Beta` is read by `pip`; a person
  typing an airplane into the beta front-end had no other way to learn that is what it is.

Recorded as a *decision*, not a cut chore: the classifier was moved on `dev/v0.8.0` rather
than at the tag, so `RELEASE_PROCESS.md` §4 step 1 has only the version bump left to
remember.
