"""Hydra-Labor L3: kleiner Auslieferer IM LABOR (probe/front.py) – Oberfläche aus dist, /api gestreamt ans Probe-Backend.

Läuft im Container, nicht auf dem Server. Getestet mit einem Attrappen-Backend (httpx.MockTransport).
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "probe"))
import front


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>Probe-App</html>")
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)")
    (tmp_path / "brand").mkdir()
    (tmp_path / "brand" / "logo.webp").write_bytes(b"RIFFwebp")
    (tmp_path / "favicon-32.png").write_bytes(b"\x89PNG")
    (tmp_path.parent / "geheim.txt").write_text("nicht da")            # neben dist, nicht darin
    return tmp_path


@pytest.fixture
def seen():
    return []


@pytest.fixture
def client(dist, seen):
    def backend(req: httpx.Request) -> httpx.Response:
        req.read()                                             # Inhalt merken, bevor der Strom weg ist
        seen.append(req)
        if req.url.path == "/api/stream":
            return httpx.Response(200, stream=httpx.ByteStream(b"data: a\n\ndata: b\n\n"),
                                  headers={"content-type": "text/event-stream"})
        import json
        body = json.dumps({"pfad": req.url.path, "q": req.url.query.decode()}).encode()
        # Wie ein echter Server: Antwort als Strom (httpx liest fertigen Inhalt sonst schon beim Bauen).
        return httpx.Response(201, stream=httpx.ByteStream(body), headers={
            "content-type": "application/json", "x-aus-backend": "1", "set-cookie": "probe=1; Path=/"})
    app = front.make_app(dist, "http://127.0.0.1:8002", transport=httpx.MockTransport(backend))
    with TestClient(app) as c:
        yield c


def test_startseite_und_assets(client):
    assert client.get("/").text == "<html>Probe-App</html>"
    r = client.get("/assets/app-123.js")
    assert r.text == "console.log(1)" and "immutable" in r.headers["cache-control"]


def test_unbekannter_pfad_liefert_index(client):
    r = client.get("/projects")
    assert r.status_code == 200 and r.text == "<html>Probe-App</html>"
    assert r.headers["cache-control"] == "no-cache"


def test_bilder_aus_dist(client):
    """Bilder aus public/ liegen im Hauptordner von dist (brand/, hydra/, favicon …) – wie nginx auf dem Server
    ausliefern (Befund Till 31.10.: in der Probe fehlten alle Grafiken)."""
    r = client.get("/brand/logo.webp")
    assert r.status_code == 200 and r.content == b"RIFFwebp" and r.headers["content-type"] == "image/webp"
    assert client.get("/favicon-32.png").content == b"\x89PNG"
    assert "immutable" not in client.get("/brand/logo.webp").headers.get("cache-control", "")


def test_ordner_liefert_index(client):
    assert client.get("/brand").text == "<html>Probe-App</html>"
    assert client.get("/brand/").text == "<html>Probe-App</html>"


@pytest.mark.parametrize("path", ["/../geheim.txt", "/assets/../../geheim.txt", "/%2e%2e/geheim.txt",
                                  "/brand/%2e%2e/%2e%2e/geheim.txt", "/..%2fgeheim.txt"])
def test_nichts_ausserhalb_dist(client, path):
    assert client.get(path).text != "nicht da"


def test_api_weiterleitung_mit_methode_body_query(client, seen):
    r = client.post("/api/auth/login?x=1", json={"u": "admin"}, headers={"Authorization": "Bearer probe-token"})
    assert r.status_code == 201 and r.json() == {"pfad": "/api/auth/login", "q": "x=1"}
    assert r.headers["x-aus-backend"] == "1"
    req = seen[-1]
    assert req.method == "POST" and req.content == b'{"u":"admin"}'
    assert req.headers["authorization"] == "Bearer probe-token"


def test_labor_cookie_wird_nicht_ans_backend_gegeben(client, seen):
    client.get("/api/x", headers={"Cookie": "hh_labor_probe=GEHEIM; probe=1"})
    sent = seen[-1].headers.get("cookie", "")
    assert "GEHEIM" not in sent and "hh_labor_probe" not in sent and "probe=1" in sent


def test_stream_wird_durchgereicht(client):
    with client.stream("GET", "/api/stream") as r:
        chunks = list(r.iter_bytes())
    assert b"".join(chunks) == b"data: a\n\ndata: b\n\n"
    assert r.headers["content-type"].startswith("text/event-stream")


def test_backend_weg(dist):
    def down(req):
        raise httpx.ConnectError("weg")
    app = front.make_app(dist, "http://127.0.0.1:8002", transport=httpx.MockTransport(down))
    with TestClient(app) as c:
        r = c.get("/api/health")
    assert r.status_code == 502


def test_ohne_dist_klare_seite(tmp_path):
    app = front.make_app(tmp_path / "fehlt", "http://127.0.0.1:8002", transport=httpx.MockTransport(lambda r: None))
    with TestClient(app) as c:
        r = c.get("/")
    assert r.status_code == 503 and "noch nicht gebaut" in r.text


def test_symlink_aus_dist_heraus(client, dist):
    (dist / "weg.txt").symlink_to(dist.parent / "geheim.txt")
    assert client.get("/weg.txt").text == "<html>Probe-App</html>"


def test_host_kopf_nicht_weitergereicht(client, seen):
    client.get("/api/x", headers={"Host": "fremd.example"})
    assert seen[-1].headers["host"] == "127.0.0.1:8002"
