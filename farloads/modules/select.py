"""Critical-load selection (SELECT.BAS, Reference 1 Ch 9).

SELECT reads the balanced V-n matrix produced by FLTLOADS and searches it for the
governing (critical) load on each major component (wing, horizontal tail, vertical
tail, fuselage). This module implements the **wing** critical-load search
(SELECT.BAS subroutine 3000, lines 2990-3540), which feeds the AIRLOADS<->SELECT
iteration and WINGINER/NETLOADS:

  PHAA  largest resultant wing load sqrt(LZW^2 + DX^2) among STALL +N / MAN A
        (positive high angle of attack; FAR 23.333(b))
  PLAA  largest resultant among MAN D / GUST D
        (positive low angle of attack; FAR 23.333(b))
  PMAA  largest LZW among MAN C / GUST +C
        (positive medium angle of attack; FAR 23.333(c) or (b))
  NMAA  largest resultant among the negative maneuver/gust points
        (STALL -N, MAN -C, MAN -D, GUST -C, GUST -D; FAR 23.333(c) or (b))
  ACRL  largest LZW among the accelerated-roll points (FAR 23.349(a))
  TORS  steady-roll condition with the most negative aileron-induced torsion proxy
        (CM - 0.01*aileron_deg)*G*V^2 among ST ROL A/C/D, with the aileron
        deflection per CAM 3.222 (DA at VA, DC = (VA/VC)*DA at VC,
        DD = 0.5*(VA/VD)*DA at VD; FAR 23.349(b))

The selected conditions become ``Project.envelope.critical`` -- the set AIRLOADS
re-evaluates for distributed airloads and WINGINER/NETLOADS combine with inertia.
``LZW`` is the wing lift normal to the airplane reference (less tail) and ``DX``
the airplane drag, both read from each :class:`VnPoint`.

The rational horizontal/vertical-tail and fuselage critical loads (the remainder of
Ch 9) are a later C6 increment; this module currently writes the wing set only.

Validation: Appendix A "Critical Wing Loads" (loads report) -- PHAA case 22
STALL +N (CL +1.519, V 117.40, CG2, 0 ft), PLAA MAN D (+0.472, 212.40, CG2,
12000 ft), PMAA GUST +C (+0.810, 170, CG2, 12000 ft), NMAA GUST -C (-0.433, 170,
CG3, 12000 ft), ACRL AC ROLL (+1.328, 116, CG2, 12000 ft), TORS ST ROL C
(+0.470, 170, CG1, 12000 ft).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ..models import (
    ConditionResult,
    CriticalCondition,
    CriticalLoadSet,
    EnvelopeResult,
    LoadValue,
    ModuleResult,
    Project,
    VnPoint,
)
from ..registry import register
from .flight_envelope import build_envelope

MODULE_NAME = "select"

# V-n condition labels grouped by the wing search they belong to (SELECT.BAS
# 2990-3340). "GUST D" covers the program's positive-D gust label.
_PHAA = ("STALL +N", "MAN A")
_PLAA = ("MAN D", "GUST D", "GUST +D")
_PMAA = ("MAN C", "GUST +C")
_NMAA = ("STALL -N", "MAN -C", "MAN -D", "GUST -C", "GUST -D")
_ACRL = ("AC ROLL", "ACC ROLL")
_STROLL = ("ST ROL A", "ST ROL C", "ST ROL D")


def _envelope(project: Project) -> EnvelopeResult:
    """The V-n matrix to search: the persisted ``Project.envelope`` if present,
    else freshly built from the flight-loads inputs (FLTLOADS)."""
    if project.envelope is not None and project.envelope.vn:
        return project.envelope
    return build_envelope(project)


def _cg_weights(project: Project) -> Dict[str, float]:
    """Map CG-case name -> design weight (for the Nx = -DX/W inertia factor)."""
    fl = project.flight_loads
    return {c.name: c.weight_lb for c in fl.cg_cases} if fl is not None else {}


def _resultant(p: VnPoint) -> float:
    """Resultant wing load sqrt(LZW^2 + DX^2) (SELECT.BAS R1PHAA/R2PLAA/R4NAA)."""
    return math.hypot(p.lzw, p.dx)


def _pick(vn: List[VnPoint], labels, key) -> Optional[VnPoint]:
    cands = [p for p in vn if p.condition in labels]
    return max(cands, key=key) if cands else None


def _steady_roll_torsion(vn: List[VnPoint], aileron_deg: float, cm: float) -> Optional[VnPoint]:
    """The steady-roll point with the most negative aileron-induced wing torsion
    (SELECT.BAS 3372-3465). Aileron deflection per CAM 3.222 scales with the
    altitude's ST ROL A/C/D speeds; the torsion proxy is (CM-0.01*defl)*G*V^2.

    Faithful to the BASIC, the per-altitude reference speeds VA/VC/VD are the last
    ST ROL A/C/D speeds seen at that altitude (the program overwrites VA(J) as it
    scans all CG blocks).
    """
    # Per-altitude reference speeds (last-wins, matching SELECT.BAS 3395-3405).
    speeds: Dict[float, Dict[str, float]] = {}
    for p in vn:
        if p.condition in _STROLL:
            speeds.setdefault(p.altitude_ft, {})[p.condition] = p.v_eas_kt

    best: Optional[VnPoint] = None
    best_ta = 0.0  # SELECT.BAS TMIN starts at 0; only negative torsion is selected.
    for p in vn:
        if p.condition not in _STROLL:
            continue
        sp = speeds.get(p.altitude_ft, {})
        va, vc, vd = sp.get("ST ROL A", 0.0), sp.get("ST ROL C", 0.0), sp.get("ST ROL D", 0.0)
        if p.condition == "ST ROL A":
            defl = aileron_deg
        elif p.condition == "ST ROL C":
            defl = (va / vc * aileron_deg) if vc else 0.0
        else:  # ST ROL D
            defl = (0.5 * va / vd * aileron_deg) if vd else 0.0
        ta = (cm - 0.01 * defl) * p.g_corr * p.v_eas_kt ** 2
        if ta < best_ta:
            best_ta, best = ta, p
    return best


def _condition(component: str, label: str, far: str, p: VnPoint, weights: Dict[str, float]) -> CriticalCondition:
    """Wrap a selected :class:`VnPoint` as a :class:`CriticalCondition`."""
    w = weights.get(p.cg, 0.0)
    nx = (-p.dx / w) if w else 0.0
    return CriticalCondition(
        component=component, label=label, far_reference=far, case=p.case,
        loads=[
            LoadValue("CL", p.cl),
            LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)"),
            LoadValue("Load factor NZ", p.nz),
            LoadValue("Inertia drag factor NX", nx),
            LoadValue("Altitude", p.altitude_ft, "ft"),
        ],
    )


def select_wing(project: Project) -> List[CriticalCondition]:
    """Search the V-n matrix for the critical wing conditions (SELECT.BAS 3000)."""
    vn = _envelope(project).vn
    if not vn:
        raise ValueError("select needs a V-n matrix (Project.envelope or flight_loads)")
    weights = _cg_weights(project)
    si = project.select_input
    aileron_deg = si.full_down_aileron_deg if si else 0.0
    cm = si.basic_airfoil_cm if si else 0.0

    picks = [
        ("PHAA", "23.333(b)", _pick(vn, _PHAA, _resultant)),
        ("PLAA", "23.333(b)", _pick(vn, _PLAA, _resultant)),
        ("PMAA", "23.333(c)or(b)", _pick(vn, _PMAA, lambda p: p.lzw)),
        ("NMAA", "23.333(c)or(b)", _pick(vn, _NMAA, _resultant)),
        ("ACRL", "23.349(a)(2)", _pick(vn, _ACRL, lambda p: p.lzw)),
        ("TORS", "23.349(b)", _steady_roll_torsion(vn, aileron_deg, cm)),
    ]
    return [_condition("wing", label, far, p, weights) for label, far, p in picks if p is not None]


def build_critical(project: Project) -> CriticalLoadSet:
    """Compute the critical-load set (currently the wing conditions) for
    ``Project.envelope.critical``."""
    return CriticalLoadSet(conditions=select_wing(project))


def _critical_conditions(cls: CriticalLoadSet, concept: bool) -> List[ConditionResult]:
    note = ("Concept mode -- unverified extrapolation past the FAR23 band."
            if concept else "")
    out: List[ConditionResult] = []
    for c in cls.conditions:
        out.append(ConditionResult(
            title=f"Critical {c.component} load {c.label} (case {c.case})",
            far_reference=c.far_reference,
            values=list(c.loads),
            note=note,
        ))
    return out


def run(project: Project) -> ModuleResult:
    """Run SELECT against a :class:`Project`'s envelope / flight-loads inputs."""
    cls = build_critical(project)
    return ModuleResult(module=MODULE_NAME,
                        conditions=_critical_conditions(cls, project.is_concept))


register(MODULE_NAME, run)
