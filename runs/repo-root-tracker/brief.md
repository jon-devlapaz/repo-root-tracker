# Change brief — repo-root-tracker

## Problem and outcome

Every tool in the tink ecosystem that operates on a project needs the git repository root. Currently:

- `tink-route/src/tink_route/cli.py` uses `Path.cwd()` directly, silently breaking when invoked from a subdirectory.
- `tink/src/lib.rs` accepts a caller-supplied `cwd` with no `.git`-walking — same silent-wrong-root risk.
- No shared, correct, testable root-discovery utility exists in the ecosystem.

**Outcome:** A standalone pip-installable Python 3.11+ package `repo-root-tracker` that walks up the filesystem to find `.git` (directory or worktree file), returns the repository root, and raises a clear error when none is found. Exposes both a library API (`find_root`) and a CLI entry point.

## Acceptance criteria

**AC-1 — Library root discovery from subdirectory**
```sh
cd /tmp && mkdir -p testrepo/subdir && cd testrepo && git init && cd subdir
python3 -c "from repo_root_tracker import find_root; import pathlib; print(find_root(pathlib.Path.cwd()))"
```
Expected: absolute path of `testrepo` root, exit 0.

**AC-2 — CLI root discovery from subdirectory**
```sh
cd /tmp/testrepo/subdir
repo-root-tracker
```
Expected: absolute path of `testrepo` root on stdout, exit 0.

**AC-3 — Fail-fast when no git repo**
```sh
cd /tmp && mkdir notarepo && cd notarepo
repo-root-tracker
```
Expected: non-empty error message on stderr, exit nonzero.

**AC-4 — Worktree support (.git file)**
```sh
cd /tmp/testrepo && git worktree add /tmp/testrepo-wt HEAD && cd /tmp/testrepo-wt
repo-root-tracker
```
Expected: absolute path of `/tmp/testrepo-wt` on stdout, exit 0.

**AC-5 — Zero third-party dependencies**
```sh
pip show repo-root-tracker
```
Expected: `Requires:` field is empty or absent.

## Approach

Implement as a minimal Python package following the `tink-route` pattern:

```
src/repo_root_tracker/
    __init__.py      # find_root(start: Path) -> Path
    __main__.py      # CLI entry point
pyproject.toml       # hatchling, Python 3.11+, zero deps
tests/
    test_find_root.py
```

`find_root(start)`:
1. Resolve `start` to an absolute path.
2. Walk up via `.parent` until a `.git` entry exists (file or directory).
3. Return that directory.
4. Raise `NotARepositoryError` (subclass of `RuntimeError`) if filesystem root is reached without finding `.git`.

CLI (`__main__.py` / `repo-root-tracker` entry point):
- Calls `find_root(Path.cwd())`.
- Prints the result to stdout on success.
- Prints an error message to stderr and exits 1 on `NotARepositoryError`.

The implementation checklist is in `checklist.json`.

## Risks and verification

| Risk | Mitigation |
|---|---|
| Symlink traversal during walk could mis-identify root | Always resolve `start` with `Path.resolve()` before walking; walk via `.parent` on the resolved path |
| `.git` file that is not a worktree pointer (unusual) gives false positive | Accept any `.git` file as sufficient signal for root detection — consistent with `git rev-parse --show-toplevel` behavior |
| tink-route integration regressions when `Path.cwd()` is replaced | Not in scope for this run; tink-route integration is a separate downstream change |

Verification: `pytest tests/` — covers all five ACs with temporary directories and git worktrees.
