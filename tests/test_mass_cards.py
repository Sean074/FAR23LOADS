"""CONM2 / MASSSET mass export (step C1-C4) and the mass unit channel (C2).

Plan 12 (``docs/30_future/12_conm2_mass_export_plan.md``). The point of the whole
step is to break a circularity: the ``FORCE``/``MOMENT`` deck's inertia half is
computed by the same code that writes it, so nothing outside sloads can
contradict it. A ``CONM2`` set gives sbeam an *independently parsed* mass model
to disagree with.

What is gated here, and what is not
-----------------------------------
sbeam is not a dependency of this package, so CI cannot run it. These tests
cover everything that lives on the sloads side:

* the derivation reproduces each payload case's weight always, and its xcg/zcg
  exactly whenever a ballast row exists (it is solved from all three);
* the credibility gate, pinned per fixture -- a case needing 20 % of the airplane
  as ballast is reported, not exported;
* the mass channel's dimensional identities, in both unit systems (C-5);
* **no overlay card is left unreferenced** -- sbeam's baseline is every CONM2 no
  MASSSET names, so an unreferenced overlay silently joins every case;
* **no deck applies both the total load set and an accelerated mass set** (C-6).

The external half was verified by hand against sbeam's own parser and
grid-point-weight generator on 2026-08-08 and is recorded in the history entry --
the same precedent as C4's "the deck parses and solves in sbeam".
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io, mass_distribution as md  # noqa: E402
from sloads.export.bands import IdKind, bands_of_kind  # noqa: E402
from sloads.export import mass_cards as mc  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.export.equilibrium import parse_cards  # noqa: E402
from sloads.cg_cases import flight_cases  # noqa: E402
from sloads.units import (  # noqa: E402
    G_IN_S2,
    Channel,
    UnitSystem,
    deliverable_units,
)

from imperial_baseline import EXAMPLES  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SYSTEMS = (UnitSystem.IMPERIAL, UnitSystem.SI)


def _project(example: str):
    return io.load_project(os.path.join(_ROOT, "examples", example))


# --------------------------------------------------------------------------- #
# C2 -- the mass unit channel
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_solver_mass_channel_is_dimensionally_consistent(system):
    """``force / (mass × length) == g`` and ``mass_inertia == mass × length²``.

    The mass analogue of the D-19 moment identity, and the reason it matters is
    the same: ``CONM2``'s ``M`` is *mass* while the database stores *weight*, so
    a set written with a weight-valued ``M`` accelerates to 386× the right force
    in a file that parses cleanly. Both factors are derived rather than quoted,
    which is what makes this exact rather than approximate.
    """
    u = deliverable_units(system, Channel.SOLVER)
    assert u.is_mass_consistent
    assert u.force.factor / (u.mass.factor * u.length.factor) == pytest.approx(
        G_IN_S2, rel=1e-15)
    assert u.mass_inertia.factor == pytest.approx(
        u.mass.factor * u.length.factor ** 2, rel=1e-15)


def test_the_two_systems_agree_on_gravity_exactly():
    """The identity above must give the *same* number in both systems.

    One standard gravity, expressed per length unit and derived from a single
    constant. Quoting 386.088 alongside 9806.65 would break this in the eighth
    digit — harmless-looking, and precisely the kind of drift the units history
    is a cautionary tale about.
    """
    def accel(system):
        u = deliverable_units(system, Channel.SOLVER)
        return u.force.factor / (u.mass.factor * u.length.factor)

    assert accel(UnitSystem.IMPERIAL) == accel(UnitSystem.SI)


#: One standard gravity **in each deck's own units** — the number a ``GRAV``
#: card must carry. Quoted here on purpose: this is the drift guard for
#: ``DeliverableUnits.gravity``, so deriving it the way the property does would
#: assert nothing. ISO 80000 standard gravity, per :data:`sloads.units.G_MM_S2`.
_DECK_GRAVITY = {UnitSystem.IMPERIAL: 386.08858267716535,
                 UnitSystem.SI: 9806.65}


@pytest.mark.parametrize("system", _SYSTEMS)
def test_deck_gravity_is_g_in_the_decks_own_length_unit(system):
    """``units.gravity`` is ``force/mass`` — **not** the identity above.

    The two differ by exactly ``length.factor``, which is 1.0 in Imperial and
    25.4 in SI, so confusing them is invisible on one side and 25.4× low on the
    other. That is what shipped: the SI mass-check deck wrote 386.0886 under a
    header claiming mm/s² (2026-08-10 review, finding C1). Pinned per system,
    against a quoted figure, because a derived expectation would have agreed
    with the defect.
    """
    u = deliverable_units(system, Channel.SOLVER)
    assert u.gravity == pytest.approx(_DECK_GRAVITY[system], rel=1e-12)
    assert u.gravity == pytest.approx(G_IN_S2 * u.length.factor, rel=1e-15)


@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_human_mass_channel_is_refused_by_the_writer(system):
    """The human channel's mass is a pound (or a kilogram) — a *weight*.

    It reads correctly in a report and is catastrophically wrong in a CONM2
    card, so the writer refuses it at the boundary rather than trusting callers,
    exactly as ``coordinates._checked`` does for the moment channel."""
    u = deliverable_units(system, Channel.HUMAN)
    assert not u.is_mass_consistent
    with pytest.raises(ValueError, match="not.*consistent"):
        mc._checked_mass_units(u)


def test_imperial_mass_is_deliberately_not_the_identity():
    """Every other dimension's Imperial factor is 1.0; mass cannot be.

    The canonical stored quantity is a pound of *force*, so a consistent
    Imperial deck's mass unit is a division by g away. Pinned so the exemption
    stays a decision rather than looking like an oversight."""
    u = deliverable_units(UnitSystem.IMPERIAL, Channel.SOLVER)
    assert u.force.factor == u.length.factor == u.moment.factor == 1.0
    assert u.mass.factor == pytest.approx(1.0 / G_IN_S2)


# --------------------------------------------------------------------------- #
# C1 -- the per-case derivation
# --------------------------------------------------------------------------- #
#: Which payload cases each fixture can actually produce as a loading, pinned.
#: The rest are reported, not exported — a case whose CG the weight database
#: cannot reach is a fact about the fixture, and burying it in a skip would hide
#: exactly what the derivation is for. ga6 (the Appendix A airplane) derives all
#: four, which is why it carries the export's oracle weight.
_DERIVABLE = {
    "ga6_normal.project.json": ["CG1", "CG2", "CG3", "CG4"],
    "cessna_210.project.json": [],
    "atr42_100.project.json": ["CGaft"],
    "dhc8_dash8.project.json": [],
    "concept_heavy.project.json": [],
    "concept_regional_jet.project.json": ["CG1 aft heavy", "CG2 fwd heavy"],
}


@pytest.mark.parametrize("example", EXAMPLES)
def test_which_payload_cases_are_derivable_is_pinned(example):
    got = [ld.name for ld in md.derive_case_loadings(_project(example))
           if ld.derivable]
    assert got == _DERIVABLE[example], example


@pytest.mark.parametrize("example", EXAMPLES)
def test_a_derived_loading_reproduces_its_case(example):
    """Weight always exactly; CG exactly **when a ballast row exists**.

    The ballast is solved from the case's weight, xcg and zcg, so a ballasted
    loading matches all three to machine precision — that is the construction
    this guards. A loading that already weighs the case weight has no ballast to
    move it, and then the match is only within the search's own tolerance: ga6's
    CG4 is the minimum-flight-weight loading at station 73.0924 against a case
    entered as 73.09. What is exported is the real loading, not one bent to the
    nominal number, so the small difference is carried rather than hidden.
    """
    p = _project(example)
    cases = {c.name: c for c in flight_cases(p)}
    for loading in md.derive_case_loadings(p):
        if not loading.derivable:
            continue
        case = cases[loading.name]
        assert loading.weight_lb == pytest.approx(case.weight_lb, rel=1e-12)
        if loading.ballast is not None:
            assert loading.cg_x == pytest.approx(case.xcg, rel=1e-12)
            assert loading.cg_z == pytest.approx(case.zcg, rel=1e-12)
        else:
            assert abs(loading.cg_x - case.xcg) <= md._CG_MATCH_TOL


@pytest.mark.parametrize("example", EXAMPLES)
def test_every_rejected_case_says_why(example):
    """A case that is not exported carries a reason, never a silent absence."""
    for loading in md.derive_case_loadings(_project(example)):
        if not loading.derivable:
            assert loading.note, f"{example} {loading.name}: rejected with no reason"


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_credibility_gate_is_what_rejects_the_rest(example):
    """Every derivable case sits under the gate; every rejected one is over it
    (or unreachable). Pins the gate as the actual discriminator rather than an
    ornament beside some other filter."""
    for loading in md.derive_case_loadings(_project(example)):
        if loading.derivable:
            assert loading.ballast_fraction <= md.BALLAST_CREDIBLE_FRACTION
        elif loading.items:
            assert loading.ballast_fraction > md.BALLAST_CREDIBLE_FRACTION


def test_ballast_never_floats_outside_the_airframe():
    """Solving the z-moment happily returns a waterline above the fin — dhc8's
    CGmid wants 1500 lb at waterline 373, 143 in over the tail. The extent gate
    is what stops a derived loading being arithmetically right and physically
    absurd."""
    for example in EXAMPLES:
        p = _project(example)
        zs = [it.z for it in p.weight.items]
        for loading in md.derive_case_loadings(p):
            if loading.ballast is not None:
                assert min(zs) <= loading.ballast.z <= max(zs), \
                    f"{example} {loading.name}"


# --------------------------------------------------------------------------- #
# C3 -- the cards
# --------------------------------------------------------------------------- #
def _fixtures_with_cards():
    """Examples with at least one *derivable* loading — the rest export nothing."""
    return [e for e in EXAMPLES
            if any(ld.derivable for ld in md.derive_case_loadings(_project(e)))]


@pytest.mark.parametrize("example", _fixtures_with_cards())
def test_no_overlay_card_is_left_unreferenced(example):
    """**The defect sbeam's own GPWG caught, now structurally impossible.**

    sbeam decides overlay-only status by *reference*: a CONM2 that no MASSSET
    ADD row names belongs to the baseline, and is therefore in **every** payload
    case. Exporting every discretionary item — including ga6's own ``Ballast``
    row, superseded by the per-case ballast this step derives — made sbeam
    recover 9.0083 slinch against sloads' 8.8063 for CG1: 78 lb too much, in
    every case, from a deck that parsed without complaint.
    """
    assert mc.unreferenced_overlay_eids(_project(example)) == []


@pytest.mark.parametrize("example", _fixtures_with_cards())
@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_card_set_reproduces_each_loading(example, system):
    """Σ CONM2 mass and its CG equal the loading's, in deck units.

    Summed from the emitted values the way a consumer would, so a formatting or
    unit error at the boundary shows up here rather than in a solver.
    """
    p = _project(example)
    u = deliverable_units(system, Channel.SOLVER)
    cards, loadings = mc.mass_cards(p)
    for i, loading in enumerate(loadings):
        eids = set(mc._overlay_eids(cards, loading, i))
        aboard = [c for c in cards if not c.overlay or c.eid in eids]
        mass = sum(c.item.weight_lb for c in aboard) * u.mass.factor
        props = mc.mass_properties(p, loading, system)
        assert mass == pytest.approx(props["mass"], rel=1e-12)
        assert props["weight"] == pytest.approx(loading.weight_lb, rel=1e-12)


@pytest.mark.parametrize("example", _fixtures_with_cards())
def test_mass_eids_are_disjoint_from_every_gid_band(example):
    """Every emitted EID sits in a registered ``clear_of_gids`` mass band, so no
    GID band -- present or future -- can collide with it.

    This test used to hand-enumerate the GID bands it compared against, and so
    could only ever see the families its author remembered (it omitted the
    balanced deck entirely; review F-C1/F-G3). The band-to-band question now
    belongs to ``tests/test_bands.py``, which asks it of the whole registry;
    what stays here is that the cards this fixture actually writes land inside
    the bands that promise it.
    """
    p = _project(example)
    cards, _ = mc.mass_cards(p)
    eids = {c.eid for c in cards}
    assert len(eids) == len(cards), "duplicate EID"
    mass_bands = [b for b in bands_of_kind(IdKind.EID)
                  if b.owner.startswith("mass_cards.")]
    assert all(b.clear_of_gids for b in mass_bands), "a mass EID band stopped "\
        "promising to stay clear of GID space"
    for eid in eids:
        assert any(eid in b for b in mass_bands), f"EID {eid} is in no mass band"
    every_gid = [b for b in bands_of_kind(IdKind.GID)]
    assert not [e for e in eids if any(e in b for b in every_gid)]


@pytest.mark.parametrize("example", _fixtures_with_cards())
@pytest.mark.parametrize("system", _SYSTEMS)
def test_every_conm2_hangs_on_a_grid_the_deck_defines(example, system):
    """A mass on a node no file defines cannot be placed — the same defect the
    body and tail load decks carried before the export-boundary step."""
    p = _project(example)
    text = mc.mass_check_deck(p, system=system)
    grids, *_ = parse_cards(text)
    for line in text.splitlines():
        if line.startswith("CONM2"):
            gid = int(line.split(",")[2])
            assert gid in grids, f"{example}: CONM2 on undefined GID {gid}"


# --------------------------------------------------------------------------- #
# C6 (sloads side) -- the no-double-count guarantee
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _fixtures_with_cards())
@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_mass_check_deck_carries_no_load_cards(example, system):
    """Decision C-6, made structural rather than warned about.

    The total FORCE/MOMENT set already contains inertia; a subcase that applied
    it *and* accelerated the CONM2 masses would count inertia twice — and the
    result reads as a heavier airplane, not as a crash. So the mass-check deck
    has no load cards at all, which is a property a test can assert and a
    warning is not.
    """
    text = mc.mass_check_deck(_project(example), system=system)
    _, _, _, forces, moments = parse_cards(text)
    assert not forces and not moments
    assert "GRAV" in text and "MASSSET" in text


@pytest.mark.parametrize("example", _fixtures_with_cards())
@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_grav_card_carries_g_in_deck_units(example, system):
    """The magnitude on the card itself, in both systems — the C1 gate.

    The deck's only previous ``GRAV`` assertion was that the string appeared,
    which a 25.4×-low acceleration satisfies perfectly. Asserted on the parsed
    card and on the ``$`` header line together, since it was the header that
    made the wrong number look right.
    """
    u = deliverable_units(system, Channel.SOLVER)
    text = mc.mass_check_deck(_project(example), system=system, nz=2.5)
    cards = [ln for ln in text.splitlines() if ln.startswith("GRAV")]
    assert cards
    for line in cards:
        f = [c.strip() for c in line.split(",")]
        assert float(f[3]) == pytest.approx(2.5 * _DECK_GRAVITY[system], rel=1e-6)
        assert [float(c) for c in f[4:7]] == [0.0, 0.0, -1.0]
    assert f"= {2.5 * u.gravity:.4f} {u.length.label}/s^2" in text


@pytest.mark.parametrize("example", _fixtures_with_cards())
def test_the_inertia_only_set_says_it_is_not_a_deliverable(example):
    """It exists to be compared against, not applied — and says so in-band,
    because a file forwarded on its own has only its header to go on."""
    text = mc.inertia_only_cards(_project(example))
    assert "COMPARISON ARTIFACT ONLY" in text
    assert "counts the inertia twice" in text
    _, _, _, forces, _ = parse_cards(text)
    assert forces


@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_inertia_only_set_sums_to_the_beam_weight(system):
    """Σ Fz = −W_beam × nz: sloads' side of the comparison, in deck units."""
    p = _project("ga6_normal.project.json")
    u = deliverable_units(system, Channel.SOLVER)
    beam = sum(s.weight_lb for s in md.fuselage_beam_stations(p))
    _, _, _, forces, _ = parse_cards(
        mc.inertia_only_cards(p, system=system, nz=2.5))
    total = sum(sc * v[2] for cards in forces.values() for _, sc, v in cards)
    assert total == pytest.approx(-beam * 2.5 * u.force.factor, rel=1e-6)


@pytest.mark.parametrize("example", _fixtures_with_cards())
@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_per_case_inertia_set_is_the_mass_the_masset_carries(example, system):
    """``inertia_only_cards(loading=...)`` is that case's mass, node by node.

    The gross form of these cards is the Ch 15 beam table — every non-wing item,
    no payload case — and the ``CONM2`` set is per case *and* carries the wing
    items on the nearest beam node. Two different airplanes, so the round-trip
    comparison had nothing exact to be equal to. This is the form that does:
    Σ Fz is the loading's own weight (ballast included, wing included), and every
    card sits on a node the mass model actually attaches to.
    """
    p = _project(example)
    u = deliverable_units(system, Channel.SOLVER)
    cards, _ = mc.mass_cards(p)
    attached = {c.gid for c in cards}
    for loading in [ld for ld in md.derive_case_loadings(p) if ld.derivable]:
        text = mc.inertia_only_cards(p, system=system, nz=2.5, loading=loading)
        _, _, _, forces, _ = parse_cards(text)
        rows = [row for sid_rows in forces.values() for row in sid_rows]
        total = sum(sc * v[2] for _, sc, v in rows)
        assert total == pytest.approx(
            -loading.weight_lb * 2.5 * u.force.factor, rel=1e-6), loading.name
        assert {gid for gid, _, _ in rows} <= attached, loading.name
        assert loading.name in text


def test_the_gross_inertia_set_is_unchanged_by_the_per_case_form():
    """The default artifact is byte-identical — the CLI and the page still write
    the gross beam table, and the per-case form is strictly an addition."""
    p = _project("ga6_normal.project.json")
    stations = md.fuselage_beam_stations(p)
    _, _, _, forces, _ = parse_cards(mc.inertia_only_cards(p))
    rows = [row for sid_rows in forces.values() for row in sid_rows]
    assert [gid for gid, _, _ in rows] == [
        sb.beam_station_gid(i) for i in range(len(stations))]
    assert [round(-sc * v[2], 6) for _, sc, v in rows] == [
        round(s.weight_lb, 6) for s in stations]


def test_the_check_deck_beam_is_massless():
    """A CBAR with density would add mass to the MASSSET baseline and corrupt
    the comparison the deck exists to make. RHO stays 0.0."""
    text = mc.mass_check_deck(_project("ga6_normal.project.json"))
    mat1 = [ln for ln in text.splitlines() if ln.startswith("MAT1")]
    assert mat1 and float(mat1[0].split(",")[-1]) == 0.0


def test_a_project_with_no_derivable_case_refuses_a_check_deck():
    """No credible loading means nothing to check — say so, rather than emit a
    deck with no subcases that a consumer would take as a clean result."""
    with pytest.raises(ValueError, match="no payload case is derivable"):
        mc.mass_check_deck(_project("cessna_210.project.json"))


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
