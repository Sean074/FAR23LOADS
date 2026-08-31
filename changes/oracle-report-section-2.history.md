## Step 152 — The oracle technical report, section 2: Loads Configuration (tier L, 2026-08-30)

**Objective.** Deliver the first analysis section of the oracle technical report under
design note 44's OR-8 protocol — content spec agreed with the owner, implemented, and
approved from the rendered PDF — covering the airplane configuration the design loads
were computed for.

**Deliverables.**
- `sloads/report/oracle_sections.py` — one content builder per step key, turning a
  `ModuleResult` into `Section` tables and figures. Computes nothing: unit conversion is
  `units.convert_results` and the ultimate boundary is `report.render`, both asked rather
  than re-implemented, which is what makes G-OR-4 hold by construction rather than by
  inspection.
- `oracle_content.DOCUMENT_TITLES` — the heading a section prints, separate from
  `WorkflowStep.title`. The workflow label exists for the oracle GUI's navigation; a
  reader of the PDF has no concept of it, and renaming a nav item must not retitle a
  report somebody has already signed. Guarded both directions.
- `oracle_content.SECTION_GROUPS` + parent/child numbering (`subsection_number`,
  `heading`) — Section 2 groups four steps as 2.1–2.4. Declared as data, so a later
  grouping needs no new logic; members are guarded contiguous in workflow order, because
  a group that skipped a step would collect whatever sat between its members.
- `oracle_content.run_sections` — the one place a module is run for the report, so the
  page's preflight and the document it writes can never describe different analyses.
- Section 2.4's V-n figures, one per loading/altitude block, plus a corner load-factor
  table.
- `ORACLE_REPORT.md` §3.3 (the section's SHALL list) and §3.3.1; note 44 §10
  (OR-38…OR-44); register rows and conformance items.

**Test.** Twelve new gates in `tests/test_oracle_report.py`: every printed number is one
a module produced, checked against the modules run independently of the report; nothing in
Section 2 is marked ultimate or states a safety factor; the declared envelope traversal
matches FLTLOADS' own case order; every plotted vertex is a produced case; one figure per
block; the paired tables' keys still exist upstream; wing area is stated once in the whole
section; a `far_reference` that is not a regulation is not cited as one; every analysis
step has a document title distinct from its workflow label; group members are contiguous.
The existing structural gates were rewritten for a section tree rather than a flat list.

**Key decisions.**
- **The V-n envelope is the polyline through the produced design points, not
  `build_vn_diagram`'s curve** (OR-40). That builder's own docstring calls it an
  approximate Structural-Speeds sanity plot; its stall boundary assumes constant CLmax and
  predicts n = 3.51 at the STALL +N corner of the reference GA wing where FLTLOADS
  computes 3.80 — 8% low, because the real boundary follows CL rising 1.395 → 1.512 with
  α plus compressibility. Drawing it would put the report's own design points visibly off
  their own boundary. Sampling the true curve is frozen-module work, backlogged and parked
  with that number.
- **The document is built from the oracle projection** (OR-43). `build_oracle_document`
  now reduces through `field_registry.reduce_to_oracle_inputs` — the same reducer the
  fingerprint hashes through — so "a field the oracle GUI cannot set moves neither the
  hash nor the document" is one guarantee with one owner. This was found by G-OR-6
  failing, not by inspection: Section 2 quotes each module's certification basis, and on a
  concept project the speeds module takes the Part 25 Mach-margin route and says so in its
  note, so a concept-only field reached the printed page. Suppressing that one field would
  have left every later section free to find another.
- **Section 2 states no load in force or moment units** (OR-44). Values still route through
  the ultimate boundary rather than being hand-formatted, so the section never decides what
  a load is. A first draft explained the absent `-ULT` marker with a note saying geometry,
  mass, speeds and load factors "are not loads"; the owner corrected that — **n is a limit
  load factor, so a load factor is a load** — and the note was removed rather than reworded.
  Where a load factor is reported the document identifies it as LIMIT, at point of use.
- **The `data/*.csv` externalisation of OR-23 is deferred to its own iteration** (OR-42),
  taking G-OR-15 and G-OR-17 with it.
- **Two upstream findings recorded rather than fixed**, `sloads/modules/**` being frozen
  (OR-14): the four modules stamp `safety_factor=1.5` on non-load conditions — geometry,
  inertia, design speeds — which affects no value but is a false claim, filed as an issue;
  and the configuration module's `far_reference` is `"configuration"`, which printed as
  "Certification basis: 14 CFR configuration" until the report learned to cite only
  references that begin with a part number.
