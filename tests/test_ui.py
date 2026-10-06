"""End to end: the real server, real temporary git repos and a real browser."""

import shutil
import threading
import time

import pytest
from gitfix import commit, git, init, with_origin
from playwright import sync_api as playwright

from repo_root_tracker import server as srv
from repo_root_tracker import status as status_module
from repo_root_tracker.github import CiState


def start(root, monkeypatch, ci="passing"):
    monkeypatch.setattr(srv, "get_default_branch_ci", lambda p, refresh=False: CiState(state=ci, repo="o/r"))
    monkeypatch.setattr(status_module, "_github_remote", lambda p: "o/r")  # pretend each origin is on GitHub; no network is used
    server = srv.make_server(0, [str(root)])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


@pytest.fixture()
def world(tmp_path, monkeypatch):
    root = tmp_path / "root"
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
    page.wait_for_function(f"document.querySelectorAll('#rows button.name').length === {count} && !document.body.innerText.includes('checking')")
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
    return row(page, name).locator("td[data-label=Status] .pill").inner_text()


def tags(page, name):
    return row(page, name).locator(".tag").all_inner_texts()


def names(page):
    settled(page)
    return page.locator("#rows button.name").all_inner_texts()


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
    commands = detail.locator("code").all_inner_texts()
    assert "git push origin --delete side" in commands and "git branch -d merged-local" in commands
    assert not any("work" in c for c in commands)  # nothing unmerged is ever offered for deletion
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
    assert "git push origin --delete" not in page.locator("tr.detail:not([hidden])").inner_html()
    assert "squash-merged" in text  # the honest limit is stated next to the list


def test_other_things_outstanding_each_get_a_command(page):
    page.locator("button.name", has_text="delta").click()
    detail = page.locator("tr.detail:not([hidden])")
    assert "No origin remote" in detail.inner_text() and "git remote add origin <url>" in detail.locator("code").all_inner_texts()
    page.locator("button.name", has_text="beta").click()
    assert "git status" in page.locator("tr.detail:not([hidden])").locator("code").all_inner_texts()


def test_copy_puts_the_command_on_the_clipboard(world):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"], bypass_csp=True)
        page = context.new_page()
        page.goto(world["url"])
        page.wait_for_function("document.querySelectorAll('#rows button.name').length === 4 && !document.body.innerText.includes('checking')")
        page.locator("button.name", has_text="gamma").click()
        page.locator("tr.detail:not([hidden]) li", has_text="origin/side").locator("button[data-copy]").click()
        assert page.evaluate("navigator.clipboard.readText()") == "git push origin --delete side"
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
        monkeypatch.setattr(srv, "get_default_branch_ci", lambda path, refresh=False: CiState(state="failing", repo="o/r"))
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
    page.click("#rescan")
    page.wait_for_function("document.querySelectorAll('#rows button.name').length === 5")
    assert "epsilon" in names(page)


def test_status_never_relies_on_color(page):
    pills = page.locator("td[data-label=Status] .pill")
    assert all(t.strip() for t in pills.all_inner_texts())
    colors = pills.evaluate_all("els => els.map(e => getComputedStyle(e).color)")
    assert len(set(colors)) >= 2  # color is a redundant cue on top of the words
    assert page.locator("td[data-label=Status] .pill svg").count() == pills.count()  # and a drawn icon, too


def test_no_horizontal_scroll_on_a_phone(page):
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.locator("td[data-label=Status]").first.is_visible()
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
    page.wait_for_function("!document.body.innerText.includes('checking')")
    all_rows = time.monotonic() - started
    assert first_row < 1.0 and all_rows < 5.0, (first_row, all_rows)


def test_an_unreadable_status_shows_in_the_row_not_a_blank(world, page):
    shutil.rmtree(world["root"] / "delta")
    page.click("#refresh")
    page.wait_for_function("document.body.innerText.includes('Gone from disk')")
    assert pill(page, "delta") == "Gone from disk"
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
        page.locator(".pill", has_text="Pending CI").wait_for()
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
        page.wait_for_function("document.querySelectorAll('#rows button.name').length === 5 && !document.body.innerText.includes('checking')")
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
        page.wait_for_function("document.querySelectorAll('#rows button.name').length === 5 && !document.body.innerText.includes('checking')")
        page.locator("button.name", has_text="quoting").click()
        commands = page.locator("tr.detail:not([hidden]) code").all_inner_texts()
        import shlex
        assert "git branch -d 'it'\\''s$odd;rm'" in commands, commands
        assert shlex.split("git branch -d 'it'\\''s$odd;rm'") == ["git", "branch", "-d", "it's$odd;rm"]  # one argument, nothing runs
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
            assert page.locator("#fetch").is_disabled() and page.locator("#rescan").is_disabled()
            assert page.locator("#refresh").is_enabled() and page.locator("#ci").is_enabled()
            assert "Only works on the computer running" in page.locator("#fetch").get_attribute("title")
            assert "Read-only on this device" in page.locator("#roots").inner_text()
            page.click("#refresh")  # a busy cycle must not re-enable the locked buttons
            page.wait_for_function("document.body.innerText.includes('Refreshed')")
            assert page.locator("#fetch").is_disabled() and page.locator("#rescan").is_disabled()
            assert page.errors == []
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_on_the_machine_itself_nothing_is_locked(page):
    assert page.locator("#fetch").is_enabled() and page.locator("#rescan").is_enabled()
    assert "Read-only" not in page.locator("#roots").inner_text()
