# Verification Baseline — Release 0.7.0

Permanent regression-baseline record for the `0.7.0` release
(`RELEASE_PROCESS.md` §4 step 5). Like
[`12_verification_baseline_0.6.0.md`](12_verification_baseline_0.6.0.md) this is
a **delta baseline**: it records what 0.7.0 verified, and carries the FAR 23
oracle tables forward from
[`02_verification_baseline_0.3.0.md`](02_verification_baseline_0.3.0.md)
**unchanged** rather than restating them.

**Run at cut (2026-08-23):** `pytest` **2716 passed, 30 skipped, 1 xfailed,
0 failed**; `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/
scripts/` clean (the gate grew by the two GUI packages this release); `mypy`
clean on `sloads/`; `scripts/smoke_test.sh` **PASS** (headless GUI render + CLI
export); `scripts/build_changelog.py --dry-run` clean; `scripts/backlog_issues.py
check` clean with band A empty; `SCHEMA_VERSION = 55`.

---

## 1. Why the 0.3.0 oracle tables still stand

Re-established for this release:

- **Everything 0.7.0 added is additive to the FAR 23 path.** The 22 Appendix-C
  modules' printed-figure assertions in `tests/test_<module>.py` are the same
  assertions against the same manual pages, and they pass in the run above.
- **The approved-deviations register took no entry**
  ([`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md)
  — last entry 2026-08-17, in 0.6.0). The one place the cycle touched a
  `.BAS` truncation — the 23.361(b)(1) stoppage-torque whole-integer basis —
  was closure-gated against the formula and given one owner for GW-BASIC
  `INT()` semantics (`sloads/basic.py`), not deviated from.
- **The derived-scalar consolidation moved no figure** (note 33, DG-1…DG-5):
  ten derived copies were removed from the dataclasses and the two class-C
  duplicate pairs retired by the v55 hop with a *reconciling* migration that
  takes the owner's value and warns on disagreement. Every shipped example
  reloads byte-identical through it; the reduction identity
  (concept → FAR 23 on GA inputs) is gated **exactly**, not at ±0.1 %.
- **The Imperial digest baseline** (`tests/fixtures_imperial/digests.json`)
  still gates every exported byte in Imperial. 0.7.0 spent the wave
  deliberately and recorded each spend in the changelog entry that made it —
  the L-7 case sentence on the five fixtures with lateral cases (no number
  moved with the term off), the fixture-data pass and the CG-datum
  reconciliation, the MINOR/NIT sweep's renamed CG case and `MASSSET` label.
  Every movement is a new channel, a reworded sentence or a stated re-pin —
  never a changed FAR 23 figure.

So §2–§6 of the 0.3.0 baseline — the per-module oracle rows, the
oracle-vs-closure status table and the closure-locked module list — remain the
authority for the FAR 23 core at 0.7.0.

---

## 2. New verification in 0.7.0 — oracles, closure and invariant gates

One 0.7.0 capability has a **printed oracle** of its own — the DATCOM sample
cases for the lateral body aero — and it is locked to it. Everything else ships
with a **stated physics-closure or invariant gate in CI** per `CLAUDE.md`
practice 2. This table adds to the 0.6.0 one; it does not replace it.

| Area | Module / package | Gate | Basis |
|---|---|---|---|
| Lateral body aero `Cy_β`/`Cn_β` | `lateral_body_aero`, `atmosphere` | DATCOM 5.2.1.1 / 5.2.3.1 transcription **oracle-locked to Digital DATCOM's printed sample output** (`ex1`, `ex3` M 0.6/0.8, `ex4`, `ex5`; ±0.1 %, every value within 0.05 %) — `test_lateral_body_aero.py` G1 | note 19 rev. 3 §8 |
| L-7 in the balance | `select`, `balance` | one `body-aero` load per lateral case when enabled (off by default); side force at the body side-area centroid with the free couple closing `Cn_β` about `xw`; Munk's couple has one owner and its yaw form is the cross-check; the fin + body `Cn_β` static-stability verdict flagged when not restoring; **no number moves with the term off** — `test_l7_lateral_balance.py` G2–G12 | note 19 L-7.8…L-7.17, FAR 23.441(a) |
| Engine thrust at the hub | `balance`, `export/lra_model` | the applied thrust and its couple `−T·(z_hub − z_cg)` are the pre-closure `Fx`/`My` **in full**, reacted by `n_x = (D − ΣT)/W` and `q̇`; `ΣT = D ⇒ n_x = 0`; the hub node's transfer couple is exactly zero; six-DOF closure read back from the deck's own cards — `test_hub_thrust.py` G-1…G-11 | note 21 P-6a, #10 |
| The oracle GUI | `oracle_app/`, `app_shell/` | **G1** no dual path (every number from `sloads`, every conversion through `units`, no private CSV writer); **G2** the page set is derived from `workflow.oracle_steps()` and no step key is spelled in the GUI; **G3/G4** the field registry is total in both directions against a type walk of the schema; **G5** the reduced input set is *run* — the same modules run or refuse, every load within ±0.1 % of the full project, four Appendix A figures restated on the reduced project, five of six examples reduce exactly; **G6** round-trip between the two front-ends unchanged; **G7** one download call site, file names from one sanitiser; **G8** one `set_page_config` per entry point, no GUI package imports the other — `test_oracle_gui.py`, `test_oracle_inputs.py`, `test_field_registry.py`, `test_app_shell.py` | note 32 OG-1…OG-14 |
| The oracle GUI's project *is* the gate's project | `oracle_app/results`, `field_registry` | the typed project is the reduced key; every page gives the reduced key's numbers; **save → reload → rerun is a fixed point** — `test_oracle_journey.py` (#62) | pre-cut review PB-1…PB-3 |
| Inputs with one owner | `oracle_app/form`, `models/project` | seeded, unique, case-insensitive selector names; coded inputs withheld until they agree (#63); an engine layout that disagrees with its engine count is asked, never enforced — loader warns, oracle page withholds, WINGGEOM refuses by name (`test_engine_layout_consistency.py`, #66) | PB-4…PB-7 |
| The shell | `app_shell/` | the project-file block renders **after** the page so the download and the dirty flag describe this rerun's edit; no view calls `st.stop()` directly (`stop_page()` is the owner); an Upload is processed exactly once across reruns; Save over another project asks first; widget identity is generation-stamped so a loaded project reaches every widget and a stale one cannot overwrite it — `test_app_shell.py`, `test_widget_freshness.py` (#64, #65, #34, #51) | GUI_design §4/§5 |
| The unit boundary, everywhere | `app_shell/components` | every project-seeded numeric widget in both GUIs goes through `unit_number_input` (98 `app/views/` widgets keyed in the same pass; the guard fails closed on an unkeyed one) | #44, #51 |
| Derived scalars | `models/`, `io` | one owner per quantity in the dataclasses (DG-1…DG-5); the v55 migration reconciles and warns; pre-v55 files load | note 33 DS-1…DS-7, #52 |
| The balance says how it ended | `balance` | converged / clamped / failed are distinct states with one predicate owner; a solve that cannot close says so and the one that closes on nothing is named, not refused; force and pitch judged against their own acceptances; the residual-gate exemption has one owner and §6 declares nothing the code does not (#33, #41) | review 2026-08-20 CR-B/CR-C |
| Sudden-stoppage torque | `engine_loads` | 23.361(b)(1) formula closure with the whole-integer truncation basis stated; `INT()` semantics owned by `sloads/basic.py` | CR-B-3 |
| Export bundle | `export/` | the bundle has one owner and the manifest gate reads the real namelist; `inertia_only.bdf` declared LIMIT | CR-C-1/C-3 |
| Platform-stable picks | `sloads/` | every keyed `max`/`min` is first-in-order inside the band and the guard cannot be satisfied by an empty match | #38 |
| Decisions, not work | — | **D-28** no combined flight + ground station envelope (the two families are assessed with different internal-pressure companions); **D-29** the derived `ACRL` point names SELECT's own pick; **D-30** the ATR-42's Mach-capped corner is stall-limited flight (the past-fit coefficients filed as #32); **D-31** the gust-shape study merged — reusing Schrenk is inside the Schrenk band by construction | backlog re-cut 2026-08-18 |
| Process | `scripts/`, `docs/`, `.github/` | `test_doc_currency` (no copied numbers; INDEX ↔ tree both ways), `test_changelog_fragments`, `test_backlog_issues`, `test_solo_scripts` (`--suffix`/`--date`, fragment name printed); the PR-fast CI gate on `dev/**` with the full matrix on the merge to `main` | notes 26/28, solo profile |

---

## 3. Stated exceptions, pinned rather than hidden

Each is an asserted bound that goes red when it changes in either direction.
The 0.6.0 list is carried forward with these changes:

| What | Where pinned | At 0.7.0 |
|---|---|---|
| Pre-closure pitch residual, per fixture and family | `test_balance.py::_PITCH_RESIDUAL_RATCHET` under `FORCE_RESIDUAL_CEILING` / `CLAMPED_PITCH_CEILING = 0.025` | carried forward; a **powered** case stands outside the 1 % pre-closure gate by design with a stronger gate of its own — its residual *is* the entered thrust, in closed form (`test_hub_thrust.py`); no shipped fixture enters a thrust, so every shipped number is unchanged |
| Lateral cases outside the pre-closure gate | `test_l7_lateral_balance.py` | carried forward; with `lateral_body_aero.enabled` the measured effect is stated, not absorbed — RJ `\|n_y\|` +11 / +11 / +33 %, `\|ψ̈\|` −73 / −71 % / reversed; ga6 `\|n_y\|` +27 / +27 % / ×2.9, `\|ψ̈\|` −41 / −40 % / reversed; both fixtures directionally stable (net −0.00154 / −0.00107 per deg) |
| Which examples reduce exactly to the oracle input set | `test_oracle_inputs.py` | **5 of 6** exactly; `concept_regional_jet` excused in the file with its reason (the 25.335(b) Mach-margin route and turbofan engine data have no counterpart in the original suite); a new example must be one or the other |
| The one quantity the reduction drops | `test_oracle_inputs.py` | `root_torsion_myy_lra` — declared sloads-only output, not a lost oracle |
| ATR-42 balanced points above the Mach-capped stall CL | `test_aero_curves.py` | carried forward; **D-30** records it as ordinary stall-limited flight, the past-fit marker is #32 (band C) |
| The SELECT unsymmetrical split | `test_balance._UNSYMMETRICAL_SPLIT` | carried forward (≤ 0.08 % per value) |
| Which conditions assemble / which decks each fixture produces | `test_balance.py`, `test_export_equilibrium.py` | carried forward; the 23.499 supplementary nose-wheel family skipped with a recorded reason |
| Widened oracle tolerances | per test | every widened tolerance now states the effect it comes from (CR-B-5) |

**Skips at cut (30) and the one xfail.** Every skip is structural with a
stated reason — a fixture that carries no control-surface, tail, h-/v-tail
spanwise or station-table slice; a `app/views/` page with no Apply form
(`test_configuration_layout_view.py`); the `roundtrip`-marked tests, which run
in their own CI job with the pinned solver. The `xfail` is the standing one
(`test_sbeam_roundtrip.py`: sbeam's dense-path condition heuristic refuses the
mm channel), a reasoned expectation, not a hidden failure. No skip without a
backlog entry (`RELEASE_PROCESS.md` §3.3).

---

## 4. Standing limitations of a 0.7.0 deliverable

All travel **in band** (deck `$` headers, case notes, the report's methods &
limitations section) and the key set is pinned by test.

1. **The oracle GUI is a beta.** It is functionally complete on the fresh-project
   journey through all fourteen pages, and the pre-cut review's sixteen
   KNOWN-ISSUE findings ship as the release notes — band B rows 11–18
   (#67–#74): gate-rot proxies, the migration notice that cannot fire, page-order
   dependencies that silently change downloaded numbers, the shell unit radio
   beating a loaded project's system, masked errors, Optional overrides that
   cannot be cleared, presentation nits and note 32's wording drift.
2. **Lateral aerodynamics are fin-only by default** — the wing-body `Cy_β`/`Cn_β`
   term ships (L-7) but is **off unless enabled**, because it raises `|n_y|` and
   lowers `|ψ̈|`; every lateral case states which it carries.
3. **Power effects on the wing are the hub thrust only** (note 21 P-6a) — one
   entered axial `FORCE` per engine, reacted by the closure; `N_p`, slipstream,
   the DATCOM increments and the `-P` families stay parked. Ground cases state
   the entered thrust and do not apply it; an asymmetric entry is stated, not
   handled.
4. **Pressurization is out of scope, permanently**, and with it any combined
   flight + ground station envelope (**D-28**).
5. **23.427(a) ships as a handed pair and is a maneuver case.**
6. **Concept mode is closure-locked, not oracle-locked** (decision **D-R6**).
7. **Engine failure is propeller-only** (#4) — ONENGOUT refuses an installation
   without a propeller disc.
8. **The `app/views/` UI is frozen pending the 0.8.0 GUI review (#29)**; the
   0.7.0 carve-out was exactly `key=` plus the unit-boundary helper at the
   #51/#44 call sites.

---

## 5. What measurement changed in this release

Each was found by a check, not by review — the argument for the gates.

- **The oracle GUI's project was not the project gate G5 tests**: `mass` was
  never produced from the page, items were untagged, rotors and station tables
  sat outside the reduction — found by walking the fresh-project journey
  (PB-1…PB-3); the journey is now a fixed point in CI.
- **98 unkeyed `app/views/` widgets lost data on a shipped example** (#51's
  reopen, reproduced 2026-08-22); the guard now fails closed on an unkeyed
  project-seeded widget.
- **A blank-seeded selector name silently changed loads** (#63): the form's
  "first row wins" pick had no owner.
- **Two modules resolved the one wing area with opposite precedence** (note 33
  CR-A-2) — the measurement behind removing ten derived copies.
- **2 of the 14 oracle pages sent a fresh project upstream for a slice their
  own form enters** (#45, measured, not asserted).
- **The download and the dirty flag lagged the page by one edit** (#64): the
  sidebar serialised before the page persisted — a rerun-order fact, verified
  under `AppTest`, and the reason the project-file block now renders after.
- **An engine layout could save a file the loader refused** (#66): the only
  cross-field rule enforced at construction.
- **Nine published ATR-42 rows evaluate coefficients past their fit** (D-30) —
  no governing load affected; filed as #32 with the number.

---

## 6. Supersession

This document **supplements** the 0.3.0 baseline for the FAR 23 core, the 0.4.0
and 0.5.0 baselines for the balanced free-free deliverable and the 0.6.0
baseline for the ground family and the LRA model, and **supersedes** nothing in
them except 0.6.0 §4 item 2 (lateral aero is no longer fin-only) and item 6
(the hub thrust ships). The next full re-statement of the oracle tables should
happen the first time a FAR 23 printed figure is affected.
