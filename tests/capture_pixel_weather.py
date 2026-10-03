"""Capture real pixel glyphs at each PR size with stale-branch warnings."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from bonsai_review import DASHBOARD, open_scene


def capture(output, dashboard=DASHBOARD):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1000,'height':400})
        open_scene(page, dashboard=dashboard)
        page.evaluate('''() => {
          const repo=repos.find(r=>pixelFamilyForPath(r.path));
          repo._status.stale_branches=[{name:'old-one'},{name:'old-two'}];
          const cards=[0,6,21,null].map((count,i)=>{
            acceptGithubSnapshot(githubSlugForRepo(repo),100+i,{has_github:true,prs:[],issues:[],
              checked_at:new Date().toISOString(),merged_pr_count:count});
            // Unknown must have no retained successful count.
            if(count===null)githubSnapshotForRepo(repo).mergedGrowth=null;
            return '<section><h2>'+(count===null?'Unknown':count+' merged PRs')+'</h2>'+bonsaiGlyph(repo,{large:true,still:true})+'</section>';
          });
          const panel=document.createElement('main');panel.id='weather-review';
          panel.style.cssText='position:fixed;inset:0;max-width:none;width:100%;margin:0;z-index:9999;background:#161514;display:flex;justify-content:space-around;padding:24px';
          panel.innerHTML='<style>#weather-review h2{font:18px sans-serif}#weather-review svg{width:200px;height:280px}</style>'+cards.join('');
          document.body.append(panel);
        }''')
        page.screenshot(path=str(output/'growth-stages.png'))
        browser.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dashboard',type=Path,default=DASHBOARD)
    args=parser.parse_args()
    capture(args.output,args.dashboard)
