import pytest

from test_board import PATHS, goto_board, page, status_for
from test_board_finish import family_fixture


@pytest.mark.parametrize('zoom', [.5, 1, 2.5])
def test_foreground_canopy_owns_click_and_hover_over_rear_ground(page, zoom):
    goto_board(page)
    point = page.evaluate('''zoom => {
      boardCamera.zoom=zoom;boardFitPending=false;applyBoardCamera();
      const front=boardScene.plots.find(p=>p.col===1&&p.row===1);
      const stage=document.getElementById('board-stage').getBoundingClientRect();
      const x=front.x*zoom+boardCamera.x,y=(front.y-60)*zoom+boardCamera.y;
      return {x:stage.left+x,y:stage.top+y,picked:pickBoardPlot(x,y)};
    }''', zoom)
    assert point['picked'] == PATHS[4]
    page.mouse.move(point['x'], point['y'])
    page.wait_for_function('boardHoveredPath === repos[4].path')
    assert page.evaluate('''({x,y}) => document.elementFromPoint(x,y).closest('.board-select').dataset.path''', point) == PATHS[4]
    assert 'noupstream' in page.locator('#board-hover-tip').inner_text()
    page.mouse.click(point['x'], point['y'])
    assert page.evaluate('boardSelectedPath') == PATHS[4]
    assert page.locator('#board-inspector h3').inner_text() == 'noupstream'


@pytest.mark.parametrize('zoom', [.5, 1, 2.5])
def test_transparent_sprite_bounds_do_not_steal_rear_ground(page, zoom):
    goto_board(page)
    result = page.evaluate('''zoom => {
      boardCamera={x:-117,y:43,zoom};
      const front=boardScene.plots.find(p=>p.col===1&&p.row===1);
      return pickBoardPlot((front.x+28)*zoom-117,(front.y-65)*zoom+43);
    }''', zoom)
    assert result == PATHS[0]


@pytest.mark.parametrize('coverage,label', [
    ('incomplete', 'GitHub incomplete'),
    ('unchecked', 'GitHub not checked'),
    ('checking', 'GitHub checking'),
])
def test_clean_selected_checkout_cannot_hide_sibling_github_coverage(page, coverage, label):
    family_fixture(page)
    page.evaluate('''coverage => {
      repos[0]._github={has_github:true,repo:'demo/shared',prs:[],issues:[],errors:[]};
      repos[1]._status.github_repo='demo/other';
      delete repos[1]._github;
      if(coverage==='incomplete')repos[1]._github={has_github:false,gh_unavailable:true,prs:[],issues:[],errors:['Unavailable']};
      if(coverage==='checking')githubTasks.set('demo/other',Promise.resolve());
      selectBoardRepo(repos[0].path);
    }''', coverage)
    summary = page.locator('#board-inspector .board-family-gh').inner_text()
    assert label in summary
    assert 'No known PR blockers' not in summary
    badge = page.locator('[data-family-gh] title').text_content()
    assert label in badge
    page.evaluate('githubTasks.clear()')


def test_project_badge_includes_blocker_outside_active_25_checkout_chunk(page):
    goto_board(page)
    page.evaluate('''() => {
      repos=Array.from({length:26},(_,i)=>({path:'/family/r'+i,_status:{project_id:'family',project_path:'/family/r0',is_worktree:i>0,dirty:{is_clean:true},github_repo:'demo/r'+i},
        _github:{has_github:true,repo:'demo/r'+i,prs:i===25?[{number:10,title:'Outside chunk',url:'https://github.com/demo/r25/pull/10',ci:{state:'fail',failing:1}}]:[],issues:[],errors:[]}}));
      boardLayoutReady=false;renderBoard();selectBoardRepo(repos[0].path);
    }''')
    assert page.locator('.board-select').count() == 25
    assert '1 PR with blockers' in page.locator('[data-family-gh] title').text_content()
    assert '1 PR with blockers' in page.locator('#board-inspector .board-family-gh').inner_text()
    page.locator('#board-next').click()
    assert page.locator('.board-select').count() == 1
    assert '1 PR with blockers' in page.locator('[data-family-gh] title').text_content()


def test_held_status_response_does_not_interrupt_active_pan(page):
    goto_board(page)
    held = []
    page.route('**/api/repos/status?*', lambda route: held.append(route))
    page.evaluate('void fetchBoardStatus(0)')
    page.wait_for_function('boardControllers.size === 1')
    page.evaluate('boardCamera.zoom=2.5;boardCamera.x=-60;boardCamera.y=-50;boardFitPending=false;applyBoardCamera();')
    box = page.locator('#board-stage').bounding_box()
    x, y = box['x'] + box['width']/2, box['y'] + box['height']/2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x-20, y-15, steps=3)
    before = page.evaluate('({...boardCamera})')
    assert held
    held.pop().fulfill(json=status_for(PATHS[0]))
    page.wait_for_function('boardControllers.size === 0')
    page.mouse.move(x-60, y-45, steps=3)
    after = page.evaluate('({...boardCamera})')
    page.mouse.up()
    assert after['x'] == before['x'] - 40
    assert after['y'] == before['y'] - 30
    assert page.evaluate('boardSelectedPath') is None
