"""Wing inertia loads along the 25% chord, from WINGINER.BAS.

WINGINER computes the spanwise inertia load, shear, bending moment and torsion of
the wing (FAR 23.301(b): the air loads must be balanced by the inertia forces of
each item of mass). The outboard wing-panel mass is modelled as an area density
that tapers linearly from root to tip; the root density is iterated until the
integrated panel mass equals the entered panel weight (WINGINER.BAS lines
690-880). Concentrated wing masses (gear, engine, fuel, stores) are added as
spanwise steps.

Three unit distributions are formed along the quarter chord (airplane axes):

* **1g vertical** -- ``Fz = W``; ``Sz`` cumulative; ``Mxx = Σ Sz·dy``; torsion
  ``Tyy = −Σ Sz·Δx25 − Σ W·(x50−x25)`` (lines 950-1110);
* **1g drag** -- ``Fx = W``; ``Sx`` cumulative; ``Mzz = Σ Sx·dy``; torsion from the
  mass Z offset ``Σ Sx·Δz`` (lines 1150-1310);
* **unit roll** (100 000 in-lb) -- ``Fz = W·Y·1e5/Iwxx`` with ``Iwxx = 2·Σ W·Y²``,
  integrated like the vertical case (lines 1350-1610).

For a condition ``(Nz, Nx, unbalanced rolling moment)`` they combine (lines
1740-1820): ``Fz = Nz·W + UNB/1e5·Fz_roll``, ``Fx = Nx·W``, and likewise for the
shears/moments; torsion ``Myy = Nz·Tyy + Nx·Tvyy + UNB/1e5·Tuyy``. The signs are
entered so the inertia acts opposite the air load (up and aft positive), i.e.
``Nz`` is the negative of the air-load load factor -- NETLOADS then *adds* air and
inertia.

Reference: WINGINER.BAS (Appendix C p455-458), Ref 1 Ch 13; worked example
Appendix A "Wing Inertia Loads" p217-221 (panel 165 lb, density ratio 0.95, rib
BL 23: root density 2.213 lb/ft²; case 138 Nz −2.54 Nx −0.1318 root Mxx −41041).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from ..models import (
    ConditionResult,
    LoadValue,
    ModuleResult,
    Project,
    SurfaceInput,
    WingLoadCase,
    WingLoadResult,
    WingMassInput,
    WingStationLoad,
)
from ..registry import register
from .wing_geometry import _interp_x

_DEG = 57.3  # WINGINER.BAS rad<->deg factor


@dataclass
class _InertiaUnits:
    """Per-strip mass distribution and the three unit inertia distributions.

    All lists are root->tip, one entry per strip. ``w`` is the strip mass (lb);
    the ``*_v`` are the 1g-vertical, ``*_d`` the 1g-drag and ``*_r`` the unit-roll
    (100 000 in-lb) cumulative distributions."""
    ye: List[float] = field(default_factory=list)
    c25x: List[float] = field(default_factory=list)
    z: List[float] = field(default_factory=list)
    w: List[float] = field(default_factory=list)
    sz_v: List[float] = field(default_factory=list)
    mxx_v: List[float] = field(default_factory=list)
    tyy_v: List[float] = field(default_factory=list)
    sx_d: List[float] = field(default_factory=list)
    mzz_d: List[float] = field(default_factory=list)
    tvyy_d: List[float] = field(default_factory=list)
    fz_r: List[float] = field(default_factory=list)
    sz_r: List[float] = field(default_factory=list)
    mxx_r: List[float] = field(default_factory=list)
    tyy_r: List[float] = field(default_factory=list)
    density_root: float = 0.0
    density_tip: float = 0.0


def _root_density(dA, ye, c, dy, ytip, wm: WingMassInput, ii: int):
    """Iterate the root area density until the panel mass equals the entered weight.

    Mirrors WINGINER.BAS lines 730-880 (a partial first-strip correction at the
    inboard rib, ±1% tolerance, 1e-5 density steps)."""
    dr = wm.tip_root_density_ratio
    rsta = wm.inboard_rib_y
    target = wm.panel_weight_lb
    span_out = ytip - rsta
    densr = 0.02
    w = [0.0] * len(ye)
    for _ in range(100000):
        tw = 0.0
        for i in range(ii, len(ye)):
            w[i] = dA[i] * densr * (1.0 - (ye[i] - rsta) * (1.0 - dr) / span_out)
            tw += w[i]
        # Subtract the part of the first strip inboard of the rib.
        d = dy / 2.0 - (ye[ii] - rsta)
        dw = d * c[ii] * densr
        tw -= dw
        w[ii] -= dw
        if 0.99 * target < tw < 1.01 * target:
            break
        if tw >= 1.01 * target:
            densr -= 0.00001
        else:
            densr += 0.00001
    return w, densr


def inertia_units(geom: SurfaceInput, wm: WingMassInput) -> _InertiaUnits:
    """Build the wing-panel mass distribution and the three unit inertia cases."""
    yroot = geom.leading_edge[0][1]
    ytip = geom.leading_edge[-1][1]
    h = geom.elements
    dy = (ytip - yroot) / h
    ye = [yroot + dy / 2 + j * dy for j in range(h)]
    c = [_interp_x(geom.trailing_edge, y) - _interp_x(geom.leading_edge, y) for y in ye]
    c25x = [_interp_x(geom.leading_edge, y) + 0.25 * cc for y, cc in zip(ye, c)]
    c50x = [_interp_x(geom.leading_edge, y) + 0.50 * cc for y, cc in zip(ye, c)]
    dA = [cc * dy for cc in c]
    z = [wm.wrp_waterline + math.tan(wm.dihedral_deg / _DEG) * y for y in ye]

    ii = next((i for i, y in enumerate(ye) if y >= wm.inboard_rib_y), 0)
    w, densr = _root_density(dA, ye, c, dy, ytip, wm, ii)

    u = _InertiaUnits(ye=ye, c25x=c25x, z=z, w=w,
                      density_root=int(144 * densr * 1000) / 1000,
                      density_tip=int(144 * wm.tip_root_density_ratio * densr * 1000) / 1000)

    iwxx = 2.0 * (sum(w[i] * ye[i] ** 2 for i in range(h))
                  + sum(cw.weight_lb * cw.y ** 2 for cw in wm.concentrated)) or 1.0
    fz_r = [w[i] * ye[i] * 100000.0 / iwxx for i in range(h)]
    u.fz_r = fz_r

    # Cumulative integration tip->root for the vertical, drag and roll cases.
    sz_v = [0.0] * h
    mxx_v = [0.0] * h
    tyy_v = [0.0] * h
    sx_d = [0.0] * h
    mzz_d = [0.0] * h
    tvyy_d = [0.0] * h
    sz_r = [0.0] * h
    mxx_r = [0.0] * h
    tyy_r = [0.0] * h
    sz_v[h - 1] = w[h - 1]
    sx_d[h - 1] = w[h - 1]
    sz_r[h - 1] = fz_r[h - 1]
    tyy_v[h - 1] = -w[h - 1] * (c50x[h - 1] - c25x[h - 1])
    tyy_r[h - 1] = -fz_r[h - 1] * (c50x[h - 1] - c25x[h - 1])
    for i in range(h - 2, -1, -1):
        sz_v[i] = sz_v[i + 1] + w[i]
        sx_d[i] = sx_d[i + 1] + w[i]
        sz_r[i] = sz_r[i + 1] + fz_r[i]
        mxx_v[i] = mxx_v[i + 1] + sz_v[i + 1] * dy
        mzz_d[i] = mzz_d[i + 1] + sx_d[i + 1] * dy
        mxx_r[i] = mxx_r[i + 1] + sz_r[i + 1] * dy
        tyy_v[i] = tyy_v[i + 1] - sz_v[i + 1] * (c25x[i + 1] - c25x[i]) - w[i] * (c50x[i] - c25x[i])
        tvyy_d[i] = tvyy_d[i + 1] + sx_d[i + 1] * (z[i + 1] - z[i])
        tyy_r[i] = tyy_r[i + 1] - sz_r[i + 1] * (c25x[i + 1] - c25x[i]) - fz_r[i] * (c50x[i] - c25x[i])

    # Concentrated wing masses (gear, engine, fuel, store) add spanwise steps to
    # the shears/moments/torsion of every strip inboard of the weight (WINGINER.BAS
    # lines 1180-1270, 1570-1610). The per-strip Fz/Fx stay panel-only; the weight
    # is a point load carried in the cumulative shear.
    for cw in wm.concentrated:
        fzcwt = cw.weight_lb * cw.y * 100000.0 / iwxx
        for i in range(h):
            if ye[i] < cw.y:
                sz_v[i] += cw.weight_lb
                mxx_v[i] += cw.weight_lb * (cw.y - ye[i])
                tyy_v[i] += cw.weight_lb * (c25x[i] - cw.x)
                sx_d[i] += cw.weight_lb
                mzz_d[i] += cw.weight_lb * (cw.y - ye[i])
                tvyy_d[i] += cw.weight_lb * (cw.z - z[i])
                sz_r[i] += fzcwt
                mxx_r[i] += fzcwt * (cw.y - ye[i])
                tyy_r[i] += fzcwt * (c25x[i] - cw.x)

    u.sz_v, u.mxx_v, u.tyy_v = sz_v, mxx_v, tyy_v
    u.sx_d, u.mzz_d, u.tvyy_d = sx_d, mzz_d, tvyy_d
    u.sz_r, u.mxx_r, u.tyy_r = sz_r, mxx_r, tyy_r
    return u


def wing_inertia_distribution(geom: SurfaceInput, wm: WingMassInput,
                              case: WingLoadCase, units: Optional[_InertiaUnits] = None
                              ) -> WingLoadResult:
    """Combine the unit inertia distributions for one condition's Nz/Nx/UNB."""
    u = units if units is not None else inertia_units(geom, wm)
    nz = case.nz if case.nz is not None else 0.0
    nx = case.nx if case.nx is not None else 0.0
    ur = case.unbal_moment / 100000.0
    stations: List[WingStationLoad] = []
    for i in range(len(u.ye)):
        stations.append(WingStationLoad(
            x=u.c25x[i], y=u.ye[i], z=u.z[i],
            fx=nx * u.w[i],
            fz=nz * u.w[i] + ur * u.fz_r[i],
            sx=nx * u.sx_d[i],
            sz=nz * u.sz_v[i] + ur * u.sz_r[i],
            mxx=nz * u.mxx_v[i] + ur * u.mxx_r[i],
            myy=nz * u.tyy_v[i] + nx * u.tvyy_d[i] + ur * u.tyy_r[i],
            mzz=nx * u.mzz_d[i],
        ))
    return WingLoadResult(case=case.name, nz=nz, nx=nx, stations=stations)


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
def _resolve_case(project: Project, case: WingLoadCase) -> WingLoadCase:
    """Fill Nz/Nx from the referenced V-n point when not given explicitly.

    The C3-before-SELECT bridge: ``Nz = −NZ`` and ``Nx = −DX/W`` come straight from
    the FLTLOADS ``envelope.vn`` point (inertia opposes the air load)."""
    if case.nz is not None and case.nx is not None:
        return case
    if case.case is None or project.envelope is None:
        raise ValueError(
            f"wing load case '{case.name}' needs explicit nz/nx or a 'case' "
            "reference into Project.envelope.vn"
        )
    vp = next((p for p in project.envelope.vn if p.case == case.case), None)
    if vp is None:
        raise ValueError(f"wing load case '{case.name}' references unknown V-n case {case.case}")
    nz = case.nz if case.nz is not None else -vp.nz
    nx = case.nx
    if nx is None:
        weight = _case_weight(project, vp.cg)
        nx = -vp.dx / weight if weight else 0.0
    return WingLoadCase(name=case.name, case=case.case, nz=nz, nx=nx,
                        unbal_moment=case.unbal_moment, cl=case.cl, v_eas_kt=case.v_eas_kt)


def _case_weight(project: Project, cg_name: str) -> float:
    if project.flight_loads is not None:
        for cg in project.flight_loads.cg_cases:
            if cg.name == cg_name:
                return cg.weight_lb
    return 0.0


MODULE_NAME = "wing_inertia"


def build_wing_inertia(project: Project) -> List[WingLoadResult]:
    """Compute the wing inertia distribution for every configured load case."""
    wm = project.wing_mass
    if wm is None:
        raise ValueError("Project has no 'wing_mass' inputs for the wing_inertia module")
    if project.geometry is None or project.geometry.by_name(wm.surface) is None:
        raise ValueError(f"wing_inertia needs a '{wm.surface}' geometry surface")
    if not wm.cases:
        raise ValueError("wing_inertia needs at least one load case")
    geom = project.geometry.by_name(wm.surface)
    units = inertia_units(geom, wm)
    return [wing_inertia_distribution(geom, wm, _resolve_case(project, c), units) for c in wm.cases]


def run(project: Project) -> ModuleResult:
    """Run WINGINER against a :class:`Project`'s wing-mass inputs."""
    results = build_wing_inertia(project)
    conditions: List[ConditionResult] = []
    for r in results:
        root = r.stations[0]
        conditions.append(ConditionResult(
            title=f"Wing inertia loads: {r.case} (Nz={r.nz:g}, Nx={r.nx:g})",
            far_reference="23.301(b)",
            values=[
                LoadValue("Root shear Sz", root.sz, "lb"),
                LoadValue("Root bending Mxx", root.mxx, "lb-in"),
                LoadValue("Root torsion Myy", root.myy, "lb-in"),
                LoadValue("Root drag shear Sx", root.sx, "lb"),
                LoadValue("Root chord bending Mzz", root.mzz, "lb-in"),
            ],
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
