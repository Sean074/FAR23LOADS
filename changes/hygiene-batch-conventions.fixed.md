- **Hygiene batch — one authority for σ, ρ₀ and every SI display factor; the
  guards that were claimed to exist now exist (backlog Pri 5, tier S, 2026-08-17).**
  Closes the 2026-08-05 conventions-extraction findings (a)–(d), M4-23, CH-3, CH-6,
  CH-7 and the 427 lb fuselage-mass pin in one change. **(a)** `tests/test_load_keys.py`
  written — `LoadValue` keys unique within every `ConditionResult`, every module ×
  every example project (verified zero duplicates before writing). **(b)**
  `constants.py`/`models/results.py` cite "14 CFR 23.303 / 25.303", the SF
  authority's phrasing. **(c)** already carried the comment. **(d)** the three
  partially-shared SI factor maps consolidated: `units.HUMAN_SI` is the one owner
  (every factor a named constant, products derived — `FT2_TO_M2`, `IN2_TO_M2`,
  `HP_TO_KW`, `SLUG_FT2_TO_KG_M2 = FT_LB_TO_N_M`); `SI_PER_IMPERIAL`,
  `UNIT_LABELS`, `_RESULT_TO_SI`, `_SI_BY_QUANTITY`, `_SCALAR_TO_SI`,
  `_KIND_FACTORS` are views built by `_view()`, no call site moved; **CH-7**
  `report/content._EXTRA_DIMENSIONS` takes its four factors from it (labels stay
  the report's ASCII ones, so no deliverable byte moved). **CH-6** `constants.RHO_SL`
  replaces the eight `0.002378` literals under three private names; **M4-23**
  `flight_envelope.density_ratio` now returns `standard_atmosphere(alt)[1]` and
  keeps only FLTLOADS' own speed of sound. **CH-3** `tests/test_tail_transforms.py`
  tests the three empennage maps directly against `CONVENTIONS.md` §7, with the fin
  torsion sign recomputed as `r × F` rather than asserted. **427 lb pin retired as
  superseded** — verified: no FAR23 oracle module reads `fuselage_mass`; `body_loads`
  builds its beam from `weight.items` via B1's `fuselage_beam_stations`, and
  `mass_distribution.fuselage_reconciliation` (+ `test_mass_distribution`) is the
  standing guard on the entered table. The review-§1.7 `[Unreleased]` currency check
  is out of scope: `[Unreleased]` is build-generated from `changes/` since 2026-08-16.
  Guards: `test_constants.py` (ρ₀ literal has one owner; σ delegated),
  `test_units.py::test_every_si_view_reads_the_one_owner` /
  `::test_si_factor_literals_have_one_owner`; `CONVENTIONS.md` §7 gains the two owner
  rows, §8 is closed. Suite, digests and oracles unchanged.
