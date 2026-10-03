#!/usr/bin/env bash
# One-shot installer for a Raspberry Pi (Debian/Raspberry Pi OS). Idempotent: run it again to upgrade.
# Usage: bash install-pi.sh [rrt-source.tar.gz]     (the tarball defaults to the one next to this script)
# Result: the dashboard on a public HTTPS URL via Tailscale Funnel, behind a password.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARBALL="${1:-$HERE/rrt-source.tar.gz}"
APP=/opt/repo-root-tracker
STATE=/var/lib/rrt
ENVFILE=/etc/repo-root-tracker.env
[ -f "$TARBALL" ] || { echo "Source tarball not found: $TARBALL" >&2; exit 1; }
command -v tailscale >/dev/null || { echo "Tailscale is not installed on this Pi." >&2; exit 1; }

say() { printf '\n==> %s\n' "$*"; }

say "Installing packages"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3-venv openssl >/dev/null

say "Creating the service user and unpacking the app"
id rrt >/dev/null 2>&1 || sudo useradd --system --create-home --home-dir "$STATE" --shell /usr/sbin/nologin rrt
sudo mkdir -p "$APP" "$STATE/config" "$STATE/repos"
sudo tar -xzf "$TARBALL" -C "$APP"
sudo python3 -m venv "$APP/.venv"
sudo "$APP/.venv/bin/pip" install -q -e "$APP"
sudo chown -R rrt:rrt "$STATE"
sudo chmod +x "$APP/deploy/fetch-all.sh"

say "Working out this Pi's public name"
HOST="$(tailscale status --json | python3 -c 'import sys,json; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
[ -n "$HOST" ] || { echo "Could not read the Tailscale name." >&2; exit 1; }

PASSWORD=""
if [ ! -f "$ENVFILE" ]; then
  say "Creating a password"
  PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)"
  HASH="$(printf '%s' "$PASSWORD" | sudo -u rrt "$APP/.venv/bin/python" -c 'import sys; from repo_root_tracker import auth; print(auth.hash_password(sys.stdin.read()))')"
  printf 'RRT_PUBLIC_HOST=%s\nRRT_PASSWORD_HASH=%s\n' "$HOST" "$HASH" | sudo tee "$ENVFILE" >/dev/null
  sudo chmod 600 "$ENVFILE"
else
  sudo sed -i "s|^RRT_PUBLIC_HOST=.*|RRT_PUBLIC_HOST=$HOST|" "$ENVFILE"
fi

say "Preparing the repo list"
[ -f "$STATE/config/repos.json" ] || echo '[]' | sudo -u rrt tee "$STATE/config/repos.json" >/dev/null

say "Starting the services"
sudo cp "$APP/deploy/repo-root-tracker.service" "$APP/deploy/rrt-fetch.service" "$APP/deploy/rrt-fetch.timer" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now repo-root-tracker rrt-fetch.timer >/dev/null 2>&1
sudo systemctl restart repo-root-tracker
for _ in $(seq 1 20); do curl -sf -o /dev/null -H "Host: $HOST" http://127.0.0.1:7842/login && break; sleep 1; done
curl -sf -o /dev/null -H "Host: $HOST" http://127.0.0.1:7842/login || { echo "The service did not start: journalctl -u repo-root-tracker" >&2; exit 1; }

say "Publishing over Tailscale Funnel"
sudo tailscale funnel --bg 7842 >/dev/null

printf '\n=========================================\n'
printf ' Dashboard: https://%s/\n' "$HOST"
if [ -n "$PASSWORD" ]; then printf ' Password:  %s\n (shown once; it is stored only as a hash)\n' "$PASSWORD"; else printf ' Password:  unchanged from the earlier install\n'; fi
printf '=========================================\n'
