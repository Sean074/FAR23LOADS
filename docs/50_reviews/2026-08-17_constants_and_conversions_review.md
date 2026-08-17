# Constants and conversion factors — ownership review (2026-08-17)

**Charge (user, 2026-08-17, raised while closing backlog Pri 5):** several
analysis modules define their own gravity, degrees-per-radian and in²/ft²
factors, sometimes at a different value from `constants.py` (`_G = 32.2` beside
`G = 32.174`; `57.3` beside `57.2957795` beside `180/π`). Review every
hard-coded physical constant and unit factor in `sloads/`, `app/`, `scripts/`
and `cli.py`; state one owner per quantity; state one rule for what lives in
`constants.py` versus `units.py`; feed one backlog item.

**Decisions taken before the review (user, 2026-08-17):**

1. Scope: `sloads/` + `app/` + `scripts/` + `cli.py`.
2. **Value policy: exact by default.** A `.BAS`-truncated value survives only as
   a named `*_SUITE` constant with the oracle that requires it cited (the
   `KT_TO_FPS_SUITE` precedent, `constants.py`); each survivor and each value
   change gets a line in `docs/20_theory/02_approved_corrections.md`.
3. **Demarcation.** `constants.py` = physical constants, FAR-mandated numbers,
   and every *suite-internal* (Imperial↔Imperial) factor — in²/ft², in/ft,
   deg/rad, kt→ft/s, slug↔lb, hp→ft·lb/s, the atmosphere. `units.py` = only
   the Imperial↔SI boundary — base SI factors, `HUMAN_SI`, `deliverable_units`,
   the ISO gravity of the deck channel (`G_MM_S2`/`G_IN_S2`, deliberately exact,
   `units.py:64-75`). Written into `CONVENTIONS.md` §7 with a drift guard.
4. Deliverable: this note + one ranked backlog row.

Method: ripgrep sweep for the literal set (57.3, 57.29…, 32.2, 32.17, 518.x,
661.x, 1.688, 1.15·88/60, 295, 550, 33000, 1728, /12.0, 144, 386, 9.80665,
25.4, 0.3048, 0.45359, 1.3558, 0.0929, 6.4516, 0.7457, 3.1416, 498, 114.6) plus
every `^_[A-Z0-9_]+ = <number>` module constant; each live hit checked for an
existing owner and for a value delta. Doc-only mentions (BASIC listings in
docstrings) were noted and excluded. Effect sizes below were **measured** by
swapping the value and running the suite (`tests/test_engine.py` and every
page-cited oracle unaffected in both experiments; only regression pins and the
frozen-bytes digest moved).

## 1. Findings by quantity

| # | Quantity | Owner today | Stray sites (live code) | Value delta vs exact | Disposition |
|---|---|---|---|---|---|
| C-1 | **deg/rad** | none | `select.py:82`, `airloads.py:67`, `wing_inertia.py:60`, `one_engine_out.py:97` (`57.3`); `flight_envelope.py:82`, `vn_diagram.py:36` (`57.2957795`); `fuselage_moment.py:68` (`180/π`); `flight_envelope.py:83`, `aero_curves.py:50` (`π/180`); `select.py:327` `114.6` (= 2·57.3, downwash) | 57.3 is +0.0074 % | `DEG_PER_RAD = 180/PI`, `RAD_PER_DEG` in `constants.py`; all ten sites import. **Measured:** 12 tests move — the frozen digest + `test_balance` SELECT unsymmetrical-split pins (`rel=1e-9`); no oracle. Re-pin; register line. |
| C-2 | **g** | `constants.G = 32.174` | `select.py:83`, `vn_diagram.py:37` (`_G = 32.2`); `flight_envelope.py:228` (bare `32.2`) | +0.081 % | import `G`. **Measured:** 7 tests move (digest + 3 SELECT pins); no oracle. `rigid_body.G_IN_S2 = G*12` stays (documented cycle-avoidance, `rigid_body.py:57-67`); `units.G_IN_S2` (ISO) stays — different channel, deliberate. |
| C-3 | **in²/ft²** | `constants.IN2_PER_FT2 = 144` (3 consumers) | six private aliases under two names (`_SQIN_PER_SQFT` in `tail_geometry`, `taildist`, `flap`, `aileron`, `tab`; `_IN2_PER_FT2` in `one_engine_out`) + inline `144` in `fuselage_moment:146`, `validation:122`, `landing:507`, `structural_speeds:211`, `airloads:369-371`, `migrations:150`, `wing_inertia:146-147` | none | import the owner everywhere; grep guard. Zero bytes move. |
| C-4 | **in/ft** | none | ~24 inline `/ 12.0`, `* 12.0` across `select` (7), `one_engine_out` (3), `landing` (2), `engine` (2), `flap` (2), `flight_envelope`, `configuration`, `rigid_body`, `report/content`, `app/views/flight_envelope` (2), `app/views/aircraft_comparison` | none | `IN_PER_FT = 12.0` in `constants.py`; import. Zero bytes move. |
| C-5 | **dynamic pressure `V²/295`** | `constants.DYNAMIC_PRESSURE_DIVISOR = 295.0` (one consumer, `stall_speed_kt`) | 15 inline sites + `one_engine_out._Q_DIVISOR`: `aero_curves:150` (the notional shared helper!), `aileron:78`, `tab:67`, `flight_envelope:142/145/152/281/344`, `select:330/475/693/698`, `airloads:340`, `flap:118-120`, `balance:758` | 295 vs exact 1/(½·ρ₀·kt²) = **295.24** (−0.08 % in q everywhere) | **The one real decision.** Route every site through `aero_curves.dynamic_pressure` (which reads the owner). Value: exact `0.5*RHO_SL*KT_TO_FPS**2` per policy 2 — **but** 295 is the printed FAR-23-era engineering form and every McMaster oracle was computed with it; the change is uniform, so oracle tolerance is expected to hold, to be **measured before re-pinning**. If any Appendix-A oracle exceeds ±0.1 %, keep `295` as `DYNAMIC_PRESSURE_DIVISOR_SUITE` with that oracle cited. |
| C-6 | **kt→ft/s** | `KT_TO_FPS_SUITE = 1.15·88/60 = 1.68667` | none stray (both consumers import) | −0.066 % vs 1.68781 | already the precedent pattern; add exact `KT_TO_FPS = 1852/3600/0.3048` beside it for C-5, keep `_SUITE` for the slipstream oracle it cites. |
| C-7 | **speed of sound / atmosphere** | `constants.standard_atmosphere`, `TROPOPAUSE_FT`, `SEA_LEVEL_SOUND_KT` | `flight_envelope._speed_of_sound` (`518.688`, `575.0`, `35332.0`, `29.02436`, `0.003566` re-quoted) | 518.688 vs 518.4 °R: +0.03 % in *a*, kept "for oracle fidelity near the Mach cap" | keep FLTLOADS' value **as a named `_SUITE` constant next to the shared one** (`SEA_LEVEL_TEMP_R_SUITE`), read `TROPOPAUSE_FT` and the lapse from the owner; register line. Three sea-level a₀ values exist in the package (660.84 / 661.02 / ISA 661.48) — the note must say which one each consumer means. |
| C-8 | **hp → ft·lb/s** | none (`HP_TO_TORQUE = 33000` = 550·60) | `one_engine_out:161`, `flap:91` (`550.0`) | none | `FT_LB_S_PER_HP = 550.0`; derive `HP_TO_TORQUE = 60*FT_LB_S_PER_HP`. Zero bytes move. |
| C-9 | **π** | `constants.PI` (1 consumer) | nine sites call `math.pi` directly | none | policy call, not a defect: pick one (`math.pi` everywhere and drop `PI`, or `PI` everywhere); guard by grep. |
| C-10 | **FAR 23.341 gust constants** `498`, `0.88`, `5.3` | none | `vn_diagram:97/101`, `flight_envelope:229-230`, `select:539-540/574-575/725-726` | regulatory (printed in the rule) — **no exact value exists**; never "corrected" | `GUST_ALLEVIATION_KG = (0.88, 5.3)`, `GUST_498 = 498.0` in `constants.py` with the § citation; import at 5 sites. |
| C-11 | **SI factors outside `units.py`** | `units.py` | `report/latex.py:165` (`25.4`, mm→TeX pt page geometry) | none | typographic, not physics — import `IN_TO_MM` anyway so the grep guard is absolute. |
| C-12 | dead/near-dead owners | — | `SEA_LEVEL_SOUND_KT`, `TROPOPAUSE_FT` unused outside `constants.py`; `IN2_PER_FT2` 3/19 sites | — | resolved by C-3/C-7. |

Not in scope: tolerances (`_TOL = 1e-9`, `_COINCIDENT_TOL`), fractions of
geometry (`_H_AC_WING`, `_FUSE_*_FRAC`), FAR ratios owned by their module with a
citation (`_VNE_VD_RATIO` 23.1505) — these are per-module engineering
parameters, not shared physical constants, and stay where they are.

## 2. The rule (to be written into `CONVENTIONS.md` §7)

| Lives in | What | Guard |
|---|---|---|
| `sloads/constants.py` | physical constants (`G`, `RHO_SL`, `PI`, atmosphere), FAR-mandated numbers (`ULTIMATE_FACTOR`, gust 498/0.88/5.3, gyro rates), **every Imperial↔Imperial factor** (`IN_PER_FT`, `IN2_PER_FT2`, `DEG_PER_RAD`, `KT_TO_FPS`, `FT_LB_S_PER_HP`, `LBIN2_PER_SLUGFT2`), and each `*_SUITE` survivor beside its exact twin with the oracle cited | grep guard: the literal set above appears in no other file under `sloads/`, `app/`, `scripts/` |
| `sloads/units.py` | **only** Imperial↔SI: base factors, `HUMAN_SI` and its views, `deliverable_units`, the deck channel's ISO gravity | grep guard: no SI factor outside `units.py`; no Imperial-only factor inside it (`units.py` imports `constants`, never the reverse) |
| a module | a parameter that is that module's own engineering choice, cited (`_VNE_VD_RATIO`), or a tolerance | none — but a *value that has an owner* may not be re-declared |

## 3. Cost and effect

- Ownership moves (C-3, C-4, C-8, C-10, C-11, half of C-1/C-9): **zero bytes
  move**; a mechanical import sweep + guards. S-sized on its own.
- Value moves (C-1 57.3→exact, C-2 32.2→G): measured ≤0.081 %; no printed
  oracle moves; the frozen digest and ~12 `test_balance` pins re-pin. Under the
  ±0.1 % oracle tolerance and far under the base-method error bar
  (`theory_sources.md` §Base-method uncertainty) — so per CLAUDE.md rule 6 the
  *value* change ranks only as part of the ownership item, never on its own.
- C-5 (295 → exact) is the one with a real decision inside it; measure first.
- Tier **M**: `PROGRAM_SPEC`/`CONVENTIONS` §7 rows, register lines, one-paragraph
  history fragment; **no schema change**.

Ranked on the backlog as band A (cost-of-change fix, review 2026-08-16 §1
lens): the same three-spellings defect class CH-6 opened, closed once.
