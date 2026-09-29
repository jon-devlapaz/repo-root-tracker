"""Per-repo git status signals for the repo-root-tracker dashboard."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

STALE_DAYS = 30


@dataclass
class LastCommit:
    hash: str = ""
    subject: str = ""
    date: str = ""
    relative: str = ""


@dataclass
class DirtyState:
    modified: int = 0
    staged: int = 0
    untracked: int = 0
    is_clean: bool = True


@dataclass
class SyncState:
    ahead: int = 0
    behind: int = 0
    has_upstream: bool = False


@dataclass
class StaleBranch:
    name: str = ""
    last_commit_date: str = ""


@dataclass
class RepoStatus:
    path: str = ""
    branch: str = ""
    last_commit: LastCommit = field(default_factory=LastCommit)
    dirty: DirtyState = field(default_factory=DirtyState)
    sync: SyncState = field(default_factory=SyncState)
    stale_branches: list[StaleBranch] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class GitNotAvailableError(RuntimeError):
    """Raised when the git binary cannot be found."""


def _run(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError as e:
        raise GitNotAvailableError("git binary not found on PATH") from e
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    # Strip only newlines: porcelain XY codes use a significant leading space
    return result.stdout.strip("\n")


def _relative(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m} minute{'s' if m != 1 else ''} ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h} hour{'s' if h != 1 else ''} ago"
        d = seconds // 86400
        if d < 30:
            return f"{d} day{'s' if d != 1 else ''} ago"
        months = d // 30
        if months < 12:
            return f"{months} month{'s' if months != 1 else ''} ago"
        years = months // 12
        return f"{years} year{'s' if years != 1 else ''} ago"
    except (ValueError, TypeError):
        return iso_date


def get_repo_status(path: str | Path) -> RepoStatus:
    """Collect dashboard status signals for the repo at *path*.

    Uses local git subprocess calls only — no network, no auth.
    """
    repo = Path(path).expanduser().resolve()
    status = RepoStatus(path=str(repo))

    # Branch
    try:
        status.branch = _run(repo, "rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError:
        status.branch = "(no commits)"

    # Last commit
    try:
        out = _run(repo, "log", "-1", "--format=%H|%s|%cI")
        h, subject, date = out.split("|", 2)
        status.last_commit = LastCommit(
            hash=h[:7], subject=subject, date=date, relative=_relative(date)
        )
    except (RuntimeError, ValueError):
        pass

    # Dirty state — porcelain v1, XY status codes
    try:
        out = _run(repo, "status", "--porcelain=v1")
        for line in out.splitlines():
            if not line:
                continue
            x, y = line[0], line[1]
            if x == "?" and y == "?":
                status.dirty.untracked += 1
            else:
                if x not in (" ", "?"):
                    status.dirty.staged += 1
                if y not in (" ", "?"):
                    status.dirty.modified += 1
        status.dirty.is_clean = (
            status.dirty.modified == 0
            and status.dirty.staged == 0
            and status.dirty.untracked == 0
        )
    except RuntimeError:
        pass

    # Sync — ahead/behind vs upstream
    try:
        out = _run(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}")
        ahead, behind = out.split()
        status.sync = SyncState(ahead=int(ahead), behind=int(behind), has_upstream=True)
    except (RuntimeError, ValueError):
        status.sync = SyncState(has_upstream=False)

    # Stale branches — local branches untouched > STALE_DAYS
    try:
        out = _run(
            repo,
            "for-each-ref",
            "--format=%(refname:short)|%(committerdate:iso-strict)",
            "refs/heads/",
        )
        now = datetime.now(timezone.utc)
        for line in out.splitlines():
            if "|" not in line:
                continue
            name, date_str = line.split("|", 1)
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if (now - dt).days > STALE_DAYS:
                    status.stale_branches.append(
                        StaleBranch(name=name, last_commit_date=date_str)
                    )
            except ValueError:
                continue
    except RuntimeError:
        pass

    return status
