"""The engine hub thrust ``FORCE`` -- gates G-1 … G-11 (backlog #10).

Carved out of design note ``docs/30_future/21_power_effects_wing_note.md``,
whose seven-step wake plan stays parked. What ships is one user-entered
``EngineInput.thrust_lb`` per engine, applied as an axial force at that
engine's hub, and this file is its benchmark-first gate. There is no printed
oracle for a number the user types, so every gate here is a **closed form or an
invariant** -- the standard `CLAUDE.md` rule 2 sets for concept-mode physics:

* **G-1** the feature is off by default and changes nothing: no shipped fixture
  enters thrust, ``None`` and ``0.0`` both apply nothing, and the assembled set
  is identical load for load to the one built before this step;
* **G-2** what is applied is exactly what was entered: one force per engine at
  its own ``prop_cg``, ``fx = -T`` (``CONVENTIONS.md`` §1, ``x`` +aft), summing
  to the entered total;
* **G-3** the residual **is** the thrust: the pre-closure ``Fx`` moves by
  exactly ``-sum T`` and the pre-closure ``My`` by exactly
  ``sum -T*(z_hub - z_cg)``, both in closed form -- the reason
  :data:`~sloads.modules.balance.RESIDUAL_GATE` is exempted for a powered case
  rather than merely relaxed;
* **G-4** ``n_x = (D - sum T)/W``: a constructed case whose thrust equals its
  own drag closes at ``n_x = 0`` -- design note 21 §4.3's stated gate;
* **G-5** six-DOF closure still holds with thrust in the set, in memory and from
  the balanced deck's own card text;
* **G-6** the thrust lands on the LRA **hub node**, with a transfer couple of
  exactly zero, and the transferred set keeps the case's resultant (the plan-07
  gate, with thrust present);
* **G-7** thrust with nowhere to act **raises**, naming the datum, rather than
  being placed on a guess;
* **G-8** ground cases carry no thrust and say so in-band;
* **G-9** the hub falls back to ``engine_cg`` only when no ``prop_cg`` is
  entered;
* **G-10** the port twin of a handed powered case carries the mirrored thrust;
* **G-11** an **asymmetric** installation yaws the airplane and says so, mints
  no twin of its own (``is_handed`` measures lateral force and roll, and an
  axial force off the centreline makes neither), and states that a twin got
  from another source mirrors the installation with everything else.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import replace

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

from sloads import io  # noqa: E402
from sloads.export.balanced_deck import balanced_deck, case_sids  # noqa: E402
from sloads.export.equilibrium import closes, deck_resultants  # noqa: E402
from sloads.export.lra_model import build_lra_model, transferred_case_loads  # noqa: E402
from sloads.models import MissingInputError  # noqa: E402
from sloads.modules.balance import (  # noqa: E402
    HUB_THRUST_SOURCE,
    build_balanced_cases,
    handed_twin,
    hub_thrust,
    is_ground,
    is_powered,
    resultant6,
)

#: A twin-turboprop with wing-mounted engines whose hub (``prop_cg``, x = 300)
#: is forward of the mount (x = 365) and off the centreline (y = +/-168) -- so
#: the thrust has a real lever arm in pitch and the two hubs are distinct nodes.
TWIN = "dhc8_dash8.project.json"

#: A single, fuselage-mounted engine on the centreline: the degenerate case the
#: closed forms must also hold for (and the one where ``side`` is ``"C"``).
SINGLE = "ga6_normal.project.json"

#: The entered thrust, lb per engine. Deliberately large enough that the pitch
#: couple it makes is far outside the 1 % residual gate (G-3's whole point) and
#: not a round fraction of anything else in the fixture.
THRUST = 4000.0


def _project(name):
    return io.load_project(os.path.join(_ROOT, "examples", name))


def _powered(name, thrust=THRUST):
    """``(unpowered project, powered project)`` -- the same fixture, one input
    apart. Every gate below is a difference between these two, so nothing here
    can pass by agreeing with a number this test wrote."""
    p = _project(name)
    return p, replace(p, engines=[replace(e, thrust_lb=thrust)
                                  for e in p.engines])


def _by_id(cases):
    return {(c.label, c.hand): c for c in cases}


def _flight(cases):
    return [c for c in cases if not is_ground(c)]


# --------------------------------------------------------------------------- #
# G-1 -- off by default, and off means bit-for-bit
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", ["ga6_normal.project.json",
                                     "cessna_210.project.json",
                                     "atr42_100.project.json",
                                     "dhc8_dash8.project.json",
                                     "concept_regional_jet.project.json"])
def test_no_shipped_fixture_enters_thrust(example):
    """G-1a. Today's cases are **exactly** zero-thrust, which is the claim the
    backlog row makes and the reason no shipped deck moved when this landed."""
    project = _project(example)
    assert all(e.thrust_lb is None for e in project.engines), (
        f"{example} enters thrust -- every gate that reads 'unchanged' in this "
        "suite assumed it did not")
    for case in build_balanced_cases(project):
        assert not is_powered(case), f"{example} {case.label}"
        assert hub_thrust(case) == 0.0


@pytest.mark.parametrize("example", [TWIN, SINGLE])
@pytest.mark.parametrize("value", [None, 0.0])
def test_no_thrust_and_zero_thrust_are_the_same_airplane(example, value):
    """G-1b. ``0.0`` is not a load. The two projects assemble load for load,
    number for number identical sets -- so a fixture that enters an explicit
    zero cannot drift from one that enters nothing."""
    _, project = _powered(example, value)
    base = _by_id(build_balanced_cases(_project(example)))
    got = _by_id(build_balanced_cases(project))
    assert got.keys() == base.keys()
    for key, case in got.items():
        ref = base[key]
        assert not is_powered(case), key
        assert case.loads == ref.loads, key
        assert (case.residual_fx, case.residual_my) == (ref.residual_fx,
                                                        ref.residual_my), key
        assert (case.delta_nx, case.q_dot) == (ref.delta_nx, ref.q_dot), key


# --------------------------------------------------------------------------- #
# G-2 -- what is applied is what was entered
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", [TWIN, SINGLE])
def test_one_force_per_engine_at_its_own_hub(example):
    """G-2. One load per engine, at that engine's ``prop_cg``, purely axial and
    forward: ``fx = -T`` with no ``fy``/``fz``/moment content (the thrust-line
    incidence and toe angles stay parked with note 21)."""
    _, project = _powered(example)
    # Sorted, because a port twin's set is the mirror image of the starboard
    # one (G-10) and the fixture's hub pair is mirror-symmetric: the *positions*
    # are the assertion, not the order the reflection happens to leave them in.
    hubs = sorted(tuple(e.prop_cg) for e in project.engines)
    for case in _flight(build_balanced_cases(project)):
        applied = [ld for ld in case.loads if ld.source == HUB_THRUST_SOURCE]
        assert len(applied) == len(project.engines), case.label
        assert sorted((ld.x, ld.y, ld.z) for ld in applied) == hubs, case.label
        for load in applied:
            assert load.fx == -THRUST
            assert (load.fy, load.fz, load.mx, load.my, load.mz) == (
                0.0, 0.0, 0.0, 0.0, 0.0)
        assert hub_thrust(case) == pytest.approx(
            THRUST * len(project.engines), rel=0, abs=1e-9)
        assert is_powered(case)


# --------------------------------------------------------------------------- #
# G-3 -- the residual IS the thrust (closed form, both components)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", [TWIN, SINGLE])
def test_the_pre_closure_residual_moves_by_exactly_the_thrust(example):
    """G-3. Nothing else in the case changes, so the whole difference between
    the powered and unpowered residual is the applied force and its own arm:

        ``dFx = -sum T``      ``dMy = sum -T*(z_hub - z_cg)``

    That exactness is *why* the 1 % pitch gate is exempted for a powered case
    rather than widened -- the residual is a known quantity, not a slack one.
    """
    base_p, project = _powered(example)
    base = _by_id(build_balanced_cases(base_p))
    n_engines = len(project.engines)
    for case in _flight(build_balanced_cases(project)):
        ref = base[(case.label, case.hand)]
        want_fx = -THRUST * n_engines
        want_my = math.fsum(-THRUST * (e.prop_cg[2] - case.cg_z)
                            for e in project.engines)
        where = f"{example} {case.label}{case.hand}"
        assert case.residual_fx - ref.residual_fx == pytest.approx(
            want_fx, rel=1e-12, abs=1e-6), where
        assert case.residual_my - ref.residual_my == pytest.approx(
            want_my, rel=1e-12, abs=1e-6), where
        # Nothing else moved: the vertical and lateral balance is untouched by
        # an axial force at a hub.
        assert case.residual_fz == pytest.approx(ref.residual_fz, rel=1e-12), where
        assert case.residual_fy == pytest.approx(ref.residual_fy, rel=1e-12), where
        assert case.residual_mz == pytest.approx(ref.residual_mz, rel=1e-12), where


@pytest.mark.parametrize("example", [TWIN, SINGLE])
def test_a_powered_case_states_what_nothing_balances(example):
    """G-3b. The exemption is in-band, not only in this file: every powered case
    carries the sentence that says the thrust is unbalanced by construction and
    which degrees of freedom carry it."""
    _, project = _powered(example)
    for case in _flight(build_balanced_cases(project)):
        note = "; ".join(case.notes)
        assert "engine thrust APPLIED at the hub" in note, case.label
        assert "NOTHING balances" in note, case.label
        assert "nx = (D - sum T)/W" in note, case.label
        assert "1 % residual gate does not apply" in note, case.label


# --------------------------------------------------------------------------- #
# G-4 -- n_x = (D - sum T) / W
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", [TWIN, SINGLE])
def test_thrust_equal_to_drag_closes_at_zero_longitudinal_load_factor(example):
    """G-4. Design note 21 §4.3's stated gate. The unpowered case's own
    ``residual_fx`` **is** its net drag; entering exactly that much thrust,
    split between the engines, must give ``n_x = 0`` -- not approximately, to
    the solver's own arithmetic.

    A case chosen rather than every case, because one entered thrust cannot
    equal every case's drag at once: this is the identity, not a sweep.
    """
    base_p, _ = _powered(example)
    # The case with the most net **aft** axial force. Not simply the first: the
    # strip model's chordwise force runs forward on the high-alpha conditions
    # (leading-edge suction), and a "thrust" equal to a forward residual would
    # be an aft force wearing the name.
    base = max(_flight(build_balanced_cases(base_p)),
               key=lambda c: c.residual_fx)
    drag = base.residual_fx
    assert drag > 0.0, f"{example} {base.label}: no case has net aft drag"
    n_engines = len(base_p.engines)
    project = replace(base_p, engines=[replace(e, thrust_lb=drag / n_engines)
                                       for e in base_p.engines])
    case = _by_id(build_balanced_cases(project))[(base.label, base.hand)]
    assert hub_thrust(case) == pytest.approx(drag, rel=1e-12)
    assert case.residual_fx == pytest.approx(0.0, abs=1e-6 * base.n_w)
    assert case.delta_nx == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# G-5 -- the closure still closes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", [TWIN, SINGLE])
def test_six_dof_closure_holds_with_thrust_in_the_set(example):
    """G-5a. Applied + closure sums to zero about the CG in all six components.
    The thrust is not exempt from equilibrium -- only from *trim*."""
    _, project = _powered(example)
    for case in _flight(build_balanced_cases(project)):
        fx, fy, fz, mx, my, mz = resultant6(
            case.loads, (case.cg_x, 0.0, case.cg_z))
        n_w = case.n_w
        where = f"{example} {case.label}{case.hand}"
        for name, got, scale in (("fx", fx, n_w), ("fy", fy, n_w),
                                 ("fz", fz, n_w),
                                 ("mx", mx, n_w * case.semi_span),
                                 ("my", my, n_w * case.mac),
                                 ("mz", mz, n_w * case.semi_span)):
            assert abs(got) < 1e-9 * scale, f"{where}: {name} = {got}"


def test_the_balanced_deck_carries_the_thrust_and_still_balances():
    """G-5b. From the deck's own card text, not from memory: the subcase's
    ``FORCE`` cards sum to the entered thrust in ``x``, and the whole set
    (applied + closure) resolves to zero -- the deck's free-free claim, with
    power in it."""
    _, project = _powered(TWIN)
    cases = build_balanced_cases(project)
    text = balanced_deck(project, cases=cases)
    resultants = deck_resultants(text)
    powered = [(c, sid) for c, sid in zip(cases, case_sids(cases))
               if is_powered(c)]
    assert powered
    for case, sid in powered:
        got = resultants[sid]
        where = f"{case.label}{case.hand} (SID {sid})"
        # The applied thrust is in the deck's own cards: the x sum of the load
        # set is zero only because the closure relief cancels it, so check the
        # thrust is there before checking it closes.
        assert got.n_force, where
        for name in ("fx", "fy", "fz"):
            assert closes(getattr(got, name), 0.0, scale=got.force_scale), (
                f"{where}: {name} = {getattr(got, name)}")
        for name in ("mx", "my", "mz"):
            assert closes(getattr(got, name), 0.0, scale=got.moment_scale), (
                f"{where}: {name} = {getattr(got, name)}")


# --------------------------------------------------------------------------- #
# G-6 -- it lands on the hub node the skeleton already had
# --------------------------------------------------------------------------- #
def test_the_thrust_lands_on_the_lra_hub_node_with_no_transfer_couple():
    """G-6. The point of the carve-out: the LRA skeleton has carried an engine
    hub node since R-9 and has never had a load on it. The thrust is built at
    that node's own position, so the lever-arm couple is *identically* zero and
    the deck's hub node shows the entered force and nothing else."""
    _, project = _powered(TWIN)
    model = build_lra_model(project)
    hubs = {tuple(e.prop_cg) for e in project.engines}
    hub_gids = {n.gid: n.pos for n in model.members["engine"] if n.pos in hubs}
    assert len(hub_gids) == len(project.engines), "the hub nodes are not distinct"

    case = next(c for c in build_balanced_cases(project) if is_powered(c))
    thrust_only = replace(case, loads=[ld for ld in case.loads
                                       if ld.source == HUB_THRUST_SOURCE])
    transferred = transferred_case_loads(thrust_only, model)
    assert set(transferred) == set(hub_gids), (
        "the thrust did not land on the hub nodes")
    for gid, (force, moment) in transferred.items():
        assert force == [-THRUST, 0.0, 0.0], gid
        assert moment == [0.0, 0.0, 0.0], gid


def test_the_transferred_set_keeps_the_resultant_with_thrust_present():
    """G-6b. The plan-07 acceptance gate (LM-1), re-run with power: the set on
    the model's nodes has the identical resultant the balanced case's set has,
    about the CG."""
    _, project = _powered(TWIN)
    model = build_lra_model(project)
    case = next(c for c in build_balanced_cases(project) if is_powered(c))
    ref = (case.cg_x, 0.0, case.cg_z)
    want = resultant6(case.loads, ref)

    got = [0.0] * 6
    for gid, (force, moment) in transferred_case_loads(case, model).items():
        pos = next(n.pos for n in model.nodes if n.gid == gid)
        dx, dy, dz = pos[0] - ref[0], pos[1] - ref[1], pos[2] - ref[2]
        got[0] += force[0]
        got[1] += force[1]
        got[2] += force[2]
        got[3] += moment[0] + dy * force[2] - dz * force[1]
        got[4] += moment[1] + dz * force[0] - dx * force[2]
        got[5] += moment[2] + dx * force[1] - dy * force[0]
    scale = case.n_w * max(1.0, case.semi_span)
    for name, a, b in zip("fx fy fz mx my mz".split(), got, want):
        assert abs(a - b) < 1e-6 * scale, f"{name}: {a} vs {b}"


# --------------------------------------------------------------------------- #
# G-7 -- a thrust with nowhere to act is a refusal, not a guess
# --------------------------------------------------------------------------- #
def test_thrust_without_a_station_raises_naming_the_datum():
    """G-7. The refusal rule the LRA exporter already follows: name the missing
    datum rather than place the load on an assumed one."""
    project = _project(SINGLE)
    broken = replace(project, engines=[
        replace(e, thrust_lb=THRUST, prop_cg=(0.0, 0.0, 0.0),
                engine_cg=(0.0, 0.0, 0.0)) for e in project.engines])
    with pytest.raises(MissingInputError) as excinfo:
        build_balanced_cases(broken)
    message = str(excinfo.value)
    assert "prop_cg" in message and "engine_cg" in message
    assert "does not guess" in message


# --------------------------------------------------------------------------- #
# G-8 -- ground cases are not powered, and say so
# --------------------------------------------------------------------------- #
def test_a_ground_case_carries_no_thrust_and_states_it():
    """G-8. Flight only (the agreed scope): rating thrust per case family is
    note 21's parked power-policy table. The entered value is stated in-band on
    the ground case rather than dropped in silence."""
    _, project = _powered(TWIN)
    ground = [c for c in build_balanced_cases(project) if is_ground(c)]
    assert ground, "the fixture assembles no ground case"
    for case in ground:
        assert not is_powered(case), case.label
        assert hub_thrust(case) == 0.0
        note = "; ".join(case.notes)
        assert "is NOT applied to a ground case" in note, case.label


# --------------------------------------------------------------------------- #
# G-9 -- the hub, then the mount, and nothing else
# --------------------------------------------------------------------------- #
def test_the_station_falls_back_to_the_engine_cg_only_without_a_hub():
    """G-9. ``prop_cg`` is the hub and is what a thrust acts at; ``engine_cg``
    is the fallback for a project that entered a mount and no propeller."""
    project = _project(TWIN)
    no_hub = replace(project, engines=[
        replace(e, thrust_lb=THRUST, prop_cg=(0.0, 0.0, 0.0))
        for e in project.engines])
    case = next(c for c in build_balanced_cases(no_hub) if is_powered(c))
    applied = [(ld.x, ld.y, ld.z) for ld in case.loads
               if ld.source == HUB_THRUST_SOURCE]
    assert applied == [tuple(e.engine_cg) for e in project.engines]


# --------------------------------------------------------------------------- #
# G-10 -- reflection
# --------------------------------------------------------------------------- #
def test_the_port_twin_carries_the_mirrored_thrust():
    """G-10. A powered case that gains a hand from something else (its fin load
    or tail split) mirrors through the single owner: the starboard engine's
    thrust appears at the port hub, still forward, still ``-T``."""
    _, project = _powered(TWIN)
    case = next(c for c in build_balanced_cases(project)
                if is_powered(c) and c.hand == "R")
    twin = handed_twin(case)
    starboard = [ld for ld in case.loads if ld.source == HUB_THRUST_SOURCE]
    port = [ld for ld in twin.loads if ld.source == HUB_THRUST_SOURCE]
    assert len(port) == len(starboard)
    assert sorted(ld.y for ld in port) == sorted(-ld.y for ld in starboard)
    assert {ld.fx for ld in port} == {-THRUST}
    assert hub_thrust(twin) == pytest.approx(hub_thrust(case), rel=1e-12)


# --------------------------------------------------------------------------- #
# G-11 -- asymmetric thrust
# --------------------------------------------------------------------------- #
def test_asymmetric_thrust_yaws_the_airplane_and_says_so():
    """G-11. One engine of a pair, which is what the GUI produces when a user
    fills in the selected engine only. The case genuinely yaws, and the yaw is
    a moment ``is_handed`` cannot see (decision L-6: it reads lateral force and
    rolling moment, and a pure ``fx`` at ``y != 0`` makes neither). So it is
    measured and stated rather than silently emitted as a symmetric case, and
    the closure's ``r_dot`` carries it."""
    project = _project(TWIN)
    asymmetric = replace(project, engines=[
        replace(e, thrust_lb=THRUST if i == 0 else None)
        for i, e in enumerate(project.engines)])
    cases = [c for c in build_balanced_cases(asymmetric) if is_powered(c)]
    assert cases
    hub_y = project.engines[0].prop_cg[1]
    for case in cases:
        note = "; ".join(case.notes)
        assert "the entered thrust is ASYMMETRIC" in note, case.label
        assert "mints NO port twin of its own" in note, case.label
        assert "mirror-image airplane's case" in note, case.label
        # The yaw is the closed form mz = -y*fx (resultant6's own convention),
        # asserted as the *difference* from the same case without thrust so the
        # rest of the case's yaw content is not being fitted. A port twin got by
        # reflection has the whole set mirrored, hand included.
        sign = -1.0 if case.hand == "L" else 1.0
        want = _unpowered_mz(project, case) + sign * (-hub_y * -THRUST)
        assert case.residual_mz == pytest.approx(want, rel=1e-9, abs=1e-6), (
            f"{case.label}{case.hand}")
        assert case.r_dot != 0.0, case.label


def test_a_symmetric_pair_makes_no_yaw_and_no_asymmetry_note():
    """G-11b. The mirror-symmetric installation nets exactly zero yaw, so the
    statement above appears only where it is true."""
    _, project = _powered(TWIN)
    for case in _flight(build_balanced_cases(project)):
        assert not any("ASYMMETRIC" in n for n in case.notes), case.label


def _unpowered_mz(project, case):
    """The same case's yaw residual without thrust -- so G-11 asserts the
    *difference* is the thrust's own moment, not the whole number."""
    base = _by_id(build_balanced_cases(project))
    return base[(case.label, case.hand)].residual_mz


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
