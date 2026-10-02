"""Board is the home page; the list lives at #/list."""

from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
DASHBOARD = Path(__file__).parents[1] / "src/repo_root_tracker/dashboard.html"
PATHS = ["/p/a", "/p/b"]


@pytest.fixture
def open_at():
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.route("http://dashboard.test/", lambda route: route.fulfill(
            content_type="text/html", body=DASHBOARD.read_text().replace("__HOME__", "/home/test", 1)))
        context.route("**/api/organization", lambda route: route.fulfill(
            json={"revision": 1, "pins": [], "collections": [], "assignments": {}, "collapsed": [],
                  "grouping": "collection", "sort": "name", "githubEnabled": False}))
        context.route("**/api/repos", lambda route: route.fulfill(json=[{"path": x} for x in PATHS]))
        context.route("**/api/repos/status?*", lambda route: route.fulfill(
            json={"branch": "main", "dirty": {"is_clean": True}, "sync": {"has_upstream": False}}))

        def go(hash_=""):
            page = context.new_page()
            page.goto("http://dashboard.test/" + hash_)
            return page
        yield go
        browser.close()


@pytest.mark.parametrize("start", ["", "#", "#/"])
def test_root_opens_the_board(open_at, start):
    page = open_at(start)
    page.wait_for_selector("#board-view", state="visible")
    assert page.evaluate("location.hash") == "#/board"
    assert page.locator("#list-view").is_hidden()


def test_list_lives_at_list_route_and_board_button_comes_first(open_at):
    page = open_at("#/list")
    page.wait_for_selector("#list-view", state="visible")
    assert page.locator("#view-list").get_attribute("aria-pressed") == "true"
    ids = page.evaluate("[...document.querySelectorAll('[aria-label=View] button')].map(b => b.id)")
    assert ids == ["view-board", "view-list"]
    page.locator("#view-board").click()
    page.wait_for_selector("#board-view", state="visible")


def test_board_uses_the_wide_layout(open_at):
    page = open_at()
    page.wait_for_selector("#board-stage", state="visible")
    box = page.locator("#board-stage").bounding_box()
    assert box["width"] > 900 and box["height"] > 520
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
