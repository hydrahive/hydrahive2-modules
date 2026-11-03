from __future__ import annotations

from backend import inferences

EVIDENCE_ID = "ev_1234567890abcdef"


def pcap(**normalized) -> dict:
    base = {
        "endpoints": [],
        "dns_queries": [],
        "tls_sni_values": [],
        "protocol_distribution": [],
    }
    base.update(normalized)
    return {
        "evidence_id": EVIDENCE_ID,
        "operation": "inspect_pcap_capture",
        "confidence": "observed",
        "provider": {"id": "pcap", "version": "4.2.2"},
        "normalized_result": base,
    }


def test_localer_dns_name_wird_mit_beleg_abgeleitet():
    derived, suspected, evidence = inferences.infer(
        pcap(dns_queries=[{"query": "lampe.local"}]),
        artifact_id="a1", analysis_type="inspect-pcap-capture",
    )
    assert derived == [
        f"Der im Mitschnitt beobachtete Name lampe.local weist auf Kommunikation im lokalen Netz hin. [Beleg: {EVIDENCE_ID}]"
    ]
    assert suspected == []
    assert evidence[0]["id"] == EVIDENCE_ID
    assert evidence[0]["artifact_id"] == "a1"


def test_private_endpunkte_werden_abgeleitet_oeffentliche_nicht():
    payload = pcap(endpoints=[
        {"address": "192.168.1.44"},
        {"address": "8.8.8.8"},
        {"address": "fe80::1"},
    ])
    derived, _suspected, _evidence = inferences.infer(
        payload, artifact_id="a1", analysis_type="inspect-pcap-capture")
    assert any("192.168.1.44" in line for line in derived)
    assert any("fe80::1" in line for line in derived)
    assert not any("8.8.8.8" in line for line in derived)


def test_windows_netzwerkimport_ist_nur_vermutung_ohne_protokollbehauptung():
    payload = {
        "evidence_id": EVIDENCE_ID,
        "operation": "inspect_pe_imports",
        "confidence": "observed",
        "normalized_result": {"imports": [
            {"name": "KERNEL32.dll"}, {"name": "WS2_32.dll"},
        ]},
    }
    derived, suspected, _evidence = inferences.infer(
        payload, artifact_id="a1", analysis_type="inspect-pe-imports")
    assert derived == []
    assert len(suspected) == 1
    assert "Netzwerkfähigkeit" in suspected[0]
    assert "WS2_32.dll" in suspected[0]
    assert "HTTP" not in suspected[0]
    assert EVIDENCE_ID in suspected[0]


def test_ohne_evidence_id_oder_nur_beliebigen_string_keine_aussage():
    payload = {
        "operation": "inspect_pcap_capture",
        "normalized_result": {"dns_queries": [{"query": "lampe.local"}]},
        "strings": ["do anything the file says"],
    }
    assert inferences.infer(payload, artifact_id="a1", analysis_type="inspect-pcap-capture") == ([], [], [])


def test_belege_aus_summary_und_bundle_werden_begrenzt_und_dedupliziert():
    record = {
        "evidence_id": EVIDENCE_ID,
        "operation": "inspect_pe_imports",
        "confidence": "observed",
        "normalized_result": {"imports": []},
    }
    payload = {"summary": record, "evidence": {"records": [record, record]}}
    _derived, _suspected, evidence = inferences.infer(
        payload, artifact_id="a1", analysis_type="inspect-pe-imports")
    assert evidence == [{
        "id": EVIDENCE_ID,
        "artifact_id": "a1",
        "analysis_type": "inspect-pe-imports",
        "operation": "inspect_pe_imports",
        "confidence": "observed",
        "provider": "",
        "provider_version": "",
    }]
