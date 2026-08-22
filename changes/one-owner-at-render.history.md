- **One owner at render — the registry reaches the widgets (#36, CR-A-2, tier M,
  2026-08-21)** — the last third of the 0.7.0 band's one-owner item, and much the
  smallest, because the two thirds before it changed what was left to do. CR-A-2
  found ten quantities with two or more independently editable copies and
  proposed that the renderer disable the non-owners; the owner's answer was to
  ask why the copies existed at all, and
  [note 33](../docs/30_future/33_derived_scalar_consolidation_note.md) removed
  ten fields outright, leaving four quantities and five copies. That reframing is
  what made the remaining work tractable, and it also changed the *shape* of the
  fix: with the pure caches gone, the survivors are not a homogeneous set to grey
  out. Four of the five are read verbatim by a module — `speeds.weight_lb` by
  STRSPEED, `vtail.gross_weight_lb` and `vtail.airplane_length_in` by SELECT,
  `mach_limit.shoulder_altitude_ft` by MACHLIM — so disabling them would have
  removed a capability, and quietly substituting the owner's value would have
  changed published loads. Only `speeds.wing_area_sqft` is genuinely inert, and
  only because STRSPEED resolves the wing planform first and reaches the field
  solely when no wing surface exists. So the renderer needed to distinguish
  *display-only* from *override*, which no existing registry column could
  express: `derived_from` records **where** a quantity lives, not **whether this
  copy takes effect**. Hence `FieldEntry.governs`, checked against the calc by
  reading each consumer rather than inferred — a distinction that had been
  carried in prose (the registry's `speeds.weight_lb` row still described a
  "read-through" the calc never had, corrected under note 33) and is now a field
  with its own guards. Adding it landed one trap worth recording: the column sits
  before `supplied` on the dataclass, and the `_E` helper built entries
  positionally, so the two bound to each other until the helper moved to
  keywords — a silent mis-tagging of the oracle GUI's whole input set, caught
  only because the guards were run before the field was populated. The marking
  guards were verified by reverting the renderer change and confirming all seven
  fail, the same discipline note 32 §8 records.
