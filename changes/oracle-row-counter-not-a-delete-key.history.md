- **A row counter that deleted, and a row that stopped the calc (code review
  2026-08-24, tier M)** — The 0.7.2 code review of `oracle_app/` and `app_shell/`
  found the shell in good order and two live defects, both inside eight lines of
  one function. `render_table` sized a list record by reconciling the model to a
  number input, against the project's own attached list, so the widget wrote to
  the project in both directions during a render pass. Counting down popped
  entered rows — 21 of 24 weight items on one keystroke, no confirmation, no undo,
  blanks on the way back up, and a truncated project that saved — which is the
  same failure the generation stamp was built for at #51, closed there for the
  path where Streamlit's retained state caused it and left open for the path where
  the user does. The same pop also fired on a plain page revisit whenever the
  project had been mutated rather than replaced underneath the retained count, the
  case `02_parked.md` L-8d parks and #78's seed button was about to trigger.
  Counting up was the more surprising half: the seeded row joins the project
  immediately, because `commit_pending`'s blank-record rule governs records a pass
  creates and not rows appended to a list that is already attached — and for the
  CG-case table that row is a `FLIGHT`-tagged case of zero weight, which every
  balance divides by, so asking for one more row killed the entire flight envelope
  and SELECT. What made that invisible was a third thing: the results renderer
  caught `ZeroDivisionError` as *not ready yet*, so a page that had been working a
  second earlier said only that it was unfinished. The fix keeps the counter (it
  is what the journey test types projects through) but makes it non-destructive —
  the model wins, and a deletion is a named button that says which rows go — and
  puts the refusal where it belongs for every writer rather than for the GUI that
  happened to produce it: `build_envelope` names a weightless case, `validation`
  warns before anything runs, and `ZeroDivisionError` is out of the not-ready
  catch, which is the narrow half of #71. The page's caption, which had promised
  that incomplete rows are not saved, now states the rule that actually applies to
  each kind of row.
