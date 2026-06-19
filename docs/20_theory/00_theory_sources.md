# Theory & Equation Sources

Every load equation in `farloads/` traces back to a printed source. This file is
the map from "the number in the code" to "the page it came from". **Per the
project's documentation requirement, cite the source in the code and the test
whenever you port or change a calculation** (see `CLAUDE.md`).

## Authoritative references (in `reference/`)

| Short name | File | Role |
|------------|------|------|
| **Reference 1** | `reference/FAR23 loads (1).pdf` (371 pp) | McMaster's theory manual — the source of truth for **equations** *and* the **regression oracle**. Appendix A (6-place GA single) p131; Appendix B (10-place twin turboprop) p251; Appendix C `.BAS` source p373. |
| **FAA User's Guide** | `reference/ADA324952.pdf` (DOT/FAA/AR-96/46) | Module data-flow reference (Table 2.2) — which module consumes which upstream quantity. |
| **Brochure** | `reference/FAR-23-Loads-Brochure-2023.pdf` | Product overview / context. |

## How to cite

- **In test code:** keep the manual's printed figure *and* a page citation next
  to each assertion, so drift is traceable. The math is modernised (`math.pi`,
  clean equations, not the BASIC's `3.1416`), so the printed figures are
  **tolerance-based** oracles — `math.isclose(..., rel_tol=1e-3)` (±0.1%), exact
  equality only for integer/dimensionless quantities. See `PROJECT_GUIDE.md §6`.
- **In module code:** when a constant or formula is non-obvious, comment it with
  the FAR section (e.g. `23.361(a)(1)`) and/or the Reference 1 page.

## Per-module equation citations

Add a row here as each module is ported, pointing to the Reference 1 chapter/page
its equations come from and the Appendix A/B figures its test checks against.

| Module | `.BAS` source | Reference 1 location | Oracle (appendix figures) |
|--------|---------------|----------------------|---------------------------|
| `engine` (ENGLOADS) | `ENGLOADS.BAS` | Engine-mount loads chapter | Appendix A p131 / Appendix B p251 |
