"""A documented git/CI setting cannot differ from the live one in silence.

**The defect class (2026-08-25, backlog row 6 / issue #46, review CR-D-4).** Two
instances in one day, the same shape both times: a doc stated one thing, the
live setting another, and nothing compared them.

* `RELEASE_PROCESS.md` §4, `DEVELOPMENT_PROCESS.md` §0 (two rows) and
  `WORKFLOW_COMMANDS.txt` all said "linear history off, merge commits allowed".
  `main` enforces linear history; it refused the 0.7.2 milestone PR with "This
  branch must not contain merge commits" — at the cut, which is the worst moment
  to find it. Worse, the documented hotfix recovery told you to `git merge main`
  onto the milestone branch: the exact act that makes the milestone PR
  unmergeable, invisible until the cut.
* `DEVELOPMENT_PROCESS.md` §2 listed six required checks — `test (3.9)`,
  `test (3.11)`, `sbeam-roundtrip (3.11)` among them — three of which `ci.yml`
  never produces on a pull request at all. A required check that never reports
  blocks its PR forever; the live setting was (correctly) the fast-gate three,
  and §2 contradicted its own §0 table on the same page.

**Why the comparison is two hops.** CI has no `gh` credential, so a test cannot
read GitHub. Hop 1 is here and always runs: `.github/branch-protection.json` (a
checked-in snapshot of the live settings) is asserted against the prose, and
against what `ci.yml` actually reports on a pull request. Hop 2 is
`scripts/branch_protection_snapshot.py --check`, which the owner runs — it needs
auth, and a gate that needs a credential CI lacks is a gate that silently skips,
which is the failure mode this file exists to end.
"""

from __future__ import annotations

import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CI = os.path.join(_ROOT, ".github", "workflows", "ci.yml")
_SNAPSHOT = os.path.join(_ROOT, ".github", "branch-protection.json")
_STD = os.path.join(_ROOT, "docs", "10_standard")

_DEV_PROCESS = os.path.join(_STD, "DEVELOPMENT_PROCESS.md")
_RELEASE = os.path.join(_STD, "RELEASE_PROCESS.md")
_COMMANDS = os.path.join(_STD, "WORKFLOW_COMMANDS.txt")

#: Standard docs that describe the CI matrix to a reader.
_CI_CLAIM_SITES = (
    "README.md",
    "CLAUDE.md",
    os.path.join("docs", "10_standard", "00_program_overview.md"),
    os.path.join("docs", "10_standard", "DEVELOPMENT_PROCESS.md"),
)


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# --- what ci.yml actually reports ------------------------------------------

#: `python-version: ${{ <push-to-main cond> && fromJSON('[..full..]') || fromJSON('[..fast..]') }}`
_MATRIX = re.compile(
    r"python-version:\s*\$\{\{.*?fromJSON\('(?P<full>\[[^']*\])'\).*?fromJSON\('(?P<fast>\[[^']*\])'\)",
    re.S,
)
_JOB = re.compile(r"^  (?P<name>[a-z][a-z0-9-]*):\s*$", re.M)


def _ci_jobs():
    """{job name: (versions on a PR, versions on the push to main)}.

    A job with no version matrix reports under its bare name, so it maps to
    ``([""], [""])`` and yields the check name ``"<job>"``.
    """
    text = _read(_CI)
    starts = [(m.group("name"), m.start()) for m in _JOB.finditer(text)]
    jobs = {}
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        m = _MATRIX.search(text, start, end)
        if m:
            jobs[name] = (json.loads(m.group("fast")), json.loads(m.group("full")))
        else:
            jobs[name] = ([""], [""])
    return jobs


def _check_names(index):
    """The check names GitHub reports; ``index`` 0 = on a PR, 1 = on push to main."""
    out = set()
    for name, versions in _ci_jobs().items():
        for v in versions[index]:
            out.add(f"{name} ({v})" if v else name)
    return out


def test_the_ci_matrix_is_parsed_at_all():
    """Guard the guard: every assertion below is vacuous if the regexes stop
    matching a rewritten ci.yml, and a vacuous conformance test is worse than
    none — it reports the drift class as covered."""
    jobs = _ci_jobs()
    assert {"test", "typecheck", "sbeam-roundtrip"} <= set(jobs), (
        f"ci.yml job names not recognised: {sorted(jobs)}"
    )
    assert jobs["test"][0] != jobs["test"][1], (
        "ci.yml's `test` matrix no longer differs between a PR and the push to main. "
        "If the asymmetry was removed deliberately, this file and the docs it asserts "
        "must be rewritten together — that asymmetry is their whole subject."
    )


# --- hop 1a: snapshot <-> ci.yml -------------------------------------------

def test_every_required_check_actually_runs_on_a_pull_request():
    """CR-D-4's second instance, made structural. A required status check that
    `ci.yml` does not produce on a pull request can never report, so the PR can
    never merge — which is why the required set is the fast gate and not the
    full matrix. This is the assertion that would have caught the six-check
    list `DEVELOPMENT_PROCESS.md` §2 carried."""
    required = set(json.load(open(_SNAPSHOT, encoding="utf-8"))["required_status_checks"])
    on_pr = _check_names(0)
    missing = sorted(required - on_pr)
    assert not missing, (
        f"required check(s) that never run on a PR: {missing}.\n"
        f"ci.yml reports {sorted(on_pr)} on a pull request. Either the protection "
        "setting is wrong (fix it on GitHub, then run "
        "`python scripts/branch_protection_snapshot.py --write`) or ci.yml stopped "
        "producing the check."
    )


# --- hop 1b: snapshot <-> the process docs ---------------------------------

def test_the_process_docs_name_the_snapshot_required_checks():
    """`DEVELOPMENT_PROCESS.md` states the required-check set twice — §0's solo
    table and §2's protection bullet. Both must name exactly what is required,
    and neither may name a check that is not."""
    snap = json.load(open(_SNAPSHOT, encoding="utf-8"))
    text = _read(_DEV_PROCESS)
    for check in snap["required_status_checks"]:
        assert text.count(f"`{check}`") >= 2, (
            f"required check {check!r} is named fewer than twice in "
            "DEVELOPMENT_PROCESS.md — §0's table and §2's protection bullet must both "
            "state the live required set."
        )
    stale = [
        c
        for c in ("test (3.9)", "test (3.11)", "sbeam-roundtrip (3.11)")
        if c not in snap["required_status_checks"] and f"required checks `{c}`" in text
    ]
    assert not stale, f"DEVELOPMENT_PROCESS.md still lists non-required check(s): {stale}"


#: A phrase that follows one of these, within a short window, is being retracted
#: rather than asserted ("**Rebase, not `git merge main`**").
_NEGATION = re.compile(r"(?:\bnot\b|\bnever\b|\bno longer\b|rather than|instead of)[^.]{0,40}$")


def _unquoted(text: str, phrase: str) -> list:
    """Line numbers where ``phrase`` is *asserted* rather than cited.

    These docs correct themselves in place — §0's protection row quotes the
    wording it retracts ("linear history off, merge commits allowed"), and
    `RELEASE_PROCESS.md` §6 names the banned command to forbid it ("**Rebase, not
    `git merge main`**"). A flat substring ban fires on both and would force the
    correction off the page, which is the opposite of what this row wants. Two
    forms count as citation: inside quotation marks, or immediately after a
    negation. Anything else is the page telling you to do it.
    """
    quoted = set()
    for m in re.finditer(r'"[^"]*"', text):
        if phrase in m.group(0):
            quoted.update(range(m.start(), m.end()))
    out = []
    for m in re.finditer(re.escape(phrase), text):
        if m.start() in quoted:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        if _NEGATION.search(text[line_start : m.start()]):
            continue
        out.append(text.count("\n", 0, m.start()) + 1)
    return out


def test_the_process_docs_agree_with_the_live_merge_method():
    """The 0.7.2 instance: `main` requires linear history, so the milestone PR is
    rebase-merged. No process doc may tell you to merge it any other way, and the
    hotfix recovery must not tell you to merge `main` *into* the milestone branch
    — that is what makes the PR unmergeable, and it is invisible until the cut."""
    snap = json.load(open(_SNAPSHOT, encoding="utf-8"))
    assert snap["required_linear_history"] is True and snap["milestone_pr_merge_method"] == "rebase", (
        "the snapshot no longer describes a linear-history/rebase repository; this "
        "test's assertions below are written for that setting and must be revisited."
    )
    for path in (_DEV_PROCESS, _RELEASE, _COMMANDS):
        text = _read(path)
        assert "--rebase" in text or "rebase-merge" in text, (
            f"{os.path.relpath(path, _ROOT)} describes the milestone merge but never "
            "says rebase, while `main` requires linear history."
        )
        for banned in ("merge commits allowed", "linear history off", "git merge main"):
            loose = _unquoted(text, banned)
            assert not loose, (
                f"{os.path.relpath(path, _ROOT)} asserts {banned!r} — contradicts the live "
                "linear-history setting recorded in .github/branch-protection.json. "
                "(Quoting the old wrong wording to correct it is fine; this fires only on "
                f"an occurrence outside quotation marks. Offending line(s): {loose})"
            )


# --- hop 1c: no doc may state the matrix without its asymmetry -------------

_FULL_LIST = re.compile(r"3\.9\s*(?:/|,)\s*3\.11\s*(?:/|,)\s*3\.12")


@pytest.mark.parametrize("rel", _CI_CLAIM_SITES)
def test_no_doc_states_the_full_matrix_as_if_it_ran_everywhere(rel):
    """CR-D-4's first instance. Three documents said "CI runs ... on 3.9 / 3.11 /
    3.12" with no caveat, while a PR runs 3.12 alone — so a change that breaks
    3.9 merges green by design, and the docs promised otherwise. Any sentence
    naming the full matrix must also name `main`, where it actually runs."""
    lines = _read(os.path.join(_ROOT, rel)).splitlines()
    bad = []
    for n, line in enumerate(lines):
        if not _FULL_LIST.search(line):
            continue
        window = " ".join(lines[max(0, n - 2) : n + 3])  # prose wraps
        if "main" not in window:
            bad.append(f"{rel}:{n + 1}: {line.strip()[:100]}")
    assert not bad, (
        "the full CI matrix is stated without saying it runs only on the push to "
        "`main` (a PR runs 3.12 alone):\n  " + "\n  ".join(bad)
    )


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
