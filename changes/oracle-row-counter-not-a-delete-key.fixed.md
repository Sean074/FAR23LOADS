- **The oracle GUI's row counter was a delete key, and the row it added broke the
  page it was added on (code review 2026-08-24, tier M).** `render_table` sized a
  list record by reconciling the model to a `st.number_input`, and `rows` is the
  project's **own attached list** — so both directions wrote to the project during
  a render pass. Counting down ran `rows.pop()`: typing `3` on the Weight & Mass
  page dropped 21 of 24 weight items with no confirmation and no undo, counting
  back up returned blanks, and a project truncated that way saved to disk. That is
  the scenario `app_shell/widget_keys.py` records as the reason the generation
  stamp exists (#51, which blocked the 0.7.0 cut) — the stamp closed the
  state-triggered path and left the user-triggered one open. The mass item
  database is the D-25b mass SSOT, so the loss reaches `Project.mass`, the CG
  cases, SELECT's inertias, the fuselage beam and every exported deck.
- **The same pop fired with no user interaction at all.** A retained count beats
  the model whenever the project is *mutated* rather than *replaced* — no
  generation bump covers that, which is exactly the remainder `02_parked.md` L-8d
  parks. Six items added by another writer vanished on the next render of the
  page. Latent today (nothing in the oracle GUI grows a registry list) and not
  latent for long: #78's item-table seeding is such a writer.
- **The model wins now, and deleting is a named click.** The counter still grows
  the list; counting down deletes nothing and instead says so, naming the rows at
  risk, with a `🗑 Delete the last N row(s)` button beside it. The counter was
  kept rather than replaced with an Add button on purpose: `tests/test_oracle_journey.py`
  types whole projects by setting widget values, and a button would have cost that
  harness for no gain in the defect.
- **A blank row is in the project at once, and one of them stops the calc.** The
  counter attaches a seeded row immediately — `commit_pending`'s blank-record rule
  (OG-F) governs records the pass *created*, not rows appended to an already
  attached list. For `weight.cg_cases` the seeded row is a `FLIGHT`-tagged case of
  zero weight at station 0, which `flight_cases` picks up and every balance
  divides by: the whole Flight Envelope and SELECT died on `ZeroDivisionError`
  one click after being asked for one more row. `build_envelope` now refuses a
  weightless case **by name** (the #81/#84 shape — the point that divides is the
  point that refuses), and `validation` warns before anything is run
  (`cg_case_without_weight`, page `weight_mass`).
- **The page said the opposite of what it did.** Its caption read *"Table rows with
  an empty cell are not saved — fill every column to keep the row."* True of grid
  cells (`_cell_in`'s NaN guard) and false of counter rows, which are saved blank.
  The caption now states both rules, so a user reading it is not told the tool
  protects them from the state it just created.
- **The catch that hid all of it (#71/PB-18, narrow half).** `_NOT_READY` included
  `ZeroDivisionError`, which is not a `ValueError`, is raised deliberately by no
  module, and never means "keep typing" — so a page that had been working reported
  *cannot run yet*, the sentence for an unfinished form. It is gone; the contract's
  own two halves (`MissingInputError`, `ValueError` for present-but-unusable)
  stay, because narrowing further breaks the documented contract — `torque_factor`
  raises a bare `ValueError` for a missing cylinder count, which the journey test
  caught immediately. The rest of #71 (exception type + expandable traceback,
  C210-24) stays with #73.
