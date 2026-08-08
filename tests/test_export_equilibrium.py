"""Export-boundary closure gate: every deck, every example, both unit systems.

Concept mode has no printed oracle, so a *stated physics-closure gate in CI* is
what stands in for one (``CLAUDE.md`` required practice 2). Four such checks
already existed, but all four were force-only, Imperial-only, and hand-rolled
four separate times. This module is the gate in its intended form -- one
parameterised sweep over

    every shipped example  x  {Imperial, SI}  x  {wing, body, tail, control}

asserting that each deck's Σ``FORCE`` **and** Σ``MOMENT``, re-derived from the
deck's own card text via :mod:`sloads.export.equilibrium`, equal that
component's own stated resultant. What it adds over what existed:

* **moment closure at all** -- nothing verified a moment from any deck's text.
  In particular the body deck's ``$`` header has claimed "Terminal Myy ...
  (moment equilibrium)" since step C6 with nothing checking it;
* **SI** -- ``system=`` was never varied, so a unit set with
  ``moment.factor != force.factor x length.factor`` (the exact D-19 failure mode)
  passed the whole suite, force-only sums being blind to it;
* **the ga6 oracle fixture's body / tail / control decks**, previously covered on
  the concept fixture only.

Reference points are the per-component convention (``CONVENTIONS.md``; design
note ``docs/30_future/07_export_equilibrium_invariant_plan.md`` §3, E-2): wing ->
its root station, body -> its aft-most station, tail -> its leading-edge chord
station. Tolerances are :mod:`sloads.export.equilibrium`'s, not this file's.

Physics basis: Ref 1 Ch 14 (net wing loads), Ch 15 p103 (the free-free fuselage
beam), Ch 10 (chordwise tail distribution).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.export.coordinates import to_force, to_grid, to_moment  # noqa: E402
from sloads.export.equilibrium import (  # noqa: E402
    closes,
    deck_resultants,
    parse_cards,
    ref_aftmost_loaded,
    ref_first_loaded,
)
from sloads.modules.aileron import build_aileron  # noqa: E402
from sloads.modules.body_loads import build_body_loads  # noqa: E402
from sloads.modules.flap import build_flap  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402
from sloads.modules.tab import build_tabs  # noqa: E402
from sloads.modules.taildist import build_tail_chordwise  # noqa: E402
from sloads.units import Channel, UnitSystem, deliverable_units  # noqa: E402

from imperial_baseline import EXAMPLES, _try  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SYSTEMS = (UnitSystem.IMPERIAL, UnitSystem.SI)


def _project(example: str):
    """One example with its envelope + critical set materialised."""
    p = io.load_project(os.path.join(_ROOT, "examples", example))
    if p.envelope is None:
        p.envelope = build_envelope(p)
    if p.envelope.critical is None:
        p.envelope.critical = build_critical(p)
    return p


def _components(example: str):
    """``(wing, body, tail, control)`` for one example; a missing slice is ``[]``.

    ``_try`` is ``imperial_baseline``'s: an example that lacks the inputs for a
    component has no deck, and the sweep skips it *with a reason* rather than
    quietly passing an empty assertion (see :func:`test_every_example_has_decks`,
    which pins what each fixture is expected to produce)."""
    p = _project(example)
    net = _try(build_net_loads, p)
    wing = loads_ref_axis_results(p, net.wing_net) if net is not None else []
    body = _try(build_body_loads, p) or []
    tail = _try(build_tail_chordwise, p) or []
    control = []
    for build in (build_aileron, build_flap, build_tabs):
        control += _try(build, p) or []
    return wing, body, tail, control


_CACHE = {}


def _cached(example: str):
    if example not in _CACHE:
        _CACHE[example] = _components(example)
    return _CACHE[example]


def _units(system):
    return deliverable_units(system, Channel.SOLVER)


def _skip_if_empty(results, example, what):
    if not results:
        pytest.skip(f"{example}: no {what} slice (fixture carries no {what} inputs)")


# --------------------------------------------------------------------------- #
# Wing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_wing_deck_resultants(example, system):
    """Wing: Σ``FORCE`` = SF x root ``Sz``/``Sx``, and the ``MOMENT`` set = SF x
    root ``Myy``.

    ``Myy`` is checked as the applied-``MOMENT``-card sum, **not** the full
    rigid-body ``m.y``: the exported torsion is a beam torsion about the loads
    reference axis, and the wing's chordwise ``x`` and dihedral ``z`` vary along
    the span, so the rigid transfer term is of the same order as the torsion
    itself. The deck's header claims the card sum, and that is what is asserted.

    ``Mxx`` closure is asserted separately, in
    :func:`test_wing_deck_bending_closure` -- it does **not** hold on a wing
    carrying concentrated masses, which this sweep is what found.
    """
    wing, _, _, _ = _cached(example)
    _skip_if_empty(wing, example, "wing")
    u = _units(system)
    # The stick deck is the wing artifact carrying GRID cards, so it is the one
    # that can be moment-checked from its own text.
    text = sb.stick_model_bdf(wing, sid_base=1, system=system)
    res = deck_resultants(text, ref_first_loaded)
    assert sorted(res) == sorted(sb._sid(1, i, r) for i, r in enumerate(wing))

    for idx, r in enumerate(wing):
        got = res[sb._sid(1, idx, r)]
        root, sf = r.stations[0], r.safety_factor
        want_fx, _, want_fz = to_force(root.sx * sf, 0.0, root.sz * sf, u)
        _, want_myy, _ = to_moment(0.0, root.myy * sf, 0.0, u)
        where = f"{example} {system.value} wing {r.case}"
        assert closes(got.fz, want_fz, scale=got.force_scale), f"{where} Fz"
        assert closes(got.fx, want_fx, scale=got.force_scale), f"{where} Fx"
        assert closes(got.m0y, want_myy, scale=got.moment_scale), f"{where} Myy"


def _has_concentrated_wing_mass(example: str) -> bool:
    """True if the fixture hangs point masses (engine, gear, fuel, store) on the
    wing -- ``atr42_100``, ``dhc8_dash8``, ``concept_heavy`` do; the rest do not."""
    wm = _project(example).wing_mass
    return bool(wm and wm.concentrated)


@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_wing_deck_bending_closure(example, system):
    """The ``FORCE`` set's moment about the root station = SF x root ``Mxx``...

    ...**except on a wing carrying concentrated masses**, where it does not, and
    that is a defect this sweep found rather than a tolerance to widen.

    WINGINER adds a concentrated wing mass to the cumulative bending at its true
    spanwise station (``mxx[i] += w * (cw.y - ye[i])``, WINGINER.BAS 1180-1270).
    The export recovers nodal loads as *increments of the cumulative shear*
    (``dFz[i] = sz[i] - sz[i+1]``), so the point mass is picked up entirely at the
    outermost station strictly inboard of it -- its lever arm moves inboard by up
    to one strip width. Shear still closes exactly (the increments telescope);
    bending does not. On ``atr42_100`` (two engine masses, 24.2 in strips) the
    exported root bending is 1.91 % high; ``dhc8_dash8`` 1.11 %,
    ``concept_heavy`` 0.44 %. Direction is consistent: always high, because the
    mass always moves inboard.

    Nothing shipped is wrong today for the fixtures the oracle covers (ga6 and
    cessna_210 have no concentrated masses and close exactly), but a deck for a
    twin sizes wing structure to a bending moment ~2 % above the NETLOADS value
    the report prints beside it. The fix is an export-side change -- split each
    concentrated mass between its bracketing station nodes -- and it is a physics
    change to a deliverable, so it gets its own step and design note. Filed:
    ``docs/30_future/00_backlog.md``, "Concentrated wing masses are smeared to
    the nearest node in the exported bending".

    The negative branch is deliberately strict: when the fix lands, this test
    fails and stops being an exception.
    """
    wing, _, _, _ = _cached(example)
    _skip_if_empty(wing, example, "wing")
    u = _units(system)
    res = deck_resultants(sb.stick_model_bdf(wing, sid_base=1, system=system),
                          ref_first_loaded)
    smeared = _has_concentrated_wing_mass(example)
    for idx, r in enumerate(wing):
        got = res[sb._sid(1, idx, r)]
        want, _, _ = to_moment(r.stations[0].mxx * r.safety_factor, 0.0, 0.0, u)
        where = f"{example} {system.value} wing {r.case} Mxx"
        if smeared:
            assert not closes(got.mx, want, scale=got.moment_scale), (
                f"{where}: bending now closes on a concentrated-mass wing -- if "
                "the export discretisation was fixed, delete this branch")
            # ...and the gap is the smear, not something new: always high, and
            # bounded by one strip width of the total exported shear.
            dy = r.stations[1].y - r.stations[0].y
            bound = abs(to_grid(dy, 0.0, 0.0, u)[0] * got.fz)
            assert 0.0 < got.mx - want < bound, f"{where}: gap {got.mx - want}"
        else:
            assert closes(got.mx, want, scale=got.moment_scale), where


@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_wing_card_deck_force_matches_stick_deck(example, system):
    """The bare wing card deck and the stick deck carry the same load sets -- the
    two wing artifacts cannot disagree about the load they export."""
    wing, _, _, _ = _cached(example)
    _skip_if_empty(wing, example, "wing")
    _, _, _, cards_f, cards_m = parse_cards(
        sb.force_moment_cards(wing, sid_base=1, system=system))
    _, _, _, stick_f, stick_m = parse_cards(
        sb.stick_model_bdf(wing, sid_base=1, system=system))
    assert cards_f == stick_f and cards_m == stick_m


# --------------------------------------------------------------------------- #
# Body -- the free-free fuselage beam (Ref 1 Ch 15 p103)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_body_deck_closes_in_force_and_moment(example, system):
    """Body: Σ``FORCE``.Fz = 0 **and** its moment about the aft-most station = 0.

    The fuselage deck is assembled free-free -- fuselage inertia + the balancing
    tail air load + the wing carry-through reaction -- so its equilibrium
    statement is ``Σ = 0``, not ``Σ = n·W``. The moment half is the ``$`` header's
    "Terminal Myy ... (moment equilibrium)" claim, checked here from the deck's
    own ``GRID`` + ``FORCE`` cards for the first time.
    """
    _, body, _, _ = _cached(example)
    _skip_if_empty(body, example, "body")
    res = deck_resultants(sb.body_force_moment_cards(body, sid_base=1, system=system),
                          ref_aftmost_loaded)
    assert sorted(res) == sorted(sb._sid(1, i, r) for i, r in enumerate(body))

    for idx, r in enumerate(body):
        got = res[sb._sid(1, idx, r)]
        where = f"{example} {system.value} body {r.case}"
        assert got.n_force, f"{where}: deck emitted no FORCE cards"
        assert closes(got.fz, 0.0, scale=got.force_scale), f"{where} Fz -> 0"
        assert closes(got.my, 0.0, scale=got.moment_scale), f"{where} My -> 0"


@pytest.mark.parametrize("example", EXAMPLES)
def test_body_grids_match_station_geometry(example):
    """Every body ``FORCE`` GID has a ``GRID`` at that station's ``x``.

    The check above is only as good as the coordinates it integrates; before this
    step these decks named GIDs that had no ``GRID`` card in any file.
    """
    _, body, _, _ = _cached(example)
    _skip_if_empty(body, example, "body")
    u = _units(UnitSystem.SI)
    grids, _, _, forces, _ = parse_cards(
        sb.body_force_moment_cards(body, sid_base=1, system=UnitSystem.SI))
    want = {gid: to_grid(s.x, 0.0, 0.0, u)[0]
            for r in body for gid, s in zip(sb.body_station_gids(r), r.stations)}
    assert set(grids) == set(want)
    for gid, (gx, gy, gz) in grids.items():
        assert math.isclose(gx, want[gid], rel_tol=1e-6, abs_tol=1e-6)
        assert (gy, gz) == (0.0, 0.0)
    loaded = {gid for cards in forces.values() for gid, _, _ in cards}
    assert loaded <= set(grids)


def test_body_moment_check_is_not_vacuous():
    """Perturb one station's ``fz`` by 1% and the moment check must *fail*.

    A zero-target tolerance that scales with the sum's own magnitude is exactly
    the kind that can be tuned into passing everything; this pins that it is not.
    """
    import copy

    _, body, _, _ = _cached("ga6_normal.project.json")
    assert body
    broken = copy.deepcopy(body[:1])
    station = max(broken[0].stations, key=lambda s: abs(s.fz))
    station.fz *= 1.01
    got = deck_resultants(sb.body_force_moment_cards(broken, sid_base=1),
                          ref_aftmost_loaded)[sb._sid(1, 0, broken[0])]
    assert not closes(got.fz, 0.0, scale=got.force_scale)
    assert not closes(got.my, 0.0, scale=got.moment_scale)


# --------------------------------------------------------------------------- #
# Tail -- the chordwise distribution (Ref 1 Ch 10)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_tail_deck_resultants(example, system):
    """Tail: Σ``FORCE``.Fz = SF x (``LT25`` + ``LT50``), and the set's chordwise
    first moment about the leading-edge station matches the in-memory profile.

    The tail has no independent moment oracle -- the chordwise moment *is* the
    profile's own first moment -- so the assertion is that the deck and the CSV
    beside it cannot disagree about it, which is the failure mode the boundary
    owns (a card routed to the wrong GID, a truncated coordinate, a GID block
    shared between two components with different chords).
    """
    _, _, tail, _ = _cached(example)
    _skip_if_empty(tail, example, "tail")
    u = _units(system)
    res = deck_resultants(sb.tail_force_moment_cards(tail, sid_base=1, system=system),
                          ref_first_loaded)
    assert sorted(res) == sorted(sb._sid(1, i, r) for i, r in enumerate(tail))

    for idx, r in enumerate(tail):
        got = res[sb._sid(1, idx, r)]
        where = f"{example} {system.value} tail {r.component} {r.case}"
        _, _, want_fz = to_force(0.0, 0.0, (r.lt25 + r.lt50) * r.safety_factor, u)
        assert closes(got.fz, want_fz, scale=got.force_scale), f"{where} Fz"
        # My = (p - ref) x F with F purely vertical => -Σ f_i (x_i - x_ref).
        # x_ref is the deck's own -- the first *loaded* node, which is not always
        # chord station 0 (a station whose pressure is ~0 emits no card at all).
        # The two moments are then about the same point by construction, which is
        # the only way this comparison means anything.
        stations = sorted(r.stations, key=lambda s: s.x)
        want_my = 0.0
        for s, f in zip(stations, sb._tail_nodal_forces(r)):
            x_deck = to_grid(s.x, 0.0, 0.0, u)[0]
            _, _, f_deck = to_force(0.0, 0.0, f, u)
            want_my -= f_deck * (x_deck - got.ref[0])
        assert closes(got.my, want_my, scale=got.moment_scale), f"{where} My"


@pytest.mark.parametrize("example", EXAMPLES)
def test_tail_components_take_disjoint_grids(example):
    """The h-tail and the v-tail are different beams with different average
    chords, so their chord stations must not share GIDs.

    They did until this step -- harmlessly, while the deck named GIDs that
    existed nowhere. The moment a ``GRID`` card is emitted the collision would
    define one node at two locations, and the moment check would integrate the
    wrong lever arms.
    """
    _, _, tail, _ = _cached(example)
    _skip_if_empty(tail, example, "tail")
    grids, _, _, forces, _ = parse_cards(sb.tail_force_moment_cards(tail, sid_base=1))
    by_component = {}
    for r in tail:
        stations = sorted(r.stations, key=lambda s: s.x)
        gids = {sb.tail_station_gid(r.component, i) for i in range(len(stations))}
        by_component.setdefault(r.component, set()).update(gids)
    components = sorted(by_component)
    assert len(components) >= 1
    for a, b in zip(components, components[1:]):
        assert not (by_component[a] & by_component[b]), \
            f"{example}: {a} and {b} share tail GIDs"
    loaded = {gid for cards in forces.values() for gid, _, _ in cards}
    assert loaded <= set(grids)


# --------------------------------------------------------------------------- #
# Control surfaces -- force only, and no GRID cards (design note §3.1)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_control_deck_force_resultant(example, system):
    """Control surfaces: Σ``FORCE``.Fz = SF x the critical surface load."""
    _, _, _, control = _cached(example)
    _skip_if_empty(control, example, "control-surface")
    u = _units(system)
    text = sb.control_surface_force_moment_cards(control, sid_base=1, system=system)
    _, _, _, forces, moments = parse_cards(text)
    assert not moments, "control-surface decks emit no MOMENT cards"
    for idx, r in enumerate(control):
        sid = sb._sid(1, idx, r)
        got = sum(sc * v[2] for _, sc, v in forces[sid])
        scale = max(abs(sc * v[2]) for _, sc, v in forces[sid])
        _, _, want = to_force(0.0, 0.0, r.load_lb * r.safety_factor, u)
        assert closes(got, want, scale=scale), \
            f"{example} {system.value} control {r.surface} {r.case} Fz"


@pytest.mark.parametrize("example", EXAMPLES)
def test_control_deck_carries_no_geometry(example):
    """Control decks emit no ``GRID`` cards, and say so in-band (§3.1).

    ``ControlSurfaceStation.x`` is a fraction of chord and the result carries no
    chord length, so any coordinate emitted here would be silently wrong -- in a
    millimetre deck, off by three orders of magnitude and dimensionally
    meaningless besides. Revisit if the result ever gains a chord length.
    """
    _, _, _, control = _cached(example)
    _skip_if_empty(control, example, "control-surface")
    text = sb.control_surface_force_moment_cards(control, sid_base=1)
    grids, *_ = parse_cards(text)
    assert not grids
    assert "FRACTIONS OF CHORD" in text


# --------------------------------------------------------------------------- #
# GID-block disjointness (design note §5 step 3)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_gid_blocks_are_disjoint(example):
    """Wing / body-mass / body-reaction / tail / control GIDs never collide.

    Emitting ``GRID`` cards makes collisions real for the first time (the GIDs
    used to be bare references), and an assembled multi-component deck (L-1)
    needs this to hold across the whole airframe, not one family at a time.
    """
    wing, body, tail, control = _cached(example)
    blocks = {}
    if wing:
        blocks["wing"] = {sb._ROOT_GID} | {
            sb.station_gid(i) for i in range(len(wing[0].stations))}
    if body:
        mass, reaction = set(), set()
        for r in body:
            for gid, s in zip(sb.body_station_gids(r), r.stations):
                (reaction if s.source in sb._BODY_REACTION_SOURCES else mass).add(gid)
        blocks["body-mass"] = mass
        blocks["body-reaction"] = reaction
    if tail:
        blocks["tail"] = {sb.tail_station_gid(r.component, i)
                          for r in tail for i in range(len(r.stations))}
    if control:
        blocks["control"] = {sb._CS_GID_BASE + i
                             for r in control for i in range(len(r.stations))}
    names = sorted(blocks)
    assert names, f"{example}: no exportable component at all"
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlap = blocks[a] & blocks[b]
            assert not overlap, f"{example}: {a} and {b} share GIDs {sorted(overlap)}"


@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_deck_comments_fit_the_free_field_card_width(example, system):
    """No ``$`` line in the body / tail / control decks exceeds 72 columns, in
    either unit system.

    Free-field bulk data is 72 columns wide, and the body deck already had a
    one-off assertion of this. It was a one-off: the tail deck's "Applied Fz set
    sums to ... = SF x (LT25 + LT50) = ..." line overran on any five-figure load
    (73 columns on ``ga6_normal``), unnoticed, because nothing swept the other
    deck families. SI makes it worse -- the same number in newtons is wider.

    **Deliberately does not cover the wing decks.** They overrun too (the
    ``$ Axes:`` line, and ``$ FORCE set sums to root Sz ... Myy ...`` at up to
    ~100 columns in SI), which this sweep is what found -- but fixing them
    changes exported **wing** Imperial bytes, and this step's acceptance
    restricts the Imperial diff to the two deck families that gained ``GRID``
    cards. ``$`` is a comment to every bulk-data parser, so the overrun is
    cosmetic, not a parse risk. Filed as its own item in
    ``docs/30_future/00_backlog.md``; widen this sweep to ``wing`` when it lands.
    """
    _, body, tail, control = _cached(example)
    decks = []
    if body:
        decks.append(("body", sb.body_force_moment_cards(body, system=system)))
    if tail:
        decks.append(("tail", sb.tail_force_moment_cards(tail, system=system)))
    if control:
        decks.append(("control",
                      sb.control_surface_force_moment_cards(control, system=system)))
    if not decks:
        pytest.skip(f"{example}: no body / tail / control deck (see "
                    "test_every_example_has_decks)")
    for name, text in decks:
        over = [ln for ln in text.splitlines()
                if ln.startswith("$") and len(ln) > 72]
        assert not over, f"{example} {system.value} {name}: {over}"


def test_body_gid_block_capacity_still_guarded():
    """``body_station_gids`` still refuses to run past its 500-GID block into the
    tail's -- the guard that keeps the disjointness above true by construction
    rather than by fixture size."""
    import copy

    _, body, _, _ = _cached("ga6_normal.project.json")
    assert body
    r = copy.deepcopy(body[0])
    proto = [s for s in r.stations if s.source not in sb._BODY_REACTION_SOURCES][0]
    r.stations = [copy.deepcopy(proto) for _ in range(sb._BODY_GID_BLOCK + 1)]
    with pytest.raises(ValueError, match="exceed"):
        sb.body_station_gids(r)


# --------------------------------------------------------------------------- #
# Sweep coverage -- what each fixture is expected to produce
# --------------------------------------------------------------------------- #
def test_every_example_has_decks():
    """Pin which components each fixture exports, so a skip above is a recorded
    fact about the fixture and not a silently-vanished check.

    Order is ``(wing, body, tail, control)``. The reference aircraft carry no
    ``aileron_loads`` / ``flap_loads`` / ``tab_loads`` input slices, so they have
    no control-surface deck; ``concept_heavy`` additionally carries no
    ``fuselage_mass`` stations and no tail slice. ``ga6_normal``,
    ``cessna_210`` and ``concept_regional_jet`` export all four families.
    """
    coverage = {ex: tuple(bool(c) for c in _cached(ex)) for ex in EXAMPLES}
    assert coverage == {
        "atr42_100.project.json": (True, True, True, False),
        "cessna_210.project.json": (True, True, True, True),
        "concept_heavy.project.json": (True, False, False, False),
        "concept_regional_jet.project.json": (True, True, True, True),
        "dhc8_dash8.project.json": (True, True, True, False),
        "ga6_normal.project.json": (True, True, True, True),
    }


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
