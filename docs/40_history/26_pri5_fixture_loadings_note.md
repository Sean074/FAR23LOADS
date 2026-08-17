# Pri 5 — payload loadings for the four silent fixtures (design note)

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: agreed and SHIPPED 2026-08-15.** Practice 1 (`CLAUDE.md`) — this note was
agreed in chat before code. Consumes the D-25 schema
([`22_d25_cgcase_loading_note.md`](25_d25_cgcase_loading_note.md), v50). Decisions of
record **D-26 / D-26a…c** in
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md);
closure trail in `CHANGELOG.md` and
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).

**What shipped is option A *and* option B** (§5), not A alone. The user chose A first;
re-measuring against the zoned question showed A alone cannot work, and §5's
recommendation was amended in the same session — see §7. Result: **6 of 6 fixtures
assemble, 34 of 34 cases carry an entered loading, and not one of them carries a pound
of ballast.**

## 1. What the row asked for, and what it runs into

Pri 5 reads as pure data entry: give `cessna_210`, `atr42_100`, `dhc8_dash8` and
`concept_heavy` a `CgCase.loading` per case, the way `concept_regional_jet`'s
`CG3 fwd light` got one, and four more fixtures start producing balanced cases.

Measured before entering anything: **that is not enterable on any of the four.** An
entered loading is not free — D-25a makes the case's `weight_lb`/`xcg`/`zcg` a *checked
echo* of the loading's own `Σw`, `Σwx/Σw`, `Σwz/Σw`, within `max(0.5 lb, 0.1 %)` and
0.5 in. So an entered loading must genuinely reproduce the case, and on these fixtures no
combination of the weight database can, by margins of 15–60 in in station and 4–31 in in
waterline. Closing the row as written would mean entering 10–44 % of each airplane as
nose or tail ballast, at stations pressed against the airframe's own extremes — i.e.
putting loadings no airplane could fly into decks CI publishes. That is the case the
2026-08-09 ordering rule calls out: **wrong cards outrank missing cards.**

This note states the measurement, names the root cause, and puts the choice to the user.

## 2. Method

For each fixture: `empty + minimum` rows are aboard by definition (D-25 §3.1), so they
are a fixed base; the case then demands a **payload** of
`P = W_case − W_base` whose CG is forced to

    x_P = (W·x_cg − W_base·x_base) / P        z_P = (W·z_cg − W_base·z_base) / P

Then an exhaustive search over discretionary subsets × a continuous fuel fraction (the
`fractions` lever D-25 §3.2 gives an entered loading, which the derived search does not
use on FLIGHT cases) for the **least ballast** that reproduces the case, with the ballast
row constrained to lie inside the airframe's own extent in both `x` and `z`. Script kept
in the session scratchpad; every number below is reproducible from the fixtures on HEAD.

## 3. The measurement

### 3.1 The signature: ga6 sits on its database, the others do not

`all-up` = every row of `weight.items` aboard, i.e. the heaviest loading the database can
produce.

| fixture | empty + minimum | all-up | heaviest case, entered | Δx | Δz |
|---|---|---|---|---|---|
| `ga6_normal` | 2,063 @ x 73.09 / z 90.72 | 3,400 @ x **85.00** / z **92.58** | CG1 3,400 @ x 85.10 / z 93.00 | **+0.10** | **+0.42** |
| `concept_regional_jet` | 21,200 @ x 636.29 / z 64.36 | 34,800 @ x **619.40** / z **62.66** | CG1 33,000 @ x 619.48 / z 70.00 | **+0.08** | **+7.34** |
| `cessna_210` | 2,474 @ x 71.06 / z 89.94 | 3,800 @ x **85.10** / z **92.20** | CG1 3,800 @ x 70.00 / z 96.00 | **−15.10** | **+3.80** |
| `atr42_100` | 19,247 @ x 400.32 / z 130.65 | 37,781 @ x **417.69** / z **135.74** | CGfwd 36,817 @ x 383.00 / z 145.00 | **−34.7** | **+9.3** |
| `dhc8_dash8` | 22,050 @ x 403.44 / z 137.35 | 34,500 @ x **420.40** / z **138.55** | CGfwd 34,500 @ x 378.00 / z 150.00 | **−42.40** | **+11.45** |
| `concept_heavy` | 9,700 @ x 258.04 / z 68.61 | 18,000 @ x **264.78** / z **69.06** | CGfwd 18,000 @ x 205.00 / z 100.00 | **−59.78** | **+30.94** |

Read the last three rows carefully: on `cessna_210`, `dhc8_dash8` and `concept_heavy` the
heaviest case weighs **exactly the all-up weight**, so there is precisely **one** loading
that produces it — everything aboard — and its CG is not a choice. That single loading
misses the entered station by 15 / 42 / 60 in. No schema, no ballast and no fraction can
change that; the case as entered is not a loading of this airplane.

`ga6_normal` — the Appendix A airplane, the one built from its own database — matches to
0.10 in and 0.42 in. `concept_regional_jet` matches in **station** (0.08 in) and misses in
**waterline** by 7.34 in. That split is the whole diagnosis.

### 3.2 Least entered ballast, honouring the entered `zcg`

Ballast constrained inside the airframe extent in both axes; fuel fraction free.

| fixture | case | least ballast | at | note |
|---|---|---|---|---|
| `cessna_210` | CG1 / CG2 / CG3 | 404 (11 %) / 570 (15 %) / 471 (16 %) | x −8 … −12, z 121–130 | x pinned at the **propeller spinner**; z at the fin |
| | CG4 | **impossible** | — | 2,300 lb case is **174 lb lighter than empty + pilot + reserve fuel** (2,474) |
| | 3 ground cases | 404–630 (11–17 %) | same corners | |
| `atr42_100` | CGfwd / CGmid | 4,273 (12 %) | x 163 / 309, z **229.8** | z pinned at the fin tip |
| | CGaft | 2,379 (7 %) | x 492, z 223.5 | the one case the search already calls derivable |
| | 3 ground cases | 6,283–7,425 (18–25 %) | z pinned at 55 (the gear) | |
| `dhc8_dash8` | CGfwd / CGmid / CGaft | 4,166 (12 %) / 4,166 (12 %) / 3,235 (11 %) | z pinned at **240** (fin tip) | |
| | aft/fwd max landing | 8,402 (26 %) | z pinned at 60 (the gear) | |
| | fwd light | **impossible** | — | |
| `concept_heavy` | CGfwd | **impossible** | — | only one loading exists (§3.1) |
| `concept_regional_jet` | fwd light (ground) | 1,690 (7 %) | x 91.8, z 186.7 | the RJ's one still-unassembled case |

Every surviving row is pressed against a bound — the ballast wants to go further forward
or higher than the airplane extends. These are not loadings; they are the optimizer
running out of airplane.

### 3.3 The same search with `zcg` freed

Identical search, `zcg` no longer a target (the loading's own waterline is reported
instead):

| fixture | case | ballast, `zcg` honoured | ballast, `zcg` freed | resulting `zcg` vs entered |
|---|---|---|---|---|
| `atr42_100` | CGfwd | 4,273 (12 %) | **3,759 (10 %)** | 134.3 vs 145 (−10.7) |
| | CGmid | 4,273 (12 %) | **1,392 (4 %)** | 136.0 vs 145 (−9.0) |
| | CGaft | 2,379 (7 %) | **208 (1 %)** | 133.3 vs 145 (−11.8) |
| | fwd light (ground) | 7,425 (25 %) | **1,579 (5 %)** | 140.1 vs 113 (**+27.1**) |
| `dhc8_dash8` | CGfwd | 4,166 (12 %) | **4,035 (12 %)** | 137.8 vs 150 (−12.2) |
| | CGmid | 4,166 (12 %) | **1,863 (5 %)** | 139.6 vs 150 (−10.4) |
| | CGaft | 3,235 (11 %) | **281 (1 %)** | 137.1 vs 150 (−12.9) |
| | aft max landing | 8,402 (26 %) | **1,403 (4 %)** | 138.6 vs 117 (**+21.6**) |
| `concept_regional_jet` | CG1 / CG2 | derived 1,640 (5 %) | **113 (0 %) / 523 (2 %)** | 63.7 / 63.9 vs 70 (−6.3) |
| | fwd light (ground) | 1,690 (7 %) | **1,690 (7 %)** | 61.9 vs 70 (−8.1) |
| `cessna_210` | CG1 / CG2 / CG3 | 404 / 570 / 471 (11–16 %) | 377 / 570 / 471 (10–16 %) | ~91 vs 96 (−4.5 … −5.1) |
| | CG4 | impossible | **impossible** | — |
| `concept_heavy` | CGfwd | impossible | 7,900 (**44 %**) | 68.7 vs 100 (−31.3) |

Freeing `zcg` alone takes `atr42_100` and `dhc8_dash8` from 11–26 % ballast down to
**1–12 %**, and the RJ to **0–7 %**. It does nothing for `cessna_210` or `concept_heavy`,
whose problems are in weight and station.

## 4. Diagnosis

Three distinct defects, not one:

**(a) `zcg` was never derived from anything.** The weight–CG envelope WTENV owns is 2-D —
weight against *station*. `CgCase.zcg` is a third number with no envelope behind it, and
on five of six fixtures it is a round figure (70 / 96 / 145 / 150 / 100) entered
independently of the item waterlines. It sits 6–31 in **above** the loading's real
waterline on the flight cases and 20–27 in **below** it on the `atr42`/`dhc8` ground
cases — inconsistent in sign, which is what an unsourced entry looks like. `ga6_normal`
is the exception (93.00 against 92.58) because it was built from its database.
**`zcg` is the dominant blocker and it is the cheapest to fix.**

**(b) Three fixtures' heaviest case is the all-up weight and states the wrong station.**
`cessna_210` CG1, `dhc8_dash8` CGfwd and `concept_heavy` CGfwd each weigh exactly what the
database weighs with everything aboard, so their CG is forced, and the entered station is
15 / 42 / 60 in away from it. This is unreachable by construction, not by search.

**(c) `cessna_210` CG4 is lighter than the airplane.** 2,300 lb against an
empty-plus-minimum weight of 2,474 lb — the case is 174 lb below empty + pilot + 30 min
fuel. It is not a loading under any schema. (Filed as a defect regardless of which option
below is taken.)

Underlying all three: on the five non-ga6 fixtures the CG cases were entered as
CG-envelope corner points read off a type's published envelope, while `weight.items` was
built independently as a plausible breakdown. That is the finding the backlog already
records — this note adds that the gap is **too wide for D-25's mechanism to bridge**,
which the D-25 note assumed it would not be.

## 5. Options

| | What it does | Result | Cost |
|---|---|---|---|
| **A** | **Make the case data consistent with the database.** Re-enter `zcg` per case from its loading (all fixtures except ga6, which already matches); correct `xcg`/`weight_lb` on the cases §4(b)/(c) shows are unreachable; then enter a `loading` per case. | 6 / 6 fixtures assemble; ballast 0–12 %, mostly ≤5 % | Amends D-25's *"the corner points stand"* → needs a **D-26**. Moves `atr42`/`dhc8`/`cessna`/`concept_heavy`/RJ baselines and digests (`zcg` feeds LANDLOAD, SELECT and FLTLOADS). **ga6 and every Appendix A oracle untouched.** |
| **B** | **Enrich the databases instead** — split `Passengers (n)` / `Baggage / cargo` into zoned rows (fwd/aft cabin, fwd/aft hold) at real stations and waterlines, preserving each row's `Σw`, `Σwx`, `Σwz` so no total moves. Keep every corner point. | Buys real CG travel at *intermediate* weights only; the all-up cases §4(b) stay unreachable | More work than A, and does not finish the job — A is still needed for the max-weight cases and for CG4 |
| **C** | **Enter the ballast and accept it** (D-25d lets an entered row export at any fraction). | Pri 5 closes numerically on 3 of 4 fixtures; 2 cases stay impossible | Ships 10–26 % nose/fin ballast as fixture truth. Against the wrong-cards rule |
| **D** | **Close only what is honest today.** | Essentially nothing without A | Row stays open, coverage stays 2 / 6 |

**Recommendation: A, optionally followed by B** as a separate later step for distribution
realism. A is the only option that ends with six fixtures carrying loadings a real
airplane could fly, and it isolates the fixture edits from the oracle-locked path
completely — `ga6_normal` is the one fixture that needs no change at all.

## 6. Shape of the work as agreed

1. **D-26 recorded** in [`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md):
   `zcg` is a derived echo of the loading, not an independent corner point; a case whose
   weight/station the database cannot produce is corrected to the database rather than
   ballasted to fit. Amends, and cites, D-25.
2. **Per fixture, per case:** choose the loading as an engineering statement (which zones
   and what fuel state), enter `aboard` / `fractions` / `ballast`, then set
   `weight_lb`/`xcg`/`zcg` to that loading's own properties, rounded to the echo
   tolerance. Entered ballast target ≤ 5 %, stated in the case note wherever it is used.
3. **`cessna_210` CG4** re-entered at or above minimum flight weight (2,474 lb), or
   removed with its reason recorded.
4. **Acceptance** (benchmark-first — no printed oracle exists for an entered loading):
   Appendix A oracles ±0.1 % unchanged (`ga6_normal` is not touched); every case on all
   six fixtures passes the D-25a echo check; `test_which_payload_cases_are_derivable_is_pinned`
   and `test_which_conditions_assemble_is_pinned` re-pinned to 6 / 6; plan 07's
   global-equilibrium invariant closes on every newly assembled deck; the sbeam round-trip
   CI leg stays green; both unit systems' digests re-baselined in the same change.
5. **Closure tier L** (contract amendment + fixture data across five projects): CHANGELOG,
   backlog removal, full step format in the history file, `PROGRAM_SPEC.md` and this note
   folded into the resolved-decision register.

## 7. What was actually done (2026-08-15)

**§5's recommendation was amended mid-step, and the reason is a measurement.** Option A
was chosen first. Re-running the enumeration with `zcg` corrected then showed that at
each fixture's gross weight the database admits **exactly one** loading — including
`ga6_normal`'s — because two or three lumped payload rows give almost no CG freedom. A
fwd and an aft corner case at the same weight therefore collapse onto the same loading,
and A alone would have produced fixtures whose "fwd" and "aft" cases were the same
airplane. Option **B** was folded in on that evidence (D-26b), which is what makes a
zero-ballast answer reachable at all.

What shipped, per D-26:

1. **Zoned payload rows** on `atr42_100`, `dhc8_dash8` and `concept_regional_jet` — fwd/aft
   cabin and fwd/aft hold — with each fixture's discretionary `Σw`, `Σwx`, `Σwz` preserved
   exactly, so no database total moves. `cessna_210` was already zoned by seat;
   `concept_heavy` gains nothing from zoning (one case, one loading) and was left alone.
2. **`cessna_210`'s fuel corrected** to 720 lb usable (120 US gal) and `CG4` re-entered at
   the minimum flight weight it had been entered 174 lb below (D-26c).
3. **Every case re-entered** as the fwd-most or aft-most loading of its own design weight,
   with `weight_lb`/`xcg`/`zcg` read off that loading. **No ballast row anywhere.**
4. `mass.cases` re-derived from the edited databases; the legacy `flight_loads.cg_cases`
   mirror kept in step for the G-3b migration guard.
5. Two cases renamed because the corner point they were named for is not one:
   `concept_heavy` `CGfwd` → `CGmax` (its only loading is the all-up one) and the RJ's
   `CG3 fwd light` → `CG3 light` (at 24,000 lb that airplane's CG goes *aft*, not forward).

**Coverage:** balanced flight cases 2 → **6** fixtures; the complete 27-case ground family
on all **5** fixtures with gear geometry (`concept_heavy` has none — Pri 8); every payload
case on every fixture derivable and entered.

### 7.1 Two defects this uncovered, fixed in the same change

* **A part-full consumable row left the exported `CONM2` set entirely.** Overlay cards are
  matched by object identity, and a fractional row is a scaled *copy*, so it matched no
  card: the exported mass model weighed less than the loading it declared — `dhc8_dash8`'s
  MLW case by 4,160 lb — in a deck that parsed and solved. Fixed with a per-(case, row)
  card band (`mass-part-full`, EID 9501+), since one card is one mass and the same tank at
  two fuel states is two masses.
* **An entered loading is weight-blind, so LANDLOAD's gross-weight-scaled ground
  conditions silently got the landing-weight inertia set.** 23.473(a) lets 23.485/23.493 be
  met at MTOW while 23.479/481/483 are met at MLW, and `_ground_target` re-weights the case
  for it — carrying the entered loading onto that target assembled 31,000 lb of mass under
  a case declaring 33,000. The re-weighted target now drops the loading and goes through
  the subset search, which is the one route that solves for weight as well as station.

### 7.2 One finding recorded, not fixed

The four fixtures D-26 brought into the assembly reach a **pre-closure force residual of
1.2–2.0 % of n·W**, against plan 11's 1 % acceptance, and three of them show a **positive
`dCD` on `NMAA`** (α ≈ −13°) — the wing strips carrying more axial force than the whole
airplane less tail, which cannot be true. Both are recorded per fixture in
`tests/test_balance.py` (`_FORCE_RESIDUAL_RATCHET`,
`_DELTA_CD_POSITIVE_AT_TRUSTED_ALPHA`) rather than absorbed by widening a gate.

The ordering is the diagnosis: `ga6_normal` — the one fixture whose aero comes from a
printed source — is best by 2×, and the concept configurations are worst. This reads as
**fixture aero-data quality** (an airplane-less-tail polar being evaluated far outside
where it was fitted), not an assembly defect: every case still closes exactly after
correction, and the pitch residual stays at 0.07–0.84 %. Filed as its own backlog row.

## 8. Units & conventions

Imperial-internal throughout; weights in lb, stations and waterlines in inches. Axis and
waterline sense per [`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md).
