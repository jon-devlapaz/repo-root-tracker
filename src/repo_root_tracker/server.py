"""Web dashboard server for repo-root-tracker."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import NotARepositoryError, find_root
from . import auth, organization
from .detail import get_commit_diff, get_repo_detail, get_working_diff
from .github import get_github_info
from .history import MAX_DAYS, get_activity
from .status import GitNotAvailableError, get_repo_identity, get_repo_status

CONFIG_DIR = Path(os.environ.get("RRT_CONFIG_DIR", Path.home() / ".config" / "repo-root-tracker"))
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
# Remote mode (all None/empty by default): set by serve() from the environment.
PUBLIC_HOSTS: set[str] = set()
PASSWORD_HASH: str | None = None
SESSION_SECRET: bytes = b""
LIMITER = auth.LoginLimiter()
REPOS_FILE = CONFIG_DIR / "repos.json"
ASSET = Path(__file__).resolve().parent / "dashboard.html"
# Serializes read-modify-write cycles on repos.json (concurrent add/remove
# would otherwise interleave and silently drop entries).
_REPOS_LOCK = threading.Lock()
# Activity reads one git log per tracked repo; a short cache keeps the replay scrubber cheap.
_ACTIVITY_CACHE: dict[int, tuple[float, dict]] = {}
_ACTIVITY_TTL = 30.0


def activity_for_all(days: int) -> dict:
    now = time.monotonic()
    hit = _ACTIVITY_CACHE.get(days)
    if hit and now - hit[0] < _ACTIVITY_TTL:
        return hit[1]
    repos: dict[str, dict[str, int]] = {}
    for r in load_repos():
        try:
            repos[r["path"]] = get_activity(r["path"], days)
        except (NotARepositoryError, GitNotAvailableError, subprocess.TimeoutExpired):
            continue
    result = {"days": days, "repos": repos}
    _ACTIVITY_CACHE[days] = (now, result)
    return result


def _font_faces() -> str:
    """The dashboard's embedded @font-face rules, so the sign-in page matches the brand without a network font."""
    import re
    html = ASSET.read_text(encoding="utf-8")
    return "".join(re.findall(r"@font-face\s*\{[^}]*\}", html))


def repos_with_identity(repos: list[dict]) -> list[dict]:
    """Attach project identity so the dashboard can group worktrees on first paint."""
    if not repos:
        return repos
    with ThreadPoolExecutor(max_workers=8) as pool:
        identities = list(pool.map(lambda repo: get_repo_identity(repo.get("path", "")), repos))
    return [{**repo, **identity} for repo, identity in zip(repos, identities)]


def load_repos() -> list[dict]:
    if not REPOS_FILE.exists():
        return []
    try:
        data = json.loads(REPOS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    # Sanitize: one malformed entry must not brick every endpoint
    return [r for r in data
            if isinstance(r, dict) and isinstance(r.get("path"), str) and r["path"]]


def save_repos(repos: list[dict]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = REPOS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(repos, indent=2))
    tmp.replace(REPOS_FILE)


def validate_repo(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    try:
        root = find_root(p)
        return {"valid": True, "root": str(root)}
    except NotARepositoryError as e:
        return {"valid": False, "error": str(e)}


class Handler(BaseHTTPRequestHandler):
    # ---- remote access: host allowlist, password session, same-origin writes ----
    def _client_ip(self) -> str:
        ip = self.client_address[0]
        forwarded = self.headers.get("X-Forwarded-For", "")
        # Only a proxy on this machine may speak for the client; its last hop is the real one.
        if ip in ("127.0.0.1", "::1") and forwarded:
            return forwarded.split(",")[-1].strip() or ip
        return ip

    def _cookie(self, name: str) -> str:
        for part in self.headers.get("Cookie", "").split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return ""

    def _redirect(self, location: str, cookie: str | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _login_page(self, error: str = "", code: int = 200) -> None:
        body = auth.LOGIN_PAGE.replace("__ERROR__", error).replace("__FONTS__", _font_faces()).encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _session_cookie(self, value: str, max_age: int) -> str:
        secure = self.headers.get("X-Forwarded-Proto") == "https" or self.headers.get("Host", "").split(":")[0] not in LOCAL_HOSTS
        return f"rrt_session={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}" + ("; Secure" if secure else "")

    def _handle_login(self, path: str) -> None:
        if self.command == "GET":
            self._login_page()
            return
        ip = self._client_ip()
        wait = LIMITER.locked_for(ip)
        if wait:
            self.send_response(429)
            self.send_header("Retry-After", str(wait))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            length = max(0, min(int(self.headers.get("Content-Length", "0") or "0"), 4096))
        except ValueError:
            length = 0
        form = dict(kv.split("=", 1) for kv in self.rfile.read(length).decode(errors="replace").split("&") if "=" in kv)
        password = unquote(form.get("password", "").replace("+", " "))
        if PASSWORD_HASH and auth.verify_password(password, PASSWORD_HASH):
            LIMITER.succeeded(ip)
            self._redirect("/", self._session_cookie(auth.make_token(SESSION_SECRET), auth.SESSION_SECONDS))
            return
        LIMITER.failed(ip)
        time.sleep(0.4)
        self._login_page("That password is not right.", 401)

    def _admit(self) -> bool:
        """Gate every request. True means the caller may proceed."""
        host = self.headers.get("Host", "").split(":")[0]
        if host not in LOCAL_HOSTS | PUBLIC_HOSTS:
            self.send_error(403)
            return False
        command = getattr(self, "command", "GET")
        if command in ("POST", "PUT", "DELETE"):
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).hostname not in LOCAL_HOSTS | PUBLIC_HOSTS:
                self.send_error(403)
                return False
        if not PASSWORD_HASH:
            return True
        path = urlsplit(self.path).path
        if path == "/login":
            self._handle_login(path)
            return False
        if path == "/logout" and command == "POST":
            self._redirect("/login", self._session_cookie("", 0))
            return False
        if auth.verify_token(SESSION_SECRET, self._cookie("rrt_session")):
            return True
        if command == "GET" and not path.startswith("/api/"):
            self._redirect("/login")
        else:
            self._json(401, {"error": "Sign in required"})
        return False

    def do_OPTIONS(self) -> None:
        # No CORS and no method listing, signed in or not.
        self.send_error(405)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def do_GET(self):
        if not self._admit():
            return
        split = urlsplit(self.path)
        path = split.path
        params = dict(
            kv.split("=", 1) for kv in split.query.split("&") if "=" in kv
        )
        if path in ("/", "/index.html"):
            body = ASSET.read_bytes().replace(
                b'"__HOME__"', json.dumps(str(Path.home())).replace("<", "\\u003c").encode(), 1)
            if PASSWORD_HASH:
                body = body.replace(b'data-remote="0"', b'data-remote="1"', 1)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/organization":
            try:
                self._json(200, organization.read(CONFIG_DIR))
            except organization.StorageError as e:
                self._json(500, {"error": str(e)})
        elif path == "/api/repos":
            self._json(200, repos_with_identity(load_repos()))
        elif path == "/api/repos/status":
            # ?path=<repo-root> — status signals for one repo
            repo_path = unquote(params.get("path", ""))
            if not repo_path:
                self._json(400, {"error": "path query param is required"})
                return
            if not any(r["path"] == repo_path for r in load_repos()):
                self._json(404, {"error": "not tracked"})
                return
            try:
                self._json(200, get_repo_status(repo_path).to_dict())
            except NotARepositoryError as e:
                self._json(410, {"error": str(e), "gone": True})
            except (GitNotAvailableError, RuntimeError, subprocess.TimeoutExpired) as e:
                self._json(503, {"error": str(e)})
        elif path == "/api/activity":
            try:
                days = max(1, min(int(params.get("days", "30")), MAX_DAYS))
            except ValueError:
                self._json(400, {"error": "days must be an integer"})
                return
            self._json(200, activity_for_all(days))
        elif path == "/api/repo":
            repo_path = unquote(params.get("path", ""))
            if not repo_path:
                self._json(400, {"error": "path query param is required"})
                return
            if not any(r["path"] == repo_path for r in load_repos()):
                self._json(404, {"error": "not tracked"})
                return
            try:
                self._json(200, get_repo_detail(repo_path).to_dict())
            except NotARepositoryError as e:
                self._json(410, {"error": str(e), "gone": True})
            except RuntimeError as e:
                self._json(500, {"error": str(e)})
        elif path == "/api/github":
            repo_path = unquote(params.get("path", ""))
            if not repo_path:
                self._json(400, {"error": "path query param is required"})
                return
            if not any(r["path"] == repo_path for r in load_repos()):
                self._json(404, {"error": "not tracked"})
                return
            self._json(200, get_github_info(repo_path, refresh=params.get("refresh") == "1").to_dict())
        elif path == "/api/commit":
            repo_path = unquote(params.get("path", ""))
            commit_hash = params.get("hash", "")
            if not repo_path or not commit_hash:
                self._json(400, {"error": "path and hash query params required"})
                return
            try:
                diff = get_commit_diff(repo_path, commit_hash)
                self._text(200, diff)
            except ValueError as e:
                self._json(400, {"error": str(e)})
            except NotARepositoryError as e:
                self._json(410, {"error": str(e), "gone": True})
            except RuntimeError as e:
                self._json(500, {"error": str(e)})
        elif path == "/api/working-diff":
            repo_path = unquote(params.get("path", ""))
            file = unquote(params.get("file", ""))
            if not repo_path or not file:
                self._json(400, {"error": "path and file query params required"})
                return
            try:
                diff = get_working_diff(repo_path, file)
                self._text(200, diff)
            except ValueError as e:
                self._json(400, {"error": str(e)})
            except NotARepositoryError as e:
                self._json(410, {"error": str(e), "gone": True})
            except RuntimeError as e:
                self._json(500, {"error": str(e)})
        else:
            self.send_error(404)

    def do_PUT(self):
        if not self._admit():
            return
        if urlsplit(self.path).path != "/api/organization":
            self.send_error(404)
            return
        try:
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Transfer-Encoding is not supported")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= organization.MAX_BYTES:
                raise ValueError("Organization request must be between 1 byte and 1 MiB")
            payload = json.loads(self.rfile.read(length))
            code, state = organization.update(CONFIG_DIR, payload)
        except (ValueError, UnicodeError, RecursionError) as e:
            self._json(400, {"error": str(e)})
        except organization.StorageError as e:
            self._json(500, {"error": str(e)})
        else:
            self._json(code, state)

    def do_POST(self):
        if not self._admit():
            return
        path = urlsplit(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if path == "/api/repos":
            repo_path = str(payload.get("path", "")).strip()
            if not repo_path:
                self._json(400, {"error": "path is required"})
                return
            result = validate_repo(repo_path)
            if not result["valid"]:
                self._json(400, result)
                return
            with _REPOS_LOCK:
                repos = load_repos()
                root = result["root"]
                if any(r["path"] == root for r in repos):
                    self._json(409, {"error": "already tracked", "root": root})
                    return
                repos.append({"path": root})
                save_repos(repos)
            self._json(201, {"path": root})

        elif path == "/api/repos/validate":
            repo_path = str(payload.get("path", "")).strip()
            self._json(200, validate_repo(repo_path))

        else:
            self.send_error(404)

    def do_DELETE(self):
        if not self._admit():
            return
        path = urlsplit(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if path == "/api/repos":
            repo_path = str(payload.get("path", "")).strip()
            with _REPOS_LOCK:
                repos = load_repos()
                before = len(repos)
                repos = [r for r in repos if r["path"] != repo_path]
                if len(repos) == before:
                    self._json(404, {"error": "not found"})
                    return
                save_repos(repos)
            self._json(200, {"removed": repo_path})
        else:
            self.send_error(404)

    def _json(self, code: int, data) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code: int, text: str) -> None:
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def configure_remote() -> None:
    """Read remote-access settings from the environment (all optional)."""
    global PUBLIC_HOSTS, PASSWORD_HASH, SESSION_SECRET
    PUBLIC_HOSTS = {h.strip().lower() for h in os.environ.get("RRT_PUBLIC_HOST", "").split(",") if h.strip()}
    hash_file = os.environ.get("RRT_PASSWORD_HASH_FILE")
    PASSWORD_HASH = (Path(hash_file).read_text().strip() if hash_file else os.environ.get("RRT_PASSWORD_HASH")) or None
    if PUBLIC_HOSTS and not PASSWORD_HASH:
        raise SystemExit("RRT_PUBLIC_HOST is set but no password is configured. Run "
                         "`python -m repo_root_tracker.server --hash-password` and set RRT_PASSWORD_HASH.")
    SESSION_SECRET = auth.load_secret(CONFIG_DIR) if PASSWORD_HASH else b""


def serve(port: int = 7842) -> None:
    configure_remote()
    # Always loopback: remote access goes through a TLS reverse proxy on the same machine.
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="repo-root-tracker dashboard")
    parser.add_argument("--port", type=int, default=7842)
    parser.add_argument("--hash-password", action="store_true", help="prompt for a password and print its hash")
    args = parser.parse_args()
    if args.hash_password:
        import getpass
        first = getpass.getpass("New password: ")
        if len(first) < 12:
            raise SystemExit("Use at least 12 characters.")
        if first != getpass.getpass("Repeat it: "):
            raise SystemExit("Passwords differ.")
        print(auth.hash_password(first))
        return
    serve(args.port)


if __name__ == "__main__":
    main()
