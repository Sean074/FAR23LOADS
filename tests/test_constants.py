"""Single-owner guards for the shared physical constants (CLAUDE.md rule 3).

``RHO_SL`` (CH-6): the sea-level density used to be open-coded at eight sites
under three private names; the literal is now allowed in ``constants.py`` only.
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads.constants import RHO_SL, standard_atmosphere  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _package_sources(*pkgs):
    for pkg in pkgs:
        for path in glob.glob(os.path.join(_ROOT, pkg, "**", "*.py"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                yield os.path.relpath(path, _ROOT), fh.read()


def test_rho_sl_value():
    assert RHO_SL == 0.002378  # slug/ft^3, Reference 1 Ch 6


def test_sea_level_density_literal_has_one_owner():
    offenders = [rel for rel, text in _package_sources("sloads", "app", "cli.py")
                 if "0.002378" in text and rel != os.path.join("sloads", "constants.py")]
    assert not offenders, f"open-coded rho_0 outside constants.py: {offenders}"


def test_sigma_is_read_from_the_shared_atmosphere():
    """M4-23: FLTLOADS' density ratio delegates to constants.standard_atmosphere."""
    from sloads.modules.flight_envelope import density_ratio

    for alt in (0.0, 5000.0, 20000.0, 35332.0, 40000.0):
        assert density_ratio(alt) == standard_atmosphere(alt)[1]


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

