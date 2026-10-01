"""Shared organization, legacy migration, conflicts, and portable backups."""

import json
from pathlib import Path

import pytest

from organization_fake import OrganizationFake

playwright = pytest.importorskip("playwright.sync_api")
DASHBOARD = Path(__file__).parents[1] / "src/repo_root_tracker/dashboard.html"
KEY = "repo-root-tracker.organization.v1"
PENDING_KEY = KEY + ".pending"
RECOVERY_TOAST = "Updated elsewhere, reloaded. Unsaved changes kept; use Restore unsaved organization."
REPO = "/workspace/alpha"


def legacy():
    return {"pins": [REPO], "collections": [{"id": "work", "name": "Work"}],
            "assignments": {REPO: "work", "/stale": "work"}, "grouping": "folder",
            "sort": "recent", "collapsed": ["unsorted"], "githubEnabled": True}


@pytest.fixture
def workspace():
    fake = OrganizationFake()
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        contexts, errors = [], []

        def open_page(saved=None):
            context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
            contexts.append(context)
            if saved is not None:
                context.add_init_script("if (localStorage.getItem(" + json.dumps(KEY) + ") === null) localStorage.setItem(" +
                                        json.dumps(KEY) + ", " + json.dumps(json.dumps(saved)) + ");")
            context.route("http://dashboard.test/", lambda route: route.fulfill(
                content_type="text/html", body=DASHBOARD.read_text().replace("__HOME__", "/home/test", 1)))
            context.route("**/api/organization", fake.route)
            context.route("**/api/repos", lambda route: route.fulfill(json=[{"path": REPO}]))
            context.route("**/api/repos/status?*", lambda route: route.fulfill(json={
                "branch": "main", "dirty": {"is_clean": True}, "sync": {"has_upstream": False}}))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://dashboard.test/")
            settled(page)
            return page

        yield open_page, fake
        for context in contexts:
            context.close()
        browser.close()
        assert errors == []


def settled(page):
    page.evaluate("() => organizationQueue")
    page.wait_for_function("repos.length === 1 && repos.every(r => r._status)")


def test_migration_succeeds_once_and_keeps_browser_preferences(workspace):
    open_page, fake = workspace
    saved = legacy()
    page = open_page(saved)
    assert fake.state["revision"] == 1
    assert fake.state["pins"] == saved["pins"] and fake.state["assignments"] == saved["assignments"]
    assert "collapsed" not in fake.state and "githubEnabled" not in fake.state
    assert page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY) == saved
    page.reload()
    settled(page)
    assert fake.state["revision"] == 1
    assert len([method for method, _ in fake.requests if method == "PUT"]) == 1
    assert page.evaluate("organization.collapsed") == saved["collapsed"]
    assert page.evaluate("organization.githubEnabled") is True
    page.evaluate("() => { toggleCollection('unsorted'); organization.githubEnabled = false; return persistOrganization(true); }")
    assert fake.state["revision"] == 1  # These preferences never write shared state.


def test_failed_migration_retries_on_reload_without_losing_legacy_copy(workspace):
    open_page, fake = workspace
    fake.fail_puts = 1
    page = open_page(legacy())
    assert fake.state["revision"] == 0
    assert page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY) == legacy()
    assert "reload to retry" in page.locator("#local-note").inner_text()
    page.reload()
    settled(page)
    assert fake.state["revision"] == 1 and fake.state["pins"] == [REPO]
    assert "could not" not in page.locator("#local-note").inner_text()


def test_server_wins_over_local_and_independent_contexts_share_after_reload(workspace):
    open_page, fake = workspace
    first = open_page(legacy())
    second = open_page({**legacy(), "pins": [], "grouping": "none", "collapsed": []})
    assert second.evaluate("organization.pins") == [REPO]
    assert second.evaluate("organization.grouping") == "folder"
    assert second.evaluate("organization.collapsed") == []
    assert fake.state["revision"] == 1
    first.evaluate("() => { organization.grouping = 'project'; organization.sort = 'name'; return persistOrganization(); }")
    second.reload()
    settled(second)
    assert second.evaluate("organization.grouping") == "project"
    assert second.evaluate("organization.sort") == "name"


def test_conflict_refetches_toasts_and_discards_queued_stale_edits(workspace):
    open_page, fake = workspace
    first = open_page(legacy())
    second = open_page()
    first.evaluate("() => { organization.pins = []; return persistOrganization(); }")
    get_count = len([m for m, _ in fake.requests if m == 'GET'])
    second.evaluate("""() => {
      organization.pins = ['/other']; const firstSave = persistOrganization();
      organization.sort = 'name'; const queuedSave = persistOrganization();
      return Promise.all([firstSave, queuedSave]);
    }""")
    playwright.expect(second.locator("#toast")).to_have_text(RECOVERY_TOAST)
    assert second.evaluate("organization.pins") == []
    assert second.evaluate("organization.sort") == "recent"
    assert fake.state["pins"] == [] and fake.state["revision"] == 2
    assert len([m for m, _ in fake.requests if m == 'GET']) == get_count + 1
    assert second.evaluate("key => JSON.parse(localStorage.getItem(key)).pins", KEY) == []
    recovered = pending_storage(second)["backups"][0]["organization"]
    assert recovered["pins"] == ['/other'] and recovered["sort"] == 'name'


@pytest.mark.parametrize("failure", ["unreachable", "Invalid organization.json. Restore a valid backup."])
def test_server_failure_uses_local_copy_with_actionable_warning(workspace, failure):
    open_page, fake = workspace
    fake.failure = failure
    page = open_page(legacy())
    assert page.evaluate("organization.pins") == [REPO]
    assert "Using the browser copy" in page.locator("#local-note").inner_text()
    page.evaluate("() => { organization.grouping = 'none'; return persistOrganization(); }")
    assert page.evaluate("key => JSON.parse(localStorage.getItem(key)).grouping", KEY) == "none"
    assert "reload to retry" in page.locator("#local-note").inner_text()
    fake.failure = None
    page.reload()
    settled(page)
    assert fake.state["grouping"] == "none" and fake.state["revision"] == 1


def test_unknown_revision_reconnect_adopts_existing_server_instead_of_overwriting(workspace):
    open_page, fake = workspace
    fake.failure = "unreachable"
    page = open_page(legacy())
    fake.failure = None
    fake.state.update(revision=3, exists=True, pins=[], grouping="none")
    page.evaluate("() => { organization.pins = ['/offline']; return persistOrganization(); }")
    assert fake.state["revision"] == 3 and fake.state["pins"] == []
    assert page.evaluate("organization.pins") == []
    playwright.expect(page.locator("#toast")).to_have_text(RECOVERY_TOAST)


def test_export_import_round_trip_preserves_stale_assignments_and_local_preferences(workspace):
    open_page, fake = workspace
    page = open_page(legacy())
    with page.expect_download() as download:
        page.get_by_role("button", name="Export organization", exact=True).click()
    artifact = download.value
    exported = json.loads(Path(artifact.path()).read_text())
    assert artifact.suggested_filename == "organization.json"
    assert exported == {"version": 1, **{k: v for k, v in legacy().items() if k not in ('collapsed', 'githubEnabled')}}
    page.evaluate("() => { organization.pins = []; organization.assignments = {}; return persistOrganization(); }")
    page.locator("#organization-file").set_input_files({"name": "organization.json", "mimeType": "application/json", "buffer": json.dumps(exported).encode()})
    playwright.expect(page.locator("#toast")).to_have_text("Organization imported")
    assert fake.state["pins"] == [REPO] and fake.state["assignments"]["/stale"] == "work"
    assert page.evaluate("organization.collapsed") == ["unsorted"]
    assert page.evaluate("organization.githubEnabled") is True


@pytest.mark.parametrize("data", [
    b'{broken', b'{"version": 99}', b' ' * (1024 * 1024 + 1),
    json.dumps({"version": 1, **{k: v for k, v in legacy().items() if k not in ('collapsed', 'githubEnabled')},
                "collections": [{"id": "a", "name": "A"}, {"id": "a", "name": "B"}]}).encode(),
], ids=['invalid-json', 'wrong-version', 'oversized', 'duplicate-ids'])
def test_invalid_import_changes_nothing(workspace, data):
    open_page, fake = workspace
    page = open_page(legacy())
    before = page.evaluate("JSON.stringify(organization)")
    revision = fake.state["revision"]
    page.locator("#organization-file").set_input_files({"name": "invalid.json", "mimeType": "application/json", "buffer": data})
    playwright.expect(page.locator("#toast")).to_contain_text("Could not import organization:")
    assert page.evaluate("JSON.stringify(organization)") == before
    assert fake.state["revision"] == revision


def pending_storage(page):
    return page.evaluate("key => JSON.parse(localStorage.getItem(key))", PENDING_KEY)


def fail_change(page, fake):
    fake.fail_puts = 1
    page.evaluate("() => { organization.grouping = 'none'; return persistOrganization(); }")
    assert pending_storage(page)["pending"]["base_revision"] == 1
    assert "unsaved changes" in page.locator("#local-note").inner_text()
    assert "Organization is saved" not in page.locator("#local-note").inner_text()


def test_failed_put_retries_same_base_on_reload_and_clears_only_after_ack(workspace):
    open_page, fake = workspace
    page = open_page(legacy())
    fail_change(page, fake)
    copy = pending_storage(page)["pending"]
    assert copy["organization"]["grouping"] == "none"
    fake.fail_puts = 1
    page.reload()
    settled(page)
    assert pending_storage(page)["pending"] == copy
    assert fake.state["revision"] == 1
    assert page.evaluate("organization.grouping") == "none"
    assert "Organization is saved" not in page.locator("#local-note").inner_text()
    page.reload()
    settled(page)
    assert fake.state["revision"] == 2 and fake.state["grouping"] == "none"
    assert pending_storage(page) is None
    assert "Organization is saved" in page.locator("#local-note").inner_text()
    assert page.evaluate("organization.collapsed") == legacy()["collapsed"]
    assert page.evaluate("organization.githubEnabled") is True


@pytest.mark.parametrize("recover_with", ["restore", "import"])
def test_changed_server_keeps_failed_copy_recoverable_after_reload(workspace, recover_with):
    open_page, fake = workspace
    page = open_page(legacy())
    fail_change(page, fake)
    copy = pending_storage(page)["pending"]
    fake.state.update(revision=2, grouping="project", pins=[])
    page.reload()
    settled(page)
    assert page.evaluate("organization.grouping") == "project"
    assert fake.state["revision"] == 2
    playwright.expect(page.locator("#toast")).to_have_text(RECOVERY_TOAST)
    assert pending_storage(page) == {"version": 1, "pending": None, "backups": [copy]}
    assert "Organization is saved" not in page.locator("#local-note").inner_text()
    page.reload()
    settled(page)
    assert pending_storage(page)["backups"] == [copy]
    with page.expect_download() as download:
        page.get_by_role("button", name="Export unsaved organization", exact=True).click()
    artifact = download.value
    exported = json.loads(Path(artifact.path()).read_text())
    assert artifact.suggested_filename == "organization-unsaved.json"
    assert exported == copy["organization"]
    if recover_with == "restore":
        page.get_by_role("button", name="Restore unsaved organization", exact=True).click()
        playwright.expect(page.locator("#toast")).to_have_text("Unsaved organization restored and saved")
        assert pending_storage(page) is None
    else:
        page.locator("#organization-file").set_input_files({"name": "organization-unsaved.json", "mimeType": "application/json", "buffer": json.dumps(exported).encode()})
        playwright.expect(page.locator("#toast")).to_have_text("Organization imported")
    assert fake.state["revision"] == 3 and fake.state["grouping"] == "none"
    assert page.evaluate("organization.grouping") == "none"


def test_pending_is_written_before_put_acknowledgement(workspace):
    open_page, fake = workspace
    page = open_page(legacy())
    page.evaluate("""() => {
      const original = window.fetch;
      window.fetch = (url, options) => url === '/api/organization' && options?.method === 'PUT'
        ? new Promise(() => {}) : original(url, options);
      organization.sort = 'name'; persistOrganization();
    }""")
    assert pending_storage(page)["pending"]["organization"]["sort"] == "name"
    assert "Organization is saved" not in page.locator("#local-note").inner_text()
    page.reload()
    settled(page)
    assert fake.state["revision"] == 2 and fake.state["sort"] == "name"
    assert pending_storage(page) is None


def test_multiple_conflicts_keep_each_copy_selectable_after_reload(workspace):
    open_page, fake = workspace
    page = open_page(legacy())
    fake.state["revision"] = 2
    page.evaluate("() => { organization.grouping = 'none'; return persistOrganization(); }")
    first = pending_storage(page)["backups"][0]
    fake.state["revision"] = 3
    page.evaluate("() => { organization.sort = 'name'; return persistOrganization(); }")
    copies = pending_storage(page)["backups"]
    assert len(copies) == 2 and copies[0] == first
    page.reload()
    settled(page)
    for copy in copies:
        page.get_by_label("Unsaved organization copy", exact=True).select_option(copy["id"])
        with page.expect_download() as download:
            page.get_by_role("button", name="Export unsaved organization", exact=True).click()
        assert json.loads(Path(download.value.path()).read_text()) == copy["organization"]
    assert fake.state["revision"] == 3


@pytest.mark.parametrize("exists,populated", [(True, True), (False, True), (True, False)])
def test_migration_requires_missing_file_and_empty_content(workspace, exists, populated):
    open_page, fake = workspace
    fake.state["exists"] = exists
    if populated:
        fake.state.update(pins=["/server"], collections=[{"id": "server", "name": "Server"}], grouping="project")
    before = json.loads(json.dumps(fake.state))
    page = open_page(legacy())
    assert fake.state == before
    assert all(method == "GET" for method, _ in fake.requests)
    assert page.evaluate("organization.pins") == before["pins"]
    assert page.evaluate("organization.collections") == before["collections"]
    assert "Organization is saved" not in page.locator("#local-note").inner_text()


def test_rename_keeps_stable_target_when_conflict_reorders_collections(workspace):
    open_page, fake = workspace
    page = open_page(legacy())
    page.get_by_role("button", name="Rename Work", exact=True).click()
    page.get_by_label("Collection name", exact=True).fill("My entered name")
    fake.state.update(revision=2, collections=[{"id": "other", "name": "Other"}, {"id": "work", "name": "Work"}])
    page.evaluate("() => { organization.sort = 'name'; return persistOrganization(); }")
    assert page.get_by_label("Collection name", exact=True).input_value() == "My entered name"
    page.get_by_role("button", name="Save collection", exact=True).click()
    page.evaluate("() => organizationQueue")
    assert fake.state["collections"] == [{"id": "other", "name": "Other"}, {"id": "work", "name": "My entered name"}]
    assert fake.state["revision"] == 3


@pytest.mark.parametrize("position", [0, 1])
def test_rename_removed_target_keeps_input_and_changes_nothing(workspace, position):
    open_page, fake = workspace
    collections = [{"id": "other", "name": "Other"}]
    collections.insert(position, {"id": "work", "name": "Work"})
    fake.state.update(revision=1, exists=True, collections=collections)
    page = open_page()
    page.get_by_role("button", name="Rename Work", exact=True).click()
    page.get_by_label("Collection name", exact=True).fill("Keep this draft")
    fake.state.update(revision=2, collections=[{"id": "other", "name": "Other"}])
    page.evaluate("() => { organization.sort = 'recent'; return persistOrganization(); }")
    request_count = len(fake.requests)
    page.get_by_role("button", name="Save collection", exact=True).click()
    playwright.expect(page.locator("#collection-error")).to_contain_text("removed elsewhere")
    assert page.locator("#collection-dialog").is_visible()
    assert page.get_by_label("Collection name", exact=True).input_value() == "Keep this draft"
    assert fake.state["collections"] == [{"id": "other", "name": "Other"}]
    assert fake.state["revision"] == 2 and len(fake.requests) == request_count


@pytest.mark.parametrize("removed", [False, True])
def test_delete_revalidates_stable_target_after_confirmation(workspace, removed):
    open_page, fake = workspace
    page = open_page(legacy())
    replacement = {**fake.state, "revision": 2, "collections": [{"id": "other", "name": "Other"}]}
    if not removed:
        replacement["collections"].append({"id": "work", "name": "Work"})
    fake.state = replacement
    page.evaluate("state => { window.confirm = () => { adoptOrganization(state); return true; }; }", replacement)
    page.get_by_role("button", name="Delete collection Work", exact=True).click()
    page.evaluate("() => organizationQueue")
    assert fake.state["collections"] == [{"id": "other", "name": "Other"}]
    if removed:
        assert fake.state["revision"] == 2
        playwright.expect(page.locator("#toast")).to_contain_text("removed elsewhere")
    else:
        assert fake.state["revision"] == 3



def test_migration_racing_populated_revision_zero_retains_legacy_copy(workspace):
    open_page, fake = workspace
    original_route = fake.route

    def file_appears_after_get(route):
        was_missing = route.request.method == 'GET' and not fake.state['exists']
        original_route(route)
        if was_missing:
            fake.state.update(exists=True, pins=['/server'])

    fake.route = file_appears_after_get
    page = open_page(legacy())
    assert fake.state['revision'] == 0 and fake.state['pins'] == ['/server']
    assert page.evaluate('organization.pins') == ['/server']
    backup = pending_storage(page)['backups'][0]
    assert backup['base_revision'] == 0 and backup['organization']['pins'] == [REPO]
    playwright.expect(page.locator('#toast')).to_have_text(RECOVERY_TOAST)
    assert 'Organization is saved' not in page.locator('#local-note').inner_text()



def test_collection_saved_toast_requires_put_acknowledgement(workspace):
    open_page, fake = workspace
    page = open_page(legacy())
    fake.fail_puts = 1
    page.get_by_role('button', name='+ Collection', exact=True).click()
    page.get_by_label('Collection name', exact=True).fill('Unsaved collection')
    page.get_by_role('button', name='Save collection', exact=True).click()
    page.evaluate('() => organizationQueue')
    playwright.expect(page.locator('#toast')).to_have_text('Collection updated in this browser. Reload to retry saving.')
    assert fake.state['revision'] == 1
    assert pending_storage(page)['pending']['organization']['collections'][-1]['name'] == 'Unsaved collection'
    page.reload()
    settled(page)
    assert fake.state['revision'] == 2
    assert fake.state['collections'][-1]['name'] == 'Unsaved collection'
    assert 'Organization is saved' in page.locator('#local-note').inner_text()
