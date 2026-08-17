- **`atr42_100`/`dhc8_dash8` are T-tails, and are now modelled as such
  (backlog Pri 1, from T-8a, tier M, 2026-08-16).** Both fixtures set
  `tail_type: t_tail` (their own `xt25`/`xv25` were the tell); the fin root
  stays on the outline datum (`h_tail_z` left `0`, so the just-closed
  fuselage-top branch governs: atr42 191.2 in, dhc8 203.5 in — unchanged), and
  the horizontal tail now attaches at the fin tip. Consequences in the
  deliverables: every fin case on both airplanes carries the **T7 tip
  transfer** (the concurrent balancing h-tail load plus h-tail inertia at the
  fin's last `GRID` — a load that was missing, not merely absent), the h-tail
  beam has the single fin-tip joint instead of a fuselage-side pair, and the
  LRA model ties the h-tail centreline to the fin tip. Two same-class sweeps
  (rule 4): the h-tail's **stations sit on the fin tip** on any T-tail
  (`tail_span._h_tail_waterline` read the wing root waterline regardless of
  layout — 146–180 in low on every T-tail fixture including
  `concept_regional_jet`; no load moves, the h-tail carries `fz` only, but the
  `GRID`s and the fin-tip joint were at the wrong waterline), and the
  three-view's defaulted T-tail/cruciform h-tail is drawn on the *resolved*
  fin (`fin_root + span`) instead of `fuselage_height/2 + span` above the wing
  root (32 in apart on atr42). Also rides this digest wave: the tail-span CSV
  `Fax`/`Sax` columns no longer print `-0.00` (a negated zero by construction,
  180 rows per h-tail CSV on every fixture) — the `-0.000000E+00` card half of
  the old Pri 13 was already closed by `_fmt3`. Imperial digest regenerated for
  the two twins' tail/balanced/LRA channels and `concept_regional_jet`'s
  h-tail/LRA channels; the negative-zero guard
  (`test_export_equilibrium.py::test_the_body_deliverables_never_render_a_negative_zero`)
  now covers the tail-span decks; the two tests that used atr42 as the
  conventional-with-outline example run on `cessna_210` / a reset layout.
