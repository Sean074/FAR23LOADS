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

from typing import List, Optional, Tuple

from ..constants import IN2_PER_FT2
from ..models import (
    ConditionResult,
    CriticalCondition,
    CriticalLoadSet,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    TailChordResult,
    TailChordStation,
)
from ..registry import register
from ._vtail import lift_curve_slope, rudder_effectiveness
from .select import default_critical, effective_tail_inputs, effective_vtail_inputs

MODULE_NAME = "taildist"

# The note 35 AS-4 statements: a condition that cannot supply a quantity states
# why, in these words, never a guess. The "predates" statement is the
# stale-persisted-set case (G-AS-4); the others are quantities the source
# method itself never defines.
STALE_STATE_NOTE = ("Aero state not recorded -- critical set predates these "
                    "fields; re-run SELECT.")
CHECKED_DELTA_NOTE = ("Elevator deflection: not defined by the method -- the "
                      "23.423(b) increment is the pitching-acceleration "
                      "inertia term.")
SIDE_GUST_Q_NOTE = "Dynamic pressure: 23.443(b) is linear in V -- no q term."
HTAIL_BETA_NOTE = ("Sideslip: not defined by the method -- a symmetric "
                   "pitch-plane condition has no sideslip.")


def aero_state_values(r: TailChordResult) -> Tuple[List[LoadValue], List[str]]:
    """``(values, reasons)`` stating the aero state of one distributed case.

    Note 35 G-AS-3: every condition states each of AoA / beta / delta / q
    **or** its AS-4 reason -- no silent blank. The values are the source
    condition's published state copied onto the :class:`TailChordResult`
    (never re-derived); angles and q are non-load units, so the render
    boundary leaves them unscaled (CONVENTIONS section 3). ``alpha_tail_deg``
    is published by every condition family, so its absence *is* the stale-set
    marker (G-AS-4), and beta may still be present on an L-7-era vtail set.
    """
    values: List[LoadValue] = []
    reasons: List[str] = []
    alpha = r.alpha_tail_deg
    stale = alpha is None
    if stale:
        reasons.append(STALE_STATE_NOTE)
    if r.component == "htail":
        if alpha is not None:
            values.append(LoadValue("Tail angle of attack AT", alpha,
                                    "deg", key="tail_angle_of_attack_at"))
            if r.delta_deg is not None:
                values.append(LoadValue("Elevator deflection (TE dn +)", r.delta_deg,
                                        "deg", key="elevator_deflection_te_dn"))
            else:
                reasons.append(CHECKED_DELTA_NOTE)
        reasons.append(HTAIL_BETA_NOTE)
    else:
        if alpha is not None:
            values.append(LoadValue("Fin angle of attack", alpha,
                                    "deg", key="fin_angle_of_attack"))
            if r.delta_deg is not None:
                values.append(LoadValue("Rudder deflection (TE port +)", r.delta_deg,
                                        "deg", key="rudder_deflection_te_port"))
        if r.beta_deg is not None:
            values.append(LoadValue("Sideslip beta (SC-1)", r.beta_deg, "deg",
                                    key="sideslip_beta"))
    if not stale:
        if r.q_psf is not None:
            values.append(LoadValue("Dynamic pressure Q", r.q_psf, "lb/ft^2",
                                    key="dynamic_pressure_q"))
        elif r.component == "vtail":
            reasons.append(SIDE_GUST_Q_NOTE)
    return values, reasons


def component_constants(project: Project, component: str) -> Optional[ConditionResult]:
    """The slope/effectiveness intermediates, once per component (note 35, AS-5).

    AHT (htail) or AVT + EFFECTV (vtail), computed by calling the same
    single-source owners SELECT's loads are built from
    (:func:`.._vtail.lift_curve_slope`, :func:`.._vtail.rudder_effectiveness`)
    on the same effective inputs -- the ``surface_geom`` precedent: reading the
    owner is not recomputing another module's quantity, and it is what makes
    the printed intermediate arithmetically the one inside the loads. Not
    persisted; reference constants only (no load quantities, so nothing here
    is SF-scaled and the classifier files them as reference data). ``None``
    when the inputs are absent.
    """
    if component == "htail":
        try:
            ti = effective_tail_inputs(project)
        except ValueError:
            ti = project.tail_loads      # display only: no ARW refusal here
        if ti is None or ti.aspect_ratio_htail <= 0:
            return None
        return ConditionResult(
            title="Chordwise htail constants",
            far_reference="",
            values=[LoadValue("Tail lift-curve slope AHT",
                              lift_curve_slope(ti.aspect_ratio_htail), "/rad",
                              key="tail_lift_curve_slope_aht")],
            note="The slope inside every htail load in this table (SELECT's "
                 "own owner, note 35 AS-5). Reference constants -- no load "
                 "quantities.")
    vt = effective_vtail_inputs(project)
    if vt is None or vt.aspect_ratio_vtail <= 0 or vt.vtail_area_sqft <= 0:
        return None
    return ConditionResult(
        title="Chordwise vtail constants",
        far_reference="",
        values=[LoadValue("Vtail lift-curve slope AVT",
                          lift_curve_slope(vt.aspect_ratio_vtail), "/rad",
                          key="vtail_lift_curve_slope_avt"),
                LoadValue("Rudder effectiveness EFFECTV",
                          rudder_effectiveness(vt.rudder_area_sqft / vt.vtail_area_sqft),
                          key="rudder_effectiveness_effectv")],
        note="The slope and effectiveness inside every vtail load in this "
             "table (SELECT's own owners, note 35 AS-5). Reference constants "
             "-- no load quantities.")


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
    """The SELECT critical-load set, through its single owner
    (:func:`select.default_critical`): the persisted ``envelope.critical`` if
    present, else freshly computed."""
    return default_critical(project)


def surface_geom(project: Project, cond: CriticalCondition) -> Optional[tuple]:
    """``(area_sqin, aft_hinge_sqin, span_in)`` for a condition's surface, or None
    when the chordwise geometry (the span) is not configured.

    Public because the spanwise discrete control-load path (plan 09 T6) needs the
    *same* three numbers this chordwise view is built on: the hinge line it
    reacts the control surface at is TAILDIST's ``CEAFTHL``, and asking for it
    here is what keeps one hinge line in the suite instead of two.
    """
    if cond.component == "htail":
        ti = project.tail_loads
        if ti is None or ti.htail_semispan_in <= 0 or ti.htail_area_sqft <= 0:
            return None
        return (ti.htail_area_sqft * IN2_PER_FT2,
                ti.elevator_aft_hinge_sqft * IN2_PER_FT2,
                2.0 * ti.htail_semispan_in)
    if cond.component == "vtail":
        vt = project.vtail_loads
        if vt is None or vt.vtail_span_in <= 0 or vt.vtail_area_sqft <= 0:
            return None
        return (vt.vtail_area_sqft * IN2_PER_FT2,
                vt.rudder_aft_hinge_sqft * IN2_PER_FT2,
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
        geom = surface_geom(project, cond)
        if geom is None:
            continue
        area_sqin, aft_sqin, span_in = geom
        stations = chordwise_pressures(cond.lt25, cond.lt50, area_sqin, aft_sqin, span_in)
        results.append(TailChordResult(
            case=cond.label, component=cond.component,
            lt25=cond.lt25, lt50=cond.lt50, stations=stations,
            case_ref=cond.case_ref, far_reference=cond.far_reference,
            safety_factor=cond.safety_factor,
            # The source condition's published aero state, copied across (note
            # 35, AS-6) -- never re-derived here.
            alpha_tail_deg=cond.alpha_tail_deg, beta_deg=cond.beta_deg,
            delta_deg=cond.delta_deg, q_psf=cond.q_psf))
    return results


def run(project: Project) -> ModuleResult:
    """Run TAILDIST: chordwise distribution per critical tail condition."""
    if project.tail_loads is None and project.vtail_loads is None:
        raise MissingInputError("taildist needs 'tail_loads' and/or 'vtail_loads' inputs")
    conditions: List[ConditionResult] = []
    seen_components: List[str] = []
    for r in build_tail_chordwise(project):
        if r.component not in seen_components:
            # AHT / AVT + EFFECTV once per component, ahead of its conditions
            # (note 35, AS-5/AS-6).
            seen_components.append(r.component)
            header = component_constants(project, r.component)
            if header is not None:
                conditions.append(header)
        state_values, state_reasons = aero_state_values(r)
        # The aero state ahead of the stations (AS-6): the state that made the
        # load, on the page that distributes it.
        values: List[LoadValue] = [
            *state_values,
            LoadValue("AoA load LT25 (cp 25%)", r.lt25, "lb", key="aoa_load_lt25_cp_25_pct"),
            LoadValue("Camber load LT50 (cp 50%)", r.lt50, "lb", key="camber_load_lt50_cp_50_pct"),
        ]
        for i, s in enumerate(r.stations, start=1):
            values.append(LoadValue(f"X{i} chord station", s.x, "in",
                                    key=f"x{i}_chord_station"))
            values.append(LoadValue(f"PSI(X{i}) net pressure", s.psi, "lb/in^2",
                                    key=f"psi_x{i}"))
        conditions.append(ConditionResult(
            title=f"Chordwise {r.component} load: {r.case}",
            # Cite the governing condition's regulation (23.423/425/427 maneuver/
            # gust/unsymmetrical h-tail, 23.441/443 v-tail), not just balancing loads.
            far_reference=r.far_reference or "23.421",
            values=values,
            note=" ".join([
                "Additive (25% chord) + camber (50% chord) distribution (Ref 1 Ch 10).",
                *state_reasons])
            + (" Concept mode -- unverified extrapolation past the FAR23 band."
               if project.is_concept else ""),
            case_ref=r.case_ref,
            # Same per-case factor the sbeam export scales by, so the rendered and
            # exported ULTIMATE loads can never disagree (defect M4-7).
            safety_factor=r.safety_factor,
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
