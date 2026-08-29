- **The guard that restored the defect it was added to prevent (#122, tier M, 2026-08-29)** —
  Every shipped fixture types its `engines[].limit_load_factor`, so the OV-7
  derive path had never been walked by a test. #71's mutation sweep runs every
  module over every shipped fixture with the planform half-entered and allows
  only `ValueError` out; it passed, because `effective_engine` caught the
  planform's refusal and let the blank stand. Reproducing the reported
  `TypeError` found nothing — the traceback really was gone — but blanking LIMNZ
  in the test rather than in a fixture showed what had replaced it: a
  half-entered wing resolved LIMNZ to 0 and every mount case with it, which is
  precisely the C210-41 defect the derive exists to close. A sweep that asks
  only "did anything escape?" cannot see this: suppressing the exception is one
  of the ways to pass it. So the gate is stated on the *refusal*, not on its
  type — `test_the_limnz_derive_refuses_rather_than_resolving_to_zero` asserts
  the intact planform derives the 23.337 limit, that each of the nine mid-entry
  mutations raises naming `'wing'`, and that an absent wing surface still
  answers off STRSPEED's typed fallback.
  Two structural points beyond the one line. The fix asks
  `derived_geometry.planform_area_sqft` — the precondition's existing owner —
  rather than restating the check inside the engine module (rule 3), which is
  the same discipline #71 imposed on the five strip sweeps. And the new sweep
  `test_a_derive_by_default_field_refuses_through_a_half_entered_planform` runs
  over a mapping of the OV-7 inputs that derive *through geometry*, blanking
  them in the test so the guard cannot be hidden again by a fixture entering the
  number — which is exactly how #122 was found on `baron_58` and then
  re-concealed when the example took the POH's +4.2 [C]. Adding a future
  derive-by-default field to that mapping is the whole of covering it (rule 4);
  today only LIMNZ routes through a planform, the mass-selector derives reading
  `weight.items`, which cannot see one.
