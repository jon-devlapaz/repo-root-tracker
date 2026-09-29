# Change brief — GitHub integration

## Problem and outcome

The dashboard shows only local git state. Developers' top remote signals (per prior web research): open PRs with CI status, open issues. `gh` CLI is authenticated on this machine with full scope — zero new deps, zero token management.

**Outcome:** A GitHub tab in the repo detail view showing open PRs (number, title, branch, CI rollup badge, link-out) and open issues (number, title, link-out). Repos without a github.com remote show no tab content (graceful absence, not an error).

## Acceptance criteria

**AC-1 — PRs with CI badges**
On tink-route detail → GitHub tab: shows 3 open PRs, each with number, title, branch, and a CI badge (✓ all passing / ✗ failing / … pending / — no checks). Clicking opens the PR on github.com in a new tab.

**AC-2 — Open issues**
Same tab: open issue count + list (number, title, link-out).

**AC-3 — Non-GitHub repos degrade gracefully**
A repo with no origin or a non-github remote shows "No GitHub remote" empty state — no error, no spinner forever.

**AC-4 — Caching bounds API calls**
Repeated tab visits within 60s do not re-invoke `gh`. Verify by checking debug timing or code inspection: in-process TTL cache keyed by repo path.

**AC-5 — All existing tests still pass**
```sh
python3 -m pytest tests/ -v
```

## Approach

New `src/repo_root_tracker/github.py`:
- `get_github_info(path) -> GithubInfo | None` — None when no github remote
- Detect: `git remote get-url origin`, match `github.com[:/]owner/repo`
- Fetch: `gh pr list --json number,title,headRefName,url,statusCheckRollup` + `gh issue list --json number,title,url` (both with `--limit 20`)
- Roll up checks per PR: all-success → pass, any failure → fail, any pending → pending, empty → none
- Module-level TTL cache (60s) keyed by resolved path

Endpoint: `GET /api/github?path=` → 200 JSON, 404 if not tracked, 200 with `{"has_github": false}` if no remote.

UI: GitHub tab in detail view. PR rows with CI badge + branch tag + external-link. Issue rows. Header shows repo `owner/name` linking to github.com.

## Risks and verification

| Risk | Mitigation |
|---|---|
| `gh` not installed / not authenticated | Catch failure, return `has_github: false` with `gh_unavailable: true`; UI shows setup hint |
| Rate limits on many repos | 60s TTL cache; fetch only when tab is opened, not on list load |
| Slow `gh` calls block UI | Tab shows spinner; fetch is async like status |
| Private repos / permission errors | Treat as unavailable, same graceful path |

Verification: `pytest tests/` including new `test_github.py` (parsing + cache + endpoint with mocked gh).
