import math
from urllib.parse import unquote

import pytest

from test_board import goto_board, page, status_for  # noqa: F401

MANY = [f'/workspace/many/repo{i:03d}' for i in range(90)]


@pytest.fixture()
def many(page):
    page.route('**/api/repos', lambda route: route.fulfill(json=[{'path': p} for p in MANY]))

    def status(route):
        path = unquote(route.request.url.split('path=', 1)[1])
        i = int(path[-3:])
        data = status_for('/workspace/repos/clean')
        if i % 7 == 0:
            data['dirty'] = {'is_clean': False, 'modified': 3, 'staged': 0, 'untracked': 0}
        if i % 11 == 0:
            data['sync'] = {'has_upstream': True, 'ahead': 1, 'behind': 0}
        route.fulfill(json=data)

    page.route('**/api/repos/status?*', status)
    page.reload()
    page.wait_for_function('repos.length === 90 && repos.every(r => r._status)')
    return page


def test_ninety_repos_become_four_islands_with_a_map_of_all_of_them(many):
    goto_board(many)
    assert many.locator('#board-archipelago .isle').count() == math.ceil(90 / 25)
    assert many.locator('.board-select').count() == 25
    first = many.locator('#board-archipelago .isle').first
    assert first.get_attribute('aria-current') == 'true'
    assert first.locator('.isle-dot[data-tone="changed"]').count() == 1


def test_choosing_an_island_from_the_map_goes_there_and_keeps_focus(many):
    goto_board(many)
    many.locator('#board-isle-3').click()
    assert many.locator('#board-isle-3').get_attribute('aria-current') == 'true'
    assert many.locator('.board-select').count() == 15
    assert 'Island 4 of 4' in many.locator('#board-page-status').inner_text()
    assert many.evaluate('boardPage') == 4
    assert many.evaluate('document.activeElement.id') == 'board-page-status'


def test_a_single_island_shows_no_map(page):
    goto_board(page)
    assert page.locator('#board-archipelago').is_hidden()


def test_ninety_repos_render_fast_and_zoom_changes_the_level_of_detail(many):
    goto_board(many)
    ms = many.evaluate('() => { const t = performance.now(); for (let i = 0; i < 5; i++) renderBoard(); return (performance.now() - t) / 5; }')
    assert ms < 400
    many.evaluate('boardCamera.zoom = .4; boardFitPending = false; applyBoardCamera();')
    assert many.locator('#board-world').get_attribute('data-lod') == 'far'
    many.evaluate('boardCamera.zoom = 1.7; applyBoardCamera();')
    assert many.locator('#board-world').get_attribute('data-lod') == 'near'
    assert many.locator('.plot-name').count() > 0  # names appear on their own when you are close
    many.evaluate('boardCamera.zoom = 1; applyBoardCamera();')
    assert many.locator('#board-world').get_attribute('data-lod') == 'mid'
    assert many.locator('.plot-name').count() == 0
