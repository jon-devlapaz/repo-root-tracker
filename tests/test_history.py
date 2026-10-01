"""Tests for repo_root_tracker.history and the /api/activity endpoint."""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from repo_root_tracker import NotARepositoryError
from repo_root_tracker import server as srv
from repo_root_tracker.history import get_activity
from test_status import git, live_server, repo  # noqa: F401  (fixtures)


def test_activity_counts_commits_per_day(repo: Path) -> None:
    (repo / "b.txt").write_text("x")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "second")
    assert get_activity(repo, 30) == {date.today().isoformat(): 2}


def test_activity_includes_other_branches_and_ignores_old_commits(repo: Path) -> None:
    git(repo, "checkout", "-b", "feature/x")
    (repo / "c.txt").write_text("y")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "on a branch")
    git(repo, "checkout", "-")
    assert sum(get_activity(repo, 30).values()) == 2
    old = {"GIT_COMMITTER_DATE": "2020-01-01T12:00:00", "GIT_AUTHOR_DATE": "2020-01-01T12:00:00"}
    import os, subprocess
    (repo / "d.txt").write_text("z")
    git(repo, "add", "-A")
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "ancient"], check=True, capture_output=True, env={**os.environ, **old})
    assert sum(get_activity(repo, 30).values()) == 2  # the 2020 commit is outside the window


def test_activity_of_an_empty_repo_is_empty(tmp_path: Path) -> None:
    import subprocess
    r = tmp_path / "empty"
    r.mkdir()
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    assert get_activity(r, 30) == {}


def test_activity_of_a_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(NotARepositoryError):
        get_activity(tmp_path / "nope", 30)


def test_activity_endpoint_maps_every_tracked_repo(live_server: str, repo: Path) -> None:  # noqa: F811
    srv._ACTIVITY_CACHE.clear()
    req = urllib.request.Request(live_server + "/api/repos", data=json.dumps({"path": str(repo)}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req)
    data = json.loads(urllib.request.urlopen(live_server + "/api/activity?days=7").read())
    assert data["days"] == 7
    assert data["repos"][str(repo.resolve())] == {date.today().isoformat(): 1}


def test_activity_endpoint_rejects_a_bad_days_param(live_server: str) -> None:  # noqa: F811
    import urllib.error
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(live_server + "/api/activity?days=abc")
    assert err.value.code == 400
