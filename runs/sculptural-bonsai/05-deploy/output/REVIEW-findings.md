# Release review

The user requested "clean up and merge and get the repo to git golden please"
on 2026-10-03, immediately after receiving the completed preview and the explicit
notice that existing performance failures still blocked release. This is direct
merge authorization with that disclosed limitation. The failed performance
results remain recorded as failures; local SDLC verification is not represented
as passing. GitHub CI must pass on the final PR candidate before merging.

The preceding independent review found detached pixel stale branches. Commit
c94ffae fixes their geometry and scaling, with failing-before/passing-after
browser tests for every growth stage, board, worktree and inspector. It also
softens foliage highlights and improves mobile framing. No open demonstrated
functional defect remains from that review.

Reviewed the final backend count collection, cache and failure behavior,
frontend rendering, status ownership, test changes, and existing performance
evidence. Counts are read through a fixed-host GraphQL query with variables.
Successful counts are shared per project and retained through failures; unknown
history remains unknown. Existing PR/CI warnings and gold semantics are retained.
There is no new runtime dependency. Raster assets increase the embedded page size.
Only the first tree family uses merged-PR growth; the other families retain
history growth. Mixed artwork styles remain a visual limitation.

The final local code passed 644 tests with 3 skips, the required browser subset
passed 102, and growth checks passed 17. The skips include opt-in checks; they do
not establish performance. The latest main was merged without conflicts and
only added its stricter git-golden branch-cleanup rule. GitHub CI will verify
that exact integrated candidate.

Release remains subject to actual forge checks and merge outcome. The user's
merge request supersedes the local human-only merge instruction for this task;
this note does not manufacture an independent forge approval.
