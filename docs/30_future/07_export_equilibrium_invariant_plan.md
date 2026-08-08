# Design note — Global equilibrium invariant on exported decks

**Backlog item:** `[E] Global equilibrium invariant on exported decks` (raised
2026-08-05, process review R9). **Status:** design agreed 2026-08-08, not yet
implemented. **Closure tier:** M (behaviour change to an existing capability —
three deck families gain `GRID` cards), documented to L depth because the
acceptance is a *stated physics-closure gate* (`CLAUDE.md` required practice 2).

Conventions cited throughout: [`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md)
(axes, sign, units channels, ULT/SF contract, case identity). Deck contract:
[`../10_standard/PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md) sbeam-bridge
section. Unit-set authority: `sloads/units.py` (`Channel.SOLVER`, decision D-19).

---

## 1. What the backlog asked for, and why it cannot be built as written

R9's wording was:

> for each exported case, Σ`FORCE` = n·W (within tolerance) and Σ moments ≈ 0
> about the deck reference, in deck units.

Three facts about the current export make that statement unrealizable as
literally phrased. They were established by reading the code and running the
fixtures on 2026-08-08:

1. **The body deck already closes to zero, not to n·W.** `build_body_loads`
   assembles a *free-free* fuselage beam (Ref 1 Ch 15 p103): fuselage inertia +
   the balancing tail air load + the wing carry-through reaction. On
   `examples/ga6_normal.project.json` all four fuselage cases give
   `ΣFz = 0.000` and terminal `Myy ≈ 3e-10`. Its equilibrium statement is
   `Σ = 0`; asserting `Σ = n·W` against it would be asserting the wrong thing.

2. **Decks are per-component and their cases do not pair.** Wing cases are
   `W-01 PHAA`, `W-05 ACRL`, `W-06 TORS`; fuselage cases are `F-01 … F-04
   GREATEST NZ`; tails are `HT-xx` / `VT-xx`. Per `sloads/case_ids.py` these are
   *different physical conditions* selected by different SELECT routines, banded
   into disjoint ID ranges on purpose. There is no case id under which a wing,
   body and tail card block coexist, so "each exported case's wing + body + tail
   cards" has no referent. `BodyLoadResult` does not even carry `nz`.

3. **The wing deck is a single half-span, root-clamped cantilever, and its root
   shear is not n·W/2.** ga6 PHAA: root `Sz` = 5836.9 lb limit against
   n·W/2 = 6460 lb — the difference is fuselage-carried lift plus wing inertia
   relief. Doubling is additionally wrong for the antisymmetric cases (`ACRL`,
   `TORS`).

**Decision (2026-08-08, user):** the invariant asserts **per-deck resultant
re-derivation**, not an assembled n·W closure. For every exported deck, re-derive
Σ`FORCE` and Σ`MOMENT` from the emitted card text and assert they equal *that
component's own stated expected resultant*, in deck units, after the
limit→ultimate factor and the unit scale. The assembled-airframe n·W closure is
recorded below as a follow-on item (§9), explicitly out of scope here.

This is the honest form of the invariant: it verifies the claim each deck makes
about itself in its own `$` header, at the boundary where the numbers leave the
tool.

## 2. What already exists (so the plan does not re-ship it)

Four force-resultant checks are already in CI, already parsed from card text via
`tests/helpers.py:parse_cards`:

| Check | Test | Fixture |
|---|---|---|
| Wing Σ`FORCE`.Fz = SF·root `Sz` | `test_sbeam_bridge.py::test_force_moment_cards_round_trip`; `test_concept_closure.py::test_full_airframe_exports_cleanly` | ga6, concept |
| Tail Σ`FORCE`.Fz = SF·(LT25+LT50) | `test_concept_closure.py::test_full_airframe_exports_cleanly` | concept |
| Control Σ`FORCE`.Fz = SF·`load_lb` | `test_concept_closure.py::test_full_airframe_exports_cleanly` | concept |
| Body Σ`FORCE`.Fz ≈ 0 | `test_concept_closure.py::test_body_nodal_cards_sum_to_zero` | concept |

**The genuine gaps this step closes:**

- **G1 — No moment closure is verified from any deck.** The wing's in-memory
  bending check (`test_nodal_loads_sum_to_root_totals`) sums `n.fz * (n.y - y0)`
  from `NodalLoad` objects, never from the deck's own `GRID` coordinates — which
  are what a solver actually integrates. The body deck's `$` header asserts
  `Terminal Myy … (moment equilibrium)` and **nothing verifies that claim** at
  the boundary.
- **G2 — Every closure test runs default Imperial.** `system=` is never varied.
  A unit-set bug where `moment.factor ≠ force.factor × length.factor` — the exact
  D-19 failure mode `coordinates._checked` exists to prevent — passes the whole
  suite today, because force-only sums are insensitive to it.
- **G3 — Body / tail / control decks emit no `GRID` cards at all.** They
  reference GIDs that exist in no file, so they cannot be moment-checked from
  their own text, and a consumer cannot place the loads without a second file.
- **G4 — ga6 (the FAR23 oracle fixture) has no body/tail/control deck coverage.**
  `test_concept_closure.py` runs the concept fixture only.
- **G5 — No single owner.** Each test hand-rolls its own summation
  (`sum(sc * v[2] for _, sc, v in forces[sid])`, four times). `CLAUDE.md`
  required practice 3 wants one code owner plus a drift guard.

## 3. Agreed design decisions

Recorded here as the decisions of record for this step (user, 2026-08-08).

| # | Decision | Rationale |
|---|---|---|
| E-1 | **Per-deck resultant re-derivation**, not assembled n·W | §1 — the assembled form has no case pairing and no `nz` on the body result |
| E-2 | **Per-component moment reference**: wing → its clamped root node; body → aft-most station; tail → its first (leading-edge) chord station | Each deck then asserts exactly the claim its own `$` header makes; the CG-referred wing moment is a quantity nothing in the suite computes |
| E-3 | **Check reads the emitted deck text**, via `parse_cards` | Only this version catches the `%.6E` 6-sig-fig truncation, the `_TOL = 1e-9` card suppression, and a card routed to the wrong SID — the failure modes that live at the export boundary rather than in the physics |
| E-4 | **Test-only for now** — no runtime validator, no GUI/CLI surface | Keeps the export path's user-visible behaviour unchanged; a validator is a later, separate decision |
| E-5 | **Body / tail decks gain `GRID` cards** so the moment check is purely deck-derived | Answers G3 at its root; those decks currently name GIDs that exist nowhere, which is a defect in its own right |

### 3.1 Open sub-decision — control-surface `GRID`s (flagged, needs a call)

E-5 was answered as "body/tail/control". **Control surfaces cannot take it as
stated:** `ControlSurfaceStation.x` is a *fraction of chord* (0 = LE, 1 = TE),
dimensionless — `control_surface_csv` labels the column `X (chord frac)` and
calls it "the one column here that is identical in both unit systems".
`ControlSurfaceLoadResult` carries no chord length, so there is no way to turn
`x = 0.35` into a station in inches or millimetres. Emitting `GRID … 3.5E-01`
into a millimetre deck would be a silently wrong coordinate.

**Recommendation:** control-surface decks keep force-resultant checking only and
emit **no** `GRID` cards, with an explicit `$` line stating that the profile is
in chord fractions and the deck therefore carries no geometry. Revisit if and
when the control-surface results gain a chord length (natural pairing: **L-1**,
the assembled stick model). The alternative — adding a chord to
`ControlSurfaceLoadResult` — is a schema change and belongs in its own step.

*This plan is written assuming the recommendation. Say so if you want the chord
added here instead; it adds a `SCHEMA_VERSION` bump and a migration.*

## 4. The invariant, stated precisely

For a deck rendered from results `R` in unit set `u = deliverable_units(system,
Channel.SOLVER)`, with parsed cards `F` (FORCE) and `M` (MOMENT) keyed by SID,
and `G` the GID→(x,y,z) map from the deck's own `GRID` cards:

For each result `r` in `R` with `sid = _sid(base, i, r)`:

```
ΣF  = Σ_{cards in F[sid]}  scale · (n1, n2, n3)
ΣM₀ = Σ_{cards in M[sid]}  scale · (n1, n2, n3)
ΣM  = ΣM₀ + Σ_{cards in F[sid]}  (G[gid] − p_ref) × (scale · n)
```

where `p_ref` is the component's reference point (E-2), and the assertions are:

| Component | ΣF assertion | ΣM assertion |
|---|---|---|
| Wing | `ΣF.z = sf·r.stations[0].sz`, `ΣF.x = sf·r.stations[0].sx` | `ΣM.y = sf·r.stations[0].myy` (torsion, about the LRA); `ΣM.x = sf·r.stations[0].mxx` (bending) |
| Body | `ΣF.z ≈ 0` | `ΣM.y ≈ 0` |
| Tail | `ΣF.z = sf·(r.lt25 + r.lt50)` | *(no independent target — the chordwise moment is the profile's own first moment; assert it equals the in-memory `Σ f_i·(x_i − x_ref)` so the deck and the CSV cannot disagree)* |
| Control | `ΣF.z = sf·r.load_lb` | *(none — §3.1)* |

All quantities are ULTIMATE and in `u`. Every target on the right-hand side is
scaled into `u` through `coordinates.to_force` / `to_moment` — never through a
hand-written factor.

### 4.1 Tolerance policy

Two distinct regimes, and conflating them is the trap:

- **Non-zero targets** (wing, tail, control): `math.isclose(got, want,
  rel_tol=1e-4, abs_tol=…)`. `1e-4` is set by the `%.6E` card format (≈1e-6
  relative per card) accumulated over ≲50 cards, with margin.
- **Zero targets** (body ΣF, body ΣM): a relative tolerance is meaningless
  against zero. Scale the absolute tolerance by the **largest single term**, as
  `test_body_nodal_cards_sum_to_zero` already does:
  `abs_tol = 1e-6 · max|term| + 1e-3` in deck units. For the moment this means
  `max|f_i · (x_i − x_ref)|`, not `max|f_i|` — the lever arm is O(100 in) /
  O(2500 mm) and must be in the scale or the SI check is ~25× tighter than the
  Imperial one for no reason.

The tolerance constants live **in the checker**, not scattered across tests.

## 5. Implementation

### Step 1 — `sloads/export/equilibrium.py` (new, the single owner)

Production module, not a test helper, so the sbeam round-trip harness (the next
backlog item) and any later runtime validator consume the same authority rather
than reimplementing it. Test-only *use* today per E-4.

```python
@dataclass(frozen=True)
class Resultant:
    """Σ force and Σ moment of one parsed load set, about a stated point."""
    sid: int
    fx: float; fy: float; fz: float
    mx: float; my: float; mz: float
    ref: Tuple[float, float, float]
    scale: float          # largest single |term|, for zero-target tolerances

def resultant(forces, moments, grids, sid, ref) -> Resultant: ...
def deck_resultants(deck_text: str, ref_for) -> Dict[int, Resultant]: ...
```

`deck_resultants` parses the deck itself (moving `parse_cards` from
`tests/helpers.py` into this module and leaving a re-export in `helpers.py` so
no existing test moves). `ref_for` is a `sid -> point` callable, so the
per-component reference (E-2) is the caller's decision and the summation is
component-agnostic.

Export `resultant` / `deck_resultants` / `Resultant` from
`sloads/export/__init__.py`.

### Step 2 — `GRID` cards on the body and tail decks (E-5)

- `body_force_moment_cards`: emit a `GRID, gid, , x, 0.0, 0.0` block (scaled
  through `to_grid`) ahead of the FORCE block, from `body_station_gids(r)` and
  `s.x`. Geometry is shared across cases — emit **once**, before the per-case
  blocks, exactly as `stick_model_bdf` does.
- `tail_force_moment_cards`: same, from `_TAIL_GID_BASE + i` and the sorted
  station `x`. Note in a `$` line that y = z = 0: the deck is the chordwise line
  in isolation, not the tail's position on the airplane.
- `control_surface_force_moment_cards`: no `GRID`s; add the `$` chord-fraction
  note (§3.1).
- Header `$` comments gain the moment-closure statement the check verifies, so
  the deck's claim and the test's assertion are the same sentence.

**This changes exported Imperial bytes** for two deck families, so
`tests/fixtures_imperial/digests.json` must be regenerated with
`.venv/bin/python tests/imperial_baseline.py`. Per that module's own docstring a
regeneration is *a claim that the change is intended* — it gets its own
`CHANGELOG.md` line and a sentence in the commit.

### Step 3 — GID-block drift guard

Adding `GRID`s makes GID collisions real for the first time (previously the GIDs
were bare references). Add `test_gid_blocks_are_disjoint`: wing stick model
(1, then 2…N), body mass (1001–1500), body reaction (1501–2000), tail (2001+),
control (3001+) — assert no overlap for every example fixture, and that
`body_station_gids`' existing `ValueError` guard still fires past 500 stations.

### Step 4 — `tests/test_export_equilibrium.py` (new)

One parameterised sweep, the whole point of the step:

```
for example in EXAMPLES (all six):
    for system in (IMPERIAL, SI):
        for component in (wing, body, tail, control):
            assert the §4 table
```

`EXAMPLES` is reused from `tests/imperial_baseline.py` so a new fixture is
covered automatically. Fixtures lacking a slice skip that component with an
explicit reason (never silently) — the `_try` pattern already in
`imperial_baseline.py`.

This closes G2 (SI) and G4 (ga6 body/tail) as a by-product of the sweep shape.

### Step 5 — the structural unit drift guard (`CLAUDE.md` practice 3)

A one-line assertion with outsized value, in `tests/test_deliverable_units.py`:

```python
u = deliverable_units(system, Channel.SOLVER)
assert math.isclose(u.moment.factor, u.force.factor * u.length.factor, rel_tol=1e-12)
```

for both systems. `DeliverableUnits.is_consistent` and `coordinates._checked`
already encode this intent; nothing asserts the *arithmetic* holds. Without it,
a mistyped `LB_IN_TO_N_MM` produces decks that parse cleanly and size structure
to a wrong torsion — and the new moment check would silently inherit the error
on both sides of its own comparison.

### Step 6 — migrate the four existing hand-rolled sums

`test_concept_closure.py` and `test_sbeam_bridge.py` re-point at
`export.equilibrium` (G5). Same assertions, one implementation. This is the
"make it structural" half — leaving the old sums in place would leave five
summation implementations, not one.

### Step 7 — closure trail (Tier M, documented to L depth)

- `CHANGELOG.md` `[Unreleased]`: the invariant, plus a separate explicit line
  for the Imperial byte change and the digest regeneration.
- `docs/30_future/00_backlog.md`: remove the item.
- `docs/40_history/00_completed_development.md`: full step entry (the
  n·W-is-not-the-invariant finding is the part worth recording — it is the kind
  of thing that gets re-proposed otherwise).
- `docs/10_standard/PROGRAM_SPEC.md` sbeam-bridge section: the deck contract now
  includes `GRID` cards for wing/body/tail, and the stated closure each deck
  family satisfies.
- `docs/20_theory/00_theory_sources.md`: the closure gate and its Ch 15 p103
  basis, since it substitutes for a printed oracle (required practice 2).
- `docs/10_standard/CONVENTIONS.md`: the per-component moment reference (E-2) —
  it is a convention, and conventions live there, not in this plan.

## 6. Acceptance

1. Every exported deck, for all six examples, in **both** unit systems, satisfies
   the §4 table at the §4.1 tolerances — force **and** moment.
2. Body decks close to zero in force *and* moment from their own `GRID` +
   `FORCE` cards, verifying the `$` header claim that has been unverified since
   C6.
3. `u.moment.factor == u.force.factor · u.length.factor` for the SOLVER channel
   in both systems.
4. GID blocks are disjoint across all components on every fixture.
5. Appendix A oracles unchanged; both concept fixtures unchanged numerically.
6. `ruff check sloads/ cli.py` clean; `pytest` green on 3.9 / 3.11 / 3.12.
7. The Imperial digest fixture is regenerated **once**, deliberately, and the
   diff is limited to the two deck families that gained `GRID` cards.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Imperial byte change is larger than intended | Regenerate, then `git diff` the regenerated fixture channel-by-channel before committing; acceptance 7 |
| Zero-target tolerance is too loose and the body check passes vacuously | Add a negative test: perturb one body station's `fz` by 1% and assert the checker *fails* |
| Moment check compares the deck against a target derived from the same code path (tautology) | Wing targets come from `r.stations[0].mxx/myy` — the NETLOADS quadrature — not from the nodal loads; body target is the constant 0. Both are independent of the summation being tested |
| Scope creep into the assembled-airframe check | §9 is explicitly a separate item |

## 8. Effort

S–M. Steps 1, 4, 5 are the substance (~1 session). Step 2 is small code but
carries the byte change and its documentation. Steps 3, 6, 7 are mechanical.

## 9. Deliberately out of scope — the assembled-airframe n·W closure

The literal R9 wording remains a real and valuable goal; it is a *different*
step, and it needs decisions this one does not:

- how a `W-xx` wing case pairs to an `F-xx` fuselage case (they are different
  physical conditions today);
- where `n` comes from for a body case (`BodyLoadResult` carries no `nz`);
- the wing/body seam accounting — the fuselage carry-through *is* the wing
  reaction, so the two must not both be counted;
- half-span doubling, valid only for symmetric cases (not `ACRL`, not `TORS`).

**Recommend filing it in the backlog as its own `[E]` item, "Assembled-airframe
n·W closure for symmetric cases", pairing naturally with L-1** (the assembled
stick model), which needs the same seam accounting.
