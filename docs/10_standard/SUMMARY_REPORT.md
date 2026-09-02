# Summary Report — document standard

The authoritative specification for the **consolidated loads summary report**
(Step G8, Export phase): what the document is, what it **shall** contain, what it
**shall not** contain, and how its content is marked. The implementation plan is
[`../40_history/13_step_g8_summary_report_plan.md`](../40_history/13_step_g8_summary_report_plan.md);
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
  standard TeX distribution, and SHALL NOT reference external **image** files —
  figures are generated as pgfplots/TikZ source inside the document. This is what
  keeps a figure deterministic, diffable, unit-testable as text, and vector in the
  document's own fonts; it is the property the rule exists to hold.
- **Data reference.** A report delivered as a **package** — its own directory or
  archive, carrying a manifest (§4.7) — **MAY** read plain-text data files from
  inside that package, so that a table or figure is drawn from the delivered data
  rather than restating it. Every such file SHALL appear in the manifest; every
  path SHALL be relative and SHALL stay inside the package root; every file SHALL
  be self-describing to §3.1 (units, `-ULT` marker, safety factor and its basis);
  and determinism SHALL hold for the whole package, not the `.tex` alone. A report
  delivered as a **standalone `.tex`** SHALL NOT reference any external file.
  *(Amended 2026-08-30, tier M, design note 44 OR-23/OR-26: the standard already
  required the report to travel alongside the data files it references — §1.5,
  §4.7, §5 and the Companionship clause below. Reading them makes the reference
  mechanical instead of editorial, so the document cannot misquote its own
  companion; the image prohibition and every property it protects are unchanged.)*
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

### 4.2.1 Axes and sign conventions (required — added 2026-08-10, design note 15)

A dedicated section, rendered between the input summary and the envelope
figures, stating the sign conventions of record **once, globally** — §3.3's
point-of-use rules stay in force beside it, not replaced by it. SHALL include:

- **Prose**: the airplane reference frame (+aft / +starboard / +up, right-handed,
  identity to the solver CID 0), the centreline-reflection rule for handed
  twins, the statement that attitude angles are not state variables of the
  analysis, and the two preserved suite sentences of §3.3 **verbatim**.
- **A conventions table**: quantity → positive physical sense → the
  `CONVENTIONS.md` section (or SC-decision) it restates. The table *cites* the
  charter; it never redefines it.
- **Three figures** (`sign_axes`, `sign_controls`, `sign_beams`): the frame and
  state signs on a three-view sketch (+α, +β, the moment senses), the
  control-surface and rotation senses, and the per-component shear/moment/
  torsion diagram conventions. These are **static inline TikZ** — they carry no
  project data, so they can never be "not analysed" — and follow every figure
  rule of §4.3 (vector, document fonts, greyscale).

Single source: `sloads/report/conventions_tex.py`, drift-guarded by
`tests/test_report_conventions.py` (`CONVENTIONS.md` §7 table).

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

**A tick SHALL be read, not decoded.** An axis SHALL print its values in fixed
notation with thousands separators, never under a shared `·10ⁿ` multiplier: a
reviewer signing a report should not have to multiply an altitude back out
(owner, 2026-09-01).

**A marker label SHALL NOT be written through the figure's own ink.** Labels sit
above their markers by convention; where that would cross a plotted line, a
reference line or another marker, the emitter SHALL place the label clear of
them. The placement SHALL be a rule evaluated against the figure's own geometry —
scored over the whole label, not one point of it — and SHALL NOT be a table of
per-figure offsets: an offset tuned on one project is silently wrong on the next,
and these figures are built for whatever project a reader loads. An uncrowded
label keeps its conventional position, so the placement reads as a convention
rather than as a fault.

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

### 4.5.1 Balanced free-free airframe cases (required — added 2026-08-10, decision D-R2)

The assembled full-span free-free model is the **primary** loads deliverable
(mission extension 2026-08-08); the per-component results of §4.5 are analysis
views cut out of it. It SHALL therefore have its own section, rendered after the
results summary, containing:

- **What the model is** — full span, aero and inertia together, free-free, and
  the statement that the deck's one determinate support exists so that its
  recovered reaction *is* the residual ("reactions ≈ 0" is the equilibrium
  proof, not a modelling convenience).
- **One row per assembled case**, carrying its load factor `Nz`, its **pre-closure**
  residuals as a fraction of `n·W` / `n·W·MAC`, the applied roll couple, and the
  closure relief (`Δn`, `Δn_y`, the yaw and roll accelerations). These SHALL be
  the same rows the deck and the Balanced Cases page render (§5's
  nothing-is-recomputed rule) — i.e. `export.balanced_deck.balanced_case_rows`.
- **The residual verdict, over the family the acceptances apply to** — the worst
  pre-closure residual SHALL be maximised over the judged family only
  (`balance.residual_gate_family`), with **force and pitch judged separately**
  against their own owners (`FORCE_RESIDUAL_ACCEPTANCE` 2.5 % of `n·W`,
  `RESIDUAL_GATE` 1 % of `n·W·MAC`) rather than a single `max()` against the
  tighter of the two. The exempt families SHALL be stated beside it with their
  count and their standing (`balance.residual_gate_exemptions`), and any clamped
  cases SHALL be stated as gated per case rather than silently dropped.
  A maximum over a filtered set is honest only if the filter is visible, and the
  unfiltered maximum is not a verdict on the deliverable: a ground case's
  pre-closure residual is the applied gear reaction in full (100 % by
  construction) and a 23.427(a) case's is the maneuver tail load (143.885 % on
  `ga6_normal`) — reporting either as a failed gate is the CR-C-2 defect. The
  sentence SHALL NOT attribute a cause it has not measured.
- **The handed twin pairs** — an asymmetric case ships as a starboard/port pair
  by reflection at the assembly; a reader shown one hand SHALL be told the other
  exists, and a symmetric set SHALL be stated as such.
- **The mass-case identity** — which payload case is which `MASSSET` in the
  exported CONM2 model, with the loading's own weight and CG and its ballast
  fraction, and every case the weight database **cannot** produce marked NOT
  EXPORTED with its reason. SIDs and labels SHALL come from the same mint the
  cards use (`export.mass_cards.massset_identity`).
- **Absence is content (§3.4)** — a project that assembles no balanced case
  keeps the section and states that the assembled deck is not part of the
  deliverable. The complementary record — which SELECT conditions did not
  assemble, and why — stays in §4.4 beside the case index.

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

**Item 6 is a completeness claim, and it SHALL be testable** (review F-R4, which
found four open caveats missing from a list that claimed to be all of them).
Standing limitations are declared with a stable **key** in
`report.methods._standing_limitations()` and the key set is pinned by test, so
opening or closing a caveat is a visible edit in the same commit. A caveat that
also travels **in band** — on a case's notes, a deck `$` header, a page — SHALL
be the owning module's constant quoted verbatim, never paraphrased here: one
modelling choice, one wording, or a reader who notices the difference cannot
tell which is current. A limitation that depends on the project's own inputs
(an assumed planform, a fallback closure, assumed spar stations) SHALL be
conditional, stating itself only where it applies.

### 4.7 Bundle manifest (required)

Every companion file delivered with the report: its name, what it contains, its
units, its sign and axis conventions, and which report section summarises it. A
distribution CSV referenced by the report SHALL NOT be listed without its torsion
axis and load basis.

Section references (here and anywhere else in the document) SHALL be built from
the numbering owner, `report.content.SECTIONS` / `section_ref()`, never written
as a literal `§N` — a reference that does not move when a section is inserted
above it is a reference to the wrong section (review F-R2).

The manifest SHALL open by stating the bundle's unit system once and asserting
that every listed file is in it (§3.5); a per-file units column that disagrees with
that statement is a conformance failure, not a footnote.

The manifest SHALL list **every** artifact the bundle carries, the assembled
free-free deck and the CONM2 mass model included (D-R2) — an artifact the
controlling document does not name travels without the basis statement the
manifest exists to give it. It SHALL NOT list a file the bundle does not
contain: a manifest naming an artifact that was never written sends the reader
looking for it.

Both of those SHALLs were already written here when the LRA beam model shipped
inside the bundle with no row (review CR-C-1) — the rule was never the problem;
nothing read the bundle. So the member list has a **single owner**,
`sloads/report/bundle.py`, which the Export page loops over instead of deciding
for itself, and `tests/test_bundle_manifest.py` holds the real namelist against
the rendered manifest **in both directions** on the fixture that exports every
channel. A row whose artifact can refuse to build (the LRA model, which refuses
a project missing a datum it must not guess) SHALL be gated on the artifact
building, not on its inputs existing — otherwise the second SHALL above is
broken by the fix to the first.

Each row's **basis** cell SHALL be pinned by its text, not merely by its
filename: the manifest declared the LIMIT-by-design inertia check "ULTIMATE"
through two reviews because the conformance test read row names and stopped
(CR-C-3). `MANIFEST_BASIS` in `tests/test_report_content.py` is that pin, and it
is exhaustive both ways.

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

A report conforms when all of the following hold. Each is held by a named test
(Step G8 shipped 2026-08-05; see
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)):

- [x] Every required section of §4 is present, or explicitly marked *not analysed*
      with a reason — `test_report_content.py::test_every_required_section_is_present`,
      `::test_every_component_subsection_is_present`,
      `::test_sections_degrade_rather_than_raise_on_an_empty_project`.
- [x] No bare limit load; every load carries `-ULT` and a stated `SF` —
      `test_report_content.py::test_every_load_column_is_ultimate_marked`,
      `test_report_latex.py::test_ultimate_markers_and_sf_columns_are_present`.
- [x] Every load traces to a case ID that exists in the companion case index —
      `test_report_content.py::test_case_index_states_a_safety_factor_for_every_case`
      (the report's index is built from the same `case_index_rows_from` the CSV is).
- [x] Every condition cites a FAR reference —
      `test_report_content.py::test_input_tables_carry_the_projects_values_and_name_their_owner`
      and the coverage matrix's own `test_far_coverage.py`.
- [x] Every torsion names its axis; every maximum names its station; envelopes are
      two-sided — `test_report_content.py::test_wing_maxima_are_two_sided_and_name_their_station_and_axis`.
- [x] The FAR coverage matrix classifies every listed regulation, with
      "not analysed" rows visually distinct —
      `test_far_coverage.py`, `test_report_latex.py::test_not_analysed_rows_are_visually_distinct_without_colour`.
- [x] Axes print fixed ticks with thousands separators, never a shared multiplier —
      `test_report_latex.py::test_the_axes_print_fixed_ticks_rather_than_a_shared_multiplier`.
- [x] A marker label is placed clear of the figure's lines and of the other
      markers, scored over the whole label, and an uncrowded one keeps its
      conventional position —
      `test_report_latex.py::test_a_marker_label_is_placed_off_the_line_it_sits_on`,
      `::test_a_long_label_is_scored_over_its_whole_length`,
      `::test_an_uncrowded_marker_label_still_sits_above_its_point`.
- [x] The methods statement is generated from the shared source and matches the
      statement stamped into the CSV and BDF exports —
      `test_methods_stamp.py::test_summary_report_carries_the_same_statement`.
- [x] Concept-mode and closure-only caveats appear wherever the affected figures
      are read, not only in the methods section —
      `test_report_latex.py::test_concept_caveat_appears_only_in_concept_fixtures`;
      the fuselage closure caveat is stated verbatim in §4's Fuselage subsection.
- [x] The export scope (full vs governing set) is stated, with exclusions listed —
      `test_report_content.py::test_deselected_cases_are_excluded_from_the_results_and_named_in_scope`.
- [x] The report and every companion file in the bundle are in the **selected**
      unit system, each states that system in-band, and no figure is dual-displayed —
      `test_report_content.py::test_manifest_states_one_system_for_the_whole_bundle`,
      `test_deliverable_units.py` for the companions.
- [x] Load markers match the system (`lbs-ULT`/`ft-lb-ULT` or `N-ULT`/`Nm-ULT`);
      KEAS and altitude are unconverted and said to be —
      `test_report_content.py::test_si_report_carries_si_markers_and_converts_the_loads`,
      `::test_speeds_and_altitudes_are_not_converted_in_si`,
      `::test_geometry_areas_and_lengths_convert_with_their_labels_in_si`.
- [x] A standalone `.tex` references no external file; a packaged report
      references only manifest-listed, relative, in-package data files (§2 *Data
      reference*) — `test_report_latex.py` for the standalone summary report,
      the oracle report's package gates for the packaged case.
- [x] Two renders of the same project at the same unit selection are byte-identical,
      and an Imperial → SI → Imperial round trip is lossless to display precision —
      `test_report_latex.py::test_two_renders_are_byte_identical`,
      `test_deliverable_units.py` (the round trip).
- [x] No excluded content from §5 appears —
      `test_report_content.py::test_no_internal_development_artifacts_in_the_document`.

### 6.1 Implementation notes (recorded when the standard was first met)

Three readings this standard left open, resolved while building against it:

- **Depth for discrete-case modules.** Landing gear and engine mount produce tens
  of reaction cases. §4.5 is met by reporting **two-sided extremes** per quantity,
  each naming its case and safety factor, with the full set in the case index and
  the module's load-case CSV — the same pointer-to-companions trade §5 makes for
  station-by-station distributions.
- **The derived gust velocities are tabulated, not plotted.** §4.3's third figure
  carries the Mach-limited equivalent airspeeds; the `Ude` taper above 20,000 ft
  is a velocity in fps and shares no axis with them, so it appears in that
  figure's corner table instead. Plotting both would be a unit error drawn as a
  picture.
- **Emphasis is weight, never colour.** "Not analysed" rows and figure traces are
  distinguished by bold and by line style respectively, per §4.3's greyscale rule.

---

## 7. Related documents

- [`../40_history/13_step_g8_summary_report_plan.md`](../40_history/13_step_g8_summary_report_plan.md) — the implementation plan for this standard.
- [`../../CLAUDE.md`](../../CLAUDE.md) — the ultimate-load output rules this standard applies.
- [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md) — per-module inputs/outputs and FAR conditions feeding §4.4 and §4.5.
- [`../20_theory/00_theory_sources.md`](../20_theory/00_theory_sources.md) — oracle status wording quoted by §4.6.
- [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md) — the corrections listed by §4.4 and §4.6.
- [`GUI_design.md`](GUI_design.md) — the LIMIT-vs-ULTIMATE display rules for analysis pages (the exception this standard does not inherit).
