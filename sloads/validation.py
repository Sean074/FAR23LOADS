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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .models import Project

# Pages that render consistency warnings (the ``page`` tag on each warning).
PAGE_CONFIGURATION = "configuration_layout"
PAGE_WING_GEOMETRY = "wing_geometry"
PAGE_STRUCTURAL_SPEEDS = "structural_speeds"
PAGE_WEIGHT_CG = "weight_cg_inertia"

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
    total_in2 = next((v.value for v in r.values if v.label == "Total area"), None)
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


def wtenv_cg_limits(project: Project) -> Optional["tuple[float, float]"]:
    """(forward-most, aft-most) structural CG station (in) from WTENV, or None.

    Needs the WTENV envelope slice and the wing geometry it reads XLEMAC/MAC from;
    returns None (check skipped) when either is absent or the calc cannot run.

    Public (M2R-5): also seeds the Landing Loads CG-case editor and the Weight/CG
    grid overlay, so it is imported by ``app/`` -- hence a public name (M4-12: ``app/``
    must not import ``sloads`` underscore symbols).
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
    limits = {v.label: v.value for r in results for v in r.values}
    fwd_candidates = [limits[k] for k in ("Forward gross station", "Forward regardless station")
                      if k in limits]
    aft = limits.get("Aft gross station")
    if not fwd_candidates or aft is None:
        return None
    return min(fwd_candidates), aft


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
    xbar = next((v.value for v in result.values if v.label == "XBAR (fus station)"), None)
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
    return out
