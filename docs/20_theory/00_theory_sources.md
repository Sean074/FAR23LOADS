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
| `weight_estimate` (WTESTIMA) | `WTESTIMA.BAS` | Ch 2; Appendix C p374-376 (`K`, fuel/component/engine-weight correlations; UG Tables 3.1/3.2) | Appendix A p133 (MTOW 3468, empty 2150, component breakdown) |
| `weight_onecg` (WTONECG) | `WTONECG.BAS` | Ch 4; Appendix C p377-381 (CG `S2/S1`; parallel-axis inertias ÷144·g; principal-axis rotation) | Appendix A p136 (aft gross: weight 3400, XBAR 84.999, ZBAR 92.579, IXX/IYY/IZZ 1201.5/2058.2/3022.8 slug-ft²) |
| `wing_geometry` (WINGGEOM) | `WINGGEOM.BAS` | Ch 5; Appendix C geometry subroutine p409-410 (strip sum `A=ΣC·dy`, `MAC=ΣC²·dy/A`, `XLEMAC=XBAR−MAC/2`, `AR=(2·Ytip)²/2A`) | Appendix A p141 (wing: AREA/SIDE 13257, MAC 69.246, YLE(MAC) 87.854, XLE(MAC) 63.641, AR 6.095) |
| `weight_envelope` (WTENV) | `WTENV.BAS` | Ch 3 (`X(limit)=XLEMAC+pct·MAC/100`; ballast `WB=WL−WA`, `XB=(WL·XL−WA·XA)/WB`) | Ch 3 p21-22 (stations 85.1/77.49/72.64; min flight 2063@73.09; max load 3322@84.56; ballast wts 78/418/158). Aft-gross ballast station is the exact moment balance (~108.5); the manual hand-rounded to 103.7 (limit station 85.0 vs 85.107). |
| `structural_speeds` (STRSPEED) | `STRSPEED.BAS` | Ch 6 (`n=2.1+24000/(W+10000)`; `VC_min=Kc·√(W/S)`; `VD=max(Kd·VC, 1.25·VC)`; `VA=VS·√n`; `VF=max(1.4VS, 1.8VSF)`; atmosphere `a=29.02436√(T+459.4)`) | Appendix A V-n table (VA 121.3, VC 170, VD 212.5, VF 105.5; n +3.8/−1.52; MC 0.323, MD 0.403 @ 12000 ft; S = 2·13257/144 = 184.1 ft²). VD uses the 1.25·VC floor (Kd·VC=238 reported as recommended). |
| `mach_limit` (MACHLIM) | `MACHLIM.BAS` (Appendix C p393-394) | Ch 6 (`MNE=0.9·MD`; `MFC=1.2·MD`; `V(M,EAS)=M·a·√σ`; shared `standard_atmosphere`) | Appendix A p160 (MC 0.323, MD 0.403, shoulder 12000 → 18000 ft: MNE 0.3627, MFC 0.4836; V(MC) 170.16→150.77, V(MD) 212.31→188.11). Program used a=29.02 vs the shared helper's 29.02436 (~0.01%). |
