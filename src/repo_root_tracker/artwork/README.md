# First pixel family

The informal-upright family uses these generated trunk, foliage, and pot layers.
They are unchanged copies of the imagegen outputs documented in
`tests/fixtures/bonsai-pixel/prompts.json`.

Run `python3 scripts/embed_pixel_family.py` after changing pixel-family.js or an
asset. It updates marked sections of dashboard.html. The served dashboard remains
self-contained. The three PNGs add about 2.9 MB of embedded base64 to the page;
performance approval is still required before release.

A project whose main path selects the informal-upright style uses the pixel
family, including its worktrees. The other seven styles retain their renderer.
Merged PRs set tree scale: 0–5 at 40%, 6–20 at 70%, 21+ at 100%. Pots stay fixed;
existing worktree scaling still makes linked checkout trees smaller.

The GitHub response carries merged_pr_count, merged_pr_checked_at and
merged_pr_error. A count of zero is valid. Missing, invalid and failed counts
are never turned into zero. The server retains successful counts through failed
refreshes in its project cache, and the browser retains its last successful
record through transport failures. These caches are in memory; restarting both
while offline leaves history unknown. Changing remotes switches project identity.

The inspector displays the project total and original check time. Retained or
expired totals are labeled last known. This field is independent of CI and PR
blocker status and does not itself turn a checkout gold.
