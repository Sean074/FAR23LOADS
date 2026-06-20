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
| `airloads` (AIRLOADS + TAU) | `AIRLOADS.BAS` / `TAU.BAS` | Ch 7 p46-47 (Schrenk: additive `c·cl=½(mo·c/Mo+4S/πB·√(1−(2y/B)²))` for CL=1; basic `Awo=Σmo·c·ac·dy/Σmo·c·dy`, `c·cl_b=(mo/2)(ac−Awo)c`; combine `c·cl=c·cl_a·CL+c·cl_b`; wing slope `M=mo/(1+mo/πAR·(1+τ))` Peery 9.59); TAU quartic curve-fit p407 (ANC(1) 1938) | Appendix A p161-162 (additive `CC(LA1)` elem 1/10/20 = 91.05576 / 69.44847 / 31.82978, `C(LA1)` elem 1 = 0.9275981, additive ∫ → CL 1.00061; basic `Awo` = 3.988146, `CC(lb)` elem 1 = +5.09762, `Clb` elem 1 = 0.05193). Modernized π vs the BASIC's 3.1416 → ±0.1% drift. |
| `flight_envelope` (FLTLOADS) | `FLTLOADS.BAS` (Appendix C p421-428) | Ch 8 (balance subr 3900: `CL=C0+ΣCi·αⁱ·G/Gmn`, `CD=ΣDi·CLⁱ`, `CM=M0+ΣMi·αⁱ·G/Gmn`; `L=CL·Q·S`, `Q=V²/295`; rotate `LZ=L·cosα+D·sinα`, `DX=D·cosα−L·sinα`; balance `LT=[M(W+F)+LZ(Xcg−Xw)−DX(Zcg−Zw)]/(XT−Xcg)`, `NZ=(LZ+LT)/W`; iterate α to NZ then Q to Mach-adjusted stall; Glauert `G=1/√(1−M²)`; CLmax-vs-Mach 5th-order fit; gust subr 4864 FAR 23.341: `μ=2(W/S)/(ρ·c̄·a·g)`, `Kg=.88μ/(5.3+μ)`, `NZ=1+NG·Kg·Ude·V·a/(498·W/S)`, `Ude` 50 fps @ VC / 25 @ VD) | Appendix A "V-n Data" p179-180 (cruise CG1: STALL 1G V 61.4 / LZW 3266 / LT 132; MAN A V 121.3 / NZ +3.80 / LZW 12419 / LT 493; GUST +C NZ +3.96; AC ROLL LT 412; CG2 MAN A LZW 12970 / LT −59). AoA converges to ±0.005 NZ → ~0.5% noise on low-load points; LT + corner speeds/factors match tightly. Speed of sound uses the program's 518.688 (vs shared 518.4). |
| `airloads` (load distribution) | `AIRLOADS.BAS` subr 4500 (Appendix C, lines 4600-5060) | Ch 12 (operating section lift `kcl=cl_basic+CL·cl_add`; induced angle `ai=(α−Awo+refang)−kcl/mo`, induced drag `cdi=kcl·ai/57.3`, `cd=cdi+CDO`; strip `L=kcl·c·dy·Q/144`, `D=cd·c·dy·Q/144`, `ML=CM·c²·dy·Q/144`, `Q=V²/295`; rotate by `α_rw2wl=CL/M−Awo`; integrate tip→root `Sz,Mxx=ΣSz·dy,Tyy=−ΣSz·Δx25`, `Sx,Mzz=ΣSx·dy,Tvyy=ΣSx·Δz`, `Trq=ΣML`; `Myy=Tyy+Tvyy+Trq`) | Appendix A "Airloads for Case 22 PHAA" p206 (CL 1.52, V 117.4: root FZ +466, SZ +6470, MXX +516955, MYY −79003, MZZ −91283; tip MYY −198) — exact with `tau=0.05` (the manual's printed wing TAU). |
| `wing_inertia` (WINGINER) | `WINGINER.BAS` (Appendix C p455-458) | Ch 13 (panel area density tapered root→tip, root density iterated to panel weight; 1g vertical `Fz=W, Sz=ΣW, Mxx=ΣSz·dy, Tyy=−ΣSz·Δx25−ΣW·(x50−x25)`; 1g drag `Mzz=ΣSx·dy, Tvyy=ΣSx·Δz`; unit roll `Iwxx=2ΣW·Y²`, `Fz=W·Y·1e5/Iwxx`; combine `Fz=Nz·W+UNB/1e5·Fz_roll`, `Myy=Nz·Tyy+Nx·Tvyy+UNB/1e5·Tuyy`; concentrated weights add inboard steps) | Appendix A "Wing Inertia Loads" p217-221 (panel 165 lb, ratio 0.95, rib BL 23 → root 2.213 / tip 2.102 lb/ft²; unit-vert root Mxx −16158; case 138 Nz −2.54 Nx −0.1318 root Mxx −41041, Myy +11161, Mzz −2130). |
| `net_loads` (NETLOADS) | `NETLOADS.BAS` (Appendix C p461-463) | Ch 14 (net = air + inertia per station, `A(I)=A_air(I)+A_inertia(I)`; inertia entered with signs opposing the air load) | Appendix A "Net Loads, Case 22 PHAA" p222 (root Sz +5837, Mxx +455555, Myy −60940, Mzz −81483 = air p206 + inertia case 22 Nz −3.8 Nx +0.6065). |
| `export/sbeam_bridge` (C4 export bridge — **no `.BAS` oracle**) | — (renderer; card style from `sbeam/results/load_export.py`) | Ref 1 Ch 14 (the net wing load being exported); NASTRAN bulk data: `FORCE`/`MOMENT` (`F·(N1,N2,N3)`, comma free-field, unit scale), `GRID`/`CBAR`/`PBAR`/`MAT1`/`SPC1`, `SOL 101`. Nodal load = increment of the cumulative NETLOADS column (`dFz[i]=sz[i]−sz[i+1]`), so `ΣdFz=sz_root` and `ΣdFz·(y−y₀)=mxx_root` exactly under the WINGINER quadrature (`y[i]−y[0]=i·dy`). | **No printed oracle.** Closure: re-summed FORCE/MOMENT = NETLOADS root totals (exact); a self-contained free-field reader round-trips the cards; the stick deck parses **and solves SOL 101** in the real sbeam (manual step). |
| `configuration` (Step C5 — **no `.BAS` oracle**) | — (modern addition) | Ref 1 Ch 5 (trapezoidal wing: `b=√(AR·S)`, `c_root=2S/(b(1+λ))`, `MAC=⅔c_root(1+λ+λ²)/(1+λ)`, `Y_MAC=(b/6)(1+2λ)/(1+λ)`; MAC/XLEMAC obtained via the WINGGEOM strip integrator, not re-derived); Ch 8 (tail-volume neutral point `V_H=S_t·l_t/(S_w·MAC)`, `h_n=h_acw+V_H·(a_t/a_w)·(1−dε/dα)`, defaults `h_acw=0.25`, `a_t/a_w=1`, `1−dε/dα=0.6`); landing-gear tip-back `atan((x_main−x_cg)/h_cg)` and overturn `atan(h_cg/d)` (standard gear geometry; no FAR oracle). | **No printed oracle.** Sanity: analytic-vs-WINGGEOM-strip MAC ±0.1%; Appendix A trapezoid plausibility — MAC 69.246 / MAC butt line 87.854 within ±10% (the real wing has an inboard strake). |
