"""Concept-mode foundation (Step C0): the >12,500 lb / user-load-factor path.

Concept mode has no printed oracle (it extrapolates past the FAR23 calibration
band), so these checks are physics/identity rather than manual figures:

* ``WeightInput.database_totals`` sums the itemized data base by kind (the
  direct-weight path that replaces WTESTIMA's GA regression for a heavy concept);
* the ``examples/concept_heavy.project.json`` fixture (MTOW 18,000 lb, user n)
  runs STRSPEED and WTESTIMA end-to-end without tripping a GA cap, and WTESTIMA
  flags itself as a sanity-only estimate.

The FAR23 identity invariant (concept reduces exactly to FAR23 on GA inputs) is
guarded two ways: indirectly by the unchanged Appendix-A oracle tests in
test_structural_speeds.py / test_weight_estimate.py, and directly -- through the
concept branch itself -- by ``test_concept_reduces_to_far23_on_ga_inputs`` below
(Step P1-3), which flips ``ga6_normal`` to ``category="C"`` with the FAR23-computed
load factors and asserts the whole pipeline reproduces the FAR23 loads.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import (  # noqa: E402
    MassItem,
    MassItemKind,
    Project,
    WeightInput,
    io,
)
from sloads.modules import structural_speeds as speeds_calc  # noqa: E402
from sloads.modules import weight_estimate as weight_calc  # noqa: E402
from sloads.registry import run_all_modules  # noqa: E402

_EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
)
_EXAMPLE = os.path.join(_EXAMPLES_DIR, "concept_heavy.project.json")
_GA_EXAMPLE = os.path.join(_EXAMPLES_DIR, "ga6_normal.project.json")


def test_database_totals_sums_items_by_kind():
    w = WeightInput(items=[
        MassItem(name="structure", weight_lb=9000, kind=MassItemKind.EMPTY),
        MassItem(name="pilot", weight_lb=700, kind=MassItemKind.MINIMUM),
        MassItem(name="payload", weight_lb=8300, kind=MassItemKind.DISCRETIONARY),
    ])
    mtow, oew, useful = w.database_totals()
    assert mtow == 18000
    assert oew == 9000
    assert useful == 9000


def test_database_totals_empty_database():
    assert WeightInput(items=[]).database_totals() == (0, 0, 0)


def test_fixture_is_concept_and_over_ga_limit():
    project = io.load_project(_EXAMPLE)
    assert project.is_concept
    mtow, _oew, _useful = project.weight.database_totals()
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


# ---------------------------------------------------------------------------
# Step P1-3 -- concept reduces exactly to FAR23 on GA inputs (identity test).
#
# The ONLY numeric branch between concept and FAR23 is
# ``structural_speeds.maneuver_load_factors``: concept mode returns the user's
# chosen_n/chosen_nneg verbatim, FAR23 computes the 23.337 cap. Every other
# ``is_concept`` branch (configuration/flap/aileron/tab/taildist/landing/airloads/
# balloads/select/flight_envelope/weight_estimate/engine) only appends a note and
# changes no numbers. So feeding the FAR23-computed load factors back through the
# concept path must reproduce the whole pipeline bit-for-bit, differing only in the
# appended note text (which the sweep deliberately ignores).
# ---------------------------------------------------------------------------

def _design_load_factors(project: Project):
    """(n+, n-) that STRSPEED reports for ``project`` in its native category."""
    conditions = speeds_calc.design_speeds(project, project.speeds)
    by_label = {v.label: v.value for c in conditions for v in c.values}
    return (by_label["Limit positive load factor"],
            by_label["Limit negative load factor"])


def _as_concept(project: Project, n: float, nneg: float) -> Project:
    """Flip a project to concept category with explicit load factors."""
    project.speeds.category = "C"
    project.speeds.chosen_n = n
    project.speeds.chosen_nneg = nneg
    return project


def _assert_modules_identical(far, concept):
    """Assert two run_all_modules() results are numerically identical.

    Compares by module name -> condition (title, far_reference) -> LoadValue label,
    so registry ordering can't cause a false failure. Ignores ConditionResult.note
    (the concept note is the one permitted difference).
    """
    far_by_name = {r.module: r for r in far}
    con_by_name = {r.module: r for r in concept}
    assert far_by_name.keys() == con_by_name.keys(), (
        "different module sets ran: "
        f"far-only={far_by_name.keys() - con_by_name.keys()} "
        f"concept-only={con_by_name.keys() - far_by_name.keys()}"
    )

    for name, far_mod in far_by_name.items():
        con_mod = con_by_name[name]
        far_conds = {(c.title, c.far_reference): c for c in far_mod.conditions}
        con_conds = {(c.title, c.far_reference): c for c in con_mod.conditions}
        assert far_conds.keys() == con_conds.keys(), (
            f"module {name!r}: condition set differs")

        for key, far_cond in far_conds.items():
            con_cond = con_conds[key]
            assert far_cond.safety_factor == con_cond.safety_factor, (
                f"module {name!r} condition {key!r}: safety factor differs "
                f"({far_cond.safety_factor} vs {con_cond.safety_factor})")
            far_vals = {v.label: v for v in far_cond.values}
            con_vals = {v.label: v for v in con_cond.values}
            assert far_vals.keys() == con_vals.keys(), (
                f"module {name!r} condition {key!r}: value labels differ")
            for label, fv in far_vals.items():
                cv = con_vals[label]
                assert fv.units == cv.units, (
                    f"module {name!r} condition {key!r} value {label!r}: "
                    f"units differ ({fv.units!r} vs {cv.units!r})")
                # Exact equality, deliberately: this is an identity, not an
                # oracle comparison. Concept mode differs from FAR23 mode at
                # exactly one place -- `maneuver_load_factors` returns the
                # caller's (n, n-) instead of the 23.337 cap -- so feeding the
                # FAR23 caps back in must re-run the same arithmetic on the same
                # floats. Any difference at all, however small, means some other
                # branch also reads the category, and that is a finding to
                # investigate, not a rounding artefact to absorb (CR-B-2).
                assert fv.value == cv.value, (
                    f"module {name!r} condition {key!r} value {label!r}: "
                    f"{fv.value} != {cv.value} -- the concept branch must "
                    "reduce to FAR23 bit-for-bit; a non-zero difference means a "
                    "second category-dependent branch exists")


def test_concept_load_factors_match_far23_caps():
    """STRSPEED's load-factor tuple is identical FAR23 vs concept (the crux).

    This is the single numeric divergence point (``maneuver_load_factors``): the
    FAR23 Normal cap for ga6_normal is n=3.8, nneg=-0.4*3.8=-1.52 (14 CFR 23.337);
    concept mode fed those exact values must echo them.
    """
    n, nneg = _design_load_factors(io.load_project(_GA_EXAMPLE))
    assert math.isclose(n, 3.8, rel_tol=1e-3)      # 23.337(a) Normal cap
    assert math.isclose(nneg, -1.52, rel_tol=1e-3)  # 23.337(b): -0.4 * 3.8

    concept = _as_concept(io.load_project(_GA_EXAMPLE), n, nneg)
    assert concept.is_concept
    cn, cnneg = _design_load_factors(concept)
    assert cn == n and cnneg == nneg


def test_concept_reduces_to_far23_on_ga_inputs():
    """The full pipeline reproduces FAR23 loads when a GA project runs as concept.

    Guards the C-1 invariant *through the concept branch itself* (Step P1-3): the
    only difference permitted is appended note text.
    """
    far_project = io.load_project(_GA_EXAMPLE)
    assert not far_project.is_concept
    far_results = run_all_modules(far_project)
    assert far_results, "baseline GA run produced no modules"

    n, nneg = _design_load_factors(io.load_project(_GA_EXAMPLE))
    concept_project = _as_concept(io.load_project(_GA_EXAMPLE), n, nneg)
    assert concept_project.is_concept
    concept_results = run_all_modules(concept_project)

    _assert_modules_identical(far_results, concept_results)


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
