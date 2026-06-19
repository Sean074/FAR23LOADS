"""Weight, centre of gravity and inertia for one loading -- WTONECG.BAS.

Given the itemized weight data base (each component's weight and station, plus
its own moments of inertia), WTONECG returns the loading's total weight, CG and
the airplane moments of inertia about both the airplane axes and the principal
axes, in slug-ft^2 and lb-in^2. These mass/inertia properties feed the flight,
landing and one-engine-out load modules in later phases.

The inertias are the parallel-axis (transfer) sum of each item about the
airplane CG; W*d^2 accumulates in lb-in^2 and is divided by 144*g to report
slug-ft^2 (WTONECG.BAS lines 780-860). Y is carried but is zero for a laterally
symmetric airplane.

Reference: WTONECG.BAS, Appendix C p377-381; worked example Appendix A p136.
"""

from __future__ import annotations

import math
from typing import List

from ..constants import LBIN2_PER_SLUGFT2
from ..models import ConditionResult, LoadValue, MassItem, ModuleResult, Project
from ..registry import register

_FAR = "23.21/23.23"
_SLUGFT2 = "slug-ft^2"
_LBIN2 = "lb-in^2"


def weights_and_inertia(items: List[MassItem]) -> ConditionResult:
    """Total weight, CG and moments of inertia for the given loading."""
    loaded = [it for it in items if it.weight_lb != 0]
    if not loaded:
        raise ValueError("WTONECG needs at least one non-zero weight item")

    # Weight and CG (WTONECG.BAS lines 657-750).
    total = sum(it.weight_lb for it in loaded)
    xbar = sum(it.weight_lb * it.x for it in loaded) / total
    zbar = sum(it.weight_lb * it.z for it in loaded) / total

    # Moments of inertia about airplane coordinates, lb-in^2 (lines 780-860):
    # the parallel-axis transfer of each item plus the item's own inertia.
    ixx = sum(it.weight_lb * (it.y ** 2 + (it.z - zbar) ** 2) for it in loaded) + sum(it.ixx for it in loaded)
    iyy = sum(it.weight_lb * ((it.x - xbar) ** 2 + (it.z - zbar) ** 2) for it in loaded) + sum(it.iyy for it in loaded)
    izz = sum(it.weight_lb * (it.y ** 2 + (it.x - xbar) ** 2) for it in loaded) + sum(it.izz for it in loaded)
    ixz = sum(it.weight_lb * (it.x - xbar) * (it.z - zbar) for it in loaded)

    # Convert lb-in^2 -> slug-ft^2.
    ixx_s = ixx / LBIN2_PER_SLUGFT2
    iyy_s = iyy / LBIN2_PER_SLUGFT2
    izz_s = izz / LBIN2_PER_SLUGFT2
    ixz_s = ixz / LBIN2_PER_SLUGFT2

    # Principal axes (lines 865-910): rotate in the x-z plane to null the IXZ
    # product of inertia.
    if izz_s == ixx_s:
        two_theta = math.pi / 2
    else:
        two_theta = math.atan(2 * ixz_s / (izz_s - ixx_s))
    theta = 0.5 * two_theta
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    sin_2t = math.sin(2 * theta)
    pxi = ixx_s * cos_t ** 2 + izz_s * sin_t ** 2 - ixz_s * sin_2t
    pyi = iyy_s
    pzi = ixx_s * sin_t ** 2 + izz_s * cos_t ** 2 + ixz_s * sin_2t

    return ConditionResult(
        title="Weight, centre of gravity and inertia for one loading",
        far_reference=_FAR,
        values=[
            LoadValue("Weight", total, "lb", quantity="mass"),
            LoadValue("XBAR (fus station)", xbar, "in"),
            LoadValue("ZBAR (waterline)", zbar, "in"),
            LoadValue("IXX", ixx_s, _SLUGFT2),
            LoadValue("IYY", iyy_s, _SLUGFT2),
            LoadValue("IZZ", izz_s, _SLUGFT2),
            LoadValue("IXZ", ixz_s, _SLUGFT2),
            LoadValue("IXX (lb-in^2)", ixx, _LBIN2),
            LoadValue("IYY (lb-in^2)", iyy, _LBIN2),
            LoadValue("IZZ (lb-in^2)", izz, _LBIN2),
            LoadValue("IXZ (lb-in^2)", ixz, _LBIN2),
            LoadValue("IX(P) principal", pxi, _SLUGFT2),
            LoadValue("IY(P) principal", pyi, _SLUGFT2),
            LoadValue("IZ(P) principal", pzi, _SLUGFT2),
            LoadValue("Principal-axis angle theta", math.degrees(theta), "deg"),
        ],
        note="Theta measured up from the waterline and aft from the CG.",
    )


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "weight_onecg"


def run(project: Project) -> ModuleResult:
    """Run WTONECG against a :class:`Project`'s ``weight.items`` data base."""
    if project.weight is None or not project.weight.items:
        raise ValueError("Project has no 'weight.items' data base for the weight_onecg module")
    return ModuleResult(module=MODULE_NAME, conditions=[weights_and_inertia(project.weight.items)])


register(MODULE_NAME, run)
