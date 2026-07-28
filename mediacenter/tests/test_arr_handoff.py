"""V3/E1: einen Suchtreffer an Radarr/Sonarr uebergeben.

tills Wunsch: "ich dachte das ich in hydra suchen kann und es an radarr oder
sonarr uebergeben kann". Die Suche bleibt im Mediacenter, den Download macht
der Zieldienst — der kennt Bibliothek, Qualitaetsprofile, Umbenennung, Import.

Nebeneffekt: das Kategorie-Problem loest sich. Ein Direktdownload des
Mediacenters landet in SABnzbd-Kategorie "movies", die Radarr ueberwacht, ohne
dass Radarr ihn bestellt hat -> importBlocked. Uebergibt Radarr selbst, kennt
es den Download.

Kette: lookup -> ggf. anlegen -> POST /release {guid, indexerId}
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend import arr_handoff
from backend.errors import MediacenterConfigError
from backend.models import ProfileDecision, RawRelease, ReleaseMeta

_NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)


def _decision(media_type: str = "movie", *, imdb: str | None = "0133093",
              tvdb: str | None = None, decision: str = "eligible") -> ProfileDecision:
    meta = ReleaseMeta(imdb_id=imdb, tvdb_id=tvdb, title_clean="The Matrix", year=1999)
    release = RawRelease(
        title="Matrix.1999.German.1080p.BluRay-GRP", guid="guid-abc",
        category_id=2140, size_bytes=1000, language="de", published_at=_NOW,
        download_url="https://treasure-maps.com/x", meta=meta,
    )
    return ProfileDecision(release, media_type, decision, ("language_confirmed",),
                           "de", "1080", None, None, 10)


class _FakeArr:
    """Protokolliert die Aufrufe an den Zieldienst."""

    def __init__(self, *, in_library: bool = False, indexer_id: int = 2):
        self.in_library = in_library
        self.indexer_id = indexer_id
        self.calls: list[tuple[str, dict]] = []

    async def lookup(self, connection, *, imdb_id=None, tvdb_id=None, term=None):
        self.calls.append(("lookup", {"imdb": imdb_id, "tvdb": tvdb_id, "term": term}))
        return {"title": "The Matrix", "year": 1999, "tmdbId": 603, "tvdbId": 1234,
                "titleSlug": "the-matrix-603", "images": [],
                "id": 42 if self.in_library else 0}

    async def add_title(self, connection, payload):
        self.calls.append(("add", payload))
        return {"id": 99, **payload}

    async def push_release(self, connection, release, indexer_id):
        self.calls.append(("push", {"guid": release.guid, "indexerId": indexer_id}))
        return True

    async def default_indexer_id(self, connection):
        return self.indexer_id


@pytest.fixture
def patched(monkeypatch):
    """Zieldienst und Credential-Aufloesung ersetzen."""
    fake = _FakeArr()

    class _Conn:
        service = "radarr"
        origin = "http://arr.example:7878"
        api_key = "geheim"

    monkeypatch.setattr(arr_handoff, "resolve_arr_connection", lambda *_: _Conn())
    monkeypatch.setattr(arr_handoff, "client", fake)
    return fake


# --- 1. Zielwahl ------------------------------------------------------------

@pytest.mark.parametrize("media_type,expected", [("movie", "radarr"), ("tv", "sonarr")])
def test_zieldienst_folgt_dem_medientyp(media_type, expected):
    assert arr_handoff.service_for(media_type) == expected


@pytest.mark.parametrize("media_type", ["book", "audiobook", "audioplay", "music"])
def test_ohne_passenden_dienst_kein_ziel(media_type):
    """Radarr/Sonarr kennen keine Buecher, Hoerbuecher oder Musik."""
    assert arr_handoff.service_for(media_type) is None


# --- 2. Uebergabe: Titel schon in der Bibliothek ---------------------------

def test_vorhandener_titel_wird_nicht_doppelt_angelegt(patched):
    import asyncio
    patched.in_library = True

    result = asyncio.run(arr_handoff.handoff(
        "till", _decision("movie"), "radarr"))

    kinds = [name for name, _ in patched.calls]
    assert "add" not in kinds, "vorhandener Titel darf nicht neu angelegt werden"
    assert "push" in kinds
    assert result.added is False
    assert result.pushed is True


def test_release_wird_mit_guid_und_indexer_uebergeben(patched):
    import asyncio
    patched.in_library = True

    asyncio.run(arr_handoff.handoff("till", _decision("movie"), "radarr"))

    push = dict(next(payload for name, payload in patched.calls if name == "push"))
    assert push["guid"] == "guid-abc"
    assert push["indexerId"] == 2


# --- 3. Uebergabe: Titel noch nicht in der Bibliothek ----------------------

def test_neuer_titel_wird_mit_profil_und_ordner_angelegt(patched):
    import asyncio

    result = asyncio.run(arr_handoff.handoff(
        "till", _decision("movie"), "radarr",
        quality_profile_id=4, root_folder_path="/filme"))

    add = dict(next(payload for name, payload in patched.calls if name == "add"))
    assert add["qualityProfileId"] == 4
    assert add["rootFolderPath"] == "/filme"
    assert add["monitored"] is True
    assert result.added is True


def test_neuer_titel_ohne_profilangabe_wird_abgelehnt(patched):
    """Kein Raten: Profil und Ordner muessen bewusst gewaehlt werden."""
    import asyncio

    with pytest.raises(MediacenterConfigError) as exc:
        asyncio.run(arr_handoff.handoff("till", _decision("movie"), "radarr"))
    assert exc.value.code == "arr_target_required"


# --- 4. Schutzregeln --------------------------------------------------------

def test_abgelehnte_fassung_wird_nicht_uebergeben(patched):
    """Die V1-Profilpruefung gilt weiter."""
    import asyncio

    with pytest.raises(MediacenterConfigError) as exc:
        asyncio.run(arr_handoff.handoff(
            "till", _decision("movie", decision="rejected"), "radarr"))
    assert exc.value.code == "result_not_eligible"


def test_falscher_dienst_fuer_den_medientyp_wird_abgelehnt(patched):
    import asyncio

    with pytest.raises(MediacenterConfigError) as exc:
        asyncio.run(arr_handoff.handoff("till", _decision("movie"), "sonarr"))
    assert exc.value.code == "arr_service_mismatch"


def test_unbekannter_dienstname_wird_abgewiesen(patched):
    import asyncio

    with pytest.raises(ValueError):
        asyncio.run(arr_handoff.handoff("till", _decision("movie"), "beliebig"))


def test_ohne_identifikator_kein_lookup_ins_blaue(patched):
    """Ohne imdb/tvdb-ID kann der Zieldienst den Titel nicht sicher zuordnen —
    dann lieber ein klarer Fehler als ein falscher Film in der Bibliothek."""
    import asyncio

    with pytest.raises(MediacenterConfigError) as exc:
        asyncio.run(arr_handoff.handoff(
            "till", _decision("movie", imdb=None), "radarr"))
    assert exc.value.code == "arr_identifier_missing"


def test_schluessel_erscheint_in_keiner_fehlermeldung(patched):
    import asyncio

    with pytest.raises(MediacenterConfigError) as exc:
        asyncio.run(arr_handoff.handoff(
            "till", _decision("movie", decision="rejected"), "radarr"))
    assert "geheim" not in str(exc.value)


# --- 5. Serien --------------------------------------------------------------

def test_serie_geht_an_sonarr_mit_tvdb_id(patched):
    import asyncio
    patched.in_library = True

    asyncio.run(arr_handoff.handoff(
        "till", _decision("tv", imdb=None, tvdb="121361"), "sonarr"))

    lookup = dict(next(payload for name, payload in patched.calls if name == "lookup"))
    assert lookup["tvdb"] == "121361"
