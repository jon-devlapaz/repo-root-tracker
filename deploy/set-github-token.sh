#!/usr/bin/env bash
# Give the Pi read access to your private GitHub repos so its 10-minute fetch can refresh them.
# Use a fine-grained token with ONLY: Repository access = your repos, Permissions = Contents: Read-only.
# Never use a classic all-scopes token here: this machine is reachable from the internet.
#
#   Mac:  printf '%s' "$TOKEN" | ssh <user>@<pi> 'bash -s' < deploy/set-github-token.sh
#   Pi:   printf '%s' "$TOKEN" | bash set-github-token.sh
set -euo pipefail
IFS= read -r TOKEN || true  # tolerate input with no trailing newline
[ -n "$TOKEN" ] || { echo "No token on stdin." >&2; exit 1; }
case "$TOKEN" in github_pat_*) ;; *) echo "Refusing: not a fine-grained token (github_pat_...). Classic tokens carry far more power than a fetch needs." >&2; exit 1;; esac
CRED=/var/lib/rrt/.git-credentials
printf 'https://x-access-token:%s@github.com\n' "$TOKEN" | sudo -u rrt tee "$CRED" >/dev/null
sudo chmod 600 "$CRED"
sudo -u rrt git config --global credential.helper "store --file $CRED"
sudo -u rrt git config --global credential.https://github.com.useHttpPath false
echo "Token stored for the rrt user (mode 600). Test: sudo -u rrt git -C /var/lib/rrt/repos/<repo> fetch"
