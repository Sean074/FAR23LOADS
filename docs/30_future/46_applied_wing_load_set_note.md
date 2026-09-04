# The applied wing load set — six components, and a deck built from them

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-09-03 (owner, in session — `CLAUDE.md` rule 1's
working-alone path).** Milestone: **0.8.2**. Closure tier **L** (part B; part A
is tier M and ships with it). No frozen file is edited: everything here lives in
`sloads/export/` and `sloads/report/`, and `sloads/modules/` is untouched.

The oracle report's Appendix B.1 and the `wing_applied_loads.csv` beside it
(OR-64) are the deliverable a stress analyst builds a model from. They state
three of the six components a body-axis load needs, and the sbeam deck written
from the same wing results states a **torsion that does not survive being
applied at a point**. This note settles both.

Sources reviewed: `sloads/export/sbeam_bridge.py` (`wing_nodal_loads`,
`applied_load_rows`, `span_load_csv`), `sloads/export/equilibrium.py` (module
docstring, lines 32–44), `sloads/export/coordinates.py`
(`bending_moment_vector`), `sloads/modules/net_loads.py` (`to_loads_ref_axis`),
`sloads/models/results.py` (`WingStationLoad`, `ConcentratedLoad`),
`docs/10_standard/CONVENTIONS.md` §Physical senses of positive moments and
§Wing torsion physical sense, `docs/30_future/44_oracle_report_note.md` §12
(OR-59…OR-64), `docs/40_history/19_concentrated_wing_mass_nodal_split_plan.md`.

---

## 1. The evidence

### 1.1 The applied set states half a vector

`AppliedLoad` carried `fz`, `fx` and `myy_free`. A consumer writing `FORCE` and
`MOMENT` cards needs six components, and from three columns cannot tell whether
a missing one is zero or merely unpublished. Two of the three absences are
structural and one is a modelling limit:

- **`Fy`** — the wing chain has no producer for a spanwise strip load
  (`WingStationLoad.f_span` belongs to the fin, whose span is airplane `z`), and
  every delivered wing condition is symmetric or rolling (`PHAA`, `TORS`,
  `ACRL`). No lateral wing condition exists, so the zero is a property of the
  load set and not only of the model.
- **`Mx`, `Mz`** — a strip applies forces and a section moment about the span
  axis and nothing else. The whole of the cumulative `Mxx`/`Mzz` is those forces
  acting through spanwise arms, which a geometric model regenerates. A free
  bending published here would be counted twice.

### 1.2 The deck's torsion does not survive transfer

`wing_nodal_loads` builds its cards by **differencing the cumulative**:
`dmy(i) = Myy(i) − Myy(i+1)`. That difference already contains the sweep and
dihedral transfer of the shear carried at `i+1`, so a solver that applies the
card at the node and generates the transfer itself counts it twice.
`equilibrium.py` documents the consequence rather than fixing it: the wing deck
header claims only `m0.y` (the `MOMENT` cards summed bare), because the
rigid-body resultant `m.y` "would be asserting a quantity nothing in the suite
computes."

Measured, both example airplanes, every case, accumulating today's cards
tip-inboard with the rigid-body transfer a solver applies:

| Airplane | Case | `Sx` | `Sz` | `Mxx` | `Myy` | `Mzz` |
|---|---|---|---|---|---|---|
| ga6_normal | PHAA | 0.000 | 0.000 | 0.000 | **1.515** | 0.000 |
| ga6_normal | TORS | 0.000 | 0.000 | 0.000 | **1.902** | 0.000 |
| ga6_normal | ACRL | 0.000 | 0.000 | 0.000 | **1.195** | 0.000 |
| baron_58 | PHAA | 0.000 | 0.000 | 0.000 | **0.338** | 0.000 |
| baron_58 | TORS | 0.000 | 0.000 | 0.000 | **0.210** | 0.000 |

(relative error against the NETLOADS cumulative table, worst station). Shear and
both bending columns already close exactly; the torsion is wrong by 21 % to
190 %. This is a first-order error in shipped content, which `CLAUDE.md` rule 6
ranks above every fidelity item.

### 1.3 The applied set does survive transfer

The same accumulation over the **applied** set — every strip at its own point
with its own `myy_free`, every concentrated mass at its own point as a pure
force — reproduces all five published columns at **every** station, not only the
root:

| Airplane | worst relative error over all cases, all stations, `Sx`/`Sz`/`Mxx`/`Myy`/`Mzz` |
|---|---|
| ga6_normal | 1.1e-15 |
| baron_58 (four concentrated masses) | 2.5e-15 |

So the fix is not new physics. It is applying the set the suite already computes
instead of a difference of its integral.

### 1.4 One sign asymmetry, already owned

The calc stores spanwise bending as **positive-magnitude integrals**, so against
the right-handed `r × F` a solver recovers, `Mxx → +x` unchanged and
`Mzz → −z` negated (`CONVENTIONS.md` §Wing torsion physical sense; owner
`coordinates.bending_moment_vector`, measured ±1.0000). Publishing a six-column
body-axis set therefore cannot read moments off the record raw. It must route
through that owner, or the sign map acquires a second home.

---

## 2. Decisions

| ID | Decision | Depends on |
|---|---|---|
| **OR-65** | **The applied set states all six body-axis components, and prints its structural zeros.** `AppliedLoad` carries `fx`/`fy`/`fz` and `mxx_free`/`myy_free`/`mzz_free`; `Fy`, `Mx` and `Mz` are zero for every row, named at their single point of construction (`_NO_SPANWISE_STRIP_LOAD`, `_NO_FREE_BENDING`) rather than written `0.0` inline, so the day a lateral wing condition arrives the search finds everything that assumed it away. Both views of B.1 — the report table and `wing_applied_loads.csv` — print the zeros with the reason stated in the note beneath. | OR-64 |
| **OR-66** | **The map from the calc's moment convention to body axes has one owner for the applied set: `applied_body_moments`,** which routes through `coordinates.bending_moment_vector`. Neither consumer carries sign logic. (`CLAUDE.md` rule 3: a cross-cutting convention gets a code owner plus a drift guard, never a prose rule.) | OR-65 |
| **OR-67** | **The exported wing deck is built from the applied set, not from differences of the cumulative.** `wing_nodal_loads` returns each strip's own `fx`/`fz`/`myy_free` at its own node; a concentrated mass, which has no grid, is reduced to the node inboard of it as a force plus the **full** three-component offset couple `r × F` about that node. The `Mx`/`Mz` offset couples that exist today are a partial case of this; the missing member was `My`, which the differencing was silently supplying wrong. | OR-65, §1.2 |
| **OR-68** | **The deck's equilibrium claim strengthens from `m0.y` to `m.y`.** With OR-67 in force the rigid-body resultant of the wing card set *is* the root torsion, so `equilibrium.py`'s wing gate asserts it and its module docstring stops recording the weaker claim as a convention. | OR-67 |
| **OR-69** | **`wing_span_loads.csv` names its two conventions in its headers.** Its `Fx`/`Fz`/`My`/`Mx`/`Mz` are body-axis card values and its `Sx`/`Sz`/`Mxx`/`Myy`/`Mzz` are the beam's positive-magnitude integrals; `Mz` and `Mzz` in one row therefore have opposite senses. Today nothing in the file says so. | OR-66 |
| **OR-70** | **Appendix B.2 is not widened.** It states what the structure carries in the beam's own convention, and adding `Mzz` beside a body-axis `Mz` in B.1 would put the two conventions in one appendix without a reader-visible reason. Filed, not done. | OR-69 |

## 3. Gates

| ID | Gate | Where |
|---|---|---|
| **G-OR-35** | The applied set's six-component resultant reproduces `Sx`, `Sz`, `Mxx`, `Myy` and `−Mzz` at **every** station of every case of both example airplanes, to `closes()` tolerance. | `tests/test_sbeam_bridge.py::test_the_applied_set_reproduces_the_whole_vmt_at_every_station` |
| **G-OR-36** | `Fy`, `Mx` and `Mz` are zero on every applied row, and `My` is not — the zeros are published, and the guard fails if a real component is silently dropped into one of them. | `tests/test_sbeam_bridge.py::test_the_applied_set_states_all_six_components` |
| **G-OR-37** | The exported nodal set reproduces the cumulative table at every station under **rigid-body** transfer, all five columns — the claim OR-68 makes the deck header state. | `tests/test_export_equilibrium.py` |
| **G-OR-38** | B.1's table and `wing_applied_loads.csv` agree row for row on all six components. | `tests/test_oracle_report.py::test_the_appendix_table_and_the_exported_csv_are_one_load_set` |

## 4. What this does not change

The FAR23 core is untouched: `sloads/modules/` is not edited, the Appendix A
oracles are unaffected, and the cumulative columns B.2 prints are the same
numbers they were. What changes is the **applied** set the deck is written from
and the appendix that states it — a view and an export, which is what note 44
OR-6 says this milestone is allowed to move.
