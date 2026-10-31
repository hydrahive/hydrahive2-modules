"""Lautheit je Titel (0.2.3): einmal messen (ffmpeg ebur128), speichern, beim Abspielen als fester Wert mitgeben.

Ersetzt normalize() im Sender, das am Titelende das Ausklingen hochzog (Befund Till 31.10.).
"""
from __future__ import annotations

import io
import subprocess

import pytest
from backend import loudness

# ffmpeg-Ausgabe von ebur128 (Ausschnitt, wie gemessen 31.10.)
_EBUR = """[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -12.1 LUFS
    Threshold: -22.4 LUFS

  Loudness range:
    LRA:         6.3 LU
"""


def test_ziel_und_grenzen():
    assert loudness.TARGET_LUFS == -14.0
    assert loudness.MAX_GAIN_DB == 10.0 and loudness.MIN_GAIN_DB == -15.0


@pytest.mark.parametrize("lufs,gain", [(-12.1, -1.9), (-14.0, 0.0), (-24.5, 10.0), (-20.0, 6.0), (0.0, -14.0),
                                       (10.0, -15.0), (-70.0, None)])
def test_gain_aus_lautheit(lufs, gain):
    assert loudness.gain_for(lufs) == gain


def test_lautheit_aus_ffmpeg_ausgabe():
    assert loudness.parse_lufs(_EBUR) == -12.1


@pytest.mark.parametrize("text", ["", "I: abc LUFS", "Integrated loudness:\n    I:  -inf LUFS", "kaputt"])
def test_lautheit_unlesbar(text):
    assert loudness.parse_lufs(text) is None


def test_lautheit_nimmt_den_zusammenfassungs_wert():
    """ebur128 schreibt zwischendurch Zeilen mit „I:“ – gilt nur der Wert unter „Integrated loudness“."""
    text = "t: 0.1 M:-20 S:-20 I: -30.0 LUFS LRA: 0\n" + _EBUR
    assert loudness.parse_lufs(text) == -12.1


def test_messen_echte_datei():
    """Echte kurze MP3 aus den Test-Daten (Sinus) – ffmpeg ist auf jedem HydraHive-Server (Kern-Installer)."""
    from smb_fake import FIX
    lufs = loudness.measure(io.BytesIO((FIX / "stille.mp3").read_bytes()), "mp3")
    assert lufs is not None and -30 < lufs < -15


def test_messen_kaputte_datei():
    assert loudness.measure(io.BytesIO(b"keine musik" * 100), "mp3") is None


def test_messen_ffmpeg_haengt(monkeypatch):
    def slow(*a, **kw):
        raise subprocess.TimeoutExpired("ffmpeg", 1)
    monkeypatch.setattr(loudness.subprocess, "run", slow)
    assert loudness.measure(io.BytesIO(b"x"), "mp3") is None


def test_messen_ohne_ffmpeg(monkeypatch):
    monkeypatch.setattr(loudness.shutil, "which", lambda _n: None)
    assert loudness.measure(io.BytesIO(b"x"), "mp3") is None


def test_messen_mit_zeitgrenze_und_ohne_shell(monkeypatch):
    seen = {}

    def run(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        return subprocess.CompletedProcess(cmd, 0, "", _EBUR)
    monkeypatch.setattr(loudness.subprocess, "run", run)
    assert loudness.measure(io.BytesIO(b"daten"), "flac") == -12.1
    assert isinstance(seen["cmd"], list) and "shell" not in seen["kw"]
    assert seen["kw"]["timeout"] == loudness.TIMEOUT_S and seen["kw"]["input"] == b"daten"
    assert seen["cmd"][seen["cmd"].index("-f") + 1] == "flac"
    assert "ebur128=framelog=quiet" in seen["cmd"]
