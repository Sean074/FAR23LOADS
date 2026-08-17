"""Munk slender-body fuselage pitching-moment estimator (Step G4).

A pure, geometry-only helper that derives the fuselage's contribution to the
airplane-less-tail pitching-moment slope ``dCm/dalpha`` from the G1 fuselage
outline (:class:`~sloads.models.FuselageOutline`), so a concept configuration
built up from a planform no longer has to hand-fold the fuselage into the
FLTLOADS input coefficients.

Method -- Munk slender-body (potential-flow apparent-mass) moment. A body of
revolution at a small angle of attack ``alpha`` develops an unstable (nose-up)
free moment whose magnitude is

    M_fus = (k2 - k1) * q * Vol * alpha            (alpha in radians)

where ``Vol`` is the body volume and ``(k2 - k1)`` is Munk's apparent-mass
correction factor, a function of the body fineness ratio ``l/d`` (Munk's inertia
coefficients for a prolate spheroid; the classic table below). Non-dimensionalized
on the wing reference ``S * mac`` this is a pure slope increment, zero at
``alpha = 0`` for an uncambered body:

    dCm/dalpha (per rad) = (k2 - k1) * Vol / (S * mac)

The cross-section area at each station is taken as an ellipse of the section
width and height, ``A = pi/4 * width * height`` (the reading G1 committed to in
:class:`~sloads.models.FuselageSection`); ``Vol`` is the trapezoidal integral
of ``A`` along the body and the fineness ratio uses the equivalent diameter
``d_eq = sqrt(width*height)`` at the widest station. The result is reference-point
independent (it depends on volume, not on the moment reference), so no CG station
is required.

Sign: the increment is positive -- destabilizing, adding to the airplane-less-tail
``M1`` (dCm/dalpha), which is itself positive for the tail-off airplane.

References:
- Munk, M. M., "The Aerodynamic Forces on Airship Hulls," NACA TR-184 (1924).
- USAF Stability & Control DATCOM 4.2.1.1 (fuselage pitching moment); this
  reduces to the Munk result for the slender ideal body.
- ``reference/fuselage_pitching_moment.md`` (bundled derivation + table).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .constants import DEG_PER_RAD, IN2_PER_FT2
from .models import FuselageOutline

# Munk apparent-mass factor (k2 - k1) versus body fineness ratio l/d, for a
# prolate spheroid (NACA TR-184 / DATCOM 4.2.1.1). Linearly interpolated;
# clamped to the table ends (l/d <= 1 -> 0, sphere; l/d -> inf -> 1).
_K_TABLE: Tuple[Tuple[float, float], ...] = (
    (1.0, 0.000),
    (1.5, 0.305),
    (2.0, 0.485),
    (2.5, 0.607),
    (3.0, 0.681),
    (4.0, 0.787),
    (5.0, 0.850),
    (6.0, 0.887),
    (7.0, 0.911),
    (8.0, 0.930),
    (10.0, 0.947),
    (14.0, 0.972),
    (18.0, 0.985),
)



def munk_k2_minus_k1(fineness_ratio: float) -> float:
    """Munk apparent-mass factor ``(k2 - k1)`` for a body fineness ratio ``l/d``.

    Linear interpolation of the prolate-spheroid table, clamped to its ends.
    """
    lo = _K_TABLE[0]
    hi = _K_TABLE[-1]
    if fineness_ratio <= lo[0]:
        return lo[1]
    if fineness_ratio >= hi[0]:
        return hi[1]
    for (x0, y0), (x1, y1) in zip(_K_TABLE, _K_TABLE[1:]):
        if x0 <= fineness_ratio <= x1:
            t = (fineness_ratio - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return hi[1]  # unreachable; keeps type-checkers happy


def _section_area(width: float, height: float) -> float:
    """Ellipse cross-section area ``pi/4 * width * height`` (in^2)."""
    return math.pi / 4.0 * width * height


@dataclass
class FuselageMomentEstimate:
    """The estimator's output plus the intermediates worth surfacing.

    ``d_cm_dalpha`` is the slope increment **per degree** (matching the FLTLOADS
    moment polynomial's ``M1`` convention); the rest are display/traceability
    values. All lengths inches, ``volume_in3`` cubic inches.
    """
    d_cm_dalpha: float          # per degree
    volume_in3: float
    length_in: float
    max_equiv_diameter_in: float
    fineness_ratio: float
    k2_minus_k1: float


def fuselage_volume_in3(outline: FuselageOutline) -> float:
    """Body volume (in^3): trapezoidal integral of the ellipse section area."""
    secs = sorted(outline.sections, key=lambda s: s.x)
    vol = 0.0
    for a, b in zip(secs, secs[1:]):
        aa = _section_area(a.width, a.height)
        ab = _section_area(b.width, b.height)
        vol += 0.5 * (aa + ab) * (b.x - a.x)
    return vol


def estimate(
    outline: Optional[FuselageOutline],
    wing_area_sqft: float,
    mac_in: float,
) -> Optional[FuselageMomentEstimate]:
    """Estimate the fuselage ``dCm/dalpha`` increment (per degree).

    Returns ``None`` when the geometry is insufficient (fewer than two stations,
    or a non-positive wing reference ``S`` / ``mac``) so callers can show a
    "define the outline first" message rather than a bogus number.
    """
    if outline is None:
        return None
    secs: List = sorted(outline.sections, key=lambda s: s.x)
    if len(secs) < 2 or wing_area_sqft <= 0.0 or mac_in <= 0.0:
        return None

    length = secs[-1].x - secs[0].x
    d_max = max(math.sqrt(s.width * s.height) for s in secs)
    if length <= 0.0 or d_max <= 0.0:
        return None

    fineness = length / d_max
    k = munk_k2_minus_k1(fineness)
    vol = fuselage_volume_in3(outline)
    s_in2 = wing_area_sqft * IN2_PER_FT2

    dcm_dalpha_per_rad = k * vol / (s_in2 * mac_in)
    dcm_dalpha_per_deg = dcm_dalpha_per_rad / DEG_PER_RAD
    return FuselageMomentEstimate(
        d_cm_dalpha=dcm_dalpha_per_deg,
        volume_in3=vol,
        length_in=length,
        max_equiv_diameter_in=d_max,
        fineness_ratio=fineness,
        k2_minus_k1=k,
    )
