"""The LRA beam model (step 12) -- skeleton, transfer rule, refusals, import.

Design notes: ``docs/30_future/24_lra_beam_model_review_note.md`` (BM-1..BM-5)
and ``docs/30_future/25_lra_model_implementation_note.md`` (LM-1..LM-7, the
gates this file pins). The solver half of the gates -- reactions, the SOB and
post internal loads through sbeam -- lives in ``tests/test_sbeam_roundtrip.py``.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pytest  # noqa: E402

from sloads import io  # noqa: E402
from sloads.export.coordinates import transfer_couple  # noqa: E402
from sloads.export.equilibrium import (closes, deck_resultants,  # noqa: E402
                                       parse_cards, resultant)
from sloads.export.lra_import import (LRA_IMPORT_TOL_IN,  # noqa: E402
                                      lra_loads_on_imported_model,
                                      read_lra_model, validate_imported_model)
from sloads.export.lra_model import (LraRefusal, build_lra_model,  # noqa: E402
                                     lra_model_bdf, transferred_case_loads)

_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def _project(name: str):
    return io.load_project(os.path.join(_EXAMPLES, name))


_ORIGIN = (0.0, 0.0, 0.0)


def _origin_ref(sid, grids, cards):
    return _ORIGIN


# --------------------------------------------------------------------------- #
# LM-1 -- the transfer rule and its single owner
# --------------------------------------------------------------------------- #
def test_the_transfer_couple_is_the_exact_lever_arm_cross_product():
    """``(p - n) x F``, right-handed, in the identity frame -- the drift guard
    on the one owner every mover in the export channel instantiates (R-11)."""
    p, n, f = (10.0, 20.0, 30.0), (1.0, 2.0, 3.0), (5.0, -7.0, 11.0)
    dx, dy, dz = 9.0, 18.0, 27.0
    expected = (dy * f[2] - dz * f[1], dz * f[0] - dx * f[2],
                dx * f[1] - dy * f[0])
    assert transfer_couple(p, n, f) == expected
    # Moving a load to its own point carries no couple -- the identity that
    # makes an on-node transfer exact rather than approximately zero.
    assert transfer_couple(p, p, f) == (0.0, 0.0, 0.0)


# --------------------------------------------------------------------------- #
# The skeleton (LM-2..LM-6) on the shipped fixtures
# --------------------------------------------------------------------------- #
def test_the_skeleton_carries_every_named_node_family():
    """Conventional layout (atr42): SOB pair, posts, fin root, h-tail
    attachment pair, gear, engines -- each tagged, each tied (BM-5)."""
    model = build_lra_model(_project("atr42_100.project.json"))
    families = {(n.family, n.side) for n in model.nodes if n.family}
    for expected in (("lra-sob", "R"), ("lra-sob", "L"), ("lra-post", "F"),
                     ("lra-post", "A"), ("lra-fin-root", "C"),
                     ("lra-attach", "R"), ("lra-attach", "L"),
                     ("lra-centre", "C"), ("lra-engine-mount", "R"),
                     ("lra-engine-mount", "L")):
        assert expected in families, expected
    # Every tagged special node is tied into the structure: it is either a
    # chain member (attachments are inserted into the h-tail chain) or an
    # RBE2 dependent -- an orphan node would make the solve singular.
    chained = {g for ga, gb in model.cbars for g in (ga, gb)}
    tied = model.dependent_gids | {gn for gn, *_ in model.rbe2s}
    for n in model.nodes:
        assert n.gid in chained or n.gid in tied, (n.family, n.side, n.gid)


def test_the_t_tail_htail_hangs_on_the_fin_tip_not_the_fuselage():
    """concept_regional_jet declares a T-tail: the h-tail's one support is the
    centreline joint tied to the fin tip (R-6), and no lra-attach R/L pair
    exists -- a fuselage-side pair would describe a load path this airplane
    does not have."""
    model = build_lra_model(_project("concept_regional_jet.project.json"))
    families = {(n.family, n.side) for n in model.nodes if n.family}
    assert ("lra-attach", "C") in families
    assert ("lra-attach", "R") not in families
    joint = next(n for n in model.nodes if n.family == "lra-attach")
    fin_tip_ties = [gms for _gn, _cm, gms, label in model.rbe2s
                    if "fin tip" in label]
    assert fin_tip_ties and joint.gid in fin_tip_ties[0]


def test_the_split_fuselage_has_no_element_through_the_carry_through():
    """BM-2 structurally: no CBAR spans the front->rear spar region, so the
    forward and aft cantilever sums are recoverable element end forces."""
    from sloads.derived_geometry import carry_through

    project = _project("atr42_100.project.json")
    ct = carry_through(project)
    model = build_lra_model(project)
    pos = {n.gid: n.pos for n in model.nodes}
    for ga, gb in model.cbars:
        xa, xb = pos[ga][0], pos[gb][0]
        # Only fuselage elements have both ends on the centreline plane and
        # a run along x (the fin runs along z at y = 0 but shares one x).
        if abs(pos[ga][1]) < 1e-9 and abs(pos[gb][1]) < 1e-9 \
                and abs(xa - xb) > 1e-9:
            lo, hi = min(xa, xb), max(xa, xb)
            assert not (lo < ct.x_f - 1e-6 and hi > ct.x_r + 1e-6), (
                f"element {ga}-{gb} spans the carry-through "
                f"({lo:.1f}..{hi:.1f} vs spars {ct.x_f:.1f}/{ct.x_r:.1f})")


def test_the_wing_chain_starts_at_the_sob_and_inboard_strips_collapse_there():
    """R-3: the wing member's inboard-most node is the SOB, and every wing
    strip load inboard of it lands ON that node -- the sob_collapsed_load
    behaviour, produced by the one transfer rule rather than a special case."""
    from sloads.derived_geometry import sob_station
    from sloads.modules.balance import build_balanced_cases

    project = _project("atr42_100.project.json")
    sob = sob_station(project)
    model = build_lra_model(project)
    right = model.members["wing-R"]
    assert abs(right[0].pos[1] - sob.y) < 1e-6 and right[0].family == "lra-sob"

    case = build_balanced_cases(project, [])[0]
    inboard = [ld for ld in case.loads
               if ld.source.startswith("wing-") and ld.side == "R"
               and ld.y < sob.y - 1e-6]
    assert inboard, "the centre box carries strips inboard of the SOB"
    loads = transferred_case_loads(case, model)
    sob_gid_r = right[0].gid
    assert sob_gid_r in loads
    # The collapse is resultant-preserving by LM-1 (the invariant test below
    # proves it); what this pins is the ROUTING: every inboard strip's nearest
    # wing-chain node is the SOB itself, so none lands anywhere outboard.
    nearest = {min(right, key=lambda n: (n.pos[1] - ld.y) ** 2
               + (n.pos[0] - ld.x) ** 2 + (n.pos[2] - ld.z) ** 2).gid
               for ld in inboard}
    assert nearest == {sob_gid_r}


def test_missing_data_refuses_with_the_datum_named():
    """BM-3/LM-4: ga6 (no fuselage data) refuses on the SOB; a wing with no
    entered LRA refuses on the axis; a strip-pair h-tail attachment refuses.
    The error is the fix's name, never a default."""
    with pytest.raises(LraRefusal, match="side of body"):
        build_lra_model(_project("ga6_normal.project.json"))

    project = _project("atr42_100.project.json")
    project.geometry.by_name("wing").ref_axis_pct = None
    with pytest.raises(LraRefusal, match="ref_axis_pct"):
        build_lra_model(project)


def test_discrete_control_nodes_ship_as_tagged_skeleton(monkeypatch):
    """LM-6: with T6 hinge geometry entered the elevator's hinge/actuator
    nodes appear, tagged, each rigidly tied to an inserted parent node -- and
    with no chain of their own (that would be R-12's redundant hinge set)."""
    from sloads.models import TailMassInput

    project = _project("atr42_100.project.json")
    project.tail_mass.append(TailMassInput(
        surface="htail", control_load_mode="discrete",
        hinges_span_in=[30.0, 90.0], actuator_span_in=55.0))
    model = build_lra_model(project)
    hinges = [n for n in model.nodes if n.family == "lra-hinge"]
    actuators = [n for n in model.nodes if n.family == "lra-actuator"]
    assert len(hinges) == 4 and len(actuators) == 2   # both sides
    chained = {g for ga, gb in model.cbars for g in (ga, gb)}
    for n in hinges + actuators:
        assert n.gid in model.dependent_gids     # tied to the parent
        assert n.gid not in chained              # no chain of their own


# --------------------------------------------------------------------------- #
# The plan-07 invariant on the transferred set (gate 1)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", ["atr42_100.project.json",
                                     "concept_regional_jet.project.json",
                                     "dhc8_dash8.project.json",
                                     "cessna_210.project.json"])
def test_the_transferred_set_has_the_balanced_decks_resultant(example):
    """Every case, all six components, about one reference point: the LRA
    deck's card resultant equals the assembled balanced deck's -- the transfer
    is exact (LM-1) and nothing was dropped or double-routed (LM-7)."""
    from sloads.export.balanced_deck import balanced_deck

    project = _project(example)
    lra = deck_resultants(lra_model_bdf(project), _origin_ref)
    bal = deck_resultants(balanced_deck(project), _origin_ref)
    assert set(lra) == set(bal) and lra
    for sid in bal:
        a, b = lra[sid], bal[sid]
        for comp in ("fx", "fy", "fz", "mx", "my", "mz"):
            scale = a.force_scale if comp.startswith("f") else a.moment_scale
            assert closes(getattr(a, comp), getattr(b, comp), scale=scale), (
                sid, comp, getattr(a, comp), getattr(b, comp))


# --------------------------------------------------------------------------- #
# Import (note 25 §6)
# --------------------------------------------------------------------------- #
def test_an_exported_model_reimports_with_every_family_mapped():
    project = _project("concept_regional_jet.project.json")
    deck = lra_model_bdf(project)
    imported = read_lra_model(deck)
    families = {key.split()[0] for key in imported.tags}
    assert {"lra-sob", "lra-post", "lra-fin-root", "lra-attach",
            "lra-centre", "lra-gear"} <= families
    notes = validate_imported_model(project, imported)
    assert any("validated" in n for n in notes)


def test_the_imported_loads_reproduce_the_exported_resultant():
    """Export -> import -> transfer lands the same load sets: identical
    resultant per case, under the imported (here: the exported) GIDs."""
    project = _project("atr42_100.project.json")
    deck = lra_model_bdf(project)
    imported = read_lra_model(deck)
    cards = lra_loads_on_imported_model(project, imported)
    grids, _, _, f1, m1 = parse_cards(deck)
    _, _, _, f2, m2 = parse_cards(cards)
    assert set(f1) == set(f2)
    for sid in f1:
        a = resultant(f1, m1, grids, sid, _ORIGIN)
        b = resultant(f2, m2, grids, sid, _ORIGIN)
        for comp in ("fx", "fy", "fz", "mx", "my", "mz"):
            scale = a.force_scale if comp.startswith("f") else a.moment_scale
            assert closes(getattr(a, comp), getattr(b, comp), scale=scale), (
                sid, comp)


def test_a_divergent_tagged_node_fails_loudly():
    """An import whose tagged SOB sits beyond LRA_IMPORT_TOL_IN of the
    geometry-derived position raises, naming both points -- the T1 validator
    pattern; loads must never be exported onto the wrong structure."""
    project = _project("atr42_100.project.json")
    deck = lra_model_bdf(project)
    doctored = []
    hit = False
    for i, line in enumerate(deck.splitlines()):
        if not hit and line.startswith("GRID, 7001,"):
            f = [c.strip() for c in line.split(",")]
            f[4] = f"{float(f[4]) + 2 * LRA_IMPORT_TOL_IN:.6E}"
            line = ", ".join(f)
            hit = True
        doctored.append(line)
    assert hit
    imported = read_lra_model("\n".join(doctored))
    with pytest.raises(ValueError, match="disagree"):
        validate_imported_model(project, imported)


def test_a_model_with_no_grids_is_refused():
    with pytest.raises(ValueError, match="no GRID"):
        read_lra_model("$ empty\nCBAR, 1, 1, 2, 3, 0., 0., 1.\n")


if __name__ == "__main__":  # pragma: no cover - self-runner
    import subprocess

    raise SystemExit(subprocess.call(
        [sys.executable, "-m", "pytest", "-q", __file__]))
