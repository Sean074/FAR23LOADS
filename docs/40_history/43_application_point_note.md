# The ground reaction is transferred from the contact patch on every case; the manual applies the landing attitudes at the axle

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: SHIPPED in 0.8.1 (2026-08-29) — the owner agreed AP-1…AP-6 and
G-AP-1…G-AP-5 in session 2026-08-29; implemented and closed the same day.** Issue **#139**. Blocks **#134**
(design note 38 GF-6), which emits the application point as a deliverable and
must not emit a point the deck does not transfer from.

**The claim in one line.** `sloads/gear_loads.py` transfers every one of the 33
LANDLOAD cases from the tyre contact patch; LANDLOAD applies cases 1–12 at the
**axle** and 13–24 at the **ground contact point** — its own printed column — so
the twelve landing cases carry a spurious `r × F` pitching moment into every
balanced ground case, absorbed silently into the solved `q̈`.

**Scope.** The *point* at which a ground reaction is applied, and nothing else.
The reactions themselves are LANDLOAD's own, oracle-locked to Appendix A
p230/p231/p232/p233/p236, and are **not touched by anything proposed here** —
what moves is the lever arm from that point to the gear reference node, and with
it the transfer couple, the pre-closure residual and the solved rigid-body
accelerations of the twelve landing cases. Frames and signs are design note 38's
subject and are settled (AGREED 2026-08-29); this note assumes them.

**Sources reviewed.** Ref 1 Appendix A **p231** and **p233** (the ground-line and
unbalanced-moment tables, whose header column states the point of application per
family: "CENTER OF EACH WHEEL" for cases 1–12, "GROUND CONTACT POINT" for 13–24)
and **p232** ("CL AXLE" for 25/26, 28/29, 31/32; "GROUND" for 27, 30, 33) — the
column the OCR lost, recovered 2026-08-29 at 200 dpi and recorded in design note
38 §1.14; **p234** ("3 WHEEL LEVEL LANDING"), whose construction is axle-to-axle
throughout. Conventions:
[`CONVENTIONS.md`](../10_standard/CONVENTIONS.md) §1 (frames and axes), §3
(LIMIT → ULTIMATE), §7 (single-source owners and their drift guards). Code:
[`sloads/gear_loads.py`](../../sloads/gear_loads.py) (`contact_patch`,
`transfer_couple`, `_leg_load`, `applied_wheels`),
[`sloads/modules/balance.py`](../../sloads/modules/balance.py)
(`build_ground_cases`, `assemble_ground`). Related:
[`38_ground_frame_note.md`](38_ground_frame_note.md) §1.7 (the application-point
chain, audited 2026-08-28 and passed — see §3 below for why),
§1.14 (the printed column and the #134 ruling).

---

## 1. What the code does

`_leg_load` builds `patch = contact_patch(leg, state, GRA)` for every case and
hands it to `transfer_couple(patch, node, force)`; `applied_wheels` does the same
per wheel. There is exactly one point construction and it is used for all 33
cases. The couple is exact for the point it is given (guarded at `rel_tol
1e-12`), so nothing downstream can notice that the point is wrong: the free body
is internally consistent about the wrong lever arm.

## 2. The evidence: an identity that never sees the point

LANDLOAD prints its own **unbalanced pitching moment** `PITCHP` (p233). sloads
assembles the same case as a free body and reports a **pre-closure residual**
`residual_My` before solving for the rigid-body accelerations. The two are the
same quantity, up to the one term sloads deliberately adds and the manual does
not — G-7a's distributed lift, which LANDLOAD nets at the CG (`NLG = N − L`):

    residual_My(at the point) − G-7a lift moment  ==  PITCHP

Nothing in that identity is derived from the application point, so it adjudicates
it. Recomputing each balanced case's residual with the reaction applied at the
patch and at the axle, and differencing against `PITCHP` — max |error| in lb-in,
over every balanced ground case of every bundled fixture that has gear:

| fixture | cases 1–12 at **axle** | 1–12 at patch | 13–24 at axle | 13–24 at **patch** |
|---|---|---|---|---|
| ga6_normal | **4.7** | 20,964 | 28,938 | **7.0** |
| baron_58 | **15.5** | 51,355 | 52,660 | **12.3** |
| cessna_210 | **7.4** | 26,129 | 32,341 | **7.7** |
| atr42_100 | **62.0** | 524,302 | 665,862 | **84.5** |
| dhc8_dash8 | **51.5** | 491,345 | 623,958 | **79.2** |
| concept_regional_jet | **49.7** | 382,437 | 491,568 | **43.9** |

Four orders of magnitude, on every fixture, splitting **exactly** at the printed
column's own boundary — which is the point of the table: the column was recovered
from the scan (§1.14) and this reproduces it from arithmetic that never read it.

The per-case detail on `ga6_normal`, all 24 balanced cases (lb-in):

| case | `PITCHP` | residual at patch | at axle | G-7a lift | error at axle | error at patch |
|---|---|---|---|---|---|---|
| LG-01 | **0.0** | −9,840.6 | 9,786.7 | 9,786.6 | **0.1** | −19,627.2 |
| LG-02 | **0.0** | −28,553.5 | −9,513.3 | −9,511.5 | **−1.8** | −19,042.0 |
| LG-03 | **0.0** | −31,182.9 | −14,860.9 | −14,860.4 | **−0.5** | −16,322.6 |
| LG-04 | −168,056.9 | −179,232.1 | −158,271.3 | 9,786.6 | **−1.1** | −20,961.8 |
| LG-05 | −242,050.8 | −272,526.5 | −251,565.7 | −9,511.5 | **−3.5** | −20,964.2 |
| LG-06 | −232,913.3 | −265,948.7 | −247,778.4 | −14,860.4 | **−4.7** | −18,175.0 |
| LG-07…09 | −9,819.2 … −94,570.0 | — | (no drag: identical) | | **−1.5 … −3.1** | −1.5 … −3.1 |
| LG-10 | −84,028.4 | −84,722.7 | −74,242.4 | 9,786.6 | **−0.5** | −10,480.9 |
| LG-11 | −121,025.4 | −141,019.0 | −130,538.6 | −9,511.5 | **−1.7** | −10,482.1 |
| LG-12 | −116,456.7 | −140,404.5 | −131,319.4 | −14,860.4 | **−2.4** | −9,087.5 |
| LG-13 | **0.0** | −0.7 | 19,352.8 | 0.0 | 19,352.8 | **−0.7** |
| LG-14 | **0.0** | −1.6 | 17,258.6 | 0.0 | 17,258.6 | **−1.6** |
| LG-15 | **0.0** | 0.5 | 13,619.5 | 0.0 | 13,619.5 | **0.5** |
| LG-16 | −192,645.3 | −192,652.3 | −163,711.5 | 0.0 | 28,933.8 | **−7.0** |
| LG-17 | −235,794.3 | −235,797.4 | −206,856.6 | 0.0 | 28,937.6 | **−3.2** |
| LG-18 | −205,288.5 | −205,293.1 | −181,459.5 | 0.0 | 23,829.0 | **−4.6** |
| LG-19…24 | −39,834.3 … −79,354.7 | — | (no drag: identical) | 0.0 | **−1.5 … −3.8** | −1.5 … −3.8 |

Three readings of it:

1. **LG-01/02/03 are the sharpest cells in the suite.** `PITCHP` is *exactly*
   zero — the manual states these cases as pitch-balanced — so the entire
   patch-transferred residual (−9,840.6 / −28,553.5 / −31,182.9 lb-in) is
   spurious, and at the axle the whole of it is the G-7a lift moment sloads
   knowingly adds, to **0.1 / −1.8 / −0.5 lb-in**.
2. **The tail-down and side families cannot discriminate** (LG-07…09, LG-19…24):
   they carry no drag, so patch and axle differ by nothing. They are not evidence
   either way, and are listed so the table is not read as 24 independent
   confirmations. The discriminating cases are the twelve that carry drag.
3. **The residue is uniform and small.** At the correct point the worst identity
   error over all six fixtures is **2.65e-5** of `n·W·MAC` (baron_58 LG-17), and
   every fixture's worst lies between 1e-5 and 2.7e-5 — a rounding floor, not a
   modelling gap.

## 3. Why the manual's split is physically right, and why the 2026-08-28 audit passed

The level-landing drag is a **spin-up** load: the patch friction accelerates the
wheel's rotation, and what the leg carries arrives through the **bearing** — at
the axle. The braked-roll drag is a **braking** load: the brake torque is
internal to the wheel/leg free body, so what the leg carries is the patch force
at the patch. The manual splits the column exactly there. It is a statement about
where the load enters the structure, not a presentation convention, which is why
`r × F` is missing rather than merely relocated.

Design note 38 §1.7 audited this chain end-to-end on 2026-08-28 and recorded "no
defect". The audit was of the right thing and reached the wrong verdict for the
same reason the `BETA` sign survived three sessions: it checked that the chain
was **consistent** — patch built at the case's own attitude, mirrored correctly,
transferred exactly — and consistency is what a wrong point preserves. The
printed column, which is the only independent statement of the point, was
illegible on the day of the audit and was recovered the day after.

## 4. What moves, and what does not

**Unchanged.** Every LANDLOAD reaction (the forces are LANDLOAD's own), so every
Appendix A oracle and every p230–p236 printed-cell lock passes untouched; the
contact patch itself as a *geometric* output; the exactness of the transfer
(`rel_tol 1e-12`); the deck's internal equilibrium, which is self-consistent
about whichever point it is given.

**Moves.** The transfer couple on cases 1–12 and their `MOMENT` cards; the
pre-closure residual and the solved `q̈` of those cases; the frozen Imperial
digest; the worked-example table in
[`balanced_cases.md`](../20_theory/balanced_cases.md) §9.5 (`LG-04`'s
−179,232 lb-in residual becomes −158,271, and its identity error against `PITCHP`
falls from −20,962 to −1.1).

**Not a deviation from a printed oracle.** Unlike design note 38's GF-3″, this
change moves *toward* the manual on every measurable: no register entry in
[`02_approved_corrections.md`](../20_theory/02_approved_corrections.md) is
needed, and a `theory_sources.md` citation for the p231/p233 column is (tier L).

## 5. Decisions of record

| | Decision | Why |
|---|---|---|
| **AP-1** | **The point of application per case is the manual's printed column**: axle for 1–12, ground contact point for 13–24, CL axle for 25/26, 28/29, 31/32, ground for 27, 30, 33. It is a physical point, not a report label. | §2 reproduces the column from an identity that never read it; §3 gives the mechanism. |
| **AP-2** | **One owner** — a single function returning the case's point per leg, consumed by the transfer, the gear free-body report and #134's emitted location. No second construction of a point anywhere, guarded. | Practice 3. A load and its point are one statement (§1.14); two constructions is how they come apart. |
| **AP-3** | **The contact patch stays a reported output on every case**, labelled as the patch — a gear analysis starts from it. What changes is that it is no longer the *transfer* point on cases 1–12. | The gear report's whole purpose (G-12). Removing the patch to fix the transfer would trade one deliverable for another. |
| **AP-4** | **No reaction changes.** The fix touches the lever arm only. | Keeps the oracle surface out of the change: a red oracle after this lands means the fix reached something it must not. |
| **AP-5** | **Ships with the gate that found it** (G-AP-1), not with a tolerance widened to accept the old numbers. | Benchmark-first. The identity is the strongest closure statement the ground family has, and it was available all along. |
| **AP-6** | **Tier L**, defect-first: it lands before #134, whose deliverable is the point. | Rule 6 — a defect with first-order effect on shipped content outranks the fidelity item; #134's row records the dependency. |

## 6. Closure gates

| Gate | Statement | Tolerance |
|---|---|---|
| **G-AP-1** | `residual_My − (G-7a lift moment) == PITCHP` on **every balanced ground case of every bundled fixture**, with each case's reaction applied at AP-1's point. Red today on cases 1–12, green on 13–24. | `1e-4 · n·W·MAC` (observed worst at the correct point: **2.65e-5**, so ~4× margin) |
| **G-AP-2** | The point the owner returns matches the printed column for every case 1–33, asserted against a transcribed table, not against the code that builds it. | exact (family membership) |
| **G-AP-3** | Exactly one construction of an application point in the package; the transfer, the report and #134's emitted location read the same owner. | structural test |
| **G-AP-4** | The transfer stays exact: force + couple at the node has the identical resultant about every reference as the force at the point. | `rel_tol 1e-12` (existing, unchanged) |
| **G-AP-5** | Every Appendix A landing oracle and printed-cell lock passes **unmodified** — no pin moved, no tolerance widened. | ±0.1 % (existing) |

## 7. Sweep (rule 4 — the same defect class elsewhere)

| Site | Point it uses | Status |
|---|---|---|
| `gear_loads._leg_load` → `transfer_couple(patch, …)` | patch, all cases | **the defect** |
| `gear_loads.applied_wheels` → `transfer_couple(patch, …)` | patch, all cases | **same defect, second call site** — one fix if AP-2's owner is threaded, two if not |
| `gear_loads.GearLegLoad.patch` (reported) | patch | correct and stays (AP-3) |
| `balance.assemble_ground` | consumes the wheels' node + couple | follows AP-2 with no change of its own |
| `export.sbeam_bridge` gear cards | consumes the same couple | follows |
| the 23.499 family (25–33) | patch | follows AP-1's column; **not** covered by G-AP-1 (they carry no airplane equilibrium — see OQ-A1) |

## 8. Open questions

**OQ-A1 — cases 25–33 have no gate.** The supplementary-nose family is a local
gear-design case with no airplane in equilibrium, so the identity cannot reach
it. Its point follows AP-1's column by construction and is covered by G-AP-2
alone. Recorded rather than papered over.

**OQ-A2 — does the sbeam roundtrip move? RESOLVED 2026-08-29: no.** The deck's
own equilibrium is self-consistent about whichever point it is given, and the
roundtrip stayed green on different numbers, as predicted. Recorded as confirmed
rather than assumed.

---

## 9. What the implementation found that the note did not predict

**The gate had been making the correction.** The rotational closure gate
(``test_the_ground_closure_reproduces_landloads_unbalanced_moments``) moved the applied load from the tyre to
the axle *inside the test*, on exactly cases 1–12 (and 19–24, where it is a
no-op), with a comment recording that getting it wrong "is not subtle: the level
family misses by 12 % (21,000 lb-in on ga6_normal case 4)". §2's number, measured
and written down on 2026-08-15, read as bookkeeping between two conventions
because the point the code used had nothing independent to be wrong against until
the column was recovered. The correction now lives at the origin and the gate
makes none of its own — and with it gone, and #133's sign fixed, the braked-roll
pitch line drops the 5 % slack it carried: **every family closes on one 1e-4
bound**. A gate that corrects the code before comparing is not testing it.

**A negative control had silently stopped being able to fire.**
``test_the_static_contact_patch_breaks_the_level_landing_gate`` perturbed
``patch``; the moment the patch stopped being the transfer point on cases 1–12,
the control passed while proving nothing. Both controls are now anchored to
``point``, the attribute the transfer reads.

**The transfer rule was implemented twice** — identically, in ``gear_loads`` and
in ``export/coordinates``, each docstring claiming to be note 24 R-11's single
owner. Consolidated onto the calc layer (the export side can import it, not the
reverse), name re-exported so no export call site moved. Found by G-AP-3's guard
tripping over the ambiguity, which is the guard doing its job on its first run.
