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
from urllib.parse import quote, urlencode

CACHE_TTL_SECONDS = 60
PR_LIMIT = 200
ISSUE_LIMIT = 20
WORKFLOW_LIMIT = 100

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
class WorkflowRun:
    name: str = ""
    workflow_id: int = 0
    status: str = ""
    conclusion: str = ""
    url: str = ""
    updated_at: str = ""
    current_head: bool = False
    head_sha: str = ""
    workflow_state: str = "active"


@dataclass
class WorkflowHealth:
    state: str = "unknown"  # failing | pending | passing | unknown | stale
    head_sha: str = ""
    runs: list[WorkflowRun] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


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
    default_branch: str = ""
    workflows: WorkflowHealth | None = None
    merged_pr_count: int | None = None
    merged_pr_checked_at: str = ""
    merged_pr_error: str = ""

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


def _api_record(endpoint: str, fields: str, path: Path) -> dict | None:
    # Wrap the selected API object in a list to use the same gh timeout/error path.
    data = _gh("api", endpoint, "--hostname", "github.com", "--method", "GET",
               "--jq", f"[. | {{{fields}}}]", cwd=path)
    return data[0] if data and isinstance(data[0], dict) else None


def _workflow_health(slug: str, path: Path) -> tuple[str, WorkflowHealth, bool]:
    health = WorkflowHealth()
    base = f"repos/{slug}"
    metadata = _api_record(base, "default_branch", path)
    branch = (metadata or {}).get("default_branch")
    if not isinstance(branch, str) or not branch:
        health.errors.append("Default branch could not be checked. Check gh authentication, connectivity, and repository access.")
        return "", health, False
    head = _api_record(f"{base}/branches/{quote(branch, safe='')}", "sha: .commit.sha", path)
    health.head_sha = (head or {}).get("sha") or ""
    if not isinstance(health.head_sha, str) or not health.head_sha:
        health.head_sha = ""
        health.errors.append("Default-branch head could not be checked.")
        return branch, health, True

    catalog = _api_record(f"{base}/actions/workflows?per_page={WORKFLOW_LIMIT}", "total_count,workflows", path)
    query = urlencode({"branch": branch, "head_sha": health.head_sha, "per_page": WORKFLOW_LIMIT})
    current = _api_record(f"{base}/actions/runs?{query}", "total_count,workflow_runs", path)

    def records(response: dict | None, key: str, label: str) -> list[dict]:
        if response is None or not isinstance(response.get(key), list):
            health.errors.append(f"Default-branch {label} could not be checked.")
            return []
        rows = response[key]
        count = response.get("total_count")
        if not isinstance(count, int) or count > len(rows) or len(rows) > WORKFLOW_LIMIT:
            health.errors.append(f"Default-branch {label} coverage is incomplete (limit {WORKFLOW_LIMIT}).")
        if any(not isinstance(row, dict) for row in rows):
            health.errors.append(f"Default-branch {label} returned invalid data.")
        return [row for row in rows[:WORKFLOW_LIMIT] if isinstance(row, dict)]

    workflows = records(catalog, "workflows", "workflows")
    current_runs = records(current, "workflow_runs", "workflow runs")
    if any(not isinstance(workflow.get("id"), int) for workflow in workflows):
        health.errors.append("Default-branch workflow inventory returned invalid IDs.")

    def latest(runs: list[dict], *, current_head: bool) -> dict[int, dict]:
        def order(run: dict) -> tuple[int, int, int]:
            return tuple(run.get(key) if isinstance(run.get(key), int) else 0
                         for key in ("run_number", "id", "run_attempt"))

        selected = {}
        for run in runs:
            # PR checks are reported separately. Never borrow a result from another branch.
            if (run.get("head_branch") != branch or run.get("event") in {"pull_request", "pull_request_target"}
                    or (run.get("head_sha") == health.head_sha) != current_head):
                continue
            wid = run.get("workflow_id")
            if not isinstance(wid, int):
                health.errors.append("Default-branch workflow run has no workflow ID.")
                continue
            if wid not in selected or order(run) > order(selected[wid]):
                selected[wid] = run
        return selected

    selected = latest(current_runs, current_head=True)
    # Include confirmed runs even if the workflow inventory is inaccessible or truncated.
    inventory = {w["id"]: w for w in workflows if isinstance(w.get("id"), int)}
    for wid, run in selected.items():
        inventory.setdefault(wid, {"id": wid, "name": run.get("name", ""), "state": "active"})
    missing = set(inventory) - set(selected)
    older = {}
    if missing and current is not None:
        query = urlencode({"branch": branch, "per_page": WORKFLOW_LIMIT})
        history = _api_record(f"{base}/actions/runs?{query}", "total_count,workflow_runs", path)
        older = latest(records(history, "workflow_runs", "workflow history"), current_head=False)
    for wid, workflow in inventory.items():
        run = selected.get(wid) or older.get(wid) or {}
        health.runs.append(WorkflowRun(
            name=workflow.get("name") or run.get("name") or f"Workflow {wid}", workflow_id=wid,
            status=run.get("status") or "unknown", conclusion=run.get("conclusion") or "",
            url=run.get("html_url") or workflow.get("html_url") or "",
            updated_at=run.get("updated_at") or "", head_sha=run.get("head_sha") or "",
            current_head=wid in selected, workflow_state=workflow.get("state") or "unknown",
        ))

    def outcome(run: WorkflowRun) -> str:
        if not run.current_head:
            return "stale" if run.head_sha else "unknown"
        if run.status == "completed" and run.conclusion in {"failure", "timed_out", "action_required", "startup_failure", "error"}:
            return "failing"
        if run.workflow_state != "active":
            return "unknown"
        if run.status in {"queued", "in_progress", "waiting", "pending", "requested"}:
            return "pending"
        if run.status == "completed" and run.conclusion == "success":
            return "passing"
        # Cancelled, skipped, neutral, and unrecognised results are explicitly not passing.
        return "unknown"

    states = [outcome(run) for run in health.runs]
    health.state = ("failing" if "failing" in states else "pending" if "pending" in states else
                    "unknown" if health.errors or not states or "unknown" in states else
                    "stale" if "stale" in states else "passing")
    return branch, health, True


def _merged_pr_count(slug: str, path: Path) -> int | None:
    owner, name = slug.split("/", 1)
    query = "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){pullRequests(states:MERGED){totalCount}}}"
    data = _gh("api", "graphql", "--hostname", "github.com", "--method", "POST", "-f", f"query={query}",
               "-f", f"owner={owner}", "-f", f"name={name}",
               "--jq", "if .errors then [] else [.data.repository.pullRequests.totalCount] end", cwd=path)
    count = data[0] if data and len(data) == 1 else None
    return count if type(count) is int and count >= 0 else None


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
            merged_count = _merged_pr_count(slug, repo_path)
            previous = _cache.get(key, (0, GithubInfo()))[1]
            merged_checked = datetime.now(timezone.utc).isoformat() if merged_count is not None else previous.merged_pr_checked_at
            errors = []
            if prs_raw is None:
                errors.append("Pull requests could not be checked. Check gh authentication, connectivity, and repository access.")
            if issues_raw is None:
                errors.append("Issues could not be checked. Check gh authentication, connectivity, and repository access.")
            default_branch, workflows, workflow_access = _workflow_health(slug, repo_path)
            errors.extend(workflows.errors)
            info = GithubInfo(
                has_github=prs_raw is not None or issues_raw is not None or workflow_access or merged_count is not None,
                gh_unavailable=prs_raw is None and issues_raw is None and not workflow_access and merged_count is None,
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
                default_branch=default_branch, workflows=workflows,
                merged_pr_count=merged_count if merged_count is not None else previous.merged_pr_count,
                merged_pr_checked_at=merged_checked,
                merged_pr_error="" if merged_count is not None else "Merged PR total could not be checked.",
            )
        _cache[key] = (time.monotonic(), info)
        return info


@dataclass
class CiState:
    """Whether the latest CI run on the default branch's current commit succeeded."""

    state: str = "unknown"  # passing | failing | pending | unknown | none (no GitHub remote)
    default_branch: str = ""
    repo: str = ""
    errors: list[str] = field(default_factory=list)
    checked_at: str = ""
    head_sha: str = ""  # the commit on GitHub's default branch that these runs belong to

    def to_dict(self) -> dict:
        return asdict(self)


_ci_cache: dict[str, tuple[float, CiState]] = {}

ITEM_LIMIT = 30


@dataclass
class OpenItems:
    """Open pull requests and issues, for display only: they never change a repo's golden verdict."""

    repo: str = ""
    available: bool = False          # False: no GitHub remote, or gh could not answer at all
    prs: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    prs_known: bool = False          # a failed call is "unknown", never "zero"
    issues_known: bool = False
    prs_truncated: bool = False
    issues_truncated: bool = False
    checked_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_items_cache: dict[str, tuple[float, OpenItems]] = {}


def get_open_items(path: str | Path, *, refresh: bool = False) -> OpenItems:
    """Two `gh` calls: open pull requests and open issues, newest ITEM_LIMIT of each."""
    repo_path = Path(path).expanduser().resolve()
    slug = _github_remote(repo_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    if slug is None:
        return OpenItems(checked_at=now_iso)
    with _cache_guard:
        lock = _locks.setdefault(f"items:{slug}", threading.Lock())
    with lock:
        hit = _items_cache.get(slug)
        if hit and not refresh and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
        target = ("--limit", str(ITEM_LIMIT + 1), "--repo", f"github.com/{slug}")
        prs_raw = _gh("pr", "list", "--state", "open", "--json", "number,title,url,isDraft,headRefName", *target, cwd=repo_path)
        issues_raw = _gh("issue", "list", "--state", "open", "--json", "number,title,url", *target, cwd=repo_path)
        info = OpenItems(
            repo=slug, available=prs_raw is not None or issues_raw is not None, checked_at=now_iso,
            prs_known=prs_raw is not None, issues_known=issues_raw is not None,
            prs=[{"number": p.get("number", 0), "title": p.get("title", ""), "url": p.get("url", ""), "draft": bool(p.get("isDraft")),
                  "branch": p.get("headRefName", "")} for p in (prs_raw or [])[:ITEM_LIMIT]],
            issues=[{"number": i.get("number", 0), "title": i.get("title", ""), "url": i.get("url", "")} for i in (issues_raw or [])[:ITEM_LIMIT]],
            prs_truncated=prs_raw is not None and len(prs_raw) > ITEM_LIMIT,
            issues_truncated=issues_raw is not None and len(issues_raw) > ITEM_LIMIT,
        )
        _items_cache[slug] = (time.monotonic(), info)
        return info


def get_default_branch_ci(path: str | Path, *, refresh: bool = False) -> CiState:
    """One lightweight CI lookup (default branch and its workflow runs); no PR, issue or merge counts."""
    repo_path = Path(path).expanduser().resolve()
    slug = _github_remote(repo_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    if slug is None:
        return CiState(state="none", checked_at=now_iso)
    with _cache_guard:
        lock = _locks.setdefault(f"ci:{slug}", threading.Lock())
    with lock:
        hit = _ci_cache.get(slug)
        if hit and not refresh and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
        branch, health, _access = _workflow_health(slug, repo_path)
        state = health.state if health.state in ("passing", "failing", "pending") else "unknown"
        info = CiState(state=state, default_branch=branch, repo=slug, errors=list(health.errors), checked_at=now_iso,
                       head_sha=health.head_sha)
        _ci_cache[slug] = (time.monotonic(), info)
        return info


def clear_cache() -> None:
    _cache.clear()
    _ci_cache.clear()
    _items_cache.clear()
