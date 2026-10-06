"""The Delete button and its dialog, end to end: real server, real repos with real bare remotes, real browser. gh is stubbed."""

import pytest
from gitfix import commit, git
from test_ui import open_page, page, playwright, remote_branches, settled, world, world_template  # noqa: F401 (fixtures)

from repo_root_tracker import branch_delete as bd
from repo_root_tracker import server as srv


@pytest.fixture(autouse=True)
def log_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "LOG", tmp_path / "deleted.log")
    return tmp_path / "deleted.log"


def open_gamma(page):
    page.locator("button.name", has_text="gamma").click()
    page.wait_for_selector("tr.detail:not([hidden]) [data-del]")
    return page.locator("tr.detail:not([hidden])")


def del_button(page, key):
    return page.locator(f"tr.detail:not([hidden]) [data-del='{key}']")


def test_buttons_appear_only_on_branches_the_server_says_may_go(page):
    detail = open_gamma(page)
    assert sorted(b.get_attribute("data-del") for b in detail.locator("[data-del]").all()) == ["local:merged-local", "remote:side"]
    assert detail.locator("[data-del='remote:work']").count() == 0  # one commit not on main
    page.locator("button.name", has_text="gamma").click()  # close gamma
    page.locator("button.name", has_text="beta").click()
    page.wait_for_selector("tr.detail:not([hidden])")
    settled(page)
    assert page.locator("tr.detail:not([hidden]) [data-del]").count() == 0


def test_the_dialog_names_what_goes_cancel_is_focused_and_escape_and_cancel_delete_nothing(page, world):
    open_gamma(page)
    del_button(page, "remote:side").click()
    dialog = page.locator("dialog[open]")
    text = dialog.inner_text()
    gamma = world["root"].resolve() / "gamma"
    sha = git(gamma, "rev-parse", "refs/remotes/origin/side")
    assert "Delete remote branch side?" in text and sha[:10] in text and "merged into main" in text and "Judged from" in text
    assert page.evaluate("document.activeElement.textContent") == "Cancel"
    page.keyboard.press("Enter")  # the default action is the safe one
    assert page.locator("dialog[open]").count() == 0
    assert "side" in remote_branches(world["root"] / "gamma-origin.git")
    button = del_button(page, "remote:side")  # the same by keyboard alone: open, Escape, focus comes back, nothing deleted
    button.focus()
    page.keyboard.press("Enter")
    assert page.locator("dialog[open]").count() == 1
    page.keyboard.press("Escape")
    assert page.locator("dialog[open]").count() == 0
    assert page.evaluate("document.activeElement.dataset.del") == "remote:side"
    assert "side" in remote_branches(world["root"] / "gamma-origin.git")


def test_confirming_deletes_that_branch_only_shows_the_undo_and_updates_the_row_remote_then_local(page, world):
    bare = world["root"] / "gamma-origin.git"
    sha = git(world["root"] / "gamma", "rev-parse", "refs/remotes/origin/side")
    open_gamma(page)
    del_button(page, "remote:side").click()
    page.get_by_role("button", name="Delete branch").click()
    page.wait_for_function("document.querySelector('#result') && !document.querySelector('#result').hidden")
    result = page.locator("#result").inner_text()
    assert "Deleted remote branch side" in result and sha[:7] in result and f"git push origin {sha}:refs/heads/side" in result
    assert "side" not in remote_branches(bare) and "work" in remote_branches(bare) and "main" in remote_branches(bare)
    page.wait_for_function("!document.querySelector('tr.detail:not([hidden])').innerText.includes('origin/side')")
    assert page.locator("tr.detail:not([hidden]) [data-del='remote:side']").count() == 0
    del_button(page, "local:merged-local").click()  # a local branch goes the same way
    page.get_by_role("button", name="Delete branch").click()
    page.wait_for_function("document.querySelector('#result').innerText.includes('local branch merged-local')")
    assert "merged-local" not in git(world["root"] / "gamma", "branch", "--format=%(refname:short)").split()
    assert "work" in remote_branches(bare)
    assert page.errors == []


def test_a_closed_unmerged_pull_request_branch_gets_a_button_and_a_stronger_warning(page, world, monkeypatch):
    tip = git(world["root"] / "gamma", "rev-parse", "refs/remotes/origin/work")
    monkeypatch.setattr(bd, "pull_requests", lambda s, b, c: [{"number": 11, "state": "CLOSED", "headRefName": b, "headRefOid": tip}] if b == "work" else [])
    page.click("#refresh")
    page.wait_for_function("document.body.innerText.includes('Refreshed')")
    open_gamma(page)
    del_button(page, "remote:work").click()
    dialog = page.locator("dialog[open]")
    assert "closed pull request #11" in dialog.inner_text() and "never merged" in dialog.inner_text()
    page.get_by_role("button", name="Delete branch").click()
    page.wait_for_function("document.querySelector('#result') && !document.querySelector('#result').hidden")
    assert "work" not in remote_branches(world["root"] / "gamma-origin.git")


def test_a_refusal_after_the_page_looked_is_shown_in_the_dialog_and_nothing_goes(page, world, monkeypatch):
    open_gamma(page)
    del_button(page, "remote:side").click()
    monkeypatch.setattr(bd, "pull_requests", lambda s, b, c: [{"number": 5, "state": "OPEN", "headRefName": b, "headRefOid": "x"}])
    page.get_by_role("button", name="Delete branch").click()
    page.wait_for_selector("dialog[open] [role=alert]:not([hidden])")
    assert "open pull request, #5" in page.locator("dialog[open]").inner_text()
    assert page.errors == ["Failed to load resource: the server responded with a status of 409 (Conflict)"]  # the browser's note of the refusal
    page.errors.clear()
    assert page.locator("dialog[open]").get_by_role("button", name="Delete branch").is_disabled()
    assert "side" in remote_branches(world["root"] / "gamma-origin.git")
    page.get_by_role("button", name="Close").click()
    assert page.locator("dialog[open]").count() == 0


def test_the_dialog_fits_a_phone_without_sideways_scrolling(world, monkeypatch):
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = open_page(browser, world["url"], 4)
        page.set_viewport_size({"width": 390, "height": 800})
        page.locator("button.name", has_text="gamma").click()
        page.wait_for_selector("tr.detail:not([hidden]) [data-del]")
        assert page.evaluate("document.documentElement.scrollWidth <= 390")
        del_button(page, "remote:side").click()
        box = page.locator("dialog[open]").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390
        assert page.evaluate("document.documentElement.scrollWidth <= 390")
        browser.close()


def test_in_read_only_mode_there_are_no_delete_buttons_and_no_questions_asked(tmp_path, monkeypatch, world):
    import threading
    monkeypatch.setattr(srv, "lan_addresses", lambda: [])
    monkeypatch.setattr(srv, "lan_hostnames", lambda: set())
    server = srv.make_server(0, [str(world["root"])], lan=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(srv.Handler, "_peer", lambda self: "private")
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch()
            page = open_page(browser, f"http://127.0.0.1:{server.server_address[1]}/", 4)
            page.locator("button.name", has_text="gamma").click()
            settled(page)
            page.wait_for_selector("tr.detail:not([hidden])")
            assert "origin/side" in page.locator("tr.detail:not([hidden])").inner_text()  # the list and the copyable command stay
            assert page.locator("[data-del]").count() == 0
            assert not any("/api/branch" in r for r in page.requests)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
