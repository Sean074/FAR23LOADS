## Step #123 — The landing load factor is entered as N, not NLG (note 37, tier L, schema v57, 2026-08-27)

**Objective.** Kill a defect with a first-order effect on shipped output by removing its class.
`LandingInput.gear_load_factor` was an NLG override that superseded LGFACTOR's energy result;
because `VMP = ½·NLG·W·AP/DP` reads NLG and nothing else, an entered NLG made the wing lift
factor `L` **inert on the vertical gear reaction** — the user changed the lift assumption and
no wheel load moved — while the page kept reporting the *energy-derived* N the reactions were
not computed from, and the `0.0` sentinel gave "unset" and a legal value one encoding. Vertical
equilibrium at peak load is `N = NLG + L`: three quantities, one equation, two degrees of
freedom, and which two are inputs decides whether L moves the reaction. The fix inverts the
pair — **`N` and `L` are the inputs; `NLG = N − L` is derived, reported, and never entered.**

**Deliverables.**

- **`landing.governing_load_factors`** — the one owner of the governing pair: entered `N`
  (`LandingInput.airplane_load_factor`, `Optional`, no sentinel) when filled, else the energy
  value; `NLG = N − L` derived nowhere else; `N ≤ L` refused by name (LF-5 — with the L cap
  gone, the only guard between `K = NAP/NLG·K0` and a zero or sign-flipped NLG).
- **The `L ≤ 0.667` refusal and widget cap removed** (LF-4): 0.667 is FAR 23.473's default and
  1.0 the FAR 25.473(a)(2) basis; both GUIs caption them as guidance through one shared string
  (`app_shell.components.LANDING_L_FAR_CAPTION`).
- **The 23.473(g) floor policy** (LF-6, one owner + drift guard, practice 3):
  `landing.far23_473g_floor_violations` with the floors in `constants.py`; a governing pair
  below `N ≥ 2.67` / `NLG ≥ 2.0` is a named refusal in a FAR 23 category (`build_landing`) and
  a warn-only note in concept (`run`), superseding the M2-8 concept-only warning.
- **Schema v56 → 57, semantic hop** (LF-8): `N = gear_load_factor + lift_factor` where the old
  override was non-zero, else unfilled; the old key is dropped. The hop reproduces every NLG
  the reaction path read, so no load number moves (LF-11). `ga6_normal`/`cessna_210` carry
  `N = 3.167` (LF-9 — p230 reproduces at NLG 2.5 and at no other value); the three concept
  examples are set to `N = 2.67`, not the hop's 2.6670 (LF-10 — a 0.11 % rounding artifact
  would have started three shipped examples warning on nothing real; NLG moves +0.15 %, the
  only moved numbers in the fleet). `field_registry` row replaced with origin `SLOADS`,
  `supplied` (demonstrably load-bearing, G5): LGFACTOR.BAS had an NLG override, never an N
  input (LF-12).
- **Both GUIs** (LF-7): `app/` seeds N from the computed energy value with a "Computed N
  governs" checkbox as the way back; the oracle GUI renders the unfilled Optional with
  "✕ clear" and a landing group note stating the computed → governing pair. `NLG` renders as a
  derived output in both; `landing.below_energy_caution` (one owner) fires when the entered N
  undercuts the energy value. The module output gains governing-N/NLG rows beside the
  oracle-locked energy rows (the S2 fix at the deliverable, not only on screen).
- **Docs.** `PROGRAM_SPEC.md` §LGFACTOR/§LANDLOAD rewritten (including the sentence that
  recorded the split as intended behaviour); `theory_sources.md` grown the FAR 23.473(g) /
  25.473(a)(2) lift-basis row and the governing-pair citation; the schema ledger
  (`test_schema_guards.py` + `project.py`) records v57; `DATA_DICTIONARY.md` and the guide
  tables regenerated; guide chapter 14 rewritten with its screenshot recaptured. Note 37's two
  arithmetic slips corrected in place, marked as implementation corrections (LF-5's inverted
  refusal; G-LF-2's K/γ figures).

**Test / Acceptance (gates G-LF-1 … G-LF-6, all in CI).**

- **G-LF-1 (oracle invariance):** the p236 Appendix-A assertions pass unmodified —
  `landing_load_factor` is untouched (LF-3); p230 passes with ga6 at `N = 3.167`.
- **G-LF-2 (L moves the reaction):** on ga6 at fixed N, raising L 0.667 → 1.0 lowers NLG
  2.500 → 2.167 and every case-4–12 VMP by exactly 2.167/2.5, and raises K to
  `(3.167/2.167)·0.256133 = 0.3743` (γ 20.52°); the pre-fix behaviour — no change at all — is
  in the test's docstring.
- **G-LF-3 (N recoverable from the reactions):** `NVP == N` exactly (rel 1e-9) on cases 4–9
  and `NVP == ½·NLG + L` on 10–12, for every bundled example.
- **G-LF-4 (the guards):** `N ≤ L` refused by name; the floors block in FAR 23 (energy-governed
  *and* entered-N paths) and warn in concept; the floor constants drift-guarded; all six
  examples pass their own category's rule.
- **G-LF-5 (schema round-trip):** the frozen v56 fixture hops to `N = 3.167` with the old key
  gone, the `0.0` sentinel loads to unfilled, `applied_hops(56) == [56]`, and the migrated
  project's 33-case matrix is bit-identical to the current fixture's.
- **G-LF-6 (both GUIs):** the caption enumerated once and consumed by both GUI sources
  (guarded); the below-computed-N caution fires on `cessna_210` (3.1670 vs 3.3885) and not on
  ga6. Imperial digests deliberately regenerated: landing channels on all fleet examples (the
  new governing rows), balance/gear/deck channels on the three concept fixtures only (the
  LF-10 nudge) — ga6/cessna/baron load channels byte-identical, as LF-11 promised.

**Key decisions.** LF-1 … LF-12 in `docs/30_future/37_landing_load_factor_note.md` (AGREED
2026-08-27); implementation choices in session: energy + governing rows both reported (not
governing-only), one solo-close commit, floor policy homed in `modules/landing.py` with
constants in `constants.py`.
