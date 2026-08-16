# Sign-Convention Summary & Report Section — design note

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: ✅ shipped 2026-08-10.** P-1…P-6 user-approved 2026-08-10 and stamped
into `CONVENTIONS.md` §1.1 as decisions **SC-1…SC-6**; the report section and
figures shipped per §4 (`report/conventions_tex.py`,
`tests/test_report_conventions.py`, `SUMMARY_REPORT.md` §4.2.1). P-4's `.BAS`
verification: the basic-lift formula `c·cl_b=(mo/2)(ac−Awo)c` and the
"WL to section zero-lift" datum confirm nose-up-positive twist entries
(`theory_sources.md`, AIRLOADS row). Kept as the plan of record.
**Tier M** at closure: behavior change to the summary report → `SUMMARY_REPORT.md`
+ this note + CHANGELOG + history line. Charter sections relied on:
`CONVENTIONS.md` §1, §1.1 (added with this note), §5, §7.1, §7.2;
`SUMMARY_REPORT.md` §2, §3.3, §4.3.

Two full-code extractions (2026-08-09) back every claim below; each entry is
tagged:

- **VERIFIED** — stated in code/docs, citation given.
- **DERIVED** — not stated anywhere, but mathematically forced by the
  right-handed frame; cannot be changed without changing the frame.
- **PROPOSED** — genuinely absent from the codebase; the stated convention is
  this note's proposal and **requires user approval** before it is stamped into
  `CONVENTIONS.md` or the report.

---

## 1. The frame (everything else follows from this)

All VERIFIED — `export/coordinates.py:6-16`, `CONVENTIONS.md` §1.

- `x` = fuselage station, **positive aft**; `y` = butt line, **positive right
  (starboard)**; `z` = waterline, **positive up**. Right-handed
  (`x̂ × ŷ = ẑ`); identity map to NASTRAN basic CID 0 (`SBEAM_CID = 0`).
- Forces: `fz` = lift (+up), `fx` = drag (+aft), `fy` = side force
  (+starboard). Moments are right-handed about the same axes:
  `mx` roll, `my` pitch, `mz` yaw (`balance.py:535-543`).
- **Physical senses of positive moments (DERIVED — forced by the frame):**
  - `+mx` rolls the **starboard wing up** (roll to port),
  - `+my` pitches the **nose up** (consistent with the one stated instance:
    "a positive M1 (nose-up with alpha)", `validation.py:609`,
    `fuselage_moment.py:31-33`),
  - `+mz` yaws the **nose to port** (nose-left; consistent with the fin:
    `+fy` aft of the CG gives `+mz = dx·fy` and physically pushes the tail
    starboard).
- Centreline reflection (handedness, `CONVENTIONS.md` §7.1): `y → −y`; a force
  flips only `fy`; a moment flips `mx` and `mz`, never `my`
  (`coordinates.py:143-171`).

## 2. VERIFIED conventions (the summary of record)

### 2.1 Airplane state

| Quantity | Convention | Evidence |
|---|---|---|
| Angle of attack α | **Positive nose-up**, measured **waterline to relative wind** (`alpha_wl`); +α ⇒ +lift (`C1 > 0` enforced) | `flight_envelope.py:154-176` (search direction + wind-to-body rotation), `aero_curves.py:9`, `validation.py:631` |
| Tail angle of attack | `AT = alpha_wl + IT − E`; downwash `E = 114.6·CL/(π·ARW)` positive-defined and subtractive; +AT ⇒ up (+`fz`) tail load | `select.py:215, 237-246, 250` |
| Tail incidence IT | Positive = tail chord **nose-up** relative to the waterline (adds to AT) | `inputs.py:833`, `select.py:246` |
| Load factor `nz` | Positive up; inertia force on a station weight is `fz = −NZ·w` (down for +NZ) | `flight_envelope.py:167`, `body_loads.py:9-11, 188` |
| Load factor `nx` | `nx = −DX/W` — the longitudinal **inertia** (deceleration) factor; negative for ordinary positive (aft) drag | `select.py:117, 169` |
| Load factor `ny` | `n_y = L_v/W`, positive **starboard**; each `n` component takes the sign of the force residual in the +aft/+right/+up frame | `balance.py:632`, plan 13 §"lateral balance" |
| Angular accelerations `ω̇ = (p̈, q̈, r̈)` | Right-handed about `(x, y, z)`; carried in **weight-space 1/in**; relief field `f = −m(a_cg + ω̇ × r)`, each axis producing **two** force components | `rigid_body.py:225-251`, `CONVENTIONS.md` §1 |
| Handedness of state | `p_dot`, `r_dot`, `n_y` reverse between handed twins; `q_dot`, `n_z`, `n_x` do not | `results.py:499-501`, `balance.py:824-825` |
| Attitude angles φ/θ/ψ | **Do not exist as state variables anywhere in the suite** — only accelerations are carried; the report shall say so rather than invent them | extraction 2026-08-09 |
| Vertical gust | `Ude` entered as a positive magnitude; `ng = +1` is the **up** gust (increases n), `−1` the down gust | `flight_envelope.py:227, 306-309` |
| Lateral gust | Unsigned — always a positive (+`fy`) fin load; the −hand is minted by reflection | `select.py:603-616, 669` |

### 2.2 Controls

| Quantity | Convention | Evidence |
|---|---|---|
| Elevator δe | **Positive = trailing-edge DOWN** ("TE dn +"); TE-down ⇒ +LT50 (up tail load). Travel limits stored as magnitudes (`EUP`/`EDN`), sign applied at use (−1 for TE-up) | `select.py:216, 303, 369-376`, `inputs.py:846-847` |
| Aileron δa | Deflections stored as **magnitudes per direction**: `down_deflection_deg` (TE-down, +) / `up_deflection_deg` (magnitude, applied negative). Down throw ⇒ positive (up) surface load, up throw ⇒ negative. **Which wing is deliberately unstated** — hand is minted only at assembly, as the case-ID suffix `L`/`R` | `inputs.py:1004-1005`, `aileron.py:68-96`, `CONVENTIONS.md` §7.1 |
| Aileron→wing torsion | Steady-roll proxy `(cm − 0.01·δa)·G·V²`: a TE-down aileron makes the section moment more **negative** (nose-down); only negative torsion is selected (`TMIN` starts at 0) | `select.py:18-21, 148-159` |
| Rudder δr | Entered as an **unsigned magnitude** (`RD`); a positive RD always produces a **positive (+`fy`, starboard)** fin load; the opposite kick is the reflected twin. Direction label PROPOSED in §3 | `inputs.py:889`, `select.py:591-595` |
| Sideslip/yaw cases | Sideslip yaw angles entered **negative** (−19.5°, −15°), producing −`fy`; rudder term positive — they oppose (ga6: −683 + 586 = −97.8 lb) | `select.py:646-662`, `CONVENTIONS.md` §7.1 |

### 2.3 Wing loads and diagrams

| Quantity | Convention | Evidence |
|---|---|---|
| Shear `Sz` | Cumulative, integrated **tip→root** (`stations[0]` = root carries the total); positive = up-acting load | `airloads.py:378-396`, `sbeam_bridge.py:43` |
| Bending `Mxx` (and chord `Mzz`) | Stored as **positive-magnitude integrals** `Σ load·(y − y_ref)` — up-lift gives +`Mxx` ("tip-up"); the CID-0 vector map is owned by `bending_moment_vector`: `Mxx → +x` unchanged, `Mzz → −z` (**negated**, since `(r×F)_z = −dy·fx`) | `airloads.py:392-393`, `coordinates.py:93-122` |
| Torsion `Myy` | About the **LRA** (always named, as %chord); computed about local 25 % chord, transferred once at the boundary (`Myy_lra = Myy_25 + Sz·(x_lra − x_25)`). **`+Myy` = leading-edge-up / nose-up (DERIVED:** `my = (x_lra − x_load)·fz`; lift aft of the axis ⇒ negative, matching the negative Appendix-A root values, e.g. −60 940 lb-in) | `net_loads.py:87-125`, `coordinates.py:218-222`, `net_loads.py:17-18` |
| Cumulative vs free | `WingStationLoad.myy` is **cumulative** (contains the sweep/dihedral transfer); only the free moment may be applied with a position offset — double counting is worth ~20 % of n·W·MAC | `results.py:295-308`, `CONVENTIONS.md` §1 |
| Wing inertia | Entered opposing the air load: `Nz = −NZ`, `Nx = −DX/W`; NETLOADS **adds** air + inertia | `wing_inertia.py:22-25, 221-238` |

### 2.4 Body (fuselage) loads

| Quantity | Convention | Evidence |
|---|---|---|
| Inertia | `fz = −NZ·w` per station (down for +NZ) | `body_loads.py:9-11, 188` |
| Tail load | Applied with its **own** sign (`LT` from FLTLOADS; down-load = negative) | `body_loads.py:189, 256`, `flight_envelope.py:27` |
| Integration | **Nose→tail**; `Myy` accumulates the area under the shear curve; the terminal moment is stated about the **aft-most station** and equals the unbalanced moment closed by the spar reactions (`ΣFz = 0`, terminal `Myy = 0`) | `body_loads.py:99-136` |
| Axis labels | `Sz` vertical shear, `Myy` bending, `Mxx` body torsion, `Mzz` side bending (the latter two currently written as 0 — no producer) | `report/content.py:1096-1100`, `body_loads.py:119-120` |

### 2.5 Empennage

| Quantity | Convention | Evidence |
|---|---|---|
| H-tail | Maps like the wing: span `y`, load `fz`, torsion `myy`; beam is **full span tip-to-tip**, reacted at the fuselage attachments; down-load = negative `LT` | `coordinates.py:186-208`, `tail_span.py:43-51`, `select.py:310-311` |
| V-tail | Spans `z`, load is **side force `fy`**, torsion is **`mzz` = the stored strip torsion negated** (`r×F` reverses for a side force); station `z` stores the root, span in `y`, composed once by `tail_station_to_airplane` | `coordinates.py:188-231`, `CONVENTIONS.md` §7.2 |
| Tail inertia | d'Alembert, signed by the case's load factor **alone** — never "opposing the air load" — and built on the acceleration along the surface's **own normal axis** (2026-08-10, superseding L-8's per-condition half): h-tail `−n_z·W_ht` bending; fin `−n_y·W_vt` bending + `−n_z·W_vt` **axial**. The assembled case still applies each mass once: `balance.fin_sets` reads the air-only `fz − f_inertia` | `tail_span.py` (`distribute` `n_normal`/`n_axial`), `CONVENTIONS.md` §1 |
| Fin waterline | A first-order **sign** quantity (`−Fy·(z − z_cg)`): never implicitly zero | `tail_geometry.py:249-252`, `balance.py:411-415` |

### 2.6 Engine and rotation

| Quantity | Convention | Evidence |
|---|---|---|
| Rotor/prop rotation | **Clockwise from the pilot's view is positive** (signed `max_rpm`; default clockwise) | `engine.py:7-9`, `inputs.py:52-53` |
| Mount reaction torque | Reported **negative** (the reaction to a positive engine torque) — preserved suite convention, every emit site | `engine.py:165, 195, 256, 285`, `CONVENTIONS.md` §5 |
| Gyroscopic moments | Carry **no sign by design**: `Myy` (pitching) from the 2.5 rad/s **yaw** rate, `Mzz` (yawing) from the 1 rad/s **pitch** rate — all four ± permutations enumerated, each with the single-sense +2.5 g vertical and max-continuous thrust | `engine.py:294-339`, `constants.py:42-44` |

### 2.7 Landing gear

| Quantity | Convention | Evidence |
|---|---|---|
| Reactions V/D/S | Per-wheel ground-line "prime" values plus airplane-datum resolutions; vertical formulas positive-magnitude; drag **aft positive** (nose supplementary: aft +0.8·VNP, fwd −0.4·VNP); side loads carry the FAR 23.485 literals (−0.5W inboard / +0.33W outboard); dimensionless NVP/NDP/NS never ULT-scaled | `landing.py:261-310`, `results.py:698-736` |

### 2.8 Export and equilibrium bookkeeping

- A deck's **torsion claim** is about its applied `MOMENT` cards (`m0`); only
  the **bending claim** integrates the `FORCE` lever arms (`m = m0 + Σ r×F`,
  right-handed) — the transfer term is the same order as the torsion itself
  (`equilibrium.py:31-46, 267-281`; `CONVENTIONS.md` §1).
- Per-component moment references: wing → root station, body → aft-most
  station, tail → LE chord station (`equilibrium.py:293-306`).
- **No sign flips at presentation** — verified by sweep of `report/` and
  `app/views/`: values plot as computed (LIMIT), scaled only by units and the
  ULT factor; envelopes two-sided; every torsion names its axis.

## 3. PROPOSED conventions (the gaps — approval required)

Genuinely absent from code and docs. Each proposal is chosen to (a) be
consistent with what the code already computes, and (b) match standard
flight-mechanics usage. **None of these changes any computed number** — they
are labels the report and docs will carry.

| # | Quantity | Proposal | Consistency argument |
|---|---|---|---|
| P-1 | Sideslip β | **+β = relative wind from starboard** (velocity has a +y body component; nose points port of the flight path) | The fin's restoring load is then −`fy`, exactly matching SELECT's negative entered yaw angles (−19.5°, −15°); the computed unhanded "R" case is the +β case |
| P-2 | Rudder δr | **Positive = trailing edge toward port** (left pedal) | Produces +`fy` (starboard fin force) and +`mz` (nose-left) — matching the code's unsigned `RD → +fy`, and the standard convention (positive rudder = TE left) |
| P-3 | Roll/pitch/yaw **rate & attitude labels** for the report | State rates/accelerations right-handed about `(x,y,z)` with the physical senses of §1 (+p̈ starboard-wing-up, +q̈ nose-up, +r̈ nose-port); attitudes stated **not modelled** | Matches `rigid_body.py`'s field verbatim; inventing attitude signs for the report would imply state the suite does not carry |
| P-4 | Wing twist table | Entries (zero-lift angle, deg) are **nose-up-positive in the same sense as α**, relative to the root section; washout (tip nose-down) enters as more-negative tip values | The table feeds the basic (twist) distribution the same way α feeds CL; verify against `AIRLOADS.BAS` before stamping |
| P-5 | Gear reactions in airplane axes | **V positive up (+z), D positive aft (+x), S positive starboard (+y)**, stated per wheel; the FAR 23.485 inboard/outboard literals keep their printed signs | Matches the datum-resolution trigonometry in `landing.py:378-381` and the global frame; today the sense is entirely unstated |
| P-6 | Aileron hand label | When a handed rolling case is reported, name the deflected pair explicitly ("right aileron TE-down / left TE-up") from the case's hand suffix, rather than assigning δa a global sign | The calc carries magnitudes only; hand exists only at assembly (`CONVENTIONS.md` §7.1) — a global δa sign would be a fiction |

On approval: P-1…P-6 are added to `CONVENTIONS.md` §1.1 with a
`(decision SC-n)` marker, and P-4 gets its `.BAS` verification noted in
`20_theory/00_theory_sources.md`. Adding labels is a clarification, not a
convention change — no L-tier sweep is triggered unless a proposal contradicts
code (none found).

## 4. The report section (spec — to implement after approval)

### 4.1 Placement and standard

A new required section **"Axes and sign conventions"**, rendered immediately
after the Input summary and before the envelope figures. At closure,
`SUMMARY_REPORT.md` gains §4.2.1 making it required, cross-referencing §3.3
(whose per-moment/per-torsion rules stay in force — this section states the
global conventions once; §3.3 keeps them repeated at point of use).

### 4.2 Content

1. **Prose** (from a single Python owner, see §4.4): the frame, the reflection
   rule, the ULT/limit boundary pointer, and the two preserved ENGLOADS
   sentences `SUMMARY_REPORT.md` §3.3 already mandates verbatim.
2. **One conventions table** — the §2.1/§2.2 rows condensed to the quantities a
   reader of *this* report meets (state, controls, per-component load signs,
   diagram conventions), each with its physical sense in words.
3. **Three TikZ figures** (inline source, deterministic, greyscale — decision
   G8-2 unchanged; no `\includegraphics`):
   - **`sign_axes`** — three-view line sketch (plan/side/front) of a generic
     airplane: the `x/y/z` triad with "+aft / +starboard / +up", curved arrows
     for `+mx/+my/+mz` labelled with their physical senses, straight arrows
     for +α (side view) and +β (plan view, P-1).
   - **`sign_controls`** — control-surface and engine senses: elevator
     "TE-down +", rudder per P-2, aileron per P-6 (labelled as case-hand, not
     a δa sign), prop rotation "CW from pilot +", mount torque "reported −".
   - **`sign_beams`** — diagram conventions: wing semispan with +Sz/+Mxx/+Myy
     arrows and "integrated tip→root; torsion about the LRA (named per
     figure)"; body beam nose→tail with +Sz/+Myy and the aft-most reference;
     fin with +Fy/+Mzz (negated-strip note).
   Figures are generic sketches, not project geometry; project-specific facts
   (the LRA %chord, the rotor direction in force) appear in captions/table,
   sourced from the `Project`.

### 4.3 Mechanics

- New pure module `sloads/report/conventions_tex.py`: three zero-argument
  emitters returning `tikzpicture` strings, plus the prose/table row constants.
- `Figure` gains nothing; `plots_tex.figure_body_tex` checks a
  `STATIC_EMITTERS` map (keyed as §4.2) **before** the `data is None` absence
  test, so a static figure needs no `PlotData` and can never be "absent".
- `content.build_report` inserts the section unconditionally — conventions
  exist for every project.

### 4.4 Single source + drift guard (CLAUDE.md rule 3)

The conventions table rows live once, in `conventions_tex.py`, each row carrying
the `CONVENTIONS.md` section it restates. New `tests/test_report_conventions.py`:

- byte-determinism (two builds identical);
- the §3.3 mandated sentences present verbatim (engine torque negative,
  clockwise-positive);
- the frame line matches `export/coordinates.py`'s docstring constants
  (drift guard against a silent frame edit);
- every emitted figure contains its required labels ("+aft", "TE-down +", …);
- escape-safety (`^`, `%`, Greek letters) through `plots_tex.escape`;
- the existing PDF compile smoke test (where the tectonic harness runs) covers
  the new TikZ.

### 4.5 Acceptance

- `ruff` clean, full `pytest` green, all Appendix-A oracles untouched (this is
  presentation-only — no calc change).
- Report builds for `ga6_normal` and both concept fixtures; section present,
  three figures render, table cites no convention absent from
  `CONVENTIONS.md`.
- Closure: Tier M trail (CHANGELOG, backlog removal, history line,
  `SUMMARY_REPORT.md` §4.2.1, `CONVENTIONS.md` cross-link).

## 5. Out of scope (filed, not solved here)

- The four flagged producer gaps from the extraction: body `Mxx`/`Mzz` columns
  with no producer; no hinge-moment convention for aileron/flap/tab; the
  load-application-axis vs elastic-axis deck-header stamp (already on the
  backlog); attitude state variables.
