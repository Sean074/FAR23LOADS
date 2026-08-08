# Design note — F25-2: Speeds & placards, Part 25 variant (Mach-margin VD route)

**Backlog item:** `[E] F25-2 — Speeds & placards Part 25 variant (S→M)`
**[contained a Major concept-mode defect]**. **Status: SHIPPED 2026-08-08** —
implemented as planned; the record of what landed is in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
and `CHANGELOG.md`. **Closure tier: L** — new physics (a second,
regulation-alternative VD basis), a `Project` schema/contract change
(`SCHEMA_VERSION` 39 → 40, `MachLimitInput.mc/md` retired), and a changed
governing load set on a shipped fixture.

> **Deviations from this plan as written**, recorded for the doc-sync rule:
> (1) step 0's blocking assumption was **confirmed** — 25.335(a) is
> `VC ≥ VB + 1.32·U_REF` with U_REF from 25.341(a)(5)(i), so D-5 shipped the
> ordering check only, as the plan provided for; (2) the frozen migration fixture
> is `v39_mach_limit_mc_md.json` (renamed from `v38_current.json`, which was the
> file carrying that shape) plus a new `v40_current.json`, rather than a new file
> alongside the old one; (3) the reduction-invariant test compares VD/VC/VA/VF —
> not VD alone — against values read off the pre-change build, which caught a
> wrong expectation for `cessna_210` (its VD is set by the K_d·VCmin term at
> 214.53, not the 1.25·VC floor at 208.75); (4) MACHLIM output moves slightly for
> the **GA** fixtures too, which §5 did not anticipate: their stored MC/MD were
> the manual's *rounded* printed figures, so single-sourcing replaces them with
> the full-precision derived pair. The Appendix A oracles still pass at ±0.1 %
> and no load channel moved on any fixture but the RJ.

Authorities cited throughout:
[`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md) (units channels,
ULT/SF contract — unaffected here, no load quantity is redefined),
[`../10_standard/PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md) (STRSPEED /
MACHLIM sections), [`../20_theory/00_theory_sources.md`](../20_theory/00_theory_sources.md)
(equation citations), [`../20_theory/01_far25_gap_analysis.md`](01_far25_gap_analysis.md)
§1.3 row 2 (the gap this closes), and the verified regulation extract
[`../../reference/14CFR_MC_MD_speed_margin.md`](../../reference/14CFR_MC_MD_speed_margin.md)
(captured 2026-07-20).

---

## 1. The defect, reproduced

`structural_speeds.design_speed_values` applies the FAR 23.335(b) dive-speed
floor **unconditionally**, in every category including concept "C":

```python
vd_125  = 1.25 * vc                                    # sloads/modules/structural_speeds.py
vd_min  = max(kd * vc_min, vd_125)
hard_floor = vd_125 if cat == "C" else vd_min
vd = max(inp.chosen_vd, hard_floor) if inp.chosen_vd is not None else hard_floor
```

There is no route by which a user can select a dive speed on the **Mach-margin**
basis, which is the alternative the regulation itself offers
(14 CFR 25.335(b): VC/MC ≤ 0.8·VD/MD **or** the margin route; 14 CFR
23.335(b)(4) has the identical "need not be shown if" structure). Since
`1.25·VC` **is** the `VC ≤ 0.8·VD` ratio expressed the other way round, what the
code implements today is precisely, and only, the *first* half of that "or".

Reproduced on `examples/concept_regional_jet.project.json` (2026-08-08,
`design_speed_values`):

| Quantity | Fixture intent | What the code produces |
|---|---|---|
| VC | 310 kt | 310 kt |
| VD | `chosen_vd` = 350 kt | **387.5 kt** (= 1.25·VC, silently overriding) |
| MC @ 24,000 ft | 0.7538 | 0.7538 |
| MD | 0.8511 | **0.9423** |
| MD − MC margin | **+0.097** (a normal transport margin) | **+0.189** |

√σ·a at 24,000 ft = 411.19 kt, so MD = VD/411.19 throughout this note.

Consequences, in order of severity:

1. **Every dive-speed load case is inflated.** `flight_envelope.design_inputs`
   reads VD and MD straight out of STRSPEED (`vals["dive_speed_vd"]`,
   `vals["dive_mach_md"]`), and drives `MAN D`, `MAN −D`, `GUST ±D`, `BAL D`,
   `ST ROL D` from them — which then feed SELECT, the wing/tail/body
   distributions, and the exported decks. The airplane is being designed to a
   dive speed 11 % above the one the user asked for.
2. **MACHLIM goes nonphysical.** MNE = 0.9·MD = 0.848, MFC = 1.2·MD = **1.13** —
   a supersonic flutter-clearance Mach for a subsonic transport.
3. **The user's input is discarded without a word.** No warning, no note, no
   validation entry: `chosen_vd` simply does not survive.

### 1b. A second, independent defect found while reproducing this — MC/MD split brain

`MachLimitInput.mc/md` are *stored* in the project JSON, but the Streamlit
Speed–Altitude tab ignores them and recomputes from `design_speed_values`
(`app/views/structural_speeds.py`, "MC/MD … read them from there instead of
re-asking"). The registry/CLI path does **not**:

```
$ registry.get("mach_limit")(regional_jet)   →  MC 0.74   MD 0.82   MNE 0.738  MFC 0.984   (stored)
   GUI Speed–Altitude tab, same project      →  MC 0.7538 MD 0.9423 MNE 0.848  MFC 1.13    (derived)
```

Same project, same module, two different answers depending on the front-end —
which violates the "GUI, CLI and tests are interchangeable front-ends" contract
in `PROJECT_GUIDE`. It is fixed here rather than filed, per CLAUDE.md required
practice 3 (*make it structural*) and 4 (*generalize on first find*): the
margin is a statement *about* MC and MD, so there must be exactly one MC/MD.

---

## 2. Decisions taken (user, 2026-08-08)

| # | Question | Decision |
|---|---|---|
| D-1 | Which category owns the margin route? | **Concept "C" only.** No `"T"` category is introduced here; F25-1 defines the transport preset and will inherit this resolver unchanged. |
| D-2 | How is the route selected? | **Explicit enum** `vd_basis` on the speeds slice — `"speed_ratio"` (default, today's behaviour) or `"mach_margin"`. Nothing changes silently for an existing project. |
| D-3 | MC/MD single source? | **Fix it now.** `MachLimitInput.mc/md` retire; MACHLIM derives MC/MD from `design_speed_values` on every path. Schema bump + migration hop + drift-guard test. |
| D-4 | Margin default and floor | **Default 0.07 M.** 0.05–0.07 permitted only with an explicit rational-analysis basis, flagged everywhere it appears, with a GUI note that it demands significant justification and **represents a certification risk**. Below 0.05 M is **rejected** — the CFR floor is absolute. |
| D-5 | VB | **Input-only.** Accept an optional `vb_kt` and check VC against it; computing VB per 25.335(d) stays with F25-1/L-4. |
| D-6 | M2-10 placard ladder | **In scope.** The hardcoded `_MC_MD_MARGIN = 0.05` becomes the resolved margin, and the placard block reports the implied MC→MD margin. |
| D-7 | 25.335(b)(1) upset criterion (7.5°/20 s/1.5 g) | **Out.** Filed as a new backlog item (§8). |

**Deliberate, documented deviation from the regulation's scope (D-1):** FAR
23.335(b)(4) offers the margin route to normal/utility/acrobatic airplanes too.
This step withholds it from N/U/A so that the Appendix-A-oracle-locked FAR 23
path is provably untouched. `vd_basis = "mach_margin"` in a FAR 23 category
**raises** with a message naming the restriction. Extending it to N/U/A (and to
the dormant commuter tier at 0.07/rational/0.05 per (b)(4)(iii)) is a follow-on
item in §8.

---

## 3. Step 0 — reference-first (blocking, before any code)

Per the reference-authority rule and F25-0's discipline, **no equation lands
without a captured regulation extract.** Two rows need pulling:

1. **25.335(a)** — the VC-vs-VB margin. The gap analysis marks its exact wording
   *(verify)*. Capture the current eCFR text into a new
   `reference/14CFR_25_335_design_airspeeds.md` (pattern:
   `14CFR_Part25_engine_torque.md`), with amendment level and capture date.
2. **25.335(d)** — the VB definition, captured for completeness even though VB
   computation is F25-1's.

**Assumption to be confirmed against that text, stated up front:** 25.335(a)'s
VC-vs-VB margin is expected to involve the 25.341(a)(5) reference gust velocity
U_ref (believed `VC ≥ VB + 1.32·U_ref`-shaped). U_ref is *not implemented
anywhere in the suite* — it arrives with F25-1's transport gust pack. **If the
verified text does require U_ref, this step ships only the ordering check
(`VC > VB`, plus VB ≤ VC ≤ VD sanity) and records the U_ref term as explicitly
deferred to F25-1** in both the module docstring and the gap-analysis row.
Shipping half a margin check silently would be the exact failure mode this
project's reference rule exists to prevent.

Step 0 also appends a §5 entry to `reference/14CFR_MC_MD_speed_margin.md`
recording that the 0.07-default / 0.05-floor policy is now implemented in code,
with the resolver's name.

---

## 4. Design

### 4.1 The margin policy resolver (the single owner)

Lives in `sloads/modules/structural_speeds.py` — the module that already owns
the design speeds (`flight_envelope.design_inputs` reads from it, not the other
way round) — and is exported in `__all__`. Two module constants replace the
current `_MC_MD_MARGIN = 0.05`:

```python
MACH_MARGIN_DEFAULT = 0.07   # 25.335(b)(2) rule default (Amdt 25-91, eff. 1997-08-28);
                             # AC 25.335-1A (2000): "sufficient without further
                             # investigation". Also 23.335(b)(4)(iii), commuter tier.
MACH_MARGIN_FLOOR   = 0.05   # absolute CFR minimum -- 25.335(b)(2) final sentence;
                             # 23.335(b)(4)(ii). Never reducible.
```

```python
class MachMargin(NamedTuple):
    required: float       # the margin MD must clear
    basis: str            # "default 0.07M" | "rational analysis: <user text>"
    reduced: bool         # True when required < MACH_MARGIN_DEFAULT (drives every flag)

def resolve_mach_margin(inp: StructuralSpeedsInput) -> MachMargin:
    ...
```

Resolution rules — note the distinction that keeps this coherent: **the 0.05
floor constrains what the user may *declare*; a short *achieved* margin raises
VD**, exactly like every other `chosen_*` speed in this module.

| `mach_margin_min` | `mach_margin_basis` | Behaviour |
|---|---|---|
| `None` | — | required = 0.07, `reduced = False`, clean |
| ≥ 0.07 | anything | required = the value, clean |
| 0.05 ≤ v < 0.07 | non-empty | required = v, **`reduced = True`** → flagged in the module note, in `validation.py`, and in the GUI |
| 0.05 ≤ v < 0.07 | empty/None | **`ValueError`** — "a margin below 0.07 M requires an explicit rational-analysis basis (25.335(b)(2), including the effects of automatic systems)" |
| < 0.05 | anything | **`ValueError`** — "0.05 M is the absolute regulatory floor and may not be reduced" |

### 4.2 VD resolution

`design_speed_values` is restructured so the atmosphere is resolved *before* VD
(today MC/MD are computed last):

```python
a, sigma = standard_atmosphere(inp.shoulder_altitude_ft)
q = math.sqrt(sigma) * a                       # kt(EAS) per unit Mach
mc = vc / q

if basis == "mach_margin":                     # category C only (D-1)
    mm = resolve_mach_margin(inp)
    vd_margin_floor = (mc + mm.required) * q   # 25.335(b)(2) / 23.335(b)(4)(iii)
    vd = max(inp.chosen_vd, vd_margin_floor)
    # NOTE: the 1.25*VC ratio floor is deliberately NOT applied -- the regulation
    # offers the two routes disjunctively ("or"), and 1.25*VC IS the 0.8 ratio.
else:
    ...unchanged...                            # today's code, byte-for-byte

md = vd / q
```

Preconditions for the margin route, each raising `MissingInputError` with a
concrete message: `category == "C"`; `shoulder_altitude_ft > 0` (a Mach margin
at sea level is meaningless); `chosen_vd is not None` (there is nothing to
honour otherwise — the route *is* "the user picks VD/MD").

`DesignSpeeds` gains four fields (appended with defaults, so existing keyword
construction and attribute access are untouched): `vd_basis`,
`mach_margin` (achieved, `md - mc`), `mach_margin_required`,
`mach_margin_reduced`.

Worked results on the RJ fixture, which double as the test vectors:

| `chosen_vd` | MD | achieved margin | Outcome |
|---|---|---|---|
| 350 | 0.85112 | **+0.09728** | honoured as-is, clean — **the fixture's intent, restored** |
| 338.79 | 0.82384 | +0.07000 | exactly at the default; honoured, clean |
| 335 (basis given) | 0.81471 | +0.06087 | honoured, **flagged** (`reduced`) |
| 335 (no basis) | — | — | `ValueError` |
| 320, required 0.07 | — | — | VD **raised** to 338.79; note records the raise |
| `mach_margin_min = 0.04` | — | — | `ValueError` (below the 0.05 floor) |

### 4.3 Reported output

The `Structural design speeds` condition gains, when the margin route is active:
`Dive Mach margin MD−MC` (key `dive_mach_margin`) and `Required Mach margin`
(key `required_mach_margin`), plus a note stating the basis, that the 1.25·VC
ratio floor is not applicable on this route (naming the value it *would* have
imposed, so the difference is auditable — 387.5 kt for the RJ), and, when
`reduced`, the certification-risk sentence with the user's basis text quoted.

### 4.4 Placards (M2-10 ladder, D-6)

- `operational_target_checks`: `_MC_MD_MARGIN` deleted; the MMO check uses
  `resolve_mach_margin(...).required`. A target MMO on the RJ now needs
  MD ≥ MMO + 0.07, not + 0.05.
- `operational_placards` output block gains the implied MC→MD margin with the
  `< 0.07` flag, as `14CFR_MC_MD_speed_margin.md` §4 asks for the VMO/MMO form.
- No change to VNE/VNO/VFE, and the both-families display decision from M2-10
  stands.

### 4.5 MC/MD single source (D-3)

- `MachLimitInput` keeps `shoulder_altitude_ft` / `max_operating_altitude_ft` /
  `increment_ft`; `mc` and `md` are **removed**.
- `mach_limit_lines(inp, mc, md)` takes them as explicit arguments.
  `mach_limit.run(project)` calls `design_speed_values(project, project.speeds)`
  and passes `ds.mc`, `ds.md` — so the CLI, the registry, the report and the GUI
  all produce one answer. The `MissingInputError` when `speeds` is absent
  is retained and extended to the missing-`aero_coeffs` case (MC/MD now depend
  on the design speeds, hence on CLmax).
- Callers to update: `app/views/structural_speeds.py` (its local
  `design_speed_values` call collapses into the module),
  `sloads/report/content.py` (both the design-speed table at ~L570, which
  currently sources MC/MD from `speeds.mach_limit`, and the figure builder at
  ~L771).

### 4.6 Schema (SCHEMA_VERSION 39 → 40)

`StructuralSpeedsInput` gains, all optional and all defaulting to today's
behaviour:

```python
vd_basis: str = "speed_ratio"                 # "speed_ratio" | "mach_margin"
mach_margin_min: Optional[float] = None       # None -> MACH_MARGIN_DEFAULT (0.07)
mach_margin_basis: Optional[str] = None       # rational-analysis / HSPF justification
vb_kt: Optional[float] = None                 # rough-air speed, 25.335(d) -- input only
```

Migration hop `v39 → v40` in `sloads/migrations.py`:

- drop `speeds.mach_limit.mc` / `.md` (they were already ignored by the GUI —
  the values on disk are not a user decision being discarded but a stale
  duplicate; the hop docstring records this and cites §1b);
- default `speeds.vd_basis = "speed_ratio"`, so **every existing project keeps
  its current numbers exactly**;
- a frozen fixture `tests/fixtures_schema/v39_mach_limit_mc_md.json` pins the
  hop, per the frozen-fixture discipline in `test_migrations.py`.

An unknown `vd_basis` string is a `ValueError` at read, not a silent fallback.

### 4.7 GUI (`app/views/structural_speeds.py`, Design Speeds tab)

Shown **only** when the category is "C" (D-1):

- a radio, `Dive speed basis` — *Speed ratio (VD ≥ 1.25·VC)* / *Mach margin
  (MD ≥ MC + margin)*, with help text naming 25.335(b) and the "or";
- on the margin branch: `Minimum Mach margin` (default 0.07, `min_value=0.05`
  so the widget itself cannot express an illegal value) and a
  `Rational-analysis basis` text input that becomes **required** below 0.07;
- a persistent `st.warning` under the margin input whenever it is below 0.07:

  > Reducing the MC→MD margin below **0.07 M** requires **significant
  > justification** — a rational analysis including the effects of automatic
  > systems (14 CFR 25.335(b)(2)) — and **represents a certification risk**.
  > AC 25.335-1A treats 0.07 M as sufficient without further investigation;
  > sub-0.07 margins in service are HSPF-credited and typically remain above
  > 0.06 M. 0.05 M is an absolute floor. See
  > `reference/14CFR_MC_MD_speed_margin.md` §2–3.

- a live caption on the margin route showing achieved vs required margin and
  the VD that the ratio route would have imposed;
- an optional `VB (rough-air speed)` input feeding the D-5 check.

### 4.8 Validation (`sloads/validation.py`)

Three new `ConsistencyWarning` codes on `PAGE_STRUCTURAL_SPEEDS`, following
`_check_operational_targets`' shape (silent when the speeds cannot be computed):

| code | condition |
|---|---|
| `mach_margin_reduced` | margin route active with `required < 0.07` — states the basis and the certification-risk framing |
| `mach_margin_below_ratio_floor` | informational: the resolved VD is below 1.25·VC (expected on this route; surfaced so it is never a surprise) |
| `vb_above_vc` | `vb_kt` is set and ≥ VC (25.335(a) ordering) |

---

## 5. Blast radius — what changes numerically

FAR 23 categories: **nothing.** `vd_basis` defaults to `"speed_ratio"`, whose
code path is unchanged, and the margin route is category-gated. The Appendix A
oracles (p155 VD 198.53; p156 VD 212.5) are the guard.

Concept fixtures, once `vd_basis` is switched:

| Fixture | Today's VD | On the margin route | Note |
|---|---|---|---|
| `concept_regional_jet` | 387.5 | **350** (its own `chosen_vd`) | **switch it** — this is the defect case |
| `atr42_100` | 300 | — | `chosen_vd` 300 = 1.25·240 exactly; leave on `speed_ratio` |
| `dhc8_dash8` | 306.25 | — | 306 vs 1.25·245 = 306.25, a 0.25-kt nudge; leave |
| `concept_heavy` | 312.5 | — | = 1.25·250 exactly; leave |

So exactly one fixture moves, and its loads **decrease**. Re-baselining is
required in: `tests/test_concept_regional_jet.py`, `tests/test_concept_closure.py`
(RJ deck resultants), any RJ figure in
[`../40_history/02_verification_baseline_0.3.0.md`](../40_history/02_verification_baseline_0.3.0.md),
and the RJ summary-report snapshot if one is pinned. Every changed number must
be recorded in the history entry as **a defect fix — the previous values were
wrong**, not as a methodology tuning.

MACHLIM on the RJ: MNE 0.848 → **0.766**, MFC 1.13 → **1.021**.

---

## 6. Acceptance — the CI gates (benchmark-first, written with the feature)

No printed oracle exists for the margin route, so per CLAUDE.md required
practice 2 the gates are **stated invariants**, all in
`tests/test_structural_speeds.py` unless noted:

1. **FAR 23 oracles unchanged** — p155 VD 198.53, p156 VD 212.5, MC 0.323,
   MD 0.403 (±0.1 %). Existing tests, must pass untouched.
2. **Reduction invariant** — for every fixture in `examples/`, `vd_basis =
   "speed_ratio"` reproduces the pre-change `DesignSpeeds` tuple exactly
   (values frozen in the test). This is the "concept mode reduces exactly to
   FAR23 on GA inputs" invariant applied to the new switch.
3. **Margin route honours a compliant VD** — RJ, `chosen_vd = 350` →
   `vd == 350.0`, `md ≈ 0.85112`, `mach_margin ≈ 0.09728`, `reduced is False`
   (rel_tol 1e-3).
4. **Margin route raises a short VD** — `chosen_vd = 320` → `vd ≈ 338.79`,
   achieved margin ≈ 0.07000.
5. **Policy table** — parametrised over §4.1: 0.06 + basis → accepted and
   `reduced`; 0.06 without basis → `ValueError`; 0.04 → `ValueError`; default
   → 0.07.
6. **Category gate** — `vd_basis = "mach_margin"` with category N/U/A raises.
7. **Precondition gates** — zero shoulder altitude, or no `chosen_vd`, raise.
8. **MC/MD drift guard** (`tests/test_mach_limit.py`) — for every fixture in
   `examples/`, `registry.get("mach_limit")(project)` yields MNE and MFC equal
   to `0.9·ds.md` and `1.2·ds.md` from `design_speed_values`. This is the test
   that would have caught §1b, and it is the structural guard CLAUDE.md rule 3
   demands.
9. **Schema round-trip** (`tests/test_io.py`, `tests/test_migrations.py`) — the
   four new fields survive save/load; the frozen v39 fixture migrates with
   `mc`/`md` dropped and `vd_basis = "speed_ratio"` applied; `SUPPORTED_FLOOR`
   respected; unknown `vd_basis` raises.
10. **Placard ladder** (`tests/test_structural_speeds.py`) — a target MMO now
    requires MD ≥ MMO + 0.07 by default, and + the resolved value when reduced.
11. **VB check** — `vb_kt ≥ VC` produces `vb_above_vc`; below produces nothing.
12. **Validation codes** (`tests/test_app_components.py` or the validation
    test) — the three new codes fire on a purpose-built project and are silent
    otherwise.
13. **RJ end-to-end** (`tests/test_concept_regional_jet.py`,
    `test_concept_closure.py`) — the fixture runs end-to-end on the margin
    route, VD is 350, and the deck resultants re-baseline cleanly.
14. **DATA_DICTIONARY regenerated** — `docs/generate_data_dict.py`;
    `tests/test_data_dictionary.py` must pass (it is the drift guard for the
    generated file).

Plus the standing merge gate: `ruff check sloads/ cli.py` clean, full `pytest`
green on 3.9 / 3.11 / 3.12.

---

## 7. Implementation order

Each step ends green; nothing is left half-applied across steps.

| # | Step | Files |
|---|---|---|
| 0 | **Reference capture** (§3, blocking) | `reference/14CFR_25_335_design_airspeeds.md` (new), `reference/14CFR_MC_MD_speed_margin.md` §5 |
| 1 | Constants + `MachMargin` + `resolve_mach_margin`, with the §4.1 policy table as its unit test | `sloads/modules/structural_speeds.py`, `tests/test_structural_speeds.py` |
| 2 | Schema fields + migration hop + frozen fixture (behaviour still identical — gate 2 passes here) | `sloads/models/inputs.py`, `sloads/models/project.py`, `sloads/io.py`, `sloads/migrations.py`, `tests/fixtures_schema/v39_mach_limit_mc_md.json`, `tests/test_migrations.py`, `tests/test_io.py` |
| 3 | VD resolution + `DesignSpeeds` fields + reported values/notes (gates 3–7) | `sloads/modules/structural_speeds.py` |
| 4 | MC/MD SSOT: `MachLimitInput` trim, `mach_limit_lines` signature, all callers (gate 8) | `sloads/modules/mach_limit.py`, `sloads/report/content.py`, `app/views/structural_speeds.py`, `tests/test_mach_limit.py` |
| 5 | Placard ladder + VB check + validation codes (gates 10–12) | `sloads/modules/structural_speeds.py`, `sloads/validation.py` |
| 6 | GUI controls, warnings, captions | `app/views/structural_speeds.py` |
| 7 | RJ fixture switched to the margin route; all downstream baselines re-cut (gate 13) | `examples/concept_regional_jet.project.json`, `tests/test_concept_regional_jet.py`, `tests/test_concept_closure.py` |
| 8 | **Tier-L closure** (below) | docs, `CHANGELOG.md`, backlog |

### Step 8 — closure checklist (tier L, same session as the last code step)

- `CHANGELOG.md` `[Unreleased]`: the defect fix (RJ loads decrease), the new
  VD basis, the schema bump, the MC/MD SSOT fix.
- `docs/40_history/00_completed_development.md`: **full step format** —
  motivation, the two defects, decisions D-1…D-7, the numbers before/after,
  the gates.
- `docs/10_standard/PROGRAM_SPEC.md`: STRSPEED inputs/outputs (new fields and
  reported values) and the MACHLIM section (MC/MD are derived, not input).
- `docs/20_theory/00_theory_sources.md`: the 25.335(b)(2) / 23.335(b)(4)
  citation for the margin route, pointing at the reference extracts.
- `docs/20_theory/01_far25_gap_analysis.md` §1.3 row 2 and §3 F25-2: mark the
  margin route implemented, note what remains (upset criterion, N/U/A route,
  VB computation).
- `docs/10_standard/DATA_DICTIONARY.md`: regenerate via
  `docs/generate_data_dict.py` (never hand-edit).
- `docs/10_standard/GUI_USER_GUIDE.md`: the new Design Speeds controls and the
  certification-risk warning.
- `docs/40_history/03_resolved_decisions.md`: D-1 (C-only) and D-4 (0.07
  default / 0.05 floor / justification requirement) as recorded decisions.
- `docs/30_future/00_backlog.md`: **remove** F25-2; add the §8 follow-ons.
- `cspell.json`: `HSPF`, `MMO`, `VMO`, `Amdt` if not already present.
- Nothing in `CONVENTIONS.md` changes — no load quantity, axis, unit channel or
  safety factor is touched by this step.

---

## 8. Explicitly out of scope — filed as new backlog items

1. **25.335(b)(1) upset-criterion calculator** (7.5° / 20 s / 1.5 g per
   AC 25.335-1A) — the regulation's *other* margin term, of which the 0.07 is
   the "greater of" partner. Until it exists, the tool checks only the Mach
   term; the module note must say so, since "greater of" means the implemented
   check is not by itself sufficient. **[V]**, descriptive name: *"Upset-criterion
   speed increase (25.335(b)(1) / 23.335(b)(4)(i))"*.
2. **Margin route for FAR 23 categories** — 23.335(b)(4) permits it for N/U/A
   (0.05) and commuter (0.07 / rational / 0.05); withheld here by D-1. Pairs
   with the dormant "Distinct Commuter category" item. **[V]**
3. **VB computation per 25.335(d)** and the full VC-vs-VB gust margin with
   U_ref — belongs to F25-1's transport gust pack (§3). **[V]**
4. **MACHLIM's MFC = 1.2·MD is GA-lineage** (MACHLIM.BAS, Ref 1 Ch 6). Even
   with the RJ corrected it gives MFC 1.021 — transonic-nonsense for a subsonic
   transport, where flutter clearance is conventionally MD + ~0.05–0.10 M.
   Noticed while reproducing this defect; needs a verified reference and a
   decision before any change. **[V]**, descriptive name: *"Flutter-clearance
   Mach basis for transport concepts"*.
5. **Assembled-airframe re-baseline of the RJ deck** — covered by the existing
   sbeam round-trip harness item; noted only so the re-cut baselines in step 7
   are re-verified there once that harness lands.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Silent behaviour change for an existing concept project | `vd_basis` defaults to `"speed_ratio"`; gate 2 pins byte-identical results for every current fixture. The route is opt-in, by decision D-2. |
| A user reads the margin check as compliance | Every affected output carries the existing concept banner plus, on the margin route, the "the (b)(1) upset term is not evaluated" sentence (§8 item 1). |
| Re-baselined RJ numbers hide an unrelated regression | Step 7 is a separate, isolated step; the diff must show *only* D-line-driven changes. Non-D cases (`PHAA`, `NHAA`, ground) must be numerically unchanged — assert that explicitly rather than eyeballing it. |
| `MachLimitInput` field removal breaks a third-party/saved file | Migration hop + frozen fixture + `SUPPORTED_FLOOR` respected; unknown-key tolerance in `_filtered` already drops strays. |
| Scope creep into F25-1 | VB is input-only (D-5); no gust, no envelope, no category "T". |
