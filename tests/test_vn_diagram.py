"""Unit tests for the pure V-n diagram builder (``farloads.vn_diagram``).

These are physics-closure checks (no printed oracle): the stall boundary is the
parabola through (VS, 1) and the manoeuvre corner, the flaps-down envelope is
capped at n=2.0 (14 CFR 23.337(b)), and the gust line is linear through (0, 1).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import build_vn_diagram, resolve_gust_inputs
from farloads.vn_diagram import GustInputs, gust_load_factor

TOL = 1e-6


def _trace(diagram, name):
    for t in diagram.traces:
        if t.name == name:
            return t
    raise KeyError(name)


def test_clean_envelope_corners_match_inputs():
    # VA consistent with VS and n_pos: VA = VS*sqrt(n_pos).
    vs, n_pos, n_neg = 65.0, 3.8, -1.52
    va = vs * math.sqrt(n_pos)
    d = build_vn_diagram(vs=vs, va=va, vc=170.0, vd=212.5, n_pos=n_pos, n_neg=n_neg)
    t = _trace(d, "Manoeuvre (flaps up)")
    # The positive stall boundary passes through (VS, 1).
    i0 = t.v.index(min(t.v))
    assert math.isclose(t.v[i0], vs, rel_tol=1e-9)
    assert math.isclose(t.n[i0], 1.0, rel_tol=1e-6)
    # Top load factor is exactly n_pos; bottom is n_neg.
    assert math.isclose(max(t.n), n_pos, rel_tol=1e-9)
    assert math.isclose(min(t.n), n_neg, rel_tol=1e-9)


def test_stall_boundary_is_parabolic():
    vs, n_pos = 60.0, 4.0
    va = vs * math.sqrt(n_pos)
    d = build_vn_diagram(vs=vs, va=va, vc=150.0, vd=190.0, n_pos=n_pos, n_neg=-1.6)
    t = _trace(d, "Manoeuvre (flaps up)")
    # Every point on the rising (positive, V<=VA) stall branch satisfies n=(V/VS)^2.
    for v, n in zip(t.v, t.n):
        if 0 < n < n_pos and v <= va + TOL:
            assert math.isclose(n, (v / vs) ** 2, rel_tol=1e-6, abs_tol=1e-6)


def test_flap_envelope_capped_at_2g():
    d = build_vn_diagram(vs=65.0, va=126.0, vc=170.0, vd=212.5, n_pos=3.8, n_neg=-1.52,
                         vsf=55.0, vf=105.5, flaps="down")
    t = _trace(d, "Manoeuvre (flaps down)")
    assert math.isclose(max(t.n), 2.0, rel_tol=1e-9)
    assert min(t.n) >= 0.0


def test_flap_envelope_below_2g_when_vf_low():
    # VF below the 2 g corner speed (VSF*sqrt(2)) -> the top is the stall value at VF.
    vsf, vf = 60.0, 75.0
    d = build_vn_diagram(vs=60.0, va=120.0, vc=170.0, vd=210.0, n_pos=3.8, n_neg=-1.52,
                         vsf=vsf, vf=vf, flaps="down")
    t = _trace(d, "Manoeuvre (flaps down)")
    assert math.isclose(max(t.n), (vf / vsf) ** 2, rel_tol=1e-6)
    assert max(t.n) < 2.0


def test_flaps_both_includes_two_envelopes():
    d = build_vn_diagram(vs=65.0, va=126.0, vc=170.0, vd=212.5, n_pos=3.8, n_neg=-1.52,
                         vsf=55.0, vf=105.5, flaps="both")
    names = {t.name for t in d.traces}
    assert "Manoeuvre (flaps up)" in names
    assert "Manoeuvre (flaps down)" in names


def test_gust_line_linear_through_origin_load():
    gust = resolve_gust_inputs(ws=25.0, altitude_ft=0.0, lift_slope_per_deg=0.0765, mac_ft=4.9)
    d = build_vn_diagram(vs=65.0, va=126.0, vc=170.0, vd=212.5, n_pos=3.8, n_neg=-1.52,
                         gust=gust)
    up = _trace(d, "Gust up @ VC (C)")
    assert up.v == [0.0, 170.0]
    assert math.isclose(up.n[0], 1.0, rel_tol=1e-9)   # anchored at n=1 at V=0
    assert up.n[1] > 1.0                              # up-gust raises n
    down = _trace(d, "Gust down @ VC (C)")
    assert down.n[1] < 1.0                            # down-gust lowers n
    # Symmetric about n=1.
    assert math.isclose(up.n[1] - 1.0, 1.0 - down.n[1], rel_tol=1e-9)


def test_gust_missing_mac_flagged_approximate():
    g = resolve_gust_inputs(ws=25.0, altitude_ft=0.0, lift_slope_per_deg=None, mac_ft=None)
    assert g.approximate
    d = build_vn_diagram(vs=65.0, va=126.0, vc=170.0, vd=212.5, n_pos=3.8, n_neg=-1.52, gust=g)
    assert d.gust_approximate
    # Kg falls back to 1.0 (no alleviation) when MAC is unknown.
    n_no_mac = gust_load_factor(170.0, "C", g, 1.0)
    n_with_mac = gust_load_factor(170.0, "C", GustInputs(25.0, 0.0, g.lift_slope_per_deg, 4.9), 1.0)
    assert n_no_mac > n_with_mac  # alleviation reduces the increment


def test_up_selects_clean_only():
    d = build_vn_diagram(vs=65.0, va=126.0, vc=170.0, vd=212.5, n_pos=3.8, n_neg=-1.52,
                         vsf=55.0, vf=105.5, flaps="up")
    names = {t.name for t in d.traces}
    assert names == {"Manoeuvre (flaps up)"}


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
