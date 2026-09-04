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

from sloads import Project, io
from sloads.modules import net_loads as nl
from sloads.modules.airloads import air_load_distribution
from sloads.modules.flight_envelope import build_envelope
from sloads.modules.net_loads import build_net_loads

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
    assert rows and set(rows[0]) == {"Case", "X", "Y", "Z", "Fx", "Fz", "Sx", "Sz",
                                     "Mxx", "Myy", "Mzz", "MyyAxis", "Basis"}
    assert len(rows) == sum(len(r.stations) for r in loads.wing_net)
    # The basis and the torsion reference axis travel in-band with every row
    # (defect M4-15 pattern).
    assert all(r["Basis"] == "LIMIT" for r in rows)
    assert all(r["MyyAxis"] == "25% chord" for r in rows)


def test_loads_ref_axis_transfer():
    """Torsion transfer to the LRA: identity at 25%, Sz x axis-shift elsewhere."""
    from sloads.modules.wing_geometry import interp_x

    p = io.load_project(_GA)
    loads = build_net_loads(p)
    wing = p.geometry.by_name(p.wing_mass.surface)

    # Unset axis -> the effective 25% chord: bitwise no-op, oracle reporting
    # unchanged. (The fixture enters 0.40 since step 12/R-7a, so the unset
    # branch is exercised by clearing it.)
    assert wing.ref_axis_pct == 0.40
    wing.ref_axis_pct = None
    same = nl.to_loads_ref_axis(loads.wing_net, wing)
    assert same[0] is loads.wing_net[0]
    assert same[0].torsion_axis == "25% chord"

    # LRA at 40% chord: station x moves 0.15*chord aft, Myy shifts by Sz*dx;
    # shears and bending are untouched.
    wing.ref_axis_pct = 0.40
    moved = nl.to_loads_ref_axis(loads.wing_net, wing)
    for r0, r1 in zip(loads.wing_net, moved):
        assert r1.torsion_axis == "LRA 40% chord"
        assert r1.safety_factor == r0.safety_factor and r1.case == r0.case
        for s0, s1 in zip(r0.stations, r1.stations):
            chord = interp_x(wing.trailing_edge, s0.y) - interp_x(wing.leading_edge, s0.y)
            assert math.isclose(s1.x - s0.x, 0.15 * chord, rel_tol=1e-9, abs_tol=1e-6)
            assert math.isclose(s1.myy, s0.myy + s0.sz * (s1.x - s0.x), abs_tol=1e-6)
            assert s1.sz == s0.sz and s1.sx == s0.sx
            assert s1.mxx == s0.mxx and s1.mzz == s0.mzz and s1.fz == s0.fz


def test_run_labels_torsion_axis():
    """Every reported root torsion names its axis; the LRA value appears when set."""
    p = io.load_project(_GA)
    p.geometry.by_name(p.wing_mass.surface).ref_axis_pct = None
    labels = [v.label for v in nl.run(p).conditions[0].values]
    assert "Root torsion Myy (25% chord)" in labels
    assert not any("LRA" in label for label in labels)

    p.geometry.by_name(p.wing_mass.surface).ref_axis_pct = 0.45
    labels = [v.label for v in nl.run(p).conditions[0].values]
    assert "Root torsion Myy (25% chord)" in labels        # oracle-traceable value stays
    assert "Root torsion Myy (LRA 45% chord)" in labels    # LRA deliverable value added


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


# --------------------------------------------------------------------------- #
# The applied set closes onto the cumulative one (OR-15 admission, 2026-09-03)
# --------------------------------------------------------------------------- #
_BARON = os.path.join(_EXAMPLES, "baron_58.project.json")


def _reaccumulate(result):
    """Rebuild the cumulative loads from the applied ones, tip inboard.

    The relations section 3.2 of the oracle report prints, executed. Nothing
    here reads a cumulative field: if the applied set is short of a load, the
    totals come out short and the comparison fails, which is the whole point.
    """
    s = result.stations
    h = len(s)
    dy = s[1].y - s[0].y
    sz = [0.0] * h
    sx = [0.0] * h
    mxx = [0.0] * h
    myy = [0.0] * h
    sz[h - 1] = s[h - 1].fz
    sx[h - 1] = s[h - 1].fx
    myy[h - 1] = s[h - 1].myy_free
    for i in range(h - 2, -1, -1):
        sz[i] = sz[i + 1] + s[i].fz
        sx[i] = sx[i + 1] + s[i].fx
        mxx[i] = mxx[i + 1] + sz[i + 1] * dy
        myy[i] = (myy[i + 1] - sz[i + 1] * (s[i + 1].x - s[i].x)
                  + sx[i + 1] * (s[i + 1].z - s[i].z) + s[i].myy_free)
    # A concentrated mass is a point force: it enters every station inboard of
    # it, once, through the arms its own coordinates state.
    for pl in result.point_loads:
        for i in range(h):
            if s[i].y < pl.y:
                sz[i] += pl.fz
                sx[i] += pl.fx
                mxx[i] += pl.fz * (pl.y - s[i].y)
                myy[i] += -pl.fz * (pl.x - s[i].x) + pl.fx * (pl.z - s[i].z)
    return sz, sx, mxx, myy


def _assert_closes(result, tol=1e-6):
    sz, sx, mxx, myy = _reaccumulate(result)
    for i, station in enumerate(result.stations):
        for got, name in ((sz[i], "sz"), (sx[i], "sx"),
                          (mxx[i], "mxx"), (myy[i], "myy")):
            want = getattr(station, name)
            assert abs(got - want) <= tol * max(1.0, abs(want)), (
                f"{result.case} station {i} {name}: applied set gives {got}, "
                f"published cumulative is {want}")


def test_the_applied_strip_set_reproduces_the_cumulative_loads():
    """Fz, Fx and myy_free, summed tip inboard, ARE the published Sz/Sx/Mxx/Myy.

    The gate under the oracle report's Appendix B, which hands this set to a
    structural model. A model is given applied loads and returns the internal
    ones; if the two do not agree here they will not agree there either, and
    the disagreement would be invisible in a table of numbers that all look
    plausible.
    """
    p = io.load_project(_GA)
    net = build_net_loads(p)
    assert net.wing_net
    for result in net.wing_net:
        _assert_closes(result)


def test_a_concentrated_wing_mass_is_published_as_its_own_applied_load():
    """The Baron carries four; without them the applied set is short by all of them.

    ``WINGINER`` steps the cumulative shear at each concentrated mass and leaves
    the per-strip fz panel-only, so the strip table alone misses -4821.5 lb of
    the -5004.1 lb PHAA root shear -- most of the inertia relief, and
    unconservative in exactly the direction that matters.
    """
    p = io.load_project(_BARON)
    net = build_net_loads(p)
    phaa = next(r for r in net.wing_net if r.case == "PHAA")
    assert len(phaa.point_loads) == 4, "the four entered wing masses"
    _assert_closes(phaa)

    strips_only = sum(s.fz for s in phaa.stations)
    with_points = strips_only + sum(pl.fz for pl in phaa.point_loads)
    assert math.isclose(with_points, phaa.stations[0].sz, rel_tol=1e-9)
    assert abs(strips_only - phaa.stations[0].sz) > 4000.0, (
        "the strip set alone must be visibly short, or this guards nothing")


def test_a_point_mass_carries_no_free_moment():
    """Its every moment is its force through an arm the coordinates already state.

    Asserted because the appendix prints a zero there, and a zero a reader
    cannot distinguish from an unpopulated field is worth nothing.
    """
    p = io.load_project(_BARON)
    for result in build_net_loads(p).wing_net:
        for pl in result.point_loads:
            assert not hasattr(pl, "myy"), "a point mass has no moment field"
            assert pl.name, "each point load names the mass it came from"


def test_the_published_free_moment_matches_balances_own_recovery():
    """Two owners of the free moment agree -- on the air loads, where both work.

    ``balance._free_moments`` reconstructs it by undoing the sweep and dihedral
    transfer from the cumulative column, which is exact for an air load and
    **wrong** once a concentrated mass steps the shear: the step is not a
    transfer, so it lands in the recovered free moment as a spurious term. The
    published field is therefore the owner for anything that must work on a net
    result; this guards the two against drift where they overlap.
    """
    from sloads.modules.balance import _free_moments

    for path in (_GA, _BARON):
        for result in build_net_loads(io.load_project(path)).wing_air:
            recovered = _free_moments(result)
            for i, station in enumerate(result.stations):
                assert math.isclose(recovered[i], station.myy_free,
                                    rel_tol=1e-6, abs_tol=1e-6)


def test_the_axis_transfer_moves_the_free_moment_on_its_own_force():
    """A strip's free moment shifts by fz*dx; the cumulative one by sz*dx.

    Same shift, two different lever populations -- and getting it wrong would
    put a plausible number in the appendix that no gate elsewhere would catch.
    """
    p = io.load_project(_GA)
    p.geometry.by_name(p.wing_mass.surface).ref_axis_pct = 0.40
    raw = build_net_loads(p).wing_net
    moved = nl.loads_ref_axis_results(p, raw)
    for before, after in zip(raw, moved):
        for a, b in zip(before.stations, after.stations):
            assert math.isclose(b.myy_free - a.myy_free, a.fz * (b.x - a.x),
                                rel_tol=1e-9, abs_tol=1e-6)
        assert [pl.fz for pl in after.point_loads] == [pl.fz for pl in before.point_loads], (
            "a point load is a force at a point; moving the axis does not move it")


def test_point_loads_survive_the_io_round_trip():
    p = io.load_project(_BARON)
    p.loads = build_net_loads(p)
    rebuilt = io.project_from_dict(io.project_to_dict(p))
    before = p.loads.wing_net[0].point_loads
    after = rebuilt.loads.wing_net[0].point_loads
    assert len(after) == len(before) == 4
    assert [c.name for c in after] == [c.name for c in before]
    assert math.isclose(after[0].fz, before[0].fz)


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
