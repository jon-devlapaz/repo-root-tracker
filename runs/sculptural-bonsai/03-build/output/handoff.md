# Build handoff

Implemented the approved brief in the isolated checkout. Code commits are `86e19c6` for the sculptural renderer, factual labels and retained review tools, then `641c951` for lower sampling on short branches. Trunks retain their original sampling. The final screenshot files show the exact final renderer.

Final configured verification ran all checks: 627 passed, 3 opt-in skips in 285.10 seconds, then 102 focused browser checks passed in 51.74 seconds. All 18 added rendered tests executed. The three skips are the two separately executed opt-in reference performance cases and the live GitHub profile. The generated SDLC receipt correctly remains failed for reference-performance and human-appearance.

Reference performance failed baseline and final candidate. A request-counter defect in the existing probe was repaired without changing any threshold or disabling background work; both sources used that corrected probe. Final desktop longest task is 54 ms, replay p95 is 22.5 ms, and promotion median is 14.5 ms. Mobile promotion median is 16.6 ms and p95 24.7 ms. See the full paired table and raw metadata in `04-test/output/review.md` and the performance logs. The repeated controlled diagnostic reduced SVG size 13.4% but does not replace the failed headed gate.

Human appearance acceptance is still pending. The real user's implementation approval is not approval of unseen final output. No approval, threshold waiver, merge, deployment, PR or stage-5 review was fabricated. The launcher can record an actual appearance response and address the failed performance requirement before reopening the remaining gates.

## Review files

- `04-test/output/review.md`: changes, matrix, limits, exact test/performance results and skill decisions.
- `04-test/output/candidate-final/specimens.png`: all eight shapes and three sizes.
- `04-test/output/candidate-final/quiet-1440.png`: final default composition.
- `04-test/output/candidate-final/attention-selected-0.png`: selected clean main with changed worktree and mixed project-wide GitHub conditions.
- `04-test/output/candidate-final/crowded-390.png`: dense narrow default.
- `04-test/output/provenance.json`: source and screenshot hashes.
- `04-test/output/test-log.md` and `verification.json`: actual final configured results and gate refusal.

## Preview and environment

The synthetic preview is still running at http://127.0.0.1:7856/#/board for the owner's review, unified exec session 30495. It reads this checkout's HTML and keeps fake organization changes in memory. Parent should stop that session when review ends. Port 7842 and real tracker data were untouched.

Task Python environment: `/tmp/sculptural-bonsai-venv`, with pytest 9.1.1 and Playwright 1.60.0. Scripts under `tests/` reproduce screenshots, synthetic preview, frozen-source performance and the bounded rendering diagnostic. The shared support environment was not modified.

Required/routed skills were read in full: build-the-lever, unslop, control-ui and prove-it-works. Initial unapproved mounts were resolved by the launcher; the build agent made no skill mutations. Compiled AGENTS state comes from the launcher.
