#!/usr/bin/env python3
"""Real-machine check for branch deletion, on disposable clones only.

For each of two real repositories it makes a clone in a temp folder whose pushes go to a local bare repository, so
nothing here can reach the real checkout or the real GitHub remote (GitHub is only read, by `gh pr list`). Then:
  1. a branch merged into main is judged deletable, deleted, logged, and brought back by the recovery command;
  2. a branch carrying the name of a real open pull request is refused, and stays.
The real checkouts' refs are compared before and after, and the check fails if they differ.

  python3 scripts/check_branch_delete.py [repo-name ...]     (default: the first two repos under ~/dev/active with an open PR)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from repo_root_tracker import branch_delete as bd  # noqa: E402
from repo_root_tracker.scan import scan  # noqa: E402
from repo_root_tracker.status import get_repo_status  # noqa: E402

ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
failures: list[str] = []


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=ENV, timeout=120)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def check(ok: bool, what: str) -> None:
    print(("  ok    " if ok else "  FAIL  ") + what)
    if not ok:
        failures.append(what)


def open_pr_branch(real: Path, slug: str) -> str | None:
    r = subprocess.run(["gh", "pr", "list", "--repo", f"github.com/{slug}", "--state", "open", "--limit", "1", "--json", "headRefName"],
                       capture_output=True, text=True, cwd=real, timeout=60)
    rows = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else []
    return rows[0]["headRefName"] if rows else None


def candidates(names: list[str]) -> list[tuple[Path, str, str]]:
    found = []
    for c in scan(["~/dev/active"]).checkouts:
        real = Path(c["path"])
        if c["is_worktree"] or (names and real.name not in names):
            continue
        status = get_repo_status(real)
        if not status.github_repo or not status.has_origin:
            continue
        pr = open_pr_branch(real, status.github_repo)
        if pr:
            found.append((real, status.github_repo, pr))
        if len(found) == 2 and not names:
            break
    return found


def run_one(real: Path, slug: str, pr_branch: str, tmp: Path) -> None:
    print(f"{real.name} ({slug}), open PR on {pr_branch}")
    before = git(real, "for-each-ref")
    bare, clone = tmp / f"{real.name}.git", tmp / real.name
    subprocess.run(["git", "clone", "-q", str(real), str(clone)], check=True, env=ENV, timeout=300)
    subprocess.run(["git", "clone", "-q", "--bare", str(clone), str(bare)], check=True, env=ENV, timeout=300)
    base = "main" if "refs/remotes/origin/main" in git(clone, "for-each-ref", "--format=%(refname)") else git(clone, "rev-parse", "--abbrev-ref", "origin/HEAD").split("/")[-1]
    git(clone, "remote", "set-url", "origin", f"https://github.com/{slug}")   # so the tool sees a GitHub repository
    git(clone, "remote", "set-url", "--push", "origin", str(bare))             # but every push lands in the local bare repository
    git(clone, "switch", "-q", "-C", "main", f"origin/{base}") if base != "main" else git(clone, "switch", "-q", "-C", "main", "origin/main")
    git(clone, "branch", "--set-upstream-to=origin/main", "main")
    git(clone, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")  # the clone of a clone inherits the wrong default
    tip = git(clone, "rev-parse", "main")
    for name in ("rrt-check/merged", pr_branch):
        git(clone, "branch", "-f", name, tip)
        git(clone, "push", "-q", "--force", "origin", f"refs/heads/{name}:refs/heads/{name}")
        git(clone, "update-ref", f"refs/remotes/origin/{name}", tip)

    status = get_repo_status(clone)
    check(status.github_repo == slug, "the clone looks like the GitHub repository to the tool")
    v = bd.judge(status, "remote", "rrt-check/merged")
    check(v.ok and v.kind == "merged", f"merged branch is deletable ({v.reason})")
    result = bd.delete(clone, "remote", "rrt-check/merged", tip, log_path=tmp / "log.tsv")
    check("rrt-check/merged" not in git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads/"), "it is gone from the remote")
    check("refs/remotes/origin/rrt-check/merged" not in git(clone, "for-each-ref", "--format=%(refname)"), "and from our copy of the remote")
    lines = [l.split("\t") for l in (tmp / "log.tsv").read_text().splitlines()]
    check([l[1] for l in lines] == ["attempt", "deleted"] and all(l[5] == tip for l in lines), "the log has the attempt and the result with the sha")
    subprocess.run(result["recovery"].replace("git push origin", f"git -C {clone} push origin"), shell=True, check=True, capture_output=True, env=ENV)
    check(git(bare, "rev-parse", "refs/heads/rrt-check/merged") == tip, "the recovery command restores the same sha")

    status = get_repo_status(clone)
    v = bd.judge(status, "remote", pr_branch)
    check(not v.ok and "open pull request" in v.reason, f"a branch named like an open PR is refused ({v.reason})")
    try:
        bd.delete(clone, "remote", pr_branch, tip, log_path=tmp / "log.tsv")
        check(False, "delete of the open-PR branch raised Refused")
    except bd.Refused:
        check(True, "delete of the open-PR branch raised Refused")
    check(pr_branch in git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads/"), "the open-PR branch is still on the remote")
    check(git(real, "for-each-ref") == before, "the real checkout's refs are exactly as before")


def main() -> int:
    picks = candidates(sys.argv[1:])
    if len(picks) < (1 if sys.argv[1:] else 2):
        print("could not find enough repositories with an open pull request (is gh signed in?)")
        return 2
    with tempfile.TemporaryDirectory(prefix="rrt-branch-delete-") as d:
        for real, slug, pr in picks:
            work = Path(d) / real.name
            work.mkdir()
            run_one(real, slug, pr, work)
    print("\nFAILED: " + "; ".join(failures) if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
