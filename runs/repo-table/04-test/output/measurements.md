# repo-table measurements

Machine: this one, real `~/dev/active` (19 checkouts), Chromium via Playwright, median of 3 fresh page loads. Not a benchmark; one machine.

| | before (bonsai board, commit 94e441a) | after |
|---|---|---|
| page size | 3,371,530 bytes (3.37 MB) | 16,231 bytes (16.2 KB) |
| first row visible | not measured (old board needs its images decoded and its scene drawn) | 0.03s (runs: 0.25, 0.03, 0.03) |
| every row's status in | 3.2 s sequential on the API alone (measured before building) | 0.53s (runs: 0.69, 0.52, 0.53) |
| bytes transferred per load | not measured | 39,623 bytes (page + API responses) |

Targets from the brief: page under 60 KB; first rows within 1 s; all rows within 5 s.
