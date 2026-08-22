- **The concept→FAR23 reduction is gated bit-for-bit, not at ±0.1 % (CR-B-2
  `[MAJOR]`, tier S, 2026-08-22).** `tests/test_concept.py`'s
  `_assert_modules_identical` compared float load values with
  `math.isclose(rel_tol=1e-3)` while its own docstring — and
  `theory_sources.md` — called the reduction *exact*. It is an identity, not an
  oracle comparison: concept mode differs from FAR23 mode at exactly one place
  (`maneuver_load_factors` returns the caller's `(n, n-)` instead of the 23.337
  cap), so feeding the FAR23 caps back through the concept branch re-runs the
  same arithmetic on the same floats. Anything the oracle tolerance absorbed
  would have been a *second* category-dependent branch hiding under 0.1 %, which
  is a finding to investigate rather than a rounding artefact. Now `==`, and it
  passes — no divergence exists today, so the gate is what keeps it that way.
  Swept in the same change (rule 4):
  `tests/test_oracle_inputs.py::test_the_reduced_project_reproduces_every_number`
  was the same defect class — dropping a field that is genuinely not an input
  must change nothing at all, and a value that moves by less than 0.1 % is
  precisely the misclassified registry row that gate exists to name. Also exact
  now, and also already passing; design note 32's ±0.1 % wording remains the
  floor this exceeds. `tests/test_taildist.py::test_airload4_reduction_invariant`
  was checked and was already exact; `test_speed_ratio_route_reproduces_todays_numbers_on_every_example`
  is *not* the class — its frozen pre-F25-2 literals are 6-decimal
  transcriptions, so `1e-6` is required there by construction.
