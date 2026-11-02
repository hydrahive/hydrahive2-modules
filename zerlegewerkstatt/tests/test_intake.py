"""Samba-Eingang: nur stabile reguläre Dateien werden übernommen."""
from __future__ import annotations

from pathlib import Path

from conftest import MOD_PREFIX, PROJECT_ID

PE_HEAD = b"MZ" + b"\x90\x00" * 2 + b"\x00" * 60


def pe_bytes(payload: bytes = b"hello") -> bytes:
    """Minimal gültige PE-Datei mit echtem PE-Signatur-Offset."""
    stub = bytearray(b"\x00" * 0x80)
    stub[0:2] = b"MZ"
    offset = 0x40
    stub[0x3C:0x40] = offset.to_bytes(4, "little")
    stub[offset:offset + 4] = b"PE\x00\x00"
    return bytes(stub) + payload


def create_case(client, headers, project_id: str = PROJECT_ID) -> str:
    response = client.post(f"{MOD_PREFIX}/cases", headers=headers, json={
        "project_id": project_id,
        "title": "Samba-Fall",
        "target": "Testgeraet",
        "question": "Wie kommuniziert das eigene Geraet lokal?",
        "purpose": "interoperability",
        "authorized": True,
        "authorization_note": "Eigenes Geraet",
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def intake_dir(project_id: str, case_id: str) -> Path:
    from hydrahive.projects._paths import workspace_path

    return workspace_path(project_id) / "zerlegewerkstatt" / "eingang" / case_id


def test_intake_nimmt_regulaere_datei_auf(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "geraet.exe").write_bytes(pe_bytes())

    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    assert response.status_code == 200
    body = response.json()
    assert body["taken"] == 1
    assert body["files"][0]["kind"] == "pe"
    assert body["files"][0]["original_name"] == "geraet.exe"


def test_intake_original_bleibt_unveraendert(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    original = pe_bytes(b"unveraendert")
    (folder / "geraet.exe").write_bytes(original)
    before = (folder / "geraet.exe").stat()

    client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)

    after = (folder / "geraet.exe").stat()
    assert (folder / "geraet.exe").read_bytes() == original
    assert after.st_size == before.st_size
    assert after.st_mtime_ns == before.st_mtime_ns


def test_intake_ueberspringt_symlink(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "echt.exe"
    target.write_bytes(pe_bytes())
    (folder / "verweis.exe").symlink_to(target)

    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    body = response.json()
    codes = {item["original_name"]: item.get("error") for item in body["files"]}
    assert codes["verweis.exe"] == "reverse_intake_not_regular"
    assert body["taken"] == 1


def test_intake_ignoriert_unterordner(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    (folder / "unter").mkdir(parents=True, exist_ok=True)
    (folder / "unter" / "geraet.exe").write_bytes(pe_bytes())

    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    assert response.json()["scanned"] == 0


def test_intake_weist_unbekannten_typ_ab(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "notiz.txt").write_bytes("ganz gewöhnlicher Text".encode())

    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    assert response.json()["files"][0]["error"] == "reverse_artifact_type_unknown"


def test_intake_weist_leere_datei_ab(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "leer.exe").write_bytes(b"")

    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    assert response.json()["files"][0]["error"] == "reverse_artifact_empty"


def test_intake_weist_dubletten_ab(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    payload = pe_bytes(b"gleich")
    (folder / "a.exe").write_bytes(payload)
    (folder / "b.exe").write_bytes(payload)

    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    body = response.json()
    assert body["taken"] == 1
    assert any(item.get("error") == "reverse_artifact_duplicate"
               for item in body["files"])


def test_intake_braucht_projektzugriff(client, alice, bob):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "geraet.exe").write_bytes(pe_bytes())

    denied = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=bob)
    assert denied.status_code == 404
    assert denied.json()["detail"]["code"] == "reverse_project_not_found"


def test_intake_laeuft_in_denselben_validierten_pfad_wie_web(client, alice):
    """Ein per Samba aufgenommenes Artefakt ist so abgelegt wie ein Web-Upload."""
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "geraet.exe").write_bytes(pe_bytes())

    client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    case = client.get(f"{MOD_PREFIX}/cases/{case_id}", headers=alice).json()
    assert len(case["artifacts"]) == 1
    artifact = case["artifacts"][0]
    assert artifact["kind"] == "pe"
    assert artifact["relative_path"].startswith("input/")
    assert len(artifact["sha256"]) == 64


def test_intake_info_zeigt_pfad_und_dateien(client, alice):
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "geraet.exe").write_bytes(pe_bytes())

    response = client.get(f"{MOD_PREFIX}/cases/{case_id}/intake", headers=alice)
    assert response.status_code == 200
    body = response.json()
    assert body["path"] == f"zerlegewerkstatt/eingang/{case_id}"
    assert body["exists"] is True
    assert body["files"] == ["geraet.exe"]


def test_intake_ohne_ordner_liefert_leeres_ergebnis(client, alice):
    case_id = create_case(client, alice)
    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    assert response.status_code == 200
    assert response.json() == {"scanned": 0, "taken": 0, "files": []}


def test_intake_verwirft_datei_die_sich_waehrend_der_aufnahme_aendert(client, alice, monkeypatch):
    """Ändert sich die Datei zwischen Vor- und Nachprüfung, wird sie verworfen."""
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "geraet.exe"
    target.write_bytes(pe_bytes())

    from backend import intake

    original_copy = intake._copy_out

    def changing_copy(source, destination):
        size, digest = original_copy(source, destination)
        # Datei nach der Kopie verändern: Größe und Zeitstempel weichen ab.
        source.write_bytes(pe_bytes(b"veraendert"))
        return size, digest

    monkeypatch.setattr(intake, "_copy_out", changing_copy)
    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    body = response.json()
    assert body["taken"] == 0
    assert body["files"][0]["error"] == "reverse_intake_changed"

    case = client.get(f"{MOD_PREFIX}/cases/{case_id}", headers=alice).json()
    assert case["artifacts"] == []


def test_intake_braucht_fallzugriff(client, alice):
    """Ein unbekannter Fall liefert den stabilen Fallfehler."""
    response = client.post(
        f"{MOD_PREFIX}/cases/00000000-0000-0000-0000-000000000000/intake/scan",
        headers=alice,
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "reverse_case_not_found"


def test_intake_braucht_login(client, alice):
    """Ohne Anmeldung wird der Eingang nicht gelesen."""
    case_id = create_case(client, alice)
    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan")
    assert response.status_code == 401


def test_intake_ignoriert_punktdateien(client, alice):
    """Versteckte Dateien wie `.DS_Store` werden nicht aufgenommen."""
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ".versteckt.exe").write_bytes(pe_bytes())

    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    assert response.json()["scanned"] == 0


def test_intake_oeffnet_keinen_symlink_der_zwischenzeitlich_entsteht(client, alice, monkeypatch):
    """Wird die Datei nach der Vorprüfung zum Symlink, wird nichts gelesen."""
    case_id = create_case(client, alice)
    folder = intake_dir(PROJECT_ID, case_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "geraet.exe"
    target.write_bytes(pe_bytes())
    fremd = folder / "fremd.txt"
    fremd.write_bytes("nicht lesen".encode())

    from backend import intake

    original_stat = intake._stable_stat

    def swapping_stat(path):
        info = original_stat(path)
        if path.name == "geraet.exe":
            # Direkt nach der Vorprüfung durch einen Symlink ersetzen.
            path.unlink()
            path.symlink_to(fremd)
        return info

    monkeypatch.setattr(intake, "_stable_stat", swapping_stat)
    response = client.post(f"{MOD_PREFIX}/cases/{case_id}/intake/scan", headers=alice)
    body = response.json()
    assert body["taken"] == 0
    case = client.get(f"{MOD_PREFIX}/cases/{case_id}", headers=alice).json()
    assert case["artifacts"] == []
