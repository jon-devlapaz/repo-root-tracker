"""Opt-in §8 release gate. Run headed on the recorded reference machine:

RRT_REFERENCE_PERF=1 PYTHONPATH=$PWD/src python3 -m pytest tests/test_board_performance.py -q -s

The ordinary CI timing tests remain unchanged. Every run prints its own evidence;
--junitxml additionally retains it as a testcase property. No runs are pooled.
"""
import importlib.metadata
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
from urllib.parse import unquote

import pytest

from organization_fake import route_organization
from test_board import DASHBOARD, playwright

pytestmark = pytest.mark.skipif(os.environ.get('RRT_REFERENCE_PERF') != '1', reason='§8 requires an active headed browser on the recorded reference machine; set RRT_REFERENCE_PERF=1')


def fixture_data():
    statuses = {}
    for i in range(90):
        main = f'/performance/project-{i:02d}'
        count = 4 if i < 30 else 3 if i < 60 else 2
        for j, path in enumerate([main, *[f'{main}-w{k:02d}' for k in range(count)]]):
            statuses[path] = {'project_id': main + '/.git', 'project_path': main, 'is_worktree': j > 0,
                              'github_repo': f'demo/project-{i:02d}', 'branch': 'main' if not j else f'feature/{j}',
                              'dirty': {'is_clean': (i+j) % 7 != 0, 'modified': 2 if (i+j) % 7 == 0 else 0},
                              'sync': {'has_upstream': True, 'ahead': 2 if (i+j) % 11 == 0 else 0, 'behind': 0},
                              'branches': ['main', f'feature/{j}', 'live'],
                              'stale_branches': [{'name': 'old'}] if (i+j) % 13 == 0 else [],
                              'activity_30d': (i+j) % 18, 'first_commit_date': '2020-01-01'}
    return statuses


def routes(page, statuses, held=False):
    route_organization(page)
    page.route('http://dashboard.test/', lambda route: route.fulfill(content_type='text/html', body=DASHBOARD.read_text().replace('__HOME__', '/home/test', 1)))
    page.route('**/api/repos', lambda route: route.fulfill(json=[{'path': p} for p in statuses]))
    if held:
        page.route('**/api/repos/status?*', lambda route: None)
        page.route('**/api/github?*', lambda route: None)
        page.route('**/api/activity?*', lambda route: None)
    else:
        page.route('**/api/repos/status?*', lambda route: route.fulfill(json=statuses[unquote(route.request.url.split('path=', 1)[1])]))
    identities = {p: {key: s[key] for key in ['project_id', 'project_path', 'is_worktree']} for p, s in statuses.items()}
    page.add_init_script('''(()=>{let waiting=false;const observer=new MutationObserver(()=>{
      if(!waiting && typeof toggleBoardNames==='function' && !boardNamesVisible && document.getElementById('board-names-toggle'))toggleBoardNames();
      if(waiting || !document.querySelector('.board-member'))return;waiting=true;
      const check=()=>{const tile=document.querySelector('.tile'),member=tile?.querySelector('.member-body'),rect=member?.getBoundingClientRect();
        if(!rect?.width || Number(getComputedStyle(tile).opacity)===0){requestAnimationFrame(check);return;}
        requestAnimationFrame(()=>{window.coldPaintMs=performance.now();window.coldGroundDraws=groundDraws;observer.disconnect();});};requestAnimationFrame(check);
      });observer.observe(document,{childList:true,subtree:true});})();''')
    page.add_init_script('localStorage.setItem("repo-root-tracker.project-identities.v1",' + json.dumps(json.dumps({'version': 1, 'entries': identities})) + ');')


@pytest.mark.parametrize('viewport', [{'width': 1440, 'height': 900}, {'width': 390, 'height': 844}], ids=['desktop', 'mobile'])
def test_reference_performance_gate(viewport, record_property):
    statuses = fixture_data()
    assert len(statuses) == 360
    hardware = platform.machine()
    cpu = platform.processor()
    memory = None
    if platform.system() == 'Darwin':
        hardware = subprocess.check_output(['sysctl', '-n', 'hw.model'], text=True).strip()
        cpu = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip()
        memory = int(subprocess.check_output(['sysctl', '-n', 'hw.memsize'], text=True).strip())
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        metadata = {'hardware': hardware, 'cpu': cpu, 'cores': os.cpu_count(), 'memory_bytes': memory,
                    'os': platform.platform(), 'browser': browser.version,
                    'chromium_executable': p.chromium.executable_path, 'playwright': importlib.metadata.version('playwright'),
                    'candidate': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                    'dashboard_sha256': hashlib.sha256(DASHBOARD.read_bytes()).hexdigest(),
                    'fixture_sha256': hashlib.sha256(json.dumps(statuses, sort_keys=True).encode()).hexdigest(),
                    'viewport': viewport, 'dpr': 1, 'headed': True, 'foreground': True,
                    'motion': 'normal', 'names': True, 'throttling': 'none', 'devtools': 'closed'}
        print('RRT_PERFORMANCE_REFERENCE ' + json.dumps(metadata))
        record_property('reference', json.dumps(metadata))
        cold = []
        for i in range(5):
            context = browser.new_context(viewport=viewport, device_scale_factor=1, reduced_motion='no-preference')
            page = context.new_page()
            routes(page, statuses, held=True)
            page.bring_to_front()
            page.goto('http://dashboard.test/#/board', wait_until='domcontentloaded')
            page.wait_for_selector('.board-member')
            page.wait_for_function('window.coldPaintMs>0')
            ms=page.evaluate('coldPaintMs')
            assert page.evaluate('coldGroundDraws') == 0
            cold.append(ms)
            assert page.locator('.tile').count() == 25 and page.locator('.board-member').count() == 100
            context.close()
        print('RRT_PERFORMANCE_COLD ' + json.dumps(cold))
        record_property('coldPaintMs', json.dumps(cold))
        assert all(ms < 1000 for ms in cold), cold
        for run in range(1, 4):
            context = browser.new_context(viewport=viewport, device_scale_factor=1, reduced_motion='no-preference')
            page = context.new_page()
            routes(page, statuses)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.bring_to_front()
            page.goto('http://dashboard.test/#/board')
            page.wait_for_function('boardLayoutReady && !refreshingBoard && repos.length===360 && repos.every(r=>!r._checking)', timeout=30000)
            page.evaluate('''()=>{for(let i=0;i<90;i++){const slug='demo/project-'+String(i).padStart(2,'0');
              acceptGithubSnapshot(slug,1,{has_github:true,repo:slug,prs:[],issues:[],errors:[],checked_at:new Date().toISOString(),
                workflows:{state:i%11===0?'pending':'passing',errors:[],runs:[{current_head:true,status:i%11===0?'in_progress':'completed',conclusion:'success'}]}});}
              renderBoard();}''')
            page.evaluate(Path(__file__).with_name('board_performance.js').read_text())
            evidence = page.evaluate('run=>runBoardReferenceSample(run)', run)
            print('RRT_PERFORMANCE_RUN ' + json.dumps(evidence))
            record_property(f'run{run}', json.dumps(evidence))
            assert errors == []
            assert evidence['plots'] <= 25 and evidence['targets'] <= 100
            assert evidence['measuredPromotions'] == 30 and evidence['panCameraPositions'] > 1
            assert evidence['refresh']['requests'] == 360 and evidence['refresh']['peak'] <= 3
            assert evidence['longestObservedTaskMs'] <= 50, evidence
            for category, samples in evidence['categories'].items():
                assert samples['work']['count'] > 0, category
                assert samples['work']['median'] < 10 and samples['work']['p95'] < 16.7, (category, evidence)
                assert samples['paint']['p95'] <= 50 and samples['paint']['max'] <= 100, (category, evidence)
            context.close()
        browser.close()
