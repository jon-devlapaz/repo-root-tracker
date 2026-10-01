from urllib.parse import quote

from test_board import PATHS, click_plot, goto_board, page, selected_tile


def family_fixture(page):
    goto_board(page)
    page.evaluate('''() => {
      for(const r of repos.slice(0,2)) {
        r._status.project_id='shared';r._status.project_path=repos[0].path;
        r._status.github_repo='demo/shared';
        r._github={has_github:true,repo:'demo/shared',prs:[{number:10,title:'Fix checks',url:'https://github.com/demo/shared/pull/10',ci:{state:'fail',failing:3},mergeable:'CONFLICTING'}],issues:[]};
      }
      repos[1]._status.is_worktree=true;
      repos.forEach(r=>rememberRepoMetadata(r.path,r._status)); rebuildProjectModel();
      renderBoard();
    }''')


def test_shared_pr_badge_is_once_per_family_and_inspector_has_actions(page):
    family_fixture(page)
    assert page.locator('[data-family-gh]').count() == 1
    assert page.locator('.tile[data-project="git:shared"] [data-repo-gh]').count() == 0
    assert page.evaluate('boardFamilyGithub(boardProjects[0]).blocked') == 1
    page.evaluate('selectBoardRepo(repos[1].path)')
    panel = page.locator('#board-inspector')
    assert 'Project-wide GitHub' in panel.inner_text()
    assert '3 failing checks' in panel.inner_text()
    assert 'Merge conflict' in panel.inner_text()
    assert panel.locator('.board-pr-item a').get_attribute('href') == 'https://github.com/demo/shared/pull/10'
    assert page.locator('[data-island]').count() == 1
    assert page.locator('[data-island] [data-island]').count() == 0


def test_changes_link_and_close_restore_plot_focus(page):
    goto_board(page)
    click_plot(selected_tile(page))
    assert page.locator('#board-open-changes').get_attribute('href') == '#/repo/' + quote(PATHS[0], safe='') + '?tab=changes'
    page.route('**/api/repo?*', lambda route: route.fulfill(status=410, json={'error':'gone'}))
    page.locator('#board-open-changes').click()
    page.wait_for_function("activeTab === 'changes'")
    page.locator('#back-btn').click()
    page.wait_for_function('!refreshingBoard')
    page.get_by_role('button', name='Close panel', exact=True).click()
    assert page.evaluate('boardSelectedPath') is None
    assert selected_tile(page).evaluate('el => el === document.activeElement')


def test_unchecked_and_incomplete_are_not_all_clear(page):
    family_fixture(page)
    page.evaluate('''() => {
      repos[0]._github={has_github:true,repo:'demo/shared',prs:[],issues:[],errors:['Pull requests unavailable']};
      repos[1]._github=repos[0]._github;
      selectBoardRepo(repos[1].path);
    }''')
    assert 'GitHub incomplete' in page.locator('#board-inspector').inner_text()
    assert 'No known PR blockers' not in page.locator('#board-inspector').inner_text()


def test_names_dense_scene_remain_readable_and_separate(page):
    family_fixture(page)
    page.get_by_role('button',name='Names',exact=True).click()
    for width in [1400, 390]:
        page.set_viewport_size({'width':width,'height':900})
        page.get_by_role('button',name='Fit island',exact=True).click()
        assert page.locator('.plot-name').count() == 4
        assert page.locator('.plot-name').evaluate_all('''els => {
          const r=els.map(el=>el.getBoundingClientRect());
          return !r.some((a,i)=>r.slice(i+1).some(b=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top));
        }''')


def test_tree_variants_are_deterministic_and_independent_of_git_health(page):
    goto_board(page)
    appearance = '''els => els.map(el => ({variant:el.dataset.treeVariant,scale:el.getAttribute('transform'),
      geometry:[...el.querySelectorAll('path,circle')].map(shape => ({type:shape.tagName,
        attributes:['d','cx','cy','r','fill'].map(name=>shape.getAttribute(name))}))}))'''
    before=page.locator('[data-tree-variant]').evaluate_all(appearance)
    assert len(before) == len(PATHS)
    page.evaluate('''() => { repos.forEach(r=>r._status.dirty={is_clean:true});renderBoard(); }''')
    assert before == page.locator('[data-tree-variant]').evaluate_all(appearance)
