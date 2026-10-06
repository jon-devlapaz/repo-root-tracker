"""Per-checkout git status signals for the repo-root-tracker table."""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import NotARepositoryError
from .changes import parse_changes
from .github import _github_remote
from .golden import Verdict, evaluate, worktree_verdict


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
    kinds: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.kinds.values())


@dataclass
class SyncState:
    ahead: int = 0
    behind: int = 0
    has_upstream: bool = False


@dataclass
class RepoStatus:
    path: str = ""
    branch: str = ""
    last_commit: LastCommit = field(default_factory=LastCommit)
    dirty: DirtyState = field(default_factory=DirtyState)
    sync: SyncState = field(default_factory=SyncState)
    checked_at: str = ""
    last_fetch_at: str = ""
    project_id: str = ""
    project_path: str = ""
    is_worktree: bool = False
    github_repo: str = ""
    branches: list[str] = field(default_factory=list)
    remote_branches: list[str] = field(default_factory=list)
    has_origin: bool = False
    other_worktrees: list[str] = field(default_factory=list)
    # One entry per branch other than main: whether git can show it is fully merged, and its age.
    branch_details: list[dict] = field(default_factory=list)
    branch_details_total: int = 0
    # Local main against origin/main (not against whatever main tracks), and the commit CI results must match.
    main_sha: str = ""
    main_sync: dict = field(default_factory=lambda: {"exists": False, "ahead": 0, "behind": 0, "tracks_origin_main": False})

    def golden(self, ci: str = "unchecked") -> Verdict:
        if self.is_worktree:
            return worktree_verdict()
        return evaluate(
            branch=self.branch, changed=self.dirty.total, local_branches=self.branches,
            remote_branches=self.remote_branches, has_origin=self.has_origin,
            other_worktrees=self.other_worktrees, ahead=self.main_sync["ahead"], behind=self.main_sync["behind"],
            has_upstream=self.main_sync["tracks_origin_main"], main_exists=self.main_sync["exists"], ci=ci,
        )

    def to_dict(self, ci: str = "unchecked") -> dict:
        data = asdict(self)
        data["dirty"]["total"] = self.dirty.total
        data["golden"] = self.golden(ci).to_dict()
        return data


class GitNotAvailableError(RuntimeError):
    """Raised when the git binary cannot be found."""


def _run(repo: Path, *args: str, timeout: float = 10) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=timeout,
            # Read-only: never take the optional index lock, never wait on a credential prompt.
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"},
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
        seconds = int((datetime.now(timezone.utc) - dt).total_seconds())
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


MAX_BRANCH_DETAILS = 40
HEADS, REMOTES = "refs/heads/", "refs/remotes/"


def _refs(repo: Path, prefix: str) -> list[tuple[str, str, str]]:
    """(full ref name, commit, date) for each ref under prefix. Full names, so a local branch called `origin/x` can
    never be mistaken for the remote-tracking `origin/x`."""
    rows = _run(repo, "for-each-ref", "--format=%(refname)%09%(objectname)%09%(committerdate:iso-strict)", prefix)
    return [tuple(line.split("\t")) for line in rows.splitlines() if line]  # type: ignore[misc]


def _ref_exists(repo: Path, ref: str) -> bool:
    try:
        _run(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
        return True
    except RuntimeError:
        return False


def _judge(repo: Path, base: str, ref: str) -> tuple[bool | None, int | None, bool]:
    """(merged, commits not on base, is an ancestor of base). `merged` is True only when git can show it, None when it
    cannot tell, and False when the branch holds commits that are not on base.

    `git cherry` sees through rebase merges but never looks at merge commits, which can carry changes of their own. So
    a branch that is not an ancestor counts as merged only when every commit has an equivalent patch on base AND it
    has no merge commits that base lacks. A change that main applied and later reverted still counts: it was merged,
    and its history stays on main, so deleting the branch loses nothing that history does not hold."""
    try:
        unmerged = sum(1 for line in _run(repo, "cherry", base, ref).splitlines() if line.startswith("+"))
    except RuntimeError:
        return None, None, False
    if unmerged:
        return False, unmerged, False
    try:
        _run(repo, "merge-base", "--is-ancestor", ref, base)
        return True, 0, True
    except RuntimeError:
        pass
    try:
        merges = int(_run(repo, "rev-list", "--merges", "--count", f"{base}..{ref}"))
    except (RuntimeError, ValueError):
        return None, 0, False
    return (True if merges == 0 else None), 0, False


def _branch_details(repo: Path, local: list[tuple[str, str, str]], remote: list[tuple[str, str, str]]) -> tuple[list[dict], int]:
    """For every branch except main. Squash merges leave no trace git can follow, so such a branch reads as unmerged.
    Returns (details, how many branches exist) because the list is capped."""
    details: list[dict] = []
    total = 0
    for scope, refs, prefix, base in (("local", local, HEADS, HEADS + "main"), ("remote", remote, REMOTES, REMOTES + "origin/main")):
        have_base = _ref_exists(repo, base)
        extra = [(ref, sha, date) for ref, sha, date in refs if ref != base and not ref.endswith("/HEAD")]
        total += len(extra)
        for ref, sha, date in extra[:MAX_BRANCH_DETAILS]:
            merged, unmerged, ancestor = _judge(repo, base, ref) if have_base else (None, None, False)
            details.append({"name": ref[len(prefix):] if scope == "local" else ref[len(REMOTES):], "scope": scope, "ref": ref,
                            "sha": sha, "merged": merged, "unmerged": unmerged, "ancestor": ancestor,
                            "last_commit_date": date, "relative": _relative(date)})
    return details, total


def _main_sync(repo: Path) -> dict:
    """Local main against origin/main, whatever is checked out and whatever main tracks."""
    local, origin = HEADS + "main", REMOTES + "origin/main"
    info = {"exists": _ref_exists(repo, local), "ahead": 0, "behind": 0, "tracks_origin_main": False}
    if info["exists"]:
        try:
            info["tracks_origin_main"] = _run(repo, "for-each-ref", "--format=%(upstream)", local) == origin
            if _ref_exists(repo, origin):
                ahead, behind = _run(repo, "rev-list", "--left-right", "--count", f"{local}...{origin}").split()
                info.update(ahead=int(ahead), behind=int(behind))
        except (RuntimeError, ValueError):
            pass
    return info


def list_worktrees(repo: Path) -> list[str]:
    """Every checkout of the repository, main checkout first, as reported by git."""
    items = _run(repo, "worktree", "list", "--porcelain", "-z").split("\0")
    return [item[9:] for item in items if item.startswith("worktree ")]


def get_repo_status(path: str | Path) -> RepoStatus:
    """Collect status signals for the checkout at *path* from local git only: no network, no auth.

    Raises NotARepositoryError if the path does not exist, never fake-clean defaults.
    """
    repo = Path(path).expanduser().resolve()
    if not repo.is_dir():
        raise NotARepositoryError(f"path does not exist: {repo}")
    status = RepoStatus(path=str(repo))
    status.project_id = str(Path(_run(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve())
    worktrees = list_worktrees(repo)
    status.project_path = worktrees[0] if worktrees else str(repo)
    status.is_worktree = str(repo) != status.project_path
    status.other_worktrees = [w for w in worktrees if Path(w).resolve() != repo]
    status.github_repo = _github_remote(repo) or ""
    fetch_head = Path(_run(repo, "rev-parse", "--path-format=absolute", "--git-path", "FETCH_HEAD"))
    try:
        status.last_fetch_at = datetime.fromtimestamp(fetch_head.stat().st_mtime, timezone.utc).isoformat()
    except FileNotFoundError:
        pass

    try:
        status.branch = _run(repo, "rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError:
        status.branch = "(no commits)"

    try:
        h, subject, date = _run(repo, "log", "-1", "--format=%H|%s|%cI").split("|", 2)
        status.last_commit = LastCommit(hash=h[:7], subject=subject, date=date, relative=_relative(date))
    except (RuntimeError, ValueError):
        pass

    changes = parse_changes(_run(repo, "status", "--porcelain=v1", "-z"))
    for change in changes:
        status.dirty.kinds[change.kind] = status.dirty.kinds.get(change.kind, 0) + 1
        status.dirty.untracked += int(change.untracked)
        status.dirty.staged += int(change.staged)
        status.dirty.modified += int(bool(change.worktree_kind))
    status.dirty.is_clean = not changes

    try:
        ahead, behind = _run(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}").split()
        status.sync = SyncState(ahead=int(ahead), behind=int(behind), has_upstream=True)
    except (RuntimeError, ValueError):
        status.sync = SyncState(has_upstream=False)

    local_refs: list[tuple[str, str, str]] = []
    remote_refs: list[tuple[str, str, str]] = []
    try:
        local_refs = _refs(repo, HEADS)
        status.branches = [ref[len(HEADS):] for ref, _, _ in local_refs]
    except RuntimeError:
        pass
    try:
        _run(repo, "remote", "get-url", "origin")
        status.has_origin = True
        remote_refs = [r for r in _refs(repo, REMOTES + "origin/") if not r[0].endswith("/HEAD")]
        status.remote_branches = sorted(ref[len(REMOTES):] for ref, _, _ in remote_refs)
    except RuntimeError:
        status.has_origin = False
    status.main_sync = _main_sync(repo)
    try:
        status.main_sha = _run(repo, "rev-parse", "--verify", "--quiet", HEADS + "main")
    except RuntimeError:
        pass
    if not status.is_worktree:
        status.branch_details, status.branch_details_total = _branch_details(repo, local_refs, remote_refs)
    status.checked_at = datetime.now(timezone.utc).isoformat()
    return status


def fetch_origin(path: str | Path) -> None:
    """Update remote-tracking refs only. Never touches the working tree, local branches or commits."""
    repo = Path(path).expanduser().resolve()
    if not repo.is_dir():
        raise NotARepositoryError(f"path does not exist: {repo}")
    _run(repo, "fetch", "--prune", "--quiet", "origin", timeout=60)
