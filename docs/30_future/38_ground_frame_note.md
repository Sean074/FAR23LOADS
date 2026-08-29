# The ground-roll attitude's airplane-datum resolution rotates the wrong way

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: AGREED — GF-1 and GF-2′ approved by the owner 2026-08-29, GF-3″ with
them.** The sign question is closed by the manual's own construction figures
(§1.15): p234 states the rule (`BETA = GAMMA − GRD ANGLE`, arms axle-to-axle
normal to the resultant) and p235 prints braked-roll arms of 77.052 / 17.760 /
94.811 where the p230 table prints 69.886 / 23.260 / 93.147 — reproduced exactly
by flipping `beta[1]`. **GF-1 and GF-2′ are one defect at one line**
(`landing.py:229`), positive ground angle is **nose up**, and GF-3″ records that
the replication follows the manual's figure over the manual's program rather
than deviating from a printed oracle.

*History of the adjudication, kept because most of it was wrong at least once:*
GF-3′ was withdrawn 2026-08-28 for understating the deviation surface (§1.11).
A 2026-08-29 reading of the newly legible p232 force cells as *refuting* GF-1 was
withdrawn the same day (§1.12) — the manual derives those cells from the angle
they were taken to test. §1.13 then closed §1.11's oracle-coverage hole (p231,
p232 and p233 fully transcribed and locked) and found a **third instance** of the
§4 class in p233's datum-moment transform. §1.14 recorded the owner's ruling on
the #134 deliverable. §1.15 closed the question and **withdrew §1.10's `DP`
argument**, whose conclusion held for a reason it did not give. GF-2 (PHIM-only
fix site) remains refuted (§1.9), which §1.15 explains: it left the other use
site reading the same wrong `beta`.

Deliverables: **(a)** the defect — every attitude-1 ground case resolves and is
levered off the wrong-signed `beta`, and the exported ground FORCE cards and gear
reference-point loads carry it; **(b)** the dual-frame reporting the original
ships and the replication does not, scope ruled at §1.14 (#134, GF-6/GF-7).

> **BOTH DELIVERED 2026-08-29.** (a) landed as #133 (GF-1/GF-2′/GF-3″/GF-4/GF-5),
> and (b) as #134 (GF-6/GF-7) after a second ordering condition found while
> opening it — the deck transferred cases 1–12 from the tyre where the manual
> applies them at the axle ([note 39](39_application_point_note.md), #139), which
> landed the same day. The whole note is discharged; §5.4's one open disposition
> is answered in the same change (the p233 datum-moment transform is registered
> with the item that built it).

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
unlocked p232 for this note; **p234** ("3 WHEEL LEVEL LANDING") and **p235** ("BRAKED ROLL") — the two
construction figures that state the lever-arm rule and settle the sign (§1.15);
**p233** ("LIMIT UNBALANCED MOMENTS", both frames, §1.13); Appendix C **LANDLOAD.BAS listing** (scan
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

> **All five CLOSED 2026-08-29 (#134).** `run()` emits the fuselage-axis angle
> per case (1), the airplane-datum table — both GUIs and the CSV (2) — the
> NR/NV/ND datum load factors and the p233 datum moments (3), and, for each of
> **three wheels on every case**, the body-frame force and the point it acts at
> (5). Frames are named on the value itself and captioned from one owner (4), so
> the split that made this list possible cannot silently come back: the primed
> set stays in the text report and the CSV carries the body frame alone,
> drift-guarded both ways.

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

> **VERDICT OVERTURNED 2026-08-29 — see [design note 39](39_application_point_note.md) (#139).** The chain below is consistent, and that is all this audit established: it checked that each patch was built at its own attitude, mirrored correctly and transferred exactly, which is precisely what a *wrong point* preserves. The printed column — the only independent statement of the point — was illegible on the day of this audit and was recovered the next (§1.14). It says the **axle** for cases 1–12, where the transfer uses the patch, and an identity that never reads the column reproduces it on every fixture. The paragraph is kept as written; only its conclusion is withdrawn.

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

**`DP` decides it on its own.** ~~DP is the wheelbase along the ground line — the
distance between the two contact points.~~ **WITHDRAWN 2026-08-29 (§1.15):** p234
shows DP is measured *axle to axle*, normal to the *resultant*, and the actual
contact-patch separation is 94.622, not 94.811. The conclusion was right for a
reason this paragraph did not give — p235 prints 94.811. The original argument
follows, kept as the record of how it was reached — and note that its arithmetic
was wrong as well as its premise: the patch separation is 94.622.

> DP is the distance between the two contact points. That is the distance
> between two points and admits no sign convention:
>
>     |patch_main − patch_nose| = 94.811   (ga6, ground roll)
>
> against a printed **93.147**. The corrected projection returns 94.811 exactly.

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

### 1.13 The pages are legible, the surface is locked, and p233 holds a second rotation (2026-08-29)

Three things came out of rendering the rest of Appendix A's LANDLOAD output.

**1. The open finding of §1.11 is closed.** p231, p232 and p233 read cleanly at
200 dpi, and every printed cell of all three now locks against the port at the
page's own print resolution — `test_landload_p231_ground_line_table`,
`test_landload_p232_airplane_datum_table`,
`test_landload_p233_unbalanced_moments_table`. All 33 cases, both frames, the
NVP/NDP/NS factors and the unbalanced moments. The braked-roll and
supplementary-nose families no longer rest on internal identities, and the
40 %-move-leaves-the-suite-green hole is gone. The pages were never illegible;
they were un-**OCR**-able, and the project recorded the two as the same thing
from 2026-08-15 until yesterday.

**2. GF-3″'s deviated-from set is now transcribed and executable**, which is what
the gate was blocked on. It is also larger than §1.11 measured, because §1.11
measured what the correction moves in *sloads* and the register needs what it
deviates from in the *manual*:

| page | cells a GF-1 / GF-2′ correction departs from |
|---|---|
| p230 | the ground-roll AP/BP/DP row (GF-2′ only) — §1.10's values |
| p231 | cases 13–15 and 25–33: VNP/DNP/SNP/RESULT/VMP/DMP/RESM and NVP/NDP (GF-2′ only) |
| p232 | **cases 13–33, essentially the whole table** — VN/DN/VM/DM (GF-1); the same rows again under GF-2′ |
| p233 | cases 16–24 PITCHP, and 19–24 ROLLP/YAWP (GF-2′ only) |

The p231/p233 rows are the expensive ones: they match the port today at ±0.1 %
or better, so GF-2′ trades a set of exact printed agreements for a physical
argument. GF-1 alone does not touch p231 or p233 at all — it moves only p232 —
which is worth stating plainly, because **GF-1 and GF-2′ no longer cost the same
thing.** §1.9 bound them together on the closure-residual evidence; the register
now has to price them separately.

**3. p233 prints a second ground-to-datum rotation, and it is independent of
PHIM.** The page carries both frames of the unbalanced moments with its
equations:

```basic
PMOM = PMOMP
RMOM = RMOMP*COS(GA) + YMOMP*SIN(GA)
YMOM = YMOMP*COS(GA) - RMOMP*SIN(GA)
```

Checked against the printed cells, this is a clean rotation (magnitude preserved
to the last digit) of **+GRA on every attitude** — +4.0566° on the level cases
10–12 against GRA₁ = 4.057, +4.724° on the ground-roll cases 19–24 against
GRA₂ = 4.7241. A moment vector and a force vector rotate identically under the
same change of frame (`ROLLP = −M_x`, `YAWP = −M_z` from the printed
`RMOMP = VMP·TREAD/2`, `YMOMP = −DMP·TREAD/2`; the common sign cancels, and the
result is unchanged whether x is taken forward or aft). So p233 demands
`PHIM = θ + GRA` **on every attitude** — agreeing with the ground-roll PHIM row
and contradicting the level and tail-down rows, which is the opposite pairing
from §1.2.

**This does not overturn GF-1; it enlarges the defect.** §1.2's adjudication did
not rest on the count of rows on each side, and the tail-down row settles the
convention on its own without appeal to consistency at all: there
`θ = 0`, so PHIM *is* the ground normal expressed in body axes, and it prints
**−15.000 = −GRA₃**. An airplane 15° nose-up sees the ground normal tilted 15°
toward the nose. That is not a convention, and it fixes the sense as
`PHIM = θ − GRA`. The reading is therefore: the level and tail-down **force**
rows are right, the ground-roll force rows are wrong (GF-1, unchanged), and the
**moment** transform is wrong on *all* attitudes.

That makes the datum-moment transform a **third instance of the §4 class**,
after PHIM/PHIN and the ND lift term of §1.6 — and, like the ND term, it is not
in sloads: `run()` emits only the primed moments, so it can only arrive with
GF-6. It must arrive with the corrected sign.

**Transcribed for GF-6/#134** — the p232 datum load factors, which the note had
only partially (case 1 and case 16, both of which this reading confirms):

| cases | NR | NV | ND |
|---|---|---|---|
| 1–6 | 3.287 | 3.216 | 0.679 |
| 7–9 | 3.167 | 3.059 | −0.820 |
| 10–12 | 1.975 | 1.941 | 0.363 |
| 13 / 14 / 15 | 1.485 / 1.452 / 1.442 | 1.271 / 1.277 / 1.280 | 0.768 / 0.691 / 0.665 |
| 16–18 | 1.703 | 1.238 | 1.170 |
| 19–24 | 1.330 | 1.325 | 0.110 |

**Still AWAITING RE-AGREEMENT.** Nothing here unblocks the code: GF-3″ still has
to be drafted and agreed, and it now has a bigger surface to state and a new
question to answer — whether GF-1 and GF-2′ are approved together or separately,
given that only GF-2′ costs the p231/p233 agreements.

---

### 1.14 The application point is a printed column, and the deliverable's shape is ruled (2026-08-29)

§1.5 item 5 recorded that no application point is identified in the landing
output and treated it as something GF-6 would have to decide. It does not: **the
manual prints it**, in a column the OCR lost along with the rest of these pages.

| cases | printed point of load | page |
|---|---|---|
| 1–12 | CENTER OF EACH WHEEL — the **axle** | p231, p233 |
| 13–24 | GROUND CONTACT POINT | p231, p233 |
| 25 / 26, 28 / 29, 31 / 32 | CL AXLE | p232 |
| 27, 30, 33 | GROUND | p232 |

The split is not arbitrary: the families that carry a drag or side reaction
resolved against the ground surface are applied at the patch, and the families
whose reaction is stated about the wheel are applied at the axle. It is also
**not** a free choice for the replication — a load and its point are one
statement, and moving the point silently changes every moment downstream.

**Owner's ruling on the deliverable (in session, 2026-08-29), folded into GF-6
and G-GF-6:**

1. **`Fx, Fy, Fz` and the location `x, y, z`** — signed body-frame components
   with the point they act at, not a magnitude plus an angle.
2. **All three legs on every case** — nose, left main, right main — with an
   unloaded gear recorded at zero rather than omitted.
3. **The ground-line set stays in the text report and leaves the CSV.** The CSV
   is the body-frame deliverable; the primed set remains available as the
   analysis view the manual prints beside it.
4. **The item still waits on the GF-1 ruling.** GF-6's ordering condition is
   kept deliberately, not by default. *(GF-1 landed 2026-08-29; the item then
   acquired a second condition — [note 39](39_application_point_note.md) /
   #139 — because the point ruled here is not the point the deck transfers
   from on cases 1–12.)*

There is a second reason for (4) beyond not promoting wrong-sign forces: the
contact-patch coordinates are themselves built from `GRA`
(`x + r·sin GRA`, `z − r·cos GRA`, `gear_loads`), so **the application point
moves with the sign ruling too** — by the radius offset, on exactly the
cases 13–24 and 27/30/33 that are applied at the patch. Shipping the point
before the sign is settled would ship a point that then moves.

---

### 1.15 The manual's own figures settle it: p234 states the rule, p235 breaks the table (2026-08-29)

Appendix A carries two construction figures for LANDLOAD's lever arms, on the
pages immediately after the result tables. Both were rendered at 200 dpi and read
cleanly. **They are the independent reference this note has been missing since
§1.8**, and between them they close the sign question, dissolve §1.10's argument
while confirming its conclusion, and merge GF-1 and GF-2′ into one defect at one
line.

#### p234 — "3 WHEEL LEVEL LANDING": the rule, stated

The figure draws WL, FS, NORMAL TO GRD and the RESULTANT through CG 6
(X = 76.12, Z = 93) with the compressed axles (nose R 5.7 at 1.9/46.9, main R 8.0
at 96.3/55.9), and states in the drawing:

```
K = .324
GAMMA = ARCTAN K = 17.978
BETA = GAMMA - GRD ANGLE = 17.978 - 4.057 = 13.921
GRD ANGLE = +4.057
AP = 60.948    BP = 28.513    DP = 89.462
```

Three things are settled by the drawing alone. **The arms are measured between
the axles**, not the contact patches — the dimension lines run from the wheel
centres. **They are normal to the RESULTANT**, not to the ground line. And
**`BETA` is the resultant-to-FS angle**, obtained by subtracting the ground angle
from `GAMMA` — which is exactly what `_Geometry.beta`'s field comment already
claims it is (`landing.py:169`), and exactly what the code computes for this
attitude and no other.

#### p235 — "BRAKED ROLL": the same construction, and a different answer from the table

The same CG 6, the static axles (nose 2.4/49.5, main 96.7/59.6), the 4.724 deg
ground angle, the 4522 lb vertical and the `.8RVM` drag — and the arms:

| | p230 table (program output) | **p235 figure** |
|---|---|---|
| AP | 69.886 | **77.052** |
| BP | 23.260 | **17.760** |
| DP | 93.147 | **94.811** |
| CP | 42.981 | 42.981 — agrees |

The figure's three values are precisely the arms §1.10 derived as corrected, and
they are reproduced **exactly** by flipping one sign:

| arm | `beta[1] = +GRA₂` (as coded) | `beta[1] = −GRA₂` | p235 figure |
|---|---|---|---|
| AP | 69.887 | **77.052** | 77.052 |
| BP | 23.261 | **17.759** | 17.760 |
| DP | 93.148 | **94.811** | 94.811 |

`CP` is untouched by the flip and agrees with the figure at 42.981, confirming
§1.10's prediction that it enters through `cos` and is even. The figure's
**4522 lb** is a second, incidental confirmation of #135: `1.33 × 3400`, the
braked-roll weight at `WCG × WR` for a max-landing loading.

#### The sign convention, settled against both figures at once

Both readings of "positive GRD ANGLE" were tested against both figures:

| reading | level (p234: 60.948 / 28.513 / 89.462) | braked roll (p235: 77.052 / 17.760 / 94.811) |
|---|---|---|
| **positive = nose up** (`+4.057 / +4.724 / +15`) | BETA 13.920 → 60.950 / 28.512 / 89.463 ✓ | BETA −4.724 → 77.052 / 17.759 / 94.811 ✓ |
| positive = nose down (`−4.057 / −4.724 / −15`) | BETA 22.033 → 51.505 / 32.624 / 84.129 ✗ | BETA +4.724 → 69.887 / 23.261 / 93.148 ✗ |

**Positive ground angle is nose up.** The nose-down reading reproduces neither
figure; it matches only the p230 row under dispute, and destroys the level
attitude, which never was. It is also forced geometrically: the level and
ground-roll angles come from the same axle geometry rising aft (compressed
contacts 41.2 → 47.9, static 43.8 → 51.6), so all three attitudes share one
sense and cannot be signed against each other. The tail-down entry is the plain
statement of it — a tail-down landing is unambiguously nose-up, and it is entered
`+15`.

A drawing of the ground sloping away toward the nose, with WL held horizontal, is
the same geometry seen in body axes; it is not a nose-down attitude.

#### One rule, one wrong line

```
BETA = GAMMA − GROUND ANGLE,  with GAMMA = 0 where the drag rides the .8·CP term
     → (13.920, −4.724, −15.000)
```

`landing.py:229` computes `beta = (gamma - gra1, gra2, gra3)` → `(13.920, +4.724,
+15.000)`. Attitudes 2 and 3 both hold the wrong sign; only attitude 3 negates it
back, and it does so **at both of its use sites**: `bp[2]` is written longhand as
`a·cos(GRA₃) − c·sin(GRA₃)`, which is `fn_bp` with `−GRA₃`, and `PHIM(7–9) =
−BETA(3)`. Attitude 2 negates it at neither, so both its arms and its
`PHIM`/`PHIN` carry it.

| attitude | `beta` holds | arms use | PHIM uses | net |
|---|---|---|---|---|
| 1 level | `GAMMA − GRA₁` ✓ | `+beta[0]` | `+beta[0]` | correct |
| 3 tail down | `+GRA₃` ✗ | longhand **−GRA₃** | **−**`beta[2]` | correct — compensated twice |
| 2 ground roll | `+GRA₂` ✗ | `+beta[1]` | `+beta[1]` | **wrong at both sites** |

A sign negated at one use site and not the other is the signature of an error
fixed where it was noticed rather than where it originated. **This is the whole
defect**, and `gear_loads`' own instrumentation had already isolated it: ρ
recovered per case reads −4.0570 (level), **−15.0003 (tail down)** and +4.7253 /
+4.7239 (ground roll) — tail down negative despite `beta[2]` holding `+15`,
ground roll the only positive. That was read as a quirk of LANDLOAD to be routed
around ("never has to adjudicate a sign inconsistency that is in LANDLOAD.BAS
itself", `gear_loads.py:214`) rather than as a defect with a location.

#### Consequences for the decisions

1. **GF-1 and GF-2′ are one defect, not two claims to price separately.**
   §5's separation is void as a *choice*; it survives only as a description of
   which pages each symptom touches. Fix site: `beta = (gamma - gra1, -gra2,
   gra3)` plus `ap[1]`'s call site, which passes the literal `gra2` rather than
   `beta[1]`. `cp[1]` stays on `+gra2` — it builds the contact-patch line, and
   the figure confirms CP unchanged.
2. **§1.9 is explained rather than overturned.** Correcting one use site left the
   other reading the same wrong `beta`, which is exactly the incoherence measured
   at 0.106·W·MAC.
3. **§1.10's `DP` argument is WITHDRAWN, though its conclusion was right.** `DP`
   is axle-to-axle and normal to the resultant (p234), not the ground-line
   distance between contact points; the actual patch separation is **94.622**,
   not 94.811. The number 94.811 is correct because p235 prints it, not because
   of the wheelbase reasoning. §1.11's axle-vs-patch self-consistency argument
   falls with it, for the same reason.
4. **GF-3″ changes character.** This is no longer a deviation from a printed
   oracle. The manual contradicts *itself* — its construction figure against its
   program's table — and the register entry records that the replication follows
   the figure over the program. That is a materially weaker thing to approve, and
   §5 should be re-cut against it.
5. **§1.13's p233 finding is explained.** The datum-moment transform rotates
   `+GRA` on every attitude because it reads the same `beta`.

#### What the figures do not settle

There is **no tail-down figure** — printed p236 is the LGFACTOR output, so the
set is p234 and p235 only. Attitude 3 therefore has no figure corroboration; it
is simply already correct in the code, by compensation. And nothing here touches
the deviation surface itself: the p230 arm row and the p231/p232/p233 cells that
derive from it still move, in the amounts §5 tabulates.

---

## 2. Decisions (GF-1 … GF-8)

| # | Decision | Rationale |
|---|---|---|
| **GF-1** | **The attitude-1 airplane-datum resolution is adjudicated a defect in LANDLOAD.BAS**: the physical PHIM/PHIN subtract the ground angle in every attitude. Corrected: PHIM(13–18) = atan(0.8) − GRA₂; PHIM(19–24) = −GRA₂; PHIN(13–15) = −GRA₂; PHIN(25/28/31) = atan(0.8) − GRA₂, (26/29/32) = atan(−0.4) − GRA₂, (27/30/33) = −GRA₂. | §1.2. The manual's own level and tail-down rows prove the convention; the ground-roll rows violate it. |
| **GF-2′** *(proposed 2026-08-28, replacing the refuted GF-2)* | **Fix site is five tables, one sign: `AP(2,·)`, `BP(2,·)`, `DP(2,·)` (`_geometry`, ground-roll attitude only) and `PHIM(13–24)` / `PHIN(13–15, 25–33)`.** `CP(2,·)` is untouched (enters through `cos`); the level and tail-down attitudes are untouched; `beta` itself, `gamma` and the `FNAP`/`FNBP`/`FNDP` definitions are untouched — only the rotation handed to them on attitude 1. ~~Fix site is the PHIM/PHIN tables only~~ (REFUTED §1.9: correcting the resultant direction while leaving the arms produces an incoherent module, measured at 0.106·W·MAC) ([landing.py:471–490](../../sloads/modules/landing.py)). `_geometry`, `beta`, and the p230-locked AP/BP/DP/CP lever arms are untouched; every primed (ground-line) quantity is untouched. | The lever arms and the primed set are oracle-locked and *correct* — the ground-line equilibrium closes (NVP identities). Only the frame resolution is wrong. Smallest true fix site. |
| **GF-3′** *(WITHDRAWN 2026-08-28 — understated the deviation surface; see §1.11 and GF-3″)* | The register entry additionally records the **p230 ground-roll lever-arm row** — AP 78.836/69.886/66.501 → 86.002/77.052/73.502; BP 14.311/23.260/26.646 → 8.810/17.759/21.310; DP 93.147 → 94.811 (§1.10) — with DP's independent check as the headline evidence: the wheelbase along the ground line is the distance between two contact points, 94.811, and the printout states 93.147. `test_landload_lever_arms_oracle` is **re-pinned to the corrected arms**, not deleted, citing this entry. | The p230 table is a printed oracle; departing from it needs the register, and DP's discrepancy is the cleanest statement of the defect in the whole note — it needs no frame argument at all. |
| **GF-3″** *(drafted 2026-08-29, replacing the withdrawn GF-3′ — **awaiting the owner's AGREED**)* | **The register entry states the whole surface, and prices GF-1 and GF-2′ separately.** §5 carries the draft entry with every deviated-from value transcribed from the rendered page and its corrected expectation beside it. The two corrections are no longer one purchase: **GF-1 alone departs from p232 only** (cases 13–33) and leaves p230, p231, p233 and p236 untouched; **GF-2′ additionally departs from p230's ground-roll arm row, p231 cases 13–15 and 25–33, and p233 cases 16–24** — further cells that reproduce today to the printed digit. ~~**The ruling GF-3″ needs is which of the two claims is approved on its own evidence**~~ **SUPERSEDED by §1.15 (2026-08-29):** the two are one defect at one line (`beta[1]`), so there is nothing to price apart — and the entry is no longer a deviation from a printed oracle at all, but a record that the replication follows the manual's **p235 construction figure** over its own program's p230 table. §5's tables remain valid as the deviation *surface*; §5's framing of the choice does not. | §1.13. GF-3′ was withdrawn for understating the surface; the surface is now measured rather than estimated, and measuring it separated two corrections §1.9 had bound together. A register entry that cannot say what each half costs cannot be approved on evidence. |
| **GF-3** | **This is an approved oracle deviation**: an entry in [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md) recording the printed p232 values deviated from (43.387 / −17.079 / +4.724 and the vm/dm rows of §1.3, **plus the ND/NR cells of the lift-carrying cases per §1.6** — case 1: ND 0.679 → 0.585, NR 3.287 → 3.269) and the corrected expectations, owner-approved in the PR. The p232 **level and tail-down force** rows, which are correct, become new oracle locks (±0.1 %); the wheels-only **NR** values lock as printed (frame-invariant, §1.6). The entry **supersedes the register's "Considered and declined" decision of 2026-08-15** on the same question (§1.2): the declined entry is converted in place (declined → approved deviation, with the new evidence and a pointer to this note), and its pin test `test_the_ground_roll_attitude_is_resolved_against_the_other_sign` is flipped to pin ρ = −GRA on every attitude, never deleted. | The register is the process for departing from a printed oracle (`CLAUDE.md` §Math fidelity). Locking the rows that are right while deviating from the rows that are wrong is exactly what the register exists to state — and the declined entry's own text names this note's evidence as its reopening condition. |
| **GF-4** | **ρ gets an absolute gate**: `ground_rotation_deg(case) == −GRA(attitude of case)` for every case, against `ground_angles` directly, exact (1e-9), all bundled examples. The gate's docstring states its assumption: the nose-up sense of GRA (§1.2's proof) was derived on **tricycle geometry**, the only arrangement the suite models — a tail-wheel configuration would re-open the sign derivation, not inherit it. | §1.4 — the existing G-6 gate is self-consistent and structurally cannot catch a sign error. This converts the documented anomaly in `gear_loads.py:224–229` from prose into an assertion (practice 3), and that prose is rewritten to describe history, not behaviour. |
| **GF-5** | **Downstream re-verification rides the existing CI gates**: the assembled ground cases re-close in six DOF from the corrected reactions; the sbeam round-trip stays green; the gear reference-point loads **and the patch-to-trunnion transfer couples** move with `vm/dm` (§1.6 — the couple is derived from the force, so it co-corrects with no additional code). No consumer needs code changes. | The consumers were built to trust `vm/dm`; correcting the producer corrects them all. G-7a is untouched (§1.4); the application-point chain itself is verified sound (§1.7). |
| **GF-6** *(scope set by the owner 2026-08-29 — §1.14; **DELIVERED 2026-08-29, #134**)* | **The delivered landing load is a body-frame force with a stated point of application, for every gear on every case.** Per case, per leg — **nose, left main, right main, all three always present, zeros included** — `run()` emits the signed body components **`Fx, Fy, Fz`** and the **location `x, y, z`** of that force, plus the strut state and reference node. The point is the manual's own printed column, not an inference: **axle centre** for cases 1–12, **ground contact point** for 13–24, **CL axle** for 25/26, 28/29, 31/32 and **ground contact point** for 27, 30, 33 (p231/p232/p233, §1.14). Also emitted: the fuselage-axis angle (units `deg`, never SF-scaled) and the NR/NV/ND datum factors per OQ-1's resolved formula **with the lift term's corrected sign** (§1.6). **The ground-line (primed) set stays in the text/report output and is excluded from the CSV** — the CSV is the body-frame deliverable. Lands **with or after GF-1**, whose condition is **discharged** (GF-1/GF-2′ landed 2026-08-29). A **second ordering condition took its place the same session**: opening this item found that the deck transfers cases 1–12 from the contact patch where the manual applies them at the axle ([note 39](39_application_point_note.md), #139), so the point this item is to emit is not yet the point the deck uses. GF-6 lands after #139, on the corrected numbers **and** the corrected point (the contact-patch coordinates are built from `GRA` and moved with the sign fix too). **Both conditions discharged and the item built the same day.** One thing it added that this row did not ask for: the primed unbalanced moments could not leave the CSV without the *datum* ones taking their place, or the deliverable would have carried no moment at all — so #134 also builds p233's second table, which is §5.4's open disposition answered by the item that needed it. | §1.5, §1.14. The replication's deliverable is thinner than the 1990 printout it replicates; M4-17e closed that gap for the primed set and stopped there. A stress model consumes a force and a point; a magnitude with an unnamed frame is not a load. Emitting all three legs on every case — rather than only the loaded ones — is what makes a case's free body readable without reconstructing which gear the family implies. |
| **GF-7** *(**DELIVERED 2026-08-29, #134**)* | **Every reactions table names its frame, in both GUIs**, using the manual's own words — "with respect to ground line" / "with respect to airplane datum" — one caption owner in `app_shell` with a drift guard, not two prose copies. | §1.5 item 4; practice 3. The Oracle currently shows unlabeled ground-line numbers while the deck consumes body — a reader moving between them has no stated bridge. Built as `sloads/frames.py`: the words, the frame vocabulary, the report/deliver rule and the rotation between the frames, all in one module both GUIs and the render boundary read. |
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
| **G-GF-6** (body-frame deliverable with a stated point) — **MET 2026-08-29**, `tests/test_landing_deliverable.py` | Every case carries **three legs** (nose, left main, right main) each with signed `Fx, Fy, Fz` **and** a location `x, y, z`; a case that leaves a gear unloaded emits it at zero rather than omitting it, and a **guard asserts the three-leg invariant on every case of every bundled example**. The point matches the printed column per family (axle 1–12, ground contact 13–24, CL axle 25/26/28/29/31/32, ground 27/30/33). **CSV carries the body frame only; the ground-line set appears in the text report and not in the CSV** — drift-guarded both ways so neither can leak into the other. Frames named per GF-7 from one caption owner with a drift guard; datum factors NR/NV/ND per OQ-1's formula with the corrected lift sign — case 1 locks at **NR 3.269 / NV 3.216 / ND 0.585** (printed 3.287/3.216/0.679 register-recorded per GF-3); wheels-only NR locks as printed (case 16: 1.703). | per-leg force sums reproduce the locked p232 magnitudes; angle units `deg`, blank SF column, never scaled |

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
| `landing.py` `beta[1]` (`:229`) | `+GRA₂` where the rule gives `−GRA₂` | **The origin (§1.15).** Every other row below that touches attitude 2 is this one line read twice. Attitude 3 holds the same wrong sign but negates it at both use sites, which is why only attitude 2 shows. |
| `landing.py` PHIM/PHIN (attitude 1) | +GRA₂ | **This note (GF-1).** First wrong-way instance *observed*; §1.15 locates it upstream in `beta[1]`. |
| p232's VM/DM cells, used to test p232's PHIM | — | **The enabler class again** (§1.12). `VM=RMP·COS(PHIM)` in the listing: one printed quantity read as two. Withdrawn 2026-08-29; the cells stay, as GF-3″ deviated-from values. |
| LANDLOAD.BAS datum moment transform (`RMOM`/`YMOM`) | +GRA, **all attitudes** | **Third instance, same class** (§1.13). Printed on p233 with its equations; not in sloads (only the primed moments are emitted), so like the ND lift term it arrives only via GF-6 and must arrive corrected. |
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

---

## 5. The GF-3″ register entry (draft, 2026-08-29 — not yet agreed)

> **Partly superseded by §1.15 (2026-08-29).** The value tables below stand — they are the deviation
> surface, unchanged. What does not stand is §5.1/§5.2's framing of GF-1 and GF-2′ as two separately
> priceable claims: p235's figure shows them to be one defect at one line, and recasts the entry from
> *deviation from a printed oracle* to *the manual's figure against the manual's program*. Re-cut §5
> against §1.15 before taking it to the register.

Ready to move into [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md)
**if and when** the owner rules on §2's GF-3″. Every "as printed" figure below is
transcribed from the rendered page and is locked in `tests/test_landing.py`
(`test_landload_p231/p232/p233_*`); every "corrected" figure is computed from the
manual's own printed formulas with the single substitution each correction makes.
Nothing here is estimated, and nothing is computed from the pre-fix code — which
is the defect that withdrew GF-3′.

### 5.1 What GF-1 alone costs: p232, and nothing else

The resultants are untouched, so this is a pure re-resolution of already-locked
magnitudes. p230, p231, p233 and p236 stay green unmodified.

**Read this as a deviation surface, not as a shippable option.** §1.9 already
refuted the PHIM-only fix site (the old GF-2): correcting the resolution while
leaving the arms leaves the module incoherent against its own unbalanced
moments, measured at 0.106·W·MAC. So "GF-1 alone" is what the *register* would
have to state if only the resolution were adjudicated — it is not a build. What
§1.13 separates is the **cost** of the two claims, so that each is approved on
its own evidence; what §1.9 binds is the **implementation**, and that binding
stands.

| cases | quantity | as printed → GF-1 corrected |
|---|---|---|
| 13 / 14 / 15 | VM | 1307 → 1492, 1153 → 1316, 908 → 1036 (**+14.2 %**) |
| 13 / 14 / 15 | DM | 1235 → 1004, 1090 → 886, 858 → 697 (**−18.7 %**) |
| 13 / 14 / 15 | VN, DN | VN unchanged (1708 / 2037 / 1767); DN **flips sign** — 141 → −141, 168 → −168, 146 → −146 |
| 16 / 17 | VM, DM | 2104 → 2402; 1989 → 1616 |
| 18 | VM, DM | 1733 → 1978; 1638 → 1331 |
| 19–24 | VM | unchanged (2253, 2253, 1856) — `cos` is even |
| 19–24 | DM | **flips sign** — 186 → −186 (19–22), 153 → −153 (23–24) |
| 25 / 28 / 31 (aft) | VN, DN | 1094 → 1249, 1778 → 2030, 1677 → 1915 (+14.2 %); 1034 → 840, 1680 → 1366, 1585 → 1288 (−18.7 %) |
| 26 / 29 / 32 (fwd) | VN, DN | 1210 → 1133, 1967 → 1841, 1855 → 1737 (**−6.4 %**); −372 → −565, −604 → −919, −570 → −867 (**+52 %**) |
| 27 / 30 / 33 (side) | VN, DN | VN unchanged; DN **flips sign** — 97 → −97, 157 → −157, 148 → −148 |

**The sign flips are the physical claim, not an artefact.** In the side families
the ground-line load is purely normal, so the entire body-frame drag component
*is* the rotation: printed aft, corrected forward, which is what nose-up geometry
demands (G-GF-4). A reviewer who reads only one line of this entry should be shown
that one.

Also in scope per §1.6/GF-3: the p232 **ND** cells of the lift-carrying cases
(case 1: ND 0.679 → 0.585, NR 3.287 → 3.269), which arrive with #134.

### 5.2 What GF-2′ additionally costs: p230, p231 and p233

| page | cases | quantity | as printed → GF-2′ corrected |
|---|---|---|---|
| p230 | ground roll | AP | 78.836 / 69.886 / 66.501 → 86.002 / 77.052 / 73.502 |
| p230 | ground roll | BP | 14.311 / 23.260 / 26.646 → 8.810 / 17.759 / 21.310 (**−38 %** on the first) |
| p230 | ground roll | DP | 93.147 → **94.811** |
| p231 | 13 / 14 / 15 | VMP | 1404 → 1512, 1239 → 1348, 975 → 1064 (+7.7 / +8.8 / +9.1 %) |
| p231 | 13 / 14 / 15 | DMP | 1123 → 1210, 991 → 1079, 780 → 851 |
| p231 | 13 / 14 / 15 | RESM | 1798 → 1936, 1587 → 1727, 1249 → 1363 |
| p231 | 13 / 14 / 15 | VNP | 1714 → 1498, 2044 → 1825, 1773 → 1596 (−12.6 / −10.7 / −10.0 %) |
| p231 | 25–27 | VNP, DNP | 1175 → 711 (**−39.5 %**); 940 → 569, −470 → −284 |
| p231 | 28–30 | VNP, DNP | 1910 → 1433 (−25.0 %); 1528 → 1146, −764 → −573 |
| p231 | 31–33 | VNP, DNP | 1802 → 1416 (−21.4 %); 1442 → 1133, −721 → −566 |
| p233 | 16 / 17 / 18 | PITCHP | −217530 → −192650, −260675 → −235794, −225167 → −205292 |
| p233 | 19–20 / 21–22 / 23–24 | PITCHP | −64716 → −39839, −105186 → −80306, −99232 → −79358 (−38 / −24 / −20 %) |
| p233 | 19–20 / 21–22 / 23–24 | YAWP | ∓40386 → ∓24862, ∓65640 → ∓50116, ∓61925 → ∓49524 |

The NVP/NDP ground-line factors of cases 13–15 and the p231 SNP column move with
these; they derive from the same reactions.

**The evidence for GF-2′ is unchanged and remains strong** — `DP` is the distance
between two contact points and admits no sign convention (94.811 against a printed
93.147, §1.10); a ground-parallel arm cannot depend on whether it is measured to
the axle or to the patch, and only the corrected rotation makes those two agree
(§1.11); and the correction drives case 13's pre-closure residual pitching moment
from −757.1 to −0.7 lb-in (§1.11). **What §1.13 changed is only that the cost is
now precise rather than indicative.**

### 5.3 Disposition of the existing register entry and the pinned tests

Unchanged from GF-3: the "Considered and declined" decision of **2026-08-15**
converts in place — its own text names legible printed output as its reopening
condition, and §1.13 supplies exactly that — and
`test_the_ground_roll_attitude_is_resolved_against_the_other_sign` is **flipped**
to pin ρ = −GRA on every attitude, never deleted. The three page locks added
2026-08-29 get the same treatment: any row a ruling deviates from **moves to the
corrected value with this entry cited beside it**. No lock is removed, and the
number of locked cells does not fall.

### 5.4 The one thing this entry cannot decide

Whether the **p233 datum-moment transform** (§1.13, the third instance of the §4
class) is registered here or with #134. It is not in sloads and cannot be until
GF-6 emits datum moments. Recommendation: name it here as known and adjudicated,
and let #134 carry its own deviated-from cells when it builds them — the same
treatment §1.6's ND lift term already has.

> **ANSWERED 2026-08-29 as recommended.** #134 emits the datum moments — it had
> to: with the primed set leaving the CSV, a deliverable with no moment at all
> would have been the alternative — and both the transform and the ND lift term
> are registered together in `02_approved_corrections.md` under #134, as one
> entry, because they are one error in two places.
