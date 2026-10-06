# repo-table: closure

## Outcome
Merged. PR: https://github.com/jon-devlapaz/repo-root-tracker/pull/28 ("Replace the bonsai dashboard with a simple repo table"). Merge revision: `0086d50b82be8c52bf875f9d8eb64827f5086bb1` (merge commit on `main`). Delivery archive: `~/.local/share/tink-substrate/archive/repo-root-tracker/repo-table/` (phase `delivery`, taken before the license commit; not revised).

## Observed checks
- **CI:** the first run failed in 3 seconds with no steps because GitHub would not start the job ("recent account payments have failed or your spending limit needs to be increased"), not because of the code. After Jon made the repository public (so standard runners are free), the run on `680f166` completed with **success** on Ubuntu, Python 3.13, with Chromium installed fresh. It finished before the merge.
- **Local, after the merge, on `main` at `0086d50`:** 245 tests passed, 1 skipped (the opt-in live-GitHub test). The run's checklist was 9/9 with `Verification: current` at `680f166`.

## Human feedback
Jon: "its alright. feels wordy and not super UI helpful"; later "It's pretty good"; then "it's good, write the retro and open the PR". On merging: "this is mainly for me". He did not say whether he tried the iPhone view.

## What changed after delivery
- The repository was made **public** at Jon's request so Actions would not need billing, after an audit found no credentials in history. An MIT `LICENSE` was added first. Left as they were, and now public: the second author identity `sb@x.io` on 93 commits, and `/Users/jondev` paths in older run evidence under `runs/`.

## Remaining limits
- Never run against real GitHub or a real phone from this build: the CI check, the PR and issue lookups (covered with stand-ins for `gh`), and `--lan` access. The first real use will be Jon's.
- Squash-merged branches read as unmerged (git cannot see them); the page says so.
- `--lan` has no password; anyone on the private network can read repo paths, branch names and commit messages while it runs.
- About 200 lines of dead PR and issue code remain in `github.py`.

## Follow-ups
Open it on the phone and with real GitHub and report anything off. Delete the dead `get_github_info` code and its tests in a small PR. Upgrade this repo's SDLC scaffold from 1.18.4 to 1.20.0 (its `status` still prints the misleading "Next:" text). Optionally scrub the old `/Users/jondev` paths from `runs/`.
