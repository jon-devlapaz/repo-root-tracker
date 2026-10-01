from test_board import PATHS, goto_board, page  # noqa: F401


def settled_draws(page):
    """Wait until the ground has stopped repainting (a slow runner repaints late), then return the draw count."""
    page.wait_for_function('groundDraws >= 1')
    page.wait_for_function('''() => new Promise(resolve => {
      let last = groundDraws, quiet = 0;
      const t = setInterval(() => { if (groundDraws === last) quiet++; else { quiet = 0; last = groundDraws; }
        if (quiet >= 4) { clearInterval(t); resolve(true); } }, 150);
    })''', timeout=20000)
    return page.evaluate('groundDraws')


def test_ground_is_painted_not_blank(page):
    goto_board(page)
    page.wait_for_function('groundDraws >= 1')
    stats = page.evaluate("""() => {
      const c = document.getElementById('board-ground'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let opaque = 0; const seen = new Set();
      for (let i = 0; i < d.length; i += 4 * 97) { if (d[i + 3] > 200) { opaque++; seen.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2]); } }
      return {w: c.width, h: c.height, opaque, colours: seen.size};
    }""")
    assert stats['w'] > 800 and stats['opaque'] > 200 and stats['colours'] > 8


def test_light_follows_the_hour(page):
    r = page.evaluate("""() => ({dawn: skyAt(7), noon: skyAt(13), dusk: skyAt(18), night: skyAt(23)})""")
    assert r['dawn']['x'] > 0 > r['dusk']['x']             # the light crosses the garden from right to left
    assert r['noon']['elev'] > r['dawn']['elev']           # high at noon, low at the edges of the day
    assert r['night']['kind'] == 'night' and r['dawn']['kind'] == 'dawn' and r['noon']['kind'] == 'day'
    assert r['dawn']['tint'] != r['night']['tint']


def test_each_tree_casts_a_shadow_and_the_hour_changes_the_ground(page):
    goto_board(page)
    page.evaluate('boardHourOverride = 23; renderBoard();')
    page.wait_for_function('groundCache.sig !== "" && groundCache.shadows > 0')
    night = page.evaluate('({shadows: groundCache.shadows, sig: groundCache.sig})')
    assert night['shadows'] == len(PATHS)
    page.evaluate('boardHourOverride = 7; renderBoard();')
    page.wait_for_function('groundCache.sig !== ' + repr(night['sig']))   # repaints once things settle
    assert page.locator('#board-sky').get_attribute('data-kind') == 'dawn'


def test_redraw_is_cached_until_something_the_ground_shows_changes(page):
    goto_board(page)
    before = settled_draws(page)
    page.evaluate('renderBoard(); renderBoard(); renderBoard();')
    assert page.evaluate('groundDraws') == before
    page.evaluate("repos[3]._status.dirty = {is_clean: false, modified: 1}; renderBoard();")
    page.wait_for_function(f'groundDraws === {before + 1}')   # a disturbed pot breaks its rings


def test_drawing_the_ground_is_fast_even_with_a_full_island(page):
    goto_board(page)
    ms = page.evaluate("""() => { const g = boardScene.islands[0], t = performance.now(); drawGround(g, 2, skyAt(23)); return performance.now() - t; }""")
    assert ms < 250


def test_rechecking_a_repo_does_not_repaint_the_bed(page):
    goto_board(page)
    before = settled_draws(page)
    page.evaluate("repos[0]._boardQueued = true; renderBoard(); repos[0]._boardQueued = false; renderBoard();")
    assert settled_draws(page) == before


def test_numbers_appear_on_the_state_discs_only_when_asked_for(page):
    goto_board(page)
    num = page.locator('.board-select').nth(1).locator('.plot-number text')
    assert num.evaluate("el => getComputedStyle(el).opacity") == '0'
    page.get_by_role('button', name='Names', exact=True).click()
    assert page.locator('.board-select').nth(1).locator('.plot-number text').evaluate("el => getComputedStyle(el).opacity") == '1'


def test_camera_tools_float_over_the_stage_so_the_garden_keeps_the_space(page):
    goto_board(page)
    box = page.evaluate("""() => { const t = document.querySelector('.board-camera-tools').getBoundingClientRect(), s = document.getElementById('board-stage').getBoundingClientRect(); return {toolsTop: t.top, toolsBottom: t.bottom, stageTop: s.top}; }""")
    # the tools overlay their own band above the stage (they add no row of their own and never sit on the garden)
    assert box['toolsBottom'] <= box['stageTop'] + 8 and box['stageTop'] - box['toolsTop'] <= 60
