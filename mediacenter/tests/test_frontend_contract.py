from __future__ import annotations

from pathlib import Path

FRONTEND = Path(__file__).parents[1] / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_canonical_frontend_is_a_cockpit_module() -> None:
    index = _read("index.tsx")
    assert 'path: "/mediacenter"' in index
    assert "cockpit: true" in index
    assert "Radarr" not in index
    assert "Sonarr" not in index


def test_frontend_api_uses_only_the_v1_mediacenter_routes() -> None:
    source = _read("api.ts")
    for route in (
        '`${BASE}/status`',
        '`${BASE}/connections/test`',
        '`${BASE}/search`',
        '`${BASE}/enqueue`',
        '`${BASE}/queue`',
        '`${BASE}/history`',
    ):
        assert route in source
    assert "http://" not in source
    assert "https://" not in source


def test_frontend_renders_all_v1_views_without_destructive_actions() -> None:
    page = _read("MediacenterPage.tsx")
    assert "ConnectionStatus" in page
    assert "SearchPanel" in page
    # V2: ResultGrid kapselt die Poster- UND die Listenansicht (ResultList).
    assert "ResultGrid" in page
    assert "ResultList" in _read("ResultGrid.tsx")
    assert "JobsPanel" in page
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.glob("*.tsx"))
    assert "mediacenterApi.enqueue" in combined
    assert "mediacenterApi.queue" in combined
    assert "mediacenterApi.history" in combined
    assert "mediacenterApi.cancel" not in combined
    assert "mediacenterApi.delete" not in combined


# --- V2: Cover-Oberflaeche und Sprachsuche ---------------------------------

def test_poster_grid_zeigt_cover_ohne_referrer_zu_lecken() -> None:
    """referrerPolicy verhindert, dass HydraHive-URLs an den Bildhost gehen."""
    for name in ("PosterCard.tsx", "GroupDetail.tsx"):
        source = _read(name)
        assert "<img" in source
        assert 'referrerPolicy="no-referrer"' in source


def test_cover_bilder_werden_lazy_geladen() -> None:
    assert 'loading="lazy"' in _read("PosterCard.tsx")


def test_poster_hat_einen_fallback_ohne_cover() -> None:
    """Buecher liefert der Indexer ohne Cover — das Raster darf nicht loechrig
    werden und ein kaputtes Bild nichts zerstoeren."""
    source = _read("PosterCard.tsx")
    assert "onError" in source
    assert "broken" in source


def test_detailansicht_behaelt_die_v1_freigabelogik() -> None:
    """V2 aendert nur die Darstellung — nie die Entscheidung, was erlaubt ist."""
    source = _read("GroupDetail.tsx")
    assert 'decision === "eligible"' in source
    assert "result_id" in source
    assert "mediacenterApi.enqueue" in source


def test_spracheingabe_ist_optional_und_clientseitig() -> None:
    """Kein Audio-Upload, kein toter Knopf ohne Browser-Unterstuetzung."""
    hook = _read("useSpeechInput.ts")
    assert "webkitSpeechRecognition" in hook
    assert "supported" in hook
    assert "fetch(" not in hook, "Spracheingabe darf nichts hochladen"
    panel = _read("SearchPanel.tsx")
    assert "speech.supported &&" in panel, "Mikrofon nur bei Unterstuetzung zeigen"


def test_frontend_nennt_weiterhin_keine_fremdprodukte() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in FRONTEND.glob("*.ts*")
    )
    assert "Radarr" not in combined
    assert "Sonarr" not in combined
