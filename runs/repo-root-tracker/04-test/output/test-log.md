
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
  Stored in directory: /private/var/folders/sk/r2ns7lvn2ygcsj7bhd0mvnyw0000gn/T/pip-ephem-wheel-cache-f53s3q10/wheels/59/4f/16/862fe7aee12d0c22486bd297d27902a281d2cf9afa2d7ea0d4
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
collecting ... collected 19 items

tests/test_find_root.py::test_find_root_from_repo_root PASSED            [  5%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 10%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 15%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 21%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 26%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 31%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 36%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 42%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 47%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 52%]
tests/test_server.py::test_validate_repo_valid PASSED                    [ 57%]
tests/test_server.py::test_validate_repo_from_subdirectory PASSED        [ 63%]
tests/test_server.py::test_validate_repo_invalid PASSED                  [ 68%]
tests/test_server.py::test_load_repos_missing_file PASSED                [ 73%]
tests/test_server.py::test_save_and_load_roundtrip PASSED                [ 78%]
tests/test_server.py::test_config_dir_created_on_save PASSED             [ 84%]
tests/test_server.py::test_dashboard_html_served PASSED                  [ 89%]
tests/test_server.py::test_repos_api_crud PASSED                         [ 94%]
tests/test_server.py::test_validate_endpoint PASSED                      [100%]

============================== 19 passed in 2.81s ==============================

# checklist item zero-deps
$ ["python3", "-c", "import tomllib, sys; d=tomllib.load(open('pyproject.toml','rb')); deps=d.get('project',{}).get('dependencies',[]); sys.exit(0 if deps==[] else 1)"]

# checklist item all-tests-pass
$ ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items

tests/test_find_root.py::test_find_root_from_repo_root PASSED            [  5%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 10%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 15%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 21%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 26%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 31%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 36%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 42%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 47%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 52%]
tests/test_server.py::test_validate_repo_valid PASSED                    [ 57%]
tests/test_server.py::test_validate_repo_from_subdirectory PASSED        [ 63%]
tests/test_server.py::test_validate_repo_invalid PASSED                  [ 68%]
tests/test_server.py::test_load_repos_missing_file PASSED                [ 73%]
tests/test_server.py::test_save_and_load_roundtrip PASSED                [ 78%]
tests/test_server.py::test_config_dir_created_on_save PASSED             [ 84%]
tests/test_server.py::test_dashboard_html_served PASSED                  [ 89%]
tests/test_server.py::test_repos_api_crud PASSED                         [ 94%]
tests/test_server.py::test_validate_endpoint PASSED                      [100%]

============================== 19 passed in 2.84s ==============================

# checklist item cli-importable
$ ["python3", "-c", "from repo_root_tracker import find_root, NotARepositoryError"]
