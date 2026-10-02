"""Tests for the repo-root-tracker web dashboard server."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from repo_root_tracker import server as srv
from repo_root_tracker.server import Handler, load_repos, save_repos, validate_repo


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch):
    """Point the server's config dir at a temp directory for test isolation."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setattr(srv, "CONFIG_DIR", cfg)
    monkeypatch.setattr(srv, "REPOS_FILE", cfg / "repos.json")
    yield cfg


def test_validate_repo_valid(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    result = validate_repo(str(tmp_path))
    assert result["valid"] is True
    assert result["root"] == str(tmp_path.resolve())


def test_validate_repo_from_subdirectory(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subdir = tmp_path / "nested"
    subdir.mkdir()
    result = validate_repo(str(subdir))
    assert result["valid"] is True
    assert result["root"] == str(tmp_path.resolve())


def test_validate_repo_invalid(tmp_path: Path) -> None:
    result = validate_repo(str(tmp_path))
    assert result["valid"] is False
    assert "error" in result


def test_load_repos_missing_file(isolated_config: Path) -> None:
    assert load_repos() == []


def test_save_and_load_roundtrip(isolated_config: Path) -> None:
    repos = [{"path": "/tmp/a"}, {"path": "/tmp/b"}]
    save_repos(repos)
    assert load_repos() == repos


def test_config_dir_created_on_save(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "newdir"
    monkeypatch.setattr(srv, "CONFIG_DIR", cfg)
    monkeypatch.setattr(srv, "REPOS_FILE", cfg / "repos.json")
    save_repos([{"path": "/tmp/x"}])
    assert cfg.is_dir()
    assert (cfg / "repos.json").is_file()


# ---------------------------------------------------------------------------
# Live-server integration test
# ---------------------------------------------------------------------------

@pytest.fixture()
def live_server(isolated_config: Path):
    """Start the dashboard server on a test port in a background thread."""
    import http.server

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 18742), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    yield "http://127.0.0.1:18742"
    httpd.shutdown()


def _get(url: str):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read().decode()


def _post(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_dashboard_html_served(live_server: str) -> None:
    status, body = _get(live_server + "/")
    assert status == 200
    assert "repo-root-tracker" in body
    assert "<style>" in body


def test_repos_api_crud(live_server: str, tmp_path: Path) -> None:
    # Start empty
    status, _ = _get(live_server + "/api/repos")
    assert status == 200

    # Reject non-repo
    code, data = _post(live_server + "/api/repos", {"path": str(tmp_path)})
    assert code == 400
    assert "valid" in data

    # Accept a real repo
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    code, data = _post(live_server + "/api/repos", {"path": str(tmp_path)})
    assert code == 201
    assert data["path"] == str(tmp_path.resolve())

    # List shows it
    status, body = _get(live_server + "/api/repos")
    assert status == 200
    assert str(tmp_path.resolve()) in body

    # Duplicate rejected
    code, _ = _post(live_server + "/api/repos", {"path": str(tmp_path)})
    assert code == 409

    # Delete works
    req = urllib.request.Request(
        live_server + "/api/repos",
        data=json.dumps({"path": str(tmp_path.resolve())}).encode(),
        headers={"Content-Type": "application/json"},
        method="DELETE",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200

    # Gone
    status, body = _get(live_server + "/api/repos")
    assert str(tmp_path.resolve()) not in body


def test_validate_endpoint(live_server: str, tmp_path: Path) -> None:
    code, data = _post(live_server + "/api/repos/validate", {"path": str(tmp_path)})
    assert code == 200
    assert data["valid"] is False

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    code, data = _post(live_server + "/api/repos/validate", {"path": str(tmp_path)})
    assert code == 200
    assert data["valid"] is True


def test_deleted_repo_returns_410_gone(live_server: str, tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "gone"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    req = urllib.request.Request(
        live_server + "/api/repos",
        data=json.dumps({"path": str(repo)}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5):
        pass
    shutil.rmtree(repo)

    for endpoint in ("/api/repos/status?path=", "/api/repo?path="):
        url = live_server + endpoint + urllib.parse.quote(str(repo.resolve()))
        try:
            urllib.request.urlopen(url, timeout=5)
            raise AssertionError(f"{endpoint} should not return 2xx for deleted repo")
        except urllib.error.HTTPError as e:
            assert e.code == 410, f"{endpoint} returned {e.code}, want 410"
            body = json.loads(e.read().decode())
            assert body.get("gone") is True


def test_malformed_repos_entries_filtered(isolated_config: Path) -> None:
    from repo_root_tracker.server import REPOS_FILE, load_repos
    REPOS_FILE.write_text(json.dumps([
        {"path": "/tmp/ok"},
        {"foo": 1},
        "not-a-dict",
        {"path": ""},
        {"path": None},
        42,
    ]))
    assert load_repos() == [{"path": "/tmp/ok"}]


def test_malformed_repos_file_shapes(isolated_config: Path) -> None:
    from repo_root_tracker.server import REPOS_FILE, load_repos
    REPOS_FILE.write_text(json.dumps({"path": "/tmp/nope"}))
    assert load_repos() == []
    REPOS_FILE.write_text("{broken json")
    assert load_repos() == []


def test_dashboard_home_value_is_json_encoded_and_guard_preserved(live_server, monkeypatch):
    monkeypatch.setattr(srv.Path, 'home', lambda: Path("/Users/it's-home"))
    status, body = _get(live_server + '/')
    assert status == 200
    assert 'const HOME_DIR = "/Users/it\'s-home";' in body
    assert "HOME_DIR !== '__HOME__'" in body


def test_non_git_directory_is_not_reported_as_clean(live_server, tmp_path):
    save_repos([{'path': str(tmp_path)}])
    url = live_server + '/api/repos/status?path=' + urllib.parse.quote(str(tmp_path))
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(url, timeout=5)
    assert error.value.code == 503
    assert 'error' in json.loads(error.value.read())


def test_github_refresh_is_explicit(live_server, tmp_path, monkeypatch):
    from repo_root_tracker.github import GithubInfo
    save_repos([{'path': str(tmp_path)}])
    calls = []

    def github(path, *, refresh=False):
        calls.append(refresh)
        return GithubInfo()

    monkeypatch.setattr(srv, 'get_github_info', github)
    url = live_server + '/api/github?path=' + urllib.parse.quote(str(tmp_path))
    assert _get(url)[0] == 200
    assert _get(url + '&refresh=1')[0] == 200
    assert calls == [False, True]


def test_repo_list_carries_project_identity_for_worktrees(tmp_path: Path) -> None:
    main = tmp_path / "main"
    wt = tmp_path / "wt"
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-b", "main", str(main)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(main), "commit", "--allow-empty", "-m", "x"], check=True, capture_output=True, env={**os.environ, **env})
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-b", "feat", str(wt)], check=True, capture_output=True)
    listed = srv.repos_with_identity([{"path": str(main)}, {"path": str(wt)}, {"path": str(tmp_path / "gone")}])
    by_path = {item["path"]: item for item in listed}
    assert by_path[str(main)]["project_id"] == by_path[str(wt)]["project_id"]
    assert by_path[str(main)]["is_worktree"] is False and by_path[str(wt)]["is_worktree"] is True
    assert by_path[str(wt)]["project_path"] == str(main.resolve())
    assert "project_id" not in by_path[str(tmp_path / "gone")]
