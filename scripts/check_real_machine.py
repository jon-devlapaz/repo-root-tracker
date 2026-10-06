#!/usr/bin/env python3
"""Compare the table's verdicts with independent git commands on this machine's real repositories.

The reference below re-derives every golden condition from plain `git` output and its own copy of the AGENTS.md
definition; it deliberately shares no code with the tool's status or golden modules. Read-only: it runs git
queries and never fetches. CI is excluded (it needs the network); only the local conditions are compared.

Exit status is 1 when any verdict or any discovered repository disagrees.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo_root_tracker.scan import SKIP_DIRS, scan  # noqa: E402
from repo_root_tracker.status import get_repo_status  # noqa: E402

# How each of the tool's reason texts maps onto the condition names the reference uses.
REASON_TO_CONDITION = (
    ("on ", "branch"), ("uncommitted", "dirty"), ("local branch", "local-branches"), ("no origin", "no-origin"),
    ("remote branch", "remote-branches"), ("not found (not fetched", "remote-branches"), ("extra worktree", "worktrees"),
    ("not even with", "sync"), ("does not track", "tracking"), ("does not exist", "remote-branches"),
)


def git(repo: str, *args: str) -> str:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, env=env, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else ""


def reference(repo: str) -> set[str]:
    """The failing local conditions, from plain git output. Empty means golden on every local condition."""
    failing: set[str] = set()
    current = git(repo, "symbolic-ref", "--short", "-q", "HEAD") or "HEAD"
    has_origin = bool(git(repo, "remote", "get-url", "origin"))
    if current != "main":
        failing.add("branch")
    if git(repo, "status", "--porcelain"):
        failing.add("dirty")
    # The checked-out branch is already reported as "branch"; the tool does not count it a second time.
    if set(git(repo, "branch", "--format=%(refname:short)").split()) - {"main", current}:
        failing.add("local-branches")
    remotes = {b for b in git(repo, "branch", "-r", "--format=%(refname:short)").split() if b != "origin" and not b.endswith("/HEAD")}
    if not has_origin:
        failing.add("no-origin")
    elif remotes != {"origin/main"}:
        failing.add("remote-branches")
    if len(git(repo, "worktree", "list", "--porcelain").split("\n\n")) > 1:
        failing.add("worktrees")
    # Local main against origin/main, whatever is checked out and whatever main tracks.
    if has_origin and git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/main") and "origin/main" in remotes:
        if git(repo, "rev-list", "--left-right", "--count", "refs/heads/main...refs/remotes/origin/main").split() != ["0", "0"]:
            failing.add("sync")
        if git(repo, "rev-parse", "--abbrev-ref", "main@{upstream}") != "origin/main":
            failing.add("tracking")
    return failing


def tool_conditions(status) -> set[str]:
    found = set()
    for reason in status.golden("passing").reasons:
        found.update(name for needle, name in REASON_TO_CONDITION if needle in reason)
    return found


def independent_checkouts(root: Path, depth: int) -> set[str]:
    found = set()
    for base, dirs, files in os.walk(root):
        if len(Path(base).relative_to(root).parts) > depth:
            dirs[:] = []
            continue
        if ".git" in dirs or ".git" in files:
            found.add(os.path.realpath(base))
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS and not os.path.islink(os.path.join(base, d))]
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", action="append", default=None, help="folder to compare (default ~/dev/active)")
    roots = parser.parse_args().root or ["~/dev/active"]
    result = scan(roots)
    print(f"scan: {len(result.checkouts)} checkouts in {result.elapsed_seconds}s, truncated={result.truncated}, "
          f"{result.deeper_not_searched} folders beyond depth {result.max_depth}")
    mine = {c["path"] for c in result.checkouts}  # every checkout, linked worktrees included, as the independent walk sees them
    theirs = set().union(*(independent_checkouts(Path(r).expanduser().resolve(), result.max_depth) for r in roots))
    disagreements = 0
    for path in sorted(mine ^ theirs):
        print(f"  DISCOVERY DISAGREES: {path}: " + ("only the tool found it" if path in mine else "only the independent walk found it"))
        disagreements += 1
    print(f"\n{'repo':34} {'tool':16} {'reference':12} agree")
    for checkout in result.checkouts:
        if checkout["is_worktree"]:
            continue
        status = get_repo_status(checkout["path"])
        tool, ref = tool_conditions(status), reference(checkout["path"])
        agree = tool == ref and (status.golden("passing").status == "golden") == (not ref)
        disagreements += not agree
        print(f"{Path(checkout['path']).name:34} {'not golden' if tool else 'golden (local)':16} "
              f"{'not golden' if ref else 'golden':12} {'yes' if agree else 'NO'}")
        if not agree:
            print(f"    tool conditions: {sorted(tool)}\n    reference:       {sorted(ref)}")
    print(f"\n{'ALL AGREE' if not disagreements else f'{disagreements} DISAGREEMENT(S)'}")
    return 1 if disagreements else 0


if __name__ == "__main__":
    sys.exit(main())
