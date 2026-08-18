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
from typing import Dict, List, NamedTuple, Optional, Tuple

from ..case_ids import WING_BAND_EXTRA, WING_SLOTS, CaseIdAllocator, wing_case_id
from ..cg_cases import flight_cases, max_takeoff_weight
from ..constants import (
    DEG_PER_RAD,
    GUST_LOAD_FACTOR_DIVISOR,
    IN_PER_FT,
    KT_TO_FPS,
    RHO_SL,
    G,
    dynamic_pressure_psf,
    gust_alleviation_factor,
)
from ..derived_geometry import sync_geometry_derived
from ..models import (
    CaseRef,
    CgCase,
    ConditionResult,
    CriticalCondition,
    CriticalLoadSet,
    EnvelopeResult,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
    TailLoadsInput,
    VnPoint,
    VTailLoadsInput,
)
from ..registry import register
from ._vtail import large_deflection_factor, rudder_effectiveness, vtail_lift_slope
from .flight_envelope import build_envelope, density_ratio, design_inputs

MODULE_NAME = "select"

# V-n condition labels grouped by the wing search they belong to (SELECT.BAS
# 2990-3340). "GUST D" covers the program's positive-D gust label.
_PHAA = ("STALL +N", "MAN A")
_PLAA = ("MAN D", "GUST D", "GUST +D")
_PMAA = ("MAN C", "GUST +C")
_NMAA = ("STALL -N", "MAN -C", "MAN -D", "GUST -C", "GUST -D")
_ACRL = ("AC ROLL", "ACC ROLL")
_STROLL = ("ST ROL A", "ST ROL C", "ST ROL D")


def default_envelope(project: Project) -> EnvelopeResult:
    """The V-n matrix to search: the persisted ``Project.envelope`` if present, else
    freshly built from the flight-loads inputs (FLTLOADS).

    M2R-8: the **single** fallback site. ``build_critical`` computes this once and
    threads it into every ``select_*`` helper (via their ``envelope=`` parameter)
    instead of each rebuilding the whole envelope (up to 7x when nothing is
    persisted). Raises :class:`MissingInputError` when no V-n matrix can be
    obtained -- ``build_envelope`` itself raises it when the flight-loads inputs are
    absent, and an empty result is caught here."""
    if project.envelope is not None and project.envelope.vn:
        return project.envelope
    env = build_envelope(project)
    if not env.vn:
        raise MissingInputError("select needs a V-n matrix (Project.envelope or flight_loads)")
    return env


def _resolve_envelope(project: Project, envelope: Optional[EnvelopeResult]) -> EnvelopeResult:
    """The threaded envelope when ``build_critical`` supplies one, else built once."""
    return envelope if envelope is not None else default_envelope(project)


def default_critical(project: Project,
                     envelope: Optional[EnvelopeResult] = None) -> CriticalLoadSet:
    """The critical-load set to work from -- the **single owner** of the
    "persisted, else computed" choice for ``Project.envelope.critical``, one level
    below :func:`default_envelope`.

    The persisted set when the project carries one (its ``CaseRef``s already
    stamped), else SELECT's own search, run fresh. Every consumer must come through
    here: ``registry.run_all_modules`` -- the path the Export page and the CLI take
    -- never assigns ``Project.envelope``, so a module that reads
    ``project.envelope.critical`` directly and falls back to *nothing* silently
    loses every case exactly where it matters most (review F-C6; the ``tail_span``
    ``n = 1.0`` defect was the same class one level up).

    ``envelope`` is threaded to :func:`build_critical` the same way, so a caller
    that already resolved the matrix does not pay for it twice.

    Raises :class:`MissingInputError` when no V-n matrix can be obtained at all.
    """
    if project.envelope is not None and project.envelope.critical is not None:
        return project.envelope.critical
    return build_critical(project, envelope)


def vn_points(project: Project) -> List[VnPoint]:
    """The V-n matrix as a list, through :func:`default_envelope` -- ``[]`` when no
    matrix can be built at all.

    The **tolerant** read, for consumers whose fallback for a case with no V-n point
    is documented and stated in-band (``tail_span``'s ``n = 1.0``,
    ``wing_inertia``'s explicit-``nz``/``nx`` cases): the mere absence of
    flight-loads inputs must not become a hard input error for them, and they must
    not read ``project.envelope`` directly to get that tolerance.
    """
    try:
        return list(default_envelope(project).vn)
    except MissingInputError:
        return []


def vn_by_case(project: Project) -> Dict[int, VnPoint]:
    """:func:`vn_points` keyed by V-n case number -- the shape every consumer that
    resolves a ``CriticalCondition.case`` / ``WingLoadCase.case`` reference wants."""
    return {p.case: p for p in vn_points(project)}


def _cg_weights(project: Project) -> Dict[str, float]:
    """Map CG-case name -> design weight (for the Nx = -DX/W inertia factor)."""
    return {c.name: c.weight_lb for c in flight_cases(project)}


def _resultant(p: VnPoint) -> float:
    """Resultant wing load sqrt(LZW^2 + DX^2) (SELECT.BAS R1PHAA/R2PLAA/R4NAA)."""
    return math.hypot(p.lzw, p.dx)


#: Relative band inside which two candidate loads count as **the same** load
#: for a critical-case pick. Far below any printed precision, far above the
#: last-ulp reassociation noise between libm builds and Python versions.
_TIE_REL = 1e-9


def _extreme(items, key, largest: bool = True):
    """``max``/``min`` by ``key`` with a **deterministic, platform-stable tie**.

    Two V-n points can carry the same physical load — VA is the same EAS at
    every altitude and CG, so ``BAL A`` at altitude 1 and altitude 2 tie
    exactly on the rudder-load key. Exact in exact arithmetic; in floating
    point the two are computed along different paths (a ``sqrt(sigma)``
    round-trip, a ``sum()`` that Python 3.12 compensates and 3.11 does not)
    and land one ulp apart, on **different sides on different platforms**.
    ``max()`` then picks a different case in CI than on the developer's Mac
    and the frozen Imperial digest fails for a difference no printed digit
    shows.

    So: the winner is the largest (smallest) key, and among candidates whose
    keys agree to :data:`_TIE_REL` relative, the **first in list order** —
    which is exactly what ``max``/``min`` return for a bit-exact tie, so no
    pick moves on the local machine; only the platform-dependent ones become
    stable.
    """
    seq = list(items)
    keys = [key(x) for x in seq]
    best = max(keys) if largest else min(keys)
    band = _TIE_REL * abs(best)
    for x, k in zip(seq, keys):
        if (k >= best - band) if largest else (k <= best + band):
            return x
    return seq[0]  # unreachable: `best` is one of `keys`


def _pick(vn: List[VnPoint], labels, key) -> Optional[VnPoint]:
    cands = [p for p in vn if p.condition in labels]
    return _extreme(cands, key) if cands else None


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
            LoadValue("CL", p.cl, key="cl"),
            LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)", key="v_eas"),
            LoadValue("Load factor NZ", p.nz, key="load_factor_nz"),
            LoadValue("Inertia drag factor NX", nx, key="inertia_drag_factor_nx"),
            LoadValue("Altitude", p.altitude_ft, "ft", key="altitude"),
        ],
    )


def select_wing(project: Project, envelope: Optional[EnvelopeResult] = None) -> List[CriticalCondition]:
    """Search the V-n matrix for the critical wing conditions (SELECT.BAS 3000)."""
    vn = _resolve_envelope(project, envelope).vn
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
class HtailBalance(NamedTuple):
    """One V-n point's rational horizontal-tail balance (Ref 1 Ch 9).

    Attributes are lowercase Python names; the manual's symbols are the second
    column, and the equations that produce each are in :func:`htail_balance`.

    ==========  ========  =============================================
    attribute   Ch 9      quantity
    ==========  ========  =============================================
    ``lt25``    LT25      angle-of-attack load, acting at 25 % tail MAC (lb)
    ``lt50``    LT50      camber/elevator load, acting at 50 % tail MAC (lb)
    ``at``      AT        tail angle of attack, ``alpha_wl + IT - E`` (deg)
    ``delta``   DELTA     elevator deflection balancing the CG moment, TE-down + (deg)
    ``lt``      LT        total balancing load, ``LT25 + LT50`` (lb)
    ``cp``      CP        centre of pressure of the total load (% tail MAC)
    ==========  ========  =============================================

    All loads are **LIMIT** (the calc-side convention; the 1.5 factor is applied
    at the render/export boundary -- see CLAUDE.md's ultimate-load contract).
    """
    lt25: float
    lt50: float
    at: float
    delta: float
    lt: float
    cp: float


def htail_balance(p: VnPoint, cg: CgCase, xw: float, zw: float,
                  ti: TailLoadsInput) -> HtailBalance:
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
    e_down = 2.0 * DEG_PER_RAD * p.cl / (math.pi * ti.aspect_ratio_wing)  # 114.6*CL/(pi*AR)
    at = p.alpha_deg + ti.tail_incidence_deg - e_down
    aht = 2.0 * math.pi / (1.0 + 2.0 / ti.aspect_ratio_htail)
    q = dynamic_pressure_psf(p.v_eas_kt)
    st = ti.htail_area_sqft
    lt25 = (at * aht / DEG_PER_RAD) * q * st
    lt50_per_delta = (ti.elevator_effectiveness * aht / DEG_PER_RAD) * q * st
    delta = ((p.m_wf - p.dx * (cg.zcg - zw) + p.lzw * (cg.xcg - xw)
              - lt25 * (ti.xt25 - cg.xcg)) / (lt50_per_delta * (ti.xt50 - cg.xcg)))
    lt50 = lt50_per_delta * delta
    lt = lt25 + lt50
    cp = (25.0 * lt25 + 50.0 * lt50) / lt if lt else 0.0
    return HtailBalance(lt25=lt25, lt50=lt50, at=at, delta=delta, lt=lt, cp=cp)


def flaps_by_config_name(project: Project) -> Dict[str, bool]:
    """Map each ``Project.aero_coeffs`` configuration name to its flaps state
    (cruise = False, flaps_down = True), for pairing against V-n points'
    ``config`` field. Empty when the slice is absent."""
    aero = project.aero_coeffs
    flaps: Dict[str, bool] = {}
    if aero is None:
        return flaps
    if aero.cruise is not None:
        flaps[aero.cruise.name] = False
    if aero.flaps_down is not None:
        flaps[aero.flaps_down.name] = True
    return flaps


def select_htail_balancing(project: Project,
                           envelope: Optional[EnvelopeResult] = None) -> List[CriticalCondition]:
    """Select the largest up and down rational balancing tail loads (FAR 23.421),
    flaps retracted and -- when the flapped V-n envelope is present -- flaps
    extended (excluding the off-pipeline LEV LAND point)."""
    ti = project.tail_loads
    fl = project.flight_loads
    if ti is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in flight_cases(project)}
    flaps: Dict[str, bool] = flaps_by_config_name(project)

    retracted: List[Tuple[VnPoint, HtailBalance]] = []
    extended: List[Tuple[VnPoint, HtailBalance]] = []
    for p in _resolve_envelope(project, envelope).vn:
        cg = cg_map.get(p.cg)
        if cg is None:
            continue
        bucket = extended if flaps.get(p.config, False) else retracted
        if bucket is extended and p.condition == "LEV LAND":
            continue
        bucket.append((p, htail_balance(p, cg, fl.xw, fl.zw, ti)))

    def emit(label: str, pick) -> CriticalCondition:
        p, b = pick
        return _htail_condition(label, "23.421", p, b.lt, [
            LoadValue("AoA load LT25 (cp 25%)", b.lt25, "lb", key="aoa_load_lt25_cp_25_pct"),
            LoadValue("Camber/elevator load LT50 (cp 50%)", b.lt50, "lb", key="camber_elevator_load_lt50_cp_50_pct"),
            LoadValue("Tail angle of attack AT", b.at, "deg", key="tail_angle_of_attack_at"),
            LoadValue("Elevator deflection (TE dn +)", b.delta, "deg", key="elevator_deflection_te_dn"),
            LoadValue("CP of total load", b.cp, "% tail MAC", key="cp_of_total_load"),
            LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)", key="v_eas"),
        ], lt25=b.lt25, lt50=b.lt50)

    out: List[CriticalCondition] = []
    if retracted:
        out.append(emit("BAL UP RETRACTED", _extreme(retracted, lambda pb: pb[1].lt)))
        out.append(emit("BAL DN RETRACTED", _extreme(retracted, lambda pb: pb[1].lt, largest=False)))
    if extended:
        out.append(emit("BAL UP EXTENDED", _extreme(extended, lambda pb: pb[1].lt)))
        out.append(emit("BAL DN EXTENDED", _extreme(extended, lambda pb: pb[1].lt, largest=False)))
    return out


def _htail_condition(label: str, far: str, p: VnPoint, total_lt: float,
                     extra: List[LoadValue], lt25: Optional[float] = None,
                     lt50: Optional[float] = None) -> CriticalCondition:
    """Build an htail :class:`CriticalCondition` whose first load is the total.

    ``lt25``/``lt50`` are the angle-of-attack (25% MAC) and camber (50% MAC) split
    TAILDIST distributes chordwise; ``lt25 + lt50 == total_lt``."""
    return CriticalCondition(
        component="htail", label=label, far_reference=far, case=p.case,
        loads=[LoadValue("Total tail load", total_lt, "lb", key="total_tail_load"), *extra],
        lt25=lt25, lt50=lt50)


def _ef(defl: float, se2st: float) -> float:
    """Large-deflection effectiveness factor EF (SELECT.BAS subroutine 10000); see
    :func:`sloads.modules._vtail.large_deflection_factor`."""
    return large_deflection_factor(defl, se2st)


def elevator_load_parts(lt50: float, lt25: float,
                        ti: TailLoadsInput) -> Tuple[float, float]:
    """``(camber share, angle-of-attack share)`` of the elevator load.

    The two terms of :func:`elevator_load`, returned separately because the
    discrete control-surface load path (plan 09 T6, decision T-12) has to take
    each one back out of the distribution at *its own* chord station -- the
    camber share off the 50 % line and the AoA share off the 25 %, which is where
    TAILDIST puts them. Their sum is the same expression, in the same order, so
    :func:`elevator_load` is unchanged to the bit.
    """
    se, st = ti.elevator_area_sqft, ti.htail_area_sqft
    cam = (ti.elevator_fwd_hinge_sqft + 0.5 * ti.elevator_aft_hinge_sqft) * lt50 / (st - ti.elevator_aft_hinge_sqft)
    att = 0.5 * (se / (0.75 * st)) * lt25 / st * se
    return cam, att


def elevator_load(lt50: float, lt25: float, ti: TailLoadsInput) -> float:
    """Load carried by the elevator: the camber-load share aft of the hinge plus the
    angle-of-attack-load share (SELECT.BAS 5216-5218)."""
    cam, att = elevator_load_parts(lt50, lt25, ti)
    return cam + att


def select_htail_maneuver(project: Project,
                          envelope: Optional[EnvelopeResult] = None) -> List[CriticalCondition]:
    """The unchecked (FAR 23.423(a)) and checked (23.423(b)) maneuver tail loads,
    flaps retracted: full elevator deflection at the 1g VA points (unchecked) and a
    pitch-acceleration increment at the VC/VD points (checked)."""
    ti, fl = project.tail_loads, project.flight_loads
    if ti is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in flight_cases(project)}
    np_ = design_inputs(project).n_pos
    aht = 2.0 * math.pi / (1.0 + 2.0 / ti.aspect_ratio_htail)
    se2st = ti.elevator_area_sqft / ti.htail_area_sqft if ti.htail_area_sqft else 0.0
    vn = _resolve_envelope(project, envelope).vn

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
                lt50 = sign * edefl * ti.elevator_effectiveness * _ef(edefl, se2st) * aht / DEG_PER_RAD \
                    * dynamic_pressure_psf(p.v_eas_kt) * ti.htail_area_sqft
                return b.lt25 + lt50, b, lt50
            p = (min if want_min else max)(bal_a, key=lambda p: total(p)[0])
            tot, b, lt50 = total(p)
            out.append(_htail_condition(label, far, p, tot, [
                LoadValue("Balanced tail load", b.lt, "lb", key="balanced_tail_load"),
                LoadValue("AoA load (cp 25%)", b.lt25, "lb", key="aoa_load_cp_25_pct"),
                LoadValue("Elevator-deflection increment (cp 50%)", lt50, "lb",
                    key="elevator_deflection_increment_cp_50_pct"),
                LoadValue("Elevator load", elevator_load(lt50, b.lt25, ti), "lb", key="elevator_load"),
                LoadValue("Elevator deflection", sign * edefl, "deg", key="elevator_deflection"),
            ], lt25=b.lt25, lt50=lt50))

    # Checked: pitch-acceleration increment T = Iyy*theta_ddot/(arm) at VC/VD.
    def iyy(p: VnPoint) -> float:
        # Slender rod I = m*L^2/12 (the 12 is geometric, not in/ft), x0.44.
        return cg_map[p.cg].weight_lb * (ti.airplane_length_in / IN_PER_FT) ** 2 / G / 12.0 * 0.44

    def theta_ddot(p: VnPoint) -> float:
        return 39.0 * np_ * (np_ - 1.5) / p.v_eas_kt

    def increment(p: VnPoint) -> float:
        return iyy(p) * theta_ddot(p) / ((ti.xt50 - cg_map[p.cg].xcg) / IN_PER_FT)

    bal_cd = [p for p in vn if p.condition in ("BAL C", "BAL D") and in_cg(p)]
    man_cd = [p for p in vn if p.condition in ("MAN C", "MAN D") and in_cg(p)]
    if bal_cd:
        p = _extreme(bal_cd, lambda p: bal(p).lt - increment(p), largest=False)   # largest down
        b = bal(p)
        out.append(_htail_condition("CHECKED MAN DN", "23.423(b)", p, b.lt - increment(p), [
            LoadValue("Balanced tail load", b.lt, "lb", key="balanced_tail_load"),
            LoadValue("Maneuver load increment", -increment(p), "lb", key="maneuver_load_increment"),
            LoadValue("Pitch inertia Iyy", iyy(p), "slug-ft^2", key="pitch_inertia_iyy")],
            lt25=b.lt25 - increment(p), lt50=b.lt50))
    if man_cd:
        p = _extreme(man_cd, lambda p: bal(p).lt + increment(p))   # largest up
        b = bal(p)
        out.append(_htail_condition("CHECKED MAN UP", "23.423(b)", p, b.lt + increment(p), [
            LoadValue("Balanced tail load", b.lt, "lb", key="balanced_tail_load"),
            LoadValue("Maneuver load increment", increment(p), "lb", key="maneuver_load_increment"),
            LoadValue("Pitch inertia Iyy", iyy(p), "slug-ft^2", key="pitch_inertia_iyy")],
            lt25=b.lt25 + increment(p), lt50=b.lt50))
    return out


def select_htail_gust(project: Project,
                      envelope: Optional[EnvelopeResult] = None) -> List[CriticalCondition]:
    """Up and down gust tail loads, flaps retracted (FAR 23.425(a)(1)): the initial
    balancing load plus the rational gust increment at the BAL C / BAL D points."""
    ti, fl = project.tail_loads, project.flight_loads
    if ti is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in flight_cases(project)}
    aht = 2.0 * math.pi / (1.0 + 2.0 / ti.aspect_ratio_htail)
    aw, arw = ti.wing_lift_slope_per_rad, ti.aspect_ratio_wing
    mac_ft = fl.mac / IN_PER_FT
    vn = _resolve_envelope(project, envelope).vn

    def gust_increment(p: VnPoint) -> float:
        w = cg_map[p.cg].weight_lb
        ude = 50.0 if p.condition == "BAL C" else 25.0
        if p.altitude_ft > 20000.0:
            ude *= 1.0 - 0.5 * (p.altitude_ft - 20000.0) / 30000.0
        rho = density_ratio(p.altitude_ft) * RHO_SL
        ug = 2.0 * (w / fl.wing_area_sqft) / (rho * mac_ft * aw * G)
        kg = gust_alleviation_factor(ug)
        return (kg * ude * p.v_eas_kt * ti.htail_area_sqft * aht
                * (1.0 - 36.0 * (aw / DEG_PER_RAD) / arw) / GUST_LOAD_FACTOR_DIVISOR)

    bal_cd = [p for p in vn if p.condition in ("BAL C", "BAL D")
              and p.cg in cg_map and not p.config.upper().startswith("LAND")]
    if not bal_cd:
        return []

    def bal_full(p: VnPoint) -> HtailBalance:
        return htail_balance(p, cg_map[p.cg], fl.xw, fl.zw, ti)

    def bal_lt(p: VnPoint) -> float:
        return bal_full(p).lt

    out: List[CriticalCondition] = []
    up = _extreme(bal_cd, lambda p: bal_lt(p) + gust_increment(p))
    b = bal_full(up)
    out.append(_htail_condition("GUST UP RETRACTED", "23.425(a)(1)", up,
                                b.lt + gust_increment(up), [
        LoadValue("Balanced tail load", b.lt, "lb", key="balanced_tail_load"),
        LoadValue("Gust increment (cp 25%)", gust_increment(up), "lb", key="gust_increment_cp_25_pct")],
        lt25=b.lt25 + gust_increment(up), lt50=b.lt50))
    dn = _extreme(bal_cd, lambda p: bal_lt(p) - gust_increment(p), largest=False)
    b = bal_full(dn)
    out.append(_htail_condition("GUST DN RETRACTED", "23.425(a)(1)", dn,
                                b.lt - gust_increment(dn), [
        LoadValue("Balanced tail load", b.lt, "lb", key="balanced_tail_load"),
        LoadValue("Gust increment (cp 25%)", -gust_increment(dn), "lb", key="gust_increment_cp_25_pct")],
        lt25=b.lt25 - gust_increment(dn), lt50=b.lt50))

    # Flaps extended (FAR 23.425(a)(2)): the BAL VF points with a 25 fps gust at
    # sea-level density (FLTLOADS.BAS 5700-5910).
    def flap_gust_increment(p: VnPoint) -> float:
        w = cg_map[p.cg].weight_lb
        ug = 2.0 * (w / fl.wing_area_sqft) / (RHO_SL * mac_ft * aw * G)
        kg = gust_alleviation_factor(ug)
        return (kg * 25.0 * p.v_eas_kt * ti.htail_area_sqft * aht
                * (1.0 - 36.0 * (aw / DEG_PER_RAD) / arw) / GUST_LOAD_FACTOR_DIVISOR)

    bal_vf = [p for p in vn if p.condition == "BAL VF" and p.cg in cg_map]
    if bal_vf:
        up = _extreme(bal_vf, lambda p: bal_lt(p) + flap_gust_increment(p))
        b = bal_full(up)
        out.append(_htail_condition("GUST UP EXTENDED", "23.425(a)(2)", up,
                                    b.lt + flap_gust_increment(up), [
            LoadValue("Balanced tail load", b.lt, "lb", key="balanced_tail_load"),
            LoadValue("Gust increment (cp 25%)", flap_gust_increment(up), "lb", key="gust_increment_cp_25_pct")],
            lt25=b.lt25 + flap_gust_increment(up), lt50=b.lt50))
        dn = _extreme(bal_vf, lambda p: bal_lt(p) - flap_gust_increment(p), largest=False)
        b = bal_full(dn)
        out.append(_htail_condition("GUST DN EXTENDED", "23.425(a)(2)", dn,
                                    b.lt - flap_gust_increment(dn), [
            LoadValue("Balanced tail load", b.lt, "lb", key="balanced_tail_load"),
            LoadValue("Gust increment (cp 25%)", -flap_gust_increment(dn), "lb", key="gust_increment_cp_25_pct")],
            lt25=b.lt25 - flap_gust_increment(dn), lt50=b.lt50))
    return out


# Approved oracle deviation (M1-4, approved 2026-07-20): restore the full SELECT.BAS
# 23.427 candidate set, i.e. include the unchecked maneuvers. See the module note
# below and docs/20_theory/00_theory_sources.md.
_UNSYMMETRICAL_DEVIATION_NOTE = (
    "Approved oracle deviation (M1-4): the 23.427(a) unsymmetrical search includes "
    "the unchecked-maneuver conditions, per SELECT.BAS lines 6070-6175 (Ref 1 "
    "Appendix C p440-441) and 23.427(a)'s scope ('the loads prescribed in 23.421 "
    "through 23.425'). The Appendix A sample output (total -1111.8, governed by "
    "GUST -C) is a stale printout from a superseded SELECT.BAS that excluded the "
    "unchecked cases; it disagrees with its own Appendix C listing, which loads "
    "U1CK/U2CK into the candidate array (L(5)/L(6)) and takes the max over all 12."
)


def select_htail_unsymmetrical(htail: List[CriticalCondition], np_: float) -> List[CriticalCondition]:
    """The unsymmetrical horizontal-tail load (FAR 23.427(a)): the largest-magnitude
    symmetric tail load, 100% on one side and 100 - 10*(n-1) percent on the other.

    Approved oracle deviation (M1-4, approved 2026-07-20). SELECT.BAS builds a
    12-condition candidate array (lines 6030-6140) that **includes** the unchecked
    maneuvers (``L(5)=U1CK`` / ``L(6)=U2CK``) and searches all of them for the
    largest magnitude (``FOR I=1 TO 12`` at 6150-6175). 23.427(a) itself applies the
    unsymmetrical distribution to "the loads prescribed in 23.421 **through** 23.425"
    -- which spans 23.423, the unchecked maneuver. Earlier revisions of this module
    filtered the unchecked cases out (citing a CAM 3.216 rationale); that was an
    undocumented, non-conservative deviation from the BASIC and is removed here.

    The unchecked maneuver is frequently the largest H-tail load: on the Appendix A
    GA6 it governs (DN UNCHECKED, ~-1400 lb) over the down gust (-1292.8), so the
    unsymmetrical total moves from the Appendix A printout's -1111.8 to ~-1204.7.
    That printout is itself inconsistent with the Appendix C listing (it selected
    GUST -C, which the listing's full search would not) -- it was produced by a
    superseded SELECT.BAS that excluded the unchecked cases, i.e. the very behavior
    removed here. The listing + 23.427(a) are authoritative; the sample output is not.

    Sign: SELECT.BAS 6180 sets ``RHSIDE = .5*HTMAX*SGN(LT(HZCASE))`` -- half the
    governing magnitude, signed by the source case's balanced tail load. For the
    governing conditions that sign coincides with the condition's own total-load
    sign (verified against Appendix A), so ``rh = 0.5 * total`` reproduces it.
    """
    candidates = list(htail)
    if not candidates:
        return []
    pc = min(100.0 - 10.0 * (np_ - 1.0), 80.0)
    worst = _extreme(candidates, lambda c: abs(c.loads[0].value))
    total = worst.loads[0].value
    rh = 0.5 * total
    lh = (pc / 100.0) * rh
    # The chordwise distribution (cond 13) uses the worst symmetric condition's
    # LT25/LT50 split (the unsymmetrical case is the same chordwise shape).
    return [CriticalCondition(
        component="htail", label="UNSYMMETRICAL", far_reference="23.427(a)", case=worst.case,
        loads=[LoadValue("Total tail load", rh + lh, "lb", key="total_tail_load"),
               LoadValue("RH side load", rh, "lb", key="rh_side_load"),
               LoadValue("LH side load", lh, "lb", key="lh_side_load"),
               LoadValue("Other-side percent", pc, "%", key="other_side_percent")],
        lt25=worst.lt25, lt50=worst.lt50, note=_UNSYMMETRICAL_DEVIATION_NOTE)]


def select_htail(project: Project, envelope: Optional[EnvelopeResult] = None) -> List[CriticalCondition]:
    """All horizontal-tail critical loads (flaps retracted): balancing (23.421),
    unchecked/checked maneuver (23.423), gust (23.425(a)(1)) and the unsymmetrical
    load (23.427(a))."""
    if project.tail_loads is None or project.flight_loads is None:
        return []
    out = select_htail_balancing(project, envelope)
    out.extend(select_htail_maneuver(project, envelope))
    out.extend(select_htail_gust(project, envelope))
    out.extend(select_htail_unsymmetrical(out, design_inputs(project).n_pos))
    return out


# --------------------------------------------------------------------------- #
# Rational vertical-tail loads (Ch 9; SELECT.BAS subroutine 8300)
# --------------------------------------------------------------------------- #
def _effectv(vt: VTailLoadsInput) -> float:
    """Rudder effectiveness EFFECTV, a cubic in the rudder/tail area ratio SR/SV
    (SELECT.BAS) -- the same dalpha/ddelta chart fit the elevator uses."""
    return rudder_effectiveness(vt.rudder_area_sqft / vt.vtail_area_sqft)


def _avt(vt: VTailLoadsInput) -> float:
    """Vertical-tail lift-curve slope AVT = 2*pi/(1 + 2/ARVT)."""
    return vtail_lift_slope(vt.aspect_ratio_vtail)


def _default_izz(vt: VTailLoadsInput, gw: float) -> float:
    """Default airplane yaw inertia IZZ (slug-ft^2): wing mass on the span and the
    rest of the empty weight on the length (SELECT.BAS 8884)."""
    w_wing = 0.09 * gw
    # Two slender rods, I = m*L^2/12 each (the 12 is geometric, not in/ft).
    return ((w_wing / G) * (vt.wing_span_in / IN_PER_FT) ** 2 / 12.0
            + ((0.62 * gw - w_wing) / G) * (vt.airplane_length_in / IN_PER_FT) ** 2 / 12.0)


def _vt_rudder_load(p: VnPoint, vt: VTailLoadsInput) -> float:
    """Side load from full rudder deflection (camber, cp 50% chord)."""
    return (vt.rudder_deflection_deg * vt.rudder_large_deflection_factor * _effectv(vt)
            * _avt(vt) / DEG_PER_RAD * dynamic_pressure_psf(p.v_eas_kt) * vt.vtail_area_sqft)


def _vt_aoa_load(yaw_deg: float, p: VnPoint, vt: VTailLoadsInput) -> float:
    """Side load from a yaw (angle of attack, cp 25% chord)."""
    return yaw_deg * _avt(vt) / DEG_PER_RAD * dynamic_pressure_psf(p.v_eas_kt) * vt.vtail_area_sqft


def rudder_load_parts(lrud: float, lyaw: float,
                      vt: VTailLoadsInput) -> Tuple[float, float]:
    """``(camber share, angle-of-attack share)`` of the load carried by the rudder.

    The vertical tail's counterpart to :func:`elevator_load_parts`, and the same
    two terms ``select_vtail`` has computed inline since C6 -- lifted here, in the
    same order, so the conditions' ``load_on_rudder`` values are unchanged to the
    bit and the discrete control-load path (plan 09 T6, decision T-12) has one
    producer to read instead of a second copy of the arithmetic.
    """
    srf, sra, sv = vt.rudder_fwd_hinge_sqft, vt.rudder_aft_hinge_sqft, vt.vtail_area_sqft
    cam = (srf + 0.5 * sra) * lrud / (sv - sra)
    att = 0.5 * (vt.rudder_area_sqft / (0.75 * sv)) * lyaw / sv * vt.rudder_area_sqft
    return cam, att


def _vt_side_gust_terms(p: VnPoint, cg: CgCase, vt: VTailLoadsInput, izz: float
                        ) -> Tuple[float, float]:
    """``(side load, effective sideslip deg)`` of the lateral gust at VC
    (FAR 23.443(b), SELECT.BAS 8840-8930).

    The load is the .BAS's own ``Kgt*Ude*V*AVT*SV/498``; the sideslip it
    corresponds to, ``beta = Kgt*Ude/V`` (radians, ``V`` in ft/s), is
    **published** with it (L-7, decision L-7.6) rather than re-derived downstream
    -- the same ``Kgt`` and ``Ude``, so it is the load's own angle and not a
    second opinion of it. Signed for the *computed* case: the returned load is
    ``+fy`` (starboard), which is the wind-from-port, ``-beta`` hand (SC-1).
    """
    av = _avt(vt)
    k = math.sqrt(izz / (cg.weight_lb / G))            # radius of gyration
    rho = density_ratio(p.altitude_ft) * RHO_SL
    lxvt = (vt.xv25 - cg.xcg) / IN_PER_FT                     # tail arm, ft
    ude = 50.0 if p.altitude_ft <= 20000.0 else 50.0 - (25.0 / 30000.0) * (p.altitude_ft - 20000.0)
    ugt = 2.0 * cg.weight_lb / (rho * (vt.vtail_mac_in / IN_PER_FT) * G * av * vt.vtail_area_sqft * (k / lxvt) ** 2)
    kgt = gust_alleviation_factor(ugt)
    load = kgt * ude * p.v_eas_kt * av * vt.vtail_area_sqft / GUST_LOAD_FACTOR_DIVISOR
    beta_deg = -DEG_PER_RAD * kgt * ude / (p.v_eas_kt * KT_TO_FPS)
    return load, beta_deg


def _vt_side_gust(p: VnPoint, cg: CgCase, vt: VTailLoadsInput, izz: float) -> float:
    """Lateral gust side load at VC (FAR 23.443(b), SELECT.BAS 8840-8930)."""
    return _vt_side_gust_terms(p, cg, vt, izz)[0]


def fin_sideslip_derivatives(project: Project, vt: VTailLoadsInput
                             ) -> Tuple[Optional[float], Optional[float]]:
    """The fin's ``(Cy_beta, Cn_beta)`` **per degree, suite sign, about ``xw``**
    (L-7, decision L-7.11) -- built from the very ``AVT``, ``S_v`` and arm that
    make SELECT's sideslip loads, so ``balance``'s static-stability gate (note
    19 G3) sums the fin's and the body's derivatives from their owners.

    ``Cy_beta,fin = -(AVT/57.3) S_v/S_w`` (the ``+beta`` load is ``-fy``, SC-1);
    ``Cn_beta,fin = Cy_beta,fin (x_v25 - x_w)/b`` (``mz = (x - x_ref) fy`` in
    the +aft/+starboard/+up frame -- negative, restoring, for an aft fin).
    ``(None, None)`` when the wing reference (``S``, ``b``, ``xw``) is missing.
    """
    fl = project.flight_loads
    if fl is None or fl.wing_area_sqft <= 0.0 or vt.wing_span_in <= 0.0:
        return None, None
    cy = -(_avt(vt) / DEG_PER_RAD) * vt.vtail_area_sqft / fl.wing_area_sqft
    cn = cy * (vt.xv25 - fl.xw) / vt.wing_span_in
    return cy, cn


def select_vtail(project: Project, envelope: Optional[EnvelopeResult] = None) -> List[CriticalCondition]:
    """The four critical vertical-tail loads (FAR 23.441 maneuver / 23.443 gust),
    searched over the V-n ``BAL A`` (VA) and ``BAL C`` (VC) points."""
    vt = project.vtail_loads
    fl = project.flight_loads
    if vt is None or fl is None:
        return []
    cg_map: Dict[str, CgCase] = {c.name: c for c in flight_cases(project)}
    vn = _resolve_envelope(project, envelope).vn
    bal_a = [p for p in vn if p.condition == "BAL A" and p.cg in cg_map]
    bal_c = [p for p in vn if p.condition == "BAL C" and p.cg in cg_map]
    if not bal_a or not bal_c:
        return []

    # The fin's design weight: an explicit override, else the airplane's MTOW --
    # read from its single owner (G-14) rather than re-derived as the heaviest CG
    # case, which is the same number on every fixture and no longer a second
    # opinion of it.
    gw = vt.gross_weight_lb or max_takeoff_weight(project, required=False)
    izz = vt.izz_slugft2 or _default_izz(vt, gw)
    cy_fin, cn_fin = fin_sideslip_derivatives(project, vt)
    out: List[CriticalCondition] = []

    # 1. Sudden full rudder deflection (FAR 23.441(a)(1)) -- largest rudder load.
    p1 = _extreme(bal_a, lambda p: _vt_rudder_load(p, vt))
    lv = _vt_rudder_load(p1, vt)
    on_rudder1 = math.fsum(rudder_load_parts(lv, 0.0, vt))
    out.append(CriticalCondition(
        component="vtail", label="SUDDEN RUDDER", far_reference="23.441(a)(1)", case=p1.case,
        loads=[LoadValue("Total tail load", lv, "lb", key="total_tail_load"),
               LoadValue("Load on rudder", on_rudder1, "lb", key="load_on_rudder"),
               LoadValue("V (EAS)", p1.v_eas_kt, "kt(EAS)", key="v_eas")],
        lt25=0.0, lt50=lv,
        beta_deg=0.0, cy_beta_fin=cy_fin, cn_beta_fin=cn_fin))

    # 2. Yaw to sideslip 19.5 deg, rudder held full (FAR 23.441(a)(2)) -- largest down.
    def total2(p: VnPoint) -> float:
        return _vt_rudder_load(p, vt) + _vt_aoa_load(-19.5, p, vt)
    p2 = _extreme(bal_a, total2, largest=False)
    lrud, lyaw = _vt_rudder_load(p2, vt), _vt_aoa_load(-19.5, p2, vt)
    on_rudder2 = math.fsum(rudder_load_parts(lrud, lyaw, vt))
    out.append(CriticalCondition(
        component="vtail", label="YAW TO SIDESLIP", far_reference="23.441(a)(2)", case=p2.case,
        loads=[LoadValue("Total tail load", lrud + lyaw, "lb", key="total_tail_load"),
               LoadValue("Load due to yaw 19.5deg (cp 25%)", lyaw, "lb", key="load_due_to_yaw_19_5deg_cp_25_pct"),
               LoadValue("Load due to rudder (cp 50%)", lrud, "lb", key="load_due_to_rudder_cp_50_pct"),
               LoadValue("Load on rudder", on_rudder2, "lb", key="load_on_rudder")],
        lt25=lyaw, lt50=lrud,
        beta_deg=19.5, cy_beta_fin=cy_fin, cn_beta_fin=cn_fin))

    # 3. Yaw 15 deg, rudder neutral (FAR 23.441(a)(3)) -- largest down.
    p3 = _extreme(bal_a, lambda p: _vt_aoa_load(-15.0, p, vt), largest=False)
    out.append(CriticalCondition(
        component="vtail", label="YAW 15 NEUTRAL", far_reference="23.441(a)(3)", case=p3.case,
        loads=[LoadValue("Total tail load (cp 25%)", _vt_aoa_load(-15.0, p3, vt), "lb",
            key="total_tail_load_cp_25_pct")],
        lt25=_vt_aoa_load(-15.0, p3, vt), lt50=0.0,
        beta_deg=15.0, cy_beta_fin=cy_fin, cn_beta_fin=cn_fin))

    # 4. Lateral gust at VC (FAR 23.443(b)) -- largest.
    p4 = _extreme(bal_c, lambda p: _vt_side_gust(p, cg_map[p.cg], vt, izz))
    gust_load, gust_beta = _vt_side_gust_terms(p4, cg_map[p4.cg], vt, izz)
    out.append(CriticalCondition(
        component="vtail", label="SIDE GUST", far_reference="23.443(b)", case=p4.case,
        loads=[LoadValue("Total tail load (cp 25%)", gust_load, "lb",
            key="total_tail_load_cp_25_pct"),
               LoadValue("Yaw inertia IZZ", izz, "slug-ft^2", key="yaw_inertia_izz")],
        lt25=gust_load, lt50=0.0,
        beta_deg=gust_beta, cy_beta_fin=cy_fin, cn_beta_fin=cn_fin))
    return out


# --------------------------------------------------------------------------- #
# Critical fuselage conditions (Ch 9; SELECT.BAS subroutine 4000)
# --------------------------------------------------------------------------- #
def select_fuselage(project: Project, envelope: Optional[EnvelopeResult] = None) -> List[CriticalCondition]:
    """The critical fuselage *conditions* (Ch 9): the fuselage load reacted at the
    wing ``LZW - NZ*WW``, the aft-fuselage down/up bending (largest signed product
    of that load and the tail load), and the greatest vertical inertia factor for
    concentrated-weight installations. ``WW`` is the wing weight."""
    fl = project.flight_loads
    if fl is None:
        return []
    vn = _resolve_envelope(project, envelope).vn
    if not vn:
        return []
    si = project.select_input
    mtow = max_takeoff_weight(project, required=False)
    ww = (si.wing_weight_lb if si and si.wing_weight_lb else 0.09 * mtow)

    def fus_on_wing(p: VnPoint) -> float:      # fuselage load reacted at the wing
        return p.lzw - p.nz * ww

    def bending(p: VnPoint) -> float:          # aft-fuselage bending proxy
        return -fus_on_wing(p) * p.lt

    out: List[CriticalCondition] = []

    vsmax = _extreme(vn, fus_on_wing)
    out.append(CriticalCondition(
        component="fuselage", label="MAX DOWN LOAD ON WING", far_reference="23.301", case=vsmax.case,
        loads=[LoadValue("Fuselage down load on wing", fus_on_wing(vsmax), "lb", key="fuselage_down_load_on_wing"),
               LoadValue("Load factor NZ", vsmax.nz, key="load_factor_nz"),
               LoadValue("Tail load", vsmax.lt, "lb", key="tail_load")]))

    pos = [p for p in vn if p.nz > 0]
    neg = [p for p in vn if p.nz < 0]
    if pos:
        bmmax = _extreme(pos, bending)
        out.append(CriticalCondition(
            component="fuselage", label="AFT DOWN BENDING", far_reference="23.331", case=bmmax.case,
            loads=[LoadValue("Fuselage down load on wing", fus_on_wing(bmmax), "lb", key="fuselage_down_load_on_wing"),
                   LoadValue("Load factor NZ", bmmax.nz, key="load_factor_nz"),
                   LoadValue("Tail load", bmmax.lt, "lb", key="tail_load")]))
    if neg:
        bmmin = _extreme(neg, bending, largest=False)
        out.append(CriticalCondition(
            component="fuselage", label="AFT UP BENDING", far_reference="23.331", case=bmmin.case,
            loads=[LoadValue("Fuselage load on wing", fus_on_wing(bmmin), "lb", key="fuselage_load_on_wing"),
                   LoadValue("Load factor NZ", bmmin.nz, key="load_factor_nz"),
                   LoadValue("Tail load", bmmin.lt, "lb", key="tail_load")]))

    nzmax = _extreme(vn, lambda p: p.nz)
    out.append(CriticalCondition(
        component="fuselage", label="GREATEST NZ", far_reference="23.301", case=nzmax.case,
        loads=[LoadValue("Load factor NZ", nzmax.nz, key="load_factor_nz"),
               LoadValue("Balancing tail load", nzmax.lt, "lb", key="balancing_tail_load")]))
    return out


def _stamp_case_refs(project: Project, conditions: List[CriticalCondition],
                     envelope: Optional[EnvelopeResult] = None) -> None:
    """Mint a :class:`CaseRef` per condition, in this list's fixed emission order
    (wing, then htail, then vtail, then fuselage -- ``build_critical``'s own call
    order), and copy it onto the originating :class:`VnPoint` in
    ``Project.envelope.vn`` when one exists, so the V-n table can show it too.

    One allocator, scoped to this call, mints the htail/vtail/fuselage sequences.
    **Wing conditions do not use it** (M4-2 decision 4): their ``seq`` comes from
    the fixed ``case_ids.WING_SLOTS`` table, so ``PHAA`` is ``W-01`` whatever else
    the envelope selected, and WINGINER/NETLOADS reach the *same* ID for the same
    condition (decision 1 -- one ID per physical condition, no separate SELECT
    wing band). A wing label outside the table falls back to the extra band.
    """
    allocator = CaseIdAllocator()
    allocator.seed("wing", WING_BAND_EXTRA)
    vn_by_case = {p.case: p for p in _resolve_envelope(project, envelope).vn}
    for c in conditions:
        p = vn_by_case.get(c.case) if c.case is not None else None
        if c.component == "wing" and c.label in WING_SLOTS:
            case_id = wing_case_id(c.label)
        else:
            case_id = allocator.next_id(c.component)
        ref = CaseRef(
            case_id=case_id,
            component=c.component,
            condition=c.label,
            cg=p.cg if p else "",
            speed_kt=p.v_eas_kt if p else None,
            altitude_ft=p.altitude_ft if p else None,
            far_reference=c.far_reference,
        )
        c.case_ref = ref
        if p is not None:
            p.case_ref = ref


def build_critical(project: Project,
                   envelope: Optional[EnvelopeResult] = None) -> CriticalLoadSet:
    """Compute the critical-load set for ``Project.envelope.critical``: the wing
    conditions always, plus the rational horizontal-tail loads (when
    ``Project.tail_loads`` is present), the vertical-tail loads (when
    ``Project.vtail_loads`` is present) and the critical fuselage conditions.

    ``envelope`` is the caller's already-resolved V-n matrix, threaded in so a
    caller that needs both the matrix and the set does not build it twice."""
    sync_geometry_derived(project)
    # M2R-8: build the V-n envelope once and thread it into every search, instead of
    # each helper independently rebuilding it (up to 7x when nothing is persisted).
    env = _resolve_envelope(project, envelope)
    conditions = select_wing(project, env)
    conditions.extend(select_htail(project, env))
    conditions.extend(select_vtail(project, env))
    conditions.extend(select_fuselage(project, env))
    _stamp_case_refs(project, conditions, env)
    return CriticalLoadSet(conditions=conditions)


def _critical_conditions(cls: CriticalLoadSet, concept: bool) -> List[ConditionResult]:
    note = ("Concept mode -- unverified extrapolation past the FAR23 band."
            if concept else "")
    out: List[ConditionResult] = []
    for c in cls.conditions:
        notes = [n for n in (note, c.note) if n]
        out.append(ConditionResult(
            title=f"Critical {c.component} load {c.label} (case {c.case})",
            far_reference=c.far_reference,
            values=list(c.loads),
            note="  ".join(notes),
            case_ref=c.case_ref,
        ))
    return out


def run(project: Project) -> ModuleResult:
    """Run SELECT against a :class:`Project`'s envelope / flight-loads inputs."""
    cls = build_critical(project)
    return ModuleResult(module=MODULE_NAME,
                        conditions=_critical_conditions(cls, project.is_concept))


register(MODULE_NAME, run)

# --------------------------------------------------------------------------- #
# Public surface (M4-12b). Names not listed here are module-private: an
# underscore-free name outside this list is still not an import contract, and
# ``app/`` must import nothing underscored from ``sloads``.
# --------------------------------------------------------------------------- #
__all__ = [
    "MODULE_NAME",
    "HtailBalance",
    "build_critical",
    "default_critical",
    "default_envelope",
    "elevator_load",
    "elevator_load_parts",
    "flaps_by_config_name",
    "htail_balance",
    "rudder_load_parts",
    "run",
    "select_fuselage",
    "select_htail",
    "select_htail_balancing",
    "select_htail_gust",
    "select_htail_maneuver",
    "select_htail_unsymmetrical",
    "select_vtail",
    "select_wing",
    "vn_by_case",
    "vn_points",
]
