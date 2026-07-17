from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import router
from hydrahive.api.middleware.auth import require_auth


PREFIX = "/api/modules/haushaltsbuch"


def _client(*, authenticated: bool) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix=PREFIX)
    if authenticated:
        app.dependency_overrides[require_auth] = lambda: ("testuser", "user")
    return TestClient(app)


def test_status_requires_authentication() -> None:
    response = _client(authenticated=False).get(f"{PREFIX}/status")

    assert response.status_code == 401


def test_status_reports_v1_contract() -> None:
    response = _client(authenticated=True).get(f"{PREFIX}/status")

    assert response.status_code == 200
    assert response.json() == {
        "module": "haushaltsbuch",
        "state": "active",
        "features": {
            "bookings_budgets": "available",
            "bank_import": "planned",
            "lidl_plus": "planned",
            "payback": "planned",
        },
    }
