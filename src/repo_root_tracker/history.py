"""Daily commit activity per repo: where attention went over the last N days."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import NotARepositoryError
from .status import _run

MAX_DAYS = 90


def get_activity(path: str | Path, days: int = 30) -> dict[str, int]:
    """Return {YYYY-MM-DD: commit count} for commits on any branch in the last *days* days.

    Local git only. Raises NotARepositoryError for a missing directory;
    a repo with no commits (or a git failure) yields an empty mapping.
    """
    repo = Path(path).expanduser().resolve()
    if not repo.is_dir():
        raise NotARepositoryError(f"path does not exist: {repo}")
    days = max(1, min(int(days), MAX_DAYS))
    try:
        out = _run(repo, "log", "--all", f"--since={days}.days.ago", "--format=%cs")
    except RuntimeError:
        return {}
    return dict(Counter(line for line in out.splitlines() if line))
