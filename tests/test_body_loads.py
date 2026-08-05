"""Net fuselage loads (Step C6, R6): the Ch 15 body distribution + sbeam export.

Ch 15 ("Net Fuselage Loads") ships no program and no printed station table, so
the fuselage net distribution is a modern calc validated by **equilibrium
closure**: the applied vertical loads (fuselage inertia + tail air load + wing
carry-through reaction) sum to zero, the running shear returns to zero at the aft
end, the terminal bending `Myy` returns to zero, and the exported FORCE set
re-sums to zero.

Moment closure (M4-1, closed 2026-08-03) follows the two passes of Ref 1 p103:
the terminal moment of the wing-reaction-free set is the unbalanced moment, and
it is reacted at the wing front/rear spar attachments. The closure suite below
locks both residuals, the `d -> 0` collapse onto the manual's literal two-point
solve, the node-count independence of the distributed form, and the flagged
whole-body fallback used when the spar stations are underivable.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.constants import CARRY_THROUGH_NODES  # noqa: E402
from sloads.derived_geometry import CarryThrough, carry_through  # noqa: E402
from sloads.export import sbeam_bridge  # noqa: E402
from sloads.models import FuselageMassInput, FuselageStation, TailLoadsInput  # noqa: E402
from sloads.modules import body_loads  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _project():
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.fuselage_mass = FuselageMassInput(stations=[
        FuselageStation(x=x, weight_lb=w) for x, w in
        [(30, 200), (60, 400), (90, 600), (140, 500), (200, 300), (250, 150)]
    ])
    p.tail_loads = TailLoadsInput(xt25=261.027)
    return p


def _no_wing_project():
    """The same fixture with the wing planform removed, so ``carry_through``
    returns ``None`` and the moment falls back to the whole-body correction.

    The wing area has to be restored on the STRSPEED scalar slice: deleting the
    surface also removes the area the upstream modules read off the planform.
    """
    p = _project()
    p.speeds.wing_area_sqft = 174.0
    p.geometry.surfaces = [s for s in p.geometry.surfaces if s.name != "wing"]
    return p


def _closes(r, rel_tol=1e-9):
    """Both equilibrium residuals of one body result, relative to the loads that
    produced them (an absolute tolerance would be meaningless across cases whose
    peak bending spans 10^5-10^6 lb-in)."""
    scale_f = sum(abs(s.fz) for s in r.stations) or 1.0
    scale_m = max(abs(s.myy) for s in r.stations) or 1.0
    return (abs(sum(s.fz for s in r.stations)) < rel_tol * scale_f
            and abs(r.stations[-1].sz) < rel_tol * scale_f
            and abs(r.stations[-1].myy) < rel_tol * scale_m)


def test_body_distribution_for_each_fuselage_condition():
    res = body_loads.build_body_loads(_project())
    # One distribution per critical fuselage condition (SELECT R5).
    assert {r.case for r in res} == {
        "MAX DOWN LOAD ON WING", "AFT DOWN BENDING", "AFT UP BENDING", "GREATEST NZ"}


def test_body_net_closes_in_equilibrium():
    """The M4-1 closure lock: **both** residuals, on every fuselage condition.

    Ref 1 p103 -- the beam carries no net force and no net couple once the
    unbalanced moment is reacted at the spar attachments. Before M4-1 closed, the
    terminal ``Myy`` here ran to 7.3e4 - 5.5e5 lb-in.
    """
    results = body_loads.build_body_loads(_project())
    assert results
    for r in results:
        assert _closes(r), (
            r.case, sum(s.fz for s in r.stations), r.stations[-1].sz, r.stations[-1].myy)
        assert not r.closure_artifact


def test_spar_reactions_carry_the_unbalanced_moment():
    """``R_f + R_r`` is the vertical residual, and the pair's moment about the
    integrator's reference station recovers ``-M_ub`` (that is the 2x2 solve)."""
    p = _project()
    carry = carry_through(p)
    assert carry is not None
    for r in body_loads.build_body_loads(p):
        r_total = sum(-s.fz for s in r.stations if s.source in ("mass", "tail"))
        assert math.isclose(r.r_front + r.r_rear, r_total, rel_tol=1e-9)
        x_ref = max(s.x for s in r.stations)
        moment = r.r_front * (x_ref - r.x_front) + r.r_rear * (x_ref - r.x_rear)
        assert math.isclose(moment, -r.m_unbalanced, rel_tol=1e-9)
        assert (r.x_front, r.x_rear) == (carry.x_f, carry.x_r)


def test_closure_is_independent_of_the_carry_through_node_count():
    """The linear line load is lumped by its exact static equivalent, so the
    resultant and first moment -- and therefore the closure -- do not depend on
    how many nodes the carry-through is discretized into."""
    for nodes in (2, 3, 5, 9, 33):
        pts = body_loads._linear_load_nodes(60.0, 110.0, 1000.0, 25000.0, nodes=nodes)
        assert len(pts) == nodes
        assert math.isclose(sum(fz for _, fz, _ in pts), 1000.0, rel_tol=1e-12)
        mid = 85.0
        assert math.isclose(sum(fz * (x - mid) for x, fz, _ in pts), 25000.0, rel_tol=1e-12)
    assert CARRY_THROUGH_NODES >= 2


def test_carry_through_collapses_onto_the_two_point_solve_as_d_shrinks():
    """Ref 1 p103 prescribes two point reactions; the distributed form is its
    ``d -> 0`` limit. Shrinking the carry-through must keep the beam closed while
    the reactions grow as ``+/-M_ub/d`` -- which is exactly the shear spike the
    distributed form exists to avoid at a realistic spar spacing."""
    p = _project()
    base = carry_through(p)
    x_mid = 0.5 * (base.x_f + base.x_r)
    prev_span = None
    for d in (base.d, 5.0, 0.5, 0.05):
        carry = CarryThrough(base.surface_name, x_mid - d / 2.0, x_mid + d / 2.0, d,
                             base.front_pct, base.rear_pct, base.assumed)
        rows, info = body_loads.body_distribution(
            [(s.x, s.weight_lb) for s in p.fuselage_mass.stations],
            3.8, 250.0, 261.027, 85.0, carry)
        scale = max(abs(s.myy) for s in rows)
        assert abs(rows[-1].myy) < 1e-9 * scale, (d, rows[-1].myy)
        span = abs(info["r_rear"] - info["r_front"])
        if prev_span is not None:
            assert span > prev_span            # +/- M_ub/d, growing without bound
        prev_span = span


def test_fallback_closes_but_is_flagged_a_closure_artifact():
    """No derivable spar stations -> the whole-body correction. It still closes
    the beam, but it is flagged, reports no fitting loads, and carries the
    caveat onto the deliverable."""
    results = body_loads.build_body_loads(_no_wing_project())
    assert results
    for r in results:
        assert r.closure_artifact
        assert _closes(r)
        assert r.r_front is None and r.r_rear is None
        assert r.m_unbalanced != 0.0        # the moment it had to cancel is still reported
    assert body_loads.fitting_load_rows(results) == []
    cards = sbeam_bridge.body_force_moment_cards(results)
    assert "$ CAVEAT:" in cards
    assert sbeam_bridge.body_fitting_load_csv(results).strip().count("\n") == 0  # header only


def test_body_load_rows_shape():
    rows = body_loads.body_load_rows(body_loads.build_body_loads(_project()))
    assert rows and set(rows[0]) == {"Case", "X", "Fz", "Sz", "Myy", "Basis"}
    # The basis travels in-band with every row (defect M4-15).
    assert all(r["Basis"] == "LIMIT" for r in rows)


def test_sbeam_body_export_force_set_sums_to_zero():
    res = body_loads.build_body_loads(_project())
    cards = sbeam_bridge.body_force_moment_cards(res)
    assert "FORCE" in cards
    # Re-sum the Fz of every FORCE card in the first load set: must close to ~0.
    # The tolerance is relative to the load magnitude on the cards -- the cards
    # carry 6 significant digits (_fmt), so a set of ~10^4 lb loads re-sums to
    # ~10^-3 lb of print rounding, not of calc error.
    fz = [float(ln.split(",")[-1]) for ln in cards.splitlines() if ln.startswith("FORCE, 1,")]
    assert math.isclose(sum(fz), 0.0, abs_tol=1e-5 * sum(abs(f) for f in fz))


def test_sbeam_body_span_csv():
    csv_text = sbeam_bridge.body_span_load_csv(body_loads.build_body_loads(_project()))
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    # Unit-and-ULT-marked headers since M4-20 step 4 (was bare "X,Fz,Sz,Myy").
    assert lines[0] == "Case,GID,X (in),Fz (lbs-ULT),Sz (lbs-ULT),Myy (lb-in-ULT),SF"
    assert len(lines) > 1


def test_body_bdf_ships_no_caveat_on_the_carry_through_path():
    """M4-1 closed: a set reacted at the spar attachments carries no caveat.

    The old lock asserted the opposite (every set stated the open ΣM limitation).
    It is inverted here: the caveat now belongs only to the whole-body fallback,
    which ``test_body_bdf_flags_the_closure_artifact`` covers. The assumed-spar
    provenance still ships on every card block.
    """
    results = body_loads.build_body_loads(_project())
    assert all(not r.closure_artifact for r in results)
    cards = sbeam_bridge.body_force_moment_cards(results)
    assert "$ CAVEAT:" not in cards
    # The spar stations were not entered, so every block says so (decision 2).
    assert len([ln for ln in cards.splitlines()
                if "spar stations ASSUMED" in ln]) == len(results)
    # Each block states both closure residuals.
    assert len([ln for ln in cards.splitlines()
                if "moment equilibrium" in ln]) == len(results)
    # Every comment line stays inside the free-field card width.
    assert all(len(ln) <= 72 for ln in cards.splitlines() if ln.startswith("$"))


def test_body_gids_are_stable_when_the_spar_stations_move():
    """GIDs key off ``BodyStationLoad.source``, not the station's index in the
    merged table: the carry-through inserts reaction nodes into the *middle* of
    the beam, and index-based GIDs would have silently renumbered every mass
    station aft of the wing whenever a spar fraction changed."""
    p = _project()
    r = body_loads.build_body_loads(p)[0]
    mass_gids = {s.x: g for s, g in zip(r.stations, sbeam_bridge.body_station_gids(r))
                 if s.source != "carry"}
    # A carry node lands between mass stations, so the interleaving is real.
    gids = sbeam_bridge.body_station_gids(r)
    assert any(a > b for a, b in zip(gids, gids[1:]))

    wing = p.geometry.by_name("wing")
    wing.front_spar_pct, wing.rear_spar_pct = 0.20, 0.70
    r2 = body_loads.build_body_loads(p)[0]
    moved = {s.x: g for s, g in zip(r2.stations, sbeam_bridge.body_station_gids(r2))
             if s.source != "carry"}
    assert moved == mass_gids
    assert not r2.spars_assumed and r.spars_assumed


def test_body_gid_blocks_are_disjoint():
    """Mass/tail stations keep the historical 1001+ numbering; reaction nodes
    take their own 1501+ block, below the tail family's 2001."""
    r = body_loads.build_body_loads(_project())[0]
    for s, gid in zip(r.stations, sbeam_bridge.body_station_gids(r)):
        if s.source in ("carry", "correction"):
            assert 1501 <= gid < 2001
        else:
            assert 1001 <= gid < 1501
    assert len(set(sbeam_bridge.body_station_gids(r))) == len(r.stations)


def test_body_fitting_load_csv_is_ultimate():
    """The wing-attach fitting loads ship as their own ULTIMATE CSV -- not in the
    FORCE set, which already carries them as the carry-through distribution."""
    results = body_loads.build_body_loads(_project())
    lines = sbeam_bridge.body_fitting_load_csv(results).strip().splitlines()
    # The force marker is the renderer's ``lbs-ULT`` since M4-20 step 4; this
    # file used to be the only deliverable spelling it ``lb-ULT``.
    assert lines[0].split(",") == [
        "Case", "Case ID", "X front (in)", "R front (lbs-ULT)", "X rear (in)",
        "R rear (lbs-ULT)", "M unbalanced (lb-in-ULT)", "Spars", "SF"]
    assert len(lines) == len(results) + 1
    row = dict(zip(lines[0].split(","), lines[1].split(",")))
    r = results[0]
    sf = r.safety_factor
    assert math.isclose(float(row["R front (lbs-ULT)"]), r.r_front * sf, rel_tol=1e-4)
    assert math.isclose(float(row["R rear (lbs-ULT)"]), r.r_rear * sf, rel_tol=1e-4)
    assert row["SF"] == f"{sf:g}" and row["Spars"] == "assumed"
    # Stations are geometry, never scaled by the limit->ultimate factor.
    assert math.isclose(float(row["X front (in)"]), r.x_front, rel_tol=1e-9)


def test_moment_closure_fields_round_trip_through_io():
    """The new ``BodyLoadResult`` fields (and the station ``source`` the export
    keys its GIDs off) survive save/load -- schema v35."""
    import tempfile

    from sloads.models import LoadsResult

    p = _project()
    results = body_loads.build_body_loads(p)
    p.loads = LoadsResult(body_net=results)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "p.json")
        io.save_project(p, path)
        back = io.load_project(path)
    got, want = back.loads.body_net[0], results[0]
    for f in ("m_unbalanced", "r_front", "r_rear", "x_front", "x_rear"):
        assert math.isclose(getattr(got, f), getattr(want, f), rel_tol=1e-9), f
    assert got.spars_assumed == want.spars_assumed
    assert got.closure_artifact == want.closure_artifact
    assert [s.source for s in got.stations] == [s.source for s in want.stations]


def test_run_requires_fuselage_mass():
    # GA6 now ships a fuselage_mass slice (M2R-3), so clear it here to exercise
    # the missing-slice guard directly rather than relying on the fixture's gaps.
    project = io.load_project(_GA)
    project.fuselage_mass = None
    raised = False
    try:
        body_loads.run(project)
    except ValueError:
        raised = True
    assert raised


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
