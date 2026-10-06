# Design

A plain table. The aim is to be read in a second, not admired.

- **Type and color:** the system font and the system light or dark scheme (`prefers-color-scheme`). No web fonts, no
  images. Three status colors (green, amber, red) on top of words; every verdict is also spelled out
  (`✓ golden`, `✗ not golden: ...`, `golden pending CI`).
- **Layout:** one `<table>`, one row per checkout, linked worktrees indented under their project. A row expands
  in place for details. Under 720 px the table becomes stacked cards so nothing scrolls sideways.
- **Order:** repos that need attention first, then by name. Search, three filters and a sort are the only controls,
  plus four buttons: Refresh (local git), Check GitHub, Fetch all, Rescan.
- **Accessibility:** semantic table with a caption, real buttons with `aria-expanded` and `aria-pressed`, a polite
  live status line, visible focus, and no motion beyond what the browser does by default.
- **Text from git is untrusted.** Names, branches and commit subjects are inserted with `textContent` and never as
  HTML; a test commits hostile text and checks it appears literally and never runs.
- **Weight:** under 60 KB in one file, no external requests, and a strict content-security policy
  (`default-src 'none'`, scripts and styles inline only, connections to itself only).
