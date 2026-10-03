This project uses Tink to manage Agent Skills under `.agents/skills/`.


## git-golden

A repository is `git-golden` when all of the following are true:

- It is checked out on `main` with a clean working tree.
- `main` is the only branch, locally and on `origin`: no other local branches, no other remote branches, and no extra worktrees holding branches.
- Local `main` is even with `origin/main`.
- Open issues and pull requests are tracked separately; they do not make the checkout unclean.
- The latest `CI` run on `main` succeeded.

<!-- AI-Native SDLC Router -->
## SDLC Workspace
- Read `_system/SDLC.md` for setup, evidence boundaries, and recovery.
- Inspect `python3 _system/scripts/sdlc.py status` before creating a run.
- Read `stages/<stage-name>/CONTEXT.md` before processing a stage.
- Keep factory references in `_shared/` unchanged during feature runs.
- Use separate worktrees or clones for code-writing runs.
- Stage skills: see the Skills section of the current stage's CONTEXT.md.
- Need a specialised skill mid-task? `tink-route --receipt runs/<slug>/skills.jsonl "<what you need>"` prints it on stdout; exit 1 means none fits, so continue without one.
<!-- End AI-Native SDLC Router -->
