# Live merged-PR growth

The first pixel family now reads real project-wide merged PR totals. The local
candidate is http://127.0.0.1:7861/#/board, with a separate configuration containing
the real repo-root-tracker main checkout and this implementation worktree. The
existing port 7842 service was not changed.

The real GitHub check returned 21 merged PRs for jon-devlapaz/repo-root-tracker.
Both checkouts rendered the mature stage with the same count and timestamp.
The worktree remains physically smaller under the existing layout rules.
Desktop and mobile captures and the exact result are retained beside this file.

Collection uses Repository.pullRequests(states: MERGED).totalCount through a
read-only GraphQL query, pinned to github.com and the origin owner/name. It adds
one request per project cache refresh. It does not count a limited PR list.
Reference: https://docs.github.com/en/graphql/reference/pulls

Counts and their original timestamps survive refresh failures in the running
server/browser. Unknown never becomes zero. Remote changes select a different
project record. Old responses cannot overwrite a newer snapshot. The inspector
labels retained/expired values as last known. In-memory retention does not
survive restarting both server and browser while offline.

The initial full-suite run exposed a real pointer-hit regression in the raster
family, now fixed with explicit tree hit shapes and non-interactive image bounds.
The other failures were old mocks rejecting the new GraphQL query, fixed by
adding that read request to the mocks. Existing CI state assertions remain.
Call-count assertions increased by exactly one query per uncached refresh.
The focused rerun passed 121 tests, with one opt-in live test skipped. The
separate actual GitHub/browser capture passed.

The embed script reproduced the committed HTML byte for byte. The runtime stays
self-contained. Raster data adds about 2.9 MB to the HTML; performance and human
appearance approval remain required before release. Only the informal-upright
project family uses the new artwork; seven other styles retain their renderer.

Build the Lever supplied the repeatable embed and capture scripts. Prove It Works
required the actual GitHub-to-inspector check. Unslop guided labels and this note.
No release approval, merge, push or deployment to the main service is claimed.

## Final candidate verification

The full suite passed on the committed candidate: 639 passed, 3 opt-in skips,
in 378.15 seconds. The first attempt reached the previous 300-second runner
limit without failures; the runner allowance was raised to 600 seconds so the
suite could finish. No behavioral assertion or reference performance threshold
was relaxed. The three skips are the two explicit headed performance cases and
the opt-in authenticated live GitHub test. The real GitHub/browser capture above
was run separately against the candidate service.

The separate required browser regression check passed 102 tests in 74.67 seconds;
the merged-PR checklist check passed 12 tests in 1.39 seconds. The official SDLC
verification stopped at incomplete reference-performance and human-appearance
items, after the executable checks passed.

## Performance result

The current headed reference run failed both viewport cases. Desktop's longest
observed task was 54 ms against a 50 ms maximum. Mobile worktree promotion took
15.9 ms median against a limit below 10 ms; its p95 was 22 ms against 16.7 ms.
Desktop replay p95 was 24.8 ms against 16.7 ms. Cold paint samples were 274.7 to
337.9 ms, below the 1000 ms limit. The full raw log retains candidate, dashboard
hash, machine, browser, fixtures and all observations. Each case stopped on its
first failed assertion, so three repeated runs were not completed.

Earlier baseline and SVG candidates also failed reference timing gates. This
run does not establish whether the pixel change caused a regression. No release
or performance pass is claimed. The next release work is to address the timing
failures and obtain human appearance acceptance; the live candidate is available
for inspection in the meantime.
