"""P1.3: draw and pick the production checkout sprites, not copied geometry."""
from urllib.parse import quote, unquote

import pytest

from test_board import page  # noqa: F401

MAIN = '/projects/oak'
WORKTREES = [f'/projects/oak-w{i:02d}' for i in range(8)]


def project_board(page, count=3, foreground=False, projects=1, counts=None):
    if counts is not None:
        count, projects = counts[0], len(counts)
    paths = (["/projects/rear"] if foreground else []) + [MAIN, *WORKTREES[:count]]
    for i in range(1, projects):
        worktree_count = counts[i] if counts is not None else count
        paths.extend([f'/projects/p{i:02d}', *[f'/projects/p{i:02d}-w{j}' for j in range(worktree_count)]])
    statuses = {}
    for path in paths:
        main = MAIN if path == MAIN or path in WORKTREES else path.split('-w', 1)[0]
        statuses[path] = {
            'project_id': main + '/.git', 'project_path': main, 'is_worktree': path != main,
            'branch': 'main' if path == main else 'feature/' + path.rsplit('-w', 1)[-1],
            'dirty': {'is_clean': True}, 'sync': {'has_upstream': True, 'ahead': 0, 'behind': 0},
            'stale_branches': [], 'branches': ['main'], 'github_repo': None,
            'last_commit': {'date': '2026-10-01T00:00:00Z'},
        }
    page.route('**/api/repos', lambda route: route.fulfill(json=[{'path': p} for p in paths]))
    page.route('**/api/repos/status?*', lambda route: route.fulfill(json=statuses[unquote(route.request.url.split('path=', 1)[1])]))
    page.evaluate('''statuses => {
      repos=Object.entries(statuses).map(([path,_status])=>({path,_status}));
      repoIdentities.clear();metadataObservedPaths.clear();rebuildProjectModel();
      for(const r of repos)rememberRepoMetadata(r.path,r._status);
      rebuildProjectModel();render();location.hash='#/board';
    }''', statuses)
    page.wait_for_function('boardLayoutReady && !refreshingBoard && repos.every(r=>!r._checking) && boardScene?.targets.length>0')
    return paths


def member(page, path):
    return page.locator('[id="board-tile-' + quote(path, safe='') + '"]')


def set_camera(page, zoom, path=MAIN):
    """Use the app's clamped, rounded camera, including pan where zoom permits it."""
    page.evaluate('''async ({zoom,path}) => {
      const stage=document.getElementById('board-stage'),target=boardScene.targets.find(t=>t.path===path);
      boardCamera={zoom,x:stage.clientWidth/2-target.x*zoom-17,y:stage.clientHeight/2-target.y*zoom+13};
      boardFitPending=false;
      applyBoardCamera();
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    }''', {'zoom': zoom, 'path': path})


def geometry(page, path=WORKTREES[0]):
    # Shape only: a clean checkout is gold by design, so colour is not part of the geometry contract.
    return member(page, path).locator('[data-tree-variant]').evaluate("el=>({transform:el.getAttribute('transform'),html:el.innerHTML.replace(/(fill|stroke)=\"#[0-9a-fA-F]{3,8}\"/g,''),box:JSON.stringify(el.getBBox())})")


def test_three_saplings_fit_the_pinned_sprite_box(page):
    project_board(page)
    result = page.locator('.tile').evaluate('''tile => ({
      box:[tile.offsetWidth,tile.offsetHeight],
      siblings:[...tile.children].every(el=>el.matches('button.board-member')),
      roles:[...tile.children].map(el=>el.dataset.role),
      offsets:[...tile.children].map(el=>[el.offsetLeft,el.offsetTop]),
      bodies:[...tile.querySelectorAll('.member-body')].map(el=>({matrix:el.transform.baseVal.consolidate().matrix.a,box:el.getBBox(),variant:el.dataset.treeVariant})),
      saplings:[...tile.querySelectorAll('.board-sapling > svg:not(.board-shared-marks)')].map(svg=>{
        const el=svg.querySelector('.member-body'),box=el.getBBox(),m=el.transform.baseVal.consolidate().matrix;
        return {x:box.x*m.a+m.e,y:box.y*m.d+m.f,right:(box.x+box.width)*m.a+m.e,bottom:(box.y+box.height)*m.d+m.f,
          anchor:[m.e,m.f],potScale:m.a,ink:!!el.querySelector('[filter="url(#ink-edge)"]')};
      })})''')
    assert result['box'] == [128, 148]
    assert result['siblings'] and result['roles'] == ['main', 'worktree', 'worktree', 'worktree']
    assert result['offsets'] == [[0, 0]] * 4
    assert [s['anchor'] for s in result['saplings']] == [[20, 94], [108, 94], [64, 122]]
    assert all(0 <= s['x'] < s['right'] <= 128 and 0 <= s['y'] < s['bottom'] <= 148 for s in result['saplings'])
    assert all(s['potScale'] < .55 and not s['ink'] for s in result['saplings'])
    assert page.evaluate('BOARD_ART_DIRECTION.tile') == [156, 78]
    assert member(page, MAIN).locator('.tile-top').get_attribute('points') == '64,47 142,86 64,125 -14,86'


def test_overflow_indicator_counts_only_unrendered_worktrees(page):
    project_board(page, 8)
    assert page.locator('.tile').count() == 1
    assert page.locator('.board-sapling').count() == 3
    assert page.locator('.plot-more').text_content() == '+5'
    before = page.evaluate('boardScene.plots.map(p=>[p.x,p.y,p.number])')
    page.evaluate('path=>selectBoardRepo(path)', WORKTREES[-1])
    assert member(page, WORKTREES[-1]).get_attribute('data-slot') == 'front'
    assert page.locator('.plot-more').text_content() == '+5'
    assert page.evaluate('boardScene.plots.map(p=>[p.x,p.y,p.number])') == before
    assert page.locator('.board-select[aria-pressed="true"]').count() == 1
    assert member(page, MAIN).locator('.plot-flag').count() == 0
    assert member(page, WORKTREES[-1]).locator('.plot-flag').count() == 1


def test_each_sapling_has_its_own_local_weather(page):
    project_board(page)
    page.evaluate('''() => {
      repos[1]._status.dirty={is_clean:false,modified:2};
      repos[2]._status.sync={has_upstream:true,ahead:2,behind:1};
      repos[3]._status.stale_branches=[{name:'old'}];renderBoard();
    }''')
    assert member(page, MAIN).locator('[data-marker="local-work"], [data-marker="sync"], [data-marker="stale"]').count() == 0
    for path, marker in zip(WORKTREES, ['local-work', 'sync', 'stale']):
        assert member(page, path).locator(f'[data-marker="{marker}"]').count() == 1
        assert member(page, path).locator('.tree-fx').first.locator('xpath=..').get_attribute('transform').endswith('scale(0.55)')
    page.evaluate("repos[1]._status.dirty={is_clean:false,kinds:{conflicted:1}};repos[2]._status={error:true};repos[3]._status={error:true,gone:true};renderBoard();")
    assert member(page, WORKTREES[0]).locator('[data-marker="local-conflict"]').count() == 1
    assert member(page, WORKTREES[1]).locator('.is-faded .tree-bounds').count() == 1
    assert member(page, WORKTREES[2]).locator('[data-tree-variant]').count() == 0
    assert member(page, WORKTREES[2]).locator('.member-body .tree-hit').count() == 1


def test_sapling_geometry_is_stable_when_bounded_vitals_are_fixed(page):
    project_board(page)
    page.evaluate("repos[1]._status.activity_30d=12;repos[1]._status.first_commit_date='2020-01-01';repos[1]._status.branches=['main','feature/00','live'];renderBoard();")
    before = geometry(page)
    page.evaluate('''() => {
      const r=repos[1];r._status.dirty={is_clean:false,modified:5};r._status.sync.ahead=3;
      r._status.stale_branches=[{name:'not-live'}];r._status.github_repo='demo/oak';rememberRepoMetadata(r.path,r._status);acceptGithubSnapshot('demo/oak',1,{has_github:true,prs:[{number:1,ci:{state:'fail',failing:1}}],issues:[]});
      selectBoardRepo(r.path);renderBoard();
    }''')
    assert geometry(page) == before
    page.evaluate('boardReplay.open=true;boardReplay.data={repos:{}};applyReplay()')
    assert geometry(page) == before


def test_live_branch_vitals_can_change_sapling_geometry(page):
    project_board(page)
    page.evaluate("repos[1]._status.branches=['feature/00','live'];renderBoard()")
    before = geometry(page)
    assert page.evaluate('bonsaiVitalsOf(repos[1].path).br') == 1
    page.evaluate("repos[1]._status.stale_branches=[{name:'live'}];renderBoard()")
    assert page.evaluate('bonsaiVitalsOf(repos[1].path).br') == 0
    assert geometry(page) != before


def test_error_retains_last_successful_normalized_vitals(page):
    project_board(page)
    page.route('**/api/repos/status?*', lambda route: route.fulfill(json={'dirty': {'is_clean': True}, 'activity_30d': 17, 'first_commit_date': '2020-01-01', 'branches': ['main', 'live'], 'branch': 'main'}))
    page.evaluate('async()=>{await fetchBoardStatus(1);renderBoard()}')
    before, normalized = geometry(page), page.evaluate('repos[1]._bonsaiVitals.normalized')
    page.route('**/api/repos/status?*', lambda route: route.fulfill(status=503, json={'error': 'git failed'}))
    page.evaluate('async()=>{await fetchBoardStatus(1);renderBoard()}')
    assert geometry(page) == before
    assert page.evaluate('repos[1]._bonsaiVitals.normalized') == normalized
    assert 'Branch not checked' in member(page, WORKTREES[0]).get_attribute('aria-label')
    assert page.evaluate('!repos[1]._status.branch')
    page.evaluate('repos[1]._boardQueued=true;renderBoard()')
    assert geometry(page) == before
    page.evaluate('repos[1]._boardQueued=false;repos[1]._status={gone:true,error:true};renderBoard()')
    assert member(page, WORKTREES[0]).locator('[data-tree-variant]').count() == 0
    assert page.evaluate('bonsaiVitalsOf(repos[1].path)') == normalized
    page.route('**/api/repos/status?*', lambda route: route.fulfill(json={'dirty': {'is_clean': True}}))
    page.evaluate('async()=>{await fetchBoardStatus(1);renderBoard()}')
    assert page.evaluate('bonsaiVitalsOf(repos[1].path).key') == '1,1,0'
    assert geometry(page) != before


@pytest.mark.parametrize('zoom', [.5, 1, 2.5])
def test_main_sapling_and_diamond_pick_distinct_repo_paths(page, zoom):
    project_board(page)
    set_camera(page, zoom)
    samples = page.evaluate('boardScene.targets.map(t=>({path:t.path,diamond:false})).concat({path:boardScene.plots[0].path,diamond:true})')
    for sample in samples:
        # Selection may reveal an anchor; compute each point from the current
        # camera instead of reusing screen coordinates from before that reveal.
        point = page.evaluate('''({path,diamond}) => {
          const stage=document.getElementById('board-stage').getBoundingClientRect();
          const t=boardScene.targets.find(t=>t.path===path),p=boardScene.plots.find(p=>p.path===path);
          const world=diamond?{x:p.x-68,y:p.y}:{x:t.x,y:t.y-52*t.scale*bonsaiLayout(t.path).scale};
          const x=Math.round(world.x*boardCamera.zoom+boardCamera.x+stage.left),y=Math.round(world.y*boardCamera.zoom+boardCamera.y+stage.top);
          return {expected:path,picked:pickBoardPlot(x-stage.left,y-stage.top),
            native:document.elementFromPoint(x,y)?.closest('.board-select')?.dataset.path,x,y};
        }''', sample)
        assert point['picked'] == point['expected'] == point['native']
        page.mouse.move(point['x'], point['y'])
        page.wait_for_function('path=>boardHoveredPath===path', arg=point['expected'])
        page.mouse.click(point['x'], point['y'])
        assert page.evaluate('boardSelectedPath') == point['expected']
    assert page.evaluate('pickBoardPlot(-1000,-1000)') is None


def foreground_sample(page, painted):
    return page.evaluate('''painted => {
      const plot=boardScene.plots.find(p=>p.project.paths.includes('/projects/oak'));
      const target=plot.targets.find(t=>t.slot==='left'),rear=boardScene.plots.find(p=>p.path==='/projects/rear');
      const stage=document.getElementById('board-stage').getBoundingClientRect();
      const screen=(x,y)=>({x:x*boardCamera.zoom+boardCamera.x+stage.left,y:y*boardCamera.zoom+boardCamera.y+stage.top});
      const min=screen(target.x-18,target.y-36),max=screen(target.x+18,target.y+5);
      const expected=painted?target.path:rear.path;
      const owns=(x,y)=>document.elementFromPoint(x,y)?.closest('.board-select')?.dataset.path===expected&&pickBoardPlot(x-stage.left,y-stage.top)===expected;
      let best=null,score=-1;
      // Use whole screen pixels shared by the sampled native hit and mouse
      // events, and prefer the interior rather than the first shape edge.
      for(let x=Math.ceil(min.x);x<=Math.floor(max.x);x++)for(let y=Math.ceil(min.y);y<=Math.floor(max.y);y++){
        const world=boardScreenToWorld(x-stage.left,y-stage.top);
        if(Math.abs(world.x-rear.x)/78+Math.abs(world.y-rear.y)/39>.98)continue;
        if(boardSpriteContains(target,world)!==painted)continue;
        if(!owns(x,y))continue;
        let clearance=0;
        for(const radius of [.25,.5,1,1.5,2,3]){
          if(![[radius,0],[-radius,0],[0,radius],[0,-radius]].every(([dx,dy])=>owns(x+dx,y+dy)))break;
          clearance=radius;
        }
        if(clearance>score){score=clearance;best={x,y,expected,picked:pickBoardPlot(x-stage.left,y-stage.top),
          native:document.elementFromPoint(x,y)?.closest('.board-select')?.dataset.path};}
      }
      return best;
    }''', painted)


@pytest.mark.parametrize('zoom', [.5, 1, 2.5])
def test_front_sapling_owns_visible_overlap_with_rear_plot(page, zoom):
    project_board(page, foreground=True)
    set_camera(page, zoom)
    point = foreground_sample(page, True)
    assert point is not None, 'A foreground sapling must own its painted overlap with rear ground'
    assert point['picked'] == point['native'] == point['expected'] == WORKTREES[0]
    page.mouse.move(point['x'], point['y'])
    page.wait_for_function('path=>boardHoveredPath===path', arg=point['expected'])
    page.mouse.click(point['x'], point['y'])
    assert page.evaluate('boardSelectedPath') == point['expected']


@pytest.mark.parametrize('zoom', [.5, 1, 2.5])
def test_sapling_bounds_weather_and_shadow_do_not_steal_rear_ground(page, zoom):
    project_board(page, foreground=True)
    page.evaluate("repos.find(r=>r.path===boardProjects[1].worktreePaths[0])._status.dirty={is_clean:false,modified:10};renderBoard()")
    set_camera(page, zoom)
    assert page.evaluate("[...boardHitCache.values()].every(hit=>hit.shapes.every(({shape})=>!shape.closest('.tree-fx,.tree-shadow,.plot-marks')&&!shape.matches('.tree-bounds,.plot-outline,.member-focus')))")
    for selector in ['.tree-bounds', '.tree-fx path', '.tree-shadow']:
        assert member(page, WORKTREES[0]).locator(selector).first.evaluate("el=>getComputedStyle(el).pointerEvents") == 'none'
    point = foreground_sample(page, False)
    assert point is not None
    assert point['picked'] == point['native'] == point['expected'] == '/projects/rear'
    page.mouse.move(point['x'], point['y'])
    page.wait_for_function('boardHoveredPath==="/projects/rear"')
    page.mouse.click(point['x'], point['y'])
    assert page.evaluate('boardSelectedPath') == '/projects/rear'


@pytest.mark.parametrize('zoom', [.5, 1, 2.5])
def test_all_seeded_tree_styles_have_stable_click_centers(page, zoom):
    project_board(page, 8)
    page.evaluate('''() => {
      const styles=new Set(),paths=[];
      for(let i=0;styles.size<8;i++){const path='/styles/w'+i,style=bonsaiSeed(path)%8;if(!styles.has(style)){styles.add(style);paths.push(path);}}
      repos=paths.map(path=>({path,_status:{project_id:'/styles/.git',project_path:'/styles/main',is_worktree:true,branch:'work',dirty:{is_clean:true},github_repo:null}}));
      repoIdentities.clear();metadataObservedPaths.clear();rebuildProjectModel();repos.forEach(r=>rememberRepoMetadata(r.path,r._status));renderBoard();
    }''')
    paths = page.evaluate('boardProjects[0].worktreePaths')
    seen = set()
    for path in paths:
        page.evaluate('path=>selectBoardRepo(path)', path)
        set_camera(page, zoom, path)
        target = member(page, path).locator('[data-tree-variant]')
        seen.add(target.get_attribute('data-tree-variant'))
        before = target.bounding_box()
        page.evaluate('''path=>{const r=repoByPath.get(path);r._status.dirty={is_clean:false,modified:2};renderBoard()}''', path)
        # Camera and the generator bounds remain fixed under a weather-only patch.
        assert target.bounding_box() == before
        page.evaluate('path=>{repoByPath.get(path)._status={error:true};renderBoard()}', path)
        assert target.bounding_box() == before
        page.evaluate('clearBoardSelection()')
        assert page.evaluate('boardSelectedPath') is None
        assert target.bounding_box() == before
        point = target.bounding_box()
        x,y = round(point['x']+point['width']/2),round(point['y']+point['height']/2)
        picked = page.evaluate('''({x,y})=>{const s=document.getElementById('board-stage').getBoundingClientRect();return pickBoardPlot(x-s.left,y-s.top)}''', {'x':x,'y':y})
        assert picked == path
        assert page.evaluate('''({x,y})=>document.elementFromPoint(x,y)?.closest('.board-select')?.dataset.path''', {'x':x,'y':y}) == path
        page.mouse.move(x, y)
        page.wait_for_function('path=>boardHoveredPath===path', arg=path)
        page.mouse.click(x, y)
        assert page.evaluate('boardSelectedPath') == path
    assert len(seen) == 8
