"""Shared fixtures. Building a repository with a real bare remote costs dozens of git processes, so the common starting
point is built once per run and copied for each test (a plain directory copy; nothing is shared between tests)."""

import shutil

import pytest
from gitfix import commit, git, with_origin


def _build(tmp):
    repo, bare = with_origin(tmp, "r")
    for name, merged in (("done", True), ("wip", False)):  # done: merged into main everywhere; wip: one commit main does not have
        git(repo, "switch", "-q", "-c", name)
        commit(repo, f"{name}.txt", message=name)
        git(repo, "push", "-q", "origin", name)
        git(repo, "switch", "-q", "main")
        if merged:
            git(repo, "merge", "-q", "--ff-only", name)
            git(repo, "push", "-q", "origin", "main")
    return tmp


@pytest.fixture(scope="session")
def branch_template(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("branch-template"))


@pytest.fixture()
def branch_world(tmp_path, branch_template):
    """(repo, bare) with branches `done` and `wip`, local and remote, in a private copy."""
    shutil.copytree(branch_template, tmp_path / "w", symlinks=True)
    repo, bare = tmp_path / "w" / "r", tmp_path / "w" / "r-origin.git"
    git(repo, "remote", "set-url", "origin", str(bare))
    return repo, bare
