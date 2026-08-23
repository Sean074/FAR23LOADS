# Cessna 210 from blank — oracle GUI build review (milestone 0.7.1)

**Status (2026-08-23):** in progress. Milestone branch `dev/v0.7.1`.

## Aim

Build a normally-aspirated Cessna 210 (210L/M class) **from a blank project, by hand, in
the oracle GUI** (`oracle_app/Oracle.py`), with every value typed by the owner from public
data, and run it from Geometry through Wing Loads and Landing Loads; then open the saved
file in the main GUI (`app/Home.py`) and take it through Export & Report. The oracle GUI
shipped as a beta at the 0.7.0 cut (`v0.7.0`, 2026-08-23) with issues #67–#74 open; this
exercise tests that release as a first-time user would, and verifies the workflow the
docs describe.

The bundled `examples/cessna_210.project.json` is **not consulted** while building. The
new model is `projects/C210_new.project.json` (the sidebar's Save-to-disk name for project
name `C210_new`) and does not replace the example. Comparisons against the example are a
closing step, not an input.

**Roles:** the owner drives the GUI and reports what they see; Claude keeps this log,
answers questions as they arise, and writes the closures. Git is the owner's.

## Ground rules — how a finding is classified

The oracle GUI is "ready for release": the expectation going in is **no** bugs. Every
finding gets exactly one of three classes, decided when it is logged:

| Class | Meaning | Where it goes |
|-------|---------|---------------|
| **a — interface does not work** | A page, widget or path a first-time user needs cannot be completed as shipped. This class pulls the 0.7.0 release back: if any `a` survives the exercise, **0.8.0 is repurposed to fix the oracle GUI** before band B's planned content. | Filed as an issue at once; fixed in 0.8.0 (or sooner if the owner decides the release is unusable) |
| **b — bug** | Wrong number, wrong state, crash, stale display; the path completes but the result cannot be trusted. | Fixed in **0.7.2** (PATCH) |
| **c — development** | Works as designed but the design is short: a missing field, a better flow, a clearer label, a capability the FAR23 suite never had. | Backlog, some later `0.X.0` |

A finding that matches an already-filed beta issue (#67–#74) is logged **against that
number**, not as a new one — the value of that row is the reproduction from a real build.

Findings are numbered `C210-N` in order of discovery. Each row carries: page, what was
done, what happened, what was expected, class, and disposition (issue number when filed).
Nothing is fixed during the exercise unless it blocks the next page; a blocking `a` is
noted here first, then handled.

## Route through the GUI

The oracle GUI's page set is derived from `sloads.workflow.oracle_steps()` — fourteen
pages. The route for this exercise, in page order, marking what is in scope:

| # | Page (`workflow.py` key) | `.BAS` it replicates | In scope |
|---|--------------------------|----------------------|----------|
| 1 | Geometry (`configuration_layout`) | WINGGEOM | yes — produces `geometry` |
| 2 | Weight & Mass Properties (`weight_mass`) | WTESTIMA + WTONECG + WTENV | yes — produces `mass` |
| 3 | Aerodynamic Data (`aero_coefficients`) | (feeds STRSPEED / FLTLOADS) | yes — produces `aero_coeffs` |
| 4 | Structural Speeds (`structural_speeds`) | STRSPEED + MACHLIM | yes — produces `speeds` |
| 5 | Flight Envelope (`flight_envelope`) | FLTLOADS + SELECT | yes — produces `flight_loads` |
| 6 | **Wing Loads** (`wing_loads`) | AIRLOADS + WINGINER + NETLOADS | **yes — target 1** |
| 7 | Fuselage Loads (`fuselage_loads`) | NETLOADS | optional |
| 8 | Tail Loads (`tail_loads`) | TAILDIST + BALLOADS | optional |
| 9 | Aileron Loads | AILERON | no |
| 10 | Flap Loads | FLAPLOAD | no |
| 11 | Tab Loads | TABLOADS | no |
| 12 | Engine Mount Loads | ENGLOADS | no |
| 13 | One Engine Out | ONENGOUT | n/a (single) |
| 14 | **Landing Loads** (`landing_loads`) | LGFACTOR + LANDLOAD | **yes — target 2** |

**Export is not an oracle page** (by design: OG-1/OG-13 — the oracle GUI exposes only
what the McMaster suite had; sbeam decks, plots, the workbook and the report are `app/`
only). The export leg is therefore: *Save to disk* in the oracle GUI → launch
`app/Home.py` → *Open* `C210_new.project.json` from the sidebar → **Export & Report**.
That the file opens unchanged in the other front-end is gate G6 and is checked here as
step 15.

| 15 | Export & Report (`export_report`, main GUI) | — | yes — sbeam cards for wing and gear |

The oracle GUI shows only `ORIGINAL | supplied` fields (`field_registry.SUPPLIED_RULE`): the
sloads-only wing `ref_axis_pct`, spar fractions, `sob_y_in` and the fuselage `z_centre` are
**not offered** there, by design (OG-2/OG-5). The LRA beam exporter refuses a blank
`ref_axis_pct`, so step 15 begins by setting the wing LRA (0.40 c) on the main GUI's
Geometry page before exporting. Expected behaviour, recorded so it is not logged as a defect.

## Data sheet — Cessna 210L/M, public figures

All values are the owner's to source and type; this table is Claude's pre-read of the
figures the pages will ask for, with a confidence mark so the owner knows which to check
against the type certificate (TCDS 3A21) or a POH before entering. **Nothing here was
read from the bundled example.** Imperial throughout (the GUI's canonical units).

| Quantity | Value | Confidence / source to check |
|----------|-------|-----------------------------|
| Category / limit load factor | Normal, +3.8 / −1.52 | high (FAR 23.337 normal; POH) |
| Maximum take-off / landing weight | 3,800 lb | high (210L/M; TCDS 3A21) |
| Typical empty weight | ≈ 2,200–2,300 lb | medium (POH sample) |
| Seats | 6 | high |
| Usable fuel | 89 US gal (≈ 534 lb) | medium — 90 gal total on late 210L/M; earlier 65 gal |
| Wing span | 36 ft 9 in (36.75 ft) | high (cantilever wing, 1967 on) |
| Wing area | 175 ft² | high |
| Mean chord (area / span) | 4.76 ft = 57.1 in | derived |
| Root / tip chord, taper | owner to source | low — the cantilever 210 wing is tapered outboard; chords not in the TCDS |
| Airfoil | NACA 2412 / 2412 (mod) family | medium |
| Overall length | 28 ft 2 in | high |
| Height | 9 ft 8 in | high |
| Horizontal tail span / area | owner to source | low |
| Engine | Continental IO-520-L, 300 hp take-off (5 min) @ 2,850 rpm, 285 hp max continuous @ 2,700 rpm | high (TCDS) |
| Engine dry weight | ≈ 470 lb | medium |
| Propeller | McCauley 3-blade constant-speed, ≈ 80–82 in diameter | medium — TCDS lists the approved models |
| V_NE | 200 KIAS (210L) | medium — check POH; earlier models lower |
| V_NO | 167 KIAS | medium |
| V_A at 3,800 lb | 130 KIAS | medium |
| V_FE | 140 KIAS (10°), 115 KIAS (full) | medium |
| V_S1 (flaps up, 3,800 lb) | ≈ 66 KCAS | medium |
| V_S0 (flaps down) | ≈ 57 KCAS | medium |
| Landing gear | retractable tricycle; main-gear track ≈ 9 ft? | low — track to source |
| Tyre sizes | main 6.00-6, nose 5.00-5 | medium |

The GUI asks for several things no public source states (CLmax values, tail coefficients,
gear stroke and tyre deflection, mass-item breakdown). These are **engineering estimates**
and are recorded in the *Estimates* section below as they are made, with the basis, so the
model's provenance is complete.

## Estimates made during the build

| Field | Value entered | Basis |
|-------|---------------|-------|
| Datum | front face of firewall (POH datum), X positive aft | so POH CG limits can be typed directly |
| Wing LE station | FS 28 in, straight unswept LE | places the 3,800-lb CG range (≈ 39–47 in) at ~19–33 % MAC; cantilever 210 wing has a straight LE, taper on the TE |
| Wing root / tip chord | 68 in / 46 in (taper 0.68) | sized to the public 175 ft² at 441 in span; AR 7.7 checks |
| Wing strip count | 20 | Appendix A convention |
| Wing LRA / spars | 0.40 c; spars 0.20 c / 0.60 c | typical Cessna two-spar box; LRA midway |
| Wing side-of-body | BL 21 in | half cabin width ≈ 42 in |
| Parametric wing | S 174.6 ft², AR 7.7, λ 0.68, dihedral 1.5°, sweep 0, LE root X 28, root WL 96, datum X 0, h-tail Z −36 (offset from root WL) | matches the polylines; dihedral / waterlines estimated |
| Fuselage outline | 6 sections X −40 … 298 in (338 in overall), cabin 42 × 52 in, tail post 10 × 14 in, Z centre 68 → 78 | public overall length; cabin width from the 6-seat cabin; tapers estimated |
| H-tail (SELECT) | ST 40 ft², span 156 in, ARHT 4.2, elevator 16 ft² (14 aft / 2 fwd of hinge), travel +15/−25°, dα/dδe 0.5, it 0°, AW 4.98/rad, αL0 −3.5° (cruise/enroute) / −10° (landing), xt25 255, xt50 265 | span ≈ 13 ft public; areas, travels and stations estimated from 182/210-class tails; xt25 gives a tail arm ≈ 212 in |
| V-tail (SELECT) | SV 18 ft², span 65 in, ARVT 1.6, MAC 40 in, rudder 7 ft² (6.3 aft / 0.7 fwd), ±24°, EFV 1.0, IZZ 0 (computed), xv25 262, xv50 272 | estimates; swept fin with dorsal |
| Airplane length | 338 in | 28 ft 2 in public |

## Findings log

| ID | Page | Did | Saw | Expected | Class | Disposition |
|----|------|-----|-----|----------|-------|-------------|
| C210-1 | Geometry | Entered the `wing` LE/TE polylines, then reached the parametric block | Wing area, aspect ratio, taper, LE sweep, LE root X all **0.0**, to be typed by hand | The five scalars the polylines determine to be **seeded from the surface and overridable** — the GR-GEOM-3 ruling, and what the main GUI already does (`app/views/configuration_layout.py:117`, `wing_layout_from_surface`). The loads path is unaffected (STRSPEED/LGFACTOR/FLTLOADS read the surface), but the `configuration` module's own planform/stability/gear conditions read the parametric copy, so the two front-ends give one project two behaviours (OG-4/G8 class). | c | backlog; fix is the existing helper called from the generic renderer's Geometry page |
| C210-2 | Geometry | Parametric block offers `fuselage_length` as an input | It is overwritten from the fuselage outline on every run (`derived_geometry.sync_geometry_derived`) once sections exist; the registry row says "summarised … when entered" but the widget gives no sign | Shown read-only / marked derived once an outline exists, like `fuselage_width`/`height` (which the registry already marks derived) | c | backlog, with C210-1 |
| C210-3 | Geometry (empennage) | Reached SELECT's h-tail / v-tail block | `htail.aspect_ratio_wing`, `vtail.wing_span_in` and `vtail.gross_weight_lb` asked for again — already determined by the parametric wing / the `wing` polylines / the Weight page's MTOW | One owner per quantity (GR-INPUT-2, the field-ownership registry): these rows seeded or display-only with the governing value shown. `gross_weight_lb` is registered `governs=True` (G-14 review N1 instance 1), so today the copy typed *here* is what SELECT reads — a user who later changes MTOW on the Weight page changes nothing in SELECT. Owner's observation on reaching the v-tail block: "we again have the wing span, and airplane weight data — gross weight and Izz — that all should be in different sections" (`vtail.izz_slugft2` is a mass property: C210-6 placement as well) | c | backlog; same family as C210-1 (registry `derived_from` + renderer seeding) |
| C210-4 | Geometry (fuselage sections) | Typed a value into a cell of the sections table, pressed Enter / Tab | The cell **reverted to 0**; typing the same value a second time held. Reproduced on a second instance (port 8503): X 40 → lost → 40 held; Width 42 → lost, and still 0 after an unrelated rerun (Fuselage Length), so the first edit never reached the project, not a display lag. The persist path (`_cell_in` → `_set_entered`) takes the value correctly when called directly | One entry, one value. Every `st.data_editor` table on every oracle page is the same renderer (`_render_flat_table` / `render_curve`), so the whole GUI is affected; the beta review §6 records that the grid was never driven by mouse | **a** (external) | Narrowed with an instrumented `_render_flat_table`: a cell committed with **Tab** reaches the server and persists first time; a cell committed with **Enter** never triggers a rerun (the edit overlay stays open) and a following Tab discards it. Reproduced identically in a 15-line bare `st.data_editor` app (`scratchpad/repro_editor.py`, Streamlit 1.58.0, pandas 3.0.3) — **Streamlit's grid, not `form.py`**. Disposition: try the adjacent Streamlit versions and pin the one whose grid commits on Enter (0.7.2, **b**); until then the page should say "commit a cell with Tab" (**c**). Workaround in this build: Tab out of every cell |
| C210-5 | Geometry (empennage) | Elevator area, area aft of hinge and area ahead of hinge all asked for | No consistency check: SELECT reads `SE/ST` (`select.py:502`) and `(SE_fwd + 0.5·SE_aft)/(ST − SE_aft)` (`select.py:477`) independently, `configuration` reads `SE_aft/ST`; an SE ≠ aft + fwd entry is silently accepted and each formula takes its own view (as the original `.BAS` did) | SE derived as aft + fwd (one owner), or a warning when they disagree beyond a tolerance; same for the rudder triple | c | backlog, with C210-1/3 |
| C210-6 | Geometry (empennage) | Read the H-tail block | Wing aerodynamics asked for under **Htail**: `wing_lift_slope_per_rad` (SELECT AW), `wing_zero_lift_{cruise,enroute,landing}_deg` (IW), `aspect_ratio_wing` (ARW). They live on `HTailInput` because SELECT consumes them there, and the oracle renderer groups widgets by dataclass record | Wing aero with the wing's inputs (the Aerodynamic Data page, beside CLmax and the less-tail coefficients). Placement-only (GR-INPUT-2): the field stays on its record; the renderer needs a registry display group | c | backlog; with C210-1 (the Geometry-page presentation family) |
| C210-7 | Geometry (wing polylines) | Typed the wing LE/TE corners into the empty polyline grids, filled the rest of the page | The page **crashed** in the results block: `TypeError: unsupported operand type(s) for -: 'str' and 'str'` at `wing_geometry.py:112` (`ytip - yroot`). Cause: an empty `DataFrame` has object-typed columns, the grid renders them as text, every typed corner came back as `'28'`, `'0'`… and `_to_imperial_kept` passed the strings through to the model | Numbers in, numbers stored. **Fixed in place** (blocking): curve frame built `dtype=float`; `_numeric` parses any text cell on the way in; guard `test_a_curve_typed_from_blank_is_numeric`; fragment `changes/oracle-curve-typed-from-blank.fixed.md` | **a** | fixed on `dev/v0.7.1` (tier S) — still counts toward the `a` tally that decides 0.8.0. Residual: `io.project_from_dict` accepts string corners unchanged (verified), so a file saved during the crash reloads with them; the fixed grid repairs them on the next Geometry render. Whether the loader should coerce/refuse is a **b** for 0.7.2 |

## Closing checks (after Landing Loads)

1. Save to disk → `projects/C210_new.project.json` exists; reload in the oracle GUI →
   every page re-runs to the same numbers (the PB review's bit-identity check, by hand).
2. Open in `app/Home.py` unchanged (G6) → Export & Report → wing and gear `FORCE`/`MOMENT`
   cards written in the consistent-unit channel, `ULT SF` stated per case.
3. Comparison with `examples/cessna_210.project.json` (first look at it): geometry, mass,
   speeds, and the wing root bending at the governing case — differences explained by
   input provenance, not by the GUI.
4. Findings triage: every `a` → issue; every `b` → 0.7.2 list; every `c` → backlog row.
   The count of `a` decides whether 0.8.0 is repurposed.
