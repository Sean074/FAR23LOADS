- **Selector names and coded inputs have one owner (#63, review 2026-08-22
  PB-5/8/9, tier M, 2026-08-23)** — the replication carries as *names* what
  the original suite carried by position, and those names are dictionary
  keys downstream; the oracle form seeded them blank and checked nothing, so
  the most ordinary from-scratch mistake (leave the seed) changed tail loads
  with the page reporting success. The fix is structural rather than a
  warning: `keyed` refuses a duplicate wherever `select.py` looks a name up,
  the form withholds results on the same check, and a new row is named
  before the user sees it. Name identity became one rule (`same_name`), which
  is also what let `Wing` find the wing. The two coded `str` fields got the
  same treatment as the safety-factor table — a code the owner cannot
  classify is refused by name, never defaulted — with the tables moved out of
  an `app/` view's private dictionary into the models so both GUIs offer one
  list. `strut` stays a `str` (an enum is a schema hop; not this pass).
