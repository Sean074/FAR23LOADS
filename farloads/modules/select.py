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
from .flight_envelope import _design_inputs, _sigma, build_envelope

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
    """Select the largest up and down rational balancing tail loads (FAR 23.421),
    flaps retracted and -- when the flapped V-n envelope is present -- flaps
    extended (excluding the off-pipeline LEV LAND point)."""
    ti = project.tail_loads
    fl = project.flight_loads
    if ti is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in fl.cg_cases}
    flaps: Dict[str, bool] = {c.name: c.flaps_down for c in fl.configurations}

    retracted, extended = [], []
    for p in _envelope(project).vn:
        cg = cg_map.get(p.cg)
        if cg is None:
            continue
        bucket = extended if flaps.get(p.config, False) else retracted
        if bucket is extended and p.condition == "LEV LAND":
            continue
        bucket.append((p, htail_balance(p, cg, fl.xw, fl.zw, ti)))

    def emit(label: str, pick) -> CriticalCondition:
        p, b = pick
        return _htail_condition(label, "23.421", p, b["LT"], [
            LoadValue("AoA load LT25 (cp 25%)", b["LT25"], "lb"),
            LoadValue("Camber/elevator load LT50 (cp 50%)", b["LT50"], "lb"),
            LoadValue("Tail angle of attack AT", b["AT"], "deg"),
            LoadValue("Elevator deflection (TE dn +)", b["DELTA"], "deg"),
            LoadValue("CP of total load", b["CP"], "% tail MAC"),
            LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)"),
        ], lt25=b["LT25"], lt50=b["LT50"])

    out: List[CriticalCondition] = []
    if retracted:
        out.append(emit("BAL UP RETRACTED", max(retracted, key=lambda pb: pb[1]["LT"])))
        out.append(emit("BAL DN RETRACTED", min(retracted, key=lambda pb: pb[1]["LT"])))
    if extended:
        out.append(emit("BAL UP EXTENDED", max(extended, key=lambda pb: pb[1]["LT"])))
        out.append(emit("BAL DN EXTENDED", min(extended, key=lambda pb: pb[1]["LT"])))
    return out


def _htail_condition(label: str, far: str, p: VnPoint, total_lt: float,
                     extra: List[LoadValue], lt25: Optional[float] = None,
                     lt50: Optional[float] = None) -> CriticalCondition:
    """Build an htail :class:`CriticalCondition` whose first load is the total.

    ``lt25``/``lt50`` are the angle-of-attack (25% MAC) and camber (50% MAC) split
    TAILDIST distributes chordwise; ``lt25 + lt50 == total_lt``."""
    return CriticalCondition(
        component="htail", label=label, far_reference=far, case=p.case,
        loads=[LoadValue("Total tail load", total_lt, "lb"), *extra],
        lt25=lt25, lt50=lt50)


def _ef(defl: float, se2st: float) -> float:
    """Large-deflection effectiveness factor EF(deflection, control/surface area
    ratio) -- SELECT.BAS subroutine 10000 (Dommasch fig 12:3). The four polynomials
    give EF at area ratios 0.15/0.2/0.3/0.4 (EF=1 at 0); interpolate by ``se2st``.
    """
    ef00 = 1.0
    ef15 = 1.008576 - 5.770396e-3 * defl - 3.452382e-4 * defl ** 2 + 7.1777799e-6 * defl ** 3
    ef20 = 1.003143 - 1.521429e-3 * defl - 2.757143e-4 * defl ** 2
    ef30 = 0.991602 - 3.329421e-2 * defl + 0.001373 * defl ** 2 - 2.595556e-5 * defl ** 3
    ef40 = 1.010976 - 2.866663e-3 * defl - 1.110476e-3 * defl ** 2 + 2.266667e-5 * defl ** 3
    s = se2st
    if s <= 0:
        return ef00
    if s < 0.15:
        return ef00 + s / 0.15 * (ef15 - ef00)
    if s < 0.2:
        return ef15 + (s - 0.15) / 0.05 * (ef20 - ef15)
    if s < 0.3:
        return ef20 + (s - 0.2) / 0.1 * (ef30 - ef20)
    if s <= 0.4:
        return ef30 + (s - 0.3) / 0.1 * (ef40 - ef30)
    return ef40 + (s - 0.4) / 0.1 * (ef40 - ef30)


def _elevator_load(lt50: float, lt25: float, ti: TailLoadsInput) -> float:
    """Load carried by the elevator: the camber-load share aft of the hinge plus the
    angle-of-attack-load share (SELECT.BAS 5216-5218)."""
    se, st = ti.elevator_area_sqft, ti.htail_area_sqft
    cam = (ti.elevator_fwd_hinge_sqft + 0.5 * ti.elevator_aft_hinge_sqft) * lt50 / (st - ti.elevator_aft_hinge_sqft)
    att = 0.5 * (se / (0.75 * st)) * lt25 / st * se
    return cam + att


def select_htail_maneuver(project: Project) -> List[CriticalCondition]:
    """The unchecked (FAR 23.423(a)) and checked (23.423(b)) maneuver tail loads,
    flaps retracted: full elevator deflection at the 1g VA points (unchecked) and a
    pitch-acceleration increment at the VC/VD points (checked)."""
    ti, fl = project.tail_loads, project.flight_loads
    if ti is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in fl.cg_cases}
    np_ = _design_inputs(project).n_pos
    aht = 2.0 * math.pi / (1.0 + 2.0 / ti.aspect_ratio_htail)
    se2st = ti.elevator_area_sqft / ti.htail_area_sqft if ti.htail_area_sqft else 0.0
    vn = _envelope(project).vn

    def bal(p: VnPoint):
        return htail_balance(p, cg_map[p.cg], fl.xw, fl.zw, ti)

    def in_cg(p: VnPoint) -> bool:
        return p.cg in cg_map and not p.config.upper().startswith("LAND")

    out: List[CriticalCondition] = []
    bal_a = [p for p in vn if p.condition == "BAL A" and in_cg(p)]
    if bal_a:
        # Unchecked: full TE-up (down load) / TE-down (up load) elevator at the 1g VA.
        for label, far, edefl, sign, want_min in (
            ("UNCHECKED MAN DN", "23.423(a)(1)", ti.elevator_te_up_deg, -1.0, True),
            ("UNCHECKED MAN UP", "23.423(a)(2)", ti.elevator_te_down_deg, +1.0, False),
        ):
            def total(p: VnPoint, edefl=edefl, sign=sign):
                b = bal(p)
                lt50 = sign * edefl * ti.elevator_effectiveness * _ef(edefl, se2st) * aht / _DEG \
                    * p.v_eas_kt ** 2 / 295.0 * ti.htail_area_sqft
                return b["LT25"] + lt50, b, lt50
            p = (min if want_min else max)(bal_a, key=lambda p: total(p)[0])
            tot, b, lt50 = total(p)
            out.append(_htail_condition(label, far, p, tot, [
                LoadValue("Balanced tail load", b["LT"], "lb"),
                LoadValue("AoA load (cp 25%)", b["LT25"], "lb"),
                LoadValue("Elevator-deflection increment (cp 50%)", lt50, "lb"),
                LoadValue("Elevator load", _elevator_load(lt50, b["LT25"], ti), "lb"),
                LoadValue("Elevator deflection", sign * edefl, "deg"),
            ], lt25=b["LT25"], lt50=lt50))

    # Checked: pitch-acceleration increment T = Iyy*theta_ddot/(arm) at VC/VD.
    def iyy(p: VnPoint) -> float:
        return cg_map[p.cg].weight_lb * ti.airplane_length_ft ** 2 / _G / 12.0 * 0.44

    def theta_ddot(p: VnPoint) -> float:
        return 39.0 * np_ * (np_ - 1.5) / p.v_eas_kt

    def increment(p: VnPoint) -> float:
        return iyy(p) * theta_ddot(p) / ((ti.xt50 - cg_map[p.cg].xcg) / 12.0)

    bal_cd = [p for p in vn if p.condition in ("BAL C", "BAL D") and in_cg(p)]
    man_cd = [p for p in vn if p.condition in ("MAN C", "MAN D") and in_cg(p)]
    if bal_cd:
        p = min(bal_cd, key=lambda p: bal(p)["LT"] - increment(p))   # largest down
        b = bal(p)
        out.append(_htail_condition("CHECKED MAN DN", "23.423(b)", p, b["LT"] - increment(p), [
            LoadValue("Balanced tail load", b["LT"], "lb"),
            LoadValue("Maneuver load increment", -increment(p), "lb"),
            LoadValue("Pitch inertia Iyy", iyy(p), "slug-ft^2")],
            lt25=b["LT25"] - increment(p), lt50=b["LT50"]))
    if man_cd:
        p = max(man_cd, key=lambda p: bal(p)["LT"] + increment(p))   # largest up
        b = bal(p)
        out.append(_htail_condition("CHECKED MAN UP", "23.423(b)", p, b["LT"] + increment(p), [
            LoadValue("Balanced tail load", b["LT"], "lb"),
            LoadValue("Maneuver load increment", increment(p), "lb"),
            LoadValue("Pitch inertia Iyy", iyy(p), "slug-ft^2")],
            lt25=b["LT25"] + increment(p), lt50=b["LT50"]))
    return out


def select_htail_gust(project: Project) -> List[CriticalCondition]:
    """Up and down gust tail loads, flaps retracted (FAR 23.425(a)(1)): the initial
    balancing load plus the rational gust increment at the BAL C / BAL D points."""
    ti, fl = project.tail_loads, project.flight_loads
    if ti is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in fl.cg_cases}
    aht = 2.0 * math.pi / (1.0 + 2.0 / ti.aspect_ratio_htail)
    aw, arw = ti.wing_lift_slope_per_rad, ti.aspect_ratio_wing
    mac_ft = fl.mac / 12.0
    vn = _envelope(project).vn

    def gust_increment(p: VnPoint) -> float:
        w = cg_map[p.cg].weight_lb
        ude = 50.0 if p.condition == "BAL C" else 25.0
        if p.altitude_ft > 20000.0:
            ude *= 1.0 - 0.5 * (p.altitude_ft - 20000.0) / 30000.0
        rho = _sigma(p.altitude_ft) * 0.002378
        ug = 2.0 * (w / fl.wing_area_sqft) / (rho * mac_ft * aw * _G)
        kg = 0.88 * ug / (5.3 + ug)
        return kg * ude * p.v_eas_kt * ti.htail_area_sqft * aht * (1.0 - 36.0 * (aw / _DEG) / arw) / 498.0

    bal_cd = [p for p in vn if p.condition in ("BAL C", "BAL D")
              and p.cg in cg_map and not p.config.upper().startswith("LAND")]
    if not bal_cd:
        return []

    def bal_full(p: VnPoint) -> Dict[str, float]:
        return htail_balance(p, cg_map[p.cg], fl.xw, fl.zw, ti)

    def bal_lt(p: VnPoint) -> float:
        return bal_full(p)["LT"]

    out: List[CriticalCondition] = []
    up = max(bal_cd, key=lambda p: bal_lt(p) + gust_increment(p))
    b = bal_full(up)
    out.append(_htail_condition("GUST UP RETRACTED", "23.425(a)(1)", up,
                                b["LT"] + gust_increment(up), [
        LoadValue("Balanced tail load", b["LT"], "lb"),
        LoadValue("Gust increment (cp 25%)", gust_increment(up), "lb")],
        lt25=b["LT25"] + gust_increment(up), lt50=b["LT50"]))
    dn = min(bal_cd, key=lambda p: bal_lt(p) - gust_increment(p))
    b = bal_full(dn)
    out.append(_htail_condition("GUST DN RETRACTED", "23.425(a)(1)", dn,
                                b["LT"] - gust_increment(dn), [
        LoadValue("Balanced tail load", b["LT"], "lb"),
        LoadValue("Gust increment (cp 25%)", -gust_increment(dn), "lb")],
        lt25=b["LT25"] - gust_increment(dn), lt50=b["LT50"]))

    # Flaps extended (FAR 23.425(a)(2)): the BAL VF points with a 25 fps gust at
    # sea-level density (FLTLOADS.BAS 5700-5910).
    def flap_gust_increment(p: VnPoint) -> float:
        w = cg_map[p.cg].weight_lb
        ug = 2.0 * (w / fl.wing_area_sqft) / (0.002378 * mac_ft * aw * _G)
        kg = 0.88 * ug / (5.3 + ug)
        return kg * 25.0 * p.v_eas_kt * ti.htail_area_sqft * aht * (1.0 - 36.0 * (aw / _DEG) / arw) / 498.0

    bal_vf = [p for p in vn if p.condition == "BAL VF" and p.cg in cg_map]
    if bal_vf:
        up = max(bal_vf, key=lambda p: bal_lt(p) + flap_gust_increment(p))
        b = bal_full(up)
        out.append(_htail_condition("GUST UP EXTENDED", "23.425(a)(2)", up,
                                    b["LT"] + flap_gust_increment(up), [
            LoadValue("Balanced tail load", b["LT"], "lb"),
            LoadValue("Gust increment (cp 25%)", flap_gust_increment(up), "lb")],
            lt25=b["LT25"] + flap_gust_increment(up), lt50=b["LT50"]))
        dn = min(bal_vf, key=lambda p: bal_lt(p) - flap_gust_increment(p))
        b = bal_full(dn)
        out.append(_htail_condition("GUST DN EXTENDED", "23.425(a)(2)", dn,
                                    b["LT"] - flap_gust_increment(dn), [
            LoadValue("Balanced tail load", b["LT"], "lb"),
            LoadValue("Gust increment (cp 25%)", -flap_gust_increment(dn), "lb")],
            lt25=b["LT25"] - flap_gust_increment(dn), lt50=b["LT50"]))
    return out


def select_htail_unsymmetrical(htail: List[CriticalCondition], np_: float) -> List[CriticalCondition]:
    """The unsymmetrical horizontal-tail load (FAR 23.427(a)): the largest-magnitude
    symmetric tail load, 100% on one side and 100 - 10*(n-1) percent on the other."""
    # The unchecked-maneuver loads are carried locally to the attach points (FAA CAM
    # 3.216 policy) and are not combined unsymmetrically, so they are excluded here.
    candidates = [c for c in htail if "UNCHECKED" not in c.label]
    if not candidates:
        return []
    pc = min(100.0 - 10.0 * (np_ - 1.0), 80.0)
    worst = max(candidates, key=lambda c: abs(c.loads[0].value))
    total = worst.loads[0].value
    rh = 0.5 * total
    lh = (pc / 100.0) * rh
    # The chordwise distribution (cond 13) uses the worst symmetric condition's
    # LT25/LT50 split (the unsymmetrical case is the same chordwise shape).
    return [CriticalCondition(
        component="htail", label="UNSYMMETRICAL", far_reference="23.427(a)", case=worst.case,
        loads=[LoadValue("Total tail load", rh + lh, "lb"),
               LoadValue("RH side load", rh, "lb"),
               LoadValue("LH side load", lh, "lb"),
               LoadValue("Other-side percent", pc, "%")],
        lt25=worst.lt25, lt50=worst.lt50)]


def select_htail(project: Project) -> List[CriticalCondition]:
    """All horizontal-tail critical loads (flaps retracted): balancing (23.421),
    unchecked/checked maneuver (23.423), gust (23.425(a)(1)) and the unsymmetrical
    load (23.427(a))."""
    if project.tail_loads is None or project.flight_loads is None:
        return []
    out = select_htail_balancing(project)
    out.extend(select_htail_maneuver(project))
    out.extend(select_htail_gust(project))
    out.extend(select_htail_unsymmetrical(out, _design_inputs(project).n_pos))
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
               LoadValue("V (EAS)", p1.v_eas_kt, "kt(EAS)")],
        lt25=0.0, lt50=lv))

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
               LoadValue("Load on rudder", on_rudder2, "lb")],
        lt25=lyaw, lt50=lrud))

    # 3. Yaw 15 deg, rudder neutral (FAR 23.441(a)(3)) -- largest down.
    p3 = min(bal_a, key=lambda p: _vt_aoa_load(-15.0, p, vt))
    out.append(CriticalCondition(
        component="vtail", label="YAW 15 NEUTRAL", far_reference="23.441(a)(3)", case=p3.case,
        loads=[LoadValue("Total tail load (cp 25%)", _vt_aoa_load(-15.0, p3, vt), "lb")],
        lt25=_vt_aoa_load(-15.0, p3, vt), lt50=0.0))

    # 4. Lateral gust at VC (FAR 23.443(b)) -- largest.
    p4 = max(bal_c, key=lambda p: _vt_side_gust(p, cg_map[p.cg], vt, izz))
    out.append(CriticalCondition(
        component="vtail", label="SIDE GUST", far_reference="23.443(b)", case=p4.case,
        loads=[LoadValue("Total tail load (cp 25%)", _vt_side_gust(p4, cg_map[p4.cg], vt, izz), "lb"),
               LoadValue("Yaw inertia IZZ", izz, "slug-ft^2")],
        lt25=_vt_side_gust(p4, cg_map[p4.cg], vt, izz), lt50=0.0))
    return out


# --------------------------------------------------------------------------- #
# Critical fuselage conditions (Ch 9; SELECT.BAS subroutine 4000)
# --------------------------------------------------------------------------- #
def select_fuselage(project: Project) -> List[CriticalCondition]:
    """The critical fuselage *conditions* (Ch 9): the fuselage load reacted at the
    wing ``LZW - NZ*WW``, the aft-fuselage down/up bending (largest signed product
    of that load and the tail load), and the greatest vertical inertia factor for
    concentrated-weight installations. ``WW`` is the wing weight."""
    fl = project.flight_loads
    if fl is None:
        return []
    vn = _envelope(project).vn
    if not vn:
        return []
    si = project.select_input
    mtow = max((c.weight_lb for c in fl.cg_cases), default=0.0)
    ww = (si.wing_weight_lb if si and si.wing_weight_lb else 0.09 * mtow)

    def fus_on_wing(p: VnPoint) -> float:      # fuselage load reacted at the wing
        return p.lzw - p.nz * ww

    def bending(p: VnPoint) -> float:          # aft-fuselage bending proxy
        return -fus_on_wing(p) * p.lt

    out: List[CriticalCondition] = []

    vsmax = max(vn, key=fus_on_wing)
    out.append(CriticalCondition(
        component="fuselage", label="MAX DOWN LOAD ON WING", far_reference="23.301", case=vsmax.case,
        loads=[LoadValue("Fuselage down load on wing", fus_on_wing(vsmax), "lb"),
               LoadValue("Load factor NZ", vsmax.nz),
               LoadValue("Tail load", vsmax.lt, "lb")]))

    pos = [p for p in vn if p.nz > 0]
    neg = [p for p in vn if p.nz < 0]
    if pos:
        bmmax = max(pos, key=bending)
        out.append(CriticalCondition(
            component="fuselage", label="AFT DOWN BENDING", far_reference="23.331", case=bmmax.case,
            loads=[LoadValue("Fuselage down load on wing", fus_on_wing(bmmax), "lb"),
                   LoadValue("Load factor NZ", bmmax.nz),
                   LoadValue("Tail load", bmmax.lt, "lb")]))
    if neg:
        bmmin = min(neg, key=bending)
        out.append(CriticalCondition(
            component="fuselage", label="AFT UP BENDING", far_reference="23.331", case=bmmin.case,
            loads=[LoadValue("Fuselage load on wing", fus_on_wing(bmmin), "lb"),
                   LoadValue("Load factor NZ", bmmin.nz),
                   LoadValue("Tail load", bmmin.lt, "lb")]))

    nzmax = max(vn, key=lambda p: p.nz)
    out.append(CriticalCondition(
        component="fuselage", label="GREATEST NZ", far_reference="23.301", case=nzmax.case,
        loads=[LoadValue("Load factor NZ", nzmax.nz),
               LoadValue("Balancing tail load", nzmax.lt, "lb")]))
    return out


def build_critical(project: Project) -> CriticalLoadSet:
    """Compute the critical-load set for ``Project.envelope.critical``: the wing
    conditions always, plus the rational horizontal-tail loads (when
    ``Project.tail_loads`` is present), the vertical-tail loads (when
    ``Project.vtail_loads`` is present) and the critical fuselage conditions."""
    conditions = select_wing(project)
    conditions.extend(select_htail(project))
    conditions.extend(select_vtail(project))
    conditions.extend(select_fuselage(project))
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
