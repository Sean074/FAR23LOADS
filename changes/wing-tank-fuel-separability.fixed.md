- **Wing-tank fuel no longer rides both beams — `MassItem.wing_fraction`
  (backlog Pri 6 / #6, design note 29, tier L, 2026-08-17; schema **v53**, the
  0.6.0 freeze's one hop, additive with a `0.0` default, no migration hop).**
  On `atr42_100`, `dhc8_dash8` and `concept_heavy` the wing-tank fuel sat inside
  an undivided `"Fuel to gross"` row tagged `fuselage` while WINGINER's
  `concentrated` hung the same 3,800 / 4,000 / 1,200 lb on the wing — 11.6 /
  14.5 / 7.4 % of the derived body beam, above the base-method band, so every
  body inertia load, shear, bending moment and carry-through reaction on those
  fixtures was over-stated by `n ×` those pounds while the wing deck relieved
  with them, and the assembled case carried the fuel as body inertia with no
  wing relief. A row now states the fraction of its weight (and own inertias)
  the wing reacts; the remainder stays on `component`; both parts sit at the
  row's position, so WTONECG/WTENV/`cg_cases`/every derived `CaseLoading` are
  bit-identical (they read rows). One owner, `mass_distribution.reacted_parts`,
  turns rows into parts for `distribution()`, `balance` (wing/body inertia,
  self-inertia, body-drag fallback) and the CONM2 header; a drift guard pins
  that they agree. Fixture fractions are derived from WINGINER's own entries
  (3800/9174, 4000/4660, 1200/5500 — no number invented); the per-fixture
  "unmodelled wing mass" pin is deleted and survives as the reduction gate
  (strip the fraction, exactly those pounds reappear). The wing tie is now a
  validator (`wing_mass_tie_open`, both signs, with the remedy) plus two entry
  rules (`wing_fraction_out_of_range`, `wing_fraction_on_wing_row`). Measured
  consequences, all on the three fixtures only: body beams 32,751 → 28,951 /
  27,500 → 23,500 / 16,200 → 15,000 lb; wing-inertia scale 1.898 → 3.332 /
  2.333 → 3.667 / 1.000 → 1.667; and — the one effect the note did not predict
  in size — `Izz(closure)` **+33 / +31 / +29 %** because the fuel left the
  centreline lump for WINGINER's spanwise spread, so the twins' yaw and roll
  accelerations under the same fin load fell by a quarter to a third (fin load
  and `Ny` unchanged — inertia moved, not aero). Imperial digest regenerated
  for exactly those fixtures on the body / balance / LRA channels; every wing
  deck, every CONM2 card and every other fixture byte-unchanged; Appendix A
  untouched. `dhc8_dash8`'s hand-entered station table (25,890 lb) now
  *exceeds* the derived beam by 2,390 lb — it was written with the fuel on the
  body — and is pinned as such.
