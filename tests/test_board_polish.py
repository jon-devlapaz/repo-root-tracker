from urllib.parse import unquote

from test_board import PATHS, goto_board, many_repos, page, selected_tile, status_for


def test_direct_board_load_groups_metadata_after_initial_checks(page):
    def status(route):
        path = unquote(route.request.url.split('path=', 1)[1])
        data = status_for(path)
        if path in PATHS[:2]:
            data.update(project_id='/git/common', project_path=PATHS[0], is_worktree=path == PATHS[1])
        route.fulfill(json=data)

    page.route('**/api/repos/status?*', status)
    page.goto('http://dashboard.test/#/board')
    page.reload()
    page.wait_for_function('boardLayoutReady && repos.every(r => r._status && !r._checking)')
    assert page.locator('.board-family .board-select').count() == 2
    assert page.locator('.board-family .tile-name').all_text_contents() == ['dirty', 'feature']


def test_mobile_panel_and_keyboard_close_restore_selection_focus(page):
    goto_board(page)
    page.set_viewport_size({'width':390,'height':844})
    selected_tile(page).click()
    assert page.locator('#board-inspector').is_visible()
    assert page.locator('#board-inspector').evaluate('el => getComputedStyle(el).position') == 'fixed'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.keyboard.press('Escape')
    assert not page.locator('#board-inspector').is_visible()
    assert selected_tile(page).evaluate('el => el === document.activeElement')
    page.keyboard.press('Enter')
    page.keyboard.press('Tab')
    assert page.locator('#board-open-details').evaluate('el => el === document.activeElement')


def test_search_selects_match_on_other_page_without_reordering(page):
    paths = many_repos(page)
    page.get_by_role('searchbox', name='Search the island').fill('r25')
    assert '1 of 26 matching' in page.locator('#board-match-count').inner_text()
    page.get_by_role('searchbox', name='Search the island').press('Enter')
    assert 'Page 2 of 2' in page.locator('#board-page-status').inner_text()
    assert page.locator('.board-select').get_attribute('data-path') == paths[-1]
    assert page.locator('#board-inspector').get_by_role('heading').inner_text() == 'r25'


def test_board_origin_change_discards_old_github_signals(page):
    goto_board(page)
    page.evaluate("repos[0]._github = {repo:'old/project',has_github:true,prs:[{number:1,ci:{state:'fail',failing:1}}],issues:[]};")

    def status(route):
        data = status_for(unquote(route.request.url.split('path=', 1)[1]))
        data['github_repo'] = 'new/project'
        route.fulfill(json=data)

    page.route('**/api/repos/status?*', status)
    page.locator('#board-refresh').click()
    page.wait_for_function('!refreshingBoard')
    assert page.evaluate('repos[0]._github === undefined')
    assert 'GitHub not checked' in selected_tile(page).inner_text()
