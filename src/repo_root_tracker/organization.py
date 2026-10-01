"""Versioned dashboard organization; one atomic writer per server process."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading

MAX_BYTES = 1024 * 1024
_LOCK = threading.Lock()
FIELDS = {"version", "pins", "collections", "assignments", "grouping", "sort"}


class StorageError(Exception):
    """Organization storage must never be mistaken for an empty workspace."""


def empty() -> dict:
    return {"version": 1, "revision": 0, "pins": [], "collections": [],
            "assignments": {}, "grouping": "collection", "sort": "name", "exists": False}


def validate(data: object, extra: str) -> dict:
    if not isinstance(data, dict) or set(data) != FIELDS | {extra}:
        raise ValueError(f"Expected shared organization fields and {extra}")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("Organization version must be 1")
    if type(data[extra]) is not int or data[extra] < 0:
        raise ValueError(f"{extra} must be a nonnegative integer")
    if not isinstance(data["pins"], list) or not all(isinstance(p, str) for p in data["pins"]):
        raise ValueError("pins must be an array of strings")
    collections = data["collections"]
    if not isinstance(collections, list):
        raise ValueError("collections must be an array")
    ids, names = set(), set()
    for c in collections:
        if (not isinstance(c, dict) or set(c) != {"id", "name"}
                or not isinstance(c["id"], str) or not c["id"].strip()
                or not isinstance(c["name"], str) or not c["name"].strip()):
            raise ValueError("Each collection needs a nonempty string id and name")
        if c["id"] in ids or c["name"].strip().lower() in names:
            raise ValueError("Collection ids and names must be unique")
        ids.add(c["id"])
        names.add(c["name"].strip().lower())
    assignments = data["assignments"]
    if not isinstance(assignments, dict) or not all(isinstance(v, str) for v in assignments.values()):
        raise ValueError("assignments must be an object of string collection ids")
    # Unknown paths and collection ids remain available for the offline fallback.
    if data["grouping"] not in ("collection", "folder", "project", "none"):
        raise ValueError("grouping must be collection, folder, project, or none")
    if data["sort"] not in ("name", "recent"):
        raise ValueError("sort must be name or recent")
    return data


def _read(config_dir: Path) -> dict:
    path = config_dir / "organization.json"
    try:
        raw = path.read_bytes()
    except FileNotFoundError as e:
        if path.is_symlink():
            raise StorageError(f"Could not read organization.json: {e}") from e
        return empty()
    except OSError as e:
        raise StorageError(f"Could not read organization.json: {e}") from e
    try:
        if len(raw) > MAX_BYTES:
            raise ValueError("file exceeds 1 MiB")
        data = validate(json.loads(raw), "revision")
    except (ValueError, UnicodeError, RecursionError) as e:
        raise StorageError(f"Invalid organization.json: {e}. Restore a valid backup.") from e
    return {**data, "exists": True}


def read(config_dir: Path) -> dict:
    with _LOCK:
        return _read(config_dir)


def update(config_dir: Path, payload: dict) -> tuple[int, dict]:
    validate(payload, "base_revision")
    with _LOCK:
        current = _read(config_dir)
        populated = bool(current["pins"] or current["collections"] or current["assignments"]
                         or current["grouping"] != "collection" or current["sort"] != "name")
        if (payload["base_revision"] != current["revision"]
                or payload["base_revision"] == 0 and current["exists"] and populated):
            return 409, current
        data = {k: payload[k] for k in FIELDS}
        data["revision"] = current["revision"] + 1
        encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise ValueError("Organization file exceeds 1 MiB")
        tmp = None
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="wb", dir=config_dir,
                                             prefix="organization-", suffix=".tmp", delete=False) as f:
                tmp = Path(f.name)
                f.write(encoded)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(config_dir / "organization.json")
        except OSError as e:
            raise StorageError(f"Could not save organization.json: {e}. Check config directory permissions.") from e
        finally:
            if tmp is not None:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass  # Preserve the original storage error if cleanup also fails.
        return 200, {**data, "exists": True}
