"""Shared vertical-tail aerodynamic helpers (rational v-tail loads).

These three pure functions are the common aero terms used by both SELECT's static
critical v-tail loads (FAR 23.441/23.443) and ONENGOUT's one-engine-out transient
(FAR 23.367). They were originally private to ``select.py``; lifted here so the two
modules share a single source of truth (SELECT.BAS subroutines 8300 / 10000, the
same chart fits the elevator and rudder use).
"""

from __future__ import annotations

import math


def vtail_lift_slope(aspect_ratio: float) -> float:
    """Vertical-tail lift-curve slope AVT = 2*pi/(1 + 2/ARVT) (per radian)."""
    return 2.0 * math.pi / (1.0 + 2.0 / aspect_ratio)


def rudder_effectiveness(area_ratio: float) -> float:
    """Rudder effectiveness EFFECTV, a cubic in the rudder/tail area ratio SR/SV
    (SELECT.BAS / ONENGOUT.BAS) -- the dalpha/ddelta chart fit (small deflections)."""
    r = area_ratio
    return 0.014844 + 2.7358 * r - 4.4679 * r ** 2 + 3.0306 * r ** 3


def large_deflection_factor(defl: float, area_ratio: float) -> float:
    """Large-deflection effectiveness factor EF(deflection, control/surface area
    ratio) -- SELECT.BAS subroutine 10000 (Dommasch fig 12:3). The four polynomials
    give EF at area ratios 0.15/0.2/0.3/0.4 (EF=1 at 0); interpolate by ``area_ratio``.
    """
    ef00 = 1.0
    ef15 = 1.008576 - 5.770396e-3 * defl - 3.452382e-4 * defl ** 2 + 7.1777799e-6 * defl ** 3
    ef20 = 1.003143 - 1.521429e-3 * defl - 2.757143e-4 * defl ** 2
    ef30 = 0.991602 - 3.329421e-2 * defl + 0.001373 * defl ** 2 - 2.595556e-5 * defl ** 3
    ef40 = 1.010976 - 2.866663e-3 * defl - 1.110476e-3 * defl ** 2 + 2.266667e-5 * defl ** 3
    s = area_ratio
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
