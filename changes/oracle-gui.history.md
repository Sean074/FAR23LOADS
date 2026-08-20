- **The oracle GUI, and what "derived" had to mean to be worth claiming (design note 32 step OG-D, tier M, 2026-08-20)** —
  Note 32's estimate for OG-D was ~600–800 LOC of new front-end. It came in near
  the bottom of that, and the reason is the three steps before it: OG-B gave the
  second GUI a shell to share, OG-C gave it a registry that already knew which
  page edits every field, and G5 proved the reduced input set was real. What was
  left was a renderer, and the interesting decisions were all about how hard to
  push "derived". Two went further than the note asked. First, **there are no
  page files.** The obvious shape is `oracle_app/views/<key>.py` per page,
  fourteen three-line files, matching `app/`; but gate G2 says adding a `bas` to
  a workflow step adds a page *with no GUI edit*, and fourteen files is a
  hand-maintained page list wearing a different hat — it would satisfy a test
  that checked the list was right and fail the one that matters. So a page is
  `st.Page(callable)` bound to a step key, and the guard asserts that **no
  workflow step key appears as a string literal anywhere in the GUI**. Second,
  the same argument one level down: a page's *content* is not written either. It
  is the registry rows for that step, grouped by record, with each widget's shape
  from the resolved annotation, its unit from the schema's three-way unit
  classification, and its help text from the row's own `basis` — which gives the
  oracle GUI a property the full app does not have, that every field on screen
  can name the `.BAS` program that asked for it.
  The cost of that is one honest concession, and it is worth naming precisely
  because the temptation is to hide it. A generic renderer cannot know that a
  `Tuple[float, float]` is a gear axle's (X, Z) here and a planform corner's
  (X, Y) there; the type carries no such thing. So the member labels are
  hand-declared — presentation only, never data — and a guard fails if a
  composite field in the input set is missing from the table, so a new one
  cannot quietly render as "1, 2". Everything else is derived, and the line
  between the two is a test rather than a good intention.
  Three things fell out of building it. `field_registry.field_at` could read a
  field's default but not its *type*, because `Field.type` is a string under
  postponed annotations — hence `field_type`, which the renderer builds every
  widget from. `units` needed a `moment` input kind for the one entered lb-in
  quantity, distinct from the engine channel's ft-lb `torque`. And the browser
  found what 2,273 green tests could not: `oracle_app` is an installed package,
  the editable install had not been refreshed, and the entry point could not
  import its own renderer — invisible to pytest, which puts the repo root on
  `sys.path` anyway. The suite was right about the code and wrong about the
  environment, which is the standing argument for opening the thing before
  calling it shipped.
  The lint gate was swept for the second time in two days — `app_shell/` cost
  nine hand edits, `oracle_app/` eleven — so it is now guarded from both ends:
  every derived GUI directory must be in CI's ruff command, and every one of the
  eleven documents and scripts that repeats that command must repeat it exactly,
  with CI as the authority.
