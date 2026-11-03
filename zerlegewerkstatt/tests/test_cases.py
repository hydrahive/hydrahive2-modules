from __future__ import annotations

import json
from pathlib import Path

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID


def body(**changes):
    value = {
        "project_id": PROJECT_ID,
        "title": "Wohnzimmer-Lampe",
        "target": "Hersteller-App 2.4",
        "question": "Wie steuert die App die eigene Lampe lokal?",
        "purpose": "interoperability",
        "authorized": True,
        "authorization_note": "Eigene Lampe und öffentlich angebotene App",
    }
    value.update(changes)
    return value


def test_manifest_ist_admin_only_und_service():
    manifest = json.loads((Path(__file__).parents[1] / "manifest.json").read_text())
    assert manifest["id"] == "zerlegewerkstatt"
    assert manifest["has_service"] is True
    assert manifest["default_agent_tools"] is False
    grund = manifest["capabilities"][0]
    assert grund == {
        "id": "module.zerlegewerkstatt",
        "label": "Zerlege-Werkstatt (Apps, Firmware und Mitschnitte)",
        "default": "admin_only",
    }


def test_werkzeug_capability_ist_admin_only_und_nennt_genau_drei_werkzeuge():
    manifest = json.loads((Path(__file__).parents[1] / "manifest.json").read_text())
    capability = next(c for c in manifest["capabilities"]
                       if c["id"] == "zerlegewerkstatt.agents")
    assert capability["default"] == "admin_only"
    assert capability["tools"] == ["reverse_cases", "reverse_inspect", "reverse_report"]


def test_anlage_braucht_login(client):
    assert client.post(f"{MOD_PREFIX}/cases", json=body()).status_code == 401


def test_anlage_braucht_berechtigungsbestaetigung(client, alice):
    response = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body(authorized=False))
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "reverse_authorization_required"


def test_zweck_wird_streng_validiert(client, alice):
    response = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body(purpose="cloud_bypass"))
    assert response.status_code == 422


def test_fremdes_projekt_bleibt_unsichtbar(client, alice, bob):
    denied = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body(project_id=OTHER_PROJECT_ID))
    assert denied.status_code == 404
    assert denied.json()["detail"]["code"] == "reverse_project_not_found"

    created = client.post(f"{MOD_PREFIX}/cases", headers=bob, json=body(project_id=OTHER_PROJECT_ID))
    assert created.status_code == 201
    case_id = created.json()["id"]
    assert client.get(f"{MOD_PREFIX}/cases/{case_id}", headers=alice).status_code == 404


def test_fall_anlegen_listen_und_lesen(client, alice):
    response = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body())
    assert response.status_code == 201
    case = response.json()
    assert len(case["id"]) == 36
    assert case["project_id"] == PROJECT_ID
    assert case["created_by"] == "alice"
    assert case["status"] == "draft"
    assert case["authorized"] is True
    assert case["artifacts"] == []
    assert case["jobs"] == []

    listed = client.get(f"{MOD_PREFIX}/cases", headers=alice, params={"project_id": PROJECT_ID})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [case["id"]]
    assert listed.json()[0]["artifact_count"] == 0
    assert listed.json()[0]["job_count"] == 0

    from backend import store
    store.add_artifact(case["id"], {
        "artifact_id": "artifact-1", "original_name": "router.bin", "kind": "firmware",
        "size": 8, "sha256": "a" * 64, "relative_path": "artifact-1/router.bin",
    })
    store.create_job(case["id"], "artifact-1", "inspect-firmware-regions")
    counted = client.get(f"{MOD_PREFIX}/cases", headers=alice, params={"project_id": PROJECT_ID})
    assert counted.json()[0]["artifact_count"] == 1
    assert counted.json()[0]["job_count"] == 1

    loaded = client.get(f"{MOD_PREFIX}/cases/{case['id']}", headers=alice)
    assert loaded.status_code == 200
    assert loaded.json()["question"] == body()["question"]


def test_unbekannter_fall_hat_stabilen_fehler(client, alice):
    response = client.get(f"{MOD_PREFIX}/cases/00000000-0000-0000-0000-000000000000", headers=alice)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "reverse_case_not_found"


def test_falldaten_liegen_nicht_unter_den_moduldateien():
    """Ein Update überschreibt data_dir/modules. Die Falldaten dürfen dort
    nicht liegen, sonst wären sie nach dem Update weg."""
    from hydrahive.settings import settings

    from backend.files import cases_root

    root = cases_root("fall-0001")
    assert settings.modules_dir not in root.parents
    assert root.parent.parent.name == "zerlegewerkstatt"
    assert root.parent.parent.parent == settings.data_dir
