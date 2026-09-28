"""Gesundheitsdaten des eigenen Users löschen (Art. 17 DSGVO).

Spec: patientenakte/SPEC-daten-loeschen.md

Bereiche: apple_health (optional Zeitraum), fhir, ega, all (+ Akte).
Gelöscht wird ausschließlich per user_id/owner_user_id des Aufrufers.
Apple Health geht in kleinen Stapeln (eine Transaktion pro Stapel), damit der
Schreib-Lock der gemeinsamen sessions.db nie lange gehalten wird. Die
Rohsätze sind groß (Median ~11 MB), und secure_delete überschreibt jede
freigegebene Seite.

Kein Agent-Tool: Löschen darf nur der User selbst über die UI auslösen.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

SCOPES = ("apple_health", "fhir", "ega", "all")
# Stapelgrenzen für health_ingest: höchstens so viele Sätze UND so viele Bytes
# pro Transaktion. Gemessen auf einer Kopie der Live-DB: 20 Sätze am Stück
# (~220 MB, secure_delete) hielten den Lock bis 27 s, der Core wartet 5 s.
BATCH_SIZE = 20
BATCH_BYTES = 16 * 1024 * 1024


def _parse_range(scope: str, date_from: str | None, date_to: str | None) -> tuple[str, str] | None:
    if scope not in SCOPES:
        raise ValueError("unknown_scope")
    if date_from is None and date_to is None:
        return None
    if scope != "apple_health":
        raise ValueError("range_only_for_apple_health")
    if date_from is None or date_to is None:
        raise ValueError("range_needs_from_and_to")
    try:
        start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
    except ValueError as exc:
        raise ValueError("invalid_date") from exc
    if start > end:
        raise ValueError("from_after_to")
    return start.isoformat(), end.isoformat()


def _sample_days(payload: str) -> set[str]:
    try:
        data = json.loads(payload)
        data = data.get("data", data)
        metrics = data.get("metrics", [])
        return {s["date"][:10] for m in metrics for s in m.get("data", [])
                if isinstance(s, dict) and isinstance(s.get("date"), str) and s["date"][:10]}
    except (ValueError, AttributeError, TypeError, KeyError):
        return set()


def _raw_ids_in_range(user_id: str, rng: tuple[str, str]) -> tuple[list[str], int]:
    """Rohsätze, deren Samples alle im Zeitraum liegen, plus Anzahl der Grenzfälle.

    Liest Satz für Satz, damit nie mehrere große Payloads gleichzeitig im
    Speicher liegen.
    """
    start, end = rng
    with db() as conn:
        rows = conn.execute(
            "SELECT id, substr(received_at, 1, 10) AS day FROM health_ingest WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    ids, partial = [], 0
    for row in rows:
        with db() as conn:
            payload = conn.execute("SELECT payload FROM health_ingest WHERE id = ?", (row["id"],)).fetchone()
        days = _sample_days(payload["payload"]) if payload else set()
        days = days or {row["day"]}
        inside = {d for d in days if start <= d <= end}
        if inside == days:
            ids.append(row["id"])
        elif inside:
            partial += 1
    return ids, partial


def _batches(user_id: str, ids: list[str] | None) -> list[list[str]]:
    """Teilt die zu löschenden Rohsätze in Stapel nach Anzahl UND Größe."""
    with db() as conn:
        sizes = {r[0]: r[1] or 0 for r in conn.execute(
            "SELECT id, length(payload) FROM health_ingest WHERE user_id = ?", (user_id,))}
    wanted = list(sizes) if ids is None else [i for i in ids if i in sizes]
    batches: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0
    for rid in wanted:
        if current and (len(current) >= BATCH_SIZE or current_bytes + sizes[rid] > BATCH_BYTES):
            batches.append(current)
            current, current_bytes = [], 0
        current.append(rid)
        current_bytes += sizes[rid]
    if current:
        batches.append(current)
    return batches


def _delete_raw(user_id: str, ids: list[str] | None) -> int:
    deleted = 0
    for chunk in _batches(user_id, ids):
        marks = ",".join("?" * len(chunk))
        with db() as conn:
            deleted += conn.execute(
                f"DELETE FROM health_ingest WHERE user_id = ? AND id IN ({marks})", (user_id, *chunk),
            ).rowcount
    return deleted


def _delete_apple_health(user_id: str, rng: tuple[str, str] | None) -> tuple[dict[str, int], int]:
    ids, partial = _raw_ids_in_range(user_id, rng) if rng else (None, 0)
    raw = _delete_raw(user_id, ids)
    with db() as conn:
        if rng:
            daily = conn.execute(
                "DELETE FROM health_daily WHERE user_id = ? AND date BETWEEN ? AND ?", (user_id, *rng),
            ).rowcount
        else:
            daily = conn.execute("DELETE FROM health_daily WHERE user_id = ?", (user_id,)).rowcount
    return {"health_ingest": raw, "health_daily": daily}, partial


def _delete_by_user(table: str, user_id: str) -> int:
    with db() as conn:
        return conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,)).rowcount


def delete_scope(user_id: str, scope: str, date_from: str | None = None,
                 date_to: str | None = None) -> dict[str, Any]:
    """Löscht einen Bereich für genau diesen User. Wirft ValueError bei ungültiger Anfrage."""
    rng = _parse_range(scope, date_from, date_to)
    deleted: dict[str, int] = {}
    partial = 0
    if scope in ("apple_health", "all"):
        counts, partial = _delete_apple_health(user_id, rng)
        deleted.update(counts)
    if scope in ("fhir", "all"):
        deleted["fhir_resources"] = _delete_by_user("fhir_resources", user_id)
    if scope in ("ega", "all"):
        deleted["ega_records"] = _delete_by_user("ega_records", user_id)
    if scope == "all":
        with db() as conn:  # Kind-Tabellen akte_* gehen per ON DELETE CASCADE mit
            deleted["akte_patient"] = conn.execute(
                "DELETE FROM akte_patient WHERE owner_user_id = ?", (user_id,),
            ).rowcount
    logger.info("akte_data_deletion user=%s scope=%s range=%s deleted=%s raw_kept_partial=%d",
                user_id, scope, rng, deleted, partial)
    result: dict[str, Any] = {"scope": scope, "deleted": deleted}
    if scope in ("apple_health", "all"):
        result["raw_kept_partial"] = partial
    return result


def overview(user_id: str) -> dict[str, Any]:
    """Anzahlen pro Bereich für die Lösch-Ansicht (ohne Inhalte)."""
    with db() as conn:
        raw = conn.execute("SELECT COUNT(*) FROM health_ingest WHERE user_id = ?", (user_id,)).fetchone()[0]
        daily = conn.execute(
            "SELECT COUNT(*), MIN(date), MAX(date) FROM health_daily WHERE user_id = ?", (user_id,),
        ).fetchone()
        fhir = conn.execute("SELECT COUNT(*) FROM fhir_resources WHERE user_id = ?", (user_id,)).fetchone()[0]
        ega = conn.execute("SELECT COUNT(*) FROM ega_records WHERE user_id = ?", (user_id,)).fetchone()[0]
        akte = conn.execute(
            "SELECT 1 FROM akte_patient WHERE owner_user_id = ? LIMIT 1", (user_id,),
        ).fetchone() is not None
    return {
        "apple_health": {"raw": raw, "daily": daily[0], "first_day": daily[1], "last_day": daily[2]},
        "fhir": fhir,
        "ega": ega,
        "akte": akte,
    }
