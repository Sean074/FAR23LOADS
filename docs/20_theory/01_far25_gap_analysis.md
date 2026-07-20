# FAR 25 Gap Analysis — Extending the FAR23 Loads Methods to Transport-Category Concepts

**Status:** initial review, 2026-07-20. Regulation rows are drawn from the
FAR 25 loads subpart as known at review time and from the program's own
references; **every row must be verified against the current 14 CFR text (and
amendment level) before any code lands** — same discipline as the `.BAS`
verify-vs-source rule. Rows carry a *verify* tag where the exact figure or
wording needs confirmation.

**Purpose.** The concept mission (regional-jet-class fixtures, MTOW > 12,500 lb,
high-subsonic Mach) puts concept airplanes under **FAR 25** loads rules, while
every analysis in this suite implements **pre-Amdt-23-64 FAR 23** (via Ref 1 /
DOT/FAA/AR-96/46). This document lists, per load topic: the FAR 25 regulation,
the FAR 23 regulation the program implements, what the program actually does,
the difference, and a disposition — feeding a phased plan (§3) to modify the
FAR 23 analyses into a defensible **FAR 25 concept surrogate**. It is a
concept-development aid, not a certification basis.

**The central observation.** The FAR23 program's methods are CAR-4b-lineage
*statics*. Pre-1996 FAR 25 (before Amdt 25-86/25-141) used essentially the same
statics — the Pratt gust formula, static maneuver balances, energy-method
landing gear. So the Part 25 gap splits cleanly in two:

1. **Parameter/schedule differences** (load-factor floors, gust velocities,
   sink speeds, deflection schedules) — cheap to implement inside the existing
   modules, exactly like the shipped `engine` FAR 25 supplement.
2. **Generational differences** — requirements added to Part 25 after the
   statics era (tuned discrete gust with dynamic response, continuous
   turbulence PSD, dynamic engine-failure loads, rational taxi analysis,
   systems-interaction Appendix K). These cannot be "parameterized in" and are
   **out of scope**; the surrogate approach is to run the old-generation static
   method with the new-generation *velocities/factors* and document the caveat.

**Existing FAR 25 support (baseline).** `engine.py` already ships a
`far25` supplement (`EngineInput.include_far25`): 25.361(a)(3)(i)/(ii) turbine
torque cases (duplicate-dropping vs the FAR 23 set) and 25.371 gyroscopic with
declared-rate advisories (decision D-2). `reference/14CFR_Part25_engine_torque.md`
holds the verified regulation text. This is the **pattern to replicate**: an
opt-in supplement flag per module, additive conditions with proper
`far_reference` strings, no change to the FAR 23 path.

---

## 1 · Comparison table

Disposition codes: **A** = already covered · **P** = parameter/schedule change
in an existing module · **S** = static surrogate feasible (documented
approximation of a dynamic/rational Part 25 requirement) · **N** = new
analysis, concept scope · **X** = out of scope (document, never silently skip).

### 1.1 General provisions

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.301/303/305/307 | 23.301/303/305/307 | Limit/ultimate framework, SF 1.5, `-ULT` marking on every output | None — identical framework | **A** |
| 25.321 (flight loads general; every weight/CG incl. **MZFW**) | 23.321 | V-n balance at CG cases from the weight envelope; no zero-fuel design weight concept | Part 25 requires the maximum zero-fuel weight as a design weight (wing-bending critical with full payload / no fuel relief) | **N** — add MZFW to weights/envelope inputs; run the corner set at MZFW |
| 25.343 (design fuel loads, structural reserve fuel) | — | Fuel is one weight-envelope item | Fuel-distribution design cases (incl. zero wing fuel) absent | **N** (fold into the MZFW item) |

### 1.2 Flight envelope & maneuver factors

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.337(b): n₁ = 2.1 + 24,000/(W+10,000), **floor 2.5**, cap 3.8 | 23.337(a): same formula, cap 3.8, category floors differ | `structural_speeds._maneuver_load_factors` per category; concept "C" = user-chosen | **Same formula** — only the 2.5 floor differs (bites above W ≈ 50,000 lb) | **P** |
| 25.337(c): negative **−1.0** to VC, linear to 0 at VD | 23.337(b): −0.4·n₁ (N/U), −0.5·n₁ (A) | MAN −C at −0.4n/−0.5n, MAN −D → 0 at VD (N) or −1.0·? at VD (U/A) | Same envelope *shape* as normal category; magnitude −1.0 fixed instead of −0.4n | **P** |
| 25.333 (envelope) | 23.333 | FLTLOADS corner-set + balance machinery | None structural — corner set membership changes (see gust rows) | **A** (machinery reused) |
| 25.345 (high-lift: n = 2.0 flaps + 25 fps gust; en-route flap condition) | 23.345 (same 2.0 g + 25 fps head-on gust) | Flap envelope R3/R4: STAL/MAN 2G/0G VF, GUST ±VF at 25 fps, BAL VF | Very close; *verify* the head-on-gust component and the 25.345(c) en-route-flaps condition (relates to L-5 enroute config) | **P** *(verify)* |

### 1.3 Design airspeeds

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.335(a) VC/MC: no formula minimum; must exceed VB by a margin *(verify exact wording)* | 23.335(a): VC ≥ K√(W/S) | K√(W/S) minima; advisory-only in concept mode | Part 25 has no wing-loading formula — VC is chosen against VB/gust and VMO intent | **P** — category-gate the GA minima off; add the VB-margin check |
| 25.335(b) VD/MD: VC/MC ≤ 0.8·VD/MD **or** margin = greater of upset criterion and **0.07M** (rational analysis w/ automatic systems may reduce; floor **0.05M**) — *verified 2026-07-20, see `reference/14CFR_MC_MD_speed_margin.md`* | 23.335(b)(4): margin = greater of upset and **0.05** (N/U/A) / **0.07** (commuter, rational floor 0.05) — verbatim in the same reference file | STRSPEED floors (b)(1)–(3) only; the (b)(4) margin route is discussed in Ref 1 p47 but never computed | 0.07 entered the Part 25 *rule* at Amdt 25-91 (eff. 1997-08-28); AC 25.335-1A (2000): 0.07 "sufficient without further investigation"; sub-0.07 in practice = HSPF-credited rational analysis (A350 SC template), typically >0.06 per FTHWG 2020 | **P** — "T" category defaults MD ≥ MC + 0.07; 0.05–0.07 only as explicit rational-analysis override (ties into M2-10 ladder, VMO/MMO form) |
| 25.335(c) VA = VS₁√n | 23.335(c) same | `va_min = VS√n` | None | **A** |
| 25.335(d) **VB** (rough-air speed; gust-line ∩ CLmax intersection formula) | 23.335(d) (commuter only; absent) | Not computed anywhere (noted in review; L-4) | New speed + a gust case at VB (see 1.4) | **N** |

### 1.4 Gust loads — the biggest gap

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.341(a) discrete **tuned** gust: 1-cos shape, gradient H tuned 30–350 ft, U_ref ≈ 56 fps (SL) → 44 fps (15,000 ft) → ~21 fps (60,000 ft) *(verify schedule)*, flight-profile alleviation F_g, **dynamic response** required | 23.341: Pratt static — n = 1 ± Kg·U_de·V·a/(498·W/S), U_de 50/25 fps tapering above 20,000 ft | Exact Pratt implementation (byte-for-byte vs FLTLOADS subr 4864) | **Generational.** But: pre-Amdt-25-86 FAR 25 used the *same Pratt method* — the program is effectively old-Part-25-compliant already | **S** — static surrogate: Pratt formula with the Part 25 U_ref schedule and F_g at VB/VC/VD; document that tuning + dynamic response are omitted (unconservatism unknown, typically ~10–20% on flexible airframes) |
| 25.341(b) continuous turbulence (PSD, App G) | — | — | Generational; needs a dynamic model | **X** — document |
| Gust at VB (rough air, 25.341 via 25.335(d)) | 23.341 commuter 66-fps line (dormant) | Not computed | Third gust line for the transport corner set | **N** (with VB, 1.3) |

### 1.5 Pitch maneuvers & horizontal tail

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.331(c)(1) unchecked: max elevator at VA, pitch-acceleration formula *(verify: believed identical 39n(n−1.5)/V lineage)* | 23.423(a)(1) via θ̈ = 39n(n−1.5)/V | SELECT unchecked-maneuver cases (exact to SELECT.BAS) | Possibly none — the formulas share CAR-4b lineage; *verify* the current 25.331(c)(1) text | **A/P** *(verify)* |
| 25.331(c)(2) **checked** maneuver: prescribed sinusoidal elevator motion, ω from VA…VD | 23.423 checked via the same θ̈ formula at C/D | SELECT checked cases at VC/VD | Part 25 prescribes an elevator time-history, not a θ̈ shortcut | **S** — static surrogate: keep the θ̈ method, tabulate vs the 25.331(c)(2) result once for a reference case; or implement the closed-form checked-maneuver n(t)/δ(t) evaluation (no dynamics beyond rigid-body pitch) |
| 25.427 unsymmetrical tail (span-wise distribution %, *verify current (b) percentages*) | 23.427 | 100%/50% split (SELECT.BAS; M1-4 restores full candidate set) | Percentage/shape differences | **P** *(verify)* |
| 25.349(a) rolling: 2/3·n₁ with aileron schedule (full at VA; p-matched at VC; p/3 at VD) *(verify)* | 23.349 similar | AC ROLL/ST ROL cases, deflection schedule per CAM 3.222(b)(3) | Schedule/factor deltas | **P** *(verify)* |

### 1.6 Yaw / vertical tail

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.351 yaw maneuver: 4-phase sequence (abrupt full rudder → overswing sideslip → steady sideslip → abrupt return), 1 g, VMC…VD | 23.441/443/445: maneuver sideslip (19.5°/15°), sudden full rudder, lateral gust | SELECT v-tail set: SUDDEN RUDDER, YAW 19.5/15, SIDE GUST (Kgt) | Part 25's sequence maps phase-by-phase onto the existing static cases; the **overswing** phase (transient sideslip > steady, factor ≈ 1.3–1.5 on the steady load) is the addition | **S** — add the overswing case as steady-sideslip × dynamic factor; *verify* the accepted factor; keep the Kgt lateral gust with the 25.341 U_ref |
| 25.353 rudder-reversal / yaw damper *(newer amendments — verify applicability)* | — | — | Post-statics addition | **X** — document |

### 1.7 Engine mounts & powerplant

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.361 engine torque (turbine mean/transient cases) | 23.361 | **Shipped** — `far25` supplement: 25.361(a)(3)(i)/(ii) with duplicate-dropping | — | **A** |
| 25.362 engine-failure dynamic loads (transient blade-out/seizure spectra) | — | — | Generational (dynamic FEM territory) | **X** — document |
| 25.363 engine-mount side load *(verify factor vs 23.363's max(1.33, n/3))* | 23.363 | max(n/3, 1.33)·T | Likely identical or minor | **P** *(verify)* |
| 25.367 asymmetric thrust ≈ 23.367 | 23.367 | ONENGOUT time-march | Part 25 applies to all engine types (not turboprop-scoped) — the M4-3 gate must be category-aware | **A/P** |
| 25.371 gyroscopic (refers to 25.331/341/351 conditions) | 23.371 fixed rates | **Shipped** — far25 gyro with declared-rate advisories (D-2) | Full 25.371 wants maneuver-derived rates — the declared-rate guard is the documented surrogate | **A** (surrogate documented) |

### 1.8 Pressurization & fuselage

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.365: ΔP × 1.33 (valve tolerance), combined with flight loads, external pressure cases *(verify sub-cases)* | 23.365 | Nothing (M4-6 plans the pressure case) | Part 25's combination rules (ΔP + maneuver/gust simultaneously; ΔP alone × factor) must shape M4-6 | **P/N** — fold into M4-6's acceptance |
| Body distributed loads (25.301/321 general) | Ch 15 method | `body_loads` (M4-1 fixes moment closure) | Same method serves once M4-1 lands + ground cases (M4-6) | **A** (after M4-1) |

### 1.9 Ground loads

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.473: sink **10 fps** at design landing weight, **6 fps** at MTOW; lift ≤ W during impact *(verify)* | 23.473: V = 4.4(W/S)^0.25 clipped 7–10 fps; L = 2/3·W in the energy method | LGFACTOR energy method (oracle-locked) | Same energy framework, different sink/lift/weight-pairing parameters | **P** — parameterize sink speed, lift ratio, and the LDW/MTOW pair |
| 25.479–485 landing attitudes/combinations (incl. rational spin-up/spring-back drag) | 23.479–485 (CAR-lineage combination tables) | LANDLOAD 33-case matrix | Part 25 wants rational gear dynamics for drag; the static combination tables are the old-generation surrogate | **S** — keep the tables, document; *verify* which combinations map |
| 25.491 taxi/takeoff-run (rational runway-profile dynamic analysis) | 23.493–499 braked roll etc. | LANDLOAD braked-roll/supplementary cases | Generational (dynamic taxi) | **S/X** — static bump-factor surrogate only, documented |
| 25.499/503/507/509/519 (nose-gear dynamic braking, pivoting, reversed braking, towing, jacking) | 23.499/507/509 subset | LANDLOAD supplementary nose + pivoting subset | Case-by-case deltas; towing/jacking absent | **P/N** *(verify per case)* |

### 1.10 Control surfaces & miscellaneous

| FAR 25 | FAR 23 | What the program does | Difference | Disp. |
|---|---|---|---|---|
| 25.395/397 control-system loads (pilot-effort schedule) | 23.395/397 | Not a suite analysis (loads on surfaces, not systems) | Same gap both parts — out of the suite's historic scope | **X** (document) or **N** later |
| 25.415 **ground gust** (hinge moments, K·q·c·S table) | 23.415 | **Not ported** (not one of the 22 programs) | Gap for *both* parts; cheap static table calc | **N** — small new module, serves 23 and 25 |
| 25.457/459 flaps/tabs | 23.457/459 | FLAPLOAD/TABLOADS (M1-9 fixes takeoff-power) | Parameter check only | **A/P** |

---

## 2 · Summary of the gap

Covered already (A): the limit/ultimate framework, the balance/corner-set
machinery, VA, engine torque + gyro supplements, ONENGOUT, flaps/tabs.
Parameter work (P): load-factor floor 2.5, negative envelope −1.0, GA speed
minima gated off, Mach-margin VD, flap-gust check, roll/yaw/unsymmetrical
schedules, landing sink/lift/weight parameters, side-load factor.
New-but-static (N/S): **VB + the transport gust corner set with the Part 25
U_ref schedule (the single most important item)**, MZFW design weight, checked
maneuver surrogate, yaw overswing case, ground gust module, towing/jacking.
Out of scope (X, documented): tuned-gust dynamics, continuous turbulence,
25.362, rational taxi, systems interaction (25.302/App K), rudder-reversal.

---

## 3 · Implementation plan — Phase F25 (post-0.3.0)

Pattern for every step: **opt-in supplement, FAR 23 path untouched** (the
shipped `engine.include_far25` flag is the template — additive conditions,
proper `far_reference`, duplicate-dropping, advisory notes). All Part 25
results carry the concept banner plus "FAR 25 static surrogate — not a
certification analysis." Every step starts by pulling and recording the
current CFR text for its rows (into `reference/`, like
`14CFR_Part25_engine_torque.md`).

**F25-0 — Verify pass (S).** Pull the current text for every *(verify)* row
above into `reference/14CFR_Part25_loads_extracts.md`; correct this table;
freeze the parameter set. *Do this once, first — everything else parameterizes
against it.*

**F25-1 — Transport category "T" envelope pack (M).** New category preset:
25.337 factors (floor 2.5), negative −1.0 → 0 at VD, GA speed minima off,
**VB per 25.335(d)**, transport gust corner set (VB/VC/VD lines) using the
Pratt engine with the **25.341 U_ref schedule + F_g**, MZFW design weight in
the envelope. Depends on M1-1/M1-2/M1-6 (envelope fixes) and reuses the
FLTLOADS machinery. Acceptance: the RJ fixture runs category "T" end-to-end;
closure suite extended; V-n plot shows the Part 25 shape; identity test —
category "T" with FAR 23 parameters reproduces the FAR 23 envelope.

**F25-2 — Speeds & placards, Part 25 variant (S).** 25.335 minima/margins
(VB margin on VC; MD ≥ MC + 0.05 / upset route) wired into `structural_speeds`
+ the M2-10 operational ladder in its VMO/MMO (no-yellow-arc) form — Ref 1 p47
already documents this linkage.

**F25-3 — Maneuver & tail surrogates (M).** Checked-maneuver 25.331(c)(2)
static evaluation (or documented equivalence of the θ̈ method); yaw overswing
case (steady sideslip × verified dynamic factor); 25.427 percentages;
25.349 roll schedule. All additive SELECT conditions.

**F25-4 — Ground-loads parameter variant (M).** LGFACTOR with 10/6 fps,
lift = W, LDW/MTOW pairing; LANDLOAD combination tables retained as the
documented static surrogate; towing/jacking as new static cases if wanted.
Depends on M4-6 (ground distributed loads) for the distributed follow-through.

**F25-5 — Pressurization & small gaps (S).** Part 25 combination rules into
M4-6's pressurization case; the 25.415/23.415 ground-gust hinge-moment module
(serves both parts).

**Explicitly not planned** (revisit only with a real need + tooling): dynamic
tuned-gust response, continuous turbulence PSD, 25.362 transients, rational
taxi profiles, Appendix K. If VSPAERO/OpenVSP integration lands (backlog
Future directions), a quasi-flexible gust re-examination becomes thinkable.

---

*Maintained under the doc-sync rule: rows change only with a `reference/`
extract recording the regulation text at the amendment level used.*
