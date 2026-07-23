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

from sloads import io  # noqa: E402
from sloads.modules import airloads as airloads_mod  # noqa: E402
from sloads.registry import run_all_modules  # noqa: E402

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
