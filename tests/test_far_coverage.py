"""The FAR 23 Subpart C coverage matrix (Step G8.4).

This is the section of the summary report that tells a reviewer what is
**missing**, so its failure mode is silence: a regulation that quietly falls out
of the table, or a real gap classified as something harmless. The tests below
pin exactly that.

Reference for the static table: `docs/10_standard/PROGRAM_SPEC.md` (per-module
FAR conditions) cross-read with the FAA User's Guide Table 2.2.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.registry import run_all_modules  # noqa: E402
from sloads.report.coverage import (  # noqa: E402
    COVERED,
    FAR23_SUBPART_C,
    NOT_ANALYSED,
    NOT_APPLICABLE,
    OUT_OF_SCOPE,
    coverage_matrix,
    coverage_summary,
)
import sloads.modules  # noqa: E402,F401  (module registration)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _run(path):
    project = io.load_project(path)
    refs = [c.far_reference for mr in run_all_modules(project) for c in mr.conditions]
    return project, refs, coverage_matrix(project, refs)


def test_every_regulation_is_classified_exactly_once():
    """No regulation is silently dropped, and none is double-counted."""
    _, _, rows = _run(_GA)
    assert len(rows) == len(FAR23_SUBPART_C)
    fars = [r.far for r in rows]
    assert len(set(fars)) == len(fars), "duplicate regulation row"
    assert set(fars) == {reg.far for reg in FAR23_SUBPART_C}
    assert all(r.status in (COVERED, NOT_APPLICABLE, NOT_ANALYSED, OUT_OF_SCOPE) for r in rows)


def test_every_absent_row_carries_a_reason():
    """'Absent' without a reason is unreviewable — the analyst cannot tell a
    conclusion from an omission."""
    _, _, rows = _run(_GA)
    for r in rows:
        if r.status != COVERED:
            assert r.reason.strip(), f"{r.far} is {r.status} with no reason"


def test_ga_fixture_covers_the_core_flight_and_ground_regulations():
    _, _, rows = _run(_GA)
    covered = {r.far for r in rows if r.status == COVERED}
    # The conditions the Appendix A oracle locks: envelope, speeds, load factors,
    # tail balancing/manoeuvre/gust, engine torque, and the landing cases.
    for far in ("23.301", "23.331", "23.333", "23.335", "23.337", "23.421",
                "23.423", "23.425", "23.427", "23.441", "23.443",
                "23.361", "23.363", "23.479", "23.481", "23.483", "23.485", "23.493"):
        assert far in covered, f"{far} should be covered by the GA fixture"


def test_combined_citations_credit_every_regulation_they_name():
    """``flight_envelope`` cites ``23.333/23.337/23.341/23.345/23.421`` in one
    string. A prefix test against the whole string would credit only 23.333 and
    report the other four as gaps despite their having been analysed."""
    _, refs, rows = _run(_GA)
    assert any("/" in (r or "") for r in refs), "fixture no longer exercises a combined citation"
    covered = {r.far for r in rows if r.status == COVERED}
    assert {"23.333", "23.337", "23.341", "23.345", "23.421"} <= covered


def test_out_of_scope_rows_are_never_reported_as_gaps():
    """A regulation no module implements is a permanent boundary of the tool, not
    a gap in this run — misclassifying it buries the real gaps."""
    _, _, rows = _run(_GA)
    out = [r for r in rows if r.status == OUT_OF_SCOPE]
    assert out, "expected some out-of-scope regulations (water loads, jacking, ...)"
    assert not any(r.is_gap for r in out)
    assert all(not r.module for r in out), "an out-of-scope row must name no module"
    # A representative sample the suite genuinely does not do.
    fars = {r.far for r in out}
    assert {"23.521", "23.507", "23.509", "23.562"} <= fars


def test_gap_list_is_short_enough_to_be_read():
    """The section fails at its job if the gap list is 25 rows of noise."""
    _, _, rows = _run(_GA)
    gaps = [r for r in rows if r.is_gap]
    assert 0 < len(gaps) <= 12, [r.far for r in gaps]
    assert all(r.module for r in gaps), "a gap must name the module that would close it"


def test_turboprop_only_conditions_are_not_applicable_to_a_piston_single():
    project, _, rows = _run(_GA)
    assert not project.is_concept
    by_far = {r.far: r for r in rows}
    for far in ("23.367", "23.371"):
        assert by_far[far].status == NOT_APPLICABLE, (far, by_far[far])
    # 23.367 is *engine failure*, so on a single the governing reason is that there
    # is no second engine to fail — reported ahead of the turboprop reason, which
    # would also apply. 23.371(b)'s rotor gyroscopic case is turboprop-specific.
    assert "single-engine" in by_far["23.367"].reason.lower()
    assert "turboprop" in by_far["23.371"].reason.lower()


def test_unflapped_airplane_marks_the_flap_conditions_not_applicable():
    """23.345 / 23.457 are an engineering conclusion on an unflapped wing, not a gap."""
    project = io.load_project(_GA)
    project.flap_loads = None
    if project.aero_coeffs is not None:
        project.aero_coeffs.flaps_down = None
    if project.speeds is not None:
        project.speeds.vf = None
    rows = {r.far: r for r in coverage_matrix(project, [])}
    for far in ("23.345", "23.457"):
        assert rows[far].status == NOT_APPLICABLE, (far, rows[far])
        assert "flap" in rows[far].reason.lower()


def test_summary_counts_add_up():
    _, _, rows = _run(_GA)
    summary = coverage_summary(rows)
    assert sum(summary.values()) == len(rows)
    assert summary[COVERED] > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
