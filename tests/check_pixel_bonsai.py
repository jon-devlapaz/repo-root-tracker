"""Capture the one-tree trial and check selection and the dirty-state fallback."""
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
            assert tile.locator('[data-pixel-trial]').count() == 1
            tile.click()
            assert tile.get_attribute('aria-pressed') == 'true'
            page.screenshot(path=str(output / f'board-{width}.png'), full_page=True)
            tile.screenshot(path=str(output / f'tree-{width}.png'))
            # A change in local state must remove gold artwork immediately.
            page.evaluate('''path => {
                repoByPath.get(path)._status.dirty = {is_clean:false, modified:1};
                renderBoard();
            }''', TARGET)
            assert tile.locator('[data-pixel-trial]').count() == 0
            page.close()
        browser.close()
        assert not errors, errors
    (output / 'checks.json').write_text(json.dumps({
        'widths': [1440, 390], 'selection': 'passed',
        'dirty_fallback': 'passed', 'page_errors': errors,
        'scope': 'One synthetic clean tree. No production or performance approval.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    check(parser.parse_args().output)
