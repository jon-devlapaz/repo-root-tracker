# Change brief — dashboard status signals (v2)

## Problem and outcome

The v1 dashboard lists tracked repo paths and validates existence, but shows no git state. Web research on developer dashboard preferences consistently identifies four high-signal local indicators:

1. **Dirty/clean working-tree state** — "what did I touch" (ranked #1)
2. **Current branch + last commit** — orientation (ranked #2)
3. **Ahead/behind vs upstream** — "where do I stand vs team" (ranked #3)
4. **Stale branches** — "stale branch blindness" is a top complaint

**Outcome:** Each repo card in the dashboard shows these four signals, fetched via local git subprocess calls. No remote API auth. No vanity metrics (LOC, velocity, commit graphs — explicitly dismissed by research).

## Acceptance criteria

**AC-1 — Dirty/clean badge with counts**
```sh
cd /tmp && mkdir -p v2test && cd v2test && git init
touch newfile && echo change >> README.md 2>/dev/null || echo x > README.md
# Add /tmp/v2test to the dashboard, verify the card shows modified/untracked counts
```
Expected: card shows dirty indicator with "1 modified, 1 untracked" (or equivalent counts). Clean repos show a green clean badge.
Runs in: browser at the dashboard URL after adding the repo.

**AC-2 — Branch + last commit displayed**
```sh
# With /tmp/v2test tracked:
git -C /tmp/v2test add -A && git -C /tmp/v2test commit -m "test commit"
```
Expected: card shows current branch name, short hash + "test commit", and a relative date (e.g. "just now", "2 minutes ago").

**AC-3 — Ahead/behind with graceful no-upstream**
```sh
# /tmp/v2test has no upstream — card must show "no upstream" (not crash)
# For a repo WITH upstream: branch 2 commits ahead of origin/main
```
Expected: repos with upstream show "↑N ↓M"; repos without show "no upstream" in muted text.

**AC-4 — Stale branch count**
```sh
# In a tracked repo: git branch old-feature <old-commit>; touch its date back
```
Expected: card shows stale-branch count (branches untouched >30 days). Clicking reveals the branch list.

**AC-5 — All existing tests still pass**
```sh
python3 -m pytest tests/ -v
```
Expected: all tests pass (existing 19 + new status tests).

**AC-6 — Status fetch does not block dashboard load**
Expected: repo list renders immediately; status signals load asynchronously (per-card spinner, then populated). A repo that is slow or errors shows an error state, not a blank page.

## Approach

Add a `status.py` module to `src/repo_root_tracker/`:

```python
get_repo_status(path: Path) -> RepoStatus
# Returns: branch, last_commit {hash, subject, date, relative},
#          dirty {modified, staged, untracked, is_clean},
#          sync {ahead, behind, has_upstream},
#          stale_branches [{name, last_commit_date}]
```

Add `GET /api/repos/status?path=<path>` endpoint to `server.py`. Each dashboard card fetches its status async after the list loads.

The implementation checklist is in `checklist.json`.

## Risks and verification

| Risk | Mitigation |
|---|---|
| `git` subprocess per repo is slow for many repos | Async per-card fetch (AC-6); cards render before status arrives |
| Missing `git` binary on PATH | `get_repo_status` raises; endpoint returns 503 with clear message |
| Upstream ref missing (`@{u}` fails) | Catch and return `has_upstream: false`; do not propagate exception |
| Symlink in tracked path | `find_root` already resolves; status uses the resolved root |

Verification: `pytest tests/` including new `test_status.py`.
