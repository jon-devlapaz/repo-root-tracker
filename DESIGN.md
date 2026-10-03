---
name: repo-root-tracker
description: A quiet near-black dashboard in the socratink.ai voice (Instrument Serif over Inter, one teal accent) where every git repo is a seeded bonsai and git state is weather.
colors:
  ground: "#100f0f"
  surface: "#1c1b1a"
  surface-raised: "#282726"
  hairline: "#343331"
  control-line: "#878580"
  teal: "#3aa99f"
  teal-hover: "#4cbcb1"
  teal-fill: "#1f7a72"
  on-teal: "#100f0f"
  paper-text: "#f2f0e5"
  body-ink: "#cecdc3"
  muted-stone: "#a3a199"
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
  slate-unavailable: "#9a988f"
  slate-fill: "#3b4642"
  sync-blue: "#8fbfe0"
  sync-fill: "#2f5672"
  clean-green: "#9bd3a5"
  merge-purple: "#c5b1de"
  celadon: "#a0d8cf"
  orb-rim: "#e6e4d9"
  orb-shadow: "#575653"
  unchecked-stroke: "#6f6e69"
  dormant-moss: "#71876a"
  replay-pool: "#cfe6f0"
typography:
  display:
    fontFamily: "'Instrument Serif', 'Instrument Serif Embedded', ui-serif, Georgia, serif"
    fontSize: "clamp(36px, 4.8vw, 54px)"
    fontWeight: 400
    lineHeight: 1.04
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "'Instrument Serif', 'Instrument Serif Embedded', ui-serif, Georgia, serif"
    fontSize: "clamp(28px, 3.6vw, 36px)"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  inspector-title:
    fontFamily: "'Instrument Serif', 'Instrument Serif Embedded', ui-serif, Georgia, serif"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  title:
    fontFamily: "'Instrument Serif', 'Instrument Serif Embedded', ui-serif, Georgia, serif"
    fontSize: "22px"
    fontWeight: 400
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Inter, 'Inter Embedded', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Inter, 'Inter Embedded', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "12px"
    fontWeight: 400
    letterSpacing: "0.04em"
  caption:
    fontFamily: "Inter, 'Inter Embedded', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "11px"
    fontWeight: 400
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  control: "8px"
  row: "10px"
  panel: "12px"
spacing:
  space-1: "4px"
  space-2: "8px"
  space-3: "12px"
  space-4: "16px"
  space-6: "24px"
components:
  button-primary:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.on-teal}"
    rounded: "{rounded.control}"
    padding: "8px 20px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.teal-hover}"
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

**Creative North Star: "The Quiet Garden"**

The visual identity follows https://socratink.ai/ by user decision (2026-10-01): a warm near-black ground, warm paper text, one teal accent, a large tight Instrument Serif display over a quiet Inter, hairline dividers and a small glossy orb as the mark. The ground is flat. There are no mist gradients, only a 3.5% paper grain, and the header is a solid bar with a 1px hairline. Every repo is still a bonsai whose form is seeded by its path, and its git state shows as weather around it, never as chrome.

The spirit of yohaku (emptiness as material) is kept as an intent: generous air, restraint, one ensō behind the garden, almost nothing in a box. Density is low and typographic. A tree's trunk, canopy and limbs reflect the repo's age, recent activity and live branches, and the ground under it is lit by the real time of day. Rows are sparse, controls are quiet text with hairline underlines, and the one filled control is a flat teal button. The list is an 820px column (880px in detail); the board is a borderless stage that fades into the ground, with a single margin-note inspector at the right.

The build refuses card grids, boxed panels, colored edge stripes and dashboard gray. State is legible through the trees and six semantic hues, and expression never replaces the label. Instrument Serif and Inter are common faces; they were chosen deliberately to match the brand, not for distinctiveness.

**Key Characteristics:**
- Dark-only (`color-scheme: dark`); one accent, teal.
- Flat warm-grey ground, hairlines and tonal surfaces, no boxes at rest.
- Instrument Serif display, Inter text, mono for paths and hashes.
- Git state encoded as weather outside the seeded tree geometry; history encoded as bounded vitals inside it.
- Single-file constraint: the whole UI is one `dashboard.html` (inline CSS, JS, the two embedded fonts and SVG/canvas drawing) because the server and tests load that one file. This is deliberate; do not split it.

## Colors

A flat warm near-black ground with paper-warm text, one teal accent, and six state hues (gold, orange, lilac, slate, blue, vermilion) that each own exactly one git state.

### Primary
- **Teal** (`{colors.teal}`, CSS `--accent`, also `--accent-dim`): the one live accent. Primary button fill, links, focus rings, active tab/filter/island text, branch names, selection background, caret, checkbox accent, selected-tile leader line. Its tints (11% background, 42% border) are mixed from it with `color-mix`.
- **Teal Hover** (`{colors.teal-hover}`): primary button hover.
- **On Teal** (`{colors.on-teal}`, `--on-accent`, same value as the ground): text on the teal fill and on selection.
- **Teal Fill** (`{colors.teal-fill}`, `--accent-fill`): the deeper teal for filled badges.

### Secondary
- **Vermilion Seal** (`{colors.vermilion-seal}`, CSS `--danger-fill`): blockers and conflicts only. It fills the carved hanko seal on a tree. **Vermilion Line** (`{colors.vermilion-line}`, `--red`) draws the kintsugi crack, diff deletions and failing CI; **Vermilion Text** (`{colors.vermilion-text}`) is the readable text tint for errors and GitHub blocker signals.
- **Gold** (`{colors.gold-clean}`): clean. One still glint on the tree, the disc fill `{colors.gold-fill}`, the "all calm" island title and the dirty-to-clean bloom. A clean tree has no status ring.
- **Orange** (`{colors.orange-changes}`): local changes. Falling and fallen leaves, legend, changed ring and filter count, changed repo label, warning notes, tab count pill. Disc fill `{colors.orange-fill}`.
- **Lilac** (`{colors.lilac-stale}`): stale branches. Jin dead-wood strokes and a dotted ring; stale labels and branch rows. Disc fill `{colors.lilac-fill}`.
- **Slate** (`{colors.slate-unavailable}`): unavailable data, now a warm grey. Dashed ring and unavailable repo label. Disc fill `{colors.slate-fill}`.
- **Sync Blue** (`{colors.sync-blue}`): ahead/behind sync (motes). `{colors.sync-fill}` is its filled form.
- **Amber Leaf** (`{colors.amber-leaf}`, `--yellow`, fill `{colors.amber-fill}` as `--warning-fill`): not a state hue. It survives only for the pending-CI badge and the family-level GitHub "checking/incomplete" disc fill.
- **Unchecked** has no hue: the numbered disc is hollow (transparent, 1px `{colors.unchecked-stroke}` stroke).

### Tertiary
- **Clean Green** (`{colors.clean-green}`): diff additions, passing CI, current branch (not the clean state; that is gold).
- **Merge Purple** (`{colors.merge-purple}`, `--purple`) and **Celadon** (`{colors.celadon}`, `--cyan`): merge commits, remote tags, and commit-graph lane colors (lanes also use teal and warm or muted tones).

### Neutral
- **Ground** (`{colors.ground}`, `--bg`): page, header bar and diff boxes; carries fixed paper grain at 3.5% opacity and nothing else.
- **Surface** (`{colors.surface}`) and **Raised Surface** (`{colors.surface-raised}`, `--surface2`): menus, dialogs, palette, toasts, inspector sheet, diff file heads. Rows have no resting surface. The header hairline is the Raised Surface value.
- **Hairline** (`{colors.hairline}`, `--border`): dividers and panel edges. **Control Line** (`{colors.control-line}`): the underline of inputs and selects.
- **Paper Text** (`{colors.paper-text}`), **Body Ink** (`{colors.body-ink}`), **Muted Stone** (`{colors.muted-stone}`): headings, body, secondary.
- **Orb** (`{colors.orb-rim}` rim, `{colors.orb-shadow}` highlight stop): the header mark is a 16px circle with an SVG radial gradient (ground to raised surface to orb shadow), a rim at 55% and a small glossy ellipse at 35%.
- **Dormant Moss** (`{colors.dormant-moss}`): moss patches on the gravel at the base of a dormant tree (`.moss`, 75% opacity). Hard-coded in CSS.
- **Replay pool** (`{colors.replay-pool}`, gradient `#board-glow`, 75/22/0%): pale blue-white pool under tiles touched that day.
- **Sky disc**: moon is a thin crescent ring in `{colors.orb-rim}` at 60%; dawn, dusk and day are a solid warm paper disc (`#ece6d8`, 20px, 42%). Hard-coded in CSS.
- **Bonsai palettes** live in JS, not CSS tokens. `BONSAI_FOLIAGE` family 0 is teal (dark `#0f2926`, mid `#1f6b64`, high `#6fc2b7`, fleck `#c6ece6`), family 1 rose, family 2 indigo, family 3 olive (`#25261a`, `#6b7048`, `#b8bd8a`, fleck `#e6e9c8`). Each carries a warm-grey gravel and stone; pots, soil and avatars are warm greys. The gravel is mixed toward the time-of-day tint on the canvas ground.

### Named Rules
**The Seal Rule.** Vermilion fill means a blocker or conflict and nothing else, whether the carved hanko seal on the board or the list badge. Never use it for decoration or emphasis.
**The One Meaning Rule.** Gold is clean, orange is local changes, lilac is stale, slate is unavailable, blue is ahead/behind, vermilion is blocked, teal is the accent and focus. Each state owns one hue and each hue one state; amber is not a state colour, and the same hues apply in list and detail views as on the board.
**The Redundant Signal Rule.** Hue never works alone. Severity also changes ring weight and pattern, and the text label always stays (see Bonsai weather).
**The One Accent Rule.** Teal is the only brand colour. A tree family may be teal, rose, indigo or olive by seed, but UI chrome never takes a second accent.

## Typography

**Display Font:** Instrument Serif (embedded as `'Instrument Serif Embedded'`, 400, Latin subset, WOFF data URI; fallback ui-serif, Georgia, serif)
**Body Font:** Inter (embedded variable subset as `'Inter Embedded'`, weights 400-600; fallback ui-sans-serif, system-ui, Segoe UI)
**Label/Mono Font:** ui-monospace stack (SF Mono, Menlo, Consolas) for paths, hashes, branches, diffs

**Character:** A large, tightly tracked display serif carries names and headings over a quiet Inter that carries data. Both faces are SIL Open Font License 1.1, embedded so nothing loads from the network, and the copyright and license notices stay in the stylesheet comment and must travel with the fonts. They are common faces, used deliberately to match the socratink.ai brand. The subsets are Latin only; the stacks name the system `Inter` and `Instrument Serif` first so an installed copy wins over the embedded one.

### Hierarchy
- **Display** (400, `clamp(36px, 4.8vw, 54px)`, 1.04, -0.025em): view titles (list overview, board island name).
- **Headline** (400, `clamp(28px, 3.6vw, 36px)`, 1.3, -0.02em): repo name in the detail header. **Inspector title** is 32px, 1.3, -0.02em.
- **Title** (400, 22px, -0.01em): collection headings, attention summary, branch and GitHub section titles, repo names in rows. Dialog titles are 28px (-0.015em); the worktree dialog title is 24px.
- **Field** (display face, 20px, -0.005em): list search and board search; the command palette input is 24px.
- **Body** (Inter 400, 14px, 1.6): controls, tabs, commit subjects, the garden brief. Buttons are 500. Tabular numerals are on globally.
- **Label** (400, 12px, +0.04em): metadata, notes, counts, hints. Notes cap near 62ch.
- **Caption** (400, 11px): hashes, relative times, file badges, kbd.
- **Board text:** island title in the SVG is 22px display; plot names and the hover tip are 14px display; archipelago buttons are 16px display; empty-state lines are 20px.

### Named Rules
**The Serif Names Rule.** Names of things (repos, collections, islands) and headings use the display face; data, controls and paths use Inter or mono.
**The Tight Display Rule.** Display sizes track negative (-0.01em to -0.025em); small text keeps its positive or neutral tracking.

## Layout

Single centered column: `main` is 820px max (detail view 880px) with a fluid gutter of `clamp(20px, 5vw, 56px)` and generous top air (overview margin 44px). Spacing steps are 4, 8, 12, 16, 24; sections separate by 30-56px of empty space rather than rules. Rows lead with a 58px bonsai glyph (58x69 svg), then name, path, meta; on mobile the menu sits on the name line; detail headers lead with a 132x158 bonsai.

The Board is home (`#/board`; the list is `#/list`) and uses the full window up to 1840px. It is a two-column workspace: a fluid stage (height `clamp(460px, calc(100dvh - 300px), 1300px)`, edges masked to fade into the ground, fit zoom up to 2x) and a 300px inspector set off by one hairline on its left. Islands are user-made: the archipelago row lists Workspace then each custom island, and a quiet row of text buttons (New island, Choose projects, Rename, Delete, Export) sits under the search. Island dialogs are native `<dialog>`s with 44px picker rows and an inline error line that keeps the draft on a failed save. An empty island shows one muted sentence and a Choose projects button inside a finite ensō. Under 850px the inspector is hidden; under 650px the header becomes a grid and the stage shortens to `clamp(300px, 46vh, 440px)`. Board geometry is isometric 2:1 with a 156x78 grid pitch, 36px depth, and a fixed 128x148 sprite box per tile. On narrow screens the camera fits to 96% of the stage width with a 0.56 zoom floor. Label layout is idempotent. The board caption reads "Select a tree..." on touch devices. In list rows, freshness and unknown-GitHub signals are hidden until hover or focus on hover-capable devices.

The garden brief (`#list-brief`, `#board-brief`) is one 14px body-ink sentence summarising git state. It reserves a single line (min-height 1.6em, no wrap, ellipsis, max 92ch) so the layout never jumps; on phones it may wrap to two lines. The archipelago strip (`.isle`) lists islands as 16px display text buttons with a repo count and `.isle-dot` state counts (7px tone dot plus 11px count; unavailable is a dashed ring); the current island is teal with an underline; touch targets grow to 44px.

Semantic zoom sets `data-lod` from camera zoom: far (under 0.5) enlarges status rings and discs and hides glint and moss; near (1.6 and up) shows all plot names. Zoom is 0.35 to 1.5 at fit time with a +/- control and percentage readout.

Keyboard: arrow keys walk between board tiles, Escape clears selection, Left/Right/Home/End move between detail tabs. The command palette adds verbs (Board view, List view, and with a repo in focus Copy path of / Open in VS Code) ahead of fuzzy path matches. The board stage carries an aria label and a spoken summary of each island.

## Elevation & Depth

Flat and tonal, not shadowed. Depth comes from the step from ground to Surface to Raised Surface, hairline borders, recession (when a tile is selected the rest drop to 50% opacity with 0.7px blur and 0.4 saturation) and the canvas-painted raked-gravel bed. Shadows exist only on things that lie over the garden; the garden's own cast shadows are painted into the ground and point away from the light.

### Shadow Vocabulary
- **Lifted slip** (`box-shadow: 0 6px 12px -4px #000`): menu panel, dialog, command palette.
- **Sheet rising** (`box-shadow: 0 -4px 12px #0008`): the narrow-screen board inspector sheet.
- Tree shadows under pots and stones are `#000` ellipses at 26-35% opacity; the ground canvas adds a blurred (2.4px) 36% cast shadow whose length follows the light height.

### Named Rules
**The Flat-At-Rest Rule.** Rows, tiles and controls carry no shadow or box at rest; hover is a faint teal wash (6%) or a color shift.

## Shapes

Soft but restrained radii: 8px controls, 10px rows, 12px panels (menus, dialogs, palette). Inputs and filters have none (underline only). Circles are reserved for avatars, CI badges, branch dots, numbered discs and the orb mark. Marks on the board (pinned star, no-upstream wavy line, selection strip, disclosure chevron) are drawn paths, not glyphs. Silhouettes belong to the trees: seeded ink-brush bonsai in eight styles chosen from a hash of the repo path, with four pot glazes and four family foliage palettes. Hanko seals use a separate `#hanko-edge` filter (displacement plus a pitted alpha mask) and a -5deg rotation so the edge looks carved. A canopy ink filter roughens canopy edges. Tree geometry is deterministic per path and history; only weather animates. Vitals bend the form within bounds (see Vitals).

## Components

### Buttons
- **Shape:** 8px radius, 40px min height.
- **Primary:** flat Teal fill, On Teal text, no border, 14px/500, -0.01em, padding 8px 20px. Hover moves to Teal Hover (0.2s ease). Disabled is 45% opacity.
- **Ghost / secondary:** plain text, no fill or border, body ink 12px; hover raises text to paper and draws a plain 1px underline. `btn-danger` hover turns text vermilion.
- **Focus:** 1.5px teal outline, 4px offset, on every focusable element.

### Filters, tabs, view toggles
- Plain text, muted. Active state is teal (filters, islands) or paper (tabs) plus a plain 1px underline. Counts are tabular at 80% opacity.

### Inputs / Fields
- Transparent with a 1px Control Line bottom border and 40px height; focus swaps to a teal border plus matching 1px bottom glow. Search fields use the display face; the add-repo path field uses mono. Placeholders are muted stone.

### Repo rows
- No box. 10px radius with a left-to-right teal 6% wash on hover. Bonsai glyph, 22px display name, mono path, 12px meta (branch in mono teal), signals aligned right. Pin and menu icons are muted until row hover.

### Menus, dialogs, palette
- Raised Surface, 1px hairline, 12px radius, Lifted slip shadow. Palette: 24px display input, mono 14px items.

### Header mark
- Solid ground bar with a 1px Raised Surface hairline, a 16px glossy orb (radial-gradient circle, rim and highlight) and a 15px Inter 500 wordmark.

### Bonsai weather (signature)
Weather is drawn outside the seeded tree geometry and encodes state; a status ring under the pot repeats it by weight and pattern:
- **Clean:** one still gold glint (no loop), gold disc, no ring. Going dirty-to-clean fires a gold bloom (two expanding ellipses, 2.6s) and an "all calm" toast; a fully clean island title turns gold.
- **Local changes:** 4-10 orange leaves fall, with a few lying at the base (count scales with changed files).
- **Ahead / behind:** up to 4 pale-blue motes drift up (ahead) or down (behind). Ring 1.2px.
- **Stale branches:** lilac jin (dead wood) on the trunk; dotted ring (1.4px).
- **Unavailable:** dashed ring (1.6px).
- **Blocked / conflicts:** heaviest ring (1.9px), a vermilion kintsugi crack across the pot and a carved vermilion hanko seal (2px-radius square, rotated -5deg, `#hanko-edge` pitted edge, blocker count) left of the pot.
- **Unchecked:** hollow disc, no ring.
- **Dormancy:** 45+ days idle desaturates the canopy (saturate .65, brightness .92) and lays 3 moss patches on the gravel; 120+ days is heavier (saturate .32, brightness .8, 7 moss patches).
- **Marks:** the numbered state disc sits to the right of each pot. Pinned is a drawn star in text colour; no-upstream is a wavy-line badge with its own legend entry. The selected tree hangs a swallow-tailed paper strip above it, and tree name labels are unboxed display text on a hairline with a dark halo.
- Weather animates (leaf-fall 6s, motes 7s, sway 8s) and freezes under `prefers-reduced-motion`, leaving leaves and motes visible (the bloom is hidden). Trees in lists, inspectors and detail headers are still; board trees sway.

### Vitals (tree form from history)
A tree may say only what history is known. Girth by age of first commit: under 45 days 0.78, under 200 days 0.92, under 800 days 1.08, older 1.22. Canopy density by 30-day activity: none 0.86, 1-6 commits 1.0, more 1.07. Up to 4 live (non-current, non-stale) branches grow as limbs with buds. When history is unknown the tree is the plain seeded tree. Vitals never encode git state; weather does.

### Raked-gravel ground
The bed is a single canvas (`#board-ground`) under the SVG terrain, painted at 2-4x device scale: a warm-grey gravel radial gradient lit toward the sun/moon, grain specks, three-tine rake passes that flow around each pot, swept ellipses under pots with raked rings (dashed when the repo is disturbed), a blurred cast shadow away from the light, and an elliptical edge fade into the ground. Repaint is cached by a signature; detail-only changes repaint after a 160ms debounce. `skyAt(hour)` interpolates night, dawn, day and dusk into a tint and a light height; `#board-sky` is a small crisp disc with no halo.

### Replay
A Replay toggle reveals a Play/Pause button, a 30-day scrubber (1px track, 14px accent thumb, up to 300px wide) and a day readout (active projects, active checkouts, labelled checkout commit counts). Each plot uses the maximum activity over all its checkouts, including hidden worktrees; checkout counts are never added and called unique project commits. The pale pool fades through 1, .55, .3 and .15; untouched plots recede to 42% opacity. Playing steps one day per 420ms.

### Inspector and detail actions
The board inspector (272px) and detail header offer ghost actions Copy path (clipboard, toast, manual-copy fallback) and Open in VS Code (a `vscode://file` link). Palette verbs mirror them.

### Board and project plots
Tiles fade in staggered 70ms, hover or focus lights a pool under the pot, a selected tile leaves the rest receded and one faint ensō sits behind the stage (7.5%; 3% under `prefers-contrast: more`).

Each project owns one plot: a full main bonsai and up to three worktree saplings at scale 0.55 in fixed slots left (-44, 8), right (44, 8) and front (0, 36), which keeps them inside the 128x148 sprite box. Left and right saplings stay fixed. The front slot prefers selection, then focus, then a matching hidden worktree, then the normal third worktree. A selected checkout always remains rendered and pressed. Alt+Left/Right cycles all tracked project members without changing selection; if the requested member stays hidden, focus moves to its 44px inspector checkout row.

Ring and disc tone include every tracked checkout, in this order: blocked, unavailable, changed, sync, stale, unknown, clean. The shared circle reports project-wide GitHub: gold dot for confirmed coverage, a number for PR blockers, CI for failing workflows, ? for unconfirmed coverage, and ! for incomplete checks. The separate +N counts hidden worktrees. All calm requires settled local health across the whole Workspace and fresh, complete, confirmed GitHub checks.

### Empty states
An empty pot (84x62) above a 20px display line: the space is the subject.

## Do's and Don'ts

### Do:
- **Do** express repo state as weather on the tree and keep a text label alongside for legibility.
- **Do** keep one hue per state: gold clean, orange changes, lilac stale, slate unavailable, blue sync, vermilion blocked, and vary ring weight/pattern with severity.
- **Do** use hairlines, underlines and air before reaching for a box; keep the yohaku restraint of one ensō and no extra ornament.
- **Do** set names and headings in Instrument Serif with negative tracking, and data in Inter or mono.
- **Do** keep the primary button a flat teal fill with dark text and no border.
- **Do** disable all animation under `prefers-reduced-motion`.
- **Do** keep the dark color scheme and the teal accent; the brand commitment pins them.
- **Do** keep the app in the single `dashboard.html`; the server and tests load that file.
- **Do** keep the Instrument Serif and Inter OFL notices with the embedded fonts, and honour `prefers-contrast: more` and `forced-colors` when adding surfaces.
- **Do** let history show only through bounded vitals and the ground through time of day; reserve the brief to one line.

### Don't:
- **Don't** use card grids, boxed panels, colored edge stripes, or dashboard gray.
- **Don't** reintroduce mist gradients, matcha green, mincho type or a filled-with-border button.
- **Don't** reuse a semantic hue for decoration or another state.
- **Don't** put git state into the seeded tree geometry; the same path and the same history must always grow the same tree.
- **Don't** change the pinned board geometry (156x78 pitch, 128x148 sprite box) without updating tests.

### Known build drift (recorded, not canonized)
- The tapered, rotated brush underline is retired for tabs, filters and ghost hover (plain 1px line), but the archipelago `.isle[aria-current]` underline is still the 2px tapered brush stroke. The spinner is still a brush-ring ensō, and the CSS keeps `.brush` class names and a stale header comment about a "night garden in sumi".
- Leftover green-tinted values from the retired palette: the `prefers-contrast: more` overrides (muted `#c4d2ca`, body `#e2e9df`, border `#6a7f75`, control `#9fb4aa`), the slate disc fill `#3b4642`, the scrollbar thumb `#2c3a35`, the `#56625b` soil highlight and the `#71876a` moss.
- Off-scale one-offs: 3px radii on kbd, focus ring, palette items, toast, commit hash and diff box; a 6px inspector-sheet radius; 20px attention-pill and 10px PR-branch radii; a 2px hanko radius; `#000` shadows; `#050807cc/d0` overlay scrims (green-black, not the warm ground); the 9px disc numerals and 10px legend glyphs in the SVG.
- The type scale has grown beyond the old seven sizes (11, 12, 14, 16, 20, 22, 24, 28, 32, clamp 28-36 and 36-54 are all in use); a consolidation is not done.
- Foliage, pot, wood and sky palettes and the replay pool are hard-coded in JS/CSS rather than custom properties.
- The embedded fonts are Latin subsets only; any non-Latin text (for example in repo names) falls back to system fonts.
- Two detector warnings remain untraced to a source line.

## Known limitations

- **Reference performance gate (opt-in, not in CI).** `RRT_REFERENCE_PERF=1 python -m pytest tests/test_board_performance.py` stress-tests 90 projects and 360 checkouts with Names on and a full refresh. On the development machine it did not pass when last recorded (median promotion work about 16-19 ms against a limit of 10; longest task 58-85 ms against 50). Measurements swing about 30% between identical runs, so a clean verdict needs a quiet reference machine. This was not re-measured for the restyle.

## Golden canopies (2026-10-03)
A clean checkout (git-golden) grows a gold canopy: `{dark:#5a3d05, mid:#d4a017, high:#ffd966, fleck:#fff6c9}` replaces the family foliage palette for that tree. Every other state keeps its family colour and shows its state through weather and the ring, so gold stays rare enough to mean something. This supersedes the earlier rule that foliage never encodes health. Tree geometry is still independent of git health; tests compare shape, not colour.
