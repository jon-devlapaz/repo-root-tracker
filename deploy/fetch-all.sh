#!/usr/bin/env bash
# Refresh every tracked repo so ahead/behind reflects the remote. Run by the timer.
set -u
CONFIG="${RRT_CONFIG_DIR:-/var/lib/rrt/config}/repos.json"
[ -f "$CONFIG" ] || exit 0
python3 - "$CONFIG" <<'PY' | while IFS= read -r repo; do
import json, sys
for entry in json.load(open(sys.argv[1])):
    print(entry["path"])
PY
  timeout 120 git -C "$repo" fetch --all --prune --quiet 2>&1 | sed "s|^|$repo: |"
done
exit 0
