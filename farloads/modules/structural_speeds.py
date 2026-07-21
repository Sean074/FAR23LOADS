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
# Operational-limitation placards (M2-10, Subpart G) -- ADVISORY ONLY
# --------------------------------------------------------------------------- #
# The design speeds (Subpart C) bound the *operating limitations* set at
# certification (Subpart G). This derives the preliminary placard speeds those
# limits imply and, when the user supplies operational *targets*, inverts the
# ladder into the required design minima and flags infeasible targets. It NEVER
# changes a design speed or a load -- display/validation only.
# Sources: reference/14CFR_operating_limitations.md -- Ref 1 p47 (VNE=0.9VD,
# MNE=0.9MD, yellow arc, turbine VMO/MMO<=VC/MC), 14 CFR 23.1505 (VNE<=0.9VD;
# VNO<=min(VC, 0.89VNE)), 23.1511 (VFE<=VF), 23.335(b)(4) (MC->MD 0.05 margin).
_MC_MD_MARGIN = 0.05     # N/U/A minimum Mach margin (23.335(b)(4)(ii)); commuter 0.07 (F25-2)
_VNO_VNE_RATIO = 0.89    # 23.1505(b)(2)(ii)
_VNE_VD_RATIO = 0.9      # 23.1505(a)(2)(i) / Ref 1 p47


class OperationalPlacards(NamedTuple):
    """Preliminary Subpart-G placard speeds derived from the design speeds.

    ``vne``/``vno``/``mne`` are the recip yellow-arc family; ``vmo``/``mmo`` the
    turbine (no-yellow-arc) family; ``vfe`` is common. All KEAS except the Mach
    numbers. Advisory only -- the certificated placards are set at certification."""
    vne: float          # 0.9*VD                       (23.1505(a))
    vno: float          # min(VC, 0.89*VNE)            (23.1505(b))
    vfe: float          # VF                           (23.1511)
    mne: float          # 0.9*MD                       (Ref 1 p47)
    vmo: float          # VC   (turbine max operating) (Ref 1 p47)
    mmo: float          # MC   (turbine max operating) (Ref 1 p47)


def operational_placards(ds: DesignSpeeds) -> OperationalPlacards:
    """The preliminary placard speeds implied by a set of design speeds."""
    vne = _VNE_VD_RATIO * ds.vd
    vno = min(ds.vc, _VNO_VNE_RATIO * vne)
    return OperationalPlacards(
        vne=vne, vno=vno, vfe=ds.vf, mne=_VNE_VD_RATIO * ds.md, vmo=ds.vc, mmo=ds.mc,
    )


class TargetCheck(NamedTuple):
    """One operational-target feasibility check: the design-speed minimum a target
    implies, the actual design speed, and whether the target is achievable."""
    target_label: str    # e.g. "VNE"
    target: float        # the user's target value
    driver_label: str    # the design speed that must clear the minimum, e.g. "VD"
    required: float      # required minimum of the driver
    actual: float        # actual design-speed value
    units: str

    @property
    def feasible(self) -> bool:
        return self.actual >= self.required - 1e-9


def operational_target_checks(inp: StructuralSpeedsInput, ds: DesignSpeeds) -> List[TargetCheck]:
    """Invert the placard ladder into required design minima for each set target.

    target VNE => VD >= VNE/0.9;  target VNO => VC >= VNO and VNE >= VNO/0.89
    (i.e. VD >= VNO/0.89/0.9);  target VMO => VC >= VMO;  target MMO => MD >= MMO
    + 0.05;  target VFE => VF >= VFE. Warn-only: nothing here mutates a speed.
    """
    out: List[TargetCheck] = []
    if inp.target_vne:
        out.append(TargetCheck("VNE", inp.target_vne, "VD",
                               inp.target_vne / _VNE_VD_RATIO, ds.vd, _KT))
    if inp.target_vno:
        out.append(TargetCheck("VNO", inp.target_vno, "VC",
                               inp.target_vno, ds.vc, _KT))
        out.append(TargetCheck("VNO", inp.target_vno, "VD (via VNE)",
                               inp.target_vno / _VNO_VNE_RATIO / _VNE_VD_RATIO, ds.vd, _KT))
    if inp.target_vmo:
        out.append(TargetCheck("VMO", inp.target_vmo, "VC", inp.target_vmo, ds.vc, _KT))
    if inp.target_mmo:
        out.append(TargetCheck("MMO", inp.target_mmo, "MD",
                               inp.target_mmo + _MC_MD_MARGIN, ds.md, "Mach"))
    if inp.target_vfe:
        out.append(TargetCheck("VFE", inp.target_vfe, "VF", inp.target_vfe, ds.vf, _KT))
    return out


def operational_implications(project: Project, inp: StructuralSpeedsInput) -> List[ConditionResult]:
    """Advisory operating-limitation placards + optional target feasibility.

    Both placard families are always shown (per the M2-10 decision): the recip
    yellow-arc set and the turbine VMO/MMO set, each captioned with when it applies.
    A second condition appears only when the user set operational targets. This is
    display/validation only -- no design speed or load is changed.
    """
    ds = design_speed_values(project, inp)
    p = operational_placards(ds)
    fam = ("turbine / 23.335(b)(4) (VMO/MMO govern; no yellow arc)"
           if inp.no_yellow_arc else "recip / naturally-aspirated (yellow arc VC->VNE)")

    placards = ConditionResult(
        title="Preliminary operating-limitation placards (advisory)",
        far_reference="23.1505/23.1511",
        values=[
            LoadValue("Never-exceed VNE (recip)", p.vne, _KT),
            LoadValue("Max structural cruise VNO (recip)", p.vno, _KT),
            LoadValue("Never-exceed Mach MNE (recip)", p.mne),
            LoadValue("Max operating VMO (turbine)", p.vmo, _KT),
            LoadValue("Max operating MMO (turbine)", p.mmo),
            LoadValue("Flap extended VFE", p.vfe, _KT),
        ],
        note=(
            f"Preliminary placards implied by the design speeds; primary family here: {fam}. "
            "VNE = 0.9*VD, VNO = min(VC, 0.89*VNE), MNE = 0.9*MD (14 CFR 23.1505; Ref 1 p47); "
            "turbine airplanes have no yellow arc, VMO/MMO <= VC/MC; VFE = VF (23.1511). "
            "Operating limitations are set at certification (Subpart G), NOT by this tool -- "
            "these are advisory design implications only."
        ),
    )
    results = [placards]

    checks = operational_target_checks(inp, ds)
    if checks:
        values = []
        for c in checks:
            mark = "" if c.feasible else "  <-- INFEASIBLE"
            values.append(LoadValue(
                f"{c.target_label} target {c.target:g} => {c.driver_label} >= "
                f"{c.required:.4g} (have {c.actual:.4g}){mark}", c.required, c.units))
        infeasible = [c for c in checks if not c.feasible]
        note = (
            "All operational targets are achievable with the chosen design speeds."
            if not infeasible else
            "INFEASIBLE target(s): " + "; ".join(
                f"{c.target_label} {c.target:g} needs {c.driver_label} >= {c.required:.4g} "
                f"but {c.driver_label.split(' ')[0]} = {c.actual:.4g}" for c in infeasible)
            + ". Raise the driving design speed(s) or lower the target. "
            "Targets never change the design speeds or any load (display/validation only)."
        )
        results.append(ConditionResult(
            title="Operational-target feasibility (advisory)",
            far_reference="23.1505/23.335(b)(4)",
            values=values,
            note=note,
        ))
    return results


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
