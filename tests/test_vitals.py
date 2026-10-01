import pytest

from test_board import PATHS, click_plot, goto_board, page, selected_tile


def layout_sig(page, i=0):
    return page.evaluate("""i => { const L = bonsaiLayout(repos[i].path); return JSON.stringify([L.strokes.map(s => s.d), L.pads.map(p => p.body), L.limbs]); }""", i)


def test_unknown_history_reproduces_the_plain_tree(page):
    assert page.evaluate("bonsaiVitalsOf(repos[0].path).key") == '1,1,0'
    assert page.evaluate("bonsaiLayout(repos[0].path).limbs.length") == 0


def test_age_sets_girth_and_activity_sets_fullness(page):
    plain = layout_sig(page)
    page.evaluate("""() => { repos[0]._status.first_commit_date = new Date(Date.now() - 5 * 365 * 864e5).toISOString(); repos[0]._status.activity_30d = 12; }""")
    old_busy = layout_sig(page)
    page.evaluate("""() => { repos[0]._status.first_commit_date = new Date(Date.now() - 10 * 864e5).toISOString(); repos[0]._status.activity_30d = 0; }""")
    young_quiet = layout_sig(page)
    assert len({plain, old_busy, young_quiet}) == 3
    # the same vitals always draw the same tree
    page.evaluate("""() => { repos[0]._status.first_commit_date = new Date(Date.now() - 5 * 365 * 864e5).toISOString(); repos[0]._status.activity_30d = 12; }""")
    assert layout_sig(page) == old_busy


def test_live_branches_become_limbs_and_stale_ones_do_not(page):
    page.evaluate("""() => { const s = repos[0]._status; s.branches = [s.branch, 'feature/a', 'feature/b', 'old']; s.stale_branches = [{name: 'old'}]; }""")
    assert page.evaluate("bonsaiLayout(repos[0].path).limbs.length") == 2
    page.evaluate("""() => { const s = repos[0]._status; s.branches = [s.branch, 'a', 'b', 'c', 'd', 'e', 'f']; s.stale_branches = []; }""")
    assert page.evaluate("bonsaiLayout(repos[0].path).limbs.length") == 4  # capped


def test_health_never_changes_the_tree_but_history_does(page):
    before = layout_sig(page)
    page.evaluate("repos[0]._status.dirty = {is_clean: true}; repos[0]._status.sync = {has_upstream: true, ahead: 5, behind: 2}; repos[0]._status.stale_branches = [{name: 'x'}];")
    assert layout_sig(page) == before


def test_board_draws_limbs_inside_the_tree_variant_and_inspector_shows_vitals(page):
    goto_board(page)
    page.evaluate("""() => { const s = repos[0]._status; s.branches = [s.branch, 'feature/a']; s.commit_count = 1204; s.activity_30d = 14; s.first_commit_date = new Date(Date.now() - 3 * 365 * 864e5).toISOString(); renderBoard(); }""")
    assert selected_tile(page).locator('[data-tree-variant] path[stroke-linecap="round"]').count() >= 1
    click_plot(selected_tile(page))
    text = page.locator('#board-inspector .inspector-vitals').inner_text()
    assert text.replace('\u00a0', ' ') == '3 years · 1,204 commits · 14 this month · 2 branches'
