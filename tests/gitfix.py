"""Real temporary git repositories for tests: no mocks of git, no network, no global git config needed."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.t",
         "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                            env={**os.environ, **IDENT})
    return result.stdout.strip()


def commit(repo: Path, name: str = "file.txt", text: str = "x\n", message: str = "commit") -> None:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)


def init(path: Path, branch: str = "main") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", branch, str(path)], check=True, capture_output=True, env={**os.environ, **IDENT})
    commit(path, message="first")
    return path


def with_origin(tmp: Path, name: str, branch: str = "main") -> tuple[Path, Path]:
    """A repository with a real bare origin, main pushed and tracking: the git-golden starting point."""
    bare = tmp / f"{name}-origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", branch, str(bare)], check=True, capture_output=True, env={**os.environ, **IDENT})
    repo = init(tmp / name, branch)
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", branch)
    return repo, bare
