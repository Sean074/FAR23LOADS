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
from typing import List, Optional

from ..constants import LBIN2_PER_SLUGFT2
from ..models import (
    ConditionResult,
    LoadValue,
    MassCase,
    MassItem,
    MassResult,
    MissingInputError,
    ModuleResult,
    Project,
)
from ..registry import register

# 23.23 load-distribution limits (the CG/loading basis) + 23.29 empty weight and
# corresponding CG -- the quantities WTONECG actually computes (User's Guide S4.3).
_FAR = "23.23/23.29"
_SLUGFT2 = "slug-ft^2"
_LBIN2 = "lb-in^2"


def weights_and_inertia(items: List[MassItem]) -> ConditionResult:
    """Total weight, CG and moments of inertia for the given loading."""
    loaded = [it for it in items if it.weight_lb != 0]
    if not loaded:
        raise MissingInputError("WTONECG needs at least one non-zero weight item")

    # Weight and CG (WTONECG.BAS lines 657-750).
    total = math.fsum(it.weight_lb for it in loaded)
    xbar = math.fsum(it.weight_lb * it.x for it in loaded) / total
    zbar = math.fsum(it.weight_lb * it.z for it in loaded) / total

    # Moments of inertia about airplane coordinates, lb-in^2 (lines 780-860):
    # the parallel-axis transfer of each item plus the item's own inertia.
    ixx = (math.fsum(it.weight_lb * (it.y ** 2 + (it.z - zbar) ** 2) for it in loaded)
           + math.fsum(it.ixx for it in loaded))
    iyy = (math.fsum(it.weight_lb * ((it.x - xbar) ** 2 + (it.z - zbar) ** 2) for it in loaded)
           + math.fsum(it.iyy for it in loaded))
    izz = (math.fsum(it.weight_lb * (it.y ** 2 + (it.x - xbar) ** 2) for it in loaded)
           + math.fsum(it.izz for it in loaded))
    ixz = math.fsum(it.weight_lb * (it.x - xbar) * (it.z - zbar) for it in loaded)

    # Convert lb-in^2 -> slug-ft^2.
    ixx_s = ixx / LBIN2_PER_SLUGFT2
    iyy_s = iyy / LBIN2_PER_SLUGFT2
    izz_s = izz / LBIN2_PER_SLUGFT2
    ixz_s = ixz / LBIN2_PER_SLUGFT2

    # Principal axes (lines 865-910): rotate in the x-z plane to null the IXZ
    # product of inertia.
    two_theta = math.pi / 2 if izz_s == ixx_s else math.atan(2 * ixz_s / (izz_s - ixx_s))
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
            LoadValue("Weight", total, "lb", quantity="mass", key="weight"),
            LoadValue("XBAR (fus station)", xbar, "in", key="xbar_fus_station"),
            LoadValue("ZBAR (waterline)", zbar, "in", key="zbar_waterline"),
            LoadValue("IXX", ixx_s, _SLUGFT2, key="ixx"),
            LoadValue("IYY", iyy_s, _SLUGFT2, key="iyy"),
            LoadValue("IZZ", izz_s, _SLUGFT2, key="izz"),
            LoadValue("IXZ", ixz_s, _SLUGFT2, key="ixz"),
            LoadValue("IXX (lb-in^2)", ixx, _LBIN2, key="ixx_lb_in_2"),
            LoadValue("IYY (lb-in^2)", iyy, _LBIN2, key="iyy_lb_in_2"),
            LoadValue("IZZ (lb-in^2)", izz, _LBIN2, key="izz_lb_in_2"),
            LoadValue("IXZ (lb-in^2)", ixz, _LBIN2, key="ixz_lb_in_2"),
            LoadValue("IX(P) principal", pxi, _SLUGFT2, key="ix_p_principal"),
            LoadValue("IY(P) principal", pyi, _SLUGFT2, key="iy_p_principal"),
            LoadValue("IZ(P) principal", pzi, _SLUGFT2, key="iz_p_principal"),
            LoadValue("Principal-axis angle theta", math.degrees(theta), "deg", key="principal_axis_angle_theta"),
        ],
        note="Theta measured up from the waterline and aft from the CG.",
    )


def build_mass(project: Project, name: str = "itemized loading", gear_down: bool = True) -> MassResult:
    """The persisted mass-properties slice (``Project.mass``) for the itemized
    loading: weight, CG and the airplane moments/product of inertia (lb-in^2) about
    the CG. One :class:`MassCase`; the full per-CG-loading set (the four structural-
    limit loadings x gear up/down) is a later refinement. SELECT reads this when a
    precise inertia is wanted; its oracle searches use the documented Ch 9
    approximations, so persisting the mass does not change them.
    """
    if project.weight is None or not project.weight.items:
        raise MissingInputError("Project has no 'weight.items' data base for the mass slice")
    v = {lv.label: lv.value for lv in weights_and_inertia(project.weight.items).values}
    return MassResult(cases=[MassCase(
        name=name, weight_lb=v["Weight"], cg_x=v["XBAR (fus station)"], cg_y=0.0,
        cg_z=v["ZBAR (waterline)"], ixx=v["IXX (lb-in^2)"], iyy=v["IYY (lb-in^2)"],
        izz=v["IZZ (lb-in^2)"], ixz=v["IXZ (lb-in^2)"], gear_down=gear_down)])


def refresh_mass(project: Project) -> bool:
    """Make ``project.mass`` the slice ``weight.items`` derives; say whether it moved.

    The one writer of ``Project.mass`` (#62, PB-1). Both GUIs call it whenever
    the item data base is persisted, and gate G5's reduction calls it after
    dropping the stored slice, so "the mass slice" has exactly one meaning:
    :func:`build_mass` over the items as they stand. No items, or none with a
    weight, derive nothing and the slice is ``None`` -- the ``weight_mass``
    step's ✅ goes out with them rather than lingering on a loading that no
    longer exists. Idempotent by value: a project whose stored slice already
    equals the derivation is left untouched, which is what lets a render pass
    call this without dirtying the project (``tests/test_dirty_flag.py``).
    """
    fresh: Optional[MassResult]
    try:
        fresh = build_mass(project)
    except MissingInputError:
        fresh = None
    if fresh == project.mass:
        return False
    project.mass = fresh
    return True


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "weight_onecg"


def run(project: Project) -> ModuleResult:
    """Run WTONECG against a :class:`Project`'s ``weight.items`` data base."""
    if project.weight is None or not project.weight.items:
        raise MissingInputError("Project has no 'weight.items' data base for the weight_onecg module")
    return ModuleResult(module=MODULE_NAME, conditions=[weights_and_inertia(project.weight.items)])


register(MODULE_NAME, run)
