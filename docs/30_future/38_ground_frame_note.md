# The ground-roll attitude's airplane-datum resolution rotates the wrong way

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: AGREED on GF-1/GF-2′; GF-3′ WITHDRAWN 2026-08-28 and the note is
AWAITING RE-AGREEMENT on the deviation surface (§1.11). A 2026-08-29 reading of
the newly legible p232 force cells as *refuting* GF-1 was withdrawn the same day
(§1.12) — the manual derives those cells from the angle they were taken to
test — but that reading's byproduct, the first transcribed p231/p232 cells,
is what GF-3″ was blocked on.** GF-3′ was agreed on a
scope that understated the deviation — it named the p230 arm table, and the
correction in fact moves printed **p231 ground-line reactions** by up to 40 %
(§1.11). The owner stopped implementation at that measurement rather than
proceed. **Nothing is built**: the GF-1/GF-2′ code and the GF-4 gate were
written, measured, and reverted. The note was reopened the same day when the GF-2 fix
site failed an existing closure gate (§1.8), then re-adjudicated from the
Appendix C listing: GF-1 is confirmed from a second, independent direction,
GF-2 is refuted and replaced by **GF-2′** (five tables, one sign — the
ground-roll lever arms move with the resolution), and GF-3 grows into **GF-3′**
(the deviation reaches the printed p230 arm row, where `DP` states a wheelbase
of 93.147 between contact points that are 94.811 apart). §1.8–§1.10 carry the
evidence and supersede §1.4.
Milestone 0.8.1 (re-milestoned 2026-08-28 when the patch band opened ahead of
0.9.0 — backlog re-cut 2026-08-28, ruling 1). Nothing built; the GF-1/GF-2 code
change was written, measured against the gates, and reverted. GF-6/GF-7 (the
reporting item, #134) are untouched by the reopening but are blocked behind it
by GF-6's own ordering condition.** Proposed and amended the
same day after the owner-directed Appendix C `.BAS` verification: GF-1 confirmed
at source level, OQ-1 resolved (revealing a second instance of the sign error,
§1.6), the application-point audit folded into GF-6, the flight-side α/β sweep
rows added at the owner's direction. Raised from the
owner's review of the ground/landing reference frames (in session, 2026-08-28),
aimed at the 2-point braked roll. Two deliverables share this note because they
share their machinery: **(a)** a first-order defect in the airplane-datum
resolution of every attitude-1 ground case, inherited from LANDLOAD.BAS and
adjudicated here against the manual's own printed output; **(b)** the
dual-frame reporting the original program ships and the replication does not —
the p231/p232 pair of tables, the per-case fuselage-axis angle, and the
airplane-datum load factors.

**Scope.** LANDLOAD computes every ground reaction in the **ground line** frame
(perpendicular/parallel to the ground through the contact patches) and then
resolves each resultant to the **airplane datum** (body FS/WL) through the
per-case angle `PHIM`/`PHIN`. The input geometry is body; `_geometry` rotates it
to the ground line per attitude through `GRA(1..3)`; the primed set
(`VMP/DMP/SMP`, `VNP/DNP/SNP`, `NVP/NDP/NS`, the unbalanced moments) is
ground-line; `vm/dm/vn/dn` are body. The body set is what the exported deck
cards and the gear reference-point loads consume — and for the attitude-1
families (braked roll 13–18, side 19–24, supplementary nose 25–33) it is
rotated the **wrong way**, by twice the ground angle. Separately, `run()` emits
only the ground-line set: the body resolutions, the per-case body-to-ground
angle, and the datum load factors never reach `ModuleResult`, so the Oracle
GUI, the CSV and Results Review are single-frame where the original printout is
two full tables.

**Sources reviewed (verified 2026-08-28, by rendering the scanned pages and
running ga6):** Ref 1 Appendix A **p230** (geometry: ground angles + BETA —
already oracle-locked), **p231** ("VALUES ARE WITH RESPECT TO GROUND LINE —
DENOTED BY P (PRIME)", with its per-family FUSELAGE AXIS ANGLE column) and
**p232** ("VALUES ARE WITH RESPECT TO AIRPLANE DATUM", with PHIN/PHIM and
NR/NV/ND) — the p231–233 scan is OCR-garbled as text (recorded in
`tests/test_landing.py`) but reads cleanly rendered at 200 dpi, which is what
unlocked p232 for this note; Appendix C **LANDLOAD.BAS listing** (scan
pp. 343/347 — the BETA/PHIM/PHIN assignments and the NV/ND datum-factor
equations, quoted in §1.1/§1.5). Code: `sloads/modules/landing.py` (`_geometry`,
`ground_angles`, `landing_reactions` PHIM/PHIN at :469–494, `_case_values`,
`run`), `sloads/gear_loads.py` (`ground_rotation_deg`, `to_airplane_datum`,
`_leg_load`), `sloads/modules/balance.py` (ground assembly, `GROUND_LIFT_CASES`),
`sloads/export/balanced_deck.py` (the NVP/NDP gate), `app/views/landing_loads.py`,
`oracle_app/results.py` (generic rendering). Conventions: `CONVENTIONS.md` §1
(frames), §Ground cases (G-1/G-6/G-7a).

---

## 1. What exists today (verified inventory, 2026-08-28)

### 1.1 The rotation, as coded and as printed

`beta = (gamma − gra1, gra2, gra3)` ([landing.py:229](../../sloads/modules/landing.py));
PHIM/PHIN are built from it per family (:471–490) and `vm = R·cos(PHIM)`,
`dm = R·sin(PHIM)`. The recovered body-to-ground rotation ρ per family, on
`ga6_normal` (GRA = 4.057 / 4.724 / 15.000 — p230, oracle-locked):

| cases | attitude | ρ applied | p232 PHIM printed |
|---|---|---|---|
| 1–6, 10–12 | level | **−GRA₁** = −4.057 | 13.921 = γ − GRA₁ |
| 7–9 | tail down | **−GRA₃** = −15.000 | −15.000 |
| 13–18 | ground roll (braked) | **+GRA₂** = +4.724 | 43.387 = atan(0.8) **+** GRA₂ |
| 19–24 | ground roll (side) | **+GRA₂** | 4.724 |
| 25–33 | ground roll (supp. nose) | **+GRA₂** | 43.387 / −17.079 / 4.724 |

The code reproduces the printed p232 table to the digit (case 1
vm 3208/dm 795; case 7 3900/−1045; case 16 2104/1989; case 19 2253/186) —
the replication is faithful. The defect is in the original, **confirmed at
source level** in the Appendix C LANDLOAD.BAS listing (scan pp. 343/347):

```basic
BETA(1)=GAMMA-GRA(1) : BETA(2)=GRA(2) : BETA(3)=GRA(3)
FOR L=1  TO 6 : PHIM(L)=BETA(1)               ' level:     γ − GRA₁  (subtracts)
FOR L=7  TO 9 : PHIM(L)=-BETA(3)              ' tail-down: −GRA₃     (subtracts)
FOR L=13 TO 18: PHIM(L)=ATN(.8)*57.3+BETA(2)  ' braked:    +GRA₂     (adds) ← GF-1
FOR L=19 TO 24: PHIM(L)=BETA(2)               ' side:      +GRA₂     (adds)
```

with the same `+BETA(2)` pattern in `PHIN` for cases 13–15 and 25–33.

### 1.2 The adjudication: the manual is internally inconsistent

The geometric sense of the ground angle is one convention throughout:
`_ground_angle` is a single formula, and with the p230 axle inputs both the
compressed line (Δz 9.0 in over 94.4 in) and the static line (10.1 over
94.3 in) **rise going aft in body coordinates** — so in both attitudes the
airplane sits **nose-up by GRA** relative to the ground. With one convention,
the body angle of the resultant is *(its ground-line angle) − GRA* in every
attitude. The printout subtracts for level (17.978 − 4.057 = 13.921 ✓) and for
tail down (0 − 15 = −15.000 ✓), and **adds** for ground roll (atan(0.8) +
4.724 = 43.387 ✗, physically 33.936). p230 telegraphs it: the printed
definition "BETA = GAMMA − GROUND ANGLE" is followed four lines later by "BETA
FOR GROUND ROLL = +4.724" — the ground angle itself, sign discarded, then
*added* in PHIM. `gear_loads.py` (:224–229) already records the inconsistency
in prose; this note adjudicates it.

**This reverses a standing decision.** The register already holds a
"Considered and declined" entry for this exact question —
[*"LANDLOAD's ground-roll attitude resolves at `+BETA(2)`" (declined
2026-08-15 — replicate as printed)*](../20_theory/02_approved_corrections.md) —
taken when the p231–233 airplane-datum table was OCR-garbled and the case
rested on the geometry argument alone. That entry states its own reopening
condition ("should a legible … output surface, this entry is where the
question resumes"), and this note is the resumption: the p232 table now reads
legibly (rendered at 200 dpi rather than through the OCR layer), the verbatim
Appendix C `.BAS` lines are confirmed, the printed page is internally
inconsistent against its own level/tail-down rows, and §1.6 finds a second
instance of the same sign error in the datum load-factor lift term. The
declined decision is **superseded by this note's owner agreement**; its pin
test — `tests/test_gear_report.py::
test_the_ground_roll_attitude_is_resolved_against_the_other_sign`, which
asserts ρ = +GRA on the ground-roll attitude — goes red under GF-2 *by
design* and is **flipped, not deleted**, when #133 lands (it becomes a pin of
the corrected convention, citing the superseding register entry).

### 1.3 The effect, measured (ga6, 2026-08-28)

Error = 2·GRA₂ = **9.448°** of resultant direction on every attitude-1 case.
Ground-line values (and the p230/p231 oracles) are untouched; only the body
resolutions move:

| case | family | as coded vm / dm | corrected vm / dm | Δ |
|---|---|---|---|---|
| 13 | braked, nose down (main) | 1306.9 / 1235.2 | 1491.6 / 1003.8 | **+14 % / −19 %** |
| **14** | (nose) | 2037 / +168 | 2037 / **−168** | drag sign flips *(corrected 2026-08-28: this row is case **14**, not 13 — case 13's nose pair is 1707.8 / −141.1. Every main-gear figure in this table reproduced exactly when measured.)* |
| 16 | **braked, nose clear** | 2104.3 / 1988.9 | **2402.3 / 1616.4** | **+14 % / −19 %** |
| 19–24 | side | 2253 / +186 | 2253 / **−186** | drag sign flips |
| 25 | supp. nose aft | 1094 / 1034 | 1248.6 / 840.2 | +14 % / −19 % |
| 26 | supp. nose fwd | 1210 / −372 | 1132.6 / −565.4 | −6 % / +52 % |
| 27 | supp. nose side | 1171 / +97 | 1171 / **−97** | drag sign flips |

First-order on shipped output: these are the numbers the **exported FORCE
cards** and the **gear reference-point loads** carry ("The exported cards
themselves take LANDLOAD's vm/dm directly" — `gear_loads.py`). The side
family's flip is qualitative — a purely ground-vertical reaction currently
acquires an *aft* body drag component where the airplane, sitting nose-up,
must see it *forward*.

### 1.4 Why no gate caught it

The G-6 closed-form gate rotates the solved rigid-body field back to the
ground line through ρ — but ρ is **recovered from the case's own two
resolutions** (`ground_rotation_deg`), precisely so the gate never adjudicates
the LANDLOAD sign. Self-consistent by construction: it verifies the rotation
was applied, not that it was applied the right way. The assembled ground cases
re-solve equilibrium from the applied (wrong-way) reactions, so they close in
six DOF regardless. The G-7a ground-line lift axis reads ρ only on cases 1–12
(`GROUND_LIFT_CASES`), which carry the correct sign — unaffected.

### 1.5 The reporting gap (deliverable b)

The original printout ships, and `run()` does not:

1. **The fuselage-axis angle per case** — p231 carries a FUSELAGE AXIS ANGLE
   column (4.056955 / 15 / 4.724467 deg per family). No angle is emitted
   anywhere in `ModuleResult`; the main GUI shows GRA only on the gear
   free-body table.
2. **The airplane-datum table** — p232 prints the full matrix a second time
   (PHIN/PHIM, VN/DN/SN, VM/DM/SM, resultants). `vm/dm/vn/dn` live on
   `GearReactionCase` but never reach `ModuleResult`, so the Oracle GUI, the
   CSV and Results Review are single-frame.
3. **The airplane-datum load factors NR/NV/ND** (p232 right-hand columns,
   e.g. 3.287/3.216/0.679 on case 1) — not computed at all; only the
   ground-line NVP/NDP/NS ship.
4. **Frame labels** — the main GUI's landing page says "(ground line)"; the
   Oracle's generically-rendered per-case tables say nothing, while the deck
   consumes the other frame.

5. **The application point** — each case's contact patch, its attitude
   (strut state + ground angle) and the trunnion node it is transferred to
   live only in the gear free-body report and the deck; the per-case
   `ModuleResult` identifies none of them, so the Oracle GUI and the CSV state
   loads with neither a frame nor a point of application.

**OQ-1 — resolved 2026-08-28 from the `.BAS` (was: the printed ND
derivation).** The datum factors are Σ(datum components)/W **plus the lift
factor rotated into body axes** on the lift-carrying cases, and
NR = √(NV²+ND²):

```basic
FOR L=1 TO 6:   NV(L)=LF*COS(GRA(1)/57.3)+(VN(L)+2*VM(L))/WL(L)
FOR L=10 TO 12: ND(L)=LF*SIN(GRA(1)/57.3)+DM(L)/WL(L)
```

Case 1 reproduces exactly: ND = 0.667·sin 4.057° + 2042/3230 = 0.047 + 0.632
= 0.679 ✓. **But the lift term is a second instance of the sign error**
(§1.6): `+LF·SIN(GRA)` puts the lift's body drag component *aft*, where the
nose-up convention — and sloads' own assembled deck, which applies the ground
lift as `(L·sin ρ, 0, L·cos ρ)` with ρ = −GRA
([balance.py:2282](../../sloads/modules/balance.py)) — puts it *forward*.

### 1.6 The second instance, and the corroboration (from the `.BAS` check)

> **Contingent on GF-1 (marked 2026-08-28).** The "second instance" below is
> the *same* sign question in the datum load-factor lift term, so it stands or
> falls with GF-1 and is reopened with it (§1.8). The corroborations — NR's
> frame invariance and the contact-patch construction — are independent of the
> adjudication and stand.

* **The datum ND lift term** carries `+sin(GRA)` where the physics gives `−`.
  It affects only the to-be-built NR/NV/ND reporting (GF-6) — the assembled
  deck's lift is already correct — and it adds two p232 cells per
  lift-carrying case to GF-3's deviation register: corrected case 1 is
  **ND 0.585, NR 3.269** vs printed 0.679/3.287 (NV unchanged, cos is even).
* **NR is frame-invariant on the wheels-only cases, and the GF-1 fix
  preserves it**: case 16 NV/ND 1.238/1.170 → 1.413/0.951 corrected, NR 1.703
  both ways, matching the printout — an independent consistency check on the
  corrected rotation.
* **The contact-patch construction corroborates the nose-up convention**:
  `patch = axle + r·(sin GRA, −cos GRA)` ([gear_loads.py:178](../../sloads/gear_loads.py))
  is the ground-down unit vector of a nose-up airplane; the geometry side of
  LANDLOAD treats GRA in the sense GF-1 adjudicates, making the PHIM add the
  outlier, not the convention.
* **The wrong-way force propagates into the transfer couples** —
  `transfer_couple(patch, node, force)` takes the airplane-datum force — but
  the couple is derived, so GF-2's fix corrects force and couple together
  with no additional code (recorded under GF-5).

### 1.7 The application-point chain (verified sound, 2026-08-28)

Audited end-to-end, no defect: each case's patch is built at its **own
attitude** (compressed axles for cases 1–12, static for 13–33 — the manual's
split, single-owner `attitude_of`); main wheels mirrored at ±tread/2 on their
own nodes, nose on centreline; the 23.483 family drops the port wheel; the
23.485 family takes the partner case's SMP sign-flipped; the transfer to each
trunnion (`leg.attach`, deck GIDs 10001+, carrier BODY/WING stated) carries
the exact lever-arm couple, guarded at `rel_tol 1e-12`. What is missing is
item 5 above — the *output* does not identify the point — which GF-6 now
covers.

---

### 1.8 GF-1/GF-2 falsified as scoped (2026-08-28, found implementing them)

**The correction was written exactly as GF-1/GF-2 specify, measured, and
reverted.** It reproduces every main-gear figure of §1.3 to the digit
(case 13 vm/dm 1491.9/1003.9; case 16 2402.3/1616.4; case 26 1132.6/−565.3) and
leaves `test_landing.py` green — so **G-GF-1 holds**: the p230/p231/p236 oracles
and every primed quantity really are untouched. It then fails a gate this note
did not consider.

**The gate.** `test_gear_report.py::
test_the_ground_closure_reproduces_landloads_unbalanced_moments` compares
LANDLOAD's stated unbalanced pitching moment against a reconstruction from the
assembled case. It is **not** the self-referential shape §1.4 describes:
`pitchp` is built only from primed quantities (`rmp`, `vmp`, `dmp`) and the
p230-locked `bp`/`cp` arms and never reads `phim`/`phin`, and a moment about y
is invariant under a rotation about y — so ground-line `pitchp` and the
body-frame `M_y` are directly comparable. It is an **independent, absolute**
reference for the rotation, which is exactly what §1.4 says no gate provides.

Residual as a fraction of W·MAC, `ga6_normal`:

| case | printed `+GRA₂` | GF-1's `−GRA₂` | gate tolerance |
|---|---|---|---|
| 13 (braked roll) | 0.00322 | **0.11777** | 5e-2 |
| 16 (braked, nose clear) | 0.00578 | **0.10565** | 5e-2 |
| 19 (side) | **0.00001** | **0.10566** | 1e-4 |

Case 19 closes to **1e-5** against the sign the manual prints. That is
machine-level agreement with an independent reference, and GF-1 destroys it.

**Why — and this is a hole in GF-2, not merely a failed test.** `_geometry`
builds the AP/BP/DP/CP lever arms from **the same `beta` tuple** that feeds
PHIM/PHIN (`fn_bp(xm, xcg, b, ...)` with `b = beta[attitude]`). GF-2 rules the
fix site to be "the PHIM/PHIN tables only … `_geometry`, `beta` and the
p230-locked lever arms untouched" on the premise that they are independent.
**They are not.** `beta[1]` is consumed twice — as the lever-arm frame and as
the resultant direction — and LANDLOAD uses it coherently in both places.
Correcting one and not the other makes the module internally inconsistent, and
0.106·W·MAC is the size of that inconsistency.

**What this does and does not establish.** It does *not* show the manual is
right; §1.2's geometric argument is unrefuted, and `_ground_angle` being a
single formula (checked 2026-08-28) confirms GRA₁ and GRA₂ do share one
geometric sense, as §1.2 asserts. What it shows is that **the defect, if it is
one, is wider than the fix site this note authorised** — and that its
continuation runs straight into the p230-locked lever arms, which reproduce the
printout and cannot simply move.

**The inhomogeneity the re-adjudication has to resolve.** `BETA` is not one kind
of quantity across the attitudes:

* level — `BETA(1) = γ − GRA₁`, a **resultant-direction** angle (it carries the
  flight-path angle γ), used directly as `PHIM(1–6)`;
* ground roll — `BETA(2) = GRA₂`, a bare **ground** angle, used as
  `PHIM = atan(0.8) + BETA(2)`.

§1.2 compares the two as though both were ground angles. They are not, and the
same two values also rotate the lever arms. Until that is settled, the sign
question cannot be answered from the printed p232 rows alone.

**Open questions for the re-adjudication.**

* **OQ-2** — what frame are the AP/BP/DP/CP arms actually in, per attitude, and
  is `BETA`'s double duty (lever-arm rotation *and* resultant direction)
  faithful to the `.BAS` or an artefact of the port? The Appendix C listing
  around the arm assignments answers this and was not read for this note.
* **OQ-3** — if GF-1's geometry holds, what happens to the attitude-1 lever
  arms, which are p230-oracle-locked and reproduce the printout? Either they
  are in a frame where `+GRA₂` is correct (and PHIM is too), or the deviation
  is far larger than GF-3 contemplates.
* **OQ-4** — does the case-19 `1e-5` closure survive on the other fixtures with
  a non-trivial GRA₂ (`cessna_210`, GRA₂ = 4.810)? `atr42_100` and
  `dhc8_dash8` carry GRA₂ ≈ 8e-5 deg and cannot discriminate.

**Process note.** This is the benchmark-first rule (`CLAUDE.md` rule 2) doing
the work it exists for: the note's own §1.4 asserted that no gate could
adjudicate the sign, and an existing gate adjudicated it in the first minute of
implementation, against the note. §1.4 is wrong as written and is superseded by
this section. **The register's 2026-08-15 "Considered and declined" entry is
therefore NOT superseded** — GF-3's conversion does not proceed, and the entry
stands as written until GF-1 is re-adjudicated.

---

### 1.9 OQ-2/OQ-3 resolved from the `.BAS` (2026-08-28): GF-1 supported, GF-2 refuted

**OQ-2 — what frame are the lever arms in?** Read from the Appendix C listing
(`reference/code.txt`, the J-blocks at lines 560–720). The rotation each arm
takes is per attitude, and it is **not** one kind of quantity:

```basic
' J=1 level          BP,DP take BETA(1) = GAMMA - GRA(1)   (a resultant direction)
' J=3 tail down  640 BP(3,I)= ... COS(GRA(3)/57.3) ...     (a ground angle)
' J=2 ground roll
670 J=2
680 AP(2,I)=FNAP(XCG(I),XNG(2),GRA(2),ZCG(I),ZNG(2))       ' GRA(2)
690 BP(2,I)=FNBP(XMG(2),XCG(I),BETA(2),ZCG(I),ZMG(2))      ' BETA(2)
700 DP(2,I)=FNDP(XMG(2),XNG(2),BETA(2),ZMG(2),ZNG(2))      ' BETA(2)
712 CP(2,I)=(ZCG(I)-ZS)*COS(GRA(2)/57.3)                   ' GRA(2)
```

with `BETA(2)=GRA(2)`, so all four are the same number on the ground-roll
attitude. **`sloads` ports every one of these exactly** (`ap[1]`/`cp[1]` from
`gra2`, `bp[1]`/`dp[1]` from `beta[1]`). So `BETA`'s double duty — rotating the
lever arms *and* giving the resultant direction — is **faithful to the original,
not a port artefact**, and the coupling §1.8 identified is in LANDLOAD itself.

**The geometric premise re-checked and confirmed.** On `ga6_normal` the main
axle is aft of and above the nose axle in **both** states (compressed
Δx 94.40 / Δz +9.00; static Δx 94.30 / Δz +10.10; `cessna_210` likewise), so
both ground lines rise going aft and GRA₁/GRA₂ share one geometric sense.
**§1.2 stands.**

**The decisive experiment.** Flipping the ground-roll **lever-arm rotation and**
the PHIM/PHIN tables together, closure residual as a fraction of W·MAC:

| case | as printed | GF-2 (PHIM only) | arms **and** PHIM |
|---|---|---|---|
| 13 | 0.00322 | 0.11777 | **0.00000** |
| 16 | 0.00578 | 0.10565 | **0.00003** |
| 19 | 0.00001 | 0.10566 | **0.00002** |

The complete correction closes LANDLOAD's own unbalanced pitching moments
**better than the printed numbers do**. The 0.003–0.006 residual on cases 13–18
that forced `test_the_ground_closure_...` to carry a `5e-2` tolerance where the
rest of the matrix holds `1e-4` — documented in that test as "the ground-roll
attitude's frame difference, which no rotation in the check can remove" — **is
the defect, and it goes to zero when the correction is complete.** That is
independent corroboration of GF-1 from a direction §1.2 never used.

**OQ-3 — what does it cost?** Exactly **one** printed table. With both flipped,
`test_landing.py` fails only `test_landload_lever_arms_oracle`; every p231
ground-line reaction lock and the p236 LGFACTOR locks still pass:

| arm (ground roll, 3 CG cases) | as printed / p230 | corrected |
|---|---|---|
| AP(2,·) | 78.836 / 69.886 / 66.501 | 86.001 / 77.052 / 73.501 |
| BP(2,·) | 14.311 / 23.260 / 26.646 | 8.809 / 17.759 / 21.309 |
| DP(2,·) | 93.147 | 94.811 |
| CP(2,·) | 42.241 / 42.981 / 42.271 | **unchanged** (cos is even) |

**Standing after this section:** **GF-1 is supported** — more strongly than by
§1.2 alone, and now from an independent reference. **GF-2 is refuted**: the fix
site is not the PHIM/PHIN tables, and the correction reaches the p230-locked
ground-roll lever arms. **GF-3 must grow** to record the p230 AP/BP/DP
ground-roll row above alongside the p232 rows.

**OQ-5 (new, and the remaining work).** The experiment above flipped all three
arm rotations *indiscriminately*, which is enough to locate the fix site and not
enough to specify it. AP and CP take `GRA(2)` while BP and DP take `BETA(2)`;
whether each is a resultant-direction rotation (which flips) or a ground-line
projection where `GRA(2)` enters as a magnitude (which does not) needs the
per-arm geometric derivation against `FNAP`/`FNBP`/`FNDP`. CP is already known
not to move — it enters through `cos`, an even function. **No code until OQ-5 is
answered per arm**, since a partial flip is exactly the incoherent state GF-2
produced.

---

### 1.10 OQ-5 answered (2026-08-28): all three arms flip, CP does not

**`FNBP` simplifies to a projection.** From the Appendix C definitions:

```basic
DEF FNAP(XCG,XNG,B,ZCG,ZNG) = (XCG-XNG)*COS(B) - (ZCG-ZNG)*SIN(B)
DEF FNDP(XMG,XNG,B,ZMG,ZNG) = (XMG-XNG)*COS(B) - (ZMG-ZNG)*SIN(B)
DEF FNBP(XMG,XCG,B,ZCG,ZMG) = (XMG-XCG)/COS(B) + ((ZCG-ZMG)-(XMG-XCG)*TAN(B))*SIN(B)
```

with `a = XMG-XCG`, `c = ZCG-ZMG`:

    BP = a/cos b + (c - a·tan b)·sin b = a(1-sin²b)/cos b + c·sin b = a·cos b + c·sin b

So **all three are plain projections onto a direction rotated by `b`** — the
`/cos` and `tan` are algebra, not a different construction. The question OQ-5
asks ("resultant-direction rotation, or a magnitude in a ground-line
projection?") therefore has one answer for all three: they are ground-line
projections, and the only question is the sign of the rotation.

**The sign, settled without reference to any convention.** GRA is *defined* as
the axle-line slope less the radius correction, so the contact line lies at
**+GRA in body axes** (ga6 ground roll: axle line 6.1134°, correction 1.3893°,
GRA 4.7241°) — the ground rises going aft, i.e. the airplane is nose-up, as
§1.2 argued. The ground-parallel unit vector is therefore
**u = (cos GRA, +sin GRA)**, and the printed arms project onto
`(cos GRA, −sin GRA)`.

**`DP` decides it on its own.** DP is the wheelbase along the ground line — the
distance between the two contact points. That is the distance between two
points and admits no sign convention:

    |patch_main − patch_nose| = 94.811   (ga6, ground roll)

against a printed **93.147**. The corrected projection returns 94.811 exactly.

| arm (ground roll, 3 CG cases) | printed p230 | true ground-line projection |
|---|---|---|
| DP(2,·) | 93.147 | **94.811** |
| AP(2,·) | 78.836 / 69.886 / 66.501 | **86.002 / 77.052 / 73.502** |
| BP(2,·) | 14.311 / 23.260 / 26.646 | **8.810 / 17.759 / 21.310** |
| CP(2,·) | 42.241 / 42.981 / 42.271 | **unchanged** — enters through `cos`, even |

Two internal checks: projecting from the **contact patch** and from the **axle**
give identical values (the patch offset is along the ground *normal*, so it
contributes nothing to a ground-parallel projection); and the derived values
reproduce §1.9's closure experiment to three decimals, which was measured
independently.

**OQ-5: answered. AP, BP and DP all take the corrected rotation; CP is
untouched.** The fix site is therefore `AP(2,·)`, `BP(2,·)`, `DP(2,·)`,
`PHIM(13–24)` and `PHIN(13–15, 25–33)` — five tables, one sign.

---

### 1.11 The deviation surface is larger than GF-3′ stated (2026-08-28)

GF-2′ was implemented and measured before commit. The correction behaves exactly
as §1.9/§1.10 predict — case 13's pre-closure residual pitching moment falls from
**−757.1 to −0.7 lb-in**, and `test_the_ground_closure_reproduces_landloads_
unbalanced_moments` passes on every case with no loosened tolerance. But the arms
feed the **reaction solve**, not only the moment bookkeeping, so the deviation
reaches the printed p231 table:

| cases | quantity | as printed → corrected |
|---|---|---|
| 13–15 (braked, nose down) | VMP / DMP / RMP | 1404.19 → 1511.99 (**+7.7 %**) |
| 13–15 | VNP | 1713.61 → 1498.01 (**−12.6 %**) |
| 13–15 | NDP | 0.6608 → 0.7115 |
| 16–18 | PITCHP | −217525 → −192645 (−11 %) |
| 19–24 | PITCHP / YAWP | −64714 → −39834; ∓40386 → ∓24859 (**−38 %**) |
| 25–33 (supplementary nose) | VNP / DNP / SNP / RESULT | case 25 1175.34 → 710.77 (**−40 %**) |

**The driver is `BP`** — the CG-to-main-gear ground-parallel arm — at
14.311 → 8.810 (−38 %); the nose reaction is `W·BP/DP`.

**The evidence still favours the correction, and one argument is new.** A
ground-parallel arm cannot depend on whether it is measured to the axle or to
the contact patch: the patch offset is along the ground **normal**, so it
contributes nothing to the projection. Under the corrected rotation both give
**8.810**. Under the printed rotation they give **14.311** (axle) and **15.63**
(patch), differing by `2·r·sin GRA`. **The printed sign fails a self-consistency
test that makes no reference to the frame argument at all.** The families' FAR
relations also survive the correction unchanged (`DMP = 0.8·VMP`,
`VNP = 1.33·W − 2·VMP`, `DNP = 0.8·VNP`).

**Why no oracle caught the size of this.** `test_landing.py`'s printed-value
locks cover **case 1** (VMP 3144, VNP 1787, RESULT 1879) and **case 19's VMP
(2261)** — all level or side, all unmoved by the correction. Cases 13–15 and
25–33 are pinned only by *internal identities*, which hold under either sign
because they are relations rather than printed values. **The p231 oracle
coverage has a hole exactly where this deviation lands**, which is why a 40 %
move in the supplementary nose reactions leaves the module's oracle suite green
but for the arm table. That is a practice-3 gap in its own right and is
independent of how the sign question is ruled — see the open finding below.

**GF-3″ (to be drafted, replacing the withdrawn GF-3′).** The register entry
must state the whole deviation surface — p230 arms, p231 cases 13–15 and 25–33,
p232 datum — with each deviated-from value transcribed from the rendered page
rather than computed from the pre-fix code, and the corrected expectation beside
it. Until that entry is drafted and agreed, **no code**.

**Open finding — the p231 lock hole (filed 2026-08-28, rule 5).** Independently
of GF-1: the braked-roll and supplementary-nose families carry no printed-value
oracle, on any fixture. Whatever is ruled here, those rows should be locked to
p231 as printed (or, if the deviation is approved, to the corrected values with
the register entry beside them) so the families stop resting on identities alone.
Sized S; it is the assertion that would have made this whole question visible in
2026-08-15 rather than 2026-08-28.

---

### 1.12 The p232 force cells do not adjudicate the sign (2026-08-29, withdrawn same day)

Reading the rendered p231/p232 for the `WR` defect (#135) and the light-landing
weight (#137) produced the braked-roll family's first printed-value oracle,
including case 18's airplane-datum pair, **Fz 1733 / Fx 1638**. That pair
reproduces to 0.06 % under the shipped `PHIM = atan(0.8) + GRA₂` (1733.0 /
1637.9) and misses by 14 % / 19 % under GF-1's `atan(0.8) − GRA₂` (1978.4 /
1331.2), and was recorded that morning as refuting GF-1 from a printed number.

**It does not, and the claim is withdrawn.** The Appendix C listing computes the
force cells *from* the angle cell:

```basic
L=13 TO 18:PHIM(L)=ATN(.8)*57.3+BETA(2)          ' code.txt:36319
VM(L)=RMP(L)*COS(PHIM(L)/57.3)                   ' code.txt:36346
DM(L)=RMP(L)*SIN(PHIM(L)/57.3)                   ' code.txt:36347
```

p232's PHIM column and its VM/DM columns are one printed quantity, not two. The
pair therefore confirms exactly two things — that `RMP(18)` is right (already
locked from p231) and that this port reproduces the manual's rotation faithfully
— and carries no information about whether that rotation is the correct one.
GF-1's claim is that the printed values are wrong; an arithmetic identity among
the printed values cannot answer it. **This is the note's own §4 class, one turn
further out**: a check that recovers its reference from the thing it checks. §1.4
found it in the G-6 gate; here it appeared in the adjudicator's own reasoning.

**What the reading is actually worth to this item — which is more than nothing
and is on the critical path.** GF-3″ is blocked on transcribing the whole
deviation surface from the rendered pages rather than computing it from the
pre-fix code (§1.11), and these are the first cells so transcribed: p231 cases
16/17 (VMP 2261 / DMP 1808.8) and 18 (1862 / 1490), and p232 case 18 (Fz 1733 /
Fx 1638). They are deviated-from values in the register, not evidence for it.
The reading also removed one hazard silently: the p231 cells that GF-3″ must
record were, until #137, unusable as a reference at all, because a fixture input
had been back-solved from one of them.

**GF-1's standing is unchanged.** The evidence remains where §1.10/§1.11 left it:
the manual's own level (`GAMMA − GRA₁` = 13.921) and tail-down (`−GRA₃` =
−15.000) rows resolve as `θ − GRA`, the ground-roll row alone as `θ + GRA`
(§1.2); `DP`'s wheelbase between two contact points is 94.811 against a printed
93.147, which needs no frame convention (§1.10); and a ground-parallel arm
measured to the axle and to the patch agree only under the corrected rotation
(§1.11). Against that, the cost is a deviation surface reaching printed p231
reactions by up to 40 %. The note stays **AWAITING RE-AGREEMENT on GF-3″**; no
code.

---

## 2. Decisions (GF-1 … GF-8)

| # | Decision | Rationale |
|---|---|---|
| **GF-1** | **The attitude-1 airplane-datum resolution is adjudicated a defect in LANDLOAD.BAS**: the physical PHIM/PHIN subtract the ground angle in every attitude. Corrected: PHIM(13–18) = atan(0.8) − GRA₂; PHIM(19–24) = −GRA₂; PHIN(13–15) = −GRA₂; PHIN(25/28/31) = atan(0.8) − GRA₂, (26/29/32) = atan(−0.4) − GRA₂, (27/30/33) = −GRA₂. | §1.2. The manual's own level and tail-down rows prove the convention; the ground-roll rows violate it. |
| **GF-2′** *(proposed 2026-08-28, replacing the refuted GF-2)* | **Fix site is five tables, one sign: `AP(2,·)`, `BP(2,·)`, `DP(2,·)` (`_geometry`, ground-roll attitude only) and `PHIM(13–24)` / `PHIN(13–15, 25–33)`.** `CP(2,·)` is untouched (enters through `cos`); the level and tail-down attitudes are untouched; `beta` itself, `gamma` and the `FNAP`/`FNBP`/`FNDP` definitions are untouched — only the rotation handed to them on attitude 1. ~~Fix site is the PHIM/PHIN tables only~~ (REFUTED §1.9: correcting the resultant direction while leaving the arms produces an incoherent module, measured at 0.106·W·MAC) ([landing.py:471–490](../../sloads/modules/landing.py)). `_geometry`, `beta`, and the p230-locked AP/BP/DP/CP lever arms are untouched; every primed (ground-line) quantity is untouched. | The lever arms and the primed set are oracle-locked and *correct* — the ground-line equilibrium closes (NVP identities). Only the frame resolution is wrong. Smallest true fix site. |
| **GF-3′** *(WITHDRAWN 2026-08-28 — understated the deviation surface; see §1.11 and GF-3″)* | The register entry additionally records the **p230 ground-roll lever-arm row** — AP 78.836/69.886/66.501 → 86.002/77.052/73.502; BP 14.311/23.260/26.646 → 8.810/17.759/21.310; DP 93.147 → 94.811 (§1.10) — with DP's independent check as the headline evidence: the wheelbase along the ground line is the distance between two contact points, 94.811, and the printout states 93.147. `test_landload_lever_arms_oracle` is **re-pinned to the corrected arms**, not deleted, citing this entry. | The p230 table is a printed oracle; departing from it needs the register, and DP's discrepancy is the cleanest statement of the defect in the whole note — it needs no frame argument at all. |
| **GF-3** | **This is an approved oracle deviation**: an entry in [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md) recording the printed p232 values deviated from (43.387 / −17.079 / +4.724 and the vm/dm rows of §1.3, **plus the ND/NR cells of the lift-carrying cases per §1.6** — case 1: ND 0.679 → 0.585, NR 3.287 → 3.269) and the corrected expectations, owner-approved in the PR. The p232 **level and tail-down force** rows, which are correct, become new oracle locks (±0.1 %); the wheels-only **NR** values lock as printed (frame-invariant, §1.6). The entry **supersedes the register's "Considered and declined" decision of 2026-08-15** on the same question (§1.2): the declined entry is converted in place (declined → approved deviation, with the new evidence and a pointer to this note), and its pin test `test_the_ground_roll_attitude_is_resolved_against_the_other_sign` is flipped to pin ρ = −GRA on every attitude, never deleted. | The register is the process for departing from a printed oracle (`CLAUDE.md` §Math fidelity). Locking the rows that are right while deviating from the rows that are wrong is exactly what the register exists to state — and the declined entry's own text names this note's evidence as its reopening condition. |
| **GF-4** | **ρ gets an absolute gate**: `ground_rotation_deg(case) == −GRA(attitude of case)` for every case, against `ground_angles` directly, exact (1e-9), all bundled examples. The gate's docstring states its assumption: the nose-up sense of GRA (§1.2's proof) was derived on **tricycle geometry**, the only arrangement the suite models — a tail-wheel configuration would re-open the sign derivation, not inherit it. | §1.4 — the existing G-6 gate is self-consistent and structurally cannot catch a sign error. This converts the documented anomaly in `gear_loads.py:224–229` from prose into an assertion (practice 3), and that prose is rewritten to describe history, not behaviour. |
| **GF-5** | **Downstream re-verification rides the existing CI gates**: the assembled ground cases re-close in six DOF from the corrected reactions; the sbeam round-trip stays green; the gear reference-point loads **and the patch-to-trunnion transfer couples** move with `vm/dm` (§1.6 — the couple is derived from the force, so it co-corrects with no additional code). No consumer needs code changes. | The consumers were built to trust `vm/dm`; correcting the producer corrects them all. G-7a is untouched (§1.4); the application-point chain itself is verified sound (§1.7). |
| **GF-6** | **`run()` ships the airplane-datum set alongside the primed set** (deliverable b): per case ≤ 24, `vm/dm/vn/dn`, the fuselage-axis angle (units `deg`, never SF-scaled, like the dimensionless factors), **and the application point** — the contact-patch coordinates, strut state and reference node per leg (§1.5 item 5); cases 25–33 the nose pair; the NR/NV/ND datum factors per OQ-1's resolved formula **with the lift term's corrected sign** (§1.6). Lands **with or after GF-1** — never before, so the wrong-sign numbers are never promoted into the deliverable. | §1.5. The replication's deliverable is thinner than the 1990 printout it replicates; M4-17e closed that gap for the primed set and stopped there. The stress model needs body-frame loads with stated application points; today's deliverable states neither. |
| **GF-7** | **Every reactions table names its frame, in both GUIs**, using the manual's own words — "with respect to ground line" / "with respect to airplane datum" — one caption owner in `app_shell` with a drift guard, not two prose copies. | §1.5 item 4; practice 3. The Oracle currently shows unlabeled ground-line numbers while the deck consumes body — a reader moving between them has no stated bridge. |
| **GF-8** | **Split delivery: GF-1…GF-5 are the defect item (tier L); GF-6/GF-7 are the reporting item (tier M)**, ordered defect-first. | Rule 6: a first-order defect on shipped content outranks the fidelity item; and GF-6 must not ship the pre-fix numbers (GF-6's own condition). |

---

## 3. Closure gates (G-GF-1 … G-GF-6)

Benchmark-first (rule 2). Identities exact (`rel_tol=1e-9`); oracle locks ±0.1 %.

| Gate | Statement | Expected numbers |
|---|---|---|
| **G-GF-1** (oracle invariance) | p230 geometry and p236 LGFACTOR locks pass **unmodified**; the p231 ground-line spot-locks pass unmodified (every primed quantity bit-identical across the fix). | GRA 4.057/4.724/15.000; VMP case 1 3144, case 19 2261 |
| **G-GF-2** (new p232 locks, the correct rows) | Level and tail-down airplane-datum rows locked to the printout. | case 1 vm 3208 / dm 795 (PHIM 13.921); case 7 vm 3900 / dm −1045 (PHIM −15.000) |
| **G-GF-3** (ρ identity) | GF-4's gate: ρ == −GRA(attitude) per case, every bundled example, exact. | cases 1–12: −GRA₁; 7–9: −GRA₃; 13–33: **−GRA₂** (ga6: −4.057 / −15.000 / **−4.724**) |
| **G-GF-4** (the corrected attitude-1 numbers) | ga6 spot values per §1.3, and the two qualitative signs stated in the test docstring: the side family's body drag is *forward*, and the pre-fix behaviour (+GRA₂) is recorded as what the manual prints. | case 16 vm 2402.3 / dm 1616.4 (PHIM 33.936); case 19 dm −186; case 27 dn −97 |
| **G-GF-5** (downstream closure) | Every assembled ground case closes in six DOF from the corrected reactions; `sbeam-roundtrip` green; the exported ground FORCE cards carry the corrected `vm/dm`. | CI's existing gates, re-run |
| **G-GF-6** (dual-frame deliverable) | Each case's `ConditionResult` carries both frames, the fuselage-axis angle and the application point (patch, strut state, node per leg); frames named per GF-7 from one caption owner with a drift guard; datum factors NR/NV/ND per OQ-1's formula with the corrected lift sign — case 1 locks at **NR 3.269 / NV 3.216 / ND 0.585** (printed 3.287/3.216/0.679 register-recorded per GF-3); wheels-only NR locks as printed (case 16: 1.703). | angle units `deg`, blank SF column, never scaled |

**Closure tiers:** defect item **L** — this note at AGREED first;
`theory_sources.md` grows the p231/p232 citation rows;
`02_approved_corrections.md` entry per GF-3; `PROGRAM_SPEC.md` §LANDLOAD
frame paragraph rewritten; full-format history fragment + `changes/` fragment.
Reporting item **M** — spec section + one-paragraph history fragment; no
schema change in either item (no input moves; `GearReactionCase` is a result
type).

---

## 4. The sweep (practice 4 — generalize on first find)

The class: **a frame rotation whose sign is asserted by construction rather
than adjudicated against an external reference** — and its enabler, a gate
that recovers its reference from the thing it checks.

| Site | Rotation | Verdict |
|---|---|---|
| `landing.py` PHIM/PHIN (attitude 1) | +GRA₂ | **This note (GF-1).** First wrong-way instance. |
| p232's VM/DM cells, used to test p232's PHIM | — | **The enabler class again** (§1.12). `VM=RMP·COS(PHIM)` in the listing: one printed quantity read as two. Withdrawn 2026-08-29; the cells stay, as GF-3″ deviated-from values. |
| LANDLOAD.BAS datum ND lift term (`+LF·SIN(GRA)`) | +GRA | **Second instance, same class** (§1.6). Not yet in sloads — it lands only via GF-6's datum factors, which build with the corrected sign; the p232 cells join GF-3's register. |
| `landing.py` PHIM (level, tail-down) | −GRA₁/−GRA₃ | Correct; becomes locked by G-GF-2. |
| `gear_loads.to_airplane_datum` (G-7a lift axis) | ρ, cases 1–12 only | Correct sign on every case it touches; gains GF-4's gate upstream. |
| `gear_loads.ground_rotation_deg` + the G-6 gate | recovered ρ | **The enabler.** Self-consistent by design; GF-4 adds the absolute reference. The docstring's "sign inconsistency in LANDLOAD.BAS itself" prose is rewritten once adjudicated. |
| Wing CL/CD → body `fz/fx` (flight, α) | balanced α, twice | **Sound** (reviewed 2026-08-28, owner question). The FLTLOADS trim resolves through the balanced α by construction (`VnPoint.lzw` is "lift … normal to the reference", `dx` the drag), and the strips rotate section lift + drag at [airloads.py:396-397](../../sloads/modules/airloads.py) (`lz = lift·cos an + drag·sin an`, `dx = drag·cos an − lift·sin an`); `body_axial_set` cross-checks the two frames through the same α (dL/L ≤ 0.6 %, constant dCD ≈ −0.018 on ga6 — a parasite-term signature, not a frame disagreement). Residual α content is base method, parked with its number: the stall boundary caps n with CL where FAR 23.321's body-normal factor strictly wants CN — cos α = 0.968 at ga6's stall corner (α +14.7°), worth ~1–3 % on where the stall corner sits (V_A), nothing on the design n; the tail balancing load body-normal at the CP is the stated lumped basis. Both inside the 5–10 % band (`theory_sources.md` §Base-method uncertainty). |
| Fin / wing-body side force (sideslip, β) | none needed | **Sound** (same review). Stability axes share the y-axis with body, so the consumed derivatives — the fin's from SELECT, wing-body `Cy_β`/`Cn_β` from DATCOM 5.2.1.1/5.2.3.1 — deliver the side force along body y directly, signs asserted in-band (`CONVENTIONS.md` §lateral frame-map guard). What a sideslip case lacks is any drag term at all, so `D·sin β`/cos β effects are *outside the base method*, not unrotated: a few % of the fin design load at β ≈ 12–15°, below the lateral basis's own DATCOM-level uncertainty. Parked with the number. |
| `export/coordinates.py` (sloads → sbeam) | identity map | Single edit-point by charter (`CONVENTIONS.md` §1), guarded. No action. |
| Lateral frame signs (DATCOM `+Cy`, destabilizing body `Cn_β`) | — | Asserted in-band per `CONVENTIONS.md` §lateral, with the frame-map guard the charter cites. No action. |
| `report/` torsion axis naming | — | Reporting rule (torsion names its axis); not a rotation. No action. |

**No adjacent finding.** The one other self-referential check considered —
`transfer_couple`'s exact guard — verifies a constructed identity that *is*
the property claimed, not a sign adjudication, so it is not in the class.
