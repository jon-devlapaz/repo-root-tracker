"""P1.1/P1.2: exercise the shared production model, scheduler, and scene.

Sapling SVGs and member interaction are the P1.3/P1.4 handoff. These tests
assert the target records now, without pretending those sprites are drawn.
"""
from urllib.parse import quote, unquote

import pytest

from test_board import PATHS, goto_board, page, status_for  # noqa: F401

IDENTITY_KEY = 'repo-root-tracker.project-identities.v1'
MAIN = '/projects/oak'
WORKTREES = ['/projects/oak-a', '/projects/oak-b', '/projects/oak-c']


def seed_projects(page, paths=None, identities=None):
    paths = paths or [MAIN, *WORKTREES]
    identities = identities or {
        path: {'project_id': MAIN + '/.git', 'project_path': MAIN, 'is_worktree': path != MAIN}
        for path in paths
    }
    page.evaluate('''({paths,identities}) => {
      repos=paths.map(path=>({path,_status:{dirty:{is_clean:true},branch:'main'}}));
      repoIdentities.clear(); metadataObservedPaths.clear(); rebuildProjectModel();
      for(const repo of repos) rememberRepoMetadata(repo.path,{...repo._status,...identities[repo.path]});
      render();
    }''', {'paths': paths, 'identities': identities})


def project_state(page):
    return page.evaluate('boardProjects')


def test_project_id_creates_one_plot_for_main_and_worktrees(page):
    seed_projects(page)
    goto_board(page)
    assert page.locator('.tile').count() == 1
    result = page.evaluate('''() => ({project:boardProjects[0],plots:boardScene.plots.length,
      targets:boardScene.targets,mapped:repos.every(r=>projectForPath(r.path)===boardProjects[0]),
      indexed:repoByPath.size===4 && boardProjectByKey.size===1 && boardProjectByPath.size===4})''')
    assert result['plots'] == 1 and result['mapped'] and result['indexed']
    assert result['project']['paths'] == [MAIN, *WORKTREES]
    assert [target['slot'] for target in result['targets']] == ['main', 'left', 'right', 'front']
    assert [target['scale'] for target in result['targets']] == [1, .4, .4, .4]


def test_missing_and_error_status_keep_last_known_family_identity(page):
    seed_projects(page)
    page.evaluate('repos[0]._status=null; repos[1]._status={error:true}; repos[2]._status={error:true,gone:true}; rebuildProjectModel();')
    project = project_state(page)[0]
    assert len(project_state(page)) == 1 and project['paths'] == [MAIN, *WORKTREES]
    assert project['mainRepoPath'] == MAIN
    page.evaluate("rememberRepoMetadata(repos[0].path,{dirty:{is_clean:true}})")
    assert project_state(page)[0]['key'] == 'git:' + MAIN + '/.git'


def test_cached_identity_restores_family_without_restoring_health(page):
    seed_projects(page)
    page.route('**/api/repos', lambda route: route.fulfill(json=[{'path': MAIN}, {'path': WORKTREES[0]}]))
    page.route('**/api/repos/status?*', lambda route: route.fulfill(status=503, json={'error': 'unavailable'}))
    page.reload()
    page.wait_for_function('repos.length===2 && repos.every(r=>r._status?.error && !r._checking)')
    assert len(project_state(page)) == 1
    assert page.evaluate('repos.every(r=>!r._status.branch && !r._status.dirty && !r._status.activity_30d && !r._github)')
    cache = page.evaluate('JSON.parse(localStorage.getItem(PROJECT_IDENTITIES_KEY))')
    assert cache['version'] == 1
    assert set(cache['entries'][MAIN]) == {'project_id', 'project_path', 'is_worktree'}


def test_identity_cache_ignores_invalid_entries_and_storage_failure_keeps_memory(page):
    page.evaluate('''key => localStorage.setItem(key,JSON.stringify({version:1,entries:{
      '/bad':{project_id:12},'/blank':{project_id:' '},'/wrong':{is_worktree:'true'},
      '/good':{project_id:'/git/good',project_path:'/good',is_worktree:false,branch:'never restore'}
    }}))''', IDENTITY_KEY)
    page.reload()
    page.wait_for_function('repos.every(r=>r._status)')
    assert page.evaluate("[...repoIdentities.keys()]") == ['/good']
    page.evaluate("Storage.prototype.setItem=()=>{throw Error('blocked')}; rememberRepoMetadata(repos[0].path,{project_id:'/git/memory',is_worktree:false});")
    assert page.evaluate('projectForPath(repos[0].path).projectId') == '/git/memory'


def test_untracked_main_is_an_unselectable_empty_pot(page):
    seed_projects(page, WORKTREES)
    goto_board(page)
    assert page.evaluate('boardProjects[0].mainRepoPath') is None
    assert page.evaluate('boardProjects[0].centralRepoPath') is None
    assert page.evaluate('boardScene.targets.every(t=>t.role==="worktree" && t.scale===.4)')
    assert page.locator('.board-main-placeholder').get_attribute('aria-label') == 'Main checkout not tracked.'
    assert page.locator('.board-main-placeholder .tree-hit').count() == 0
    assert page.evaluate(f'boardScene.targets.some(t=>t.path==={MAIN!r})') is False
    picked = page.evaluate('''() => { const p=boardScene.plots[0];return pickBoardPlot(p.x*boardCamera.zoom+boardCamera.x,p.y*boardCamera.zoom+boardCamera.y); }''')
    assert picked == WORKTREES[0]


def test_worktree_only_family_never_promotes_a_full_bonsai(page):
    identities = {path: {'project_id': '/git/common', 'is_worktree': True} for path in WORKTREES}
    seed_projects(page, WORKTREES, identities)
    goto_board(page)
    assert page.evaluate('boardScene.targets.every(t=>t.role==="worktree" && t.slot!=="main" && t.scale===.4)')
    assert page.locator('.board-main-placeholder').get_attribute('aria-label') == 'Main checkout not identified.'
    assert page.locator('[data-tree-variant]').count() == 0


def test_legacy_singleton_renders_centrally_without_claiming_main(page):
    seed_projects(page, [MAIN], {MAIN: {}})
    goto_board(page)
    project = project_state(page)[0]
    assert project['identityState'] == 'standalone'
    assert project['centralRepoPath'] == MAIN and project['mainRepoPath'] is None
    assert not project['mainRoleConfirmed']
    assert page.locator('.board-main-placeholder').count() == 0
    assert page.locator('[data-tree-variant]').count() == 1
    assert page.evaluate('boardScene.targets[0].role') == 'standalone'
    assert page.locator('#board-tile-' + quote(MAIN, safe='')).count() == 1


def test_known_worktree_without_family_id_stays_a_separate_sapling_project(page):
    identities = {path: {'project_path': MAIN, 'is_worktree': True} for path in WORKTREES}
    seed_projects(page, WORKTREES, identities)
    goto_board(page)
    assert len(project_state(page)) == 3
    assert all(project['identityState'] == 'worktree-unresolved' and project['centralRepoPath'] is None for project in project_state(page))
    assert page.evaluate('boardScene.targets.every(t=>t.role==="worktree" && t.scale===.4)')
    assert page.locator('.board-main-placeholder').count() == 3


def test_repos_without_project_id_remain_separate_path_projects(page):
    seed_projects(page, WORKTREES, {path: {'project_path': MAIN, 'github_repo': 'same/remote'} for path in WORKTREES})
    assert [project['key'] for project in project_state(page)] == ['path:' + path for path in WORKTREES]


def test_exact_main_claim_attaches_unchecked_main_but_never_other_established_id(page):
    seed_projects(page, [MAIN, WORKTREES[0]], {MAIN: {}, WORKTREES[0]: {'project_id': '/git/oak', 'project_path': MAIN, 'is_worktree': True}})
    assert len(project_state(page)) == 1
    assert project_state(page)[0]['mainRepoPath'] == MAIN
    page.evaluate("rememberRepoMetadata(repos[0].path,{project_id:'/git/other',is_worktree:false});")
    assert len(project_state(page)) == 2
    assert project_state(page)[1]['mainRepoPath'] is None
    assert 'Refresh local Git' in project_state(page)[1]['identityWarning']


def test_project_order_and_numbers_ignore_health_branch_and_list_sort(page):
    paths = [WORKTREES[1], '/independent', MAIN, WORKTREES[0]]
    identities = {path: {'project_id': MAIN + '/.git', 'project_path': MAIN, 'is_worktree': path != MAIN} for path in paths if path != '/independent'}
    seed_projects(page, paths, identities)
    before = page.evaluate('boardProjects.map(p=>[p.key,p.paths,p.number,p.order])')
    page.evaluate("repos.forEach(r=>{r._status.branch='changed';r._status.dirty={is_clean:false}}); organization.sort='recent'; organization.grouping='none'; rebuildProjectModel(); render();")
    assert page.evaluate('boardProjects.map(p=>[p.key,p.paths,p.number,p.order])') == before
    assert before[0][1] == [MAIN, WORKTREES[0], WORKTREES[1]]
    assert [record[2] for record in before] == [1, 2]


@pytest.mark.parametrize('grouping', ['collection', 'folder', 'project', 'none'])
def test_list_first_shared_model_survives_errors_in_every_grouping_mode(page, grouping):
    seed_projects(page)
    page.route('**/api/repos', lambda route: route.fulfill(json=[{'path': path} for path in [MAIN, *WORKTREES]]))
    page.route('**/api/repos/status?*', lambda route: route.fulfill(status=503, json={'error': 'unavailable'}))
    page.reload()
    page.wait_for_function('repos.length===4 && repos.every(r=>r._status?.error && !r._checking)')
    page.evaluate('''grouping => {
      organization.grouping=grouping; organization.pins=[repos[1].path]; render();
    }''', grouping)
    assert page.evaluate('boardScene') is None
    assert page.evaluate('boardProjectByPath.size') == 4
    assert len(project_state(page)) == 1
    assert page.locator('.repo-card').count() == 4
    assert page.locator('#pin-' + quote(WORKTREES[0], safe='')).get_attribute('aria-pressed') == 'true'
    if grouping != 'project':
        assert page.locator('.project-family .repo-card').count() == 3
    else:
        assert page.locator('.collection-toggle').all_text_contents()[1].startswith('oak')


def test_direct_cold_board_load_times_out_held_initial_request_and_consolidates_siblings(page):
    held, calls, concurrency = [], [], []
    page.evaluate('localStorage.removeItem(PROJECT_IDENTITIES_KEY)')
    page.route('**/api/repos', lambda route: route.fulfill(json=[{'path': path} for path in [MAIN, *WORKTREES]]))

    def status(route):
        path = unquote(route.request.url.split('path=', 1)[1])
        calls.append(path)
        concurrency.append(page.evaluate('localStatusInFlight'))
        if path == MAIN:
            held.append(route)  # Never released: only the real production deadline settles it.
        else:
            route.fulfill(json={**status_for(path), 'project_id': MAIN + '/.git', 'project_path': MAIN, 'is_worktree': True})

    page.route('**/api/repos/status?*', status)
    page.clock.install()
    page.goto('http://dashboard.test/#/board')
    page.wait_for_function('repos.length===4 && boardScene?.plots.length===4')
    assert page.locator('.tile').count() == 4
    page.wait_for_function('repos.slice(1).every(r=>r._status && !r._checking)')
    assert len(project_state(page)) == 1  # Model changes immediately, scene waits.
    assert not page.evaluate('boardLayoutReady')
    page.evaluate('window.coldJoinSettled=false;fetchBoardAll(false).then(()=>{coldJoinSettled=true});')
    assert page.evaluate('coldJoinSettled') is False
    assert len(calls) == 4 and len(held) == 1
    assert max(concurrency) == 3
    assert page.evaluate('localStatusInFlight') == 1
    page.clock.fast_forward(10_001)
    page.wait_for_function('boardLayoutReady && boardScene.plots.length===1')
    assert page.evaluate('repos[0]._status.error && repos.every(r=>!r._checking) && boardControllers.size===0')
    assert page.locator('#board-refresh').is_enabled()
    assert page.locator('#board-github-refresh').is_enabled()
    assert page.evaluate('coldJoinSettled')
    assert len(calls) == 4  # No duplicate Board pass.


def test_list_and_board_requests_share_deadline_counter_and_concurrency(page):
    page.clock.install()
    page.evaluate('''() => {
      window.originalFetch=fetch; window.localCalls=[];
      window.fetch=()=>new Promise(resolve=>localCalls.push(resolve));
      window.jobs=[fetchStatus(0),fetchBoardStatus(1),fetchStatus(2),fetchBoardStatus(3),fetchStatus(4)];
    }''')
    assert page.evaluate('localCalls.length') == 3
    assert page.evaluate('localStatusInFlight') == 3
    assert page.evaluate('boardControllers.size') == 3
    page.clock.fast_forward(10_001)
    page.wait_for_function('localCalls.length===5')
    assert page.evaluate('localStatusInFlight') == 2
    page.clock.fast_forward(10_001)
    page.evaluate('''async () => { await Promise.all(jobs);window.fetch=originalFetch; }''')
    assert page.evaluate('repos.every(r=>r._status.error && !r._checking) && boardControllers.size===0')
    # The counter is shared even when callers supersede one another.
    result = page.evaluate('''async () => {
      window.fetch=()=>new Promise(resolve=>localCalls.push(resolve));
      const start=localCalls.length, previous=repos[0]._statusRequest;
      const first=fetchStatus(0), second=fetchBoardStatus(0);
      localCalls[start+1]({ok:true,status:200,json:async()=>({branch:'new',dirty:{is_clean:true}})});
      await second; await first; window.fetch=originalFetch;
      return {counter:repos[0]._statusRequest-previous,branch:repos[0]._status.branch,checking:repos[0]._checking};
    }''')
    assert result == {'counter': 2, 'branch': 'new', 'checking': False}


def test_late_status_response_cannot_update_identity_vitals_or_newer_status(page):
    page.clock.install()
    page.evaluate('''() => {
      window.originalFetch=fetch;window.localCalls=[];
      window.fetch=()=>new Promise(resolve=>localCalls.push(resolve));
      window.expiring=fetchStatus(0);
      localCalls[0]({ok:true,status:200,json:()=>new Promise(resolve=>window.lateBody=resolve)});
    }''')
    page.wait_for_function('typeof lateBody==="function"')
    page.clock.fast_forward(10_001)
    page.evaluate('''async () => {
      await expiring;
      const newer=fetchBoardStatus(0);
      localCalls[1]({ok:true,status:200,json:async()=>({project_id:'/git/new',branch:'new',first_commit_date:'2026-09-01',activity_30d:2,dirty:{is_clean:true}})});
      await newer;
      lateBody({project_id:'/git/old',branch:'old',first_commit_date:'2000-01-01',activity_30d:999,github_repo:'old/remote'});
      await new Promise(resolve=>queueMicrotask(resolve));await new Promise(resolve=>queueMicrotask(resolve));
      window.fetch=originalFetch;
    }''')
    assert page.evaluate('projectForPath(repos[0].path).projectId') == '/git/new'
    assert page.evaluate('repos[0]._status.branch') == 'new'
    assert page.evaluate('repos[0]._status.activity_30d') == 2
    assert page.evaluate('bonsaiVitalsOf(repos[0].path).density') == 1
    assert page.evaluate('githubIdentityByPath.has(repos[0].path)') is False


def test_removed_request_cannot_mutate_replacement_object_with_same_path(page):
    result = page.evaluate('''async () => {
      const original=fetch;let resolveOld;
      window.fetch=()=>new Promise(resolve=>resolveOld=resolve);
      const old=fetchStatus(0),path=repos[0].path;
      repos[0]={path,_status:{branch:'replacement',dirty:{is_clean:true}}};rebuildProjectModel();
      resolveOld({ok:true,status:200,json:async()=>({branch:'old',project_id:'/git/old'})});
      await old; window.fetch=original;
      return {branch:repos[0]._status.branch,id:projectForPath(path).projectId,controllers:boardControllers.size};
    }''')
    assert result == {'branch': 'replacement', 'id': None, 'controllers': 0}


def test_initial_metadata_commits_once_and_preserves_selected_path(page):
    goto_board(page)
    page.evaluate('''() => {
      selectBoardRepo(repos[1].path);
      window.beforeScene=boardSceneSignature;window.originalFetch=fetch;window.localCalls=[];
      window.membershipCommits=0; window.originalCommit=commitBoardMembership;
      commitBoardMembership=()=>{const changed=originalCommit();if(changed)membershipCommits++;return changed;};
      window.fetch=()=>new Promise(resolve=>localCalls.push(resolve));
      window.refreshBatch=runLocalStatusBatch([...repos], 'board', true);
    }''')
    page.evaluate('''async () => {
      localCalls[0]({ok:true,status:200,json:async()=>({project_id:'/git/shared',project_path:repos[0].path,is_worktree:false,dirty:{is_clean:true}})});
      localCalls[1]({ok:true,status:200,json:async()=>({project_id:'/git/shared',project_path:repos[0].path,is_worktree:true,dirty:{is_clean:true}})});
    }''')
    page.wait_for_function('boardProjects.length===4 && localCalls.length===5')
    assert page.evaluate('boardSceneSignature===beforeScene')
    page.evaluate('''async () => {
      for(let i=2;i<5;i++)localCalls[i]({ok:true,status:200,json:async()=>({dirty:{is_clean:true}})});
      await refreshBatch; window.fetch=originalFetch;
    }''')
    assert page.evaluate('boardSelectedPath') == PATHS[1]
    assert page.evaluate('boardScene.plots.length') == 4
    assert page.evaluate('membershipCommits') == 1
    signature = page.evaluate('boardSceneSignature')
    page.evaluate('renderBoard()')
    assert page.evaluate('boardSceneSignature') == signature


def test_topology_commit_waits_for_active_pan_to_end(page):
    goto_board(page)
    stage = page.locator('#board-stage')
    stage.dispatch_event('pointerdown', {'button': 0, 'clientX': 100, 'clientY': 100, 'pointerId': 1})
    page.evaluate('''() => {
      for(const r of repos.slice(0,2))rememberRepoMetadata(r.path,{project_id:'/git/shared',project_path:repos[0].path,is_worktree:r!==repos[0]});
      renderBoard();
    }''')
    assert page.evaluate('boardProjects.length') == 4
    assert page.evaluate('boardScene.plots.length') == 5
    stage.dispatch_event('pointerup', {'button': 0, 'pointerId': 1})
    assert page.evaluate('boardScene.plots.length') == 4
    assert page.evaluate('boardMembershipPending') is False


def test_zero_repos_have_a_finite_empty_scene(page):
    page.evaluate("repos=[]; rebuildProjectModel(); renderBoard();")
    assert page.evaluate('boardLayoutReady')
    assert page.evaluate('({empty:boardScene.empty,width:boardScene.width,height:boardScene.height,plots:boardScene.plots,targets:boardScene.targets})') == {
        'empty': True, 'width': 430, 'height': 240, 'plots': [], 'targets': []}
    assert page.evaluate('boardScene.islands[0].cols===0 && boardScene.islands[0].rows===0')
    assert page.evaluate('Object.values(boardCamera).every(Number.isFinite) && pickBoardPlot(0,0)===null')
    assert page.evaluate('boardActivePageKey') == 'workspace:0'


def test_empty_neighborhood_has_no_terrain_ground_or_targets(page):
    goto_board(page)
    result = page.evaluate('''() => {
      boardNeighborhoods=[{key:'workspace',name:'Workspace',projectKeys:[]}];renderBoard();
      const g=boardScene.islands[0];return {empty:boardScene.empty,finite:[g.x,g.y,g.width,g.height,g.titleY,g.origin.x,g.origin.y].every(Number.isFinite)};
    }''')
    assert result == {'empty': True, 'finite': True}
    assert page.locator('#board-terrain, #board-ground, .tile, .plot-name').count() == 0
    page.wait_for_timeout(250)
    assert page.locator('#board-ground').count() == 0


def test_removing_last_page_project_clears_scene_and_keeps_finite_camera(page):
    seed_projects(page, [MAIN], {MAIN: {}})
    goto_board(page)
    page.evaluate('repos=[];rebuildProjectModel();renderBoard();')
    assert page.locator('#board-terrain, #board-ground, .tile, .plot-name').count() == 0
    assert page.locator('#board-empty').is_visible()
    assert page.evaluate('boardScene.empty && Object.values(boardCamera).every(Number.isFinite)')


def test_pagination_counts_projects_and_keeps_global_numbers(page):
    paths = [f'/many/p{i:02}' for i in range(90)]
    seed_projects(page, paths, {path: {} for path in paths})
    goto_board(page)
    assert page.evaluate('boardIslands(boardNeighborhoods).map(p=>p.projectKeys.length)') == [25, 25, 25, 15]
    page.evaluate('boardGo(4)')
    assert page.evaluate('boardActivePageKey') == 'workspace:3'
    assert sorted(page.evaluate('boardScene.plots.map(p=>p.number)')) == list(range(76, 91))
    page.locator('#board-search').fill('p89')
    assert page.evaluate('boardIslands(boardNeighborhoods).length') == 4


def test_twenty_six_checkouts_consume_one_project_plot(page):
    paths = [MAIN, *[f'/projects/oak-w{i:02}' for i in range(25)]]
    seed_projects(page, paths)
    goto_board(page)
    assert page.locator('.tile').count() == 1
    assert page.evaluate('boardIslands(boardNeighborhoods).length') == 1
    assert page.evaluate('boardScene.targets.length') == 4
    assert len(project_state(page)[0]['paths']) == 26


def test_remote_identity_survives_local_error_and_omission_until_explicit_clear(page):
    page.evaluate("rememberRepoMetadata(repos[0].path,{github_repo:'demo/oak'});")
    page.route('**/api/repos/status?*', lambda route: route.fulfill(status=503, json={'error': 'offline'}))
    page.evaluate('fetchStatus(0)')
    assert page.evaluate('githubIdentityByPath.get(repos[0].path)') == 'demo/oak'
    page.route('**/api/repos/status?*', lambda route: route.fulfill(json={'dirty': {'is_clean': True}}))
    page.evaluate('fetchBoardStatus(0)')
    assert page.evaluate('githubIdentityByPath.get(repos[0].path)') == 'demo/oak'
    page.route('**/api/repos/status?*', lambda route: route.fulfill(json={'dirty': {'is_clean': True}, 'github_repo': None}))
    page.evaluate('fetchStatus(0)')
    assert page.evaluate('githubIdentityByPath.get(repos[0].path)') is None
