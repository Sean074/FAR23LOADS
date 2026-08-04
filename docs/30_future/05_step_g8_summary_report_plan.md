# Step G8 — Consolidated Summary Report (Export phase) — implementation plan

**Backlog item:** M3-3 / Step G8, the first item of **M4** (was the M3 stretch).
**Source spec:** [`03_gui_rework_plan.md §4 Phase 6`](03_gui_rework_plan.md) — the
four-section summary report.
**Document standard:** [`../10_standard/SUMMARY_REPORT.md`](../10_standard/SUMMARY_REPORT.md)
— the authoritative structure, required content and **excluded** content. Where
this plan and the standard disagree, **the standard wins**; §4 below is the
build-order reading of it, not a second specification.
**Status:** planned, not started. This document is the execution plan; the backlog
entry links here and stays the one-line "open work" record until the step closes.

---

## 1. Goal

Produce **one controlled document** that a structural analyst can size airframe
structure from: the airplane, its weights and CG travel, its flight envelope, the
FAR conditions analysed, and every governing **ULTIMATE** load with its safety
factor — plus an explicit methods-and-limitations statement that travels with the
machine-readable deliverables (CSV / BDF) so downstream sizing inherits the
concept-mode caveat the UI already shows.

**Non-goal:** any change to the calc. No load equation, oracle figure or exported
number moves. Step G8 is a **new render/export channel over existing results**,
governed by the same ultimate-load boundary that `report.py` and
`export/sbeam_bridge.py` already own.

---

## 2. Locked decisions (user, this session)

| # | Decision | Rationale |
|---|----------|-----------|
| **G8-1** | **LaTeX only.** A pure renderer emits `.tex`; PDF is compiled when a TeX engine is on `PATH`, otherwise the `.tex` is served with a hint. The bundle always carries the `.tex`. | Controlled-document features (pagination, headers/footers, page *n of m*, ToC, figure/table numbering, `longtable`, signature/revision block) that browser print-to-PDF cannot give. No HTML backend — one renderer, one format. `tectonic` is present at `/opt/homebrew/bin/tectonic`. |
| **G8-2** | **Plots are pgfplots/TikZ emitted as text.** No plotly in the report, no `kaleido`, no refactor of the Streamlit plot code. | Deterministic, unit-testable source (the same way BDF cards are tested), vector output in the document's own fonts. The plot *data* already comes from pure functions (`vn_diagram.build_vn_diagram`, `weight_envelope.loading_envelope_points`), so no GUI extraction is needed to avoid divergence. |
| **G8-3** | **Methods statement stamped everywhere:** `$` comment block in each BDF, `#`-prefixed provenance lines above each CSV header, `METHODS.txt` in the zip, a `Methods` sheet in the workbook, and §5 of the report. | Follows the existing `body_loads.CLOSURE_ARTIFACT_CAVEAT` precedent for BDF. A CSV forwarded on its own still carries its basis. Accepted risk: naive CSV consumers see comment rows (mitigation in §7). |
| **G8-4** | **Depth: summary + every governing case, pointing at companions.** The report carries the governing cases, per-component V/M/T maxima and *where* they occur; full station-by-station distributions stay in the bundle's CSV/BDF files, named from the report. | A single self-contained PDF of every station × every case runs to hundreds of pages. The bundle is the deliverable; the report is its controlling document. |

---

## 3. Package layout

`sloads/report.py` becomes a package, exactly as `models.py` → `models/` did at
M3-1. `sloads/report/__init__.py` re-exports the current public names
(`results_to_rows`, `load_cases_to_rows`, `governing_loads_table`,
`module_text_report`, `text_report`, `has_load_case_data`, `ultimate_units`,
`to_ultimate`, `envelope_extremes`) so **every existing import keeps working
unchanged** — this is a mechanical move, not an API change.

```
sloads/report/
  __init__.py      re-exports render.* (back-compat) + the new document entry points
  render.py        <- today's report.py, verbatim (tables, ULT boundary, text report)
  methods.py       the ONE source of the methods & limitations statement + the
                   CSV `#` / BDF `$` comment blocks built from it
  coverage.py      FAR Subpart C coverage matrix (static reg table x this run's
                   far_reference values -> covered / n-a / not analysed)
  content.py       pure content model: Project + module results -> ReportDocument
                   (sections, tables, figures, notes). No LaTeX, no Streamlit.
  latex.py         pure renderer: ReportDocument -> .tex string (escaping,
                   longtable, document control block)
  plots_tex.py     pgfplots/TikZ emitters: V-n, weight/CG, speed-altitude
sloads/export/
  pdf.py           the only impure piece: engine discovery + subprocess compile
```

**Why a content model between the data and the `.tex`.** Tests assert structured
content (`doc.section("Design speeds").table.rows`) instead of matching LaTeX
strings, which makes them readable and resilient to formatting changes; and the
`.tex` renderer stays a dumb, fully-covered string function. It also leaves a
future HTML/Markdown backend as a small addition rather than a rewrite — without
building one now.

**I/O exemption (must be documented in the module docstring).** `sloads/export/pdf.py`
runs a subprocess and writes a temp directory, which the "calc never does I/O"
rule forbids for calc code. It is an *export-side* helper on the same footing as
`io.py`, it contains no math, and nothing in `sloads/report/` imports it — the
pure renderer never touches the filesystem. State this explicitly in the docstring
and in `PROJECT_GUIDE §4`, or it reads as a violation.

---

## 4. Report structure

Ten to twenty pages for a typical GA project, in this order. The normative
statement of this structure — including the whole-document rules (load marking,
traceability, axes/signs/stations, absence handling, units) and the **excluded
content** list — is [`../10_standard/SUMMARY_REPORT.md`](../10_standard/SUMMARY_REPORT.md).
What follows is the implementation reading: which existing pure function supplies
each block, and what is new work.

### Title page + document control
Project name, engineer, date, **revision**, checked-by / approved-by signature
block, category badge (**FAR 23** or **Concept (C) — unverified extrapolation**),
tool version + `SCHEMA_VERSION`, and the one-line basis statement
("All loads ULTIMATE; safety factor stated per case"). Table of contents follows.

### §1 — Input summary
Everything the analyst needs to confirm they were given the right airplane:

- **Configuration** — category, engine layout and count, engine/prop designation,
  turboprop flag, occupants / seats / crew, `include_far25` flag.
- **Geometry** — wing area, span, MAC, aspect ratio, taper, sweep, dihedral,
  incidence; h-tail and v-tail area/arm/volume-coefficient; elevator/rudder and
  aileron/flap/tab chord fractions; landing-gear stations and track; fuselage
  length and max width/depth.
- **Weights & CG** — MTOW, empty, fuel, payload; the per-CG design weights SELECT
  uses; forward/aft CG limits (in and %MAC) and the loading-envelope travel;
  mass properties (Iyy, Izz) with their provenance (WTONECG per-CG values vs. the
  Ch 9 approximation — see backlog M4-4).
- **Design speeds** — VS, VSF, VA, VC, VD, VF (and VMO/MMO when `mach_limit` ran),
  each with its FAR reference and whether it was user-set or derived.
- **Aero** — CLmax (clean / flapped), lift-curve slopes, CM set, and whether the
  Munk fuselage `dCm/dα` contribution is enabled.

Each table cites the page that owns the input, so a wrong number is traceable to
one screen.

### §2 — Envelope plots (pgfplots)
Three figures, **each with its corner-point table underneath** — the numbers must
be readable, not merely plotted:

1. **V-n diagram** — manoeuvre + stall boundaries, gust lines, flap envelope, from
   `vn_diagram.build_vn_diagram()`. Corner table: VS/VA/VC/VD/VF × n⁺/n⁻, with the
   gust-vs-manoeuvre governing flag per corner and a note when
   `gust_approximate` is set.
2. **Weight / CG envelope** — the loading-envelope polygon from
   `weight_envelope.loading_envelope_points()` with the fwd/aft limits and each
   design CG case marked. Corner table: weight, CG (in and %MAC), and the item
   sequence that produces each corner.
3. **Speed / altitude envelope** — VMO/MMO from `mach_limit.mach_limit_lines()`
   plus the derived-gust taper above 20,000 ft (`vn_diagram._gust_ude`). **This
   figure has no GUI equivalent today** — it is genuinely new work (small: two
   pure lines over an altitude sweep). If `speeds.mach_limit` is absent the figure
   is omitted and the section says so rather than drawing an empty axis.

### §3 — Conditions analysed + FAR coverage
- **Case index** — every structured case ID mapped to its full definition
  (component, condition, CG, speed, altitude, SF), rendered `longtable` in a small
  font, from the existing `sbeam_bridge.case_index_csv_from()`. State plainly
  whether the **full set** or the **governing set** (the Critical Loads opt-out
  selection) was exported, and list the deselected IDs if any — an analyst must
  never silently receive a filtered set.
- **FAR coverage matrix** (`report/coverage.py`) — a static table of the FAR 23
  Subpart C regulations the suite covers (sourced from `PROGRAM_SPEC.md` and the
  FAA User's Guide Table 2.2), each row cross-checked against the
  `far_reference` values this run actually produced: **covered** (with case
  count), **not applicable** (with the reason — e.g. 23.345 flap conditions on an
  unflapped airplane), or **not analysed** (inputs absent). This is the section
  that tells a reviewer what is *missing*, so "not analysed" rows must be visually
  distinct, not buried.
- **Approved corrections** — the three register entries (23.361(a)(1),
  23.361(a)(3), 23.427(a)) listed with their citations, since they are deliberate
  deviations from the source manual that a reviewer will otherwise flag.

### §4 — Results summary (all ULTIMATE, SF per case)
Per component, the governing cases via the existing
`report.governing_loads_table()` (already ULTIMATE-marked and SF-columned), plus a
maxima block naming *where* each maximum occurs:

| Component | Reported |
|-----------|----------|
| **Wing** | Governing cases (PHAA/PMAA/PLAA/NMAA); max shear / bending / torsion with the span station of each; the torsion axis named explicitly (LRA, % chord, from `net_loads.torsion_axis_label`); two-sided max **and** min envelopes. |
| **Fuselage** | Governing cases; max V/M/T with body station; the closure statement — the exported set closes both ΣFz and the terminal `Myy` at the front/rear spar attachments (M4-1); the wing-attach fitting loads, and `body_loads.CLOSURE_ARTIFACT_CAVEAT` **verbatim** whenever a case fell back to the whole-body correction. |
| **Horizontal / vertical tail** | Balancing, manoeuvre, gust and unsymmetrical conditions; the 25%/50% MAC chordwise split (`lt25`/`lt50`). |
| **Control surfaces** | Aileron / flap / tab: design pressures, hinge moments, and the *standard simplified* distribution used — flagged as such. |
| **Landing gear** | Reaction cases per gear (level, tail-down, one-wheel, side, braked) with the gear geometry they act on. |
| **Engine mount** | Torque, thrust, side and gyroscopic cases, incl. the four 23.371(b) sign combinations; note the preserved sign conventions (reaction torque reported negative; clockwise-from-pilot positive). |

### §5 — Methods & limitations
The full statement (§5 below drives its content) plus a **references** list: Ref 1
page citations per module (from `20_theory/00_theory_sources.md`), the CFR parts,
and the oracle-status statement.

### Appendix A — Bundle manifest
Each companion file: what it contains, its units, its sign convention, and which
report section summarises it. This is what makes the pointer-to-companions
decision (G8-4) safe — `wing_span_loads.csv` is useless without knowing its
torsion axis and that its loads are ULTIMATE.

---

## 5. The methods & limitations statement

Single source: `report/methods.py`. One function builds the full prose block; two
thin wrappers wrap it as `#` (CSV) and `$` (BDF) comment blocks. Content, assembled
per project:

1. **Basis** — loads are ULTIMATE (= limit × SF); SF stated per case; default 1.5
   per 14 CFR 23.303; load factors are limit and dimensionless.
2. **Category** — FAR 23 (normal/utility/acrobatic/commuter), *or* the concept-mode
   caveat: an unverified extrapolation above the FAR 23 calibration band, listing
   the specific applicability exceedances from `far23_applicability()`.
3. **Verification status** — the FAR 23 GA path is oracle-locked to Appendix A
   within ±0.1%; twin-turboprop cases are **closure-locked, not oracle-locked**
   (Appendix B is not bundled). Quote the `00_theory_sources.md` oracle-status
   wording rather than paraphrasing it.
4. **Modernized math** — `math.pi` and clean equations replace the source's
   `3.1416`, hence tolerance-based (±0.1%) rather than exact agreement.
5. **Approved corrections** — the three register entries, with citations.
6. **Known limitations** — the fuselage closure artifact (`CLOSURE_ARTIFACT_CAVEAT`, fallback path only) and assumed spar stations; *standard
   simplified* control-surface distributions; wing and control-surface exports
   always carry the full case set regardless of the governing-set filter (M4-2
   case-identity gap); no ground-case distributed fuselage loads; no pressurization
   cases.
7. **Scope of this export** — full set vs. governing set, and the deselected IDs.
8. **Provenance** — tool version, `SCHEMA_VERSION`, project name/engineer/date/
   revision, and the generation timestamp.

**Determinism.** The timestamp is a caller-supplied argument
(`generated: Optional[str] = None`, omitted when `None`), never `datetime.now()`
inside the pure code — the GUI passes it. Two runs of the same project must
produce byte-identical `.tex`, or the tests become flaky and the diff between two
revisions becomes unreadable.

---

## 6. Sub-steps (dependency order)

Each sub-step ends with a green build (`ruff check sloads/ cli.py` clean, `pytest`
passing) and is independently reviewable.

**G8.1 — `report.py` → `report/` package.**
Mechanical move (`git mv` by the user, per the git rule) plus
`__init__.py` re-exports. Acceptance: zero changes to any importing module; full
suite green; no test edits needed. *Do this first and alone* — mixing it with new
code makes the diff unreviewable.

**G8.2 — Document-control fields (schema).**
Add optional `revision`, `checked_by`, `approved_by`, `description` to `Project`,
round-trip in `io.py`, bump `SCHEMA_VERSION` 34 → 35, add the fields to the
Project Dashboard / JSON editor. All default to `""`, so older files load
unchanged and the title page degrades gracefully when they are absent.
Regenerate `DATA_DICTIONARY.md`.

**G8.3 — `methods.py` + stamping (the backlog item's explicit ask).**
The statement, plus wiring it into every channel:
`io.load_cases_csv`, the sbeam CSV writers and `case_index_csv*` gain a
`header_comment: str = ""` parameter; the BDF writers extend their existing `$`
block; the zip gains `METHODS.txt`; `build_workbook` gains a `Methods` sheet.
Guard test `tests/test_methods_stamp.py` (modelled on `test_ultimate_contract.py`):
every channel carries the statement, and every stamped CSV still parses.

**G8.4 — `content.py` + `coverage.py`.**
The `ReportDocument` model and the builder that fills §§1–4 from a `Project` and
`registry.run_all_modules()`. The FAR coverage table. No LaTeX yet — this
sub-step is fully testable on its own.

**G8.5 — `latex.py` + `plots_tex.py`.**
The `.tex` renderer: preamble (`article`, `geometry`, `booktabs`, `longtable`,
`fancyhdr`, `pgfplots`, `hyperref`), LaTeX escaping of every user-supplied string
(project names contain `&`, `_`, `%`), the document-control block, and the three
pgfplots figures. Landscape or reduced font for the wide case-index table.

**G8.6 — `export/pdf.py` + Export page UI.**
Engine discovery (`tectonic` → `latexmk` → `pdflatex`, first found), compile in a
temp dir, return bytes; surface engine/compile failure as a caption, never an
exception. A new **Summary report** section on `app/views/export_report.py` —
`.tex` download always, `.pdf` download when an engine is available, plus the
report and `METHODS.txt` in the zip bundle. *No new nav entry*: Phase 6's
direction is consolidation, and the Export page is already the hand-off page. (The
alternative — a dedicated `summary_report` workflow step — is noted here and
rejected; revisit only if the section outgrows the page.)

**G8.7 — Doc sync + close-out.**
`SUMMARY_REPORT.md` (reconcile the standard with what shipped — any content rule
the implementation forced a change to updates the standard, not just the code),
`PROGRAM_SPEC.md` (the report as an export channel), `PROJECT_GUIDE.md §4`
(package layout + the `export/pdf.py` I/O exemption), `GUI_design.md` /
`GUI_USER_GUIDE.md` (the new Export section), `20_theory/00_theory_sources.md`
(coverage-table provenance: User's Guide Table 2.2), backlog → history,
`CHANGELOG.md`. The LaTeX toolchain terms (tectonic, pgfplots, longtable,
fancyhdr, booktabs, hyperref, latexmk, …) are already seeded in `cspell.json`,
which was created 2026-08-03 — add any further new terms there as usual.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| **CSV `#` comment lines break a consumer.** `pandas.read_csv` needs `comment="#"`; the workbook builder and the Export page's `DictReader` currently read these strings back. | Audit every in-repo reader in G8.3 (`export/workbook.py::_csv_to_df`, `export_report.py` case-index preview, tests) and fix in the same commit. Guard test asserts a stamped CSV round-trips to the same rows as an unstamped one. Keep the block to ≤5 lines. |
| **No TeX engine on the machine / on a future Streamlit Cloud deploy.** | By design (G8-1): `.tex` always downloads, PDF is best-effort, the bundle is complete without it. UI states which engine was used or why there is none. |
| **`tectonic`'s first run downloads its package bundle** (needs network, then caches). | Documented in the UI hint and the user guide. Never invoked during tests except the opt-in compile test. |
| **`report.py` → package move churn.** | Isolated as G8.1, back-compat re-exports, no test edits — if the suite needs edits, the move was wrong. |
| **A wide case index overflows the page.** | `longtable` + small font + landscape for that table; cap the columns to the ones an analyst needs, with the full set in the companion CSV. |
| **Report drifts from the GUI numbers.** | The report calls the same pure builders the pages do (`run_all_modules`, `build_critical`, `governing_loads_table`, `build_vn_diagram`); it must not recompute anything itself. A test asserts the report's governing-load figures equal `governing_loads_table()`'s. |
| **Scope creep into calc.** | Invariant test: the Appendix A oracle suite and `test_ultimate_contract.py` are untouched and pass throughout. |

---

## 8. Tests

| File | Asserts |
|------|---------|
| `tests/test_report_content.py` | The `ReportDocument` built from `examples/ga6_normal` carries all five sections; weights/speeds/geometry cells equal the project's values; the governing-case count equals `build_critical().selected()`; sections degrade (not raise) when a slice is absent. |
| `tests/test_far_coverage.py` | Every reg in the static table is either covered by a real `far_reference` from the GA fixture or classified with a reason; no reg is silently dropped; an unflapped project marks 23.345 not-applicable. |
| `tests/test_report_latex.py` | `.tex` renders for the GA and both concept fixtures; LaTeX specials in a project name are escaped; the VA corner point appears in the V-n `\addplot` coordinates; `-ULT` markers and the `SF` column are present; the concept caveat appears **only** in the concept fixtures; two renders are byte-identical. |
| `tests/test_methods_stamp.py` | The statement reaches CSV, BDF, `METHODS.txt`, the workbook sheet and the report; stamped CSVs parse to unchanged rows; the concept caveat and the fuselage closure-artifact caveat are present when applicable. |
| `tests/test_pdf_compile.py` | `skipif` no engine: compiles the GA report, asserts `%PDF-` magic and ≥1 page. Skipped in CI by design. |
| `tests/test_views_smoke.py` (extend) | The Export page's new section renders without exception when every slice is absent. |
| Unchanged | Every Appendix A oracle test and `test_ultimate_contract.py` — the invariant. |

---

## 9. Definition of done

- Every box in [`SUMMARY_REPORT.md §6 Conformance`](../10_standard/SUMMARY_REPORT.md)
  is ticked, each by a named test.
- `sloads/report/` package in place, all prior imports working, suite green.
- The report renders for `examples/ga6_normal`, the twin fixture and both concept
  fixtures; PDF compiles locally with `tectonic`.
- The methods statement is present in **every** export channel, guard-tested.
- No calc change: Appendix A oracles and the ultimate-load contract pass unchanged.
- `ruff` clean; new domain terms in `cspell.json`.
- Six doc artifacts synced (`PROGRAM_SPEC`, `PROJECT_GUIDE`, `GUI_design` /
  `GUI_USER_GUIDE`, `00_theory_sources`, backlog → history, `CHANGELOG`).
- Backlog entry removed, history entry added, `[Unreleased]` changelog entry added
  — same session, per the lifecycle rule.

---

## 10. Open questions for the next session

1. **Report units** — ***Resolved 2026-08-03: honour the user's selection.*** The
   report (and the whole export bundle, sbeam BDF included) renders in the system
   the user chose — GUI toggle, persisted project field, CLI `--units` override,
   default Imperial. SI markers (`N-ULT`, `Nm-ULT`, `Pa-ULT`), no dual display,
   KEAS/altitude unconverted, unit system stated on the title page and in-band in
   every companion file. The standard is `../10_standard/SUMMARY_REPORT.md` §3.5;
   the enabling work (project field, CLI flag, unit-aware BDF/CSV writers) is
   backlog **M4-20** and is a prerequisite for G8's conformance tests.
2. **`revision` semantics** — a free-text field the user types, or an
   auto-incrementing counter stored in the project? Recommendation: **free text**,
   with a revision-history table the user maintains.
3. **Engine preference order** — `tectonic` first (self-contained, already
   installed) vs. `latexmk`/`pdflatex` first when a full TeX Live exists.
   Recommendation: **tectonic first**, overridable by an env var.
