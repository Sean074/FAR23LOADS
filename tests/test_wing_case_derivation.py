"""Deriving the wing structural cases from SELECT (Step M4-2, decisions 2 and 7).

``WingMassInput.cases`` used to be a hand-authored second entry of conditions
SELECT had already searched the V-n matrix for. M4-2 makes SELECT the authority:
an empty ``cases`` list derives from ``envelope.critical``.

**The gate (decision 7).** There is no printed oracle for the derivation, so the
benchmark-first requirement is met by a *closure* check instead: derive
``ga6_normal``'s wing cases from its own envelope and compare them against the
hand-typed values in the fixture, which are the Appendix A worked example's
printed figures (Ref 1 p217-221). Derivation never fires for ga6 in normal use
(its ``cases`` list is non-empty, so the Appendix A oracles are untouched by
construction) -- this test exists to check that the two routes *agree*, i.e. that
turning derivation on for a project would not quietly change the loads.

What it locks, and one thing it found
-------------------------------------
Nz and Nx agree closely for every shared condition. The air-load CL/V agree for
the balanced picks (PHAA, TORS). They do **not** agree for ACRL: SELECT's
23.349(a)(2) pick lands on a point whose own CL is ~1.30 at 117.4 kt, while the
worked example enters CL 1.55 at 116 kt for the same condition -- so a derived
ACRL case would carry a materially different air load. That divergence is
recorded as an open defect ("derived ACRL air-load point", docs/30_future/
00_backlog.md) rather than papered over with a loose tolerance here; the
hand-entered route is unaffected and remains what every shipped example uses.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.models import WingMassInput  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.net_loads import _air_cl_v  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402
from sloads.modules.wing_inertia import (  # noqa: E402
    _resolve_case,
    resolve_wing_cases,
    wing_case_ref,
)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")

# Tolerances the derivation is held to, per quantity. Nz is the load factor
# itself and must land on the same V-n point; Nx = -DX/W is a small difference of
# larger numbers and is allowed more room; V is the point's own speed.
_NZ_TOL = 5e-3      # 0.5%
_NX_TOL = 5e-2      # 5%
_V_TOL = 1.5e-2     # 1.5%

#: Conditions whose air-load CL/V the two routes agree on (see the module
#: docstring for ACRL, the one that does not).
_AIR_LOAD_AGREES = ("PHAA", "TORS")


def _selected_project():
    """ga6 with its envelope and SELECT critical-load set computed and persisted."""
    project = io.load_project(_GA)
    project.envelope = build_envelope(project)
    project.envelope.critical = build_critical(project)
    return project


def test_an_empty_case_list_derives_from_select():
    """Decision 2: no cases entered -> SELECT's wing conditions, by name."""
    project = _selected_project()
    derived = resolve_wing_cases(project, WingMassInput())
    assert derived, "SELECT produced no wing conditions to derive from"
    names = [c.name for c in derived]
    assert names == [c.label for c in project.envelope.critical.conditions
                     if c.component == "wing"]
    # Every derived case references a real V-n point, which is what lets
    # _resolve_case fill Nz/Nx and _air_cl_v fill the air-load condition.
    for c in derived:
        assert c.case is not None
        assert any(p.case == c.case for p in project.envelope.vn)


def test_explicit_cases_always_win():
    """Decision 2: a non-empty list is returned untouched, so every existing
    project -- and every Appendix A oracle -- takes the path it always did."""
    project = _selected_project()
    assert resolve_wing_cases(project, project.wing_mass) == project.wing_mass.cases


def test_derived_load_factors_match_the_worked_example():
    """Decision 7's closure gate: the derived Nz/Nx reproduce the hand-typed
    Appendix A figures for every condition the fixture and SELECT share."""
    project = _selected_project()
    hand = {c.name: c for c in project.wing_mass.cases}
    derived = [c for c in resolve_wing_cases(project, WingMassInput()) if c.name in hand]
    assert {c.name for c in derived} == set(hand), "fixture and SELECT name different conditions"

    for case in derived:
        got = _resolve_case(project, case)
        want = _resolve_case(project, hand[case.name])
        assert math.isclose(got.nz, want.nz, rel_tol=_NZ_TOL), f"{case.name} Nz {got.nz} vs {want.nz}"
        assert math.isclose(got.nx, want.nx, rel_tol=_NX_TOL), f"{case.name} Nx {got.nx} vs {want.nx}"


def test_derived_air_load_matches_for_the_balanced_conditions():
    """The air-load half of the same gate, for the conditions where the two
    routes genuinely name the same point (see the module docstring for ACRL)."""
    project = _selected_project()
    hand = {c.name: c for c in project.wing_mass.cases}
    for case in resolve_wing_cases(project, WingMassInput()):
        if case.name not in _AIR_LOAD_AGREES or case.name not in hand:
            continue
        cl, v = _air_cl_v(project, case)
        cl_want, v_want = _air_cl_v(project, hand[case.name])
        assert math.isclose(cl, cl_want, rel_tol=1e-2), f"{case.name} CL {cl} vs {cl_want}"
        assert math.isclose(v, v_want, rel_tol=_V_TOL), f"{case.name} V {v} vs {v_want}"


def test_the_acrl_divergence_is_the_documented_one():
    """Pin the divergence so it cannot drift silently: the derived ACRL air load
    differs from the worked example's by more than the balanced conditions' 1%.

    **Decided 2026-08-18 (D-29, #13):** SELECT's own 23.349(a)(2) pick is what the
    derived case names, and the ~19 % difference against the worked example's
    entered point (CL 1.55 at 116 kt vs CL ~1.30 at 117.4 kt) is accepted and
    stated rather than reconciled -- there is no printed oracle for the derived
    route, and every shipped fixture enters its cases explicitly, so no oracle or
    deliverable is affected. The consequence this pin guards: the derived route is
    a *first pass*, and an ACRL case used for sizing is entered, never derived
    (a derived one also carries ``unbal_moment = 0``, AILERON Ch 13 being where
    the rolling moment comes from). So this stays an inequality by decision. If it
    ever starts failing because the two agree, that is new information about the
    derived route -- reopen D-29 rather than quietly making it an equality."""
    project = _selected_project()
    hand = {c.name: c for c in project.wing_mass.cases}
    acrl = next((c for c in resolve_wing_cases(project, WingMassInput()) if c.name == "ACRL"), None)
    assert acrl is not None and "ACRL" in hand
    cl, _ = _air_cl_v(project, acrl)
    cl_want, _ = _air_cl_v(project, hand["ACRL"])
    assert not math.isclose(cl, cl_want, rel_tol=1e-2), (
        "derived and hand-entered ACRL CL now agree -- close the backlog defect "
        "and turn this into an equality assertion")


# --------------------------------------------------------------------------- #
# The row states the condition its numbers were computed at (user decision
# 2026-08-13, backlog priority 1)
# --------------------------------------------------------------------------- #
def _atr42_project():
    """ATR-42 with a persisted envelope + critical set -- the fixture whose entered
    wing conditions genuinely differ from SELECT's V-n picks."""
    project = io.load_project(os.path.join(_EXAMPLES, "atr42_100.project.json"))
    project.envelope = build_envelope(project)
    project.envelope.critical = build_critical(project)
    return project


def test_every_wing_case_row_names_the_speed_its_loads_were_computed_at():
    """The gate for the decision: for every entered case on every fixture, the
    ``CaseRef`` speed is the speed ``net_loads`` built the air load from. Before
    this, a case SELECT had already named kept SELECT's V-n speed instead."""
    for name in sorted(f for f in os.listdir(_EXAMPLES) if f.endswith(".project.json")):
        project = io.load_project(os.path.join(_EXAMPLES, name))
        if project.wing_mass is None or not project.wing_mass.cases:
            continue
        if project.flight_loads is None:
            continue
        project.envelope = build_envelope(project)
        project.envelope.critical = build_critical(project)
        cases = resolve_wing_cases(project, project.wing_mass)
        for i, case in enumerate(cases):
            _, v = _air_cl_v(project, case)
            ref = wing_case_ref(project, i, case)
            assert ref.speed_kt is not None and math.isclose(ref.speed_kt, v, rel_tol=1e-12), (
                f"{name} {case.name}: row states {ref.speed_kt} kt, loads computed at {v} kt")


def test_the_case_id_stays_selects_when_the_speed_is_the_cases_own():
    """The other half of the decision: only the flight-condition fields move.
    ``case_id`` remains SELECT's (M4-2 decision 1 -- one ID per physical
    condition, which the case-index dedupe assumes), and CG / altitude / FAR stay
    SELECT's too, since the case states none of them."""
    project = _atr42_project()
    select_refs = {c.label: c.case_ref for c in project.envelope.critical.conditions
                   if c.component == "wing" and c.case_ref is not None}
    cases = resolve_wing_cases(project, project.wing_mass)
    diverged = 0
    for i, case in enumerate(cases):
        want = select_refs.get(case.name)
        if want is None:
            continue
        ref = wing_case_ref(project, i, case)
        assert ref.case_id == want.case_id, case.name
        assert (ref.cg, ref.altitude_ft, ref.far_reference) == (
            want.cg, want.altitude_ft, want.far_reference), case.name
        if want.speed_kt is not None and case.v_eas_kt is not None \
                and not math.isclose(ref.speed_kt, want.speed_kt, rel_tol=1e-9):
            diverged += 1
        # SELECT's own CaseRef is never mutated -- the wing row takes a copy.
        assert want.speed_kt == select_refs[case.name].speed_kt
    assert diverged, (
        "atr42_100 no longer enters a wing condition at a different speed from "
        "SELECT's V-n pick -- this fixture is the reason the decision exists")


def test_the_atr42_phaa_divergence_is_pinned():
    """The measured instance behind the decision: the fixture enters PHAA at
    170 kt, SELECT's PHAA point is 185.36 kt. The row now reads 170.

    SELECT's pick moved from 185.85 kt with Pri 5 / D-26: PHAA is flown at
    ``CGmid``, whose station and waterline are now its loading's own rather than
    an unreachable corner point, so the balanced V-n point behind it moved with
    them. **And back to 185.36 kt with D-27 (2026-08-17):** the flight cases are
    the WTENV limit points now, PHAA is flown at ``fwd gross`` (MTOW at the
    forward-gross limit), and the balanced point moved with the case once more.
    The divergence the decision exists for is unchanged in kind and in sign --
    the fixture still enters a speed SELECT did not pick.
    """
    project = _atr42_project()
    cases = resolve_wing_cases(project, project.wing_mass)
    phaa = next(((i, c) for i, c in enumerate(cases) if c.name == "PHAA"), None)
    assert phaa is not None, "atr42_100 no longer enters a PHAA wing case"
    i, case = phaa
    select_ref = next(c.case_ref for c in project.envelope.critical.conditions
                      if c.component == "wing" and c.label == "PHAA")
    assert math.isclose(case.v_eas_kt, 170.0, rel_tol=1e-9)
    assert math.isclose(select_ref.speed_kt, 185.36, rel_tol=1e-3), select_ref.speed_kt
    assert math.isclose(wing_case_ref(project, i, case).speed_kt, 170.0, rel_tol=1e-9)


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
