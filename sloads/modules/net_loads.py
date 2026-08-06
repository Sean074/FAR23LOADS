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
    MissingInputError,
    ConditionResult,
    LoadsResult,
    LoadValue,
    ModuleResult,
    Project,
    SurfaceInput,
    WingLoadCase,
    WingLoadResult,
    WingStationLoad,
)
from ..constants import ULTIMATE_FACTOR
from ..derived_geometry import sync_geometry_derived
from ..registry import register
from .airloads import air_load_distribution
from .wing_geometry import interp_x
from .wing_inertia import (
    _resolve_case,
    build_wing_inertia,
    inertia_units,
    resolve_wing_cases,
    wing_case_ref,
    wing_inertia_distribution,
)


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
        raise MissingInputError(
            f"net wing case '{case.name}' needs cl/v_eas_kt (explicit or via a "
            "'case' reference into Project.envelope.vn)"
        )
    return cl, v


def torsion_axis_label(pct: float) -> str:
    """The in-band axis label for a torsion stated about ``pct`` of chord.

    The original suite's quarter chord stays ``"25% chord"``; anything else is
    the surface's loads reference axis, e.g. ``"LRA 40% chord"``.
    """
    return "25% chord" if pct == 0.25 else f"LRA {pct * 100:g}% chord"


def to_loads_ref_axis(results: List[WingLoadResult],
                      geom: SurfaceInput) -> List[WingLoadResult]:
    """Transfer cumulative torsion from the 25% chord to the surface's LRA.

    The calc (AIRLOADS/WINGINER/NETLOADS) accumulates torsion about the local
    25%-chord line (oracle-locked); the beam model the deliverables apply to uses
    the surface's **loads reference axis** (``SurfaceInput.ref_axis_pct``,
    typically the 40-50%-chord elastic axis). This pure boundary transform moves
    each station's cumulative torsion to that axis:

        Myy_lra(y) = Myy_25(y) + Sz(y) * (x_lra(y) - x_25(y))

    (a station's torsion is the sum over outboard loads of ``fz_j*(x_axis - x_j)``
    -- WINGINER.BAS's ``-W*(x50-x25)`` convention -- so shifting the axis
    chordwise adds ``Sz`` times the shift; shears and bending ``Mxx``/``Mzz``
    are unchanged). Station ``x`` becomes the LRA coordinate and each result's
    ``torsion_axis`` is stamped. With ``ref_axis_pct == 0.25`` the input is
    returned unchanged -- the original quarter-chord reporting, so the FAR23
    oracles are unaffected.
    """
    pct = geom.ref_axis_pct
    if pct == 0.25:
        return list(results)
    axis = torsion_axis_label(pct)
    out: List[WingLoadResult] = []
    for r in results:
        stations: List[WingStationLoad] = []
        for s in r.stations:
            x_le = interp_x(geom.leading_edge, s.y)
            x_te = interp_x(geom.trailing_edge, s.y)
            x_lra = x_le + pct * (x_te - x_le)
            stations.append(WingStationLoad(
                x=x_lra, y=s.y, z=s.z, fx=s.fx, fz=s.fz, sx=s.sx, sz=s.sz,
                mxx=s.mxx, myy=s.myy + s.sz * (x_lra - s.x), mzz=s.mzz,
            ))
        out.append(WingLoadResult(case=r.case, nz=r.nz, nx=r.nx, stations=stations,
                                  case_ref=r.case_ref, safety_factor=r.safety_factor,
                                  torsion_axis=axis))
    return out


def wing_lra(project: Project) -> float:
    """The wing surface's loads-reference-axis chord fraction (0.25 when unset)."""
    wm = project.wing_mass
    geom = (project.geometry.by_name(wm.surface)
            if wm is not None and project.geometry is not None else None)
    return geom.ref_axis_pct if geom is not None else 0.25


def loads_ref_axis_results(project: Project,
                           results: List[WingLoadResult]) -> List[WingLoadResult]:
    """Resolve the project's wing surface and transfer ``results`` to its LRA.

    The render/export-boundary convenience over :func:`to_loads_ref_axis` (the
    same role ``report.py`` plays for the limit->ultimate factor): views and the
    sbeam bridge call this so every delivered wing torsion is stated about the
    surface's loads reference axis. Results pass through unchanged when the
    project has no resolvable wing surface or the LRA is the 25% chord.
    """
    wm = project.wing_mass
    geom = (project.geometry.by_name(wm.surface)
            if wm is not None and project.geometry is not None else None)
    if geom is None:
        return list(results)
    return to_loads_ref_axis(results, geom)


def build_net_loads(project: Project) -> LoadsResult:
    """Compute the air, inertia and net wing-load distributions for every case."""
    sync_geometry_derived(project)
    wm = project.wing_mass
    if wm is None:
        raise MissingInputError("Project has no 'wing_mass' inputs for the net_loads module")
    if project.geometry is None or project.geometry.by_name(wm.surface) is None:
        raise MissingInputError(f"net_loads needs a '{wm.surface}' geometry surface")
    if project.aero is None or project.aero.by_name(wm.surface) is None:
        raise MissingInputError(f"net_loads needs a '{wm.surface}' aero surface (AIRLOADS)")
    cases = resolve_wing_cases(project, wm)
    if not cases:
        raise MissingInputError(
            "net_loads needs at least one load case -- enter them in "
            "'wing_mass.cases' or run SELECT so they can be derived from "
            "envelope.critical")

    geom = project.geometry.by_name(wm.surface)
    aero = project.aero.by_name(wm.surface)
    units = inertia_units(geom, wm)

    air_results: List[WingLoadResult] = []
    inertia_results: List[WingLoadResult] = []
    net_results: List[WingLoadResult] = []
    for i, case in enumerate(cases):
        ref = wing_case_ref(project, i, case)
        # The wing case's limit->ultimate factor, minted once here (net_loads owns
        # the wing conditions -- no upstream CriticalCondition exists for them) and
        # copied onto all three families and the rendered ConditionResult so report
        # and export can never disagree (defect M4-13).
        sf = ULTIMATE_FACTOR
        cl, v = _air_cl_v(project, case)
        air = air_load_distribution(geom, aero, cl, v, wm.wrp_waterline, wm.dihedral_deg)
        air.case = case.name
        air.case_ref = ref
        air.safety_factor = sf
        inertia = wing_inertia_distribution(geom, wm, _resolve_case(project, case), units)
        inertia.case_ref = ref
        inertia.safety_factor = sf
        net = WingLoadResult(case=case.name, nz=inertia.nz, nx=inertia.nx,
                             stations=[_sum_stations(a, i) for a, i in zip(air.stations, inertia.stations)],
                             case_ref=ref, safety_factor=sf)
        air_results.append(air)
        inertia_results.append(inertia)
        net_results.append(net)
    return LoadsResult(wing_air=air_results, wing_inertia=inertia_results, wing_net=net_results)


def wing_load_rows(results: List[WingLoadResult]) -> List[Dict[str, str]]:
    """One CSV row per station per case (root->tip), the canonical wing-load shape.

    All loads are **LIMIT** (the oracle-traceable calc values), stated in-band by
    the ``Basis`` column so the basis travels with any table/CSV built from these
    rows (defect M4-15); the ``MyyAxis`` column likewise carries the torsion
    reference axis (25% chord as computed, or the LRA after
    :func:`to_loads_ref_axis`). The ULTIMATE deliverable is
    ``sbeam_bridge.span_load_csv``.
    """
    rows: List[Dict[str, str]] = []
    for r in results:
        for s in r.stations:
            rows.append({
                "Case": r.case,
                "X": f"{s.x:.3f}", "Y": f"{s.y:.3f}", "Z": f"{s.z:.3f}",
                "Fx": f"{s.fx:.1f}", "Fz": f"{s.fz:.1f}",
                "Sx": f"{s.sx:.1f}", "Sz": f"{s.sz:.1f}",
                "Mxx": f"{s.mxx:.0f}", "Myy": f"{s.myy:.0f}", "Mzz": f"{s.mzz:.0f}",
                "MyyAxis": r.torsion_axis,
                "Basis": "LIMIT",
            })
    return rows


MODULE_NAME = "net_loads"


def run(project: Project) -> ModuleResult:
    """Run NETLOADS: net = air + inertia at each wing station, per condition."""
    loads = build_net_loads(project)
    lra = wing_lra(project)
    conditions: List[ConditionResult] = []
    for r, r_lra in zip(loads.wing_net, loads_ref_axis_results(project, loads.wing_net)):
        root = r.stations[0]
        # The torsion label always names its reference axis: the oracle-traceable
        # 25%-chord value, plus the LRA-transferred value when the LRA differs.
        values = [
            LoadValue("Root shear Sz", root.sz, "lb", key="root_shear_sz"),
            LoadValue("Root bending Mxx", root.mxx, "lb-in", key="root_bending_mxx"),
            LoadValue("Root torsion Myy (25% chord)", root.myy, "lb-in", key="root_torsion_myy_25_pct_chord"),
        ]
        if lra != 0.25:
            values.append(LoadValue(
                f"Root torsion Myy ({torsion_axis_label(lra)})",
                r_lra.stations[0].myy, "lb-in", key="root_torsion_myy_lra"))
        values += [
            LoadValue("Root drag shear Sx", root.sx, "lb", key="root_drag_shear_sx"),
            LoadValue("Root chord bending Mzz", root.mzz, "lb-in", key="root_chord_bending_mzz"),
        ]
        conditions.append(ConditionResult(
            title=f"Net wing loads: {r.case} (Nz={r.nz:g}, Nx={r.nx:g})",
            far_reference="23.301",
            values=values,
            case_ref=r.case_ref,
            # Same per-case factor the sbeam export scales by, so the rendered and
            # exported ULTIMATE loads can never disagree (defect M4-13).
            safety_factor=r.safety_factor,
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)


# Re-export for the registry import side effect (build_wing_inertia used by callers).
__all__ = ["build_net_loads", "wing_load_rows", "run", "build_wing_inertia",
           "to_loads_ref_axis", "loads_ref_axis_results", "wing_lra",
           "torsion_axis_label"]
