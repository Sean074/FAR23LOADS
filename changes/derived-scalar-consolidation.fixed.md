- **One owner per quantity, in the dataclasses: ten derived copies removed from
  the `Project` slices (note 33 DS-1…DS-7, review 2026-08-20 CR-A-2, tier L,
  2026-08-21).** Ten quantities were enterable in two or more places at once.
  Seven of the copies were never a second *input* at all — they were a cache of
  `Project.geometry`, filled on every run by `sync_geometry_derived` and
  deliberately never serialized — but because they were public dataclass fields
  the registry listed them, and both GUIs offered a second editable widget for a
  number the planform owns. They are gone: `FlightLoadsInput.mac`/
  `wing_area_sqft`/`xw`/`zw`, `WingMassInput.dihedral_deg`/`wrp_waterline`, and
  `LandingInput.main_gear`/`nose_gear`/`tread_in`/`wing_area_sqft`. Their values
  are resolved where they are used, by `derived_geometry.require_wing_reference`
  (or the tolerant `wing_reference` where the caller degrades rather than
  refuses), `derived_geometry.wing_plane`, and `landing.gear_geometry`. Functions
  that were handed a bare `SurfaceInput` and so could not look the parametric
  wing up now take the two wing-plane scalars as arguments — the shape
  `air_load_distribution` already used. **No schema hop and no
  `SCHEMA_VERSION` bump:** none of the ten was ever written to `project.json`,
  checked against all six shipped examples rather than assumed. The registry is
  down from 323 rows to 299 and from ten multi-copy quantities to four, the four
  being two genuine overrides and two entered-twice pairs that need a schema hop
  to remove and are filed rather than smuggled in. Guards: gate DG-2 asserts the
  surviving four **by name**, so removing one duplicate cannot mask another
  arriving; gate DG-3 asserts no module integrates the wing planform behind the
  resolver's back (checked against a deliberate violation), plus a numeric check
  that the two modules keeping their own area accessor agree on every fixture.
  Every Appendix A oracle passes unchanged.
