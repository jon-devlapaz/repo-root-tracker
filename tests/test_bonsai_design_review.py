"""Rendered acceptance checks for the sculptural tree and factual board labels."""
import pytest
from playwright.sync_api import sync_playwright
from bonsai_review import open_scene


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':900},has_touch=True)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        open_scene(page)
        yield page
        assert not errors
        browser.close()


def shape(page):
    return page.evaluate("JSON.stringify(bonsaiLayout(repos[0].path))")


def test_shape_survives_health_github_and_failed_refresh(page):
    before=shape(page)
    page.evaluate("""()=>{const r=repos[0];r._status={...r._status,dirty:{is_clean:false,modified:7},sync:{has_upstream:true,ahead:3,behind:2}};
      acceptGithubSnapshot('review/project-0',1,{has_github:true,repo:'review/project-0',prs:[],issues:[],errors:['Unavailable'],checked_at:new Date().toISOString()});renderBoard();}""")
    assert shape(page)==before
    page.evaluate("repos[0]._status={error:'git unavailable'};renderBoard()")
    assert shape(page)==before


def test_all_styles_have_connected_branches_and_sparse_stays_sparse(page):
    forms=page.evaluate("""()=>BONSAI_STYLES.map((style,n)=>{let i=0;while(bonsaiSeed('/specimen/'+i)%8!==n)i++;
      const L=bonsaiLayout('/specimen/'+i);return {style,pads:L.pads.length,body:L.strokes.map(s=>s.d),
        area:L.pads.reduce((v,p)=>v+p.rx*p.ry,0),
        connected:L.twigs.every((t,i)=>L.strokes.some(s=>s.center.some(c=>Math.hypot(c.x-t.start[0],c.y-t.start[1])<.01)) && Math.hypot(t.end[0]-L.pads[i].x,t.end[1]-L.pads[i].y)<.01),
        low:Math.max(...L.pads.map(p=>p.y))};})""")
    assert len({str(f['body']) for f in forms})==8
    assert all(f['connected'] for f in forms)
    by_style={f['style']:f for f in forms}
    assert by_style['bunjin']['pads']==3
    assert by_style['bunjin']['area']<by_style['chokkan']['area']*.6
    assert by_style['kengai']['low']>-15
    assert all(f['low']<-20 for f in forms if f['style']!='kengai')


def test_names_conditions_and_full_identity_by_keyboard_and_touch(page):
    assert page.evaluate('boardNamesVisible') is False
    page.locator('#board-names-toggle').click()
    labels=page.locator('.plot-name')
    assert labels.count()==4
    main=page.locator('.board-main').filter(has=page.locator('[data-tree-variant]')).nth(2)
    main.focus()
    assert page.locator('#board-hover-tip').is_visible()
    assert 'a-very-long-project-name-with-a-complete-readable-identity' in page.locator('#board-hover-tip').inner_text()
    page.keyboard.press('Enter')
    assert 'a-very-long-project-name-with-a-complete-readable-identity' in page.locator('#board-inspector-title').inner_text()
    assert 'Main clean · 1 worktree changed' in page.locator('.plot-name[data-selected="true"]').inner_text()
    assert 'Project-wide GitHub' in page.locator('#board-inspector').inner_text()
    assert 'GitHub not checked' in page.locator('#board-inspector').inner_text()
    page.locator('#board-names-toggle').click()
    assert page.evaluate('boardNamesVisible') is False
    page.locator('#board-names-toggle').click()
    assert page.evaluate('boardNamesVisible') is True
    # The existing inspector is the full-text touch reveal, including checkout ownership.
    page.locator('#board-inspector-worktrees').tap()
    assert page.get_by_role('dialog').is_visible()


@pytest.mark.parametrize('case',['quiet','crowded','attention'])
@pytest.mark.parametrize('size',[(390,844),(768,900),(1440,900)])
def test_label_rectangles_do_not_overlap_or_escape(page,case,size):
    page.set_viewport_size({'width':size[0],'height':size[1]})
    open_scene(page,case)
    page.locator('#board-names-toggle').click()
    for role in [None, 'main', 'worktree']:
        if role:
            path=page.locator('.board-'+('sapling' if role=='worktree' else 'main')).first.get_attribute('data-path')
            page.evaluate('path=>selectBoardRepo(path)',path)
        result=page.evaluate("""()=>{const stage=document.getElementById('board-stage').getBoundingClientRect();
          const rects=[...document.querySelectorAll('.plot-name,.sapling-name')].map(e=>e.getBoundingClientRect());
          return {count:rects.length,clipped:rects.some(r=>r.left<stage.left || r.right>stage.right || r.top<stage.top || r.bottom>stage.bottom),
          overlap:rects.some((a,i)=>rects.some((b,j)=>j>i && a.left<b.right && a.right>b.left && a.top<b.bottom && a.bottom>b.top))};}""")
        assert result['count']>0
        assert not result['clipped'] and not result['overlap']


def test_refresh_keeps_positions_selection_and_shared_tree(page):
    path=page.locator('.board-sapling').first.get_attribute('data-path')
    page.evaluate('path=>selectBoardRepo(path)',path)
    before=page.evaluate('boardScene.plots.map(p=>[p.projectKey,p.x,p.y])')
    page.get_by_role('button',name='Refresh local Git',exact=True).click()
    page.wait_for_function('!refreshingBoard && repos.every(r=>!r._checking)')
    assert page.evaluate('boardSelectedPath')==path
    assert page.evaluate('boardScene.plots.map(p=>[p.projectKey,p.x,p.y])')==before
    assert page.locator('.bonsai-trunk').count()>0
    page.get_by_role('button',name='List',exact=True).click()
    page.wait_for_selector('#list-view .bonsai-trunk')
    page.evaluate("location.hash='#/repo/'+encodeURIComponent(repos[0].path)")
    page.wait_for_selector('#detail-header .bonsai-trunk')


def test_selected_tree_does_not_keep_hover_tip_over_condition(page):
    tree=page.locator('.board-main [data-tree-variant]').first
    tree.hover()
    page.wait_for_function("!document.getElementById('board-hover-tip').hidden")
    tree.click()
    assert page.locator('#board-hover-tip').is_hidden()
    assert 'Main clean' in page.locator('.plot-name[data-selected="true"]').inner_text()
    tree.hover()
    assert page.locator('#board-hover-tip').is_hidden()


@pytest.mark.parametrize('kind,condition,role',[
    ('standalone','Checkout clean','checkout'),
    ('untracked','Main not tracked','linked worktree'),
    ('unknown','Main not identified','linked worktree'),
    ('unresolved','Main identity unavailable','linked worktree'),
])
def test_condition_preserves_confirmed_and_unknown_checkout_roles(page,kind,condition,role):
    from test_board_projects import seed_projects, MAIN, WORKTREES
    paths=[MAIN] if kind=='standalone' else WORKTREES
    identities={p:({} if kind=='standalone' else
        {'project_path':MAIN,'is_worktree':True} if kind=='unresolved' else
        {'project_id':'/git/common','is_worktree':True} if kind=='unknown' else
        {'project_id':'/git/common','project_path':MAIN,'is_worktree':True}) for p in paths}
    seed_projects(page,paths,identities)
    page.evaluate('path=>selectBoardRepo(path)',paths[0])
    assert page.locator('.plot-name[data-selected="true"] .plot-condition').inner_text()==condition
    assert page.locator('.inspector-local strong').inner_text()=='Local Git · '+role
