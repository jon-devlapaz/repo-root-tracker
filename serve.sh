#!/usr/bin/env bash
# Open the repo-root-tracker dashboard in your browser.
# Starts the server first if it isn't already running.
#
# Usage: ./serve.sh            (uses port 7842)
#        RRT_PORT=9000 ./serve.sh
set -euo pipefail

PORT="${RRT_PORT:-7842}"
URL="http://127.0.0.1:${PORT}/"

# Install the package if Python can't see it yet
if ! python3 -c "import repo_root_tracker.server" 2>/dev/null; then
  echo "Installing repo-root-tracker..."
  pip install -e "$(cd "$(dirname "$0")" && pwd)" -q
fi

# Start the server if nothing is answering on the port
if curl -sf -o /dev/null "${URL}api/repos" 2>/dev/null; then
  echo "Dashboard already running on :${PORT}"
else
  echo "Starting dashboard on :${PORT} ..."
  nohup python3 -m repo_root_tracker.server --port "${PORT}" \
    >/tmp/repo-root-tracker.log 2>&1 &
  for _ in $(seq 1 40); do
    curl -sf -o /dev/null "${URL}api/repos" 2>/dev/null && break
    sleep 0.25
  done
  curl -sf -o /dev/null "${URL}api/repos" 2>/dev/null \
    || { echo "Server failed to start — see /tmp/repo-root-tracker.log"; exit 1; }
  echo "Server started (log: /tmp/repo-root-tracker.log)"
fi

open "${URL}" 2>/dev/null || true
echo "→ ${URL}"
