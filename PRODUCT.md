# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
A single developer on macOS who keeps many git repositories under local folders and runs the dashboard on localhost. They open it to answer "where do I stand across all my repos?": which are dirty, ahead/behind, or blocked by a PR, and which need attention first. Sessions are short and frequent.

## Product Purpose
repo-root-tracker finds git repository roots and serves a local dashboard (Python server, single `dashboard.html`) that tracks many repos at once. It has three views: a searchable, groupable list, an isometric island board where each project is a plot, and a per-checkout detail view (commits, changes, branches, GitHub). The main checkout is a full bonsai and linked worktrees are small saplings in that plot. Success is seeing the state of every checkout at a glance and opening the right one without friction.

## Positioning
Local-first and read-only. Pins and collections are saved on the localhost dashboard server with a browser copy for offline use, and removing a repo from the dashboard never deletes its files. It shows local git state and optional GitHub signals in one spatial overview, which a terminal `git status` loop cannot do.

## Operating Context
Localhost server on port 7842 via `serve.sh`. Data comes from `/api/repos` and related endpoints. GitHub status is fetched on demand ("Check GitHub"), and local git is refreshed on demand.

## Capabilities and Constraints
- Stack is fixed: a Python backend (`status.py`, `history.py`, `detail.py`, `github.py`, `server.py`) serving one self-contained `dashboard.html` (the display font fallback is embedded). No build step, no network at runtime.
- Views: list, board, detail. Command palette for jumping to a repo. Collections, pins, bulk organize, search, and filters (changed, sync, attention, unavailable).
- Board: one island per page with pagination, camera zoom and pan, fit-to-island, name toggle, search with match count, a "needs attention" filter, and an inspector for the selected plot.
- Existing Playwright and pytest suites (16 files) assert on element IDs, classes, and ARIA behavior. The overhaul must keep them green. Assertions may change only where a visual change makes one obsolete, and each such change is reported to the user.
- Semantic attention states already exist (changed, sync, blocked, unavailable) and must stay distinguishable.
- Vitals: the status API also reports commit count, first-commit date, 30-day activity and local branch names. A tree's trunk girth follows its age, its canopy fullness follows recent activity, and each live branch is a literal limb. Unknown history draws the plain tree.
- Replay: `/api/activity?days=N` (local `git log`, cached 30s) gives per-repo daily commit counts; the board can replay the last 30 days. Project activity includes hidden worktrees, visible members show their own activity, and the readout distinguishes active projects from active checkouts and checkout commit counts.
- Scale: Workspace paginates at 25 projects, with at most three visible worktrees per plot. Counts distinguish projects and checkouts. GitHub, health, replay and ground include hidden worktrees.
- Overflow navigation: left and right saplings stay fixed. The front slot prefers the selected checkout, then the focused checkout, then the first matching hidden worktree, then the normal third worktree. Alt+Left/Right visits every tracked checkout without changing selection. When a requested focus target stays hidden because the selected checkout owns the front slot, focus moves to its inspector checkout row. Enter/Space selects it. The selected checkout always stays rendered and pressed.
- Ambient: tab title carries the count of repos needing action, the favicon is a live bonsai in the worst state's colour, and a one-line brief summarises the garden.
- Actions are client-side only: copy a repo path, or open it through the `vscode://file` URL scheme. Neither touches a repository.
- Ground lighting follows the viewer's local time (moon, dawn, day, dusk); it is decoration and never encodes git state.

## Brand Commitments
Binding visual constraints volunteered by the user for this redesign (recorded, not expanded):
- Visual identity follows https://socratink.ai/ (user decision, 2026-10-01): warm near-black ground (#100f0f), warm paper text, one teal accent (#3aa99f, deeper #1f7a72 for filled badges), Instrument Serif for display and Inter for text (both SIL OFL, embedded so nothing loads from the network), hairline dividers, a glossy dark orb as the mark. This supersedes the earlier night-garden palette, Hiragino/Shippori mincho type and matcha accent. Instrument Serif and Inter are common faces; they are used deliberately to match the brand.
- The spirit of *yohaku no bi* (emptiness as a design material) is kept: generous space, one ensō behind the garden, restraint. The six git-state hues (gold clean, orange changes, blue sync, lilac stale, slate unavailable, vermilion blockers) are kept so state stays readable at a glance.
- Each repo on the board is represented as a bonsai, one bonsai per repo, with tree form encoding git state.
- Radical overhaul across list, board, and detail, not incremental polish. The ambition is to show the upper bound of what Claude models can build in a front end.

## Evidence on Hand
Real repo data comes from the local machine via the API. There are no customers, benchmarks, or testimonials, and none may be invented.

## Product Principles
1. Status first: state is legible at a glance, and expression never obscures it.
2. Read-only and reversible: the dashboard never mutates repositories. Copying a path or opening an editor URL is client-side and counts as read-only.
3. Local and self-contained: no external services required to render, and no build step.
4. The board is a true spatial view of the same data as the list, never decoration.

## Accessibility & Inclusion
Keyboard operation and ARIA semantics already exist and are covered by tests. They must be preserved. Attention states must not rely on color alone. Respect `prefers-reduced-motion`.
