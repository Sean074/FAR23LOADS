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
    rows whose issues closed.

    A row is **owned by its first** ``(#N)`` -- the one ``row_from_issue`` emits
    after the item title. A later ``(#N)`` in the same line is a cross-reference
    to another row's issue ("the view functions wait for the GUI review (#29)"),
    and closing *that* issue must not delete this row. Both halves are asserted
    below, because the distinction is invisible while the table happens to lead
    with an issue nothing else cites -- which is how it read until #13 closed."""
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

    def owner(line):
        """The issue a row line belongs to -- its first ``(#N)``, or None."""
        refs = bi.ISSUE_REF.findall(line)
        return int(refs[0]) if refs else None

    kept = [ln for ln in backlog_text.splitlines()
            if not bi.ITEM_ROW.match(ln) or owner(ln) != first]
    assert rendered == "\n".join(kept) + "\n"
    # A row that only *cites* the closed issue survives, with its text intact.
    citing = [ln for ln in backlog_text.splitlines()
              if bi.ITEM_ROW.match(ln) and owner(ln) != first and f"(#{first})" in ln]
    for ln in citing:
        assert ln in rendered.splitlines(), (
            f"row owned by #{owner(ln)} was dropped for citing #{first}")
    # A body without the row block leaves the line alone.
    issues[first] = ("OPEN", "hand-written body")
    assert bi.render_backlog(backlog_text, issues) == backlog_text


# --- band -> milestone (issue #46, 2026-08-25) -------------------------------

def test_every_band_header_is_parsed_including_the_two_character_one(bi, backlog_text):
    """`BAND_ROW` matched a single letter until 2026-08-25, so the **B2** header
    (0.9.0) never matched and every row beneath it inherited band **B** — the
    0.8.0 label — with no gate seeing it. The band an issue is filed under is
    what the milestone check compares, so a band the parser cannot see is a
    milestone check that cannot work."""
    headers = [ln for ln in backlog_text.splitlines() if re.match(r"^\|\s*\*\*[A-Z]\d?\s+[—-]", ln)]
    parsed = bi.band_milestones(backlog_text)
    assert len(parsed) == len(headers) > 0, (
        f"{len(headers)} band header row(s) in the file, {len(parsed)} parsed: {sorted(parsed)}"
    )
    assert any(len(b) > 1 for b in parsed), (
        "no multi-character band in the table — if B2 was retired, this assertion "
        "and BAND_ROW's `\\d?` can go together; until then it is the regression pin"
    )


def test_a_band_names_the_release_it_ships_in_or_names_none(bi, backlog_text):
    """The map is read from the header text, never hardcoded: band letters move at
    every re-cut (band A retired when 0.7.2 was cut, making **B** the milestone in
    flight), and a hardcoded letter→release map is the drift this check exists to
    catch. Only a band that names no release — 'when the module is next touched' —
    may map to ``None``."""
    milestones = bi.band_milestones(backlog_text)
    named = {b: v for b, v in milestones.items() if v}
    assert named, "no band header names a release"
    assert len(set(named.values())) == len(named), f"two bands name the same release: {named}"
    for band, ship in milestones.items():
        if ship is None:
            header = next(ln for ln in backlog_text.splitlines()
                          if re.match(rf"^\|\s*\*\*{band}\s+[—-]", ln))
            assert "when the module is next touched" in header, (
                f"band {band} names no release and is not the maintenance band: {header[:120]}"
            )


def test_a_rows_issue_is_its_item_cell_not_a_cross_reference(bi):
    """A row is identified by the ``(#N)`` in its **Item** cell. Other cells cite
    other rows' issues in prose, and reading the whole line put #29 — the single
    band-B2 row — under band D, where the milestone check would have demanded it
    carry no milestone: a guard reporting a fault against the row it misread."""
    line = "| 13 | Calc-side function size (#17) | the view functions wait for the review (#29) | V | S / S | — |"
    assert bi.row_ref(line) == 17
    assert bi.row_bands("| **D — maintenance, when the module is next touched** ||||||\n" + line) == {17: "D"}


def test_no_open_row_sits_in_a_band_whose_release_is_already_cut(bi, backlog_text):
    """The offline half of the #71 case: that issue sat open on the already-cut
    0.7.1 while its row was in the 0.8.0 band. The live half needs `gh` and lives
    in ``check``; this half needs only the two files — a band still in the table
    may not name a release ``CHANGELOG.md`` shows as shipped."""
    cut = bi.cut_milestones()
    assert cut, "no released section parsed out of CHANGELOG.md — the pattern broke"
    shipped = {b: v for b, v in bi.band_milestones(backlog_text).items() if v in cut}
    assert not shipped, (
        f"band(s) naming an already-cut release: {shipped}. Retire the band at the cut "
        "(RELEASE_PROCESS.md §4) — rows under it can never ship."
    )


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
