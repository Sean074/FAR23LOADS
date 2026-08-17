#!/usr/bin/env bash
# Solo close loop, steps 3–7 — gate, commit, land, close, verify one item.
# DEVELOPMENT_PROCESS.md §0 (solo profile); the opening half is solo_start.sh.
#
# Usage: scripts/solo_close.sh [options] <issue-number> "<Subject>"
#
#   <Subject>        commit subject in the project style, WITHOUT the trailing
#                    parenthetical — the script appends
#                    "(backlog Pri N, tier X, YYYY-MM-DD)" (or "(issue #N, …)"
#                    when the fragment names no backlog row).
# Options:
#   --slug <slug>    changes/ fragment slug (default: the branch name after '/')
#   --suffix "<…>"   replace the generated parenthetical (e.g. to cite a note)
#   --skip-gate      do not re-run ruff/mypy/pytest (they were just run by hand)
#   --yes            no confirmation prompts
#   --dry-run        print the sequence; touch nothing
#
# Preflight (nothing mutates until every check passes):
#   * on a <type>/<slug> branch (not main); `gh` authenticated; issue OPEN
#   * changes/<slug>.<added|changed|fixed|removed|breaking>.md exists and its
#     lead names the tier; tier M/L also has changes/<slug>.history.md
#   * the item's row is gone from the priority table (no "(#N)" left in
#     docs/30_future/00_backlog.md)
#   * origin/main is an ancestor of HEAD (else: rebase first)
#   * something to land: uncommitted changes, or the branch is ahead of main
# Steps:
#   3  gate    ruff · mypy · pytest (the CLAUDE.md merge gate, once)
#   4  commit  git add -A, show the list, confirm, one commit
#   5  land    checkout main, pull --ff-only, merge --ff-only, push
#   6  close   gh issue close N with the main SHA of record
#   7  verify  branch -d, backlog_issues.py check, issue state, last CI run
# The pre-commit/pre-push hooks are skipped for the commit and push made here
# because the identical gate ran in step 3 (SKIP=ruff,mypy / SKIP=pytest).
# Exit 0 on success; non-zero with the reason and the recovery on stderr.

set -euo pipefail

usage() {
  sed -n '2,36p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() { printf 'solo_close: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }
run() { printf '$ %s\n' "$*"; "$@"; }
confirm() {
  [[ $YES -eq 1 ]] && return 0
  local ans
  read -r -p "$1 [y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]] || die "stopped at your request (nothing after this point ran)"
}

SLUG=""; SUFFIX=""; SKIP_GATE=0; YES=0; DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --suffix) SUFFIX="$2"; shift 2 ;;
    --skip-gate) SKIP_GATE=1; shift ;;
    --yes) YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) die "unknown option $1" ;;
    *) break ;;
  esac
done
[[ $# -eq 2 ]] || { usage >&2; exit 2; }
ISSUE="$1"; SUBJECT="$2"
[[ "$ISSUE" =~ ^[0-9]+$ ]] || die "issue must be a number, got '$ISSUE'"
[[ -n "$SUBJECT" ]] || die "subject must not be empty"

TODAY="$(date +%Y-%m-%d)"

if [[ $DRY_RUN -eq 1 ]]; then
  cat <<EOF
solo_close --dry-run  (issue #$ISSUE) — nothing executed
  preflight: git rev-parse --abbrev-ref HEAD              != main, matches <type>/<slug>
             gh auth status; gh issue view $ISSUE --json state == OPEN
             ls changes/<slug>.{added,changed,fixed,removed,breaking}.md   (tier in the lead)
             ls changes/<slug>.history.md                   (tier M/L)
             grep -c "(#$ISSUE)" docs/30_future/00_backlog.md == 0
             git fetch origin main; git merge-base --is-ancestor origin/main HEAD
  step 3:    .venv/bin/ruff check sloads/ cli.py app/ scripts/
             .venv/bin/mypy
             .venv/bin/python -m pytest -q -p no:cacheprovider
  step 4:    git add -A && git status --short
             SKIP=ruff,mypy git commit -m "$SUBJECT (backlog Pri N, tier X, $TODAY)"
  step 5:    git checkout main && git pull --ff-only
             git merge --ff-only <branch>
             SKIP=pytest git push origin main
  step 6:    gh issue close $ISSUE --reason completed --comment "Closed by <sha> on main (tier X: changes/<slug>.<type>.md; row N removed from the priority table)."
  step 7:    git branch -d <branch>
             .venv/bin/python scripts/backlog_issues.py check
             gh issue view $ISSUE --json state,number
             gh run list --branch main --limit 1
EOF
  exit 0
fi

# ---- preflight ------------------------------------------------------------
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
cd "$ROOT_DIR"
PY="$ROOT_DIR/.venv/bin/python"
[[ -x "$PY" ]] || die "no .venv/bin/python — the gate needs the project venv"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" != "main" ]] || die "on main — close from the item's branch (scripts/solo_start.sh)"
[[ "$BRANCH" =~ ^(chore|feat|fix|docs|note)/[a-z0-9][a-z0-9-]*$ ]] \
  || die "branch '$BRANCH' is not <type>/<slug>"
[[ -n "$SLUG" ]] || SLUG="${BRANCH#*/}"

gh auth status >/dev/null 2>&1 || die "gh is not authenticated — run: gh auth login"
STATE="$(gh issue view "$ISSUE" --json state -q .state 2>/dev/null)" \
  || die "issue #$ISSUE not found"
[[ "$STATE" == "OPEN" ]] || die "issue #$ISSUE is already $STATE — wrong number, or already closed"

# closure artefacts
FRAG=""
for t in added changed fixed removed breaking; do
  if [[ -f "changes/$SLUG.$t.md" ]]; then FRAG="changes/$SLUG.$t.md"; break; fi
done
[[ -n "$FRAG" ]] || die "no changes/$SLUG.<added|changed|fixed|removed|breaking>.md — write the fragment (changes/README.md), or pass --slug"

TIER="$(grep -o -m1 'tier [SML]' "$FRAG" | head -1 | cut -d' ' -f2 || true)"
[[ -n "$TIER" ]] || die "$FRAG lead does not name the tier ('tier S|M|L' — see changes/README.md)"
PRI="$(grep -o -m1 'Pri [0-9][0-9]*' "$FRAG" | head -1 | cut -d' ' -f2 || true)"

HIST=""
if [[ "$TIER" != "S" ]]; then
  HIST="changes/$SLUG.history.md"
  [[ -f "$HIST" ]] || die "tier $TIER needs $HIST (changes/README.md; CLAUDE.md tier table)"
fi

if grep -q "(#$ISSUE)" docs/30_future/00_backlog.md; then
  die "docs/30_future/00_backlog.md still carries (#$ISSUE) — delete the item's row (the row leaves in the closing commit)"
fi

# main untouched under us
git fetch origin main --quiet
if ! git merge-base --is-ancestor origin/main HEAD; then
  die "origin/main has moved past this branch — run: git stash && git rebase origin/main && git stash pop   (regenerate digests if they conflicted), then re-run"
fi

DIRTY=0
[[ -n "$(git status --porcelain)" ]] && DIRTY=1
AHEAD="$(git rev-list --count origin/main..HEAD)"
if [[ $DIRTY -eq 0 && "$AHEAD" -eq 0 ]]; then
  die "nothing to land: working tree clean and $BRANCH is not ahead of origin/main"
fi

if [[ -z "$SUFFIX" ]]; then
  if [[ -n "$PRI" ]]; then SUFFIX="backlog Pri $PRI, tier $TIER, $TODAY"
  else SUFFIX="issue #$ISSUE, tier $TIER, $TODAY"; fi
fi
MSG="$SUBJECT ($SUFFIX)"

echo "solo_close: issue #$ISSUE · branch $BRANCH · slug $SLUG · tier $TIER${PRI:+ · Pri $PRI}"
echo "            fragment $FRAG${HIST:+ + $HIST}"
echo "            commit   \"$MSG\""

# ---- step 3: gate -----------------------------------------------------------
if [[ $SKIP_GATE -eq 0 ]]; then
  say "step 3 — gate (ruff · mypy · pytest)"
  run "$ROOT_DIR/.venv/bin/ruff" check sloads/ cli.py app/ scripts/ \
    || die "ruff failed — fix and re-run"
  run "$ROOT_DIR/.venv/bin/mypy" || die "mypy failed — fix and re-run"
  set +e
  "$PY" -m pytest -q -p no:cacheprovider 2>&1 | tail -15
  RC=${PIPESTATUS[0]}
  set -e
  if [[ $RC -ne 0 ]]; then
    cat >&2 <<EOF
solo_close: pytest failed. Known closure-time causes:
  test_backlog_issues (render round-trip) — a table row without '(#N)' (parentheses!)
  test_changelog_fragments               — fragment name/body not in changes/README.md form
  test_schema_guards / digests           — SCHEMA_VERSION or digest not re-pinned
  test_doc_currency                      — a number copied into a standard doc
Fix, then re-run (add --skip-gate only if you re-ran the full gate by hand).
EOF
    exit 1
  fi
else
  say "step 3 — gate skipped (--skip-gate)"
fi

# ---- step 4: commit ---------------------------------------------------------
if [[ $DIRTY -eq 1 ]]; then
  say "step 4 — commit"
  run git add -A
  git status --short
  confirm "Commit the files above as: \"$MSG\"?"
  SKIP=ruff,mypy run git commit -q -m "$MSG"
  run git log --oneline -1
else
  say "step 4 — nothing uncommitted; landing the $AHEAD commit(s) already on $BRANCH"
  git log --oneline "origin/main..HEAD"
  confirm "Land these on main?"
fi

# ---- step 5: land -----------------------------------------------------------
say "step 5 — land on main"
run git checkout -q main
run git pull --ff-only
run git merge --ff-only "$BRANCH" \
  || die "fast-forward refused — main moved. Run: git checkout $BRANCH && git rebase main, then re-run"
confirm "Push main to origin?"
SKIP=pytest run git push origin main
SHA="$(git rev-parse --short HEAD)"
run git log --oneline -1

# ---- step 6: close ----------------------------------------------------------
say "step 6 — close issue #$ISSUE"
COMMENT="Closed by $SHA on main (tier $TIER: $FRAG${HIST:+ + $HIST}"
[[ -n "$PRI" ]] && COMMENT="$COMMENT; row $PRI removed from the priority table"
COMMENT="$COMMENT)."
run gh issue close "$ISSUE" --reason completed --comment "$COMMENT"

# ---- step 7: verify ---------------------------------------------------------
say "step 7 — verify"
run git branch -d "$BRANCH"
run "$PY" scripts/backlog_issues.py check
run gh issue view "$ISSUE" --json state,number -q '"#\(.number) \(.state)"'
run gh run list --branch main --limit 1

cat <<EOF

Done: #$ISSUE closed by $SHA. Watch CI with: gh run watch
EOF
