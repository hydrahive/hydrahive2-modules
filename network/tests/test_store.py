"""Speicher: Messungen, Ereignisse ohne Dubletten, Verlauf der Dream Machine."""
from __future__ import annotations

from backend import store, unifi_parse


def test_messung_speichern_und_lesen(db_ready):
    store.add_sample({"ts": 1000, "inet_loss": 0.0, "inet_rtt_avg": 12.5, "path": "cable"})
    store.add_sample({"ts": 1060, "inet_loss": 100.0, "path": "none"})
    store.add_sample({"ts": 1060, "inet_loss": 50.0, "path": "cable"})
    rows = store.samples(900, 2000)
    assert [(r["ts"], r["path"], r["inet_loss"]) for r in rows] == [(1000, "cable", 0.0), (1060, "cable", 50.0)]
    assert rows[0]["inet_rtt_avg"] == 12.5
    assert store.samples(1001, 2000)[0]["ts"] == 1060
    assert store.samples(0, 1000)[0]["ts"] == 1000
    assert store.latest_sample()["ts"] == 1060


def test_ereignisse_ohne_dubletten(db_ready, udm_data):
    rows = unifi_parse.events(udm_data["system_log"])
    assert store.add_events(rows) == len(rows)
    assert store.add_events(rows) == 0
    got = store.events(0, 2_000_000_000)
    assert len(got) == len(rows) and got == sorted(got, key=lambda r: r["ts"])
    assert store.last_event_ts("udm") == max(r["ts"] for r in rows)
    assert store.last_event_ts("fritz") is None


def test_speedtests_und_verlauf(db_ready, udm_data):
    assert store.add_speedtests(unifi_parse.speedtests(udm_data["speedtests"])) == 5
    assert store.add_speedtests(unifi_parse.speedtests(udm_data["speedtests"])) == 0
    st = store.speedtests(0, 2_000_000_000)
    assert [r["up_mbit"] for r in st] == [51.0, 3.0, 3.0, 0.0, 2.0]
    rows = unifi_parse.series("hour", udm_data["site_hourly"])
    store.put_series(rows)
    store.put_series(rows)
    got = store.series("hour", 0, 2_000_000_000)
    assert len(got) == len(rows)
    assert store.series("5min", 0, 2_000_000_000) == []
