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
    VD_min = max(K_d*VCmin, 1.25*VC)                      K_d by category
    VA_min = VS*sqrt(n)             [<= VC]
    VF_min = max(1.4*VS, 1.8*VSF)
    VS     = sqrt(295*(W/S)/CLmax_clean),  VSF = sqrt(295*(W/S)/CLmax_flap)
    MC     = VC/(sqrt(sigma)*a),  MD = VD/(sqrt(sigma)*a)  at the shoulder altitude

The clean/flapped stall speeds VS/VSF are DERIVED from the maximum lift
coefficients on ``Project.aero_coeffs`` (``clmax_clean``/``clmax_flap``) at the
design weight -- CLmax is entered once and is the single stall source (M1-1b;
User's Guide p7-5). VS/VSF then set VA and VF.

FAR 23.335(b) imposes both dive-speed minimums: VD >= max(K_d*VCmin, 1.25*VC),
where the K_d term uses the *minimum* cruise VCmin (STRSPEED.BAS V2DMIN=K2*V1CMIN,
lines 380/390). With no chosen speeds the K_d*VCmin term governs (Appendix A p155,
Cat N: 198.53 kt). For the worked chosen-speeds example (p156) the chosen VD 212.5
already clears both floors, which is why the absolute 1.25*VC floor is what shows.
Concept mode (Cat C) treats the GA-calibrated K_d term as advisory only.

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
    stall_speed_kt,
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


def _stall_speeds(project: Project, weight_lb: float, wing_area_sqft: float):
    """Clean/flapped stall speeds VS/VSF (KEAS) from the CLmax on ``aero_coeffs``.

    CLmax is the single authored stall source (M1-1b): ``clmax_clean`` gives VS,
    ``clmax_flap`` gives VSF, both at the design weight (``stall_speed_kt``).
    Raises when the Aerodynamic Data page's CLmax has not been entered.
    """
    aero = project.aero_coeffs
    if aero is None or not aero.clmax_clean or not aero.clmax_flap:
        raise ValueError(
            "STRSPEED needs the maximum lift coefficients: set clmax_clean and "
            "clmax_flap on the Aerodynamic Data page (Project.aero_coeffs). VS/VSF "
            "(and hence VA/VF) are derived from CLmax."
        )
    vs = stall_speed_kt(weight_lb, wing_area_sqft, aero.clmax_clean)
    vsf = stall_speed_kt(weight_lb, wing_area_sqft, aero.clmax_flap)
    return vs, vsf


class DesignSpeeds(NamedTuple):
    """The scalar STRSPEED outputs (knots / dimensionless) downstream modules read.

    AILERON / FLAPLOAD / TABLOADS (Step C8) and the rest of the pipeline take the
    design speeds and limit load factors from here rather than re-deriving them."""
    va: float
    vc: float
    vd: float
    vf: float
    vs: float
    vsf: float
    vc_min: float
    va_min: float
    vf_min: float
    vd_min: float
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

    vs, vsf = _stall_speeds(project, w, s)

    # Cruise speed VC. In concept mode the K_c/K_d coefficients are GA-calibrated
    # (taper to W/S = 100), so VC(min)/VD(min) are out-of-band *advisories* only --
    # the concept supplies chosen_vc/chosen_vd, which govern.
    kc = cruise_speed_coefficient(cat, ws)
    vc_min = kc * ws ** 0.5
    if inp.vh_kt and vc_min > 0.9 * inp.vh_kt:
        vc_min = 0.9 * inp.vh_kt
    vc = max(inp.chosen_vc, vc_min) if inp.chosen_vc is not None else vc_min

    # Dive speed VD: FAR 23.335(b) requires BOTH minimums -- VD >= max(K_d*VCmin,
    # 1.25*VC). STRSPEED.BAS lines 380/390 (V2DMIN = K2*V1CMIN) use VCmin, not the
    # chosen VC, in the K_d term. Concept mode (Cat C) treats the GA-calibrated K_d
    # term as advisory only, retaining just the absolute 1.25*VC floor.
    kd = dive_ratio_coefficient(cat, ws)
    vd_kd_min = kd * vc_min          # K_d * VCmin  (23.335(b)(2); BASIC V2DMIN)
    vd_125 = 1.25 * vc               # absolute floor on the actual cruise speed
    vd_min = max(vd_kd_min, vd_125)
    hard_floor = vd_125 if cat == "C" else vd_min
    vd = max(inp.chosen_vd, hard_floor) if inp.chosen_vd is not None else hard_floor

    # Maneuver speed VA.
    va_min = vs * math.sqrt(n)
    va = max(inp.chosen_va, va_min) if inp.chosen_va is not None else va_min
    va = min(va, vc)

    # Flap speed VF.
    vf_min = max(1.4 * vs, 1.8 * vsf)
    vf = max(inp.chosen_vf, vf_min) if inp.chosen_vf is not None else vf_min

    # Cruise/dive Mach at the shoulder altitude.
    a, sigma = standard_atmosphere(inp.shoulder_altitude_ft)
    root_sigma = math.sqrt(sigma)
    mc = vc / (root_sigma * a)
    md = vd / (root_sigma * a)
    return DesignSpeeds(
        va=va, vc=vc, vd=vd, vf=vf, vs=vs, vsf=vsf,
        vc_min=vc_min, va_min=va_min, vf_min=vf_min,
        vd_min=vd_min, n=n, n_min=n_min, nneg=nneg, nneg_min=nneg_min,
        ws=ws, wing_area_sqft=s, speed_of_sound_kt=a, sigma=sigma, mc=mc, md=md,
    )


def design_speeds(project: Project, inp: StructuralSpeedsInput) -> List[ConditionResult]:
    """Compute the design speeds, maneuver load factors and cruise/dive Mach."""
    sv = design_speed_values(project, inp)
    cat = inp.category.upper()
    va, vc, vd, vf = sv.va, sv.vc, sv.vd, sv.vf
    vc_min, va_min, vf_min, vd_min = sv.vc_min, sv.va_min, sv.vf_min, sv.vd_min
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
            LoadValue("Minimum dive VD(min)", vd_min, _KT),
            LoadValue("Wing area S", s, "ft^2"),
        ],
        note=(
            f"OUT-OF-BAND: W/S = {ws:.1f} lb/ft^2 exceeds the FAR 23.335 coefficient "
            "schedule (tabulated to W/S = 100). Kc/Kd are held at their W/S = 100 "
            "values (28.6 / 1.35); VC(min)/VD(min) are GA-extrapolated advisories -- "
            "supply chosen VC/VD."
            if ws > 100.0 else ""
        ),
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
