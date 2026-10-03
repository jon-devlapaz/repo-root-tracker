# PR-based growth proof

The user asked for a pragmatic version and approved first proving that seedling,
medium and mature trees look clearly different at actual board size.

Replaced age, activity and branch-driven geometry in the pixel preview with
three proposed merged-PR bands. Tree scale is 0.4, 0.7 or 1.0, anchored at the
soil; the pot stays fixed. Unknown counts have their own state and question mark.
All counts are labeled sample data. The current GitHub collector does not fetch
merged totals; no open-PR count, commit count or age is substituted.

The renderer bypasses its old age-based markup cache for the preview family,
so a changed count appears immediately. Tests cover 55 count/color combinations,
actual rendered size separation, color transitions, independence from old history
inputs, refreshed counts, unknown counts, desktop/mobile selection and list/detail.
See checks.json and the actual gallery screenshot family-all.png.

The proof uses the existing generated layers. No runtime dependency, new image
or production renderer change was needed. Live totals, failure retention and
production integration remain future work. Existing performance failures remain
unresolved. No SDLC approval receipt was changed.
