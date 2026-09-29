# Change brief — repo detail view (v3)

## Problem and outcome

The dashboard lists repos with status signals, but there's nowhere to go. Clicking a repo should open a full git dashboard: commit history with graph, working-tree changes with diffs, branch list. Research says developers want commit+diff side-by-side, branch orientation, and zero tab-switching.

**Outcome:** Clicking a repo card navigates to a detail view showing commits (with graph lanes), working-tree changes (expandable diffs), and branches — all inline, no page reloads.

## Acceptance criteria

**AC-1 — Click card navigates to detail**
Clicking a repo card (path or anywhere except buttons) opens the detail view for that repo. Back button returns to the list. URL hash reflects the view (`#/` list, `#/repo/<encoded-path>` detail) so refresh preserves place.

**AC-2 — Commit history with graph**
Detail shows last 30 commits: graph lane markers, short hash, subject, author, relative date. Merge commits visually distinct. Clicking a commit expands its full diff inline.

**AC-3 — Working-tree changes with diffs**
If dirty, a Changes section lists modified/staged/untracked files. Clicking a file expands its diff (tracked files) or shows "untracked" (untracked files).

**AC-4 — Branch list**
Branches section shows all local branches with last-commit date, ahead/behind vs upstream where available, current branch highlighted, stale branches flagged.

**AC-5 — All existing tests still pass**
```sh
python3 -m pytest tests/ -v
```
All 29 existing tests plus new detail tests pass.

## Approach

Backend (`src/repo_root_tracker/detail.py`):
- `get_repo_detail(path)` — branches, 30 commits with lane assignment, working-tree file list
- `get_commit_diff(path, hash)` — full diff for one commit
- `get_working_diff(path, file)` — diff for one working-tree file
- Simple graph lane algorithm server-side (track active lanes by commit parents)

Endpoints in `server.py`:
- `GET /api/repo?path=` → detail JSON
- `GET /api/commit?path=&hash=` → diff text
- `GET /api/working-diff?path=&file=` → diff text

Frontend: hash-based view switching in `dashboard.html`. Detail view replaces list. Inline diff expansion with syntax-tinted diff lines (add=green, del=red, hunk=blue).

## Risks and verification

| Risk | Mitigation |
|---|---|
| Large diffs slow the page | Cap diff output at 2000 lines server-side with truncation notice |
| Binary files in diff | Detect and show "binary file" placeholder instead |
| Graph lane algorithm wrong on complex merges | Lanes are cosmetic; correctness of commit list doesn't depend on them |

Verification: `pytest tests/` including new `test_detail.py`.
