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

MC and MD are **not** MACHLIM inputs (F25-2, schema v40): they are produced by
``structural_speeds.design_speed_values`` from VC/VD at the shoulder altitude and
passed to :func:`mach_limit_lines`. Storing them here as well used to let the CLI
and the GUI disagree about the same project's MNE/MFC -- the GUI recomputed and
the CLI did not.

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
    MissingInputError,
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


def mach_limit_lines(inp: MachLimitInput, mc: float, md: float) -> List[ConditionResult]:
    """The MNE/MFC Mach numbers and the per-altitude Mach-limited EAS table.

    ``mc``/``md`` are passed in rather than stored on ``inp`` (F25-2, schema v40).
    They used to be persisted on :class:`MachLimitInput` *and* recomputed from the
    design speeds by the Streamlit page, which ignored the stored pair -- so the
    same project reported one MNE from the CLI and a different one from the GUI.
    :func:`sloads.modules.structural_speeds.design_speed_values` is now the only
    producer, and every front-end passes what it produced.
    """
    if mc <= 0 or md <= 0:
        raise ValueError("MACHLIM needs positive MC and MD")

    mne = 0.9 * md
    mfc = 1.2 * md

    summary = ConditionResult(
        title="Mach limitation summary",
        far_reference=_FAR,
        values=[
            LoadValue("Cruise Mach MC", mc, key="cruise_mach_mc"),
            LoadValue("Dive Mach MD", md, key="dive_mach_md"),
            LoadValue("Never-exceed Mach MNE", mne, key="never_exceed_mach_mne"),
            LoadValue("Flutter-clearance Mach MFC", mfc, key="flutter_clearance_mach_mfc"),
            LoadValue("Shoulder altitude", inp.shoulder_altitude_ft, "ft", key="shoulder_altitude"),
            LoadValue("Max operating altitude", inp.max_operating_altitude_ft, "ft", key="max_operating_altitude"),
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
                LoadValue("Altitude", h, "ft", key="altitude"),
                LoadValue("V(MC)", mc * a * rs, _KT, key="v_mc"),
                LoadValue("V(MNE)", mne * a * rs, _KT, key="v_mne"),
                LoadValue("V(MD)", md * a * rs, _KT, key="v_md"),
                LoadValue("V(FC)", mfc * a * rs, _KT, key="v_fc"),
            ],
        ))
    return results


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "mach_limit"


def run(project: Project) -> ModuleResult:
    """Run MACHLIM against a :class:`Project`'s ``speeds.mach_limit`` inputs.

    MC/MD come from STRSPEED, not from the MACHLIM slice (F25-2) -- so this path
    now needs whatever ``design_speed_values`` needs, which includes the design
    weight, the wing area and the CLmax pair. Those raise ``MissingInputError``
    from ``structural_speeds`` itself, and run-all skips the module accordingly.
    """
    if project.speeds is None or project.speeds.mach_limit is None:
        raise MissingInputError("Project has no 'speeds.mach_limit' inputs for the mach_limit module")
    from .structural_speeds import design_speed_values

    ds = design_speed_values(project, project.speeds)
    return ModuleResult(
        module=MODULE_NAME,
        conditions=mach_limit_lines(project.speeds.mach_limit, ds.mc, ds.md),
    )


register(MODULE_NAME, run)
