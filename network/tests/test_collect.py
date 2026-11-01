"""Sammler: eigene Messung jede Minute, Dream Machine alle 5 Minuten / stündlich (Geräte gemockt)."""
from __future__ import annotations

import pytest
from backend import collect, config_store, fritz_igd, probe, store
from backend.errors import NetError

OKP = {"loss": 0.0, "min": 8.0, "avg": 9.0, "max": 12.0, "mdev": 1.0}
LOST = {"loss": 100.0, "min": None, "avg": None, "max": None, "mdev": None}


@pytest.fixture
def fakes(monkeypatch):
    st = {"ping": {}, "fritz": {"link": "Up", "access": "Cable", "conn": "Connected", "uptime_s": 1, "ext_ip": "37.24.1.2",
                                "up_max_mbit": 52.48, "down_max_mbit": 1126.4}, "pinged": []}

    async def ping(target, count=5):
        st["pinged"].append(target)
        return st["ping"].get(target, OKP)

    async def fstatus(host):
        st["fritz_host"] = host
        return st["fritz"]
    monkeypatch.setattr(probe, "ping", ping)
    monkeypatch.setattr(fritz_igd, "status", fstatus)
    return st


async def test_minute_ohne_einrichtung_misst_internet(db_ready, fakes):
    s = await collect.tick_minute(now=600)
    assert s["ts"] == 600 and s["path"] == "unknown"
    assert set(fakes["pinged"]) == set(collect.INTERNET_TARGETS)
    assert store.latest_sample()["inet_loss"] == 0.0


async def test_minute_mit_geraeten_und_weg(db_ready, fakes):
    config_store.save(owner="boss", udm_url="https://192.168.178.1", udm_credential="udm", fritz_host="192.168.3.1",
                      fritz_credential=None, plan_down_mbit=1000, plan_up_mbit=50, plan_price_eur=None)
    s = await collect.tick_minute(now=1260)
    assert s["ts"] == 1260 and s["path"] == "cable"
    assert {"192.168.178.1", "192.168.3.1"} <= set(fakes["pinged"])
    assert s["lan_rtt"] == 9.0 and s["fritz_link"] == "Up" and s["fritz_access"] == "Cable"
    fakes["fritz"] = {**fakes["fritz"], "link": "Down"}
    assert (await collect.tick_minute(now=1320))["path"] == "mobile"
    for t in collect.INTERNET_TARGETS:
        fakes["ping"][t] = LOST
    assert (await collect.tick_minute(now=1380))["path"] == "none"


async def test_minute_runde_auf_minute(db_ready, fakes):
    assert (await collect.tick_minute(now=1299))["ts"] == 1260


class FakeUdm:
    def __init__(self, data, fail=None):
        self.data, self.fail, self.calls = data, fail, []

    async def get(self, path):
        self.calls.append(("GET", path, None))
        if self.fail:
            raise NetError(self.fail)
        if path.endswith("stat/health"):
            return self.data["health"]
        raise AssertionError(path)

    async def post(self, path, body):
        self.calls.append(("POST", path, body))
        if "system-log" in path:
            return self.data["system_log"] if body["pageNumber"] == 0 else {"data": []}
        if "archive.speedtest" in path:
            return self.data["speedtests"]
        if "5minutes.site" in path:
            return self.data["site_5min"]
        if "hourly.site" in path or "daily.site" in path:
            return self.data["site_hourly"]
        raise AssertionError(path)


@pytest.fixture
def udm(monkeypatch, udm_data):
    holder = {"udm": FakeUdm(udm_data)}
    monkeypatch.setattr(collect, "_udm", lambda cfg: holder["udm"])
    config_store.save(owner="boss", udm_url="https://192.168.178.1", udm_credential="udm", fritz_host=None,
                      fritz_credential=None, plan_down_mbit=None, plan_up_mbit=None, plan_price_eur=None)
    return holder


async def test_udm_status_und_5min(db_ready, udm):
    await collect.tick_udm(now=1_793_560_000)
    cfg = config_store.get()
    assert cfg["last_status"]["isp"] == "Vodafone Germany" and cfg["last_error"] is None
    assert cfg["last_status_at"] == 1_793_560_000
    assert store.series("5min", 0, 2_000_000_000)
    assert store.speedtests(0, 2_000_000_000)[-1]["up_mbit"] == 2.0


async def test_udm_fehler_wird_gemerkt(db_ready, udm, udm_data):
    udm["udm"] = FakeUdm(udm_data, fail="network_auth_failed")
    await collect.tick_udm(now=5)
    assert config_store.get()["last_error"] == "network_auth_failed"


async def test_stuendlich_ereignisse_speedtests_verlauf(db_ready, udm):
    n = await collect.tick_hourly(now=1_793_560_000)
    assert n["events"] > 30 and n["speedtests"] == 5
    first = next(c for c in udm["udm"].calls if "system-log" in c[1])[2]
    assert first["timestampFrom"] == (1_793_560_000 - 90 * 86400) * 1000
    assert store.series("hour", 0, 2_000_000_000) and store.series("day", 0, 2_000_000_000)
    udm["udm"].calls.clear()
    await collect.tick_hourly(now=1_793_563_600)
    nxt = next(c for c in udm["udm"].calls if "system-log" in c[1])[2]
    assert nxt["timestampFrom"] == (store.last_event_ts("udm") - 7200) * 1000


async def test_ohne_einrichtung_nichts(db_ready, monkeypatch):
    monkeypatch.setattr(collect, "_udm", lambda cfg: (_ for _ in ()).throw(AssertionError("kein Abruf")))
    await collect.tick_udm(now=1)
    assert await collect.tick_hourly(now=1) == {"events": 0, "speedtests": 0}
