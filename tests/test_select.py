"""Critical wing-load selection (Step C6): SELECT.BAS port.

The FAR23 path is oracle-locked against the Appendix A "Critical Wing Loads"
summary in the 6-place loads report. SELECT searches the balanced V-n matrix
(FLTLOADS, cruise, CGs 1-4, altitudes 0 / 12000 / 18000 ft) for the governing
wing condition of each design point:

    CASE  ANGLE   CL       V KEAS   CG    ALT     COND       FAR
     22   PHAA    +1.519   117.40   CG2      0    STALL +N   23.333(b)
    145   PLAA    +0.472   212.40   CG2  12000    MAN D      23.333(b)
    150   PMAA    +0.810   170.00   CG2  12000    GUST +C    23.333(c)or(b)
    173   NMAA    -0.433   170.00   CG3  12000    GUST -C    23.333(c)or(b)
    160   ACRL    +1.328   116.00   CG2  12000    AC ROLL    23.349(a)(2)
    138   TORS    +0.470   170.00   CG1  12000    ST ROL C   23.349(b)

(The 6-place loads report uses full-down aileron = 15 deg and basic-airfoil
cm = -0.03 for the steady-roll torsion search.) Our renumbered envelope assigns
different integer case numbers, so the regression asserts the selected
*condition*, CL and V (the V-n oracle) -- not the manual's case index.

Reference: SELECT.BAS (Appendix C, lines ~2990-3540), Ref 1 Ch 9; Appendix A
loads report "Critical Wing Loads".
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, SelectInput, io  # noqa: E402
from farloads.modules import select  # noqa: E402
from farloads.modules.flight_envelope import build_envelope  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _ga6_three_altitudes() -> Project:
    """The 6-place GA project with the Appendix A altitude set (0/12000/18000 ft)
    and the loads-report steady-roll inputs."""
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.select_input = SelectInput(full_down_aileron_deg=15.0, basic_airfoil_cm=-0.03)
    return p


def _by_label(project: Project):
    cls = select.build_critical(project)
    by_label = {c.label: c for c in cls.conditions}
    vn = {v.case: v for v in build_envelope(project).vn}
    return by_label, vn


def _vals(cond):
    return {lv.label: lv.value for lv in cond.loads}


def test_critical_wing_conditions_match_appendix_a():
    p = _ga6_three_altitudes()
    by_label, vn = _by_label(p)
    # (label, source V-n condition, CL, V KEAS) from the Appendix A summary.
    expect = [
        ("PHAA", "STALL +N", 1.519, 117.40),
        ("PLAA", "MAN D", 0.472, 212.40),
        ("PMAA", "GUST +C", 0.810, 170.00),
        ("NMAA", "GUST -C", -0.433, 170.00),
        ("ACRL", "AC ROLL", 1.328, 116.00),
        ("TORS", "ST ROL C", 0.470, 170.00),
    ]
    assert set(by_label) == {lbl for lbl, *_ in expect}
    for label, cond_name, cl, v in expect:
        c = by_label[label]
        assert vn[c.case].condition == cond_name, (label, vn[c.case].condition)
        vals = _vals(c)
        # SELECT carries the CL/V the FLTLOADS balance produced; the AoA iteration
        # converges NZ only to +-0.005 (flight_envelope.py), so the selected CL
        # inherits ~0.5% noise -- the FLTLOADS oracle tolerance, not 0.1%.
        assert math.isclose(vals["CL"], cl, rel_tol=5e-3, abs_tol=3e-3), (label, vals["CL"], cl)
        assert math.isclose(vals["V (EAS)"], v, rel_tol=2e-3), (label, vals["V (EAS)"], v)


def test_phaa_is_positive_high_aoa_at_limit_n():
    # PHAA is the positive-high-angle-of-attack stall corner at the limit load
    # factor (Appendix A: NZ +3.8).
    p = _ga6_three_altitudes()
    by_label, _ = _by_label(p)
    assert math.isclose(_vals(by_label["PHAA"])["Load factor NZ"], 3.80, abs_tol=0.01)
    assert _vals(by_label["NMAA"])["Load factor NZ"] < 0      # down load
    assert _vals(by_label["PMAA"])["CL"] > 0


def test_select_far23_far_references():
    p = _ga6_three_altitudes()
    by_label, _ = _by_label(p)
    assert by_label["PHAA"].far_reference == "23.333(b)"
    assert by_label["ACRL"].far_reference == "23.349(a)(2)"
    assert by_label["TORS"].far_reference == "23.349(b)"
    assert all(c.component == "wing" for c in by_label.values())


def test_run_returns_module_result():
    p = _ga6_three_altitudes()
    result = select.run(p)
    assert result.module == "select"
    assert len(result.conditions) == 6
    assert result.conditions[0].far_reference  # FAR cite rendered


def test_critical_set_round_trips_through_io():
    p = _ga6_three_altitudes()
    p.envelope = build_envelope(p)
    p.envelope.critical = select.build_critical(p)
    rebuilt = io.project_from_dict(io.project_to_dict(p))
    assert rebuilt.envelope.critical is not None
    labels = {c.label for c in rebuilt.envelope.critical.conditions}
    assert labels == {"PHAA", "PLAA", "PMAA", "NMAA", "ACRL", "TORS"}


def test_select_uses_persisted_envelope_when_present():
    # When Project.envelope is already populated, SELECT searches it directly
    # rather than rebuilding from flight_loads.
    p = _ga6_three_altitudes()
    p.envelope = build_envelope(p)
    p.flight_loads = None  # force the persisted-envelope path
    cls = select.build_critical(p)
    assert len(cls.conditions) == 6


def test_concept_flag_in_report():
    p = _ga6_three_altitudes()
    p.speeds.category = "C"
    p.speeds.chosen_n = 4.0
    p.speeds.chosen_nneg = -2.0
    result = select.run(p)
    assert any("Concept mode" in c.note for c in result.conditions)


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
