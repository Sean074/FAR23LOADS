- **The oracle GUI's project is the project gate G5 tests (#62, review
  2026-08-22 PB-1/2/3, tier M, 2026-08-23)** — G5 compared a reduced copy of
  each example against the full one, and the reduction kept three things it
  claimed to drop: the stored result slices, the records the oracle GUI never
  creates, and everything the station tables show. So a stored `Project.mass`
  carried every gate while no oracle page wrote one (a fresh twin dead-ended
  at One Engine Out), the turbine rotors rode inside "the oracle input set"
  (−16 % twin mount torque unseen), and the fuselage table's dependence on
  `component`/`wing_fraction` was invisible because nothing compared it. The
  design call was the shape of the mass slice: **derive at persist through one
  owner** (`sloads/derived.py`) rather than derive-on-read (a stored cache
  beside its source) or an Apply button (the one button on fourteen
  per-keystroke pages) — chosen because it keeps the slice's schema and ✅
  semantics, makes the `app/` Apply and the oracle persist the same call, and
  lets the reduction re-derive what the GUI writes, which is the reduction's
  definition. The rotors were the second call: **declared value divergence**
  per example, not a widget for data the original never took. The gate got a
  second leg, the typed-from-blank journey under `AppTest`, compared against
  the reduced key so the divergence is stated once; it passed only after the
  shell stopped rounding widget seeds to four decimals, which had made every
  fifth-decimal input (`zcg` 90.73001) read back as a different number. Two
  shipped examples turned out to store a mass slice one ulp off their own
  items — the class the drift guard now holds bit-identical.
