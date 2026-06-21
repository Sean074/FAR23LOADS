"""Aileron loads, from AILERON.BAS (Reference 1 Ch 16).

The ailerons are sized for the *deflected* (unsymmetrical) rolling conditions of
FAR 23.455(a)(2); the symmetrical undeflected case is never critical (Ref 1 Ch 16
p105). The deflected load uses the CAM 3.222(c) simplified coefficient::

    LAIL = CL_ail * Q * SA,   CL_ail = 0.04 * DEFL,   Q = V^2 / 295

with the aileron area ``SA = SAFWD + SAAFT`` (sq ft) and the deflection schedule

    at VA:  DEFL                                  (full deflection)
    at VC:  (VA/VC) * DEFL                        23.455(a)(2)(ii)
    at VD:  0.5 * (VA/VD) * DEFL                  23.455(a)(iii) + CAM 3.222(b)(3)

evaluated for the up and the down throw; the largest up load and the largest down
load govern. The chordwise pressure is constant from the leading edge to the
hinge line and tapers to zero at the trailing edge, so the forward pressure is

    W = LAIL / (SAFWD + 0.5*SAAFT)     [lb/ft^2];   psi = W / 144

VA/VC/VD are read from ``Project.speeds`` (STRSPEED) -- the only upstream input
per UG Table 2.2; the aileron geometry is ``Project.aileron_loads``.

Reference: AILERON.BAS (Appendix C p450); Ref 1 Ch 16 p105-106; worked example
Appendix A "Critical Aileron Loads" p200 (down 271.44 lb @170 kt, up -180.96 lb
@170 kt; pressure +0.484 / -0.323 lb/in^2).
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
)
from ..registry import register
from .structural_speeds import design_speed_values

MODULE_NAME = "aileron"

_SQIN_PER_SQFT = 144.0


class AileronResult(NamedTuple):
    """Critical aileron loads + forward-of-hinge pressures (AILERON.BAS)."""
    down_load_lb: float
    down_speed_kt: float
    up_load_lb: float
    up_speed_kt: float
    down_pressure_psi: float    # forward of hinge line, lb/in^2
    up_pressure_psi: float
    hinge_chord_fraction: float  # SAFWD / SA (for the chordwise profile)


def aileron_loads(va: float, vc: float, vd: float, down_deg: float, up_deg: float,
                  area_fwd_hinge_sqft: float, area_aft_hinge_sqft: float) -> AileronResult:
    """Critical up/down aileron loads (AILERON.BAS lines 56-205).

    ``down_deg``/``up_deg`` are deflection magnitudes (the up throw is applied as a
    negative deflection). Returns the governing loads, the speeds they occur at and
    the constant forward-of-hinge pressures."""
    sa = area_fwd_hinge_sqft + area_aft_hinge_sqft
    if sa <= 0:
        raise ValueError("aileron area (SAFWD + SAAFT) must be positive")
    adeg = abs(down_deg)
    aupdeg = -abs(up_deg)

    def load(defl: float, v: float) -> float:
        return 0.04 * defl * sa * v ** 2 / 295.0

    # Deflection schedule per FAR 23.455 / CAM 3.222.
    cdeg, cupdeg = (va / vc) * adeg, (va / vc) * aupdeg
    ddeg, dupdeg = 0.5 * (va / vd) * adeg, 0.5 * (va / vd) * aupdeg

    down = [(load(adeg, va), va), (load(cdeg, vc), vc), (load(ddeg, vd), vd)]
    up = [(load(aupdeg, va), va), (load(cupdeg, vc), vc), (load(dupdeg, vd), vd)]
    down_load, down_v = max(down, key=lambda t: t[0])      # largest down load
    up_load, up_v = min(up, key=lambda t: t[0])            # largest (most negative) up load

    denom = area_fwd_hinge_sqft + 0.5 * area_aft_hinge_sqft
    w_down = down_load / denom
    w_up = up_load / denom
    return AileronResult(
        down_load_lb=down_load, down_speed_kt=down_v,
        up_load_lb=up_load, up_speed_kt=up_v,
        down_pressure_psi=w_down / _SQIN_PER_SQFT,
        up_pressure_psi=w_up / _SQIN_PER_SQFT,
        hinge_chord_fraction=area_fwd_hinge_sqft / sa,
    )


def _stations(pressure_psi: float, hinge_fraction: float) -> List[ControlSurfaceStation]:
    """Chordwise profile: constant ``pressure`` LE->hinge, linear to 0 at the TE."""
    return [
        ControlSurfaceStation(x=0.0, psi=pressure_psi),
        ControlSurfaceStation(x=hinge_fraction, psi=pressure_psi),
        ControlSurfaceStation(x=1.0, psi=0.0),
    ]


def build_aileron(project: Project) -> List[ControlSurfaceLoadResult]:
    """The critical up/down aileron loads as control-surface result records."""
    if project.aileron_loads is None:
        raise ValueError("aileron needs the 'aileron_loads' input slice")
    if project.speeds is None:
        raise ValueError("aileron needs 'speeds' (STRSPEED VA/VC/VD)")
    inp = project.aileron_loads
    sv = design_speed_values(project, project.speeds)
    r = aileron_loads(sv.va, sv.vc, sv.vd, inp.down_deflection_deg,
                      inp.up_deflection_deg, inp.area_fwd_hinge_sqft,
                      inp.area_aft_hinge_sqft)
    return [
        ControlSurfaceLoadResult(
            surface=inp.surface, case="down aileron", load_lb=r.down_load_lb,
            v_kt=r.down_speed_kt,
            stations=_stations(r.down_pressure_psi, r.hinge_chord_fraction)),
        ControlSurfaceLoadResult(
            surface=inp.surface, case="up aileron", load_lb=r.up_load_lb,
            v_kt=r.up_speed_kt,
            stations=_stations(r.up_pressure_psi, r.hinge_chord_fraction)),
    ]


def run(project: Project) -> ModuleResult:
    """Run AILERON: the critical deflected up/down aileron loads (FAR 23.455)."""
    if project.aileron_loads is None:
        raise ValueError("Project has no 'aileron_loads' inputs for the aileron module")
    if project.speeds is None:
        raise ValueError("aileron needs 'speeds' (STRSPEED VA/VC/VD)")
    inp = project.aileron_loads
    sv = design_speed_values(project, project.speeds)
    r = aileron_loads(sv.va, sv.vc, sv.vd, inp.down_deflection_deg,
                      inp.up_deflection_deg, inp.area_fwd_hinge_sqft,
                      inp.area_aft_hinge_sqft)
    note = ("Deflected aileron, CAM 3.222(c) CL_ail = 0.04*DEFL; constant pressure "
            "LE->hinge tapering to 0 at the TE.")
    if project.is_concept:
        note += " Concept mode -- unverified extrapolation past the FAR23 band."
    condition = ConditionResult(
        title="Critical aileron loads",
        far_reference="23.455",
        values=[
            LoadValue("Critical down aileron load", r.down_load_lb, "lb"),
            LoadValue("Down aileron speed", r.down_speed_kt, "kt(EAS)"),
            LoadValue("Critical up aileron load", r.up_load_lb, "lb"),
            LoadValue("Up aileron speed", r.up_speed_kt, "kt(EAS)"),
            LoadValue("Pressure fwd of hinge (down)", r.down_pressure_psi, "lb/in^2"),
            LoadValue("Pressure fwd of hinge (up)", r.up_pressure_psi, "lb/in^2"),
        ],
        note=note,
    )
    return ModuleResult(module=MODULE_NAME, conditions=[condition])


register(MODULE_NAME, run)
