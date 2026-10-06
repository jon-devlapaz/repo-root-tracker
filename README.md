# repo-root-tracker

A table of every git repository under a folder, and which of them are git-golden. It runs on your machine, needs
no setup and no registration, and changes a repository only when you press **Fetch** or confirm deleting a branch.

```bash
./serve.sh        # starts the server on http://127.0.0.1:7842 and opens it
```

Python 3.11 or newer, standard library only, no build step.

## What you see

Repos are grouped by what needs doing: **Needs work**, **Pending CI**, then **Golden**. Inside a group the repos
closest to clean come first, so the quick wins are on top. Each row is a small status icon and the repo name, its
branch (dimmed on `main`, red anywhere else), short chips for what is outstanding (`1 change`, `9 remote branches`,
`↑2 ↓1`, `no origin`), and when it last changed. The counts on the filter chips are the summary, and the tab title
shows how many repos need work. "Everything is clean." appears only when every repo is golden.

Open pull requests and issues show as quiet dashed chips (`2 PRs`, `3 issues`, `30+ issues` when there are more than
the newest 30). Open a row to see them numbered with titles and links to GitHub. They are information only: your
`AGENTS.md` tracks them separately, so they never change a repo's verdict. They are read with `gh` on load, together with
the CI check (switch off with `--no-auto-ci`), and from this computer only; a phone sees what was last read. If `gh` cannot
answer, the row says "unavailable", never zero.

Select a row to see exactly what to do about each outstanding item, with a copy button for the command. Every command
names its repository (`git -C <path> ...`), so pasting it into the wrong terminal cannot touch another repo. The tool
only shows and copies commands. It never runs them.

For stray branches it says whether each one is **merged and safe to delete**, holds **N commits not on main**, or
that it **cannot tell**. A branch counts as merged when it is an ancestor of `main`, or when every commit has an
equivalent patch on `main` (`git cherry` sees through rebase merges) and it has no merge commits of its own, which can
carry changes `git cherry` never inspects. A change `main` applied and later reverted still counts as merged: it was
merged and its history stays on `main`. Git cannot see squash merges, so such a branch reads as unmerged; check its pull
request. Branches judged by patch need `git branch -D`, so they get their own labelled command.

### Deleting a branch

Next to a branch that may be deleted there is a **Delete** button. It opens a dialog naming the repo, the branch, its
commit, and why it may go; **Cancel** has the focus, so Enter alone deletes nothing. A branch may go when it is
proven merged into `main`, or (remote branches only) when its pull request was closed without merging and the branch
has no commits newer than that pull request. Those commits stay on GitHub at `refs/pull/<n>/head`.

The server decides, not the page, and checks again when you confirm. It refuses: `main`, `master` and the default
branch; the checked-out branch or one held by any worktree; a branch with an open pull request; a branch that moved
since the page looked (the remote delete is lease-guarded); and anything it cannot check, such as `gh` being
unavailable. Every attempt is appended to `~/.local/share/repo-root-tracker/deleted-branches.log` with the commit
sha before anything is deleted, and if that log cannot be written, nothing is deleted. After a delete the page shows
the command that brings the branch back. There is no "delete all" button. Deleting only works from the computer
running the tool: a phone in `--lan` mode sees no buttons.

Remote branches are judged from the last fetch, which the row shows. Each remote delete is lease-guarded
(`--force-with-lease=<branch>:<commit>`): if someone pushed to the branch after your last fetch, git refuses instead of
deleting their work.

### git-golden

The definition is in [AGENTS.md](AGENTS.md). A repo is golden when it is on `main` with a clean tree; `main` is the
only branch locally and on `origin`, with no extra worktrees; local `main` is even with `origin/main`; and the
latest CI run on `main` succeeded. Open issues and pull requests never count.

| Verdict | Meaning |
| --- | --- |
| `Golden` | every condition holds, including a passing CI run on `main` |
| `Needs work` | a condition fails; the chips and the row detail list all of them |
| `Pending CI` | every local condition holds, but CI is unchecked, running or unknown. It is never shown as golden without CI |
| `Worktree` | a linked worktree; golden is judged on its project's main checkout |

Remote branches and "even with origin" come from local refs, so they are only as fresh as the last fetch. Each row
shows when that was. **Fetch** runs `git fetch --prune` in each repo: it updates remote-tracking refs and never
touches a working tree, branch or commit. On load, **CI is checked automatically for repos that are otherwise clean** (never for repos that already need work), and
**GitHub** (or **Check CI** in the Pending CI heading) asks `gh` for the CI state on the default branch (needs
`gh` signed in; without it the verdict stays `Pending CI`). A CI result counts only for the exact commit it was checked
for, so a new local `main` goes back to "stale" until checked again. Switch the automatic check off with `--no-auto-ci`
or `RRT_AUTO_CI=0`.

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

## Local only, and an opt-in phone view

By default the server binds `127.0.0.1` and refuses any request whose `Host` is not `localhost`, `127.0.0.1` or `[::1]`,
and any cross-site POST. The page makes no external requests (its one outbound link, "Open Actions" for failing CI, only
opens when you click it) and ships under a strict content-security policy. There is no password mode or remote hosting.

To look at it from your phone on the same wifi, start it with `--lan`:

```bash
RRT_LAN=1 ./serve.sh        # or: python3 -m repo_root_tracker.server --lan
```

It prints the address to open (`http://<your-mac's-address>:7842/` and `http://<your-mac>.local:7842/`). LAN mode is
**read-only and has no password**: anyone on that private network can see repo paths, branch names and commit messages.
What still protects it: it is off unless you ask; only clients on private network ranges (10.x, 172.16-31.x,
192.168.x, link-local) are served, so a port forwarded from the internet is refused; the `Host` must be this
machine's own address or name; and **Fetch**, **Rescan** and the GitHub checks only work from the computer running it, so a phone can look but
never change anything or use your GitHub login. macOS may ask you to allow incoming connections for Python the first time.

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

## License

MIT. See [LICENSE](LICENSE).
