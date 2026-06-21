"""Aileron loads (Step C8): AILERON.BAS port (FAR 23.349 / 23.455 / CAM 3.222).

Oracle-locked against the Appendix A "Critical Aileron Loads" report p200: the
deflected-aileron load ``LAIL = 0.04*DEFL*SA*V^2/295`` evaluated at the rolling
schedule (full at VA, ``(VA/VC)*DEFL`` at VC, ``0.5*(VA/VD)*DEFL`` at VD) with the
largest up/down loads selected, plus the constant forward-of-hinge pressure
``W = LAIL/(SAFWD + 0.5*SAAFT)``.

Reference: AILERON.BAS (Appendix C p450); Ref 1 Ch 16 p105; oracle Appendix A p200
(VA/VC/VD 121/170/213; down 15 / up -10 deg; SAFWD 1.3 / SAAFT 5.188 -> down
271.44 lb / up -180.96 lb @170 kt; pressure +0.484 / -0.323 lb/in^2).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import io  # noqa: E402
from farloads.modules.aileron import aileron_loads, build_aileron, run  # noqa: E402

REL = 1e-3  # ±0.1%

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def test_aileron_oracle():
    """Appendix A p200 with the manual's exact entered speeds (121/170/213)."""
    r = aileron_loads(121.0, 170.0, 213.0, 15.0, 10.0, 1.3, 5.188)
    assert math.isclose(r.down_load_lb, 271.44, rel_tol=REL), r.down_load_lb
    assert math.isclose(r.up_load_lb, -180.96, rel_tol=REL), r.up_load_lb
    assert r.down_speed_kt == 170.0 and r.up_speed_kt == 170.0
    assert math.isclose(r.down_pressure_psi, 0.484, rel_tol=2e-3), r.down_pressure_psi
    assert math.isclose(r.up_pressure_psi, -0.323, rel_tol=2e-3), r.up_pressure_psi


def test_aileron_pipeline():
    """The GA6 example flows STRSPEED VA/VC/VD into AILERON (VA ~ 121.3 computed)."""
    p = io.load_project(_GA)
    results = build_aileron(p)
    assert [r.case for r in results] == ["down aileron", "up aileron"]
    down = results[0]
    # Computed VA = 121.3 (vs the manual's rounded 121) shifts the load ~0.3%.
    assert math.isclose(down.load_lb, 271.44, rel_tol=4e-3), down.load_lb
    assert down.v_kt == 170.0
    # Chordwise profile: constant LE->hinge, zero at TE; three stations.
    assert len(down.stations) == 3
    assert down.stations[-1].psi == 0.0
    mod = run(p)
    assert mod.module == "aileron" and len(mod.conditions) == 1


def test_aileron_io_roundtrip():
    """The aileron_loads slice round-trips; an older file without it still loads."""
    p = io.load_project(_GA)
    d = io.project_to_dict(p)
    p2 = io.project_from_dict(d)
    assert p2.aileron_loads.area_aft_hinge_sqft == 5.188
    assert p2.aileron_loads.down_deflection_deg == 15.0
    d.pop("aileron_loads", None)
    p3 = io.project_from_dict(d)
    assert p3.aileron_loads is None


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
