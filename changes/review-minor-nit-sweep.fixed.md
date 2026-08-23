- **A renamed CG case quietly changed the loads (CR-B-4 `[MINOR]`, #43, tier M,
  2026-08-22).** Every row of the V-n matrix names the weight/CG case it was
  balanced at. When a *persisted* envelope named one the project no longer
  carried, the wing search read the weight as zero and published `nx = 0.0` into
  a WINGINER load case, and the 23.421 h-tail search dropped the candidate with
  a `continue` — a missing candidate being the harder of the two to notice,
  since it leaves no mark in the result at all. Both were reading stale
  persistence as a case with no weight. `default_envelope` — the one owner of
  "persisted, else built" — now **refuses** such a matrix (`ValueError`, naming
  what is missing, what the project has instead, and the module to re-run),
  because the mismatch invalidates every number the envelope carries and not
  only the two that happened to look for a weight. The two reads go through
  `_cg_weight`/`_cg_case` and refuse for themselves too, which covers a caller
  that threads an envelope of its own. The check is deliberately one-way: an
  **extra** flight case the matrix has not seen is an ordinary edit.

- **Two payload cases could mint one `MASSSET` label (CR-C-4 `[MINOR]`, tier
  S).** The label is the case name upper-cased, stripped to alphanumerics and
  cut to sbeam's eight characters, so "Max take-off forward CG" and "Max
  take-off aft CG" both reach `MAXTAKEO`. The SIDs stay distinct — a solver is
  unaffected — but the deck's comment block, the report's mass-case table and
  any label-reading consumer then show two cases, at two weights and two CGs,
  under one name. `massset_labels` gives the second and later claimants a numeric
  suffix in list order; the whole derivable list is passed to `massset_identity`
  rather than one loading, because uniqueness is a property of the set and a
  signature that cannot see the others cannot check it. Disambiguated rather
  than refused: the eight characters are sbeam's and the truncation is ours, so
  a project is not blocked over a display label it did not choose. **No shipped
  fixture collides** (measured: `AFTGROSS`/`FWDGROSS`/`FWDREGAR`/`MINWEIGH`/
  `MIDGROSS`, `CG1..CG4`, `CGMAX`), so no deck bytes moved.

- **`stamp()` skipped a result with no carrier, silently (CR-B-6 `[NIT]`).** An
  unstamped result is one whose report figure and whose bulk-data card can state
  different factors — the F-R1 defect class the governing table exists to close —
  so the skip is recorded in `GoverningTable.unstampable` the way `defaulted`
  records an unclassifiable case, and a test asserts it is empty on every shipped
  path, with a second that proves the recording works.

- **Every widened oracle tolerance now states the effect it comes from (CR-B-5
  `[MINOR]`).** The finding was that several Appendix-A assertions sat at 2e-3 or
  5e-3 against a ±0.1 % contract with no reason beside them. Measuring them found
  the review's two candidate reasons do not divide the way it guessed: case 21's
  speed is 0.22 % out against a print resolution of 0.08 %, so print granularity
  does not explain it, while case 21's tail load is inside the print's own half
  pound and needed no widening at all. So each tolerance is computed from what
  justifies it — the printed figure's resolution, the ±0.005 NZ band, the ±0.005
  CL band on a stall-line speed, or the NZ band through the local slope for an
  angle of attack (which lands at 0.018 deg against a measured 0.020) — and the
  one place a measured allowance stands in, the flapped LANDING case, says so
  with its numbers and its date, because there the print error is in the *input*:
  those aero polynomials are themselves read off a printed page.

- **Three guards that had rotted into always-passing (CR-C-5, CR-C-6, CR-A-8).**
  The body deck's zero-lateral assertion claimed it "goes red the day the ground
  cases land"; they landed in 0.6.0 and it did not, because D-28 made that deck
  flight-only permanently — the comment now cites the decision instead of waiting
  for an event that already happened. `test_ultimate_contract` exempted
  `export_report.py` **wholesale** on a comment's say-so, an exemption that grows
  silently with the file; the page is scanned like every other view now, with its
  two CSVs named individually and a guard that fails when a named exemption stops
  matching a real download. The oracle GUI's one-download-call-site scan covered
  only `oracle_app/`, while the shared shell renders a `download_button` inside
  that same GUI: it covers `app_shell/` too, and bounds what the shell may offer
  by *content* — the project file is an input, not a load deliverable — rather
  than by which directory it lives in. Its CSV-stamp companion accepted the
  ULTIMATE stamp anywhere in the payload, which a data row containing the words
  would satisfy; it must be in the comment block, where a consumer reads it.

- **Wording, and two already shipped (CR-A-7, CR-A-9, CR-D-9).** The oracle
  GUI's LIMIT caption said the basis travels "in its `Basis` column", which is
  wrong for the tail chordwise table — it has no such column and marks every load
  header instead — so the caption states both. Checked while sweeping: **CR-A-9**
  (the 14× `oracle_steps()[0]` recompute) and **CR-D-9** (Download writing
  `.json` where Save/Open use `.project.json`) are already fixed in the tree, and
  are recorded here as verified rather than re-fixed.

- **L-8a closed as shipped, on the evidence.** The parked row said the G6/G6b
  empennage and landing-gear forms hardcode ft²/in labels and ignore the SI
  toggle. They go through `unit_number_input` now, and
  `tests/test_view_unit_roundtrip.py` drives both directions through the very
  widgets it named — H-tail area, `xt25`, tread. Removed from `02_parked.md`.
