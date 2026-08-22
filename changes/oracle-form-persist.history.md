- **Oracle form persist path made loss-free (#35, review 2026-08-20
  CR-A-1/CR-A-3/CR-A-6, tier M, 2026-08-21)** — the 0.7.0 band's Pri 1: the
  generic renderer's detached-record machinery (`_PENDING`, note 32 OG-F)
  appended a **fresh** blank for every record group that walked through a
  missing ancestor, so two edits in one rerun on a blank project raced their
  own blank chains and `commit_pending`'s last writer clobbered the earlier
  edit — what the user typed was not what reached the calc, and a Save carried
  the loss to disk. `_PENDING` is now a dict keyed on `(id(owner), attribute)`;
  `record_at`/`rows_at` reuse the pending record every later group asks for,
  preserving the whole-chain-or-nothing commit. Two riders landed with it,
  swept across both persist sites (scalar widgets and flat-table cells): an
  unfilled Optional scalar renders empty via `unit_number_input(value=None)` —
  the shell boundary's new Optional mode, stated in `GUI_design.md` §7 — so a
  deliberate 0 is no longer indistinguishable from the seed and unpersistable
  (the review's park-with-number escape did not survive checking: sea-level
  `one_engine_out.altitude_ft` and `fuselage_nose_x` have meaningful zeros);
  and `render_curve` captions when a partially-filled row is held out of the
  stored curve rather than dropping it silently. Guards in
  `tests/test_dirty_flag.py`: a two-edits-one-rerun AppTest per affected page
  shape (`configuration_layout`, `weight_mass`, `landing_loads`,
  `structural_speeds`), typed-zero persistence, unfilled-stays-absent on
  render, and the incomplete-row caption.
