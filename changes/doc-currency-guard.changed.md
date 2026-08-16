- **Documentation currency rule + guard (tier M, 2026-08-16).** A standard doc
  never states a number that describes the code's current state — schema
  version, test count, coverage %, "currently N", "version is now X" — it points
  at the owner (`SCHEMA_VERSION` in `sloads/models/project.py`, CI, the generated
  `DATA_DICTIONARY.md`); provenance stays as `schema vN`. Rule:
  `00_program_overview.md` §Documentation currency, `CLAUDE.md` required
  practices, `CODE_REVIEW_PROCESS.md` step 1. Guard `tests/test_doc_currency.py`:
  literal patterns over `README.md`/`CLAUDE.md`/`docs/00_INDEX.md`/`10_standard/`/
  `20_theory/` (generated data dictionary exempt), plus `docs/00_INDEX.md` ↔ the
  docs tree both ways (a doc with no INDEX row, or a row with no file, fails —
  the R6-D2 class). Swept on first find: four `SCHEMA_VERSION = N` currency
  claims in `GUI_design.md` and `PROGRAM_SPEC.md` rewritten as provenance or
  pointers. Origin: the review's finding that R6-D1…D8 shipped past the
  structural guards.
