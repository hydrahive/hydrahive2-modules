"""Fremde Ideen anderer Instanzen (Gemeinsame Taskpflege, Spec federation-shared-tasks.md
§Modul-Routen, AK G3): include_foreign mit Projekt- und Statusfilter, Volltext-Route
(Text + Anmerkungen), alter Kern, Nutzername nur vom angemeldeten Nutzer, fremde IDs nie auf
den normalen Routen.
"""
from __future__ import annotations

import pytest
from helpers import MOD_PREFIX, PROJECT_A

from backend import foreign

BASE = f"{MOD_PREFIX}/ideas"
FP = "fp-hydrahome"


def _item(item_id, owner="alice", *, status="new", updated="2026-11-20T10:00:00Z", local=PROJECT_A, origin="o-dev"):
    return {"origin_fp": FP, "origin_name": "hydrahome", "kind": "idea", "item_id": item_id, "owner": owner,
            "title": f"Fremd {item_id}", "status": status, "priority": None, "project_id": origin,
            "project_name": "Hydrahive DEV", "created_at": updated, "updated_at": updated, "foreign": True,
            "origin_last_seen": "2026-11-22T10:00:00Z", "stale": False, "pending_edits": 0,
            "local_project_id": local}


class FakeCtx:
    """Neuer Kern mit catalog_foreign_list/get. Filtert wie der echte Kern (Zuordnung, Status)."""

    def __init__(self, items=None, full=None):
        self.items, self.full, self.calls, self.get_calls = items or [], full, [], []

    def catalog_foreign_list(self, kind, username, project_id="*", statuses=None, q=None, limit=100, offset=0):
        self.calls.append((kind, username, project_id, statuses, limit, offset))
        rows = [i for i in self.items if i["owner"] == username]
        if project_id is None:
            rows = [i for i in rows if not i["project_id"]]
        elif project_id != "*":
            rows = [i for i in rows if i["local_project_id"] == project_id]
        if statuses:
            rows = [i for i in rows if i["status"] in statuses]
        return rows[offset:offset + limit]

    async def catalog_foreign_get(self, kind, username, origin_fp, item_id):
        self.get_calls.append((kind, username, origin_fp, item_id))
        return self.full if username == "alice" else None


@pytest.fixture(autouse=True)
def _unbind():
    foreign._ctx = None
    yield
    foreign._ctx = None


def _new(client, headers, **body):
    r = client.post(BASE, json={"title": "Eigen", **body}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_ohne_parameter_antwort_wie_bisher(client, alice):
    foreign.bind(FakeCtx([_item("f-1")]))
    _new(client, alice)
    data = client.get(BASE, headers=alice).json()
    assert [i["title"] for i in data["ideas"]] == ["Eigen"] and "foreign" not in data["ideas"][0]
    assert data["counts"]["new"] == 1


def test_include_foreign_zusammen_neueste_zuerst_und_zaehler(client, alice):
    foreign.bind(FakeCtx([_item("f-alt", updated="2020-01-01T00:00:00Z"),
                          _item("f-neu", updated="2099-01-01T00:00:00Z", status="done")]))
    _new(client, alice)
    data = client.get(BASE, params={"include_foreign": 1}, headers=alice).json()
    assert [i.get("item_id") or i["title"] for i in data["ideas"]] == ["f-neu", "Eigen", "f-alt"]
    assert data["counts"]["new"] == 2 and data["counts"]["done"] == 1
    f = data["ideas"][0]
    assert f["foreign"] is True and f["origin_name"] == "hydrahome" and f["local_project_id"] == PROJECT_A


def test_projekt_und_statusfilter_gelten_auch_fuer_fremde(client, alice):
    ctx = FakeCtx([_item("f-a"), _item("f-b", local="anderes"), _item("f-c", status="done"),
                   _item("f-ohne", local=None, origin=None)])
    foreign.bind(ctx)
    data = client.get(BASE, params={"include_foreign": 1, "project_id": PROJECT_A, "status": "open"},
                      headers=alice).json()
    assert [i["item_id"] for i in data["ideas"]] == ["f-a"]
    assert ctx.calls[-1][2] == PROJECT_A
    assert data["counts"]["done"] == 1                               # Zähler nur nach Projekt, wie eigene
    none = client.get(BASE, params={"include_foreign": 1, "project_id": "none", "status": "all"}, headers=alice)
    assert [i["item_id"] for i in none.json()["ideas"]] == ["f-ohne"] and ctx.calls[-1][2] is None
    client.get(BASE, params={"include_foreign": 1}, headers=alice)
    assert ctx.calls[-1][2] == "*"


def test_alter_kern_keine_fremden(client, alice):
    foreign.bind(object())
    assert not foreign.available()
    _new(client, alice)
    data = client.get(BASE, params={"include_foreign": 1}, headers=alice).json()
    assert [i["title"] for i in data["ideas"]] == ["Eigen"]
    assert client.get(f"{BASE}/foreign/{FP}/f-1", headers=alice).status_code == 404


def test_username_nicht_ueberschreibbar(client, alice, bob):
    ctx = FakeCtx([_item("f-a"), _item("f-b", owner="bob")])
    foreign.bind(ctx)
    data = client.get(BASE, params={"include_foreign": 1, "username": "bob", "owner": "bob"}, headers=alice).json()
    assert [i["item_id"] for i in data["ideas"]] == ["f-a"] and {c[1] for c in ctx.calls} == {"alice"}
    client.get(f"{BASE}/foreign/{FP}/f-b", params={"username": "bob"}, headers=alice)
    assert ctx.get_calls[-1][1] == "alice"
    assert [i["item_id"] for i in client.get(BASE, params={"include_foreign": 1}, headers=bob).json()["ideas"]] == ["f-b"]


def test_fremde_zeilen_mit_falschem_owner_verworfen(client, alice):
    class Leaky(FakeCtx):
        def catalog_foreign_list(self, *a, **kw):
            return [_item("f-x", owner="bob")]
    foreign.bind(Leaky())
    assert client.get(BASE, params={"include_foreign": 1}, headers=alice).json()["ideas"] == []


@pytest.mark.parametrize("method,path", [
    ("get", "/f-1"), ("patch", "/f-1"), ("delete", "/f-1"), ("delete", "/f-1/notes/1"),
    ("post", "/f-1/task"), ("post", "/f-1/board"),
])
def test_fremde_id_auf_normalen_routen_404(client, alice, method, path):
    foreign.bind(FakeCtx([_item("f-1")]))
    kwargs = {"json": {"status": "done"}} if method in ("patch", "post") else {}
    assert getattr(client, method)(BASE + path, headers=alice, **kwargs).status_code == 404


def test_volltext_mit_text_und_anmerkungen(client, alice, bob):
    full = {"item": _item("f-1"), "content": {"body": "Ideentext", "notes": [
        {"author": "agent", "agent_name": "Buddy", "body": "Anmerkung", "created_at": "2026-11-21T10:00:00Z"}]},
        "source": "live", "origin_offline": False, "snapshot_at": None, "last_seen": None, "hub_unreachable": False}
    foreign.bind(FakeCtx([_item("f-1")], full=full))
    r = client.get(f"{BASE}/foreign/{FP}/f-1", headers=alice)
    assert r.status_code == 200 and r.json()["content"]["body"] == "Ideentext"
    assert r.json()["content"]["notes"][0]["body"] == "Anmerkung"
    assert client.get(f"{BASE}/foreign/{FP}/f-1", headers=bob).status_code == 404


def test_volltext_fremder_owner_verworfen(client, alice):
    foreign.bind(FakeCtx(full={"item": _item("f-1", owner="bob"), "content": {"body": "x"}, "source": "live"}))
    assert client.get(f"{BASE}/foreign/{FP}/f-1", headers=alice).status_code == 404


def test_kern_wirft_trotzdem_liste_bleibt(client, alice):
    class Boom(FakeCtx):
        def catalog_foreign_list(self, *a, **kw):
            raise RuntimeError("Zwischenstand")
    foreign.bind(Boom())
    _new(client, alice)
    assert [i["title"] for i in client.get(BASE, params={"include_foreign": 1}, headers=alice).json()["ideas"]] == ["Eigen"]


def test_blaettert_ueber_seiten(client, alice):
    ctx = FakeCtx([_item(f"f-{n:04d}") for n in range(foreign.PAGE + 3)])
    foreign.bind(ctx)
    data = client.get(BASE, params={"include_foreign": 1}, headers=alice).json()
    assert len(data["ideas"]) == foreign.PAGE + 3 and [c[5] for c in ctx.calls] == [0, foreign.PAGE]


def test_register_bindet_nur_neuen_kern():
    from backend import register

    class Ctx:
        def register_router(self, r): ...
        def register_tool(self, t): ...
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
