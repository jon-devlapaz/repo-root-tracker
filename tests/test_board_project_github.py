"""Authoritative project GitHub coverage, exercised through the whole dashboard."""
from datetime import datetime, timedelta, timezone

import pytest

from test_board import page  # noqa: F401
from test_board_saplings import MAIN, WORKTREES, member, project_board

SLUG = 'demo/oak'


def payload(state='passing', *, slug=SLUG, old=False, pr=False):
    date = datetime.now(timezone.utc) - (timedelta(minutes=5) if old else timedelta())
    return {'has_github': True, 'repo': slug, 'repo_url': 'https://github.com/' + slug,
            'checked_at': date.isoformat(), 'default_branch': 'main', 'errors': [], 'issues': [],
            'prs': [{'number': 7, 'title': 'Fix checks', 'url': f'https://github.com/{slug}/pull/7',
                     'ci': {'state': 'fail', 'failing': 1}}] if pr else [],
            'workflows': {'state': state, 'errors': [], 'runs': [{
                'name': 'Build', 'current_head': state != 'stale',
                'status': 'in_progress' if state == 'pending' else 'completed',
                'conclusion': 'failure' if state == 'failing' else 'cancelled' if state == 'unknown' else 'success',
                'url': f'https://github.com/{slug}/actions/runs/1', 'workflow_state': 'active'}]}}


def identify(page, paths=None, slug=SLUG):
    page.evaluate('''({paths,slug})=>{for(const path of paths){const r=repoByPath.get(path);r._status.github_repo=slug;rememberRepoMetadata(path,r._status);}renderBoard()}''',
                  {'paths': paths or [MAIN, *WORKTREES], 'slug': slug})


def accept(page, info, number=1):
    assert page.evaluate('''({info,number})=>acceptGithubSnapshot(info.repo,number,info)''', {'info': info, 'number': number})
    page.evaluate('render()')


@pytest.mark.parametrize('reverse', [False, True])
def test_unavailable_main_stale_pass_cannot_hide_sibling_fresh_failure(page, reverse):
    project_board(page, 8)
    identify(page)
    old = payload(old=True)
    accept(page, old)
    page.evaluate('repoByPath.get("/projects/oak")._status={error:true};renderBoard()')
    fresh = payload('failing', pr=True)
    page.route('**/api/github?*', lambda route: route.fulfill(json=fresh))
    page.evaluate('async()=>{await fetchGithub(repoByPath.get("/projects/oak-w07"));renderBoard()}')
    # Compatibility mirrors deliberately disagree; authority must ignore them.
    page.evaluate('''({old,reverse})=>{repoByPath.get('/projects/oak')._github=old;if(reverse){repos.reverse();rebuildProjectModel();}renderBoard();selectBoardRepo('/projects/oak')}''', {'old': old, 'reverse': reverse})
    gh = page.evaluate('boardFamilyGithub(boardProjects[0])')
    assert gh['workflowFailures'] == gh['blocked'] == 1
    assert page.locator('.tile').get_attribute('data-tone') == 'blocked'
    assert page.locator('[data-family-gh]').get_attribute('data-tone') == 'blocked'
    assert '1 failing workflow' in page.locator('#board-inspector').inner_text()
    assert '1 PR with blockers' in page.locator('#board-inspector').inner_text()
    assert page.evaluate('gardenSummary().attention') == 2  # one source plus one unavailable checkout
    assert page.evaluate('repos.every(boardNeedsAttention)')
    page.evaluate("location.hash='#/list'")
    page.wait_for_selector('#list-view', state='visible')
    assert page.locator('.gh-signal').count() == 9
    assert page.locator('.gh-signal').evaluate_all("els=>els.every(el=>el.textContent.includes('1 failing workflow'))")
    assert '1 failing default-branch workflow across 1 repo' in page.locator('#attention-heading').inner_text()


@pytest.mark.parametrize('reverse', [False, True])
def test_unavailable_main_stale_failure_cannot_survive_sibling_fresh_success(page, reverse):
    project_board(page, 8)
    identify(page)
    old = payload('failing', old=True, pr=True)
    accept(page, old)
    page.evaluate('repoByPath.get("/projects/oak")._status={error:true};renderBoard()')
    page.route('**/api/github?*', lambda route: route.fulfill(json=payload()))
    page.evaluate('async()=>{await fetchGithub(repoByPath.get("/projects/oak-w07"));renderBoard()}')
    page.evaluate('''({old,reverse})=>{repoByPath.get('/projects/oak')._github=old;if(reverse){repos.reverse();rebuildProjectModel();}renderBoard();selectBoardRepo('/projects/oak')}''', {'old': old, 'reverse': reverse})
    gh = page.evaluate('boardFamilyGithub(boardProjects[0])')
    assert gh['workflowFailures'] == gh['blocked'] == 0
    assert 'passing' in gh['label']
    assert page.locator('.tile').get_attribute('data-tone') == 'unavailable'
    assert page.locator('[data-family-gh]').get_attribute('data-tone') == 'clean'
    assert page.locator('#board-inspector .board-pr-list').count() == 0
    assert page.evaluate('gardenSummary().attention') == 1
    assert page.evaluate('boardNeedsAttention(repoByPath.get("/projects/oak-w07"))') is False
    assert page.evaluate('boardNeedsAttention(repoByPath.get("/projects/oak"))') is True
    assert page.evaluate('githubSnapshotForRepo(repoByPath.get("/projects/oak")).requestNumber') == 2


def test_latest_slug_request_wins_over_late_response(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    accept(page, payload('failing', pr=True), 3)
    assert page.evaluate('info=>acceptGithubSnapshot(info.repo,2,info)', payload()) is False
    assert page.evaluate('boardGithub(repos[0]).workflowFailures') == 1
    accept(page, payload(), 4)
    assert page.evaluate('info=>acceptGithubSnapshot(info.repo,3,info)', payload('failing', pr=True)) is False
    assert page.evaluate('boardFamilyGithub(boardProjects[0]).blocked') == 0


def test_failed_refresh_replaces_passing_coverage_with_incomplete(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    accept(page, payload())
    page.route('**/api/github?*', lambda route: route.fulfill(status=503, json={'error': 'offline'}))
    page.evaluate('async()=>{await fetchGithub(repos[1],true);selectBoardRepo(repos[0].path)}')
    gh = page.evaluate('boardFamilyGithub(boardProjects[0])')
    assert gh['incomplete'] and gh['workflowUnconfirmed']
    assert page.evaluate('githubBySlug.get("demo/oak").transportFailed')
    assert 'GitHub incomplete' in page.locator('#board-inspector').inner_text()
    assert 'passing' not in page.locator('#board-inspector').inner_text()
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])') is False


def test_partial_current_failure_survives_other_missing_sections(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    info = payload('failing')
    del info['issues']
    del info['prs']
    page.route('**/api/github?*', lambda route: route.fulfill(json=info))
    page.evaluate('async()=>{await fetchGithub(repos[1]);renderBoard()}')
    gh = page.evaluate('boardFamilyGithub(boardProjects[0])')
    assert gh['incomplete'] and gh['workflowFailures'] == 1
    assert page.locator('.plot-number').get_attribute('data-tone') == 'blocked'


@pytest.mark.parametrize('state', ['pending', 'unknown', 'stale', 'missing', 'incomplete'])
def test_unconfirmed_coverage_never_uses_a_clean_shared_badge(page, state):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    info = payload('passing' if state in ['missing', 'incomplete'] else state)
    if state == 'missing':
        del info['workflows']
    if state == 'incomplete':
        info['errors'] = ['Pull requests unavailable']
    accept(page, info)
    badge = page.locator('[data-family-gh]')
    assert badge.get_attribute('data-tone') == ('unavailable' if state == 'incomplete' else 'unknown')
    assert badge.get_attribute('data-coverage') in ['incomplete', 'unconfirmed']
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])') is False
    assert 'Project-wide GitHub:' in page.locator('.tile').get_attribute('aria-description')
    assert 'Circle: project-wide GitHub' in page.locator('.board-legend').inner_text()
    assert '+N: hidden worktrees' in page.locator('.board-legend').inner_text()


@pytest.mark.parametrize('old_date', [None, '2000-01-01T00:00:00Z'])
def test_expired_snapshot_cannot_establish_calm(page, old_date):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    info = payload(old=True)
    if old_date:
        info['checked_at'] = old_date
    accept(page, info)
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])') is False
    assert 'previous check (expired)' in page.locator('.tile').get_attribute('aria-description')
    assert 'previous GitHub check' in page.locator('#board-brief').inner_text()
    assert page.locator('[data-family-gh]').get_attribute('data-tone') == 'unknown'


def test_legacy_timestamp_uses_receive_time_and_known_date_is_preserved(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    info = payload()
    del info['checked_at']
    accept(page, info)
    assert page.evaluate('githubSnapshotFresh(githubBySlug.get("demo/oak"))')
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])')
    accept(page, payload(old=True), 2)
    assert not page.evaluate('githubSnapshotFresh(githubBySlug.get("demo/oak"))')


def test_distinct_project_slugs_are_not_merged(page):
    project_board(page, 1)
    identify(page, [MAIN])
    identify(page, [WORKTREES[0]], 'demo/second')
    accept(page, payload('failing', pr=True))
    accept(page, payload('failing', slug='demo/second', pr=True))
    gh = page.evaluate('boardFamilyGithub(boardProjects[0])')
    assert gh['blocked'] == gh['workflowFailures'] == 2
    assert page.evaluate('gardenSummary().attention') == 2


def test_remote_change_does_not_accept_old_slug_response(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    page.evaluate('''()=>{window.oldGithubRequest=new Promise(resolve=>window.finishOldGithub=resolve);window.fetch=()=>oldGithubRequest;window.oldGithubDone=fetchGithub(repos[0]);}''')
    page.wait_for_function('githubTasks.size===1')
    identify(page, [MAIN], 'demo/new')
    accept(page, payload(slug='demo/new'))
    page.evaluate('''async info=>{finishOldGithub({ok:true,json:async()=>info});await oldGithubDone;renderBoard()}''', payload('failing', pr=True))
    assert page.evaluate('githubIdentityByPath.get("/projects/oak")') == 'demo/new'
    assert page.evaluate('githubSnapshotForRepo(repoByPath.get("/projects/oak")).info.repo') == 'demo/new'
    assert page.evaluate('repoByPath.get("/projects/oak")._github.repo') == 'demo/new'
    assert page.evaluate('boardGithub(repoByPath.get("/projects/oak")).workflowFailures') == 0
    # The unchanged sibling can still use the captured old source.
    assert page.evaluate('boardGithub(repoByPath.get("/projects/oak-w00")).workflowFailures') == 1


def test_forced_refresh_during_ordinary_request_queues_one_followup(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    page.evaluate('''({ordinary,forced})=>{
      window.githubCalls=[];window.fetch=url=>{githubCalls.push(url);return githubCalls.length===1?
        new Promise(resolve=>window.releaseOrdinary=()=>resolve({ok:true,json:async()=>ordinary})):
        Promise.resolve({ok:true,json:async()=>forced});};
      window.firstCheck=fetchGithub(repos[0]);
      window.forceOne=fetchGithub(repos[1],true);window.forceTwo=fetchGithub(repos[0],true);
    }''', {'ordinary': payload(), 'forced': payload('failing', pr=True)})
    page.wait_for_function('githubCalls.length===1')
    page.evaluate('async()=>{releaseOrdinary();await Promise.all([firstCheck,forceOne,forceTwo]);renderBoard()}')
    calls = page.evaluate('githubCalls')
    assert len(calls) == 2 and not calls[0].endswith('&refresh=1') and calls[1].endswith('&refresh=1')
    assert page.evaluate('githubBySlug.get("demo/oak").requestNumber') == 2
    assert page.evaluate('boardFamilyGithub(boardProjects[0]).workflowFailures') == 1
    assert page.evaluate('githubTasks.size===0 && githubForcedFollowups.size===0')


@pytest.mark.parametrize('anonymous', [False, True])
def test_no_remote_snapshots_are_path_scoped_and_only_local_absence_skips_freshness(page, anonymous):
    project_board(page, 1)
    if anonymous:
        page.evaluate('delete repos[0]._status.github_repo;githubIdentityByPath.delete(repos[0].path)')
    info = {'has_github': False, 'repo': '', 'prs': [], 'issues': [], 'errors': [], 'checked_at': '2000-01-01T00:00:00Z'}
    page.route('**/api/github?*', lambda route: route.fulfill(json=info))
    page.evaluate('async()=>{await fetchGithub(repos[0]);renderBoard()}')
    assert page.evaluate('githubBySlug.size') == 0
    assert page.evaluate('githubByPath.size') == 1
    assert page.evaluate('githubSnapshotForRepo(repos[1])===undefined')
    assert page.evaluate('repos[1]._github===undefined')
    # A current local null proves no source needs coverage. An expired anonymous
    # negative response alone cannot prove that the checkout still has no remote.
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])') is (not anonymous)


def test_path_scoped_positive_response_preserves_workflow_uncertainty(page):
    project_board(page, 1)
    page.route('**/api/github?*', lambda route: route.fulfill(json=payload('pending')))
    page.evaluate('async()=>{await fetchGithub(repos[0]);renderBoard()}')
    assert page.evaluate('githubBySlug.size') == 0
    assert page.evaluate('githubByPath.size') == 1
    assert page.evaluate('boardGithub(repos[0]).workflowUnconfirmed')
    assert not page.evaluate('boardIslandCalm(boardScene.islands[0])')
    assert page.locator('[data-family-gh]').get_attribute('data-tone') == 'unknown'


def test_late_response_cannot_replace_a_newer_accepted_request(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    page.evaluate('''()=>{window.fetch=()=>new Promise(resolve=>window.releaseOld=resolve);window.oldDone=fetchGithub(repos[0])}''')
    page.wait_for_function('typeof releaseOld==="function"')
    accept(page, payload(), 2)
    page.evaluate('''async info=>{releaseOld({ok:true,json:async()=>info});await oldDone;renderBoard()}''', payload('failing', pr=True))
    assert page.evaluate('githubBySlug.get("demo/oak").requestNumber') == 2
    assert page.evaluate('boardFamilyGithub(boardProjects[0]).blocked') == 0
    assert page.evaluate('boardFamilyGithub(boardProjects[0]).workflowFailures') == 0


def test_bulk_forced_refresh_during_ordinary_batch_queues_one_forced_batch(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    page.evaluate('''({ordinary,forced})=>{
      const original=window.fetch;window.githubCalls=[];
      window.fetch=(url,...args)=>{if(!String(url).startsWith('/api/github?'))return original(url,...args);
        githubCalls.push(url);return githubCalls.length===1?new Promise(resolve=>window.releaseBulk=()=>resolve({ok:true,json:async()=>ordinary})):
          Promise.resolve({ok:true,json:async()=>forced});};
      window.bulkOrdinary=refreshGithubAll();window.bulkForceOne=refreshGithubAll(true);window.bulkForceTwo=refreshGithubAll(true);
    }''', {'ordinary': payload(), 'forced': payload('failing')})
    page.wait_for_function('githubCalls.length===1')
    page.evaluate('async()=>{releaseBulk();await Promise.all([bulkOrdinary,bulkForceOne,bulkForceTwo]);renderBoard()}')
    calls = page.evaluate('githubCalls')
    assert len(calls) == 2 and calls[1].endswith('&refresh=1')
    assert page.evaluate('githubBySlug.get("demo/oak").requestNumber') == 2
    assert page.evaluate('boardFamilyGithub(boardProjects[0]).workflowFailures') == 1
    assert page.evaluate('!refreshingGithub && !githubBulkForcedFollowup && githubTasks.size===0')


@pytest.mark.parametrize('reverse', [False, True])
def test_bulk_check_prefers_an_available_retained_sibling_independently_of_order(page, reverse):
    project_board(page, 8)
    identify(page)
    page.evaluate('''reverse=>{repos[0]._status={error:true};if(reverse){repos.reverse();rebuildProjectModel()}renderBoard()}''', reverse)
    calls = []

    def response(route):
        calls.append(route.request.url)
        route.fulfill(json=payload('failing'))

    page.route('**/api/github?*', response)
    page.evaluate('async()=>{await refreshGithubAll();renderBoard()}')
    assert len(calls) == 1 and calls[0].endswith('path=%2Fprojects%2Foak-w00')
    assert page.evaluate('boardGithub(repoByPath.get("/projects/oak")).workflowFailures') == 1
    assert page.evaluate('boardFamilyGithub(boardProjects[0]).workflowFailures') == 1


def test_detail_view_uses_current_store_and_labels_old_backend_timestamp(page):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    old = payload('failing', pr=True)
    accept(page, old)
    page.evaluate('''info=>{detailPath='/projects/oak';githubData=info;githubLoadedForPath=detailPath;renderGithub()}''', old)
    assert page.locator('#tab-github .workflow-health').get_attribute('data-tone') == 'blocked'
    identify(page, [MAIN], 'demo/new')
    page.evaluate('renderGithub()')
    assert page.locator('#tab-github .workflow-health').count() == 0
    assert 'GitHub not checked' in page.locator('#tab-github').text_content()
    assert 'Fix checks' not in page.locator('#tab-github').text_content()
    accept(page, payload(slug='demo/new', old=True))
    assert page.locator('#tab-github .workflow-health').get_attribute('data-state') == 'passing'
    assert 'Previous GitHub check' in page.locator('#tab-github').text_content()


@pytest.mark.parametrize('checking', ['github', 'local', 'queued'])
def test_rechecking_clean_coverage_suppresses_calm_without_a_new_bloom(page, checking):
    project_board(page, 1)
    identify(page, [MAIN, WORKTREES[0]])
    accept(page, payload())
    # The first successful check is a real coverage transition; clear that bloom.
    page.evaluate("document.querySelectorAll('.board-bloom').forEach(el=>el.remove())")
    page.evaluate('''checking=>{
      if(checking==='github')githubTasks.set('demo/oak',Promise.resolve());
      else repos[0][checking==='local'?'_checking':'_boardQueued']=true;
      renderBoard();
    }''', checking)
    assert not page.evaluate('boardIslandCalm(boardScene.islands[0])')
    page.evaluate('''()=>{githubTasks.clear();repos[0]._checking=false;repos[0]._boardQueued=false;renderBoard()}''')
    assert page.evaluate('boardIslandCalm(boardScene.islands[0])')
    assert page.locator('.board-bloom').count() == 0


def test_accepting_a_missing_snapshot_is_a_safe_no_op(page):
    result = page.evaluate("""() => ({undef: acceptGithubSnapshot('demo/x', 1, undefined), nul: acceptGithubSnapshot('demo/x', 2, null), stored: githubBySlug.has('demo/x')})""")
    assert result == {'undef': False, 'nul': False, 'stored': False}
