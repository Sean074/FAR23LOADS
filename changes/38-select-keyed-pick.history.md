- **The keyed-pick convention got a real owner and a real guard (defect, tier M,
  2026-08-22)** — review 2026-08-20 CR-B-1 found the `CONVENTIONS.md` §7
  platform-stability row asserting something untrue of the very line its owner's
  docstring used as the worked example: SELECT's 23.423(a) `BAL A` pick was a raw
  `(min if want_min else max)(…, key=…)`, and the row's guard — a substring grep
  for `max(`/`min(` on a line with `key=` — matched neither spelling, so it passed
  with the invariant broken. The fix took the general form rather than the
  instance: `_extreme` moved out of `sloads/modules/select.py` into
  `sloads/picks.py` as the public `extreme`, because a convention that governs the
  whole package cannot be owned by a private function inside one FAR23 module; the
  grep became an AST walk over `sloads/` matching on the *callee expression*, so
  the conditional form, an aliased builtin and a multi-line call all read alike;
  and rule 4 swept every sibling — fourteen sites across nine calc modules and five
  exporters, including nearest-node picks on a symmetric airplane (ties by
  construction), the Gaussian pivot row in `rigid_body`, and the case named in a
  shipped validation warning. The walk immediately earned itself: four of the
  fourteen were multi-line calls that the old grep could not have seen either.
  Nothing numeric moved — `extreme` returns first-in-order, which is what
  `max`/`min` already return for a bit-exact tie, so the oracles and the frozen
  Imperial digest were untouched and the acceptance rule agreed for this item (any
  movement stops the change and is filed as its own finding) never fired. §7's
  wording was narrowed to exactly what the guard enforces and now says outright
  that a pick written as an accumulation loop is beyond a static walk's reach — the
  repo's own §4 lesson, that a gate which does not read the shipped artefact rots
  the first time the code grows past the shape the gate assumed, applied to the
  gate's *wording* as well as its mechanism.
