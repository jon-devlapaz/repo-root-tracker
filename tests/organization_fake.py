"""Small revision-aware API fake shared by dashboard browser fixtures."""

from copy import deepcopy


class OrganizationFake:
    def __init__(self):
        self.state = {"version": 1, "revision": 0, "exists": False, "pins": [],
                      "collections": [], "assignments": {}, "grouping": "collection", "sort": "name"}
        self.requests = []
        self.failure = None
        self.fail_puts = 0

    def route(self, route):
        method = route.request.method
        payload = route.request.post_data_json if method == "PUT" else None
        self.requests.append((method, deepcopy(payload)))
        if method == "PUT" and self.fail_puts:
            self.fail_puts -= 1
            route.fulfill(status=500, json={"error": "Could not save organization.json. Check permissions."})
        elif self.failure == "unreachable":
            route.abort()
        elif self.failure:
            route.fulfill(status=500, json={"error": self.failure})
        elif method == "GET":
            route.fulfill(json=self.state)
        elif payload["base_revision"] != self.state["revision"]:
            route.fulfill(status=409, json=self.state)
        else:
            self.state = {k: v for k, v in payload.items() if k != "base_revision"}
            self.state.update(revision=payload["base_revision"] + 1, exists=True)
            route.fulfill(json=self.state)


def route_organization(page):
    fake = OrganizationFake()
    page.route("**/api/organization", fake.route)
    return fake
