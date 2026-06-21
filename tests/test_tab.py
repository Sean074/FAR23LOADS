"""Tab loads (Step C8): TABLOADS.BAS port (FAR 23.409 / CAM 3.224).

Oracle-locked against the Appendix A "Tab Loads" report p202: full tab deflection
at VC, ``LTAB = 0.0446*(1-E)*delta*Q*STAB/144`` with ``E = MACTAB/CAIRFOIL`` and a
trapezoidal chordwise distribution (LE = 2x TE).

Reference: TABLOADS.BAS (Appendix C p490); Ref 1 Ch 18 p113; oracle Appendix A p202
(h-tail tab: VC 170, MACTAB 7.478, STAB 226, CAIRFOIL 42.166, delta 15 -> E
0.17735, LTAB 84.62 lb, LE 0.4992 / TE 0.2496 lb/in^2).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import io  # noqa: E402
from farloads.modules.tab import build_tabs, run, tab_load  # noqa: E402

REL = 1e-3  # ±0.1%

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def test_tab_oracle():
    """Appendix A p202 horizontal-tail tab."""
    r = tab_load(170.0, 7.478, 226.0, 42.166, 15.0)
    assert math.isclose(r.chord_ratio, 0.17735, rel_tol=REL), r.chord_ratio
    assert math.isclose(r.load_lb, 84.618, rel_tol=REL), r.load_lb
    assert math.isclose(r.le_pressure_psi, 0.49922, rel_tol=REL), r.le_pressure_psi
    assert math.isclose(r.te_pressure_psi, 0.24961, rel_tol=REL), r.te_pressure_psi


def test_tab_pipeline():
    """The GA6 example carries one h-tail tab; VC comes from speeds (170)."""
    p = io.load_project(_GA)
    results = build_tabs(p)
    assert len(results) == 1
    t = results[0]
    assert t.surface == "tab:htail" and t.v_kt == 170.0
    assert math.isclose(t.load_lb, 84.618, rel_tol=REL), t.load_lb
    # Trapezoid LE = 2x TE.
    assert math.isclose(t.stations[0].psi, 2.0 * t.stations[1].psi, rel_tol=1e-9)
    mod = run(p)
    assert mod.module == "tab" and len(mod.conditions) == 1


def test_tab_io_roundtrip():
    """The tab_loads slice (nested tabs) round-trips; older files load without it."""
    p = io.load_project(_GA)
    d = io.project_to_dict(p)
    p2 = io.project_from_dict(d)
    assert len(p2.tab_loads.tabs) == 1
    assert p2.tab_loads.tabs[0].area_sqin == 226.0
    assert p2.tab_loads.tabs[0].surface == "htail"
    d.pop("tab_loads", None)
    assert io.project_from_dict(d).tab_loads is None


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
