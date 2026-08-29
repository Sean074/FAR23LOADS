- **The door that only opened (#143, tier M, 2026-08-29)** — The writer half of
  the defect class #144 closed at the consumer, found the same day diagnosing
  the same GA6 V-n failure. `commit_pending`'s rule was that a record the render
  pass created is attached only if the pass put something in it, which is what
  makes a page visit clean (OG-F) — but "something" is any non-blank field, and
  the LANDING coefficient set's own flaps-down flag is a field. Ticking it said
  nothing about the airplane and attached a complete zero-coefficient set;
  `normalize()` then filled its `stall_cl` from `clmax_flap`, so the record was
  permanently non-blank and un-checking could not take it back. Silent data
  *gain*, the inverse of the #51 class, persisting into a saved project file —
  and #144's refusal, once it landed, ended by telling the user to "remove the
  set" through a GUI that had no control for it: an Optional record was a
  one-way door, exactly the finding #72/PB-20 made one level down about a scalar
  override.
  The fix is the row-deletion contract lifted one level: an Optional record is
  created by a named click and removed by a named click, and until it exists its
  fields are off the page behind a caption that says which ones — the same
  answer `_empty_table_note` already gave for an empty table, because it is the
  same question. Two structural points. It is stated for **every** Optional
  record block, not the one it was found on (rule 4): the set of them is read
  from the registry through `optional_steps`, there is no list in the GUI, and
  the parametrised guard
  `test_every_optional_record_block_is_added_and_removed_by_name` walks every
  one of them — detaching each, proving a render and a revisit attach nothing,
  then adding and removing by name. And the add writes *through* rather than
  into `_PENDING`, so the record-block half of the #35/CR-A-1 pending clobber is
  now unreachable rather than guarded: one click is one rerun, so two blocks
  cannot mint competing blanks. The pending path that can still race is the one
  `rows_at` walks, where two tables share a missing ancestor and neither is a
  click; `test_dirty_flag.py` says so where the CR-A-1 cases live.
  The evidence that the posture does not cost the GUI its job is the round-trip
  journey: it types both example airplanes into an empty project from nothing,
  performing exactly the clicks a user would — the answer page carries a record
  wherever it does not offer to add one — and still reproduces the reduced
  answer key byte for byte.
