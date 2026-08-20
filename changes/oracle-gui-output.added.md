- **The oracle GUI computes: results, CSV and text on all fourteen pages (design note 32 step OG-E, tier M, 2026-08-20).**
  Every oracle page now runs its programs and shows what they produce, from one
  renderer — `oracle_app/results.py`, ~250 lines, no per-page output code. A
  page's programs come from `workflow.step_modules()`: the step's own `module`
  plus the contributors folded into it, which together are exactly what its
  `bas` string claims, so **Weight & Mass Properties runs all three of
  WTESTIMA+WTONECG+WTENV** and Wing Loads runs AIRLOADS, WINGINER and NETLOADS
  because `workflow.py` says so, not because the GUI names them.
  **Every file comes from an owner** (OG-6): load cases through
  `sloads.io.load_cases_csv` with `report.csv_comment_block`, the text report
  through `report.module_text_report` — the same two calls `cli.py` makes, so
  the ULT marker and the per-case SF statement are identical by construction.
  **The station tables come too.** AIRLOADS, NETLOADS and TAILDIST *print* a
  spanwise/chordwise table — it is what Appendix A is — and it lives in no
  `ModuleResult`. OG-6 is amended to name a third owner, `app_shell.limit_csv`,
  which OG-B had already extracted for exactly this channel. Those tables are
  LIMIT, the `CONVENTIONS.md` §3 analysis-page carve-out, and say so in-band
  and in a `*_LIMIT.csv` filename.
  A page whose upstream slices are missing says which ones; a program that
  cannot run says why (the error contract's `MissingInputError`/`ValueError`,
  caught as *not ready yet*, never as a blank table); and Aerodynamic Data —
  the one oracle page with no `.BAS` of its own — shows no results heading at
  all rather than an empty one.
