"""Read-only validation of this planning packet; does not approve or test the product."""
import hashlib
import json
from pathlib import Path

run = Path(__file__).resolve().parent
root = run.parents[1]
manifest = json.loads((run / "inputs/manifest.json").read_text())
for name, expected in manifest["files"].items():
    assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, name
metadata = json.loads((run / "run.json").read_text())
assert metadata["seed_contract"]["sha256"] == manifest["files"]["seed-contract.md"]
checklist = json.loads((run / "checklist.json").read_text())
assert checklist["schema"] == 1 and checklist["items"]
ids = set()
for item in checklist["items"]:
    assert set(item) <= {"id", "description", "verify", "check"}
    assert all(isinstance(item.get(k), str) and item[k].strip() for k in ("id", "description", "verify"))
    assert item["id"] not in ids
    ids.add(item["id"])
    if "check" in item:
        check = item["check"]
        assert check["argv"] and check["timeout_seconds"] > 0
        for arg in check["argv"]:
            if arg.startswith("tests/"):
                assert (root / arg).is_file(), arg
assert (run / "brief.md").is_file() and (run / "handoff.md").is_file()
print(f"Planning input hashes and {len(ids)} checklist definitions validated; no product tests or approvals.")
