import pytest

from test_board import PATHS, click_plot, goto_board, page, selected_tile  # noqa: F401


def test_embedded_socratink_fonts_load_offline(page):
    for family in ('Instrument Serif Embedded', 'Inter Embedded'):
        loaded = page.evaluate("""async family => (await document.fonts.load('16px "' + family + '"')).length""", family)
        assert loaded == 1, family
    root = "getComputedStyle(document.documentElement).getPropertyValue("
    assert 'Instrument Serif Embedded' in page.evaluate(root + "'--display')")
    assert 'Inter Embedded' in page.evaluate(root + "'--font')")


def test_the_dashboard_uses_the_socratink_palette_and_type(page):
    look = page.evaluate("""() => { const s = getComputedStyle(document.body), r = getComputedStyle(document.documentElement);
      return {bg: s.backgroundColor, text: s.color, accent: r.getPropertyValue('--accent').trim(),
              title: getComputedStyle(document.querySelector('.overview h2')).fontFamily}; }""")
    assert look['bg'] == 'rgb(16, 15, 15)' and look['accent'] == '#3aa99f'
    assert look['title'].startswith('"Instrument Serif"') or look['title'].startswith('Instrument Serif')


def test_island_is_described_to_screen_readers(page):
    goto_board(page)
    label = page.locator('#board-stage').get_attribute('aria-label')
    assert page.locator('#board-stage').get_attribute('role') == 'group'
    assert 'Workspace: 5 projects, 5 checkouts.' in label and '1 with uncommitted changes' in label


def test_more_contrast_lifts_muted_text_and_borders(page):
    base = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--muted').trim()")
    page.emulate_media(contrast='more')
    boosted = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--muted').trim()")
    assert boosted != base and boosted == '#c4d2ca'


def test_forced_colors_give_buttons_real_borders(page):
    page.emulate_media(forced_colors='active')
    assert page.locator('#local-refresh').evaluate("el => getComputedStyle(el).borderTopWidth") == '1px'


def test_reduced_motion_stills_the_garden_but_keeps_it_usable(page):
    page.emulate_media(reduced_motion='reduce')
    goto_board(page)
    assert page.locator('.bonsai-sway').first.evaluate("el => getComputedStyle(el).animationName") == 'none'
    click_plot(selected_tile(page))
    assert page.evaluate('boardSelectedPath') == PATHS[0]


@pytest.mark.parametrize('width', [390, 768, 1440])
@pytest.mark.parametrize('view', ['list', 'board', 'detail', 'replay'])
def test_every_view_fits_every_width_without_errors(page, width, view):
    errors = []
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.set_viewport_size({'width': width, 'height': 900})
    page.route('**/api/activity?*', lambda route: route.fulfill(json={'days': 30, 'repos': {PATHS[0]: {'2026-09-30': 2}}}))
    page.route('**/api/repo?*', lambda route: route.fulfill(json={'path': PATHS[0], 'branch': 'main', 'commits': [], 'branches': [], 'changed_files': []}))
    if view in ('board', 'replay'):
        goto_board(page)
    if view == 'replay':
        page.get_by_role('button', name='Replay', exact=True).click()
        page.wait_for_selector('#board-replay-controls', state='visible')
    if view == 'detail':
        page.evaluate("location.hash = '#/repo/' + encodeURIComponent(repos[0].path)")
        page.wait_for_selector('#detail-view', state='visible')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert errors == []


def test_touch_devices_get_touch_wording_and_the_pinned_star_is_drawn(page):
    page.evaluate("const real = window.matchMedia.bind(window); window.matchMedia = q => String(q).includes('hover:none') ? {matches: true, addEventListener() {}, removeEventListener() {}} : real(q)")
    goto_board(page)
    page.evaluate('updateBoardCaption(null)')
    assert page.locator('#board-caption').inner_text() == 'Select a tree to identify its repository.'
    page.evaluate("organization.pins = [repos[0].path]; render();")
    assert page.locator('#filter-pinned').inner_text().strip().startswith('Pinned')
    assert page.locator('#filter-pinned').evaluate("el => getComputedStyle(el, '::before').content") != 'none'


def test_the_sun_never_borrows_a_state_colour(page):
    goto_board(page)
    for hour in (7, 13, 18):
        page.evaluate(f'boardHourOverride = {hour}; renderBoard();')
        page.wait_for_function(f'document.getElementById("board-sky").dataset.kind !== ""')
        colour = page.locator('#board-sky').evaluate("el => getComputedStyle(el).backgroundColor")
        assert colour == 'rgb(236, 230, 216)'
