import pytest

from test_board import click_plot, goto_board, page, selected_tile


def test_shared_theme_controls_and_headings_across_views(page):
    styles = """el => {const s=getComputedStyle(el);return {font:s.fontFamily,size:s.fontSize,radius:s.borderRadius,background:s.backgroundColor,color:s.color}}"""
    list_heading = page.locator('.overview h2').evaluate(styles)
    list_control = page.locator('#local-refresh').evaluate(styles)
    goto_board(page)
    assert page.locator('.board-head h2').evaluate(styles) == list_heading
    assert page.locator('#board-refresh').evaluate(styles) == list_control
    click_plot(selected_tile(page))
    assert page.locator('#board-inspector').evaluate('el=>getComputedStyle(el).backgroundColor') == page.locator('.repo-card').first.evaluate('el=>getComputedStyle(el).backgroundColor')
    page.route('**/api/repo?*', lambda route: route.fulfill(status=410, json={'error': 'repo gone from disk'}))
    page.locator('#board-open-details').click()
    page.wait_for_selector('#detail-view', state='visible')
    assert page.locator('#detail-refresh').evaluate(styles) == list_control


def test_theme_text_contrast_and_selection_tokens(page):
    contrast = page.evaluate("""() => {
      const root=getComputedStyle(document.documentElement);
      const rgb=v=>{const e=document.createElement('span');e.style.color=v;document.body.append(e);const c=getComputedStyle(e).color.match(/[\\d.]+/g).slice(0,3).map(Number);e.remove();return c};
      const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
      const value=k=>root.getPropertyValue(k).trim();
      const ratio=(a,b)=>{a=lum(rgb(value(a)));b=lum(rgb(value(b)));return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
      return {ratios:['--text','--body','--muted','--accent','--green','--red-text','--yellow'].flatMap(f=>['--bg','--surface','--surface2'].map(b=>ratio(f,b))),primary:ratio('--on-accent','--accent-dim'),hover:ratio('--on-accent','--accent-hover'),control:ratio('--control-border','--surface2'),scheme:root.colorScheme,accent:value('--accent')};
    }""")
    assert min(contrast['ratios']) >= 4.5
    assert min(contrast['primary'], contrast['hover']) >= 4.5
    assert contrast['control'] >= 3
    assert contrast['scheme'] == 'dark'
    assert contrast['accent'] == '#b9d891'
    goto_board(page)
    click_plot(selected_tile(page))
    assert page.locator('.plot-flag polygon').evaluate('el=>getComputedStyle(el).fill') == page.locator('.plot-name[data-selected="true"]').evaluate('el=>getComputedStyle(el).borderTopColor')


@pytest.mark.parametrize('view', ['list', 'board', 'detail'])
def test_theme_mobile_controls_and_no_overflow(page, view):
    page.set_viewport_size({'width': 390, 'height': 844})
    if view != 'list':
        goto_board(page)
    if view == 'detail':
        page.route('**/api/repo?*', lambda route: route.fulfill(status=410, json={'error': 'repo gone from disk'}))
        click_plot(selected_tile(page))
        page.locator('#board-open-details').click()
        page.wait_for_selector('#detail-view', state='visible')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    controls = page.locator('.btn').evaluate_all("els=>els.filter(e=>e.getClientRects().length).map(e=>e.getBoundingClientRect().height)")
    assert controls and min(controls) >= 44


def test_reduced_motion_applies_to_all_views_and_input_focus_is_visible(page):
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('#local-refresh').evaluate('el=>getComputedStyle(el).transitionDuration') == '0s'
    page.locator('#path-input').focus()
    assert page.locator('#path-input').evaluate('el=>getComputedStyle(el).outlineStyle') != 'none'
    page.locator('#repo-search').focus()
    assert page.locator('#repo-search').evaluate('el=>getComputedStyle(el).outlineStyle') != 'none'
