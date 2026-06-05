"""C2 — News: Client-Transform + /news-Route (Auth, Validierung, Cache)."""
from __future__ import annotations

from backend import news

PREFIX = "/api/modules/cryptoboard"


async def test_latest_flacht_ab(monkeypatch):
    async def fake_get(params):
        return {"Data": [{
            "id": "1", "title": "BTC steigt", "url": "http://x", "source": "coindesk",
            "source_info": {"name": "CoinDesk"}, "body": "lang " * 500,
            "imageurl": "img", "published_on": 1700000000, "categories": "BTC",
        }]}

    monkeypatch.setattr(news, "_get", fake_get)
    out = await news.latest()
    assert out[0]["title"] == "BTC steigt"
    assert out[0]["source"] == "CoinDesk"  # source_info bevorzugt
    assert len(out[0]["body"]) <= 600  # gekürzt
    assert out[0]["published_at"] == 1700000000


async def test_latest_leerer_payload(monkeypatch):
    async def fake_get(params):
        return "kaputt"

    monkeypatch.setattr(news, "_get", fake_get)
    assert await news.latest() == []


def test_news_route_braucht_auth(client):
    assert client.get(f"{PREFIX}/news").status_code == 401


def test_news_route_durchstich(client, auth_headers, monkeypatch):
    async def fake_latest(categories=None, lang="EN"):
        return [{"id": "1", "title": "Hallo", "url": "u", "source": "s",
                 "body": "b", "image": None, "published_at": 1, "categories": "BTC"}]

    monkeypatch.setattr(news, "latest", fake_latest)
    r = client.get(f"{PREFIX}/news?categories=BTC&lang=EN", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()[0]["title"] == "Hallo"


def test_news_route_lehnt_ungueltige_categories_ab(client, auth_headers):
    r = client.get(f"{PREFIX}/news?categories=BTC;DROP", headers=auth_headers)
    assert r.status_code == 400
