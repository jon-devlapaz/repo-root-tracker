"""CLI entry point for repo-root-tracker."""

from __future__ import annotations

import sys
from pathlib import Path

from . import NotARepositoryError, find_root


def main() -> None:
    try:
        root = find_root(Path.cwd())
    except NotARepositoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(root)


if __name__ == "__main__":
    main()
