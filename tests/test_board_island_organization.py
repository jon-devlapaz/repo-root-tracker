"""P2.1/P2.2: shared project assignments, List actions, and read-time migration.

These tests load the production dashboard without needing the later Board island UI.
"""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, quote, urlparse

import pytest

from organization_fake import OrganizationFake

playwright = pytest.importorskip("playwright.sync_api")
DASHBOARD = Path(__file__).parents[1] / "src/repo_root_tracker/dashboard.html"
KEY = "repo-root-tracker.organization.v1"
IDENTITY_KEY = "repo-root-tracker.project-identities.v1"
MAIN = "/projects/oak"
WT_A = "/worktrees/oak-a"
WT_B = "/other/oak-b"
STALE = "/untracked/oak-old"
PROJECT_ID = MAIN + "/.git"
PROJECT_KEY = "project:git:" + quote(PROJECT_ID, safe="")
UNTRACKED_KEY = "project:git:%2Funtracked%2F.git"
COLLECTIONS = [{"id": "work", "name": "Work"}, {"id": "personal", "name": "Personal"}]


def identity(path):
    return {"project_id": PROJECT_ID, "project_path": MAIN, "is_worktree": path != MAIN}


def settled(page):
    page.evaluate("() => organizationQueue")  # Playwright awaits the queue promise.
    page.wait_for_function("initialLocalBatchSettled && repos.every(r => r._status && !r._checking)")


def puts(fake):
    return [payload for method, payload in fake.requests if method == "PUT"]


def placement(page):
    return page.evaluate("boardProjects.map(project => projectCollectionId(project, organization))")


@pytest.fixture
def workspace():
    fake = OrganizationFake()
    state = SimpleNamespace(fake=fake, paths=[MAIN, WT_A, WT_B], fail_status=False, requests=[])
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        contexts, errors = [], []

        def open_page(assignments=None, grouping="collection", saved=None, cached=False, missing=False, pins=None):
            fake.state.update(revision=0 if missing else 1, exists=not missing,
                              collections=[] if missing else deepcopy(COLLECTIONS),
                              assignments=deepcopy(assignments or {}), grouping=grouping, pins=list(pins or []))
            context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
            contexts.append(context)
            copies = {}
            if saved is not None:
                copies[KEY] = saved
            if cached:
                copies[IDENTITY_KEY] = {"version": 1, "entries": {path: identity(path) for path in state.paths}}
            if copies:
                context.add_init_script("for (const [key,value] of Object.entries(" + json.dumps(copies) +
                                        ")) if (localStorage.getItem(key) === null) localStorage.setItem(key,JSON.stringify(value));")
            context.route("http://dashboard.test/", lambda route: route.fulfill(
                content_type="text/html", body=DASHBOARD.read_text().replace("__HOME__", "/home/test", 1)))
            context.route("**/api/organization", fake.route)

            def registry(route):
                state.requests.append((route.request.method, route.request.url))
                if route.request.method == "POST":
                    path = route.request.post_data_json["path"]
                    state.paths.append(path)
                    route.fulfill(status=201, json={"path": path})
                else:
                    route.fulfill(json=[{"path": path} for path in state.paths])

            def status(route):
                state.requests.append((route.request.method, route.request.url))
                path = parse_qs(urlparse(route.request.url).query)["path"][0]
                if state.fail_status:
                    route.fulfill(status=503, json={"error": "Local Git unavailable"})
                else:
                    route.fulfill(json={**identity(path), "branch": "main" if path == MAIN else "feature",
                                        "dirty": {"is_clean": True}, "sync": {"has_upstream": False}})

            context.route("**/api/repos", registry)
            context.route("**/api/repos/status?*", status)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://dashboard.test/#/list")
            settled(page)
            return page

        state.open_page = open_page
        yield state
        for context in contexts:
            context.close()
        browser.close()
        assert errors == []


@pytest.fixture
def page(workspace):
    return workspace.open_page()


@pytest.mark.parametrize("canonical,expected", [("personal", "personal"), ("", None), ("missing-island", None)])
def test_canonical_project_assignment_wins_over_path_aliases(workspace, canonical, expected):
    assignments = {PROJECT_KEY: canonical, MAIN: "work", WT_A: "work"}
    page = workspace.open_page(assignments)
    assert placement(page) == [expected]
    result = page.evaluate("projectCollectionResolution(boardProjects[0], organization)")
    assert result["source"] == "canonical" and result["rawValue"] == canonical
    assert bool(result["warning"]) == (canonical == "missing-island")
    for index in range(3):
        assert page.locator(f"#collection-{index}").input_value() == (expected or "")
    if canonical == "missing-island":
        page.locator("#card-0 summary").click()
        assert "Unknown collection" in page.locator("#card-0 .menu-panel").inner_text()
    assert page.evaluate("organization.assignments") == assignments
    assert puts(workspace.fake) == []


def test_project_path_key_uses_encode_uri_component_for_standalone(page):
    result = page.evaluate("""() => {
      const project = {projectId:null, defaultPath:'/plain/a b#c', paths:['/plain/a b#c'], mainPath:null, mainRepoPath:null, centralRepoPath:'/plain/a b#c'};
      const snapshot = organizationSnapshot();
      setProjectCollection(snapshot, project, 'work');
      const custom = projectCollectionId(project, snapshot);
      setProjectCollection(snapshot, project, null);
      return {key:projectAssignmentKey(project), custom, assignments:snapshot.assignments, workspace:projectCollectionId(project,snapshot)};
    }""")
    assert result == {"key": "project:path:%2Fplain%2Fa%20b%23c", "custom": "work",
                      "assignments": {"project:path:%2Fplain%2Fa%20b%23c": ""}, "workspace": None}


def test_legacy_worktree_assignment_lifts_to_whole_project_without_put(workspace):
    assignments = {WT_A: "work", "/unrelated": "personal"}
    page = workspace.open_page(assignments)
    assert placement(page) == ["work"]
    group = page.locator(".collection").filter(has=page.locator('[id="toggle-collection%3Awork"]'))
    assert group.locator(".repo-card").count() == 3
    assert page.locator(".project-family .repo-card").count() == 3
    assert [page.locator(f"#collection-{i}").input_value() for i in range(3)] == ["work"] * 3
    assert workspace.fake.state["assignments"] == assignments
    assert puts(workspace.fake) == []


@pytest.mark.parametrize("main,expected", [("personal", "personal"), ("", None), ("missing-island", "work"), (None, "work")])
def test_conflicting_legacy_assignments_use_main_then_collection_order(workspace, main, expected):
    # Exact member ordering favours Personal; collection ordering must favour Work instead.
    assignments = {WT_A: "work", WT_B: "personal", "/unrelated": "personal"}
    if main is not None:
        assignments[MAIN] = main
    page = workspace.open_page(assignments)
    result = page.evaluate("projectCollectionResolution(boardProjects[0], organization)")
    assert placement(page) == [expected]
    assert "Conflicting checkout assignments" in result["warning"]
    assert set(result["conflictingAliases"]) >= {WT_A, WT_B}
    if main is None:
        page.evaluate("organization.collections.reverse(); render();")
        assert placement(page) == ["personal"]
    assert page.evaluate("organization.assignments") == assignments
    assert puts(workspace.fake) == []


def test_untracked_main_alias_wins_but_unrelated_untracked_alias_does_not(workspace):
    workspace.paths = [WT_A, WT_B]
    page = workspace.open_page({MAIN: "personal", WT_A: "work", STALE: "work"})
    assert placement(page) == ["personal"]
    page.evaluate("delete organization.assignments[repos[0]._status.project_path]; delete organization.assignments[repos[0].path]; render();")
    assert placement(page) == [None]  # STALE is not a tracked member.
    assert puts(workspace.fake) == []
    page.evaluate("() => assignCollection(0,'personal')")
    assert workspace.fake.state["assignments"] == {PROJECT_KEY: "personal", MAIN: "personal", WT_A: "personal", WT_B: "personal", STALE: "work"}
    page.evaluate("() => assignCollection(0,'')")
    assert workspace.fake.state["assignments"] == {PROJECT_KEY: "", STALE: "work"}


def test_workspace_move_blocks_untracked_worktree_alias_after_retracking_and_reload(workspace):
    workspace.paths = [MAIN, WT_A]
    page = workspace.open_page({MAIN: "work", WT_A: "work", STALE: "work"})
    page.locator("#card-1 summary").click()
    page.locator("#collection-1").select_option("")
    settled(page)
    assert workspace.fake.state["assignments"] == {PROJECT_KEY: "", STALE: "work"}
    page.get_by_label("Repository path to track").fill(STALE)
    page.locator("#add-btn").click()
    page.wait_for_function("repos.length === 3 && repos.every(r => r._status && !r._checking)")
    assert placement(page) == [None]
    page.reload()
    settled(page)
    assert placement(page) == [None]
    assert [page.locator(f"#collection-{i}").input_value() for i in range(3)] == [""] * 3
    assert workspace.fake.state["assignments"][STALE] == "work"
    assert len(puts(workspace.fake)) == 1


def test_delete_work_does_not_expose_personal_alias_after_reload(workspace):
    assignments = {MAIN: "work", WT_A: "personal", STALE: "work", UNTRACKED_KEY: "work",
                   "project:path:%2Funtracked-standalone": "work", "/unknown": "removed-island"}
    page = workspace.open_page(assignments, pins=[WT_A])
    page.evaluate("organization.collapsed=['collection:work','collection:personal']; storeLocalOrganization();")
    tracked = page.evaluate("repos.map(r => r.path)")
    requests_before = list(workspace.requests)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete collection Work", exact=True).click()
    settled(page)
    assert placement(page) == [None]
    assert workspace.requests == requests_before  # Organization deletion never calls repo APIs.
    assert page.evaluate("repos.map(r => r.path)") == tracked
    assert workspace.fake.state["pins"] == [WT_A]
    assert workspace.fake.state["assignments"] == {
        PROJECT_KEY: "", UNTRACKED_KEY: "", "project:path:%2Funtracked-standalone": "", "/unknown": "removed-island"}
    assert page.evaluate("organization.collapsed") == ["collection:personal"]
    page.reload()
    settled(page)
    assert placement(page) == [None]
    assert workspace.fake.state["collections"] == [COLLECTIONS[1]]
    assert len(puts(workspace.fake)) == 1


def test_identity_discovery_and_assignment_interpretation_do_not_put(page, workspace):
    workspace.fake.state["assignments"] = {WT_A: "work"}
    page.reload()
    settled(page)
    result = page.evaluate("""() => {
      const statuses = repos.map(r => ({...r._status}));
      repoIdentities.clear(); metadataObservedPaths.clear();
      repos.forEach(r => {r._status=null;}); rebuildProjectModel();
      const before = boardProjects.length;
      repos.forEach((r,i) => rememberRepoMetadata(r.path,statuses[i]));
      return {before, after:boardProjects.length, placement:projectCollectionId(boardProjects[0],organization)};
    }""")
    assert result == {"before": 3, "after": 1, "placement": "work"}
    page.evaluate("location.hash='#/board'")
    playwright.expect(page.locator("#board-view")).to_be_visible()
    page.wait_for_function("boardScene !== null")
    page.evaluate("boardProjects.forEach(p => projectCollectionResolution(p,organization)); renderBoard();")
    assert puts(workspace.fake) == []
    assert workspace.fake.state["assignments"] == {WT_A: "work"}


def test_browser_migration_put_remains_exempt(workspace):
    assignments = {WT_A: "work", STALE: "work"}
    saved = {"pins": [], "collections": deepcopy(COLLECTIONS), "assignments": assignments,
             "grouping": "collection", "sort": "name", "collapsed": [], "githubEnabled": False}
    page = workspace.open_page(saved=saved, missing=True)
    assert placement(page) == ["work"]
    assert len(puts(workspace.fake)) == 1
    assert puts(workspace.fake)[0]["assignments"] == assignments  # No opportunistic normalization.
    page.reload()
    settled(page)
    assert len(puts(workspace.fake)) == 1


def test_valid_pending_recovery_put_remains_exempt(page, workspace):
    workspace.fake.fail_puts = 1
    page.evaluate("() => assignCollection(1, 'work')")
    assert workspace.fake.state["revision"] == 1
    pending = page.evaluate("JSON.parse(localStorage.getItem(PENDING_ORGANIZATION_KEY)).pending")
    assert pending["base_revision"] == 1 and pending["organization"]["assignments"][PROJECT_KEY] == "work"
    page.reload()
    settled(page)
    assert placement(page) == ["work"]
    assert len(puts(workspace.fake)) == 2
    assert puts(workspace.fake)[0] == puts(workspace.fake)[1]
    assert workspace.fake.state["revision"] == 2
    assert page.evaluate("localStorage.getItem(PENDING_ORGANIZATION_KEY)") is None


@pytest.mark.parametrize("grouping", ["collection", "folder", "project", "none"])
def test_list_first_assignment_and_bulk_move_use_whole_projects_in_every_grouping_mode(workspace, grouping):
    workspace.fail_status = True
    page = workspace.open_page(grouping=grouping, cached=True, pins=[WT_A])
    assert page.evaluate("boardScene === null && boardProjects.length === 1 && repos.every(r => r._status.error)")
    # Assign from a worktree menu before Board has ever rendered.
    page.locator("#card-2 summary").click()
    page.locator("#collection-2").select_option("work")
    settled(page)
    assert workspace.fake.state["assignments"] == {PROJECT_KEY: "work", MAIN: "work", WT_A: "work", WT_B: "work"}
    assert workspace.fake.state["pins"] == [WT_A]
    assert [page.locator(f"#collection-{i}").input_value() for i in range(3)] == ["work"] * 3
    if grouping == "collection":
        assert "1 pinned above" in page.locator('[id="toggle-collection%3Awork"]').inner_text()
        assert page.locator(".project-family .repo-card").count() == 2
    page.get_by_role("button", name="Organize repos", exact=True).click()
    page.get_by_role("button", name="Select matching", exact=True).click()
    page.get_by_label("Collection for selected repos").select_option("personal")
    # Observe calls to the production setter: three selected paths must produce one project edit.
    page.evaluate("""() => {
      window.projectWrites=0; const original=setProjectCollection;
      setProjectCollection=(...args)=>{window.projectWrites++; return original(...args);};
    }""")
    page.get_by_role("button", name="Move selected", exact=True).click()
    settled(page)
    assert page.evaluate("projectWrites") == 1
    assert placement(page) == ["personal"]
    assert all(value == "personal" for value in workspace.fake.state["assignments"].values())
    assert len(puts(workspace.fake)) == 2
    page.reload()
    settled(page)
    assert placement(page) == ["personal"]
    assert page.evaluate("boardScene === null && organization.pins") == [WT_A]
    assert [page.locator(f"#collection-{i}").input_value() for i in range(3)] == ["personal"] * 3
    # The existing bulk Workspace choice also writes one canonical marker for the whole family.
    page.get_by_role("button", name="Organize repos", exact=True).click()
    page.get_by_role("button", name="Select matching", exact=True).click()
    page.get_by_label("Collection for selected repos").select_option("unsorted")
    page.get_by_role("button", name="Move selected", exact=True).click()
    settled(page)
    assert workspace.fake.state["assignments"] == {PROJECT_KEY: ""}
    assert workspace.fake.state["pins"] == [WT_A]


def test_unknown_paths_and_collection_ids_survive_island_edits(workspace):
    unknown = {"/unknown": "deleted-island", "/untracked-personal": "personal",
               "project:path:%2Funknown": "deleted-island"}
    page = workspace.open_page({**unknown, STALE: "work"})
    page.evaluate("() => assignCollection(1,'work')")
    page.get_by_role("button", name="+ Collection", exact=True).click()
    page.get_by_label("Collection name", exact=True).fill(" Experiments ")
    page.get_by_role("button", name="Save collection", exact=True).click()
    settled(page)
    page.get_by_role("button", name="Rename Experiments", exact=True).click()
    page.get_by_label("Collection name", exact=True).fill("Research")
    page.get_by_role("button", name="Save collection", exact=True).click()
    settled(page)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete collection Work", exact=True).click()
    settled(page)
    assert workspace.fake.state["assignments"] == {**unknown, PROJECT_KEY: ""}
    page.reload()
    settled(page)
    assert workspace.fake.state["assignments"] == {**unknown, PROJECT_KEY: ""}


def test_snapshot_helpers_validate_before_changing_and_keep_collection_order(page, workspace):
    result = page.evaluate("""() => {
      const snapshot=organizationSnapshot(), original=JSON.stringify(organization), errors=[];
      for (const action of [
        () => createOrganizationCollection(snapshot,' wOrK ','new'),
        () => createOrganizationCollection(snapshot,'New',''),
        () => createOrganizationCollection(snapshot,'x'.repeat(61),'new'),
        () => renameOrganizationCollection(snapshot,'gone','New'),
        () => deleteOrganizationCollection(snapshot,'gone'),
        () => setProjectCollection(snapshot,boardProjects[0],'gone')
      ]) { const before=JSON.stringify(snapshot); try {action();} catch(error) {errors.push(before===JSON.stringify(snapshot));} }
      createOrganizationCollection(snapshot,' Workspace ','new');
      renameOrganizationCollection(snapshot,'work',' Office ');
      setProjectCollection(snapshot,boardProjects[0],'new');
      return {errors, unchanged:JSON.stringify(organization)===original, collections:snapshot.collections, placement:projectCollectionId(boardProjects[0],snapshot)};
    }""")
    assert result == {"errors": [True] * 6, "unchanged": True,
                      "collections": [{"id": "work", "name": "Office"}, COLLECTIONS[1], {"id": "new", "name": "Workspace"}],
                      "placement": "new"}
    assert puts(workspace.fake) == []


def test_export_import_and_restore_preserve_project_keys_and_workspace_markers(workspace):
    assignments = {PROJECT_KEY: "", WT_A: "work", UNTRACKED_KEY: "missing-island"}
    page = workspace.open_page(assignments)
    with page.expect_download() as download:
        page.get_by_role("button", name="Export organization", exact=True).click()
    exported = json.loads(Path(download.value.path()).read_text())
    assert exported["assignments"] == assignments
    page.evaluate("() => assignCollection(0,'personal')")
    page.locator("#organization-file").set_input_files({"name": "organization.json", "mimeType": "application/json", "buffer": json.dumps(exported).encode()})
    playwright.expect(page.locator("#toast")).to_have_text("Organization imported")
    settled(page)
    assert workspace.fake.state["assignments"] == assignments and placement(page) == [None]
    workspace.fake.fail_puts = 1
    page.evaluate("key => { organization.assignments[key]=''; return persistOrganization(); }", UNTRACKED_KEY)
    workspace.fake.state["revision"] += 1
    page.reload()
    settled(page)
    assert page.evaluate("organizationBackups[0].organization.assignments") == {**assignments, UNTRACKED_KEY: ""}
    page.get_by_role("button", name="Restore unsaved organization", exact=True).click()
    settled(page)
    assert workspace.fake.state["assignments"] == {**assignments, UNTRACKED_KEY: ""}
    assert placement(page) == [None]


# --- P2.3: Board islands -------------------------------------------------------------

def test_neighborhoods_put_workspace_first_then_custom_islands_including_empty(workspace):
    page = workspace.open_page({PROJECT_KEY: "personal"})
    names = page.evaluate("deriveBoardNeighborhoods(boardProjects, organization).map(n => [n.key, n.name, n.projectKeys.length])")
    assert names == [["workspace", "Workspace", 0], ["collection:work", "Work", 0], ["collection:personal", "Personal", 1]]


def test_island_dialog_creates_island_with_selection_in_one_put(workspace):
    page = workspace.open_page()
    page.goto("http://dashboard.test/#/board")
    settled(page)
    before = len(puts(workspace.fake))
    page.locator("#board-island-create").click()
    assert page.locator("#board-island-dialog").evaluate("d => d.open")
    page.locator("#board-island-name").fill("Focus")
    row = page.locator('#board-island-picker input[type=checkbox]')
    assert row.count() == 1
    assert row.bounding_box()["height"] >= 20
    assert page.locator("#board-island-picker label").bounding_box()["height"] >= 44
    row.check()
    page.locator("#board-island-save").click()
    page.wait_for_function("!document.getElementById('board-island-dialog').open")
    page.evaluate("() => organizationQueue")
    assert len(puts(workspace.fake)) == before + 1
    saved = puts(workspace.fake)[-1]
    focus = next(c["id"] for c in saved["collections"] if c["name"] == "Focus")
    assert saved["assignments"][PROJECT_KEY] == focus
    assert page.evaluate("boardActivePageKey") == "collection:" + focus + ":0"
    assert page.locator("#board-island-delete").is_visible()


def test_island_dialog_cancel_restores_focus_and_changes_nothing(workspace):
    page = workspace.open_page()
    page.goto("http://dashboard.test/#/board")
    settled(page)
    before = len(puts(workspace.fake))
    page.locator("#board-island-create").focus()
    page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    assert page.evaluate("document.activeElement.id") == "board-island-create"
    assert len(puts(workspace.fake)) == before
    assert page.evaluate("organization.collections.length") == 2


def test_island_dialog_reports_a_project_that_disappeared_without_saving(workspace):
    page = workspace.open_page()
    page.goto("http://dashboard.test/#/board")
    settled(page)
    page.locator("#board-island-create").click()
    page.locator("#board-island-name").fill("Focus")
    page.locator('#board-island-picker input[type=checkbox]').check()
    before = len(puts(workspace.fake))
    page.evaluate("() => { repos.splice(0); rebuildProjectModel(); }")
    page.locator("#board-island-save").click()
    assert "no longer tracked" in page.locator("#board-island-error").inner_text()
    assert page.locator("#board-island-dialog").evaluate("d => d.open")
    assert len(puts(workspace.fake)) == before


def board(workspace, assignments=None):
    page = workspace.open_page(assignments)
    page.goto("http://dashboard.test/#/board")
    settled(page)
    return page


def test_empty_island_is_finite_and_offers_projects(workspace):
    page = board(workspace, {PROJECT_KEY: "personal"})
    page.locator("#board-archipelago button").nth(1).click()
    assert page.locator("#board-island-empty").is_visible()
    assert page.evaluate("boardScene.plots.length") == 0
    assert page.evaluate("Number.isFinite(boardScene.width) && Number.isFinite(boardScene.height)")
    page.locator("#board-island-empty button").click()
    assert page.locator("#board-island-dialog").evaluate("d => d.open")
    page.keyboard.press("Escape")
    page.locator("#board-archipelago button").nth(2).click()
    assert page.locator("#board-island-empty").is_hidden()


def test_delete_island_confirms_then_moves_projects_to_workspace_in_one_put(workspace):
    page = board(workspace, {PROJECT_KEY: "personal"})
    page.locator("#board-archipelago button").nth(2).click()
    page.evaluate("selectBoardRepo(boardProjects[0].defaultPath)")
    assert page.evaluate("boardSelectedPath") == MAIN
    before = len(puts(workspace.fake))
    page.locator("#board-island-delete").click()
    assert "1 project will move to Workspace" in page.locator("#board-island-delete-body").inner_text()
    page.keyboard.press("Escape")
    assert page.evaluate("document.activeElement.id") == "board-island-delete"
    assert len(puts(workspace.fake)) == before
    page.locator("#board-island-delete").click()
    page.locator("#board-island-delete-confirm").click()
    page.wait_for_function("!document.getElementById('board-island-delete-dialog').open")
    page.evaluate("() => organizationQueue")
    assert len(puts(workspace.fake)) == before + 1
    saved = puts(workspace.fake)[-1]
    assert [c["id"] for c in saved["collections"]] == ["work"]
    assert saved["assignments"][PROJECT_KEY] == ""
    assert page.evaluate("boardActivePageKey") == "workspace:0"
    assert page.evaluate("boardSelectedPath") == MAIN


def test_rename_island_keeps_page_and_membership(workspace):
    page = board(workspace, {PROJECT_KEY: "personal"})
    page.locator("#board-archipelago button").nth(2).click()
    page.locator("#board-island-rename").click()
    page.locator("#board-island-name").fill("Home")
    page.locator("#board-island-save").click()
    page.wait_for_function("!document.getElementById('board-island-dialog').open")
    page.evaluate("() => organizationQueue")
    assert page.evaluate("boardActivePageKey") == "collection:personal:0"
    assert page.evaluate("boardNeighborhoods.map(n => [n.name, n.projectKeys.length])")[2] == ["Home", 1]


def toast_text(page):
    return page.evaluate("[...document.querySelectorAll('.toast, #toast, [role=status]')].map(e => e.textContent).join(' | ')")


def test_failed_put_with_working_storage_says_saved_in_this_browser_only(workspace):
    page = board(workspace)
    workspace.fake.fail_puts = 5
    page.locator("#board-island-create").click()
    page.locator("#board-island-name").fill("Offline")
    page.locator("#board-island-save").click()
    page.wait_for_function("document.getElementById('board-island-error').textContent.includes('Saved in this browser only')")
    assert page.locator("#board-island-dialog").evaluate("d => d.open")
    assert "Kept for this session" not in page.locator("#board-island-error").inner_text()


def test_failed_put_and_failed_storage_says_kept_for_this_session(workspace):
    page = board(workspace)
    workspace.fake.fail_puts = 5
    page.evaluate("() => { Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }}); }")
    page.locator("#board-island-create").click()
    page.locator("#board-island-name").fill("Offline")
    page.locator("#board-island-save").click()
    page.wait_for_function("document.getElementById('board-island-error').textContent.includes('Kept for this session; export before closing.')")
    assert page.locator("#board-island-dialog").evaluate("d => d.open")


def open_edit(page, name="Personal"):
    page.locator("#board-archipelago button", has_text=name).click()
    page.locator("#board-island-projects").click()


def test_save_only_applies_deliberate_changes(workspace):
    page = board(workspace, {PROJECT_KEY: "personal"})
    open_edit(page)
    page.evaluate("() => { organization.assignments[boardProjects[0] && projectAssignmentKey(boardProjects[0])] = 'work'; boardMembershipPending = true; }")
    page.locator("#board-island-save").click()
    page.wait_for_function("!document.getElementById('board-island-dialog').open")
    page.evaluate("() => organizationQueue")
    assert puts(workspace.fake)[-1]["assignments"][PROJECT_KEY] == "work"


def test_conflicting_merge_intents_are_rejected(workspace):
    page = board(workspace, {PROJECT_KEY: "personal"})
    open_edit(page)
    before = len(puts(workspace.fake))
    page.evaluate("""() => {
      const key = boardProjects[0].key;
      islandDraft.checked.delete(key);
      islandDraft.known.set('ghost', {paths: [boardProjects[0].defaultPath], projectId: boardProjects[0].projectId});
      islandDraft.checked.add('ghost');
    }""")
    page.locator("#board-island-save").click()
    assert "merged with another project" in page.locator("#board-island-error").inner_text()
    assert len(puts(workspace.fake)) == before


def test_failed_save_keeps_draft_and_retry_creates_one_island(workspace):
    page = board(workspace)
    workspace.fake.fail_puts = 1
    page.locator("#board-island-create").click()
    page.locator("#board-island-name").fill("Retry")
    page.locator('#board-island-picker input[type=checkbox]').check()
    page.locator("#board-island-save").click()
    page.wait_for_function("document.getElementById('board-island-error').textContent.includes('Your choices are still here')")
    assert page.locator('#board-island-picker input[type=checkbox]').is_checked()
    page.locator("#board-island-save").click()
    page.wait_for_function("!document.getElementById('board-island-dialog').open")
    assert page.evaluate("organization.collections.filter(c => c.name === 'Retry').length") == 1


def test_moving_selected_project_to_workspace_keeps_selection_and_follows_it(workspace):
    page = board(workspace, {PROJECT_KEY: "personal"})
    page.locator("#board-archipelago button", has_text="Personal").click()
    page.evaluate("selectBoardRepo(boardProjects[0].defaultPath)")
    page.locator("#board-island-projects").click()
    page.locator('#board-island-picker input[type=checkbox]').uncheck()
    page.locator("#board-island-save").click()
    page.wait_for_function("!document.getElementById('board-island-dialog').open")
    assert page.evaluate("boardSelectedPath") == MAIN
    assert page.evaluate("boardActivePageKey") == "workspace:0"


def test_vanished_page_falls_back_inside_its_island(workspace):
    page = board(workspace)
    page.evaluate("() => { boardActivePageKey = 'collection:work:3'; boardSelectedPath = null; boardMembershipPending = true; commitBoardMembership(); }")
    assert page.evaluate("boardActivePageKey") == "collection:work:0"


def test_enter_in_search_does_not_submit(workspace):
    page = board(workspace)
    before = len(puts(workspace.fake))
    page.locator("#board-island-create").click()
    page.locator("#board-island-name").fill("Nope")
    page.locator("#board-island-search").press("Enter")
    assert page.locator("#board-island-dialog").evaluate("d => d.open")
    assert len(puts(workspace.fake)) == before


def test_workspace_projects_can_move_to_an_existing_island(workspace):
    page = board(workspace)
    page.locator("#board-island-projects").click()
    assert page.locator("#board-island-destination-row").is_visible()
    page.locator("#board-island-destination").select_option("work")
    page.locator('#board-island-picker input[type=checkbox]').check()
    page.locator("#board-island-save").click()
    page.wait_for_function("!document.getElementById('board-island-dialog').open")
    page.evaluate("() => organizationQueue")
    assert puts(workspace.fake)[-1]["assignments"][PROJECT_KEY] == "work"


def test_board_offers_export_and_recovery_actions(workspace):
    page = board(workspace)
    assert page.locator("#board-organization-export").is_visible()
    assert page.locator("#board-organization-restore").is_hidden()
    page.evaluate("() => { keepUnsavedOrganization(); renderBoard(); }")
