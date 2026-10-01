# repo-root-tracker\n\nFind the git repository root by walking up the filesystem.

## Tests

`python -m pytest tests/ -q` runs the deterministic backend and browser suites (no network, no GitHub account needed).

The live GitHub integration test is opt-in and read-only. It never creates, closes or pushes anything and does not depend on how many PRs or issues the repo has:

```bash
RRT_LIVE_GITHUB=1 RRT_LIVE_GITHUB_REPO=<owner>/<name> python -m pytest tests/test_github.py::test_endpoint_live_github
```

Not requested: it is skipped and says why. Requested but `RRT_LIVE_GITHUB_REPO` is missing or malformed, or `gh` is not authenticated: it fails, so a requested run is never green by skipping.
