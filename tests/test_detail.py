"""Tests for repo_root_tracker.detail — v3 drill-in view."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from repo_root_tracker import server as srv
from repo_root_tracker.detail import (
    get_commit_diff,
    get_repo_detail,
    get_working_diff,
)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "config", "user.email", "t@t.t"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "config", "user.name", "t"],
                   check=True, capture_output=True)
    (r / "a.txt").write_text("v1")
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "commit", "-m", "first"],
                   check=True, capture_output=True)
    (r / "a.txt").write_text("v2")
    subprocess.run(["git", "-C", str(r), "commit", "-am", "second"],
                   check=True, capture_output=True)
    return r


def test_detail_commits(repo: Path) -> None:
    d = get_repo_detail(repo)
    assert len(d.commits) == 2
    assert d.commits[0].subject == "second"
    assert d.commits[1].subject == "first"
    assert all(c.short for c in d.commits)
    assert all(c.relative for c in d.commits)


def test_detail_lanes_assigned(repo: Path) -> None:
    d = get_repo_detail(repo)
    assert all(isinstance(c.lane, int) and c.lane >= 0 for c in d.commits)


def test_detail_branches(repo: Path) -> None:
    d = get_repo_detail(repo)
    assert len(d.branches) >= 1
    current = [b for b in d.branches if b.current]
    assert len(current) == 1
    assert all(b.kind == "local" for b in d.branches)  # no remotes here


def test_detail_remote_branches(tmp_path: Path, repo: Path) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)],
                   check=True, capture_output=True)
    branch = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", branch],
                   check=True, capture_output=True)
    d = get_repo_detail(repo)
    remotes = [b for b in d.branches if b.kind == "remote"]
    assert len(remotes) == 1
    assert remotes[0].name == f"origin/{branch}"
    assert branch in remotes[0].tracked_by
    # Local branch now has an upstream
    local = [b for b in d.branches if b.kind == "local" and b.name == branch][0]
    assert local.has_upstream is True


def test_detail_no_remotes_section_when_none(repo: Path) -> None:
    d = get_repo_detail(repo)
    assert [b for b in d.branches if b.kind == "remote"] == []


def test_detail_changed_files_clean(repo: Path) -> None:
    d = get_repo_detail(repo)
    assert d.changed_files == []


def test_detail_changed_files_dirty(repo: Path) -> None:
    (repo / "a.txt").write_text("v3-dirty")
    (repo / "new.txt").write_text("untracked")
    d = get_repo_detail(repo)
    paths = {f.path for f in d.changed_files}
    assert "a.txt" in paths
    assert "new.txt" in paths
    assert any(f.untracked for f in d.changed_files if f.path == "new.txt")


def test_commit_diff(repo: Path) -> None:
    d = get_repo_detail(repo)
    diff = get_commit_diff(repo, d.commits[0].hash)
    assert "v2" in diff or "a.txt" in diff


def test_commit_diff_rejects_bad_hash(repo: Path) -> None:
    with pytest.raises(ValueError):
        get_commit_diff(repo, "../../etc/passwd")
    with pytest.raises(ValueError):
        get_commit_diff(repo, "")


def test_working_diff(repo: Path) -> None:
    (repo / "a.txt").write_text("v3-dirty")
    diff = get_working_diff(repo, "a.txt")
    assert "v3-dirty" in diff


def test_working_diff_rejects_traversal(repo: Path) -> None:
    with pytest.raises(ValueError):
        get_working_diff(repo, "../outside")
    with pytest.raises(ValueError):
        get_working_diff(repo, "/absolute")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@pytest.fixture()
def live_server(tmp_path: Path, monkeypatch):
    from repo_root_tracker.server import Handler

    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setattr(srv, "CONFIG_DIR", cfg)
    monkeypatch.setattr(srv, "REPOS_FILE", cfg / "repos.json")

    import http.server

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 18744), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    yield "http://127.0.0.1:18744"
    httpd.shutdown()


def _register(base: str, repo: Path) -> None:
    req = urllib.request.Request(
        base + "/api/repos",
        data=json.dumps({"path": str(repo)}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5):
        pass


def test_repo_endpoint(live_server: str, repo: Path) -> None:
    _register(live_server, repo)
    url = live_server + "/api/repo?path=" + urllib.parse.quote(str(repo))
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200
        data = json.loads(r.read().decode())
    assert len(data["commits"]) == 2
    assert "branches" in data
    assert "changed_files" in data


def test_repo_endpoint_untracked_404(live_server: str, tmp_path: Path) -> None:
    url = live_server + "/api/repo?path=" + urllib.parse.quote(str(tmp_path))
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(url, timeout=5)
    assert e.value.code == 404


def test_commit_endpoint(live_server: str, repo: Path) -> None:
    _register(live_server, repo)
    h = get_repo_detail(repo).commits[0].hash
    url = (live_server + "/api/commit?path=" + urllib.parse.quote(str(repo))
           + "&hash=" + h)
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200
        body = r.read().decode()
    assert "a.txt" in body


def test_working_diff_endpoint(live_server: str, repo: Path) -> None:
    _register(live_server, repo)
    (repo / "a.txt").write_text("endpoint-dirty")
    url = (live_server + "/api/working-diff?path=" + urllib.parse.quote(str(repo))
           + "&file=a.txt")
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200
        body = r.read().decode()
    assert "endpoint-dirty" in body


def test_detail_missing_dir_raises(tmp_path: Path) -> None:
    from repo_root_tracker import NotARepositoryError
    from repo_root_tracker.detail import get_commit_diff, get_working_diff
    with pytest.raises(NotARepositoryError):
        get_repo_detail(tmp_path / "does-not-exist")
    with pytest.raises(NotARepositoryError):
        get_commit_diff(tmp_path / "does-not-exist", "abc1234")
    with pytest.raises(NotARepositoryError):
        get_working_diff(tmp_path / "does-not-exist", "f.txt")


def test_working_diff_labels_staged_sections(repo: Path) -> None:
    from repo_root_tracker.detail import get_working_diff
    (repo / "a.txt").write_text("staged-change")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"],
                   check=True, capture_output=True)
    (repo / "a.txt").write_text("unstaged-change")
    diff = get_working_diff(repo, "a.txt")
    assert "--- staged ---" in diff
    assert "--- unstaged ---" in diff
