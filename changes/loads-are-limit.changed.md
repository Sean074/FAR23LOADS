- **Every load sloads delivers is LIMIT — stated, never applied (design note 49,
  tier L, 2026-09-05).** The safety factor of 14 CFR 23.303 is stated against
  every case and applied nowhere: not on a module view, not in the case index,
  not in either report, not in an exported CSV, and **not in the sbeam deck**.
  `sloads` is an external-loads program; the regulation says the factor must be
  applied, not by whom, and the sizing analysis is where it is applied
  (**OR-116/OR-117**, owner's ruling, overruling note 48's OR-87 and OR-93).
  The multiply is **removed** from 81 sites across 7 files rather than
  neutralised — a `_sf()` returning 1.0 would have left dead arithmetic reading
  as if a factor were applied, which is the opposite of what the ruling is for.
- **The deck states, per subcase, the factor it did not apply (OR-117).** One
  owner for that sentence, `export.sbeam_bridge.basis_sentence`, on the wing,
  fuselage, tail-chordwise, tail-spanwise, control-surface, stick, assembled
  balanced and LRA decks. This is the obligation that **replaces** the multiply:
  until now a recipient could read the basis off the numbers, and now the
  sentence is the only thing between them and a 1.5× error.
- **`report.LoadChannel` has one member (tier L, 2026-09-05).** Note 48 built it
  as a switch and defaulted it to ULTIMATE so the frozen `oracle_app` needed no
  edit; the default inverted underneath that file, and the `ULTIMATE` member was
  **removed** so a stale caller fails at import rather than silently receiving
  limit loads. `to_ultimate` and `render._ult` are deleted. The parameter itself
  goes at #29, when `app/views/` can be edited.
- **The `-ULT` marker now means one thing: apply nothing further.** It survives
  on the two families 14 CFR prescribes already ultimate — 23.367(a)(2) sudden
  engine stoppage and 23.561(b) emergency-landing inertia — and nowhere else
  (**OR-118**), which makes it rare enough to be conspicuous. A shared column
  header is marked only when *every* case in its table is already ultimate
  (**OR-118a**); otherwise it is plain and the `SF` column carries the basis.
- **Every artifact's in-band basis statement was rewritten to match its
  contents.** ~35 statements on shipped deliverables still claimed ULTIMATE
  after the arithmetic changed: the summary report's title-page basis line, the
  compiled PDF's per-page footer, fourteen rows of Appendix A's bundle manifest,
  the oracle report's §1 paragraph and issue-package README, the workbook's
  units line on both channels, and three validation warnings.
- **Standard docs record the inverted contract.** `CONVENTIONS.md` §3 (retitled
  *"LIMIT load contract — stated, never applied"*), `CLAUDE.md`'s Phase C
  mission sentence and load-output contract, `PROGRAM_SPEC.md`'s M4-15 block,
  `SUMMARY_REPORT.md` §3.1, `ORACLE_REPORT.md` §3/§3.4,
  `00_program_overview.md`, `PROJECT_GUIDE.md`, `GUI_design.md`,
  `GUI_USER_GUIDE.md` and `theory_sources.md`.
