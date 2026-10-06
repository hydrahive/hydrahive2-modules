"""Stufe 1 (Entwurf): Das Backend meldet nur den Stand – und nur an angemeldete Nutzer."""
from __future__ import annotations

from conftest import MOD_PREFIX


def test_status_needs_login(client):
    assert client.get(f"{MOD_PREFIX}/status").status_code in (401, 403)


def test_status_reports_draft(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/status", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"stage": "draft", "storage": "browser", "ai": "placeholder"}


def test_register_adds_router():
    import backend

    seen = []

    class Ctx:
        def register_router(self, router):
            seen.append(router)

    backend.register(Ctx())
    assert seen == [backend.router]
