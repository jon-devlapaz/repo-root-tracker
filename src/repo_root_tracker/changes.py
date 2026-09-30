from dataclasses import dataclass


@dataclass
class ChangedFile:
    path: str = ""
    staged: bool = False
    untracked: bool = False
    kind: str = "modified"
    index_kind: str = ""
    worktree_kind: str = ""
    original_path: str = ""


def parse_changes(output: str) -> list[ChangedFile]:
    names = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed", "C": "copied", "T": "type changed", "U": "conflicted"}
    records = iter(output.split("\0"))
    changes = []
    for record in records:
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise ValueError("Malformed Git porcelain status")
        x, y = record[:2]
        if x + y == "!!":
            continue
        original = next(records, "") if x in "RC" or y in "RC" else ""
        if (x in "RC" or y in "RC") and not original:
            raise ValueError("Git rename status is missing its source path")
        untracked = x + y == "??"
        conflicted = x + y in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
        index_kind = names.get(x, "")
        worktree_kind = names.get(y, "")
        kind = "untracked" if untracked else "conflicted" if conflicted else (
            "renamed" if "R" in (x, y) else "copied" if "C" in (x, y) else worktree_kind or index_kind
        )
        if not kind:
            raise ValueError("Unknown Git porcelain status")
        changes.append(ChangedFile(
            path=record[3:], staged=x not in {" ", "?", "!"} and not conflicted,
            untracked=untracked, kind=kind, index_kind=index_kind,
            worktree_kind=worktree_kind, original_path=original,
        ))
    return changes
