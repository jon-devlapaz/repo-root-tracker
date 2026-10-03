# Sculptural bonsai review

Final code `641c951` passes 627 tests with three documented opt-in skips, plus all 102 focused browser checks. SDLC verification remains failed because reference performance fails and human appearance acceptance is pending. Nothing was merged or deployed.

## What changed

The renderer now draws solid tapered branches into asymmetric foliage masses. Broad light replaces white flecks and repeated stripes. Pots use warm matte colors and small feet. Sparse, cascading and twin-trunk forms retain their distinct plans. The same renderer still supplies board, list and detail trees.

The ensō opacity is one third of its previous value. Gravel relief is quieter. Selection no longer blurs and desaturates the other trees; their opacity is 0.82 instead of 0.5. Existing status colors and marker rules are unchanged.

Names remain off by default, as before. The visible Names control shows project names. A selected project's label adds factual ownership, for example `Main clean · 1 worktree changed`. The inspector labels local state as main checkout or linked worktree, separately from project-wide GitHub. Selecting a tree hides its redundant hover tooltip so it cannot cover the condition line.

No backend, storage, repository operation, font, runtime dependency, plot bounds, style selection or history-normalization rule changed.

## Actual appearance and limits

- `baseline/specimens.png` and `candidate-final/specimens.png` show all eight styles at detail, board and worktree sizes. The stronger trunks and solid branch junctions survive the smaller scale. Bunjin remains sparse; kengai retains its descending outer branch.
- The broad foliage shading is deliberately simplified. It does not reproduce the photographic study. At detail size some pads still look rather flat; this is a human taste decision, not a claimed realism result.
- Quiet boards preserve open ground. Gold remains clearly distinct from orange change markers. The gold main/dirty worktree case explicitly names the owner of each state.
- Crowded mobile boards are inherently dense at the existing fit zoom. Names-on can cover parts of trees and the existing placement drops labels that cannot fit. The default remains names-off, and selecting, focusing, searching or opening Worktrees identifies each checkout. No plot bounds were expanded and no controls were hidden.
- The selected label fits without label-label collisions in the rendered checks, including main/worktree selection in all nine matrix cells. Full project and checkout names remain available through the keyboard and touch inspector.
- Screenshots use reduced motion to make comparisons stable. Existing browser tests also exercise normal motion, reduced motion, increased contrast and forced colors. No general accessibility or speed improvement is claimed.

## Screenshot matrix

Each directory contains the same synthetic fixtures and viewport dimensions. Files ending in `-names` show the Names control enabled. The unsuffixed final files show the unchanged names-off default.

| Case | 390 × 844 | 768 × 900 | 1440 × 900 |
| --- | --- | --- | --- |
| Quiet, 4 projects with worktrees | `quiet-390.png` | `quiet-768.png` | `quiet-1440.png` |
| Crowded, 25 projects, 3 visible worktrees and overflow each | `crowded-390.png` | `crowded-768.png` | `crowded-1440.png` |
| Attention, mixed local/GitHub states | `attention-390.png` | `attention-768.png` | `attention-1440.png` |

Additional files cover selected clean main, selected changed worktree, increased contrast, all eight specimens, list and detail. Baseline and final detail screenshots were regenerated after adding the missing synthetic `/api/repo` response; the initial prototype detail capture showed a fixture error and is not shared-sprite evidence.

`prototype/` retains the bounded specimen experiment before board polish. `candidate/` retains the rejected permanent two-line label experiment and intermediate test failures. `candidate-final/` is the review target.

## Reproduce

Use Python 3.11+ with pytest 9.1.1 and Playwright 1.60.0 and its Chromium. This session uses a separate `/tmp/sculptural-bonsai-venv`, without changing another task's installation.

```sh
PYTHONPATH=src python3 -m pytest tests/test_bonsai_design_review.py -q -ra
PYTHONPATH=src python3 -m pytest tests/ -q -ra
python3 tests/bonsai_review.py --output /tmp/bonsai-candidate
python3 tests/bonsai_review.py --dashboard runs/sculptural-bonsai/04-test/output/baseline/dashboard-source.html --output /tmp/bonsai-baseline
python3 tests/serve_bonsai_review.py --port 7856 --case quiet
RRT_REFERENCE_PERF=1 PYTHONPATH=src python3 tests/bonsai_performance_review.py --dashboard runs/sculptural-bonsai/04-test/output/baseline/dashboard-source.html
RRT_REFERENCE_PERF=1 PYTHONPATH=src python3 -m pytest tests/test_board_performance.py -q -s
```

All fixture requests stay inside Playwright or the disposable preview server. The preview server stores organization changes only in memory. The live tracker on port 7842 and real repository data were not used or changed.

## Verification results

Baseline full suite: 609 passed, 3 skipped in 262.47 seconds. The skips are two opt-in reference-performance cases and one opt-in live-GitHub profile. Playwright tests executed. The live-GitHub profile remains outside the synthetic visual review.

The first focused candidate run passed 114 checks and failed one new test's premature list assertion. A subsequent run exposed the missing synthetic detail API. Both fixture issues were corrected; product assertions were not weakened. The final tooltip regression and new rendered tests passed before the broader run.

Final full-suite and performance results are recorded below after completion.

## Performance measurement correction

The original headed baseline failed at the refresh-count assertion, counting 1394 desktop and 720 mobile requests instead of 360. `board_performance.js` counted every local-status request throughout the sample, including `livePoll`, which runs every 15 seconds. The original raw log is retained as `baseline/performance.log`.

The corrected probe waits for an idle local queue before starting, counts the explicit board batch only while that batch owns `refreshingBoard`, and separately reports `backgroundRequests`. Polling stays enabled and all work/paint/long-task measurements still include its work. All numeric limits and assertions in `test_board_performance.py` remain unchanged. Both frozen baseline HTML and candidate use this same corrected probe. The host was shared with other work, so a quiet reference-machine condition cannot be certified.

## Review gates

The owner must review actual rendered output. No agent appearance judgment or screenshot creation substitutes for that response. Independent release review, merge and deployment are not performed by this build session.

## Skills used

- `principle-build-the-lever` led to the retained fixture/capture runner, disposable preview server and rendered acceptance tests.
- `control-ui` led to reuse of the repository's Playwright request fixtures, real pointer/keyboard/touch actions and retained screenshots.
- `principle-prove-it-works` required inspection of actual SVG output and failed results, including the incomplete performance gate.
- `unslop` guided the factual labels and this report.

The initially unavailable control-ui and principle-prove-it-works payloads were read successfully after the launcher approved/fetched them. This session made no skill-state changes.

## Test assertion change

`test_selected_plot_shows_name_without_toggle` previously required the entire label to equal `dirty`. It now requires the title span to equal `dirty` and the new factual line to equal `Checkout local changes`. This preserves the exact name check while covering the approved second line. The first full candidate run retained 622 passes, one old-label assertion failure, and the same three opt-in skips. It also revealed that unconfirmed standalone identity must say Checkout, not Main. Four added rendered cases now distinguish standalone checkout, confirmed untracked main, unidentified main, and unavailable identity.

## Corrected baseline performance

Both viewports still fail the existing timing limits with the request-count error corrected. Each explicit refresh now has exactly 360 requests and peak concurrency 3. Background polling remains visible as 1080 desktop and 360 mobile requests. Desktop longest task is 52 ms and mobile 54 ms against the 50 ms limit. Desktop promotion median is 11.3 ms and mobile promotion median 11.3 ms, above the 10 ms limit. Several desktop paint p95 values also exceed 50 ms. The original and corrected baseline logs are retained separately.

## First candidate performance results

Both corrected runs failed both viewports. Each stopped after its first failing sample, so the required three successful samples were not completed. Cold paint and explicit 360-request/peak-3 checks passed. The table lists every timing metric that failed in either observed run. Values are rounded for display; strict assertions use the raw values.

| Metric, ms | Limit | Baseline desktop | Candidate desktop | Baseline mobile | Candidate mobile |
| --- | --- | --- | --- | --- | --- |
| Longest task | ≤ 50 | 52 FAIL | 54 FAIL | 54 FAIL | 0 |
| pan work median | < 10 | 10.20 FAIL | 7.40 | 6.40 | 6.10 |
| pan paint p95 | ≤ 50 | 57.70 FAIL | 26.70 | 26.90 | 19.60 |
| zoom paint p95 | ≤ 50 | 65.20 FAIL | 32.50 | 31.70 | 17.60 |
| replay work p95 | < 16.7 | 14.30 | 19.00 FAIL | 14.60 | 14.00 |
| replay paint p95 | ≤ 50 | 57.70 FAIL | 35.90 | 34.00 | 25.10 |
| promotion work median | < 10 | 11.30 FAIL | 13.80 FAIL | 11.30 FAIL | 17.20 FAIL |
| promotion work p95 | < 16.7 | 16.50 | 17.50 FAIL | 17.60 FAIL | 34.20 FAIL |
| promotion paint p95 | ≤ 50 | 52.90 FAIL | 32.30 | 33.50 | 44.20 |
| refreshGroundOverlap work median | < 10 | 10.80 FAIL | 7.60 | 6.60 | 6.20 |
| refreshGroundOverlap work p95 | < 16.7 | 16.70 FAIL | 14.10 | 11.10 | 10.20 |
| refreshGroundOverlap paint p95 | ≤ 50 | 60.30 FAIL | 27.10 | 27.30 | 19.70 |

Candidate desktop replay and mobile promotion are worse in these observations; desktop paint latency is lower. One sample on a shared host does not distinguish repeatable regressions from scheduling noise, so neither a speed improvement nor a regression-free result is claimed. These failures remain an adoption gate. No timing threshold was relaxed, no poll disabled, and no broader optimization was attempted.

The baseline HTML hash is bound to product revision `a41a4a1f3bd2cc1472ac3a4afd0a3fb4ff653a5f`; the corrected probe and candidate are from `86e19c6392d93027001c48429e603492c6697b4d`. The baseline runner's reported Git HEAD is the runner checkout, not the baseline product revision; its separate dashboard SHA-256 identifies the actual frozen input.

## Bounded renderer-cost check

The first candidate used 24 samples for each short branch, the same as a full trunk. A repeated controlled diagnostic compared 25 synthetic projects with Names on, discarding one warm round and measuring five rounds of 25 promotions in each of three fresh browser contexts.

| Renderer | SVG text for 125 trees | Promotion medians, ms | Promotion p95, ms |
| --- | --- | --- | --- |
| Frozen baseline | 1,124,323 bytes | 5.9 / 6.1 / 5.9 | 7.1 / 7.4 / 7.2 |
| First candidate | 1,855,296 bytes | 6.0 / 6.0 / 6.0 | 7.0 / 6.8 / 6.7 |
| Final, short branches at 8 samples | 1,607,022 bytes | 5.8 / 5.7 / 5.8 | 7.0 / 6.7 / 6.8 |

The change removes 13.4% of the candidate SVG text. Trunks remain at 24 samples, and the same curved branch endpoints and tapered form remain. Regenerated specimens were inspected at all three sizes. The small timing differences do not establish a speed improvement; this diagnostic did not reproduce a consistent warm-promotion regression. It is not the headed reference-performance gate. The final code commit is `641c951`; original candidate code is `86e19c6`.

Reproduce with `python3 tests/bonsai_render_benchmark.py --dashboard FILE`. The retained baseline, pre-sampling candidate and final files can each be supplied. Raw rounds are in `baseline/render-benchmark.json`, `candidate/render-benchmark-before.json`, and `candidate/render-benchmark-after.json`.

## Final performance results

Final `641c951` fails both viewports in 49.33 seconds. The explicit refresh count remains 360 with peak 3. This table supersedes the first-candidate table for adoption decisions.

| Metric, ms | Limit | Baseline desktop | Final desktop | Baseline mobile | Final mobile |
| --- | --- | --- | --- | --- | --- |
| Longest task | ≤ 50 | 52 FAIL | 54 FAIL | 54 FAIL | 0 |
| pan work median | < 10 | 10.20 FAIL | 7.10 | 6.40 | 6.40 |
| pan paint p95 | ≤ 50 | 57.70 FAIL | 27.80 | 26.90 | 19.30 |
| zoom paint p95 | ≤ 50 | 65.20 FAIL | 31.20 | 31.70 | 18.40 |
| replay work p95 | < 16.7 | 14.30 | 22.50 FAIL | 14.60 | 10.90 |
| replay paint p95 | ≤ 50 | 57.70 FAIL | 36.50 | 34.00 | 25.00 |
| promotion work median | < 10 | 11.30 FAIL | 14.50 FAIL | 11.30 FAIL | 16.60 FAIL |
| promotion work p95 | < 16.7 | 16.50 | 16.50 | 17.60 FAIL | 24.70 FAIL |
| promotion paint p95 | ≤ 50 | 52.90 FAIL | 33.30 | 33.50 | 34.00 |
| refreshGroundOverlap work median | < 10 | 10.80 FAIL | 7.30 | 6.60 | 6.50 |
| refreshGroundOverlap work p95 | < 16.7 | 16.70 FAIL | 14.20 | 11.10 | 11.30 |
| refreshGroundOverlap paint p95 | ≤ 50 | 60.30 FAIL | 28.30 | 27.30 | 21.00 |

The final performance mark remains failed. The full three-successful-sample procedure is incomplete because each viewport stops on its first failed sample.

## Final configured verification

The required `sdlc.py verify sculptural-bonsai` ran against committed `641c951` with the task venv on PATH. Installation passed. The full suite passed 627 tests with three opt-in skips in 285.10 seconds; all 18 new tests executed. The focused browser checklist check passed 102 tests in 51.74 seconds. No browser dependency skips occurred and no timeout was changed.

The generated receipt correctly says failed: `Checklist incomplete: reference-performance, human-appearance`. The implementation is ready for the owner's review, but adoption and stage-5 release review remain gated. `test-log.md`, `verification.json`, and `verify-command.log` retain the exact final outputs. Earlier failing or superseded measurements remain separately named.
