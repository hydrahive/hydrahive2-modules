from __future__ import annotations

import hashlib
import io
import struct
import zipfile

import pytest

from backend import artifacts, uploads


def pe_bytes() -> bytes:
    value = bytearray(256)
    value[:2] = b"MZ"
    struct.pack_into("<I", value, 0x3C, 0x80)
    value[0x80:0x84] = b"PE\x00\x00"
    return bytes(value)


def apk_bytes(payload: bytes = b"dex\n035\x00") -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"manifest")
        archive.writestr("classes.dex", payload)
    return output.getvalue()


PE_BYTES = pe_bytes()
ZIP_BYTES = b"PK\x03\x04" + b"\x00" * 64
ELF_BYTES = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 64
PCAP_BYTES = b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00" + b"\x00" * 64
PCAPNG_BYTES = b"\x0a\x0d\x0d\x0a" + b"\x00" * 64


class FakeUpload:
    """Minimaler Ersatz für Starlettes UploadFile."""

    def __init__(self, data: bytes, filename: str = "datei.bin"):
        self.filename = filename
        self._data = data
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk = self._data[self._offset:]
            self._offset = len(self._data)
            return chunk
        chunk = self._data[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk


def test_erkennt_pe_zip_apk_elf_und_mitschnitt():
    assert artifacts.detect_kind(PE_BYTES) == "pe"
    assert artifacts.detect_kind(ZIP_BYTES) == "zip"
    assert artifacts.detect_kind(ELF_BYTES) == "elf"
    assert artifacts.detect_kind(PCAP_BYTES) == "pcap"
    assert artifacts.detect_kind(PCAPNG_BYTES) == "pcapng"


def test_unbekannter_typ_wird_abgelehnt():
    assert artifacts.detect_kind(b"nur text ohne signatur") is None
    assert artifacts.detect_kind(b"") is None


def test_groesse_wird_beim_schreiben_gezaehlt():
    assert artifacts.MAX_ARTIFACT_BYTES == 512 * 1024 * 1024
    assert artifacts.MAX_CASE_BYTES == 2 * 1024 * 1024 * 1024
    assert uploads.MAX_FILES_PER_REQUEST == 5


@pytest.mark.asyncio
async def test_upload_berechnet_hash_und_legt_nur_ids_ab(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    data = PE_BYTES + b"rest"
    result = await uploads.store_upload(
        "case-1", FakeUpload(data, "Hersteller Tool.exe"), kind="pe",
    )
    assert result["ok"] is True
    assert result["size"] == len(data)
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["original_name"] == "Hersteller Tool.exe"
    stored = tmp_path / "case-1" / "input" / f"{result['artifact_id']}.pe"
    assert stored.read_bytes() == data
    # Der Originalname steht nur in der Begleitdatei, nie im Pfad.
    assert "Hersteller" not in str(stored)


@pytest.mark.asyncio
async def test_leere_datei_wird_abgelehnt(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    result = await uploads.store_upload("case-1", FakeUpload(b"", "leer.exe"), kind="pe")
    assert result["ok"] is False
    assert result["error"] == "reverse_artifact_empty"
    leftovers = list((tmp_path / "case-1").rglob("*.part")) if (tmp_path / "case-1").exists() else []
    assert leftovers == []


@pytest.mark.asyncio
async def test_zip_ohne_android_struktur_wird_nicht_als_apk_angenommen(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    result = await uploads.store_upload("case-1", FakeUpload(ZIP_BYTES, "fake.apk"))
    assert result["ok"] is False
    assert result["error"] == "reverse_artifact_type_unknown"


@pytest.mark.asyncio
async def test_echte_apk_struktur_wird_angenommen(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    result = await uploads.store_upload("case-1", FakeUpload(apk_bytes(), "app.apk"))
    assert result["ok"] is True
    assert result["kind"] == "apk"


@pytest.mark.asyncio
async def test_zip_bombe_wird_vor_analyse_abgelehnt(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    monkeypatch.setattr(artifacts, "MAX_ARCHIVE_UNCOMPRESSED", 1024)
    result = await uploads.store_upload("case-1", FakeUpload(apk_bytes(b"x" * 4096), "bomb.apk"))
    assert result["ok"] is False
    assert result["error"] == "reverse_artifact_archive_unsafe"


@pytest.mark.asyncio
async def test_mz_ohne_pe_header_wird_abgelehnt(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    result = await uploads.store_upload("case-1", FakeUpload(b"MZ" + b"x" * 100, "fake.exe"))
    assert result["ok"] is False
    assert result["error"] == "reverse_artifact_type_unknown"


@pytest.mark.asyncio
async def test_unbekannter_typ_wird_vor_dem_speichern_abgelehnt(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    result = await uploads.store_upload("case-1", FakeUpload(b"textdatei", "notiz.txt"), kind=None)
    assert result["ok"] is False
    assert result["error"] == "reverse_artifact_type_unknown"


@pytest.mark.asyncio
async def test_groessenueberschreitung_bricht_ab_und_entfernt_teil_datei(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    monkeypatch.setattr(artifacts, "MAX_ARTIFACT_BYTES", 16)
    result = await uploads.store_upload("case-1", FakeUpload(PE_BYTES + b"x" * 64, "gross.exe"), kind="pe")
    assert result["ok"] is False
    assert result["error"] == "reverse_artifact_too_large"
    leftovers = list((tmp_path / "case-1").rglob("*")) if (tmp_path / "case-1").exists() else []
    assert [p for p in leftovers if p.name.endswith(".part")] == []


@pytest.mark.asyncio
async def test_gleicher_hash_im_fall_wird_abgelehnt(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    first = await uploads.store_upload("case-1", FakeUpload(PE_BYTES, "a.exe"), kind="pe")
    assert first["ok"] is True
    second = await uploads.store_upload("case-1", FakeUpload(PE_BYTES, "b.exe"), kind="pe")
    assert second["ok"] is False
    assert second["error"] == "reverse_artifact_duplicate"


@pytest.mark.asyncio
async def test_dateiname_wird_bereinigt(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "cases_root", lambda case_id: tmp_path / case_id)
    result = await uploads.store_upload(
        "case-1", FakeUpload(PE_BYTES, "../../../etc/passwd"), kind="pe",
    )
    assert result["ok"] is True
    assert "/" not in result["original_name"]
    assert ".." not in result["original_name"]


def test_fallgrenze_wird_geprueft(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "MAX_CASE_BYTES", 100)
    case = tmp_path / "case-1" / "input"
    case.mkdir(parents=True)
    (case / "alt.pe").write_bytes(b"x" * 80)
    assert artifacts.case_size_exceeded(case, incoming=40) is True
    assert artifacts.case_size_exceeded(case, incoming=10) is False


def test_web_upload_speichert_artefakt_in_fall(client, alice):
    from conftest import MOD_PREFIX
    from test_cases import body

    created = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body()).json()
    response = client.post(
        f"{MOD_PREFIX}/cases/{created['id']}/artifacts",
        headers=alice,
        files=[("files", ("tool.exe", PE_BYTES, "application/octet-stream"))],
    )
    assert response.status_code == 201
    artifact = response.json()["files"][0]
    assert artifact["ok"] is True
    loaded = client.get(f"{MOD_PREFIX}/cases/{created['id']}", headers=alice).json()
    assert loaded["artifacts"][0]["sha256"] == hashlib.sha256(PE_BYTES).hexdigest()
    assert loaded["artifacts"][0]["relative_path"].startswith("input/")


def test_web_upload_prueft_fallzugriff(client, alice, bob):
    from conftest import MOD_PREFIX, OTHER_PROJECT_ID
    from test_cases import body

    created = client.post(
        f"{MOD_PREFIX}/cases", headers=bob, json=body(project_id=OTHER_PROJECT_ID),
    ).json()
    response = client.post(
        f"{MOD_PREFIX}/cases/{created['id']}/artifacts",
        headers=alice,
        files=[("files", ("tool.exe", PE_BYTES, "application/octet-stream"))],
    )
    assert response.status_code == 404


def test_web_upload_prueft_gemeldete_groesse_vor_dem_schreiben(client, alice, monkeypatch):
    from conftest import MOD_PREFIX
    from test_cases import body

    monkeypatch.setattr(artifacts, "MAX_ARTIFACT_BYTES", 8)
    created = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body()).json()
    response = client.post(
        f"{MOD_PREFIX}/cases/{created['id']}/artifacts", headers=alice,
        files=[("files", ("tool.exe", PE_BYTES, "application/octet-stream"))],
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "reverse_artifact_too_large"


def test_web_upload_begrenzt_dateianzahl(client, alice):
    from conftest import MOD_PREFIX
    from test_cases import body

    created = client.post(f"{MOD_PREFIX}/cases", headers=alice, json=body()).json()
    files = [("files", (f"tool-{i}.exe", PE_BYTES + bytes([i]), "application/octet-stream")) for i in range(6)]
    response = client.post(f"{MOD_PREFIX}/cases/{created['id']}/artifacts", headers=alice, files=files)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "reverse_artifact_too_many"


def test_stream_wird_nicht_voll_gelesen():
    """Der Upload darf die ganze Datei nicht in den Speicher holen."""
    stream = io.BytesIO(b"x" * 100)
    chunks = list(artifacts.iter_chunks(stream, size=8))
    assert len(chunks) == 13
    assert b"".join(chunks) == b"x" * 100
