from urllib.parse import quote

from test_board import PATHS, click_plot, goto_board, page, selected_tile


def test_brief_names_what_needs_you_and_calm_is_celebrated(page):
    page.evaluate("""() => { repos[0]._status.dirty = {is_clean: false, kinds: {conflicted: 1}, modified: 1}; render(); }""")
    brief = page.locator('#list-brief').inner_text()
    assert 'dirty is blocked' in brief
    page.evaluate("""() => { repos.forEach(r => { r._status.dirty = {is_clean: true}; r._status.sync = {has_upstream: true, ahead: 0, behind: 0}; r._status.stale_branches = []; }); render(); }""")
    assert page.locator('#list-brief').inner_text() == 'All 5 repos are calm.'


def test_title_counts_what_needs_action_and_favicon_follows_the_worst_state(page):
    calm = """() => { repos.forEach(r => { r._status.dirty = {is_clean: true}; r._status.sync = {has_upstream: true, ahead: 0, behind: 0}; r._status.stale_branches = []; }); }"""
    page.evaluate(calm + "; render();")
    assert page.title() == 'repo-root-tracker'
    calm_icon = page.locator('#favicon').get_attribute('href')
    page.evaluate("() => { repos[1]._status = {error: true, gone: true}; repos[2]._status.dirty = {is_clean: false, kinds: {conflicted: 1}, modified: 1}; render(); }")
    assert page.title() == '(2) repo-root-tracker'
    blocked_icon = page.locator('#favicon').get_attribute('href')
    assert blocked_icon != calm_icon and quote('#e8705c') in blocked_icon


def test_summary_is_available_on_the_board_too(page):
    goto_board(page)
    assert 'uncommitted' in page.locator('#board-brief').inner_text()


def test_arrow_keys_walk_between_trees(page):
    goto_board(page)
    first = page.locator('.board-select').first
    first.focus()
    seen = [page.evaluate('document.activeElement.dataset.path')]
    for key in ['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp']:
        page.keyboard.press(key)
        seen.append(page.evaluate('document.activeElement.dataset.path'))
    assert all(p in PATHS for p in seen)
    assert len(set(seen)) >= 3
    assert page.evaluate('boardSelectedPath') is None  # walking is not selecting


def test_inspector_copies_the_path_and_links_to_the_editor(page):
    goto_board(page)
    page.evaluate("window.__copied = null; Object.defineProperty(navigator, 'clipboard', {value: {writeText: async v => { window.__copied = v; }}, configurable: true});")
    click_plot(selected_tile(page))
    link = page.locator('#board-open-editor')
    assert link.get_attribute('href') == 'vscode://file' + PATHS[0]
    page.get_by_role('button', name='Copy path', exact=True).click()
    page.wait_for_function('window.__copied !== null')
    assert page.evaluate('window.__copied') == PATHS[0]


def test_palette_verbs_follow_the_selection(page):
    goto_board(page)
    click_plot(selected_tile(page))
    page.keyboard.press('Meta+k')
    page.locator('#palette-input').fill('copy')
    assert 'copy path of dirty' in page.locator('.palette-item').first.inner_text().lower()
    page.locator('#palette-input').fill('list')
    assert 'list view' in page.locator('.palette-item').first.inner_text().lower()
