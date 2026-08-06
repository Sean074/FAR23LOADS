"""Structured load-case IDs (Step D1; unified at M4-2): uniqueness, stability,
one ID per physical condition, and the deck subcase map.

No calc-math change -- ``case_ref`` is an added field, not a value change; the
existing Appendix A/B oracle tests (unchanged, still passing) are the
math-fidelity check. This file checks the ID-assignment properties the design
promises: every delivered case gets a stable id, no two *different* physical
cases share one, the same physical condition gets the *same* id from every
module that delivers it, and re-running the same project yields byte-identical
ids.

Reference: docs/30_future/00_backlog.md M4-2 (decisions 1/4/5/8); docs/40_history/
05_phase_d_gui_workflow_plan.md D-1.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io, registry  # noqa: E402
from sloads.case_ids import (  # noqa: E402
    VTAIL_BAND_ONENGOUT,
    VTAIL_BAND_TAB,
    WING_BAND_EXTRA,
    WING_SLOTS,
    CaseIdAllocator,
    subcase_id,
    wing_case_id,
)
from sloads.modules.one_engine_out import run as run_one_engine_out  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402
from sloads.modules.wing_inertia import build_wing_inertia  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_ALL_EXAMPLES = [
    os.path.join(_EXAMPLES, "ga6_normal.project.json"),
    os.path.join(_EXAMPLES, "concept_heavy.project.json"),
    os.path.join(_EXAMPLES, "cessna_210.project.json"),
    os.path.join(_EXAMPLES, "dhc8_dash8.project.json"),
]


def _twin_with_one_engine_out():
    """The GA6 example turned into a synthetic twin so ONENGOUT has a failed
    engine -- the same closure fixture ``tests/test_one_engine_out.py`` uses (no
    bundled example carries both a v-tail slice and a failed engine)."""
    from dataclasses import replace

    from sloads.models import EngineLayout, MassCase, MassResult, OneEngineOutInput

    p = io.load_project(os.path.join(_EXAMPLES, "ga6_normal.project.json"))
    e = p.engines[0]
    p.engines = [replace(e, engine_designation="LEFT", engine_cg=(22.0, -60.0, -10.0)),
                 replace(e, engine_designation="RIGHT", engine_cg=(22.0, 60.0, -10.0))]
    p.engine_layout = EngineLayout.TWIN_WING
    p.vtail_loads.xv50 = p.vtail_loads.xv25 + 12.0
    p.mass = MassResult(cases=[MassCase(name="gross", weight_lb=3400, cg_x=110.0, izz=3.0e7)])
    p.one_engine_out = OneEngineOutInput(
        thrust_decay_time_s=0.5, windmill_drag_time_s=1.5,
        rudder_travel_time_s=0.3, time_step_s=0.05)
    return p


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


def test_the_same_wing_condition_has_one_id_everywhere():
    """M4-2 decision 1/4: SELECT's wing ``CriticalCondition`` and the
    WINGINER/NETLOADS distribution derived from it are two deliverables of **one**
    case, so they carry the identical id -- and that id is the condition's fixed
    ``WING_SLOTS`` slot, not its position in either list.

    Before M4-2 these were two banded sequences (``W-01..`` and ``W-40..``): the
    same physical PHAA condition appeared twice in the exported case index under
    two ids, with two independently-entered sets of Nz/Nx that could disagree."""
    project = io.load_project(os.path.join(_EXAMPLES, "ga6_normal.project.json"))

    critical = build_critical(project)
    select_by_label = {c.label: c.case_ref.case_id for c in critical.conditions
                       if c.component == "wing" and c.case_ref is not None}
    assert select_by_label, "select_wing produced no wing conditions to check"
    for label, cid in select_by_label.items():
        assert cid == wing_case_id(label), f"{label} should hold its fixed slot"

    project.envelope = build_envelope(project)
    project.envelope.critical = critical
    winginer = build_wing_inertia(project)
    assert winginer, "WINGINER produced no cases to check"
    for r in winginer:
        assert r.case_ref is not None
        # ga6's hand-authored cases are all SELECT conditions -> the same id.
        assert r.case_ref.case_id == select_by_label[r.case], (
            f"WINGINER's {r.case} took a different id from SELECT's")


def test_a_missing_pick_leaves_a_gap_rather_than_renumbering():
    """M4-2 decision 4: the wing seq belongs to the condition. A case list that
    omits PLAA/PMAA/NMAA still puts TORS at its own slot -- persisted
    ``selected_case_ids`` and already-exported decks reference these strings, so
    they may not float with list position."""
    project = io.load_project(os.path.join(_EXAMPLES, "ga6_normal.project.json"))
    ids = {r.case: r.case_ref.case_id for r in build_wing_inertia(project)}
    # ga6 enters PHAA, TORS, ACRL -- positions 0, 1, 2 but slots 1, 6, 5.
    assert ids == {"PHAA": "W-01", "TORS": "W-06", "ACRL": "W-05"}


def test_one_engine_out_does_not_collide_with_select_vtail():
    """M4-2 decision 5: ONENGOUT's 23.367 dynamic case is a different case object
    from SELECT's v-tail picks, so it mints from its own band. Before M4-2 both
    started at ``VT-01`` -- the same id for two different physical conditions."""
    project = _twin_with_one_engine_out()
    select_vtail_ids = {c.case_ref.case_id for c in build_critical(project).conditions
                        if c.component == "vtail" and c.case_ref is not None}
    oeo_ids = {c.case_ref.case_id for c in run_one_engine_out(project).conditions
               if c.case_ref is not None}
    assert oeo_ids, "ONENGOUT produced no cases to check"
    assert not (select_vtail_ids & oeo_ids)
    for cid in oeo_ids:
        seq = int(cid.split("-")[1])
        assert VTAIL_BAND_ONENGOUT <= seq < VTAIL_BAND_TAB, f"{cid} outside its band"


def test_subcase_id_is_a_stable_reversible_map():
    """M4-2 decision 8: the deck ``SUBCASE``/``SID`` integer is a pure function of
    the case id, so a filtered export cannot renumber the subcases that survive,
    and the per-component blocks stay disjoint in an assembled deck."""
    assert subcase_id("W-01") == 101
    assert subcase_id("W-06") == 106
    assert subcase_id("HT-02") == 202
    assert subcase_id("VT-31") == 331
    assert subcase_id("F-04") == 404
    assert subcase_id("LG-05") == 605
    # Distinct ids never share a subcase number, across every band in use.
    ids = ([wing_case_id(lbl) for lbl in WING_SLOTS]
           + [f"W-{WING_BAND_EXTRA:02d}", "W-50", "W-70", "HT-01", "HT-50",
              "VT-01", f"VT-{VTAIL_BAND_ONENGOUT:02d}", "VT-50", "F-01", "EM-01", "LG-01"])
    assert len({subcase_id(i) for i in ids}) == len(ids)
    with pytest.raises(ValueError):
        subcase_id("not-a-case")


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
