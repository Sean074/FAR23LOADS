"""Airplane-less-tail aero-coefficient curves + their closure checks (M4-5).

The single authority for **evaluating** the Ch 7 airplane-less-tail coefficient
polynomials, and a pure builder for the Aerodynamic Data page's CL-alpha /
drag-polar / CM-alpha plot (the ``vn_diagram`` pattern: all math here, the view
only draws). ``modules.flight_envelope`` imports the evaluators, so the plotted
curve and the FLTLOADS balance can never drift apart:

    CL = C0 + (C1*a + C2*a^2 + C3*a^3 + C4*a^4) * G/Gmn        (a = AoA, deg)
    CD = D0 + D1*CL + D2*CL^2 + D3*CL^3 + D4*CL^4
    CM = M0 + (M1*a + M2*a^2 + M3*a^3 + M4*a^4) * G/Gmn

``G = 1/sqrt(1 - M^2)`` is the Glauert factor at the point's local Mach and
``Gmn`` the same at the reference Mach the coefficients were obtained at, so the
as-entered curve (the one this module plots by default) is the ``G/Gmn = 1``
curve. Reference: Ref 1 Ch 7/Ch 8; FLTLOADS.BAS subroutine 3900.

**The closure check (M4-5), stated honestly.** Two residuals, with different
content:

- ``worst_cl`` -- the **recovered-CL** residual. Each balanced ``VnPoint`` is
  re-read through the balance force triangle: inverting
  ``LZ = L*cos(a) + D*sin(a)`` / ``DX = D*cos(a) - L*sin(a)`` gives
  ``L = LZ*cos(a) - DX*sin(a)`` and hence ``CL = L/(Q*S)`` from the *dimensional*
  outputs alone; that is compared with the coefficient polynomial evaluated here.
  Within one converged point the two are algebraically the same number, so this
  residual is ~1e-16 on healthy output: it is a **drift guard**, not a numerical
  discovery. It fails if the curve and the balance ever stop evaluating the same
  polynomial, if the rotation convention changes on one side only, or if a point
  carries inconsistent dimensional output. Tolerance ``CL_CLOSURE_TOL``.
- ``worst_stall_excess`` -- the **stall-clamp** margin, which does carry
  numerical content: no balanced point may sit above its Mach-adjusted stall CL
  by more than the solver's own band. A coefficient set whose polynomial cannot
  reach the entered CLmax leaves the q-iteration unconverged, and this residual
  is what shows it. Tolerance ``STALL_CLOSURE_TOL`` (the ``_balance`` band).

The *input-side* coefficient-entry checks (CLmax reachable, positive lift slope,
positive drag over the operating band, polar shape, moment-slope sign) live in
:mod:`sloads.validation` as ``ConsistencyWarning``s, tagged for this page.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .constants import RAD_PER_DEG, dynamic_pressure_psf
from .models import AeroCoeffSet, EnvelopeResult, VnPoint

# Default plotted angle-of-attack band (deg). Widened automatically by
# :func:`build_aero_curves` when an operating point or the stall alpha falls
# outside it, so the plot never silently clips the airplane's own envelope.
ALPHA_LO_DEG = -12.0
ALPHA_HI_DEG = 20.0
ALPHA_SAMPLES = 97

# Closure tolerances (see the module docstring). The CL residual is a drift
# guard on an algebraic identity, so it is tight; the stall margin is bounded by
# the balance's own convergence band (``_balance`` breaks at +-0.005 CL).
CL_CLOSURE_TOL = 1.0e-9
STALL_CLOSURE_TOL = 0.005


# --------------------------------------------------------------------------- #
# Coefficient evaluation -- the single authority (imported by flight_envelope)
# --------------------------------------------------------------------------- #
def clmax_curve(mach: float) -> float:
    """CLmax as a function of Mach (Ch 8 least-squares fit, AR-6 23016/23009)."""
    m = mach
    return (1.19367 + 0.32739 * m + 10.8352 * m ** 2 - 44.4985 * m ** 3
            + 51.8759 * m ** 4 - 19.5434 * m ** 5)


def poly(coeffs: Sequence[float], x: float) -> float:
    """Evaluate ``c0 + c1*x + c2*x^2 + ...`` (the drag polar's plain form)."""
    return math.fsum(c * x ** i for i, c in enumerate(coeffs))


def lift_cl(config: AeroCoeffSet, alpha_deg: float,
            g: float = 1.0, gmn: float = 1.0) -> float:
    """Airplane-less-tail ``CL`` at ``alpha_deg`` (deg), Glauert-scaled by ``g/gmn``.

    ``g`` is the local Glauert factor and ``gmn`` the reference-Mach one (see the
    module docstring); the defaults give the as-entered curve. The two are kept
    as *separate* arguments rather than a pre-divided ratio so the arithmetic
    order is ``(...)*g/gmn`` exactly as FLTLOADS.BAS subroutine 3900 evaluates it
    -- this function *is* the balance's evaluation, bit-for-bit.
    """
    c0, c1, c2, c3, c4 = config.lift
    a = alpha_deg
    return c0 + (c1 * a + c2 * a ** 2 + c3 * a ** 3 + c4 * a ** 4) * g / gmn


def drag_cd(config: AeroCoeffSet, cl: float) -> float:
    """Airplane-less-tail ``CD`` at lift coefficient ``cl`` (the drag polar)."""
    return poly(config.drag, cl)


def moment_cm(config: AeroCoeffSet, alpha_deg: float,
              g: float = 1.0, gmn: float = 1.0) -> float:
    """Airplane-less-tail ``CM`` at ``alpha_deg`` (deg), Glauert-scaled by ``g/gmn``.

    Same two-argument Glauert form as :func:`lift_cl`, for the same reason.
    """
    m0, m1, m2, m3, m4 = config.moment
    a = alpha_deg
    return m0 + (m1 * a + m2 * a ** 2 + m3 * a ** 3 + m4 * a ** 4) * g / gmn


def reference_glauert(mach_ref: float) -> float:
    """``Gmn = 1/sqrt(1 - Mn^2)`` at the coefficients' reference Mach.

    ``mach_ref`` is ``FlightLoadsInput.mn``. Falls back to 1.0 (no correction)
    for a degenerate/supersonic reference Mach rather than raising -- a plot and
    a closure metric must not be the thing that breaks on odd input.
    """
    if mach_ref >= 1.0 or mach_ref < 0.0:
        return 1.0
    return 1.0 / math.sqrt(1.0 - mach_ref ** 2)


def local_mach(g_corr: float) -> float:
    """Recover a point's local Mach from its stored Glauert factor ``G``."""
    if g_corr <= 1.0:
        return 0.0
    return math.sqrt(1.0 - 1.0 / g_corr ** 2)


def stall_limits(config: AeroCoeffSet, g_corr: float,
                 mach_ref: float) -> Tuple[float, float]:
    """The (positive, negative) Mach-adjusted stall CL the balance clamps to.

    The same ``config.stall_cl * clmax_curve(M) / clmax_curve(Mn)`` scaling
    ``_balance`` applies, recovered from the point's stored Glauert factor.
    """
    kmn = clmax_curve(mach_ref)
    if not kmn:
        return config.stall_cl, config.neg_stall_cl
    k = clmax_curve(local_mach(g_corr)) / kmn
    return config.stall_cl * k, config.neg_stall_cl * k


# --------------------------------------------------------------------------- #
# Recovery from a balanced V-n point (the dimensional outputs alone)
# --------------------------------------------------------------------------- #
def dynamic_pressure(v_eas_kt: float) -> float:
    """Dynamic pressure (psf) of an equivalent airspeed in knots -- the owner is
    :func:`sloads.constants.dynamic_pressure_psf` (``V^2/295`` in FLTLOADS)."""
    return dynamic_pressure_psf(v_eas_kt)


def recovered_coefficients(point: VnPoint, wing_area_sqft: float,
                           mac_in: float) -> Tuple[float, float, float]:
    """Recover ``(CL, CD, CM)`` from one balanced point's dimensional output.

    Inverts the balance rotation (``L = LZ*cos(a) - DX*sin(a)``,
    ``D = LZ*sin(a) + DX*cos(a)``) and divides by ``Q*S`` (and ``Q*S*MAC`` for
    the moment ``M(W+F)``). Raises ``ValueError`` on a degenerate point (zero
    speed, area or MAC), which the callers treat as "no operating point".
    """
    q = dynamic_pressure(point.v_eas_kt)
    if q <= 0.0 or wing_area_sqft <= 0.0 or mac_in <= 0.0:
        raise ValueError("cannot recover coefficients from a degenerate point")
    a = point.alpha_deg * RAD_PER_DEG
    lift = point.lzw * math.cos(a) - point.dx * math.sin(a)
    drag = point.lzw * math.sin(a) + point.dx * math.cos(a)
    return (lift / (q * wing_area_sqft), drag / (q * wing_area_sqft),
            point.m_wf / (q * wing_area_sqft * mac_in))


def recovered_cl(point: VnPoint, wing_area_sqft: float) -> float:
    """The recovered ``CL`` alone (see :func:`recovered_coefficients`)."""
    q = dynamic_pressure(point.v_eas_kt)
    if q <= 0.0 or wing_area_sqft <= 0.0:
        raise ValueError("cannot recover CL from a degenerate point")
    a = point.alpha_deg * RAD_PER_DEG
    return (point.lzw * math.cos(a) - point.dx * math.sin(a)) / (q * wing_area_sqft)


# --------------------------------------------------------------------------- #
# Plot payloads
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CurveTrace:
    """One sampled polyline of a coefficient plot (equal-length x / y)."""
    name: str
    x: List[float]
    y: List[float]


@dataclass(frozen=True)
class OperatingPoints:
    """The balanced envelope points of one configuration, recovered for overlay.

    ``cl``/``cd``/``cm`` come from :func:`recovered_coefficients` (the points'
    own dimensional output), so the overlay is a read of the balance rather than
    a second evaluation of the polynomials. ``label`` is
    ``"<condition> / <cg> / <altitude> ft"``.
    """
    alpha_deg: List[float] = field(default_factory=list)
    cl: List[float] = field(default_factory=list)
    cd: List[float] = field(default_factory=list)
    cm: List[float] = field(default_factory=list)
    label: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.alpha_deg)


@dataclass(frozen=True)
class ClosureResult:
    """The M4-5 closure residuals over one configuration's balanced points.

    ``worst_cl`` is the recovered-CL drift guard and ``worst_stall_excess`` the
    stall-clamp margin (both described in the module docstring). ``passed`` is
    True when both sit inside their tolerances; ``n_points`` is 0 when the
    project carries no envelope for this configuration, in which case ``passed``
    is True vacuously and the view shows no metric.
    """
    n_points: int = 0
    worst_cl: float = 0.0
    worst_cl_label: str = ""
    worst_stall_excess: float = 0.0
    worst_stall_label: str = ""
    cl_tol: float = CL_CLOSURE_TOL
    stall_tol: float = STALL_CLOSURE_TOL

    @property
    def passed(self) -> bool:
        return (self.worst_cl <= self.cl_tol
                and self.worst_stall_excess <= self.stall_tol)


@dataclass(frozen=True)
class AeroCurves:
    """The three coefficient curves of one configuration, plus overlays.

    ``lift`` is CL vs alpha (deg), ``polar`` is CL vs **CD** (the conventional
    drag-polar orientation -- CD on the x axis, from the ``CD = f(CL)``
    polynomial), ``moment`` is CM vs alpha. ``alpha_stall_deg`` is where the lift
    curve first reaches ``stall_cl`` within the sampled band (None when it never
    does -- itself a coefficient-entry symptom, reported by ``validation``).
    """
    config_name: str
    lift: CurveTrace
    polar: CurveTrace
    moment: CurveTrace
    stall_cl: float
    neg_stall_cl: float
    alpha_lo_deg: float
    alpha_hi_deg: float
    alpha_stall_deg: Optional[float] = None
    cl_max_on_curve: float = 0.0
    points: Optional[OperatingPoints] = None
    closure: Optional[ClosureResult] = None


def _alpha_band(alpha_lo: float, alpha_hi: float,
                points: Optional[OperatingPoints]) -> Tuple[float, float]:
    """Widen the default band to hold every operating point (+2 deg of margin)."""
    lo, hi = alpha_lo, alpha_hi
    if points is not None and len(points):
        lo = min(lo, math.floor(min(points.alpha_deg)) - 2.0)
        hi = max(hi, math.ceil(max(points.alpha_deg)) + 2.0)
    return lo, hi


def build_aero_curves(config: AeroCoeffSet, *,
                      alpha_lo: float = ALPHA_LO_DEG,
                      alpha_hi: float = ALPHA_HI_DEG,
                      samples: int = ALPHA_SAMPLES,
                      g_ratio: float = 1.0,
                      points: Optional[OperatingPoints] = None,
                      closure: Optional[ClosureResult] = None) -> AeroCurves:
    """Sample one configuration's CL-alpha, drag-polar and CM-alpha curves.

    The default ``g_ratio = 1.0`` plots the coefficients **as entered** (at the
    reference Mach); operating points at a different local Mach therefore sit
    slightly off the curve, which is the honest picture and is captioned as such
    on the page.
    """
    lo, hi = _alpha_band(alpha_lo, alpha_hi, points)
    n = max(2, int(samples))
    alphas = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    cls = [lift_cl(config, a, g_ratio, 1.0) for a in alphas]
    cds = [drag_cd(config, c) for c in cls]
    cms = [moment_cm(config, a, g_ratio, 1.0) for a in alphas]

    alpha_stall: Optional[float] = None
    if config.stall_cl:
        for a, c in zip(alphas, cls):
            if c >= config.stall_cl:
                alpha_stall = a
                break

    return AeroCurves(
        config_name=config.name,
        lift=CurveTrace("CL vs alpha", list(alphas), cls),
        polar=CurveTrace("drag polar", cds, list(cls)),
        moment=CurveTrace("CM vs alpha", list(alphas), cms),
        stall_cl=config.stall_cl, neg_stall_cl=config.neg_stall_cl,
        alpha_lo_deg=lo, alpha_hi_deg=hi,
        alpha_stall_deg=alpha_stall, cl_max_on_curve=max(cls) if cls else 0.0,
        points=points, closure=closure,
    )


# --------------------------------------------------------------------------- #
# Envelope overlay + closure
# --------------------------------------------------------------------------- #
def _points_of(env: EnvelopeResult, config_name: str) -> List[VnPoint]:
    return [p for p in env.vn if p.config == config_name]


def _label(p: VnPoint) -> str:
    return f"{p.condition} / {p.cg} / {p.altitude_ft:,.0f} ft"


def operating_points(env: EnvelopeResult, config_name: str, *,
                     wing_area_sqft: float, mac_in: float) -> OperatingPoints:
    """Recover the overlay points for one configuration from a built envelope.

    Degenerate points (zero speed) are skipped rather than raising -- a plot
    overlay must never be the thing that breaks a page.
    """
    alpha, cl, cd, cm, label = [], [], [], [], []
    for p in _points_of(env, config_name):
        try:
            c_l, c_d, c_m = recovered_coefficients(p, wing_area_sqft, mac_in)
        except ValueError:
            continue
        alpha.append(p.alpha_deg)
        cl.append(c_l)
        cd.append(c_d)
        cm.append(c_m)
        label.append(_label(p))
    return OperatingPoints(alpha_deg=alpha, cl=cl, cd=cd, cm=cm, label=label)


def curve_closure(env: EnvelopeResult, config: AeroCoeffSet, *,
                  wing_area_sqft: float, mach_ref: float,
                  cl_tol: float = CL_CLOSURE_TOL,
                  stall_tol: float = STALL_CLOSURE_TOL) -> ClosureResult:
    """The M4-5 closure over every balanced point of ``config``.

    See the module docstring for what each residual does and does not prove.
    """
    worst_cl = 0.0
    worst_cl_label = ""
    worst_stall = 0.0
    worst_stall_label = ""
    n = 0
    gmn = reference_glauert(mach_ref)
    for p in _points_of(env, config.name):
        try:
            rec = recovered_cl(p, wing_area_sqft)
        except ValueError:
            continue
        n += 1
        residual = abs(rec - lift_cl(config, p.alpha_deg, p.g_corr, gmn))
        if residual > worst_cl:
            worst_cl, worst_cl_label = residual, _label(p)
        pos, neg = stall_limits(config, p.g_corr, mach_ref)
        excess = max(rec - pos, neg - rec, 0.0)
        if excess > worst_stall:
            worst_stall, worst_stall_label = excess, _label(p)
    return ClosureResult(
        n_points=n, worst_cl=worst_cl, worst_cl_label=worst_cl_label,
        worst_stall_excess=worst_stall, worst_stall_label=worst_stall_label,
        cl_tol=cl_tol, stall_tol=stall_tol,
    )
