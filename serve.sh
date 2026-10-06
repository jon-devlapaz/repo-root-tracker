#!/usr/bin/env bash
# Open the repo-root-tracker dashboard in your browser.
# Starts the server first if it isn't already running.
#
# Usage: ./serve.sh            (uses port 7842)
#        RRT_PORT=9000 ./serve.sh
set -euo pipefail

PORT="${RRT_PORT:-7842}"
URL="http://127.0.0.1:${PORT}/"

# Resolve the repo root even when invoked via a symlink (e.g. ~/.local/bin)
SCRIPT_PATH="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$0")"
REPO_ROOT="$(dirname "${SCRIPT_PATH}")"

# Always run this checkout's own source (standard library only, nothing to install), even if another copy is installed.
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

# Start the server if nothing is answering on the port
if curl -sf -o /dev/null "${URL}api/scan" 2>/dev/null; then
  echo "Dashboard already running on :${PORT}"
else
  echo "Starting dashboard on :${PORT} ..."
  nohup python3 -m repo_root_tracker.server --port "${PORT}" \
    >/tmp/repo-root-tracker.log 2>&1 &
  for _ in $(seq 1 40); do
    curl -sf -o /dev/null "${URL}api/scan" 2>/dev/null && break
    sleep 0.25
  done
  curl -sf -o /dev/null "${URL}api/scan" 2>/dev/null \
    || { echo "Server failed to start — see /tmp/repo-root-tracker.log"; exit 1; }
  echo "Server started (log: /tmp/repo-root-tracker.log)"
fi

open "${URL}" 2>/dev/null || true
echo "→ ${URL}"
