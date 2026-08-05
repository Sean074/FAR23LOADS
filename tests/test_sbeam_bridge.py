"""sbeam export bridge (Step C4): span-load CSV + FORCE/MOMENT cards + stick model.

Concept mode has no printed oracle, so the bridge is validated by *closure*: the
exported FORCE set sums to the NETLOADS root shear, the MOMENT(My) set to the
root torsion, and the FORCE moments about the root reproduce the root bending --
all by the increment construction in ``sbeam_bridge``. The cards are re-parsed by
a self-contained free-field reader (no sbeam dependency) and re-summed. Stick-deck
structure (one root clamp, a CBAR chain, one load set per case) is checked too.

The "deck parses and solves in sbeam" deliverable is verified manually against
the real sbeam parser/solver and recorded in the C4 history entry.

Reference: card style sbeam/results/load_export.py; NASTRAN FORCE/MOMENT/GRID/
CBAR/PBAR/MAT1/SPC1 cards.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.modules.net_loads import build_net_loads  # noqa: E402
from helpers import parse_cards  # noqa: E402  (shared free-field reader)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_heavy.project.json")


def _wing_net(path):
    p = io.load_project(path)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    return build_net_loads(p).wing_net


# --------------------------------------------------------------------------- #
# Nodal-load closure (the core guarantee)
# --------------------------------------------------------------------------- #
# The bridge exports ULTIMATE loads (limit x SF); closure holds against SF x root.
_SF = sb._SF


def test_nodal_loads_sum_to_root_totals():
    for r in _wing_net(_GA):
        nodes = sb.wing_nodal_loads(r)
        root = r.stations[0]
        y0 = nodes[0].y
        assert math.isclose(sum(n.fz for n in nodes), root.sz * _SF, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.fx for n in nodes), root.sx * _SF, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.my for n in nodes), root.myy * _SF, rel_tol=1e-9, abs_tol=1e-3)
        # Bending = FORCE moments about the root strip (exact under the WINGINER quadrature).
        assert math.isclose(sum(n.fz * (n.y - y0) for n in nodes), root.mxx * _SF, rel_tol=1e-6, abs_tol=1.0)
        assert math.isclose(sum(n.fx * (n.y - y0) for n in nodes), root.mzz * _SF, rel_tol=1e-6, abs_tol=1.0)


def test_concept_closure():
    results = _wing_net(_CONCEPT)
    assert results
    for r in results:
        nodes = sb.wing_nodal_loads(r)
        assert math.isclose(sum(n.fz for n in nodes), r.stations[0].sz * _SF, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.my for n in nodes), r.stations[0].myy * _SF, rel_tol=1e-9, abs_tol=1e-3)


# --------------------------------------------------------------------------- #
# FORCE/MOMENT card text
# --------------------------------------------------------------------------- #
def test_force_moment_cards_round_trip():
    results = _wing_net(_GA)
    _, _, _, forces, moments = parse_cards(sb.force_moment_cards(results, sid_base=1))
    # One SID per case, contiguous from sid_base.
    assert sorted(forces) == [1, 2, 3]
    for idx, r in enumerate(results):
        sid = 1 + idx
        # Re-summed FORCE / MOMENT match the NETLOADS root totals (scale * vector).
        fz = sum(scale * v[2] for _, scale, v in forces[sid])
        fx = sum(scale * v[0] for _, scale, v in forces[sid])
        my = sum(scale * v[1] for _, scale, v in moments[sid])
        assert math.isclose(fz, r.stations[0].sz * _SF, rel_tol=1e-4, abs_tol=1.0)
        assert math.isclose(fx, r.stations[0].sx * _SF, rel_tol=1e-4, abs_tol=1.0)
        assert math.isclose(my, r.stations[0].myy * _SF, rel_tol=1e-4, abs_tol=1.0)


def test_force_moment_card_format():
    text = sb.force_moment_cards(_wing_net(_GA))
    force_lines = [ln for ln in text.splitlines() if ln.startswith("FORCE")]
    assert force_lines
    for ln in force_lines:
        f = [c.strip() for c in ln.split(",")]
        assert len(f) == 8                  # FORCE, SID, GID, CID, scale, N1, N2, N3
        assert f[3] == "0"                  # CID 0 (basic frame)
        assert float(f[4]) == 1.0           # unit scale; magnitude in components
        assert "E" in f[5]                  # scientific %.6E format


def test_near_zero_components_skipped():
    # No card should carry an all-zero direction vector.
    text = sb.stick_model_bdf(_wing_net(_GA))
    for ln in text.splitlines():
        if ln.startswith(("FORCE", "MOMENT")):
            f = [c.strip() for c in ln.split(",")]
            assert any(abs(float(v)) > 0 for v in f[5:8])


# --------------------------------------------------------------------------- #
# Stick model deck
# --------------------------------------------------------------------------- #
def test_stick_model_structure():
    results = _wing_net(_GA)
    text = sb.stick_model_bdf(results)
    assert text.startswith("SOL 101")
    assert "BEGIN BULK" in text and text.rstrip().endswith("ENDDATA")
    grids, cbars, spc1, forces, moments = parse_cards(text)
    n_stations = len(results[0].stations)
    # One GRID per station + a clamped root node; a CBAR per element of the chain.
    assert len(grids) == n_stations + 1
    assert len(cbars) == n_stations
    # CBAR chain is connected root -> station 0 -> ... -> tip.
    assert cbars[0][1] == 1                                  # GA of first bar is the root node
    for (_, _, gb_prev), (_, ga, _) in zip(cbars, cbars[1:]):
        assert ga == gb_prev
    # Root node clamped in all 6 DOF, and it is not a loaded grid.
    assert spc1 and spc1[0][1] == "123456" and spc1[0][2] == [1]
    loaded = {gid for cards in forces.values() for gid, _, _ in cards}
    assert 1 not in loaded
    # One subcase + load set per case.
    assert text.count("SUBCASE ") == len(results)
    assert sorted(forces) == [1, 2, 3]


def test_grids_match_station_geometry():
    results = _wing_net(_GA)
    grids, *_ = parse_cards(sb.stick_model_bdf(results))
    for i, st in enumerate(results[0].stations):
        gx, gy, gz = grids[sb.station_gid(i)]
        assert math.isclose(gx, st.x, abs_tol=1e-3)
        assert math.isclose(gy, st.y, abs_tol=1e-3)
        assert math.isclose(gz, st.z, abs_tol=1e-3)


# --------------------------------------------------------------------------- #
# Span-load CSV
# --------------------------------------------------------------------------- #
def test_span_load_csv_shape():
    results = _wing_net(_GA)
    text = sb.span_load_csv(results)
    lines = text.strip().splitlines()
    header = lines[0].split(",")
    # Every dimensional column states its unit and, if it is a load, its ULT
    # marker (M4-20 step 4). Before that the header was bare -- ``Fx``, ``My`` --
    # and a reader had to know the file was Imperial from somewhere else.
    assert header == ["Case", "GID", "X (in)", "Y (in)", "Z (in)",
                      "Fx (lbs-ULT)", "Fz (lbs-ULT)", "My (lb-in-ULT)",
                      "Sx (lbs-ULT)", "Sz (lbs-ULT)", "Mxx (lb-in-ULT)",
                      "Myy (lb-in-ULT)", "Mzz (lb-in-ULT)", "MyyAxis", "SF"]
    assert len(lines) - 1 == sum(len(r.stations) for r in results)
    # The torsion axis travels in-band: untransferred results state 25% chord.
    assert all(line.split(",")[-2] == "25% chord" for line in lines[1:])


# --------------------------------------------------------------------------- #
# Inputs & file writers
# --------------------------------------------------------------------------- #
def test_accepts_project_and_requires_loads():
    p = io.load_project(_GA)
    try:
        sb.span_load_csv(p)  # no Project.loads set yet
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError when Project.loads is missing")
    p.loads = build_net_loads(p)
    assert sb.span_load_csv(p).startswith("Case,GID")


def test_project_export_transfers_to_loads_ref_axis():
    """The Project path states wing torsion about the surface's LRA, labelled in-band."""
    from sloads.modules.wing_geometry import interp_x

    p = io.load_project(_GA)
    p.loads = build_net_loads(p)
    wing = p.geometry.by_name(p.wing_mass.surface)
    wing.ref_axis_pct = 0.40
    text = sb.span_load_csv(p)
    lines = text.strip().splitlines()
    assert all(line.split(",")[-2] == "LRA 40% chord" for line in lines[1:])
    # Cumulative root torsion = the 25%-chord value + SF x Sz x (x_lra - x_25).
    raw = p.loads.wing_net[0].stations[0]
    sf = p.loads.wing_net[0].safety_factor
    x_le = interp_x(wing.leading_edge, raw.y)
    x_te = interp_x(wing.trailing_edge, raw.y)
    x_lra = x_le + 0.40 * (x_te - x_le)
    expected = (raw.myy + raw.sz * (x_lra - raw.x)) * sf
    row = lines[1].split(",")
    assert math.isclose(float(row[11]), expected, rel_tol=1e-3, abs_tol=1.0)
    # The BDF headers and stick-model beam axis carry the same label.
    assert "$ Torsion My/Myy about the LRA 40% chord" in sb.force_moment_cards(p)
    assert "$ Beam axis: the wing LRA 40% chord line." in sb.stick_model_bdf(p)


def test_writers(tmp_path=None):
    import tempfile

    results = _wing_net(_GA)
    d = tmp_path or tempfile.mkdtemp()
    csv_p = os.path.join(str(d), "w.span_loads.csv")
    bdf_p = os.path.join(str(d), "w.loads.bdf")
    stick_p = os.path.join(str(d), "w.stick.bdf")
    sb.write_span_load_csv(results, csv_p)
    sb.write_force_moment_cards(results, bdf_p)
    sb.write_stick_model_bdf(results, stick_p)
    for path in (csv_p, bdf_p, stick_p):
        assert os.path.getsize(path) > 0


# --------------------------------------------------------------------------- #
# Control-surface export (Step C8): closure -- the FORCE set sums to the load.
# --------------------------------------------------------------------------- #
def _control_results():
    from sloads.modules.aileron import build_aileron
    from sloads.modules.flap import build_flap
    from sloads.modules.tab import build_tabs

    p = io.load_project(_GA)
    return build_aileron(p) + build_flap(p) + build_tabs(p)


def test_control_surface_force_closure():
    """Each control-surface FORCE set's applied Fz sums to the critical load."""
    results = _control_results()
    assert results
    for r in results:
        forces = sb._control_nodal_forces(r)
        assert math.isclose(sum(forces), r.load_lb * _SF, rel_tol=1e-6, abs_tol=1e-6), r.case
    cards = sb.control_surface_force_moment_cards(results)
    assert "FORCE" in cards
    assert sb.control_surface_csv(results).startswith("Surface,Case,GID")


def test_control_surface_writers(tmp_path=None):
    import tempfile

    results = _control_results()
    d = tmp_path or tempfile.mkdtemp()
    csv_p = os.path.join(str(d), "cs.csv")
    bdf_p = os.path.join(str(d), "cs.bdf")
    sb.write_control_surface_csv(results, csv_p)
    sb.write_control_surface_force_moment_cards(results, bdf_p)
    for path in (csv_p, bdf_p):
        assert os.path.getsize(path) > 0


# --------------------------------------------------------------------------- #
# Export-scope filter (Step D8.3)
# --------------------------------------------------------------------------- #
def test_filter_by_selected_case_ids_none_is_unfiltered():
    results = _wing_net(_GA)
    assert sb.filter_by_selected_case_ids(results, None) == results


def test_filter_by_selected_case_ids_keeps_only_selected():
    results = _wing_net(_GA)
    ids = {results[0].case_ref.case_id}
    filtered = sb.filter_by_selected_case_ids(results, ids)
    assert len(filtered) == 1
    assert filtered[0].case_ref.case_id == results[0].case_ref.case_id


def test_filter_by_selected_case_ids_empty_selection_drops_all_tagged():
    results = _wing_net(_GA)
    assert sb.filter_by_selected_case_ids(results, set()) == []


def test_export_package_exposes_all_component_families():
    """Step P1-4: the whole export surface is reachable from ``sloads.export``.

    Before P1-4 ``__all__`` listed only wing + tail, so a caller following the
    package API could export only two of the four component families. The concept
    deliverable is "all components to sbeam" -- assert body + control + the case
    index are all importable from the package (not just the submodule).
    """
    from sloads.export import (  # noqa: F401
        body_force_moment_cards,
        body_span_load_csv,
        case_index_csv,
        control_surface_csv,
        control_surface_force_moment_cards,
        filter_by_selected_case_ids,
        write_case_index_csv,
        write_control_surface_csv,
        write_control_surface_force_moment_cards,
    )
    import sloads.export as export_pkg

    # Every re-exported name is advertised in __all__ and resolves to the
    # sbeam_bridge implementation (no accidental shadowing).
    for name in (
        "body_span_load_csv", "body_force_moment_cards",
        "control_surface_csv", "write_control_surface_csv",
        "control_surface_force_moment_cards",
        "write_control_surface_force_moment_cards",
        "case_index_csv", "write_case_index_csv",
        "filter_by_selected_case_ids",
    ):
        assert name in export_pkg.__all__, f"{name} missing from export __all__"
        assert getattr(export_pkg, name) is getattr(sb, name)


# --------------------------------------------------------------------------- #
# Per-case safety factor (defect M4-7)
#
# The bridge used to hardcode a flat x1.5 and ignore the case's own factor, so a
# case whose values are already ultimate (safety_factor = 1.0, per the CLAUDE.md
# ultimate-load contract) would have been multiplied by 1.5 a second time. These
# lock the factor to the *result*, not to a suite-wide constant.
# --------------------------------------------------------------------------- #
def _wing_net_with_sf(sf):
    """The GA wing net loads with every case's safety factor forced to ``sf``."""
    results = _wing_net(_GA)
    for r in results:
        r.safety_factor = sf
    return results


def test_wing_export_honours_per_case_safety_factor():
    """Closure holds against *that case's* factor -- SF=1.0 exports unscaled."""
    for sf in (1.0, 1.25, _SF):
        for r in _wing_net_with_sf(sf):
            nodes = sb.wing_nodal_loads(r)
            root = r.stations[0]
            assert math.isclose(sum(n.fz for n in nodes), root.sz * sf,
                                rel_tol=1e-9, abs_tol=1e-6), sf
            assert math.isclose(sum(n.my for n in nodes), root.myy * sf,
                                rel_tol=1e-9, abs_tol=1e-3), sf


def test_wing_export_mixes_factors_across_cases():
    """Two cases, two factors: each load set scales by its own, not by the first."""
    results = _wing_net(_GA)
    assert len(results) >= 2
    results[0].safety_factor = 1.0
    results[1].safety_factor = 1.5
    for r in results[:2]:
        nodes = sb.wing_nodal_loads(r)
        assert math.isclose(sum(n.fz for n in nodes), r.stations[0].sz * r.safety_factor,
                            rel_tol=1e-9, abs_tol=1e-6), r.case


def test_cards_state_the_factor_they_used():
    """The ``$`` header quotes the case's actual SF, never a baked-in 1.5."""
    cards = sb.force_moment_cards(_wing_net_with_sf(1.0))
    # "SF=1.0", not "SF=1" -- deliverable formatting (M4-16).
    assert "$ Loads are ULTIMATE (limit x SF=1.0)." in cards
    assert "SF=1.5" not in cards


def test_span_csv_carries_the_safety_factor_column():
    """Every exported load case states its factor (the CLAUDE.md ULT contract)."""
    rows = [ln.split(",") for ln in
            sb.span_load_csv(_wing_net_with_sf(1.0)).strip().splitlines()]
    assert rows[0][-1] == "SF"
    assert {r[-1] for r in rows[1:]} == {"1.0"}


def test_body_tail_control_exports_honour_the_factor():
    """The other three component families scale by the result's factor too."""
    from sloads.modules.body_loads import build_body_loads
    from sloads.modules.taildist import build_tail_chordwise

    p = io.load_project(_GA)
    if p.envelope is None:
        p.envelope = build_envelope(p)

    body = build_body_loads(p)
    for r in body:
        r.safety_factor = 1.0
    body_rows = [ln.split(",") for ln in sb.body_span_load_csv(body).strip().splitlines()]
    assert body_rows[0][-1] == "SF" and {r[-1] for r in body_rows[1:]} == {"1.0"}
    assert "$ Loads are ULTIMATE (limit x SF=1.0)." in sb.body_force_moment_cards(body)

    tail = build_tail_chordwise(p)
    assert tail
    for r in tail:
        r.safety_factor = 1.0
        assert math.isclose(sum(sb._tail_nodal_forces(r)), r.lt25 + r.lt50,
                            rel_tol=1e-6, abs_tol=1e-6), r.case
    tail_rows = [ln.split(",") for ln in sb.tail_chordwise_csv(tail).strip().splitlines()]
    assert tail_rows[0][-1] == "SF" and {r[-1] for r in tail_rows[1:]} == {"1.0"}

    control = _control_results()
    for r in control:
        r.safety_factor = 1.0
        assert math.isclose(sum(sb._control_nodal_forces(r)), r.load_lb,
                            rel_tol=1e-6, abs_tol=1e-6), r.case
    cs_rows = [ln.split(",") for ln in sb.control_surface_csv(control).strip().splitlines()]
    assert cs_rows[0][-1] == "SF" and {r[-1] for r in cs_rows[1:]} == {"1.0"}


def test_taildist_and_body_copy_the_condition_factor():
    """The producers carry the owning CriticalCondition's factor into the slice."""
    from sloads.modules.body_loads import build_body_loads
    from sloads.modules.select import build_critical
    from sloads.modules.taildist import build_tail_chordwise

    p = io.load_project(_GA)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    # Persist the critical set so both producers read the *same* (mutated) conditions.
    p.envelope.critical = build_critical(p)
    for cond in p.envelope.critical.conditions:
        cond.safety_factor = 1.25

    derived = build_body_loads(p) + build_tail_chordwise(p)
    assert derived
    for r in derived:
        assert r.safety_factor == 1.25, r.case


# --------------------------------------------------------------------------- #
# Per-case safety factor, wing + control surfaces (defect M4-13)
#
# These four modules own their conditions (no upstream CriticalCondition to copy
# from), so the factor is minted once in build_* and run()'s ConditionResult must
# copy it from the built result -- never re-default it independently.
# --------------------------------------------------------------------------- #
def _ga_project():
    p = io.load_project(_GA)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    return p


def test_wing_and_control_results_agree_with_their_conditions():
    """Each producer's result slice and rendered ConditionResult carry one factor."""
    from sloads.modules import aileron, flap, net_loads, tab

    p = _ga_project()

    loads = net_loads.build_net_loads(p)
    conds = {c.case_ref.case_id: c for c in net_loads.run(p).conditions}
    for r in loads.wing_air + loads.wing_inertia + loads.wing_net:
        assert r.safety_factor == conds[r.case_ref.case_id].safety_factor, r.case

    down, up = aileron.build_aileron(p)
    assert down.safety_factor == up.safety_factor
    assert aileron.run(p).conditions[0].safety_factor == down.safety_factor

    built = flap.build_flap(p)[0]
    assert flap.run(p).conditions[0].safety_factor == built.safety_factor

    for r, c in zip(tab.build_tabs(p), tab.run(p).conditions):
        assert r.safety_factor == c.safety_factor, r.case


def test_run_copies_the_built_results_factor():
    """run() reads the mint in build_* rather than defaulting a second source of
    truth -- a non-default factor must reach the rendered ConditionResult."""
    from sloads.modules import aileron, flap, net_loads, tab

    p = _ga_project()

    def force_sf(results):
        for r in results:
            r.safety_factor = 1.25
        return results

    # build_net_loads returns a LoadsResult; the control-surface builders a list.
    patches = [
        (net_loads, "build_net_loads", lambda built: force_sf(built.wing_net)),
        (aileron, "build_aileron", force_sf),
        (flap, "build_flap", force_sf),
        (tab, "build_tabs", force_sf),
    ]
    for module, attr, mutate in patches:
        real = getattr(module, attr)

        def patched(proj, real=real, mutate=mutate):
            built = real(proj)
            mutate(built)
            return built

        setattr(module, attr, patched)
        try:
            for cond in module.run(p).conditions:
                assert cond.safety_factor == 1.25, (module.MODULE_NAME, cond.title)
        finally:
            setattr(module, attr, real)


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
