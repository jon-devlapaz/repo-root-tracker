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
    ids = page.evaluate("[...document.querySelectorAll('[aria-label=View] > button')].map(b => b.id)")
    assert ids == ["view-board", "view-list"]
    page.locator("#view-board").click()
    page.wait_for_selector("#board-view", state="visible")


def test_board_uses_the_wide_layout(open_at):
    page = open_at()
    page.wait_for_selector("#board-stage", state="visible")
    box = page.locator("#board-stage").bounding_box()
    assert box["width"] > 900 and box["height"] > 520
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_first_paint_groups_worktrees_before_any_status_arrives():
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.route("http://dashboard.test/", lambda route: route.fulfill(
            content_type="text/html", body=DASHBOARD.read_text().replace("__HOME__", "/home/test", 1)))
        context.route("**/api/organization", lambda route: route.fulfill(
            json={"revision": 1, "pins": [], "collections": [], "assignments": {}, "collapsed": [],
                  "grouping": "collection", "sort": "name", "githubEnabled": False}))
        ident = {"project_id": "/p/main/.git", "project_path": "/p/main"}
        context.route("**/api/repos", lambda route: route.fulfill(json=[
            {"path": "/p/main", **ident, "is_worktree": False},
            {"path": "/p/wt", **ident, "is_worktree": True}]))
        # Statuses never answer: grouping must not depend on them.
        context.route("**/api/repos/status?*", lambda route: None)
        page = context.new_page()
        page.goto("http://dashboard.test/#/board")
        page.wait_for_function("boardProjects.length > 0")
        assert page.evaluate("boardProjects.length") == 1
        assert page.evaluate("boardProjects[0].paths.length") == 2
        browser.close()


def test_phone_shows_the_island_above_the_fold_with_sign_out_beside_the_view_buttons(open_at):
    page = open_at()
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_selector("#board-stage", state="visible")
    page.evaluate("document.getElementById('signout').hidden = false")
    stage = page.locator("#board-stage").bounding_box()
    assert stage["y"] < 700, "island should start above the fold"
    board = page.locator("#view-board").bounding_box()
    out = page.locator("#signout button").bounding_box()
    assert abs(board["y"] - out["y"]) < 12, "sign out shares the view-button row"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    tools = page.locator(".board-islands-tools").bounding_box()
    assert tools["y"] > stage["y"], "island controls follow the island on a phone"


def test_island_caption_is_not_truncated_on_a_phone(open_at):
    page = open_at()
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_selector("#board-stage", state="visible")
    caption = page.locator("[data-island] text").first.text_content()
    assert "…" not in caption and caption.endswith("projects")
