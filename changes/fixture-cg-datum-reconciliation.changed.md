- **Fixture CG datum reconciled and the flight cases pinned to the WTENV limits (D-27; the remainder of the fixture-data pass, issue #9, tier L, 2026-08-17).**
  Root cause found and closed: the four type fixtures' fuselage-carried item
  stations were hand-entered (2026-07-15) on a datum ~20–65 in aft of the wing
  polyline's, so every D-26 CG case — not only the all-up loading — sat 15–25 in
  aft of the entered `%MAC` aft limit, at 51–65 % MAC. Item stations are the
  less authoritative input (D-27a): the fuselage-carried rows shift onto the wing
  datum so the empty CG sits at a type-plausible %MAC (C210 18, ATR-42/Dash 8 25,
  RJ 35); wing-tied and tail rows do not move; the C210 nose group and the RJ's
  engines/gear/crew are held by hand and the RJ's cabin/holds re-spaced. The
  cases turn round with them: **a FLIGHT case is now a WTENV structural-limit
  point by construction** — new `cg_cases.seed_flight_cases` (aft gross, fwd
  gross, fwd regardless, min weight + `mid gross`), loading derived under D-25d's
  10 % gate (0–8.5 % solved ballast on every case), `zcg` the closing loading's
  own; the ground three re-seeded by `seed_landing_cases`; `mass.cases` and the
  legacy `flight_loads`/`landing` mirrors regenerated. On the Appendix A airplane
  the seed reproduces CG1..CG4 (85.1 / 77.49 / 72.64 / 73.09) — ga6 is untouched.
  New warning `mass_item_outside_body` (a fuselage-carried row ahead of the
  outline's nose or behind its tail; fore/aft extent only) — the three-view's
  claim made structural; the ga6 outline's nose moves to FS −12 (spinner tip:
  Appendix A's propeller sits at −10) so its Appendix A rows are inside it.
  Guards: `tests/test_cg_cases.py` (fixture cases *are* the seeds; every case
  inside its envelope; every fuselage item inside the outline; the ga6
  reproduction). Re-pinned by design (`test_balance.py` and friends): the closure
  `Izz`, the lateral cases, the unsymmetrical split, the `dCD` bands, the
  residual ratchets (worst symmetric force residual now `atr42` 2.36 % at the
  aft-gross point — under the 2.5 % hard stop, same lift-model reading, heavier
  case; RJ down to 0.48 % unclamped), the ATR PHAA speed (185.36 kt) and its
  25,000 ft stall exceedance (9 points, +0.27), the RJ fin roll arm. Digest wave:
  35–37 channels on each of the four fixtures; `ga6_normal` only the four
  outline-nose channels (h-tail attachment / LRA / balanced deck / tail text —
  balance CSV unmoved); `concept_heavy` untouched. WTENV's degenerate-marker
  tests rebuilt on synthetic databases (the RJ no longer exhibits them). Closes
  the WTENV-envelope defect and #9.
