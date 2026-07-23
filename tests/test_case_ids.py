"""Structured load-case IDs (Step D1): uniqueness, stability, and the accepted
wing / one-engine-out sequence-divergence gap.

No calc-math change -- ``case_ref`` is an added field, not a value change; the
existing Appendix A/B oracle tests (unchanged, still passing) are the
math-fidelity check for this step. This file checks the ID-assignment
properties the D1 design promises: every delivered case gets a stable id, no
two *different* physical cases share one, and re-running the same project
yields byte-identical ids.

Reference: docs/30_future/00_backlog.md Step D1; docs/30_future/
02_gui_workflow_plan.md D-1.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io, registry  # noqa: E402
from sloads.case_ids import (  # noqa: E402
    WING_BAND_SELECT,
    WING_BAND_STRUCTURAL,
    CaseIdAllocator,
)
from sloads.modules.select import build_critical  # noqa: E402
from sloads.modules.wing_inertia import build_wing_inertia  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_ALL_EXAMPLES = [
    os.path.join(_EXAMPLES, "ga6_normal.project.json"),
    os.path.join(_EXAMPLES, "concept_heavy.project.json"),
    os.path.join(_EXAMPLES, "cessna_210.project.json"),
    os.path.join(_EXAMPLES, "dhc8_dash8.project.json"),
]


def _case_refs(project):
    """Every (module, case_id, condition) triple a full run produces."""
    out = []
    for mr in registry.run_all_modules(project):
        for c in mr.conditions:
            if c.case_ref is not None:
                out.append((mr.module, c.case_ref.case_id, c.case_ref.condition))
    return out


def test_case_ids_present_across_all_example_projects():
    """Every bundled example produces at least one structured case id -- the
    minting sites are actually wired up, not silently inert."""
    for path in _ALL_EXAMPLES:
        project = io.load_project(path)
        refs = _case_refs(project)
        assert refs, f"no case_ref emitted for {path}"


def test_no_case_id_means_two_different_cases():
    """The real uniqueness invariant: the same ``case_id`` may legitimately
    appear more than once (a case propagated through several pipeline stages --
    e.g. SELECT's HT-01 reappearing on TAILDIST's chordwise result for the same
    case), but it must never label two *different* physical conditions."""
    for path in _ALL_EXAMPLES:
        project = io.load_project(path)
        by_id = {}
        for _module, case_id, condition in _case_refs(project):
            if case_id in by_id:
                assert by_id[case_id] == condition, (
                    f"{path}: case id {case_id} means both "
                    f"{by_id[case_id]!r} and {condition!r}"
                )
            else:
                by_id[case_id] = condition


def test_case_ids_stable_across_identical_runs():
    """Re-running the same project (fresh load, fresh compute) yields a
    byte-identical id set -- the fixed-enumeration-order decision (D-1)."""
    for path in _ALL_EXAMPLES:
        refs1 = sorted(_case_refs(io.load_project(path)))
        refs2 = sorted(_case_refs(io.load_project(path)))
        assert refs1 == refs2, path


def test_wing_gap_is_banded_not_colliding():
    """The accepted gap (docs/30_future/00_backlog.md Step D1): select_wing's own
    wing CriticalCondition list and WINGINER/NETLOADS's WingMassInput.cases list
    are two independent sequences that share the "wing" component/"W" prefix.
    They must not collide -- this test locks the banding that prevents it, so a
    future change that moves either sequence's start without updating the other
    fails loudly here instead of silently reintroducing the collision a smoke
    check first caught (select_wing's W-02 = PLAA vs. WINGINER's W-02 = TORS
    before the bands were split)."""
    project = io.load_project(os.path.join(_EXAMPLES, "ga6_normal.project.json"))

    critical = build_critical(project)
    select_wing_ids = [c.case_ref.case_id for c in critical.conditions
                       if c.component == "wing" and c.case_ref is not None]
    assert select_wing_ids, "select_wing produced no wing conditions to check"
    for cid in select_wing_ids:
        seq = int(cid.split("-")[1])
        assert seq >= WING_BAND_SELECT, f"select_wing id {cid} not in its own band"

    winginer_results = build_wing_inertia(project)
    winginer_ids = [r.case_ref.case_id for r in winginer_results if r.case_ref is not None]
    assert winginer_ids, "WINGINER produced no cases to check"
    for cid in winginer_ids:
        seq = int(cid.split("-")[1])
        assert WING_BAND_STRUCTURAL <= seq < WING_BAND_SELECT, (
            f"WINGINER id {cid} strayed into select_wing's band"
        )

    # The two sequences are disjoint by construction (no shared allocator state).
    assert not (set(select_wing_ids) & set(winginer_ids))


def test_allocator_is_a_pure_per_call_counter():
    """CaseIdAllocator has no shared/global state -- two independent instances
    produce the same sequence from the same starting point (determinism comes
    from each minting module's own fixed emission order, not shared state)."""
    a = CaseIdAllocator()
    b = CaseIdAllocator()
    ids_a = [a.next_id("wing") for _ in range(3)]
    ids_b = [b.next_id("wing") for _ in range(3)]
    assert ids_a == ids_b == ["W-01", "W-02", "W-03"]


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
