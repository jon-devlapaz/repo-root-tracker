# repo-table measurements (redesigned page)

Machine: this one, real `~/dev/active` (19 checkouts), Chromium via Playwright, median of 3 fresh page loads. One machine, not a benchmark.

| | before (bonsai board, commit 94e441a) | after |
|---|---|---|
| page size | 3,371,530 bytes (3.37 MB) | 26,208 bytes (26.2 KB) |
| first row visible | not measured | 0.03s (runs: 0.21, 0.03, 0.03) |
| every row's status in | 3.2 s sequential on the API alone | 0.79s (runs: 0.92, 0.79, 0.79) |
| bytes transferred per load | not measured | 59,483 bytes (page + API responses, now including branch details) |

Targets from the brief: page under 60 KB; first rows within 1 s; all rows within 5 s.
