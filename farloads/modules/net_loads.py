"""Net wing loads along the 25% chord, from NETLOADS.BAS.

NETLOADS forms the net wing load distribution as the algebraic sum of the air
loads (AIRLOADS) and the inertia loads (WINGINER) at each wing station (FAR
23.301(b): air and inertia loads in equilibrium). This is the headline structural
deliverable -- the spanwise net shear, bending moment and torsion (root values
size the wing). The inertia load factors are entered so the inertia opposes the
air load, so the net is a direct sum (NETLOADS.BAS lines 1560 ``A(I,J) =
A(I-14,J) + A(I-7,J)``).

For each critical condition the air-load distribution is evaluated at that
condition's wing ``CL`` and speed (read from the FLTLOADS ``envelope.vn`` point,
the C3-before-SELECT bridge) and the inertia distribution at its ``Nz``/``Nx``/
unbalanced-rolling-moment; the two are summed station-by-station.

Reference: NETLOADS.BAS (Appendix C p461-463), Ref 1 Ch 14; worked example
Appendix A "Net Loads, Case 22 PHAA" p222 (root Sz +5837, Mxx +455555,
Myy -60940, Mzz -81483) and "Case 160 ACCEL ROLL" / "Case 138 TORS".
"""

from __future__ import annotations

from typing import Dict, List

from ..models import (
    ConditionResult,
    LoadsResult,
    LoadValue,
    ModuleResult,
    Project,
    WingLoadCase,
    WingLoadResult,
    WingStationLoad,
)
from ..registry import register
from .airloads import air_load_distribution
from .wing_inertia import _resolve_case, build_wing_inertia, inertia_units, wing_inertia_distribution


def _sum_stations(air: WingStationLoad, inertia: WingStationLoad) -> WingStationLoad:
    """Algebraic sum of an air and inertia station load (NETLOADS.BAS line 1560)."""
    return WingStationLoad(
        x=air.x, y=air.y, z=air.z,
        fx=air.fx + inertia.fx, fz=air.fz + inertia.fz,
        sx=air.sx + inertia.sx, sz=air.sz + inertia.sz,
        mxx=air.mxx + inertia.mxx, myy=air.myy + inertia.myy, mzz=air.mzz + inertia.mzz,
    )


def _air_cl_v(project: Project, case: WingLoadCase):
    """Operating wing CL and speed for a case (explicit, else from envelope.vn)."""
    cl, v = case.cl, case.v_eas_kt
    if (cl is None or v is None) and case.case is not None and project.envelope is not None:
        vp = next((p for p in project.envelope.vn if p.case == case.case), None)
        if vp is not None:
            cl = cl if cl is not None else vp.cl
            v = v if v is not None else vp.v_eas_kt
    if cl is None or v is None:
        raise ValueError(
            f"net wing case '{case.name}' needs cl/v_eas_kt (explicit or via a "
            "'case' reference into Project.envelope.vn)"
        )
    return cl, v


def build_net_loads(project: Project) -> LoadsResult:
    """Compute the air, inertia and net wing-load distributions for every case."""
    wm = project.wing_mass
    if wm is None:
        raise ValueError("Project has no 'wing_mass' inputs for the net_loads module")
    if project.geometry is None or project.geometry.by_name(wm.surface) is None:
        raise ValueError(f"net_loads needs a '{wm.surface}' geometry surface")
    if project.aero is None or project.aero.by_name(wm.surface) is None:
        raise ValueError(f"net_loads needs a '{wm.surface}' aero surface (AIRLOADS)")
    if not wm.cases:
        raise ValueError("net_loads needs at least one load case")

    geom = project.geometry.by_name(wm.surface)
    aero = project.aero.by_name(wm.surface)
    units = inertia_units(geom, wm)

    air_results: List[WingLoadResult] = []
    inertia_results: List[WingLoadResult] = []
    net_results: List[WingLoadResult] = []
    for case in wm.cases:
        cl, v = _air_cl_v(project, case)
        air = air_load_distribution(geom, aero, cl, v, wm.wrp_waterline, wm.dihedral_deg)
        air.case = case.name
        inertia = wing_inertia_distribution(geom, wm, _resolve_case(project, case), units)
        net = WingLoadResult(case=case.name, nz=inertia.nz, nx=inertia.nx,
                             stations=[_sum_stations(a, i) for a, i in zip(air.stations, inertia.stations)])
        air_results.append(air)
        inertia_results.append(inertia)
        net_results.append(net)
    return LoadsResult(wing_air=air_results, wing_inertia=inertia_results, wing_net=net_results)


def wing_load_rows(results: List[WingLoadResult]) -> List[Dict[str, str]]:
    """One CSV row per station per case (root->tip), the canonical wing-load shape."""
    rows: List[Dict[str, str]] = []
    for r in results:
        for s in r.stations:
            rows.append({
                "Case": r.case,
                "X": f"{s.x:.3f}", "Y": f"{s.y:.3f}", "Z": f"{s.z:.3f}",
                "Fx": f"{s.fx:.1f}", "Fz": f"{s.fz:.1f}",
                "Sx": f"{s.sx:.1f}", "Sz": f"{s.sz:.1f}",
                "Mxx": f"{s.mxx:.0f}", "Myy": f"{s.myy:.0f}", "Mzz": f"{s.mzz:.0f}",
            })
    return rows


MODULE_NAME = "net_loads"


def run(project: Project) -> ModuleResult:
    """Run NETLOADS: net = air + inertia at each wing station, per condition."""
    loads = build_net_loads(project)
    conditions: List[ConditionResult] = []
    for r in loads.wing_net:
        root = r.stations[0]
        conditions.append(ConditionResult(
            title=f"Net wing loads: {r.case} (Nz={r.nz:g}, Nx={r.nx:g})",
            far_reference="23.301",
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


# Re-export for the registry import side effect (build_wing_inertia used by callers).
__all__ = ["build_net_loads", "wing_load_rows", "run", "build_wing_inertia"]
