- **Thirty-four project fields showed the wrong number in the SI view, and the guard that should have caught them could not see them (tier M, 2026-08-19).**
  `sloads.units` classifies a schema field by **name**, and the drift guard
  decided which names to demand a classification for from a **suffix regex** —
  `_lb`, `_in`, `_sqft`, `_hp`, `torque`, `inertia`, `psi`. A quantity whose name
  does not follow that convention was therefore invisible to the guard rather
  than reported by it. Thirty-four were: on one record the SI view showed
  `htail_semispan_in` as **1856.7 mm** and `xt25` — an inch station beside it —
  as **261.0**, and `weight.envelope.gross_weight` displayed 3400 lb as
  **3400 kg**. The rest are the unsuffixed stations and waterlines (`xt50`,
  `xv25`, `xv50`, `xtc`, `xtf`, `xw`, `zw`, `mac`, `xlemac`, `datum_x`,
  `le_root_x`, `h_tail_z`, the three `*_waterline*`, `inboard_rib_y`, the
  fuselage-section `width`/`height`/`z_centre`, `fuselage_nose_x`/`_tail_x`, the
  parametric `fuselage_length`/`width`/`height`), the gear `axle_*` points and
  the engine-mount `attach` vector, `fwd_regardless_weight`, `izz_slugft2` and
  `unbal_moment`. All are now classified, and the wing planform's
  `leading_edge`/`trailing_edge` polylines convert too — through a new
  per-member rule, because a `[[a, b], …]` curve is not one quantity twice: the
  planform edges are (station, station) and convert on both members, while
  `twist`, `profile_drag` and `section_cm` are (station, coefficient) and
  convert on the first only. Nothing in the calc, in `project.json` or in any
  oracle moves — the affected path is the Project JSON Editor's SI display,
  which was unconverted in both directions and so round-tripped perfectly while
  showing the wrong number.
  **The guard now runs the other way round:** every *numeric* schema leaf must
  be classified — converted, aviation-standard, or dimensionless with a stated
  reason — and a new one fails until somebody decides which
  (`units.field_classification`, the same totality standard gate G4 holds the
  field registry's 323 rows to). Two smaller holes closed with it: the
  aviation-standard airspeed/altitude fields are now **declared**
  (`units.AVIATION_STANDARD`) rather than implied by absence, so *stated in
  KEAS* and *forgotten* stop looking identical; and the guard's field set comes
  from `field_registry.schema_paths()` instead of one example project's slices,
  which had left every field of `one_engine_out` (absent from `ga6_normal`) and
  of `tail_mass` (set by no shipped example) outside it entirely.
