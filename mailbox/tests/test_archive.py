"""M1 Schritt 5: Archiv (Spec §5a) – Pfad lesbar, Name nur vom Server, gleiche Mail eine Datei, umziehen statt löschen."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from conftest import MODULE_DIR, eml

ADDR = "till@example.net"


def _store(archive, raw=None, folder="INBOX", date="2026-10-20T07:15:00Z", subject="Termin morgen"):
    from backend import archive as ar
    raw = raw or eml("plain")
    return ar.store(ADDR, folder, raw, date=date, subject=subject)


def test_pfad_nach_spec(archive):
    rel = _store(archive)
    sha = hashlib.sha256(eml("plain")).hexdigest()
    assert rel == f"till@example.net/INBOX/2026/2026-10-20_0715_Termin_morgen_{sha[:8]}.eml"
    assert (archive / rel).read_bytes() == eml("plain")


@pytest.mark.parametrize("subject", ["../../etc/passwd", "a/b\\c", "x\x00y", "🙂 Grüße 🙂", "." * 50, "", "CON", "x" * 300,
                                     "-rf --help", "\u202eRTL"])
def test_name_nur_aus_erlaubten_zeichen(archive, subject):
    rel = _store(archive, subject=subject)
    name = Path(rel).name
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{4}_[A-Za-z0-9äöüÄÖÜß_-]{0,60}_[0-9a-f]{8}\.eml", name), name
    assert (archive / rel).resolve().is_relative_to(archive.resolve())


@pytest.mark.parametrize("folder, want", [("INBOX", "INBOX"), ("Gesendete Objekte", "Gesendete_Objekte"),
                                          ("Archiv/2019/Steuer", "Archiv/2019/Steuer"), ("../..", "_/_"),
                                          ("[Gmail]/Alle Nachrichten", "_Gmail_/Alle_Nachrichten"), ("", "_")])
def test_ordner_wird_sicherer_pfad(archive, folder, want):
    from backend import archive as ar
    assert ar.folder_dir(folder) == want
    rel = _store(archive, folder=folder)
    assert (archive / rel).resolve().is_relative_to(archive.resolve())


def test_konto_adresse_als_ordner_sicher(archive):
    from backend import archive as ar
    with pytest.raises(ValueError):
        ar.store("../x@y.de", "INBOX", b"x", date="", subject="")
    with pytest.raises(ValueError):
        ar.store("a/b@y.de", "INBOX", b"x", date="", subject="")


def test_ohne_datum_ordner_unbekannt(archive):
    rel = _store(archive, date="")
    assert "/0000/0000-00-00_0000_" in rel


def test_gleiche_mail_eine_datei(archive):
    a = _store(archive)
    b = _store(archive)
    assert a == b and len(list(archive.rglob("*.eml"))) == 1


def test_umziehen_statt_loeschen(archive):
    from backend import archive as ar
    rel = _store(archive)
    new = ar.move(rel, ADDR, "Archiv/2026")
    assert new.startswith("till@example.net/Archiv/2026/2026/") and (archive / new).read_bytes() == eml("plain")
    assert not (archive / rel).exists()
    assert ar.move(new, ADDR, "Archiv/2026") == new, "gleicher Ordner: nichts tun"


def test_umzug_ueberschreibt_nie(archive):
    """Liegt am Ziel schon eine (andere) Datei gleichen Namens, bleibt sie – die Quelle auch."""
    from backend import archive as ar
    rel = _store(archive)
    target = archive / ar.target(ADDR, "Ziel", Path(rel).name)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"anders")
    with pytest.raises(ar.ArchiveError):
        ar.move(rel, ADDR, "Ziel")
    assert target.read_bytes() == b"anders" and (archive / rel).exists()


def test_manifest_mit_hash(archive):
    from backend import archive as ar
    rel = _store(archive)
    ar.manifest_add(ADDR, rel, "<plain-1@example.org>", "INBOX", "ok")
    line = (archive / ADDR / "MANIFEST.tsv").read_text().splitlines()[-1].split("\t")
    assert line[1] == rel and line[2] == hashlib.sha256(eml("plain")).hexdigest()
    assert line[3:] == ["<plain-1@example.org>", "INBOX", "ok"]


def test_manifest_tabs_und_umbrueche_entschaerft(archive):
    from backend import archive as ar
    rel = _store(archive)
    ar.manifest_add(ADDR, rel, "<a\tb\nc>", "IN\tBOX", "ok")
    lines = (archive / ADDR / "MANIFEST.tsv").read_text().splitlines()
    assert len(lines[-1].split("\t")) == 6 and len([x for x in lines if x and not x.startswith("#")]) == 1


def test_lesen_nur_im_archiv(archive):
    from backend import archive as ar
    rel = _store(archive)
    assert ar.read(rel) == eml("plain")
    for bad in ("../../etc/passwd", "/etc/passwd", "till@example.net/../../x.eml"):
        with pytest.raises(ar.ArchiveError):
            ar.read(bad)


def test_datei_wird_atomar_geschrieben(archive, monkeypatch):
    """Absturz beim Schreiben: keine halbe .eml am Zielort."""
    import os

    from backend import archive as ar

    def boom(src, dst):
        raise OSError("Platte voll")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        _store(archive)
    assert list(archive.rglob("*.eml")) == []
    assert ar  # noqa: B018


def test_kein_loeschpfad_im_modul():
    """Spec §5: Das Archiv löscht nie. Im Backend gibt es keinen Aufruf, der Dateien entfernt (außer der eigenen tmp-Datei)."""
    allowed = {("archive.py", "tmp.unlink(missing_ok=True)"),  # eigene halbe tmp-Datei
               ("archive.py", "src.unlink()")}                   # alter Name nach Hardlink (samefile geprüft)
    for f in sorted((MODULE_DIR / "backend").glob("*.py")):
        for no, line in enumerate(f.read_text().splitlines(), 1):
            code = line.split("#", 1)[0]
            for word in ("unlink(", "rmtree(", "os.remove(", ".rmdir(", "shutil.move("):
                if word in code and (f.name, code.strip()) not in allowed:
                    pytest.fail(f"{f.name}:{no} löscht: {line.strip()}")


def test_namenskollision_ueberschreibt_nicht(archive):
    """Zwei verschiedene Mails mit gleichem Namen (gleiches Datum/Betreff, Hash-Präfix gleich): die erste bleibt unangetastet."""
    from backend import archive as ar
    rel = _store(archive)
    (archive / rel).write_bytes(b"Fremde Daten unter diesem Namen")
    with pytest.raises(ar.ArchiveError):
        _store(archive)
    assert (archive / rel).read_bytes() == b"Fremde Daten unter diesem Namen"


def test_lesen_von_ordner_oder_fehlender_datei(archive):
    from backend import archive as ar
    _store(archive)
    for rel in ("till@example.net/INBOX", "till@example.net/INBOX/2026/gibts-nicht.eml"):
        with pytest.raises(ar.ArchiveError):
            ar.read(rel)
