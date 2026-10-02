"""Project checkout access, tone, replay, ground, counts and accessibility."""
from urllib.parse import quote, unquote

import pytest

from test_board import page  # noqa: F401
from test_board_saplings import MAIN, WORKTREES, member, project_board


def active_path(page):
    return page.evaluate('document.activeElement.dataset.path')


def focus_style(page, path):
    return member(page, path).evaluate('''el=>{
      const mark=el.querySelector('.member-focus'),style=getComputedStyle(mark),rect=mark.getBoundingClientRect();
      return {active:document.activeElement===el,visible:el.matches(':focus-visible'),opacity:style.opacity,
        stroke:style.stroke,width:style.strokeWidth,vectorEffect:style.vectorEffect,box:[rect.width,rect.height],
        pointerEvents:style.pointerEvents,pressed:el.getAttribute('aria-pressed')};
    }''')


def assert_visible_focus(page, path):
    style = focus_style(page, path)
    assert style['active'] and style['visible'] and float(style['opacity']) > 0
    assert style['stroke'] not in ('none', 'transparent', 'rgba(0, 0, 0, 0)')
    assert float(style['width'].replace('px', '')) >= 2
    assert style['vectorEffect'] == 'non-scaling-stroke'
    assert style['box'][0] > 0 and style['box'][1] > 0
    assert style['pointerEvents'] == 'none'
    return style


def open_chooser(page, path=MAIN):
    page.evaluate('path=>selectBoardRepo(path)', path)
    page.locator('#board-inspector-worktrees').click()
    assert page.locator('#board-worktree-dialog').evaluate('el=>el.open')


def exact_chooser_row(page, path):
    # Use data attributes for exact paths, including overlapping folder prefixes.
    return page.locator('#board-worktree-list [data-checkout-path="' + path + '"]')


def test_arrows_reach_visible_saplings_without_selecting(page):
    project_board(page)
    member(page, MAIN).focus()
    for key, expected in [('ArrowLeft', WORKTREES[0]), ('ArrowRight', MAIN), ('ArrowRight', WORKTREES[1]), ('ArrowLeft', MAIN), ('ArrowDown', WORKTREES[2])]:
        page.keyboard.press(key)
        assert active_path(page) == expected
        assert page.evaluate('boardSelectedPath') is None
    page.keyboard.press('Enter')
    assert page.evaluate('boardSelectedPath') == WORKTREES[2]
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'
    page.keyboard.press('Escape')
    assert active_path(page) == WORKTREES[2]


def test_alt_arrows_reach_overflow_worktrees(page):
    paths = project_board(page, 8)
    member(page, MAIN).focus()
    before = page.evaluate('({camera:{...boardCamera},plots:boardScene.plots.map(p=>[p.x,p.y,p.number])})')
    for path in paths[1:]:
        page.keyboard.press('Alt+ArrowRight')
        assert active_path(page) == path
        assert page.evaluate('boardSelectedPath') is None
        assert member(page, path).count() == 1
        assert member(page, WORKTREES[0]).get_attribute('data-slot') == 'left'
        assert member(page, WORKTREES[1]).get_attribute('data-slot') == 'right'
    page.keyboard.press('Alt+ArrowRight')
    assert active_path(page) == MAIN
    page.wait_for_function('boardScene.targets.some(t=>t.slot==="front"&&t.path==="/projects/oak-w02")')
    page.keyboard.press('Alt+ArrowLeft')
    assert active_path(page) == WORKTREES[-1]
    assert page.evaluate('({camera:{...boardCamera},plots:boardScene.plots.map(p=>[p.x,p.y,p.number])})') == before


def test_unselected_sapling_has_visible_member_focus(page):
    project_board(page)
    member(page, MAIN).focus()
    page.keyboard.press('ArrowLeft')
    style = assert_visible_focus(page, WORKTREES[0])
    assert style['pressed'] == 'false'
    assert member(page, WORKTREES[0]).locator('.plot-flag').count() == 0
    assert member(page, MAIN).locator('.member-focus').evaluate('el=>getComputedStyle(el).opacity') == '0'
    member_box = member(page, WORKTREES[0]).bounding_box()
    assert style['box'][0] < member_box['width'] / 2


def test_member_focus_remains_visible_in_forced_colors(page):
    project_board(page)
    page.emulate_media(forced_colors='active')
    member(page, MAIN).focus()
    page.keyboard.press('ArrowRight')
    style = assert_visible_focus(page, WORKTREES[1])
    system_color = page.evaluate('''()=>{const el=document.createElement('span');el.style.color='Highlight';document.body.append(el);const color=getComputedStyle(el).color;el.remove();return color}''')
    assert style['stroke'] == system_color
    assert style['pressed'] == 'false'


def test_worktrees_action_exists_without_overflow(page):
    project_board(page, 1)
    page.evaluate('path=>selectBoardRepo(path)', MAIN)
    assert page.locator('.plot-more').count() == 0
    assert page.locator('#board-inspector-worktrees').inner_text() == 'Worktrees'
    assert page.locator('.board-checkout-list button').count() == 2
    page.locator('#board-inspector-worktrees').click()
    assert page.locator('#board-worktree-list button').count() == 2


def test_worktree_chooser_rows_are_44px_and_include_all_members(page):
    paths = project_board(page, 8)
    open_chooser(page)
    rows = page.locator('#board-worktree-list button')
    assert rows.evaluate_all('els=>els.map(el=>el.dataset.checkoutPath)') == paths
    assert rows.evaluate_all('els=>els.every(el=>el.getBoundingClientRect().height>=44&&!el.matches(".board-select")&&!el.id)')
    for path in paths:
        row = exact_chooser_row(page, path)
        text = row.inner_text()
        assert path in text and ('Main checkout' if path == MAIN else 'Linked worktree') in text
        assert ('main' if path == MAIN else 'feature/') in text
        assert 'Working tree clean' in text
    assert page.locator('[id="board-tile-' + quote(WORKTREES[-1], safe='') + '"]').count() == 0
    page.keyboard.press('Escape')
    assert page.locator('.board-checkout-list button').evaluate_all('els=>els.every(el=>el.getBoundingClientRect().height>=44)')


@pytest.mark.parametrize('cancel', ['Escape', 'Cancel'])
def test_chooser_cancellation_restores_opener(page, cancel):
    project_board(page, 8)
    open_chooser(page)
    if cancel == 'Escape':
        page.keyboard.press('Escape')
    else:
        page.locator('#board-worktree-dialog').get_by_role('button', name='Cancel').click()
    page.wait_for_function('!document.getElementById("board-worktree-dialog").open && document.activeElement.id==="board-inspector-worktrees"')
    assert page.evaluate('boardSelectedPath') == MAIN
    assert member(page, WORKTREES[-1]).count() == 0


def test_chooser_closes_then_selects_then_focuses_inspector(page):
    project_board(page, 8)
    open_chooser(page)
    page.evaluate('''() => {
      window.checkoutOrder=[];
      const original=selectBoardRepo;
      window.selectBoardRepo=(path,...args)=>{checkoutOrder.push(['select',document.getElementById('board-worktree-dialog').open,path]);return original(path,...args)};
      document.getElementById('board-worktree-dialog').addEventListener('close',()=>checkoutOrder.push(['closed',document.activeElement.id]));
      document.addEventListener('focusin',e=>{if(e.target.id==='board-inspector-title')checkoutOrder.push(['focus',document.getElementById('board-worktree-dialog').open])});
    }''')
    exact_chooser_row(page, WORKTREES[-1]).click()
    page.wait_for_function('document.activeElement.id==="board-inspector-title"')
    order = page.evaluate('checkoutOrder')
    assert order[0] == ['select', False, WORKTREES[-1]]
    assert ['focus', False] in order
    assert order[-1] == ['closed', 'board-inspector-title']
    assert page.evaluate('boardSelectedPath') == WORKTREES[-1]
    assert member(page, WORKTREES[-1]).get_attribute('aria-pressed') == 'true'
    # The chooser close event must not restore its opener after the final focus.
    page.wait_for_timeout(30)
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'


def test_mobile_chooser_selects_hidden_worktree_and_close_restores_exact_member(page):
    project_board(page, 8)
    page.set_viewport_size({'width': 390, 'height': 844})
    open_chooser(page)
    exact_chooser_row(page, WORKTREES[-1]).click()
    page.wait_for_function('document.activeElement.id==="board-inspector-title"')
    assert page.locator('#board-inspector').is_visible()
    assert page.locator('#board-inspector').evaluate('el=>getComputedStyle(el).position') == 'fixed'
    assert WORKTREES[-1] in page.locator('#board-inspector').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_role('button', name='Close panel', exact=True).click()
    assert page.evaluate('boardSelectedPath') is None
    assert active_path(page) == WORKTREES[-1]
    assert member(page, WORKTREES[-1]).get_attribute('data-slot') == 'front'
    page.keyboard.press('Space')
    assert page.evaluate('boardSelectedPath') == WORKTREES[-1]
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'
    page.keyboard.press('Escape')
    assert active_path(page) == WORKTREES[-1]


def test_worktree_selection_and_detail_return_restore_exact_path(page):
    project_board(page, 8, projects=26)
    path = '/projects/p25-w7'
    page.evaluate('path=>selectBoardRepo(path)', path)
    assert 'Page 2 of 2' in page.locator('#board-page-status').inner_text()
    assert member(page, path).get_attribute('data-slot') == 'front'
    assert page.locator('.board-select[aria-pressed="true"]').count() == 1
    assert page.locator('#board-open-details').get_attribute('href') == '#/repo/' + quote(path, safe='')
    assert page.locator('#board-open-editor').get_attribute('href') == 'vscode://file' + path
    page.route('**/api/repo?*', lambda route: route.fulfill(status=410, json={'error': 'gone'}))
    page.locator('#board-open-details').click()
    page.locator('#back-btn').click()
    page.wait_for_function('path=>document.activeElement.dataset.path===path', arg=path)
    assert member(page, path).get_attribute('data-slot') == 'front'
    assert page.evaluate('boardSelectedPath') == path


def test_worktree_search_dims_siblings_and_exposes_hidden_match(page):
    project_board(page, 8)
    before = page.evaluate('({camera:{...boardCamera},plots:boardScene.plots.map(p=>[p.x,p.y,p.number])})')
    page.get_by_role('searchbox', name='Search the island').fill('feature/07')
    assert page.locator('.tile:not(.dimmed)').count() == 1
    assert member(page, WORKTREES[-1]).get_attribute('data-matched') == 'true'
    assert member(page, WORKTREES[-1]).get_attribute('data-slot') == 'front'
    assert member(page, MAIN).get_attribute('data-matched') == 'false'
    assert member(page, WORKTREES[0]).get_attribute('data-matched') == 'false'
    assert '1 of 1 matching projects · 1 matching checkouts' in page.locator('#board-match-count').inner_text()
    assert page.evaluate('({camera:{...boardCamera},plots:boardScene.plots.map(p=>[p.x,p.y,p.number])})') == before
    page.get_by_role('searchbox', name='Search the island').press('Enter')
    # Search Enter is keyboard selection, so §4.3 requires inspector focus.
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'
    assert member(page, WORKTREES[-1]).get_attribute('aria-pressed') == 'true'
    assert page.evaluate('boardSelectedPath') == WORKTREES[-1]
    page.get_by_role('searchbox', name='Search the island').fill('oak')
    assert page.locator('.board-member[data-matched="true"]').count() == 4
    assert '9 matching checkouts' in page.locator('#board-match-count').inner_text()


def test_attention_filter_uses_project_github_and_checkout_local_problems(page):
    project_board(page, 8)
    page.evaluate("repos[8]._status.dirty={is_clean:false,kinds:{conflicted:1}};renderBoard()")
    page.get_by_label('Needs attention', exact=True).check()
    assert page.locator('.tile:not(.dimmed)').count() == 1
    assert member(page, WORKTREES[-1]).get_attribute('data-matched') == 'true'
    assert member(page, MAIN).get_attribute('data-matched') == 'false'
    page.evaluate("repos[8]._status.dirty={is_clean:false,modified:2};repos[0]._status.github_repo='oak/main';rememberRepoMetadata(repos[0].path,repos[0]._status);acceptGithubSnapshot('oak/main',1,{has_github:true,repo:'oak/main',prs:[{number:1,ci:{state:'fail',failing:1}}],issues:[]});renderBoard()")
    assert page.locator('.board-member[data-matched="true"]').count() == 4
    assert '9 matching checkouts' in page.locator('#board-match-count').inner_text()
    page.evaluate("repos[0]._status.github_repo=null;rememberRepoMetadata(repos[0].path,repos[0]._status);renderBoard()")
    assert page.locator('.tile:not(.dimmed)').count() == 0


def test_paging_limits_projects_not_checkout_buttons(page):
    project_board(page, 3, projects=26)
    assert page.locator('.tile').count() == 25
    assert page.locator('.board-member').count() == 100
    page.locator('#board-next').click()
    assert page.locator('.tile').count() == 1
    assert page.locator('.board-member').count() == 4
    assert page.evaluate('boardSelectedPath') is None
    assert page.evaluate('document.activeElement.id') == 'board-page-status'


def test_plot_description_and_checkout_list_include_overflow_members(page):
    paths = project_board(page, 8)
    description = page.locator('.tile').get_attribute('aria-description')
    assert 'oak' in description and 'Main checkout on main' in description
    assert '8 linked worktrees; 3 shown, 5 hidden' in description
    assert 'Use Worktrees to choose any checkout' in description
    page.evaluate('path=>selectBoardRepo(path)', WORKTREES[-1])
    assert 'Linked worktree of oak' in page.locator('#board-inspector').inner_text()
    rows = page.locator('.board-checkout-list button')
    assert rows.evaluate_all('els=>els.map(el=>el.dataset.checkoutPath)') == paths
    assert rows.locator('[id^="board-tile-"]').count() == 0
    # §4.3 requires heading focus after keyboard selection. Desktop pointer
    # selection is only required to select the checkout and update the panel.
    rows.first.focus()
    page.keyboard.press('Enter')
    assert page.evaluate('boardSelectedPath') == MAIN
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'


def test_names_show_projects_and_only_active_worktree_labels(page):
    project_board(page, 8)
    page.get_by_role('button', name='Names', exact=True).click()
    assert page.locator('.plot-name').count() == 1
    assert page.locator('.plot-name').inner_text() == '1 · oak'
    assert page.locator('.sapling-name').count() == 0
    member(page, MAIN).focus()
    page.keyboard.press('Alt+ArrowLeft')
    assert page.locator('.sapling-name').count() == 1
    assert page.locator('.sapling-name').inner_text() == 'feature/07'
    page.locator('.sapling-name').evaluate('el=>window.savedSaplingLabel=el')
    page.evaluate('layoutBoardNames();layoutBoardNames()')
    assert page.locator('.sapling-name').evaluate('el=>el===savedSaplingLabel')
    page.evaluate('path=>selectBoardRepo(path)', WORKTREES[-1])
    for width in [1440, 768, 390]:
        page.set_viewport_size({'width': width, 'height': 900})
        page.get_by_role('button', name='Fit island', exact=True).click()
        assert page.locator('.plot-name, .sapling-name').evaluate_all('''els=>{
          const rects=els.map(el=>el.getBoundingClientRect()),stage=document.getElementById('board-stage').getBoundingClientRect();
          return rects.every(r=>r.left>=stage.left&&r.right<=stage.right&&r.top>=stage.top&&r.bottom<=stage.bottom)&&
            !rects.some((a,i)=>rects.slice(i+1).some(b=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top))&&
            els.every(el=>parseFloat(getComputedStyle(el).fontSize)>=11);
        }''')


def test_member_hover_names_exact_checkout(page):
    project_board(page)
    path = WORKTREES[0]
    point = member(page, path).locator('.tree-hit').bounding_box()
    page.mouse.move(point['x']+point['width']/2, point['y']+point['height']/2)
    page.wait_for_function('path=>boardHoveredPath===path', arg=path)
    assert page.locator('#board-hover-tip').inner_text() == 'feature/00 · Linked worktree · oak-w00'
    assert path in page.locator('#board-caption').inner_text()


def test_health_patch_keeps_focused_member_node(page):
    project_board(page)
    member(page, MAIN).focus()
    page.keyboard.press('ArrowLeft')
    member(page, WORKTREES[0]).evaluate('el=>window.savedMember=el')
    page.evaluate("repos[1]._status.dirty={is_clean:false,modified:2};renderBoard()")
    assert member(page, WORKTREES[0]).evaluate('el=>el===savedMember&&el===document.activeElement')
    assert_visible_focus(page, WORKTREES[0])


def test_removed_focused_checkout_uses_surviving_project_default(page):
    project_board(page)
    member(page, MAIN).focus()
    page.keyboard.press('ArrowLeft')
    page.evaluate('path=>{repos=repos.filter(r=>r.path!==path);rebuildProjectModel();renderBoard()}', WORKTREES[0])
    assert active_path(page) == MAIN
    page.evaluate('repos=[];rebuildProjectModel();renderBoard()')
    assert page.evaluate('document.activeElement.id') == 'board-page-status'


def test_ninety_projects_with_worktrees_have_bounded_visible_dom(page):
    project_board(page, counts=[4] * 30 + [3] * 30 + [2] * 30)
    assert page.evaluate('boardProjects.length') == 90
    assert page.evaluate('repos.length') == 360
    assert page.locator('.tile').count() == 25
    assert page.locator('.board-member').count() == 100
    assert page.locator('.board-member > svg:not(.board-shared-marks)').count() == 100
    assert page.locator('.plot-more').all_text_contents() == ['+1'] * 25
    assert 'Page 1 of 4' in page.locator('#board-page-status').inner_text()


def test_alt_navigation_keeps_selected_overflow_pressed_and_reaches_hidden_rows(page):
    paths = project_board(page, 8)
    page.evaluate('path=>selectBoardRepo(path)', WORKTREES[-1])
    member(page, MAIN).focus()
    before = page.evaluate('boardScene.plots.map(p=>[p.x,p.y,p.number])')
    for path in paths[1:] + [MAIN]:
        page.keyboard.press('Alt+ArrowRight')
        assert page.evaluate('document.activeElement.dataset.path || document.activeElement.dataset.checkoutPath') == path
        assert page.evaluate('boardSelectedPath') == WORKTREES[-1]
        assert member(page, WORKTREES[-1]).get_attribute('data-slot') == 'front'
        assert member(page, WORKTREES[-1]).get_attribute('aria-pressed') == 'true'
        assert page.locator('.board-select[aria-pressed="true"]').count() == 1
        assert page.locator('.board-sapling').count() == 3
        assert page.locator('.plot-more').text_content() == '+5'
        assert page.evaluate('boardScene.plots.map(p=>[p.x,p.y,p.number])') == before
        if path in WORKTREES[2:-1]:
            assert member(page, path).count() == 0
            assert page.evaluate('document.activeElement.matches(".board-checkout-list button")')
            assert page.evaluate('document.activeElement.matches(":focus-visible")')
    # Reverse cycling still reaches every member, and activating a hidden row
    # changes selection, exposes that checkout, and focuses the heading.
    for path in reversed(WORKTREES[2:]):
        page.keyboard.press('Alt+ArrowLeft')
        assert page.evaluate('document.activeElement.dataset.path || document.activeElement.dataset.checkoutPath') == path
        assert member(page, WORKTREES[-1]).get_attribute('aria-pressed') == 'true'
    page.keyboard.press('Enter')
    assert page.evaluate('boardSelectedPath') == WORKTREES[2]
    assert member(page, WORKTREES[2]).get_attribute('data-slot') == 'front'
    assert member(page, WORKTREES[2]).get_attribute('aria-pressed') == 'true'
    assert page.locator('.board-select[aria-pressed="true"]').count() == 1
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'


@pytest.mark.parametrize('selected', [WORKTREES[2], WORKTREES[-1]])
def test_selected_front_member_wins_over_hidden_focus_and_search(page, selected):
    project_board(page, 8)
    page.evaluate('path=>selectBoardRepo(path)', selected)
    other = WORKTREES[-2]
    page.get_by_role('searchbox', name='Search the island').fill('feature/06')
    page.evaluate('path=>presentBoardMember(path)', other)
    assert page.evaluate('boardSelectedPath') == selected
    assert member(page, selected).get_attribute('data-slot') == 'front'
    assert member(page, selected).get_attribute('aria-pressed') == 'true'
    assert member(page, selected).locator('.plot-flag').count() == 1
    assert member(page, other).count() == 0
    assert page.locator('.board-select[aria-pressed="true"]').count() == 1
    assert page.locator('.board-sapling').count() == 3
    assert page.locator('.plot-more').text_content() == '+5'
    # Selecting the matching checkout replaces the pinned front member.
    page.get_by_role('searchbox', name='Search the island').press('Enter')
    assert page.evaluate('boardSelectedPath') == other
    assert member(page, other).get_attribute('data-slot') == 'front'
    assert member(page, other).get_attribute('aria-pressed') == 'true'
    assert page.locator('.board-select[aria-pressed="true"]').count() == 1
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'


def test_reduced_motion_stills_main_saplings_and_replay_effects(page):
    project_board(page)
    page.emulate_media(reduced_motion='reduce')
    page.evaluate('''() => {
      repos.forEach(r=>{r._status.dirty={is_clean:false,modified:3};r._status.sync={has_upstream:true,ahead:2,behind:0}});
      selectBoardRepo(repos[1].path);
      boardReplay.open=true;boardReplay.data={repos:{[repos[1].path]:{[replayKey(0)]:2}}};renderBoard();
    }''')
    assert page.locator('.board-member').count() == 4
    assert page.locator('.bonsai-sway,.tree-fx .leaf,.tree-fx .mote-up').evaluate_all("els=>els.length>0&&els.every(el=>getComputedStyle(el).animationName==='none')")
    assert page.locator('.tile,.plot-pool').evaluate_all("els=>els.every(el=>getComputedStyle(el).transitionDuration==='0s')")
    assert page.evaluate('boardReplay.timer') is None
    page.evaluate('scrubReplay(29)')
    assert page.evaluate('boardReplay.ago') == 1


def test_removal_during_held_refresh_keeps_surviving_checkout_controls(page):
    project_board(page)
    held = []
    page.route('**/api/repos/status?*', lambda route: held.append(route))
    page.evaluate('void fetchBoardAll(false)')
    page.wait_for_function('boardControllers.size===3')
    page.evaluate('path=>{repos=repos.filter(r=>r.path!==path);rebuildProjectModel();renderBoard()}', MAIN)
    assert page.locator('.tile').count() == 1
    assert member(page, MAIN).count() == 0
    assert page.locator('.board-sapling').count() == 3
    assert page.locator('.board-main-placeholder').count() == 1
    assert page.evaluate('boardScene.targets.every(t=>repoByPath.has(t.path))')
    assert page.evaluate('''()=>{const p=boardScene.plots[0];return pickBoardPlot((p.x-68)*boardCamera.zoom+boardCamera.x,p.y*boardCamera.zoom+boardCamera.y)}''') == WORKTREES[0]
    while page.evaluate('refreshingBoard'):
        for route in list(held):
            held.remove(route)
            path = route.request.url.split('path=', 1)[1]
            path = unquote(path)
            if path == MAIN:
                continue  # The shared scheduler aborted and settled the removed object.
            status = page.evaluate('path=>repoByPath.get(path)._status', path)
            route.fulfill(json=status)
        page.wait_for_timeout(20)
    assert page.locator('.board-sapling').count() == 3


@pytest.mark.parametrize('state,tone', [
    ('conflict', 'blocked'), ('error', 'unavailable'), ('dirty', 'changed'),
    ('sync', 'sync'), ('stale', 'stale'), ('unknown', 'unknown'), ('clean', 'clean'),
])
def test_plot_tone_and_shared_badge_include_hidden_members(page, state, tone):
    project_board(page, 8, projects=26)
    page.evaluate('''({state,path})=>{
      const r=repoByPath.get(path);
      if(state==='conflict')r._status.dirty={is_clean:false,kinds:{conflicted:1}};
      if(state==='error')r._status={error:true};
      if(state==='dirty')r._status.dirty={is_clean:false,modified:2};
      if(state==='sync')r._status.sync={has_upstream:true,ahead:2,behind:0};
      if(state==='stale')r._status.stale_branches=[{name:'old'}];
      if(state==='unknown')r._status={branch:'unknown'};
      renderBoard();
    }''', {'state': state, 'path': WORKTREES[-1]})
    tile = page.locator('.tile[data-path="/projects/oak"]')
    assert tile.get_attribute('data-tone') == tone
    assert tile.locator('.plot-number').get_attribute('data-tone') == tone
    if tone not in ['clean', 'unknown']:
        assert tile.locator('.status-ring').get_attribute('data-tone') == tone
        assert page.locator('#board-isle-0 .isle-dot[data-tone="' + tone + '"]').text_content() == '1'
    assert member(page, WORKTREES[-1]).count() == 0
    assert 'Project state: ' + tone in tile.get_attribute('aria-description')
    if state == 'conflict':
        assert 'local conflict' in tile.get_attribute('aria-description')
    assert member(page, MAIN).get_attribute('data-stage') == 'healthy'


def test_known_severity_beats_unknown_and_conflict_beats_unavailable(page):
    project_board(page, 8)
    page.evaluate("repos[1]._status={error:true};repos[2]._status={};repos[8]._status.dirty={is_clean:false,kinds:{conflicted:1}};renderBoard()")
    assert page.evaluate('boardPlotTone(boardProjects[0])') == 'blocked'
    page.evaluate("repos[8]._status.dirty={is_clean:true};renderBoard()")
    assert page.evaluate('boardPlotTone(boardProjects[0])') == 'unavailable'
    page.evaluate("repos[1]._status={dirty:{is_clean:false,modified:1}};renderBoard()")
    assert page.evaluate('boardPlotTone(boardProjects[0])') == 'changed'


def test_project_and_checkout_counts_have_distinct_units(page):
    project_board(page, 3, projects=26)
    assert page.locator('#board-project-count').inner_text() == '26 projects · 104 checkouts'
    assert page.locator('#count-badge').inner_text() == '104 repos'
    assert page.locator('#board-isle-0 .isle-count').inner_text() == '25'
    page.get_by_role('searchbox', name='Search the island').fill('feature/00')
    assert 'matching projects' in page.locator('#board-match-count').inner_text()
    assert 'matching checkouts' in page.locator('#board-match-count').inner_text()


def test_calm_title_checks_the_whole_workspace_not_only_its_page(page):
    project_board(page, 3, projects=26)
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])')
    page.evaluate("repoByPath.get('/projects/p25-w2')._status.dirty={is_clean:false,kinds:{conflicted:1}};renderBoard()")
    assert not page.evaluate('boardIslandCalm(boardScene.islands[0])')
    assert 'all calm' not in page.locator('#board-terrain').text_content()
    assert page.locator('#board-isle-1 .isle-dot[data-tone="blocked"]').text_content() == '1'
    page.evaluate("repoByPath.get('/projects/p25-w2')._status.dirty={is_clean:true};renderBoard()")
    assert page.locator('.board-bloom').count() == 1
    page.locator('#board-next').click()
    assert page.locator('.board-bloom').count() == 0
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])')


def test_replay_uses_family_max_and_individual_member_glow(page):
    project_board(page, 8)
    before = page.evaluate('boardScene.targets.map(t=>t.path)')
    page.evaluate('''()=>{boardReplay.open=true;boardReplay.data={repos:{
      '/projects/oak-w07':{[replayKey(0)]:5},'/projects/oak-w00':{[replayKey(2)]:2}}};applyReplay()}''')
    assert page.locator('.tile').get_attribute('data-glow') == '1'
    assert member(page, MAIN).get_attribute('data-glow') is None
    assert member(page, WORKTREES[0]).get_attribute('data-glow') == '0.3'
    assert member(page, WORKTREES[0]).locator('.member-replay-pool').evaluate('el=>parseFloat(getComputedStyle(el).opacity)') > 0
    assert page.locator('.plot-more').get_attribute('data-glow') == '1'
    assert page.evaluate('boardScene.targets.map(t=>t.path)') == before
    assert '1 active project · 1 active checkout' in page.locator('#board-replay-day').inner_text()
    page.evaluate('boardReplay.open=false;applyReplay()')
    assert page.locator('.tile[data-glow],.board-member[data-glow],.plot-more[data-glow]').count() == 0


def test_replay_does_not_sum_overlapping_checkout_histories_as_unique_commits(page):
    project_board(page, 8)
    page.evaluate('''()=>{boardReplay.open=true;boardReplay.data={repos:{
      '/projects/oak':{[replayKey(0)]:5},'/projects/oak-w07':{[replayKey(0)]:5}}};applyReplay()}''')
    activity = page.evaluate('replayProjectActivity(boardProjects[0],0)')
    assert activity['maxCheckoutCommits'] == 5
    assert activity['activePaths'] == [MAIN, WORKTREES[-1]]
    label = page.locator('#board-replay-day').inner_text()
    assert '1 active project · 2 active checkouts' in label
    assert 'checkout commit counts:' in label and '10 commits' not in label
    assert page.locator('#board-replay-range').get_attribute('aria-valuetext') == label
    page.evaluate('renderBoard()')
    assert page.locator('.tile').get_attribute('data-glow') == '1'


def test_ground_cache_tracks_saplings_without_repainting_on_recheck(page):
    from test_ground import settled_draws
    project_board(page, 8)
    before = settled_draws(page)
    original = page.evaluate('groundCache.sig')
    records = page.evaluate('groundCache.records')
    assert len(records) == 1 and len(records[0]['members']) == 4
    assert records[0]['clearRx'] > 36 and records[0]['clearRy'] > 17.5
    assert [m['scale'] for m in records[0]['members']] == [1, .55, .55, .55]
    assert page.evaluate('groundCache.shadows') == 4
    page.evaluate('repos[1]._boardQueued=true;renderBoard();repos[1]._boardQueued=false;renderBoard()')
    assert settled_draws(page) == before
    assert page.evaluate('groundCache.sig') == original
    page.evaluate('path=>selectBoardRepo(path)', WORKTREES[-1])
    page.wait_for_function('sig=>groundCache.sig!==sig && groundCache.pendingSig===""', arg=original)
    promoted = page.evaluate('groundCache.sig')
    assert page.evaluate('groundCache.records[0].members[3].path') == WORKTREES[-1]
    page.evaluate("repos[7]._status.dirty={is_clean:false,modified:1};renderBoard()")
    page.wait_for_function('sig=>groundCache.sig!==sig && groundCache.pendingSig===""', arg=promoted)
    assert page.evaluate('groundCache.records[0].disturbed')


def test_untracked_main_casts_only_a_pot_shadow(page):
    from test_ground import settled_draws
    project_board(page)
    page.evaluate('path=>{repos=repos.filter(r=>r.path!==path);rebuildProjectModel();renderBoard()}', MAIN)
    settled_draws(page)
    records = page.evaluate('groundCache.records[0].members')
    assert len(records) == 4
    placeholder = records[0]
    assert placeholder['role'] == 'placeholder' and placeholder['path'] is None
    assert placeholder['potOnly'] and placeholder['canopyHeight'] == 0
    assert all(m['scale'] == .55 for m in records[1:])
    assert page.evaluate('groundCache.shadows') == 4


def test_identity_warning_is_visible_in_inspector_and_plot_description(page):
    project_board(page)
    page.evaluate("repos[1]._status.project_path=repos[1].path;rememberRepoMetadata(repos[1].path,repos[1]._status);renderBoard();selectBoardRepo('/projects/oak')")
    assert 'Conflicting project identity. Refresh local Git.' in page.locator('.tile').get_attribute('aria-description')
    assert page.locator('#board-inspector .identity-warning').inner_text() == 'Conflicting project identity. Refresh local Git.'


@pytest.mark.parametrize('width', [390, 768])
def test_touch_close_zoom_and_paging_controls_are_44px(page, width):
    project_board(page, projects=26)
    page.set_viewport_size({'width': width, 'height': 900})
    page.evaluate('''()=>{boardReplay.open=true;boardReplay.data={repos:{}};syncReplayControls();applyReplay();selectBoardRepo('/projects/oak')}''')
    controls = page.locator('#board-inspector .inspector-close,.board-camera-tools button')
    assert controls.evaluate_all('els=>els.every(el=>el.getClientRects().length>0)')
    assert controls.evaluate_all('els=>els.every(el=>{const r=el.getBoundingClientRect();return r.width>=44 && r.height>=44})')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


def test_label_measurements_and_project_aggregates_are_reused(page):
    project_board(page, 8)
    page.get_by_role('button', name='Names', exact=True).click()
    result = page.evaluate('''()=>{
      const sizes=[...boardLabelMeasurements];
      boardCamera.zoom=1.6;applyBoardCamera();
      const sameSizes=sizes.every(([key,value])=>boardLabelMeasurements.get(key)===value);
      return dashboardUpdate(()=>({sameSizes,sameAggregate:boardProjectAggregate(boardProjects[0])===boardProjectAggregate(boardProjects[0])}));
    }''')
    assert result == {'sameSizes': True, 'sameAggregate': True}


def test_focused_overflow_inspector_row_survives_health_patches(page):
    project_board(page, 8)
    page.evaluate('path=>selectBoardRepo(path)', WORKTREES[-1])
    member(page, MAIN).focus()
    for _ in range(3):
        page.keyboard.press('Alt+ArrowRight')
    assert page.evaluate('document.activeElement.dataset.checkoutPath') == WORKTREES[2]
    assert member(page, WORKTREES[2]).count() == 0
    page.evaluate('''()=>{window.focusedCheckoutRow=document.activeElement;
      repos[3]._status.dirty={is_clean:false,modified:2};renderBoard()}''')
    assert page.evaluate('document.activeElement===focusedCheckoutRow')
    assert 'Local changes' in page.evaluate('focusedCheckoutRow.innerText')
    assert member(page, WORKTREES[-1]).get_attribute('aria-pressed') == 'true'
    page.keyboard.press('Alt+ArrowRight')
    assert page.evaluate('document.activeElement.dataset.checkoutPath') == WORKTREES[3]
    page.keyboard.press('Enter')
    assert member(page, WORKTREES[3]).get_attribute('aria-pressed') == 'true'
    assert page.locator('.board-select[aria-pressed="true"]').count() == 1
    assert page.evaluate('document.activeElement.id') == 'board-inspector-title'
