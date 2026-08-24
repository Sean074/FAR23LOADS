"""Flap loads, from FLAPLOAD.BAS (Reference 1 Ch 17).

The flaps are sized for the critical flaps-extended condition of FAR 23.345 /
23.457(a). The flap section lift is the wing-angle-of-attack contribution plus the
deflection contribution, both from Abbott & von Doenhoff Fig 98::

    D1 = -2.6*E + 2.6        (dCLf/d(delta), per rad)      E = flap chord / wing chord
    D2 =  0.59*E + 0.08      (dCLf/dCLw)
    CLf = D1*delta_rad + D2*CLw,   CLw = n*W/(Q*SW),   Q = V^2/295

evaluated for four conditions and the largest taken:

    1G stall (V=VSF) | 2G stall (V=sqrt(2)*VSF) | 2G at VF | NG-gust at VF
    LF = CLf * Q * SF                                       23.345(a)

The chordwise distribution tapers from the leading edge to half that pressure at
the trailing edge, so ``LE psi = LF / 0.75 / SF / 144``.

Two amplifications ride on the critical load, and both are **delivered as cases**,
not merely printed (#85):

* **Slipstream** (FAR 23.457(b)) -- a momentum-theory subroutine (FLAPLOAD.BAS
  sub 500) finds the fully-developed slipstream velocity ``U1`` that absorbs
  0.85*MAXHP, contracts the prop disk area to the flap and adds the nacelle/body
  frontal area to get the slipstream band (BL_eng +/- radius); the flap load in
  the slipstream is raised by ``(V_ss/VF)^2``.
* **Head-on 25 fps gust** (FAR 23.345(c)(1)) -- the load is raised by
  ``((VF_fps + 25)/VF_fps)^2``.

The two are **independent** worst cases (a head-on gust; full takeoff power at
VF), so they are enveloped, never multiplied: ``build_flap`` emits the
gust-combined case and, when the airplane has propeller power, the slipstream
case beside it. FLAPLOAD.BAS itself printed both factors and left the
application to the designer -- defensible for a printed report, not for a solver
deck, which was shipping the understated case.

VS/VSF/VF and the design weight come from ``Project.speeds`` (STRSPEED); the wing
area from the ``Project.geometry`` wing surface; the propeller MAXHP/diameter from
``Project.engines[0]``. The flap geometry is ``Project.flap_loads``.

Reference: FLAPLOAD.BAS (Appendix C p452-454); Ref 1 Ch 17 p109-110; worked
example Appendix A "Critical Flap Loads" p201 (CLf 1.7046/1.7046/1.5593/1.5476;
LF 212/424/629/624; critical 629 lb, LE 0.545 psi; slipstream x1.407; gust
x1.301; combined 819 lb).
"""

from __future__ import annotations

import math
from typing import List, NamedTuple

from ..case_ids import WING_BAND_FLAP, CaseIdAllocator
from ..constants import (
    FT_LB_S_PER_HP,
    IN2_PER_FT2,
    IN_PER_FT,
    KT_TO_FPS,
    RHO_SL,
    ULTIMATE_FACTOR,
    dynamic_pressure_psf,
)
from ..convergence import solver_failure
from ..models import (
    CaseRef,
    ConditionResult,
    ControlSurfaceLoadResult,
    ControlSurfaceStation,
    LoadValue,
    MissingInputError,
    ModuleResult,
    Project,
)
from ..registry import register
from .structural_speeds import _wing_area_sqft, design_speed_values

# Upper bound on the slipstream-velocity search, and the trip count it implies at
# the BAS's 0.5 ft/s step. Never reached for realistic inputs -- reaching it means
# the disk cannot absorb the power at any speed, which is a refusal, not a result.
_U1_MAX_FPS = 1.0e5
_U1_TRIPS = 200000

MODULE_NAME = "flap"



class FlapResult(NamedTuple):
    """Critical flap load (+ amplifications) from FLAPLOAD.BAS."""
    clf: List[float]            # the four condition flap CLs
    clw: List[float]            # the four condition wing CLs
    lf: List[float]             # the four condition flap loads (lb)
    critical_lf_lb: float       # FAR 23.345(a) critical
    le_pressure_psi: float      # leading-edge pressure (TE = half)
    # Slipstream (FAR 23.457(b)); 0 when no engine power is supplied.
    slipstream_factor: float
    slipstream_velocity_kt: float
    slipstream_bl_inboard: float
    slipstream_bl_outboard: float
    slipstream_load_lb: float   # factor x the VF-governed condition; 0 with no slipstream
    # Head-on gust (FAR 23.345(c)(1)).
    gust_factor: float
    combined_gust_lb: float


def _slipstream_velocity(vf_kt: float, maxhp: float, pdia_in: float):
    """Fully-developed slipstream velocity ``U1`` (ft/s) absorbing 0.85*MAXHP, and
    the disk velocity ``U`` (FLAPLOAD.BAS sub 500, momentum theory).

    The upper bound on ``U1`` **raises** rather than breaking (#33,
    :mod:`sloads.convergence`). It used to fall out of the loop and return the
    bound itself as the slipstream velocity -- a 100,000 ft/s slipstream, and the
    flap load computed from it, delivered as if the search had succeeded.
    """
    pdia_ft = pdia_in / IN_PER_FT
    area = math.pi * pdia_ft ** 2 / 4.0
    vf_fps = vf_kt * KT_TO_FPS
    u1 = 0.0
    # Iterate U1 upward (the BASIC steps by 0.5) until the absorbed power reaches
    # 0.85*MAXHP: HP = area*rho*(U1-Vf)*(U1+Vf)^2 / (4*550).
    while u1 <= _U1_MAX_FPS:
        hp_try = area * RHO_SL * (u1 - vf_fps) * (u1 + vf_fps) ** 2 / (4.0 * FT_LB_S_PER_HP)
        if hp_try >= 0.85 * maxhp:
            break
        u1 += 0.5
    else:
        raise solver_failure(
            "the flap slipstream-velocity search",
            trips=_U1_TRIPS,
            detail=(f"no U1 below {_U1_MAX_FPS:.6g} ft/s absorbs 0.85 x {maxhp:.6g} hp "
                    f"through a {pdia_in:.6g} in disk at VF {vf_kt:.6g} kt"),
        )
    u = (vf_fps + u1) / 2.0
    return u1, u, area


def flap_loads(vs: float, vsf: float, vf: float, weight: float, ng: float,  # noqa: ARG001  -- FLAPLOAD input list kept whole; VSF governs
               sf: float, sw: float, delta_deg: float, e: float,
               maxhp: float = 0.0, pdia_in: float = 0.0, blprop: float = 0.0,
               af_sqft: float = 0.0) -> FlapResult:
    """Critical flap load + slipstream/gust amplifications (FLAPLOAD.BAS).

    ``vs``/``vsf`` clean/flapped stall (kt), ``vf`` flap design speed, ``weight``
    MTOW, ``ng`` flaps-extended gust factor, ``sf`` flap area one side (sq ft),
    ``sw`` wing area (sq ft), ``delta_deg`` flap deflection, ``e`` flap/wing chord
    ratio. Slipstream is computed only when ``maxhp > 0``."""
    if sf <= 0 or sw <= 0:
        raise ValueError("flap and wing areas must be positive")
    d1 = -2.6 * e + 2.6
    d2 = 0.59 * e + 0.08
    delta_rad = math.radians(delta_deg)

    # Dynamic pressures and wing CLs for the four flaps-extended conditions.
    q1 = dynamic_pressure_psf(vsf)                    # 1G stall
    q2 = dynamic_pressure_psf(math.sqrt(2.0) * vsf)   # 2G stall
    qvf = dynamic_pressure_psf(vf)                    # at VF
    clw = [
        1.0 * weight / (q1 * sw),
        2.0 * weight / (q2 * sw),
        2.0 * weight / (qvf * sw),
        ng * weight / (qvf * sw),
    ]
    qs = [q1, q2, qvf, qvf]
    clf = [d1 * delta_rad + d2 * c for c in clw]
    lf = [cl * q * sf for cl, q in zip(clf, qs)]
    critical = max(lf)
    le_psi = critical / 0.75 / sf / IN2_PER_FT2

    # Slipstream (FAR 23.457(b)).
    slip_factor = slip_v_kt = bl_in = bl_out = slip_load = 0.0
    if maxhp > 0 and pdia_in > 0:
        u1, u, aprop = _slipstream_velocity(vf, maxhp, pdia_in)
        a1 = aprop * u / u1 if u1 > 0 else 0.0   # contracted slipstream area at flap
        atot = a1 + af_sqft
        rtot_in = ((4.0 * atot / math.pi) ** 0.5 / 2.0) * IN_PER_FT
        bl_in = blprop - rtot_in
        bl_out = blprop + rtot_in
        slip_v_kt = u1 / KT_TO_FPS
        slip_factor = slip_v_kt ** 2 / vf ** 2
        # The factor is (Vss/VF)^2 -- a ratio of dynamic pressures *at VF* -- so it
        # scales the VF-based conditions, not the stall-speed ones evaluated at
        # VSF: applying it to a load computed at VSF would multiply a q it has no
        # relation to. On the manual's own example the critical condition is 2G at
        # VF, so this is exactly ``factor x critical`` there (#85).
        slip_load = slip_factor * max(lf[2], lf[3])

    # Head-on 25 fps gust (FAR 23.345(c)(1)).
    vf_fps = vf * KT_TO_FPS
    gust_factor = ((vf_fps + 25.0) / vf_fps) ** 2
    combined = gust_factor * critical

    return FlapResult(
        clf=clf, clw=clw, lf=lf, critical_lf_lb=critical, le_pressure_psi=le_psi,
        slipstream_factor=slip_factor, slipstream_velocity_kt=slip_v_kt,
        slipstream_bl_inboard=bl_in, slipstream_bl_outboard=bl_out,
        slipstream_load_lb=slip_load,
        gust_factor=gust_factor, combined_gust_lb=combined,
    )


def _engine_power(project: Project):
    """``(MAXHP, prop diameter in)`` from the first engine, or ``(0, 0)``.

    FAR 23.457(b) sizes the flap slipstream on **takeoff power** (Ref 1 p109;
    UG p14-2), so ``takeoff_hp`` is preferred, falling back to ``max_cont_hp``
    only when takeoff power is unset. FLAPLOAD.BAS's "MAX HP OF ONE ENGINE"
    prompt is the sole ambiguity; both PDFs' text quotes takeoff power.
    """
    eng = project.engine
    if eng is None:
        return 0.0, 0.0
    hp = eng.takeoff_hp or eng.max_cont_hp or 0.0
    return hp or 0.0, eng.prop_diameter_in or 0.0


def slipstream_is_available(project: Project) -> bool:
    """True when the airplane record supplies what FAR 23.457(b) needs.

    The 23.457(b) term needs both a power to absorb and a disk to absorb it
    through, which is exactly the condition :func:`flap_loads` computes it under
    (``maxhp > 0 and pdia_in > 0``). Stated once here so
    :mod:`sloads.validation` can warn on the *same* condition the module skips on
    rather than a second copy of it that can drift; the two are tied together by
    a test (#83).
    """
    hp, dia = _engine_power(project)
    return hp > 0 and dia > 0


def _compute(project: Project) -> FlapResult:
    if project.flap_loads is None:
        raise MissingInputError("flap needs the 'flap_loads' input slice")
    if project.speeds is None:
        raise MissingInputError("flap needs 'speeds' (STRSPEED VS/VSF/VF)")
    inp = project.flap_loads
    sp = project.speeds
    sv = design_speed_values(project, sp)
    sw = _wing_area_sqft(project, sp)
    maxhp, pdia = _engine_power(project)
    return flap_loads(
        vs=sv.vs, vsf=sv.vsf, vf=sv.vf, weight=sp.weight_lb,
        ng=inp.gust_load_factor, sf=inp.flap_area_one_side_sqft, sw=sw,
        delta_deg=inp.flap_deflection_deg, e=inp.flap_chord_ratio,
        maxhp=maxhp, pdia_in=pdia, blprop=inp.engine_butt_line_in,
        af_sqft=inp.nacelle_frontal_area_sqft,
    )


def build_flap(project: Project) -> List[ControlSurfaceLoadResult]:
    """The delivered flap cases: the gust-combined envelope, plus the FAR 23.457(b)
    slipstream case whenever the airplane carries propeller power.

    The slipstream case is a **second case beside** the gust-combined one, not a
    product with it: the two are independent worst cases (a 25 fps head-on gust
    and full takeoff power at VF), and the manual prints their factors
    separately. The governing flap load is the larger of the two -- on the C210 it
    is the slipstream case, 19 % above what shipped before #85.

    The factored load is stated over the **whole** flap, not over the band alone:
    :class:`~sloads.models.ControlSurfaceLoadResult` carries chord fractions and no
    spanwise dimension (see ``control_surface_force_moment_cards``), so there is
    nowhere to put a partial-span distribution. The band's butt lines are reported
    beside the case; applying the factor over the full surface is conservative for
    the flap and its attachments, and is stated rather than implied.
    """
    r = _compute(project)
    inp, sp = project.flap_loads, project.speeds
    if inp is None or sp is None:  # _compute has already refused; narrows for the reads below
        raise MissingInputError("flap needs 'flap_loads' and 'speeds'")
    surface = inp.surface
    sv = design_speed_values(project, sp)
    load = max(r.critical_lf_lb, r.combined_gust_lb)
    case = "flap gust-combined" if r.combined_gust_lb >= r.critical_lf_lb else "flap 23.345(a)"
    # W- ids from the FLAPLOAD band (case_ids.WING_BAND_FLAP..69).
    allocator = CaseIdAllocator()
    allocator.seed("wing", WING_BAND_FLAP)

    def _case(name: str, lb: float) -> ControlSurfaceLoadResult:
        """One flap case with the Ch 17 chordwise taper (LE -> half at TE)."""
        le = lb / 0.75 / inp.flap_area_one_side_sqft / IN2_PER_FT2
        ref = CaseRef(case_id=allocator.next_id("wing"), component="wing",
                      condition=name, far_reference="23.345/23.457")
        # Minted here (flap owns its conditions); run() copies each onto its
        # rendered ConditionResult so report and export can never disagree
        # (defect M4-13).
        return ControlSurfaceLoadResult(
            surface=surface, case=name, load_lb=lb, v_kt=sv.vf,
            stations=[ControlSurfaceStation(x=0.0, psi=le),
                      ControlSurfaceStation(x=1.0, psi=le / 2.0)],
            case_ref=ref, safety_factor=ULTIMATE_FACTOR)

    cases = [_case(case, load)]
    if r.slipstream_load_lb > 0:
        cases.append(_case("flap slipstream 23.457(b)", r.slipstream_load_lb))
    return cases


def run(project: Project) -> ModuleResult:
    """Run FLAPLOAD: the critical flaps-extended flap load (FAR 23.345 / 23.457)."""
    if project.flap_loads is None:
        raise MissingInputError("Project has no 'flap_loads' inputs for the flap module")
    r = _compute(project)
    values = [
        LoadValue("Critical flap load (23.345(a))", r.critical_lf_lb, "lb", key="critical_flap_load_23_345_a"),
        LoadValue("LE pressure (TE = half)", r.le_pressure_psi, "lb/in^2", key="le_pressure_te_half"),
        LoadValue("Flap CL 1G stall", r.clf[0], key="flap_cl_1g_stall"),
        LoadValue("Flap CL 2G stall", r.clf[1], key="flap_cl_2g_stall"),
        LoadValue("Flap CL 2G at VF", r.clf[2], key="flap_cl_2g_at_vf"),
        LoadValue("Flap CL gust at VF", r.clf[3], key="flap_cl_gust_at_vf"),
        LoadValue("Flap load 1G stall", r.lf[0], "lb", key="flap_load_1g_stall"),
        LoadValue("Flap load 2G stall", r.lf[1], "lb", key="flap_load_2g_stall"),
        LoadValue("Flap load 2G at VF", r.lf[2], "lb", key="flap_load_2g_at_vf"),
        LoadValue("Flap load gust at VF", r.lf[3], "lb", key="flap_load_gust_at_vf"),
        LoadValue("Head-on gust factor", r.gust_factor, key="head_on_gust_factor"),
        LoadValue("Flap load combined w/ gust", r.combined_gust_lb, "lb", key="flap_load_combined_w_gust"),
    ]
    note = ("Critical flaps-extended load (Abbott & von Doenhoff Fig 98); chordwise "
            "taper LE -> half at TE. Slipstream FAR 23.457(b), gust FAR 23.345(c)(1).")
    if project.is_concept:
        note += " Concept mode -- unverified extrapolation past the FAR23 band."
    built = build_flap(project)
    conditions = [ConditionResult(
        title="Critical flap loads", far_reference="23.345", values=values, note=note,
        # Same per-case factor the sbeam export scales by, so the rendered and
        # exported ULTIMATE loads can never disagree (defect M4-13).
        case_ref=built[0].case_ref, safety_factor=built[0].safety_factor)]
    # The slipstream is its own delivered case, so it is its own reported
    # condition: one ConditionResult per exported case keeps the M4-13 pairing
    # exact, and prints the governing number instead of leaving the factor as an
    # exercise for the reader (#85).
    if r.slipstream_factor > 0:
        conditions.append(ConditionResult(
            title="Flap loads in the propeller slipstream",
            far_reference="23.457(b)",
            values=[
                LoadValue("Slipstream factor", r.slipstream_factor, key="slipstream_factor"),
                LoadValue("Slipstream velocity at flap", r.slipstream_velocity_kt, "kt(EAS)",
                    key="slipstream_velocity_at_flap"),
                LoadValue("Slipstream inboard BL", r.slipstream_bl_inboard, "in",
                    key="slipstream_inboard_bl"),
                LoadValue("Slipstream outboard BL", r.slipstream_bl_outboard, "in",
                    key="slipstream_outboard_bl"),
                LoadValue("Flap load in slipstream", r.slipstream_load_lb, "lb",
                    key="flap_load_in_slipstream"),
            ],
            note=("FAR 23.457(b): the flap load inside the slipstream band is the "
                  "VF-governed condition raised by (Vss/VF)^2. Delivered as a case "
                  "beside the gust-combined one, not multiplied with it -- the two "
                  "are independent worst cases. The factored load is stated over "
                  "the whole flap (the case carries chord fractions, no span), "
                  "which is conservative for the flap and its attachments."),
            case_ref=built[-1].case_ref, safety_factor=built[-1].safety_factor))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)
