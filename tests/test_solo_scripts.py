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
    assert _bash(_CLOSE, "--dry-run", "27").returncode == 2
    assert _bash(_CLOSE, "--dry-run", "x", "Subject").returncode == 1


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
