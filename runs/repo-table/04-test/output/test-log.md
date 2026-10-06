
$ ["pip", "install", "-e", "."]
Obtaining file:///Users/jondev/dev/active/tools/repo-root-tracker-repo-table
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
  Created wheel for repo-root-tracker: filename=repo_root_tracker-0.1.0-py3-none-any.whl size=3410 sha256=2f04954469684c37624a9b98fb1ac89e29819ee924bc345b2e3d672d91a3a448
  Stored in directory: /private/var/folders/sk/r2ns7lvn2ygcsj7bhd0mvnyw0000gn/T/pip-ephem-wheel-cache-k0pwyag7/wheels/0c/fe/2a/909081eccd1a04be61ae0b7bccfc84befca0caec90a7608130
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
rootdir: /Users/jondev/dev/active/tools/repo-root-tracker-repo-table
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-7.1.0, agentproof-0.1.0, base-url-2.1.0, playwright-0.8.0
collecting ... collected 179 items

tests/test_default_branch_ci.py::test_no_prs_but_default_branch_fails PASSED [  0%]
tests/test_default_branch_ci.py::test_one_passing_workflow_never_masks_another_failure PASSED [  1%]
tests/test_default_branch_ci.py::test_old_success_cannot_mask_current_head_pending PASSED [  1%]
tests/test_default_branch_ci.py::test_remote_default_branch_is_used_and_encoded[trunk] PASSED [  2%]
tests/test_default_branch_ci.py::test_remote_default_branch_is_used_and_encoded[release/stable] PASSED [  2%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-success-passing] PASSED [  3%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[in_progress-None-pending] PASSED [  3%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[queued-None-pending] PASSED [  4%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[waiting-None-pending] PASSED [  5%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-failure-failing] PASSED [  5%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-timed_out-failing] PASSED [  6%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-action_required-failing] PASSED [  6%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-cancelled-unknown] PASSED [  7%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-skipped-unknown] PASSED [  7%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-neutral-unknown] PASSED [  8%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[completed-None-unknown] PASSED [  8%]
tests/test_default_branch_ci.py::test_current_head_outcomes_are_truthful[unexpected--unknown] PASSED [  9%]
tests/test_default_branch_ci.py::test_old_success_never_masks_current_failure_or_pending[failure] PASSED [ 10%]
tests/test_default_branch_ci.py::test_old_success_never_masks_current_failure_or_pending[None] PASSED [ 10%]
tests/test_default_branch_ci.py::test_latest_run_per_workflow_wins_even_if_old_run_updated_later PASSED [ 11%]
tests/test_default_branch_ci.py::test_failure_wins_over_pending_in_other_workflow PASSED [ 11%]
tests/test_default_branch_ci.py::test_success_only_on_an_older_head_is_stale PASSED [ 12%]
tests/test_default_branch_ci.py::test_no_runs_or_disabled_is_never_passing[workflows0] PASSED [ 12%]
tests/test_default_branch_ci.py::test_no_runs_or_disabled_is_never_passing[workflows1] PASSED [ 13%]
tests/test_default_branch_ci.py::test_no_runs_or_disabled_is_never_passing[workflows2] PASSED [ 13%]
tests/test_default_branch_ci.py::test_disabled_workflow_old_success_is_not_passing PASSED [ 14%]
tests/test_default_branch_ci.py::test_missing_workflow_run_is_not_hidden_by_one_success PASSED [ 15%]
tests/test_default_branch_ci.py::test_wrong_branch_head_or_pr_event_cannot_count_as_default_branch_run[bad_run0] PASSED [ 15%]
tests/test_default_branch_ci.py::test_wrong_branch_head_or_pr_event_cannot_count_as_default_branch_run[bad_run1] PASSED [ 16%]
tests/test_default_branch_ci.py::test_wrong_branch_head_or_pr_event_cannot_count_as_default_branch_run[bad_run2] PASSED [ 16%]
tests/test_default_branch_ci.py::test_wrong_branch_head_or_pr_event_cannot_count_as_default_branch_run[bad_run3] PASSED [ 17%]
tests/test_default_branch_ci.py::test_partial_gh_failure_is_explicit_and_never_passing[repo] PASSED [ 17%]
tests/test_default_branch_ci.py::test_partial_gh_failure_is_explicit_and_never_passing[head] PASSED [ 18%]
tests/test_default_branch_ci.py::test_partial_gh_failure_is_explicit_and_never_passing[workflows] PASSED [ 18%]
tests/test_default_branch_ci.py::test_partial_gh_failure_is_explicit_and_never_passing[current] PASSED [ 19%]
tests/test_default_branch_ci.py::test_partial_gh_failure_is_explicit_and_never_passing[older] PASSED [ 20%]
tests/test_default_branch_ci.py::test_confirmed_failure_survives_inventory_and_pr_query_failures PASSED [ 20%]
tests/test_default_branch_ci.py::test_bounded_incomplete_data_never_claims_passing[workflows-success-unknown] PASSED [ 21%]
tests/test_default_branch_ci.py::test_bounded_incomplete_data_never_claims_passing[workflows-failure-failing] PASSED [ 21%]
tests/test_default_branch_ci.py::test_bounded_incomplete_data_never_claims_passing[current-success-unknown] PASSED [ 22%]
tests/test_default_branch_ci.py::test_bounded_incomplete_data_never_claims_passing[current-failure-failing] PASSED [ 22%]
tests/test_default_branch_ci.py::test_cache_refresh_and_worktree_family_deduplication PASSED [ 23%]
tests/test_default_branch_ci.py::test_gh_transport_failure_uses_existing_timeout_and_error_path[timeout] PASSED [ 24%]
tests/test_default_branch_ci.py::test_gh_transport_failure_uses_existing_timeout_and_error_path[missing] PASSED [ 24%]
tests/test_default_branch_ci.py::test_gh_transport_failure_uses_existing_timeout_and_error_path[invalid-json] PASSED [ 25%]
tests/test_default_branch_ci.py::test_gh_transport_failure_uses_existing_timeout_and_error_path[denied] PASSED [ 25%]
tests/test_default_branch_ci.py::test_default_branch_ci_state_maps_the_workflow_health[<lambda>-failing] PASSED [ 26%]
tests/test_default_branch_ci.py::test_default_branch_ci_state_maps_the_workflow_health[<lambda>-passing] PASSED [ 26%]
tests/test_default_branch_ci.py::test_default_branch_ci_state_maps_the_workflow_health[<lambda>-pending] PASSED [ 27%]
tests/test_default_branch_ci.py::test_default_branch_ci_state_maps_the_workflow_health[<lambda>-unknown] PASSED [ 27%]
tests/test_default_branch_ci.py::test_default_branch_ci_is_cached_until_refreshed PASSED [ 28%]
tests/test_default_branch_ci.py::test_default_branch_ci_is_unknown_never_green_when_gh_fails[timeout] PASSED [ 29%]
tests/test_default_branch_ci.py::test_default_branch_ci_is_unknown_never_green_when_gh_fails[missing] PASSED [ 29%]
tests/test_default_branch_ci.py::test_default_branch_ci_is_unknown_never_green_when_gh_fails[invalid-json] PASSED [ 30%]
tests/test_default_branch_ci.py::test_default_branch_ci_is_unknown_never_green_when_gh_fails[denied] PASSED [ 30%]
tests/test_default_branch_ci.py::test_malformed_workflow_inventory_cannot_claim_all_passing PASSED [ 31%]
tests/test_default_branch_ci.py::test_actions_api_host_is_pinned_even_with_a_different_gh_host PASSED [ 31%]
tests/test_default_branch_ci.py::test_no_github_remote_has_no_workflow_health[None] PASSED [ 32%]
tests/test_default_branch_ci.py::test_no_github_remote_has_no_workflow_health[https://gitlab.com/owner/repo.git] PASSED [ 32%]
tests/test_default_branch_ci.py::test_github_remote_access_failure_preserves_unknown_workflow_health PASSED [ 33%]
tests/test_find_root.py::test_find_root_from_repo_root PASSED            [ 34%]
tests/test_find_root.py::test_find_root_from_subdirectory PASSED         [ 34%]
tests/test_find_root.py::test_find_root_returns_path_type PASSED         [ 35%]
tests/test_find_root.py::test_cli_from_repo_root PASSED                  [ 35%]
tests/test_find_root.py::test_cli_from_subdirectory PASSED               [ 36%]
tests/test_find_root.py::test_find_root_raises_outside_repo PASSED       [ 36%]
tests/test_find_root.py::test_cli_exits_nonzero_outside_repo PASSED      [ 37%]
tests/test_find_root.py::test_find_root_with_git_file PASSED             [ 37%]
tests/test_find_root.py::test_find_root_from_subdir_of_worktree PASSED   [ 38%]
tests/test_find_root.py::test_no_third_party_deps PASSED                 [ 39%]
tests/test_github.py::test_rollup_empty PASSED                           [ 39%]
tests/test_github.py::test_rollup_all_pass PASSED                        [ 40%]
tests/test_github.py::test_rollup_failure PASSED                         [ 40%]
tests/test_github.py::test_rollup_pending PASSED                         [ 41%]
tests/test_github.py::test_no_origin PASSED                              [ 41%]
tests/test_github.py::test_non_github_remote PASSED                      [ 42%]
tests/test_github.py::test_github_https_remote_parsed PASSED             [ 43%]
tests/test_github.py::test_github_ssh_remote_parsed PASSED               [ 43%]
tests/test_github.py::test_gh_failure_marks_unavailable PASSED           [ 44%]
tests/test_github.py::test_prs_and_issues_mapped PASSED                  [ 44%]
tests/test_github.py::test_cache_bounds_calls PASSED                     [ 45%]
tests/test_github.py::test_endpoint_no_remote PASSED                     [ 45%]
tests/test_github.py::test_endpoint_untracked_404 PASSED                 [ 46%]
tests/test_github.py::test_live_profile_is_opt_in_and_never_silently_green PASSED [ 46%]
tests/test_github.py::test_endpoint_live_github SKIPPED (live GitHub...) [ 47%]
tests/test_github_reliability.py::test_github_queries_explicitly_target_origin PASSED [ 48%]
tests/test_github_reliability.py::test_prs_beyond_one_hundred_include_blockers PASSED [ 48%]
tests/test_github_reliability.py::test_pr_coverage_bound_and_lookahead[200-False] PASSED [ 49%]
tests/test_github_reliability.py::test_pr_coverage_bound_and_lookahead[201-True] PASSED [ 49%]
tests/test_github_reliability.py::test_pr_coverage_bound_and_lookahead[250-True] PASSED [ 50%]
tests/test_github_reliability.py::test_paginated_query_failure_stays_explicit PASSED [ 50%]
tests/test_golden.py::test_every_condition_met_with_passing_ci_is_golden PASSED [ 51%]
tests/test_golden.py::test_each_condition_fails_alone[change0-on feat/x, not main] PASSED [ 51%]
tests/test_golden.py::test_each_condition_fails_alone[change1-on HEAD, not main] PASSED [ 52%]
tests/test_golden.py::test_each_condition_fails_alone[change2-1 uncommitted change] PASSED [ 53%]
tests/test_golden.py::test_each_condition_fails_alone[change3-3 uncommitted changes] PASSED [ 53%]
tests/test_golden.py::test_each_condition_fails_alone[change4-other local branch: x] PASSED [ 54%]
tests/test_golden.py::test_each_condition_fails_alone[change5-other local branches: x, y] PASSED [ 54%]
tests/test_golden.py::test_each_condition_fails_alone[change6-3 other local branches] PASSED [ 55%]
tests/test_golden.py::test_each_condition_fails_alone[change7-other remote branch: origin/x] PASSED [ 55%]
tests/test_golden.py::test_each_condition_fails_alone[change8-3 other remote branches] PASSED [ 56%]
tests/test_golden.py::test_each_condition_fails_alone[change9-origin/main not found (not fetched yet?)] PASSED [ 56%]
tests/test_golden.py::test_each_condition_fails_alone[change10-no origin remote] PASSED [ 57%]
tests/test_golden.py::test_each_condition_fails_alone[change11-1 extra worktree] PASSED [ 58%]
tests/test_golden.py::test_each_condition_fails_alone[change12-2 extra worktrees] PASSED [ 58%]
tests/test_golden.py::test_each_condition_fails_alone[change13-not even with origin/main (ahead 2, behind 0)] PASSED [ 59%]
tests/test_golden.py::test_each_condition_fails_alone[change14-not even with origin/main (ahead 0, behind 1)] PASSED [ 59%]
tests/test_golden.py::test_each_condition_fails_alone[change15-main has no upstream] PASSED [ 60%]
tests/test_golden.py::test_each_condition_fails_alone[change16-latest CI run on main failed] PASSED [ 60%]
tests/test_golden.py::test_the_first_failing_condition_is_the_headline_and_all_are_listed PASSED [ 61%]
tests/test_golden.py::test_ci_that_cannot_be_judged_is_pending_never_golden_and_never_a_failure[pending-still running] PASSED [ 62%]
tests/test_golden.py::test_ci_that_cannot_be_judged_is_pending_never_golden_and_never_a_failure[unknown-unavailable] PASSED [ 62%]
tests/test_golden.py::test_ci_that_cannot_be_judged_is_pending_never_golden_and_never_a_failure[none-no GitHub remote] PASSED [ 63%]
tests/test_golden.py::test_ci_that_cannot_be_judged_is_pending_never_golden_and_never_a_failure[unchecked-not checked] PASSED [ 63%]
tests/test_golden.py::test_failing_ci_wins_over_everything_else_being_fine PASSED [ 64%]
tests/test_golden.py::test_open_pull_requests_and_issues_are_not_inputs_at_all PASSED [ 64%]
tests/test_golden.py::test_a_detached_head_cannot_hide_behind_main_being_in_sync PASSED [ 65%]
tests/test_golden.py::test_linked_worktrees_are_judged_through_their_project PASSED [ 65%]
tests/test_golden.py::test_verdict_serializes_with_a_headline PASSED     [ 66%]
tests/test_scan.py::test_finds_repos_at_several_depths_and_does_not_descend_into_them PASSED [ 67%]
tests/test_scan.py::test_a_root_that_is_itself_a_repository_is_found PASSED [ 67%]
tests/test_scan.py::test_plain_folders_files_and_empty_trees_are_ignored PASSED [ 68%]
tests/test_scan.py::test_linked_worktrees_are_nested_under_their_project_even_when_they_live_outside_the_roots PASSED [ 68%]
tests/test_scan.py::test_a_worktree_found_first_still_reports_its_project PASSED [ 69%]
tests/test_scan.py::test_symlinks_are_never_followed_so_a_loop_cannot_hang_or_duplicate PASSED [ 69%]
tests/test_scan.py::test_a_symlink_to_a_repository_outside_the_roots_is_not_followed_out PASSED [ 70%]
tests/test_scan.py::test_build_hidden_and_dependency_folders_are_skipped PASSED [ 70%]
tests/test_scan.py::test_the_depth_limit_is_a_counted_note_not_an_alarm PASSED [ 71%]
tests/test_scan.py::test_the_entry_cap_stops_the_scan_and_says_so PASSED [ 72%]
tests/test_scan.py::test_the_time_cap_stops_the_scan_and_says_so PASSED  [ 72%]
tests/test_scan.py::test_missing_roots_are_reported_and_other_roots_still_scan PASSED [ 73%]
tests/test_scan.py::test_overlapping_roots_do_not_duplicate_repos PASSED [ 73%]
tests/test_scan.py::test_unreadable_folders_are_skipped_not_fatal PASSED [ 74%]
tests/test_scan.py::test_roots_come_from_the_environment_then_the_default PASSED [ 74%]
tests/test_scan.py::test_results_are_sorted_and_serializable PASSED      [ 75%]
tests/test_sdlc_install.py::InstalledWorkflowTest::test_later_failed_mark_invalidates_verification PASSED [ 75%]
tests/test_server.py::test_binds_loopback_only PASSED                    [ 76%]
tests/test_server.py::test_the_page_is_small_self_contained_and_locked_down PASSED [ 77%]
tests/test_server.py::test_scan_then_status_flow PASSED                  [ 77%]
tests/test_server.py::test_only_paths_the_scan_found_can_be_queried PASSED [ 78%]
tests/test_server.py::test_hosts_other_than_loopback_are_refused PASSED  [ 78%]
tests/test_server.py::test_cross_site_posts_are_refused_and_local_ones_allowed PASSED [ 79%]
tests/test_server.py::test_the_old_registration_organization_and_detail_endpoints_are_gone PASSED [ 79%]
tests/test_server.py::test_rescan_picks_up_a_new_repo_and_the_old_scan_is_replaced PASSED [ 80%]
tests/test_server.py::test_a_repo_deleted_after_the_scan_is_gone_not_clean PASSED [ 81%]
tests/test_server.py::test_ci_state_feeds_the_golden_verdict_on_later_status_calls PASSED [ 81%]
tests/test_server.py::test_fetch_updates_remote_refs_and_returns_fresh_status PASSED [ 82%]
tests/test_server.py::test_fetch_failure_is_reported_not_hidden PASSED   [ 82%]
tests/test_server.py::test_missing_root_is_reported_on_the_scan PASSED   [ 83%]
tests/test_server.py::test_no_password_or_remote_access_settings_exist_anymore PASSED [ 83%]
tests/test_status.py::test_a_fresh_pushed_main_has_every_local_golden_fact PASSED [ 84%]
tests/test_status.py::test_to_dict_carries_the_verdict_and_the_dirty_total PASSED [ 84%]
tests/test_status.py::test_an_extra_remote_branch_makes_it_not_golden PASSED [ 85%]
tests/test_status.py::test_an_extra_local_branch_and_being_off_main PASSED [ 86%]
tests/test_status.py::test_ahead_and_behind_come_from_the_upstream PASSED [ 86%]
tests/test_status.py::test_no_origin_and_no_upstream PASSED              [ 87%]
tests/test_status.py::test_extra_worktrees_are_counted_for_the_main_checkout_and_the_worktree_is_not_judged PASSED [ 87%]
tests/test_status.py::test_a_repo_with_no_commits_does_not_crash PASSED  [ 88%]
tests/test_status.py::test_a_missing_path_is_an_error_not_a_clean_repo PASSED [ 88%]
tests/test_status.py::test_reading_status_never_writes_to_the_repository PASSED [ 89%]
tests/test_status.py::test_fetch_updates_remote_refs_and_only_remote_refs PASSED [ 89%]
tests/test_status.py::test_fetch_prunes_deleted_remote_branches PASSED   [ 90%]
tests/test_status.py::test_fetch_failure_is_an_error_and_never_hangs PASSED [ 91%]
tests/test_status.py::test_ci_is_none_when_there_is_no_github_remote PASSED [ 91%]
tests/test_ui.py::test_every_repo_appears_with_a_verdict_in_words PASSED [ 92%]
tests/test_ui.py::test_default_order_puts_what_needs_attention_first PASSED [ 92%]
tests/test_ui.py::test_search_and_filters PASSED                         [ 93%]
tests/test_ui.py::test_a_row_expands_with_reasons_branches_and_path_and_is_keyboard_operable PASSED [ 93%]
tests/test_ui.py::test_check_github_turns_a_pending_repo_golden_and_never_rescues_the_others PASSED [ 94%]
tests/test_ui.py::test_fetch_all_reveals_a_branch_pushed_elsewhere PASSED [ 94%]
tests/test_ui.py::test_rescan_finds_a_new_repo PASSED                    [ 95%]
tests/test_ui.py::test_verdicts_do_not_rely_on_color PASSED              [ 96%]
tests/test_ui.py::test_no_horizontal_scroll_on_a_phone PASSED            [ 96%]
tests/test_ui.py::test_nothing_leaves_the_machine PASSED                 [ 97%]
tests/test_ui.py::test_both_color_schemes_render_with_readable_contrast PASSED [ 97%]
tests/test_ui.py::test_the_page_is_light_and_fast PASSED                 [ 98%]
tests/test_ui.py::test_an_unreadable_status_shows_in_the_row_not_a_blank PASSED [ 98%]
tests/test_ui.py::test_the_page_runs_cleanly_under_its_own_strict_policy PASSED [ 99%]
tests/test_ui.py::test_hostile_text_in_git_data_is_shown_as_text_and_never_runs PASSED [100%]

======================= 178 passed, 1 skipped in 38.26s ========================

# checklist item scan
$ ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_scan.py"]
................                                                         [100%]
16 passed in 1.51s

# checklist item golden
$ ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_golden.py"]
............................                                             [100%]
28 passed in 0.01s

# checklist item status
$ ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_status.py"]
..............                                                           [100%]
14 passed in 5.16s

# checklist item server
$ ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_server.py"]
..............                                                           [100%]
14 passed in 9.49s

# checklist item ui
$ ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_ui.py"]
...............                                                          [100%]
15 passed in 20.20s

# checklist item page-weight
$ ["python3", "-B", "-c", "import re,pathlib;p=pathlib.Path('src/repo_root_tracker/dashboard.html');s=p.read_text();assert len(s.encode())<61440,len(s.encode());assert 'data:image' not in s;assert not re.search(r'(src|href)=[\"\\']https?://',s)"]

# checklist item full-suite
$ ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"]
........................................................................ [ 40%]
............s........................................................... [ 80%]
...................................                                      [100%]
178 passed, 1 skipped in 38.66s
