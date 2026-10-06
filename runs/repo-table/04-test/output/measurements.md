# repo-table measurements (after the critique round)

Machine: this one, real `~/dev/active` (19 checkouts), Chromium via Playwright, median of 3 fresh page loads, automatic CI check off. One machine, not a benchmark.

| | before (bonsai board, commit 94e441a) | after |
|---|---|---|
| page size | 3,371,530 bytes (3.37 MB) | 31,346 bytes (31.3 KB) |
| first row visible | not measured | 0.03s (runs: 0.22, 0.03, 0.03) |
| every row's status in | 3.2 s sequential on the API alone | 0.90s (runs: 1.11, 0.90, 0.90) |
| bytes transferred per load | not measured | 73,828 bytes (page + API responses, including per-branch details) |

Targets from the brief: page under 60 KB; first rows within 1 s; all rows within 5 s.
