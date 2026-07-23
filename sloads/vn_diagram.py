"""V-n (velocity-load factor) diagram geometry -- a pure, unit-testable builder.

Turns the STRSPEED design speeds + limit maneuver load factors (and optional gust
inputs) into the plottable polylines of a FAR 23.333 V-n diagram, so the Streamlit
view does no math of its own:

- the **curved** stall boundary ``n = (V/VS)**2`` sampled from the 1 g stall speed
  up to the manoeuvre corner (VA) -- not the straight line a corner-to-corner plot
  would draw;
- the closed positive/negative **manoeuvre envelope** (flaps up), and the
  flaps-down envelope capped at ``n = 2.0`` per 14 CFR 23.337(b);
- the **gust lines** at VC and VD (14 CFR 23.333(c)/23.341), drawn as connected
  lines through ``(0, 1)``.

This is a *presentation* helper: it does not change any oracle-locked calc. The
gust factor here is the classic Pratt form (``Δn = Kg·Ude·Ve·a / (498·W/S)``) used
by FLTLOADS, minus that program's Mach/Glauert correction -- a Structural-Speeds
sanity plot, explicitly captioned as approximate. The rigorous Mach-corrected gust
V-n lives on the Flight Envelope page (FLTLOADS, ``modules/flight_envelope.py``).

References: 14 CFR 23.333 (flight envelope), 23.335 (design speeds), 23.337 (limit
manoeuvre load factors), 23.341 (gust loads); Reference 1 Ch 6 (STRSPEED) and the
FLTLOADS gust subroutine (Ch 8).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .constants import standard_atmosphere

# Classic gust-formula constants (FLTLOADS gust subroutine): degrees-per-radian to
# turn a per-degree lift-curve slope into per-radian, sea-level density, and g.
_DEG_PER_RAD = 57.2957795
_RHO0 = 0.002378          # slug/ft^3, sea-level standard density
_G = 32.2                 # ft/s^2
_DEFAULT_LIFT_SLOPE_PER_DEG = 0.1   # textbook wing CL_alpha when no aero slice

_STALL_SAMPLES = 40       # points sampled along each curved stall boundary


@dataclass(frozen=True)
class VnTrace:
    """One named polyline of a V-n diagram: equal-length speed / load-factor lists."""
    name: str
    v: List[float]   # KEAS
    n: List[float]   # load factor (dimensionless)


@dataclass(frozen=True)
class GustInputs:
    """Resolved inputs for the gust lines (see :func:`resolve_gust_inputs`).

    ``lift_slope_per_deg`` is the wing lift-curve slope; ``mac_ft`` the wing MAC in
    feet (drives the gust-alleviation factor Kg); ``approximate`` is True when a
    default slope/MAC was substituted because the aero/geometry slices were absent.
    """
    ws: float
    altitude_ft: float
    lift_slope_per_deg: float
    mac_ft: float
    approximate: bool = False


@dataclass(frozen=True)
class VnDiagram:
    """The assembled V-n diagram: manoeuvre / stall / gust traces + flags."""
    traces: List[VnTrace] = field(default_factory=list)
    gust_approximate: bool = False


def _gust_ude(ref: str, altitude_ft: float) -> float:
    """Derived gust velocity Ude (fps): 50 @ VC, 25 @ VD, tapering above 20,000 ft.

    14 CFR 23.333(c) / 23.341; identical taper to FLTLOADS ``_gust_ude``.
    """
    h = altitude_ft
    if ref == "D":
        return 25.0 if h <= 20000.0 else max(0.0, 25.0 - (12.5 / 30000.0) * (h - 20000.0))
    return 50.0 if h <= 20000.0 else max(0.0, 50.0 - (25.0 / 30000.0) * (h - 20000.0))  # VC


def gust_load_factor(v_keas: float, ref: str, gust: GustInputs, sign: float = 1.0) -> float:
    """Gust normal load factor at equivalent airspeed ``v_keas`` (14 CFR 23.341).

    ``sign`` is +1 for the up-gust line, -1 for the down-gust line. The Pratt form
    ``n = 1 + sign·Kg·Ude·Ve·a / (498·W/S)`` with ``a`` the per-radian lift-curve
    slope; the 498 constant embeds the KEAS/fps unit conversion. When the MAC is
    unknown Kg falls back to 1.0 (no alleviation) -- flagged ``approximate``.
    """
    _a_sound, sigma = standard_atmosphere(gust.altitude_ft)
    rho = _RHO0 * sigma
    a_rad = gust.lift_slope_per_deg * _DEG_PER_RAD
    if gust.mac_ft > 0.0 and a_rad > 0.0:
        mu = 2.0 * gust.ws / (rho * gust.mac_ft * a_rad * _G)
        kg = 0.88 * mu / (5.3 + mu)
    else:
        kg = 1.0
    ude = _gust_ude(ref, gust.altitude_ft)
    return 1.0 + sign * kg * ude * v_keas * a_rad / (498.0 * gust.ws)


def _stall_curve(vs: float, v_end: float, n_sign: float,
                 n_cap: Optional[float] = None) -> Tuple[List[float], List[float]]:
    """Sample the parabolic stall boundary ``n = n_sign·(V/VS)**2`` from VS to v_end.

    ``n_cap`` (magnitude) clamps the load factor so a flaps-down curve stops at the
    2.0 corner even if v_end is the flap speed beyond it. Returns (V list, n list).
    """
    if vs <= 0.0 or v_end <= vs:
        return [], []
    vs_list, n_list = [], []
    for i in range(_STALL_SAMPLES + 1):
        v = vs + (v_end - vs) * i / _STALL_SAMPLES
        n = n_sign * (v / vs) ** 2
        if n_cap is not None and abs(n) > n_cap:
            n = math.copysign(n_cap, n_sign)
        vs_list.append(v)
        n_list.append(n)
    return vs_list, n_list


def _clean_envelope(vs: float, va: float, vc: float, vd: float,
                    n_pos: float, n_neg: float) -> VnTrace:
    """The closed flaps-up manoeuvre envelope polyline (14 CFR 23.333(b))."""
    v, n = [], []
    # Positive stall boundary VS -> VA (curved), then flat top to VD, down the dive
    # edge to n=0, back along the negative ramp/flat and negative stall to VS.
    sv, sn = _stall_curve(vs, va, 1.0, n_cap=abs(n_pos))
    v += sv or [vs, va]
    n += sn or [1.0, n_pos]
    v += [vd, vd]
    n += [n_pos, 0.0]
    # Negative side: 0 at VD -> n_neg at VC (ramp) -> n_neg held to the negative
    # corner -> negative stall curve back to VS.
    v_neg_corner = vs * math.sqrt(abs(n_neg)) if n_neg else vs
    v += [vc, v_neg_corner]
    n += [n_neg, n_neg]
    nv, nn = _stall_curve(vs, v_neg_corner, -1.0, n_cap=abs(n_neg))
    v += list(reversed(nv)) or [v_neg_corner, vs]
    n += list(reversed(nn)) or [n_neg, -1.0]
    # Close the loop along the low-speed (VS) edge.
    v.append(vs)
    n.append(1.0)
    return VnTrace("Manoeuvre (flaps up)", v, n)


def _flap_envelope(vsf: float, vf: float) -> Optional[VnTrace]:
    """The flaps-down manoeuvre envelope, positive only, capped at n = 2.0."""
    if vsf <= 0.0 or vf <= vsf:
        return None
    n_cap = 2.0
    v_corner = min(vsf * math.sqrt(n_cap), vf)   # where the stall curve reaches n=2
    sv, sn = _stall_curve(vsf, v_corner, 1.0, n_cap)
    # Flat top at the 2.0 cap from the stall corner to VF; if VF is reached before
    # the curve hits 2.0, the top is just the (lower) stall value at VF.
    top = min(n_cap, (vf / vsf) ** 2)
    v = [vsf] + (sv or [vsf, v_corner]) + [vf, vf, vsf]
    n = [0.0] + (sn or [1.0, top]) + [top, 0.0, 0.0]
    return VnTrace("Manoeuvre (flaps down)", v, n)


def resolve_gust_inputs(ws: float, altitude_ft: float,
                        lift_slope_per_deg: Optional[float],
                        mac_ft: Optional[float]) -> GustInputs:
    """Resolve gust inputs from what the caller could read off the project.

    A missing lift-curve slope falls back to a textbook value and a missing MAC
    drops the gust-alleviation factor to 1.0; either substitution sets
    ``approximate`` so the view can caption the gust lines accordingly.
    """
    approximate = False
    if not lift_slope_per_deg or lift_slope_per_deg <= 0.0:
        lift_slope_per_deg = _DEFAULT_LIFT_SLOPE_PER_DEG
        approximate = True
    if not mac_ft or mac_ft <= 0.0:
        mac_ft = 0.0
        approximate = True
    return GustInputs(ws=ws, altitude_ft=altitude_ft,
                      lift_slope_per_deg=lift_slope_per_deg, mac_ft=mac_ft,
                      approximate=approximate)


def build_vn_diagram(*, vs: float, va: float, vc: float, vd: float,
                     n_pos: float, n_neg: float,
                     vsf: float = 0.0, vf: float = 0.0,
                     flaps: str = "up",
                     gust: Optional[GustInputs] = None) -> VnDiagram:
    """Build the V-n diagram traces.

    ``flaps`` selects which manoeuvre envelope(s) to include: ``"up"`` (clean only),
    ``"down"`` (flaps-down box only) or ``"both"``. ``gust`` (optional) adds the
    up/down gust lines at VC and VD. All speeds are KEAS; ``n_neg`` is negative.
    """
    traces: List[VnTrace] = []
    if flaps in ("up", "both"):
        traces.append(_clean_envelope(vs, va, vc, vd, n_pos, n_neg))
    if flaps in ("down", "both"):
        flap = _flap_envelope(vsf, vf)
        if flap is not None:
            traces.append(flap)

    gust_approx = False
    if gust is not None:
        gust_approx = gust.approximate
        for ref, speed in (("C", vc), ("D", vd)):
            if speed <= 0.0:
                continue
            for sign, tag in ((1.0, "up"), (-1.0, "down")):
                n_end = gust_load_factor(speed, ref, gust, sign)
                traces.append(VnTrace(f"Gust {tag} @ V{ref} ({ref})", [0.0, speed], [1.0, n_end]))
    return VnDiagram(traces=traces, gust_approximate=gust_approx)
