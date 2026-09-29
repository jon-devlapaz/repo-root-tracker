# pre-intent: repo-root-tracker

**Originator:** jondev  
**Date:** 2026-09-29  
**Revision:** r1  
**Status:** pre-intent — confirmed for intake; not approved for implementation

---

## Problem Statement

Every tool in the tink ecosystem that operates on a project (tink, tink-route, future tools) needs to know the git repository root. Currently:

- `tink-route/src/tink_route/cli.py` uses `Path.cwd()` directly, implicitly assuming the process is always started from the repo root — an assumption that silently breaks when invoked from a subdirectory.
- `tink/src/lib.rs` accepts a caller-supplied `cwd` and passes it directly to all skill operations with no `.git`-walking — the same silent-wrong-root risk.
- No shared, correct, testable root-discovery utility exists in the ecosystem.

The gap matters because skills are installed into `.agents/skills/` at the project root; using the wrong root means installing into or reading from the wrong directory.

---

## Proposed Outcome

A standalone Python 3.11+ package, `repo-root-tracker`, that:

1. Walks up the filesystem from a given path until it finds a `.git` directory **or** `.git` file (worktree pointer), then returns that directory as the repository root.
2. Raises a clear exception (library) / exits nonzero with an error message (CLI) when no `.git` is found before the filesystem root.
3. Is importable as a Python library by tink-route (zero subprocess overhead).
4. Exposes a CLI entry point for use by tink (Rust) and shell scripts via subprocess.
5. Has zero third-party dependencies; stdlib only.

---

## Acceptance Criteria

Each criterion is independently verifiable without re-reading this document.

**AC-1 — Library root discovery from subdirectory**
```sh
cd /tmp && mkdir -p testrepo/subdir && cd testrepo && git init && cd subdir
python3 -c "from repo_root_tracker import find_root; import pathlib; print(find_root(pathlib.Path.cwd()))"
```
Expected output: the absolute path of `/tmp/testrepo` (or equivalent resolved path).
Runs in: any POSIX shell after `pip install repo-root-tracker`.

**AC-2 — CLI root discovery from subdirectory**
```sh
cd /tmp/testrepo/subdir
repo-root-tracker
```
Expected output: the absolute path of `/tmp/testrepo`, printed to stdout, exit code 0.
Runs in: any POSIX shell after `pip install repo-root-tracker`.

**AC-3 — Fail-fast when no git repo**
```sh
cd /tmp && mkdir notarepo && cd notarepo
repo-root-tracker
```
Expected output: a non-empty error message on stderr, exit code nonzero (1 or 2).
Runs in: any POSIX shell after `pip install repo-root-tracker`.

**AC-4 — Worktree support (.git file)**
```sh
cd /tmp/testrepo && git worktree add /tmp/testrepo-wt HEAD && cd /tmp/testrepo-wt
repo-root-tracker
```
Expected output: the absolute path of `/tmp/testrepo-wt`, exit code 0.  
(The worktree root is its own `.git`-file-containing directory, correctly returned.)
Runs in: any POSIX shell after `pip install repo-root-tracker`.

**AC-5 — Zero third-party dependencies**
```sh
pip show repo-root-tracker
```
Expected output: `Requires:` field is empty or absent.
Runs in: any POSIX shell after `pip install repo-root-tracker`.

---

## Affected Users and Systems

- **tink-route** (`~/dev/active/tink-route/src/tink_route/cli.py`) — primary first consumer; will replace `Path.cwd()` calls with `find_root(Path.cwd())`.
- **tink** (`~/dev/active/tink/src/lib.rs`) — secondary CLI consumer; will invoke `repo-root-tracker` via subprocess as needed.
- **Developers** running tink/tink-route from project subdirectories.
- **Automated agent pipelines** (Pi, Claude Code, Cursor) invoking tink-route from non-root directories.

---

## Constraints and Boundaries

- **Python 3.11+ only** — matches tink-route's `requires-python = ">=3.11"` (`tink-route/pyproject.toml`).
- **Zero third-party dependencies** — stdlib only; matches tink-route's established zero-dep constraint.
- **No caching at v1** — always walk the filesystem fresh; no in-process memoization, no persistence.
- **Not a project manager** — does not create, modify, or verify git repos; read-only discovery only.
- **Not embedded in tink-route** — distributed as a standalone pip-installable package, not as an inline module.

---

## Accepted Decisions

| Decision | Answer | Authority | Rationale |
|---|---|---|---|
| Primary purpose | Walk up from a given path to find `.git`; return root; library + CLI | delegated | No shared root resolver exists in ecosystem; `tink-route/cli.py` uses `Path.cwd()` directly |
| Implementation language | Python | user | Matches tink-route runtime; zero-dep stdlib walker is trivial; Rust would require FFI or subprocess boundary |
| First consumers | tink-route (library import); tink (CLI subprocess) | delegated | tink-route is same Python runtime; tink is Rust — CLI invocation is the only boundary |
| Delivery interface | Both library and CLI | delegated | tink-route imports directly; tink/shell scripts use CLI |
| Distribution | Standalone pip package (hatchling) | delegated | Jev p=0.79; matches ecosystem pattern of independently installable tools |
| Caching | None at v1 — always walk fresh | delegated | Jev p=0.73; tink-route is a single-invocation CLI process; no repeated lookups |
| Failure mode | Exception (library) / exit nonzero (CLI) | delegated | Jev p=0.72; consistent with tink's fail-fast `Result` pattern |
| Worktree `.git` file | Treated same as `.git` directory | evidence | Jev noul p=0.84; git worktree spec; tink `check.rs:194` uses directory form only — confirming gap |

---

## Evidence and Uncertainty

**Grounded in (paths read this session):**
- `~/dev/active/tink-route/src/tink_route/cli.py`
- `~/dev/active/tink-route/pyproject.toml`
- `~/dev/active/tink-route/src/tink_route/core/engine.py`
- `~/dev/active/tink-route/src/tink_route/core/constants.py`
- `~/dev/active/tink-route/src/tink_route/core/validation.py`
- `~/dev/active/tink-route/src/tink_route/adapters/ledger.py`
- `~/dev/active/tink/Cargo.toml`
- `~/dev/active/tink/src/lib.rs`
- `~/dev/active/tink/src/git.rs`
- `~/dev/active/tink/src/home.rs`
- `~/dev/active/tink/src/init.rs`
- `~/dev/active/tink/src/check.rs` (line 194 — `.git` directory test)

**Unverified hypotheses / assumptions:**
- PROVISIONAL: tink-route integration (replacing `Path.cwd()`) has no test coverage for the root-discovery path — not verified; downstream risk.
- PROVISIONAL: tink (Rust) consumers would invoke `repo-root-tracker` via CLI subprocess; actual integration design is deferred to implementation.

**Not read this session (named risks):**
- `tink-route/tests/` — test coverage for `Path.cwd()` usage unknown; integration tests may need updates when tink-route adopts this library.
- `tink/tests/` — tink's test assumptions about `cwd == project_root` are unverified.

---

## Suggested First Slice

_Proposal only — seeds Stage 01 approach drafting, does not authorize work._

```sh
cd ~/dev/active/repo-root-tracker
# Initialize a Python package
python3 -m venv .venv && source .venv/bin/activate
pip install hatchling
```

Implement `src/repo_root_tracker/__init__.py` with a single `find_root(start: Path) -> Path` function and a `__main__.py` CLI entry point. Wire up `pyproject.toml` matching `tink-route`'s pattern. Write tests for AC-1 through AC-5 before any tink-route integration.

---

## Risks and Verification

| Risk | Mitigation |
|---|---|
| Symlink traversal during root walk could escape repo boundary | Refuse symlinks in `.parent` walk or resolve before walking; verify with a test |
| `.git` file content is not validated — a non-worktree file named `.git` would give a false positive | Read and validate `gitdir:` prefix before accepting `.git` file as worktree pointer |
| tink-route `Path.cwd()` replacement introduces a regression if called outside a repo in a pipeline | AC-3 covers this; tink-route integration must add a test for the outside-repo error path |
| Caching absence may be revisited if consumers call `find_root` in a hot loop | Non-issue at v1; add `functools.lru_cache` at v1.1 if profiling shows it matters |

---

## Open Questions and Deferrals

- **Module name:** `repo_root_tracker` (underscore form of the package name) — assumed, not confirmed. Non-blocking; change before first release.
- **PyPI publication:** not in scope for v1 — install from source or local path. Revisit when tink-route declares it as a dependency.
- **tink integration design:** deferred — how tink (Rust) invokes the CLI is an implementation decision for Stage 01. Non-blocking for this pre-intent.

---

## Migration Footer

| Item | Owner / Gate / Loop |
|---|---|
| Module name (Q2 — minor) | Developer — confirm before first `pip install`; loop: Stage 01 design |
| PyPI publication (Q3 — deferred) | Developer — revisit when first external consumer declares dependency |
| tink-route test coverage (unread) | Loop: Stage 03 build — read `tink-route/tests/` before integration |
| Symlink safety (breeding ground) | Guardrail: refuse symlinks in walk; test before merge |

---

## Downstream Handoff

`pre-intent.md` is the handoff artifact. The session ledger and viewer are interview records only. This document is discovery input — not an implementation plan, approved specification, or review receipt.

Downstream stages (design, build, test) own subsequent specification and implementation approval. Do not preselect a downstream profile or fabricate stage approval.
