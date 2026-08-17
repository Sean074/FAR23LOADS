# Wing-tank fuel separability — `MassItem.wing_fraction` (design note)

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: agreed 2026-08-17 (chat) and SHIPPED 2026-08-17** (schema **v53**) — kept
as the design record; what shipped matches §2–§5 with the two amendments in §8
(CONM2 cards stay per row; `Izz(closure)` moved more than predicted). Closure
trail in `changes/wing-tank-fuel-separability.{fixed,history}.md`. Backlog Pri 6
(GitHub #6), band A of 0.6.0; scope-review 2026-08-16 item **1.3**. **Tier L**
(one additive schema field — *the* schema hop the 0.6.0 freeze allows,
`00_backlog.md` "schema freeze through 0.6.0"), so this note comes first
(`CLAUDE.md` rule 1). Branch `feat/wing-tank-fuel-separability`.

**Conventions:** [`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md)
— mass is not a load quantity (no safety factor is involved; SF is applied once at
the render/export boundary, to loads only); the §7 SSOT table (the mass partition
has one code owner, `sloads/mass_distribution.py`, plan 11 B-2); the plan 11 §4
seam rule ("a load a free-body cut introduces is never applied in the assembled
model"). **Theory:** Ref 1 Ch 15 p103 (the body beam carries everything the wing
does not; the wing enters as the carry-through reaction — applying it as mass too
double-counts it) and WINGINER.BAS 1180–1270 / 1570–1610 (concentrated wing masses,
per side). **No printed oracle** covers a wing-tank fuel split — `ga6_normal`
(Appendix A) and `cessna_210` carry none — so this closes against **stated
invariants** (rule 2): the wing tie and the partition, both already in code.

Related and not duplicated here:
[`11_balanced_airframe_cases_plan.md`](../30_future/11_balanced_airframe_cases_plan.md) (B-2, the
mass SSOT; §4 the double-count authority table),
[`12_conm2_mass_export_plan.md`](../30_future/12_conm2_mass_export_plan.md) (C1 — the per-case
itemization this note explicitly does **not** rebuild),
[`22_d25_cgcase_loading_note.md`](25_d25_cgcase_loading_note.md) §6 (D-25's
`fractions` scale a row *in time*; this field splits it *in space* — complementary,
and orthogonal by construction, §3.2).

---

## 1. What is being fixed

`weight.items` is the mass single source of truth (plan 11 B-2, step B1). Every
row is reacted by exactly one beam, named by `MassItem.component`. Three shipped
fixtures carry their wing-tank fuel inside an **undivided** `"Fuel to gross"` row
tagged `fuselage`, while WINGINER's per-side `wing_mass.concentrated` hangs the
same fuel on the wing:

| fixture | `Fuel to gross` row (lb, `fuselage`) | WINGINER `concentrated` "wing fuel" | pounds on both beams | of the derived body beam | of gross |
|---|---|---|---|---|---|
| `atr42_100` | 9,174 | 1,900 /side | **3,800** | 11.6 % of 32,751 | 10.1 % |
| `dhc8_dash8` | 4,660 | 2,000 /side | **4,000** | 14.5 % of 27,500 | 11.6 % |
| `concept_heavy` | 5,500 | 600 /side | **1,200** | 7.4 % of 16,200 | 6.7 % |

(Measured 2026-08-17 with `mass_distribution.derived_fuselage_stations` /
`unmodelled_wing_mass`; the engine + nacelle (+ dhc8 main-gear) half of the
concentrated model reconciles **exactly** on both twins, so the gap is the fuel
alone — pinned to the pound today by
`tests/test_mass_distribution.py::test_the_unmodelled_wing_mass_is_pinned_per_fixture`,
whose own docstring says: *"When the item rows are eventually split into wing-tank
and body-tank fuel, this test goes red and is deleted."*)

Where it shows in shipped content:

1. **Per-component body deck** (`body_loads`, Ch 15 p103): the derived beam is
   heavier than the airplane's body by the wing fuel, so every body inertia load,
   the shear and bending distribution and the carry-through reaction
   `R_total = NZ·W_fus − tail` are over-stated by `n ×` those pounds — 7–15 % of the
   beam. Meanwhile the WINGINER wing deck relieves the wing with the same fuel. The
   same pounds ride both beams.
2. **Assembled balanced case / LRA deck** (`balance.py`, decision B-2): not
   double-counted — the assembly reads items only — but the fuel is carried as
   **body inertia at x ≈ 395** with **no wing relief**, and `place_wing_inertia`
   scales WINGINER's panel shape onto WING items that are short by the fuel
   (`atr42_100` scale 1.898 today). Wing bending in the primary deliverable is
   missing its fuel relief.
3. **CONM2 mass export** (`mass_cards.py`): the fuel CONM2 is a fuselage card.

**Effect vs error bar (`CLAUDE.md` rule 6):** the body-beam mass error is
7–15 %, above the 5–10 % base-method band for a distributed load
([`../20_theory/00_theory_sources.md` §Base-method uncertainty](../20_theory/00_theory_sources.md#base-method-uncertainty))
— and it is a defect in shipped content (the same pounds twice), which outranks
fidelity regardless. That is why it sits in band A.

## 2. Decisions proposed

| # | Decision | Why |
|---|---|---|
| **WF-1** | **Form: one additive field, `MassItem.wing_fraction: float = 0.0`** — *not* a second item row. | A row is the WTONECG/WTENV **loading-hierarchy** unit: `kind` says when it is aboard, `consumable` how it burns (G-5), D-25's `LoadingDefinition.fractions` how full it is, and `derive_case_loadings` searches **`2^n` discretionary subsets** to reconstruct a case. Splitting `"Fuel to gross"` into two discretionary rows doubles that search space and lets the search choose a loading no airplane can fly — wing tanks full, body tanks empty — to hit a CG; it also changes which subset the twins' `CGaft` cases resolve to. The **reaction partition** (which beam) is orthogonal to all of that and is the only thing that needs to split. It costs the one schema hop the freeze budgets for it; a second row would cost none but move the wrong thing. |
| **WF-2** | **Semantics.** `wing_fraction ∈ [0, 1]` is the fraction of the row's `weight_lb` — and of its own `ixx`/`iyy`/`izz` — reacted by the **wing (both sides together)**; the remainder is reacted by `component`. Position `x`/`y`/`z` is shared by both parts. `0.0` (the default) is today's behaviour bit-for-bit. A non-zero value on a row already tagged `WING` is rejected by validation (a wing row is wholly wing by definition; the field is for rows carried *elsewhere* that the wing also carries part of). Out of `[0, 1]` is rejected. | Both parts at one position means **WTONECG/WTENV weight, CG and inertia are unchanged to the last digit** — they read rows, not parts (§3.3). Under G-5 burn-down and D-25 `fractions` the *row* scales, so both parts scale together and the wing/body split is invariant in time — which is exactly why it is a fraction and not a pound figure (a `wing_weight_lb` would have to know about burn-down). Airplane-total rows (`"Engines (2)"`, every item at `y = 0`) are the fixture convention, so the fraction is airplane-total too. |
| **WF-3** | **One owner: `mass_distribution.reacted_parts(items, project) -> List[MassItem]`** turns rows into parts (each part carries an explicit `component` and `wing_fraction = 0.0`; a part is named `"<row> [wing]"` / `"<row> [<component>]"`; a zero-fraction row is returned as the same object); `distribution()` builds its partition from parts, and every consumer that sums by component — `balance.py` (`_wing_inertia_scale`, `place_wing_inertia`, `body_inertia`, `body_axial_set`'s fallback, `point_mass_self_inertia`), `mass_cards.py`'s header — consumes parts through it. `component_of()` stays valid **only for a part or a `wing_fraction == 0` row**, and a drift guard pins that the three consumers agree with `distribution()` on a project carrying a fractional row (rule 3: owner + guard, not a prose rule). | Today three modules call `component_of` on raw items independently; a fourth copy of the split would be the drift `CLAUDE.md` practice 3 forbids. |
| **WF-4** | **The tie becomes a validator.** `validation._check_wing_mass_tie` emits `ConsistencyWarning("wing_mass_tie_open", …, PAGE_WEIGHT_CG)` whenever `wing_mass_tie(project)` fails, stating the pounds (`unmodelled_wing_mass`, sign-aware) and the remedy (*set `wing_fraction` on the fuel row(s), or re-tag / correct `wing_mass.concentrated`*). The pinned test is deleted; `test_the_wing_tie_holds_where_the_item_model_is_complete` runs unskipped on all six fixtures. | Today the tie is a test plus one `st.info` on the fuselage page; a user's own file with this defect gets no signal in the CLI or the report. |
| **WF-5** | **Fixture data: the `"Fuel to gross"` row only, valued to close the tie exactly against WINGINER's *existing* `concentrated` "wing fuel"** — `atr42_100` 3800/9174 = 0.4142140833, `dhc8_dash8` 4000/4660 = 0.8583690987, `concept_heavy` 1200/5500 = 0.2181818182 (10 significant figures; the tie's `RECONCILE_REL_TOL = 1e-6` is ±0.009 lb). `Reserve fuel` / `Unusable fuel` rows are **not** touched. | No new number is invented: the per-side "wing fuel" entry is the fixture's own statement of how much fuel the wing carries, and the fraction is derived from it. (Physically an ATR 42 carries *all* its fuel in the wing; re-stating the fixture's fuel system is fixture-data work — band B Pri 10's class — not this defect.) The fraction is written in the JSON as the decimal; the note records the ratio. |
| **WF-6** | **The WINGINER per-component wing deck does not move.** `wing_inertia` reads `wing_mass` (panel + `concentrated`), not items; the fix is on the item side. Per-component wing bytes are an acceptance item (§5.4), and the *fixed* 1,900 lb/side against a *case-dependent* item fuel (`CGaft` burns `"Fuel to gross"` down to 5,623 lb on `atr42_100`) is a pre-existing property of the FAR23 wing deck, not a target here. | Additive step: if a wing deck digest moves, something leaked. |

## 3. Schema and behaviour

### 3.1 Schema

```python
@dataclass
class MassItem:
    ...
    consumable: bool = False
    #: Fraction of this row (weight and own inertias) reacted by the WING, both
    #: sides together; the remainder by ``component``. 0.0 = today's behaviour.
    wing_fraction: float = 0.0
```

`SCHEMA_VERSION` **52 → 53**, additive with a default: **no migration hop**
(`migrations.py` — "a version absent here changed only by adding optional fields,
which the tolerant readers already default"). `io._mass_item_to_dict` /
`_mass_item_from_dict` carry it (the ballast row shares the mapping — a ballast
row with a non-zero fraction is legal but pointless; validation is silent on it).
`tests/test_schema_guards.py`'s persisted-shape hash and
`docs/10_standard/DATA_DICTIONARY.md` (via `generate_data_dict.py`) are
regenerated on the branch **after** rebasing on `main` (MD-7).

### 3.2 Orthogonality — three concepts on one row, stated once

| field | axis | scales | owner |
|---|---|---|---|
| `kind` | **when** aboard (empty / minimum / discretionary) | the subset search | WTONECG/WTENV hierarchy |
| `consumable` + D-25 `fractions` | **how full** — in time | `weight_lb` of the row | G-5 burn-down / D-25 |
| `component` + `wing_fraction` | **which beam reacts it** — in space | the partition of the row into parts | `mass_distribution.reacted_parts` |

A row burnt to 40 % with `wing_fraction = 0.41` puts `0.4 × 0.41 × w` on the wing
and `0.4 × 0.59 × w` on the fuselage; nothing about `kind` or the search changes.

### 3.3 Who reads rows, who reads parts

| consumer | reads | this step |
|---|---|---|
| WTONECG / WTENV / `cg_cases` / `derive_case_loadings` (subset search, burn-down, D-25 echo checks, ballast) | **rows** | untouched — weight, CG, `Ixx/Iyy/Izz` and every derived `CaseLoading` bit-identical |
| `mass_distribution.distribution()`, `derived_fuselage_stations`, `partition_closes`, `wing_mass_tie`, `unmodelled_wing_mass`, `component_summary` | **parts** | the wing part joins `WING`; the body beam loses it |
| `balance.py` wing / body inertia and self-inertia; `mass_cards.py` header wing total | **parts** of the loading's rows (via `reacted_parts`) | fuel relief appears on the wing; CONM2 **cards stay one per row** (§8) |
| `body_loads` (via `fuselage_beam_stations`) | parts, indirectly | the beam lighter by the fuel |
| `wing_inertia` (WINGINER) | `wing_mass` | untouched (WF-6) |

### 3.4 What is predicted to move (the three fixtures only)

| quantity | `atr42_100` | `dhc8_dash8` | `concept_heavy` |
|---|---|---|---|
| derived body beam total | 32,751 → **28,951** lb | 27,500 → **23,500** lb | 16,200 → **15,000** lb |
| WING items (gross loading) | 5,030 → 8,830 lb | 7,000 → 11,000 lb | 1,800 → 3,000 lb |
| `place_wing_inertia` scale (`Σ WING items / 2·panel`) | 1.898 → 3.332 | 2.333 → 3.667 | 1.000 → 1.667 |
| body deck `R_total`, shear, bending | down by `n × 3,800 lb` and its moment | `n × 4,000` | `n × 1,200` |
| balanced-case pre-closure residual | expected to stay **< 1 %** — mass moves between beams at the same `x`/`z`; the wing centroid shifts from x ≈ 385 to ≈ 389 (`atr42`) | same | same |

Every other fixture — `ga6_normal` (Appendix A), `cessna_210`,
`concept_regional_jet` — carries no fractional row and must not move on any
channel.

## 4. Steps (one branch, one PR, one digest wave)

| # | Scope | Tier |
|---|---|---|
| F1 | Field + io mapping + `SCHEMA_VERSION` 53 + validation (`wing_fraction_out_of_range`, `wing_fraction_on_wing_row`) + `reacted_parts` + `distribution()` on parts + the consumer sweep in `balance.py` / `mass_cards.py` + the agreement drift guard (WF-3). | L |
| F2 | The tie validator (WF-4); pinned test deleted; tie test unskipped. | M |
| F3 | Fixture data (WF-5); digest regenerated after rebase (MD-7); `DATA_DICTIONARY.md` + schema-guard hash regenerated. | — |
| F4 | Closure trail (§6). | — |

## 5. Acceptance (benchmark-first; the invariants are the oracle substitute)

1. **Tie closes everywhere:** `wing_mass_tie(p).ok` and `unmodelled_wing_mass(p) == 0 ± 0.01 lb` on all six fixtures; the per-fixture pin is gone.
2. **Partition still closes:** `partition_closes` — `Σ(wing parts) + Σ(beam) == Σ(rows) == W` on all six, `rel 1e-6`.
3. **Rows unchanged for the mass-properties path:** WTONECG / WTENV / `cg_cases` outputs and every derived `CaseLoading` (item names, weights, ballast, `derivable`) **bit-identical** on all six fixtures; Appendix A ±0.1 % oracles unmoved.
4. **Additive where it must be:** Imperial digest unchanged on **every** channel of `ga6_normal`, `cessna_210`, `concept_regional_jet`; the WINGINER wing deck (`sbeam/wing*` channels) unchanged on **all six** (WF-6).
5. **Moves where it should:** the digest wave touches exactly `atr42_100`, `dhc8_dash8`, `concept_heavy` on the body / balance / mass channels; the body beam totals equal §3.4 to the pound; `body_loads` still satisfies its own `ΣFz = 0` and the plan 07 global-equilibrium invariant on every deck.
6. **Balanced cases:** the plan 11 §6 gates hold — pre-closure residual `< 1 %`, `|Δn|/n < 1 %` — on the three fixtures; the sbeam round-trip CI leg green; the `place_wing_inertia` scale note reports the new factor.
7. **CONM2:** cards and `MASSSET`s byte-unchanged (one card per row — §8); the header's wing total reads parts.
8. **The validator fires:** a test strips the fraction from `atr42_100` and asserts `wing_mass_tie_open` with `3800 lb` in its text; a fraction of `1.2`, and `0.3` on a `WING` row, are rejected by name.
9. **Round-trip:** v53 write→read→write identical; a v52 file (`wing_fraction` absent) reads as `0.0` and yields byte-identical decks; `test_migrations` contiguity holds with no new hop.
10. `ruff`, `mypy`, `pytest` green (3.12 fast gate on the PR; 3.9/3.11 on `main`).

## 6. Scope boundary

- **Not** plan 12 C1's per-case itemization (already shipped) and **not** a mass-model rebuild: no new row types, no tank objects, no per-tank burn schedule.
- **Not** where along the span the fuel sits in the assembled model: decision B-2's spread of WING items over WINGINER's panel shape is unchanged; a spanwise fuel distribution is fidelity work and is parked until an effect above the error bar is stated.
- **Not** the twins' fuel-system truth (all-wing fuel on the ATR); WF-5 closes the tie against the fixture's own `concentrated` statement.
- **Not** the WINGINER wing deck's fixed-vs-case-dependent fuel (WF-6).

## 7. Units & conventions

Imperial-internal (`units.py` converts at the boundary only): lb, in, lb·in².
`wing_fraction` is dimensionless and channel-independent. Mass is not a load: no
`-ULT` marker, no SF (`CONVENTIONS.md`). Axes and waterline sense per
`CONVENTIONS.md`.

**Closure tier: L** — `changes/wing-tank-fuel-separability.fixed.md` +
`changes/wing-tank-fuel-separability.history.md` (full step format);
`PROGRAM_SPEC.md` (mass model / body loads inputs), `PROJECT_GUIDE.md` (`Project`
schema), `CONVENTIONS.md` §7 (the partition owner row names `reacted_parts`),
`DATA_DICTIONARY.md` regenerated, `theory_sources.md` (the tie as the invariant
gate for this step); backlog Pri 6 removed and #6 closed by the PR; this note flips
to *shipped* and its decisions fold into
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md).

## 8. What shipped, and what measurement changed (2026-08-17)

- **CONM2 cards stay one per row.** A card is one mass at one position; every
  item — wing items included — hangs on the nearest fuselage beam node today
  (`mass_cards._attach_gid`, a documented limitation), so which beam *reacts* a
  row does not move its card, and splitting it would only have complicated the
  identity-keyed overlay matching. The header's "wing items" total reads parts.
  The `sbeam/mass*` channels did not move.
- **`Izz(closure)` moved more than predicted — +33 % / +31 % / +29 %** on
  `atr42_100` / `dhc8_dash8` / `concept_heavy` (157,652 → 209,595; 216,222 →
  283,943; 25,009 → 32,302 slug·ft² at the mid/max loading). §3.4 predicted the
  translational effects and said nothing about the tensor: the fuel left a
  centreline lump (`Σw·y² = 0`) for WINGINER's spanwise spread, and gained its
  `Σw·y²`. The twins' lateral `r_dot`/`p_dot` under the same fin load fell by a
  quarter to a third (`atr42` SIDE GUST `r_dot` +50.1 → +37.8 deg/s²); fin load
  and `Ny` are unchanged, which is the check that inertia moved and not aero.
  Re-pinned in `test_balance.py` with the reason.
- **Predictions that held to the pound:** body beams 28,951 / 23,500 / 15,000 lb;
  wing-inertia scales 3.332 / 3.667 / 1.667; residual gates unchanged; digest
  wave exactly the three fixtures on body / balance / LRA channels; wing decks,
  CONM2 cards, Appendix A and the other three fixtures byte-unchanged.
- **One pin flipped sign:** `dhc8_dash8`'s hand-entered `fuselage_mass.stations`
  (25,890 lb) was written with the wing fuel on the body and now exceeds the
  derived beam by 2,390 lb; pinned as such, not excused (it is an override
  table nothing reads by default).
