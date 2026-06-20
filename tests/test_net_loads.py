"""Net wing loads (Step C3): AIRLOADS air-load distribution + NETLOADS sum.

Oracle-locked against the Appendix A worked example: the air-load distribution
"Airloads for Case 22 PHAA" (p206) and the "Net Loads, Case 22 PHAA" table
(p222) -- the algebraic sum of air and inertia along the 25% chord. The math is
faithful (tau override 0.05 reproduces the manual wing slope), so the printed
integers match; small quantities use an absolute floor. Concept mode has no
oracle and is checked by the net = air + inertia identity and physics closure.

Reference: AIRLOADS.BAS 4500-5060 / NETLOADS.BAS, Ref 1 Ch 12 & 14; Appendix A
p206 (air) and p222 (net).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, io  # noqa: E402
from farloads.modules import net_loads as nl  # noqa: E402
from farloads.modules.airloads import air_load_distribution  # noqa: E402
from farloads.modules.flight_envelope import build_envelope  # noqa: E402
from farloads.modules.net_loads import build_net_loads  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_heavy.project.json")


def _close(a, e, rel=2e-3, abs_=2.0):
    return math.isclose(a, e, rel_tol=rel, abs_tol=abs_)


def test_air_load_distribution_matches_appendix_a():
    # Case 22 PHAA: CL 1.52, V 117.4 KEAS (p206).
    p = io.load_project(_GA)
    r = air_load_distribution(p.geometry.by_name("wing"), p.aero.by_name("wing"),
                              cl=1.52, v_eas_kt=117.4, wrp_waterline=78.5, dihedral_deg=6.0)
    root, tip = r.stations[0], r.stations[-1]
    assert _close(root.fz, 466) and _close(root.fx, -68)
    assert _close(root.sz, 6470) and _close(root.sx, -1126)
    assert _close(root.mxx, 516955) and _close(root.myy, -79003) and _close(root.mzz, -91283)
    assert _close(root.x, 71.628) and _close(root.z, 79.028)
    assert _close(tip.fz, 143) and _close(tip.myy, -198, abs_=2.0)
    # Mid station (Y ~ 105.5).
    mid = r.stations[10]
    assert _close(mid.sz, 2509) and _close(mid.mxx, 97044)


def test_net_loads_case22_matches_appendix_a():
    # Net Loads, Case 22 PHAA (p222) = air + inertia.
    loads = build_net_loads(io.load_project(_GA))
    net = next(r for r in loads.wing_net if r.case == "PHAA")
    root, tip = net.stations[0], net.stations[-1]
    assert _close(root.fx, -68) and _close(root.fz, 466)
    assert _close(root.sx, -1025) and _close(root.sz, 5837)
    assert _close(root.mxx, 455555) and _close(root.myy, -60940) and _close(root.mzz, -81483)
    assert _close(tip.fx, -12, abs_=2.0) and _close(tip.fz, 118)
    assert _close(tip.myy, 85, abs_=3.0)


def test_net_is_air_plus_inertia_identity():
    loads = build_net_loads(io.load_project(_GA))
    air = loads.wing_air[0].stations
    inertia = loads.wing_inertia[0].stations
    net = loads.wing_net[0].stations
    for a, i, n in zip(air, inertia, net):
        assert math.isclose(n.sz, a.sz + i.sz, abs_tol=1e-6)
        assert math.isclose(n.mxx, a.mxx + i.mxx, abs_tol=1e-6)
        assert math.isclose(n.myy, a.myy + i.myy, abs_tol=1e-6)


def test_root_bending_matches_trapezoidal_schrenk():
    # Closure: air-load root bending = trapezoidal integral of the lift distribution.
    p = io.load_project(_GA)
    r = air_load_distribution(p.geometry.by_name("wing"), p.aero.by_name("wing"),
                              cl=1.52, v_eas_kt=117.4, wrp_waterline=78.5, dihedral_deg=6.0)
    st = r.stations
    dy = st[1].y - st[0].y
    # Mxx(root) = sum over strips of (cumulative shear above) * dy; rebuild from Fz.
    bm = 0.0
    shear = 0.0
    for k in range(len(st) - 1, -1, -1):
        shear += st[k].fz
        if k > 0:
            bm += shear * dy
    assert math.isclose(bm, st[0].mxx, rel_tol=2e-3)


def test_concept_net_closure():
    # Concept (no oracle): derive Nz/Nx/CL/V from the V-n point; net = air + inertia.
    p = io.load_project(_CONCEPT)
    p.envelope = build_envelope(p)
    loads = build_net_loads(p)
    net = loads.wing_net[0]
    # Inertia opposes the air load: Nz = -NZ(vn) = -4.0 (concept chosen_n).
    assert math.isclose(net.nz, -4.0, abs_tol=0.01)
    air = loads.wing_air[0].stations[0]
    inertia = loads.wing_inertia[0].stations[0]
    assert math.isclose(net.stations[0].sz, air.sz + inertia.sz, abs_tol=1e-6)
    # Inertia root shear includes the panel mass (~900 lb) + fuel (600 lb) at Nz.
    assert inertia.sz < 0  # downward inertia relief under positive g


def test_wing_load_rows_shape():
    loads = build_net_loads(io.load_project(_GA))
    rows = nl.wing_load_rows(loads.wing_net)
    assert rows and set(rows[0]) == {"Case", "X", "Y", "Z", "Fx", "Fz", "Sx", "Sz", "Mxx", "Myy", "Mzz"}
    assert len(rows) == sum(len(r.stations) for r in loads.wing_net)


def test_run_requires_slices():
    try:
        nl.run(Project(name="empty"))
    except ValueError:
        return
    raise AssertionError("expected ValueError when wing_mass/geometry/aero are missing")


def test_loads_slice_round_trips_through_io():
    p = io.load_project(_GA)
    p.loads = build_net_loads(p)
    rebuilt = io.project_from_dict(io.project_to_dict(p))
    assert rebuilt.loads is not None
    assert rebuilt.loads.wing_net[0].case == "PHAA"
    assert math.isclose(rebuilt.loads.wing_net[0].stations[0].mxx, p.loads.wing_net[0].stations[0].mxx)
    assert len(rebuilt.loads.wing_air) == len(p.loads.wing_air)


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
