"""The mass SSOT (step B1): ``weight.items`` -> per-component station inertia.

Plan 11 decision **B-2**. Before this step the suite carried two mass models —
the itemized ``weight.items`` database and a short hand-entered
``fuselage_mass.stations`` lump table — and **nothing compared them**. The
entered table was short of the item model by 10 % to 100 % of the beam on every
shipped fixture, so every fuselage inertia load, shear, bending moment and
exported body card was computed from a beam carrying less mass than the airplane
weighed.

This module is the structural guard half of the fix (``CLAUDE.md`` required
practice 3: a single owner *plus* a drift test). The invariants:

* the partition is complete — wing items + beam stations == every item == W;
* the wing tie — ``Σ(items tagged wing) == 2 × (panel + concentrated)``, the two
  models of the same physical wing agreeing;
* the derived beam is what ``body_loads`` actually integrates;
* an untagged (pre-B1) file still loads, and its inference is conservative.

The three fixtures where the wing tie does **not** hold are pinned with their
exact gap rather than excused — see
:func:`test_the_unmodelled_wing_mass_is_pinned_per_fixture`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io, mass_distribution as md  # noqa: E402
from sloads.models import MassComponent  # noqa: E402
from sloads.modules.body_loads import build_body_loads  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402

from imperial_baseline import EXAMPLES  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _project(example: str):
    return io.load_project(os.path.join(_ROOT, "examples", example))


# --------------------------------------------------------------------------- #
# Tagging
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_every_shipped_item_is_explicitly_tagged(example):
    """No shipped fixture relies on inference.

    ``infer_component`` exists for pre-B1 files, and it is a fallback with a
    documented blind spot (every item sits at ``y = 0``, so nothing distinguishes
    a wing-mounted engine from a fuselage one). Shipped data must not depend on
    it, or the SSOT's authority rests on a guess.
    """
    dist = md.distribution(_project(example))
    assert dist.inferred == (), f"{example}: untagged items {list(dist.inferred)}"


def test_an_untagged_file_gets_a_complete_beam_and_a_loud_wing_tie():
    """A pre-B1 project has no ``component`` anywhere and must still work.

    The fallback refuses to guess and puts every untagged pound on the fuselage
    beam — so the beam is *complete* (heavier than the truth by the wing panel,
    never lighter, never mis-attributed to a surface). What must **not** happen
    is an untagged file passing as tagged, so the wing tie fails loudly: nothing
    is claimed for the wing, and the tie reads 0 against 2 x panel_weight_lb.
    That failure is the instruction to tag the items.
    """
    p = _project("ga6_normal.project.json")
    for it in p.weight.items:
        it.component = None
    dist = md.distribution(p)
    assert len(dist.inferred) == len(p.weight.items)
    assert not dist.by_component[MassComponent.WING], \
        "the fallback must never claim an item for the wing on y=0 data"
    assert dist.weight(MassComponent.FUSELAGE) == sum(it.weight_lb for it in p.weight.items)
    assert md.partition_closes(p).ok, "the partition still closes"

    tie = md.wing_mass_tie(p)
    assert tie is not None and not tie.ok
    assert tie.got == 0.0 and tie.want == 330.0


def test_an_explicit_tag_beats_the_fallback():
    p = _project("ga6_normal.project.json")
    item = next(it for it in p.weight.items if it.name == "Wing, outboard")
    assert item.component is MassComponent.WING
    assert md.component_of(item, p) is MassComponent.WING
    assert md.infer_component(item, p) is MassComponent.FUSELAGE
    item.component = None
    assert md.component_of(item, p) is MassComponent.FUSELAGE


def test_the_component_tag_round_trips_through_json():
    """``component`` must survive save/load, or the SSOT is one file-write from
    reverting to inference."""
    p = _project("atr42_100.project.json")
    before = [(it.name, it.component) for it in p.weight.items]
    after = io.project_from_dict(io.project_to_dict(p))
    assert [(it.name, it.component) for it in after.weight.items] == before
    assert any(c is MassComponent.WING for _, c in before)


# --------------------------------------------------------------------------- #
# The partition
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_partition_closes(example):
    """wing + fuselage beam == every item == W, to the pound.

    The structural guard on the partition: no item is lost between the two
    distributions and none is counted twice. Fails if a member is added to
    ``MassComponent`` without a home in ``BEAM_COMPONENTS``.
    """
    check = md.partition_closes(_project(example))
    assert check.ok, f"{example}: {check.detail}"


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_beam_carries_the_empennage_but_not_the_wing(example):
    """The h-tail and v-tail hang off the aft fuselage, so the beam carries them;
    the wing enters as the carry-through *reaction*, never as mass.

    Applying the wing as both would double-count it — the seam rule (plan 11 §4:
    *a load that a free-body cut introduces is never applied in the assembled
    model*).
    """
    p = _project(example)
    dist = md.distribution(p)
    beam = sum(s.weight_lb for s in md.derived_fuselage_stations(p))
    want = dist.weight(*md.BEAM_COMPONENTS)
    assert MassComponent.WING not in md.BEAM_COMPONENTS
    assert abs(beam - want) < 1e-6, example


def test_stations_at_the_same_x_merge_into_one_node():
    """ga6 has four items at x = 97/1 (the gear) and two at x = 75 (the pilots);
    a beam node is a station, not an item."""
    p = _project("ga6_normal.project.json")
    stations = md.derived_fuselage_stations(p)
    xs = [s.x for s in stations]
    assert xs == sorted(xs), "nose->tail"
    assert len(xs) == len(set(xs)), "no duplicate stations"
    assert len(stations) < len(p.weight.items)
    gear = next(s for s in stations if abs(s.x - 97.0) < 1e-9)
    assert gear.weight_lb == 45.0 + 110.0     # wheel + structure, one node


# --------------------------------------------------------------------------- #
# The wing tie, and the fixtures where it does not hold
# --------------------------------------------------------------------------- #
#: Fixtures whose ``weight.items`` cannot show all of WINGINER's concentrated
#: wing mass, and the exact shortfall in lb. Every gap is wing-tank fuel sitting
#: inside an undivided ``"Fuel to gross"`` row; the engine+nacelle half of the
#: twins' concentrated model reconciles exactly (atr42 ``Engines (2)`` 1780 +
#: ``Nacelles (2)`` 600 = 2 x 1190). Closing these means splitting item rows into
#: wing-tank and body-tank fractions, which is new fixture data with no oracle —
#: so it is filed on the backlog, and pinned here rather than excused.
_UNMODELLED_WING_MASS = {
    "atr42_100.project.json": 3800.0,     # "wing fuel" 1900 lb/side
    "dhc8_dash8.project.json": 4000.0,    # "wing fuel" 2000 lb/side
    "concept_heavy.project.json": 1200.0,  # "fuel" 600 lb/side
}


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_wing_tie_holds_where_the_item_model_is_complete(example):
    """``Σ(items tagged wing) == 2 × (panel_weight_lb + Σ concentrated)``.

    Both of WINGINER's terms are **per side**, so the airplane carries twice
    their sum — and that is what the item database must show if the two models
    describe one wing. Exact on the three fixtures whose data is complete.
    """
    if example in _UNMODELLED_WING_MASS:
        pytest.skip(f"{example}: see test_the_unmodelled_wing_mass_is_pinned_per_fixture")
    check = md.wing_mass_tie(_project(example))
    if check is None:
        pytest.skip(f"{example}: no wing mass input")
    assert check.ok, f"{example}: {check.detail}"


@pytest.mark.parametrize("example", sorted(_UNMODELLED_WING_MASS))
def test_the_unmodelled_wing_mass_is_pinned_per_fixture(example):
    """The three fixtures the tie fails on, pinned to the pound.

    Asserting the *exact* gap rather than skipping: the number is a fact about
    the fixture, it has one identified cause each, and if it moves — in either
    direction — the suite says so. When the item rows are eventually split into
    wing-tank and body-tank fuel, this test goes red and is deleted.
    """
    p = _project(example)
    check = md.wing_mass_tie(p)
    assert check is not None and not check.ok, \
        f"{example}: the wing tie now holds — delete this pin and the skip above"
    assert md.unmodelled_wing_mass(p) == pytest.approx(_UNMODELLED_WING_MASS[example])
    # It is entirely wing-tank fuel: the engine/nacelle half reconciles exactly.
    assert check.want - check.got == pytest.approx(_UNMODELLED_WING_MASS[example])


# --------------------------------------------------------------------------- #
# Derived beam vs entered override
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_shipped_fixtures_use_the_derived_beam(example):
    p = _project(example)
    if p.fuselage_mass is not None:
        assert not p.fuselage_mass.stations_are_override
    assert md.fuselage_beam_stations(p) == md.derived_fuselage_stations(p)


def test_an_explicit_override_wins_and_is_still_reconciled():
    """The entered table is a deliberate act, not a stale default — but the
    difference from the SSOT is reported either way, so an override is a decision
    made in front of the number rather than instead of it."""
    p = _project("ga6_normal.project.json")
    p.fuselage_mass.stations_are_override = True
    assert md.fuselage_beam_stations(p) == p.fuselage_mass.stations
    check = md.fuselage_reconciliation(p)
    assert check is not None and not check.ok
    assert check.gap == pytest.approx(2578.0 - 3070.0)


def test_a_project_with_no_items_falls_back_to_the_entered_table():
    """The SSOT does not strand a project that only ever had the lump table."""
    p = _project("ga6_normal.project.json")
    entered = list(p.fuselage_mass.stations)
    p.weight = None
    assert md.derived_fuselage_stations(p) == []
    assert md.fuselage_beam_stations(p) == entered


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_entered_tables_are_all_short_of_the_item_model(example):
    """Pins the finding that motivated B1, per fixture.

    Every hand-entered table understates the beam — never overstates it — which
    is the signature of items being forgotten rather than of a different
    modelling choice. Recorded so the fixtures cannot quietly drift back.
    """
    p = _project(example)
    check = md.fuselage_reconciliation(p)
    if check is None:
        pytest.skip(f"{example}: no entered station table to compare")
    assert check.gap < 0, f"{example}: entered table now exceeds the item model"
    assert not check.ok, f"{example}: gap closed — update this test"


# --------------------------------------------------------------------------- #
# The consumer
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_body_loads_integrates_the_ssot_beam(example):
    """``body_loads`` reads the SSOT, not ``fuselage_mass.stations``.

    The point of the whole step: the module that computes fuselage shear and
    bending now integrates every pound the airplane weighs outside the wing.
    """
    p = _project(example)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    if p.envelope.critical is None:
        p.envelope.critical = build_critical(p)
    results = build_body_loads(p)
    assert results
    beam = md.fuselage_beam_stations(p)
    mass_x = {round(s.x, 6) for s in beam}
    for r in results:
        got = {round(s.x, 6) for s in r.stations if s.source == "mass"}
        assert mass_x <= got | {round(s.x, 6) for s in r.stations}, example
        # ...and the beam still closes free-free, which is the Ch 15 invariant.
        scale = max(abs(s.fz) for s in r.stations)
        assert abs(sum(s.fz for s in r.stations)) <= 1e-6 * scale + 1e-6


def test_concept_heavy_gained_a_fuselage_it_never_had():
    """The fixture with no ``fuselage_mass.stations`` at all now has a beam.

    It was the one example with no body deck, purely because the only input the
    Ch 15 module read was a table nobody had entered. 16,200 lb of airplane had
    no fuselage loads; it does now.
    """
    p = _project("concept_heavy.project.json")
    assert not (p.fuselage_mass and p.fuselage_mass.stations)
    beam = md.fuselage_beam_stations(p)
    assert beam
    assert sum(s.weight_lb for s in beam) == pytest.approx(16200.0)


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_component_summary_covers_the_whole_airplane(example):
    rows = md.component_summary(_project(example))
    assert rows
    total = sum(float(r["Weight (lb)"]) for r in rows)
    assert total == pytest.approx(md.distribution(_project(example)).weight(), rel=1e-6)


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
