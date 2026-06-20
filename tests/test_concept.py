"""Concept-mode foundation (Step C0): the >12,500 lb / user-load-factor path.

Concept mode has no printed oracle (it extrapolates past the FAR23 calibration
band), so these checks are physics/identity rather than manual figures:

* ``WeightInput.direct_totals`` sums the itemized data base by kind (the
  direct-weight path that replaces WTESTIMA's GA regression for a heavy concept);
* the ``examples/concept_heavy.project.json`` fixture (MTOW 18,000 lb, user n)
  runs STRSPEED and WTESTIMA end-to-end without tripping a GA cap, and WTESTIMA
  flags itself as a sanity-only estimate.

The FAR23 identity invariant (concept reduces exactly to FAR23 on GA inputs) is
guarded by the unchanged Appendix-A oracle tests in test_structural_speeds.py /
test_weight_estimate.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import (  # noqa: E402
    MassItem,
    MassItemKind,
    Project,
    StructuralSpeedsInput,
    WeightInput,
    io,
)
from farloads.modules import structural_speeds as speeds_calc  # noqa: E402
from farloads.modules import weight_estimate as weight_calc  # noqa: E402

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "concept_heavy.project.json",
)


def test_direct_totals_sums_items_by_kind():
    w = WeightInput(items=[
        MassItem(name="structure", weight_lb=9000, kind=MassItemKind.EMPTY),
        MassItem(name="pilot", weight_lb=700, kind=MassItemKind.MINIMUM),
        MassItem(name="payload", weight_lb=8300, kind=MassItemKind.DISCRETIONARY),
    ])
    mtow, oew, useful = w.direct_totals()
    assert mtow == 18000
    assert oew == 9000
    assert useful == 9000


def test_direct_totals_empty_database():
    assert WeightInput(items=[]).direct_totals() == (0, 0, 0)


def test_fixture_is_concept_and_over_ga_limit():
    project = io.load_project(_EXAMPLE)
    assert project.is_concept
    mtow, _oew, _useful = project.weight.direct_totals()
    assert mtow > 12500  # exercises the band the GA caps were calibrated for


def test_concept_fixture_runs_end_to_end():
    project = io.load_project(_EXAMPLE)

    # STRSPEED: user load factors honoured verbatim, no GA cap.
    sp = speeds_calc.run(project)
    factors = sp.conditions[0]
    by_label = {v.label: v.value for v in factors.values}
    assert by_label["Limit positive load factor"] == 4.0
    assert by_label["Limit negative load factor"] == -2.0
    assert "concept" in factors.note.lower()

    # WTESTIMA still runs, but is flagged as a GA sanity estimate.
    we = weight_calc.run(project)
    assert "sanity" in we.conditions[0].note.lower()


def test_concept_round_trips_through_io():
    project = io.load_project(_EXAMPLE)
    rebuilt = io.project_from_dict(io.project_to_dict(project))
    assert rebuilt.is_concept
    assert rebuilt.speeds.chosen_n == 4.0
    assert rebuilt.speeds.chosen_nneg == -2.0


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
