- **One input-field registry: where each field is edited, and where it came from (design note 32 step OG-C, tier M, 2026-08-19).**
  `sloads/field_registry.py` classifies all **323** input fields of `Project`
  with six columns — `path │ slice │ editing page │ origin │ quantity │ owner` —
  replacing the two separate tables OG-14 merged: OG-5's field-*origin* registry
  and the 2026-08-16 GUI review's field-*ownership* registry (GR-INPUT-2 /
  GR-GEOM-2 / GR-GEOM-4). **207 fields (64 %) are `ORIGINAL`** — an input of a
  named `.BAS` program, so the oracle GUI must offer it — and **116 (36 %) are
  `SLOADS`**, capability this replication added. Every row cites what settles its
  origin: the `.BAS` variable carried over at porting time (`SAAFT`, `DELTA`,
  `NG`, `D0..D4`, `ENGWT`, `TREAD`), the `PROGRAM_SPEC.md` line restating UG
  Table 2.2, or the sloads step that introduced the field (Step C5/D5/E1/G1/G4,
  F25-2, L-7, plan 09, decision D-25). Gate **G4** (`tests/test_field_registry.py`)
  asserts totality in both directions against a type-based walk of the schema, so
  a new field in `models/inputs.py` fails the build until it is classified — the
  classification is a decision, not a default. The registry also closes the
  review's duplicate-owner class: **18 quantities are stored on more than one
  field**, each with one declared owner (or an explicit external one — "engine
  count" is `len(Project.engines)`, "engine mass" the weight database), including
  all five instances the review found by hand plus a sixth,
  `speeds.shoulder_altitude_ft` against `speeds.mach_limit.shoulder_altitude_ft`.
  `docs/generate_data_dict.py` now takes its per-field owning page from the
  registry and its own `PAGE_OVERRIDES` table is deleted.
