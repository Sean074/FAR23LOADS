# Engine-Mount Loads (ENGLOADS)

How the `engine` module (`farloads/modules/engine.py`, ported from `ENGLOADS.BAS`)
computes the structural design loads an engine mount must sustain under **FAR Part
23 Subpart C**, with a fully worked example on the Continental IO-520-BB
reciprocating installation printed in the manual (Reference 1, Appendix A p131).

- **Source of truth:** Reference 1 (McMaster) engine-mount chapter; the regression
  oracle is Appendix A (GA single) p131 / Appendix B (twin turboprop) p251.
- **Regulations:** FAR 23.361 (engine-torque & vertical loads), 23.363 (side
  load), 23.371 (gyroscopic loads). Two approved deviations from the manual, on
  23.361(a)(1) and (a)(3) — see the **Approved correction** section below.
- **Units:** calc runs in the original program's Imperial units. Torque ft-lb,
  force lb, length in, inertia slug-ft². The values in this document are **LIMIT**
  loads (the oracle figures); deliverables apply the ×1.5 ultimate factor at the
  render/export boundary — see `docs/20_theory/00_theory_sources.md`.

> **Sign convention (preserved from ENGLOADS):** engine-mount reaction torque is
> reported **negative**; "clockwise from the pilot's view is positive" for rotor
> RPM and stoppage torque.

---

## 1. Shared / derived quantities

Every condition is built from a small set of derived quantities computed once per
engine.

### Combined propeller + engine weight (PPWT)

The propeller and engine are treated as one rigid mass hung on the mount:

```
PPWT = prop_weight + engine_weight        [lb]
```

### Combined centre of gravity (XPP, YPP, ZPP)

The weight-averaged CG of the prop + engine, per axis. The BASIC truncated each
coordinate to three decimals (`INT(x*1000)/1000`); this is preserved because it
affects compared figures:

```
XPP = trunc3( (prop_weight·prop_x + engine_weight·engine_x) / PPWT )
```

(and likewise for Y, Z). All vertical/side loads in the conditions below are
applied **at this point**.

### Engine torque from horsepower

For a **reciprocating** engine the mean shaft torque is derived from rated power
and RPM:

```
T = HP · 33000 / (2π · RPM)               [ft-lb]
```

evaluated at the takeoff rating (`TOTORQ`) and the max-continuous rating
(`CONTTORQ`). A **turbopropeller** instead supplies its mean torque directly
(`max_engine_torque` for takeoff, `cruise_torque` for max-continuous).

### Torque multiplication factor

The design torque is the *mean* torque times a factor that accounts for the
peak-to-mean ratio of the firing impulses (a four-stroke engine with fewer
cylinders fires less often per revolution, so the peak/mean ratio rises):

| Engine | Factor |
|--------|--------|
| Reciprocating, ≥5 cylinders | 1.33 |
| Reciprocating, 4 cylinders | 2.0 |
| Reciprocating, 3 cylinders | 3.0 |
| Reciprocating, 2 cylinders | 4.0 |
| Turbopropeller | 1.25 |

(`reciprocating_torque_factor` / `TURBOPROP_TORQUE_FACTOR` in `constants.py`,
mirroring `ENGLOADS.BAS` lines 320-328.)

---

## 2. The FAR conditions

The module always evaluates three conditions; a turbopropeller adds three more.

| Function | FAR | Applies to | What it produces |
|----------|-----|-----------|------------------|
| `condition_361_a1` | 23.361(a)(1) | all | factor × mean **takeoff** torque + **75 %** limit maneuver vertical load |
| `condition_361_a2` | 23.361(a)(2) | all | factor × **max-continuous** torque + **100 %** limit vertical load |
| `condition_363`    | 23.363(a)&(b) | all | lateral (**side**) load, independent of other flight loads |
| `condition_361_a3` | 23.361(a)(3) | turboprop | propeller-control-malfunction torque (1.6 × 1.25 × mean takeoff torque) |
| `condition_361_b1` | 23.361(b)(1) | turboprop | torque from **sudden engine stoppage** |
| `condition_371_b`  | 23.371(b) | turboprop | **gyroscopic** pitch/yaw moments at max-continuous RPM |

### 2.1 23.361(a)(1) — takeoff torque + 75 % vertical

```
n        = 0.75 · limit_load_factor              (vertical load factor)
V_down   = n · PPWT                              [lb], applied at the combined CG
torque   = factor · mean_takeoff_torque          [ft-lb], reported negative
```

### 2.2 23.361(a)(2) — max-continuous torque + 100 % vertical

```
n        = limit_load_factor                     (full vertical load factor)
V_down   = n · PPWT                              [lb]
torque   = factor · max_continuous_torque        [ft-lb], reported negative
```

### 2.3 23.363 — side load

A lateral load on the mount, independent of the flight loads, applied at the CG:

```
n_y      = max( limit_load_factor / 3 , 1.33 )
side     = n_y · PPWT                            [lb]
```

### 2.4 Turbopropeller-only conditions

- **23.361(a)(3)** propeller-control malfunction:
  `torque = 1.6 · 1.25 · mean_takeoff_torque` (= 2.0 × mean), with 1 g vertical.
  The base limit takeoff torque carries 23.361(c)'s 1.25 turbopropeller
  mean-torque factor (an approved correction, the same as (a)(1); see the
  **Approved correction** section below); the 1.6 malfunction factor multiplies on top.
- **23.361(b)(1)** sudden stoppage — the prop (and any compressor/turbine rotors)
  shed all their angular momentum over the stop time `Δt`:
  ```
  torque = I_prop·(ω_prop/Δt) + Σ I_rotor·(ω_rotor/Δt)
  ```
  where `ω = RPM · 2π/60`. `I_prop` uses the measured value if supplied, else the
  blades-only thin-rod approximation `I = m·L²/3`; rotors default to a solid disk
  `I = ½·m·r²`.
- **23.371(b)** gyroscopic loads — the spinning prop/rotor angular momentum
  `T = Σ I·ω` (at max-continuous RPM) crossed with the airframe rates gives a
  pitching moment `Myy = 2.5·T` (2.5 rad/s yaw) and a yawing moment `Mzz = 1·T`
  (1 rad/s pitch). Both act in either direction, so **all four sign combinations**
  are enumerated, each combined with a steady 2.5 g vertical load and the
  max-continuous thrust.

An optional FAR 25 superset (`Project.include_far25`, turbopropeller only) appends
the non-duplicative Part 25 cases; see `00_theory_sources.md` and
`reference/14CFR_Part25_engine_torque.md`.

---

## 3. Worked example — Continental IO-520-BB

The reciprocating worked example from Appendix A (the GA single). Inputs (from
`tests/test_engine.py::io520bb`):

| Input | Value |
|-------|-------|
| Engine type | Reciprocating, 6 cylinders |
| Limit load factor | 3.8 |
| Engine weight / CG | 505 lb @ (22.0, 0.0, −10.0) in |
| Propeller weight / CG | 74 lb @ (−10.0, 0.0, 93.022) in |
| Takeoff rating | 285 HP @ 2700 RPM |
| Max-continuous rating | 265 HP @ 2500 RPM |

### Step 1 — derived quantities

```
PPWT   = 74 + 505 = 579 lb
XPP    = (74·(−10) + 505·22) / 579 = 17.91 in   (Y = 0, Z = 3.166 in)
factor = 1.33                                   (reciprocating, 6 cylinders ≥ 5)

TOTORQ   = 285 · 33000 / (2π · 2700) = 554.39 ft-lb   (mean takeoff torque)
CONTTORQ = 265 · 33000 / (2π · 2500) = 556.72 ft-lb   (mean max-continuous torque)
```

### Step 2 — 23.361(a)(1), takeoff

```
n      = 0.75 · 3.8        = 2.85
V_down = 2.85 · 579        = 1650.15 lb   (at XPP = 17.91 in)
torque = 1.33 · 554.39     = 737.34 ft-lb → reported −737.34 ft-lb
```

### Step 3 — 23.361(a)(2), max-continuous

```
n      = 3.8
V_down = 3.8 · 579         = 2200.2 lb
torque = 1.33 · 556.72     = 740.44 ft-lb → reported −740.44 ft-lb
```

### Step 4 — 23.363, side load

```
n_y  = max(3.8/3, 1.33) = max(1.267, 1.33) = 1.33
side = 1.33 · 579       = 770.07 lb
```

### Result summary (LIMIT loads)

| Condition | Vertical / side load | Mount torque |
|-----------|---------------------|--------------|
| 23.361(a)(1) takeoff | 1650.15 lb (n = 2.85) | −737.34 ft-lb |
| 23.361(a)(2) max-cont. | 2200.20 lb (n = 3.80) | −740.44 ft-lb |
| 23.363 side | 770.07 lb (n_y = 1.33) | — |

These match the manual's printed Appendix A p131 figures within ±0.1% (the
modernized `math.pi` shifts McMaster's `3.1416`-based numbers in the ~6th
significant digit — see Decision 3). The deliverable load-case CSV / sbeam export
multiplies the **load** quantities by the ×1.5 factor of safety to report ULTIMATE
(e.g. 1650.15 → 2475.2 `lb-ULT`); the load factors and CG stay dimensionless/plain.

---

## Approved correction — 23.361(a)(1) and (a)(3)

McMaster's manual paraphrases FAR 23.361(c) narrowly — as applying only to the
**(a)(2)** max-continuous case — and leaves the **(a)(1)** takeoff torque and the
**(a)(3)** malfunction torque unfactored. That paraphrase encodes the **Amendment
23-26** drafting error. Per **AC 23-19A** the omission was non-conservative (lower
loads); the *corrected* 23.361(c) (restored by **Amendment 23-45**) directs the
mean-torque factor onto the limit engine torque considered under **all** of
paragraph (a). This suite applies that correction to both takeoff-derived cases —
an approved, documented deviation from the oracle:

- **(a)(1)** *(approved 2026-06-22)* — `factor × mean takeoff torque`. IO-520-BB:
  1.33 × 554.39 = **737.34 ft-lb** (manual prints the unfactored 554.39). For a
  turbopropeller the result (1.25 × mean takeoff torque) is identical to
  25.361(a)(1)(i). The manual's 554.39 is retained as the printed "mean takeoff
  torque" in `test_361_a1` for traceability.
- **(a)(3)** *(approved 2026-06-23)* — the malfunction torque's base "limit engine
  torque corresponding to takeoff power and propeller speed" is the same quantity
  as (a)(1), so 23.361(c)'s **1.25** turbopropeller factor applies before the 1.6
  malfunction factor: `torque = 1.6 × 1.25 × mean takeoff torque` (= 2.0 × mean).
  The manual / `ENGLOADS.BAS` (`TTP = 1.6*ENGTORQ`) apply 1.6 × mean only. The
  bundled PDF has no printed Appendix B engine-mount output, so (a)(3) is
  formula-checked (`test_361_a3_applies_mean_torque_factor`), not locked to a
  printed figure.

Source: `reference/AC_23-19A_engine_torque.md`; see CLAUDE.md "Approved corrections
to the source".
