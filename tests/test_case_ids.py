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
    ASSEMBLED_DECK,
    COMPONENT_DECK,
    HANDS,
    NO_LOAD_ID,
    SUBCASE_BLOCK,
    VTAIL_BAND_ONENGOUT,
    VTAIL_BAND_TAB,
    WING_BAND_EXTRA,
    WING_SLOTS,
    CaseIdAllocator,
    balanced_subcase_id,
    case_label,
    deck_load_id,
    subcase_id,
    unhanded_case_id,
    wing_case_id,
)
from sloads.export.sbeam_bridge import LOAD_ID_COLUMN  # noqa: E402
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


def test_balanced_subcase_id_gives_each_hand_its_own_block():
    """**D-R7**: the assembled deck's subcase id is minted from the case id, and
    a handed twin differs from its opposite only in the block it lands in.

    The suffix cannot ride on the number -- a ``SUBCASE`` id is an integer -- so
    the hand is the thousands digit and the rest is the case's own
    :func:`subcase_id`, readable straight off a solver result.
    """
    assert balanced_subcase_id("W-01") == 5101
    assert balanced_subcase_id("W-05R") == 7105
    assert balanced_subcase_id("W-05L") == 8105
    assert balanced_subcase_id("VT-01R") == 7301
    assert balanced_subcase_id("VT-04L") == 8304
    # Blocks are wide enough for every case id, and no two ids share a number.
    ids = [f"{p}-{n:02d}{h}" for p in SUBCASE_BLOCK for n in (1, 99)
           for h in ("", "R", "L")]
    assert len({balanced_subcase_id(i) for i in ids}) == len(ids)
    with pytest.raises(ValueError):
        balanced_subcase_id("not-a-case")


def test_balanced_subcase_ids_survive_an_edit_to_the_case_set():
    """The instability the positional scheme had, stated as the property that
    replaced it: drop a condition and the survivors keep their numbers.

    This is what a consumer of the flagship deck relies on -- ``SUBCASE 7105``
    is starboard ACRL in every run, not "whatever was seventh this time".
    """
    full = ["W-01", "W-02", "W-05R", "W-05L", "W-06", "VT-01R", "VT-01L"]
    before = {cid: balanced_subcase_id(cid) for cid in full}
    after = {cid: balanced_subcase_id(cid) for cid in full if cid != "W-02"}
    assert all(after[cid] == before[cid] for cid in after)


# --------------------------------------------------------------------------- #
# The deliverables' deck-number columns (design note 17)
# --------------------------------------------------------------------------- #
# `deck_load_id` is the single owner of "which minter applies to this case, in
# this deck family". These are its drift guards (CLAUDE.md rule 3): the number a
# document prints is checked against the number the deck writers actually emit,
# parsed from the deck text itself, so the two cannot drift apart silently.
_LINKAGE_EXAMPLE = "ga6_normal.project.json"


def _linkage_artifacts(example=_LINKAGE_EXAMPLE):
    """Every deck channel plus the case index for ``example``, from one run.

    ``tests/imperial_baseline.py`` already assembles exactly this set (and is the
    digest baseline), so the gate reads the same artifacts the frozen digests
    cover rather than building a second, possibly divergent, set.
    """
    import imperial_baseline as baseline

    return baseline.artifacts(example)


def _index_rows(artifacts):
    """The case index parsed back out of its CSV text: ``{case_id: row}``."""
    import csv as _csv
    import io as _io

    text = artifacts["case_index"]
    body = "\n".join(ln for ln in text.splitlines() if not ln.startswith("$"))
    return {r["ID"]: r for r in _csv.DictReader(_io.StringIO(body))}


def _hands_by_case_id(example):
    """``{case_id: hand}`` for the assembled cases of ``example``.

    The assembled deck's numbering is a function of the case id **and its hand**
    (G-8), and for the 23.485 side family the id does not carry the hand -- so a
    gate that wants to re-derive a SUBCASE number has to be told it, exactly as
    the deck writer is.
    """
    from sloads.modules.balance import build_balanced_cases

    project = io.load_project(os.path.join(_EXAMPLES, example))
    return {c.case_ref.case_id: c.hand
            for c in build_balanced_cases(project) if c.case_ref}


def _pairs_from_decks(artifacts):
    """``{case_id: subcase_int}`` per deck family, read from the decks' own text.

    Card-only channels state the pairing in their ``$`` subcase-map block
    (``$ SUBCASE 103 = W-03 -- PHAA``); the stick and assembled decks state it as
    a ``SUBCASE n`` / ``LABEL = id`` pair in the case control section. Both are
    parsed, so every deck family this project writes is covered.
    """
    import re

    component: dict = {}
    assembled: dict = {}
    for channel, text in artifacts.items():
        if not channel.startswith("sbeam/"):
            continue
        into = assembled if channel.endswith("balanced_deck") else component
        for sid, case_id in re.findall(r"^\$ SUBCASE (\d+) = (\S+) --", text, re.M):
            if case_id != "(no":          # a result with no CaseRef: no identity
                into[case_id] = int(sid)
        sid = None
        for line in text.splitlines():
            m = re.match(r"^SUBCASE (\d+)\s*$", line)
            if m:
                sid = int(m.group(1))
                continue
            m = re.match(r"^\s*LABEL = (\S+)\s*$", line)
            if m and sid is not None:
                into[m.group(1)] = sid
                sid = None
    return component, assembled


def test_the_index_quotes_the_decks_own_numbers():
    """Each LOAD column is the integer that deck family actually emitted.

    The gate the linkage rests on: a reader who joins ``SUBCASE 7105`` from a
    solver result to the case index must land on the case that produced it. The
    numbers are compared against the deck **text**, not against a second call to
    the minter, so a writer that stopped using ``deck_load_id`` would fail here.

    The minter is asked with the case's **hand**, not with its id alone (decision
    G-8). For every family but one the two are the same question, because the
    hand is a suffix on the id; the 23.485 side pair is the exception and is the
    reason the parameter exists -- ``LG-19`` (port) and ``LG-20`` (starboard) are
    LANDLOAD's own ids and carry no suffix, so an id-only call reads both as
    symmetric and returns a 5000-block number the deck does not contain.
    """
    artifacts = _linkage_artifacts()
    rows = _index_rows(artifacts)
    component, assembled = _pairs_from_decks(artifacts)
    hands = _hands_by_case_id(_LINKAGE_EXAMPLE)
    assert component and assembled, sorted(artifacts)

    for family, pairs in ((COMPONENT_DECK, component), (ASSEMBLED_DECK, assembled)):
        column = LOAD_ID_COLUMN[family]
        for case_id, sid in pairs.items():
            assert case_id in rows, (family, case_id)
            assert rows[case_id][column] == str(sid), (family, case_id, sid)
            assert deck_load_id(case_id, family,
                                hands.get(case_id, "")) == str(sid), (family, case_id)


def test_a_case_in_the_index_always_carries_at_least_one_deck_number():
    """No silent blank: a row with neither column filled would be a case the
    deliverable names and no deck carries, which is a defect, not a display gap."""
    for example in ("ga6_normal.project.json", "concept_regional_jet.project.json"):
        rows = _index_rows(_linkage_artifacts(example))
        assert rows
        for case_id, row in rows.items():
            filled = [row[LOAD_ID_COLUMN[f]] for f in (COMPONENT_DECK, ASSEMBLED_DECK)]
            assert any(filled), (example, case_id, row)


def test_a_handed_case_is_numbered_in_the_assembled_deck_only():
    """Handed twins exist only in the assembled deck (D-R7), so the component
    column is blank for them -- and blank *because* they are not in that deck,
    not because the number was unavailable: their unhanded id still has one."""
    rows = _index_rows(_linkage_artifacts())
    handed = [cid for cid in rows if cid[-1:] in HANDS]
    assert handed, sorted(rows)
    for case_id in handed:
        assert rows[case_id][LOAD_ID_COLUMN[COMPONENT_DECK]] == ""
        assert rows[case_id][LOAD_ID_COLUMN[ASSEMBLED_DECK]] == str(
            balanced_subcase_id(case_id))
        assert deck_load_id(case_id, COMPONENT_DECK) == ""
        assert deck_load_id(unhanded_case_id(case_id), COMPONENT_DECK) != ""


def test_the_report_case_index_states_the_same_pairs_as_the_csv():
    """One case identity, two renderings: the report's Case index table and the
    CSV beside it must agree cell for cell on ID and both LOAD columns, or a
    reader joining through the document lands somewhere else than one joining
    through the file."""
    from sloads.report.content import build_report

    path = os.path.join(_EXAMPLES, _LINKAGE_EXAMPLE)
    project = io.load_project(path)
    doc = build_report(project)
    tables = [t for section in doc.sections for t in section.tables
              if t.title == "Case index"]
    assert len(tables) == 1, [t.title for section in doc.sections for t in section.tables]
    table = tables[0]

    csv_rows = _index_rows(_linkage_artifacts())
    cols = {name: i for i, name in enumerate(table.columns)}
    assert [r[cols["ID"]] for r in table.rows] == list(csv_rows)
    for row in table.rows:
        csv_row = csv_rows[row[cols["ID"]]]
        for header, family in (("LOAD (comp.)", COMPONENT_DECK),
                               ("LOAD (asm.)", ASSEMBLED_DECK)):
            assert row[cols[header]] == (csv_row[LOAD_ID_COLUMN[family]] or NO_LOAD_ID)


def test_the_index_row_states_the_condition_its_cards_were_computed_at():
    """User decision 2026-08-13. ``atr42_100`` enters ``PHAA`` at 170 kt while
    SELECT's ``PHAA`` V-n point is 185.85 kt, and both deliverables share one
    ``case_id`` (M4-2 decision 1). The index is what a consumer joins
    ``SUBCASE 101`` to, so it states the condition the **cards** were built at --
    which is the entered case's, since that is what ``net_loads`` computed from.

    The mechanism is caller ordering (deck-exported results before SELECT's
    conditions, first-seen wins), so this also guards the ordering in
    ``imperial_baseline``, the Export page and the report against a well-meaning
    tidy-up that puts the module results back in front.
    """
    from sloads.modules.wing_inertia import resolve_wing_cases

    project = io.load_project(os.path.join(_EXAMPLES, "atr42_100.project.json"))
    entered = {c.name: c for c in resolve_wing_cases(project, project.wing_mass)}
    rows = _index_rows(_linkage_artifacts("atr42_100.project.json"))

    checked = 0
    for name, case in entered.items():
        if case.v_eas_kt is None:
            continue
        row = rows.get(wing_case_id(name))
        if row is None:                      # a condition this project does not export
            continue
        assert float(row["Speed (kt)"]) == pytest.approx(case.v_eas_kt, rel=1e-9), (
            f"{name}: index says {row['Speed (kt)']} kt, loads computed at {case.v_eas_kt}")
        checked += 1
    assert checked, "no entered wing case reached the index -- the gate checked nothing"


def test_deck_load_id_never_raises_on_a_case_id_it_cannot_map():
    """A reference table with a blank cell beats a report that failed to build --
    but the family itself is a programming error and does raise."""
    assert deck_load_id("not-a-case") == ""
    assert deck_load_id("not-a-case", ASSEMBLED_DECK) == ""
    assert deck_load_id("W-05R", COMPONENT_DECK) == ""
    assert deck_load_id("W-05R", ASSEMBLED_DECK) == "7105"
    assert deck_load_id("W-05") == "105"
    with pytest.raises(ValueError):
        deck_load_id("W-05", "wing_deck")


def test_the_case_label_states_id_load_and_condition():
    """The one formatter every GUI page uses: identity a reader can act on."""
    from sloads.models import CaseRef

    ref = CaseRef(case_id="W-03", component="wing", condition="PHAA",
                  far_reference="23.333(b)")
    assert case_label(ref) == "W-03 · LOAD 103 · PHAA · FAR 23.333(b)"
    assert case_label(ref, ASSEMBLED_DECK).startswith("W-03 · LOAD 5103 ·")
    assert "PMAA" in case_label(ref, condition="PMAA")
    # A case with no number in the family it is quoted in says so.
    handed = CaseRef(case_id="W-05R", component="wing", condition="ACRL")
    assert case_label(handed) == f"W-05R · LOAD {NO_LOAD_ID} · ACRL"


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
