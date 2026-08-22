"""Flight envelope + balancing tail loads (Step C2): FLTLOADS port.

The FAR23 path is oracle-locked against the Appendix A "V-n Data" worked example
(p179-180): the cruise balanced-flight-load matrix (V, NZ, alpha, G, CL, M(W+F),
LZW, LT, DX) for each CG case. The balance iterates the angle of attack to the
required load factor only to within +-0.005 NZ (FLTLOADS.BAS line 4130), so the
manual's printed figures carry that convergence noise (~0.5% on low-load-factor
quantities); the regression tolerances below reflect it. The headline balancing
tail load LT and the corner speeds/load factors match tightly.

Concept mode has no printed oracle and is checked by physics closure: the balance
attains the user-chosen load factor (no GA cap) and the wing-plus-tail normal
load equals NZ*W.

Reference: FLTLOADS.BAS (Appendix C p421-428), Ref 1 Ch 8; Appendix A p179-180.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import (  # noqa: E402
    AeroCoefficientsInput,
    AeroCoeffSet,
    FlightLoadsInput,
    Project,
    io,
)
from sloads.derived_geometry import require_wing_reference  # noqa: E402
from sloads.modules import flight_envelope as fe  # noqa: E402
from sloads.modules.flight_envelope import build_envelope, design_inputs  # noqa: E402
from sloads.cg_cases import flight_cases  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_heavy.project.json")


def _by_case(env):
    return {p.case: p for p in env.vn}


def _close(actual, expected, rel=3e-3, abs_=2.0):
    """True within a relative tolerance or an absolute floor (for small numbers)."""
    return math.isclose(actual, expected, rel_tol=rel, abs_tol=abs_)


def test_design_speeds_match_appendix_a():
    di = design_inputs(io.load_project(_GA))
    assert math.isclose(di.va, 121.3, rel_tol=1e-3)     # Appendix A p179
    assert math.isclose(di.vc, 170.0, rel_tol=1e-3)
    assert math.isclose(di.vd, 212.5, rel_tol=1e-3)
    assert math.isclose(di.vf, 105.5, rel_tol=1e-3)
    assert math.isclose(di.mc, 0.323, rel_tol=2e-3)
    assert math.isclose(di.md, 0.403, rel_tol=2e-3)
    assert math.isclose(di.n_pos, 3.8, rel_tol=1e-3)
    assert math.isclose(di.n_neg, -1.52, rel_tol=1e-3)


def test_cg1_corner_speeds_and_load_factors():
    pts = _by_case(build_envelope(io.load_project(_GA)))
    # (case, V, NZ, alpha) -- Appendix A p179 CG1.
    for case, v, nz, alpha in [
        (1, 61.4, 1.00, 13.38),     # STALL 1G
        (3, 121.3, 3.80, 12.75),    # MAN A
        (5, 212.5, 3.80, 1.56),     # MAN D
        (7, 170.0, -1.52, -7.00),   # MAN -C
        (20, 115.0, 3.25, 11.96),   # AC ROLL
    ]:
        p = pts[case]
        assert math.isclose(p.v_eas_kt, v, rel_tol=2e-3), (case, p.v_eas_kt, v)
        assert math.isclose(p.nz, nz, abs_tol=0.01), (case, p.nz, nz)
        assert math.isclose(p.alpha_deg, alpha, abs_tol=0.05), (case, p.alpha_deg, alpha)


def test_cg1_balancing_tail_loads():
    pts = _by_case(build_envelope(io.load_project(_GA)))
    # Balancing tail load LT, Appendix A p179 CG1.
    for case, lt in [(1, 132), (3, 493), (5, 169), (7, -465), (10, 352), (20, 412)]:
        assert _close(pts[case].lt, lt, rel=5e-3, abs_=3.0), (case, pts[case].lt, lt)


def test_cg1_wing_lift_and_pitching_moment():
    pts = _by_case(build_envelope(io.load_project(_GA)))
    # LZW (lift less tail) + M(W+F), Appendix A p179 CG1 -- larger-magnitude points.
    assert _close(pts[3].lzw, 12419)         # MAN A
    assert _close(pts[10].lzw, 13120)        # GUST +C
    assert _close(pts[20].lzw, 10637)        # AC ROLL
    assert _close(pts[3].m_wf, 22864, rel=5e-3)
    assert _close(pts[7].m_wf, -58797, rel=5e-3)


def test_cg2_balancing_tail_loads():
    pts = _by_case(build_envelope(io.load_project(_GA)))
    # CG2 (cases 21-40), Appendix A p179.
    # Stall-line speeds carry the most balance-convergence noise (Q iteration).
    assert math.isclose(pts[21].v_eas_kt, 62.6, rel_tol=5e-3)   # STALL 1G
    assert _close(pts[21].lt, -16, abs_=3.0)
    assert math.isclose(pts[23].nz, 3.80, abs_tol=0.01)         # MAN A
    assert _close(pts[23].lzw, 12970)
    assert _close(pts[23].lt, -59, abs_=4.0)


def test_gust_load_factors_match_appendix_a():
    pts = _by_case(build_envelope(io.load_project(_GA)))
    assert math.isclose(pts[10].nz, 3.96, abs_tol=0.01)   # GUST +C, p179
    assert math.isclose(pts[13].nz, -1.96, abs_tol=0.01)  # GUST -C
    assert math.isclose(pts[11].nz, 2.88, abs_tol=0.01)   # GUST +D
    assert math.isclose(pts[12].nz, -0.88, abs_tol=0.01)  # GUST -D


def test_tail_balance_parallels_vn():
    env = build_envelope(io.load_project(_GA))
    assert len(env.tail_balance) == len(env.vn)
    for vp, tb in zip(env.vn, env.tail_balance):
        assert tb.case == vp.case
        assert tb.tail_load_lb == vp.lt
        assert tb.tail_cp_station == 253.364   # XTC, cruise (flaps up)
        assert tb.flaps_down is False


def test_multi_altitude_vn_regression():
    """Step D5: ``build_envelope`` already loops ``for alt in fl.altitudes_ft``
    (Step C2) -- this locks in that a second altitude produces its own balanced
    matrix without changing the sea-level (Appendix A) numbers, i.e. no equation
    change, purely a GUI exposure of an existing calc loop."""
    project = io.load_project(_GA)
    baseline = _by_case(build_envelope(project))

    project.flight_loads.altitudes_ft = [0.0, 8000.0]
    two_alt = build_envelope(project)

    # Sea-level cases are bit-for-bit unchanged by adding a second altitude.
    for case, p in baseline.items():
        p2 = next(v for v in two_alt.vn if v.case == case)
        assert p2.altitude_ft == 0.0
        assert math.isclose(p2.v_eas_kt, p.v_eas_kt)
        assert math.isclose(p2.lt, p.lt)

    # The 8000 ft matrix is present, distinct, and the same size as sea level.
    hi = [v for v in two_alt.vn if v.altitude_ft == 8000.0]
    lo = [v for v in two_alt.vn if v.altitude_ft == 0.0]
    assert len(hi) == len(lo) == len(baseline)
    hi_man_a = next(v for v in hi if v.condition == "MAN A" and v.cg == "CG1")
    lo_man_a = next(v for v in lo if v.condition == "MAN A" and v.cg == "CG1")
    assert hi_man_a.v_eas_kt != lo_man_a.v_eas_kt or hi_man_a.alpha_deg != lo_man_a.alpha_deg


def test_concept_attains_chosen_load_factor_no_cap():
    project = io.load_project(_CONCEPT)
    assert project.is_concept
    env = build_envelope(project)
    man_a = next(p for p in env.vn if p.condition == "MAN A")
    # The balance attains the user load factor (chosen_n = 4.0; no FAR 23.337 cap).
    assert math.isclose(man_a.nz, 4.0, abs_tol=0.01)
    # Physics closure: wing-plus-tail normal load == NZ * W.
    assert math.isclose((man_a.lzw + man_a.lt) / 18000.0, man_a.nz, abs_tol=0.01)


def test_balance_zeroes_pitching_moment_about_cg():
    # By construction LT zeroes the moment sum about the CG (Ch 8 balance).
    project = io.load_project(_GA)
    fl = project.flight_loads
    wr = require_wing_reference(project)
    cg = flight_cases(project)[0]
    p = next(pt for pt in build_envelope(project).vn if pt.condition == "MAN A")
    moment = (p.m_wf + p.lzw * (cg.xcg - wr.xw) - p.dx * (cg.zcg - wr.zw)
              - p.lt * (fl.xtc - cg.xcg))
    assert abs(moment) < 1.0


def test_run_flags_concept_note():
    result = fe.run(io.load_project(_CONCEPT))
    assert result.module == "flight_envelope"
    assert "concept" in result.conditions[0].note.lower()


def test_run_requires_flight_loads_slice():
    try:
        fe.run(Project(name="no-flight-loads"))
    except ValueError:
        return
    raise AssertionError("expected ValueError when the flight_loads slice is missing")


def test_envelope_round_trips_through_io():
    project = io.load_project(_GA)
    project.envelope = build_envelope(project)
    rebuilt = io.project_from_dict(io.project_to_dict(project))
    assert rebuilt.envelope is not None
    assert len(rebuilt.envelope.vn) == len(project.envelope.vn)
    assert rebuilt.envelope.vn[2].condition == "MAN A"
    assert math.isclose(rebuilt.envelope.vn[2].lt, project.envelope.vn[2].lt)
    assert len(rebuilt.envelope.tail_balance) == len(project.envelope.tail_balance)


def test_flight_loads_slice_round_trips_through_io():
    project = io.load_project(_GA)
    rebuilt = io.project_from_dict(io.project_to_dict(project))
    fl = rebuilt.flight_loads
    assert fl is not None
    # Note 33: mac/S/xw/zw are not on the slice at all -- they are read from the
    # planform, which survives the round-trip, so the reloaded project still
    # reproduces the wing geometry (mac within +/-0.1% of Appendix A's 69.246, zw
    # from the parametric wing reference plane).
    wr = require_wing_reference(rebuilt)
    assert math.isclose(wr.mac, 69.246, rel_tol=1e-3)
    assert math.isclose(wr.zw, 87.734, rel_tol=1e-3)
    assert flight_cases(rebuilt)[0].name == "CG1"


def test_flight_loads_wing_geometry_not_persisted():
    """Step M2-6: the derived wing scalars are dropped from the serialized slice
    (single source is Project.geometry) -- only the tail-CP/Mach/altitude inputs
    survive on the flight_loads dict. The weight/CG cases left it too, at decision
    G-3b: ``weight.cg_cases`` is the one list."""
    project = io.load_project(_GA)
    d = io.project_to_dict(project)["flight_loads"]
    for k in ("mac", "wing_area_sqft", "xw", "zw", "cg_cases"):
        assert k not in d


def test_aero_coeffs_slice_round_trips_through_io():
    project = io.load_project(_GA)
    rebuilt = io.project_from_dict(io.project_to_dict(project))
    aero = rebuilt.aero_coeffs
    assert aero is not None
    assert aero.cruise is not None
    assert aero.cruise.lift[1] == 0.080358
    assert aero.flaps_down is None


def test_legacy_flight_loads_configurations_migrate_to_aero_coeffs():
    """Pre-schema-18 files carried the coefficient sets as
    ``flight_loads.configurations``; loading one must still populate
    ``Project.aero_coeffs`` (Step D4.1 migration).

    M4-10: the fixture now declares ``schema_version = 17``, i.e. it really is a
    pre-v18 file. Before the migration chain this shim ran on every file
    regardless of version, so the test passed while mutating a current-schema
    dict -- and a modern project that deliberately had no ``aero_coeffs`` would
    have had a set resurrected from a stale ``flight_loads.configurations``."""
    legacy = io.project_to_dict(io.load_project(_GA))
    cruise = legacy["aero_coeffs"].pop("cruise")
    legacy["flight_loads"]["configurations"] = [dict(cruise, name="CRUISE", flaps_down=False)]
    del legacy["aero_coeffs"]
    legacy["schema_version"] = 17

    rebuilt = io.project_from_dict(legacy)
    assert rebuilt.aero_coeffs is not None
    assert rebuilt.aero_coeffs.cruise is not None
    assert rebuilt.aero_coeffs.cruise.lift[1] == 0.080358
    assert rebuilt.aero_coeffs.flaps_down is None


# The GA6 flaps-extended (LANDING) aero coefficients, transcribed from the
# Appendix A "V-n Data" input listing (Ref 1 Code.pdf p179): the flaps-down
# lift/drag/pitching-moment polynomials and the flaps-down stall CL. These ARE in
# the reference -- the 0.2.0 baseline claim that the repo lacked the landing-config
# polynomials was wrong (they are printed alongside the cruise set), and using them
# is what validates the flaps-extended balancing tail loads against Appendix A p181.
_LANDING = AeroCoeffSet(
    name="LANDING",
    lift=(1.089965, 0.080358, 0.0, 0.0, 0.0),
    drag=(0.072334, 0.001716, 0.053644, 0.0, 0.0),
    moment=(-0.280453, 0.004128, 0.0, 0.0, 0.0),
    stall_cl=1.5857, neg_stall_cl=-0.41, flaps_down=True,
)


def _with_landing():
    # The GA6 project plus the real (Appendix A p179) LANDING configuration. The
    # flapped envelope is exercised for both closure (NZ achieved, n<=2 maneuver
    # limit) and the printed flaps-extended balancing tail loads (Appendix A p181).
    import copy

    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0]
    p.aero_coeffs.flaps_down = copy.deepcopy(_LANDING)
    return p


def test_flapped_envelope_corner_set_and_closure():
    # Step C6 R3: the flaps-extended corner set (FLTLOADS subr 3000) at VF, n<=2.
    env = build_envelope(_with_landing())
    flap = [v for v in env.vn if v.config == "LANDING"]
    conds = {v.condition for v in flap}
    assert {"STAL 2/3G", "STALL 2G", "MAN 2G VF", "GUST VF", "BAL VF", "BAL 1.4VSF"} <= conds
    # The maneuver points achieve their target NZ (2/3, 1, 2) and sit at VF.
    man2 = next(v for v in flap if v.condition == "MAN 2G VF")
    assert math.isclose(man2.nz, 2.0, abs_tol=0.01)
    assert math.isclose(man2.v_eas_kt, 105.5, rel_tol=5e-3)   # VF
    stal = next(v for v in flap if v.condition == "STAL 2/3G")
    assert math.isclose(stal.nz, 2.0 / 3.0, abs_tol=0.01)


def test_bal_1p4vsf_balances_at_one_g_flaps_down_stall():
    """M1-2 / review T2: BAL 1.4VSF balances at 1.4x the **1-g** flaps-down stall
    (STALL 1GL), not 1.4x the 2-g stall. FLTLOADS.BAS (Code.pdf p300-302) saves the
    STALL 1GL speed for this condition; the earlier code captured STALL 2G, giving a
    balance speed ~1.4x too high and a tail load ~2.2x too large.

    Oracle: Appendix A LANDING configuration, CG5 (FS 85.1), landing-block case 9
    (absolute case 89) 'BAL 1.4VS' -- V 83.6 kt / LT -430 lb (Code.pdf p181; landing
    aero polynomials p179). LT is a small residual of the CG moment balance, so it
    carries the widest tolerance, as the cruise LT oracles above do."""
    flap = [v for v in build_envelope(_with_landing()).vn
            if v.config == "LANDING" and v.cg == "CG1"]   # manual CG5 (FS 85.1)
    by = {v.condition: v for v in flap}
    bal, stall_1gl, stall_2g = by["BAL 1.4VSF"], by["STALL 1GL"], by["STALL 2G"]

    # The fix, stated exactly: the BAL speed is 1.4x the 1-g flaps-down stall speed,
    assert math.isclose(bal.v_eas_kt, 1.4 * stall_1gl.v_eas_kt, rel_tol=1e-9)
    # and NOT 1.4x the 2-g stall (the T2 defect, which produced ~116 kt / -957 lb).
    assert not math.isclose(bal.v_eas_kt, 1.4 * stall_2g.v_eas_kt, rel_tol=1e-2)

    # Appendix A p181 case 89 -- reproduced within print precision.
    assert math.isclose(bal.v_eas_kt, 83.6, rel_tol=5e-3)     # manual 83.6 kt
    assert math.isclose(bal.lt, -430.0, rel_tol=1.5e-2)       # manual -430 lb
    assert math.isclose(bal.alpha_deg, -2.54, abs_tol=0.12)   # manual -2.54 deg
    assert math.isclose(bal.cl, 0.89, abs_tol=0.02)           # manual +0.89


def test_merged_replaces_the_altitude_list():
    """Step D5 / decision G-3b: the Flight Envelope page edits the *whole* altitude
    list (multi-altitude V-n), and the weight/CG cases are no longer on this slice
    at all -- they left it at G-3b, since ``flight_loads.cg_cases`` had been a
    derived copy of ``weight.cg_cases`` since v19 and a second way to say the same
    thing is what that decision removes. ``merged()`` therefore replaces the
    altitude list wholesale and there is nothing partial left to preserve."""
    fl = FlightLoadsInput(xtc=253.364, xtf=261.027, mn=0.1,
                          altitudes_ft=[0.0, 20000.0])

    merged = fl.merged(xtc=253.364, xtf=261.027, mn=0.1,
                       altitudes_ft=[10000.0, 5000.0])

    # There are no derived wing scalars left to carry through (note 33).
    assert merged.xtc == 253.364
    assert merged.altitudes_ft == [10000.0, 5000.0]
    assert not hasattr(merged, "cg_cases"), "the case list is owned by WeightInput"
    # The original slice is untouched (merged() returns a new instance).
    assert fl.altitudes_ft == [0.0, 20000.0]


def test_aero_coefficients_input_preserves_flaps_down_on_cruise_edit():
    """The view's write-back pattern (``app/views/flight_envelope.py``): editing
    the cruise set must not drop an existing flaps-down set."""
    landing = AeroCoeffSet(name="LANDING", stall_cl=1.95, neg_stall_cl=-0.59,
                           lift=(0.9, 0.08, 0.0, 0.0, 0.0),
                           drag=(0.08, 0.0, 0.054, 0.0, 0.0),
                           moment=(-0.12, 0.004, 0.0, 0.0, 0.0), flaps_down=True)
    aero = AeroCoefficientsInput(cruise=None, flaps_down=landing)
    edited_cruise = AeroCoeffSet(name="CRUISE", stall_cl=1.45, neg_stall_cl=-0.6,
                                 lift=(0.32, 0.08, 0.0, 0.0, 0.0),
                                 drag=(0.027, 0.0, 0.054, 0.0, 0.0),
                                 moment=(-0.017, 0.004, 0.0, 0.0, 0.0), flaps_down=False)
    updated = AeroCoefficientsInput(cruise=edited_cruise, flaps_down=aero.flaps_down)
    assert updated.cruise.stall_cl == 1.45
    assert updated.flaps_down is landing


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
