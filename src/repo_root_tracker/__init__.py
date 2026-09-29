"""repo-root-tracker: find the git repository root by walking up the filesystem."""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"
__all__ = ["find_root", "NotARepositoryError"]


class NotARepositoryError(RuntimeError):
    """Raised when no .git entry is found walking up to the filesystem root."""


def find_root(start: Path) -> Path:
    """Return the git repository root containing *start*.

    Walks up from *start* (resolved to an absolute path) looking for a ``.git``
    entry — either a directory (normal clone) or a file (git worktree pointer).
    Returns the first directory that contains such an entry.

    Raises:
        NotARepositoryError: if the filesystem root is reached without finding ``.git``.
    """
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            raise NotARepositoryError(
                f"No git repository found walking up from {start!r}"
            )
        current = parent
