"""S2 Vorschaubilder (Spec §12.3): Bildschirmfoto mit Chromium, ohne Shell, Zeitgrenze, nie Pflicht."""
from __future__ import annotations

from pathlib import Path

import pytest
from backend import preview, store
from conftest import MOD_PREFIX, PROJECT_ID

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _d():
    return store.create(username="testuser", project_id=PROJECT_ID, session_id="s", agent_id=None, title="T",
                        kind="workflow", html="<html>x</html>", source="{}", source_ext="json")


@pytest.fixture
def fake_chrome(monkeypatch):
    state = {"calls": [], "fail": False}

    def run(argv, *, timeout, env):
        state["calls"].append({"argv": list(argv), "timeout": timeout, "env": dict(env)})
        if state["fail"]:
            return 1
        out = next(a for a in argv if a.startswith("--screenshot=")).split("=", 1)[1]
        Path(out).write_bytes(PNG)
        return 0

    monkeypatch.setattr(preview, "_run", run)
    monkeypatch.setattr(preview.chrome, "find", lambda: "/opt/chrome/chrome")
    return state


def test_make_writes_png_and_marks_ok(store_dir, fake_chrome):
    d = _d()
    assert preview.make(d["id"]) is True
    assert (store_dir / d["id"] / "vorschau.png").read_bytes() == PNG
    assert store.get(d["id"])["preview_state"] == "ok"
    argv = fake_chrome["calls"][0]["argv"]
    assert argv[0] == "/opt/chrome/chrome"
    for flag in ("--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,750"):
        assert flag in argv
    assert argv[-1] == f"file://{store_dir / d['id'] / 'diagramm.html'}"
    assert fake_chrome["calls"][0]["timeout"] == preview.TIMEOUT_SECONDS == 60
    assert "HH_SECRET_KEY" not in fake_chrome["calls"][0]["env"]


def test_without_chrome_no_image_and_marked_missing(store_dir, fake_chrome, monkeypatch):
    monkeypatch.setattr(preview.chrome, "find", lambda: None)
    d = _d()
    assert preview.make(d["id"]) is False
    assert fake_chrome["calls"] == [] and store.get(d["id"])["preview_state"] == "fehlt"


def test_failed_screenshot_is_remembered(store_dir, fake_chrome):
    fake_chrome["fail"] = True
    d = _d()
    assert preview.make(d["id"]) is False
    assert store.get(d["id"])["preview_state"] == "fehler"
    assert not (store_dir / d["id"] / "vorschau.png").exists()


def test_failed_screenshot_leaves_no_half_image(store_dir, monkeypatch):
    """Chromium schreibt eine Datei, meldet aber Fehler → kein halbes Bild bleiben lassen."""
    monkeypatch.setattr(preview.chrome, "find", lambda: "/opt/chrome/chrome")

    def broken(argv, *, timeout, env):
        out = next(a for a in argv if a.startswith("--screenshot=")).split("=", 1)[1]
        Path(out).write_bytes(b"halb")
        return 1
    monkeypatch.setattr(preview, "_run", broken)
    d = _d()
    assert preview.make(d["id"]) is False
    assert not (store_dir / d["id"] / "vorschau.png").exists()


def test_timeout_does_not_raise(store_dir, monkeypatch):
    monkeypatch.setattr(preview.chrome, "find", lambda: "/opt/chrome/chrome")

    def slow(argv, *, timeout, env):
        raise preview.subprocess.TimeoutExpired(argv, timeout)
    monkeypatch.setattr(preview, "_run", slow)
    d = _d()
    assert preview.make(d["id"]) is False and store.get(d["id"])["preview_state"] == "fehler"


def test_route_serves_png(client, auth_headers, other_headers, store_dir, fake_chrome):
    d = _d()
    preview.make(d["id"])
    r = client.get(f"{MOD_PREFIX}/preview/{d['id']}", headers=auth_headers)
    assert r.status_code == 200 and r.content == PNG and r.headers["content-type"] == "image/png"
    assert client.get(f"{MOD_PREFIX}/preview/{d['id']}", headers=other_headers).status_code == 404


def test_route_makes_missing_preview_once(client, auth_headers, store_dir, fake_chrome):
    d = _d()
    assert store.get(d["id"])["preview_state"] is None
    assert client.get(f"{MOD_PREFIX}/preview/{d['id']}", headers=auth_headers).status_code == 200
    assert len(fake_chrome["calls"]) == 1


def test_route_does_not_retry_after_failure(client, auth_headers, store_dir, fake_chrome):
    fake_chrome["fail"] = True
    d = _d()
    assert client.get(f"{MOD_PREFIX}/preview/{d['id']}", headers=auth_headers).status_code == 404
    assert client.get(f"{MOD_PREFIX}/preview/{d['id']}", headers=auth_headers).status_code == 404
    assert len(fake_chrome["calls"]) == 1


def test_real_runner_uses_no_shell(monkeypatch, tmp_path):
    seen = {}

    def fake(argv, **kw):
        seen.update(kw, argv=argv)
        return preview.subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(preview.subprocess, "run", fake)
    assert preview._run(["chrome", "x"], timeout=5, env={"A": "1"}) == 0
    assert seen.get("shell", False) is False and seen["timeout"] == 5 and seen["env"] == {"A": "1"}
    assert seen["stdin"] == preview.subprocess.DEVNULL
