- **Every keyed `max`/`min` pick in the package is platform-stable, and the guard
  that says so now reads the AST (review 2026-08-20 CR-B-1, tier M, 2026-08-22).**
  `CONVENTIONS.md` §7 claimed that every keyed critical-case pick went through
  `select._extreme` — first-in-order inside a `TIE_REL` relative band, so two
  candidates that tie in exact arithmetic cannot select different cases on
  different platforms. The claim was false at the worked example itself: the
  23.423(a) unchecked-manoeuvre pick over the `BAL A` points was a raw
  `(min if want_min else max)(bal_a, key=…)`, and the guard was a substring grep
  for a line containing `max(`/`min(` **and** `key=` — a construction containing
  neither, so the guard passed over a live bypass.
  The tie rule is now `sloads/picks.py::extreme`, a public single owner (it was
  private to one module while the convention it enforces is repo-wide), and the
  guard is `tests/test_platform_stability.py::test_every_keyed_pick_in_sloads_goes_through_picks_extreme`
  — an AST walk over the whole package for a built-in `min`/`max` call carrying a
  `key=` argument, matched on the callee expression so the conditional form, an
  alias, and a call spread over several lines all read the same.
  Rule 4 swept the class rather than the instance: **fourteen** call sites were
  converted, in `select`, `landing` (the gear family whose own docstring records
  that cases 19-22 share a VMP), `one_engine_out`, `weight_envelope`, `aileron`,
  `tail_span`, `rigid_body` (the Gaussian pivot row), `validation`, and the
  exporters `equilibrium`, `sbeam_bridge`, `mass_cards`, `lra_import` and
  `lra_model` — where equidistant nodes are the rule on a symmetric airplane, not
  the exception, and the pick decides which node carries a load. Four of those
  the old grep could not have seen either: they are multi-line calls. Nearest-node
  selection gained one owner (`lra_model.nearest_node`) instead of three copies.
  No delivered number moves: the whole suite, the oracles and the frozen Imperial
  digest are unchanged — `extreme` returns first-in-order, which is exactly what
  `max`/`min` already return for a bit-exact tie. §7's wording was narrowed to the
  shape the guard actually enforces, and states that a pick written as an
  accumulation loop is outside any static walk.
