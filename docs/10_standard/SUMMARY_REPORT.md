# Summary Report — document standard

The authoritative specification for the **consolidated loads summary report**
(Step G8, Export phase): what the document is, what it **shall** contain, what it
**shall not** contain, and how its content is marked. The implementation plan is
[`../30_future/05_step_g8_summary_report_plan.md`](../30_future/05_step_g8_summary_report_plan.md);
this file is the standard the implementation is judged against and is the one to
update when the report's content rules change.

Keyword convention (RFC 2119 sense, as used throughout `10_standard/`):
**SHALL** = mandatory, a violation is a `[CRITICAL]` review finding;
**SHOULD** = strongly expected, deviation requires a stated reason;
**MAY** = optional.

---

## 1. Purpose and audience

The report is the **controlling document of a loads deliverable**. Its reader is a
**structural analyst** who did not run the analysis and who will size airframe
structure from it. The report SHALL be sufficient, on its own, for that reader to:

1. confirm the airplane analysed is the airplane they were expecting (§4.2);
2. see the flight envelope and the design conditions the loads come from (§4.3, §4.4);
3. read every governing ULTIMATE load, with its safety factor, and know **where**
   on the structure it acts (§4.5);
4. know exactly what the analysis does **not** cover, and how much to trust it (§4.6);
5. locate and correctly interpret the companion data files that carry the full
   distributions (§4.7).

The report is **not** a certification document, **not** a stress report, and
**not** a substitute for the analyst's own judgement. It states this plainly in
its own text (§4.6).

---

## 2. Document identity

- **Format.** The report SHALL be produced as LaTeX source (`.tex`) and SHALL be
  compiled to PDF when a TeX engine is available. The `.tex` is the primary
  artifact and is always delivered; the PDF is the reading copy.
- **Self-containment.** The `.tex` SHALL depend only on packages available in a
  standard TeX distribution, and SHALL NOT reference external image files —
  figures are generated as pgfplots/TikZ source inside the document.
- **Determinism.** Two renders of the same project **at the same unit selection**
  SHALL be byte-identical (the unit system is an input to the render, like the
  project itself). Any
  time-varying value (a generation timestamp) SHALL be supplied by the caller, not
  read from the clock inside the renderer.
- **Companionship.** The report SHALL be delivered inside the export bundle
  alongside the data files it references, never as a lone attachment.

---

## 3. Content rules that apply to the whole document

These are the rules a reviewer checks on **every** page.

### 3.1 Load basis and marking

- Every load figure in the report SHALL be **ULTIMATE**. The report SHALL NOT
  contain a bare limit load anywhere, including in figures, captions and examples.
  (The per-module *analysis* pages in the GUI may show LIMIT; the report is a
  deliverable and MAY NOT.)
- Every load quantity SHALL carry the `-ULT` marker in its units string
  (`lbs-ULT`, `ft-lb-ULT`, `lb-in-ULT`, `lb/in^2-ULT`).
- Every load case SHALL state its **safety factor** in an `SF` column or an `SF=`
  marker. A case already at ultimate is marked `ULT SF=1.0` — never "limit".
- Non-load quantities (weights, lengths, areas, inertias, speeds, angles, and the
  dimensionless load factors) SHALL carry plain units and no `-ULT` marker, and
  SHALL NOT be scaled. A load factor is limit and dimensionless; saying otherwise
  is an error.
- The title page and §4.6 SHALL both state the basis in words: *"All loads are
  ULTIMATE (= limit × SF); safety factor is stated per case; load factors are
  limit."*

### 3.2 Traceability

- Every **load** SHALL be attributable to a **case ID** that also appears in the
  companion case-index CSV and in the sbeam BDF cards. IDs SHALL NOT be
  re-minted, re-ordered or renumbered for presentation.
- Every **condition** SHALL cite its FAR reference (e.g. `23.337`, `23.427(a)`).
- Every **input** table SHALL name the page or slice that owns the value, so a
  wrong number is traceable to one screen.
- Every **equation source** referenced in the text SHALL cite Reference 1 by page,
  or the CFR by section — consistent with
  [`../20_theory/00_theory_sources.md`](../20_theory/00_theory_sources.md).

### 3.3 Axes, signs and stations

- Every **torsion** SHALL name the axis it is taken about. Wing torsion SHALL
  state the loads reference axis (LRA) as a % chord.
- Every **moment** SHALL state its sign convention. The preserved suite
  conventions SHALL be repeated where they apply: engine-mount reaction torque is
  reported **negative**; "clockwise from the pilot's view is positive" for rotor
  RPM and stoppage torque.
- Every **maximum** SHALL be accompanied by the station (span station, body
  station, or component location) at which it occurs. A maximum without a location
  is not usable for sizing and SHALL NOT be reported alone.
- Envelopes SHALL be reported **two-sided** (maximum *and* minimum at each
  station). A single max-magnitude trace hides the opposite-sign extreme and SHALL
  NOT be used.

### 3.4 Absence and uncertainty

- A section whose inputs are absent SHALL say so explicitly ("not analysed — no
  landing-gear inputs in this project"). It SHALL NOT be silently omitted, and it
  SHALL NOT render an empty table or an empty axis.
- Any figure derived from a default or approximated input SHALL be flagged as such
  at the point of use (e.g. an approximate gust-alleviation factor, or the Ch 9
  inertia approximation in place of per-CG values).
- Any **filtered** export (a governing-set selection rather than the full set)
  SHALL be stated prominently, with the deselected case IDs listed. An analyst
  SHALL never receive a filtered set without being told.

### 3.5 Units

**The report SHALL be produced in the unit system the user selected.** It is not
fixed to the calc's internal Imperial units. The rule and its consequences:

- **Selection.** The unit system is the one the user chose: in the GUI, the
  sidebar **Imperial / SI** toggle; headless, the persisted `Project` unit-system
  field, overridden per-run by the CLI `--units imperial|si` flag. Absent any
  selection the default is **Imperial**, so an unspecified run reproduces today's
  output exactly.
- **Whole bundle, one system.** The selection governs **every deliverable** in the
  export bundle — the report, the load-case CSV, the span-load CSVs and the sbeam
  `FORCE`/`MOMENT` bulk-data cards — not the report alone. Mixing systems across
  files in one bundle is a `[CRITICAL]` finding: a BDF in newtons alongside a
  report in pounds will size structure wrongly and nothing in either file would
  show it.
- **Every file states its system.** The report states it on the title page (§4.1)
  and in the manifest (§4.7); each machine-readable companion states it in-band
  (a header comment for the BDF, a header row or column-header unit for a CSV).
  A deliverable whose unit system must be inferred from the numbers is
  non-conforming.
- **Markers convert with the unit.** In SI, loads carry the SI marker —
  `N-ULT`, `Nm-ULT`, `kPa-ULT` — exactly as Imperial carries `lbs-ULT`,
  `ft-lb-ULT`, `lb-in-ULT`, `lb/in^2-ULT`. "Limit vs. ultimate" remains a property
  of the units string (§3.1) in both systems.
- **Single system, no dual display.** A figure SHALL NOT be shown in one system
  with the other in parentheses. One unit per dimension throughout the document
  (no mixing `in` and `ft`, or `mm` and `m`, for the same quantity in adjacent
  tables).
- **Solver-deck exception (M4-20 D-19).** The rule above governs *the document*.
  The machine-readable **sbeam** companions (the `FORCE`/`MOMENT` bulk data and
  the span/chordwise CSVs that feed them) SHALL use a dimensionally **consistent**
  unit set, which in SI means moments in **`N·mm`** and stresses/pressures in
  **`MPa`** (= N/mm²) beside `N` forces and `mm` coordinates — not the `N·m` and
  `kPa` the report uses. Every derived unit in that set is its base units
  combined, so no card can be off by a decimal power. This is one system with two
  channels, never two systems: a deck carrying `N·m` against `mm` GRID
  coordinates is wrong by 1000× and nothing in the file would show it. Each file
  states its own set in-band, and the report's manifest (§4.7) SHALL name the
  deck's set where it lists the companions.
- **Aviation-standard exception.** Airspeed (**KEAS**) and altitude (**ft**) are
  aviation-standard and are **not** converted in either system, matching the GUI
  (`GUI_design.md §7`). Where they appear, the report SHALL state that they are
  aviation-standard units held in both systems, so a reader of an SI report does
  not mistake an unconverted speed for an oversight.
- **Conversion is presentation, not calc.** The internal calc and the stored
  `project.json` values stay canonical **Imperial** regardless of the selection
  (`PROJECT_GUIDE.md §"Units at the boundary"`); conversion happens once, at the
  render/export boundary, via `units.py`. The persisted unit-system field records
  a *preference*, never the units of the stored values. Consequently the oracles
  are untouched: an SI report is a converted view of the same LIMIT calc, and
  round-tripping Imperial → SI → Imperial SHALL be lossless to display precision.
- Units SHALL appear in the column header, not repeated in every cell.

---

## 4. Required structure

The report SHALL contain the following sections, in this order. Section numbering
in the document itself follows this list.

### 4.1 Title page and document control (required)

| Required | Content |
|----------|---------|
| ✔ | Project name; engineer; date; revision |
| ✔ | Checked-by / approved-by signature block (blank lines are acceptable; the block SHALL exist) |
| ✔ | Certification-basis badge: **FAR 23** *or* **Concept (C) — unverified extrapolation** |
| ✔ | Tool name and version; project `SCHEMA_VERSION` |
| ✔ | The one-line load-basis statement (§3.1) |
| ✔ | Unit system — the selection in force (§3.5), plus the note that airspeed (KEAS) and altitude (ft) are aviation-standard and unconverted |
| ✔ | Table of contents |
| MAY | Revision-history table; project description |

### 4.2 Input summary (required)

The airplane, in enough detail to confirm identity. SHALL include:

- **Configuration** — category; engine layout, count, designation and type
  (reciprocating / turboprop); occupants, seats and crew; any opt-in supersets in
  force (e.g. FAR 25 cases).
- **Geometry** — wing area, span, MAC, aspect ratio, taper, sweep, dihedral,
  incidence; horizontal- and vertical-tail area, arm and volume coefficient;
  control-surface chord fractions (elevator, rudder, aileron, flap, tab); landing-gear
  stations and track; fuselage length and maximum width/depth.
- **Weights and CG** — MTOW, empty, fuel and payload; the design weights used per
  CG case; forward and aft CG limits in both inches and %MAC; the CG travel; mass
  properties (Iyy, Izz) **with their provenance**.
- **Design speeds** — VS, VSF, VA, VC, VD, VF, and VMO/MMO where applicable; each
  with its FAR reference and whether it was user-specified or derived.
- **Aerodynamic data** — CLmax clean and flapped; lift-curve slopes; the CM set;
  and whether a fuselage pitching-moment contribution is enabled.

### 4.3 Envelope figures (required)

Three figures, each followed by a **corner-point table** — a plotted boundary
without its numeric corners is not sufficient:

1. **V-n diagram** — manoeuvre and stall boundaries, gust lines, flap envelope.
   Corner table: each design speed against n⁺ and n⁻, and which of gust or
   manoeuvre governs at each corner.
2. **Weight / CG envelope** — the loading-envelope polygon with forward and aft
   limits and every design CG case marked. Corner table: weight, CG in inches and
   %MAC.
3. **Speed / altitude envelope** — where a Mach limit applies; otherwise the
   section SHALL state that the airplane has no Mach-limited boundary rather than
   omitting the heading.

Figures SHALL be vector, SHALL use the document's fonts, and SHALL be legible in
greyscale (line style, not colour alone, distinguishes traces).

### 4.4 Conditions analysed and FAR coverage (required)

- **Case index** — every case ID produced by the run, mapped to its full
  definition: component, condition, CG case, speed, altitude, safety factor.
- **Export-scope statement** — full set or governing set (§3.4).
- **FAR coverage matrix** — each FAR 23 Subpart C regulation the suite addresses,
  classified as **covered** (with case count), **not applicable** (with the
  reason), or **not analysed** (inputs absent). "Not analysed" rows SHALL be
  visually distinct; this matrix is how a reviewer finds gaps, and burying them
  defeats the section.
- **Approved corrections** — every deliberate deviation from the source manual in
  force for this run, with its citation, per
  [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md).

### 4.5 Results summary (required)

Per component, the governing conditions with their ULTIMATE loads and safety
factors, plus a maxima block naming the station of each maximum (§3.3). The
following components SHALL each have a subsection, present or explicitly marked
"not analysed":

| Component | Required content |
|-----------|------------------|
| **Wing** | Governing conditions; maximum shear, bending and torsion with span stations; the torsion axis named as a % chord; two-sided envelopes |
| **Fuselage** | Governing conditions; maximum shear, bending and torsion with body stations; any closure caveat in force, stated verbatim |
| **Horizontal tail** | Balancing, manoeuvre, gust and unsymmetrical conditions; the chordwise load split |
| **Vertical tail** | Manoeuvre and gust conditions; the chordwise load split |
| **Control surfaces** | Aileron, flap and tab design pressures and hinge moments; the distribution model named and flagged as a standard simplified distribution |
| **Landing gear** | Reaction cases per gear, and the gear geometry they act on |
| **Engine mount** | Torque, thrust, side and gyroscopic cases including all sign combinations; sign conventions restated |

### 4.6 Methods and limitations (required)

The section that governs how much weight the analysis can bear. SHALL contain:

1. **Load basis** — ultimate, per-case safety factor, the governing regulation for
   the factor, and that load factors are limit.
2. **Certification basis** — the category; or, in concept mode, the caveat that
   results are an **unverified extrapolation** above the calibrated band, listing
   each specific applicability exceedance with its value and limit.
3. **Verification status** — which paths are locked to a printed oracle and to
   what tolerance, and which are closure-locked only because no printed oracle is
   in hand. This SHALL NOT be softened or generalised into a blanket claim of
   validation.
4. **Numerical basis** — that the implementation uses modern constants rather than
   the source program's rounded literals, and that agreement with printed figures
   is therefore tolerance-based.
5. **Approved corrections** — the deviations in force, with citations.
6. **Known limitations** — every open caveat affecting the exported numbers,
   including any unclosed moment balance, simplified distribution models,
   case-set gaps, and load cases the suite does not compute at all.
7. **Scope of this export** — full set or governing set, and what was excluded.
8. **Provenance** — tool version, schema version, project identity, generation
   timestamp.
9. **The standing disclaimer** — this is an initial-concept loads analysis, not a
   certified analysis.

The methods statement SHALL be generated from a single source shared with the
machine-readable exports, so the statement in the report and the statement stamped
into the CSV and BDF files cannot diverge.

### 4.7 Bundle manifest (required)

Every companion file delivered with the report: its name, what it contains, its
units, its sign and axis conventions, and which report section summarises it. A
distribution CSV referenced by the report SHALL NOT be listed without its torsion
axis and load basis.

The manifest SHALL open by stating the bundle's unit system once and asserting
that every listed file is in it (§3.5); a per-file units column that disagrees with
that statement is a conformance failure, not a footnote.

### 4.8 Optional content

The report **MAY** additionally contain: a revision-history table, a fleet /
similar-aircraft comparison, trim and static-margin plots, and a glossary. Optional
content SHALL NOT displace or interrupt the required sections.

---

## 5. Excluded content

The following SHALL NOT appear in the report. Each exclusion has a reason; the
reason is what a reviewer applies to a case not listed here.

| Excluded | Why |
|----------|-----|
| **Bare limit loads** | The deliverable is ultimate throughout; a limit number sitting in a deliverable will be used as if it were ultimate. |
| **Unmarked loads** (no `-ULT`, no `SF`) | Marking is what makes the basis unambiguous at the point of use. |
| **Full station-by-station distributions for every case** | They belong in the companion CSV/BDF files. Inlining them buries the governing cases in hundreds of pages and makes the document unreadable — the failure mode this standard exists to prevent. |
| **Raw input echo dumps** (whole-JSON listings) | §4.2 is a curated identity summary, not a serialization. A dump obscures the few numbers that matter. |
| **Stress, margin-of-safety, sizing or material content** | The report delivers loads. Sizing is the analyst's work and depends on inputs this tool does not hold; implying otherwise invites loads and margins to be confused. |
| **Certification claims or compliance findings** | The tool computes loads; it does not show compliance, and no output of it may read as if it does. |
| **Unverified figures presented as verified** | Concept-mode and closure-only results SHALL carry their caveat wherever they are read, not only in §4.6. |
| **Numbers recomputed inside the report** | Every figure SHALL come from the same pure calc path the rest of the suite uses. A report that computes its own values will eventually disagree with the exports it accompanies. |
| **Internal development artifacts** — backlog IDs, ticket references, TODOs, source-file paths, code identifiers | The reader is an analyst, not a maintainer. A limitation is described in engineering terms; the tracking ID stays in the repository. |
| **Placeholder, "TBD" or example content** | An unfilled field is stated as *not analysed* with its reason, never left as a placeholder that reads as a real value. |
| **Decorative content** — logos, colour-only encodings, marketing text | Adds no engineering information; colour-only encoding fails in greyscale print. |
| **Personally identifying content beyond the document-control block** | The control block is the sanctioned place for names. |

---

## 6. Conformance

A report conforms when all of the following hold. These map one-to-one onto the
Step G8 test suite (see the plan, §8):

- [ ] Every required section of §4 is present, or explicitly marked *not analysed*
      with a reason.
- [ ] No bare limit load; every load carries `-ULT` and a stated `SF`.
- [ ] Every load traces to a case ID that exists in the companion case index.
- [ ] Every condition cites a FAR reference.
- [ ] Every torsion names its axis; every maximum names its station; envelopes are
      two-sided.
- [ ] The FAR coverage matrix classifies every listed regulation, with
      "not analysed" rows visually distinct.
- [ ] The methods statement is generated from the shared source and matches the
      statement stamped into the CSV and BDF exports.
- [ ] Concept-mode and closure-only caveats appear wherever the affected figures
      are read, not only in the methods section.
- [ ] The export scope (full vs governing set) is stated, with exclusions listed.
- [ ] The report and every companion file in the bundle are in the **selected**
      unit system, each states that system in-band, and no figure is dual-displayed.
- [ ] Load markers match the system (`lbs-ULT`/`ft-lb-ULT` or `N-ULT`/`Nm-ULT`);
      KEAS and altitude are unconverted and said to be.
- [ ] Two renders of the same project at the same unit selection are byte-identical,
      and an Imperial → SI → Imperial round trip is lossless to display precision.
- [ ] No excluded content from §5 appears.

---

## 7. Related documents

- [`../30_future/05_step_g8_summary_report_plan.md`](../30_future/05_step_g8_summary_report_plan.md) — the implementation plan for this standard.
- [`../../CLAUDE.md`](../../CLAUDE.md) — the ultimate-load output rules this standard applies.
- [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md) — per-module inputs/outputs and FAR conditions feeding §4.4 and §4.5.
- [`../20_theory/00_theory_sources.md`](../20_theory/00_theory_sources.md) — oracle status wording quoted by §4.6.
- [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md) — the corrections listed by §4.4 and §4.6.
- [`GUI_design.md`](GUI_design.md) — the LIMIT-vs-ULTIMATE display rules for analysis pages (the exception this standard does not inherit).
