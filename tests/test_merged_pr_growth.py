from pathlib import Path
from unittest.mock import patch
import pytest
from repo_root_tracker import github


@pytest.mark.parametrize('response,expected', [([0],0),([3201],3201),([True],None),([-1],None),(['8'],None),([1.5],None),([],None),(None,None),([3,4],None)])
def test_merged_count_validation(response, expected):
    with patch.object(github, '_gh', return_value=response) as request:
        assert github._merged_pr_count('acme/widget',Path('.')) == expected
    args=request.call_args.args
    assert 'graphql' in args
    assert any('states:MERGED' in arg and 'totalCount' in arg for arg in args)
    assert 'owner=acme' in args and 'name=widget' in args


def test_cache_shared_by_project_and_failed_refresh_retains_count(tmp_path):
    github.clear_cache()
    with patch.object(github,'_github_remote',return_value='acme/widget'), patch.object(github,'_gh',return_value=[]), patch.object(github,'_merged_pr_count',side_effect=[25,None]) as count:
        first=github.get_github_info(tmp_path)
        linked=github.get_github_info(tmp_path/'worktree')
        assert linked is first and count.call_count==1
        failed=github.get_github_info(tmp_path,refresh=True)
    assert failed.merged_pr_count==25
    assert failed.merged_pr_checked_at==first.merged_pr_checked_at
    assert failed.merged_pr_error
    github.clear_cache()


def test_new_project_cannot_inherit_count(tmp_path):
    github.clear_cache()
    with patch.object(github,'_github_remote',side_effect=['acme/one','acme/two']), patch.object(github,'_gh',return_value=[]), patch.object(github,'_merged_pr_count',side_effect=[25,None]):
        assert github.get_github_info(tmp_path).merged_pr_count==25
        assert github.get_github_info(tmp_path).merged_pr_count is None
    github.clear_cache()


def test_browser_growth_state(tmp_path):
    from playwright.sync_api import sync_playwright
    from bonsai_review import open_scene
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        open_scene(page)
        page.evaluate('''() => {
          const repo=repos[0], slug=githubSlugForRepo(repo), linked=repos[1];
          const accept=(n,extra)=>acceptGithubSnapshot(slug,n,{has_github:true,prs:[],issues:[],checked_at:new Date().toISOString(),...extra});
          if(mergedPrGrowthInfo(repo).count!==null)throw Error('Unknown count');
          accept(1,{merged_pr_count:0});
          if(mergedPrGrowthInfo(repo).stage!=='seedling')throw Error('Zero count');
          accept(2,{merged_pr_count:25});
          if(mergedPrGrowthInfo(linked).count!==25)throw Error('Worktree count differs');
          const time=mergedPrGrowthInfo(repo).checkedAt;
          accept(3,{transport_failed:true,merged_pr_count:0});
          const retained=mergedPrGrowthInfo(repo);
          if(retained.count!==25 || !retained.stale || retained.checkedAt!==time)throw Error('Failed retention');
          accept(2,{merged_pr_count:1});
          if(mergedPrGrowthInfo(repo).count!==25)throw Error('Old response accepted');
          accept(4,{merged_pr_count:26});
          if(mergedPrGrowthInfo(repo).stale)throw Error('Did not recover');
          linked._status.github_repo='other/repo';
          if(mergedPrGrowthInfo(linked).count!==null)throw Error('Identity leaked');
          for(const [count,stage] of [[0,'seedling'],[5,'seedling'],[6,'growing'],[20,'growing'],[21,'mature'],[null,'unknown']]) {
            if(pixelGrowth(count).stage!==stage)throw Error('Boundary');
          }
          selectBoardRepo(repo.path);
          renderBoard();
        }''')
        assert '26 merged PRs' in page.locator('.merged-pr-growth').inner_text()
        assert not errors
        page.screenshot(path=str(tmp_path/'live-growth.png'))
        browser.close()
