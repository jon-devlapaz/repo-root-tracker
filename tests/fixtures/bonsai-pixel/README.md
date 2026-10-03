# Pixel bonsai preview

The latest proposal uses total merged PRs for three clearly different sizes.
This is a visual proof with sample data. Live GitHub totals are not connected.

- 0–5 merged PRs: seedling at 40% tree size.
- 6–20: growing tree at 70%.
- 21+: mature tree at 100%.
- Unknown: neutral 70% tree, labeled with a question mark, never treated as zero.

These thresholds are provisional. Size means merged work, not quality. Age,
activity, and branch count no longer change this preview family's geometry.
The pot stays fixed. Gold and the four project colors retain their existing
meaning. Cedar and its worktree both use the synthetic project total of 12.
Other trees and production HTML are unchanged.

## Run

`python tests/serve_bonsai_review.py --port 7860 --pixel-tree`

Open http://127.0.0.1:7860/?family=1#/board. The gallery compares sizes at
96px, 48px and 160px. Close it to try cedar in the board and inspector.

`python tests/check_pixel_bonsai.py --output /tmp/pr-growth-check`

Requires Playwright and Chromium. Checks cover count boundaries, invalid and
unknown counts, all five colors, actual rendered height differences, independence
from age/activity, count refresh without stale markup, desktop/mobile selection,
and list/detail rendering. Screenshots and checks.json are retained.

## Artwork

The built-in OpenAI imagegen tool generated trunk.png, foliage.png and pot.png.
The unchanged originals and exact prompts are recorded in prompts.json. gold.png
is the earlier whole-tree reference. The browser composes the layers and tints
only foliage. No new artwork or image-editing tool was needed for PR sizes.

## Remaining work

This first visual proof does not fetch live merged PR counts. Production needs
that collection, shared project totals, retained last-known growth on failed
checks, visible freshness, the other seven shapes, and performance verification.
No production release or appearance approval is claimed. Earlier 300-state
age/activity evidence remains historical and does not describe this proposal.
