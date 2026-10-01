---
name: repo-root-tracker
description: A night garden in sumi where every git repo is a seeded bonsai and git state is weather.
colors:
  sumi-ground: "#0a0f0e"
  surface: "#111816"
  surface-raised: "#182220"
  hairline: "#27332f"
  control-line: "#6d8479"
  matcha: "#b9d891"
  matcha-deep: "#2d4a37"
  matcha-hover: "#3a5d46"
  on-matcha: "#f5f8ef"
  paper-text: "#edf1e7"
  body-ink: "#c3cdc2"
  muted-moss: "#8fa298"
  vermilion-seal: "#b23a2a"
  vermilion-text: "#ffb4a8"
  vermilion-line: "#e8705c"
  amber-leaf: "#e6b85c"
  amber-fill: "#785c28"
  gold-clean: "#f2dc7a"
  gold-fill: "#6b5a1e"
  orange-changes: "#f29a4e"
  orange-fill: "#8a4a1a"
  lilac-stale: "#b9a2e6"
  lilac-fill: "#4d3f78"
  slate-unavailable: "#8d9a94"
  slate-fill: "#3b4642"
  sync-blue: "#8fbfe0"
  sync-fill: "#2f5672"
  dormant-moss: "#71876a"
  muted-contrast: "#c4d2ca"
  body-contrast: "#e2e9df"
  border-contrast: "#6a7f75"
  control-contrast: "#9fb4aa"
  sky-moon: "#dfe9d2"
  sky-dawn-dusk: "#f4b080"
  clean-green: "#9bd3a5"
  merge-purple: "#c5b1de"
  celadon: "#a0d8cf"
typography:
  display-xl:
    fontFamily: "'Hiragino Mincho ProN', 'Hiragino Mincho Pro', 'Yu Mincho', YuMincho, 'Shippori Mincho Embedded', 'Noto Serif JP', Georgia, serif"
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 1.12
    letterSpacing: "0.02em"
  headline:
    fontFamily: "'Hiragino Mincho ProN', 'Hiragino Mincho Pro', 'Yu Mincho', YuMincho, 'Shippori Mincho Embedded', 'Noto Serif JP', Georgia, serif"
    fontSize: "26px"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "0.015em"
  title:
    fontFamily: "'Hiragino Mincho ProN', 'Hiragino Mincho Pro', 'Yu Mincho', YuMincho, 'Shippori Mincho Embedded', 'Noto Serif JP', Georgia, serif"
    fontSize: "22px"
    fontWeight: 400
    letterSpacing: "0.02em"
  subtitle:
    fontFamily: "'Hiragino Mincho ProN', 'Hiragino Mincho Pro', 'Yu Mincho', YuMincho, 'Shippori Mincho Embedded', 'Noto Serif JP', Georgia, serif"
    fontSize: "18px"
    fontWeight: 400
    letterSpacing: "0.015em"
  body:
    fontFamily: "'Avenir Next', Avenir, 'Hiragino Sans', 'Segoe UI', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "'Avenir Next', Avenir, 'Hiragino Sans', 'Segoe UI', system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    letterSpacing: "0.04em"
  caption:
    fontFamily: "'Avenir Next', Avenir, 'Hiragino Sans', 'Segoe UI', system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 400
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  control: "3px"
  panel: "4px"
  row: "6px"
  pill: "20px"
spacing:
  space-1: "4px"
  space-2: "8px"
  space-3: "12px"
  space-4: "16px"
  space-6: "24px"
components:
  button-primary:
    backgroundColor: "{colors.matcha-deep}"
    textColor: "{colors.on-matcha}"
    rounded: "{rounded.control}"
    padding: "8px 20px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.matcha-hover}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.body-ink}"
    typography: "{typography.label}"
    padding: "6px 12px"
    height: "38px"
  button-ghost-hover:
    textColor: "{colors.paper-text}"
  input-underline:
    backgroundColor: "transparent"
    textColor: "{colors.paper-text}"
    rounded: "0"
    padding: "8px 2px"
    height: "40px"
  panel-raised:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.paper-text}"
    rounded: "{rounded.panel}"
    padding: "14px"
  repo-row:
    textColor: "{colors.body-ink}"
    rounded: "{rounded.row}"
    padding: "8px 10px 8px 6px"
---

# Design System: repo-root-tracker

## Overview

**Creative North Star: "The Night Garden"**

Emptiness (ma, yohaku) is the main material. The ground is ink-black green with fixed mist and paper grain, and almost nothing sits on it in a box. Every repo is a bonsai whose form is seeded by its path, and its git state shows as weather around it, never as chrome. Matcha is new growth and the single live accent; vermilion is rare enough to read as a seal.

Density is low and typographic, and the garden carries a little history: a tree's trunk, canopy and limbs reflect the repo's age, recent activity and live branches, and the ground under it is lit by the real time of day. Rows are sparse, controls are quiet text with hairline underlines, and a mincho display face carries names and headings against a calm gothic text face. The list is an 820px column (880px in detail); the board is a borderless stage that fades into the void, with a single margin-note inspector at the right.

The build refuses card grids, boxed panels, colored edge stripes and dashboard gray. State is legible through the trees and a small set of semantic hues, and expression never replaces the label.

**Key Characteristics:**
- Dark-only (`color-scheme: dark`); one accent, matcha.
- Hairlines and tonal ground, no boxes at rest.
- Mincho display, gothic text, mono for paths and hashes.
- One ornament: the tapered brush-stroke underline.
- Git state encoded as weather outside the seeded tree geometry; history encoded as bounded vitals inside it.
- Single-file constraint: the whole UI is one `dashboard.html` (inline CSS, JS, the embedded font and SVG/canvas drawing) because the server and tests load that one file. This is deliberate; do not split it.

## Colors

A sumi-ink ground with moss-grey text, one matcha accent, and six state hues (gold, orange, lilac, slate, blue, vermilion) that each own exactly one git state.

### Primary
- **Matcha** (`{colors.matcha}`): new growth and the one live accent. Links, focus rings, active tab/filter text, branch names, selection, caret, checkbox accent. Pinned by tests together with the dark scheme.
- **Deep Matcha** (`{colors.matcha-deep}`) and **Matcha Hover** (`{colors.matcha-hover}`): the only filled button, selection background, active palette row. Text on them is `{colors.on-matcha}`.

### Secondary
- **Vermilion Seal** (`{colors.vermilion-seal}`, CSS `--danger-fill`): blockers and conflicts only. It fills the carved hanko seal on a tree. **Vermilion Line** (`{colors.vermilion-line}`) draws the kintsugi crack, diff deletions and failing CI; **Vermilion Text** (`{colors.vermilion-text}`) is the readable text tint for errors and GitHub blocker signals.
- **Gold** (`{colors.gold-clean}`): clean. One still glint on the tree, the disc fill `{colors.gold-fill}`, the "all calm" island title and the dirty-to-clean bloom. A clean tree has no status ring. Gold motion is reserved for the bloom.
- **Orange** (`{colors.orange-changes}`): local changes. Falling and fallen leaves, board legend, changed ring and filter count; also list and detail views (changed repo label, warning notes, tab count pill, unstaged badge, "N changed" meta). Disc fill `{colors.orange-fill}`.
- **Lilac** (`{colors.lilac-stale}`): stale branches. Jin dead-wood strokes and a dotted ring; also the stale repo label and stale branch rows in list and detail. Disc fill `{colors.lilac-fill}`.
- **Slate** (`{colors.slate-unavailable}`): unavailable data. Dashed ring; also the unavailable repo label. Disc fill `{colors.slate-fill}`.
- **Sync Blue** (`{colors.sync-blue}`): ahead/behind sync (motes). `{colors.sync-fill}` is its filled form.
- **Amber Leaf** (`{colors.amber-leaf}`, CSS `--yellow`, fill `{colors.amber-fill}` as `--warning-fill`): no longer a state hue. It survives only for the pending-CI badge and the family-level GitHub "checking/incomplete" disc fill.
- **Unchecked** has no hue: the numbered disc is hollow (transparent, 1px `#5d6863` stroke, 55% text).

### Tertiary
- **Clean Green** (`{colors.clean-green}`): diff additions, passing CI, current branch (not the clean state; that is gold).
- **Merge Purple** (`{colors.merge-purple}`, CSS `--purple`) and **Celadon** (`{colors.celadon}`): merge commits, remote tags, and commit-graph lane colors (lanes also use matcha and three muted tones).

### Neutral
- **Sumi Ground** (`{colors.sumi-ground}`): page and header fade; carries a top mist gradient and fixed paper grain at 7% opacity.
- **Surface** (`{colors.surface}`) and **Raised Surface** (`{colors.surface-raised}`): menus, dialogs, palette, toasts. Rows have no resting surface.
- **Hairline** (`{colors.hairline}`): dividers and panel edges. **Control Line** (`{colors.control-line}`): the underline of inputs and selects.
- **Paper Text** (`{colors.paper-text}`), **Body Ink** (`{colors.body-ink}`), **Muted Moss** (`{colors.muted-moss}`): headings, body, secondary.
- **Dormant Moss** (`{colors.dormant-moss}`): moss patches on the gravel at the base of a dormant tree (`.moss`, 75% opacity). Hard-coded in CSS, not a custom property.
- **Sky Moon** (`{colors.sky-moon}`) and **Sky Dawn/Dusk** (`{colors.sky-dawn-dusk}`): the sun/moon disc fill (night moon; dawn and dusk peach; day uses Gold). Hard-coded in CSS.
- **High-contrast overrides** (`prefers-contrast: more`): muted becomes `{colors.muted-contrast}`, body `{colors.body-contrast}`, hairline `{colors.border-contrast}`, control line `{colors.control-contrast}`; paper grain and the ensō drop to 3% opacity. Under `forced-colors: active` buttons get a ButtonText border, active tabs/toggles/filters are underlined at 2px, the glow pool and bloom are hidden, and the board stage opts out of forced colors so the garden keeps its own hues.
- Tree foliage ships four family palettes (matcha-green, plum, indigo, teal), each with dark/mid/high/fleck plus gravel and stone tones, plus fixed wood, dead-wood and four glaze pot colors. These live in JS, not CSS tokens. The gravel tone is mixed toward the time-of-day tint on the canvas ground.
- **Matcha glow** (`--glow`, gradient `#board-glow`, `#b9d891` at 70/22/0%): the replay pool under tiles touched that day.

### Named Rules
**The Seal Rule.** Vermilion fill means a blocker or conflict and nothing else, whether the carved hanko seal on the board or the list badge. Never use it for decoration or emphasis.
**The One Meaning Rule.** Gold is clean, orange is local changes, lilac is stale, slate is unavailable, blue is ahead/behind, vermilion is blocked, matcha is growth and focus. Each state owns one hue and each hue one state; amber is no longer a state colour, and the same hues apply in list and detail views as on the board.
**The Redundant Signal Rule.** Hue never works alone. Severity also changes ring weight and pattern, and the text label always stays (see Bonsai weather).

## Typography

**Display Font:** Hiragino Mincho ProN (with Hiragino Mincho Pro, Yu Mincho, the embedded Shippori Mincho, Noto Serif JP, Georgia, serif)
**Body Font:** Avenir Next (with Avenir, Hiragino Sans, Segoe UI, system-ui, sans-serif)
**Label/Mono Font:** ui-monospace stack (SF Mono, Menlo, Consolas) for paths, hashes, branches, diffs

**Character:** A quiet gothic carries data; a literary mincho carries names, headings and the search field. Shippori Mincho is embedded as `'Shippori Mincho Embedded'` (400, Latin subset, WOFF as a data URI, `font-display: swap`) and sits after Hiragino and Yu Mincho, so machines without either still get a true mincho before Noto Serif JP or Georgia. It is licensed under the SIL Open Font License 1.1 (Copyright 2021 The Shippori Mincho Project Authors, github.com/fontdasu/ShipporiMincho); the notice stays in the stylesheet comment and must travel with the font. The Latin-only subset means Japanese glyphs (the header 間) still depend on system fonts. The text stack is macOS-oriented: off macOS it falls back to Segoe UI or system-ui, so metrics shift slightly.

### Hierarchy
- **Display** (400, `clamp(30px, 4.2vw, 44px)`, 1.12, +0.02em): view titles (list overview, board island name). 26px under 650px.
- **Headline** (400, `clamp(22px, 3vw, 26px)` in detail, 26px in the inspector, 1.3): repo name in detail header and inspector.
- **Title** (400, 22px, +0.02em): collection headings, dialog titles, palette input.
- **Subtitle** (400, 18px): repo names in rows, section titles, search field, empty-state lines.
- **Body** (400, 14px, 1.6): controls, tabs, commit subjects. Tabular numerals are on globally.
- **Label** (400, 12px, +0.04em): metadata, notes, counts, hints. Notes cap near 62ch.
- **Caption** (400, 11px): hashes, relative times, file badges (uppercase, +0.1em), kbd.

### Named Rules
**The Mincho Names Rule.** Names of things (repos, collections, islands) and headings use the display face; data, controls and paths use text or mono.
**The Seven Sizes Rule.** The scale is 11 / 12 / 14 / 18 / 22 / 26 / 44. Do not add intermediate sizes (the board's 9px disc numerals and 10px leaf legend glyphs are SVG one-offs).

## Layout

Single centered column: `main` is 820px max (detail view 880px) with a fluid gutter of `clamp(20px, 5vw, 56px)` and generous top air (overview margin 44px). Spacing steps are 4, 8, 12, 16, 24; sections separate by 30-56px of empty space rather than rules. Rows lead with a 58px bonsai glyph (58x69 svg), then name, path, meta; on mobile the menu sits on the name line; detail headers lead with a 132x158 bonsai.

The board is a two-column workspace: a fluid stage (height `clamp(360px, 65vh, 620px)`, edges masked to fade into the void) and a 272px inspector set off by one hairline on its left. Under 850px the inspector is hidden; under 650px the header becomes a grid, titles drop to 26px and the stage shortens to `clamp(300px, 46vh, 440px)`. Board geometry is isometric 2:1 with a 156x78 grid pitch, 36px depth, and a fixed 128x148 sprite box per tile (only the hover diamond follows the pitch). On narrow screens (650px) the camera fits to 96% of the stage width with a 0.56 zoom floor, centred (wider scene margin), and the stage height is set to the island (280-480px) so there are no empty bands. Label layout is idempotent: a resize that changes nothing does not rebuild labels. The board caption reads "Select a tree..." on touch (hover:none) devices instead of "Hover or select...". In list rows, freshness and unknown-GitHub signals are hidden until hover or focus on hover-capable devices.

The garden brief (`#list-brief` under the list title, `#board-brief` under the board title) is one 14px body-ink sentence summarising git state ("2 uncommitted · 1 stale", "All N repos are calm."). It reserves a single line (min-height 1.6em, no wrap, ellipsis, max 92ch, full text in the title attribute) so the layout never jumps; on phones (650px) it may wrap to two lines (min-height 3.2em). The archipelago strip (`.isle`, `#board-archipelago`) lists islands as mincho 14px text buttons with a repo count and `.isle-dot` state counts (7px tone dot plus 11px count; unavailable is a dashed ring); the current island is matcha with a brush underline; touch targets grow to 44px under 850px.

Semantic zoom sets `data-lod` on the board world from camera zoom: far (under 0.5) enlarges status rings (3px) and scales discs 1.55x and hides glint and moss; mid is the default; near (1.6 and up) shows all plot names automatically, as the Names toggle does. Zoom is 0.35 to 1.5 at fit time with a +/- control and percentage readout.

Keyboard: arrow keys walk between board tiles (nearest in the pressed direction), Escape clears selection, Left/Right/Home/End move between detail tabs. The command palette adds verbs (Board view, List view, and with a repo in focus Copy path of / Open in VS Code) ahead of fuzzy path matches. The board stage carries an aria label "Island garden." plus a spoken summary of each island, and the stage group is named "Repository board".

## Elevation & Depth

Flat by default and tonal, not shadowed. Depth comes from the mist and grain on the ground, hairline borders, recession (when a tile is selected the rest drop to 50% opacity with 0.7px blur and 0.4 saturation) and the canvas-painted raked-gravel bed (see Raked-gravel ground). Shadows exist only on things that lie over the garden; the garden's own cast shadows are painted into the ground and point away from the light.

### Shadow Vocabulary
- **Lifted slip** (`box-shadow: 0 6px 12px -4px #000`): menu panel, dialog, command palette.
- **Sheet rising** (`box-shadow: 0 -4px 12px #0008`): the narrow-screen board inspector sheet.
- Backdrops are `#050807cc` to `#050807d0` washes. Tree shadows under pots and stones are `#000` ellipses at 26-35% opacity; the ground canvas adds a blurred (2.4px) 36% cast shadow whose length follows the light height.

### Named Rules
**The Flat-At-Rest Rule.** Rows, tiles and controls carry no shadow or box at rest; hover is a faint matcha wash (5-6%) or a color shift.

## Shapes

Small, quiet radii: 3px controls (replacing the earlier 2px), 4px panels, 6px rows, a 20px attention pill. Inputs and filters have none (underline only). Circles are reserved for avatars, CI badges, branch dots and numbered discs. Marks on the board (pinned star, no-upstream wavy line, selection strip, disclosure chevron in the attention panel) are drawn paths, not glyphs. Silhouettes belong to the trees: seeded ink-brush bonsai in eight styles (chokkan, moyogi, shakan, bunjin, hokidachi, sokan, kengai cascade, fukinagashi windswept) chosen from a hash of the repo path, with four pot glazes and four family foliage palettes. Hanko seals use a separate `#hanko-edge` filter (displacement plus a pitted alpha mask) and a -5deg rotation so the edge looks carved. A canopy ink filter (turbulence displacement plus a 45% blurred halo for a wet edge, on a fixed userSpaceOnUse region) roughens the edges. Tree geometry is deterministic per path and history; only weather animates. Vitals bend the form within bounds (see Vitals).

## Components

### Buttons
- **Shape:** 3px radius, 40px min height.
- **Primary:** Deep Matcha fill, matcha 42% border, on-matcha text, 14px/500, +0.04em, padding 8px 20px. Hover moves to Matcha Hover (0.25s ease). Disabled is 45% opacity.
- **Ghost:** no fill or border, body ink 12px; hover raises text to paper and draws the brush underline. `btn-danger` hover turns text vermilion.
- **Focus:** 1.5px matcha outline, 4px offset, on every focusable element.

### Filters, tabs, view toggles
- Plain text, muted. Active state is matcha (filters) or paper (tabs) plus the brush-stroke underline. Counts are tabular at 80% opacity.

### Inputs / Fields
- Transparent with a 1px Control Line bottom border and 40px height; focus swaps to a matcha border plus matching 1px bottom glow. The list search uses the display face at 18px; the add-repo path field uses mono. Placeholders are muted moss.

### Repo rows
- No box. 6px radius with a left-to-right matcha 6% wash on hover. Bonsai glyph, 18px mincho name, mono path (home segment muted), 12px meta (branch in mono matcha), signals aligned right. Pin and menu icons are muted until row hover.

### Menus, dialogs, palette
- Raised Surface, 1px hairline, 4px radius, Lifted slip shadow. Palette: 22px mincho input, mono 14px items, active item Deep Matcha.

### Bonsai weather (signature)
Weather is drawn outside the seeded tree geometry and encodes state; a status ring under the pot repeats it by weight and pattern:
- **Clean:** one still gold glint (no loop), gold disc, no ring. Going dirty-to-clean fires a gold bloom (two expanding ellipses, 2.6s, removed after 3s) and an "all calm" toast; a fully clean island title turns gold.
- **Local changes:** 4-10 orange leaves fall, with a few lying at the base (count scales with changed files).
- **Ahead / behind:** up to 4 pale-blue motes drift up (ahead) or down (behind). Ring 1.2px.
- **Stale branches:** lilac jin (dead wood) on the trunk; dotted ring (1.4px, dash 1 5, round caps).
- **Unavailable:** dashed ring (dash 3 4, 1.6px).
- **Blocked / conflicts:** heaviest ring (1.9px), a vermilion kintsugi crack across the pot and a carved vermilion hanko seal (2px-radius square, rotated -5deg, `#hanko-edge` pitted edge, pale carved glyph and inner border, blocker count) left of the pot.
- **Unchecked:** hollow disc, no ring.
- **Dormancy:** 45+ days idle desaturates the canopy (saturate .65, brightness .92) and lays 3 moss patches on the gravel; 120+ days is heavier (saturate .32, brightness .8, 7 moss patches). Leaves are not used for dormancy.
- **Marks:** the numbered state disc sits to the right of each pot so front-row canopies never hide it. Pinned is a drawn star in text colour; no-upstream is a wavy-line badge with its own legend entry. The selected tree hangs a swallow-tailed matcha paper strip above it, and tree name labels are unboxed mincho on a hairline with a dark text halo.
- Weather animates (leaf-fall 6s, motes 7s, sway 8s) and freezes under `prefers-reduced-motion`, leaving leaves and motes visible (the bloom is hidden). Trees in lists, inspectors and detail headers are still; board trees sway. The glint is a still glint: its keyframes exist but are not applied.

### Vitals (tree form from history)
A tree may say only what history is known. Girth by age of first commit: under 45 days 0.78, under 200 days 0.92, under 800 days 1.08, older 1.22. Canopy density by 30-day activity: none 0.86, 1-6 commits 1.0, more 1.07. Up to 4 live (non-current, non-stale) branches grow as limbs with buds. When history is unknown (no first commit or activity data) the tree is the plain seeded tree, identical to before. Vitals never encode git state; weather does.

### Raked-gravel ground
The bed is a single canvas (`#board-ground`) inserted under the SVG terrain, painted at 2-4x device scale: a gravel radial gradient lit toward the sun/moon, grain specks (about 1,100), three-tine rake passes that flow around each pot with a dark and a light offset line for relief, swept ellipses under pots with three slightly wobbling raked rings (dashed when the repo is disturbed: gone, error or dirty), a blurred cast shadow away from the light, and an elliptical edge fade into the void. Repaint is cached by a signature (structure, per-repo disturbed flags, quarter-hour of day, tree scales); detail-only changes keep the old bitmap and repaint after a 160ms debounce. Stones and moss remain SVG.

### Sky and time of day
`skyAt(hour)` interpolates night, dawn, day and dusk stops into a tint, an amount, a light height and direction. The tint mixes into the gravel; the light moves cast shadows. `#board-sky` is a 16px crisp disc (opacity .6-.7) with a 1px ring at 28%, no halo; moon in pale sage, dawn/dusk peach, day gold.

### Replay
A Replay toggle (`#board-replay-toggle`, text button with brush underline when pressed) reveals a Play/Pause button, a 30-day scrubber (`#board-replay-range`, 1px track, 14px matcha thumb, up to 300px wide) and a day readout ("Today", or weekday and date, plus up to three repos touched with commit counts). Tiles touched that day show a matcha glow pool (`--glow`: 1 on the day, .55, .3, .15 on the following days; opacity .35 to 1) and untouched tiles recede to 42% opacity. Playing steps one day per 420ms, scrubbing pauses; if activity cannot load the toggle closes with an error toast. The glow pool is hidden under forced colors.

### Inspector and detail actions
The board inspector (272px) and detail header offer ghost actions Copy path (clipboard, "Path copied" toast, manual-copy fallback message) and Open in VS Code (a `vscode://file` link). Palette verbs mirror them.

### Board behaviour
Tiles fade in staggered 70ms, hover or focus lights a pale pool under the pot, a selected tile leaves the rest receded (50% opacity, 0.7px blur, 0.4 saturation) and one faint ensō sits behind the stage (7.5%).

### Brush underline (the one drawn ornament)
A 2.5px tapered, slightly rotated (-0.7deg) stroke in the current color with masked ends, on active toggles, tabs, filters and ghost-button hover.

### Empty states
An empty pot (84x62) above an 18px mincho line: the space is the subject.

## Do's and Don'ts

### Do:
- **Do** express repo state as weather on the tree and keep a text label alongside for legibility.
- **Do** keep one hue per state: gold clean, orange changes, lilac stale, slate unavailable, blue sync, vermilion blocked, and vary ring weight/pattern with severity.
- **Do** use hairlines, underlines and air before reaching for a box.
- **Do** keep type to the 11/12/14/18/22/26/44 scale and set names in the display face.
- **Do** disable all animation under `prefers-reduced-motion`.
- **Do** keep the matcha `#b9d891` accent and dark color scheme; tests pin them.
- **Do** keep the app in the single `dashboard.html`; the server and tests load that file.
- **Do** keep the Shippori Mincho OFL notice with the embedded font and honour `prefers-contrast: more` and `forced-colors` when adding surfaces.
- **Do** let history show only through bounded vitals and the ground through time of day; reserve the brief to one line.

### Don't:
- **Don't** use card grids, boxed panels, colored edge stripes, or dashboard gray.
- **Don't** add ornament beyond the brush underline (the ensō backdrop and sun/moon disc are existing scene elements, not a license for more decoration).
- **Don't** reuse a semantic hue for decoration or another state.
- **Don't** put git state into the seeded tree geometry; the same path and the same history must always grow the same tree.
- **Don't** change the pinned board geometry (156x78 pitch, 128x148 sprite box) without updating tests.

### Known build drift (recorded, not canonized)
- Off-scale one-offs: 20px attention-pill and 10px PR-branch radii (and a 2px hanko/isle-underline radius), `#71876a` moss hard-coded in CSS and in the legend, `#000` shadows, `#050807cc/d0` overlay scrims, `#5d6863` unchecked stroke, the `clamp(30px, ...)` display floor, 26px mobile titles, 20px close glyph.
- The kintsugi crack uses the lighter `--red` rather than the seal fill, so the Seal Rule is applied to fill only.
- Foliage, pot and wood palettes, the sky disc colors and the glow gradient stop colors are hard-coded in JS/CSS rather than custom properties.
- The `#000` shadows and the `#050807d0` scrim stay off-scale; the 30px display clamp floor stays.
- Two detector warnings remain untraced to a source line.
