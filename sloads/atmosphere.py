"""Air viscosity and Reynolds number on the suite's standard atmosphere (L-7.13).

The suite's atmosphere -- temperature law, speed of sound and density ratio --
is owned by :mod:`sloads.constants` (``standard_temperature_f``,
``standard_atmosphere``, ``RHO_SL``); this module adds the one property those
do not carry, the air's **dynamic viscosity**, and the Reynolds number built
from it. It exists because DATCOM's wing-body yawing-moment method
(``sloads.lateral_body_aero``, figure 5.2.3.1-9 ``K_Rl``) is a function of the
Reynolds number on the body length, evaluated on **true** airspeed and the
**local** viscosity -- design note 19, decision **L-7.13** -- rather than the
sea-level/EAS shortcut, which is a few per cent off at 20,000 ft.

Sutherland's law in Imperial units::

    mu = 2.27e-8 * T**1.5 / (T + 198.6)      slug/(ft*s),  T in deg R

which gives ``3.737e-7 slug/(ft*s)`` at the 518.67 R standard day -- the
textbook sea-level value (Anderson, *Fundamentals of Aerodynamics*, App. E;
White, *Viscous Fluid Flow*, Table 1-2). Rankine is Fahrenheit + 459.67 exactly;
the ``+459.4`` inside ``standard_atmosphere``'s speed-of-sound line is the
.BAS programs' own rounding and is left where it is (it is oracle-locked).

Everything here is pure and Imperial-internal, like the rest of the package.
"""

from __future__ import annotations

from .constants import KT_TO_FPS, RHO_SL, standard_atmosphere, standard_temperature_f

#: Sutherland constant, deg R (198.6 R = 110.4 K).
SUTHERLAND_S_R = 198.6
#: Sutherland pre-factor for slug/(ft*s) with T in deg R.
SUTHERLAND_C = 2.27e-8
#: deg R = deg F + this (exact).
RANKINE_OFFSET_F = 459.67


def standard_temperature_r(altitude_ft: float) -> float:
    """Standard-day air temperature in deg R at ``altitude_ft``."""
    return standard_temperature_f(altitude_ft) + RANKINE_OFFSET_F


def dynamic_viscosity(temperature_r: float) -> float:
    """Sutherland dynamic viscosity, slug/(ft*s), for a temperature in deg R."""
    if temperature_r <= 0.0:
        raise ValueError("temperature must be positive (deg R)")
    return SUTHERLAND_C * temperature_r ** 1.5 / (temperature_r + SUTHERLAND_S_R)


def air_density(altitude_ft: float) -> float:
    """Standard-day air density, slug/ft^3: ``RHO_SL * sigma(altitude)``."""
    return RHO_SL * standard_atmosphere(altitude_ft)[1]


def true_airspeed_fps(v_eas_kt: float, altitude_ft: float) -> float:
    """True airspeed (ft/s) of an equivalent airspeed (kt): ``V_eas / sqrt(sigma)``."""
    sigma = standard_atmosphere(altitude_ft)[1]
    return v_eas_kt * KT_TO_FPS / sigma ** 0.5


def reynolds_per_ft(v_eas_kt: float, altitude_ft: float) -> float:
    """Reynolds number per foot, ``rho * V_tas / mu``, on the standard day.

    Multiply by a length in **feet** for the Reynolds number on that length --
    the same unit-length form Digital DATCOM takes as ``RNNUB``.
    """
    rho = air_density(altitude_ft)
    v = true_airspeed_fps(v_eas_kt, altitude_ft)
    mu = dynamic_viscosity(standard_temperature_r(altitude_ft))
    return rho * v / mu


__all__ = [
    "RANKINE_OFFSET_F",
    "SUTHERLAND_C",
    "SUTHERLAND_S_R",
    "air_density",
    "dynamic_viscosity",
    "reynolds_per_ft",
    "standard_temperature_r",
    "true_airspeed_fps",
]
