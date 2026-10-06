"""Find git checkouts by scanning folders. Nothing is registered, nothing is written."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .status import list_worktrees

DEFAULT_ROOT = "~/dev/active"
MAX_DEPTH = 4
MAX_ENTRIES = 50_000
MAX_SECONDS = 5.0
SKIP_DIRS = frozenset({"node_modules", ".venv", "venv", "dist", "build", "target", ".next", "__pycache__", "site-packages"})


@dataclass
class Scan:
    roots: list[str] = field(default_factory=list)
    missing_roots: list[str] = field(default_factory=list)
    checkouts: list[dict] = field(default_factory=list)
    truncated: bool = False
    truncated_reason: str = ""
    deeper_not_searched: int = 0
    max_depth: int = MAX_DEPTH
    elapsed_seconds: float = 0.0
    scanned_at: str = ""

    def paths(self) -> set[str]:
        return {c["path"] for c in self.checkouts}

    def to_dict(self) -> dict:
        return asdict(self)


def default_roots(environ: dict[str, str] | None = None) -> list[str]:
    """Roots from RRT_ROOTS (path-separator list), else the default folder."""
    environ = os.environ if environ is None else environ
    raw = environ.get("RRT_ROOTS", "")
    roots = [part for part in raw.split(os.pathsep) if part.strip()]
    return roots or [DEFAULT_ROOT]


def find_checkout_dirs(
    roots: list[str],
    *,
    max_depth: int = MAX_DEPTH,
    max_entries: int = MAX_ENTRIES,
    max_seconds: float = MAX_SECONDS,
    clock=time.monotonic,
) -> tuple[list[str], list[str], bool, str, int]:
    """Walk the roots for directories holding a `.git` entry.

    Returns (checkout paths, missing roots, truncated, reason, folders beyond the depth limit). `truncated` is
    reserved for the entry and time caps; the depth limit is a deterministic, counted note. Never follows symlinks, never descends into a
    checkout, skips hidden and build directories, and stops at the caps instead of silently returning less.
    """
    found: dict[str, str] = {}
    missing: list[str] = []
    started, examined = clock(), 0
    truncated, reason, deeper = False, "", 0
    for raw in roots:
        root = Path(raw).expanduser()
        if not root.is_dir():
            missing.append(str(root))
            continue
        stack = [(os.path.abspath(root), 0)]
        while stack:
            directory, depth = stack.pop()
            if clock() - started > max_seconds:
                truncated, reason = True, f"stopped after {max_seconds:g} seconds"
                break
            try:
                with os.scandir(directory) as entries:
                    listing = sorted(entries, key=lambda e: e.name)
            except OSError:
                continue
            examined += len(listing)
            if examined > max_entries:
                truncated, reason = True, f"stopped after {max_entries} entries"
                break
            if any(e.name == ".git" for e in listing):
                found.setdefault(os.path.realpath(directory), directory)
                continue
            if depth >= max_depth:
                deeper += sum(_is_walkable(e) for e in listing)
                continue
            for entry in reversed(listing):
                if _is_walkable(entry):
                    stack.append((entry.path, depth + 1))
        if truncated and reason.startswith("stopped"):
            break
    return sorted(found.values()), missing, truncated, reason, deeper


def _is_walkable(entry: os.DirEntry) -> bool:
    try:
        return (entry.is_dir(follow_symlinks=False) and not entry.is_symlink()
                and not entry.name.startswith(".") and entry.name not in SKIP_DIRS)
    except OSError:
        return False


def scan(roots: list[str] | None = None, **limits) -> Scan:
    """Find every checkout under the roots, plus linked worktrees that live elsewhere."""
    started = time.monotonic()
    roots = roots or default_roots()
    directories, missing, truncated, reason, deeper = find_checkout_dirs(roots, **limits)
    checkouts: dict[str, dict] = {}
    for directory in directories:
        try:
            worktrees = list_worktrees(Path(directory))
        except Exception:
            worktrees = [directory]
        project = worktrees[0] if worktrees else directory
        for worktree in worktrees or [directory]:
            if not os.path.exists(os.path.join(worktree, ".git")):
                continue  # a bare repository or a pruned worktree has no working tree to report
            real = os.path.realpath(worktree)
            checkouts.setdefault(real, {
                "path": real, "project_path": os.path.realpath(project),
                "is_worktree": os.path.realpath(worktree) != os.path.realpath(project),
            })
    return Scan(
        roots=[str(Path(r).expanduser()) for r in roots], missing_roots=missing,
        checkouts=sorted(checkouts.values(), key=lambda c: (c["project_path"], c["is_worktree"], c["path"])),
        truncated=truncated, truncated_reason=reason, deeper_not_searched=deeper,
        max_depth=limits.get("max_depth", MAX_DEPTH),
        elapsed_seconds=round(time.monotonic() - started, 3),
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )
