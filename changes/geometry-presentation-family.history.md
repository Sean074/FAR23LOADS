## Step — The geometry-page presentation family: quantity-true placement and one summary shape per module (#95, tier M, 2026-08-27)

Ten C210 findings (C210-1/2/3/5/6/8/22/25/26/27), closed as three mechanisms.
**One summary shape, both channels:** `report.summary_rows` is the single
dispatch the module CSV, the oracle results page and Results Review all render
through (`SUMMARY_SHAPES`; CONVENTIONS §7 row) — SELECT one line per case with
its per-case SF via `critical_rows`, sharing `governing_loads_table`'s
one-line core so the M2-4 tables cannot diverge; WTENV one row per
(weight, station) point via `weight_station_rows`, paired on the machine
`LoadValue.key`; every other property module the data-shaped floor
(`results_to_rows` drops all-empty columns). The owner's CSV ruling made this
an accepted deliverable-format change: only the `csv/*` Imperial digests
moved — text, sbeam and index channels are byte-identical. **Derives and
disclosures on the #97 mechanism:** SE/SR blank-derive from their own hinge
halves with a 1 %-tolerance mismatch warning (the Appendix A inputs' own
rounding is 0.2–0.7 % and stays silent); the v-tail wing span blank-derives
from the WINGGEOM integrator's span, read through `effective_vtail_inputs` by
SELECT, ONENGOUT and the tail-span split alike; the 0 → 0.09·MTOW wing-weight
and rod-IZZ fallbacks are disclosed beside their fields and the SELECT block
captions both rod inertias against WTONECG's database values (C210-25).
**Placement and seeding:** `DISPLAY_GROUPS` renders a field on the page its
quantity belongs to (the h-tail record's wing aero with the aero data, the
SELECT trio each to its home) without moving it off its record;
`RECORD_SEEDS` offers the parametric wing from a typed planform behind a
button (GR-GEOM-3 — seeded and overridable, a visit never dirties the
project); `fuselage_length` renders disabled exactly while an outline exists.
Guards: `tests/test_summary_shapes.py` (10 tests, incl. the screen-equals-CSV
drift guards) plus the extended select/validation/configuration/registry
suites; the G7 CSV gate now requires the SF column exactly where a `-ULT`
column exists, since the always-blank SF on property tables was C210-27's own
complaint.
