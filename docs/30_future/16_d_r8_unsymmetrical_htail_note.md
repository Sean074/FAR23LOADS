# Design note — the 23.427(a) handed balanced h-tail family (D-R8)

**Status: shipped 2026-08-10.** Agreed in chat before code, per `CLAUDE.md`
required practice 1. Decision of record: **D-R8**
([`03_resolved_decisions.md`](../40_history/03_resolved_decisions.md)), raised as
review finding **F-R5**
([`../50_reviews/2026-08-10_code_review_0_5_0.md`](../50_reviews/2026-08-10_code_review_0_5_0.md)
§2).

This note is the *decision* record. The method, the worked numbers and the
gate map live in [`../20_theory/balanced_cases.md`](../20_theory/balanced_cases.md)
§8, and the module spec in
[`../10_standard/PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md) — never
duplicated here.

## 1. What was missing

`build_balanced_cases` handled the wing and vertical-tail families. FAR
**23.427(a)** — the unsymmetrical horizontal-tail load — is the one h-tail
condition with a genuine left/right hand, and the full-span tail topology (plan
09 decision **T-8**) was built to carry it, yet it had no assembled
representation and the gap was filed nowhere. Every other h-tail condition is
symmetric and *is* in the deliverable already, as the trim tail load of every
wing case; that is a statement worth making rather than an absence to infer.

## 2. Decisions taken

| # | Decision | Alternative rejected |
|---|---|---|
| **D-R8.1** | The applied tail load is SELECT's **full** 23.427(a) `RH + LH`, distributed over the full-span `tail_span` table, **replacing** the lumped trim load `vn.lt` | Apply only the asymmetric increment `±(RH − LH)/2` on top of the trim load. Rejected (user, 2026-08-10): the case would stay inside the 1 % residual gate with no restatement, but the assembled h-tail would carry **one sixth** of its 23.427(a) design load on `ga6_normal` — unconservative for the tail and the fuselage, which is what this case is for |
| **D-R8.2** | The pre-closure `Fz`/`My` are **reported, not gated**: 23.427(a)'s load is a maneuver load on a V-n point at `n_z ≈ 1`, so the airplane is genuinely out of trim and the vertical/pitch closure is the maneuver. The gate is the case's **trim half**, at the same 1 % | Widen the residual gate for everyone. Rejected for the reason the lateral families were not merged into it either: a single widened number lets a real symmetric regression through |
| **D-R8.3** | The applied set is **air only** (`fz − f_inertia`), the surface's mass riding the closure field through its `htail`-tagged items | Read the strips' net load. Rejected: it applies the tail mass twice, once relieving the applied load and once in the relief field — the same seam the fin holds (decision L-8, `CONVENTIONS.md` §1) |
| **D-R8.4** | Handedness is decided by the **net applied rolling moment** against `HANDEDNESS_TOL · n·W · b/2` | Leave `is_handed` reading side force and free moments only. Not viable: this case has neither, so it would mint unhanded and emit one twin where 23.427(a) requires both sides |
| **D-R8.5** | The relief field is solved about the **mass set's own centroid**, not the entered CG | Keep the entered CG. Rejected on measurement: `ga6_normal`'s `CG4` centroid sits 0.0024 in forward / 0.0052 in below its entered CG, which at this case's 637 deg/s² leaves 0.31 lb of `Fx` unclosed — four orders above the closure gate. Found *because* this family accelerates hard enough to show it |

## 3. Gates (CI, `tests/test_balance.py`)

No printed oracle exists for an assembled airplane, so the gates are closed
forms and independent producers (`CLAUDE.md` practice 2):

| Gate | Test | Result |
|---|---|---|
| each applied half = SELECT's own `RH`/`LH`; the twins swap them | `test_the_unsymmetrical_case_carries_selects_own_split` | exact (6.7e-16) |
| applied roll = `(RH − LH)·ȳ`, `ȳ` from the planform | `test_the_unsymmetrical_roll_is_the_closed_form` | ratio 1.000000000 |
| the trim half still closes inside 1 % | `test_the_trim_half_of_an_unsymmetrical_case_still_closes` | 0.187 % / −0.246 % force |
| six-DOF closure, in memory and **from the deck's own card text** | `test_the_case_closes_in_all_six_dof`, `test_the_deck_balances_from_its_own_cards` | ~1e-16 / card-format floor |
| the deck solves free-free in sbeam, both unit systems | `test_assembled_deck_reacts_to_zero` | reactions ~ 0 |
| the roll of the case is the tail split's own moment and nothing else | `test_the_roll_moment_is_the_applied_couple` | exact |
| the closure's reference point is the mass centroid | `test_the_closure_is_solved_at_the_mass_centroid` | property + a loading where they differ |
| which conditions assemble, and their hands | `test_which_conditions_assemble_is_pinned` | `HT-09R`/`HT-09L` on both fixtures |

## 4. What moved, and what did not

**Moved:** four new subcases (`7209`/`8209` on `ga6_normal` and
`concept_regional_jet`), hence one regeneration of the Imperial digest set —
`csv/balance`, `txt/balance` and `sbeam/balanced_deck` on those two fixtures, and
nothing else. The relief field's new reference point (D-R8.5) is a no-op on every
other loading, by measurement, which is why no other deck byte moved.

**Did not move:** SELECT, `tail_span` and every per-component deck are *read*,
never recomputed — no Appendix A figure is at risk. The FAR 23 core never sees
handedness; the twin is a reflection (decisions B-6/B-7).

## 5. Known limitations carried forward

- The h-tail planform is the **assumed rectangle** on every shipped fixture
  (backlog: empennage planform polylines), so `ȳ` — and with it the applied
  rolling moment — is a first-order figure. Stated in-band on the case through
  the planform's own `assumed` marker.
- The wing loads of this case carry ~0.5 g of relief on `ga6_normal`: it is a
  **tail and fuselage** design case, not a wing one.
- 23.427(b) — the unsymmetrical load on a **vertical** tail with a horizontal
  surface attached to it — is not assembled; the T-tail transfer it would need is
  backlog step 9 (plan 09 T6–T7).
