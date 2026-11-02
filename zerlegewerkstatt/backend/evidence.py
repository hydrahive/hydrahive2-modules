"""Aufbereitung des REA-Ergebnisses fuer den Bericht.

REA liefert tief verschachtelte Werte. Dieser Teil macht daraus kurze,
lesbare Zeilen. Getrennt vom Bericht, damit die Aufbereitung fuer sich
getestet werden kann.
"""
from __future__ import annotations

MAX_TEXT = 400
MAX_OBSERVATIONS = 200

#: Containerpfade und Werkzeug-Interna gehoeren nicht in den Bericht.
#: Sie verraten nichts ueber das Ziel und machen den Bericht unlesbar.
SKIP_KEYS = frozenset({
    "path",
    "local_path",
    "caller_input_path",
    "input_path",
    "parent_evidence_id",
    "evidence_id",
})


def flatten(key: str, value, depth: int = 0) -> list[str]:
    """Einen Wert aus dem REA-Ergebnis in lesbare Zeilen ueberfuehren."""
    if depth > 3 or key in SKIP_KEYS:
        return []
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, str):
        text = value.strip()
        return [f"{key}: {text}"[:MAX_TEXT]] if text else []
    if isinstance(value, (int, float)):
        return [f"{key}: {value}"]
    if isinstance(value, list):
        strings = [item for item in value if isinstance(item, str)]
        if strings:
            return [f"{key}: {', '.join(strings[:8])}"[:MAX_TEXT]]
        lines: list[str] = []
        for item in value[:20]:
            if isinstance(item, dict):
                for sub_key, sub_value in list(item.items())[:6]:
                    lines.extend(flatten(sub_key, sub_value, depth + 1))
        return lines[:MAX_OBSERVATIONS]
    if isinstance(value, dict):
        lines: list[str] = []
        for sub_key, sub_value in list(value.items())[:40]:
            lines.extend(flatten(sub_key, sub_value, depth + 1))
        return lines[:MAX_OBSERVATIONS]
    return []


def from_normalized(payload: dict) -> list[str]:
    """Aussagen aus dem normalisierten REA-Ergebnis uebernehmen."""
    normalized = payload.get("normalized_result")
    if not isinstance(normalized, dict):
        return []
    lines: list[str] = []
    for key, value in normalized.items():
        lines.extend(flatten(key, value))
    return lines


def collect(payload: dict) -> list[str]:
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
    lines.extend(from_normalized(payload))
    return lines[:MAX_OBSERVATIONS]


def bundle_facts(payload: dict) -> list[str]:
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
                lines.extend(flatten(key, value))
    for artifact in bundle.get("artifacts", [])[:10]:
        if isinstance(artifact, dict):
            digest = artifact.get("digest", {})
            sha = digest.get("sha256") if isinstance(digest, dict) else None
            if sha:
                lines.append(f"Belegt: SHA-256 {sha}"[:MAX_TEXT])
            if artifact.get("format"):
                lines.append(f"Belegt: Format {artifact['format']}"[:MAX_TEXT])
    return lines[:MAX_OBSERVATIONS]


def _unique(lines: list[str], seen: set[str]) -> list[str]:
    """Zeilen ohne Wiederholung. `seen` waechst mit."""
    fresh: list[str] = []
    for line in lines:
        body = line.split(": ", 1)[1].strip() if ": " in line else line.strip()
        if body in seen:
            continue
        seen.add(body)
        fresh.append(line)
    return fresh


def limitations(payload: dict) -> list[str]:
    """Einschraenkungen der Analyse nennen. Sie gehoeren zum Bericht.

    Werte, die schon mit gleichem Wortlaut in den normalisierten Daten stehen,
    werden nicht wiederholt.
    """
    seen: set[str] = set()
    for line in from_normalized(payload):
        body = line.split(": ", 1)[1].strip() if ": " in line else line.strip()
        seen.add(body)
    lines: list[str] = []
    for key in ("limitations", "relationship_coverage"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            text = value.strip()[:MAX_TEXT]
            if text not in seen:
                lines.append(text)
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                lines.extend(_unique(flatten(sub_key, sub_value), seen))
        elif isinstance(value, list):
            for item in value[:20]:
                if isinstance(item, str) and item.strip():
                    text = item.strip()[:MAX_TEXT]
                    if text not in seen:
                        lines.append(text)
                elif isinstance(item, dict):
                    for sub_key, sub_value in item.items():
                        lines.extend(_unique(flatten(sub_key, sub_value), seen))
    return lines[:MAX_OBSERVATIONS]
