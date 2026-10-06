# Design

A plain table. The aim is to be read in a second, not admired.

- **Type and color:** the system font and the system light or dark scheme (`prefers-color-scheme`). No web fonts, no
  images; icons are small inline SVGs in one stroke weight. Three status colors (green, amber, red) on top of words.
- **Layout:** one `<table>`, grouped by status (Needs work, Pending CI, Golden), linked worktrees indented under
  their project. A row expands in place. Under 720 px each repo becomes a three-line card with no field labels and a 44 px tap target.
- **Say little, show state:** the group heading says the status once; each row has a small drawn icon (with the words in
  its accessible name) and a few short chips, not sentences, so nothing repeats. The counts on the filter chips are the summary, so there is no separate headline block.
  The branch is dimmed on `main` so only deviations carry color.
- **Order:** within a group, repos with the fewest outstanding items first. Search, a sort and four buttons
  (Refresh, Fetch, GitHub, Rescan) are the only controls.
- **Feedback you can act on:** the expanded row lists each outstanding item with its fix command and a copy button.
  Stray branches are marked merged (safe to delete) or unmerged, and the delete command covers only the merged ones.
- **Honest praise:** "Everything is clean." appears only when every repo is golden, and a repo is never golden until CI
  passed.
- **Accessibility:** semantic table with a caption, real buttons with `aria-expanded` and `aria-pressed`, a polite
  live status line, visible focus, and no motion beyond what the browser does by default.
- **Text from git is untrusted.** Names, branches and commit subjects are inserted with `textContent` and never as
  HTML; a test commits hostile text and checks it appears literally and never runs.
- **Weight:** under 60 KB in one file, no external requests, and a strict content-security policy
  (`default-src 'none'`, scripts and styles inline only, connections to itself only).
