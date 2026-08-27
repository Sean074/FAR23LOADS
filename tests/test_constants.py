"""Single-owner guards for the shared physical constants (CLAUDE.md rule 3).

``RHO_SL`` (CH-6): the sea-level density used to be open-coded at eight sites
under three private names; the literal is now allowed in ``constants.py`` only.
Issue #26 (review 2026-08-17) generalised that guard to every shared constant and
unit factor, and to the ``constants.py`` (Imperial<->Imperial) vs ``units.py``
(Imperial<->SI) demarcation of CONVENTIONS.md §7 -- both directions.
"""

import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re

from sloads import constants, units
from sloads.constants import RHO_SL, standard_atmosphere

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


#: Every package a shared constant could be re-declared in. ``app_shell/``
#: renders inside both GUIs and ``oracle_app/`` is a front-end in its own right,
#: so scanning ``sloads``/``app`` alone left two of the four places a literal can
#: live unguarded -- the same gap the SI scan had (review PB-12, swept here under
#: rule 4).
_SCANNED_PACKAGES = ("sloads", "app", "app_shell", "oracle_app", "scripts", "cli.py")


def _package_sources(*pkgs):
    for pkg in pkgs:
        for path in glob.glob(os.path.join(_ROOT, pkg, "**", "*.py"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                yield os.path.relpath(path, _ROOT), fh.read()


def test_rho_sl_value():
    assert RHO_SL == 0.002378  # slug/ft^3, Reference 1 Ch 6


def test_sea_level_density_literal_has_one_owner():
    offenders = [rel for rel, text in _package_sources(*_SCANNED_PACKAGES)
                 if "0.002378" in text and rel != os.path.join("sloads", "constants.py")]
    assert not offenders, f"open-coded rho_0 outside constants.py: {offenders}"


# --------------------------------------------------------------------------- #
# Issue #26: one owner per shared constant / factor, and the two-file demarcation
# --------------------------------------------------------------------------- #
_CONSTANTS_PY = os.path.join("sloads", "constants.py")

#: The Imperial<->Imperial literals (and their historical .BAS truncations) that
#: are owned by ``constants.py`` and may appear in **no other** source file's code.
#: Each entry: (regex, owner it stands for). Matched on code only -- comment and
#: docstring lines quoting a BASIC listing (``Q = V^2/295``) are exempt.
_IMPERIAL_LITERALS = [
    (r"\b57\.3\b|\b57\.29\d*", "DEG_PER_RAD"),
    (r"\b114\.6\b", "2*DEG_PER_RAD"),
    (r"\b32\.2\b|\b32\.17\d*", "G"),
    (r"\b295(\.\d*)?\b", "DYNAMIC_PRESSURE_DIVISOR / dynamic_pressure_psf"),
    (r"\b498(\.\d*)?\b", "GUST_LOAD_FACTOR_DIVISOR"),
    (r"\b0\.88\b|\b5\.3\b", "gust_alleviation_factor"),
    (r"\b144(\.\d*)?\b", "IN2_PER_FT2"),
    (r"\b550(\.\d*)?\b|\b33000(\.\d*)?\b", "FT_LB_S_PER_HP / HP_TO_TORQUE"),
    (r"\b1\.688\d*|\b1\.687\d*|1\.15 ?\* ?88", "KT_TO_FPS"),
    (r"\b518\.\d+|\b35332(\.\d*)?\b|\b575\.0\b|29\.02436|0\.003566", "standard_atmosphere"),
    (r"\b3\.1416\b|\b3\.14159\d*", "math.pi"),
    (r"\b0\.002378\b", "RHO_SL"),
]

def _code_lines(text):
    """Source lines with comments stripped and docstring/triple-quoted blocks removed."""
    text = re.sub(r'("""|\'\'\')(?:.|\n)*?\1', "", text)
    for line in text.split("\n"):
        code = line.split("#", 1)[0]
        code = re.sub(r'"[^"]*"|\'[^\']*\'', '""', code)   # prose in string literals is not a value
        if code.strip():
            yield code


def _offenders(literals, allowed_owner):
    hits = []
    for rel, text in _package_sources(*_SCANNED_PACKAGES):
        if rel == allowed_owner:
            continue
        for code in _code_lines(text):
            for pat, owner in literals:
                if re.search(pat, code):
                    hits.append(f"{rel}: {code.strip()!r} -> use constants/units {owner}")
    return hits


def test_imperial_factors_have_one_owner():
    """No suite-internal constant or factor is re-declared or open-coded outside
    ``constants.py`` (C-1..C-10 of the 2026-08-17 review; CH-6 generalised)."""
    assert not _offenders(_IMPERIAL_LITERALS, _CONSTANTS_PY), "\n".join(_offenders(_IMPERIAL_LITERALS, _CONSTANTS_PY))


def test_si_factors_live_only_in_units_py():
    """The Imperial<->SI boundary is ``units.py`` and nothing else (C-11); and
    ``units.py`` imports ``constants``, never the reverse.

    The factor scan itself is
    ``test_units.py::test_si_factor_literals_have_one_owner``: it derives the
    numbers from ``units.py``'s own constants instead of transcribing six of
    them into a regex list here, and covers every package. Two hand-kept lists
    of the same factors were the CH-7 defect class applied to its own guard --
    each was missing factors the other had, and neither looked at ``app_shell/``
    or ``oracle_app/`` (review PB-12). What remains here is the half that scan
    cannot see: the direction of the dependency between the two owners.
    """
    with open(os.path.join(_ROOT, _CONSTANTS_PY), encoding="utf-8") as fh:
        constants_src = fh.read()
    assert not re.search(r"^\s*(from \.units|from sloads\.units|import sloads\.units)", constants_src, re.M)


def test_no_private_aliases_of_owned_constants():
    """The defect class itself: a module-level ``_DEG = ...``, ``_G = ...``,
    ``_SQIN_PER_SQFT = ...`` etc. is a second declaration of an owned value."""
    banned = re.compile(r"^(_DEG(_PER_RAD)?|_RAD|_G|_Q_DIVISOR|_IN2_PER_FT2|_SQIN_PER_SQFT|PI|TWO_PI) = ", re.M)
    hits = [f"{rel}: {m.group(0).strip()}" for rel, text in _package_sources(*_SCANNED_PACKAGES)
            for m in banned.finditer(text) if not (rel.endswith("configuration.py") and "_DEG = " in m.group(0))]
    assert not hits, hits


def test_exact_by_default_values():
    """The owners hold the exact values; the survivors are named twins with the
    oracle that pins them (register 2026-08-17)."""
    import math

    assert 180.0 / math.pi == constants.DEG_PER_RAD
    assert math.pi / 180.0 == constants.RAD_PER_DEG
    assert constants.IN_PER_FT == 12.0 and constants.IN2_PER_FT2 == 144.0
    assert constants.FT_LB_S_PER_HP == 550.0 and constants.HP_TO_TORQUE == 33000.0
    # kt->ft/s: 1852 m / 0.3048 m/ft / 3600 s -- stated in constants, derived here from units.
    assert math.isclose(constants.FT_PER_NMI, 1852.0 / units.FT_TO_M, rel_tol=1e-15)
    assert math.isclose(constants.KT_TO_FPS, 1.687810, rel_tol=1e-6)
    assert math.isclose(constants.KT_TO_FPS_SUITE, 1.686667, rel_tol=1e-6)      # survivor: VSF only
    assert constants.VSF == 60 * constants.KT_TO_FPS_SUITE                       # -> 101.2, ENGLOADS oracle
    assert math.isclose(constants.DYNAMIC_PRESSURE_DIVISOR, 295.237, rel_tol=1e-6)
    assert constants.DYNAMIC_PRESSURE_DIVISOR == 1.0 / (0.5 * RHO_SL * constants.KT_TO_FPS ** 2)
    q = constants.dynamic_pressure_psf(170.0)
    assert math.isclose(constants.eas_from_dynamic_pressure(q), 170.0, rel_tol=1e-12)
    gust = (constants.GUST_KG_NUMERATOR, constants.GUST_KG_OFFSET, constants.GUST_LOAD_FACTOR_DIVISOR)
    assert gust == (0.88, 5.3, 498.0)
    assert constants.gust_alleviation_factor(10.0) == 0.88 * 10.0 / (5.3 + 10.0)


def test_flight_envelope_reads_the_shared_speed_of_sound():
    """C-7: FLTLOADS' private 518.688 / 575 atmosphere is retired; ``a`` is read from the owner."""
    from sloads.modules.flight_envelope import _speed_of_sound

    for alt in (0.0, 5000.0, 20000.0, 35332.0, 40000.0):
        assert _speed_of_sound(alt) == standard_atmosphere(alt)[0]


def test_sigma_is_read_from_the_shared_atmosphere():
    """M4-23: FLTLOADS' density ratio delegates to constants.standard_atmosphere."""
    from sloads.modules.flight_envelope import density_ratio

    for alt in (0.0, 5000.0, 20000.0, 35332.0, 40000.0):
        assert density_ratio(alt) == standard_atmosphere(alt)[1]



# --------------------------------------------------------------------------- #
# The airspeed inverse (#80) -- KCAS in, KEAS out
# --------------------------------------------------------------------------- #
def test_the_three_airspeeds_agree_at_sea_level():
    """KEAS == KCAS == KTAS at h = 0, by definition of the relations."""
    for measure in ("KEAS", "KCAS", "KTAS"):
        assert math.isclose(constants.eas_from_airspeed(150.0, 0.0, measure), 150.0,
                            rel_tol=1e-12), measure


def test_eas_from_airspeed_inverts_convert_airspeed_exactly():
    """The converter offers all three measures as an *input*, so the two
    directions must be one relation read backwards -- not two fits that agree
    near sea level and part at altitude."""
    for altitude in (0.0, 8000.0, 20000.0, 35000.0, 45000.0):
        for measure in ("KEAS", "KCAS", "KTAS"):
            for speed in (80.0, 180.0, 350.0):
                eas = constants.eas_from_airspeed(speed, altitude, measure)
                back = constants.convert_airspeed(eas, altitude, measure)
                assert math.isclose(back, speed, rel_tol=1e-9), (altitude, measure, speed)


def test_airspeeds_order_themselves_the_way_altitude_makes_them():
    """Above sea level a given EAS reads as a larger TAS (thinner air) and a
    larger CAS (the compressibility correction, which is *subtracted* from CAS
    to get EAS) -- so KEAS is the smallest of the three, and an inverse that
    ran the CAS relation the wrong way would put it in the middle."""
    eas = 200.0
    tas = constants.convert_airspeed(eas, 25000.0, "KTAS")
    cas = constants.convert_airspeed(eas, 25000.0, "KCAS")
    assert tas > cas > eas, (tas, cas, eas)
    assert constants.eas_from_airspeed(cas, 25000.0, "KCAS") < cas


def test_an_unknown_airspeed_measure_is_refused_in_both_directions():
    for fn in (constants.convert_airspeed, constants.eas_from_airspeed):
        try:
            fn(100.0, 0.0, "KIAS")
        except ValueError:
            continue
        raise AssertionError(f"{fn.__name__} accepted KIAS, which it cannot compute")


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

