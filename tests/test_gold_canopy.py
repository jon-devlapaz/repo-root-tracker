"""Clean (git-golden) checkouts grow a gold canopy; every other state keeps its family colour."""

from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
DASHBOARD = Path(__file__).parents[1] / "src/repo_root_tracker/dashboard.html"
GOLD_HIGH, GOLD_MID = "#ffd966", "#d4a017"
CLEAN, DIRTY = "/p/clean", "/p/dirty"


@pytest.fixture
def page():
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.route("http://dashboard.test/", lambda route: route.fulfill(
            content_type="text/html", body=DASHBOARD.read_text().replace("__HOME__", "/home/test", 1)))
        context.route("**/api/organization", lambda route: route.fulfill(
            json={"revision": 1, "pins": [], "collections": [], "assignments": {}, "collapsed": [],
                  "grouping": "collection", "sort": "name", "githubEnabled": False}))
        context.route("**/api/repos", lambda route: route.fulfill(json=[{"path": CLEAN}, {"path": DIRTY}]))

        def status(route):
            dirty = route.request.url.endswith("dirty")
            route.fulfill(json={"branch": "main", "sync": {"has_upstream": True, "ahead": 0, "behind": 0},
                                "dirty": {"is_clean": not dirty, "modified": 1 if dirty else 0,
                                          "kinds": {"modified": 1} if dirty else {}}})
        context.route("**/api/repos/status?*", status)
        page = context.new_page()
        page.goto("http://dashboard.test/#/board")
        page.wait_for_function("initialLocalBatchSettled && repos.every(r => r._status && !r._checking)")
        yield page
        browser.close()


def tree_markup(page, path):
    return page.evaluate("""(path) => {
      const button = document.querySelector(`button.board-select[data-path="${path}"]`);
      return button ? button.closest('.tile').innerHTML : '';
    }""", path)


def test_clean_checkout_is_gold_and_dirty_one_is_not_on_the_board(page):
    clean, dirty = tree_markup(page, CLEAN), tree_markup(page, DIRTY)
    assert GOLD_HIGH in clean and GOLD_MID in clean
    assert GOLD_HIGH not in dirty and GOLD_MID not in dirty


def test_list_and_inspector_sprites_follow_the_same_rule(page):
    page.evaluate("location.hash = '#/list'")
    page.wait_for_selector("#list-view .repo-card")
    sprites = page.evaluate("[...document.querySelectorAll('#list-view .repo-card')].map(c => [c.querySelector('.repo-name').textContent, c.querySelector('.repo-sprite').innerHTML.includes('%s')])" % GOLD_HIGH)
    assert dict(sprites) == {"clean": True, "dirty": False}


def test_a_dirty_checkout_turns_gold_when_it_becomes_clean(page):
    assert GOLD_HIGH not in tree_markup(page, DIRTY)
    page.evaluate("""() => { const r = repos.find(x => x.path.endsWith('dirty'));
      r._status = {...r._status, dirty: {is_clean: true, modified: 0, kinds: {}}}; renderBoard(); }""")
    page.wait_for_function("(p) => document.querySelector(`button.board-select[data-path=\"${p}\"]`)?.closest('.tile').innerHTML.includes('#ffd966')", arg=DIRTY)
