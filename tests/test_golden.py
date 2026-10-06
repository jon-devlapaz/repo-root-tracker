"""The git-golden definition from AGENTS.md as a truth table: each condition fails on its own, and only then."""

import pytest

from repo_root_tracker.golden import GOLDEN, NOT_GOLDEN, PENDING_CI, WORKTREE, evaluate, worktree_verdict

CLEAN = dict(branch="main", changed=0, local_branches=["main"], remote_branches=["origin/main"], has_origin=True,
             other_worktrees=[], ahead=0, behind=0, has_upstream=True, ci="passing")


def verdict(**changes):
    return evaluate(**{**CLEAN, **changes})


def test_every_condition_met_with_passing_ci_is_golden():
    v = verdict()
    assert (v.status, v.reasons, v.notes, v.headline) == (GOLDEN, [], [], "")


@pytest.mark.parametrize("change, reason", [
    (dict(branch="feat/x"), "on feat/x, not main"),
    (dict(branch="HEAD"), "on HEAD, not main"),
    (dict(changed=1), "1 uncommitted change"),
    (dict(changed=3), "3 uncommitted changes"),
    (dict(local_branches=["main", "x"]), "other local branch: x"),
    (dict(local_branches=["main", "x", "y"]), "other local branches: x, y"),
    (dict(local_branches=["main", "x", "y", "z"]), "3 other local branches"),
    (dict(remote_branches=["origin/main", "origin/x"]), "other remote branch: origin/x"),
    (dict(remote_branches=["origin/main", "origin/a", "origin/b", "origin/c"]), "3 other remote branches"),
    (dict(remote_branches=[]), "origin/main not found (not fetched yet?)"),
    (dict(has_origin=False, remote_branches=[]), "no origin remote"),
    (dict(other_worktrees=["/w"]), "1 extra worktree"),
    (dict(other_worktrees=["/a", "/b"]), "2 extra worktrees"),
    (dict(ahead=2), "not even with origin/main (ahead 2, behind 0)"),
    (dict(behind=1), "not even with origin/main (ahead 0, behind 1)"),
    (dict(has_upstream=False), "main has no upstream"),
    (dict(ci="failing"), "latest CI run on main failed"),
])
def test_each_condition_fails_alone(change, reason):
    v = verdict(**change)
    assert v.status == NOT_GOLDEN
    assert reason in v.reasons
    assert v.headline == v.reasons[0]


def test_the_first_failing_condition_is_the_headline_and_all_are_listed():
    v = verdict(branch="dev", changed=2, ahead=1, ci="failing")
    assert v.headline == "on dev, not main"
    assert v.reasons == ["on dev, not main", "2 uncommitted changes", "latest CI run on main failed"]


@pytest.mark.parametrize("ci, note", [
    ("pending", "still running"), ("unknown", "unavailable"), ("none", "no GitHub remote"), ("unchecked", "not checked"),
])
def test_ci_that_cannot_be_judged_is_pending_never_golden_and_never_a_failure(ci, note):
    v = verdict(ci=ci)
    assert (v.status, v.reasons) == (PENDING_CI, [])
    assert note in v.notes[0] and v.headline == v.notes[0]


def test_failing_ci_wins_over_everything_else_being_fine():
    assert verdict(ci="failing").status == NOT_GOLDEN


def test_open_pull_requests_and_issues_are_not_inputs_at_all():
    import inspect
    names = set(inspect.signature(evaluate).parameters)
    assert not {n for n in names if "pr" in n.split("_") or "issue" in n}


def test_a_detached_head_cannot_hide_behind_main_being_in_sync():
    v = verdict(branch="HEAD", ahead=5)
    assert v.status == NOT_GOLDEN and not any("origin/main (ahead" in r for r in v.reasons)


def test_linked_worktrees_are_judged_through_their_project():
    v = worktree_verdict()
    assert v.status == WORKTREE and v.reasons == []


def test_verdict_serializes_with_a_headline():
    data = verdict(changed=1).to_dict()
    assert data["status"] == NOT_GOLDEN and data["headline"] == "1 uncommitted change"


def test_every_reason_has_a_short_chip_in_the_same_order():
    v = verdict(branch="dev", changed=3, local_branches=["main", "x"], remote_branches=["origin/main", "origin/a", "origin/b"],
                other_worktrees=["/w"], ci="failing")
    assert [i["kind"] for i in v.items] == ["branch", "changes", "local-branches", "remote-branches", "worktrees", "ci"]
    assert [i["label"] for i in v.items] == ["on dev", "3 changes", "1 local branch", "2 remote branches", "1 worktree", "CI failing"]
    assert len(v.items) == len(v.reasons)


def test_sync_chip_uses_arrows_and_only_the_nonzero_side():
    assert verdict(ahead=2).items == [{"kind": "sync", "label": "\u21912"}]
    assert verdict(behind=3).items == [{"kind": "sync", "label": "\u21933"}]
    assert verdict(ahead=1, behind=4).items[0]["label"] == "\u21911 \u21934"
    assert verdict(has_upstream=False).items == [{"kind": "sync", "label": "no upstream"}]


def test_golden_and_pending_have_no_chips():
    assert verdict().items == [] and verdict(ci="unchecked").items == []
