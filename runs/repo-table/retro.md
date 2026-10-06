# repo-table: retro

## Outcome
Replaced the bonsai dashboard with one small page: a table of every git repository found under `~/dev/active`, grouped by Needs work, Pending CI and Golden, with short chips for what is outstanding and a per-row explanation with copyable fix commands. Scans for repos (no registration), localhost by default with an opt-in read-only `--lan` view for a phone, and open pull requests and issues shown for information. Page weight 3.37 MB to 31 KB; first row in 0.03 s, every verdict in about 0.9 s on this machine's 19 checkouts. PR: see `closure.md` for the number and merge revision.

## Evidence and its limits
**Automated (all passed in `verify`):** 245 tests plus one opt-in live-GitHub test that skips unless asked, in about 74 s. They use real temporary git repositories with real bare remotes and a real browser, never mocks of git. About 75 deliberate bugs were injected over five mutation sweeps across the golden rules, status, scanner, server and page; all are now caught, but 8 were not at first and each of those was a weak test or a wrong test, not a code bug. A script re-derives every verdict from plain `git` with its own copy of the definition: all 17 main checkouts agree.

**Independent critique:** a fresh-context reviewer found real defects my own tests had missed (below). I reproduced each as a failing test before fixing it.

**Human (Jon, in chat):** "its alright. feels wordy and not super UI helpful", then "It's pretty good", then "it's good". He did not say whether he opened it on his iPhone SE, nor whether the automatic CI and PR/issue lookups worked against his real GitHub account.

**Not verified:** the real phone and the real network path (this build's shell cannot reach any off-loopback address, and this Mac's firewall was on); any call to real GitHub (CI and PR/issue lookups are covered with stand-ins for `gh`); squash-merged branches (git cannot see them, so they read as unmerged and the page says so); a fresh-machine run.

## What went wrong, and the repairs
- **The "safe to delete" judgment was wrong in three ways** (found by the critique, not by me): a local ref named `origin/x` shadowed the remote one; a remote branch pushed to after the last fetch still read merged, so the copied `git push --delete` would have destroyed new work; and `git cherry` skips merge commits, so a merge commit carrying its own change read as merged. Fixed with full ref names, lease-guarded deletes, and a no-merge-commits rule. My first version of that last fix compared trees and made almost every old branch "cannot tell" on a living repo; a screenshot showed it and I replaced it.
- **A test that proved nothing:** my "rebase-merged branch" test passed without testing rebase detection, because `main` had not moved and the cherry-pick recreated an identical commit. Found by mutation testing; it now proves the case plain `git branch --merged` gets wrong.
- **False praise on screen:** the "Everything is clean." banner showed while 10 repos needed work (a CSS `display:flex` overrode `hidden`). Found only by looking at real data. Fixed, with a test in both directions.
- **Layout bugs only a real browser at real size showed:** group `<tbody>`s nested inside a `<tbody>` crushed the headings; long paths overflowed on a phone; times wrapped.
- **A scanner false alarm** on the real folder (one non-git folder at the depth limit) found by running it on real data before building on it.
- **The first full suite was slow** (the old one never finished in 5 minutes); this one took 102 s and then crept toward the approved 120 s limit, so I shared one browser and built the test repos once: 74 s.
- **Environment traps:** the package was installed in editable mode pointing at the main checkout, so tests and `serve.sh` in this worktree silently imported the old bonsai code. Fixed by pinning pytest and `serve.sh` to this checkout's `src/`.

## Manual interventions and decisions (all Jon's)
Approved the brief once, with four decisions settled in chat (Fetch included, scan root `~/dev/active`, deploy and auth code removed, saved islands dropped). Chose `--lan` with **no token** after being offered a secret link and Tailscale; I added private-network-only, Host allowlist, and loopback-only write and GitHub actions around that choice. Authorized the critique round and the automatic CI check.

## Deviations from the approved brief
The brief (r1) no longer describes what shipped. Jon directed four changes in chat after approval and none was re-approved as a new brief: the redesign (status pill and sentences became a status icon and chips; Working tree, Sync and the Changed and Sync-needed filters were removed), LAN access (the brief said localhost only), open PR and issue display, and the critique fixes (including automatic CI on load). `handoff.md` records each with its reasons; the brief itself was left as approved. A reviewer should read the handoff, not the brief, for what the tool does.

## tink-sdlc in practice
This repo's scaffold is still 1.18.4, so `status` kept printing the misleading "Next: implement the approved brief" while a real checklist item was incomplete, which 1.20.0 fixes. Approving the brief once and then changing the product four times in chat worked in practice but left the approved artifacts stale; nothing in the workflow prompted a brief r2. The gate that did earn its keep was the human attested item: it kept "Jon says it is simple" from being filled in by me.

## What made the next change harder or easier
Easier: real repos and a real browser in the tests made every behavior claim checkable, and reading screenshots at true size found four bugs no assertion would have. Harder: my tests mostly confirmed what I had just built; the independent reviewer and the mutation sweeps found what they missed. About 200 lines of dead PR and issue code in `github.py` remain from the old tool.

## Smallest justified next step
Merge, then open it on the phone and with real GitHub and report anything off. If the automatic lookups prove slow or noisy for him, `--no-auto-ci` is already the switch. Consider deleting the dead `get_github_info` code and its tests in a separate small PR, and upgrading this repo's scaffold to 1.20.0. No workflow change is justified by one run, but "a brief that is directed away from in chat should get a revision" is worth watching for a second occurrence.
