from test_board import PATHS, goto_board, page


def grouped_board(page):
    # The retired family-island fixture becomes two Workspace project pages.
    paths = [*PATHS, *[f'/workspace/pages/p{i:02}' for i in range(23)]]
    page.evaluate('''paths => {
      repos=paths.map(path=>({path,_status:{dirty:{is_clean:true},branch:'main'}}));
      rebuildProjectModel();
      for(const repo of repos)rememberRepoMetadata(repo.path,repo._status);
      rememberRepoMetadata(paths[0],{project_id:'/git/family',project_path:paths[0],is_worktree:false});
      rememberRepoMetadata(paths[1],{project_id:'/git/family',project_path:paths[0],is_worktree:true});
      rebuildProjectModel(); renderBoard();
    }''', paths)
    goto_board(page)
    return paths


def test_only_active_island_is_rendered_and_cycles_with_keyboard(page):
    grouped_board(page)
    assert page.locator('[data-island]').count() == 1
    assert page.locator('.tile').count() == 25
    assert 'Workspace · Page 1 of 2' in page.locator('#board-page-status').inner_text()
    assert page.locator('#board-prev').is_disabled()
    page.locator('#board-next').focus()
    page.keyboard.press('Enter')
    assert page.locator('[data-island]').count() == 1
    assert page.locator('.tile').count() == 2
    assert 'Workspace · Page 2 of 2' in page.locator('#board-page-status').inner_text()
    assert page.locator('#board-next').is_disabled()
    assert page.locator('#board-page-status').evaluate('el => el === document.activeElement')
    page.locator('#board-prev').click()
    assert page.locator('.tile').count() == 25
    assert page.locator('[data-island]').count() == 1


def test_search_can_select_hidden_family_and_camera_refits(page):
    paths = grouped_board(page)
    page.get_by_role('button', name='Zoom in', exact=True).click()
    page.get_by_role('searchbox', name='Search the island').fill('p22')
    page.get_by_role('searchbox', name='Search the island').press('Enter')
    assert page.evaluate('boardSelectedPath') == paths[-1]
    assert page.locator('.tile').count() == 2
    assert page.locator('[data-island]').count() == 1
    assert 'Page 2 of 2' in page.locator('#board-page-status').inner_text()
    page.locator('#board-prev').click()
    assert page.evaluate('boardSelectedPath') is None
    assert page.locator('#board-inspector h3').inner_text() == 'Select a plot'
    assert page.evaluate('boardScene.islands.length') == 1


def test_single_island_has_no_navigation_and_mobile_does_not_overflow(page):
    goto_board(page)
    assert not page.locator('#board-pager').is_visible()
    grouped_board(page)
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#board-next').click()
    assert page.locator('[data-island]').count() == 1
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
