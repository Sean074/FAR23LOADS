- **The gate that proved boot, and the walk that proved use (#145, tier M,
  2026-08-29)** — The GUI release gate started both front-ends and checked the
  root page answered 200. Every automated test above it rendered **one** page,
  with a **fresh** session, on a **fresh** project, and almost always on
  `ga6_normal`. Between those two shapes sat the defect class that had produced
  both post-0.8.0 escapes: load an example, touch something, find the damage two
  pages later. `tests/test_gui_journey.py` closes it by walking every bundled
  example through every `workflow.py` step in order — one session carried
  forward, widget state included, since the stale-widget class `widget_keys`
  exists for lives in exactly that carry-over — pressing every Apply over
  untouched widgets and then running every registered module. Its assertion is
  that the project comes out byte-identical, because nothing was entered.
  It failed on its first run, and what it found was the reason to have written
  it. #143's ruling — an `Optional` record is created and removed by a named
  gesture, never attached by a touch — had been implemented in the oracle GUI
  through its field registry, and the main GUI, whose pages are hand-written, had
  never received it. Pressing Apply on a page nobody had filled in attached a
  zero-valued slice; on the sparser examples the walk collected eight of them,
  and two were load-bearing: a zero-area `flap_loads` and a zero-cylinder engine
  make their modules raise, so **Results Review and Export were both dead on
  three of the seven shipped examples** — reachable by opening a bundled project
  and clicking Apply. `app_shell/optional_slice.py` is the single owner of the
  app-side rule, which is narrower than the oracle GUI's add/remove pair because
  here the Apply *is* the named gesture: it may fill a slice in and may empty one
  out, but it may not create one out of nothing. "Entered nothing" is read off
  the dataclass defaults rather than a per-page field list, with a `seed=` form
  for the forms whose widget defaults are not the dataclass's, and the walk is
  the drift guard — a new page that writes an `Optional` slice directly fails the
  day it is written.
  The sweep (practice 4) found the same shape inverted three more times: a
  wholesale rebuild that enumerates the fields its own form renders **deletes**
  every field it does not. The Aero Apply destroyed a populated `lateral_body_aero`
  block and re-derived `cruise.stall_cl` from CLmax — the exact failure the
  neighbouring fuselage-moment form carries a paragraph of comment about guarding
  against, worth +30 % on the atr42_100 stall clamp; the Payload Cases Apply
  deleted the `LoadingDefinition` off three of baron_58's six CG cases, which is
  what produces their mass model; the engine form wrote unset `Optional` power
  fields back as stated zeros, #121's class from the writing side.
  The crash had a second cause, and the first attempt at it was wrong. Two modules
  raise a plain `ValueError` for a slice that exists with nothing in it, and the
  obvious move — refuse by name so "run every module" skips them — was made and
  then reverted: `test_cli.py::test_an_invalid_control_surface_input_fails_rather_than_vanishing`
  is m2 ruling that a zero aileron area is an *invalid* input and must fail the
  run, not an absent one to be skipped, precisely so a deck cannot come out one
  case short in silence. The ruling stands and the fix moved to the consumer:
  `run_all_modules_reporting` hands the failures back beside the results, and the
  two pages name the module instead of dying with it. The lesson is the cheaper
  one to have learned from a red test than from a review — a page crashing is not
  evidence that the exception is wrong, only that its reader is.
  The residue is ten writes the walk still sees, kept in the file's `KNOWN_OPEN`
  list with a backlog row and — the part that matters — a test asserting each one
  still reproduces, so an entry cannot outlive the defect it names. The lesson is
  narrower than "test the GUI": per-page coverage and a boot check are both real
  gates and neither can see a journey, and the cheapest thing that can is a walk
  that enters nothing and demands the project come back unchanged.
