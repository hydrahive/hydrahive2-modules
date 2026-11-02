"""Kleine normalisierte Berichte aus den Analyseergebnissen.

Der Bericht trennt, wie SPEC §11 es verlangt:
Beobachtet, Abgeleitet, Vermutet, Unbekannt und die naechste erlaubte
Pruefung. Text aus dem Ziel gilt als nicht vertrauenswuerdig und wird
gekennzeichnet.
"""
from __future__ import annotations

import json

from .files import cases_root

MAX_OBSERVATIONS = 200
MAX_TEXT = 400


def _load_result(case_id: str, relative_path: str | None) -> dict:
    """Ergebnisdatei eines Jobs laden. Fehlt sie, bleibt das Ergebnis leer."""
    if not relative_path:
        return {}
    root = cases_root(case_id)
    target = root / relative_path
    try:
        resolved = target.resolve()
        resolved.relative_to(root.resolve())
        return json.loads(resolved.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _collect(payload: dict) -> list[str]:
    """Beobachtungen aus einem REA-Ergebnis in kurze Zeilen ueberfuehren."""
    lines: list[str] = []
    for key in ("observations", "evidence", "findings", "summary", "result"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(value.strip()[:MAX_TEXT])
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    lines.append(item.strip()[:MAX_TEXT])
                elif isinstance(item, dict):
                    label = item.get("type") or item.get("kind") or item.get("name")
                    detail = item.get("value") or item.get("text") or item.get("summary")
                    if detail:
                        lines.append(f"{label}: {detail}"[:MAX_TEXT])
                    elif label:
                        lines.append(str(label)[:MAX_TEXT])
    lines.extend(_from_normalized(payload))
    return lines[:MAX_OBSERVATIONS]


def _from_normalized(payload: dict) -> list[str]:
    """Aussagen aus dem normalisierten REA-Ergebnis uebernehmen."""
    normalized = payload.get("normalized_result")
    if not isinstance(normalized, dict):
        return []
    lines: list[str] = []
    for key, value in normalized.items():
        if isinstance(value, str) and value.strip():
            lines.append(f"{key}: {value.strip()}"[:MAX_TEXT])
        elif isinstance(value, list) and value and all(isinstance(i, str) for i in value):
            lines.append(f"{key}: {', '.join(value[:8])}"[:MAX_TEXT])
    return lines


def _bundle_facts(payload: dict) -> list[str]:
    """Belegbare Fakten aus dem Evidence-Bundle ziehen."""
    bundle = payload.get("evidence")
    if not isinstance(bundle, dict):
        return []
    lines: list[str] = []
    for record in bundle.get("records", [])[:50]:
        if not isinstance(record, dict):
            continue
        normalized = record.get("normalized_result")
        if isinstance(normalized, dict):
            for key, value in normalized.items():
                if isinstance(value, str) and value.strip():
                    lines.append(f"{key}: {value.strip()}"[:MAX_TEXT])
                elif isinstance(value, list) and value and all(isinstance(i, str) for i in value):
                    lines.append(f"{key}: {', '.join(value[:8])}"[:MAX_TEXT])
    for artifact in bundle.get("artifacts", [])[:10]:
        if isinstance(artifact, dict):
            digest = artifact.get("digest", {})
            sha = digest.get("sha256") if isinstance(digest, dict) else None
            if sha:
                lines.append(f"Belegt: SHA-256 {sha}"[:MAX_TEXT])
            if artifact.get("format"):
                lines.append(f"Belegt: Format {artifact['format']}"[:MAX_TEXT])
    return lines[:MAX_OBSERVATIONS]


def build_report(case: dict) -> dict:
    """Bericht zu einem Fall aus den Ergebnissen seiner Jobs bauen."""
    observed: list[str] = []
    jobs = []
    for job in case.get("jobs", []):
        payload = _load_result(case["id"], job.get("result_path"))
        lines = _collect(payload)
        lines.extend(_bundle_facts(payload))
        observed.extend(lines)
        jobs.append({
            "id": job["id"],
            "artifact_id": job["artifact_id"],
            "analysis_type": job["analysis_type"],
            "status": job["status"],
            "progress": job["progress"],
            "error_code": job.get("error_code"),
            "observations": len(lines),
        })

    artifacts = [{
        "id": item["id"],
        "original_name": item["original_name"],
        "kind": item["kind"],
        "size_bytes": item["size_bytes"],
        "sha256": item["sha256"],
    } for item in case.get("artifacts", [])]

    return {
        "case_id": case["id"],
        "title": case["title"],
        "target": case["target"],
        "question": case["question"],
        "purpose": case["purpose"],
        "artifacts": artifacts,
        "observed": observed[:MAX_OBSERVATIONS],
        "derived": [],
        "suspected": [],
        "unknown": [
            "Verschluesselung, dynamisch erzeugte Werte und serverseitige Logik "
            "sind ohne Mitschnitt nicht belegbar.",
        ],
        "next_allowed_step": [
            "Passive Mitschnitte des eigenen Geraets oder die eigene App im WLAN testen.",
        ],
        "jobs": jobs,
        "untrusted_target_content": True,
    }
