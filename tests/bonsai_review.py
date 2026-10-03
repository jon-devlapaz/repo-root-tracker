"""Reproducible, disposable browser scenes for the sculptural bonsai review.

Run: PYTHONPATH=src python tests/bonsai_review.py --output DIR [--dashboard FILE]
No server or tracker data is used; HTTP responses stay inside the browser context.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import unquote
from playwright.sync_api import sync_playwright
from organization_fake import route_organization

DASHBOARD = Path(__file__).parents[1] / 'src/repo_root_tracker/dashboard.html'


def fixture_data(case='quiet'):
    data = {}
    for i in range(25 if case == 'crowded' else 8 if case == 'attention' else 4):
        name = ['cedar', 'willow', 'juniper', 'maple'][i % 4]
        if i == 2:
            name = 'a-very-long-project-name-with-a-complete-readable-identity'
        main = f'/review/team-{i:02d}/{name}'
        for j in range(5 if case == 'crowded' else 2):
            path = main if not j else f'{main}-worktree-{j}'
            dirty = j == 1 or (case == 'attention' and i % 4 == 1)
            data[path] = dict(project_id=main+'/.git', project_path=main, is_worktree=j>0,
                branch='main' if not j else 'feature/a-long-worktree-branch-name',
                dirty={'is_clean': not dirty, 'modified': 2 if dirty else 0},
                sync={'has_upstream': True, 'ahead': 2 if case == 'attention' and i % 4 == 2 else 0, 'behind': 0},
                stale_branches=[], branches=['main', 'develop'], activity_30d=8,
                first_commit_date='2020-01-01', github_repo=f'review/project-{i}',
                last_commit={'date':'2026-10-02T12:00:00Z'})
    return data


def open_scene(page, case='quiet', dashboard=DASHBOARD):
    data = fixture_data(case)
    route_organization(page)
    page.route('http://dashboard.test/', lambda r: r.fulfill(content_type='text/html', body=dashboard.read_text().replace('__HOME__', '/review', 1)))
    page.route('**/api/repos', lambda r: r.fulfill(json=[{'path':p} for p in data]))
    page.route('**/api/repos/status?*', lambda r: r.fulfill(json=data[unquote(r.request.url.split('path=',1)[1])]))
    page.route('**/api/repo?*', lambda r: r.fulfill(json={'path':unquote(r.request.url.split('path=',1)[1]),'branch':'main','commits':[],'branches':[],'changed_files':[]}))
    page.route('**/api/github?*', lambda r: r.fulfill(json={'has_github':False}))
    page.route('**/api/activity?*', lambda r: r.fulfill(json=[]))
    page.goto('http://dashboard.test/#/board')
    page.wait_for_function('boardLayoutReady && !refreshingBoard && repos.every(r=>r._status && !r._checking)')
    page.evaluate("""caseName=>{ if(caseName==='attention')for(let i=0;i<8;i++){
      if(i%4===0)continue;
      acceptGithubSnapshot('review/project-'+i,1,{has_github:true,repo:'review/project-'+i,prs:[],issues:[],
        errors:i%4===3?['GitHub unavailable']:[],checked_at:new Date().toISOString(),
        workflows:{state:i%4===2?'failing':'passing',errors:[],runs:[{current_head:true,status:'completed',conclusion:i%4===2?'failure':'success',name:'CI',url:'https://example.test/workflow'}]}});
      }renderBoard();} """, case)
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_timeout(500)
    return data


def specimens(page):
    page.evaluate("""()=>{
      const paths=BONSAI_STYLES.map((style,n)=>{let i=0;while(bonsaiSeed('/specimen/'+i)%8!==n)i++;return '/specimen/'+i;});
      document.body.innerHTML='<main id="specimens" style="padding:32px;display:grid;grid-template-columns:repeat(4,220px);gap:28px;background:#161514;color:#ddd8ce">'+paths.map((p,i)=>
        '<section><h2 style="font:18px Georgia">'+BONSAI_STYLES[i]+'</h2><svg width="220" height="200" viewBox="-45 -90 90 110">'+bonsaiTree(p,{...BONSAI_FOLIAGE[0],...BONSAI_GOLD})+'</svg><div style="display:flex;align-items:end;gap:24px"><svg width="80" height="110" viewBox="-40 -85 80 110">'+bonsaiTree(p,{...BONSAI_FOLIAGE[0],...BONSAI_GOLD})+'</svg><svg width="40" height="55" viewBox="-40 -85 80 110">'+bonsaiTree(p,BONSAI_FOLIAGE[0])+'</svg></div><p style="font:12px sans-serif">Detail · board · worktree</p></section>').join('')+'</main>';
    }""")


def capture(output, dashboard=DASHBOARD):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for case in ['quiet','crowded','attention']:
            for width,height in [(390,844),(768,900),(1440,900)]:
                page=browser.new_page(viewport={'width':width,'height':height})
                open_scene(page,case,dashboard)
                page.screenshot(path=str(output/f'{case}-{width}.png'),full_page=True)
                if not page.evaluate('boardNamesVisible'):
                    page.locator('#board-names-toggle').click()
                page.screenshot(path=str(output/f'{case}-{width}-names.png'),full_page=True)
                if case=='attention' and width==1440:
                    for j in [0,1]:
                        page.evaluate('j=>selectBoardRepo(repos[j].path)',j)
                        page.screenshot(path=str(output/f'attention-selected-{j}.png'),full_page=True)
                    page.emulate_media(contrast='more')
                    page.screenshot(path=str(output/'attention-contrast.png'),full_page=True)
                if case=='quiet' and width==1440:
                    page.evaluate("location.hash='#/list'")
                    page.wait_for_selector('#list-view .repo-card')
                    page.screenshot(path=str(output/'list.png'),full_page=True)
                    page.evaluate("location.hash='#/repo/'+encodeURIComponent(repos[0].path)")
                    page.wait_for_selector('#detail-header .detail-sprite')
                    page.screenshot(path=str(output/'detail.png'),full_page=True)
                page.close()
        page=browser.new_page(viewport={'width':1040,'height':900})
        open_scene(page,dashboard=dashboard)
        specimens(page)
        page.screenshot(path=str(output/'specimens.png'),full_page=True)
        browser.close()
    (output/'fixture.json').write_text(json.dumps({c:fixture_data(c) for c in ['quiet','crowded','attention']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dashboard',type=Path,default=DASHBOARD)
    args=parser.parse_args()
    capture(args.output,args.dashboard)
