"""Kleine normalisierte Berichte aus den Analyseergebnissen.

Der Bericht trennt, wie SPEC §11 es verlangt:
Beobachtet, Abgeleitet, Vermutet, Unbekannt und die naechste erlaubte
Pruefung. Text aus dem Ziel gilt als nicht vertrauenswuerdig und wird
gekennzeichnet.

Die Aufbereitung der REA-Ergebnisse steht in `evidence.py`.
"""
from __future__ import annotations

import json

from . import evidence, inferences
from .files import cases_root

MAX_OBSERVATIONS = evidence.MAX_OBSERVATIONS
MAX_TEXT = evidence.MAX_TEXT
SKIP_KEYS = evidence.SKIP_KEYS


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
    return evidence.collect(payload)


def _from_normalized(payload: dict) -> list[str]:
    """Aussagen aus dem normalisierten REA-Ergebnis uebernehmen."""
    return evidence.from_normalized(payload)


def _bundle_facts(payload: dict) -> list[str]:
    """Belegbare Fakten aus dem Evidence-Bundle ziehen."""
    return evidence.bundle_facts(payload)


def _limitations(payload: dict) -> list[str]:
    """Einschraenkungen der Analyse nennen."""
    return evidence.limitations(payload)


def build_report(case: dict) -> dict:
    """Bericht zu einem Fall aus den Ergebnissen seiner Jobs bauen."""
    observed: list[str] = []
    derived: list[str] = []
    suspected: list[str] = []
    references: list[dict] = []
    seen_evidence: set[str] = set()
    jobs = []
    for job in case.get("jobs", []):
        payload = _load_result(case["id"], job.get("result_path"))
        lines = _collect(payload)
        lines.extend(_bundle_facts(payload))
        lines.extend(_limitations(payload))
        observed.extend(lines)
        inferred, hypotheses, job_references = inferences.infer(
            payload,
            artifact_id=job["artifact_id"],
            analysis_type=job["analysis_type"],
        )
        derived.extend(inferred)
        suspected.extend(hypotheses)
        for reference in job_references:
            evidence_id = reference["id"]
            if evidence_id not in seen_evidence and len(references) < inferences.MAX_EVIDENCE:
                seen_evidence.add(evidence_id)
                references.append(reference)
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
        "observed": list(dict.fromkeys(observed))[:MAX_OBSERVATIONS],
        "derived": list(dict.fromkeys(derived))[:inferences.MAX_STATEMENTS],
        "suspected": list(dict.fromkeys(suspected))[:inferences.MAX_STATEMENTS],
        "evidence": references,
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
