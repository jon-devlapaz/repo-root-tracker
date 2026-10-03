import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from repo_root_tracker.changes import parse_changes
from repo_root_tracker.detail import get_repo_detail
from repo_root_tracker.github import _rollup, clear_cache, get_github_info
from repo_root_tracker.status import get_repo_status


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    repo = tmp_path / "project"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "tracked.txt").write_text("first\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial")
    return repo


@pytest.mark.parametrize("xy,kind", [(" D", "deleted"), ("D ", "deleted"), ("A ", "added"), (" M", "modified"), (" T", "type changed"), ("UU", "conflicted"), ("AA", "conflicted"), ("DD", "conflicted"), ("??", "untracked")])
def test_change_kinds(xy, kind):
    change = parse_changes(xy + " path\0")[0]
    assert change.kind == kind
    if kind == "conflicted":
        assert not change.staged


def test_deleted_file_is_not_labeled_modified(repo):
    (repo / "tracked.txt").unlink()
    detail = get_repo_detail(repo)
    assert detail.changed_files[0].kind == "deleted"
    assert get_repo_status(repo).dirty.kinds == {"deleted": 1}


def test_rename_paths_keep_special_characters(repo):
    destination = 'renamed -> "雪"\nfile.txt'
    git(repo, "mv", "tracked.txt", destination)
    change = get_repo_detail(repo).changed_files[0]
    assert change.kind == "renamed"
    assert change.path == destination
    assert change.original_path == "tracked.txt"
    (repo / destination).write_text("changed\n")
    change = get_repo_detail(repo).changed_files[0]
    assert change.kind == "renamed"
    assert change.worktree_kind == "modified"


def test_conflict_from_real_git_merge(repo):
    original = git(repo, "branch", "--show-current")
    git(repo, "checkout", "-b", "side")
    (repo / "tracked.txt").write_text("side\n")
    git(repo, "commit", "-am", "side")
    git(repo, "checkout", original)
    (repo / "tracked.txt").write_text("main\n")
    git(repo, "commit", "-am", "main")
    result = subprocess.run(["git", "-C", str(repo), "merge", "side"], capture_output=True)
    assert result.returncode == 1
    assert get_repo_detail(repo).changed_files[0].kind == "conflicted"
    assert get_repo_status(repo).dirty.kinds == {"conflicted": 1}


def test_worktree_family_is_from_git_not_name(repo, tmp_path):
    checkout = tmp_path / "unrelated-name"
    git(repo, "worktree", "add", "--detach", str(checkout))
    main = get_repo_status(repo)
    linked = get_repo_status(checkout)
    assert main.project_id == linked.project_id
    assert main.project_path == linked.project_path == str(repo)
    assert not main.is_worktree
    assert linked.is_worktree
    assert main.checked_at and linked.checked_at
    assert main.last_fetch_at == ""


def test_pending_check_does_not_hide_failure():
    summary = _rollup([{"status": "COMPLETED", "conclusion": "FAILURE"}, {"status": "IN_PROGRESS"}])
    assert summary.state == "fail"
    assert summary.failing == 1 and summary.pending == 1


def test_legacy_github_status_contexts():
    summary = _rollup([{"state": "SUCCESS"}, {"state": "ERROR"}, {"state": "PENDING"}])
    assert (summary.state, summary.passing, summary.failing, summary.pending) == ("fail", 1, 1, 1)


def test_github_partial_failure_is_explicit_and_refresh_bypasses_cache(repo):
    git(repo, "remote", "add", "origin", "https://github.com/test/project.git")
    clear_cache()
    with patch("repo_root_tracker.github._gh", side_effect=[None, [], None, None]) as run:
        first = get_github_info(repo)
        cached = get_github_info(repo)
        assert cached is first
        assert first.has_github
        assert first.errors and "Pull requests" in first.errors[0]
        assert first.checked_at
        assert run.call_count == 4
    with patch("repo_root_tracker.github._gh", side_effect=[
        [], [], [0], [{"default_branch": "trunk"}], [{"sha": "a" * 40}],
        [{"total_count": 0, "workflows": []}], [{"total_count": 0, "workflow_runs": []}],
    ]) as run:
        refreshed = get_github_info(repo, refresh=True)
        assert not refreshed.errors
        assert run.call_count == 7
    clear_cache()


def test_github_cache_deduplicates_worktrees_and_maps_review_signals(repo, tmp_path):
    git(repo, "remote", "add", "origin", "https://github.com/test/project.git")
    checkout = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", str(checkout))
    clear_cache()

    def gh(*args, cwd):
        if args[0] == "pr":
            return [{"number": 1, "reviewDecision": "CHANGES_REQUESTED", "mergeable": "CONFLICTING", "isDraft": True}]
        return []

    with patch("repo_root_tracker.github._gh", side_effect=gh) as run:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(get_github_info, [repo, checkout]))
        assert run.call_count == 4
        assert results[0] is results[1]
        assert results[0].prs[0].review_decision == "CHANGES_REQUESTED"
        assert results[0].prs[0].mergeable == "CONFLICTING"
        assert results[0].prs[0].draft
    clear_cache()


def test_home_template_substitutes_only_the_value():
    from repo_root_tracker.server import ASSET
    body = ASSET.read_bytes().replace(b'"__HOME__"', json.dumps('/Users/it\'s-home').encode(), 1).decode()
    assert 'const HOME_DIR = "/Users/it\'s-home";' in body
    assert "HOME_DIR !== '__HOME__'" in body


def test_last_fetch_time_uses_each_checkouts_git_path(repo, tmp_path):
    import os
    checkout = tmp_path / 'linked'
    git(repo, 'worktree', 'add', '--detach', str(checkout))
    main_fetch = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-path', 'FETCH_HEAD'))
    linked_fetch = Path(git(checkout, 'rev-parse', '--path-format=absolute', '--git-path', 'FETCH_HEAD'))
    main_fetch.write_text('metadata')
    linked_fetch.write_text('metadata')
    os.utime(main_fetch, (946684800, 946684800))
    os.utime(linked_fetch, (1577836800, 1577836800))
    assert get_repo_status(repo).last_fetch_at.startswith('2000-01-01')
    assert get_repo_status(checkout).last_fetch_at.startswith('2020-01-01')
