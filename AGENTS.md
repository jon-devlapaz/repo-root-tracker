This project uses Tink to manage Agent Skills under `.agents/skills/`.


## git-golden

A repository is `git-golden` when all of the following are true:

- It is checked out on `main` with a clean working tree.
- Local `main` is even with `origin/main`.
- GitHub has no open pull requests and no open issues.
- The latest `CI` run on `main` succeeded.

<!-- AI-Native SDLC Router -->
## SDLC Workspace
- Read `_system/SDLC.md` for setup, evidence boundaries, and recovery.
- Inspect `_system/scripts/status.sh` before creating a run.
- Read `stages/<stage-name>/CONTEXT.md` before processing a stage.
- Keep factory references in `_shared/` unchanged during feature runs.
- Use separate worktrees or clones for code-writing runs.
<!-- End AI-Native SDLC Router -->
