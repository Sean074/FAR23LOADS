#!/usr/bin/env bash
# Solo loop, steps 3–7 — gate, commit, push, close, verify ONE item on the
# milestone branch. DEVELOPMENT_PROCESS.md §0; the opening half is solo_start.sh.
#
# Usage: scripts/solo_close.sh --slug <slug> [options] [<issue-number>] "<Subject>"
#
#   --slug <slug>    REQUIRED. The changes/ fragment slug for this item. It is
#                    no longer derivable from the branch name: every item of a
#                    milestone is committed on the same `dev/vX.Y.Z` branch, so
#                    the branch identifies the milestone, not the item.
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
#   --suffix "<…>"   replace the generated parenthetical (e.g. to cite a note);
#                    a 'Pri N' and a YYYY-MM-DD inside it are honoured by the
#                    close comment and the commit date
#   --date <YYYY-MM-DD>  date for the parenthetical (default: today)
#   --full-gate      run the whole suite even for a docs-only change set
#   --skip-gate      do not re-run ruff/mypy/pytest (they were just run by hand)
#   --yes            no confirmation prompts
#   --dry-run        print the sequence; touch nothing
#
# This closes an item **in place on the milestone branch**: there is no
# checkout, no merge and no branch delete, because nothing lands on `main`
# except the milestone's single pull request at the end (§0). The item's issue
# closes and its priority-table row leaves in this commit, so the backlog stays
# a live view of what is still open mid-milestone.
#
# The gate still scales to the change set: a **docs-only** change set — every
# path either *.md or under docs/ or changes/ — runs ruff, mypy and the five
# guard test files §0 names, in a few seconds instead of the whole suite. Any
# other path (.py, fixtures, config) takes the full suite. --full-gate forces
# it. The push runs the fast gate on this branch, advisory; the gate of record
# is the full matrix on the milestone merge into main.
#
# Preflight (nothing mutates until every check passes):
#   * on the milestone branch (dev/vX.Y.Z) — never on main
#   * changes/<slug>.<added|changed|fixed|removed|breaking>.md exists and its
#     lead names the tier; tier M/L also has changes/<slug>.history.md
#   * with an issue number only: `gh` authenticated; the issue is OPEN; and the
#     item's row is gone from the priority table (no "(#N)" left in
#     docs/30_future/00_backlog.md)
#   * origin/<branch> has not moved past HEAD (else: pull --rebase first)
#   * something to land: uncommitted changes, or commits not yet pushed
# Steps:
#   3  gate    ruff · mypy · pytest (the CLAUDE.md merge gate, once, scaled)
#   4  commit  git add -A, show the list, confirm, one commit
#   5  push    git push origin <branch>
#   6  close   gh issue close N with the branch SHA of record   (issue only)
#   7  verify  backlog_issues.py check, issue state, last CI run on the branch
# The pre-commit/pre-push hooks are skipped for the commit and push made here
# because the identical gate ran in step 3 (SKIP=ruff,mypy / SKIP=pytest).
# Exit 0 on success; non-zero with the reason and the recovery on stderr.

set -euo pipefail

usage() {
  sed -n '2,62p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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
[[ -n "$SLUG" ]] || die "--slug <slug> is required (the milestone branch names the release, not the item)"

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
  echo "solo_close --dry-run  (${ISSUE:+issue #$ISSUE, }slug $SLUG) — nothing executed"
  echo "  preflight: git rev-parse --abbrev-ref HEAD              == dev/vX.Y.Z (never main)"
  if [[ -n "$ISSUE" ]]; then
    echo "             gh auth status; gh issue view $ISSUE --json state == OPEN"
  else
    echo "             (no issue number — gh is not called in preflight, step 6 or step 7)"
  fi
  echo "             ls changes/$SLUG.{added,changed,fixed,removed,breaking}.md   (tier in the lead)"
  echo "             ls changes/$SLUG.history.md                     (tier M/L)"
  [[ -n "$ISSUE" ]] && echo "             grep -c \"(#$ISSUE)\" docs/30_future/00_backlog.md == 0"
  echo "             git fetch origin <branch>; git merge-base --is-ancestor origin/<branch> HEAD"
  echo "  step 3:    .venv/bin/ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/"
  echo "             .venv/bin/mypy"
  echo "             .venv/bin/python -m pytest -q -p no:cacheprovider"
  echo "             a docs-only change set runs only: ${GUARD_TESTS[*]}"
  echo "  step 4:    git add -A && git status --short"
  echo "             SKIP=ruff,mypy git commit -m \"$SUBJECT (${SUFFIX:-backlog Pri N, tier X, $TODAY})\""
  echo "  step 5:    SKIP=pytest git push origin <branch>"
  if [[ -n "$ISSUE" ]]; then
    echo "  step 6:    gh issue close $ISSUE --reason completed --comment \"Closed by <sha> on <branch> (tier X: changes/$SLUG.<type>.md; row N removed from the priority table).\""
  else
    echo "  step 6:    (skipped — no issue number; 00_backlog.md is the record)"
  fi
  if [[ -n "$ISSUE" ]]; then
    echo "  step 7:    .venv/bin/python scripts/backlog_issues.py check"
    echo "             gh issue view $ISSUE --json state,number"
  fi
  echo "             gh run list --branch <branch> --limit 1        (only if gh is available)"
  exit 0
fi

# ---- preflight ------------------------------------------------------------
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
cd "$ROOT_DIR"
PY="$ROOT_DIR/.venv/bin/python"
[[ -x "$PY" ]] || die "no .venv/bin/python — the gate needs the project venv"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" == "main" ]]; then
  die "on main — nothing is closed on main any more. Items are committed on the
milestone branch (scripts/solo_start.sh dev/vX.Y.Z), and main only ever receives
the milestone's single pull request (DEVELOPMENT_PROCESS.md §0)."
fi
[[ "$BRANCH" =~ ^dev/v[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || die "branch '$BRANCH' is not a milestone branch 'dev/vX.Y.Z' — run: git checkout dev/v<X.Y.Z>"

# Has this branch been pushed yet? The first item of a milestone may close
# before origin has the branch.
HAS_REMOTE=0
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  HAS_REMOTE=1
  git fetch origin "$BRANCH" --quiet
fi

# The change set: what this close will land — uncommitted work plus anything
# committed on this branch but not yet pushed. (Not `origin/main...HEAD`: on a
# milestone branch that is every item closed so far.)
BASE=""
[[ $HAS_REMOTE -eq 1 ]] && BASE="origin/$BRANCH"
CHANGED="$(
  {
    [[ -n "$BASE" ]] && { git diff --name-only "$BASE"...HEAD 2>/dev/null || true; }
    git diff --name-only HEAD 2>/dev/null || true
    git ls-files --others --exclude-standard 2>/dev/null || true
  } | sed '/^$/d' | sort -u
)"

# Docs-only: every path is Markdown, or under docs/ or changes/. Anything else
# — .py, fixtures, config, this script — takes the full suite. This decides the
# gate SIZE only; it no longer decides where the item is closed.
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
[[ -n "$FRAG" ]] || die "no changes/$SLUG.<added|changed|fixed|removed|breaking>.md — write the fragment (changes/README.md), or check --slug"

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

# the branch untouched under us
if [[ $HAS_REMOTE -eq 1 ]] && ! git merge-base --is-ancestor "origin/$BRANCH" HEAD; then
  die "origin/$BRANCH has moved past this checkout — run: git pull --rebase --autostash, then re-run"
fi

DIRTY=0
[[ -n "$(git status --porcelain)" ]] && DIRTY=1
AHEAD=0
[[ $HAS_REMOTE -eq 1 ]] && AHEAD="$(git rev-list --count "origin/$BRANCH..HEAD")"
if [[ $DIRTY -eq 0 && "$AHEAD" -eq 0 ]]; then
  die "nothing to land: working tree clean and $BRANCH is not ahead of origin/$BRANCH"
fi

if [[ -z "$SUFFIX" ]]; then
  if [[ -n "$PRI" ]]; then SUFFIX="backlog Pri $PRI, tier $TIER, $TODAY"
  elif [[ -n "$ISSUE" ]]; then SUFFIX="issue #$ISSUE, tier $TIER, $TODAY"
  else SUFFIX="tier $TIER, $TODAY"; fi
fi
MSG="$SUBJECT ($SUFFIX)"

echo "solo_close: ${ISSUE:+issue #$ISSUE · }milestone $BRANCH · slug $SLUG · tier $TIER${PRI:+ · Pri $PRI}"
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
  run "$ROOT_DIR/.venv/bin/ruff" check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/ \
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
  say "step 4 — nothing uncommitted; pushing the $AHEAD commit(s) already on $BRANCH"
  git log --oneline "origin/$BRANCH..HEAD"
  confirm "Push these?"
fi

# ---- step 5: push -----------------------------------------------------------
say "step 5 — push $BRANCH"
confirm "Push $BRANCH to origin?"
if [[ $HAS_REMOTE -eq 1 ]]; then
  SKIP=pytest run git push origin "$BRANCH"
else
  SKIP=pytest run git push -u origin "$BRANCH"
fi
SHA="$(git rev-parse --short HEAD)"
run git log --oneline -1

# ---- step 6: close ----------------------------------------------------------
if [[ -n "$ISSUE" ]]; then
  say "step 6 — close issue #$ISSUE"
  COMMENT="Closed by $SHA on $BRANCH (tier $TIER: $FRAG${HIST:+ + $HIST}"
  [[ -n "$PRI" ]] && COMMENT="$COMMENT; row $PRI removed from the priority table"
  COMMENT="$COMMENT). Reaches main with the $BRANCH milestone pull request."
  run gh issue close "$ISSUE" --reason completed --comment "$COMMENT"
else
  say "step 6 — no issue to close (00_backlog.md is the record — §0)"
fi

# ---- step 7: verify ---------------------------------------------------------
say "step 7 — verify"
if [[ -n "$ISSUE" ]]; then
  run "$PY" scripts/backlog_issues.py check
  run gh issue view "$ISSUE" --json state,number -q '"#\(.number) \(.state)"'
fi
if gh auth status >/dev/null 2>&1; then
  run gh run list --branch "$BRANCH" --limit 1
else
  echo "(gh unavailable — check CI yourself)"
fi

cat <<EOF

Done: ${ISSUE:+#$ISSUE closed by }$SHA on $BRANCH. The fast gate is running there
(advisory): gh run watch. Next item: work it on this same branch.
EOF
