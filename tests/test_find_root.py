"""Tests for repo_root_tracker covering AC-1 through AC-5."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from repo_root_tracker import NotARepositoryError, find_root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git_init(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.invalid"],
                   check=True, capture_output=True)


# ---------------------------------------------------------------------------
# AC-1: Library root discovery from subdirectory
# ---------------------------------------------------------------------------

def test_find_root_from_repo_root(tmp_path: Path) -> None:
    git_init(tmp_path)
    assert find_root(tmp_path) == tmp_path


def test_find_root_from_subdirectory(tmp_path: Path) -> None:
    git_init(tmp_path)
    subdir = tmp_path / "a" / "b" / "c"
    subdir.mkdir(parents=True)
    assert find_root(subdir) == tmp_path


def test_find_root_returns_path_type(tmp_path: Path) -> None:
    git_init(tmp_path)
    result = find_root(tmp_path)
    assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# AC-2: CLI root discovery from subdirectory (tested via subprocess)
# ---------------------------------------------------------------------------

def test_cli_from_repo_root(tmp_path: Path) -> None:
    git_init(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "repo_root_tracker"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == str(tmp_path.resolve())


def test_cli_from_subdirectory(tmp_path: Path) -> None:
    git_init(tmp_path)
    subdir = tmp_path / "sub"
    subdir.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "repo_root_tracker"],
        cwd=subdir,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == str(tmp_path.resolve())


# ---------------------------------------------------------------------------
# AC-3: Fail-fast when no git repo
# ---------------------------------------------------------------------------

def test_find_root_raises_outside_repo(tmp_path: Path) -> None:
    with pytest.raises(NotARepositoryError):
        find_root(tmp_path)


def test_cli_exits_nonzero_outside_repo(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "repo_root_tracker"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert result.stderr.strip() != ""


# ---------------------------------------------------------------------------
# AC-4: Worktree support (.git file)
# ---------------------------------------------------------------------------

def test_find_root_with_git_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir()
    git_init(repo)
    # Create a minimal commit so worktree add works
    subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "worktree", "add", str(worktree), "HEAD"],
                   check=True, capture_output=True)

    # The worktree root has a .git FILE, not a directory
    git_entry = worktree / ".git"
    assert git_entry.is_file(), ".git should be a file in a worktree"

    assert find_root(worktree) == worktree


def test_find_root_from_subdir_of_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir()
    git_init(repo)
    subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "worktree", "add", str(worktree), "HEAD"],
                   check=True, capture_output=True)
    subdir = worktree / "nested"
    subdir.mkdir()

    assert find_root(subdir) == worktree


# ---------------------------------------------------------------------------
# AC-5: Zero third-party dependencies (checked via checklist.json check)
# ---------------------------------------------------------------------------

def test_no_third_party_deps(tmp_path: Path) -> None:
    import tomllib
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    assert deps == [], f"Expected no dependencies, got: {deps}"
