# Pixel bonsai family

The user chose pixel art, then said to proceed with one complete tree family
before extending the other seven shapes. This preview supplies an informal
upright tree for the synthetic cedar checkout and its linked worktree.
Production HTML and real repository data remain unchanged.

## Preview and checks

Run `python tests/serve_bonsai_review.py --port 7859 --pixel-tree`, then open
http://127.0.0.1:7859/?family=1#/board. The Pixel tree states button reopens
the gallery. Close it and select cedar to see the board and inspector.

Run `python tests/check_pixel_bonsai.py --output /tmp/pixel-bonsai-check`
with Playwright and Chromium installed. It checks 300 combinations, clean to
changed color transitions, retained history after an unavailable check, neutral
unknown history, desktop/mobile selection, and list/detail rendering. It saves
screenshots and machine-readable results.

## States

- Five foliage colors: gold, teal, mauve, indigo, olive.
- Four known age bands use the existing trunk-width factors.
- Three activity bands use the existing foliage-density factors.
- Zero through four extra limbs represent other live local branches, capped at four.
- Unknown history uses neutral growth. Failed checks retain prior growth.
- The gallery displays the same artwork at 48, 80 and 128 pixels wide.

The browser composes trunk, foliage and pot layers. A foliage-only SVG color
filter maps grayscale shading into the existing project palettes. Bark and pot
colors stay fixed. Additional limbs use small native paths and leaf sprites.
Git warnings and weather keep their existing code and meanings.

## Artwork and prompts

The built-in OpenAI imagegen tool generated `trunk.png`, `foliage.png`, and
`pot.png` on 2026-10-03. These files were copied unchanged into this directory.
`prompts.json` records the exact prompts and original output paths. `gold.png`
is the preserved earlier whole-tree reference, generated in the same chat.
The runtime colors and positions the layers; no offline image editing was used.

## Limits

This is one family in a synthetic preview. Seven other forms still need artwork
and placement. The 48px tree retains its silhouette, but fine bark and branch
changes are hard to distinguish at that size. It uses the same artwork at small
sizes rather than a separately drawn miniature. The gallery exposes that limit.

No production release, final appearance acceptance, full-suite pass for this
revision, or performance pass is claimed. Existing failed performance results
remain unresolved. The first-family user instruction authorizes this preview;
it does not record release approval or change old SDLC receipts.
