# Branch delete buttons — build brief r1

## Problem and outcome

The dashboard already tells Jon which branches are safe to delete and prints a copyable `git branch -d` or lease-guarded `git push … :refs/heads/x` command for each. He then pastes it into a terminal. Add a **Delete** button on those branches so he can do it from the page. Deliver a review-ready PR.

Source: Jon's chat ("could i have deleting capabilities as buttons on the dashboard?", then "proceed"). This is a proposal for the light-profile definition gate; no approval is recorded. The numbers and wording below are proposed defaults.

This is the tool's first destructive action, so the design is mostly about when a button is allowed to exist and what the server re-checks before acting.

## What the page shows

- A **Delete** button beside each branch the page currently judges deletable, in the expanded row's local and remote branch lists. It replaces nothing: the copyable command stays for reading and for LAN/phone viewing.
- Clicking opens a confirm dialog naming the repo, the branch, local or remote, its tip sha (short), its age, and the reason it is deletable in words ("merged into main", "closed PR #11, never merged"). The dialog has **Cancel** (default focus) and a **Delete branch** button. No one-click delete.
- After a delete, the row refreshes from the server and the page shows a one-line result with the full sha and the recovery command (`git push origin <sha>:refs/heads/<name>`), with a copy button. A failed delete says why in words and leaves everything as it was.
- Buttons are absent (not just disabled) when the page is viewed from another device in `--lan` mode, since `writable` is already false there. States are words as well as color; keyboard operable; dialog traps focus and closes on Escape.

## When a branch counts as deletable

The server decides, never the page. A branch is deletable only if all of these hold at the moment of the request:
1. It is not `main`, `master`, the remote's default branch, or (for local) the currently checked-out branch or one checked out in any worktree.
2. It is **proven merged** by the existing rule (ancestor of main, or every commit has an equivalent patch and no merge commits), **or** its PR is closed without merging (see decision 1).
3. It has no open PR (checked with `gh`; if `gh` or the network is unavailable, the answer is "cannot check", which refuses the delete rather than allowing it).
4. For a remote branch, its tip still equals the sha the page showed (lease), and for a local branch, git's own `-d`/`-D` rules apply (`-D` only when the patch rule proved it merged).

Anything else returns a refusal with the reason in words. Branches judged "not merged, no PR" never get a button.

## Server

- New `POST /api/branch/delete` with JSON `{path, scope, branch, sha}`. Same admission as Fetch and Rescan: loopback peer only, local `Host`, no cross-site origin, path must be one the scan found (else 404), so `--lan` viewers cannot delete.
- The server re-runs the status and verdict itself, compares `sha` to the current tip, and refuses on any mismatch (409, "the branch moved since you looked").
- The branch name is validated with `git check-ref-format --branch` and passed as a single argv element with `--` where git allows; no shell. Names starting with `-` are refused.
- Every attempt, success or failure, is appended to `~/.local/share/repo-root-tracker/deleted-branches.log` in the existing tab-separated format (timestamp, deleted|FAILED, repo path, scope, branch, sha, note). If the log cannot be written, the delete does not happen.
- Closed-PR lookup: one `gh pr list --state closed --head <branch>` per candidate, on demand only (at delete time and when the row is expanded), never at page load. Result shapes: merged, closed-unmerged with PR number, none, unknown.

## Out of scope

Bulk "delete all" (a bigger blast radius for little gain), worktrees, stashes, tags, renaming `master` to `main`, and deleting branches with unmerged work and no PR.

## Acceptance criteria

1. Truth-table tests for the server verdict, one per rule in "When a branch counts as deletable", each on a temporary repo with a bare remote: merged ancestor, merged by patch, closed-unmerged PR (with `gh` stubbed), open PR, unmerged with no PR, default branch, current branch, branch in another worktree, `gh` unavailable.
2. A request is refused (and nothing is deleted) when the sha is stale, the name is malformed or starts with `-`, the path is unscanned, the peer is not loopback, the Host is wrong, or the request is cross-site. Each has a test.
3. A successful local and a successful remote delete remove exactly that ref and no other, and each writes one log line with the right sha. A failed push writes a FAILED line. An unwritable log blocks the delete.
4. The recovery command in the result, run as shown, restores the branch at the same sha (tested on a temporary repo).
5. Browser tests: button appears only on deletable branches and not in LAN/read-only mode; Cancel is the default focus and deletes nothing; confirm deletes and the row updates; a refused delete shows its reason; dialog is keyboard operable and closes on Escape; usable at 390 px.
6. Mutation checks, recorded in the handoff: removing the sha check, the open-PR check, the loopback check, the log-before-delete order, and the current-branch check each makes at least one test fail.
7. Page stays under 60 KB, no external requests; the full suite stays under 120 s and passes; no existing test is weakened.
8. A real-machine check against disposable clones of two real repos confirms a merged branch deletes and is recoverable, and that a branch with an open PR is refused. It never deletes a branch in Jon's actual checkouts or on his real remotes.

## Risks and verification

- **Deleting the wrong thing** is the whole risk. Mitigations: server-side re-judgment, sha lease, per-branch confirm, append-only log, recovery command, no bulk action, and a disposable-clone real-machine check.
- **Stale data**: the page's last fetch may be old. The lease and the server re-check make a stale click fail safely; the dialog shows the fetch age.
- **`gh` flakiness** fails closed.
- **Whether the confirm flow feels right** is Jon's judgment; that item is attested by him and never filled in by me.

## Decisions (proposed; Jon to settle before approval)

1. **Closed-PR branches get a button:** yes, with a stronger warning line, since their commits stay at `refs/pull/<n>/head`.
2. **No bulk delete** in this version.
3. **Branches only**: worktrees and stashes stay out.
