#!/usr/bin/env bash
# Solo loop, step 1 — open the MILESTONE branch for a release.
# DEVELOPMENT_PROCESS.md §0 (solo profile); the per-item half is solo_close.sh.
#
# Usage: scripts/solo_start.sh [--dry-run] dev/v<X.Y.Z>
#
#   dev/v<X.Y.Z>   the milestone branch, opened off `main` ONCE per release.
#                  Every item of that milestone is then worked and committed
#                  directly on it — there is no per-item branch and no per-item
#                  `solo_start`. The milestone lands on `main` as one pull
#                  request, rebase-merged (§0 — main enforces linear history),
#                  and the release is cut on
#                  this branch, so there is no separate `release/x.y.z` either.
#
# Preflight (nothing mutates until every check passes):
#   * run from inside the repo
#   * on `main` with a clean working tree
#   * the branch does not already exist
#
# Then: `git pull --ff-only`, `git checkout -b <branch>`, `git push -u origin`,
# and print what the milestone loop is.
#
# `gh` is never called here: the issue set is opened once, by hand or by
# `scripts/backlog_issues.py`, when the milestone is scoped — not at branch
# time. Per item, the `gh` work belongs to solo_close.sh.
#
# --dry-run prints the sequence and exits without touching git.
# Exit 0 on success; non-zero with the reason (and the recovery) on stderr.

set -euo pipefail

usage() {
  sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() { printf 'solo_start: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }
run() { printf '$ %s\n' "$*"; "$@"; }

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=1; shift; fi
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
[[ $# -eq 1 ]] || { usage >&2; exit 2; }

BRANCH="$1"

# `dev/` plus a version — dots allowed, which is why this is not the old
# <type>/<kebab-slug> pattern. A per-item branch name is a mistake now, so the
# refusal names the model rather than the regex.
[[ "$BRANCH" =~ ^dev/v[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || die "expected a milestone branch 'dev/vX.Y.Z', got '$BRANCH'. Items are no
longer worked on their own branches — commit them directly on the milestone
branch and close each with scripts/solo_close.sh (DEVELOPMENT_PROCESS.md §0)."

MILESTONE="${BRANCH#dev/}"

if [[ $DRY_RUN -eq 1 ]]; then
  echo "solo_start --dry-run  (milestone branch $BRANCH) — nothing executed"
  echo "  preflight: git rev-parse --show-toplevel"
  echo "             git rev-parse --abbrev-ref HEAD            == main"
  echo "             git status --porcelain                     == (empty)"
  echo "             git rev-parse --verify $BRANCH             (must NOT exist)"
  echo "  step 1:    git pull --ff-only"
  echo "             git checkout -b $BRANCH"
  echo "             git push -u origin $BRANCH"
  echo "             git status --short && git log --oneline -1"
  echo "  next:      scope the milestone (issues labelled band:*, milestone $MILESTONE),"
  echo "             then per item: work + closure artefacts, and"
  echo "             scripts/solo_close.sh --slug <slug> [<issue>] \"<Subject>\""
  exit 0
fi

# ---- preflight ------------------------------------------------------------
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
cd "$ROOT_DIR"

CUR="$(git rev-parse --abbrev-ref HEAD)"
[[ "$CUR" == "main" ]] || die "on branch '$CUR', not main — run: git checkout main"

if [[ -n "$(git status --porcelain)" ]]; then
  git status --short >&2
  die "working tree is not clean — commit, stash (git stash) or discard first"
fi

if git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  die "branch '$BRANCH' already exists — run: git checkout $BRANCH (the milestone branch is opened once)"
fi

# ---- step 1 ---------------------------------------------------------------
say "step 1 — milestone branch $BRANCH"
run git pull --ff-only
run git checkout -b "$BRANCH"
run git push -u origin "$BRANCH"
run git status --short
run git log --oneline -1

cat <<EOF

On $BRANCH — the milestone branch for $MILESTONE. It stays open until the
milestone is done; every item commits straight onto it.

  scope     open the issues for this milestone (labels tier:*, tag:*, band:*,
            kind:*; milestone $MILESTONE) and keep their rows in the priority
            table of docs/30_future/00_backlog.md
  per item  do the work + the closure artefacts for the tier —
              fragment   changes/<slug>.<added|changed|fixed|removed|breaking>.md
                         (tier M/L also changes/<slug>.history.md)
              backlog    delete that item's row from the priority table
            then:

              scripts/solo_close.sh --slug <slug> [<issue>] "<Subject>"

            Each push runs the fast gate on this branch — advisory, nothing
            waits on it.
  finish    when the milestone is empty, cut the release ON this branch
            (RELEASE_PROCESS.md §4), then open ONE pull request into main and
            rebase-merge it (gh pr merge --rebase; main enforces linear
            history, so a merge commit is refused and a squash would lose
            the per-item record). That push to main runs the full matrix;
            tag from main, then delete this branch (rebase rewrote its SHAs).
EOF
