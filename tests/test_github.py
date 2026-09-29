"""Tests for repo_root_tracker.github — GH integration via gh CLI."""

from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

from repo_root_tracker import server as srv
from repo_root_tracker.github import (
    _rollup,
    clear_cache,
    get_github_info,
)


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Check rollup
# ---------------------------------------------------------------------------

def test_rollup_empty() -> None:
    s = _rollup([])
    assert s.state == "none" and s.total == 0


def test_rollup_all_pass() -> None:
    s = _rollup([
        {"status": "COMPLETED", "conclusion": "SUCCESS"},
        {"status": "COMPLETED", "conclusion": "NEUTRAL"},
    ])
    assert s.state == "pass" and s.passing == 2 and s.total == 2


def test_rollup_failure() -> None:
    s = _rollup([
        {"status": "COMPLETED", "conclusion": "SUCCESS"},
        {"status": "COMPLETED", "conclusion": "FAILURE"},
    ])
    assert s.state == "fail" and s.passing == 1 and s.total == 2


def test_rollup_pending() -> None:
    s = _rollup([
        {"status": "COMPLETED", "conclusion": "SUCCESS"},
        {"status": "IN_PROGRESS", "conclusion": ""},
    ])
    assert s.state == "pending"


# ---------------------------------------------------------------------------
# Remote detection (mocked git)
# ---------------------------------------------------------------------------

def _completed(stdout: str, code: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


def test_no_origin(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    info = get_github_info(tmp_path)
    assert info.has_github is False
    assert info.gh_unavailable is False


def test_non_github_remote(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "git@gitlab.com:foo/bar.git"],
                   check=True, capture_output=True)
    info = get_github_info(tmp_path)
    assert info.has_github is False


def test_github_https_remote_parsed(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "https://github.com/acme/widget.git"],
                   check=True, capture_output=True)
    with patch("repo_root_tracker.github._gh", return_value=[]):
        info = get_github_info(tmp_path)
    assert info.has_github is True
    assert info.repo == "acme/widget"
    assert info.repo_url == "https://github.com/acme/widget"


def test_github_ssh_remote_parsed(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "git@github.com:acme/widget.git"],
                   check=True, capture_output=True)
    with patch("repo_root_tracker.github._gh", return_value=[]):
        info = get_github_info(tmp_path)
    assert info.repo == "acme/widget"


def test_gh_failure_marks_unavailable(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "https://github.com/acme/widget.git"],
                   check=True, capture_output=True)
    with patch("repo_root_tracker.github._gh", return_value=None):
        info = get_github_info(tmp_path)
    assert info.has_github is False
    assert info.gh_unavailable is True


def test_prs_and_issues_mapped(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "https://github.com/acme/widget.git"],
                   check=True, capture_output=True)
    calls = {"n": 0}

    def fake_gh(*args, cwd):
        calls["n"] += 1
        if "pr" in args:
            return [{"number": 7, "title": "Fix it", "headRefName": "fix/x",
                     "url": "https://github.com/acme/widget/pull/7",
                     "statusCheckRollup": [{"status": "COMPLETED",
                                            "conclusion": "SUCCESS"}]}]
        return [{"number": 3, "title": "Bug", "url": "https://github.com/acme/widget/issues/3"}]

    with patch("repo_root_tracker.github._gh", side_effect=fake_gh):
        info = get_github_info(tmp_path)
    assert len(info.prs) == 1
    assert info.prs[0].number == 7
    assert info.prs[0].ci.state == "pass"
    assert len(info.issues) == 1
    assert info.issues[0].number == 3
    assert calls["n"] == 2


def test_cache_bounds_calls(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "https://github.com/acme/widget.git"],
                   check=True, capture_output=True)
    calls = {"n": 0}

    def fake_gh(*args, cwd):
        calls["n"] += 1
        return []

    with patch("repo_root_tracker.github._gh", side_effect=fake_gh):
        get_github_info(tmp_path)
        get_github_info(tmp_path)
        get_github_info(tmp_path)
    assert calls["n"] == 2  # one pr + one issue call, then cache hits


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@pytest.fixture()
def live_server(tmp_path: Path, monkeypatch):
    from repo_root_tracker.server import Handler

    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setattr(srv, "CONFIG_DIR", cfg)
    monkeypatch.setattr(srv, "REPOS_FILE", cfg / "repos.json")

    import http.server

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 18745), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    yield "http://127.0.0.1:18745"
    httpd.shutdown()


def test_endpoint_no_remote(live_server: str, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
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
    url = live_server + "/api/github?path=" + urllib.parse.quote(str(repo))
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200
        data = json.loads(r.read().decode())
    assert data["has_github"] is False


def test_endpoint_untracked_404(live_server: str, tmp_path: Path) -> None:
    url = live_server + "/api/github?path=" + urllib.parse.quote(str(tmp_path))
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(url, timeout=5)
    assert e.value.code == 404


def test_endpoint_live_github(live_server: str) -> None:
    """Live test against tink-route (real PRs). Skipped without gh auth."""
    tink_route = Path("/Users/jondev/dev/active/tink-route")
    if not (tink_route / ".git").exists():
        pytest.skip("tink-route checkout not present")
    probe = subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=10)
    if probe.returncode != 0:
        pytest.skip("gh not authenticated")
    req = urllib.request.Request(
        live_server + "/api/repos",
        data=json.dumps({"path": str(tink_route)}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except urllib.error.HTTPError:
        pass  # already tracked is fine
    url = live_server + "/api/github?path=" + urllib.parse.quote(str(tink_route))
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read().decode())
    assert data["has_github"] is True
    assert data["repo"] == "jon-devlapaz/tink-route"
    assert len(data["prs"]) >= 1
