"""Chordwise tail-load distribution, from TAILDIST.BAS (Reference 1 Ch 10).

TAILDIST takes SELECT's critical horizontal- and vertical-tail loads -- each
resolved into an angle-of-attack load ``LT25`` (at 25% MAC) and a camber load
``LT50`` (at 50% MAC) -- and spreads them **chordwise** along the average tail
chord, producing the net pressure profile sbeam needs for tail sizing. These
distributions replace the arbitrary FAR 23 Appendix B figures (pre-amendment 42).

The method (Ref 1 Ch 10, TAILDIST.BAS subroutine 3000) builds two piecewise-linear
distributions on five chord stations and sums them:

* the **additive** (angle-of-attack) distribution -- 4x the average pressure at the
  leading edge, the average at the quarter chord, zero at the trailing edge; and
* the **camber** distribution -- a trapezoid symmetric about the 50% chord, ``w``
  at the hinge line and zero at the trailing edge (the basic stabilizer/elevator
  two-line shape).

Working in the suite's native full-surface areas (square inches), the per-station
pressures (TAILDIST.BAS 3010-3145) are::

    S    = tail area (both sides for the htail), Saft = control area aft of hinge
    CAVE = S / span                              average chord (= CT)
    CEAFTHL = (Saft/S) * CAVE                     hinge-line chord station
    X1,X2,X3,X4,X5 = 0, 0.25*CT, CT, CEAFTHL, CT-CEAFTHL
    WATT = LT25 / S                               additive average pressure
    WATT1 = 4*WATT   WATT2 = WATT   WATT3 = 0
    WATT4 = WATT                          if X4 == X2
          = 4*WATT - X4*3*WATT/X2         if X4 <  X2   (linear LE -> 1/4c)
          = WATT - (X4-X2)*WATT/(X3-X2)   if X4 >  X2   (linear 1/4c -> TE)
    WATT5 = WATT - (X5-X2)*WATT/(X3-X2)
    WCAM = LT50 / (S - Saft)                       camber pressure at hinge
    WCAM1 = WCAM3 = 0   WCAM4 = WCAM5 = WCAM
    WCAM2 = (X2/X4)*WCAM  if X4 > X2  else  WCAM
    PSI(Xi) = WATTi + WCAMi                         net chordwise pressure

The original program prompts for ``LT25``/``LT50`` per condition as **total**
(both-sides) loads and divides by the *half* tail area; folding both factors of two
together leaves the unified ``LT/S`` form above with the full surface area -- which
is what the suite already stores (``TailLoadsInput.htail_area_sqft`` etc. are full,
both-sides). The horizontal tail needs only the new ``htail_semispan_in`` (the
average chord ``CAVE = S / (2*semispan)``); the vertical tail needs ``vtail_span_in``.

Reference: TAILDIST.BAS (Appendix C, subroutine 3000); Ref 1 Ch 10 p82-84; worked
example Appendix A "Chordwise Distribution of Tail Loads" p237 (cond 1 UP-BAL-RET
LT25 +907.62 / LT50 -387.77 -> PSI 0.682 / 0.095 / 0 / 0.015 / -0.030).
"""

from __future__ import annotations

from typing import List, Optional

from ..models import (
    ConditionResult,
    CriticalCondition,
    CriticalLoadSet,
    LoadValue,
    ModuleResult,
    Project,
    TailChordResult,
    TailChordStation,
)
from ..registry import register
from .select import build_critical

MODULE_NAME = "taildist"

_SQIN_PER_SQFT = 144.0


def chordwise_pressures(lt25: float, lt50: float, area_sqin: float,
                        aft_hinge_sqin: float, span_in: float) -> List[TailChordStation]:
    """The five chordwise pressure stations for one tail load (TAILDIST.BAS 3000).

    ``area_sqin`` is the full surface area, ``aft_hinge_sqin`` the control-surface
    area aft of the hinge line, ``span_in`` the full span (tip to tip for the
    symmetric horizontal tail). ``lt25``/``lt50`` are the angle-of-attack and camber
    loads (lb). Returns leading-edge-first ``(x, psi)`` stations (in, lb/in^2)."""
    cave = area_sqin / span_in
    ct = cave
    ceafthl = (aft_hinge_sqin / area_sqin) * cave
    x1, x2, x3, x4, x5 = 0.0, 0.25 * ct, ct, ceafthl, ct - ceafthl

    # Additive (angle-of-attack) distribution.
    watt = lt25 / area_sqin
    watt1, watt2, watt3 = 4.0 * watt, watt, 0.0
    if x4 == x2:
        watt4 = watt
    elif x4 < x2:
        watt4 = 4.0 * watt - x4 * 3.0 * watt / x2
    else:
        watt4 = watt - (x4 - x2) * watt / (x3 - x2)
    watt5 = watt - (x5 - x2) * watt / (x3 - x2)

    # Camber distribution (trapezoid symmetric about 50% chord).
    wcam = lt50 / (area_sqin - aft_hinge_sqin)
    wcam1, wcam3, wcam4, wcam5 = 0.0, 0.0, wcam, wcam
    wcam2 = (x2 / x4) * wcam if x4 > x2 else wcam

    xs = [x1, x2, x3, x4, x5]
    ws = [watt1 + wcam1, watt2 + wcam2, watt3 + wcam3, watt4 + wcam4, watt5 + wcam5]
    return [TailChordStation(x=x, psi=w) for x, w in zip(xs, ws)]


def _critical_set(project: Project) -> CriticalLoadSet:
    """The SELECT critical-load set: the persisted ``envelope.critical`` if present,
    else freshly computed."""
    if project.envelope is not None and project.envelope.critical is not None:
        return project.envelope.critical
    return build_critical(project)


def _surface_geom(project: Project, cond: CriticalCondition) -> Optional[tuple]:
    """``(area_sqin, aft_hinge_sqin, span_in)`` for a condition's surface, or None
    when the chordwise geometry (the span) is not configured."""
    if cond.component == "htail":
        ti = project.tail_loads
        if ti is None or ti.htail_semispan_in <= 0 or ti.htail_area_sqft <= 0:
            return None
        return (ti.htail_area_sqft * _SQIN_PER_SQFT,
                ti.elevator_aft_hinge_sqft * _SQIN_PER_SQFT,
                2.0 * ti.htail_semispan_in)
    if cond.component == "vtail":
        vt = project.vtail_loads
        if vt is None or vt.vtail_span_in <= 0 or vt.vtail_area_sqft <= 0:
            return None
        return (vt.vtail_area_sqft * _SQIN_PER_SQFT,
                vt.rudder_aft_hinge_sqft * _SQIN_PER_SQFT,
                vt.vtail_span_in)
    return None


def build_tail_chordwise(project: Project) -> List[TailChordResult]:
    """Chordwise load distribution for every critical horizontal/vertical-tail
    condition SELECT produced (those carrying an ``lt25``/``lt50`` split)."""
    results: List[TailChordResult] = []
    for cond in _critical_set(project).conditions:
        if cond.component not in ("htail", "vtail"):
            continue
        if cond.lt25 is None or cond.lt50 is None:
            continue
        geom = _surface_geom(project, cond)
        if geom is None:
            continue
        area_sqin, aft_sqin, span_in = geom
        stations = chordwise_pressures(cond.lt25, cond.lt50, area_sqin, aft_sqin, span_in)
        results.append(TailChordResult(
            case=cond.label, component=cond.component,
            lt25=cond.lt25, lt50=cond.lt50, stations=stations))
    return results


def run(project: Project) -> ModuleResult:
    """Run TAILDIST: chordwise distribution per critical tail condition."""
    if project.tail_loads is None and project.vtail_loads is None:
        raise ValueError("taildist needs 'tail_loads' and/or 'vtail_loads' inputs")
    conditions: List[ConditionResult] = []
    for r in build_tail_chordwise(project):
        values: List[LoadValue] = [
            LoadValue("AoA load LT25 (cp 25%)", r.lt25, "lb"),
            LoadValue("Camber load LT50 (cp 50%)", r.lt50, "lb"),
        ]
        for i, s in enumerate(r.stations, start=1):
            values.append(LoadValue(f"X{i} chord station", s.x, "in"))
            values.append(LoadValue(f"PSI(X{i}) net pressure", s.psi, "lb/in^2"))
        conditions.append(ConditionResult(
            title=f"Chordwise {r.component} load: {r.case}",
            far_reference="23.421",
            values=values,
            note="Additive (25% chord) + camber (50% chord) distribution (Ref 1 Ch 10)."
            + (" Concept mode -- unverified extrapolation past the FAR23 band."
               if project.is_concept else ""),
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
