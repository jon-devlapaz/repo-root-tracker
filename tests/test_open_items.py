"""Open pull requests and issues: counts and numbers for display only. They never change the golden verdict."""

import http.client
import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from gitfix import git, with_origin

from repo_root_tracker import server as srv
from repo_root_tracker.github import ITEM_LIMIT, OpenItems, clear_cache, get_open_items


@pytest.fixture(autouse=True)
def cache():
    clear_cache()
    yield
    clear_cache()


def pr(number, title="a change", draft=False):
    return {"number": number, "title": title, "url": f"https://github.com/o/r/pull/{number}", "isDraft": draft, "headRefName": f"b{number}"}


def issue(number, title="a bug"):
    return {"number": number, "title": title, "url": f"https://github.com/o/r/issues/{number}"}


class Gh:
    def __init__(self, prs=(), issues=(), fail=()):
        self.prs, self.issues, self.fail, self.calls = list(prs), list(issues), set(fail), []

    def __call__(self, *args, cwd):
        self.calls.append(args)
        kind = args[0]
        if kind in self.fail:
            return None
        return self.prs if kind == "pr" else self.issues


def items_for(tmp_path, gh, refresh=True):
    with patch("repo_root_tracker.github._github_remote", return_value="o/r"), patch("repo_root_tracker.github._gh", side_effect=gh):
        return get_open_items(tmp_path, refresh=refresh)


def test_numbers_titles_links_and_draft_state_come_through(tmp_path):
    got = items_for(tmp_path, Gh(prs=[pr(12, "Add tron", draft=True), pr(7)], issues=[issue(45, "closure docs")]))
    assert got.available and got.repo == "o/r"
    assert [p["number"] for p in got.prs] == [12, 7] and got.prs[0] == {
        "number": 12, "title": "Add tron", "url": "https://github.com/o/r/pull/12", "draft": True, "branch": "b12"}
    assert got.issues == [{"number": 45, "title": "closure docs", "url": "https://github.com/o/r/issues/45"}]
    assert not got.prs_truncated and not got.issues_truncated and got.checked_at


def test_only_open_items_are_asked_for_and_only_two_calls_are_made(tmp_path):
    gh = Gh()
    items_for(tmp_path, gh)
    assert sorted(c[0] for c in gh.calls) == ["issue", "pr"]
    for call in gh.calls:
        assert "--state" in call and call[call.index("--state") + 1] == "open"
        assert call[call.index("--repo") + 1] == "github.com/o/r"


def test_long_lists_are_cut_and_say_so(tmp_path):
    got = items_for(tmp_path, Gh(prs=[pr(n) for n in range(ITEM_LIMIT + 5)], issues=[issue(n) for n in range(3)]))
    assert len(got.prs) == ITEM_LIMIT and got.prs_truncated and not got.issues_truncated


def test_gh_failing_is_unavailable_never_zero(tmp_path):
    assert items_for(tmp_path, Gh(fail={"pr", "issue"})).available is False
    half = items_for(tmp_path, Gh(prs=[pr(1)], fail={"issue"}), refresh=True)
    assert half.available and half.issues_known is False and half.prs_known is True and len(half.prs) == 1


def test_a_repo_without_a_github_remote_has_nothing_to_show(tmp_path):
    with patch("repo_root_tracker.github._github_remote", return_value=None):
        got = get_open_items(tmp_path, refresh=True)
    assert got.available is False and got.repo == "" and got.prs == [] and got.issues == []


def test_results_are_cached_until_refreshed(tmp_path):
    gh = Gh(prs=[pr(1)])
    items_for(tmp_path, gh)
    calls = len(gh.calls)
    items_for(tmp_path, gh, refresh=False)
    assert len(gh.calls) == calls
    gh.prs = [pr(1), pr(2)]
    assert len(items_for(tmp_path, gh, refresh=True).prs) == 2


# ---- through the server -------------------------------------------------------------------------------------------

@pytest.fixture()
def live(tmp_path, monkeypatch):
    root = tmp_path / "root"
    alpha, _ = with_origin(root, "alpha")
    server = srv.make_server(0, [str(root)])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def call(method, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        conn.request(method, path, headers=headers or {})
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw)

    call.alpha, call.port = alpha, port
    yield call
    server.shutdown()
    server.server_close()


def test_the_server_remembers_the_items_and_adds_them_to_status(live, monkeypatch):
    path = str(live.alpha.resolve())
    live("GET", "/api/scan")
    assert live("GET", "/api/repos/status?path=" + path)[1]["github"] is None
    stub = OpenItems(repo="o/r", prs=[{"number": 3, "title": "t", "url": "u", "draft": False, "branch": "b"}], issues=[], available=True,
                     checked_at="2026-10-06T10:00:00+00:00")
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: stub)
    status, body = live("GET", "/api/items?path=" + path)
    assert status == 200 and body["items"]["prs"][0]["number"] == 3
    again = live("GET", "/api/repos/status?path=" + path)[1]
    assert again["github"]["prs"][0]["number"] == 3 and again["github"]["checked_at"]


def test_open_pull_requests_and_issues_never_change_the_verdict(live, monkeypatch):
    path = str(live.alpha.resolve())
    live("GET", "/api/scan")
    before = live("GET", "/api/repos/status?path=" + path)[1]["golden"]
    stub = OpenItems(repo="o/r", prs=[{"number": n, "title": "t", "url": "u", "draft": False, "branch": "b"} for n in range(9)],
                     issues=[{"number": n, "title": "t", "url": "u"} for n in range(20)], available=True, checked_at="x")
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: stub)
    live("GET", "/api/items?path=" + path)
    assert live("GET", "/api/repos/status?path=" + path)[1]["golden"] == before


def test_only_scanned_paths_and_only_this_computer_may_ask(live, monkeypatch):
    calls = []
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: calls.append(p) or OpenItems())
    live("GET", "/api/scan")
    assert live("GET", "/api/items?path=/etc")[0] == 404 and live("GET", "/api/items")[0] == 400 and calls == []
    monkeypatch.setattr(srv.Handler, "_peer", lambda self: "private")
    monkeypatch.setattr(srv, "LAN", True)
    monkeypatch.setattr(srv, "_lan_hosts", {"192.168.9.9"})
    status, body = live("GET", "/api/items?path=" + str(live.alpha.resolve()), {"Host": "192.168.9.9"})
    assert status == 403 and calls == []  # it runs gh with the owner's login, so only the owner's computer may start it
    assert live("GET", "/api/items?path=" + str(live.alpha.resolve()) + "&x=1", {"Sec-Fetch-Site": "cross-site"})[0] == 403
