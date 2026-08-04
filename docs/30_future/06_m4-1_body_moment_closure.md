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

      R_r = (M_ub + R_total*(L - x_f)) / (x_r - x_f)
      R_f = R_total - R_r

  where `L` is the aft-most station (the reference the terminal moment is taken
  at) — see the **Step 0 verification** below; an earlier draft of this note
  printed `R_total*x_f`, which does not close under this module's integrator.

- Instead of two point loads, distribute `R_total` plus the couple **linearly**
  over `[x_f, x_r]`:

      w(ξ) = 12*M_ub/d^2 * (ξ - 1/2),   ξ = (x - x_f)/d,   d = x_r - x_f

  This is the physically correct support region, degenerates continuously to
  option A as `d → 0`, and avoids A's `±M_ub/d` shear spike over a short
  carry-through — smooth for the beam model, and consistent with how the
  carry-through diffuses load into the frames. Linear is sufficient: a
  second-order shape buys nothing over a short interval with only two
  constraints to satisfy.

  **Provenance of the distributed shape.** This is our engineering choice, *not*
  something p103 sanctions: the manual prescribes two point reactions (option A),
  and its Bruhn Ch A5 pointer is about *beaming the inertia loads to the adjacent
  two frames*, not about diffusing the wing reaction across the carry-through.
  The choice is defensible on the support-region and smoothness grounds above and
  reduces continuously to the manual's own procedure, so it is a refinement
  rather than a deviation — but the calc docstring shall state it as ours.

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

## Implementation decisions (locked 2026-08-03)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Spar stations from chord fractions on `SurfaceInput`** — `front_spar_pct`/`rear_spar_pct`, resolved in `derived_geometry` as `x = x_LE(root) + pct*c_root` from the wing surface polylines at `y = 0`. | Geometry stays single-sourced (the M2-6 rule); no second editable copy of wing geometry on the body slice. |
| 2 | **Defaults 0.15 / 0.65 `c_root`, flagged as *assumed*.** | Every existing project (incl. `ga6_normal` and the fixtures) closes on the primary path, so the caveat comes off for existing work. The provenance flag (`assumed` vs `entered`) is stated in the BDF header, the GUI and the report, so an assumed spar location is never mistaken for input. |
| 3 | **`R_f`/`R_r` are reported, not applied** — carried on `BodyLoadResult`, shown in the GUI, exported as their own ULTIMATE fitting-loads CSV. | The distributed carry-through set already carries `R_total` *and* the couple; adding the fittings to the FORCE set would double-count and break the `ΣFz = 0` property of the deliverable. |
| 4 | **Station-derived stable GIDs** — mass stations keep `1001 + i` in nose→tail order; carry-through correction nodes take a disjoint `1500+` block. | The correction inserts sub-nodes inside `[x_f, x_r]`; positional numbering would silently renumber every station aft of the wing whenever the correction grid changes. |

Non-blocking defaults adopted with them: `M_ub` is the residual of the **existing**
free body (no wing pitching moment or thrust/drag couple pulled in — M4-19/M4-21
own those); the closure tolerance is relative to peak `|Myy|`, not a bare
`abs_tol`; the fallback keeps the current caveat text renamed
`CLOSURE_ARTIFACT_CAVEAT`; the spar fractions are edited on the Geometry page
beside `ref_axis_pct`.

## Step 0 verification (2026-08-03) — done

Ref 1 Ch 15 p103 (`reference/code.txt:8366`) prescribes a **two-pass** procedure,
which the implementation follows literally:

> "Multiply the component weights by the linear and pitching load factors.
> Calculate the shear by progressively adding the inertia loads from the nose to
> the tail and include the air load on the tail. Calculate the moment from the
> nose to the tail by accumulating the area under the shear curve. **The moment at
> the aft end is the unbalanced moment.** The unbalanced moment is reacted by the
> wing at the front and rear spar attachments. Calculate the wing reactions.
> Recalculate the loads, shear and moments along the fuselage including the wing
> reactions."

So `M_ub` is the terminal `Myy` of the **wing-reaction-free** set (inertia + tail
air load) — which the module's existing integrator already produces. ("linear
**and pitching** load factors" is the M4-21 half; `θ̈ = 0` on these balanced trim
cases, so it does not affect this closure.)

**Sign convention.** `body_distribution` accumulates `Myy += Sz*(x - x_prev)`
nose→tail, so the terminal moment is `M = Σ fz_i*(L - x_i)` with `L` the aft-most
station. Imposing `ΣFz = 0` and `M = 0` gives the `(L - x_f)` form above.
Confirmed numerically on all four GA6 critical fuselage conditions (scratch check,
spar defaults 0.15/0.65 `c_root` → `x_f = 60.150`, `x_r = 110.650`, `d = 50.500`):

| Condition | `M_ub` (lb-in) | `R_total` (lb) | `R_f` (lb) | `R_r` (lb) | terminal `Myy` (this form) | terminal `Myy` (shipped today) |
|---|---:|---:|---:|---:|---:|---:|
| MAX DOWN LOAD ON WING | −1 315 552 | 9 355 | −1 805 | 11 160 | 5.7e−11 | 368 969 |
| AFT DOWN BENDING | −1 486 338 | 10 916 | −3 072 | 13 988 | 3.7e−10 | 479 328 |
| AFT UP BENDING | 695 783 | −4 268 | −1 068 | −3 201 | −5.2e−11 | −72 845 |
| GREATEST NZ | −1 798 759 | 13 021 | −3 153 | 16 174 | 1.4e−10 | 545 914 |

Two findings carried into the plan: the reaction formula needed the `(L - x_f)`
correction (recorded above), and `R_f` is **negative** on every GA6 condition — a
front-spar pull-off, not a benign split of `R_total`. That is a real design number
for the fittings and vindicates reporting them (decision 3). The last column is
the defect this item closes.

## Step plan

**0 — Reference check.** ✅ Done (above). Cite p103 in the calc docstring and the
closure test.

**1 — Inputs.** `front_spar_pct`/`rear_spar_pct` on `SurfaceInput`; resolver in
`derived_geometry.py` returning `(x_f, x_r, provenance)` or `None`;
`SCHEMA_VERSION` 34 → 35; `io.py` round-trip.

**2 — Calc (`modules/body_loads.py`).** Build the point set **without** the wing
point reaction; `R_total = nz*W_fus − LT`, `M_ub` = ΣM about `x_f`. Solve
`R_r = (M_ub + R_total*x_f)/d`, `R_f = R_total − R_r`. Apply over `[x_f, x_r]` as
uniform `R_total/d` plus `w(ξ) = 12*M_ub/d² * (ξ − ½)`, discretized onto sub-nodes
merged into the sorted point list; re-integrate nose→tail unchanged. Degenerate
`d → 0` (below tolerance) → the literal two-point A solve. No spar stations →
option B over the whole body with `closure_artifact = True`.

**3 — Export (`export/sbeam_bridge.py`).** Stable GID scheme; `$ CAVEAT:` only on
the artifact path; a terminal-`Myy` line beside the ΣFz line; fitting-loads CSV.

**4 — GUI.** `fuselage_loads.py`: drop the `st.warning`, add a terminal-`Myy`
closure metric, show resolved `x_f`/`x_r` + `R_f`/`R_r` (marked LIMIT) and the
fraction provenance; artifact warning only on the fallback path.
`export_report.py`: same conditional treatment for the Fuselage row.

**5 — Tests.** Terminal `Myy ≈ 0` + `ΣFz = 0` for every fuselage condition;
`d → 0` continuity to the two-point solve; fallback flags and still closes;
`R_f + R_r == R_total` and the moment about `x_f` recovers `M_ub`; invert
`test_body_bdf_carries_closure_caveat` (no caveat on the spar path, caveat on the
fallback); io round-trip; FAR23 flight oracles unchanged.

**6 — Docs (same session).** `PROGRAM_SPEC.md` §`body_loads`,
`20_theory/00_theory_sources.md` oracle-status cell, backlog M4-1 →
`40_history/00_completed_development.md`, `CHANGELOG.md` `[Unreleased]`, this note
folded into the history entry, new terms into `cspell.json`.
