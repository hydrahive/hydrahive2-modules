"""Konservative, beleggebundene Ableitungen aus normalisierten REA-Daten.

Keine freie Textdeutung: Nur explizite strukturierte Felder und eine kleine
Positivliste erzeugen Aussagen. Ohne gueltige Evidence-ID gibt es weder
Ableitung noch Vermutung.
"""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterator

MAX_EVIDENCE = 100
MAX_STATEMENTS = 50
EVIDENCE_RE = re.compile(r"^ev_[0-9a-f]{16,128}$")
LOCAL_SUFFIXES = (".local", ".lan", ".home", ".home.arpa", ".internal")
LOCAL_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8",
    "169.254.0.0/16", "fc00::/7", "fe80::/10", "::1/128",
))
NETWORK_LIBRARIES = frozenset({
    "ws2_32.dll", "winhttp.dll", "wininet.dll", "urlmon.dll", "dnsapi.dll",
    "iphlpapi.dll", "libcurl.dll", "libssl.dll", "libcrypto.dll",
})


def _safe_text(value: object, *, limit: int = 253) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(char for char in value.strip() if char.isprintable())[:limit]


def _sources(payload: dict) -> Iterator[dict]:
    if isinstance(payload, dict):
        yield payload
    summary = payload.get("summary")
    if isinstance(summary, dict):
        yield summary
    bundle = payload.get("evidence")
    if isinstance(bundle, dict):
        for record in bundle.get("records", [])[:MAX_EVIDENCE]:
            if isinstance(record, dict):
                yield record


def _reference(source: dict, *, artifact_id: str, analysis_type: str) -> dict | None:
    evidence_id = source.get("evidence_id")
    if not isinstance(evidence_id, str) or not EVIDENCE_RE.fullmatch(evidence_id):
        return None
    provider = source.get("provider")
    provider_id = provider.get("id", "") if isinstance(provider, dict) else ""
    provider_version = provider.get("version", "") if isinstance(provider, dict) else ""
    return {
        "id": evidence_id,
        "artifact_id": artifact_id,
        "analysis_type": analysis_type,
        "operation": _safe_text(source.get("operation"), limit=100),
        "confidence": _safe_text(source.get("confidence"), limit=30),
        "provider": _safe_text(provider_id, limit=100),
        "provider_version": _safe_text(provider_version, limit=160),
    }


def _is_local_address(value: object) -> bool:
    text = _safe_text(value, limit=64)
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    return any(address in network for network in LOCAL_NETWORKS)


def _cite(text: str, evidence_id: str) -> str:
    return f"{text} [Beleg: {evidence_id}]"


def _pcap_statements(normalized: dict, evidence_id: str) -> list[str]:
    lines: list[str] = []
    for item in normalized.get("dns_queries", [])[:50]:
        query = _safe_text(item.get("query") if isinstance(item, dict) else None)
        if query.casefold().endswith(LOCAL_SUFFIXES):
            lines.append(_cite(
                f"Der im Mitschnitt beobachtete Name {query} weist auf Kommunikation im lokalen Netz hin.",
                evidence_id,
            ))
    for item in normalized.get("endpoints", [])[:100]:
        address = _safe_text(item.get("address") if isinstance(item, dict) else None, limit=64)
        if address and _is_local_address(address):
            lines.append(_cite(
                f"Der Mitschnitt belegt Kommunikation mit der lokalen Adresse {address}.", evidence_id))
    return lines


def _import_statements(normalized: dict, evidence_id: str) -> list[str]:
    names = {
        _safe_text(item.get("name") if isinstance(item, dict) else None, limit=120)
        for item in normalized.get("imports", [])[:512]
    }
    network = sorted(name for name in names if name.casefold() in NETWORK_LIBRARIES)
    if not network:
        return []
    libraries = ", ".join(network[:8])
    return [_cite(
        f"Die importierten Bibliotheken {libraries} sprechen für Netzwerkfähigkeit; Nutzung und Protokoll sind nicht belegt.",
        evidence_id,
    )]


def infer(payload: dict, *, artifact_id: str, analysis_type: str) -> tuple[list[str], list[str], list[dict]]:
    """Ableitungen, Vermutungen und Belegverzeichnis fuer ein Job-Ergebnis."""
    derived: list[str] = []
    suspected: list[str] = []
    evidence: list[dict] = []
    seen_ids: set[str] = set()
    for source in _sources(payload):
        reference = _reference(source, artifact_id=artifact_id, analysis_type=analysis_type)
        if reference is None:
            continue
        evidence_id = reference["id"]
        if evidence_id not in seen_ids and len(evidence) < MAX_EVIDENCE:
            seen_ids.add(evidence_id)
            evidence.append(reference)
        normalized = source.get("normalized_result")
        if not isinstance(normalized, dict):
            continue
        operation = source.get("operation")
        if operation == "inspect_pcap_capture":
            derived.extend(_pcap_statements(normalized, evidence_id))
        elif operation == "inspect_pe_imports":
            suspected.extend(_import_statements(normalized, evidence_id))
    return (
        list(dict.fromkeys(derived))[:MAX_STATEMENTS],
        list(dict.fromkeys(suspected))[:MAX_STATEMENTS],
        evidence,
    )
