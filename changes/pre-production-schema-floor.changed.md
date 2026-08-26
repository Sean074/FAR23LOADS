- **The six bundled examples are re-stamped at the current schema (#93, tier L, 2026-08-25).**
  They had sat at v41 for fourteen versions, so every example load ran hops 43, 46 and 54 in
  memory — the repo's own fixtures were the only prior-schema files in existence. Regenerated
  through the chain before it was deleted, and verified output-neutral two ways: the `Project`
  loaded from each old file and from its replacement are identical dicts, and
  `tests/fixtures_imperial/digests.json` did not move. New guard
  `test_schema_guards.py::test_every_bundled_example_is_written_at_the_current_version` reads
  the stamp off **disk**, so the next `SCHEMA_VERSION` bump fails CI until the examples are
  re-stamped with it.
