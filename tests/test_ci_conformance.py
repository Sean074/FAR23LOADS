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
_SMOKE = os.path.join(_ROOT, "scripts", "smoke_test.sh")

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
        for c in ("test (3.9)", "test (3.10)", "test (3.11)", "sbeam-roundtrip (3.11)")
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


def test_the_process_docs_agree_with_the_live_review_settings():
    """The 2026-08-26 instance, and CR-D-4's own class one field deeper. §2 promised
    an approving review from a non-author, Code Owners review and stale-approval
    dismissal against a branch that required none of them: `required_pull_request`
    was true the moment GitHub carried *any* review block, so no assertion here
    could see the difference. The snapshot now tracks the three settings
    themselves, and this test holds the prose to whichever way they are set —
    including back, when a second collaborator turns them on."""
    snap = json.load(open(_SNAPSHOT, encoding="utf-8"))
    text = _read(_DEV_PROCESS)

    # The one review setting that IS live, in both profiles.
    assert snap["required_conversation_resolution"] is True, (
        "`main` no longer requires conversation resolution; §2 still says it does."
    )
    assert "conversations resolved" in text, (
        "DEVELOPMENT_PROCESS.md §2 stopped naming conversation resolution, which is "
        "live on `main`."
    )

    solo = (
        snap["required_approving_review_count"] == 0
        and snap["required_code_owner_reviews"] is False
        and snap["dismiss_stale_reviews"] is False
    )
    caveat = "Review requirements are the multi-dev profile's, and are OFF under §0"
    if solo:
        assert caveat in text, (
            "no review requirement is live on `main` (approvals, Code Owners and "
            "stale dismissal are all off in .github/branch-protection.json), but "
            "DEVELOPMENT_PROCESS.md §2 does not carry the bullet saying so. Written "
            "as a live requirement, it is a promise the branch does not keep."
        )
    else:
        assert caveat not in text, (
            "a review requirement is now live on `main`, so §2's 'OFF under §0' "
            "bullet is stale — state the settings as live and move them out of the "
            "switch-over list."
        )


# --- hop 1c: no doc may state the matrix without its asymmetry -------------

_FULL_LIST = re.compile(r"3\.10\s*(?:/|,)\s*3\.11\s*(?:/|,)\s*3\.12")


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


# --------------------------------------------------------------------------- #
# The §3.5 smoke gate and the front-ends it claims to boot (#127)
# --------------------------------------------------------------------------- #
# The same defect class as the rest of this file, in the release gate rather than
# in CI: §3.5 is a hard gate, and for the release whose headline deliverable is
# the oracle GUI it started `app/Home.py` and nothing else. A second front-end
# nothing boots under a real server is a front-end whose boot no gate covers.

#: Directories that hold no front-end. Everything else at the top level is
#: scanned, so a third GUI joins the comparison by existing rather than by
#: someone remembering to list it here.
_NOT_A_GUI = {"tests", "scripts", "docs", "reference", "sloads", "changes",
              "examples", "projects", "changes", "sloads.egg-info"}
#: A GUI entry point is the file that calls ``st.set_page_config`` -- exactly one
#: per front-end (``tests/test_app_shell.py`` owns that rule). Anchored at the
#: line start so prose *about* the call, in a test or a doc, is not a front-end.
_PAGE_CONFIG = re.compile(r"^\s*st\.set_page_config\(", re.M)


def _front_ends():
    found = []
    for gui in sorted(os.listdir(_ROOT)):
        path = os.path.join(_ROOT, gui)
        if gui.startswith(".") or gui in _NOT_A_GUI or not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            entry = os.path.join(path, name)
            if not name.endswith(".py") or not os.path.isfile(entry):
                continue
            if _PAGE_CONFIG.search(_read(entry)):
                found.append(f"{gui}/{name}")
    return found


def test_the_smoke_gate_boots_every_front_end_this_repo_has():
    """`st.set_page_config` marks a GUI entry point (one per front-end, guarded
    by tests/test_app_shell.py). Every one of them is booted by the §3.5 script."""
    script = _read(_SMOKE)
    declared = re.search(r"GUI_ENTRY_POINTS=\((?P<body>[^)]*)\)", script)
    assert declared, "smoke_test.sh no longer declares GUI_ENTRY_POINTS"
    booted = re.findall(r'"([^"]+\.py)"', declared.group("body"))
    front_ends = _front_ends()
    assert front_ends, "no front-end found -- the detector, not the gate, is broken"
    assert sorted(booted) == sorted(front_ends), (
        "scripts/smoke_test.sh boots {booted} but this repo's front-ends are "
        "{front}: a GUI the §3.5 gate never starts is a GUI no release gate "
        "starts (#127)".format(booted=sorted(booted), front=sorted(front_ends))
    )
    # Declaring them is not booting them: one smoke_gui call per front-end.
    calls = re.findall(r"^smoke_gui ", script, re.M)
    assert len(calls) == len(front_ends), (
        f"{len(front_ends)} front-end(s) declared, {len(calls)} booted")


def test_the_release_checklist_names_every_front_end_the_gate_boots():
    """§3.5 is the line a release manager reads. It names what the script does."""
    release = _read(_RELEASE)
    section = release[release.index("### 3.5"):]
    section = section[:section.index("---")]
    for entry in _front_ends():
        assert entry in section, (
            f"RELEASE_PROCESS.md §3.5 does not name {entry}, which the smoke "
            "gate boots -- the checklist and the script must say the same thing"
        )
    assert "sloads-oracle" in section, (
        "§3.5 must say the oracle GUI is launched through its console script: "
        "running the launcher is the half of #127 that path-checking missed"
    )


def test_the_smoke_gate_runs_the_oracle_launcher_rather_than_resolving_it():
    """`test_oracle_gui.test_the_launcher_points_at_the_entry_point` proves the
    path resolves; only this proves the console script `pyproject.toml` binds
    actually starts a server."""
    script = _read(_SMOKE)
    assert "sloads-oracle" in script, "the console script is never invoked"
    with open(os.path.join(_ROOT, "pyproject.toml"), encoding="utf-8") as fh:
        assert "sloads-oracle" in fh.read(), "the console script is not declared"


_CLASSIFIER = re.compile(r'"Programming Language :: Python :: (3\.\d+)"')
_REQ_PY = re.compile(r'requires-python\s*=\s*">=(3\.\d+)"')
_MATRIX_LIST = re.compile(r"fromJSON\('\[([^\]]*)\]'\)")


def test_the_python_support_claim_is_one_claim_in_three_places():
    """The 0.8.0 cut shipped `requires-python >= 3.9` beside a streamlit floor
    whose own Requires-Python is >= 3.10 — the 3.9 leg failed at *install*, on
    the push to `main`, after the tag (#132). Three statements of the supported
    interpreters exist (`requires-python`, the trove classifiers, the ci.yml
    full matrix) and the classifier comment's mirror rule was prose. This makes
    it structural: the classifier set IS the full-matrix set, the floor is the
    smallest of them, and every leg satisfies the floor. The half a test cannot
    reach offline — whether the *dependencies'* Requires-Python admits the
    floor — is enforced by the full-matrix install on `main` being green, which
    is exactly where #132 surfaced."""
    with open(os.path.join(_ROOT, "pyproject.toml"), encoding="utf-8") as fh:
        pyproject = fh.read()
    floor = _REQ_PY.search(pyproject)
    assert floor, "pyproject.toml states no '>=' requires-python floor"
    floor_v = tuple(int(n) for n in floor.group(1).split("."))
    classifiers = {c for c in _CLASSIFIER.findall(pyproject) if c != "3"}

    ci = _read(_CI)
    lists = [
        {v.strip().strip('"') for v in m.group(1).split(",")}
        for m in _MATRIX_LIST.finditer(ci)
    ]
    versions = [vs for vs in lists if vs and all(v.startswith("3.") for v in vs)]
    assert versions, "no python-version matrix list parsed out of ci.yml"
    full = max(versions, key=len)  # the main-push list; PR legs are a subset

    assert classifiers == full, (
        f"the classifier set {sorted(classifiers)} is not the ci.yml full matrix "
        f"{sorted(full)} — the classifier list mirrors the matrix (pyproject's own "
        "comment); a classifier claiming an untested interpreter is #132's shape"
    )
    as_tuples = {tuple(int(n) for n in v.split(".")) for v in full}
    assert min(as_tuples) == floor_v, (
        f"requires-python >= {floor.group(1)} but the smallest tested leg is "
        f"{'.'.join(map(str, min(as_tuples)))} — the floor must be the smallest "
        "interpreter CI actually installs on"
    )


def test_the_dependency_ceiling_policy_rests_on_an_unpinned_install():
    """`pyproject.toml` states a runtime floor and deliberately **no** upper
    bound (#129). That decision is only safe because CI installs the runtime
    dependencies unpinned on every run, so an upstream release that removes a
    deprecated API -- `use_container_width` is documented for removal -- fails
    the GUI tests here before it reaches anyone's fresh install. A constraints
    file or a `streamlit==` in a workflow step would retire that early warning
    silently, leaving the "no ceiling" decision resting on nothing."""
    ci = _read(_CI)
    installs = [line.strip() for line in ci.splitlines()
                if "pip install" in line and "--upgrade pip" not in line
                and not line.lstrip().startswith("#")]
    assert installs, "no dependency install step found in ci.yml"
    for line in installs:
        assert re.search(r"-e '?\.", line), (
            f"ci.yml installs something other than this project: {line!r} -- the "
            "unpinned-install policy is stated in pyproject.toml's dependencies"
        )
        assert "-c " not in line and "--constraint" not in line, (
            f"ci.yml constrains the install ({line!r}); the ceiling policy in "
            "pyproject.toml assumes CI meets the newest releases first"
        )
    for pinned in ("streamlit==", "streamlit<", "pandas==", "plotly=="):
        assert pinned not in ci, (
            f"ci.yml pins {pinned!r}; a pinned CI is a CI that cannot warn about "
            "the upstream removal pyproject.toml's ceiling policy relies on it for"
        )


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
