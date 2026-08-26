"""Mach-limit lines for the flight-limits diagram, ported from MACHLIM.BAS.

For high-performance / high-altitude airplanes the cruise and dive speed limits
above the "shoulder" altitude are set by Mach number rather than equivalent
airspeed. MACHLIM tabulates the Mach-limited equivalent airspeeds from the
shoulder altitude up to the maximum operating altitude, for the cruise (MC), dive
(MD) and never-exceed (MNE) Mach lines, to be drawn on the flight-limits diagram
(Reference 1 Ch 6).

Equations (MACHLIM.BAS):
    MNE = 0.9 * MD            never-exceed Mach
    V(M, EAS) = M * a * sqrt(sigma)   at each altitude, with a and sigma from the
                                      shared standard atmosphere

**Flutter clearance is not computed here (#79, C210-19).** MACHLIM.BAS also prints
``MFC = 1.2 * MD`` and its per-altitude ``V(FC)``, and this module reproduced both
until 2026-08-26. They are flutter-substantiation content under 14 CFR 23.629, not
a design load, and the symbol reads to a Part 25 audience as §25.253's VFC/MFC,
which is a different quantity with a different definition. Removed from the tool by
owner directive: a deliberate replication-scope reduction, registered in
``docs/20_theory/02_approved_corrections.md`` -- the printed 0.4836 is not wrong,
it is out of scope. MNE and the V(MC)/V(MNE)/V(MD) lines are unaffected and stay
oracle-locked.

(The original used a = 29.02; the shared ``standard_atmosphere`` uses 29.02436 --
a ~0.01% difference absorbed by the ±0.1% regression tolerance, per Decision 3.)

MC and MD are **not** MACHLIM inputs (F25-2, schema v40): they are produced by
``structural_speeds.design_speed_values`` from VC/VD at the shoulder altitude and
passed to :func:`mach_limit_lines` -- as is the shoulder altitude itself since
schema v55 (#52): ``speeds.shoulder_altitude_ft`` is its one home. Storing them here as well used to let the CLI
and the GUI disagree about the same project's MNE -- the GUI recomputed and
the CLI did not.

Reference: MACHLIM.BAS, Ch 6; worked example Appendix A p160 (MC 0.323, MD 0.403,
shoulder 12000 ft, max 18000 ft: MNE 0.3627; V(MC) 170.16 .. 150.77). The same page
prints MFC 0.4836, which this port deliberately does not produce (above).
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


def _altitudes(inp: MachLimitInput, shoulder_altitude_ft: float) -> List[float]:
    """Shoulder altitude up to max operating altitude in ``increment_ft`` steps.

    The final altitude is clamped to the max operating altitude (MACHLIM.BAS
    GOTO 240: the last partial step lands exactly on HMAXALT).
    """
    if inp.increment_ft <= 0:
        raise ValueError("MACHLIM altitude increment must be positive")
    if inp.max_operating_altitude_ft < shoulder_altitude_ft:
        raise ValueError("MACHLIM max operating altitude must be >= shoulder altitude")
    out = []
    h = shoulder_altitude_ft
    while h < inp.max_operating_altitude_ft:
        out.append(h)
        h += inp.increment_ft
    out.append(inp.max_operating_altitude_ft)
    return out


def mach_limit_lines(inp: MachLimitInput, mc: float, md: float,
                     shoulder_altitude_ft: float) -> List[ConditionResult]:
    """The MNE Mach number and the per-altitude Mach-limited EAS table.

    ``mc``/``md`` are passed in rather than stored on ``inp`` (F25-2, schema v40).
    They used to be persisted on :class:`MachLimitInput` *and* recomputed from the
    design speeds by the Streamlit page, which ignored the stored pair -- so the
    same project reported one MNE from the CLI and a different one from the GUI.
    :func:`sloads.modules.structural_speeds.design_speed_values` is now the only
    producer, and every front-end passes what it produced.

    ``shoulder_altitude_ft`` is passed the same way (#52, schema v55): it is
    ``speeds.shoulder_altitude_ft``, the altitude MC/MD were derived at, so the
    table's first row and the Mach numbers on it can no longer come from two
    different altitudes.
    """
    if mc <= 0 or md <= 0:
        raise ValueError("MACHLIM needs positive MC and MD")

    mne = 0.9 * md

    summary = ConditionResult(
        title="Mach limitation summary",
        far_reference=_FAR,
        values=[
            LoadValue("Cruise Mach MC", mc, key="cruise_mach_mc"),
            LoadValue("Dive Mach MD", md, key="dive_mach_md"),
            LoadValue("Never-exceed Mach MNE", mne, key="never_exceed_mach_mne"),
            LoadValue("Shoulder altitude", shoulder_altitude_ft, "ft", key="shoulder_altitude"),
            LoadValue("Max operating altitude", inp.max_operating_altitude_ft, "ft", key="max_operating_altitude"),
        ],
        note="MNE = 0.9*MD (never-exceed Mach).",
    )

    results = [summary]
    for h in _altitudes(inp, shoulder_altitude_ft):
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
        conditions=mach_limit_lines(project.speeds.mach_limit, ds.mc, ds.md,
                                    project.speeds.shoulder_altitude_ft),
    )


register(MODULE_NAME, run)
