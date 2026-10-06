# Product

## Purpose
A single developer keeps many git repositories under a folder and wants one answer: which of them are not git-golden?
repo-root-tracker scans a folder, shows every checkout in a table, and says why each one that is not golden is not.

## Users
One developer, on their own machine, on localhost. No accounts and no remote hosting. An opt-in `--lan` mode lets their phone
on the same private network look (read-only, no password); it is off by default.

## Principles
1. **It just works.** Opening it needs no setup, no registration and no configuration. It finds the repos.
2. **Status first.** The verdict is words, not decoration. Color is a second cue and never the only one.
3. **Honest about what it knows.** Remote branches and "even with origin" are only as fresh as the last fetch, and
   each row says when that was. CI that cannot be judged is `golden pending CI`, never golden. A scan that hit a cap
   says so.
4. **Read-only, with two explicit exceptions.** It never changes a working tree or commit. Git is run without optional
   locks so reading status does not rewrite the index. The exceptions are the **Fetch all** button, which updates
   remote-tracking refs only, and a per-branch **Delete** button for branches the server proves merged (or whose pull
   request was closed unmerged). Deleting is confirmed in a dialog, re-checked by the server, logged before it
   happens, loopback-only, and never offered in bulk.
5. **Local and self-contained.** Standard library only, one small page, no build step, no external requests.

## Scope
In: scan folders, one row per checkout, golden verdict with reasons, search, filters, sort, on-demand GitHub CI,
explicit fetch, copy path.
Out: registering repos by hand, saved groupings, history or replay, diffs and commit views, editor links, accounts,
remote hosting, and anything that edits a repository.

## Success
Opening the page shows every repo within seconds and answers "which repos are not golden, and why?" without a click.
