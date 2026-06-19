"""Mach-limit lines for the flight-limits diagram, ported from MACHLIM.BAS.

For high-performance / high-altitude airplanes the cruise and dive speed limits
above the "shoulder" altitude are set by Mach number rather than equivalent
airspeed. MACHLIM tabulates the Mach-limited equivalent airspeeds from the
shoulder altitude up to the maximum operating altitude, for the cruise (MC), dive
(MD), never-exceed (MNE) and flutter-clearance (MFC) Mach lines, to be drawn on
the flight-limits diagram (Reference 1 Ch 6).

Equations (MACHLIM.BAS):
    MNE = 0.9 * MD            never-exceed Mach
    MFC = 1.2 * MD            flutter-clearance Mach
    V(M, EAS) = M * a * sqrt(sigma)   at each altitude, with a and sigma from the
                                      shared standard atmosphere

(The original used a = 29.02; the shared ``standard_atmosphere`` uses 29.02436 --
a ~0.01% difference absorbed by the ±0.1% regression tolerance, per Decision 3.)

Reference: MACHLIM.BAS, Ch 6; worked example Appendix A p160 (MC 0.323, MD 0.403,
shoulder 12000 ft, max 18000 ft: MNE 0.3627, MFC 0.4836; V(MC) 170.16 .. 150.77).
"""

from __future__ import annotations

import math
from typing import List

from ..constants import standard_atmosphere
from ..models import (
    ConditionResult,
    LoadValue,
    MachLimitInput,
    ModuleResult,
    Project,
)
from ..registry import register

_FAR = "23.335(b)"
_KT = "kt(EAS)"


def _altitudes(inp: MachLimitInput) -> List[float]:
    """Shoulder altitude up to max operating altitude in ``increment_ft`` steps.

    The final altitude is clamped to the max operating altitude (MACHLIM.BAS
    GOTO 240: the last partial step lands exactly on HMAXALT).
    """
    if inp.increment_ft <= 0:
        raise ValueError("MACHLIM altitude increment must be positive")
    if inp.max_operating_altitude_ft < inp.shoulder_altitude_ft:
        raise ValueError("MACHLIM max operating altitude must be >= shoulder altitude")
    out = []
    h = inp.shoulder_altitude_ft
    while h < inp.max_operating_altitude_ft:
        out.append(h)
        h += inp.increment_ft
    out.append(inp.max_operating_altitude_ft)
    return out


def mach_limit_lines(inp: MachLimitInput) -> List[ConditionResult]:
    """The MNE/MFC Mach numbers and the per-altitude Mach-limited EAS table."""
    if inp.mc <= 0 or inp.md <= 0:
        raise ValueError("MACHLIM needs positive MC and MD")

    mne = 0.9 * inp.md
    mfc = 1.2 * inp.md

    summary = ConditionResult(
        title="Mach limitation summary",
        far_reference=_FAR,
        values=[
            LoadValue("Cruise Mach MC", inp.mc),
            LoadValue("Dive Mach MD", inp.md),
            LoadValue("Never-exceed Mach MNE", mne),
            LoadValue("Flutter-clearance Mach MFC", mfc),
            LoadValue("Shoulder altitude", inp.shoulder_altitude_ft, "ft"),
            LoadValue("Max operating altitude", inp.max_operating_altitude_ft, "ft"),
        ],
        note="MNE = 0.9*MD; MFC = 1.2*MD (never-exceed and flutter-clearance Mach).",
    )

    results = [summary]
    for h in _altitudes(inp):
        a, sigma = standard_atmosphere(h)
        rs = math.sqrt(sigma)
        results.append(ConditionResult(
            title=f"Mach limit line at {h:g} ft",
            far_reference=_FAR,
            values=[
                LoadValue("Altitude", h, "ft"),
                LoadValue("V(MC)", inp.mc * a * rs, _KT),
                LoadValue("V(MNE)", mne * a * rs, _KT),
                LoadValue("V(MD)", inp.md * a * rs, _KT),
                LoadValue("V(FC)", mfc * a * rs, _KT),
            ],
        ))
    return results


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "mach_limit"


def run(project: Project) -> ModuleResult:
    """Run MACHLIM against a :class:`Project`'s ``speeds.mach_limit`` inputs."""
    if project.speeds is None or project.speeds.mach_limit is None:
        raise ValueError("Project has no 'speeds.mach_limit' inputs for the mach_limit module")
    return ModuleResult(module=MODULE_NAME, conditions=mach_limit_lines(project.speeds.mach_limit))


register(MODULE_NAME, run)
