- **Two one-way doors in the oracle GUI (#72, PB-20/PB-23, tier M,
  2026-08-25).** Both halves of this item were the same shape: a state the user
  could enter and not leave. An `Optional` override could be filled but never
  emptied, and a table row could be added anywhere but deleted only from the
  end — and because this GUI is the only editor its projects have, "edit the
  JSON" was not an escape from either. The review's fix for the first (write
  `None` when the widget comes back empty) was tested before it was written and
  does not work: a number-seeded `st.number_input` cannot be emptied at all —
  the frontend restores the last value on blur and `NumberInputSerde.deserialize`
  reads an empty submission as the seed — so no handling of the return path can
  un-fill a field, and the clear has to be an affordance. That made the fix
  structural rather than local: the widget's own state is the only door, it may
  only be written before the widget is instantiated, and the key it is written
  under is spelled two ways (the converted mode suffixes the active unit system,
  the fixed-unit and dimensionless modes must not, so a unit-agnostic number
  survives the switch). One owner now names that key for the widget and for the
  clear alike, so the two cannot drift into clearing a widget that does not
  exist. The row half turned out to carry the counter defect of #88 in mirror
  image: a deletion that does not re-size the row counter is undone by the very
  next render, which grows the list back up to the retained count and returns
  the deleted row as a blank — so the delete runs as a callback, which is the
  only moment a widget's state can be re-sized. Two smaller findings closed with
  them, both about the GUI saying nothing where it had acted: the Save-to-disk
  confirmation was emitted immediately before the `st.rerun()` that discards it,
  so the one action with an effect outside the session had never once been
  confirmed on screen; and a cleared required table cell restored its old value
  in silence, which is the right behaviour reading as the wrong one — a grid
  that ate the edit. The contract both halves now answer to is stated once, in
  `GUI_design.md`, beside the #35 rule it completes: unfilled is empty, a typed
  0 is real, **and the door opens both ways**.
