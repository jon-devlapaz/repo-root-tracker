# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
A single developer on macOS who keeps many git repositories under local folders and runs the dashboard on localhost. They open it to answer "where do I stand across all my repos?": which are dirty, ahead/behind, or blocked by a PR, and which need attention first. Sessions are short and frequent.

## Product Purpose
repo-root-tracker finds git repository roots and serves a local dashboard (Python server, single `dashboard.html`) that tracks many repos at once. It has three views: a searchable, groupable list, an isometric island board where each repo is a plot, and a per-repo detail view (commits, changes, branches, GitHub). Success is seeing the state of every repo at a glance and opening the right one without friction.

## Positioning
Local-first and read-only. Pins and collections live in the browser, and removing a repo from the dashboard never deletes its files. It shows local git state and optional GitHub signals in one spatial overview, which a terminal `git status` loop cannot do.

## Operating Context
Localhost server on port 7842 via `serve.sh`. Data comes from `/api/repos` and related endpoints. GitHub status is fetched on demand ("Check GitHub"), and local git is refreshed on demand.

## Capabilities and Constraints
- Stack is fixed: a Python backend (`status.py`, `history.py`, `detail.py`, `github.py`, `server.py`) serving one self-contained `dashboard.html` (the display font fallback is embedded). No build step, no network at runtime.
- Views: list, board, detail. Command palette for jumping to a repo. Collections, pins, bulk organize, search, and filters (changed, sync, attention, unavailable).
- Board: one island per page with pagination, camera zoom and pan, fit-to-island, name toggle, search with match count, a "needs attention" filter, and an inspector for the selected plot.
- Existing Playwright and pytest suites (16 files) assert on element IDs, classes, and ARIA behavior. The overhaul must keep them green. Assertions may change only where a visual change makes one obsolete, and each such change is reported to the user.
- Semantic attention states already exist (changed, sync, blocked, unavailable) and must stay distinguishable.
- Vitals: the status API also reports commit count, first-commit date, 30-day activity and local branch names. A tree's trunk girth follows its age, its canopy fullness follows recent activity, and each live branch is a literal limb. Unknown history draws the plain tree.
- Replay: `/api/activity?days=N` (local `git log`, cached 30s) gives per-repo daily commit counts; the board can replay the last 30 days, glowing the repos touched on each day.
- Scale: islands paginate at 25 repos; an archipelago strip lists every island with its state counts; the board changes level of detail with zoom.
- Ambient: tab title carries the count of repos needing action, the favicon is a live bonsai in the worst state's colour, and a one-line brief summarises the garden.
- Actions are client-side only: copy a repo path, or open it through the `vscode://file` URL scheme. Neither touches a repository.
- Ground lighting follows the viewer's local time (moon, dawn, day, dusk); it is decoration and never encodes git state.

## Brand Commitments
Binding visual constraints volunteered by the user for this redesign (recorded, not expanded):
- Seeded from the spirit of *yohaku no bi*, the beauty of empty space (Seattle Japanese Garden essay).
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
