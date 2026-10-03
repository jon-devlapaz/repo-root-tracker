"""Diagnostic SVG size and repeated warm promotion timings; not a release gate."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from bonsai_review import open_scene


def measure(dashboard):
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for repeat in range(3):
            page=browser.new_page(viewport={'width':1440,'height':900})
            open_scene(page,'crowded',dashboard)
            result=page.evaluate('''async()=>{
              boardNamesVisible=true;renderBoard();
              await new Promise(requestAnimationFrame);
              const bytes=repos.map(r=>bonsaiTree(r.path,BONSAI_FOLIAGE[0]).length);
              const rounds=[];
              for(let round=0;round<6;round++){
                const times=[];
                for(const project of boardProjects){
                  const path=project.worktreePaths.find(p=>!boardScene.targets.some(t=>t.path===p));
                  const start=performance.now();selectBoardRepo(path);
                  await Promise.resolve();times.push(performance.now()-start);
                  await new Promise(requestAnimationFrame);
                }
                if(round)rounds.push(times);
              }
              const ranked=rounds.flat().sort((a,b)=>a-b);
              return {markupBytes:bytes.reduce((a,b)=>a+b,0),trees:bytes.length,
                promotions:ranked.length,median:ranked[Math.floor(ranked.length/2)],
                p95:ranked[Math.ceil(ranked.length*.95)-1],rounds};
            }''')
            results.append(result);page.close()
        browser.close()
    return {'dashboard':str(dashboard),'sha256':hashlib.sha256(dashboard.read_bytes()).hexdigest(),
            'headed':False,'viewport':[1440,900],'notes':'Synthetic25-project fixture;Names on;one warm round discarded;three fresh contexts;five25-promotion rounds per context. Diagnostic only.',
            'results':results}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dashboard',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(measure(args.dashboard),indent=2))
