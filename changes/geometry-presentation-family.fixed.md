- **The geometry-page presentation family, and one summary-table shape per
  module (tier M, 2026-08-27, #95; C210-1/2/3/5/6/8/22/25/26/27).** The
  C210 build's placement/duplication findings closed as mechanisms, not
  patches. **Tables (owner directive, "one line per case"):**
  `report.summary_rows` is now the one dispatch every summary channel renders
  through — the module CSV (`io.load_cases_csv`), the oracle results page and
  the main GUI's Results Review — so the screen and the CSV are the same rows
  by construction. SELECT renders one row per condition with its per-case SF
  (`report.critical_rows`, sharing `governing_loads_table`'s one-line core;
  the oracle page groups the rows per component), replacing the stacked
  ~150-row shape whose SF column was blank on every wing case; WTENV renders
  one row per (weight, station) point (`report.weight_station_rows` — the
  envelope vertices, CG-limit corners and summary weights fold from stacked
  pairs); every other non-load-case module gets the data-shaped floor
  (`results_to_rows` drops all-empty columns). **Accepted deliverable-format
  change: the frozen Imperial `csv/*` digests moved with it — every other
  channel (text, sbeam decks, case index, gear report) is byte-identical.**
  **Derives (the #97 mechanism, extended):** a blank elevator/rudder area
  derives as the sum of its own hinge halves (`select.derived_elevator_area` /
  `derived_rudder_area`; a >1 % typed disagreement warns,
  `elevator_area_mismatch`/`rudder_area_mismatch` — Appendix A's own rounding
  sits at 0.2–0.7 % and stays silent) and a blank v-tail `wing_span_in` from
  the WINGGEOM planform's own span (`select.effective_vtail_inputs`; ONENGOUT
  and the tail-span control split read through it, rule 4). The undisclosed
  fallbacks are disclosed: `wing_weight_lb`'s 0 → 0.09·MTOW and the side-gust
  rod IZZ (`select.default_side_gust_izz`) render beside their fields, and the
  SELECT block captions both rod inertias against WTONECG's database values
  (C210-25: +34 %/+49 % on the C210). **Placement:**
  `field_registry.DISPLAY_GROUPS` renders a field on the page its *quantity*
  belongs to — the h-tail record's wing-aero fields (ARW, AW, the IW angles)
  with the aero data, SELECT's section cm with the aero data, the aileron
  travel with the aileron record, the wing weight with the weight data.
  **Geometry:** the parametric wing seeds from a typed `wing` planform behind
  a button (`configuration.parametric_wing_seed` via
  `field_registry.RECORD_SEEDS` — GR-GEOM-3, seeded and overridable), and
  `fuselage_length` renders disabled exactly while the outline it summarises
  exists. New CONVENTIONS §7 SSOT row; guards in
  `tests/test_summary_shapes.py` and the extended registry/select/validation
  suites.
