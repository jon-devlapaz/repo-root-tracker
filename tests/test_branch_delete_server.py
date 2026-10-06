"""POST /api/branch/delete: who may ask, what is refused, what a delete does and writes down, and how to undo it."""

import http.client
import json
import subprocess
import threading
from pathlib import Path

import pytest
from gitfix import commit, git

from repo_root_tracker import branch_delete as bd
from repo_root_tracker import server as srv
from repo_root_tracker import status as status_module


@pytest.fixture()
def live(branch_world, monkeypatch, tmp_path):
    repo, bare = branch_world
    root = repo.parent
    monkeypatch.setattr(bd, "pull_requests", lambda s, b, c: [])
    monkeypatch.setattr(status_module, "_github_remote", lambda p: "o/r")
    log = tmp_path / "logs" / "deleted.log"
    monkeypatch.setattr(bd, "LOG", log)
    server = srv.make_server(0, [str(root)])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def call(method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        conn.request(method, path, body=data, headers={"Content-Type": "application/json", **(headers or {})})
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = raw
        return response.status, parsed

    def ask(scope, branch, sha=None, path=None, **extra):
        sha = sha or git(repo, "rev-parse", ("origin/" if scope == "remote" else "") + branch)
        return call("POST", "/api/branch/delete", body={"path": path or str(repo.resolve()), "scope": scope, "branch": branch, "sha": sha}, **extra)

    call("GET", "/api/scan")
    call.repo, call.bare, call.log, call.ask, call.server = repo, bare, log, ask, server
    yield call
    server.shutdown()
    server.server_close()


def remote_branches(live):
    return set(git(live.repo, "ls-remote", "--heads", "origin").replace("refs/heads/", "").split()[1::2])


def log_lines(live):
    return [line.split("\t") for line in live.log.read_text().splitlines()] if live.log.exists() else []


def test_a_merged_remote_branch_is_deleted_and_only_that_one(live):
    sha = git(live.repo, "rev-parse", "origin/done")
    status, body = live.ask("remote", "done")
    assert status == 200 and body["deleted"] and body["sha"] == sha
    assert remote_branches(live) == {"main", "wip"}
    assert "origin/done" not in git(live.repo, "branch", "-r")  # our copy is forgotten too
    assert git(live.repo, "rev-parse", "wip") and git(live.repo, "rev-parse", "origin/wip")


def test_a_merged_local_branch_is_deleted_and_only_that_one(live):
    status, body = live.ask("local", "done")
    assert status == 200 and body["deleted"]
    assert "done" not in git(live.repo, "branch", "--format=%(refname:short)").split()
    assert "wip" in git(live.repo, "branch", "--format=%(refname:short)").split()
    assert remote_branches(live) == {"main", "done", "wip"}


def test_every_attempt_is_written_down_before_and_after(live):
    sha = git(live.repo, "rev-parse", "origin/done")
    live.ask("remote", "done")
    rows = log_lines(live)
    assert [r[1] for r in rows] == ["attempt", "deleted"]
    for row in rows:
        assert row[2] == str(live.repo.resolve()) and row[3:6] == ["remote", "done", sha]


def test_the_recovery_command_brings_the_branch_back_at_the_same_sha(live):
    sha = git(live.repo, "rev-parse", "origin/done")
    _, body = live.ask("remote", "done")
    subprocess.run(body["recovery"], shell=True, check=True, cwd=live.repo, capture_output=True)  # exactly as the page shows it
    assert git(live.bare, "rev-parse", "refs/heads/done") == sha
    local_sha = git(live.repo, "rev-parse", "done")
    _, local = live.ask("local", "done")
    assert "done" not in git(live.repo, "branch", "--format=%(refname:short)").split()
    subprocess.run(local["recovery"], shell=True, check=True, cwd=live.repo, capture_output=True)
    assert git(live.repo, "rev-parse", "done") == local_sha


def test_a_failed_delete_is_logged_as_failed_and_leaves_everything(live):
    git(live.repo, "remote", "set-url", "origin", str(live.bare) + "-gone")
    status, body = live.ask("remote", "done")
    assert status == 502 and "git said no" in body["error"]
    assert [r[1] for r in log_lines(live)] == ["attempt", "FAILED"]
    assert git(live.bare, "rev-parse", "refs/heads/done")


def test_an_unwritable_log_blocks_the_delete(live):
    live.log.parent.mkdir(parents=True)
    live.log.mkdir()  # a directory where the log file should be
    status, body = live.ask("remote", "done")
    assert status == 500 and "deletion log" in body["error"]
    assert remote_branches(live) == {"main", "done", "wip"}


def test_a_stale_sha_deletes_nothing(live):
    status, body = live.ask("remote", "done", sha="0" * 40)
    assert status == 409 and "moved" in body["error"]
    assert remote_branches(live) == {"main", "done", "wip"} and log_lines(live) == []


def test_the_branch_moving_on_the_remote_after_the_page_looked_is_caught_by_the_lease(live, tmp_path):
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(live.bare), str(other)], check=True, capture_output=True)
    git(other, "switch", "-q", "done")
    commit(other, "extra.txt", message="someone else pushed")
    git(other, "push", "-q", "origin", "done")
    status, body = live.ask("remote", "done")  # our refs are old: the tool still thinks done is merged at the old tip
    assert status == 502
    assert "done" in remote_branches(live)
    assert [r[1] for r in log_lines(live)] == ["attempt", "FAILED"]


@pytest.mark.parametrize("branch", ["-D", "--force", "a..b", "", "main", "nope"])
def test_bad_or_protected_branch_names_delete_nothing(live, branch):
    status, _ = live.ask("remote", branch, sha="a" * 40)
    assert status == 409
    assert remote_branches(live) == {"main", "done", "wip"}


def test_unmerged_work_is_refused(live):
    status, body = live.ask("remote", "wip")
    assert status == 409 and "not on main" in body["error"] and "wip" in remote_branches(live)


def test_an_open_pull_request_is_refused(live, monkeypatch):
    monkeypatch.setattr(bd, "pull_requests", lambda s, b, c: [{"number": 3, "state": "OPEN", "headRefName": b, "headRefOid": "x"}])
    status, body = live.ask("remote", "done")
    assert status == 409 and "#3" in body["error"] and "done" in remote_branches(live)


def test_a_path_the_scan_did_not_find_is_404(live, tmp_path):
    status, _ = live.ask("remote", "done", path=str(tmp_path))
    assert status == 404


@pytest.mark.parametrize("body", [b"not json", b"{}", b'{"path": 1, "scope": "x", "branch": "b", "sha": "s"}', b"[]"])
def test_malformed_requests_are_400(live, body):
    assert live("POST", "/api/branch/delete", body=body)[0] == 400


def test_the_wrong_content_type_is_400(live):
    assert live("POST", "/api/branch/delete", {"Content-Type": "text/plain"}, body=b"{}")[0] == 400


def test_a_wrong_host_a_cross_site_page_and_a_foreign_origin_are_refused(live):
    for headers in ({"Host": "evil.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Origin": "http://evil.example"}):
        assert live.ask("remote", "done", headers=headers)[0] == 403, headers
    assert remote_branches(live) == {"main", "done", "wip"}


def test_a_phone_on_the_network_cannot_delete_or_even_ask_what_is_deletable(live, monkeypatch):
    monkeypatch.setattr(srv, "LAN", True)
    monkeypatch.setattr(srv.Handler, "_peer", lambda self: "private")
    monkeypatch.setattr(srv, "_lan_hosts", {"192.168.9.9"})
    headers = {"Host": "192.168.9.9:7842"}
    assert live.ask("remote", "done", headers=headers)[0] == 403
    assert live("GET", "/api/branch/verdicts?path=" + str(live.repo.resolve()), headers)[0] == 403
    assert remote_branches(live) == {"main", "done", "wip"}


def test_verdicts_name_each_branch_and_its_sha(live):
    status, body = live("GET", "/api/branch/verdicts?path=" + str(live.repo.resolve()))
    v = body["verdicts"]
    assert status == 200 and v["remote:done"]["ok"] and not v["remote:wip"]["ok"] and v["remote:done"]["sha"] == git(live.repo, "rev-parse", "origin/done")
    assert live("GET", "/api/branch/verdicts?path=/etc")[0] == 404


def test_the_attempt_is_written_down_before_the_branch_is_touched_and_the_result_after(live, monkeypatch):
    seen = []
    real_log = bd._log

    def spy(handle, outcome, *rest):
        seen.append((outcome, "done" in remote_branches(live)))  # is the branch still on the remote at the moment of writing?
        real_log(handle, outcome, *rest)

    monkeypatch.setattr(bd, "_log", spy)
    assert live.ask("remote", "done")[0] == 200
    assert seen == [("attempt", True), ("deleted", False)]
