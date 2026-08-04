"""Net fuselage loads -- the body analogue of NETLOADS (Reference 1 Ch 15).

Ch 15 ("Net Fuselage Loads") gives a *suggested procedure* rather than a ported
``.BAS`` program: the fuselage is a simple beam carrying the inertia of the
fuselage mass items reacted by the air load on the tail and the wing-attach
reactions. For each critical fuselage condition (selected by SELECT, R5) this
module follows the two passes of Ref 1 p103:

  1. multiplies each fuselage station weight by the linear load factor ``NZ`` to
     get its inertia force (``fz = -NZ*w``, down for positive NZ);
  2. applies the balancing tail air load ``LT`` at the tail station;
  3. integrates nose->tail to the running shear ``Sz`` and bending ``Myy``; the
     terminal moment of *that* set is the **unbalanced moment** ``M_ub``
     ("the moment at the aft end is the unbalanced moment", p103);
  4. reacts ``M_ub`` -- and the residual vertical force ``R_total = NZ*W_fus -
     LT`` -- at the wing **front and rear spar attachments**, then re-integrates
     the whole set ("the unbalanced moment is reacted by the wing at the front
     and rear spar attachments ... recalculate the loads, shear and moments").

There is **no printed station-by-station oracle** (Ch 15 ships no program), so the
result is validated by **equilibrium closure**: the applied vertical force sums to
zero, the shear returns to ~0 at the aft end, and the terminal ``Myy`` is ~0
(moment closure -- backlog M4-1, closed 2026-08-03). The fuselage station weights
(``Project.fuselage_mass``) should already exclude the wing mass outside the
fuselage, per Ch 15.

**The distributed carry-through reaction is a refinement of p103, ours and not
the manual's.** p103 prescribes two point reactions; applied literally they put a
``+/-M_ub/d`` shear spike across a short carry-through. The two reactions are
therefore applied as the statically equivalent **linear distribution over
``[x_f, x_r]``** -- identical resultant and first moment, no spike, and it
collapses continuously onto the manual's two-point solve as ``d -> 0``. (The
manual's own Bruhn Ch A5 pointer is about beaming the *inertia* loads into the
adjacent frames, so it is precedent for diffusing discrete loads into structure,
not authority for this particular shape.) The reactions ``R_f``/``R_r`` are still
reported as the fitting loads; they are *not* applied on top of the distribution,
which already carries them. The options trade is in
``docs/30_future/06_m4-1_body_moment_closure.md``.

The spar stations come from :func:`sloads.derived_geometry.carry_through`. When
they are underivable (no wing surface, degenerate root chord) the module falls
back to a whole-body self-equilibrated linear correction: it still closes the
beam, but the correction has **no physical source** -- it relieves the wing
region and loads the tail cone with a moment nothing applies there. Such a result
is flagged ``closure_artifact`` and carries :data:`CLOSURE_ARTIFACT_CAVEAT` onto
every deliverable.

Still open, split out of M4-1: the **pitching** half of p103's "linear and
pitching load factors" (**M4-21**; ``theta_ddot = 0`` on these balanced trim
cases, so it does not affect this closure) and the distributed body aero moment
(**M4-19**).

Coordinates are the airplane body axes (fuselage station X aft, waterline Z up),
pounds and inch-pounds.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from ..constants import CARRY_THROUGH_NODES
from ..models import (
    MissingInputError,
    BodyLoadResult,
    BodyStationLoad,
    CriticalCondition,
    ModuleResult,
    Project,
    VnPoint,
)
from ..derived_geometry import CarryThrough, carry_through, sync_geometry_derived
from ..registry import register
from .flight_envelope import build_envelope
from .select import _stamp_case_refs, select_fuselage

MODULE_NAME = "body_loads"

#: Caveat stamped onto a body-load deliverable **only** when the moment closure
#: fell back to the whole-body correction (no derivable spar stations). The
#: primary carry-through path reacts the moment where the wing actually attaches
#: and ships no caveat. See the module docstring.
CLOSURE_ARTIFACT_CAVEAT = (
    "CLOSURE ARTIFACT -- the wing spar stations could not be derived, so the "
    "unbalanced moment was reacted by a self-equilibrated correction spread over "
    "the WHOLE body instead of the wing carry-through. The beam closes, but the "
    "correction has no physical source: it relieves wing-region bending and loads "
    "the tail cone. Define the wing front/rear spar chord fractions to get the "
    "Ch 15 carry-through reaction."
)


def _tail_station(project: Project, fallback: float) -> float:
    """Fuselage station of the tail air load (25% h-tail MAC) if available."""
    ti = project.tail_loads
    return ti.xt25 if ti is not None and ti.xt25 else fallback


def _integrate(points: Sequence[Tuple[float, float]]) -> List[BodyStationLoad]:
    """Integrate applied point loads ``(x, fz)`` nose->tail to shear and bending.

    ``Myy`` accumulates the area under the shear curve, so the terminal moment is
    ``sum(fz_i * (L - x_i))`` about the aft-most station -- the reference the
    p103 reaction solve is written against (:func:`_spar_reactions`)."""
    ordered = sorted(points, key=lambda pt: pt[0])
    out: List[BodyStationLoad] = []
    sz = 0.0
    myy = 0.0
    prev_x = ordered[0][0]
    for x, fz in ordered:
        myy += sz * (x - prev_x)                    # area under the shear curve
        sz += fz
        prev_x = x
        out.append(BodyStationLoad(x=x, fx=0.0, fy=0.0, fz=fz, sx=0.0, sy=0.0,
                                   sz=sz, mxx=0.0, myy=myy, mzz=0.0))
    return out


def _spar_reactions(m_ub: float, r_total: float, x_f: float, x_r: float,
                    x_ref: float) -> Tuple[float, float]:
    """The p103 front/rear spar reactions ``(R_f, R_r)``, solved 2x2.

    ``m_ub`` is the unbalanced moment of the wing-reaction-free set taken about
    ``x_ref`` (the aft-most station, matching :func:`_integrate`). Imposing
    ``sum(Fz) = 0`` and terminal ``Myy = 0`` on the reacted set gives

        R_r = (M_ub + R_total*(x_ref - x_f)) / (x_r - x_f)
        R_f = R_total - R_r
    """
    r_r = (m_ub + r_total * (x_ref - x_f)) / (x_r - x_f)
    return r_total - r_r, r_r


def _linear_load_nodes(x_a: float, x_b: float, total: float, couple: float,
                       nodes: int = CARRY_THROUGH_NODES) -> List[Tuple[float, float]]:
    """Lump a linear line load over ``[x_a, x_b]`` onto ``nodes`` point loads.

    The line load ``w(xi) = a + b*(xi - 1/2)`` (``xi = (x - x_a)/d``) is the unique
    linear distribution whose resultant is ``total`` and whose moment about the
    interval midpoint is ``couple``::

        a = total / d          b = 12 * couple / d**2

    Each segment is lumped by its **exact** static equivalent for a linear load
    (``P_left = h*(2*w_k + w_k1)/6``, ``P_right = h*(w_k + 2*w_k1)/6``), so both
    the resultant and the first moment are preserved to machine precision at any
    node count -- the closure does not depend on ``nodes``.
    """
    d = x_b - x_a
    a = total / d
    b = 12.0 * couple / (d * d)
    xs = [x_a + d * k / (nodes - 1) for k in range(nodes)]
    w = [a + b * ((x - x_a) / d - 0.5) for x in xs]
    p = [0.0] * nodes
    for k in range(nodes - 1):
        h = xs[k + 1] - xs[k]
        p[k] += h * (2.0 * w[k] + w[k + 1]) / 6.0
        p[k + 1] += h * (w[k] + 2.0 * w[k + 1]) / 6.0
    return list(zip(xs, p))


def body_distribution(stations, nz: float, tail_load: float, tail_x: float,
                      wing_x: float, carry: Optional[CarryThrough] = None,
                      ) -> Tuple[List[BodyStationLoad], Dict[str, float]]:
    """Net body shear/bending for one condition (Ref 1 Ch 15 p103).

    Returns the integrated station table and a dict of the closure quantities:
    ``m_unbalanced``, ``r_total``, and -- on the carry-through path -- the
    fitting loads ``r_front``/``r_rear`` at ``x_front``/``x_rear``.

    With ``carry`` given, the unbalanced moment is reacted over the wing
    carry-through (the primary path). Without it, the single wing reaction at
    ``wing_x`` is kept and the residual moment is cancelled by a self-equilibrated
    whole-body correction -- a **closure artifact**, flagged as such by the
    caller.
    """
    w_fus = sum(w for _, w in stations)
    r_total = nz * w_fus - tail_load                # vertical equilibrium

    # Pass 1 (p103): inertia + tail air load only. Its terminal moment about the
    # aft-most station is the unbalanced moment.
    applied: List[Tuple[float, float]] = [(x, -nz * w) for x, w in stations]
    applied.append((tail_x, tail_load))
    x_ref = max(x for x, _ in applied)
    m_ub = _integrate(applied)[-1].myy

    info: Dict[str, float] = {"m_unbalanced": m_ub, "r_total": r_total}

    if carry is not None:
        # Pass 2: react at the spar attachments, applied as the statically
        # equivalent linear distribution over the carry-through.
        r_f, r_r = _spar_reactions(m_ub, r_total, carry.x_f, carry.x_r, x_ref)
        couple = (r_r - r_f) * carry.d / 2.0        # about the carry-through midpoint
        applied += _linear_load_nodes(carry.x_f, carry.x_r, r_total, couple)
        info.update({"r_front": r_f, "r_rear": r_r,
                     "x_front": carry.x_f, "x_rear": carry.x_r})
        return _integrate(applied), info

    # Fallback: the historical single wing reaction closes sum(Fz); the moment it
    # leaves over is cancelled by a zero-net-force linear correction over the
    # whole body (``A = 12*M_res/L**2``). Closes the beam, invents the source.
    applied.append((wing_x, r_total))
    m_res = _integrate(applied)[-1].myy
    x_nose = min(x for x, _ in applied)
    applied += _linear_load_nodes(x_nose, x_ref, 0.0, m_res)
    return _integrate(applied), info


def _critical_fuselage(project: Project) -> List[CriticalCondition]:
    """The SELECT-critical fuselage conditions -- the persisted ``envelope.critical``
    if present (its ``CaseRef``s already stamped), else freshly computed.

    Calls ``select_fuselage`` directly (not ``build_critical``) so this module
    doesn't require ``tail_loads``/``vtail_loads`` to be well-formed just to get
    fuselage conditions -- it reuses SELECT's own ``_stamp_case_refs`` helper so
    the ``F-`` ids agree with a full SELECT run byte-for-byte (only the fuselage
    entries advance the fuselage counter, regardless of what other components are
    in the list)."""
    if project.envelope is not None and project.envelope.critical is not None:
        cached = [c for c in project.envelope.critical.conditions if c.component == "fuselage"]
        if cached:
            return cached
    conditions = select_fuselage(project)
    _stamp_case_refs(project, conditions)
    return conditions


def build_body_loads(project: Project) -> List[BodyLoadResult]:
    """Net fuselage load distribution for each critical fuselage condition."""
    sync_geometry_derived(project)
    fm = project.fuselage_mass
    fl = project.flight_loads
    if fm is None or not fm.stations or fl is None:
        raise MissingInputError("body_loads needs 'fuselage_mass' stations and 'flight_loads'")
    vn: Dict[int, VnPoint] = {p.case: p for p in build_envelope(project).vn}
    stations = [(s.x, s.weight_lb) for s in fm.stations]
    wing_x = fl.xw
    tail_x = _tail_station(project, max(s.x for s in fm.stations))
    carry = carry_through(project)                  # None -> flagged fallback

    results: List[BodyLoadResult] = []
    for cond in _critical_fuselage(project):
        p = vn.get(cond.case)
        if p is None:
            continue
        rows, info = body_distribution(stations, p.nz, p.lt, tail_x, wing_x, carry)
        results.append(BodyLoadResult(
            case=cond.label, stations=rows, case_ref=cond.case_ref,
            safety_factor=cond.safety_factor,
            m_unbalanced=info["m_unbalanced"],
            r_front=info.get("r_front"), r_rear=info.get("r_rear"),
            x_front=info.get("x_front"), x_rear=info.get("x_rear"),
            closure_artifact=carry is None,
            spars_assumed=carry.assumed if carry is not None else False,
        ))
    return results


def body_load_rows(results: List[BodyLoadResult]) -> List[Dict[str, str]]:
    """One CSV row per fuselage station per condition.

    All loads are **LIMIT** (the oracle-traceable calc values), stated in-band by
    the ``Basis`` column so the basis travels with any table/CSV built from these
    rows (defect M4-15); the ULTIMATE deliverable is
    ``sbeam_bridge.body_span_load_csv``.
    """
    rows: List[Dict[str, str]] = []
    for r in results:
        for s in r.stations:
            rows.append({
                "Case": r.case, "X": f"{s.x:.3f}", "Fz": f"{s.fz:.2f}",
                "Sz": f"{s.sz:.2f}", "Myy": f"{s.myy:.1f}",
                "Basis": "LIMIT",
            })
    return rows


def fitting_load_rows(results: List[BodyLoadResult]) -> List[Dict[str, str]]:
    """One row per condition of the wing-attachment fitting loads (**LIMIT**).

    The front/rear spar reactions of the p103 solve (Ref 1 p103) -- the sizing
    loads for the wing-attach fittings. Empty for a ``closure_artifact`` result,
    which has no spar stations to report."""
    rows: List[Dict[str, str]] = []
    for r in results:
        if r.r_front is None or r.r_rear is None:
            continue
        rows.append({
            "Case": r.case,
            "X front": f"{r.x_front:.3f}", "R front": f"{r.r_front:.2f}",
            "X rear": f"{r.x_rear:.3f}", "R rear": f"{r.r_rear:.2f}",
            "M unbalanced": f"{r.m_unbalanced:.1f}",
            "Spars": "assumed" if r.spars_assumed else "entered",
            "Basis": "LIMIT",
        })
    return rows


def run(project: Project) -> ModuleResult:
    """Run the fuselage net-load distribution (returns an empty report; the
    station table is consumed via ``build_body_loads`` / the CSV)."""
    build_body_loads(project)
    return ModuleResult(module=MODULE_NAME, conditions=[])


register(MODULE_NAME, run)
