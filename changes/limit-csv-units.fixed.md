- **Analysis-page LIMIT CSVs follow the unit toggle and label their units (L-8i,
  backlog Pri 3, tier S, 2026-08-16).** The Wing/Fuselage/Tail Loads pages built
  their LIMIT download inline from the raw Imperial row dicts, so an SI session
  downloaded Imperial numbers under unit-less headers while the table above was
  converted — the units-defect class M4-20 already paid for. New `app/limit_csv.py`
  is the one owner per page of the column→unit map, the display conversion and the
  unit-suffixed header (`Fz (lbf)`/`Fz (N)`, `Mxx (lb-in)`/`Mxx (N·m)`, tail
  `PSI(Xn) (psi, LIMIT)`/`(kPa, LIMIT)`), and feeds **both** the on-screen table and
  the download so they cannot disagree; the two hand-authored tail header sets
  collapse into one. Decisions: map stays per page (the row builders return
  pre-formatted strings with no quantity kind); units in the headers and basis in
  the `Basis` column / `*_LIMIT.csv` filename, **no** `units_statement` line — the
  LIMIT analysis-page carve-out, not a deliverable (`CONVENTIONS.md` §3). On review
  `loads_plots` was already converted and labels units in its `Field` cell, so it
  is verified conformant and unchanged (the issue's "four pages" is three). The
  sbeam/export channel is untouched. Guard: `tests/test_limit_csv.py` (Imperial in
  → Imperial out, SI cells equal `to_si_scalar` of the Imperial ones, no bare load
  header in either system).
