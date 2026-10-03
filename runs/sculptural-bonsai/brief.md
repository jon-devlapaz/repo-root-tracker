# Current scope update: live merged-PR growth

On 2026-10-03 the user approved the six-step live-integration plan with "proceed"
in this chat. This update supersedes the older SVG-only and age-growth clauses
below for the first pixel family. It does not approve release.

- Fetch total merged PRs once per GitHub project per cache interval, sharing
  the count across its worktrees. Count merged PRs directly, without list caps.
- Use 0–5, 6–20, and 21+ for the first pixel family's 40%, 70%, and 100% sizes.
  Main and linked worktrees use their project's main-path family selection.
- Unknown counts remain unknown. Failed checks retain the last known count and
  check time in the running server/browser. Remote identity changes reset ownership.
- Show the total and check time in the inspector. Preserve local gold and Git
  warning semantics. Other seven tree styles remain as before in this slice.
- Embed existing raster layers into the single HTML runtime without adding a
  runtime dependency. Retain a repeatable embedding script and source assets.
- Verify collection, refresh/failure behavior, worktree ownership, browser views
  and performance. Demonstrate real data in an isolated local candidate before release.

The historical brief follows for context. Previous performance failures and
pending human appearance acceptance remain unresolved.

# Sculptural bonsai

**Draft for your acceptance.** This brief and `checklist.json` define the proposed work. Your “i love it” accepted the visual direction; the simulated interview supplies suggestions, not approval receipts.

## Problem and outcome

Make the garden feel more composed while keeping every repository and worktree easy to identify. Build stronger asymmetric trees with tapered, connected trunks, clear canopy gaps and matte pots. Quiet the gravel and ensō so factual names and conditions remain readable.

## Scope and approach

1. Capture the current renderer as the baseline. Build actual-board-size SVG comparisons for upright, leaning, sparse and cascading trees, including small worktree saplings. Preserve all eight existing styles, path identity and history-based growth; health changes must not reshape a tree. Review these specimens before extending the treatment across the board.
2. Refine the shared renderer in `src/repo_root_tracker/dashboard.html`: trunk/canopy connections, broad restrained shading and pot finish. Retain the single-file runtime, embedded fonts/licenses and current dark brand. Add no runtime dependency or raster tree asset. The concept image suggests form and material; its photographic detail is not a deliverable.
3. Quiet the ground and refine existing name/condition presentation. Use short factual wording with clear project versus checkout ownership and accessible full names. Keep names available through the existing controls and demonstrate the chosen default visibility. Preserve plot bounds, stable positions, inspector space and visible organization controls. Adjust decorative selection dimming only as needed to keep names and state markers readable.
4. Compare the whole board at 390, 768 and 1440 pixels wide, then verify list/detail shared sprites, existing interaction and performance. Retain reproducible fixtures, baseline/candidate screenshots and a concise review report.

Palette shades, label placement and texture are implementation choices to demonstrate to you. If text cannot fit current bounds, report the conflict for a decision before changing those bounds.

## Acceptance criteria

- Distinct upright, leaning, sparse and cascading silhouettes at their real display size. Sparse stays sparse; canopy masses visibly connect to trunks and retain open gaps. Other existing styles and history meanings remain intact.
- Gold retains the existing clean-checkout rule and stays distinct from orange changes, selected or unselected. GitHub unchecked, unavailable and blockers retain their existing meanings and non-color signals. A clean main checkout alongside a dirty worktree must identify whose condition is shown.
- Quiet, crowded (25 projects with worktrees) and attention-heavy boards remain readable. Long and duplicate names have reliable full-text identification. Refresh preserves plot positions and selected checkout when identities and history are unchanged.
- Keyboard, focus, touch, zoom/pan, worktree overflow, organization controls, reduced motion and increased contrast continue to work. Review the shared list/detail output too.
- Existing regression tests pass with browser coverage actually executed. New tests exercise the implemented label/status and shape-preservation behavior. Screenshots alone do not establish accessibility or performance.
- You review actual rendered specimens and board comparisons before adopting the appearance. Record your real response; neither the illustration nor an agent's review substitutes for it.

The detailed acceptance matrix and evidence requirements are in `checklist.json`.

## Verification and risks

Run existing focused browser tests and the full project suite before and after implementation. CI currently installs pytest 9.1.1 and Playwright 1.60.0 with Chromium; missing Playwright can silently skip browser tests. Record all failures and skips, including preexisting ones. No product tests have been run for this planning session.

Run the existing headed reference-performance procedure on the same quiet reference setup for baseline and candidate: `RRT_REFERENCE_PERF=1 PYTHONPATH=src python3 -m pytest tests/test_board_performance.py -q -s`. Retain its machine, browser and timing output. Its ordinary opt-in skips are not performance proof. Missing reference access or failures stay unresolved; do not claim a speed or accessibility improvement without measurements.

Likely risks are clutter from labels, loss of sparse/cascading character, dimmed status, and excess SVG cost. Preserve backend status rules, storage, repository actions, motion behavior and factory files. Report any proposed test assertion change with its visual reason; do not weaken behavior checks to obtain a pass.

## Delivery

After this definition is accepted, implement and verify in this isolated worktree, retain evidence, then obtain the SDLC independent release review. Present the actual appearance and remaining limitations to you. Only a human merges under the current project workflow. No implementation, verification or release is approved by this draft.
