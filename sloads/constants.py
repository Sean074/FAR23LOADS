"""Physical constants, FAR-mandated numbers and every suite-internal unit factor.

**The one owner** (CONVENTIONS.md §7, review 2026-08-17 constants-and-conversions):
physical constants (``G``, ``RHO_SL``, the atmosphere), FAR-mandated numbers
(``ULTIMATE_FACTOR``, the 23.341 gust constants, the 23.371 gyro rates) and every
**Imperial<->Imperial** factor (``IN_PER_FT``, ``IN2_PER_FT2``, ``DEG_PER_RAD``,
``KT_TO_FPS``, ``FT_LB_S_PER_HP``) live here and nowhere else; the Imperial<->SI
boundary lives in :mod:`sloads.units` (which imports this module, never the
reverse). ``tests/test_constants.py`` grep-guards both directions.

**Value policy: exact by default.** Where a ``.BAS`` program truncated a value
(3.1416, 57.3, 32.2, 295, 1.15*88/60) the exact value is used; a truncated value
survives only as a named ``*_SUITE`` twin beside its exact owner, with the printed
oracle that requires it cited (register: ``docs/20_theory/02_approved_corrections.md``).
The manual's figures are tolerance oracles (+-0.1 %), which every such move was
measured against before it was made.
"""

import math

# --------------------------------------------------------------------------- #
# Physical constants
# --------------------------------------------------------------------------- #
# Acceleration of gravity, ft/s^2 -- the value the ported calc uses everywhere
# (SELECT/BALLOADS/FLTLOADS/VNDIAG wrote 32.2, WTONECG 32.17; measured effect of
# reading this one owner instead: <= 0.081 %, no printed oracle moves; register
# 2026-08-17). ``units.G_MM_S2`` is the ISO standard gravity of the *deck* channel
# and is deliberately a separate, exact value (see the note there).
G = 32.174  # ft / s^2

# --------------------------------------------------------------------------- #
# Suite-internal (Imperial <-> Imperial) unit factors
# --------------------------------------------------------------------------- #
IN_PER_FT = 12.0
IN2_PER_FT2 = IN_PER_FT ** 2                     # 144
DEG_PER_RAD = 180.0 / math.pi                    # 57.29578 (the .BAS wrote 57.3)
RAD_PER_DEG = math.pi / 180.0
FT_LB_S_PER_HP = 550.0                           # 1 hp = 550 ft-lb/s (exact, by definition)
# International nautical mile in feet: 1852 m / 0.3048 m/ft exactly. The SI
# origin is *stated* here (and asserted against units.FT_TO_M in the guard test),
# not imported, so units.py stays downstream of this module.
FT_PER_NMI = 6076.115485564304
KT_TO_FPS = FT_PER_NMI / 3600.0                  # 1.687810 ft/s per knot (exact)
# ... as the suite computed it, via mph: kt * 1.15 * 88/60 = 1.68667 (-0.066 %).
# Survives ONLY for VSF below: the ENGLOADS gyro-thrust oracle prints THRUST =
# T*omega/101.2 (Ref 1 Appendix A; tests/test_engine.py::test_gyro_thrust_matches_manual,
# abs_tol 1 lb, which the exact value exceeds). FLAPLOAD's p201 and ONENGOUT read
# the exact factor (measured: their oracles hold).
KT_TO_FPS_SUITE = 1.15 * 88.0 / 60.0

# Factor of safety used to turn the calc's LIMIT loads into the ULTIMATE loads the
# rendered output / structural-sizing export reports (14 CFR 23.303 / 25.303: ultimate =
# 1.5 x limit unless otherwise specified). This is the DEFAULT for the per-case
# ConditionResult.safety_factor; it is applied only at the render/export boundary
# so the calc stays oracle-locked to McMaster's printed LIMIT figures. A future
# 14 CFR 25.302 / Appendix K refinement may give a failure case a probability-
# interpolated factor (1.0-1.5); sudden engine stoppage is held at 1.5 for now.
ULTIMATE_FACTOR = 1.5

# pi: Decision 3 ("modernize the math") -- the .BAS programs wrote 3.1416; the
# package uses ``math.pi`` directly everywhere (no ``PI`` alias to drift; the
# guard test forbids the literal). This shifts the manual's worked-example
# figures in roughly the 6th significant digit, so the regression tests compare
# with engineering tolerance (±0.1%) rather than exact equality.

# Conversion from RPM to radians per second: omega = RPM * 2*pi / 60.
RPM_TO_RAD_S = 2.0 * math.pi / 60.0

# Horsepower-to-torque constant: TORQUE = HP * 33000 / (2*pi*RPM)  [ft-lb],
# 33000 = 550 ft-lb/s per hp * 60 s/min.
HP_TO_TORQUE = 60.0 * FT_LB_S_PER_HP

# Stall-speed term used for gyroscopic thrust, FAR 23.371(b):
#   VSF = 60 kt * 1.15 * (88/60)  -> 101.2 ft/s
# (60 kt minimum stall, x1.15, converted kt->ft/s; conservative for twins.)
# Reads the *suite* kt->ft/s on purpose: the printed oracle divides by 101.2.
VSF = 60 * KT_TO_FPS_SUITE  # ft/s

# Gyroscopic angular velocities required by FAR 23.371(b).
YAW_RATE = 2.5   # rad/s
PITCH_RATE = 1.0  # rad/s
GYRO_VERTICAL_LOAD_FACTOR = 2.5  # normal load factor combined with gyro loads

# Turboprop propeller-control-malfunction torque multiplier, FAR 23.361(a)(3).
TURBOPROP_MALFUNCTION_FACTOR = 1.6

# Torque multiplication factor for 23.361(a)(2).
TURBOPROP_TORQUE_FACTOR = 1.25

# The angle-of-attack window (deg, body ``alpha`` of the trim point) over which
# the entered airplane-less-tail polar ``CD(CL)`` and the wing strip model are
# both trusted, so that their difference -- the ``body-axial`` non-wing drag the
# balanced model carries -- is a physical load (design note 20 D-4 as revised
# 2026-08-17, backlog Pri 2). **One-sided on purpose.** The polar is a fit over
# the positive-lift range: above the upper bound the strip model's induced drag
# overshoots it (``concept_regional_jet``, alpha >= 19 deg), and below the lower
# bound the fit is being read well below zero lift, where on the three
# crudest-polar fixtures the two drag models cross over (``NMAA`` at -12.9 to
# -14.3 deg) while the Appendix A airplane and ``cessna_210`` are still
# consistent at -8.4 / -8.9 deg. Outside the window a FORWARD non-wing force is
# not applied (its ``dCD`` is still reported); inside it a forward value is a
# fixture-data defect and the G10 gate fails. Single owner: read it, never copy
# it (``tests/test_balance.py`` reads it from here).
POLAR_TRUSTED_ALPHA_DEG = (-10.0, 15.0)

# --------------------------------------------------------------------------- #
# Wing carry-through (Ref 1 Ch 15 p103 fuselage moment closure, M4-1)
# --------------------------------------------------------------------------- #
# Assumed front/rear spar chord fractions when SurfaceInput.front_spar_pct /
# .rear_spar_pct are unset -- a conventional light-aircraft two-spar wing box
# (front spar just aft of the leading-edge radius, rear spar ahead of the
# flap/aileron hinge line). They are an ASSUMPTION, not a derived value:
# derived_geometry.carry_through marks a result that uses them ``assumed`` so
# every deliverable states that the spar stations were not entered.
DEFAULT_FRONT_SPAR_PCT = 0.15
DEFAULT_REAR_SPAR_PCT = 0.65

# The effective loads-reference-axis chord fraction when SurfaceInput.
# ref_axis_pct is unset (v52, note 24 R-7c) -- the original suite's quarter
# chord, so a bare project's reported torsion is bit-identical to the oracle
# reporting. Reporting consumers read it through SurfaceInput.ref_axis; the
# LRA beam-model exporter refuses an unset axis instead of assuming this.
DEFAULT_REF_AXIS_PCT = 0.25

# Point loads the carry-through line load is lumped onto (body_loads). The
# per-segment lumping is the exact static equivalent of a linear load, so the
# closure holds at any count >= 2; this only sets how finely the reaction is
# resolved along the carry-through for the beam model.
CARRY_THROUGH_NODES = 5


# --------------------------------------------------------------------------- #
# Mass properties (WTESTIMA / WTONECG)
# --------------------------------------------------------------------------- #
# Per-occupant design weight, WTESTIMA.BAS line 440 (WTSEATS = SEATS * 170).
SEAT_WEIGHT_LB = 170.0

# --------------------------------------------------------------------------- #
# FAR 23 applicability limits (14 CFR 23.1, pre-Amendment 23-64 applicability)
# --------------------------------------------------------------------------- #
# The certificated band the FAR23 replication is calibrated to. Non-commuter
# (Normal / Utility / Acrobatic): <= 12,500 lb max takeoff weight and <= 9
# passenger seats. Commuter: <= 19,000 lb and <= 19 passenger seats. The required
# flight crew are excluded from the passenger-seat count -- the crew count is a
# user input (WeightEstimationInput.crew); DEFAULT_FLIGHT_CREW is the fallback the
# applicability check assumes when no weight-estimation slice is present. Exceeding
# these limits does not block the tool -- it flags the airplane as a concept-mode
# extrapolation (see sloads/applicability.py). The commuter tier is encoded but
# dormant: no distinct Commuter category exists yet (the merged "Normal / commuter"
# category maps to "N"), so the check uses the non-commuter tier until a distinct
# Commuter category lands (backlog "Distinct Commuter category").
FAR23_MAX_WEIGHT_LB = 12500.0
FAR23_COMMUTER_MAX_WEIGHT_LB = 19000.0    # encoded; dormant until a distinct Commuter category exists
FAR23_MAX_PASSENGER_SEATS = 9
FAR23_COMMUTER_MAX_PASSENGER_SEATS = 19   # encoded; dormant (see above)
DEFAULT_FLIGHT_CREW = 1                   # assumed crew when no WeightEstimationInput.crew is set

# Inertia unit conversion. WTONECG sums W*d^2 in lb-in^2 and divides by 144*g to
# report slug-ft^2 (WTONECG.BAS lines 830-860, "A = 32.17*144"). Decision 3 keeps
# g = 32.174 here; the ~0.01% shift from the program's 32.17 stays within the
# ±0.1% regression tolerance.
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

# Sea-level standard air density, slug/ft^3 -- the suite's rho_0 (Reference 1
# Ch 6; every .BAS module quotes 0.002378). The one owner (CH-6): the V-n
# builders, FLTLOADS' atmosphere, FLAPLOAD's power check and ONENGOUT's dynamic
# pressure all read it from here; ``tests/test_constants.py`` guards that the
# literal appears nowhere else in the package.
RHO_SL = 0.002378


def standard_temperature_f(altitude_ft: float) -> float:
    """Standard-day air temperature (deg F) of the suite's atmosphere.

    The one owner of the temperature law ``T = 59 - 0.003566*H`` (Reference 1
    Ch 6, STRSPEED/MACHLIM), isothermal above :data:`TROPOPAUSE_FT`.
    :func:`standard_atmosphere` reads it for the speed of sound and
    :mod:`sloads.atmosphere` for the air viscosity (L-7 decision L-7.13), so
    the lapse rate is written once.
    """
    return 59.0 - 0.003566 * min(altitude_ft, TROPOPAUSE_FT)


def standard_atmosphere(altitude_ft: float) -> "tuple[float, float]":
    """Speed of sound (knots) and density ratio sigma at an altitude.

    Mirrors the STRSPEED/MACHLIM atmosphere (Reference 1 Ch 6):
        T     = 59 - 0.003566*H              (deg F; :func:`standard_temperature_f`)
        a     = 29.02436*(T+459.4)**0.5      (knots)
        sigma = (1 - 0.000006879*H)**4.258
    Above the tropopause (``H > 35332 ft``) the speed of sound is constant and
    sigma follows the isothermal exponential law.
    """
    h = altitude_ft
    t = standard_temperature_f(h)
    a = 29.02436 * (t + 459.4) ** 0.5   # constant above the tropopause (T is)
    if h <= TROPOPAUSE_FT:
        sigma = (1.0 - 0.000006879 * h) ** 4.258
    else:
        sigma = (0.00072725 * math.exp(-0.00004778 * (h - TROPOPAUSE_FT))) / RHO_SL
    return a, sigma


# Speed of sound at sea level for this atmosphere (kt); the reference used to map
# an equivalent airspeed to calibrated airspeed (KEAS == KCAS == KTAS at h = 0).
SEA_LEVEL_SOUND_KT = 29.02436 * (59.0 + 459.4) ** 0.5


def eas_to_mach(eas_kt: float, a: float, sigma: float) -> float:
    """Mach number of an equivalent airspeed: M = TAS/a = KEAS / (a*sqrt(sigma))."""
    return eas_kt / (a * math.sqrt(sigma))


def mach_to_eas(mach: float, a: float, sigma: float) -> float:
    """Equivalent airspeed (kt) of a Mach number at an altitude: KEAS = M*a*sqrt(sigma)."""
    return mach * a * math.sqrt(sigma)


def convert_airspeed(eas_kt: float, altitude_ft: float, unit: str) -> float:
    """Convert an equivalent airspeed (KEAS) to KEAS / KTAS / KCAS at an altitude.

    KTAS = KEAS / sqrt(sigma) (true airspeed). KCAS uses the standard subsonic
    compressible impact-pressure relation::

        M       = KEAS / (a*sqrt(sigma))                 Mach at altitude
        delta   = P/P0 = sigma * (a/a0)**2               static-pressure ratio
        qc/P0   = delta * ((1 + 0.2*M**2)**3.5 - 1)      impact pressure
        KCAS    = a0 * sqrt(5 * ((qc/P0 + 1)**(2/7) - 1))

    with ``a0 = SEA_LEVEL_SOUND_KT``. Exact at sea level (KCAS == KEAS == KTAS) and
    diverging from EAS with Mach and altitude, matching the CAS x-axis of a
    speed–altitude flight-limits diagram. Reference: standard airspeed relations
    (NASA RP-1046 / Aeronautical Vestpocket Handbook), subsonic (M < 1).
    """
    u = unit.upper().lstrip("K")  # accept "KEAS"/"EAS", "KTAS"/"TAS", "KCAS"/"CAS"
    if u == "EAS":
        return eas_kt
    a, sigma = standard_atmosphere(altitude_ft)
    if u == "TAS":
        return eas_kt / math.sqrt(sigma)
    if u == "CAS":
        mach = eas_to_mach(eas_kt, a, sigma)
        delta = sigma * (a / SEA_LEVEL_SOUND_KT) ** 2
        qc_over_p0 = delta * ((1.0 + 0.2 * mach * mach) ** 3.5 - 1.0)
        return SEA_LEVEL_SOUND_KT * math.sqrt(5.0 * ((qc_over_p0 + 1.0) ** (2.0 / 7.0) - 1.0))
    raise ValueError(f"Unknown airspeed unit {unit!r} (expected KEAS/KTAS/KCAS)")


# Dynamic pressure of an equivalent airspeed: q = 1/2 rho_0 V^2 with V in ft/s, so
# Q [lb/ft^2] = V_keas^2 / DYNAMIC_PRESSURE_DIVISOR. The suite wrote the divisor as
# 295 (its FAR-23-era engineering form); the exact value from the two owners above
# is 295.237 (-0.08 % in q, uniformly). Measured 2026-08-17: no printed oracle
# moves; the frozen digest and the SELECT regression pins were re-pinned
# (register). Every q in the package is computed by ``dynamic_pressure_psf``.
DYNAMIC_PRESSURE_DIVISOR = 1.0 / (0.5 * RHO_SL * KT_TO_FPS ** 2)


def dynamic_pressure_psf(v_eas_kt: float) -> float:
    """``q = 1/2 rho_0 V^2`` (lb/ft^2) of an equivalent airspeed in knots.

    The one owner of dynamic pressure (``V^2/295`` in the .BAS listings);
    ``eas_from_dynamic_pressure`` is its inverse.
    """
    return v_eas_kt ** 2 / DYNAMIC_PRESSURE_DIVISOR


def eas_from_dynamic_pressure(q_psf: float) -> float:
    """Equivalent airspeed (kt) at a dynamic pressure (lb/ft^2): ``V = sqrt(295 q)``."""
    return math.sqrt(DYNAMIC_PRESSURE_DIVISOR * q_psf)


# --------------------------------------------------------------------------- #
# FAR 23.341(c) gust load factor: n = 1 +- Kg*Ude*V*a / (498*W/S), Kg = 0.88*mu/(5.3+mu)
# --------------------------------------------------------------------------- #
# Regulatory numbers, printed in the rule -- there is no "exact" value to correct
# them to; they are owned here so the five gust sites (VNDIAG, FLTLOADS, SELECT x3)
# read one copy. 498 embeds the rule's own KEAS->ft/s and 2/rho_0 rounding.
GUST_KG_NUMERATOR = 0.88
GUST_KG_OFFSET = 5.3
GUST_LOAD_FACTOR_DIVISOR = 498.0


def gust_alleviation_factor(mass_ratio: float) -> float:
    """``Kg = 0.88*mu / (5.3 + mu)`` of the airplane (or tail) mass ratio, 23.341(c)."""
    return GUST_KG_NUMERATOR * mass_ratio / (GUST_KG_OFFSET + mass_ratio)


def stall_speed_kt(weight_lb: float, wing_area_sqft: float, clmax: float) -> float:
    """1-g stall speed VS (KEAS) from CLmax and wing loading.

    Solves lift = weight at CLmax with ``q = 1/2 rho_0 V^2`` (the suite's
    ``Q = V^2/295`` convention, exact divisor above; EAS folds in density):
    ``VS = sqrt(DYNAMIC_PRESSURE_DIVISOR*(W/S)/CLmax)``. The optional
    CLmax -> stall-speed input path of the User's Guide (p7-5); ``clmax`` is the
    clean or flaps-down maximum lift coefficient, ``weight_lb`` the design weight.
    """
    if clmax <= 0.0 or wing_area_sqft <= 0.0:
        raise ValueError("stall_speed_kt needs a positive CLmax and wing area")
    return eas_from_dynamic_pressure((weight_lb / wing_area_sqft) / clmax)


def cruise_speed_coefficient(category: str, wing_loading: float) -> float:
    """K in VC(min) = K*(W/S)**0.5, by category (Reference 1 Ch 6).

    K is constant up to W/S = 20, tapers linearly to 28.6 at W/S = 100, and holds
    constant at 28.6 for W/S >= 100 (FAR 23.335(a); STRSPEED.BAS clamps there).
    Normal and utility share K0 = 33; acrobatic uses K0 = 36. Above W/S = 100 the
    schedule is outside 23.335's tabulated range -- structural_speeds flags the
    resulting minimum as out-of-band.
    """
    k0 = 36.0 if category == "A" else 33.0
    ws = min(wing_loading, 100.0)
    if ws <= 20.0:
        return k0
    return k0 - (k0 - 28.6) / (100.0 - 20.0) * (ws - 20.0)


def dive_ratio_coefficient(category: str, wing_loading: float) -> float:
    """K in VD(min) = K*VC, by category (Reference 1 Ch 6).

    K0 (at W/S <= 20) is 1.40 normal, 1.50 utility, 1.55 acrobatic, tapering to
    1.35 at W/S = 100 and holding constant at 1.35 for W/S >= 100 (FAR 23.335(b);
    STRSPEED.BAS clamps there). (The absolute FAR floor VD >= 1.25*VC also applies
    and, for the worked example, governs.) Above W/S = 100 the schedule is outside
    23.335's tabulated range -- structural_speeds flags the minimum as out-of-band.
    """
    k0 = {"U": 1.50, "A": 1.55}.get(category, 1.40)
    ws = min(wing_loading, 100.0)
    if ws <= 20.0:
        return k0
    return k0 - (k0 - 1.35) / (100.0 - 20.0) * (ws - 20.0)


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
