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

from farloads import io  # noqa: E402
from farloads.modules.flight_envelope import build_envelope  # noqa: E402
from farloads.export import sbeam_bridge as sb  # noqa: E402
from farloads.modules.net_loads import build_net_loads  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_heavy.project.json")


def _wing_net(path):
    p = io.load_project(path)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    return build_net_loads(p).wing_net


# --------------------------------------------------------------------------- #
# Self-contained free-field BDF reader (no sbeam import, per the test plan)
# --------------------------------------------------------------------------- #
def _parse_cards(text):
    """Parse the bridge's comma free-field deck into simple card structures.

    Returns ``(grids, cbars, spc1, forces, moments)`` where ``grids`` is
    ``{gid: (x, y, z)}``, ``cbars`` a list of ``(eid, ga, gb)``, ``spc1`` a list
    of ``(sid, comp, [gids])`` and ``forces``/``moments`` are ``{sid: [(gid,
    scale, (n1, n2, n3))]}``.
    """
    grids, cbars, spc1 = {}, [], []
    forces, moments = {}, {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("$"):
            continue
        f = [c.strip() for c in line.split(",")]
        kw = f[0].upper()
        if kw == "GRID":
            grids[int(f[1])] = (float(f[3]), float(f[4]), float(f[5]))
        elif kw == "CBAR":
            cbars.append((int(f[1]), int(f[3]), int(f[4])))
        elif kw == "SPC1":
            spc1.append((int(f[1]), f[2], [int(g) for g in f[3:] if g]))
        elif kw in ("FORCE", "MOMENT"):
            sid, gid, scale = int(f[1]), int(f[2]), float(f[4])
            vec = (float(f[5]), float(f[6]), float(f[7]))
            (forces if kw == "FORCE" else moments).setdefault(sid, []).append((gid, scale, vec))
    return grids, cbars, spc1, forces, moments


# --------------------------------------------------------------------------- #
# Nodal-load closure (the core guarantee)
# --------------------------------------------------------------------------- #
def test_nodal_loads_sum_to_root_totals():
    for r in _wing_net(_GA):
        nodes = sb.wing_nodal_loads(r)
        root = r.stations[0]
        y0 = nodes[0].y
        assert math.isclose(sum(n.fz for n in nodes), root.sz, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.fx for n in nodes), root.sx, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.my for n in nodes), root.myy, rel_tol=1e-9, abs_tol=1e-3)
        # Bending = FORCE moments about the root strip (exact under the WINGINER quadrature).
        assert math.isclose(sum(n.fz * (n.y - y0) for n in nodes), root.mxx, rel_tol=1e-6, abs_tol=1.0)
        assert math.isclose(sum(n.fx * (n.y - y0) for n in nodes), root.mzz, rel_tol=1e-6, abs_tol=1.0)


def test_concept_closure():
    results = _wing_net(_CONCEPT)
    assert results
    for r in results:
        nodes = sb.wing_nodal_loads(r)
        assert math.isclose(sum(n.fz for n in nodes), r.stations[0].sz, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.my for n in nodes), r.stations[0].myy, rel_tol=1e-9, abs_tol=1e-3)


# --------------------------------------------------------------------------- #
# FORCE/MOMENT card text
# --------------------------------------------------------------------------- #
def test_force_moment_cards_round_trip():
    results = _wing_net(_GA)
    _, _, _, forces, moments = _parse_cards(sb.force_moment_cards(results, sid_base=1))
    # One SID per case, contiguous from sid_base.
    assert sorted(forces) == [1, 2, 3]
    for idx, r in enumerate(results):
        sid = 1 + idx
        # Re-summed FORCE / MOMENT match the NETLOADS root totals (scale * vector).
        fz = sum(scale * v[2] for _, scale, v in forces[sid])
        fx = sum(scale * v[0] for _, scale, v in forces[sid])
        my = sum(scale * v[1] for _, scale, v in moments[sid])
        assert math.isclose(fz, r.stations[0].sz, rel_tol=1e-4, abs_tol=1.0)
        assert math.isclose(fx, r.stations[0].sx, rel_tol=1e-4, abs_tol=1.0)
        assert math.isclose(my, r.stations[0].myy, rel_tol=1e-4, abs_tol=1.0)


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
    grids, cbars, spc1, forces, moments = _parse_cards(text)
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
    grids, *_ = _parse_cards(sb.stick_model_bdf(results))
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
    assert header == ["Case", "GID", "X", "Y", "Z", "Fx", "Fz", "My",
                      "Sx", "Sz", "Mxx", "Myy", "Mzz"]
    assert len(lines) - 1 == sum(len(r.stations) for r in results)


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
