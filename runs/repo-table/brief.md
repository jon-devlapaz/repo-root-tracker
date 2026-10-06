# Repo table — build brief r1

## Problem and outcome

Replace the repo-root-tracker dashboard with one simple page that "just works": a table of every git repository under a folder, showing at a glance which are clean and which are not. Today's UI is an isometric bonsai board in a 3.4 MB single HTML file (3.0 MB of it embedded PNGs) with islands, collections, pins, replay, a command palette, a detail view, and password-protected remote hosting. It must be registered repo by repo, and its own test suite takes over 5 minutes. Deliver a review-ready PR.

Source: Jon's chat requests: "something simple and that just works", then choices (a) a status table only, scan for repos, localhost only. This is a proposal for the light-profile definition gate; no approval is recorded. Numbers below are proposed defaults.

The test for "simple": opening the page needs no setup, shows every repo within seconds, and answers "which repos are not git-golden?" without clicking.

## What the page shows

One table, one row per checkout (linked worktrees nest under their project). Columns:
- **Repo** (name, path muted), **Branch**, **Working tree** (`clean` or `3 changed`), **Sync** (`ahead 2 behind 0`, or `no upstream`), **Last commit** (relative time and subject), **Golden**.
- **Golden** applies the definition in `AGENTS.md`: on `main` with a clean tree; `main` is the only branch locally and on `origin`; no extra worktrees; local `main` even with `origin/main`; latest CI run on `main` succeeded. Values: `golden`; `not golden`, with the first failing reason in words and all reasons in the row's detail; `golden pending CI`, when every local condition holds but CI is unchecked or unknown. Open issues and PRs never count against it.
- A search box (name, path, branch), filter chips (All, Needs attention, Changed, Sync needed), sort (needs-attention first by default, then name). The tab title shows how many repos need attention. Selecting a row expands it: all failing reasons, full path with a copy button, local and remote branches, worktrees, last fetch time. No other actions.
- States are words as well as color. Light and dark follow the system. Keyboard operable, semantic `<table>`, visible focus. No images, no web fonts, no build step.

## Finding repos (no registration)

- Roots come from the `RRT_ROOTS` environment variable (path-separator list) or repeated `--root PATH` flags, defaulting to `~/dev/active` (Jon's choice). The page shows which roots it scanned.
- The scan looks up to 4 directory levels below each root, does not follow symlinks, does not descend into a repository (except to read `git worktree list`), and skips `node_modules`, `.venv`, `dist`, `build`, `target`, `.next` and `__pycache__`. Worktrees located outside the roots are found through their main repository.
- It runs on page load and on **Rescan**, under a time and entry cap. If a cap is hit, the page says the scan was truncated; it never silently shows a short list.
- Only paths found by the scan can be queried; any other path gets 404. The old `repos.json` registration API is removed.

## Data and speed

- Reuse `status.py` and `github.py`. Add: remote-tracking branches (from local refs), the count and branches of extra worktrees, and the golden evaluation as a pure function.
- The page lists repos first, then fetches each repo's status in parallel (at most 6 in flight, 10 s timeout each), so rows appear as they arrive. Baseline today: 11 repos take 3.2 s sequentially.
- CI on `main` comes from the existing default-branch workflow health in `github.py`, using the `gh` CLI, on demand through a **Check GitHub** button; with no `gh` or no network it shows `unknown`, never a guess.
- **Fetch (explicit, never automatic):** remote branches and "even with origin" rely on local refs, which go stale. Each row shows when it was last fetched, and a **Fetch all** button runs `git fetch --prune` per repo. It only updates remote-tracking refs and never touches a working tree, branch or commit. This is the one deliberate exception to the "never mutates repositories" principle and is listed under decisions below.
- Targets, to be measured and recorded: page weight under 60 KB (from 3.4 MB); first rows visible within 1 s of load on this machine's repos; all rows within 5 s.

## Localhost only

The server binds `127.0.0.1` only and rejects requests whose `Host` is not `localhost`, `127.0.0.1` or `[::1]` (DNS-rebinding protection). Password auth, public-host mode and the Pi deployment are removed.

## What is removed

All of it stays in git history.
- **Features:** the board, islands, collections, pins, replay and activity, the command palette, the detail view and diff view, bulk organize, editor links, saved organization (`organization.py`, `~/.config/repo-root-tracker/organization.json` is no longer read or written), `history.py`, `detail.py`, `auth.py`, the artwork directory.
- **Deployment:** `deploy/` (systemd units, Caddy, Pi installer, token scripts).
- **Docs:** `DESIGN.md` (bonsai system) and `PRODUCT.md` are replaced by short documents describing the table; `README.md` is updated.
- **Tests:** the roughly 40 board, island, bonsai and detail test files and their capture scripts are deleted because the features are. None are failing; each deleted file is listed in `runs/repo-table/handoff.md` against the feature it covered. Anything that tests behavior that survives (status, GitHub, server basics, accessibility) is kept or adapted, not dropped.

Kept: stdlib-only Python 3.11+, port 7842 and `serve.sh`.

## Acceptance criteria

1. The scan finds the 11 repos registered today plus every other repo under `~/dev/active`, and nothing else; a test with a fake tree covers nested repos, linked worktrees, symlink loops, skipped directories, the depth cap and truncation.
2. The golden evaluation is a pure function with a truth-table test for each of the five conditions and for the three result values.
3. Status adds remote branches and extra worktrees, with tests on temporary repositories (including a bare remote).
4. Server tests: scan-then-status flow, untracked path returns 404, localhost-only bind and `Host` rejection, removed endpoints are gone.
5. One browser smoke test against fixture repos: rows render, search and filters work, row expansion works, golden text is present without color, usable at 390 px width with no horizontal scroll, and keyboard operable.
6. Page weight is under 60 KB with no `data:image` or external requests; measured numbers recorded.
7. The full suite runs in under 120 s and passes. Previously failing tests are not weakened to get there.
8. A real-machine check compares the page's golden verdicts on this machine against independent `git` commands for every repo found, and records any disagreement.

## Risks and verification

- **Stale remote data** makes badges wrong. Mitigation: last-fetch time on every row, an explicit Fetch all, and no claim of "golden" without CI knowledge.
- **A huge or odd folder** slows the scan. Mitigation: depth, entry and time caps and a visible truncated message.
- **Removing features Jon may still miss.** They are recoverable from history; the brief asks for a clear yes.
- **Deleting about 40 test files** must not look like weakening tests. The handoff maps each file to the removed feature.
- Whether it feels simple and fast is Jon's judgment; that item is attested by him and never filled in by me.

## Decisions (settled by Jon in chat before approval)

1. **Fetch all:** yes, the explicit button is in.
2. **Default scan root:** `~/dev/active`.
3. **Deleting `deploy/` and the auth code:** confirmed; Pi hosting stops working.
4. **Removing saved islands, collections and pins:** confirmed.
