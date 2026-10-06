"""Finding repositories by scanning: nested repos, linked worktrees, symlink loops, skipped folders and the caps."""

import os
from pathlib import Path

from gitfix import git, init

from repo_root_tracker.scan import DEFAULT_ROOT, MAX_DEPTH, default_roots, find_checkout_dirs, scan


def names(result, root: Path) -> list[str]:
    return sorted(str(Path(c["path"]).relative_to(root.resolve())) for c in result.checkouts)


def test_finds_repos_at_several_depths_and_does_not_descend_into_them(tmp_path):
    init(tmp_path / "a")
    init(tmp_path / "group" / "b")
    init(tmp_path / "group" / "deep" / "c")
    init(tmp_path / "a" / "vendored")  # inside a repo: never reported
    result = scan([str(tmp_path)])
    assert names(result, tmp_path) == ["a", "group/b", "group/deep/c"]
    assert not result.truncated and not result.missing_roots


def test_a_root_that_is_itself_a_repository_is_found(tmp_path):
    init(tmp_path)
    assert names(scan([str(tmp_path)]), tmp_path) == ["."]


def test_plain_folders_files_and_empty_trees_are_ignored(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.txt").write_text("x")
    (tmp_path / "empty").mkdir()
    assert scan([str(tmp_path)]).checkouts == []


def test_linked_worktrees_are_nested_under_their_project_even_when_they_live_outside_the_roots(tmp_path):
    root, elsewhere = tmp_path / "scan", tmp_path / "elsewhere"
    main = init(root / "proj")
    git(main, "worktree", "add", "-q", "-b", "side", str(elsewhere / "proj-side"))
    git(main, "worktree", "add", "-q", "-b", "inside", str(root / "proj-inside"))
    result = scan([str(root)])
    by_path = {c["path"]: c for c in result.checkouts}
    project = os.path.realpath(main)
    assert set(by_path) == {project, os.path.realpath(elsewhere / "proj-side"), os.path.realpath(root / "proj-inside")}
    assert not by_path[project]["is_worktree"]
    assert all(c["project_path"] == project for c in by_path.values())
    assert sum(c["is_worktree"] for c in by_path.values()) == 2


def test_a_worktree_found_first_still_reports_its_project(tmp_path):
    main = init(tmp_path / "outside" / "proj")
    git(main, "worktree", "add", "-q", "-b", "w", str(tmp_path / "roots" / "w"))
    result = scan([str(tmp_path / "roots")])
    assert {c["project_path"] for c in result.checkouts} == {os.path.realpath(main)}
    assert any(not c["is_worktree"] for c in result.checkouts)  # the project's main checkout is listed too


def test_symlinks_are_never_followed_so_a_loop_cannot_hang_or_duplicate(tmp_path):
    real = init(tmp_path / "real")
    os.symlink(tmp_path, tmp_path / "loop")  # points back at the root
    os.symlink(real, tmp_path / "alias")  # points at a repository
    assert names(scan([str(tmp_path)]), tmp_path) == ["real"]


def test_a_symlink_to_a_repository_outside_the_roots_is_not_followed_out(tmp_path):
    root = tmp_path / "root"
    init(root / "inside")
    outside = init(tmp_path / "elsewhere" / "sneaky")
    os.symlink(outside, root / "link")
    os.symlink(outside.parent, root / "parent-link")
    assert names(scan([str(root)]), root) == ["inside"]


def test_build_hidden_and_dependency_folders_are_skipped(tmp_path):
    for skipped in ("node_modules", ".venv", "dist", "build", "target", ".next", "__pycache__", ".hidden"):
        init(tmp_path / skipped / "repo")
    init(tmp_path / "kept")
    assert names(scan([str(tmp_path)]), tmp_path) == ["kept"]


def test_the_depth_limit_is_a_counted_note_not_an_alarm(tmp_path):
    init(tmp_path / "a" / "b" / "c" / "d" / "ok")  # depth 5 below the root: found only if depth allows
    (tmp_path / "x" / "y" / "z" / "w" / "more").mkdir(parents=True)
    default = scan([str(tmp_path)])
    assert default.max_depth == MAX_DEPTH == 4
    assert names(default, tmp_path) == []
    assert default.deeper_not_searched >= 1 and not default.truncated
    deeper = scan([str(tmp_path)], max_depth=5)
    assert names(deeper, tmp_path) == ["a/b/c/d/ok"]


def test_the_entry_cap_stops_the_scan_and_says_so(tmp_path):
    for i in range(30):
        (tmp_path / f"dir{i:02}").mkdir()
    init(tmp_path / "zzz")
    result = scan([str(tmp_path)], max_entries=10)
    assert result.truncated and "10 entries" in result.truncated_reason


def test_the_time_cap_stops_the_scan_and_says_so(tmp_path):
    for i in range(5):
        (tmp_path / f"d{i}").mkdir()
    ticks = iter(range(0, 1000, 3))
    _, _, truncated, reason, _ = find_checkout_dirs([str(tmp_path)], max_seconds=5, clock=lambda: next(ticks))
    assert truncated and "5 seconds" in reason


def test_missing_roots_are_reported_and_other_roots_still_scan(tmp_path):
    init(tmp_path / "here")
    result = scan([str(tmp_path / "nope"), str(tmp_path)])
    assert result.missing_roots == [str(tmp_path / "nope")]
    assert names(result, tmp_path) == ["here"]


def test_overlapping_roots_do_not_duplicate_repos(tmp_path):
    init(tmp_path / "g" / "r")
    result = scan([str(tmp_path), str(tmp_path / "g")])
    assert len(result.checkouts) == 1


def test_unreadable_folders_are_skipped_not_fatal(tmp_path):
    init(tmp_path / "ok")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        assert names(scan([str(tmp_path)]), tmp_path) == ["ok"]
    finally:
        locked.chmod(0o755)


def test_roots_come_from_the_environment_then_the_default():
    assert default_roots({}) == [DEFAULT_ROOT] == ["~/dev/active"]
    assert default_roots({"RRT_ROOTS": os.pathsep.join(["/a", "/b"])}) == ["/a", "/b"]
    assert default_roots({"RRT_ROOTS": "  "}) == [DEFAULT_ROOT]


def test_results_are_sorted_and_serializable(tmp_path):
    for n in ("b", "a", "c"):
        init(tmp_path / n)
    data = scan([str(tmp_path)]).to_dict()
    assert [Path(c["path"]).name for c in data["checkouts"]] == ["a", "b", "c"]
    assert set(data) >= {"roots", "missing_roots", "checkouts", "truncated", "truncated_reason", "deeper_not_searched", "scanned_at"}
