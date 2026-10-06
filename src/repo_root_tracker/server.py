"""Localhost web server for the repo-root-tracker table."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import NotARepositoryError
from .github import get_default_branch_ci
from .scan import Scan, default_roots, scan
from .status import GitNotAvailableError, fetch_origin, get_repo_status

ASSET = Path(__file__).resolve().parent / "dashboard.html"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

PRIVATE_NETWORKS = tuple(ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",   # RFC 1918: home and office networks
    "169.254.0.0/16", "fe80::/10", "fc00::/7"))          # link-local and IPv6 local
AUTO_CI = True                   # the page checks CI by itself on load, for repos that are otherwise clean (off: --no-auto-ci)
LAN = False                      # opt-in with --lan; off means loopback only
_lan_hosts: set[str] = set()     # Host names accepted in LAN mode: this machine's own addresses and names
ROOTS: list[str] = []
_scan_lock = threading.Lock()
_scan: Scan | None = None
_ci_last: dict[str, dict] = {}  # path -> {"state", "head_sha", "checked_at"}: the last CI check, with the commit it was for


def current_scan(*, refresh: bool = False) -> Scan:
    """The last scan, made on first use. Only checkouts found here can be queried."""
    global _scan
    with _scan_lock:
        if _scan is None or refresh:
            _scan = scan(ROOTS or default_roots())
        return _scan


def lan_addresses() -> list[str]:
    """This machine's own non-loopback IPv4 addresses. The UDP connect sends nothing; it only picks the outgoing interface."""
    found: set[str] = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))
            found.add(probe.getsockname()[0])
    except OSError:
        pass
    try:
        found.update(info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    return sorted(ip for ip in found if not ip.startswith("127."))


def lan_hostnames() -> set[str]:
    name = socket.gethostname().lower()
    short = name.removesuffix(".local")
    return {name, short, f"{short}.local"}


def peer_class(ip: str) -> str:
    """'loopback', 'private' (home or office network) or 'public' for a client address."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return "public"
    if address.is_loopback:
        return "loopback"
    # An explicit list, not ipaddress.is_private, which also accepts the reserved documentation ranges.
    return "private" if any(address in network for network in PRIVATE_NETWORKS) else "public"


def _host_is_local(header: str | None) -> bool:
    host = urlsplit(f"//{header or ''}").hostname or ""
    return host in LOCAL_HOSTS or (LAN and host.lower() in _lan_hosts)


class Handler(BaseHTTPRequestHandler):
    server_version = "repo-root-tracker"

    def _peer(self) -> str:
        return peer_class(self.client_address[0])

    def _ci_for(self, path: str, status) -> tuple[str, dict | None]:
        """The CI state to judge with. A passing or failing result counts only for the exact commit it was checked for;
        after local main moves, it is 'stale' until checked again."""
        remembered = _ci_last.get(path)
        if not remembered:
            return "unchecked", None
        current = remembered["state"] not in ("passing", "failing", "pending") or (
            bool(status.main_sha) and remembered["head_sha"] == status.main_sha)
        return (remembered["state"] if current else "stale"), {**remembered, "current": current}

    def _admit(self) -> bool:
        """Loopback only by default. In LAN mode, also private-network peers asking for this machine by its own name or
        address, read-only. Anything else, and any cross-site POST, is refused."""
        peer = self._peer()
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.send_error(403)  # another website's page is asking; browsers say so, and nothing here is meant for that
            return False
        if peer == "public" or (peer == "private" and not LAN):
            self.send_error(403)
            return False
        if not _host_is_local(self.headers.get("Host")):
            self.send_error(403)
            return False
        if self.command == "POST":
            origin = self.headers.get("Origin")
            if peer != "loopback" or (origin and not _host_is_local(urlsplit(origin).netloc)):
                self.send_error(403)  # only the machine running the tool may fetch or rescan
                return False
        return True

    def _scan_response(self, refresh: bool = False) -> dict:
        return {**current_scan(refresh=refresh).to_dict(), "writable": self._peer() == "loopback", "auto_ci": AUTO_CI}

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_error(405)  # no CORS

    def _checked_path(self, query: dict[str, list[str]]) -> str | None:
        """The requested path if the last scan found it; otherwise answer 400 or 404 and return None."""
        values = query.get("path", [])
        if not values or not values[0]:
            self._json(400, {"error": "path query param is required"})
            return None
        if values[0] not in current_scan().paths():
            self._json(404, {"error": "not found by the scan"})
            return None
        return values[0]

    def _status_response(self, path: str) -> None:
        try:
            status = get_repo_status(path)
            state, remembered = self._ci_for(path, status)
            self._json(200, {**status.to_dict(ci=state), "ci": remembered})
        except NotARepositoryError as e:
            self._json(410, {"error": str(e), "gone": True})
        except (GitNotAvailableError, RuntimeError, subprocess.TimeoutExpired) as e:
            self._json(503, {"error": str(e)})

    def do_GET(self) -> None:
        if not self._admit():
            return
        split = urlsplit(self.path)
        query = parse_qs(split.query)
        if split.path in ("/", "/index.html"):
            self._send(200, ASSET.read_bytes(), "text/html; charset=utf-8")
        elif split.path == "/api/scan":
            self._json(200, self._scan_response())
        elif split.path == "/api/repos/status":
            path = self._checked_path(query)
            if path:
                self._status_response(path)
        elif split.path == "/api/ci":
            path = self._checked_path(query)
            if not path:
                return
            if self._peer() != "loopback":
                self._json(403, {"error": "CI checks run with your GitHub login, so only this computer may start them"})
                return
            ci = get_default_branch_ci(path, refresh=query.get("refresh") == ["1"])
            _ci_last[path] = {"state": ci.state, "head_sha": ci.head_sha, "checked_at": ci.checked_at}
            self._json(200, {"ci": ci.to_dict()})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if not self._admit():
            return
        split = urlsplit(self.path)
        if split.path == "/api/scan":
            self._json(200, self._scan_response(refresh=True))
        elif split.path == "/api/fetch":
            path = self._checked_path(parse_qs(split.query))
            if not path:
                return
            try:
                fetch_origin(path)
            except NotARepositoryError as e:
                self._json(410, {"error": str(e), "gone": True})
                return
            except (GitNotAvailableError, RuntimeError, subprocess.TimeoutExpired) as e:
                self._json(503, {"error": f"fetch failed: {e}"})
                return
            self._status_response(path)
        else:
            self.send_error(404)

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data) -> None:
        self._send(code, json.dumps(data).encode(), "application/json")

    def log_message(self, fmt, *args) -> None:
        pass

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser went away mid-response (a reload or a closed tab)


def make_server(port: int = 7842, roots: list[str] | None = None, lan: bool = False, auto_ci: bool = True) -> ThreadingHTTPServer:
    """Loopback only unless `lan`. Port 0 picks a free port."""
    global ROOTS, _scan, LAN, _lan_hosts, AUTO_CI
    ROOTS, _scan, LAN, AUTO_CI = list(roots or default_roots()), None, lan, auto_ci
    _lan_hosts = ({*lan_addresses(), *lan_hostnames()} if lan else set())
    _ci_last.clear()
    return ThreadingHTTPServer(("0.0.0.0" if lan else "127.0.0.1", port), Handler)


def serve(port: int = 7842, roots: list[str] | None = None, lan: bool = False, auto_ci: bool = True) -> None:
    server = make_server(port, roots, lan, auto_ci)
    bound = server.server_address[1]
    print(f"http://127.0.0.1:{bound}/", flush=True)
    if lan:
        for address in lan_addresses():
            print(f"http://{address}:{bound}/   <- open this on your phone (same wifi)", flush=True)
        print(f"http://{socket.gethostname().lower().removesuffix('.local')}.local:{bound}/", flush=True)
        print("LAN mode: anyone on this private network can view repo paths, branches and commit messages. "
              "There is no password. Fetch and Rescan only work from this machine.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="repo-root-tracker: a table of every git repo under a folder")
    parser.add_argument("--port", type=int, default=7842)
    parser.add_argument("--root", action="append", dest="roots", metavar="PATH",
                        help="folder to scan (repeatable). Default: RRT_ROOTS, else ~/dev/active")
    parser.add_argument("--lan", action="store_true",
                        help="also serve devices on your private network (read-only, no password); default is this machine only")
    parser.add_argument("--no-auto-ci", action="store_true",
                        help="do not ask GitHub for CI results when the page loads (the GitHub button still works)")
    args = parser.parse_args()
    serve(args.port, args.roots, args.lan, auto_ci=not args.no_auto_ci and os.environ.get("RRT_AUTO_CI", "1") != "0")


if __name__ == "__main__":
    main()
