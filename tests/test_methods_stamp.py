"""The methods & limitations statement reaches every export channel (Step G8.3).

Modelled on ``test_ultimate_contract.py``, and for the same reason: a deliverable
that leaves this tool must carry its own basis *in band*. A span-load CSV
forwarded to a stress engineer, or a BDF handed to sbeam, has to say by itself
that its numbers are ULTIMATE, under what category, and what the tool does not
do. An on-page caption does not travel with a downloaded file.

Two failure modes are pinned:

1. **A channel loses the stamp** — the statement is built in one place
   (``report.methods``) but has to be *passed* to each writer, and a writer that
   silently drops its ``header_comment`` argument would go unnoticed.
2. **The stamp breaks the payload** — ``#`` comment lines above a CSV header row
   are only harmless if every reader skips them. A stamped CSV must parse to the
   *same rows* as an unstamped one.
"""

import csv as _csv
import io as _io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.net_loads import build_net_loads  # noqa: E402
from sloads.registry import run_all_modules  # noqa: E402
from sloads.report.methods import (  # noqa: E402
    APPROVED_CORRECTIONS,
    bdf_comment_block,
    csv_comment_block,
    methods_statement,
    strip_comment_lines,
)
import sloads.modules  # noqa: E402,F401

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")


def _project(path):
    return io.load_project(path)


def _wing_net(path):
    p = _project(path)
    if p.envelope is None:
        p.envelope = build_envelope(p)
    return p, build_net_loads(p).wing_net


# --------------------------------------------------------------------------- #
# The statement itself
# --------------------------------------------------------------------------- #
def test_statement_carries_every_required_block():
    """The eight content blocks of plan §5, each identified by its heading."""
    text = methods_statement(_project(_GA), tool_version="0.3.0", scope="full case set")
    for heading in ("METHODS AND LIMITATIONS", "BASIS:", "CATEGORY:", "VERIFICATION:",
                    "MATH:", "APPROVED CORRECTIONS", "KNOWN LIMITATIONS:",
                    "SCOPE OF THIS EXPORT:", "PROVENANCE:"):
        assert heading in text, f"missing block: {heading}"


def test_statement_states_ultimate_and_the_default_factor():
    text = methods_statement(_project(_GA))
    assert "ULTIMATE" in text
    assert "1.5" in text and "23.303" in text


def test_statement_lists_every_approved_correction():
    """A deviation from the source manual that is not declared is invisible to the
    analyst — which defeats the point of approving it in the open."""
    text = methods_statement(_project(_GA))
    for far, _ in APPROVED_CORRECTIONS:
        assert far in text, far


def test_verification_states_the_twin_cases_are_not_oracle_locked():
    """The oracle-status distinction is the single most load-bearing caveat in the
    document: Appendix B is not bundled, so twin results are closure-locked."""
    text = methods_statement(_project(_GA))
    assert "CLOSURE-LOCKED" in text and "NOT ORACLE-LOCKED" in text
    assert "Appendix B" in text


def test_concept_fixture_gets_the_caveat_and_the_ga_one_does_not():
    ga = methods_statement(_project(_GA))
    concept = methods_statement(_project(_CONCEPT))
    assert "UNVERIFIED EXTRAPOLATION" in concept
    assert "UNVERIFIED EXTRAPOLATION" not in ga
    assert "FAR 23 category" in ga


def test_deselected_cases_are_named_never_silently_dropped():
    text = methods_statement(_project(_GA), scope="governing case set",
                             deselected_case_ids=["W-03", "HT-02"])
    assert "DESELECTED" in text
    assert "W-03" in text and "HT-02" in text


def test_statement_is_deterministic():
    """Two renders must be byte-identical, or the diff between two report
    revisions is unreadable and the tests turn flaky. Nothing reads the clock."""
    p = _project(_GA)
    assert methods_statement(p, tool_version="0.3.0") == methods_statement(p, tool_version="0.3.0")
    stamped = methods_statement(p, generated="2026-08-04T00:00:00Z")
    assert "2026-08-04T00:00:00Z" in stamped
    assert "Generated:" not in methods_statement(p), "no timestamp unless the caller supplies one"


# --------------------------------------------------------------------------- #
# Comment-block wrappers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("wrapper,marker", [(csv_comment_block, "#"), (bdf_comment_block, "$")])
def test_every_line_of_a_comment_block_is_marked(wrapper, marker):
    """One unmarked line turns a comment block into a parse error."""
    block = wrapper(_project(_GA))
    lines = [ln for ln in block.split("\n") if ln]
    assert lines
    assert all(ln.startswith(marker) for ln in lines), [ln for ln in lines
                                                        if not ln.startswith(marker)]


def test_strip_comment_lines_is_the_inverse_for_readers():
    block = csv_comment_block(_project(_GA))
    assert strip_comment_lines(block + "a,b\n1,2\n") == "a,b\n1,2\n"


# --------------------------------------------------------------------------- #
# The channels
# --------------------------------------------------------------------------- #
def test_load_cases_csv_carries_the_stamp_and_still_parses():
    project = _project(_GA)
    results = run_all_modules(project)
    module = next(r for r in results if r.conditions)
    plain = io.load_cases_csv(module)
    stamped = io.load_cases_csv(module, header_comment=csv_comment_block(project))

    assert stamped.startswith("#")
    assert "ULTIMATE" in stamped
    # The payload is untouched: same rows, same header.
    assert strip_comment_lines(stamped) == plain
    rows_plain = list(_csv.DictReader(_io.StringIO(plain)))
    rows_stamped = list(_csv.DictReader(_io.StringIO(strip_comment_lines(stamped))))
    assert rows_stamped == rows_plain
    assert rows_plain, "fixture produced no rows to compare"


def test_span_load_csv_carries_the_stamp_and_still_parses():
    project, wing = _wing_net(_GA)
    plain = sb.span_load_csv(wing)
    stamped = sb.span_load_csv(wing, header_comment=csv_comment_block(project))
    assert stamped.startswith("#") and "ULTIMATE" in stamped
    assert strip_comment_lines(stamped) == plain


def test_case_index_csv_carries_the_stamp():
    project = _project(_GA)
    if project.envelope is None:
        project.envelope = build_envelope(project)
    plain = sb.case_index_csv(project)
    stamped = sb.case_index_csv(project, header_comment=csv_comment_block(project))
    assert stamped.startswith("#")
    assert strip_comment_lines(stamped) == plain


def test_pandas_reads_a_stamped_csv_with_comment_marker():
    """The documented consumer contract: ``comment='#'``."""
    pd = pytest.importorskip("pandas")
    project = _project(_GA)
    results = run_all_modules(project)
    module = next(r for r in results if r.conditions)
    stamped = io.load_cases_csv(module, header_comment=csv_comment_block(project))
    df = pd.read_csv(_io.StringIO(stamped), comment="#")
    plain_df = pd.read_csv(_io.StringIO(io.load_cases_csv(module)))
    assert list(df.columns) == list(plain_df.columns)
    assert len(df) == len(plain_df)


def test_workbook_reader_skips_the_stamp():
    """``export/workbook._csv_to_df`` is an in-repo reader; G8.3 audited it."""
    pytest.importorskip("pandas")
    from sloads.export.workbook import _csv_to_df

    project = _project(_GA)
    results = run_all_modules(project)
    module = next(r for r in results if r.conditions)
    stamped = io.load_cases_csv(module, header_comment=csv_comment_block(project))
    df = _csv_to_df(stamped)
    plain = _csv_to_df(io.load_cases_csv(module))
    assert df is not None and plain is not None
    assert list(df.columns) == list(plain.columns)
    assert len(df) == len(plain)


def test_workbook_gains_a_methods_sheet():
    pytest.importorskip("openpyxl")
    pytest.importorskip("pandas")
    from openpyxl import load_workbook

    from sloads.export.workbook import build_workbook

    project = _project(_GA)
    data = build_workbook(
        {"Project": project.name}, {}, {}, "", {},
        methods=methods_statement(project),
    )
    wb = load_workbook(_io.BytesIO(data))
    assert "Methods" in wb.sheetnames
    text = "\n".join(str(c.value) for row in wb["Methods"].iter_rows() for c in row)
    assert "ULTIMATE" in text


def test_summary_report_carries_the_same_statement(tmp_path):
    """Step G8: the report is a channel like the others. Its §5 is the shared
    statement verbatim, so the document and the CSV/BDF files stamped beside it in
    the bundle cannot state different bases (SUMMARY_REPORT.md §4.6)."""
    from sloads.report.content import build_report
    from sloads.report.latex import render_report

    project = _project(_GA)
    doc = build_report(project)
    assert doc.methods == methods_statement(project)
    assert "ULTIMATE" in doc.section("5. Methods and limitations").body[0]
    # And it survives the trip through the renderer (escaped, not dropped).
    assert "ULTIMATE" in render_report(project)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
