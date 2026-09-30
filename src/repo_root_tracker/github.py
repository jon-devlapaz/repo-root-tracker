"""GitHub integration via the authenticated `gh` CLI.

Zero new dependencies: shells out to `gh`, which handles auth via keyring.
Results are cached in-process with a short TTL to bound API calls.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
import threading
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from pathlib import Path

CACHE_TTL_SECONDS = 60
PR_LIMIT = 200
ISSUE_LIMIT = 20

_cache: dict[str, tuple[float, "GithubInfo"]] = {}
_locks: dict[str, threading.Lock] = {}
_cache_guard = threading.Lock()


@dataclass
class CheckSummary:
    state: str = "none"  # "pass" | "fail" | "pending" | "none"
    passing: int = 0
    total: int = 0
    failing: int = 0
    pending: int = 0


@dataclass
class PullRequest:
    number: int = 0
    title: str = ""
    branch: str = ""
    url: str = ""
    ci: CheckSummary = field(default_factory=CheckSummary)
    review_decision: str = ""
    mergeable: str = "UNKNOWN"
    draft: bool = False


@dataclass
class Issue:
    number: int = 0
    title: str = ""
    url: str = ""


@dataclass
class GithubInfo:
    has_github: bool = False
    repo: str = ""  # "owner/name"
    repo_url: str = ""
    prs: list[PullRequest] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    gh_unavailable: bool = False
    checked_at: str = ""
    errors: list[str] = field(default_factory=list)
    pr_limit_reached: bool = False
    pr_limit: int = PR_LIMIT
    issue_limit_reached: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _github_remote(path: Path) -> str | None:
    """Return 'owner/repo' if origin points at github.com, else None."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=path, capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    m = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


def _gh(*args: str, cwd: Path) -> list | None:
    """Run a `gh` JSON command, returning parsed list or None on any failure."""
    try:
        result = subprocess.run(
            ["gh", *args], cwd=cwd,
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def _rollup(checks: list) -> CheckSummary:
    passing = failing = pending = 0
    for check in checks:
        status = check.get("status")
        conclusion = check.get("conclusion") if status else check.get("state")
        if status and status != "COMPLETED":
            pending += 1
        elif conclusion in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
            passing += 1
        elif conclusion in {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}:
            failing += 1
        else:
            pending += 1
    state = "fail" if failing else "pending" if pending else "pass" if checks else "none"
    return CheckSummary(state=state, passing=passing, total=len(checks), failing=failing, pending=pending)


def get_github_info(path: str | Path, *, refresh: bool = False) -> GithubInfo:
    repo_path = Path(path).expanduser().resolve()
    slug = _github_remote(repo_path)
    key = slug or str(repo_path)
    with _cache_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        now = time.monotonic()
        if not refresh and key in _cache and now - _cache[key][0] < CACHE_TTL_SECONDS:
            return _cache[key][1]
        if slug is None:
            info = GithubInfo(checked_at=datetime.now(timezone.utc).isoformat())
        else:
            prs_raw = _gh("pr", "list", "--state", "open",
                          "--json", "number,title,headRefName,url,statusCheckRollup,reviewDecision,mergeable,isDraft",
                          "--limit", str(PR_LIMIT + 1), "--repo", f"github.com/{slug}", cwd=repo_path)
            issues_raw = _gh("issue", "list", "--state", "open",
                             "--json", "number,title,url",
                             "--limit", str(ISSUE_LIMIT), "--repo", f"github.com/{slug}", cwd=repo_path)
            errors = []
            if prs_raw is None:
                errors.append("Pull requests could not be checked. Check gh authentication, connectivity, and repository access.")
            if issues_raw is None:
                errors.append("Issues could not be checked. Check gh authentication, connectivity, and repository access.")
            info = GithubInfo(
                has_github=prs_raw is not None or issues_raw is not None,
                gh_unavailable=prs_raw is None and issues_raw is None,
                repo=slug, repo_url=f"https://github.com/{slug}",
                prs=[PullRequest(
                    number=p.get("number", 0), title=p.get("title", ""),
                    branch=p.get("headRefName", ""), url=p.get("url", ""),
                    ci=_rollup(p.get("statusCheckRollup") or []),
                    review_decision=p.get("reviewDecision") or "",
                    mergeable=p.get("mergeable") or "UNKNOWN", draft=bool(p.get("isDraft")),
                ) for p in (prs_raw or [])[:PR_LIMIT]],
                issues=[Issue(number=i.get("number", 0), title=i.get("title", ""), url=i.get("url", "")) for i in (issues_raw or [])],
                errors=errors, checked_at=datetime.now(timezone.utc).isoformat(),
                pr_limit_reached=prs_raw is not None and len(prs_raw) > PR_LIMIT,
                issue_limit_reached=issues_raw is not None and len(issues_raw) >= ISSUE_LIMIT,
            )
        _cache[key] = (time.monotonic(), info)
        return info


def clear_cache() -> None:
    _cache.clear()
