
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
  Stored in directory: /private/var/folders/sk/r2ns7lvn2ygcsj7bhd0mvnyw0000gn/T/pip-ephem-wheel-cache-ikaz1gl8/wheels/59/4f/16/862fe7aee12d0c22486bd297d27902a281d2cf9afa2d7ea0d4
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
collecting ... collected 42 items

tests/test_detail.py::test_detail_commits PASSED                         [  2%]
tests/test_detail.py::test_detail_lanes_assigned PASSED                  [  4%]
tests/test_detail.py::test_detail_branches PASSED                        [  7%]
tests/test_detail.py::test_detail_changed_files_clean PASSED             [  9%]
tests/test_detail.py::test_detail_changed_files_dirty PASSED             [ 11%]
tests/test_detail.py::test_commit_diff PASSED                            [ 14%]
tests/test_detail.py::test_commit_diff_rejects_bad_hash PASSED           [ 16%]
tests/test_detail.py::test_working_diff PASSED                           [ 19%]
tests/test_detail.py::test_working_diff_rejects_traversal PASSED         [ 21%]
tests/test_detail.py::test_repo_endpoint PASSED                          [ 23%]
tests/test_detail.py::test_repo_endpoint_untracked_404 PASSED            [ 26%]
tests/test_detail.py::test_commit_endpoint PASSED                        [ 28%]
tests/test_detail.py::test_working_diff_endpoint PASSED                  [ 30%]
tests/test_find_root.py::test_find_root_from_repo_root PASSED            [ 33%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 35%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 38%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 40%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 42%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 45%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 47%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 50%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 52%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 54%]
tests/test_server.py::test_validate_repo_valid PASSED                    [ 57%]
tests/test_server.py::test_validate_repo_from_subdirectory PASSED        [ 59%]
tests/test_server.py::test_validate_repo_invalid PASSED                  [ 61%]
tests/test_server.py::test_load_repos_missing_file PASSED                [ 64%]
tests/test_server.py::test_save_and_load_roundtrip PASSED                [ 66%]
tests/test_server.py::test_config_dir_created_on_save PASSED             [ 69%]
tests/test_server.py::test_dashboard_html_served PASSED                  [ 71%]
tests/test_server.py::test_repos_api_crud PASSED                         [ 73%]
tests/test_server.py::test_validate_endpoint PASSED                      [ 76%]
tests/test_status.py::test_branch_and_last_commit PASSED                 [ 78%]
tests/test_status.py::test_clean_repo_is_clean PASSED                    [ 80%]
tests/test_status.py::test_modified_and_untracked_counts PASSED          [ 83%]
tests/test_status.py::test_staged_counts PASSED                          [ 85%]
tests/test_status.py::test_no_upstream PASSED                            [ 88%]
tests/test_status.py::test_ahead_of_upstream PASSED                      [ 90%]
tests/test_status.py::test_no_stale_branches_on_fresh_repo PASSED        [ 92%]
tests/test_status.py::test_stale_branch_detected PASSED                  [ 95%]
tests/test_status.py::test_status_endpoint_tracked PASSED                [ 97%]
tests/test_status.py::test_status_endpoint_untracked_404 PASSED          [100%]

============================= 42 passed in 10.21s ==============================

# checklist item detail-module
$ ["python3", "-m", "pytest", "tests/test_detail.py", "-v", "--tb=short"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 13 items

tests/test_detail.py::test_detail_commits PASSED                         [  7%]
tests/test_detail.py::test_detail_lanes_assigned PASSED                  [ 15%]
tests/test_detail.py::test_detail_branches PASSED                        [ 23%]
tests/test_detail.py::test_detail_changed_files_clean PASSED             [ 30%]
tests/test_detail.py::test_detail_changed_files_dirty PASSED             [ 38%]
tests/test_detail.py::test_commit_diff PASSED                            [ 46%]
tests/test_detail.py::test_commit_diff_rejects_bad_hash PASSED           [ 53%]
tests/test_detail.py::test_working_diff PASSED                           [ 61%]
tests/test_detail.py::test_working_diff_rejects_traversal PASSED         [ 69%]
tests/test_detail.py::test_repo_endpoint PASSED                          [ 76%]
tests/test_detail.py::test_repo_endpoint_untracked_404 PASSED            [ 84%]
tests/test_detail.py::test_commit_endpoint PASSED                        [ 92%]
tests/test_detail.py::test_working_diff_endpoint PASSED                  [100%]

============================== 13 passed in 4.90s ==============================

# checklist item all-tests-pass
$ ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 42 items

tests/test_detail.py::test_detail_commits PASSED                         [  2%]
tests/test_detail.py::test_detail_lanes_assigned PASSED                  [  4%]
tests/test_detail.py::test_detail_branches PASSED                        [  7%]
tests/test_detail.py::test_detail_changed_files_clean PASSED             [  9%]
tests/test_detail.py::test_detail_changed_files_dirty PASSED             [ 11%]
tests/test_detail.py::test_commit_diff PASSED                            [ 14%]
tests/test_detail.py::test_commit_diff_rejects_bad_hash PASSED           [ 16%]
tests/test_detail.py::test_working_diff PASSED                           [ 19%]
tests/test_detail.py::test_working_diff_rejects_traversal PASSED         [ 21%]
tests/test_detail.py::test_repo_endpoint PASSED                          [ 23%]
tests/test_detail.py::test_repo_endpoint_untracked_404 PASSED            [ 26%]
tests/test_detail.py::test_commit_endpoint PASSED                        [ 28%]
tests/test_detail.py::test_working_diff_endpoint PASSED                  [ 30%]
tests/test_find_root.py::test_find_root_from_repo_root PASSED            [ 33%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 35%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 38%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 40%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 42%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 45%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 47%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 50%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 52%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 54%]
tests/test_server.py::test_validate_repo_valid PASSED                    [ 57%]
tests/test_server.py::test_validate_repo_from_subdirectory PASSED        [ 59%]
tests/test_server.py::test_validate_repo_invalid PASSED                  [ 61%]
tests/test_server.py::test_load_repos_missing_file PASSED                [ 64%]
tests/test_server.py::test_save_and_load_roundtrip PASSED                [ 66%]
tests/test_server.py::test_config_dir_created_on_save PASSED             [ 69%]
tests/test_server.py::test_dashboard_html_served PASSED                  [ 71%]
tests/test_server.py::test_repos_api_crud PASSED                         [ 73%]
tests/test_server.py::test_validate_endpoint PASSED                      [ 76%]
tests/test_status.py::test_branch_and_last_commit PASSED                 [ 78%]
tests/test_status.py::test_clean_repo_is_clean PASSED                    [ 80%]
tests/test_status.py::test_modified_and_untracked_counts PASSED          [ 83%]
tests/test_status.py::test_staged_counts PASSED                          [ 85%]
tests/test_status.py::test_no_upstream PASSED                            [ 88%]
tests/test_status.py::test_ahead_of_upstream PASSED                      [ 90%]
tests/test_status.py::test_no_stale_branches_on_fresh_repo PASSED        [ 92%]
tests/test_status.py::test_stale_branch_detected PASSED                  [ 95%]
tests/test_status.py::test_status_endpoint_tracked PASSED                [ 97%]
tests/test_status.py::test_status_endpoint_untracked_404 PASSED          [100%]

============================= 42 passed in 10.38s ==============================
