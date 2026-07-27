"""V2/C: Natuerlichsprachige Sucheingabe.

Zerlegt freien Text in strukturierte Filter. Rein lokal und regelbasiert — kein
LLM: die Suche muss offline funktionieren und darf keine Kosten pro Tastendruck
erzeugen.

Wichtigste Regel: erkannte Teile werden AUS dem Suchbegriff entfernt. Heute
scheitert "Matrix von 1999" daran, dass "von 1999" mitgesucht wird.
"""
from __future__ import annotations

import pytest

from backend.query_parser import parse_query


# --- 1. Jahr ----------------------------------------------------------------

def test_jahr_wird_erkannt_und_entfernt():
    r = parse_query("Matrix von 1999")
    assert r.query == "Matrix"
    assert r.year == 1999
    assert "year" in r.recognized


def test_jahr_in_klammern():
    r = parse_query("Der Pate (1972)")
    assert r.query == "Der Pate"
    assert r.year == 1972


def test_zahl_im_titel_ist_kein_jahr():
    """'2001' ist hier Teil des Titels — ohne Jahres-Marker nicht wegnehmen."""
    r = parse_query("2001 Odyssee im Weltraum")
    assert "2001" in r.query


def test_unplausibles_jahr_wird_ignoriert():
    r = parse_query("Test von 3200")
    assert r.year is None


# --- 2. Serie: Staffel/Folge ------------------------------------------------

@pytest.mark.parametrize("text,season", [
    ("Foundation Staffel 2", 2),
    ("Foundation staffel 2", 2),
    ("Foundation Season 2", 2),
    ("Foundation S02", 2),
])
def test_staffel_deutsch_und_englisch(text, season):
    r = parse_query(text)
    assert r.season == season
    assert r.media_type == "tv"
    assert r.query == "Foundation"


def test_s02e05_setzt_staffel_und_folge():
    r = parse_query("Foundation S02E05")
    assert (r.season, r.episode) == (2, "05")
    assert r.media_type == "tv"
    assert r.query == "Foundation"


def test_folge_deutsch():
    r = parse_query("Tatort Staffel 3 Folge 7")
    assert (r.season, r.episode) == (3, "7")
    assert r.query == "Tatort"


# --- 3. Medientyp aus Schluesselwoertern ------------------------------------

@pytest.mark.parametrize("text,media_type", [
    ("Hörbuch Der Hobbit", "audiobook"),
    ("Hoerbuch Der Hobbit", "audiobook"),
    ("Hörspiel Die drei Fragezeichen", "audioplay"),
    ("Album Rammstein Zeit", "music"),
    ("Ebook Der Hobbit", "book"),
    ("Film Matrix", "movie"),
    ("Serie Foundation", "tv"),
])
def test_medientyp_schluesselwoerter(text, media_type):
    r = parse_query(text)
    assert r.media_type == media_type
    assert "hörbuch" not in r.query.lower()
    assert "album" not in r.query.lower()


def test_medientyp_wort_wird_aus_query_entfernt():
    r = parse_query("Hörbuch Der Hobbit")
    assert r.query == "Der Hobbit"


# --- 4. Sprache -------------------------------------------------------------

def test_auf_deutsch_wird_erkannt_und_entfernt():
    r = parse_query("Foundation auf Deutsch")
    assert r.query == "Foundation"
    assert r.language == "de"


def test_german_englisch():
    r = parse_query("Foundation in german")
    assert r.query == "Foundation"
    assert r.language == "de"


# --- 5. Qualitaet -----------------------------------------------------------

@pytest.mark.parametrize("text,resolution", [
    ("Matrix in 4K", 2160),
    ("Matrix 2160p", 2160),
    ("Matrix in HD", 1080),
    ("Matrix 1080p", 1080),
])
def test_aufloesungswunsch(text, resolution):
    r = parse_query(text)
    assert r.resolution == resolution
    assert r.query == "Matrix"


def test_flac_setzt_musikformat():
    r = parse_query("Album Rammstein Zeit als FLAC")
    assert r.media_type == "music"
    assert r.audio_format == "flac"
    assert "flac" not in r.query.lower()


# --- 6. Kombination + Robustheit -------------------------------------------

def test_alles_zusammen():
    r = parse_query("Foundation Staffel 2 auf Deutsch in 4K")
    assert r.query == "Foundation"
    assert r.media_type == "tv"
    assert r.season == 2
    assert r.language == "de"
    assert r.resolution == 2160


def test_ohne_erkennbares_bleibt_alles_unveraendert():
    """Kein Treffer = exakt das Verhalten von heute."""
    r = parse_query("Irgendein Titel")
    assert r.query == "Irgendein Titel"
    assert r.media_type is None
    assert r.year is None
    assert r.recognized == []


def test_leere_eingabe():
    r = parse_query("   ")
    assert r.query == ""
    assert r.recognized == []


def test_query_wird_nie_komplett_leer_geraeumt():
    """Wenn NUR Schluesselwoerter drinstehen, darf der Titel nicht verschwinden —
    sonst sucht man ins Leere. Dann lieber den Originaltext behalten."""
    r = parse_query("Staffel 2")
    assert r.query.strip() != ""


def test_mehrfache_leerzeichen_werden_normalisiert():
    r = parse_query("Foundation   Staffel 2")
    assert r.query == "Foundation"


def test_recognized_listet_alle_treffer():
    """Die Oberflaeche zeigt daraus abnehmbare Chips — der Nutzer sieht, was
    verstanden wurde, statt unsichtbarer Magie."""
    r = parse_query("Foundation Staffel 2 auf Deutsch")
    assert set(r.recognized) >= {"media_type", "season", "language"}
