- **The one field registry, and OG-2 amended to close its page set (design note 32 step OG-C, tier M, 2026-08-19)** —
  OG-14 merged two planned tables into one on the argument that they share a key
  and differ only in columns; building it confirmed that and then turned up three
  things the note had not seen. **First**, four columns were not enough. The GUI
  review's duplicate-owner class is not "two pages edit one field" but *one
  physical quantity stored in two fields* — `VTailLoadsInput.gross_weight_lb`
  against MTOW, `EngineInput.engine_weight_lb` against the weight database, 300 lb
  apart on the regional-jet fixture — which `path │ slice │ page │ origin` cannot
  express. Agreed in session: a `quantity` column and an owner-or-`derived_from`
  column, guarded as one owner per quantity with every copy naming its sync. The
  table now records **18** duplicated quantities, the review's five among them
  plus a sixth the writing turned up (`speeds.shoulder_altitude_ft` and
  `speeds.mach_limit.shoulder_altitude_ft` are the same altitude on two
  dataclasses). **Second**, OG-2's page set was not closed: `aero_coeffs` is
  `require`d by both `structural_speeds` and `flight_envelope` but produced only
  by `aero_coefficients`, whose `bas` is `None`, so a page set of exactly the
  `.BAS`-backed steps left 22 fields with nowhere to be entered and made gate G5
  unsatisfiable whatever the calc did. The rule is amended — *a step is an oracle
  page if it runs a `.BAS` program **or** produces a slice such a step requires*
  — still fully derived, which was the part of OG-2 that mattered;
  `workflow.oracle_steps()` owns it and the oracle set is 14 pages, not 13.
  **Third**, the registry absorbed a page-ownership table that had been living in
  a documentation generator: `docs/generate_data_dict.py`'s private
  `PAGE_OVERRIDES` guessed at what `workflow.py`'s `produces` could not
  attribute, and is deleted in favour of the registry's per-field page — so
  `DATA_DICTIONARY.md` now names *both* pages for a slice edited on two, instead
  of flattening it to one. The origin classification itself is the bulk of the
  work and is sourced rather than asserted: 207 of 323 fields are `ORIGINAL`, and
  each row cites the `.BAS` variable name carried over at porting time, the
  `PROGRAM_SPEC.md` line restating UG Table 2.2, or the sloads step that added
  the field. Two standing rulings cover classes rather than rows — surface and
  set selectors are `sloads` (the model carries N surfaces where the original
  carried a fixed one, and the second GUI resolves them positionally), and
  `origin` is about who *asked*, not who *computes*, so a field the original
  entered and sloads now derives stays `ORIGINAL` and carries `derived_from`,
  which is OG-7 falling out of the table rather than needing its own mechanism.
  The guard is `tests/test_field_registry.py`; three of its assertions failed on
  the first run against the author's own table and were fixed there, which is the
  argument for the guard existing.
