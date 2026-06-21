"""Control-surface tab loads, from TABLOADS.BAS (Reference 1 Ch 18).

Tabs are designed for full deflection at VC at the shoulder point (the highest
KEAS / greatest Mach), with a trapezoidal chordwise distribution per CAM
3.224-1(b) (leading-edge loading twice the trailing edge). The tab lift slope is
from NACA TN 353 + Abbott & von Doenhoff Fig 98::

    E    = MACTAB / CAIRFOIL                  (tab chord / host-airfoil chord)
    M    = 0.0446 * (1 - E)                   per deg
    LTAB = M * DELTATAB * Q * STAB / 144,     Q = VC^2 / 295   (STAB in sq in)

The chordwise pressures are ``W = LTAB / 1.5 / STAB``, ``LE = 2W``, ``TE = W``.
The lift due to host-surface CL is neglected (the tab/airfoil chord ratio ~0.12 is
tiny). VC comes from ``Project.speeds`` (STRSPEED); each tab's geometry is a
``TabSpec`` in ``Project.tab_loads``.

Reference: TABLOADS.BAS (Appendix C p490-491); Ref 1 Ch 18 p113-114; worked
example Appendix A "Tab Loads" p202 (h-tail tab: E 0.17735, LTAB 84.62 lb,
LE 0.4992 / TE 0.2496 lb/in^2).
"""

from __future__ import annotations

from typing import List, NamedTuple

from ..models import (
    ConditionResult,
    ControlSurfaceLoadResult,
    ControlSurfaceStation,
    LoadValue,
    ModuleResult,
    Project,
    TabSpec,
)
from ..registry import register

MODULE_NAME = "tab"

_SQIN_PER_SQFT = 144.0


class TabResult(NamedTuple):
    """One tab's load + trapezoidal chordwise pressures (TABLOADS.BAS)."""
    chord_ratio: float          # E
    load_lb: float              # LTAB
    le_pressure_psi: float
    te_pressure_psi: float


def tab_load(vc: float, mac_in: float, area_sqin: float, airfoil_chord_in: float,
             deflection_deg: float) -> TabResult:
    """One tab's load and chordwise pressures (TABLOADS.BAS lines 250-330)."""
    if airfoil_chord_in <= 0 or area_sqin <= 0:
        raise ValueError("tab area and host-airfoil chord must be positive")
    q = vc ** 2 / 295.0
    e = mac_in / airfoil_chord_in
    m = 0.0446 * (1.0 - e)
    ltab = m * deflection_deg * q * area_sqin / _SQIN_PER_SQFT
    w = ltab / 1.5 / area_sqin
    return TabResult(chord_ratio=e, load_lb=ltab,
                     le_pressure_psi=2.0 * w, te_pressure_psi=w)


def _surface_tag(spec: TabSpec) -> str:
    return f"tab:{spec.surface}"


def build_tabs(project: Project) -> List[ControlSurfaceLoadResult]:
    """Each tab's load as a control-surface result record (trapezoid LE = 2x TE)."""
    if project.tab_loads is None:
        raise ValueError("tab needs the 'tab_loads' input slice")
    if project.speeds is None:
        raise ValueError("tab needs 'speeds' (STRSPEED VC)")
    vc = project.speeds.chosen_vc or 0.0
    if vc <= 0:
        from .structural_speeds import design_speed_values
        vc = design_speed_values(project, project.speeds).vc
    results: List[ControlSurfaceLoadResult] = []
    for spec in project.tab_loads.tabs:
        r = tab_load(vc, spec.mac_in, spec.area_sqin, spec.airfoil_chord_in,
                     spec.deflection_deg)
        results.append(ControlSurfaceLoadResult(
            surface=_surface_tag(spec), case=f"{spec.surface} tab", load_lb=r.load_lb,
            v_kt=vc, stations=[
                ControlSurfaceStation(x=0.0, psi=r.le_pressure_psi),
                ControlSurfaceStation(x=1.0, psi=r.te_pressure_psi)]))
    return results


def run(project: Project) -> ModuleResult:
    """Run TABLOADS: tab loads at full deflection at VC (FAR 23.409 / CAM 3.224)."""
    if project.tab_loads is None:
        raise ValueError("Project has no 'tab_loads' inputs for the tab module")
    if project.speeds is None:
        raise ValueError("tab needs 'speeds' (STRSPEED VC)")
    vc = project.speeds.chosen_vc or 0.0
    if vc <= 0:
        from .structural_speeds import design_speed_values
        vc = design_speed_values(project, project.speeds).vc
    conditions: List[ConditionResult] = []
    note = ("Full tab deflection at VC; trapezoidal chordwise distribution "
            "(LE = 2x TE) per CAM 3.224-1(b).")
    if project.is_concept:
        note += " Concept mode -- unverified extrapolation past the FAR23 band."
    for spec in project.tab_loads.tabs:
        r = tab_load(vc, spec.mac_in, spec.area_sqin, spec.airfoil_chord_in,
                     spec.deflection_deg)
        conditions.append(ConditionResult(
            title=f"{spec.surface} tab load",
            far_reference="23.409",
            values=[
                LoadValue("VC", vc, "kt(EAS)"),
                LoadValue("Tab chord ratio E", r.chord_ratio),
                LoadValue("Tab load", r.load_lb, "lb"),
                LoadValue("Tab LE pressure", r.le_pressure_psi, "lb/in^2"),
                LoadValue("Tab TE pressure", r.te_pressure_psi, "lb/in^2"),
            ],
            note=note,
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
