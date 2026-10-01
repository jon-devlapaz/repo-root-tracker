"""Default-branch Actions health, mocked at the read-only gh boundary."""

from urllib.parse import parse_qs, unquote, urlsplit
from unittest.mock import patch

import pytest

from repo_root_tracker.github import clear_cache, get_github_info

HEAD = "a" * 40
OLD = "b" * 40


def workflow(number=1, name="CI", state="active"):
    return {"id": number, "name": name, "state": state, "html_url": f"https://github.com/owner/repo/actions/workflows/{number}"}


def run(number=1, workflow_id=1, conclusion="failure", sha=HEAD, status="completed", branch="trunk"):
    return {"id": number, "workflow_id": workflow_id, "name": "CI", "run_number": number,
            "run_attempt": 1, "head_sha": sha, "head_branch": branch, "event": "push",
            "status": status, "conclusion": conclusion, "updated_at": "2026-10-01T00:00:00Z",
            "html_url": f"https://github.com/owner/repo/actions/runs/{number}"}


@pytest.fixture(autouse=True)
def cache():
    clear_cache()
    yield
    clear_cache()


class Gh:
    def __init__(self, *, branch="trunk", workflows=None, current=None, older=None):
        self.branch = branch
        self.workflows = workflows if workflows is not None else [workflow()]
        self.current = current if current is not None else [run()]
        self.older = older or []
        self.calls = []
        self.fail = set()
        self.counts = {}

    def __call__(self, *args, cwd):
        self.calls.append(args)
        if args[0] in {"pr", "issue"}:
            return None if args[0] in self.fail else []
        assert args[0] == "api"
        endpoint = urlsplit(args[1])
        path, query = unquote(endpoint.path), parse_qs(endpoint.query)
        assert path.startswith("repos/owner/repo")
        if path.endswith("/actions/workflows"):
            key, data = "workflows", self.workflows
            result = [{"total_count": self.counts.get(key, len(data)), "workflows": data}]
        elif path.endswith("/actions/runs"):
            assert query["branch"] == [self.branch]
            assert query["per_page"] == ["100"]
            key = "current" if "head_sha" in query else "older"
            if key == "current":
                assert query["head_sha"] == [HEAD]
            data = self.current if key == "current" else self.older
            result = [{"total_count": self.counts.get(key, len(data)), "workflow_runs": data}]
        elif "/branches/" in path:
            assert path.endswith("/branches/" + self.branch)
            key, result = "head", [{"sha": HEAD}]
        else:
            assert path == "repos/owner/repo"
            key, result = "repo", [{"default_branch": self.branch}]
        return None if key in self.fail else result


def info_for(tmp_path, gh, refresh=False):
    with patch("repo_root_tracker.github._github_remote", return_value="owner/repo"), patch("repo_root_tracker.github._gh", side_effect=gh):
        return get_github_info(tmp_path, refresh=refresh)


def test_no_prs_but_default_branch_fails(tmp_path):
    info = info_for(tmp_path, Gh())
    assert not info.prs
    assert info.default_branch == "trunk"
    assert info.workflows.state == "failing"
    assert info.to_dict()["workflows"]["runs"][0]["current_head"] is True


def test_one_passing_workflow_never_masks_another_failure(tmp_path):
    gh = Gh(workflows=[workflow(1), workflow(2, "Lint")], current=[run(1, 1, "success"), run(2, 2)])
    assert info_for(tmp_path, gh).workflows.state == "failing"


def test_old_success_cannot_mask_current_head_pending(tmp_path):
    gh = Gh(current=[run(status="in_progress", conclusion=None)], older=[run(99, conclusion="success", sha=OLD)])
    info = info_for(tmp_path, gh)
    assert info.workflows.state == "pending"
    assert all(r.current_head for r in info.workflows.runs)


@pytest.mark.parametrize('branch', ['trunk', 'release/stable'])
def test_remote_default_branch_is_used_and_encoded(tmp_path, branch):
    gh = Gh(branch=branch, current=[run(conclusion='success', branch=branch)])
    info = info_for(tmp_path, gh)
    assert info.default_branch == branch
    assert info.workflows.state == 'passing'
    assert any('/branches/' + branch.replace('/', '%2F') in args[1] for args in gh.calls if args[0] == 'api')
    assert all(args[args.index('--method') + 1] == 'GET' for args in gh.calls if args[0] == 'api')
    assert len(gh.calls) == 6  # two existing queries plus four bounded API calls


@pytest.mark.parametrize('status,conclusion,state', [
    ('completed', 'success', 'passing'), ('in_progress', None, 'pending'),
    ('queued', None, 'pending'), ('waiting', None, 'pending'),
    ('completed', 'failure', 'failing'), ('completed', 'timed_out', 'failing'),
    ('completed', 'action_required', 'failing'), ('completed', 'cancelled', 'unknown'),
    ('completed', 'skipped', 'unknown'), ('completed', 'neutral', 'unknown'),
    ('completed', None, 'unknown'), ('unexpected', '', 'unknown'),
])
def test_current_head_outcomes_are_truthful(tmp_path, status, conclusion, state):
    info = info_for(tmp_path, Gh(current=[run(status=status, conclusion=conclusion)]))
    assert info.workflows.state == state
    assert info.workflows.runs[0].conclusion == (conclusion or '')


@pytest.mark.parametrize('conclusion', ['failure', None])
def test_old_success_never_masks_current_failure_or_pending(tmp_path, conclusion):
    current = run(conclusion=conclusion, status='completed' if conclusion else 'queued')
    gh = Gh(current=[current], older=[run(99, conclusion='success', sha=OLD)])
    info = info_for(tmp_path, gh)
    assert info.workflows.state == ('failing' if conclusion else 'pending')
    assert info.workflows.runs[0].url.endswith('/runs/1')


def test_latest_run_per_workflow_wins_even_if_old_run_updated_later(tmp_path):
    old = run(1)
    old['updated_at'] = '2026-10-02T00:00:00Z'
    gh = Gh(current=[old, run(2, conclusion='success')])
    info = info_for(tmp_path, gh)
    assert info.workflows.state == 'passing'
    assert len(info.workflows.runs) == 1
    assert info.workflows.runs[0].url.endswith('/runs/2')


def test_failure_wins_over_pending_in_other_workflow(tmp_path):
    gh = Gh(workflows=[workflow(1), workflow(2)], current=[run(), run(2, 2, None, status='queued')])
    assert info_for(tmp_path, gh).workflows.state == 'failing'


def test_success_only_on_an_older_head_is_stale(tmp_path):
    gh = Gh(current=[], older=[run(conclusion='success', sha=OLD)])
    info = info_for(tmp_path, gh)
    assert info.workflows.state == 'stale'
    result = info.to_dict()['workflows']['runs'][0]
    assert result['current_head'] is False
    assert result['head_sha'] == OLD
    assert result['conclusion'] == 'success'


@pytest.mark.parametrize('workflows', [[], [workflow()], [workflow(state='disabled_manually')]])
def test_no_runs_or_disabled_is_never_passing(tmp_path, workflows):
    info = info_for(tmp_path, Gh(workflows=workflows, current=[]))
    assert info.workflows.state == 'unknown'


def test_disabled_workflow_old_success_is_not_passing(tmp_path):
    gh = Gh(workflows=[workflow(state='disabled_manually')], current=[run(conclusion='success')])
    assert info_for(tmp_path, gh).workflows.state == 'unknown'


def test_missing_workflow_run_is_not_hidden_by_one_success(tmp_path):
    gh = Gh(workflows=[workflow(1), workflow(2, 'Lint')], current=[run(conclusion='success')])
    assert info_for(tmp_path, gh).workflows.state == 'unknown'


@pytest.mark.parametrize('bad_run', [run(branch='feature'), run(sha=OLD), dict(run(), event='pull_request'), dict(run(), event='pull_request_target')])
def test_wrong_branch_head_or_pr_event_cannot_count_as_default_branch_run(tmp_path, bad_run):
    info = info_for(tmp_path, Gh(current=[bad_run]))
    assert info.workflows.state == 'unknown'
    assert not info.workflows.runs[0].current_head


@pytest.mark.parametrize('failure', ['repo', 'head', 'workflows', 'current', 'older'])
def test_partial_gh_failure_is_explicit_and_never_passing(tmp_path, failure):
    gh = Gh(current=[] if failure == 'older' else [run(conclusion='success')])
    gh.fail.add(failure)
    info = info_for(tmp_path, gh)
    assert info.workflows.state == 'unknown'
    assert info.workflows.errors
    assert set(info.workflows.errors) <= set(info.errors)
    assert info.has_github and not info.gh_unavailable


def test_confirmed_failure_survives_inventory_and_pr_query_failures(tmp_path):
    gh = Gh()
    gh.fail.update({'workflows', 'pr', 'issue'})
    info = info_for(tmp_path, gh)
    assert info.workflows.state == 'failing'
    assert info.errors and info.has_github and not info.gh_unavailable
    assert info.workflows.runs[0].current_head


@pytest.mark.parametrize('conclusion,state', [('success', 'unknown'), ('failure', 'failing')])
@pytest.mark.parametrize('query', ['workflows', 'current'])
def test_bounded_incomplete_data_never_claims_passing(tmp_path, conclusion, state, query):
    gh = Gh(current=[run(conclusion=conclusion)])
    gh.counts[query] = 101
    info = info_for(tmp_path, gh)
    assert info.workflows.state == state
    assert any('coverage is incomplete' in error for error in info.errors)
    assert len(gh.calls) <= 7


def test_cache_refresh_and_worktree_family_deduplication(tmp_path):
    import subprocess
    from concurrent.futures import ThreadPoolExecutor

    root, sibling = tmp_path / 'repo', tmp_path / 'worktree'
    subprocess.run(['git', 'init', str(root)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test', '-c', 'user.email=test@example.test',
                    'commit', '--allow-empty', '-m', 'initial'], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(root), 'remote', 'add', 'origin', 'https://github.com/owner/repo.git'], check=True)
    subprocess.run(['git', '-C', str(root), 'worktree', 'add', '--detach', str(sibling)], check=True, capture_output=True)
    gh = Gh()
    with patch('repo_root_tracker.github._gh', side_effect=gh):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(get_github_info, [root, sibling]))
        assert results[0] is results[1]
        assert results[0].workflows.state == 'failing'
        assert len(gh.calls) == 6
        gh.current = [run(conclusion='success')]
        assert get_github_info(sibling).workflows.state == 'failing'
        assert len(gh.calls) == 6
        assert get_github_info(sibling, refresh=True).workflows.state == 'passing'
        assert len(gh.calls) == 12


@pytest.mark.parametrize('error', ['timeout', 'missing', 'invalid-json', 'denied'])
def test_gh_transport_failure_uses_existing_timeout_and_error_path(tmp_path, error):
    import subprocess

    def process(args, **kwargs):
        if args[0] == 'git':
            return subprocess.CompletedProcess(args, 0, 'https://github.com/owner/repo.git', '')
        assert args[0] == 'gh' and kwargs['timeout'] == 30
        if error == 'timeout':
            raise subprocess.TimeoutExpired(args, 30)
        if error == 'missing':
            raise FileNotFoundError()
        return subprocess.CompletedProcess(args, int(error == 'denied'), '{invalid', '')

    with patch('repo_root_tracker.github.subprocess.run', side_effect=process):
        info = get_github_info(tmp_path)
    assert info.gh_unavailable and not info.has_github
    assert info.workflows.state == 'unknown'
    assert info.errors and info.workflows.errors


def test_api_github_exposes_health_and_keeps_existing_fields(tmp_path):
    from repo_root_tracker import server

    gh = Gh()
    handler = server.Handler.__new__(server.Handler)
    handler.headers = {'Host': 'localhost'}
    handler.path = '/api/github?path=' + str(tmp_path) + '&refresh=1'
    with patch('repo_root_tracker.github._github_remote', return_value='owner/repo'), \
         patch('repo_root_tracker.github._gh', side_effect=gh), \
         patch('repo_root_tracker.server.load_repos', return_value=[{'path': str(tmp_path)}]), \
         patch.object(handler, '_json') as respond:
        handler.do_GET()
    code, data = respond.call_args.args
    assert code == 200
    assert data['default_branch'] == 'trunk'
    assert data['workflows']['state'] == 'failing'
    assert data['workflows']['head_sha'] == HEAD
    assert data['workflows']['runs'][0]['url'].endswith('/actions/runs/1')
    assert data['prs'] == [] and data['issues'] == [] and data['errors'] == []
    assert data['has_github'] and not data['gh_unavailable']


def test_malformed_workflow_inventory_cannot_claim_all_passing(tmp_path):
    gh = Gh(workflows=[workflow(1), {'name': 'Missing workflow ID', 'state': 'active'}], current=[run(conclusion='success')])
    info = info_for(tmp_path, gh)
    assert info.workflows.state == 'unknown'
    assert any('invalid' in error for error in info.workflows.errors)


def test_actions_api_host_is_pinned_even_with_a_different_gh_host(tmp_path, monkeypatch):
    monkeypatch.setenv('GH_HOST', 'github.enterprise.test')
    # A missing current run also exercises the history request through the same helper.
    gh = Gh(current=[], older=[run(conclusion='success', sha=OLD)])
    info = info_for(tmp_path, gh)
    assert info.workflows.state == 'stale'
    api_calls = [args for args in gh.calls if args[0] == 'api']
    assert len(api_calls) == 5
    for args in api_calls:
        assert '--hostname' in args
        assert args[args.index('--hostname') + 1] == 'github.com'
        assert args[args.index('--method') + 1] == 'GET'


@pytest.mark.parametrize('origin', [None, 'https://gitlab.com/owner/repo.git'])
def test_no_github_remote_has_no_workflow_health(tmp_path, origin):
    import subprocess

    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    if origin:
        subprocess.run(['git', '-C', str(tmp_path), 'remote', 'add', 'origin', origin], check=True)
    with patch('repo_root_tracker.github._gh') as gh:
        info = get_github_info(tmp_path)
    data = info.to_dict()
    assert data['workflows'] is None
    assert not data['has_github'] and not data['gh_unavailable']
    assert data['repo'] == '' and data['default_branch'] == '' and data['errors'] == []
    gh.assert_not_called()


def test_github_remote_access_failure_preserves_unknown_workflow_health(tmp_path):
    gh = Gh()
    gh.fail.update({'pr', 'issue', 'repo'})
    data = info_for(tmp_path, gh).to_dict()
    assert data['repo'] == 'owner/repo'
    assert not data['has_github'] and data['gh_unavailable']
    assert data['workflows']['state'] == 'unknown'
    assert data['workflows']['errors']
