#!/usr/bin/env bash
# GUI/CLI smoke test — RELEASE_PROCESS.md §3.5.
#
# 1. Starts the main GUI (app/Home.py) headless, waits for it to come up, and
#    checks the root page answers 200 with no traceback in the server log.
# 2. Does the same for the oracle GUI (oracle_app/Oracle.py) — launched through
#    the `sloads-oracle` console script, so the packaging entry point is run and
#    not merely resolved.
# 3. Runs the CLI "engine" module against the ga6_normal example and checks
#    the CSV it writes is non-empty with the expected header.
#
# **Both front-ends, because there are two** (#127). The release whose headline
# deliverable is the oracle GUI had a hard §3.5 gate that booted only the other
# one. In-process AppTest coverage coincidentally reaches Oracle.py's
# set_page_config, st.navigation and sidebar context manager; what only a real
# server reaches is the boot itself, and what only this reaches is the console
# script a user actually types.
#
# Usage: scripts/smoke_test.sh
# Exit 0 on success; non-zero (with a message on stderr) on the first failure.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Resolve the interpreter: honour an explicit PYTHON override, else prefer the
# project .venv when present, else fall back to whatever python is on PATH. All
# tooling runs through this one interpreter (python -m streamlit / cli.py) so
# the smoke test no longer assumes a .venv-shaped install layout.
PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON="$ROOT_DIR/.venv/bin/python"
  else
    PYTHON="$(command -v python3 || command -v python || true)"
  fi
fi
PROJECT="$ROOT_DIR/examples/ga6_normal.project.json"

# The GUI entry points this gate boots, one per front-end. RELEASE_PROCESS.md
# §3.5 names the same two, and tests/test_ci_conformance.py compares the lists:
# a third front-end that never reaches this line is a front-end no release gate
# starts (the defect class that file exists for).
GUI_ENTRY_POINTS=("app/Home.py" "oracle_app/Oracle.py")

if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
  echo "smoke_test: no usable Python interpreter (set \$PYTHON or install python3)" >&2
  exit 1
fi
if ! "$PYTHON" -c 'import streamlit, sloads' >/dev/null 2>&1; then
  echo "smoke_test: streamlit/sloads not importable by $PYTHON — run 'pip install -e .[dev]' first" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
OUT_CSV="$TMP_DIR/out.csv"
STREAMLIT_PID=""

cleanup() {
  if [[ -n "$STREAMLIT_PID" ]] && kill -0 "$STREAMLIT_PID" 2>/dev/null; then
    kill "$STREAMLIT_PID" 2>/dev/null || true
    wait "$STREAMLIT_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# Resolve the oracle launcher the way a user meets it: the console script
# `pyproject.toml` binds to `oracle:main`, taken from the interpreter's own bin
# directory so it matches $PYTHON, then from PATH. A source checkout with no
# install still has `python oracle.py`, which is the same entry point one hop
# earlier -- the fallback keeps the gate runnable, and says which it took.
ORACLE_BIN="$(dirname "$PYTHON")/sloads-oracle"
if [[ -x "$ORACLE_BIN" ]]; then
  ORACLE_LAUNCH=("$ORACLE_BIN")
  ORACLE_HOW="the sloads-oracle console script"
elif command -v sloads-oracle >/dev/null 2>&1; then
  ORACLE_LAUNCH=("$(command -v sloads-oracle)")
  ORACLE_HOW="the sloads-oracle console script (from PATH)"
else
  ORACLE_LAUNCH=("$PYTHON" "$ROOT_DIR/oracle.py")
  ORACLE_HOW="python oracle.py (no console script installed)"
fi

# Boot one front-end, prove it serves, and stop it again.
#   smoke_gui <label> <port> <command ...>
# The command is anything that ends in a Streamlit server; the server flags are
# appended here so every front-end is started on identical terms.
smoke_gui() {
  local label="$1" port="$2"
  shift 2
  local slug="${label// /-}"
  local log="$TMP_DIR/$slug.log"

  "$@" \
    --server.headless true \
    --server.address 127.0.0.1 \
    --server.port "$port" \
    --browser.gatherUsageStats false \
    >"$log" 2>&1 &
  STREAMLIT_PID=$!

  local up=0
  for _ in $(seq 1 30); do
    if ! kill -0 "$STREAMLIT_PID" 2>/dev/null; then
      echo "smoke_test: FAIL — $label exited early; log:" >&2
      cat "$log" >&2
      exit 1
    fi
    if curl -sf "http://127.0.0.1:$port/_stcore/health" >/dev/null 2>&1; then
      up=1
      break
    fi
    sleep 1
  done
  if [[ "$up" -ne 1 ]]; then
    echo "smoke_test: FAIL — $label did not report healthy within 30s; log:" >&2
    cat "$log" >&2
    exit 1
  fi

  local status_code
  status_code="$(curl -s -o "$TMP_DIR/$slug.html" -w '%{http_code}' "http://127.0.0.1:$port/")"
  if [[ "$status_code" != "200" ]]; then
    echo "smoke_test: FAIL — $label root page returned HTTP $status_code" >&2
    exit 1
  fi

  if grep -qiE "traceback \(most recent call last\)|streamlit\.errors\." "$log"; then
    echo "smoke_test: FAIL — traceback in the $label server log:" >&2
    cat "$log" >&2
    exit 1
  fi

  kill "$STREAMLIT_PID" 2>/dev/null || true
  wait "$STREAMLIT_PID" 2>/dev/null || true
  STREAMLIT_PID=""
  echo "smoke_test: $label started headless and rendered its root page (HTTP 200, no traceback)."
}

echo "smoke_test: [1/3] starting the main GUI (${GUI_ENTRY_POINTS[0]}) headless on port 8765 ..."
smoke_gui "main GUI" 8765 "$PYTHON" -m streamlit run "$ROOT_DIR/${GUI_ENTRY_POINTS[0]}"

echo "smoke_test: [2/3] starting the oracle GUI (${GUI_ENTRY_POINTS[1]}) headless on port 8766 via $ORACLE_HOW ..."
smoke_gui "oracle GUI" 8766 "${ORACLE_LAUNCH[@]}"

echo "smoke_test: [3/3] running CLI export against $(basename "$PROJECT") ..."
"$PYTHON" cli.py engine "$PROJECT" -o "$OUT_CSV"

if [[ ! -s "$OUT_CSV" ]]; then
  echo "smoke_test: FAIL — $OUT_CSV was not written or is empty" >&2
  exit 1
fi

# Since G8.3 every exported CSV carries the methods & limitations statement as
# `#` lines above the header row, so a reader that takes line 1 as the header
# reads prose. This script is a CSV reader like any other and skips them --
# `workbook._csv_to_df` (comment="#") is the same contract in Python.
if ! grep -q "^# METHODS AND LIMITATIONS" "$OUT_CSV"; then
  echo "smoke_test: FAIL — CSV carries no G8.3 methods & limitations stamp" >&2
  exit 1
fi

data="$(grep -v '^#' "$OUT_CSV" | grep -v '^[[:space:]]*$')"
header="$(printf '%s\n' "$data" | head -n 1)"
if [[ "$header" != *"ID"* ]]; then
  echo "smoke_test: FAIL — unexpected CSV header: $header" >&2
  exit 1
fi

row_count="$(($(printf '%s\n' "$data" | wc -l) - 1))"
if [[ "$row_count" -lt 1 ]]; then
  echo "smoke_test: FAIL — CSV has a header but no load-case rows" >&2
  exit 1
fi

echo "smoke_test: CLI wrote $row_count load-case row(s) with header: $header"
echo "smoke_test: PASS"
