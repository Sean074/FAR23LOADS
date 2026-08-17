"""The backlog ↔ issues bridge's parser and rewriter, on the live backlog (design note 28 MD-5).

`scripts/backlog_issues.py check` needs `gh` and is a release/review step, not a
test. What can be asserted offline: the parser sees every priority-table row,
each row carries a band, a tier and a tag label, and the rewriter is a pure
function that adds `(#N)` once and only once.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_ROOT, "scripts", "backlog_issues.py")
_BACKLOG = os.path.join(_ROOT, "docs", "30_future", "00_backlog.md")


@pytest.fixture(scope="module")
def bi():
    spec = importlib.util.spec_from_file_location("backlog_issues", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["backlog_issues"] = mod  # dataclasses resolve the module through sys.modules
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def backlog_text():
    with open(_BACKLOG, encoding="utf-8") as fh:
        return fh.read()


def test_every_priority_table_row_is_parsed_with_band_tier_tag(bi, backlog_text):
    rows_in_file = [ln for ln in backlog_text.splitlines() if re.match(r"^\|\s*\d+\s*\|", ln)]
    rows = [it for it in bi.parse_backlog(backlog_text) if it.kind == "row"]
    assert len(rows) == len(rows_in_file) > 0
    for r in rows:
        kinds = {lb.split(":")[0] for lb in r.labels}
        assert {"band", "tier", "tag", "kind"} <= kinds, r.title
        assert r.title and len(r.title) <= 120


def test_issue_set_folds_matching_detail_sections_and_keeps_the_rest(bi, backlog_text):
    items = bi.parse_backlog(backlog_text)
    out = bi.issue_set(items)
    titles = [it.title for it in out]
    assert len(titles) == len(set(titles)), "duplicate issue titles"
    assert sum(it.kind == "row" for it in out) == sum(it.kind == "row" for it in items)


def test_rewrite_adds_issue_refs_once(bi):
    text = ("| Pri | Item | What ships | Tag | Tier / effort | Depends on |\n|---|---|---|---|---|---|\n"
            "| **A — x** ||||||\n| 1 | First `item` | ships | E | S / S | — |\n| 2 | Second | ships | V | M / M | — |\n"
            "\n### [V] Second detail\n\nbody line\n\n---\n\n## Open defects (index)\n\n- **A defect.** text\n  more\n")
    numbers = {"First item": 10, "Second": 11, "Second detail": 11, "A defect.": 12}
    once = bi.rewrite_backlog(text, numbers)
    assert "| First `item` (#10) |" in once and "| Second (#11) |" in once
    assert "### [V] Second detail → #11" in once and "Body moved to issue #11" in once
    assert "- #12 — A defect." in once and "  more" not in once
    assert bi.rewrite_backlog(once, numbers) == once  # idempotent
    assert bi.table_refs(once) == [10, 11]


def test_render_round_trips_the_live_table_and_drops_closed_rows(bi, backlog_text):
    """``render`` is the inverse of ``create``: a row -> its issue body ->
    ``row_from_issue`` reproduces the row byte-for-byte on the live file, so the
    table can be regenerated from the issues without moving anything but the
    rows whose issues closed."""
    rows = [it for it in bi.parse_backlog(backlog_text) if it.kind == "row"]
    assert rows
    issues = {}
    for it in rows:
        refs = bi.ISSUE_REF.findall(backlog_text.splitlines()[it.line - 1])
        assert refs, f"row {it.pri} in band {it.band} carries no (#N)"
        issues[int(refs[0])] = ("OPEN", it.body)
    assert bi.render_backlog(backlog_text, issues) == backlog_text
    # Close the first row's issue: exactly that line goes, nothing else moves.
    first = int(bi.ISSUE_REF.findall(backlog_text.splitlines()[rows[0].line - 1])[0])
    issues[first] = ("CLOSED", issues[first][1])
    rendered = bi.render_backlog(backlog_text, issues)
    kept = [ln for ln in backlog_text.splitlines() if f"(#{first})" not in ln or not bi.ITEM_ROW.match(ln)]
    assert rendered == "\n".join(kept) + "\n"
    # A body without the row block leaves the line alone.
    issues[first] = ("OPEN", "hand-written body")
    assert bi.render_backlog(backlog_text, issues) == backlog_text


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
