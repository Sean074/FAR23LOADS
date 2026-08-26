- **Two GUI copies that told the truth about the wrong number (#70, PB-16/PB-17,
  2026-08-25).** Both halves of this item were the same failure in different
  clothes: a widget stating something about the analysis that the analysis did
  not do. The unit radio was exempted from the project-generation stamp on the
  stated grounds that stamping it "would reset the user's unit choice on every
  project they open" — which is precisely what it is for, because `unit_system`
  is a field of `Project`; the exemption was argued from the widget's subject
  matter rather than from where its value lives, and the result was that loading
  an SI file into an Imperial session edited the file on the way in and flagged
  it unsaved. The wing-area copy was registered against
  `geometry.parametric.wing_area_sqft` while STRSPEED integrates the
  `speeds.wing_surface` planform, so the disabled widget — a widget whose whole
  claim is "this is what the calc uses" — displayed 500.0 against the 497.75 in
  the answer. Fixing the second exposed why it was possible: four separate
  implementations of the same strip integral, guarded by a sweep that scanned
  `sloads/modules/` alone and allowlisted two of the four, so `validation.py`
  grew a third outside its view and the GUI a fourth number that was not the
  integral at all. The integral now has one owner (`planform_area_sqft`), the
  callers keep only their policy for an absent planform, the sweep covers the
  package, and the registry can resolve an external owner's value through the
  same function the calc calls (`EXTERNAL_VALUES`) — which also made the row's
  conditional nature expressible: with no wing surface the field stops being
  inert and becomes what STRSPEED reads, so it goes live rather than staying
  disabled against the advice of its own `MissingInputError`. Two smaller
  defects came out with them, on the generalize-on-first-find rule: the
  wing-area mismatch warning was tagged for Configuration & Layout twice, so
  that page said it twice and Design Speeds never; and captions quoting an
  owner's current value quoted it in Imperial beside a widget rendering SI.
