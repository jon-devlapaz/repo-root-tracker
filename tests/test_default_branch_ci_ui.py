"""Current-head workflow signals across the whole dashboard.

Uses the served, complete dashboard and the existing board page fixture.
"""

from urllib.parse import unquote

import pytest

from test_board import PATHS, goto_board, page

RUN_URL = 'https://github.com/demo/shared/actions/runs/42'


def github_payload(state='failing', conclusion='failure', *, current_head=True, prs=None, errors=None):
    return {
        'has_github': True, 'repo': 'demo/shared', 'repo_url': 'https://github.com/demo/shared',
        'default_branch': 'trunk', 'checked_at': '2026-10-01T00:00:00Z',
        'prs': prs or [], 'issues': [], 'errors': errors or [],
        'workflows': {'state': state, 'head_sha': 'a' * 40, 'errors': errors or [], 'runs': [{
            'name': 'Build', 'workflow_id': 1, 'status': 'in_progress' if state == 'pending' else 'completed',
            'conclusion': conclusion, 'url': RUN_URL, 'updated_at': '2026-10-01T00:00:00Z',
            'current_head': current_head, 'head_sha': ('a' if current_head else 'b') * 40,
            'workflow_state': 'active',
        }]},
    }


def check_github(page, payload, *, family=False, remote=True):
    statuses = page.evaluate('''({family, remote}) => {
      return repos.map((r, i) => {
        r._status.dirty = {is_clean:true};
        r._status.sync = {has_upstream:true,ahead:0,behind:0};
        r._status.stale_branches = [];
        r._status.github_repo = remote && (i === 0 || (family && i === 1)) ? 'demo/shared' : null;
        if (family && i < 2) {
          r._status.project_id = 'shared'; r._status.project_path = repos[0].path;
          r._status.is_worktree = i === 1;
        }
        rememberRepoMetadata(r.path,r._status);
        return r._status;
      });
    }''', {'family': family, 'remote': remote})

    def status(route):
        path = unquote(route.request.url.split('path=', 1)[1].split('&', 1)[0])
        route.fulfill(json=statuses[PATHS.index(path)])

    requests = []

    def github(route):
        requests.append(route.request.url)
        route.fulfill(json=payload)

    page.route('**/api/repos/status?*', status)
    page.route('**/api/github?*', github)
    page.route('**/api/repo?*', lambda route: route.fulfill(status=410, json={'error': 'Detail fixture unavailable'}))
    page.evaluate('render()')
    if remote:
        page.get_by_role('button', name='Check GitHub', exact=True).click()
    else:
        page.evaluate('fetchGithub(repos[0])')
    page.wait_for_function('!refreshingGithub && githubTasks.size === 0')
    return requests


def test_failing_ci_without_prs_overrides_clean_and_reaches_every_view(page):
    requests = check_github(page, github_payload())
    assert len(requests) == 1
    card = page.locator('#card-0')
    assert card.get_attribute('data-tone') == 'blocked'
    assert card.locator('.repo-label').first.get_attribute('data-tone') == 'clean'
    assert card.locator('.gh-signal').get_attribute('data-tone') == 'blocked'
    assert 'Default-branch CI on trunk: 1 failing workflow' in card.inner_text()
    assert 'no known PR blockers' in page.locator('#attention-heading').inner_text()
    assert '1 failing default-branch workflow across 1 repo' in page.locator('#attention-heading').inner_text()
    assert 'failing default-branch CI' in page.locator('#list-brief').inner_text()
    assert page.title() == '(1) repo-root-tracker'
    assert page.locator('[data-workflow-attention] a').first.get_attribute('href') == RUN_URL
    page.locator('#filter-attention').click()
    assert page.locator('.repo-card').count() == 1

    goto_board(page)
    plot = page.locator(f'.board-select[data-path="{PATHS[0]}"]')
    assert plot.locator('.plot-number').get_attribute('data-tone') == 'blocked'
    assert plot.locator('.status-ring[data-tone="blocked"]').count() == 1
    assert plot.locator('[data-workflow-ci="true"] text').text_content() == 'CI'
    assert plot.locator('[data-marker="calm"]').count() == 0
    assert 'failing default-branch CI' in page.locator('#board-brief').inner_text()
    page.locator('#board-attention').check()
    assert 'dimmed' not in page.locator(f'.tile[data-path="{PATHS[0]}"]').get_attribute('class')
    assert 'dimmed' in page.locator(f'.tile[data-path="{PATHS[1]}"]').get_attribute('class')
    page.evaluate('selectBoardRepo(repos[0].path)')
    inspector = page.locator('#board-inspector')
    assert inspector.get_attribute('data-tone') == 'blocked'
    assert inspector.locator('.inspector-local').get_attribute('data-tone') == 'clean'
    assert 'Project-wide GitHub' in inspector.inner_text()
    assert inspector.locator('.workflow-run a').get_attribute('href') == RUN_URL
    page.locator('#board-open-github').click()
    page.wait_for_selector('#tab-github .workflow-health')
    assert page.locator('#tab-github .workflow-health').get_attribute('data-tone') == 'blocked'
    assert page.locator('#tab-github .workflow-run a').get_attribute('href') == RUN_URL
    assert 'No open pull requests.' in page.locator('#tab-github').inner_text()


def test_shared_worktree_ci_is_checked_and_counted_once_without_pr_blockers(page):
    requests = check_github(page, github_payload(), family=True)
    assert len(requests) == 1
    assert page.locator('[data-workflow-attention]').count() == 1
    assert 'across 1 repo' in page.locator('#attention-heading').inner_text()
    assert page.locator('#list-brief').inner_text().count('failing default-branch CI') == 1
    page.locator('#filter-attention').click()
    assert page.locator('.repo-card').count() == 2
    goto_board(page)
    page.evaluate('selectBoardRepo(repos[1].path)')
    assert page.locator('[data-family-gh]').count() == 1
    assert page.locator('[data-family-gh] text').text_content() == 'CI'
    assert page.locator('.tile[data-project="git:shared"] [data-repo-gh]').count() == 0
    family = page.evaluate("boardFamilyGithub(boardProjects.find(g => g.key === 'git:shared'))")
    assert family['blocked'] == 0
    assert family['workflowFailures'] == 1
    assert len(family['workflows']) == 1
    assert page.locator('#board-inspector .workflow-run').count() == 1
    assert page.locator('#board-inspector').get_attribute('data-tone') == 'blocked'


@pytest.mark.parametrize('state,conclusion,current_head,copy', [
    ('pending', '', True, 'pending · unconfirmed'),
    ('unknown', 'cancelled', True, 'unconfirmed · cancelled'),
    ('stale', 'success', False, 'stale · current commit unconfirmed'),
    ('stale', 'failure', False, 'stale · current commit unconfirmed'),
    ('unknown', '', False, 'unconfirmed'),
])
def test_pending_cancelled_unknown_and_stale_are_not_passing_or_blockers(page, state, conclusion, current_head, copy):
    check_github(page, github_payload(state, conclusion, current_head=current_head))
    signal = page.locator('#card-0 .gh-signal')
    assert copy in signal.inner_text()
    assert 'passing' not in signal.inner_text().lower()
    assert signal.get_attribute('data-tone') != 'blocked'
    assert 'default-branch CI unconfirmed' in page.locator('#list-brief').inner_text()
    assert 'calm' not in page.locator('#list-brief').inner_text()
    assert page.evaluate("matchesFilter(repos[0], 'attention')") is False
    signal.click()
    page.wait_for_selector('#tab-github .workflow-health')
    section = page.locator('#tab-github .workflow-health')
    assert copy in section.inner_text()
    assert 'passing' not in section.inner_text().lower()
    assert section.get_attribute('data-tone') != 'blocked'
    assert section.locator('.workflow-run a').get_attribute('href') == RUN_URL
    page.locator('#back-btn').click()
    goto_board(page)
    page.evaluate('selectBoardRepo(repos[0].path)')
    assert page.locator('.board-family-gh').get_attribute('data-tone') == 'unknown'
    assert copy in page.locator('.board-family-gh').inner_text()


def test_pr_and_workflow_counts_are_separate_even_with_partial_data(page):
    pr = {'number': 7, 'title': 'Fix', 'url': 'https://github.com/demo/shared/pull/7', 'ci': {'state': 'fail', 'failing': 2}}
    check_github(page, github_payload(prs=[pr], errors=['Issues could not be checked.']))
    heading = page.locator('#attention-heading').inner_text()
    assert '1 PR with blockers' in heading
    assert '1 failing default-branch workflow across 1 repo' in heading
    assert '1 incomplete' in heading
    assert '2 PRs with blockers' not in heading
    goto_board(page)
    page.evaluate('selectBoardRepo(repos[0].path)')
    data = page.evaluate('boardFamilyGithub({paths:[repos[0].path]})')
    assert data['blocked'] == 1 and data['workflowFailures'] == 1
    assert page.locator('.board-family-gh').get_attribute('data-tone') == 'blocked'
    assert page.locator('#board-inspector .workflow-run a').get_attribute('href') == RUN_URL


def test_mixed_workflow_results_show_each_run_and_failed_ci_remains_attention(page):
    payload = github_payload()
    payload['workflows']['runs'].append(dict(payload['workflows']['runs'][0], name='Lint', conclusion='success', url=RUN_URL + '1'))
    check_github(page, payload)
    assert page.locator('#card-0').get_attribute('data-tone') == 'blocked'
    assert '1 failing workflow' in page.locator('#card-0 .gh-signal').inner_text()
    page.locator('#card-0 .gh-signal').click()
    page.wait_for_selector('#tab-github .workflow-health')
    assert page.locator('#tab-github .workflow-run').count() == 2
    assert page.locator('#tab-github .workflow-run a').all_text_contents() == ['Build', 'Lint']
    assert 'passing' not in page.locator('#tab-github .workflow-summary').inner_text()


def test_current_success_is_passing_but_stale_success_is_not(page):
    check_github(page, github_payload('passing', 'success'))
    assert 'passing' in page.locator('#card-0 .gh-signal').inner_text()
    assert page.locator('#card-0').get_attribute('data-tone') == 'clean'
    assert page.evaluate("matchesFilter(repos[0], 'attention')") is False
    page.locator('#card-0 .gh-signal').click()
    page.wait_for_selector('#tab-github .workflow-health')
    assert page.locator('#tab-github .workflow-health').get_attribute('data-state') == 'passing'
    assert 'Current commit · success' in page.locator('#tab-github .workflow-run').inner_text()


def test_inaccessible_ci_stays_explicit_without_hiding_other_github_data(page):
    payload = github_payload('unknown', '', current_head=False, errors=['Default-branch workflow runs could not be checked.'])
    payload['workflows']['runs'] = []
    check_github(page, payload)
    signal = page.locator('#card-0 .gh-signal')
    assert signal.get_attribute('data-tone') == 'unavailable'
    assert 'unconfirmed' in signal.inner_text()
    assert 'passing' not in signal.inner_text()
    assert page.evaluate("matchesFilter(repos[0], 'attention')") is False
    signal.click()
    page.wait_for_selector('#tab-github .workflow-health')
    assert 'workflow runs could not be checked' in page.locator('#tab-github').inner_text()
    assert 'No workflow runs confirmed for the current commit.' in page.locator('#tab-github .workflow-health').inner_text()
    assert 'No open pull requests.' in page.locator('#tab-github').inner_text()


def test_long_branch_and_workflow_names_fit_mobile(page):
    payload = github_payload()
    payload['default_branch'] = 'release/' + 'x' * 90
    payload['workflows']['runs'][0]['name'] = 'Build ' + 'Long workflow name ' * 8
    page.set_viewport_size({'width': 390, 'height': 844})
    check_github(page, payload)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#card-0 .gh-signal').click()
    page.wait_for_selector('#tab-github .workflow-health')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def test_shared_ci_title_counts_once_and_local_problems_count_per_checkout(page):
    check_github(page, github_payload(), family=True)
    assert page.title() == '(1) repo-root-tracker'
    assert page.evaluate('gardenSummary().attention') == 1
    goto_board(page)
    assert page.title() == '(1) repo-root-tracker'
    page.evaluate('''() => {
      repos[0]._status.dirty = {is_clean:false,modified:1,kinds:{conflicted:1}};
      render();
    }''')
    assert page.title() == '(2) repo-root-tracker'  # one shared CI failure, one local conflict
    page.evaluate('''() => {
      repos[1]._status.dirty = {is_clean:false,modified:1,kinds:{conflicted:1}};
      render();
    }''')
    assert page.title() == '(3) repo-root-tracker'
    page.evaluate('''() => { repos[0]._status.error = true; render(); }''')
    assert page.title() == '(3) repo-root-tracker'  # CI, one unreadable checkout, one conflict


def test_different_github_repositories_in_one_family_count_separately(page):
    check_github(page, github_payload(), family=True)
    page.evaluate('''() => {
      repos[1]._status.github_repo = 'demo/another';
      rememberRepoMetadata(repos[1].path,repos[1]._status);
      acceptGithubSnapshot('demo/another',1,{...githubBySlug.get('demo/shared').info,repo:'demo/another'});
      render();
    }''')
    assert page.title() == '(2) repo-root-tracker'
    assert page.evaluate('gardenSummary().attention') == 2


@pytest.mark.parametrize('health', [None, {'state': 'unknown', 'head_sha': '', 'runs': [], 'errors': []}])
def test_no_github_remote_never_shows_or_counts_unknown_ci(page, health):
    # Also tolerate the previous server payload with an empty workflow object.
    payload = {'has_github': False, 'repo': '', 'repo_url': '', 'default_branch': '',
               'gh_unavailable': False, 'prs': [], 'issues': [], 'errors': [], 'workflows': health}
    requests = check_github(page, payload, remote=False)
    assert len(requests) == 1
    assert page.locator('#card-0 .gh-signal').count() == 0
    assert page.locator('#list-brief').inner_text() == 'All 5 repos are calm.'
    assert page.title() == 'repo-root-tracker'
    assert page.evaluate('workflowSignal(repos[0]._github).label') == ''
    page.evaluate("location.hash = '#/repo/' + encodeURIComponent(repos[0].path) + '?tab=github'")
    page.wait_for_function('githubLoadedForPath === repos[0].path')
    assert 'No GitHub remote' in page.locator('#tab-github').inner_text()
    assert page.locator('#tab-github .workflow-health').count() == 0
    page.locator('#back-btn').click()
    goto_board(page)
    page.evaluate('selectBoardRepo(repos[0].path)')
    assert 'Default-branch CI' not in page.locator('#board-inspector').inner_text()
    assert page.locator('#board-brief').inner_text() == 'All 5 repos are calm.'


def test_github_access_failure_keeps_unknown_ci_when_remote_is_identified(page):
    payload = github_payload('unknown', '', current_head=False, errors=['Default branch could not be checked.'])
    payload.update(has_github=False, gh_unavailable=True, default_branch='')
    payload['workflows']['runs'] = []
    check_github(page, payload)
    assert 'Default-branch CI: unconfirmed' in page.locator('#card-0 .gh-signal').inner_text()
    assert '1 default-branch CI unconfirmed' in page.locator('#list-brief').inner_text()
    page.locator('#card-0 .gh-signal').click()
    page.wait_for_function('githubLoadedForPath === repos[0].path')
    assert 'Default-branch CI: unconfirmed' in page.locator('#tab-github .workflow-health').inner_text()
    page.locator('#back-btn').click()
    goto_board(page)
    page.evaluate('selectBoardRepo(repos[0].path)')
    assert 'Default-branch CI: unconfirmed' in page.locator('.board-family-gh').inner_text()
