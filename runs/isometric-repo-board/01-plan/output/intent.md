# Intent: Isometric repo board

**Originator:** jondev (chat request)
**Status:** draft
**Date:** 2026-09-30

## 1. Problem Statement

`dev/active` holds roughly 10 git repos at time of writing (count not normative; the tracker list is authoritative). Repo health today is visible as the dashboard card list (`dashboard-status-v2`) with per-repo detail views (`repo-detail-view`: commit graph, diffs, branches). There is no at-a-glance, spatial view: answering "what needs my attention right now across all repos" requires reading every card. Groveboard already solves the analogous problem for goals with a 5x5 isometric island where each tile's growth stage encodes progress — that visual language has no counterpart for repos.

## 2. Proposed Outcome

An optional, additive isometric board view in repo-root-tracker — alongside, not replacing, the existing card list — where each tile represents one repo from the tracker's existing tracked list (human decision 2026-09-30; auto-discovery rejected), modeled on Groveboard's isometric island visual language. Tile visuals encode a defined subset of the `dashboard-status-v2` signals (Stage 02 must state which: at minimum dirty/clean, sync state, stale count; branch/last-commit shown as tile label or detail, not necessarily as stage) plus explicit loading/error stages. A clean, in-sync, unstale repo with no upstream renders `healthy` with an explicit muted no-upstream badge (human decision D1, 2026-09-30: no-upstream is healthy-family, not attention). Needs-attention oracle: `data-stage` starting with `attention-`, or `gone`, or `error` — `healthy` (badged or not) and `loading` never count. Selecting a tile navigates to the existing detail view using the exact `#/repo/<encoded-path>` contract from `repo-detail-view` (encoding scheme plus back-button/refresh behavior preserved; Stage 02 must cite the encoding function). The card list remains the default; the board is a switchable view. Rendering technology (Groveboard-style SVG port vs. clean-room reimplementation in another stack) is an explicit Stage-02 decision with a11y/perf rationale.

Success: the board renders exactly N tiles for the N repos in the chosen set with no silent omissions, and every repo matching the needs-attention predicate (`is_clean == false OR ahead+behind > 0 OR stale_branches > 0`, per v2 `RepoStatus` semantics) renders in a non-healthy tile stage distinguishable by DOM attribute (e.g. `data-stage != healthy`) and by more than color alone; all others render healthy. Verified by tests asserting the DOM mapping for dirty, ahead, stale, clean, loading, error, and no-upstream fixture states.

## 3. Affected Users and Systems

- Users / Teams: jondev (solo, local use).
- Services / Repos / Modules: `repo-root-tracker` web server/dashboard (new board view + git-status-to-tile mapping); repos in the chosen set as read-only data sources; Groveboard as a visual/structural model only.
- Prior runs in scope as context, not to be modified (routes, `#/repo/<encoded-path>` contract, and `/api/*` shapes unchanged): `dashboard-status-v2` (status signals, async semantics), `repo-detail-view` (detail view, navigation target).

## 4. Constraints & Boundaries

- Local-only; no remote API auth (consistent with v2/v3 decisions).
- Read-only, optional visualization: the board issues no git mutations (no commit/stash/checkout from tiles), changes no existing routes or default view, and is reachable without losing the card list.
- Groveboard is a model, not a dependency. Clean-room only (human decision 2026-09-30): Stage 02 may study its tile math and layout but must not copy code or add a cross-repo import; no exceptions.
- Board inherits v2 async semantics: the repo set renders immediately; tile statuses resolve asynchronously with loading and error stages. Slow or locked repos, missing upstream, and missing git binary produce explicit tile error or muted states — never a blank or blocked board. Status is a snapshot per page load with an explicit manual refresh control (human decision 2026-09-30; live updates rejected).
- Board is not color-only for information: every tile exposes a text equivalent (name plus status summary via title/aria-label), keyboard focus with Enter navigating to detail, and health is never encoded by color alone (shape or label redundancy required).
- Factory references in `_shared/` stay unchanged during the run; code-writing happens in a separate worktree or clone, never bare branches in this checkout.
- Verification requires real project checks in `_system/verification.json` before any passing claim.

## 5. Open Questions

- Rendering technology: SVG port vs. reimplementation (Stage 02, with a11y/perf rationale; clean-room either way per §4).
- Capacity overflow: behavior when the tracked set exceeds the island tile cap (wrap, scroll, paginate — Stage 02 must define; Groveboard caps at 25).
- Load budget: first paint of the repo set without per-tile status within a defined millisecond budget (Stage 02 to propose the number).
- Empty state (zero tracked repos) and untracked-dir exclusion note (Stage 02 to define).
- Resolved 2026-09-30 (human): repo set = tracker tracked list; reuse = clean-room only, no exceptions; a11y = full equivalence (§4); refresh = snapshot-on-load with manual refresh (§4); needs-attention predicate and DOM-attribute oracle as drafted in §2 unless challenged at Stage-02 review.
