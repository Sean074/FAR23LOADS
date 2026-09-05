- **The methods statement declares every approved correction (#174, review R-3,
  tier M, 2026-09-05)** — `report/methods.APPROVED_CORRECTIONS` had drifted four
  entries behind `docs/20_theory/02_approved_corrections.md`, and its guard could
  not see it: `test_statement_lists_every_approved_correction` looped over the
  tuple and asserted each key appeared in the statement rendered from that same
  tuple, so it proved the renderer worked and nothing else — the P-2 shape, in
  the project's own vocabulary. The four missing entries (the 2026-08-17
  constants sweep, LANDLOAD #133 and #134, WINGGEOM's 2026-08-30 closed-form
  integration) are the three most recent approvals plus one, and three of them
  change figures an analyst would compare against the printed manual, so the
  omission was not cosmetic: a stamped CSV said the numbers agreed with the
  source except in three named ways, when there were seven. The tuple grows a
  third field — the register entry's own `###` heading — which never prints and
  exists solely so the guard has a non-circular key; the guard now parses the
  register, scoped to its `## Register` section, and asserts the declared
  headings equal the approved ones in the register's own order. A companion test
  reads the *Withdrawn from scope* and *Considered and declined* sections and
  asserts none of their headings is declared, closing the inverse drift, which is
  the worse one: a refused deviation advertised as approved is a false claim, not
  a silent omission. The printed reference stops meaning "FAR" — it is the
  governing paragraph where a single paragraph governs and the source program
  otherwise (owner ruling, 2026-09-05), because `WINGGEOM` and `CONSTANTS`
  deviate from no regulation and the LANDLOAD pair span 23.479–23.493; the report
  table's column follows, `FAR` → `Reference`. No calc changes and no schema hop;
  `sloads/report/methods.py` is not in the note 44 OR-13 frozen manifest, so no
  OR-15 admission was needed. `SUMMARY_REPORT.md` §4.4 carries the completeness
  contract and the reference rule.
