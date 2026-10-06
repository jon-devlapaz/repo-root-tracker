"""The git-golden definition from AGENTS.md, as a pure function of facts about one repository."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

MAIN = "main"
GOLDEN = "golden"
PENDING_CI = "golden pending CI"
NOT_GOLDEN = "not golden"
WORKTREE = "worktree"

# passing/failing/pending come from the latest CI run on main; the rest mean it could not be judged.
CI_NOTES = {
    "pending": "CI on main is still running",
    "unknown": "CI result is unavailable (gh missing, offline, or no run on the current commit)",
    "none": "no GitHub remote, so CI cannot be checked",
    "unchecked": "CI not checked yet",
}


@dataclass
class Verdict:
    status: str
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def headline(self) -> str:
        return self.reasons[0] if self.reasons else (self.notes[0] if self.notes else "")

    def to_dict(self) -> dict:
        return {**asdict(self), "headline": self.headline}


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _named(kind: str, names: list[str]) -> str:
    """Short enough to scan: the names for one or two, a count beyond that (the page lists them all in the row detail)."""
    if len(names) <= 2:
        return f"other {kind}{'' if len(names) == 1 else 'es'}: {', '.join(names)}"
    return f"{len(names)} other {kind}es"


def evaluate(
    *,
    branch: str,
    changed: int,
    local_branches: list[str],
    remote_branches: list[str],
    has_origin: bool,
    other_worktrees: list[str],
    ahead: int,
    behind: int,
    has_upstream: bool,
    ci: str = "unchecked",
) -> Verdict:
    """Apply every condition; the first failing reason is the headline, all are listed.

    Open issues and pull requests never count. CI that cannot be judged is a note, never a failure.
    """
    reasons: list[str] = []
    if branch != MAIN:
        reasons.append(f"on {branch}, not {MAIN}")
    if changed:
        reasons.append(f"{_plural(changed, 'uncommitted change')}")
    other_local = sorted(b for b in local_branches if b != MAIN)
    if other_local:
        reasons.append(_named("local branch", other_local))
    if not has_origin:
        reasons.append("no origin remote")
    else:
        origin_main = f"origin/{MAIN}"
        other_remote = sorted(b for b in remote_branches if b != origin_main)
        if other_remote:
            reasons.append(_named("remote branch", other_remote))
        if origin_main not in remote_branches:
            reasons.append(f"{origin_main} not found (not fetched yet?)")
    if other_worktrees:
        reasons.append(f"{_plural(len(other_worktrees), 'extra worktree')}")
    if has_origin and branch == MAIN:
        if not has_upstream:
            reasons.append(f"{MAIN} has no upstream")
        elif ahead or behind:
            reasons.append(f"not even with origin/{MAIN} (ahead {ahead}, behind {behind})")
    if ci == "failing":
        reasons.append("latest CI run on main failed")
    if reasons:
        return Verdict(NOT_GOLDEN, reasons)
    if ci == "passing":
        return Verdict(GOLDEN)
    return Verdict(PENDING_CI, notes=[CI_NOTES.get(ci, CI_NOTES["unknown"])])


def worktree_verdict() -> Verdict:
    """A linked worktree is judged through its project's main checkout, not on its own."""
    return Verdict(WORKTREE, notes=["linked worktree: golden is judged on the project's main checkout"])
