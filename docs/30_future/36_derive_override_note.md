# One derive-by-default override mechanism for the duplicated inputs

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: AGREED 2026-08-26 (owner, in session — `CLAUDE.md` rule 1's
working-alone path). Milestone: 0.8.0, issue #97 (tier L — the tip-cap and
engine-selector schema fields make it a schema change). Agreed as drafted;
nothing below is built yet.** Owner rulings
already taken (in session, 2026-08-26): the derivation lives at **calc
level** (a blank field in any project file derives, CLI and GUI alike); the
engine↔mass linkage is an **explicit row selector on `EngineInput`**, not a
role tag; seeded `aero.surfaces` rows carry **geometry values only**; and the
step is tier L with this note agreed before code.

**Scope.** Eight C210 findings, one defect class: an input that duplicates a
value the project already holds, asked blank, with a silent fallback or a
silent skew behind it — C210-13 (WTENV's four copies + `gross_weight`),
C210-15 (per-set stall CLs), C210-31 (taper/tip ratio, **owner directive**),
C210-36 (h-tail's `aspect_ratio_wing` / `wing_lift_slope_per_rad`), C210-38
(`full_down_aileron_deg` on two pages), C210-39 (`gust_load_factor` the
envelope already computes, **owner directive**), C210-41 step 2 (engine
weight/CG/LIMNZ, **owner directive**; step 1's captions shipped at #69), and
the seed half of C210-29 (empty `aero.surfaces`, split from #98). The
deliverable is one mechanism serving all of them — blank derives from the
owner, a typed value overrides, the computed value shows beside the field
(the C210-15 ruling) — plus the registry `derived_from` link naming each
owner and a drift guard (rule 3: the mechanism *is* the single-source
owner). `wing_weight_lb` and the SELECT copies (C210-22/25) stay at #95 and
**wire onto this mechanism** when that row lands; MAC/XLEMAC resolution is
already single-sourced (#80).

Sources reviewed (verified 2026-08-26): `sloads/derived_geometry.py`
(`mac_reference`, `wing_reference`), `sloads/modules/weight_envelope.py`
(`_fuselage_extent`), `sloads/cg_cases.py` (`max_takeoff_weight`,
`_MTOW_FALLBACKS`), `sloads/models/inputs.py` (`AeroCoefficientsInput.
normalize`, `AeroSurfaceInput`, `SurfaceInput`, `TailLoadsInput`,
`SelectInput`, `AileronLoadsInput`, `FlapLoadsInput`, `EngineInput`,
`MassItem`), `sloads/modules/airloads.py` (`_tau`, `schrenk_distribution`),
`sloads/modules/select.py` (`:367`, `:580`, `:840`),
`sloads/modules/flight_envelope.py` (`_gust_load_factor`, `_gust_ude`,
`_flap_config_points`), `sloads/vn_diagram.py`, `sloads/modules/
structural_speeds.py` (`design_speed_values`), `sloads/field_registry.py`
(`FieldEntry.derived_from`, `EXTERNAL`, `EXTERNAL_VALUES`),
`oracle_app/form.py` (`_copy_note`, `_external_note`, `_offer_clear`),
`sloads/migrations.py`, `sloads/io.py:project_from_dict`. Theory: the
derivations are existing owned computations (WINGGEOM planform integrals,
the 23.345(b) gust chain, the 23.337 limit, Perkins & Hage Eq 5-23's ARW
role) — no new physics.

---

## 1. What exists today (verified inventory, 2026-08-26)

| Finding | Field(s) (default) | Fallback today | The gap |
|---|---|---|---|
| C210-13 | `envelope.mac`/`xlemac` (`None`) | **already None-means-derive** via `derived_geometry.mac_reference` (`"override"`/`"planform"` source) | `mac` registered EXTERNAL, `xlemac` a plain row — half-marked; nothing shown on the page |
| C210-13 | `envelope.fuselage_nose_x`/`tail_x` (`None`) | already derives from the outline (`_fuselage_extent`, **all-or-nothing pair**) | plain registry rows, nothing shown |
| C210-13 | `envelope.gross_weight` (0.0) | **reverse only**: MTOW falls back *to* it (`_MTOW_FALLBACKS`); a 0 makes WTENV report 0 | no derive; disagreement only warned (`validation.py:1062`) |
| C210-15 | per-set `stall_cl`/`neg_stall_cl` (0.0) | bidirectional fill-through already exists (`normalize()`, falsy-means-missing) | shown as peer inputs; plain registry rows; `flaps_down.neg_stall_cl` gap documented, unchanged |
| C210-31 | `aero.surfaces[].taper_ratio`/`tip_ratio` (0.0) | none — 0 hits the square-tip knot: τ = **0.206209**, the pointed-wing maximum | taper derivable from the polyline chords; **tip_ratio is not derivable** — the polylines end square by construction |
| C210-36 | `htail.aspect_ratio_wing`/`wing_lift_slope_per_rad` (0.0) | none — `select.py:367` divides by ARW unguarded | wing AR computed twice already (`wing_geometry.py:135`, `airloads.py:210`), owned nowhere; AW = the aero C1 per-degree × 57.3 |
| C210-38 | `select.full_down_aileron_deg` (0.0) vs `aileron_loads.down_deflection_deg` (0.0) | none; no cross-check | same quantity, two pages, skews 23.349(b) torsion vs aileron loads |
| C210-39 | `flap_loads.gust_load_factor` (0.0) | none — 0 yields a non-critical gust case | the envelope computes the same number at the GUST VF corner (`flight_envelope.py:434`) |
| C210-41 | `engines[].engine_weight_lb`/`engine_cg`/`limit_load_factor` (0) | none — a 0 LIMNZ silently zeroes the mount loads | registry EXTERNAL marks exist (`:938-962`) but `EXTERNAL_VALUES` has one resolver total; `prop_weight_lb`/`prop_cg` unmarked; MassItem identity is an input, not a name match |
| C210-29 seed | `aero.surfaces` (`[]`) | none — an absent row means the surface is never analysed | geometry and aero rows are joined by `name` at `schrenk_distribution`; overlap: name, taper, sweep |

The idiom to generalise already exists once:
`vt.gross_weight_lb or max_takeoff_weight(project, required=False)`
(`select.py:840`, registered with `derived_from` + `governs=True`). No
collapsed-override widget exists in either GUI; `_copy_note` +
`_external_note` + `_offer_clear` are the nearest affordances. The main
`app/` GUI does not read the registry at all.

---

## 2. Decisions (OV-1 … OV-12)

| # | Decision | Rationale |
|---|---|---|
| **OV-1** | **The contract: falsy-means-derive, typed-means-override, at calc level.** Every collapsed field keeps its schema type; a blank/0 (or `None` where already Optional) resolves through one named resolver function, `value or derive(project)` — the `select.py:840` idiom. The resolver is the single source; module code never re-spells the derivation (rule 3). A falsy authored value is never load-bearing for any field in scope (a genuinely pointed wing derives τ from its own polylines to the same answer), so **no field changes its schema default and no semantic migration hop is needed**. | Owner ruling: calc-level, so CLI and file projects get the fix; falsy-derive avoids the 0.0→None hop `migrations.py` would otherwise force. |
| **OV-2** | **Each field's owner and resolver, by name:** `gross_weight` ← `cg_cases.max_takeoff_weight` (resolvers read raw fields, so the existing reverse fallback cannot recurse); `taper_ratio` ← a new `derived_geometry` chord helper (tip/centreline chord from the paired surface's polylines); `tip_ratio` ← the new geometry field (OV-4) / semi-span; `aspect_ratio_wing` ← the consolidated wing-AR owner (OV-5); `wing_lift_slope_per_rad` ← `aero_coeffs.cruise.lift[1] * DEG_PER_RAD` (McMaster's AW is the uncorrected per-radian slope; `select.py:594` divides it back by 57.3); `full_down_aileron_deg` ← `aileron_loads.down_deflection_deg` (direct read); `gust_load_factor` ← the envelope's GUST VF corner (OV-6); engine fields ← the selected mass rows / `design_speed_values(project).n` (OV-7). WTENV's four keep their existing derivations unchanged. | One resolver per quantity, all pre-existing owned computations — no new physics anywhere in this step. |
| **OV-3** | **The per-set stall CLs change nothing in calc** — `normalize()`'s fill-through *is* the mechanism, shipped. The work is registration (`derived_from` on the four per-set rows naming the CLmax trio) and presentation (OV-9), captioned per the C210-15 ruling ("leave blank to inherit CLmax; enter only to reproduce a deck that clamps at a different value — e.g. ga6, 1.41 vs 1.4068"). The `flaps_down.neg_stall_cl` gap stays as documented. | The oracle clamp is why the fields must survive; the ruling text is the owner's own. |
| **OV-4** | **The rounded-tip width becomes geometry** (owner directive, C210-31): `SurfaceInput` gains `tip_cap_width_in: float = 0.0` (0 = square tip, today's meaning), entered once with the wing on the Geometry page; `tip_ratio` falsy-derives as `tip_cap_width_in / semi-span`. The `tau: Optional[float]` escape hatch is unchanged. | The polylines cannot carry rounding; ownership (GR-INPUT-2), not re-entry. Additive input field → OV-10. |
| **OV-5** | **The wing aspect ratio gets one owner** in `derived_geometry` (beside `wing_reference`); the two independent spellings (`wing_geometry.py:135`, `airloads.py:210`) become calls to it — consolidation over decoration, the AS-5 pattern. `aspect_ratio_wing` falsy-derives from it for the project's wing surface. | A third spelling for the h-tail derive would be the disease this note cures. |
| **OV-6** | **The flap NG derives from the envelope's own number**: a public `flight_envelope.gust_at_vf(project)` returns the maximum positive GUST VF load factor over the flaps-down corner sets (the same `_gust_load_factor`/`_gust_ude` internals, same configs × CG cases × the flaps-at-SL rule) — not a re-spelling via `vn_diagram` (whose `GustInputs` has no "F" branch and would be a second chain to keep equal). `flap.py` resolves `ng = inp.gust_load_factor or gust_at_vf(project)` and the result states which it used. | Owner directive verbatim: "ok with a user overwrite, but we need the code to calculate it". Calling the single-source function is not recomputing another module's quantity (module contract). |
| **OV-7** | **Engine linkage (owner ruling: explicit row selector).** `EngineInput` gains `engine_mass_item: str = ""` and `prop_mass_item: str = ""` — the `name` of a weight-database row, matched with `same_name` (identity stays an input; blank selector = no derivation, today's behavior). With a selector set: `engine_weight_lb`/`prop_weight_lb` falsy-derive from the row's `weight_lb`, the CG `Vec3`s derive when `(0,0,0)` from the row's `(x,y,z)`; a typed value overrides and a >1e-6 disagreement warns via the consistency channel. `limit_load_factor` falsy-derives from `design_speed_values(project).n` (the 23.337 limit — the accessor `aileron.py`/`flap.py` already use), selector-independent. A selector naming no row is refused by name (the C210-21 pattern). `prop_weight_lb`/`prop_cg` get the EXTERNAL mark their siblings have. | D-25 mass SSOT with the linkage stated where it is consumed; multi-engine mapping explicit per engine row. |
| **OV-8** | **Empty `aero.surfaces` derives, per name, at the calc boundary**: a resolver `resolve_aero_surfaces(project)` supplies, for each geometry lifting surface with no same-name aero row, a default `AeroSurfaceInput(name=<surface>)` — whose taper/tip then falsy-derive per OV-2/OV-4 and whose other fields are the schema defaults (geometry values only, owner ruling; `section_slope` 0.1075 and `target_cl` 1.0 are real defaults, and #98's caption makes the absence visible). Typed rows are kept as typed; nothing is written to the project (OG-1's capability cap untouched — this is derive-from-an-owner, not a seed button). | The owner's split ruling: the seed half is a derivation, the caption half stays at #98. Per-name keeps a typed wing row from suppressing a derivable second surface. |
| **OV-9** | **Presentation (oracle GUI): the collapsed-override widget.** Each collapsed field renders with the computed value beside it — blank: "blank — derives ⟨owner⟩ (currently X)"; typed: the existing `_copy_note` override caption + the >1e-9 disagreement warning; Optional fields keep the `_offer_clear` "✕ clear" back to derived. Mechanically: each collapsed path gets `derived_from` naming its owner **and a resolver registered in `EXTERNAL_VALUES`** (the existing map, today one entry), which is what the caption reads — one registry mechanism, no second channel. The **main GUI needs no change for correctness** (the calc derives for both by construction); its caption parity is recorded against the main-GUI review (#29's row), not silently dropped. | The C210-15 ruling's exact shape; practice 3 — registry + resolver + guard, never a prose rule. |
| **OV-10** | **Schema: additive input fields, `SCHEMA_VERSION` 55 → 56** with an identity hop in `MIGRATIONS` (old files load unchanged; the new fields read `d.get(..., default)`), floor moved per the #93 gate. Fields added: `SurfaceInput.tip_cap_width_in`, `EngineInput.engine_mass_item`/`prop_mass_item`. No default changes, no field removals, DATA_DICTIONARY regenerated. | The gate refuses any non-current version, so an additive field still costs a bump + hop; all three defaults are backward-benign. |
| **OV-11** | **The drift guard (rule 3):** a registry-level test owns the collapsed set — every path in it carries a non-empty `derived_from` **and** a resolver in `EXTERNAL_VALUES`; and the inverse, no registry row whose `quantity` names another owner's quantity may lack a `derived_from` link. A future duplicated input without its link fails CI, which is what makes the mechanism the single-source owner rather than a convention. | The deliverable's own words: "a drift guard failing on a duplicated input that has an owner but no link". |
| **OV-12** | **No load number changes on any fully-specified project.** Every Appendix A oracle and twin closure passes untouched; the fixtures type explicit values, so derivation never fires on them. Where a blank used to produce a silently wrong number (τ 0.206 on a tapered wing, a zeroed mount case, an unguarded ARW divide), the number *changes to the derived one* — that is the fix, not a deviation, and each such path gets a test stating both the old failure and the new value. | The backlog's standing invariant plus rule 6: the defect class is the silent default, and the derived value is the owner's own computation. |

---

## 3. Closure gates (G-OV-1 … G-OV-6)

Benchmark-first (rule 2). Identities exact (`rel_tol=1e-9`); oracle suite
±0.1 % untouched.

| Gate | Statement | Expected numbers |
|---|---|---|
| **G-OV-1** (oracle invariance) | The full Appendix A oracle suite and both twin-closure suites pass unchanged; the frozen fixture digests are untouched. | Zero diffs — the fixtures author every collapsed field explicitly. |
| **G-OV-2** (derive-equals-owner, CI) | On ga6 with each collapsed field blanked in turn, the resolved value equals its owner's computation: taper = tip/centreline chord from the polylines; ARW = the consolidated planform AR; AW = `cruise.lift[1]·57.3`; aileron = `down_deflection_deg`; NG = the envelope's own GUST VF corner factor **bit-for-bit** (same function); LIMNZ = `design_speed_values(project).n`; `gross_weight` = MTOW; engine weight/CG = the selected row's values. | rel 1e-9 (NG and LIMNZ exact — same call). |
| **G-OV-3** (the defect dies) | A blank `taper_ratio` on a tapered planform no longer yields the pointed-wing τ: τ(derived taper, tip) ≠ 0.206209 and equals `_tau` at the polyline chord ratio; a blank ARW no longer divides by zero — it derives; a blank LIMNZ no longer zeroes the mount loads. | τ = `_tau(c_tip/c_root, tip_ratio)`; each test states the pre-fix failure. |
| **G-OV-4** (widget + registry guard) | OV-11's drift guard: every collapsed path has `derived_from` + an `EXTERNAL_VALUES` resolver (extending `test_every_external_resolver_names_a_registry_row`); the oracle GUI renders the computed value beside each collapsed field, blank and typed, and warns on a >1e-9 typed disagreement (the `_copy_note` pattern). | The collapsed set enumerated once, in the guard. |
| **G-OV-5** (schema round-trip) | A v55 project file loads through the 55→56 hop unchanged; a v56 file round-trips the three new fields; `applied_hops(55)` names the hop; the schema-ledger records the addition. | `SCHEMA_VERSION == 56`; ga6 loads bit-identical. |
| **G-OV-6** (mismatch surfaced) | Typed-and-disagreeing pairs warn via the consistency channel (rendered in both GUIs since #82): the aileron pair, engine weight/CG vs the selected row, and a selector naming no mass row is refused by name. `gross_weight` vs MTOW keeps its existing warning. | New codes: `aileron_deflection_mismatch`, `engine_mass_row_mismatch`; refusal message names the selector and the missing row. |

**Closure tier:** L — this note at AGREED first, then implementation with the
`theory_sources.md` rows grown one sentence each (airloads τ derivation
source, flap NG source, engine LIMNZ source), the schema-ledger entry, a
full-format history fragment, `PROGRAM_SPEC.md`'s affected sections
(AIRLOADS, FLAPLOAD, ENGLOADS, WTENV, SELECT) and the regenerated
DATA_DICTIONARY.
