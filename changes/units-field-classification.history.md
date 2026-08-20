- **The units table's blind spot, found by asking it a question it had never been asked (tier M, 2026-08-19)** —
  Design note 32's step OG-D needs a **generic** form renderer: one piece of code
  that, given any of the 230 fields in the oracle GUI's input set, produces a
  widget. That forces a question no hand-written view ever had to ask, because
  every existing call site answers it by hand at the call site — *what unit does
  this field carry?* Sizing the renderer against `sloads.units` turned up
  thirty-four fields it could not answer for, and the reason is worth recording
  because it is a property of the guard, not of the table. `_PROJECT_FIELD_KIND`
  is keyed by field name, and its drift guard decided **which names to demand an
  answer for** from a suffix regex over `_lb`/`_in`/`_sqft`/`_hp`/`torque`/
  `inertia`/`psi`. So the guard's reach was exactly the set of fields that follow
  the naming convention, and a length called `xt25` was not *missed* by it — it
  was outside the question. In the SI view that field sat at 261.0 next to
  `htail_semispan_in` correctly showing 1856.7 mm, on the same record, and
  `gross_weight` showed 3400 lb as 3400 kg. Unconverted in both directions, so
  the round-trip test was green and the numbers on screen were wrong.
  The fix is the inversion: **every numeric leaf is classified**, one of three
  ways — converted, aviation-standard, or dimensionless with a stated reason —
  and `units.field_classification` is the one place that answers. That is the
  same totality standard gate G4 already holds the field registry's 323 rows to,
  and the argument for it is the same: a guard that decides for itself what is
  worth checking can only find what somebody already thought of. Two further
  things fell out of building it. The `[[a, b], …]` curve fields needed a shape
  the table could not express — one kind per field would have multiplied a
  profile-drag coefficient by 25.4 — so a pair carries a kind **per member**,
  which is what lets the wing planform polylines convert (both members are
  stations) while `twist`, `profile_drag` and `section_cm` convert on the first
  only. And the guard's own field set was one example project's slice list,
  which meant a single-engine fixture's missing `one_engine_out` slice, and
  `tail_mass` that no example sets, were not merely unclassified but unreachable
  by the check; it now reads `field_registry.schema_paths()`, the schema-walk
  owner. The order matters more than the count: this was found *before* the
  renderer was written rather than by shipping it into a second GUI, which is
  the same lesson G5 recorded a day earlier — a classification that changes a
  delivered number is settled by running it.
