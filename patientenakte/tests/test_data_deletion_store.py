"""Löschen von Gesundheitsdaten: Store-Ebene (Spec patientenakte/SPEC-daten-loeschen.md)."""
from __future__ import annotations

import json

import pytest

from hydrahive.db._utils import uuid7
from hydrahive.db.connection import db

from backend import data_deletion, entities, patients


def _raw(user: str, sample_days: list[str], received: str = "2026-05-15T20:00:00+00:00") -> str:
    """Rohsatz + Tageswerte wie beim echten Ingest (Samples mit Datum)."""
    from backend.health_store import _process_payload_to_daily
    payload = {"data": {"metrics": [{
        "name": "step_count", "units": "count",
        "data": [{"date": f"{d} 08:00:00 +0200", "qty": 100} for d in sample_days],
    }]}}
    rid = uuid7()
    with db() as conn:
        conn.execute(
            "INSERT INTO health_ingest (id, received_at, user_id, payload) VALUES (?, ?, ?, ?)",
            (rid, received, user, json.dumps(payload)),
        )
        _process_payload_to_daily(payload, user, conn)
    return rid


def _count(table: str, where: str, *args) -> int:
    with db() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args).fetchone()[0]


def _fhir(user: str, rid: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO fhir_resources (id, user_id, resource_type, resource_id, resource_json) "
            "VALUES (?, ?, 'Condition', ?, '{}')", (uuid7(), user, rid))


def _ega(user: str, rid: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO ega_records (id, user_id, dto_type, record_json) VALUES (?, ?, 'X', '{}')",
            (rid, user))


def test_apple_health_all_deletes_only_own_user():
    _raw("u1", ["2025-01-01"])
    _raw("u1", ["2025-06-01", "2025-06-02"])
    _raw("u2", ["2025-01-01"])

    result = data_deletion.delete_scope("u1", "apple_health")

    assert result["deleted"] == {"health_ingest": 2, "health_daily": 3}
    assert _count("health_ingest", "user_id = ?", "u1") == 0
    assert _count("health_daily", "user_id = ?", "u1") == 0
    assert _count("health_ingest", "user_id = ?", "u2") == 1
    assert _count("health_daily", "user_id = ?", "u2") == 1


def test_apple_health_range_keeps_outside_and_straddling_raw():
    inside = _raw("u1", ["2025-06-10", "2025-06-11"])
    outside = _raw("u1", ["2025-08-01"])
    straddle = _raw("u1", ["2025-06-30", "2025-07-01"])

    result = data_deletion.delete_scope("u1", "apple_health", date_from="2025-06-01", date_to="2025-06-30")

    with db() as conn:
        left = {r[0] for r in conn.execute("SELECT id FROM health_ingest WHERE user_id = 'u1'")}
        days = {r[0] for r in conn.execute("SELECT date FROM health_daily WHERE user_id = 'u1'")}
    assert inside not in left
    assert {outside, straddle} <= left
    assert days == {"2025-07-01", "2025-08-01"}, "Tageswerte im Zeitraum weg, außerhalb bleiben"
    assert result["deleted"] == {"health_ingest": 1, "health_daily": 3}
    assert result["raw_kept_partial"] == 1


def test_apple_health_range_raw_without_samples_uses_received_day():
    from hydrahive.db.connection import db as _db
    rid_in, rid_out = uuid7(), uuid7()
    with _db() as conn:
        conn.executemany(
            "INSERT INTO health_ingest (id, received_at, user_id, payload) VALUES (?, ?, 'u1', ?)",
            [(rid_in, "2025-06-15T10:00:00+00:00", '{"data": {"metrics": []}}'),
             (rid_out, "2025-09-15T10:00:00+00:00", "kein json")])
    data_deletion.delete_scope("u1", "apple_health", date_from="2025-06-01", date_to="2025-06-30")
    assert _count("health_ingest", "id = ?", rid_in) == 0
    assert _count("health_ingest", "id = ?", rid_out) == 1


def test_apple_health_deletes_in_small_transactions(monkeypatch):
    monkeypatch.setattr(data_deletion, "BATCH_SIZE", 2)
    for i in range(5):
        _raw("u1", [f"2025-01-0{i + 1}"])
    result = data_deletion.delete_scope("u1", "apple_health")
    assert result["deleted"]["health_ingest"] == 5
    assert _count("health_ingest", "user_id = ?", "u1") == 0


def test_apple_health_batches_are_bounded_by_bytes(monkeypatch):
    monkeypatch.setattr(data_deletion, "BATCH_BYTES", 1)
    ids = [_raw("u1", [f"2025-02-0{i + 1}"]) for i in range(3)]
    batches = data_deletion._batches("u1", None)
    assert sorted(i for b in batches for i in b) == sorted(ids)
    assert all(len(b) == 1 for b in batches), "ein großer Satz pro Transaktion"


def test_fhir_and_ega_delete_only_own_user():
    _fhir("u1", "a")
    _fhir("u2", "a")
    _ega("u1", "e1")
    _ega("u2", "e2")

    assert data_deletion.delete_scope("u1", "fhir")["deleted"] == {"fhir_resources": 1}
    assert data_deletion.delete_scope("u1", "ega")["deleted"] == {"ega_records": 1}
    assert _count("fhir_resources", "user_id = ?", "u2") == 1
    assert _count("ega_records", "user_id = ?", "u2") == 1


def test_all_removes_akte_with_children_imports_and_health():
    pid = patients.create("u1", {"slug": "ich"})
    entities.create("u1", pid, "conditions", {"name": "Test-Diagnose"})
    other = patients.create("u2", {"slug": "du"})
    entities.create("u2", other, "conditions", {"name": "Fremd"})
    _raw("u1", ["2025-01-01"])
    _fhir("u1", "a")
    _ega("u1", "e1")

    result = data_deletion.delete_scope("u1", "all")

    assert result["deleted"]["akte_patient"] == 1
    assert _count("akte_patient", "owner_user_id = ?", "u1") == 0
    assert _count("akte_condition", "patient_id = ?", pid) == 0, "Kind-Einträge per CASCADE weg"
    assert _count("akte_condition", "patient_id = ?", other) == 1
    for table in ("health_ingest", "health_daily", "fhir_resources", "ega_records"):
        assert _count(table, "user_id = ?", "u1") == 0, table


def test_overview_counts_only_own_data():
    _raw("u1", ["2025-01-01", "2025-03-05"])
    _raw("u2", ["2024-01-01"])
    _fhir("u1", "a")
    patients.create("u1", {"slug": "ich"})

    ov = data_deletion.overview("u1")

    assert ov["apple_health"] == {"raw": 1, "daily": 2, "first_day": "2025-01-01", "last_day": "2025-03-05"}
    assert ov["fhir"] == 1
    assert ov["ega"] == 0
    assert ov["akte"] is True


@pytest.mark.parametrize(("scope", "kwargs"), [
    ("unbekannt", {}),
    ("fhir", {"date_from": "2025-01-01", "date_to": "2025-01-02"}),
    ("apple_health", {"date_from": "2025-01-01"}),
    ("apple_health", {"date_from": "2025-02-01", "date_to": "2025-01-01"}),
    ("apple_health", {"date_from": "01.01.2025", "date_to": "2025-02-01"}),
])
def test_invalid_requests_delete_nothing(scope, kwargs):
    _raw("u1", ["2025-01-01"])
    with pytest.raises(ValueError):
        data_deletion.delete_scope("u1", scope, **kwargs)
    assert _count("health_ingest", "user_id = ?", "u1") == 1
