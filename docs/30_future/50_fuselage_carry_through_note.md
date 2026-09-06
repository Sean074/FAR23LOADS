# The wing carry-through is entered as a fuselage station

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: AGREED 2026-09-05 (owner, in session — `CLAUDE.md` rule 1's
working-alone path).** Milestone **0.8.2**;
closure tier **L** (schema hop, and the oracle input set is a stated contract —
gate G5). `CLAUDE.md` rule 1 puts this note at AGREED before code.

**The change in one sentence:** the wing carry-through is two numbers — the
fuselage station of the front spar and of the rear spar — and the user types
them on the geometry page, instead of the chord percentages they are presently
derived from.

Raised by the owner 2026-09-05 against note 44 §13's **OR-97** finding: every
wing-attach fitting load the oracle report can print is derived from *assumed*
spar stations, and the field that would hold the real answer does not exist.
This note supersedes note 44 **§14**, which answered the same finding by making
the chord percentages an oracle input.

**Scope.** The input only. The owner's related proposal — publishing the
fuselage as two cantilevers off the carry-through — is **not** in this note; it
is deferred to its own, with its measurements kept in §7 so they are not lost.
This note touches **no frozen file** (§6).

Sources reviewed: `sloads/derived_geometry.py` (`carry_through`,
`wing_reference`), `sloads/constants.py`, `sloads/models/inputs.py`,
`sloads/field_registry.py` (`COLLAPSED_OVERRIDES`, `EXTERNAL_VALUES`,
`derived_from`, `FieldEntry.governs`, `SUPPLIED_RULE`), `oracle_app/form.py`
(`_collapsed_note`, `_copy_note`), `sloads/io.py`, `sloads/migrations.py`,
`app/views/configuration_layout.py`, `tests/test_frozen_set.py`,
note 36 OV-1/OV-9, note 44 §13/§14.

*Measurements taken 2026-09-05 against the shipped fixtures at `a9d6619`.*

---

## 1. What the code does today

`derived_geometry.carry_through` places the spars at

    x_f = x_LE(root) + front_pct * c_root
    x_r = x_LE(root) + rear_pct  * c_root

off the wing's **centreline** root chord — `leading_edge[0]`, the inboard-most
polyline point, which is at y = 0.00 on every shipped fixture, confirming the
owner's centreline reading. `SurfaceInput.front_spar_pct`/`.rear_spar_pct` are
`Optional` fractions; unset, `constants.DEFAULT_FRONT_SPAR_PCT`/`_REAR_SPAR_PCT`
(0.15/0.65) are substituted and the result is flagged `assumed`. All seven
bundled examples write both keys as `null`, so every fitting load the project
ships is computed from the defaults.

## 2. Why the percentage cannot be the datum

**It cannot express the geometry it stands for.** The percentage is measured on
the wing root chord *at the centreline*; the fittings are at the fuselage. On a
swept or cranked wing those are different stations and no value of the
percentage reconciles them. OR-97 found that the *value* is always assumed; this
is the same finding one level down — the *field* could not hold a real measured
station even if the analyst had one.

**And %MAC is not an alternative unit for it.** Put to the owner as a candidate
and measured:

| Fixture | 20 % root chord | as %MAC | 60 % root chord | as %MAC |
|---|---:|---:|---:|---:|
| `ga6_normal` | 65.20 in | **2.28 %MAC** | 105.60 in | 60.60 %MAC |
| `baron_58` | 78.80 in | 18.57 %MAC | 112.40 in | 70.00 %MAC |
| `cessna_210` | 58.40 in | 12.64 %MAC | 85.20 in | 59.18 %MAC |

The gap is large and inconsistent — `ga6_normal`'s MAC leading edge sits 18.6 in
aft of its root leading edge, so 20 % root chord lands at 2 %MAC and entering
"20 %MAC" expecting today's default would move the front spar 12.3 in aft.
`MAC`/`XLEMAC` are also **derived** from the wing polylines, so a station stored
as %MAC would migrate whenever anyone refined the planform. A global X station
is invariant under that edit, which is the owner's own conclusion and the reason
it is right.

## 3. Decisions

| # | Decision | Amends |
|---|---|---|
| **OR-121** | **The carry-through is entered as a fuselage station in global X.** `SurfaceInput.front_spar_x_in` / `.rear_spar_x_in`, `Optional[float]`, in the geometry page's length channel, one pair per surface (`carry_through` reads the wing's). Both carry `supplied=True` — the mark note 44's OR-103 aimed at the percentages moves here — earned on `SUPPLIED_RULE` route 2 and demonstrated by G-OR-76. Origin stays `SLOADS`: Ch 15 ships no `.BAS` and the distributed carry-through is this project's refinement of p103, so `ORIGINAL` would enter a false claim in the table gate G5 measures. | **OR-97 (discharges)**, **OR-103 (supersedes)** |
| **OR-122** | **A blank station defaults to 20 % / 60 % of the centreline root chord.** OR-104's values survive unchanged and are re-cast in role: no longer a stored input's fallback but the estimator that computes the default station, from the y = 0 root chord §1 confirms the code reads. OR-104's measured fitting-load deltas for the 15/65 → 20/60 move stand as taken; on `ga6_normal` the carry-through moves from x = 60.15–110.65 in to **65.20–105.60 in**. | OR-104 (re-cast, values unchanged) |
| **OR-123** | **The station is a note 36 collapsed override (OV-1): blank derives, typed overrides.** Owner ruling 2026-09-05: *"use the percentage to calculate the location and the GUI only shows the station X with a note as to how it was calculated."* The mechanism is the one the project already enumerates in `field_registry.COLLAPSED_OVERRIDES` — the field renders **live and blank**, and `oracle_app.form._collapsed_note` captions it *"Blank — derives from **20 % of the centreline root chord** (currently 65.20 in). Enter a value only to override."*, switching to the override wording with the derived number beside it once a value is typed. The row needs `governs=True` (typed-means-override), a `derived_from`, and one `EXTERNAL_VALUES` resolver taking the surface row as `record`, which the API already supports; membership of `COLLAPSED_OVERRIDES` follows from the resolver. Both halves are guarded — `test_derive_override.py::test_every_collapsed_path_is_linked_and_resolvable` and `test_oracle_gui.py::test_every_external_copy_states_how_it_resolves` each refuse a collapsed row that does not govern. This is what makes OR-126 true rather than merely intended: blank means nothing is written, so `assumed` cannot be falsified by a page visit. **The calc side already has the OV-1 shape** — `carry_through` reads `DEFAULT if ... is None else float(...)` — so the contract is honoured by construction. **The behaviour was put to the owner in these terms and accepted 2026-09-05** (*"this functionality sounds acceptable"*), the `ga6_normal` caption above being the worked case shown. *(The draft first named this the collapsed override and then, mid-review, called `governs=True` the display-only path. Both halves were half-right and the registry's own guards settled it while the row was being written: `governs=True` is **required** here, and `_copy_note`'s "entering a value here has no effect" disabling applies only to the rows `_NOT_COLLAPSED` excludes — a collapsed row renders live through `_collapsed_note`.)* | **note 36 OV-1/OV-9**, #70/PB-17 |
| **OR-124** | **`front_spar_pct`/`rear_spar_pct` leave the schema.** The page never shows them, nothing but `carry_through` reads them, and the percentages that replace them are `constants`. Keeping them would leave two stored fields for one quantity with only one visible — the duplicate-owner shape this project removes rather than marks. Both keys are `null` in all seven examples, so no fixture data is lost. | `constants.py`, OR-105 |
| **OR-125** | **OR-105 is withdrawn, and its premise is corrected for the record.** It ruled the spar fractions be stored as percent (0–100) so the two front-ends could not ask for one quantity in two scales; with the fields gone there is no scale to fix. Its premise was also wrong: the spar pair were **not** the only `_pct` leaves holding a fraction — `SurfaceInput.ref_axis_pct` is the same shape (stored 0.25, `_pct$`-classified "a percentage" by `units.py:554`, ×100 on render and ÷100 on Apply at `app/views/configuration_layout.py:770`). It is **filed, not swept**: the two-front-end trap OR-105 named cannot reach it, because `ref_axis_pct` is `Origin.SLOADS` and not `supplied`, so the oracle GUI never offers it. | **OR-105 (withdrawn)**, practice 4 |
| **OR-126** | **Provenance stays two-state, and `assumed` recovers its plain meaning.** `CarryThrough.assumed` is True exactly when no station was entered — i.e. the estimator supplied it. No third state exists, because the percentage is no longer an input that could be entered while the station is not. OR-106's substance survives, and OR-123's collapsed override is what enforces it: the derived station is shown in the caption and never written, so a page visit cannot turn an assumed station into an entered one. | OR-106 (survives, restated), OR-123 |
| **OR-127** | **Schema v60 → v61, and `_hop_60` preserves geometry rather than dropping it.** The hop removes the two `_pct` keys and adds the two `_x_in` keys. A v60 file that **entered** a percentage has its station computed in the hop from its own polylines (`x = x_LE(root) + pct × c_root` — the dict carries `leading_edge`/`trailing_edge`), so an entered carry-through survives as the same physical station instead of silently reverting to a default; a `null` file hops to `null`. No shipped fixture takes the first branch, so it is guarded on a constructed dict. | `migrations.py`, OR-124 |

## 4. Gates

- **G-OR-75** — the station pair is in `oracle_input_paths()` and survives
  `reduce_to_oracle_inputs`: a project entering a station reports **that**
  station in the oracle report, not the default. OR-97's finding run from the
  other side, and the assertion the whole change turns on.
- **G-OR-76** — the **G5 demonstration** earning the `supplied` mark
  (`SUPPLIED_RULE` route 2): dropping an entered station changes a Fuselage
  Loads result on a shipped example. Without it the mark is speculative, which
  the rule forbids.
- **G-OR-77** — `CarryThrough.assumed` is True exactly when no station is
  entered, asserted **through the projection** as well as on the raw project, so
  no future reducer change can turn an entered station into an assumed one.
- **G-OR-78** — the derived default is *shown, not written*: rendering the
  geometry page on a project with no entered station leaves the project
  byte-identical (`tests/test_gui_journey.py`'s posture), and the mark states
  the derivation.
- **G-OR-79** — the hop: a v60 file carrying an entered `0.20`/`0.60` loads at
  v61 with stations equal to its own `x_LE(root) + pct × c_root` and reproduces
  its pre-hop carry-through exactly — a representation change, not a geometry
  change; a `null` file hops to `null`.

## 5. What this supersedes in note 44

| Note 44 §14 decision | Status |
|---|---|
| **OR-103** (the fractions become an oracle input by `supplied=True`) | **Superseded by OR-121** — the mark moves to the station pair. |
| **OR-104** (default 20 %/60 %) | **Survives, re-cast by OR-122** — same values, now the estimator for the default station. |
| **OR-105** (store percent 0–100; `_hop_60` ×100) | **Withdrawn by OR-125**, premise corrected in the same entry. |
| **OR-106** (`None` means assumed; widget blank) | **Survives, restated by OR-126.** OR-123's collapsed override keeps the widget blank *and* states the derived number, so the blank-versus-prefilled question OR-106 answered does not arise. |
| **OR-107** (no frozen file edited; OR-15 not engaged) | **Stands.** Verified against `tests/test_frozen_set.py`: the freeze covers `sloads/modules/*` and five `oracle_app/` files, and this change touches `models/inputs.py`, `io.py`, `migrations.py`, `constants.py`, `derived_geometry.py`, `field_registry.py` and `app/views/` — none of them frozen. The oracle GUI gains the field without an edit, its pages being registry-built. |
| **OR-97** (4.4 states the stations were assumed) | **Discharged structurally by OR-121.** §4.4 still states which of the two it is; now the entered branch is reachable. |
| **G-OR-60 … G-OR-63** | Replaced by **G-OR-75 … G-OR-79**. |

Note 44 §14 gets a superseded banner pointing here. §13 (OR-94…OR-102) and §15
(OR-108…OR-113) are untouched, except that OR-97's finding is now discharged
rather than merely stated.

## 6. Closure obligations (tier L)

- `docs/10_standard/PROGRAM_SPEC.md` — the `body_loads` / geometry input rows.
- `docs/20_theory/00_theory_sources.md` — the `body_loads` row says "spar
  stations from the G1 planform × `SurfaceInput.front_spar_pct`/`rear_spar_pct`
  (defaults 0.15/0.65)" and must say entered stations, defaulted 20 %/60 %.
- `docs/10_standard/ORACLE_REPORT.md` — §7 register row with its guard (G-OR-8).
- `docs/10_standard/DATA_DICTIONARY.md`,
  `docs/60_guide/_generated/configuration_layout.md` — regenerated, never edited.
- `changes/` fragments in full step format; backlog row; issue.
- **Filed, not fixed** (OR-14): `body_loads.CLOSURE_ARTIFACT_CAVEAT` closes with
  *"Define the wing front/rear spar chord fractions to get the Ch 15
  carry-through reaction"*, and `sbeam_bridge` writes *"Wing spar stations
  ASSUMED (chord-fraction defaults)"*. Both wordings go stale with this note.
  `body_loads.py` is frozen and a wording change is not additive, so they are
  filed for the 0.8.2 cut rather than edited here.

## 7. Deferred — the segmented fuselage beam

The owner's second proposal of 2026-09-05: *"Forward fuselage VMT loads would be
summed to the front spar. Likewise rear fuselage loads would be summed from the
tail to the rear spar. The VMT between the spars is not meaningful."* It is a
reporting change to `sloads/modules/body_loads.py` — **frozen**, so it needs an
OR-15 admission, which note 44 §15's OR-108 already holds over that same file.
It gets its own note. The review's measurements are kept here so they are not
re-derived:

1. **It republishes, rather than re-derives.** The aft segment integrated
   tail→forward gives the same `Myy` at the rear spar as the published nose→aft
   table, to the digit — ga6 `MAX DOWN LOAD ON WING` −131,912.0 both ways,
   `AFT DOWN BENDING` −196,352.4; baron −221,791.1 and −281,174.2. That follows
   from the beam closing (terminal `Myy` ≈ 4e−10, terminal `Sz` ≲ 2e−12 — the
   M4-1 gates), so the correctness of the rule rests on a gate already passing.
2. **Half the reacted load is mass between the spars.** ga6 `MAX DOWN LOAD ON
   WING`: forward inertia −3,083.2, between-spar mass **−5,904.9**, aft applied
   −3,403.7, carry-through reaction +12,391.8 — summing to exactly zero. Two
   cantilever tables that do not state the middle term will appear not to add up.
3. **A segment sum is not a fitting load.** Forward inertia −3,083.2 against
   `R_f` +5,842.0 on the same case: `R_f`/`R_r` come from the global 2×2
   (`_spar_reactions`), not from segment statics. They meet at a station and are
   different quantities.
4. **A question that note should settle:** M4-1 spreads the carry-through
   reaction to avoid a ±`M_ub`/`d` shear spike that lives *between the spars* —
   the region that would stop being published. Fitting loads are identical
   either way, so it is a question about what the refinement is still buying.
