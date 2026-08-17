#!/usr/bin/env bash
# Solo close loop, step 1 — open the branch for one backlog item / issue.
# DEVELOPMENT_PROCESS.md §0 (solo profile); the closing half is solo_close.sh.
#
# Usage: scripts/solo_start.sh [--dry-run] <issue-number> <type>/<slug>
#
#   <issue-number>  the open GitHub issue the work closes (open work is issues)
#   <type>/<slug>   branch name; type in chore | feat | fix | docs | note
#                   (chore = tier S hygiene, feat/fix = tier M/L work, note =
#                   design-note-only branch)
#
# Preflight (nothing mutates until every check passes):
#   * run from inside the repo; `gh` authenticated
#   * on `main` with a clean working tree
#   * the issue exists and is OPEN
#   * the branch does not already exist
# Then: `git pull --ff-only`, `git checkout -b <branch>`, print status + HEAD.
#
# --dry-run prints the sequence and exits without touching git or gh.
# Exit 0 on success; non-zero with the reason (and the recovery) on stderr.

set -euo pipefail

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() { printf 'solo_start: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }
run() { printf '$ %s\n' "$*"; "$@"; }

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=1; shift; fi
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
[[ $# -eq 2 ]] || { usage >&2; exit 2; }

ISSUE="$1"
BRANCH="$2"

[[ "$ISSUE" =~ ^[0-9]+$ ]] || die "issue must be a number, got '$ISSUE'"
[[ "$BRANCH" =~ ^(chore|feat|fix|docs|note)/[a-z0-9][a-z0-9-]*$ ]] \
  || die "branch must be <type>/<kebab-slug> with type in chore|feat|fix|docs|note, got '$BRANCH'"

if [[ $DRY_RUN -eq 1 ]]; then
  cat <<EOF
solo_start --dry-run  (issue #$ISSUE, branch $BRANCH) — nothing executed
  preflight: git rev-parse --show-toplevel
             gh auth status
             git rev-parse --abbrev-ref HEAD            == main
             git status --porcelain                     == (empty)
             gh issue view $ISSUE --json state          == OPEN
             git rev-parse --verify $BRANCH             (must NOT exist)
  step 1:    git pull --ff-only
             git checkout -b $BRANCH
             git status --short && git log --oneline -1
  next:      do the work + the closure artefacts (CLAUDE.md tier table):
             changes/${BRANCH#*/}.<type>.md (the name solo_close.sh expects), then
             scripts/solo_close.sh $ISSUE "<Subject>"
EOF
  exit 0
fi

# ---- preflight ------------------------------------------------------------
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
cd "$ROOT_DIR"

gh auth status >/dev/null 2>&1 || die "gh is not authenticated — run: gh auth login"

CUR="$(git rev-parse --abbrev-ref HEAD)"
[[ "$CUR" == "main" ]] || die "on branch '$CUR', not main — run: git checkout main"

if [[ -n "$(git status --porcelain)" ]]; then
  git status --short >&2
  die "working tree is not clean — commit, stash (git stash) or discard first"
fi

GH_ERR="$(mktemp)"
STATE="$(gh issue view "$ISSUE" --json state -q .state 2>"$GH_ERR")" \
  || { cat "$GH_ERR" >&2; rm -f "$GH_ERR"; die "gh could not read issue #$ISSUE (see above — not created yet, wrong number, or GitHub unavailable; retry)"; }
rm -f "$GH_ERR"
[[ "$STATE" == "OPEN" ]] || die "issue #$ISSUE is $STATE, not OPEN"

if git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  die "branch '$BRANCH' already exists — run: git checkout $BRANCH (or pick another slug)"
fi

# ---- step 1 ---------------------------------------------------------------
say "step 1 — branch for issue #$ISSUE"
run git pull --ff-only
run git checkout -b "$BRANCH"
run git status --short
run git log --oneline -1

cat <<EOF

On $BRANCH. Now: the work + the closure artefacts for the tier —
  fragment   changes/${BRANCH#*/}.<added|changed|fixed|removed|breaking>.md
             (this is the name solo_close.sh will look for; lead carries
             '(backlog Pri N, tier X, YYYY-MM-DD)'; tier M/L also
             changes/${BRANCH#*/}.history.md)
  backlog    delete the item's (#$ISSUE) row from the priority table
Then:

  scripts/solo_close.sh $ISSUE "<Subject in the project style>"
EOF
