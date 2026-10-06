"""Delete one branch, only when the tool can show it is safe, and only after writing it down.

The page never decides. `judge` is the single place that says whether a branch may go, and `delete` calls it again
at the moment of the request, so a stale page or a hand-made request cannot get past it. Everything fails closed:
a question that cannot be answered (gh missing, no network, git error) is a refusal, never a yes."""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .github import _gh
from .status import HEADS, REMOTES, RepoStatus, _run, get_repo_status

LOG = Path.home() / ".local/share/repo-root-tracker/deleted-branches.log"
ALWAYS_KEPT = ("main", "master")


@dataclass
class Verdict:
    ok: bool
    reason: str           # when ok: why it may go, in words. Otherwise: why it may not.
    kind: str = ""        # "merged" or "closed-pr" when ok
    pr: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def no(reason: str) -> Verdict:
    return Verdict(False, reason)


def pull_requests(slug: str, branch: str, cwd: Path) -> list[dict] | None:
    """Every pull request, open, merged or closed, whose head branch has this name. None when gh cannot answer."""
    rows = _gh("pr", "list", "--repo", f"github.com/{slug}", "--state", "all", "--head", branch, "--limit", "30",
               "--json", "number,state,headRefName,headRefOid", cwd=cwd)
    return None if rows is None else [r for r in rows if r.get("headRefName") == branch]


def valid_name(name: str) -> bool:
    """A plain branch name: no leading dash (it could pass for an option), and one git itself accepts."""
    if not name or name.startswith("-") or "\0" in name:
        return False
    return subprocess.run(["git", "check-ref-format", HEADS + name], capture_output=True).returncode == 0


def _held_by_worktrees(repo: Path) -> set[str]:
    """Branches checked out in any worktree of this repository, this checkout included."""
    held = set()
    for item in _run(repo, "worktree", "list", "--porcelain", "-z").split("\0"):
        if item.startswith("branch " + HEADS):
            held.add(item[len("branch " + HEADS):])
    return held


def _default_branch(repo: Path) -> str:
    try:
        return _run(repo, "symbolic-ref", "-q", REMOTES + "origin/HEAD").removeprefix(REMOTES + "origin/")
    except RuntimeError:
        return ""


def judge(status: RepoStatus, scope: str, branch: str, *, sha: str | None = None) -> Verdict:
    """May this branch be deleted right now? `sha`, when given, is the tip the caller looked at."""
    if scope not in ("local", "remote"):
        return no("scope must be local or remote")
    if not valid_name(branch):
        return no("not a usable branch name")
    if status.is_worktree:
        return no("this is a linked worktree; use the main checkout")
    repo = Path(status.path)
    shown = ("origin/" + branch) if scope == "remote" else branch
    detail = next((d for d in status.branch_details if d["scope"] == scope and d["name"] == shown), None)
    if detail is None:
        return no("no such branch, or it is beyond the first branches this tool lists")
    if sha is not None and sha != detail["sha"]:
        return no("the branch moved since you looked; reload and check again")

    default = _default_branch(repo)
    if branch in ALWAYS_KEPT or branch == default:
        return no("this is the default branch")
    if scope == "local":
        try:
            held = _held_by_worktrees(repo)
        except RuntimeError:
            return no("could not list worktrees")
        if branch == status.branch or branch in held:
            return no("this branch is checked out")

    prs: list[dict] = []
    if status.github_repo:
        found = pull_requests(status.github_repo, branch, repo)
        if found is None:
            return no("could not ask GitHub about its pull requests, so nothing is deleted")
        prs = found
    open_pr = next((p for p in prs if p["state"] == "OPEN"), None)
    if open_pr:
        return Verdict(False, f"it has an open pull request, #{open_pr['number']}", pr=open_pr["number"])

    if detail["merged"] is True:
        return Verdict(True, "merged into main", kind="merged")
    if scope == "remote" and prs and all(p["state"] == "CLOSED" for p in prs):
        latest = max(prs, key=lambda p: p["number"])
        if latest.get("headRefOid") != detail["sha"]:
            return Verdict(False, f"it has commits newer than closed pull request #{latest['number']}, which would be lost", pr=latest["number"])
        return Verdict(True, f"closed pull request #{latest['number']}, never merged; its commits stay at refs/pull/{latest['number']}/head",
                       kind="closed-pr", pr=latest["number"])
    if detail["merged"] is False:
        return no("it has commits that are not on main")
    return no("git cannot tell whether it is merged")


def verdicts(path: str | Path) -> dict[str, dict]:
    """A verdict for each listed branch, keyed `scope:name`, so the page knows where to put a Delete button."""
    status = get_repo_status(path)
    out = {}
    for d in status.branch_details:
        name = d["name"].removeprefix("origin/") if d["scope"] == "remote" else d["name"]
        out[f"{d['scope']}:{name}"] = {**judge(status, d["scope"], name).to_dict(), "sha": d["sha"]}
    return out


class Refused(Exception):
    """The branch may not be deleted (409), or the request was malformed (400)."""

    def __init__(self, reason: str, code: int = 409):
        super().__init__(reason)
        self.reason, self.code = reason, code


class Failed(Exception):
    """git was asked and said no (502). The branch is as it was."""


def _log(handle, outcome: str, repo: str, scope: str, branch: str, sha: str, note: str) -> None:
    stamp = datetime.now().isoformat(timespec="seconds")
    handle.write(f"{stamp}\t{outcome}\t{repo}\t{scope}\t{branch}\t{sha}\t{note}\n")
    handle.flush()
    os.fsync(handle.fileno())


def recovery_command(scope: str, branch: str, sha: str) -> str:
    return f"git push origin {sha}:refs/heads/{branch}" if scope == "remote" else f"git branch {branch} {sha}"


def delete(path: str | Path, scope: str, branch: str, sha: str, *, log_path: Path | None = None) -> dict:
    """Delete one branch. Raises Refused or Failed; returns what happened and how to undo it."""
    if not isinstance(sha, str) or len(sha) < 40:
        raise Refused("a full commit sha is required", 400)
    if scope not in ("local", "remote") or not valid_name(branch):
        raise Refused("not a usable branch name or scope")  # nothing to read from the repository yet
    status = get_repo_status(path)
    verdict = judge(status, scope, branch, sha=sha)
    if not verdict.ok:
        raise Refused(verdict.reason)
    repo = Path(status.path)
    detail = next(d for d in status.branch_details if d["scope"] == scope and d["name"] == (("origin/" + branch) if scope == "remote" else branch))

    log_path = log_path or LOG
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handle = log_path.open("a")
    except OSError as e:
        raise Refused(f"cannot write the deletion log, so nothing is deleted ({e.strerror or e})", 500) from e
    with handle:
        try:
            _log(handle, "attempt", str(repo), scope, branch, sha, verdict.reason)  # written down before anything changes
        except OSError as e:
            raise Refused(f"cannot write the deletion log, so nothing is deleted ({e.strerror or e})", 500) from e
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        if scope == "remote":
            argv = ["git", "-C", str(repo), "push", f"--force-with-lease=refs/heads/{branch}:{sha}", "origin", f":refs/heads/{branch}"]
        else:
            argv = ["git", "-C", str(repo), "branch", "-d" if detail["ancestor"] else "-D", "--", branch]
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)
            error = "" if result.returncode == 0 else (result.stderr.strip().splitlines() or ["git failed"])[-1][:200]
        except (subprocess.TimeoutExpired, OSError) as e:
            error = f"git did not finish: {e}"
        if error:
            _log(handle, "FAILED", str(repo), scope, branch, sha, error)
            raise Failed(error)
        if scope == "remote":  # forget our copy of the remote branch too, so the page does not show a branch that is gone
            subprocess.run(["git", "-C", str(repo), "update-ref", "-d", f"{REMOTES}origin/{branch}", sha], capture_output=True, env=env)
        _log(handle, "deleted", str(repo), scope, branch, sha, verdict.reason)
    return {"deleted": True, "scope": scope, "branch": branch, "sha": sha, "why": verdict.reason, "recovery": recovery_command(scope, branch, sha)}
