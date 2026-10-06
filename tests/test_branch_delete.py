"""When a branch may be deleted: the server's verdict, one rule at a time, on real repositories with a real bare origin.
gh is stubbed (no network); git is never mocked. Rules that only need to read the repository share one status read."""

import dataclasses

import pytest
from gitfix import commit, git

from repo_root_tracker import branch_delete as bd
from repo_root_tracker.status import get_repo_status

NO_PRS = lambda slug, branch, cwd: []  # noqa: E731


def prs(*rows):
    """A gh stub answering with these pull requests (state, number) for every branch, each at the given tip."""
    return lambda slug, branch, cwd: [{"number": n, "state": state, "headRefName": branch, "headRefOid": tip} for state, n, tip in rows]


@pytest.fixture(scope="session")
def template_status(branch_template):
    return get_repo_status(branch_template / "r")  # read once; judging never changes it


@pytest.fixture()
def judge(template_status, monkeypatch):
    monkeypatch.setattr(bd, "pull_requests", NO_PRS)
    return lambda scope, branch, *, slug="o/r", sha=None: bd.judge(dataclasses.replace(template_status, github_repo=slug), scope, branch, sha=sha)


@pytest.fixture()
def world(branch_world, monkeypatch):
    monkeypatch.setattr(bd, "pull_requests", NO_PRS)
    return branch_world


def look(repo, scope, branch, *, slug="o/r", sha=None):
    status = get_repo_status(repo)
    status.github_repo = slug
    return bd.judge(status, scope, branch, sha=sha)


def tip(status, scope, name):
    return next(d["sha"] for d in status.branch_details if d["scope"] == scope and d["name"] == name)


def test_merged_branches_may_go_and_unmerged_ones_may_not(judge):
    for scope in ("local", "remote"):
        v = judge(scope, "done")
        assert v.ok and v.kind == "merged" and v.reason == "merged into main"
        v = judge(scope, "wip")
        assert not v.ok and "not on main" in v.reason


def test_an_open_pull_request_beats_everything_even_a_merged_branch_or_an_earlier_closed_one(judge, template_status, monkeypatch):
    done = tip(template_status, "remote", "origin/done")
    monkeypatch.setattr(bd, "pull_requests", prs(("OPEN", 7, done)))
    v = judge("remote", "done")
    assert not v.ok and v.pr == 7 and "open pull request, #7" in v.reason
    wip = tip(template_status, "remote", "origin/wip")
    monkeypatch.setattr(bd, "pull_requests", prs(("CLOSED", 1, wip), ("OPEN", 2, wip)))
    assert not judge("remote", "wip").ok


def test_the_remote_branch_of_a_closed_unmerged_pull_request_may_go_only_at_the_tip_that_was_reviewed(judge, template_status, monkeypatch):
    wip = tip(template_status, "remote", "origin/wip")
    monkeypatch.setattr(bd, "pull_requests", prs(("CLOSED", 11, wip)))
    v = judge("remote", "wip")
    assert v.ok and v.kind == "closed-pr" and v.pr == 11 and "refs/pull/11/head" in v.reason
    monkeypatch.setattr(bd, "pull_requests", prs(("CLOSED", 11, "0" * 40)))
    v = judge("remote", "wip")
    assert not v.ok and "newer than closed pull request #11" in v.reason


def test_a_closed_pull_request_never_makes_a_local_branch_deletable(judge, template_status, monkeypatch):
    monkeypatch.setattr(bd, "pull_requests", prs(("CLOSED", 11, tip(template_status, "local", "wip"))))
    assert not judge("local", "wip").ok  # a local -D would throw away commits that exist nowhere else


def test_when_gh_cannot_answer_nothing_is_deletable_and_without_a_github_remote_it_is_not_asked(judge, monkeypatch):
    monkeypatch.setattr(bd, "pull_requests", lambda s, b, c: None)
    v = judge("remote", "done")
    assert not v.ok and "could not ask GitHub" in v.reason
    monkeypatch.setattr(bd, "pull_requests", lambda s, b, c: pytest.fail("gh must not be asked without a GitHub remote"))
    assert judge("remote", "done", slug="").ok


def test_a_stale_sha_unknown_branches_bad_scopes_and_bad_names_are_refused(judge, template_status):
    now = tip(template_status, "remote", "origin/done")
    assert judge("remote", "done", sha=now).ok
    assert "moved" in judge("remote", "done", sha="0" * 40).reason
    assert not judge("remote", "nope").ok
    assert judge("tag", "done").reason == "scope must be local or remote"
    assert judge("local", "-x").reason == "not a usable branch name"
    assert not judge("remote", "main").ok and not judge("local", "main").ok  # main is never even listed


@pytest.mark.parametrize("name", ["", "-x", "--force", "a..b", "a b", "x.lock", "/x", "a\0b"])
def test_malformed_names_are_not_usable(name):
    assert not bd.valid_name(name)


def test_a_branch_merged_by_patch_may_go(world):
    repo, _ = world
    git(repo, "switch", "-q", "-c", "feat")
    commit(repo, "a.txt", message="a")
    git(repo, "switch", "-q", "main")
    git(repo, "cherry-pick", "feat")  # main gets an equivalent patch, a different commit
    v = look(repo, "local", "feat")
    assert v.ok and v.kind == "merged"


def test_the_default_branch_is_never_deletable(world):
    repo, _ = world
    git(repo, "push", "-q", "origin", "main:develop", "main:master")
    git(repo, "remote", "set-head", "origin", "develop")
    git(repo, "fetch", "-q", "origin")
    status = get_repo_status(repo)
    status.github_repo = "o/r"
    assert bd.judge(status, "remote", "develop").reason == "this is the default branch"
    assert bd.judge(status, "remote", "master").reason == "this is the default branch"
    assert bd.judge(status, "remote", "done").ok  # the rule is about those names, not about every merged branch


def test_a_branch_that_is_checked_out_anywhere_is_refused_locally(world, tmp_path):
    repo, _ = world
    git(repo, "switch", "-q", "done")
    assert look(repo, "local", "done").reason == "this branch is checked out"
    assert look(repo, "remote", "done").ok  # the remote copy is not what is checked out
    git(repo, "switch", "-q", "main")
    git(repo, "worktree", "add", "-q", str(tmp_path / "wt"), "done")
    assert look(repo, "local", "done").reason == "this branch is checked out"


def test_linked_worktrees_are_refused(world, tmp_path):
    repo, _ = world
    git(repo, "worktree", "add", "-q", "-b", "other", str(tmp_path / "wt2"))
    assert not bd.judge(get_repo_status(tmp_path / "wt2"), "local", "done").ok


def test_verdicts_lists_each_branch_with_its_sha(world):
    repo, _ = world
    v = bd.verdicts(repo)
    assert v["remote:done"]["ok"] and v["local:done"]["ok"] and not v["remote:wip"]["ok"]
    assert v["remote:done"]["sha"] == git(repo, "rev-parse", "origin/done")
