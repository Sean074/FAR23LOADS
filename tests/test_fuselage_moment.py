"""Munk slender-body fuselage pitching-moment estimator (Step G4).

The estimator derives the fuselage's contribution to the airplane-less-tail
moment slope ``dCm/dalpha`` from the G1 fuselage outline, so a concept airplane
built from a planform can pick it up from geometry instead of hand-folding it
into the FLTLOADS input coefficients. It is off by default: on the FAR23 GA
Appendix A inputs (whose coefficients already include the fuselage) it is left
disabled and the V-n oracle is bit-for-bit unchanged.

Method + citation: Munk, NACA TR-184 (1924); USAF DATCOM 4.2.1.1. Derivation and
the ``(k2-k1)`` table are in ``reference/fuselage_pitching_moment.md``.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import (  # noqa: E402
    AeroCoefficientsInput,
    FuselageMomentInput,
    FuselageOutline,
    FuselageSection,
    io,
)
from farloads import fuselage_moment as fm  # noqa: E402
from farloads.modules.flight_envelope import build_envelope  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _cylinder_outline(length=200.0, diameter=20.0, n=21):
    """A constant-section circular body (width = height = diameter)."""
    return FuselageOutline(sections=[
        FuselageSection(x=length * i / (n - 1), width=diameter, height=diameter)
        for i in range(n)
    ])


def test_k_factor_table_endpoints_and_interpolation():
    # Clamped at the ends; linear between tabulated points (NACA TR-184).
    assert fm.munk_k2_minus_k1(0.5) == 0.0          # l/d <= 1 -> sphere
    assert fm.munk_k2_minus_k1(100.0) == 0.985      # clamped to table top
    # Midpoint of the 2.0->2.5 interval (0.485 -> 0.607).
    assert math.isclose(fm.munk_k2_minus_k1(2.25), (0.485 + 0.607) / 2, rel_tol=1e-9)


def test_estimate_matches_closed_form():
    # A 200 in long, 20 in diameter cylinder: Vol = A*L, A = pi/4*d^2; fineness
    # 200/20 = 10 -> (k2-k1) = 0.947. dCm/dalpha = k*Vol/(S_in2*mac)/57.2958.
    outline = _cylinder_outline(length=200.0, diameter=20.0)
    s_sqft, mac_in = 174.0, 58.0
    est = fm.estimate(outline, s_sqft, mac_in)
    assert est is not None

    vol = math.pi / 4.0 * 20.0 ** 2 * 200.0
    assert math.isclose(est.volume_in3, vol, rel_tol=1e-9)
    assert math.isclose(est.fineness_ratio, 10.0, rel_tol=1e-9)
    assert math.isclose(est.k2_minus_k1, 0.947, rel_tol=1e-9)

    expected = 0.947 * vol / (s_sqft * 144.0 * mac_in) / (180.0 / math.pi)
    assert math.isclose(est.d_cm_dalpha, expected, rel_tol=1e-9)
    assert est.d_cm_dalpha > 0.0    # destabilizing (nose-up with alpha)


def test_estimate_returns_none_on_insufficient_geometry():
    assert fm.estimate(None, 174.0, 58.0) is None
    one = FuselageOutline(sections=[FuselageSection(x=0.0, width=20.0, height=20.0)])
    assert fm.estimate(one, 174.0, 58.0) is None                 # < 2 stations
    assert fm.estimate(_cylinder_outline(), 0.0, 58.0) is None   # S <= 0
    assert fm.estimate(_cylinder_outline(), 174.0, 0.0) is None  # mac <= 0


def test_disabled_fuselage_moment_leaves_oracle_unchanged():
    # The Appendix A GA project has no fuselage_moment; adding a *disabled* one
    # (or an enabled one with a zero increment) must not perturb the V-n matrix.
    base = build_envelope(io.load_project(_GA))
    base_by_case = {p.case: p for p in base.vn}

    for fmi in (
        FuselageMomentInput(enabled=False, d_cm_dalpha=0.123),   # off -> ignored
        FuselageMomentInput(enabled=True, d_cm_dalpha=0.0),      # zero -> no change
    ):
        proj = io.load_project(_GA)
        assert proj.aero_coeffs is not None
        proj.aero_coeffs = AeroCoefficientsInput(
            cruise=proj.aero_coeffs.cruise, flaps_down=proj.aero_coeffs.flaps_down,
            fuselage_moment=fmi,
        )
        env = build_envelope(proj)
        for p in env.vn:
            b = base_by_case[p.case]
            assert p.m_wf == b.m_wf
            assert p.lt == b.lt
            assert p.nz == b.nz


def test_enabled_fuselage_moment_shifts_balanced_tail_load():
    # Enabling a positive (destabilizing) fuselage dCm/dalpha must change the
    # pitching moment M(W+F) and hence the balancing tail load -- i.e. the wiring
    # actually reaches the balance. (Balance targets the same NZ, so NZ is held.)
    base = {p.case: p for p in build_envelope(io.load_project(_GA)).vn}

    proj = io.load_project(_GA)
    proj.aero_coeffs = AeroCoefficientsInput(
        cruise=proj.aero_coeffs.cruise, flaps_down=proj.aero_coeffs.flaps_down,
        fuselage_moment=FuselageMomentInput(enabled=True, d_cm_dalpha=0.01),
    )
    env = {p.case: p for p in build_envelope(proj).vn}

    # At least one aero-limited (non-stall) point must move its tail load.
    moved = [c for c in env if abs(env[c].lt - base[c].lt) > 1.0]
    assert moved, "enabled fuselage moment did not change any balancing tail load"


def test_serialization_round_trips_fuselage_moment(tmp_path):
    proj = io.load_project(_GA)
    proj.aero_coeffs = AeroCoefficientsInput(
        cruise=proj.aero_coeffs.cruise, flaps_down=proj.aero_coeffs.flaps_down,
        fuselage_moment=FuselageMomentInput(enabled=True, d_cm_dalpha=0.0042),
    )
    path = os.path.join(tmp_path, "with_fus_moment.project.json")
    io.save_project(proj, path)
    back = io.load_project(path)
    assert back.aero_coeffs.fuselage_moment is not None
    assert back.aero_coeffs.fuselage_moment.enabled is True
    assert math.isclose(back.aero_coeffs.fuselage_moment.d_cm_dalpha, 0.0042, rel_tol=1e-12)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            if "tmp_path" in getattr(fn, "__code__", type("x", (), {"co_varnames": ()})).co_varnames:
                import tempfile
                with tempfile.TemporaryDirectory() as d:
                    fn(d)
            else:
                fn()
            print(f"ok  {name}")
    print("all fuselage-moment tests passed")
