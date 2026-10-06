#!/usr/bin/env python3
"""Mutation check for branch deletion: break each safety rule on purpose and confirm the tests notice.

Each mutation edits a source file in place, runs the named tests, and restores the file. A mutation that leaves the tests
green is a safety rule nobody is checking, and this exits 1."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BD, SRV = ROOT / "src/repo_root_tracker/branch_delete.py", ROOT / "src/repo_root_tracker/server.py"
T = ["tests/test_branch_delete.py", "tests/test_branch_delete_server.py"]

MUTATIONS = [
    ("sha check removed", BD, 'if sha is not None and sha != detail["sha"]:', "if False:"),
    ("open-PR check removed", BD, "if open_pr:", "if False:"),
    ("current-branch check removed", BD, 'if branch == status.branch or branch in held:', "if False:"),
    ("default-branch check removed", BD, 'if branch in ALWAYS_KEPT or branch == default:', "if False:"),
    ("gh failure treated as no pull requests", BD, "        if found is None:\n            return no(", "        if False:\n            return no("),
    ("closed-PR tip check removed", BD, 'if latest.get("headRefOid") != detail["sha"]:', "if False:"),
    ("closed PR allowed for local branches", BD, 'if scope == "remote" and prs and all(', 'if prs and all('),
    ("loopback check removed from POST", SRV, 'if peer != "loopback" or (origin and', "if (origin and"),
    ("loopback check removed from verdicts", SRV, 'self._json(403, {"error": "deleting is only offered on this computer"})\n                return', "pass"),
    ("attempt never logged", BD, "            _log(handle, \"attempt\", str(repo), scope, branch, sha, verdict.reason)  # written down before anything changes\n", "            pass\n"),
    ("attempt logged after the delete", BD, "            _log(handle, \"attempt\", str(repo), scope, branch, sha, verdict.reason)  # written down before anything changes\n", "            pass\n",
     '        _log(handle, "deleted", str(repo), scope, branch, sha, verdict.reason)\n', '        _log(handle, "attempt", str(repo), scope, branch, sha, verdict.reason)\n        _log(handle, "deleted", str(repo), scope, branch, sha, verdict.reason)\n'),
    ("lease removed from the remote delete", BD, 'f"--force-with-lease=refs/heads/{branch}:{sha}", ', ""),
    ("unscanned path allowed", SRV, 'if path not in current_scan().paths():\n            self._json(404, {"error": "not found by the scan"})\n            return\n        try:\n            result', "if False:\n            return\n        try:\n            result"),
]


def failing(tests: list[str]) -> list[str]:
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=ROOT, capture_output=True, text=True)
    hit = [l for l in r.stdout.splitlines() if l.startswith("FAILED")] if r.returncode else []
    if r.returncode and not hit:
        raise SystemExit("a mutation broke the code instead of changing its behaviour:\n" + r.stdout[-800:])
    return hit


def main() -> int:
    survived = 0
    for name, path, *edits in MUTATIONS:
        pairs = list(zip(edits[::2], edits[1::2]))
        original = path.read_text()
        bad = [old for old, _ in pairs if original.count(old) != 1]
        if bad:
            print(f"  BROKEN  {name}: the text to mutate is not there exactly once")
            survived += 1
            continue
        mutated = original
        for old, new in pairs:
            mutated = mutated.replace(old, new)
        try:
            path.write_text(mutated)
            hit = failing(T)
        finally:
            path.write_text(original)
        print(("  caught   " if hit else "  SURVIVED ") + name + (f"  <- {hit[0].split(' - ')[0][7:]}" if hit else ""))
        survived += not hit
    print(f"\n{len(MUTATIONS) - survived}/{len(MUTATIONS)} caught")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
