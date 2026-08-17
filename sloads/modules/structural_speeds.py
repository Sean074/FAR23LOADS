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

**The dive-speed basis (F25-2).** ``1.25*VC`` is algebraically 25.335(b)'s first
route, ``VC/MC <= 0.8*VD/MD`` -- so what the paragraph above describes is one half
of a regulation that reads "VD must be selected so that VC/MC is not greater than
0.8 VD/MD, **or** so that the minimum speed margin between VC/MC and VD/MD is the
greater of ...". ``speeds.vd_basis`` selects which route applies:

    VdBasis.SPEED_RATIO   VD >= 1.25*VC                (the default; unchanged)
    VdBasis.MACH_MARGIN   MD >= MC + margin            (25.335(b)(2); 0.07 default)

On the margin route the 1.25*VC floor does **not** apply -- the two are offered
disjunctively -- and the margin policy comes from :func:`resolve_mach_margin`, the
single owner of that decision. The route is restricted to concept category "C"
(decision D-1, F25-2) so the Appendix-A-oracle-locked FAR 23 path is provably
untouched; FAR 23.335(b)(4) would also permit it for N/U/A, and extending it there
is a separate backlog item.

**What the margin check does NOT cover.** 25.335(b) requires the *greater of* the
(b)(1) upset-criterion speed increase (7.5 deg / 20 s / 1.5 g) and the (b)(2) Mach
margin. Only the Mach term is evaluated here; the upset term is not implemented,
so a clean margin is not by itself a sufficiency demonstration. Every margin-route
output says so. Likewise 25.335(a) requires ``VC >= VB + 1.32*U_ref``: ``vb_kt`` is
accepted and checked for ordering only, because U_ref (25.341(a)(5)(i)) arrives
with F25-1's transport gust pack.

Regulation text: ``reference/14CFR_25_335_design_airspeeds.md`` (25.335(a)/(b)/(d),
captured 2026-08-08) and ``reference/14CFR_MC_MD_speed_margin.md`` (the 0.07/0.05
margin history and certification practice, captured 2026-07-20).

Reference: STRSPEED.BAS, Ch 6; worked example Appendix A (VA 121.3, VC 170,
VD 212.5, VF 105.5; n = +3.8 / -1.52; MC 0.323, MD 0.403 at 12000 ft).
"""

from __future__ import annotations

import math
from typing import List, NamedTuple, Optional

from ..constants import (
    IN2_PER_FT2,
    cruise_speed_coefficient,
    dive_ratio_coefficient,
    stall_speed_kt,
    standard_atmosphere,
)
from ..models import (
    ConditionResult,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    StructuralSpeedsInput,
    VdBasis,
)
from ..registry import register

_FAR = "23.335/23.337"
_KT = "kt(EAS)"


# --------------------------------------------------------------------------- #
# MC->MD Mach-margin policy (F25-2) -- the single owner of that decision
# --------------------------------------------------------------------------- #
#: Default minimum MC->MD Mach margin. Entered the Part 25 *rule* at Amdt. 25-91
#: (62 FR 40704, eff. 1997-08-28); AC 25.335-1A (2000) calls 0.07 M "sufficient
#: without further investigation". FAR 23.335(b)(4)(iii) carries the same figure
#: for the commuter tier. See reference/14CFR_MC_MD_speed_margin.md §2.
MACH_MARGIN_DEFAULT = 0.07

#: Absolute regulatory floor -- 25.335(b)(2) ("In any case, the margin may not be
#: reduced to less than 0.05M") and 23.335(b)(4)(ii). Not reducible by any input.
MACH_MARGIN_FLOOR = 0.05


class MachMargin(NamedTuple):
    """The resolved MC->MD margin requirement, with the authority behind it.

    ``reduced`` is True when the requirement sits below :data:`MACH_MARGIN_DEFAULT`
    -- it drives every flag (module note, ``validation.py`` warning, GUI banner),
    so there is exactly one predicate for "this needs justifying"."""
    required: float
    basis: str
    reduced: bool


def resolve_mach_margin(inp: StructuralSpeedsInput) -> MachMargin:
    """Resolve the minimum MC->MD Mach margin for ``inp`` (14 CFR 25.335(b)(2)).

    The **single authority** for that number: the design-speed resolution, the
    M2-10 placard ladder and ``sloads.validation`` all call this rather than
    deciding for themselves (a hardcoded 0.05 in ``operational_target_checks`` is
    what this replaced).

    Policy (user decision D-4, F25-2):

    ==========================  ==============  ==================================
    ``mach_margin_min``         basis given?    outcome
    ==========================  ==============  ==================================
    unset                       --              0.07 M, the rule default
    >= 0.07                     --              accepted as declared
    0.05 .. 0.07                **required**    accepted, ``reduced`` -> flagged
    0.05 .. 0.07                missing         ``ValueError``
    < 0.05                      --              ``ValueError`` (absolute floor)
    ==========================  ==============  ==================================

    Note the distinction that keeps this coherent: the 0.05 floor constrains what
    a user may **declare**; a *chosen VD* that falls short of the declared margin
    is **raised** to meet it, exactly like every other design-speed minimum in
    this module.
    """
    declared = inp.mach_margin_min
    if declared is None:
        return MachMargin(MACH_MARGIN_DEFAULT, "25.335(b)(2) default 0.07 M", False)

    declared = float(declared)
    if declared < MACH_MARGIN_FLOOR:
        raise ValueError(
            f"minimum Mach margin {declared:.4g} is below the absolute regulatory "
            f"floor of {MACH_MARGIN_FLOOR} M -- 14 CFR 25.335(b)(2) ends 'In any "
            "case, the margin may not be reduced to less than 0.05M', and "
            "23.335(b)(4)(ii) says the same. This floor is not an input."
        )
    if declared >= MACH_MARGIN_DEFAULT:
        return MachMargin(declared, f"declared {declared:.4g} M", False)

    basis = (inp.mach_margin_basis or "").strip()
    if not basis:
        raise ValueError(
            f"a minimum Mach margin of {declared:.4g} M is below the "
            f"{MACH_MARGIN_DEFAULT} M default and requires an explicit "
            "rational-analysis basis: set speeds.mach_margin_basis. 14 CFR "
            "25.335(b)(2) permits a lower margin only when 'determined using a "
            "rational analysis that includes the effects of any automatic "
            "systems' -- in practice a credited high-speed protection function "
            "(see reference/14CFR_MC_MD_speed_margin.md §3)."
        )
    return MachMargin(declared, f"rational analysis ({basis})", True)


def maneuver_load_factors(category: str, weight: float, chosen_n: Optional[float],
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
            raise MissingInputError(
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
            total_in2 = next(v.value for v in r.values if v.key == "total_area")
            return total_in2 / IN2_PER_FT2
    if inp.wing_area_sqft:
        return inp.wing_area_sqft
    raise MissingInputError(
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
        raise MissingInputError(
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
    # --- Dive-speed basis (F25-2). Appended with defaults so every existing
    # keyword construction and attribute read is untouched. ---------------------
    #: Which 25.335(b) route set ``vd``.
    vd_basis: VdBasis = VdBasis.SPEED_RATIO
    #: Achieved MD - MC. Meaningful on both routes; only *required* on the margin one.
    mach_margin: float = 0.0
    #: The requirement ``mach_margin`` had to clear (0.0 on the speed-ratio route).
    mach_margin_required: float = 0.0
    #: True when the requirement was reduced below 0.07 M on a rational-analysis basis.
    mach_margin_reduced: bool = False
    #: What ``1.25*VC`` would have been. Reported on the margin route so the
    #: difference between the two regulatory routes is auditable, never implicit.
    vd_ratio_floor: float = 0.0


def _resolve_vd(inp: StructuralSpeedsInput, cat: str, vc: float, vc_min: float,
                ws: float, kt_per_mach: float):
    """Resolve the design dive speed VD by the selected 25.335(b) route.

    Returns ``(vd, vd_min, margin_required, margin_reduced, vd_ratio_floor)``.
    ``vd_min`` keeps its existing meaning -- the floor that actually governed --
    so the reported "Minimum dive VD(min)" row stays honest on both routes.

    The two routes are the regulation's own disjunction (see the module
    docstring), so the margin route deliberately does **not** also apply the
    1.25*VC ratio floor: applying both would re-impose exactly the constraint the
    "or" exists to relieve.
    """
    kd = dive_ratio_coefficient(cat, ws)
    vd_kd_min = kd * vc_min          # K_d * VCmin  (23.335(b)(2); BASIC V2DMIN)
    vd_125 = 1.25 * vc               # == the 25.335(b) "VC/MC <= 0.8 VD/MD" ratio

    if inp.vd_basis is VdBasis.SPEED_RATIO:
        # FAR 23.335(b) requires BOTH minimums -- VD >= max(K_d*VCmin, 1.25*VC).
        # STRSPEED.BAS lines 380/390 (V2DMIN = K2*V1CMIN) use VCmin, not the chosen
        # VC, in the K_d term. Concept mode (Cat C) treats the GA-calibrated K_d
        # term as advisory only, retaining just the absolute 1.25*VC floor.
        vd_min = max(vd_kd_min, vd_125)
        hard_floor = vd_125 if cat == "C" else vd_min
        vd = max(inp.chosen_vd, hard_floor) if inp.chosen_vd is not None else hard_floor
        return vd, vd_min, 0.0, False, vd_125

    # --- The Mach-margin route (25.335(b)(2) / 23.335(b)(4)(iii)) --------------
    if cat != "C":
        raise ValueError(
            f"the Mach-margin dive-speed basis is available in the concept "
            f"category 'C' only, not category '{cat}'. The FAR 23 categories keep "
            "the 23.335(b)(1)-(3) speed-ratio floors so the Appendix A oracles "
            "stay locked; 23.335(b)(4) would permit the margin route for N/U/A "
            "too, and extending it there is tracked in the backlog."
        )
    if inp.shoulder_altitude_ft <= 0:
        raise MissingInputError(
            "the Mach-margin dive-speed basis needs a non-zero shoulder altitude: "
            "the margin is a statement about MC and MD, which are only defined at "
            "the altitude where the Mach limit is established (25.335(b), "
            "'at altitudes where MD is established')."
        )
    if inp.chosen_vd is None:
        raise MissingInputError(
            "the Mach-margin dive-speed basis needs a chosen VD (speeds.chosen_vd): "
            "the route exists so a concept can nominate its own VD/MD, so there is "
            "nothing to check a margin against without one."
        )

    mm = resolve_mach_margin(inp)
    mc = vc / kt_per_mach
    vd_margin_floor = (mc + mm.required) * kt_per_mach
    vd = max(inp.chosen_vd, vd_margin_floor)
    return vd, vd_margin_floor, mm.required, mm.reduced, vd_125


def design_speed_values(project: Project, inp: StructuralSpeedsInput) -> DesignSpeeds:
    """Compute the scalar STRSPEED design speeds + maneuver load factors."""
    w = inp.weight_lb
    if w <= 0:
        raise ValueError("STRSPEED needs a positive design weight")
    s = _wing_area_sqft(project, inp)
    ws = w / s
    cat = inp.category.upper()

    n, n_min, nneg, nneg_min = maneuver_load_factors(cat, w, inp.chosen_n, inp.chosen_nneg)

    vs, vsf = _stall_speeds(project, w, s)

    # Cruise speed VC. In concept mode the K_c/K_d coefficients are GA-calibrated
    # (taper to W/S = 100), so VC(min)/VD(min) are out-of-band *advisories* only --
    # the concept supplies chosen_vc/chosen_vd, which govern.
    kc = cruise_speed_coefficient(cat, ws)
    vc_min = kc * ws ** 0.5
    if inp.vh_kt and vc_min > 0.9 * inp.vh_kt:
        vc_min = 0.9 * inp.vh_kt
    vc = max(inp.chosen_vc, vc_min) if inp.chosen_vc is not None else vc_min

    # The atmosphere is resolved before VD because the Mach-margin route needs MC
    # to place the dive speed (F25-2); the speed-ratio route does not care.
    a, sigma = standard_atmosphere(inp.shoulder_altitude_ft)
    kt_per_mach = math.sqrt(sigma) * a          # KEAS per unit Mach at the shoulder

    # Dive speed VD, by the selected 25.335(b) route.
    vd, vd_min, margin_req, margin_reduced, vd_ratio_floor = _resolve_vd(
        inp, cat, vc, vc_min, ws, kt_per_mach)

    # Maneuver speed VA.
    va_min = vs * math.sqrt(n)
    va = max(inp.chosen_va, va_min) if inp.chosen_va is not None else va_min
    va = min(va, vc)

    # Flap speed VF.
    vf_min = max(1.4 * vs, 1.8 * vsf)
    vf = max(inp.chosen_vf, vf_min) if inp.chosen_vf is not None else vf_min

    # Cruise/dive Mach at the shoulder altitude.
    mc = vc / kt_per_mach
    md = vd / kt_per_mach
    return DesignSpeeds(
        va=va, vc=vc, vd=vd, vf=vf, vs=vs, vsf=vsf,
        vc_min=vc_min, va_min=va_min, vf_min=vf_min,
        vd_min=vd_min, n=n, n_min=n_min, nneg=nneg, nneg_min=nneg_min,
        ws=ws, wing_area_sqft=s, speed_of_sound_kt=a, sigma=sigma, mc=mc, md=md,
        vd_basis=inp.vd_basis, mach_margin=md - mc,
        mach_margin_required=margin_req, mach_margin_reduced=margin_reduced,
        vd_ratio_floor=vd_ratio_floor,
    )


def _margin_route_note(inp: StructuralSpeedsInput, sv: DesignSpeeds) -> str:
    """The mandatory annotation on a Mach-margin-route design-speed result.

    Three things must always be said, because each is a way the number could be
    misread: which route set VD, what the ratio route would have given (so the
    difference between the two regulatory paths is auditable rather than
    implicit), and that the 25.335(b)(1) upset term of the "greater of" is not
    evaluated. A reduced margin adds the certification-risk sentence.
    """
    mm = resolve_mach_margin(inp)
    parts = [
        f"Dive speed on the 25.335(b) Mach-margin route ({mm.basis}): "
        f"MD = {sv.md:.4f} against MC = {sv.mc:.4f}, margin {sv.mach_margin:+.4f} "
        f"vs the required {sv.mach_margin_required:.4f}."
    ]
    if inp.chosen_vd is not None and sv.vd > inp.chosen_vd * (1 + 1e-9):
        parts.append(
            f"The chosen VD {inp.chosen_vd:.4g} kt did not clear that margin and was "
            f"RAISED to {sv.vd:.4g} kt."
        )
    parts.append(
        f"The 1.25*VC speed-ratio floor ({sv.vd_ratio_floor:.4g} kt) does not apply "
        "on this route -- 25.335(b) offers the two disjunctively."
    )
    if sv.mach_margin_reduced:
        parts.append(
            f"REDUCED MARGIN: {sv.mach_margin_required:.4g} M is below the "
            f"{MACH_MARGIN_DEFAULT} M default. 25.335(b)(2) allows this only on a "
            "rational analysis including the effects of automatic systems; it "
            "requires significant justification and carries certification risk "
            "(AC 25.335-1A treats 0.07 M as sufficient without further "
            "investigation). Floor 0.05 M."
        )
    parts.append(
        "NOT A SUFFICIENCY DEMONSTRATION: 25.335(b) requires the GREATER of this "
        "Mach margin and the (b)(1) upset-criterion speed increase (7.5 deg / 20 s "
        "/ 1.5 g); the upset term is not implemented in this suite."
    )
    return " ".join(parts)


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
            LoadValue("Limit positive load factor", n, key="limit_positive_load_factor"),
            LoadValue("Minimum required positive factor", n_min, key="minimum_required_positive_factor"),
            LoadValue("Limit negative load factor", nneg, key="limit_negative_load_factor"),
            LoadValue("Minimum required negative factor", nneg_min, key="minimum_required_negative_factor"),
            LoadValue("Wing loading W/S", ws, "lb/ft^2", key="wing_loading_w_s"),
        ],
        note=(
            "Category C (concept) -- user-defined load factors, no FAR 23.337 cap "
            "applied; results are an unverified extrapolation."
            if cat == "C" else f"Category {cat}."
        ),
    )

    values = [
        LoadValue("Maneuver speed VA", va, _KT, key="maneuver_speed_va"),
        LoadValue("Cruise speed VC", vc, _KT, key="cruise_speed_vc"),
        LoadValue("Dive speed VD", vd, _KT, key="dive_speed_vd"),
        LoadValue("Flap speed VF", vf, _KT, key="flap_speed_vf"),
        LoadValue("Minimum cruise VC(min)", vc_min, _KT, key="minimum_cruise_vc_min"),
        LoadValue("Minimum maneuver VA(min)", va_min, _KT, key="minimum_maneuver_va_min"),
        LoadValue("Minimum flap VF(min)", vf_min, _KT, key="minimum_flap_vf_min"),
        LoadValue("Minimum dive VD(min)", vd_min, _KT, key="minimum_dive_vd_min"),
        LoadValue("Wing area S", s, "ft^2", key="wing_area_s"),
    ]
    notes = []
    if ws > 100.0:
        notes.append(
            f"OUT-OF-BAND: W/S = {ws:.1f} lb/ft^2 exceeds the FAR 23.335 coefficient "
            "schedule (tabulated to W/S = 100). Kc/Kd are held at their W/S = 100 "
            "values (28.6 / 1.35); VC(min)/VD(min) are GA-extrapolated advisories -- "
            "supply chosen VC/VD."
        )
    if sv.vd_basis is VdBasis.MACH_MARGIN:
        values += [
            LoadValue("Dive Mach margin MD-MC", sv.mach_margin, key="dive_mach_margin"),
            LoadValue("Required Mach margin", sv.mach_margin_required,
                      key="required_mach_margin"),
        ]
        notes.append(_margin_route_note(inp, sv))
    speeds = ConditionResult(
        title="Structural design speeds",
        far_reference="25.335(b)" if sv.vd_basis is VdBasis.MACH_MARGIN else "23.335",
        values=values,
        note=" ".join(notes),
    )

    mach = ConditionResult(
        title="Cruise/dive Mach at shoulder altitude",
        far_reference="23.335(b)",
        values=[
            LoadValue("Shoulder altitude", inp.shoulder_altitude_ft, "ft", key="shoulder_altitude"),
            LoadValue("Speed of sound", a, _KT, key="speed_of_sound"),
            LoadValue("Density ratio sigma", sigma, key="density_ratio_sigma"),
            LoadValue("Cruise Mach MC", mc, key="cruise_mach_mc"),
            LoadValue("Dive Mach MD", md, key="dive_mach_md"),
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
# VNO<=min(VC, 0.89VNE)), 23.1511 (VFE<=VF), 23.335(b)(4) (the MC->MD margin).
# The MC->MD margin used to be a hardcoded 0.05 here. It is now resolved by
# resolve_mach_margin (F25-2), so the ladder and the design-speed resolution can
# never disagree about the same project's margin.
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
    + the resolved Mach margin;  target VFE => VF >= VFE. Warn-only: nothing here
    mutates a speed.

    The MMO row takes its margin from :func:`resolve_mach_margin` (F25-2) -- it was
    a hardcoded 0.05, which understated the requirement for every transport concept
    and could contradict the margin the same project's dive speed was resolved on.
    """
    margin = resolve_mach_margin(inp).required
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
                               inp.target_mmo + margin, ds.md, "Mach"))
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

    # The MC->MD margin the chosen speeds actually imply, shown with the VMO/MMO
    # family (F25-2; reference/14CFR_MC_MD_speed_margin.md §4 asks for exactly
    # this). It is reported on BOTH routes -- on the speed-ratio route it is the
    # margin the 1.25*VC floor happened to produce, which is the number a
    # transport concept needs to see even though nothing checked it.
    implied_margin = ds.md - ds.mc
    margin_note = ""
    if inp.shoulder_altitude_ft:
        if implied_margin < MACH_MARGIN_FLOOR:
            margin_note = (
                f" The implied MC->MD margin is {implied_margin:+.4f} M, BELOW the "
                f"{MACH_MARGIN_FLOOR} M absolute floor of 25.335(b)(2)/23.335(b)(4)(ii)."
            )
        elif implied_margin < MACH_MARGIN_DEFAULT:
            margin_note = (
                f" The implied MC->MD margin is {implied_margin:+.4f} M, below the "
                f"{MACH_MARGIN_DEFAULT} M default -- for a transport that needs the "
                "25.335(b)(2) rational-analysis route (automatic systems credited), "
                "which carries certification risk."
            )

    values = [
        LoadValue("Never-exceed VNE (recip)", p.vne, _KT, key="never_exceed_vne_recip"),
        LoadValue("Max structural cruise VNO (recip)", p.vno, _KT, key="max_structural_cruise_vno_recip"),
        LoadValue("Never-exceed Mach MNE (recip)", p.mne, key="never_exceed_mach_mne_recip"),
        LoadValue("Max operating VMO (turbine)", p.vmo, _KT, key="max_operating_vmo_turbine"),
        LoadValue("Max operating MMO (turbine)", p.mmo, key="max_operating_mmo_turbine"),
        LoadValue("Flap extended VFE", p.vfe, _KT, key="flap_extended_vfe"),
    ]
    if inp.shoulder_altitude_ft:
        values.append(LoadValue("Implied MC->MD margin", implied_margin,
                                key="implied_mc_md_margin"))

    placards = ConditionResult(
        title="Preliminary operating-limitation placards (advisory)",
        far_reference="23.1505/23.1511",
        values=values,
        note=(
            f"Preliminary placards implied by the design speeds; primary family here: {fam}. "
            "VNE = 0.9*VD, VNO = min(VC, 0.89*VNE), MNE = 0.9*MD (14 CFR 23.1505; Ref 1 p47); "
            "turbine airplanes have no yellow arc, VMO/MMO <= VC/MC; VFE = VF (23.1511). "
            "Operating limitations are set at certification (Subpart G), NOT by this tool -- "
            "these are advisory design implications only." + margin_note
        ),
    )
    results = [placards]

    checks = operational_target_checks(inp, ds)
    if checks:
        values = []
        for i, c in enumerate(checks, start=1):
            mark = "" if c.feasible else "  <-- INFEASIBLE"
            # The label is a whole sentence (target, driver, actual, feasibility);
            # the key is the check's position in the ordered check list.
            values.append(LoadValue(
                f"{c.target_label} target {c.target:g} => {c.driver_label} >= "
                f"{c.required:.4g} (have {c.actual:.4g}){mark}", c.required, c.units,
                key=f"target_check_{i}"))
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
        raise MissingInputError("Project has no 'speeds' inputs for the structural_speeds module")
    return ModuleResult(module=MODULE_NAME, conditions=design_speeds(project, project.speeds))


register(MODULE_NAME, run)

# --------------------------------------------------------------------------- #
# Public surface (M4-12b). Names not listed here are module-private: an
# underscore-free name outside this list is still not an import contract, and
# ``app/`` must import nothing underscored from ``sloads``.
# --------------------------------------------------------------------------- #
__all__ = [
    "MACH_MARGIN_DEFAULT",
    "MACH_MARGIN_FLOOR",
    "MODULE_NAME",
    "DesignSpeeds",
    "MachMargin",
    "OperationalPlacards",
    "TargetCheck",
    "design_speed_values",
    "design_speeds",
    "maneuver_load_factors",
    "operational_implications",
    "operational_placards",
    "operational_target_checks",
    "resolve_mach_margin",
    "run",
]
