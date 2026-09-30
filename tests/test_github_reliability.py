import subprocess
from unittest.mock import patch

import pytest

from repo_root_tracker.github import clear_cache, get_github_info


@pytest.fixture()
def repo(tmp_path):
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(tmp_path), 'remote', 'add', 'origin', 'https://github.com/owner/fork.git'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'remote', 'add', 'upstream', 'https://github.com/other/base.git'], check=True)
    clear_cache()
    yield tmp_path
    clear_cache()


def test_github_queries_explicitly_target_origin(repo):
    def gh(*args, cwd):
        slug = args[args.index('--repo') + 1].removeprefix('github.com/') if '--repo' in args else 'other/base'
        return [{'number': 1, 'url': f'https://github.com/{slug}/pull/1'}] if args[0] == 'pr' else []

    with patch('repo_root_tracker.github._gh', side_effect=gh) as run:
        info = get_github_info(repo)
    assert info.prs[0].url == f'{info.repo_url}/pull/1'
    for call in run.call_args_list:
        args = call.args
        assert args[args.index('--repo') + 1] == f'github.com/{info.repo}'


def test_prs_beyond_one_hundred_include_blockers(repo):
    def gh(*args, cwd):
        if args[0] != 'pr':
            return []
        limit = int(args[args.index('--limit') + 1])
        prs = [{'number': n} for n in range(1, 126)]
        prs[-1]['statusCheckRollup'] = [{'status': 'COMPLETED', 'conclusion': 'FAILURE'}]
        return prs[:limit]

    with patch('repo_root_tracker.github._gh', side_effect=gh):
        info = get_github_info(repo)
    assert len(info.prs) == 125
    assert info.prs[-1].ci.state == 'fail'
    assert not info.pr_limit_reached


@pytest.mark.parametrize('count,incomplete', [(200, False), (201, True), (250, True)])
def test_pr_coverage_bound_and_lookahead(repo, count, incomplete):
    def gh(*args, cwd):
        if args[0] != 'pr':
            return []
        limit = int(args[args.index('--limit') + 1])
        assert limit == 201
        return [{'number': n} for n in range(count)][:limit]

    with patch('repo_root_tracker.github._gh', side_effect=gh):
        info = get_github_info(repo)
    assert len(info.prs) == min(count, 200)
    assert info.pr_limit_reached is incomplete
    assert info.pr_limit == 200
    assert info.to_dict()['pr_limit'] == 200


def test_paginated_query_failure_stays_explicit(repo):
    with patch('repo_root_tracker.github._gh', side_effect=[None, []]):
        info = get_github_info(repo)
    assert info.errors and 'Pull requests' in info.errors[0]
    assert info.has_github
    assert not info.prs
