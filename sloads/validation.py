"""Input-consistency validation -- pure, unit-testable predicates over a Project.

A companion to :mod:`sloads.applicability`: where that module reports whether an
airplane exceeds the FAR 23 *applicability* band, this one reports whether the
definition inputs are self-consistent. Both are pure (no Streamlit, no file
access); the definition pages surface the returned warnings as ``st.warning``.

The checks are deliberately conservative -- each yields a warning only on a clear
inconsistency and is silent on well-formed input (in particular, it yields no
warnings on the Appendix-A GA fixture). Each :class:`ConsistencyWarning` carries a
``page`` tag so a view renders only the subset it owns (see
``consistency_warnings`` below and ``GUI_design.md`` §8.3).

Checks (14 CFR / Reference-1 context in each predicate):
- ``taper_gt_1``          -- taper ratio (tip/root chord) above 1 (WINGGEOM/TAU).
- ``nonpositive_area``    -- a wing/reference area that is zero or negative.
- ``le_te_ordering``      -- a surface whose leading edge is not forward of its
                             trailing edge, or edge polylines not ordered inboard->out.
- ``area_mismatch``       -- Configuration & Layout wing area disagreeing with the
                             WINGGEOM planform area by more than a tolerance.
- ``cg_outside_envelope`` -- the WTONECG centre of gravity outside the WTENV
                             structural CG envelope (14 CFR 23.23; Reference 1 Ch 3).
- ``operational_target_infeasible`` -- an operational placard target (VNE/VNO/VMO/
                             MMO/VFE) the chosen design speeds cannot achieve (M2-10;
                             14 CFR 23.1505/23.335(b)(4)). Advisory; no load changes.
- ``safety_factor_out_of_range`` -- a per-case limit->ultimate ``safety_factor``
                             outside the legal [1.0, 1.5] band (14 CFR 23.303;
                             the factor is owned by the load-case definition).
                             Advisory companion to ``io._safety_factor``'s
                             read-time coercion (M4-14).
- ``safety_factor_override_unknown_family`` / ``safety_factor_override_without_basis`` /
  ``safety_factor_override_out_of_range`` / ``safety_factor_below_regulation``
                          -- the governing safety-factor table's override layer
                             (M4-8 / decision G-11; 14 CFR 23.303). Every row is
                             user-editable, so an override must name a real family,
                             state a basis, and -- when it sits below the value the
                             regulation derives -- say so as a certification risk.
                             See ``_check_safety_factor_overrides``.
- ``aero_clmax_unreachable`` / ``aero_lift_slope_sign`` / ``aero_drag_negative`` /
  ``aero_drag_polar_shape`` / ``aero_clmax_neg_sign``
                          -- coefficient-entry checks on the airplane-less-tail
                             polynomials (M4-5; Ref 1 Ch 7/Ch 8). See
                             ``_check_aero_coefficients``.
- ``gross_ge_max_landing`` / ``landing_light_le_max`` / ``landing_cg_ordering`` /
  ``landing_cg_below_axle`` / ``landing_cg_names`` -- the LANDLOAD weight/CG
                             hierarchy (M4-17d; 14 CFR 23.473-23.499). See
                             ``_check_landing_hierarchy``.

Two public helpers here are *not* checks and are consumed by ``app/``:
``wtenv_cg_limits`` (the weight-agnostic structural CG hull) and
``wtenv_fwd_cg_limit_at_weight`` (the forward limit interpolated at one weight).
:func:`landing_reaction_warnings` is a **post-compute** sanity pass over a solved
LANDLOAD reaction table -- deliberately outside :func:`consistency_warnings`,
which must stay input-only so no definition page pays for a gear solve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

from . import cg_cases
from .constants import ULTIMATE_FACTOR
from .modules.wing_geometry import interp_x
from .models import (
    GROUND_CASE_ROLE_ORDER,
    AnalysisKind,
    GearCarrier,
    MassComponent,
    MissingInputError,
    Project,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import GearReactionCase

# Pages that render consistency warnings (the ``page`` tag on each warning).
PAGE_CONFIGURATION = "configuration_layout"
PAGE_WING_GEOMETRY = "wing_geometry"
PAGE_STRUCTURAL_SPEEDS = "structural_speeds"
PAGE_WEIGHT_CG = "weight_cg_inertia"
PAGE_EXPORT = "export_report"
PAGE_LANDING = "landing_loads"
PAGE_AERO_COEFFS = "aero_coefficients"

# The three canonical LANDLOAD loadings, in the order LANDLOAD consumes them (UG
# fig 18.2). Since decision G-3a the *contract* is ``CgCase.role``, not the name --
# these survive as the display names the GUI seeds a new project with and as the
# source the v46 migration reads a legacy file's roles from.
LANDING_CG_NAMES = ("aft max landing", "fwd max landing", "fwd light")

# Fractional tolerance for the Configuration-vs-WINGGEOM wing-area agreement check.
_AREA_MISMATCH_TOL = 0.05


@dataclass(frozen=True)
class ConsistencyWarning:
    """One input-consistency finding.

    ``code`` is a stable slug (for tests); ``message`` is the human-readable
    ``st.warning`` text; ``page`` is the view-key that should render it.
    """
    code: str
    message: str
    page: str


def _wing_geometry_area_sqft(project: Project) -> Optional[float]:
    """WINGGEOM planform total area (ft^2) for the 'wing' surface, or None."""
    if project.geometry is None:
        return None
    surf = project.geometry.by_name("wing")
    if surf is None:
        return None
    from .modules.wing_geometry import surface_properties
    try:
        r = surface_properties(surf)
    except (ValueError, ZeroDivisionError):
        return None
    total_in2 = next((v.value for v in r.values if v.key == "total_area"), None)
    return total_in2 / 144.0 if total_in2 is not None else None


def _check_taper(project: Project) -> List[ConsistencyWarning]:
    out: List[ConsistencyWarning] = []
    cfg = project.geometry.parametric if project.geometry is not None else None
    if cfg is not None and cfg.taper_ratio and cfg.taper_ratio > 1.0:
        out.append(ConsistencyWarning(
            "taper_gt_1",
            f"Wing taper ratio {cfg.taper_ratio:.3f} is greater than 1 (tip chord "
            "exceeds root chord). Taper ratio is tip/root chord and is normally "
            "0 < λ ≤ 1 (WINGGEOM/TAU).",
            PAGE_CONFIGURATION))
    if project.aero is not None:
        for s in project.aero.surfaces:
            if s.taper_ratio and s.taper_ratio > 1.0:
                out.append(ConsistencyWarning(
                    "taper_gt_1",
                    f"Aero surface '{s.name}' taper ratio {s.taper_ratio:.3f} is "
                    "greater than 1 (tip chord exceeds root chord).",
                    PAGE_WING_GEOMETRY))
    return out


def _check_area(project: Project) -> List[ConsistencyWarning]:
    out: List[ConsistencyWarning] = []
    cfg = project.geometry.parametric if project.geometry is not None else None
    if cfg is not None and cfg.wing_area_sqft is not None and cfg.wing_area_sqft <= 0.0:
        # Only warn once a layout is being defined (non-default fuselage/aspect).
        if cfg.aspect_ratio or cfg.taper_ratio or cfg.fuselage_length:
            out.append(ConsistencyWarning(
                "nonpositive_area",
                "Wing reference area S is zero or negative. It drives the wing "
                "loading W/S and every downstream load (14 CFR 23.335).",
                PAGE_CONFIGURATION))
    geo_area = _wing_geometry_area_sqft(project)
    if geo_area is not None and geo_area <= 0.0:
        out.append(ConsistencyWarning(
            "nonpositive_area",
            "WINGGEOM planform area is zero or negative -- check the wing "
            "leading-/trailing-edge points.",
            PAGE_WING_GEOMETRY))
    return out


def _check_le_te_ordering(project: Project) -> List[ConsistencyWarning]:
    out: List[ConsistencyWarning] = []
    if project.geometry is None:
        return out
    for surf in project.geometry.surfaces:
        le = surf.leading_edge
        te = surf.trailing_edge
        if not le or not te or len(le) != len(te):
            continue
        # The leading edge must be forward of (lower fuselage station X than) the
        # trailing edge at each matching butt line (WINGGEOM edge polylines).
        bad_chord = any(lx >= tx for (lx, _ly), (tx, _ty) in zip(le, te))
        # Edge points are prompted inboard -> outboard (increasing |Y|).
        ys = [y for _x, y in le]
        bad_order = any(b < a for a, b in zip([abs(v) for v in ys], [abs(v) for v in ys][1:]))
        if bad_chord:
            out.append(ConsistencyWarning(
                "le_te_ordering",
                f"Surface '{surf.name}': a leading-edge station is not forward of "
                "the trailing edge (LE fuselage station X must be less than TE).",
                PAGE_WING_GEOMETRY))
        if bad_order:
            out.append(ConsistencyWarning(
                "le_te_ordering",
                f"Surface '{surf.name}': edge points are not ordered inboard→outboard "
                "(butt line |Y| should increase).",
                PAGE_WING_GEOMETRY))
    return out


def _check_area_mismatch(project: Project) -> List[ConsistencyWarning]:
    cfg = project.geometry.parametric if project.geometry is not None else None
    if cfg is None or not cfg.wing_area_sqft or cfg.wing_area_sqft <= 0.0:
        return []
    geo_area = _wing_geometry_area_sqft(project)
    if geo_area is None or geo_area <= 0.0:
        return []
    rel = abs(cfg.wing_area_sqft - geo_area) / cfg.wing_area_sqft
    if rel > _AREA_MISMATCH_TOL:
        msg = (
            f"Wing area mismatch: Configuration & Layout has "
            f"{cfg.wing_area_sqft:,.1f} ft² but the WINGGEOM planform is "
            f"{geo_area:,.1f} ft² ({rel * 100:.0f}% apart). They should agree.")
        return [ConsistencyWarning("area_mismatch", msg, PAGE_CONFIGURATION),
                ConsistencyWarning("area_mismatch", msg, PAGE_WING_GEOMETRY)]
    return []


def _wtenv_stations(project: Project) -> Optional[Dict[str, float]]:
    """``{label: value}`` from a successful WTENV run, or None when it cannot run.

    Shared by :func:`wtenv_cg_limits` and :func:`wtenv_fwd_cg_limit_at_weight`; the
    guards and the swallowed-exception set are the originals from ``wtenv_cg_limits``.
    """
    if project.weight is None or project.weight.envelope is None:
        return None
    if project.geometry is None or project.geometry.by_name("wing") is None:
        return None
    from .modules.weight_envelope import envelope as compute_envelope
    try:
        results = compute_envelope(project, project.weight.envelope)
    except (ValueError, ZeroDivisionError, KeyError):
        return None
    return {v.label: v.value for r in results for v in r.values}


def wtenv_cg_limits(project: Project) -> Optional["tuple[float, float]"]:
    """(forward-most, aft-most) structural CG station (in) from WTENV, or None.

    Needs the WTENV envelope slice and the wing geometry it reads XLEMAC/MAC from;
    returns None (check skipped) when either is absent or the calc cannot run.

    This is the weight-agnostic **outer hull** -- the forward station is the
    forward-most reached at *any* weight (``min`` of the gross and regardless
    stations), which is what an envelope-containment check wants. For the forward
    limit *at a given weight* (what a landing case wants) use
    :func:`wtenv_fwd_cg_limit_at_weight`.

    Public (M2R-5): also seeds the Landing Loads CG-case editor and the Weight/CG
    grid overlay, so it is imported by ``app/`` -- hence a public name (M4-12: ``app/``
    must not import ``sloads`` underscore symbols).
    """
    limits = _wtenv_stations(project)
    if limits is None:
        return None
    fwd_candidates = [limits[k] for k in ("Forward gross station", "Forward regardless station")
                      if k in limits]
    aft = limits.get("Aft gross station")
    if not fwd_candidates or aft is None:
        return None
    return min(fwd_candidates), aft


def wtenv_fwd_cg_limit_at_weight(project: Project, weight_lb: float) -> Optional[float]:
    """The WTENV **forward** structural CG limit (fuselage station, in) at ``weight_lb``.

    WTENV's forward limit is a two-point line in the weight/CG envelope (Ref 1 Ch 3;
    14 CFR 23.23): the *forward-regardless* station applies at
    ``envelope.fwd_regardless_weight`` and the *forward-gross* station at
    ``envelope.gross_weight``, with the limit linear in weight between them. The
    manual reads it **at the landing weight** -- Appendix A p230 pairs the 3230 lb
    max landing weight with 76.12 in, between 72.643 in @ 2800 lb and 77.490 in @
    3400 lb. (``wtenv_cg_limits`` returns the weight-agnostic hull, 72.643 in, which
    is the right answer for a containment check and the wrong one for a landing
    case -- pairing it with the max landing weight was the M4-17c seed defect.)

    **Clamped, never extrapolated**: at or below the lighter anchor the lighter
    anchor's station is returned, at or above the heavier anchor the heavier one's,
    so a mis-entered envelope cannot run the limit off the end of the line.

    Returns ``None`` -- and the caller must then leave the cell blank rather than
    fabricate a station (M4-17c) -- when ``weight_lb <= 0``, when the envelope or
    wing geometry is absent, when WTENV cannot run, or when either anchor weight or
    station is missing.

    Public (M4-17c): the Landing Loads CG-case seed imports it, and ``app/`` must not
    import ``sloads`` underscore symbols (M4-12).
    """
    if weight_lb <= 0:
        return None
    limits = _wtenv_stations(project)
    if limits is None:
        return None
    fwd_s = limits.get("Forward gross station")
    reg_s = limits.get("Forward regardless station")
    if fwd_s is None or reg_s is None:
        return None
    env = project.weight.envelope
    w_gross, w_reg = env.gross_weight, env.fwd_regardless_weight
    if not w_gross or not w_reg or w_gross <= 0 or w_reg <= 0:
        return None
    if w_gross == w_reg:
        return fwd_s
    # Anchor by weight, not by name, so a swapped envelope clamps instead of running away.
    (w_lo, s_lo), (w_hi, s_hi) = (
        ((w_reg, reg_s), (w_gross, fwd_s)) if w_reg < w_gross
        else ((w_gross, fwd_s), (w_reg, reg_s)))
    if weight_lb <= w_lo:
        return s_lo
    if weight_lb >= w_hi:
        return s_hi
    return s_lo + (weight_lb - w_lo) / (w_hi - w_lo) * (s_hi - s_lo)


def _check_cg_envelope(project: Project) -> List[ConsistencyWarning]:
    if project.weight is None or not project.weight.items:
        return []
    limits = wtenv_cg_limits(project)
    if limits is None:
        return []
    fwd, aft = limits
    from .modules.weight_onecg import weights_and_inertia
    try:
        result = weights_and_inertia(project.weight.items)
    except (ValueError, ZeroDivisionError):
        return []
    xbar = next((v.value for v in result.values if v.key == "xbar_fus_station"), None)
    if xbar is None:
        return []
    if xbar < fwd - 1e-6 or xbar > aft + 1e-6:
        return [ConsistencyWarning(
            "cg_outside_envelope",
            f"Loading CG at station {xbar:,.1f} in is outside the WTENV structural "
            f"CG envelope ({fwd:,.1f}–{aft:,.1f} in). Adjust the loading or the "
            "envelope limits (14 CFR 23.23).",
            PAGE_WEIGHT_CG)]
    return []


def _check_operational_targets(project: Project) -> List[ConsistencyWarning]:
    """Warn when an operational placard *target* is infeasible for the chosen
    design speeds (M2-10). Advisory: nothing here changes a speed or a load.

    Reads the same ladder inversion as the Design Speeds page
    (``operational_target_checks``); silent when no targets are set or the design
    speeds cannot be computed (e.g. CLmax not entered yet).
    """
    speeds = project.speeds
    if speeds is None:
        return []
    if not any((speeds.target_vne, speeds.target_vno, speeds.target_vmo,
                speeds.target_mmo, speeds.target_vfe)):
        return []
    from .modules.structural_speeds import (
        design_speed_values,
        operational_target_checks,
    )
    try:
        ds = design_speed_values(project, speeds)
    except (ValueError, ZeroDivisionError, KeyError):
        return []
    out: List[ConsistencyWarning] = []
    for c in operational_target_checks(speeds, ds):
        if not c.feasible:
            out.append(ConsistencyWarning(
                "operational_target_infeasible",
                f"Operational target {c.target_label} = {c.target:g} {c.units} needs "
                f"{c.driver_label} ≥ {c.required:.4g} {c.units}, but the chosen "
                f"{c.driver_label.split(' ')[0]} = {c.actual:.4g} {c.units}. Raise the "
                "design speed or lower the target (advisory only — 14 CFR 23.1505/"
                "23.335(b)(4); design speeds and loads are unchanged).",
                PAGE_STRUCTURAL_SPEEDS))
    return out


def _check_dive_speed_basis(project: Project) -> List[ConsistencyWarning]:
    """Surface what the 25.335(b) dive-speed route implies (F25-2).

    Three findings, all advisory -- none changes a speed or a load:

    ``mach_margin_reduced``
        the margin requirement was declared below 0.07 M on a rational-analysis
        basis. Legal under 25.335(b)(2), but it must never pass silently.
    ``mach_margin_below_ratio_floor``
        informational: the margin route put VD below 1.25*VC. That is the whole
        point of the route, and it is surfaced so a reviewer comparing against a
        FAR 23 habit is never surprised by it.
    ``vb_above_vc``
        VB (25.335(d)) is at or above VC, which inverts the 25.335(a) ordering.

    Silent when the design speeds cannot be computed yet, like every other check
    here -- a half-filled project is not a defect.
    """
    speeds = project.speeds
    if speeds is None:
        return []
    from .models import VdBasis
    from .modules.structural_speeds import MACH_MARGIN_DEFAULT, design_speed_values

    try:
        ds = design_speed_values(project, speeds)
    except (ValueError, ZeroDivisionError, KeyError):
        return []

    out: List[ConsistencyWarning] = []
    if ds.vd_basis is VdBasis.MACH_MARGIN:
        if ds.mach_margin_reduced:
            out.append(ConsistencyWarning(
                "mach_margin_reduced",
                f"The MC→MD Mach margin is set to {ds.mach_margin_required:.4g} M, "
                f"below the {MACH_MARGIN_DEFAULT} M default. 14 CFR 25.335(b)(2) "
                "permits this only on a rational analysis including the effects of "
                "automatic systems (a credited high-speed protection function): it "
                "requires significant justification and represents a certification "
                f"risk. Basis on file: “{(speeds.mach_margin_basis or '').strip()}”. "
                "AC 25.335-1A treats 0.07 M as sufficient without further "
                "investigation; 0.05 M is an absolute floor.",
                PAGE_STRUCTURAL_SPEEDS))
        if ds.vd < ds.vd_ratio_floor - 1e-9:
            out.append(ConsistencyWarning(
                "mach_margin_below_ratio_floor",
                f"VD = {ds.vd:.4g} kt sits below the 1.25·VC speed-ratio floor "
                f"({ds.vd_ratio_floor:.4g} kt) because the Mach-margin route was "
                "selected. 14 CFR 25.335(b) offers the two routes disjunctively, so "
                "this is expected — but note the margin check covers only the "
                "(b)(2) Mach term, not the (b)(1) upset criterion, which this suite "
                "does not implement.",
                PAGE_STRUCTURAL_SPEEDS))
    if speeds.vb_kt and speeds.vb_kt >= ds.vc:
        out.append(ConsistencyWarning(
            "vb_above_vc",
            f"The rough-air speed VB = {speeds.vb_kt:.4g} kt is at or above "
            f"VC = {ds.vc:.4g} kt. 14 CFR 25.335(a)(2) requires VC ≥ VB + 1.32·U_ref, "
            "so VC must exceed VB. (Only the ordering is checked here — the "
            "1.32·U_ref term needs the 25.341 reference gust schedule, which is not "
            "yet implemented.)",
            PAGE_STRUCTURAL_SPEEDS))
    return out


def safety_factor_valid(value) -> bool:
    """True when ``value`` is a usable per-case limit->ultimate factor: numeric,
    finite and inside the legal **[1.0, ULTIMATE_FACTOR]** band (14 CFR 23.303 —
    the factor is owned by the load-case definition; a case already at ultimate
    is 1.0, an agreed 23.302/25.302 failure-case factor lies between).

    Public (M4-14): shared by ``io._safety_factor`` (read-time coercion), the
    check below, and the Project JSON Editor's Apply handler (``app/`` must not
    import underscore names, M4-12)."""
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and 1.0 <= value <= ULTIMATE_FACTOR)


def _check_safety_factors(project: Project) -> List[ConsistencyWarning]:
    """Warn on a per-case ``safety_factor`` outside the legal [1.0, 1.5] band.

    The factor is owned by the load-case definition (14 CFR 23.303; a case
    already at ultimate is 1.0, and a 23.302/25.302 agreed failure-case factor
    lies between). ``io._safety_factor`` already coerces a corrupt *persisted*
    value to ``ULTIMATE_FACTOR`` on load, so this check mainly catches a value
    mutated in-session (or set programmatically) before it reaches a deliverable:
    below 1.0 the export would be **unconservative while still labelled
    ULTIMATE**; above 1.5 is conservative but non-standard.
    """
    cases = []
    if project.envelope is not None and project.envelope.critical is not None:
        cases += [(c.label or c.component, c.safety_factor)
                  for c in project.envelope.critical.conditions]
    loads = project.loads
    if loads is not None:
        for family in (loads.wing_air, loads.wing_inertia, loads.wing_net,
                       loads.body_net, loads.tail_chordwise, loads.control_surface):
            cases += [(r.case, r.safety_factor) for r in family]
    out: List[ConsistencyWarning] = []
    for name, sf in cases:
        if not safety_factor_valid(sf):
            out.append(ConsistencyWarning(
                "safety_factor_out_of_range",
                f"Load case '{name}' has safety_factor = {sf!r}, outside the legal "
                f"[1.0, {ULTIMATE_FACTOR:g}] band (14 CFR 23.303; the factor is set "
                "by the load-case definition). Below 1.0 the exported loads would "
                "be unconservative while still labelled ULTIMATE. A corrupt value "
                f"in a saved project.json is reset to {ULTIMATE_FACTOR:g} on load; "
                "re-run the producing module to restore the case's own factor.",
                PAGE_EXPORT))
    return out


def _check_safety_factor_overrides(project: Project) -> List[ConsistencyWarning]:
    """Guard the governing safety-factor table's override layer (M4-8 / G-11).

    Every row of that table is user-editable, including the regulation-fixed ones.
    That reach is safe for the oracles — the factor is applied at the render/export
    boundary only, so no override can move a LIMIT calc value — but it is *not*
    safe for the deliverable, which can be shipped at a non-regulatory factor.
    Three of G-11's four mitigations are enforced here (the fourth, override
    marking, is in ``report``/``safety_factors``):

    * an unknown family key is an error, not a silently ignored row;
    * an override without a ``basis`` is rejected — the price of editability;
    * an override **below** the regulation's derived value raises an explicit
      certification-risk warning (the F25-2-d precedent: a floor constrains what
      may be *declared*, and the declaration is what must be visible).
    """
    from .safety_factors import FAMILIES, GoverningTable

    policy = project.safety_factors
    if policy is None or not policy.overrides:
        return []
    out: List[ConsistencyWarning] = []
    keys = {f.key for f in FAMILIES}
    for ov in policy.overrides:
        if ov.family not in keys:
            out.append(ConsistencyWarning(
                "safety_factor_override_unknown_family",
                f"Safety-factor override names family {ov.family!r}, which is not a "
                f"row of the governing table ({', '.join(sorted(keys))}). The "
                "override is ignored, so the deliverable is NOT carrying the factor "
                "you intended.", PAGE_EXPORT))
            continue
        if not str(ov.basis).strip():
            out.append(ConsistencyWarning(
                "safety_factor_override_without_basis",
                f"Safety-factor override on '{ov.family}' has no basis. Every row of "
                "the governing table is editable, and the condition of that is that "
                "an override states why it exists — an undeclared deviation is "
                "invisible to the analyst reading the deliverable.", PAGE_EXPORT))
        if not safety_factor_valid(ov.factor):
            out.append(ConsistencyWarning(
                "safety_factor_override_out_of_range",
                f"Safety-factor override on '{ov.family}' is {ov.factor!r}, outside "
                f"the legal [1.0, {ULTIMATE_FACTOR:g}] band (14 CFR 23.303).",
                PAGE_EXPORT))
    for row in GoverningTable.for_project(project).overrides:
        if row.below_regulation:
            out.append(ConsistencyWarning(
                "safety_factor_below_regulation",
                f"CERTIFICATION RISK: '{row.label}' ({row.far_reference}) is "
                f"overridden to SF = {row.factor:g}, below the {row.derived_factor:g} "
                "the regulation derives for it. Loads exported under this row are "
                "labelled ULTIMATE but are not ultimate by 14 CFR 23.303/25.303. "
                f"Declared basis: {row.basis or '(none)'}.", PAGE_EXPORT))
    return out


def _check_landing_hierarchy(project: Project) -> List[ConsistencyWarning]:
    """The LANDLOAD weight/CG hierarchy (M4-17d). Warn-only -- no math changes.

    LANDLOAD consumes its three loadings **positionally** (aft max landing, fwd max
    landing, fwd light; UG fig 18.2) and derives ``WR = MTOW/MLW``, so an
    inconsistent set computes silently and plausibly. The checks:

    * ``landing_light_le_max`` -- the fwd-light loading must not exceed the max
      landing weight; it is the light corner of the envelope.
    * ``landing_cg_ordering`` -- the aft loading's station must be aft of both
      forward loadings'. AP/BP/CP are formed about ``xcg``, so a swap silently
      mis-assigns the nose-gear and braked-roll lever arms.
    * ``landing_cg_below_axle`` -- every ``zcg`` must be above the static main-axle
      waterline. A CG at or below the axle is geometrically impossible for a
      tricycle airplane, and is the signature of the zero-waterline seed (M4-17c).
    * ``landing_case_weight_is_mlw`` -- decision G-4 made MLW the single owner of
      the landing weight, so a roled max-landing case that disagrees with it is an
      **error**, not a preference: it is one number, and a certified airplane-level
      limit rather than a property of a loading.

    ``gross_ge_max_landing`` and ``landing_cg_names`` are gone with the fields they
    policed. ``GW`` is no longer an overridable copy on the landing slice but the
    MTOW SSOT, and the ordering chain below checks ``MLW <= MTOW`` for every
    project rather than only for one with three landing cases; the canonical-name
    check was the workaround for the positional contract that ``CgCase.role``
    replaced (G-3a).

    Silent on the Appendix-A GA fixture (2803 <= 3230; 85.1 aft of 76.12/72.64;
    zcg 92-93 in above the 59.6 in static axle; both max-landing cases at 3230).
    """
    try:
        cgs = cg_cases.landing_role_cases(project)
    except (MissingInputError, ValueError):
        return []
    out: List[ConsistencyWarning] = []
    aft, fwd_max, fwd_light = cgs
    w_land = cg_cases.max_landing_weight(project, required=False)

    if w_land > 0 and fwd_light.weight_lb > w_land + 1e-6:
        out.append(ConsistencyWarning(
            "landing_light_le_max",
            f"The '{fwd_light.name}' loading weighs {fwd_light.weight_lb:,.0f} lb, more "
            f"than the max landing weight {w_land:,.0f} lb. It is the *light* corner of "
            "the landing envelope (UG fig 18.2).",
            PAGE_LANDING))
    if w_land > 0:
        off = [c for c in (aft, fwd_max) if abs(c.weight_lb - w_land) > 1e-6]
        if off:
            out.append(ConsistencyWarning(
                "landing_case_weight_is_mlw",
                "The max-landing loadings must weigh exactly the max landing weight "
                f"{w_land:,.0f} lb (weight.max_landing_weight_lb, the single owner "
                "since decision G-4 -- only their CG station is entered): "
                + ", ".join(f"'{c.name}' {c.weight_lb:,.0f} lb" for c in off) + ".",
                PAGE_LANDING))
    if aft.xcg <= max(fwd_max.xcg, fwd_light.xcg):
        out.append(ConsistencyWarning(
            "landing_cg_ordering",
            f"The aft loading '{aft.name}' is at station {aft.xcg:,.2f} in, not aft of "
            f"the forward loadings ({fwd_max.xcg:,.2f} / {fwd_light.xcg:,.2f} in). The "
            "AP/BP/CP lever arms are formed about xcg, so a fwd/aft swap mis-assigns "
            "the nose-gear and braked-roll reactions.",
            PAGE_LANDING))
    lg = project.geometry.landing_gear if project.geometry is not None else None
    if lg is not None:
        axle_wl = lg.main_gear.axle_static[1]
        if axle_wl > 0:
            low = [c for c in cgs if c.zcg <= axle_wl]
            if low:
                out.append(ConsistencyWarning(
                    "landing_cg_below_axle",
                    "Landing CG waterline at or below the static main-axle waterline "
                    f"({axle_wl:,.1f} in) for: "
                    + ", ".join(f"'{c.name}' zcg={c.zcg:,.1f} in" for c in low)
                    + ". A CG at or below the axle is geometrically impossible for a "
                    "tricycle airplane; a zero waterline puts the CG on the ground "
                    "line and inverts the nose-gear reaction (M4-17c).",
                    PAGE_LANDING))
    return out


def landing_reaction_warnings(cases: "List[GearReactionCase]") -> List[ConsistencyWarning]:
    """Post-compute sanity checks on a solved LANDLOAD reaction table (M4-17d).

    Pure, and deliberately *outside* :func:`consistency_warnings`: these need the
    solved reactions, and that aggregate must stay an input-only predicate that no
    definition page pays a gear solve for. The Landing Loads view calls this after
    ``modules.landing.build_landing``.

    * ``landing_negative_vertical`` -- any VMP or VNP below zero. A wheel cannot pull
      the airplane down; a negative vertical reaction means the CG/lever arms are
      wrong. With a zero waterline the GA-6 nose reactions run -233..-2887 lb.
    * ``landing_zero_nose`` -- VNP is zero on a 3-wheel level case (1-3) or a
      braked-roll nose-down case (13-15), where the nose wheel is loaded by
      construction.
    """
    out: List[ConsistencyWarning] = []
    negative = [c for c in cases if c.vmp < -1e-6 or c.vnp < -1e-6]
    if negative:
        worst = min(negative, key=lambda c: min(c.vmp, c.vnp))
        out.append(ConsistencyWarning(
            "landing_negative_vertical",
            f"{len(negative)} ground case(s) have a **negative vertical reaction** "
            f"(worst: case {worst.case}, {worst.description}, VMP {worst.vmp:,.0f} / "
            f"VNP {worst.vnp:,.0f} lb). A wheel cannot pull the airplane down -- check "
            "the CG waterlines and stations against the axle geometry (a zero "
            "waterline is the usual cause). Cases: "
            + ", ".join(str(c.case) for c in negative) + ".",
            PAGE_LANDING))
    nose_loaded = [c for c in cases if c.case in tuple(range(1, 4)) + tuple(range(13, 16))]
    zero_nose = [c for c in nose_loaded if abs(c.vnp) <= 1e-9]
    if zero_nose:
        out.append(ConsistencyWarning(
            "landing_zero_nose",
            "The nose wheel carries no load in case(s) "
            + ", ".join(str(c.case) for c in zero_nose)
            + " (3-wheel level / braked roll nose down), where it is loaded by "
              "construction. Check the nose-gear axle geometry and the CG stations.",
            PAGE_LANDING))
    return out


def _check_aero_coefficients(project: Project) -> List[ConsistencyWarning]:
    """Coefficient-entry checks on the airplane-less-tail polynomials (M4-5).

    The input-side companion to the ``aero_curves`` closure metric: these catch
    the hand-built-polynomial mistakes a concept airplane is exposed to (the
    FAR23 examples enter wind-tunnel/DATCOM sets), before the FLTLOADS balance
    turns them into loads. Advisory only -- nothing here blocks an Apply or
    changes a number, per this module's conservative charter.

    Reachability is tested against the configuration's own ``stall_cl`` (the
    value ``_balance`` clamps to, and the one the q-iteration must be able to
    attain) rather than the parent ``clmax_*`` scalars, which legitimately
    differ from it (see ``AeroCoefficientsInput.__post_init__``).
    """
    aero = project.aero_coeffs
    if aero is None:
        return []
    from .aero_curves import ALPHA_HI_DEG, ALPHA_LO_DEG, ALPHA_SAMPLES, drag_cd, lift_cl

    # No moment-slope check: a positive M1 (nose-up with alpha) is the *normal*
    # airplane-less-tail state -- the tail is what makes the airplane stable --
    # and every shipped fixture including the Appendix A GA example carries one
    # (ga6 M1 = +0.004128). A sign check here would fire on the oracle.
    out: List[ConsistencyWarning] = []

    if aero.clmax_clean_neg > 0.0:
        out.append(ConsistencyWarning(
            "aero_clmax_neg_sign",
            f"Clean negative CLmax = {aero.clmax_clean_neg:+.4g} is positive; the "
            "negative maximum lift coefficient caps the *negative* balancing "
            "solution and is normally negative (e.g. −0.59 on the Appendix A GA "
            "example). Check the sign.",
            PAGE_AERO_COEFFS))

    for label, cfg in (("Cruise", aero.cruise), ("Flaps down", aero.flaps_down)):
        if cfg is None:
            continue
        name = f"{label} ({cfg.name})"
        if cfg.lift[1] <= 0.0:
            out.append(ConsistencyWarning(
                "aero_lift_slope_sign",
                f"{name}: the lift-curve slope C1 = {cfg.lift[1]:+.4g} is not positive. "
                "CL = C0 + C1·α + … expects α in **degrees** (a per-radian slope "
                "entered here would be ~57× too large; a transposed row can flip the "
                "sign). The balance will not converge sensibly.",
                PAGE_AERO_COEFFS))

        # Can the entered polynomial actually reach the stall CL the balance
        # clamps to? If not, the dynamic-pressure iteration never converges onto
        # the stall line and every stall-limited corner is wrong.
        if cfg.stall_cl > 0.0 and cfg.lift[1] > 0.0:
            n = max(2, ALPHA_SAMPLES)
            band = [ALPHA_LO_DEG + (ALPHA_HI_DEG - ALPHA_LO_DEG) * i / (n - 1)
                    for i in range(n)]
            cl_max_on_curve = max(lift_cl(cfg, a) for a in band)
            if cl_max_on_curve < cfg.stall_cl:
                out.append(ConsistencyWarning(
                    "aero_clmax_unreachable",
                    f"{name}: the lift polynomial peaks at CL = {cl_max_on_curve:.4g} "
                    f"between α = {ALPHA_LO_DEG:g}° and {ALPHA_HI_DEG:g}°, below the "
                    f"stall CL = {cfg.stall_cl:.4g} the balance clamps to. The "
                    "FLTLOADS dynamic-pressure iteration cannot reach the stall line, "
                    "so the stall-limited corners will not converge. Check the lift "
                    "coefficients against the CLmax entered above.",
                    PAGE_AERO_COEFFS))

        # Drag over the operating CL band the balance can visit.
        lo_cl = min(cfg.neg_stall_cl, 0.0)
        hi_cl = max(cfg.stall_cl, 0.0)
        if hi_cl > lo_cl:
            n = 41
            band_cl = [lo_cl + (hi_cl - lo_cl) * i / (n - 1) for i in range(n)]
            worst = min((drag_cd(cfg, c), c) for c in band_cl)
            if worst[0] <= 0.0:
                out.append(ConsistencyWarning(
                    "aero_drag_negative",
                    f"{name}: the drag polar gives CD = {worst[0]:+.4g} at "
                    f"CL = {worst[1]:+.4g}, inside the operating band "
                    f"({lo_cl:+.4g} … {hi_cl:+.4g}). Drag cannot be zero or negative; "
                    "the balance rotates it into the airplane axes (DX), so a negative "
                    "CD corrupts the balancing tail load. Check D0…D4 "
                    "(CD = D0 + D1·CL + D2·CL² + …).",
                    PAGE_AERO_COEFFS))

        # A plain quadratic polar with a non-positive CL^2 term is inverted or
        # missing its induced-drag term. Only checked for the plain form -- a
        # general higher-order polar is left alone.
        if cfg.drag[2] <= 0.0 and not any(cfg.drag[3:]) and any(cfg.drag):
            out.append(ConsistencyWarning(
                "aero_drag_polar_shape",
                f"{name}: the drag polar's CL² term D2 = {cfg.drag[2]:+.4g} is not "
                "positive with no higher-order terms entered, so drag does not grow "
                "with lift — the induced-drag term is missing or inverted "
                "(CD = D0 + D1·CL + D2·CL²; the Appendix A GA example uses "
                "D2 = 0.0536).",
                PAGE_AERO_COEFFS))

    return out


def _check_weight_case_model(project: Project) -> List[ConsistencyWarning]:
    """The tagged case list and the design-weight ordering chain (G-3, G-4, G-14).

    Required practice 3: the case model is a cross-cutting convention, so it gets a
    code owner (:mod:`sloads.cg_cases`) **and** these guards, not a prose rule.

    * ``cg_case_no_analysis`` -- an empty ``analyses`` set. A case that is run for
      nothing is an entry error, not a state (G-3c): it silently disappears from
      every analysis while still occupying a row on the page.
    * ``cg_case_role_without_ground`` -- a ``role`` on a case not tagged ``GROUND``.
      The role is LANDLOAD's ordering contract; carried by a flight-only case it
      says the user meant one thing and the calc will do another.
    * ``ground_role_incomplete`` -- the ``GROUND`` cases do not carry exactly one of
      each role, so the landing module cannot run. Stated here as a page finding
      rather than only as the exception ``landing_role_cases`` raises.
    * ``weight_order_chain`` -- ``OEW <= MLW <= MTOW <= sum(items)``, the one place
      four scattered checks became. The floor half is G-4's ("you must be able to
      land with reserves") and the ceiling half G-14's ("you cannot weigh more than
      everything you have"); violations are the fixture-data class this project
      keeps finding by accident.
    * ``mlw_below_landing_estimate`` -- MLW below ``OEW + max payload + reserve
      fuel``, meaning the airplane cannot land at MLW with full payload and
      reserves. Measured 2026-08-14 this fires on ``concept_regional_jet`` (31,000
      against 31,360) and on no other shipped fixture, which is why the estimate is
      a floor and not a prediction.
    * ``mtow_representation_drift`` -- a stored ``speeds.weight_lb`` or
      ``weight.envelope.gross_weight`` that disagrees with the MTOW SSOT. G-14 made
      those derived reads; this is what keeps the compatibility fallback in
      :func:`sloads.cg_cases.max_takeoff_weight` from quietly becoming a second
      authority.
    """
    out: List[ConsistencyWarning] = []
    weight = project.weight
    cases = list(weight.cg_cases) if weight is not None else []

    blank = [c.name for c in cases if not c.analyses]
    if blank:
        out.append(ConsistencyWarning(
            "cg_case_no_analysis",
            "These weight/CG cases are run for no analysis, so they are silently "
            "absent from every result: " + ", ".join(f"'{n}'" for n in blank)
            + ". Tag each with FLIGHT and/or GROUND.",
            PAGE_WEIGHT_CG))
    stray = [c.name for c in cases
             if c.role is not None and AnalysisKind.GROUND not in c.analyses]
    if stray:
        out.append(ConsistencyWarning(
            "cg_case_role_without_ground",
            "These cases carry a landing role but are not tagged GROUND, so "
            "LANDLOAD will never see them: " + ", ".join(f"'{n}'" for n in stray)
            + ".", PAGE_WEIGHT_CG))

    ground = [c for c in cases if AnalysisKind.GROUND in c.analyses]
    if ground:
        counts = {role: sum(1 for c in ground if c.role == role)
                  for role in GROUND_CASE_ROLE_ORDER}
        wrong = {r.value: n for r, n in counts.items() if n != 1}
        if wrong:
            out.append(ConsistencyWarning(
                "ground_role_incomplete",
                "LANDLOAD needs exactly one GROUND case per role (aft max landing, "
                "fwd max landing, fwd light; UG fig 18.2). Found: "
                + ", ".join(f"{role} x{n}" for role, n in sorted(wrong.items()))
                + ". The landing conditions cannot run until this is one of each.",
                PAGE_WEIGHT_CG))

    if weight is None:
        return out
    mlw = cg_cases.max_landing_weight(project, required=False)
    mtow = cg_cases.max_takeoff_weight(project, required=False)
    total, oew, _ = weight.database_totals()
    chain = [("OEW", oew), ("max landing weight", mlw),
             ("max take-off weight", mtow), ("the item database total", total)]
    stated = [(label, value) for label, value in chain if value > 0]
    breaks = [(stated[i], stated[i + 1]) for i in range(len(stated) - 1)
              if stated[i][1] > stated[i + 1][1] + 1e-6]
    for (lo_label, lo), (hi_label, hi) in breaks:
        out.append(ConsistencyWarning(
            "weight_order_chain",
            f"{lo_label} {lo:,.0f} lb exceeds {hi_label} {hi:,.0f} lb. The design "
            "weights must satisfy OEW <= MLW <= MTOW <= sum(items) -- you must be "
            "able to land with reserves, and you cannot weigh more than everything "
            "you have (decisions G-4 / G-14).",
            PAGE_WEIGHT_CG))

    floor = cg_cases.max_landing_weight_estimate(project)
    if mlw > 0 and floor is not None and mlw < floor - 1e-6:
        out.append(ConsistencyWarning(
            "mlw_below_landing_estimate",
            f"Max landing weight {mlw:,.0f} lb is below OEW + max payload + reserve "
            f"fuel ({floor:,.0f} lb), so this airplane cannot land at MLW with full "
            "payload and reserves -- some payload has to be left behind on every "
            "flight that lands heavy. Confirm the MLW, the payload rows, or which "
            "fuel rows are consumable mission fuel (14 CFR 23.473(b)/(c)).",
            PAGE_WEIGHT_CG))

    if mtow > 0:
        others = []
        if project.speeds is not None and project.speeds.weight_lb > 0:
            others.append(("speeds.weight_lb (STRSPEED design weight)",
                           project.speeds.weight_lb))
        if weight.envelope is not None and weight.envelope.gross_weight > 0:
            others.append(("weight.envelope.gross_weight (WTENV)",
                           weight.envelope.gross_weight))
        drift = [(label, v) for label, v in others if abs(v - mtow) > 1e-6]
        if drift:
            out.append(ConsistencyWarning(
                "mtow_representation_drift",
                f"Max take-off weight is {mtow:,.0f} lb, but "
                + "; ".join(f"{label} says {v:,.0f} lb" for label, v in drift)
                + ". Decision G-14 made weight.max_takeoff_weight_lb the single "
                "owner and the others derived reads of it.",
                PAGE_WEIGHT_CG))
    return out


def _check_gear_carrier(project: Project) -> List[ConsistencyWarning]:
    """The gear's carrier and attachment node (decision G-2).

    * ``gear_carrier_unset`` -- no ``carrier`` on a leg. Ground cases cannot be
      exported without it (the export raises); body-carried and wing-carried gear
      are different load paths, not different labels.
    * ``gear_carrier_mass_disagrees`` -- a leg carried by the ``WING`` whose gear
      mass items are tagged ``fuselage`` (or vice versa): the same structure
      carrying the load but not the weight. This fires on ``dhc8_dash8`` today --
      main gear in wing-mounted nacelles, mass tagged ``fuselage`` -- which is the
      point of writing it; correcting that fixture moves
      ``mass_distribution.wing_mass_tie`` and so is claimed separately from this
      byte-neutral hop.
    * ``gear_attach_missing`` -- ``carrier`` stated but ``attach`` left at the
      origin. ``(0, 0, 0)`` is not a trunnion; it is the default nobody replaced.
    * ``gear_attach_off_the_wing`` -- a ``WING``-carried leg whose ``attach`` is
      outside the planform: at or inboard of the centreline, outboard of the tip,
      or forward/aft of the chord at its butt line. Loud, in the style of the T1
      planform validator, because the export transfers the contact-patch reaction
      to this point and a point off the surface is a lever arm into thin air.

    The third guard G-2 owes -- **the transfer preserves resultants about the CG**,
    gated exactly at ``rel_tol 1e-12`` -- belongs with the transfer itself and
    lands with the ground export, not with these input checks.
    """
    geom = project.geometry
    lg = geom.landing_gear if geom is not None else None
    if lg is None:
        return []
    out: List[ConsistencyWarning] = []
    legs = (("main", lg.main_gear), ("nose", lg.nose_gear))
    unset = [name for name, g in legs if g.carrier is None]
    if unset:
        out.append(ConsistencyWarning(
            "gear_carrier_unset",
            "No carrier stated for the " + " and ".join(unset) + " gear. Ground "
            "cases cannot be exported without it: a wing-carried reaction relieves "
            "or reverses inboard wing bending and reaches the fuselage only through "
            "the carry-through, so applying it to the body beam over-loads the "
            "fuselage and hides a real wing sizing case (decision G-2).",
            PAGE_CONFIGURATION))
    items = project.weight.items if project.weight is not None else []
    gear_items = [it for it in items if "gear" in it.name.strip().lower()]
    if gear_items:
        tagged_wing = any(it.component == MassComponent.WING for it in gear_items)
        tagged_body = any(it.component == MassComponent.FUSELAGE for it in gear_items)
        for name, g in legs:
            if g.carrier == GearCarrier.WING and tagged_body and not tagged_wing:
                out.append(ConsistencyWarning(
                    "gear_carrier_mass_disagrees",
                    f"The {name} gear is carried by the WING, but its mass rows are "
                    "tagged as fuselage mass: the same structure carries the load "
                    "but not the weight. Re-tag the gear items "
                    "MassComponent.WING, or correct the carrier (decision G-2).",
                    PAGE_WEIGHT_CG))
    wing = project.geometry.by_name("wing") if project.geometry is not None else None
    for name, g in legs:
        if g.carrier != GearCarrier.WING or wing is None or not wing.leading_edge:
            continue
        x, y, _ = g.attach
        if (x, y) == (0.0, 0.0):
            continue                      # the unset-attach case, reported below
        tip_y = max(p[1] for p in wing.leading_edge)
        why = ""
        if abs(y) < 1e-9:
            why = "on the centreline, where there is no wing structure to carry it"
        elif abs(y) > tip_y + 1e-9:
            why = f"outboard of the tip (butt line {tip_y:,.1f} in)"
        else:
            le = interp_x(wing.leading_edge, abs(y))
            te = interp_x(wing.trailing_edge, abs(y))
            if not (min(le, te) - 1e-9 <= x <= max(le, te) + 1e-9):
                why = (f"outside the chord at butt line {abs(y):,.1f} in "
                       f"({min(le, te):,.1f} to {max(le, te):,.1f} in)")
        if why:
            out.append(ConsistencyWarning(
                "gear_attach_off_the_wing",
                f"The {name} gear is carried by the WING but its attachment node "
                f"({x:,.1f}, {y:,.1f}) is {why}. The export transfers the "
                "contact-patch reaction to this point and resolves it onto the "
                "wing loads reference axis (G-2/G-12).",
                PAGE_CONFIGURATION))
    for name, g in legs:
        if g.carrier is not None and tuple(g.attach) == (0.0, 0.0, 0.0):
            out.append(ConsistencyWarning(
                "gear_attach_missing",
                f"The {name} gear states a carrier but no attachment node -- "
                "attach is still (0, 0, 0), which is the airplane's origin, not a "
                "trunnion. The export transfers the contact-patch reaction to this "
                "point, so the lever arm would be the whole fuselage (G-2/G-12).",
                PAGE_CONFIGURATION))
    return out


def consistency_warnings(project: Project) -> List[ConsistencyWarning]:
    """All input-consistency warnings for ``project`` (each tagged with its page).

    A view renders the subset whose ``page`` matches it, e.g.::

        for w in consistency_warnings(project):
            if w.page == "weight_cg_inertia":
                st.warning(w.message)
    """
    out: List[ConsistencyWarning] = []
    out += _check_taper(project)
    out += _check_area(project)
    out += _check_le_te_ordering(project)
    out += _check_area_mismatch(project)
    out += _check_cg_envelope(project)
    out += _check_operational_targets(project)
    out += _check_dive_speed_basis(project)
    out += _check_safety_factors(project)
    out += _check_safety_factor_overrides(project)
    out += _check_landing_hierarchy(project)
    out += _check_weight_case_model(project)
    out += _check_gear_carrier(project)
    out += _check_aero_coefficients(project)
    return out
