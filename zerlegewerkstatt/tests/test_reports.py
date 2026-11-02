"""Bericht: Beobachtungen trennen, Belege nennen, nichts behaupten."""
from __future__ import annotations

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


def test_zieltext_ist_als_nicht_vertrauenswuerdig_markiert():
    case = {"id": "f", "title": "t", "target": "", "question": "q",
            "purpose": "interoperability", "artifacts": [], "jobs": []}
    assert reports.build_report(case)["untrusted_target_content"] is True


def test_ergebnisdatei_ausserhalb_des_falls_wird_ignoriert(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "cases_root", lambda case_id: tmp_path)
    assert reports._load_result("fall-1", "../../etc/passwd") == {}
    assert reports._load_result("fall-1", None) == {}
