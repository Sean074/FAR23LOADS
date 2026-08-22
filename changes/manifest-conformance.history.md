- **Manifest conformance: the bundle gets one owner and the gate reads the zip
  (CR-C-1 + CR-C-3 `[MAJOR]`, #42, tier M, 2026-08-22)** — the review's third
  theme again, and the clearest instance of its repeated lesson: a gate that
  does not read the shipped artifact rots the first time the code grows past the
  shape the gate assumed. Appendix A exists because of F-D2 ("an artifact the
  controlling document does not name travels without a basis"), and its two
  SHALLs — name every file, name no absent file — were already written when
  three of the bundle's own files walked past them. `lra_model.bdf`, the third
  deliverable, shipped inside every bundle from 0.6.0 with no row; the CLI's
  `lra_loads.bdf` was named in no controlling document; and sweeping the whole
  namelist rather than the reported file turned up two the review had not
  reached — the summary report's own `.tex` and `.pdf`, so the manifest named
  every file in the bundle except itself. The conformance test could not see any
  of it, because it compared the manifest with a hand-kept set of names in the
  test file: the two could only ever agree about what the test already believed.
  So the member list has a single owner, `sloads/report/bundle.py`, pure and
  Streamlit-free, which the Export page loops over instead of deciding its own
  members, and `tests/test_bundle_manifest.py` asserts set **equality** between
  the real namelist and the rendered manifest on the fixture that exports every
  channel, plus a guard that the page writes no member of its own and another
  that reads the page's `_bdf_artifacts` assignments so a new deck cannot arrive
  unnamed. Working the LRA row settled a question the review's proposed fix
  would have got wrong: gating it on `run.cases` names a deck `concept_heavy`
  does not carry — that fixture assembles balanced cases and its LRA model
  refuses for want of a side of body — so the row is gated on the model
  *building*, the price `_gear_cases` already pays for the gear row, and §4.7's
  second SHALL is not broken by the fix to the first. The same read found
  `PROGRAM_SPEC.md` still claiming `ga6_normal` refuses the model; it has built
  one since the fixture-data pass entered its reference axis, and that is the
  sentence saying which bundles carry the new row. CR-C-3 was the same class one
  cell to the right: the manifest declared the LIMIT-by-design inertia check
  ULTIMATE, out by exactly 1.5 on the one artifact whose whole purpose is to be
  compared unfactored against what a solver recovers, and it survived two
  reviews because the conformance test read row names and stopped there. Every
  basis cell is now pinned by its text, exhaustively and in both directions.
  The extraction is the whole of the change to `app/views/export_report.py`, so
  the freeze pending #29 holds and the namelist arrives at the main-GUI review
  as a calc-side owner rather than an open question.
