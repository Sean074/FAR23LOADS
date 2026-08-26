- **An Optional override entered in the oracle GUI could never be taken back**
  (PB-20, issue #72, tier M, 2026-08-25). Once `landing.gear_load_factor`,
  `speeds.chosen_vc/vd`, `aero.surfaces[].tau` or `weight.envelope.mac` held a
  number, nothing in this GUI could return the field to "computed" — and it is
  the only editor its projects have, so a value typed to see what it did was
  permanent. The review's proposed fix (write `None` when the widget comes back
  empty) cannot work: a number-seeded `st.number_input` never comes back empty,
  because the frontend restores the last value and the serde reads an empty
  submission as the seed. A filled Optional field now carries a **✕ clear**
  button — a deliberate named click, the posture row deletion already takes —
  which empties the widget through the one door Streamlit offers, its own state,
  from the `on_click` callback that is the only legal moment to write it. The
  next render reads the empty widget and unfills the field on its normal persist
  path, so there is still exactly one writer. Required fields offer no clear
  (`None` is not one of their values) and neither do the display-only copies of
  a quantity someone else owns.
- **The confirmation for the one action that writes outside the session was
  never seen** (PB-23, #72, tier S, 2026-08-25). Save-to-disk emitted
  `st.success` and then `st.rerun()`, which discards the frame that carried it.
  It is a toast now — the channel the loader's repair warnings already use
  because it survives the rerun.
- **A table row could only be deleted from the end** (PB-23, #72, tier M,
  2026-08-25). The row counter plus #88's surplus button meant removing item 3
  of 24 cost twenty-one deletions and twenty retypes. Rows are now deleted where
  they sit: a button inside each row's expander where rows carry a polyline, a
  by-name picker beneath the grid where they do not, both naming the row that
  goes. The deletion re-sizes the counter with it — left where it was, the next
  render grows the list back up to the retained count and the deleted row
  reappears as a blank, which is the #88 data-loss defect wearing the other sign.
- **Clearing a required table cell put the old value back in silence** (PB-23,
  #72, tier S, 2026-08-25). Restoring it is correct — a required field has no
  `None` — but with nothing said, the grid read as having eaten the edit. The
  columns that refused are now named beneath the table, beside the existing rule
  for a row with an empty cell.
