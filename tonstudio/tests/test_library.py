"""Erzeugen und Bibliothek (SPEC.md §4, M1). Anbieter gemockt; ffprobe/ffmpeg echt (Audio wird lokal erzeugt)."""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess

import pytest

from conftest import PROJECT_ID

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                                  reason="ffmpeg/ffprobe fehlt")


def _tone(path, seconds: float = 1.0, fmt: str = "mp3") -> bytes:
    """Echte kleine Audiodatei (Sinuston) erzeugen."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                    "-f", fmt, str(path)], check=True)
    return path.read_bytes()


class _FakeBackend:
    name = "fake"

    def __init__(self, audio: bytes, text: str = ""):
        self.audio, self.text, self.calls = audio, text, []

    async def list_models(self):
        from backend.providers import MusicModel
        return [MusicModel(id="fake/musik", name="Fake", backend="fake", lyrics=True)]

    async def generate(self, model_id, req):
        from backend.prompt import build_prompt
        from backend.providers import MusicResult
        self.calls.append((model_id, req))
        return MusicResult(audio=self.audio, ext="mp3", text=self.text, prompt=build_prompt(req))


@pytest.fixture
def fake_backend(monkeypatch, tmp_path):
    from backend import providers
    fb = _FakeBackend(_tone(tmp_path / "t.mp3", 2.0), text="[Chorus]\nla")
    monkeypatch.setattr(providers, "BACKENDS", [fb])
    return fb


@needs_ffmpeg
def test_erzeugen_speichert_clip_mit_herkunft(fake_backend, ws):
    from backend import generate
    item = asyncio.run(generate.generate_clip(PROJECT_ID, "fake/musik",
                                              {"description": "ruhiges Klavier", "bpm": 90}, user="testuser"))
    clip = ws / item["source_rel"]
    assert clip.is_file() and clip.parent == ws / "tonstudio" / "clips"
    side = json.loads(clip.with_suffix(".json").read_text())
    assert side["origin"] == "generated" and side["model"] == "fake/musik" and side["backend"] == "fake"
    assert side["prompt"].startswith("ruhiges Klavier") and side["request"]["bpm"] == 90
    assert side["returned_text"] == "[Chorus]\nla" and side["created_by"] == "testuser"
    assert 1.5 < side["duration"] < 2.6 and side["price_note"]


def test_unbekanntes_modell_wird_abgelehnt(fake_backend):
    from backend import generate
    from backend.providers import UnknownModel
    with pytest.raises(UnknownModel):
        asyncio.run(generate.generate_clip(PROJECT_ID, "gibt/es-nicht", {"description": "x"}, user="u"))


@needs_ffmpeg
def test_antwort_ohne_gueltiges_audio_wird_verworfen(monkeypatch, ws):
    """Liefert der Anbieter kein lesbares Audio, entsteht keine Datei in der Bibliothek."""
    from backend import generate, providers
    monkeypatch.setattr(providers, "BACKENDS", [_FakeBackend(b"kein audio")])
    with pytest.raises(providers.ProviderError):
        asyncio.run(generate.generate_clip(PROJECT_ID, "fake/musik", {"description": "x"}, user="u"))
    assert not list((ws / "tonstudio" / "clips").glob("*"))


@needs_ffmpeg
def test_bibliothek_zeigt_eigene_clips_und_projekt_audio(fake_backend, ws):
    from backend import generate, library
    asyncio.run(generate.generate_clip(PROJECT_ID, "fake/musik", {"description": "x"}, user="u"))
    _tone(ws / "generated" / "lied.mp3")
    _tone(ws / "atelier" / "audio" / "score.wav", fmt="wav")
    (ws / "notizen.txt").write_text("kein audio")
    items = library.list_sources(PROJECT_ID)
    origins = sorted((i["origin"], i["source_rel"].split("/")[0]) for i in items)
    assert origins == [("generated", "tonstudio"), ("project", "atelier"), ("project", "generated")]
    own = next(i for i in items if i["origin"] == "generated")
    assert own["model"] == "fake/musik" and own["duration"] > 0


@needs_ffmpeg
def test_bibliothek_nur_aus_festen_quellordnern(fake_backend, ws):
    """Live 11.10.: Die Bibliothek zeigte jede Audiodatei im Workspace (Repos, Backups, Arbeitsordner, Temp-WAVs).
    SPEC §4/M1: nur generated/ (mit Unterordnern), atelier/audio/, media/audio/ – wie der Musicplayer."""
    from backend import library
    _tone(ws / "generated" / "sub" / "a.mp3")
    _tone(ws / "media" / "audio" / "b.mp3")
    _tone(ws / "atelier" / "audio" / "c.mp3")
    for fremd in ("voice-pe/build/beep.mp3", "research/x/t.wav", "_db-backup/m/d.mp3", "media/video/v.mp3",
                  "atelier/videos/e.mp3", "atelier/audio/tief/f.mp3", "irgendwas.mp3"):
        _tone(ws / fremd)
    (ws / "generated" / "bild.png").write_bytes(b"PNG")      # kein Audio im Quellordner
    (ws / "media" / "audio" / "liste.txt").write_text("x")
    rels = sorted(i["source_rel"] for i in library.list_sources(PROJECT_ID))
    assert rels == ["atelier/audio/c.mp3", "generated/sub/a.mp3", "media/audio/b.mp3"]


@needs_ffmpeg
def test_bibliothek_folgt_keinem_symlink_nach_draussen(fake_backend, ws, tmp_path):
    from backend import library
    draussen = tmp_path / "draussen"
    _tone(draussen / "geheim.mp3")
    (ws / "generated").mkdir(exist_ok=True)
    (ws / "generated" / "link").symlink_to(draussen, target_is_directory=True)
    (ws / "generated" / "link.mp3").symlink_to(draussen / "geheim.mp3")
    try:
        assert library.list_sources(PROJECT_ID) == []
    finally:
        (ws / "generated" / "link").unlink()
        (ws / "generated" / "link.mp3").unlink()


def test_quellordner_selbst_als_symlink_wird_ignoriert(tmp_path):
    """Ganzer Quellordner (z. B. atelier) als Symlink nach draußen → nichts davon listen."""
    from backend import library
    root = tmp_path / "ws"
    draussen = tmp_path / "anderswo"
    (draussen / "audio").mkdir(parents=True)
    (draussen / "audio" / "x.mp3").write_bytes(b"ID3")
    root.mkdir()
    (root / "atelier").symlink_to(draussen, target_is_directory=True)
    assert library._files_in(root, "atelier/audio", False) == []
    (root / "echt" / "audio").mkdir(parents=True)
    (root / "echt" / "audio" / "y.mp3").write_bytes(b"ID3")
    assert [p.name for p in library._files_in(root, "echt/audio", False)] == ["y.mp3"]


@needs_ffmpeg
def test_upload_prueft_inhalt_nicht_nur_endung(ws):
    from backend import library
    good = _tone(ws / "tmp" / "a.mp3")
    item = asyncio.run(library.add_upload(PROJECT_ID, "mein song.mp3", good, user="u"))
    assert item["origin"] == "upload" and item["name"] == "mein song.mp3" and item["duration"] > 0
    with pytest.raises(library.UploadError, match="Audio"):
        asyncio.run(library.add_upload(PROJECT_ID, "falsch.mp3", b"<html>nope</html>", user="u"))
    with pytest.raises(library.UploadError, match="Format"):
        asyncio.run(library.add_upload(PROJECT_ID, "bild.png", good, user="u"))


def test_upload_zu_gross_wird_abgelehnt(monkeypatch):
    from backend import library, storage
    monkeypatch.setattr(storage, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(library.UploadError, match="groß"):
        asyncio.run(library.add_upload(PROJECT_ID, "a.mp3", b"x" * 11, user="u"))


@needs_ffmpeg
def test_loeschen_nur_eigene_clips_nicht_projektdateien(fake_backend, ws):
    from backend import generate, library
    item = asyncio.run(generate.generate_clip(PROJECT_ID, "fake/musik", {"description": "x"}, user="u"))
    _tone(ws / "generated" / "lied.mp3")
    assert library.delete_clip(PROJECT_ID, "generated/lied.mp3") is False
    assert (ws / "generated" / "lied.mp3").is_file()
    assert library.delete_clip(PROJECT_ID, "../../etc/passwd") is False
    assert library.delete_clip(PROJECT_ID, item["source_rel"]) is True
    assert not (ws / item["source_rel"]).exists()
