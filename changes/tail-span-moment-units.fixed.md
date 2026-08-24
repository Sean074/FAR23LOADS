- **Tail Span Loads stated its moments in the engine's ft-lb channel — every
  figure 12x its label (C210-51, issue #86, tier S, 2026-08-24).** The module was
  never wrong: `tail_span` accumulates `sz * dy` with the span in inches and
  publishes `lb-in` on its own `LoadValue`s, which is why the oracle GUI's report
  read correctly and only the main GUI's page disagreed. But
  `app/views/tail_span_loads.py` rendered six lb-in quantities — root Mxx/Myy,
  the station table, the control-point torsion, the hinge moment (whose field is
  literally `hinge_moment_lbin`), the T-tail transfer and the station CSV —
  through the `torque` channel, whose Imperial label is **ft-lb**: Imperial
  figures read 12x their label, and SI applied the ft-lb→N·m factor to an lb-in
  number, so both systems were wrong by the same 12. Found by reading the C210
  station CSV: an htail `Mxx` of 42.857 "ft-lb" is 5.4945 lb x the 7.8 **in**
  station pitch. The page now derives one moment label and one converter from
  the `lb-in` channel its module produces — the call the wing, fuselage, landing
  and plots views already share, making this the fifth rather than the outlier.
  Guards (rule 3): no view outside the engine page may read the `torque` channel
  at all, and the page's moment label must be the unit its module publishes
  (`tests/test_deliverable_units.py`).
