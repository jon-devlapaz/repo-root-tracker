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
