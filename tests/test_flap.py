"""Flap loads (Step C8): FLAPLOAD.BAS port (FAR 23.345 / 23.457).

Oracle-locked against the Appendix A "Critical Flap Loads" report p201: the
four-condition flaps-extended envelope (1G/2G stall, 2G at VF, gust at VF) with
the Abbott & von Doenhoff Fig 98 flap-lift build-up, plus the FAR 23.457(b)
momentum-theory slipstream amplification and the FAR 23.345(c)(1) head-on 25 fps
gust.

Reference: FLAPLOAD.BAS (Appendix C p452); Ref 1 Ch 17 p109; oracle Appendix A
p201 (VS 62.2, VSF 58.6, VF 105.48, W 3400, NG 1.9, SF 10.7, SW 184.125, delta 40,
E 0.27, MAXHP 250, BLPROP 68, AF 8.2, PDIA 85 -> CLf 1.7046/1.7046/1.5593/1.5476;
LF 212/424/629/624; critical 629 lb, LE 0.545 psi; slipstream x1.407, BL
22.828..113.172, VSS 125.1; gust x1.301; combined 819 lb).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import io  # noqa: E402
from farloads.modules.flap import build_flap, flap_loads, run  # noqa: E402

REL = 1e-3  # ±0.1%

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _oracle():
    return flap_loads(vs=62.2, vsf=58.6, vf=105.48, weight=3400.0, ng=1.9, sf=10.7,
                      sw=184.125, delta_deg=40.0, e=0.27, maxhp=250.0, pdia_in=85.0,
                      blprop=68.0, af_sqft=8.2)


def test_flap_clf_oracle():
    """The four flap CLs (Appendix A p201)."""
    r = _oracle()
    for got, exp in zip(r.clf, [1.704565, 1.704565, 1.559282, 1.547566]):
        assert math.isclose(got, exp, rel_tol=REL), (got, exp)


def test_flap_critical_load_oracle():
    """Critical flap load 629 lb and leading-edge pressure 0.545 psi (p201)."""
    r = _oracle()
    assert math.isclose(r.critical_lf_lb, 629.0, rel_tol=2e-3), r.critical_lf_lb
    assert math.isclose(r.le_pressure_psi, 0.545, rel_tol=2e-3), r.le_pressure_psi
    # The four flap loads match the printed (INT-truncated) figures within 1 lb.
    for got, exp in zip(r.lf, [212, 424, 629, 624]):
        assert abs(got - exp) <= 1.5, (got, exp)


def test_flap_slipstream_and_gust_oracle():
    """Slipstream band/factor and the head-on-gust combined load (p201)."""
    r = _oracle()
    assert math.isclose(r.slipstream_factor, 1.407, rel_tol=2e-3), r.slipstream_factor
    assert math.isclose(r.slipstream_velocity_kt, 125.1, rel_tol=2e-3), r.slipstream_velocity_kt
    assert math.isclose(r.slipstream_bl_inboard, 22.828, rel_tol=2e-3), r.slipstream_bl_inboard
    assert math.isclose(r.slipstream_bl_outboard, 113.172, rel_tol=2e-3), r.slipstream_bl_outboard
    assert math.isclose(r.gust_factor, 1.301, rel_tol=2e-3), r.gust_factor
    assert math.isclose(r.combined_gust_lb, 819.0, rel_tol=2e-3), r.combined_gust_lb


def test_flap_pipeline():
    """The GA6 example runs FLAPLOAD end-to-end (its engine differs from the manual's
    so the slipstream geometry differs; this checks physics closure + plumbing)."""
    p = io.load_project(_GA)
    mod = run(p)
    assert mod.module == "flap" and len(mod.conditions) == 1
    res = build_flap(p)[0]
    assert res.load_lb > 0 and len(res.stations) == 2
    assert math.isclose(res.stations[1].psi, res.stations[0].psi / 2.0, rel_tol=1e-9)


def test_flap_io_roundtrip():
    """The flap_loads slice round-trips; an older file without it still loads."""
    p = io.load_project(_GA)
    d = io.project_to_dict(p)
    p2 = io.project_from_dict(d)
    assert p2.flap_loads.flap_chord_ratio == 0.27
    assert p2.flap_loads.gust_load_factor == 1.9
    d.pop("flap_loads", None)
    assert io.project_from_dict(d).flap_loads is None


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
