- **Three files shipped in the Export bundle with no manifest row, and the one
  artifact that exists to be compared was declared on the wrong basis (CR-C-1
  `[MAJOR]` + CR-C-3 `[MAJOR]`, #42, tier M, 2026-08-22).** Appendix A is the
  bundle's statement of every file it carries and on what basis — "an artifact
  the controlling document does not name travels without a basis" is the F-D2
  finding the section was written for. One release later the class was open
  again on the newest deliverable: `lra_model.bdf` went into the zip from 0.6.0
  and into no row here, and the CLI's `--export-target lra` output was named in
  no controlling document at all. Sweeping the whole namelist rather than the
  one reported file found two more in the same state — the bundle carries the
  summary report's own `<project>_summary_report.tex` and, once compiled, its
  `.pdf`, and the manifest named every file except itself. All three now have
  rows, with the report's own pair pointing at §1.

  **The LRA row is gated on the model building, not on balanced cases
  existing.** `lra_model_bdf` refuses a project missing a datum it must not
  guess (`LraRefusal`: no resolvable SOB, no ref axis, no outline, no spars, a
  strip-pair h-tail attachment), and `concept_heavy` is exactly such a project —
  it assembles balanced cases and produces no LRA deck. The obvious gate, the
  one the review proposed, would have named a file that bundle does not carry,
  which is §4.7's *second* SHALL broken by the fix to the first. The cost is one
  model build per document, the price `_gear_cases` already pays for the gear
  row.

- **The bundle has one owner, and the gate reads the real namelist (tier M).**
  Both of §4.7's SHALLs were already written when all three files drifted past
  them: the rule was never the problem, nothing read the bundle. The old
  conformance test held the manifest against a hand-kept set in
  `test_report_content.SUMMARISED_IN`, so the two could only agree about what
  the test already believed. `sloads/report/bundle.py` is now the single owner
  of the member list — pure, Streamlit-free, importable — and `_zip_bundle` in
  the Export page loops over it instead of deciding its own members.
  `tests/test_bundle_manifest.py` asserts the two sets are **equal** on the
  fixture that exports every channel, that a refused LRA model is neither
  shipped nor manifested, and that the page writes no zip member of its own; a
  companion guard reads the page's own `_bdf_artifacts[...]` assignments, so a
  deck added to the bundle fails here before it can reach a user unnamed. The
  extraction is the whole of the change to `app/views/export_report.py` — the
  freeze holds otherwise, and the namelist is now a calc-side owner that the
  main-GUI review (#29) inherits rather than re-litigates.

- **`inertia_only.bdf` is declared LIMIT, because that is what it is (CR-C-3,
  tier S).** The manifest said ULTIMATE; the file writes `$ Per-node inertia
  load at Nz = …, LIMIT (no SF)` in band, deliberately — its writer's docstring
  is explicit that factoring one side of a comparison and not the other is how
  you make a check pass while meaning nothing, and the roundtrip M-b leg
  compares it unfactored. The controlling document and the artifact were out by
  exactly 1.5 on the one file whose only purpose is to be compared against what
  a solver recovers. The cell now reads "LIMIT (no SF) — comparison only, never
  applied". The reason it survived two reviews is that the conformance test read
  row *names*: `MANIFEST_BASIS` in `tests/test_report_content.py` now pins every
  row's basis text, exhaustively and both ways, with the five cells that name a
  live axis pinned by substring.

- **Swept with it:** `PROGRAM_SPEC.md` said `ga6_normal` and `concept_heavy`
  both refuse the LRA model by design. `ga6_normal` has built one since the
  fixture-data pass entered its reference axis and outline — the sentence went
  stale under a change that had no reason to look at it, and it is the sentence
  that says which bundles carry the row this change added. Only `concept_heavy`
  refuses. The CLI-only `lra_loads.bdf` is named in the spec's LRA section with
  its basis rather than in the bundle manifest, since it never rides the bundle.
