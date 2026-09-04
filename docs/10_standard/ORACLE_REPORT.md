# The oracle technical report — content standard

The rules the **oracle technical report** conforms to, section by section, as
each is agreed. Created under design note 44 OR-9 and grown with each OR-8
iteration: chat is not a register, so every agreement lands here with the test
that guards it.

**Scope.** The report generated from the oracle GUI (`oracle_app`), covering the
analysis the original McMaster FAR 23 LOADS suite performs and nothing this
replication added. It is not `app/`'s summary report (`SUMMARY_REPORT.md`) and
not the user guide.

**Inherited rules, by citation.** `SUMMARY_REPORT.md` §2 (document identity,
self-containment, the *Data reference* clause, determinism) and §3 (content
rules: ULT marking, absence, filtered exports, one unit system per bundle) apply
to this report **verbatim and are not restated here** (OR-5). Where this document
adds a rule, it is one those sections do not already carry.

Axes, signs, units channels and the ULT/SF contract are
[`CONVENTIONS.md`](CONVENTIONS.md)'s throughout.

---

## 1. The issue package

A report issue is a **package**, not a file: the document, the data behind every
table and plot, the definition it was built from, and a manifest — in one
directory that can be archived, signed, and reopened years later.

- The package directory **SHALL** be named from the report number and revision,
  never from the clock. A rebuild must land on the same directory, which a
  timestamped name makes impossible.
- The **working spec lives inside the package** as `report.json` (OR-28). One
  issue, one directory. Opening a package is resuming work, not reading history.
- `report.json` **SHALL NOT** be written by a build (OR-30). It records what a
  person typed. The as-built stamp — fingerprint, build timestamp, generator —
  belongs in `build.json`, which the builder owns.
- Rebuilding an issue **overwrites in place, silently**; bumping the revision
  **SHALL** produce a new directory beside the old, so an issued revision is
  never destroyed by continued work.
- A build **SHALL NOT** delete a file it did not write. `report.pdf` from a local
  compile lives in the package and is not the builder's to remove. It **SHALL**
  clear `data/` first, so a file left over from a build whose section has since
  been excluded cannot survive as a stray.
- Every member path **SHALL** be relative and stay inside the package root.

## 2. The manifest

`MANIFEST.txt` **SHALL** be a full `SUMMARY_REPORT.md` §4.7 manifest, not a list
of hashes (OR-35): per file, its contents, units, sign and axis conventions, and
the section that summarises it, under an opening statement of the package's unit
system, with section references built from the numbering owner and never written
as a literal section mark.

It **SHALL** be exhaustive in both directions — it lists every file the package
carries, including itself, and names nothing the package does not carry. Its own
hash cannot be inside it, so that row states as much rather than being omitted.

Both rules exist because of real defects: an artifact shipped inside a bundle
with no row at all (review CR-C-1), and a basis cell that called a LIMIT artifact
ULTIMATE through two reviews because the conformance test read row names and
stopped (review CR-C-3).

## 3. Sections

The section set is **derived, never listed**: the owner is
`sloads.workflow.oracle_steps()`, and a step is an analysis section **iff it
produces a result** (it has a `module`). An input-only step has nothing to report
and belongs to the input sections. Adding a module-backed step to the workflow
adds a section with no edit to the report code.

Numbering has one owner, `oracle_content.section_number`, derived from position.
Section references **SHALL** be built from it. A reference that does not move
when a section is inserted above it is a reference to the wrong section.

### 3.1 The section states

A section that is **deselected is not printed at all** — no heading, no reason,
and the sections after it renumber to close the gap. Numbering is by position
among the sections that *render*: numbering by workflow position would leave a
hole in the printed sequence and every reference after it would name the wrong
section.

> **Documented deviation (2026-08-30, owner's decision).** This reverses OR-19
> and departs from `SUMMARY_REPORT.md` §3.4, which this document otherwise
> inherits verbatim under OR-5, and whose stated purpose is that an analyst
> never receives a reduced document without being told. It is recorded here
> rather than by amending `SUMMARY_REPORT.md`, which governs a different
> document and is unchanged. The reasoning is that deselection is the reader's
> own act in this tool, so there is no second party to inform.

Of the sections that **do** print, the state says why it carries no analysis —
three states, kept apart because each names a different cause (OR-32):

| State | Means | Bold lead | Sentence |
|---|---|---|---|
| **Included** | the section carries its analysis | — | the analysis |
| **Not yet implemented** | the generator cannot build it yet | *Not yet implemented.* | This revision of the report generator does not yet produce this section. Nothing about this project or this issue is missing. |
| **Absent** | the inputs it needs are missing | *Not analysed.* | The inputs this section needs are not present in the project. |

No state's wording **SHALL** be produced by another's cause. Collapsing the two
would tell a reader their own data was incomplete when it was the generator that
was.

**The lead is part of the rule, not presentation.** It is printed in bold ahead
of the sentence and is what a reader skimming the document takes in, so two
states sharing one lead say the same thing twice however carefully the sentences
differ. The first build of this document gave each state a distinct sentence and
then printed all of them under a hard-coded *"Not analysed"* — absence's wording
— telling readers their inputs were missing when the generator was incomplete.
The guard therefore asserts the **rendered** lead, not the model's strings. The
sentences are capitalised: they follow the lead and a full stop.

**Precedence.** Deselection is decided first, because it is the state that stops
the section printing and there is then no reader to owe a reason to. Among the
states that print, *not yet implemented* outranks *absent*. When every section
is implemented that ordering stops mattering and *absent* is the only one left.

Selection is limited to analysis-body sections and the input echo. Front matter,
the governing-loads summary and methods & limitations are never selectable: they
carry the load basis and the traceability statements.

The cover carries identity and the approval record and nothing that has to be
read through. With the analysis basis and a thirteen-item list of unbuilt
sections on it, the signature block was pushed onto a second sheet, leaving the
approval record on a page carrying none of the document's identity — the one
page that must never travel alone.

## 3.2 Section 1: introduction, analysis basis, limitations

Section 1 carries the introduction prose, then two unnumbered subsections:
**Analysis basis** (§5) and **Limitations and scope**. Both appear in the
contents.

- The introduction prose and the limitations text are **the author's**. The GUI
  pre-fills each with the generator's default; from then on the spec carries what
  was typed, and a later change to a default **SHALL NOT** reword a report that
  has already been written. Each is a snapshot, deliberately: a signed issue must
  keep saying what it said when it was signed.
- The limitations default **SHALL** come from
  `sloads.report.methods.methods_statement` — the single owner of that statement
  across every export channel — so the report opens saying what the CSVs and the
  decks say. Its own banner is stripped; the subsection already carries the title.
- An empty field means *not yet edited*, not *empty section*: the renderer falls
  back to the same default, so a spec written before these fields existed still
  produces a complete document.

## 3.3 Section 2: Loads Configuration

Agreed 2026-08-30 (OR-8 iteration 2). Section 2 collects four analysis steps as
subsections of one numbered section: 2.1 Geometry, 2.2 Weight and Mass
Properties, 2.3 Structural Design Speeds, 2.4 Flight Envelope.

- **Grouping is declarative.** `oracle_content.SECTION_GROUPS` names the members;
  `section_plan` numbers the group at the top level and its members as `N.1`,
  `N.2`, ... Every step **SHALL** still have exactly one home, so G-OR-2 is
  unchanged. A group's members **SHALL** be contiguous in workflow order.
- **The document names its own sections.** `oracle_content.DOCUMENT_TITLES`
  maps step key to printed heading, and a heading **SHALL NOT** be taken from
  `WorkflowStep.title`: that is the oracle GUI's navigation label, written for a
  different audience, and renaming a nav item must not retitle a signed report.
- **2.1 states every lifting and control surface, one table each** (owner,
  2026-08-30): wing planform, horizontal tail and elevator, vertical tail and
  rudder, aileron, flap, and one table per trim tab. Each carries the surface's
  area, its planform figures, its tail arm stations where it has them, and its
  control deflections.
- **These are the first values read from the project rather than from a
  `ModuleResult`.** No module returns a control-surface area or a throw, so the
  only source is the definition the analysis was given. Echoing an input is not
  recomputation — OR-6 forbids re-deriving a value, not reporting one — but the
  section **SHALL** state that they are the configuration *as entered* and not
  analysis output, **once**, in its prose. The rows are declared as data
  (`oracle_sections._HTAIL_ROWS` and its siblings) so a renamed or dropped input
  field fails the suite rather than silently emptying a row.
- **A surface key SHALL NOT reach a heading.** `TabInput.surface` carries the
  analysis's own `"htail"`; the document says "horizontal tail", for the same
  reason `DOCUMENT_TITLES` exists one level up.
- **2.2 states the weight and CG cases analysed**, one row each: case name,
  role, weight, Xcg, Zcg and analysis. A note under it **SHALL** explain what
  role and analysis govern — which load families the case is carried into, and
  which of the landing analysis's three positional loadings a ground case
  supplies. A flight case has no role and prints a dash, never a blank cell.
  The analysis tags **SHALL** be printed in a declared order: `CgCase.analyses`
  is a set, and set iteration order is not a document property the determinism
  gates can rest on.
- **The CG-case table SHALL state Xcg in percent of MAC beside the station**,
  and **SHALL** state the relation it used. The entered CG limits are given in
  %MAC and the cases in stations, so a table that prints only the station makes
  every reader convert by hand against whichever XLEMAC and MAC they can find.
  Three rules:
  - The column **SHALL** come from `derived_geometry.mac_reference` and
    `station_to_pct_mac` — the one resolver and one relation the limit lines
    and the summary report's `% MAC` column already use (C210-13). This is a
    change of reference, not a derivation, and is the third and last source
    G-OR-3 admits in section 2.
  - The note **SHALL** print the relation both ways —
    `%MAC = 100 (X - XLEMAC) / MAC` and `X = XLEMAC + (%MAC / 100) MAC` — with
    the XLEMAC and MAC in use and whether they came from the typed override or
    the wing planform of 2.1. A percentage of MAC is not checkable without the
    pair behind it.
  - Where no reference resolves, the column **SHALL** print a dash and the note
    **SHALL** say why. `station_to_pct_mac` answers `0.0` on a degenerate MAC by
    contract, and a column of zeroes reads as a centre of gravity at the leading
    edge (OR-32).
- **2.2 carries the weight and centre-of-gravity envelope figure** (design note
  45 WE-8, built 2026-08-31 — the oracle's own p140, *"USEFUL LOAD ENVELOPE AND
  STRUCTURAL LIMITS"*). Five rules govern it:
  - It **SHALL** draw **both** loading edges — the discretionary items added
    most-forward first and most-aft first. Drawing one is not a partial figure
    but a misleading one: on the GA6 the forward edge never approaches a limit
    while the aft edge passes 2.2 in beyond the aft-gross station, so a reader
    takes containment from a figure that has not shown it. Both edges come from
    `weight_envelope.loading_envelope`, whose aft half `WTENV.BAS` computes and
    the port did not carry until note 45.
  - The structural limits **SHALL** be drawn as one **closed** envelope, and
    **SHALL** be omitted entirely when any corner is unentered rather than drawn
    with a side missing — a limit boundary with a gap in it reads as permission.
  - Every entered CG case **SHALL** be marked. Cases sharing a weight and
    station **SHALL** share one marker and state both names; the GA6's `CG3` and
    `fwd light` are the same loading, and two labels on one point are a smudge
    rather than information.
  - The plotted vertices **SHALL** be tabulated beside the figure, from WTENV's
    own `ModuleResult` (G-OR-3) rather than swept by the report. The table
    **SHALL NOT** name the item added at each vertex: the analysis does not
    carry it, and the note under the table says so instead of the report
    inferring it.
  - The figure **SHALL** have one owner shared with the summary report
    (`report.content.weight_cg_plot_data`, OR-7). The oracle report **SHALL NOT**
    grow a second builder for a figure the other document already draws.
- **Section 2 states no load in force or moment units.** Its load factors *are*
  loads — n is a limit load factor — but they are dimensionless and LIMIT, so no
  value in section 2 **SHALL** be scaled to ultimate or carry the `-ULT` marker,
  and no table **SHALL** state a safety factor. Values still pass through
  `report.render.to_ultimate` / `ultimate_units` rather than being formatted by
  hand, so the section never decides what a load is.
- **No table note SHALL claim that load factors are not loads** (owner,
  2026-08-30). An earlier draft carried exactly that under every table; it is
  wrong, and it was removed rather than reworded. Where a load factor is
  reported it **SHALL** be identified as LIMIT — the V-n figure captions and the
  corner table do this at point of use.
- **2.3 pairs each value with its regulation's floor.** A design speed or limit
  load factor **SHALL** be printed beside the FAR 23 minimum the module computed
  for it. No compliance verdict is printed: whether a value complies is the
  reviewer's finding, not the generator's. A paired table **SHALL NOT** print a
  `Units` column no row fills: a limit load factor is dimensionless, and a blank
  cell reads as a unit that went missing rather than one that does not exist.
  "g" is not that unit -- it names an acceleration the table does not state.
- **2.4 plots produced design points only.** The envelope boundary is the
  polyline through the cases FLTLOADS returned, one figure per loading and
  altitude block. `vn_diagram.build_vn_diagram` **SHALL NOT** be used: it is
  documented as an approximate Structural-Speeds sanity plot with a
  constant-CLmax stall boundary, which on the reference GA wing predicts n = 3.51
  where the analysis computes 3.80 — an 8% disagreement that would put the
  report's own design points off their own boundary. The subsection **SHALL**
  say that the boundary is curved between the plotted points. Gust cases are
  drawn as marked points, never as boundary vertices.
- **A V-n figure carries no caption of its own.** What a caption would say is
  the same for all of them — they differ only in loading — so the construction
  statement, and the LIMIT identification of the load factors with it, is made
  **once** in the subsection body above the figures, and the caption line
  carries the block name alone. Captions **SHALL** stay empty rather than the
  rule softening to "a caption states it if it has one" (owner, 2026-08-31).
- **2.4 opens with the speed and altitude envelope** (built 2026-08-31). The
  V-n diagrams are slices of that envelope at a stated altitude, so the
  envelope is drawn before its cuts. Four rules:
  - It **SHALL** run from **sea level** to the maximum operating altitude, not
    from the shoulder altitude. Each boundary is constant in equivalent
    airspeed below the shoulder and Mach-limited above it, and the kink at the
    shoulder is what the figure is for; MACHLIM tabulates only the Mach-limited
    half, and a figure starting where the table starts shows a boundary with no
    beginning.
  - The sub-shoulder segment **SHALL** be the shoulder row's own speed held
    constant, never a second evaluation of it — every speed plotted is a value
    MACHLIM returned (G-OR-3 through a figure).
  - **Vh SHALL be marked at sea level, not drawn as a line.** `speeds.vh_kt` is
    the maximum level-flight speed at sea level and the analysis carries no
    altitude variation of it; a full-height line would assert a boundary
    nothing computed. It is not a limit speed, and the caption says so.
  - The Mach-limited half **SHALL** be tabulated beside the figure from
    MACHLIM's own `ModuleResult`, with a note stating that the boundaries are
    constant in EAS below the first row's altitude.
- **The speed/altitude figure has one builder**,
  `report.content.speed_altitude_plot_data`, shared with the summary report
  (OR-7) — which is why the summary report's own speed/altitude figure now
  begins at sea level and marks Vh.
- **The case list belongs to the load-case section**, not here; 2.4 cross-refers
  to it through the numbering owner and renders "a section this issue does not
  carry" until it exists.
- **2.1 draws one planform figure per main surface** — wing, horizontal tail,
  vertical tail (OR-45's "its planform figures", built 2026-08-31). Each
  **SHALL** show the surface's entered leading- and trailing-edge polylines as a
  closed outline, with the control surfaces that live on it filled on top, and
  **SHALL** be drawn on equal axes: a swept tapered surface on independent axes
  is a different shape from the one the loads were computed for, which is the one
  thing the figure exists to show. Regions **SHALL** be distinguished by fill
  density, never by colour (`SUMMARY_REPORT.md` §4.3). The figures and the
  surfaces they are drawn for are declared together
  (`oracle_sections._PLANFORM_FIGURES`), both directions.
- **A planform figure SHALL be TikZ source, never an image file.**
  `SUMMARY_REPORT.md` §2 *Self-containment* forbids the report referencing an
  external image, and the 2026-08-30 *Data reference* amendment reaffirms the
  prohibition verbatim while opening only the plain-text data channel. A
  planform is a closed polygon, so the properties the rule protects —
  deterministic, diffable, unit-testable as text, vector in the document's own
  fonts — cost nothing to keep here.
- **A planform figure SHALL NOT draw a hinge line** while the analysis carries
  no hinge geometry. The suite holds a control surface's areas forward and aft
  of its hinge as scalars, from which `taildist` derives a chord *station* on the
  average chord (`CEAFTHL = (S_aft/S)·CAVE`); a line drawn from that would be an
  inference on a rectangle-equivalent, printed with the standing of entered
  geometry. The caption **SHALL** say the line is absent and why. It arrives with
  **#156** (band B4), which makes the hinge polyline an input and the two areas
  derived.
- **A region's area is the value tabulated beside it**, read from the same owner
  — the "printed once" rule below, extended to the figures. A region whose total
  area no table states (the aileron: `AileronInput` carries its areas forward and
  aft of the hinge and no total) **SHALL** be drawn and named without an area,
  never with one summed here.
- **The vertical tail is drawn in the fuselage-station/waterline plane and SHALL
  NOT be mirrored.** Its polylines' second coordinate is a waterline, not a butt
  line. The frame decides this, never `SurfaceInput.symmetric`, which
  `examples/baron_58.project.json` sets `true` on its fin — mirroring on the flag
  would draw a second fin below the airplane.
- **A number is printed once.** Wing area is produced by the speeds module and
  printed under 2.1 Geometry, where a reader looks for it; 2.3 omits it.
- **A `far_reference` that is not a regulation is not cited as one.** The
  configuration module sets it to `"configuration"`; a reference **SHALL** be
  printed only when it begins with a part number.
- **Excluded from 2.1**: the configuration module's *Longitudinal stability
  (estimate)* and *Landing-gear geometry (estimate)* conditions, both of which
  note themselves first-order with no oracle. A first-order estimate printed
  beside oracle-locked geometry reads as carrying the same standing.

### 3.3.1 The document is a function of the oracle projection

`build_oracle_document` reduces its project through
`field_registry.reduce_to_oracle_inputs` before running anything — the same
reducer the fingerprint hashes through (OR-21, G-OR-13). A field the oracle GUI
cannot set therefore moves neither the hash nor the document, as one guarantee
with one owner.

This is load-bearing, not belt-and-braces: section 2 quotes each module's own
certification basis, and on a concept project the speeds module takes the Part 25
Mach-margin route and says so in its note — so a concept-only field reached the
printed page, and G-OR-6 caught it. Suppressing that one field would have left
every future section free to find another.

## 3.4 Section 3: Wing Loads

Design note 44 §11 (OR-48 … OR-58) and §12 (OR-59 … OR-63). Four subsections
and one appendix, built from the `wing_loads` step
(`AIRLOADS+WINGINER+NETLOADS`).

- **3.1 states the wing data the cases were run from**, not the planform: the
  planform is 2.1's and **SHALL** be cross-referred rather than repeated.
- **3.1 defines the loads reference axis.** Every distributed load in the section
  is stated about it, and the **torsion is the only quantity the choice moves**.
  The replicated programs accumulate about the local 25 % chord, so for the
  oracle the LRA *is* the quarter chord; in this suite the axis is entered per
  surface and the torsion is transferred at the delivery boundary. 3.1 **SHALL**
  carry the axis point (X, Y, Z) at each load station and a planform figure with
  the axis drawn on it. The axis **SHALL** be drawn as an open path: closing it
  would cut a chord from tip back to root that no part of the airplane follows
  (`content.Series.closed`).
- **The axis a torsion is stated about SHALL be named wherever it is printed**,
  in the column header, the figure title or the table note. The oracle
  projection (§3.3.1) resets the entered axis to the quarter chord, which is why
  an oracle report cannot print a 40 %-chord torsion for a project that enters
  one — the document is a function of that projection, not of the file.
- **3.1's span loading is `c*cl`, not running load**, drawn at three wing lift
  coefficients: `CL = 0` (the basic distribution alone), `CL = 1.0`, and
  `CL = CLmax`. `CLmax` **SHALL** be the aero set's own `stall_cl`, never a
  constant chosen here. Each curve **SHALL** be AIRLOADS' own distribution
  evaluated at that target `CL` — the report calls the owner once per
  coefficient and **SHALL NOT** combine the additive and basic parts itself.
- **The flaps-down span load SHALL be stated absent, never filled with the clean
  set.** AIRLOADS does not model the lift discontinuity a deflected flap puts in
  the basic distribution — the Appendix A wing has none — so no project can
  produce it. The oracle prints two sets and this analysis can print one, and
  the figure says so. The capability gap is **#163**.
- **3.1's coefficient curves are the airplane *less its tail*** — the tail-off
  data the balance solves against — with the balanced conditions marked on
  them. There is **no tail-on lift coefficient in this suite**: the balance
  carries the tail load as a separate force rather than inside the coefficient,
  so a marked point sits on the curve and the section **SHALL** say that rather
  than implying a second curve exists.
- **3.2 is the run register**: one row per selected case with its case ID,
  condition, 14 CFR paragraph, CG case and weight, speed, altitude and
  `Nz`/`Nx`. This discharges OR-41. It also states the axes and sign convention,
  and **SHALL** compose its own cross-references through the numbering owner —
  a subsection reference typed as "3.1" is the F-R2 defect one level down
  (`oracle_content.subsection_ref`).
- **3.2 states the sign convention of its load factors and whether the set is
  enveloping.** `Nz` in a wing case is the *inertia* load factor, the negative of
  the airplane's flight load factor, so a +3.8 g manoeuvre prints as −3.8. Every
  load factor in the table is negative whichever kind of condition it is, so 3.2
  **SHALL** state the convention and **SHALL** state — from the analysed set, not
  by assertion — whether it holds a negative-load-factor case. A set of
  positive-g cases alone does not envelop the wing.
- **3.2 states where its case list came from.** Two paths reach a wing case set:
  the critical-load selection's search, and a case list entered on the project,
  which wins when present. 3.2 **SHALL** name which, **SHALL** state what the
  V-n matrix enumerates — every combination of configuration, weight/CG case,
  altitude and condition, since a V-n diagram itself states none of those — and,
  where the list is entered, **SHALL** tabulate every condition the selection
  names against whether it was run.
- **SELECT's subset is the critical set.** 3.3 tabulates its root values and
  3.4 plots every one of it; no second criticality rule is invented for the
  report. 3.4 carries one figure per quantity — `Sz`, `Mxx`, `Myy`, `Sx`,
  `Mzz` — showing the **net** loads only, and **SHALL** state that they are
  summed from the tip inboard.
- **The cases 3.2, 3.3, 3.4 and the appendix state SHALL be one set**, in one
  order: four projections of the same analysis.
- **Every load in section 3 and its appendix is ULTIMATE and marked**; every
  input distribution is LIMIT and says so. This is where G-OR-4 stops being
  vacuous — section 2 held it by carrying no force or moment at all (OR-44),
  and section 3 holds it only by marking every one of them.
- **3.2 owns the notation and the derivation.** It **SHALL** carry a symbol
  table giving, for every symbol section 3 or its appendix prints, the quantity,
  its units, and **whether it is an applied increment or a cumulative load** —
  and it **SHALL** write out the recurrences that build `Sz`, `Sx`, `Mxx` and
  `Myy` from the applied set, naming which terms are position transfers a
  structural model generates for itself. A column heading anywhere in section 3
  **SHALL** name a symbol from that table and nothing else.
- **Appendix B is a structures deck, and is split in two.** B.1 is the
  **applied** set: per row, the point the load acts at (`X`, `Y`, `Z`) and the
  load applied there (`Fz`, `Fx`, `Myy` free). B.2 is what the structure
  **carries**: `Sz`, `Sx`, `Mxx`, `Myy`, `Mzz` against station. No load column is
  shared between them. B.1 **SHALL** carry its own coordinates — a force
  without its point is half a load definition, and a deck that sends the reader
  to another section for the other half is not one.
- **The applied moment SHALL be the free moment**, never a difference of the
  cumulative column. `Myy` accumulates a section moment *and* two position
  transfers of the outboard shear across the bay's sweep and dihedral; only the
  first is applied, and the two are not close — on `ga6_normal` PHAA's outboard
  strip they are opposite in sign. By the same argument `Mx` and `Mz` have no
  applied increment and **SHALL NOT** be given one.
- **B.1 SHALL state all six body-axis components, printing the structural zeros
  (OR-65).** `Fy`, `Mx` and `Mz` are zero for every row of this load set — the
  wing chain has no spanwise strip-load producer and no delivered wing condition
  is lateral; a strip applies forces and a section moment and nothing else — and
  each zero **SHALL** be printed with that reason stated in the table's note. A
  reader building `FORCE`/`MOMENT` cards from a partial vector cannot tell a
  zero from an omission, and the earlier rule (omit `Fy` lest a zero read as a
  measured zero) traded one misreading for a worse one.
- **The map from the calc's moment convention to body axes SHALL have one owner
  (OR-66).** The calc stores `Mxx`/`Mzz` as positive-magnitude beam integrals,
  so against a right-handed `r × F` the second is negated; B.1 and the exported
  CSV both take their moments through `export.sbeam_bridge.applied_body_moments`
  and neither restates the sign.
- **B.1 SHALL be a view of the exported applied set, not a second assembler
  of it (OR-64).** The rows come from `export.sbeam_bridge.applied_load_rows`,
  the same owner behind the `wing_applied_loads.csv` download on the Wing Loads
  page and in the Export bundle, so the appendix a stress analyst reads and the
  file they build the model from cannot disagree about what is applied. The
  report converts and marks at its own boundary, as it does for every other
  export-owned row shape.
- **Every concentrated wing mass SHALL be a row of B.1** at its own
  coordinates, carrying zero free moment. `WINGINER` steps the cumulative shear
  at each mass and leaves the per-strip loads panel-only, so a deck built from
  the strip table alone loses the whole of the point-mass inertia relief — on
  `baron_58` PHAA, 4,821.5 lb of a 5,004.1 lb root shear. A point mass produces
  no free moment: every moment it makes is its force through an arm its own
  coordinates state.
- **The applied set SHALL close onto the cumulative one.** Summed tip inboard,
  with each point mass entering through its own arms, the six applied components
  reproduce the published `Sz`, `Sx`, `Mxx`, `Myy` and `Mzz` at every station of
  every case. This is the gate under the whole appendix: a model is given the
  applied loads and returns the internal ones, and if the two disagree here they
  disagree there, invisibly.
- **B.2 SHALL state chord bending `Mzz` (OR-71, superseding OR-70).** It is
  computed for every case, oracle-locked at the root (Appendix A p222), printed
  by `wing_span_loads.csv`, printed at the root by 3.3, and named by the
  closure gate above — and at the root it exceeds the torsion beside it on four
  of the five example cases. The earlier omission was recorded as "not
  delivered by this analysis", which was never true of the number, and OR-70's
  own reason (a beam `Mzz` beside a body-axis `Mz` mixes conventions) does not
  hold: B.2 already prints `Mxx` beside B.1's `Mx`, and 3.2 already defines the
  difference. 3.2 **SHALL** print `Mzz`'s recurrence with the other four.
- **3.4 SHALL plot every quantity B.2 tabulates (OR-72, superseding OR-55's
  `Mzz` omission).** The figure set and the appendix's cumulative column set are
  the same set, so a column cannot arrive unplotted by omission rather than by
  decision.
- **B.2's note SHALL restate the sign, not only cross-reference it (OR-73).**
  Its `Mzz` and B.1's `Mz` are opposite in sense and B.1's `Mz` is identically
  zero, so nothing else on the page would warn a reader who looks a number up
  rather than reading the section through. 3.2's notation table remains the
  definition and the note **SHALL** name it.
- **A notation symbol SHALL be data on the value, never a substring of its
  label (OR-74).** `LoadValue.symbol` carries it and `net_loads` populates it;
  parsing was never available, since `"Root torsion Myy (25% chord)"` does not
  end in its symbol and two labels carry the same one. This is what makes the
  "names a symbol from that table" SHALL checkable where the heading is prose.
- **The notation guard SHALL walk section 3's own tables, not only the
  appendix's (OR-75).** The rule says "anywhere in section 3"; a guard that
  covered two of its tables let 3.3 ship the heading "Root chord bending Mzz"
  against a notation table that did not define `Mzz`.
- **Every appendix SHALL start a fresh page**, and Appendix B **SHALL** be
  landscape throughout — one orientation per appendix, so it survives a column
  being added rather than being re-decided per table.
- **The Appendix A input echo holds a reserved slot** that renders its OR-32
  state. Lettering is derived from position, so an unreserved slot would print
  the wing appendix as A today and move it to B when the echo lands — and an
  issue signed in between would disagree with its own reissue. A reserved slot
  is lettered and **SHALL NOT** be referable: prose points at a built appendix
  only.

## 4. Identity, signatures and DRAFT

The title block carries report number, revision, issue date, issuing
organisation, customer/programme, classification marking, distribution statement
and three signature rows — prepared, checked, approved. It carries **only**
those: the analysis basis and the not-carried list belong to the introduction
(§3), so the signature block stays on the same sheet as the identity it signs
for.

- **Any empty signature name makes the document a DRAFT**: a watermark and a
  footer sentence. All three present clears it. The build **SHALL NOT** be
  blocked by an unsigned spec — a signed and an unsigned report are built by the
  same control, and the document says which it is. There is no user toggle for
  the draft state; it is a fact about the signatures.
- An unsigned signature row **SHALL** still be rendered, with a ruled blank. The
  reader must see *that* a signature is missing.
- An unsigned row **SHALL NOT** print a date. A date beside a ruled name blank
  reads as an approval that happened on that day and was signed illegibly — the
  document asserting an event that did not occur, on the page a reader trusts
  most. The value is kept in the spec (a planned date is legitimate); it is the
  printing of it against an absent name that is refused. The role is not
  suppressed: naming who is due to sign claims nothing about whether they have.
- Dates **SHALL** be entered through a picker and stored as ISO `YYYY-MM-DD`, so
  one document cannot carry `30/8/26` and `Aug 30 2026` in the same block. The
  picker **SHALL** open empty rather than at today: a control that defaults to
  the current date puts an issue date and three signature dates into the
  document that nobody stated. A stored value that is not a date is preserved
  and reported, never silently replaced — the spec is a file a person edits.
- The classification marking **SHALL** appear on every page, not only the cover.
  A marking that appears once is one photocopied page away from being absent.
- The DRAFT mark **SHALL NOT** be the sole carrier of its meaning: the footer
  states it in words, so the document stays legible in greyscale and to a screen
  reader.
- The watermark **SHALL NOT** add a LaTeX package. The preamble is shared with
  the summary report, and `SUMMARY_REPORT.md` §2 limits the document to a
  standard distribution; the machinery needed is already loaded.
  *Note: the overlay needs two LaTeX passes to position itself. `tectonic` and
  `latexmk` do this; a single bare `pdflatex` run does not.*

## 5. Provenance

The spec records what airplane definition the report was authored against, and
the document prints it. Two questions, two answers, and the document carries
both:

Both are printed in the **introduction**, under *Analysis basis* — not on the
cover, per §4.

- **Anchors** — project name, FAR 23 category (spelled out from
  `models.inputs.CATEGORIES` rather than left as a letter to look up), the
  sloads version that wrote the document and the schema version of the project
  definition it read — answer *is this the same airplane, produced by what* for
  a reader holding a drawing. The tool version is **handed to** the anchors, not
  looked up by them: the build resolves it once for `build.json`, and resolving
  it twice is how a document and its own stamp come to disagree. Where no
  version is supplied the row is omitted rather than invented. They
  **SHALL** be computed at build time, never stored: stored text goes stale
  exactly when it matters, and would be frozen in whichever unit system was
  selected when it was written.
- **The fingerprint** answers *has anything moved*. It **SHALL** be taken over a
  canonical projection of the inputs the oracle report consumes — never over the
  project file, which would fire on a concept-mode field, an sloads-only field or
  a re-save with different key ordering. Free-text document control is excluded
  for the same reason: renaming the engineer cannot move a load.
- The fingerprint **SHALL** carry its own version, so a later milestone widening
  the projection makes existing reports say *"cannot compare"* rather than
  *"does not match"*. Those are different statements.
- On a mismatch the page **SHALL** warn and build anyway. A project is
  legitimately revised under the same report number; refusing would obstruct the
  normal case to police the rare one.
- The fingerprint is **not a signature** — there is no key, so it detects
  accident, not tampering — and it is not the record of what was analysed. The
  input echo is that.
- **The anchors were reduced from six rows to two** on 2026-08-30 (design
  weight, wing area, VC and VD removed as analysis outputs a reader meets in the
  body). The consequence is stated rather than glossed: name and category are a
  weak answer to *is this the same airplane*, so the fingerprint is now the only
  thing printed in the document that detects a changed input.

## 6. Units and determinism

The document's unit system is a property of the **spec**, so a report plus a
project is a complete, reproducible recipe. The build path **SHALL NOT** read the
GUI's unit toggle: that governs what the analysis pages display, which is a
different question with a different owner.

Two builds of the same project and the same spec **SHALL** produce byte-identical
packages, file for file.

**The qualifier is real and is stated rather than hidden:** `build.json` carries
the build timestamp, which the caller supplies. Determinism is over the recipe,
not over the wall clock. A builder that read the clock itself would make this
rule impossible to assert, and it would quietly mean nothing.

## 7. Section register

One row per agreed section, with the guard that holds it (G-OR-8: an agreement
without a guard is prose, not a gate).

| Section | Agreed | Guarded by |
|---|---|---|
| Dates and signatures | 2026-08-30 | `test_oracle_report.py::test_an_unsigned_row_prints_no_date`, `::test_the_report_page_never_defaults_a_date_to_today`, `::test_a_date_is_stored_as_an_iso_string_and_a_non_date_survives` |
| Cover / title block | 2026-08-30 | `test_oracle_report.py::test_the_draft_mark_follows_the_signatures`, `::test_the_classification_marking_is_on_every_page` |
| Abstract | 2026-08-30 | `test_oracle_report.py::test_it_builds_for_both_example_airplanes` |
| Contents, figures, tables | 2026-08-30 | `test_oracle_report.py::test_it_builds_for_both_example_airplanes` |
| 1. Introduction | 2026-08-30 | `test_oracle_report.py::test_section_numbers_come_from_the_owner_not_from_literals` |
| 1. Introduction prose and limitations | 2026-08-30 | `test_oracle_report.py::test_the_default_introduction_claims_nothing_about_omitted_sections`, `::test_the_report_page_renders_every_block` |
| Deselection is silent | 2026-08-30 | `test_oracle_report.py::test_a_deselected_section_is_omitted_entirely_and_numbering_closes_up` |
| Analysis-body placeholders | 2026-08-30 | `test_oracle_report.py::test_every_result_producing_oracle_step_has_exactly_one_section`, `::test_the_gap_states_have_distinct_wording`, `::test_each_gap_state_renders_under_its_own_lead` |
| 2. Loads Configuration (grouping, titles) | 2026-08-30 | `test_oracle_report.py::test_every_analysis_step_has_a_document_title_of_its_own`, `::test_every_group_member_is_a_step_and_the_members_are_contiguous` |
| 2.1 Geometry and control surfaces | 2026-08-30 | `test_oracle_report.py::test_a_wing_area_is_stated_once_in_the_whole_section`, `::test_a_far_reference_that_is_not_a_regulation_is_not_printed_as_one`, `::test_every_control_surface_the_project_defines_gets_a_table`, `::test_the_echoed_surface_inputs_are_the_fields_the_project_still_has`, `::test_the_as_entered_statement_is_made_once` |
| 2.2 Weight and Mass Properties | 2026-08-30 | `test_oracle_report.py::test_section_two_invents_no_number`, `::test_the_cg_case_table_states_every_case_and_its_role_and_analysis`, `::test_the_analysis_column_is_ordered_not_set_ordered` |
| 2.2 Weight/CG envelope figure (note 45 WE-8) | 2026-08-31 | `test_oracle_report.py::test_the_weight_cg_figure_draws_both_loading_edges`, `::test_the_weight_cg_figure_reaches_its_own_emitter_and_closes_its_limits`, `::test_the_weight_cg_figure_marks_every_entered_case_once`, `::test_the_envelope_vertex_table_is_wtenv_s_own_result`, `::test_the_weight_cg_figure_states_no_load_and_no_safety_factor`, `::test_a_project_with_no_weight_database_says_why_instead_of_drawing`, `::test_the_limit_envelope_is_omitted_rather_than_half_drawn` |
| 2.2 CG-case %MAC column | 2026-08-31 | `test_oracle_report.py::test_the_cg_case_table_states_xcg_in_percent_mac_from_the_one_reference`, `::test_the_cg_case_table_prints_the_percent_mac_relation_and_its_reference`, `::test_a_case_table_with_no_mac_reference_says_so_instead_of_printing_zero` |
| 2.3 Structural Design Speeds | 2026-08-30 | `test_oracle_report.py::test_the_paired_tables_pair_keys_the_modules_actually_produce` , `::test_a_paired_table_drops_a_units_column_no_row_fills` |
| 2.4 Speed/altitude envelope | 2026-08-31 | `test_oracle_report.py::test_the_speed_altitude_envelope_opens_2_4_and_reaches_sea_level`, `::test_the_speed_altitude_envelope_plots_only_machlim_s_own_speeds`, `::test_vh_is_marked_at_sea_level_and_is_not_drawn_as_a_boundary`, `::test_the_speed_altitude_envelope_has_one_builder_for_both_reports`, `::test_an_airplane_with_no_mach_inputs_says_so_instead_of_drawing` |
| 2.4 Flight Envelope | 2026-08-30 | `test_oracle_report.py::test_the_envelope_boundary_order_is_the_analysis_order`, `::test_the_envelope_figures_plot_only_produced_design_points`, `::test_one_envelope_figure_per_loading_and_altitude` |
| 3. Wing Loads (subsections, appendix lettering) | 2026-09-01 | `test_oracle_report.py::test_the_wing_section_renders_its_four_subsections_numbered_by_the_owner`, `::test_wing_loads_is_appendix_b_while_the_input_echo_holds_appendix_a`, `::test_the_reserved_appendix_states_its_state_and_is_not_pointed_at` |
| 3.1 Loads reference axis and wing inputs | 2026-09-01 | `test_oracle_report.py::test_every_wing_torsion_names_the_axis_it_is_stated_about`, `::test_the_reference_axis_is_drawn_open_on_a_closed_planform`, `::test_the_span_load_is_drawn_at_zero_unit_and_the_airplanes_own_clmax`, `::test_the_span_load_curves_are_airloads_own_distribution`, `::test_a_project_with_no_flaps_down_set_says_so_and_draws_nothing` |
| 3.2 Load-factor sign and envelope coverage (OR-58) | 2026-09-03 | `test_oracle_report.py::test_the_register_states_what_the_sign_of_a_load_factor_means`, `::test_a_case_set_with_no_negative_load_factor_says_it_does_not_envelop` |
| 3.2 Case-list provenance (OR-57) | 2026-09-03 | `test_oracle_report.py::test_the_register_states_the_matrix_the_selection_actually_searched`, `::test_an_entered_wing_case_list_is_not_reported_as_the_selections_result`, `::test_a_project_that_enters_no_wing_cases_reports_the_selections_own_result` |
| 3.2-3.4 Cases, root loads and distributions | 2026-09-01 | `test_oracle_report.py::test_the_wing_cases_are_one_set_seen_four_ways`, `::test_the_wing_root_loads_are_the_limit_result_times_the_case_factor`, `::test_a_project_with_no_wing_loads_states_the_absence_and_still_builds` |
| Section 3 delivers ULTIMATE; inputs stated LIMIT | 2026-09-01 | `test_oracle_report.py::test_every_load_the_wing_section_prints_is_marked_ultimate` |
| 3.2 Notation and the cumulative-load derivation (OR-62) | 2026-09-03 | `test_oracle_report.py::test_section_three_defines_every_symbol_its_tables_use`, `::test_section_three_states_how_the_cumulative_loads_are_built`, `::test_the_point_mass_rule_is_stated_only_where_there_is_one` |
| Appendix B: applied set and carried set (OR-59, OR-60) | 2026-09-03 | `test_oracle_report.py::test_the_appendix_separates_the_applied_loads_from_the_carried_ones`, `::test_the_applied_table_carries_the_point_every_load_acts_at`, `::test_the_appendix_subsections_are_lettered_from_their_parent` |
| Appendix B: concentrated masses and closure (OR-59, G-OR-29) | 2026-09-03 | `test_oracle_report.py::test_every_concentrated_wing_mass_is_a_row_of_the_applied_table`, `test_net_loads.py::test_the_applied_strip_set_reproduces_the_cumulative_loads`, `::test_a_concentrated_wing_mass_is_published_as_its_own_applied_load`, `::test_the_axis_transfer_moves_the_free_moment_on_its_own_force` |
| B.1 and the exported CSV are one load set (OR-64) | 2026-09-03 | `test_oracle_report.py::test_the_appendix_table_and_the_exported_csv_are_one_load_set`, `test_sbeam_bridge.py::test_the_applied_moment_is_the_free_moment_not_the_increment` |
| B.1 states all six components and prints its structural zeros (OR-65, OR-66) | 2026-09-03 | `test_sbeam_bridge.py::test_the_applied_set_states_all_six_components`, `::test_the_applied_set_reproduces_the_whole_vmt_at_every_station`; note 46 G-OR-35/36 |
| Appendix page breaks and landscape (OR-63) | 2026-09-03 | `test_oracle_report.py::test_the_appendix_is_landscape_and_starts_a_fresh_page` |
| Section 2 marks nothing ultimate; load factors identified as LIMIT | 2026-08-30 | `test_oracle_report.py::test_section_two_marks_nothing_ultimate_and_states_no_safety_factor`, `::test_no_table_claims_a_load_factor_is_not_a_load`, `::test_reported_load_factors_are_identified_as_limit` |

## 8. Conformance

- [x] Appendix B is two subsections — the applied loads and the loads carried —
      sharing no load column, with B.1 carrying the point each load acts at —
      `test_oracle_report.py`
- [x] The applied moment is the free moment; `Mx` and `Mz` are given no applied
      increment — `test_oracle_report.py`, `test_net_loads.py`
- [x] B.1 states all six body-axis components and prints `Fy`, `Mx`, `Mz` as
      zero with the reason stated (OR-65) — `test_sbeam_bridge.py`,
      `test_oracle_report.py`
- [x] Both views take their moments through `applied_body_moments`, the one
      owner of the body-axis sign map (OR-66) — `test_sbeam_bridge.py`
- [x] Every concentrated wing mass is a row of B.1 at its own coordinates,
      carrying zero free moment — `test_oracle_report.py`
- [x] The applied set summed tip inboard reproduces the published cumulative
      loads at every station of every case, on both example airplanes —
      `test_net_loads.py`
- [x] The published free moment and `balance`'s own recovery agree where both
      are valid — `test_net_loads.py`
- [x] B.1's rows and the `wing_applied_loads.csv` download come from one owner
      and agree row for row — `test_oracle_report.py`, `test_sbeam_bridge.py`
- [x] Every symbol a section 3 or Appendix B heading uses is defined in 3.2's
      notation table with its sense — including 3.3's prose headings, checked
      through `LoadValue.symbol` rather than parsed out of the text, and
      including that the label prints the symbol it declares (OR-74/OR-75,
      G-OR-42) — `test_oracle_report.py`
- [x] 3.2 writes out the cumulative-load recurrences — one for every column B.2
      carries, `Mzz` included — and names which terms are position transfers
      (G-OR-43) — `test_oracle_report.py`
- [x] B.2 states chord bending `Mzz`, every value the module's own station value
      × that case's SF (OR-71, G-OR-39) — `test_oracle_report.py`
- [x] B.2's note states that its moments are the beam's own and that `Mzz` is
      the negation of a body-axis `Mz` (OR-73, G-OR-40) —
      `test_oracle_report.py`
- [x] The quantities 3.4 plots are exactly the quantities B.2 tabulates
      (OR-72, G-OR-41) — `test_oracle_report.py`
- [x] Every appendix starts a fresh page; Appendix B is landscape and the
      environment opens and closes once — `test_oracle_report.py`
- [x] 2.2's weight/CG figure draws both loading edges, closes its limit
      envelope, and omits the limits rather than half-drawing them —
      `test_oracle_report.py`
- [x] Every entered CG case is marked once, coincident cases sharing a marker
      and both names — `test_oracle_report.py`
- [x] The plotted vertices are reproduced from WTENV's own `ModuleResult`, not
      re-swept by the report — `test_oracle_report.py`
- [x] The weight/CG figure has one builder, shared with the summary report; its
      limit corners read the same MAC reference the `% MAC` column does —
      `test_derived_geometry.py`
- [x] The CG-case table states Xcg in %MAC from `mac_reference`, prints the
      relation both ways with the pair it used, and dashes rather than zeroes
      when no reference resolves — `test_oracle_report.py`
- [x] 2.4 opens with the speed/altitude envelope, drawn from sea level, plotting
      only MACHLIM's own speeds, with Vh marked and not drawn as a boundary —
      `test_oracle_report.py`
- [x] The V-n figures carry no caption and the LIMIT identification is made once
      in the subsection body — `test_oracle_report.py`

- [x] Section 3 renders four subsections numbered by the numbering owner, and
      Wing Loads is Appendix B behind a reserved, unreferable Appendix A —
      `test_oracle_report.py`
- [x] Every load section 3 and Appendix B print carries the `-ULT` marker, and
      each root value is the module's own LIMIT result times that case's stated
      factor — `test_oracle_report.py`
- [x] Every wing torsion names the axis it is stated about, and the reference
      axis is drawn as an open path on a closed planform —
      `test_oracle_report.py`
- [x] The span load is AIRLOADS' own distribution at `CL = 0`, `1.0` and the
      aero set's `stall_cl`, and the flaps-down set is stated absent rather than
      filled with the clean one — `test_oracle_report.py`
- [x] 3.2, 3.3, 3.4 and Appendix B state one set of cases in one order —
      `test_oracle_report.py`
- [x] 3.2 says whether its cases are the selection's result or the project's
      entered list, counts the matrix searched, and marks each named condition
      run or not — `test_oracle_report.py`
- [x] 3.2 states that Nz is the inertia load factor and says when the analysed
      set holds no negative-load-factor case — `test_oracle_report.py`
- [x] Appendix B carries the station increment and the cumulative total, and the
      station coordinates are printed once — `test_oracle_report.py`

- [x] The section set is `oracle_steps()`'s result-producing steps, both
      directions — `test_oracle_report.py`
- [x] The printing section states are distinct in wording, in rendered lead, and
      in precedence — `test_oracle_report.py`
- [x] A deselected section is omitted and the numbering closes up behind it —
      `test_oracle_report.py`
- [x] The document numbers its pages continuously and marks every page —
      verified at each iteration's local compile
- [x] No report metadata reaches a `ModuleResult` or a table cell —
      `test_oracle_report.py`
- [x] The build reads the spec's unit system and never the GUI toggle —
      `test_oracle_report.py`
- [x] The package is exactly its manifest, hashes included —
      `test_oracle_report_package.py`
- [x] The manifest meets `SUMMARY_REPORT.md` §4.7 —
      `test_oracle_report_package.py`
- [x] Every analysis step has a document title distinct from its workflow label —
      `test_oracle_report.py`
- [x] A section group's members are contiguous in workflow order and each has
      exactly one home — `test_oracle_report.py`
- [x] Every number section 2 prints comes from a `ModuleResult` or from the
      project as entered; none is invented — `test_oracle_report.py`
- [x] Section 2 marks nothing ultimate and states no safety factor —
      `test_oracle_report.py`
- [x] Every control surface the project defines has a table, and no surface key
      reaches a heading — `test_oracle_report.py`
- [x] The CG-case table explains role and analysis, and prints the analysis tags
      in a declared order — `test_oracle_report.py`
- [x] The envelope figures plot produced design points only, one figure per
      block, in the analysis's own traversal order — `test_oracle_report.py`
- [x] Every main surface has a planform figure and every planform figure has a
      declared surface; each key reaches its own emitter and is drawn on equal
      axes — `test_oracle_report.py::test_every_main_surface_has_a_planform_figure`,
      `::test_a_planform_key_reaches_its_own_emitter`
- [x] A planform plots only entered vertices and labels a region only with the
      area its table prints —
      `test_oracle_report.py::test_a_planform_plots_only_entered_vertices`,
      `::test_a_planform_labels_a_region_with_the_area_its_table_prints`
- [x] A surface with no entered polylines states why instead of rendering an
      empty axis —
      `test_oracle_report.py::test_a_surface_without_polylines_states_why_instead_of_drawing`
- [x] The vertical tail is drawn in its own frame and is never mirrored, whatever
      `SurfaceInput.symmetric` says —
      `test_oracle_report.py::test_the_vertical_tail_is_drawn_in_its_own_frame_and_never_mirrored`
- [x] No planform figure marks a load, a safety factor or a force/moment unit —
      `test_oracle_report.py::test_a_planform_states_no_load_and_no_safety_factor`
- [x] A half-entered planform is refused by the precondition owner and stated,
      not drawn, and the other surfaces still build —
      `test_oracle_report.py::test_a_half_entered_planform_is_refused_rather_than_drawn`
- [x] The document is built from the oracle projection, so no concept-mode field
      reaches it — `test_oracle_report.py::test_concept_fields_cannot_reach_the_document`
- [x] The List of Figures carries titles, not whole captions —
      `test_oracle_report.py`
- [x] Two builds of one recipe are byte-identical —
      `test_oracle_report_package.py`
- [x] The build never rewrites the user's spec —
      `test_oracle_report_package.py`
- [x] The spec round-trips; a missing file opens a blank draft —
      `test_report_spec_io.py`
- [x] The fingerprint moves on an oracle input and not on document control —
      `test_oracle_report.py`, `test_report_spec_io.py`
- [ ] Every shipped data file states units, SF and basis, step key and
      fingerprint — `test_oracle_report_package.py`, **vacuous until the first
      analysis section ships data**
- [ ] No orphan data files in either direction — `test_oracle_report_package.py`,
      **vacuous for the same reason**
- [ ] Every load value equals its `ModuleResult` value × its case's SF — lands
      with the first analysis section
- [ ] The `.tex` compiles to PDF from inside the package — lands with the
      package-aware compile
