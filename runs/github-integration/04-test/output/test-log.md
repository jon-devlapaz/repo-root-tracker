
$ ["pip", "install", "-e", "."]
Obtaining file:///Users/jondev/dev/active/repo-root-tracker
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Installing backend dependencies: started
  Installing backend dependencies: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Building wheels for collected packages: repo-root-tracker
  Building editable for repo-root-tracker (pyproject.toml): started
  Building editable for repo-root-tracker (pyproject.toml): finished with status 'done'
  Created wheel for repo-root-tracker: filename=repo_root_tracker-0.1.0-py3-none-any.whl size=1653 sha256=3b308f00e8344f5e762e4ea40f4100442397c24c52f90dea5f7538439d15244e
  Stored in directory: /private/var/folders/sk/r2ns7lvn2ygcsj7bhd0mvnyw0000gn/T/pip-ephem-wheel-cache-iym66qqm/wheels/59/4f/16/862fe7aee12d0c22486bd297d27902a281d2cf9afa2d7ea0d4
Successfully built repo-root-tracker
Installing collected packages: repo-root-tracker
  Attempting uninstall: repo-root-tracker
    Found existing installation: repo-root-tracker 0.1.0
    Uninstalling repo-root-tracker-0.1.0:
      Successfully uninstalled repo-root-tracker-0.1.0
Successfully installed repo-root-tracker-0.1.0

$ ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 58 items

tests/test_detail.py::test_detail_commits PASSED                         [  1%]
tests/test_detail.py::test_detail_lanes_assigned PASSED                  [  3%]
tests/test_detail.py::test_detail_branches PASSED                        [  5%]
tests/test_detail.py::test_detail_remote_branches PASSED                 [  6%]
tests/test_detail.py::test_detail_no_remotes_section_when_none PASSED    [  8%]
tests/test_detail.py::test_detail_changed_files_clean PASSED             [ 10%]
tests/test_detail.py::test_detail_changed_files_dirty PASSED             [ 12%]
tests/test_detail.py::test_commit_diff PASSED                            [ 13%]
tests/test_detail.py::test_commit_diff_rejects_bad_hash PASSED           [ 15%]
tests/test_detail.py::test_working_diff PASSED                           [ 17%]
tests/test_detail.py::test_working_diff_rejects_traversal PASSED         [ 18%]
tests/test_detail.py::test_repo_endpoint PASSED                          [ 20%]
tests/test_detail.py::test_repo_endpoint_untracked_404 PASSED            [ 22%]
tests/test_detail.py::test_commit_endpoint PASSED                        [ 24%]
tests/test_detail.py::test_working_diff_endpoint PASSED                  [ 25%]
tests/test_find_root.py::test_find_root_from_repo_root PASSED            [ 27%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 29%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 31%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 32%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 34%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 36%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 37%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 39%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 41%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 43%]
tests/test_github.py::test_rollup_empty PASSED                           [ 44%]
tests/test_github.py::test_rollup_all_pass PASSED                        [ 46%]
tests/test_github.py::test_rollup_failure PASSED                         [ 48%]
tests/test_github.py::test_rollup_pending PASSED                         [ 50%]
tests/test_github.py::test_no_origin PASSED                              [ 51%]
tests/test_github.py::test_non_github_remote PASSED                      [ 53%]
tests/test_github.py::test_github_https_remote_parsed PASSED             [ 55%]
tests/test_github.py::test_github_ssh_remote_parsed PASSED               [ 56%]
tests/test_github.py::test_gh_failure_marks_unavailable PASSED           [ 58%]
tests/test_github.py::test_prs_and_issues_mapped PASSED                  [ 60%]
tests/test_github.py::test_cache_bounds_calls PASSED                     [ 62%]
tests/test_github.py::test_endpoint_no_remote PASSED                     [ 63%]
tests/test_github.py::test_endpoint_untracked_404 PASSED                 [ 65%]
tests/test_github.py::test_endpoint_live_github PASSED                   [ 67%]
tests/test_server.py::test_validate_repo_valid PASSED                    [ 68%]
tests/test_server.py::test_validate_repo_from_subdirectory PASSED        [ 70%]
tests/test_server.py::test_validate_repo_invalid PASSED                  [ 72%]
tests/test_server.py::test_load_repos_missing_file PASSED                [ 74%]
tests/test_server.py::test_save_and_load_roundtrip PASSED                [ 75%]
tests/test_server.py::test_config_dir_created_on_save PASSED             [ 77%]
tests/test_server.py::test_dashboard_html_served PASSED                  [ 79%]
tests/test_server.py::test_repos_api_crud PASSED                         [ 81%]
tests/test_server.py::test_validate_endpoint PASSED                      [ 82%]
tests/test_status.py::test_branch_and_last_commit PASSED                 [ 84%]
tests/test_status.py::test_clean_repo_is_clean PASSED                    [ 86%]
tests/test_status.py::test_modified_and_untracked_counts PASSED          [ 87%]
tests/test_status.py::test_staged_counts PASSED                          [ 89%]
tests/test_status.py::test_no_upstream PASSED                            [ 91%]
tests/test_status.py::test_ahead_of_upstream PASSED                      [ 93%]
tests/test_status.py::test_no_stale_branches_on_fresh_repo PASSED        [ 94%]
tests/test_status.py::test_stale_branch_detected PASSED                  [ 96%]
tests/test_status.py::test_status_endpoint_tracked PASSED                [ 98%]
tests/test_status.py::test_status_endpoint_untracked_404 PASSED          [100%]

============================= 58 passed in 14.34s ==============================

# checklist item github-module
$ ["python3", "-m", "pytest", "tests/test_github.py", "-v", "--tb=short"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 14 items

tests/test_github.py::test_rollup_empty PASSED                           [  7%]
tests/test_github.py::test_rollup_all_pass PASSED                        [ 14%]
tests/test_github.py::test_rollup_failure PASSED                         [ 21%]
tests/test_github.py::test_rollup_pending PASSED                         [ 28%]
tests/test_github.py::test_no_origin PASSED                              [ 35%]
tests/test_github.py::test_non_github_remote PASSED                      [ 42%]
tests/test_github.py::test_github_https_remote_parsed PASSED             [ 50%]
tests/test_github.py::test_github_ssh_remote_parsed PASSED               [ 57%]
tests/test_github.py::test_gh_failure_marks_unavailable PASSED           [ 64%]
tests/test_github.py::test_prs_and_issues_mapped PASSED                  [ 71%]
tests/test_github.py::test_cache_bounds_calls PASSED                     [ 78%]
tests/test_github.py::test_endpoint_no_remote PASSED                     [ 85%]
tests/test_github.py::test_endpoint_untracked_404 PASSED                 [ 92%]
tests/test_github.py::test_endpoint_live_github PASSED                   [100%]

============================== 14 passed in 4.09s ==============================

# checklist item all-tests-pass
$ ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 58 items

tests/test_detail.py::test_detail_commits PASSED                         [  1%]
tests/test_detail.py::test_detail_lanes_assigned PASSED                  [  3%]
tests/test_detail.py::test_detail_branches PASSED                        [  5%]
tests/test_detail.py::test_detail_remote_branches PASSED                 [  6%]
tests/test_detail.py::test_detail_no_remotes_section_when_none PASSED    [  8%]
tests/test_detail.py::test_detail_changed_files_clean PASSED             [ 10%]
tests/test_detail.py::test_detail_changed_files_dirty PASSED             [ 12%]
tests/test_detail.py::test_commit_diff PASSED                            [ 13%]
tests/test_detail.py::test_commit_diff_rejects_bad_hash PASSED           [ 15%]
tests/test_detail.py::test_working_diff PASSED                           [ 17%]
tests/test_detail.py::test_working_diff_rejects_traversal PASSED         [ 18%]
tests/test_detail.py::test_repo_endpoint PASSED                          [ 20%]
tests/test_detail.py::test_repo_endpoint_untracked_404 PASSED            [ 22%]
tests/test_detail.py::test_commit_endpoint PASSED                        [ 24%]
tests/test_detail.py::test_working_diff_endpoint PASSED                  [ 25%]
tests/test_find_root.py::test_find_root_from_repo_root PASSED            [ 27%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 29%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 31%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 32%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 34%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 36%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 37%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 39%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 41%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 43%]
tests/test_github.py::test_rollup_empty PASSED                           [ 44%]
tests/test_github.py::test_rollup_all_pass PASSED                        [ 46%]
tests/test_github.py::test_rollup_failure PASSED                         [ 48%]
tests/test_github.py::test_rollup_pending PASSED                         [ 50%]
tests/test_github.py::test_no_origin PASSED                              [ 51%]
tests/test_github.py::test_non_github_remote PASSED                      [ 53%]
tests/test_github.py::test_github_https_remote_parsed PASSED             [ 55%]
tests/test_github.py::test_github_ssh_remote_parsed PASSED               [ 56%]
tests/test_github.py::test_gh_failure_marks_unavailable PASSED           [ 58%]
tests/test_github.py::test_prs_and_issues_mapped PASSED                  [ 60%]
tests/test_github.py::test_cache_bounds_calls PASSED                     [ 62%]
tests/test_github.py::test_endpoint_no_remote PASSED                     [ 63%]
tests/test_github.py::test_endpoint_untracked_404 PASSED                 [ 65%]
tests/test_github.py::test_endpoint_live_github PASSED                   [ 67%]
tests/test_server.py::test_validate_repo_valid PASSED                    [ 68%]
tests/test_server.py::test_validate_repo_from_subdirectory PASSED        [ 70%]
tests/test_server.py::test_validate_repo_invalid PASSED                  [ 72%]
tests/test_server.py::test_load_repos_missing_file PASSED                [ 74%]
tests/test_server.py::test_save_and_load_roundtrip PASSED                [ 75%]
tests/test_server.py::test_config_dir_created_on_save PASSED             [ 77%]
tests/test_server.py::test_dashboard_html_served PASSED                  [ 79%]
tests/test_server.py::test_repos_api_crud PASSED                         [ 81%]
tests/test_server.py::test_validate_endpoint PASSED                      [ 82%]
tests/test_status.py::test_branch_and_last_commit PASSED                 [ 84%]
tests/test_status.py::test_clean_repo_is_clean PASSED                    [ 86%]
tests/test_status.py::test_modified_and_untracked_counts PASSED          [ 87%]
tests/test_status.py::test_staged_counts PASSED                          [ 89%]
tests/test_status.py::test_no_upstream PASSED                            [ 91%]
tests/test_status.py::test_ahead_of_upstream PASSED                      [ 93%]
tests/test_status.py::test_no_stale_branches_on_fresh_repo PASSED        [ 94%]
tests/test_status.py::test_stale_branch_detected PASSED                  [ 96%]
tests/test_status.py::test_status_endpoint_tracked PASSED                [ 98%]
tests/test_status.py::test_status_endpoint_untracked_404 PASSED          [100%]

============================= 58 passed in 15.28s ==============================
