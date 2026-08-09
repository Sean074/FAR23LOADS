# Design note — sbeam round-trip CI harness

**Backlog item:** `[E] sbeam round-trip CI harness` (raised 2026-08-05, process
review R9). **Status:** **SHIPPED 2026-08-08** (mission phase 1, step 2);
decisions S-1…S-9 below, all implemented as written except where §10 records
otherwise. **Closure tier:** M — no calc-math change and no deliverable
byte change, but new dependency surface, a new CI job and a new
`sloads/export/` module. Documented to L depth because the acceptance *is* a
stated physics gate (`CLAUDE.md` required practice 2), and because it is the
first time sloads takes a dependency on another repository.

Conventions cited throughout:
[`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md) (axes, sign,
units channels, ULT/SF contract, case identity). Deck contract:
[`../10_standard/PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md) sbeam-bridge
section. Sibling step, which this one builds on:
[`07_export_equilibrium_invariant_plan.md`](07_export_equilibrium_invariant_plan.md).

---

## 1. Why this item exists, and what the spike established

C4's acceptance — "the exported BDF parses and solves in the real sbeam" — is
recorded in `PROGRAM_SPEC.md` §sbeam-bridge as a **manual verification step**.
It was performed once, in 2026, and nothing has re-checked it since. The
mission's core claim ("an exported deck solves in sbeam with verified global
equilibrium, continuously in CI") therefore rests on an unrepeated manual act.

**Spike, 2026-08-08 (run before this plan was written).** `examples/ga6_normal`
was exported with `--export-sbeam … --stick-model` and solved with the local
sbeam checkout (`~/Documents/99-Tests/sbeam`, `python -m sbeam ga6.stick.bdf`):
clean exit, `.f06` written, 0.6 s wall clock for three subcases. The recovered
quantities agree with the sloads span CSV to the printed precision:

| Quantity | sbeam `.f06` | sloads `ga6.span_loads.csv` | |
|---|---|---|---|
| SPC reaction T3, root node | `-8.755285E+03` | root `Sz` = `8755.3` lb-ULT | sign-flipped, exact |
| SPC reaction T1, root node | `1.537812E+03` | root `Sx` = `-1537.8` lb-ULT | sign-flipped, exact |
| CBAR elem 1, `BENDING-2 B` | `6.833320E+05` | station-2 `Mxx` = `683332` lb-in-ULT | exact |
| CBAR elem 1, `BENDING-1 B` | `1.222244E+05` | station-2 `Mzz` = `-122224` | sign-flipped, exact |

**So the physics is already right and this is a harness item, not a calc item.**
That is the reason it is the highest-value new test in the project per unit of
effort: it converts an unrepeated manual claim into a standing gate without
having to make anything true first.

Three facts from the same spike shape the design and must not be re-discovered
during implementation:

1. **The root node is not station 0 — it is the aircraft centerline (BL 0).**
   `_root_node` places the clamp half a strip inboard of the first station.
   Because `wing_geometry.surface_properties:113` takes `yroot =
   surf.leading_edge[0][1]` and every fixture defines the wing LE polyline from
   BL 0 (gross-area convention, `span = 2*ytip`), that puts the clamp at
   **y = 0.000 exactly** — the aircraft centerline, *not* the side of body where
   the wing attaches. See §1.1: this is a real modelling limitation, but it is
   **not** something this step changes.
   The clamp is also swept-offset from station 0 in `x`, so the SPC *moment*
   reaction is **not** station-0 `Mxx`/`Myy`: measured root `R2` = `-1.847E5`
   against station-2 `Myy` = `-91410`. A naive "reaction moment == root station
   moment" assertion fails for a correct deck. The clean identities are the
   **force** reactions and the **CBAR element-1 end-B** internal loads (§4).
2. **Only the wing deck is solvable as exported.** `--export-sbeam` accepts
   `--export-target {wing,tail,control}`; only `wing --stick-model` emits `SOL
   101` + `GRID`/`CBAR`/`PBAR`/`MAT1`/`SPC1`. The tail and control decks are
   load-cards-only, and the body deck has no CLI surface at all
   (`body_force_moment_cards` is reached from `app/views/export_report.py`
   only). Solving those needs a wrapper this step builds (S-2).
3. **`examples/concept_heavy.project.json` cannot export today.**
   `--export-sbeam` on it raises `MissingInputError: net wing case 'PHAA' needs
   cl/v_eas_kt (explicit or via a 'case' reference into Project.envelope.vn)`
   from `net_loads._air_cl_v:71`. It is excluded from the matrix and filed as a
   defect (§8).

### 1.1 The centerline clamp, and why it is not this step's to fix (user query, 2026-08-08)

Raised during review: *the wing root node should be the side of body (SOB),
where the wing attaches to the fuselage, not the centerline.* Verified — the
observation is correct, the effect is material, and the fix is **not** a clamp
relocation. Recorded here so the harness does not overstate what its wing
reaction means, and so the real item is filed with its reasoning intact (§8).

**The effect is material.** ga6 carries an inboard rib at BL 23
(`wing_mass.inboard_rib_y`; Appendix A p217 prints "rib BL 23"), and two of its
twenty stations lie inboard of it. PHAA, ULTIMATE:

| Clamp station | `Sz` | `Mxx` | vs BL 0 |
|---|---|---|---|
| BL 0 (today) | 8755 | 683,332 | — |
| BL 15.075 (stn 1) | 8056 | 602,369 | −8 % / −12 % |
| BL 25.125 (stn 2) | 7383 | 528,165 | −16 % / **−23 %** |

A centerline clamp therefore reports a wing root bending moment ~¼ higher than
the wing-to-fuselage joint actually carries; the balance is reacted by the
carry-through structure and the fuselage, not by the root joint.

**But relocating the SPC would not produce the SOB loads.** A single clamp on a
connected CBAR chain reacts the *entire* applied load by statics, wherever it
sits — move the SPC to station 2 and the reaction is still 8755 lb, with
stations 0–1 hanging off it as an inboard stub. What changes is the **internal**
load in the element just outboard of the clamp. Consequences:

- The SOB answer is **already present in the current deck**, as a CBAR internal
  force — it is not a reaction and never will be.
- What the deck lacks is a **node at the SOB**. ga6's BL 23 falls between
  stations 1 and 2; the RJ's BL 40 falls between its stations at 29.7 and 49.5.
  No fixture has a station there.
- The correct model — wing beam from SOB to tip, with the carry-through load
  going into the fuselage instead of into the wing root — **is the wing/body
  seam accounting**, deferred by plan 07 §9 and by L-1. It cannot be reached by
  moving a constraint.

**Two hard constraints on any future fix.**

1. **The station set cannot be truncated at the SOB.** Appendix A's printed
   NETLOADS root (p222: `Sz` +5837, `Mxx` +455555) is station 0 at `y = dy/2`,
   and the closure identity in `theory_sources.md` is `ΣdFz·(y−y₀) = mxx_root`
   about **y₀ = station 0**. Dropping inboard stations breaks the oracle the
   whole FAR23 core is locked to. A SOB station must be *added* as a
   reporting/support node, never subtracted.
2. **There is no authoritative SOB input today.** `inboard_rib_y` exists on
   `WingMassInput` (ga6 23, cessna 24, atr42 38, dhc8 40, RJ 40) but it is the
   WINGINER *mass-panel* start (RSTA), close to but not definitionally the side
   of body — BL 40 is well inboard of a regional jet's ~59 in fuselage
   half-width. `geometry.parametric.fuselage_width` is in the schema but is
   `None` in all five fixtures. Choosing the SOB source is a schema decision.

**What this step does about it:** nothing to the model, one sentence to the
record. The harness asserts what the deck actually claims (§4), and the deck's
`$` header gains a line naming the clamp as the **centerline** node and its
reaction as the **half-span total**, so no consumer reads it as a wing root
design load. The real work is filed as a backlog item in §8.

## 2. Relationship to the equilibrium-invariant step (plan 07)

These are the two export-boundary items the empennage plan's decision T-11 gates
on, and they are complementary, not redundant:

| | Plan 07 — equilibrium invariant | This plan — round-trip harness |
|---|---|---|
| Question answered | "Do the cards sum to what the deck claims?" | "Does a real solver read the deck and recover the same loads?" |
| Reads | the emitted card text | the solver's `.f06` and result objects |
| Catches | card suppression, wrong SID routing, `%.6E` truncation, unit-scale slips | card syntax sbeam rejects, GID references to nothing, sign/frame mismatches, case-control errors |
| Needs a solver | no | yes |

**Sequencing decision (S-9): plan 07 lands first.** Two hard reasons, not
preference: (a) plan 07 step 1 creates `sloads/export/equilibrium.py` as the
single owner of card parsing and resultant summation — this harness consumes it
rather than hand-rolling a sixth summation; (b) plan 07 step 2 (decision E-5)
puts `GRID` cards on the body and tail decks, and **without those GRIDs there
is no geometry to build a body/tail stick wrapper from** (S-2 is unbuildable).

## 3. Agreed design decisions

Recorded here as the decisions of record for this step (user, 2026-08-08).

| # | Decision | Rationale |
|---|---|---|
| S-1 | **sbeam enters as a pinned-SHA optional extra**, `pip install -e '.[solver]'`, plus a **weekly scheduled non-blocking job** that installs `sbeam@main` | Pinning keeps PR CI reproducible — an unrelated sbeam commit must never redden an unrelated sloads PR. The weekly job makes interface drift visible on a channel where it costs nothing. Both repos are public under `Sean074`, so no CI secret is needed |
| S-2 | Scope is the **wing stick model *plus* test-only stick wrappers for the body and tail decks** | The wing alone leaves the fuselage — the component whose whole equilibrium statement is `Σ = 0` — never passed through a solver. The wrapper is test-only: it does **not** become a sloads deliverable, and it does not pre-empt L-1 |
| S-3 | Control-surface decks are **out of scope, permanently for this step** | `ControlSurfaceStation.x` is a dimensionless chord fraction with no chord length on the result; plan 07 §3.1 already decided those decks emit no `GRID`s. There is no geometry to solve. Revisit with L-1 |
| S-4 | Matrix: **`ga6_normal` + `concept_regional_jet` × Imperial + SI** | ga6 is the FAR23 oracle fixture; the RJ is the flagship concept fixture and the mission's own subject. Varying the unit system is what makes the solve catch a `moment.factor ≠ force.factor × length.factor` slip (plan 07's G2), which a force-only check is structurally blind to |
| S-5 | **Interface is both:** one subprocess smoke test through `python -m sbeam` reading the `.f06`, and the numeric assertions through the `parse_bdf` / `run_sol101` API | The subprocess run proves the path a real user takes actually works; the API assertions keep the gate from being hostage to `.f06` text formatting in another repo. Neither alone is honest |
| S-6 | **Reference identities are the force reactions and the CBAR element-1 end-B internal loads** — never a root-node moment comparison | §1 fact 1. The root node is inboard of station 0 on a swept wing |
| S-7 | The harness **skips when sbeam is absent**, but `SLOADS_REQUIRE_SBEAM=1` (set in the CI job) turns the skip into a **failure** | A bare `importorskip` means a broken CI install silently reports green — the exact failure mode this item exists to end. Local dev without sbeam stays frictionless |
| S-8 | The gate is **blocking on 3.11 + 3.12**, in its **own job**, not folded into the 3.9/3.11/3.12 test matrix | Keeps `pip install scipy` off the three existing matrix legs; a separate job names the failure ("sbeam round trip") in the PR check list instead of burying it in a 900-test run. 3.9 is skipped for install cost only — sbeam's own CI covers 3.9 |
| S-9 | **Lands after plan 07** | §2 |

**Addendum (2026-08-08 critical review):** once plan 11's step B5 ships the
assembled full-span deck — the **primary** deliverable per its decision B-5 —
this harness gains an **assembled-deck leg**: free-free, determinate support,
reactions ≈ 0 (the same identity as §3.1's body wrapper, now on the whole
airplane). The S-4 matrix and the wing/body/tail legs are unchanged; the
per-component decks remain views and stay gated.

### 3.1 Open sub-decision — the body wrapper's support set (flagged, my call unless you object)

The fuselage beam is **free-free**: `build_body_loads` assembles it so that
`ΣFz = 0` and terminal `Myy ≈ 3e-10` (plan 07 §1 fact 1). SOL 101 cannot solve a
free-free model — and sbeam's `SUPORT` card is honoured by the **SOL 144** trim
partition only; `sol101.py` and `assembly/stiffness.py` never reference it
(verified 2026-08-08). So an unsupported body deck is singular and
`solve_static` raises `ValueError: Singular stiffness matrix`.

**Recommendation — the determinate-support trick, and it is a feature, not a
workaround.** Constrain the body wrapper at a **statically determinate** set of
DOFs (for the fuselage's `x`-line beam in the `x`–`z` plane: `z` at two
stations plus `x` at one, the rest free), solve, and assert **the reactions come
out ≈ 0**. A determinate support carries exactly the residual the applied set
fails to balance, so this is a *stronger* statement than plan 07's card-sum: it
proves free-free equilibrium **through the solver's own assembly**, including
the lever arms the solver computes from the deck's `GRID` cards, not from
sloads' idea of them. A body deck that closes on paper but reacts non-zero here
has a geometry error the card sum cannot see.

The same trick gives the tail wrapper its support: clamp the first (leading-edge)
chord station, and the reaction is then the deck's own resultant about that
point — which is exactly plan 07's E-2 tail reference, recovered independently.

*This plan is written assuming the recommendation. Say so if you would rather the
body wrapper be root-clamped like the wing (simpler, but then the reaction is
just the resultant again and the free-free claim goes unverified through a
solver).*

## 4. The assertions, stated precisely

For each fixture `P` in S-4's matrix, each unit system `s`, and each deck family:

Let `u = deliverable_units(s, Channel.SOLVER)`, let `R` be the exported results,
and for result `r` at index `i` let `sid = _sid(base, i, r)` — the deck's own
`SUBCASE`/`LOAD` id (M4-2 decisions 8/9). Solve, and for each `sid`:

### Wing (stick model)

| # | Assertion | Independent of? |
|---|---|---|
| W-a | `reactions[_ROOT_GID][0:3] == -ΣF_applied` (the plan-07 `Resultant` for that sid) | Solver vs card text — different code paths |
| W-b | `reactions[_ROOT_GID][3:6] == -ΣM_applied about the root node` | Uses the deck's `GRID` coordinates on both sides, via `equilibrium.resultant(ref=root)` |
| W-c | `reactions[_ROOT_GID].T3 == -sf · r.stations[0].sz` scaled through `to_force` | Yes — target is the NETLOADS quadrature, not the nodal loads |
| W-d | `bar_forces[1]` end B `BENDING-2 == sf · r.stations[0].mxx`, `BENDING-1 == -sf · r.stations[0].mzz`, `SHEAR-1 == sf · r.stations[0].sz` | Yes — same |

W-c/W-d are the substance: they compare a **solver-recovered internal load**
against the **independently computed NETLOADS quadrature**. W-a/W-b are the
cheap global closure and will essentially never fail alone.

### Body (test-only wrapper, determinate support)

| # | Assertion |
|---|---|
| B-a | The deck **solves** — no singularity, no parse error (this is most of the value: it proves the plan-07 `GRID`s are real and consistent) |
| B-b | `Σ|reactions|` ≈ 0 at the §5 zero-target tolerance — free-free equilibrium **through the solver** |
| B-c | The recovered CBAR shear at the aft-most element ≈ 0 — the terminal-`Myy` claim in the deck's own `$` header, verified downstream |

### Tail (test-only wrapper, clamped at the LE station)

| # | Assertion |
|---|---|
| T-a | The deck solves |
| T-b | `reaction.T3 == -sf · (r.lt25 + r.lt50)` scaled through `to_force` |
| T-c | `reaction` moment about the LE station equals the in-memory chordwise first moment `Σ f_i·(x_i − x_LE)` |

### Tolerances

- **Non-zero targets:** `math.isclose(got, want, rel_tol=1e-4)`. Set by the deck's
  `%.6E` card format (≈1e-6 relative per card) accumulated over ≲50 cards, with
  margin — the same reasoning and the same number as plan 07 §4.1, deliberately,
  so the two gates never disagree about what "equal" means.
- **Zero targets** (B-b, B-c): `abs_tol = 1e-6 · max|term| + 1e-3` in deck units,
  where `max|term|` is the largest single contribution **including its lever
  arm** for moment quantities. Reuse `Resultant.scale` from plan 07 rather than
  recomputing — one definition of "small".
- The constants live **in the harness module**, not scattered across test
  functions.

## 5. Implementation

### Step 1 — the dependency (S-1)

`pyproject.toml` gains

```toml
[project.optional-dependencies]
solver = [
    # Pinned by commit: an unrelated sbeam commit must never redden an
    # unrelated sloads PR. Bumped deliberately; see docs/.../10_sbeam_roundtrip…
    "sbeam @ git+https://github.com/Sean074/sbeam.git@<40-char-sha>",
]
```

`dev` **does not** pull it in — `pip install -e '.[dev]'` stays scipy-free and
fast for everyone not touching the export boundary. The pinned SHA and the
reason for the pin go in a comment beside it and in `PROJECT_GUIDE.md`.

### Step 2 — `sloads/export/roundtrip.py` (new; test-only *use*, production code)

Lives in `sloads/`, not `tests/`, for the same reason plan 07's
`equilibrium.py` does: a later runtime "validate this deck" surface must consume
the same authority. Nothing in the shipping code path imports it today.

```python
def solve_deck(deck_text: str) -> Dict[int, "Sol101Result"]:
    """parse_bdf + run_sol101 per subcase. Raises SbeamUnavailable if absent."""

def wrap_as_stick_model(deck_text: str, *, support: Support,
                        system: UnitSystem) -> str:
    """Wrap a cards-only deck (body/tail) in SOL 101 + CBAR chain + SPC1.

    Consumes the deck's own GRID cards (plan 07 E-5) — it invents no geometry.
    Test-only: this is NOT a sloads deliverable and is never written by the CLI
    or the GUI. L-1 supersedes it with a real assembled stick model.
    """
```

`Support` is a small enum/dataclass carrying the two cases S-3.1 needs:
`CLAMPED_FIRST` (tail, wing-like) and `DETERMINATE` (body — `z` at two stations,
`x` at one). Placeholder `MAT1`/`PBAR` properties are **reused from
`sbeam_bridge`** (`_MAT1_E`, `_PBAR_A`, …), imported not re-declared, so the
"reactions are stiffness-independent" comment stays true in one place.

### Step 3 — `tests/test_sbeam_roundtrip.py` (new)

```
@pytest.mark.roundtrip
for project in ("ga6_normal", "concept_regional_jet"):
    for system in (IMPERIAL, SI):
        wing   → assert W-a … W-d
        body   → wrap, solve, assert B-a … B-c
        tail   → wrap, solve, assert T-a … T-c
```

plus **one** subprocess smoke test (S-5): write the ga6 Imperial stick deck to a
`tmp_path`, run `[sys.executable, "-m", "sbeam", str(bdf)]`, assert exit 0, and
assert the `.f06` contains the expected `SUBCASE` ids and an
`F O R C E S   O F   S I N G L E - P O I N T   C O N S T R A I N T` block whose
root `T3` matches W-c. That single test is the end-to-end claim; everything else
is API-level.

Skip semantics (S-7), in `conftest.py` so it is one implementation:

```python
def sbeam_or_skip():
    try:
        import sbeam  # noqa: F401
    except ImportError:
        if os.environ.get("SLOADS_REQUIRE_SBEAM") == "1":
            pytest.fail("sbeam is required in this environment (SLOADS_REQUIRE_SBEAM=1) but is not installed")
        pytest.skip("sbeam not installed — `pip install -e '.[solver]'` to run the round-trip gate")
```

A `roundtrip` marker is registered in `pyproject.toml` so the job can select it
(`pytest -m roundtrip`) and the main matrix can deselect it.

### Step 4 — the negative tests (the part that makes the gate real)

A gate nobody has seen fail is a gate nobody knows works. Three mutation tests,
each perturbing the deck text and asserting the harness **fails**:

1. Scale one wing `FORCE` card's `n3` by 1.01 → W-a and W-c must fail.
2. Displace one body `GRID`'s `x` by 1% → B-b must fail (this is the assertion
   that a card-sum check cannot make, so it must be shown to bite).
3. Swap two `SUBCASE`s' `LOAD` ids → the per-sid assertions must fail rather
   than passing by symmetry.

### Step 5 — CI (S-1, S-8)

`.github/workflows/ci.yml` gains a job:

```yaml
  sbeam-roundtrip:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}", cache: "pip" }
      - run: pip install --upgrade pip && pip install -e '.[dev,solver]'
      - name: Round-trip gate
        env:
          SLOADS_REQUIRE_SBEAM: "1"
          STREAMLIT_SERVER_HEADLESS: "true"
        run: pytest -m roundtrip -v --tb=short --no-cov
```

`--no-cov` because the existing `--cov-fail-under=80` gate belongs to the full
suite; a marker-selected subset would trip it spuriously.

A second workflow, `.github/workflows/sbeam-drift.yml`, runs `on: schedule`
(weekly) with `continue-on-error: true`, installing
`git+https://github.com/Sean074/sbeam.git@main` instead of the pin. Its failure
is a notification that the pin needs a look, never a merge block. It also runs
on `workflow_dispatch` so the pin can be checked on demand before a bump.

### Step 6 — pin-bump procedure (documented, not automated)

`PROJECT_GUIDE.md` gains a short subsection: how to bump the sbeam pin (change
the SHA, run `pytest -m roundtrip` locally against the new SHA, record the bump
in `CHANGELOG.md` with the sbeam commit subject). Bumping the pin is a claim
that the new sbeam still honours the deck contract — the same posture
`tests/imperial_baseline.py` takes about digest regeneration.

### Step 7 — closure trail (Tier M)

- `CHANGELOG.md` `[Unreleased]`: the gate, the new `solver` extra, the new CI job.
- `docs/30_future/00_backlog.md`: remove the item; note in the empennage plan's
  T-11 gate that half of it is now satisfied.
- `docs/40_history/00_completed_development.md`: full step entry — the spike
  table in §1 is the part worth preserving, because "the round trip already
  agreed exactly" is the finding that dates the regression window if one ever
  appears.
- `docs/10_standard/PROGRAM_SPEC.md` sbeam-bridge section: replace "manual
  verification step" with the standing gate, and name what it asserts.
- `docs/20_theory/00_theory_sources.md`: the round-trip identities as a closure
  gate substituting for a printed oracle (required practice 2).
- `docs/10_standard/PROJECT_GUIDE.md`: the `solver` extra, the pin, and the
  bump procedure.
- `cspell.json`: `roundtrip`, `SPCFORCE`, `suport` if not already present.

## 6. Acceptance

1. `pytest -m roundtrip` is green with sbeam installed, for both fixtures in
   both unit systems, across wing / body / tail.
2. The ga6 Imperial wing deck solves through `python -m sbeam` as a subprocess,
   exit 0, and the `.f06` root reaction matches the span CSV at `rel_tol=1e-4`.
3. Each of the three step-4 mutations makes the harness fail, and the failure
   message names the case id and the component.
4. Without sbeam installed, the suite skips those tests and stays green; with
   `SLOADS_REQUIRE_SBEAM=1` and sbeam absent, it **fails**.
5. The existing 3.9/3.11/3.12 matrix is unchanged in content and does not
   install scipy.
6. No exported byte changes — no digest regeneration in this step. (If one
   appears, something in step 2 leaked into the shipping path; stop.)
7. Appendix A oracles unchanged; `ruff check sloads/ cli.py` clean.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Plan 07 slips, and body/tail decks still have no `GRID`s | S-9 makes the ordering explicit. If this step must start first, land wing-only (assertions W-a…W-d) and add body/tail in a follow-on commit — the harness module is written to take a deck family as a parameter, so that split is clean |
| sbeam's SOL 101 API changes and the pin bump becomes a chore | The weekly drift job surfaces it early; the API used is deliberately tiny (`parse_bdf`, `run_sol101`, `Sol101Result.reactions/.bar_forces`) |
| The determinate body support is over-constrained or under-constrained on some fixture, giving a singular solve or a non-zero reaction for a *correct* deck | Choose the support DOFs from the deck's actual station list at runtime (first/last station for `z`), not from fixed indices; the negative test (step 4 #2) proves the check discriminates |
| `.f06` text parsing in the smoke test breaks on an sbeam formatting change | Only **one** test parses text, and it asserts a substring plus one number — not a layout |
| Tautology: the harness compares the deck against a target derived from the same code that wrote it | W-c/W-d targets are `r.stations[0]` — the NETLOADS quadrature — while the deck cards come from `wing_nodal_loads`. Different producers. B-b's target is the constant 0 |
| CI wall clock | Measured: 0.6 s per stick deck, three subcases. Full matrix ≈ 12 solves ≈ under 10 s; the `pip install scipy` dominates and is cached |

## 8. Items to file alongside this step

### 8.1 Backlog item — wing beam is supported at the centerline, not the side of body

**`[E]` Side-of-body station for the wing beam (raised 2026-08-08, user).** The
exported stick model clamps at BL 0; the wing-to-fuselage joint is at the side
of body, and for ga6 the difference is 16 % in root shear and 23 % in root
bending (§1.1). Relocating the SPC does **not** fix it — a single clamp reacts
the whole applied load wherever it sits; the SOB quantity is an *internal* load
and needs a node at the SOB, and the physically correct model routes the
carry-through load into the fuselage instead of the wing root. Scope: (a) decide
the SOB source — a new explicit `SurfaceInput` butt line, or
`geometry.parametric.fuselage_width/2` (unpopulated in every fixture today), or
`wing_mass.inboard_rib_y` (a proxy: it is the WINGINER mass-panel start, and BL
40 is well inboard of the RJ's fuselage); (b) add a SOB station to the exported
station set **without truncating** the centerline-origin stations, since
Appendix A's root is station 0 at `y = dy/2` and the `ΣdFz·(y−y₀) = mxx_root`
closure is stated about it; (c) report/export the SOB shear, bending and torsion
as the wing root design loads, distinct from the half-span totals. **Pairs with
L-1 and with plan 07 §9** — all three need the same wing/body seam accounting,
and none should invent it separately. Effort: M. Full reasoning and the
measured numbers: §1.1 of this plan.

### 8.2 Defect to file alongside this step

**`examples/concept_heavy.project.json` cannot be exported to sbeam [Minor,
found 2026-08-08 by this plan's spike].** `--export-sbeam` raises
`MissingInputError: net wing case 'PHAA' needs cl/v_eas_kt (explicit or via a
'case' reference into Project.envelope.vn)` from
`sloads/modules/net_loads.py:71`. The other five examples export cleanly. It is
either a fixture gap (the wing cases were entered without a `case` reference) or
a derivation gap in the derived-case route; decide which, then fix the fixture
or the derivation. It keeps that fixture out of the S-4 matrix until closed, so
it belongs in `00_backlog.md` under **Open defects**, not inside this step.

## 9. Effort

**M (~1–1.5 sessions).** Steps 2–4 are the substance; step 2's body wrapper is
the only place with real design content. Step 1 and step 5 are ~30 lines of
configuration. The S-2 choice (body/tail wrappers) is what moves this from the
backlog's S–M to M — the wing-only variant would be S.

---

## 10. What shipped, and where it departed from this note (2026-08-08)

Delivered: `sloads/export/roundtrip.py` (`solve_deck`, `wrap_as_stick_model`,
`total_reaction`, `Support`, `Topology`), `tests/test_sbeam_roundtrip.py`
(24 solver tests plus 7 wrapper tests that need no solver), the `sbeam` fixture
in `tests/conftest.py`, the pinned `solver` extra and the `roundtrip` marker in
`pyproject.toml`, the `sbeam-roundtrip` job in `ci.yml`, and
`.github/workflows/sbeam-drift.yml`. Acceptance §6 held: **no exported byte
changed**, so no digest was regenerated.

Four departures, each forced by what the decks actually contain:

1. **The body support is `1234` + `23`, not "z at two stations plus x at one."**
   §3.1's 3-2-1 is three constraints, not six, and cannot be completed into a
   determinate set on a **collinear** node line: no combination of translation
   constraints restrains rotation about the beam axis, and the solve is singular.
   Beam elements carry rotational stiffness at their nodes, so the collinear
   analog constrains that rotation directly — six constraints, no redundancy,
   reactions still fixed by statics alone.
2. **B-c became the whole cumulative table, not the aft-most element's shear.**
   That element carries the last station's load, so its shear is *not* zero
   (measured: −136.79 lb on `ga6_normal`); what vanishes at a free end is the
   bending, trivially. The available statement is far stronger and is the body's
   analog of W-c/W-d: sbeam is handed the `FORCE` cards and the `GRID`
   coordinates and must reproduce `body_loads`' entire Ch 15 cumulative shear and
   bending table, whose terminal value being zero *is* the deck header's
   moment-equilibrium claim.
3. **The wrapper needs node groups.** The tail deck holds **two disjoint beams** —
   the h-tail and the v-tail, each stated from its own leading edge — so their
   chord stations interleave in `x` and their first stations are *coincident*.
   One element run through them solves happily and means nothing, which is a
   silent failure rather than a loud one; `groups` makes the structures explicit
   and a test pins the consequence. Coincident nodes *within* a run are real too
   (`concept_regional_jet` carries the tail air load at exactly a mass lump's
   station) and are rigidly tied rather than chained.
4. **The assembled deck needed a `STAR` topology and no new support.** It ships
   with case control, `GRID`s and its own determinate `SPC1` but **no elements** —
   a load set on a node cloud, which is all a load deliverable needs to be. The
   wrapper adds a tree of bars and changes nothing else, because the support
   under test must be the one the deliverable ships with.

**Solver finding, filed for sbeam, not for sloads.** `recover_reactions`
subtracts the *unreduced* applied vector at the constrained DOFs, so a load a
rigid element transfers onto a constrained node is never subtracted and comes
back out as reaction: on `concept_regional_jet`'s fuselage the aft support
reported 1738.13 lb against an applied set closing to 0.007 lb — to the pound,
the tied node's own load. The harness supports away from tied nodes
(`roundtrip._supportable`), which costs nothing because determinacy needs two
distinct positions and not two particular ones.

**Pin.** `sbeam @ ed23b2681feccd9fadfd2e4b829d414094c4b63c` — the commit the
CONM2 work (plan 12) and this step's spike were both verified against.
`origin/main` was **not** used: it dates from 2026-06-07 and lacks `MASSSET`,
which plan 12 C6's leg will need. The weekly drift job still tracks `main`, so
the divergence stays visible.

**Not in this step:** plan 12 **C6**'s mass-deck leg (`MASSSET` + `GRAV` vs
`mass_cards.inertia_only_cards`). It remains its own backlog item with its own
closure tier; it is now unblocked, and the harness takes a fourth deck family
without structural change.

**One planned item deliberately NOT shipped, because this note contradicts
itself about it.** §1.1 says the wing deck's `$` header "gains a line naming the
clamp as the **centerline** node and its reaction as the **half-span total**",
while acceptance §6 says "no exported byte changes ... if one appears, something
in step 2 leaked into the shipping path; **stop**". A `$` line in
`stick_model_bdf` is an exported byte change and forces an Imperial digest
regeneration. The explicit stop-condition won: the harness asserts what the deck
claims and nothing was added to the deck. The header line is still worth having —
it is the guard against a consumer reading a centerline reaction as a wing root
design load — and it pairs naturally with the `[V]` "wing deck `$` comments
overrun 72 columns" backlog item, which changes the same bytes and needs the same
single digest regeneration. Ship the two together.
