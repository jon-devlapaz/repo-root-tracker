# repo-table: build handoff

Built from the approved brief (r1, with Jon's four decisions settled in chat before approval).

## Not done, and why

- **Jon has not used it yet.** `jon-simple` is Jon's call. Everything else is automated or compared against plain git on this machine.
- **CI verdicts are untested against real GitHub.** The page's "Check GitHub" path is covered with the CI lookup replaced by a stand-in, and `get_default_branch_ci` is covered with a fake `gh`. No live call to GitHub was made. The existing opt-in live test (`RRT_LIVE_GITHUB=1`) was adapted to `/api/ci` but not run.
- **`scripts/check_real_machine.py` excludes CI** (it needs the network), so on your machine "golden" in that comparison means golden on every local condition.

## Interpretations and deviations (for review)

1. **Linked worktrees show `worktree` in the Golden column** instead of a verdict. The brief defines golden for a repository, not a worktree; extra worktrees already count against their project's main checkout.
2. **The depth limit is a counted note, not "truncated".** The brief said any cap hit means truncated. On your real folder one non-git experiment folder sits at the depth limit, so flagging it would be a permanent false alarm. `truncated` is reserved for the entry and time caps; folders beyond the depth limit are counted and shown ("2 folders deeper than 4 levels not searched").
3. **"Even with origin/main" is judged only while on `main`.** Off main, the reason is already "on X, not main".
4. **`pyproject.toml` now pins pytest to `src/`.** The package is installed in editable mode pointing at the main checkout, so without this every test run in this worktree imported the old code.
5. **`GET /api/ci` takes the place of `/api/github`.** It makes only the default-branch workflow calls, not PR, issue and merged-PR calls. `get_github_info` and its dataclasses still exist in `github.py` and are tested, but nothing calls them any more. They are dead code and a candidate for a follow-up deletion; I left them because the brief said to reuse `github.py`.
6. **Status lost its bonsai-only fields** (commit count, first commit date, 30-day activity, stale branches) and `get_repo_identity`, which saves three git calls per repo.
7. **Git now runs with `GIT_OPTIONAL_LOCKS=0` and `GIT_TERMINAL_PROMPT=0`**, so reading status never rewrites the index and a fetch can never wait on a credential prompt. A test checks the index is byte-identical after status calls.
8. **Strict content-security policy** (`default-src 'none'`, inline script and style only, connect to self only). The browser tests bypass it for their own string evaluation; one test runs the page under the policy with no bypass.
9. **Left untouched:** `.impeccable/` (design-tool context for the old design), `~/.config/repo-root-tracker/` on your disk (`organization.json`, `repos.json`, `session.key` are no longer read or written and were not deleted), and the dashboard server you already had running on port 7850 from the main checkout.
10. **Two legacy test files were adapted** (`test_github.py`, `test_default_branch_ci.py`): their endpoint tests now target `/api/ci` and `get_default_branch_ci`; the rest are unchanged.

## Findings

- **A real UI bug, found by the phone-width test:** the scan summary line contained a long path with no break opportunity, so on a narrow screen its text overflowed its box and the page scrolled sideways. It did not show on your real data (`~/dev/active` is short). Fixed with `overflow-wrap:anywhere` on `main`.
- **A false alarm in my first scanner**: it flagged a truncated scan on your real folder because of that one experiment directory. Found by running it on real data before building on it.
- **Mutation checks:** 25 deliberate bugs across the golden rules, status, scanner, server and page. 23 were caught at first; the 2 misses were test mistakes (a remote branch deleted from the same clone never needed pruning; results de-duplicated by real path hid symlink following). Both tests were fixed and all 25 are now caught.
- **Test mistakes found on the way (not product bugs):** a rescan test that created the repo before the first scan; a fetch test that pushed from the same clone; a `"never fetched" not in text` assertion that was simply wrong; the strict CSP rejecting Playwright's own `wait_for_function`.
- **Real-machine comparison:** all 17 main checkouts under `~/dev/active` agree with independent git commands (plus its own worktree in discovery). It was also shown to fail when a rule is deliberately broken.
- **The old suite was slow:** it reached 55% in 280 s and was stopped. The new suite runs in about 45 s.

## Page weight and speed (measured)

See `04-test/output/measurements.md`.

## Test files deleted, and the feature each covered

None of these were failing. They tested features that no longer exist.

- **Board, islands, scene and bonsai drawing (the isometric board and its trees)** (22): `test_ambient.py`, `test_board.py`, `test_board_batched_patching.py`, `test_board_finish.py`, `test_board_first.py`, `test_board_island_organization.py`, `test_board_performance.py`, `test_board_polish.py`, `test_board_project_behavior.py`, `test_board_project_github.py`, `test_board_projects.py`, `test_board_review_regressions.py`, `test_board_saplings.py`, `test_bonsai_design_review.py`, `test_gold_canopy.py`, `test_ground.py`, `test_island_cycle.py`, `test_isometric_scene.py`, `test_merged_pr_growth.py`, `test_replay.py`, `test_scale.py`, `test_vitals.py`
- **Organization: saved islands, collections and pins** (2): `test_organization.py`, `test_organization_browser.py`
- **Detail and history views (commits, working diff, activity)** (2): `test_detail.py`, `test_history.py`
- **Password-protected remote mode** (1): `test_remote_access.py`
- **Old dashboard theming, metadata, CI-in-board and accessibility smoke (replaced by tests/test_ui.py)** (6): `test_a11y_and_smoke.py`, `test_attention_colors.py`, `test_dashboard.py`, `test_dashboard_metadata.py`, `test_default_branch_ci_ui.py`, `test_theme.py`
- **Rewritten, not just deleted (replaced by the new files of the same purpose)** (2): `test_server.py`, `test_status.py`

Also deleted with their features: the helper and capture scripts `tests/bonsai_*.py`, `tests/capture_*.py`, `tests/check_pixel_bonsai.py`, `tests/pixel_bonsai_preview.py`, `tests/serve_bonsai_review.py`, `tests/organization_fake.py`, `tests/board_performance.js`, `tests/fixtures/bonsai-pixel/`, `scripts/embed_pixel_family.py`, `deploy/`, `src/repo_root_tracker/{auth,detail,history,organization}.py`, `src/repo_root_tracker/artwork/`.

Kept as they were: `test_find_root.py`, `test_github_reliability.py`, `test_sdlc_install.py`.


## Change after the approved brief: Jon's design feedback (chat, after trying it)

Jon tried the first build: "its alright. feels wordy and not super UI helpful", and said what he wants: to feel good
knowing a repo is clean and to get good feedback on what is outstanding. He asked for a design skill to punch it up
and for research on how others do it. This deviates from the approved brief r1 (columns, filters, wording); it was
directed in chat, not re-approved as a new brief.

Research (read, not run): `gita` and `gitpane` compress status into symbols and aligned columns, dim `main` so only
deviations carry color, and offer a "dirty first" sort; dashboard guidance puts the verdict and a summary first and
the table second and reserves color for status; branch-cleanup tools (`git-trim`, `git-sweep`) separate branches that
are merged from ones with unmerged work and warn that `git branch --merged` misses rebase and squash merges.

Skill: this repo's `impeccable` design skill (installed in the main checkout, not in this worktree). I read its
operate, critique, clarify, distill and craft-floor playbooks and applied them by hand. I did **not** run its launcher
binary and I did not run its `critique` command, which needs that binary and isolated sub-agents. So this is the
skill's guidance applied, not a full critique run.

What changed: grouped by status with counts on the filter chips (no hero-metric block, per the skill's refusals); a
status pill with a drawn SVG icon instead of sentences; short outstanding chips; branch dimmed on `main`; "closest to
clean" sort; the explanation and a copyable fix command per item in the expanded row; stray branches marked merged
(safe to delete) or unmerged via `git cherry`; a "Check CI" button in the Pending CI heading; and "Everything is
clean." only when every repo is golden. Removed: the Working tree and Sync columns, the Changed and Sync-needed
filters, and most sentence text.

Bugs found while doing it, all fixed, all with tests: the "Everything is clean." banner showed while 10 repos needed
work (a CSS `display:flex` overrode the `hidden` attribute); group `<tbody>`s nested inside another `<tbody>` crushed
the column headings; times wrapped onto two lines. My "rebase-merged branch" test was passing without testing rebase
detection at all (main had not moved, so the cherry-pick recreated the identical commit); it now proves the case that
plain `git branch --merged` gets wrong.

Limits: `git cherry` cannot see squash merges, so a squash-merged branch reads as unmerged (stated next to every list).
The "Check CI" path was never run against real GitHub from this build. The copy buttons only copy; nothing runs a
command.


## Change after the approved brief: phone access on the same wifi (Jon, chat)

The approved brief said "Localhost only" and Jon confirmed removing the password mode and Pi hosting. After trying the
page he asked to reach it from his iPhone SE on the same network. I offered three ways (opt-in `--lan` with a secret
token, opt-in `--lan` with no token, a private network such as Tailscale) and Jon chose **`--lan` with no token**. This
reverses part of the brief's "Localhost only" section by his direction; it was not re-approved as a new brief.

What I built around that choice, so that "no token" is as safe as it can be: it is off unless `--lan` is passed (also
`RRT_LAN=1 ./serve.sh`); only private-network client addresses are served (explicit list: 10/8, 172.16/12, 192.168/16,
169.254/16, IPv6 local; not Python's `is_private`, which also accepts reserved documentation ranges, found by a test);
the `Host` header must be this machine's own address or name (DNS rebinding stays refused); POSTs (Fetch, Rescan) are
accepted only from the loopback client, so a phone is read-only, and the page tells it so and disables those buttons.

Known risk Jon accepted: anyone on that private network (guest wifi, a shared office) can read repo paths, branch names
and commit messages while `--lan` is running. There is no password. The terminal prints a warning at start.

Not verified from this build: **a real phone, and the real network path.** My shell cannot reach any off-loopback
address (not even the router), and this Mac's firewall is on with `python3.13` not in its allow list, so connections to
the wifi address timed out here. The access rules are tested with a simulated phone (9 mutants caught); whether macOS
lets the connection through, and how the page looks on an actual iPhone SE, is for Jon to confirm.


## Independent critique and what I changed (Jon: "have a subagent critique it for design and function", then "yes")

A fresh-context reviewer read the code, drove the page in a real browser, and built temporary repositories to reproduce
problems. I did not take its claims on trust: each safety finding became a failing test first, using its repro, then a fix.

**Function, fixed and tested (all reproduced):**
1. A local branch named `origin/feat` shadowed the remote one, so the wrong ref was judged. Now every ref is read and judged
   by its full name.
2. Remote refs go stale: a branch pushed to after the last fetch still read "safe to delete", and the old command deleted
   the new work. Deletes are now `--force-with-lease=<branch>:<commit>`, and the page says the remote state is "as of last
   fetch". A test runs the copied command for real and confirms it is refused after the branch moves.
3. `git cherry` skips merge commits, so a merge commit carrying its own change read as merged. A non-ancestor branch is now
   merged only if it also has no merge commits that main lacks. (My first fix compared merge results with main's tree; it
   made almost every old branch "cannot tell" on a living repo, which I saw in a screenshot, so I replaced it.)
4. `git branch -d` refuses patch-merged branches. They now get their own labelled `-D` command; ancestors keep `-d`.
5. "Even with origin/main" now compares local `main` with `origin/main`, whatever is checked out and whatever `main` tracks
   (a fork tracking `upstream/main` could read Golden while `origin/main` was ahead). "Not tracking origin/main" is its own item.
6. Copied commands now name their repository (`git -C <path>`), the diverged case gets a valid `&&` command, not two glued together.
7. A CI result is tied to the commit it was checked for; after local main moves it is "stale", and a stale failing result is
   not reported as failing.
8. Error rows now land under Needs work; a project with no main checkout of its own (a bare layout) is judged by its worktree.
9. `/api/ci` runs `gh` with the owner's login, so only the computer running the tool may start it (phones cannot), and any
   request a browser marks `Sec-Fetch-Site: cross-site` is refused.

**One judgment call, for Jon to overrule:** a branch whose patch main applied and *later reverted* is still called merged by
patch. The reviewer called this "should fix". I kept it because the work was merged and its history stays on main, so
deleting the branch loses nothing that history does not hold. It still needs `-D`, and a test pins the decision.

**Design, changed:** CI is now checked automatically on load for repos that are otherwise clean (never for repos that need
work), so Golden is visible without a click; switch off with `--no-auto-ci`. The status column is gone (the group heading
says it once) in favour of a small icon with the words in its accessible name; the redundant branch chip is gone and the
checked-out branch is no longer also counted as a stray branch; "not fetched" is told apart from "origin has no main"
(a `master` repo); merged branches are summarized in one line and unmerged ones listed; the phone cards lost their labels
and now fit about five repos per screen with 44 px tap targets; counts now agree (projects everywhere, a cap of 40 branches
is disclosed as "showing 40 of N"); control and selected-filter borders reach 3:1 contrast.

**Not done, on purpose:** about 200 lines of dead PR/issue code in `github.py` (the reviewer and my earlier note both flag
it) because deleting it also deletes tests of it and was not part of what Jon approved. A fix for the stale
`origin/HEAD` label oddities was not needed after the "no origin/main" change.

**Mutation checks on this round:** 19 deliberate bugs in the new logic (merge-commit check, full ref names, sync rules,
commit-tied CI, loopback-only CI, cross-site refusal, lease guard, repo-scoped commands, error grouping, auto-CI scope,
`-D` labelling, unmerged-as-merged, branch cap note, diverged command, tap target, generated phone labels). All caught;
one needed a stronger test first (CSS-generated labels are invisible to text checks).


## Change after the approved brief: open PRs and issues (Jon: "can it number the gh issues and PR's?")

I read this as: show the open pull requests and issues for each repo, with counts and numbers. Added: quiet dashed chips
(`2 PRs`, `3 issues`, `30+` past the newest 30) and, in the expanded row, a numbered list with titles, draft state and
links to GitHub. Two choices I made that Jon can reverse: they are informational only and never change the golden verdict
(`AGENTS.md` says open issues and PRs are tracked separately), and they are read automatically on load from the Mac with
the CI check (the same `--no-auto-ci` switch) because they use his `gh` login; a phone sees what was last read and cannot
start a lookup. A failed `gh` call shows "unavailable" or "could not be read", never zero. Links are made clickable only if
they start with `https://github.com/`; titles are inserted as text. This revives a small, tested slice of what was dead PR
and issue code (it is a new two-call function, not the old five-call one, which is still unused).

Mutation checks: 10 deliberate bugs (a failed call read as zero, phones starting lookups, any link clickable, zero-count
chips, missing "+", titles as markup, PRs styled as problems, ...), all caught after fixing one of my own mutants that
changed nothing.

Not verified: real GitHub. The two `gh` calls are covered with a stand-in for `gh`; the `gh pr list` / `gh issue list` JSON
field names (`number,title,url,isDraft,headRefName`) come from the existing, previously-working call in this file.
