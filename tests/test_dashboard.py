from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

DASHBOARD = Path(__file__).parents[1] / "src/repo_root_tracker/dashboard.html"
KEY = "repo-root-tracker.organization.v1"
PATHS = ["/workspace/apps/alpha", "/workspace/tools/alpha", "/workspace/apps/beta", '/workspace/apps/<odd>"repo']


@pytest.fixture()
def page():
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("http://dashboard.test/", lambda route: route.fulfill(
            content_type="text/html", body=DASHBOARD.read_text().replace("__HOME__", "/home/test", 1)
        ))
        page.route("**/api/repos", lambda route: route.fulfill(json=[{"path": path} for path in PATHS]))

        def status(route):
            path = route.request.url.split("path=", 1)[1]
            if "beta" in path:
                route.fulfill(status=410, json={"gone": True, "error": "Gone from disk"})
            else:
                dirty = "tools" in path
                route.fulfill(json={
                    "branch": "main", "dirty": {"is_clean": not dirty, "modified": int(dirty)},
                    "sync": {"has_upstream": True, "ahead": int(dirty), "behind": 0},
                    "last_commit": {"relative": "2 hours ago", "date": "2026-01-01T12:00:00Z"},
                })

        page.route("**/api/repos/status?*", status)
        page.goto("http://dashboard.test/")
        page.wait_for_function("repos.every(r => r._status)")
        yield page
        assert errors == []
        browser.close()


def create_collection(page, name):
    page.get_by_role("button", name="+ Collection").click()
    page.get_by_label("Collection name", exact=True).fill(name)
    page.get_by_role("button", name="Save collection").click()


def collection(page, name):
    return page.locator("section.collection").filter(has=page.get_by_role("button", name=name, exact=False))


def test_name_first_search_filters_and_escaped_paths(page):
    assert page.locator(".repo-name").all_text_contents() == ['<odd>"repo', "alpha", "alpha", "beta"]
    page.get_by_role("searchbox").fill("/tools/")
    assert page.locator(".repo-name").all_text_contents() == ["alpha"]
    page.get_by_role("searchbox").fill("")
    for label, names in [("Changed", ["alpha"]), ("Sync needed", ["alpha"]), ("Unavailable", ["beta"])]:
        page.get_by_role("button", name=label).click()
        assert page.locator(".repo-name").all_text_contents() == names
    page.get_by_role("searchbox").fill("not-a-project")
    assert page.get_by_text("No projects match your search or filter.").is_visible()
    page.get_by_role("button", name="Clear search and filters").click()
    assert page.locator(".repo-name").count() == 4
    assert page.locator(".repo-card script").count() == 0


def test_pins_collections_collapse_and_reload(page):
    create_collection(page, 'Tools <&> "work"')
    page.locator("#card-1 summary").click()
    page.locator("#collection-1").select_option(label='Tools <&> "work"')
    group = collection(page, 'Tools <&> "work"')
    assert group.locator(".repo-name").all_text_contents() == ["alpha"]
    group.locator(".collection-toggle").click()
    assert not group.locator(".repo-name").is_visible()
    assert group.locator(".collection-toggle").get_attribute("aria-expanded") == "false"
    page.locator("#card-0 .pin-button").click()
    assert collection(page, "★ Pinned").locator(".repo-name").all_text_contents() == ["alpha"]
    assert page.locator(".repo-name").count() == 4
    page.reload()
    page.wait_for_function("repos.every(r => r._status)")
    assert not collection(page, 'Tools <&> "work"').locator(".repo-name").is_visible()
    assert collection(page, "★ Pinned").locator(".repo-name").all_text_contents() == ["alpha"]
    page.locator("#repo-grouping").select_option("folder")
    assert collection(page, "/workspace/tools").locator(".repo-name").all_text_contents() == ["alpha"]
    assert page.locator(".repo-name").count() == 4


def test_collection_rename_delete_and_duplicate_validation(page):
    create_collection(page, "Tools")
    create_collection(page, "Apps")
    page.get_by_role("button", name="+ Collection").click()
    page.get_by_label("Collection name", exact=True).fill(" tools ")
    page.get_by_role("button", name="Save collection").click()
    assert page.get_by_role("alert").inner_text() == "Choose a nonempty, unique collection name."
    page.get_by_role("button", name="Cancel", exact=True).click()
    page.locator("#card-1 summary").click()
    page.locator("#collection-1").select_option(label="Tools")
    page.get_by_role("button", name="Rename Tools", exact=True).click()
    page.get_by_label("Collection name", exact=True).fill("Utilities")
    page.get_by_role("button", name="Save collection").click()
    assert collection(page, "Utilities").locator(".repo-name").count() == 1
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Delete collection Utilities", exact=True).click()
    assert collection(page, "Utilities").count() == 1
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete collection Utilities", exact=True).click()
    assert collection(page, "Utilities").count() == 0
    assert collection(page, "Unsorted").locator(".repo-name").count() == 4


def test_storage_failure_and_corrupt_preferences_are_visible(page):
    page.evaluate("key => localStorage.setItem(key, '{broken')", KEY)
    page.reload()
    assert "could not be loaded" in page.locator("#local-note").inner_text()
    page.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('blocked'); }; }")
    page.locator("#card-0 .pin-button").click()
    assert "last only for this session" in page.locator("#local-note").inner_text()
    assert collection(page, "★ Pinned").locator(".repo-name").count() == 1


def test_keyboard_focus_and_mobile_layout(page):
    button = page.locator("#card-0 .pin-button")
    button.focus()
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.className") == "pin-button"
    page.get_by_role("button", name="Changed").focus()
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "filter-changed"
    page.locator("#filter-all").click()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.locator("#card-1 summary").click()
    assert page.locator("#collection-1").is_visible()


def test_status_response_does_not_update_shifted_repo(page):
    result = page.evaluate("""async () => {
      let finish;
      const originalFetch = window.fetch;
      window.fetch = () => new Promise(resolve => { finish = resolve; });
      const first = repos[0];
      const second = repos[1];
      const originalStatus = second._status;
      const request = fetchStatus(0);
      repos.splice(0, 1);
      finish({status: 200, ok: true, json: async () => ({branch: 'removed-repo'})});
      await request;
      window.fetch = originalFetch;
      return {same: second._status === originalStatus, updated: first._status.branch};
    }""")
    assert result == {"same": True, "updated": "removed-repo"}


def test_repo_links_keep_detail_navigation(page):
    page.route("**/api/repo?*", lambda route: route.fulfill(status=410, json={"error": "repo gone from disk"}))
    page.locator("#card-2 .repo-name").click()
    playwright.expect(page.get_by_role("button", name="← All repos")).to_be_visible()
    playwright.expect(page.locator("#detail-header")).to_contain_text("beta")
    page.get_by_role("button", name="← All repos").click()
    playwright.expect(page.get_by_role("searchbox")).to_be_visible()


def test_recent_sort_empty_state_and_status_menu_refresh(page):
    page.evaluate("""() => {
      repos[2]._status = {branch: 'main', dirty: {is_clean: true}, last_commit: {date: '2026-02-01T00:00:00Z'}};
      render();
    }""")
    page.locator("#repo-sort").select_option("recent")
    assert page.locator(".repo-name").first.inner_text() == "beta"
    page.locator("#card-1 summary").click()
    page.locator("#collection-1").focus()
    page.evaluate("render()")
    assert page.locator("#card-1 details").get_attribute("open") is not None
    assert page.evaluate("document.activeElement.id") == "collection-1"
    page.keyboard.press("Escape")
    assert page.locator("#card-1 details").get_attribute("open") is None
    assert page.locator("#card-1 summary").evaluate("el => el === document.activeElement")
    page.evaluate("repos = []; render();")
    assert page.get_by_text("No repos tracked yet. Add a repository path below.").is_visible()
    assert page.locator("#add-btn").is_visible()


def test_removal_cancellation_and_path_identity(page):
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.evaluate("removeRepo(0)")
    assert page.locator(".repo-name").count() == 4
    result = page.evaluate("""async () => {
      let finish;
      const originalFetch = window.fetch;
      const originalConfirm = window.confirm;
      window.fetch = () => new Promise(resolve => { finish = resolve; });
      window.confirm = () => true;
      const removed = repos[1].path;
      const survivor = repos[2].path;
      const request = removeRepo(1);
      repos.splice(0, 1);
      finish({ok: true});
      await request;
      window.fetch = originalFetch;
      window.confirm = originalConfirm;
      return {removed: repos.some(r => r.path === removed), survivor: repos.some(r => r.path === survivor)};
    }""")
    assert result == {"removed": False, "survivor": True}


def test_search_expands_matches_without_overwriting_collapsed_groups(page):
    page.locator('.collection-toggle').click()
    assert not page.locator('#card-1').is_visible()
    page.get_by_role('searchbox').fill('/tools/')
    assert page.locator('#card-1').is_visible()
    assert page.locator('#filter-all').inner_text() == 'All1'
    assert page.locator('#filter-sync').inner_text() == 'Sync needed1'
    page.get_by_role('button', name='Clear search and filters').click()
    assert not page.locator('#card-1').is_visible()
    page.get_by_role('button', name='Changed').click()
    assert page.locator('#card-1').is_visible()


def test_collection_feedback_and_pinned_membership(page):
    page.get_by_role('searchbox').fill('/tools/')
    create_collection(page, 'Tools')
    assert 'Collection saved' in page.locator('#toast').inner_text()
    page.locator('#card-1 summary').click()
    page.locator('#collection-1').select_option(label='Tools')
    page.locator('#card-1 .pin-button').click()
    page.get_by_role('button', name='Clear search and filters').click()
    group = collection(page, 'Tools')
    assert '1 pinned above' in group.locator('.group-count').inner_text()
    assert 'shown in Pinned above' in group.inner_text()


def test_bulk_assignment_includes_explicitly_selected_hidden_matches(page):
    create_collection(page, 'Tools')
    page.get_by_role('button', name='Organize repos', exact=True).click()
    page.get_by_role('searchbox').fill('alpha')
    page.get_by_role('button', name='Select matching').click()
    assert page.locator('#selection-count').inner_text() == '2 selected'
    page.get_by_label('Collection for selected repos').select_option(label='Tools')
    page.get_by_role('searchbox').fill('/tools/')
    assert '1 outside current filter' in page.locator('#selection-count').inner_text()
    page.get_by_role('button', name='Move selected', exact=True).click()
    assignments = page.evaluate('organization.assignments')
    assert assignments[PATHS[0]] == assignments[PATHS[1]]
    assert page.locator('#selection-count').inner_text() == '0 selected'
    page.get_by_role('button', name='Done', exact=True).click()
    assert page.locator('.repo-select').count() == 0


def test_git_metadata_nests_worktrees_and_project_grouping(page):
    page.evaluate("""paths => {
      repos[0]._status.project_id = repos[1]._status.project_id = '/actual/git/common';
      repos[0]._status.project_path = repos[1]._status.project_path = paths[0];
      repos[1]._status.is_worktree = true;
      render();
    }""", PATHS)
    assert page.locator('.project-family .repo-card').count() == 2
    assert 'Worktree of alpha' in page.locator('#card-1').inner_text()
    page.locator('.project-family .collection-toggle').click()
    assert not page.locator('#card-1').is_visible()
    page.get_by_role('searchbox').fill('/tools/')
    assert page.locator('#card-1').is_visible()
    page.locator('#repo-grouping').select_option('project')
    assert page.locator('.project-family').count() == 0
    assert page.locator('#card-1').is_visible()


def test_github_attention_deduplicates_and_preserves_partial_errors(page):
    requests = []

    def github(route):
        requests.append(route.request.url)
        route.fulfill(json={
            'has_github': True, 'repo': 'test/shared', 'repo_url': 'https://github.com/test/shared',
            'checked_at': '2026-01-01T12:00:00Z', 'errors': ['Issues could not be checked.'], 'issues': [],
            'prs': [{'number': 7, 'title': 'Fix checks', 'url': 'https://github.com/test/shared/pull/7',
                     'branch': 'fix', 'ci': {'state': 'fail', 'total': 3, 'passing': 0, 'failing': 1, 'pending': 2},
                     'review_decision': 'CHANGES_REQUESTED', 'mergeable': 'CONFLICTING', 'draft': False}],
        })

    page.route('**/api/github?*', github)
    page.evaluate("""() => {
      repos[0]._status.github_repo = repos[1]._status.github_repo = 'test/shared';
      render();
    }""")
    page.get_by_role('button', name='Check GitHub', exact=True).click()
    page.wait_for_function('!refreshingGithub')
    assert len(requests) == 1
    assert '1 PR with blockers' in page.locator('#attention-heading').inner_text()
    assert '1 incomplete' in page.locator('#attention-heading').inner_text()
    assert '1 failing check' in page.locator('#attention-list').inner_text()
    page.get_by_role('button', name='GitHub attention').click()
    assert page.locator('.repo-card').count() == 2
    page.locator('#card-0 .gh-signal').click()
    playwright.expect(page.get_by_role('tab', name='GitHub')).to_have_attribute('aria-selected', 'true')
    playwright.expect(page.locator('#tab-github')).to_contain_text('Issues unavailable.')
    assert 'No open issues.' not in page.locator('#tab-github').inner_text()
    assert '1 failing · 2 pending' in page.locator('#tab-github').inner_text()
    assert 'Changes requested' in page.locator('#tab-github').inner_text()
    assert 'Merge conflict' in page.locator('#tab-github').inner_text()
    page.get_by_role('button', name='Refresh GitHub', exact=True).click()
    page.wait_for_function('githubTasks.size === 0')
    assert requests[-1].endswith('&refresh=1')


def test_change_expanders_have_truthful_labels_and_keyboard_access(page):
    page.route('**/api/repo?*', lambda route: route.fulfill(json={
        'path': PATHS[0], 'branch': 'main', 'commits': [], 'branches': [],
        'changed_files': [{'path': 'deleted.txt', 'kind': 'deleted', 'staged': False, 'untracked': False}],
    }))
    page.route('**/api/working-diff?*', lambda route: route.fulfill(body='deleted file mode 100644'))
    page.locator('#card-0 .repo-name').click()
    page.get_by_role('tab', name='Changes').click()
    button = page.get_by_role('button', name='deleted.txt deleted', exact=True)
    playwright.expect(button).to_be_visible()
    button.focus()
    page.keyboard.press('Enter')
    playwright.expect(button).to_have_attribute('aria-expanded', 'true')
    assert button.evaluate('el => el === document.activeElement')
    page.get_by_role('tab', name='Changes').focus()
    page.keyboard.press('ArrowRight')
    assert page.get_by_role('tab', name='Branches').get_attribute('aria-selected') == 'true'


def test_home_shortening_guard_is_preserved(page):
    assert page.evaluate("shortHome('/home/test/work/project')") == '~/work/project'


def test_detail_loading_clears_old_counts_and_ignores_late_responses(page):
    result = page.evaluate("""async paths => {
      const originalFetch = window.fetch;
      const waiting = [];
      window.fetch = () => new Promise(resolve => waiting.push(resolve));
      document.getElementById('changes-count').textContent = '(16)';
      const first = showDetail(paths[0]);
      const cleared = document.getElementById('changes-count').textContent === '';
      const second = showDetail(paths[1]);
      const data = path => ({path, branch: 'main', commits: [], branches: [], changed_files: []});
      waiting[1]({status: 200, ok: true, json: async () => data(paths[1])});
      await second;
      waiting[0]({status: 200, ok: true, json: async () => data(paths[0])});
      await first;
      window.fetch = originalFetch;
      return {cleared, path: detailData.path, header: document.getElementById('detail-header').textContent};
    }""", PATHS)
    assert result['cleared']
    assert result['path'] == PATHS[1]
    assert PATHS[1] in result['header']


def test_return_refreshes_stale_local_data_without_enabling_github(page):
    result = page.evaluate("""async () => {
      repos.forEach(r => { r._checkedAt = new Date(Date.now() - 120000).toISOString(); });
      const original = window.fetch;
      const requests = [];
      window.fetch = (...args) => { requests.push(args[0]); return original(...args); };
      await refreshOnReturn();
      await refreshOnReturn();
      window.fetch = original;
      return {requests, enabled:organization.githubEnabled};
    }""")
    assert len(result['requests']) == len(PATHS)
    assert all('/api/repos/status?' in url for url in result['requests'])
    assert not result['enabled']


@pytest.mark.parametrize('guard', ['fresh', 'detail', 'dialog', 'organizing', 'busy', 'hidden'])
def test_return_refresh_does_not_interrupt_or_refresh_fresh_data(page, guard):
    result = page.evaluate("""async guard => {
      repos.forEach(r => { r._checkedAt = new Date(Date.now() - (guard === 'fresh' ? 0 : 120000)).toISOString(); });
      if (guard === 'detail') detailPath = repos[0].path;
      if (guard === 'dialog') document.getElementById('collection-dialog').showModal();
      if (guard === 'organizing') organizing = true;
      if (guard === 'busy') refreshingLocal = true;
      if (guard === 'hidden') Object.defineProperty(document, 'visibilityState', {value:'hidden', configurable:true});
      const original = window.fetch;
      let requests = 0;
      window.fetch = (...args) => { requests++; return original(...args); };
      await refreshOnReturn();
      window.fetch = original;
      return requests;
    }""", guard)
    assert result == 0


@pytest.mark.parametrize('events', [['focus'], ['visibilitychange'], ['focus', 'visibilitychange']])
def test_focus_and_visibility_coalesce_bounded_opted_in_refresh(page, events):
    page.evaluate("""events => {
      organization.githubEnabled = true;
      repos.forEach((r,i) => {
        r._checkedAt = new Date(Date.now() - 120000).toISOString();
        if (!r._status.error) r._status.github_repo = 'demo/project-' + i;
      });
      window.returnProbe = {local:0, github:0, active:0, peak:0};
      const original = window.fetch;
      window.fetch = async url => {
        const probe = window.returnProbe;
        probe.active++; probe.peak = Math.max(probe.peak, probe.active);
        await new Promise(resolve => setTimeout(resolve, 20));
        let response;
        if (url.startsWith('/api/github?')) {
          probe.github++;
          response = {ok:true,json:async () => ({has_github:true,prs:[],issues:[],checked_at:new Date().toISOString()})};
        } else {
          probe.local++;
          const path = new URL(url, location.href).searchParams.get('path');
          response = {ok:true,json:async () => repos.find(r => r.path === path)._status};
        }
        probe.active--;
        return response;
      };
      events.forEach(event => (event === 'focus' ? window : document).dispatchEvent(new Event(event)));
    }""", events)
    page.wait_for_function('returnProbe.local === 4 && returnProbe.github === 3 && !refreshingLocal && !refreshingGithub')
    result = page.evaluate('returnProbe')
    assert result['peak'] <= 3
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    assert page.evaluate('returnProbe.local + returnProbe.github') == 7


def test_pr_truncation_uses_reported_coverage_limit(page):
    page.evaluate("""() => {
      githubData = {has_github:true,repo:'demo/project',repo_url:'https://github.com/demo/project',prs:[],issues:[],errors:[],pr_limit_reached:true,pr_limit:200};
      renderGithub();
    }""")
    assert 'Showing up to 200 open PRs' in page.locator('#tab-github').inner_text()


def test_return_checks_stale_cached_github_and_backs_off_after_failure(page):
    result = page.evaluate("""async () => {
      organization.githubEnabled = true;
      repos.forEach(r => { r._checkedAt = new Date().toISOString(); });
      repos[0]._status.github_repo = 'demo/project';
      repos[0]._github = {has_github:true,prs:[],issues:[],checked_at:new Date(Date.now() - 120000).toISOString()};
      repos[0]._githubCheckedAt = new Date().toISOString();
      const original = window.fetch;
      const requests = [];
      window.fetch = async url => { requests.push(url); throw new Error('offline'); };
      await refreshOnReturn();
      repos[0]._github.checked_at = new Date(Date.now() - 120000).toISOString();
      await refreshOnReturn();
      window.fetch = original;
      return {requests, failed:repos[0]._github.gh_unavailable};
    }""")
    assert len(result['requests']) == 1
    assert result['requests'][0].startswith('/api/github?')
    assert result['failed']
