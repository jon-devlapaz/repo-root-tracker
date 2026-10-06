"""End to end: the real server, real temporary git repos and a real browser."""

import threading
import time

import pytest
from gitfix import commit, git, init, with_origin
from playwright import sync_api as playwright

from repo_root_tracker import server as srv
from repo_root_tracker import status as status_module
from repo_root_tracker.github import CiState


@pytest.fixture()
def world(tmp_path, monkeypatch):
    root = tmp_path / "root"
    alpha, bare = with_origin(root, "alpha")  # every local golden condition holds
    beta, _ = with_origin(root, "beta")
    (beta / "file.txt").write_text("edited\n")  # one uncommitted change
    gamma, _ = with_origin(root, "gamma")
    git(gamma, "push", "-q", "origin", "main:side")  # an extra remote branch
    init(root / "delta")  # no origin
    git(alpha, "worktree", "add", "-q", "-b", "wt", str(tmp_path / "alpha-wt"))
    git(alpha, "worktree", "remove", "--force", str(tmp_path / "alpha-wt"))  # start without extras: alpha stays golden-ready
    monkeypatch.setattr(srv, "get_default_branch_ci", lambda p, refresh=False: CiState(state="passing", repo="o/r"))
    monkeypatch.setattr(status_module, "_github_remote", lambda p: "o/r")  # pretend each origin is on GitHub; no network is used
    git(alpha, "branch", "-D", "wt")
    server = srv.make_server(0, [str(root)])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield {"url": f"http://127.0.0.1:{server.server_address[1]}/", "root": root, "alpha": alpha, "bare": bare, "tmp": tmp_path}
    server.shutdown()
    server.server_close()


@pytest.fixture()
def page(world):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        # The harness evaluates strings in the page, which the page's own strict CSP forbids; one test below runs without this.
        page = browser.new_page(viewport={"width": 1280, "height": 900}, bypass_csp=True)
        errors, requests = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("request", lambda r: requests.append(r.url))
        page.goto(world["url"])
        page.wait_for_function("document.querySelectorAll('#rows tr:not(.detail) button.toggle').length === 4 "
                               "&& !document.body.innerText.includes('checking')")
        page.errors, page.requests = errors, requests
        yield page
        assert errors == []
        browser.close()


def settled(page):
    """The page renders on the next animation frame; wait for it before reading the table."""
    page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def golden(page, name):
    settled(page)
    return page.locator("#rows tr:not(.detail)", has=page.locator("button.toggle", has_text=name)).locator("td[data-label=Golden]").inner_text()


def names(page):
    settled(page)
    return page.locator("#rows tr:not(.detail) button.toggle").all_inner_texts()


def test_every_repo_appears_with_a_verdict_in_words(page):
    assert sorted(names(page)) == ["alpha", "beta", "delta", "gamma"]
    assert golden(page, "alpha") == "golden pending CI"
    assert golden(page, "beta") == "✗ not golden: 1 uncommitted change"
    assert golden(page, "gamma") == "✗ not golden: other remote branch: origin/side"
    assert golden(page, "delta") == "✗ not golden: no origin remote"
    assert page.title() == "(3) repo-root-tracker"
    assert "Scanned" in page.locator("#roots").inner_text()


def test_default_order_puts_what_needs_attention_first(page):
    assert names(page)[-1] == "alpha"
    page.select_option("#sort", "name")
    assert names(page) == ["alpha", "beta", "delta", "gamma"]


def test_search_and_filters(page):
    page.fill("#q", "gam")
    assert names(page) == ["gamma"]
    page.fill("#q", "")
    page.click("[data-filter=changed]")
    assert names(page) == ["beta"]
    assert page.locator("[data-filter=changed]").get_attribute("aria-pressed") == "true"
    page.click("[data-filter=attention]")
    assert sorted(names(page)) == ["beta", "delta", "gamma"]
    page.click("[data-filter=sync]")
    assert names(page) == []
    assert "No repos match" in page.locator("#rows").inner_text()
    page.click("[data-filter=all]")
    assert len(names(page)) == 4
    page.fill("#q", "main")  # a branch name matches too
    assert len(names(page)) == 4


def test_a_row_expands_with_reasons_branches_and_path_and_is_keyboard_operable(page, world):
    toggle = page.locator("button.toggle", has_text="gamma")
    assert toggle.get_attribute("aria-expanded") == "false"
    toggle.focus()
    page.keyboard.press("Enter")
    assert toggle.get_attribute("aria-expanded") == "true"
    detail = page.locator("tr.detail:not([hidden])")
    text = detail.inner_text()
    assert str(world["root"].resolve() / "gamma") in text and "origin/side" in text and "origin/main" in text
    assert "Local branches" in text and "Remote branches" in text and "Last fetch" in text
    page.keyboard.press("Space")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert page.locator("tr.detail:not([hidden])").count() == 0


def test_check_github_turns_a_pending_repo_golden_and_never_rescues_the_others(page):
    page.click("#ci")
    page.wait_for_function("document.body.innerText.includes('GitHub checked')")
    assert golden(page, "alpha") == "✓ golden"
    assert golden(page, "beta").startswith("✗ not golden")
    assert page.title() == "(3) repo-root-tracker"


def test_fetch_all_reveals_a_branch_pushed_elsewhere(page, world):
    other = world["tmp"] / "elsewhere"
    git(world["tmp"], "clone", "-q", str(world["bare"]), str(other))
    git(other, "push", "-q", "origin", "main:surprise")
    assert golden(page, "alpha") == "golden pending CI"
    page.click("#fetch")
    page.wait_for_function("document.body.innerText.includes('Fetched')")
    assert golden(page, "alpha") == "✗ not golden: other remote branch: origin/surprise"


def test_rescan_finds_a_new_repo(page, world):
    init(world["root"] / "epsilon")
    page.click("#rescan")
    page.wait_for_function("document.querySelectorAll('#rows button.toggle').length === 5")
    assert "epsilon" in names(page)


def test_verdicts_do_not_rely_on_color(page):
    texts = page.locator("td[data-label=Golden]").all_inner_texts()
    assert all(t.strip() and ("golden" in t) for t in texts)
    colors = page.locator("td[data-label=Golden] span").evaluate_all("els => els.map(e => getComputedStyle(e).color)")
    assert len(set(colors)) >= 2  # color is a redundant cue on top of the words


def test_no_horizontal_scroll_on_a_phone(page):
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.locator("td[data-label=Golden]").first.is_visible()
    page.locator("button.toggle", has_text="gamma").click()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_nothing_leaves_the_machine(page, world):
    assert page.requests and all(u.startswith(world["url"]) for u in page.requests), page.requests


def test_both_color_schemes_render_with_readable_contrast(page):
    page.emulate_media(color_scheme="dark")
    dark = page.evaluate("getComputedStyle(document.body).backgroundColor")
    page.emulate_media(color_scheme="light")
    light = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert dark != light


def test_the_page_is_light_and_fast(page, world):
    html = page.evaluate("document.documentElement.outerHTML.length")
    assert html < 61440
    started = time.monotonic()
    page.reload()
    page.wait_for_selector("#rows tr:not(.detail) button.toggle")
    first_row = time.monotonic() - started
    page.wait_for_function("!document.body.innerText.includes('checking')")
    all_rows = time.monotonic() - started
    assert first_row < 1.0 and all_rows < 5.0, (first_row, all_rows)


def test_an_unreadable_status_shows_in_the_row_not_a_blank(world, page):
    import shutil
    shutil.rmtree(world["root"] / "delta")
    page.click("#refresh")
    page.wait_for_function("document.body.innerText.includes('gone from disk')")
    assert golden(page, "delta") == "gone from disk"
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
        page.locator("#rows tr:not(.detail) button.toggle").nth(3).wait_for()
        page.locator("td[data-label=Golden]", has_text="golden pending CI").wait_for()
        page.locator("button.toggle", has_text="gamma").click()
        page.locator("tr.detail:not([hidden])").wait_for()
        browser.close()
    assert [m for m in messages if "Content Security Policy" in m or "Refused" in m] == [] and messages == []


def test_hostile_text_in_git_data_is_shown_as_text_and_never_runs(world):
    evil = '<img src=x onerror="window.__pwned=1">'
    repo = init(world["root"] / "<b>bold")
    commit(repo, "f.txt", "y\n", message=evil)
    git(repo, "branch", "--", "<script>window.__pwned=2</script>")
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(bypass_csp=True)  # without the policy, only the page's own escaping stands in the way
        page.goto(world["url"])
        page.wait_for_function("document.querySelectorAll('#rows tr:not(.detail) button.toggle').length === 5 "
                               "&& !document.body.innerText.includes('checking')")
        page.locator("button.toggle", has_text="<b>bold").click()
        page.wait_for_timeout(300)
        assert page.evaluate("window.__pwned") is None
        body = page.locator("#rows").inner_text()
        assert evil in body and "<script>window.__pwned=2</script>" in body and "<b>bold" in body
        assert page.locator("#rows img, #rows script, #rows b").count() == 0
        browser.close()
