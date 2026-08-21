- **The oracle GUI no longer dirties a project by being looked at (design note 32 step OG-F, tier M, 2026-08-20).**
  Opening an oracle page changed the project on **9 of its 14 pages** with the
  fully-populated `ga6_normal` fixture, and 12 of 14 with a sparser one: the
  sidebar showed "Unsaved changes" and the discard dialog fired at the next load,
  on a user who had typed nothing. Three causes, all in the generic renderer:
  it **attached a record** to the project merely so its widgets had somewhere to
  write; it **rewrote every field it rendered**, turning a JSON `45` into `45.0`
  — the same number, a different file; and in **SI** it converted each value out
  to metric and straight back, so `116 in` returned as `115.99999999999999` and
  the geometry walked a hair on every rerun.
  Fixed in `oracle_app/form.py`: a record created for a page is committed only
  if the pass leaves something in it, a write whose value is unchanged does not
  happen, and an untouched converted field returns the value that was stored
  rather than a reconstruction of it (the same rule `unit_number_input` already
  applied to scalars, now applied to the composite and table widgets that
  convert for themselves).
  `tests/test_dirty_flag.py` — "a render pass must not mutate the project", the
  M2-3 contract — now covers **both** front-ends, every oracle page against every
  shipped example, plus the other half without which "never write anything"
  would pass: a typed value still lands, and still attaches the record it
  belongs to. `tests/test_view_unit_roundtrip.py` adds the SI direction over
  every oracle page and pins the scalar / composite-member paths through the
  renderer.
