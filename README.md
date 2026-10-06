# repo-root-tracker

A table of every git repository under a folder, and which of them are git-golden. It runs on your machine, needs
no setup and no registration, and never changes a repository (the one exception is the explicit **Fetch all** button).

```bash
./serve.sh        # starts the server on http://127.0.0.1:7842 and opens it
```

Python 3.11 or newer, standard library only, no build step.

## What you see

One row per checkout: repo, branch, working tree, sync, last commit, and a **Golden** verdict. Linked worktrees sit
under their project. Search by name, path or branch; filter to *Needs attention*, *Changed* or *Sync needed*;
sort by attention, name or last commit. Select a row to see every reason, the full path, local and remote branches,
other worktrees and when it was last fetched. The tab title shows how many repos need attention.

### git-golden

The definition is in [AGENTS.md](AGENTS.md). A repo is golden when it is on `main` with a clean tree; `main` is the
only branch locally and on `origin`, with no extra worktrees; local `main` is even with `origin/main`; and the
latest CI run on `main` succeeded. Open issues and pull requests never count.

| Verdict | Meaning |
| --- | --- |
| `golden` | every condition holds, including a passing CI run on `main` |
| `not golden: <reason>` | a condition fails; the row lists all of them |
| `golden pending CI` | every local condition holds, but CI is unchecked, running or unknown. It is never shown as golden without CI |
| `worktree` | a linked worktree; golden is judged on its project's main checkout |

Remote branches and "even with origin" come from local refs, so they are only as fresh as the last fetch. Each row
shows when that was. **Fetch all** runs `git fetch --prune` in each repo: it updates remote-tracking refs and never
touches a working tree, branch or commit. **Check GitHub** asks `gh` for the CI state on the default branch (needs
`gh` signed in; without it the verdict stays `golden pending CI`).

## Which folders are scanned

`~/dev/active` by default. Change it with `RRT_ROOTS` (a `:`-separated list) or repeat `--root PATH`:

```bash
RRT_ROOTS=~/dev:~/work ./serve.sh
python3 -m repo_root_tracker.server --root ~/dev/active --root ~/code --port 7842
```

The scan looks four folder levels below each root, never follows symlinks, does not look inside a repo, and skips
hidden and build folders (`node_modules`, `.venv`, `dist`, `build`, `target`, `.next`, `__pycache__`). It stops at
50,000 entries or five seconds and says **SCAN INCOMPLETE** if it does. Folders beyond the depth limit are counted,
not silently ignored. **Rescan** looks again.

## Local only

The server binds `127.0.0.1` and refuses any request whose `Host` is not `localhost`, `127.0.0.1` or `[::1]`, and any
cross-site POST. The page makes no external requests and ships under a strict content-security policy. There is no
password mode or remote hosting.

## Tests

```bash
python3 -m pytest tests -q
```

Real temporary git repositories (with a real bare remote) and a real browser: no network, no GitHub account. Needs
`pip install pytest playwright` and `python3 -m playwright install chromium`. The opt-in live GitHub test is
read-only and skipped unless you ask for it:

```bash
RRT_LIVE_GITHUB=1 RRT_LIVE_GITHUB_REPO=<owner>/<name> python3 -m pytest tests/test_github.py::test_endpoint_live_github
```

`python3 scripts/check_real_machine.py` compares the table's verdicts for the repos on this machine against plain
`git` commands and exits non-zero on any disagreement.

## Also in this package

`python3 -m repo_root_tracker` prints the git root of the current directory (`find_root`).
