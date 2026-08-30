"""#33 -- an iterative solve says how it ended, or it does not return.

The defect class: a bounded search that ``break``s when it succeeds and falls out
of the loop when it does not, returning the last iterate either way. The caller
cannot tell the two apart, and in this suite the caller is every V-n point, every
SELECT pick, every balanced case and every exported deck. This file is the gate
that the class stays closed:

* a **source sweep** -- no bounded search in ``sloads/`` may fall out silently;
* the **behaviour** at the three sites the sweep found (the balance's two loops,
  the wing panel density, the flap slipstream);
* the **clamp** -- the one non-converged outcome that is a real flight state, and
  the fixed-point property that makes exiting on it arithmetically free.

Run standalone: ``python tests/test_convergence.py``.
"""
from __future__ import annotations

import ast
import dataclasses
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io
from sloads.convergence import SolverFailure, SolveState
from sloads.modules import flight_envelope as fe
from sloads.modules.flap import _slipstream_velocity
from sloads.modules.wing_inertia import _root_density

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sloads")


def _project(name):
    return io.load_project(os.path.join(_EXAMPLES, name))


def _examples():
    return sorted(f for f in os.listdir(_EXAMPLES) if f.endswith(".project.json"))


# --------------------------------------------------------------------------- #
# The drift guard: no bounded search falls out of its loop in silence
# --------------------------------------------------------------------------- #
#: Loops that ``break`` but need no refusal, each with the reason it is not the
#: defect class. Keyed by ``module:function``.
_NO_REFUSAL_NEEDED = {
    "modules/one_engine_out.py:simulate":
        "a time march to a fixed end time, not a search: running out of steps is "
        "the normal end of the simulation and 'recovered' already states whether "
        "the airplane came back before it",
    "modules/weight_estimate.py:estimate":
        "WTESTIMA's 1 % take-off-weight inflation has no trip bound to exhaust -- "
        "options/misc grows without limit while the structural fractions sum to "
        "less than one, so the loop ends or the fraction table is degenerate",
    "export/report_package.py:browse_start":
        "a walk up the filesystem to the nearest directory that exists, not a "
        "numerical search: the loop is bounded by the path's own depth and "
        "falling out at the filesystem root is the correct answer, which is the "
        "value it then returns",
}


def _is_trip_counted(node):
    """Is this loop an *iteration*, as opposed to a walk over a collection?

    The class is the fixed-point search: a trip counter (``for _ in range(N)``)
    or a condition (``while ...``). A loop over ``zip``/``enumerate``/a list that
    breaks on a match is a lookup -- falling off the end of a collection means
    "not there", which is a fact, not an unconverged answer.
    """
    if isinstance(node, ast.While):
        return True
    return (isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range")


def _loops_that_can_fall_out():
    """Every bounded *iteration* in ``sloads/`` that ``break``s, with its function."""
    found = []
    for root, _dirs, files in os.walk(_PKG):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, _PKG)
            tree = ast.parse(open(path, encoding="utf-8").read(), path)
            for func in ast.walk(tree):
                if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(func):
                    if not isinstance(node, (ast.For, ast.While)):
                        continue
                    if not _is_trip_counted(node):
                        continue
                    breaks = any(isinstance(n, ast.Break) for n in ast.walk(node)
                                 if not isinstance(n, (ast.For, ast.While))
                                 or n is node)
                    if not breaks:
                        continue          # runs to completion by design
                    raises = any(isinstance(n, ast.Raise) for n in node.orelse)
                    found.append((f"{rel}:{func.name}", raises))
    return found


def test_no_bounded_search_in_the_package_falls_out_in_silence():
    """The #33 class, closed structurally rather than by prose.

    A loop that ``break``s on success and has no ``else: raise`` returns its last
    iterate when the search fails -- the shape this step removed from three sites.
    A new one has to either refuse or be classified here, with its reason.
    """
    silent = sorted({where for where, raises in _loops_that_can_fall_out()
                     if not raises and where not in _NO_REFUSAL_NEEDED})
    assert not silent, (
        "bounded search with no refusal on exhaustion (add 'else: raise "
        "solver_failure(...)' or classify it in _NO_REFUSAL_NEEDED): "
        + ", ".join(silent))


def test_the_classified_loops_still_exist():
    """An allowlist that outlives its entries stops meaning anything."""
    present = {where for where, _ in _loops_that_can_fall_out()}
    stale = sorted(set(_NO_REFUSAL_NEEDED) - present)
    assert not stale, f"_NO_REFUSAL_NEEDED names loops that are gone: {stale}"


# --------------------------------------------------------------------------- #
# The balance: what the shipped fixtures actually do
# --------------------------------------------------------------------------- #
#: Every V-n row on a shipped fixture whose balance clamps at the Mach cap --
#: measured 2026-08-22, and the same nine rows decision **D-30** ruled ordinary
#: stall-limited flight. Nothing else in the suite reaches a non-converged state.
_CLAMPED = {
    "atr42_100.project.json": {
        ("MAN A", "aft gross", 25000.0), ("MAN C", "aft gross", 25000.0),
        ("AC ROLL", "aft gross", 25000.0),
        ("MAN A", "fwd gross", 25000.0), ("MAN C", "fwd gross", 25000.0),
        ("AC ROLL", "fwd gross", 25000.0),
        ("MAN A", "mid gross", 25000.0), ("MAN C", "mid gross", 25000.0),
        ("AC ROLL", "mid gross", 25000.0),
    },
}


@pytest.mark.parametrize("example", _examples())
def test_every_shipped_fixture_balances_or_says_why(example):
    """No shipped fixture reaches the ``FAILED`` state: the refusals added here
    are dead paths on the delivered data, which is the point of adding them."""
    env = fe.build_envelope(_project(example))
    clamped = {(p.condition, p.cg, p.altitude_ft) for p in env.vn if env.is_clamped(p)}
    assert clamped == _CLAMPED.get(example, set())


def test_the_clamped_rows_are_the_mach_capped_corner_and_nothing_else():
    """Pinned by count as well as identity: a tenth clamped row on this fixture
    is a physics change, not a rounding difference, and #32's marker will publish
    exactly this set."""
    env = fe.build_envelope(_project("atr42_100.project.json"))
    assert len(env.vn) == 300
    assert len(env.clamped_cases) == 9
    assert all(env.is_clamped(p) == (p.case in env.clamped_cases) for p in env.vn)


def test_a_clamped_solve_is_a_fixed_point_not_an_abandoned_search():
    """Why breaking on the clamp costs nothing.

    The Mach cap pins the true airspeed, so every further trip of the
    dynamic-pressure loop re-solves the identical inner problem from the identical
    ``q``. Demonstrated as the fixed point itself: re-balancing the clamped point
    *from its own converged speed* reproduces it bit-for-bit, so the 199 trips the
    exit skips could not have changed the answer. (The whole-fixture check is the
    frozen digest and the SELECT pins, which did not move when this landed.)
    """
    project = _project("atr42_100.project.json")
    env = fe.build_envelope(project)
    point = next(p for p in env.vn if env.is_clamped(p) and p.condition == "MAN A")

    fl = project.flight_loads
    wr = fe.require_wing_reference(project)
    di = fe.design_inputs(project)
    cruise = next(c for c in fe.balance_configs(project.aero_coeffs) if not c.flaps_down)
    cg = next(c for c in fe.flight_cases(project) if c.name == point.cg)

    again = fe._balance(point.nz, point.v_eas_kt, di.mc, cruise, cg, fl, wr,
                        point.altitude_ft)
    assert again.state is SolveState.CLAMPED
    assert again.v_eas == point.v_eas_kt
    assert again.lt == point.lt
    assert again.cl == point.cl

    # And the speed it is pinned at is the Mach cap's own, not a search result.
    sig = fe.density_ratio(point.altitude_ft)
    capped = di.mc * fe._speed_of_sound(point.altitude_ft) * math.sqrt(sig)
    assert math.isclose(point.v_eas_kt, capped, rel_tol=1e-12)


def test_the_clamped_set_is_the_rows_the_published_numbers_also_flag():
    """One state, two ways of seeing it -- pinned to agree.

    ``aero_curves.curve_closure`` finds the same corner from the *outside*: it
    recovers each published point's CL and compares it with the Mach-adjusted
    stall CL (the Aerodynamic Data page's stall-clamp margin, and the predicate
    #32's marker would otherwise re-derive). ``clamped_cases`` is the same fact
    from the inside, stated by the solver that hit it. They must name the same
    rows: if they ever diverge, one of them is describing something else.
    """
    from sloads.aero_curves import STALL_CLOSURE_TOL, recovered_cl, stall_limits

    project = _project("atr42_100.project.json")
    env = fe.build_envelope(project)
    wr = fe.require_wing_reference(project)
    config = fe.balance_configs(project.aero_coeffs)[0]

    outside = set()
    for p in env.vn:
        rec = recovered_cl(p, wr.s_sqft)
        pos, neg = stall_limits(config, p.g_corr, project.flight_loads.mn)
        if max(rec - pos, neg - rec) > STALL_CLOSURE_TOL:
            outside.add(p.case)
    assert outside == set(env.clamped_cases)


def test_a_clamped_row_carries_its_state_no_further_than_memory():
    """``clamped_cases`` is derived, not persisted (no schema hop): a project
    round-tripped through JSON comes back with the list empty rather than stale."""
    project = _project("atr42_100.project.json")
    project.envelope = fe.build_envelope(project)
    assert project.envelope.clamped_cases
    reloaded = io.project_from_dict(io.project_to_dict(project))
    assert reloaded.envelope is not None
    assert len(reloaded.envelope.vn) == 300
    assert reloaded.envelope.clamped_cases == []


# --------------------------------------------------------------------------- #
# The refusals
# --------------------------------------------------------------------------- #
def test_an_unreachable_load_factor_is_refused_instead_of_reported():
    """The masked defect, made visible.

    A CG 40 in ahead of the forwardmost mass in the airplane cannot be trimmed to
    1 g at any angle of attack. The balance used to report the angle it gave up
    at -- NZ 0.658 presented as a 1-g point, on into SELECT and the decks. Now it
    refuses, and the message carries the condition rather than a stack trace.
    """
    project = _project("concept_regional_jet.project.json")
    case = next(c for c in project.weight.cg_cases if c.name == "fwd gross")
    case.loading = None
    case.xcg = min(it.x for it in project.weight.items) - 40.0
    with pytest.raises(SolverFailure) as excinfo:
        fe.build_envelope(project)
    message = str(excinfo.value)
    assert "angle-of-attack iteration" in message
    assert "fwd gross" in message and "CRUISE" in message
    assert "target n=" in message and "reached NZ=" in message


def test_the_wing_panel_density_refuses_rather_than_returning_its_last_step(monkeypatch):
    """A panel weight the taper cannot reach: the density walks its whole range
    without the integrated mass entering the ±1 % band."""
    monkeypatch.setattr("sloads.modules.wing_inertia._DENSITY_TRIPS", 500)
    project = _project("ga6_normal.project.json")
    wm = dataclasses.replace(project.wing_mass, panel_weight_lb=1.0e9)
    ye = [10.0, 20.0, 30.0]
    with pytest.raises(SolverFailure) as excinfo:
        _root_density([100.0] * 3, ye, [50.0] * 3, 10.0, 30.0, wm, 0)
    assert "root-density iteration" in str(excinfo.value)
    assert "500 iterations" in str(excinfo.value)


def test_the_slipstream_search_refuses_a_disk_that_cannot_absorb_the_power():
    """It used to return the guard value: a 100,000 ft/s slipstream, and the flap
    load amplified by its square, delivered as a result."""
    with pytest.raises(SolverFailure) as excinfo:
        _slipstream_velocity(100.0, maxhp=1.0e12, pdia_in=1.0)
    assert "slipstream-velocity search" in str(excinfo.value)


def test_a_solver_failure_is_a_value_error_so_run_all_cannot_swallow_it():
    """The error contract: ``MissingInputError`` means 'not my turn' and is
    skipped by ``run_all_modules``; a calc that cannot close is a defect and must
    stay visible (`00_program_overview.md`)."""
    from sloads.models import MissingInputError

    assert issubclass(SolverFailure, ValueError)
    assert not issubclass(SolverFailure, MissingInputError)


if __name__ == "__main__":  # zero-dependency self-runner
    raise SystemExit(pytest.main([__file__, "-q"]))
