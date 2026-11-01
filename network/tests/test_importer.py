"""Sicherung der Dream Machine (Format _work/netz-beweise/udm-*.json.gz) als Vorgeschichte übernehmen."""
from __future__ import annotations

import gzip
import json

import pytest
from backend import importer, store
from backend.errors import NetError


def snapshot(udm_data) -> dict:
    return {"_meta": {"quelle": "test"}, "system_log_90d": {"status": 200, "data": udm_data["system_log"]["data"]},
            "speedtest_90d": {"status": 200, "data": udm_data["speedtests"]},
            "site_hourly_7d": {"status": 200, "data": udm_data["site_hourly"]},
            "site_5min_24h": {"status": 200, "data": udm_data["site_5min"]},
            "site_daily_90d": {"status": 404, "data": None}}


def test_import_json_und_gz(db_ready, udm_data):
    raw = json.dumps(snapshot(udm_data)).encode()
    n = importer.load(gzip.compress(raw))
    assert n["events"] > 30 and n["speedtests"] == 5 and n["hour"] == len(udm_data["site_hourly"]["data"])
    assert n["day"] == 0
    assert importer.load(raw) == {"events": 0, "speedtests": 0, "5min": n["5min"], "hour": n["hour"], "day": 0}
    assert store.events(0, 2_000_000_000)


@pytest.mark.parametrize("raw", [b"kein json", json.dumps({"foo": 1}).encode(), json.dumps([1, 2]).encode(),
                                 gzip.compress(b"\xff\xfe")])
def test_import_falsch(db_ready, raw):
    with pytest.raises(NetError) as e:
        importer.load(raw)
    assert e.value.code == "network_import_invalid"


def test_fehlgeschlagene_abfrage_wird_nicht_uebernommen(db_ready, udm_data):
    snap = {"system_log_90d": {"status": 500, "data": udm_data["system_log"]["data"]},
            "speedtest_90d": {"status": 200, "data": udm_data["speedtests"]}}
    n = importer.load(json.dumps(snap).encode())
    assert n["events"] == 0 and n["speedtests"] == 5
