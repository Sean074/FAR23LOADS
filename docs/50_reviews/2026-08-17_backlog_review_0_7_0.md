# Backlog review after the 0.6.0 cut — the 0.7.0 re-cut (2026-08-17)

**Charge (user, 2026-08-17):** post-release housekeeping — review
`docs/30_future/00_backlog.md` and confirm the priority order for the next
development cycle, **0.7.0**. Issue #30 carries the re-cut; this file is its
body of record (`CLAUDE.md` rule 5: findings filed with bodies, same session).

**Yardstick:** `CLAUDE.md` rule 6 — a physics/fidelity item is ranked only if
its stated effect on a delivered load exceeds the base method's own uncertainty
(`theory_sources.md` §Base-method uncertainty: **order 5–10 % on a distributed
load**); below that it is parked with the number. Defects with first-order effect
on shipped content outrank every fidelity item. Reporting and process items are
not fidelity items and are ranked on delivery value.

**Inputs:** the priority table as left by the 0.6.0 cut (band A empty; band B
rows 9–15, band C 16–20), `02_parked.md` "Parked 2026-08-16", the open-defects
index, design notes 19 (L-7, PROPOSED rev. 2) and 21 (power effects, AGREED,
parked), and the shipped state on `main` at `7b56cf8`.

---

## 1. Findings

| # | Finding | Disposition |
|---|---|---|
| BR-1 | The file's prose is a cut behind: "Where things stand (2026-08-16)" describes 0.5.0 + `[Unreleased]`; the table header says "re-cut 2026-08-16"; band A is titled 0.6.0 with a `Cut 0.6.0` marker row; the "schema freeze through 0.6.0" rule has expired; the "notes 09–25 per step" pointer predates the 0.6.0 history roll (19 notes now in `40_history/`). | Rewritten in this re-cut (mechanical). |
| BR-2 | **Row 9, L-7 lateral body aero (#8).** Measured effect (note 19 §7, `concept_regional_jet`): `ψ̈` over-stated **73–84 %** on the rudder-neutral conditions and reversed on `YAW TO SIDESLIP`; `n_y` under-stated **4–12 %**. A missing term of the order of the one kept, and the only band-B item with a **printed oracle** (Digital DATCOM's 11 sample cases, `CYB`/`CNB`, ±0.1 %). Lands on one fixture until `ga6_normal` has a body outline. | Well above the bar → **0.7.0 headline**, tier L. Note 19 → AGREED in chat before code (rule 1); the seven L-7.x decisions and open items 3–4 (`K_Rl` chart edge, `CL_α,B`) settled then. |
| BR-3 | **Row 10, fixture-data pass (#9).** Data, not physics — but it is (i) the fix for the open WTENV-envelope defect (four fixtures' all-up loading 15–22 in aft of their entered limits) and (ii) the vehicle for `ga6_normal`'s body outline that L-7 needs (note 19 §10.2's sequence: pin `vtail_root_waterline_z = 78.5` first, then the outline with its own digest wave, then L-7). | Keep, tier S; **ordered before L-7**. |
| BR-4 | **Row 11, thrust `FORCE` at the engine hub (#10).** Today's wing cases are exactly zero-thrust (note 21 measured); a wing-mounted engine's thrust × its arm to the LRA is a torsion/pitch term the wing box has never seen — 100 % of a missing term, not a refinement. The LRA hub node already exists. | Above the bar → keep, tier S. |
| BR-5 | **Row 12, combined flight + ground station envelope (#11).** Reporting: two-sided max/min per station across both families, each extreme naming its governing case (`CONVENTIONS.md`: envelopes are two-sided). Rule 6 does not apply. | Keep, tier M. |
| BR-6 | **Row 13, gust spanwise-distribution decision (#12).** Reusing the Schrenk shape for the gust case: the gust-vs-manoeuvre spanwise difference is *inside* the Schrenk band by construction (Schrenk is the base method's own approximation of the spanwise shape, ±5–10 %). | **Below the bar** → the decision is recorded (keep Schrenk, with this number) and the row is **merged into the decisions row** (#13); #12 closed as merged. |
| BR-7 | **Row 14, decisions not effort (#13)** — the derived-`ACRL` air-load point and the ATR-42 Mach-capped stall corner, each pinned by test; now also the gust shape (BR-6). | Keep, tier S; three recorded decisions. |
| BR-8 | **Row 15, aileron lift increment (#14).** First-order for `ACRL` torsion at ~70 % span, but only if a consumer sizes to `ACRL`; schema fields shipped v52 and wait for data and a consumer. | Keep in **band B (0.8+)**, unchanged condition. |
| BR-9 | **Band C rows 16–20 (#15–#19)** — export primitives, dead code, function size, the 2026-08-10 minor sweep, the mypy ratchet. Hygiene when the module is next touched. | Unchanged. |
| BR-10 | **Parked items** — power effects' seven-step plan (row 11 is its carve-out), `concept_heavy` gear geometry, CG-dependent MTOW, M4-8 Layer 2, the F25 pack, Multhopp `Cm`, the pitching load factor, per-CG inertia: none has a first-order effect on a delivered load today. | Nothing promoted. |
| BR-11 | **GUI review (user, this session; #29).** The Streamlit UI was frozen outright on 2026-08-16 (CLI is the delivery path); the user wants it reviewed against what 0.6.0 ships — page order vs `workflow.py`, unit toggle/labels, the ground/gear and LRA-model pages, CLI-vs-UI gaps, plan 03 status. | Added to band A as its own row (kind review, tier S for the review); the freeze paragraph amended: frozen **pending #29**, whose findings decide what re-opens. |
| BR-12 | **Note 12 (CONM2 plan) is the one part-shipped note left in `30_future/`.** Its status says "C6's solver-side gate is not shipped" — but it is: `tests/test_sbeam_roundtrip.py` M-a…M-c ("plan 12 C6") accelerates the `CONM2` set in sbeam and reproduces sloads' inertia. Stale status, no decision needed. | Status flipped to shipped (C1–C7); rolls to `40_history/` at the 0.7.0 cut. |
| BR-13 | **Schema rule for 0.7.0.** The freeze through 0.6.0 held (one hop, v53). L-7 needs one additive hop (the fuselage/fin lateral inputs, off-by-default per L-7.3). | Freeze lifted **for exactly that hop**; anything else in 0.7.0 rides it or waits. |

## 2. The 0.7.0 order (band A) and the cut signal

| Pri | Item | Issue | Tier / effort |
|---|---|---|---|
| 1 | Fixture-data pass — empennage polylines, WTENV envelopes reconciled, `ga6_normal` body outline (+ `vtail_root_waterline_z` pinned first) | #9 | S / S |
| 2 | **L-7 lateral body aero `Cy_β`/`Cn_β`** — the 0.7.0 headline; note 19 agreed first | #8 | L / M |
| 3 | Thrust `FORCE` at the engine hub | #10 | S / S |
| 4 | Combined flight + ground station envelope | #11 | M / M |
| 5 | Decisions, not effort: `ACRL` point, ATR-42 Mach corner, gust shape = Schrenk (#12 merged) | #13 | S / S |
| 6 | GUI review — the Streamlit UI against the 0.6.0 deliverables | #29 | S (review) / M |

**Cut 0.7.0 when band A is empty** — six rows, one tier L, one M, four S: inside
`RELEASE_PROCESS.md` §2's "~2–3 weeks or ~5 steps". Band B = #14 (aileron
increment, 0.8+); band C = #15–#19 unchanged.

## 3. What this review did not do

No code, no test, no physics was re-derived; every effect number above is
quoted from the design note or the changelog entry that measured it. The
Streamlit UI was not reviewed here — that is #29's job. Parked bodies were not
re-read beyond their titles and stated effects (rule 6 needs only the number).

## 4. Closure

Tier S: this file; the table and prose re-cut in `00_backlog.md`; note 12's
status; `00_INDEX.md` row; `changes/backlog-recut-0-7-0.changed.md`; issue
labels/milestone updated for the moved rows (`band:A` on #8/#9/#10/#11/#13/#29,
`band:B` on #14; milestone `0.7.0`); #12 closed as merged into #13; #30 closed
by the landing commit.
