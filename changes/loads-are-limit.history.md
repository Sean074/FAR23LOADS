## Step — Every load is LIMIT: stated, never applied (design note 49, tier L, 2026-09-05)

**Objective.** Carry the owner's ruling — *"FAR 23.303 safety factor IS an
external loads factor; for this version of sloads all loads will be identified as
limit loads WITHOUT the safety factor applied"* — through the whole project.
This is **OR-116/OR-117**, and it overrules note 48's OR-87 and OR-93, which had
kept the deck and the summary report on the ultimate basis. It also dissolves the
cost note 49 §3 accepted under protest: *"the project ends 0.8.3 with two reports
on two bases."* The reasoning is a division of responsibility, not a tolerance:
sloads is an external-loads program, and 14 CFR 23.303 says the factor must be
applied without saying by whom. The loads program delivers the prescribed limit
load and states the factor; the sizing step applies it.

**Deliverables.** The multiply is **removed** from 81 sites across 7 files —
`report/render.py`, `report/content.py`, `report/oracle_sections.py`,
`export/sbeam_bridge.py` (73 sites), `export/balanced_deck.py`,
`export/lra_import.py`, `export/lra_model.py` — rather than neutralised: a
`_sf()` returning 1.0 would have left every `* sf` as dead arithmetic that still
read as if a factor were applied. `_sf` survives as the *stated* factor.
`report.LoadChannel` loses its `ULTIMATE` member, so a stale caller fails at
import instead of silently receiving limit loads; `to_ultimate` and `_ult` are
deleted. `export.sbeam_bridge.basis_sentence` becomes the single owner of the
deck's per-subcase statement (OR-117) across all eight deck writers. Every
in-band basis statement on every shipped artifact was rewritten to match its
contents, and the standard docs record the inverted contract:
`CONVENTIONS.md` §3 (retitled), `CLAUDE.md`'s Phase C mission sentence,
`PROGRAM_SPEC.md` M4-15, `SUMMARY_REPORT.md` §3.1, `ORACLE_REPORT.md` §3/§3.4,
`00_program_overview.md`, `PROJECT_GUIDE.md`, `GUI_design.md`,
`GUI_USER_GUIDE.md`, `theory_sources.md`, `safety_factors.py`'s row bases
(OR-88's rewording: `SF=1.0` reads *"already ultimate; apply nothing"*).

**Test / Acceptance.** Full suite green (3515 passed), `ruff` and `mypy` clean.
Three new gates, because **the existing suite could not see this change at all**:

* **G-OR-71** (`tests/test_limit_channel.py`) — a text scan asserting no path in
  `sloads/` multiplies a load by a safety factor. Its own teeth test found a real
  gap in the scan on the first run: the pattern was anchored to the bare name and
  matched neither `* c.safety_factor` nor `* r.safety_factor`, which are exactly
  the spellings removed from `content.py`. One documented carve-out, named with
  its reason: `flap.py`'s `sf` is FLAPLOAD.BAS's name for the flap area of one
  side.
* **G-OR-72** (`tests/test_export_equilibrium.py`) — the balanced deck's `FORCE`
  resultant closes against `nz × W` **without** the factor. Every pre-existing
  deck check is scale-invariant, so all 3400 tests were green at either basis;
  the 1.5000 ratio between the two (27,037.996 vs 40,556.996) was measured by
  hand before this gate existed. Mutation-verified: it fires on all six fixtures
  while 154 other equilibrium checks stay green.
* **G-OR-73** (`tests/test_deck_basis.py`) and **G-OR-74**
  (`tests/test_basis_statements.py`) — the deck and every rendered document must
  state, per subcase, the factor they did not apply, and the stated number must
  be the case's own. Both mutation-verified.

The Imperial baseline was regenerated twice, deliberately, and each move was
accounted for before the regeneration: **208 of 330 digests** for the basis change
itself (all `sbeam/*`, `gear_report`, all `txt/*` headers; the 122 unmoved are
`csv/*`, LIMIT since note 48, and `case_index`, which carries no load value), then
**2 channels × 5 examples** for the two deck sentences corrected afterwards.

**Key decisions.** OR-116 … OR-120 and OR-118a, design note 49 §8, ruled by the
owner in session on 2026-09-04/05. **OR-120** moved the LIMIT core from 0.8.3
into 0.8.2 so that the oracle report's new §4 is written once, on the final basis,
rather than twice. **OR-119** resolves review R-12 (#182) as *decided, not fixed*:
G-OR-49 was unsatisfiable while OR-93 kept the summary report ultimate, and
becomes satisfiable as written once OR-93 falls.

Four gates and two documents were found to be **passing while wrong**, which is
the substance of this step beyond the arithmetic. The oracle technical report was
printing 1.5× Appendix A's figures — the oracle tests compare at calc level and
never cross the render boundary — against a document whose purpose is to be read
against p131. Seven deck comments asserted their cards were ultimate over LIMIT
numbers, two of them printing a `1.5 ×` derivation for a sum that no longer had
it. Appendix A's bundle manifest had called the per-module CSVs ULTIMATE since
note 48, because its guard pins prose against a hand-written map and so detects
drift between the two rather than falsehood in the pair. And
`test_ultimate_markers_and_sf_columns_are_present` passed on the methods stamp's
*explanation* of the `-ULT` marker rather than on any marked cell.

The first version of G-OR-73 shared that weakness: it matched one phrasing and
missed two live sites saying the same thing in other words. It now scans a list
of spellings — a gate that catches one phrasing of a false statement licenses
every other phrasing. Following CLAUDE.md practice 4, the same generalisation
produced `test_every_test_a_standard_doc_cites_exists`, after two conformance
rows were found naming tests renamed by this milestone; it immediately found
three more dead citations and one live defect, a broken zero-dependency
self-runner in `tests/test_data_dictionary.py`.
