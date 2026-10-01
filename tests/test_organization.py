"""Organization HTTP contract and durable storage regressions."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
from io import BytesIO
from http.client import HTTPResponse
from pathlib import Path
import threading

import pytest

from repo_root_tracker import organization as org, server


class MemorySocket:
    """Exercise BaseHTTPRequestHandler's HTTP parser without binding a port."""
    def __init__(self, data):
        self.data = data
        self.output = BytesIO()

    def makefile(self, *args):
        return BytesIO(self.data)

    def sendall(self, data):
        self.output.write(data)


@contextmanager
def running_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler, bind_and_activate=False)
    try:
        yield httpd
    finally:
        httpd.server_close()


@pytest.fixture
def config(tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    monkeypatch.setenv("RRT_CONFIG_DIR", str(cfg))
    monkeypatch.setattr(server, "CONFIG_DIR", cfg)
    return cfg


@pytest.fixture
def api(config):
    with running_server() as url:
        yield url


def request(httpd, payload=None, *, raw=None, headers=None):
    if payload is not None:
        raw = json.dumps(payload).encode()
    method = "GET" if raw is None else "PUT"
    headers = {"Host": "127.0.0.1", **(headers or {})}
    if raw is not None:
        headers.setdefault("Content-Length", str(len(raw)))
    lines = [f"{method} /api/organization HTTP/1.1", *(f"{k}: {v}" for k, v in headers.items())]
    sock = MemorySocket(("\r\n".join(lines) + "\r\n\r\n").encode() + (raw or b""))
    server.Handler(sock, ("127.0.0.1", 12345), httpd)
    response = HTTPResponse(MemorySocket(sock.output.getvalue()))
    response.begin()
    body = response.read()
    return response.status, json.loads(body) if body.startswith(b'{') else body.decode()


def payload(base=0):
    return {"version": 1, "base_revision": base, "pins": ["/repo"],
            "collections": [{"id": "work", "name": "Work"}],
            "assignments": {"/repo": "work", "/no-longer-tracked": "work"},
            "grouping": "folder", "sort": "recent"}


def test_get_missing_and_put_round_trip(api, config):
    code, state = request(api)
    assert code == 200 and state == org.empty()
    assert not config.exists()  # Reads never create a file or directory.
    code, saved = request(api, payload())
    assert code == 200 and saved["revision"] == 1 and saved["exists"] is True
    assert request(api) == (200, saved)
    disk = json.loads((config / "organization.json").read_text())
    assert disk == {k: v for k, v in saved.items() if k != "exists"}
    assert "base_revision" not in disk
    assert saved["assignments"]["/no-longer-tracked"] == "work"
    assert list(config.glob("*.tmp")) == []


def test_revision_increments_and_stale_write_does_not_replace(api):
    assert request(api, payload())[1]["revision"] == 1
    newer = payload(1)
    newer["pins"] = ["/new"]
    code, current = request(api, newer)
    assert code == 200 and current["revision"] == 2
    assert request(api, payload()) == (409, current)
    assert request(api) == (200, current)


@pytest.mark.parametrize("change", [
    {"version": 2}, {"version": True}, {"base_revision": True}, {"base_revision": -1},
    {"pins": "bad"}, {"pins": [1]}, {"collections": {}},
    {"collections": [{"id": "a", "name": "A"}, {"id": "a", "name": "B"}]},
    {"collections": [{"id": "a", "name": "A"}, {"id": "b", "name": " a "}]},
    {"collections": [{"id": "", "name": "Empty"}]},
    {"collections": [{"id": "a", "name": " "}]},
    {"collections": [{"id": "a", "name": "A", "extra": True}]},
    {"assignments": []}, {"assignments": {"/repo": 3}},
    {"grouping": "bad"}, {"grouping": []}, {"sort": None},
    {"collapsed": []}, {"githubEnabled": True}, {"revision": 0},
])
def test_invalid_payload_changes_nothing(api, change):
    data = payload()
    data.update(change)
    code, state = request(api, data)
    assert code == 400 and state["error"]
    assert request(api) == (200, org.empty())


@pytest.mark.parametrize("raw", [b'[]', b'null', b'{broken', b'\xff', b'{}', b' ' * (org.MAX_BYTES + 1)], ids=["array", "null", "broken", "encoding", "missing-fields", "oversized"])
def test_invalid_json_and_oversized_requests(api, raw):
    code, state = request(api, raw=raw)
    assert code == 400 and state["error"]
    assert request(api) == (200, org.empty())


def test_host_guard_for_get_and_put(api):
    for data in (None, payload()):
        assert request(api, data, headers={"Host": "evil.example"})[0] == 403
    assert request(api) == (200, org.empty())


@pytest.mark.parametrize("content", [b'{broken', b'\xff', b'[]', b'{"version": 99}',
                                      json.dumps({**org.empty(), "exists": True}).encode()])
def test_corrupt_file_is_error_and_never_overwritten(api, config, content):
    config.mkdir()
    path = config / "organization.json"
    path.write_bytes(content)
    for data in (None, payload()):
        code, state = request(api, data)
        assert code == 500 and "organization.json" in state["error"]
    assert path.read_bytes() == content


def test_unreadable_file_is_explicit_error(api, config, monkeypatch):
    original = Path.read_bytes

    def denied(path):
        if path == config / "organization.json":
            raise PermissionError("Read permission denied")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", denied)
    for data in (None, payload()):
        code, state = request(api, data)
        assert code == 500 and "Could not read" in state["error"]


def test_unwritable_directory_is_explicit_error(api, config):
    config.mkdir()
    config.chmod(0o500)
    try:
        code, state = request(api, payload())
        assert code == 500 and "permissions" in state["error"]
        assert not (config / "organization.json").exists()
    finally:
        config.chmod(0o700)


def test_failed_atomic_replace_preserves_previous_file(api, config, monkeypatch):
    assert request(api, payload())[0] == 200
    before = (config / "organization.json").read_bytes()

    def fail_replace(*args):
        raise PermissionError("Replace denied")

    monkeypatch.setattr(Path, "replace", fail_replace)
    code, state = request(api, payload(1))
    assert code == 500 and state["error"]
    assert (config / "organization.json").read_bytes() == before
    assert list(config.glob("*.tmp")) == []


def test_persistence_across_new_server_instance(config):
    with running_server() as first:
        code, state = request(first, payload())
        assert code == 200
    with running_server() as second:
        assert request(second) == (200, state)


def test_concurrent_puts_have_one_winner_and_retries_preserve_all_pins(api):
    barrier = threading.Barrier(6)

    def write(index):
        data = payload()
        data["pins"] = [f"/repo-{index}"]
        barrier.wait(timeout=5)
        return request(api, data)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(write, range(6)))
    assert sorted(code for code, _ in results) == [200, 409, 409, 409, 409, 409]
    winner = next(state for code, state in results if code == 200)
    assert all(state == winner for _, state in results)

    def append(index):
        for _ in range(30):
            _, state = request(api)
            data = {k: deepcopy(v) for k, v in state.items() if k not in ("revision", "exists")}
            data["base_revision"] = state["revision"]
            if f"/extra-{index}" not in data["pins"]:
                data["pins"].append(f"/extra-{index}")
            code, _ = request(api, data)
            if code == 200:
                return
            assert code == 409
        pytest.fail("Concurrent retries never completed")

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(append, range(6)))
    code, state = request(api)
    assert code == 200 and state["revision"] == 7
    assert set(state["pins"]) == set(winner["pins"]) | {f"/extra-{i}" for i in range(6)}


@pytest.mark.parametrize("headers", [
    {"Content-Length": "bad"}, {"Content-Length": "-1"}, {"Content-Length": "0"},
    {"Content-Length": str(org.MAX_BYTES + 1)}, {"Transfer-Encoding": "chunked"},
])
def test_invalid_request_framing_is_rejected_before_reading(api, headers):
    code, state = request(api, payload(), headers=headers)
    assert code == 400 and state["error"]
    assert request(api) == (200, org.empty())


def test_broken_storage_symlink_is_not_empty(api, config):
    config.mkdir()
    path = config / "organization.json"
    path.symlink_to(config / "missing-backup")
    for data in (None, payload()):
        code, state = request(api, data)
        assert code == 500 and "Could not read" in state["error"]
    assert path.is_symlink()


def test_unicode_organization_remains_readable(api):
    data = payload()
    data["collections"][0]["name"] = "仕事 🌱"
    code, state = request(api, data)
    assert code == 200 and state["collections"] == data["collections"]
    assert request(api) == (200, state)


def test_deeply_nested_json_returns_explicit_error(api, config):
    raw = b'[' * 2000 + b'0' + b']' * 2000
    code, state = request(api, raw=raw)
    assert code == 400 and state["error"]
    config.mkdir()
    (config / "organization.json").write_bytes(raw)
    code, state = request(api)
    assert code == 500 and "Invalid organization.json" in state["error"]
