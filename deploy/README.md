# Running on a Raspberry Pi behind a URL

## Fastest route: one command (Tailscale Funnel)
If the Pi is on your Tailscale network, `install-pi.sh` does everything below for you and publishes a public HTTPS URL (`https://<pi>.<tailnet>.ts.net/`) with no router changes or domain. It generates a strong password and prints it once.

From the Mac: `git archive HEAD | gzip > rrt-source.tar.gz && tailscale file cp deploy/install-pi.sh rrt-source.tar.gz <pi>:`
On the Pi: `tailscale file get . && bash install-pi.sh` (run it again with a fresh tarball to upgrade).

The manual steps below are for a router port-forward with Caddy instead.

The dashboard reads git repos on the machine it runs on. On the Pi that means **clones of your repos on the Pi**; they are refreshed by a timer (`git fetch`), so ahead/behind and GitHub state stay current. Local uncommitted changes on your Mac are not visible there.

How it is protected: the Python server only listens on `127.0.0.1`. Caddy on the Pi terminates HTTPS and forwards to it. Every page and API call needs a password sign-in (scrypt hash, signed 7-day cookie, five wrong tries lock an address out for 15 minutes). Requests for any other host name are refused, and writes must come from the same site.

> Exposing this to the internet still means anyone can reach the sign-in page. Use a long password (12+ characters, a passphrase is ideal), keep the Pi patched, and consider a private alternative such as Tailscale if you do not need a public URL.

## 1. A name for your home address
Pick a host name and point it at your home IP (a free dynamic-DNS name from DuckDNS works). Forward router ports **80** and **443** to the Pi. Port 80 is needed for the certificate.

## 2. Install
```bash
sudo apt update && sudo apt install -y git python3-venv caddy
sudo useradd --system --create-home --home-dir /var/lib/rrt --shell /usr/sbin/nologin rrt
sudo git clone https://github.com/jon-devlapaz/repo-root-tracker /opt/repo-root-tracker
cd /opt/repo-root-tracker && sudo python3 -m venv .venv && sudo .venv/bin/pip install -e .
```

## 3. Set the password and host name
```bash
sudo -u rrt /opt/repo-root-tracker/.venv/bin/python -m repo_root_tracker.server --hash-password
sudo cp deploy/repo-root-tracker.env.example /etc/repo-root-tracker.env
sudo nano /etc/repo-root-tracker.env     # paste the hash, set your host name
sudo chmod 600 /etc/repo-root-tracker.env
```

## 4. Start it
```bash
sudo cp deploy/repo-root-tracker.service deploy/rrt-fetch.service deploy/rrt-fetch.timer /etc/systemd/system/
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile && sudo nano /etc/caddy/Caddyfile   # your host name
sudo systemctl daemon-reload
sudo systemctl enable --now repo-root-tracker rrt-fetch.timer
sudo systemctl restart caddy
```
Open `https://<your host name>/` and sign in.

## 5. Add repos
Clone them on the Pi (for example under `/var/lib/rrt/repos`, as the `rrt` user), then use **Add repo** in the dashboard with the Pi path. Private GitHub repos need a read-only deploy key or token for the `rrt` user.

## Operating notes
- Logs: `journalctl -u repo-root-tracker -f`. Change the password by re-running step 3 and `sudo systemctl restart repo-root-tracker`.
- Signing everyone out: delete `/var/lib/rrt/config/session.key` and restart the service.
- Firewall: allow only 22, 80 and 443 (`sudo ufw allow 22,80,443/tcp && sudo ufw enable`).

## Keeping private repos fresh
The Pi has no GitHub login by default, so its 10-minute fetch cannot update private repos. Create a **fine-grained** token (Repository access: your repos, Permissions: Contents → Read-only) and install it with `deploy/set-github-token.sh` (it refuses classic tokens unless you set `RRT_ALLOW_CLASSIC=1`). It also signs the `gh` CLI in, which the dashboard's GitHub tab needs. Rotate it like any credential; the Pi stores it only for the `rrt` service user.
