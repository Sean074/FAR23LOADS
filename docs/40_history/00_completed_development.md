# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

**Live cycle only.** This file holds the current release cycle plus the previous
release cut. Older blocks roll into frozen, do-not-edit archives at each release
(`RELEASE_PROCESS.md` §4): everything before 0.5.0 is in
[`11_completed_development_to_0.5.0.md`](11_completed_development_to_0.5.0.md).
Tier S closures do not write here (a `changes/` fragment is their record); tier M
writes one paragraph, tier L the full step format — **as a `changes/<slug>.history.md`
fragment** (design note 28 MD-4), rolled to the top of this file at release cut, so
concurrent PRs never edit the same line here. Only the release-cut block itself is
written directly, by the release manager.

---

- **Fin-root body datum (backlog Pri 1, defect from T-8a, tier M, 2026-08-16)** — `tail_geometry.fin_root_waterline`'s fuselage-top branch is `z_centre(xv25) + height(xv25)/2` from the fuselage outline (the v52 section-centre line + the new `derived_geometry.fuselage_height_at`), retiring the wing-root-plus-half-a-body substitution to a no-outline fallback that names itself; new project-level resolver `tail_geometry.fin_root` read by both the load path and the three-view (`configuration.tail_planform` gained an optional `project` arg). Re-pinned three fin roots (`atr42_100` 223.15 → 191.17 in, `dhc8_dash8` 232.95 → 203.45, `cessna_210` 109.60 → 100.24), the twelve lateral cases (`p_dot`/`r_dot` only — fin load and `n_y` byte-identical), and the Imperial digest baseline; docs: `CONVENTIONS.md` §7 fin-position bullet rewritten from "known limitation" to the resolved formula.

- **Static typing and lint depth (design note 27, tier M, 2026-08-16)** — `mypy` is a merge gate over `sloads/` (own CI job, 3.12; zero errors in default mode; per-package strictness ratchet, stage 1 on the SSOT owners); 153 → 0 errors by narrowing only, no output byte changed (frozen digest + oracles unmodified); latent `None` dereferences on already-refused paths now raise per the error contract (`balance.py`, `engine.py`); `ruff` widened to `E F W B SIM PLE PLW ARG RUF I C4` with reasoned ignores, 243 → 0. Rules: `00_program_overview.md` §Static typing & lint. Backlog: ratchet stages 2 (`export/`) and 3 (`modules/`).

- **Documentation currency rule + guard (tier M, 2026-08-16)** — standard docs point at owners, never copy volatile values (schema number, test count, coverage %, "currently N"); provenance stays `schema vN`. Rule in `00_program_overview.md` §Documentation currency, `CLAUDE.md`, `CODE_REVIEW_PROCESS.md` step 1; guard `tests/test_doc_currency.py` (literal patterns over the standard set + `docs/00_INDEX.md` ↔ tree both ways, the R6-D2 class). Four `SCHEMA_VERSION = N` claims in `GUI_design.md`/`PROGRAM_SPEC.md` swept to provenance/pointers.

- **Doc volume: history archive, changelog fragments, tier S trimmed (backlog R11, tier M, 2026-08-16)** — design note `docs/30_future/26_doc_volume_reduction_note.md`, all three recommendations accepted at user review. (a) This file cut at the 0.5.0 release block; 7,970 pre-0.5.0 lines moved verbatim to `11_completed_development_to_0.5.0.md`. (b) `CHANGELOG.md` `[Unreleased]` is no longer hand-edited: each closure drops one `changes/<slug>.<type>.md` fragment and `scripts/build_changelog.py X.Y.Z` assembles them into the release section at cut time (`tests/test_changelog_fragments.py` guards fragment names/shape and warns when this file passes 1,500 lines). (c) Tier S = fragment + backlog removal, no history entry (`CLAUDE.md` table, `CODE_REVIEW_PROCESS.md` §0). `RELEASE_PROCESS.md` §4 gains the mechanical history-roll step: build changelog, move shipped plan notes to `40_history/`, roll the previous release block into an archive when the live file exceeds the threshold. Legacy hand-written `[Unreleased]` text is folded into 0.6.0 verbatim; fragments start now.

- **Doc currency: schema literal in `00_program_overview.md` (tier S, 2026-08-16)** — §Version & phase said "currently **15**" (`SCHEMA_VERSION` = 52) with a stale `models.py` path; now points at the constant in `sloads/models/project.py`, no literal number; `.claude/launch.json` dropped an unrelated `life-app` entry.

- **CH-1 test-suite runtime (backlog Pri 1, tier S, 2026-08-16)** — coverage out of `addopts` and into the CI `test` job's explicit flags (floor unchanged at 80); `pytest-xdist -n auto` on by default (`pytest-xdist` added to `dev`); the ~18½-min single-threaded run drops to minutes; docs: `00_program_overview.md` §Testing & coverage.

- **Backlog re-cut per the 2026-08-16 scope and deficiency review (tier S, 2026-08-16)** — `docs/50_reviews/2026-08-16_scope_and_deficiency_review.md`; band A = 0.6.0, step 14 descoped to a `PBAR`/`MAT1` pass-through, fourteen rows parked with bodies, effect-vs-error-bar rule + schema freeze added, frozen-capability list recorded.

**Step 12 — the LRA beam model, export + import (complete 2026-08-16, tier L)**

**Objective.** Close backlog Pri 1: ship the **third deliverable** (note 24
R-1, agreed 2026-08-15) — a structural idealization on the load reference
axes that the FORCE/MOMENT sets apply to, whose value is the internal loads
at the named nodes (SOB, posts, fin root, h-tail attachments) that neither
the per-component decks nor the assembled balanced deck can state — plus the
import half: an external beam model becomes the LRA. Implementation
decisions LM-1…LM-7 recorded in
`docs/30_future/25_lra_model_implementation_note.md` (note 24 §7's
delegated choices, chiefly LM-1: nearest-node transfer with the exact
lever-arm couple, not tributary interpolation).

**Deliverables.** `sloads/export/lra_model.py` (`lra_model.bdf`: wing chains
starting at the SOB per R-3; split-fuselage cantilevers onto the front/rear
spar posts, BM-2, no element through the carry-through; rigid centre-box
hub; fin-root, h-tail-attachment/T-tail-joint, gear (`carrier`, BM-4) and
engine hub+mount (`EngineInput.mounted_on`, R-9) ties; `$ SLOADS-NODE`
tags per BM-5; refusals naming the missing datum per BM-3/LM-4);
`sloads/export/lra_import.py` (`read_lra_model` /
`lra_loads_on_imported_model`: the same case sets under the imported GIDs,
tag-mapped, position-validated at ±2 in, nearest-node marked-assumed
fallback); `export/coordinates.transfer_couple` — the one owner of the
transfer rule (R-11); bands `lra-wing-left`/`lra-fuselage`/`lra-centre`/
`lra-engine`/`lra-attach`/`lra-cbar`/`lra-rbe2` (production RBE2 promoted
from the test-only 900001+); `derived_geometry.fuselage_centreline` (R-4);
schema **v52** (`z_centre`, `mounted_on`, aileron/flap butt-line +
hinge/actuator fields, `ref_axis_pct` Optional with the `ref_axis`
effective accessor and the stored-0.25→unset io mapping, R-7c); CLI
`--export-target lra` / `--lra-import`; the Export page bundles the deck;
fixtures enter `ref_axis_pct = 0.40` (R-7a) and engine `mounted_on`.

**Test / Acceptance.** `tests/test_lra_model.py` (15): the transfer-rule
drift guard; skeleton families tagged and tied on atr42; the T-tail joint on
the fin tip with no fuselage pair (R-6, T7 excluded); no element spans the
carry-through; the wing chain starts at the SOB and every inboard strip
routes onto it; refusals named; discrete-mode hinge/actuator skeleton
(synthetic, LM-6); the **plan-07 invariant** — LRA deck resultant ≡
balanced deck resultant per case, all six components, four fixtures;
export→import round trip resultant-identical, divergent tags fail loudly.
`tests/test_sbeam_roundtrip.py`: the model **solves** and the support
reaction = −applied resultant ≈ 0 (free-free proof through real structure,
both unit systems), and the SOB / front-post internal loads equal the
cut-side card sums through the element frame (graph partition at the cut,
the step-13 sign map). Pinned strict xfail: sbeam's dense-path 1e15
condition heuristic refuses the regional jet's SI (mm) deck — a units
artifact (equilibrated cond ≈ 1.3e9; the Imperial twin solves exactly);
support placed beside the front post (nose-clamped conditioning measured
1.6e15 → 2.8e14). Digest wave stated in the CHANGELOG: wing/tail/net-loads
channels + the balanced deck moved once for the 0.40 fixture axis;
`sbeam/lra_model` joined the baseline on the four building fixtures;
body/chordwise/oracle channels byte-identical.

**Key decisions.** LM-1 (nearest-node + exact couple; single owner);
LM-3/BM-2 (split fuselage structural — the two cantilever sums are
recoverable end forces; the p103 comparison is reported, not gated);
LM-4/BM-3 (refuse: unset `ref_axis_pct`, no SOB, no outline, no
carry-through, strip-pair attachment); LM-5 (gear's BM-4 field **is** the
shipped G-2 `carrier`); LM-6 (hinge/actuator nodes ship as tagged skeleton
with rigid parent ties; the hinge-line chain + torsion identity gate ride
with Pri 7's data); LM-7 (source-routed members, nearest-in-skeleton for
closure/relief loads); R-7d closes the CONVENTIONS §1 torsion-reference
question (backlog Pri 14 removed with it). Specs synced: PROGRAM_SPEC "LRA
beam model" section + R-1 three-artifact statement, CONVENTIONS §1 + two §7
owner rows, PROJECT_GUIDE §4, theory_sources row, GUI_design v52 paragraph,
DATA_DICTIONARY regenerated, backlog renumbered.

**Step 12 phase 0 + step 13 — the LRA skeleton contract and the wing
side-of-body node (complete 2026-08-16, tier M)** — backlog Pri 1, note 24
(agreed 2026-08-15): decisions **BM-1…BM-5** recorded in
`03_resolved_decisions.md`; `SurfaceInput.sob_y_in` (schema **v51**, additive)
with `derived_geometry.sob_station` as the one SOB owner (entered → half
fuselage width marked assumed → none; never `inboard_rib_y`) and the h-tail
attachment reading the same quantity (`ATTACH_ENTERED`); the per-component wing
stick deck **adds** a tagged reporting node at the joint (GID band `lra-sob`
7001+, the BM-5 `$ SLOADS-NODE` tag's first use) without moving any station or
card, so the Appendix A station-0 closure is untouched; the wing root design
load is stated **two ways and gated** — `sob_internal_loads` closed-form (deck
`$` header per case + the report's "Wing side-of-body internal loads" table)
against the solver's CBAR end force in the first element outboard
(`test_the_sob_internal_load_is_the_first_outboard_elements_end_force`, RJ +
atr42, both unit systems) — and `sob_collapsed_load` (the inboard strips as one
resultant-preserving equivalent at the SOB) is built and pinned as the step 12
LRA wing-beam start. GUI: the surface form and the WINGGEOM re-seed carry
`sob_y_in`. Specs synced: PROGRAM_SPEC sbeam-bridge section, GUI_design schema
line, DATA_DICTIONARY regenerated, `bands.py` map. Digest wave: `wing_stick`
on all six (four gain the node; all six the amended one-wording
`CENTERLINE_CLAMP_NOTE`); every other channel byte-identical.

**The h-tail beam is reacted where the airplane reacts it (complete 2026-08-15, tier L)**

**Objective.** Close backlog Pri 1 — decision **T-8a**. The row read "populate
`fuselage_width` on the fixtures so the h-tail attachment stops taking the
`±ds/2` fallback" (note 24 BM-1/BM-3, F5.1), Tier S, effort S.

**What the measurement changed.** Three things, each found before any edit.

1. **`fuselage_width` is not persisted.** It is a derived read-only *summary* of
   `geometry.fuselage` (M2-6, `derived_geometry.py`), so "populate it" meant
   "ship a fuselage outline" — and only `concept_regional_jet` had one.
2. **The summary is the *maximum* section, and the h-tail attaches in the tail
   cone.** On `atr42_100` that is 106.3 in of published diameter against ~22 in
   of body at `xt25` — the formula as written would have put the attachments
   **five times too far outboard**, an error in the opposite direction from the
   fallback it was replacing and larger than it.
3. **The function ignored `tail_type`.** `concept_regional_jet` is a declared
   T-tail, whose horizontal surface is not fuselage-attached at all, and it was
   getting a fuselage-side pair at ±52.5 in — the one fixture that *had* an
   outline was the one being described wrongest. Swept in the same change
   (practice 4).

And one more that could not be swept: entering a fuselage **height** activates
`fin_root_waterline`'s `"fuselage-top"` branch, dormant on every fixture until
now. See **Consequence** below.

**Deliverables.**

* **`derived_geometry.fuselage_width_at(outline, x)`** — the single owner of
  "how wide is the body *here*", beside `fuselage_summary`'s "how wide at most".
  Linear interpolation between bracketing sections, clamped at both ends.
* **`tail_span.htail_attachment` → `HTailAttachment(y, assumed, basis, note)`**,
  the `FinRoot`/`BodyDragWaterline` provenance shape. Resolution order: T-tail
  fin-tip joint at `y = 0` (not assumed — entered `tail_type` is the whole
  authority) → outline width at the h-tail **root LRA station**, `±w/2` →
  `±ds/2`. `attachment_stations` survives as the stations-only wrapper.
* **`TailSpanResult.attachment_assumed`/`attachment_basis`** — additive result
  fields, no `SCHEMA_VERSION` bump and no migration hop; `io` round-trips them.
* **Three published fuselage outlines** (`atr42_100`, `dhc8_dash8`,
  `cessna_210`): max diameter 2.70 / 2.69 / 1.20 m on the three-section default
  shape, each source's overall length cross-checking the fixture's entered
  `airplane_length_in` to under 0.3 in. Attachments move ±5.5 → ±10.9,
  ±5.75 → ±10.8, ±3.6 → ±11.3 in. `ga6_normal` and `concept_heavy` are
  synthetic and keep the flagged fallback rather than an invented outline.

**Consequence, accepted and filed (this is what made the step tier L).**
`fin_root_waterline`'s third branch is `root_waterline_z + fuselage_height/2`;
with no fixture carrying a height it had silently degraded to
`root_waterline_z` on all five. It now fires — `atr42_100` 170 → 223.15 in,
`dhc8_dash8` 180 → 232.95, `cessna_210` 86 → 109.60 — and that is the fin's
**roll arm**, so twelve lateral cases moved with it (`cessna_210`'s `p_dot`
−28.99 → −74.59 deg/s², a factor of 2.6). Fin **loads** and `Ny` are unchanged,
which is the check that a lever arm moved and not the aerodynamics. The user was
shown the numbers and chose to accept and re-pin rather than gate the branch.

**The formula is wrong and the pins say so.** It reads `root_waterline_z` as the
body centreline; it is the **wing** root — the same substitution `CONVENTIONS.md`
refuses for D-1 — and all three of these types are **high-wing**, so it stacks
half a body height above a wing root already near the body top. Filed as backlog
Pri 5a with note 24 R-4's `FuselageSection.z_centre` as the fix, and paired with
Pri 6a: `atr42_100` and `dhc8_dash8` are declared `tail_type: conventional` and
are really T-tails, so they are also missing the T7 tip transfer.

**Test / Acceptance.** `tests/test_tail_span.py` gains
`test_the_ttail_htail_is_reacted_at_the_fin_tip_not_at_the_fuselage`,
`test_the_attachment_interpolates_the_body_at_the_htail_and_never_its_maximum`
(which asserts the interpolated width is under a quarter of the maximum — the
gate against ever silently reverting to `fuselage_summary`) and
`test_the_attachment_falls_back_to_the_strip_pair_without_a_body_outline`; the
full-span topology test now branches on `is_t_tail`. `_FIN_ROOT` and
`_LATERAL_CASE_NUMBERS` re-pinned with the reason in-comment;
`test_fwd_regardless_negative_station_marks_none_via_datum` rebuilt on a
constructed loading, as its own comment has twice instructed. Imperial baseline
regenerated (24 digests); schema-shape hash updated. Suite 1893 passed,
`ruff check sloads/ cli.py app/` clean.

**Key decisions.** **T-8a** — the attachment is a *resolution order with
provenance*, not a number: T-tail topology first, then the body outline
interpolated at the h-tail LRA station, then the stated strip pair; the maximum
section is never used. The outline branch is marked **assumed even for an
entered outline**, because no shipped outline resolves the tail cone and the
default shape factor — not the published diameter — sets the number (the
half-span swings by half again on it). Consumers gate on `basis`, not on
`assumed`. Synthetic fixtures get no invented geometry (T-17 upheld).

---

**Every shipped fixture assembles balanced cases (complete 2026-08-15, tier L)**

**Objective.** Close backlog Pri 5 — decision **D-26** (amending D-25). Give the
four silent fixtures a `CgCase.loading` each so the concept-loads → sbeam loop is
exercised in CI on six airplanes instead of two.

**What the measurement changed.** The row read as data entry. Measured before any
edit, it was not enterable. D-25a makes a case's `weight_lb`/`xcg`/`zcg` a checked
echo of the loading's own properties, so an entered loading must genuinely
reproduce the case — and on five of six fixtures the entered cases miss what the
item database can produce by **15–60 in in station and 4–31 in in waterline**. On
`cessna_210`, `dhc8_dash8` and `concept_heavy` the heaviest case weighs *exactly*
the all-up weight, so precisely one loading produces it and its CG is not a
choice. The least ballast that closes the cases inside the airframe runs **10–44 %
of each airplane**, pressed against the propeller spinner and the fin tip: the
"wrong cards outrank missing cards" case in full. `ga6_normal` is the exception
and the tell — the Appendix A airplane sits on its own database to 0.10 in and
0.42 in, because it was built from it.

Two further measurements set the shape of the fix. **`zcg` has no envelope behind
it**: WTENV's weight–CG envelope is weight against *station*, and on five fixtures
the waterline was a round figure entered independently of the item waterlines,
6–31 in above the loading's real waterline on the flight cases and 20–27 in
*below* it on the `atr42`/`dhc8` ground cases — inconsistent in sign, which is
what an unsourced entry looks like. And **a database of two or three lumped
payload rows admits exactly one loading at gross weight** (ga6's included), so a
fwd and an aft corner case at the same weight collapse onto the same airplane.
That second measurement is why the agreed option A was amended mid-step to A+B:
zoning is what makes a zero-ballast answer reachable at all.

**Deliverables.**

* **Case data corrected to the database (D-26).** All 34 cases across
  `cessna_210`, `atr42_100`, `dhc8_dash8`, `concept_heavy` and
  `concept_regional_jet` re-entered as the forward-most or aft-most loading of
  their own design weight, with `weight_lb`/`xcg`/`zcg` read off that loading.
  **No ballast row anywhere.** `ga6_normal` untouched.
* **Zoned payload rows (D-26b).** `Passengers (n)` and `Baggage / cargo` split
  into fwd/aft cabin and fwd/aft hold on the three fixtures that carried them as
  point masses, at stations chosen so each fixture's discretionary `Σw`, `Σwx` and
  `Σwz` are preserved exactly — so the all-up weight and CG move by nothing, and
  every full-database total and reconciliation is unchanged. The point-mass
  inertias about the airplane CG do rise, which is the physically correct
  consequence of a cabin no longer being a point; `mass.cases` is re-derived from
  the items.
* **`cessna_210` capacity and `CG4` (D-26c).** Usable fuel corrected to 720 lb
  (120 US gal, the type's long-range option) — its database had summed to
  *exactly* MTOW, so no two loadings of that airplane weighed the same and neither
  the flight nor the landing fwd/aft pair could exist. `CG4`, entered at 2,300 lb
  against an empty-plus-pilot-plus-reserve weight of 2,474 lb, re-entered at 2,474.
* **Two renames**, because the corner point each was named for is not one:
  `concept_heavy` `CGfwd` → `CGmax` (its only loading is the all-up one) and the
  RJ's `CG3 fwd light` → `CG3 light` (at 24,000 lb that airplane's CG goes aft).
* **`export/mass_cards.py` — the part-full card defect.** Overlay cards are matched
  by object identity and a fractional row is a scaled copy, so it matched no card
  and left the deck: the exported mass model weighed less than the loading it
  declared — `dhc8_dash8`'s max-landing case by **4,160 lb** — in a file that
  parsed and solved. Each (case, part-full row) now gets its own card in a new
  `mass-part-full` EID band (9501+, registered in `bands.py`), and `MassCard`
  gains `case_index` to say which cards are per-case rather than shared. A
  part-full **non**-discretionary row would need a MASSSET `REPLACE` row and is
  refused loudly rather than mis-emitted.
* **`modules/balance.py` — the re-weighted ground target.** 23.473(a) lets
  23.485/23.493 be met at MTOW while 23.479/481/483 are met at MLW, and
  `_ground_target` re-weights the case for it. A `LoadingDefinition` states which
  items are aboard, not what the airplane weighs, so carrying it onto the
  re-weighted target assembled 31,000 lb of mass under a case declaring 33,000.
  The re-weighted target now drops the loading and goes through the subset search
  — the one route that solves for weight as well as station, and what produced
  these cases before any loading was entered.

**Test / Acceptance.**

* **Appendix A oracles unchanged**, `ga6_normal` untouched by the step.
* Coverage pins re-pinned and now stating completeness rather than partiality:
  `test_which_conditions_assemble_is_pinned` 2 → **6 of 6** fixtures;
  `test_which_ground_cases_assemble_is_pinned` the full 27-case family on all
  **5** fixtures with gear geometry; `test_which_payload_cases_are_derivable_is_pinned`
  and `test_which_loadings_are_entered_is_pinned` every case, every fixture;
  `test_ground_coverage_matches_what_the_plan_measured` 3/3 everywhere.
* `test_the_card_set_reproduces_each_loading` — Σ CONM2 mass and CG equal the
  loading's, in deck units, on every fixture in both unit systems. This is the
  gate the part-full defect failed.
* `test_the_inertia_set_weighs_the_case` — Σ modelled mass equals the case weight
  exactly, on every assembled case. The gate the ground-target defect failed.
* Plan 07's global-equilibrium invariant closes on every assembled deck and the
  sbeam round-trip CI leg stays green; Imperial and SI digests re-baselined.
* Four tests whose premise was "some fixture fails to assemble" now **build** the
  failing state instead of naming a fixture: the no-derivable-case refusals, the
  F-C7 assembly record, and D-25d's entered-ballast-is-not-gated case. A mechanism
  whose only test is a fixture that may legitimately stop exercising it is a
  mechanism that silently loses its guard.

**Key decisions.** **D-26** (correct the case data to the database where the case
is not a loading the database can produce), **D-26a** (`zcg` is a derived echo,
not an independent corner point), **D-26b** (zone the lumped payload rows,
preserving the discretionary totals), **D-26c** (`cessna_210` fuel capacity and
`CG4`). Design note:
[`../30_future/23_pri5_fixture_loadings_note.md`](../30_future/23_pri5_fixture_loadings_note.md).

**Filed, not fixed.** The five non-oracle fixtures reach a pre-closure force
residual of **1.2–2.0 % of n·W** against plan 11's 1 % acceptance, and three show a
**positive `dCD` on `NMAA`** at α ≈ −13°. ga6 is best by 2× and the concept
configurations worst, which reads as fixture aero-data quality rather than an
assembly defect — every case still closes exactly after correction and the pitch
residual stays at 0.07–0.84 %. Recorded per fixture in `test_balance.py`
(`_FORCE_RESIDUAL_RATCHET`, `_DELTA_CD_POSITIVE_AT_TRUSTED_ALPHA`) rather than
absorbed by widening a gate, and filed as backlog Pri 6.

---

**`CgCase` gains an explicit loading definition (complete 2026-08-15, tier L)**

**Objective.** Close backlog Pri 6 — decision **D-25**. A `CgCase` stated a
weight and a CG (a corner of the weight/CG envelope, the real engineering input
on a reference airplane) but not *what loading produces it*, so the mass model
behind every payload case was **searched for**: `derive_case_loadings` tried the
`2^n` discretionary subsets of `weight.items` plus a ballast row solved from the
residual, and accepted the result only under the 10 % credibility gate. That
reached **7 of 18** shipped cases; four of six fixtures produced no balanced case
at all, not for any failure of the assembly but because no honest inertia set
existed behind their cases. D-25 made the loading an input rather than editing
the fixtures' corner points to suit their item databases.

**Deliverables.**

* `LoadingDefinition` (`models/inputs.py`) and `CgCase.loading` —
  `aboard` (discretionary rows carried; `EMPTY`/`MINIMUM` are implicitly aboard
  and naming one is rejected), `fractions` (a `consumable` row scaled to a
  part-full value in `(0, 1]`, station and inertias unchanged, so a tank layout
  is preserved exactly as G-5's burn-down preserves it) and an optional entered
  `ballast` row carrying its own waterline. `SCHEMA_VERSION` **49 → 50**,
  additive and optional, so no migration hop.
* `mass_distribution.entered_loading` — assembles what the case states. No
  search, no solved ballast, no credibility gate; every malformed loading is a
  `ValueError` (unknown row, a non-discretionary row named, a duplicate, a
  fraction on a non-consumable row or outside `(0, 1]`, a fraction for an item
  not aboard) rather than a silent fall back to the search, which would hide an
  entry error behind a plausible answer. `CaseLoading.entered` carries the
  provenance to every consumer.
* `case_loading_checks` gained the **echo check** (D-25a) and `validation.py` two
  Weight & CG findings — `cg_case_loading_echo` and `cg_case_loading_invalid` —
  so a loading edited on the page reports there as well as at calc time.
* `io.py` maps the slice both ways (`_loading_from_dict`/`_loading_to_dict`, with
  `_mass_item_to_dict` extracted so the ballast row and the item list share one
  serializer); an absent key is both the pre-v50 shape and the live "derive it"
  state, so a re-saved older file keeps its bytes.
* First user: `concept_regional_jet`'s **CG3 fwd light** — 24,000 lb at station
  595.12, needing 2,800 lb (12 %) of ballast, which the solved-ballast gate
  refused. Entered as a `Test ballast, fwd hold` row at x 283.4 / z 112.7, it
  reproduces the case to 0.0008 in. The fixture's **NMAA** condition, the concrete
  case review finding F-C7 was raised on, now assembles: the flight family is
  complete on that fixture, and the record's remaining `loading-not-derivable`
  entries are its ground family (Pri 7).
* The provenance travels with the mass model: `mass_case_rows` carries
  `entered`, and the report's payload-case table and the Weight & Mass page both
  state `entered` / `derived` per case.

**Test / acceptance.** Appendix A oracles untouched (no calc-math path reads
`loading`); the Imperial baseline moved on **four channels of one fixture** — the
RJ's `case_index`, `csv/balance`, `sbeam/balanced_deck`, `txt/balance` — and
nowhere else. New: the **reduction gate**
(`test_an_entered_loading_reproduces_the_derived_one_on_ga6` — entering what the
search finds on ga6's CG2, the case needing the largest ballast, reproduces it
item for item and to `rel=1e-12`), the echo check firing on a perturbed `xcg`,
the entered-ballast exemption, six malformed-loading rejections, the partial-tank
station invariant, three `io` round-trip tests and two validation tests. Pins
re-pinned by design: `test_which_payload_cases_are_derivable_is_pinned`
(RJ 2/3 → 3/3), `test_which_conditions_assemble_is_pinned` (NMAA), the closure
`Izz` table, and a new `test_which_loadings_are_entered_is_pinned`.
`test_a_symmetric_case_reduces_to_three_dof` was **strengthened rather than
loosened**: its `q_dot = My/Iyy` identity now carries the CG→centroid transfer
`M_c = M_cg + (cg − c) × F` explicitly, which is identically zero on a
solved-ballast loading and non-zero (0.0008 in here, 0.0024 in on ga6's CG4)
whenever a real loading lands *near* its case instead of on it — the relief field
is exact about the centroid, and the residual is reported about the CG (D-R8).

**Key decisions.** D-25a (the loading is authoritative, the case scalars are a
checked echo at `max(0.5 lb, 0.1 %)` / `0.5 in`), D-25b (item references +
`consumable` fractions + an entered ballast row; `weight.items` stays the mass
SSOT), D-25c (optional, search retained as fallback), D-25d (the credibility gate
is on solved ballast only). Design note:
[`../30_future/22_d25_cgcase_loading_note.md`](../30_future/22_d25_cgcase_loading_note.md).
**Scope boundary:** populating `cessna_210`, `atr42_100`, `dhc8_dash8` and
`concept_heavy` — the 2 → 6 fixture CI multiplication — is backlog Pri 7, which
consumes this schema; wing-tank fuel separability (Pri 8) rides the same wave as
a separate `MassItem` change.

**SELECT Apply no longer persists un-applied geometry edits (complete
2026-08-15, tier M)** — backlog M4-22: the Flight Envelope page's SELECT-inputs
form handler wrote the page's *probe* copy back to session state, and that copy
carries `fl_effective` (the live merge of the "Apply geometry & altitudes"
widgets), so pressing Apply inside the SELECT expander silently committed
whatever had been typed into the other form (XTC / XTF / reference Mach /
altitudes) — the M2-3 persist-only-on-Apply contract, violated for a different
form's fields. The handler now writes only `select_input`, onto the session
project. `tests/test_flight_envelope_view.py` drives the page headlessly and
pins both halves: the SELECT Apply saves its own field and leaves
`flight_loads.xtc` at its stored value (it fails on the old handler), and the
geometry form's own Apply still persists. Sweep (practice 4): the probe-copy
pattern exists on this page only — every other view writes the session project
directly.

**The Dash 8's wing-carried main gear is wing mass in both models (complete
2026-08-15, tier M)** — G-2's mass half: `dhc8_dash8` states
`main_gear.carrier = wing` (nacelle-mounted leg) while the 1,200 lb `Main gear`
item was tagged `fuselage` and WINGINER's `concentrated` omitted it, so the body
beam held 1,200 lb it does not carry and the wing lost its own gear's inertia
relief. Item re-tagged `wing`; a 600 lb/side `main gear` concentrated mass added
at BL 75 (the trunnion butt line) and the item's own station — so the wing tie's
gap stays 4,000 lb = wing-tank fuel alone rather than mixing two causes. Wing
inertia root `Sz` −18,320 → −20,570 lb-ULT (the leg's 2,250 lb-ULT per side),
net wing root shear −4.5 % and bending −1.3 %; ten Imperial channels re-pinned
on that fixture. `gear_carrier_mass_disagrees` now fires on no shipped fixture,
with a re-mistag test keeping the guard honest and a per-fixture pin on the
offset-couple node count (the gear brackets a second strip). `CONVENTIONS.md`
§ground states the carrier↔mass-model rule.

**The FAR 23 gate reads the MTOW SSOT (complete 2026-08-15, tier M)** — G-14's
deferred half: `applicability.design_weight_lb` fell back to the item-database
*total* (the ceiling of `OEW ≤ MLW ≤ MTOW ≤ Σ items`, up to 1,800 lb above MTOW)
whenever `speeds.weight_lb` was unset, and now reads
`cg_cases.max_takeoff_weight`. `WeightInput.direct_totals()` →
`database_totals()`, with the same-class read-throughs swept on Structural
Speeds, Weight & Mass Properties, Aircraft Comparison and the report's weights
table (one row split into MTOW + database ceiling). **The "moves output on
atr42/RJ" claim in the 2026-08-14 entry below is wrong** — measured 2026-08-15,
both fixtures set `speeds.weight_lb`, so the gate already read the right number;
the defect was latent, live only for a project caught mid-entry. Guard:
`test_design_weight_is_the_mtow_ssot_and_never_the_database_total` pins the
fallback. Digest: `txt/weight_estimate` on the four concept fixtures (renamed
method in the concept note); no numeric channel moved.

**`LATERAL_AERO_NOTE`'s `n_y` direction corrected (complete 2026-08-15, tier M)**
— the in-band lateral caveat called `n_y` over-stated and its inertia
conservative; the missing body/wing side force *adds* to the fin's at `+β`, so
`n_y` is **under**-stated and that inertia is **not** conservative (the yaw half
was right). The sentence now states a direction per DOF, magnitudes still unknown
in band (quoting them is backlog L-7's job); corrected in
`balance.LATERAL_AERO_NOTE` + docstring, `CONVENTIONS.md` §1 and
`PROGRAM_SPEC.md`'s two lateral bullets, with a per-DOF pin in
`tests/test_methods_stamp.py`; Imperial baseline regenerated (two text channels
on the two lateral fixtures, no numeric channel moved).

**The body drag carrier — non-wing drag in the assembled model (complete
2026-08-15, tier L)**

**Objective.** Close backlog Pri 5. The assembled model carried no non-wing drag:
the FLTLOADS trim balances the airplane-less-tail drag from the polar
(`drag_cd(config, cl)`), while the only `fx` in `balance.assemble` was the wing
strips' own chordwise force from `airloads`. The fuselage, nacelle and remaining
parasite drag had no carrier, so `residual_fx` *equalled* the wing's drag and the
couple the missing force left about the CG was the whole of the pre-closure pitch
residual — the exceedance that had been open since B2 and had twice been
attributed to other causes.

**Deliverables.**
- `balance.body_axial_set` — the `body-axial` load, `vn.dx − Σfx(wing-air)`,
  spread over the fuselage outline by cross-section-area share
  (`_body_drag_stations`) or lumped at the body masses' centroid where there is
  no outline. Flight cases only; the ground families have no aero.
- `derived_geometry.body_drag_waterline` — the single owner of `z_b`, the only
  free parameter of the load, with a **two-branch** resolution order (explicit →
  wing reference plane with a loud `assumed` note).
- New input `LayoutInput.body_drag_waterline_z` (schema **v49**, additive, no
  migration hop); `BalancedCaseResult` gains `body_axial` and `delta_cd`.
- The per-fixture pitch ceiling retired: `_PITCH_RESIDUAL_CEILING` →
  `_PITCH_RESIDUAL_RATCHET`.

**Test / Acceptance.** Gates G1–G10 of the design note, in `tests/test_balance.py`:
the applied axial resultant equals the trim's `dx` and `delta_nx` equals `dx/W`,
both to 1e-9; ground cases carry no `body-axial` load; the `ΔC_D` band is pinned
per fixture **and asserted negative below `α = 15°`** (the assertion with physics
in it — the wing strips must carry strictly less axial force than the whole
airplane while the strip model is trusted); the waterline is `assumed` with its
note, and entering one moves every residual by exactly `(z_new − z_cg)·fx`, which
is the drift guard that `assemble` reads the owner. Pitch residuals: ga6
0.075/0.014/0.018 % and RJ 0.086/0.069/0.030 % (symmetric/lateral/unsym trim
half) against a flat 1 %. Imperial baseline moved in `csv/balance`, `txt/balance`
and `sbeam/balanced_deck` only, on the two fixtures with balanced cases; every
per-component deck and every Appendix A oracle byte-unchanged. Suite 1705 passed.

**Key decisions.**
- **D-1, the one the step turns on.** `z_b` is *stated*, not derived, and its
  fallback is the wing reference plane. The draft rationale — "default to `zw`
  because it is residual-neutral" — was **withdrawn on review**: it optimises a
  validation number rather than a load position, and is self-defeating, since
  placing the load at any height makes `residual_fx` equal `dx` by construction.
  The rebuilt rationale is that the suite has no body-centreline datum at all
  (`FuselageSection` carries no `z`), so `zw` — the trim's own assumption — is
  what a project that has not stated where its body is can honestly assert. It is
  also the most robust point: the residual is zero there and linear either side,
  so `zw` sits at the **centre** of the band in which every gated case passes
  (±10.6 in on the RJ, ±8.0 in on the ga6), and a later measurement replaces it
  without re-baselining anything.
- **No `root_waterline_z` branch.** The obvious geometric candidate is the *wing*
  root; deriving from it puts `ga6_normal`'s `SIDE GUST` at −1.173 %, over the
  gate on the Appendix A fixture. It would also be a trap: that fixture carries
  `fuselage_height = 0.0`, so a geometry-conditioned branch would flip the first
  time a fixture gained a body — a fixture-data change silently moving a gate.
- **Placing it at the body's mass centroid would make the residual worse**, not
  better (RJ SIDE GUST 1.586 % → 1.881 %). The trim lumps the whole
  airplane-less-tail force system at `(xw, zw)` and is oracle-locked to Appendix A
  p179, so it cannot be met halfway. This is why the placement needed a decision
  rather than an obvious answer.
- **Negative (forward) values are reported, not clamped** (D-4). Above `α ≈ 19°`
  on the RJ the strip model's induced drag overshoots the polar and the
  correction comes out forward. Clamping would reopen the axial gate and hide the
  overshoot; it is carried as a case note and filed as its own observation.
- **`ΔC_D` is reported per case** (G10) because carrying the load necessarily
  removes the drag cross-check from the residual. It is the measurement that
  identified the defect and it stays visible.
- **The load is named `body-axial`, not `body-drag`**, since at those high-`α`
  points a card labelled "drag" would point forward.

**The balanced-case residual floors are correctly attributed (complete
2026-08-15, tier S)** — the element-count study backlog Pri 5 asked for was run:
the pitch residual is flat in `elements` (RJ PLAA 1.041 % from 20 to 640) and an
exact three-term identity shows it is `(zw − zcg)·(ΣFx_wing − dx)` — the
assembled model carries no non-wing drag — refuting both plan 11 R3 and M4-19
(a free couple cannot change a resultant), and the same missing load is the `nx`
gap; the `Fz` floor keeps R3's identification but loses the "quadrature" name
(converges to −42.3 lb / 0.327 % on ga6 PHAA), and the lumped fuselage `Cm` is a
sign-changing slope term (−8.5 to +5.8 %), not "+4.3 to +6.3 %, positive".
Pri 5 re-titled and left open; docs and docstrings only.

**The package tree is as-built, single-owner and guarded (complete 2026-08-15,
tier S)** — 0.6.0-candidate review finding R6-D5, the last of the pre-0.6.0
block. `PROJECT_GUIDE.md` §4 stopped being the restructure-era *proposal* and
became the shipped tree: every `sloads/` module with a one-line purpose, the
three `export/` lines un-nested from under `mass_distribution.py`, and the cycle's
SSOT owners (`cg_cases`, `safety_factors`, `gear_loads`) plus the older
omissions (`case_ids`, `rigid_body`, `tail_geometry`, `aero_curves`,
`migrations`, `load_keys`, `derived_geometry`, `equilibrium`,
`conventions_tex`, the `models/` split, `balance`/`tail_span`/`body_loads`) all
present. `00_program_overview.md`'s second, staler copy became a shape summary
plus a link (user decision: one owner — two trees is one more than can be kept
true). The guard is `tests/test_package_layout.py`: it rebuilds each path from
the tree's own box-drawing indentation and compares with the package on disk
both ways, so an unlisted module, a stale line and a mis-nested line each fail,
and the deleted second tree cannot return. Verified by mutation in both
directions. Scope is `sloads/` alone (user decision): `app/views` is already
generated from `workflow.py` and guarded there, and `tests/`/`examples/` churn
without telling a reader anything about where the single sources live.

**The ground family is in the balancing-method document (complete 2026-08-15,
tier S)** — 0.6.0-candidate review finding R6-D7: `20_theory/balanced_cases.md`
described three families where four ship. It now has **§9 — the ground families
(FAR 23.471–23.499)**: what a ground case does not have (no V-n point, no given
load factor, no balancing tail load, its own design weight per 23.473(a)), which
of LANDLOAD's 33 cases assemble and why 25–33 do not, the applied set
(`gear-main`/`gear-nose` with the exact patch→node transfer, `ground-lift` along
the ground line on cases 1–12 only), the solve at `n_z = 0` against FAR 23.471
with the `NVP`/`NDP`/`NS` identity and its rotational half, `ρ` measured from
LANDLOAD's own two resolutions with the ground-roll-attitude decision of record
linked, **why `RESIDUAL_GATE` does not apply** and the gates that replace it, and
a worked example over three families on `ga6_normal`. §2/§3 gained the ground
rows and the not-gated bullet; the old §9 pin table is §10 and gains ten ground
rows. Per the document's own contract every quoted figure is pinned:
`test_the_ground_worked_example_is_pinned` and
`test_the_worked_examples_contact_patch_is_where_the_prose_says` (new, in
`tests/test_gear_report.py`) hold the table, the lever arms, the two
lift-moment percentages and the side twin's mirrored field. Docs + test only.

**`balance` and `tail_span` are specified, and the spec is guarded (complete
2026-08-15, tier S)** — 0.6.0-candidate review finding R6-D6: the two registered
modules with no `PROGRAM_SPEC.md` section — the one carrying the mission's
primary deliverable and the one carrying steps 7–9's physics — now have theirs,
on the document's own template and citing the plan docs rather than restating
them (user decision: template + link out; the ground family's narrative stays
with R6-D7's `balanced_cases.md` work). Made structural per practice 3:
`sloads/spec_names.py` is the single owner of the registry-name → spec-heading
correspondence (`weight_estimate` → `WTESTIMA`) plus the allowlist of sections
that are not calc modules, and `tests/test_spec_coverage.py` guards it in both
directions — the guard reproduces the finding when either new section is
removed. `WorkflowStep.bas` was considered and rejected as the map's source: it
is per step, merged steps name several programs and folded modules own no step.
Docs + test only; no shipped number moves and no digest channel changes.

**G-6's rotational gate half, and what it found (complete 2026-08-15, tier M)**
— 0.6.0-candidate review findings R6-T1 and R6-T2. The step-10 benchmark had
shipped with its translational half only; the three moment lines the design note
promised now exist in
`test_the_ground_closure_reproduces_landloads_unbalanced_moments`, which takes
the solved `[I]{ω̇}`, transfers it from the mass centroid to the CG, subtracts
the G-7a lift term rebuilt in closed form, moves the applied reactions to the arm
point each family's own LANDLOAD formula measures to, rotates into the ground
line and compares with `PITCHP`/`ROLLP`/`YAWP` — an identity at `rel_tol 1e-9`
on the one-wheel family's tread arms, within `1e-4·W·MAC` elsewhere (the BASIC's
3-decimal arm truncation). `NS` is now compared signed (R6-T2).
`InertiaTensor.moment()` is the new owner of `[I]{ω̇}`, guarded beside `solve`.
A negative control pins both corrections as non-trivial (12.5 % and 5.8 % of
`PITCHP` on `ga6_normal` case 4). Test-only: nothing shipped moved, no digest
channel changed. **The gate then did what the note said it would**: it found
that `LANDLOAD.BAS` resolves the ground-roll attitude at `PHIM = +BETA(2)` where
the other two attitudes carry `−GRA`, so the 23.485 family's own `ROLLP` and
`YAWP` are stated 9.45° apart on `ga6_normal` and cannot both be reproduced by
one rotation. The port is faithful to the BASIC, and the user decided the same
day to **keep the manual's convention as a faithful replication** — recorded
under "Considered and declined" in `20_theory/02_approved_corrections.md`, with
the state pinned per attitude on all five gear fixtures so it cannot drift.

**A ground case's source case is named as LANDLOAD's, not as a V-n point
(complete 2026-08-15, tier M)** — 0.6.0-candidate review finding R6-C3: the
wording of `BalancedCaseResult.vn_case` gained one owner
(`balance.source_case_name` / `case_source_name`, family from `is_ground`,
registered in the `CONVENTIONS.md` §7 SSOT table), and all five surfaces the
review named go through it — deck `$` header, deck case map, `run()` titles,
the rows table (column re-headed `Source case`, family-aware value) and
`SkippedCondition.name` (which gained a `ground` field). Swept alongside: the
shared `no-cg-case` skip reason and the Balanced Cases selector's ground hand.
Display wording only. Pinned by
`test_no_surface_calls_a_ground_case_a_v_n_point` (all five surfaces, both
ground fixtures, flight wording pinned too) and
`test_the_source_case_label_has_one_owner`. Digest wave: `txt/csv balance` +
`sbeam/balanced_deck` on the two ground fixtures — one channel wider than the
backlog row declared, because two surfaces live in the deck.

**Gear report CSV meets the load-output contract (complete 2026-08-15,
tier M)** — 0.6.0-candidate review finding R6-C2, with the R6-C4 hygiene row
folded in by user decision: the `gear_report` channel's header row is now built
from the resolved unit set (`-ULT` on every load column, plain force unit on
the two weights, the SI `Stroke` header no longer hard-coded `(in)`), every row
states its `SF` (last column), and a `Wheel` column says which wheel a `main`
row describes (starboard of the pair; port is the mirror). Hygiene:
`balance.gear_sets` dropped its unused `nvp` parameter; `_gear_stroke_table`
docstring paste blemish removed. Pinned by an Imperial contract test and the
SI-channel assertion whose absence let the defect ship; spec: the `gear_loads`
PROGRAM_SPEC section's Writes bullet. Digest wave `gear_report` on the five
gear fixtures, exactly as declared.

**Ground condition rows cite their own FAR condition (complete 2026-08-15,
tier S)** — 0.6.0-candidate review finding R6-C1: `balance.run()` ground rows
now read the case's `CaseRef.far_reference` (23.479…23.493) instead of the
flight-balancing literal 23.321; flight rows keep their literals by design;
pinned per ground fixture; digest wave `txt/csv balance` as declared.

**Documentation currency batch (complete 2026-08-15, tier S)** — 0.6.0-candidate
review findings R6-D1/D2/D3/D4 (`docs/50_reviews/2026-08-15_review_0_6_0_candidate.md`):
changelog `[Unreleased]` headings unscrambled, backlog "shipped since the tag"
gains step 9 + D-24, plan 09 marked closed, `00_INDEX.md` gains plans 14 and 18.

**Backlog priority re-cut + decision D-25 (complete 2026-08-15, tier S)** —
the priority table re-banded to the restated objective (ship the sbeam
deliverable), with the open defects and the unscheduled 0.5.0 review findings
interleaved by severity and the table renumbered 1–36; **D-25** answered the
outstanding `CgCase` question in favour of an explicit loading definition over
rewriting the fixtures' CG corner points, promoting it to Pri 9 and unblocking
its two sibling coverage items.

## Step 10 piece 3 — ground/landing cases + the gear load report (complete 2026-08-15, tier L)

**Objective.** The last piece of M4-6, and the one that **absorbs step 11 (plan 11
B8b)**: put the FAR 23 ground conditions into the assembled free-free deck as
balanced cases, and give the gear a deliverable of its own. Design note:
[`../30_future/18_step10_ground_cases_plan.md`](../30_future/18_step10_ground_cases_plan.md),
decisions **G-1, G-6, G-7 (+G-7a), G-8, G-9, G-12 (+G-12a), G-13**.

**Deliverables.**

- `sloads/gear_loads.py` — the gear as a **free body**, and the single owner of
  everything geometric about it: the per-attitude contact patch
  (`x + r·sin GRA`, `z − r·cos GRA`, compressed axle for cases 1–12 and static for
  13–33), the strut stroke recovered from the three entered axle states, the
  ground-line ↔ airplane-datum rotation `ρ`, the resultant-preserving transfer to
  the reference point, and the wheel placement an assembled case needs.
- `modules/balance.assemble_ground` + `build_ground_cases` — the ground family,
  sharing `_closure`, `body_inertia`, `resultant6`, `point_mass_self_inertia` and
  the new `wing_inertia_strips` / `place_wing_inertia` (factored out of
  `wing_sets`, behaviour-neutral) with the flight families. Plus
  `ground_lift_sets`, `gear_sets`, `is_ground`, and two new `SKIP_REASONS`
  (`gear-design-only`, `side-twin-by-reflection`).
- The **gear load report**: `export.gear_report_csv` / `gear_report_rows`, report
  §8 with the strut-state table, a manifest row, the Landing Loads page's free-body
  section, and the CLI's `--export-target gear`.
- Schema **v48** — `LandingGearInput.weight_lb` (G-12a), additive, `0.0` = not
  stated, no migration hop. Two result types gain fields that existed only
  implicitly: `GearReactionCase.weight_lb` (the design weight the case is computed
  at) and `BalancedCaseResult.cg_x`/`cg_z` (the point its residuals are stated
  about).
- `export/bands.py` gains the **`balanced-gear` GID band** (10001+) so a gear node
  is findable by id rather than by coordinate; `case_ids.balanced_subcase_id` and
  `deck_load_id` take the case's **hand explicitly** (G-8).
- Fixture data: leg weights on five airplanes × two legs, **per leg** — half the
  database's main-gear rows, all of its nose-gear rows.

**Test / Acceptance.** `tests/test_gear_report.py` (44 tests) is the step's
benchmark-first gate; the whole suite is green (1670 passed / 21 skipped), lint
clean, and the **real solver** leg passes in 16.5 s with the solve count roughly
doubled — G-13's "one cost to check rather than assume", answered.

- **The closed-form gate is an exact identity** (G-6). The solved rigid-body
  field, rotated back to the ground line, reproduces LANDLOAD's `NVP`, `NDP` and
  `NS` on **every** case of both fixtures at `rel_tol 1e-9`. Two completely
  different routes — a mass matrix here, lever arms and FAR percentages there —
  one answer.
- **The transfer preserves resultants exactly** (G-2's third guard, the one it
  owed this piece): worst relative moment error **3.4e-16** over all 33 cases and
  both legs, taken about a deliberately arbitrary reference rather than the CG,
  where a dropped couple could cancel against something.
- **Two negative controls**, per G-13: dropping the offset couple breaks the
  transfer, and computing a level-landing case at the *static* contact patch
  breaks the moment gate. The second is asserted on the **moment**, not on `NVP`
  — moving the patch does not change the vertical force factor, so a control
  watching `NVP` would have passed and proved nothing.
- **G-13's ground-specific solver assertion**: the reaction sbeam recovers at each
  gear GID is the gear report's reference-point reaction, in both unit systems.
  This is what stops the inherited "reactions ≈ 0" leg passing vacuously — a
  transfer that dropped its lever arm *consistently* would still sum to zero at
  the support.
- **LANDLOAD's own twins check the reflection operator** (G-8): `reflect(19)`
  reproduces case 20's `NS`/`ROLLP`/`YAWP` sign-flipped and equal. Every other
  reflection in the suite is guarded against itself; this is the only external
  check it will ever get.
- **Coverage is pinned twice and the two sets differ by design**: assembled ground
  cases on **2** fixtures (ga6 3/3 loadings, the RJ 2/3 — the already-pinned Pri 9
  fixture-data finding, inherited not created), the gear report on **5**.
- The digest wave is exactly G-13's stated expectation: `sbeam/balanced_deck` +
  `case_index` on ga6 and the RJ, a **new** `gear_report` channel on five
  fixtures, and `csv/landing` + `txt/landing` on five from the case-labelling fix
  below.

**Key decisions.**

- **G-7a — the lift acts along the ground line, not along airplane `z`.** Raised
  by implementation, because G-7's wording and G-6's promise of an exact gate
  could not both hold: LANDLOAD sums `lf·WL` into the *ground-line* vertical, so
  a lift on `z` enters that sum short by `cos ρ` — 0.053 % of `NVP` on ga6, small
  and *not* solver noise. It is also the physics: lift is perpendicular to the
  flight path, the ground line is the flight path at touchdown, and the airplane
  sits at `ρ` to it (152 lb of ga6's 2,154 lb lift acts forward).
- **`ρ` is taken from LANDLOAD's own two resolutions of one reaction**,
  `atan2(dm, vm) − atan2(DMP, VMP)`, not re-derived from `GRA`. That means this
  step never has to adjudicate a sign inconsistency that is in LANDLOAD.BAS
  itself — `beta` is `gamma − GRA(1)` for the level attitude and `+GRA(2)` for
  the ground-roll one — and the rotation appears only in the **check**, never in
  the load path.
- **G-12a — the leg weight is an input, one number per leg.** Nothing marks a
  `weight.items` row as gear; on every fixture they are identifiable only by name,
  and matching on that is the `LANDING_CG_NAMES` failure mode G-3a had just
  retired one layer up. Deliberately *not* a sprung/unsprung split: only the
  unsprung mass sees the impact amplification that sizes an axle, and sloads does
  not model that, so entering the split would imply a capability the tool lacks.
- **A correction to G-12's own arithmetic.** The note read "155 lb → 491 lb, 12 %
  of a 4,038 lb reaction", pairing the **whole main gear** with a **per-wheel**
  reaction. `weight_lb` is therefore defined per leg (consistent with `attach`,
  likewise one leg's node), ga6's main leg is 77.5 lb, and the real figure is
  **6.1 %** — still far too large to leave out of a free body, which is what the
  paragraph exists to argue.
- **The report and the assembled deck carry different case sets, and say so.**
  33 against 24. The 23.499 family is not merely excluded from the assembly, it
  has a home.
- **What the report is not travels with it**, in the CSV stamp, the report
  section and the GUI: no gear kinematic model, so no drag-brace, side-brace,
  trunnion or axle-bending loads. Overstating it would be the "a wrong card
  outranks a missing card" failure in its purest form.

**Two defects found on the way, both fixed here.** The per-case record labelled
the wrong loading on five of the six 23.485 side cases (`(m-1) % 3` against a
family that is three loadings × two drift directions) — cosmetic, so no load ever
moved, but it is the label a reader joins on and it matters now that the assembled
case builds its inertia set from it. And `is_handed` tested "any load carries a
free moment" where it meant the net, which minted every symmetric level-landing
case handed once both wheels carried a transfer couple.

## Step 10 piece 2 — the weight/CG case model + gear inputs (complete 2026-08-14, tier L)

**Objective.** Land the whole schema hop decisions G-2/G-3/G-4/G-5/G-14 imply as
**one** `SCHEMA_VERSION` bump rather than four, and prove it moves nothing. Three
weight/CG case lists and six representations of MTOW become one owner each, so the
ground-case physics (piece 3) has inputs to consume instead of inventing them.

**Deliverables.**

- `sloads/cg_cases.py` — the one resolver. `cases_for` / `flight_cases` /
  `ground_cases` / `landing_role_cases`, `max_landing_weight` /
  `max_takeoff_weight` / `max_landing_weight_estimate` / `database_total`, and
  `seed_landing_cases` (the WTENV seed, moved out of the Landing Loads view into
  the calc package where it can be tested as a function).
- Schema **v47**. `CgCase.analyses: Set[AnalysisKind]` (`FLIGHT` | `GROUND`,
  default `{FLIGHT}`) and `CgCase.role: Optional[GroundCaseRole]`;
  `WeightInput.max_landing_weight_lb` / `.max_takeoff_weight_lb`;
  `MassItem.consumable`; `LandingGearInput.carrier` (no default) / `.attach`.
  **Removed:** `FlightLoadsInput.cg_cases`, `LandingInput.cg_cases`,
  `LandingInput.gross_weight_lb`, `LandingInput.max_landing_weight_lb`.
  New enums `AnalysisKind`, `GroundCaseRole` (+ `GROUND_CASE_ROLE_ORDER`),
  `GearCarrier`.
- `migrations._v46_cg_case_model` — tags existing `weight.cg_cases` `FLIGHT`,
  folds `landing.cg_cases` in as `GROUND` with roles from the canonical names
  (merging onto an existing case where name **and** `(weight_lb, xcg, zcg)`
  match), moves MLW across, and seeds MTOW from `speeds.weight_lb`. It also
  recovers a pre-v19 file whose cases live only on `flight_loads` and that carries
  no `weight` dict — a case `_v19_cg_cases` gave up on.
- `landing.py` reads the roled cases and takes `mlw`/`mtow` as explicit arguments;
  every flight consumer (`select`, `flight_envelope`, `balance`, `balloads`,
  `tail_span`, `wing_inertia`, `mass_distribution`) reads `flight_cases(project)`.
- `mass_distribution.derive_case_loadings(project, cases=None)` is generalized to
  any case list, with the **G-5 burn-down** path for `GROUND` targets
  (`_burn_down`: one fraction applied to every `consumable` row, so a tank layout
  survives).
- Validation: `_check_weight_case_model` (`cg_case_no_analysis`,
  `cg_case_role_without_ground`, `ground_role_incomplete`, `weight_order_chain`,
  `mlw_below_landing_estimate`, `mtow_representation_drift`) and
  `_check_gear_carrier` (`gear_carrier_unset`, `gear_carrier_mass_disagrees`,
  `gear_attach_missing`, `gear_attach_off_the_wing`).
  `_check_landing_hierarchy` loses `gross_ge_max_landing` and `landing_cg_names`
  with the fields they policed and gains `landing_case_weight_is_mlw`.
- GUI: the **Payload Cases** tab becomes the sole editor (`FLIGHT`/`GROUND`
  checkboxes, a landing-`role` selectbox, and the WTENV seed on a button); the
  **Weight / CG Envelope** tab owns MLW and MTOW and shows the derived MLW
  estimate; the mass-item editor gains a `consumable` checkbox; the **Landing
  Loads** page's CG table and both design weights become read-only.
- Fixture data: `carrier` + `attach` on five airplanes × two legs, and the mission
  fuel row tagged `consumable` on each.

**Test / Acceptance.** `tests/test_cg_cases.py` (43 tests) is the drift guard.
The whole suite is green (1614 passed / 21 skipped) with **`digests.json`
unchanged** — the piece's stated expectation, "nothing moves", and if something
had, the migration would not be output-neutral. Specifically pinned:

- The `FLIGHT`-tagged set after migration equals the pre-hop
  `flight_loads.cg_cases` **exactly, per fixture**, compared against the file on
  disk rather than a re-derivation (G-3b's stated guard). Likewise the `GROUND`
  set against the pre-hop `landing.cg_cases`.
- MTOW agrees with every representation it replaced, per fixture, and is *not*
  the heaviest landing case (3,400 against 3,230 on ga6) — the latent `WR = 1.0`
  defect, pinned so it cannot return.
- The role fixes the order: reversing the entry order changes nothing, renaming
  every case changes nothing, and a missing or duplicated role **raises**.
- G-5, reproducing the plan's measurements exactly: ga6's aft landing case burns
  **317 lb** of fuel, needs **no ballast** and lands **0.12 in** from its target;
  burn-down is proportional across two tanks; and marking *every* item consumable
  leaves every flight loading unchanged on all six fixtures — the acceptance test
  for the field, and why the Appendix-A oracles cannot move.
- Ground-loading coverage is exactly what G-3/G-5 predicted: ga6 3/3, the RJ 2/3,
  `cessna_210` / `atr42_100` / `dhc8_dash8` 0/3, each skipped and recorded.
- The MLW floor fires on `concept_regional_jet` **and no other fixture**; the
  carrier ↔ mass guard fires on `dhc8_dash8` **and no other fixture**. Both are
  asserted as set equalities, so a second fixture drifting into either is a red
  build rather than a longer warning list.

**Key decisions.**

- **The removals are the point.** A proxy field would have left a second way to
  say the same thing, which is what G-3 exists to remove (the G6b single-source
  precedent, deliberately not the `tail_loads` proxy precedent). That is also why
  this hop needs a migration where v44-v46 did not: absent is *not* the old
  behaviour for a removed or relocated field.
- **`max_takeoff_weight` keeps a documented fallback chain** to
  `speeds.weight_lb` → `weight.envelope.gross_weight` → the heaviest `FLIGHT`
  case. A loaded project never reaches it (the hop seeds the SSOT); a
  directly-constructed test project does. `mtow_representation_drift` is what
  keeps it a compatibility path rather than a second authority.
- **Two findings are left firing rather than fixed here**, because fixing either
  moves output and this piece is claimed as "nothing moves": `dhc8_dash8`'s gear
  mass tag (correcting it re-pins `mass_distribution.wing_mass_tie`) and the
  `applicability` / `direct_totals` design-weight re-point (believed at the time
  to change the FAR 23 exceedance line 37,781 → 36,817 on atr42 and 34,800 →
  33,000 on the RJ — **measured 2026-08-15, it does not**: both fixtures set
  `speeds.weight_lb`, which won ahead of the database branch, so the defect was
  latent rather than shipped-wrong; see that item's own entry above). Both are
  in the backlog with the guard that found them.
- **The `atr42_100` sponson and the RJ's wing-body junction are `BODY`**, stated
  rather than guessed: a sponson is a fuselage fairing and an RJ's main-gear
  trunnion lands on the keel beam in the wing-body fairing. `dhc8_dash8` is the
  `WING` fixture — gear in wing-mounted nacelles — and so is the one that will
  prove the wing load path in piece 3.
- **G-2's third guard is deferred with its subject.** "The transfer preserves
  resultants about the CG at `rel_tol 1e-12`" tests the transfer, which lands with
  the ground export in piece 3; the two input-side guards ship here.

---

## Step 10 piece 1 — the governing safety-factor table (M4-8, complete 2026-08-14, tier L)

**Objective.** Make the factor of safety a stated authority instead of a
distributed default. Before this, `ConditionResult.safety_factor` defaulted to
`constants.ULTIMATE_FACTOR`, exactly one module (`one_engine_out`) overrode it, and
`report/content.py` twice read `getattr(item, "safety_factor", ULTIMATE_FACTOR)` —
so a factorless case was reported at 1.5 with no trace that anything had been
assumed. Sequenced **first** of step 10's three pieces so the ground family
consumes an existing authority rather than becoming a third ad-hoc factor site.

**Deliverables.**
- `sloads/safety_factors.py` — the single code owner. `LoadClass` +
  `DERIVED_FACTOR` (Layer 1: `LIMIT → 1.5`, `ULTIMATE → 1.0`, 14 CFR 23.303/25.303);
  eight `FAMILIES` rows whose boundaries are **14 CFR Subpart C's own section
  groupings**; `classify()` mapping a case to a family from its FAR reference (with
  the case ref as fallback, since the distributed component results carry theirs
  only there); `GoverningTable` with `resolve` / `factor_for` / `stamp`.
- `Project.safety_factors` (`SafetyFactorPolicyInput` / `SafetyFactorOverride`) —
  schema **v46**, additive, written only when it carries an override, no hop.
- Report **§3 Governing safety factors** (renumbering §3–§7 → §4–§8 through
  `section_ref`, which is what F-R2 built it for), the case index's `SF` column
  re-pointed to the table, an override paragraph and a live `DEFAULTED:` line.
- `export.safety_factors_csv` / `write_safety_factors_csv`, the bundle channel
  `<project>_safety_factors.csv`, and its manifest row.
- `report.methods._safety_factor_block` — the override declaration, silent when
  there is nothing to declare.
- `validation._check_safety_factor_overrides` — unknown family, missing basis,
  out-of-band factor, and the below-regulation **certification-risk** warning.
- Docs: `CONVENTIONS.md` §3 (the owner named), `CLAUDE.md` load-output contract,
  `00_program_overview.md`, `PROGRAM_SPEC.md` (SELECT notes + the export SF note),
  `00_theory_sources.md` (the family/citation table), `GUI_design.md` v46,
  `DATA_DICTIONARY.md` regenerated.

**Test / Acceptance.** `tests/test_safety_factors.py` (37 tests). The authority
claim is **reproduction, not assertion**: for all six shipped fixtures, case by
case, the table resolves exactly the factor the producing module mints — including
`one_engine_out`'s 23.367(a)(2) at 1.0 — and **no case falls through
unclassified**. A defaulted case in any shipped fixture is a red build, which is
what stops "flagged" from normalising. Also pinned: an exact row beats the range it
sits inside (23.367(a)(2) is an ultimate case inside the limit flight range, and
double-factoring it was the live risk); a multi-section reference whose families
disagree on a factor is left unclassified rather than decided by word order; an
override reaches the carrier, the case index, the companion CSV and the methods
stamp together. **No shipped fixture carries an override, no digest moved, no
number changed.** Suite: 1561 passed, 21 skipped; ruff clean.

**Key decisions.**
- **G-10** — every FAR ground case is limit × 1.5, read from the CFR text rather
  than inherited from the default; the deliverable can now say why.
- **G-11** — the table is the authority, at **condition-family** granularity, and
  is **fully user-editable including the regulation rows** (user decision, taken
  against the recommendation, with the risk stated). Safe for the oracles — the
  factor is applied at the render/export boundary only, so no override can move an
  Appendix-A figure — but *not* for the deliverable, so the four mitigations are
  part of the decision: an override is never silent, must state a basis, warns when
  below the regulation, and no shipped fixture carries one.
- **An unresolved case defaults to 1.5 and is flagged** rather than raising (user
  decision), with the zero-defaulted-rows test as the guard against drift.
- The **carrier stays the carrier** (M4-8's original design): the table *writes*
  `safety_factor` at `registry.run_all_modules`, `component_loads` and
  `balanced_run` rather than replacing the field, so ~18 `_sf()` call sites in the
  export bridge and every report reader needed no change — and an override cannot
  reach the report without also reaching the cards.

---

## Pressurization removed from scope (decision D-24 — complete 2026-08-14, tier S)

User decision, taken while scoping step 10 (M4-6): **pressurization is out of
scope for sloads, permanently.** The `pressurization` standing limitation is
reworded from "No pressurization load cases." — which reads as pending — to an
explicit exclusion naming 23.365/25.365, disclaiming the deliverable as a
complete set for a pressurized fuselage (four shipped fixtures are pressurized
airplanes), and separating it from the unrelated WTESTIMA `pressurized`
weight-allowance flag. The key stays in the pinned `STANDING_LIMITATION_KEYS`
set; `tests/test_methods_stamp.py` gains a guard that the sentence reads as an
exclusion. M4-6 is re-scoped to the ground/landing distributed loads and gear
reactions alone, and **F25-5** loses its ΔP-combination half (§1.8's 25.365 row
becomes disposition **X**), keeping only the 23.415/25.415 ground-gust module.
One consequence is carried forward rather than assumed: the old "for a
pressurized airplane, ground cases cannot be down-selected against flight" rule
leaves with the case, so the ground-case down-selection question is now open for
step 10's design note. Docs synced: backlog row + M4-6 body,
`03_gui_rework_plan.md` (§3 table, Phase 4, §5 item 3, §6),
`01_far25_gap_analysis.md` (§1.8 + F25-5), `02_parked.md`,
`05_step_g8_summary_report_plan.md` §6, `03_resolved_decisions.md` (D-24).

---

## Mission step 9 — discrete control surfaces + the T-tail transfer (plan 09 T6–T8, complete, 2026-08-13)

**Objective.** Close plan 09's phase 2, the two load paths its phase 1 left
unstarted: a control surface whose load reaches the parent surface through
**hinges and an actuator** rather than smeared into it — producing the suite's
first hinge-moment output — and a **T-tail** whose fin deck carries the
horizontal tail it is holding up. Tier L (new physics, schema change, new result
types), design note agreed in chat first as
[`plan 09 §10`](../30_future/09_distributed_empennage_loads_plan.md).

**Deliverables.**
- **T6 — the discrete control-load path.** `control_load_mode = "discrete"`,
  per surface, with new `TailMassInput.hinges_span_in` / `.actuator_span_in`
  (`SCHEMA_VERSION` 45, additive, no hop). The control surface's own load leaves
  the smeared strips over the span its hinges hold and re-enters at dedicated
  `GRID`s on the load reference axis: hinge reactions by chord-weighted
  tributary span, and the hinge-moment couple at the actuator. New GID bands
  `tail-control-htail` 5001-5300 and `tail-control-vtail` 5301-5600, registered
  in `export/bands.py` like every other family. New result types
  `ControlPointLoad` and the `TailSpanResult.control_loads` /
  `.control_surface_load_lb` / `.hinge_moment_lbin` / `.hinge_moment_arm_in`
  fields, surfaced on the **Tail Span Loads** page, in the module's own
  `LoadValue`s and in the deck `$` header.
- **T7 — the T-tail transfer.** `TailType.T_TAIL`'s first load-path consumer.
  Each v-tail case's deck carries, at the fin's **last** node, the concurrent
  h-tail set (balancing load at that case's own V-n point plus `−n·W_ht`) as a
  vertical `FORCE` and the `MOMENT` its two lever arms make. New `TipTransfer`
  result and `coordinates.ttail_transfer_to_airplane` — the one load in a fin
  deck that is not in the fin's local frame, so it gets its own named map.
- **`select.py` gained two part-returning helpers** (`elevator_load_parts`,
  `rudder_load_parts`) whose sums are the existing expressions in the existing
  order, so the oracle-locked `elevator_load` / `load_on_rudder` values are
  unchanged to the bit and the discrete path has one producer to read rather
  than a second copy of the arithmetic. `taildist._surface_geom` became public
  (`surface_geom`) so the hinge line has one owner across the two tail views.
- **Closure trail:** `CONVENTIONS.md` (two SSOT-table rows + five prose bullets:
  the two control-load paths, the hinge-moment arm, and the T-tail transfer
  reference point), `PROGRAM_SPEC.md` (two module/deck rows),
  `theory_sources.md` (both gate tables as the R10 oracle substitute),
  `GUI_design.md` (v45), regenerated `DATA_DICTIONARY.md`, `cspell.json`.

**Test / Acceptance.** Ten new gates in `tests/test_tail_span.py` and a rewritten
v-tail row in `tests/test_export_equilibrium.py`. The strong ones:
- **Cross-mode force identity, exact** (`rel_tol 1e-12`, both surfaces, every
  condition) — a property of the construction, since exactly the control load is
  removed and exactly it is applied. Distributing the removal by the raw strip
  fractions would have rested the identity on `Σ frac == 1`, which is exact for a
  derived rectangle and only 1 %-true for an entered polyline: the T1 validator's
  own tolerance, quietly become a load error.
- **The hinge moment against its closed form**, `HM = L_cs · c_e/3` — 4.856 in of
  arm on ga6, hand-derived in the test from `Saft/S = 0.40039` of a 36.388 in
  chord.
- **Hinge torsion + actuator couple = the control load at its own CP.** Reverse
  the actuator's sign and the sum lands on the hinge *line* instead — a 4.86 in
  chordwise error with nothing else in the deck to catch it.
- **The cross-mode torsion difference as an identity, not a tolerance**: exactly
  the chordwise relocation `att·x_25 + cam·x_50 − L_cs·x_cp`, printed as the
  physical explanation. Plan §5's T6 asked only for "within a stated tolerance".
- **T7's free-body gate**, read from the deck's own card text: the fin deck's
  resultant about the origin is the axial column at its own stations plus the
  transferred set at the node it is stated to be applied at.
- **Gating and mode isolation, byte-level**: flip `tail_type` back to
  conventional and the deck returns exactly; no shipped fixture carries hinge
  geometry, so every smeared deck is unchanged. Imperial digests moved on
  **three** channels of one fixture only (`concept_regional_jet`'s
  `sbeam/vtail_span_cards`, `csv/tail_span`, `txt/tail_span`) — the fin's own
  station table did not.

Suite green: 1523 passed, 21 skipped; `ruff check sloads/ cli.py app/` clean.

**Key decisions** (recorded as T-12…T-17 in plan 09 §10.1, agreed with the user
before implementation).
- **T-12 — the control-surface load is SELECT's, read never recomputed.** This
  **supersedes T6's own sentence**, which said "the control part (`LT50`)".
  `LT50` is the *camber* load and its TAILDIST trapezoid runs leading edge to
  trailing edge, so hanging all of it on the hinges would move stabilizer load
  onto the elevator while ignoring the angle-of-attack share the elevator really
  carries. `select.elevator_load` (SELECT.BAS 5216-5218) is oracle-locked, is the
  load on the surface *including* its aerodynamic-balance area forward of the
  hinge, and the module contract forbids recomputing it. Where a condition
  publishes none — the balancing, checked, gust and unsymmetrical h-tail
  conditions, and the rudder-neutral fin ones — the load is derived from
  TAILDIST's aft-of-hinge block and **marked**, the derive-and-mark contract the
  tail planform is already under.
- **T-13 — the hinge-moment arm is exactly `c_e/3`**, not an approximation:
  TAILDIST's net trailing-edge pressure is identically zero (`WATT3 = WCAM3 = 0`),
  so the block aft of the hinge is always a triangle, whatever the condition.
- **T-14 — the removal is normalised**, so the force identity is structural.
- **T-15 — the actuator carries a couple, not a force.** With no horn radius in
  the schema a rotary actuator is the honest model, and it is what makes the
  chordwise identity exact.
- **T-16 — the transfer set is `Fz` and `Myy` only.** The T-5 pairing is a
  *balancing* condition, which is symmetric, so the h-tail's halves cancel about
  the centreline; a transferred `Mxx` would be a number with no producer.
- **T-17 — no shipped fixture gets hinge geometry.** Inventing hinge stations for
  six aircraft with no oracle is the fabrication §9.1 refused for the tail
  polylines. The discrete gates run against a project the test builds, and every
  shipped deck stays byte-identical in the mode nobody changed.

**Measured, and worth recording.** The fin is shorter than the h-tail's semispan
(57.0 in against 73.1 on ga6), so the first version of the cross-mode test —
written with one set of hinge stations for both surfaces — was refused by the
new validator rather than silently accepted. That is the validation working on
its author.

---

## Release cut: **sloads 0.5.0** (the assembled free-free deliverable), tag `v0.5.0`, 2026-08-13

**Objective.** Close the review of record's Phase 3 (release mechanics) and cut
the release decision **D-R1** had held for the deliverable — the summary report
plus wing/body/tail and balanced/CONM2 sbeam output. `[Unreleased]` had grown to
~900 content lines across three review phases; unreleased work has no regression
baseline.

**Deliverables.**
- **Workbook per-sheet unit statements** (review **m14**, tier M). One `.xlsx`
  carries both unit channels — module and case-index sheets are HUMAN, span-load
  sheets are the SOLVER channel the sbeam decks use — and in SI those sets differ
  (`N·m`/`kPa` vs `N·mm`/`MPa`), so the single Project-sheet `Units` row
  mis-stated every span sheet by 1000× in moment (SUMMARY_REPORT.md §3.5/§4.7:
  "a per-file units column that disagrees ... is a conformance failure, not a
  footnote"). `build_workbook` now **owns** the statement instead of taking a
  pre-formatted one from the page: it resolves both channels once from the
  `system` it is given, writes each data sheet's own set into cell `A1` above
  that sheet's header row, and names both channels plus the unconverted KEAS/ft
  exception on the Project sheet. The case index, carrying no load quantity,
  states that rather than claiming either set.
- **`app/` joined the lint gate** (review **m21**). The merge gate left the whole
  Streamlit layer unlinted and it had drifted — an unused `build_tail_span`
  import in `export_report.py`. Now `ruff check sloads/ cli.py app/` in CI and in
  every document that states the gate (`CLAUDE.md`, `00_program_overview.md`,
  `RELEASE_PROCESS.md` §3.2, `CODE_REVIEW_PROCESS.md` ×2, `PROJECT_GUIDE.md`,
  `README.md`).
- **Root cleanup** (review **m19**). `.DS_Store` gitignored and untracked;
  `CODE_REVIEW_2026-07-21.md` and `PROJECT_REVIEW_2026-07-19.md` moved to
  `docs/50_reviews/` and indexed in `00_INDEX.md` (which also gained the
  2026-08-10 code review, previously unlisted); `requirements.txt` **deleted**
  rather than regenerated — a second dependency source that had already drifted
  from `pyproject.toml` (streamlit ≥1.30 vs ≥1.36, listing pytest, omitting
  plotly and openpyxl), and one source that is right beats two that disagree.
  `README.md` and `PROJECT_GUIDE.md` §4's tree updated.
- **Release-doc currency** (review **m20**). `RELEASE_PROCESS.md` §1 pointed at
  the pre-M3-1 `sloads/models.py` for the schema version — now
  `sloads/models/project.py`, and named `SCHEMA_VERSION` as the code does.
  pyproject classifiers list 3.9 / 3.11 / 3.12, the CI matrix, instead of 3.9
  alone.
- **`scripts/smoke_test.sh` fixed — the §3.5 gate failed the release it gates.**
  It read line 1 of the CLI's CSV as the header, but since G8.3 every exported
  CSV carries the methods & limitations statement as `#` lines above it, so the
  script saw `# METHODS AND LIMITATIONS` and reported an unexpected header. The
  Python readers were audited when the stamp landed (`workbook._csv_to_df` reads
  with `comment="#"`); this shell one was not — practice 4 (generalize on first
  find) applied late. It now skips comment lines, counts rows from the data
  block, and **requires** the stamp to be present, so the gate proves the
  headless deliverable states its own basis.
- **Version** `0.4.0` → **`0.5.0`** in `pyproject.toml` (MINOR: new capability,
  no breaking change — `SCHEMA_VERSION` 44 is reached by additive hops and
  `io.py` loads every older save).
- **Changelog cut** — `[Unreleased]` dated to `## [0.5.0] — 2026-08-13` with its
  **ten headings merged to three** (Added / Fixed / Changed), verified
  content-preserving as a line multiset before and after, and a fresh empty
  `[Unreleased]` opened — the same consolidation the 0.3.0 and 0.4.0 cuts
  performed. It opens with a **release-notes block** stating the four standing
  caveats a 0.5.0 deck carries: the flight-only fuselage deck (D-R3), fin-only
  lateral aerodynamics (L-7, over-stated and conservative), the handed
  23.427(a) maneuver pair (D-R8), and concept mode as closure-locked rather than
  oracle-locked (D-R6).
- **Verification baseline** —
  [`09_verification_baseline_0.5.0.md`](09_verification_baseline_0.5.0.md), a
  **delta** baseline like 0.4.0's: the closure gates for everything 0.5.0 added
  (six-DOF balanced closure, handed twins, the lateral three, the report's own
  conformance gates, per-sheet workbook units), the nine pinned exceptions with
  their measured figures, the four standing limitations, and what measurement
  changed — carrying the 0.3.0 oracle tables forward unchanged on the same two
  confirmations (register unchanged; every Imperial digest movement a new or
  renamed channel, the wave spent four times inside the release).
- **Backlog re-cut to post-release form** — the 0.5.0 row and its whole "Item
  detail — 0.5.0 release scope" section removed per the removal rule, the
  remaining 31 rows renumbered with their `Pri` cross-references followed, and
  the release prose replaced with the cut record.
- **Gates at cut:** `pytest` **1494 passed / 21 skipped / 0 failed** (coverage
  93 %), `ruff check sloads/ cli.py app/` clean, `scripts/smoke_test.sh` **PASS**
  (headless GUI render + CLI export), every skip carrying a stated reason and a
  backlog entry, no open CRITICAL/MAJOR review findings.

**Key decisions.** `build_workbook` owns the unit statement rather than
receiving it (practice 3, single owner + drift guard): the source guard in
`test_deliverable_units.py` that used to pin the *defect* (`"Units":
units_statement(` present in the page) now pins the contract — the page passes
`system=_system` and states nothing itself. `requirements.txt` deleted rather
than regenerated, for the same reason.

**Post-release.** The cadence rule (`RELEASE_PROCESS.md` §2) restarts from this
tag. Per **D-R3** the ground/landing case families (backlog Pri 4–5) are the
0.6.0 headline; the sequence-independent rows — ONENGOUT fixture data, the
wing-case-condition naming decision, M4-8 Layer 1's full resolver — ship in any
gap. `scripts/smoke_test.sh` into CI (review **m20**) remains the stated
fast-follow, not a gate.
