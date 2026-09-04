## Step 154 — The oracle report states the wing loads (tier L, 2026-09-01)

**Objective.** Give the oracle technical report its first load-bearing section: the wing
loads, as four subsections and a lettered appendix, built from the `wing_loads` step
(`AIRLOADS+WINGINER+NETLOADS`) without the report computing anything of its own.

**Agreed first.** Design note 44 §11, decisions **OR-48 … OR-56** and gates
**G-OR-20 … G-OR-26**, settled with the owner in session before any code.

**Deliverables.**
- `report/oracle_sections.py` — 3.1 wing input data, 3.2 the run register and sign
  convention, 3.3 the root loads assessed, 3.4 the net distributions, and Appendix B's
  station table. A step that renders as subsections titles them and does not number them;
  `build_section` numbers them through `subsection_number`, the one numbering owner.
- `report/oracle_content.py` — the `Appendix` slot type, `APPENDICES` with the input echo
  **reserved** and the wing appendix built, `appendix_letter`/`appendix_heading`/
  `appendix_plan`, and `subsection_ref` so a "3.1" in prose is composed rather than typed
  (F-R2, one level down).
- `report/content.py` — `Series.closed`, and `Units.load_value`/`plain_value`.
- `report/planform_tex.py` — an open path is drawn open; `planform_wing_lra` registered.

**Key decisions.**
- **The 25 % chord is the LRA for oracle loads.** The suite accumulates torsion about the
  local quarter chord and transfers it to the surface's entered axis at the delivery
  boundary. The report is a function of the oracle projection (OR-43), and that projection
  resets the entered axis — so an oracle report cannot print a 40 %-chord torsion for a
  project that enters one, which is what `ga6_normal` does. Every torsion names its axis.
- **The three span-load curves call AIRLOADS once each.** `CL = 0`, `1.0` and the aero set's
  own `stall_cl`; the report never combines the additive and basic distributions itself.
- **The flaps-down span load cannot be produced at all** — AIRLOADS does not model the lift
  discontinuity a deflected flap puts in the basic distribution — so it is stated absent with
  its reason rather than filled with the clean set, and the capability gap is filed
  as **#163**.
- **There is no tail-on lift coefficient in this suite.** The balance carries the tail load
  as a separate force rather than inside the coefficient, so the tail-off curve is drawn with
  the balanced conditions marked on it and the section says that, rather than implying a
  second curve exists.
- **SELECT's subset is the critical set.** No second criticality rule is invented for the
  report; 3.2, 3.3, 3.4 and Appendix B are four projections of one set, in one order.
- **The register says where its case list came from (OR-57, owner's review 2026-09-03).**
  Two paths reach a wing case set — the selection's search, and a list entered on the project,
  which wins when present — and the first draft of 3.2 claimed the first while `ga6_normal`
  runs the second: three entered cases against the six the selection names. The section now
  states which path produced the list, counts the V-n matrix by every dimension it enumerates
  (80 points over four CG cases, twenty conditions and one altitude), and tabulates every named
  condition against whether it was run, so PLAA, PMAA and NMAA are visible as named-not-run
  rather than absent without trace. The same review established that the fixture balances at
  sea level only while Appendix A names five of the six conditions at 12,000 ft — filed as
  **#164**, since adding the altitude renumbers every V-n case.

**Test.** Thirteen new gates in `tests/test_oracle_report.py`, including: every load column
in the section and the appendix carries `-ULT`; each root value equals the module's own LIMIT
result times that case's stated factor; the span-load series equal `schrenk_distribution`'s
own output at each target `CL`; the reference axis is emitted as an open path while the
outlines close; the four projections state one set of cases; and a project with no wing loads
states the absence in both the section and its appendix and still builds a complete document.
Three existing structural tests were restated rather than relaxed: a rendered section is now a
plan row, a builder's own subsection, or an appendix, so plan and document are paired **by
number** instead of by position.
