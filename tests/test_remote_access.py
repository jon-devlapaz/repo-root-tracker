"""Password-protected remote mode (behind a TLS proxy) and the unchanged local default."""

from __future__ import annotations

import http.client
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

import pytest

from repo_root_tracker import auth
from repo_root_tracker import server as srv

PASSWORD = "correct horse battery"
PUBLIC = "repos.example.com"


@pytest.fixture()
def run(tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setattr(srv, "CONFIG_DIR", cfg)
    monkeypatch.setattr(srv, "REPOS_FILE", cfg / "repos.json")
    servers = []

    def start(remote: bool):
        monkeypatch.setattr(srv, "LIMITER", auth.LoginLimiter())
        monkeypatch.setattr(srv, "PUBLIC_HOSTS", {PUBLIC} if remote else set())
        monkeypatch.setattr(srv, "PASSWORD_HASH", auth.hash_password(PASSWORD) if remote else None)
        monkeypatch.setattr(srv, "SESSION_SECRET", b"test-secret" if remote else b"")
        server = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        port = server.server_address[1]

        def request(method, path, host=PUBLIC, body=None, headers=None):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            hdrs = {"Host": host, **(headers or {})}
            if body is not None:
                hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
            conn.request(method, path, body=body, headers=hdrs)
            response = conn.getresponse()
            data = response.read()
            conn.close()
            return response, data
        return request

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


def login(request, password=PASSWORD, **kw):
    return request("POST", "/login", body=urlencode({"password": password}), **kw)


def test_default_mode_is_unchanged(run):
    request = run(remote=False)
    assert request("GET", "/", host="localhost")[0].status == 200
    assert request("GET", "/api/repos", host="127.0.0.1")[0].status == 200
    assert request("GET", "/", host=PUBLIC)[0].status == 403
    assert request("GET", "/login", host="localhost")[0].status in (200, 404)


def test_remote_requires_sign_in(run):
    request = run(remote=True)
    response, _ = request("GET", "/")
    assert response.status == 303 and response.getheader("Location") == "/login"
    assert request("GET", "/api/repos")[0].status == 401
    assert request("GET", "/api/organization")[0].status == 401
    assert request("POST", "/api/repos", body="{}", headers={"Content-Type": "application/json"})[0].status == 401
    assert request("GET", "/", host="evil.example")[0].status == 403
    page, data = request("GET", "/login")
    assert page.status == 200 and b'type="password"' in data


def test_good_password_gives_a_locked_down_session(run):
    request = run(remote=True)
    response, _ = login(request)
    assert response.status == 303
    cookie = response.getheader("Set-Cookie")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Secure" in cookie
    session = cookie.split(";")[0]
    page, body = request("GET", "/", headers={"Cookie": session})
    assert page.status == 200 and b'data-remote="1"' in body
    assert request("GET", "/api/repos", headers={"Cookie": session})[0].status == 200
    assert page.getheader("X-Frame-Options") == "DENY" and page.getheader("X-Content-Type-Options") == "nosniff"


def test_wrong_password_is_rejected_then_locked_out(run):
    request = run(remote=True)
    for _ in range(auth.MAX_FAILURES):
        response, data = login(request, "nope")
        assert response.status == 401 and b"not right" in data
    locked, _ = login(request, "nope")
    assert locked.status == 429 and int(locked.getheader("Retry-After")) > 0
    # Even the right password waits out the lockout.
    assert login(request)[0].status == 429


def test_forged_and_expired_sessions_fail(run):
    request = run(remote=True)
    assert request("GET", "/api/repos", headers={"Cookie": "rrt_session=9999999999.deadbeef"})[0].status == 401
    expired = auth.make_token(b"test-secret", now=0)
    assert request("GET", "/api/repos", headers={"Cookie": f"rrt_session={expired}"})[0].status == 401
    other = auth.make_token(b"other-secret")
    assert request("GET", "/api/repos", headers={"Cookie": f"rrt_session={other}"})[0].status == 401


def test_writes_must_be_same_origin_and_logout_clears(run):
    request = run(remote=True)
    session = login(request)[0].getheader("Set-Cookie").split(";")[0]
    cross = request("POST", "/api/repos/validate", body="{}", headers={
        "Cookie": session, "Origin": "https://evil.example", "Content-Type": "application/json"})
    assert cross[0].status == 403
    same = request("POST", "/api/repos/validate", body='{"path": "/nonexistent"}', headers={
        "Cookie": session, "Origin": f"https://{PUBLIC}", "Content-Type": "application/json"})
    assert same[0].status == 200
    out, _ = request("POST", "/logout", body="", headers={"Cookie": session})
    assert out.status == 303 and "Max-Age=0" in out.getheader("Set-Cookie")


def test_password_hashing_and_startup_guard(monkeypatch, tmp_path):
    stored = auth.hash_password("a long enough secret")
    assert auth.verify_password("a long enough secret", stored)
    assert not auth.verify_password("another secret", stored)
    assert not auth.verify_password("x", "not-a-hash")
    assert auth.hash_password("same") != auth.hash_password("same")
    monkeypatch.setenv("RRT_PUBLIC_HOST", PUBLIC)
    monkeypatch.delenv("RRT_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("RRT_PASSWORD_HASH_FILE", raising=False)
    with pytest.raises(SystemExit):
        srv.configure_remote()


def test_session_key_file_is_private_and_stable(tmp_path, monkeypatch):
    monkeypatch.delenv("RRT_SECRET", raising=False)
    first = auth.load_secret(tmp_path)
    assert auth.load_secret(tmp_path) == first
    assert (tmp_path / "session.key").stat().st_mode & 0o777 == 0o600
