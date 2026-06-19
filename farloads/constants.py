"""Physical and regulatory constants used by the engine-mount load calculations.

Values follow ENGLOADS.BAS (Hal C. McMaster, v3.0); per Decision 3
("modernize the math") pi is taken from the standard library rather than the
program's 3.1416 literal. This is the one centralized home for these constants
(g, pi, unit factors), so revisiting that decision is a one-file change.
"""

import math

# Acceleration of gravity used throughout the original program (slug conversion).
G = 32.174  # ft / s^2

# Decision 3 ("modernize the math"): the original ENGLOADS.BAS used the literal
# 3.1416 for pi; we use math.pi instead. This shifts the manual's worked-example
# figures in roughly the 6th significant digit, so the regression tests compare
# with engineering tolerance (±0.1%) rather than exact equality.
PI = math.pi

# Conversion from RPM to radians per second: omega = RPM * 2*pi / 60.
TWO_PI = 2 * PI
RPM_TO_RAD_S = TWO_PI / 60.0

# Horsepower-to-torque constant: TORQUE = HP * 33000 / (2*pi*RPM)  [ft-lb].
HP_TO_TORQUE = 33000.0

# Stall-speed term used for gyroscopic thrust, FAR 23.371(b):
#   VSF = 60 kt * 1.15 * (88/60)  -> 101.2 ft/s
# (60 kt minimum stall, x1.15, converted kt->ft/s; conservative for twins.)
VSF = 60 * 1.15 * 88 / 60  # ft/s

# Gyroscopic angular velocities required by FAR 23.371(b).
YAW_RATE = 2.5   # rad/s
PITCH_RATE = 1.0  # rad/s
GYRO_VERTICAL_LOAD_FACTOR = 2.5  # normal load factor combined with gyro loads

# Turboprop propeller-control-malfunction torque multiplier, FAR 23.361(a)(3).
TURBOPROP_MALFUNCTION_FACTOR = 1.6

# Torque multiplication factor for 23.361(a)(2).
TURBOPROP_TORQUE_FACTOR = 1.25


# --------------------------------------------------------------------------- #
# Mass properties (WTESTIMA / WTONECG)
# --------------------------------------------------------------------------- #
# Per-occupant design weight, WTESTIMA.BAS line 440 (WTSEATS = SEATS * 170).
SEAT_WEIGHT_LB = 170.0

# Inertia unit conversion. WTONECG sums W*d^2 in lb-in^2 and divides by 144*g to
# report slug-ft^2 (WTONECG.BAS lines 830-860, "A = 32.17*144"). Decision 3 keeps
# g = 32.174 here; the ~0.01% shift from the program's 32.17 stays within the
# ±0.1% regression tolerance.
IN2_PER_FT2 = 144
LBIN2_PER_SLUGFT2 = IN2_PER_FT2 * G  # multiply slug-ft^2 -> lb-in^2

# WTESTIMA empty/take-off weight ratio K (WTESTIMA.BAS lines 330-400; UG Table 3.1).
WT_K_BASE = 0.62                 # unpressurized single 4-cycle recip
WT_K_ONE_SEAT = -0.04            # SEATS = 1
WT_K_PRESSURIZED = 0.02          # P$ = "P"
WT_K_MULTI_ENGINE = 0.01         # NOENGS > 1
WT_K_TURBOPROP = -0.05           # ENGTYPE = TP
WT_K_RECIP_2CYCLE = -0.01        # ENGTYPE = RT
WT_K_TURBOCHARGED = 0.01         # ENGTYPE = TC
WT_K_LIQUID_COOLED = 0.01        # ENGTYPE = LC

# Cruise fuel burn coefficient, WTFUEL = WT_FUEL_*_COEFF * HP * HOURS
# (WTESTIMA.BAS lines 410-430). Recip/turbocharged/liquid-cooled and 2-cycle use
# 0.75 * specific-fuel-fraction; turboprop is a single 0.55 factor.
WT_FUEL_COEFF_RECIP = 0.75 * 0.5   # RF / TC / LC
WT_FUEL_COEFF_2CYCLE = 0.75 * 0.7  # RT
WT_FUEL_COEFF_TURBOPROP = 0.55     # TP

# Structure component weights as a fraction of take-off weight
# (WTESTIMA.BAS lines 500-550; UG Table 3.2).
WT_STRUCTURE_FRACTIONS = {
    "Wing": 0.1036,
    "Fuselage": 0.0982,
    "Tail": 0.0234,
    "Nacelle": 0.0146,
    "Landing gear": 0.0571,
    "Controls": 0.015,
}

# Powerplant fractions (of installed-engine weight), WTESTIMA.BAS lines 620-660.
WT_FUEL_SYSTEM_FRACTION = 0.1068
WT_EXHAUST_FRACTION_MULTI = 0.251   # NOENGS >= 2
WT_EXHAUST_FRACTION_SINGLE = 0.147  # NOENGS = 1
WT_ENGINE_OTHER_FRACTION = 0.1757
WT_PROP_COEFF = 0.2515              # WTPROP = NOENGS * 0.2515 * (HP/NOENGS)^1.04
WT_PROP_EXPONENT = 1.04

# Systems fractions of take-off weight, single- vs multi-engine
# (WTESTIMA.BAS lines 680-840). The original prints "misc other system wt" from
# an unset MISC variable on the single-engine path, so it reads 0 there even
# though the total-systems fraction already embeds it -- preserved below.
WT_SYSTEMS_SINGLE = {
    "Instruments & nav equip": 0.0044,
    "Pneumatics": 0.00099,
    "Electrical": 0.0241,
    "Electronics": 0.0,
    "Furnishings & equipment": 0.0441,
    "Environmental & anti-ice": 0.0031,
    "Misc other system wt": 0.0,   # MISC unset on single-engine path (preserved quirk)
}
WT_SYSTEMS_SINGLE_TOTAL_FRACTION = 0.0774
WT_SYSTEMS_MULTI = {
    "Instruments & nav equip": 0.0118,
    "Pneumatics": 0.0,
    "Electrical": 0.0269,
    "Electronics": 0.0024,
    "Furnishings & equipment": 0.0458,
    "Environmental & anti-ice": 0.0118,
    "Misc other system wt": 0.0079,
}
WT_SYSTEMS_MULTI_TOTAL_FRACTION = 0.119


def installed_engine_weight(engine_type: str, hp: float, engines: int) -> float:
    """Installed engine weight (lb) by engine family, WTESTIMA.BAS lines 570-610.

    A per-engine polynomial in HP-per-engine (turboprop is a single linear fit),
    multiplied by the engine count. ``engine_type`` is the two-letter code
    (RF/RT/TC/TP/LC).
    """
    n = max(engines, 1)
    hp_each = hp / n
    if engine_type == "RF":
        return n * (105.8439 + 1.448059 * hp_each + 6.31254e-06 * hp_each ** 2)
    if engine_type == "RT":
        return n * (26.08666 + 0.650924 * hp_each - 4.431183e-03 * hp_each ** 2)
    if engine_type == "TC":
        return n * (155.6418 + 1.4689 * hp_each + 3.37101e-04 * hp_each ** 2)
    if engine_type == "TP":
        return 0.48 * hp * 1.3
    if engine_type == "LC":
        return n * (387.2534 + 1.02973 * hp_each - 4.09947e-04 * hp_each ** 2)
    raise ValueError(f"Unknown engine weight type {engine_type!r} (expected RF/RT/TC/TP/LC)")


# --------------------------------------------------------------------------- #
# Standard atmosphere & design speeds (STRSPEED / MACHLIM)
# --------------------------------------------------------------------------- #
# Tropopause altitude used by the suite (STRSPEED/MACHLIM.BAS): above it the
# speed of sound is constant and the density-ratio law changes.
TROPOPAUSE_FT = 35332.0


def standard_atmosphere(altitude_ft: float):
    """Speed of sound (knots) and density ratio sigma at an altitude.

    Mirrors the STRSPEED/MACHLIM atmosphere (Reference 1 Ch 6):
        T     = 59 - 0.003566*H              (deg F)
        a     = 29.02436*(T+459.4)**0.5      (knots)
        sigma = (1 - 0.000006879*H)**4.258
    Above the tropopause (``H > 35332 ft``) the speed of sound is constant and
    sigma follows the isothermal exponential law.
    """
    h = altitude_ft
    if h <= TROPOPAUSE_FT:
        t = 59.0 - 0.003566 * h
        a = 29.02436 * (t + 459.4) ** 0.5
        sigma = (1.0 - 0.000006879 * h) ** 4.258
    else:
        t = 59.0 - 0.003566 * TROPOPAUSE_FT
        a = 29.02436 * (t + 459.4) ** 0.5  # constant above the tropopause
        sigma = (0.00072725 * math.exp(-0.00004778 * (h - TROPOPAUSE_FT))) / 0.002378
    return a, sigma


def cruise_speed_coefficient(category: str, wing_loading: float) -> float:
    """K in VC(min) = K*(W/S)**0.5, by category (Reference 1 Ch 6).

    K is constant up to W/S = 20 and tapers linearly to 28.6 at W/S = 100.
    Normal and utility share K0 = 33; acrobatic uses K0 = 36.
    """
    k0 = 36.0 if category == "A" else 33.0
    if wing_loading <= 20.0:
        return k0
    return k0 - (k0 - 28.6) / (100.0 - 20.0) * (wing_loading - 20.0)


def dive_ratio_coefficient(category: str, wing_loading: float) -> float:
    """K in VD(min) = K*VC, by category (Reference 1 Ch 6).

    K0 (at W/S <= 20) is 1.40 normal, 1.50 utility, 1.55 acrobatic, tapering to
    1.35 at W/S = 100. (The absolute FAR floor VD >= 1.25*VC also applies and, for
    the worked example, governs.)
    """
    k0 = {"U": 1.50, "A": 1.55}.get(category, 1.40)
    if wing_loading <= 20.0:
        return k0
    return k0 - (k0 - 1.35) / (100.0 - 20.0) * (wing_loading - 20.0)


def reciprocating_torque_factor(cylinders: int) -> float:
    """Torque factor for a reciprocating engine, by cylinder count.

    Mirrors lines 320-328 of ENGLOADS.BAS: a four-stroke engine fires fewer
    times per revolution with fewer cylinders, so the peak-to-mean torque ratio
    (and hence the design factor) rises as cylinders drop.
    """
    if cylinders >= 5:
        return 1.33
    if cylinders == 4:
        return 2.0
    if cylinders == 3:
        return 3.0
    if cylinders == 2:
        return 4.0
    raise ValueError("Reciprocating engines must have at least 2 cylinders")
