"""Fremde Tasks anderer Instanzen (Gemeinsame Taskpflege, Spec federation-shared-tasks.md
§Modul-Routen): include_foreign, Volltext-Route, alter Kern, Nutzername nur vom angemeldeten
Nutzer, fremde IDs nie auf den normalen Routen.
"""
from __future__ import annotations

import pytest

from backend import foreign

BASE = "/api/modules/tasks/tasks"
FP = "fp-hydrahome"


def _item(item_id, owner="alice", *, priority="medium", created="2026-11-20T10:00:00Z", status="open",
          local="p-dev"):
    return {"origin_fp": FP, "origin_name": "hydrahome", "kind": "task", "item_id": item_id, "owner": owner,
            "title": f"Fremd {item_id}", "status": status, "priority": priority, "project_id": "o-dev",
            "project_name": "Hydrahive DEV", "created_at": created, "updated_at": created, "foreign": True,
            "origin_last_seen": "2026-11-22T10:00:00Z", "stale": False, "pending_edits": 0,
            "local_project_id": local}


class FakeCtx:
    """Neuer Kern mit catalog_foreign_list/get. Merkt sich die Aufrufe."""

    def __init__(self, items=None, full=None):
        self.items, self.full, self.calls, self.get_calls = items or [], full, [], []

    def catalog_foreign_list(self, kind, username, project_id="*", statuses=None, q=None, limit=100, offset=0):
        self.calls.append((kind, username, project_id, statuses, limit, offset))
        rows = [i for i in self.items if i["owner"] == username]
        if project_id not in ("*", None):
            rows = [i for i in rows if i["local_project_id"] == project_id]
        if statuses:
            rows = [i for i in rows if i["status"] in statuses]
        return rows[offset:offset + limit]

    async def catalog_foreign_get(self, kind, username, origin_fp, item_id):
        self.get_calls.append((kind, username, origin_fp, item_id))
        if self.full is None or username != "alice":
            return None
        return self.full


class OldCtx:
    """Kern vor G3: kennt die Methoden nicht."""


@pytest.fixture(autouse=True)
def _unbind():
    foreign._ctx = None
    yield
    foreign._ctx = None


def test_ohne_parameter_antwort_wie_bisher(client, alice):
    foreign.bind(FakeCtx([_item("f-1")]))
    client.post(BASE, json={"title": "Eigen"}, headers=alice)
    rows = client.get(BASE, headers=alice).json()
    assert [r["title"] for r in rows] == ["Eigen"] and "foreign" not in rows[0]


def test_include_foreign_eigene_und_fremde_sortiert(client, alice):
    ctx = FakeCtx([_item("f-low", priority="low"), _item("f-high", priority="high", created="2026-11-01T00:00:00Z")])
    foreign.bind(ctx)
    client.post(BASE, json={"title": "Eigen", "priority": "medium"}, headers=alice)
    rows = client.get(BASE, params={"include_foreign": 1}, headers=alice).json()
    assert [r.get("item_id") or r["title"] for r in rows] == ["f-high", "Eigen", "f-low"]
    f = rows[0]
    assert f["foreign"] is True and f["origin_name"] == "hydrahome" and f["stale"] is False
    assert f["local_project_id"] == "p-dev" and f["origin_last_seen"] == "2026-11-22T10:00:00Z"


def test_projekt_und_status_gehen_an_den_kern(client, alice):
    ctx = FakeCtx([_item("f-1"), _item("f-2", local="p-other"), _item("f-3", status="done")])
    foreign.bind(ctx)
    rows = client.get(BASE, params={"include_foreign": 1, "project_id": "p-dev", "status": "open"},
                      headers=alice).json()
    assert [r["item_id"] for r in rows] == ["f-1"]
    assert ctx.calls[0][:4] == ("task", "alice", "p-dev", ["open"])
    client.get(BASE, params={"include_foreign": 1}, headers=alice)
    assert ctx.calls[-1][2] == "*"                                   # ohne Projekt: alle


def test_alter_kern_keine_fremden(client, alice):
    foreign.bind(OldCtx())
    assert not foreign.available()
    client.post(BASE, json={"title": "Eigen"}, headers=alice)
    rows = client.get(BASE, params={"include_foreign": 1}, headers=alice).json()
    assert [r["title"] for r in rows] == ["Eigen"]
    assert client.get(f"{BASE}/foreign/{FP}/f-1", headers=alice).status_code == 404


def test_username_nicht_ueberschreibbar(client, alice, bob):
    ctx = FakeCtx([_item("f-a"), _item("f-b", owner="bob")])
    foreign.bind(ctx)
    rows = client.get(BASE, params={"include_foreign": 1, "username": "bob", "owner": "bob"}, headers=alice).json()
    assert [r["item_id"] for r in rows] == ["f-a"]
    assert {c[1] for c in ctx.calls} == {"alice"}
    client.get(f"{BASE}/foreign/{FP}/f-b", params={"username": "bob"}, headers=alice)
    assert ctx.get_calls[-1][1] == "alice"
    assert [r["item_id"] for r in client.get(BASE, params={"include_foreign": 1}, headers=bob).json()] == ["f-b"]


def test_fremde_zeilen_mit_falschem_owner_verworfen(client, alice):
    class Leaky(FakeCtx):
        def catalog_foreign_list(self, *a, **kw):
            return [_item("f-x", owner="bob")]
    foreign.bind(Leaky())
    assert client.get(BASE, params={"include_foreign": 1}, headers=alice).json() == []


def test_fremde_id_auf_normalen_routen_404(client, alice):
    foreign.bind(FakeCtx([_item("f-1")]))
    assert client.patch(f"{BASE}/f-1", json={"status": "done"}, headers=alice).status_code == 404
    assert client.delete(f"{BASE}/f-1", headers=alice).status_code == 404
    assert client.get(f"{BASE}/f-1/history", headers=alice).status_code == 404


def test_volltext_route(client, alice, bob):
    full = {"item": _item("f-1"), "content": {"description": "Volltext"}, "source": "live",
            "origin_offline": False, "snapshot_at": None, "last_seen": None, "hub_unreachable": False}
    foreign.bind(FakeCtx([_item("f-1")], full=full))
    r = client.get(f"{BASE}/foreign/{FP}/f-1", headers=alice)
    assert r.status_code == 200 and r.json()["content"] == {"description": "Volltext"}
    assert client.get(f"{BASE}/foreign/{FP}/f-1", headers=bob).status_code == 404   # Kern sagt None


def test_volltext_fremder_owner_verworfen(client, alice):
    full = {"item": _item("f-1", owner="bob"), "content": {"description": "x"}, "source": "live"}
    foreign.bind(FakeCtx(full=full))
    assert client.get(f"{BASE}/foreign/{FP}/f-1", headers=alice).status_code == 404


def test_kern_wirft_trotzdem_liste_bleibt(client, alice):
    class Boom(FakeCtx):
        def catalog_foreign_list(self, *a, **kw):
            raise RuntimeError("Zwischenstand")
    foreign.bind(Boom())
    client.post(BASE, json={"title": "Eigen"}, headers=alice)
    assert [r["title"] for r in client.get(BASE, params={"include_foreign": 1}, headers=alice).json()] == ["Eigen"]


def test_blaettert_ueber_seiten(client, alice):
    ctx = FakeCtx([_item(f"f-{n:04d}") for n in range(foreign.PAGE + 3)])
    foreign.bind(ctx)
    rows = client.get(BASE, params={"include_foreign": 1}, headers=alice).json()
    assert len(rows) == foreign.PAGE + 3 and [c[5] for c in ctx.calls] == [0, foreign.PAGE]


def test_register_bindet_nur_neuen_kern():
    from backend import register

    class Ctx:
        def __init__(self):
            self.tools = []

        def register_router(self, r): ...
        def register_tool(self, t): self.tools.append(t)
        def register_migrations(self, m): ...

    register(Ctx())
    assert not foreign.available()

    class NewCtx(Ctx):
        def catalog_foreign_list(self, *a, **kw): return []

    register(NewCtx())
    assert foreign.available()


def test_volltext_ohne_owner_verworfen(client, alice):
    item = {k: v for k, v in _item("f-1").items() if k != "owner"}
    foreign.bind(FakeCtx(full={"item": item, "content": {}, "source": "live"}))
    assert client.get(f"{BASE}/foreign/{FP}/f-1", headers=alice).status_code == 404
