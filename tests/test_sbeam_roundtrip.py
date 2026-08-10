"""The round-trip gate: exported decks solved in the **real** sbeam.

Design note: ``docs/30_future/10_sbeam_roundtrip_ci_harness_plan.md``
(decisions S-1...S-9, assertions §4). Machinery:
:mod:`sloads.export.roundtrip`. Sibling gate, card-text only:
``tests/test_export_equilibrium.py``.

The mission's core claim is that *an exported deck solves in sbeam with verified
global equilibrium, continuously in CI*. Until this module that rested on a
manual check performed once, in 2026, and never repeated. What is new here is
not the physics -- the 2026-08-08 spike found the round trip already agreed
exactly -- but that it is now a standing gate: the day a card format, a GID
scheme, a unit factor or a case-control block drifts, this goes red.

Why a solver, when the card sum already closes
----------------------------------------------
``test_export_equilibrium`` re-derives each deck's resultant from its own card
text. That catches suppression, truncation, SID misrouting and an inconsistent
unit set. It cannot catch what only another program's reader can: a card sbeam
rejects, a ``LOAD`` id no ``SUBCASE`` selects, a GID that resolves to nothing, a
frame or sign convention that differs from the one the deck assumes. And it is
blind to whether the deck is *solvable* at all.

The strongest assertions here are the ones with two independent producers:

* **W-c / W-d** compare a solver-recovered internal load against the **NETLOADS
  quadrature** (``r.stations[...]``). The deck's cards come from
  ``wing_nodal_loads``, the target from the cumulative table -- different code.
* **B-c** does the same along the fuselage beam, station by station: sbeam
  reassembles the Ch 15 cumulative shear and bending from the ``FORCE`` cards
  and the ``GRID`` coordinates alone, and it must reproduce ``body_loads``'
  table. (The design note asked only for "aft-most element shear ~ 0" here; that
  turned out to be neither true nor meaningful -- the last element carries the
  last station's load -- while the whole-beam comparison is both, so it is what
  is asserted. See :func:`test_body_deck_recovers_the_cumulative_beam`.)
* **B-b** and the assembled leg target the constant **zero**, which no
  producer can bias.

Scope (S-2/S-3/S-4): ``ga6_normal`` + ``concept_regional_jet``, Imperial + SI,
across the wing stick deck, test-only body/tail wrappers, and the assembled
full-span deck. Control-surface decks are permanently out -- their chordwise
``x`` is a fraction of chord with no chord length on the result, so there is no
geometry to solve (S-3).

Tolerances are :mod:`sloads.export.equilibrium`'s, not this file's, so the two
export gates can never disagree about what "equal" means.
"""

import os
import re
import subprocess
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.export.balanced_deck import (  # noqa: E402
    BALANCED_SID_BASE,
    balanced_deck,
)
from sloads.export.coordinates import to_force, to_grid, to_moment  # noqa: E402
from sloads.export.equilibrium import (  # noqa: E402
    closes,
    parse_cards,
    ref_first_loaded,
    resultant,
)
from sloads.export.roundtrip import (  # noqa: E402
    Support,
    Topology,
    solve_deck,
    total_reaction,
    wrap_as_stick_model,
)
from sloads.modules.balance import (  # noqa: E402
    build_balanced_cases,
    fin_load,
    is_lateral,
)
from sloads.modules.body_loads import build_body_loads  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402
from sloads.modules.tail_span import build_tail_span  # noqa: E402
from sloads.modules.taildist import build_tail_chordwise  # noqa: E402
from sloads.units import Channel, UnitSystem, deliverable_units  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Decision S-4. ``ga6_normal`` is the FAR23 Appendix-A oracle fixture;
#: ``concept_regional_jet`` is the flagship concept fixture and the mission's own
#: subject. ``concept_heavy`` is excluded until its export defect is closed (see
#: the backlog's "cannot be exported to sbeam"); the twins add solve time without
#: adding a deck family.
MATRIX = ("ga6_normal.project.json", "concept_regional_jet.project.json")

#: The wing leg adds ``atr42_100`` -- the only fixture in the harness whose wing
#: hangs **concentrated** masses (engines, nacelles, wing fuel), and therefore
#: the only one whose deck carries the offset-couple ``MOMENT`` cards that
#: restore their lever arms. Both MATRIX fixtures are mass-free, so before this
#: the solver leg could not tell whether sbeam *honours* an ``Mx`` component or
#: silently drops it -- and W-d, which compares element 1's end-B bending with
#: the NETLOADS root ``Mxx``, is exactly the assertion that would catch it (it
#: read 1.91 % high here until the couples existed). Wing-only: this fixture
#: assembles no balanced case, so it has no business in the other legs.
WING_MATRIX = MATRIX + ("atr42_100.project.json",)

#: Varying the unit system is what makes a *solve* catch a
#: ``moment.factor != force.factor x length.factor`` slip (plan 07's G2), which a
#: force-only check is structurally blind to.
SYSTEMS = (UnitSystem.IMPERIAL, UnitSystem.SI)

_CACHE = {}


def _project(example: str):
    p = io.load_project(os.path.join(_ROOT, "examples", example))
    if p.envelope is None:
        p.envelope = build_envelope(p)
    if p.envelope.critical is None:
        p.envelope.critical = build_critical(p)
    return p


def _components(example: str):
    if example not in _CACHE:
        p = _project(example)
        net = build_net_loads(p)
        _CACHE[example] = (
            p,
            loads_ref_axis_results(p, net.wing_net),
            build_body_loads(p),
            build_tail_chordwise(p),
        )
    return _CACHE[example]


def _units(system):
    return deliverable_units(system, Channel.SOLVER)


def _tail_groups(tail):
    """The tail deck's two disjoint beams, by component.

    The h-tail and v-tail chord lines both start at ``x = 0`` on ``y = z = 0``
    (each stated from its own leading edge), so their stations are coincident in
    space and a single element run through them is degenerate.
    """
    groups = {}
    for r in tail:
        groups.setdefault(r.component, set()).update(
            sb.tail_station_gid(r.component, i) for i in range(len(r.stations)))
    return [sorted(g) for g in groups.values()]


def _span_groups(results, component):
    """The one beam a spanwise tail deck contains, as the wrapper's node group.

    One group, not two: unlike the *chordwise* deck — where the h-tail and v-tail
    are separate beams with coincident stations — a spanwise deck carries a single
    surface, and for the h-tail that surface is one full-span member through the
    centreline (decision T-8).
    """
    return [[sb.tail_span_gid(component, i)
             for i in range(len(results[0].stations))]]


def _solved(text):
    """``(solutions, grids)`` for a deck -- solve it and keep its geometry."""
    return solve_deck(text), parse_cards(text)[0]


# --------------------------------------------------------------------------- #
# Wing -- the deck that is solvable exactly as exported
# --------------------------------------------------------------------------- #
@pytest.mark.roundtrip
@pytest.mark.parametrize("example", WING_MATRIX)
@pytest.mark.parametrize("system", SYSTEMS)
def test_wing_stick_deck_solves_and_recovers_the_root_loads(sbeam, example, system):
    """W-a...W-d: the wing stick model solves, and sbeam recovers the NETLOADS root.

    W-a/W-b (reaction == -applied resultant) are the cheap global closure and
    will essentially never fail alone. W-c/W-d are the substance: the recovered
    reaction and the element-1 end-B internal loads are compared against
    ``r.stations[0]`` -- the NETLOADS quadrature, computed by different code than
    the cards.

    **Never a root-node moment comparison** (S-6). The clamped root node sits half
    a strip inboard of station 0 and, on a swept wing, offset in ``x``, so the
    reaction moment is not station-0 ``Mxx``/``Myy``: on ``ga6_normal`` PHAA it is
    -1.847E5 against a -91,410 lb-in root torsion. Element 1 is the exception the
    identities rest on -- ``_root_node`` copies station 0's ``x`` and ``z``, so
    that element lies exactly along ``y`` and its local frame maps cleanly onto
    the airplane axes.
    """
    _, wing, _, _ = _components(example)
    u = _units(system)
    text = sb.stick_model_bdf(wing, sid_base=1, system=system)
    sols, grids = _solved(text)
    _, _, _, forces, moments = parse_cards(text)
    root = grids[sb._ROOT_GID]

    assert sorted(sols) == sorted(sb._sid(1, i, r) for i, r in enumerate(wing))

    for idx, r in enumerate(wing):
        sid = sb._sid(1, idx, r)
        sol, st, sf = sols[sid], r.stations[0], r.safety_factor
        where = f"{example} {system.value} wing {r.case}"
        applied = resultant(forces, moments, grids, sid, root)
        reaction = sol.reactions[sb._ROOT_GID]

        # W-a / W-b: the solver's reaction is the applied resultant, negated,
        # about the node the deck itself constrains.
        for axis, want in enumerate((applied.fx, applied.fy, applied.fz)):
            assert closes(reaction[axis], -want, scale=applied.force_scale), \
                f"{where} W-a axis {axis}"
        for axis, want in enumerate((applied.mx, applied.my, applied.mz)):
            assert closes(reaction[3 + axis], -want, scale=applied.moment_scale), \
                f"{where} W-b axis {axis}"

        # W-c: the vertical reaction is the NETLOADS root shear.
        want_fx, _, want_fz = to_force(st.sx * sf, 0.0, st.sz * sf, u)
        assert closes(reaction[2], -want_fz, scale=abs(want_fz)), f"{where} W-c Sz"
        assert closes(reaction[0], -want_fx, scale=abs(want_fx)), f"{where} W-c Sx"

        # W-d: element 1's end-B internal loads are the root station's cumulative
        # shear, bending and lateral bending. Element 1 runs exactly along +y, so
        # its local frame is a fixed permutation of the airplane axes: local y is
        # airplane z (shear1 == Sz) and local "bending 2" is airplane Mxx.
        bar = sol.bar_forces[1]
        want_mxx, _, _ = to_moment(st.mxx * sf, 0.0, 0.0, u)
        _, _, want_mzz = to_moment(0.0, 0.0, st.mzz * sf, u)
        assert closes(bar.shear1, want_fz, scale=abs(want_fz)), f"{where} W-d shear"
        assert closes(bar.bm2_b, want_mxx, scale=abs(want_mxx)), f"{where} W-d Mxx"
        assert closes(bar.bm1_b, -want_mzz, scale=abs(want_mzz)), f"{where} W-d Mzz"


# --------------------------------------------------------------------------- #
# Body -- free-free, on a determinate support (S-3.1)
# --------------------------------------------------------------------------- #
def _body_deck(body, system):
    return wrap_as_stick_model(
        sb.body_force_moment_cards(body, sid_base=1, system=system),
        support=Support.DETERMINATE, system=system, title="fuselage beam")


@pytest.mark.roundtrip
@pytest.mark.parametrize("example", MATRIX)
@pytest.mark.parametrize("system", SYSTEMS)
def test_body_deck_solves_free_free(sbeam, example, system):
    """B-a / B-b: the fuselage deck solves, and its determinate support reacts zero.

    B-a is most of the value on its own -- it proves the ``GRID`` cards plan 07
    added are real, consistent and sufficient to stand a model up.

    B-b is the free-free claim proved **through the solver**: the support carries
    exactly the residual the applied set fails to balance, and the lever arms are
    the ones sbeam computes from the deck's own coordinates, not the ones sloads
    used. A deck that closes on paper but reacts non-zero here has a geometry
    error the card sum cannot see -- which is what the third negative test below
    demonstrates.
    """
    _, _, body, _ = _components(example)
    text = _body_deck(body, system)
    sols, grids = _solved(text)
    _, _, _, forces, moments = parse_cards(text)

    for idx, r in enumerate(body):
        sid = sb._sid(1, idx, r)
        where = f"{example} {system.value} body {r.case}"
        applied = resultant(forces, moments, grids, sid, (0.0, 0.0, 0.0))
        got = total_reaction(sols[sid].reactions, grids)
        for axis in range(3):
            assert closes(got.force[axis], 0.0, scale=applied.force_scale), \
                f"{where} B-b force axis {axis}: {got.force[axis]}"
            assert closes(got.moment[axis], 0.0, scale=applied.moment_scale), \
                f"{where} B-b moment axis {axis}: {got.moment[axis]}"


@pytest.mark.roundtrip
@pytest.mark.parametrize("example", MATRIX)
@pytest.mark.parametrize("system", SYSTEMS)
def test_body_deck_recovers_the_cumulative_beam(sbeam, example, system):
    """B-c: sbeam reassembles the Ch 15 cumulative shear and bending, station by station.

    The design note's B-c ("recovered CBAR shear at the aft-most element ~ 0")
    does not hold and would not mean much if it did: the last element carries the
    last station's load, and the quantity that vanishes at a free end is the
    *bending*, trivially. The real statement available here is far stronger and is
    the body's analog of W-c/W-d -- sbeam is handed the per-station ``FORCE``
    cards and the ``GRID`` coordinates, and from those alone it must reproduce
    ``body_loads``' entire cumulative table, whose terminal value being zero is
    the deck header's "moment equilibrium" claim.

    Local frame: each element runs along +x, so its ``bm2`` is the airplane
    ``Myy`` and its ``shear1`` is minus the cumulative ``Sz``.

    Indexed by **station position**, not by GID: a fuselage may carry two loads
    at one station (``concept_regional_jet`` puts the tail air load at exactly a
    mass lump's station), which is one node of the beam and therefore one cut.
    The cumulative shear at that cut is the table's *last* entry there.
    """
    _, _, body, _ = _components(example)
    u = _units(system)
    text = _body_deck(body, system)
    sols, grids = _solved(text)
    positions = sorted({grids[g][0] for g in grids})

    def _deck_x(x):
        """The station coordinate **as the deck wrote it** -- six significant
        figures. Re-deriving it in Python instead would miss by a rounding step
        in SI, where the millimetre value has more digits than the card keeps."""
        return float(f"{to_grid(x, 0.0, 0.0, u)[0]:.6E}")

    for idx, r in enumerate(body):
        sid = sb._sid(1, idx, r)
        sol, sf = sols[sid], r.safety_factor
        where = f"{example} {system.value} body {r.case}"
        # Table order, so a coincident pair leaves the outboard-most cumulative
        # value -- the one the cut just outboard of that station carries.
        sz = {_deck_x(s.x): s.sz * sf for s in r.stations}
        myy = {_deck_x(s.x): s.myy * sf for s in r.stations}
        scale = max(abs(to_force(0.0, 0.0, s.sz * sf, u)[2]) for s in r.stations)
        m_scale = max(abs(to_moment(0.0, s.myy * sf, 0.0, u)[1]) for s in r.stations)
        assert len(sol.bar_forces) == len(positions) - 1

        for eid, bar in sorted(sol.bar_forces.items()):
            x_a, x_b = positions[eid - 1], positions[eid]
            _, _, want_sz = to_force(0.0, 0.0, sz[x_a], u)
            _, want_myy, _ = to_moment(0.0, myy[x_b], 0.0, u)
            assert closes(bar.shear1, -want_sz, scale=scale), \
                f"{where} B-c shear, element {eid} (station {x_a})"
            assert closes(bar.bm2_b, want_myy, scale=m_scale), \
                f"{where} B-c bending, element {eid} (station {x_b})"


# --------------------------------------------------------------------------- #
# Tail -- clamped at the leading-edge chord station
# --------------------------------------------------------------------------- #
def _tail_deck(tail, system):
    return wrap_as_stick_model(
        sb.tail_force_moment_cards(tail, sid_base=1, system=system),
        support=Support.CLAMPED_FIRST, system=system,
        groups=_tail_groups(tail), title="tail chord beams")


@pytest.mark.roundtrip
@pytest.mark.parametrize("example", MATRIX)
@pytest.mark.parametrize("system", SYSTEMS)
def test_tail_deck_solves_and_recovers_the_total_load(sbeam, example, system):
    """T-a...T-c: the tail deck solves; its reaction is ``LT25 + LT50`` and the
    chordwise first moment about the leading-edge station.

    Both tail beams are clamped, so the reaction of a case that loads only one
    component is that component's alone -- the other contributes zero, which is
    itself a check that no card leaked across the two GID blocks.
    """
    _, _, _, tail = _components(example)
    u = _units(system)
    text = _tail_deck(tail, system)
    sols, grids = _solved(text)
    _, _, _, forces, moments = parse_cards(text)

    for idx, r in enumerate(tail):
        sid = sb._sid(1, idx, r)
        where = f"{example} {system.value} tail {r.component} {r.case}"
        ref = ref_first_loaded(sid, grids, forces.get(sid, []))
        applied = resultant(forces, moments, grids, sid, ref)
        got = total_reaction(sols[sid].reactions, grids, ref=ref)

        _, _, want_fz = to_force(0.0, 0.0, (r.lt25 + r.lt50) * r.safety_factor, u)
        assert closes(got.force[2], -want_fz, scale=abs(want_fz)), f"{where} T-b"
        # T-c: the reaction moment about the LE station is the deck's own
        # chordwise first moment -- recovered by the solver from the GRID
        # coordinates rather than read back out of the card text.
        assert closes(got.moment[1], -applied.my, scale=applied.moment_scale), \
            f"{where} T-c"


# --------------------------------------------------------------------------- #
# Spanwise empennage decks (plan 09 T4)
# --------------------------------------------------------------------------- #
@pytest.mark.roundtrip
@pytest.mark.parametrize("example", MATRIX)
@pytest.mark.parametrize("system", SYSTEMS)
@pytest.mark.parametrize("component", ("htail", "vtail"))
def test_tail_span_deck_solves(sbeam, example, system, component):
    """The spanwise tail decks solve, and their supports react the applied set.

    The h-tail is the first **full-span** beam in the suite to reach a solver, and
    the v-tail the first deck whose load is a side force. Both are wrapped with a
    determinate support and checked the way the body deck is: the reaction is the
    negative of the applied resultant, computed by sbeam from the deck's own
    ``GRID`` coordinates.
    """
    _, _, _, _ = _components(example)
    project, _, _, _ = _components(example)
    spans = build_tail_span(project)
    results = spans[component]
    assert results, f"{example}: no {component} spanwise result"

    text = wrap_as_stick_model(
        sb.tail_span_force_moment_cards(results, component=component,
                                        sid_base=1, system=system),
        support=Support.DETERMINATE, system=system,
        groups=_span_groups(results, component),
        title=f"{component} spanwise beam")
    sols, grids = _solved(text)
    _, _, _, forces, moments = parse_cards(text)

    for idx, r in enumerate(results):
        sid = sb._sid(1, idx, r)
        where = f"{example} {system.value} {component}-span {r.case}"
        applied = resultant(forces, moments, grids, sid, (0.0, 0.0, 0.0))
        got = total_reaction(sols[sid].reactions, grids)
        for axis, want in enumerate((applied.fx, applied.fy, applied.fz)):
            assert closes(got.force[axis], -want, scale=applied.force_scale), \
                f"{where} reaction axis {axis}"


# --------------------------------------------------------------------------- #
# The assembled full-span deck -- the primary deliverable (plan 11 B-5)
# --------------------------------------------------------------------------- #
def _assembled_deck(project, system):
    """The shipped assembled deck plus the elements it does not carry.

    The deliverable is a load set on a node cloud, which is all a load deck needs
    to be; the wrapper adds a tree of bars so a linear static solve has a
    stiffness matrix, and changes nothing else -- the deck's own determinate
    six-DOF support is kept, because that support *is* what is under test.
    """
    return _assembled_deck_from(project, system, ())


def _assembled_deck_from(project, system, cases):
    """:func:`_assembled_deck` for a stated case list -- ``()`` means "all of
    them", which is what the shipped deck writes."""
    return wrap_as_stick_model(
        balanced_deck(project, system=system, cases=cases),
        support=Support.DECK, topology=Topology.STAR, system=system,
        title="assembled full-span balanced deck")


@pytest.mark.roundtrip
@pytest.mark.parametrize("example", MATRIX)
@pytest.mark.parametrize("system", SYSTEMS)
def test_assembled_deck_reacts_to_zero(sbeam, example, system):
    """The mission's primary deliverable, solved: reactions ~ 0 on every case.

    The assembled deck's ``$`` header claims its determinate support is doing
    nothing -- that aero and inertia balance the airplane wing tip to wing tip
    with no constraint needed. This is that claim checked by a solver which
    reassembles the whole load set from the card text and the ``GRID``
    coordinates: six recovered reaction components, all zero.

    **Plan 13 G3**, from B8a-3 on: the lateral subcases are the first to put a
    real ``fy``/``mx``/``mz`` through this leg, and they are where a sign or
    frame error in the fin's span-to-waterline map would show up as a reaction
    the paper closure cannot see. Two things guard against passing on that
    vacuously -- every assembled case must appear as a subcase, and each lateral
    one must actually carry side load into the solver. That the gate has teeth
    on those DOF is shown separately, by
    :func:`test_a_flipped_fin_load_breaks_the_assembled_solve`.
    """
    project, _, _, _ = _components(example)
    cases = build_balanced_cases(project)
    text = _assembled_deck(project, system)
    sols, grids = _solved(text)
    _, _, spc1, forces, moments = parse_cards(text)
    assert sols, "the assembled deck produced no subcases"
    (_, comp, support_gids), = [s for s in spc1 if s[1] == "123456"][:1] or [(0, "", [])]
    assert comp == "123456" and len(support_gids) == 1, \
        "the assembled deck's support is meant to be one determinate node"

    # Every case reaches the solver, and the lateral family is among them --
    # a deck that quietly stopped emitting them would otherwise pass here.
    by_sid = {BALANCED_SID_BASE + i: c for i, c in enumerate(cases)}
    assert set(sols) == set(by_sid), (
        f"{example}: solved {sorted(sols)} against {sorted(by_sid)}")
    assert sum(1 for c in cases if is_lateral(c)) == 8, \
        f"{example}: {sum(1 for c in cases if is_lateral(c))} lateral subcases"

    for sid, sol in sols.items():
        case = by_sid[sid]
        where = f"{example} {system.value} assembled SID {sid} {case.label}"
        applied = resultant(forces, moments, grids, sid, grids[support_gids[0]])
        got = total_reaction(sol.reactions, grids, ref=grids[support_gids[0]])
        assert applied.n_force, f"{where}: no FORCE cards in this subcase"
        if is_lateral(case):
            # The cards sum to zero by construction; what must not be zero is
            # the side load flowing through them, or "reaction ~ 0" would be the
            # trivial statement that nothing lateral was applied at all.
            side = sum(abs(scale * n[1]) for _, scale, n in forces[sid])
            floor = 0.1 * abs(fin_load(case)) * case.safety_factor
            _, floor, _ = to_force(0.0, floor, 0.0, _units(system))
            assert side > abs(floor), (
                f"{where}: only {side} of side load reached the solver")
        for axis in range(3):
            assert closes(got.force[axis], 0.0, scale=applied.force_scale), \
                f"{where} force axis {axis}: {got.force[axis]}"
            assert closes(got.moment[axis], 0.0, scale=applied.moment_scale), \
                f"{where} moment axis {axis}: {got.moment[axis]}"


@pytest.mark.roundtrip
@pytest.mark.parametrize("system", SYSTEMS)
def test_a_flipped_fin_load_breaks_the_assembled_solve(sbeam, system):
    """**G3's teeth**: reverse the fin load alone and the solver reacts it.

    A zero-target gate is only worth what its sensitivity is, and "the reactions
    came out zero" proves nothing unless a wrong deck would have made them
    non-zero. The mutation is the exact defect plan 13 §3.3 found in the fin's
    waterline and the one L-6's frame map could reintroduce: the fin's side load
    with its sign reversed, everything else -- including the closure field that
    balanced the *original* load -- left untouched. The airplane is then carrying
    twice the fin load with nothing to react it, and the support must say so.

    Run on ``ga6_normal`` only: the mutation is a property of the assembly, not
    of a fixture, and a second airplane would only add solve time.
    """
    project, _, _, _ = _components("ga6_normal.project.json")
    cases = build_balanced_cases(project)
    case = next(c for c in cases if is_lateral(c) and c.hand == "R")
    flipped = replace(case, loads=[
        replace(ld, fy=-ld.fy, mz=-ld.mz) if ld.source == "vtail-air" else ld
        for ld in case.loads])

    text = _assembled_deck_from(project, system, [flipped])
    sols, grids = _solved(text)
    _, _, spc1, forces, moments = parse_cards(text)
    (_, _, support_gids), = [s for s in spc1 if s[1] == "123456"]
    (sid, sol), = sols.items()

    applied = resultant(forces, moments, grids, sid, grids[support_gids[0]])
    got = total_reaction(sol.reactions, grids, ref=grids[support_gids[0]])
    assert not closes(got.force[1], 0.0, scale=applied.force_scale), (
        f"a reversed fin load left the support reacting {got.force[1]} in y -- "
        "this gate cannot see a lateral sign error")
    # ...and it is the fin load **twice over**: the deck now applies the reversed
    # load *and* the relief that was solved to cancel the original one, so it
    # carries -2*L_v and the support reacts +2*L_v. Asserting the number and not
    # merely "non-zero" is what makes this a calibration of the gate rather than
    # a smoke test -- it says how much of a sign error it would take to hide.
    _, want, _ = to_force(0.0, 2.0 * fin_load(case) * case.safety_factor, 0.0,
                          _units(system))
    assert closes(got.force[1], want, scale=applied.force_scale), got.force[1]

    # The roll and yaw reactions move with it -- the two moment DOF the lateral
    # family is the first to exercise, and the two the paper closure and the
    # card sum share an assumption about (the lever arms). Here they are the
    # solver's own, computed from the GRID cards.
    for axis, name in ((0, "roll"), (2, "yaw")):
        assert not closes(got.moment[axis], 0.0, scale=applied.moment_scale), (
            f"a reversed fin load left the support's {name} reaction at "
            f"{got.moment[axis]}")


# --------------------------------------------------------------------------- #
# The end-to-end claim: the path a real user takes (S-5)
# --------------------------------------------------------------------------- #
@pytest.mark.roundtrip
def test_wing_deck_solves_through_the_sbeam_command_line(sbeam, tmp_path):
    """``python -m sbeam ga6.stick.bdf`` exits 0 and writes an ``.f06`` that agrees.

    Every other test here goes through sbeam's Python API, which keeps them out
    of hostage to another repository's report formatting. This one proves the
    path an actual user takes works end to end -- and it is the only test that
    reads ``.f06`` text, asserting a substring and one number rather than a
    layout.
    """
    _, wing, _, _ = _components("ga6_normal.project.json")
    u = _units(UnitSystem.IMPERIAL)
    bdf = tmp_path / "ga6.stick.bdf"
    bdf.write_text(sb.stick_model_bdf(wing, sid_base=1, system=UnitSystem.IMPERIAL))

    run = subprocess.run([sys.executable, "-m", "sbeam", str(bdf)],
                         capture_output=True, text=True)
    assert run.returncode == 0, f"sbeam exited {run.returncode}: {run.stderr}"
    f06 = (tmp_path / "ga6.stick.f06").read_text()
    assert "F O R C E S   O F   S I N G L E - P O I N T   C O N S T R A I N T" in f06
    for idx, r in enumerate(wing):
        assert f"SUBCASE {sb._sid(1, idx, r)}" in f06

    # The root reaction printed in the .f06 is the span CSV's root shear (W-c).
    first = wing[0]
    _, _, want = to_force(0.0, 0.0, first.stations[0].sz * first.safety_factor, u)
    block = f06.split(f"SUBCASE {sb._sid(1, 0, first)}")[1]
    spc = block.split("S I N G L E - P O I N T   C O N S T R A I N T")[1].splitlines()
    row = [ln for ln in spc if ln.split()[:2] == [str(sb._ROOT_GID), "G"]][0]
    # The six components are fixed-width and run together when one is negative
    # ("1.537812E+03-1.255918E-09"), so they are read as numbers, not as columns.
    got = float(re.findall(r"-?\d\.\d+E[+-]\d+", row)[2])   # T1, T2, T3
    assert closes(got, -want, scale=abs(want)), f"f06 root T3 {got} vs {-want}"


# --------------------------------------------------------------------------- #
# The negative tests -- a gate nobody has seen fail is a gate nobody knows works
# --------------------------------------------------------------------------- #
def _mutate(text, predicate, transform):
    """Rewrite the first deck line satisfying ``predicate``; assert one matched."""
    out, hit = [], False
    for line in text.splitlines():
        if not hit and predicate(line):
            line, hit = transform(line), True
        out.append(line)
    assert hit, "the mutation matched no line -- the deck format changed"
    return "\n".join(out) + "\n"


@pytest.mark.roundtrip
def test_a_scaled_wing_force_card_breaks_the_wing_assertions(sbeam):
    """Mutation 1: scale one wing ``FORCE`` card's ``n3`` by 1.01 -> W-a and W-c fail."""
    _, wing, _, _ = _components("ga6_normal.project.json")
    u = _units(UnitSystem.IMPERIAL)
    text = sb.stick_model_bdf(wing, sid_base=1)
    sid = sb._sid(1, 0, wing[0])

    def bump(line):
        f = line.split(",")
        f[-1] = f" {float(f[-1]) * 1.01:.6E}"
        return ",".join(f)

    broken = _mutate(text, lambda ln: ln.startswith(f"FORCE, {sid},"), bump)
    sols, grids = _solved(broken)
    _, _, _, forces, moments = parse_cards(broken)
    applied = resultant(forces, moments, grids, sid, grids[sb._ROOT_GID])
    reaction = sols[sid].reactions[sb._ROOT_GID]
    st, sf = wing[0].stations[0], wing[0].safety_factor
    _, _, want_fz = to_force(0.0, 0.0, st.sz * sf, u)

    # W-a still holds -- the solver faithfully reacts whatever it was given...
    assert closes(reaction[2], -applied.fz, scale=applied.force_scale)
    # ...and W-c is what catches it, because its target is the NETLOADS
    # quadrature rather than the cards.
    assert not closes(reaction[2], -want_fz, scale=abs(want_fz))
    assert not closes(sols[sid].bar_forces[1].shear1, want_fz, scale=abs(want_fz))


@pytest.mark.roundtrip
def test_swapped_subcase_load_ids_break_the_per_case_assertions(sbeam):
    """Mutation 2: swap two ``SUBCASE``s' ``LOAD`` ids -> the per-case checks fail.

    Symmetry is the risk this rules out: if every case were checked against a
    deck-wide total, a routing error would pass. Case identity (M4-2 decisions
    8/9) is only real if a mis-selected load set is detectable.
    """
    _, wing, _, _ = _components("ga6_normal.project.json")
    u = _units(UnitSystem.IMPERIAL)
    a, b = sb._sid(1, 0, wing[0]), sb._sid(1, 1, wing[1])
    text = sb.stick_model_bdf(wing, sid_base=1)
    swapped = text.replace(f"  LOAD = {a}", "  LOAD = @@").replace(
        f"  LOAD = {b}", f"  LOAD = {a}").replace("  LOAD = @@", f"  LOAD = {b}")
    assert swapped != text

    sols, _ = _solved(swapped)
    st, sf = wing[0].stations[0], wing[0].safety_factor
    _, _, want_fz = to_force(0.0, 0.0, st.sz * sf, u)
    assert not closes(sols[a].reactions[sb._ROOT_GID][2], -want_fz,
                      scale=abs(want_fz))


@pytest.mark.roundtrip
def test_a_displaced_body_grid_breaks_the_free_free_reaction(sbeam):
    """Mutation 3: displace one body ``GRID``'s ``x`` by 1% -> B-b fails.

    This is the assertion a card-sum check **cannot** make. The applied ``FORCE``
    cards are untouched, so every force sum in the deck still closes exactly; what
    moves is a lever arm the solver reads from the file, and only a solve that
    assembles the model from those coordinates can see it. If this test ever
    stops failing, B-b has stopped being a geometry check.
    """
    _, _, body, _ = _components("ga6_normal.project.json")
    text = _body_deck(body, UnitSystem.IMPERIAL)
    sid = sb._sid(1, 0, body[0])
    grids = parse_cards(text)[0]
    # Displace a mid-beam node: an end node is a support, and moving it would
    # change the support geometry rather than a load's lever arm.
    target = sorted(grids, key=lambda g: grids[g][0])[len(grids) // 2]

    def shift(line):
        f = line.split(",")
        f[3] = f" {float(f[3]) * 1.01:.6E}"
        return ",".join(f)

    broken = _mutate(text, lambda ln: ln.startswith(f"GRID, {target},"), shift)
    sols, broken_grids = _solved(broken)
    _, _, _, forces, moments = parse_cards(broken)

    applied = resultant(forces, moments, broken_grids, sid, (0.0, 0.0, 0.0))
    assert closes(applied.fz, 0.0, scale=applied.force_scale), \
        "the force sum must still close -- only geometry was mutated"
    got = total_reaction(sols[sid].reactions, broken_grids)
    assert not closes(got.moment[1], 0.0, scale=applied.moment_scale)


# --------------------------------------------------------------------------- #
# The wrapper itself -- checked without a solver, so it is covered everywhere
# --------------------------------------------------------------------------- #
def test_the_wrapper_refuses_a_deck_with_no_geometry():
    """Control-surface decks carry no ``GRID`` cards, and cannot be wrapped (S-3)."""
    from sloads.modules.aileron import build_aileron

    control = build_aileron(_project("ga6_normal.project.json"))
    text = sb.control_surface_force_moment_cards(control, sid_base=1)
    with pytest.raises(ValueError, match="no GRID cards"):
        wrap_as_stick_model(text, support=Support.CLAMPED_FIRST)


def test_the_wrapper_refuses_an_already_solvable_deck():
    """The wing stick deck must be tested as shipped, not as a wrapped copy."""
    _, wing, _, _ = _components("ga6_normal.project.json")
    with pytest.raises(ValueError, match="already carries CBAR"):
        wrap_as_stick_model(sb.stick_model_bdf(wing, sid_base=1),
                            support=Support.CLAMPED_FIRST)


def test_the_wrapper_refuses_an_ungrouped_node():
    """A node in no group is unattached, hence singular -- so it must be loud."""
    _, _, _, tail = _components("ga6_normal.project.json")
    text = sb.tail_force_moment_cards(tail, sid_base=1)
    with pytest.raises(ValueError, match="in no group"):
        wrap_as_stick_model(text, support=Support.CLAMPED_FIRST,
                            groups=_tail_groups(tail)[:1])


def test_the_tail_wrapper_needs_its_groups():
    """Ungrouped, the wrapper threads one beam through **both** tail surfaces.

    Pinned because it is the finding that shaped the wrapper's API, and because
    the failure is silent rather than loud: the h-tail and v-tail chord lines are
    different beams stated from their own leading edges, so their stations
    interleave in ``x`` and their first stations are coincident. A single element
    run through them solves happily and means nothing. ``groups`` is therefore
    load-bearing, not decorative.
    """
    _, _, _, tail = _components("ga6_normal.project.json")
    text = sb.tail_force_moment_cards(tail, sid_base=1)
    groups = _tail_groups(tail)
    assert len(groups) == 2, "ga6 exports both an h-tail and a v-tail"
    bands = {gid: i for i, g in enumerate(groups) for gid in g}

    _, mixed, _, _, _ = parse_cards(
        wrap_as_stick_model(text, support=Support.CLAMPED_FIRST))
    assert any(bands[ga] != bands[gb] for _, ga, gb in mixed), \
        "ungrouped, the chain is expected to cross the two tail beams"

    _, clean, _, _, _ = parse_cards(
        wrap_as_stick_model(text, support=Support.CLAMPED_FIRST, groups=groups))
    assert all(bands[ga] == bands[gb] for _, ga, gb in clean), \
        "grouped, no element may join the h-tail to the v-tail"


@pytest.mark.parametrize("system", SYSTEMS)
def test_the_body_wrapper_support_is_determinate(system):
    """Six constraints, no redundancy -- and the deck's own cards are untouched.

    Statically determinate is the whole basis of "the reaction is the residual":
    a redundant support would share the residual out by stiffness and the zero
    target would stop meaning anything.
    """
    _, _, body, _ = _components("ga6_normal.project.json")
    cards = sb.body_force_moment_cards(body, sid_base=1, system=system)
    text = _body_deck(body, system)
    _, cbars, spc1, forces, moments = parse_cards(text)
    grids, _, _, card_forces, card_moments = parse_cards(cards)

    assert (forces, moments) == (card_forces, card_moments), \
        "the wrapper must not touch the deck's load cards"
    assert len(cbars) == len(grids) - 1, "one element per gap in the beam line"
    constrained = sum(len(comp) for _, comp, gids in spc1 for _ in gids)
    assert constrained == 6, f"support has {constrained} constraints, not 6"


def test_the_assembled_wrapper_keeps_the_decks_own_support():
    """The wrapper adds structure to the primary deliverable and nothing else.

    If it re-supported the deck, the leg would be testing the harness's idea of a
    determinate support instead of the one the deliverable ships with.
    """
    project, _, _, _ = _components("ga6_normal.project.json")
    shipped = balanced_deck(project)
    wrapped = _assembled_deck(project, UnitSystem.IMPERIAL)
    s_grids, s_cbars, s_spc1, s_f, s_m = parse_cards(shipped)
    w_grids, w_cbars, w_spc1, w_f, w_m = parse_cards(wrapped)

    assert (s_grids, s_spc1, s_f, s_m) == (w_grids, w_spc1, w_f, w_m)
    assert not s_cbars and len(w_cbars) == len(s_grids) - 1
    assert "SOL 101" in wrapped and wrapped.count("BEGIN BULK") == 1


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
