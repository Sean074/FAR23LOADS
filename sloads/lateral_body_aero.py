"""Lumped wing-body lateral aero in sideslip: ``Cy_beta`` and ``Cn_beta`` (L-7).

Design note ``docs/30_future/19_l7_lateral_body_aero_note.md`` (rev. 3, agreed
2026-08-17). The fin was the only lateral aerodynamic load the suite computed;
this module supplies the **wing-body** side-force and yawing-moment derivatives
in sideslip so ``balance`` can apply the missing term beside the fin's
(``source="body-aero"``) and the two lateral degrees of freedom of the free-free
closure -- ``n_y`` and ``psi_ddot`` -- stop being stated as "over/under-stated
by an unknown amount".

Method: **USAF DATCOM 5.2.1.1 (wing-body ``Cy_beta``) and 5.2.3.1 (wing-body
``Cn_beta``)**, transcribed from the Digital DATCOM Fortran (public domain,
bundled at ``reference/datcom/datcom.f``; provenance in its ``PROVENANCE.md``),
including its digitised chart data, so no constant here is invented:

* body lift-curve slope ``CL_alpha,B`` -- DATCOM 4.2.1.1, subroutine ``BODYRT``
  (``datcom.f:2326-2462``): ``2 (k2-k1) S_0 / S_ref`` per radian, ``S_0`` the
  section area at ``x_0 = 0.378 l_B + 0.527 x_1``, ``x_1`` the station of the
  steepest area decrease (``l_B`` if the area never decreases), ``(k2-k1)`` from
  figure 4.2.1.1-20 on the fineness ratio ``l_B / d_eq(S_max)``;
* wing-body side force -- subroutine ``SUBLAT`` (``datcom.f:29027-29036``):
  ``Cy_beta,WB = -K_i CL_alpha,B - 0.0001 |Gamma|`` per degree, ``K_i`` the
  wing-height interference factor of figure 5.2.1.1-7 in closed form
  (``1 + 0.49 (2 z_w/d)`` for a low wing, ``1 - 0.85 (2 z_w/d)`` for a high
  one; ``z_w`` positive for a wing below the body centreline);
* wing-body yawing moment -- ``SUBLAT`` (``datcom.f:29038-29052``):
  ``Cn_beta,WB = -K_N K_Rl S_BS l_B / (S_ref b)`` per degree, ``K_N`` from the
  three chained charts of figure 5.2.3.1-8 (tables ``X158A..Y58C`` at
  ``datcom.f:28723-28756``) on ``l_B^2/S_BS``, ``x_cg/l_B``,
  ``sqrt(h_1/h_2)`` (body heights at 0.25 and 0.75 ``l_B``) and ``h_max/w_max``;
  ``K_Rl = 1 + ln(Re_l 1e-6)/4.86`` the closed form of figure 5.2.3.1-9.

The chart look-ups reproduce Digital DATCOM's own interpolators (``TLINEX``,
``TLIN1X``, ``TBFUNX``, ``datcom.f:40816``, ``:40501``, ``:39130``): piecewise
linear inside a table, and outside it clamped / linearly / quadratically
extrapolated exactly as the Fortran's per-call flags say -- **the port follows
the Fortran, not the printed figures** (decision L-7.14), because the Fortran's
sample output is the oracle: ``tests/test_lateral_body_aero.py`` pins the
applicable printed ``CYB``/``CNB`` of ``reference/datcom/examples`` at +/-0.1 %.

Signs. DATCOM's derivatives are stability-axis (``+Cy`` starboard, ``+Cn`` nose
starboard); the suite's frame (``CONVENTIONS.md`` §1, +aft/+starboard/+up,
``+mz`` = nose to port, SC-1: ``+beta`` = wind from starboard) shares the side
force sign and **negates** the yaw sign. :class:`LateralBodyAeroEstimate`
carries both: ``cn_beta`` in the suite's sign (positive = destabilizing) and
``cn_beta_datcom`` for the oracle. Everything is **per degree** (L-7.15),
matching ``FuselageMomentInput.d_cm_dalpha`` and DATCOM's printout.

The moment reference for the computed ``Cn_beta`` is the wing 25 %-MAC station
``xw`` -- the suite's aerodynamic reference, where the trim's airplane-less-tail
force system already acts (``flight_envelope._balance``, ``fuselage-cm``) --
and it is transferred to each case's CG by ``balance`` through the fixed
side-force station (decision L-7.9): ``balance`` applies the side force at the
body side-area centroid :func:`side_area_centroid` and the balance of the
moment as a free couple, so the pair reproduces ``(Cy_beta, Cn_beta)`` about
``xw`` exactly and about the case CG by the lever arm.

What has a printed oracle and what does not: ``K_N``, ``K_Rl`` (with its
Reynolds dependence), ``CL_alpha,B`` on both ``x_1`` paths and with the section
area entered or derived from a circular half-width -- yes (G1). The wing-height
factor ``K_i`` and the dihedral term -- **no**: every Digital DATCOM sample case
has ``z_w = 0`` and zero dihedral, so those two lines are transcribed and
unit-tested against the closed forms only, and the test says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .constants import DEG_PER_RAD, IN2_PER_FT2, IN_PER_FT
from .models import FuselageOutline

# --------------------------------------------------------------------------- #
# Digitised DATCOM charts (datcom.f, DATA statements)
# --------------------------------------------------------------------------- #
#: Figure 4.2.1.1-20, apparent-mass factor (k2 - k1) vs body fineness ratio
#: (``X21120``/``Y21120``, datcom.f:2334-2335). Digital DATCOM's own
#: digitisation -- distinct from Munk's TR-184 table in ``fuselage_moment``,
#: which is the pitch estimator's owner; this one is the oracle's.
_K2K1_FINENESS = (4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0)
_K2K1_VALUES = (0.77, 0.825, 0.865, 0.91, 0.94, 0.955, 0.965, 0.97, 0.973, 0.975)

#: Figure 5.2.3.1-8A: rows ``l_B^2/S_BS`` (descending, as the Fortran stores
#: it), columns ``x_cg/l_B`` = 0.2, 0.8 (``X158A``/``X258A``/``Y58A``).
_KN_A_X1 = (20.0, 14.0, 10.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.5)
_KN_A_X2 = (0.2, 0.8)
_KN_A_Y = ((0.10, 1.88), (0.40, 2.21), (0.74, 2.60), (0.98, 2.80), (1.30, 3.13),
           (1.61, 3.50), (2.00, 3.88), (2.50, 4.40), (2.99, 5.00), (3.45, 5.40))
#: Figure 5.2.3.1-8B: rows ``sqrt(h1/h2)``, columns = chart A's output.
_KN_B_X1 = (0.8, 1.0, 1.2, 1.4, 1.6)
_KN_B_X2 = (0.0, 3.0, 6.0)
_KN_B_Y = ((0.0, 2.35, 4.68), (0.0, 3.00, 6.00), (0.0, 3.60, 7.25),
           (0.0, 4.18, 8.50), (0.0, 4.79, 9.50))
#: Figure 5.2.3.1-8C: rows ``h_max/w_max``, columns = chart B's output -> K_N.
_KN_C_X1 = (0.5, 0.6, 0.8, 1.0, 2.0)
_KN_C_X2 = (0.0, 6.0)
_KN_C_Y = ((-0.00048, 0.00251), (-0.00048, 0.0035), (-0.00048, 0.00477),
           (-0.00048, 0.00559), (-0.00048, 0.00641))

#: Closed form of figure 5.2.3.1-9 (``RKRL``, datcom.f:29040).
_KRL_LOG_DIVISOR = 4.86
#: Dihedral term of DATCOM 5.2.1.1, per degree of sideslip per degree of dihedral.
_DIHEDRAL_CY_PER_DEG = 0.0001
#: ``x_0 = 0.378 l_B + 0.527 x_1`` (BODYRT, datcom.f:2401 ``BD(7)``).
_X0_LENGTH_FRAC = 0.378
_X0_X1_FRAC = 0.527


# --------------------------------------------------------------------------- #
# Digital DATCOM's interpolators, ported (TBFUNX / TLIN1X / TLINEX / QUAD)
# --------------------------------------------------------------------------- #
def _quad(xs: Sequence[float], ys: Sequence[float], xa: float) -> float:
    """``QUAD``: the parabola through three points, evaluated at ``xa``."""
    (x0, x1, x2), (y0, y1, y2) = xs, ys
    # Lagrange form -- identical to the Fortran's determinant solve.
    return (y0 * (xa - x1) * (xa - x2) / ((x0 - x1) * (x0 - x2))
            + y1 * (xa - x0) * (xa - x2) / ((x1 - x0) * (x1 - x2))
            + y2 * (xa - x0) * (xa - x1) / ((x2 - x0) * (x2 - x1)))


def _quad_slope(xs: Sequence[float], ys: Sequence[float], xa: float) -> float:
    """``QUAD``'s derivative branch: slope of the parabola through three points."""
    (x0, x1, x2), (y0, y1, y2) = xs, ys
    return (y0 * (2 * xa - x1 - x2) / ((x0 - x1) * (x0 - x2))
            + y1 * (2 * xa - x0 - x2) / ((x1 - x0) * (x1 - x2))
            + y2 * (2 * xa - x0 - x1) / ((x2 - x0) * (x2 - x1)))


def _switch(xa: float, xg: Sequence[float], lxl: int, lxu: int
            ) -> Tuple[bool, bool, bool]:
    """``SWITCH``: ``(above, below, extrapolate)`` for a look-up at ``xa``.

    ``lxl``/``lxu`` are the Fortran's per-call flags for a value below/above the
    table: ``<= 0`` clamp to the end value, ``1`` extrapolate linearly, ``> 1``
    extrapolate on the parabola through the end three points.
    """
    ascending = not (xg[0] > xg[-1])
    above = below = False
    if ascending:
        above, below = xa > xg[-1], xa < xg[0]
    else:
        below, above = xa > xg[0], xa < xg[-1]
    if above:
        return above, below, lxu > 0
    if below:
        return above, below, lxl > 0
    return False, False, False


def _glook(xa: float, xg: Sequence[float]) -> Tuple[bool, int, float]:
    """``GLOOK``: bracketing index and fraction; ``noin`` when no interpolation
    is needed (exact hit to 0.1 %, or the value is at/outside an end)."""
    ascending = not (xg[0] > xg[-1])
    tempg = 0.0
    ii = len(xg) - 1
    noin = False
    for i, x in enumerate(xg):
        ii = i
        temg = xa - x
        dmg = xa if xa != 0.0 else x
        if abs(dmg) <= 1e-4:
            dmg = 1.0
        if abs(temg / dmg) < 1e-3:
            noin = True
            break
        if ascending and temg < 0.0:
            break
        if not ascending and temg > 0.0:
            break
        tempg = temg
    else:
        noin = True
    if ii == 0:
        noin = True
    tg = 0.0 if noin else tempg / (tempg - (xa - xg[ii]))
    return noin, ii, tg


def _tlin1x(x: Sequence[float], y: Sequence[float], xa: float,
            lxl: int, lxu: int) -> float:
    """``TLIN1X``: linear look-up in one variable with the Fortran's end rules."""
    above, _below, extrap = _switch(xa, x, lxl, lxu)
    n = len(x)
    if not extrap:
        noin, i, t = _glook(xa, x)
        d2 = y[i]
        return d2 if noin else y[i - 1] + t * (d2 - y[i - 1])
    if above:
        if lxu > 1 and n > 2:
            return _quad(x[n - 3:], y[n - 3:], xa)
        t = (xa - x[-1]) / (x[-1] - x[-2])
        return y[-1] + t * (y[-1] - y[-2])
    if lxl > 1 and n > 2:
        return _quad(x[:3], y[:3], xa)
    t = (xa - x[0]) / (x[1] - x[0])
    return y[0] + t * (y[1] - y[0])


def _tlinex(x1: Sequence[float], x2: Sequence[float],
            y: Sequence[Sequence[float]], xa1: float, xa2: float,
            lx1l: int, lx2l: int, lx1u: int, lx2u: int) -> float:
    """``TLINEX``: ``y = f(x1, x2)``, rows of ``y`` indexed by ``x1``.

    Linear in both variables inside the table; the ``x2`` direction goes through
    :func:`_tlin1x` with its own flags, the ``x1`` direction reproduces the
    Fortran's row bookkeeping (linear between rows, and beyond the table either
    clamped, linear from the end two rows, or the parabola through the end
    three rows).
    """
    def row(i: int) -> float:
        return _tlin1x(x2, y[i], xa2, lx2l, lx2u)

    above, below, extrap = _switch(xa1, x1, lx1l, lx1u)
    n = len(x1)
    if not extrap:
        noin, i1, t1 = _glook(xa1, x1)
        d2 = row(i1)
        if noin:
            return d2
        d1 = row(i1 - 1)
        return d1 + t1 * (d2 - d1)
    if below:
        t1 = (xa1 - x1[0]) / (x1[1] - x1[0])
        i1 = 1
    else:
        t1 = (xa1 - x1[-1]) / (x1[-1] - x1[-2])
        i1 = n - 1
    d2 = row(i1)
    d1 = row(i1 - 1)
    if n >= 3:
        if above and lx1u > 1:
            d0 = row(i1 - 2)
            return _quad(x1[i1 - 2:i1 + 1], (d0, d1, d2), xa1)
        if below and lx1l > 1:
            d0, d1, d2 = d1, d2, row(2)
            return _quad(x1[:3], (d0, d1, d2), xa1)
    if above:
        return d2 + t1 * (d2 - d1)
    return d1 + t1 * (d2 - d1)


def _tbfunx(xa: float, x: Sequence[float], y: Sequence[float],
            lexl: int, lexu: int) -> Tuple[float, float]:
    """``TBFUNX``: ``(y, dy/dx)`` -- piecewise-linear value, parabolic slope.

    Inside the table the value is linear between the bracketing points and the
    slope is that of the parabola through the three points around them; at or
    beyond an end the flags rule as in :func:`_switch` (``1`` = linear from the
    end two points, ``> 1`` = the end parabola, ``<= 0`` = the end value).
    """
    n = len(x)
    if n < 3:
        # The Fortran's two-point branch: linear, clamped.
        if xa <= x[0]:
            return y[0], (y[1] - y[0]) / (x[1] - x[0])
        if xa >= x[-1]:
            return y[-1], (y[1] - y[0]) / (x[1] - x[0])
        t = (xa - x[0]) / (x[1] - x[0])
        return y[0] + t * (y[1] - y[0]), (y[1] - y[0]) / (x[1] - x[0])
    if x[0] < xa < x[-1]:
        idx = 0
        for i in range(n - 1):
            if xa >= x[i]:
                idx = i
        if idx == 0:
            idx = 1
        xs, ys = x[idx - 1:idx + 2], y[idx - 1:idx + 2]
        if xa < x[1]:
            val = ys[0] + (ys[1] - ys[0]) * (xa - xs[0]) / (xs[1] - xs[0])
        else:
            val = ys[1] + (ys[2] - ys[1]) * (xa - xs[1]) / (xs[2] - xs[1])
        return val, _quad_slope(xs, ys, xa)
    # At or beyond an end.
    at_upper = xa >= x[-1]
    lind = lexu if at_upper else lexl
    xs, ys = (x[n - 3:], y[n - 3:]) if at_upper else (x[:3], y[:3])
    if lind == 1:
        slope = ((y[-1] - y[-2]) / (x[-1] - x[-2]) if at_upper
                 else (y[1] - y[0]) / (x[1] - x[0]))
        base = y[-1] if at_upper else y[0]
        anchor = x[-1] if at_upper else x[0]
        return (xa - anchor) * slope + base, slope
    if lind <= 0:
        return (y[-1] if at_upper else y[0]), _quad_slope(xs, ys, xa)
    return _quad(xs, ys, xa), _quad_slope(xs, ys, xa)


def _trapz(y: Sequence[float], x: Sequence[float]) -> float:
    """``TRAPZ``: trapezoidal integral of ``y`` over ``x``."""
    return math.fsum(0.5 * (y[i] + y[i + 1]) * (x[i + 1] - x[i])
                     for i in range(len(x) - 1))


def _getmax(x: Sequence[float], s: Sequence[float]) -> Tuple[float, float]:
    """``GETMAX``: ``(x, s)`` at the first strict maximum of ``s``."""
    xm, sm = x[0], s[0]
    for xi, si in zip(x[1:], s[1:]):
        if si > sm:
            xm, sm = xi, si
    return xm, sm


# --------------------------------------------------------------------------- #
# The DATCOM body, in DATCOM's own terms
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DatcomBody:
    """A body as Digital DATCOM's ``$BODY`` namelist describes it.

    ``x`` fuselage stations from the nose; ``s`` cross-section areas; ``r``
    planform half-widths; ``zu``/``zl`` the upper/lower profile (optional --
    when absent the body is taken as round, height ``2 r``, exactly as the
    Fortran does). One consistent length unit throughout; the results are
    dimensionless except ``reynolds_per_length``, which must be per that unit.
    """
    x: Tuple[float, ...]
    s: Tuple[float, ...]
    r: Tuple[float, ...]
    zu: Optional[Tuple[float, ...]] = None
    zl: Optional[Tuple[float, ...]] = None

    @property
    def length(self) -> float:
        return self.x[-1] - self.x[0]

    def heights(self) -> Tuple[float, ...]:
        """Body depth at each station: ``zu - zl``, else ``2 r``."""
        if self.zu is not None and self.zl is not None:
            return tuple(u - low for u, low in zip(self.zu, self.zl))
        return tuple(2.0 * ri for ri in self.r)


def datcom_body_from_outline(outline: Optional[FuselageOutline]) -> Optional[DatcomBody]:
    """The suite's G1 outline as a :class:`DatcomBody` (inches, from the nose).

    Section area is the ellipse ``pi/4 * width * height`` the outline commits to
    (:class:`~sloads.models.FuselageSection`); half-width ``width/2``; the profile
    ``+/- height/2`` about the section centre (only ``zu - zl`` and its integral
    are read, so the datum does not matter). ``None`` with fewer than two
    sections or a non-positive length -- the same "no body, no term" answer
    :func:`sloads.fuselage_moment.estimate` gives.
    """
    if outline is None:
        return None
    secs = sorted(outline.sections, key=lambda sec: sec.x)
    if len(secs) < 2 or secs[-1].x - secs[0].x <= 0.0:
        return None
    x0 = secs[0].x
    return DatcomBody(
        x=tuple(sec.x - x0 for sec in secs),
        s=tuple(math.pi / 4.0 * sec.width * sec.height for sec in secs),
        r=tuple(0.5 * sec.width for sec in secs),
        zu=tuple(0.5 * sec.height for sec in secs),
        zl=tuple(-0.5 * sec.height for sec in secs),
    )


# --------------------------------------------------------------------------- #
# DATCOM 4.2.1.1 -- body lift-curve slope (BODYRT)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BodyLiftSlope:
    """``CL_alpha,B`` per degree and the intermediates BODYRT prints."""
    cl_alpha: float          # per degree, on s_ref
    k2_minus_k1: float
    fineness_ratio: float    # l_B / d_eq(S_max)
    x0: float                # station of S_0, from the nose
    s0: float                # section area at x0
    x1: float                # station of the steepest area decrease (l_B if none)


def body_lift_slope(body: DatcomBody, s_ref: float) -> BodyLiftSlope:
    """DATCOM 4.2.1.1 body lift-curve slope, subroutine ``BODYRT``
    (``datcom.f:2326-2462``): ``2 (k2-k1) S_0 / (RAD S_ref)`` per degree.

    ``x_1`` is the station where ``-dS/dx`` (the parabolic slope of ``TBFUNX``,
    flags ``(2, 1)``) is greatest, if the area ever decreases, else the body
    length; ``x_0 = 0.378 l_B + 0.527 x_1``; ``S_0`` is the area interpolated at
    ``x_0``; ``(k2-k1)`` reads figure 4.2.1.1-20 on ``l_B / sqrt(4 S_max / pi)``.
    """
    x, s = body.x, body.s
    l_b = x[-1]
    _, s_max = _getmax(x, s)
    decreasing = any(s[k] < s[k - 1] for k in range(1, len(s)))
    if decreasing:
        neg_slopes = [-_tbfunx(xk, x, s, 2, 1)[1] for xk in x]
        x1, _ = _getmax(x, neg_slopes)
    else:
        x1 = l_b
    x0 = _X0_LENGTH_FRAC * l_b + _X0_X1_FRAC * x1
    s0 = _tbfunx(x0, x, s, 0, 0)[0]
    fineness = l_b / math.sqrt(s_max * 4.0 / math.pi)
    k = _tbfunx(fineness, _K2K1_FINENESS, _K2K1_VALUES, 2, 1)[0]
    cl_alpha = 2.0 * k * s0 / (DEG_PER_RAD * s_ref)
    return BodyLiftSlope(cl_alpha, k, fineness, x0, s0, x1)


# --------------------------------------------------------------------------- #
# DATCOM 5.2.1.1 -- wing-body side force
# --------------------------------------------------------------------------- #
def wing_height_factor(z_w: float, d_body: float) -> float:
    """``K_i`` of figure 5.2.1.1-7 in DATCOM's closed form (``datcom.f:29028-29033``).

    ``z_w`` is the distance from the body centreline to the wing root
    quarter-chord, **positive for a wing below the centreline**; ``d_body`` the
    body depth at the wing. Mid-wing (``z_w = 0``) gives 1.
    """
    if d_body <= 0.0:
        return 1.0
    arg = 2.0 * z_w / d_body
    return 1.0 + 0.49 * arg if arg >= 0.0 else 1.0 - 0.85 * arg


def side_force_derivative(cl_alpha_body: float, k_i: float,
                          dihedral_deg: float) -> float:
    """``Cy_beta,WB = -K_i CL_alpha,B - 0.0001 |Gamma|`` per degree
    (DATCOM 5.2.1.1; ``datcom.f:29034``). Negative: at ``+beta`` the force is to port."""
    return -k_i * cl_alpha_body - _DIHEDRAL_CY_PER_DEG * abs(dihedral_deg)


# --------------------------------------------------------------------------- #
# DATCOM 5.2.3.1 -- wing-body yawing moment
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class YawDerivative:
    """``Cn_beta,WB`` (DATCOM sign) and the intermediates of ``SUBLAT``."""
    cn_beta_datcom: float    # per degree; negative = destabilizing (DATCOM sign)
    k_n: float
    k_rl: float
    s_bs: float              # projected side area
    l_b: float
    h_quarter: float         # body depth at 0.25 l_B
    h_three_quarter: float   # ... at 0.75 l_B
    h_max: float
    w_max: float
    reynolds: float          # on l_B


def body_side_area(body: DatcomBody) -> float:
    """``S_BS``: trapezoidal integral of the body depth along the length."""
    return _trapz(body.heights(), body.x)


def side_area_centroid(body: DatcomBody) -> float:
    """Station (from the nose) of the centroid of the projected side area --
    the trapezoid's first moment over its area. Where ``balance`` applies the
    lumped side force (decision L-7.5)."""
    x, h = body.x, body.heights()
    area = _trapz(h, x)
    if area <= 0.0:
        return 0.5 * body.length
    moment = 0.0
    for i in range(len(x) - 1):
        dx = x[i + 1] - x[i]
        h0, h1 = h[i], h[i + 1]
        # centroid of a trapezoid panel, exact
        moment += dx * (h0 * (x[i] + dx / 3.0) + h1 * (x[i] + 2.0 * dx / 3.0)) / 2.0
    return moment / area


def k_rl(reynolds_on_length: float) -> float:
    """Figure 5.2.3.1-9 in closed form: ``1 + ln(Re 1e-6) / 4.86``."""
    if reynolds_on_length <= 0.0:
        raise ValueError("Reynolds number must be positive")
    return 1.0 + math.log(1e-6 * reynolds_on_length) / _KRL_LOG_DIVISOR


def k_n(l2_over_sbs: float, xcg_over_l: float, sqrt_h1_h2: float,
        hmax_over_wmax: float) -> float:
    """``K_N`` through the three chained charts of figure 5.2.3.1-8, with the
    Fortran's own look-up flags (``datcom.f:29044-29049``)."""
    a = _tlinex(_KN_A_X1, _KN_A_X2, _KN_A_Y, l2_over_sbs, xcg_over_l, 2, 1, 2, 1)
    b = _tlinex(_KN_B_X1, _KN_B_X2, _KN_B_Y, sqrt_h1_h2, a, 2, 0, 2, 1)
    return _tlinex(_KN_C_X1, _KN_C_X2, _KN_C_Y, hmax_over_wmax, b, 2, 0, 2, 1)


def yaw_derivative(body: DatcomBody, x_ref: float, s_ref: float, b_ref: float,
                   reynolds_per_length: float) -> YawDerivative:
    """DATCOM 5.2.3.1 wing-body ``Cn_beta`` per degree about ``x_ref`` (from the
    nose), subroutine ``SUBLAT`` (``datcom.f:29038-29052``)."""
    x = body.x
    l_b = x[-1]
    heights = body.heights()
    s_bs = _trapz(heights, x)
    h1 = _tbfunx(0.25 * l_b, x, heights, 0, 0)[0]
    h2 = _tbfunx(0.75 * l_b, x, heights, 0, 0)[0]
    _, h_max = _getmax(x, heights)
    _, r_max = _getmax(x, body.r)
    w_max = 2.0 * r_max
    re = reynolds_per_length * l_b
    krl = k_rl(re)
    kn = k_n(l_b ** 2 / s_bs, x_ref / l_b, math.sqrt(h1 / h2), h_max / w_max)
    cn = -kn * krl * s_bs * l_b / (s_ref * b_ref)
    return YawDerivative(cn, kn, krl, s_bs, l_b, h1, h2, h_max, w_max, re)


# --------------------------------------------------------------------------- #
# The suite adaptor
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LateralBodyAeroEstimate:
    """The lumped wing-body derivatives for one flight condition, per degree.

    ``cy_beta`` and ``cn_beta`` are in the **suite's** sign convention
    (``CONVENTIONS.md`` §1: ``+fy`` starboard, ``+mz`` nose to port), so
    ``cn_beta > 0`` is destabilizing; ``cn_beta_datcom`` is DATCOM's sign for
    traceability to the printed oracle. ``cn_beta`` is about ``x_ref``.
    ``x_force`` is the fuselage station (in, airplane axes) the side force is
    applied at -- the body side-area centroid.
    """
    cy_beta: float
    cn_beta: float
    cn_beta_datcom: float
    x_ref: float
    x_force: float
    cl_alpha_body: float
    k_i: float
    z_w: float
    dihedral_deg: float
    cy_beta_body: float      # the -K_i CL_alpha,B share
    cy_beta_dihedral: float  # the -0.0001 |Gamma| share
    k_n: float
    k_rl: float
    s_bs_in2: float
    length_in: float
    reynolds: float


def estimate(outline: Optional[FuselageOutline], wing_area_sqft: float,
             span_in: float, x_ref: float, reynolds_per_ft: float,
             z_w_in: float = 0.0, d_body_in: float = 0.0,
             dihedral_deg: float = 0.0) -> Optional[LateralBodyAeroEstimate]:
    """The suite-facing estimate: derivatives per degree, suite sign, about
    ``x_ref`` (fuselage station, airplane axes -- ``balance`` passes ``xw``).

    ``reynolds_per_ft`` is the Reynolds number per foot at the case's speed and
    altitude (:func:`sloads.atmosphere.reynolds_per_ft`); ``z_w_in`` /
    ``d_body_in`` feed :func:`wing_height_factor` (both zero -> mid-wing,
    ``K_i = 1``). Returns ``None`` when there is no usable body or wing
    reference, exactly as the pitch estimator does.
    """
    body = datcom_body_from_outline(outline) if outline is not None else None
    if body is None or wing_area_sqft <= 0.0 or span_in <= 0.0:
        return None
    if body_side_area(body) <= 0.0 or max(body.s) <= 0.0:
        return None
    x_nose = min(sec.x for sec in outline.sections)  # type: ignore[union-attr]
    s_ref_in2 = wing_area_sqft * IN2_PER_FT2
    lift = body_lift_slope(body, s_ref_in2)
    ki = wing_height_factor(z_w_in, d_body_in)
    cy_body = -ki * lift.cl_alpha
    cy_dih = -_DIHEDRAL_CY_PER_DEG * abs(dihedral_deg)
    yaw = yaw_derivative(body, x_ref - x_nose, s_ref_in2, span_in,
                         reynolds_per_ft / IN_PER_FT)
    return LateralBodyAeroEstimate(
        cy_beta=cy_body + cy_dih,
        cn_beta=-yaw.cn_beta_datcom,
        cn_beta_datcom=yaw.cn_beta_datcom,
        x_ref=x_ref,
        x_force=x_nose + side_area_centroid(body),
        cl_alpha_body=lift.cl_alpha,
        k_i=ki, z_w=z_w_in, dihedral_deg=dihedral_deg,
        cy_beta_body=cy_body, cy_beta_dihedral=cy_dih,
        k_n=yaw.k_n, k_rl=yaw.k_rl, s_bs_in2=yaw.s_bs, length_in=yaw.l_b,
        reynolds=yaw.reynolds,
    )


def transfer_cn_beta(cn_beta_ref: float, cy_beta: float, x_ref: float,
                     x_to: float, span_in: float) -> float:
    """``Cn_beta`` about ``x_to`` from its value about ``x_ref`` (suite sign,
    per degree): the side force at the fixed station carries the difference,
    ``Cn(x_to) = Cn(x_ref) - Cy * (x_to - x_ref) / b`` in the +aft/+starboard/
    +up frame (``mz = (x - x_to) fy``). Decision L-7.9's linear transfer."""
    return cn_beta_ref - cy_beta * (x_to - x_ref) / span_in


__all__: List[str] = [
    "BodyLiftSlope",
    "DatcomBody",
    "LateralBodyAeroEstimate",
    "YawDerivative",
    "body_lift_slope",
    "body_side_area",
    "datcom_body_from_outline",
    "estimate",
    "k_n",
    "k_rl",
    "side_area_centroid",
    "side_force_derivative",
    "transfer_cn_beta",
    "wing_height_factor",
    "yaw_derivative",
]
