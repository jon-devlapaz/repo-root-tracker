"""Web dashboard server for repo-root-tracker."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import NotARepositoryError, find_root
from .status import GitNotAvailableError, get_repo_status

CONFIG_DIR = Path(os.environ.get("RRT_CONFIG_DIR", Path.home() / ".config" / "repo-root-tracker"))
REPOS_FILE = CONFIG_DIR / "repos.json"
ASSET = Path(__file__).resolve().parent / "dashboard.html"


def load_repos() -> list[dict]:
    if not REPOS_FILE.exists():
        return []
    try:
        data = json.loads(REPOS_FILE.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


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
    def do_GET(self):
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self.send_error(403)
            return
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            body = ASSET.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/repos":
            self._json(200, load_repos())
        elif path == "/api/repos/status":
            # ?path=<repo-root> — status signals for one repo
            query = urlsplit(self.path).query
            params = dict(
                kv.split("=", 1) for kv in query.split("&") if "=" in kv
            )
            from urllib.parse import unquote

            repo_path = unquote(params.get("path", ""))
            if not repo_path:
                self._json(400, {"error": "path query param is required"})
                return
            if not any(r["path"] == repo_path for r in load_repos()):
                self._json(404, {"error": "not tracked"})
                return
            try:
                self._json(200, get_repo_status(repo_path).to_dict())
            except GitNotAvailableError as e:
                self._json(503, {"error": str(e)})
        else:
            self.send_error(404)

    def do_POST(self):
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self.send_error(403)
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
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self.send_error(403)
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

    def log_message(self, fmt, *args):
        pass


def serve(port: int = 7842) -> None:
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
    args = parser.parse_args()
    serve(args.port)


if __name__ == "__main__":
    main()
