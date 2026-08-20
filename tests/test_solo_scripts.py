"""The solo close-loop scripts stay parseable and self-describing (DEVELOPMENT_PROCESS.md §0).

`scripts/solo_start.sh` / `scripts/solo_close.sh` need `git` and `gh` against
the live repository, so the loop itself is not a test. What can be asserted
offline: both scripts parse (`bash -n`), answer `--help` with their usage, and
`--dry-run` prints the full step sequence without executing anything — the
sequence is what §0 promises, so the dry-run text is checked for each step's
signature command.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_START = os.path.join(_ROOT, "scripts", "solo_start.sh")
_CLOSE = os.path.join(_ROOT, "scripts", "solo_close.sh")

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash not on PATH")


def _bash(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", *args], capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("script", [_START, _CLOSE])
def test_scripts_parse_and_answer_help(script):
    assert _bash("-n", script).returncode == 0
    res = _bash(script, "--help")
    assert res.returncode == 0
    assert "Usage:" in res.stdout and "DEVELOPMENT_PROCESS.md" in res.stdout


def test_start_dry_run_lists_step_1_and_refuses_bad_branch_names():
    res = _bash(_START, "--dry-run", "27", "chore/some-slug")
    assert res.returncode == 0, res.stderr
    for sig in ("git pull --ff-only", "git checkout -b chore/some-slug", "solo_close.sh 27"):
        assert sig in res.stdout
    bad = _bash(_START, "--dry-run", "27", "some-slug")
    assert bad.returncode != 0 and "<type>/<kebab-slug>" in bad.stderr


def test_close_dry_run_lists_steps_3_to_7_in_order():
    res = _bash(_CLOSE, "--dry-run", "27", "Subject")
    assert res.returncode == 0, res.stderr
    signatures = [
        "ruff check sloads/ cli.py app/ scripts/",
        "mypy",
        "pytest -q -p no:cacheprovider",
        "git add -A",
        "git commit -m",
        "git merge --ff-only",
        "git push origin main",
        "gh issue close 27 --reason completed",
        "git branch -d",
        "backlog_issues.py check",
        "gh run list --branch main",
    ]
    positions = [res.stdout.find(s) for s in signatures]
    assert all(p >= 0 for p in positions), dict(zip(signatures, positions))
    assert positions == sorted(positions), "steps 3–7 are out of order in the dry-run"


def test_close_rejects_missing_or_empty_arguments():
    assert _bash(_CLOSE, "--dry-run").returncode == 2
    assert _bash(_CLOSE, "--dry-run", "x", "Subject").returncode == 1


# --- the issue number is optional under the solo profile (§0) ---------------


#: The `gh` work an issue number costs, per item. Omitting the issue must drop
#: every one of them; the trailing `gh run list` CI peek is not in this set —
#: it is a courtesy, guarded on `gh auth status` succeeding at the time.
_ISSUE_GH_CALLS = ("gh auth status", "gh issue view", "gh issue close", "backlog_issues.py check")


@pytest.mark.parametrize(
    "argv, with_issue",
    [
        ([_START, "--dry-run", "27", "chore/some-slug"], True),
        ([_START, "--dry-run", "chore/some-slug"], False),
        ([_CLOSE, "--dry-run", "27", "Subject"], True),
        ([_CLOSE, "--dry-run", "--slug", "some-slug", "Subject"], False),
    ],
)
def test_the_issue_number_is_optional_and_omitting_it_drops_every_gh_call(argv, with_issue):
    res = _bash(*argv)
    assert res.returncode == 0, res.stderr
    present = [c for c in _ISSUE_GH_CALLS if c in res.stdout]
    if with_issue:
        assert present, res.stdout
    else:
        assert present == [], f"{present} survived without an issue number:\n{res.stdout}"


def test_close_without_an_issue_still_lists_the_gate_commit_and_land_steps():
    res = _bash(_CLOSE, "--dry-run", "--slug", "some-slug", "Subject")
    assert res.returncode == 0, res.stderr
    signatures = [
        "ruff check sloads/ cli.py app/ scripts/",
        "mypy",
        "pytest -q -p no:cacheprovider",
        "git add -A",
        "git commit -m",
        "git push origin main",
    ]
    positions = [res.stdout.find(s) for s in signatures]
    assert all(p >= 0 for p in positions), dict(zip(signatures, positions))
    assert positions == sorted(positions)


# --- the gate scales to the change set (§0) ---------------------------------


def test_the_dry_run_names_the_docs_only_guard_set():
    """The docs-only gate is §0's own five guard files, not a second list."""
    res = _bash(_CLOSE, "--dry-run", "27", "Subject")
    assert res.returncode == 0, res.stderr
    for guard in (
        "tests/test_doc_currency.py",
        "tests/test_changelog_fragments.py",
        "tests/test_backlog_issues.py",
        "tests/test_schema_guards.py",
        "tests/test_workflow.py",
    ):
        assert guard in res.stdout, guard


def test_the_docs_only_predicate_admits_docs_and_rejects_everything_else():
    """The `case` arms in solo_close.sh decide branch-or-main and gate size."""
    src = open(_CLOSE, encoding="utf-8").read()
    assert "*.md|docs/*|changes/*)" in src, "the docs-only allowlist moved — re-check this guard"
    # anything outside the allowlist must fall through to the full suite
    assert "DOCS_ONLY=0; break" in src


def test_close_on_main_needs_a_slug_and_is_refused_for_a_code_change_set():
    """Both refusals are stated in the usage, so --help carries the contract."""
    res = _bash(_CLOSE, "--help")
    assert res.returncode == 0
    assert "REQUIRED when closing on main" in res.stdout
    assert "docs-only" in res.stdout


def test_start_dry_run_names_the_fragment_solo_close_will_expect():
    res = _bash(_START, "--dry-run", "28", "chore/some-slug")
    assert "changes/some-slug.<type>.md" in res.stdout


def test_close_honours_suffix_and_date_and_rejects_a_bad_date():
    res = _bash(_CLOSE, "--dry-run", "--suffix", "backlog Pri 9, tier S, 2026-08-17", "28", "X")
    assert res.returncode == 0 and 'git commit -m "X (backlog Pri 9, tier S, 2026-08-17)"' in res.stdout
    res = _bash(_CLOSE, "--dry-run", "--date", "2026-08-17", "28", "X")
    assert res.returncode == 0 and "2026-08-17)" in res.stdout
    bad = _bash(_CLOSE, "--dry-run", "--date", "2026-13-40", "28", "X")
    assert bad.returncode == 1 and "--date must be YYYY-MM-DD" in bad.stderr


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
