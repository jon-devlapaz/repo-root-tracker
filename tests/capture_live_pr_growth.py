"""Opt-in read-only browser check against a running candidate and real GitHub data."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True)
    parser.add_argument('--repo',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/#/board')
        page.wait_for_function('repos.length>0 && repos.every(r=>r._status && !r._checking)')
        result=page.evaluate('''async path=>{
          const repo=repoByPath.get(path);
          if(!repo)throw Error('Repository not registered');
          await fetchGithub(repo,true);
          renderBoard();selectBoardRepo(path);
          const growth=mergedPrGrowthInfo(repo);
          if(growth.count===null || growth.stale)throw Error('No fresh merged total');
          if(!pixelFamilyForPath(path))throw Error('Target does not use first pixel family');
          return {repository:githubSlugForRepo(repo),...growth,
            worktrees:repos.filter(r=>githubSlugForRepo(r)===githubSlugForRepo(repo)).map(r=>({path:r.path,...mergedPrGrowthInfo(r)}))};
        }''',args.repo)
        page.screenshot(path=str(args.output/'desktop.png'),full_page=True)
        assert page.locator('#board-inspector [data-pixel-family]').count()==1
        assert all(r['count']==result['count'] for r in result['worktrees'])
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(args.output/'mobile-inspector.png'),full_page=True)
        page.evaluate('clearBoardSelection();fitBoardCamera()')
        page.screenshot(path=str(args.output/'mobile.png'),full_page=True)
        assert not errors,errors
        (args.output/'live-check.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));browser.close()
