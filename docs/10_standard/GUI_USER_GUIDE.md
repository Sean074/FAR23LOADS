# GUI User Guide

A short, task-oriented guide to driving the loads suite through its Streamlit
GUI: the workflow phases, what you enter on each page, how one page *seeds* the
next, how to read the results (especially **LIMIT vs. ULTIMATE**), and one
end-to-end walkthrough of the bundled `ga6_normal` example with hand-checkable
numbers.

> **Naming note.** This guide is written brand-neutral and refers to "the app"
> or "the suite." A planned rename (backlog M3-1) will settle the product name,
> CLI command, and import package; when it lands, the few command examples here
> get a find/replace pass. Nothing about the workflow below changes.

For the *why* behind the design, see
[`GUI_design.md`](GUI_design.md) (navigation model, page anatomy, the
unit-boundary input pattern). For every input field's type/units/default, see
the generated [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

---

## 1. What the tool computes

The suite computes the structural **design loads** a small aircraft must sustain
under **14 CFR Part 23, Subpart C** (flight, control-surface, ground, and
engine-mount loads). It is a modern replication of the FAR23 LOADS programs, and
in **concept mode** it generalizes beyond the GA caps to size an early-concept
airframe and hand its per-component loads to a downstream structural tool.

You build up **one project** (`project.json`) page by page. Each page owns a
slice of the input, runs its calculation, and stores results back into the same
project — so the whole airplane travels as a single reloadable file.

### The one rule to internalize first: LIMIT vs. ULTIMATE

- **LIMIT load** — the highest load expected in service. The suite's *internal
  math* runs in limit loads (that is what the manual's oracle figures are).
- **ULTIMATE load** — limit × a **factor of safety** (default **1.5**, per
  14 CFR 23.303). This is what structure is actually sized to.

**Every deliverable is ULTIMATE.** The load-case CSV, the exported sizing cards,
and the Review/Export consolidation pages all report ultimate loads. You can
tell at a glance because **the unit string carries the marker**:

| You see | It means |
|---|---|
| `lbs-ULT`, `N-ULT` | an **ultimate** force |
| `ft-lb-ULT`, `Nm-ULT`, `lb-in-ULT` | an **ultimate** moment / torque |
| `psi-ULT`, `lb/in^2-ULT` | an **ultimate** design pressure |
| plain `lbs`, `ft-lb`, `in`, `deg`, `kt` | a **limit** load, *or* a non-load quantity (geometry, weight, speed, load factor) |
| `SF=1.5` (or `SF=1.0`) | the factor of safety applied to that case |

**Exception — per-module analysis pages may show LIMIT.** A single module's own
analysis page (e.g. Flap Loads, Tab Loads, One Engine Out) may show the
oracle-traceable **LIMIT** numbers so you can cross-check them against the
manual. Those pages are explicitly captioned `LIMIT` and point you to the
ultimate deliverables. Everything that is exported or consolidated is ultimate.

> Non-load quantities are **never** amplified: weights, inertias, areas, speeds,
> angles, and the dimensionless load factors *n* stay as-is. Only forces,
> moments, and pressures get the ×1.5.

---

## 2. The workflow: phases and pages

The left sidebar is built from the workflow graph, so page order is the analysis
order. There are seven phases:

| Phase | Pages | What happens |
|---|---|---|
| **Start** | Project Dashboard · Project JSON Editor | Load/save a project; see completeness. |
| **Develop V-n diagram** | Geometry · Weight & Mass Properties · Aerodynamic Data · Structural Speeds · Flight Envelope (V-n) | Define the airplane and build its flight envelope. |
| **Flight loads** | Wing Loads · Fuselage Loads · Tail Loads | Distribute the balanced flight loads onto the structure. |
| **Other loads** | Aileron · Flap · Tab · Engine Mount · One Engine Out | Control-surface and engine-mount loads. |
| **Landing loads** | Landing Loads | Ground/landing gear loads. |
| **Load-case plotting** | Loads Plots · Aircraft Comparison | Visualize the envelope and load cases. |
| **Export** | Results Review · Export & Report | Consolidate and export the ultimate deliverables. |

**The Dashboard is your map.** It shows which slices are present and which pages
are ready to run (a page is "ready" once the slices it *requires* exist). Work
top-to-bottom and the requirements fall into place.

---

## 3. The seed chain (why order matters)

The suite is **single-source**: a quantity is entered on exactly one page and
every downstream page reads it read-only. You will see fields shown greyed-out /
read-only on later pages — that is deliberate, not a bug. The important chains:

- **Geometry is the root.** The wing planform you draw on **Geometry** seeds the
  wing area *S*, mean aerodynamic chord *MAC*, and the 25%-MAC station used by
  the weight envelope, the design speeds, the flight envelope, and the wing/tail
  load distributions. Fuselage and empennage geometry (including elevator/rudder)
  are also entered here once.
- **Maximum lift coefficient is entered once**, on **Aerodynamic Data**
  (`clmax_clean` / `clmax_flap`). Stall speeds *VS*/*VSF* are *derived* from it —
  you never type a stall speed.
- **Design speeds and limit load factors** come from **Structural Speeds**
  (STRSPEED). The **Flight Envelope**, aileron, flap, and tab pages all read
  *VA/VC/VD/VF* from there.
- **Weight/CG cases** are entered once on the weight pages and flow into the
  flight-envelope balancing.

Practical consequence: **do Geometry → Weight → Aerodynamic Data → Structural
Speeds → Flight Envelope in that order.** After that, the Flight/Other/Landing
pages can be run in any order.

---

## 4. What to enter where

A compact tour. Field-level detail (type, units, default, owning page) is in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md); this is the orientation.

**Geometry.** The wing (and other lifting-surface) planforms as leading/trailing
edge point lists, the parametric fuselage/wing/tail/gear layout, the fuselage
station-area outline, and the single-source empennage (h-tail + v-tail +
elevator + rudder). Everything geometric starts here.

**Weight & Mass Properties.** The mission inputs for the statistical weight
estimate (seats, crew, power, hours, baggage), the itemized mass database
(each item's weight and station), the structural CG-envelope limits (percent
MAC), and the named weight/CG loading cases.

**Aerodynamic Data.** The airplane-less-tail aero-coefficient polynomials
(cruise and, optionally, flaps-down), the maximum lift coefficients, and the
per-surface spanwise airload inputs (section lift slope, twist).

**Structural Speeds.** The category (**N/U/A** for FAR 23, or **C** for
concept), design weight, sea-level max speed *VH*, and your chosen *VA/VC/VD/VF*
(each verified against — and raised to — its FAR minimum). Optional Subpart-G
placard targets (VNE/VNO/VFE) are advisory only.

**Flight Envelope (V-n).** The tail center-of-pressure stations, reference Mach,
and the altitude list. Runs FLTLOADS: builds the V-n diagram and the balancing
tail loads at every CG case and altitude.

**Flight-loads pages (Wing / Fuselage / Tail).** The mass distributions and
critical conditions that turn the envelope into distributed structural loads.

**Other-loads pages (Aileron / Flap / Tab / Engine Mount / One Engine Out).**
Each control surface's own geometry and deflection limits; the engine-mount
page takes the engine/propeller weights, CG, power/torque, and rotor data.

**Landing Loads.** Gear geometry (axle positions, strut stroke, tire/hub sizes)
and the landing load factor.

**Export & Report.** Writes the ultimate load-case CSV and the structural-sizing
cards, with a methods/limitations statement stamped in. Its **Summary report**
section renders the controlling document of the whole deliverable — the airplane,
its envelope figures, the FAR coverage matrix, and every governing ultimate load
with the safety factor and station it acts at. The LaTeX `.tex` always downloads;
press **Compile PDF** to typeset it here when a TeX engine (`tectonic`,
`latexmk` or `pdflatex`) is installed. Both, plus `METHODS.txt` and every CSV/BDF,
go in the bundle `.zip`. Headless, the same document comes from
`python cli.py --report out.pdf project.json`.

---

## 5. Reading the results

Every module renders results as **load cases** — one row per structural
condition — with labelled outputs. On any consolidated or exported view:

1. **Check the units string** for `-ULT`. If it is there, the number is
   ultimate and ready for sizing. If a page shows a plain unit, confirm the page
   is a per-module *analysis* page (captioned `LIMIT`) — do not export those
   numbers as-is.
2. **Read the `SF` marker.** `SF=1.5` is the default. `SF=1.0` means the value
   is *already* ultimate (or an inherently-ultimate quantity) — it is still an
   ultimate deliverable, not a limit load.
3. **Load factors, speeds, angles, weights** have no `-ULT` — they are
   dimensionless or non-load and are reported directly.

---

## 6. End-to-end walkthrough: `ga6_normal`

The bundled `examples/ga6_normal.project.json` is the manual's **Appendix A**
airplane — a 6-place GA single (the Cessna-210-class example McMaster works
through). Loading it and stepping the pages reproduces the manual's printed
figures. Below are **four hand-checkable numbers** that trace the seed chain
from weight through to the flight envelope; each is a currently-passing
regression oracle (see
[`../40_history/01_verification_baseline_0.2.0.md`](../40_history/01_verification_baseline_0.2.0.md)
for the full table and page citations).

**Load it:**

```bash
# GUI
.venv/bin/streamlit run app/Home.py      # then Start → Project JSON Editor → load examples/ga6_normal.project.json

# or one module from the CLI
.venv/bin/python cli.py engine examples/ga6_normal.project.json
```

**Checkpoint 1 — Weight & Mass Properties (WTESTIMA).**
Max take-off weight = **3468 lb**, empty weight = **2150 lb**, empty/take-off
ratio = **0.62**. *(Manual Appendix A p133.)*

**Checkpoint 2 — Weight & Mass Properties (WTONECG, aft-gross loading).**
CG fuselage station XBAR = **84.99936 in**; pitch inertia IYY =
**2058.209 slug-ft²**. *(Appendix A p136.)* These are geometry/inertia — note
**no `-ULT`**.

**Checkpoint 3 — Structural Speeds (STRSPEED).**
Limit positive load factor *n₊* = **3.8**, limit negative *n₋* = **−1.52**;
maneuver speed VA = **121.3 KEAS**, cruise VC = **170 KEAS**, dive VD =
**212.5 KEAS**. The load factor is dimensionless; the speeds are KEAS — again no
`-ULT`. *(Appendix A V-n table.)*

**Checkpoint 4 — Flight Envelope (FLTLOADS), CG1 aft-gross.**
The **MAN A** corner (positive maneuver at VA) balances to
**V = 121.3 KEAS, NZ = 3.80, α = 12.75°** — VA and *n₊* from Checkpoints 3
carried straight into the envelope corner, confirming the seed chain end-to-end.
*(Appendix A p179–180.)*

If those four match on your machine, the input path is wired correctly. The
**Export** phase then applies the ×1.5 factor of safety at the boundary, so the
same 3.80-g maneuver appears in the exported CSV as an **ultimate** case
(`SF=1.5`, loads in `lbs-ULT` / `ft-lb-ULT`).

> Because the math is modernized (real `math.pi`, not the BASIC's `3.1416`), the
> manual's printed figures are **±0.1% regression oracles**, not exact — the
> suite asserts `math.isclose(..., rel_tol=1e-3)` against them.

---

## 7. Concept mode & caveats

Set the Structural Speeds **category to `C`** to enter concept mode: the GA-only
caps (the 23.337 maneuver-load-factor limit, the 12,500-lb / GA-seat limits) are
bypassed, you provide explicit design load factors, and the statistical weight
estimate becomes a sanity figure rather than the source of truth (weights come
straight from the itemized mass database). Concept mode is a **superset** — on
GA inputs it reduces exactly to the oracle-locked FAR 23 path.

**Dive-speed basis (concept only).** In category `C` the Design Speeds tab adds a
**Dive speed basis** choice, because 14 CFR 25.335(b) offers two routes and the
regulation joins them with an *or*:

- **Speed ratio (VD ≥ 1.25·VC)** — the default, and what the suite has always
  done. `VC/MC ≤ 0.8·VD/MD` is the same statement written the other way round.
- **Mach margin (MD ≥ MC + margin)** — your chosen VD is honoured as long as MD
  clears MC by the margin, and raised to meet it if not. Needs a shoulder
  altitude and a chosen VD. Use this when the ratio route would force a dive
  speed your configuration does not have (a regional jet at VC 310 kt is pushed
  to VD 387.5 kt by the ratio, MD 0.94 — a margin of +0.19, which no transport
  designs to).

The margin defaults to **0.07 M**. Entering less than that requires a written
**rational-analysis basis** and raises a standing warning: reducing below 0.07 M
needs significant justification — a rational analysis crediting automatic systems
(25.335(b)(2)) — and **represents a certification risk**. **0.05 M is an absolute
floor** the form will not go below. Whichever route you pick, the results state
that only the (b)(2) Mach term is evaluated: 25.335(b) wants the *greater of*
that margin and the (b)(1) upset criterion, which this suite does not compute, so
a clean margin here is not a compliance demonstration.

An optional **rough-air speed VB** (25.335(d)) can be entered; it is checked for
ordering against VC and never changes a design speed or a load.

Some concept-mode results carry caveats the UI surfaces (e.g. the fuselage
body-load moment-closure note, and the fixed body-rate stand-in for the 25.371
gyro case). The Export deliverables stamp a methods/limitations statement so a
downstream sizing tool inherits the same caveats. Read them before trusting an
out-of-band result.

---

## 8. Bundled examples

Load any of these from **Start → Project JSON Editor** (or `New from example`):

| Example | Category | Runs |
|---|---|---|
| `ga6_normal` | FAR 23 Normal (Appendix A) | full workflow, all six phases |
| `cessna_210` | FAR 23 Normal | full workflow |
| `concept_regional_jet` | concept jet (T-tail, Part 25 supplement on, **25.335(b) Mach-margin dive speed**) | full workflow |
| `dhc8_dash8` | concept twin-turboprop (one-engine-out) | full workflow |
| `atr42_100` | concept twin-turboprop (one-engine-out) | full workflow |
| `concept_heavy` | **minimal concept core** | V-n → Flight Envelope only |

`concept_heavy` is deliberately minimal — it carries just the weight / geometry /
speeds / aero / flight-loads / wing-mass core to demonstrate the concept V-n
path, and has no engine, control-surface, fuselage-mass or landing data, so it
stops cleanly at the Flight Envelope rather than running the downstream loads
pages. The other five are authored to run end-to-end without a red error.

## 9. Where to go deeper

- **Field reference:** [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) — every input
  field's type, units, default, owning page, and consuming modules.
- **Design rationale:** [`GUI_design.md`](GUI_design.md) — navigation model and
  page conventions.
- **What each module computes:** [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md).
- **Equation/oracle sources:** [`../20_theory/00_theory_sources.md`](../20_theory/00_theory_sources.md).
- **The exact oracle figures:** [`../40_history/01_verification_baseline_0.2.0.md`](../40_history/01_verification_baseline_0.2.0.md).
