"""Status facts and the golden verdict, against real repositories and a real bare remote."""

import os
import time

import pytest
from gitfix import commit, git, init, with_origin

from repo_root_tracker import NotARepositoryError
from repo_root_tracker.github import get_default_branch_ci
from repo_root_tracker.status import fetch_origin, get_repo_status


def test_a_fresh_pushed_main_has_every_local_golden_fact(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    s = get_repo_status(repo)
    assert (s.branch, s.dirty.is_clean, s.dirty.total) == ("main", True, 0)
    assert (s.sync.has_upstream, s.sync.ahead, s.sync.behind) == (True, 0, 0)
    assert (s.has_origin, s.remote_branches, s.branches, s.other_worktrees) == (True, ["origin/main"], ["main"], [])
    assert (s.is_worktree, s.last_commit.subject) == (False, "first")
    assert s.golden().status == "golden pending CI"
    assert s.golden("passing").status == "golden"
    assert s.golden("failing").status == "not golden"


def test_to_dict_carries_the_verdict_and_the_dirty_total(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    (repo / "new.txt").write_text("u")
    (repo / "file.txt").write_text("changed\n")
    data = get_repo_status(repo).to_dict(ci="passing")
    assert data["dirty"]["total"] == 2 and not data["dirty"]["is_clean"]
    assert data["golden"]["status"] == "not golden" and data["golden"]["headline"] == "2 uncommitted changes"


def test_an_extra_remote_branch_makes_it_not_golden(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    git(repo, "push", "-q", "origin", "main:feature")
    git(repo, "fetch", "-q")
    s = get_repo_status(repo)
    assert s.remote_branches == ["origin/feature", "origin/main"]
    assert s.golden("passing").reasons == ["other remote branch: origin/feature"]


def test_an_extra_local_branch_and_being_off_main(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    git(repo, "switch", "-q", "-c", "work")
    s = get_repo_status(repo)
    assert s.branch == "work" and s.branches == ["main", "work"]
    assert s.golden("passing").reasons[0] == "on work, not main"


def test_ahead_and_behind_come_from_the_upstream(tmp_path):
    repo, bare = with_origin(tmp_path, "r")
    commit(repo, "a.txt", message="local only")
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    commit(other, "b.txt", message="remote only")
    git(other, "push", "-q", "origin", "main")
    git(repo, "fetch", "-q")
    s = get_repo_status(repo)
    assert (s.sync.ahead, s.sync.behind) == (1, 1)
    assert "not even with origin/main (ahead 1, behind 1)" in s.golden("passing").reasons


def test_no_origin_and_no_upstream(tmp_path):
    repo = init(tmp_path / "solo")
    s = get_repo_status(repo)
    assert (s.has_origin, s.remote_branches, s.sync.has_upstream) == (False, [], False)
    assert s.golden("passing").reasons == ["no origin remote"]


def test_extra_worktrees_are_counted_for_the_main_checkout_and_the_worktree_is_not_judged(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    git(repo, "worktree", "add", "-q", "-b", "side", str(tmp_path / "side"))
    main, side = get_repo_status(repo), get_repo_status(tmp_path / "side")
    assert [os.path.realpath(w) for w in main.other_worktrees] == [os.path.realpath(tmp_path / "side")]
    assert "1 extra worktree" in main.golden("passing").reasons
    assert side.is_worktree and side.project_path == main.project_path == str(repo.resolve())
    assert side.golden().status == "worktree"


def test_a_repo_with_no_commits_does_not_crash(tmp_path):
    import subprocess
    bare = tmp_path / "empty"
    subprocess.run(["git", "init", "-q", str(bare)], check=True, capture_output=True)
    s = get_repo_status(bare)
    assert s.branch and s.last_commit.subject == ""


def test_a_missing_path_is_an_error_not_a_clean_repo(tmp_path):
    with pytest.raises(NotARepositoryError):
        get_repo_status(tmp_path / "gone")


def test_reading_status_never_writes_to_the_repository(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    (repo / "file.txt").touch()  # stat-dirty index, the case where `git status` would normally rewrite it
    time.sleep(1.1)
    index = repo / ".git" / "index"
    before = (index.stat().st_mtime_ns, index.read_bytes())
    for _ in range(3):
        get_repo_status(repo)
    assert (index.stat().st_mtime_ns, index.read_bytes()) == before
    assert not (repo / ".git" / "index.lock").exists()


def test_fetch_updates_remote_refs_and_only_remote_refs(tmp_path):
    repo, bare = with_origin(tmp_path, "r")
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    commit(other, "b.txt", message="upstream moved")
    git(other, "push", "-q", "origin", "main")
    git(other, "push", "-q", "origin", "main:extra")
    (repo / "file.txt").write_text("my edit\n")
    head, branches, tree = git(repo, "rev-parse", "HEAD"), git(repo, "branch", "--list"), (repo / "file.txt").read_text()
    assert get_repo_status(repo).sync.behind == 0
    fetch_origin(repo)
    after = get_repo_status(repo)
    assert after.sync.behind == 1 and "origin/extra" in after.remote_branches
    assert after.last_fetch_at
    assert (git(repo, "rev-parse", "HEAD"), git(repo, "branch", "--list"), (repo / "file.txt").read_text()) == (head, branches, tree)


def test_fetch_prunes_deleted_remote_branches(tmp_path):
    repo, bare = with_origin(tmp_path, "r")
    git(repo, "push", "-q", "origin", "main:gone")
    fetch_origin(repo)
    assert "origin/gone" in get_repo_status(repo).remote_branches
    other = tmp_path / "other"  # deleted from a different clone: this checkout's tracking ref only goes away by pruning
    git(tmp_path, "clone", "-q", str(bare), str(other))
    git(other, "push", "-q", "origin", "--delete", "gone")
    assert "origin/gone" in get_repo_status(repo).remote_branches
    fetch_origin(repo)
    assert "origin/gone" not in get_repo_status(repo).remote_branches


def test_fetch_failure_is_an_error_and_never_hangs(tmp_path):
    repo, bare = with_origin(tmp_path, "r")
    git(repo, "remote", "set-url", "origin", str(tmp_path / "no-such-remote"))
    with pytest.raises(RuntimeError):
        fetch_origin(repo)


def test_ci_is_none_when_there_is_no_github_remote(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    assert get_default_branch_ci(repo).state == "none"
    assert get_repo_status(repo).github_repo == ""


def test_each_extra_branch_says_whether_git_can_show_it_is_merged(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    git(repo, "branch", "merged-local")  # same commit as main: nothing unmerged
    git(repo, "switch", "-q", "-c", "unmerged-local")
    commit(repo, "u.txt", message="only on this branch")
    commit(repo, "v.txt", message="and another")
    git(repo, "switch", "-q", "main")
    git(repo, "push", "-q", "origin", "main:merged-remote", "unmerged-local")
    details = {(d["scope"], d["name"]): d for d in get_repo_status(repo).branch_details}
    assert set(details) == {("local", "merged-local"), ("local", "unmerged-local"), ("remote", "origin/merged-remote"), ("remote", "origin/unmerged-local")}
    assert details[("local", "merged-local")]["merged"] is True and details[("local", "merged-local")]["unmerged"] == 0
    assert details[("remote", "origin/merged-remote")]["merged"] is True
    assert (details[("local", "unmerged-local")]["merged"], details[("local", "unmerged-local")]["unmerged"]) == (False, 2)
    assert details[("remote", "origin/unmerged-local")]["unmerged"] == 2
    assert all(d["last_commit_date"] and d["relative"] for d in details.values())


def test_a_rebase_merged_branch_reads_as_merged_but_a_squash_merge_cannot_be_seen(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    git(repo, "switch", "-q", "-c", "rebased")
    commit(repo, "r.txt", message="rebased work")
    git(repo, "switch", "-q", "-c", "squashed", "main")
    commit(repo, "s1.txt", message="squash me 1")
    commit(repo, "s2.txt", message="squash me 2")
    git(repo, "switch", "-q", "main")
    commit(repo, "moved.txt", message="main moved on")  # so the cherry-pick below is a new commit, not the same one
    git(repo, "cherry-pick", "rebased")  # the same patch lands on main as a new commit: a rebase merge
    git(repo, "merge", "-q", "--squash", "squashed")
    git(repo, "commit", "-q", "-m", "squash merge of squashed")
    assert "rebased" not in git(repo, "branch", "--merged", "main")  # the case plain --merged gets wrong
    details = {d["name"]: d for d in get_repo_status(repo).branch_details}
    assert details["rebased"]["merged"] is True and details["rebased"]["unmerged"] == 0
    assert details["squashed"]["merged"] is False and details["squashed"]["unmerged"] == 2  # honest limit: git cannot tell


def test_branch_details_are_skipped_for_linked_worktrees_and_empty_when_there_are_no_extras(tmp_path):
    repo, _ = with_origin(tmp_path, "r")
    assert get_repo_status(repo).branch_details == []
    git(repo, "worktree", "add", "-q", "-b", "side", str(tmp_path / "side"))
    assert get_repo_status(tmp_path / "side").branch_details == []
    assert [d["name"] for d in get_repo_status(repo).branch_details] == ["side"]


def test_branch_details_are_capped(tmp_path):
    from repo_root_tracker.status import MAX_BRANCH_DETAILS
    repo, _ = with_origin(tmp_path, "r")
    for i in range(MAX_BRANCH_DETAILS + 5):
        git(repo, "branch", f"b{i:03}")
    assert len(get_repo_status(repo).branch_details) == MAX_BRANCH_DETAILS
