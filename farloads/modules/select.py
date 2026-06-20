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

It also computes the **rational horizontal-tail balancing loads** (Ch 9 "Balancing
Tail Loads" / BALLOADS method) when ``Project.tail_loads`` is present: for every
balanced V-n point it resolves the total balanced tail load into the angle-of-
attack load at 25% tail MAC and the camber (elevator) load at 50%, then selects the
largest up and largest down balancing load with flaps retracted (FAR 23.421). This
refines FLTLOADS' approximate tail CP rationally.

When ``Project.vtail_loads`` is present it also computes the four critical
**vertical-tail** loads (Ch 9 / SELECT.BAS subroutine 8300), searched over the V-n
``BAL A`` (VA) and ``BAL C`` (VC) points: sudden full rudder deflection
(FAR 23.441(a)(1)), yaw to a 19.5 deg sideslip with the rudder held
(FAR 23.441(a)(2)), a 15 deg yaw with the rudder neutral (FAR 23.441(a)(3)) and the
lateral gust at VC (FAR 23.443(b)).

The remaining horizontal-tail conditions (unchecked/checked maneuver, gust,
unsymmetrical), the flaps-extended balancing (which needs the flapped V-n envelope,
not yet built) and the fuselage net loads are later C6 increments.

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
    CgCase,
    ConditionResult,
    CriticalCondition,
    CriticalLoadSet,
    EnvelopeResult,
    LoadValue,
    ModuleResult,
    Project,
    TailLoadsInput,
    VnPoint,
    VTailLoadsInput,
)
from ..registry import register
from .flight_envelope import _sigma, build_envelope

MODULE_NAME = "select"
_DEG = 57.3  # SELECT.BAS / BALLOADS use 57.3 deg/rad
_G = 32.2

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


# --------------------------------------------------------------------------- #
# Rational horizontal-tail balancing loads (Ch 9 / BALLOADS method)
# --------------------------------------------------------------------------- #
def htail_balance(p: VnPoint, cg: CgCase, xw: float, zw: float,
                  ti: TailLoadsInput) -> Dict[str, float]:
    """Resolve the balanced tail load at one V-n point into the rational
    angle-of-attack (25% MAC) and camber/elevator (50% MAC) components (Ch 9).

    Tail angle of attack ``AT = alpha_wl + IT - E`` with downwash
    ``E = 114.6*CL/(pi*ARW)`` (the wing zero-lift incidence IW cancels out of AT for
    flaps-retracted; the flaps-extended balancing, a later increment, reintroduces
    it). Tail lift slope ``AHT = 2*pi/(1 + 2/ARHT)``, ``LT25 = (AT*AHT/57.3)*Q*ST``
    with ``Q = V^2/295``; the elevator deflection balances the pitching moment about
    the CG and gives the camber load ``LT50``; ``LT = LT25 + LT50``. ``cp`` is the
    load centre of pressure in percent tail MAC.
    """
    e_down = 114.6 * p.cl / (math.pi * ti.aspect_ratio_wing)
    at = p.alpha_deg + ti.tail_incidence_deg - e_down
    aht = 2.0 * math.pi / (1.0 + 2.0 / ti.aspect_ratio_htail)
    q = p.v_eas_kt ** 2 / 295.0
    st = ti.htail_area_sqft
    lt25 = (at * aht / _DEG) * q * st
    lt50_per_delta = (ti.elevator_effectiveness * aht / _DEG) * q * st
    delta = ((p.m_wf - p.dx * (cg.zcg - zw) + p.lzw * (cg.xcg - xw)
              - lt25 * (ti.xt25 - cg.xcg)) / (lt50_per_delta * (ti.xt50 - cg.xcg)))
    lt50 = lt50_per_delta * delta
    lt = lt25 + lt50
    cp = (25.0 * lt25 + 50.0 * lt50) / lt if lt else 0.0
    return {"LT25": lt25, "LT50": lt50, "AT": at, "DELTA": delta, "LT": lt, "CP": cp}


def select_htail_balancing(project: Project) -> List[CriticalCondition]:
    """Select the largest up and down rational balancing tail loads, flaps
    retracted (FAR 23.421). Returns an empty list if there are no flaps-retracted
    points (the flaps-extended balancing needs the not-yet-built flapped envelope).
    """
    ti = project.tail_loads
    fl = project.flight_loads
    if ti is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in fl.cg_cases}
    flaps: Dict[str, bool] = {c.name: c.flaps_down for c in fl.configurations}

    vn = _envelope(project).vn
    balanced = []
    for p in vn:
        cg = cg_map.get(p.cg)
        if cg is None or flaps.get(p.config, False):  # flaps retracted only
            continue
        b = htail_balance(p, cg, fl.xw, fl.zw, ti)
        balanced.append((p, b))
    if not balanced:
        return []

    out: List[CriticalCondition] = []
    for label, far, pick in (
        ("BAL UP RETRACTED", "23.421", max(balanced, key=lambda pb: pb[1]["LT"])),
        ("BAL DN RETRACTED", "23.421", min(balanced, key=lambda pb: pb[1]["LT"])),
    ):
        p, b = pick
        out.append(CriticalCondition(
            component="htail", label=label, far_reference=far, case=p.case,
            loads=[
                LoadValue("Total balanced tail load LT", b["LT"], "lb"),
                LoadValue("AoA load LT25 (cp 25%)", b["LT25"], "lb"),
                LoadValue("Camber/elevator load LT50 (cp 50%)", b["LT50"], "lb"),
                LoadValue("Tail angle of attack AT", b["AT"], "deg"),
                LoadValue("Elevator deflection (TE dn +)", b["DELTA"], "deg"),
                LoadValue("CP of total load", b["CP"], "% tail MAC"),
                LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)"),
            ],
        ))
    return out


# --------------------------------------------------------------------------- #
# Rational vertical-tail loads (Ch 9; SELECT.BAS subroutine 8300)
# --------------------------------------------------------------------------- #
def _effectv(vt: VTailLoadsInput) -> float:
    """Rudder effectiveness EFFECTV, a cubic in the rudder/tail area ratio SR/SV
    (SELECT.BAS) -- the same dalpha/ddelta chart fit the elevator uses."""
    r = vt.rudder_area_sqft / vt.vtail_area_sqft
    return 0.014844 + 2.7358 * r - 4.4679 * r ** 2 + 3.0306 * r ** 3


def _avt(vt: VTailLoadsInput) -> float:
    """Vertical-tail lift-curve slope AVT = 2*pi/(1 + 2/ARVT)."""
    return 2.0 * math.pi / (1.0 + 2.0 / vt.aspect_ratio_vtail)


def _default_izz(vt: VTailLoadsInput, gw: float) -> float:
    """Default airplane yaw inertia IZZ (slug-ft^2): wing mass on the span and the
    rest of the empty weight on the length (SELECT.BAS 8884)."""
    w_wing = 0.09 * gw
    return (w_wing / _G) * vt.wing_span_ft ** 2 / 12.0 \
        + ((0.62 * gw - w_wing) / _G) * vt.airplane_length_ft ** 2 / 12.0


def _vt_rudder_load(p: VnPoint, vt: VTailLoadsInput) -> float:
    """Side load from full rudder deflection (camber, cp 50% chord)."""
    return (vt.rudder_deflection_deg * vt.rudder_large_deflection_factor * _effectv(vt)
            * _avt(vt) / _DEG * p.v_eas_kt ** 2 / 295.0 * vt.vtail_area_sqft)


def _vt_aoa_load(yaw_deg: float, p: VnPoint, vt: VTailLoadsInput) -> float:
    """Side load from a yaw (angle of attack, cp 25% chord)."""
    return yaw_deg * _avt(vt) / _DEG * p.v_eas_kt ** 2 / 295.0 * vt.vtail_area_sqft


def _vt_side_gust(p: VnPoint, cg: CgCase, vt: VTailLoadsInput, izz: float) -> float:
    """Lateral gust side load at VC (FAR 23.443(b), SELECT.BAS 8840-8930)."""
    av = _avt(vt)
    k = math.sqrt(izz / (cg.weight_lb / _G))            # radius of gyration
    rho = _sigma(p.altitude_ft) * 0.002378
    lxvt = (vt.xv25 - cg.xcg) / 12.0                     # tail arm, ft
    ude = 50.0 if p.altitude_ft <= 20000.0 else 50.0 - (25.0 / 30000.0) * (p.altitude_ft - 20000.0)
    ugt = 2.0 * cg.weight_lb / (rho * vt.vtail_mac_ft * _G * av * vt.vtail_area_sqft * (k / lxvt) ** 2)
    kgt = 0.88 * ugt / (5.3 + ugt)
    return kgt * ude * p.v_eas_kt * av * vt.vtail_area_sqft / 498.0


def select_vtail(project: Project) -> List[CriticalCondition]:
    """The four critical vertical-tail loads (FAR 23.441 maneuver / 23.443 gust),
    searched over the V-n ``BAL A`` (VA) and ``BAL C`` (VC) points."""
    vt = project.vtail_loads
    fl = project.flight_loads
    if vt is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in fl.cg_cases}
    vn = _envelope(project).vn
    bal_a = [p for p in vn if p.condition == "BAL A" and p.cg in cg_map]
    bal_c = [p for p in vn if p.condition == "BAL C" and p.cg in cg_map]
    if not bal_a or not bal_c:
        return []

    srf, sra, sv = vt.rudder_fwd_hinge_sqft, vt.rudder_aft_hinge_sqft, vt.vtail_area_sqft
    gw = vt.gross_weight_lb or max(c.weight_lb for c in fl.cg_cases)
    izz = vt.izz_slugft2 or _default_izz(vt, gw)
    out: List[CriticalCondition] = []

    # 1. Sudden full rudder deflection (FAR 23.441(a)(1)) -- largest rudder load.
    p1 = max(bal_a, key=lambda p: _vt_rudder_load(p, vt))
    lv = _vt_rudder_load(p1, vt)
    on_rudder1 = (srf + 0.5 * sra) * lv / (sv - sra)
    out.append(CriticalCondition(
        component="vtail", label="SUDDEN RUDDER", far_reference="23.441(a)(1)", case=p1.case,
        loads=[LoadValue("Total tail load", lv, "lb"),
               LoadValue("Load on rudder", on_rudder1, "lb"),
               LoadValue("V (EAS)", p1.v_eas_kt, "kt(EAS)")]))

    # 2. Yaw to sideslip 19.5 deg, rudder held full (FAR 23.441(a)(2)) -- largest down.
    def total2(p: VnPoint) -> float:
        return _vt_rudder_load(p, vt) + _vt_aoa_load(-19.5, p, vt)
    p2 = min(bal_a, key=total2)
    lrud, lyaw = _vt_rudder_load(p2, vt), _vt_aoa_load(-19.5, p2, vt)
    on_rudder2 = ((srf + 0.5 * sra) * lrud / (sv - sra)
                  + 0.5 * (vt.rudder_area_sqft / (0.75 * sv)) * lyaw / sv * vt.rudder_area_sqft)
    out.append(CriticalCondition(
        component="vtail", label="YAW TO SIDESLIP", far_reference="23.441(a)(2)", case=p2.case,
        loads=[LoadValue("Total tail load", lrud + lyaw, "lb"),
               LoadValue("Load due to yaw 19.5deg (cp 25%)", lyaw, "lb"),
               LoadValue("Load due to rudder (cp 50%)", lrud, "lb"),
               LoadValue("Load on rudder", on_rudder2, "lb")]))

    # 3. Yaw 15 deg, rudder neutral (FAR 23.441(a)(3)) -- largest down.
    p3 = min(bal_a, key=lambda p: _vt_aoa_load(-15.0, p, vt))
    out.append(CriticalCondition(
        component="vtail", label="YAW 15 NEUTRAL", far_reference="23.441(a)(3)", case=p3.case,
        loads=[LoadValue("Total tail load (cp 25%)", _vt_aoa_load(-15.0, p3, vt), "lb")]))

    # 4. Lateral gust at VC (FAR 23.443(b)) -- largest.
    p4 = max(bal_c, key=lambda p: _vt_side_gust(p, cg_map[p.cg], vt, izz))
    out.append(CriticalCondition(
        component="vtail", label="SIDE GUST", far_reference="23.443(b)", case=p4.case,
        loads=[LoadValue("Total tail load (cp 25%)", _vt_side_gust(p4, cg_map[p4.cg], vt, izz), "lb"),
               LoadValue("Yaw inertia IZZ", izz, "slug-ft^2")]))
    return out


def build_critical(project: Project) -> CriticalLoadSet:
    """Compute the critical-load set for ``Project.envelope.critical``: the wing
    conditions always, plus the rational horizontal-tail balancing loads (when
    ``Project.tail_loads`` is present) and the vertical-tail loads (when
    ``Project.vtail_loads`` is present)."""
    conditions = select_wing(project)
    conditions.extend(select_htail_balancing(project))
    conditions.extend(select_vtail(project))
    return CriticalLoadSet(conditions=conditions)


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
