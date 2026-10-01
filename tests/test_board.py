from pathlib import Path
from urllib.parse import quote, unquote

import pytest

from organization_fake import route_organization

playwright = pytest.importorskip('playwright.sync_api')
DASHBOARD = Path(__file__).parents[1] / 'src/repo_root_tracker/dashboard.html'
KEY = 'repo-root-tracker.organization.v1'
PATHS = ['/workspace/repos/' + name for name in ['dirty', 'ahead', 'stale', 'clean', 'noupstream']]


def status_for(path):
    dirty = path.endswith('/dirty')
    ahead = path.endswith('/ahead')
    return {
        'branch': 'feature' if ahead else 'main',
        'dirty': {'is_clean': not dirty, 'modified': 2 if dirty else 0, 'staged': 0, 'untracked': 0},
        'sync': {'has_upstream': not path.endswith('/noupstream'), 'ahead': 2 if ahead else 0, 'behind': 1 if ahead else 0},
        'stale_branches': [{'name': 'old-branch', 'last_commit_date': '2025-01-01T00:00:00Z'}] if path.endswith('/stale') else [],
        'last_commit': {'relative': '2 hours ago' if dirty else 'just now', 'date': '2026-01-01T12:00:00Z'},
    }


@pytest.fixture()
def page():
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        route_organization(page)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('http://dashboard.test/', lambda route: route.fulfill(content_type='text/html', body=DASHBOARD.read_text().replace('__HOME__', '/home/test', 1)))
        page.route('**/api/repos', lambda route: route.fulfill(json=[{'path': path} for path in PATHS]))

        def status(route):
            path = unquote(route.request.url.split('path=', 1)[1])
            if 'gone' in path:
                route.fulfill(status=410, json={'error': 'Gone from disk', 'gone': True})
            elif 'broken' in path:
                route.fulfill(status=503, json={'error': 'git failed'})
            else:
                route.fulfill(json=status_for(path))

        page.route('**/api/repos/status?*', status)
        page.goto('http://dashboard.test/')
        page.wait_for_function('repos.length === 5 && repos.every(r => r._status)')
        yield page
        assert errors == []
        browser.close()


def goto_board(page):
    page.evaluate("location.hash = '#/board'")
    page.wait_for_selector('#board-view .tile[data-stage]', timeout=5000)  # CI runners are slow; the real ground paints after first paint
    page.wait_for_function('!refreshingBoard')


def tile_stages(page):
    return page.locator('#board-view .tile').evaluate_all("els => els.map(el => el.dataset.stage)")


def selected_tile(page):
    return page.locator('#board-view .board-select').first


def click_plot(locator):
    locator.locator('[data-tree-variant]').click()


def test_board_routes(page):
    page.get_by_role('button', name='Board', exact=True).click()
    playwright.expect(page.locator('#board-view')).to_be_visible()
    playwright.expect(page.locator('#list-view')).not_to_be_visible()
    page.wait_for_function('!refreshingBoard')
    click_plot(selected_tile(page))
    assert page.evaluate('location.hash') == '#/board'
    playwright.expect(page.locator('#board-inspector')).to_contain_text('dirty')
    page.locator('#board-open-details').click()
    playwright.expect(page.locator('#back-btn')).to_be_visible()
    playwright.expect(page.locator('#board-view')).not_to_be_visible()
    page.locator('#back-btn').click()
    assert page.evaluate('location.hash') == '#/board'
    page.wait_for_function("document.activeElement.id.startsWith('board-tile-')")
    page.get_by_role('button', name='List', exact=True).click()
    playwright.expect(page.locator('#list-view')).to_be_visible()


def test_board_tile_count_and_order(page):
    goto_board(page)
    assert page.locator('#board-view .tile').count() == len(PATHS)
    paths = page.locator('.board-select').evaluate_all('els => els.map(el => el.dataset.path)')
    assert paths == PATHS
    page.evaluate("location.hash = '#/'")
    page.locator('#repo-sort').select_option('recent')
    page.locator('#repo-grouping').select_option('folder')
    goto_board(page)
    assert page.locator('.board-select').evaluate_all('els => els.map(el => el.dataset.path)') == paths


def test_board_stage_mapping(page):
    goto_board(page)
    assert tile_stages(page) == ['attention-dirty', 'attention-sync', 'attention-stale', 'healthy', 'healthy']
    assert 'Local changes' in selected_tile(page).inner_text()
    assert selected_tile(page).locator('[data-marker="local-work"]').count() == 1


def test_board_upstream_badge(page):
    goto_board(page)
    tiles = page.locator('#board-view .tile')
    assert tiles.nth(4).get_attribute('data-stage') == 'healthy'
    assert tiles.nth(4).locator('[data-badge="no-upstream"]').is_visible()
    assert tiles.nth(3).locator('[data-badge="no-upstream"]').count() == 0
    click_plot(tiles.nth(4).locator('button'))
    assert 'No upstream configured' in page.locator('#board-inspector').inner_text()


def test_board_stage_precedence(page):
    def status(route):
        data = status_for(unquote(route.request.url.split('path=', 1)[1]))
        data['stale_branches'] = [{'name': 'old'}]
        if not data['dirty']['is_clean']:
            data['sync'] = {'has_upstream': True, 'ahead': 3, 'behind': 0}
        route.fulfill(json=data)

    page.route('**/api/repos/status?*', status)
    goto_board(page)
    assert tile_stages(page)[:3] == ['attention-dirty', 'attention-sync', 'attention-stale']
    assert page.evaluate("repoStage({ok:true,status:200},{dirty:{},sync:{}}).stage") == 'loading'


def test_board_keyboard_nav(page):
    goto_board(page)
    selected_tile(page).focus()
    page.keyboard.press('Enter')
    assert selected_tile(page).get_attribute('aria-pressed') == 'true'
    assert page.evaluate('location.hash') == '#/board'
    page.locator('#board-open-details').focus()
    page.keyboard.press('Enter')
    assert page.evaluate('location.hash').startswith('#/repo/')


def test_board_focus_visible(page):
    goto_board(page)
    selected_tile(page).evaluate('el => el.focus({focusVisible:true})')
    assert selected_tile(page).evaluate("el => el.matches(':focus-visible')")
    assert selected_tile(page).evaluate('el => getComputedStyle(el).outlineStyle') != 'none'


def test_board_pin_marker(page):
    page.evaluate('paths => { organization.pins = [paths[0]]; persistOrganization(); }', PATHS)
    goto_board(page)
    assert selected_tile(page).locator('.tile-pin').is_visible()
    assert 'pinned' in selected_tile(page).get_attribute('aria-label')
    page.reload()
    page.wait_for_function('repos.every(r => r._status) && !refreshingBoard')
    assert selected_tile(page).locator('.tile-pin').is_visible()


def test_board_tile_link_href(page):
    goto_board(page)
    for i, path in enumerate(PATHS):
        click_plot(page.locator('.board-select').nth(i))
        assert page.locator('#board-open-details').get_attribute('href') == '#/repo/' + quote(path, safe='')
    assert page.locator('.board-label').count() == len(PATHS)
    assert '2 hours ago' in page.locator('.board-label').first.inner_text()
    assert page.locator('.board-label').first.locator('.tile-status').count() >= 1


def test_board_tile_a11y_names(page):
    goto_board(page)
    names = page.locator('.board-select').evaluate_all("els => els.map(el => el.getAttribute('aria-label'))")
    assert len(names) == len(PATHS)
    assert PATHS[0] in names[0] and 'Local changes' in names[0]
    assert 'Working tree clean' in names[3]
    assert 'GitHub not checked' in names[3]


def test_board_reduced_motion(page):
    page.emulate_media(reduced_motion='reduce')
    goto_board(page)
    assert page.evaluate("matchMedia('(prefers-reduced-motion:reduce)').matches")
    assert page.locator('.board-select').count() == len(PATHS)


def test_board_refresh(page):
    goto_board(page)
    page.route('**/api/repos/status?*', lambda route: route.fulfill(status=410, json={'error':'gone'}))
    page.locator('#board-refresh').click()
    page.wait_for_function('!refreshingBoard')
    assert tile_stages(page) == ['gone'] * len(PATHS)
    assert page.evaluate('repos.every(r => r._status.gone)')
    page.route('**/api/repos/status?*', lambda route: route.fulfill(status=503, json={'error':'broken'}))
    page.locator('#board-refresh').click()
    page.wait_for_function('!refreshingBoard')
    assert tile_stages(page) == ['error'] * len(PATHS)
    assert page.locator('#board-refresh').is_enabled()


def test_board_empty_state(page):
    page.evaluate("repos = []; location.hash = '#/board'")
    playwright.expect(page.locator('#board-empty')).to_be_visible()
    assert page.locator('#board-empty-add').get_attribute('href') == '#/'
    assert page.locator('.board-select').count() == 0


def many_repos(page):
    paths = [f'/workspace/repos/r{i:02d}' for i in range(26)]
    page.evaluate('paths => { repos = paths.map(path => ({path})); }', paths)
    goto_board(page)
    return paths


def test_board_pager_layout(page):
    many_repos(page)
    assert page.locator('.tile').count() == 25
    assert page.locator('.board-select').count() == 25
    assert page.locator('#board-next').is_visible()
    assert 'Page 1 of 2' in page.locator('#board-page-status').inner_text()


def test_board_pager_reset(page):
    many_repos(page)
    page.locator('#board-next').click()
    page.evaluate('repos = repos.slice(0,2); renderBoard();')
    assert 'Page 1 of 1' in page.locator('#board-page-status').inner_text()
    assert page.locator('.board-select').count() == 2


def test_board_pager_persist(page):
    many_repos(page)
    page.route('**/api/repo?*', lambda route: route.fulfill(status=410, json={'error':'gone'}))
    page.locator('#board-next').click()
    click_plot(selected_tile(page))
    page.locator('#board-open-details').click()
    playwright.expect(page.locator('#back-btn')).to_be_visible()
    page.locator('#back-btn').click()
    assert 'Page 2 of 2' in page.locator('#board-page-status').inner_text()
    page.wait_for_function("document.activeElement.id.startsWith('board-tile-')")
    page.locator('#board-refresh').click()
    page.wait_for_function('!refreshingBoard')
    assert 'Page 2 of 2' in page.locator('#board-page-status').inner_text()


def test_board_first_paint(page):
    held = []
    page.route('**/api/repos/status?*', lambda route: held.append(route))
    page.evaluate("location.hash = '#/board'")
    page.wait_for_selector('.board-select', timeout=1000)
    assert page.locator('.tile[data-stage="loading"]').count() == len(PATHS)
    while page.evaluate('refreshingBoard'):
        page.wait_for_function('boardControllers.size > 0')
        for route in list(held):
            held.remove(route)
            route.fulfill(json=status_for(unquote(route.request.url.split('path=', 1)[1])))
        page.wait_for_timeout(20)
    assert tile_stages(page) == ['attention-dirty', 'attention-sync', 'attention-stale', 'healthy', 'healthy']
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def test_board_palette_command(page):
    page.keyboard.press('Control+k')
    page.locator('#palette-input').fill('board')
    assert 'board view' in page.locator('.palette-item').first.inner_text().lower()
    page.keyboard.press('Enter')
    playwright.expect(page.locator('#board-view')).to_be_visible()
    page.keyboard.press('Control+k')
    page.locator('#palette-input').fill('dirty')
    page.keyboard.press('Enter')
    assert page.evaluate('location.hash').startswith('#/repo/')


def test_board_worktree_labels(page):
    def status(route):
        path = unquote(route.request.url.split('path=', 1)[1])
        data = status_for(path)
        if path in PATHS[:2]:
            data.update(project_id='/actual/git/common', project_path=PATHS[0], is_worktree=path == PATHS[1])
        route.fulfill(json=data)

    page.route('**/api/repos/status?*', status)
    page.evaluate('paths => { repos[0]._status.project_id = repos[1]._status.project_id = "/actual/git/common"; repos[0]._status.project_path = repos[1]._status.project_path = paths[0]; repos[1]._status.is_worktree = true; repos.forEach(r=>rememberRepoMetadata(r.path,r._status)); rebuildProjectModel(); }', PATHS)
    goto_board(page)
    assert page.locator('.board-family').count() == 0
    assert page.locator('.tile').count() == 4
    assert page.locator('#board-pager').is_hidden()
    project = page.locator('.tile[data-project="git:/actual/git/common"]')
    assert project.locator('.board-select').count() == 2
    assert project.locator('[id="board-tile-' + quote(PATHS[0], safe='') + '"]').count() == 1
    assert project.locator('[id="board-tile-' + quote(PATHS[1], safe='') + '"]').count() == 1
    names = project.locator('.tile-name').all_text_contents()
    assert names == ['dirty', 'feature']
    assert 'Linked worktree' in project.locator('.board-label').nth(1).inner_text()


def test_scene_has_accessible_labels_without_card_nameplates(page):
    many_repos(page)
    for width in [1280, 390]:
        page.set_viewport_size({'width':width,'height':900})
        page.get_by_role('button', name='Fit island', exact=True).click()
        assert page.locator('[data-island]').count() == 1
        assert page.locator('.board-select').count() == 25
        assert page.locator('.board-label').evaluate_all("els => els.every(el => getComputedStyle(el).clipPath === 'inset(50%)')")
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def test_search_and_attention_dim_without_repositioning(page):
    goto_board(page)
    before = page.locator('.tile').evaluate_all('els => els.map(el => { const r=el.getBoundingClientRect(); return [r.x,r.y]; })')
    page.get_by_role('searchbox', name='Search the island').fill('ahead')
    assert page.locator('.tile:not(.dimmed)').count() == 1
    assert page.locator('.tile').evaluate_all('els => els.map(el => { const r=el.getBoundingClientRect(); return [r.x,r.y]; })') == before
    page.get_by_role('searchbox', name='Search the island').press('Enter')
    assert page.locator('#board-inspector').get_by_role('heading').inner_text() == 'ahead'
    page.get_by_role('searchbox', name='Search the island').fill('')
    page.get_by_label('Needs attention', exact=True).check()
    assert page.locator('.tile:not(.dimmed)').count() == 0
    assert page.locator('.tile').count() == len(PATHS)


def test_local_cleanliness_and_github_blockers_stay_separate(page):
    goto_board(page)
    page.evaluate('''() => {
      repos[3]._github = {has_github:true,prs:[{number:1,ci:{state:'fail',failing:1}}],issues:[],errors:[]};
      renderBoard();
    }''')
    tile = page.locator('.board-select').nth(3)
    assert 'Working tree clean' in tile.inner_text()
    assert '1 PR with blockers' in tile.inner_text()
    click_plot(tile)
    assert '1 PR with blockers' in page.locator('#board-inspector').inner_text()
    page.get_by_label('Needs attention', exact=True).check()
    assert page.locator('.tile:not(.dimmed)').count() == 1


def test_board_refresh_keeps_selection_and_positions(page):
    goto_board(page)
    click_plot(selected_tile(page))
    before = page.locator('.tile').evaluate_all('els => els.map(el => [el.dataset.path, el.getBoundingClientRect().x, el.getBoundingClientRect().y])')
    page.route('**/api/repos/status?*', lambda route: route.fulfill(json=status_for('/workspace/repos/clean')))
    page.locator('#board-refresh').click()
    page.wait_for_function('!refreshingBoard')
    assert selected_tile(page).get_attribute('aria-pressed') == 'true'
    assert 'Working tree clean' in page.locator('#board-inspector').inner_text()
    assert page.locator('.tile').evaluate_all('els => els.map(el => [el.dataset.path, el.getBoundingClientRect().x, el.getBoundingClientRect().y])') == before


def test_board_timeout_and_late_response_are_not_clean(page):
    goto_board(page)
    result = page.evaluate('''async () => {
      const original = window.fetch;
      const waiting = [];
      window.fetch = () => new Promise(resolve => waiting.push(resolve));
      const first = fetchBoardStatus(0);
      const second = fetchBoardStatus(0);
      waiting[1]({ok:false,status:503,json:async () => ({error:'failed'})});
      await second;
      waiting[0]({ok:true,status:200,json:async () => ({dirty:{is_clean:true}})});
      await first;
      window.fetch = original;
      return repos[0]._status;
    }''')
    assert result['error']
    assert selected_tile(page).locator('.tile-status').first.inner_text() == 'Status unavailable'
    page.route('**/api/repos/status?*', lambda route: None)
    page.locator('#board-refresh').click()
    page.wait_for_function('!refreshingBoard', timeout=25000)
    assert tile_stages(page) == ['error'] * len(PATHS)
