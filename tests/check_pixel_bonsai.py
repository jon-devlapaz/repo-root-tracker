"""Capture the family trial and verify its state combinations and transitions."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright
from bonsai_review import DASHBOARD, open_scene
from pixel_bonsai_preview import TARGET, pixel_dashboard


def check(output):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as temp, sync_playwright() as p:
        dashboard = Path(temp) / 'dashboard.html'
        dashboard.write_text(pixel_dashboard(DASHBOARD.read_text()))
        browser = p.chromium.launch()
        errors = []
        for width in [1440, 390]:
            page = browser.new_page(viewport={'width': width, 'height': 900})
            page.on('pageerror', lambda error: errors.append(str(error)))
            open_scene(page, dashboard=dashboard)
            tile = page.locator(f'button.board-member[data-path="{TARGET}"]')
            assert tile.locator('[data-pixel-family]').count() == 1
            tile.click()
            assert tile.get_attribute('aria-pressed') == 'true'
            page.screenshot(path=str(output / f'board-{width}.png'), full_page=True)
            tile.screenshot(path=str(output / f'tree-{width}.png'))
            # A local change switches foliage color without changing growth.
            before = tile.locator("[data-pixel-family]").get_attribute("data-growth")
            page.evaluate('''path => {
                repoByPath.get(path)._status.dirty = {is_clean:false, modified:1};
                renderBoard();
            }''', TARGET)
            assert tile.locator('[data-pixel-family]').get_attribute('data-pixel-color') != 'gold'
            assert tile.locator('[data-pixel-family]').get_attribute('data-growth') == before
            page.evaluate('showPixelFamily()')
            page.locator('#pixel-family-review').screenshot(path=str(output / f'family-{width}.png'))
            page.locator('#pixel-family-close').click()
            if width == 1440:
                page.evaluate("location.hash='#/list'")
                page.wait_for_selector('#list-view .repo-card')
                assert page.locator('#list-view [data-pixel-family]').count() >= 1
                page.screenshot(path=str(output/'list.png'),full_page=True)
                page.evaluate("path=>location.hash='#/repo/'+encodeURIComponent(path)", TARGET)
                page.wait_for_selector('#detail-header .detail-sprite')
                assert page.locator('#detail-header [data-pixel-family]').count() == 1
                page.screenshot(path=str(output/'detail.png'),full_page=True)
            page.close()
        page=browser.new_page(viewport={'width':1440,'height':1100})
        open_scene(page,dashboard=dashboard)
        combinations=page.evaluate("""() => {
            const cases=[[0,'seedling'],[5,'seedling'],[6,'growing'],[20,'growing'],[21,'mature'],[500,'mature'],[null,'unknown'],[undefined,'unknown'],[-1,'unknown'],[1.5,'unknown'],['12','unknown']];
            let total=0;
            for(const [count,stage] of cases)for(const palette of [BONSAI_GOLD,...BONSAI_FOLIAGE]){
              const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
              svg.innerHTML=pixelFamilyTree(palette,count);
              if(svg.querySelector('[data-pixel-family]').dataset.growth!==stage)throw Error('Wrong stage');
              if(svg.querySelector('[data-pixel-family]').dataset.pixelColor==='gold' !== (palette===BONSAI_GOLD))throw Error('Wrong color');
              total++;
            }
            const path='/review/team-00/cedar',repo=repoByPath.get(path);
            const original=bonsaiTree(path,BONSAI_GOLD);
            repo._status.first_commit_date='2026-10-03';repo._status.activity_30d=0;repo._status.branches=[];
            if(bonsaiTree(path,BONSAI_GOLD)!==original)throw Error('Time or activity changed growth');
            PIXEL_SAMPLE_MERGES.set(path,30);
            if(!bonsaiTree(path,BONSAI_GOLD).includes('data-growth="mature"'))throw Error('Cached old size');
            PIXEL_SAMPLE_MERGES.delete(path);
            if(!bonsaiTree(path,BONSAI_GOLD).includes('data-growth="unknown"'))throw Error('Unknown became zero');
            return total;
        }""")
        page.evaluate('showPixelFamily()')
        sizes=page.locator('#pixel-family-review section').first.locator('[data-growth-body]').evaluate_all('nodes=>nodes.map(n=>n.getBoundingClientRect().height)')
        assert sizes[2] > sizes[0]*2.3 and sizes[1] > sizes[0]*1.6, sizes
        gallery=page.evaluate("""() => document.querySelector('svg:has(#pixel-trunk)').outerHTML+
            '<main>'+document.getElementById('pixel-family-review').innerHTML+'</main>'""")
        page.set_content('<style>body{margin:0;background:#161514;color:#ded8ca;font:16px system-ui}main{padding:28px}h1,h2{font-weight:500}button{display:none}</style>'+gallery)
        page.screenshot(path=str(output/'family-all.png'),full_page=True)
        page.close()
        browser.close()
        assert not errors, errors
    (output / 'checks.json').write_text(json.dumps({
        'widths': [1440, 390], 'selection': 'passed',
        'color_transition': 'passed', 'combinations': combinations, 'age_and_activity_independence': 'passed', 'count_refresh': 'passed', 'page_errors': errors,
        'scope': 'Three PR growth stages on synthetic cedar main and worktree. No production or performance approval.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    check(parser.parse_args().output)
