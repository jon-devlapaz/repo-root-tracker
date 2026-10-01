import json

from test_board import PATHS, goto_board, page


def mock_activity(page):
    def handler(route):
        keys = page.evaluate("[replayKey(0), replayKey(2), replayKey(9)]")
        route.fulfill(json={'days': 30, 'repos': {PATHS[0]: {keys[0]: 3, keys[2]: 1}, PATHS[1]: {keys[1]: 5}}})
    page.route('**/api/activity?*', handler)


def test_replay_glows_the_trees_touched_today_and_fades_recent_days(page):
    mock_activity(page)
    goto_board(page)
    assert page.locator('.tile[data-glow]').count() == 0
    page.get_by_role('button', name='Replay', exact=True).click()
    page.wait_for_selector('#board-replay-controls', state='visible')
    assert page.get_by_role('button', name='Replay', exact=True).get_attribute('aria-pressed') == 'true'
    # today: PATHS[0] committed today (full glow); PATHS[1] two days ago has faded to .3
    assert page.locator(f'.tile[data-path="{PATHS[0]}"]').get_attribute('data-glow') == '1'
    assert page.locator(f'.tile[data-path="{PATHS[1]}"]').get_attribute('data-glow') == '0.3'
    assert page.locator(f'.tile[data-path="{PATHS[2]}"]').get_attribute('data-glow') is None
    assert 'Today' in page.locator('#board-replay-day').inner_text() and 'dirty 3' in page.locator('#board-replay-day').inner_text()


def test_scrubbing_moves_through_days_and_closing_clears_everything(page):
    mock_activity(page)
    goto_board(page)
    page.get_by_role('button', name='Replay', exact=True).click()
    page.wait_for_selector('#board-replay-controls', state='visible')
    page.locator('#board-replay-range').fill('28')  # two days ago
    assert page.locator(f'.tile[data-path="{PATHS[1]}"]').get_attribute('data-glow') == '1'
    assert 'ahead 5' in page.locator('#board-replay-day').inner_text()
    page.locator('#board-replay-range').fill('10')  # twenty days ago: nothing happened
    assert page.locator('.tile[data-glow]').count() == 0
    assert 'quiet' in page.locator('#board-replay-day').inner_text()
    page.get_by_role('button', name='Replay', exact=True).click()
    assert page.locator('#board-stage').get_attribute('data-replay') is None
    assert page.locator('#board-replay-controls').is_hidden()


def test_replay_survives_a_board_re_render(page):
    mock_activity(page)
    goto_board(page)
    page.get_by_role('button', name='Replay', exact=True).click()
    page.wait_for_selector('#board-replay-controls', state='visible')
    page.evaluate('renderBoard()')
    assert page.locator(f'.tile[data-path="{PATHS[0]}"]').get_attribute('data-glow') == '1'


def test_play_walks_forward_to_today_and_a_failed_load_closes_replay(page):
    mock_activity(page)
    goto_board(page)
    page.get_by_role('button', name='Replay', exact=True).click()
    page.wait_for_selector('#board-replay-controls', state='visible')
    page.locator('#board-replay-range').fill('29')
    page.get_by_role('button', name='Play', exact=True).click()
    page.wait_for_function('boardReplay.ago < 28')
    page.get_by_role('button', name='Pause', exact=True).click()
    page.unroute('**/api/activity?*')
    page.route('**/api/activity?*', lambda route: route.fulfill(status=500, json={'error': 'x'}))
    page.evaluate('boardReplay.data = null; boardReplay.open = false;')
    page.get_by_role('button', name='Replay', exact=True).click()
    page.wait_for_function('!boardReplay.open')
    assert page.locator('#board-replay-controls').is_hidden()
