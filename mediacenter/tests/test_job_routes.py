from __future__ import annotations

from types import SimpleNamespace

from backend import routes_jobs
from backend.errors import IndexerResponseError

_RESULT_ID = "abcdefghijklmnopqrstuvwx"


def _job(state="consumed"):
    return SimpleNamespace(
        result_id=_RESULT_ID, title="Film", media_type="movie", state=state,
        sab_job_id="SABnzbd_nzo_abc" if state == "consumed" else None,
        error_code=None,
        speed_kbps=None,
    )


def test_jobs_routes_require_auth(client):
    assert client.post("/api/modules/mediacenter/enqueue", json={"result_id": _RESULT_ID}).status_code == 401
    assert client.get("/api/modules/mediacenter/queue").status_code == 401
    assert client.get("/api/modules/mediacenter/history").status_code == 401


def test_enqueue_uses_authenticated_owner_and_strict_schema(client, alice, monkeypatch):
    seen = []

    async def fake(username, result_id, *, priority, **kwargs):
        seen.append((username, result_id, priority, kwargs.get("owner_id")))
        return _job()

    monkeypatch.setattr(routes_jobs.enqueue_service, "enqueue_result", fake)
    response = client.post(
        "/api/modules/mediacenter/enqueue",
        headers=alice,
        json={"result_id": _RESULT_ID, "priority": "high"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "consumed"
    assert seen[0][:3] == ("alice", _RESULT_ID, "high")
    assert seen[0][3] and seen[0][3] != "alice"
    invalid = client.post(
        "/api/modules/mediacenter/enqueue", headers=alice,
        json={"result_id": _RESULT_ID, "url": "https://evil.invalid/a.nzb"},
    )
    assert invalid.status_code == 422
    assert "evil" not in invalid.text


def test_enqueue_hides_missing_and_reports_uncertain(client, alice, monkeypatch):
    async def missing(*args, **kwargs):
        raise IndexerResponseError("result_unavailable")

    monkeypatch.setattr(routes_jobs.enqueue_service, "enqueue_result", missing)
    response = client.post(
        "/api/modules/mediacenter/enqueue", headers=alice,
        json={"result_id": _RESULT_ID},
    )
    # 409 statt 404/502: ein abgelaufener Treffer ist ein Zustandskonflikt,
    # kein fehlender Endpunkt und kein Serverausfall (till sah zuvor
    # "Bad Gateway" und hielt es fuer einen Ausfall).
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "result_unavailable"

    async def uncertain(*args, **kwargs):
        return _job("uncertain")

    monkeypatch.setattr(routes_jobs.enqueue_service, "enqueue_result", uncertain)
    response = client.post(
        "/api/modules/mediacenter/enqueue", headers=alice,
        json={"result_id": _RESULT_ID},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "enqueue_status_uncertain"

    async def submitting(*args, **kwargs):
        return _job("submitting")

    monkeypatch.setattr(routes_jobs.enqueue_service, "enqueue_result", submitting)
    response = client.post(
        "/api/modules/mediacenter/enqueue", headers=alice,
        json={"result_id": _RESULT_ID},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "enqueue_status_uncertain"


def test_queue_and_history_are_bound_to_authenticated_owner(client, alice, bob, monkeypatch):
    seen = []

    async def list_jobs(username, mode, **kwargs):
        seen.append((username, mode))
        return []

    monkeypatch.setattr(routes_jobs.job_service, "list_jobs", list_jobs)
    assert client.get("/api/modules/mediacenter/queue", headers=alice).json() == []
    assert client.get("/api/modules/mediacenter/history", headers=bob).json() == []
    assert seen == [("alice", "queue"), ("bob", "history")]


def test_enqueue_rate_limit_is_strict_and_per_user(client, alice, bob, monkeypatch):
    async def fake(*args, **kwargs):
        return _job()

    monkeypatch.setattr(routes_jobs.enqueue_service, "enqueue_result", fake)
    for _ in range(5):
        assert client.post(
            "/api/modules/mediacenter/enqueue", headers=alice,
            json={"result_id": _RESULT_ID},
        ).status_code == 200
    blocked = client.post(
        "/api/modules/mediacenter/enqueue", headers=alice,
        json={"result_id": _RESULT_ID},
    )
    assert blocked.status_code == 429
    assert client.post(
        "/api/modules/mediacenter/enqueue", headers=bob,
        json={"result_id": _RESULT_ID},
    ).status_code == 200
