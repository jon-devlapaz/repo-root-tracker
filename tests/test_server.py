"""The localhost server: scan-then-status flow, only scanned paths are queryable, loopback only, removed endpoints gone."""

import http.client
import json
import threading
from pathlib import Path

import pytest
from gitfix import commit, git, init, with_origin

from repo_root_tracker import server as srv
from repo_root_tracker.github import CiState


@pytest.fixture()
def tree(tmp_path):
    root = tmp_path / "root"
    alpha, _ = with_origin(root, "alpha")
    init(root / "beta")
    return root, alpha


@pytest.fixture()
def live(tree):
    root, alpha = tree
    server = srv.make_server(0, [str(root)])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def call(method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        try:
            data = json.loads(raw)
        except ValueError:
            data = raw
        return response.status, data, dict(response.getheaders())

    call.port, call.server, call.root, call.alpha = port, server, root, alpha
    yield call
    server.shutdown()
    server.server_close()


def real(path: Path) -> str:
    return str(path.resolve())


def test_binds_loopback_only(live):
    assert live.server.server_address[0] == "127.0.0.1"


def test_the_page_is_small_self_contained_and_locked_down(live):
    status, html, headers = live("GET", "/")
    assert status == 200 and html.startswith(b"<!doctype html>") and len(html) < 61440
    assert b"data:image" not in html and b"http://" not in html and b"https://" not in html
    assert "default-src 'none'" in headers["Content-Security-Policy"] and "connect-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY" and headers["Cache-Control"] == "no-store"


def test_scan_then_status_flow(live):
    status, scan, _ = live("GET", "/api/scan")
    assert status == 200 and not scan["truncated"]
    paths = sorted(c["path"] for c in scan["checkouts"])
    assert paths == sorted([real(live.alpha), real(live.root / "beta")])
    status, alpha, _ = live("GET", "/api/repos/status?path=" + real(live.alpha))
    assert status == 200 and alpha["branch"] == "main" and alpha["golden"]["status"] == "golden pending CI"
    status, beta, _ = live("GET", "/api/repos/status?path=" + real(live.root / "beta"))
    assert beta["golden"]["status"] == "not golden" and beta["golden"]["headline"] == "no origin remote"


def test_only_paths_the_scan_found_can_be_queried(live):
    for path in ("/etc", "/", str(live.root.parent), real(live.alpha) + "/..", "relative"):
        for route in ("/api/repos/status", "/api/ci"):
            assert live("GET", f"{route}?path={path}")[0] == 404, (route, path)
        assert live("POST", f"/api/fetch?path={path}")[0] == 404
    assert live("GET", "/api/repos/status")[0] == 400 and live("GET", "/api/repos/status?path=")[0] == 400


def test_hosts_other_than_loopback_are_refused(live):
    for host in ("evil.example", "evil.example:7842", "127.0.0.1.evil.example", "0.0.0.0"):
        assert live("GET", "/api/scan", {"Host": host})[0] == 403, host
    for host in (f"127.0.0.1:{live.port}", f"localhost:{live.port}", "localhost", f"[::1]:{live.port}"):
        assert live("GET", "/api/scan", {"Host": host})[0] == 200, host


def test_cross_site_posts_are_refused_and_local_ones_allowed(live):
    assert live("POST", "/api/scan", {"Origin": "https://evil.example"})[0] == 403
    assert live("POST", "/api/scan", {"Origin": f"http://127.0.0.1:{live.port}"})[0] == 200
    assert live("POST", "/api/scan")[0] == 200
    assert live("OPTIONS", "/api/scan")[0] == 405


def test_the_old_registration_organization_and_detail_endpoints_are_gone(live):
    for method, path in [("GET", "/api/repos"), ("POST", "/api/repos"), ("DELETE", "/api/repos"), ("PUT", "/api/organization"),
                         ("GET", "/api/organization"), ("GET", "/api/activity"), ("GET", "/api/repo"), ("GET", "/api/github"),
                         ("GET", "/api/commit"), ("GET", "/api/working-diff"), ("GET", "/login"), ("POST", "/login")]:
        assert live(method, path)[0] in (404, 501), (method, path)


def test_rescan_picks_up_a_new_repo_and_the_old_scan_is_replaced(live, tree):
    root, _ = tree
    assert len(live("GET", "/api/scan")[1]["checkouts"]) == 2
    init(root / "gamma")
    assert len(live("GET", "/api/scan")[1]["checkouts"]) == 2  # cached until asked
    status, scan, _ = live("POST", "/api/scan")
    assert status == 200 and len(scan["checkouts"]) == 3
    assert live("GET", "/api/repos/status?path=" + real(root / "gamma"))[0] == 200


def test_a_repo_deleted_after_the_scan_is_gone_not_clean(live):
    import shutil
    live("GET", "/api/scan")
    shutil.rmtree(live.root / "beta")
    status, body, _ = live("GET", "/api/repos/status?path=" + real(live.root / "beta"))
    assert status == 410 and body["gone"] is True


def test_ci_state_feeds_the_golden_verdict_on_later_status_calls(live, monkeypatch):
    live("GET", "/api/scan")
    path = real(live.alpha)
    for state, expected in (("passing", "golden"), ("failing", "not golden"), ("pending", "golden pending CI")):
        monkeypatch.setattr(srv, "get_default_branch_ci", lambda p, refresh=False, s=state: CiState(state=s, repo="o/r"))
        status, body, _ = live("GET", f"/api/ci?path={path}&refresh=1")
        assert status == 200 and body["ci"]["state"] == state
        assert live("GET", "/api/repos/status?path=" + path)[1]["golden"]["status"] == expected


def test_fetch_updates_remote_refs_and_returns_fresh_status(live):
    live("GET", "/api/scan")
    other = live.root.parent / "other-clone"  # a different clone, so this checkout cannot already know about it
    git(live.root, "clone", "-q", git(live.alpha, "remote", "get-url", "origin"), str(other))
    git(other, "push", "-q", "origin", "main:extra")
    path = real(live.alpha)
    assert "origin/extra" not in live("GET", "/api/repos/status?path=" + path)[1]["remote_branches"]
    status, body, _ = live("POST", "/api/fetch?path=" + path)
    assert status == 200 and "origin/extra" in body["remote_branches"]
    assert body["golden"]["headline"] == "other remote branch: origin/extra"


def test_fetch_failure_is_reported_not_hidden(live):
    live("GET", "/api/scan")
    git(live.alpha, "remote", "set-url", "origin", str(live.root / "nowhere"))
    status, body, _ = live("POST", "/api/fetch?path=" + real(live.alpha))
    assert status == 503 and "fetch failed" in body["error"]


def test_missing_root_is_reported_on_the_scan(tmp_path):
    server = srv.make_server(0, [str(tmp_path / "nope")])
    try:
        assert srv.current_scan().missing_roots == [str(tmp_path / "nope")] and srv.current_scan().checkouts == []
    finally:
        server.server_close()


def test_no_password_or_remote_access_settings_exist_anymore():
    for name in ("PUBLIC_HOSTS", "PASSWORD_HASH", "SESSION_SECRET", "configure_remote", "REPOS_FILE", "CONFIG_DIR"):
        assert not hasattr(srv, name), name
