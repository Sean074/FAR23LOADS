# M4-1 — Fuselage body loads: moment closure (design note)

Supporting detail for backlog item **M4-1** (`docs/30_future/00_backlog.md`).
The backlog holds the summary, the decided method and the acceptance criteria;
this note holds the diagnosis, the options weighed and the reasoning behind the
choice. Reference 1 Ch 15 (p103) is the source procedure.

## The defect

`body_loads` applies a single vertical wing reaction and closes **ΣFz only**.
The Ch 15 procedure reacts the unbalanced moment at the front/rear spar
attachments (and includes the pitching load factor). Verified symptom: terminal
`Myy ≠ 0` — the exported body set carries a net couple.

**Caveat note shipped 2026-07-23** (the M3 pre-release obligation is
discharged): `body_loads.CLOSURE_CAVEAT` is stamped as `$ CAVEAT:` comments in
`fuselage_loads.bdf`, and the Fuselage Loads page + the Export page's Fuselage
row carry the warning. The note comes out when the moment balance lands.

## Diagnosis (2026-08-03)

The residual is the **wing-attachment reaction moment**, not a trim error.
FLTLOADS already closes ΣM_cg for the whole airplane
(`flight_envelope._balance` solves `LT`), so what is open is the **fuselage-only
free body**: the wing lift resultant offset from `xw`, the wing pitching
moment/torque, the wing inertia and the thrust/drag couple are all collapsed
into one point force at 25 % MAC (`body_loads.body_distribution`, the
`wing_reaction = nz*w_fus - lt` line). One vertical force at one station has no
freedom left to satisfy ΣM.

The error is **not uniformly conservative**: bending aft of the wing is offset
by +M_ub, and forward of it the other way.

## Options weighed

| | Option | Verdict |
|---|---|---|
| A | The literal Ch 15 two-point spar solve | Adopted as the degenerate case of C |
| B | Self-equilibrated distributed correction (linear or second-order, `∫w dx = 0` and `∫w·x dx = M_ub`) smeared over the **whole** body | **Rejected as primary**; retained as a flagged fallback |
| C | The same self-equilibrated shape restricted to the **wing carry-through** | **Adopted** |
| D | The missing pitching load factor | Split out → **M4-21** |
| E | A distributed (Multhopp/Nelson) body aero moment | Split out → **M4-19** |

**Why B is rejected as the primary method.** The couple physically lives at the
wing box, so smearing it over the whole body relieves wing-region bending and
loads the tail cone with a correction that has no physical source. It closes the
beam while making a known unknown invisible.

**Why neither D nor E substitutes for the closure.** For the balanced trim cases
`θ̈ = 0`, so the pitching load factor (D) contributes nothing there and M4-1
stands on its own. E changes `M_ub` but does not react it.

## Decided approach (2026-08-03) — ship C, with A as its degenerate case

- Reactions at the front/rear spar stations (derived from `geometry.surfaces`
  planform + spar fractions), solved 2×2 from ΣFz = 0 and ΣM = 0:

      R_r = (M_ub + R_total*x_f) / (x_r - x_f)
      R_f = R_total - R_r

- Instead of two point loads, distribute `R_total` plus the couple **linearly**
  over `[x_f, x_r]`:

      w(ξ) = 12*M_ub/d^2 * (ξ - 1/2),   ξ = (x - x_f)/d,   d = x_r - x_f

  This is the physically correct support region, degenerates continuously to
  option A as `d → 0`, and avoids A's `±M_ub/d` shear spike over a short
  carry-through — smooth for the beam model, and consistent with how the
  carry-through diffuses load into the frames (Bruhn Ch A5, which p103 itself
  points at). Linear is sufficient: a second-order shape buys nothing over a
  short interval with only two constraints to satisfy.

- **Fallback** (behind an explicit flag) when spar stations are undefined:
  option B, linear over the whole body, `A = 12*M_ub/L^2`. It **SHALL** be
  labelled in output as a *closure artifact*, not as a computed load.

## Acceptance

- Terminal `Myy ≈ 0` and `ΣFz = 0` in the closure suite.
- Front/rear fitting loads emitted (sbeam wants them).
- FAR23 flight oracles unchanged — nothing upstream of `body_loads` changes.
- On close, remove `CLOSURE_CAVEAT` and its three stamp sites: `body_loads.py`,
  the BDF `$ CAVEAT:` comments in `export/sbeam_bridge.py`, and the Fuselage
  Loads + Export Fuselage-row captions.
