import pytest

from test_board import PATHS, goto_board, page
from test_board_finish import family_fixture


@pytest.mark.parametrize('state,tone', [
    ('clean', 'clean'), ('dirty', 'changed'), ('conflict', 'blocked'),
    ('sync', 'sync'), ('gone', 'unavailable'), ('error', 'unavailable'),
    ('unknown', 'unknown'), ('stale', 'stale'), ('github-blocked', 'blocked'),
    ('github-incomplete', 'unavailable'), ('github-unchecked', 'clean'),
])
def test_attention_tone_matches_list_plot_and_inspector(page, state, tone):
    page.evaluate("""state => {
      const r=repos[0];r._status={branch:'main',dirty:{is_clean:true},sync:{has_upstream:true,ahead:0,behind:0},github_repo:'qa/demo'};delete r._github;githubBySlug.clear();githubIdentityByPath.clear();
      if(state==='dirty')r._status.dirty={is_clean:false,modified:2,untracked:1};
      if(state==='conflict')r._status.dirty={is_clean:false,kinds:{conflicted:1},modified:1};
      if(state==='sync')r._status.sync={has_upstream:true,ahead:2,behind:1};
      if(state==='gone')r._status={error:true,gone:true};
      if(state==='error')r._status={error:true};
      if(state==='unknown')r._status={branch:'main'};
      if(state==='stale')r._status.stale_branches=[{name:'old'}];
      if(state==='github-blocked')r._github={has_github:true,repo:'qa/demo',prs:[{number:1,title:'Failing CI',url:'https://github.com/qa/demo/pull/1',ci:{state:'fail',failing:1}}]};
      if(state==='github-incomplete')r._github={has_github:true,repo:'qa/demo',prs:[],errors:['Could not check PRs']};
      if(r._github)acceptGithubSnapshot('qa/demo',1,r._github);render();
    }""", state)
    card = page.locator('#card-0')
    assert card.get_attribute('data-tone') == tone
    if state == 'conflict':
        assert 'Local conflict' in card.inner_text()
        assert card.locator('.repo-label').first.get_attribute('data-tone') == 'blocked'
    if state == 'dirty':
        assert '2 modified · 1 untracked' in card.inner_text()
    status = page.evaluate('repos[0]._status')
    code = 410 if state == 'gone' else 503 if state == 'error' else 200
    page.route('**/api/repos/status?path=%2Fworkspace%2Frepos%2Fdirty', lambda route: route.fulfill(status=code, json=status))
    goto_board(page)
    plot = page.locator(f'.board-select[data-path="{PATHS[0]}"]')
    assert plot.locator('.plot-number').get_attribute('data-tone') == tone
    page.evaluate('selectBoardRepo(repos[0].path)')
    assert page.locator('#board-inspector').get_attribute('data-tone') == tone
    assert page.locator('.plot-flag polygon').evaluate('e=>getComputedStyle(e).fill') == page.locator('.plot-name[data-selected="true"]').evaluate('e=>getComputedStyle(e).borderTopColor')
    if tone in ('changed', 'blocked', 'sync', 'unavailable', 'stale'):
        assert plot.locator('.status-ring').count() == 1
    else:
        assert plot.locator('.status-ring').count() == 0
    page.get_by_role('button', name='Close panel', exact=True).click()
    assert page.locator('#board-inspector').get_attribute('data-tone') is None


def test_dirty_is_amber_conflict_is_red_and_selection_is_independent(page):
    goto_board(page)
    page.evaluate("""() => {
      repos[0]._status.dirty={is_clean:false,modified:2};
      repos[1]._status.dirty={is_clean:false,kinds:{conflicted:1}};
      repos[2]._status={error:true,gone:true};
      renderBoard();selectBoardRepo(repos[0].path);
    }""")
    color = lambda i: page.locator(f'.board-select[data-path="{PATHS[i]}"] .plot-number circle').evaluate('e=>getComputedStyle(e).fill')
    assert color(0) != color(1)
    assert color(0) != color(2)
    assert page.locator('.plot-flag polygon').evaluate('e=>getComputedStyle(e).fill') != color(0)
    page.locator('#board-attention').check()
    assert page.locator(f'.tile[data-path="{PATHS[0]}"]').get_attribute('class') == 'tile dimmed'
    assert 'dimmed' not in page.locator(f'.tile[data-path="{PATHS[1]}"]').get_attribute('class')


def test_family_blocker_colors_inspector_but_not_clean_sibling_local_summary(page):
    family_fixture(page)
    page.evaluate("""() => {
      repos[1]._status.dirty={is_clean:true};repos[1]._status.sync={has_upstream:true,ahead:0,behind:0};
      repos[1]._status.github_repo='qa/unchecked';delete repos[1]._github;
      selectBoardRepo(repos[1].path);
    }""")
    assert page.locator('#board-inspector').get_attribute('data-tone') == 'blocked'
    assert page.locator('.inspector-local').get_attribute('data-tone') == 'clean'
    assert page.locator('.board-family-gh').get_attribute('data-tone') == 'blocked'
    assert 'unchecked' in page.locator('.board-family-gh').inner_text()
    assert page.locator('[data-family-gh]').count() == 1


def test_filters_have_semantic_accents_without_changing_membership(page):
    for key, tone in [('changed', 'changed'), ('sync', 'sync'), ('attention', 'blocked'), ('unavailable', 'unavailable')]:
        button=page.locator('#filter-'+key)
        assert button.get_attribute('data-tone') == tone
        button.click()
        assert button.get_attribute('aria-pressed') == 'true'
    assert page.locator('.repo-card').count() == 0


def test_attention_pill_text_and_number_marker_contrast(page):
    ratios=page.evaluate("""() => {
      const root=getComputedStyle(document.documentElement);
      const rgb=s=>s.match(/[\\d.]+/g).slice(0,3).map(Number);
      const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
      const ratio=(a,b)=>{a=lum(a);b=lum(b);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
      return ['changed','blocked','sync','unavailable'].map(tone=>{
        const host=document.createElement('div');host.style.background='var(--surface)';
        const pill=document.createElement('span');pill.className='attention-pill';pill.dataset.tone=tone;host.append(pill);document.body.append(host);
        const s=getComputedStyle(pill),surface=rgb(getComputedStyle(host).backgroundColor),fg=rgb(s.color),bg=rgb(s.backgroundColor);
        const alpha=Number(s.backgroundColor.match(/[\\d.]+/g)[3]??1),mixed=bg.map((v,i)=>v*alpha+surface[i]*(1-alpha));
        const marker=document.createElement('span');marker.style.color=s.getPropertyValue('--signal-fill');host.append(marker);
        const fill=rgb(getComputedStyle(marker).color);host.remove();return [ratio(fg,mixed),ratio([255,255,255],fill)];
      }).flat();
    }""")
    assert min(ratios) >= 4.5
