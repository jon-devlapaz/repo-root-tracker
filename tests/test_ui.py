"""End to end: the real server, real temporary git repos and a real browser."""

import shutil
import threading
import time
from pathlib import Path

import pytest
from gitfix import commit, git, init, with_origin
import atexit
import types

from playwright import sync_api as _real_playwright

_SHARED = {}


class _Browser:
    """The one real browser, shared by every test. Each test still gets its own pages and contexts; close() leaves it running."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def close(self):
        pass


def _shared_browser():
    if "browser" not in _SHARED:
        _SHARED["pw"] = _real_playwright.sync_playwright().start()
        _SHARED["browser"] = _SHARED["pw"].chromium.launch()
        atexit.register(lambda: (_SHARED["browser"].close(), _SHARED["pw"].stop()))
    return _Browser(_SHARED["browser"])


class _SyncPlaywright:
    chromium = types.SimpleNamespace(launch=lambda **_: _shared_browser())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


playwright = types.SimpleNamespace(sync_playwright=_SyncPlaywright)

from repo_root_tracker import branch_delete as bd
from repo_root_tracker import server as srv
from repo_root_tracker import status as status_module
from repo_root_tracker.github import CiState, OpenItems


def start(root, monkeypatch, ci="passing", auto_ci=False):
    head = lambda p: git(Path(p), "rev-parse", "refs/heads/main")  # a real CI result names the commit it ran on
    monkeypatch.setattr(srv, "get_default_branch_ci", lambda p, refresh=False: CiState(state=ci, repo="o/r", head_sha=head(p), checked_at="2026-10-06T10:00:00+00:00"))
    monkeypatch.setattr(status_module, "_github_remote", lambda p: "o/r")  # pretend each origin is on GitHub; no network is used
    monkeypatch.setattr(bd, "pull_requests", lambda slug, branch, cwd: [])  # and no pull request exists anywhere
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: OpenItems(repo="o/r", available=True, prs_known=True, issues_known=True,
                                                                              checked_at="2026-10-06T10:00:00+00:00"))
    server = srv.make_server(0, [str(root)], auto_ci=auto_ci)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def build_world(root):
    """The shared starting point: four real repos with real bare remotes."""
    alpha, bare = with_origin(root, "alpha")  # every local golden condition holds
    beta, _ = with_origin(root, "beta")
    (beta / "file.txt").write_text("edited\n")  # one uncommitted change
    gamma, _ = with_origin(root, "gamma")
    git(gamma, "push", "-q", "origin", "main:side")  # an extra remote branch that is fully merged
    git(gamma, "switch", "-q", "-c", "work")
    commit(gamma, "w.txt", message="unmerged work")
    git(gamma, "push", "-q", "origin", "work")
    git(gamma, "switch", "-q", "main")
    git(gamma, "branch", "merged-local")
    git(gamma, "branch", "-D", "work")
    delta = init(root / "delta")  # no origin, an extra local branch and an uncommitted file: three things outstanding
    git(delta, "branch", "extra")
    (delta / "scratch.txt").write_text("x\n")


@pytest.fixture(scope="session")
def world_template(tmp_path_factory):
    root = tmp_path_factory.mktemp("world-template") / "root"
    build_world(root)
    return root


@pytest.fixture()
def world(tmp_path, monkeypatch, world_template):
    root = tmp_path / "root"
    shutil.copytree(world_template, root, symlinks=True)  # a private copy per test, so tests can never affect each other
    for name in ("alpha", "beta", "gamma"):  # the copies must push to their own copy of the remote, not the template's
        git(root / name, "remote", "set-url", "origin", str(root / f"{name}-origin.git"))
    alpha, bare = root / "alpha", root / "alpha-origin.git"
    server, url = start(root, monkeypatch)
    yield {"url": url, "root": root, "alpha": alpha, "bare": bare, "tmp": tmp_path}
    server.shutdown()
    server.server_close()


@pytest.fixture()
def clean_world(tmp_path, monkeypatch):
    root = tmp_path / "root"
    with_origin(root, "alpha")
    with_origin(root, "bravo")
    server, url = start(root, monkeypatch)
    yield {"url": url, "root": root}
    server.shutdown()
    server.server_close()


def open_page(browser, url, count):
    page = browser.new_page(viewport={"width": 1280, "height": 900}, bypass_csp=True)  # the harness evaluates strings, which the page's CSP forbids
    errors, requests = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("request", lambda r: requests.append(r.url))
    page.goto(url)
    page.wait_for_function(f"document.querySelectorAll('#rows button.name').length === {count} && !document.querySelector('[data-state=checking]')")
    page.errors, page.requests = errors, requests
    return page


@pytest.fixture()
def page(world):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = open_page(browser, world["url"], 4)
        yield page
        assert page.errors == []
        browser.close()


def settled(page):
    """The page renders on the next animation frame; wait for it before reading the table."""
    page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def row(page, name):
    settled(page)
    return page.locator("#rows tr.row", has=page.locator("button.name", has_text=name))


def pill(page, name):
    return row(page, name).locator(".state").get_attribute("title")


def tags(page, name):
    return row(page, name).locator(".tag").all_inner_texts()


def names(page):
    settled(page)
    return page.locator("#rows button.name .rname").all_inner_texts()


def counts(page):
    return {k: page.locator(f"#n-{k}").inner_text() for k in ("all", "bad", "pending", "golden")}


def test_every_repo_shows_a_status_and_what_is_outstanding_in_a_few_words(page):
    assert sorted(names(page)) == ["alpha", "beta", "delta", "gamma"]
    assert pill(page, "alpha") == "Pending CI" and tags(page, "alpha") == []
    assert (pill(page, "beta"), tags(page, "beta")) == ("Needs work", ["1 change"])
    assert (pill(page, "gamma"), tags(page, "gamma")) == ("Needs work", ["1 local branch", "2 remote branches"])
    assert (pill(page, "delta"), tags(page, "delta")) == ("Needs work", ["1 change", "1 local branch", "no origin"])
    assert counts(page) == {"all": "4", "bad": "3", "pending": "1", "golden": "0"}
    assert page.title() == "(3) repo-root-tracker"
    assert "Scanned" in page.locator("#roots").inner_text()


def test_the_screen_is_not_wordy(page):
    body = page.locator("main").inner_text()
    for sentence in ("Working tree", "Sync needed", "uncommitted change", "other remote branch", "not golden:"):
        assert sentence not in body
    assert len(body.split()) < 120, len(body.split())


def test_groups_come_in_priority_order_and_the_closest_to_clean_come_first(page):
    titles = [t.lower() for t in page.locator("#rows tr.title th").all_inner_texts()]
    assert len(titles) == 2 and titles[0].startswith("needs work") and titles[1].startswith("pending ci"), titles
    assert names(page) == ["beta", "gamma", "delta", "alpha"]  # 1, 2 and 3 things outstanding, then the pending-CI group
    page.select_option("#sort", "name")
    assert names(page) == ["beta", "delta", "gamma", "alpha"]


def test_search_and_filters_use_the_group_counts(page):
    page.fill("#q", "gam")
    assert names(page) == ["gamma"]
    page.fill("#q", "")
    page.click("[data-filter=bad]")
    assert names(page) == ["beta", "gamma", "delta"]
    assert page.locator("[data-filter=bad]").get_attribute("aria-pressed") == "true"
    page.click("[data-filter=pending]")
    assert names(page) == ["alpha"]
    page.click("[data-filter=golden]")
    assert names(page) == [] and "No repos match" in page.locator("#rows").inner_text()
    page.click("[data-filter=all]")
    assert len(names(page)) == 4
    page.fill("#q", "main")  # a branch name matches too
    assert len(names(page)) == 4


def test_a_row_says_what_to_do_and_offers_the_delete_commands_only_for_merged_branches(page, world):
    toggle = page.locator("button.name", has_text="gamma")
    assert toggle.get_attribute("aria-expanded") == "false"
    toggle.focus()
    page.keyboard.press("Enter")
    assert toggle.get_attribute("aria-expanded") == "true"
    detail = page.locator("tr.detail:not([hidden])")
    text = detail.inner_text()
    assert "2 remote branches besides main" in text and "origin/side" in text and "merged, safe to delete" in text
    assert "origin/work" in text and "1 commit not on main" in text
    assert "1 local branch besides main" in text and "merged-local" in text
    assert str(world["root"].resolve() / "gamma") in text and "Last fetch" in text
    commands = "\n".join(detail.locator("code").all_inner_texts())
    gamma = world["root"].resolve() / "gamma"
    side = git(gamma, "rev-parse", "refs/remotes/origin/side")
    assert f"git -C {gamma} push --force-with-lease=refs/heads/side:{side} origin :refs/heads/side" in commands
    assert f"git -C {gamma} branch -d merged-local" in commands
    assert "refs/heads/work" not in commands and "--delete" not in commands  # nothing unmerged is offered, and no unguarded delete
    page.keyboard.press("Space")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert page.locator("tr.detail:not([hidden])").count() == 0


def test_unmerged_work_is_flagged_and_never_offered_for_deletion(page, world):
    other = world["tmp"] / "elsewhere"
    git(world["tmp"], "clone", "-q", str(world["root"] / "beta-origin.git"), str(other))
    git(other, "switch", "-q", "-c", "keep-me")
    commit(other, "k.txt", message="precious")
    commit(other, "k2.txt", message="more")
    git(other, "push", "-q", "origin", "keep-me")
    page.click("#fetch")
    page.wait_for_function("document.body.innerText.includes('Fetched')")
    page.locator("button.name", has_text="beta").click()
    text = page.locator("tr.detail:not([hidden])").inner_text()
    assert "origin/keep-me" in text and "2 commits not on main" in text
    assert "keep-me" not in "\n".join(page.locator("tr.detail:not([hidden])").locator("code").all_inner_texts())
    assert "squash-merged" in text  # the honest limit is stated next to the list


def test_other_things_outstanding_each_get_a_command(page):
    page.locator("button.name", has_text="delta").click()
    detail = page.locator("tr.detail:not([hidden])")
    assert "No origin remote" in detail.inner_text()
    assert any(c.startswith("git -C ") and c.endswith(" remote add origin <url>") for c in detail.locator("code").all_inner_texts())
    page.locator("button.name", has_text="beta").click()
    assert any(c.startswith("git -C ") and c.endswith(" status") for c in page.locator("tr.detail:not([hidden])").locator("code").all_inner_texts())


def test_copy_puts_the_command_on_the_clipboard(world):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"], bypass_csp=True)
        page = context.new_page()
        page.goto(world["url"])
        page.wait_for_function("document.querySelectorAll('#rows button.name').length === 4 && !document.querySelector('[data-state=checking]')")
        page.locator("button.name", has_text="gamma").click()
        page.locator("tr.detail:not([hidden]) li", has_text="origin/side").locator("button[data-copy]").click()
        gamma = world["root"].resolve() / "gamma"
        side = git(gamma, "rev-parse", "refs/remotes/origin/side")
        assert page.evaluate("navigator.clipboard.readText()") == f"git -C {gamma} push --force-with-lease=refs/heads/side:{side} origin :refs/heads/side"
        browser.close()


def test_check_ci_turns_a_pending_repo_golden_and_never_rescues_the_others(page):
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert pill(page, "alpha") == "Golden"
    assert pill(page, "beta") == "Needs work"
    assert counts(page) == {"all": "4", "bad": "3", "pending": "0", "golden": "1"}
    assert page.title() == "(3) repo-root-tracker"


def test_the_pending_group_has_its_own_check_ci_button(page):
    page.click("tr.title .btn")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert pill(page, "alpha") == "Golden"


def test_everything_is_clean_never_shows_while_anything_is_outstanding(page):
    assert page.locator("#clear").is_hidden()  # beta, gamma and delta need work, and pending CI is not clean either
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert counts(page)["golden"] == "1" and page.locator("#clear").is_hidden()  # alpha is golden now, but three repos still need work


def test_everything_is_clean_appears_once_every_repo_is_golden(clean_world):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = open_page(browser, clean_world["url"], 2)
        assert page.locator("#clear").is_hidden()  # both repos are only "Pending CI": the claim must wait for CI
        page.click("#ci")
        page.wait_for_function("document.body.innerText.includes('GitHub checked')")
        page.wait_for_function("!document.getElementById('clear').hidden")
        assert "Everything is clean." in page.locator("#clear").inner_text()
        assert counts(page) == {"all": "2", "bad": "0", "pending": "0", "golden": "2"}
        assert page.title() == "repo-root-tracker"  # no attention count in the tab
        assert page.errors == []
        browser.close()


def test_failing_ci_is_never_called_clean(world, monkeypatch):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        monkeypatch.setattr(srv, "get_default_branch_ci", lambda path, refresh=False: CiState(state="failing", repo="o/r", head_sha=git(Path(path), "rev-parse", "refs/heads/main")))
        page = open_page(browser, world["url"], 4)
        page.click("#ci")
        page.wait_for_function("document.body.innerText.includes('GitHub checked')")
        assert pill(page, "alpha") == "Needs work" and tags(page, "alpha") == ["CI failing"]
        assert row(page, "alpha").locator(".tag.hot").all_inner_texts() == ["CI failing"]  # the red outline marks the serious chips
        page.locator("button.name", has_text="alpha").click()
        assert "Open Actions" in page.locator("tr.detail:not([hidden])").inner_text()
        assert page.locator("#clear").is_hidden()
        browser.close()


def test_fetch_reveals_a_branch_pushed_elsewhere(page, world):
    other = world["tmp"] / "elsewhere"
    git(world["tmp"], "clone", "-q", str(world["bare"]), str(other))
    git(other, "push", "-q", "origin", "main:surprise")
    assert pill(page, "alpha") == "Pending CI"
    page.click("#fetch")
    page.wait_for_function("document.body.innerText.includes('Fetched')")
    assert (pill(page, "alpha"), tags(page, "alpha")) == ("Needs work", ["1 remote branch"])


def test_rescan_finds_a_new_repo(page, world):
    init(world["root"] / "epsilon")
    rescan_until(page, 5)
    assert "epsilon" in names(page)


def test_status_never_relies_on_color(page):
    states = page.locator(".state")
    assert states.count() == 4
    assert all(t and t.strip() for t in states.evaluate_all("els => els.map(e => e.title)"))  # the words are there for assistive tech and hover
    assert all(t.strip() for t in states.locator(".sr").all_text_contents())  # and in the accessible name of the row's button
    assert states.locator("svg").count() == 4  # plus a drawn icon
    colors = states.evaluate_all("els => els.map(e => getComputedStyle(e).color)")
    assert len(set(colors)) >= 2  # color is a redundant cue on top of the icon and words


def test_the_phone_layout_is_compact_labelless_and_easy_to_tap(page):
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    body = page.locator("#rows").inner_text()
    for label in ("Branch:", "Status:", "Outstanding:", "Last commit:"):
        assert label not in body, label
    assert page.locator("td[data-label]").count() == 0
    generated = page.locator("tr.row td").evaluate_all("els => els.map(e => getComputedStyle(e, '::before').content)")
    assert set(generated) <= {"none", "normal"}, generated  # CSS-generated labels never show up in the page text, so check the style
    heights = page.locator("button.name").evaluate_all("els => els.map(e => e.getBoundingClientRect().height)")
    assert min(heights) >= 44, heights  # a finger-sized target
    first = page.locator("tr.row").first.bounding_box()
    assert first["height"] < 110, first  # about four repos per screen instead of three
    page.locator("button.name", has_text="gamma").click()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_columns_line_up_with_their_headings_on_a_wide_screen(page):
    heads = page.locator("#rows thead th").evaluate_all("els => els.map(e => Math.round(e.getBoundingClientRect().left))")
    cells = page.locator("#rows tr.row").first.locator("td").evaluate_all("els => els.map(e => Math.round(e.getBoundingClientRect().left))")
    assert all(abs(h - c) <= 2 for h, c in zip(heads, cells)), (heads, cells)
    assert page.locator("td.when").first.evaluate("e => e.getBoundingClientRect().height") < 60  # a time never wraps


def test_nothing_leaves_the_machine(page, world):
    assert page.requests and all(u.startswith(world["url"]) for u in page.requests), page.requests


def test_both_color_schemes_render(page):
    page.emulate_media(color_scheme="dark")
    dark = page.evaluate("getComputedStyle(document.body).backgroundColor")
    page.emulate_media(color_scheme="light")
    light = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert dark != light


def test_the_page_is_light_and_fast(page, world):
    assert page.evaluate("document.documentElement.outerHTML.length") < 61440
    started = time.monotonic()
    page.reload()
    page.wait_for_selector("#rows button.name")
    first_row = time.monotonic() - started
    page.wait_for_function("!document.querySelector('[data-state=checking]')")
    all_rows = time.monotonic() - started
    assert first_row < 1.0 and all_rows < 5.0, (first_row, all_rows)


def test_an_unreadable_status_shows_in_the_row_not_a_blank(world, page):
    shutil.rmtree(world["root"] / "delta")
    page.click("#refresh")
    page.wait_for_function("document.body.innerText.includes('Gone from disk')")
    assert pill(page, "delta") == "Gone from disk" and tags(page, "delta") == ["Gone from disk"]
    assert page.errors == ["Failed to load resource: the server responded with a status of 410 (Gone)"]  # the browser logs any 4xx
    page.errors.clear()


def test_the_page_runs_cleanly_under_its_own_strict_policy(world):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()  # no CSP bypass: exactly what a user's browser enforces
        messages = []
        page.on("console", lambda m: messages.append(m.text))
        page.on("pageerror", lambda e: messages.append(str(e)))
        page.goto(world["url"])
        page.locator("#rows button.name").nth(3).wait_for()
        page.locator(".state[data-state=pending]").wait_for()
        page.locator("button.name", has_text="gamma").click()
        page.locator("tr.detail:not([hidden])").wait_for()
        page.locator("tr.detail:not([hidden]) li", has_text="origin/side").locator("button[data-copy]").wait_for()
        browser.close()
    assert messages == []


def test_hostile_text_in_git_data_is_shown_as_text_and_never_runs(world):
    evil = '<img src=x onerror="window.__pwned=1">'
    repo = init(world["root"] / "<b>bold")
    commit(repo, "f.txt", "y\n", message=evil)
    git(repo, "branch", "--", "<script>window.__pwned=2</script>")
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(bypass_csp=True)  # without the policy, only the page's own escaping stands in the way
        page.goto(world["url"])
        page.wait_for_function("document.querySelectorAll('#rows button.name').length === 5 && !document.querySelector('[data-state=checking]')")
        page.locator("button.name", has_text="<b>bold").click()
        page.wait_for_timeout(300)
        assert page.evaluate("window.__pwned") is None
        body = page.locator("#rows").inner_text()
        assert evil in body and "<script>window.__pwned=2</script>" in body and "<b>bold" in body
        assert page.locator("#rows img, #rows script, #rows b").count() == 0
        browser.close()


def test_branch_names_with_shell_characters_are_quoted_in_copied_commands(world):
    repo = init(world["root"] / "quoting")
    git(repo, "branch", "it's$odd;rm")
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(bypass_csp=True)
        page.goto(world["url"])
        page.wait_for_function("document.querySelectorAll('#rows button.name').length === 5 && !document.querySelector('[data-state=checking]')")
        page.locator("button.name", has_text="quoting").click()
        commands = page.locator("tr.detail:not([hidden]) code").all_inner_texts()
        import shlex
        line = next(c for c in commands if "branch -d" in c)
        parsed = shlex.split(line)
        assert parsed[:3] == ["git", "-C", str(world["root"].resolve() / "quoting")] and parsed[3:] == ["branch", "-d", "it's$odd;rm"], line  # one argument, nothing runs
        browser.close()


def test_on_a_phone_over_the_network_fetch_and_rescan_are_off_and_say_why(tmp_path, monkeypatch):
    root = tmp_path / "root"
    with_origin(root, "alpha")
    monkeypatch.setattr(srv, "lan_addresses", lambda: [])
    monkeypatch.setattr(srv, "lan_hostnames", lambda: set())
    monkeypatch.setattr(status_module, "_github_remote", lambda p: "o/r")
    monkeypatch.setattr(srv, "get_default_branch_ci", lambda p, refresh=False: CiState(state="passing", repo="o/r"))
    server = srv.make_server(0, [str(root)], lan=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(srv.Handler, "_peer", lambda self: "private")  # this browser plays a phone on the wifi
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch()
            page = open_page(browser, f"http://127.0.0.1:{server.server_address[1]}/", 1)
            assert all(page.locator(f"#{b}").is_disabled() for b in ("fetch", "rescan", "ci"))
            assert page.locator("#refresh").is_enabled()
            assert "Only works on the computer running" in page.locator("#fetch").get_attribute("title")
            assert "Read-only on this device" in page.locator("#roots").inner_text()
            page.click("#refresh")  # a busy cycle must not re-enable the locked buttons
            page.wait_for_function("document.body.innerText.includes('Refreshed')")
            assert all(page.locator(f"#{b}").is_disabled() for b in ("fetch", "rescan", "ci"))
            assert page.errors == []
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_on_the_machine_itself_nothing_is_locked(page):
    assert all(page.locator(f"#{b}").is_enabled() for b in ("fetch", "rescan", "ci"))
    assert "Read-only" not in page.locator("#roots").inner_text()


# ---- findings from the independent critique -------------------------------------------------------------------------

import subprocess


def copied(page, name, containing):
    """The command text of the item in the open detail row whose text contains `containing`."""
    page.locator("button.name", has_text=name).click()
    return page.locator("tr.detail:not([hidden]) li", has_text=containing).locator("code").first.inner_text()


def run_shell(command, cwd):
    return subprocess.run(["bash", "-c", command], cwd=cwd, capture_output=True, text=True)


def remote_branches(bare):
    return git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads/").split()


def rescan_until(page, count):
    page.click("#rescan")
    page.wait_for_function(f"document.querySelectorAll('#rows button.name').length === {count} && !document.querySelector('[data-state=checking]')")
    settled(page)


def test_the_copied_remote_delete_really_deletes_the_merged_branch_and_only_that_one(page, world):
    gamma, bare = world["root"] / "gamma", world["root"] / "gamma-origin.git"
    assert {"side", "work"} <= set(remote_branches(bare))
    command = copied(page, "gamma", "origin/side")
    result = run_shell(command, world["tmp"])  # from an unrelated directory: the command names its repository
    assert result.returncode == 0, result.stderr
    assert "side" not in remote_branches(bare) and "work" in remote_branches(bare)  # the unmerged branch is untouched


def test_the_copied_remote_delete_is_refused_if_the_branch_moved_after_the_page_looked(page, world):
    bare = world["root"] / "gamma-origin.git"
    command = copied(page, "gamma", "origin/side")
    other = world["tmp"] / "elsewhere"
    git(world["tmp"], "clone", "-q", str(bare), str(other))
    git(other, "switch", "-q", "side")
    commit(other, "late.txt", message="work pushed after the page loaded")
    git(other, "push", "-q", "origin", "side")
    result = run_shell(command, world["tmp"])
    assert result.returncode != 0 and "side" in remote_branches(bare)  # the lease refuses; nothing is lost
    assert git(bare, "log", "-1", "--format=%s", "side") == "work pushed after the page loaded"


def test_a_branch_merged_by_patch_gets_a_labelled_capital_d_and_ancestors_get_a_plain_d(page, world):
    repo = init(world["root"] / "rebasey")
    git(repo, "branch", "plain")
    git(repo, "switch", "-q", "-c", "rebased")
    commit(repo, "r.txt", message="rebased work")
    git(repo, "switch", "-q", "main")
    commit(repo, "moved.txt", message="main moved on")
    git(repo, "cherry-pick", "rebased")
    rescan_until(page, 5)
    page.locator("button.name", has_text="rebasey").click()
    detail = page.locator("tr.detail:not([hidden])")
    text = detail.inner_text()
    assert "rebased: merged by patch, so git insists on -D" in text
    commands = detail.locator("code").all_inner_texts()
    assert any(c.endswith(" branch -d plain") for c in commands) and any(c.endswith(" branch -D rebased") for c in commands)
    assert not any(" branch -d " in c and "rebased" in c for c in commands)
    assert run_shell(next(c for c in commands if c.endswith("branch -D rebased")), world["tmp"]).returncode == 0
    assert "rebased" not in git(repo, "branch", "--list")


def test_a_branch_whose_merge_commit_carries_its_own_change_is_never_offered_for_deletion(page, world):
    repo = init(world["root"] / "sneaky")
    git(repo, "switch", "-q", "-c", "side")
    commit(repo, "s.txt", message="side work")
    git(repo, "switch", "-q", "-c", "evilbr", "main")
    git(repo, "merge", "-q", "--no-commit", "--no-ff", "side")
    (repo / "extra.txt").write_text("only on this branch\n")
    git(repo, "add", "extra.txt")
    git(repo, "commit", "-q", "-m", "merge side and add extra")
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--ff-only", "side")
    rescan_until(page, 5)
    page.locator("button.name", has_text="sneaky").click()
    detail = page.locator("tr.detail:not([hidden])")
    assert "evilbr" in detail.inner_text() and "cannot tell if merged" in detail.inner_text()
    assert not any("evilbr" in c for c in detail.locator("code").all_inner_texts())


def test_ahead_and_behind_gets_a_valid_command_not_two_glued_together(page, world):
    alpha, bare = world["alpha"], world["bare"]
    commit(alpha, "local.txt", message="local only")
    other = world["tmp"] / "elsewhere"
    git(world["tmp"], "clone", "-q", str(bare), str(other))
    commit(other, "remote.txt", message="remote only")
    git(other, "push", "-q", "origin", "main")
    git(alpha, "fetch", "-q")
    page.click("#refresh")
    page.wait_for_function("document.body.innerText.includes('Refreshed')")
    page.locator("button.name", has_text="alpha").click()
    detail = page.locator("tr.detail:not([hidden])")
    assert "diverged" in detail.inner_text()
    command = detail.locator("code").first.inner_text()
    assert " && " in command and command.count("git ") == 3 and "pull --rebase origin main" in command
    assert "   " not in command  # the old bug: two commands glued together with spaces


def test_the_shown_commands_name_their_repository(page, world):
    page.locator("button.name", has_text="beta").click()
    for code in page.locator("tr.detail:not([hidden]) code").all_inner_texts():
        assert code.startswith("git -C ") and str(world["root"].resolve() / "beta") in code, code


def test_an_unreadable_repo_lands_under_needs_work_not_pending_ci(page, world):
    shutil.rmtree(world["root"] / "alpha")
    page.click("#refresh")
    page.wait_for_function("document.body.innerText.includes('Refreshed')")
    assert pill(page, "alpha") == "Gone from disk" and tags(page, "alpha") == ["Gone from disk"]
    assert counts(page) == {"all": "4", "bad": "4", "pending": "0", "golden": "0"}
    assert page.title() == "(4) repo-root-tracker"
    page.errors.clear()


def test_a_bare_repository_layout_with_a_dirty_worktree_needs_work_instead_of_looking_golden(page, world):
    bare = world["tmp"] / "bare-origin.git"
    seed = init(world["tmp"] / "seed")
    subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(bare)], check=True, capture_output=True)
    git(bare, "worktree", "add", "-q", str(world["root"] / "bare-wt"), "main")
    (world["root"] / "bare-wt" / "dirty.txt").write_text("x\n")
    rescan_until(page, 5)
    assert (pill(page, "bare-wt"), tags(page, "bare-wt")) == ("Worktree", ["1 change"])
    assert counts(page)["bad"] == "4" and counts(page)["golden"] == "0"  # judged by its worktree: dirty, so it needs work


def test_the_tab_count_and_the_chips_count_the_same_thing(page, world):
    git(world["alpha"], "worktree", "add", "-q", "-b", "wt", str(world["tmp"] / "alpha-wt"))
    (world["tmp"] / "alpha-wt" / "d.txt").write_text("x\n")
    rescan_until(page, 5)
    assert counts(page)["all"] == "4" and counts(page)["bad"] == "4"  # alpha now has an extra worktree: one project, counted once
    assert page.title() == "(4) repo-root-tracker"
    page.wait_for_function("document.getElementById('status').innerText.includes('checked')")
    assert "4 repos, 1 worktree" in page.locator("#status").inner_text()


def test_a_long_branch_list_says_how_much_it_shows(page, world):
    repo = init(world["root"] / "crowded")
    for i in range(45):
        git(repo, "branch", f"old{i:02}")
    rescan_until(page, 5)
    assert "45 local branches" in " ".join(tags(page, "crowded"))
    page.locator("button.name", has_text="crowded").click()
    assert "Showing 40 of 45 branches" in page.locator("tr.detail:not([hidden])").inner_text()


def test_ci_is_checked_automatically_for_clean_repos_only_and_never_for_the_others(tmp_path, monkeypatch):
    root = tmp_path / "root"
    with_origin(root, "clean")
    dirty, _ = with_origin(root, "dirty")
    (dirty / "file.txt").write_text("edited\n")
    asked = []
    server, url = start(root, monkeypatch, auto_ci=True)
    head = lambda p: git(Path(p), "rev-parse", "refs/heads/main")
    monkeypatch.setattr(srv, "get_default_branch_ci", lambda p, refresh=False: asked.append(Path(p).name) or CiState(
        state="passing", repo="o/r", head_sha=head(p), checked_at="2026-10-06T10:00:00+00:00"))
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch()
            page = open_page(browser, url, 2)
            page.wait_for_function("document.querySelector('.state[data-state=golden]') !== null")  # no click anywhere
            assert pill(page, "clean") == "Golden" and pill(page, "dirty") == "Needs work"
            assert asked == ["clean"], asked  # a repo that already needs work is never sent to GitHub
            assert counts(page) == {"all": "2", "bad": "1", "pending": "0", "golden": "1"}
            page.locator("button.name", has_text="clean").click()
            assert "CI passing, checked" in page.locator("tr.detail:not([hidden])").inner_text()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()



def items(prs=(), issues=(), **extra):
    mk = lambda n, t: {"number": n, "title": t, "url": f"https://github.com/o/r/pull/{n}", "draft": False, "branch": f"b{n}"}
    return OpenItems(repo="o/r", available=True, prs_known=True, issues_known=True, checked_at="2026-10-06T10:00:00+00:00",
                     prs=[mk(n, t) for n, t in prs],
                     issues=[{"number": n, "title": t, "url": f"https://github.com/o/r/issues/{n}"} for n, t in issues], **extra)


def test_open_pull_requests_and_issues_are_counted_numbered_and_never_change_the_verdict(page, world, monkeypatch):
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: items(
        prs=[(12, "Add Tron"), (9, "Fix scan <b>x</b>")], issues=[(45, "closure docs"), (46, "status text"), (47, "delivery warning")]))
    beta_before = pill(page, "beta")
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert tags(page, "alpha") == ["2 PRs", "3 issues"]  # quiet extra chips, nothing else changed
    assert (pill(page, "alpha"), pill(page, "beta")) == ("Golden", beta_before)  # CI passed, so Golden; the 5 open items changed nothing
    assert row(page, "alpha").locator(".tag.info").count() == 2 and row(page, "alpha").locator(".tag.hot").count() == 0
    page.locator("button.name", has_text="alpha").click()
    detail = page.locator("tr.detail:not([hidden]) .gh")
    text = detail.inner_text().lower()
    assert "pull requests (2)" in text and "#12" in text and "add tron" in text and "issues (3)" in text and "#47" in text
    assert "do not affect the verdict" in text
    links = detail.locator("a").evaluate_all("els => els.map(e => [e.textContent, e.href, e.target, e.rel])")
    assert ["#12", "https://github.com/o/r/pull/12", "_blank", "noopener noreferrer"] in links
    assert detail.locator("b").count() == 0  # a title is text, never markup


def test_singular_and_truncated_counts(page, monkeypatch):
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: items(prs=[(1, "one")], issues=[(n, "i") for n in range(30)], issues_truncated=True))
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert tags(page, "alpha") == ["1 PR", "30+ issues"]
    page.locator("button.name", has_text="alpha").click()
    assert "Only the newest are shown." in page.locator("tr.detail:not([hidden]) .gh").inner_text()


def test_a_repo_with_nothing_open_shows_no_chips_and_says_none_open(page):
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert tags(page, "alpha") == []
    page.locator("button.name", has_text="alpha").click()
    assert page.locator("tr.detail:not([hidden]) .gh").inner_text().count("None open.") == 2


def test_when_gh_cannot_answer_it_says_unavailable_instead_of_zero(page, monkeypatch):
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: OpenItems(repo="o/r", available=False, checked_at="2026-10-06T10:00:00+00:00"))
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert tags(page, "alpha") == []
    page.locator("button.name", has_text="alpha").click()
    assert "unavailable" in page.locator("tr.detail:not([hidden]) .gh").inner_text()


def test_a_link_that_is_not_github_is_shown_as_plain_text(page, monkeypatch):
    bad = items(prs=[(5, "sneaky")])
    bad.prs[0]["url"] = "javascript:alert(1)"
    monkeypatch.setattr(srv, "get_open_items", lambda p, refresh=False: bad)
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    page.locator("button.name", has_text="alpha").click()
    detail = page.locator("tr.detail:not([hidden]) .gh")
    assert "#5" in detail.inner_text() and detail.locator("a").count() == 0
