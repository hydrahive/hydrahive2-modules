"""Routen: signierter Ansichts-Link (mit Login) und Sandbox-Ansicht (ohne Login, Spec §4, §4a)."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from backend import links, store
from conftest import DEV_PREFIX, MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

SANDBOX_CSP = ("sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none'; "
               "script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; "
               "connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'")


def _diagram(username="testuser", project_id=PROJECT_ID):
    return store.create(username=username, project_id=project_id, session_id="s", agent_id="a", title="T",
                        kind="workflow", html="<html><body>DIAGRAMM</body></html>", source="{}", source_ext="json")


def _split(url):
    u = urlparse(url)
    q = parse_qs(u.query)
    return u.path, q["exp"][0], q["sig"][0]


def test_view_link_for_owner(client, auth_headers, store_dir):
    d = _diagram()
    r = client.get(f"{MOD_PREFIX}/view-link/{d['id']}", headers=auth_headers)
    assert r.status_code == 200
    url = r.json()["url"]
    assert url.startswith(f"{DEV_PREFIX}/sandbox/{d['id']}?")
    path, exp, sig = _split(url)
    assert links.check(d["id"], int(exp), sig)


def test_view_link_for_stranger_is_404(client, other_headers, store_dir):
    d = _diagram()
    r = client.get(f"{MOD_PREFIX}/view-link/{d['id']}", headers=other_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "diagram_not_found"


def test_view_link_for_admin(client, admin_headers, store_dir):
    d = _diagram(username="other", project_id=OTHER_PROJECT_ID)
    assert client.get(f"{MOD_PREFIX}/view-link/{d['id']}", headers=admin_headers).status_code == 200


def test_view_link_needs_login(client, store_dir):
    d = _diagram()
    assert client.get(f"{MOD_PREFIX}/view-link/{d['id']}").status_code in (401, 403)


@pytest.mark.parametrize("bad", ["d_gibtsnicht", "..%2Fx", "d_a%2Fb"])
def test_view_link_unknown_or_bad_id(client, auth_headers, store_dir, bad):
    assert client.get(f"{MOD_PREFIX}/view-link/{bad}", headers=auth_headers).status_code == 404


def test_sandbox_serves_html_with_fixed_headers(client, auth_headers, store_dir):
    d = _diagram()
    url = client.get(f"{MOD_PREFIX}/view-link/{d['id']}", headers=auth_headers).json()["url"]
    r = client.get(url)
    assert r.status_code == 200 and "DIAGRAMM" in r.text
    assert r.headers["content-type"].startswith("text/html")
    assert r.headers["content-security-policy"] == SANDBOX_CSP
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_sandbox_without_or_with_wrong_signature_is_404(client, store_dir):
    d = _diagram()
    exp, sig = links.sign(d["id"])
    bad = ("0" if sig[0] != "0" else "1") + sig[1:]
    for query in ("", f"?exp={exp}", f"?sig={sig}", f"?exp={exp}&sig={bad}", f"?exp=abc&sig={sig}"):
        r = client.get(f"{DEV_PREFIX}/sandbox/{d['id']}{query}")
        assert r.status_code == 404, query
        assert "DIAGRAMM" not in r.text


def test_sandbox_with_signature_of_other_diagram_is_404(client, store_dir):
    a, b = _diagram(), _diagram()
    exp, sig = links.sign(a["id"])
    assert client.get(f"{DEV_PREFIX}/sandbox/{b['id']}?exp={exp}&sig={sig}").status_code == 404


def test_sandbox_expired_is_404(client, store_dir):
    d = _diagram()
    exp, sig = links.sign(d["id"], now=1000)
    assert client.get(f"{DEV_PREFIX}/sandbox/{d['id']}?exp={exp}&sig={sig}").status_code == 404


def test_sandbox_still_shows_trashed_diagram(client, store_dir):
    """Papierkorb = noch nachschlagbar (Spec §5a)."""
    d = _diagram()
    store.trash(d["id"])
    exp, sig = links.sign(d["id"])
    assert client.get(f"{DEV_PREFIX}/sandbox/{d['id']}?exp={exp}&sig={sig}").status_code == 200


def test_sandbox_signed_but_unknown_id_is_404(client, store_dir):
    exp, sig = links.sign("d_gibtsnicht")
    assert client.get(f"{DEV_PREFIX}/sandbox/d_gibtsnicht?exp={exp}&sig={sig}").status_code == 404


def test_device_auth_only_allows_sandbox_get(client, store_dir):
    """Die Geräte-Prüfung lässt nur die Sandbox-Route durch, nichts anderes unter dem Geräte-Pfad."""
    from backend.device_routes import device_router
    paths = {(r.path, tuple(sorted(r.methods))) for r in device_router.routes}
    assert paths == {("/sandbox/{view_id}", ("GET",))}
