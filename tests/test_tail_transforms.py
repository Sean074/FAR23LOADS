"""Direct closure tests for the three empennage local -> airplane maps (CH-3).

Authority: CONVENTIONS.md §7, "Empennage local frame -> airplane axes" (the
h-tail spans ``y``, loads ``fz``, twists ``myy``; the v-tail spans ``z``, loads
``fy``, twists ``mzz``; a span-axis axial load follows the span) and "The T-tail
transfer" (``Fz``/``Myy`` only, in airplane axes, at the fin's tip node). The
torsion sign is not asserted from the code's docstring: it is recomputed here as
``r x F`` about the LRA from a strip geometry, the way the stored strip torsion
``(x_lra - x_load) * normal`` is defined, so the test closes on the mechanics.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads.export.coordinates import (
    tail_axial_to_airplane,
    tail_force_to_airplane,
    tail_torsion_to_airplane,
    ttail_transfer_to_airplane,
)


def _cross(r, f):
    return (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])


@pytest.mark.parametrize("component, expected", [("htail", (0.0, 123.5, 0.0)),
                                                 ("vtail", (0.0, 0.0, 123.5))])
def test_axial_load_follows_the_span_axis(component, expected):
    """CONVENTIONS §7: h-tail span is y, fin span is z; the axial map is that axis."""
    assert tail_axial_to_airplane(123.5, component) == expected
    assert tail_axial_to_airplane(-123.5, component) == tuple(-e for e in expected)


def test_axial_and_normal_maps_are_orthogonal():
    """An axial load must never land on the axis the normal load uses (or on x)."""
    for comp in ("htail", "vtail"):
        a = tail_axial_to_airplane(1.0, comp)
        n = tail_force_to_airplane(1.0, comp)
        assert sum(ai * ni for ai, ni in zip(a, n)) == 0.0
        assert a[0] == 0.0 and n[0] == 0.0


@pytest.mark.parametrize("component", ["htail", "vtail"])
@pytest.mark.parametrize("x_load, x_lra, normal", [(100.0, 110.0, 250.0),
                                                   (130.0, 110.0, 250.0),
                                                   (100.0, 110.0, -80.0)])
def test_torsion_sign_closes_on_r_cross_f(component, x_load, x_lra, normal):
    """The stored strip torsion is (x_lra - x_load) * normal about the surface's own
    span axis. Recompute the airplane moment as r x F about the LRA point (r from
    LRA to load, F the normal load on its §7 axis) and require the map to agree --
    which is what forces the fin's mzz to carry the *negated* stored value."""
    stored = (x_lra - x_load) * normal
    r = (x_load - x_lra, 0.0, 0.0)
    f = tail_force_to_airplane(normal, component)
    expected = _cross(r, f)
    got = tail_torsion_to_airplane(stored, component)
    assert got == pytest.approx(expected)
    # And the axis is the span axis named in §7: myy for the h-tail, mzz for the fin.
    axis = 1 if component == "htail" else 2
    assert got[axis] != 0.0 and all(got[i] == 0.0 for i in range(3) if i != axis)


def test_ttail_transfer_is_fz_and_myy_in_airplane_axes():
    """§7 T-tail transfer: a vertical force and a pitching moment, never a side load
    (the plausible error is routing it through the fin's side-force map)."""
    force, moment = ttail_transfer_to_airplane(fz=-900.0, myy=12000.0)
    assert force == (0.0, 0.0, -900.0)
    assert moment == (0.0, 12000.0, 0.0)
    assert force != tail_force_to_airplane(-900.0, "vtail")  # not a fin side load
    assert force[1] == 0.0 and moment[0] == 0.0 and moment[2] == 0.0  # roll/yaw zero


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

