"""Antworten der Dream Machine lesen (echte Antworten vom 01.11.2026 in fixtures/udm.json)."""
from __future__ import annotations

import pytest
from backend import unifi_parse as up


@pytest.mark.parametrize("text,sec", [("8h 31m", 30660), ("21s", 21), ("1m 13s", 73), ("1d 2h", 93600),
                                      ("3m 6s", 186), ("", None), (None, None), ("viel", None), ("5x", None)])
def test_dauer_in_sekunden(text, sec):
    assert up.duration_s(text) == sec


def test_health_liest_internet_und_speedtest(udm_data):
    h = up.health(udm_data["health"])
    assert h["wan_status"] == "ok"
    assert h["isp"] == "Vodafone Germany"
    assert h["availability"] == 100.0
    assert h["latency_ms"] == 40
    assert h["drops"] == 11
    assert h["speedtest"] == {"down": 270.0, "up": 2.0, "ping": 27, "at": 1793556215}


def test_health_ohne_wan_teile_liefert_leere_werte():
    h = up.health({"data": [{"subsystem": "wlan", "status": "ok"}]})
    assert h["wan_status"] is None and h["speedtest"] is None and h["isp"] is None


def test_ereignisse_nur_internet_mit_dauer_und_ohne_fremde(udm_data):
    rows = up.events(udm_data["system_log"])
    assert all(r["source"] == "udm" for r in rows)
    assert "x-client-1" not in {r["event_id"] for r in rows}
    first_fail = next(r for r in rows if r["kind"] == "wan_failed")
    assert first_fail["ts"] == 1793539069 or first_fail["ts"] > 1_700_000_000
    restored = [r for r in rows if r["kind"] == "wan_restored"]
    assert restored[0]["duration_s"] == 8 * 3600 + 31 * 60
    assert restored[0]["wan"] == "Internet 1"
    kinds = {r["kind"] for r in rows}
    assert {"wan_failed", "wan_restored", "packet_loss"} <= kinds
    lat = [r for r in rows if r["kind"] == "high_latency"]
    assert lat and lat[0]["detail"] == "303"


def test_ereignis_zeit_in_sekunden(udm_data):
    raw = next(e for e in udm_data["system_log"]["data"] if e["category"] == "INTERNET_AND_WAN")
    row = next(r for r in up.events(udm_data["system_log"]) if r["event_id"] == raw["id"])
    assert row["ts"] == raw["timestamp"] // 1000


def test_speedtests(udm_data):
    rows = up.speedtests(udm_data["speedtests"])
    assert len(rows) == 5
    first = min(rows, key=lambda r: r["ts"])
    assert (first["down_mbit"], first["up_mbit"], first["ping_ms"]) == (947.0, 51.0, 9)
    assert first["server"] == "Frankfurt am Main"
    assert first["source"] == "udm"


def test_verlauf(udm_data):
    rows = up.series("hour", udm_data["site_hourly"])
    assert rows and all(r["scale"] == "hour" for r in rows)
    raw = udm_data["site_hourly"]["data"][0]
    assert rows[0]["ts"] == raw["time"] // 1000
    assert rows[0]["latency_min"] == raw.get("latency_min")
    assert rows[0]["rx_bytes"] == raw["wan-rx_bytes"]


def test_verlauf_unbekannte_skala():
    with pytest.raises(ValueError):
        up.series("woche", {"data": []})
