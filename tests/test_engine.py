"""Validate the calculation core against the FAR 23 LOADS manual appendices.

The reciprocating reference is the Continental IO-520-BB example printed in the
manual (full.txt:24910-25028). The comparison values below are the manual's
*printed* figures; per Decision 3 ("modernize the math", pi -> math.pi) they are
matched with an engineering tolerance of ±0.1% (rel_tol=1e-3) rather than exact
equality, so genuine drift still fails loudly while the pi modernization does not.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import run_all
from sloads.basic import basic_int
from sloads.modules import engine as calc
from fixtures import io520bb, turboprop
from helpers import value_of

# Engineering tolerance for matching the manual's printed figures (see Decision 3).
TOL = 1e-3  # ±0.1% relative


def test_derived_quantities():
    inp = io520bb()
    assert calc.combined_weight(inp) == 579  # integers, pi-independent
    assert math.isclose(calc.takeoff_torque(inp), 554.3884, rel_tol=TOL)
    assert math.isclose(calc.max_cont_torque(inp), 556.7227, rel_tol=TOL)
    assert calc.torque_factor(inp) == 1.33
    xpp, ypp, zpp = calc.combined_cg(inp)
    assert math.isclose(xpp, 17.91, abs_tol=0.01)


def test_361_a1():
    # Approved correction (AC 23-19A): 23.361(c) applies the mean-torque factor to
    # the takeoff case too (1.33 for the 6-cyl IO-520-BB). The manual's printed p131
    # figure is the pre-Amdt-45 UNFACTORED value (554.3884, asserted below as the
    # mean torque); the corrected design torque is 1.33 x 554.3884 = 737.34 ft-lb.
    # Vertical loads are unchanged. See CLAUDE.md "Approved corrections to the source".
    r = calc.condition_361_a1(io520bb())
    assert math.isclose(value_of(r, "vertical_load_factor"), 2.85, abs_tol=1e-9)
    assert math.isclose(value_of(r, "fz_vertical"), 1650.15, rel_tol=TOL)
    assert math.isclose(value_of(r, "torque_factor"), 1.33, abs_tol=1e-9)
    assert math.isclose(value_of(r, "mean_takeoff_torque"), 554.3884, rel_tol=TOL)
    assert math.isclose(value_of(r, "mx_mount_torque"), -737.337, rel_tol=TOL)


def test_361_a2():
    r = calc.condition_361_a2(io520bb())
    assert math.isclose(value_of(r, "fz_vertical"), 2200.2, rel_tol=TOL)
    assert math.isclose(value_of(r, "torque_factor"), 1.33, abs_tol=1e-9)
    assert math.isclose(value_of(r, "max_continuous_torque"), 556.7227, rel_tol=TOL)
    assert math.isclose(value_of(r, "mx_mount_torque"), -740.4412, rel_tol=TOL)


def test_363():
    r = calc.condition_363(io520bb())
    assert math.isclose(value_of(r, "side_load_factor"), 1.33, abs_tol=1e-9)
    assert math.isclose(value_of(r, "fy_side"), 770.07, rel_tol=TOL)


def test_reciprocating_runs_three_conditions():
    assert len(run_all(io520bb())) == 3


def test_prop_inertia_matches_manual():
    # Manual hand calc: IProp = 50/32.174*(50.5/12)^2/3 = 9.174 slug-ft^2
    inp = turboprop()
    assert math.isclose(calc._prop_inertia(inp), 9.174, abs_tol=1e-2)


# --------------------------------------------------------------------------- #
# 23.361(b)(1) sudden stoppage -- formula-closure gate (CR-B-3).
#
# Twin-only condition: Appendix B is not bundled, so there is no printed figure
# to lock (CONVENTIONS.md §6 -- "no oracle" never means "no gate"). The gate is
# the formula ENGLOADS.BAS lines 850-926 evaluate, restated here from the
# rotor-by-rotor inputs rather than from the module's own summation, so a
# regression in the loop, in a rotor's sign, or in the Delta-t division fails.
# --------------------------------------------------------------------------- #

def test_361_b1_closes_on_the_angular_momentum_formula():
    """torque == I_prop*omega_prop/dt + SUM_i I_rotor(i)*omega_rotor(i)/dt.

    Independently re-derived from the fixture's own numbers (ENGLOADS.BAS 853-926,
    reference/FAR23Loads_Code.pdf p466). Rotor 1 spins counter-clockwise
    (max_rpm < 0), so its contribution *subtracts*: this pins the signed summation,
    not just its magnitude.
    """
    inp = turboprop()
    dt = inp.stop_time_s
    expected = calc._prop_inertia(inp) * calc._omega(inp.takeoff_rpm) / dt
    contributions = [calc._rotor_inertia(r) * calc._omega(r.max_rpm) / dt for r in inp.rotors]
    expected += sum(contributions)
    assert min(contributions) < 0 < max(contributions)  # the counter-rotating pair

    r = calc.condition_361_b1(inp)
    assert value_of(r, "time_to_stop") == dt
    assert math.isclose(value_of(r, "ixx_propeller"), calc._prop_inertia(inp), abs_tol=1e-9)
    # Reported torque is the negated total, floored (see the truncation test below).
    assert math.isclose(value_of(r, "mx_mount_torque"), -expected, abs_tol=1.0)
    assert math.isclose(expected, 6824.62, rel_tol=TOL)  # today's value, pinned


def test_361_b1_torque_is_floored_as_basic_int_did():
    """``INT(-TORQSUDSTOP)`` floors; Python's ``int()`` truncates toward zero.

    ENGLOADS.BAS line 944 prints ``INT(-TORQSUDSTOP)`` and the argument is negative
    by construction (reaction torque is reported negative, CONVENTIONS.md §5), so
    the two differ by exactly 1 ft-lb -- and ``int()`` was the non-conservative
    one. -6824.624... floors to -6825, truncates to -6824.
    """
    r = calc.condition_361_b1(turboprop())
    assert value_of(r, "mx_mount_torque") == -6825.0
    assert value_of(r, "mx_mount_torque") == basic_int(-6824.624095864674)
    assert int(-6824.624095864674) == -6824  # what the port used to report


def test_measured_prop_inertia_overrides_geometry():
    from dataclasses import replace
    inp = replace(turboprop(), prop_inertia=12.5)
    assert calc._prop_inertia(inp) == 12.5  # geometry (9.174) ignored


def test_measured_rotor_inertia_overrides_geometry():
    from dataclasses import replace
    base = turboprop()
    geom = calc._rotor_inertia(base.rotors[0])
    measured = replace(base.rotors[0], inertia=0.5)
    assert calc._rotor_inertia(measured) == 0.5
    assert not math.isclose(geom, 0.5)  # the disk approximation differs


def test_361_a3_applies_mean_torque_factor():
    # Approved correction (AC 23-19A): 23.361(c) applies the 1.25 turbopropeller
    # mean-torque factor to *all* of paragraph (a), so the malfunction torque is
    # 1.6 x 1.25 x mean takeoff torque, not 1.6 x mean alone. The manual /
    # ENGLOADS.BAS (TTP=1.6*ENGTORQ) encode the pre-Amdt-45 unfactored form:
    #   manual:    1.6 x 1970          = 3152 ft-lb
    #   corrected: 1.6 x 1.25 x 1970   = 3940 ft-lb
    # See CLAUDE.md "Approved corrections to the source".
    r = calc.condition_361_a3(turboprop())
    assert math.isclose(value_of(r, "torque_factor"), 1.25, abs_tol=1e-9)
    assert math.isclose(value_of(r, "malfunction_factor"), 1.6, abs_tol=1e-9)
    assert math.isclose(value_of(r, "mean_takeoff_torque"), 1970, abs_tol=1e-9)
    assert math.isclose(value_of(r, "mx_mount_torque"), -3940, rel_tol=TOL)
    assert math.isclose(value_of(r, "fz_vertical"), 450, abs_tol=1e-9)  # 1g x PPWT


def test_gyro_thrust_matches_manual():
    # Manual: THRUST = 1970 * 230.38 / 101.2 = 4484.7 lb
    r = calc.condition_371_b(turboprop())
    assert math.isclose(value_of(r, "fx_thrust"), 4484.7, abs_tol=1.0)


def test_turboprop_runs_six_conditions():
    assert len(run_all(turboprop())) == 6


# --------------------------------------------------------------------------- #
# Multi-engine layout (first-class; loads loop over every engine)
# --------------------------------------------------------------------------- #
def test_single_engine_run_matches_run_all():
    from sloads import EngineLayout, Project

    project = Project(name="single", engines=[io520bb()], engine_layout=EngineLayout.SINGLE_NOSE)
    mr = calc.run(project)
    ref = run_all(io520bb())
    # One engine: run(project) is byte-identical to run_all (no title prefixes).
    assert [c.title for c in mr.conditions] == [c.title for c in ref]
    assert len(mr.conditions) == 3


def test_twin_wing_loops_over_each_engine():
    from dataclasses import replace
    from sloads import EngineLayout, Project

    left = replace(io520bb(), engine_designation="LEFT", engine_cg=(22.0, -60.0, -10.0))
    right = replace(io520bb(), engine_designation="RIGHT", engine_cg=(22.0, 60.0, -10.0))
    project = Project(name="twin", engines=[left, right], engine_layout=EngineLayout.TWIN_WING)
    mr = calc.run(project)
    # Two reciprocating engines -> 2 x 3 conditions, each tagged by designation.
    assert len(mr.conditions) == 6
    assert mr.conditions[0].title.startswith("[LEFT]")
    assert mr.conditions[3].title.startswith("[RIGHT]")


def test_engine_layout_count_is_validated():
    from sloads import EngineLayout, Project

    raised = False
    try:
        Project(name="bad", engines=[io520bb()], engine_layout=EngineLayout.TWIN_WING)
    except ValueError:
        raised = True
    assert raised  # TWIN_WING needs 2 engines, got 1


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
