"""Localhost web server for the repo-root-tracker table."""

from __future__ import annotations

import argparse
import json
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

ROOTS: list[str] = []
_scan_lock = threading.Lock()
_scan: Scan | None = None
_ci_last: dict[str, str] = {}


def current_scan(*, refresh: bool = False) -> Scan:
    """The last scan, made on first use. Only checkouts found here can be queried."""
    global _scan
    with _scan_lock:
        if _scan is None or refresh:
            _scan = scan(ROOTS or default_roots())
        return _scan


def _host_is_local(header: str | None) -> bool:
    return (urlsplit(f"//{header or ''}").hostname or "") in LOCAL_HOSTS


class Handler(BaseHTTPRequestHandler):
    server_version = "repo-root-tracker"

    def _admit(self) -> bool:
        """Localhost only: refuse any Host that is not a loopback name, and any cross-site POST."""
        if not _host_is_local(self.headers.get("Host")):
            self.send_error(403)
            return False
        if self.command == "POST":
            origin = self.headers.get("Origin")
            if origin and not _host_is_local(urlsplit(origin).netloc):
                self.send_error(403)
                return False
        return True

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
            self._json(200, get_repo_status(path).to_dict(ci=_ci_last.get(path, "unchecked")))
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
            self._json(200, current_scan().to_dict())
        elif split.path == "/api/repos/status":
            path = self._checked_path(query)
            if path:
                self._status_response(path)
        elif split.path == "/api/ci":
            path = self._checked_path(query)
            if not path:
                return
            ci = get_default_branch_ci(path, refresh=query.get("refresh") == ["1"])
            _ci_last[path] = ci.state
            self._json(200, {"ci": ci.to_dict()})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if not self._admit():
            return
        split = urlsplit(self.path)
        if split.path == "/api/scan":
            self._json(200, current_scan(refresh=True).to_dict())
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


def make_server(port: int = 7842, roots: list[str] | None = None) -> ThreadingHTTPServer:
    """A server bound to loopback only. Port 0 picks a free port."""
    global ROOTS, _scan
    ROOTS, _scan = list(roots or default_roots()), None
    _ci_last.clear()
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(port: int = 7842, roots: list[str] | None = None) -> None:
    server = make_server(port, roots)
    print(f"http://127.0.0.1:{server.server_address[1]}/", flush=True)
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
    args = parser.parse_args()
    serve(args.port, args.roots)


if __name__ == "__main__":
    main()
