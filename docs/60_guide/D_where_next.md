# Appendix D — Where next

The oracle GUI is deliberately the smaller of the two front-ends: the
original suite's inputs, and nothing this replication added. Everything you
entered here is fully understood by the main application —

```bash
.venv/bin/streamlit run app/Home.py
```

— and the project file needs no conversion: open the same
`<name>.project.json` there and the airplane arrives intact. The
task-oriented guide to the full application is
[`GUI_USER_GUIDE.md`](../10_standard/GUI_USER_GUIDE.md).

## What the full application adds

- **Plots.** The V-n envelope drawn, spanwise load diagrams, planform and
  configuration sketches — the pictures the oracle GUI's tables imply.
- **Spanwise tail distributions and the export bridge.** Distributed
  per-component loads on a load reference axis and the **sbeam solver
  decks** (`FORCE`/`MOMENT` bulk data with verified equilibrium) — the
  bridge from loads to structural sizing.
- **The workbook and report.** Whole-project exports: every module's
  results in one workbook, and the formatted loads report.
- **Concept mode.** The superset for airplanes beyond the FAR 23 band —
  concept configurations, supplemental FAR 25 cases, applicability
  flagging — which reduces exactly to what you used here on a conforming
  GA input.
- **The full input surface.** Fields the original suite never had (load
  reference axes, distributed masses, rotor records, declared design
  rates) — each one visible in this guide's generated field tables as
  `sloads`-origin, and each editable there.

## When to move over

Stay here while the question is *"what are this airplane's FAR 23 loads,
as the original suite would compute them?"* — the oracle GUI answers it
with the smallest possible input surface and the printed-oracle pedigree
of [Appendix A](A_worked_single.md). Move over when you need the loads
*delivered* somewhere: plotted, distributed on a beam axis, exported to a
solver, bound into a report — or when the airplane itself outgrows the
FAR 23 band. Your project file moves with you, unchanged, in both
directions.
