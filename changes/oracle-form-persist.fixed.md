- **The oracle form's persist path keeps every edit — two edits in one rerun
  both land, a typed 0 lands in an unfilled Optional field, and a held-back
  table row says so (#35, review 2026-08-20 CR-A-1/CR-A-3/CR-A-6, tier M,
  2026-08-21).** `record_at` minted a fresh detached blank for **every** record
  group that walked through a missing ancestor, so on a blank project two
  widget changes in one rerun — fast typing, `data_editor` batching — could
  silently discard one of them: eight groups on the Geometry page each built
  their own blank `geometry`, and the last non-blank chain clobbered the rest
  at commit while the widget still displayed the lost value. `_PENDING` is now
  keyed on `(owner, attribute)` and every group reuses the same pending
  record. With it: an unfilled Optional scalar renders **empty**
  (`unit_number_input(value=None)`) instead of a fake `0.0`, so a deliberate 0
  — sea level, a datum-at-nose station — is now enterable (CR-A-3, same fix in
  flat-table cells); and a curve row with an empty cell is still held out of
  the stored value but the page now says so instead of letting it silently
  vanish (CR-A-6). Guards: `tests/test_dirty_flag.py` (two-edits-one-rerun on
  all four affected page shapes, typed-zero-lands, unfilled-stays-absent,
  incomplete-row caption).
