# D-25 — `CgCase` explicit loading definition (design note)

**Status: agreed and SHIPPED 2026-08-15** (schema **v50**). Practice 1 (`CLAUDE.md`) —
this note was agreed in chat before code on an L step, and is kept as the design record.
Decisions of record D-25 and **D-25a…d** in
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md);
closure trail in `CHANGELOG.md` and
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).
What shipped matches §3–§5 below; §5's acceptance item 5 was **stronger than
predicted** — `test_which_conditions_assemble_is_pinned` did move, because
`concept_regional_jet`'s `CG3 fwd light` gained a loading in this step and brought its
`NMAA` condition into the assembled deck. Remaining fixture work is backlog Pri 6.

## 1. What is being fixed

`flight_loads.cg_cases` (now the single case list, G-3) and the itemized
`weight.items` database are entered independently. `mass_distribution.derive_case_loadings`
searches `2^n` discretionary subsets plus a solved ballast row to reconstruct a loading
behind each case; it reaches **7 of 18** shipped cases within the 10 % credibility gate,
so **4 of 6 fixtures produce no balanced case at all**
(`test_balance.py::test_which_conditions_assemble_is_pinned`). D-25 answers the
outstanding decision: the CG corner points are the real engineering input and stay; the
**loading is the derived quantity and belongs in the schema**, entered rather than
searched for.

## 2. Decisions taken (user, 2026-08-15)

| # | Decision |
|---|---|
| **D-25a** | **The loading is authoritative.** `weight_lb`/`xcg`/`zcg` stay on `CgCase` as the engineering statement and become a **checked echo**: validated against the loading's own `Σw`, `Σwx/Σw`, `Σwz/Σw`; a mismatch beyond tolerance is loud. What is exported is the loading's real properties — never a set bent to hit the nominal number. |
| **D-25b** | **Form:** item references into `weight.items` + per-item fractions for `consumable` rows + an optional explicit ballast row. The weight database stays the mass SSOT (plan 11 B1); no weights are duplicated. |
| **D-25c** | **Optional, with the search as fallback.** `loading is None` → today's subset derivation, bit-for-bit. Older files load unchanged. |
| **D-25d** | **The 10 % ballast gate applies to solved ballast only.** An *entered* ballast row is an engineering statement (real stress/flight-test ballast) and always exports; its fraction is reported on the case and stamped in the deck `$` header. |

## 3. Schema

New input dataclass in `sloads/models/inputs.py`, and one field on `CgCase`:

```python
@dataclass
class LoadingDefinition:
    """Which discretionary useful load is aboard for one weight/CG case (D-25)."""
    aboard: List[str] = field(default_factory=list)        # weight.items names
    fractions: Dict[str, float] = field(default_factory=dict)  # consumable rows, (0, 1]
    ballast: Optional[MassItem] = None

@dataclass
class CgCase:
    ...
    loading: Optional[LoadingDefinition] = None
```

Semantics, and the validation that enforces each:

1. **`EMPTY` and `MINIMUM` rows are implicitly aboard.** A loading is a statement about
   the *useful load*; the empty weight and the minimum-flight-weight rows (pilot,
   reserve fuel) are not optional. `aboard` therefore names **`DISCRETIONARY` rows
   only** — naming an `EMPTY`/`MINIMUM` row is rejected as an entry error, on the same
   reasoning as G-3c's empty `analyses` set. This mirrors the WTONECG/WTENV database
   partition that `MassItemKind` already encodes.
2. **`fractions` applies to `consumable=True` rows only** (G-5), of any kind, whether
   named in `aboard` or implicitly aboard. The fraction scales `weight_lb`; `x`/`y`/`z`
   and the inertias are unchanged — proportional burn-down preserves the tank layout,
   which is the rule G-5 already states for the derived route. A fraction on a
   non-consumable row is rejected; so is a value outside `(0, 1]` — `0` means "not
   aboard", which is said by omitting the name, not by a zero.
3. **`ballast`** is a full `MassItem` carrying its own `x` **and** `z` (the waterline is
   required, not defaulted — `zcg` is checked against it under D-25a). Its `kind` must be
   `DISCRETIONARY`. Where the database already carries a ballast row — ga6 has
   `Ballast` 78 lb — the loading names it in `aboard` and needs no explicit row.
4. **Unknown name in `aboard`/`fractions`** → rejected, naming the case and the item.

`SCHEMA_VERSION` **49 → 50**. `io.py` gains the mapping in both directions; absent
`loading` reads as `None`. Per D-25c a v49 file loads and produces byte-identical
output.

## 4. Behaviour

`derive_case_loadings` gains one branch ahead of the search:

```
case.loading is None  ->  subset search + solved ballast   (today, unchanged)
case.loading set      ->  assemble the entered loading; no ballast is ever solved
```

For an entered loading the returned `CaseLoading` carries `weight_lb`, `cg_x`, `cg_z`
computed from its own items (D-25a), `ballast` = the entered row (or `None`),
`derivable = True` unconditionally (D-25d), and a `note` stating the ballast fraction
when one is present.

`case_loading_checks` gains the echo check: entered loading vs the case scalars, as a
`MassCheck` failure when outside tolerance — the existing loud mechanism, surfaced in
the report and red in CI.

**Tolerances** (§5 acceptance uses the same numbers):

| Quantity | Tolerance | Basis |
|---|---|---|
| `weight_lb` | `max(0.5 lb, 0.1 %)` | a rounded corner-point weight, not a computation |
| `xcg`, `zcg` | `0.5 in` = the existing `_CG_MATCH_TOL` | precedent: ga6 CG4 is the minimum-flight-weight loading at station 73.0924 against an entered 73.09 |

## 5. Acceptance (benchmark-first; there is no printed oracle for an entered loading)

1. **FAR23 path untouched** — Appendix A oracles ±0.1 %. No calc-math path reads
   `loading`; the mass model is not a load quantity, so no safety factor is involved
   (`CONVENTIONS.md` — SF applies once at the render/export boundary, to loads only).
2. **Reduction gate.** ga6's four cases are already derivable by search. Entering their
   loadings must reproduce the searched result: identical item set, `weight_lb` to
   `rel=1e-12`, `cg_x`/`cg_z` within `_CG_MATCH_TOL`. Entered == searched, or the entry
   is wrong. *As shipped this is a test
   (`test_an_entered_loading_reproduces_the_derived_one_on_ga6`, run on CG2 — the case
   needing the largest ballast) rather than a fixture edit, so ga6's own bytes do not
   move at all.*
3. **Echo check fires.** A test perturbs one entered `xcg` past 0.5 in and asserts the
   `MassCheck` fails — the loud path is exercised, not assumed.
4. **Round-trip.** v50 write→read→write is identical; a v49 fixture loads with
   `loading=None` and yields byte-identical `CaseLoading`s and decks.
5. **Pins re-pinned.** `test_mass_cards.py::test_which_payload_cases_are_derivable_is_pinned`
   moves by exactly the cases this step enters (ga6 4/4 unchanged; `concept_regional_jet`
   2/3 → 3/3). *`test_balance.py::test_which_conditions_assemble_is_pinned` was predicted
   unchanged and did move* — the RJ's `CG3 fwd light` carries its `NMAA` condition, so the
   fixture's flight family completed in this step rather than the next one; the Imperial
   baseline moved on four channels of that one fixture (`case_index`, `csv/balance`,
   `sbeam/balanced_deck`, `txt/balance`) and on nothing else.
6. **Equilibrium unchanged in form** — plan 07's global-equilibrium invariant still
   closes on every assembled deck, and the sbeam round-trip CI leg stays green.

## 6. Scope boundary

This step ships the **schema, the machinery, the validation and one demonstration
fixture** — `concept_regional_jet`'s `CG3 fwd light`, the first case only an entered
loading can produce. ga6 stays entirely on the derived route, so the Appendix A
airplane's bytes do not move and the reduction gate is asserted as a test instead.
Populating `cessna_210`, `atr42_100`, `dhc8_dash8` and `concept_heavy` — the rest of the
fixture CI multiplication — is **backlog Pri 6** (renumbered from Pri 7 when this row
closed), which consumes this schema. Wing-tank fuel separability (**Pri 7**) is a
separate `MassItem` change: `fractions` scales a consumable row *in time* (a part-full
tank), not *in space* (which tank), so the two are complementary.

## 7. Units & conventions

Imperial-internal throughout (`units.py` converts at the boundary only): weights in lb,
stations/butt lines/waterlines in inches, item inertias in lb·in². Axis and waterline
sense per [`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md).

**Closure tier: L** (schema + contract change) — CHANGELOG entry, backlog removal, full
step format in the history file, `PROGRAM_SPEC.md` + `DATA_DICTIONARY.md` (via its
generator) + this note's decisions folded into
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md).
