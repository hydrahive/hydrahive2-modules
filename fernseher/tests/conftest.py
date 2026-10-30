"""Eigenständige Test-Fixtures fürs Fernseher-Modul (wie homeassistant/tests/conftest.py).

Kein echter Netzverkehr: Der Fernseher wird über `fake_tv` nachgebaut (client._post wird ersetzt).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest  # noqa: E402
from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks, über conftest registriert
    isolated_root,
    only_own_files,
    only_own_rows,
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
    remove_test_tree,
)
from fastapi.testclient import TestClient  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

MOD_PREFIX = "/api/modules/fernseher"
PSK = "geheim-psk-4711"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)
        import bcrypt
        ph = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "testuser": {"password_hash": ph, "role": "user"},
            "admin": {"password_hash": ph, "role": "admin"},
        }, indent=2))
        from backend.routes import router
        from hydrahive.api import main
        main.app.include_router(router, prefix=MOD_PREFIX)
        yield tmp_path


@pytest.fixture(autouse=True)
def _settings_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    init_db()
    apply_module_migrations("fernseher", MODULE_DIR / "migrations")
    from backend import client as tv_client
    tv_client.clear_cache()
    with only_own_rows("module_fernseher_settings"):
        yield
    tv_client.clear_cache()


@pytest.fixture
def client(setup_test_env):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    from hydrahive.api import main
    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = original


def login(c, name: str) -> dict:
    r = c.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


CHANNELS = [
    {"dispNum": "001", "title": "Das Erste HD", "uri": "tv:dvbt?trip=1.1051.10301&srvName=Das Erste HD"},
    {"dispNum": "002", "title": "ZDF HD", "uri": "tv:dvbt?trip=1.1079.11110&srvName=ZDF HD"},
    {"dispNum": "006", "title": "SAT.1", "uri": "tv:dvbt?trip=61441.10019.53626&srvName=SAT.1"},
    {"dispNum": "007", "title": "kabel eins", "uri": "tv:dvbt?trip=61441.10005.53622&srvName=kabel eins"},
    {"dispNum": "010", "title": "ZDFinfo HD", "uri": "tv:dvbt?trip=1.1079.11170&srvName=ZDFinfo HD"},
    {"dispNum": "012", "title": "ZDFneo HD", "uri": "tv:dvbt?trip=61441.10009.11130&srvName=ZDFneo HD"},
]
APPS = [
    {"title": "Plex", "uri": "com.sony.dtv.com.plexapp.android.com.plexapp.plex.activities.SplashActivity"},
    {"title": "Netflix", "uri": "com.sony.dtv.com.netflix.ninja.com.netflix.ninja.MainActivity"},
    {"title": "YouTube", "uri": "com.sony.dtv.com.google.android.youtube.tv.com.google.android.apps.youtube.tv.activity.ShellActivity"},
]


class FakeTV:
    """Nachgebauter Sony-Fernseher (JSON-RPC wie am echten KD-60XF8305 gemessen)."""

    def __init__(self) -> None:
        self.power = "active"
        self.volume = 14
        self.mute = False
        self.playing = CHANNELS[2]
        self.calls: list[tuple[str, str, list, str, dict]] = []
        self.psk = PSK
        self.mode = "ok"          # ok | unreachable | needs_restart
        self.app_open = False     # wie am echten TV: erstes setPlayContent holt nur aus der App
        self.ignore_switch = False
        self.output = "speaker"   # speaker | audioSystem (Ton über den Yamaha-Receiver, gemessen 29.10.)

    def handle(self, ip: str, service: str, method: str, params: list, version: str, headers: dict):
        self.calls.append((service, method, params, version, dict(headers)))
        if self.mode == "unreachable":
            raise TimeoutError("zeitüberschreitung")
        if self.mode == "needs_restart":
            return 404, {"error": [404, "Not Found"]}
        if service == "system" and method == "getInterfaceInformation":
            return 200, {"result": [{"productName": "BRAVIA", "modelName": "KD-60XF8305", "interfaceVersion": "5.4.0"}]}
        if headers.get("X-Auth-PSK") != self.psk:
            return 200, {"error": [403, "Forbidden"]}
        p = params[0] if params else {}
        if (service, method) == ("system", "getPowerStatus"):
            return 200, {"result": [{"status": self.power}]}
        if (service, method) == ("system", "setPowerStatus"):
            self.power = "active" if p.get("status") else "standby"
            return 200, {"result": []}
        if (service, method) == ("avContent", "getPlayingContentInfo"):
            if self.power != "active":
                return 200, {"error": [40005, "Display Is Turned off"]}
            if self.app_open:
                return 200, {"error": [7, "Illegal State"]}
            return 200, {"result": [{**self.playing, "source": "tv:dvbt", "programTitle": "Sendung " + self.playing["title"]}]}
        if (service, method) == ("avContent", "getContentList"):
            if version not in ("1.0", "1.2"):
                return 200, {"error": [3, "Illegal Argument"]}
            st, cnt = p.get("stIdx", 0), p.get("cnt", 50)
            return 200, {"result": [CHANNELS[st:st + cnt]]}
        if (service, method) == ("avContent", "setPlayContent"):
            hit = [c for c in CHANNELS if c["uri"] == p.get("uri")]
            if not hit:
                return 200, {"error": [3, "Illegal Argument"]}
            if self.ignore_switch:
                return 200, {"result": []}
            if self.app_open:
                self.app_open = False
                return 200, {"result": []}
            self.playing = hit[0]
            return 200, {"result": []}
        if (service, method) == ("audio", "getVolumeInformation"):
            if self.power != "active":                 # gemessen 29.10.: im Standby 40005
                return 200, {"error": [40005, "Display Is Turned off"]}
            if self.output == "audioSystem":         # gemessen 29.10.: Receiver liefert eigene Skala
                return 200, {"result": [[{"target": "speaker", "volume": self.volume, "mute": self.mute,
                                          "maxVolume": 100, "minVolume": 0, "outputTerminal": "audioSystem"}]]}
            return 200, {"result": [[{"target": "speaker", "volume": self.volume, "mute": self.mute,
                                      "maxVolume": 100, "minVolume": 0, "outputTerminal": self.output}]]}
        if (service, method) == ("audio", "setAudioVolume"):
            v = str(p.get("volume"))
            self.volume = self.volume + int(v) if v[:1] in "+-" else int(v)
            return 200, {"result": [0]}
        if (service, method) == ("audio", "setAudioMute"):
            self.mute = bool(p.get("status"))
            return 200, {"result": [0]}
        if (service, method) == ("appControl", "getApplicationList"):
            return 200, {"result": [APPS]}
        if (service, method) == ("appControl", "setActiveApp"):
            return 200, {"result": []} if any(a["uri"] == p.get("uri") for a in APPS) else {"error": [3, "x"]}
        return 200, {"error": [12, "No Such Method"]}


@pytest.fixture
def fake_tv(monkeypatch):
    tv = FakeTV()
    from backend import client as tv_client

    async def no_wait(_s):
        return None
    monkeypatch.setattr(tv_client, "_sleep", no_wait)

    async def fake_post(ip, service, method, params, version, psk):
        headers = {"X-Auth-PSK": psk} if psk else {}
        return tv.handle(ip, service, method, params, version, headers)

    monkeypatch.setattr(tv_client, "_post", fake_post)
    return tv


@pytest.fixture
def configured(fake_tv):
    from backend import settings_store
    settings_store.save(name="TV Wohnzimmer", address="192.168.178.186", psk=PSK, volume_limit=60, user="admin")
    return fake_tv
