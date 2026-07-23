"""Validate the EAS -> CAS/TAS airspeed conversions used by the speed–altitude
flight-limits diagram (Speed–Altitude Envelope page).

KTAS = KEAS/sqrt(sigma) is exact from the shared standard atmosphere. KCAS uses
the standard subsonic compressible impact-pressure relation and reduces to KEAS at
sea level. There is no printed manual oracle for these (they are a presentation
layer over MACHLIM, Ch 6), so the checks are the defining identities plus ordering.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads.constants import (  # noqa: E402
    convert_airspeed,
    eas_to_mach,
    mach_to_eas,
    standard_atmosphere,
)

TOL = 1e-9


def test_sea_level_all_units_equal():
    # At h = 0, sigma = 1 and delta = 1, so KEAS == KCAS == KTAS.
    for u in ("KEAS", "KCAS", "KTAS"):
        assert math.isclose(convert_airspeed(200.0, 0.0, u), 200.0, rel_tol=1e-6)


def test_ktas_is_eas_over_root_sigma():
    for h in (5000.0, 12000.0, 30000.0):
        _, sigma = standard_atmosphere(h)
        assert math.isclose(convert_airspeed(170.0, h, "KTAS"),
                            170.0 / math.sqrt(sigma), rel_tol=TOL)


def test_keas_is_identity():
    for h in (0.0, 12000.0, 40000.0):
        assert convert_airspeed(163.4, h, "KEAS") == 163.4


def test_cas_between_eas_and_tas_at_altitude():
    # Compressibility raises CAS above EAS but keeps it below TAS (subsonic).
    for h in (10000.0, 20000.0, 30000.0):
        eas = 200.0
        cas = convert_airspeed(eas, h, "KCAS")
        tas = convert_airspeed(eas, h, "KTAS")
        assert eas < cas < tas


def test_mach_roundtrip():
    for h in (0.0, 12000.0, 25000.0):
        a, sigma = standard_atmosphere(h)
        assert math.isclose(mach_to_eas(eas_to_mach(180.0, a, sigma), a, sigma),
                            180.0, rel_tol=TOL)


def test_unknown_unit_raises():
    raised = False
    try:
        convert_airspeed(100.0, 0.0, "KIAS")
    except ValueError:
        raised = True
    assert raised


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
