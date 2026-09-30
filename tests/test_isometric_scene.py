import pytest

from test_board import PATHS, click_plot, goto_board, page, selected_tile


@pytest.mark.parametrize('col,row', [(0,0),(1,0),(0,1),(4,3),(-2,5)])
def test_isometric_projection_round_trip(page, col, row):
    result = page.evaluate('''([col,row]) => {
      const point=boardGridToWorld(col,row);
      return {point,grid:boardWorldToGrid(point.x,point.y),anchor:BOARD_ART_DIRECTION.anchor};
    }''',[col,row])
    assert result['point'] == {'x':(col-row)*60,'y':(col+row)*30}
    assert result['grid'] == {'col':col,'row':row}
    assert result['anchor'] == 'ground-center'


@pytest.mark.parametrize('zoom', [.5,1,2.5])
def test_picking_inverts_pan_and_zoom_and_rejects_water(page, zoom):
    goto_board(page)
    result = page.evaluate('''zoom => {
      boardCamera={x:-117,y:43,zoom};
      const matches=boardScene.plots.map(p => pickBoardPlot(p.x*zoom-117,(p.y-27)*zoom+43));
      return {matches,paths:boardScene.plots.map(p=>p.path),water:pickBoardPlot(-1000,-1000)};
    }''', zoom)
    assert result['matches'] == result['paths']
    assert result['water'] is None


def test_occlusion_uses_anchor_depth_and_visible_sprite_selects_owner(page):
    goto_board(page)
    assert page.evaluate('''() => {
      const plots=boardScene.plots;
      return plots.every((p,i)=>!i||(plots[i-1].row+plots[i-1].col)<=p.row+p.col);
    }''')
    click_plot(selected_tile(page))
    assert page.evaluate('boardSelectedPath') == PATHS[0]
    assert selected_tile(page).get_attribute('aria-pressed') == 'true'


def test_camera_zoom_anchors_pointer_clamps_and_fits(page):
    goto_board(page)
    result = page.evaluate('''() => {
      boardCamera.zoom=2;applyBoardCamera();
      const x=300,y=220,before=boardScreenToWorld(x,y);
      zoomBoardAt(1.1,x,y);
      const after=boardScreenToWorld(x,y);
      const error=Math.hypot(before.x-after.x,before.y-after.y);
      boardCamera.x=10000;boardCamera.y=-10000;boardCamera.zoom=9;
      zoomBoardAt(1,100,100);
      const s=document.getElementById('board-stage');
      return {error,zoom:boardCamera.zoom,x:boardCamera.x,y:boardCamera.y,width:s.clientWidth,height:s.clientHeight,scene:boardScene};
    }''')
    assert result['error'] < 1
    assert result['zoom'] == 2.5
    assert result['x'] <= 0
    assert result['y'] >= min(0,result['height']-result['scene']['height']*result['zoom'])-1
    page.get_by_role('button',name='Fit island',exact=True).click()
    assert page.evaluate('boardCamera.zoom') <= 1.5


def test_search_and_refresh_preserve_camera_and_spatial_coordinates(page):
    goto_board(page)
    page.get_by_role('button',name='Zoom in',exact=True).click()
    before=page.evaluate('({camera:{...boardCamera},plots:boardScene.plots.map(p=>[p.path,p.x,p.y])})')
    page.get_by_role('searchbox',name='Search the island').fill('ahead')
    assert page.locator('.tile:not(.dimmed)').count() == 1
    after=page.evaluate('({camera:{...boardCamera},plots:boardScene.plots.map(p=>[p.path,p.x,p.y])})')
    assert before == after
    page.locator('#board-refresh').click()
    page.wait_for_function('!refreshingBoard')
    assert before == page.evaluate('({camera:{...boardCamera},plots:boardScene.plots.map(p=>[p.path,p.x,p.y])})')


def test_dragging_tree_pans_without_accidentally_selecting_it(page):
    goto_board(page)
    page.evaluate('boardCamera.zoom=2.5;applyBoardCamera();')
    box=selected_tile(page).bounding_box()
    x=box['x']+box['width']/2
    y=box['y']+box['height']*.17
    before=page.evaluate('({...boardCamera})')
    page.mouse.move(x,y)
    page.mouse.down()
    page.mouse.move(x-45,y-25,steps=5)
    page.mouse.up()
    assert page.evaluate('boardSelectedPath') is None
    assert before != page.evaluate('({...boardCamera})')


def test_zoomed_sprite_click_keeps_owner_and_live_caption(page):
    goto_board(page)
    page.get_by_role('button',name='Zoom in',exact=True).click()
    click_plot(selected_tile(page))
    assert page.evaluate('boardSelectedPath') == PATHS[0]
    page.evaluate('repos[0]._status.dirty = {is_clean:true}; renderBoard();')
    assert 'Working tree clean' in page.locator('#board-caption').inner_text()


def test_selected_plot_has_outline_flag_and_locate(page):
    goto_board(page)
    click_plot(selected_tile(page))
    assert page.evaluate('boardSelectedPath') == PATHS[0]
    assert page.locator('.board-select[aria-pressed="true"] .plot-outline').count() == 1
    assert page.locator('.board-select[aria-pressed="true"] .plot-flag').count() == 1
    assert page.locator('#board-inspector').get_by_role('button',name='Locate on island').is_visible()
    page.locator('#board-inspector').get_by_role('button',name='Locate on island').click()
    assert page.locator('.board-select[aria-pressed="true"] .plot-outline').count() == 1


def test_names_toggle_renders_plot_names(page):
    goto_board(page)
    assert page.locator('.plot-name').count() == 0
    page.get_by_role('button',name='Names',exact=True).click()
    assert page.locator('.plot-name').count() == len(PATHS)
    page.get_by_role('button',name='Names',exact=True).click()
    assert page.locator('.plot-name').count() == 0


def test_selected_plot_shows_name_without_toggle(page):
    goto_board(page)
    assert page.locator('.plot-name').count() == 0
    click_plot(selected_tile(page))
    assert page.locator('.plot-name[data-selected="true"]').count() == 1
    assert page.locator('.plot-name[data-selected="true"]').inner_text() == 'dirty'


def test_plot_names_do_not_overlap_and_use_screen_space(page):
    goto_board(page)
    page.get_by_role('button',name='Names',exact=True).click()
    for width in [1280, 390]:
        page.set_viewport_size({'width':width,'height':900})
        page.get_by_role('button',name='Fit island',exact=True).click()
        assert page.locator('.plot-name').count() == len(PATHS)
        result = page.locator('.plot-name').evaluate_all('''els => {
          const rects=els.map(el=>el.getBoundingClientRect());
          const stage=document.getElementById('board-stage').getBoundingClientRect();
          return {overlap:rects.some((a,i)=>rects.slice(i+1).some(b=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)),
            inside:rects.every(a=>a.left>=stage.left&&a.right<=stage.right&&a.top>=stage.top&&a.bottom<=stage.bottom),
            fonts:els.every(el=>parseFloat(getComputedStyle(el).fontSize)>=11)};
        }''')
        assert result == {'overlap':False,'inside':True,'fonts':True}


def test_hover_tip_shows_full_name_above_plot(page):
    goto_board(page)
    target = page.locator('.board-select').nth(1)
    box = target.bounding_box()
    page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']*.58, steps=3)
    page.wait_for_function('!document.getElementById("board-hover-tip").hidden')
    tip = page.locator('#board-hover-tip')
    assert tip.inner_text() == 'ahead \u00b7 feature'
    tip_box = tip.bounding_box()
    assert abs((tip_box['x'] + tip_box['width']/2) - (box['x'] + box['width']/2)) < 80
    assert tip_box['y'] < box['y'] + 30


def test_canopy_click_resolves_to_math_picked_plot(page):
    goto_board(page)
    target = selected_tile(page)
    box = target.bounding_box()
    page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']*.17)
    page.wait_for_function('boardSelectedPath !== null')
    assert page.evaluate('boardSelectedPath') == PATHS[0]


def test_caption_labels_hover_and_selection(page):
    goto_board(page)
    click_plot(selected_tile(page))
    assert 'Selected' in page.locator('#board-caption').inner_text()
    page.locator('.board-select').nth(1).hover()
    assert 'Hover preview' in page.locator('#board-caption').inner_text()
    click_plot(selected_tile(page))
    assert 'Selected' in page.locator('#board-caption').inner_text()
