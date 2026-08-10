# Design note — concentrated wing masses smeared to the nearest node

**Status:** **shipped 2026-08-09.** D-1 decided by the user in favour of
**Option B (offset couple)**, and the `Mzz` sweep accepted with it. What was
built matches §3 Option B and §4 exactly; §6 records the two things measurement
changed during implementation.
**Item:** `00_backlog.md` Pri 1, *"Concentrated wing masses are smeared to the
nearest node in the exported bending"* (filed 2026-08-08 by the step-1
equilibrium sweep). **Tier L** — physics change to a deliverable, so this note
comes first (CLAUDE.md required practice 1).
**Conventions:** [`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md)
— wing axes (`y` spanwise, `Fz` normal, `Mxx` bending about the streamwise
axis), the LIMIT→ULTIMATE boundary (the fix sits *inside* the export, so the
per-case factor stays uniform and every existing force closure is untouched).
**Theory:** WINGINER.BAS 1180–1270 / 1570–1610 (concentrated masses); Ref 1
Ch 14 (net wing loads). No printed oracle covers a concentrated wing mass —
`ga6_normal` (Appendix A) and `cessna_210` carry none — so this closes against a
**stated closure gate**, per CLAUDE.md required practice 2.

---

## 1. Mechanism, restated exactly

`wing_inertia` integrates tip→root with the recursion

    mxx[i] = mxx[i+1] + sz[i+1]*dy                                   (1)

and `airloads` (`airloads.py:392`) uses the identical form. A concentrated mass
is then added to every station **strictly inboard** of it at its true station:

    sz[i]  += w              }  for ye[i] < y_c                      (2)
    mxx[i] += w*(y_c - ye[i]) }

The export (`sbeam_bridge.wing_nodal_loads`) recovers nodal loads by
differencing the cumulative column, `dFz[i] = sz[i] - sz[i+1]`.

**The key identity.** For a set of loads lumped *at the nodes*, (1) holds
identically. So define the per-station **moment defect**

    δ[k] = mxx[k] - mxx[k+1] - sz[k+1]*(y[k+1] - y[k])               (3)

δ[k] ≡ 0 wherever the table came from (1), and for a mass at `y_c` bracketed by
`y[j] < y_c ≤ y[j+1]`, substituting (2) into (3) gives

    δ[j] = w*(y_c - y[j]),   δ[k≠j] = 0                              (4)

i.e. **δ is exactly the first moment the differencing loses**, it is recoverable
from the published table alone, and it needs no new input, no schema change and
no access to `wing_mass.concentrated`. Summing (3) over all k gives
`mxx[0] - Σ dFz[i]*(y[i]-y[0]) = Σ δ[k]`, which is the filed error.

The published cumulative table is **correct** — `mxx[0]` carries the true lever
arm. Only the discretisation into nodes is wrong, which is why the fix is
export-side and no calc math moves.

## 2. Measurement (this session, all six fixtures, both channels)

δ computed per station from each fixture's `net_loads.wing_net`:

| fixture | masses (lb @ y) | bracket node j | δ[j] (lb-in) | root `Mxx` err | root `Mzz` err |
|---|---|---|---|---|---|
| `atr42_100` | 1190 @ 161, 1900 @ 175 | 6 (y=157.3, dy=24.2) | −9.508e4 | **+1.913 %** | **+1.136 %** |
| `dhc8_dash8` | 1400 @ 168, 2000 @ 180 | 6 (y=165.75, dy=25.5) | −7.912e4 | **+1.109 %** | **+0.673 %** |
| `concept_heavy` | 600 @ 120 | 7 (y=112.875, dy=15.05) | −1.710e4 | **+0.435 %** | **+0.324 %** |
| `ga6_normal`, `cessna_210`, `concept_regional_jet` | none | — | ≤ 8.1e-10 | 0.000 % | 0.000 % |

Three things this establishes that the filed item did not:

1. **The Mxx figures reproduce the filed numbers exactly** (1.91 / 1.11 / 0.44),
   confirming (4) is the same defect and not a second one.
2. **δ is nonzero at exactly one node per fixture** and is machine-zero
   (≤ 8.1e-10 lb-in against root moments of order 1e7) at every other node and on
   all three masses-free fixtures. The correction is therefore **provably a
   no-op** on the Appendix-A fixture — not merely "measured as small".
3. **`Mzz` (in-plane/drag bending) carries the same defect, unfiled and
   ungated** — `mzz_d` uses the same recursion and takes the same `w*(y_c-ye[i])`
   step (`wing_inertia.py:180`). The existing pin checks `Mxx` only. Per CLAUDE.md
   rule 4 (generalize on first find) the fix sweeps both channels.

**Scope limit — the assembled deck is not affected.** `balance._wing_air_set`
builds from `air_load_distribution`'s **per-strip** `fx`/`fz` and places the
inertia items at their own stations; it never differences a cumulative column
(no `wing_nodal_loads` call in `sloads/modules/`). So this is confined to the
per-component wing deck — an analysis view — and the primary full-span
deliverable is already free of it.

## 3. The decision (D-1): how the lost first moment is restored

Both options preserve `Σ F` exactly, so every existing force closure stays green.

**Option A — force split between the bracketing nodes** (as filed). Transfer
`t = δ[j]/dy` from node `j` to node `j+1`. Force and total first moment are both
preserved, so root bending closes; it is the standard tributary/consistent
lumping and is equivalent to splitting each mass by lever arm.
*Cost, measured:* the model's shear at node `j+1` gains `t`, which the truth does
not carry — `atr42_100` **3929 lb = 22.2 % of the local `Sz`** (16.0 % of root
shear), `dhc8_dash8` 3103 lb = 13.4 % local, `concept_heavy` 1136 lb = 6.5 %
local. It trades a ~2 % bending error across the whole inboard wing for a ~20 %
shear error at one node — right beside the engine rib, where a consumer sizes
shear webs. It also **cannot** fix a mass outboard of the last station (no node
to transfer to); no shipped fixture has one, but nothing forbids it.

**Option B — rigid-offset couple at the bracketing node (recommended).** Leave
`dFz` alone and emit the offset moment `Mx = δ[j]` as an additional component on
that node's `MOMENT` card. A force `w` at `y_c` is *statically equivalent* to
force `w` at node `j` plus a couple `w*(y_c - y[j])` — equation (4) is that
couple. This is exact, not an approximation:

* shear reproduces `sz[k]` at **every** node (nothing moves), and
* bending reproduces `mxx[k]` at **every** node — the couple adds `δ[j]` to the
  internal moment at every station inboard of `j` and nothing outboard, which is
  precisely the defect.

It is the standard way a mass offset from a beam node is transferred, it handles
the outboard-of-tip case naturally, and `MOMENT` cards already exist on this deck
(torsion). `equilibrium.resultant` already accumulates applied `MOMENT` cards
(`m0x/m0y/m0z`) separately from the `FORCE` lever-arm terms (`mx/my/mz`), so the
gate becomes `mx + m0x == want` with no harness change.
*Cost:* a consumer who takes the `FORCE` cards and discards the `MOMENT` set gets
the old (high) bending. That is stated in the deck `$` header, and the header's
existing claim *"MOMENT(My) set sums to root torsion"* must widen to name the
`Mx` content.

**Recommendation: Option B** — it is exact in both channels where A is exact in
one and materially worse in the other, and the filed wording ("lever-arm split")
predates the shear-cost measurement above.

## 4. Acceptance (the closure gate, written with the feature)

1. **`test_wing_deck_bending_closure` loses its exception.** The negative branch
   and `_has_concentrated_wing_mass` are **deleted**; all six fixtures assert
   exact closure, both unit systems — `Mxx` from `FORCE` lever arms **+ applied
   `MOMENT` `Mx`** under B.
2. **New: the `Mzz` closure gate**, all six fixtures, both systems — the channel
   nothing checked.
3. **Station-by-station, not just the root:** assert the exported set reproduces
   `sz[k]` and `mxx[k]` at **every** station (this is what B buys and what A
   cannot pass on shear).
4. **A drift guard on δ:** assert δ is machine-zero at every node on the
   masses-free fixtures — the property that makes the change a no-op there.
5. **No-op proof:** `ga6_normal`, `cessna_210`, `concept_regional_jet` decks stay
   **byte-identical** (`tests/fixtures_imperial/digests.json` unchanged for them);
   Appendix A oracles untouched (no calc file is modified).
6. **Digest regeneration** for the three affected fixtures' wing decks, with the
   before/after root `Mxx`/`Mzz` recorded in the history entry.
7. `ruff` clean, full suite green, sbeam round-trip job green.

## 6. What measurement changed during implementation

Two things the note above did not anticipate, both found by running the gates
rather than by reasoning:

1. **δ needs a *relative* zero threshold, not an absolute one.** δ is a
   difference of large nearly-cancelling numbers, so on a mass-free wing it
   leaves cancellation residue up to **8e-10 lb-in** — which straddles the
   bridge's existing `_TOL = 1e-9` negligible-load constant. Emitting it
   unconditionally replaced the clean `0.000000E+00` moment columns of *every*
   mass-free deck with float noise (and, in SI, noise multiplied by the moment
   factor), breaking acceptance 5. Fixed with `_DEFECT_REL_TOL = 1e-9` applied
   to the column's own scale: residue sits at ~1e-16 of the column, a real mass
   at ~1e-2, so the separation is ~14 orders. An absolute threshold would also
   have been a different test on a 200-inch wing than on a 500-inch one, and a
   different test again in N·mm.
2. **IEEE negative zero.** `bending_moment_vector` negates `mzz`, turning a zero
   into `-0.0`, which formats as `-0.000000E+00` and rewrote the `MOMENT` card of
   every mass-free wing — a byte change with no number behind it. Normalised in
   the one function that owns the sign.

Both were caught by acceptance 5 (`ga6_normal` byte-identity), which is why that
gate was written as byte-identity rather than "numerically unchanged".

**Two scope facts confirmed by measurement**, both recorded rather than acted on:

* `concept_heavy` has **no wing deck in the Imperial baseline channel at all**
  (`imperial_baseline.artifacts` does not build the envelope, so `build_net_loads`
  fails there and only `body_*` artifacts are digested). Its wing deck *is*
  covered by the equilibrium sweep and by the new couple guard. Pre-existing
  digest-coverage gap, unrelated to this step — filed, not fixed here.
* The round-trip solver matrix was `ga6_normal` + `concept_regional_jet`, both
  mass-free, so **no solver-side test exercised a concentrated-mass wing**.
  Adding `atr42_100` to the wing leg (`WING_MATRIX`) is what proves sbeam
  *honours* an `Mx` component rather than silently dropping it — W-d compares
  element 1's end-B bending against the NETLOADS root `Mxx` and read 1.91 % high
  until the couples existed.

**Mutation-checked:** with the couples suppressed (`_DEFECT_REL_TOL` raised),
15 card-text assertions and **2 real-solver assertions** fail, and every
mass-free fixture stays green — so the gates bite, and they bite only where the
physics is.

## 5. Closure trail (Tier L)

`CHANGELOG.md` `[Unreleased]`; backlog Pri 1 removed and the table renumbered;
**full step format** in `docs/40_history/00_completed_development.md`;
`PROGRAM_SPEC.md` sbeam-bridge section (the `MOMENT` set's `Mx` content under B);
`docs/20_theory/00_theory_sources.md` citation for (1)–(4);
`sbeam_bridge` module docstring "Nodal loads from the cumulative table" rewritten
(it currently documents the defect as a guarantee), and the `tail_span` writer's
note 1 cross-reference updated.
