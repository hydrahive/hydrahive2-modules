"""Bericht: Beobachtungen trennen, Belege nennen, nichts behaupten."""
from __future__ import annotations

import json

from backend import reports


def bundle() -> dict:
    """Evidence-Bundle in der Form, die REA liefert."""
    return {
        "artifacts": [{
            "format": "pe",
            "architecture": "x86_64",
            "digest": {"sha256": "a7370caccfe212af57f10f0b87e366a8977139dc08146106d2b80d1433b85b38"},
        }],
        "records": [{
            "confidence": "observed",
            "normalized_result": {
                "assembly": "System.Private.CoreLib",
                "target_framework": "net8.0",
                "permissions": ["INTERNET"],
            },
        }],
    }


def test_normalisiertes_ergebnis_wird_uebernommen():
    payload = {"normalized_result": {"package_name": "de.wled.app", "version_name": "2.4.0"}}
    lines = reports._collect(payload)
    assert "package_name: de.wled.app" in lines
    assert "version_name: 2.4.0" in lines


def test_verschachtelte_werte_werden_ausgepackt():
    """REA liefert tiefe Strukturen. Der Bericht muss sie lesbar machen."""
    payload = {"normalized_result": {
        "pe": {"architecture": "x86_64", "section_count": 7},
        "classification": {"status": "not-managed", "runtime_family": "unknown"},
        "target_frameworks": ["net8.0", "netstandard2.0"],
        "byte_length": 990000,
    }}
    lines = reports._collect(payload)
    assert "architecture: x86_64" in lines
    assert "section_count: 7" in lines
    assert "status: not-managed" in lines
    assert "target_frameworks: net8.0, netstandard2.0" in lines
    assert "byte_length: 990000" in lines


def test_leere_und_falsche_werte_werden_ausgelassen():
    payload = {"normalized_result": {
        "cli": None, "analysis_profile": None, "enabled": False, "leer": "",
    }}
    assert reports._collect(payload) == []


def test_containerpfade_kommen_nicht_in_den_bericht():
    """Pfade im Container verraten nichts ueber das Ziel."""
    payload = {"normalized_result": {
        "artifact": {"path": "/work/abc123/artifact.pe"},
        "local_path": "/work/abc123/artifact.pe",
        "format": "pe",
    }}
    lines = reports._collect(payload)
    assert "format: pe" in lines
    assert not any("/work/" in line for line in lines)


def test_einschraenkung_wird_nicht_doppelt_genannt():
    """Derselbe Satz darf im Bericht nur einmal stehen."""
    payload = {
        "normalized_result": {"detail": "The PE has no CLI data directory."},
        "limitations": "The PE has no CLI data directory.",
    }
    beobachtet = reports._collect(payload) + reports._limitations(payload)
    assert beobachtet.count("The PE has no CLI data directory.") == 0
    assert len([l for l in beobachtet if "CLI data directory" in l]) == 1


def test_einschraenkungen_gehoeren_zum_bericht():
    payload = {"limitations": "The PE has no CLI data directory."}
    assert reports._limitations(payload) == ["The PE has no CLI data directory."]


def test_bericht_nennt_die_einschraenkungen_der_analyse():
    case = {
        "id": "fall-1",
        "title": "Lampe",
        "target": "",
        "question": "Frage",
        "purpose": "interoperability",
        "artifacts": [],
        "jobs": [],
    }
    report = reports.build_report(case)
    assert report["observed"] == []
    assert report["derived"] == []
    assert report["suspected"] == []
    assert report["unknown"], "Unbekanntes muss benannt werden"
    assert report["next_allowed_step"], "Es muss einen erlaubten naechsten Schritt geben"
    assert report["untrusted_target_content"] is True


def test_belege_aus_dem_bundle_werden_genannt():
    lines = reports._bundle_facts({"evidence": bundle()})
    assert any("SHA-256 a7370caccfe" in line for line in lines)
    assert any("Format pe" in line for line in lines)
    assert any("assembly" in line for line in lines)


def test_ohne_bundle_gibt_es_keine_erfundenen_belege():
    assert reports._bundle_facts({"normalized_result": {}}) == []
    assert reports._bundle_facts({}) == []


def test_bericht_trennt_die_abschnitte():
    case = {
        "id": "fall-1",
        "title": "Lampe",
        "target": "App 2.4",
        "question": "Wie steuert die App die Lampe?",
        "purpose": "interoperability",
        "artifacts": [],
        "jobs": [],
    }
    report = reports.build_report(case)
    assert report["observed"] == []
    assert report["derived"] == []
    assert report["suspected"] == []
    assert report["unknown"], "Unbekanntes muss benannt werden"
    assert report["next_allowed_step"], "Es muss einen erlaubten naechsten Schritt geben"
    assert report["untrusted_target_content"] is True


def test_bericht_ist_hart_begrenzt(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "cases_root", lambda case_id: tmp_path)
    case = {
        "id": "fall-1",
        "title": "Lampe",
        "target": "",
        "question": "Frage",
        "purpose": "interoperability",
        "artifacts": [],
        "jobs": [{"id": "j1", "artifact_id": "a1", "analysis_type": "inspect-artifact",
                  "status": "done", "progress": 100, "error_code": None,
                  "result_path": "results/j1.json"}],
    }
    assert len(reports.build_report(case)["observed"]) <= reports.MAX_OBSERVATIONS


def test_bericht_verknuepft_ableitung_mit_job_artefakt_und_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "cases_root", lambda case_id: tmp_path)
    (tmp_path / "results").mkdir()
    evidence_id = "ev_1234567890abcdef"
    payload = {
        "evidence_id": evidence_id,
        "operation": "inspect_pcap_capture",
        "confidence": "observed",
        "provider": {"id": "pcap", "version": "4.2.2"},
        "normalized_result": {
            "dns_queries": [{"query": "lampe.local"}],
            "endpoints": [],
        },
    }
    (tmp_path / "results/j1.json").write_text(json.dumps(payload))
    case = {
        "id": "fall-1", "title": "Lampe", "target": "", "question": "Frage",
        "purpose": "interoperability", "artifacts": [],
        "jobs": [{
            "id": "j1", "artifact_id": "a1", "analysis_type": "inspect-pcap-capture",
            "status": "done", "progress": 100, "error_code": None,
            "result_path": "results/j1.json",
        }],
    }
    report = reports.build_report(case)
    assert len(report["derived"]) == 1
    assert "lampe.local" in report["derived"][0]
    assert evidence_id in report["derived"][0]
    assert report["suspected"] == []
    assert report["evidence"] == [{
        "id": evidence_id,
        "artifact_id": "a1",
        "analysis_type": "inspect-pcap-capture",
        "operation": "inspect_pcap_capture",
        "confidence": "observed",
        "provider": "pcap",
        "provider_version": "4.2.2",
    }]


def test_zieltext_ist_als_nicht_vertrauenswuerdig_markiert():
    case = {"id": "f", "title": "t", "target": "", "question": "q",
            "purpose": "interoperability", "artifacts": [], "jobs": []}
    assert reports.build_report(case)["untrusted_target_content"] is True


def test_ergebnisdatei_ausserhalb_des_falls_wird_ignoriert(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "cases_root", lambda case_id: tmp_path)
    assert reports._load_result("fall-1", "../../etc/passwd") == {}
    assert reports._load_result("fall-1", None) == {}
