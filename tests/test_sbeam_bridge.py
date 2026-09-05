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

from sloads import io
from sloads.export import sbeam_bridge as sb
from sloads.export.equilibrium import card_totals, closes, parse_cards
from sloads.modules.flight_envelope import build_envelope
from sloads.modules.net_loads import build_net_loads

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


def _nodal_torsion_about_root(nodes):
    """The deck's rigid-body torsion about its root node: Σ my + Σ (p - root) x F.

    The cards carry each strip's **free** torsion, so the root torsion is only
    recovered once the arms are applied -- which is what a solver does and what
    the deck now claims (note 46 OR-67/OR-68). Summing ``my`` bare would give
    the free-torsion total, a different and much smaller number.
    """
    x0, z0 = nodes[0].x, nodes[0].z
    return sum(n.my + (n.z - z0) * n.fx - (n.x - x0) * n.fz for n in nodes)


def test_nodal_loads_sum_to_root_totals():
    for r in _wing_net(_GA):
        nodes = sb.wing_nodal_loads(r)
        root = r.stations[0]
        y0 = nodes[0].y
        assert math.isclose(sum(n.fz for n in nodes), root.sz, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.fx for n in nodes), root.sx, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(_nodal_torsion_about_root(nodes), root.myy,
                            rel_tol=1e-9, abs_tol=1e-3)
        # Bending = FORCE moments about the root strip (exact under the WINGINER quadrature).
        assert math.isclose(sum(n.fz * (n.y - y0) for n in nodes), root.mxx, rel_tol=1e-6, abs_tol=1.0)
        assert math.isclose(sum(n.fx * (n.y - y0) for n in nodes), root.mzz, rel_tol=1e-6, abs_tol=1.0)


def test_concept_closure():
    results = _wing_net(_CONCEPT)
    assert results
    for r in results:
        nodes = sb.wing_nodal_loads(r)
        assert math.isclose(sum(n.fz for n in nodes), r.stations[0].sz, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(_nodal_torsion_about_root(nodes),
                            r.stations[0].myy, rel_tol=1e-9, abs_tol=1e-3)


# --------------------------------------------------------------------------- #
# FORCE/MOMENT card text
# --------------------------------------------------------------------------- #
def test_force_moment_cards_round_trip():
    """Re-summed FORCE / MOMENT match the NETLOADS root totals.

    Summation and tolerance come from :mod:`sloads.export.equilibrium`, the
    single owner (this file used to hand-roll both, as did three other places).
    The bare card deck carries no ``GRID`` cards, so it gets the geometry-free
    :func:`card_totals`; the moment-closure sweep that does integrate lever arms
    lives in ``test_export_equilibrium.py``."""
    results = _wing_net(_GA)
    totals = card_totals(sb.force_moment_cards(results, sid_base=1))
    # One SID per case, taken from the case's own id (M4-2 decision 9): ga6's
    # PHAA / TORS / ACRL hold wing slots 1 / 6 / 5 -> 101 / 106 / 105.
    assert sorted(totals) == [101, 105, 106]
    for idx, r in enumerate(results):
        got = totals[sb._sid(1, idx, r)]
        root = r.stations[0]
        assert closes(got.force[2], root.sz, scale=got.force_scale)
        assert closes(got.force[0], root.sx, scale=got.force_scale)
        # The bare card deck has no GRID cards, so the lever arms come from the
        # nodal loads rather than from the deck's own text; the deck-text sweep
        # that integrates them lives in ``test_export_equilibrium.py``.
        transfer = _nodal_torsion_about_root(sb.wing_nodal_loads(r)) \
            - sum(n.my for n in sb.wing_nodal_loads(r))
        assert closes(got.moment[1] + transfer, root.myy,
                      scale=got.moment_scale)


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
    # One case-control subcase + load set per case, numbered from the case id;
    # the leading $ map block names each one (M4-2 decisions 8/10).
    subcases = [ln for ln in text.splitlines() if ln.startswith("SUBCASE ")]
    assert len(subcases) == len(results)
    assert sorted(forces) == [101, 105, 106]
    assert [int(ln.split()[1]) for ln in subcases] == [101, 106, 105]
    assert text.count("$ SUBCASE ") == len(results)


def test_a_filtered_export_does_not_renumber_the_surviving_subcases():
    """M4-2 decision 8: the deck ``SUBCASE``/``SID`` is a property of the case, so
    dropping a case from the export leaves the others' numbers exactly where they
    were. Before M4-2 the number was the case's *position*, so deselecting one
    case shifted every case after it -- ``SUBCASE 2`` meant a different condition
    in two exports of the same project, with nothing in either deck saying so."""
    results = _wing_net(_GA)
    assert len(results) >= 3
    full = {r.case_ref.case_id: sb._sid(1, i, r) for i, r in enumerate(results)}

    keep = [r for r in results if r.case_ref.case_id != results[0].case_ref.case_id]
    kept_ids = [r.case_ref.case_id for r in keep]
    assert sb.filter_by_selected_case_ids(results, kept_ids) == keep
    filtered = {r.case_ref.case_id: sb._sid(1, i, r) for i, r in enumerate(keep)}
    assert filtered == {cid: full[cid] for cid in kept_ids}

    # ... and the deck itself carries those numbers, with the map block naming
    # the condition behind each one.
    text = sb.stick_model_bdf(keep)
    for cid in kept_ids:
        assert f"SUBCASE {full[cid]}\n" in text
        assert f"$ SUBCASE {full[cid]} = {cid} -- " in text
    dropped = results[0].case_ref.case_id
    assert f"SUBCASE {full[dropped]}\n" not in text


def test_subcase_map_names_the_governing_condition():
    """Decision 10: a deck consumer can trace a subcase back to its condition
    from the deck alone -- id, condition and FAR reference, on one line."""
    results = _wing_net(_GA)
    lines = sb.subcase_map_block(results)
    assert lines and lines[0].startswith("$ ")
    body = [ln for ln in lines if ln.startswith("$ SUBCASE ")]
    assert len(body) == len(results)
    for r, ln in zip(results, body):
        ref = r.case_ref
        assert f"= {ref.case_id} -- {ref.condition}" in ln
        assert f"FAR {ref.far_reference}" in ln


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
    from sloads.report.methods import strip_comment_lines

    results = _wing_net(_GA)
    text = strip_comment_lines(sb.span_load_csv(results))
    lines = text.strip().splitlines()
    header = lines[0].split(",")
    # Every dimensional column states its unit and, if it is a load, its ULT
    # marker (M4-20 step 4). Before that the header was bare -- ``Fx``, ``My`` --
    # and a reader had to know the file was Imperial from somewhere else.
    # Mx/Mz are the concentrated-mass offset couples -- part of the applied
    # nodal load, hence beside Fx/Fz/My rather than with the cumulative columns.
    assert header == ["Case", "GID", "X (in)", "Y (in)", "Z (in)",
                      "Fx (lb)", "Fz (lb)", "My (lb-in)",
                      "Mx (lb-in)", "Mz (lb-in)",
                      "Sx (lb)", "Sz (lb)", "Mxx (lb-in)",
                      "Myy (lb-in)", "Mzz (lb-in)", "MyyAxis", "SF"]
    assert len(lines) - 1 == sum(len(r.stations) for r in results)
    # The torsion axis travels in-band: untransferred results state 25% chord.
    assert all(line.split(",")[-2] == "25% chord" for line in lines[1:])


# --------------------------------------------------------------------------- #
# Inputs & file writers
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# The applied load set (the structures deliverable, oracle report Appendix B.1)
# --------------------------------------------------------------------------- #
_BARON = os.path.join(_EXAMPLES, "baron_58.project.json")


def _lra_net(path):
    """Net wing loads transferred to the wing's loads reference axis."""
    from sloads.modules.net_loads import loads_ref_axis_results

    p = io.load_project(path)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    return loads_ref_axis_results(p, list(build_net_loads(p).wing_net))


def _csv_rows(text):
    import csv as _csv

    from sloads.report.methods import strip_comment_lines

    return list(_csv.DictReader(strip_comment_lines(text).splitlines()))


def test_the_applied_set_carries_every_strip_and_every_concentrated_mass():
    """One row per strip plus one per wing mass -- the whole applied set."""
    net = _lra_net(_BARON)
    one = net[0]
    rows = sb.applied_load_rows([one])
    assert len(rows) == len(one.stations) + len(one.point_loads)
    assert len(one.point_loads) == 4, "the Baron enters four concentrated wing masses"
    named = [r.label for r in rows if r.gid is None]
    assert named == [m.name for m in one.point_loads]


def test_a_concentrated_mass_has_no_grid_and_no_free_moment():
    """A point mass is a pure force: every moment it makes is force x arm."""
    rows = sb.applied_load_rows(_lra_net(_BARON)[:1])
    masses = [r for r in rows if r.gid is None]
    assert masses, "the Baron has concentrated wing masses"
    for m in masses:
        assert m.myy_free == 0.0
        assert m.fz != 0.0


def _resultant(rows, about, outboard_of):
    """The applied set's six-component resultant about ``about``, tip-inboard.

    ``rows`` are :class:`~sloads.export.sbeam_bridge.AppliedLoad` records; only
    those at or outboard of ``outboard_of`` (a span station, in) contribute --
    which is exactly the population the cumulative table at that station holds.
    Moments are right-handed ``r x F`` plus the record's own free moments,
    taken through ``applied_body_moments`` so the sign map has one owner.
    """
    sx = sz = mx = my = mz = 0.0
    for r in rows:
        if r.y < outboard_of:
            continue
        dx, dy, dz = r.x - about[0], r.y - about[1], r.z - about[2]
        bmx, bmy, bmz = sb.applied_body_moments(r)
        sx += r.fx
        sz += r.fz
        mx += dy * r.fz - dz * r.fy + bmx
        my += dz * r.fx - dx * r.fz + bmy
        mz += dx * r.fy - dy * r.fx + bmz
    return sx, sz, mx, my, mz


def test_the_applied_set_reproduces_the_whole_vmt_at_every_station():
    """The closure gate: the applied vector rebuilds V, M and T along the span.

    This is what makes the set a deck. A model applying the six components at
    the stated points generates every sweep, dihedral and span transfer itself,
    so the applied moment must be the *free* moment only -- carrying the
    increment of the cumulative instead would double the transfer.

    Checked at **every** station, not only the root, and on all five components
    the wing chain publishes: a set that closed at the root alone could still
    put the load in the wrong bay. ``Mzz`` is compared negated because the calc
    stores spanwise bending as a positive-magnitude integral while the body-axis
    resultant is ``r x F`` (``coordinates.bending_moment_vector``).
    """
    for path in (_GA, _BARON):
        for result in _lra_net(path):
            rows = sb.applied_load_rows([result])
            for station in result.stations:
                about = (station.x, station.y, station.z)
                got = _resultant(rows, about, station.y)
                want = (station.sx, station.sz, station.mxx, station.myy,
                        -station.mzz)
                for name, g, w in zip(("Sx", "Sz", "Mxx", "Myy", "Mzz"),
                                      got, want):
                    assert closes(g, w, scale=abs(w)), (
                        f"{path} {result.case} y={station.y:.1f} {name}: "
                        f"applied set gives {g}, table has {w}")


def test_the_applied_set_states_all_six_components():
    """Fy, Mx and Mz are published as zero, not left out (the reader's benefit).

    Their being zero is a property of this load set -- no spanwise strip load
    and no lateral wing condition; no free bending under strip theory -- and a
    consumer building cards has to be able to tell that from an omission.
    """
    for path in (_GA, _BARON):
        rows = sb.applied_load_rows(_lra_net(path))
        assert rows
        for r in rows:
            assert r.fy == 0.0
            assert sb.applied_body_moments(r)[0] == 0.0
            assert sb.applied_body_moments(r)[2] == 0.0
        assert any(r.myy_free for r in rows), "My is not structurally zero"


def test_the_applied_moment_is_the_free_moment_not_the_increment():
    """Guards the whole point of the file against a differencing 'simplification'.

    ``Myy free`` and the increment of the cumulative ``Myy`` are different
    quantities -- on ``ga6_normal`` PHAA the inboard strips disagree in sign --
    so a set built by differencing cannot be applied at these coordinates.
    """
    result = _lra_net(_GA)[0]
    s = result.stations
    increments = [s[i].myy - (s[i + 1].myy if i + 1 < len(s) else 0.0)
                  for i in range(len(s))]
    rows = [r for r in sb.applied_load_rows([result]) if r.gid is not None]
    opposed = [i for i, (r, d) in enumerate(zip(rows, increments)) if r.myy_free * d < 0]
    assert opposed, ("the two quantities no longer differ in sign anywhere -- if "
                     "the physics moved, restate the case; if the export was "
                     "rewritten to difference the cumulative, that is the defect")


def test_the_applied_csv_states_its_units_axis_and_factor():
    """A distribution file is unusable without its units, axis and basis (D-21)."""
    net = _lra_net(_GA)
    from sloads.report.methods import strip_comment_lines

    text = sb.applied_load_csv(net)
    header = strip_comment_lines(text).splitlines()[0]
    assert header.split(",") == [
        "Case", "Station", "GID", "X (in)", "Y (in)", "Z (in)",
        "Fx (lb)", "Fy (lb)", "Fz (lb)",
        "Mx (lb-in)", "My (lb-in)", "Mz (lb-in)", "MyyAxis", "SF"]
    row = _csv_rows(text)[0]
    assert row["MyyAxis"] == net[0].torsion_axis
    assert row["SF"] == "1.5"


def test_each_wing_csv_states_the_moment_convention_it_uses():
    """The two files carry different moment conventions and must say so (OR-69).

    ``Mz`` (an applied card component, right-handed) and ``Mzz`` (the beam's
    positive-magnitude bending integral) sit in the same row of the span-load
    file with opposite senses, and no column heading can carry that. The applied
    file states its structural zeros for the same reason: a printed zero and an
    omitted column are different claims.
    """
    net = _lra_net(_GA)
    span = sb.span_load_csv(net)
    assert "right-handed about" in span
    assert "negation of the body-axis Mz" in span

    applied = sb.applied_load_csv(net)
    assert "Fy is zero throughout" in applied
    assert "Mx and Mz are zero throughout" in applied
    # and the statements are comments, so the file still parses as a table
    assert len(_csv_rows(applied)) == sum(
        len(r.stations) + len(r.point_loads) for r in net)


def test_the_applied_csv_leaves_a_point_masss_gid_blank():
    """No invented grid: the deck has no node at a concentrated mass (yet)."""
    rows = _csv_rows(sb.applied_load_csv(_lra_net(_BARON)[:1]))
    blank = [r for r in rows if r["GID"] == ""]
    assert len(blank) == 4
    assert all(r["My (lb-in)"] == "0" for r in blank)
    assert all(r["GID"].isdigit() for r in rows if r not in blank)


def test_the_applied_csv_is_ultimate():
    """LIMIT x the case's own SF, like every other deliverable in this channel."""
    net = _lra_net(_GA)[:1]
    rows = sb.applied_load_rows(net)
    csv_rows = _csv_rows(sb.applied_load_csv(net))
    for r, c in zip(rows, csv_rows):
        assert math.isclose(float(c["Fz (lb)"]), r.fz,
                            abs_tol=0.05)


def test_applied_load_writer(tmp_path=None):
    import tempfile

    d = str(tmp_path) if tmp_path else tempfile.mkdtemp()
    path = os.path.join(d, "applied.csv")
    sb.write_applied_load_csv(_lra_net(_GA), path, header_comment="# ULTIMATE\n")
    text = open(path, encoding="utf-8").read()
    assert text.startswith("# ULTIMATE")
    assert "My (lb-in)" in text


def test_accepts_project_and_requires_loads():
    p = io.load_project(_GA)
    try:
        sb.span_load_csv(p)  # no Project.loads set yet
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError when Project.loads is missing")
    p.loads = build_net_loads(p)
    from sloads.report.methods import strip_comment_lines

    assert strip_comment_lines(sb.span_load_csv(p)).startswith("Case,GID")


def test_project_export_transfers_to_loads_ref_axis():
    """The Project path states wing torsion about the surface's LRA, labelled in-band."""
    from sloads.modules.wing_geometry import interp_x

    p = io.load_project(_GA)
    p.loads = build_net_loads(p)
    wing = p.geometry.by_name(p.wing_mass.surface)
    wing.ref_axis_pct = 0.40
    from sloads.report.methods import strip_comment_lines

    text = strip_comment_lines(sb.span_load_csv(p))
    lines = text.strip().splitlines()
    assert all(line.split(",")[-2] == "LRA 40% chord" for line in lines[1:])
    # Cumulative root torsion = the 25%-chord value + SF x Sz x (x_lra - x_25).
    raw = p.loads.wing_net[0].stations[0]
    sf = p.loads.wing_net[0].safety_factor
    x_le = interp_x(wing.leading_edge, raw.y)
    x_te = interp_x(wing.trailing_edge, raw.y)
    x_lra = x_le + 0.40 * (x_te - x_le)
    expected = (raw.myy + raw.sz * (x_lra - raw.x))
    # Look the column up by name -- a positional index silently follows the
    # wrong column the next time one is added (it did, when Mx/Mz arrived).
    myy_col = lines[0].split(",").index("Myy (lb-in)")
    row = lines[1].split(",")
    assert math.isclose(float(row[myy_col]), expected, rel_tol=1e-3, abs_tol=1.0)
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


def test_degenerate_chordwise_profile_raises():
    """A profile integrating to zero under a non-zero case load raises (review F-C4).

    The former ``scale = 0.0`` fallback emitted an empty load set while the case
    header still claimed the applied total -- a deck contradicting itself. Both
    chordwise writers share one owner (``_trapezoid_tributary_forces``), so both
    are pinned here; a zero case load keeps the (consistent) zero set.
    """
    from sloads.models.results import ControlSurfaceLoadResult, ControlSurfaceStation, TailChordResult, TailChordStation

    flat = [TailChordStation(x=x, psi=0.0) for x in (0.0, 10.0, 20.0)]
    tail = TailChordResult(case="X", component="htail", lt25=300.0, lt50=-100.0,
                           stations=flat, safety_factor=1.0)
    try:
        sb._tail_nodal_forces(tail)
        raise AssertionError("degenerate tail profile did not raise")
    except ValueError as exc:
        assert "integrates to zero" in str(exc) and "htail" in str(exc)

    # Antisymmetric pressures cancel to the same degeneracy, not just all-zero.
    tail.stations = [TailChordStation(x=0.0, psi=1.0),
                     TailChordStation(x=10.0, psi=0.0),
                     TailChordStation(x=20.0, psi=-1.0)]
    try:
        sb._tail_nodal_forces(tail)
        raise AssertionError("cancelling tail profile did not raise")
    except ValueError as exc:
        assert "integrates to zero" in str(exc)

    tail.lt25, tail.lt50 = 0.0, 0.0        # no claim to contradict -> zero set stands
    assert sb._tail_nodal_forces(tail) == [0.0, 0.0, 0.0]

    cs = ControlSurfaceLoadResult(
        surface="aileron", case="down aileron", load_lb=250.0, safety_factor=1.0,
        stations=[ControlSurfaceStation(x=x, psi=0.0) for x in (0.0, 0.5, 1.0)])
    try:
        sb._control_nodal_forces(cs)
        raise AssertionError("degenerate control-surface profile did not raise")
    except ValueError as exc:
        assert "integrates to zero" in str(exc) and "aileron" in str(exc)

    cs.load_lb = 0.0
    assert sb._control_nodal_forces(cs) == [0.0, 0.0, 0.0]


def test_control_surface_force_closure():
    """Each control-surface FORCE set's applied Fz sums to the critical load."""
    results = _control_results()
    assert results
    for r in results:
        forces = sb._control_nodal_forces(r)
        assert math.isclose(sum(forces), r.load_lb, rel_tol=1e-6, abs_tol=1e-6), r.case
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
    import sloads.export as export_pkg
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
            assert math.isclose(sum(n.fz for n in nodes), root.sz,
                                rel_tol=1e-9, abs_tol=1e-6), sf
            assert math.isclose(_nodal_torsion_about_root(nodes), root.myy,
                                rel_tol=1e-9, abs_tol=1e-3), sf


def test_wing_export_mixes_factors_across_cases():
    """Two cases, two factors: each load set scales by its own, not by the first."""
    results = _wing_net(_GA)
    assert len(results) >= 2
    results[0].safety_factor = 1.0
    results[1].safety_factor = 1.5
    for r in results[:2]:
        nodes = sb.wing_nodal_loads(r)
        assert math.isclose(sum(n.fz for n in nodes), r.stations[0].sz,
                            rel_tol=1e-9, abs_tol=1e-6), r.case


def test_cards_state_the_factor_they_used():
    """The ``$`` header quotes the case's actual SF, never a baked-in 1.5.

    At ``SF = 1.0`` that sentence is the already-ultimate one (note 49 OR-118):
    no shipped fixture exports a 23.367(a)(2) or 23.561(b) case to a deck, so
    this is where the branch is exercised on a real deck rather than on a string.
    """
    cards = sb.force_moment_cards(_wing_net_with_sf(1.0))
    # "SF=1.0", not "SF=1" -- deliverable formatting (M4-16).
    assert "$ Loads are ALREADY ULTIMATE (SF=1.0) -- apply no further" in cards
    assert "SF=1.5" not in cards


def test_span_csv_carries_the_safety_factor_column():
    """Every exported load case states its factor (the CLAUDE.md ULT contract)."""
    from sloads.report.methods import strip_comment_lines

    rows = [ln.split(",") for ln in strip_comment_lines(
        sb.span_load_csv(_wing_net_with_sf(1.0))).strip().splitlines()]
    assert rows[0][-1] == "SF"
    assert {r[-1] for r in rows[1:]} == {"1.0"}


def test_body_tail_control_exports_honour_the_factor():
    """The other three component families state the result's own factor too.

    They *stated* and *scaled* by it until note 49 OR-116; now they only state
    it, so what this holds is that the number still comes off the case."""
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
    assert ("$ Loads are ALREADY ULTIMATE (SF=1.0) -- apply no further"
            in sb.body_force_moment_cards(body))

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


# --------------------------------------------------------------------------- #
# Side-of-body node + internal loads (step 13, note 24 R-3)
# --------------------------------------------------------------------------- #
_RJ = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")
_ATR = os.path.join(_EXAMPLES, "atr42_100.project.json")


def _project_and_wing(path):
    from sloads.modules.net_loads import loads_ref_axis_results

    p = io.load_project(path)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    return p, loads_ref_axis_results(p, build_net_loads(p).wing_net)


def test_sob_internal_loads_match_the_cumulative_table_at_a_cut():
    """Way one of two: the outboard sum reproduces NETLOADS' own cumulative table.

    On the mass-free Appendix A wing the closed-form sum of applied nodal loads
    outboard of a cut equals the cumulative shear/torsion at the next station
    plus the bending carried back over the remaining arm -- computed by
    different code (WINGINER quadrature) than the card increments being summed.
    """
    for r in _wing_net(_GA):
        s, sf = r.stations, r.safety_factor
        for k in (0, 2, len(s) - 2):
            y_cut = 0.5 * (s[k].y + s[k + 1].y)
            si = sb.sob_internal_loads(r, y_cut)
            nxt = s[k + 1]
            assert math.isclose(si.sz, nxt.sz, rel_tol=1e-9, abs_tol=1e-6)
            assert math.isclose(si.sx, nxt.sx, rel_tol=1e-9, abs_tol=1e-6)
            # Torsion at the cut is the next station's value transferred to the
            # cut's own point on the LRA -- the cut is half a strip inboard, and
            # a swept, dihedralled axis makes that a real difference (19 % at
            # the root strip of ga6_normal). Under the old differenced cards the
            # transfer was already inside ``my`` and this read as nxt.myy flat.
            x_cut = 0.5 * (s[k].x + s[k + 1].x)
            z_cut = 0.5 * (s[k].z + s[k + 1].z)
            want_myy = (nxt.myy - nxt.sz * (nxt.x - x_cut)
                        + nxt.sx * (nxt.z - z_cut))
            assert math.isclose(si.myy, want_myy, rel_tol=1e-9, abs_tol=1e-3)
            assert math.isclose(si.mxx, (nxt.mxx + nxt.sz * (nxt.y - y_cut)),
                                rel_tol=1e-6, abs_tol=1.0)
            assert math.isclose(si.mzz, (nxt.mzz + nxt.sx * (nxt.y - y_cut)),
                                rel_tol=1e-6, abs_tol=1.0)


def test_sob_collapse_plus_internal_preserves_the_resultant():
    """The LRA-model wing beam starts at the SOB with nothing lost (R-3).

    The collapsed inboard load (force + lever-arm couples at the SOB) plus the
    internal load outboard must reproduce the half-span root totals exactly --
    on ``atr42_100``, whose concentrated wing masses (engines, nacelles, fuel)
    only balance if the offset couples carry their lever arms through both sums.
    """
    p = io.load_project(_ATR)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    from sloads.derived_geometry import sob_station

    y_sob = sob_station(p).y
    for r in build_net_loads(p).wing_net:
        s, sf = r.stations, r.safety_factor
        si = sb.sob_internal_loads(r, y_sob)
        cl = sb.sob_collapsed_load(r, sb.sob_reference_point(r, y_sob))
        assert cl.gid == sb.sob_gid()
        assert math.isclose(cl.fz + si.sz, s[0].sz, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(cl.fx + si.sx, s[0].sx, rel_tol=1e-9, abs_tol=1e-6)
        # Torsion is about the SOB reference point, so the root value transfers
        # over the chordwise and vertical offset between it and the root station
        # -- the same transfer the two halves already share (note 46 OR-67).
        ref = sb.sob_reference_point(r, y_sob)
        want_my = (s[0].myy + (s[0].z - ref[2]) * s[0].sx
                   - (s[0].x - ref[0]) * s[0].sz)
        assert math.isclose(cl.my + si.myy, want_my, rel_tol=1e-9, abs_tol=1e-3)
        # Moments about the SOB: root bending transferred over (y0 - y_sob).
        assert math.isclose(cl.mx + si.mxx,
                            (s[0].mxx + s[0].sz * (s[0].y - y_sob)),
                            rel_tol=1e-6, abs_tol=1.0)
        assert math.isclose(cl.mz + si.mzz,
                            (s[0].mzz + s[0].sx * (s[0].y - y_sob)),
                            rel_tol=1e-6, abs_tol=1.0)


def test_the_stick_deck_gains_a_tagged_sob_node_and_keeps_its_cards():
    """Step 13 in the per-component wing deck: the node is ADDED, the oracle kept.

    Plan 10 §1.1 constraint 1: the station set cannot be truncated at the SOB.
    So against the same results, the tagged deck must carry every GRID, FORCE
    and MOMENT card of the plain one unchanged -- the SOB is one new GRID
    (band ``lra-sob``, decision BM-5) splitting one CBAR, and nothing else.
    """
    from sloads.derived_geometry import sob_station

    p, wing = _project_and_wing(_RJ)
    sob = sob_station(p)
    plain = sb.stick_model_bdf(wing)
    tagged = sb.stick_model_bdf(wing, sob=sob)
    assert "\n$ SLOADS-NODE lra-sob R\n" not in plain
    assert "\n$ SLOADS-NODE lra-sob R\n" in tagged
    g0, c0, _, f0, m0 = parse_cards(plain)
    g1, c1, _, f1, m1 = parse_cards(tagged)
    assert f1 == f0 and m1 == m0
    assert set(g1) - set(g0) == {sb.sob_gid()}
    assert all(g1[gid] == g0[gid] for gid in g0)
    assert len(c1) == len(c0) + 1
    for (_, _, gb_prev), (_, ga, _) in zip(c1, c1[1:]):
        assert ga == gb_prev
    # The node sits at the resolved butt line, interpolated onto the beam line.
    assert math.isclose(g1[sb.sob_gid()][1], sob.y)
    # Each case states its closed-form SOB internal loads in-band.
    assert tagged.count("$ SOB internal loads, case") == len(wing)


def test_a_project_without_a_body_ships_the_deck_it_always_did():
    """ga6/concept_heavy state no side of body -> the deck must not invent one."""
    results = _wing_net(_GA)
    assert sb.stick_model_bdf(results) == sb.stick_model_bdf(results, sob=None)
    assert "\n$ SLOADS-NODE lra-sob R\n" not in sb.stick_model_bdf(results)


def test_a_sob_outside_the_beam_is_refused_not_bent_onto_it():
    """A butt line outboard of the tip (or on the clamp) is a geometry statement
    this deck cannot carry: no node, no tag, deck unchanged."""
    from sloads.derived_geometry import SobStation

    results = _wing_net(_GA)
    tip = results[0].stations[-1].y
    for bad_y in (tip + 10.0, 0.0):
        text = sb.stick_model_bdf(
            results, sob=SobStation(bad_y, True, "test", "test"))
        assert "\n$ SLOADS-NODE lra-sob R\n" not in text
        assert text == sb.stick_model_bdf(results)


def test_the_export_package_takes_no_silent_defaults():
    """CH-2 (code-standard review item 9): the error contract -- "flagged,
    never silently defaulted" -- holds in the export namespace structurally.

    ``getattr(obj, name, default)`` is the shape that hides a missing attribute
    behind a quiet fallback; every result the exporters read is a typed
    dataclass whose ``case_ref`` / ``case`` / ``hand`` / ``tip_transfer`` are
    declared fields, so they are read as attributes. The one dynamic lookup
    (the ``htail``/``vtail`` span slice) is an explicit map that refuses an
    unknown component. Two-argument ``getattr`` -- a *dynamic attribute name*
    on a typed object, no default -- is not this class and stays allowed."""
    import ast
    from pathlib import Path

    root = Path(sb.__file__).parent
    hits = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "getattr" and len(node.args) >= 3):
                hits.append(f"{path.name}:{node.lineno}")
    assert not hits, f"getattr(..., default) in the export package: {hits}"


def test_tail_span_export_refuses_an_unknown_component():
    """The slice lookup is a map, so a bad component name is a stated error,
    not an empty export (CH-2)."""
    project = io.load_project(_GA)
    try:
        sb.tail_span_force_moment_cards(project, component="canard")
    except ValueError as exc:
        assert "unknown component" in str(exc) and "'canard'" in str(exc)
    else:
        raise AssertionError("an unknown component was accepted")


def test_card_components_snap_dust_and_negative_zero():
    """One card's three components: dust below ``_TOL x`` the card's own scale
    prints as ``0.000000E+00`` -- never as its platform-dependent residue, and
    never as ``-0.000000E+00`` (both failed the frozen digest in CI while the
    same commit passed locally). A real small component is untouched."""
    assert sb._fmt3(-912.811, 6.101335e-15, 3244.192) == \
        "-9.128110E+02, 0.000000E+00, 3.244192E+03"
    assert sb._fmt3(-0.0, -0.0, 4384.268) == \
        "0.000000E+00, 0.000000E+00, 4.384268E+03"
    # relative floor: 1e-5 of a 1e3 load is above 1e-9 x scale -> kept
    assert sb._fmt3(1000.0, 1e-5, 0.0) == "1.000000E+03, 1.000000E-05, 0.000000E+00"
    # absolute floor for an all-tiny card: 1e-8 stays, 1e-10 goes
    assert sb._fmt3(1e-8, 1e-10, 0.0) == "1.000000E-08, 0.000000E+00, 0.000000E+00"
    # every FORCE/MOMENT triple in the exporters goes through it (rule 4 guard)
    import re
    from pathlib import Path
    root = Path(sb.__file__).parent
    triple = re.compile(r"\{_fmt\(\w+\)\}, \{_fmt\(\w+\)\}, \{_fmt\(\w+\)\}")
    hits = [f"{f.name}: {ln.strip()}" for f in root.glob("*.py")
            for ln in f.read_text().splitlines()
            if triple.search(ln) and "PBAR" not in ln]   # PBAR's A, I1, I2 is not a vector
    assert not hits, f"vector cards formatted component-wise, bypassing _fmt3: {hits}"


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


def test_no_export_csv_carries_an_already_ultimate_case():
    """The guard `_load_label` rests on (note 49 OR-116/OR-118/OR-118a).

    Export load columns carry plain units because LIMIT is the only basis and
    the two already-ultimate families -- ``engine_ultimate`` (23.367(a)(2)) and
    ``emergency`` (23.561(b)) -- do not reach these per-component CSVs. That is
    a fact about the current result set, not a law, so it is asserted rather
    than assumed: the day a component result arrives at ``SF = 1.0``, this
    fails and OR-118a's per-table marking has to be threaded through the
    ``_*_fields(u)`` helpers before the column can be trusted.
    """
    import glob
    import os

    from sloads.io import load_project
    from sloads.modules.body_loads import build_body_loads
    from sloads.modules.net_loads import build_net_loads
    from sloads.modules.taildist import build_tail_chordwise

    def _results(builder, project):
        """Every per-case result a builder yields, however it packages them."""
        out = builder(project)
        if isinstance(out, list):
            return [("", r) for r in out]
        # ``build_net_loads`` returns a LoadsResult bundle of named lists.
        return [(f.name, r) for f in dataclasses.fields(out)
                for r in (getattr(out, f.name) or [])]

    import dataclasses

    offenders = []
    for path in sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json"))):
        project = load_project(path)
        for builder in (build_net_loads, build_body_loads, build_tail_chordwise):
            try:
                found = _results(builder, project)
            except Exception:
                continue
            for slot, r in found:
                if getattr(r, "safety_factor", None) == 1.0:
                    offenders.append(
                        f"{os.path.basename(path)}: {builder.__name__}"
                        f"{'.' + slot if slot else ''} {getattr(r, 'case', '?')}")
    assert not offenders, (
        "an export result is already ultimate, so its CSV column must carry "
        "the -ULT marker (OR-118a): " + "; ".join(offenders))
