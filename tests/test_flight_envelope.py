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

from farloads import Project, io  # noqa: E402
from farloads.modules import flight_envelope as fe  # noqa: E402
from farloads.modules.flight_envelope import build_envelope, _design_inputs  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_heavy.project.json")


def _by_case(env):
    return {p.case: p for p in env.vn}


def _close(actual, expected, rel=3e-3, abs_=2.0):
    """True within a relative tolerance or an absolute floor (for small numbers)."""
    return math.isclose(actual, expected, rel_tol=rel, abs_tol=abs_)


def test_design_speeds_match_appendix_a():
    di = _design_inputs(io.load_project(_GA))
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
    cg = fl.cg_cases[0]
    p = next(pt for pt in build_envelope(project).vn if pt.condition == "MAN A")
    moment = (p.m_wf + p.lzw * (cg.xcg - fl.xw) - p.dx * (cg.zcg - fl.zw)
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
    assert math.isclose(fl.mac, 69.246)
    assert fl.configurations[0].lift[1] == 0.080358
    assert fl.cg_cases[0].name == "CG1"


def _with_landing():
    # The GA6 project plus a synthetic LANDING configuration (flaps extended): the
    # real landing aero polynomials are not in the repo, so the flapped envelope is
    # validated by closure (NZ achieved, n<=2 maneuver limit), not the printed
    # flaps-extended oracle.
    import copy

    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0]
    cruise = p.flight_loads.configurations[0]
    landing = copy.deepcopy(cruise)
    landing.name = "LANDING"
    landing.flaps_down = True
    landing.stall_cl = 1.9
    landing.neg_stall_cl = -0.8
    p.flight_loads.configurations = [cruise, landing]
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
