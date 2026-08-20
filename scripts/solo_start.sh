#!/usr/bin/env bash
# Solo close loop, step 1 — open the branch for one backlog item / issue.
# DEVELOPMENT_PROCESS.md §0 (solo profile); the closing half is solo_close.sh.
#
# Usage: scripts/solo_start.sh [--dry-run] [<issue-number>] <type>/<slug>
#
#   <issue-number>  OPTIONAL. The open GitHub issue the work closes. Under the
#                   solo profile issues are optional (§0: "00_backlog.md is the
#                   record"); omit it and the script never calls `gh`.
#   <type>/<slug>   branch name; type in chore | feat | fix | docs | note
#                   (chore = tier S hygiene, feat/fix = tier M/L work, note =
#                   design-note-only branch)
#
# Preflight (nothing mutates until every check passes):
#   * run from inside the repo
#   * on `main` with a clean working tree
#   * the branch does not already exist
#   * with an issue number only: `gh` authenticated, and the issue is OPEN
# Then: `git pull --ff-only`, `git checkout -b <branch>`, print status + HEAD.
#
# A docs-only change needs no branch at all — edit on `main` and close with
# `scripts/solo_close.sh --slug <slug> "<Subject>"` (§0).
#
# --dry-run prints the sequence and exits without touching git or gh.
# Exit 0 on success; non-zero with the reason (and the recovery) on stderr.

set -euo pipefail

usage() {
  sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() { printf 'solo_start: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }
run() { printf '$ %s\n' "$*"; "$@"; }

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=1; shift; fi
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
[[ $# -eq 1 || $# -eq 2 ]] || { usage >&2; exit 2; }

if [[ $# -eq 2 ]]; then
  ISSUE="$1"; BRANCH="$2"
  [[ "$ISSUE" =~ ^[0-9]+$ ]] || die "issue must be a number, got '$ISSUE' (omit it entirely to work without an issue)"
else
  ISSUE=""; BRANCH="$1"
fi

[[ "$BRANCH" =~ ^(chore|feat|fix|docs|note)/[a-z0-9][a-z0-9-]*$ ]] \
  || die "branch must be <type>/<kebab-slug> with type in chore|feat|fix|docs|note, got '$BRANCH'"

SLUG="${BRANCH#*/}"

if [[ $DRY_RUN -eq 1 ]]; then
  echo "solo_start --dry-run  (${ISSUE:+issue #$ISSUE, }branch $BRANCH) — nothing executed"
  echo "  preflight: git rev-parse --show-toplevel"
  [[ -n "$ISSUE" ]] && echo "             gh auth status"
  echo "             git rev-parse --abbrev-ref HEAD            == main"
  echo "             git status --porcelain                     == (empty)"
  if [[ -n "$ISSUE" ]]; then
    echo "             gh issue view $ISSUE --json state          == OPEN"
  else
    echo "             (no issue number — gh is not called at all)"
  fi
  echo "             git rev-parse --verify $BRANCH             (must NOT exist)"
  echo "  step 1:    git pull --ff-only"
  echo "             git checkout -b $BRANCH"
  echo "             git status --short && git log --oneline -1"
  echo "  next:      do the work + the closure artefacts (CLAUDE.md tier table):"
  echo "             changes/$SLUG.<type>.md (the name solo_close.sh expects), then"
  echo "             scripts/solo_close.sh ${ISSUE:+$ISSUE }\"<Subject>\""
  exit 0
fi

# ---- preflight ------------------------------------------------------------
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
cd "$ROOT_DIR"

if [[ -n "$ISSUE" ]]; then
  gh auth status >/dev/null 2>&1 || die "gh is not authenticated — run: gh auth login (or omit the issue number)"
fi

CUR="$(git rev-parse --abbrev-ref HEAD)"
[[ "$CUR" == "main" ]] || die "on branch '$CUR', not main — run: git checkout main"

if [[ -n "$(git status --porcelain)" ]]; then
  git status --short >&2
  die "working tree is not clean — commit, stash (git stash) or discard first"
fi

if [[ -n "$ISSUE" ]]; then
  GH_ERR="$(mktemp)"
  STATE="$(gh issue view "$ISSUE" --json state -q .state 2>"$GH_ERR")" \
    || { cat "$GH_ERR" >&2; rm -f "$GH_ERR"; die "gh could not read issue #$ISSUE (see above — not created yet, wrong number, or GitHub unavailable; retry)"; }
  rm -f "$GH_ERR"
  [[ "$STATE" == "OPEN" ]] || die "issue #$ISSUE is $STATE, not OPEN"
fi

if git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  die "branch '$BRANCH' already exists — run: git checkout $BRANCH (or pick another slug)"
fi

# ---- step 1 ---------------------------------------------------------------
say "step 1 — branch${ISSUE:+ for issue #$ISSUE}"
run git pull --ff-only
run git checkout -b "$BRANCH"
run git status --short
run git log --oneline -1

cat <<EOF

On $BRANCH. Now: the work + the closure artefacts for the tier —
  fragment   changes/$SLUG.<added|changed|fixed|removed|breaking>.md
             (this is the name solo_close.sh will look for; lead carries
             '(backlog Pri N, tier X, YYYY-MM-DD)'; tier M/L also
             changes/$SLUG.history.md)
  backlog    delete the item's ${ISSUE:+(#$ISSUE) }row from the priority table
Then:

  scripts/solo_close.sh ${ISSUE:+$ISSUE }"<Subject in the project style>"
EOF
