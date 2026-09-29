"""Per-repo detail view: commits with graph lanes, diffs, branches."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import NotARepositoryError
from .status import _relative

MAX_COMMITS = 30
MAX_DIFF_LINES = 2000


@dataclass
class Commit:
    hash: str = ""
    short: str = ""
    subject: str = ""
    author: str = ""
    date: str = ""
    relative: str = ""
    parents: list[str] = field(default_factory=list)
    lane: int = 0
    is_merge: bool = False
    branches: list[str] = field(default_factory=list)


@dataclass
class BranchInfo:
    name: str = ""
    kind: str = "local"  # "local" or "remote"
    current: bool = False
    last_commit: str = ""
    relative: str = ""
    ahead: int = 0
    behind: int = 0
    has_upstream: bool = False
    stale: bool = False
    tracked_by: list[str] = field(default_factory=list)  # remotes: locals tracking this


@dataclass
class ChangedFile:
    path: str = ""
    staged: bool = False
    untracked: bool = False


@dataclass
class RepoDetail:
    path: str = ""
    branch: str = ""
    commits: list[Commit] = field(default_factory=list)
    branches: list[BranchInfo] = field(default_factory=list)
    changed_files: list[ChangedFile] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _run(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=15
        )
    except FileNotFoundError as e:
        # Missing cwd (deleted repo) or missing git binary — loud, not silent
        raise RuntimeError(f"cannot run git in {repo}: {e}") from e
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip("\n")


def _require_dir(path: str | Path) -> Path:
    repo = Path(path).expanduser().resolve()
    if not repo.is_dir():
        raise NotARepositoryError(f"path does not exist: {repo}")
    return repo


def _assign_lanes(commits: list[Commit]) -> None:
    """Simple graph lane assignment. Cosmetic only — list order is authoritative."""
    lanes: list[str | None] = []  # lane index -> commit hash currently occupying
    by_hash = {c.hash: c for c in commits}
    for c in commits:
        # Find a lane: reuse one whose tip is this commit, else take a free slot
        lane = None
        for i, tip in enumerate(lanes):
            if tip == c.hash:
                lane = i
                break
        if lane is None:
            try:
                lane = lanes.index(None)
            except ValueError:
                lane = len(lanes)
                lanes.append(None)
        c.lane = lane
        # Advance: first parent continues in this lane, others open new lanes
        if c.parents:
            lanes[lane] = c.parents[0]
            for p in c.parents[1:]:
                if p not in lanes:
                    try:
                        free = lanes.index(None)
                        lanes[free] = p
                    except ValueError:
                        lanes.append(p)
        else:
            lanes[lane] = None
        # Free lanes whose tips are no longer reachable (not in remaining set)
        remaining = {x.hash for x in commits[commits.index(c) + 1:]}
        for i, tip in enumerate(lanes):
            if tip is not None and tip not in remaining and tip not in by_hash:
                lanes[i] = None


def get_repo_detail(path: str | Path) -> RepoDetail:
    repo = _require_dir(path)
    detail = RepoDetail(path=str(repo))

    try:
        detail.branch = _run(repo, "rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError:
        detail.branch = "(no commits)"

    # Branch -> commit mapping for labels
    branch_tips: dict[str, list[str]] = {}
    try:
        out = _run(repo, "for-each-ref", "--format=%(objectname)|%(refname:short)",
                   "refs/heads/")
        for line in out.splitlines():
            if "|" in line:
                h, name = line.split("|", 1)
                branch_tips.setdefault(h, []).append(name)
    except RuntimeError:
        pass

    # Recent commits
    try:
        out = _run(
            repo, "log", f"-{MAX_COMMITS}",
            "--format=%H|%h|%s|%an|%cI|%P",
        )
        for line in out.splitlines():
            if not line:
                continue
            parts = line.split("|", 5)
            if len(parts) != 6:
                continue
            h, short, subject, author, date, parents_str = parts
            parents = parents_str.split() if parents_str else []
            detail.commits.append(Commit(
                hash=h, short=short, subject=subject, author=author,
                date=date, relative=_relative(date),
                parents=parents, is_merge=len(parents) > 1,
                branches=branch_tips.get(h, []),
            ))
        _assign_lanes(detail.commits)
    except RuntimeError:
        pass

    # Branches with ahead/behind + staleness
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    try:
        current = detail.branch
        out = _run(
            repo, "for-each-ref",
            "--format=%(refname:short)|%(committerdate:iso-strict)|%(upstream:short)",
            "refs/heads/",
        )
        for line in out.splitlines():
            if "|" not in line:
                continue
            name, date_str, upstream = (line.split("|", 2) + [""])[:3]
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                stale = (now - dt).days > 30
                rel = _relative(date_str)
            except ValueError:
                stale, rel = False, date_str
            try:
                tip = _run(repo, "rev-parse", name)
            except RuntimeError:
                tip = ""
            ahead = behind = 0
            has_up = bool(upstream)
            if has_up:
                try:
                    ab = _run(repo, "rev-list", "--left-right", "--count",
                              f"{name}...{upstream}")
                    a, b = ab.split()
                    ahead, behind = int(a), int(b)
                except (RuntimeError, ValueError):
                    pass
            detail.branches.append(BranchInfo(
                name=name, kind="local", current=(name == current),
                last_commit=tip[:7], relative=rel,
                ahead=ahead, behind=behind, has_upstream=has_up,
                stale=stale,
            ))
    except RuntimeError:
        pass

    # Remote-tracking branches (refs/remotes/), skipping origin/HEAD pointers
    try:
        out = _run(
            repo, "for-each-ref",
            "--format=%(refname:short)|%(committerdate:iso-strict)|%(objectname:short)|%(symref)",
            "refs/remotes/",
        )
        # Map upstream short name -> local branches tracking it
        upstream_to_locals: dict[str, list[str]] = {}
        for b in detail.branches:
            if b.kind == "local" and b.has_upstream:
                try:
                    up = _run(repo, "for-each-ref",
                              "--format=%(upstream:short)", f"refs/heads/{b.name}")
                    if up:
                        upstream_to_locals.setdefault(up, []).append(b.name)
                except RuntimeError:
                    pass
        for line in out.splitlines():
            if "|" not in line:
                continue
            name, date_str, tip, symref = (line.split("|", 3) + ["", "", "", ""])[:4]
            if symref or name.endswith("/HEAD"):
                continue  # HEAD pointer, not a real branch
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                stale = (now - dt).days > 30
                rel = _relative(date_str)
            except ValueError:
                stale, rel = False, date_str
            detail.branches.append(BranchInfo(
                name=name, kind="remote",
                last_commit=tip, relative=rel, stale=stale,
                tracked_by=upstream_to_locals.get(name, []),
            ))
    except RuntimeError:
        pass

    # Working-tree changed files
    try:
        out = _run(repo, "status", "--porcelain=v1")
        for line in out.splitlines():
            if not line:
                continue
            x, y = line[0], line[1]
            fpath = line[3:]
            # Handle renames: "R  old -> new"
            if " -> " in fpath:
                fpath = fpath.split(" -> ", 1)[1]
            # Strip quotes git adds for special chars
            if fpath.startswith('"') and fpath.endswith('"'):
                fpath = fpath[1:-1]
            detail.changed_files.append(ChangedFile(
                path=fpath,
                staged=(x not in (" ", "?", "!")),
                untracked=(x == "?" and y == "?"),
            ))
    except RuntimeError:
        pass

    return detail


def get_commit_diff(path: str | Path, commit_hash: str) -> str:
    repo = _require_dir(path)
    # Validate hash shape to prevent arg injection
    if (not commit_hash.replace("_", "").replace("-", "").isalnum()
            or len(commit_hash) > 64 or not commit_hash):
        raise ValueError("invalid commit hash")
    out = _run(repo, "show", "--format=", "--no-ext-diff", "--no-color",
               commit_hash, "--")
    lines = out.splitlines()
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [
            f"... truncated ({len(lines) - MAX_DIFF_LINES} more lines)"
        ]
    return "\n".join(lines)


def get_working_diff(path: str | Path, file: str) -> str:
    repo = _require_dir(path)
    if not file or file.startswith("/") or ".." in file.split("/"):
        raise ValueError("invalid file path")
    # Staged + unstaged diff for the file
    try:
        staged = _run(repo, "diff", "--cached", "--no-color", "--", file)
    except RuntimeError:
        staged = ""
    try:
        unstaged = _run(repo, "diff", "--no-color", "--", file)
    except RuntimeError:
        unstaged = ""
    combined = ""
    if staged:
        combined += "--- staged ---\n" + staged
    if unstaged:
        if combined:
            combined += "\n--- unstaged ---\n"
        combined += unstaged
    if not combined:
        return "(untracked or no changes)"
    lines = combined.splitlines()
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [
            f"... truncated ({len(lines) - MAX_DIFF_LINES} more lines)"
        ]
    return "\n".join(lines)
