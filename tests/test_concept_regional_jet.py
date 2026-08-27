"""Full-airframe concept fixture (backlog Step P1-1): the regional-jet example.

Concept mode was only ever demonstrated for the wing (``concept_heavy`` defines a
wing surface only). This fixture, ``examples/concept_regional_jet.project.json``, is
a swept-wing, high-subsonic twin-turbofan regional jet (MTOW 33,000 lb, Part 25 /
``category="C"``) that drives *every* component path -- wing, body, tail and the
three control surfaces -- so the concept distributed-loads pipeline can be validated
end-to-end (its closure checks are Step P1-2).

No printed oracle exists above 12,500 lb, so these are runs-end-to-end / identity /
round-trip checks, not manual figures. This fixture is also the first to exercise
the swept ``AIRLOAD4`` branch through a project file (it caught the missing
``sweep_deg``/``design_mach`` round-trip in ``io.aero_*_dict``).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io
from sloads.modules import airloads as airloads_mod
from sloads.registry import run_all_modules

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "concept_regional_jet.project.json",
)

# The component modules that concept_heavy could NOT reach for lack of tail/body/
# control-surface inputs -- the whole point of this fixture.
_REQUIRED_COMPONENT_MODULES = {
    "airloads", "wing_inertia", "net_loads", "body_loads",
    "taildist", "aileron", "flap", "tab", "engine",
}


def test_fixture_is_concept_over_ga_limit():
    project = io.load_project(_EXAMPLE)
    assert project.is_concept
    # Part 25 maneuver load factors carried verbatim (no GA 23.337 cap).
    assert project.speeds.chosen_n == 2.5
    assert project.speeds.chosen_nneg == -1.0


def test_fixture_uses_the_mach_margin_dive_speed_route():
    """F25-2. This fixture is *the* demonstration of the 25.335(b) margin route.

    Before F25-2 its own chosen VD of 350 kt was silently overridden by the
    1.25*VC floor to 387.5 kt (MD 0.9423, margin +0.19 -- absurd for a transport),
    inflating every dive-speed case and driving MACHLIM's then-computed flutter
    clearance to a supersonic 1.13 (that quantity has since left the tool: #79).
    The route is opt-in, so the fixture must actually carry it.
    """
    from sloads import VdBasis
    from sloads.modules.structural_speeds import design_speed_values

    project = io.load_project(_EXAMPLE)
    assert project.speeds.vd_basis is VdBasis.MACH_MARGIN
    ds = design_speed_values(project, project.speeds)
    assert abs(ds.vd - 350.0) < 1e-6, "the fixture's own chosen VD must survive"
    assert ds.mach_margin > 0.07, "and it must clear the 0.07 M default on its own"
    assert abs(ds.vd_ratio_floor - 387.5) < 1e-6


def test_only_the_dive_line_moves_with_vd():
    """The containment claim behind the F25-2 re-baseline.

    Changing VD may move the D-line corner cases and nothing else. This pins the
    mechanism rather than the numbers: every ``*D`` envelope case flies at VD,
    and no ``*A``/``*C`` case does -- so a future VD change cannot quietly leak
    into the low-speed corners.
    """
    from sloads.modules.flight_envelope import design_inputs
    from sloads.registry import get

    project = io.load_project(_EXAMPLE)
    di = design_inputs(project)
    speeds_by_case = {}
    for cond in get("flight_envelope")(project).conditions:
        for lv in cond.values:
            if lv.key == "v_eas":
                speeds_by_case[cond.title] = lv.value

    assert speeds_by_case, "the flight envelope produced no cases"
    for title, v in speeds_by_case.items():
        tag = title.rsplit(":", 1)[-1].strip()
        if tag.endswith("D"):
            assert abs(v - di.vd) < 1e-6, f"{title} should fly at VD"
        elif tag.endswith("A") or tag.endswith("C"):
            assert abs(v - di.vd) > 1e-6, f"{title} must not be tied to VD"


def test_full_airframe_runs_end_to_end():
    """Every component module runs -- no missing-slice ValueError skips."""
    project = io.load_project(_EXAMPLE)
    ran = {r.module for r in run_all_modules(project)}
    missing = _REQUIRED_COMPONENT_MODULES - ran
    assert not missing, f"component modules skipped: {sorted(missing)}"


def test_airload4_swept_branch_selected():
    """The regional jet's sweep/Mach select the AIRLOAD4 branch (Ref 1 Ch 12)."""
    project = io.load_project(_EXAMPLE)
    wing = project.aero.by_name("wing")
    assert wing.sweep_deg > 15.0
    assert wing.design_mach > 0.4
    assert airloads_mod.use_airload4(wing)


def test_sweep_fields_round_trip_through_io():
    """Regression: ``sweep_deg``/``design_mach`` survive the io round-trip.

    They were added to ``AeroSurfaceInput`` in Step C7 but never wired into
    ``io.aero_*_dict``; no GA fixture set them, so the gap was invisible until this
    swept concept fixture. (Fixed alongside Step P1-1.)
    """
    project = io.load_project(_EXAMPLE)
    rebuilt = io.project_from_dict(io.project_to_dict(project))
    wing = rebuilt.aero.by_name("wing")
    assert wing.sweep_deg == project.aero.by_name("wing").sweep_deg
    assert wing.design_mach == project.aero.by_name("wing").design_mach


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
    sys.exit(1 if failed else 0)
