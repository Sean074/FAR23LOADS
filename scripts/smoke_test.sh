#!/usr/bin/env bash
# GUI/CLI smoke test — RELEASE_PROCESS.md §3.5.
#
# 1. Starts the Streamlit app headless, waits for it to come up, and checks
#    the root page answers 200 with no traceback in the server log.
# 2. Runs the CLI "engine" module against the ga6_normal example and checks
#    the CSV it writes is non-empty with the expected header.
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

if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
  echo "smoke_test: no usable Python interpreter (set \$PYTHON or install python3)" >&2
  exit 1
fi
if ! "$PYTHON" -c 'import streamlit, farloads' >/dev/null 2>&1; then
  echo "smoke_test: streamlit/farloads not importable by $PYTHON — run 'pip install -e .[dev]' first" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
SERVER_LOG="$TMP_DIR/streamlit.log"
OUT_CSV="$TMP_DIR/out.csv"
PORT=8765
STREAMLIT_PID=""

cleanup() {
  if [[ -n "$STREAMLIT_PID" ]] && kill -0 "$STREAMLIT_PID" 2>/dev/null; then
    kill "$STREAMLIT_PID" 2>/dev/null || true
    wait "$STREAMLIT_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "smoke_test: [1/2] starting Streamlit headless on port $PORT ..."
"$PYTHON" -m streamlit run "$ROOT_DIR/app/Home.py" \
  --server.headless true \
  --server.address 127.0.0.1 \
  --server.port "$PORT" \
  --browser.gatherUsageStats false \
  >"$SERVER_LOG" 2>&1 &
STREAMLIT_PID=$!

health_url="http://127.0.0.1:$PORT/_stcore/health"
up=0
for _ in $(seq 1 30); do
  if ! kill -0 "$STREAMLIT_PID" 2>/dev/null; then
    echo "smoke_test: FAIL — Streamlit process exited early; log:" >&2
    cat "$SERVER_LOG" >&2
    exit 1
  fi
  if curl -sf "$health_url" >/dev/null 2>&1; then
    up=1
    break
  fi
  sleep 1
done

if [[ "$up" -ne 1 ]]; then
  echo "smoke_test: FAIL — Streamlit did not report healthy within 30s; log:" >&2
  cat "$SERVER_LOG" >&2
  exit 1
fi

status_code="$(curl -s -o "$TMP_DIR/root.html" -w '%{http_code}' "http://127.0.0.1:$PORT/")"
if [[ "$status_code" != "200" ]]; then
  echo "smoke_test: FAIL — root page returned HTTP $status_code" >&2
  exit 1
fi

if grep -qiE "traceback \(most recent call last\)|streamlit\.errors\." "$SERVER_LOG"; then
  echo "smoke_test: FAIL — traceback found in Streamlit server log:" >&2
  cat "$SERVER_LOG" >&2
  exit 1
fi

kill "$STREAMLIT_PID" 2>/dev/null || true
wait "$STREAMLIT_PID" 2>/dev/null || true
STREAMLIT_PID=""
echo "smoke_test: Streamlit started headless and rendered the root page (HTTP 200, no traceback)."

echo "smoke_test: [2/2] running CLI export against $(basename "$PROJECT") ..."
"$PYTHON" cli.py engine "$PROJECT" -o "$OUT_CSV"

if [[ ! -s "$OUT_CSV" ]]; then
  echo "smoke_test: FAIL — $OUT_CSV was not written or is empty" >&2
  exit 1
fi

header="$(head -n 1 "$OUT_CSV")"
if [[ "$header" != *"ID"* ]]; then
  echo "smoke_test: FAIL — unexpected CSV header: $header" >&2
  exit 1
fi

row_count="$(($(wc -l <"$OUT_CSV") - 1))"
if [[ "$row_count" -lt 1 ]]; then
  echo "smoke_test: FAIL — CSV has a header but no load-case rows" >&2
  exit 1
fi

echo "smoke_test: CLI wrote $row_count load-case row(s) with header: $header"
echo "smoke_test: PASS"
