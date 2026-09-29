"""GitHub integration via the authenticated `gh` CLI.

Zero new dependencies: shells out to `gh`, which handles auth via keyring.
Results are cached in-process with a short TTL to bound API calls.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

CACHE_TTL_SECONDS = 60
PR_LIMIT = 20
ISSUE_LIMIT = 20

_cache: dict[str, tuple[float, "GithubInfo"]] = {}


@dataclass
class CheckSummary:
    state: str = "none"  # "pass" | "fail" | "pending" | "none"
    passing: int = 0
    total: int = 0


@dataclass
class PullRequest:
    number: int = 0
    title: str = ""
    branch: str = ""
    url: str = ""
    ci: CheckSummary = field(default_factory=CheckSummary)


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
    total = len(checks)
    if total == 0:
        return CheckSummary(state="none")
    states = [(c.get("status"), c.get("conclusion")) for c in checks]
    if any(s != "COMPLETED" for s, _ in states):
        passing = sum(1 for _, c in states if c in ("SUCCESS", "NEUTRAL", "SKIPPED"))
        return CheckSummary(state="pending", passing=passing, total=total)
    if all(c in ("SUCCESS", "NEUTRAL", "SKIPPED") for _, c in states):
        return CheckSummary(state="pass", passing=total, total=total)
    failing = sum(1 for _, c in states
                  if c not in ("SUCCESS", "NEUTRAL", "SKIPPED"))
    return CheckSummary(state="fail", passing=total - failing, total=total)


def get_github_info(path: str | Path) -> GithubInfo:
    repo_path = Path(path).expanduser().resolve()
    key = str(repo_path)
    now = time.monotonic()
    if key in _cache and now - _cache[key][0] < CACHE_TTL_SECONDS:
        return _cache[key][1]

    slug = _github_remote(repo_path)
    if slug is None:
        info = GithubInfo(has_github=False)
        _cache[key] = (now, info)
        return info

    prs_raw = _gh("pr", "list", "--state", "open",
                  "--json", "number,title,headRefName,url,statusCheckRollup",
                  "--limit", str(PR_LIMIT), cwd=repo_path)
    issues_raw = _gh("issue", "list", "--state", "open",
                     "--json", "number,title,url",
                     "--limit", str(ISSUE_LIMIT), cwd=repo_path)
    if prs_raw is None and issues_raw is None:
        info = GithubInfo(has_github=False, gh_unavailable=True)
        _cache[key] = (now, info)
        return info

    prs = [
        PullRequest(
            number=p.get("number", 0),
            title=p.get("title", ""),
            branch=p.get("headRefName", ""),
            url=p.get("url", ""),
            ci=_rollup(p.get("statusCheckRollup") or []),
        )
        for p in (prs_raw or [])
    ]
    issues = [
        Issue(number=i.get("number", 0), title=i.get("title", ""), url=i.get("url", ""))
        for i in (issues_raw or [])
    ]
    info = GithubInfo(
        has_github=True,
        repo=slug,
        repo_url=f"https://github.com/{slug}",
        prs=prs,
        issues=issues,
    )
    _cache[key] = (now, info)
    return info


def clear_cache() -> None:
    _cache.clear()
