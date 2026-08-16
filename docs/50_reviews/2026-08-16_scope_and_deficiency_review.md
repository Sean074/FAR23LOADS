# Scope and deficiency review — the code base and the open backlog (2026-08-16)

**Charge (user, 2026-08-16):** a senior-developer review of the `sloads` code
base and the backlog work statement, sorting every open item (and the shipped
capability it builds on) into three buckets:

1. **Needed now** — deficiencies and code issues that must be addressed for the
   next release to be trustworthy;
2. **Future release** — real capability, but the current capability is
   sufficient or the limitation is stated in-band, so it can wait for a later
   release;
3. **Nice to have** — can wait indefinitely; recommend parking or dropping.

The review was asked for against a stated management concern: **the development
scope has grown too large, and features have been built that are not needed —
in that they add fidelity above the accuracy of the base analysis and are not
required now.** The review takes that concern as its lens.

**Yardsticks agreed before the review (user answers, 2026-08-16):**

- *Accuracy baseline* = the **McMaster FAR 23 method** as ported: Schrenk
  strip span load, rigid airplane, lumped tail loads, scalar Munk body moment,
  zero-thrust wing, Pratt gust, TAU curve-fit, Appendix-A replication at
  ±0.1 %. Anything finer than what this method can resolve is over-fidelity.
- *Shipped code* is reviewed too, but the recommendation for shipped
  capability is **freeze** (no further investment, tests kept), never remove.
- *"Now"* = **0.6.0 = the sbeam `FORCE`/`MOMENT` wing/body/tail deliverable**
  plus real defects. Bucket 2 = 0.7+. Bucket 3 = unscheduled.

Sources: `docs/30_future/00_backlog.md` (priority table re-cut 2026-08-15, 27
rows + the unranked pinned defects), `02_parked.md`, plan/notes 09–25,
`CHANGELOG.md [Unreleased]`, `docs/20_theory/00_theory_sources.md`, the two
prior reviews (2026-08-10, 2026-08-15), and a code-health scan of `sloads/`,
`app/`, `tests/` (§5). No code was changed. Nothing here moves an oracle.

---

## 0. Verdict

**The concern is justified in direction, but the picture is more specific than
"too much was built."** Three findings frame everything below:

1. **What has shipped is not over-fidelity — it is the deliverable.** The
   mission (2026-08-05, extended 08-08, prioritized 08-09) is a full-span
   balanced free-free airplane model exported as sbeam cards. The balanced-case
   assembler, CONM2 mass export, handedness (left/right twins), the sbeam
   round-trip CI harness, the ground/landing families and the governing
   safety-factor table are the minimum machinery for *that* deliverable to be
   correct, not refinements of the FAR 23 method. They are consistent with the
   base method's accuracy because they add **no new aerodynamic fidelity** —
   they redistribute the method's own loads with inertia and prove global
   equilibrium. Nothing shipped since 0.5.0 should be undone. **But every one
   of them should now be frozen** (§3): the return on further investment in
   the export/report layer is low and each touch costs a "digest wave".

2. **The scope creep is real and it lives in three specific places, all still
   in front of us, not behind us:**
   - **Step 14 "real stiffness"** (backlog Pri 1, the top-ranked item). A loads
     tool that carries section properties to make an indeterminate stiffness
     model is duplicating sbeam's job — sizing is the *consumer's* half of the
     "concept-loads → sbeam sizing loop". With the LRA skeleton shipped, the
     determinate paths are already honest and the header says so. **Recommend
     descoping to a pass-through** (§2.3) — this is the single largest
     over-fidelity item and it sits at Pri 1.
   - **The physics band E** — power effects on the wing (7 steps, L/L),
     Multhopp distributed body `Cm`, lateral body aero via DATCOM, distributed
     aileron lift, per-CG inertia, pitching load factor. Each is defensible in
     isolation; together they are a **second aerodynamic method** growing
     beside the McMaster one, and most of their effects are below the base
     method's own uncertainty on the deliverable. One of them (L-7) is worth
     doing because the current lateral answer is wrong by a factor of 4, not
     4 %; the rest wait or park (§2.2, §2.3).
   - **Band H — the Part 25 pack** (8 rows). Out of the FAR 23 mission entirely;
     park as a block (§2.3).

3. **The genuine bucket-1 work is small and mostly cheap** — one first-order
   defect in shipped lateral decks (the fin-root formula, a factor 2.6 on
   `cessna_210`'s roll acceleration), one mass double-count on three fixtures
   (up to 4,000 lb of fuel riding both beams), two fixtures modelled with the
   wrong tail layout, a units-labelling gap on the per-page CSVs, and a
   hygiene batch. **About 5–6 person-days** against a backlog whose top-ranked
   row alone is estimated M–L. Re-cutting the priority table on this basis is
   the recommendation of record (§4).

**Process finding (the root of the concern):** the priority table is ordered by
*mission trace* — anything with a line to "the sbeam deliverable" ranks in band
B — and not by **effect on the number a consumer receives relative to the base
method's error bar**. That is why real stiffness sits at Pri 1 and the
fin-root defect at 3a. §4 proposes the missing test as a standing rule.

---

## 1. Bucket 1 — needed now (0.6.0)

Ordered by "wrong content in a file a consumer already receives" first, then
cost. Backlog Pri numbers refer to the 2026-08-15 table.

| # | Item (backlog ref) | Why bucket 1 | Effort | Notes |
|---|---|---|---|---|
| 1.1 | **Fin-root "fuselage-top" formula has no body-centreline datum** (Pri 3a, defect) | First-order wrong content in shipped output: three fin roots stack half a body height above the wing root; `cessna_210` lateral `p_dot` moved ×2.6; twelve lateral cases in the assembled deck carry it. `z_centre` shipped v52 so it is the formula change plus its pin wave. | S | Do first; it is the only open item that moves a shipped card by a first-order amount. |
| 1.2 | **`atr42_100`/`dhc8_dash8` are T-tails modelled as conventional** (Pri 4a, defect) | A missing load (no T7 fin-tip transfer) in two of five fin decks — the "wrong card outranks missing card" class. Depends on 1.1 (they need the fin root they actually have). Fixture data + digest wave. | S–M | Do with 1.1 in one digest wave. |
| 1.3 | **Wing-tank fuel separability** (Pri 2) | Same pounds on both beams: 3,800 / 4,000 / 1,200 lb on the three fuel-in-wing fixtures — ~10 % of the twins' gross weight carried as fuselage inertia *and* wing relief. That is above the base method's error bar for the fuselage beam. **Scope tightly:** a `wing_fraction` on `MassItem` (or a second row) and the tie validator — **not** plan 12 C1's per-case itemization, which is a mass-model rebuild. | M (schema, one hop) | The backlog pairs it with plan 12 C1; decouple. |
| 1.4 | **Fixture aero data — `NMAA` `dCD` sign** (Pri 3, defect) | A positive `dCD` at α ≈ −13° on three fixtures is unphysical and it is in a shipped balanced deck. Scope: decide the trusted-α window is one-sided and clamp/flag; do **not** re-derive the polars from a new source (that is over-fidelity — the fixtures are illustrations). | S–M | Ratchet pins already exist; make them the acceptance. |
| 1.5 | **L-8i — per-page LIMIT CSVs ignore the SI toggle and state no units** (Pri 14) | Imperial numbers in an SI session leave the tool unlabelled — a units defect, the class the project has already paid for three times. Four pages, mechanical. | S | |
| 1.6 | **M4-3(b) — turboprop gate as enforcement** (Pri 11 part) | The limitation is a *sentence* (`PROPELLER_ONLY_NOTE`); make it a gate so a turbofan project cannot produce the 41–52 klb fin loads the fixture step found. (a) and (c) of M4-3 are bucket 3. | S | |
| 1.7 | **Hygiene batch:** conventions findings (a)–(d) (Pri 16 — the cited-but-missing `test_load_keys.py` guard, 23.303/25.303 citation split, `coordinates.py` default comment, three `units.py` factor maps); M4-23 duplicate sigma (Pri 17); "verify and retire" the 427 lb fuselage-mass pin (unranked); the R6-D-style currency check on `[Unreleased]`. | Cheap, and two of them are guards that are claimed to exist. | S | One session. |
| 1.8 | **Cut 0.6.0.** `[Unreleased]` is ~940 lines / 3 days of work with no regression baseline, against the cadence rule (RELEASE_PROCESS §2). Two schema hops (v50→v52) are unreleased. | Process, not code. | — | After 1.1–1.2's digest wave; do not hold for anything in §2. |

**Explicitly *not* bucket 1 although the backlog ranks it there:** Step 14 real
stiffness (Pri 1) — see §2.3.

**Bucket-1 code-health items** (§5.1): CH-1 test-suite runtime (coverage
opt-in + xdist), CH-2 the three export-path silent defaults, CH-3 the untested
axis transforms — all S, all in the same hygiene session as 1.7.

---

## 2. Buckets 2 and 3 — the open backlog, row by row

### 2.1 Bucket 2 — future release (0.7+); current capability sufficient or limitation stated in-band

| Backlog | Item | Assessment against the base method | Verdict |
|---|---|---|---|
| Pri 6 | **L-7 lateral body aero `Cy_β`/`Cn_β`** (design note 19, DATCOM, oracle step) | The lateral balanced cases react the fin load with inertia alone: `ψ̈` over-stated 73–84 %, `n_y` under-stated 4–12 % on the RJ. That is not fidelity above the base method — it is a **missing term of the same order as the one kept**, and it is what makes the fuselage lateral bending in the assembled deck honest. In-band caveat exists on every lateral case, so it can wait a release; but it is the one band-E item that should be done, and it is an oracle step (DATCOM printed cases). | **2 — first of the physics items.** |
| Pri 4 | Empennage planform polylines (fixture data) | Rectangle-vs-taper moves the tail load centroid from b/2 toward b/3 — conservative in root bending, wrong in station distribution. Fixture data, S per fixture, marked `assumed` in every artifact. | **2** — do when a fixture is next touched. |
| Pri 12 | Combined flight + ground station envelope | Report polish a consumer wants; no physics; the two families exist. | **2** |
| Pri 7 | Aileron's own lift increment distributed on `ACRL` | The base method (WINGINER) omits it too — so this is *above* the base method — but on a wing-sizing deliverable a ~70 %-span differential lift is not below the error bar. Needs new schema data on six fixtures with no oracle. | **2, late** — only if a consumer sizes to `ACRL`. |
| Pri 15 | Gust spanwise-distribution decision | A one-page decision that the Schrenk shape is reused; record it. | **2** (S; effectively a doc note) |
| Pri 13 | Structural negative zeros in deliverables | Cosmetic; costs a full digest wave. | **2** — ride along with the next unavoidable digest wave (1.1/1.2), never alone. |
| Unranked | Derived-`ACRL` air-load divergence (19 %) — decision | Only the derived route (no shipped fixture uses it). Decide-and-record. | **2** (decision only) |
| Unranked | ATR-42 Mach-capped stall exceedance | Fixture property; the honest fix is `_balance` reporting an infeasible corner rather than an unconverged point. | **2** (S when touched) |
| Unranked | WTENV envelope entered independently of the item database (4 fixtures) | Warned in CI; fixture hygiene. | **2** — with Pri 4 as one fixture pass. |
| Pri 19 | Split the 9,121-line history file | Process cost, not user value; the file is the third-most-churned in the repo. | **2** — do it once the tree is committed; see §5. |
| Pri 18 | Review 2026-08-10 minor sweep m3–m18 | Opportunistic by design (practice 4). | **2/3** as encountered |

### 2.2 Bucket 3 — nice to have; recommend **park** (move to `02_parked.md`)

| Backlog | Item | Why it is above the base method's accuracy / off-mission | Verdict |
|---|---|---|---|
| Pri 11a | **Power effects on the wing** (note 21, P-0…P-12, 7 steps, L/L) | The base method is zero-thrust on the wing by construction, and every FAR 23 wing oracle is. DATCOM §4.6 wake modelling plus a `power_policy` table minting `-P` variants of every wing family is a second aerodynamic method. The **thrust point** is a different matter: the LRA skeleton already has the engine hub node and the design note says "the thrust `FORCE` waits" — a single card per engine at the hub is S, and it is what a consumer sizing a wing with a wing-mounted engine needs. | **Park the 7-step plan; carve out "thrust `FORCE` at the hub, user-entered thrust" as a bucket-2 S item.** |
| Pri 8 | M4-19 Multhopp distributed fuselage `Cm` | Munk scalar is the method; the distributed body aero moment is second-order against the body's inertia and tail loads in the body beam, and it needs new inputs (`i_f`, upwash curve). | **Park.** |
| Pri 9 | M4-21 fuselage pitching load factor | Zero on every balanced trim point (`θ̈ = 0`); the envelope emits no unbalanced-pitch case, so it has no consumer until 23.423 abrupt-pitch cases exist. | **Park** (with M4-4). |
| Pri 10 | M4-4 per-CG precise inertia in SELECT | The Ch 9 approximation matches the oracle. | **Park.** |
| Pri 11 (a),(c) | ONENGOUT geometry provenance, VSF alternative | Documentation-level. | **Park.** |
| Pri 5 | `concept_heavy` gear geometry | Buys a sixth fixture for an artifact that has five, and a warn-only floor check that has never fired. | **Park.** |
| Pri 20–27 | **Band H — Part 25 / F25 pack:** F25-0 verify, Mach-margin route for FAR 23 categories, flutter Mach basis, upset criterion, F25-1 "T" envelope, F25-4 ground variant, M4-8 Layer 2 named failure factors, CG-dependent MTOW | Every one is outside the FAR 23 mission and none is needed for the sbeam deliverable. F25-2 (shipped) already gives the concept fixtures a dive speed. | **Park the block.** Re-open only on a stated Part 25 concept requirement. |

### 2.3 The one item that is ranked first and should not be built as written

**Step 14 — real stiffness / assembled airframe properties (Pri 1, L-1).**
What it promises: real section properties replacing the `MAT1 E=1e7`
placeholder, unlocking indeterminate load paths (continuous fuselage on two
posts, wing carry-through, redundant hinges).

Why it is over-fidelity for a *loads* tool:

- The mission is a **loads → sbeam sizing loop**. Section properties are the
  *output* of the sizing half. Carrying them in `sloads` means the loads tool
  owns a stiffness model of the airplane it has no method to size, and every
  redundant-path internal load it then reports depends on properties the tool
  invented or was handed.
- The shipped LRA model already states (header, note 24 R-12) that only the
  **determinate** paths — SOB, fin root, post sums, gear and engine links —
  give honest internal loads with placeholder properties. Those are exactly
  the loads a concept designer needs from a loads tool: interface loads at
  the cuts. The indeterminate distributions are the sizing tool's job, run
  with *its* properties.
- It is the largest-effort row (L/M) and it drives further schema (per
  element family), further digest waves and further gates.

**Recommend:** descope to a **pass-through** — if a consumer supplies `PBAR`/
`MAT1` per LRA element family, the exporter writes them instead of the
placeholder (S, additive, no physics, no gate beyond "the deck still solves").
Retire "unlock the indeterminate paths" from the mission text. Park the rest.

---

## 3. Shipped capability — what to freeze

"Freeze" = no further investment; tests and CI gates kept; touched only for
defects. Recommended freeze set, with the reason each is *complete enough*:

| Shipped capability | Status against the deliverable | Freeze note |
|---|---|---|
| FAR 23 core (22 programs, Appendix A oracle-locked) | Done since 0.2/0.3. | Frozen by charter already. |
| Balanced free-free assembler + handedness (plan 11, plan 13) | Six-DOF closure on 6/6 fixtures flight, 5/5 ground. | Freeze; L-7 (§2.1) is the one planned physics touch. |
| CONM2 / MASSSET mass export | Round-trips in CI, both unit systems. | Freeze. |
| sbeam round-trip CI harness | Real-solver leg ~16 s. | Freeze; add legs only for defects. |
| Ground/landing families + gear report (step 10) | LANDLOAD reproduced 1e-9 on both halves of the gate. | Freeze. |
| Governing safety-factor table (M4-8 Layer 1) | One owner, drift-guarded. | Freeze; **Layer 2 parked**. |
| Distributed empennage loads, control surfaces, hinge moment, T-tail transfer (plan 09) | Complete to T8. | Freeze. Note: the T-tail transfer is exactly what 1.2 needs on two fixtures — a data fix, not a code one. |
| **LRA beam model export/import (step 12/13)** | Skeleton complete; determinate paths gated. | **Freeze at determinate paths** (§2.3). |
| Summary report, PDF, workbook, manifest, methods stamp (G8, F-R\*) | Contract-complete after two review cycles. | Freeze; report additions only for new *cases*, never new sections. |
| Streamlit UI (8,063 lines in `app/views`; six view functions at CC 33–72, parked M4-11b) | Functional; all deliverables also headless via CLI. | **Freeze the GUI outright.** Do not work M4-11b or the L-8 UX items unless a UI defect blocks a deliverable — the CLI is the delivery path. |
| Part 25 F25-2 dive speeds | Shipped for the concept fixtures. | Freeze; rest of Part 25 parked (§2.2). |

---

## 4. The missing ordering rule (process)

The 2026-08-09 rules — *wrong cards outrank missing cards; [V] items ranked,
not opportunistic* — are sound but incomplete: they say nothing about the
**magnitude** of a change against the method's own error bar, so a fidelity
item with a mission trace outranks a defect with a first-order effect. Proposed
addition to the backlog's ordering rules (one line, no new ID series):

> **Effect-vs-error-bar rule.** A [V] physics or fidelity item is ranked only
> if its stated effect on a delivered load exceeds the base method's own
> uncertainty for that quantity (order 5–10 % on distributed loads, per the
> Schrenk / rigid-airplane / lumped-tail basis in `theory_sources.md`). Below
> that it is parked with the number that justifies parking it. Defects with a
> first-order effect on shipped content rank above every [V] item regardless of
> mission trace.

Applied to today's table, it produces exactly the buckets above, and it would
have caught step 14 at design-note time.

Two supporting process observations:

- **Schema velocity.** v47 → v52 in nine days (five hops, four of them
  unreleased). Each hop is a migration + fixture wave + docs. Recommend a
  **schema freeze through 0.6.0** apart from 1.3's one additive field.
- **Digest waves as friction.** Byte-level digests on every deck family are
  the right drift guard for physics, but they make cosmetic fixes (Pri 13)
  and formula fixes (1.1) equally expensive. Consider one *tolerance* gate on
  resultants beside the byte digest so cosmetic changes re-pin without a
  wave; not urgent, note only.

---

## 5. Code health (scan of 2026-08-16)

**Headline:** the code base is unusually disciplined for its size — `ruff`
clean; **zero** `TODO`/`FIXME`/`HACK` markers; **zero** bare or `Exception`
handlers in `sloads/`; single-owner registries with drift guards for GID/EID/SID
bands (`export/bands.py` + `tests/test_bands.py`), case IDs (`case_ids.py`),
tail geometry (`tail_geometry.resolve_tail_planform`) and units
(`units._KIND_FACTORS`); the external solver pinned by SHA and gated so that a
broken CI install fails rather than skips (`tests/conftest.py:45-48`). The
problems are **scale and cost of change**, not correctness. Numbers: 71,454
lines across `sloads/`+`app/`+`tests/` (26,988 of them tests, 8,063 UI);
89 test files, 1,952 tests; `SCHEMA_VERSION = 52` with 11 shape-changing
migration hops from floor v18; `docs/` standard set 13.8k lines, history file
9.1k, `CHANGELOG.md` 5.1k. Findings, tiered:

### 5.1 Bucket 1 (fix for 0.6.0 — cheap, and each is a wrong-content risk or a daily tax)

- **CH-1 Test suite runtime 18 min 37 s single-threaded** (1,930 passed / 21 skipped / 1 xfailed, exit 0, with the sbeam round-trip leg running; a solver-free install is shorter but still an order of ten minutes). `pyproject.toml:85`
  `addopts = "--cov=sloads --cov-report=term-missing"` puts coverage
  instrumentation on *every* invocation, including `--collect-only`. Make
  coverage opt-in (CI flag) and add `pytest-xdist -n auto`. This is the single
  biggest drag on the "closure in the same session" rule and on the digest
  waves. S.
- **CH-2 Silent defaults in the export path.** Three `getattr(..., default)`
  sites can produce a smaller-or-mislabelled deck that still parses — the
  D-19 failure class the band registry was built to stop:
  `sbeam_bridge.py:2103` (`hand` defaults to unhanded → a handed case's
  left/right sets could share a `LOAD` id), `sbeam_bridge.py:1783`
  (`tip_transfer` missing → the T-tail transfer is silently omitted),
  `sbeam_bridge.py:489` (a missing `case_ref` degrades to an empty condition
  string). Make each raise or assert the attribute exists. S. *(Two further
  candidates the scan raised were checked and rejected: `:1625` raises
  `ValueError` on a missing slice, and `migrations.migrate` treats a
  version-less file as the floor before `io.py:1175` sees it.)*
- **CH-3 Untested axis transforms.** `export/coordinates.py`'s
  `tail_axial_to_airplane`, `ttail_transfer_to_airplane`,
  `tail_torsion_to_airplane` have no direct unit test — sign/axis
  conventions with only round-trip coverage. Add three closure tests. S.
  (Belongs with 1.7's hygiene batch.)

### 5.2 Bucket 2 (maintainability; do when the module is next touched)

- **CH-4 Private cross-module imports.** `lra_model.py:98`, `roundtrip.py:75`,
  `mass_cards.py:73`, `balanced_deck.py:91` import `_fmt`, `_sf_str`,
  `_stamped`, `_MAT1_*`, `_PBAR_*` from the 2,375-line `sbeam_bridge.py`;
  `lra_import.py:47`, `body_loads.py:74`, `flap.py:57` do the same to other
  modules. Extract the deck-writing primitives into a small shared module.
- **CH-5 Dead code.** Never called anywhere (definition + `__all__` only):
  `balanced_deck.write_balanced_deck:528`, `mass_cards.write_conm2_fragment:661`,
  `mass_cards.write_mass_check_deck:669`, `mass_distribution.all_checks:899`.
  Delete. About twelve more public names have no consumer outside their own
  module (`sbeam_bridge.subcase_map`, `gear_loads.contact_patch`, …) — demote
  to private.
- **CH-6 Sea-level density open-coded at 7 sites** (`0.002378` in
  `constants.py:221`, `vn_diagram.py:37`, `flap.py:62`, `one_engine_out.py:90`,
  `select.py:500/536/684`, `flight_envelope.py:93/224`) under three private
  names. One `RHO_SL` in `constants.py`. Sits naturally with M4-23 (1.7).
- **CH-7 One stray unit factor** — `report/content.py:248` re-declares the
  lb→kg mass factor beside `units.py:299`.
- **CH-8 Function size.** Ten functions ≥150 lines; the calc side has two
  worth splitting when touched — `lra_model.build_lra_model` (336) and
  `landing.landing_reactions` (200). The rest are Streamlit views
  (`_tab_design_speeds` 384, `_tab_cg_inertia` 201, …) and fall under the GUI
  freeze (§3): **do not** work M4-11b.

### 5.3 Bucket 3 (note only)

- Coverage of `sloads/` is **93 %** with branch coverage (nothing below 88 %;
  lowest `weight_estimate.py`, `weight_onecg.py`, `wing_geometry.py`), which
  makes the specific holes sharper: the export writers `write_lra_model_bdf`,
  `write_lra_loads_on_imported_model`, the body/tail card writers and
  `write_gear_report_csv` are exercised only through the round-trip harness,
  never directly, and `coordinates.py`'s three tail transforms not at all
  (CH-3). `app/` is **not measured at all** (`--cov=sloads`), so the code with
  the worst complexity has no coverage visibility; view smoke tests exist, so
  this is a reporting gap — acceptable under the GUI freeze.
- Documentation mass (see numbers above) is the process cost that most
  visibly tracks the scope concern: 25 plan/notes under `30_future/`, a
  9.1k-line history file, an 824-line backlog. Pri 19's split is the
  mechanical relief; the real relief is fewer L-tier steps (§2.2, §2.3).

---

## 6. Recommended order of work

1. CH-1 first (it makes every later session cheaper), then bucket 1 rows
   1.1 → 1.2 in one digest wave (carry Pri 13's negative-zero normalisation
   in the same wave), then 1.4, 1.5, 1.6, and the hygiene session
   1.7 + CH-2 + CH-3 — one session each at most.
2. Descope step 14 to the pass-through and rewrite the Pri 1 row (S).
3. Move the §2.2 rows to `02_parked.md` with their bodies and the number that
   parks them; carve the thrust-`FORCE`-at-hub S item out of note 21.
4. Add the effect-vs-error-bar rule to the backlog's ordering rules; declare
   the schema freeze.
5. 1.3 (fuel separability, one additive field) — the last schema hop before
   the cut.
6. **Cut 0.6.0.**
7. 0.7 opens with L-7 (§2.1) and the fixture-data pass (Pri 4 + WTENV
   envelopes), then the combined station envelope.
