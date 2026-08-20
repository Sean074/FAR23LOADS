#!/usr/bin/env bash
# Solo close loop, steps 3–7 — gate, commit, land, close, verify one item.
# DEVELOPMENT_PROCESS.md §0 (solo profile); the opening half is solo_start.sh.
#
# Usage: scripts/solo_close.sh [options] [<issue-number>] "<Subject>"
#
#   <issue-number>   OPTIONAL. Under the solo profile issues are optional (§0:
#                    "00_backlog.md is the record"); omit it and the script
#                    never calls `gh` — no auth check, no issue read, no close,
#                    no backlog_issues.py check (which needs gh to mean
#                    anything). Pass it when the item has an issue to close.
#   <Subject>        commit subject in the project style, WITHOUT the trailing
#                    parenthetical — the script appends
#                    "(backlog Pri N, tier X, YYYY-MM-DD)" (or "(issue #N, …)"
#                    when the fragment names no backlog row).
# Options:
#   --slug <slug>    changes/ fragment slug (default: the branch name after '/';
#                    REQUIRED when closing on main, which has no slug to take)
#   --suffix "<…>"   replace the generated parenthetical (e.g. to cite a note);
#                    a 'Pri N' and a YYYY-MM-DD inside it are honoured by the
#                    close comment and the commit date
#   --date <YYYY-MM-DD>  date for the parenthetical (default: today)
#   --full-gate      run the whole suite even for a docs-only change set
#   --skip-gate      do not re-run ruff/mypy/pytest (they were just run by hand)
#   --yes            no confirmation prompts
#   --dry-run        print the sequence; touch nothing
#
# The gate scales to the change set (§0). A **docs-only** change set — every
# path either *.md or under docs/ or changes/ — runs ruff, mypy and the five
# guard test files §0 names, in a few seconds instead of the whole suite; it
# also needs no branch, so it may be closed directly on `main`. Any other path
# (.py, fixtures, config) takes the full suite and a branch. --full-gate forces
# the suite; CI on the push to main is the gate either way.
#
# Preflight (nothing mutates until every check passes):
#   * on a <type>/<slug> branch — or on main with a docs-only change set
#   * changes/<slug>.<added|changed|fixed|removed|breaking>.md exists and its
#     lead names the tier; tier M/L also has changes/<slug>.history.md
#   * with an issue number only: `gh` authenticated; the issue is OPEN; and the
#     item's row is gone from the priority table (no "(#N)" left in
#     docs/30_future/00_backlog.md)
#   * origin/main has not diverged from HEAD (else: rebase / pull first)
#   * something to land: uncommitted changes, or the branch is ahead of main
# Steps:
#   3  gate    ruff · mypy · pytest (the CLAUDE.md merge gate, once, scaled)
#   4  commit  git add -A, show the list, confirm, one commit
#   5  land    checkout main, pull --ff-only, merge --ff-only, push
#   6  close   gh issue close N with the main SHA of record   (issue only)
#   7  verify  branch -d, backlog_issues.py check, issue state, last CI run
# The pre-commit/pre-push hooks are skipped for the commit and push made here
# because the identical gate ran in step 3 (SKIP=ruff,mypy / SKIP=pytest).
# Exit 0 on success; non-zero with the reason and the recovery on stderr.

set -euo pipefail

usage() {
  sed -n '2,56p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

# The five sub-second guard files DEVELOPMENT_PROCESS.md §0 names as the ones
# worth running on every docs/closure edit — this list IS the docs-only gate.
GUARD_TESTS=(
  tests/test_doc_currency.py
  tests/test_changelog_fragments.py
  tests/test_backlog_issues.py
  tests/test_schema_guards.py
  tests/test_workflow.py
)

SLUG=""; SUFFIX=""; DATE=""; SKIP_GATE=0; FULL_GATE=0; YES=0; DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --suffix) SUFFIX="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    --full-gate) FULL_GATE=1; shift ;;
    --skip-gate) SKIP_GATE=1; shift ;;
    --yes) YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) die "unknown option $1" ;;
    *) break ;;
  esac
done
[[ $# -eq 1 || $# -eq 2 ]] || { usage >&2; exit 2; }

if [[ $# -eq 2 ]]; then
  ISSUE="$1"; SUBJECT="$2"
  [[ "$ISSUE" =~ ^[0-9]+$ ]] || die "issue must be a number, got '$ISSUE' (omit it entirely to close without an issue)"
else
  ISSUE=""; SUBJECT="$1"
fi
[[ -n "$SUBJECT" ]] || die "subject must not be empty"

TODAY="${DATE:-$(date +%Y-%m-%d)}"
[[ "$TODAY" =~ ^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$ ]] || die "--date must be YYYY-MM-DD, got '$TODAY'"
# a date or a 'Pri N' inside --suffix is honoured (the fragment lead may omit them)
if [[ -n "$SUFFIX" ]]; then
  d="$(grep -o -m1 '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' <<<"$SUFFIX" || true)"; [[ -n "$d" ]] && TODAY="$d"
  SUFFIX_PRI="$(grep -o -m1 'Pri [0-9][0-9]*' <<<"$SUFFIX" | cut -d' ' -f2 || true)"
fi
SUFFIX_PRI="${SUFFIX_PRI:-}"

if [[ $DRY_RUN -eq 1 ]]; then
  LABEL="${ISSUE:+issue #$ISSUE}"
  [[ -n "$SLUG" ]] && LABEL="${LABEL:+$LABEL, }slug $SLUG"
  echo "solo_close --dry-run  (${LABEL:-no issue, slug from the branch}) — nothing executed"
  echo "  preflight: git rev-parse --abbrev-ref HEAD              <type>/<slug>, or main if docs-only"
  if [[ -n "$ISSUE" ]]; then
    echo "             gh auth status; gh issue view $ISSUE --json state == OPEN"
  else
    echo "             (no issue number — gh is not called in preflight, step 6 or step 7)"
  fi
  echo "             ls changes/<slug>.{added,changed,fixed,removed,breaking}.md   (tier in the lead)"
  echo "             ls changes/<slug>.history.md                   (tier M/L)"
  [[ -n "$ISSUE" ]] && echo "             grep -c \"(#$ISSUE)\" docs/30_future/00_backlog.md == 0"
  echo "             git fetch origin main; git merge-base --is-ancestor origin/main HEAD"
  echo "  step 3:    .venv/bin/ruff check sloads/ cli.py app/ scripts/"
  echo "             .venv/bin/mypy"
  echo "             .venv/bin/python -m pytest -q -p no:cacheprovider"
  echo "             a docs-only change set runs only: ${GUARD_TESTS[*]}"
  echo "  step 4:    git add -A && git status --short"
  echo "             SKIP=ruff,mypy git commit -m \"$SUBJECT (${SUFFIX:-backlog Pri N, tier X, $TODAY})\""
  echo "  step 5:    git checkout main && git pull --ff-only                (skipped when already on main)"
  echo "             git merge --ff-only <branch>                   (skipped when already on main)"
  echo "             SKIP=pytest git push origin main"
  if [[ -n "$ISSUE" ]]; then
    echo "  step 6:    gh issue close $ISSUE --reason completed --comment \"Closed by <sha> on main (tier X: changes/<slug>.<type>.md; row N removed from the priority table).\""
  else
    echo "  step 6:    (skipped — no issue number; 00_backlog.md is the record)"
  fi
  echo "  step 7:    git branch -d <branch>                          (skipped when closed on main)"
  if [[ -n "$ISSUE" ]]; then
    echo "             .venv/bin/python scripts/backlog_issues.py check"
    echo "             gh issue view $ISSUE --json state,number"
  fi
  echo "             gh run list --branch main --limit 1            (only if gh is available)"
  exit 0
fi

# ---- preflight ------------------------------------------------------------
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
cd "$ROOT_DIR"
PY="$ROOT_DIR/.venv/bin/python"
[[ -x "$PY" ]] || die "no .venv/bin/python — the gate needs the project venv"

git fetch origin main --quiet

# The change set: what this close will land, committed or not.
CHANGED="$(
  {
    git diff --name-only origin/main...HEAD 2>/dev/null || true
    git diff --name-only HEAD 2>/dev/null || true
    git ls-files --others --exclude-standard 2>/dev/null || true
  } | sed '/^$/d' | sort -u
)"

# Docs-only: every path is Markdown, or under docs/ or changes/. Anything else
# — .py, fixtures, config, this script — takes the full suite and a branch.
DOCS_ONLY=1
if [[ -z "$CHANGED" ]]; then
  DOCS_ONLY=0
else
  while IFS= read -r f; do
    case "$f" in
      *.md|docs/*|changes/*) ;;
      *) DOCS_ONLY=0; break ;;
    esac
  done <<<"$CHANGED"
fi
[[ $FULL_GATE -eq 1 ]] && DOCS_ONLY=0

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
ON_MAIN=0
if [[ "$BRANCH" == "main" ]]; then
  ON_MAIN=1
  [[ $DOCS_ONLY -eq 1 ]] || die "on main with a non-docs change set — open a branch (scripts/solo_start.sh <type>/<slug>); only a docs-only close may land straight on main"
  [[ -n "$SLUG" ]] || die "closing on main needs --slug <slug> (there is no branch name to take it from)"
else
  [[ "$BRANCH" =~ ^(chore|feat|fix|docs|note)/[a-z0-9][a-z0-9-]*$ ]] \
    || die "branch '$BRANCH' is not <type>/<slug>"
  [[ -n "$SLUG" ]] || SLUG="${BRANCH#*/}"
fi

if [[ -n "$ISSUE" ]]; then
  gh auth status >/dev/null 2>&1 || die "gh is not authenticated — run: gh auth login (or close without an issue number)"
  GH_ERR="$(mktemp)"
  STATE="$(gh issue view "$ISSUE" --json state -q .state 2>"$GH_ERR")" \
    || { cat "$GH_ERR" >&2; rm -f "$GH_ERR"; die "gh could not read issue #$ISSUE (see above — wrong number, or GitHub unavailable; retry)"; }
  rm -f "$GH_ERR"
  [[ "$STATE" == "OPEN" ]] || die "issue #$ISSUE is already $STATE — wrong number, or already closed"
fi

# closure artefacts
FRAG=""
for t in added changed fixed removed breaking; do
  if [[ -f "changes/$SLUG.$t.md" ]]; then FRAG="changes/$SLUG.$t.md"; break; fi
done
[[ -n "$FRAG" ]] || die "no changes/$SLUG.<added|changed|fixed|removed|breaking>.md — write the fragment (changes/README.md), or pass --slug"

TIER="$(grep -o -m1 'tier [SML]' "$FRAG" | head -1 | cut -d' ' -f2 || true)"
[[ -n "$TIER" ]] || die "$FRAG lead does not name the tier ('tier S|M|L' — see changes/README.md)"
PRI="$(grep -o -m1 'Pri [0-9][0-9]*' "$FRAG" | head -1 | cut -d' ' -f2 || true)"
[[ -n "$PRI" ]] || PRI="$SUFFIX_PRI"

HIST=""
if [[ "$TIER" != "S" ]]; then
  HIST="changes/$SLUG.history.md"
  [[ -f "$HIST" ]] || die "tier $TIER needs $HIST (changes/README.md; CLAUDE.md tier table)"
fi

if [[ -n "$ISSUE" ]] && grep -q "(#$ISSUE)" docs/30_future/00_backlog.md; then
  die "docs/30_future/00_backlog.md still carries (#$ISSUE) — delete the item's row (the row leaves in the closing commit)"
fi

# main untouched under us
if ! git merge-base --is-ancestor origin/main HEAD; then
  if [[ $ON_MAIN -eq 1 ]] && git merge-base --is-ancestor HEAD origin/main; then
    : # main is simply behind origin — step 5's pull --ff-only handles it
  else
    die "origin/main has moved past this branch — run: git stash && git rebase origin/main && git stash pop   (regenerate digests if they conflicted), then re-run"
  fi
fi

DIRTY=0
[[ -n "$(git status --porcelain)" ]] && DIRTY=1
AHEAD="$(git rev-list --count origin/main..HEAD)"
if [[ $DIRTY -eq 0 && "$AHEAD" -eq 0 ]]; then
  die "nothing to land: working tree clean and $BRANCH is not ahead of origin/main"
fi

if [[ -z "$SUFFIX" ]]; then
  if [[ -n "$PRI" ]]; then SUFFIX="backlog Pri $PRI, tier $TIER, $TODAY"
  elif [[ -n "$ISSUE" ]]; then SUFFIX="issue #$ISSUE, tier $TIER, $TODAY"
  else SUFFIX="tier $TIER, $TODAY"; fi
fi
MSG="$SUBJECT ($SUFFIX)"

echo "solo_close: ${ISSUE:+issue #$ISSUE · }branch $BRANCH · slug $SLUG · tier $TIER${PRI:+ · Pri $PRI}"
echo "            fragment $FRAG${HIST:+ + $HIST}"
if [[ $DOCS_ONLY -eq 1 ]]; then
  echo "            gate     docs-only change set — ruff · mypy · the guard files"
else
  echo "            gate     ruff · mypy · the whole suite"
fi
echo "            commit   \"$MSG\""

# ---- step 3: gate -----------------------------------------------------------
if [[ $SKIP_GATE -eq 0 ]]; then
  say "step 3 — gate (ruff · mypy · pytest)"
  run "$ROOT_DIR/.venv/bin/ruff" check sloads/ cli.py app/ scripts/ \
    || die "ruff failed — fix and re-run"
  run "$ROOT_DIR/.venv/bin/mypy" || die "mypy failed — fix and re-run"
  set +e
  if [[ $DOCS_ONLY -eq 1 ]]; then
    "$PY" -m pytest -q -p no:cacheprovider "${GUARD_TESTS[@]}" 2>&1 | tail -15
  else
    "$PY" -m pytest -q -p no:cacheprovider 2>&1 | tail -15
  fi
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
if [[ $ON_MAIN -eq 0 ]]; then
  run git checkout -q main
  run git pull --ff-only
  run git merge --ff-only "$BRANCH" \
    || die "fast-forward refused — main moved. Run: git checkout $BRANCH && git rebase main, then re-run"
else
  run git pull --rebase --autostash
fi
confirm "Push main to origin?"
SKIP=pytest run git push origin main
SHA="$(git rev-parse --short HEAD)"
run git log --oneline -1

# ---- step 6: close ----------------------------------------------------------
if [[ -n "$ISSUE" ]]; then
  say "step 6 — close issue #$ISSUE"
  COMMENT="Closed by $SHA on main (tier $TIER: $FRAG${HIST:+ + $HIST}"
  [[ -n "$PRI" ]] && COMMENT="$COMMENT; row $PRI removed from the priority table"
  COMMENT="$COMMENT)."
  run gh issue close "$ISSUE" --reason completed --comment "$COMMENT"
else
  say "step 6 — no issue to close (00_backlog.md is the record — §0)"
fi

# ---- step 7: verify ---------------------------------------------------------
say "step 7 — verify"
[[ $ON_MAIN -eq 0 ]] && run git branch -d "$BRANCH"
if [[ -n "$ISSUE" ]]; then
  run "$PY" scripts/backlog_issues.py check
  run gh issue view "$ISSUE" --json state,number -q '"#\(.number) \(.state)"'
fi
if gh auth status >/dev/null 2>&1; then
  run gh run list --branch main --limit 1
else
  echo "(gh unavailable — check CI yourself)"
fi

cat <<EOF

Done: ${ISSUE:+#$ISSUE closed by }$SHA on main. Watch CI with: gh run watch
EOF
