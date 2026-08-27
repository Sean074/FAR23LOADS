"""Chordwise tail-load distribution (Step C7): TAILDIST.BAS port + AIRLOAD4.

The FAR23 path is oracle-locked against the Appendix A "Chordwise Distribution of
Tail Loads" report (p237/p245). TAILDIST resolves SELECT's critical tail loads
(``LT25`` at 25% MAC, ``LT50`` at 50% MAC) into a five-station chordwise pressure
profile: the additive (angle-of-attack) distribution (4× the average pressure at
the leading edge, the average at the quarter chord, zero at the trailing edge)
plus the camber distribution (a trapezoid symmetric about the 50% chord). The
program works in the half (LH) tail area with both-sides loads; folding the two
factors of two together gives the unified ``LT/S`` form on the full surface area
the suite stores (TAILDIST.BAS subroutine 3000).

AIRLOAD4 (Ref 1 Ch 12) redistributes the additive Schrenk span load for sweepback
(``(c·cl/cmac)_Λ = (c·cl/cmac)_0 − (1−2y/b)·2(1−cosΛ)``); it reduces exactly to
AIRLOADS at zero sweep / low Mach.

Reference: TAILDIST.BAS (Appendix C subroutine 3000), Ref 1 Ch 10 p82-84; oracle
Appendix A p237 (13 horizontal conditions) / p245 (4 vertical conditions).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

from sloads import AeroSurfaceInput, SurfaceInput, io
from sloads.modules.airloads import schrenk_distribution, use_airload4
from sloads.modules.select import build_critical
from sloads.modules.taildist import (
    build_tail_chordwise,
    chordwise_pressures,
    run,
)

REL = 1e-3  # ±0.1%
ABS = 1e-3  # stations printed to 3 decimals; some oracle values are ~0

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")

# Appendix A horizontal tail (full both-sides areas in sq in, full span in in):
# AREA 2660 / ELEVATOR AFT-OF-HL 1065 / SEMI-SPAN 73.1 (the report's LH figures).
_HT_AREA = 2660.0 * 2.0
_HT_AFT = 1065.0 * 2.0
_HT_SPAN = 73.1 * 2.0

# Appendix A "Chordwise Distribution ... Horizontal Tail" p237: per condition
# (LT25, LT50, [PSI(X1..X5)]).
_HT_ORACLE = [
    (907.62, -387.77, [0.682, 0.095, 0.000, 0.015, -0.030]),
    (217.58, -831.50, [0.164, -0.122, 0.000, -0.228, -0.239]),
    (-34.76, -62.09, [-0.026, -0.019, 0.000, -0.025, -0.023]),
    (-532.85, -496.12, [-0.401, -0.197, 0.000, -0.236, -0.209]),
    (-51.60, -1227.79, [-0.039, -0.250, 0.000, -0.393, -0.390]),
    (65.04, 1072.70, [0.049, 0.222, 0.000, 0.346, 0.343]),
    (-458.46, -218.34, [-0.345, -0.129, 0.000, -0.137, -0.114]),
    (700.30, 87.48, [0.527, 0.149, 0.000, 0.133, 0.098]),
    (843.46, 65.04, [0.634, 0.171, 0.000, 0.147, 0.105]),
    (-1186.70, -106.00, [-0.892, -0.244, 0.000, -0.212, -0.152]),
    (-478.67, 3.52, [-0.360, -0.089, 0.000, -0.071, -0.047]),
    (-1087.52, -161.30, [-0.818, -0.236, 0.000, -0.214, -0.160]),
    (-1186.81, -106.00, [-0.892, -0.244, 0.000, -0.212, -0.152]),
]

# Appendix A vertical tail p245: AREA 2137 / RUDDER AFT-OF-HL 667 / SPAN 57 (single
# surface). Conditions (LT25, LT50, [PSI(X1..X5)]).
_VT_AREA, _VT_AFT, _VT_SPAN = 2137.0, 667.0, 57.0
_VT_ORACLE = [
    (0.00, 679.00, [0.000, 0.370, 0.000, 0.462, 0.462]),
    (-1076.00, 679.00, [-2.014, -0.134, 0.000, 0.000, 0.252]),
    (-827.00, 0.00, [-1.548, -0.387, 0.000, -0.355, -0.161]),
    (950.00, 0.00, [1.778, 0.445, 0.000, 0.408, None]),
]


def _check(stations, expect):
    assert len(stations) == 5
    for s, e in zip(stations, expect):
        if e is None:
            continue
        assert math.isclose(s.psi, e, rel_tol=REL, abs_tol=ABS), (s.x, s.psi, e)


def test_horizontal_chordwise_oracle():
    """All 13 Appendix A horizontal-tail chordwise distributions (p237)."""
    for lt25, lt50, expect in _HT_ORACLE:
        stations = chordwise_pressures(lt25, lt50, _HT_AREA, _HT_AFT, _HT_SPAN)
        _check(stations, expect)


def test_vertical_chordwise_oracle():
    """All 4 Appendix A vertical-tail chordwise distributions (p245)."""
    for lt25, lt50, expect in _VT_ORACLE:
        stations = chordwise_pressures(lt25, lt50, _VT_AREA, _VT_AFT, _VT_SPAN)
        _check(stations, expect)


def test_chord_stations():
    """The five chord stations match the oracle geometry (X3 = CAVE; X4 = hinge)."""
    st = chordwise_pressures(907.62, -387.77, _HT_AREA, _HT_AFT, _HT_SPAN)
    xs = [s.x for s in st]
    # X1=0, X2=0.25·CT, X3=CT=36.38851, X4=CEAFTHL=14.56908, X5=CT−X4=21.81942.
    assert math.isclose(xs[2], 36.38851, rel_tol=REL)
    assert math.isclose(xs[1], 0.25 * 36.38851, rel_tol=REL)
    assert math.isclose(xs[3], 14.56908, rel_tol=REL)
    assert math.isclose(xs[4], 21.81942, rel_tol=REL)


def test_select_to_taildist_integration():
    """SELECT's critical tail loads flow into TAILDIST: the GA6 example yields the
    nine flaps-retracted horizontal conditions plus the four vertical conditions.

    (The four flaps-extended horizontal conditions in the Appendix A 13-row table
    need the flapped V-n envelope, a documented C6 deferral; the pure-oracle test
    above covers all 13 rows directly via :func:`chordwise_pressures`.)"""
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    results = build_tail_chordwise(p)
    htail = [r for r in results if r.component == "htail"]
    vtail = [r for r in results if r.component == "vtail"]
    assert len(htail) == 9
    assert len(vtail) == 4
    # Every condition has five chord stations and the total splits as LT25 + LT50.
    for r in results:
        assert len(r.stations) == 5
        assert r.stations[2].psi == 0.0  # trailing edge carries no net pressure


def test_far_reference_propagates_from_select():
    """The chordwise distribution keeps the governing condition's citation, not a
    single hardcoded 23.421 (the pre-fix behaviour mis-cited every v-tail and
    maneuver/gust/unsymmetrical h-tail row as "23.421 Balancing Loads")."""
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]

    # build_tail_chordwise copies far_reference verbatim from the SELECT condition.
    src = {(c.component, c.label): c.far_reference
           for c in build_critical(p).conditions if c.component in ("htail", "vtail")}
    for r in build_tail_chordwise(p):
        assert r.far_reference == src[(r.component, r.case)]

    # run()'s ConditionResults surface the real citations, so not everything is 23.421.
    cites = {c.far_reference for c in run(p).conditions}
    assert cites != {"23.421"}
    # The four v-tail conditions carry their 23.441/23.443 citations.
    assert {"23.441(a)(1)", "23.441(a)(2)", "23.441(a)(3)", "23.443(b)"} <= cites


# --------------------------------------------------------------------------- #
# AIRLOAD4 (sweep / high-Mach branch)
# --------------------------------------------------------------------------- #
_WING = SurfaceInput(
    name="wing", elements=20,
    leading_edge=[(0.0, 0.0), (20.0, 100.0)],
    trailing_edge=[(60.0, 0.0), (50.0, 100.0)],
)
_AERO = AeroSurfaceInput(name="wing", section_slope=0.1075, tau=0.16, target_cl=1.0)


def test_airload4_reduction_invariant():
    """At zero sweep and low Mach the distribution is byte-identical to AIRLOADS,
    and Mach alone (no sweep) does not change the shape (compressibility is carried
    upstream by FLTLOADS' CL)."""
    base = schrenk_distribution(_WING, _AERO)
    assert not base.airload4
    mach = schrenk_distribution(_WING, replace(_AERO, design_mach=0.6))
    assert mach.airload4
    for a, b in zip(base.ccl_additive, mach.ccl_additive):
        assert a == b


def test_airload4_sweep_shifts_load_outboard():
    """Sweepback shifts the operating span load outboard (root reduced, tip ~unchanged
    -- the (1−2y/b) term vanishes at the tip) and, after the COL20 renormalization,
    the swept distribution re-integrates to the operating CL (M1-3). The sweep acts
    on the combined operating ``ccl_total``; the additive/basic split is the unswept
    decomposition (AIRLOAD4.BAS COL16 is the operating distribution)."""
    base = schrenk_distribution(_WING, _AERO)
    swept = schrenk_distribution(_WING, replace(_AERO, sweep_deg=25.0))
    assert swept.airload4
    assert use_airload4(replace(_AERO, sweep_deg=25.0))
    # The additive/basic decomposition is left unswept; only the total is redistributed.
    assert swept.ccl_additive == base.ccl_additive
    assert swept.ccl_total[0] < base.ccl_total[0]                  # root reduced
    assert abs(swept.ccl_total[-1] - base.ccl_total[-1]) < abs(
        swept.ccl_total[0] - base.ccl_total[0])                   # tip ~unchanged
    # COL20 renormalization: the swept span load recovers the operating CL (no lift lost).
    assert math.isclose(swept.recovered_cl, _AERO.target_cl, rel_tol=2e-3)


def test_io_roundtrip_chordwise_fields():
    """The new tail-span fields and the chordwise result slice round-trip, and an
    older (pre-C7) project without them still loads with the defaults."""
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.loads = p.loads or None
    from sloads.models import LoadsResult
    p.loads = LoadsResult(tail_chordwise=build_tail_chordwise(p))
    d = io.project_to_dict(p)
    p2 = io.project_from_dict(d)
    assert p2.tail_loads.htail_semispan_in == 73.1
    assert p2.vtail_loads.vtail_span_in == 57.0
    assert len(p2.loads.tail_chordwise) == len(p.loads.tail_chordwise)
    assert p2.loads.tail_chordwise[0].stations[0].psi == p.loads.tail_chordwise[0].stations[0].psi
    # Step G6: tail geometry serializes under geometry.empennage.htail (not top-level).
    d["geometry"]["empennage"]["htail"].pop("htail_semispan_in", None)
    p3 = io.project_from_dict(d)
    assert p3.tail_loads.htail_semispan_in == 0.0


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
