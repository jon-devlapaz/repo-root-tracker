"""Tests for repo_root_tracker.status — v2 dashboard signals."""

from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from repo_root_tracker import server as srv
from repo_root_tracker.status import (
    GitNotAvailableError,
    get_repo_status,
)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(r), "config", "user.email", "t@t.t"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(r), "config", "user.name", "t"],
        check=True, capture_output=True,
    )
    (r / "a.txt").write_text("hello")
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(r), "commit", "-m", "first"], check=True, capture_output=True
    )
    return r


# ---------------------------------------------------------------------------
# Branch + last commit (AC-2)
# ---------------------------------------------------------------------------

def test_branch_and_last_commit(repo: Path) -> None:
    s = get_repo_status(repo)
    assert s.branch in ("master", "main")
    assert s.last_commit.subject == "first"
    assert len(s.last_commit.hash) == 7
    assert s.last_commit.relative != ""


def test_clean_repo_is_clean(repo: Path) -> None:
    s = get_repo_status(repo)
    assert s.dirty.is_clean is True
    assert s.dirty.modified == 0
    assert s.dirty.untracked == 0


# ---------------------------------------------------------------------------
# Dirty state (AC-1)
# ---------------------------------------------------------------------------

def test_modified_and_untracked_counts(repo: Path) -> None:
    (repo / "a.txt").write_text("changed")
    (repo / "new.txt").write_text("untracked")
    s = get_repo_status(repo)
    assert s.dirty.is_clean is False
    assert s.dirty.modified == 1
    assert s.dirty.untracked == 1


def test_staged_counts(repo: Path) -> None:
    (repo / "b.txt").write_text("staged")
    subprocess.run(["git", "-C", str(repo), "add", "b.txt"],
                   check=True, capture_output=True)
    s = get_repo_status(repo)
    assert s.dirty.staged == 1
    assert s.dirty.is_clean is False


# ---------------------------------------------------------------------------
# Sync (AC-3)
# ---------------------------------------------------------------------------

def test_no_upstream(repo: Path) -> None:
    s = get_repo_status(repo)
    assert s.sync.has_upstream is False


def test_ahead_of_upstream(tmp_path: Path, repo: Path) -> None:
    # Create a bare remote, push, then commit locally
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)],
                   check=True, capture_output=True)
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", branch],
                   check=True, capture_output=True)
    (repo / "c.txt").write_text("ahead")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "ahead"],
                   check=True, capture_output=True)
    s = get_repo_status(repo)
    assert s.sync.has_upstream is True
    assert s.sync.ahead == 1
    assert s.sync.behind == 0


# ---------------------------------------------------------------------------
# Stale branches (AC-4)
# ---------------------------------------------------------------------------

def test_no_stale_branches_on_fresh_repo(repo: Path) -> None:
    s = get_repo_status(repo)
    assert s.stale_branches == []


def test_stale_branch_detected(repo: Path) -> None:
    # Create a branch and backdate its commit
    subprocess.run(["git", "-C", str(repo), "checkout", "-b", "old-feature"],
                   check=True, capture_output=True)
    (repo / "old.txt").write_text("old")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    env = {"GIT_AUTHOR_DATE": "2020-01-01T00:00:00",
           "GIT_COMMITTER_DATE": "2020-01-01T00:00:00"}
    import os
    full_env = {**os.environ, **env}
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "old"],
                   check=True, capture_output=True, env=full_env)
    subprocess.run(["git", "-C", str(repo), "checkout", "-"],
                   check=True, capture_output=True)
    s = get_repo_status(repo)
    assert any(b.name == "old-feature" for b in s.stale_branches)


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

@pytest.fixture()
def live_server(tmp_path: Path, monkeypatch):
    from repo_root_tracker.server import Handler

    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setattr(srv, "CONFIG_DIR", cfg)
    monkeypatch.setattr(srv, "REPOS_FILE", cfg / "repos.json")

    import http.server

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 18743), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    yield "http://127.0.0.1:18743"
    httpd.shutdown()


def test_status_endpoint_tracked(live_server: str, repo: Path) -> None:
    # Register first (urllib.request already imported at module top)
    req = urllib.request.Request(
        live_server + "/api/repos",
        data=json.dumps({"path": str(repo)}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 201

    url = live_server + "/api/repos/status?path=" + urllib.parse.quote(str(repo))
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200
        data = json.loads(r.read().decode())
    assert data["branch"] in ("master", "main")
    assert data["last_commit"]["subject"] == "first"
    assert "dirty" in data
    assert "sync" in data
    assert "stale_branches" in data


def test_status_endpoint_untracked_404(live_server: str, tmp_path: Path) -> None:
    url = live_server + "/api/repos/status?path=" + urllib.parse.quote(str(tmp_path))
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(url, timeout=5)
    assert exc_info.value.code == 404


# ---------------------------------------------------------------------------
# Loud failures: missing directory must raise, never return fake-clean data
# ---------------------------------------------------------------------------

def test_status_missing_dir_raises(tmp_path: Path) -> None:
    from repo_root_tracker import NotARepositoryError
    with pytest.raises(NotARepositoryError):
        get_repo_status(tmp_path / "does-not-exist")
