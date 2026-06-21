"""Structural design speeds & limit maneuver load factors, from STRSPEED.BAS.

STRSPEED chooses the certification category (normal/utility/acrobatic) and
computes the FAR 23.335 minimum design airspeeds and the FAR 23.337 limit
maneuver load factors, then verifies the chosen speeds meet those minimums
(raising them if not). It also reports the cruise/dive Mach numbers at the
shoulder altitude (the dividing line with MACHLIM). All speeds are knots
equivalent airspeed (KEAS). Reference 1 Ch 6.

Equations (Ch 6):
    n      = 2.1 + 24000/(W+10000), capped 3.8 (N), or 4.4 (U), 6.0 (A)
    n_neg  = -0.4*n (N/U) or -0.5*n (A)
    VC_min = K_c*(W/S)**0.5         [<= 0.9*VH]          K_c by category
    VD_min = max(K_d*VC, 1.25*VC)                         K_d by category
    VA_min = VS*sqrt(n)             [<= VC]
    VF_min = max(1.4*VS, 1.8*VSF)
    MC     = VC/(sqrt(sigma)*a),  MD = VD/(sqrt(sigma)*a)  at the shoulder altitude

For the worked example the absolute FAR floor VD >= 1.25*VC governs (212.5 kt),
so the dive speed is taken as that floor; K_d*VC is reported as the recommended
gust-based dive speed.

Reference: STRSPEED.BAS, Ch 6; worked example Appendix A (VA 121.3, VC 170,
VD 212.5, VF 105.5; n = +3.8 / -1.52; MC 0.323, MD 0.403 at 12000 ft).
"""

from __future__ import annotations

import math
from typing import List, NamedTuple, Optional

from ..constants import (
    cruise_speed_coefficient,
    dive_ratio_coefficient,
    standard_atmosphere,
)
from ..models import (
    ConditionResult,
    LoadValue,
    ModuleResult,
    Project,
    StructuralSpeedsInput,
)
from ..registry import register

_FAR = "23.335/23.337"
_KT = "kt(EAS)"


def _maneuver_load_factors(category: str, weight: float, chosen_n: Optional[float],
                           chosen_nneg: Optional[float]):
    """Limit positive and negative maneuver load factors (FAR 23.337).

    Concept mode (``category == "C"``) bypasses the GA-only 23.337 formula and cap
    entirely: it uses the user's ``chosen_n``/``chosen_nneg`` verbatim (both are
    required) so configurations above the 12,500 lb calibration band are not forced
    to a meaningless GA limit. The reported "minimum required" figures echo the
    chosen values, since there is no binding FAR floor in concept mode.
    """
    if category == "C":
        if chosen_n is None or chosen_nneg is None:
            raise ValueError(
                "concept category 'C' requires explicit chosen_n and chosen_nneg "
                "(no FAR 23.337 cap is applied)"
            )
        return chosen_n, chosen_n, chosen_nneg, chosen_nneg

    n_min = 2.1 + 24000.0 / (weight + 10000.0)
    if category == "U":
        n_min = 4.4
    elif category == "A":
        n_min = 6.0
    else:  # normal / commuter
        n_min = min(n_min, 3.8)
    n = max(chosen_n, n_min) if chosen_n is not None else n_min

    neg_factor = -0.5 if category == "A" else -0.4
    nneg_min = neg_factor * n
    # Chosen negative is acceptable only if at least as negative as the minimum.
    nneg = min(chosen_nneg, nneg_min) if chosen_nneg is not None else nneg_min
    return n, n_min, nneg, nneg_min


def _wing_area_sqft(project: Project, inp: StructuralSpeedsInput) -> float:
    """Wing area S (ft^2): from the geometry slice (in^2 -> ft^2) or direct input."""
    if project.geometry is not None:
        surf = project.geometry.by_name(inp.wing_surface)
        if surf is not None:
            from .wing_geometry import surface_properties
            r = surface_properties(surf)
            total_in2 = next(v.value for v in r.values if v.label == "Total area")
            return total_in2 / 144.0
    if inp.wing_area_sqft:
        return inp.wing_area_sqft
    raise ValueError(
        "STRSPEED needs the wing area: add a 'wing' geometry surface or set "
        "speeds.wing_area_sqft"
    )


class DesignSpeeds(NamedTuple):
    """The scalar STRSPEED outputs (knots / dimensionless) downstream modules read.

    AILERON / FLAPLOAD / TABLOADS (Step C8) and the rest of the pipeline take the
    design speeds and limit load factors from here rather than re-deriving them."""
    va: float
    vc: float
    vd: float
    vf: float
    vc_min: float
    va_min: float
    vf_min: float
    vd_recommended: float
    n: float
    n_min: float
    nneg: float
    nneg_min: float
    ws: float
    wing_area_sqft: float
    speed_of_sound_kt: float
    sigma: float
    mc: float
    md: float


def design_speed_values(project: Project, inp: StructuralSpeedsInput) -> DesignSpeeds:
    """Compute the scalar STRSPEED design speeds + maneuver load factors."""
    w = inp.weight_lb
    if w <= 0:
        raise ValueError("STRSPEED needs a positive design weight")
    s = _wing_area_sqft(project, inp)
    ws = w / s
    cat = inp.category.upper()

    n, n_min, nneg, nneg_min = _maneuver_load_factors(cat, w, inp.chosen_n, inp.chosen_nneg)

    # Cruise speed VC. In concept mode the K_c/K_d coefficients are GA-calibrated
    # (taper to W/S = 100), so VC(min)/VD(min) are out-of-band *advisories* only --
    # the concept supplies chosen_vc/chosen_vd, which govern.
    kc = cruise_speed_coefficient(cat, ws)
    vc_min = kc * ws ** 0.5
    if inp.vh_kt and vc_min > 0.9 * inp.vh_kt:
        vc_min = 0.9 * inp.vh_kt
    vc = max(inp.chosen_vc, vc_min) if inp.chosen_vc is not None else vc_min

    # Dive speed VD: the FAR floor 1.25*VC governs; K_d*VC is the recommended value.
    kd = dive_ratio_coefficient(cat, ws)
    vd_floor = 1.25 * vc
    vd_recommended = kd * vc
    vd = max(inp.chosen_vd, vd_floor) if inp.chosen_vd is not None else vd_floor

    # Maneuver speed VA.
    va_min = inp.stall_clean_kt * math.sqrt(n)
    va = max(inp.chosen_va, va_min) if inp.chosen_va is not None else va_min
    va = min(va, vc)

    # Flap speed VF.
    vf_min = max(1.4 * inp.stall_clean_kt, 1.8 * inp.stall_flap_kt)
    vf = max(inp.chosen_vf, vf_min) if inp.chosen_vf is not None else vf_min

    # Cruise/dive Mach at the shoulder altitude.
    a, sigma = standard_atmosphere(inp.shoulder_altitude_ft)
    root_sigma = math.sqrt(sigma)
    mc = vc / (root_sigma * a)
    md = vd / (root_sigma * a)
    return DesignSpeeds(
        va=va, vc=vc, vd=vd, vf=vf, vc_min=vc_min, va_min=va_min, vf_min=vf_min,
        vd_recommended=vd_recommended, n=n, n_min=n_min, nneg=nneg, nneg_min=nneg_min,
        ws=ws, wing_area_sqft=s, speed_of_sound_kt=a, sigma=sigma, mc=mc, md=md,
    )


def design_speeds(project: Project, inp: StructuralSpeedsInput) -> List[ConditionResult]:
    """Compute the design speeds, maneuver load factors and cruise/dive Mach."""
    sv = design_speed_values(project, inp)
    cat = inp.category.upper()
    va, vc, vd, vf = sv.va, sv.vc, sv.vd, sv.vf
    vc_min, va_min, vf_min, vd_recommended = sv.vc_min, sv.va_min, sv.vf_min, sv.vd_recommended
    n, n_min, nneg, nneg_min = sv.n, sv.n_min, sv.nneg, sv.nneg_min
    ws, s = sv.ws, sv.wing_area_sqft
    a, sigma, mc, md = sv.speed_of_sound_kt, sv.sigma, sv.mc, sv.md

    load_factors = ConditionResult(
        title="Limit maneuver load factors",
        far_reference="23.337",
        values=[
            LoadValue("Limit positive load factor", n),
            LoadValue("Minimum required positive factor", n_min),
            LoadValue("Limit negative load factor", nneg),
            LoadValue("Minimum required negative factor", nneg_min),
            LoadValue("Wing loading W/S", ws, "lb/ft^2"),
        ],
        note=(
            "Category C (concept) -- user-defined load factors, no FAR 23.337 cap "
            "applied; results are an unverified extrapolation."
            if cat == "C" else f"Category {cat}."
        ),
    )

    speeds = ConditionResult(
        title="Structural design speeds",
        far_reference="23.335",
        values=[
            LoadValue("Maneuver speed VA", va, _KT),
            LoadValue("Cruise speed VC", vc, _KT),
            LoadValue("Dive speed VD", vd, _KT),
            LoadValue("Flap speed VF", vf, _KT),
            LoadValue("Minimum cruise VC(min)", vc_min, _KT),
            LoadValue("Minimum maneuver VA(min)", va_min, _KT),
            LoadValue("Minimum flap VF(min)", vf_min, _KT),
            LoadValue("Recommended dive VD (gust, K*VC)", vd_recommended, _KT),
            LoadValue("Wing area S", s, "ft^2"),
        ],
    )

    mach = ConditionResult(
        title="Cruise/dive Mach at shoulder altitude",
        far_reference="23.335(b)",
        values=[
            LoadValue("Shoulder altitude", inp.shoulder_altitude_ft, "ft"),
            LoadValue("Speed of sound", a, _KT),
            LoadValue("Density ratio sigma", sigma),
            LoadValue("Cruise Mach MC", mc),
            LoadValue("Dive Mach MD", md),
        ],
    )

    return [load_factors, speeds, mach]


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "structural_speeds"


def run(project: Project) -> ModuleResult:
    """Run STRSPEED against a :class:`Project`'s ``speeds`` inputs."""
    if project.speeds is None:
        raise ValueError("Project has no 'speeds' inputs for the structural_speeds module")
    return ModuleResult(module=MODULE_NAME, conditions=design_speeds(project, project.speeds))


register(MODULE_NAME, run)
