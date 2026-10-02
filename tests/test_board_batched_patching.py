"""Frame-batched tile patching must never leave what the user is touching behind.

A refresh that changes many tiles patches the first batch immediately and the rest on later frames. These cases
pin the guarantees around that: interaction targets are patched synchronously, hit-testing follows every batch,
replay state survives a patch, and a pan that returns to its start leaves no stale label offset.
"""
from urllib.parse import quote

from test_board import page  # noqa: F401
from test_board_saplings import project_board

COUNTS = [5] * 14   # 14 projects, each a main plus five worktrees: four are drawn, two hidden


def stage_many(page):
    project_board(page, counts=COUNTS)
    assert page.evaluate('boardScene.plots.length') == 14


def dirty_everything(page):
    """Change the markup of every tile at once, as the start of a refresh does."""
    page.evaluate("""() => { repos.forEach((r, i) => { r._status = {...r._status, dirty: {is_clean: false, modified: 1 + (i % 3)}}; }); }""")


def test_selecting_a_hidden_checkout_during_pending_patches_is_drawn_immediately(page):
    stage_many(page)
    result = page.evaluate("""() => {
      const project = boardScene.plots[13].project;
      const hidden = project.worktreePaths.find(p => !boardScene.targets.some(t => t.path === p));
      repos.forEach((r, i) => { r._status = {...r._status, dirty: {is_clean: false, modified: 1 + (i % 3)}}; });
      selectBoardRepo(hidden);
      const button = document.getElementById('board-tile-' + encodeURIComponent(hidden));
      return {hidden, inScene: boardScene.targets.some(t => t.path === hidden), inDom: !!button, pressed: button?.getAttribute('aria-pressed'), pending: boardPendingTiles.size};
    }""")
    assert result['inScene'] and result['inDom'] and result['pressed'] == 'true', result


def test_every_batch_refreshes_hit_records_for_the_svgs_it_patched(page):
    stage_many(page)
    dirty_everything(page)
    assert page.evaluate('() => { renderBoard(); return boardPendingTiles.size; }') > 0   # a real deferral is in flight
    page.wait_for_function('boardPendingTiles.size === 0')                               # and then it fully drains
    stale = page.evaluate("""() => boardScene.targets.filter(t => {
      const button = document.getElementById('board-tile-' + encodeURIComponent(t.path));
      return button && boardHitCache.get(t.path)?.svg !== button.querySelector('svg');
    }).map(t => t.path)""")
    assert stale == []


def test_replay_glow_survives_deferred_patches(page):
    stage_many(page)
    page.evaluate("""() => {
      boardReplay.open = true;
      boardReplay.data = {repos: Object.fromEntries(repos.map(r => [r.path, {[replayKey(0)]: 3}]))};
      boardReplay.ago = 0; applyReplay();
    }""")
    assert page.locator('.tile[data-glow]').count() == 14
    dirty_everything(page)
    page.evaluate('renderBoard()')
    page.wait_for_function('boardPendingTiles.size === 0')
    page.wait_for_function('document.querySelectorAll(".tile[data-glow]").length === 14')


def test_returning_the_camera_to_its_layout_position_clears_the_label_offset(page):
    stage_many(page)
    page.evaluate("boardNamesVisible = true; boardFitPending = false; applyBoardCamera();")
    page.wait_for_function("document.getElementById('board-name-overlay').dataset.zsig")
    result = page.evaluate("""async () => {
      const layer = document.getElementById('board-name-overlay');
      const x = boardCamera.x, y = boardCamera.y;
      boardCamera.x = x - 40; boardCamera.y = y - 10; layoutBoardNames();
      await Promise.resolve();
      const moved = layer.style.transform;
      boardCamera.x = x; boardCamera.y = y; layoutBoardNames();
      await Promise.resolve();
      return {moved, back: layer.style.transform};
    }""")
    assert 'translate(-40px' in result['moved'] and result['back'] == ''
