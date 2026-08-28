# The landing load factor is entered as N, not NLG

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: SHIPPED 2026-08-27 (#123, schema v57;
`changes/landing-governing-n.*`). AGREED earlier the same day (owner, in
session — `CLAUDE.md` rule 1's working-alone path), milestone 0.8.0.** Owner rulings taken (in
session, 2026-08-27): **NLG shall never be entered directly**; `L` is a **free number**
with no enforced cap, default 0.667, the GUI naming the FAR defaults; the `N`
field **displays the computed drop-test value and the user may change it**; the
migration is **`N = NLG_old + L`**; the 23.473(g) floors **block in FAR 23 and
warn in concept**; **both** GUIs (`app/` and `oracle_app/`) carry the guidance;
the sweep for the same defect class is **in scope** and its one adjacent finding
is filed separately.

**Scope.** One defect with a first-order effect on shipped output, and the
re-parameterization that removes the class rather than patching the instance.
`LandingInput.gear_load_factor` is an NLG override that supersedes the LGFACTOR
energy result. Because `VMP = ½·NLG·W·AP/DP` reads NLG and nothing else, an
entered NLG makes the wing lift factor `L` **inert on the vertical gear
reaction** — the user changes the lift assumption and no wheel load moves — while
the page continues to display the *energy-derived* N that the reactions were
**not** computed from. `PROGRAM_SPEC.md` §LANDLOAD already records the split as
intended behaviour ("LANDLOAD takes the gear load factor as a rounded design
input (2.5 on p230), distinct from LGFACTOR's computed 2.428"); this note rules
that it is a defect, because the two numbers are two different airplanes.

The fix inverts the pair: **`N` and `L` are the inputs; `NLG = N − L` is
derived, reported, and never entered.** That is the only parameterization in
which `L` moves the gear reaction, which is the behaviour the change exists to
deliver. It also lets `L` reach 1.0 for the FAR 25 basis without a second
mechanism.

**Sources reviewed (verified 2026-08-27, by running the fleet):**
`sloads/modules/landing.py` (`landing_load_factor`, `_geometry`,
`landing_reactions`, `build_landing`, `run`), `sloads/models/inputs.py`
(`LandingInput`), `sloads/modules/balance.py` (`ground_lift_sets`,
`assemble_ground`, `GROUND_LIFT_CASES`), `sloads/export/balanced_deck.py`
(the GROUND residual narrative), `sloads/field_registry.py`,
`sloads/units.py`, `sloads/migrations.py`, `sloads/io.py`,
`app/views/landing_loads.py`, `oracle_app/form.py` (`_offer_clear`),
`tests/test_landing.py`, `examples/*.project.json` (six), plus the
override-pattern sweep in §4. Theory: FAR 23.473(d)–(g), FAR 23 Appendix C
23.1, FAR 25.473(a)(2) for the L = 1.0 basis; Ref 1 Ch 20 p126–130; oracles
Appendix A p236 and p230. Conventions: `CONVENTIONS.md` §load factors are
dimensionless and never scaled to ultimate — unchanged by this note.

---

## 1. What exists today (verified inventory, 2026-08-27)

### 1.1 The equations, as coded

```
V     = clamp(4.4·(W/S)^0.25, 7, 10)                          landing.py:97-98
N     = [W·V²/2g + W(1−L)(S_strut + d_tire)/12]
        / [W(η_tire·d_tire + η_strut·S_strut)/12]             landing.py:101-106
NLG   = N − L                                                 landing.py:108
NLG_used = inp.gear_load_factor or NLG                        landing.py:309   ← the defect
K     = (NLG_used + L)/NLG_used · K0                          landing.py:171-173
VMP   = ½·NLG_used·W·AP/DP  (cases 1-3) or ½·NLG_used·W       landing.py:330-334
NVP   = (2·VMP + VNP + L·W)/W   (cases 1-9)                   landing.py:386-390
```

Vertical equilibrium at peak load is `N·W = NLG·W + L·W`, i.e. `N = NLG + L`.
Three quantities, one equation, two degrees of freedom — and **which two are
inputs decides whether L moves the reaction.** Today NLG and L are the inputs,
so it cannot.

### 1.2 The three symptoms

| # | Symptom | Evidence |
|---|---|---|
| **S1** | `L` is inert on the vertical reaction whenever NLG is entered | `VMP` reads `NLG_used` only ([landing.py:330-334](../../sloads/modules/landing.py)). Owner-run ga6 cases confirm it. Second-order exception: cases 1–3 shift slightly through `β₀ = γ − GRA₁`, since `γ = atan(K)` and `K` carries `L` |
| **S2** | The page reports an N the reactions were not computed from | `m2.metric("Airplane load factor N", lf.airplane_load_factor)` ([landing_loads.py:198](../../app/views/landing_loads.py)) and the same value in `run()` ([landing.py:678](../../sloads/modules/landing.py)) are the **energy** N; ga6 prints 3.0972 while the deck runs at `2.5 + 0.667 = 3.1670` |
| **S3** | `0.0` encodes both "unset" and a legal value, so there is no way back to computed | The `or` at [landing.py:309](../../sloads/modules/landing.py); `oracle_app/form.py:542` had to build a "✕ clear" button naming this very field as the reason |

S2 reaches the assembled deck as well: `assemble_ground` applies wing lift
`L × W_case` on cases 1–12 ([balance.py:2367](../../sloads/modules/balance.py)),
so with an entered NLG the applied lift and the reactions come from unrelated
`(N, L)` pairs. The NVP/NDP gate at
[balanced_deck.py:326](../../sloads/export/balanced_deck.py) does not catch it,
because `NVP` is *defined* from the same NLG and L — an identity, not a check.

### 1.3 The fleet, measured (2026-08-27, `build_landing` on each example)

| example | cat | L | V | N (energy) | NLG (energy) | NLG used | **N after migration** | **NLG new** |
|---|---|---|---|---|---|---|---|---|
| `ga6_normal` | FAR 23 | 0.667 | 9.0049 | 3.0972 | 2.4302 | 2.5000 | **3.1670** | 2.5000 |
| `baron_58` | FAR 23 | 0.667 | 10.0000 | 3.3642 | 2.6972 | 2.6972 | *(unfilled → energy)* | 2.6972 |
| `cessna_210` | FAR 23 | 0.667 | 9.4987 | 3.3885 | 2.7215 | 2.5000 | **3.1670** | 2.5000 |
| `atr42_100` | concept | 0.667 | 10.0000 | 2.3755 | 1.7085 | 2.0000 | **2.6670** → 2.67 (LF-10) | 2.0000 → 2.0030 |
| `dhc8_dash8` | concept | 0.667 | 10.0000 | 2.3755 | 1.7085 | 2.0000 | **2.6670** → 2.67 (LF-10) | 2.0000 → 2.0030 |
| `concept_regional_jet` | concept | 0.667 | 10.0000 | 2.3755 | 1.7085 | 2.0000 | **2.6670** → 2.67 (LF-10) | 2.0000 → 2.0030 |

Two readings this table settles:

* **p230 is only reproducible at NLG = 2.5.** `K0 = 0.25 + (3230−3000)/3000·0.08
  = 0.256133`; `K = (3.167/2.5)·0.256133 = 0.3245` → oracle 0.324, `γ = 17.98°`
  → oracle 17.978. At the energy NLG of 2.4302 the same arithmetic gives
  `K = 0.3265`, `γ = 18.08°` — **+0.63 %** and **+0.58 %**, six times the ±0.1 %
  tolerance, and since `β₀ = γ − GRA₁` the whole AP/BP/DP table moves with it.
  So ga6 must carry `N = 3.167` (LF-9), not the energy value.
* **The three concept rows are nudged to N = 2.67, not the migration's 2.667**
  (LF-10). `2.0 + 0.667 = 2.6670` lands 0.0030 *below* the 23.473(g) floor and
  would start three shipped examples warning on a rounding artifact; 2.67 clears
  it and moves NLG by 0.1 %.

---

## 2. Decisions (LF-1 … LF-12)

| # | Decision | Rationale |
|---|---|---|
| **LF-1** | **`N` and `L` are the inputs; `NLG = N − L` is derived, reported and never enterable.** `LandingInput.gear_load_factor` is **deleted**, not deprecated. | The only parameterization in which `L` moves the gear reaction. A field whose meaning inverts from input to output is the second-opinion duplication note 33/DS-1 spent a step removing; keeping it writable re-creates it. |
| **LF-2** | **`airplane_load_factor: Optional[float] = None`** replaces it. `None` → the LGFACTOR energy value governs; a typed value overrides. **Not a `0.0` sentinel.** | Symptom S3. The sentinel is what made the old override a one-way door; `Optional` is the shape `36_derive_override_note.md` OV-1 leaves for fields that are genuinely `None`-able, and it is what `_offer_clear` already knows how to reverse. |
| **LF-3** | **`landing_load_factor()` is unchanged.** It keeps owning `V` and the energy `N`, and stays the p236 oracle's subject. What changes is only *who consumes it*: `landing_reactions` takes `N` from the input when filled, else from the energy result, and derives NLG once. | The oracle lock is on the function, not on the consumption path. Leaving it untouched is what makes this change oracle-neutral by construction. |
| **LF-4** | **The `L ≤ 0.667` refusal is removed** ([landing.py:95-96](../../sloads/modules/landing.py)) and the widget cap with it. `L` is a free number, default 0.667. Both GUIs caption the FAR defaults — 0.667 (FAR 23.473) and 1.0 (FAR 25.473(a)(2)) — as *guidance*, not enforcement. | Owner ruling. A hard cap cannot serve two certification bases, and the honest bound on the pair is LF-5's floors, which are regulation text rather than an input range. |
| **LF-5** | **`N ≤ L` is a hard refusal**, message naming both values and the resulting NLG. *(Corrected at implementation, #123: the row originally read "`N > L` is a hard refusal", inverted — G-LF-4 always stated the refusal as `N ≤ L`.)* | With LF-4 the cap no longer keeps `NLG = N − L` positive. `k = nap/nlg` ([landing.py:173](../../sloads/modules/landing.py)) is then one keystroke from a `ZeroDivisionError` or a sign flip that would ship as a quietly negative reaction. This guard is the *only* remaining protection. |
| **LF-6** | **The 23.473(g) floors bind by category:** `N ≥ 2.67` and `NLG ≥ 2.0` **block** in FAR 23 (N/U/A) and **warn** in concept (C). One owner for the policy plus a drift-guard test (practice 3) — not a second `if` beside the existing concept-only note at [landing.py:664](../../sloads/modules/landing.py). | Owner ruling. The floors were warn-only *and* concept-only because `N` was derived and could not be wrong; a user-supplied `N` in a certificated category can be. §1.3 confirms all three FAR 23 examples clear both floors, so nothing in the fleet breaks. |
| **LF-7** | **Both GUIs show `N` seeded from the computed value, editable, with a "✕ clear" back to computed**; `NLG` is rendered as a derived output beside it, never as an input. A caution fires when the entered `N` is **below** the energy `N`. | Owner ruling on the display; the clear affordance is what makes LF-2's `Optional` reachable from the UI instead of only from JSON. The caution is not hypothetical — `cessna_210` will trip it (3.1670 entered vs 3.3885 computed). |
| **LF-8** | **Schema `SCHEMA_VERSION` 56 → 57**, with a **semantic** hop: `airplane_load_factor = gear_load_factor + lift_factor` where `gear_load_factor` was non-zero, else `None`; the old key is dropped. | Owner ruling on the formula. Unlike OV-10's identity hop this one carries meaning, because the field's role inverts — an identity hop would silently re-point every existing project at the energy equation. |
| **LF-9** | **`ga6_normal` carries `N = 3.167`** (owner ruling), which is exactly what LF-8's hop produces. | §1.3: the p230 oracle is reproducible at NLG 2.5 and at no other value. The manual rounds NLG up and runs LANDLOAD at an implied N its own LGFACTOR page does not print; this makes that implicit choice an explicit input. |
| **LF-10** | **The three concept examples are set to `N = 2.67`**, not the hop's 2.6670, in the same change and noted in the fixture diff. | §1.3: a 0.11 % rounding artifact would otherwise start three shipped examples emitting a 23.473(g) warning that reports nothing real. |
| **LF-11** | **The hop changes no load number**, `ga6` p230 included: it reproduces every current NLG exactly, and NLG is the only quantity the reaction path reads. The **only** moved numbers in the fleet are LF-10's three concept fixtures (+0.15 % on NLG, from a deliberate fixture edit, stated in its diff) and any case where a user now varies `L` — which is the fix, not a deviation. No entry in `02_approved_corrections.md`. | Separating "the mechanism moves nothing" from "one fixture was deliberately edited" is what keeps G-LF-5's bit-identical claim honest. |
| **LF-12** | **`field_registry` row is replaced, origin `ORIGINAL` → `SLOADS`.** LGFACTOR.BAS genuinely had an NLG override; it never had an `N` input. The Oracle GUI may carry it regardless, per the fidelity ruling (C210-15: the target is the analysis contract, not the original prompt sequence). | Provenance is a fact about the BASIC, not a preference; recording it honestly is what keeps the registry auditable (`field_registry.py` §basis). |

---

## 3. Closure gates (G-LF-1 … G-LF-6)

Benchmark-first (rule 2). Identities exact (`rel_tol=1e-9`); oracle suite ±0.1 %.

| Gate | Statement | Expected numbers |
|---|---|---|
| **G-LF-1** (oracle invariance) | The Appendix A p236 assertions pass **unmodified** — they read `LoadFactorResult` off `landing_load_factor`/`build_landing` (`tests/test_landing.py:131-133`, `:235`, `:336-338`), which LF-3 leaves untouched. p230 passes with ga6 at LF-9's `N`. | V 9.0048 / N 3.0951 / NLG 2.4281; K 0.324 / γ 17.978 |
| **G-LF-2** (L moves the reaction) | The defect dies, stated as a test: on ga6 at fixed `N`, raising `L` 0.667 → 1.0 lowers NLG 2.500 → 2.167 and lowers `VMP` on cases 4–12 by the same **13.3 %**, and raises `K` 0.3245 → 0.3743 (γ 17.98° → 20.52°) *(corrected at implementation, #123: originally printed 0.3586/19.72°, an arithmetic slip against §1.1's own `K = NAP/NLG·K0`)*. The pre-fix behaviour — *no change at all* — is written into the test's docstring. | ΔNLG = −0.333 exactly; VMP ratio 2.167/2.500 |
| **G-LF-3** (N is recoverable from the reactions) | `NVP == N` exactly on cases 4–9 and `NVP == ½·NLG + L` on 10–12, for every bundled example. This is the closure gate rule 2 requires with the feature, and it converts the assembled-deck NVP/NDP check ([balanced_deck.py:326](../../sloads/export/balanced_deck.py)) from an identity into an assertion. | rel 1e-9 |
| **G-LF-4** (the guards) | `N ≤ L` is refused by name; the 23.473(g) floors block in FAR 23 and warn in concept, from one policy owner with a drift guard. All six examples pass their own category's rule. | ga6/cessna N 3.167 ≥ 2.67, NLG 2.5 ≥ 2.0; baron 3.3642 / 2.6972; the three concept rows 2.67 / 2.003 |
| **G-LF-5** (schema round-trip) | A v56 project with `gear_load_factor: 2.5, lift_factor: 0.667` loads through the 56→57 hop to `airplane_load_factor: 3.167` with the old key gone; one with `0.0` loads to `None`; `applied_hops(56)` names the hop; the schema ledger records it. | `SCHEMA_VERSION == 57`; every example's 33-case matrix bit-identical across the hop |
| **G-LF-6** (both GUIs) | `app/` and `oracle_app/` each render `L` uncapped with the FAR-default caption, `N` seeded-and-clearable, `NLG` as a derived output; the below-computed-`N` caution fires on `cessna_210` and not on `ga6`. | The caption text enumerated once, in the guard |

**Closure tier:** **L** — this note at AGREED first, then implementation with
`PROGRAM_SPEC.md` §LGFACTOR/§LANDLOAD rewritten (including the "rounded design
input … distinct from LGFACTOR's computed 2.428" sentence at :395, which states
the defect as intent), `theory_sources.md` grown one row for the FAR 25 lift
basis, the schema-ledger entry, a **full-format** history fragment, a `changes/`
fragment, the regenerated `DATA_DICTIONARY.md`, and
`docs/60_guide/14_landing_loads.md` + its screenshot re-captured
(`scripts/capture_guide_shots.py`).

---

## 4. The sweep (practice 4 — generalize on first find)

Every stored value that replaces a derivation, tested for the three symptoms of
§1.2: **S1** a sibling input stranded, **S2** the GUI reporting the un-consumed
value, **S3** unset and legal-value sharing one encoding.

| Field | S1 | S2 | S3 | Verdict |
|---|:--:|:--:|:--:|---|
| `landing.gear_load_factor` | ✓ | ✓ | ✓ | **This note.** The only instance with all three. |
| `weight.estimation.max_continuous_hp` + `override_max_continuous_hp` | ✓ | — | — | **Same class, mitigated.** With the flag set, editing the per-engine HP rows changes nothing — but the switch is an explicit named boolean, registered `SLDS`, so it is visible rather than silent. No action. |
| `weight.envelope.gross_weight` | — | — | ✓ | **Dismissed.** `or` sentinel, but reconciled against the MTOW SSOT and explicitly guarded against the reverse G-14 fallback ([weight_envelope.py:172-177](../../sloads/modules/weight_envelope.py), note 36 OV-1/OV-2). Strands nothing. |
| `speeds.chosen_vc` | — | — | — | **Dismissed.** `Optional`, and a *floor* (`max(chosen, vc_min)`, [structural_speeds.py:363](../../sloads/modules/structural_speeds.py)), not a replacement. |
| `aero.surfaces[].tau` | — | — | — | **Dismissed.** `Optional`, `ORIGINAL` provenance (TAU.BAS's own escape hatch, [airloads.py:138-148](../../sloads/modules/airloads.py)); the taper/tip inputs it supersedes still reach the planform. |
| `fuselage.stations_are_override`, `panel.weight_is_override`, `envelope.mac`, `engine.inertia`/`prop_inertia`, `d_cm_dalpha`, `izz_slugft2` | ~ | — | — | **Same shape, all mitigated** — explicit named flags or `Optional` with the clear affordance. No sentinel collision. |

**One unmitigated instance exists: the one this note fixes.** The pattern recurs
eight more times and every other occurrence had the sentinel removed
(`Optional`) or the switch named (`*_is_override`) — which is precisely why none
of them can strand an input silently. Note 36's OV-1 mechanism is why: the class
was already swept once, and this field was not in its eight because it reads as
an *override of a computation*, not as a *duplicate of another input*.

**One adjacent finding, different class — filed separately, not fixed here.**
The max-continuous-HP precedence rule is written twice —
`weight_estimate.resolve_max_continuous_hp`
([weight_estimate.py:345-359](../../sloads/modules/weight_estimate.py)) and
again inline in the view
([weight_mass.py:206-208](../../app/views/weight_mass.py)). Two copies of one
precedence, currently agreeing. That is the drift practice 3 forbids and the
same shape as the `_ground_angle` duplication `landing.py` already calls out in
prose.
