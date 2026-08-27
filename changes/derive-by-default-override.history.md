## Step — Derive-by-default overrides: one mechanism for the duplicated-input class (#97, design note 36, tier L, 2026-08-27)

**Objective.** Close the eight C210 findings that were one defect class — an
input duplicating a value the project already holds, asked blank, with a silent
fallback or a silent skew behind it (C210-13/15/29-seed/31/36/38/39/41) — with
**one mechanism** instead of eight patches: falsy-means-derive /
typed-means-override at **calc level** (a blank field in any project file
derives, CLI and GUI alike — owner ruling), one named resolver per quantity,
the computed value shown beside each collapsed field, and a drift guard that
makes the mechanism the single-source owner rather than a convention
(design note `docs/30_future/36_derive_override_note.md`, agreed 2026-08-26;
decisions OV-1…OV-12, gates G-OV-1…G-OV-6).

**Deliverables.**
- **The resolvers (OV-2), each a pre-existing owned computation** — no new
  physics: `derived_geometry.planform_aspect_ratio` (the one AR spelling,
  OV-5; both strip sweeps now call it) with `wing_aspect_ratio(project)` for
  the h-tail's blank ARW; `taper_ratio_from_planform` /
  `tip_ratio_from_planform` feeding `airloads.resolved_tau` (the TAU
  resolution spelled once); `flight_envelope.gust_at_vf` (the GUST VF corner
  factor, same `_gust_load_factor`/`_gust_ude` internals — bit-for-bit) read
  by `flap.resolved_ng`; `select.wing_lift_slope_per_rad` (cruise C1 × 57.3),
  `select.effective_tail_inputs` and `select.resolved_full_down_aileron_deg`;
  `engine.effective_engine`/`resolved_engines` (LIMNZ ← `design_speed_values
  (project).n`; weight/CG ← the `engine_mass_item`/`prop_mass_item` row,
  matched with `same_name`, refused by name when absent — every engine
  consumer swept onto the one accessor: mount loads, LRA export, WINGGEOM
  stations, nacelle sketch, OEI, hub thrust, applicability); WTENV's
  `gross_weight or max_takeoff_weight(project)` (recursion-safe: the G-14
  reverse fallback reads the raw field only when non-zero); and
  `airloads.resolve_aero_surfaces` (a schema-default aero row per unpaired
  **symmetric** planform, per name, nothing written to the project — OV-8).
- **Schema v56 (OV-10):** additive `SurfaceInput.tip_cap_width_in` (OV-4 —
  the rounding the polylines cannot carry, entered once with the wing) and the
  two engine selectors; 55→56 **identity hop** (`migrations._hop_55`), floor
  55, examples re-stamped, fields hash updated, `DATA_DICTIONARY` regenerated.
- **Registry + GUI (OV-9/OV-11):** `field_registry.COLLAPSED_OVERRIDES` — the
  collapsed set enumerated once — with `derived_from` + a record-aware
  resolver in `EXTERNAL_VALUES` per path; `oracle_app.form._collapsed_note`
  renders "Blank — derives from ⟨owner⟩ (currently X)" / the override caption
  with a > 1e-9 disagreement warning, never disabled; the stall-CL rows
  register `normalize()`'s shipped fill-through (OV-3, C210-15 ruling text;
  `flaps_down.neg_stall_cl` stays the documented #81 gap).
- **Mismatch surfaced (G-OV-6):** `validation._check_derive_overrides` —
  `aileron_deflection_mismatch`, `engine_mass_row_mismatch` (> 1e-6, the
  consistency channel); the no-such-row refusal lives in
  `engine.selected_mass_row`.

**Test / Acceptance.** `tests/test_derive_override.py` (23 tests): G-OV-2
derive-equals-owner on ga6 with each field blanked in turn (rel 1e-9; NG and
LIMNZ exact — same call); G-OV-3 the defect dies, each test stating the
pre-fix failure (τ 0.206209 on a tapered wing, the bare ARW
`ZeroDivisionError`, the zeroed mount loads, the never-analysed surface);
G-OV-4 the OV-11 drift guard (every collapsed path linked and resolvable, no
owned-quantity copy without its link); G-OV-5 v56 round-trip + the v55 hop
(`test_migrations.py::test_a_v55_file_loads_through_the_identity_hop_unchanged`);
G-OV-6 the two warning codes and the by-name refusal. **G-OV-1:** the full
suite (2,918 tests) passes with every Appendix A oracle and twin closure
untouched; the only digest movement is `csv/airloads`/`txt/airloads` on the
four fixtures carrying unpaired htail/vtail planforms — the OV-8 seed
appending their spanwise views, wing blocks byte-identical (OV-12: where a
blank used to produce a silently wrong number, the number changing to the
derived one *is* the fix).

**Key decisions.** All owner-ruled in note 36: calc-level derivation, not a
GUI affordance (OV-1, no 0.0→None migrations — a falsy authored value is never
load-bearing in scope); the engine↔mass linkage as an explicit row selector,
never a role tag (OV-7); seeded aero rows carry geometry values only (OV-8;
#98's caption owes the visibility); the main GUI needs no change for
correctness — the calc derives for both front-ends — with caption parity
recorded against #29 (OV-9); `wing_weight_lb` and the SELECT copies (C210-22/
25) stay at #95 and wire onto this mechanism when that row lands.
