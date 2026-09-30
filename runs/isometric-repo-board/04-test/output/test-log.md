
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
  Stored in directory: /private/var/folders/sk/r2ns7lvn2ygcsj7bhd0mvnyw0000gn/T/pip-ephem-wheel-cache-71xvfnj5/wheels/59/4f/16/862fe7aee12d0c22486bd297d27902a281d2cf9afa2d7ea0d4
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
collecting ... collected 140 items

tests/test_board.py::test_board_routes PASSED                            [  0%]
tests/test_board.py::test_board_tile_count_and_order PASSED              [  1%]
tests/test_board.py::test_board_stage_mapping PASSED                     [  2%]
tests/test_board.py::test_board_upstream_badge PASSED                    [  2%]
tests/test_board.py::test_board_stage_precedence PASSED                  [  3%]
tests/test_board.py::test_board_keyboard_nav PASSED                      [  4%]
tests/test_board.py::test_board_focus_visible PASSED                     [  5%]
tests/test_board.py::test_board_pin_marker PASSED                        [  5%]
tests/test_board.py::test_board_tile_link_href PASSED                    [  6%]
tests/test_board.py::test_board_tile_a11y_names PASSED                   [  7%]
tests/test_board.py::test_board_reduced_motion PASSED                    [  7%]
tests/test_board.py::test_board_refresh PASSED                           [  8%]
tests/test_board.py::test_board_empty_state PASSED                       [  9%]
tests/test_board.py::test_board_pager_layout PASSED                      [ 10%]
tests/test_board.py::test_board_pager_reset PASSED                       [ 10%]
tests/test_board.py::test_board_pager_persist PASSED                     [ 11%]
tests/test_board.py::test_board_first_paint PASSED                       [ 12%]
tests/test_board.py::test_board_palette_command PASSED                   [ 12%]
tests/test_board.py::test_board_worktree_labels PASSED                   [ 13%]
tests/test_dashboard.py::test_name_first_search_filters_and_escaped_paths PASSED [ 14%]
tests/test_dashboard.py::test_pins_collections_collapse_and_reload PASSED [ 15%]
tests/test_dashboard.py::test_collection_rename_delete_and_duplicate_validation PASSED [ 15%]
tests/test_dashboard.py::test_storage_failure_and_corrupt_preferences_are_visible PASSED [ 16%]
tests/test_dashboard.py::test_keyboard_focus_and_mobile_layout PASSED    [ 17%]
tests/test_dashboard.py::test_status_response_does_not_update_shifted_repo PASSED [ 17%]
tests/test_dashboard.py::test_repo_links_keep_detail_navigation PASSED   [ 18%]
tests/test_dashboard.py::test_recent_sort_empty_state_and_status_menu_refresh PASSED [ 19%]
tests/test_dashboard.py::test_removal_cancellation_and_path_identity PASSED [ 20%]
tests/test_dashboard.py::test_search_expands_matches_without_overwriting_collapsed_groups PASSED [ 20%]
tests/test_dashboard.py::test_collection_feedback_and_pinned_membership PASSED [ 21%]
tests/test_dashboard.py::test_bulk_assignment_includes_explicitly_selected_hidden_matches PASSED [ 22%]
tests/test_dashboard.py::test_git_metadata_nests_worktrees_and_project_grouping PASSED [ 22%]
tests/test_dashboard.py::test_github_attention_deduplicates_and_preserves_partial_errors PASSED [ 23%]
tests/test_dashboard.py::test_change_expanders_have_truthful_labels_and_keyboard_access PASSED [ 24%]
tests/test_dashboard.py::test_home_shortening_guard_is_preserved PASSED  [ 25%]
tests/test_dashboard.py::test_detail_loading_clears_old_counts_and_ignores_late_responses PASSED [ 25%]
tests/test_dashboard.py::test_return_refreshes_stale_local_data_without_enabling_github PASSED [ 26%]
tests/test_dashboard.py::test_return_refresh_does_not_interrupt_or_refresh_fresh_data[fresh] PASSED [ 27%]
tests/test_dashboard.py::test_return_refresh_does_not_interrupt_or_refresh_fresh_data[detail] PASSED [ 27%]
tests/test_dashboard.py::test_return_refresh_does_not_interrupt_or_refresh_fresh_data[dialog] PASSED [ 28%]
tests/test_dashboard.py::test_return_refresh_does_not_interrupt_or_refresh_fresh_data[organizing] PASSED [ 29%]
tests/test_dashboard.py::test_return_refresh_does_not_interrupt_or_refresh_fresh_data[busy] PASSED [ 30%]
tests/test_dashboard.py::test_return_refresh_does_not_interrupt_or_refresh_fresh_data[hidden] PASSED [ 30%]
tests/test_dashboard.py::test_focus_and_visibility_coalesce_bounded_opted_in_refresh[events0] PASSED [ 31%]
tests/test_dashboard.py::test_focus_and_visibility_coalesce_bounded_opted_in_refresh[events1] PASSED [ 32%]
tests/test_dashboard.py::test_focus_and_visibility_coalesce_bounded_opted_in_refresh[events2] PASSED [ 32%]
tests/test_dashboard.py::test_pr_truncation_uses_reported_coverage_limit PASSED [ 33%]
tests/test_dashboard.py::test_return_checks_stale_cached_github_and_backs_off_after_failure PASSED [ 34%]
tests/test_dashboard_metadata.py::test_change_kinds[ D-deleted] PASSED   [ 35%]
tests/test_dashboard_metadata.py::test_change_kinds[D -deleted] PASSED   [ 35%]
tests/test_dashboard_metadata.py::test_change_kinds[A -added] PASSED     [ 36%]
tests/test_dashboard_metadata.py::test_change_kinds[ M-modified] PASSED  [ 37%]
tests/test_dashboard_metadata.py::test_change_kinds[ T-type changed] PASSED [ 37%]
tests/test_dashboard_metadata.py::test_change_kinds[UU-conflicted] PASSED [ 38%]
tests/test_dashboard_metadata.py::test_change_kinds[AA-conflicted] PASSED [ 39%]
tests/test_dashboard_metadata.py::test_change_kinds[DD-conflicted] PASSED [ 40%]
tests/test_dashboard_metadata.py::test_change_kinds[??-untracked] PASSED [ 40%]
tests/test_dashboard_metadata.py::test_deleted_file_is_not_labeled_modified PASSED [ 41%]
tests/test_dashboard_metadata.py::test_rename_paths_keep_special_characters PASSED [ 42%]
tests/test_dashboard_metadata.py::test_conflict_from_real_git_merge PASSED [ 42%]
tests/test_dashboard_metadata.py::test_worktree_family_is_from_git_not_name PASSED [ 43%]
tests/test_dashboard_metadata.py::test_pending_check_does_not_hide_failure PASSED [ 44%]
tests/test_dashboard_metadata.py::test_legacy_github_status_contexts PASSED [ 45%]
tests/test_dashboard_metadata.py::test_github_partial_failure_is_explicit_and_refresh_bypasses_cache PASSED [ 45%]
tests/test_dashboard_metadata.py::test_github_cache_deduplicates_worktrees_and_maps_review_signals PASSED [ 46%]
tests/test_dashboard_metadata.py::test_home_template_substitutes_only_the_value PASSED [ 47%]
tests/test_dashboard_metadata.py::test_last_fetch_time_uses_each_checkouts_git_path PASSED [ 47%]
tests/test_detail.py::test_detail_commits PASSED                         [ 48%]
tests/test_detail.py::test_detail_lanes_assigned PASSED                  [ 49%]
tests/test_detail.py::test_detail_branches PASSED                        [ 50%]
tests/test_detail.py::test_detail_remote_branches PASSED                 [ 50%]
tests/test_detail.py::test_detail_no_remotes_section_when_none PASSED    [ 51%]
tests/test_detail.py::test_detail_changed_files_clean PASSED             [ 52%]
tests/test_detail.py::test_detail_changed_files_dirty PASSED             [ 52%]
tests/test_detail.py::test_commit_diff PASSED                            [ 53%]
tests/test_detail.py::test_commit_diff_rejects_bad_hash PASSED           [ 54%]
tests/test_detail.py::test_working_diff PASSED                           [ 55%]
tests/test_detail.py::test_working_diff_rejects_traversal PASSED         [ 55%]
tests/test_detail.py::test_repo_endpoint PASSED                          [ 56%]
tests/test_detail.py::test_repo_endpoint_untracked_404 PASSED            [ 57%]
tests/test_detail.py::test_commit_endpoint PASSED                        [ 57%]
tests/test_detail.py::test_working_diff_endpoint PASSED                  [ 58%]
tests/test_detail.py::test_detail_missing_dir_raises PASSED              [ 59%]
tests/test_detail.py::test_working_diff_labels_staged_sections PASSED    [ 60%]
tests/test_find_root.py::test_find_root_from_repo_root PASSED            [ 60%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 61%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 62%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 62%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 63%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 64%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 65%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 65%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 66%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 67%]
tests/test_github.py::test_rollup_empty PASSED                           [ 67%]
tests/test_github.py::test_rollup_all_pass PASSED                        [ 68%]
tests/test_github.py::test_rollup_failure PASSED                         [ 69%]
tests/test_github.py::test_rollup_pending PASSED                         [ 70%]
tests/test_github.py::test_no_origin PASSED                              [ 70%]
tests/test_github.py::test_non_github_remote PASSED                      [ 71%]
tests/test_github.py::test_github_https_remote_parsed PASSED             [ 72%]
tests/test_github.py::test_github_ssh_remote_parsed PASSED               [ 72%]
tests/test_github.py::test_gh_failure_marks_unavailable PASSED           [ 73%]
tests/test_github.py::test_prs_and_issues_mapped PASSED                  [ 74%]
tests/test_github.py::test_cache_bounds_calls PASSED                     [ 75%]
tests/test_github.py::test_endpoint_no_remote PASSED                     [ 75%]
tests/test_github.py::test_endpoint_untracked_404 PASSED                 [ 76%]
tests/test_github.py::test_endpoint_live_github PASSED                   [ 77%]
tests/test_github_reliability.py::test_github_queries_explicitly_target_origin PASSED [ 77%]
tests/test_github_reliability.py::test_prs_beyond_one_hundred_include_blockers PASSED [ 78%]
tests/test_github_reliability.py::test_pr_coverage_bound_and_lookahead[200-False] PASSED [ 79%]
tests/test_github_reliability.py::test_pr_coverage_bound_and_lookahead[201-True] PASSED [ 80%]
tests/test_github_reliability.py::test_pr_coverage_bound_and_lookahead[250-True] PASSED [ 80%]
tests/test_github_reliability.py::test_paginated_query_failure_stays_explicit PASSED [ 81%]
tests/test_server.py::test_validate_repo_valid PASSED                    [ 82%]
tests/test_server.py::test_validate_repo_from_subdirectory PASSED        [ 82%]
tests/test_server.py::test_validate_repo_invalid PASSED                  [ 83%]
tests/test_server.py::test_load_repos_missing_file PASSED                [ 84%]
tests/test_server.py::test_save_and_load_roundtrip PASSED                [ 85%]
tests/test_server.py::test_config_dir_created_on_save PASSED             [ 85%]
tests/test_server.py::test_dashboard_html_served PASSED                  [ 86%]
tests/test_server.py::test_repos_api_crud PASSED                         [ 87%]
tests/test_server.py::test_validate_endpoint PASSED                      [ 87%]
tests/test_server.py::test_deleted_repo_returns_410_gone PASSED          [ 88%]
tests/test_server.py::test_malformed_repos_entries_filtered PASSED       [ 89%]
tests/test_server.py::test_malformed_repos_file_shapes PASSED            [ 90%]
tests/test_server.py::test_dashboard_home_value_is_json_encoded_and_guard_preserved PASSED [ 90%]
tests/test_server.py::test_non_git_directory_is_not_reported_as_clean PASSED [ 91%]
tests/test_server.py::test_github_refresh_is_explicit PASSED             [ 92%]
tests/test_status.py::test_branch_and_last_commit PASSED                 [ 92%]
tests/test_status.py::test_clean_repo_is_clean PASSED                    [ 93%]
tests/test_status.py::test_modified_and_untracked_counts PASSED          [ 94%]
tests/test_status.py::test_staged_counts PASSED                          [ 95%]
tests/test_status.py::test_no_upstream PASSED                            [ 95%]
tests/test_status.py::test_ahead_of_upstream PASSED                      [ 96%]
tests/test_status.py::test_no_stale_branches_on_fresh_repo PASSED        [ 97%]
tests/test_status.py::test_stale_branch_detected PASSED                  [ 97%]
tests/test_status.py::test_status_endpoint_tracked PASSED                [ 98%]
tests/test_status.py::test_status_endpoint_untracked_404 PASSED          [ 99%]
tests/test_status.py::test_status_missing_dir_raises PASSED              [100%]

============================= 140 passed in 52.98s =============================

# checklist item board-routes
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_routes", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_routes PASSED                            [100%]

======================= 1 passed, 18 deselected in 0.62s =======================

# checklist item board-tiles
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_tile_count_and_order", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_tile_count_and_order PASSED              [100%]

======================= 1 passed, 18 deselected in 0.48s =======================

# checklist item stage-mapping
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_stage_mapping or test_board_upstream_badge", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 17 deselected / 2 selected

tests/test_board.py::test_board_stage_mapping PASSED                     [ 50%]
tests/test_board.py::test_board_upstream_badge PASSED                    [100%]

======================= 2 passed, 17 deselected in 0.88s =======================

# checklist item stage-precedence
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_stage_precedence", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_stage_precedence PASSED                  [100%]

======================= 1 passed, 18 deselected in 0.45s =======================

# checklist item tile-access
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_keyboard_nav or test_board_focus_visible or test_board_pin_marker or test_board_tile_link_href or test_board_tile_a11y_names or test_board_reduced_motion", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 13 deselected / 6 selected

tests/test_board.py::test_board_keyboard_nav PASSED                      [ 16%]
tests/test_board.py::test_board_focus_visible PASSED                     [ 33%]
tests/test_board.py::test_board_pin_marker PASSED                        [ 50%]
tests/test_board.py::test_board_tile_link_href PASSED                    [ 66%]
tests/test_board.py::test_board_tile_a11y_names PASSED                   [ 83%]
tests/test_board.py::test_board_reduced_motion PASSED                    [100%]

======================= 6 passed, 13 deselected in 2.66s =======================

# checklist item board-refresh
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_refresh", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_refresh PASSED                           [100%]

====================== 1 passed, 18 deselected in 10.93s =======================

# checklist item board-empty-state
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_empty_state", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_empty_state PASSED                       [100%]

======================= 1 passed, 18 deselected in 0.45s =======================

# checklist item board-pager
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_pager_layout or test_board_pager_reset or test_board_pager_persist", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 16 deselected / 3 selected

tests/test_board.py::test_board_pager_layout PASSED                      [ 33%]
tests/test_board.py::test_board_pager_reset PASSED                       [ 66%]
tests/test_board.py::test_board_pager_persist PASSED                     [100%]

======================= 3 passed, 16 deselected in 1.59s =======================

# checklist item board-first-paint
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_first_paint", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_first_paint PASSED                       [100%]

======================= 1 passed, 18 deselected in 0.47s =======================

# checklist item board-palette
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_palette_command", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_palette_command PASSED                   [100%]

======================= 1 passed, 18 deselected in 0.48s =======================

# checklist item board-worktree-labels
$ ["python3", "-m", "pytest", "tests/test_board.py", "-k", "test_board_worktree_labels", "-v"]
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- /Users/jondev/.pyenv/versions/3.13.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jondev/dev/active/repo-root-tracker
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 19 items / 18 deselected / 1 selected

tests/test_board.py::test_board_worktree_labels PASSED                   [100%]

======================= 1 passed, 18 deselected in 0.44s =======================
