"""Shared organization, legacy migration, conflicts, and portable backups."""

import json
from pathlib import Path

import pytest

from organization_fake import OrganizationFake

playwright = pytest.importorskip("playwright.sync_api")
DASHBOARD = Path(__file__).parents[1] / "src/repo_root_tracker/dashboard.html"
KEY = "repo-root-tracker.organization.v1"
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
    playwright.expect(second.locator("#toast")).to_have_text("Updated elsewhere, reloaded")
    assert second.evaluate("organization.pins") == []
    assert second.evaluate("organization.sort") == "recent"
    assert fake.state["pins"] == [] and fake.state["revision"] == 2
    assert len([m for m, _ in fake.requests if m == 'GET']) == get_count + 1
    assert second.evaluate("key => JSON.parse(localStorage.getItem(key)).pins", KEY) == []


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
    playwright.expect(page.locator("#toast")).to_have_text("Updated elsewhere, reloaded")


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
