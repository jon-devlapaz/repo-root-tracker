# Pixel tree trial

The user chose B, pixel art, after comparing two illustrated directions. This
trial puts one generated tree into the actual dashboard using synthetic data.
It replaces the clean cedar sample only. Other states use the existing renderer.

Run `python tests/serve_bonsai_review.py --port 7857 --pixel-tree`, then open
http://127.0.0.1:7857/#/board. Click cedar to inspect it.

Run `python tests/check_pixel_bonsai.py --output /tmp/pixel-bonsai-check`
with Playwright and Chromium installed to repeat the desktop/mobile captures,
selection check, and dirty-state fallback check.

## Artwork

`gold.png` was generated with OpenAI imagegen on 2026-10-03. The source output is
`exec-eb417b7c-6b2a-49a3-b970-634b220b92ba.png`; the reference comparison is
`exec-163fc406-8110-4420-ab9d-6fa48bb983ee.png`. Both originals remain in the
chat's generated_images folder. The PNG is copied unchanged.

The prompt requested a transparent gold bonsai matching the right-hand B
reference, with an S-curved trunk, separate asymmetric leaf clusters, square
pixel highlights, brown bark, a charcoal bowl with feet, and olive moss. It
excluded text, background, platform, particles, shadows outside the pot, and
status icons. The intended display width was 96–128 pixels.

## Remaining work

This is an artwork trial, not the finished renderer. The single image cannot
express eight forms, changing branch counts, age, or foliage density. The full
set needs those variations and the project colors. At small mobile sizes the
fine detail becomes texture; larger pixel clusters may read better.

The user chose the pixel direction, superseding the earlier SVG-only visual
proposal for this trial. No final appearance approval or performance pass is
claimed. Existing failed performance results still apply. Production HTML is
unchanged, and no runtime library was added.
