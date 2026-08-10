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
from sloads.export.coordinates import (  # noqa: E402
    bending_moment_vector,
    to_force,
    to_grid,
    to_moment,
)
from sloads.export.equilibrium import (  # noqa: E402
    closes,
    resultant,
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
from sloads.modules.tail_span import build_tail_span  # noqa: E402
from sloads.modules.tail_span import axial_total as ts_axial  # noqa: E402
from sloads.modules.tail_span import inertia_total as ts_inertia  # noqa: E402
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
    spans = _try(build_tail_span, p) or {}
    return wing, body, tail, control, spans.get("htail", []), spans.get("vtail", [])


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
    wing, _, _, _, _, _ = _cached(example)
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
    """The deck's moment about the root station = SF x root ``Mxx`` and ``Mzz``.

    Both bending channels, every fixture, no exception -- including the three
    that hang concentrated masses on the wing (``atr42_100``, ``dhc8_dash8``,
    ``concept_heavy``), which this assertion used to *exclude*.

    A concentrated mass does not sit on a station, so recovering nodal loads by
    differencing the cumulative shear picked it up whole at the node inboard of
    it and moved its lever arm inboard by up to one strip width: root bending
    read 1.91 / 1.11 / 0.44 % high in ``Mxx`` and 1.14 / 0.67 / 0.32 % high in
    ``Mzz``. The export now emits the mass's **offset couple** on that node's
    ``MOMENT`` card -- the exact static equivalent of its force at its true
    station -- so the set closes here and, more strongly, at every node
    (:func:`test_wing_deck_reproduces_the_station_table_at_every_node`).

    ``Resultant.mx``/``.mz`` already carry the applied ``MOMENT`` set plus the
    ``FORCE`` lever arms, which is exactly the sum a solver forms. ``Mzz`` maps
    to ``-z`` and ``Mxx`` to ``+x``; that asymmetry is
    ``coordinates.bending_moment_vector``'s, not restated here.

    Design note: ``docs/30_future/14_concentrated_wing_mass_nodal_split_plan.md``.
    """
    wing, _, _, _, _, _ = _cached(example)
    _skip_if_empty(wing, example, "wing")
    u = _units(system)
    res = deck_resultants(sb.stick_model_bdf(wing, sid_base=1, system=system),
                          ref_first_loaded)
    for idx, r in enumerate(wing):
        got = res[sb._sid(1, idx, r)]
        root, sf = r.stations[0], r.safety_factor
        want_mx, _, want_mz = bending_moment_vector(root.mxx * sf, root.mzz * sf, u)
        where = f"{example} {system.value} wing {r.case}"
        assert closes(got.mx, want_mx, scale=got.moment_scale), f"{where} Mxx"
        assert closes(got.mz, want_mz, scale=got.moment_scale), f"{where} Mzz"


@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_wing_deck_reproduces_the_station_table_at_every_node(example, system):
    """Shear **and** bending match the NETLOADS table at *every* station, not
    just the root -- the property the offset couples buy.

    A force split between the bracketing nodes (the fix as originally filed)
    would also close at the root, but only by moving load outboard, which
    corrupts the shear at that node by 22 % on ``atr42_100``. This test is what
    separates the two: it re-derives, from the deck's own text, the shear and
    bending carried by everything outboard of each station and compares with
    that station's published cumulative values. Design note 14 D-1.
    """
    wing, _, _, _, _, _ = _cached(example)
    _skip_if_empty(wing, example, "wing")
    u = _units(system)
    text = sb.stick_model_bdf(wing, sid_base=1, system=system)
    grids, _, _, forces, moments = parse_cards(text)
    for idx, r in enumerate(wing):
        sid = sb._sid(1, idx, r)
        sf = r.safety_factor
        gids = [sb.station_gid(i) for i in range(len(r.stations))]
        for k, st in enumerate(r.stations):
            keep = set(gids[k:])          # this station and everything outboard
            ref = grids[gids[k]]
            sub_f = {sid: [c for c in forces.get(sid, ()) if c[0] in keep]}
            sub_m = {sid: [c for c in moments.get(sid, ()) if c[0] in keep]}
            got = resultant(sub_f, sub_m, grids, sid, ref)
            _, _, want_fz = to_force(0.0, 0.0, st.sz * sf, u)
            want_mx, _, want_mz = bending_moment_vector(st.mxx * sf, st.mzz * sf, u)
            where = f"{example} {system.value} wing {r.case} station {k}"
            assert closes(got.fz, want_fz, scale=got.force_scale), f"{where} Sz"
            assert closes(got.mx, want_mx, scale=got.moment_scale), f"{where} Mxx"
            assert closes(got.mz, want_mz, scale=got.moment_scale), f"{where} Mzz"


@pytest.mark.parametrize("example", EXAMPLES)
def test_offset_couples_exist_only_where_a_concentrated_mass_does(example):
    """The couples are non-zero at exactly the nodes bracketing a concentrated
    mass, and identically zero on a wing that carries none.

    This is the drift guard behind the claim that the fix is a **no-op** on the
    Appendix A fixture: ``ga6_normal``, ``cessna_210`` and
    ``concept_regional_jet`` must export not merely small couples but zero ones,
    so their decks are byte-identical to what they were before the couples
    existed. It also pins the converse -- if a fixture ever gains a wing point
    mass, its couples appear and this test says so.
    """
    wing, _, _, _, _, _ = _cached(example)
    _skip_if_empty(wing, example, "wing")
    expected = _has_concentrated_wing_mass(example)
    for r in wing:
        loads = sb.wing_nodal_loads(r)
        nodes = [i for i, nl in enumerate(loads)
                 if abs(nl.mx) > 1e-6 or abs(nl.mz) > 1e-6]
        where = f"{example} wing {r.case}"
        if expected:
            assert nodes, f"{where}: concentrated mass but no offset couple"
            # One bracketing node per fixture -- all masses on the twins fall in
            # the same strip; a second node would mean the station set moved.
            assert len(nodes) == 1, f"{where}: couples at {nodes}, expected one"
        else:
            assert not nodes, (
                f"{where}: offset couples at {nodes} on a wing with no "
                "concentrated mass -- the correction is not a no-op here")


@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_wing_card_deck_force_matches_stick_deck(example, system):
    """The bare wing card deck and the stick deck carry the same load sets -- the
    two wing artifacts cannot disagree about the load they export."""
    wing, _, _, _, _, _ = _cached(example)
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
    _, body, _, _, _, _ = _cached(example)
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
    _, body, _, _, _, _ = _cached(example)
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

    _, body, _, _, _, _ = _cached("ga6_normal.project.json")
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
    _, _, tail, _, _, _ = _cached(example)
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
    _, _, tail, _, _, _ = _cached(example)
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
    _, _, _, control, _, _ = _cached(example)
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
    _, _, _, control, _, _ = _cached(example)
    _skip_if_empty(control, example, "control-surface")
    text = sb.control_surface_force_moment_cards(control, sid_base=1)
    grids, *_ = parse_cards(text)
    assert not grids
    assert "FRACTIONS OF CHORD" in text


# --------------------------------------------------------------------------- #
# Spanwise empennage decks (plan 09 T4) -- the two new rows of the §4 table
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_htail_span_deck_resultants(example, system):
    """H-tail: Σ``FORCE``.Fz = SF x (air + inertia), and Σ about the centreline is
    the case's rolling input -- **zero for every symmetric condition**.

    The rolling row is the one the full-span topology (T-8) buys: a per-side deck
    could not state it, and a mirrored-wrong half or a mis-signed side scale is
    invisible to a force sum but lands here immediately.
    """
    _, _, _, _, htail_span, _ = _cached(example)
    _skip_if_empty(htail_span, example, "h-tail spanwise")
    u = _units(system)
    text = sb.tail_span_force_moment_cards(htail_span, component="htail",
                                           sid_base=1, system=system)
    grids, _, _, forces, moments = parse_cards(text)
    assert sorted(forces) == sorted(sb._sid(1, i, r) for i, r in enumerate(htail_span))

    for idx, r in enumerate(htail_span):
        sid = sb._sid(1, idx, r)
        where = f"{example} {system.value} htail-span {r.case}"
        got = resultant(forces, moments, grids, sid, (0.0, 0.0, 0.0))
        _, _, want = to_force(0.0, 0.0, (r.air_total + ts_inertia(r)) * r.safety_factor, u)
        assert closes(got.fz, want, scale=got.force_scale), f"{where} Fz"
        assert closes(got.fy, 0.0, scale=got.force_scale), f"{where} Fy"

        # Rolling moment about the centreline: Σ Fz·y, which the resultant's mx
        # carries because the reference is the centreline itself.
        roll = sum(sc * v[2] * grids[gid][1] for gid, sc, v in forces[sid])
        if r.rh_scale == r.lh_scale:
            assert closes(roll, 0.0, scale=got.moment_scale), f"{where} roll -> 0"
        else:
            assert not closes(roll, 0.0, scale=got.moment_scale), \
                f"{where}: 23.427(a) must roll the centreline"


@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", _SYSTEMS)
def test_vtail_span_deck_resultants(example, system):
    """V-tail: the fin's load is a **side** force, and its torsion is ``Mzz``.

    The axis map is the whole content of this row. Emitting the fin's normal force
    as ``Fz`` -- the obvious copy-paste from the h-tail writer -- gives a deck
    that parses, solves, and loads the fin in the one direction it is not designed
    for; a force-only sum in the wrong component would still "close".

    Since the tail-mass SSOT step the fin carries inertia on **both** of its axes,
    and this row is where the two are kept apart: the lateral term ``-n_y*W_vt``
    belongs in ``Fy`` with the air load, and the axial term ``-n_z*W_vt`` -- which
    exists only because the fin spans in Z -- belongs in ``Fz``, alone. A deck
    that put the axial term in ``Fy`` would close in *total* force and load the
    fin sideways with its own weight.
    """
    _, _, _, _, _, vtail_span = _cached(example)
    _skip_if_empty(vtail_span, example, "v-tail spanwise")
    u = _units(system)
    text = sb.tail_span_force_moment_cards(vtail_span, component="vtail",
                                           sid_base=1, system=system)
    grids, _, _, forces, moments = parse_cards(text)

    for idx, r in enumerate(vtail_span):
        sid = sb._sid(1, idx, r)
        where = f"{example} {system.value} vtail-span {r.case}"
        got = resultant(forces, moments, grids, sid, (0.0, 0.0, 0.0))
        _, _, want = to_force(
            0.0, 0.0, (r.air_total + ts_inertia(r)) * r.safety_factor, u)
        assert closes(got.fy, want, scale=got.force_scale), f"{where} Fy"
        _, _, want_axial = to_force(
            0.0, 0.0, ts_axial(r) * r.safety_factor, u)
        assert closes(got.fz, want_axial, scale=got.force_scale), f"{where} Fz axial"
        # Torsion is about the fin's span axis, z -- not y.
        assert closes(got.m0y, 0.0, scale=got.moment_scale), f"{where} Myy (must be 0)"
        assert all(g[1] == 0.0 for g in grids.values()), f"{where}: fin is on the CL"


@pytest.mark.parametrize("example", EXAMPLES)
def test_spanwise_tail_decks_declare_the_double_count_rule(example):
    """The deck says, in band, that it supersedes the fuselage deck's point tail
    load -- the T-11 rule, written where a consumer will read it."""
    _, _, _, _, htail_span, vtail_span = _cached(example)
    _skip_if_empty(htail_span, example, "h-tail spanwise")
    for component, results in (("htail", htail_span), ("vtail", vtail_span)):
        text = sb.tail_span_force_moment_cards(results, component=component)
        assert "SUPERSEDES the point tail-load station" in text
        over = [ln for ln in text.splitlines() if ln.startswith("$") and len(ln) > 72]
        assert not over, f"{example} {component}: {over}"


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
    wing, body, tail, control, htail_span, vtail_span = _cached(example)
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
    for name, results in (("htail-span", htail_span), ("vtail-span", vtail_span)):
        if results:
            component = name.split("-")[0]
            blocks[name] = {sb.tail_span_gid(component, i)
                            for r in results for i in range(len(r.stations))}
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
    _, body, tail, control, _, _ = _cached(example)
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

    _, body, _, _, _, _ = _cached("ga6_normal.project.json")
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

    Order is ``(wing, body, tail, control, htail_span, vtail_span)``. The reference aircraft carry no
    ``aileron_loads`` / ``flap_loads`` / ``tab_loads`` input slices, so they have
    no control-surface deck; ``concept_heavy`` additionally has no tail slice.
    ``ga6_normal``, ``cessna_210`` and ``concept_regional_jet`` export all four
    families.

    ``concept_heavy`` **gained a body deck at step B1**: it carries no
    ``fuselage_mass.stations`` at all, and was the one fixture with no fuselage
    loads for that reason. The beam is now derived from ``weight.items`` (the
    mass SSOT), so a project needs no hand-entered station table to have a
    fuselage.
    """
    coverage = {ex: tuple(bool(c) for c in _cached(ex)) for ex in EXAMPLES}
    assert coverage == {
        "atr42_100.project.json": (True, True, True, False, True, True),
        "cessna_210.project.json": (True, True, True, True, True, True),
        "concept_heavy.project.json": (True, True, False, False, False, False),
        "concept_regional_jet.project.json": (True, True, True, True, True, True),
        "dhc8_dash8.project.json": (True, True, True, False, True, True),
        "ga6_normal.project.json": (True, True, True, True, True, True),
    }


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
